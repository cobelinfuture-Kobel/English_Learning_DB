#!/usr/bin/env python3
"""Run the U01QB15 learner-facing E2E in real Chromium on disposable local state.

This acceptance runner copies the already-cut-over V1.2.1 local_state to a
separate disposable state root, starts the existing authenticated localhost
product against that copy, and drives the real secure-static learner UI through
Chromium DevTools Protocol using only the Python standard library.

The canonical learner database/state is never opened for write.  The browser
acceptance proves Unit01 Reading/Writing/Speaking route through U01QB15-R1,
blueprint support fillers stay hidden, Reading completion advances the ordered
form sequence, Writing response capture reaches the existing M6 scoring/human
review path, Speaking requires four real practice exposures before completion,
and a non-Unit01 lane still uses the legacy learner route.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import quote, urlparse

from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as e2e
from ulga.builders import (
    build_a1fs_online_v1_s11_secure_authenticated_boundary as s11,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as chromium_support,
)
from ulga.builders import (
    build_a1fs_v1_u01qb14_unit01_twelve_form_private_production_replay_and_learner_form_acceptance
    as u01qb14,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Copies the already-cut-over local V1.2.1 learner state to a disposable state "
    "root and drives the existing authenticated U01QB15 learner UI in real "
    "Chromium. It creates no learner content, QuestionBank, planner, canonical "
    "learner-state write, scoring authority, Unit02-24 content, audio, speaking "
    "scoring, or A2 content."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB15_LearnerFacingE2EPrivateBrowserReadback"
PASS_STATUS = "PASS_A1FS_V1_U01QB15_LEARNER_FACING_E2E_PRIVATE_BROWSER_READBACK"
DEFAULT_OUTPUT_DIR = Path(".local/a1fs_v1/u01qb15/learner_facing_e2e_browser")
NEXT_SHORT_STEP = "A1FS-V1-U01QB15_ProductionReleaseStateAcceptanceAndUnit01NewQuestionBankCloseout"


class PrivateBrowserReadbackError(ValueError):
    """Fail-closed private browser readback error."""


def _digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _tree_digest(root: Path) -> str:
    root = Path(root).resolve()
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        h.update(relative.encode("utf-8"))
        h.update(b"\0")
        h.update(bytes.fromhex(_digest_file(path)))
    return h.hexdigest()


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _read_exact(sock: socket.socket, count: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < count:
        block = sock.recv(count - len(chunks))
        if not block:
            raise PrivateBrowserReadbackError("CDP_WEBSOCKET_CLOSED")
        chunks.extend(block)
    return bytes(chunks)


class _CDP:
    """Tiny masked WebSocket client sufficient for Chromium CDP JSON-RPC."""

    def __init__(self, websocket_url: str):
        parsed = urlparse(websocket_url)
        if parsed.scheme != "ws" or not parsed.hostname or not parsed.port:
            raise PrivateBrowserReadbackError("CDP_WEBSOCKET_URL_INVALID")
        self.sock = socket.create_connection((parsed.hostname, parsed.port), timeout=10)
        self.sock.settimeout(30)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = bytearray()
        while b"\r\n\r\n" not in response:
            response.extend(self.sock.recv(4096))
            if len(response) > 65536:
                raise PrivateBrowserReadbackError("CDP_WEBSOCKET_HANDSHAKE_TOO_LARGE")
        status = bytes(response).split(b"\r\n", 1)[0]
        if b" 101 " not in status:
            raise PrivateBrowserReadbackError(
                "CDP_WEBSOCKET_HANDSHAKE_FAILED:" + status.decode("latin1", "replace")
            )
        self.next_id = 1

    def close(self) -> None:
        try:
            self._send_frame(0x8, b"")
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        first = 0x80 | (opcode & 0x0F)
        length = len(payload)
        mask = os.urandom(4)
        if length < 126:
            header = struct.pack("!BB", first, 0x80 | length)
        elif length < 65536:
            header = struct.pack("!BBH", first, 0x80 | 126, length)
        else:
            header = struct.pack("!BBQ", first, 0x80 | 127, length)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def _recv_message(self) -> str:
        fragments = bytearray()
        active_opcode: int | None = None
        while True:
            first, second = _read_exact(self.sock, 2)
            fin = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", _read_exact(self.sock, 2))[0]
            elif length == 127:
                length = struct.unpack("!Q", _read_exact(self.sock, 8))[0]
            mask = _read_exact(self.sock, 4) if masked else b""
            payload = _read_exact(self.sock, length)
            if masked:
                payload = bytes(
                    value ^ mask[index % 4] for index, value in enumerate(payload)
                )
            if opcode == 0x8:
                raise PrivateBrowserReadbackError("CDP_WEBSOCKET_REMOTE_CLOSE")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode in {0x1, 0x2}:
                active_opcode = opcode
                fragments = bytearray(payload)
            elif opcode == 0x0 and active_opcode is not None:
                fragments.extend(payload)
            else:
                continue
            if fin:
                if active_opcode != 0x1:
                    raise PrivateBrowserReadbackError("CDP_NON_TEXT_MESSAGE")
                return bytes(fragments).decode("utf-8")

    def call(self, method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        payload = {"id": request_id, "method": method}
        if params:
            payload["params"] = dict(params)
        self._send_frame(0x1, json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        while True:
            message = json.loads(self._recv_message())
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise PrivateBrowserReadbackError(
                    f"CDP_CALL_FAILED:{method}:{message['error']}"
                )
            return dict(message.get("result") or {})

    def evaluate(self, expression: str, *, await_promise: bool = False) -> Any:
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": await_promise,
                "returnByValue": True,
                "userGesture": True,
            },
        )
        if result.get("exceptionDetails"):
            details = result["exceptionDetails"]
            raise PrivateBrowserReadbackError(
                "BROWSER_EVALUATION_FAILED:" + str(details.get("text") or details)
            )
        remote = result.get("result") or {}
        if remote.get("subtype") == "error":
            raise PrivateBrowserReadbackError(
                "BROWSER_REMOTE_ERROR:" + str(remote.get("description") or "")
            )
        return remote.get("value")


def _wait_eval(cdp: _CDP, expression: str, *, timeout: float = 15.0) -> Any:
    deadline = time.monotonic() + timeout
    last: Any = None
    while time.monotonic() < deadline:
        try:
            last = cdp.evaluate(expression)
            if last:
                return last
        except PrivateBrowserReadbackError:
            pass
        time.sleep(0.1)
    raise PrivateBrowserReadbackError(f"BROWSER_WAIT_TIMEOUT:{expression}:{last}")


def _wait_health(port: int, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 30
    url = f"http://127.0.0.1:{port}/api/health"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise PrivateBrowserReadbackError(
                f"PRODUCT_PROCESS_EXITED:{process.returncode}"
            )
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                value = json.loads(response.read().decode("utf-8"))
            if value.get("status") == "PASS" and value.get("authentication_required") is True:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise PrivateBrowserReadbackError("PRODUCT_HEALTH_TIMEOUT")


def _launch_chromium(chromium: Path, start_url: str, profile: Path) -> tuple[subprocess.Popen[bytes], _CDP]:
    profile.mkdir(parents=True, exist_ok=True)
    command = [
        str(chromium),
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--hide-scrollbars",
        "--window-size=1440,1200",
        "--remote-debugging-port=0",
        f"--user-data-dir={profile}",
        "about:blank",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    port_file = profile / "DevToolsActivePort"
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise PrivateBrowserReadbackError(
                f"CHROMIUM_PROCESS_EXITED:{process.returncode}"
            )
        if port_file.is_file():
            lines = port_file.read_text(encoding="utf-8").splitlines()
            if lines and lines[0].isdigit():
                debug_port = int(lines[0])
                break
        time.sleep(0.1)
    else:
        process.terminate()
        raise PrivateBrowserReadbackError("CHROMIUM_DEVTOOLS_PORT_TIMEOUT")

    target_url = (
        f"http://127.0.0.1:{debug_port}/json/new?"
        + quote(start_url, safe=":/?=&")
    )
    request = urllib.request.Request(target_url, method="PUT")
    with urllib.request.urlopen(request, timeout=5) as response:
        target = json.loads(response.read().decode("utf-8"))
    websocket_url = str(target.get("webSocketDebuggerUrl") or "")
    if not websocket_url:
        process.terminate()
        raise PrivateBrowserReadbackError("CHROMIUM_TARGET_WEBSOCKET_MISSING")
    cdp = _CDP(websocket_url)
    cdp.call("Page.enable")
    cdp.call("Runtime.enable")
    return process, cdp


def _accepted_response(database: Path, item_id: str) -> Any:
    response, _mode = u01qb14._accepted_response(database, item_id)
    return response


def _scoring_mode(database: Path, item_id: str) -> str:
    with closing(e2e.impl.sqlite3.connect(database)) as connection:
        row = connection.execute(
            """SELECT r.contract_json
               FROM u01qb02_item_catalog c
               JOIN response_contracts r USING(asset_key)
               WHERE c.item_id=?""",
            (item_id,),
        ).fetchone()
    if row is None:
        raise PrivateBrowserReadbackError(f"RESPONSE_CONTRACT_MISSING:{item_id}")
    return str(json.loads(str(row[0])).get("scoring_mode") or "")


def _latest_outcome(database: Path, session_id: str) -> str | None:
    with closing(e2e.impl.sqlite3.connect(database)) as connection:
        row = connection.execute(
            """SELECT s.outcome
               FROM response_attempts a JOIN scoring_results s USING(attempt_id)
               WHERE a.session_id=? ORDER BY a.attempt_sequence DESC,a.rowid DESC LIMIT 1""",
            (session_id,),
        ).fetchone()
    return None if row is None else str(row[0])


def _start_unit01(cdp: _CDP, skill: str) -> dict[str, Any]:
    skill_json = json.dumps(str(skill).upper())
    value = cdp.evaluate(
        f"""(async()=>{{
          const skill={skill_json};
          const semantics=state.learner_product_semantics||{{}};
          const lessonIds=semantics.unit01_questionbank_lesson_ids||{{}};
          const lessonId=lessonIds[skill];
          const unit=state.units.find(u=>u.lanes.some(l=>l.lesson_id===lessonId));
          if(!unit)throw new Error('unit01_unit_missing');
          const lane=unit.lanes.find(l=>l.lesson_id===lessonId);
          chooseUnit(unit); await begin(lane);
          return {{
            form_ordinal:Number((document.querySelector('#lane-note').textContent.match(/Form\\s+(\\d+)/)||[])[1]||0),
            card_count:document.querySelectorAll('[data-u01qb15-item-id]').length,
            item_ids:[...document.querySelectorAll('[data-u01qb15-item-id]')].map(n=>n.dataset.u01qb15ItemId),
            complete_disabled:complete.disabled,
            note:document.querySelector('#lane-note').textContent,
            session_id:active.session_id,
            session_version:active.session_version,
            skill:active.skill
          }};
        }})()""",
        await_promise=True,
    )
    if not isinstance(value, dict) or not value.get("session_id"):
        raise PrivateBrowserReadbackError(f"UNIT01_BROWSER_START_INVALID:{skill}:{value}")
    return value


def _submit_item(cdp: _CDP, item_id: str, response: Any) -> str:
    item_json = json.dumps(item_id)
    if isinstance(response, list):
        browser_value = " ".join(str(value) for value in response)
    else:
        browser_value = str(response)
    response_json = json.dumps(browser_value)
    result = cdp.evaluate(
        f"""(async()=>{{
          const itemId={item_json},answer={response_json};
          const card=[...document.querySelectorAll('[data-u01qb15-item-id]')]
            .find(n=>n.dataset.u01qb15ItemId===itemId);
          if(!card)throw new Error('item_card_missing:'+itemId);
          const radios=[...card.querySelectorAll('input[type=radio]')];
          if(radios.length){{
            const target=radios.find(node=>node.value===answer);
            if(!target)throw new Error('accepted_option_missing:'+itemId+':'+answer);
            target.checked=true;
          }}else{{
            const area=card.querySelector('textarea');
            if(!area)throw new Error('response_control_missing:'+itemId);
            area.value=answer;
          }}
          const output=card.querySelector('.result');
          card.querySelector('button.submit').click();
          for(let i=0;i<200;i++){{
            if(output.textContent.trim())return output.textContent.trim();
            await new Promise(resolve=>setTimeout(resolve,50));
          }}
          throw new Error('response_result_timeout:'+itemId+':'+status.textContent);
        }})()""",
        await_promise=True,
    )
    if not isinstance(result, str) or not result:
        raise PrivateBrowserReadbackError(f"BROWSER_RESPONSE_RESULT_INVALID:{item_id}")
    return result


def _expose_practice(cdp: _CDP, item_id: str) -> str:
    item_json = json.dumps(item_id)
    result = cdp.evaluate(
        f"""(async()=>{{
          const itemId={item_json};
          const card=[...document.querySelectorAll('[data-u01qb15-item-id]')]
            .find(n=>n.dataset.u01qb15ItemId===itemId);
          if(!card)throw new Error('practice_card_missing:'+itemId);
          const output=card.querySelector('.result');
          card.querySelector('button.submit').click();
          for(let i=0;i<200;i++){{
            if(output.textContent.trim())return output.textContent.trim();
            await new Promise(resolve=>setTimeout(resolve,50));
          }}
          throw new Error('practice_result_timeout:'+itemId+':'+status.textContent);
        }})()""",
        await_promise=True,
    )
    if not isinstance(result, str) or not result:
        raise PrivateBrowserReadbackError(f"BROWSER_PRACTICE_RESULT_INVALID:{item_id}")
    return result


def _finish_active(cdp: _CDP, *, complete_session: bool) -> None:
    button = "complete" if complete_session else "abandon"
    if complete_session:
        _wait_eval(cdp, "active&&complete.disabled===false")
    cdp.evaluate(f"{button}.click();true")
    _wait_eval(cdp, "active===null&&pendingResume===null", timeout=20)


def _capture_screenshot(cdp: _CDP, path: Path) -> dict[str, Any]:
    result = cdp.call(
        "Page.captureScreenshot",
        {"format": "png", "captureBeyondViewport": True, "fromSurface": True},
    )
    raw = base64.b64decode(str(result.get("data") or ""))
    if raw[:8] != b"\x89PNG\r\n\x1a\n" or len(raw) < 1024:
        raise PrivateBrowserReadbackError("CHROMIUM_SCREENSHOT_INVALID")
    Path(path).write_bytes(raw)
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _legacy_unit_smoke(cdp: _CDP) -> dict[str, Any]:
    value = cdp.evaluate(
        """(async()=>{
          const semantics=state.learner_product_semantics||{};
          const ids=new Set(Object.values(semantics.unit01_questionbank_lesson_ids||{}));
          const unit=state.units.find(u=>u.lanes.some(l=>!ids.has(l.lesson_id)));
          if(!unit)throw new Error('legacy_unit_missing');
          const lane=unit.lanes.find(l=>l.skill==='READING'&&!ids.has(l.lesson_id))
            || unit.lanes.find(l=>!ids.has(l.lesson_id));
          chooseUnit(unit);await begin(lane);
          return {
            unit_id:unit.internal_grammar_unit_id,
            lesson_id:lane.lesson_id,
            skill:lane.skill,
            legacy_card_count:document.querySelectorAll('#items .card').length,
            u01qb15_card_count:document.querySelectorAll('[data-u01qb15-item-id]').length,
            note:document.querySelector('#lane-note').textContent
          };
        })()""",
        await_promise=True,
    )
    if not isinstance(value, dict) or int(value.get("legacy_card_count") or 0) <= 0:
        raise PrivateBrowserReadbackError(f"LEGACY_UNIT_BROWSER_SMOKE_INVALID:{value}")
    if int(value.get("u01qb15_card_count") or 0) != 0:
        raise PrivateBrowserReadbackError("U01QB15_ADAPTER_LEAKED_TO_NON_UNIT01")
    _finish_active(cdp, complete_session=False)
    return value


def _database_counts(database: Path) -> dict[str, int]:
    with closing(e2e.impl.sqlite3.connect(database)) as connection:
        return {
            "session_count": int(connection.execute("SELECT COUNT(*) FROM learning_sessions").fetchone()[0]),
            "attempt_count": int(connection.execute("SELECT COUNT(*) FROM response_attempts").fetchone()[0]),
            "exposure_count": int(connection.execute("SELECT COUNT(*) FROM u01qb02_item_exposures").fetchone()[0]),
            "support_filler_exposure_count": int(
                connection.execute(
                    """SELECT COUNT(*) FROM u01qb02_item_exposures e
                       LEFT JOIN u01qb13_session_bindings b
                         ON b.session_id=e.session_id AND b.item_id=e.item_id
                       JOIN u01qb02_session_plans p USING(session_id)
                       WHERE b.activity_id IS NULL"""
                ).fetchone()[0]
            ),
        }


def run_readback(
    *,
    output_dir: Path,
    replace: bool,
    chromium_path: Path | None = None,
    source_state_root: Path | None = None,
) -> dict[str, Any]:
    product_root = Path(e2e.impl.base.PRODUCT_ROOT).resolve()
    source_state = (
        Path(source_state_root).resolve()
        if source_state_root is not None
        else (product_root / "local_state").resolve()
    )
    source_db = source_state / "shared/database/learner_runtime.sqlite3"
    source_pid = source_state / "shared/a1fs_v1_2_1.pid"
    if not source_db.is_file():
        raise PrivateBrowserReadbackError("SOURCE_LEARNER_DATABASE_MISSING")
    if source_pid.is_file():
        try:
            pid = int(source_pid.read_text(encoding="ascii").strip())
        except ValueError:
            pid = 0
        if pid and e2e.impl.base._pid_alive(pid):
            raise PrivateBrowserReadbackError(f"STOP_PRODUCT_BEFORE_BROWSER_READBACK_PID={pid}")
    for suffix in ("-wal", "-journal"):
        sidecar = Path(str(source_db) + suffix)
        if sidecar.exists() and sidecar.stat().st_size > 0:
            raise PrivateBrowserReadbackError(
                f"SOURCE_DATABASE_NOT_OFFLINE:{sidecar.name}"
            )

    cutover = e2e.cutover_status(source_db)
    if (
        cutover.get("active") is not True
        or cutover.get("runtime_item_count") != 474
        or cutover.get("extension_item_count") != 186
        or cutover.get("blueprint_activity_count") != 240
        or cutover.get("form_count") != 12
    ):
        raise PrivateBrowserReadbackError(f"SOURCE_U01QB15_CUTOVER_INVALID:{cutover}")

    output = Path(output_dir).resolve()
    disposable_state = output / "disposable_state"
    profile = output / "chromium_profile"
    screenshot_path = output / "unit01_u01qb15_reading_form.png"
    report_path = output / "u01qb15_learner_facing_e2e_browser_readback.json"
    if output.exists():
        if not replace:
            raise PrivateBrowserReadbackError("OUTPUT_EXISTS_USE_REPLACE")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    source_tree_before = _tree_digest(source_state)
    source_db_before = _digest_file(source_db)
    shutil.copytree(source_state, disposable_state)
    (disposable_state / "shared/a1fs_v1_2_1.pid").unlink(missing_ok=True)
    disposable_db = disposable_state / "shared/database/learner_runtime.sqlite3"
    if _digest_file(disposable_db) != source_db_before:
        raise PrivateBrowserReadbackError("DISPOSABLE_INITIAL_DATABASE_COPY_MISMATCH")

    app_port = _free_port()
    env = os.environ.copy()
    env["A1FS_V121_STATE_ROOT"] = str(disposable_state)
    env["A1FS_S11_AUTH_USERNAME"] = s11.CANARY_USERNAME
    env["A1FS_S11_AUTH_PASSWORD"] = s11.CANARY_PASSWORD
    env["A1FS_S11_SESSION_SECRET"] = s11.CANARY_SESSION_SECRET
    env["PYTHONPATH"] = str(product_root.parents[1]) + os.pathsep + env.get("PYTHONPATH", "")
    stdout_path = output / "product.stdout.log"
    stderr_path = output / "product.stderr.log"
    stdout = stdout_path.open("wb")
    stderr = stderr_path.open("wb")
    product_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            e2e.MODULE,
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(app_port),
        ],
        cwd=product_root.parents[1],
        env=env,
        stdout=stdout,
        stderr=stderr,
    )
    browser_process: subprocess.Popen[bytes] | None = None
    cdp: _CDP | None = None
    try:
        _wait_health(app_port, product_process)
        chromium = chromium_support.discover_chromium(chromium_path)
        browser_process, cdp = _launch_chromium(
            chromium,
            f"http://127.0.0.1:{app_port}/login.html",
            profile,
        )
        _wait_eval(cdp, "document.readyState==='complete'")
        username = json.dumps(s11.CANARY_USERNAME)
        password = json.dumps(s11.CANARY_PASSWORD)
        cdp.evaluate(
            f"""(()=>{{
              document.querySelector('#username').value={username};
              document.querySelector('#password').value={password};
              document.querySelector('#login-form').requestSubmit();
              return true;
            }})()"""
        )
        _wait_eval(cdp, "location.pathname==='/'", timeout=20)
        _wait_eval(
            cdp,
            "typeof state!=='undefined'&&state&&state.learner_product_semantics&&state.learner_product_semantics.unit01_questionbank_browser_route_active===true",
            timeout=20,
        )
        bootstrap = cdp.evaluate(
            """(()=>({
              revision:state.learner_product_semantics.unit01_questionbank_revision,
              runtime:state.learner_product_semantics.unit01_questionbank_runtime_item_count,
              forms:state.learner_product_semantics.unit01_questionbank_form_count,
              mode:state.learner_product_semantics.unit01_questionbank_form_selection_mode,
              next:state.learner_product_semantics.unit01_next_form_ordinal_by_skill
            }))()"""
        )
        if not isinstance(bootstrap, dict) or bootstrap.get("revision") != "U01QB15-R1":
            raise PrivateBrowserReadbackError(f"BROWSER_BOOTSTRAP_INVALID:{bootstrap}")

        reading = _start_unit01(cdp, "READING")
        if int(reading["card_count"]) != 8 or "U01QB15-R1" not in str(reading["note"]):
            raise PrivateBrowserReadbackError(f"READING_FORM_RENDER_INVALID:{reading}")
        screenshot = _capture_screenshot(cdp, screenshot_path)
        reading_results = []
        for item_id in reading["item_ids"]:
            result_text = _submit_item(
                cdp, str(item_id), _accepted_response(disposable_db, str(item_id))
            )
            outcome = _latest_outcome(disposable_db, str(reading["session_id"]))
            reading_results.append({"item_id": item_id, "ui_result": result_text, "outcome": outcome})
            if outcome != "AUTO_PASS":
                raise PrivateBrowserReadbackError(
                    f"READING_ACCEPTED_RESPONSE_NOT_AUTO_PASS:{item_id}:{outcome}"
                )
        _wait_eval(cdp, "complete.disabled===false", timeout=20)
        _finish_active(cdp, complete_session=True)
        reading_next = _start_unit01(cdp, "READING")
        expected_reading_next = int(reading["form_ordinal"]) + 1
        if int(reading_next["form_ordinal"]) != expected_reading_next:
            raise PrivateBrowserReadbackError(
                f"READING_ORDERED_FORM_PROGRESSION_INVALID:{reading_next['form_ordinal']}:{expected_reading_next}"
            )
        _finish_active(cdp, complete_session=False)

        writing = _start_unit01(cdp, "WRITING")
        if int(writing["card_count"]) != 8:
            raise PrivateBrowserReadbackError(f"WRITING_FORM_RENDER_INVALID:{writing}")
        writing_modes = {
            str(item_id): _scoring_mode(disposable_db, str(item_id))
            for item_id in writing["item_ids"]
        }
        preferred = next(
            (item_id for item_id, mode in writing_modes.items() if mode == "FEATURE_RUBRIC"),
            str(writing["item_ids"][0]),
        )
        writing_ui_result = _submit_item(
            cdp, preferred, _accepted_response(disposable_db, preferred)
        )
        writing_outcome = _latest_outcome(disposable_db, str(writing["session_id"]))
        if writing_outcome not in {"AUTO_PASS", "PENDING_HUMAN_REVIEW"}:
            raise PrivateBrowserReadbackError(
                f"WRITING_SCORING_OUTCOME_INVALID:{writing_outcome}"
            )
        _finish_active(cdp, complete_session=False)

        speaking = _start_unit01(cdp, "SPEAKING")
        if int(speaking["card_count"]) != 4 or speaking.get("complete_disabled") is not True:
            raise PrivateBrowserReadbackError(f"SPEAKING_INITIAL_GATE_INVALID:{speaking}")
        speaking_results = []
        for item_id in speaking["item_ids"]:
            speaking_results.append(
                {
                    "item_id": item_id,
                    "ui_result": _expose_practice(cdp, str(item_id)),
                }
            )
        _wait_eval(cdp, "complete.disabled===false", timeout=20)
        _finish_active(cdp, complete_session=True)
        speaking_next = _start_unit01(cdp, "SPEAKING")
        expected_speaking_next = int(speaking["form_ordinal"]) + 1
        if int(speaking_next["form_ordinal"]) != expected_speaking_next:
            raise PrivateBrowserReadbackError(
                f"SPEAKING_ORDERED_FORM_PROGRESSION_INVALID:{speaking_next['form_ordinal']}:{expected_speaking_next}"
            )
        _finish_active(cdp, complete_session=False)

        legacy = _legacy_unit_smoke(cdp)
        counts = _database_counts(disposable_db)
        if counts["support_filler_exposure_count"] != 0:
            raise PrivateBrowserReadbackError(
                f"SUPPORT_FILLER_EXPOSURE_LEAK:{counts['support_filler_exposure_count']}"
            )
        disposable_cutover = e2e.cutover_status(disposable_db)
        if disposable_cutover.get("active") is not True:
            raise PrivateBrowserReadbackError("DISPOSABLE_CUTOVER_LOST_DURING_BROWSER_REPLAY")

        result = {
            "schema_version": "a1fs.v1.u01qb15.learner_facing_e2e_private_browser_readback.v1",
            "program_id": PROGRAM_ID,
            "task_id": TASK_ID,
            "status": PASS_STATUS,
            "chromium": {
                "path": str(chromium),
                "screenshot": screenshot,
            },
            "source_authority": {
                "cutover_active": True,
                "questionbank_revision": cutover.get("questionbank_revision"),
                "runtime_item_count": cutover.get("runtime_item_count"),
                "extension_item_count": cutover.get("extension_item_count"),
                "blueprint_activity_count": cutover.get("blueprint_activity_count"),
                "form_count": cutover.get("form_count"),
            },
            "browser_bootstrap": bootstrap,
            "reading": {
                "initial_form_ordinal": reading["form_ordinal"],
                "blueprint_card_count": reading["card_count"],
                "accepted_response_count": len(reading_results),
                "all_accepted_responses_auto_pass": all(
                    row["outcome"] == "AUTO_PASS" for row in reading_results
                ),
                "completed": True,
                "next_form_ordinal": reading_next["form_ordinal"],
            },
            "writing": {
                "form_ordinal": writing["form_ordinal"],
                "blueprint_card_count": writing["card_count"],
                "submitted_item_id": preferred,
                "submitted_scoring_mode": writing_modes[preferred],
                "ui_result": writing_ui_result,
                "outcome": writing_outcome,
                "human_review_path_exercised": writing_outcome == "PENDING_HUMAN_REVIEW",
                "session_abandoned_after_route_proof": True,
            },
            "speaking": {
                "initial_form_ordinal": speaking["form_ordinal"],
                "blueprint_card_count": speaking["card_count"],
                "initial_completion_disabled": True,
                "practice_exposure_count": len(speaking_results),
                "completed_after_four_exposures": True,
                "next_form_ordinal": speaking_next["form_ordinal"],
                "capture_enabled": False,
                "scoring_enabled": False,
            },
            "legacy_non_unit01": {
                **legacy,
                "u01qb15_adapter_leaked": False,
            },
            "disposable_runtime": counts,
            "support_fillers_exposed_to_learner": False,
            "canonical_learner_state_touched": False,
            "unit02_to_unit24_runtime_replaced": False,
            "a2_unlocked": False,
            "listening_enabled": False,
            "speaking_scoring_enabled": False,
            "next_short_step": NEXT_SHORT_STEP,
        }
        report_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    finally:
        if cdp is not None:
            cdp.close()
        if browser_process is not None and browser_process.poll() is None:
            browser_process.terminate()
            try:
                browser_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                browser_process.kill()
        if product_process.poll() is None:
            product_process.terminate()
            try:
                product_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                product_process.kill()
        stdout.close()
        stderr.close()

    source_db_after = _digest_file(source_db)
    source_tree_after = _tree_digest(source_state)
    if source_db_after != source_db_before or source_tree_after != source_tree_before:
        raise PrivateBrowserReadbackError("CANONICAL_SOURCE_STATE_CHANGED_DURING_BROWSER_READBACK")
    result["canonical_source_database_sha256"] = source_db_before
    result["canonical_source_state_tree_sha256"] = source_tree_before
    result["canonical_source_state_unchanged"] = True
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--chromium", type=Path)
    parser.add_argument("--source-state-root", type=Path)
    args = parser.parse_args(argv)
    try:
        report = run_readback(
            output_dir=args.output_dir,
            replace=args.replace,
            chromium_path=args.chromium,
            source_state_root=args.source_state_root,
        )
    except Exception as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB15_LEARNER_FACING_E2E_PRIVATE_BROWSER_READBACK")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    print(f"QUESTIONBANK_REVISION={report['source_authority']['questionbank_revision']}")
    print(f"RUNTIME_ITEMS={report['source_authority']['runtime_item_count']}")
    print(f"READING_FORM={report['reading']['initial_form_ordinal']}")
    print(f"READING_BLUEPRINT_CARDS={report['reading']['blueprint_card_count']}")
    print(f"READING_NEXT_FORM={report['reading']['next_form_ordinal']}")
    print(f"WRITING_FORM={report['writing']['form_ordinal']}")
    print(f"WRITING_OUTCOME={report['writing']['outcome']}")
    print(f"SPEAKING_FORM={report['speaking']['initial_form_ordinal']}")
    print(f"SPEAKING_BLUEPRINT_CARDS={report['speaking']['blueprint_card_count']}")
    print(f"SPEAKING_NEXT_FORM={report['speaking']['next_form_ordinal']}")
    print(f"SUPPORT_FILLER_EXPOSURES={report['disposable_runtime']['support_filler_exposure_count']}")
    print(f"CANONICAL_SOURCE_STATE_UNCHANGED={report['canonical_source_state_unchanged']}")
    print(f"REPORT={DEFAULT_OUTPUT_DIR.resolve() / 'u01qb15_learner_facing_e2e_browser_readback.json'}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
