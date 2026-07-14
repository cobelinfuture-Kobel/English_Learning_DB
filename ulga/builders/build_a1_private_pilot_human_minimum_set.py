#!/usr/bin/env python3
"""Compute human-pilot coverage gaps without creating learner evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import build_and_validate_from_repo
from ulga.builders.build_a1_private_pilot_synthetic_pipeline_coverage import HUMAN_PILOT_UNITS

TASK_ID = "R7-M105P09_A1A1PlusSyntheticCoverageGapReviewAndHumanPilotMinimumSet"
DEFAULT_OUTPUT = REPO_ROOT / "ulga/reports/a1_private_pilot_human_minimum_set.json"


def _values(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        return sorted({str(row).strip() for row in value if str(row).strip()})
    return []


def _unit_dimensions(
    unit: Mapping[str, Any], item_index: Mapping[str, Mapping[str, Any]]
) -> set[str]:
    plan = unit["delivery_plan"]
    practice = list(plan["practice_item_ids"])
    assessment = list(plan["assessment_item_ids"])
    dimensions = {
        f"level:{unit.get('level')}",
        "route:practice",
        "route:assessment",
    }
    for role, item_ids in (("practice", practice), ("assessment", assessment)):
        for item_id in item_ids:
            item = item_index[item_id]
            for field in ("task_type", "skill", "item_role", "evidence_dimension"):
                for value in _values(item.get(field)):
                    dimensions.add(f"{field}:{value}")
            rubric = item.get("scoring_rubric", {})
            evaluator = "manual" if item.get("task_type") in {
                "guided_contextual_writing",
                "text_mode_writing_checkpoint",
            } else "rule"
            dimensions.add(f"evaluation:{evaluator}")
            dimensions.add(f"delivery_role:{role}")
            if rubric.get("minimum_score") is not None:
                dimensions.add("contract:minimum_score")
    return dimensions


def _greedy_cover(
    missing: set[str], candidates: Mapping[str, set[str]], sequence: Mapping[str, int]
) -> list[str]:
    remaining = set(missing)
    selected: list[str] = []
    available = dict(candidates)
    while remaining:
        ranked = sorted(
            available,
            key=lambda unit_id: (
                -len(available[unit_id] & remaining),
                sequence[unit_id],
                unit_id,
            ),
        )
        if not ranked or not (available[ranked[0]] & remaining):
            break
        chosen = ranked[0]
        selected.append(chosen)
        remaining -= available[chosen]
        available.pop(chosen)
    return selected


def _union(rows: Iterable[set[str]]) -> set[str]:
    result: set[str] = set()
    for row in rows:
        result.update(row)
    return result


def build_report() -> dict[str, Any]:
    package, package_report = build_and_validate_from_repo()
    if package_report.get("validation_status") != "PASS":
        raise RuntimeError("human_minimum_set_package_validation_failed")

    item_index = {item["item_id"]: item for item in package.get("item_bank", [])}
    units = sorted(package.get("learning_units", []), key=lambda row: row["sequence_index"])
    dimensions_by_unit = {
        unit["grammar_unit_id"]: _unit_dimensions(unit, item_index) for unit in units
    }
    sequence = {unit["grammar_unit_id"]: unit["sequence_index"] for unit in units}
    all_dimensions = _union(dimensions_by_unit.values())
    sampled = sorted(HUMAN_PILOT_UNITS, key=lambda unit_id: sequence[unit_id])
    sampled_dimensions = _union(dimensions_by_unit[unit_id] for unit_id in sampled)
    missing_before = all_dimensions - sampled_dimensions
    candidates = {
        unit_id: dimensions
        for unit_id, dimensions in dimensions_by_unit.items()
        if unit_id not in HUMAN_PILOT_UNITS
    }
    additions = _greedy_cover(missing_before, candidates, sequence)
    minimum_set = sampled + additions
    covered_after = _union(dimensions_by_unit[unit_id] for unit_id in minimum_set)
    missing_after = all_dimensions - covered_after

    unit_rows = []
    for unit in units:
        unit_id = unit["grammar_unit_id"]
        unit_rows.append({
            "grammar_unit_id": unit_id,
            "sequence_index": unit["sequence_index"],
            "human_pilot_sampled": unit_id in HUMAN_PILOT_UNITS,
            "recommended_addition": unit_id in additions,
            "dimension_count": len(dimensions_by_unit[unit_id]),
            "new_dimensions_over_existing_sample": sorted(
                dimensions_by_unit[unit_id] - sampled_dimensions
            ),
        })

    return {
        "task_id": TASK_ID,
        "validation_status": "PASS" if len(units) == 24 and not missing_after else "FAIL",
        "scope": "A1_A1_PLUS_ONLY",
        "unit_count": len(units),
        "coverage_dimension_count": len(all_dimensions),
        "existing_human_pilot_unit_ids": sampled,
        "existing_human_pilot_unit_count": len(sampled),
        "existing_human_dimension_coverage_count": len(sampled_dimensions),
        "missing_dimension_count_before_recommendation": len(missing_before),
        "missing_dimensions_before_recommendation": sorted(missing_before),
        "recommended_additional_human_pilot_unit_ids": additions,
        "recommended_additional_human_pilot_unit_count": len(additions),
        "computed_minimum_human_pilot_unit_ids": minimum_set,
        "computed_minimum_human_pilot_unit_count": len(minimum_set),
        "missing_dimension_count_after_recommendation": len(missing_after),
        "missing_dimensions_after_recommendation": sorted(missing_after),
        "human_input_policy": (
            "NO_MORE_PER_UNIT_INPUT" if not missing_after else "ONLY_RECOMMENDED_UNITS_IF_REAL_VALIDATION_IS_REQUESTED"
        ),
        "units": unit_rows,
        "claims": {
            "synthetic_pipeline_coverage_complete": True,
            "learner_evidence_created": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "automatic_per_unit_human_input_required": False,
        },
        "next_short_step": "R7-M105P10_A1A1PlusRetentionScheduleAndCoverageCloseout",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
