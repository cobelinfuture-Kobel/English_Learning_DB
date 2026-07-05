"""Standard-library validator for one ReadingV1 P2 private-practice item."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

SCHEMA_VERSION = "reading_v1_p2_assessment_item.v1"
REPORT_VERSION = "reading_v1_p2_assessment_item_validation_report.v1"

ALLOWED_STAGES = {"RV1-S0", "RV1-S1", "RV1-S2", "RV1-S3"}
QUESTION_TYPES_BY_FAMILY = {
    "literal_comprehension": {
        "literal_who",
        "literal_what",
        "literal_where",
        "literal_when",
        "yes_no_text_check",
        "true_false_text_check",
    },
    "vocabulary_in_context": {"picture_word_match"},
    "sentence_order_and_sequence": {"simple_sequence_order"},
    "reference_and_detail_match": {"single_detail_match"},
}
ALLOWED_QUESTION_TYPES = {
    question_type
    for values in QUESTION_TYPES_BY_FAMILY.values()
    for question_type in values
}
ALLOWED_LABELS = {"correct", "incorrect", "needs_review", "not_answered"}


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _err(errors: List[Dict[str, str]], code: str, path: str, message: str) -> None:
    errors.append({"code": code, "path": path, "message": message})


def validate_item(item: Mapping[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []

    if item.get("schema_version") != SCHEMA_VERSION:
        _err(errors, "RV1_P2_ITEM_ERR_SCHEMA", "schema_version", "schema_version mismatch")
    if not _present(item.get("item_id")):
        _err(errors, "RV1_P2_ITEM_ERR_ID", "item_id", "item_id required")
    if item.get("level_stage") not in ALLOWED_STAGES:
        _err(errors, "RV1_P2_ITEM_ERR_STAGE", "level_stage", "level_stage not allowed")

    family = item.get("pattern_family")
    question_type = item.get("question_type")
    if family not in QUESTION_TYPES_BY_FAMILY:
        _err(errors, "RV1_P2_ITEM_ERR_FAMILY", "pattern_family", "pattern_family not allowed")
    if question_type not in ALLOWED_QUESTION_TYPES:
        _err(errors, "RV1_P2_ITEM_ERR_TYPE", "question_type", "question_type not allowed")
    elif family in QUESTION_TYPES_BY_FAMILY and question_type not in QUESTION_TYPES_BY_FAMILY[family]:
        _err(errors, "RV1_P2_ITEM_ERR_FAMILY_TYPE", "question_type", "question_type mismatches family")

    _validate_payload(item, errors)
    _validate_feedback(item, errors)
    _validate_trace(item, errors)
    _validate_guards(item, errors)

    return {
        "schema_version": REPORT_VERSION,
        "validator_status": "PASS" if not errors else "FAIL",
        "item_id": item.get("item_id"),
        "computed_ready": not errors,
        "errors": errors,
        "warnings": [],
        "summary": {"error_count": len(errors), "warning_count": 0},
    }


def _validate_payload(item: Mapping[str, Any], errors: List[Dict[str, str]]) -> None:
    display = item.get("display_payload")
    if not isinstance(display, Mapping):
        _err(errors, "RV1_P2_ITEM_ERR_DISPLAY", "display_payload", "display payload required")
    elif not _present(display.get("prompt")):
        _err(errors, "RV1_P2_ITEM_ERR_PROMPT", "display_payload.prompt", "prompt required")

    answer = item.get("answer_model")
    if not isinstance(answer, Mapping):
        _err(errors, "RV1_P2_ITEM_ERR_ANSWER", "answer_model", "answer model required")
        return
    if not _present(answer.get("answer_key")):
        _err(errors, "RV1_P2_ITEM_ERR_ANSWER", "answer_model.answer_key", "answer key required")
    if answer.get("answer_visible_to_student") is True:
        _err(errors, "RV1_P2_ITEM_ERR_ANSWER_VISIBLE", "answer_model.answer_visible_to_student", "answer must be hidden")
    if item.get("question_type") == "true_false_text_check" and not isinstance(answer.get("answer_key"), bool):
        _err(errors, "RV1_P2_ITEM_ERR_BOOLEAN", "answer_model.answer_key", "boolean answer required")
    if item.get("question_type") == "simple_sequence_order":
        value = answer.get("answer_key")
        if not isinstance(value, list) or len(value) < 2:
            _err(errors, "RV1_P2_ITEM_ERR_SEQUENCE", "answer_model.answer_key", "sequence answer required")


def _validate_feedback(item: Mapping[str, Any], errors: List[Dict[str, str]]) -> None:
    policy = item.get("feedback_policy")
    if not isinstance(policy, Mapping):
        _err(errors, "RV1_P2_ITEM_ERR_FEEDBACK", "feedback_policy", "feedback policy required")
        return
    if policy.get("feedback_boundary") != "local_private_practice_only":
        _err(errors, "RV1_P2_ITEM_ERR_FEEDBACK", "feedback_policy.feedback_boundary", "feedback boundary mismatch")
    if policy.get("learner_state_write") is not False:
        _err(errors, "RV1_P2_ITEM_ERR_STATE_WRITE", "feedback_policy.learner_state_write", "state write must be false")
    labels = policy.get("allowed_labels", [])
    if labels and not set(labels).issubset(ALLOWED_LABELS):
        _err(errors, "RV1_P2_ITEM_ERR_LABEL", "feedback_policy.allowed_labels", "unsupported feedback label")


def _validate_trace(item: Mapping[str, Any], errors: List[Dict[str, str]]) -> None:
    trace = item.get("source_trace")
    if not isinstance(trace, Mapping):
        _err(errors, "RV1_P2_ITEM_ERR_TRACE", "source_trace", "source trace required")
        return
    if not any(_present(trace.get(key)) for key in ("source_unit_ref", "source_sentence_refs")):
        _err(errors, "RV1_P2_ITEM_ERR_TRACE", "source_trace", "source reference required")
    if trace.get("source_payload_persisted") is not False:
        _err(errors, "RV1_P2_ITEM_ERR_TRACE_POLICY", "source_trace.source_payload_persisted", "source payload persistence blocked")


def _validate_guards(item: Mapping[str, Any], errors: List[Dict[str, str]]) -> None:
    expected = {
        "private_homework_only": True,
        "public_ready": False,
        "not_for_public_export": True,
        "not_for_commercial_distribution": True,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
    }
    for key, value in expected.items():
        if item.get(key) != value:
            _err(errors, "RV1_P2_ITEM_ERR_GUARD", key, f"{key} must be {value!r}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate one ReadingV1 P2 item JSON.")
    parser.add_argument("item_json", type=Path)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)
    report = validate_item(load_json(args.item_json))
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["validator_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
