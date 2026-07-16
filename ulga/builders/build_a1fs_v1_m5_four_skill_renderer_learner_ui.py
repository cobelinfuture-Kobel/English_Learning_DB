#!/usr/bin/env python3
"""Build the private localhost four-skill learner renderer.

Task: A1FS-V1-M5_FourSkillRendererAndLearnerUI
The output is a teacher-supervised private UI, not learner release.  Listening
audio/timed subtitles and speaking recording remain explicitly deferred to M10;
response capture and scoring remain deferred to M6.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-M5_FourSkillRendererAndLearnerUI"
SCHEMA_VERSION = "a1fs.v1.m5.four_skill_learner_ui.v1"
STATUS = "PASS_A1FS_V1_M5_FOUR_SKILL_RENDERER_LEARNER_UI_READY"
CONSUMER_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
PLANNER_STATUS = "PASS_A1FS_V1_M4_LESSON_PLANNER_AND_A2_LOCK_READY"
NEXT_SHORT_STEP = "A1FS-V1-M6_ResponseCaptureScoringAndM12Evidence"
ROLE_ORDER = {
    "LISTENING": ["CTX", "AUD", "VOC", "GRM", "MOD", "GDT", "XFR", "CHK", "EVD", "ERR"],
    "SPEAKING": ["CTX", "MOD", "NTC", "PRD", "CHK", "EVD"],
    "READING": ["CTX", "TXT", "VOC", "GRM", "MOD", "PRD", "CHK", "EVD", "ERR", "XFR"],
    "WRITING": ["CTX", "NTC", "PRD", "CHK", "EVD"],
}
ROLE_LABELS = {
    "CTX": "情境", "AUD": "聆聽", "TXT": "閱讀", "VOC": "字彙", "GRM": "文法",
    "MOD": "示範", "NTC": "觀察", "GDT": "引導", "PRD": "練習", "XFR": "遷移",
    "CHK": "檢查", "EVD": "學習證據", "ERR": "再試一次",
}
BLOCKED_KEY = re.compile(r"(?:answer|rationale|decisive_evidence|acceptance|critical_failure|diagnostic|provenance|automated|sha256|teacher_delivery|release_status)", re.I)


class RendererError(ValueError):
    """Fail-closed renderer error."""


def _canonical(value: Any) -> str: return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def _digest(value: bytes) -> str: return hashlib.sha256(value).hexdigest()


def _load(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    try: raw = path.read_bytes(); value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc: raise RendererError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict): raise RendererError(f"{code}_not_object")
    return value, raw


def _atomic(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(path.suffix + ".tmp")
    if isinstance(content, bytes): temporary.write_bytes(content)
    else: temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if BLOCKED_KEY.search(str(key)) or str(key) in {"transcript", "speaker_turns"}: continue
            cleaned = _sanitize(item)
            if cleaned not in (None, "", [], {}): result[str(key)] = cleaned
        return result
    if isinstance(value, list): return [item for item in (_sanitize(item) for item in value) if item not in (None, "", [], {})]
    if isinstance(value, (str, int, float, bool)) or value is None: return value
    return str(value)


def _find_questions(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).casefold() in {"question", "prompt", "launch_cue"} and isinstance(item, str): found.append(item)
            else: found.extend(_find_questions(item))
    elif isinstance(value, list):
        for item in value: found.extend(_find_questions(item))
    return list(dict.fromkeys(found))


def _learner_asset(asset: dict[str, Any]) -> dict[str, Any]:
    payload = asset["payload"]
    if asset["skill"] == "LISTENING" and asset["role"] == "AUD":
        safe = {"learner_instruction": "音訊與定時字幕尚未製作完成；此步驟不可用文字稿代替聽力證據。",
                "questions": _find_questions(payload), "audio_state": "AUDIO_DEFERRED_TO_M10"}
    else:
        safe = _sanitize(payload)
    if not safe: safe = {"learner_instruction": "請在教師指導下完成這個學習步驟。"}
    return {"asset_key": asset["asset_key"], "role": asset["role"], "role_label": ROLE_LABELS.get(asset["role"], asset["role"]),
            "content_digest": asset["content_digest"], "learner_payload": safe}


HTML = """<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:">
<meta name="referrer" content="no-referrer"><title>A1/A1+ 四技能學習工作台</title><link rel="stylesheet" href="styles.css"></head>
<body><a class="skip" href="#lesson-card">跳到課程內容</a><main class="shell">
<header><div><p class="eyebrow">A1FS · PRIVATE LEARNER WORKBENCH</p><h1 id="lesson-title">載入課程中…</h1><p id="lesson-meta"></p></div><span id="skill-badge" class="badge"></span></header>
<section class="notice" id="boundary-notice" role="status"></section>
<nav aria-label="課程步驟"><ol id="role-nav" class="role-nav"></ol></nav>
<section id="lesson-card" class="card" tabindex="-1" aria-live="polite"><h2 id="role-title"></h2><div id="payload"></div></section>
<section class="subtitle" aria-labelledby="subtitle-title"><div><h2 id="subtitle-title">SRT 字幕面板</h2><p id="subtitle-state"></p></div><div id="subtitle-cues"></div></section>
<footer><button id="previous" type="button">上一步</button><span id="position" aria-live="polite"></span><button id="next" type="button">下一步</button></footer>
</main><script src="app.js"></script></body></html>
"""

CSS = """:root{color-scheme:light;--ink:#17213a;--muted:#667085;--paper:#fffdf8;--line:#d8deea;--brand:#4f46e5;--accent:#f59e0b;--soft:#eef2ff}*{box-sizing:border-box}body{margin:0;background:linear-gradient(145deg,#eef2ff,#fff7ed 48%,#ecfeff);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Noto Sans TC",sans-serif}.skip{position:absolute;left:-999px}.skip:focus{left:1rem;top:1rem;background:white;padding:.6rem;z-index:9}.shell{width:min(980px,calc(100% - 2rem));margin:2rem auto;background:rgba(255,255,255,.92);border:1px solid #ffffff;border-radius:28px;box-shadow:0 24px 70px rgba(37,49,94,.14);padding:clamp(1rem,3vw,2.5rem)}header{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start}.eyebrow{letter-spacing:.12em;font-size:.75rem;font-weight:800;color:var(--brand);margin:0}h1{font-size:clamp(1.7rem,4vw,3rem);line-height:1.12;margin:.3rem 0}.badge{background:var(--ink);color:white;border-radius:999px;padding:.45rem .8rem;font-weight:800}.notice{margin:1.2rem 0;padding:.85rem 1rem;border-left:5px solid var(--accent);background:#fffbeb;border-radius:12px}.role-nav{display:flex;gap:.55rem;overflow:auto;padding:.3rem 0 1rem;list-style:none}.role-nav button{white-space:nowrap;border:1px solid var(--line);background:white;border-radius:999px;padding:.55rem .8rem;cursor:pointer}.role-nav button[aria-current=true]{background:var(--brand);color:white;border-color:var(--brand)}.card{min-height:320px;border:1px solid var(--line);border-radius:22px;padding:clamp(1rem,3vw,2rem);background:var(--paper)}.field{padding:.8rem 0;border-bottom:1px dashed var(--line)}.field:last-child{border:0}.field-label{display:block;color:var(--muted);font-size:.85rem;font-weight:750;text-transform:none}.field ul{margin:.35rem 0}.subtitle{display:flex;justify-content:space-between;gap:1rem;margin-top:1rem;padding:1rem;border-radius:18px;background:var(--soft)}.subtitle h2{font-size:1rem;margin:0}.subtitle p{margin:.2rem 0;color:var(--muted)}footer{display:flex;align-items:center;justify-content:space-between;margin-top:1rem}button{font:inherit}footer button{border:0;border-radius:14px;padding:.75rem 1rem;background:var(--ink);color:white;font-weight:750;cursor:pointer}footer button:disabled{opacity:.35;cursor:not-allowed}@media(max-width:620px){header,.subtitle{flex-direction:column}.shell{margin:.5rem auto;width:calc(100% - 1rem);border-radius:20px}.card{min-height:280px}}@media(prefers-reduced-motion:no-preference){.card{animation:rise .28s ease}@keyframes rise{from{transform:translateY(5px);opacity:.65}}}
"""

JS = r"""'use strict';
const state={bundle:null,index:0};
const el=id=>document.getElementById(id);
function label(key){return String(key).replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase())}
function renderValue(value){if(Array.isArray(value)){const ul=document.createElement('ul');value.forEach(v=>{const li=document.createElement('li');li.append(renderValue(v));ul.append(li)});return ul}if(value&&typeof value==='object'){const box=document.createElement('div');Object.entries(value).forEach(([k,v])=>box.append(renderField(k,v)));return box}const span=document.createElement('span');span.textContent=String(value??'');return span}
function renderField(key,value){const row=document.createElement('div');row.className='field';const name=document.createElement('span');name.className='field-label';name.textContent=label(key);row.append(name,renderValue(value));return row}
function draw(){const b=state.bundle,a=b.assets[state.index];el('role-title').textContent=`${a.role_label} · ${a.role}`;const payload=el('payload');payload.replaceChildren();Object.entries(a.learner_payload).forEach(([k,v])=>payload.append(renderField(k,v)));[...document.querySelectorAll('#role-nav button')].forEach((button,i)=>button.setAttribute('aria-current',String(i===state.index)));el('previous').disabled=state.index===0;el('next').disabled=state.index===b.assets.length-1;el('position').textContent=`${state.index+1} / ${b.assets.length}`;el('lesson-card').focus()}
async function boot(){const response=await fetch('lesson.private.json',{cache:'no-store'});if(!response.ok)throw new Error('lesson bundle unavailable');state.bundle=await response.json();const b=state.bundle;el('lesson-title').textContent=b.lesson.lesson_id;el('lesson-meta').textContent=`${b.lesson.level} · ${b.lesson.skill} · ${b.assets.length} 個步驟`;el('skill-badge').textContent=b.lesson.skill;el('boundary-notice').textContent=b.boundary_notice;el('subtitle-state').textContent=b.subtitle_contract.timing_status;const nav=el('role-nav');b.assets.forEach((a,i)=>{const li=document.createElement('li'),button=document.createElement('button');button.type='button';button.textContent=a.role_label;button.addEventListener('click',()=>{state.index=i;draw()});li.append(button);nav.append(li)});draw()}
el('previous').addEventListener('click',()=>{if(state.index>0){state.index--;draw()}});el('next').addEventListener('click',()=>{if(state.index+1<state.bundle.assets.length){state.index++;draw()}});document.addEventListener('keydown',event=>{if(event.key==='ArrowRight')el('next').click();if(event.key==='ArrowLeft')el('previous').click()});boot().catch(error=>{el('boundary-notice').textContent=`載入失敗：${error.message}`});
"""


def build_ui(*, consumer_path: Path, plan_path: Path, output_root: Path) -> dict[str, Any]:
    consumer, consumer_raw = _load(consumer_path, "consumer"); plan, plan_raw = _load(plan_path, "plan")
    if consumer.get("validation_status") != CONSUMER_STATUS: raise RendererError("consumer_status_invalid")
    if plan.get("validation_status") != PLANNER_STATUS: raise RendererError("plan_status_invalid")
    if plan.get("plan_status") not in {"PLAN_LEARNING_LESSON", "RESUME_ACTIVE_SESSION"}: raise RendererError("plan_not_renderable_learning_lesson")
    lesson = plan.get("selected_lesson") or {}; lesson_id = lesson.get("lesson_id")
    if lesson.get("level") not in {"A1", "A1+"}: raise RendererError("A2_RENDER_LOCKED")
    catalog = next((row for row in consumer["lesson_catalog"] if row["lesson_id"] == lesson_id), None)
    if not catalog or catalog["skill"] != lesson.get("skill") or catalog["level"] != lesson.get("level"): raise RendererError("plan_consumer_lesson_mismatch")
    assets = [_learner_asset(row) for row in consumer["asset_records"] if row["lesson_id"] == lesson_id]
    order = {role: index for index, role in enumerate(ROLE_ORDER[catalog["skill"]])}
    assets.sort(key=lambda row: (order.get(row["role"], 999), row["asset_key"]))
    if not assets or {row["asset_key"] for row in assets} != set(catalog["asset_keys"]): raise RendererError("lesson_asset_bundle_incomplete")
    subtitle = {"mode": "SRT_STYLE_PANEL", "timing_status": "AUDIO_DEFERRED_NO_TIMED_CUES" if catalog["skill"] == "LISTENING" else "UNTIMED_TEXT_CARDS",
                "timed_cues": [], "actual_srt_loaded": False, "audio_synchronized": False}
    bundle = {"task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": STATUS,
              "source_consumer_sha256": _digest(consumer_raw), "source_plan_sha256": _digest(plan_raw),
              "lesson": {key: catalog[key] for key in ("lesson_id", "lesson_node_id", "skill", "level", "roles", "requirement_node_ids")},
              "assets": assets, "subtitle_contract": subtitle,
              "boundary_notice": "Private teacher-supervised workbench；尚未核准 learner release。回應、評分與證據將於 M6 啟用。",
              "capabilities": {"role_navigation": True, "keyboard_navigation": True, "responsive_layout": True,
                               "response_capture_enabled": False, "scoring_enabled": False, "audio_playback_enabled": False,
                               "speaking_recording_enabled": False, "a2_content_included": False},
              "next_short_step": NEXT_SHORT_STEP}
    output_root.mkdir(parents=True, exist_ok=True)
    _atomic(output_root / "lesson.private.json", json.dumps(bundle, ensure_ascii=False, indent=2) + "\n")
    _atomic(output_root / "index.html", HTML); _atomic(output_root / "styles.css", CSS); _atomic(output_root / "app.js", JS)
    files = {}
    for name in ("lesson.private.json", "index.html", "styles.css", "app.js"):
        raw = (output_root / name).read_bytes(); files[name] = {"sha256": _digest(raw), "bytes": len(raw)}
    manifest = {"task_id": TASK_ID, "validation_status": STATUS, "lesson_id": lesson_id, "skill": catalog["skill"], "level": catalog["level"],
                "asset_count": len(assets), "files": files, "private_localhost_only": True, "learner_release_approved": False,
                "next_short_step": NEXT_SHORT_STEP}
    _atomic(output_root / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


class PrivateHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store"); self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer"); self.send_header("X-Frame-Options", "DENY"); super().end_headers()
    def log_message(self, format: str, *args: Any) -> None: return


def serve(output_root: Path, host: str, port: int) -> None:
    if host not in {"127.0.0.1", "localhost"}: raise RendererError("private_server_must_bind_loopback")
    if not (output_root / "manifest.json").is_file(): raise RendererError("workbench_not_built")
    handler = functools.partial(PrivateHandler, directory=str(output_root.resolve()))
    with ThreadingHTTPServer((host, port), handler) as server:
        print(f"Private A1FS learner UI: http://{host}:{port}/index.html", flush=True); server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build"); build.add_argument("--consumer", type=Path, required=True); build.add_argument("--plan", type=Path, required=True); build.add_argument("--output-root", type=Path, required=True)
    server = sub.add_parser("serve"); server.add_argument("--output-root", type=Path, required=True); server.add_argument("--host", default="127.0.0.1"); server.add_argument("--port", type=int, default=8775)
    args = parser.parse_args()
    if args.command == "build": result = build_ui(consumer_path=args.consumer, plan_path=args.plan, output_root=args.output_root); print(json.dumps(result, ensure_ascii=False, indent=2))
    else: serve(args.output_root, args.host, args.port)
    return 0


if __name__ == "__main__": raise SystemExit(main())
