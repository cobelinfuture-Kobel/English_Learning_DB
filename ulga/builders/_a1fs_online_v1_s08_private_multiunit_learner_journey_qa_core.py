#!/usr/bin/env python3
"""Execute private multi-unit learner journey QA for A1FS Online V1.

S08 reuses the S07 multi-unit admission/runtime, S05 persistent M3/M6 database,
and S07 learner bundles. It adds learner-visible active-session resume and abandon
controls, then proves a deterministic multi-unit/multi-skill journey on an isolated
copy. Production learner progress is read-only during materialization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import threading
from contextlib import closing
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s04_private_online_learner_workbench_execution as s04  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s06_private_e2e_progress_readback as s06  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s07_multiunit_runtime_expansion as s07  # noqa: E402
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3  # noqa: E402
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Exercises existing S07 learner-safe bundles and existing M3/M6 runtime on an isolated "
    "database copy, and adds active-session resume/abandon controls. It authors no curriculum, "
    "learner content, answers, mastery, audio, public delivery, or parallel runtime authority."
)

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S08_PrivateMultiUnitLearnerJourneyQA_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s08.private_multiunit_learner_journey_qa.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S08_PRIVATE_MULTIUNIT_LEARNER_JOURNEY_QA"
PRODUCT_STATUS = "PRIVATE_MULTIUNIT_LEARNER_JOURNEY_QA_READY_NOT_PUBLIC"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S09_TwentyFourUnitProductionPopulation_NoAudio"

CANARY_LEARNER_ID = "A1FS_ONLINE_V1_S08_JOURNEY_CANARY"
CANARY_SUBJECT_KEY = "A1FS_ONLINE_V1_S08_PRIVATE_SLOT"
READING_SESSION_ID = "A1FS_ONLINE_V1_S08_SESSION:READING"
WRITING_SESSION_ID = "A1FS_ONLINE_V1_S08_SESSION:WRITING"
SPEAKING_SESSION_ID = "A1FS_ONLINE_V1_S08_SESSION:SPEAKING"
READING_ATTEMPT_ID = "A1FS_ONLINE_V1_S08_ATTEMPT:READING:FAIL"
WRITING_ATTEMPT_ID = "A1FS_ONLINE_V1_S08_ATTEMPT:WRITING:PASS"

FORBIDDEN_SAFE_KEYS = {
    "accepted_texts", "accepted_sequence", "answer", "answer_contract", "answer_key",
    "asset_key", "database_path", "display_label", "learner_id", "learner_payload",
    "private_scoring_contract", "private_subject_digest", "prompt", "prompt_text",
    "response", "rubric", "scoring_contract", "session_id", "subject_key",
}


class JourneyQAError(ValueError):
    """Fail-closed S08 journey or serving error."""


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
        raise JourneyQAError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise JourneyQAError(f"{code}_not_object")
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
                    raise JourneyQAError(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def _verify_s07(receipt_path: Path) -> tuple[dict[str, Any], Path, Path, dict[str, dict[str, Any]], dict[str, int]]:
    receipt = read_json(receipt_path, "s07_receipt")
    if (
        receipt.get("task_id") != s07.TASK_ID
        or receipt.get("schema_version") != s07.SCHEMA_VERSION
        or receipt.get("validation_status") != s07.PASS_STATUS
        or receipt.get("product_status") != s07.PRODUCT_STATUS
        or receipt.get("release_profile") != s07.RELEASE_PROFILE
        or receipt.get("stop_reason") != "NONE"
    ):
        raise JourneyQAError("s07_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s07.digest(core):
        raise JourneyQAError("s07_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs")
    if not isinstance(outputs, Mapping):
        raise JourneyQAError("s07_runtime_outputs_invalid")
    database = Path(str(outputs.get("database_path") or "")).resolve()
    bundle_index = Path(str(outputs.get("bundle_index_path") or "")).resolve()
    if not database.is_file() or not bundle_index.is_file():
        raise JourneyQAError("s07_runtime_outputs_missing")
    bundles, sequence_by_grammar = s07._load_bundle_index(bundle_index)
    unit_count = len(sequence_by_grammar)
    if unit_count < 2 or len(bundles) != unit_count * 3:
        raise JourneyQAError("s07_multiunit_runtime_contract_invalid")
    return receipt, database, bundle_index, bundles, sequence_by_grammar


def _grammar_from_lesson(lesson_id: str) -> str:
    if lesson_id.count(":") < 2:
        raise JourneyQAError(f"lesson_id_contract_invalid:{lesson_id}")
    return lesson_id.split(":", 2)[1]


class JourneyWorkbenchApplication(s07.MultiUnitWorkbenchApplication):
    """S07 workbench with persistent active-session recovery and abandon controls."""

    def active_session_readback(self) -> dict[str, Any]:
        with closing(_connect(self.database_path)) as connection:
            row = connection.execute(
                """SELECT session_id,lesson_id,skill,level,session_state,session_version,started_at
                   FROM learning_sessions
                   WHERE learner_id=? AND session_state='ACTIVE'
                   ORDER BY started_at,session_id LIMIT 1""",
                (self.default_learner_id,),
            ).fetchone()
        if not row:
            return {"active": False}
        lesson_id = str(row["lesson_id"])
        bundle = self.lesson_bundles.get(lesson_id)
        if not bundle:
            raise JourneyQAError(f"active_session_bundle_missing:{lesson_id}")
        grammar_id = _grammar_from_lesson(lesson_id)
        if grammar_id not in self.sequence_by_grammar:
            raise JourneyQAError(f"active_session_unit_missing:{grammar_id}")
        return {
            "active": True,
            "grammar_unit_id": grammar_id,
            "sequence_index": self.sequence_by_grammar[grammar_id],
            "session": {
                "session_id": str(row["session_id"]),
                "lesson_id": lesson_id,
                "skill": str(row["skill"]),
                "level": str(row["level"]),
                "session_state": str(row["session_state"]),
                "session_version": int(row["session_version"]),
                "started_at": str(row["started_at"]),
            },
            "assets": deepcopy(bundle["assets"]),
        }

    def abandon_session(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self.state_store.end_session(
            session_id=str(payload["session_id"]),
            outcome="ABANDONED",
            expected_session_version=int(payload["expected_session_version"]),
            at=str(payload["at"]) if payload.get("at") else None,
        )

    def progress_readback(self) -> dict[str, Any]:
        base = s06._database_progress(self.database_path, self.default_learner_id)
        with closing(_connect(self.database_path)) as connection:
            abandoned = int(connection.execute(
                "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='ABANDONED'",
                (self.default_learner_id,),
            ).fetchone()[0])
            session_rows = connection.execute(
                "SELECT lesson_id,skill,session_state FROM learning_sessions WHERE learner_id=? ORDER BY started_at,session_id",
                (self.default_learner_id,),
            ).fetchall()
        units: dict[str, dict[str, int]] = {}
        for row in session_rows:
            grammar_id = _grammar_from_lesson(str(row["lesson_id"]))
            bucket = units.setdefault(grammar_id, {"session_count": 0, "completed_session_count": 0, "abandoned_session_count": 0})
            bucket["session_count"] += 1
            if row["session_state"] == "COMPLETED":
                bucket["completed_session_count"] += 1
            elif row["session_state"] == "ABANDONED":
                bucket["abandoned_session_count"] += 1
        summary = dict(base["summary"])
        summary["abandoned_session_count"] = abandoned
        summary["unit_count_with_sessions"] = len(units)
        summary["skill_count_with_sessions"] = len(base["skills"])
        core = {
            "summary": summary,
            "skills": deepcopy(base["skills"]),
            "units": units,
            "last_event_hash_present": bool(base["last_event_hash_present"]),
        }
        return {**core, "readback_sha256": digest(core)}


class JourneyWorkbenchHandler(s07.MultiUnitWorkbenchHandler):
    @property
    def app(self) -> JourneyWorkbenchApplication:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/api/session/active":
            self._json(200, self.app.active_session_readback())
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/session/abandon":
            super().do_POST()
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0 or length > 65536:
                raise JourneyQAError("request_body_size_invalid")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise JourneyQAError("request_body_not_object")
            self._json(200, self.app.abandon_session(payload))
        except (JourneyQAError, m3.StateStoreError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})


class JourneyWorkbenchServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: JourneyWorkbenchApplication, static_root: Path):
        if str(address[0]).casefold() not in s04.LOOPBACK_HOSTS:
            raise JourneyQAError(f"non_loopback_host_forbidden:{address[0]}")
        self.app = app
        self.static_root = Path(static_root)
        super().__init__(address, JourneyWorkbenchHandler)


def _write_static(static_root: Path) -> None:
    static_root.mkdir(parents=True, exist_ok=True)
    index = """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'"><title>A1FS Learner Journey Workbench</title><link rel="stylesheet" href="/styles.css"></head><body><main><h1>A1FS 多單元學習旅程工作台</h1><p id="status" aria-live="polite">載入中</p><section id="active-panel" hidden><h2>目前進行中的技能</h2><p id="active-label"></p><button id="resume">繼續</button><button id="abandon">放棄目前技能</button></section><nav id="units" aria-label="學習單元"></nav><nav id="lanes" aria-label="技能"></nav><section id="items"></section><button id="complete" hidden>完成目前技能</button><section class="progress"><h2>學習進度</h2><button id="refresh-progress">更新進度</button><pre id="progress" aria-live="polite"></pre></section></main><script src="/app.js"></script></body></html>"""
    css = """body{font-family:system-ui,sans-serif;margin:0;background:#f4f4f4;color:#181818}main{max-width:980px;margin:auto;padding:24px}button,input,textarea{font:inherit}.unit,.lane,.submit,#complete,#refresh-progress,#resume,#abandon{margin:4px;padding:10px 14px}.selected{font-weight:700;border-width:2px}.card,.progress,#active-panel{background:white;padding:16px;margin:12px 0;border-radius:8px}.options{display:grid;gap:8px}textarea{width:100%;min-height:90px}pre{white-space:pre-wrap;overflow-wrap:anywhere}.result{font-weight:700}button:disabled{opacity:.55}#abandon{border-color:#9a2b2b}"""
    js = """'use strict';let state=null,currentUnit=null,currentLane=null,active=null,pendingResume=null;const status=document.querySelector('#status'),units=document.querySelector('#units'),lanes=document.querySelector('#lanes'),items=document.querySelector('#items'),complete=document.querySelector('#complete'),progress=document.querySelector('#progress'),refresh=document.querySelector('#refresh-progress'),activePanel=document.querySelector('#active-panel'),activeLabel=document.querySelector('#active-label'),resume=document.querySelector('#resume'),abandon=document.querySelector('#abandon');const text=(n,v)=>{n.textContent=v??''};async function api(path,body){const hasBody=body!==undefined;const r=await fetch(path,{method:hasBody?'POST':'GET',headers:hasBody?{'Content-Type':'application/json'}:{},body:hasBody?JSON.stringify(body):undefined});const j=await r.json();if(!r.ok)throw new Error(j.error||'request_failed');return j}async function loadProgress(){text(progress,JSON.stringify(await api('/api/progress'),null,2))}function findLane(lessonId){for(const value of state.units){for(const lane of value.lanes){if(lane.lesson_id===lessonId)return{unit:value,lane}}}return null}function responseFor(card,asset){const options=asset.learner_payload.options||[];if(options.length){const checked=card.querySelector('input[type=radio]:checked');if(!checked)throw new Error('請先選擇答案');return checked.value}const area=card.querySelector('textarea');if(!area||!area.value.trim())throw new Error('請先輸入答案');return area.value}async function expose(asset){const result=await api('/api/exposure',{session_id:active.session_id,asset_key:asset.asset_key,expected_session_version:active.session_version});active.session_version=result.session_version;return result}function renderLane(lane){currentLane=lane;items.replaceChildren();for(const asset of lane.assets){const card=document.createElement('article');card.className='card';const prompt=document.createElement('p');text(prompt,asset.learner_payload.prompt);card.append(prompt);const options=asset.learner_payload.options||[];if(options.length){const box=document.createElement('div');box.className='options';for(const option of options){const label=document.createElement('label'),input=document.createElement('input');input.type='radio';input.name=asset.asset_key;input.value=option;label.append(input,document.createTextNode(' '+option));box.append(label)}card.append(box)}else if(asset.learner_payload.response_capture_enabled){const area=document.createElement('textarea');area.setAttribute('aria-label','回答');card.append(area)}const button=document.createElement('button'),result=document.createElement('p');button.className='submit';result.className='result';if(asset.learner_payload.response_capture_enabled){text(button,'送出回答');button.addEventListener('click',async()=>{try{button.disabled=true;await expose(asset);const scored=await api('/api/response',{session_id:active.session_id,asset_key:asset.asset_key,response:responseFor(card,asset),expected_session_version:active.session_version});active.session_version=scored.session_version;text(result,scored.outcome);await loadProgress()}catch(error){text(status,error.message)}finally{button.disabled=false}})}else{text(button,'標記已練習');button.addEventListener('click',async()=>{try{button.disabled=true;await expose(asset);text(result,'RECORDED');await loadProgress()}catch(error){text(status,error.message)}finally{button.disabled=false}})}card.append(button,result);items.append(card)}}function updateActivePanel(){activePanel.hidden=!pendingResume;text(activeLabel,pendingResume?pendingResume.session.lesson_id:'')}function renderUnits(){units.replaceChildren();for(const value of state.units){const button=document.createElement('button');button.className='unit';text(button,value.grammar_unit_id);button.addEventListener('click',()=>{try{chooseUnit(value)}catch(error){text(status,error.message)}});units.append(button)}}function chooseUnit(value){if(active)throw new Error('請先完成或放棄目前技能');currentUnit=value;lanes.replaceChildren();items.replaceChildren();for(const lane of value.lanes){const button=document.createElement('button');button.className='lane';text(button,lane.skill);button.addEventListener('click',()=>begin(lane).catch(error=>text(status,error.message)));lanes.append(button)}}async function begin(lane){if(active)throw new Error('請先完成或放棄目前技能');active=await api('/api/session/start',{lesson_id:lane.lesson_id});pendingResume=null;updateActivePanel();complete.hidden=false;renderLane(lane);text(status,lane.lesson_id+' started')}function restore(snapshot){const match=findLane(snapshot.session.lesson_id);if(!match)throw new Error('active_session_bundle_missing');currentUnit=match.unit;chooseUnit(match.unit);active=snapshot.session;pendingResume=null;updateActivePanel();complete.hidden=false;renderLane(match.lane);text(status,match.lane.lesson_id+' resumed')}async function finish(path){if(!active)return;const done=await api(path,{session_id:active.session_id,expected_session_version:active.session_version});text(status,done.session_state);active=null;pendingResume=null;updateActivePanel();complete.hidden=true;items.replaceChildren();await loadProgress()}complete.addEventListener('click',()=>finish('/api/session/complete').catch(error=>text(status,error.message)));abandon.addEventListener('click',async()=>{try{if(!pendingResume&&!active)return;if(!active)active=pendingResume.session;await finish('/api/session/abandon')}catch(error){text(status,error.message)}});resume.addEventListener('click',()=>{try{if(pendingResume)restore(pendingResume)}catch(error){text(status,error.message)}});refresh.addEventListener('click',()=>loadProgress().catch(error=>text(status,error.message)));async function start(){state=await api('/api/bootstrap');text(status,state.product_status);renderUnits();const snapshot=await api('/api/session/active');if(snapshot.active){pendingResume=snapshot;updateActivePanel();const match=findLane(snapshot.session.lesson_id);if(match)chooseUnit(match.unit)}else if(state.units.length)chooseUnit(state.units[0]);await loadProgress()}start().catch(error=>text(status,error.message));"""
    (static_root / "index.html").write_text(index + "\n", encoding="utf-8")
    (static_root / "styles.css").write_text(css + "\n", encoding="utf-8")
    (static_root / "app.js").write_text(js + "\n", encoding="utf-8")


