#!/usr/bin/env python3
"""Patch and validate the A1FS V1.2.1 U01F learner surface."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Sequence

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reorders already-approved SINGLE_SELECT options at session presentation time, "
    "clarifies existing M6/S17 review states, and renders authenticated review feedback. "
    "It creates no item, answer, scoring rule, learner state, mastery authority, audio, "
    "A2 unlock, external route, or parallel runtime."
)

SHUFFLE_POLICY_VERSION = "U01F_OPTION_ORDER_V1"
REVIEW_CENTER_ID = "u01f-review-center"
MY_REVIEWS_ID = "u01f-my-writing-reviews"
MY_REVIEWS_LIST_ID = "u01f-my-writing-review-list"
MY_REVIEWS_STATE_ID = "u01f-my-writing-review-state"

PENDING_OLD = "PENDING_HUMAN_REVIEW:'等待人工審核'"
PENDING_NEW = "PENDING_HUMAN_REVIEW:'已送交人工審核，可完成本次學習'"
OPTIONS_MARKER = "const options=asset.learner_payload.options||[];"
OPTIONS_REPLACEMENT = (
    "const options=stableSessionOptions(active&&active.session_id?active.session_id:'',asset);"
)
BAD_REVIEW_SUBMIT = (
    "const response=await api('/api/human-review/decision',"
    "{method:'POST',headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify({attempt_id:row.attempt_id,decision,criteria,notes})});"
)
GOOD_REVIEW_SUBMIT = (
    "const response=await api('/api/human-review/decision',"
    "{attempt_id:row.attempt_id,decision,criteria,notes});"
)

INDEX_PANEL = f'''<section id="{REVIEW_CENTER_ID}" class="panel u01f-review-center">
  <div class="section-heading"><h2>寫作審核與回饋</h2></div>
  <p>寫作送出後可以繼續學習；人工裁決完成前不計通過或精熟。</p>
  <p><a href="#human-review-panel">前往教師人工審核中心</a></p>
  <section id="{MY_REVIEWS_ID}" aria-label="我的寫作審核">
    <h3>我的寫作審核</h3>
    <button type="button" id="u01f-load-my-writing-reviews">更新審核結果</button>
    <div id="{MY_REVIEWS_LIST_ID}"></div>
    <p id="{MY_REVIEWS_STATE_ID}" class="note">登入後可讀取自己的寫作審核。</p>
  </section>
</section>
'''

JS_EXTENSION = rf'''
const U01F_SHUFFLE_POLICY_VERSION='{SHUFFLE_POLICY_VERSION}';
function u01fHash32(value){{let state=2166136261>>>0;const bytes=new TextEncoder().encode(value);for(const byte of bytes){{state^=byte;state=Math.imul(state,16777619)>>>0;}}return state>>>0;}}
function u01fStableShuffle(values,seed){{const result=[...values];let state=u01fHash32(seed);for(let index=result.length-1;index>0;index--){{state=(Math.imul(state,1664525)+1013904223)>>>0;const target=state%(index+1);[result[index],result[target]]=[result[target],result[index]];}}return result;}}
function stableSessionOptions(sessionId,asset){{const values=asset.learner_payload.options||[];if(values.length<2||asset.learner_payload.interaction_mode!=='SINGLE_SELECT')return values;return u01fStableShuffle(values,`${{U01F_SHUFFLE_POLICY_VERSION}}|${{sessionId}}|${{asset.asset_key}}`);}}
const u01fMyReviewList=document.querySelector('#{MY_REVIEWS_LIST_ID}'),u01fMyReviewState=document.querySelector('#{MY_REVIEWS_STATE_ID}'),u01fLoadMyReviews=document.querySelector('#u01f-load-my-writing-reviews');
function u01fReviewLabel(value){{return ({{PENDING_HUMAN_REVIEW:'等待人工審核',HUMAN_DEFER:'審核延後',HUMAN_APPROVE:'已核准',HUMAN_REJECT:'需要修改'}}[value]||value||'—');}}
function renderMyWritingReviews(value){{u01fMyReviewList.replaceChildren();const rows=value.reviews||[];if(!rows.length){{text(u01fMyReviewState,'目前沒有寫作審核紀錄。');return;}}for(const row of rows){{const card=document.createElement('article');card.className='review-card learner-review-card';const heading=document.createElement('h4');text(heading,u01fReviewLabel(row.outcome));const response=document.createElement('pre');response.className='review-response';text(response,typeof row.response==='string'?row.response:JSON.stringify(row.response));const notes=document.createElement('p');text(notes,row.notes?`回饋：${{row.notes}}`:'尚無審核備註');card.append(heading,response,notes);u01fMyReviewList.append(card);}}text(u01fMyReviewState,`共 ${{rows.length}} 筆寫作審核紀錄。`);}}
async function loadMyWritingReviews(){{try{{text(u01fMyReviewState,'讀取中…');renderMyWritingReviews(await api('/api/my-writing-reviews'));}}catch(error){{text(u01fMyReviewState,`讀取失敗：${{error.message}}`);}}}}
if(u01fLoadMyReviews)u01fLoadMyReviews.addEventListener('click',loadMyWritingReviews);
document.addEventListener('DOMContentLoaded',()=>loadMyWritingReviews().catch(error=>text(u01fMyReviewState,error.message)));
'''

CSS_EXTENSION = """
.u01f-review-center{border-width:2px}.u01f-review-center a{font-weight:700}.learner-review-card{border-left:4px solid #40556b}.learner-review-card h4{margin-top:0}
"""


class U01FStaticError(ValueError):
    """Fail-closed V1.2.1 learner-surface patch error."""


def stable_option_order(session_id: str, asset_key: str, options: Sequence[str]) -> list[str]:
    """Python mirror of the browser's stable per-session Fisher-Yates shuffle."""
    values = [str(row) for row in options]
    if len(values) < 2:
        return values
    seed = f"{SHUFFLE_POLICY_VERSION}|{session_id}|{asset_key}".encode("utf-8")
    state = 2166136261
    for byte in seed:
        state ^= byte
        state = (state * 16777619) & 0xFFFFFFFF
    for index in range(len(values) - 1, 0, -1):
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        target = state % (index + 1)
        values[index], values[target] = values[target], values[index]
    return values


def patch_static(source_root: Path, target_root: Path) -> dict[str, Any]:
    source_root, target_root = Path(source_root), Path(target_root)
    if source_root.resolve() != target_root.resolve():
        if target_root.exists():
            shutil.rmtree(target_root)
        shutil.copytree(source_root, target_root)
    index_path = target_root / "index.html"
    app_path = target_root / "app.js"
    css_path = target_root / "styles.css"
    if not all(path.is_file() for path in (index_path, app_path, css_path)):
        raise U01FStaticError("secure_static_files_missing")

    index = index_path.read_text(encoding="utf-8")
    if REVIEW_CENTER_ID not in index:
        marker = "</main>" if "</main>" in index else "</body>"
        if marker not in index:
            raise U01FStaticError("review_center_insertion_marker_missing")
        index = index.replace(marker, INDEX_PANEL + marker, 1)
        index_path.write_text(index, encoding="utf-8")

    app = app_path.read_text(encoding="utf-8")
    if "function stableSessionOptions" not in app:
        if OPTIONS_MARKER not in app:
            raise U01FStaticError("single_select_option_marker_missing")
        app = app.replace(OPTIONS_MARKER, OPTIONS_REPLACEMENT, 1)
    if PENDING_OLD in app:
        app = app.replace(PENDING_OLD, PENDING_NEW, 1)
    elif PENDING_NEW not in app:
        raise U01FStaticError("pending_review_label_marker_missing")
    if BAD_REVIEW_SUBMIT in app:
        app = app.replace(BAD_REVIEW_SUBMIT, GOOD_REVIEW_SUBMIT, 1)
    elif GOOD_REVIEW_SUBMIT not in app:
        raise U01FStaticError("review_submission_payload_marker_missing")
    if "function loadMyWritingReviews" not in app:
        app += "\n" + JS_EXTENSION + "\n"
    app_path.write_text(app, encoding="utf-8")

    css = css_path.read_text(encoding="utf-8")
    if ".u01f-review-center" not in css:
        css += "\n" + CSS_EXTENSION
    css_path.write_text(css, encoding="utf-8")
    return validate_static(target_root)


def validate_static(root: Path) -> dict[str, Any]:
    root = Path(root)
    index = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "app.js").read_text(encoding="utf-8")
    css = (root / "styles.css").read_text(encoding="utf-8")
    checks = {
        "review_center_visible": REVIEW_CENTER_ID in index,
        "learner_review_feedback_visible": MY_REVIEWS_ID in index,
        "stable_session_shuffle_present": "function stableSessionOptions" in app,
        "single_select_uses_stable_shuffle": OPTIONS_REPLACEMENT in app,
        "pending_review_nonblocking_message": PENDING_NEW in app,
        "review_submission_payload_fixed": GOOD_REVIEW_SUBMIT in app and BAD_REVIEW_SUBMIT not in app,
        "learner_review_endpoint_connected": "/api/my-writing-reviews" in app,
        "styles_present": ".u01f-review-center" in css,
        "hidden_answers_absent": all(
            marker not in app
            for marker in ("accepted_texts", "accepted_sequence", "correct_answer")
        ),
    }
    failed = [key for key, value in checks.items() if value is not True]
    if failed:
        raise U01FStaticError("static_validation_failed:" + ",".join(failed))
    return {"validation_status": "PASS_A1FS_V1_2_1_U01F_STATIC", **checks}
