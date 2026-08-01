#!/usr/bin/env python3
"""Validate Unit01 local-private materialization and operator readback."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_local_private_materialization_operator_readback
    as builder,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_prelearning_v2_fullfix as prelearning_v2,
)
from ulga.validators import (
    validate_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as acceptance_validator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reads the local-safe operator readback, merged Unit01 acceptance artifacts, "
    "approved-content identity, Chromium outputs, authenticated HTTP evidence, "
    "release checksums, and learner-safe entry files. It creates no content, "
    "question, answer, bank, planner, renderer, learner state authority, scoring "
    "authority, audio, A2 content, Unit02-24 artifact, production activation, or "
    "public delivery."
)

PASS_STATUS = (
    "PASS_A1FS_OPS_V1_UNIT01_STUDENT_LOCAL_PRIVATE_OPERATOR_READBACK_VALIDATION"
)
FAIL_STATUS = (
    "FAIL_A1FS_OPS_V1_UNIT01_STUDENT_LOCAL_PRIVATE_OPERATOR_READBACK_VALIDATION"
)


def _relative_output_contract(
    package_root: Path,
    outputs: Mapping[str, Any],
) -> int:
    expected_names = {
        "learner_launcher",
        "prelearning_html",
        "questionbank_html",
        "prelearning_pdf",
        "questionbank_sample_pdf",
        "prelearning_png",
        "questionbank_sample_png",
    }
    if set(outputs) != expected_names:
        raise ValueError("operator_relative_output_key_set_invalid")
    for key, raw_name in outputs.items():
        name = str(raw_name or "")
        path = Path(name)
        if (
            not name
            or path.is_absolute()
            or ":" in name
            or ".." in path.parts
        ):
            raise ValueError(f"operator_relative_output_unsafe:{key}")
        if not (Path(package_root) / path).is_file():
            raise ValueError(f"operator_relative_output_missing:{key}")
    return len(outputs)


def validate(
    *,
    disposable_product_root: Path,
    approved_content_path: Path | None = None,
    search_roots: Sequence[Path] = (),
    output_root: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    counts: dict[str, Any] = {}
    disposable_product_root = Path(disposable_product_root).resolve()
    report_path = (
        disposable_product_root
        / "shared"
        / "reports"
        / builder.REPORT_NAME
    )
    try:
        report = builder.load(report_path)
        core = {
            key: value
            for key, value in report.items()
            if key != "readback_sha256"
        }
        if report.get("readback_sha256") != builder.digest(core):
            raise ValueError("operator_readback_digest_invalid")
        expected = {
            "schema_version": builder.SCHEMA_VERSION,
            "program_id": builder.PROGRAM_ID,
            "task_id": builder.TASK_ID,
            "status": builder.PASS_STATUS,
            "product_version": "1.2.1",
            "runtime_item_count": 474,
            "chromium_render_count": 4,
            "unauthenticated_prelearning_status": 401,
            "authenticated_prelearning_status": 200,
            "authenticated_questionbank_status": 200,
            "teacher_files_unchanged": True,
            "source_product_root_unchanged": True,
            "disposable_release_checksums_refreshed": True,
            "operator_visual_confirmation_required": True,
            "operator_visual_confirmation_completed": False,
            "formal_production_activation_approved": False,
            "production_root_mutated": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
            "next_short_step": builder.NEXT_SHORT_STEP,
        }
        for key, value in expected.items():
            if report.get(key) != value:
                raise ValueError(f"operator_readback_{key}_invalid")
        expected_prelearning_pages = int(
            prelearning_v2.EXPECTED_PRINT_PAGE_COUNT
        )
        actual_prelearning_pages = int(
            report.get("prelearning_pdf_page_count") or 0
        )
        if actual_prelearning_pages != expected_prelearning_pages:
            raise ValueError(
                "operator_prelearning_pdf_page_count_invalid:"
                f"expected={expected_prelearning_pages}:"
                f"actual={actual_prelearning_pages}"
            )
        if int(
            report.get("questionbank_sample_pdf_page_count") or 0
        ) < 7:
            raise ValueError(
                "operator_questionbank_sample_pdf_page_count_invalid"
            )
        expected_sha = str(
            report.get("approved_content_artifact_sha256") or ""
        )
        if len(expected_sha) != 64:
            raise ValueError(
                "operator_approved_content_artifact_sha256_invalid"
            )
        roots = list(search_roots) or builder._default_search_roots(
            disposable_product_root
        )
        approved_path, _mode = builder.discover_approved_content(
            expected_sha=expected_sha,
            explicit_path=approved_content_path,
            search_roots=roots,
        )
        if approved_path.name != report.get("approved_content_file_name"):
            raise ValueError("operator_approved_content_file_name_invalid")
        approved_content = builder.load(approved_path)

        acceptance_result = acceptance_validator.validate(
            disposable_product_root=disposable_product_root,
            approved_content=approved_content,
            output_root=output_root,
        )
        if (
            acceptance_result.get("validation_status")
            != acceptance_validator.PASS_STATUS
        ):
            raise ValueError(
                "operator_acceptance_validation_failed:"
                + "|".join(
                    str(row)
                    for row in acceptance_result.get("errors") or []
                )
            )

        package_root = (
            Path(output_root).resolve()
            if output_root is not None
            else disposable_product_root
            / "shared"
            / "print_packages"
            / "unit01"
        )
        output_count = _relative_output_contract(
            package_root,
            report.get("package_relative_outputs") or {},
        )
        counts = {
            "runtime_item_count": report["runtime_item_count"],
            "chromium_render_count": report["chromium_render_count"],
            "prelearning_pdf_page_count": report[
                "prelearning_pdf_page_count"
            ],
            "questionbank_sample_pdf_page_count": report[
                "questionbank_sample_pdf_page_count"
            ],
            "operator_output_file_count": output_count,
            "authenticated_http_route_count": 2,
            "teacher_file_count_preserved": acceptance_result[
                "teacher_file_count_preserved"
            ],
        }
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        errors.append(str(exc))
    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        **counts,
        "operator_visual_confirmation_required": True,
        "operator_visual_confirmation_completed": False,
        "authenticated_http_readback_pass": not errors,
        "teacher_files_unchanged": not errors,
        "source_product_root_unchanged": not errors,
        "formal_production_activation_approved": False,
        "production_root_mutated": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--disposable-product-root",
        type=Path,
        required=True,
    )
    parser.add_argument("--approved-content", type=Path)
    parser.add_argument(
        "--search-root",
        action="append",
        default=[],
        type=Path,
    )
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args(argv)
    result = validate(
        disposable_product_root=args.disposable_product_root,
        approved_content_path=args.approved_content,
        search_roots=args.search_root,
        output_root=args.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
