#!/usr/bin/env python3
"""Validate the U01E S05 release, migration, runtime, and rollback receipt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_2_u01e_s05_release_migration_acceptance as builder

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_ONLINE_V1_2_U01E_S05_RELEASE_MIGRATION_ACCEPTANCE_VALIDATOR"
FORBIDDEN_SAFE_KEYS = (
    '"package_root"',
    '"candidate_root"',
    '"acceptance_product_root"',
    '"installer_path"',
    '"visual_screenshot_path"',
    '"learner_id"',
    '"attempt_id"',
    '"response_json"',
    '"accepted_texts"',
    '"accepted_sequence"',
    '"correct_answer"',
    '"source_database_sha256_before"',
    '"migrated_database_sha256"',
)


def require(condition: bool, code: str, errors: list[str]) -> None:
    if not condition:
        errors.append(code)


def validate_outputs(receipt: Mapping[str, Any], safe: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    identity = (
        receipt.get("task_id"), receipt.get("program_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("source_product_version"), receipt.get("target_product_version"),
    )
    require(identity == (
        builder.TASK_ID, builder.PROGRAM_ID, builder.SCHEMA_VERSION,
        builder.PASS_STATUS, builder.PRODUCT_STATUS,
        builder.SOURCE_VERSION, builder.TARGET_VERSION,
    ), "receipt_identity_invalid", errors)
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    require(receipt.get("artifact_sha256") == builder.digest(core), "receipt_digest_invalid", errors)
    safe_core = {key: value for key, value in safe.items() if key != "report_sha256"}
    require(safe.get("report_sha256") == builder.digest(safe_core), "safe_digest_invalid", errors)
    require(safe.get("task_id") == builder.TASK_ID, "safe_task_invalid", errors)
    require(safe.get("validation_status") == builder.PASS_STATUS, "safe_status_invalid", errors)

    release = receipt.get("release_summary", {})
    expected_release = {
        "unit_count": 24,
        "lesson_count": 72,
        "source_asset_count": 264,
        "target_asset_count": 277,
        "new_asset_count": 13,
        "unit01_activity_count": 24,
        "context_count": 5,
        "question_type_count": 8,
        "preserved_lesson_count": 69,
    }
    for key, expected in expected_release.items():
        require(release.get(key) == expected, f"release_summary_invalid:{key}", errors)
    require(release.get("unit01_counts") == builder.EXPECTED_UNIT01_COUNTS, "unit01_counts_invalid", errors)
    require(set(release.get("changed_lesson_ids", [])) == set(builder.m01.LESSON_IDS.values()), "changed_lesson_set_invalid", errors)

    migration = receipt.get("migration_summary", {})
    require(migration.get("legacy_schema_unchanged") is True, "legacy_schema_changed", errors)
    require(migration.get("legacy_non_target_rows_unchanged") is True, "legacy_non_target_rows_changed", errors)
    require(migration.get("lesson_asset_rows_added") == 13, "lesson_asset_delta_invalid", errors)
    require(migration.get("response_contract_rows_added") == 13, "response_contract_delta_invalid", errors)
    require(set(migration.get("additive_tables", [])) == builder.s04.ADDITIVE_TABLES, "additive_tables_invalid", errors)
    require(migration.get("target_binding_count") == 24, "target_binding_count_invalid", errors)
    require(migration.get("v1_1_compatible") is True, "v1_1_migration_compatibility_invalid", errors)

    acceptance = receipt.get("acceptance_summary", {})
    for key, expected in (
        ("installed_version", "1.2.0"),
        ("unit_count", 24),
        ("lesson_count", 72),
        ("asset_count", 277),
        ("unit01_activity_count", 24),
        ("context_count", 5),
        ("question_type_count", 8),
        ("speaking_practice_card_count", 6),
        ("speaking_capture_enabled", False),
        ("listening_enabled", False),
        ("audio_enabled", False),
        ("a2_unlocked", False),
    ):
        require(acceptance.get(key) == expected, f"acceptance_invalid:{key}", errors)
    require(acceptance.get("unit01_counts") == builder.EXPECTED_UNIT01_COUNTS, "acceptance_unit01_counts_invalid", errors)
    require(acceptance.get("coverage_distinct_attempt_semantics_pass") is True, "coverage_semantics_failed", errors)
    require(acceptance.get("coverage_after_practised_item_count", 0) > acceptance.get("coverage_before_practised_item_count", 0), "coverage_did_not_increase", errors)
    reading = acceptance.get("reading", {})
    writing = acceptance.get("writing", {})
    require(reading.get("contract_count") == 10 and reading.get("completion_allowed") is True, "reading_dynamic_gate_invalid", errors)
    require(writing.get("contract_count") == 8 and writing.get("completion_allowed") is True, "writing_dynamic_gate_invalid", errors)
    require(reading.get("session_completed") is True, "reading_session_not_completed", errors)
    require(writing.get("session_completed") is True, "writing_session_not_completed", errors)
    http = acceptance.get("http", {})
    for key in ("authenticated_login_pass", "bootstrap_pass", "progress_pass", "coverage_endpoint_pass"):
        require(http.get(key) is True, f"http_acceptance_invalid:{key}", errors)
    static = acceptance.get("static_surface", {})
    for key in (
        "coverage_panel_visible_contract", "coverage_api_connected",
        "sequence_response_type_supported", "token_bank_renderer_present",
        "coverage_styles_present", "hidden_answers_absent",
    ):
        require(static.get(key) is True, f"static_acceptance_invalid:{key}", errors)
    visual = acceptance.get("visual", {})
    require(visual.get("dom_contract_pass") is True, "visual_dom_contract_invalid", errors)
    require(visual.get("status") in {"PASS_HEADLESS_CHROMIUM_SCREENSHOT", "NOT_AVAILABLE_IN_EXECUTION_ENVIRONMENT"}, "visual_status_invalid", errors)
    rollback = acceptance.get("rollback", {})
    for key in (
        "v1_1_version_loaded", "post_migration_database_readable",
        "forward_switch_back_to_v1_2_pass",
    ):
        require(rollback.get(key) is True, f"rollback_acceptance_invalid:{key}", errors)
    require(rollback.get("v1_1_unit01_old_activity_count") == 11, "rollback_old_activity_count_invalid", errors)
    require(rollback.get("old_contract_count") == 11, "rollback_old_contract_count_invalid", errors)
    require(rollback.get("new_contract_rows_ignored_by_old_bundle") == 13, "rollback_new_contract_count_invalid", errors)

    recovery = receipt.get("recovery_summary", {})
    for key in (
        "failed_update_automatic_rollback_pass",
        "explicit_v1_1_rollback_pass",
        "v1_1_post_migration_database_compatibility_pass",
        "forward_switch_back_to_v1_2_pass",
    ):
        require(recovery.get(key) is True, f"recovery_invalid:{key}", errors)
    production = receipt.get("production_safety", {})
    for key in (
        "production_current_version_unchanged", "production_shared_state_unchanged",
        "production_legacy_rows_unchanged",
    ):
        require(production.get(key) is True, f"production_safety_invalid:{key}", errors)
    for key in (
        "source_database_mutated", "existing_11_asset_identities_changed",
        "other_69_lessons_changed",
    ):
        require(production.get(key) is False, f"production_safety_invalid:{key}", errors)
    boundaries = receipt.get("boundaries", {})
    for key in (
        "runtime_free_generation_allowed", "unit02_modified", "listening_enabled",
        "audio_enabled", "speaking_capture_enabled", "a2_unlocked",
        "external_binding_enabled", "mastery_inferred_from_single_attempt",
    ):
        require(boundaries.get(key) is False, f"boundary_invalid:{key}", errors)
    require(receipt.get("stop_reason") == "NONE", "stop_reason_invalid", errors)
    require(receipt.get("next_short_step") == builder.NEXT_SHORT_STEP, "next_short_step_invalid", errors)

    for key in (
        "release_summary", "acceptance_summary", "recovery_summary",
        "production_safety", "boundaries", "stop_reason", "next_short_step",
    ):
        require(safe.get(key) == receipt.get(key), f"safe_receipt_drift:{key}", errors)
    encoded = json.dumps(safe, ensure_ascii=False, sort_keys=True)
    for forbidden in FORBIDDEN_SAFE_KEYS:
        require(forbidden not in encoded, f"safe_private_key_leaked:{forbidden}", errors)

    status = builder.PASS_STATUS if not errors else "FAIL"
    report_core = {
        "validator_id": VALIDATOR_ID,
        "validation_status": status,
        "error_count": len(errors),
        "errors": errors,
        "target_asset_count": release.get("target_asset_count"),
        "unit01_activity_count": release.get("unit01_activity_count"),
        "dynamic_reading_contract_count": reading.get("contract_count"),
        "dynamic_writing_contract_count": writing.get("contract_count"),
        "v1_1_rollback_pass": rollback.get("v1_1_version_loaded") is True,
        "failed_update_rollback_pass": recovery.get("failed_update_automatic_rollback_pass") is True,
        "production_unchanged": all(production.get(key) is True for key in (
            "production_current_version_unchanged", "production_shared_state_unchanged",
            "production_legacy_rows_unchanged",
        )),
        "runtime_free_generation_allowed": False,
        "a2_unlocked": False,
        "next_short_step": builder.NEXT_SHORT_STEP,
    }
    return {**report_core, "report_sha256": builder.digest(report_core)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("safe", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    safe = json.loads(args.safe.read_text(encoding="utf-8"))
    report = validate_outputs(receipt, safe)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
