#!/usr/bin/env python3
"""Independent validator for the R5 local edge runtime and evidence collector."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_r1_evidence_validity_system_error_governance as r1
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5

TABLES = {
    "r5_metadata", "edge_runtime_items", "edge_cell_supply", "edge_sessions",
    "edge_assignments", "edge_attempts", "edge_scoring_results", "edge_review_queue",
    "edge_validity_events", "edge_runtime_events", "edge_exports",
}
SAFE_FORBIDDEN_KEYS = {
    "response", "prompt", "context", "options", "supplied_tokens", "supplied_morphemes",
    "gap_display_tokens", "word_bank", "accepted_texts", "accepted_sequence", "model_texts",
    "private_scoring_contract", "learner_contract", "operator_review", "reviewer_id", "notes",
}


def _safe_scan(value: Any, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in SAFE_FORBIDDEN_KEYS:
                errors.append(f"safe_private_field:{key}")
            _safe_scan(child, errors)
    elif isinstance(value, list):
        for child in value:
            _safe_scan(child, errors)
    elif isinstance(value, str):
        if Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":/", ":\\"}):
            errors.append("safe_absolute_path")


def _attempt_chain(connection: sqlite3.Connection, errors: list[str]) -> None:
    previous = "0" * 64
    for row in connection.execute("SELECT * FROM edge_attempts ORDER BY rowid"):
        try:
            response = json.loads(row["response_json"])
        except json.JSONDecodeError:
            errors.append(f"attempt_response_invalid:{row['attempt_id']}"); continue
        core = {
            "attempt_id": row["attempt_id"], "session_id": row["session_id"],
            "learner_id": row["learner_id"], "item_id": row["item_id"],
            "response": response, "response_time_ms": row["response_time_ms"],
            "hint_count": row["hint_count"], "revision_count": row["revision_count"],
            "submitted_at": row["submitted_at"],
        }
        if row["previous_hash"] != previous:
            errors.append(f"attempt_previous_hash_invalid:{row['attempt_id']}")
        calculated = r5.digest(previous + r5.canonical(core))
        if row["attempt_hash"] != calculated:
            errors.append(f"attempt_hash_invalid:{row['attempt_id']}")
        previous = row["attempt_hash"]


def _runtime_event_chain(connection: sqlite3.Connection, errors: list[str]) -> None:
    previous = "0" * 64
    for row in connection.execute("SELECT * FROM edge_runtime_events ORDER BY event_seq"):
        try:
            payload = json.loads(row["payload_json"])
        except json.JSONDecodeError:
            errors.append(f"runtime_event_payload_invalid:{row['event_id']}"); continue
        core = {
            "event_id": row["event_id"], "learner_id": row["learner_id"],
            "session_id": row["session_id"], "event_type": row["event_type"],
            "event_at": row["event_at"], "payload": payload,
        }
        if row["previous_hash"] != previous:
            errors.append(f"runtime_event_previous_hash_invalid:{row['event_id']}")
        calculated = r5.digest(previous + r5.canonical(core))
        if row["event_hash"] != calculated:
            errors.append(f"runtime_event_hash_invalid:{row['event_id']}")
        previous = row["event_hash"]


def _validity_event_chain(connection: sqlite3.Connection, errors: list[str]) -> None:
    previous = "0" * 64
    latest: dict[str, str] = {}
    for row in connection.execute("SELECT * FROM edge_validity_events ORDER BY event_seq"):
        try:
            detail = json.loads(row["detail_json"])
        except json.JSONDecodeError:
            errors.append(f"validity_detail_invalid:{row['event_id']}"); continue
        core = {
            "event_id": row["event_id"], "attempt_id": row["attempt_id"],
            "previous_status": row["previous_status"], "new_status": row["new_status"],
            "reason_code": row["reason_code"], "detail": detail,
            "actor_id": row["actor_id"], "occurred_at": row["occurred_at"],
        }
        if row["previous_hash"] != previous:
            errors.append(f"validity_previous_hash_invalid:{row['event_id']}")
        calculated = r5.digest(previous + r5.canonical(core))
        if row["event_hash"] != calculated:
            errors.append(f"validity_event_hash_invalid:{row['event_id']}")
        previous = row["event_hash"]
        latest[row["attempt_id"]] = row["new_status"]
    for attempt_id, status in latest.items():
        projected = connection.execute("SELECT validity_status FROM edge_attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
        if not projected or projected[0] != status:
            errors.append(f"validity_projection_invalid:{attempt_id}")


def validate_database(database_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"database_unreadable:{exc}"]}
    with connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            errors.append("sqlite_integrity_failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            errors.append("foreign_key_check_failed")
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = TABLES - names
        for name in sorted(missing):
            errors.append(f"table_missing:{name}")
        if missing:
            connection.close()
            return {"validation_status": "FAIL", "error_count": len(errors), "errors": errors}
        metadata = dict(connection.execute("SELECT key,value FROM r5_metadata"))
        if metadata.get("task_id") != r5.TASK_ID or metadata.get("schema_version") != r5.SCHEMA_VERSION:
            errors.append("metadata_identity_invalid")
        if metadata.get("validation_status") != r5.STATUS:
            errors.append("metadata_status_invalid")
        for key in ("qwen_required", "network_submission_enabled", "mastery_write_enabled", "a2_session_enabled"):
            if metadata.get(key) != "false":
                errors.append(f"metadata_boundary_broken:{key}")
        items = {row["item_id"]: row for row in connection.execute("SELECT * FROM edge_runtime_items")}
        for item_id, row in items.items():
            try:
                item = json.loads(row["item_json"])
            except json.JSONDecodeError:
                errors.append(f"item_json_invalid:{item_id}"); continue
            if r5.digest(item) != row["item_digest"]:
                errors.append(f"item_digest_invalid:{item_id}")
            if item.get("admission", {}).get("status") != "APPROVED" or row["admission_status"] != "APPROVED":
                errors.append(f"item_not_admitted:{item_id}")
            if row["level"] not in {"A1", "A1_PLUS"}:
                errors.append(f"a2_item_present:{item_id}")
        open_sessions = Counter(row["learner_id"] for row in connection.execute("SELECT learner_id FROM edge_sessions WHERE session_state IN('ACTIVE','PAUSED')"))
        if any(count > 1 for count in open_sessions.values()):
            errors.append("multiple_open_sessions_per_learner")
        for session in connection.execute("SELECT * FROM edge_sessions"):
            assignment_count = connection.execute("SELECT COUNT(*) FROM edge_assignments WHERE session_id=?", (session["session_id"],)).fetchone()[0]
            if assignment_count != session["planned_item_count"]:
                errors.append(f"session_assignment_count_invalid:{session['session_id']}")
            if session["session_state"] == "COMPLETED":
                incomplete = connection.execute("SELECT COUNT(*) FROM edge_assignments WHERE session_id=? AND assignment_state!='SUBMITTED'", (session["session_id"],)).fetchone()[0]
                unresolved = connection.execute("SELECT COUNT(*) FROM edge_attempts a JOIN edge_scoring_results s USING(attempt_id) WHERE a.session_id=? AND s.outcome IN('PENDING_HUMAN_REVIEW','HUMAN_DEFER')", (session["session_id"],)).fetchone()[0]
                if incomplete or unresolved:
                    errors.append(f"completed_session_not_resolved:{session['session_id']}")
        for row in connection.execute("""SELECT a.*,s.scoring_mode,s.outcome,s.score,s.human_review_required,q.decision,i.item_json
            FROM edge_attempts a JOIN edge_scoring_results s USING(attempt_id)
            JOIN edge_review_queue q USING(attempt_id) JOIN edge_runtime_items i USING(item_id)"""):
            item = json.loads(row["item_json"]); scoring = dict(item["private_scoring_contract"])
            scoring.setdefault("case_insensitive", True); scoring.setdefault("punctuation_tolerance", True)
            try:
                expected_outcome, expected_score = m6.ResponseEvidenceStore.score(scoring, json.loads(row["response_json"]))
            except Exception:
                errors.append(f"score_rebuild_failed:{row['attempt_id']}"); continue
            if scoring["scoring_mode"] == "FEATURE_RUBRIC" and row["decision"] != "PENDING":
                expected_outcome = {"APPROVE": "HUMAN_APPROVE", "REJECT": "HUMAN_REJECT", "DEFER": "HUMAN_DEFER"}[row["decision"]]
                expected_score = 1.0 if row["decision"] == "APPROVE" else 0.0 if row["decision"] == "REJECT" else None
            if (row["outcome"], row["score"]) != (expected_outcome, expected_score):
                errors.append(f"score_rebuild_mismatch:{row['attempt_id']}")
            if row["validity_status"] not in r1.VALIDITY_STATUSES:
                errors.append(f"validity_status_invalid:{row['attempt_id']}")
        _attempt_chain(connection, errors)
        _runtime_event_chain(connection, errors)
        _validity_event_chain(connection, errors)
    connection.close()
    return {
        "validation_status": r5.STATUS if not errors else "FAIL_A1FS_V1_R5_RUNTIME_VALIDATION",
        "error_count": len(errors), "errors": errors,
        "next_short_step": r5.NEXT_SHORT_STEP if not errors else r5.TASK_ID,
    }


def validate_exports(package_path: Path, safe_path: Path, jsonl_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        package = r5.read_json(package_path, "package")
        safe = r5.read_json(safe_path, "safe")
        lines = [json.loads(line) for line in Path(jsonl_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError, r5.LocalEdgeRuntimeError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"export_unreadable:{exc}"]}
    package_core = {key: value for key, value in package.items() if key != "package_sha256"}
    safe_core = {key: value for key, value in safe.items() if key != "summary_sha256"}
    if package.get("task_id") != r5.TASK_ID or package.get("schema_version") != r5.PACKAGE_SCHEMA_VERSION:
        errors.append("package_identity_invalid")
    if safe.get("task_id") != r5.TASK_ID or safe.get("schema_version") != r5.SAFE_SCHEMA_VERSION:
        errors.append("safe_identity_invalid")
    if package.get("package_sha256") != r5.digest(package_core):
        errors.append("package_digest_invalid")
    if safe.get("summary_sha256") != r5.digest(safe_core):
        errors.append("safe_digest_invalid")
    if package.get("entries_sha256") != r5.digest(package.get("entries", [])):
        errors.append("package_entries_digest_invalid")
    if safe.get("entries_sha256") != r5.digest(safe.get("entries", [])):
        errors.append("safe_entries_digest_invalid")
    if package.get("attempt_count") != len(package.get("entries", [])) or len(lines) != package.get("attempt_count"):
        errors.append("export_attempt_count_invalid")
    if lines != package.get("entries", []):
        errors.append("jsonl_package_drift")
    if safe.get("attempt_count") != package.get("attempt_count"):
        errors.append("safe_package_count_drift")
    valid_count = sum(row.get("validity_status") == r1.VALID for row in package.get("entries", []))
    if package.get("valid_attempt_count") != valid_count or safe.get("valid_attempt_count") != valid_count:
        errors.append("valid_attempt_count_invalid")
    _safe_scan(safe, errors)
    for boundaries in (package.get("claim_boundaries", {}), safe.get("claim_boundaries", {})):
        for key in ("mastery_written", "retention_confirmed", "gpt_analysis_performed", "qwen_used", "a2_unlocked", "public_delivery"):
            if boundaries.get(key) is not False:
                errors.append(f"claim_boundary_broken:{key}")
    return {
        "validation_status": r5.STATUS if not errors else "FAIL_A1FS_V1_R5_EXPORT_VALIDATION",
        "error_count": len(errors), "errors": errors,
        "attempt_count": package.get("attempt_count"),
        "next_short_step": r5.NEXT_SHORT_STEP if not errors else r5.TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--safe", type=Path)
    parser.add_argument("--jsonl", type=Path)
    args = parser.parse_args()
    database = validate_database(args.database)
    if args.package or args.safe or args.jsonl:
        if not all((args.package, args.safe, args.jsonl)):
            raise SystemExit("package, safe and jsonl must be supplied together")
        exported = validate_exports(args.package, args.safe, args.jsonl)
        result = {
            "validation_status": r5.STATUS if not database["errors"] and not exported["errors"] else "FAIL_A1FS_V1_R5_VALIDATION",
            "error_count": database["error_count"] + exported["error_count"],
            "errors": database["errors"] + exported["errors"],
            "next_short_step": r5.NEXT_SHORT_STEP if not database["errors"] and not exported["errors"] else r5.TASK_ID,
        }
    else:
        result = database
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