def _lesson_bundle(
    bundles: Mapping[str, Mapping[str, Any]],
    sequence_by_grammar: Mapping[str, int],
    *,
    unit_rank: int,
    skill: str,
) -> tuple[str, Mapping[str, Any]]:
    grammar_ids = [row[0] for row in sorted(sequence_by_grammar.items(), key=lambda row: (row[1], row[0]))]
    if unit_rank < 1 or unit_rank > len(grammar_ids):
        raise JourneyQAError(f"journey_unit_rank_invalid:{unit_rank}")
    grammar_id = grammar_ids[unit_rank - 1]
    for lesson_id, bundle in bundles.items():
        if _grammar_from_lesson(lesson_id) == grammar_id and str(bundle["lesson"]["skill"]).upper() == skill.upper():
            return lesson_id, bundle
    raise JourneyQAError(f"journey_lesson_missing:{grammar_id}:{skill}")


def _deterministic_response(
    database_path: Path,
    assets: Sequence[Mapping[str, Any]],
    *,
    should_pass: bool,
) -> tuple[str, Any]:
    asset_keys = [str(row["asset_key"]) for row in assets]
    if not asset_keys:
        raise JourneyQAError("journey_assets_empty")
    placeholders = ",".join("?" for _ in asset_keys)
    with closing(_connect(database_path)) as connection:
        rows = connection.execute(
            f"SELECT asset_key,contract_json FROM response_contracts WHERE capture_enabled=1 AND asset_key IN ({placeholders}) ORDER BY asset_key",
            asset_keys,
        ).fetchall()
    contracts = {str(row["asset_key"]): json.loads(row["contract_json"]) for row in rows}
    for asset_key in asset_keys:
        contract = contracts.get(asset_key, {})
        mode = contract.get("scoring_mode")
        if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"} and contract.get("accepted_texts"):
            return asset_key, contract["accepted_texts"][0] if should_pass else "__intentional_s08_wrong_answer__"
        if mode == "EXACT_SEQUENCE" and contract.get("accepted_sequence"):
            return asset_key, list(contract["accepted_sequence"]) if should_pass else ["__intentional_s08_wrong_token__"]
    raise JourneyQAError("journey_deterministic_contract_missing")


