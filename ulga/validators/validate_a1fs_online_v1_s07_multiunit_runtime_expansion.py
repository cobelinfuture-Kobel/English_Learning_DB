#!/usr/bin/env python3
"""Independent validator for A1FS Online V1 S07 multi-unit runtime expansion."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_online_v1_s02_first_nonaudio_unit_admission as s02
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05
from ulga.builders import build_a1fs_online_v1_s06_private_e2e_progress_readback as s06
from ulga.builders import build_a1fs_online_v1_s07_multiunit_runtime_expansion as s07

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates canonical prerequisite closure, exact first-unit preservation, atomic M3/M6 migration, "
    "multi-unit M5 output, isolated canary evidence, and no-audio boundaries only."
)

VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_S07_MULTIUNIT_RUNTIME_EXPANSION_VALIDATED"


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
            'id="units"',
            'id="lanes"',
            'id="progress"',
            "app.js",
        ),
        "app.js": (
            "/api/bootstrap",
            "/api/progress",
            "lesson_id",
            "chooseUnit",
            "replaceChildren",
            "textContent",
        ),
        "styles.css": (".unit", ".lane", ".progress", ".card"),
    }
    for name, tokens in required.items():
        try:
            text = (static_root / name).read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"s07_static_missing:{name}:{exc}")
            continue
        for token in tokens:
            if token not in text:
                errors.append(f"s07_static_token_missing:{name}:{token}")
        if name == "app.js" and ("innerHTML" in text or "eval(" in text):
            errors.append("s07_unsafe_dom_rendering_present")


def _database_counts(database_path: Path, errors: list[str]) -> dict[str, int]:
    if not database_path.is_file():
        errors.append("s07_database_missing")
        return {}
    queries = {
        "lesson_count": "SELECT COUNT(*) FROM lesson_catalog",
        "asset_count": "SELECT COUNT(*) FROM lesson_assets",
        "response_contract_count": "SELECT COUNT(*) FROM response_contracts",
        "capture_enabled_contract_count": "SELECT COUNT(*) FROM response_contracts WHERE capture_enabled=1",
        "speaking_capture_enabled_count": "SELECT COUNT(*) FROM response_contracts WHERE skill='SPEAKING' AND capture_enabled=1",
        "listening_lesson_count": "SELECT COUNT(*) FROM lesson_catalog WHERE skill='LISTENING'",
        "profile_count": "SELECT COUNT(*) FROM learner_profiles",
        "session_count": "SELECT COUNT(*) FROM learning_sessions",
        "attempt_count": "SELECT COUNT(*) FROM response_attempts",
    }
    try:
        with sqlite3.connect(database_path) as connection:
            values = {key: int(connection.execute(sql).fetchone()[0]) for key, sql in queries.items()}
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            if metadata.get("s07_task_id") != s07.TASK_ID:
                errors.append("s07_database_task_binding_invalid")
            if metadata.get("s07_schema_version") != s07.SCHEMA_VERSION:
                errors.append("s07_database_schema_binding_invalid")
            if metadata.get("s07_validation_status") != s07.PASS_STATUS:
                errors.append("s07_database_status_binding_invalid")
            if metadata.get("mastery_write_enabled") != "false":
                errors.append("s07_database_mastery_boundary_invalid")
            return values
    except sqlite3.Error as exc:
        errors.append(f"s07_database_invalid:{exc}")
        return {}


def _canary_counts(database_path: Path, errors: list[str]) -> dict[str, int]:
    if not database_path.is_file():
        errors.append("s07_canary_database_missing")
        return {}
    queries = {
        "profile_count": "SELECT COUNT(*) FROM learner_profiles WHERE learner_id=?",
        "session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=?",
        "completed_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='COMPLETED'",
        "exposure_count": "SELECT COUNT(*) FROM state_events WHERE learner_id=? AND event_type='ASSET_EXPOSED'",
        "attempt_count": "SELECT COUNT(*) FROM response_attempts WHERE learner_id=?",
        "auto_fail_count": """SELECT COUNT(*) FROM scoring_results r
                              JOIN response_attempts a USING(attempt_id)
                              WHERE a.learner_id=? AND r.outcome='AUTO_FAIL'""",
        "speaking_attempt_count": """SELECT COUNT(*) FROM response_attempts a
                                    JOIN response_contracts c USING(asset_key)
                                    WHERE a.learner_id=? AND c.skill='SPEAKING'""",
        "listening_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND skill='LISTENING'",
    }
    try:
        with sqlite3.connect(database_path) as connection:
            counts = {
                key: int(connection.execute(sql, (s07.CANARY_LEARNER_ID,)).fetchone()[0])
                for key, sql in queries.items()
            }
            row = connection.execute(
                """SELECT s.lesson_id,r.outcome,r.score FROM learning_sessions s
                   JOIN response_attempts a USING(session_id)
                   JOIN scoring_results r USING(attempt_id)
                   WHERE s.learner_id=?""",
                (s07.CANARY_LEARNER_ID,),
            ).fetchone()
            if (
                not row
                or not str(row[0]).endswith(":READING")
                or row[1] != "AUTO_FAIL"
                or float(row[2]) != 0.0
            ):
                errors.append(f"s07_canary_scoring_invalid:{row}")
            return counts
    except sqlite3.Error as exc:
        errors.append(f"s07_canary_database_invalid:{exc}")
        return {}


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    cp01_path: Path,
    cp04_path: Path,
    m03_path: Path,
    s02_path: Path,
    s05_path: Path,
    s06_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    output_root = Path(output_root).resolve()

    cp01_artifact = _read(cp01_path, errors, "cp01")
    cp04_artifact = _read(cp04_path, errors, "cp04")
    m03_artifact = _read(m03_path, errors, "m03")
    s02_artifact = _read(s02_path, errors, "s02")
    s05_receipt = _read(s05_path, errors, "s05")
    s06_receipt = _read(s06_path, errors, "s06")

    try:
        source_database, _ = s07._source_paths(s05_receipt, s06_receipt)
    except (s07.MultiUnitExpansionError, OSError) as exc:
        errors.append(str(exc))
        source_database = Path(".")

    if receipt.get("task_id") != s07.TASK_ID or receipt.get("schema_version") != s07.SCHEMA_VERSION:
        errors.append("s07_receipt_identity_invalid")
    if receipt.get("validation_status") != s07.PASS_STATUS:
        errors.append("s07_receipt_status_invalid")
    receipt_core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s07.digest(receipt_core):
        errors.append("s07_receipt_digest_invalid")
    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s07.digest(safe_core):
        errors.append("s07_safe_digest_invalid")
    if safe_report.get("validation_status") != s07.PASS_STATUS:
        errors.append("s07_safe_status_invalid")
    try:
        s07.safe_scan(safe_report)
    except s07.MultiUnitExpansionError as exc:
        errors.append(str(exc))

    try:
        expected_admission = s07.build_admission(
            cp01_artifact=cp01_artifact,
            cp04_artifact=cp04_artifact,
            m03_artifact=m03_artifact,
            s02_artifact=s02_artifact,
        )
        expected_consumer = s07.build_consumer(expected_admission, m03_artifact)
    except (
        s07.MultiUnitExpansionError,
        s02.FirstUnitAdmissionError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(f"s07_rebuild_failed:{exc}")
        expected_admission = {}
        expected_consumer = {}

    outputs = receipt.get("runtime_outputs", {})
    root = Path(str(outputs.get("root") or "")).resolve()
    admission_path = Path(str(outputs.get("admission_path") or "")).resolve()
    consumer_path = Path(str(outputs.get("consumer_path") or "")).resolve()
    database_path = Path(str(outputs.get("database_path") or "")).resolve()
    ui_root = Path(str(outputs.get("ui_root") or "")).resolve()
    static_root = Path(str(outputs.get("static_root") or "")).resolve()
    bundle_index_path = Path(str(outputs.get("bundle_index_path") or "")).resolve()
    canary_database = Path(str(outputs.get("canary_database_path") or "")).resolve()

    for name, path in (
        ("root", root),
        ("admission", admission_path),
        ("consumer", consumer_path),
        ("ui", ui_root),
        ("static", static_root),
        ("bundle_index", bundle_index_path),
        ("canary", canary_database),
    ):
        if not _inside(path, output_root):
            errors.append(f"s07_output_outside_authority_root:{name}")
    if root != (output_root / "expanded_runtime").resolve():
        errors.append("s07_runtime_root_noncanonical")
    if database_path != source_database:
        errors.append("s07_persistent_database_binding_invalid")

    actual_admission = _read(admission_path, errors, "s07_admission")
    actual_consumer = _read(consumer_path, errors, "s07_consumer")
    bundle_index = _read(bundle_index_path, errors, "s07_bundle_index")
    if expected_admission and actual_admission != expected_admission:
        errors.append("s07_admission_rebuild_mismatch")
    if expected_consumer and actual_consumer != expected_consumer:
        errors.append("s07_consumer_rebuild_mismatch")

    admitted_units = actual_admission.get("admitted_units", [])
    if not isinstance(admitted_units, list) or len(admitted_units) < 2:
        errors.append("s07_admitted_unit_count_below_two")
    else:
        sequence = [unit.get("sequence_index") for unit in admitted_units]
        if sequence != sorted(sequence):
            errors.append("s07_admitted_sequence_not_monotonic")
        for index, unit in enumerate(admitted_units):
            prerequisites = set(unit.get("prerequisite_unit_ids", []))
            earlier = {row.get("learning_unit_id") for row in admitted_units[:index]}
            if not prerequisites.issubset(earlier):
                errors.append(f"s07_prerequisite_closure_invalid:{unit.get('grammar_unit_id')}")
        first = s02_artifact.get("selected_unit", {})
        first_s07 = admitted_units[0]
        if (
            first_s07.get("learning_unit_id") != first.get("learning_unit_id")
            or first_s07.get("grammar_unit_id") != first.get("grammar_unit_id")
        ):
            errors.append("s07_first_unit_identity_changed")
        for skill in s07.SKILL_ORDER:
            if (
                first_s07.get("admitted_lanes", {}).get(skill, {}).get("item_ids")
                != first.get("admitted_lanes", {}).get(skill, {}).get("item_ids")
            ):
                errors.append(f"s07_first_unit_lane_changed:{skill}")

    units_index = bundle_index.get("units")
    lessons_index = bundle_index.get("lessons")
    if not isinstance(units_index, list) or not isinstance(lessons_index, Mapping):
        errors.append("s07_bundle_index_contract_invalid")
    elif isinstance(admitted_units, list):
        expected_units_index = [
            {
                "grammar_unit_id": unit.get("grammar_unit_id"),
                "sequence_index": unit.get("sequence_index"),
            }
            for unit in admitted_units
        ]
        if units_index != expected_units_index:
            errors.append("s07_bundle_index_unit_order_invalid")
        if len(lessons_index) != len(admitted_units) * 3:
            errors.append("s07_bundle_index_lesson_count_invalid")

    _static_contract(static_root, errors)
    db_counts = _database_counts(database_path, errors)
    canary_counts = _canary_counts(canary_database, errors)

    summary = receipt.get("admission_summary", {})
    runtime = receipt.get("runtime_summary", {})
    admitted_count = int(summary.get("admitted_unit_count") or 0)
    expected_lessons = admitted_count * 3
    expected_assets = int(summary.get("admitted_nonaudio_item_count") or 0)
    expected_capture = int(summary.get("reading_item_count") or 0) + int(summary.get("writing_item_count") or 0)
    expected_db = {
        "lesson_count": expected_lessons,
        "asset_count": expected_assets,
        "response_contract_count": expected_assets,
        "capture_enabled_contract_count": expected_capture,
        "speaking_capture_enabled_count": 0,
        "listening_lesson_count": 0,
    }
    for key, expected in expected_db.items():
        if db_counts.get(key) != expected:
            errors.append(f"s07_database_count_invalid:{key}:{db_counts.get(key)}:{expected}")

    expected_runtime = {
        "expanded_unit_count": admitted_count,
        "expanded_lesson_count": expected_lessons,
        "expanded_asset_count": expected_assets,
        "m5_renderer_bundle_count": expected_lessons,
        "m5_rendered_asset_count": expected_assets,
        "m6_response_contract_count": expected_assets,
        "m6_capture_enabled_contract_count": expected_capture,
        "speaking_capture_enabled_count": 0,
        "listening_runtime_item_count": 0,
        "audio_runtime_asset_count": 0,
    }
    if runtime != expected_runtime:
        errors.append("s07_runtime_summary_invalid")

    migration = receipt.get("migration_summary", {})
    try:
        actual_progress_digest = s07.progress_state_digest(database_path)
    except (sqlite3.Error, OSError) as exc:
        errors.append(f"s07_progress_digest_unreadable:{exc}")
        actual_progress_digest = ""
    if (
        migration.get("progress_state_sha256_before")
        != migration.get("progress_state_sha256_after")
        or migration.get("progress_state_sha256_after") != actual_progress_digest
        or migration.get("production_progress_preserved") is not True
        or migration.get("atomic_database_migration") is not True
        or migration.get("first_unit_identity_preserved") is not True
    ):
        errors.append("s07_migration_progress_preservation_invalid")
    for key in (
        "existing_profile_count_preserved",
        "existing_session_count_preserved",
        "existing_attempt_count_preserved",
    ):
        if migration.get(key) is not True:
            errors.append(f"s07_migration_preservation_invalid:{key}")

    expected_canary = {
        "profile_count": 1,
        "session_count": 1,
        "completed_session_count": 1,
        "exposure_count": 1,
        "attempt_count": 1,
        "auto_fail_count": 1,
        "speaking_attempt_count": 0,
        "listening_session_count": 0,
    }
    for key, expected in expected_canary.items():
        if canary_counts.get(key) != expected:
            errors.append(f"s07_canary_count_invalid:{key}:{canary_counts.get(key)}:{expected}")
    canary_summary = receipt.get("new_unit_runtime_canary", {})
    if canary_summary.get("newly_admitted_unit_runtime_canary") is not True:
        errors.append("s07_new_unit_canary_missing")
    for key in (
        "session_count",
        "completed_session_count",
        "exposure_count",
        "attempt_count",
        "auto_fail_count",
        "speaking_attempt_count",
        "listening_session_count",
    ):
        if canary_summary.get(key) != expected_canary[key]:
            errors.append(f"s07_canary_summary_invalid:{key}")

    capability = receipt.get("capability_contract", {})
    expected_capability = {
        "s02_first_unit_authority_preserved": True,
        "canonical_prerequisite_closure_enforced": True,
        "m3_session_progress_authority_reused": True,
        "m5_renderer_authority_reused": True,
        "m6_response_scoring_authority_reused": True,
        "persistent_s05_database_migrated_in_place": True,
        "parallel_curriculum_created": False,
        "parallel_state_engine_created": False,
        "parallel_scoring_engine_created": False,
        "public_network_binding_allowed": False,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "mastery_write_enabled": False,
    }
    if capability != expected_capability:
        errors.append("s07_capability_contract_invalid")

    boundaries = receipt.get("claim_boundaries", {})
    for key in (
        "real_learner_progress_mutated_by_canary",
        "real_learner_attempt_claimed",
        "learner_mastery_claimed",
        "retention_confirmed",
        "public_online_delivery_claimed",
        "audio_complete",
        "speaking_recording_complete",
        "a2_unlocked",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"s07_claim_boundary_invalid:{key}")
    if receipt.get("product_status") != s07.PRODUCT_STATUS:
        errors.append("s07_product_status_invalid")
    if receipt.get("stop_reason") != "NONE" or receipt.get("next_short_step") != s07.NEXT_SHORT_STEP:
        errors.append("s07_continuation_contract_invalid")

    safe_expected = {
        "task_id": s07.TASK_ID,
        "program_id": s07.PROGRAM_ID,
        "schema_version": s07.SCHEMA_VERSION,
        "validation_status": s07.PASS_STATUS,
        "release_profile": s07.RELEASE_PROFILE,
        "admission_summary": receipt.get("admission_summary"),
        "runtime_summary": receipt.get("runtime_summary"),
        "migration_summary": {
            key: value
            for key, value in migration.items()
            if not str(key).startswith("progress_state_sha256")
        },
        "new_unit_runtime_canary": receipt.get("new_unit_runtime_canary"),
        "capability_contract": receipt.get("capability_contract"),
        "product_status": s07.PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": s07.NEXT_SHORT_STEP,
    }
    if {key: value for key, value in safe_report.items() if key != "report_sha256"} != safe_expected:
        errors.append("s07_safe_projection_invalid")

    return {
        "task_id": s07.TASK_ID,
        "schema_version": s07.SCHEMA_VERSION,
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S07_MULTIUNIT_RUNTIME_EXPANSION",
        "error_count": len(errors),
        "errors": errors,
        "validated_counts": {
            "admitted_unit_count": admitted_count,
            **db_counts,
            **{f"canary_{key}": value for key, value in canary_counts.items()},
        },
        "stop_reason": "NONE" if not errors else "S07_MULTIUNIT_RUNTIME_EXPANSION_VALIDATION_FAILED",
        "next_short_step": s07.NEXT_SHORT_STEP if not errors else s07.TASK_ID,
    }
