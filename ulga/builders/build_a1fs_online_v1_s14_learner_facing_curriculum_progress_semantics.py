#!/usr/bin/env python3
"""Materialize learner-facing curriculum and progress semantics over S13.

S14 reuses the S13 authenticated localhost deployment, S09 24-unit runtime,
M3 learner state, and M6 response contracts. It adds bilingual learner-facing
unit labels, explicit session-versus-unit completion semantics, a structured
progress dashboard, Speaking practice-only labels, and an explicit Listening
(audio-deferred) boundary. It does not author curriculum/content/answers,
change scoring or mastery, enable audio, unlock A2, or enable Cloudflare.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s13_localhost_production_deployment as s13  # noqa: E402

s11 = s13.s11

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Adapts the existing S13/S09 runtime into learner-facing bilingual curriculum and progress semantics, "
    "including explicit session-completion, practice-only Speaking, and audio-deferred Listening labels. "
    "It creates no curriculum, learner content, answers, scoring, mastery, audio, A2 unlock, Cloudflare route, "
    "public deployment, or parallel state/runtime authority."
)

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S14_LearnerFacingCurriculumAndProgressSemantics_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s14.learner_facing_semantics.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S14_LEARNER_FACING_SEMANTICS_READY"
PRODUCT_STATUS = "LOCALHOST_NONAUDIO_LEARNER_FACING_SEMANTICS_READY_NOT_SCORED_COMPLETE"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S15_ReadingWritingScoredJourneyAndCompletionGate_NoAudio"
DEFAULT_PORT = 8765

CANARY_USERNAME = "s14-local-canary"
CANARY_PASSWORD = "S14-Local-Canary-Password-Only-For-ReadOnly-Acceptance-2026!"
CANARY_SESSION_SECRET = "S14-Local-Canary-Session-Signing-Secret-For-ReadOnly-Acceptance-2026!"

UNIT_LABEL_ROWS: tuple[tuple[str, str, str], ...] = (
    ("GRAMMAR_ARTICLES_BASIC", "冠詞：a、an、the", "Articles: a, an, and the"),
    ("GRAMMAR_REGULAR_PLURAL_NOUNS", "規則複數名詞", "Regular plural nouns"),
    ("GRAMMAR_SUBJECT_PRONOUNS", "主格代名詞", "Subject pronouns"),
    ("GRAMMAR_BASIC_PREPOSITIONS_PLACE", "地點介系詞", "Prepositions of place"),
    ("GRAMMAR_BE_VERB_BASIC", "be動詞基本句", "Basic be-verb statements"),
    ("GRAMMAR_CAN_STATEMENT", "can肯定句", "Can: affirmative statements"),
    ("GRAMMAR_DEMONSTRATIVES_CONTRAST", "this、that、these、those", "This, that, these, and those"),
    ("GRAMMAR_OBJECT_PRONOUNS_BASIC", "受格代名詞", "Object pronouns"),
    ("GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC", "所有格形容詞", "Possessive adjectives"),
    ("GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS", "現在簡單式肯定句", "Present simple statements"),
    ("GRAMMAR_ADJECTIVE_PHRASES_A1", "形容詞片語", "Adjective phrases"),
    ("GRAMMAR_ADVERB_PHRASES_A1", "副詞片語", "Adverb phrases"),
    ("GRAMMAR_BE_INTERROGATIVES_A1", "be動詞問句", "Be-verb questions"),
    ("GRAMMAR_CAN_NEGATIVE_A1", "can否定句", "Can: negative statements"),
    ("GRAMMAR_COORDINATION_A1", "and、but、or連接句", "Coordination with and, but, and or"),
    ("GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1", "基本陳述句型", "Basic declarative clause forms"),
    ("GRAMMAR_PAST_SIMPLE_A1", "過去簡單式", "Past simple"),
    ("GRAMMAR_PRESENT_SIMPLE_NEGATIVES", "現在簡單式否定句", "Present simple negatives"),
    ("GRAMMAR_THERE_IS", "There is與There are", "There is and there are"),
    ("GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1", "動詞補語句型", "Verb complement patterns"),
    ("GRAMMAR_WILL_FUTURE_A1", "will未來式", "Future with will"),
    ("GRAMMAR_BECAUSE_REASON_CLAUSES_A1", "because原因子句", "Reason clauses with because"),
    ("GRAMMAR_NOUN_PHRASES_A1", "名詞片語", "Noun phrases"),
    ("GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS", "現在簡單式Yes／No問句", "Present simple yes/no questions"),
)

UNIT_LABELS: dict[str, dict[str, Any]] = {
    grammar_id: {
        "sequence_index": index,
        "title_zh": title_zh,
        "title_en": title_en,
        "learner_label": f"{index:02d}. {title_zh}",
    }
    for index, (grammar_id, title_zh, title_en) in enumerate(UNIT_LABEL_ROWS, start=1)
}

SKILL_SEMANTICS: dict[str, dict[str, Any]] = {
    "READING": {
        "learner_label": "閱讀",
        "mode": "SCORED_TEXT_ACTIVITY",
        "response_capture_expected": True,
        "recording_enabled": False,
        "completion_scope": "SESSION_COMPLETION_ONLY_UNTIL_S15",
    },
    "WRITING": {
        "learner_label": "寫作",
        "mode": "SCORED_OR_HUMAN_REVIEW_TEXT_ACTIVITY",
        "response_capture_expected": True,
        "recording_enabled": False,
        "completion_scope": "SESSION_COMPLETION_ONLY_UNTIL_S15",
    },
    "SPEAKING": {
        "learner_label": "口說練習",
        "mode": "DISPLAY_AND_EXPOSURE_PRACTICE_ONLY",
        "response_capture_expected": False,
        "recording_enabled": False,
        "completion_scope": "PRACTICE_SESSION_ONLY_NO_SCORE_NO_MASTERY",
    },
}

FORBIDDEN_SAFE_KEYS = {
    "accepted_texts", "accepted_sequence", "answer", "answer_contract", "answer_key",
    "asset_key", "auth_password", "csrf", "database_path", "display_label", "learner_id",
    "learner_payload", "password", "private_scoring_contract", "private_subject_digest",
    "prompt", "prompt_text", "response", "rubric", "scoring_contract", "session_id",
    "session_secret", "subject_key", "token",
}


class LearnerFacingSemanticsError(ValueError):
    """Fail-closed S14 learner-surface or semantic contract error."""


def digest(value: Any) -> str:
    return s13.digest(value)


def file_digest(path: Path) -> str:
    return s13.file_digest(path)


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LearnerFacingSemanticsError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise LearnerFacingSemanticsError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    s13.write_json(Path(path), value, private=private)


def safe_scan(value: Any) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                    raise LearnerFacingSemanticsError(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def _verify_s13(
    receipt_path: Path,
) -> tuple[dict[str, Any], Path, Path, Path, dict[str, dict[str, Any]], dict[str, int]]:
    receipt_path = Path(receipt_path).resolve()
    receipt = read_json(receipt_path, "s13_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    if identity != (s13.TASK_ID, s13.SCHEMA_VERSION, s13.PASS_STATUS, s13.PRODUCT_STATUS, "NONE"):
        raise LearnerFacingSemanticsError("s13_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise LearnerFacingSemanticsError("s13_receipt_digest_invalid")
    acceptance = receipt.get("localhost_acceptance_summary", {})
    if (
        acceptance.get("unit_count") != 24
        or acceptance.get("lesson_count") != 72
        or acceptance.get("asset_count") != 264
        or acceptance.get("authentication_required") is not True
        or receipt.get("production_safety", {}).get("production_database_unchanged") is not True
    ):
        raise LearnerFacingSemanticsError("s13_acceptance_contract_invalid")
    _, source_s12, auth_state = s13._source_s12(receipt_path)
    _, database, bundle_index, _, bundles, sequence = s13._verify_s12(source_s12)
    if set(sequence) != set(UNIT_LABELS):
        missing = sorted(set(UNIT_LABELS) - set(sequence))
        extra = sorted(set(sequence) - set(UNIT_LABELS))
        raise LearnerFacingSemanticsError(f"runtime_unit_identity_mismatch:missing={missing}:extra={extra}")
    for grammar_id, expected in UNIT_LABELS.items():
        if sequence.get(grammar_id) != expected["sequence_index"]:
            raise LearnerFacingSemanticsError(f"runtime_unit_sequence_mismatch:{grammar_id}")
    return receipt, database, bundle_index, auth_state, bundles, sequence


def _decorate_bootstrap(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value))
    units = result.get("units")
    if not isinstance(units, list) or len(units) != 24:
        raise LearnerFacingSemanticsError("bootstrap_unit_denominator_invalid")
    lesson_count = 0
    asset_count = 0
    for unit in units:
        if not isinstance(unit, dict):
            raise LearnerFacingSemanticsError("bootstrap_unit_not_object")
        grammar_id = str(unit.get("grammar_unit_id") or "")
        label = UNIT_LABELS.get(grammar_id)
        if label is None:
            raise LearnerFacingSemanticsError(f"bootstrap_unit_label_missing:{grammar_id}")
        if unit.get("sequence_index") != label["sequence_index"]:
            raise LearnerFacingSemanticsError(f"bootstrap_sequence_drift:{grammar_id}")
        unit["internal_grammar_unit_id"] = grammar_id
        unit["learner_label"] = label["learner_label"]
        unit["learner_title_zh"] = label["title_zh"]
        unit["learner_title_en"] = label["title_en"]
        unit["primary_label_uses_internal_id"] = False
        lanes = unit.get("lanes")
        if not isinstance(lanes, list) or len(lanes) != 3:
            raise LearnerFacingSemanticsError(f"bootstrap_lane_denominator_invalid:{grammar_id}")
        for lane in lanes:
            skill = str(lane.get("skill") or "").upper()
            semantics = SKILL_SEMANTICS.get(skill)
            if semantics is None:
                raise LearnerFacingSemanticsError(f"bootstrap_skill_not_allowed:{skill}")
            lane["learner_label"] = semantics["learner_label"]
            lane["learner_mode"] = semantics["mode"]
            lane["response_capture_expected"] = semantics["response_capture_expected"]
            lane["recording_enabled"] = semantics["recording_enabled"]
            lane["completion_scope"] = semantics["completion_scope"]
            lesson_count += 1
            asset_count += int(lane.get("asset_count") or 0)
    if lesson_count != 72 or asset_count != 264:
        raise LearnerFacingSemanticsError(
            f"bootstrap_denominator_invalid:lessons={lesson_count}:assets={asset_count}"
        )
    result.update({
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "release_profile": RELEASE_PROFILE,
        "learner_product_semantics": {
            "unit_label_count": 24,
            "bilingual_unit_labels": True,
            "internal_ids_retained_as_secondary_metadata": True,
            "internal_ids_used_as_primary_labels": False,
            "session_completed_label": "本次學習已完成",
            "session_completed_code": "SESSION_COMPLETED",
            "session_completion_implies_lesson_completion": False,
            "session_completion_implies_unit_completion": False,
            "session_completion_implies_mastery": False,
            "raw_progress_default_visible": False,
        },
        "deferred_skills": [{
            "skill": "LISTENING",
            "learner_label": "聽力（音訊暫緩）",
            "status": "DEFERRED_POST_NOAUDIO_PRODUCT_LAUNCH",
            "audio_enabled": False,
            "lesson_count": 0,
        }],
    })
    return result


def _activity_status(session_count: int, active_count: int = 0) -> str:
    if active_count > 0:
        return "SESSION_IN_PROGRESS"
    if session_count > 0:
        return "SESSION_ACTIVITY_RECORDED"
    return "NOT_STARTED"


def _decorate_progress(raw: Mapping[str, Any]) -> dict[str, Any]:
    summary = dict(raw.get("summary") or {})
    raw_skills = raw.get("skills") if isinstance(raw.get("skills"), Mapping) else {}
    raw_units = raw.get("units") if isinstance(raw.get("units"), Mapping) else {}
    sessions = int(summary.get("session_count") or 0)
    active_sessions = int(summary.get("active_session_count") or 0)
    learner_units: list[dict[str, Any]] = []
    for grammar_id, label in sorted(UNIT_LABELS.items(), key=lambda row: row[1]["sequence_index"]):
        source = raw_units.get(grammar_id) if isinstance(raw_units, Mapping) else None
        source = dict(source) if isinstance(source, Mapping) else {}
        unit_sessions = int(source.get("session_count") or 0)
        learner_units.append({
            "internal_grammar_unit_id": grammar_id,
            "sequence_index": label["sequence_index"],
            "learner_label": label["learner_label"],
            "learner_title_zh": label["title_zh"],
            "learner_title_en": label["title_en"],
            "activity_status": _activity_status(unit_sessions),
            "session_count": unit_sessions,
            "session_completed_count": int(source.get("completed_session_count") or 0),
            "session_abandoned_count": int(source.get("abandoned_session_count") or 0),
            "unit_completed": False,
            "mastery_claimed": False,
        })
    learner_skills: list[dict[str, Any]] = []
    for skill in ("READING", "WRITING", "SPEAKING"):
        semantics = SKILL_SEMANTICS[skill]
        source = raw_skills.get(skill) if isinstance(raw_skills, Mapping) else None
        source = dict(source) if isinstance(source, Mapping) else {}
        skill_sessions = int(source.get("session_count") or 0)
        learner_skills.append({
            "skill": skill,
            "learner_label": semantics["learner_label"],
            "mode": semantics["mode"],
            "activity_status": _activity_status(skill_sessions),
            "session_count": skill_sessions,
            "session_completed_count": int(source.get("completed_session_count") or 0),
            "attempt_count": int(source.get("attempt_count") or 0),
            "auto_pass_count": int(source.get("auto_pass_count") or 0),
            "auto_fail_count": int(source.get("auto_fail_count") or 0),
            "recording_enabled": False,
            "mastery_claimed": False,
        })
    learner_skills.append({
        "skill": "LISTENING",
        "learner_label": "聽力（音訊暫緩）",
        "mode": "DEFERRED_AUDIO_REQUIRED",
        "activity_status": "DEFERRED",
        "session_count": 0,
        "session_completed_count": 0,
        "attempt_count": 0,
        "auto_pass_count": 0,
        "auto_fail_count": 0,
        "recording_enabled": False,
        "mastery_claimed": False,
    })
    return {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "summary": {
            "profile_active": bool(summary.get("profile_active")),
            "course_activity_status": _activity_status(sessions, active_sessions),
            "session_count": sessions,
            "session_completed_count": int(summary.get("completed_session_count") or 0),
            "session_active_count": active_sessions,
            "session_abandoned_count": int(summary.get("abandoned_session_count") or 0),
            "exposure_count": int(summary.get("exposure_count") or 0),
            "attempt_count": int(summary.get("attempt_count") or 0),
            "auto_pass_count": int(summary.get("auto_pass_count") or 0),
            "auto_fail_count": int(summary.get("auto_fail_count") or 0),
            "pending_human_review_count": int(summary.get("pending_human_review_count") or 0),
            "unit_count_with_session_activity": int(summary.get("unit_count_with_sessions") or 0),
            "skill_count_with_session_activity": int(summary.get("skill_count_with_sessions") or 0),
            "unit_completed_count": 0,
            "mastered_unit_count": 0,
        },
        "semantic_boundaries": {
            "session_completed_means": "ONE_SESSION_ENDED_SUCCESSFULLY",
            "session_completed_implies_lesson_completed": False,
            "session_completed_implies_unit_completed": False,
            "session_completed_implies_mastery": False,
            "exposure_implies_attempt": False,
            "exposure_implies_mastery": False,
            "speaking_is_practice_only": True,
            "listening_is_audio_deferred": True,
        },
        "skills": learner_skills,
        "units": learner_units,
        "operator_debug": deepcopy(dict(raw)),
    }


class LearnerFacingApplication(s13.s11.s10.s09.PopulationWorkbenchApplication):
    """S09 runtime with S14 learner-facing metadata and progress semantics."""

    def bootstrap(self) -> dict[str, Any]:
        return _decorate_bootstrap(super().bootstrap())

    def progress_readback(self) -> dict[str, Any]:
        return _decorate_progress(super().progress_readback())


def _app(
    database: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
) -> LearnerFacingApplication:
    return LearnerFacingApplication(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence,
        default_learner_id=s13.s11.s10.s09.s05.DEFAULT_LEARNER_ID,
    )


def _write_learner_static(target_root: Path) -> None:
    target_root = Path(target_root)
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True, exist_ok=True)
    index = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'">
  <title>A1FS A1／A1+ 學習工作台</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <main>
    <header class="hero">
      <div><p class="eyebrow">A1／A1+ 無音訊學習產品</p><h1>A1FS 學習工作台</h1></div>
      <p id="status" class="status" aria-live="polite">正在載入</p>
    </header>
    <section class="boundary" aria-label="目前技能範圍">
      <strong>目前可用：</strong>閱讀、寫作、口說練習
      <span>聽力需使用音訊，暫緩至後續版本。</span>
    </section>
    <section id="active-panel" class="panel" hidden>
      <h2>尚未結束的本次學習</h2><p id="active-label"></p>
      <button id="resume">繼續本次學習</button><button id="abandon" class="secondary">放棄本次學習</button>
    </section>
    <section class="panel"><h2>選擇學習單元</h2><nav id="units" class="unit-grid" aria-label="學習單元"></nav></section>
    <section class="panel"><h2>選擇技能</h2><nav id="lanes" class="lane-grid" aria-label="技能"></nav><p id="lane-note" class="note"></p></section>
    <section id="items" class="items"></section>
    <button id="complete" class="primary" hidden>完成本次學習</button>
    <section class="panel progress-panel">
      <div class="section-heading"><h2>學習活動紀錄</h2><button id="refresh-progress" class="secondary">更新</button></div>
      <p class="note">「本次學習已完成」只代表一個session結束，不代表整個單元完成或已精熟。</p>
      <div id="progress-summary" class="summary-grid"></div>
      <h3>技能活動</h3><div id="progress-skills" class="progress-grid"></div>
      <h3>單元活動</h3><div id="progress-units" class="progress-grid"></div>
      <details><summary>Operator debug readback</summary><pre id="progress-debug"></pre></details>
    </section>
  </main>
  <script src="/app.js"></script>
</body>
</html>"""
    css = """*{box-sizing:border-box}body{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#f3f5f7;color:#18212b}main{max-width:1120px;margin:auto;padding:24px}.hero{display:flex;justify-content:space-between;gap:24px;align-items:flex-start}.eyebrow{margin:0;font-weight:700;color:#40556b}.hero h1{margin:.25rem 0 1rem}.status{padding:10px 14px;background:#fff;border:1px solid #cbd4dc;border-radius:999px}.boundary,.panel,.card{background:#fff;border:1px solid #d7dee5;border-radius:12px;padding:18px;margin:14px 0}.boundary{display:flex;gap:12px;flex-wrap:wrap}.unit-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}.lane-grid{display:flex;flex-wrap:wrap;gap:10px}button,input,textarea{font:inherit}button{padding:10px 14px;border:1px solid #8b99a7;border-radius:8px;background:#fff;cursor:pointer}button:hover{border-color:#263746}.unit{min-height:78px;text-align:left}.unit strong,.unit small{display:block}.unit small{margin-top:4px;color:#5a6875}.selected{border:2px solid #263746;font-weight:700}.primary{margin:6px 0 18px;background:#243746;color:#fff}.secondary{background:#f7f8f9}.items{display:grid;gap:12px}.card .prompt{font-size:1.05rem}.options{display:grid;gap:8px}.options label{padding:8px;border:1px solid #d7dee5;border-radius:8px}textarea{width:100%;min-height:110px;padding:10px}.result{font-weight:700}.note{color:#53616e}.section-heading{display:flex;justify-content:space-between;align-items:center}.summary-grid,.progress-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}.metric,.progress-card{border:1px solid #d7dee5;border-radius:10px;padding:12px}.metric strong{display:block;font-size:1.35rem}.badge{display:inline-block;padding:3px 8px;border-radius:999px;background:#edf1f4;font-size:.86rem}details{margin-top:18px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#111820;color:#ecf2f7;padding:14px;border-radius:8px}button:disabled{opacity:.5;cursor:not-allowed}#abandon{border-color:#9a2b2b}@media(max-width:640px){main{padding:14px}.hero{display:block}.status{display:inline-block}.unit-grid{grid-template-columns:1fr}}"""
    js = r"""'use strict';
let state=null,currentUnit=null,currentLane=null,active=null,pendingResume=null;
const status=document.querySelector('#status'),units=document.querySelector('#units'),lanes=document.querySelector('#lanes'),items=document.querySelector('#items'),complete=document.querySelector('#complete'),refresh=document.querySelector('#refresh-progress'),activePanel=document.querySelector('#active-panel'),activeLabel=document.querySelector('#active-label'),resume=document.querySelector('#resume'),abandon=document.querySelector('#abandon'),laneNote=document.querySelector('#lane-note'),progressSummary=document.querySelector('#progress-summary'),progressSkills=document.querySelector('#progress-skills'),progressUnits=document.querySelector('#progress-units'),progressDebug=document.querySelector('#progress-debug');
const text=(node,value)=>{node.textContent=value??''};const locked=()=>Boolean(active||pendingResume);
const sessionStateLabel=value=>({ACTIVE:'本次學習進行中',COMPLETED:'本次學習已完成（SESSION_COMPLETED）',ABANDONED:'本次學習已放棄'}[value]||value||'');
const activityLabel=value=>({NOT_STARTED:'尚未開始',SESSION_IN_PROGRESS:'本次學習進行中',SESSION_ACTIVITY_RECORDED:'已有學習活動',DEFERRED:'暫緩'}[value]||value||'');
const outcomeLabel=value=>({AUTO_PASS:'作答正確',AUTO_FAIL:'需要再練習',PENDING_HUMAN_REVIEW:'等待人工審核',RECORDED:'練習已記錄'}[value]||value||'');
async function api(path,body){const hasBody=body!==undefined;const response=await fetch(path,{method:hasBody?'POST':'GET',headers:hasBody?{'Content-Type':'application/json'}:{},body:hasBody?JSON.stringify(body):undefined});const value=await response.json();if(!response.ok)throw new Error(value.error||'request_failed');return value}
function metric(label,value){const node=document.createElement('div');node.className='metric';const strong=document.createElement('strong');text(strong,value);const span=document.createElement('span');text(span,label);node.append(strong,span);return node}
function progressCard(title,statusValue,lines=[]){const node=document.createElement('article');node.className='progress-card';const heading=document.createElement('h4');text(heading,title);const badge=document.createElement('span');badge.className='badge';text(badge,activityLabel(statusValue));node.append(heading,badge);for(const line of lines){const paragraph=document.createElement('p');text(paragraph,line);node.append(paragraph)}return node}
async function loadProgress(){const value=await api('/api/progress');progressSummary.replaceChildren(metric('本次學習總數',value.summary.session_count),metric('已結束的本次學習',value.summary.session_completed_count),metric('作答次數',value.summary.attempt_count),metric('需要人工審核',value.summary.pending_human_review_count));progressSkills.replaceChildren();for(const skill of value.skills){progressSkills.append(progressCard(skill.learner_label,skill.activity_status,[`本次學習：${skill.session_count}`,`作答：${skill.attempt_count}`]))}progressUnits.replaceChildren();for(const unit of value.units){progressUnits.append(progressCard(unit.learner_label,unit.activity_status,[unit.learner_title_en,`本次學習：${unit.session_count}`]))}text(progressDebug,JSON.stringify(value.operator_debug,null,2))}
function findLane(lessonId){for(const unit of state.units)for(const lane of unit.lanes)if(lane.lesson_id===lessonId)return{unit,lane};return null}
function updateActivePanel(){activePanel.hidden=!pendingResume;text(activeLabel,pendingResume?`${pendingResume.learner_label||pendingResume.grammar_unit_id}／${pendingResume.session.skill}`:'')}
function renderUnits(){units.replaceChildren();for(const unit of state.units){const button=document.createElement('button');button.className='unit';button.dataset.internalId=unit.internal_grammar_unit_id;button.classList.toggle('selected',Boolean(currentUnit&&currentUnit.internal_grammar_unit_id===unit.internal_grammar_unit_id));button.disabled=locked();const strong=document.createElement('strong');text(strong,unit.learner_label);const small=document.createElement('small');text(small,unit.learner_title_en);button.append(strong,small);button.addEventListener('click',()=>{try{chooseUnit(unit)}catch(error){text(status,error.message)}});units.append(button)}}
function renderLanes(){lanes.replaceChildren();text(laneNote,'');if(!currentUnit)return;for(const lane of currentUnit.lanes){const button=document.createElement('button');button.className='lane';button.classList.toggle('selected',Boolean(currentLane&&currentLane.lesson_id===lane.lesson_id));button.disabled=locked();text(button,lane.learner_label);button.addEventListener('click',()=>begin(lane).catch(error=>text(status,error.message)));lanes.append(button)}}
function chooseUnit(unit){if(locked())throw new Error('請先繼續或放棄目前的本次學習');currentUnit=unit;currentLane=null;items.replaceChildren();renderUnits();renderLanes();text(status,`已選擇：${unit.learner_label}`)}
function responseFor(card,asset){const options=asset.learner_payload.options||[];if(options.length){const checked=card.querySelector('input[type=radio]:checked');if(!checked)throw new Error('請先選擇答案');return checked.value}const area=card.querySelector('textarea');if(!area||!area.value.trim())throw new Error('請先輸入答案');return area.value}
async function expose(asset){const result=await api('/api/exposure',{session_id:active.session_id,asset_key:asset.asset_key,expected_session_version:active.session_version});active.session_version=result.session_version;return result}
function renderLane(lane){currentLane=lane;renderUnits();renderLanes();items.replaceChildren();text(laneNote,lane.skill==='SPEAKING'?'口說目前是練習模式：不錄音、不評分，也不代表精熟。':'完成本次學習只代表session結束；評分與單元完成規則將於S15接通。');for(const asset of lane.assets){const card=document.createElement('article');card.className='card';const prompt=document.createElement('p');prompt.className='prompt';text(prompt,asset.learner_payload.prompt);card.append(prompt);const options=asset.learner_payload.options||[];if(options.length){const box=document.createElement('div');box.className='options';for(const option of options){const label=document.createElement('label'),input=document.createElement('input');input.type='radio';input.name=asset.asset_key;input.value=option;label.append(input,document.createTextNode(' '+option));box.append(label)}card.append(box)}else if(asset.learner_payload.response_capture_enabled){const area=document.createElement('textarea');area.setAttribute('aria-label','回答');card.append(area)}const button=document.createElement('button'),result=document.createElement('p');button.className='submit';result.className='result';if(asset.learner_payload.response_capture_enabled){text(button,'送出回答');button.addEventListener('click',async()=>{try{button.disabled=true;await expose(asset);const scored=await api('/api/response',{session_id:active.session_id,asset_key:asset.asset_key,response:responseFor(card,asset),expected_session_version:active.session_version});active.session_version=scored.session_version;text(result,outcomeLabel(scored.outcome));await loadProgress()}catch(error){text(status,error.message)}finally{button.disabled=false}})}else{text(button,'完成這張口說練習');button.addEventListener('click',async()=>{try{button.disabled=true;await expose(asset);text(result,'練習已記錄');await loadProgress()}catch(error){text(status,error.message)}finally{button.disabled=false}})}card.append(button,result);items.append(card)}}
async function begin(lane){if(locked())throw new Error('請先繼續或放棄目前的本次學習');active=await api('/api/session/start',{lesson_id:lane.lesson_id});pendingResume=null;updateActivePanel();complete.hidden=false;renderLane(lane);text(status,`本次學習開始：${currentUnit.learner_label}／${lane.learner_label}`)}
function restore(snapshot){const match=findLane(snapshot.session.lesson_id);if(!match)throw new Error('active_session_bundle_missing');pendingResume=null;active=snapshot.session;currentUnit=match.unit;currentLane=match.lane;updateActivePanel();complete.hidden=false;renderLane(match.lane);text(status,`繼續本次學習：${match.unit.learner_label}／${match.lane.learner_label}`)}
async function finish(path){if(!active)return;const done=await api(path,{session_id:active.session_id,expected_session_version:active.session_version});text(status,sessionStateLabel(done.session_state));active=null;pendingResume=null;currentLane=null;updateActivePanel();complete.hidden=true;items.replaceChildren();renderUnits();renderLanes();await loadProgress()}
complete.addEventListener('click',()=>finish('/api/session/complete').catch(error=>text(status,error.message)));abandon.addEventListener('click',async()=>{try{if(!pendingResume&&!active)return;if(!active)active=pendingResume.session;await finish('/api/session/abandon')}catch(error){text(status,error.message)}});resume.addEventListener('click',()=>{try{if(pendingResume)restore(pendingResume)}catch(error){text(status,error.message)}});refresh.addEventListener('click',()=>loadProgress().catch(error=>text(status,error.message)));
async function start(){state=await api('/api/bootstrap');text(status,'已登入；請選擇一個學習單元');const snapshot=await api('/api/session/active');if(snapshot.active){const match=findLane(snapshot.session.lesson_id);if(!match)throw new Error('active_session_bundle_missing');pendingResume={...snapshot,learner_label:match.unit.learner_label};currentUnit=match.unit;currentLane=match.lane;updateActivePanel();renderUnits();renderLanes()}else if(state.units.length)chooseUnit(state.units[0]);else{renderUnits();renderLanes()}await loadProgress()}
start().catch(error=>text(status,error.message));
"""
    (target_root / "index.html").write_text(index + "\n", encoding="utf-8")
    (target_root / "styles.css").write_text(css + "\n", encoding="utf-8")
    (target_root / "app.js").write_text(js + "\n", encoding="utf-8")


