#!/usr/bin/env python3
"""Materialize and execute the private localhost-only A1FS Online V1 workbench.

S03 remains the runtime authority. S04 copies the immutable S03 runtime snapshot
into a private execution workspace, serves only learner-safe M5 bundles over a
loopback HTTP controller, and runs one deterministic synthetic response canary
through the existing M3 and M6 engines. It creates no curriculum, renderer,
scoring engine, mastery state, audio capability, or public release surface.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import shutil
import sqlite3
import sys
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s03_unified_learner_runtime as s03  # noqa: E402
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3  # noqa: E402
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Executes already-admitted S03 learner bundles through existing M3/M6 interfaces on loopback only; "
    "no learner content, answer authority, curriculum, mastery, audio, or public delivery is produced."
)

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S04_PrivateOnlineLearnerWorkbenchExecution_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s04.private_workbench_execution.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S04_PRIVATE_WORKBENCH_EXECUTED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S05_PrivateLearnerIdentityAndProgressPersistence_NoAudio"
CANARY_LEARNER_ID = "A1FS_ONLINE_V1_S04_CANARY"
CANARY_SESSION_ID = "A1FS_ONLINE_V1_S04_SESSION:READING"
CANARY_ATTEMPT_ID = "A1FS_ONLINE_V1_S04_ATTEMPT:READING:1"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
FORBIDDEN_SAFE_KEYS = {
    "accepted_texts", "accepted_sequence", "answer", "answer_contract", "answer_key",
    "learner_payload", "private_scoring_contract", "prompt", "prompt_text", "response",
    "rubric", "scoring_contract",
}


class WorkbenchError(ValueError):
    """Fail-closed S04 workbench error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkbenchError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise WorkbenchError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def _inside(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def _verify_s03(receipt: Mapping[str, Any], receipt_path: Path) -> tuple[Path, Path, Path]:
    if (
        receipt.get("task_id") != s03.TASK_ID
        or receipt.get("schema_version") != s03.SCHEMA_VERSION
        or receipt.get("validation_status") != s03.PASS_STATUS
        or receipt.get("product_status") != "PRIVATE_RUNTIME_CONNECTED_NOT_PUBLIC_ONLINE"
        or receipt.get("stop_reason") != "NONE"
    ):
        raise WorkbenchError("s03_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s03.digest(core):
        raise WorkbenchError("s03_receipt_digest_invalid")
    summary = receipt.get("runtime_summary", {})
    expected = {
        "runtime_lesson_count": 3,
        "runtime_asset_count": 11,
        "m5_renderer_bundle_count": 3,
        "m6_response_contract_count": 11,
        "speaking_capture_enabled_count": 0,
        "listening_runtime_item_count": 0,
        "audio_runtime_asset_count": 0,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise WorkbenchError(f"s03_runtime_summary_invalid:{key}")
    outputs = receipt.get("runtime_outputs", {})
    consumer = Path(str(outputs.get("consumer_path") or ""))
    database = Path(str(outputs.get("database_path") or ""))
    ui_root = Path(str(outputs.get("ui_root") or ""))
    source_root = receipt_path.parent / "runtime"
    if not all(path.exists() for path in (consumer, database, ui_root)):
        # Allow artifact-root relocation while preserving canonical relative layout.
        consumer = source_root / "unified_runtime_consumer.private.json"
        database = source_root / "learner_state.sqlite3"
        ui_root = source_root / "ui"
    if not consumer.is_file() or not database.is_file() or not ui_root.is_dir():
        raise WorkbenchError("s03_runtime_outputs_missing")
    return consumer, database, ui_root


def _safe_asset(asset: Mapping[str, Any]) -> dict[str, Any]:
    learner = asset.get("learner_payload")
    if not isinstance(learner, Mapping):
        raise WorkbenchError(f"m5_learner_payload_missing:{asset.get('asset_key')}")
    return {
        "asset_key": str(asset.get("asset_key") or ""),
        "role": str(asset.get("role") or ""),
        "learner_payload": deepcopy(dict(learner)),
    }


def _load_bundles(ui_root: Path) -> dict[str, dict[str, Any]]:
    bundles: dict[str, dict[str, Any]] = {}
    for skill in ("reading", "writing", "speaking"):
        path = ui_root / skill / "lesson.private.json"
        bundle = read_json(path, f"m5_bundle_{skill}")
        lesson = bundle.get("lesson", {})
        assets = bundle.get("assets", [])
        if str(lesson.get("skill") or "").casefold() != skill or not isinstance(assets, list) or not assets:
            raise WorkbenchError(f"m5_bundle_contract_invalid:{skill}")
        bundles[skill] = {
            "lesson": {
                "lesson_id": str(lesson["lesson_id"]),
                "skill": str(lesson["skill"]),
                "level": str(lesson["level"]),
            },
            "assets": [_safe_asset(asset) for asset in assets],
        }
    if sum(len(bundle["assets"]) for bundle in bundles.values()) != 11:
        raise WorkbenchError("m5_workbench_asset_count_not_11")
    return bundles


def _write_static(static_root: Path) -> None:
    static_root.mkdir(parents=True, exist_ok=True)
    index = """<!doctype html><html lang=\"zh-Hant\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'\"><title>A1FS Private Workbench</title><link rel=\"stylesheet\" href=\"/styles.css\"></head><body><main><h1>A1FS 私有學習工作台</h1><p id=\"status\" aria-live=\"polite\">載入中</p><nav id=\"lanes\" aria-label=\"技能\"></nav><section id=\"items\"></section></main><script src=\"/app.js\"></script></body></html>"""
    css = """body{font-family:system-ui,sans-serif;margin:0;background:#f4f4f4;color:#181818}main{max-width:760px;margin:auto;padding:24px}button,input,textarea{font:inherit}.lane,.submit{margin:4px;padding:10px 14px}.card{background:white;padding:16px;margin:12px 0;border-radius:8px}.options{display:grid;gap:8px}textarea{width:100%;min-height:90px}code{overflow-wrap:anywhere}"""
    js = """'use strict';let state=null;const status=document.querySelector('#status'),lanes=document.querySelector('#lanes'),items=document.querySelector('#items');const text=(n,v)=>{n.textContent=v??''};async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const j=await r.json();if(!r.ok)throw new Error(j.error||'request_failed');return j}function render(skill){items.replaceChildren();const lane=state.lanes.find(x=>x.skill===skill);for(const a of lane.assets){const c=document.createElement('article');c.className='card';const p=document.createElement('p');text(p,a.learner_payload.prompt);c.append(p);const opts=a.learner_payload.options||[];if(opts.length){const box=document.createElement('div');box.className='options';for(const o of opts){const l=document.createElement('label'),i=document.createElement('input');i.type='radio';i.name=a.asset_key;i.value=o;l.append(i,document.createTextNode(' '+o));box.append(l)}c.append(box)}else{const t=document.createElement('textarea');t.dataset.asset=a.asset_key;c.append(t)}items.append(c)}}async function start(){state=await api('/api/bootstrap');text(status,state.product_status);for(const lane of state.lanes){const b=document.createElement('button');b.className='lane';text(b,lane.skill);b.addEventListener('click',()=>render(lane.skill));lanes.append(b)}render(state.lanes[0].skill)}start().catch(e=>text(status,e.message));"""
    (static_root / "index.html").write_text(index + "\n", encoding="utf-8")
    (static_root / "styles.css").write_text(css + "\n", encoding="utf-8")
    (static_root / "app.js").write_text(js + "\n", encoding="utf-8")


class WorkbenchApplication:
    def __init__(self, *, database_path: Path, bundles: Mapping[str, Mapping[str, Any]]):
        self.database_path = Path(database_path)
        self.bundles = deepcopy(dict(bundles))
        self.state_store = m3.LearnerStateStore(self.database_path)
        self.response_store = m6.ResponseEvidenceStore(self.database_path)

    def bootstrap(self) -> dict[str, Any]:
        lanes = []
        for skill in ("reading", "writing", "speaking"):
            bundle = self.bundles[skill]
            lanes.append({
                "skill": skill.upper(),
                "lesson_id": bundle["lesson"]["lesson_id"],
                "level": bundle["lesson"]["level"],
                "asset_count": len(bundle["assets"]),
                "assets": deepcopy(bundle["assets"]),
            })
        return {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "product_status": "PRIVATE_LOCALHOST_WORKBENCH_EXECUTABLE_NOT_PUBLIC",
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "lanes": lanes,
        }

    def start_session(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        skill = str(payload.get("skill") or "").casefold()
        learner_id = str(payload.get("learner_id") or CANARY_LEARNER_ID)
        if skill not in self.bundles:
            raise WorkbenchError("workbench_skill_invalid")
        lesson_id = str(self.bundles[skill]["lesson"]["lesson_id"])
        session_id = str(payload.get("session_id") or f"A1FS_ONLINE_V1_S04_SESSION:{skill.upper()}")
        return self.state_store.start_session(
            learner_id=learner_id,
            lesson_id=lesson_id,
            session_id=session_id,
            at=str(payload.get("at") or "2026-01-02T00:00:00Z"),
        )

    def record_exposure(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self.state_store.record_exposure(
            session_id=str(payload["session_id"]),
            asset_key=str(payload["asset_key"]),
            expected_session_version=int(payload["expected_session_version"]),
            at=str(payload.get("at") or "2026-01-02T00:00:10Z"),
        )

    def submit_response(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self.response_store.capture_response(
            learner_id=str(payload.get("learner_id") or CANARY_LEARNER_ID),
            session_id=str(payload["session_id"]),
            asset_key=str(payload["asset_key"]),
            response=payload.get("response"),
            expected_session_version=int(payload["expected_session_version"]),
            attempt_id=str(payload.get("attempt_id") or CANARY_ATTEMPT_ID),
            submitted_at=str(payload.get("submitted_at") or "2026-01-02T00:00:20Z"),
        )

    def complete_session(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self.state_store.end_session(
            session_id=str(payload["session_id"]),
            outcome="COMPLETED",
            expected_session_version=int(payload["expected_session_version"]),
            at=str(payload.get("at") or "2026-01-02T00:00:30Z"),
        )


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "A1FSPrivateWorkbench/1"

    def _json(self, status: int, value: Mapping[str, Any]) -> None:
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def _static(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self._json(404, {"error": "not_found"})
            return
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    @property
    def app(self) -> WorkbenchApplication:
        return self.server.app  # type: ignore[attr-defined]

    @property
    def static_root(self) -> Path:
        return self.server.static_root  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json(200, {"status": "PASS", "loopback_only": True, "audio_enabled": False})
        elif path == "/api/bootstrap":
            self._json(200, self.app.bootstrap())
        elif path in {"/", "/index.html"}:
            self._static(self.static_root / "index.html", "text/html; charset=utf-8")
        elif path == "/app.js":
            self._static(self.static_root / "app.js", "application/javascript; charset=utf-8")
        elif path == "/styles.css":
            self._static(self.static_root / "styles.css", "text/css; charset=utf-8")
        else:
            self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0 or length > 65536:
                raise WorkbenchError("request_body_size_invalid")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise WorkbenchError("request_body_not_object")
            path = urlparse(self.path).path
            routes = {
                "/api/session/start": self.app.start_session,
                "/api/exposure": self.app.record_exposure,
                "/api/response": self.app.submit_response,
                "/api/session/complete": self.app.complete_session,
            }
            if path not in routes:
                self._json(404, {"error": "not_found"})
                return
            self._json(200, routes[path](payload))
        except (WorkbenchError, m3.StateStoreError, m6.ResponseEvidenceError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return


class WorkbenchServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: WorkbenchApplication, static_root: Path):
        host = str(address[0]).casefold()
        if host not in LOOPBACK_HOSTS:
            raise WorkbenchError(f"non_loopback_host_forbidden:{address[0]}")
        self.app = app
        self.static_root = Path(static_root)
        super().__init__(address, WorkbenchHandler)


def _request(port: int, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    value = json.loads(response.read().decode("utf-8"))
    connection.close()
    if response.status >= 400:
        raise WorkbenchError(f"http_canary_failed:{path}:{value.get('error')}")
    return value


def _database_counts(database_path: Path) -> dict[str, int]:
    with sqlite3.connect(database_path) as connection:
        queries = {
            "profile_count": "SELECT COUNT(*) FROM learner_profiles",
            "session_count": "SELECT COUNT(*) FROM learning_sessions",
            "completed_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE session_state='COMPLETED'",
            "response_attempt_count": "SELECT COUNT(*) FROM response_attempts",
            "scoring_result_count": "SELECT COUNT(*) FROM scoring_results",
            "auto_fail_count": "SELECT COUNT(*) FROM scoring_results WHERE outcome='AUTO_FAIL'",
            "speaking_attempt_count": "SELECT COUNT(*) FROM response_attempts a JOIN response_contracts c USING(asset_key) WHERE c.skill='SPEAKING'",
        }
        return {key: int(connection.execute(sql).fetchone()[0]) for key, sql in queries.items()}


def run_http_canary(*, app: WorkbenchApplication, static_root: Path) -> dict[str, Any]:
    server = WorkbenchServer(("127.0.0.1", 0), app, static_root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        health = _request(port, "GET", "/api/health")
        bootstrap = _request(port, "GET", "/api/bootstrap")
        reading = next(lane for lane in bootstrap["lanes"] if lane["skill"] == "READING")
        asset_key = str(reading["assets"][0]["asset_key"])
        session = _request(port, "POST", "/api/session/start", {
            "skill": "reading", "learner_id": CANARY_LEARNER_ID,
            "session_id": CANARY_SESSION_ID, "at": "2026-01-02T00:00:00Z",
        })
        session = _request(port, "POST", "/api/exposure", {
            "session_id": CANARY_SESSION_ID, "asset_key": asset_key,
            "expected_session_version": session["session_version"], "at": "2026-01-02T00:00:10Z",
        })
        result = _request(port, "POST", "/api/response", {
            "learner_id": CANARY_LEARNER_ID, "session_id": CANARY_SESSION_ID,
            "asset_key": asset_key, "response": "__intentional_s04_canary_wrong_answer__",
            "expected_session_version": session["session_version"], "attempt_id": CANARY_ATTEMPT_ID,
            "submitted_at": "2026-01-02T00:00:20Z",
        })
        with sqlite3.connect(app.database_path) as connection:
            version = int(connection.execute("SELECT session_version FROM learning_sessions WHERE session_id=?", (CANARY_SESSION_ID,)).fetchone()[0])
        completed = _request(port, "POST", "/api/session/complete", {
            "session_id": CANARY_SESSION_ID, "expected_session_version": version,
            "at": "2026-01-02T00:00:30Z",
        })
        return {
            "health": health,
            "bootstrap_lane_count": len(bootstrap["lanes"]),
            "bootstrap_asset_count": sum(len(lane["assets"]) for lane in bootstrap["lanes"]),
            "attempt_outcome": result["outcome"],
            "attempt_score": result["score"],
            "session_state": completed["session_state"],
            "loopback_transport_executed": True,
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def safe_scan(value: Any) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                    raise WorkbenchError(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def materialize(*, s03_receipt_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    s03_receipt_path = Path(s03_receipt_path).resolve()
    s03_receipt = read_json(s03_receipt_path, "s03_receipt")
    source_consumer, source_database, source_ui = _verify_s03(s03_receipt, s03_receipt_path)
    output_root = Path(output_root).resolve()
    workbench_root = output_root / "workbench"
    if workbench_root.exists():
        shutil.rmtree(workbench_root)
    runtime_root = workbench_root / "runtime"
    static_root = workbench_root / "static"
    shutil.copytree(source_ui, runtime_root / "ui")
    shutil.copy2(source_consumer, runtime_root / "unified_runtime_consumer.private.json")
    shutil.copy2(source_database, runtime_root / "learner_state.sqlite3")
    _write_static(static_root)
    bundles = _load_bundles(runtime_root / "ui")
    database_path = runtime_root / "learner_state.sqlite3"
    store = m3.LearnerStateStore(database_path)
    store.create_profile(
        learner_id=CANARY_LEARNER_ID,
        display_label="A1FS Online V1 S04 Canary",
        locale="zh-TW",
        timezone_name="Asia/Taipei",
        at="2026-01-02T00:00:00Z",
    )
    app = WorkbenchApplication(database_path=database_path, bundles=bundles)
    canary = run_http_canary(app=app, static_root=static_root)
    counts = _database_counts(database_path)
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": "ONLINE_V1_AUDIO_DEFERRED",
        "source_identity": {
            "s03_task_id": s03.TASK_ID,
            "s03_sha256": digest(s03_receipt),
        },
        "workbench_outputs": {
            "root": str(workbench_root),
            "database_path": str(database_path),
            "static_root": str(static_root),
            "ui_root": str(runtime_root / "ui"),
        },
        "execution_summary": {
            "lane_count": 3,
            "learner_visible_asset_count": 11,
            "http_loopback_canary_count": 1,
            "synthetic_response_attempt_count": counts["response_attempt_count"],
            "synthetic_scoring_result_count": counts["scoring_result_count"],
            "synthetic_auto_fail_count": counts["auto_fail_count"],
            "speaking_attempt_count": counts["speaking_attempt_count"],
            "listening_item_count": 0,
            "audio_runtime_asset_count": 0,
        },
        "http_canary": canary,
        "capability_contract": {
            "localhost_workbench_executable": True,
            "m3_session_state_engine_reused": True,
            "m5_learner_bundle_reused": True,
            "m6_response_scoring_engine_reused": True,
            "synthetic_response_submission_executed": True,
            "parallel_runtime_engine_created": False,
            "public_network_binding_allowed": False,
            "speaking_capture_enabled": False,
            "listening_enabled": False,
        },
        "product_status": "PRIVATE_LOCALHOST_WORKBENCH_EXECUTABLE_NOT_PUBLIC",
        "claim_boundaries": {
            "real_learner_attempt_claimed": False,
            "synthetic_canary_only": True,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "public_online_delivery_claimed": False,
            "audio_complete": False,
            "speaking_recording_complete": False,
            "a2_unlocked": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    receipt = {**receipt_core, "artifact_sha256": digest(receipt_core)}
    safe_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": receipt_core["release_profile"],
        "execution_summary": deepcopy(receipt_core["execution_summary"]),
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": receipt_core["product_status"],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    if host.casefold() not in LOOPBACK_HOSTS:
        raise WorkbenchError(f"non_loopback_host_forbidden:{host}")
    receipt = read_json(receipt_path, "s04_receipt")
    if receipt.get("validation_status") != PASS_STATUS:
        raise WorkbenchError("s04_receipt_status_invalid")
    outputs = receipt.get("workbench_outputs", {})
    database_path = Path(str(outputs.get("database_path") or ""))
    static_root = Path(str(outputs.get("static_root") or ""))
    ui_root = Path(str(outputs.get("ui_root") or ""))
    bundles = _load_bundles(ui_root)
    server = WorkbenchServer((host, port), WorkbenchApplication(database_path=database_path, bundles=bundles), static_root)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s03", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    server = commands.add_parser("serve")
    server.add_argument("--receipt", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            serve(receipt_path=args.receipt, host=args.host, port=args.port)
            return 0
        receipt, safe = materialize(s03_receipt_path=args.s03, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s04_private_online_learner_workbench_execution import validate_outputs
        validation = validate_outputs(receipt=receipt, safe_report=safe, output_root=args.output.parent, s03_receipt_path=args.s03)
        if validation["error_count"]:
            raise WorkbenchError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (WorkbenchError, m3.StateStoreError, m6.ResponseEvidenceError, OSError, sqlite3.Error, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
