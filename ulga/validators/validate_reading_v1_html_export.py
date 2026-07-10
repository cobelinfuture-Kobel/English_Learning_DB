"""Validator for in-memory ReadingV1 private-homework HTML export results."""

from __future__ import annotations

from typing import Any, Mapping


TASK_ID = "R7-M104E24B_A1GrammarGateHTMLExportEvidenceIntegration"
EVIDENCE_VERSION = "reading_v1_html_export_gate_evidence.v1"
OUTPUT_GATE_TASK_ID = (
    "R7-M104E24A_A1PracticeBankGrammarGatedHTMLExportIntegration"
)
OUTPUT_GATE_SCHEMA_VERSION = (
    "reading_v1_private_homework_output_gate_validation_report.v1"
)
RENDER_RESULT_SCHEMA_VERSION = "reading_v1_html_export_result.v1"

BLOCKED_MARKERS = [
    "student-answer-key",
    "answer-key-visible",
    "validator-internals",
    "promotion-metadata",
]


def _error(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def validate_html_export_result(result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    status = result.get("render_status")
    html = result.get("html")

    if result.get("schema_version") != RENDER_RESULT_SCHEMA_VERSION:
        errors.append(
            _error(
                "RV1_HTML_ERR_RESULT_SCHEMA_VERSION",
                "schema_version",
                "Render result schema_version is missing or invalid.",
            )
        )

    if status not in {"PASS", "BLOCKED"}:
        errors.append(
            _error(
                "RV1_HTML_ERR_INVALID_STATUS",
                "render_status",
                "render_status must be PASS or BLOCKED.",
            )
        )

    evidence = result.get("gate_evidence")
    if not isinstance(evidence, Mapping):
        errors.append(
            _error(
                "RV1_HTML_ERR_GATE_EVIDENCE_MISSING",
                "gate_evidence",
                "A renderer gate_evidence object is required.",
            )
        )
        evidence = {}
    else:
        _validate_gate_evidence(
            evidence,
            errors,
            require_pass=status == "PASS",
        )

    result_errors = result.get("errors")
    if not isinstance(result_errors, list):
        errors.append(
            _error(
                "RV1_HTML_ERR_RESULT_ERRORS_INVALID",
                "errors",
                "Render result errors must be a list.",
            )
        )
        result_errors = []

    if status == "PASS":
        if result_errors:
            errors.append(
                _error(
                    "RV1_HTML_ERR_PASS_WITH_RENDER_ERRORS",
                    "errors",
                    "PASS render results must not contain renderer errors.",
                )
            )
        if not isinstance(html, str) or not html:
            errors.append(
                _error(
                    "RV1_HTML_ERR_EMPTY_PAGE",
                    "html",
                    "PASS render results must contain HTML.",
                )
            )
        elif any(marker in html for marker in BLOCKED_MARKERS):
            errors.append(
                _error(
                    "RV1_HTML_ERR_STUDENT_VIEW_LEAK",
                    "html",
                    "Student HTML contains a blocked marker.",
                )
            )

        rendered_item_ids = evidence.get("rendered_item_ids")
        source_item_ids = evidence.get("source_item_ids")
        if (
            not isinstance(rendered_item_ids, list)
            or not rendered_item_ids
            or len(rendered_item_ids) != len(set(rendered_item_ids))
        ):
            errors.append(
                _error(
                    "RV1_HTML_ERR_RENDERED_ITEM_EVIDENCE_INVALID",
                    "gate_evidence.rendered_item_ids",
                    "PASS exports require unique rendered item IDs.",
                )
            )
        if (
            not isinstance(source_item_ids, list)
            or set(rendered_item_ids or []) != set(source_item_ids)
        ):
            errors.append(
                _error(
                    "RV1_HTML_ERR_RENDERED_ITEM_EVIDENCE_INVALID",
                    "gate_evidence.source_item_ids",
                    "Rendered item IDs must equal the output-gate item IDs.",
                )
            )
        if evidence.get("rendered_item_count") != len(rendered_item_ids or []):
            errors.append(
                _error(
                    "RV1_HTML_ERR_RENDERED_ITEM_EVIDENCE_INVALID",
                    "gate_evidence.rendered_item_count",
                    "rendered_item_count does not match rendered_item_ids.",
                )
            )

    if status == "BLOCKED" and html:
        errors.append(
            _error(
                "RV1_HTML_ERR_BLOCKED_WITH_PAGE",
                "html",
                "BLOCKED render results must not contain HTML.",
            )
        )

    return {
        "task_id": TASK_ID,
        "schema_version": "reading_v1_html_export_validation_report.v1",
        "validator_status": "PASS" if not errors else "FAIL",
        "render_status": status,
        "gate_evidence_present": bool(evidence),
        "grammar_gate_evidence_pass": _grammar_evidence_pass(evidence),
        "errors": errors,
        "warning_count": 0,
        "error_count": len(errors),
    }


def _validate_gate_evidence(
    evidence: Mapping[str, Any],
    errors: list[dict[str, str]],
    *,
    require_pass: bool,
) -> None:
    expected = {
        "evidence_version": EVIDENCE_VERSION,
        "renderer_task_id": TASK_ID,
        "output_gate_task_id": OUTPUT_GATE_TASK_ID,
        "output_gate_schema_version": OUTPUT_GATE_SCHEMA_VERSION,
        "private_homework_only": True,
        "public_ready": False,
        "render_mode": "local_private_homework_only",
    }
    for key, expected_value in expected.items():
        if evidence.get(key) != expected_value:
            errors.append(
                _error(
                    "RV1_HTML_ERR_GATE_EVIDENCE_INVALID",
                    f"gate_evidence.{key}",
                    f"{key} must equal {expected_value!r}.",
                )
            )

    for key in (
        "practice_bank_grammar_gate_pass_count",
        "practice_bank_grammar_gate_fail_count",
        "practice_bank_item_report_count",
        "output_item_count",
        "allowed_item_count",
        "blocked_item_count",
        "output_gate_error_count",
    ):
        if not isinstance(evidence.get(key), int):
            errors.append(
                _error(
                    "RV1_HTML_ERR_GATE_EVIDENCE_INVALID",
                    f"gate_evidence.{key}",
                    f"{key} must be an integer.",
                )
            )

    source_item_ids = evidence.get("source_item_ids")
    if (
        not isinstance(source_item_ids, list)
        or len(source_item_ids) != len(set(source_item_ids))
    ):
        errors.append(
            _error(
                "RV1_HTML_ERR_GATE_EVIDENCE_INVALID",
                "gate_evidence.source_item_ids",
                "source_item_ids must be a unique list.",
            )
        )

    if require_pass:
        pass_expectations = {
            "output_gate_validator_status": "PASS",
            "output_gate_gate_status": "HTML_ENTRY_ALLOWED",
            "html_entry_allowed": True,
            "output_gate_error_count": 0,
            "practice_bank_validator_status": "PASS",
            "practice_bank_grammar_gate_status": "PASS",
            "practice_bank_grammar_gate_fail_count": 0,
            "all_output_items_allowed": True,
            "blocked_item_count": 0,
        }
        for key, expected_value in pass_expectations.items():
            if evidence.get(key) != expected_value:
                code = (
                    "RV1_HTML_ERR_GRAMMAR_GATE_EVIDENCE_NOT_PASS"
                    if "grammar" in key or key == "practice_bank_validator_status"
                    else "RV1_HTML_ERR_OUTPUT_GATE_EVIDENCE_NOT_PASS"
                )
                errors.append(
                    _error(
                        code,
                        f"gate_evidence.{key}",
                        f"PASS export requires {key}={expected_value!r}.",
                    )
                )

        pass_count = evidence.get("practice_bank_grammar_gate_pass_count")
        item_report_count = evidence.get("practice_bank_item_report_count")
        if (
            not isinstance(pass_count, int)
            or not isinstance(item_report_count, int)
            or item_report_count < 1
            or pass_count != item_report_count
        ):
            errors.append(
                _error(
                    "RV1_HTML_ERR_GRAMMAR_GATE_EVIDENCE_NOT_PASS",
                    "gate_evidence.practice_bank_grammar_gate_pass_count",
                    "Every PracticeBank item report must have a passing grammar gate.",
                )
            )

        output_item_count = evidence.get("output_item_count")
        allowed_item_count = evidence.get("allowed_item_count")
        if (
            not isinstance(output_item_count, int)
            or output_item_count < 1
            or allowed_item_count != output_item_count
        ):
            errors.append(
                _error(
                    "RV1_HTML_ERR_OUTPUT_GATE_ITEM_ACCOUNTING",
                    "gate_evidence.allowed_item_count",
                    "Every output-gate item must be allowed before PASS export.",
                )
            )


def _grammar_evidence_pass(evidence: Mapping[str, Any]) -> bool:
    pass_count = evidence.get("practice_bank_grammar_gate_pass_count")
    item_count = evidence.get("practice_bank_item_report_count")
    return (
        evidence.get("practice_bank_validator_status") == "PASS"
        and evidence.get("practice_bank_grammar_gate_status") == "PASS"
        and evidence.get("practice_bank_grammar_gate_fail_count") == 0
        and isinstance(pass_count, int)
        and isinstance(item_count, int)
        and item_count > 0
        and pass_count == item_count
    )
