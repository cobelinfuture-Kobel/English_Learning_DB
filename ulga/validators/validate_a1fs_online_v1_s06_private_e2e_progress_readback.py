#!/usr/bin/env python3
"""Independent validator for A1FS Online V1 S06 end-to-end progress readback."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05
from ulga.builders import build_a1fs_online_v1_s06_private_e2e_progress_readback as s06

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates isolated session execution, production-database immutability, learner-safe progress readback, "
    "and no-audio boundaries only."
)

VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_S06_PRIVATE_E2E_PROGRESS_READBACK_VALIDATED"


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _read(path: Path, errors: list[str], code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{code}_unreadable:{exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{code}_not_object")
        return {}
    return value


def _canary_counts(database_path: Path, errors: list[str]) -> dict[str, int]:
    if not database_path.is_file():
        errors.append("s06_canary_database_missing")
        return {}
    queries = {
        "profile_count": "SELECT COUNT(*) FROM learner_profiles WHERE learner_id=?",
        "session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=?",
        "completed_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='COMPLETED'",
        "active_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='ACTIVE'",
        "exposure_count": "SELECT COUNT(*) FROM state_events WHERE learner_id=? AND event_type='ASSET_EXPOSED'",
        "attempt_count": "SELECT COUNT(*) FROM response_attempts WHERE learner_id=?",
        "auto_pass_count": "SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id) WHERE a.learner_id=? AND r.outcome='AUTO_PASS'",
        "auto_fail_count": "SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id) WHERE a.learner_id=? AND r.outcome='AUTO_FAIL'",
        "speaking_attempt_count": "SELECT COUNT(*) FROM response_attempts a JOIN response_contracts c USING(asset_key) WHERE a.learner_id=? AND c.skill='SPEAKING'",
        "listening_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND skill='LISTENING'",
    }
    try:
        with sqlite3.connect(database_path) as connection:
            counts = {
                key: int(connection.execute(sql, (s06.CANARY_LEARNER_ID,)).fetchone()[0])
                for key, sql in queries.items()
            }
            outcomes = connection.execute(
                """SELECT r.outcome,r.score FROM scoring_results r
                   JOIN response_attempts a USING(attempt_id)
                   WHERE a.learner_id=? ORDER BY a.submitted_at,a.attempt_id""",
                (s06.CANARY_LEARNER_ID,),
            ).fetchall()
            if outcomes != [("AUTO_PASS", 1.0), ("AUTO_FAIL", 0.0)]:
                errors.append(f"s06_canary_outcomes_invalid:{outcomes}")
            return counts
    except sqlite3.Error as exc:
        errors.append(f"s06_canary_database_invalid:{exc}")
        return {}


def _validate_static(static_root: Path, errors: list[str]) -> None:
    required = {
        "index.html": ("Content-Security-Policy", "refresh-progress", "id=\"progress\"", "app.js"),
        "app.js": ("/api/progress", "loadProgress", "textContent", "replaceChildren"),
        "styles.css": (".progress", "pre", ".card"),
    }
    for name, tokens in required.items():
        try:
            text = (static_root / name).read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"s06_static_missing:{name}:{exc}")
            continue
        for token in tokens:
            if token not in text:
                errors.append(f"s06_static_token_missing:{name}:{token}")
        if name == "app.js" and ("innerHTML" in text or "eval(" in text):
            errors.append("s06_unsafe_dom_rendering_present")


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s05_receipt_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    output_root = Path(output_root).resolve()
    s05_receipt = _read(Path(s05_receipt_path), errors, "s05_receipt")
    if (
        s05_receipt.get("task_id") != s05.TASK_ID
        or s05_receipt.get("validation_status") != s05.PASS_STATUS
        or s05_receipt.get("product_status") != s05.PRODUCT_STATUS
        or s05_receipt.get("stop_reason") != "NONE"
    ):
        errors.append("s05_source_contract_invalid")
    source_core = {key: value for key, value in s05_receipt.items() if key != "artifact_sha256"}
    if s05_receipt.get("artifact_sha256") != s05.digest(source_core):
        errors.append("s05_source_digest_invalid")

    if receipt.get("task_id") != s06.TASK_ID or receipt.get("schema_version") != s06.SCHEMA_VERSION:
        errors.append("s06_receipt_identity_invalid")
    if receipt.get("validation_status") != s06.PASS_STATUS:
        errors.append("s06_receipt_status_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s06.digest(core):
        errors.append("s06_receipt_digest_invalid")
    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s06.digest(safe_core):
        errors.append("s06_safe_digest_invalid")
    if safe_report.get("validation_status") != s06.PASS_STATUS:
        errors.append("s06_safe_status_invalid")
    try:
        s06.safe_scan(safe_report)
    except s06.ReadbackError as exc:
        errors.append(str(exc))

    source_outputs = s05_receipt.get("persistent_outputs", {})
    outputs = receipt.get("runtime_outputs", {})
    production_database = Path(str(outputs.get("database_path") or "")).resolve()
    source_database = Path(str(source_outputs.get("database_path") or "")).resolve()
    ui_root = Path(str(outputs.get("ui_root") or "")).resolve()
    source_ui_root = Path(str(source_outputs.get("ui_root") or "")).resolve()
    root = Path(str(outputs.get("root") or "")).resolve()
    static_root = Path(str(outputs.get("static_root") or "")).resolve()
    canary_database = Path(str(outputs.get("canary_database_path") or "")).resolve()
    trace_path = Path(str(outputs.get("session_trace_path") or "")).resolve()
    if production_database != source_database or not production_database.is_file():
        errors.append("s06_production_database_binding_invalid")
    if ui_root != source_ui_root or not ui_root.is_dir():
        errors.append("s06_ui_root_binding_invalid")
    for name, path in (("root", root), ("static", static_root), ("canary", canary_database), ("trace", trace_path)):
        if not _inside(path, output_root):
            errors.append(f"s06_output_outside_authority_root:{name}")
    if root != (output_root / "readback").resolve():
        errors.append("s06_readback_root_noncanonical")

    _validate_static(static_root, errors)
    counts = _canary_counts(canary_database, errors)
    expected_counts = {
        "profile_count": 1,
        "session_count": 1,
        "completed_session_count": 1,
        "active_session_count": 0,
        "exposure_count": 2,
        "attempt_count": 2,
        "auto_pass_count": 1,
        "auto_fail_count": 1,
        "speaking_attempt_count": 0,
        "listening_session_count": 0,
    }
    for key, expected in expected_counts.items():
        if counts.get(key) != expected:
            errors.append(f"s06_canary_count_invalid:{key}:{counts.get(key)}:{expected}")

    trace = _read(trace_path, errors, "s06_trace")
    if trace.get("task_id") != s06.TASK_ID or trace.get("synthetic_canary_only") is not True:
        errors.append("s06_trace_identity_invalid")
    if trace.get("completed_session_state") != "COMPLETED":
        errors.append("s06_trace_session_state_invalid")
    steps = trace.get("steps")
    if not isinstance(steps, list) or [row.get("outcome") for row in steps] != ["AUTO_PASS", "AUTO_FAIL"]:
        errors.append("s06_trace_outcomes_invalid")
    if trace.get("production_database_sha256_before") != trace.get("production_database_sha256_after"):
        errors.append("s06_trace_production_database_changed")
    if production_database.is_file() and trace.get("production_database_sha256_after") != s06.file_digest(production_database):
        errors.append("s06_production_database_digest_drift")
    if trace.get("before_readback_sha256") == trace.get("after_readback_sha256"):
        errors.append("s06_progress_readback_delta_missing")

    expected_summary = {
        "session_count": 1,
        "completed_session_count": 1,
        "exposure_count": 2,
        "attempt_count": 2,
        "auto_pass_count": 1,
        "auto_fail_count": 1,
        "restart_readback_count": 1,
        "restart_readback_digest_stable": True,
        "production_database_unchanged": True,
        "speaking_attempt_count": 0,
        "listening_session_count": 0,
        "audio_runtime_asset_count": 0,
    }
    if receipt.get("end_to_end_summary") != expected_summary:
        errors.append("s06_end_to_end_summary_invalid")
    if safe_report.get("end_to_end_summary") != expected_summary:
        errors.append("s06_safe_summary_invalid")

    expected_surface = {
        "loopback_progress_endpoint": "/api/progress",
        "learner_safe_progress_panel": True,
        "default_private_slot_bound": True,
        "progress_readback_fields": [
            "session_count", "completed_session_count", "exposure_count",
            "attempt_count", "auto_pass_count", "auto_fail_count",
        ],
    }
    if receipt.get("progress_surface") != expected_surface:
        errors.append("s06_progress_surface_invalid")

    capability = receipt.get("capability_contract", {})
    expected_capability = {
        "m3_session_progress_authority_reused": True,
        "m6_response_scoring_authority_reused": True,
        "persistent_s05_database_reused": True,
        "production_database_mutated_by_canary": False,
        "parallel_state_engine_created": False,
        "parallel_scoring_engine_created": False,
        "public_network_binding_allowed": False,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "mastery_write_enabled": False,
    }
    if capability != expected_capability:
        errors.append("s06_capability_contract_invalid")
    boundaries = receipt.get("claim_boundaries", {})
    if boundaries.get("synthetic_canary_only") is not True:
        errors.append("s06_synthetic_canary_boundary_invalid")
    for key in (
        "real_learner_attempt_claimed", "learner_mastery_claimed", "retention_confirmed",
        "public_online_delivery_claimed", "audio_complete", "speaking_recording_complete", "a2_unlocked",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"s06_claim_boundary_invalid:{key}")
    if receipt.get("product_status") != s06.PRODUCT_STATUS:
        errors.append("s06_product_status_invalid")
    if receipt.get("stop_reason") != "NONE" or receipt.get("next_short_step") != s06.NEXT_SHORT_STEP:
        errors.append("s06_continuation_contract_invalid")

    return {
        "task_id": s06.TASK_ID,
        "schema_version": s06.SCHEMA_VERSION,
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S06_PRIVATE_E2E_PROGRESS_READBACK",
        "error_count": len(errors),
        "errors": errors,
        "validated_counts": counts,
        "stop_reason": "NONE" if not errors else "S06_PROGRESS_READBACK_VALIDATION_FAILED",
        "next_short_step": s06.NEXT_SHORT_STEP if not errors else s06.TASK_ID,
    }
