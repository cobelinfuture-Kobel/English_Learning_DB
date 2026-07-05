"""Checker for ReadingV1 P6 local source units."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

SCHEMA_VERSION = "reading_v1_p6_source_unit.v1"
REPORT_VERSION = "reading_v1_p6_source_unit_check_report.v1"
SOURCE_TYPES = {"sentence", "dialogue", "passage"}


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _add(errors: List[Dict[str, str]], code: str, path: str, message: str) -> None:
    errors.append({"code": code, "path": path, "message": message})


def check_source_unit(unit: Mapping[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []
    if unit.get("schema_version") != SCHEMA_VERSION:
        _add(errors, "RV1_P6_SRC_ERR_SCHEMA", "schema_version", "schema_version mismatch")
    if not _present(unit.get("source_unit_id")):
        _add(errors, "RV1_P6_SRC_ERR_ID", "source_unit_id", "source_unit_id required")
    if unit.get("source_type") not in SOURCE_TYPES:
        _add(errors, "RV1_P6_SRC_ERR_TYPE", "source_type", "source_type not allowed")
    if not _present(unit.get("source_text")):
        _add(errors, "RV1_P6_SRC_ERR_TEXT", "source_text", "source_text required")
    if not _present(unit.get("level")):
        _add(errors, "RV1_P6_SRC_ERR_LEVEL", "level", "level required")
    if not _present(unit.get("topic")):
        _add(errors, "RV1_P6_SRC_ERR_TOPIC", "topic", "topic required")
    if not _present(unit.get("reading_skill")):
        _add(errors, "RV1_P6_SRC_ERR_SKILL", "reading_skill", "reading_skill required")
    if unit.get("reviewed") is not True:
        _add(errors, "RV1_P6_SRC_ERR_REVIEWED", "reviewed", "reviewed must be true")
    if unit.get("local_only") is not True:
        _add(errors, "RV1_P6_SRC_ERR_LOCAL", "local_only", "local_only must be true")
    if unit.get("public_ready") is not False:
        _add(errors, "RV1_P6_SRC_ERR_PUBLIC", "public_ready", "public_ready must be false")

    return {
        "schema_version": REPORT_VERSION,
        "validator_status": "PASS" if not errors else "FAIL",
        "source_unit_id": unit.get("source_unit_id"),
        "computed_ready": not errors,
        "errors": errors,
        "warnings": [],
        "summary": {"error_count": len(errors), "warning_count": 0},
    }
