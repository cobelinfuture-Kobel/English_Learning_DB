#!/usr/bin/env python3
"""Build a synthetic-only A1/A1+ coverage gap inventory.

This milestone does not collect, create, or infer learner evidence. It consumes
only the existing engineering pipeline report and classifies actionable gaps.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_private_pilot_synthetic_pipeline_coverage import build_report

TASK_ID = "R7-M105P09_A1A1PlusSyntheticCoverageGapReviewAndHumanPilotMinimumSet"
DEFAULT_OUTPUT = REPO_ROOT / "ulga/reports/a1_a1plus_synthetic_gap_inventory.json"
PASS_STATUS = "PASS_NO_SYNTHETIC_PIPELINE_GAPS"
FAIL_STATUS = "FAIL_SYNTHETIC_PIPELINE_GAPS_PRESENT"


def _failed_checks(unit: Mapping[str, Any]) -> list[str]:
    if "checks" not in unit:
        return ["checks_missing"]
    checks = unit.get("checks")
    if not isinstance(checks, Mapping):
        return ["checks_missing"]
    return sorted(str(name) for name, passed in checks.items() if passed is not True)


def build_inventory() -> dict[str, Any]:
    pipeline = build_report()
    units = pipeline.get("units", [])
    if not isinstance(units, list):
        raise ValueError("synthetic_gap_inventory_units_missing")

    inventory_units: list[dict[str, Any]] = []
    gap_unit_ids: list[str] = []
    for unit in units:
        if not isinstance(unit, Mapping):
            raise ValueError("synthetic_gap_inventory_unit_invalid")
        grammar_id = str(unit.get("grammar_unit_id", ""))
        failed = _failed_checks(unit)
        if failed:
            gap_unit_ids.append(grammar_id)
        inventory_units.append(
            {
                "grammar_unit_id": grammar_id,
                "sequence_index": unit.get("sequence_index"),
                "coverage_gate_mode": unit.get("coverage_gate_mode"),
                "coverage_gate_status": unit.get("coverage_gate_status"),
                "synthetic_pipeline_status": "GAP" if failed else "PASS",
                "failed_checks": failed,
                "historical_human_pilot_sampled": unit.get("human_pilot_sampled") is True,
                "new_human_evidence_requested": False,
                "learner_mastery_claimed": False,
                "retention_confirmed": False,
            }
        )

    pipeline_pass = pipeline.get("validation_status") == "PASS"
    gap_free = not gap_unit_ids and len(inventory_units) == 24 and pipeline_pass
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if gap_free else FAIL_STATUS,
        "scope": "A1_A1_PLUS_ONLY",
        "decision_mode": "SYNTHETIC_GAP_INVENTORY_ONLY",
        "unit_count": len(inventory_units),
        "synthetic_pass_unit_count": sum(row["synthetic_pipeline_status"] == "PASS" for row in inventory_units),
        "synthetic_gap_unit_count": len(gap_unit_ids),
        "synthetic_gap_unit_ids": sorted(gap_unit_ids),
        "direct_canonical_gate_unit_count": pipeline.get("direct_canonical_gate_unit_count"),
        "rowless_structural_gate_unit_count": pipeline.get("rowless_structural_gate_unit_count"),
        "rowless_structural_unit_ids": pipeline.get("rowless_structural_unit_ids", []),
        "historical_human_pilot_sampled_unit_count": sum(
            row["historical_human_pilot_sampled"] for row in inventory_units
        ),
        "new_human_evidence_requested_unit_count": 0,
        "inventory_units": inventory_units,
        "claims": {
            "learner_evidence_created": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
        },
        "next_short_step": "R7-M104E16A_A1A1PlusCoverageRecheck_NoNewDesignDocs",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    inventory = build_inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(inventory, ensure_ascii=False, indent=2))
    return 0 if inventory["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
