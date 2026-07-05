"""Checker for ReadingV1 P5 local review sessions."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

SCHEMA_VERSION = "reading_v1_p5_session.v1"
REPORT_VERSION = "reading_v1_p5_session_check_report.v1"


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _add(errors: List[Dict[str, str]], code: str, path: str, message: str) -> None:
    errors.append({"code": code, "path": path, "message": message})


def check_session(session: Mapping[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []
    if session.get("schema_version") != SCHEMA_VERSION:
        _add(errors, "RV1_P5_SESSION_ERR_SCHEMA", "schema_version", "schema_version mismatch")
    if not _present(session.get("session_id")):
        _add(errors, "RV1_P5_SESSION_ERR_ID", "session_id", "session_id required")
    if not _present(session.get("package_id")):
        _add(errors, "RV1_P5_SESSION_ERR_PACKAGE", "package_id", "package_id required")
    if not isinstance(session.get("focus_groups"), list) or not session.get("focus_groups"):
        _add(errors, "RV1_P5_SESSION_ERR_FOCUS", "focus_groups", "focus_groups must be non-empty")
    if session.get("local_only") is not True:
        _add(errors, "RV1_P5_SESSION_ERR_LOCAL", "local_only", "local_only must be true")
    if session.get("public_ready") is not False:
        _add(errors, "RV1_P5_SESSION_ERR_PUBLIC", "public_ready", "public_ready must be false")
    if session.get("learner_state_write") is not False:
        _add(errors, "RV1_P5_SESSION_ERR_STATE", "learner_state_write", "learner_state_write must be false")

    return {
        "schema_version": REPORT_VERSION,
        "validator_status": "PASS" if not errors else "FAIL",
        "session_id": session.get("session_id"),
        "package_id": session.get("package_id"),
        "computed_ready": not errors,
        "errors": errors,
        "warnings": [],
        "summary": {"error_count": len(errors), "warning_count": 0},
    }
