#!/usr/bin/env python3
"""Independent validator for A1FS Online V1 S05 identity/progress persistence."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_online_v1_s04_private_online_learner_workbench_execution as s04
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates private identity bindings, persistent M3/M6 state, restart proof, and safe readback only."
)

VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_S05_PRIVATE_IDENTITY_PROGRESS_VALIDATED"
FORBIDDEN_SAFE_KEYS = {
    "learner_id", "display_label", "private_subject_digest", "subject_digest",
    "profile", "sessions", "progress", "learner_payload", "response",
    "answer_contract", "answer_key", "accepted_texts", "accepted_sequence",
    "private_scoring_contract", "scoring_contract", "prompt", "prompt_text",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else _canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _read(path: Path, errors: list[str], code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{code}_unreadable:{exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{code}_not_object")
        return {}
    return value


def _walk_keys(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            result.add(str(key).casefold())
            result.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_walk_keys(child))
    return result


def _database_readback(path: Path, errors: list[str]) -> tuple[dict[str, int], dict[str, str]]:
    if not path.is_file():
        errors.append("persistent_database_missing")
        return {}, {}
    queries = {
        "identity_count": "SELECT COUNT(*) FROM s05_identity_bindings",
        "active_profile_count": "SELECT COUNT(*) FROM learner_profiles WHERE profile_state='ACTIVE'",
        "default_profile_count": "SELECT COUNT(*) FROM learner_profiles WHERE learner_id=? AND profile_state='ACTIVE'",
        "default_binding_count": "SELECT COUNT(*) FROM s05_identity_bindings WHERE learner_id=? AND enrollment_source='DEFAULT_PRIVATE_SLOT'",
        "session_count": "SELECT COUNT(*) FROM learning_sessions",
        "completed_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE session_state='COMPLETED'",
        "exposure_count": "SELECT COALESCE(SUM(exposure_count),0) FROM lesson_progress",
        "attempt_count": "SELECT COUNT(*) FROM response_attempts",
        "checkpoint_count": "SELECT COUNT(*) FROM s05_progress_checkpoints",
        "response_contract_count": "SELECT COUNT(*) FROM response_contracts",
        "speaking_capture_count": "SELECT COUNT(*) FROM response_contracts WHERE skill='SPEAKING' AND capture_enabled=1",
        "listening_lesson_count": "SELECT COUNT(*) FROM lesson_catalog WHERE skill='LISTENING'",
        "mastery_table_count": "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE '%mastery%'",
    }
    try:
        with sqlite3.connect(path) as connection:
            counts: dict[str, int] = {}
            for key, sql in queries.items():
                args = (s05.DEFAULT_LEARNER_ID,) if key in {"default_profile_count", "default_binding_count"} else ()
                counts[key] = int(connection.execute(sql, args).fetchone()[0])
            metadata = {str(row[0]): str(row[1]) for row in connection.execute("SELECT key,value FROM s05_persistence_metadata")}
            invalid_bindings = connection.execute(
                """SELECT COUNT(*) FROM s05_identity_bindings b
                LEFT JOIN learner_profiles p USING(learner_id)
                WHERE p.learner_id IS NULL OR p.profile_state!='ACTIVE' OR length(b.private_subject_digest)!=64"""
            ).fetchone()[0]
            if invalid_bindings:
                errors.append("persistent_identity_binding_invalid")
            duplicate_subjects = connection.execute(
                "SELECT COUNT(*) FROM (SELECT private_subject_digest FROM s05_identity_bindings GROUP BY private_subject_digest HAVING COUNT(*)>1)"
            ).fetchone()[0]
            if duplicate_subjects:
                errors.append("persistent_identity_subject_duplicate")
            active_sessions = connection.execute(
                "SELECT learner_id,COUNT(*) FROM learning_sessions WHERE session_state='ACTIVE' GROUP BY learner_id HAVING COUNT(*)>1"
            ).fetchall()
            if active_sessions:
                errors.append("multiple_active_sessions_per_learner")
            return counts, metadata
    except sqlite3.Error as exc:
        errors.append(f"persistent_database_invalid:{exc}")
        return {}, {}


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s04_receipt_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    output_root = Path(output_root).resolve()
    s04_receipt = _read(Path(s04_receipt_path), errors, "s04_receipt")
    if s04_receipt.get("task_id") != s04.TASK_ID or s04_receipt.get("validation_status") != s04.PASS_STATUS:
        errors.append("s04_source_status_invalid")
    s04_core = {key: value for key, value in s04_receipt.items() if key != "artifact_sha256"}
    if s04_receipt.get("artifact_sha256") != s04.digest(s04_core):
        errors.append("s04_source_digest_invalid")

    if receipt.get("task_id") != s05.TASK_ID or receipt.get("schema_version") != s05.SCHEMA_VERSION:
        errors.append("s05_receipt_identity_invalid")
    if receipt.get("validation_status") != s05.PASS_STATUS:
        errors.append("s05_receipt_status_invalid")
    receipt_core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s05.digest(receipt_core):
        errors.append("s05_receipt_digest_invalid")
    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s05.digest(safe_core):
        errors.append("s05_safe_digest_invalid")
    if safe_report.get("validation_status") != s05.PASS_STATUS:
        errors.append("s05_safe_status_invalid")
    leaked = sorted(_walk_keys(safe_report) & FORBIDDEN_SAFE_KEYS)
    if leaked:
        errors.append("s05_safe_private_identity_or_content_leak:" + ",".join(leaked))
    try:
        s05.safe_scan(safe_report)
    except s05.PersistenceError as exc:
        errors.append(str(exc))

    outputs = receipt.get("persistent_outputs", {})
    root = Path(str(outputs.get("root") or ""))
    database = Path(str(outputs.get("database_path") or ""))
    consumer = Path(str(outputs.get("consumer_path") or ""))
    static_root = Path(str(outputs.get("static_root") or ""))
    ui_root = Path(str(outputs.get("ui_root") or ""))
    for name, path in (("root", root), ("database", database), ("consumer", consumer), ("static", static_root), ("ui", ui_root)):
        if not _inside(path, output_root):
            errors.append(f"s05_output_outside_authority_root:{name}")
    if root.resolve() != (output_root / "persistent_workbench").resolve():
        errors.append("s05_persistent_root_noncanonical")
    if not consumer.is_file() or not static_root.is_dir() or not ui_root.is_dir():
        errors.append("s05_persistent_companion_artifact_missing")

    counts, metadata = _database_readback(database, errors)
    if counts.get("identity_count", 0) < 1:
        errors.append("s05_identity_count_invalid")
    if counts.get("active_profile_count", 0) < counts.get("identity_count", 0):
        errors.append("s05_active_profile_count_invalid")
    if counts.get("default_profile_count") != 1 or counts.get("default_binding_count") != 1:
        errors.append("s05_default_private_slot_invalid")
    if counts.get("response_contract_count") != 11:
        errors.append("s05_response_contract_count_invalid")
    if counts.get("speaking_capture_count") != 0:
        errors.append("s05_speaking_capture_not_zero")
    if counts.get("listening_lesson_count") != 0:
        errors.append("s05_listening_lesson_not_zero")
    if counts.get("mastery_table_count") != 0:
        errors.append("s05_mastery_table_forbidden")

    expected_metadata = {
        "task_id": s05.TASK_ID,
        "schema_version": s05.SCHEMA_VERSION,
        "validation_status": s05.PASS_STATUS,
        "source_s04_sha256": str(s04_receipt.get("artifact_sha256")),
        "mastery_write_enabled": "false",
        "a2_unlock_enabled": "false",
        "audio_enabled": "false",
        "public_delivery_enabled": "false",
    }
    for key, value in expected_metadata.items():
        if metadata.get(key) != value:
            errors.append(f"s05_metadata_invalid:{key}")
    if len(metadata.get("database_generation_id", "")) < 16:
        errors.append("s05_database_generation_id_invalid")
    if consumer.is_file() and metadata.get("consumer_sha256") != hashlib.sha256(consumer.read_bytes()).hexdigest():
        errors.append("s05_consumer_binding_invalid")

    identity_summary = receipt.get("identity_summary", {})
    if identity_summary.get("stable_identity_count") != counts.get("identity_count"):
        errors.append("s05_identity_summary_count_invalid")
    if identity_summary.get("active_profile_count") != counts.get("active_profile_count"):
        errors.append("s05_identity_summary_profile_count_invalid")
    if identity_summary.get("default_private_slot_ready") is not True:
        errors.append("s05_default_private_slot_readiness_invalid")
    if identity_summary.get("database_generation_id") != metadata.get("database_generation_id"):
        errors.append("s05_generation_identity_mismatch")

    progress_summary = receipt.get("progress_summary", {})
    progress_expected = {
        "persistent_session_count": counts.get("session_count"),
        "persistent_completed_session_count": counts.get("completed_session_count"),
        "persistent_exposure_count": counts.get("exposure_count"),
        "persistent_attempt_count": counts.get("attempt_count"),
        "checkpoint_count": counts.get("checkpoint_count"),
    }
    for key, value in progress_expected.items():
        if progress_summary.get(key) != value:
            errors.append(f"s05_progress_summary_invalid:{key}")

    canary = receipt.get("restart_canary", {})
    canary_expected = {
        "process_restart_count": 1,
        "stable_identity_count": 1,
        "persisted_session_count": 1,
        "persisted_exposure_count": 1,
        "persisted_attempt_count": 1,
        "persisted_auto_fail_count": 1,
        "snapshot_digest_stable": True,
        "mastery_claimed": False,
    }
    if canary != canary_expected:
        errors.append("s05_restart_canary_invalid")

    capability = receipt.get("capability_contract", {})
    capability_expected = {
        "m3_identity_session_progress_authority_reused": True,
        "m6_response_scoring_authority_reused": True,
        "persistent_database_non_destructive": True,
        "stable_private_identity_binding_enabled": True,
        "progress_readback_enabled": True,
        "restart_persistence_proven": True,
        "parallel_state_engine_created": False,
        "mastery_write_enabled": False,
        "audio_enabled": False,
        "public_network_binding_allowed": False,
    }
    if capability != capability_expected:
        errors.append("s05_capability_contract_invalid")
    boundaries = receipt.get("claim_boundaries", {})
    for key in (
        "default_private_slot_is_real_learner_claimed", "real_learner_attempt_claimed",
        "learner_mastery_claimed", "retention_confirmed", "public_online_delivery_claimed",
        "audio_complete", "speaking_recording_complete", "a2_unlocked",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"s05_claim_boundary_invalid:{key}")
    if receipt.get("product_status") != s05.PRODUCT_STATUS:
        errors.append("s05_product_status_invalid")
    if receipt.get("stop_reason") != "NONE" or receipt.get("next_short_step") != s05.NEXT_SHORT_STEP:
        errors.append("s05_continuation_contract_invalid")

    safe_identity = safe_report.get("identity_summary", {})
    if safe_identity.get("stable_identity_count") != counts.get("identity_count"):
        errors.append("s05_safe_identity_count_invalid")
    if safe_report.get("progress_summary") != progress_summary:
        errors.append("s05_safe_progress_summary_invalid")

    return {
        "task_id": s05.TASK_ID,
        "schema_version": s05.SCHEMA_VERSION,
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S05_PRIVATE_IDENTITY_PROGRESS",
        "error_count": len(errors),
        "errors": errors,
        "validated_counts": counts,
        "stop_reason": "NONE" if not errors else "S05_IDENTITY_PROGRESS_VALIDATION_FAILED",
        "next_short_step": s05.NEXT_SHORT_STEP if not errors else s05.TASK_ID,
    }
