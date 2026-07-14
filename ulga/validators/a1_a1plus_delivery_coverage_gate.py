#!/usr/bin/env python3
"""Shared fail-closed delivery gate for A1/A1+ canonical EGP coverage."""
from __future__ import annotations

import json
from typing import Any, Mapping

from ulga.query.a1_a1plus_coverage_query import get_row, load_coverage

TASK_ID = "R7-M106E_A1A1PlusSharedDeliveryCoverageGateConsolidation"
PASS_STATUS = "PASS_ALL_CANONICAL_ROWS_COVERED"


def validate_delivery_unit_coverage(
    unit: Mapping[str, Any],
    *,
    coverage_report: Mapping[str, Any] | None = None,
    error_prefix: str = "a1_a1plus_delivery",
) -> dict[str, Any]:
    grammar_unit_id = unit.get("grammar_unit_id")
    row_ids = unit.get("canonical_egp_row_ids", [])
    if not isinstance(row_ids, list) or not row_ids:
        raise ValueError(f"{error_prefix}_unit_has_no_canonical_rows:{grammar_unit_id}")

    report = coverage_report or load_coverage()
    blocked: list[dict[str, Any]] = []
    covered: list[str] = []
    for raw_row_id in row_ids:
        row_id = str(raw_row_id)
        row = get_row(row_id, report)
        status = row.get("status") if row else "UNKNOWN"
        if status != "COVERED":
            blocked.append({"egp_row_id": row_id, "status": status})
        else:
            covered.append(row_id)

    if blocked:
        raise ValueError(
            f"{error_prefix}_coverage_gate_blocked:"
            + json.dumps(
                {
                    "grammar_unit_id": grammar_unit_id,
                    "blocked_rows": blocked,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    return {
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "grammar_unit_id": grammar_unit_id,
        "canonical_egp_row_ids": covered,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
    }
