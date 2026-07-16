#!/usr/bin/env python3
"""Independently validate private A1FS V1 M11 non-audio human-pilot evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

TASK_ID = "A1FS-V1-M11_NonAudioHumanPilotAndEvidenceReview"
SCHEMA_VERSION = "a1fs.v1.m11.non_audio_human_pilot.v1"
READY_STATUS = "READY_A1FS_V1_M11_NON_AUDIO_HUMAN_PILOT_EVIDENCE_REVIEW"
PASS_STATUS = "PASS_A1FS_V1_M11_NON_AUDIO_HUMAN_PILOT"
GRAPH_STATUS = "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE"
M7_STATUS = "PASS_A1FS_V1_M7_MASTERY_REMEDIATION_REASSESSMENT"
M8_STATUS = "PASS_A1FS_V1_M8_REVIEW_SCHEDULING_RETENTION_SPACED_PRACTICE"
M9_STATUS = "PASS_A1FS_V1_M9_TEACHER_DASHBOARD_PROGRESS_REPORTING_EXPORT"
NEXT_PASS_STEP = "A1FS-V1-M12_V1AcceptanceCloseoutAndDeferredAudioBacklog"
ALLOWED_SKILLS = {"READING", "WRITING"}
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
FAIL_OUTCOMES = {"AUTO_FAIL", "HUMAN_REJECT"}
RESOLVED_OUTCOMES = PASS_OUTCOMES | FAIL_OUTCOMES
REQUIRED_ATTESTATIONS = {
    "real_learner_participated",
    "facilitator_observed",
    "learner_ui_used",
    "raw_response_not_exported",
    "audio_deferred",
    "speaking_recording_deferred",
    "privacy_review_completed",
}
FORBIDDEN_EVIDENCE_KEYS = {
    "response",
    "response_json",
    "prompt",
    "answer",
    "accepted_texts",
    "accepted_sequence",
    "recording",
    "stored_path",
    "media_root",
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_at(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone_required")
    return parsed.astimezone(timezone.utc)


def load(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = Path(path).read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("json_not_object")
    return value, raw


def walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.add(str(key).casefold())
            keys |= walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            keys |= walk_keys(child)
    return keys


def validate(
    database_path: Path,
    graph_path: Path,
    m7_snapshot_path: Path,
    m8_snapshot_path: Path,
    m9_report_path: Path,
    package_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        graph, graph_raw = load(graph_path)
        m7, _ = load(m7_snapshot_path)
        m8, _ = load(m8_snapshot_path)
        m9, _ = load(m9_report_path)
        package, _ = load(package_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"source_unreadable:{exc}"]}
    graph_sha = digest(graph_raw)
    if graph.get("validation_status") != GRAPH_STATUS:
        errors.append("graph_status_invalid")
    if m7.get("validation_status") != M7_STATUS or m8.get("validation_status") != M8_STATUS:
        errors.append("mastery_or_retention_status_invalid")
    if m9.get("validation_status") != M9_STATUS:
        errors.append("dashboard_status_invalid")
    if package.get("task_id") != TASK_ID or package.get("schema_version") != SCHEMA_VERSION or package.get("validation_status") != PASS_STATUS:
        errors.append("package_identity_invalid")
    expected_bindings = {
        "graph_sha256": graph_sha,
        "m7_snapshot_digest": digest(m7),
        "m8_snapshot_digest": digest(m8),
        "m9_report_digest": digest(m9),
    }
    if package.get("source_bindings") != expected_bindings:
        errors.append("package_source_binding_invalid")
    if m7.get("source_graph_sha256") != graph_sha or m8.get("source_graph_sha256") != graph_sha:
        errors.append("snapshot_graph_binding_invalid")
    if m8.get("source_m7_snapshot_digest") != digest(m7):
        errors.append("m8_m7_binding_invalid")
    if m9.get("source_bindings") != {
        "graph_sha256": graph_sha,
        "m7_snapshot_digest": digest(m7),
        "m8_snapshot_digest": digest(m8),
    }:
        errors.append("m9_binding_invalid")
    boundaries = package.get("claim_boundaries", {})
    expected_boundaries = {
        "non_audio_human_pilot_claimed": True,
        "four_skill_human_pilot_claimed": False,
        "listening_audio_complete": False,
        "speaking_recording_complete": False,
        "audio_deferred": True,
        "a2_unlocked": False,
        "public_delivery": False,
        "raw_response_exported": False,
    }
    if boundaries != expected_boundaries:
        errors.append("claim_boundaries_invalid")
    workflow = package.get("workflow_evidence", {})
    expected_workflow = {
        "learner_ui_used": True,
        "response_capture_verified": True,
        "resolved_scoring_verified": True,
        "writing_human_review_verified": True,
        "mastery_snapshot_refreshed": True,
        "review_retention_snapshot_refreshed": True,
        "teacher_dashboard_refreshed": True,
        "audio_evidence_used": False,
        "speaking_recording_used": False,
    }
    if workflow != expected_workflow:
        errors.append("workflow_evidence_invalid")
    attestations = package.get("operator_attestations", {})
    if set(attestations) != REQUIRED_ATTESTATIONS or any(attestations.get(key) is not True for key in REQUIRED_ATTESTATIONS):
        errors.append("operator_attestations_invalid")
    if walk_keys(package) & FORBIDDEN_EVIDENCE_KEYS:
        errors.append("raw_or_media_evidence_leaked")
    if package.get("private_local_only") is not True or package.get("pilot_mode") != "NON_AUDIO_READING_WRITING":
        errors.append("pilot_mode_invalid")
    if package.get("next_short_step") != NEXT_PASS_STEP:
        errors.append("next_short_step_invalid")
    try:
        started = parse_at(package["started_at"])
        ended = parse_at(package["ended_at"])
        recorded = parse_at(package["recorded_at"])
        if not 120 <= (ended - started).total_seconds() <= 4 * 60 * 60 or recorded < ended:
            errors.append("pilot_timing_invalid")
    except (KeyError, AttributeError, ValueError):
        started = ended = recorded = datetime.min.replace(tzinfo=timezone.utc)
        errors.append("pilot_timing_unreadable")
    try:
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error as exc:
        connection = None
        errors.append(f"database_unreadable:{exc}")
    if connection:
        try:
            m11_meta = dict(connection.execute("SELECT key,value FROM m11_metadata"))
            if m11_meta.get("validation_status") != READY_STATUS:
                errors.append("m11_metadata_status_invalid")
            if any(
                m11_meta.get(db_key) != expected_bindings[package_key]
                for db_key, package_key in (
                    ("source_graph_sha256", "graph_sha256"),
                    ("source_m7_snapshot_digest", "m7_snapshot_digest"),
                    ("source_m8_snapshot_digest", "m8_snapshot_digest"),
                    ("source_m9_report_digest", "m9_report_digest"),
                )
            ):
                errors.append("m11_metadata_binding_invalid")
            stored = connection.execute(
                "SELECT * FROM non_audio_human_pilot_runs WHERE pilot_id=?",
                (package.get("pilot_id"),),
            ).fetchone()
            if not stored or stored["package_digest"] != digest(package):
                errors.append("pilot_package_not_persisted")
            learner_id = stored["learner_id"] if stored else None
            if learner_id:
                refresh_rows = (
                    (
                        "m7_snapshot_not_refreshed_after_pilot",
                        connection.execute(
                            "SELECT created_at AS refreshed_at FROM mastery_snapshots WHERE learner_id=? AND snapshot_digest=?",
                            (learner_id, digest(m7)),
                        ).fetchone(),
                    ),
                    (
                        "m8_snapshot_not_refreshed_after_pilot",
                        connection.execute(
                            "SELECT created_at AS refreshed_at FROM retention_snapshots WHERE learner_id=? AND snapshot_digest=?",
                            (learner_id, digest(m8)),
                        ).fetchone(),
                    ),
                    (
                        "m9_report_not_refreshed_after_pilot",
                        connection.execute(
                            "SELECT exported_at AS refreshed_at FROM dashboard_exports WHERE learner_id=? AND report_digest=?",
                            (learner_id, digest(m9)),
                        ).fetchone(),
                    ),
                )
                for code, row in refresh_rows:
                    try:
                        if not row or parse_at(row["refreshed_at"]) < ended:
                            errors.append(code)
                    except (AttributeError, ValueError):
                        errors.append(code)
            if learner_id != m7.get("learner_id") or package.get("subject_key") != (stored["subject_key"] if stored else None):
                errors.append("pilot_subject_binding_invalid")
            session_evidence = package.get("session_evidence", [])
            session_ids = [row.get("session_id") for row in session_evidence if isinstance(row, dict)]
            if len(session_ids) < 2 or len(session_ids) != len(set(session_ids)):
                errors.append("session_evidence_identity_invalid")
            if stored and json.loads(stored["session_ids_json"]) != sorted(session_ids):
                errors.append("stored_session_ids_mismatch")
            if session_ids:
                placeholders = ",".join("?" for _ in session_ids)
                sessions = {
                    row["session_id"]: dict(row)
                    for row in connection.execute(
                        f"""SELECT session_id,lesson_id,skill,level,session_state,started_at,ended_at
                        FROM learning_sessions WHERE learner_id=? AND session_id IN({placeholders})""",
                        (learner_id, *session_ids),
                    )
                }
                if set(sessions) != set(session_ids):
                    errors.append("database_session_set_mismatch")
                session_by_id = {row.get("session_id"): row for row in session_evidence if isinstance(row, dict)}
                for session_id, row in sessions.items():
                    package_row = session_by_id.get(session_id, {})
                    projected = {key: row[key] for key in ("session_id", "lesson_id", "skill", "level", "started_at", "ended_at")}
                    if any(package_row.get(key) != value for key, value in projected.items()):
                        errors.append(f"session_projection_mismatch:{session_id}")
                    if row["session_state"] != "COMPLETED" or row["skill"] not in ALLOWED_SKILLS or row["level"] not in {"A1", "A1+"}:
                        errors.append(f"session_scope_invalid:{session_id}")
                    try:
                        if parse_at(row["started_at"]) < started or parse_at(row["ended_at"]) > ended:
                            errors.append(f"session_timing_invalid:{session_id}")
                    except (AttributeError, ValueError):
                        errors.append(f"session_timing_unreadable:{session_id}")
                if {row["skill"] for row in sessions.values()} != ALLOWED_SKILLS:
                    errors.append("reading_writing_denominator_invalid")
                attempts = [
                    dict(row)
                    for row in connection.execute(
                        f"""SELECT a.session_id,c.skill,s.scoring_mode,s.outcome,s.human_review_required,q.decision
                        FROM response_attempts a JOIN response_contracts c USING(asset_key)
                        JOIN scoring_results s USING(attempt_id) JOIN human_review_queue q USING(attempt_id)
                        WHERE a.learner_id=? AND a.session_id IN({placeholders})""",
                        (learner_id, *session_ids),
                    )
                ]
                if any(row["outcome"] not in RESOLVED_OUTCOMES for row in attempts):
                    errors.append("unresolved_attempt_present")
                counts = {
                    "completed_session_count": len(sessions),
                    "reading_session_count": sum(row["skill"] == "READING" for row in sessions.values()),
                    "writing_session_count": sum(row["skill"] == "WRITING" for row in sessions.values()),
                    "attempt_count": len(attempts),
                    "resolved_attempt_count": len(attempts),
                    "pass_count": sum(row["outcome"] in PASS_OUTCOMES for row in attempts),
                    "fail_count": sum(row["outcome"] in FAIL_OUTCOMES for row in attempts),
                    "resolved_human_review_count": sum(
                        row["skill"] == "WRITING"
                        and row["scoring_mode"] == "FEATURE_RUBRIC"
                        and row["human_review_required"] == 1
                        and row["outcome"] in {"HUMAN_APPROVE", "HUMAN_REJECT"}
                        and row["decision"] in {"APPROVE", "REJECT"}
                        for row in attempts
                    ),
                }
                if package.get("outcome_summary") != counts:
                    errors.append("outcome_summary_mismatch")
                if counts["pass_count"] < 1 or counts["resolved_human_review_count"] < 1:
                    errors.append("required_pilot_outcome_missing")
                report_rows = {row.get("skill"): row for row in m9.get("four_skill_progress", []) if isinstance(row, dict)}
                for skill in ALLOWED_SKILLS:
                    selected_session_count = sum(row["skill"] == skill for row in sessions.values())
                    selected_attempt_count = sum(row["skill"] == skill for row in attempts)
                    report_row = report_rows.get(skill, {})
                    if int(report_row.get("completed_session_count", 0)) < selected_session_count:
                        errors.append(f"m9_completed_session_count_stale:{skill}")
                    if int(report_row.get("attempt_count", 0)) < selected_attempt_count:
                        errors.append(f"m9_attempt_count_stale:{skill}")
                for session_id in session_ids:
                    package_row = session_by_id[session_id]
                    rows = [row for row in attempts if row["session_id"] == session_id]
                    expected_counts = {
                        "attempt_count": len(rows),
                        "pass_count": sum(row["outcome"] in PASS_OUTCOMES for row in rows),
                        "fail_count": sum(row["outcome"] in FAIL_OUTCOMES for row in rows),
                        "resolved_human_review_count": sum(
                            row["outcome"] in {"HUMAN_APPROVE", "HUMAN_REJECT"} for row in rows
                        ),
                    }
                    if any(package_row.get(key) != value for key, value in expected_counts.items()):
                        errors.append(f"session_attempt_counts_mismatch:{session_id}")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                errors.append("sqlite_integrity_failed")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                errors.append("foreign_key_check_failed")
        except (sqlite3.Error, KeyError, TypeError, json.JSONDecodeError) as exc:
            errors.append(f"database_validation_error:{exc}")
        finally:
            connection.close()
    return {
        "validation_status": PASS_STATUS if not errors else "FAIL_A1FS_V1_M11_NON_AUDIO_HUMAN_PILOT_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "pilot_id": package.get("pilot_id"),
        "four_skill_human_pilot_claimed": False,
        "audio_deferred": True,
        "next_short_step": NEXT_PASS_STEP if not errors else TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--m7-snapshot", type=Path, required=True)
    parser.add_argument("--m8-snapshot", type=Path, required=True)
    parser.add_argument("--m9-report", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    report = validate(
        args.database,
        args.graph,
        args.m7_snapshot,
        args.m8_snapshot,
        args.m9_report,
        args.package,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
