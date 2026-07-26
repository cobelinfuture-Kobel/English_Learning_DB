#!/usr/bin/env python3
"""Independent validator for A1FS Online V1 S08 private multi-unit learner journey QA."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_online_v1_s07_multiunit_runtime_expansion as s07
from ulga.builders import build_a1fs_online_v1_s08_private_multiunit_learner_journey_qa as s08

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Independently verifies isolated multi-unit journey evidence, learner-safe resume/abandon UI, "
    "production database immutability, and no-audio/no-mastery boundaries only."
)

VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_S08_PRIVATE_MULTIUNIT_LEARNER_JOURNEY_QA_VALIDATED"


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


def _static_contract(static_root: Path, errors: list[str]) -> None:
    required = {
        "index.html": (
            "Content-Security-Policy",
            'id="active-panel"',
            'id="resume"',
            'id="abandon"',
            'id="units"',
            'id="lanes"',
            'id="progress"',
            "app.js",
        ),
        "app.js": (
            "/api/bootstrap",
            "/api/progress",
            "/api/session/active",
            "/api/session/abandon",
            "restore(snapshot)",
            "chooseUnit",
            "textContent",
        ),
        "styles.css": ("#active-panel", "#resume", "#abandon", ".unit", ".lane", ".progress"),
    }
    for name, tokens in required.items():
        try:
            text = (static_root / name).read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"s08_static_missing:{name}:{exc}")
            continue
        for token in tokens:
            if token not in text:
                errors.append(f"s08_static_token_missing:{name}:{token}")
        if name == "app.js" and ("innerHTML" in text or "eval(" in text):
            errors.append("s08_unsafe_dom_rendering_present")


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _canary_counts(database_path: Path, errors: list[str]) -> dict[str, int]:
    if not database_path.is_file():
        errors.append("s08_canary_database_missing")
        return {}
    queries = {
        "profile_count": "SELECT COUNT(*) FROM learner_profiles WHERE learner_id=?",
        "session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=?",
        "completed_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='COMPLETED'",
        "abandoned_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='ABANDONED'",
        "active_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='ACTIVE'",
        "exposure_count": "SELECT COUNT(*) FROM state_events WHERE learner_id=? AND event_type='ASSET_EXPOSED'",
        "attempt_count": "SELECT COUNT(*) FROM response_attempts WHERE learner_id=?",
        "auto_pass_count": """SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id)
                              WHERE a.learner_id=? AND r.outcome='AUTO_PASS'""",
        "auto_fail_count": """SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id)
                              WHERE a.learner_id=? AND r.outcome='AUTO_FAIL'""",
        "speaking_attempt_count": """SELECT COUNT(*) FROM response_attempts a JOIN response_contracts c USING(asset_key)
                                     WHERE a.learner_id=? AND c.skill='SPEAKING'""",
        "listening_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND skill='LISTENING'",
    }
    try:
        with closing(_connect(database_path)) as connection:
            counts = {
                key: int(connection.execute(sql, (s08.CANARY_LEARNER_ID,)).fetchone()[0])
                for key, sql in queries.items()
            }
            counts["distinct_skill_count"] = int(connection.execute(
                "SELECT COUNT(DISTINCT skill) FROM learning_sessions WHERE learner_id=?",
                (s08.CANARY_LEARNER_ID,),
            ).fetchone()[0])
            lesson_ids = [
                str(row[0])
                for row in connection.execute(
                    "SELECT lesson_id FROM learning_sessions WHERE learner_id=? ORDER BY started_at,session_id",
                    (s08.CANARY_LEARNER_ID,),
                ).fetchall()
            ]
            counts["distinct_unit_count"] = len({s08._grammar_from_lesson(lesson_id) for lesson_id in lesson_ids})
            outcomes = [
                tuple(row)
                for row in connection.execute(
                    """SELECT s.skill,s.session_state,r.outcome,r.score
                       FROM learning_sessions s
                       LEFT JOIN response_attempts a USING(session_id)
                       LEFT JOIN scoring_results r USING(attempt_id)
                       WHERE s.learner_id=? ORDER BY s.started_at,a.attempt_sequence""",
                    (s08.CANARY_LEARNER_ID,),
                ).fetchall()
            ]
            expected_outcomes = [
                ("READING", "COMPLETED", "AUTO_FAIL", 0.0),
                ("WRITING", "COMPLETED", "AUTO_PASS", 1.0),
                ("SPEAKING", "ABANDONED", None, None),
            ]
            if outcomes != expected_outcomes:
                errors.append(f"s08_journey_outcomes_invalid:{outcomes}")
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            if metadata.get("mastery_write_enabled") != "false":
                errors.append("s08_canary_mastery_boundary_invalid")
            return counts
    except (sqlite3.Error, s08.JourneyQAError) as exc:
        errors.append(f"s08_canary_database_invalid:{exc}")
        return {}


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s07_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    output_root = Path(output_root).resolve()
    s07_receipt = _read(s07_path, errors, "s07")

    if receipt.get("task_id") != s08.TASK_ID or receipt.get("schema_version") != s08.SCHEMA_VERSION:
        errors.append("s08_receipt_identity_invalid")
    if receipt.get("validation_status") != s08.PASS_STATUS:
        errors.append("s08_receipt_status_invalid")
    if receipt.get("product_status") != s08.PRODUCT_STATUS or receipt.get("stop_reason") != "NONE":
        errors.append("s08_receipt_product_or_stop_invalid")
    receipt_core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s08.digest(receipt_core):
        errors.append("s08_receipt_digest_invalid")

    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s08.digest(safe_core):
        errors.append("s08_safe_digest_invalid")
    if safe_report.get("validation_status") != s08.PASS_STATUS:
        errors.append("s08_safe_status_invalid")
    try:
        s08.safe_scan(safe_report)
    except s08.JourneyQAError as exc:
        errors.append(str(exc))

    if (
        s07_receipt.get("task_id") != s07.TASK_ID
        or s07_receipt.get("schema_version") != s07.SCHEMA_VERSION
        or s07_receipt.get("validation_status") != s07.PASS_STATUS
        or s07_receipt.get("product_status") != s07.PRODUCT_STATUS
        or s07_receipt.get("stop_reason") != "NONE"
    ):
        errors.append("s08_source_s07_contract_invalid")
    s07_core = {key: value for key, value in s07_receipt.items() if key != "artifact_sha256"}
    if s07_receipt and s07_receipt.get("artifact_sha256") != s07.digest(s07_core):
        errors.append("s08_source_s07_digest_invalid")

    source_outputs = s07_receipt.get("runtime_outputs", {}) if isinstance(s07_receipt, Mapping) else {}
    source_database = Path(str(source_outputs.get("database_path") or "")).resolve()
    source_bundle_index = Path(str(source_outputs.get("bundle_index_path") or "")).resolve()
    outputs = receipt.get("runtime_outputs", {})
    root = Path(str(outputs.get("root") or "")).resolve()
    database_path = Path(str(outputs.get("database_path") or "")).resolve()
    bundle_index_path = Path(str(outputs.get("bundle_index_path") or "")).resolve()
    static_root = Path(str(outputs.get("static_root") or "")).resolve()
    canary_database = Path(str(outputs.get("canary_database_path") or "")).resolve()

    if root != (output_root / "learner_journey_qa").resolve():
        errors.append("s08_runtime_root_noncanonical")
    for name, path in (("root", root), ("static", static_root), ("canary", canary_database)):
        if not _inside(path, output_root):
            errors.append(f"s08_output_outside_authority_root:{name}")
    if database_path != source_database:
        errors.append("s08_production_database_binding_invalid")
    if bundle_index_path != source_bundle_index:
        errors.append("s08_bundle_index_binding_invalid")
    if not database_path.is_file() or not bundle_index_path.is_file():
        errors.append("s08_source_runtime_missing")

    _static_contract(static_root, errors)
    counts = _canary_counts(canary_database, errors)
    expected_counts = {
        "profile_count": 1,
        "session_count": 3,
        "completed_session_count": 2,
        "abandoned_session_count": 1,
        "active_session_count": 0,
        "exposure_count": 3,
        "attempt_count": 2,
        "auto_pass_count": 1,
        "auto_fail_count": 1,
        "speaking_attempt_count": 0,
        "listening_session_count": 0,
        "distinct_unit_count": 2,
        "distinct_skill_count": 3,
    }
    for key, value in expected_counts.items():
        if counts.get(key) != value:
            errors.append(f"s08_canary_count_invalid:{key}:{counts.get(key)}:{value}")

    journey = receipt.get("journey_summary", {})
    for key, value in expected_counts.items():
        if journey.get(key) != value:
            errors.append(f"s08_journey_summary_invalid:{key}:{journey.get(key)}:{value}")
    required_true = {
        "resume_after_process_restart": journey.get("resume_after_process_restart"),
        "cross_unit_switch_blocked_while_active": journey.get("cross_unit_switch_blocked_while_active"),
        "cross_unit_switch_after_completion": journey.get("cross_unit_switch_after_completion"),
        "cross_skill_switch_after_completion": journey.get("cross_skill_switch_after_completion"),
        "speaking_submission_blocked": journey.get("speaking_submission_blocked"),
        "final_progress_readback_digest_stable": journey.get("final_progress_readback_digest_stable"),
        "production_database_unchanged": receipt.get("production_safety", {}).get("production_database_unchanged"),
        "journey_executed_on_isolated_clone": receipt.get("production_safety", {}).get("journey_executed_on_isolated_clone"),
        "active_session_readback": receipt.get("learner_surface", {}).get("active_session_readback"),
        "resume_after_restart": receipt.get("learner_surface", {}).get("resume_after_restart"),
        "abandon_active_session": receipt.get("learner_surface", {}).get("abandon_active_session"),
    }
    for key, value in required_true.items():
        if value is not True:
            errors.append(f"s08_required_true_invalid:{key}")
    if journey.get("process_restart_count") != 2:
        errors.append("s08_process_restart_count_invalid")

    production = receipt.get("production_safety", {})
    before = str(production.get("database_sha256_before") or "")
    after = str(production.get("database_sha256_after") or "")
    if not before or before != after:
        errors.append("s08_production_digest_pair_invalid")
    elif database_path.is_file() and s08.file_digest(database_path) != before:
        errors.append("s08_production_database_digest_drift")

    capability = receipt.get("capability_contract", {})
    expected_capability = {
        "s07_multiunit_runtime_reused": True,
        "m3_session_progress_authority_reused": True,
        "m5_renderer_authority_reused": True,
        "m6_response_scoring_authority_reused": True,
        "parallel_curriculum_created": False,
        "parallel_state_engine_created": False,
        "parallel_scoring_engine_created": False,
        "public_network_binding_allowed": False,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "mastery_write_enabled": False,
    }
    for key, value in expected_capability.items():
        if capability.get(key) is not value:
            errors.append(f"s08_capability_invalid:{key}:{capability.get(key)}:{value}")

    expected_safe = {
        "task_id": receipt.get("task_id"),
        "program_id": receipt.get("program_id"),
        "schema_version": receipt.get("schema_version"),
        "validation_status": receipt.get("validation_status"),
        "release_profile": receipt.get("release_profile"),
        "source_runtime_summary": receipt.get("source_runtime_summary"),
        "journey_summary": receipt.get("journey_summary"),
        "production_safety": {
            "production_database_unchanged": True,
            "journey_executed_on_isolated_clone": True,
            "real_learner_progress_mutated_by_canary": False,
        },
        "learner_surface": receipt.get("learner_surface"),
        "capability_contract": receipt.get("capability_contract"),
        "product_status": receipt.get("product_status"),
        "stop_reason": receipt.get("stop_reason"),
        "next_short_step": receipt.get("next_short_step"),
    }
    if safe_core != expected_safe:
        errors.append("s08_safe_projection_mismatch")

    return {
        "task_id": s08.TASK_ID,
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S08_PRIVATE_MULTIUNIT_LEARNER_JOURNEY_QA_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "validated_counts": counts,
    }
