#!/usr/bin/env python3
"""Independent validator for A1FS V1 R1 evidence validity governance."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from ulga.builders import build_a1fs_v1_r1_evidence_validity_system_error_governance as r1


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _attempt_ids(connection: sqlite3.Connection) -> list[str]:
    return [row[0] for row in connection.execute("SELECT attempt_id FROM response_attempts ORDER BY rowid")]


def _validate_attempt_chain(connection: sqlite3.Connection, errors: list[str], prefix: str) -> None:
    previous = "0" * 64
    for row in connection.execute("SELECT * FROM response_attempts ORDER BY rowid"):
        try:
            response = json.loads(row["response_json"])
        except json.JSONDecodeError:
            errors.append(f"{prefix}_response_json_invalid:{row['attempt_id']}")
            continue
        core = {
            "attempt_id": row["attempt_id"],
            "learner_id": row["learner_id"],
            "session_id": row["session_id"],
            "lesson_id": row["lesson_id"],
            "asset_key": row["asset_key"],
            "attempt_sequence": row["attempt_sequence"],
            "response": response,
            "submitted_at": row["submitted_at"],
        }
        if row["previous_hash"] != previous:
            errors.append(f"{prefix}_attempt_previous_hash_mismatch:{row['attempt_id']}")
        calculated = digest(previous + canonical(core))
        if row["attempt_hash"] != calculated:
            errors.append(f"{prefix}_attempt_hash_mismatch:{row['attempt_id']}")
        previous = row["attempt_hash"]


def validate(source_database_path: Path, governed_database_path: Path, report_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"report_unreadable:{exc}"]}
    if not isinstance(report, dict):
        return {"validation_status": "FAIL", "error_count": 1, "errors": ["report_not_object"]}
    report_core = {key: value for key, value in report.items() if key != "report_sha256"}
    if report.get("task_id") != r1.TASK_ID or report.get("schema_version") != r1.SCHEMA_VERSION:
        errors.append("report_identity_invalid")
    if report.get("validation_status") != r1.STATUS:
        errors.append("report_status_invalid")
    if report.get("report_sha256") != digest(report_core):
        errors.append("report_digest_invalid")
    if report.get("source_database_sha256") != file_digest(source_database_path):
        errors.append("source_database_hash_mismatch")
    if report.get("governed_database_sha256") != file_digest(governed_database_path):
        errors.append("governed_database_hash_mismatch")
    boundaries = report.get("claim_boundaries", {})
    for key in (
        "raw_attempts_rewritten",
        "scoring_outcomes_rewritten",
        "mastery_policy_relaxed",
        "canonical_graph_modified",
        "a2_unlocked",
        "qwen_required",
        "audio_population_required",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"claim_boundary_broken:{key}")

    try:
        source = sqlite3.connect(source_database_path)
        source.row_factory = sqlite3.Row
        source.execute("PRAGMA foreign_keys=ON")
        governed = sqlite3.connect(governed_database_path)
        governed.row_factory = sqlite3.Row
        governed.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error as exc:
        return {"validation_status": "FAIL", "error_count": len(errors) + 1, "errors": errors + [f"database_unreadable:{exc}"]}

    with source, governed:
        if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            errors.append("source_integrity_failed")
        if source.execute("PRAGMA foreign_key_check").fetchall():
            errors.append("source_foreign_key_failed")
        if governed.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            errors.append("governed_integrity_failed")
        if governed.execute("PRAGMA foreign_key_check").fetchall():
            errors.append("governed_foreign_key_failed")

        source_names = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for name in ("evidence_validity", "evidence_validity_events"):
            if name not in source_names:
                errors.append(f"source_governance_table_missing:{name}")
        if errors and "evidence_validity" not in source_names:
            source.close(); governed.close()
            return {"validation_status": "FAIL", "error_count": len(errors), "errors": errors}

        source_ids = _attempt_ids(source)
        governed_ids = _attempt_ids(governed)
        projection = source.execute(
            "SELECT attempt_id,validity_status,latest_event_id,reason_code,detail_json,actor_id,updated_at,source_attempt_hash FROM evidence_validity ORDER BY attempt_id"
        ).fetchall()
        if {row["attempt_id"] for row in projection} != set(source_ids):
            errors.append("validity_projection_denominator_invalid")
        invalid_statuses = [row["attempt_id"] for row in projection if row["validity_status"] not in r1.VALIDITY_STATUSES]
        if invalid_statuses:
            errors.append("validity_status_invalid:" + ",".join(invalid_statuses))
        source_hashes = {row["attempt_id"]: row["attempt_hash"] for row in source.execute("SELECT attempt_id,attempt_hash FROM response_attempts")}
        for row in projection:
            if row["source_attempt_hash"] != source_hashes.get(row["attempt_id"]):
                errors.append(f"validity_attempt_hash_drift:{row['attempt_id']}")
            try:
                detail = json.loads(row["detail_json"])
            except json.JSONDecodeError:
                errors.append(f"validity_detail_invalid:{row['attempt_id']}")
            else:
                if not isinstance(detail, dict):
                    errors.append(f"validity_detail_not_object:{row['attempt_id']}")

        previous = "0" * 64
        latest_by_attempt: dict[str, str] = {}
        for row in source.execute("SELECT * FROM evidence_validity_events ORDER BY event_seq"):
            try:
                detail = json.loads(row["detail_json"])
            except json.JSONDecodeError:
                errors.append(f"validity_event_detail_invalid:{row['event_id']}")
                continue
            core = {
                "event_id": row["event_id"],
                "attempt_id": row["attempt_id"],
                "previous_status": row["previous_status"],
                "new_status": row["new_status"],
                "reason_code": row["reason_code"],
                "detail": detail,
                "actor_id": row["actor_id"],
                "occurred_at": row["occurred_at"],
                "source_attempt_hash": row["source_attempt_hash"],
            }
            if row["previous_hash"] != previous:
                errors.append(f"validity_event_previous_hash_mismatch:{row['event_id']}")
            calculated = digest(previous + canonical(core))
            if row["event_hash"] != calculated:
                errors.append(f"validity_event_hash_mismatch:{row['event_id']}")
            previous = row["event_hash"]
            latest_by_attempt[row["attempt_id"]] = row["event_id"]
        for row in projection:
            if row["latest_event_id"] != latest_by_attempt.get(row["attempt_id"]):
                if not (row["validity_status"] == r1.VALID and row["latest_event_id"] is None and row["attempt_id"] not in latest_by_attempt):
                    errors.append(f"validity_projection_event_mismatch:{row['attempt_id']}")

        expected_governed_ids = [
            attempt_id for attempt_id in source_ids
            if next(row for row in projection if row["attempt_id"] == attempt_id)["validity_status"] == r1.VALID
        ]
        if governed_ids != expected_governed_ids:
            errors.append("governed_attempt_partition_invalid")
        if report.get("source_attempt_count") != len(source_ids):
            errors.append("report_source_attempt_count_invalid")
        if report.get("effective_attempt_count") != len(governed_ids):
            errors.append("report_effective_attempt_count_invalid")
        if report.get("excluded_attempt_count") != len(source_ids) - len(governed_ids):
            errors.append("report_excluded_attempt_count_invalid")
        if report.get("source_attempt_ids_sha256") != digest(source_ids):
            errors.append("report_source_attempt_ids_digest_invalid")
        if report.get("effective_attempt_ids_sha256") != digest(governed_ids):
            errors.append("report_effective_attempt_ids_digest_invalid")
        excluded_ids = {row.get("attempt_id") for row in report.get("excluded_attempts", [])}
        if excluded_ids != set(source_ids) - set(governed_ids):
            errors.append("report_excluded_attempt_partition_invalid")

        governed_names = {row[0] for row in governed.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for name in r1.DERIVED_TABLES:
            if name in governed_names:
                errors.append(f"stale_derived_table_present:{name}")
        if "evidence_validity" in governed_names or "evidence_validity_events" in governed_names:
            errors.append("governance_projection_leaked_into_effective_overlay")
        metadata = dict(governed.execute("SELECT key,value FROM metadata"))
        if metadata.get("r1_validation_status") != r1.STATUS or metadata.get("r1_governed_overlay") != "true":
            errors.append("governed_metadata_invalid")
        if any(row[0] == "A2" for row in governed.execute("SELECT DISTINCT level FROM learning_sessions")):
            errors.append("a2_attempt_present")
        _validate_attempt_chain(source, errors, "source")
        _validate_attempt_chain(governed, errors, "governed")
    source.close(); governed.close()
    return {
        "validation_status": r1.STATUS if not errors else "FAIL_A1FS_V1_R1_EVIDENCE_VALIDITY_GOVERNANCE",
        "error_count": len(errors),
        "errors": errors,
        "source_attempt_count": report.get("source_attempt_count"),
        "effective_attempt_count": report.get("effective_attempt_count"),
        "excluded_attempt_count": report.get("excluded_attempt_count"),
        "next_short_step": r1.NEXT_SHORT_STEP if not errors else r1.TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-database", type=Path, required=True)
    parser.add_argument("--governed-database", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.source_database, args.governed_database, args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
