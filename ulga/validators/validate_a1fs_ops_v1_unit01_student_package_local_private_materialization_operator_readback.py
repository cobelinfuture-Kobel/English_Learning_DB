#!/usr/bin/env python3
"""Validate the Unit01 local private operator materialization and safe readback."""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_local_private_materialization_operator_readback
    as builder,
)
from ulga.validators import (
    validate_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as entry_validator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reads the existing disposable V1.2.1 product, merged entry acceptance, operator "
    "safe readback, release checksums, and learner-safe static files. It creates no "
    "content, answer, bank, planner, state, score, release, audio, A2 content, or "
    "Unit02-Unit24 artifact."
)
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_STUDENT_LOCAL_PRIVATE_OPERATOR_VALIDATION"
FAIL_STATUS = "FAIL_A1FS_OPS_V1_UNIT01_STUDENT_LOCAL_PRIVATE_OPERATOR_VALIDATION"

FORBIDDEN_KEYS = {
    "password",
    "token",
    "cookie",
    "csrf",
    "session_secret",
    "subject_key",
    "database_path",
    "approved_content_path",
    "product_root",
}


def _walk_safe(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_KEYS:
                raise ValueError(f"operator_readback_private_key:{key}")
            _walk_safe(child)
    elif isinstance(value, list):
        for child in value:
            _walk_safe(child)
    elif isinstance(value, str):
        normalized = value.replace("\\", "/")
        if normalized.startswith("/") or ":/" in normalized:
            raise ValueError("operator_readback_absolute_path_exposed")


def _relative_path(value: Any, code: str) -> str:
    text = str(value or "")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts or ":" in text:
        raise ValueError(f"operator_relative_path_invalid:{code}")
    return text


def validate(
    *,
    product_root: Path,
    approved_content: Mapping[str, Any],
    report_path: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    counts: dict[str, Any] = {}
    root = Path(product_root).resolve()
    path = (
        Path(report_path).resolve()
        if report_path is not None
        else root / "shared/reports" / builder.REPORT_NAME
    )
    try:
        report = builder.entry_builder.load(path)
        core = {
            key: value
            for key, value in report.items()
            if key != "readback_sha256"
        }
        if report.get("readback_sha256") != builder.entry_builder.digest(core):
            raise ValueError("operator_readback_digest_invalid")
        _walk_safe(report)
        expected = {
            "status": builder.PASS_STATUS,
            "product_version": builder.v121.TARGET_VERSION,
            "runtime_item_count": 474,
            "entry_acceptance_status": builder.entry_builder.PASS_STATUS,
            "entry_validation_status": entry_validator.PASS_STATUS,
            "real_v121_application_used": True,
            "real_learner_database_used": True,
            "existing_auth_boundary_reused": True,
            "existing_progress_api_reused": True,
            "existing_question_bank_reused": True,
            "second_question_bank_created": False,
            "formal_production_activation_approved": False,
            "production_root_mutated": False,
            "public_delivery": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
            "secrets_serialized": False,
            "absolute_local_paths_serialized": False,
        }
        for key, expected_value in expected.items():
            if report.get(key) != expected_value:
                raise ValueError(f"operator_{key}_invalid")
        http = report.get("runtime_http_readback") or {}
        http_expected = {
            "loopback_only": True,
            "unauthenticated_prelearning_status": 401,
            "authenticated_login_pass": True,
            "authenticated_bootstrap_status": 200,
            "authenticated_progress_status": 200,
            "authenticated_prelearning_status": 200,
            "authenticated_questionbank_status": 200,
            "unit_count": 24,
            "product_version": builder.v121.TARGET_VERSION,
            "prelearning_marker_pass": True,
            "questionbank_marker_pass": True,
            "security_headers_pass": True,
            "cookie_http_only": True,
            "cookie_same_site_strict": True,
            "real_v121_application_used": True,
            "real_learner_database_used": True,
            "real_progress_api_used": True,
        }
        for key, expected_value in http_expected.items():
            if http.get(key) != expected_value:
                raise ValueError(f"operator_http_{key}_invalid")
        relative_fields = (
            "entry_report_path",
            "operator_report_path",
            "release_manifest_path",
            "release_checksums_path",
            "learner_entry_root",
        )
        for field in relative_fields:
            relative = _relative_path(report.get(field), field)
            candidate = root / relative
            if not candidate.exists():
                raise ValueError(f"operator_relative_artifact_missing:{field}")
        if (root / str(report["operator_report_path"])).resolve() != path:
            raise ValueError("operator_report_path_identity_invalid")

        entry_result = entry_validator.validate(
            disposable_product_root=root,
            approved_content=approved_content,
        )
        if entry_result.get("validation_status") != entry_validator.PASS_STATUS:
            raise ValueError(
                "operator_entry_revalidation_failed:"
                + "|".join(str(row) for row in entry_result.get("errors") or [])
            )
        runtime = builder.load_operator_runtime(root)
        if runtime["release_manifest"].get("product_version") != builder.v121.TARGET_VERSION:
            raise ValueError("operator_release_revalidation_failed")
        counts = {
            "runtime_item_count": int(report["runtime_item_count"]),
            "unit_count": int(http["unit_count"]),
            "authenticated_route_count": 4,
            "relative_artifact_count": len(relative_fields),
            "entry_validation_error_count": int(entry_result["error_count"]),
        }
    except (ValueError, OSError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        **counts,
        "secrets_serialized": False,
        "absolute_local_paths_serialized": False,
        "second_question_bank_created": False,
        "formal_production_activation_approved": False,
        "production_root_mutated": False,
        "public_delivery": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-root", type=Path, required=True)
    parser.add_argument("--approved-content", type=Path, required=True)
    parser.add_argument("--report-path", type=Path)
    args = parser.parse_args(argv)
    result = validate(
        product_root=args.product_root,
        approved_content=builder.entry_builder.load(args.approved_content),
        report_path=args.report_path,
    )
    print(result)
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
