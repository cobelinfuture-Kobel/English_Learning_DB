#!/usr/bin/env python3
"""Validate the A1FS V1.1 M02F exact-sequence learner submission FullFix."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ulga.builders import _a1fs_v1_1_m02_exact_sequence_static_adapter as adapter
from ulga.builders import _a1fs_v1_1_m02_release_core as m02_core
from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.builders import build_a1fs_v1_1_m02f_exact_sequence_learner_submission_fullfix as builder

VALIDATOR_ID = "A1FS_V1_1_M02F_EXACT_SEQUENCE_SUBMISSION_VALIDATOR"


class M02FValidationError(ValueError):
    """Fail-closed validation error."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise M02FValidationError(code)


def validate_outputs(
    *, receipt: Mapping[str, Any], safe_report: Mapping[str, Any],
    product_root: Path, output_root: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        _require(receipt.get("task_id") == builder.TASK_ID, "receipt_task_invalid")
        _require(receipt.get("validation_status") == builder.PASS_STATUS, "receipt_status_invalid")
        _require(receipt.get("source_product_version") == builder.SOURCE_VERSION, "source_version_invalid")
        _require(receipt.get("target_product_version") == builder.TARGET_VERSION, "target_version_invalid")
        core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
        _require(receipt.get("artifact_sha256") == builder.digest(core), "receipt_digest_invalid")
        safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
        _require(safe_report.get("report_sha256") == builder.digest(safe_core), "safe_digest_invalid")
        _require(safe_report.get("validation_status") == builder.PASS_STATUS, "safe_status_invalid")

        outputs = receipt.get("runtime_outputs")
        _require(isinstance(outputs, Mapping), "runtime_outputs_missing")
        package_root = Path(str(outputs.get("package_root") or "")).resolve()
        _require(package_root == (Path(output_root).resolve() / "a1fs_v1_1_m02f_exact_sequence_fullfix"), "package_root_invalid")
        candidate = Path(str(outputs.get("candidate_root") or "")).resolve()
        acceptance_root = Path(str(outputs.get("acceptance_product_root") or "")).resolve()
        installer = Path(str(outputs.get("installer_path") or "")).resolve()
        app_js = Path(str(outputs.get("candidate_app_js") or "")).resolve()
        _require(candidate.is_dir(), "candidate_missing")
        _require(acceptance_root.is_dir(), "acceptance_root_missing")
        _require(installer.is_file(), "installer_missing")
        _require(app_js.is_file(), "candidate_app_js_missing")

        manifest = r01.validate_release(candidate)
        _require(manifest.get("product_version") == builder.TARGET_VERSION, "candidate_version_invalid")
        _require(manifest.get("release_id") == builder.RELEASE_ID, "candidate_release_id_invalid")
        _require(
            manifest.get("learner_submission_adapter") == "CONTROLLED_SEQUENCE_TEXT_TO_TOKEN_LIST",
            "candidate_adapter_contract_invalid",
        )
        _require(manifest.get("answer_contract_changed") is False, "answer_contract_changed")
        _require(manifest.get("scoring_authority_changed") is False, "scoring_authority_changed")
        adapter.validate_app_js(app_js)

        acceptance = receipt.get("acceptance_summary", {})
        for key in (
            "r01_atomic_update_pass",
            "shared_state_preserved",
            "controlled_sequence_text_serializes_to_token_list",
            "ordinary_text_serialization_preserved",
        ):
            _require(acceptance.get(key) is True, f"acceptance_invalid:{key}")
        _require(
            r01._current_version(acceptance_root) == builder.TARGET_VERSION,
            "acceptance_current_version_invalid",
        )

        production = Path(product_root).resolve()
        _require(r01._current_version(production) == builder.SOURCE_VERSION, "production_version_mutated")
        _require(
            m02_core.shared_identity(production) == receipt["source_identity"]["shared_identity"],
            "production_shared_identity_mutated",
        )
        safety = receipt.get("production_safety", {})
        for key in (
            "production_current_version_unchanged",
            "production_shared_state_unchanged",
        ):
            _require(safety.get(key) is True, f"production_safety_invalid:{key}")
        for key in (
            "learner_state_migration_required",
            "answer_contract_changed",
            "scoring_authority_changed",
        ):
            _require(safety.get(key) is False, f"production_boundary_invalid:{key}")

        raw_installer = installer.read_bytes()
        _require(raw_installer.startswith(b"param("), "installer_not_ascii_powershell")
        _require(b"\r\n" in raw_installer, "installer_not_crlf")
        _require(not raw_installer.startswith(b"\xef\xbb\xbf"), "installer_bom_forbidden")
        _require(builder.SOURCE_VERSION.encode("ascii") in raw_installer, "installer_source_version_missing")
        _require(builder.TARGET_VERSION.encode("ascii") in raw_installer, "installer_target_version_missing")
    except (
        M02FValidationError,
        adapter.ExactSequenceStaticAdapterError,
        m02_core.ReleaseCoreError,
        r01.ProductRootError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    return {
        "validator_id": VALIDATOR_ID,
        "task_id": builder.TASK_ID,
        "validation_status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
    }
