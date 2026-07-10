"""Validator for ReadingV1 private-homework overlay candidates.

The overlay is the render-safe bridge between PracticeBank candidate records and
local/private HTML rendering. Validation reports preserve source_item_id so
output gates can join overlay decisions back to canonical PracticeItems without
guessing from display order.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


TASK_ID = "R7-M104E24C_A1GrammarGateOverlayIdentityIntegration"
ALLOWED_STAGES = {"RV1-S0", "RV1-S1", "RV1-S2", "RV1-S3"}
V1_QUESTION_TYPES = {
    "literal_who",
    "literal_what",
    "literal_where",
    "true_false",
    "sentence_ordering",
    "cloze_vocabulary",
}

BLOCKING_ERRORS = {
    "RV1_OVERLAY_ERR_SOURCE_ITEM_ID_MISSING",
    "RV1_OVERLAY_ERR_DUPLICATE_SOURCE_ITEM_ID",
    "RV1_OVERLAY_ERR_DUPLICATE_OVERLAY_ITEM_ID",
    "RV1_OVERLAY_ERR_PRACTICE_BANK_NOT_PASS",
    "RV1_OVERLAY_ERR_HTML_READY_FALSE",
    "RV1_OVERLAY_ERR_PUBLIC_READY_TRUE",
    "RV1_OVERLAY_ERR_PUBLIC_EXPORT_ALLOWED",
    "RV1_OVERLAY_ERR_COMMERCIAL_DISTRIBUTION_ALLOWED",
    "RV1_OVERLAY_ERR_RAW_SOURCE_TEXT_INLINE",
    "RV1_OVERLAY_ERR_FULL_PASSAGE_TEXT_INLINE",
    "RV1_OVERLAY_ERR_SOURCE_PAYLOAD_STORED",
    "RV1_OVERLAY_ERR_ANSWER_KEY_REF_MISSING",
    "RV1_OVERLAY_ERR_ANSWER_EVIDENCE_REF_MISSING",
    "RV1_OVERLAY_ERR_SOURCE_TRACE_REF_MISSING",
    "RV1_OVERLAY_ERR_AUTHORITY_STATUS_NOT_CANDIDATE",
    "RV1_OVERLAY_ERR_PROMOTION_STATUS_NOT_NOT_PROMOTED",
    "RV1_OVERLAY_ERR_INVALID_LEVEL_STAGE",
    "RV1_OVERLAY_ERR_INVALID_QUESTION_TYPE",
    "RV1_OVERLAY_ERR_SCHEMA_VERSION_MISSING",
}

ALLOWED_WARNINGS = {
    "RV1_OVERLAY_WARN_DISPLAY_TEXT_REQUIRES_PRIVATE_RUNTIME",
    "RV1_OVERLAY_WARN_PARENT_VIEW_SOURCE_LOCATOR_ONLY",
    "RV1_OVERLAY_WARN_ITEM_ORDER_NOT_GROUPED_BY_TYPE",
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


def _add_error(
    errors: List[Dict[str, Any]], code: str, message: str, path: str = ""
) -> None:
    errors.append({"code": code, "message": message, "path": path})


def _add_warning(
    warnings: List[Dict[str, Any]], code: str, message: str, path: str = ""
) -> None:
    warnings.append({"code": code, "message": message, "path": path})


def validate_overlay_package(package: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate one overlay package and preserve deterministic item identity."""

    package_errors: List[Dict[str, Any]] = []
    package_warnings: List[Dict[str, Any]] = []

    if package.get("schema_version") != "reading_v1_private_homework_overlay.v1":
        _add_error(
            package_errors,
            "RV1_OVERLAY_ERR_SCHEMA_VERSION_MISSING",
            "Overlay package schema_version must be reading_v1_private_homework_overlay.v1.",
            "schema_version",
        )

    if package.get("authority_status") != "candidate_only":
        _add_error(
            package_errors,
            "RV1_OVERLAY_ERR_AUTHORITY_STATUS_NOT_CANDIDATE",
            "Overlay package must remain candidate_only.",
            "authority_status",
        )

    if package.get("promotion_status") != "not_promoted":
        _add_error(
            package_errors,
            "RV1_OVERLAY_ERR_PROMOTION_STATUS_NOT_NOT_PROMOTED",
            "Overlay package must not be promoted by implication.",
            "promotion_status",
        )

    if package.get("private_homework_only") is not True:
        _add_error(
            package_errors,
            "RV1_OVERLAY_ERR_PUBLIC_EXPORT_ALLOWED",
            "Overlay package must be private_homework_only.",
            "private_homework_only",
        )

    if package.get("public_ready") is not False:
        _add_error(
            package_errors,
            "RV1_OVERLAY_ERR_PUBLIC_READY_TRUE",
            "Overlay package public_ready must remain false in P1.",
            "public_ready",
        )

    _validate_render_policy(package, package_errors)

    items = package.get("items")
    if not isinstance(items, list):
        _add_error(
            package_errors,
            "RV1_OVERLAY_ERR_SCHEMA_VERSION_MISSING",
            "Overlay package must contain an items list.",
            "items",
        )
        items = []

    _validate_unique_item_identity(items, package_errors)
    item_reports = [
        validate_overlay_item(item, index)
        for index, item in enumerate(items)
        if isinstance(item, Mapping)
    ]

    error_count = len(package_errors) + sum(
        len(report["errors"]) for report in item_reports
    )
    warning_count = len(package_warnings) + sum(
        len(report["warnings"]) for report in item_reports
    )
    overlay_ready_count = sum(
        1 for report in item_reports if report["computed_overlay_ready"]
    )
    source_item_ids = [
        report["source_item_id"]
        for report in item_reports
        if isinstance(report.get("source_item_id"), str)
        and report["source_item_id"]
    ]

    return {
        "task_id": TASK_ID,
        "schema_version": "reading_v1_private_homework_overlay_validation_report.v1",
        "validator_status": "PASS" if error_count == 0 else "FAIL",
        "package_errors": package_errors,
        "package_warnings": package_warnings,
        "item_reports": item_reports,
        "identity_summary": {
            "source_item_id_count": len(source_item_ids),
            "unique_source_item_id_count": len(set(source_item_ids)),
            "identity_join_ready": (
                error_count == 0
                and len(source_item_ids) == len(item_reports)
                and len(set(source_item_ids)) == len(item_reports)
            ),
        },
        "summary": {
            "item_count": len(item_reports),
            "overlay_ready_count": overlay_ready_count,
            "blocked_count": sum(
                1 for report in item_reports if report["errors"]
            ),
            "warning_count": warning_count,
            "error_count": error_count,
        },
    }


