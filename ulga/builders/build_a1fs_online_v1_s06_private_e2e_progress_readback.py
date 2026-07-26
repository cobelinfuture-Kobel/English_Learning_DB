#!/usr/bin/env python3
"""Private end-to-end learner session and progress readback for A1FS Online V1.

S06 keeps the S05 persistent M3/M6 database as the only production authority.
It adds a loopback-only progress readback surface and proves the complete
session lifecycle on an isolated clone so production learner progress is not
modified by materialization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s04_private_online_learner_workbench_execution as s04  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05  # noqa: E402
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3  # noqa: E402
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Adds learner-safe progress readback and validates an isolated synthetic session through existing "
    "S05/M3/M6 authorities; no curriculum, answer content, mastery, audio, or public delivery is produced."
)

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S06_PrivateLearnerEndToEndSessionProgressReadback_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s06.private_e2e_progress_readback.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S06_PRIVATE_E2E_PROGRESS_READBACK"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S07_MultiUnitProductionAdmissionAndRuntimeExpansion_NoAudio"
PRODUCT_STATUS = "PRIVATE_END_TO_END_SESSION_PROGRESS_READBACK_READY_NOT_PUBLIC"

CANARY_LEARNER_ID = "A1FS_ONLINE_V1_S06_E2E_CANARY"
CANARY_SESSION_ID = "A1FS_ONLINE_V1_S06_SESSION:READING"
CANARY_PASS_ATTEMPT_ID = "A1FS_ONLINE_V1_S06_ATTEMPT:PASS"
CANARY_FAIL_ATTEMPT_ID = "A1FS_ONLINE_V1_S06_ATTEMPT:FAIL"
CANARY_SUBJECT_KEY = "A1FS_ONLINE_V1_S06_PRIVATE_SLOT"

FORBIDDEN_SAFE_KEYS = {
    "accepted_texts", "accepted_sequence", "answer", "answer_contract", "answer_key",
    "asset_key", "database_path", "display_label", "learner_id", "learner_payload",
    "private_scoring_contract", "private_subject_digest", "prompt", "prompt_text",
    "response", "rubric", "scoring_contract", "session_id", "subject_key",
}


class ReadbackError(ValueError):
    """Fail-closed S06 readback error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReadbackError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ReadbackError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def safe_scan(value: Any) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                    raise ReadbackError(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def _verify_s05(receipt_path: Path) -> tuple[dict[str, Any], Path, Path, Path]:
    receipt = read_json(receipt_path, "s05_receipt")
    if (
        receipt.get("task_id") != s05.TASK_ID
        or receipt.get("schema_version") != s05.SCHEMA_VERSION
        or receipt.get("validation_status") != s05.PASS_STATUS
        or receipt.get("product_status") != s05.PRODUCT_STATUS
        or receipt.get("stop_reason") != "NONE"
    ):
        raise ReadbackError("s05_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s05.digest(core):
        raise ReadbackError("s05_receipt_digest_invalid")
    outputs = receipt.get("persistent_outputs")
    if not isinstance(outputs, Mapping):
        raise ReadbackError("s05_persistent_outputs_invalid")
    database = Path(str(outputs.get("database_path") or "")).resolve()
    ui_root = Path(str(outputs.get("ui_root") or "")).resolve()
    static_root = Path(str(outputs.get("static_root") or "")).resolve()
    if not database.is_file() or not ui_root.is_dir() or not static_root.is_dir():
        raise ReadbackError("s05_persistent_outputs_missing")
    return receipt, database, ui_root, static_root


def _database_progress(database_path: Path, learner_id: str) -> dict[str, Any]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        profile = connection.execute(
            "SELECT profile_state FROM learner_profiles WHERE learner_id=?",
            (learner_id,),
        ).fetchone()
        if not profile:
            raise ReadbackError("progress_learner_not_found")
        summary = {
            "profile_active": profile["profile_state"] == "ACTIVE",
            "session_count": int(connection.execute(
                "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=?", (learner_id,)
            ).fetchone()[0]),
            "completed_session_count": int(connection.execute(
                "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='COMPLETED'",
                (learner_id,),
            ).fetchone()[0]),
            "active_session_count": int(connection.execute(
                "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='ACTIVE'",
                (learner_id,),
            ).fetchone()[0]),
            "exposure_count": int(connection.execute(
                "SELECT COUNT(*) FROM state_events WHERE learner_id=? AND event_type='ASSET_EXPOSED'",
                (learner_id,),
            ).fetchone()[0]),
            "attempt_count": int(connection.execute(
                "SELECT COUNT(*) FROM response_attempts WHERE learner_id=?", (learner_id,)
            ).fetchone()[0]),
            "auto_pass_count": int(connection.execute(
                """SELECT COUNT(*) FROM scoring_results r
                   JOIN response_attempts a USING(attempt_id)
                   WHERE a.learner_id=? AND r.outcome='AUTO_PASS'""",
                (learner_id,),
            ).fetchone()[0]),
            "auto_fail_count": int(connection.execute(
                """SELECT COUNT(*) FROM scoring_results r
                   JOIN response_attempts a USING(attempt_id)
                   WHERE a.learner_id=? AND r.outcome='AUTO_FAIL'""",
                (learner_id,),
            ).fetchone()[0]),
            "pending_human_review_count": int(connection.execute(
                """SELECT COUNT(*) FROM scoring_results r
                   JOIN response_attempts a USING(attempt_id)
                   WHERE a.learner_id=? AND r.outcome='PENDING_HUMAN_REVIEW'""",
                (learner_id,),
            ).fetchone()[0]),
        }
        skill_rows = connection.execute(
            """SELECT skill, COUNT(*) AS session_count,
                      SUM(CASE WHEN session_state='COMPLETED' THEN 1 ELSE 0 END) AS completed_count
               FROM learning_sessions WHERE learner_id=? GROUP BY skill ORDER BY skill""",
            (learner_id,),
        ).fetchall()
        attempts = connection.execute(
            """SELECT c.skill, COUNT(*) AS attempt_count,
                      SUM(CASE WHEN r.outcome='AUTO_PASS' THEN 1 ELSE 0 END) AS pass_count,
                      SUM(CASE WHEN r.outcome='AUTO_FAIL' THEN 1 ELSE 0 END) AS fail_count
               FROM response_attempts a
               JOIN response_contracts c USING(asset_key)
               JOIN scoring_results r USING(attempt_id)
               WHERE a.learner_id=? GROUP BY c.skill ORDER BY c.skill""",
            (learner_id,),
        ).fetchall()
        skills: dict[str, dict[str, int]] = {}
        for row in skill_rows:
            skills[str(row["skill"])] = {
                "session_count": int(row["session_count"]),
                "completed_session_count": int(row["completed_count"] or 0),
                "attempt_count": 0,
                "auto_pass_count": 0,
                "auto_fail_count": 0,
            }
        for row in attempts:
            bucket = skills.setdefault(str(row["skill"]), {
                "session_count": 0,
                "completed_session_count": 0,
                "attempt_count": 0,
                "auto_pass_count": 0,
                "auto_fail_count": 0,
            })
            bucket["attempt_count"] = int(row["attempt_count"])
            bucket["auto_pass_count"] = int(row["pass_count"] or 0)
            bucket["auto_fail_count"] = int(row["fail_count"] or 0)
        last_event = connection.execute(
            "SELECT event_hash FROM state_events WHERE learner_id=? ORDER BY event_seq DESC LIMIT 1",
            (learner_id,),
        ).fetchone()
    core = {"summary": summary, "skills": skills, "last_event_hash_present": bool(last_event)}
    return {**core, "readback_sha256": digest(core)}


def _response_candidates(database_path: Path, reading_assets: Sequence[Mapping[str, Any]]) -> list[tuple[str, Any, Any]]:
    asset_keys = [str(row["asset_key"]) for row in reading_assets]
    placeholders = ",".join("?" for _ in asset_keys)
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            f"""SELECT asset_key,contract_json FROM response_contracts
                WHERE capture_enabled=1 AND asset_key IN ({placeholders}) ORDER BY asset_key""",
            asset_keys,
        ).fetchall()
    result: list[tuple[str, Any, Any]] = []
    for asset_key, raw in rows:
        contract = json.loads(raw)
        mode = contract.get("scoring_mode")
        if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"} and contract.get("accepted_texts"):
            correct = contract["accepted_texts"][0]
            wrong = "__intentional_s06_wrong_answer__"
        elif mode == "EXACT_SEQUENCE" and contract.get("accepted_sequence"):
            correct = list(contract["accepted_sequence"])
            wrong = ["__intentional_s06_wrong_token__"]
        else:
            continue
        result.append((str(asset_key), correct, wrong))
    if len(result) < 2:
        raise ReadbackError("s06_two_deterministic_reading_contracts_required")
    return result[:2]


class ProgressReadbackApplication(s05.PersistentWorkbenchApplication):
    def progress_readback(self) -> dict[str, Any]:
        return _database_progress(self.database_path, s05.DEFAULT_LEARNER_ID)


class ProgressReadbackHandler(s04.WorkbenchHandler):
    @property
    def app(self) -> ProgressReadbackApplication:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] == "/api/progress":
            self._json(200, self.app.progress_readback())
            return
        super().do_GET()


class ProgressReadbackServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: ProgressReadbackApplication, static_root: Path):
        if str(address[0]).casefold() not in s04.LOOPBACK_HOSTS:
            raise ReadbackError(f"non_loopback_host_forbidden:{address[0]}")
        self.app = app
        self.static_root = Path(static_root)
        super().__init__(address, ProgressReadbackHandler)


def _write_static(static_root: Path) -> None:
    static_root.mkdir(parents=True, exist_ok=True)
    index = """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'"><title>A1FS Private Progress Workbench</title><link rel="stylesheet" href="/styles.css"></head><body><main><h1>A1FS 私有學習工作台</h1><p id="status" aria-live="polite">載入中</p><nav id="lanes" aria-label="技能"></nav><section id="items"></section><button id="complete" hidden>完成目前技能</button><section class="progress"><h2>學習進度</h2><button id="refresh-progress">更新進度</button><pre id="progress" aria-live="polite"></pre></section></main><script src="/app.js"></script></body></html>"""
    css = """body{font-family:system-ui,sans-serif;margin:0;background:#f4f4f4;color:#181818}main{max-width:760px;margin:auto;padding:24px}button,input,textarea{font:inherit}.lane,.submit,#complete,#refresh-progress{margin:4px;padding:10px 14px}.card,.progress{background:white;padding:16px;margin:12px 0;border-radius:8px}.options{display:grid;gap:8px}textarea{width:100%;min-height:90px}pre{white-space:pre-wrap;overflow-wrap:anywhere}.result{font-weight:700}button:disabled{opacity:.55}"""
    js = """'use strict';let state=null,active=null;const status=document.querySelector('#status'),lanes=document.querySelector('#lanes'),items=document.querySelector('#items'),complete=document.querySelector('#complete'),progress=document.querySelector('#progress'),refresh=document.querySelector('#refresh-progress');const text=(n,v)=>{n.textContent=v??''};async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const j=await r.json();if(!r.ok)throw new Error(j.error||'request_failed');return j}async function loadProgress(){const value=await api('/api/progress');text(progress,JSON.stringify(value,null,2))}function responseFor(card,asset){const options=asset.learner_payload.options||[];if(options.length){const checked=card.querySelector('input[type=radio]:checked');if(!checked)throw new Error('請先選擇答案');return checked.value}const area=card.querySelector('textarea');if(!area||!area.value.trim())throw new Error('請先輸入答案');return area.value}async function expose(asset){const result=await api('/api/exposure',{session_id:active.session_id,asset_key:asset.asset_key,expected_session_version:active.session_version});active.session_version=result.session_version;return result}function render(skill){items.replaceChildren();const lane=state.lanes.find(x=>x.skill===skill);for(const asset of lane.assets){const card=document.createElement('article');card.className='card';const prompt=document.createElement('p');text(prompt,asset.learner_payload.prompt);card.append(prompt);const options=asset.learner_payload.options||[];if(options.length){const box=document.createElement('div');box.className='options';for(const option of options){const label=document.createElement('label'),input=document.createElement('input');input.type='radio';input.name=asset.asset_key;input.value=option;label.append(input,document.createTextNode(' '+option));box.append(label)}card.append(box)}else if(asset.learner_payload.response_capture_enabled){const area=document.createElement('textarea');area.setAttribute('aria-label','回答');card.append(area)}const button=document.createElement('button');button.className='submit';const result=document.createElement('p');result.className='result';if(asset.learner_payload.response_capture_enabled){text(button,'送出回答');button.addEventListener('click',async()=>{try{button.disabled=true;await expose(asset);const scored=await api('/api/response',{session_id:active.session_id,asset_key:asset.asset_key,response:responseFor(card,asset),expected_session_version:active.session_version});active.session_version=scored.session_version;text(result,scored.outcome);await loadProgress()}catch(error){text(status,error.message)}finally{button.disabled=false}})}else{text(button,'標記已練習');button.addEventListener('click',async()=>{try{button.disabled=true;await expose(asset);text(result,'RECORDED');await loadProgress()}catch(error){text(status,error.message)}finally{button.disabled=false}})}card.append(button,result);items.append(card)}}async function begin(skill){if(active)throw new Error('請先完成目前技能');const session=await api('/api/session/start',{skill:skill.toLowerCase()});active=session;complete.hidden=false;render(skill);text(status,skill+' session started')}complete.addEventListener('click',async()=>{try{if(!active)return;const done=await api('/api/session/complete',{session_id:active.session_id,expected_session_version:active.session_version});text(status,done.session_state);active=null;complete.hidden=true;items.replaceChildren();await loadProgress()}catch(error){text(status,error.message)}});refresh.addEventListener('click',()=>loadProgress().catch(error=>text(status,error.message)));async function start(){state=await api('/api/bootstrap');text(status,state.product_status);for(const lane of state.lanes){const button=document.createElement('button');button.className='lane';text(button,lane.skill);button.addEventListener('click',()=>begin(lane.skill).catch(error=>text(status,error.message)));lanes.append(button)}await loadProgress()}start().catch(error=>text(status,error.message));"""
    (static_root / "index.html").write_text(index + "\n", encoding="utf-8")
    (static_root / "styles.css").write_text(css + "\n", encoding="utf-8")
    (static_root / "app.js").write_text(js + "\n", encoding="utf-8")


