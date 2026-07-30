#!/usr/bin/env python3
"""Validate U01QB05 remediation, reassessment, and carry-over behavior."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)
from ulga.builders import (
    build_a1fs_v1_u01qb04_unit01_ten_item_session_completion_evidence_export as qb04,
)
from ulga.builders import (
    build_a1fs_v1_u01qb05_unit01_failed_item_remediation_reassessment_carryover as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02_validator,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb04_unit01_ten_item_session_completion_evidence_export as qb04_validator,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB05_UNIT01_REMEDIATION_REASSESSMENT_CARRYOVER_VALIDATOR"


def load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{code}_not_object")
    return value


def walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(walk_keys(child))
    return keys


def validate(*, database: Path, output_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    root = Path(output_root)
    readback_path = root / builder.READBACK_NAME
    try:
        readback = load_json(readback_path, "readback")
    except ValueError as exc:
        return {"validator_id": VALIDATOR_ID, "status": "FAIL", "error_count": 1, "errors": [str(exc)]}

    if readback.get("task_id") != builder.TASK_ID:
        errors.append("readback_task_invalid")
    if readback.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("readback_schema_invalid")
    if readback.get("validation_status") != builder.PASS_STATUS:
        errors.append("readback_status_invalid")
    leaked = walk_keys(readback).intersection(builder.SAFE_BLOCKED_KEYS)
    if leaked:
        errors.append("safe_readback_private_keys_exposed:" + ",".join(sorted(leaked)))

    learner_id = str(readback.get("learner_id") or "")
    failed = readback.get("failed_item") if isinstance(readback.get("failed_item"), Mapping) else {}
    reassessment = readback.get("reassessment") if isinstance(readback.get("reassessment"), Mapping) else {}
    carryover = readback.get("carryover") if isinstance(readback.get("carryover"), Mapping) else {}
    failed_item_id = str(failed.get("item_id") or "")
    source_session_id = str(failed.get("source_failure_session_id") or "")
    reassessment_session_id = str(reassessment.get("session_id") or "")
    carryover_session_id = str(carryover.get("session_id") or "")

    if failed.get("source_outcome") != "AUTO_FAIL":
        errors.append("source_failure_outcome_readback_invalid")
    if reassessment.get("selection_reason") != "REMEDIATION" or reassessment.get("outcome") != "AUTO_PASS":
        errors.append("reassessment_readback_invalid")
    if reassessment.get("session_state") != "COMPLETED" or reassessment.get("session_version") != 22:
        errors.append("reassessment_session_readback_invalid")
    if reassessment.get("completed_item_count") != 10:
        errors.append("reassessment_item_count_readback_invalid")
    if carryover.get("session_state") != "ABANDONED" or carryover.get("session_version") != 2:
        errors.append("carryover_session_readback_invalid")
    if carryover.get("failed_item_reselected") is not False:
        errors.append("carryover_reselection_readback_invalid")
    if carryover.get("exclusion_gate") != "RECENT_EXPOSURE_WINDOW":
        errors.append("carryover_gate_readback_invalid")
    if carryover.get("recent_exposure_window") != qb02.RECENT_EXPOSURE_WINDOW:
        errors.append("carryover_window_readback_invalid")
    if carryover.get("carryover_plan_item_count") != 10:
        errors.append("carryover_plan_count_readback_invalid")
    expected_history = [
        {"session_id": source_session_id, "outcome": "AUTO_FAIL"},
        {"session_id": reassessment_session_id, "outcome": "AUTO_PASS"},
    ]
    if readback.get("failed_item_outcome_history") != expected_history:
        errors.append("failed_item_history_readback_invalid")

    completion_root = root / builder.REASSESSMENT_OUTPUT_DIR
    completion_readback_path = completion_root / qb04.READBACK_NAME
    record = readback.get("reassessment_completion_artifact")
    if not isinstance(record, Mapping):
        errors.append("reassessment_completion_artifact_missing")
    else:
        raw = completion_readback_path.read_bytes() if completion_readback_path.is_file() else b""
        if record.get("file_name") != completion_readback_path.name:
            errors.append("reassessment_completion_file_name_invalid")
        if record.get("sha256") != hashlib.sha256(raw).hexdigest():
            errors.append("reassessment_completion_digest_invalid")
        if record.get("bytes") != len(raw):
            errors.append("reassessment_completion_size_invalid")

    base = qb02_validator.validate(Path(database))
    if base.get("error_count"):
        errors.extend(f"qb02:{error}" for error in base.get("errors", []))
    completion_report = qb04_validator.validate(database=Path(database), output_root=completion_root)
    if completion_report.get("error_count"):
        errors.extend(f"qb04:{error}" for error in completion_report.get("errors", []))

    db_summary: dict[str, Any] = {}
    try:
        with sqlite3.connect(database) as connection:
            connection.row_factory = sqlite3.Row
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            if metadata.get("validation_status") != m3.STATUS:
                errors.append("m3_status_invalid")
            if metadata.get("mastery_write_enabled") != "false":
                errors.append("mastery_write_enabled")
            sessions = {
                row["session_id"]: dict(row)
                for row in connection.execute(
                    "SELECT * FROM learning_sessions WHERE session_id IN (?,?,?)",
                    (source_session_id, reassessment_session_id, carryover_session_id),
                )
            }
            source = sessions.get(source_session_id)
            second = sessions.get(reassessment_session_id)
            third = sessions.get(carryover_session_id)
            if not source or source["learner_id"] != learner_id or source["session_state"] != "COMPLETED":
                errors.append("source_failure_session_invalid")
            if not second or second["learner_id"] != learner_id or second["session_state"] != "COMPLETED" or second["session_version"] != 22:
                errors.append("reassessment_session_invalid")
            if not third or third["learner_id"] != learner_id or third["session_state"] != "ABANDONED" or third["session_version"] != 2:
                errors.append("carryover_session_invalid")
            if source and second and third and len({source["lesson_id"], second["lesson_id"], third["lesson_id"]}) != 1:
                errors.append("remediation_lesson_identity_drift")

            second_item = connection.execute(
                "SELECT selection_reason FROM u01qb02_session_items WHERE session_id=? AND item_id=?",
                (reassessment_session_id, failed_item_id),
            ).fetchone()
            if not second_item or second_item[0] != "REMEDIATION":
                errors.append("failed_item_not_remediation_selected")
            if connection.execute(
                "SELECT 1 FROM u01qb02_session_items WHERE session_id=? AND item_id=?",
                (carryover_session_id, failed_item_id),
            ).fetchone():
                errors.append("failed_item_immediately_reselected")

            history = [
                dict(row)
                for row in connection.execute(
                    """SELECT a.session_id,r.outcome,r.score
                       FROM response_attempts a
                       JOIN scoring_results r USING(attempt_id)
                       JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
                       WHERE a.learner_id=? AND c.item_id=? ORDER BY a.rowid""",
                    (learner_id, failed_item_id),
                )
            ]
            if [(row["session_id"], row["outcome"]) for row in history] != [
                (source_session_id, "AUTO_FAIL"),
                (reassessment_session_id, "AUTO_PASS"),
            ]:
                errors.append(f"failed_item_database_history_invalid:{history}")
            latest = history[-1] if history else None
            if not latest or latest["outcome"] != "AUTO_PASS":
                errors.append("failed_item_latest_outcome_not_pass")

            recent = [
                row[0]
                for row in connection.execute(
                    """SELECT item_id FROM u01qb02_item_exposures
                       WHERE learner_id=? ORDER BY exposure_seq DESC LIMIT ?""",
                    (learner_id, qb02.RECENT_EXPOSURE_WINDOW),
                )
            ]
            if failed_item_id not in recent:
                errors.append("failed_item_not_in_recent_exposure_window")
            third_exposures = connection.execute(
                "SELECT COUNT(*) FROM u01qb02_item_exposures WHERE session_id=?", (carryover_session_id,)
            ).fetchone()[0]
            third_attempts = connection.execute(
                "SELECT COUNT(*) FROM response_attempts WHERE session_id=?", (carryover_session_id,)
            ).fetchone()[0]
            third_plan_count = connection.execute(
                "SELECT COUNT(*) FROM u01qb02_session_items WHERE session_id=?", (carryover_session_id,)
            ).fetchone()[0]
            second_exposures = connection.execute(
                "SELECT COUNT(*) FROM u01qb02_item_exposures WHERE session_id=?", (reassessment_session_id,)
            ).fetchone()[0]
            second_attempts = connection.execute(
                "SELECT COUNT(*) FROM response_attempts WHERE session_id=?", (reassessment_session_id,)
            ).fetchone()[0]
            db_summary = {
                "failed_item_attempt_count": len(history),
                "reassessment_exposure_count": second_exposures,
                "reassessment_attempt_count": second_attempts,
                "carryover_plan_item_count": third_plan_count,
                "carryover_exposure_count": third_exposures,
                "carryover_attempt_count": third_attempts,
            }
    except sqlite3.Error as exc:
        errors.append(f"database_validation_failed:{exc}")

    expected_db_summary = {
        "failed_item_attempt_count": 2,
        "reassessment_exposure_count": 10,
        "reassessment_attempt_count": 10,
        "carryover_plan_item_count": 10,
        "carryover_exposure_count": 0,
        "carryover_attempt_count": 0,
    }
    if db_summary != expected_db_summary:
        errors.append(f"database_summary_invalid:{db_summary}")

    expected_boundaries = {
        "parallel_planner_created": False,
        "parallel_learner_database_created": False,
        "parallel_response_capture_created": False,
        "parallel_scoring_created": False,
        "parallel_remediation_engine_created": False,
        "unit02_to_unit24_modified": False,
        "speaking_capture_enabled": False,
        "mastery_written": False,
        "retention_confirmed": False,
        "a2_unlocked": False,
    }
    if readback.get("claim_boundaries") != expected_boundaries:
        errors.append("readback_claim_boundaries_invalid")

    return {
        "validator_id": VALIDATOR_ID,
        "status": builder.PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        **db_summary,
        "failed_item_id": failed_item_id,
        "source_failure_session_id": source_session_id,
        "reassessment_session_id": reassessment_session_id,
        "carryover_session_id": carryover_session_id,
        "claim_boundaries": expected_boundaries,
        "next_short_step": builder.NEXT_SHORT_STEP,
    }
