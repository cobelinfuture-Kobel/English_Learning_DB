#!/usr/bin/env python3
"""Validate A1FS V1 M9 private report projections and privacy boundaries."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-M9_TeacherDashboardProgressReportingAndExport"
STATUS = "PASS_A1FS_V1_M9_TEACHER_DASHBOARD_PROGRESS_REPORTING_EXPORT"
SKILLS = ("LISTENING", "SPEAKING", "READING", "WRITING")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode() if isinstance(value, str) else canonical(value).encode()
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    value = json.loads(raw)
    return value, raw


def skill_rows(connection: sqlite3.Connection, learner_id: str) -> list[dict[str, Any]]:
    sessions = {
        row["skill"]: dict(row)
        for row in connection.execute(
            "SELECT skill,COUNT(*) session_count,SUM(session_state='COMPLETED') completed_session_count FROM learning_sessions WHERE learner_id=? GROUP BY skill",
            (learner_id,),
        )
    }
    attempts = {
        row["skill"]: dict(row)
        for row in connection.execute(
            """SELECT c.skill,COUNT(*) attempt_count,
            SUM(s.outcome IN('AUTO_PASS','HUMAN_APPROVE')) pass_count,
            SUM(s.outcome IN('AUTO_FAIL','HUMAN_REJECT')) fail_count,
            SUM(s.outcome IN('PENDING_HUMAN_REVIEW','HUMAN_DEFER')) pending_review_count
            FROM response_attempts a JOIN response_contracts c USING(asset_key)
            JOIN scoring_results s USING(attempt_id)
            WHERE a.learner_id=? GROUP BY c.skill""",
            (learner_id,),
        )
    }
    result = []
    for skill in SKILLS:
        session = sessions.get(skill, {})
        attempt = attempts.get(skill, {})
        passed = int(attempt.get("pass_count") or 0)
        failed = int(attempt.get("fail_count") or 0)
        result.append(
            {
                "skill": skill,
                "session_count": int(session.get("session_count") or 0),
                "completed_session_count": int(session.get("completed_session_count") or 0),
                "attempt_count": int(attempt.get("attempt_count") or 0),
                "pass_count": passed,
                "fail_count": failed,
                "pending_review_count": int(attempt.get("pending_review_count") or 0),
                "resolved_pass_rate": round(passed / max(1, passed + failed), 6),
            }
        )
    return result


def validate(
    database: Path,
    graph_path: Path,
    m7_path: Path,
    m8_path: Path,
    report_path: Path,
    html_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        _, graph_raw = load(graph_path)
        m7, _ = load(m7_path)
        m8, _ = load(m8_path)
        report, _ = load(report_path)
        html_text = html_path.read_text()
    except Exception as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"source_unreadable:{exc}"]}
    if report.get("task_id") != TASK_ID or report.get("validation_status") != STATUS:
        errors.append("report_identity_invalid")
    expected_bindings = {
        "graph_sha256": digest(graph_raw),
        "m7_snapshot_digest": digest(m7),
        "m8_snapshot_digest": digest(m8),
    }
    if report.get("source_bindings") != expected_bindings:
        errors.append("source_binding_invalid")
    expected_privacy = {
        "raw_response_text_exported": False,
        "prompt_text_exported": False,
        "public_delivery": False,
        "human_pilot_claimed": False,
    }
    if report.get("privacy_boundaries") != expected_privacy:
        errors.append("privacy_boundary_invalid")
    safe_projection = dict(report)
    safe_projection.pop("privacy_boundaries", None)
    serialized = canonical(safe_projection).casefold()
    for forbidden in ("response_json", "student_response", "raw_response", "prompt_text"):
        if forbidden in serialized:
            errors.append(f"forbidden_report_field:{forbidden}")
    if re.search(r"<script|https?://|fetch\(|xmlhttprequest", html_text, re.I):
        errors.append("html_not_static_or_network_free")
    try:
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
    except sqlite3.Error as exc:
        connection = None
        errors.append(f"database_unreadable:{exc}")
    if connection:
        learner_id = report.get("learner", {}).get("learner_id")
        if report.get("four_skill_progress") != skill_rows(connection, learner_id):
            errors.append("four_skill_projection_drift")
        pending = connection.execute(
            """SELECT COUNT(*) FROM response_attempts a JOIN scoring_results s USING(attempt_id)
            WHERE a.learner_id=? AND s.outcome IN('PENDING_HUMAN_REVIEW','HUMAN_DEFER')""",
            (learner_id,),
        ).fetchone()[0]
        if report.get("human_review", {}).get("pending_count") != pending:
            errors.append("human_review_count_drift")
        metadata = dict(connection.execute("SELECT key,value FROM m9_metadata"))
        if metadata.get("validation_status") != STATUS or metadata.get("source_m8_snapshot_digest") != digest(m8):
            errors.append("m9_metadata_invalid")
        stored = connection.execute(
            "SELECT 1 FROM dashboard_exports WHERE learner_id=? AND report_digest=? AND html_digest=?",
            (learner_id, digest(report), digest(html_text)),
        ).fetchone()
        if not stored:
            errors.append("export_receipt_missing")
        connection.close()
    if report.get("mastery", {}).get("mastered_required_count") != m7.get("mastered_required_count"):
        errors.append("mastery_projection_drift")
    if report.get("retention", {}).get("retained_required_count") != m8.get("retained_required_count"):
        errors.append("retention_projection_drift")
    if report.get("a2_lock", {}).get("payload_access_granted") is not False:
        errors.append("a2_boundary_broken")
    if report.get("a2_lock", {}).get("session_start_granted") is not False:
        errors.append("a2_boundary_broken")
    return {
        "validation_status": STATUS if not errors else "FAIL_A1FS_V1_M9_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "next_short_step": report.get("next_short_step") if not errors else TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--m7-snapshot", type=Path, required=True)
    parser.add_argument("--m8-snapshot", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--html", type=Path, required=True)
    args = parser.parse_args()
    report = validate(
        args.database,
        args.graph,
        args.m7_snapshot,
        args.m8_snapshot,
        args.report,
        args.html,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["error_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
