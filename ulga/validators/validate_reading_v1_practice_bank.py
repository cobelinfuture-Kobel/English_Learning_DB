"""Validator for ReadingV1 private-homework PracticeBank candidates.

The validator is intentionally policy-first:
- candidate-only artifacts only
- private homework only
- no raw RAZ/full passage payload persisted
- V1 question types only
- direct source/evidence trace required

It uses only the Python standard library so it can run in local Codex,
GitHub Actions, or a plain Python environment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional


ALLOWED_STAGES = {"RV1-S0", "RV1-S1", "RV1-S2", "RV1-S3"}

ALLOWED_QUESTION_TYPES_BY_STAGE = {
    "RV1-S0": {"literal_what", "literal_where", "true_false"},
    "RV1-S1": {"literal_who", "literal_what", "literal_where", "true_false"},
    "RV1-S2": {"literal_who", "literal_what", "literal_where", "true_false", "cloze_vocabulary"},
    "RV1-S3": {
        "literal_who",
        "literal_what",
        "literal_where",
        "true_false",
        "sentence_ordering",
        "cloze_vocabulary",
    },
}

V1_QUESTION_TYPES = {
    question_type
    for question_types in ALLOWED_QUESTION_TYPES_BY_STAGE.values()
    for question_type in question_types
}

FORMAL_ASSESSMENT_TYPES = {
    "matching",
    "multiple_choice_with_distractors",
    "gap_fill_formal",
    "short_answer_formal",
    "picture_text_matching",
    "reading_comprehension_set",
    "cambridge_mock_exam_pattern",
    "ket_style_reading_item_set",
}

BLOCKING_ERRORS = {
    "RV1_PB_ERR_SCHEMA_VERSION_MISSING",
    "RV1_PB_ERR_INVALID_LEVEL_STAGE",
    "RV1_PB_ERR_QUESTION_TYPE_NOT_ALLOWED_FOR_STAGE",
    "RV1_PB_ERR_SOURCE_TRACE_MISSING",
    "RV1_PB_ERR_SOURCE_PAYLOAD_STORED",
    "RV1_PB_ERR_RAW_RAZ_TEXT_PERSISTED",
    "RV1_PB_ERR_FULL_PASSAGE_TEXT_PERSISTED",
    "RV1_PB_ERR_PUBLIC_EXPORT_ALLOWED",
    "RV1_PB_ERR_COMMERCIAL_DISTRIBUTION_ALLOWED",
    "RV1_PB_ERR_ANSWER_KEY_MISSING",
    "RV1_PB_ERR_ANSWER_EVIDENCE_MISSING",
    "RV1_PB_ERR_EVIDENCE_NOT_DIRECT",
    "RV1_PB_ERR_CLOZE_NOT_UNIQUE",
    "RV1_PB_ERR_SEQUENCE_EVIDENCE_MISSING",
    "RV1_PB_ERR_FORMAL_ASSESSMENT_PATTERN_LEAKAGE",
    "RV1_PB_ERR_AUTHORITY_STATUS_NOT_CANDIDATE",
    "RV1_PB_ERR_PROMOTION_STATUS_NOT_NOT_PROMOTED",
}

ALLOWED_WARNINGS = {
    "RV1_PB_WARN_PREVIEW_VOCABULARY",
    "RV1_PB_WARN_LOW_PRIORITY_CHUNK_REVIEW_REQUIRED",
    "RV1_PB_WARN_STAGE_TRANSITION_REINFORCEMENT_WEAK",
    "RV1_PB_WARN_DISPLAY_TEXT_REQUIRES_PRIVATE_RUNTIME",
}


def _get(mapping: Mapping[str, Any], path: str, default: Any = None) -> Any:
    value: Any = mapping
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return default
        value = value[part]
    return value


def _is_non_empty(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _add_error(errors: List[Dict[str, Any]], code: str, message: str, path: str = "") -> None:
    errors.append({"code": code, "message": message, "path": path})


def _add_warning(warnings: List[Dict[str, Any]], code: str, message: str, path: str = "") -> None:
    warnings.append({"code": code, "message": message, "path": path})


def validate_package(package: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate a PracticeBank package and all child items.

    Returns a deterministic report. The function does not mutate the input.
    """
    package_errors: List[Dict[str, Any]] = []
    package_warnings: List[Dict[str, Any]] = []

    if not _get(package, "schema_version"):
        _add_error(
            package_errors,
            "RV1_PB_ERR_SCHEMA_VERSION_MISSING",
            "PracticeBank package schema_version is required.",
            "schema_version",
        )

    if package.get("authority_status") != "candidate_only":
        _add_error(
            package_errors,
            "RV1_PB_ERR_AUTHORITY_STATUS_NOT_CANDIDATE",
            "PracticeBank package must remain candidate_only.",
            "authority_status",
        )

    if package.get("promotion_status") != "not_promoted":
        _add_error(
            package_errors,
            "RV1_PB_ERR_PROMOTION_STATUS_NOT_NOT_PROMOTED",
            "PracticeBank package must not be promoted by implication.",
            "promotion_status",
        )

    _validate_policy_flags(package, package_errors, prefix="", package_level=True)

    items = package.get("items")
    if not isinstance(items, list):
        _add_error(
            package_errors,
            "RV1_PB_ERR_SCHEMA_VERSION_MISSING",
            "PracticeBank package must contain an items list.",
            "items",
        )
        items = []

    item_reports = [validate_item(item, index) for index, item in enumerate(items)]

    error_count = len(package_errors) + sum(len(report["errors"]) for report in item_reports)
    warning_count = len(package_warnings) + sum(len(report["warnings"]) for report in item_reports)
    html_ready_count = sum(1 for report in item_reports if report["computed_html_ready"])

    return {
        "schema_version": "reading_v1_practice_bank_validation_report.v1",
        "validator_status": "PASS" if error_count == 0 else "FAIL",
        "package_errors": package_errors,
        "package_warnings": package_warnings,
        "item_reports": item_reports,
        "summary": {
            "item_count": len(item_reports),
            "html_ready_count": html_ready_count,
            "blocked_count": sum(1 for report in item_reports if report["errors"]),
            "warning_count": warning_count,
            "error_count": error_count,
        },
    }


