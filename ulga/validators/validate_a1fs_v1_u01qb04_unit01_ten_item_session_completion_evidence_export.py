#!/usr/bin/env python3
"""Validate one completed Unit01 ten-item session and existing M6/M12 evidence."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import (
    build_a1fs_v1_u01qb04_unit01_ten_item_session_completion_evidence_export as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02_validator,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB04_UNIT01_TEN_ITEM_SESSION_COMPLETION_EVIDENCE_VALIDATOR"


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


def file_digest(path: Path) -> tuple[str, int]:
    raw = Path(path).read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw)


def validate(*, database: Path, output_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    root = Path(output_root)
    readback_path = root / builder.READBACK_NAME
    registry_path = root / builder.PRIVATE_EVIDENCE_DIR / "a1fs_v1_m6_evidence_registry.private.json"
    m12_path = root / builder.PRIVATE_EVIDENCE_DIR / "m12_attempt_registry.private.json"
    try:
        readback = load_json(readback_path, "readback")
        registry = load_json(registry_path, "m6_registry")
        m12_registry = load_json(m12_path, "m12_registry")
    except ValueError as exc:
        return {"validator_id": VALIDATOR_ID, "status": "FAIL", "error_count": 1, "errors": [str(exc)]}

    if readback.get("task_id") != builder.TASK_ID:
        errors.append("readback_task_invalid")
    if readback.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("readback_schema_invalid")
    if readback.get("validation_status") != builder.PASS_STATUS:
        errors.append("readback_status_invalid")
    leaked = walk_keys(readback).intersection(builder.SAFE_READBACK_BLOCKED_KEYS)
    if leaked:
        errors.append("safe_readback_private_keys_exposed:" + ",".join(sorted(leaked)))
    session_info = readback.get("session") if isinstance(readback.get("session"), Mapping) else {}
    session_id = str(session_info.get("session_id") or "")
    learner_id = str(session_info.get("learner_id") or "")
    lesson_id = str(session_info.get("lesson_id") or "")
    skill = str(session_info.get("skill") or "")
    if skill not in {"READING", "WRITING"}:
        errors.append("completed_skill_invalid")
    if session_info.get("level") != "A1" or session_info.get("session_state") != "COMPLETED":
        errors.append("completed_session_readback_invalid")
    if session_info.get("session_version") != builder.FINAL_CLEAN_SESSION_VERSION:
        errors.append("completed_session_version_readback_invalid")

    expected_counts = {
        "planned_item_count": 10,
        "completed_item_count": 10,
        "exposure_count": 10,
        "attempt_count": 10,
        "scoring_result_count": 10,
        "m6_registry_entry_count": 10,
        "m12_attempt_count": 10,
    }
    if readback.get("counts") != expected_counts:
        errors.append(f"readback_counts_invalid:{readback.get('counts')}")
    outcomes = readback.get("outcome_distribution")
    if not isinstance(outcomes, Mapping) or sum(int(value) for value in outcomes.values()) != 10:
        errors.append("readback_outcome_distribution_invalid")
    allowed_outcomes = {"AUTO_PASS", "AUTO_FAIL"}
    if isinstance(outcomes, Mapping) and not set(outcomes).issubset(allowed_outcomes):
        errors.append("readback_outcome_type_invalid")

    artifacts = readback.get("evidence_artifacts") if isinstance(readback.get("evidence_artifacts"), Mapping) else {}
    for key, path in (("m6_registry", registry_path), ("m12_registry", m12_path)):
        record = artifacts.get(key) if isinstance(artifacts.get(key), Mapping) else {}
        actual_sha, actual_bytes = file_digest(path)
        if record.get("file_name") != path.name:
            errors.append(f"artifact_file_name_invalid:{key}")
        if record.get("sha256") != actual_sha:
            errors.append(f"artifact_digest_invalid:{key}")
        if record.get("bytes") != actual_bytes:
            errors.append(f"artifact_size_invalid:{key}")

    base = qb02_validator.validate(Path(database))
    if base.get("error_count"):
        errors.extend(f"qb02:{error}" for error in base.get("errors", []))

    db_counts: dict[str, int] = {}
    selected_ids: set[str] = set()
    exposed_ids: set[str] = set()
    attempted_ids: set[str] = set()
    db_outcomes: dict[str, int] = {}
    try:
        with sqlite3.connect(database) as connection:
            connection.row_factory = sqlite3.Row
            session = connection.execute(
                "SELECT * FROM learning_sessions WHERE session_id=?", (session_id,)
            ).fetchone()
            if not session:
                errors.append("database_session_missing")
            else:
                if session["learner_id"] != learner_id or session["lesson_id"] != lesson_id:
                    errors.append("database_session_identity_invalid")
                if session["skill"] != skill or session["level"] != "A1":
                    errors.append("database_session_skill_level_invalid")
                if session["session_state"] != "COMPLETED" or session["session_version"] != builder.FINAL_CLEAN_SESSION_VERSION:
                    errors.append("database_session_completion_invalid")
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            if metadata.get("validation_status") != m3.STATUS:
                errors.append("m3_status_invalid")
            if metadata.get("mastery_write_enabled") != "false":
                errors.append("mastery_write_enabled")
            selected_ids = {
                row[0]
                for row in connection.execute(
                    "SELECT item_id FROM u01qb02_session_items WHERE session_id=?", (session_id,)
                )
            }
            exposed_ids = {
                row[0]
                for row in connection.execute(
                    "SELECT item_id FROM u01qb02_item_exposures WHERE session_id=?", (session_id,)
                )
            }
            attempted_ids = {
                row[0]
                for row in connection.execute(
                    """SELECT c.item_id FROM response_attempts a
                       JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
                       WHERE a.session_id=?""",
                    (session_id,),
                )
            }
            db_counts = {
                "session_plan_count": connection.execute(
                    "SELECT COUNT(*) FROM u01qb02_session_plans WHERE session_id=?", (session_id,)
                ).fetchone()[0],
                "selected_item_count": len(selected_ids),
                "exposure_count": connection.execute(
                    "SELECT COUNT(*) FROM u01qb02_item_exposures WHERE session_id=?", (session_id,)
                ).fetchone()[0],
                "attempt_count": connection.execute(
                    "SELECT COUNT(*) FROM response_attempts WHERE session_id=?", (session_id,)
                ).fetchone()[0],
                "scoring_result_count": connection.execute(
                    """SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id)
                       WHERE a.session_id=?""",
                    (session_id,),
                ).fetchone()[0],
                "evidence_export_count": connection.execute(
                    "SELECT COUNT(*) FROM evidence_exports WHERE session_id=?", (session_id,)
                ).fetchone()[0],
                "asset_exposed_event_count": connection.execute(
                    "SELECT COUNT(*) FROM state_events WHERE session_id=? AND event_type='ASSET_EXPOSED'",
                    (session_id,),
                ).fetchone()[0],
                "session_end_event_count": connection.execute(
                    "SELECT COUNT(*) FROM state_events WHERE session_id=? AND event_type='SESSION_ENDED'",
                    (session_id,),
                ).fetchone()[0],
            }
            db_outcomes = dict(
                sorted(
                    Counter(
                        row[0]
                        for row in connection.execute(
                            """SELECT r.outcome FROM scoring_results r
                               JOIN response_attempts a USING(attempt_id)
                               WHERE a.session_id=?""",
                            (session_id,),
                        )
                    ).items()
                )
            )
    except sqlite3.Error as exc:
        errors.append(f"database_validation_failed:{exc}")

    expected_db_counts = {
        "session_plan_count": 1,
        "selected_item_count": 10,
        "exposure_count": 10,
        "attempt_count": 10,
        "scoring_result_count": 10,
        "evidence_export_count": 1,
        "asset_exposed_event_count": 10,
        "session_end_event_count": 1,
    }
    if db_counts != expected_db_counts:
        errors.append(f"database_counts_invalid:{db_counts}")
    if selected_ids != exposed_ids or selected_ids != attempted_ids or len(selected_ids) != 10:
        errors.append("selected_exposed_attempted_identity_mismatch")
    if db_outcomes != dict(outcomes or {}):
        errors.append(f"outcome_distribution_mismatch:{db_outcomes}:{outcomes}")

    if registry.get("task_id") != m6.TASK_ID or registry.get("validation_status") != m6.STATUS:
        errors.append("m6_registry_identity_invalid")
    if registry.get("private_local_only") is not True or registry.get("attempt_count") != 10:
        errors.append("m6_registry_count_or_privacy_invalid")
    if len(registry.get("entries", [])) != 10:
        errors.append("m6_registry_entries_invalid")
    registry_session = registry.get("session") if isinstance(registry.get("session"), Mapping) else {}
    if registry_session.get("session_id") != session_id or registry_session.get("learner_id") != learner_id:
        errors.append("m6_registry_session_invalid")
    claims = registry.get("claim_boundaries") if isinstance(registry.get("claim_boundaries"), Mapping) else {}
    if any(
        claims.get(key) is not False
        for key in (
            "mastery_written", "retention_confirmed", "a2_unlocked", "public_delivery",
            "audio_evidence_used", "speaking_recording_used",
        )
    ):
        errors.append("m6_registry_claim_boundary_invalid")

    m12_attempts = m12_registry.get("attempts") if isinstance(m12_registry.get("attempts"), list) else []
    if m12_registry.get("task_id") != m6.M08_TASK_ID or m12_registry.get("schema_version") != m6.M08_SCHEMA_VERSION:
        errors.append("m12_registry_identity_invalid")
    if m12_registry.get("private_local_only") is not True or m12_registry.get("session_id") != session_id:
        errors.append("m12_registry_session_or_privacy_invalid")
    if len(m12_attempts) != 10:
        errors.append("m12_attempt_count_invalid")
    m12_ids = {str(row.get("item_id")) for row in m12_attempts if isinstance(row, Mapping)}
    if m12_ids != selected_ids:
        errors.append("m12_selected_item_identity_mismatch")

    expected_boundaries = {
        "parallel_planner_created": False,
        "parallel_learner_database_created": False,
        "parallel_response_capture_created": False,
        "parallel_scoring_created": False,
        "parallel_evidence_schema_created": False,
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
        **db_counts,
        "outcome_distribution": db_outcomes,
        "m6_registry_entry_count": registry.get("attempt_count"),
        "m12_attempt_count": len(m12_attempts),
        "legacy_allowlist_import_ready": readback.get("legacy_allowlist_import_ready"),
        "claim_boundaries": expected_boundaries,
        "next_short_step": builder.NEXT_SHORT_STEP,
    }