def _write_launch_bundle(
    *,
    target_root: Path,
    receipt_path: Path,
    auth_state_db: Path,
) -> dict[str, Any]:
    target_root = Path(target_root).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    pid_file = target_root / "a1fs_s14_localhost.pid"
    stdout_log = target_root / "a1fs_s14_localhost.stdout.log"
    stderr_log = target_root / "a1fs_s14_localhost.stderr.log"
    start_script = f'''param([string]$CodeRoot = "G:\\HomeWork\\English_Learning_DB_Main",[int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Receipt = "{str(receipt_path).replace(chr(34), chr(34)+chr(34))}"
$PidFile = "{str(pid_file).replace(chr(34), chr(34)+chr(34))}"
$Stdout = "{str(stdout_log).replace(chr(34), chr(34)+chr(34))}"
$Stderr = "{str(stderr_log).replace(chr(34), chr(34)+chr(34))}"
foreach ($Name in @("A1FS_S11_AUTH_USERNAME","A1FS_S11_AUTH_PASSWORD","A1FS_S11_SESSION_SECRET")) {{ if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name))) {{ throw "MISSING_ENV=$Name" }} }}
$env:A1FS_S11_MODE = "local"
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {{ throw "PORT_IN_USE=$Port" }}
if (Test-Path -LiteralPath $PidFile) {{ throw "PID_FILE_ALREADY_EXISTS=$PidFile" }}
Set-Location $CodeRoot
$Python = (Get-Command python).Source
$Process = Start-Process -FilePath $Python -WorkingDirectory $CodeRoot -ArgumentList @("-m","ulga.builders.build_a1fs_online_v1_s14_learner_facing_curriculum_progress_semantics","serve","--receipt",$Receipt,"--host","127.0.0.1","--port",[string]$Port) -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr -PassThru
[System.IO.File]::WriteAllText($PidFile,[string]$Process.Id)
for ($Attempt=1; $Attempt -le 40; $Attempt++) {{ if ($Process.HasExited) {{ throw "A1FS_S14_PROCESS_EXITED=$($Process.ExitCode)" }}; try {{ $Health=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2; if ($Health.status -eq "PASS" -and $Health.authentication_required -eq $true) {{ Write-Host "A1FS_S14_LOCALHOST_STARTED=PASS"; Write-Host "PID=$($Process.Id)"; Write-Host "URL=http://127.0.0.1:$Port"; exit 0 }} }} catch {{ Start-Sleep -Milliseconds 500 }} }}
Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
throw "A1FS_S14_LOCALHOST_READINESS_TIMEOUT"
'''
    stop_script = f'''param([int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PidFile = "{str(pid_file).replace(chr(34), chr(34)+chr(34))}"
if (-not (Test-Path -LiteralPath $PidFile)) {{ throw "PID_FILE_MISSING=$PidFile" }}
$PidValue=[int](Get-Content -LiteralPath $PidFile -Raw)
$Process=Get-Process -Id $PidValue -ErrorAction SilentlyContinue
if ($null -eq $Process) {{ Remove-Item -LiteralPath $PidFile -Force; throw "STALE_PID_FILE=$PidValue" }}
$Command=(Get-CimInstance Win32_Process -Filter "ProcessId=$PidValue").CommandLine
if ($Command -notlike "*build_a1fs_online_v1_s14_learner_facing_curriculum_progress_semantics*") {{ throw "PID_OWNERSHIP_MISMATCH=$PidValue" }}
Stop-Process -Id $PidValue -Force
for ($Attempt=1; $Attempt -le 20; $Attempt++) {{ if (-not (Get-Process -Id $PidValue -ErrorAction SilentlyContinue)) {{ break }}; Start-Sleep -Milliseconds 250 }}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {{ throw "PORT_STILL_LISTENING=$Port" }}
Remove-Item -LiteralPath $PidFile -Force
Write-Host "A1FS_S14_LOCALHOST_STOPPED=PASS"
'''
    status_script = f'''param([int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PidFile = "{str(pid_file).replace(chr(34), chr(34)+chr(34))}"
if (-not (Test-Path -LiteralPath $PidFile)) {{ throw "A1FS_S14_LOCALHOST_STATUS=STOPPED" }}
$PidValue=[int](Get-Content -LiteralPath $PidFile -Raw)
if (-not (Get-Process -Id $PidValue -ErrorAction SilentlyContinue)) {{ throw "A1FS_S14_LOCALHOST_STATUS=STALE_PID" }}
$Listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($null -eq $Listener -or $Listener.OwningProcess -ne $PidValue) {{ throw "A1FS_S14_LOCALHOST_STATUS=PORT_OWNERSHIP_INVALID" }}
$Health=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
if ($Health.status -ne "PASS" -or $Health.authentication_required -ne $true) {{ throw "A1FS_S14_LOCALHOST_STATUS=UNHEALTHY" }}
Write-Host "A1FS_S14_LOCALHOST_STATUS=RUNNING"
Write-Host "PID=$PidValue"
Write-Host "URL=http://127.0.0.1:$Port"
'''
    files = {
        "start_a1fs_s14_localhost.ps1": start_script,
        "stop_a1fs_s14_localhost.ps1": stop_script,
        "status_a1fs_s14_localhost.ps1": status_script,
    }
    for name, content in files.items():
        (target_root / name).write_text(content, encoding="utf-8")
    contract = {
        "schema_version": "a1fs.online.v1.s14.localhost_launch_contract.v1",
        "host": "127.0.0.1",
        "port": DEFAULT_PORT,
        "authentication_required": True,
        "required_environment_variables": [
            "A1FS_S11_AUTH_USERNAME", "A1FS_S11_AUTH_PASSWORD", "A1FS_S11_SESSION_SECRET"
        ],
        "secret_values_embedded": False,
        "auth_state_database_reused_from_s13": str(auth_state_db),
        "external_network_binding_allowed": False,
        "cloudflare_enabled": False,
        "audio_enabled": False,
    }
    write_json(target_root / "localhost_launch_contract.json", contract)
    return {
        "bundle_root": str(target_root),
        "start_script_path": str(target_root / "start_a1fs_s14_localhost.ps1"),
        "stop_script_path": str(target_root / "stop_a1fs_s14_localhost.ps1"),
        "status_script_path": str(target_root / "status_a1fs_s14_localhost.ps1"),
        "launch_contract_path": str(target_root / "localhost_launch_contract.json"),
        "pid_file_path": str(pid_file),
        "stdout_log_path": str(stdout_log),
        "stderr_log_path": str(stderr_log),
        "auth_state_database_path": str(auth_state_db),
    }


