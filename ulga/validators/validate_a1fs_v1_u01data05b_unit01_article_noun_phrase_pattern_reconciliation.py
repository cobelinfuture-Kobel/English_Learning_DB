#!/usr/bin/env python3
"""Validate Unit01 article noun-phrase pattern reconciliation."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_u01data05b_unit01_article_noun_phrase_pattern_reconciliation as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01DATA05B_UNIT01_ARTICLE_NP_PATTERN_RECONCILIATION_VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_U01DATA05B_UNIT01_ARTICLE_NP_PATTERN_RECONCILIATION_VALIDATION"


class ValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValidationError(code)


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    require(report.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_VERSION_INVALID")
    require(report.get("task_id") == builder.TASK_ID, "TASK_ID_INVALID")
    require(report.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(report.get("unit", {}).get("unit_id") == builder.UNIT_ID, "UNIT_ID_INVALID")
    expected_digest = str(report.get("reconciliation_sha256") or "")
    core = {key: deepcopy(value) for key, value in report.items() if key != "reconciliation_sha256"}
    require(expected_digest == builder.digest(core), "RECONCILIATION_DIGEST_INVALID")

    contract = report.get("unit_local_pattern_contract") or {}
    patterns = contract.get("patterns") or []
    require(patterns == [deepcopy(row) for row in builder.UNIT_LOCAL_PATTERNS], "UNIT_LOCAL_PATTERN_CONTRACT_INVALID")
    require(contract.get("this_is_carrier_clause_role") == "FORMULAIC_SCAFFOLD_NOT_UNIT01_ASSESSMENT_TARGET", "THIS_IS_ROLE_INVALID")
    require(contract.get("global_pattern_authority_write_allowed") is False, "GLOBAL_PATTERN_WRITE_ALLOWED")

    deferred = report.get("deferred_global_patterns") or []
    require([row.get("pattern_id") for row in deferred] == list(builder.LEGACY_DEMONSTRATIVE_PATTERN_IDS), "DEFERRED_PATTERN_IDS_INVALID")
    for row in deferred:
        require(row.get("unit01_status") == "DEFERRED_TO_DEMONSTRATIVE_UNIT_NOT_UNIT01_TARGET", f"DEFERRED_STATUS_INVALID:{row.get('pattern_id')}")
        require(row.get("coverage_claim_allowed") is False, f"DEFERRED_COVERAGE_ALLOWED:{row.get('pattern_id')}")

    rows = report.get("activity_pattern_reconciliations") or []
    require(isinstance(rows, list) and len(rows) == builder.EXPECTED_ACTIVITY_COUNT, "ACTIVITY_COUNT_INVALID")
    require(len({row.get("activity_id") for row in rows}) == len(rows), "ACTIVITY_ID_DUPLICATE")
    allowed = {row["pattern_id"] for row in builder.UNIT_LOCAL_PATTERNS}
    expected_ids = set(builder.EXPECTED_ARTICLE_NP_ACTIVITY_IDS) | {builder.OPEN_WRITING_ACTIVITY_ID}
    require({row.get("activity_id") for row in rows} == expected_ids, "ACTIVITY_ID_SET_INVALID")
    for row in rows:
        activity_id = str(row["activity_id"])
        require(row.get("legacy_broadcast_pattern_ids") == sorted(builder.LEGACY_DEMONSTRATIVE_PATTERN_IDS), f"LEGACY_BROADCAST_INVALID:{activity_id}")
        require(row.get("legacy_broadcast_status") == "REJECTED_NOT_ACTIVITY_SPECIFIC_EVIDENCE", f"LEGACY_STATUS_INVALID:{activity_id}")
        require(set(row.get("unit_allowed_pattern_ids", [])) == allowed, f"UNIT_ALLOWED_PATTERN_SET_INVALID:{activity_id}")
        realized = row.get("activity_realized_pattern_ids")
        require(isinstance(realized, list) and set(realized).issubset(allowed), f"REALIZED_PATTERN_INVALID:{activity_id}")
        require(not set(realized).intersection(builder.LEGACY_DEMONSTRATIVE_PATTERN_IDS), f"DEMONSTRATIVE_PROMOTED:{activity_id}")
        require(row.get("demonstrative_pattern_coverage_claimed") is False, f"DEMONSTRATIVE_COVERAGE_CLAIMED:{activity_id}")
        require(row.get("global_pattern_authority_mutated") is False, f"GLOBAL_PATTERN_MUTATED:{activity_id}")
        if activity_id == builder.OPEN_WRITING_ACTIVITY_ID:
            require(realized == [], "OPEN_WRITING_PATTERN_PREDETERMINED")
            require(row.get("pattern_coverage_eligible") is False, "OPEN_WRITING_COVERAGE_ELIGIBLE")
        else:
            require(realized == ["U01-NP-ARTICLE-NOUN"], f"ARTICLE_NP_PATTERN_NOT_RESOLVED:{activity_id}")
            require(row.get("pattern_coverage_eligible") is True, f"ARTICLE_NP_COVERAGE_NOT_ELIGIBLE:{activity_id}")

    summary = report.get("coverage_summary") or {}
    require(summary.get("activity_count") == 24, "SUMMARY_ACTIVITY_COUNT_INVALID")
    require(summary.get("coverage_eligible_activity_count") == 23, "SUMMARY_ELIGIBLE_COUNT_INVALID")
    require(summary.get("pending_open_writing_activity_count") == 1, "SUMMARY_PENDING_COUNT_INVALID")
    require(summary.get("activity_count_by_unit_local_pattern") == {
        "U01-NP-ARTICLE-NOUN": 23,
        "U01-NP-ARTICLE-ADJECTIVE-NOUN": 0,
        "U01-NP-A-VERY-ADJECTIVE-NOUN": 0,
    }, "SUMMARY_PATTERN_COUNTS_INVALID")
    require(summary.get("covered_unit_local_pattern_ids") == ["U01-NP-ARTICLE-NOUN"], "SUMMARY_COVERED_SET_INVALID")
    require(summary.get("uncovered_unit_local_pattern_ids") == [
        "U01-NP-A-VERY-ADJECTIVE-NOUN",
        "U01-NP-ARTICLE-ADJECTIVE-NOUN",
    ], "SUMMARY_UNCOVERED_SET_INVALID")
    require(summary.get("legacy_demonstrative_broadcast_activity_count") == 24, "SUMMARY_LEGACY_BROADCAST_INVALID")
    require(summary.get("demonstrative_pattern_coverage_count") == 0, "SUMMARY_DEMONSTRATIVE_COVERAGE_INVALID")
    require(summary.get("coverage_merge_across_np_structures_allowed") is False, "NP_STRUCTURE_COVERAGE_MERGE_ALLOWED")

    boundaries = report.get("boundaries") or {}
    require(boundaries and all(value is False for value in boundaries.values()), "BOUNDARY_CHANGED")
    return {
        "validator_id": VALIDATOR_ID,
        "task_id": builder.TASK_ID,
        "validation_status": PASS_STATUS,
        "error_count": 0,
        "errors": [],
        "activity_count": len(rows),
        "coverage_eligible_activity_count": 23,
        "demonstrative_pattern_coverage_count": 0,
        "stop_reason": "NONE",
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.resolve().read_text(encoding="utf-8"))
        if not isinstance(report, dict):
            raise ValidationError("REPORT_NOT_OBJECT")
        result = validate_report(report)
    except (OSError, json.JSONDecodeError, ValidationError, KeyError, TypeError, ValueError) as exc:
        print("VALIDATION_STATUS=FAIL")
        print(f"ERROR={exc}")
        return 1
    print(f"VALIDATION_STATUS={result['validation_status']}")
    print(f"ACTIVITY_COUNT={result['activity_count']}")
    print(f"COVERAGE_ELIGIBLE_ACTIVITY_COUNT={result['coverage_eligible_activity_count']}")
    print("DEMONSTRATIVE_PATTERN_COVERAGE_COUNT=0")
    print("STOP_REASON=NONE")
    print(f"NEXT_SHORT_STEP={builder.NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
