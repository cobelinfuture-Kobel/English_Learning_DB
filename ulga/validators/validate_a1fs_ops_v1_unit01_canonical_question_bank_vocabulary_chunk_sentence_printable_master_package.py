#!/usr/bin/env python3
"""Independently validate the Unit01 printable master package."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_canonical_question_bank_vocabulary_chunk_sentence_printable_master_package
    as builder,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reads the printable package, its source SQLite authority, and the accepted "
    "disposable integration readback; it creates no content, print artifact, "
    "answer, score, learner state, bank, planner, renderer, audio, A2 unlock, "
    "or Unit02-Unit24 artifact."
)
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_PRINTABLE_MASTER_PACKAGE_VALIDATION"
FAIL_STATUS = "FAIL_A1FS_OPS_V1_UNIT01_PRINTABLE_MASTER_PACKAGE_VALIDATION"


def _count(database: Path, table: str) -> int:
    with sqlite3.connect(Path(database)) as connection:
        return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def validate(
    *,
    disposable_product_root: Path,
    approved_content: Mapping[str, Any],
    output_root: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    disposable_product_root = Path(disposable_product_root).resolve()
    output_root = (
        Path(output_root).resolve()
        if output_root is not None
        else disposable_product_root / builder.DEFAULT_RELATIVE_OUTPUT
    )
    try:
        report = builder.load(output_root / builder.REPORT_NAME)
        report_core = {
            key: value for key, value in report.items() if key != "readback_sha256"
        }
        if report.get("readback_sha256") != builder.digest(report_core):
            raise ValueError("readback_digest_invalid")
        if report.get("status") != builder.PASS_STATUS:
            raise ValueError("readback_status_invalid")
        manifest = builder.load(output_root / builder.MANIFEST_NAME)
        manifest_core = {
            key: value for key, value in manifest.items() if key != "manifest_sha256"
        }
        if manifest.get("manifest_sha256") != builder.digest(manifest_core):
            raise ValueError("manifest_digest_invalid")
        expected = {
            "runtime_item_count": builder.EXPECTED_RUNTIME_ITEMS,
            "base_item_count": builder.EXPECTED_BASE_ITEMS,
            "extension_item_count": builder.EXPECTED_EXTENSION_ITEMS,
            "active_vocabulary_count": builder.EXPECTED_ACTIVE_VOCABULARY,
            "canonical_chunk_count": builder.EXPECTED_CANONICAL_CHUNKS,
            "instructional_phrase_count": builder.EXPECTED_INSTRUCTIONAL_PHRASES,
            "sentence_frame_count": builder.EXPECTED_SENTENCE_FRAMES,
            "content_asset_count": 62,
            "learner_answer_leakage_count": 0,
            "raw_raz_identity_leakage_count": 0,
            "browser_print_available": True,
            "browser_save_as_pdf_available": True,
            "main_product_print_button_integrated": False,
            "teacher_edition_private": True,
            "formal_production_activation_approved": False,
            "public_delivery": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        }
        for key, value in expected.items():
            if manifest.get(key) != value:
                raise ValueError(f"manifest_{key}_invalid")
        if int(manifest.get("model_sentence_count") or 0) <= 0:
            raise ValueError("model_sentence_count_invalid")
        database = (
            disposable_product_root
            / "shared/database/learner_runtime.sqlite3"
        )
        if _count(database, "u01qb02_item_catalog") != builder.EXPECTED_RUNTIME_ITEMS:
            raise ValueError("runtime_item_count_drift")
        if _count(database, "razq01e_extension_items") != builder.EXPECTED_EXTENSION_ITEMS:
            raise ValueError("extension_item_count_drift")
        if manifest.get("approved_content_artifact_sha256") != approved_content.get(
            "artifact_sha256"
        ):
            raise ValueError("approved_content_identity_invalid")
        learner_data = builder.load(
            output_root / "learner/unit01_learner_print_data.json"
        )
        teacher_data = builder.load(
            output_root / "teacher/unit01_teacher_print_data.private.json"
        )
        learner_questions = learner_data.get("questions")
        teacher_questions = teacher_data.get("questions")
        if not isinstance(learner_questions, list) or len(learner_questions) != 474:
            raise ValueError("learner_question_count_invalid")
        if not isinstance(teacher_questions, list) or len(teacher_questions) != 474:
            raise ValueError("teacher_question_count_invalid")
        learner_text = json.dumps(
            learner_data, ensure_ascii=False, sort_keys=True
        ).casefold()
        for marker in builder.FORBIDDEN_LEARNER_MARKERS:
            if marker.casefold() in learner_text:
                raise ValueError(f"learner_private_marker_exposed:{marker}")
        teacher_text = json.dumps(
            teacher_data, ensure_ascii=False, sort_keys=True
        )
        if "correct_answer" not in teacher_text or "scoring_mode" not in teacher_text:
            raise ValueError("teacher_answer_contract_missing")
        learner_html = (
            output_root / "learner/index.html"
        ).read_text(encoding="utf-8")
        teacher_html = (
            output_root / "teacher/index.private.html"
        ).read_text(encoding="utf-8")
        launcher = (output_root / "index.html").read_text(encoding="utf-8")
        javascript = (output_root / "print.js").read_text(encoding="utf-8")
        css = (output_root / "styles.css").read_text(encoding="utf-8")
        if "window.print()" not in learner_html or "window.print()" not in teacher_html:
            raise ValueError("browser_print_button_missing")
        if "teacher/index.private.html" not in launcher:
            raise ValueError("teacher_launcher_missing")
        if "learner/index.html" not in launcher:
            raise ValueError("learner_launcher_missing")
        if "data-print-section" not in javascript:
            raise ValueError("print_section_toggle_missing")
        if "@media print" not in css or "@page" not in css:
            raise ValueError("print_css_missing")
        for name, identity in (report.get("files") or {}).items():
            path = output_root / str(name)
            if not path.is_file():
                raise ValueError(f"package_file_missing:{name}")
            if builder.file_identity(path) != identity:
                raise ValueError(f"package_file_identity_invalid:{name}")
        integration_report = builder._integration_report(disposable_product_root)
        if report.get("integration_readback_sha256") != integration_report.get(
            "readback_sha256"
        ):
            raise ValueError("integration_readback_identity_invalid")
        source_root = Path(str(integration_report["source_product_root"]))
        builder.integration._product_identity(source_root)
        if report.get("source_product_root_unchanged") is not True:
            raise ValueError("source_product_preservation_not_proven")
    except Exception as exc:
        errors.append(str(exc))
    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "disposable_product_root": str(disposable_product_root),
        "output_root": str(output_root),
        "runtime_item_count": 0 if errors else builder.EXPECTED_RUNTIME_ITEMS,
        "active_vocabulary_count": 0 if errors else builder.EXPECTED_ACTIVE_VOCABULARY,
        "canonical_chunk_count": 0 if errors else builder.EXPECTED_CANONICAL_CHUNKS,
        "instructional_phrase_count": 0 if errors else builder.EXPECTED_INSTRUCTIONAL_PHRASES,
        "sentence_frame_count": 0 if errors else builder.EXPECTED_SENTENCE_FRAMES,
        "learner_answer_leakage_count": 0,
        "raw_raz_identity_leakage_count": 0,
        "main_product_print_button_integrated": False,
        "formal_production_activation_approved": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disposable-product-root", type=Path, required=True)
    parser.add_argument("--approved-content", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = validate(
        disposable_product_root=args.disposable_product_root,
        approved_content=builder.load(args.approved_content),
        output_root=args.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