def validate_item(item: Mapping[str, Any], index: Optional[int] = None) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    item_id = item.get("item_id") if item.get("item_id") else (f"index:{index}" if index is not None else None)

    if not _get(item, "schema_version"):
        _add_error(
            errors,
            "RV1_PB_ERR_SCHEMA_VERSION_MISSING",
            "Practice item schema_version is required.",
            "schema_version",
        )

    if item.get("authority_status") != "candidate_only":
        _add_error(
            errors,
            "RV1_PB_ERR_AUTHORITY_STATUS_NOT_CANDIDATE",
            "Practice item must remain candidate_only.",
            "authority_status",
        )

    if item.get("promotion_status") != "not_promoted":
        _add_error(
            errors,
            "RV1_PB_ERR_PROMOTION_STATUS_NOT_NOT_PROMOTED",
            "Practice item must not be promoted by implication.",
            "promotion_status",
        )

    stage = item.get("level_stage")
    question_type = item.get("question_type")

    if stage not in ALLOWED_STAGES:
        _add_error(
            errors,
            "RV1_PB_ERR_INVALID_LEVEL_STAGE",
            f"Invalid or missing level_stage: {stage!r}.",
            "level_stage",
        )

    if question_type in FORMAL_ASSESSMENT_TYPES:
        _add_error(
            errors,
            "RV1_PB_ERR_FORMAL_ASSESSMENT_PATTERN_LEAKAGE",
            f"Formal assessment question type is not allowed in ReadingV1: {question_type!r}.",
            "question_type",
        )
    elif stage in ALLOWED_STAGES and question_type not in ALLOWED_QUESTION_TYPES_BY_STAGE[stage]:
        _add_error(
            errors,
            "RV1_PB_ERR_QUESTION_TYPE_NOT_ALLOWED_FOR_STAGE",
            f"Question type {question_type!r} is not allowed for stage {stage!r}.",
            "question_type",
        )

    _validate_required_bindings(item, errors)
    _validate_source_trace(item, errors)
    _validate_policy_flags(item, errors, prefix="policy_flags.", package_level=False)
    _validate_answer_model(item, errors)
    _validate_question_type_specifics(item, errors, warnings)

    computed_html_ready = _compute_html_ready(item, errors)

    return {
        "item_id": item_id,
        "validator_status": "PASS" if not errors else "FAIL",
        "computed_html_ready": computed_html_ready,
        "errors": errors,
        "warnings": warnings,
    }


