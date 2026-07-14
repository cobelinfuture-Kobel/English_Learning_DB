#!/usr/bin/env python3
"""Fail-closed package snapshot validator for rowless structural A1 units."""
from __future__ import annotations

from typing import Any, Mapping

TASK_ID = "R7-M106G_A1A1PlusSyntheticCoverageGateRegressionHardening"
EXPECTED_CANONICAL_ROW_COUNT = 109
PASS_STATUS = "PASS_PACKAGE_CANONICAL_SET_COVERED_FOR_ROWLESS_STRUCTURAL_UNIT"


def validate_structural_package_coverage(
    grammar_unit_id: str,
    coverage_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Require an internally consistent 109-row all-COVERED package snapshot."""
    rows = coverage_report.get("rows")
    if not isinstance(rows, list):
        raise ValueError(
            f"synthetic_pipeline_package_coverage_rows_missing:{grammar_unit_id}"
        )

    row_ids: list[str] = []
    noncovered: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(
                f"synthetic_pipeline_package_coverage_row_invalid:{grammar_unit_id}:{index}"
            )
        row_id = row.get("egp_row_id")
        if not isinstance(row_id, str) or not row_id.strip():
            raise ValueError(
                f"synthetic_pipeline_package_coverage_row_id_invalid:{grammar_unit_id}:{index}"
            )
        normalized = row_id.strip()
        row_ids.append(normalized)
        status = row.get("status")
        if status != "COVERED":
            noncovered.append({"egp_row_id": normalized, "status": str(status)})

    unique_ids = set(row_ids)
    if len(row_ids) != EXPECTED_CANONICAL_ROW_COUNT:
        raise ValueError(
            f"synthetic_pipeline_package_coverage_row_count_mismatch:{grammar_unit_id}:"
            f"{len(row_ids)}"
        )
    if len(unique_ids) != EXPECTED_CANONICAL_ROW_COUNT:
        raise ValueError(
            f"synthetic_pipeline_package_coverage_duplicate_rows:{grammar_unit_id}"
        )
    if noncovered:
        raise ValueError(
            f"synthetic_pipeline_package_coverage_noncovered_rows:{grammar_unit_id}:"
            f"{noncovered}"
        )

    expected_aggregates = {
        "validation_status": "PASS",
        "canonical_row_count": EXPECTED_CANONICAL_ROW_COUNT,
        "covered_row_count": EXPECTED_CANONICAL_ROW_COUNT,
        "missing_row_count": 0,
        "draft_only_row_count": 0,
        "unexpected_row_count": 0,
    }
    drift = {
        key: {"expected": expected, "actual": coverage_report.get(key)}
        for key, expected in expected_aggregates.items()
        if coverage_report.get(key) != expected
    }
    if drift:
        raise ValueError(
            f"synthetic_pipeline_package_coverage_aggregate_mismatch:{grammar_unit_id}:"
            f"{drift}"
        )

    return {
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "grammar_unit_id": grammar_unit_id,
        "canonical_egp_row_ids": [],
        "coverage_gate_mode": "PACKAGE_CANONICAL_SET_FOR_ROWLESS_STRUCTURAL_UNIT",
        "package_canonical_row_count": EXPECTED_CANONICAL_ROW_COUNT,
        "package_covered_row_count": EXPECTED_CANONICAL_ROW_COUNT,
        "package_row_ids_verified_unique": True,
        "package_row_statuses_verified_covered": True,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
    }
