#!/usr/bin/env python3
'''Validate Unit01 Chromium print and disposable main-product entry acceptance.'''
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_canonical_question_bank_vocabulary_chunk_sentence_printable_master_package
    as master,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as builder,
)
from ulga.validators import (
    validate_a1fs_ops_v1_unit01_questionbank_student_package_phrase_to_sentence
    as student_validator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reads disposable learner package, Chromium artifacts, authenticated HTTP "
    "readback, secure-static entry, source identity, and teacher hashes. It creates "
    "no learner content, answer, bank, planner, state, score, renderer, audio, A2 "
    "content, or Unit02-24 artifact."
)
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_STUDENT_CHROMIUM_MAIN_ENTRY_VALIDATION"
FAIL_STATUS = "FAIL_A1FS_OPS_V1_UNIT01_STUDENT_CHROMIUM_MAIN_ENTRY_VALIDATION"


def _validate_http_readback(value: Mapping[str, Any]) -> None:
    expected = {
        "loopback_only": True,
        "unauthenticated_prelearning_status": 401,
        "unauthenticated_access_blocked": True,
        "authenticated_login_pass": True,
        "authenticated_prelearning_status": 200,
        "authenticated_questionbank_status": 200,
        "authenticated_prelearning_marker_pass": True,
        "authenticated_questionbank_marker_pass": True,
        "security_headers_pass": True,
        "cookie_http_only": True,
        "cookie_same_site_strict": True,
        "unauthenticated_security_headers_pass": True,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValueError(f"authenticated_http_{key}_invalid")


def validate(
    *,
    disposable_product_root: Path,
    approved_content: Mapping[str, Any],
    output_root: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    counts: dict[str, Any] = {}
    disposable_product_root = Path(disposable_product_root).resolve()
    package_root = (
        Path(output_root).resolve()
        if output_root is not None
        else disposable_product_root / master.DEFAULT_RELATIVE_OUTPUT
    )
    try:
        student = student_validator.validate(
            disposable_product_root=disposable_product_root,
            approved_content=approved_content,
            output_root=package_root,
        )
        if student.get("validation_status") != student_validator.PASS_STATUS:
            raise ValueError(
                "student_package_validation_failed:"
                + "|".join(str(row) for row in student.get("errors") or [])
            )
        report = builder.load(package_root / builder.REPORT_NAME)
        core = {key: value for key, value in report.items() if key != "readback_sha256"}
        if report.get("readback_sha256") != builder.digest(core):
            raise ValueError("acceptance_readback_digest_invalid")
        expected = {
            "status": builder.PASS_STATUS,
            "product_version": builder.EXPECTED_PRODUCT_VERSION,
            "runtime_item_count": master.EXPECTED_RUNTIME_ITEMS,
            "chromium_render_count": 4,
            "prelearning_pdf_pass": True,
            "questionbank_stage_sample_pdf_pass": True,
            "chromium_screenshot_pass": True,
            "main_product_entry_integrated_in_disposable": True,
            "authenticated_static_boundary_required": True,
            "unauthenticated_access_blocked": True,
            "authenticated_entry_http_pass": True,
            "teacher_files_unchanged": True,
            "source_product_root_unchanged": True,
            "second_question_bank_created": False,
            "formal_production_activation_approved": False,
            "production_root_mutated": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        }
        for key, value in expected.items():
            if report.get(key) != value:
                raise ValueError(f"acceptance_{key}_invalid")
        if int(report.get("prelearning_pdf_page_count") or 0) < 7:
            raise ValueError("prelearning_pdf_page_count_invalid")
        if int(report.get("questionbank_sample_pdf_page_count") or 0) < 7:
            raise ValueError("questionbank_sample_pdf_page_count_invalid")
        if not str(report.get("chromium_version") or "").strip():
            raise ValueError("chromium_version_missing")
        if not str(report.get("chromium_executable_name") or "").strip():
            raise ValueError("chromium_executable_name_missing")
        _validate_http_readback(report.get("authenticated_http_readback") or {})

        _version, static_root = builder._product_static_root(disposable_product_root)
        main_entry = builder.validate_main_entry(static_root)
        if main_entry.get("validation_status") != builder.PASS_STATUS:
            raise ValueError("main_entry_validation_invalid")
        entry_root = static_root / builder.ENTRY_DIRECTORY
        learner_text = "\n".join(
            (entry_root / name).read_text(encoding="utf-8")
            for name in ("index.html", "prelearning.html", "questionbank.html")
        ).casefold()
        for marker in (
            "correct_answer",
            "accepted_answers",
            "response_contract",
            "teacher/index.private.html",
            "private_item_json",
        ):
            if marker in learner_text:
                raise ValueError(f"main_entry_private_marker_exposed:{marker}")

        teacher_identities = report.get("teacher_file_identities") or {}
        if len(teacher_identities) != 2:
            raise ValueError("teacher_identity_count_invalid")
        for name, identity in teacher_identities.items():
            if master.file_identity(package_root / str(name)) != identity:
                raise ValueError(f"teacher_file_identity_invalid:{name}")

        package_files = report.get("package_files") or {}
        if len(package_files) != 6:
            raise ValueError("acceptance_package_file_count_invalid")
        for name, identity in package_files.items():
            candidate = package_root / str(name)
            if not candidate.is_file():
                raise ValueError(f"acceptance_package_file_missing:{name}")
            if builder.file_identity(candidate) != identity:
                raise ValueError(f"acceptance_package_file_identity_invalid:{name}")

        product_entry_files = report.get("product_entry_files") or {}
        if len(product_entry_files) != 7:
            raise ValueError("product_entry_file_count_invalid")
        for name, identity in product_entry_files.items():
            candidate = static_root / str(name)
            if not candidate.is_file():
                raise ValueError(f"product_entry_file_missing:{name}")
            if builder.file_identity(candidate) != identity:
                raise ValueError(f"product_entry_file_identity_invalid:{name}")

        acceptance = package_root / "acceptance"
        prelearning_pdf = acceptance / "unit01_prelearning_chromium.pdf"
        sample_pdf = acceptance / "unit01_questionbank_stage_sample_chromium.pdf"
        prelearning_png = acceptance / "unit01_prelearning_chromium.png"
        sample_png = acceptance / "unit01_questionbank_stage_sample_chromium.png"
        if builder._pdf_page_count(prelearning_pdf) < 7:
            raise ValueError("prelearning_pdf_revalidation_failed")
        if builder._pdf_page_count(sample_pdf) < 7:
            raise ValueError("sample_pdf_revalidation_failed")
        if not builder._png_valid(prelearning_png) or not builder._png_valid(sample_png):
            raise ValueError("png_revalidation_failed")

        integration_report = master._integration_report(disposable_product_root)
        source_root = Path(str(integration_report["source_product_root"]))
        master.integration._product_identity(source_root)
        counts = {
            "runtime_item_count": report["runtime_item_count"],
            "prelearning_pdf_page_count": report["prelearning_pdf_page_count"],
            "questionbank_sample_pdf_page_count": report[
                "questionbank_sample_pdf_page_count"
            ],
            "chromium_render_count": report["chromium_render_count"],
            "teacher_file_count_preserved": len(teacher_identities),
            "main_entry_file_count": len(product_entry_files),
            "authenticated_http_route_count": 2,
        }
    except (ValueError, OSError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        **counts,
        "authenticated_http_readback_pass": not errors,
        "learner_answer_leakage_count": 0,
        "teacher_files_unchanged": not errors,
        "source_product_root_unchanged": not errors,
        "second_question_bank_created": False,
        "formal_production_activation_approved": False,
        "production_root_mutated": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disposable-product-root", type=Path, required=True)
    parser.add_argument("--approved-content", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args(argv)
    result = validate(
        disposable_product_root=args.disposable_product_root,
        approved_content=master.load(args.approved_content),
        output_root=args.output_root,
    )
    print(result)
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