def _validate_required_bindings(item: Mapping[str, Any], errors: List[Dict[str, Any]]) -> None:
    required_paths = [
        "theme",
        "content_binding.grammar_focus",
        "content_binding.vocabulary_refs",
        "source_trace",
        "question.prompt",
        "answer_evidence",
    ]
    for path in required_paths:
        if not _is_non_empty(_get(item, path)):
            code = "RV1_PB_ERR_ANSWER_EVIDENCE_MISSING" if path == "answer_evidence" else "RV1_PB_ERR_SCHEMA_VERSION_MISSING"
            _add_error(errors, code, f"Required field is missing or empty: {path}.", path)

    if _get(item, "content_binding.patterns", None) is None:
        _add_error(
            errors,
            "RV1_PB_ERR_SCHEMA_VERSION_MISSING",
            "content_binding.patterns must exist. Use an empty list only for a pure vocabulary item.",
            "content_binding.patterns",
        )

    if _get(item, "content_binding.chunk_refs", None) is None:
        _add_error(
            errors,
            "RV1_PB_ERR_SCHEMA_VERSION_MISSING",
            "content_binding.chunk_refs must exist. Use an empty list if no chunks are used.",
            "content_binding.chunk_refs",
        )


def _validate_source_trace(item: Mapping[str, Any], errors: List[Dict[str, Any]]) -> None:
    source_trace = item.get("source_trace")
    if not isinstance(source_trace, Mapping):
        _add_error(errors, "RV1_PB_ERR_SOURCE_TRACE_MISSING", "source_trace object is required.", "source_trace")
        return

    if not any(
        _is_non_empty(source_trace.get(key))
        for key in ("source_unit_ref", "source_sentence_refs", "source_page_ref", "source_locator")
    ):
        _add_error(
            errors,
            "RV1_PB_ERR_SOURCE_TRACE_MISSING",
            "source_trace must include source_unit_ref, source_sentence_refs, source_page_ref, or source_locator.",
            "source_trace",
        )

    if source_trace.get("source_payload_stored") is True:
        _add_error(
            errors,
            "RV1_PB_ERR_SOURCE_PAYLOAD_STORED",
            "source_trace.source_payload_stored must be false.",
            "source_trace.source_payload_stored",
        )


def _validate_policy_flags(
    obj: Mapping[str, Any],
    errors: List[Dict[str, Any]],
    prefix: str,
    package_level: bool,
) -> None:
    def flag(path: str, default: Any = None) -> Any:
        return _get(obj, f"{prefix}{path}" if prefix else path, default)

    required_true = {
        "private_homework_only": "PracticeBank must be private homework only.",
        "not_for_public_export": "PracticeBank must not allow public export.",
        "not_for_commercial_distribution": "PracticeBank must not allow commercial distribution.",
    }
    required_false = {
        "raw_raz_text_persisted": "PracticeBank must not persist raw RAZ text.",
        "full_passage_text_persisted": "PracticeBank must not persist full passage text.",
        "source_payload_copied_to_repo": "PracticeBank must not copy source payload to repo.",
    }

    if package_level:
        required_false = {
            "source_payload_policy.raw_source_text_persisted": required_false["raw_raz_text_persisted"],
            "source_payload_policy.full_passage_text_persisted": required_false["full_passage_text_persisted"],
            "source_payload_policy.source_payload_copied_to_repo": required_false["source_payload_copied_to_repo"],
        }

    for path, message in required_true.items():
        if flag(path) is not True:
            code = (
                "RV1_PB_ERR_PUBLIC_EXPORT_ALLOWED"
                if path == "not_for_public_export"
                else "RV1_PB_ERR_COMMERCIAL_DISTRIBUTION_ALLOWED"
                if path == "not_for_commercial_distribution"
                else "RV1_PB_ERR_SCHEMA_VERSION_MISSING"
            )
            _add_error(errors, code, message, f"{prefix}{path}" if prefix else path)

    for path, message in required_false.items():
        if flag(path) is not False:
            if "raw" in path:
                code = "RV1_PB_ERR_RAW_RAZ_TEXT_PERSISTED"
            elif "full" in path:
                code = "RV1_PB_ERR_FULL_PASSAGE_TEXT_PERSISTED"
            else:
                code = "RV1_PB_ERR_SOURCE_PAYLOAD_STORED"
            _add_error(errors, code, message, f"{prefix}{path}" if prefix else path)

    public_preview_path = f"{prefix}public_preview_allowed" if prefix else "public_preview_allowed"
    if _get(obj, public_preview_path, False) is True:
        _add_error(
            errors,
            "RV1_PB_ERR_PUBLIC_EXPORT_ALLOWED",
            "public_preview_allowed must be false for P1 ReadingV1.",
            public_preview_path,
        )


