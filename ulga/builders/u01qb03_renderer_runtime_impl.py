#!/usr/bin/env python3
"""Render Unit01 approved variants and submit real attempts through M3/M6.

U01QB03 is an adapter over U01QB02. It does not create another planner,
learner database, exposure store, response table, or scoring engine. It renders
one existing ten-item Unit01 session as a private localhost learner workbench
and routes exposure/response requests back through U01QB02, which reuses M3 and
M6.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from ulga.builders import build_a1fs_v1_m5_four_skill_renderer_learner_ui as m5
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Consumes the U01QB02 learner-safe session plan and existing M3/M6 runtime; "
    "no learner content, planner, learner database, exposure authority, response capture, "
    "scoring authority, audio, A2 content, or Unit02-Unit24 content is produced."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB03_Unit01ApprovedVariantLearnerRendererAndRealAttemptAcceptance"
SCHEMA_VERSION = "a1fs.v1.u01qb03.unit01_learner_renderer_real_attempt.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB03_UNIT01_LEARNER_RENDERER_REAL_ATTEMPT_ACCEPTANCE"
NEXT_SHORT_STEP = "A1FS-V1-U01QB04_Unit01TenItemSessionCompletionAndEvidenceExportAcceptance"
PRIVATE_ONLY = True

BLOCKED_LEARNER_KEYS = {
    "accepted_answers", "accepted_sequence", "accepted_texts", "answer_contract",
    "correct_answer", "private_item_json", "response_contract", "rubric",
}

HTML = """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'">
<meta name="referrer" content="no-referrer"><title>Unit 01 學習工作台</title><link rel="stylesheet" href="styles.css"></head>
<body><main><header><p>A1FS · PRIVATE UNIT01 SESSION</p><h1 id="title">載入中…</h1><p id="meta"></p></header>
<section id="notice" role="status"></section><nav><ol id="items"></ol></nav>
<article><p id="reason"></p><h2 id="prompt"></h2><p id="stimulus"></p><div id="response"></div>
<button id="submit" type="button">送出答案</button><p id="result" aria-live="polite"></p></article>
<footer><button id="previous" type="button">上一題</button><span id="position"></span><button id="next" type="button">下一題</button></footer>
</main><script src="app.js"></script></body></html>"""

CSS = """*{box-sizing:border-box}body{margin:0;background:#eef2f7;color:#17213a;font:16px/1.5 system-ui,-apple-system,'Noto Sans TC',sans-serif}main{width:min(900px,calc(100% - 2rem));margin:2rem auto;background:white;border-radius:22px;padding:2rem;box-shadow:0 18px 55px #17213a20}header p{color:#475467}nav ol{display:flex;gap:.5rem;overflow:auto;padding:0;list-style:none}nav button,footer button,#submit{border:0;border-radius:12px;padding:.65rem .9rem;background:#17213a;color:white;cursor:pointer}nav button[aria-current=true]{background:#4f46e5}article{min-height:330px;border:1px solid #d8deea;border-radius:18px;padding:1.5rem}#notice{padding:.8rem 1rem;background:#fffbeb;border-left:5px solid #f59e0b;border-radius:10px;margin:1rem 0}#stimulus{font-size:1.15rem}label{display:block;margin:.5rem 0}.text-response{width:100%;padding:.75rem;border:1px solid #98a2b3;border-radius:10px;font:inherit}footer{display:flex;justify-content:space-between;align-items:center;margin-top:1rem}button:disabled{opacity:.4;cursor:not-allowed}"""

JS = r"""'use strict';
const s={bundle:null,index:0,version:null,exposed:new Set()};const el=id=>document.getElementById(id);
async function api(path,payload){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const v=await r.json();if(!r.ok)throw new Error(v.error||'request failed');return v}
function control(item){const box=el('response');box.replaceChildren();if(item.response_mode==='select_one'){item.options.forEach(v=>{const label=document.createElement('label'),input=document.createElement('input');input.type='radio';input.name='response';input.value=v;label.append(input,document.createTextNode(' '+v));box.append(label)})}else{const input=document.createElement('input');input.id='text-response';input.className='text-response';input.autocomplete='off';input.placeholder=item.response_mode==='ordered_tokens'?'依正確順序輸入單字':'輸入答案';box.append(input)}}
function current(){return s.bundle.items[s.index]}
function response(){const item=current();if(item.response_mode==='select_one'){const checked=document.querySelector('input[name=response]:checked');return checked?checked.value:''}const value=el('text-response').value.trim();return item.response_mode==='ordered_tokens'?value.split(/\s+/).filter(Boolean):value}
async function expose(){const item=current();if(s.exposed.has(item.item_id)||!item.capture_enabled)return;const v=await api('/api/exposure',{item_id:item.item_id,expected_session_version:s.version});s.version=v.session_version;s.exposed.add(item.item_id)}
function draw(){const item=current();el('prompt').textContent=item.prompt;el('stimulus').textContent=item.stimulus||'';el('reason').textContent=`${item.selection_reason} · ${item.support_level}`;el('position').textContent=`${s.index+1} / ${s.bundle.items.length}`;el('previous').disabled=s.index===0;el('next').disabled=s.index===s.bundle.items.length-1;el('submit').disabled=!item.capture_enabled;el('result').textContent=item.capture_enabled?'':'口說練習卡：本版本不錄音、不評分。';control(item);[...document.querySelectorAll('#items button')].forEach((b,i)=>b.setAttribute('aria-current',String(i===s.index)));expose().catch(e=>el('result').textContent=`載入題目失敗：${e.message}`)}
async function boot(){const r=await fetch('/api/session',{cache:'no-store'});if(!r.ok)throw new Error('session unavailable');s.bundle=await r.json();s.version=s.bundle.session_version;el('title').textContent=s.bundle.lesson_id;el('meta').textContent=`${s.bundle.skill} · ${s.bundle.items.length} 題`;el('notice').textContent=s.bundle.boundary_notice;const nav=el('items');s.bundle.items.forEach((item,i)=>{const li=document.createElement('li'),b=document.createElement('button');b.type='button';b.textContent=String(i+1);b.onclick=()=>{s.index=i;draw()};li.append(b);nav.append(li)});draw()}
el('submit').onclick=async()=>{try{await expose();const item=current();const v=await api('/api/attempt',{item_id:item.item_id,response:response(),expected_session_version:s.version});s.version=v.session_version;el('result').textContent=v.outcome==='AUTO_PASS'?'答對了。':'答案已記錄，稍後會安排補救。'}catch(e){el('result').textContent=`送出失敗：${e.message}`}};
el('previous').onclick=()=>{if(s.index){s.index--;draw()}};el('next').onclick=()=>{if(s.index+1<s.bundle.items.length){s.index++;draw()}};boot().catch(e=>el('notice').textContent=`載入失敗：${e.message}`);
"""


class LearnerRendererError(ValueError):
    """Fail-closed U01QB03 renderer/controller error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def session_version(database: Path, session_id: str) -> int:
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT session_version FROM learning_sessions WHERE session_id=?", (session_id,)
        ).fetchone()
    if not row:
        raise LearnerRendererError("session_not_found")
    return int(row[0])


def response_mode(item: Mapping[str, Any]) -> str:
    if item.get("question_type") == "word_order":
        return "ordered_tokens"
    if item.get("options"):
        return "select_one"
    return "short_text"


def _assert_safe(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in BLOCKED_LEARNER_KEYS:
                raise LearnerRendererError(f"private_key_exposed:{key}")
            _assert_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_safe(child)


def build_bundle(*, database: Path, learner_id: str, session_id: str) -> dict[str, Any]:
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    plan = runtime.assemble_session(learner_id=learner_id, session_id=session_id)
    items = []
    for row in plan["items"]:
        item = dict(row)
        item["response_mode"] = response_mode(item)
        items.append(item)
    bundle = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "renderer_authority_task_id": m5.TASK_ID,
        "runtime_authority_task_id": qb02.TASK_ID,
        "learner_id": learner_id,
        "session_id": session_id,
        "session_version": session_version(database, session_id),
        "lesson_id": plan["lesson_id"],
        "skill": plan["skill"],
        "item_count": len(items),
        "items": items,
        "source_plan_digest": plan["plan_digest"],
        "source_bank_sha256": plan["source_bank_sha256"],
        "boundary_notice": "Private localhost learner workbench；Reading／Writing 可作答，Speaking 僅練習卡。",
        "capabilities": {
            "existing_m5_renderer_reused": True,
            "existing_m3_exposure_reused": True,
            "existing_m6_response_scoring_reused": True,
            "speaking_capture_enabled": False,
            "audio_enabled": False,
            "a2_unlocked": False,
            "mastery_claimed": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    if len(items) != qb02.SESSION_SIZE:
        raise LearnerRendererError(f"session_item_count_invalid:{len(items)}")
    _assert_safe(bundle)
    return bundle


def build_workbench(*, database: Path, learner_id: str, session_id: str, output_root: Path) -> dict[str, Any]:
    bundle = build_bundle(database=database, learner_id=learner_id, session_id=session_id)
    output_root = Path(output_root)
    atomic(output_root / "session.private.json", json.dumps(bundle, ensure_ascii=False, indent=2) + "\n")
    atomic(output_root / "index.html", HTML)
    atomic(output_root / "styles.css", CSS)
    atomic(output_root / "app.js", JS)
    files = {}
    for name in ("session.private.json", "index.html", "styles.css", "app.js"):
        raw = (output_root / name).read_bytes()
        files[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    manifest = {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "session_id": session_id,
        "lesson_id": bundle["lesson_id"],
        "skill": bundle["skill"],
        "item_count": bundle["item_count"],
        "files": files,
        "private_localhost_only": PRIVATE_ONLY,
        "parallel_renderer_created": False,
        "parallel_response_capture_created": False,
        "parallel_scoring_created": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
    atomic(output_root / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


class LearnerAttemptController:
    def __init__(self, database: Path, *, learner_id: str, session_id: str):
        self.database = Path(database)
        self.learner_id = learner_id
        self.session_id = session_id
        self.runtime = qb02.Unit01ApprovedVariantSessionRuntime(self.database)

    def expose(self, *, item_id: str, expected_session_version: int) -> dict[str, Any]:
        try:
            return self.runtime.record_item_exposure(
                session_id=self.session_id,
                item_id=item_id,
                expected_session_version=expected_session_version,
            )
        except qb02.SessionRuntimeError as exc:
            if str(exc) != "item_already_exposed_in_session":
                raise
            current = session_version(self.database, self.session_id)
            if current != expected_session_version:
                raise LearnerRendererError("session_version_conflict") from exc
            return {
                "validation_status": PASS_STATUS,
                "session_id": self.session_id,
                "item_id": item_id,
                "session_version": current,
                "m3_exposure_recorded": True,
                "existing_exposure_reused": True,
            }

    def submit(self, *, item_id: str, response: Any, expected_session_version: int) -> dict[str, Any]:
        exposed = self.expose(item_id=item_id, expected_session_version=expected_session_version)
        result = self.runtime.capture_response(
            learner_id=self.learner_id,
            session_id=self.session_id,
            item_id=item_id,
            response=response,
            expected_session_version=exposed["session_version"],
        )
        return {
            **result,
            "session_version": session_version(self.database, self.session_id),
            "m3_exposure_reused": True,
            "m6_response_scoring_reused": True,
            "parallel_renderer_created": False,
            "mastery_claimed": False,
            "a2_unlocked": False,
        }


class WorkbenchHandler(SimpleHTTPRequestHandler):
    controller: LearnerAttemptController
    bundle: dict[str, Any]

    def _json(self, status: int, payload: Mapping[str, Any]) -> None:
        raw = json.dumps(dict(payload), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/api/session":
            payload = dict(self.bundle)
            payload["session_version"] = session_version(
                self.controller.database, self.controller.session_id
            )
            self._json(200, payload)
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, Mapping):
                raise LearnerRendererError("request_body_not_object")
            if path == "/api/exposure":
                result = self.controller.expose(
                    item_id=str(payload.get("item_id") or ""),
                    expected_session_version=int(payload.get("expected_session_version")),
                )
            elif path == "/api/attempt":
                result = self.controller.submit(
                    item_id=str(payload.get("item_id") or ""),
                    response=payload.get("response"),
                    expected_session_version=int(payload.get("expected_session_version")),
                )
            else:
                self._json(404, {"error": "endpoint_not_found"})
                return
            self._json(200, result)
        except (ValueError, TypeError, json.JSONDecodeError, qb02.SessionRuntimeError) as exc:
            self._json(409, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve(*, database: Path, learner_id: str, session_id: str, output_root: Path, host: str, port: int) -> None:
    if host not in {"127.0.0.1", "localhost"}:
        raise LearnerRendererError("private_server_must_bind_loopback")
    bundle = build_bundle(database=database, learner_id=learner_id, session_id=session_id)

    class BoundWorkbenchHandler(WorkbenchHandler):
        pass

    BoundWorkbenchHandler.controller = LearnerAttemptController(
        database, learner_id=learner_id, session_id=session_id
    )
    BoundWorkbenchHandler.bundle = bundle
    handler = functools.partial(BoundWorkbenchHandler, directory=str(Path(output_root).resolve()))
    with ThreadingHTTPServer((host, port), handler) as server:
        server.serve_forever()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    serve_cmd = commands.add_parser("serve")
    for command in (build, serve_cmd):
        command.add_argument("--database", type=Path, required=True)
        command.add_argument("--learner-id", required=True)
        command.add_argument("--session-id", required=True)
        command.add_argument("--output-root", type=Path, required=True)
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8776)
    args = parser.parse_args(argv)
    if args.command == "build":
        result = build_workbench(
            database=args.database,
            learner_id=args.learner_id,
            session_id=args.session_id,
            output_root=args.output_root,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        serve(
            database=args.database,
            learner_id=args.learner_id,
            session_id=args.session_id,
            output_root=args.output_root,
            host=args.host,
            port=args.port,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
