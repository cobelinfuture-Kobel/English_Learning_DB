#!/usr/bin/env python3
"""Recompute A1/A1+ EGP coverage from existing canonical artifacts only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_derived_pedagogy_fullfix import build_artifact as build_pedagogy_artifact
from ulga.builders.build_a1_grammar_operator_confirmation_text_mode_pilot import build_and_validate_from_repo as build_promotion_source
from ulga.builders.build_a1_grammar_text_mode_practice_item_fullfix import build_and_validate_from_repo as build_practice_source
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import build_and_validate_from_repo as build_package_source

TASK_ID = "R7-M106_A1A1PlusActualCoverageRecheck_NoNewDesignDocs"
DEFAULT_OUTPUT = REPO_ROOT / "ulga/reports/a1_a1plus_actual_coverage_recheck.json"


def _row_ready(row: Mapping[str, Any]) -> bool:
    return bool(row.get("reading_item_ids")) and bool(row.get("writing_item_ids")) and bool(row.get("assessment_item_ids"))


def build_report() -> dict[str, Any]:
    practice, practice_report = build_practice_source()
    if practice_report.get("validation_status") != "PASS":
        raise RuntimeError("coverage_recheck_practice_source_failed")
    pedagogy = build_pedagogy_artifact(practice)
    promotion, promotion_report = build_promotion_source()
    if promotion_report.get("validation_status") != "PASS":
        raise RuntimeError("coverage_recheck_promotion_source_failed")
    package, package_report = build_package_source()
    if package_report.get("validation_status") != "PASS":
        raise RuntimeError("coverage_recheck_package_source_failed")

    canonical_rows = set(pedagogy.get("by_egp_row_id", {}))
    approved_rows = set(promotion.get("by_egp_row_id", {}))
    package_rows = package.get("by_egp_row_id", {})
    covered = sorted(
        row_id
        for row_id, row in package_rows.items()
        if row_id in approved_rows and _row_ready(row)
    )
    draft_only = sorted((canonical_rows & set(package_rows)) - set(covered))
    missing = sorted(canonical_rows - set(package_rows))
    unexpected = sorted(set(package_rows) - canonical_rows)

    row_status = []
    for row_id in sorted(canonical_rows):
        status = "COVERED" if row_id in covered else "DRAFT_ONLY" if row_id in draft_only else "MISSING"
        row = package_rows.get(row_id, {})
        row_status.append({
            "egp_row_id": row_id,
            "status": status,
            "grammar_unit_ids": list(row.get("grammar_unit_ids", [])),
            "reading_item_count": len(row.get("reading_item_ids", [])),
            "writing_item_count": len(row.get("writing_item_ids", [])),
            "assessment_item_count": len(row.get("assessment_item_ids", [])),
        })

    total = len(canonical_rows)
    covered_count = len(covered)
    return {
        "task_id": TASK_ID,
        "validation_status": "PASS" if total == 109 and not missing and not draft_only and not unexpected else "FAIL",
        "scope": "A1_A1_PLUS_ONLY",
        "canonical_row_count": total,
        "covered_row_count": covered_count,
        "draft_only_row_count": len(draft_only),
        "missing_row_count": len(missing),
        "unexpected_row_count": len(unexpected),
        "coverage_percent": round((covered_count / total * 100.0) if total else 0.0, 2),
        "covered_row_ids": covered,
        "draft_only_row_ids": draft_only,
        "missing_row_ids": missing,
        "unexpected_row_ids": unexpected,
        "rows": row_status,
        "claims": {
            "canonical_mapping_coverage_complete": not missing and not draft_only and not unexpected,
            "synthetic_pipeline_coverage_is_learner_mastery": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "a2_or_a2plus_in_scope": False,
        },
        "next_short_step": "R7-M106A_A1A1PlusCoverageRegressionGateIntegration",
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
