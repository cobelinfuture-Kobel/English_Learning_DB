#!/usr/bin/env python3
"""Validate the additive Unit 01 coverage runtime and learner-safe readback."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s04_coverage_runtime_readback as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_ONLINE_V1_2_U01E_S04_COVERAGE_RUNTIME_READBACK_VALIDATOR"


class S04ValidationError(ValueError):
    """Fail-closed S04 validation error."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise S04ValidationError(code)


def validate_outputs(
    receipt: Mapping[str, Any], safe_report: Mapping[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        require(receipt.get("task_id") == builder.TASK_ID, "receipt_task_invalid")
        require(receipt.get("validation_status") == builder.PASS_STATUS, "receipt_status_invalid")
        require(receipt.get("product_status") == builder.PRODUCT_STATUS, "receipt_product_status_invalid")
        core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
        require(receipt.get("artifact_sha256") == builder.digest(core), "receipt_digest_invalid")
        safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
        require(safe_report.get("report_sha256") == builder.digest(safe_core), "safe_digest_invalid")
        require(safe_report.get("validation_status") == builder.PASS_STATUS, "safe_status_invalid")

        outputs = receipt.get("runtime_outputs", {})
        database = Path(str(outputs.get("database_path") or ""))
        bundles = Path(str(outputs.get("bundles_path") or ""))
        static_root = Path(str(outputs.get("secure_static_root") or ""))
        require(database.is_file(), "runtime_database_missing")
        require(bundles.is_file(), "runtime_bundles_missing")
        require(static_root.is_dir(), "runtime_static_missing")
        for name in ("index.html", "app.js", "styles.css"):
            require((static_root / name).is_file(), f"runtime_static_file_missing:{name}")
        app_js = (static_root / "app.js").read_text(encoding="utf-8")
        index_html = (static_root / "index.html").read_text(encoding="utf-8")
        require("/api/coverage" in app_js, "coverage_endpoint_not_consumed")
        require("loadU01eCoverage" in app_js, "coverage_loader_missing")
        require("u01e-coverage-panel" in index_html, "coverage_panel_missing")
        require("candidate_items" not in app_js, "candidate_bank_leaked_to_static")

        migration = receipt.get("migration_summary", {})
        expected_migration = {
            "source_asset_count": 264,
            "target_asset_count": 277,
            "response_contract_count": 277,
            "target_binding_count": 24,
            "added_asset_count": 13,
            "speaking_capture_enabled_count": 0,
            "protected_state_preserved": True,
        }
        for key, expected in expected_migration.items():
            require(migration.get(key) == expected, f"migration_summary_invalid:{key}")
        require(
            migration.get("source_protected_sha256")
            == migration.get("target_protected_sha256"),
            "protected_state_digest_changed",
        )

        bundle = receipt.get("bundle_summary", {})
        require(bundle.get("unit_count") == 24, "unit_count_invalid")
        require(bundle.get("lesson_count") == 72, "lesson_count_invalid")
        require(bundle.get("asset_count") == 277, "asset_count_invalid")
        require(bundle.get("unit01_activity_count") == 24, "unit01_activity_count_invalid")
        require(bundle.get("unit01_skill_counts") == builder.EXPECTED_UNIT01_COUNTS, "unit01_skill_counts_invalid")
        require(bundle.get("modified_lesson_count") == 3, "modified_lesson_count_invalid")
        require(bundle.get("preserved_lesson_count") == 69, "preserved_lesson_count_invalid")

        coverage = receipt.get("coverage_readback", {})
        require(coverage.get("validation_status") == builder.PASS_STATUS, "coverage_status_invalid")
        activity = coverage.get("activity_summary", {})
        require(activity.get("selected_activity_count") == 24, "coverage_selected_activity_invalid")
        require(activity.get("by_skill") == builder.EXPECTED_UNIT01_COUNTS, "coverage_skill_counts_invalid")
        dimensions = coverage.get("coverage_dimensions", {})
        for dimension in builder.TARGET_DIMENSIONS:
            row = dimensions.get(dimension)
            require(isinstance(row, Mapping), f"coverage_dimension_missing:{dimension}")
            for field in ("selected_count", "exposed_count", "practised_count", "assessed_count"):
                require(isinstance(row.get(field), int), f"coverage_count_invalid:{dimension}:{field}")
            require(row.get("stable_count") is None, f"stable_overclaimed:{dimension}")
            require(row.get("mastered_count") is None, f"mastery_overclaimed:{dimension}")
            require(row.get("stable_status") == "NOT_AVAILABLE_FROM_CURRENT_EVIDENCE", f"stable_status_invalid:{dimension}")
            require(row.get("mastery_status") == "NOT_AVAILABLE_FROM_CURRENT_EVIDENCE", f"mastery_status_invalid:{dimension}")
        require(dimensions["EVP_SENSE"]["denominator"] == 784, "evp_denominator_invalid")
        require(dimensions["EGP_ROW"]["denominator"] == 109, "egp_denominator_invalid")
        require(dimensions["CANONICAL_CHUNK"]["denominator"] == 76, "chunk_denominator_invalid")
        require(dimensions["PATTERN"]["denominator"] == 27, "pattern_denominator_invalid")
        require(dimensions["KET_PREREQUISITE"]["denominator"] == 553, "ket_denominator_invalid")
        require(dimensions["KET_PREREQUISITE"]["selected_count"] == 0, "ket_selected_overclaim")
        require(dimensions["KET_PREREQUISITE"]["practised_count"] == 0, "ket_practised_overclaim")
        require(
            coverage.get("ket_readback", {}).get("coverage_claim_allowed") is False,
            "ket_coverage_claim_allowed",
        )
        require(
            coverage.get("cambridge_stage_readback", {}).get("granular_capability_percentage") is None,
            "cambridge_capability_percentage_overclaim",
        )

        compatibility = receipt.get("compatibility", {})
        for key in (
            "additive_tables_only",
            "v1_1_read_compatibility_expected",
        ):
            require(compatibility.get(key) is True, f"compatibility_true_invalid:{key}")
        for key in (
            "existing_table_shape_changed",
            "existing_response_contract_rows_changed",
            "existing_attempt_rows_changed",
            "existing_score_rows_changed",
            "existing_asset_rows_changed",
        ):
            require(compatibility.get(key) is False, f"compatibility_false_invalid:{key}")
        boundaries = receipt.get("boundaries", {})
        for key in (
            "production_database_mutated",
            "learner_state_authority_changed",
            "scoring_authority_replaced",
            "mastery_inferred",
            "runtime_free_generation_enabled",
            "unit02_modified",
            "audio_enabled",
            "speaking_capture_enabled",
            "a2_unlocked",
        ):
            require(boundaries.get(key) is False, f"boundary_invalid:{key}")
        safe_summary = safe_report.get("coverage_summary", {})
        require(
            safe_summary.get("activity_summary") == activity,
            "safe_activity_summary_drift",
        )
    except (S04ValidationError, OSError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return {
        "validator_id": VALIDATOR_ID,
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else builder.TASK_ID,
    }