def _run_acceptance(
    *,
    production_database: Path,
    secure_static_root: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
    auth_state_db: Path,
) -> dict[str, Any]:
    production_sha_before = file_digest(production_database)
    config = s13.PersistentBoundaryConfig.from_values(
        username=CANARY_USERNAME,
        password=CANARY_PASSWORD,
        session_secret=CANARY_SESSION_SECRET,
        mode="local",
        allowed_origin="http://127.0.0.1",
        allowed_host="127.0.0.1",
        revocation_db_path=auth_state_db,
        port=0,
    )
    server, thread, port = s13._start_server(
        app=_app(production_database, bundles, sequence),
        secure_static_root=secure_static_root,
        config=config,
    )
    origin = f"http://127.0.0.1:{port}"
    try:
        s11._request(port, "GET", "/api/bootstrap", expected_status=401)
        login, headers = s11._request(
            port,
            "POST",
            "/auth/login",
            {"username": CANARY_USERNAME, "password": CANARY_PASSWORD},
            origin=origin,
        )
        cookie = str(headers.get("Set-Cookie") or "").split(";", 1)[0]
        if not cookie or not login.get("csrf_token"):
            raise LearnerFacingSemanticsError("s14_login_contract_invalid")
        bootstrap, _ = s11._request(port, "GET", "/api/bootstrap", cookie=cookie)
        progress, _ = s11._request(port, "GET", "/api/progress", cookie=cookie)
        if bootstrap.get("task_id") != TASK_ID or progress.get("task_id") != TASK_ID:
            raise LearnerFacingSemanticsError("s14_http_identity_invalid")
        if len(bootstrap.get("units", [])) != 24 or len(progress.get("units", [])) != 24:
            raise LearnerFacingSemanticsError("s14_http_unit_denominator_invalid")
        if bootstrap.get("learner_product_semantics", {}).get("internal_ids_used_as_primary_labels") is not False:
            raise LearnerFacingSemanticsError("s14_primary_label_boundary_invalid")
        boundaries = progress.get("semantic_boundaries", {})
        if (
            boundaries.get("session_completed_implies_unit_completed") is not False
            or boundaries.get("session_completed_implies_mastery") is not False
            or boundaries.get("speaking_is_practice_only") is not True
            or boundaries.get("listening_is_audio_deferred") is not True
        ):
            raise LearnerFacingSemanticsError("s14_progress_semantics_invalid")
    finally:
        s13._stop_server(server, thread)
    production_sha_after = file_digest(production_database)
    if production_sha_before != production_sha_after:
        raise LearnerFacingSemanticsError("production_database_mutated_by_s14_acceptance")
    return {
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "bilingual_unit_label_count": 24,
        "learner_primary_internal_id_count": 0,
        "skill_semantics_count": 4,
        "session_completed_relabelled": True,
        "session_unit_mastery_semantics_separated": True,
        "structured_progress_dashboard": True,
        "raw_progress_default_visible": False,
        "operator_debug_collapsed": True,
        "speaking_practice_only_labelled": True,
        "speaking_recording_enabled": False,
        "listening_audio_deferred_labelled": True,
        "listening_lesson_count": 0,
        "audio_asset_count": 0,
        "authenticated_http_acceptance": True,
        "production_database_unchanged": True,
    }