def validate_overlay_item(
    item: Mapping[str, Any], index: Optional[int] = None
) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    overlay_item_id = item.get("overlay_item_id") or (
        f"index:{index}" if index is not None else None
    )
    source_item_id = item.get("source_item_id")

    if not _is_non_empty(source_item_id):
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_SOURCE_ITEM_ID_MISSING",
            "Overlay item must include source_item_id.",
            "source_item_id",
        )
        source_item_id = None

    stage = item.get("level_stage")
    if stage not in ALLOWED_STAGES:
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_INVALID_LEVEL_STAGE",
            f"Invalid level_stage: {stage!r}.",
            "level_stage",
        )

    question_type = item.get("question_type")
    if question_type not in V1_QUESTION_TYPES:
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_INVALID_QUESTION_TYPE",
            f"Invalid ReadingV1 question type: {question_type!r}.",
            "question_type",
        )

    if not _is_non_empty(_get(item, "student_view.prompt")):
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_SCHEMA_VERSION_MISSING",
            "student_view.prompt is required.",
            "student_view.prompt",
        )

    display_text_ref = _get(item, "student_view.display_text_ref")
    display_text_inline = _get(item, "student_view.display_text_inline")
    if not _is_non_empty(display_text_ref):
        _add_warning(
            warnings,
            "RV1_OVERLAY_WARN_DISPLAY_TEXT_REQUIRES_PRIVATE_RUNTIME",
            "Overlay item lacks display_text_ref and will require a private runtime resolver.",
            "student_view.display_text_ref",
        )
    if _is_non_empty(display_text_inline):
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_RAW_SOURCE_TEXT_INLINE",
            "student_view.display_text_inline must remain null in P1 overlay artifacts.",
            "student_view.display_text_inline",
        )

    if not _is_non_empty(_get(item, "parent_or_teacher_view.answer_key_ref")):
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_ANSWER_KEY_REF_MISSING",
            "parent_or_teacher_view.answer_key_ref is required.",
            "parent_or_teacher_view.answer_key_ref",
        )

    if not _is_non_empty(
        _get(item, "parent_or_teacher_view.answer_evidence_ref")
    ):
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_ANSWER_EVIDENCE_REF_MISSING",
            "parent_or_teacher_view.answer_evidence_ref is required.",
            "parent_or_teacher_view.answer_evidence_ref",
        )

    _validate_source_trace_view(item, errors)
    _validate_item_policy_flags(item, errors)
    _validate_item_gates(item, errors)

    computed_overlay_ready = len(errors) == 0
    return {
        "overlay_item_id": overlay_item_id,
        "source_item_id": source_item_id,
        "validator_status": "PASS" if not errors else "FAIL",
        "computed_overlay_ready": computed_overlay_ready,
        "errors": errors,
        "warnings": warnings,
    }


