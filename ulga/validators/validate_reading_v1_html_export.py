"""Validator for in-memory ReadingV1 private homework page export results."""

from __future__ import annotations

from typing import Any, Mapping

BLOCKED_MARKERS = [
    "student-answer-key",
    "answer-key-visible",
    "validator-internals",
    "promotion-metadata",
]


def validate_html_export_result(result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    status = result.get("render_status")
    html = result.get("html")

    if status not in {"PASS", "BLOCKED"}:
        errors.append({"code": "RV1_HTML_ERR_INVALID_STATUS", "path": "render_status"})

    if status == "PASS":
        if not isinstance(html, str) or not html:
            errors.append({"code": "RV1_HTML_ERR_EMPTY_PAGE", "path": "html"})
        elif any(marker in html for marker in BLOCKED_MARKERS):
            errors.append({"code": "RV1_HTML_ERR_STUDENT_VIEW_LEAK", "path": "html"})

    if status == "BLOCKED" and html:
        errors.append({"code": "RV1_HTML_ERR_BLOCKED_WITH_PAGE", "path": "html"})

    return {
        "schema_version": "reading_v1_html_export_validation_report.v1",
        "validator_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warning_count": 0,
        "error_count": len(errors),
    }