def _validate_answer_model(item: Mapping[str, Any], errors: List[Dict[str, Any]]) -> None:
    answer_model = item.get("answer_model")
    if not isinstance(answer_model, Mapping):
        _add_error(errors, "RV1_PB_ERR_ANSWER_KEY_MISSING", "answer_model object is required.", "answer_model")
        return

    if not _is_non_empty(answer_model.get("answer_key")):
        _add_error(errors, "RV1_PB_ERR_ANSWER_KEY_MISSING", "answer_model.answer_key is required.", "answer_model.answer_key")

    evidence = item.get("answer_evidence")
    if not isinstance(evidence, Mapping):
        _add_error(errors, "RV1_PB_ERR_ANSWER_EVIDENCE_MISSING", "answer_evidence object is required.", "answer_evidence")
        return

    if evidence.get("directness") not in {"direct", "direct_literal"}:
        _add_error(
            errors,
            "RV1_PB_ERR_EVIDENCE_NOT_DIRECT",
            "answer_evidence.directness must be direct.",
            "answer_evidence.directness",
        )

    if not any(
        _is_non_empty(evidence.get(key))
        for key in ("evidence_refs", "source_sentence_ref", "source_locator")
    ):
        _add_error(
            errors,
            "RV1_PB_ERR_ANSWER_EVIDENCE_MISSING",
            "answer_evidence must include evidence_refs, source_sentence_ref, or source_locator.",
            "answer_evidence",
        )


def _validate_question_type_specifics(
    item: Mapping[str, Any],
    errors: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
) -> None:
    question_type = item.get("question_type")
    answer_model = item.get("answer_model") if isinstance(item.get("answer_model"), Mapping) else {}
    evidence = item.get("answer_evidence") if isinstance(item.get("answer_evidence"), Mapping) else {}

    if question_type == "true_false" and not isinstance(answer_model.get("answer_key"), bool):
        _add_error(errors, "RV1_PB_ERR_ANSWER_KEY_MISSING", "true_false answer_key must be boolean.", "answer_model.answer_key")

    if question_type == "sentence_ordering":
        answer_key = answer_model.get("answer_key")
        if not isinstance(answer_key, list) or len(answer_key) < 2:
            _add_error(
                errors,
                "RV1_PB_ERR_SEQUENCE_EVIDENCE_MISSING",
                "sentence_ordering answer_key must be an ordered list of at least two sentence IDs.",
                "answer_model.answer_key",
            )
        if not _is_non_empty(evidence.get("evidence_refs")) and not _is_non_empty(evidence.get("source_sentence_ref")):
            _add_error(
                errors,
                "RV1_PB_ERR_SEQUENCE_EVIDENCE_MISSING",
                "sentence_ordering requires explicit sequence evidence.",
                "answer_evidence",
            )

    if question_type == "cloze_vocabulary":
        accepted_answers = answer_model.get("accepted_answers", [])
        answer_key = answer_model.get("answer_key")
        all_answers = [answer_key] + list(accepted_answers if isinstance(accepted_answers, list) else [])
        normalized = [str(answer).strip().lower() for answer in all_answers if _is_non_empty(answer)]
        if len(normalized) != len(set(normalized)):
            _add_error(
                errors,
                "RV1_PB_ERR_CLOZE_NOT_UNIQUE",
                "cloze_vocabulary accepted answers must be unique after normalization.",
                "answer_model.accepted_answers",
            )
        if len(set(normalized)) > 3:
            _add_warning(
                warnings,
                "RV1_PB_WARN_PREVIEW_VOCABULARY",
                "cloze_vocabulary has many accepted answers; review uniqueness before html_ready.",
                "answer_model.accepted_answers",
            )


def _compute_html_ready(item: Mapping[str, Any], errors: Iterable[Mapping[str, Any]]) -> bool:
    if list(errors):
        return False
    required_paths = [
        "level_stage",
        "question_type",
        "theme",
        "content_binding.grammar_focus",
        "content_binding.patterns",
        "content_binding.vocabulary_refs",
        "source_trace",
        "question.prompt",
        "answer_model.answer_key",
        "answer_evidence",
    ]
    return all(_is_non_empty(_get(item, path)) for path in required_paths)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate ReadingV1 PracticeBank candidate JSON.")
    parser.add_argument("practice_bank_json", type=Path)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    package = load_json(args.practice_bank_json)
    report = validate_package(package)
    report_text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report_text + "\n", encoding="utf-8")
    else:
        print(report_text)

    return 0 if report["validator_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