def materialize(*, s13_receipt_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    s13_receipt, production_database, bundle_index, auth_state_db, bundles, sequence = _verify_s13(s13_receipt_path)
    output_root = Path(output_root).resolve()
    root = output_root / "learner_facing_semantics"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    learner_static = root / "learner_static"
    secure_static = root / "secure_static"
    _write_learner_static(learner_static)
    s11._write_secure_static(learner_static, secure_static)
    acceptance_auth_state = root / "runtime" / "s14_acceptance_auth.sqlite3"
    acceptance = _run_acceptance(
        production_database=production_database,
        secure_static_root=secure_static,
        bundles=bundles,
        sequence=sequence,
        auth_state_db=acceptance_auth_state,
    )
    launch_bundle = _write_launch_bundle(
        target_root=root / "launch_bundle",
        receipt_path=output_root / "learner_facing_semantics.private.json",
        auth_state_db=auth_state_db,
    )
    production_sha = file_digest(production_database)
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "s13_sha256": digest(s13_receipt),
            "production_database_sha256": production_sha,
            "unit_label_map_sha256": digest(UNIT_LABELS),
        },
        "runtime_outputs": {
            "root": str(root),
            "source_s13_receipt_path": str(Path(s13_receipt_path).resolve()),
            "source_database_path": str(production_database),
            "source_bundle_index_path": str(bundle_index),
            "learner_static_root": str(learner_static),
            "secure_static_root": str(secure_static),
            **launch_bundle,
        },
        "learner_semantics_summary": acceptance,
        "production_safety": {
            "production_database_sha256_before": production_sha,
            "production_database_sha256_after": file_digest(production_database),
            "production_database_unchanged": True,
            "learner_progress_mutated_by_acceptance": False,
            "auth_state_reused_from_s13": True,
        },
        "capability_contract": {
            "s13_authenticated_localhost_reused": True,
            "s09_twentyfour_unit_runtime_reused": True,
            "m3_session_progress_authority_reused": True,
            "m6_response_scoring_authority_reused": True,
            "parallel_curriculum_created": False,
            "parallel_learner_state_engine_created": False,
            "parallel_scoring_engine_created": False,
            "unit_completion_claim_enabled": False,
            "mastery_write_enabled": False,
            "speaking_capture_enabled": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "a2_unlocked": False,
            "cloudflare_enabled": False,
        },
        "product_status": PRODUCT_STATUS,
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
        "learner_semantics_summary": deepcopy(acceptance),
        "production_safety": {
            "production_database_unchanged": True,
            "learner_progress_mutated_by_acceptance": False,
            "auth_state_reused_from_s13": True,
        },
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def _source(receipt_path: Path) -> tuple[dict[str, Any], Path, Path, dict[str, dict[str, Any]], dict[str, int], Path]:
    receipt = read_json(receipt_path, "s14_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"), receipt.get("validation_status"),
        receipt.get("product_status"), receipt.get("stop_reason"),
    )
    if identity != (TASK_ID, SCHEMA_VERSION, PASS_STATUS, PRODUCT_STATUS, "NONE"):
        raise LearnerFacingSemanticsError("s14_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise LearnerFacingSemanticsError("s14_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs", {})
    source_s13 = Path(str(outputs.get("source_s13_receipt_path") or "")).resolve()
    secure_static = Path(str(outputs.get("secure_static_root") or "")).resolve()
    s13_receipt, database, _, auth_state, bundles, sequence = _verify_s13(source_s13)
    if not secure_static.is_dir():
        raise LearnerFacingSemanticsError("s14_secure_static_missing")
    return s13_receipt, database, auth_state, bundles, sequence, secure_static


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    _, database, auth_state, bundles, sequence, secure_static = _source(receipt_path)
    config = s13.PersistentBoundaryConfig.from_environment(
        host=host,
        port=port,
        revocation_db_path=auth_state,
    )
    server = s11.SecureBoundaryServer(
        (host, port),
        _app(database, bundles, sequence),
        secure_static,
        config,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def readback(*, receipt_path: Path) -> dict[str, Any]:
    receipt = read_json(receipt_path, "s14_receipt")
    _source(receipt_path)
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "learner_semantics_summary": deepcopy(receipt["learner_semantics_summary"]),
        "capability_contract": deepcopy(receipt["capability_contract"]),
        "next_short_step": NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s13", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    server = commands.add_parser("serve")
    server.add_argument("--receipt", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=DEFAULT_PORT)
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
        receipt, safe = materialize(s13_receipt_path=args.s13, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s14_learner_facing_curriculum_progress_semantics import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s13_path=args.s13,
        )
        if validation["error_count"]:
            raise LearnerFacingSemanticsError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        LearnerFacingSemanticsError,
        s13.LocalhostDeploymentError,
        s13.s12.ReverseProxyAcceptanceError,
        s11.SecureBoundaryError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
