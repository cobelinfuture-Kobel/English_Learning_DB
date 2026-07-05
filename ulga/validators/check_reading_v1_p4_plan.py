"""Checker for ReadingV1 P4 local review plans."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

SCHEMA_VERSION = "reading_v1_p4_plan.v1"
REPORT_VERSION = "reading_v1_p4_plan_check_report.v1"


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _add(errors: List[Dict[str, str]], code: str, path: str, message: str) -> None:
    errors.append({"code": code, "path": path, "message": message})


def check_plan(plan: Mapping[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []
    if plan.get("schema_version") != SCHEMA_VERSION:
        _add(errors, "RV1_P4_PLAN_ERR_SCHEMA", "schema_version", "schema_version mismatch")
    if not _present(plan.get("package_id")):
        _add(errors, "RV1_P4_PLAN_ERR_PACKAGE", "package_id", "package_id required")
    if not isinstance(plan.get("focus_groups"), list) or not plan.get("focus_groups"):
        _add(errors, "RV1_P4_PLAN_ERR_FOCUS", "focus_groups", "focus_groups must be non-empty")
    if plan.get("local_only") is not True:
        _add(errors, "RV1_P4_PLAN_ERR_LOCAL", "local_only", "local_only must be true")
    if plan.get("public_ready") is not False:
        _add(errors, "RV1_P4_PLAN_ERR_PUBLIC", "public_ready", "public_ready must be false")
    if plan.get("learner_state_write") is not False:
        _add(errors, "RV1_P4_PLAN_ERR_STATE", "learner_state_write", "learner_state_write must be false")

    return {
        "schema_version": REPORT_VERSION,
        "validator_status": "PASS" if not errors else "FAIL",
        "package_id": plan.get("package_id"),
        "computed_ready": not errors,
        "errors": errors,
        "warnings": [],
        "summary": {"error_count": len(errors), "warning_count": 0},
    }
