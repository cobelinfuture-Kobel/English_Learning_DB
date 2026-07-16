#!/usr/bin/env python3
"""Independent validator for the M3 private SQLite state store."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import stat
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-M3_LearnerProfileSessionAndStateStorage"
SCHEMA_VERSION = "a1fs.v1.m3.learner_state.sqlite.v1"
STATUS = "PASS_A1FS_V1_M3_LEARNER_PROFILE_SESSION_STATE_STORAGE_READY"
CONSUMER_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
NEXT_SHORT_STEP = "A1FS-V1-M4_LessonPlannerSelectionAndA2Lock"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); os.replace(tmp, path)


def validate(database_path: Path, consumer_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        consumer_raw = consumer_path.read_bytes(); consumer = json.loads(consumer_raw)
    except (OSError, json.JSONDecodeError) as exc:
        return {"validation_status": "FAIL_A1FS_V1_M3", "error_count": 1, "errors": [f"consumer_unreadable:{exc}"]}
    if consumer.get("validation_status") != CONSUMER_STATUS: errors.append("consumer_status_invalid")
    if not database_path.is_file():
        return {"validation_status": "FAIL_A1FS_V1_M3", "error_count": 1, "errors": ["database_missing"]}
    if os.name != "nt" and stat.S_IMODE(database_path.stat().st_mode) & 0o077:
        errors.append("database_permissions_not_private")
    connection = sqlite3.connect(database_path); connection.row_factory = sqlite3.Row
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok": errors.append(f"sqlite_integrity_failure:{integrity}")
        if list(connection.execute("PRAGMA foreign_key_check")): errors.append("foreign_key_violation")
        metadata = {row[0]: row[1] for row in connection.execute("SELECT key,value FROM metadata")}
        expected_metadata = {
            "task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": STATUS,
            "consumer_sha256": _sha(consumer_raw), "scoring_write_enabled": "false",
            "mastery_write_enabled": "false", "a2_session_enabled": "false",
            "learner_release_approved": "false", "next_short_step": NEXT_SHORT_STEP,
        }
        for key, value in expected_metadata.items():
            if metadata.get(key) != value: errors.append(f"metadata_invalid:{key}")
        required_tables = {"metadata", "lesson_catalog", "lesson_assets", "learner_profiles", "learning_sessions", "lesson_progress", "state_events"}
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required_tables <= tables: errors.append("required_table_missing")
        lesson_count = connection.execute("SELECT COUNT(*) FROM lesson_catalog").fetchone()[0]
        asset_count = connection.execute("SELECT COUNT(*) FROM lesson_assets").fetchone()[0]
        if lesson_count != consumer.get("counts", {}).get("lesson_count"): errors.append("lesson_catalog_count_mismatch")
        if asset_count != consumer.get("counts", {}).get("asset_record_count"): errors.append("lesson_asset_count_mismatch")
        source_lessons = {row["lesson_id"]: row for row in consumer.get("lesson_catalog", [])}
        db_lessons = {row["lesson_id"]: dict(row) for row in connection.execute("SELECT * FROM lesson_catalog")}
        if set(source_lessons) != set(db_lessons): errors.append("lesson_catalog_identity_mismatch")
        for lesson_id, source in source_lessons.items():
            row = db_lessons.get(lesson_id, {})
            if row.get("skill") != source.get("skill") or row.get("level") != source.get("level"):
                errors.append(f"lesson_partition_mismatch:{lesson_id}")
            if bool(row.get("payload_access_allowed")) != (source.get("level") in {"A1", "A1+"}):
                errors.append(f"lesson_payload_access_mismatch:{lesson_id}")
        source_assets = {row["asset_key"]: row for row in consumer.get("asset_records", [])}
        db_assets = {row["asset_key"]: dict(row) for row in connection.execute("SELECT * FROM lesson_assets")}
        if set(source_assets) != set(db_assets): errors.append("asset_catalog_identity_mismatch")
        for key, source in source_assets.items():
            row = db_assets.get(key, {})
            if row.get("lesson_id") != source.get("lesson_id") or row.get("role") != source.get("role") or row.get("content_digest") != source.get("content_digest"):
                errors.append(f"asset_catalog_mismatch:{key}")
        if connection.execute("SELECT COUNT(*) FROM learning_sessions WHERE level='A2'").fetchone()[0]: errors.append("a2_session_present")
        if connection.execute("SELECT COUNT(*) FROM lesson_progress WHERE level='A2'").fetchone()[0]: errors.append("a2_progress_present")
        progress_states = {row[0] for row in connection.execute("SELECT DISTINCT progress_state FROM lesson_progress")}
        if not progress_states <= {"NOT_STARTED", "IN_PROGRESS", "PAUSED"}: errors.append("unauthorized_progress_state_present")
        previous = "0" * 64; event_count = 0
        for row in connection.execute("SELECT * FROM state_events ORDER BY event_seq"):
            event_count += 1
            try: payload = json.loads(row["payload_json"])
            except json.JSONDecodeError:
                errors.append(f'event_payload_invalid:{row["event_id"]}'); continue
            core = {"event_id": row["event_id"], "learner_id": row["learner_id"], "session_id": row["session_id"],
                    "event_type": row["event_type"], "event_at": row["event_at"], "payload": payload}
            expected_hash = _sha((previous + _canonical(core)).encode("utf-8"))
            if row["previous_hash"] != previous or row["event_hash"] != expected_hash:
                errors.append(f'event_chain_invalid:{row["event_id"]}')
            previous = row["event_hash"]
        profile_count = connection.execute("SELECT COUNT(*) FROM learner_profiles").fetchone()[0]
        session_count = connection.execute("SELECT COUNT(*) FROM learning_sessions").fetchone()[0]
        exposure_count = connection.execute("SELECT COUNT(*) FROM state_events WHERE event_type='ASSET_EXPOSED'").fetchone()[0]
        if exposure_count != connection.execute("SELECT COALESCE(SUM(exposure_count),0) FROM lesson_progress").fetchone()[0]: errors.append("exposure_event_progress_count_mismatch")
    except sqlite3.DatabaseError as exc:
        errors.append(f"sqlite_unreadable:{exc}"); lesson_count = asset_count = profile_count = session_count = event_count = 0
    finally:
        connection.close()
    return {
        "task_id": TASK_ID, "validation_status": STATUS if not errors else "FAIL_A1FS_V1_M3_LEARNER_PROFILE_SESSION_STATE_STORAGE",
        "error_count": len(errors), "errors": errors, "lesson_count": lesson_count, "asset_count": asset_count,
        "profile_count": profile_count, "session_count": session_count, "event_count": event_count,
        "next_short_step": NEXT_SHORT_STEP if not errors else TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--database", type=Path, required=True); parser.add_argument("--consumer", type=Path, required=True); parser.add_argument("--validation-report", type=Path, required=True)
    args = parser.parse_args(); report = validate(args.database, args.consumer); _atomic(args.validation_report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2)); return 0 if not report["errors"] else 1


if __name__ == "__main__": raise SystemExit(main())