def _journey_database_counts(database_path: Path) -> dict[str, int]:
    queries = {
        "profile_count": "SELECT COUNT(*) FROM learner_profiles WHERE learner_id=?",
        "session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=?",
        "completed_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='COMPLETED'",
        "abandoned_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='ABANDONED'",
        "active_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='ACTIVE'",
        "exposure_count": "SELECT COUNT(*) FROM state_events WHERE learner_id=? AND event_type='ASSET_EXPOSED'",
        "attempt_count": "SELECT COUNT(*) FROM response_attempts WHERE learner_id=?",
        "auto_pass_count": """SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id)
                              WHERE a.learner_id=? AND r.outcome='AUTO_PASS'""",
        "auto_fail_count": """SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id)
                              WHERE a.learner_id=? AND r.outcome='AUTO_FAIL'""",
        "speaking_attempt_count": """SELECT COUNT(*) FROM response_attempts a JOIN response_contracts c USING(asset_key)
                                     WHERE a.learner_id=? AND c.skill='SPEAKING'""",
        "listening_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND skill='LISTENING'",
    }
    with closing(_connect(database_path)) as connection:
        counts = {key: int(connection.execute(sql, (CANARY_LEARNER_ID,)).fetchone()[0]) for key, sql in queries.items()}
        counts["distinct_unit_count"] = len({
            _grammar_from_lesson(str(row[0]))
            for row in connection.execute(
                "SELECT lesson_id FROM learning_sessions WHERE learner_id=?",
                (CANARY_LEARNER_ID,),
            ).fetchall()
        })
        counts["distinct_skill_count"] = int(connection.execute(
            "SELECT COUNT(DISTINCT skill) FROM learning_sessions WHERE learner_id=?",
            (CANARY_LEARNER_ID,),
        ).fetchone()[0])
    return counts


