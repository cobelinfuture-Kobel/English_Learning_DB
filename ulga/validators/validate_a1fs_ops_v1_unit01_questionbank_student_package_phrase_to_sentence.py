#!/usr/bin/env python3
"""Validate the learner-only Unit01 phrase-to-sentence printable package."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_canonical_question_bank_vocabulary_chunk_sentence_printable_master_package
    as master,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_questionbank_student_package_phrase_to_sentence
    as builder,
)
from ulga.validators import (
    validate_a1fs_ops_v1_unit01_canonical_question_bank_vocabulary_chunk_sentence_printable_master_package
    as master_validator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reads the learner package, existing printable-master report, and teacher "
    "file identities to validate learner safety, canonical denominators, print "
    "structure, and teacher preservation. It creates no content, answer, bank, "
    "renderer, state, score, audio, A2 content, or Unit02-24 artifact."
)
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_STUDENT_PHRASE_TO_SENTENCE_PACKAGE_VALIDATION"
FAIL_STATUS = "FAIL_A1FS_OPS_V1_UNIT01_STUDENT_PHRASE_TO_SENTENCE_PACKAGE_VALIDATION"
IMAGE_MARKERS = ("<img", "<picture", "<svg", "background-image", "data:image")


def _walk_forbidden(value: Any, forbidden: Sequence[str]) -> list[str]:
    found: list[str] = []
    forbidden_set = {row.casefold() for row in forbidden}

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden_set:
                    found.append(str(key))
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return found


def validate(
    *,
    disposable_product_root: Path,
    approved_content: Mapping[str, Any],
    output_root: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    counts: dict[str, Any] = {}
    disposable_product_root = Path(disposable_product_root).resolve()
    output_root = (
        Path(output_root).resolve()
        if output_root is not None
        else disposable_product_root / master.DEFAULT_RELATIVE_OUTPUT
    )
    try:
        base = master_validator.validate(
            disposable_product_root=disposable_product_root,
            approved_content=approved_content,
            output_root=output_root,
        )
        if base.get("validation_status") != master_validator.PASS_STATUS:
            raise ValueError(
                "base_printable_validation_failed:"
                + "|".join(str(row) for row in base.get("errors") or [])
            )
        report = master.load(output_root / master.REPORT_NAME)
        if report.get("student_package_status") != builder.PASS_STATUS:
            raise ValueError("student_package_status_invalid")
        if report.get("student_package_question_count") != master.EXPECTED_RUNTIME_ITEMS:
            raise ValueError("student_package_question_count_invalid")
        if report.get("student_package_stage_count") != len(builder.STAGE_DEFINITIONS):
            raise ValueError("student_package_stage_count_invalid")
        if report.get("student_package_phrase_before_sentence") is not True:
            raise ValueError("phrase_before_sentence_not_proven")
        if report.get("student_package_images_present") is not False:
            raise ValueError("student_images_present")
        if report.get("teacher_files_unchanged") is not True:
            raise ValueError("teacher_files_changed")
        student = master.load(output_root / "learner" / builder.STUDENT_DATA_NAME)
        core = {key: value for key, value in student.items() if key != "artifact_sha256"}
        if student.get("artifact_sha256") != builder.digest(core):
            raise ValueError("student_artifact_digest_invalid")
        expected = {
            "status": builder.PASS_STATUS,
            "runtime_item_count": 474,
            "stage_count": 7,
            "active_vocabulary_count": 22,
            "active_noun_count": 16,
            "active_adjective_count": 6,
            "instructional_phrase_count": 21,
            "sentence_frame_count": 11,
            "prelearning_approved": True,
            "phrase_before_sentence_order": True,
            "learner_images_present": False,
            "learner_answer_leakage_count": 0,
            "teacher_files_unchanged": True,
            "teacher_edition_private": True,
            "second_question_bank_created": False,
            "formal_production_activation_approved": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        }
        for key, value in expected.items():
            if student.get(key) != value:
                raise ValueError(f"student_{key}_invalid")
        questions = student.get("questions")
        if not isinstance(questions, list) or len(questions) != 474:
            raise ValueError("student_questions_invalid")
        forbidden = _walk_forbidden(questions, master.FORBIDDEN_LEARNER_MARKERS)
        if forbidden:
            raise ValueError(
                "learner_private_marker_exposed:"
                + ",".join(sorted(set(forbidden)))
            )
        ranks = [int(row.get("layout_stage_rank") or 0) for row in questions]
        if ranks != sorted(ranks):
            raise ValueError("question_stage_order_invalid")
        if {
            str(row.get("pattern_family_id") or "") for row in questions
        } != set(builder.EXPECTED_FAMILIES):
            raise ValueError("pattern_family_coverage_invalid")
        if [int(row.get("student_item_no") or 0) for row in questions] != list(
            range(1, 475)
        ):
            raise ValueError("student_question_numbering_invalid")
        speaking = [row for row in questions if row.get("skill") == "SPEAKING"]
        if not speaking or any(
            row.get("practice_only") is not True for row in speaking
        ):
            raise ValueError("speaking_practice_boundary_invalid")
        prelearning = student.get("prelearning") or {}
        if len(prelearning.get("reference_nouns") or []) != 16:
            raise ValueError("prelearning_noun_count_invalid")
        if len(prelearning.get("reference_adjectives") or []) != 6:
            raise ValueError("prelearning_adjective_count_invalid")
        phrases = set(
            str(row) for row in prelearning.get("instructional_phrases") or []
        )
        for phrase in (
            "an apple",
            "a new book",
            "an old book",
            "a small bag",
            "a red book",
            "a blue bag",
        ):
            if phrase not in phrases:
                raise ValueError(f"approved_prelearning_phrase_missing:{phrase}")
        if "a new dog" in phrases or "a small room" in phrases:
            raise ValueError("unapproved_core_phrase_present")
        teacher_identities = report.get("teacher_file_identities") or {}
        for name in (
            "teacher/index.private.html",
            "teacher/unit01_teacher_print_data.private.json",
        ):
            if master.file_identity(output_root / name) != teacher_identities.get(name):
                raise ValueError(f"teacher_file_identity_changed:{name}")
        learner_files = (
            "learner/index.html",
            "learner/prelearning.html",
            "learner/questionbank.html",
            "learner/student.css",
            "learner/student.js",
        )
        texts = {
            name: (output_root / name).read_text(encoding="utf-8")
            for name in learner_files
        }
        combined = "\n".join(texts.values()).casefold()
        for marker in IMAGE_MARKERS:
            if marker.casefold() in combined:
                raise ValueError(f"learner_image_marker_present:{marker}")
        if "teacher/index.private.html" in combined:
            raise ValueError("teacher_private_link_exposed_to_learner")
        if "window.print()" not in texts["learner/index.html"]:
            raise ValueError("learner_launcher_print_missing")
        css_compact = texts["learner/student.css"].replace(" ", "").casefold()
        if "@page{size:a4" not in css_compact:
            raise ValueError("a4_print_css_missing")
        if "break-inside:avoid" not in css_compact:
            raise ValueError("question_page_split_guard_missing")
        for stage_id, _title, _families in builder.STAGE_DEFINITIONS:
            if (
                f'data-stage="{stage_id}"'
                not in texts["learner/questionbank.html"]
            ):
                raise ValueError(f"question_stage_html_missing:{stage_id}")
        for marker in (
            "Part 1",
            "Part 2",
            "Part 3",
            "Part 4",
            "Part 5",
            "Part 6",
            "Vocabulary Reference",
        ):
            if marker not in texts["learner/prelearning.html"]:
                raise ValueError(f"prelearning_section_missing:{marker}")
        counts = {
            "runtime_item_count": len(questions),
            "pattern_family_count": len(builder.EXPECTED_FAMILIES),
            "stage_count": len(builder.STAGE_DEFINITIONS),
            "speaking_practice_item_count": len(speaking),
            "teacher_file_count_preserved": len(teacher_identities),
            "learner_file_count": len(learner_files) + 1,
        }
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        **counts,
        "learner_answer_leakage_count": 0,
        "learner_images_present": False,
        "teacher_files_unchanged": not errors,
        "phrase_before_sentence_order": not errors,
        "second_question_bank_created": False,
        "formal_production_activation_approved": False,
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
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
