#!/usr/bin/env python3
"""Run the local A1/A1+ private pilot with a fail-closed coverage gate.

This is the canonical local entry point after R7-M106D. It delegates the
interactive execution flow to the existing next-unit runner, but replaces its
selector with a wrapper that requires every canonical EGP row on the selected
unit to be present and COVERED in the recomputed A1/A1+ coverage consumer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import run_a1_grammar_text_mode_private_pilot_next_unit as base
from ulga.query.a1_a1plus_coverage_query import get_row, load_coverage

TASK_ID = "R7-M106D_A1A1PlusLocalPrivatePilotSelectorCoverageGateIntegration"


def validate_unit_coverage(
    unit: Mapping[str, Any],
    *,
    coverage_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    grammar_unit_id = unit.get("grammar_unit_id")
    row_ids = unit.get("canonical_egp_row_ids", [])
    if not isinstance(row_ids, list) or not row_ids:
        raise ValueError(
            f"local_private_pilot_unit_has_no_canonical_rows:{grammar_unit_id}"
        )

    report = coverage_report or load_coverage()
    blocked: list[dict[str, Any]] = []
    covered: list[str] = []
    for row_id in row_ids:
        row = get_row(str(row_id), report)
        status = row.get("status") if row else "UNKNOWN"
        if status != "COVERED":
            blocked.append({"egp_row_id": row_id, "status": status})
        else:
            covered.append(str(row_id))

    if blocked:
        raise ValueError(
            "local_private_pilot_unit_coverage_gate_blocked:"
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
        "status": "PASS_ALL_CANONICAL_ROWS_COVERED",
        "grammar_unit_id": grammar_unit_id,
        "canonical_egp_row_ids": covered,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
    }


def select_next_covered_unit(
    package: Mapping[str, Any],
    *,
    executed_unit_ids: set[str],
    progression_ready_unit_ids: set[str],
    requested_unit_id: str | None = None,
    coverage_report: Mapping[str, Any] | None = None,
) -> Mapping[str, Any] | None:
    unit = base.select_next_unit(
        package,
        executed_unit_ids=executed_unit_ids,
        progression_ready_unit_ids=progression_ready_unit_ids,
        requested_unit_id=requested_unit_id,
    )
    if unit is not None:
        validate_unit_coverage(unit, coverage_report=coverage_report)
    return unit


def main(argv: list[str] | None = None) -> int:
    original_selector = base.select_next_unit

    def _covered_selector(
        package: Mapping[str, Any],
        *,
        executed_unit_ids: set[str],
        progression_ready_unit_ids: set[str],
        requested_unit_id: str | None = None,
    ) -> Mapping[str, Any] | None:
        unit = original_selector(
            package,
            executed_unit_ids=executed_unit_ids,
            progression_ready_unit_ids=progression_ready_unit_ids,
            requested_unit_id=requested_unit_id,
        )
        if unit is not None:
            validate_unit_coverage(unit)
        return unit

    base.select_next_unit = _covered_selector
    try:
        return base.main(argv)
    finally:
        base.select_next_unit = original_selector


if __name__ == "__main__":
    raise SystemExit(main())
