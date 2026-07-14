#!/usr/bin/env python3
"""Run the local A1/A1+ private pilot with a fail-closed coverage gate."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import run_a1_grammar_text_mode_private_pilot_next_unit as base
from ulga.validators.a1_a1plus_delivery_coverage_gate import (
    validate_delivery_unit_coverage,
)

TASK_ID = "R7-M106D_A1A1PlusLocalPrivatePilotSelectorCoverageGateIntegration"


def validate_unit_coverage(
    unit: Mapping[str, Any],
    *,
    coverage_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return validate_delivery_unit_coverage(
        unit,
        coverage_report=coverage_report,
        error_prefix="local_private_pilot",
    )


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
