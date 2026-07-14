#!/usr/bin/env python3
"""Build a non-blocking A1/A1+ retention schedule and engineering closeout."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_private_pilot_human_minimum_set import build_report as build_minimum_set
from ulga.builders.build_a1_private_pilot_synthetic_pipeline_coverage import build_report as build_synthetic_coverage

TASK_ID = "R7-M105P10_A1A1PlusRetentionScheduleAndCoverageCloseout"
DEFAULT_OUTPUT = REPO_ROOT / "ulga/reports/a1_private_pilot_retention_schedule_closeout.json"
MINIMUM_DELAY_HOURS = 24
FIXTURES = {
    "GRAMMAR_REGULAR_PLURAL_NOUNS": REPO_ROOT / "tests/fixtures/a1_grammar_text_mode/browser_review_regular_plurals_attempt3.json",
    "GRAMMAR_SUBJECT_PRONOUNS": REPO_ROOT / "tests/fixtures/a1_grammar_text_mode/subject_pronouns_p03_attempt2.json",
}
PRIVATE_ONLY_UNITS = {"GRAMMAR_ARTICLES_BASIC"}


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("retention_schedule_timezone_required")
    return parsed.astimezone(timezone.utc)


def build_report(*, now: datetime | None = None) -> dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    synthetic = build_synthetic_coverage()
    minimum = build_minimum_set()
    schedules = []
    for unit_id, path in FIXTURES.items():
        source = json.loads(path.read_text(encoding="utf-8"))
        baseline = _parse(source["session"]["completed_at"])
        eligible = baseline + timedelta(hours=MINIMUM_DELAY_HOURS)
        schedules.append({
            "grammar_unit_id": unit_id,
            "baseline_completed_at": baseline.isoformat(),
            "retention_eligible_at": eligible.isoformat(),
            "status": "ELIGIBLE_FOR_REAL_RETENTION" if now >= eligible else "DEFERRED_UNTIL_ELIGIBLE",
            "retention_evidence_created": False,
            "final_mastery_claimed": False,
        })
    for unit_id in sorted(PRIVATE_ONLY_UNITS):
        schedules.append({
            "grammar_unit_id": unit_id,
            "status": "PRIVATE_BASELINE_NOT_COMMITTED",
            "retention_evidence_created": False,
            "final_mastery_claimed": False,
        })

    engineering_pass = (
        synthetic["validation_status"] == "PASS"
        and synthetic["pipeline_pass_unit_count"] == 24
        and minimum["validation_status"] == "PASS"
        and minimum["missing_dimension_count_after_recommendation"] == 0
    )
    return {
        "task_id": TASK_ID,
        "validation_status": "PASS" if engineering_pass else "FAIL",
        "scope": "A1_A1_PLUS_ONLY",
        "generated_at": now.isoformat(),
        "minimum_delay_hours": MINIMUM_DELAY_HOURS,
        "pipeline_coverage": {
            "unit_count": synthetic["unit_count"],
            "pipeline_pass_unit_count": synthetic["pipeline_pass_unit_count"],
        },
        "human_pilot_coverage": {
            "existing_sampled_unit_count": minimum["existing_human_pilot_unit_count"],
            "computed_minimum_unit_count": minimum["computed_minimum_human_pilot_unit_count"],
            "missing_dimension_count": minimum["missing_dimension_count_after_recommendation"],
            "per_unit_human_input_required": False,
        },
        "retention_schedule": sorted(schedules, key=lambda row: row["grammar_unit_id"]),
        "engineering_closeout_status": "PASS_COVERAGE_CLOSED_RETENTION_REMAINS_SEPARATE" if engineering_pass else "FAIL",
        "claims": {
            "engineering_pipeline_coverage_complete": engineering_pass,
            "learner_evidence_created": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
        },
        "next_short_step": "R7-M106_A1A1PlusActualCoverageRecheck_NoNewDesignDocs",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