def _run_journey_canary(
    *,
    production_database: Path,
    bundle_index_path: Path,
    canary_database: Path,
) -> dict[str, Any]:
    if canary_database.exists():
        canary_database.unlink()
    shutil.copy2(production_database, canary_database)
    bundles, sequence_by_grammar = s07._load_bundle_index(bundle_index_path)
    if len(sequence_by_grammar) < 2:
        raise JourneyQAError("journey_requires_two_units")
    app = JourneyWorkbenchApplication(
        database_path=canary_database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
        default_learner_id=CANARY_LEARNER_ID,
    )
    app.state_store.create_profile(
        learner_id=CANARY_LEARNER_ID,
        display_label="S08 Journey Canary",
        locale="zh-TW",
        timezone_name="Asia/Taipei",
        at="2026-01-10T00:00:00Z",
    )
    reading_lesson_id, reading_bundle = _lesson_bundle(bundles, sequence_by_grammar, unit_rank=1, skill="READING")
    writing_lesson_id, writing_bundle = _lesson_bundle(bundles, sequence_by_grammar, unit_rank=2, skill="WRITING")
    speaking_lesson_id, speaking_bundle = _lesson_bundle(bundles, sequence_by_grammar, unit_rank=2, skill="SPEAKING")

    reading_asset, wrong_response = _deterministic_response(canary_database, reading_bundle["assets"], should_pass=False)
    reading = app.start_session({
        "learner_id": CANARY_LEARNER_ID,
        "lesson_id": reading_lesson_id,
        "session_id": READING_SESSION_ID,
        "at": "2026-01-10T00:00:10Z",
    })
    reading = app.record_exposure({
        "session_id": READING_SESSION_ID,
        "asset_key": reading_asset,
        "expected_session_version": reading["session_version"],
        "at": "2026-01-10T00:00:20Z",
    })
    reading_scored = app.submit_response({
        "learner_id": CANARY_LEARNER_ID,
        "session_id": READING_SESSION_ID,
        "asset_key": reading_asset,
        "response": wrong_response,
        "expected_session_version": reading["session_version"],
        "attempt_id": READING_ATTEMPT_ID,
        "submitted_at": "2026-01-10T00:00:30Z",
    })
    if reading_scored.get("outcome") != "AUTO_FAIL":
        raise JourneyQAError("reading_failure_path_not_proven")
    switch_blocked = False
    try:
        app.start_session({
            "learner_id": CANARY_LEARNER_ID,
            "lesson_id": writing_lesson_id,
            "session_id": WRITING_SESSION_ID,
            "at": "2026-01-10T00:00:35Z",
        })
    except m3.StateStoreError as exc:
        switch_blocked = str(exc) == "active_session_exists"
    if not switch_blocked:
        raise JourneyQAError("cross_unit_switch_not_blocked_while_active")

    del app
    app = JourneyWorkbenchApplication(
        database_path=canary_database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
        default_learner_id=CANARY_LEARNER_ID,
    )
    resumed = app.active_session_readback()
    if (
        not resumed.get("active")
        or resumed.get("session", {}).get("session_id") != READING_SESSION_ID
        or int(resumed.get("session", {}).get("session_version") or 0) != int(reading_scored["session_version"])
    ):
        raise JourneyQAError("active_session_restart_resume_failed")
    reading_done = app.complete_session({
        "session_id": READING_SESSION_ID,
        "expected_session_version": resumed["session"]["session_version"],
        "at": "2026-01-10T00:00:40Z",
    })
    if reading_done.get("session_state") != "COMPLETED":
        raise JourneyQAError("reading_completion_failed")

    writing_asset, correct_response = _deterministic_response(canary_database, writing_bundle["assets"], should_pass=True)
    writing = app.start_session({
        "learner_id": CANARY_LEARNER_ID,
        "lesson_id": writing_lesson_id,
        "session_id": WRITING_SESSION_ID,
        "at": "2026-01-10T00:01:00Z",
    })
    writing = app.record_exposure({
        "session_id": WRITING_SESSION_ID,
        "asset_key": writing_asset,
        "expected_session_version": writing["session_version"],
        "at": "2026-01-10T00:01:10Z",
    })
    writing_scored = app.submit_response({
        "learner_id": CANARY_LEARNER_ID,
        "session_id": WRITING_SESSION_ID,
        "asset_key": writing_asset,
        "response": correct_response,
        "expected_session_version": writing["session_version"],
        "attempt_id": WRITING_ATTEMPT_ID,
        "submitted_at": "2026-01-10T00:01:20Z",
    })
    if writing_scored.get("outcome") != "AUTO_PASS":
        raise JourneyQAError("writing_success_path_not_proven")
    writing_done = app.complete_session({
        "session_id": WRITING_SESSION_ID,
        "expected_session_version": writing_scored["session_version"],
        "at": "2026-01-10T00:01:30Z",
    })
    if writing_done.get("session_state") != "COMPLETED":
        raise JourneyQAError("writing_completion_failed")

    speaking_asset = str(speaking_bundle["assets"][0]["asset_key"])
    speaking = app.start_session({
        "learner_id": CANARY_LEARNER_ID,
        "lesson_id": speaking_lesson_id,
        "session_id": SPEAKING_SESSION_ID,
        "at": "2026-01-10T00:02:00Z",
    })
    speaking = app.record_exposure({
        "session_id": SPEAKING_SESSION_ID,
        "asset_key": speaking_asset,
        "expected_session_version": speaking["session_version"],
        "at": "2026-01-10T00:02:10Z",
    })
    speaking_submission_blocked = False
    try:
        app.submit_response({
            "learner_id": CANARY_LEARNER_ID,
            "session_id": SPEAKING_SESSION_ID,
            "asset_key": speaking_asset,
            "response": "synthetic speaking text must not be captured",
            "expected_session_version": speaking["session_version"],
            "attempt_id": "A1FS_ONLINE_V1_S08_FORBIDDEN_SPEAKING_ATTEMPT",
            "submitted_at": "2026-01-10T00:02:20Z",
        })
    except m6.ResponseEvidenceError as exc:
        speaking_submission_blocked = str(exc) == "response_capture_not_enabled_for_asset"
    if not speaking_submission_blocked:
        raise JourneyQAError("speaking_submission_not_blocked")
    speaking_done = app.abandon_session({
        "session_id": SPEAKING_SESSION_ID,
        "expected_session_version": speaking["session_version"],
        "at": "2026-01-10T00:02:30Z",
    })
    if speaking_done.get("session_state") != "ABANDONED":
        raise JourneyQAError("speaking_abandon_failed")

    progress_before_restart = app.progress_readback()
    del app
    app = JourneyWorkbenchApplication(
        database_path=canary_database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
        default_learner_id=CANARY_LEARNER_ID,
    )
    progress_after_restart = app.progress_readback()
    if progress_before_restart != progress_after_restart or app.active_session_readback().get("active"):
        raise JourneyQAError("final_restart_progress_readback_invalid")

    counts = _journey_database_counts(canary_database)
    expected = {
        "profile_count": 1,
        "session_count": 3,
        "completed_session_count": 2,
        "abandoned_session_count": 1,
        "active_session_count": 0,
        "exposure_count": 3,
        "attempt_count": 2,
        "auto_pass_count": 1,
        "auto_fail_count": 1,
        "speaking_attempt_count": 0,
        "listening_session_count": 0,
        "distinct_unit_count": 2,
        "distinct_skill_count": 3,
    }
    for key, value in expected.items():
        if counts.get(key) != value:
            raise JourneyQAError(f"journey_count_invalid:{key}:{counts.get(key)}:{value}")
    return {
        **counts,
        "resume_after_process_restart": True,
        "cross_unit_switch_blocked_while_active": True,
        "cross_unit_switch_after_completion": True,
        "cross_skill_switch_after_completion": True,
        "speaking_submission_blocked": True,
        "final_progress_readback_digest_stable": True,
        "process_restart_count": 2,
    }