def _validate_unique_item_identity(
    items: list[Any], errors: List[Dict[str, Any]]
) -> None:
    source_ids: list[str] = []
    overlay_ids: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            _add_error(
                errors,
                "RV1_OVERLAY_ERR_SCHEMA_VERSION_MISSING",
                "Each overlay item must be an object.",
                "items",
            )
            continue
        source_id = item.get("source_item_id")
        overlay_id = item.get("overlay_item_id")
        if isinstance(source_id, str) and source_id:
            source_ids.append(source_id)
        if isinstance(overlay_id, str) and overlay_id:
            overlay_ids.append(overlay_id)

    duplicate_source_ids = sorted(
        {item_id for item_id in source_ids if source_ids.count(item_id) > 1}
    )
    if duplicate_source_ids:
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_DUPLICATE_SOURCE_ITEM_ID",
            f"Duplicate source_item_id values: {duplicate_source_ids}.",
            "items.source_item_id",
        )

    duplicate_overlay_ids = sorted(
        {item_id for item_id in overlay_ids if overlay_ids.count(item_id) > 1}
    )
    if duplicate_overlay_ids:
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_DUPLICATE_OVERLAY_ITEM_ID",
            f"Duplicate overlay_item_id values: {duplicate_overlay_ids}.",
            "items.overlay_item_id",
        )


def _validate_render_policy(
    package: Mapping[str, Any], errors: List[Dict[str, Any]]
) -> None:
    policy = package.get("render_policy")
    if not isinstance(policy, Mapping):
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_SCHEMA_VERSION_MISSING",
            "render_policy object is required.",
            "render_policy",
        )
        return

    false_flags = {
        "allow_public_export": "RV1_OVERLAY_ERR_PUBLIC_EXPORT_ALLOWED",
        "allow_commercial_distribution": "RV1_OVERLAY_ERR_COMMERCIAL_DISTRIBUTION_ALLOWED",
        "allow_raw_source_text": "RV1_OVERLAY_ERR_RAW_SOURCE_TEXT_INLINE",
        "allow_full_passage_text": "RV1_OVERLAY_ERR_FULL_PASSAGE_TEXT_INLINE",
        "allow_source_payload_copy": "RV1_OVERLAY_ERR_SOURCE_PAYLOAD_STORED",
    }
    for flag, code in false_flags.items():
        if policy.get(flag) is not False:
            _add_error(
                errors,
                code,
                f"render_policy.{flag} must be false.",
                f"render_policy.{flag}",
            )

    if policy.get("render_mode") != "local_private_homework_only":
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_PUBLIC_EXPORT_ALLOWED",
            "render_policy.render_mode must be local_private_homework_only.",
            "render_policy.render_mode",
        )


