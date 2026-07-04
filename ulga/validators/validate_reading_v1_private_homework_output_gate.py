"""Validator for ReadingV1 private homework output gate candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

PASS = "PASS"
HTML_ENTRY_ALLOWED = "HTML_ENTRY_ALLOWED"
HTML_ENTRY_BLOCKED = "HTML_ENTRY_BLOCKED"

ERRORS = {
    "RV1_OUT_ERR_PRACTICE_BANK_NOT_PASS",
    "RV1_OUT_ERR_OVERLAY_NOT_PASS",
    "RV1_OUT_ERR_RESOLVER_NOT_PASS",
    "RV1_OUT_ERR_OVERLAY_READY_FALSE",
    "RV1_OUT_ERR_DISPLAY_PAYLOAD_UNSAFE",
    "RV1_OUT_ERR_COPIED_MATERIAL_PERSISTED",
    "RV1_OUT_ERR_PRIVATE_HOMEWORK_FALSE",
    "RV1_OUT_ERR_PUBLIC_READY_TRUE",
    "RV1_OUT_ERR_PUBLIC_EXPORT_ALLOWED",
    "RV1_OUT_ERR_COMMERCIAL_DISTRIBUTION_ALLOWED",
    "RV1_OUT_ERR_ANSWER_KEY_VISIBLE_TO_STUDENT",
    "RV1_OUT_ERR_AUTHORITY_STATUS_NOT_CANDIDATE",
    "RV1_OUT_ERR_PROMOTION_STATUS_NOT_NOT_PROMOTED",
    "RV1_OUT_ERR_SCHEMA_VERSION_MISSING",
}


def _get(mapping: Mapping[str, Any], path: str, default: Any = None) -> Any:
    value: Any = mapping
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return default
        value = value[part]
    return value


def _add_error(errors: List[Dict[str, Any]], code: str, message: str, path: str = "") -> None:
    errors.append({"code": code, "message": message, "path": path})


def validate_output_gate_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    package_errors: List[Dict[str, Any]] = []

    if report.get("schema_version") != "reading_v1_private_homework_output_gate.v1":
        _add_error(package_errors, "RV1_OUT_ERR_SCHEMA_VERSION_MISSING", "Invalid schema_version.", "schema_version")

    if report.get("authority_status") != "candidate_only":
        _add_error(package_errors, "RV1_OUT_ERR_AUTHORITY_STATUS_NOT_CANDIDATE", "authority_status must be candidate_only.", "authority_status")

    if report.get("promotion_status") != "not_promoted":
        _add_error(package_errors, "RV1_OUT_ERR_PROMOTION_STATUS_NOT_NOT_PROMOTED", "promotion_status must be not_promoted.", "promotion_status")

    if report.get("private_homework_only") is not True:
        _add_error(package_errors, "RV1_OUT_ERR_PRIVATE_HOMEWORK_FALSE", "private_homework_only must be true.", "private_homework_only")

    if report.get("public_ready") is not False:
        _add_error(package_errors, "RV1_OUT_ERR_PUBLIC_READY_TRUE", "public_ready must be false.", "public_ready")

    _validate_gate_inputs(report, package_errors)
    _validate_render_policy(report, package_errors)

    items = report.get("item_gate_results", [])
    if not isinstance(items, list):
        _add_error(package_errors, "RV1_OUT_ERR_SCHEMA_VERSION_MISSING", "item_gate_results must be a list.", "item_gate_results")
        items = []

    item_reports = [validate_output_gate_item(item, index) for index, item in enumerate(items)]
    error_count = len(package_errors) + sum(len(item["errors"]) for item in item_reports)
    warning_count = sum(len(item["warnings"]) for item in item_reports)
    allowed_item_count = sum(1 for item in item_reports if item["computed_html_entry_allowed"])

    return {
        "schema_version": "reading_v1_private_homework_output_gate_validation_report.v1",
        "validator_status": PASS if error_count == 0 else "FAIL",
        "package_errors": package_errors,
        "item_reports": item_reports,
        "summary": {
            "gate_status": HTML_ENTRY_ALLOWED if error_count == 0 else HTML_ENTRY_BLOCKED,
            "html_entry_allowed": error_count == 0,
            "item_count": len(item_reports),
            "allowed_item_count": allowed_item_count,
            "blocked_item_count": len(item_reports) - allowed_item_count,
            "warning_count": warning_count,
            "error_count": error_count,
        },
    }


def validate_output_gate_item(item: Mapping[str, Any], index: Optional[int] = None) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    source_item_id = item.get("source_item_id") or f"index:{index}"

    if item.get("gate_status") != PASS:
        _add_error(errors, "RV1_OUT_ERR_DISPLAY_PAYLOAD_UNSAFE", "item gate_status must be PASS.", "gate_status")

    if item.get("html_entry_allowed") is not True:
        _add_error(errors, "RV1_OUT_ERR_DISPLAY_PAYLOAD_UNSAFE", "item html_entry_allowed must be true.", "html_entry_allowed")

    checks = item.get("checks")
    if not isinstance(checks, Mapping):
        _add_error(errors, "RV1_OUT_ERR_SCHEMA_VERSION_MISSING", "checks object is required.", "checks")
        checks = {}

    _expect_true(checks, "practice_bank_item_pass", "RV1_OUT_ERR_PRACTICE_BANK_NOT_PASS", errors)
    _expect_true(checks, "overlay_item_pass", "RV1_OUT_ERR_OVERLAY_NOT_PASS", errors)
    _expect_true(checks, "overlay_ready", "RV1_OUT_ERR_OVERLAY_READY_FALSE", errors)
    _expect_true(checks, "display_payload_safe", "RV1_OUT_ERR_DISPLAY_PAYLOAD_UNSAFE", errors)
    _expect_false(checks, "copied_material_persisted", "RV1_OUT_ERR_COPIED_MATERIAL_PERSISTED", errors)
    _expect_true(checks, "answer_key_hidden_from_student", "RV1_OUT_ERR_ANSWER_KEY_VISIBLE_TO_STUDENT", errors)
    _expect_true(checks, "public_export_blocked", "RV1_OUT_ERR_PUBLIC_EXPORT_ALLOWED", errors)
    _expect_true(checks, "commercial_distribution_blocked", "RV1_OUT_ERR_COMMERCIAL_DISTRIBUTION_ALLOWED", errors)

    return {
        "source_item_id": source_item_id,
        "validator_status": PASS if not errors else "FAIL",
        "computed_html_entry_allowed": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def _validate_gate_inputs(report: Mapping[str, Any], errors: List[Dict[str, Any]]) -> None:
    status_paths = {
        "gate_inputs.practice_bank_validator_status": ("RV1_OUT_ERR_PRACTICE_BANK_NOT_PASS", "PracticeBank validator must be PASS."),
        "gate_inputs.overlay_validator_status": ("RV1_OUT_ERR_OVERLAY_NOT_PASS", "Overlay validator must be PASS."),
        "gate_inputs.local_resolver_status": ("RV1_OUT_ERR_RESOLVER_NOT_PASS", "Local resolver policy must be PASS."),
    }
    for path, (code, message) in status_paths.items():
        if _get(report, path) != PASS:
            _add_error(errors, code, message, path)


def _validate_render_policy(report: Mapping[str, Any], errors: List[Dict[str, Any]]) -> None:
    if _get(report, "render_policy.render_mode") != "local_private_homework_only":
        _add_error(errors, "RV1_OUT_ERR_PUBLIC_EXPORT_ALLOWED", "render_mode must be local_private_homework_only.", "render_policy.render_mode")
    if _get(report, "render_policy.allow_public_export") is not False:
        _add_error(errors, "RV1_OUT_ERR_PUBLIC_EXPORT_ALLOWED", "Public export must be blocked.", "render_policy.allow_public_export")
    if _get(report, "render_policy.allow_commercial_distribution") is not False:
        _add_error(errors, "RV1_OUT_ERR_COMMERCIAL_DISTRIBUTION_ALLOWED", "Commercial distribution must be blocked.", "render_policy.allow_commercial_distribution")
    if _get(report, "render_policy.allow_copied_material_persistence") is not False:
        _add_error(errors, "RV1_OUT_ERR_COPIED_MATERIAL_PERSISTED", "Copied material persistence must be blocked.", "render_policy.allow_copied_material_persistence")
    if _get(report, "render_policy.allow_answer_key_display_to_student") is not False:
        _add_error(errors, "RV1_OUT_ERR_ANSWER_KEY_VISIBLE_TO_STUDENT", "Student answer-key display must be blocked.", "render_policy.allow_answer_key_display_to_student")


def _expect_true(checks: Mapping[str, Any], key: str, code: str, errors: List[Dict[str, Any]]) -> None:
    if checks.get(key) is not True:
        _add_error(errors, code, f"checks.{key} must be true.", f"checks.{key}")


def _expect_false(checks: Mapping[str, Any], key: str, code: str, errors: List[Dict[str, Any]]) -> None:
    if checks.get(key) is not False:
        _add_error(errors, code, f"checks.{key} must be false.", f"checks.{key}")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate ReadingV1 private homework OutputGate report.")
    parser.add_argument("output_gate_json", type=Path)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    report = validate_output_gate_report(load_json(args.output_gate_json))
    report_text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report_text + "\n", encoding="utf-8")
    else:
        print(report_text)

    return 0 if report["validator_status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
