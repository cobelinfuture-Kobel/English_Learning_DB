#!/usr/bin/env python3
"""Validate A1FS V1.1 M02 local acceptance and release packaging."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import _a1fs_v1_1_m02_release_core as core
from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.builders import build_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as m01
from ulga.builders import build_a1fs_v1_1_m02_unit01_local_product_acceptance_release as builder

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"


class ValidationError(ValueError):
    """Fail-closed M02 validation error."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ValidationError(code)


def _load(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{code}_unreadable:{exc}") from exc
    _require(isinstance(value, dict), f"{code}_not_object")
    return value


def validate_outputs(
    *, receipt: Mapping[str, Any], safe_report: Mapping[str, Any],
    output_root: Path, product_root: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        identity = (
            receipt.get("task_id"), receipt.get("schema_version"),
            receipt.get("validation_status"), receipt.get("product_status"),
            receipt.get("release_id"), receipt.get("stop_reason"),
        )
        _require(
            identity == (
                builder.TASK_ID, builder.SCHEMA_VERSION, builder.PASS_STATUS,
                builder.PRODUCT_STATUS, builder.RELEASE_ID, "NONE",
            ),
            "receipt_identity_invalid",
        )
        body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
        _require(receipt.get("artifact_sha256") == builder.digest(body), "receipt_digest_invalid")
        safe_body = {key: value for key, value in safe_report.items() if key != "report_sha256"}
        _require(safe_report.get("report_sha256") == builder.digest(safe_body), "safe_digest_invalid")
        _require(safe_report.get("validation_status") == builder.PASS_STATUS, "safe_status_invalid")

        summary = receipt.get("release_summary", {})
        expected_summary = {
            "source_product_version": builder.SOURCE_PRODUCT_VERSION,
            "target_product_version": builder.TARGET_PRODUCT_VERSION,
            "release_id": builder.RELEASE_ID,
            "unit_count": 24,
            "lesson_count": 72,
            "asset_count": 264,
            "modified_unit_count": 1,
            "modified_lesson_count": 3,
            "preserved_lesson_count": 69,
            "reading_activity_count": 4,
            "writing_activity_count": 4,
            "speaking_practice_count": 3,
            "candidate_checksum_verified": True,
            "r01_atomic_update_acceptance_pass": True,
            "isolated_local_product_acceptance_pass": True,
            "production_shared_state_unchanged": True,
            "production_response_contracts_unchanged": True,
            "acceptance_shared_state_preserved_during_update": True,
            "acceptance_response_contracts_preserved_during_update": True,
            "installer_created": True,
        }
        for key, expected in expected_summary.items():
            _require(summary.get(key) == expected, f"release_summary_invalid:{key}")

        acceptance = receipt.get("local_acceptance", {})
        for key in (
            "authenticated_http_login_pass",
            "authenticated_bootstrap_pass",
            "authenticated_progress_pass",
            "authenticated_dashboard_pass",
            "unit01_real_reading_visible",
            "unit01_contextual_writing_visible",
            "unit01_speaking_practice_visible",
        ):
            _require(acceptance.get(key) is True, f"acceptance_invalid:{key}")
        _require(acceptance.get("installed_version") == builder.TARGET_PRODUCT_VERSION, "acceptance_version_invalid")
        _require(acceptance.get("unit_count") == 24, "acceptance_unit_count_invalid")
        _require(acceptance.get("lesson_count") == 72, "acceptance_lesson_count_invalid")
        _require(acceptance.get("asset_count") == 264, "acceptance_asset_count_invalid")
        _require(acceptance.get("speaking_practice_card_count") == 3, "acceptance_speaking_count_invalid")
        for skill in ("reading", "writing"):
            lane = acceptance.get(skill, {})
            _require(lane.get("contract_count") == 4, f"acceptance_{skill}_contract_count_invalid")
            _require(lane.get("completion_allowed") is True, f"acceptance_{skill}_completion_invalid")
            _require(lane.get("session_completed") is True, f"acceptance_{skill}_session_invalid")

        _require(
            receipt.get("production_shared_state_before") == receipt.get("production_shared_state_after"),
            "production_shared_state_drift",
        )
        current = (Path(product_root).resolve() / "current_version.txt").read_text(encoding="ascii").strip()
        _require(current == builder.SOURCE_PRODUCT_VERSION, "production_product_root_was_updated")

        boundaries = receipt.get("boundaries", {})
        for key in (
            "production_product_root_updated",
            "production_learner_state_mutated",
            "production_auth_state_mutated",
            "production_response_contract_mutated",
            "parallel_curriculum_created",
            "parallel_state_engine_created",
            "parallel_scoring_engine_created",
            "parallel_mastery_engine_created",
            "parallel_dashboard_engine_created",
            "listening_enabled",
            "audio_enabled",
            "speaking_capture_enabled",
            "a2_unlocked",
            "external_network_binding_allowed",
        ):
            _require(boundaries.get(key) is False, f"boundary_invalid:{key}")

        outputs = receipt.get("runtime_outputs", {})
        package_root = Path(str(outputs.get("package_root") or "")).resolve()
        expected_root = Path(output_root).resolve() / "a1fs_v1_1_unit01_release_package"
        _require(package_root == expected_root, "package_root_identity_invalid")
        for key in (
            "m01_materialization_root",
            "candidate_root",
            "candidate_manifest_path",
            "candidate_checksums_path",
            "update_package_manifest_path",
            "installer_path",
            "acceptance_root",
        ):
            _require(Path(str(outputs.get(key) or "")).exists(), f"output_missing:{key}")
        candidate = Path(str(outputs["candidate_root"]))
        manifest = r01.validate_release(candidate)
        _require(manifest.get("product_version") == builder.TARGET_PRODUCT_VERSION, "candidate_version_invalid")
        _require(manifest.get("release_id") == builder.RELEASE_ID, "candidate_release_id_invalid")
        _require(manifest.get("modified_unit_ids") == [m01.UNIT_ID], "candidate_modified_unit_invalid")
        _require(manifest.get("learner_state_migration_required") is False, "candidate_state_migration_forbidden")
        _require(manifest.get("shared_state_packaged_as_release_authority") is False, "candidate_shared_authority_forbidden")
        package = _load(Path(str(outputs["update_package_manifest_path"])), "update_package")
        _require(package.get("production_state_packaged") is False, "production_state_packaging_forbidden")
        _require(package.get("production_state_mutated") is False, "production_state_mutation_invalid")
        installer = Path(str(outputs["installer_path"]))
        raw = installer.read_bytes()
        _require(raw.startswith(b"param("), "installer_header_invalid")
        _require(b"\r\n" in raw and not raw.startswith(b"\xef\xbb\xbf"), "installer_encoding_invalid")
        approved = _load(
            Path(str(outputs["m01_materialization_root"])) / "content/unit01.approved.private.json",
            "m01_approved",
        )
        _require(
            approved.get("artifact_sha256") == receipt.get("source_identity", {}).get("m01_approved_content_sha256"),
            "m01_approved_identity_invalid",
        )
        _require(approved.get("admission", {}).get("status") == "APPROVED", "m01_approved_status_invalid")
        core.validate_overlay(
            source_bundles=r01._load_product(Path(product_root))[2],
            target_bundles=_load(candidate / "runtime/bundles.json", "candidate_bundles"),
        )
    except (ValidationError, core.ReleaseCoreError, r01.ProductRootError, OSError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return {
        "task_id": builder.TASK_ID,
        "validation_status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
    }