def run_canary(*, source_database: Path, ui_root: Path, canary_database: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    production_before = file_digest(source_database)
    shutil.copy2(source_database, canary_database)
    bundles = s04._load_bundles(ui_root)
    app = ProgressReadbackApplication(database_path=canary_database, bundles=bundles)
    app.enroll(
        learner_id=CANARY_LEARNER_ID,
        display_label="S06 E2E Canary",
        subject_key=CANARY_SUBJECT_KEY,
        at="2026-01-08T00:00:00Z",
    )
    before = _database_progress(canary_database, CANARY_LEARNER_ID)
    candidates = _response_candidates(canary_database, bundles["reading"]["assets"])
    session = app.start_session({
        "skill": "reading",
        "learner_id": CANARY_LEARNER_ID,
        "session_id": CANARY_SESSION_ID,
        "at": "2026-01-08T00:00:10Z",
    })
    outcomes: list[str] = []
    trace_steps: list[dict[str, Any]] = []
    for index, (asset_key, correct, wrong) in enumerate(candidates):
        session = app.record_exposure({
            "session_id": CANARY_SESSION_ID,
            "asset_key": asset_key,
            "expected_session_version": session["session_version"],
            "at": f"2026-01-08T00:00:{20 + index * 20:02d}Z",
        })
        result = app.submit_response({
            "learner_id": CANARY_LEARNER_ID,
            "session_id": CANARY_SESSION_ID,
            "asset_key": asset_key,
            "response": correct if index == 0 else wrong,
            "expected_session_version": session["session_version"],
            "attempt_id": CANARY_PASS_ATTEMPT_ID if index == 0 else CANARY_FAIL_ATTEMPT_ID,
            "submitted_at": f"2026-01-08T00:00:{30 + index * 20:02d}Z",
        })
        session["session_version"] = result["session_version"]
        outcomes.append(str(result["outcome"]))
        trace_steps.append({
            "step": index + 1,
            "asset_identity_sha256": digest(asset_key),
            "outcome": result["outcome"],
            "score": result["score"],
        })
    completed = app.complete_session({
        "session_id": CANARY_SESSION_ID,
        "expected_session_version": session["session_version"],
        "at": "2026-01-08T00:01:10Z",
    })
    after = _database_progress(canary_database, CANARY_LEARNER_ID)
    reopened = _database_progress(canary_database, CANARY_LEARNER_ID)
    production_after = file_digest(source_database)
    if outcomes != ["AUTO_PASS", "AUTO_FAIL"]:
        raise ReadbackError(f"s06_canary_outcomes_invalid:{outcomes}")
    if completed.get("session_state") != "COMPLETED":
        raise ReadbackError("s06_canary_session_not_completed")
    expected_after = {
        "session_count": 1,
        "completed_session_count": 1,
        "active_session_count": 0,
        "exposure_count": 2,
        "attempt_count": 2,
        "auto_pass_count": 1,
        "auto_fail_count": 1,
        "pending_human_review_count": 0,
    }
    for key, expected in expected_after.items():
        if after["summary"].get(key) != expected:
            raise ReadbackError(f"s06_canary_count_invalid:{key}:{after['summary'].get(key)}:{expected}")
    if reopened["readback_sha256"] != after["readback_sha256"]:
        raise ReadbackError("s06_restart_readback_digest_mismatch")
    if production_before != production_after:
        raise ReadbackError("s06_production_database_modified")
    summary = {
        "session_count": 1,
        "completed_session_count": 1,
        "exposure_count": 2,
        "attempt_count": 2,
        "auto_pass_count": 1,
        "auto_fail_count": 1,
        "restart_readback_count": 1,
        "restart_readback_digest_stable": True,
        "production_database_unchanged": True,
        "speaking_attempt_count": 0,
        "listening_session_count": 0,
        "audio_runtime_asset_count": 0,
    }
    trace = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "synthetic_canary_only": True,
        "before_readback_sha256": before["readback_sha256"],
        "after_readback_sha256": after["readback_sha256"],
        "steps": trace_steps,
        "completed_session_state": completed["session_state"],
        "production_database_sha256_before": production_before,
        "production_database_sha256_after": production_after,
        "summary": summary,
    }
    return summary, trace