def materialize(*, s07_receipt_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    s07_receipt_path = Path(s07_receipt_path).resolve()
    s07_receipt, production_database, bundle_index_path, bundles, sequence_by_grammar = _verify_s07(s07_receipt_path)
    output_root = Path(output_root).resolve()
    journey_root = output_root / "learner_journey_qa"
    if journey_root.exists():
        shutil.rmtree(journey_root)
    journey_root.mkdir(parents=True, exist_ok=True)
    static_root = journey_root / "static"
    canary_database = journey_root / "multiunit_learner_journey_canary.sqlite3"
    _write_static(static_root)

    production_sha_before = file_digest(production_database)
    journey = _run_journey_canary(
        production_database=production_database,
        bundle_index_path=bundle_index_path,
        canary_database=canary_database,
    )
    production_sha_after = file_digest(production_database)
    if production_sha_before != production_sha_after:
        raise JourneyQAError("production_database_mutated_by_journey_canary")

    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "s07_sha256": s07.digest(s07_receipt),
            "production_database_sha256": production_sha_before,
        },
        "runtime_outputs": {
            "root": str(journey_root),
            "database_path": str(production_database),
            "bundle_index_path": str(bundle_index_path),
            "static_root": str(static_root),
            "canary_database_path": str(canary_database),
        },
        "source_runtime_summary": {
            "unit_count": len(sequence_by_grammar),
            "lesson_count": len(bundles),
            "multiunit_runtime_reused": True,
        },
        "journey_summary": journey,
        "production_safety": {
            "database_sha256_before": production_sha_before,
            "database_sha256_after": production_sha_after,
            "production_database_unchanged": production_sha_before == production_sha_after,
            "journey_executed_on_isolated_clone": True,
            "real_learner_progress_mutated_by_canary": False,
        },
        "learner_surface": {
            "active_session_readback": True,
            "resume_after_restart": True,
            "abandon_active_session": True,
            "cross_unit_navigation": True,
            "cross_skill_navigation": True,
            "progress_readback": True,
        },
        "capability_contract": {
            "s07_multiunit_runtime_reused": True,
            "m3_session_progress_authority_reused": True,
            "m5_renderer_authority_reused": True,
            "m6_response_scoring_authority_reused": True,
            "parallel_curriculum_created": False,
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
        "release_profile": RELEASE_PROFILE,
        "source_runtime_summary": deepcopy(receipt_core["source_runtime_summary"]),
        "journey_summary": deepcopy(journey),
        "production_safety": {
            "production_database_unchanged": True,
            "journey_executed_on_isolated_clone": True,
            "real_learner_progress_mutated_by_canary": False,
        },
        "learner_surface": deepcopy(receipt_core["learner_surface"]),
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def _application_from_receipt(receipt_path: Path) -> tuple[JourneyWorkbenchApplication, Path]:
    receipt = read_json(receipt_path, "s08_receipt")
    if (
        receipt.get("task_id") != TASK_ID
        or receipt.get("schema_version") != SCHEMA_VERSION
        or receipt.get("validation_status") != PASS_STATUS
        or receipt.get("product_status") != PRODUCT_STATUS
        or receipt.get("stop_reason") != "NONE"
    ):
        raise JourneyQAError("s08_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise JourneyQAError("s08_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs", {})
    database = Path(str(outputs.get("database_path") or "")).resolve()
    bundle_index = Path(str(outputs.get("bundle_index_path") or "")).resolve()
    static_root = Path(str(outputs.get("static_root") or "")).resolve()
    if not database.is_file() or not bundle_index.is_file() or not static_root.is_dir():
        raise JourneyQAError("s08_runtime_outputs_missing")
    bundles, sequence_by_grammar = s07._load_bundle_index(bundle_index)
    return JourneyWorkbenchApplication(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
        default_learner_id=s05.DEFAULT_LEARNER_ID,
    ), static_root


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    app, static_root = _application_from_receipt(receipt_path)
    server = JourneyWorkbenchServer((host, port), app, static_root)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def readback(*, receipt_path: Path) -> dict[str, Any]:
    app, _ = _application_from_receipt(receipt_path)
    active = app.active_session_readback()
    return {
        "unit_count": len(app.sequence_by_grammar),
        "lesson_count": len(app.lesson_bundles),
        "active_session": active,
        "progress": app.progress_readback(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s07", type=Path, required=True)
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
        receipt, safe = materialize(s07_receipt_path=args.s07, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s08_private_multiunit_learner_journey_qa import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s07_path=args.s07,
        )
        if validation["error_count"]:
            raise JourneyQAError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        JourneyQAError,
        s04.WorkbenchError,
        s05.PersistenceError,
        s06.ReadbackError,
        s07.MultiUnitExpansionError,
        m3.StateStoreError,
        m6.ResponseEvidenceError,
        OSError,
        sqlite3.Error,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
