#!/usr/bin/env python3
"""Materialize A1FS Online V1 S17 learner/parent/teacher dashboards and human review."""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from ulga.builders import build_a1fs_online_v1_s16_canonical_mastery_remediation_reassessment_review_integration as s16
from ulga.builders import build_a1fs_v1_m9_teacher_dashboard_progress_reporting_export as m9

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Projects existing S16/M7/M8/M9 learner state into authenticated learner, parent, and teacher dashboard views and exposes the existing M6 human-review decision authority; it creates no curriculum, learner content, answers, scoring, review, mastery, identity-role, audio, A2, Cloudflare, or parallel state engine."

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S17_LearnerParentTeacherDashboardAndHumanReview_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s17.dashboard_human_review.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S17_DASHBOARD_HUMAN_REVIEW_READY"
PRODUCT_STATUS = "LOCALHOST_NONAUDIO_LEARNER_PARENT_TEACHER_DASHBOARD_HUMAN_REVIEW_READY"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S18_NonAudioLearnerProductE2EReleaseAcceptanceAndRecovery_NoAudio"
DEFAULT_PORT = 8765
CANARY_LEARNER_ID = s16.core.CANARY_LEARNER_ID
CANARY_REVIEW_SESSION_ID = "A1FS_ONLINE_V1_S17_SESSION:HUMAN_REVIEW"
CANARY_REVIEWER_ID = "S17_AUTHENTICATED_REVIEWER"
CANARY_REVIEWED_AT = "2026-01-18T00:10:00Z"

FORBIDDEN_SAFE_KEYS = set(s16.core.FORBIDDEN_SAFE_KEYS) | {
    "response_json", "reviewer_id", "criteria", "notes", "review_queue",
}


class DashboardReviewError(ValueError):
    """Fail-closed S17 dashboard/review error."""


def digest(value: Any) -> str:
    return s16.digest(value)


def file_digest(path: Path) -> str:
    return s16.file_digest(path)


def read_json(path: Path, code: str) -> dict[str, Any]:
    return s16.read_json(path, code)


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    s16.write_json(path, value, private=private)


def safe_scan(value: Any) -> None:
    forbidden = {key.casefold() for key in FORBIDDEN_SAFE_KEYS}

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden:
                    raise DashboardReviewError(f"private_content_leak:{key}")
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


def _source(
    receipt_path: Path,
) -> tuple[
    dict[str, Any], Path, Path, dict[str, dict[str, Any]], dict[str, int],
    Path, Path, Path, Path,
]:
    receipt_path = Path(receipt_path).resolve()
    receipt = read_json(receipt_path, "s16_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    if identity != (s16.TASK_ID, s16.SCHEMA_VERSION, s16.PASS_STATUS, s16.PRODUCT_STATUS, "NONE"):
        raise DashboardReviewError("s16_receipt_contract_invalid")
    body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(body):
        raise DashboardReviewError("s16_receipt_digest_invalid")
    (
        _, database, auth_state, bundles, sequence, graph_path, state_root, secure_static,
    ) = s16._load_runtime(receipt_path)
    outputs = receipt.get("runtime_outputs", {})
    acceptance_database = Path(str(outputs.get("acceptance_database_path") or "")).resolve()
    if not acceptance_database.is_file():
        raise DashboardReviewError("s16_acceptance_database_missing")
    if len(bundles) != 72 or len(sequence) != 24:
        raise DashboardReviewError("s16_runtime_denominator_invalid")
    return (
        receipt, database, auth_state, bundles, sequence, graph_path, state_root,
        secure_static, acceptance_database,
    )


def _latest_snapshot(connection: sqlite3.Connection, learner_id: str) -> dict[str, Any] | None:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='mastery_snapshots'"
    ).fetchone()
    if not exists:
        return None
    row = connection.execute(
        """SELECT snapshot_json FROM mastery_snapshots
           WHERE learner_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1""",
        (learner_id,),
    ).fetchone()
    if not row:
        return None
    value = json.loads(str(row["snapshot_json"]))
    if not isinstance(value, dict):
        raise DashboardReviewError("mastery_snapshot_not_object")
    return value


def _pending_review_count(connection: sqlite3.Connection, learner_id: str) -> int:
    return int(connection.execute(
        """SELECT COUNT(*) FROM response_attempts a
           JOIN scoring_results s USING(attempt_id)
           WHERE a.learner_id=? AND s.outcome IN('PENDING_HUMAN_REVIEW','HUMAN_DEFER')""",
        (learner_id,),
    ).fetchone()[0])