def _validate_source_trace_view(
    item: Mapping[str, Any], errors: List[Dict[str, Any]]
) -> None:
    trace = item.get("source_trace_view")
    if not isinstance(trace, Mapping):
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_SOURCE_TRACE_REF_MISSING",
            "source_trace_view object is required.",
            "source_trace_view",
        )
        return

    if not any(
        _is_non_empty(trace.get(key))
        for key in ("source_locator", "source_unit_ref")
    ):
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_SOURCE_TRACE_REF_MISSING",
            "source_trace_view must include source_locator or source_unit_ref.",
            "source_trace_view",
        )

    if trace.get("source_payload_stored") is not False:
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_SOURCE_PAYLOAD_STORED",
            "source_trace_view.source_payload_stored must be false.",
            "source_trace_view.source_payload_stored",
        )

    if trace.get("raw_source_text_visible") is not False:
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_RAW_SOURCE_TEXT_INLINE",
            "source_trace_view.raw_source_text_visible must be false.",
            "source_trace_view.raw_source_text_visible",
        )

    if trace.get("full_passage_text_visible") is not False:
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_FULL_PASSAGE_TEXT_INLINE",
            "source_trace_view.full_passage_text_visible must be false.",
            "source_trace_view.full_passage_text_visible",
        )


def _validate_item_policy_flags(
    item: Mapping[str, Any], errors: List[Dict[str, Any]]
) -> None:
    flags = item.get("policy_flags")
    if not isinstance(flags, Mapping):
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_SCHEMA_VERSION_MISSING",
            "policy_flags object is required.",
            "policy_flags",
        )
        return

    expected = {
        "private_homework_only": True,
        "public_ready": False,
        "not_for_public_export": True,
        "not_for_commercial_distribution": True,
        "raw_raz_text_persisted": False,
        "full_passage_text_persisted": False,
        "source_payload_copied_to_repo": False,
    }
    codes = {
        "public_ready": "RV1_OVERLAY_ERR_PUBLIC_READY_TRUE",
        "not_for_public_export": "RV1_OVERLAY_ERR_PUBLIC_EXPORT_ALLOWED",
        "not_for_commercial_distribution": "RV1_OVERLAY_ERR_COMMERCIAL_DISTRIBUTION_ALLOWED",
        "raw_raz_text_persisted": "RV1_OVERLAY_ERR_RAW_SOURCE_TEXT_INLINE",
        "full_passage_text_persisted": "RV1_OVERLAY_ERR_FULL_PASSAGE_TEXT_INLINE",
        "source_payload_copied_to_repo": "RV1_OVERLAY_ERR_SOURCE_PAYLOAD_STORED",
        "private_homework_only": "RV1_OVERLAY_ERR_PUBLIC_EXPORT_ALLOWED",
    }
    for flag, expected_value in expected.items():
        if flags.get(flag) is not expected_value:
            _add_error(
                errors,
                codes[flag],
                f"policy_flags.{flag} must be {expected_value!r}.",
                f"policy_flags.{flag}",
            )


def _validate_item_gates(
    item: Mapping[str, Any], errors: List[Dict[str, Any]]
) -> None:
    gates = item.get("gates")
    if not isinstance(gates, Mapping):
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_SCHEMA_VERSION_MISSING",
            "gates object is required.",
            "gates",
        )
        return

    if gates.get("practice_bank_validator_status") != "PASS":
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_PRACTICE_BANK_NOT_PASS",
            "PracticeBank validator status must be PASS before overlay.",
            "gates.practice_bank_validator_status",
        )

    if gates.get("html_ready") is not True:
        _add_error(
            errors,
            "RV1_OVERLAY_ERR_HTML_READY_FALSE",
            "html_ready must be true before overlay.",
            "gates.html_ready",
        )


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate ReadingV1 private-homework overlay candidate JSON."
    )
    parser.add_argument("overlay_json", type=Path)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    package = load_json(args.overlay_json)
    report = validate_overlay_package(package)
    report_text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report_text + "\n", encoding="utf-8")
    else:
        print(report_text)

    return 0 if report["validator_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
