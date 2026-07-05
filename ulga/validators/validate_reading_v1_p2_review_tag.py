"""Validator for ReadingV1 P2 local review tag records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

SCHEMA_VERSION = "reading_v1_p2_review_tag.v1"
REPORT_VERSION = "reading_v1_p2_review_tag_validation_report.v1"

ALLOWED_TAGS = {
    "literal_detail_miss",
    "who_what_where_when_confusion",
    "vocabulary_context_miss",
    "sequence_order_miss",
    "yes_no_mismatch",
    "true_false_mismatch",
    "unanswered",
}


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _err(errors: List[Dict[str, str]], code: str, path: str, message: str) -> None:
    errors.append({"code": code, "path": path, "message": message})


def validate_review_tag(record: Mapping[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []

    if record.get("schema_version") != SCHEMA_VERSION:
        _err(errors, "RV1_P2_TAG_ERR_SCHEMA", "schema_version", "schema_version mismatch")
    if not _present(record.get("item_id")):
        _err(errors, "RV1_P2_TAG_ERR_ITEM_ID", "item_id", "item_id required")
    if record.get("review_tag") not in ALLOWED_TAGS:
        _err(errors, "RV1_P2_TAG_ERR_TAG", "review_tag", "review_tag not allowed")
    if record.get("review_boundary") != "local_private_review_only":
        _err(errors, "RV1_P2_TAG_ERR_BOUNDARY", "review_boundary", "review boundary mismatch")
    if record.get("learner_state_write") is not False:
        _err(errors, "RV1_P2_TAG_ERR_STATE_WRITE", "learner_state_write", "learner_state_write must be false")

    _validate_guards(record, errors)

    return {
        "schema_version": REPORT_VERSION,
        "validator_status": "PASS" if not errors else "FAIL",
        "item_id": record.get("item_id"),
        "computed_ready": not errors,
        "errors": errors,
        "warnings": [],
        "summary": {"error_count": len(errors), "warning_count": 0},
    }


def _validate_guards(record: Mapping[str, Any], errors: List[Dict[str, str]]) -> None:
    expected = {
        "private_homework_only": True,
        "public_ready": False,
        "not_for_public_export": True,
        "not_for_commercial_distribution": True,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
    }
    for key, value in expected.items():
        if record.get(key) != value:
            _err(errors, "RV1_P2_TAG_ERR_GUARD", key, f"{key} must be {value!r}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate one ReadingV1 P2 review tag JSON.")
    parser.add_argument("review_tag_json", type=Path)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    report = validate_review_tag(load_json(args.review_tag_json))
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["validator_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