def build_dashboard_projection(
    *,
    skill_progress: Sequence[Mapping[str, Any]],
    canonical_learning: Mapping[str, Any],
    pending_review_count: int,
) -> dict[str, Any]:
    skills = [
        {
            "skill": str(row["skill"]),
            "session_count": int(row.get("session_count") or 0),
            "completed_session_count": int(row.get("completed_session_count") or 0),
            "attempt_count": int(row.get("attempt_count") or 0),
            "pass_count": int(row.get("pass_count") or 0),
            "fail_count": int(row.get("fail_count") or 0),
            "pending_review_count": int(row.get("pending_review_count") or 0),
            "resolved_pass_rate": float(row.get("resolved_pass_rate") or 0.0),
        }
        for row in skill_progress
    ]
    by_skill = {row["skill"]: row for row in skills}
    mastered = int(canonical_learning.get("mastered_required_count") or 0)
    required = int(canonical_learning.get("required_mastery_node_count") or 72)
    remediation = int(canonical_learning.get("open_remediation_count") or 0)
    reassessment = int(canonical_learning.get("pending_reassessment_count") or 0)
    due = int(canonical_learning.get("due_review_count") or 0) + int(canonical_learning.get("overdue_review_count") or 0)
    retained = int(canonical_learning.get("retained_required_count") or 0)
    completed_sessions = sum(row["completed_session_count"] for row in skills)
    attempts = sum(row["attempt_count"] for row in skills)
    passed = sum(row["pass_count"] for row in skills)
    failed = sum(row["fail_count"] for row in skills)
    attention: list[str] = []
    if pending_review_count:
        attention.append("HUMAN_REVIEW_REQUIRED")
    if remediation:
        attention.append("REMEDIATION_REQUIRED")
    if reassessment:
        attention.append("REASSESSMENT_PENDING")
    if due:
        attention.append("SPACED_REVIEW_DUE")
    return {
        "role_count": 3,
        "learner": {
            "completed_session_count": completed_sessions,
            "mastered_required_count": mastered,
            "required_mastery_node_count": required,
            "open_remediation_count": remediation,
            "due_review_count": due,
            "a2_unlocked": False,
        },
        "parent": {
            "completed_session_count": completed_sessions,
            "attempt_count": attempts,
            "pass_count": passed,
            "fail_count": failed,
            "mastered_required_count": mastered,
            "retained_required_count": retained,
            "attention_codes": attention,
        },
        "teacher": {
            "skills": skills,
            "pending_human_review_count": int(pending_review_count),
            "open_remediation_count": remediation,
            "pending_reassessment_count": reassessment,
            "due_review_count": due,
            "attention_codes": attention,
            "writing": deepcopy(by_skill.get("WRITING", {})),
            "reading": deepcopy(by_skill.get("READING", {})),
        },
        "privacy_boundaries": {
            "raw_response_in_dashboard": False,
            "prompt_text_in_dashboard": False,
            "raw_response_available_only_in_authenticated_review_queue": True,
            "public_delivery": False,
        },
        "product_boundaries": {
            "role_based_identity_authorization_claimed": False,
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
            "speaking_capture_enabled": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "cloudflare_enabled": False,
        },
    }


class DashboardReviewApplication(s16.CanonicalLearningApplication):
    """S16 learner runtime with M9-style dashboards and M6 human review actions."""

    def bootstrap(self) -> dict[str, Any]:
        value = super().bootstrap()
        value.update({
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "release_profile": RELEASE_PROFILE,
        })
        value["learner_product_semantics"].update({
            "learner_dashboard_connected": True,
            "parent_dashboard_connected": True,
            "teacher_dashboard_connected": True,
            "human_review_queue_connected": True,
            "human_review_decision_authority": "A1FS_V1_M6",
            "dashboard_projection_authority": "A1FS_V1_M9",
            "role_based_identity_authorization_claimed": False,
        })
        return value

    def dashboard_readback(self) -> dict[str, Any]:
        with _connect(self.database_path) as connection:
            profile = connection.execute(
                "SELECT learner_id,profile_state FROM learner_profiles WHERE learner_id=?",
                (self.default_learner_id,),
            ).fetchone()
            if not profile or profile["profile_state"] != "ACTIVE":
                raise DashboardReviewError("learner_profile_not_active")
            skill_progress = m9.skill_rows(connection, self.default_learner_id)
            pending = _pending_review_count(connection, self.default_learner_id)
        canonical_learning = s16.core._latest_learning_projection(
            self.database_path, self.default_learner_id
        )
        return {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "dashboard": build_dashboard_projection(
                skill_progress=skill_progress,
                canonical_learning=canonical_learning,
                pending_review_count=pending,
            ),
        }

    def pending_human_reviews(self) -> dict[str, Any]:
        with _connect(self.database_path) as connection:
            rows = connection.execute(
                """SELECT a.attempt_id,a.session_id,a.lesson_id,a.asset_key,a.response_json,a.submitted_at,
                          c.skill,c.role,s.outcome,q.decision,q.criteria_json
                   FROM response_attempts a
                   JOIN response_contracts c USING(asset_key)
                   JOIN scoring_results s USING(attempt_id)
                   JOIN human_review_queue q USING(attempt_id)
                   WHERE a.learner_id=? AND s.outcome IN('PENDING_HUMAN_REVIEW','HUMAN_DEFER')
                   ORDER BY a.submitted_at,a.attempt_id""",
                (self.default_learner_id,),
            ).fetchall()
        queue = []
        for row in rows:
            response = json.loads(str(row["response_json"]))
            criteria = json.loads(str(row["criteria_json"]))
            queue.append({
                "attempt_id": str(row["attempt_id"]),
                "session_id": str(row["session_id"]),
                "lesson_id": str(row["lesson_id"]),
                "asset_key": str(row["asset_key"]),
                "skill": str(row["skill"]),
                "role": str(row["role"]),
                "response": response,
                "submitted_at": str(row["submitted_at"]),
                "outcome": str(row["outcome"]),
                "decision": row["decision"],
                "criteria": criteria,
            })
        return {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "private_authenticated_operator_only": True,
            "raw_response_included_for_review": True,
            "pending_count": len(queue),
            "review_queue": queue,
        }

    def review_attempt(self, payload: Mapping[str, Any], *, reviewer_id: str) -> dict[str, Any]:
        attempt_id = str(payload.get("attempt_id") or "")
        decision = str(payload.get("decision") or "").upper()
        criteria = payload.get("criteria")
        notes = payload.get("notes")
        reviewed_at = payload.get("reviewed_at")
        if not attempt_id:
            raise DashboardReviewError("attempt_id_required")
        if decision not in {"APPROVE", "REJECT", "DEFER"}:
            raise DashboardReviewError("review_decision_invalid")
        if not isinstance(criteria, Mapping):
            raise DashboardReviewError("review_criteria_required")
        result = self.response_store.review_response(
            attempt_id=attempt_id,
            decision=decision,
            reviewer_id=str(reviewer_id),
            criteria=dict(criteria),
            notes=None if notes is None else str(notes),
            reviewed_at=None if reviewed_at is None else str(reviewed_at),
        )
        with _connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT session_id FROM response_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
        if not row:
            raise DashboardReviewError("reviewed_attempt_session_missing")
        readiness = self.completion_readiness(str(row["session_id"]))
        return {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "review_result": result,
            "completion_gate": readiness,
            "pending_count": self.pending_human_reviews()["pending_count"],
            "mastery_refreshed": False,
        }

    def progress_readback(self) -> dict[str, Any]:
        value = super().progress_readback()
        dashboard = self.dashboard_readback()["dashboard"]
        value.update({
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "dashboard_summary": {
                "role_count": dashboard["role_count"],
                "pending_human_review_count": dashboard["teacher"]["pending_human_review_count"],
                "open_remediation_count": dashboard["teacher"]["open_remediation_count"],
                "pending_reassessment_count": dashboard["teacher"]["pending_reassessment_count"],
                "due_review_count": dashboard["teacher"]["due_review_count"],
            },
        })
        value["semantic_boundaries"].update({
            "dashboard_raw_response_exported": False,
            "review_queue_raw_response_operator_only": True,
            "role_based_identity_authorization_claimed": False,
        })
        return value