def materialize(*, s05_receipt_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    s05_receipt_path = Path(s05_receipt_path).resolve()
    s05_receipt, production_database, ui_root, _ = _verify_s05(s05_receipt_path)
    output_root = Path(output_root).resolve()
    root = output_root / "readback"
    root.mkdir(parents=True, exist_ok=True)
    static_root = root / "static"
    _write_static(static_root)
    canary_database = root / "e2e_canary.sqlite3"
    if canary_database.exists():
        canary_database.unlink()
    summary, trace = run_canary(
        source_database=production_database,
        ui_root=ui_root,
        canary_database=canary_database,
    )
    trace_path = root / "e2e_session_trace.private.json"
    write_json(trace_path, trace, private=True)
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": "ONLINE_V1_AUDIO_DEFERRED",
        "source_identity": {"s05_task_id": s05.TASK_ID, "s05_sha256": digest(s05_receipt)},
        "runtime_outputs": {
            "root": str(root),
            "database_path": str(production_database),
            "ui_root": str(ui_root),
            "static_root": str(static_root),
            "canary_database_path": str(canary_database),
            "session_trace_path": str(trace_path),
        },
        "end_to_end_summary": summary,
        "progress_surface": {
            "loopback_progress_endpoint": "/api/progress",
            "learner_safe_progress_panel": True,
            "default_private_slot_bound": True,
            "progress_readback_fields": [
                "session_count", "completed_session_count", "exposure_count",
                "attempt_count", "auto_pass_count", "auto_fail_count",
            ],
        },
        "capability_contract": {
            "m3_session_progress_authority_reused": True,
            "m6_response_scoring_authority_reused": True,
            "persistent_s05_database_reused": True,
            "production_database_mutated_by_canary": False,
            "parallel_state_engine_created": False,
            "parallel_scoring_engine_created": False,
            "public_network_binding_allowed": False,
            "speaking_capture_enabled": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "mastery_write_enabled": False,
        },
        "product_status": PRODUCT_STATUS,
        "claim_boundaries": {
            "synthetic_canary_only": True,
            "real_learner_attempt_claimed": False,
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
        "end_to_end_summary": deepcopy(summary),
        "progress_surface": deepcopy(receipt_core["progress_surface"]),
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    if host.casefold() not in s04.LOOPBACK_HOSTS:
        raise ReadbackError(f"non_loopback_host_forbidden:{host}")
    receipt = read_json(receipt_path, "s06_receipt")
    if receipt.get("validation_status") != PASS_STATUS:
        raise ReadbackError("s06_receipt_status_invalid")
    outputs = receipt.get("runtime_outputs", {})
    database = Path(str(outputs.get("database_path") or ""))
    ui_root = Path(str(outputs.get("ui_root") or ""))
    static_root = Path(str(outputs.get("static_root") or ""))
    server = ProgressReadbackServer(
        (host, port),
        ProgressReadbackApplication(database_path=database, bundles=s04._load_bundles(ui_root)),
        static_root,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def readback(*, receipt_path: Path) -> dict[str, Any]:
    receipt = read_json(receipt_path, "s06_receipt")
    if receipt.get("validation_status") != PASS_STATUS:
        raise ReadbackError("s06_receipt_status_invalid")
    database = Path(str(receipt.get("runtime_outputs", {}).get("database_path") or ""))
    return _database_progress(database, s05.DEFAULT_LEARNER_ID)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s05", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    server = commands.add_parser("serve")
    server.add_argument("--receipt", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8765)
    snap = commands.add_parser("readback")
    snap.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            serve(receipt_path=args.receipt, host=args.host, port=args.port)
            return 0
        if args.command == "readback":
            print(json.dumps(readback(receipt_path=args.receipt), ensure_ascii=False, indent=2))
            return 0
        receipt, safe = materialize(s05_receipt_path=args.s05, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s06_private_e2e_progress_readback import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s05_receipt_path=args.s05,
        )
        if validation["error_count"]:
            raise ReadbackError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        ReadbackError, s05.PersistenceError, s04.WorkbenchError,
        m3.StateStoreError, m6.ResponseEvidenceError,
        OSError, sqlite3.Error, KeyError, TypeError, ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
