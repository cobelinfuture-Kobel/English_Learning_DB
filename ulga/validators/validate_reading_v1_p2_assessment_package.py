"""Validator for ReadingV1 P2 private-practice assessment packages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from ulga.validators.validate_reading_v1_p2_assessment_item import validate_item

SCHEMA_VERSION = "reading_v1_p2_assessment_package.v1"
REPORT_VERSION = "reading_v1_p2_assessment_package_validation_report.v1"


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _err(errors: List[Dict[str, str]], code: str, path: str, message: str) -> None:
    errors.append({"code": code, "path": path, "message": message})


def validate_package(package: Mapping[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []

    if package.get("schema_version") != SCHEMA_VERSION:
        _err(errors, "RV1_P2_PKG_ERR_SCHEMA", "schema_version", "schema_version mismatch")
    if not _present(package.get("package_id")):
        _err(errors, "RV1_P2_PKG_ERR_ID", "package_id", "package_id required")

    _validate_guards(package, errors)

    raw_items = package.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        _err(errors, "RV1_P2_PKG_ERR_ITEMS", "items", "items must be a non-empty list")
        raw_items = []

    item_reports = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, Mapping):
            item_reports.append(
                {
                    "schema_version": "reading_v1_p2_assessment_item_validation_report.v1",
                    "validator_status": "FAIL",
                    "item_id": f"index:{index}",
                    "computed_ready": False,
                    "errors": [
                        {
                            "code": "RV1_P2_PKG_ERR_ITEM_OBJECT",
                            "path": f"items[{index}]",
                            "message": "item must be an object",
                        }
                    ],
                    "warnings": [],
                    "summary": {"error_count": 1, "warning_count": 0},
                }
            )
        else:
            item_reports.append(validate_item(item))

    item_error_count = sum(report["summary"]["error_count"] for report in item_reports)
    error_count = len(errors) + item_error_count

    return {
        "schema_version": REPORT_VERSION,
        "validator_status": "PASS" if error_count == 0 else "FAIL",
        "package_id": package.get("package_id"),
        "package_errors": errors,
        "item_reports": item_reports,
        "summary": {
            "item_count": len(item_reports),
            "ready_item_count": sum(1 for report in item_reports if report["computed_ready"]),
            "error_count": error_count,
            "warning_count": 0,
        },
    }


def _validate_guards(package: Mapping[str, Any], errors: List[Dict[str, str]]) -> None:
    expected = {
        "private_homework_only": True,
        "public_ready": False,
        "not_for_public_export": True,
        "not_for_commercial_distribution": True,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "feedback_boundary": "local_private_practice_only",
        "learner_state_write": False,
    }
    for key, value in expected.items():
        if package.get(key) != value:
            _err(errors, "RV1_P2_PKG_ERR_GUARD", key, f"{key} must be {value!r}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate one ReadingV1 P2 package JSON.")
    parser.add_argument("package_json", type=Path)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)
    report = validate_package(load_json(args.package_json))
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["validator_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