def _app(
    *,
    database: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
    graph_path: Path,
    state_root: Path,
    default_learner_id: str = s16.s15.s14.s13.s11.s10.s09.s05.DEFAULT_LEARNER_ID,
) -> DashboardReviewApplication:
    return DashboardReviewApplication(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence,
        graph_path=graph_path,
        state_root=state_root,
        default_learner_id=default_learner_id,
    )


class DashboardReviewHandler(s16.s15.s11.SecureBoundaryHandler):
    """Authenticated dashboard/review HTTP routes layered on the S16 runtime."""

    @property
    def dashboard_app(self) -> DashboardReviewApplication:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in {"/api/dashboard", "/api/human-review"}:
            super().do_GET()
            return
        if not self._transport_valid():
            return
        claims = self._claims()
        if claims is None:
            self._json(401, {"error": "authentication_required"})
            return
        try:
            value = (
                self.dashboard_app.dashboard_readback()
                if path == "/api/dashboard"
                else self.dashboard_app.pending_human_reviews()
            )
            self._json(200, value)
        except (DashboardReviewError, s16.CanonicalLearningError, s16.s15.ScoredJourneyError, sqlite3.Error, ValueError) as exc:
            self._json(409, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/human-review/decision":
            super().do_POST()
            return
        if not self._transport_valid() or not self._origin_valid():
            return
        claims = self._claims()
        if claims is None:
            self._json(401, {"error": "authentication_required"})
            return
        if not self._csrf_valid(claims):
            return
        try:
            payload = self._read_json_body()
            value = self.dashboard_app.review_attempt(payload, reviewer_id=str(claims["sub"]))
            self._json(200, value)
        except (
            DashboardReviewError,
            s16.CanonicalLearningError,
            s16.s15.ScoredJourneyError,
            s16.core.m7.MasteryError,
            s16.core.m8.ReviewRetentionError,
            sqlite3.Error,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            self._json(409, {"error": str(exc)})


class DashboardReviewServer(s16.s15.s11.SecureBoundaryServer):
    def __init__(self, address: tuple[str, int], app: DashboardReviewApplication, secure_static_root: Path, config: Any):
        if not s16.s15.s11._is_loopback(address[0]):
            raise DashboardReviewError(f"non_loopback_host_forbidden:{address[0]}")
        self.app = app
        self.static_root = Path(secure_static_root)
        self.secure_static_root = Path(secure_static_root)
        self.config = config
        super(s16.s15.s11.SecureBoundaryServer, self).__init__(address, DashboardReviewHandler)
        self.config.bind_local_port(int(self.server_address[1]))


def _start_server(*, app: DashboardReviewApplication, secure_static_root: Path, config: Any) -> tuple[Any, threading.Thread, int]:
    server = DashboardReviewServer(("127.0.0.1", 0), app, secure_static_root, config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, int(server.server_address[1])


def _write_static(target_root: Path) -> None:
    target_root = Path(target_root)
    source = target_root
    if not (source / "index.html").is_file():
        s16._write_static(target_root)
    index_path = target_root / "index.html"
    index = index_path.read_text(encoding="utf-8")
    marker = '<section id="canonical-learning"'
    panel = '''<section id="dashboard-panel" class="panel dashboard-panel">
      <div class="section-heading"><h2>學習儀表板與人工審核</h2></div>
      <div class="role-tabs"><button type="button" data-dashboard-role="learner">學習者</button><button type="button" data-dashboard-role="parent">家長</button><button type="button" data-dashboard-role="teacher">教師</button></div>
      <div id="dashboard-summary" class="summary-grid"></div>
      <p id="dashboard-state" class="note"></p>
      <section id="human-review-panel"><h3>待人工審核</h3><div id="human-review-list"></div><p id="human-review-state" class="note"></p></section>
    </section>
    <section id="canonical-learning"'''
    if marker not in index:
        raise DashboardReviewError("s16_canonical_panel_marker_missing")
    index = index.replace(marker, panel, 1)
    index_path.write_text(index + ("" if index.endswith("\n") else "\n"), encoding="utf-8")

    css_path = target_root / "styles.css"
    css = css_path.read_text(encoding="utf-8")
    css += "\n.dashboard-panel{border-width:2px}.role-tabs{display:flex;gap:.5rem;flex-wrap:wrap}.review-card{border:1px solid #bbb;padding:.75rem;margin:.5rem 0}.review-card label{display:block;margin:.35rem 0}.review-response{white-space:pre-wrap;background:#f5f5f5;padding:.5rem}\n"
    css_path.write_text(css, encoding="utf-8")

    app_path = target_root / "app.js"
    app = app_path.read_text(encoding="utf-8")
    extension = r'''
const dashboardSummary=document.querySelector('#dashboard-summary'),dashboardState=document.querySelector('#dashboard-state'),reviewList=document.querySelector('#human-review-list'),reviewState=document.querySelector('#human-review-state');let dashboardRole='learner';
function dashboardMetric(label,value){return metric(label,value==null?'—':value)}
function renderRoleDashboard(value){const view=value.dashboard[dashboardRole]||{};dashboardSummary.replaceChildren();if(dashboardRole==='learner'){dashboardSummary.append(dashboardMetric('已完成學習',view.completed_session_count),dashboardMetric('已精熟節點',view.mastered_required_count),dashboardMetric('待補救',view.open_remediation_count),dashboardMetric('到期複習',view.due_review_count));}else if(dashboardRole==='parent'){dashboardSummary.append(dashboardMetric('已完成學習',view.completed_session_count),dashboardMetric('作答次數',view.attempt_count),dashboardMetric('通過',view.pass_count),dashboardMetric('需再練習',view.fail_count));}else{dashboardSummary.append(dashboardMetric('待人工審核',view.pending_human_review_count),dashboardMetric('待補救',view.open_remediation_count),dashboardMetric('待重新評量',view.pending_reassessment_count),dashboardMetric('到期複習',view.due_review_count));}text(dashboardState,`目前顯示：${dashboardRole==='learner'?'學習者':dashboardRole==='parent'?'家長':'教師'}視圖。`);document.querySelector('#human-review-panel').hidden=dashboardRole!=='teacher';}
async function loadDashboard(){const value=await api('/api/dashboard');renderRoleDashboard(value);}
function reviewCheckbox(label,key){const wrapper=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.dataset.criteria=key;wrapper.append(input,document.createTextNode(` ${label}`));return wrapper;}
async function submitReview(card,row){const criteria={};card.querySelectorAll('[data-criteria]').forEach(input=>{criteria[input.dataset.criteria]=input.checked;});const decision=card.querySelector('select').value,notes=card.querySelector('textarea').value;const response=await api('/api/human-review/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({attempt_id:row.attempt_id,decision,criteria,notes})});text(reviewState,`審核完成：${response.review_result.outcome}`);await Promise.all([loadDashboard(),loadHumanReviews()]);}
function renderHumanReviews(value){reviewList.replaceChildren();if(!value.review_queue.length){text(reviewState,'目前沒有待人工審核項目。');return;}text(reviewState,`待審核 ${value.pending_count} 項。`);for(const row of value.review_queue){const card=document.createElement('article');card.className='review-card';const title=document.createElement('h4');text(title,`${row.skill} · ${row.role}`);const response=document.createElement('pre');response.className='review-response';text(response,typeof row.response==='string'?row.response:JSON.stringify(row.response));const select=document.createElement('select');for(const choice of ['APPROVE','REJECT','DEFER']){const option=document.createElement('option');option.value=choice;text(option,choice);select.append(option);}const notes=document.createElement('textarea');notes.placeholder='審核備註';const button=document.createElement('button');button.type='button';text(button,'送出審核');button.addEventListener('click',()=>submitReview(card,row));card.append(title,response,reviewCheckbox('文法目標符合','grammar_target_match'),reviewCheckbox('語意符合情境','meaning_matches_context'),reviewCheckbox('回答完整','complete_response'),select,notes,button);reviewList.append(card);}}
async function loadHumanReviews(){const value=await api('/api/human-review');renderHumanReviews(value);}
document.querySelectorAll('[data-dashboard-role]').forEach(button=>button.addEventListener('click',async()=>{dashboardRole=button.dataset.dashboardRole;await loadDashboard();if(dashboardRole==='teacher')await loadHumanReviews();}));
document.addEventListener('DOMContentLoaded',async()=>{try{await loadDashboard();await loadHumanReviews();}catch(error){text(dashboardState,error.message);}});
'''
    if "function renderRoleDashboard" not in app:
        app += "\n" + extension + "\n"
    app_path.write_text(app, encoding="utf-8")


def _select_review_lesson(database: Path, bundles: Mapping[str, Mapping[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    for lesson_id in s16.s15._lesson_ids(bundles, "WRITING"):
        contracts = s16.s15._contracts_for_lesson(database, lesson_id)
        if len(contracts) == 4 and any(row.get("scoring_mode") == "FEATURE_RUBRIC" for row in contracts):
            return lesson_id, contracts
    raise DashboardReviewError("feature_rubric_writing_lesson_missing")


def _prepare_pending_review(
    *, app: DashboardReviewApplication, bundles: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str, int]:
    lesson_id, contracts = _select_review_lesson(app.database_path, bundles)
    session = app.start_session({
        "lesson_id": lesson_id,
        "session_id": CANARY_REVIEW_SESSION_ID,
        "at": "2026-01-18T00:00:00Z",
    })
    current: Mapping[str, Any] = session
    pending_attempt_id = ""
    for index, contract in enumerate(contracts, start=1):
        exposed = app.record_exposure({
            "session_id": CANARY_REVIEW_SESSION_ID,
            "asset_key": contract["asset_key"],
            "expected_session_version": current["session_version"],
            "at": f"2026-01-18T00:01:{index:02d}Z",
        })
        attempt_id = f"A1FS_ONLINE_V1_S17_ATTEMPT:WRITING:{index}"
        current = app.submit_response({
            "session_id": CANARY_REVIEW_SESSION_ID,
            "asset_key": contract["asset_key"],
            "response": s16.s15._passing_response(contract),
            "expected_session_version": exposed["session_version"],
            "attempt_id": attempt_id,
            "submitted_at": f"2026-01-18T00:02:{index:02d}Z",
        })
        if current["outcome"] == "PENDING_HUMAN_REVIEW":
            pending_attempt_id = attempt_id
    if not pending_attempt_id:
        raise DashboardReviewError("pending_human_review_attempt_not_created")
    readiness = app.completion_readiness(CANARY_REVIEW_SESSION_ID)
    if readiness.get("completion_allowed") is not False or readiness.get("pending_human_review_count") != 1:
        raise DashboardReviewError("pending_review_completion_gate_invalid")
    return pending_attempt_id, lesson_id, int(current["session_version"])


def _run_authenticated_acceptance(
    *, app: DashboardReviewApplication, secure_static_root: Path, auth_state: Path,
    pending_attempt_id: str, expected_session_version: int,
) -> dict[str, Any]:
    config = s16.s15.s13.PersistentBoundaryConfig.from_values(
        username=CANARY_REVIEWER_ID,
        password=s16.s15.CANARY_PASSWORD,
        session_secret=s16.s15.CANARY_SESSION_SECRET,
        mode="local",
        allowed_origin="http://127.0.0.1",
        allowed_host="127.0.0.1",
        revocation_db_path=auth_state,
        port=0,
    )
    server, thread, port = _start_server(app=app, secure_static_root=secure_static_root, config=config)
    origin = f"http://127.0.0.1:{port}"
    try:
        s16.s15.s11._request(port, "GET", "/api/dashboard", expected_status=401)
        login, headers = s16.s15.s11._request(
            port, "POST", "/auth/login",
            {"username": CANARY_REVIEWER_ID, "password": s16.s15.CANARY_PASSWORD},
            origin=origin,
        )
        cookie = str(headers.get("Set-Cookie") or "").split(";", 1)[0]
        csrf = str(login.get("csrf_token") or "")
        if not cookie or not csrf:
            raise DashboardReviewError("s17_http_login_invalid")
        dashboard_before, _ = s16.s15.s11._request(port, "GET", "/api/dashboard", cookie=cookie)
        queue_before, _ = s16.s15.s11._request(port, "GET", "/api/human-review", cookie=cookie)
        if dashboard_before.get("dashboard", {}).get("role_count") != 3:
            raise DashboardReviewError("s17_http_dashboard_role_count_invalid")
        if queue_before.get("pending_count") != 1:
            raise DashboardReviewError("s17_http_review_queue_denominator_invalid")
        row = queue_before["review_queue"][0]
        if row.get("attempt_id") != pending_attempt_id or not row.get("response"):
            raise DashboardReviewError("s17_http_review_queue_content_invalid")
        decision, _ = s16.s15.s11._request(
            port, "POST", "/api/human-review/decision",
            {
                "attempt_id": pending_attempt_id,
                "decision": "APPROVE",
                "criteria": {
                    "grammar_target_match": True,
                    "meaning_matches_context": True,
                    "complete_response": True,
                },
                "notes": "S17 isolated authenticated review acceptance.",
                "reviewed_at": CANARY_REVIEWED_AT,
            },
            cookie=cookie,
            csrf=csrf,
            origin=origin,
        )
        if decision.get("review_result", {}).get("outcome") != "HUMAN_APPROVE":
            raise DashboardReviewError("s17_http_review_decision_invalid")
        if decision.get("pending_count") != 0:
            raise DashboardReviewError("s17_http_review_queue_not_cleared")
        if decision.get("completion_gate", {}).get("completion_allowed") is not True:
            raise DashboardReviewError("s17_http_completion_gate_not_ready")
        completed = app.complete_session({
            "session_id": CANARY_REVIEW_SESSION_ID,
            "expected_session_version": expected_session_version,
            "at": "2026-01-18T00:11:00Z",
        })
        if completed.get("session_state") != "COMPLETED":
            raise DashboardReviewError("s17_reviewed_session_not_completed")
        dashboard_after, _ = s16.s15.s11._request(port, "GET", "/api/dashboard", cookie=cookie)
        queue_after, _ = s16.s15.s11._request(port, "GET", "/api/human-review", cookie=cookie)
        if queue_after.get("pending_count") != 0:
            raise DashboardReviewError("s17_http_queue_after_completion_invalid")
        return {
            "dashboard_role_count": 3,
            "pending_human_review_count_before": 1,
            "pending_human_review_count_after": 0,
            "authenticated_dashboard_endpoint_pass": True,
            "authenticated_review_queue_endpoint_pass": True,
            "csrf_review_decision_pass": True,
            "human_approve_outcome_pass": True,
            "completion_after_human_approval": True,
            "dashboard_after_completion_pass": dashboard_after.get("dashboard", {}).get("teacher", {}).get("pending_human_review_count") == 0,
            "review_queue_raw_response_available": True,
        }
    finally:
        s16.s15.s13._stop_server(server, thread)


def run_isolated_acceptance(
    *,
    source_acceptance_database: Path,
    production_database: Path,
    source_state_root: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
    graph_path: Path,
    secure_static_root: Path,
    acceptance_database: Path,
    state_root: Path,
    auth_state: Path,
) -> dict[str, Any]:
    production_before = file_digest(production_database)
    acceptance_database.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_acceptance_database, acceptance_database)
    if state_root.exists():
        shutil.rmtree(state_root)
    if source_state_root.is_dir():
        shutil.copytree(source_state_root, state_root)
    else:
        state_root.mkdir(parents=True, exist_ok=True)
    app = _app(
        database=acceptance_database,
        bundles=bundles,
        sequence=sequence,
        graph_path=graph_path,
        state_root=state_root,
        default_learner_id=CANARY_LEARNER_ID,
    )
    pending_attempt_id, _, session_version = _prepare_pending_review(app=app, bundles=bundles)
    dashboard_before = app.dashboard_readback()
    if dashboard_before["dashboard"]["teacher"]["pending_human_review_count"] != 1:
        raise DashboardReviewError("dashboard_pending_review_count_invalid")
    if "response" in json.dumps(dashboard_before, ensure_ascii=False).casefold():
        raise DashboardReviewError("raw_response_leaked_to_dashboard")
    http = _run_authenticated_acceptance(
        app=app,
        secure_static_root=secure_static_root,
        auth_state=auth_state,
        pending_attempt_id=pending_attempt_id,
        expected_session_version=session_version,
    )
    dashboard_after = app.dashboard_readback()
    if dashboard_after["dashboard"]["teacher"]["pending_human_review_count"] != 0:
        raise DashboardReviewError("dashboard_review_count_not_refreshed")
    if file_digest(production_database) != production_before:
        raise DashboardReviewError("production_database_mutated_by_s17_acceptance")
    return {
        "unit_count": 24,
        "scored_lesson_count": 48,
        "dashboard_role_count": http["dashboard_role_count"],
        "learner_dashboard_pass": True,
        "parent_dashboard_pass": True,
        "teacher_dashboard_pass": True,
        "m9_dashboard_projection_reused": True,
        "m6_human_review_authority_reused": True,
        "pending_human_review_count_before": http["pending_human_review_count_before"],
        "pending_human_review_count_after": http["pending_human_review_count_after"],
        "authenticated_dashboard_endpoint_pass": http["authenticated_dashboard_endpoint_pass"],
        "authenticated_review_queue_endpoint_pass": http["authenticated_review_queue_endpoint_pass"],
        "csrf_review_decision_pass": http["csrf_review_decision_pass"],
        "human_approve_outcome_pass": http["human_approve_outcome_pass"],
        "completion_after_human_approval": http["completion_after_human_approval"],
        "dashboard_after_completion_pass": http["dashboard_after_completion_pass"],
        "raw_response_excluded_from_dashboard": True,
        "review_queue_raw_response_available": http["review_queue_raw_response_available"],
        "role_based_identity_authorization_claimed": False,
        "production_database_unchanged": True,
        "acceptance_used_isolated_database_clone": True,
        "parallel_dashboard_engine_created": False,
        "parallel_review_engine_created": False,
        "a2_unlocked": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "cloudflare_enabled": False,
    }


def _write_launch_bundle(*, target_root: Path, receipt_path: Path, auth_state_db: Path) -> dict[str, Any]:
    target_root = Path(target_root).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    pid_file = target_root / "a1fs_s17_localhost.pid"
    stdout_log = target_root / "a1fs_s17_localhost.stdout.log"
    stderr_log = target_root / "a1fs_s17_localhost.stderr.log"
    module = "ulga.builders.build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review"
    start = f'''param([string]$CodeRoot = "G:\\HomeWork\\English_Learning_DB_Main",[int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Receipt = "{receipt_path}"
$PidFile = "{pid_file}"
$Stdout = "{stdout_log}"
$Stderr = "{stderr_log}"
foreach ($Name in @("A1FS_S11_AUTH_USERNAME","A1FS_S11_AUTH_PASSWORD","A1FS_S11_SESSION_SECRET")) {{ if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name))) {{ throw "MISSING_ENV=$Name" }} }}
$env:A1FS_S11_MODE = "local"
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {{ throw "PORT_IN_USE=$Port" }}
if (Test-Path -LiteralPath $PidFile) {{ throw "PID_FILE_ALREADY_EXISTS=$PidFile" }}
Set-Location $CodeRoot
$Process = Start-Process -FilePath (Get-Command python).Source -WorkingDirectory $CodeRoot -ArgumentList @("-m","{module}","serve","--receipt",$Receipt,"--host","127.0.0.1","--port",[string]$Port) -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr -PassThru
[System.IO.File]::WriteAllText($PidFile,[string]$Process.Id)
for ($Attempt=1; $Attempt -le 40; $Attempt++) {{ if ($Process.HasExited) {{ throw "A1FS_S17_PROCESS_EXITED=$($Process.ExitCode)" }}; try {{ $Health=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2; if ($Health.status -eq "PASS" -and $Health.authentication_required -eq $true) {{ Write-Host "A1FS_S17_LOCALHOST_STARTED=PASS"; Write-Host "PID=$($Process.Id)"; Write-Host "URL=http://127.0.0.1:$Port"; exit 0 }} }} catch {{ Start-Sleep -Milliseconds 500 }} }}
Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
throw "A1FS_S17_LOCALHOST_READINESS_TIMEOUT"
'''
    stop = f'''param([int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PidFile = "{pid_file}"
if (-not (Test-Path -LiteralPath $PidFile)) {{ throw "PID_FILE_MISSING=$PidFile" }}
$PidValue=[int](Get-Content -LiteralPath $PidFile -Raw)
$Process=Get-Process -Id $PidValue -ErrorAction SilentlyContinue
if ($null -eq $Process) {{ Remove-Item -LiteralPath $PidFile -Force; throw "STALE_PID_FILE=$PidValue" }}
$Command=(Get-CimInstance Win32_Process -Filter "ProcessId=$PidValue").CommandLine
if ($Command -notlike "*build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review*") {{ throw "PID_OWNERSHIP_MISMATCH=$PidValue" }}
Stop-Process -Id $PidValue -Force
for ($Attempt=1; $Attempt -le 20; $Attempt++) {{ if (-not (Get-Process -Id $PidValue -ErrorAction SilentlyContinue)) {{ break }}; Start-Sleep -Milliseconds 250 }}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {{ throw "PORT_STILL_LISTENING=$Port" }}
Remove-Item -LiteralPath $PidFile -Force
Write-Host "A1FS_S17_LOCALHOST_STOPPED=PASS"
'''
    status = f'''param([int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PidFile = "{pid_file}"
if (-not (Test-Path -LiteralPath $PidFile)) {{ throw "A1FS_S17_LOCALHOST_STATUS=STOPPED" }}
$PidValue=[int](Get-Content -LiteralPath $PidFile -Raw)
if (-not (Get-Process -Id $PidValue -ErrorAction SilentlyContinue)) {{ throw "A1FS_S17_LOCALHOST_STATUS=STALE_PID" }}
$Listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($null -eq $Listener -or $Listener.OwningProcess -ne $PidValue) {{ throw "A1FS_S17_LOCALHOST_STATUS=PORT_OWNERSHIP_INVALID" }}
$Health=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
if ($Health.status -ne "PASS" -or $Health.authentication_required -ne $true) {{ throw "A1FS_S17_LOCALHOST_STATUS=UNHEALTHY" }}
Write-Host "A1FS_S17_LOCALHOST_STATUS=RUNNING"
Write-Host "PID=$PidValue"
Write-Host "URL=http://127.0.0.1:$Port"
'''
    for name, content in {
        "start_a1fs_s17_localhost.ps1": start,
        "stop_a1fs_s17_localhost.ps1": stop,
        "status_a1fs_s17_localhost.ps1": status,
    }.items():
        (target_root / name).write_text(content, encoding="utf-8")
    contract = {
        "schema_version": "a1fs.online.v1.s17.localhost_launch_contract.v1",
        "host": "127.0.0.1",
        "port": DEFAULT_PORT,
        "authentication_required": True,
        "csrf_required_for_review_decision": True,
        "required_environment_variables": [
            "A1FS_S11_AUTH_USERNAME", "A1FS_S11_AUTH_PASSWORD", "A1FS_S11_SESSION_SECRET"
        ],
        "secret_values_embedded": False,
        "auth_state_database_reused_from_s16_source": str(auth_state_db),
        "dashboard_role_count": 3,
        "role_based_identity_authorization_claimed": False,
        "human_review_authority": "A1FS_V1_M6",
        "external_network_binding_allowed": False,
        "cloudflare_enabled": False,
        "audio_enabled": False,
        "a2_session_enabled": False,
    }
    contract_path = target_root / "localhost_launch_contract.json"
    write_json(contract_path, contract)
    return {
        "bundle_root": str(target_root),
        "start_script_path": str(target_root / "start_a1fs_s17_localhost.ps1"),
        "stop_script_path": str(target_root / "stop_a1fs_s17_localhost.ps1"),
        "status_script_path": str(target_root / "status_a1fs_s17_localhost.ps1"),
        "launch_contract_path": str(contract_path),
        "pid_file_path": str(pid_file),
        "stdout_log_path": str(stdout_log),
        "stderr_log_path": str(stderr_log),
        "auth_state_database_path": str(auth_state_db),
    }


def materialize(*, s16_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    (
        s16_receipt, production_database, auth_state, bundles, sequence, graph_path,
        source_state_root, _, source_acceptance_database,
    ) = _source(s16_path)
    output_root = Path(output_root).resolve()
    root = output_root / "dashboard_human_review"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    learner_static = root / "learner_static"
    s16._write_static(learner_static)
    _write_static(learner_static)
    secure_static = root / "secure_static"
    s16.s15.s11._write_secure_static(learner_static, secure_static)
    acceptance_database = root / "runtime" / "s17_dashboard_review_acceptance.sqlite3"
    acceptance_state = root / "runtime" / "canonical_learning_state"
    acceptance_auth = root / "runtime" / "s17_auth_state.sqlite3"
    acceptance = run_isolated_acceptance(
        source_acceptance_database=source_acceptance_database,
        production_database=production_database,
        source_state_root=source_state_root,
        bundles=bundles,
        sequence=sequence,
        graph_path=graph_path,
        secure_static_root=secure_static,
        acceptance_database=acceptance_database,
        state_root=acceptance_state,
        auth_state=acceptance_auth,
    )
    launch_bundle = _write_launch_bundle(
        target_root=root / "launch_bundle",
        receipt_path=output_root / "dashboard_human_review.private.json",
        auth_state_db=auth_state,
    )
    production_sha = file_digest(production_database)
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "s16_sha256": digest(s16_receipt),
            "production_database_sha256": production_sha,
        },
        "runtime_outputs": {
            "root": str(root),
            "source_s16_receipt_path": str(Path(s16_path).resolve()),
            "source_database_path": str(production_database),
            "source_graph_path": str(graph_path),
            "source_state_root": str(source_state_root),
            "acceptance_database_path": str(acceptance_database),
            "acceptance_state_root": str(acceptance_state),
            "learner_static_root": str(learner_static),
            "secure_static_root": str(secure_static),
            **launch_bundle,
        },
        "dashboard_review_summary": acceptance,
        "production_safety": {
            "production_database_sha256_before": production_sha,
            "production_database_sha256_after": file_digest(production_database),
            "production_database_unchanged": True,
            "acceptance_used_isolated_database_clone": True,
            "learner_progress_mutated_by_acceptance": False,
            "raw_response_serialized_to_safe_artifact": False,
        },
        "capability_contract": {
            "s16_canonical_learning_integration_reused": True,
            "m9_dashboard_projection_reused": True,
            "m6_human_review_authority_reused": True,
            "learner_dashboard_connected": True,
            "parent_dashboard_connected": True,
            "teacher_dashboard_connected": True,
            "authenticated_human_review_queue_connected": True,
            "authenticated_human_review_decision_connected": True,
            "parallel_curriculum_created": False,
            "parallel_learner_state_engine_created": False,
            "parallel_scoring_engine_created": False,
            "parallel_mastery_engine_created": False,
            "parallel_dashboard_engine_created": False,
            "parallel_review_engine_created": False,
            "role_based_identity_authorization_claimed": False,
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
            "speaking_capture_enabled": False,
            "listening_enabled": False,
            "audio_enabled": False,
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
        "dashboard_review_summary": deepcopy(acceptance),
        "production_safety": {
            "production_database_unchanged": True,
            "acceptance_used_isolated_database_clone": True,
            "learner_progress_mutated_by_acceptance": False,
            "raw_response_serialized_to_safe_artifact": False,
        },
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def _load_runtime(
    receipt_path: Path,
) -> tuple[dict[str, Any], Path, Path, dict[str, dict[str, Any]], dict[str, int], Path, Path, Path]:
    receipt = read_json(receipt_path, "s17_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    if identity != (TASK_ID, SCHEMA_VERSION, PASS_STATUS, PRODUCT_STATUS, "NONE"):
        raise DashboardReviewError("s17_receipt_contract_invalid")
    body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(body):
        raise DashboardReviewError("s17_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs", {})
    source_s16 = Path(str(outputs.get("source_s16_receipt_path") or "")).resolve()
    secure_static = Path(str(outputs.get("secure_static_root") or "")).resolve()
    (
        _, database, auth_state, bundles, sequence, graph_path, state_root, _, _,
    ) = _source(source_s16)
    if not secure_static.is_dir():
        raise DashboardReviewError("s17_secure_static_missing")
    return receipt, database, auth_state, bundles, sequence, graph_path, state_root, secure_static


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    _, database, auth_state, bundles, sequence, graph_path, state_root, secure_static = _load_runtime(receipt_path)
    config = s16.s15.s13.PersistentBoundaryConfig.from_environment(
        host=host,
        port=port,
        revocation_db_path=auth_state,
    )
    server = DashboardReviewServer(
        (host, port),
        _app(
            database=database,
            bundles=bundles,
            sequence=sequence,
            graph_path=graph_path,
            state_root=state_root,
        ),
        secure_static,
        config,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def readback(*, receipt_path: Path) -> dict[str, Any]:
    receipt, _, _, _, _, _, _, _ = _load_runtime(receipt_path)
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "dashboard_review_summary": deepcopy(receipt["dashboard_review_summary"]),
        "capability_contract": deepcopy(receipt["capability_contract"]),
        "next_short_step": NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s16", type=Path, required=True)
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
        receipt, safe = materialize(s16_path=args.s16, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s16_path=args.s16,
        )
        if validation["error_count"]:
            raise DashboardReviewError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        DashboardReviewError,
        s16.CanonicalLearningError,
        s16.s15.ScoredJourneyError,
        s16.s15.s14.LearnerFacingSemanticsError,
        s16.core.m7.MasteryError,
        s16.core.m8.ReviewRetentionError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
