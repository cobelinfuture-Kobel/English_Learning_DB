"""Checker for ReadingV1 P7 local question items."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

SCHEMA_VERSION = "reading_v1_p7_question_item.v1"
REPORT_VERSION = "reading_v1_p7_question_item_check_report.v1"
QUESTION_TYPES = {"literal_detail", "wh_question", "sequence", "true_false", "yes_no"}


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _add(errors: List[Dict[str, str]], code: str, path: str, message: str) -> None:
    errors.append({"code": code, "path": path, "message": message})


def check_question_item(item: Mapping[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []
    if item.get("schema_version") != SCHEMA_VERSION:
        _add(errors, "RV1_P7_Q_ERR_SCHEMA", "schema_version", "schema_version mismatch")
    if not _present(item.get("question_id")):
        _add(errors, "RV1_P7_Q_ERR_ID", "question_id", "question_id required")
    if not _present(item.get("source_unit_ref")):
        _add(errors, "RV1_P7_Q_ERR_SOURCE", "source_unit_ref", "source_unit_ref required")
    if item.get("question_type") not in QUESTION_TYPES:
        _add(errors, "RV1_P7_Q_ERR_TYPE", "question_type", "question_type not allowed")
    if not _present(item.get("question_text")):
        _add(errors, "RV1_P7_Q_ERR_TEXT", "question_text", "question_text required")
    if not _present(item.get("answer")):
        _add(errors, "RV1_P7_Q_ERR_ANSWER", "answer", "answer required")
    if item.get("local_only") is not True:
        _add(errors, "RV1_P7_Q_ERR_LOCAL", "local_only", "local_only must be true")
    if item.get("public_ready") is not False:
        _add(errors, "RV1_P7_Q_ERR_PUBLIC", "public_ready", "public_ready must be false")

    return {
        "schema_version": REPORT_VERSION,
        "validator_status": "PASS" if not errors else "FAIL",
        "question_id": item.get("question_id"),
        "computed_ready": not errors,
        "errors": errors,
        "warnings": [],
        "summary": {"error_count": len(errors), "warning_count": 0},
    }
