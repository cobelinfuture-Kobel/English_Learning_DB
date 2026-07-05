"""Checker for ReadingV1 P3 local records."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

SCHEMA_VERSION = "reading_v1_p3_unit.v1"
REPORT_VERSION = "reading_v1_p3_unit_validation_report.v1"

GROUPS = {
    "review_literal_detail",
    "review_wh_question_family",
    "review_vocabulary_context",
    "review_sequence_order",
    "review_yes_no_evidence",
    "review_true_false_evidence",
    "review_unanswered",
    "review_operator_needed",
}


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _add(errors: List[Dict[str, str]], code: str, path: str, message: str) -> None:
    errors.append({"code": code, "path": path, "message": message})


def check_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        _add(errors, "RV1_P3_REC_ERR_SCHEMA", "schema_version", "schema_version mismatch")
    if not _present(record.get("item_id")):
        _add(errors, "RV1_P3_REC_ERR_ITEM", "item_id", "item_id required")
    if not _present(record.get("package_id")):
        _add(errors, "RV1_P3_REC_ERR_PACKAGE", "package_id", "package_id required")
    if record.get("group_key") not in GROUPS:
        _add(errors, "RV1_P3_REC_ERR_GROUP", "group_key", "group_key not allowed")
    if record.get("private_homework_only") is not True:
        _add(errors, "RV1_P3_REC_ERR_GUARD", "private_homework_only", "private_homework_only must be true")
    if record.get("public_ready") is not False:
        _add(errors, "RV1_P3_REC_ERR_GUARD", "public_ready", "public_ready must be false")

    return {
        "schema_version": REPORT_VERSION,
        "validator_status": "PASS" if not errors else "FAIL",
        "item_id": record.get("item_id"),
        "package_id": record.get("package_id"),
        "computed_ready": not errors,
        "errors": errors,
        "warnings": [],
        "summary": {"error_count": len(errors), "warning_count": 0},
    }
