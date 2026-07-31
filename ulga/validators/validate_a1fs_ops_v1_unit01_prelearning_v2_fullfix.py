#!/usr/bin/env python3
"""Validate the learner-facing Unit01 Pre-Learning V2 package projection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_prelearning_v2_fullfix as builder,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_questionbank_student_package_phrase_to_sentence
    as student_builder,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reads and validates only the learner-facing Unit01 Pre-Learning V2 payload "
    "and HTML. It produces no learner content, question, answer, QuestionBank, "
    "teacher output, score, learner state, image asset, audio, Unit02-24 artifact, "
    "production activation, or A2 content."
)
PROGRAM_ID = builder.PROGRAM_ID
TASK_ID = "A1FS-OPS-V1_ValidateUnit01PreLearningV2FullFix"
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_PRELEARNING_V2_VALIDATION"
FAIL_STATUS = "FAIL_A1FS_OPS_V1_UNIT01_PRELEARNING_V2_VALIDATION"


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"_load_error": str(exc)}
    if not isinstance(value, dict):
        return {"_load_error": "json_object_required"}
    return value


def validate_payload(
    payload: Mapping[str, Any],
    rendered_html: str,
) -> dict[str, Any]:
    errors = builder.validate_contract(payload, rendered_html)
    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "error_count": len(errors),
        "errors": errors,
        "prelearning_schema_version": payload.get("prelearning_schema_version"),
        "print_page_count": str(rendered_html or "").count('class="print-page"'),
        "child_frame_count": len(payload.get("learner_frames") or []),
        "mention_context_count": len(payload.get("mention_contexts") or []),
        "guided_check_count": len(payload.get("guided_checks") or []),
        "ready_check_count": len(payload.get("ready_check") or []),
        "authority_sentence_frame_count": len(payload.get("sentence_frames") or []),
        "questionbank_modified": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }


def validate_package(output_root: Path) -> dict[str, Any]:
    root = Path(output_root)
    student_path = root / "learner" / student_builder.STUDENT_DATA_NAME
    html_path = root / "learner" / "prelearning.html"
    student = load(student_path)
    if student.get("_load_error"):
        return {
            "validation_status": FAIL_STATUS,
            "program_id": PROGRAM_ID,
            "task_id": TASK_ID,
            "error_count": 1,
            "errors": ["student_package_unreadable:" + str(student["_load_error"])],
        }
    try:
        rendered_html = html_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "validation_status": FAIL_STATUS,
            "program_id": PROGRAM_ID,
            "task_id": TASK_ID,
            "error_count": 1,
            "errors": ["prelearning_html_unreadable:" + str(exc)],
        }
    payload = student.get("prelearning")
    if not isinstance(payload, dict):
        return {
            "validation_status": FAIL_STATUS,
            "program_id": PROGRAM_ID,
            "task_id": TASK_ID,
            "error_count": 1,
            "errors": ["prelearning_payload_missing"],
        }
    result = validate_payload(payload, rendered_html)
    questions = student.get("questions")
    if not isinstance(questions, list) or len(questions) != student_builder.master.EXPECTED_RUNTIME_ITEMS:
        result["errors"].append("questionbank_runtime_denominator_changed")
        result["error_count"] = len(result["errors"])
        result["validation_status"] = FAIL_STATUS
    else:
        result["runtime_item_count"] = len(questions)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = validate_package(args.output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
