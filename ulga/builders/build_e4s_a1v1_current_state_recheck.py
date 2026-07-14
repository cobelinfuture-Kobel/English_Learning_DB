#!/usr/bin/env python3
"""Recompute the current A1/A1+ four-skill V1 baseline from existing artifacts.

This is a read-only engineering inventory. It does not create learner evidence,
claim mastery or retention, write persistent learner state, or expand A2/A2+.
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

from ulga.builders.build_a1_a1plus_actual_coverage_recheck import (
    build_report as build_actual_coverage,
)
from ulga.builders.build_a1_a1plus_synthetic_gap_inventory import (
    PASS_STATUS as SYNTHETIC_INVENTORY_PASS_STATUS,
    build_inventory as build_synthetic_inventory,
)
from ulga.builders.build_a1_grammar_cross_skill_closure import (
    build_and_validate_from_repo as build_cross_skill_closure,
)
from ulga.builders.build_a1_grammar_operator_confirmation_text_mode_pilot import (
    build_and_validate_from_repo as build_text_mode_promotion,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_text_mode_package,
)
from ulga.builders.build_a1_private_pilot_next_unit_pages_payload import (
    build_payload as build_pages_payload,
)

TASK_ID = "E4S-A1V1-M00_A1A1PlusCurrentStateAndCoverageRecheck"
EPIC_ID = "E4S-A1V1_A1A1PlusCompleteFourSkillLearningSystem"
PASS_STATUS = "PASS_CURRENT_STATE_BASELINE_RECOMPUTED"
DEFAULT_OUTPUT = REPO_ROOT / "ulga/reports/e4s_a1v1_current_state_recheck.json"
NEXT_SHORT_STEP = "E4S-A1V1-M01_AuthorityScopeAndQueryCompleteness"


def _require_source_pass(
    source_name: str,
    report: Mapping[str, Any],
    *,
    accepted_statuses: set[str] | None = None,
) -> None:
    accepted = accepted_statuses or {"PASS"}
    status = str(report.get("validation_status", ""))
    if status not in accepted:
        raise RuntimeError(f"m00_source_validation_failed:{source_name}:{status}")


def _milestone(
    code: str,
    name: str,
    status: str,
    evidence: list[str],
    remaining: list[str],
) -> dict[str, Any]:
    return {
        "milestone": code,
        "name": name,
        "status": status,
        "evidence": evidence,
        "remaining": remaining,
    }


def build_report() -> dict[str, Any]:
    actual_coverage = build_actual_coverage()
    cross_skill, cross_skill_report = build_cross_skill_closure()
    promotion, promotion_report = build_text_mode_promotion()
    package, package_report = build_text_mode_package()
    synthetic_inventory = build_synthetic_inventory()
    pages_payload = build_pages_payload()

    _require_source_pass("actual_coverage", actual_coverage)
    _require_source_pass("cross_skill_closure", cross_skill_report)
    _require_source_pass("text_mode_promotion", promotion_report)
    _require_source_pass("text_mode_package", package_report)
    _require_source_pass(
        "synthetic_inventory",
        synthetic_inventory,
        accepted_statuses={SYNTHETIC_INVENTORY_PASS_STATUS},
    )

    coverage = actual_coverage
    cross_summary = cross_skill.get("coverage_summary", {})
    promotion_summary = promotion.get("coverage_summary", {})
    package_manifest = package.get("package_manifest", {})

    identity_checks = {
        "canonical_rows_109": coverage.get("canonical_row_count") == 109,
        "covered_rows_109": coverage.get("covered_row_count") == 109,
        "no_coverage_gaps": (
            coverage.get("draft_only_row_count") == 0
            and coverage.get("missing_row_count") == 0
            and coverage.get("unexpected_row_count") == 0
        ),
        "canonical_units_24": cross_summary.get("canonical_unit_count") == 24,
        "four_skill_rows_109": all(
            cross_summary.get(field) == 109
            for field in (
                "rows_with_reading_path",
                "rows_with_writing_path",
                "rows_with_listening_path",
                "rows_with_speaking_path",
            )
        ),
        "candidate_cross_skill_missing_zero": (
            cross_summary.get("candidate_cross_skill_missing_row_count") == 0
        ),
        "operator_text_mode_approved_units_24": (
            promotion_summary.get("operator_approved_unit_count") == 24
        ),
        "text_mode_eligible_rows_109": (
            promotion_summary.get("text_mode_pilot_eligible_row_count") == 109
        ),
        "text_mode_package_units_24": package_manifest.get("unit_count") == 24,
        "text_mode_package_items_192": package_manifest.get("item_count") == 192,
        "text_mode_reading_items_96": package_manifest.get("reading_item_count") == 96,
        "text_mode_writing_items_96": package_manifest.get("writing_item_count") == 96,
        "synthetic_units_24": synthetic_inventory.get("unit_count") == 24,
        "synthetic_pass_units_24": (
            synthetic_inventory.get("synthetic_pass_unit_count") == 24
        ),
        "synthetic_gap_units_zero": (
            synthetic_inventory.get("synthetic_gap_unit_count") == 0
        ),
        "pages_payload_coverage_gate_pass": (
            pages_payload.get("coverage_gate", {}).get("status")
            == "PASS_ALL_CANONICAL_ROWS_COVERED"
        ),
        "pages_payload_has_eight_items": pages_payload.get("item_count") == 8,
    }
    failed_identity_checks = sorted(
        name for name, passed in identity_checks.items() if passed is not True
    )
    if failed_identity_checks:
        raise RuntimeError(
            "m00_current_state_identity_failure:"
            + ",".join(failed_identity_checks)
        )

    milestones = [
        _milestone(
            "M00",
            "Current state and coverage recheck",
            "COMPLETE",
            [
                "109/109 canonical grammar rows are COVERED",
                "24/24 canonical units are present",
                "24/24 current synthetic text-mode pipelines pass",
            ],
            [],
        ),
        _milestone(
            "M01",
            "Authority scope/query closure",
            "PARTIAL",
            [
                "Grammar coverage query is fail-closed at 109/109 rows",
                "All four candidate skill paths resolve to the same 109 rows",
            ],
            [
                "Unified A1/A1+ vocabulary/chunk/pattern/theme/situation scope query is not yet verified as one contract",
            ],
        ),
        _milestone(
            "M02",
            "LearningUnit contract/builder",
            "PARTIAL",
            [
                "24 grammar learning units and a 24-unit text-mode package exist",
            ],
            [
                "One shared four-skill LearningUnit contract has not been certified",
            ],
        ),
        _milestone(
            "M03",
            "Shared item/answer/scoring/media contract",
            "PARTIAL",
            [
                "192 approved text-mode items exist",
                "Candidate Reading/Writing/Listening/Speaking activities and checkpoints exist",
            ],
            [
                "One shared media and productive-skill scoring envelope is not yet certified",
            ],
        ),
        _milestone(
            "M04",
            "Reading V1 completion",
            "PARTIAL",
            [
                "109/109 rows have a Reading candidate path",
                "The approved text-mode package contains 96 Reading items",
            ],
            [
                "Reading V1 must be re-certified against the new shared LearningUnit and item contracts",
            ],
        ),
        _milestone(
            "M05",
            "Listening V1",
            "PARTIAL",
            ["109/109 rows have transcript-backed Listening candidate paths"],
            [
                "Rendered/validated Listening audio assets remain 0",
                "Learner-facing Listening delivery is not complete",
            ],
        ),
        _milestone(
            "M06",
            "Speaking V1",
            "PARTIAL",
            ["109/109 rows have Speaking prompt/model candidate paths"],
            [
                "Captured Speaking audio remains 0",
                "ASR/manual Speaking transcripts remain 0",
            ],
        ),
        _milestone(
            "M07",
            "Writing V1",
            "PARTIAL",
            [
                "109/109 rows have a Writing candidate path",
                "The approved text-mode package contains 96 Writing items",
            ],
            [
                "Writing rubric and learner delivery must be certified under the shared item contract",
            ],
        ),
        _milestone(
            "M08",
            "Mixed assessment",
            "NOT_STARTED",
            ["Per-skill candidate checkpoints exist"],
            ["A verified cross-skill mixed-assessment contract is absent"],
        ),
        _milestone(
            "M09",
            "Package assembler and validator",
            "PARTIAL",
            [
                "A fail-closed Reading/Writing text-mode package and delivery coverage gate exist",
            ],
            ["A full four-skill package assembler is not yet certified"],
        ),
        _milestone(
            "M10",
            "Learner delivery UI",
            "PARTIAL",
            [
                "A learner-safe eight-item private Pages payload is available",
                "The payload contains no answer key and passes the canonical coverage gate",
            ],
            ["The UI is text-mode and does not yet deliver all four skills"],
        ),
        _milestone(
            "M11",
            "Attempt / Learning Event Log",
            "PARTIAL",
            [
                "Canonical text-mode import/intake/projection paths exist",
                "Three units are marked as historical human-pilot samples",
            ],
            ["One unified four-skill Learning Event Log is not yet certified"],
        ),
        _milestone(
            "M12",
            "Error diagnosis",
            "PARTIAL",
            ["Grammar common-error tags and review projection infrastructure exist"],
            ["Cross-skill error taxonomy and weak-point aggregation are incomplete"],
        ),
        _milestone(
            "M13",
            "Remediation / next practice",
            "PARTIAL",
            ["Review and retention-candidate routing infrastructure exists"],
            ["Generalized remediation packs and bounded next-practice selection are incomplete"],
        ),
        _milestone(
            "M14",
            "24-unit synthetic full-chain QA",
            "PARTIAL",
            ["24/24 current text-mode synthetic pipelines pass with 0 gaps"],
            ["The new full four-skill package/media/event chain has not yet been exercised"],
        ),
        _milestone(
            "M15",
            "Human pilot minimum set",
            "PARTIAL",
            ["Three historical human-pilot sampled units are identified"],
            ["No new representative four-skill human pilot has been executed"],
        ),
        _milestone(
            "M16",
            "Pilot FullFix and expanded validation",
            "NOT_STARTED",
            [],
            ["Requires M15 representative human findings"],
        ),
        _milestone(
            "M17",
            "Retention / transfer evidence",
            "NOT_STARTED",
            ["Retention scheduling infrastructure exists"],
            ["No current delayed retention or transfer evidence is confirmed"],
        ),
        _milestone(
            "M18",
            "A1/A1+ V1 closeout",
            "NOT_STARTED",
            [],
            ["Requires M01-M17 completion and accepted evidence"],
        ),
    ]

    status_counts = {
        status: sum(row["status"] == status for row in milestones)
        for status in ("COMPLETE", "PARTIAL", "NOT_STARTED")
    }

    return {
        "task_id": TASK_ID,
        "epic_id": EPIC_ID,
        "validation_status": PASS_STATUS,
        "scope": "A1_A1_PLUS_ONLY",
        "baseline_mode": "READ_ONLY_RECOMPUTE_FROM_EXISTING_ARTIFACTS",
        "current_position": "M00_COMPLETE_M01_NEXT",
        "source_status": {
            "actual_coverage": actual_coverage["validation_status"],
            "cross_skill_closure": cross_skill_report["validation_status"],
            "text_mode_promotion": promotion_report["validation_status"],
            "text_mode_package": package_report["validation_status"],
            "synthetic_inventory": synthetic_inventory["validation_status"],
            "pages_payload": pages_payload["coverage_gate"]["status"],
        },
        "coverage_summary": {
            "canonical_row_count": coverage["canonical_row_count"],
            "covered_row_count": coverage["covered_row_count"],
            "draft_only_row_count": coverage["draft_only_row_count"],
            "missing_row_count": coverage["missing_row_count"],
            "unexpected_row_count": coverage["unexpected_row_count"],
            "coverage_percent": coverage["coverage_percent"],
            "canonical_unit_count": cross_summary["canonical_unit_count"],
            "candidate_four_skill_closed_row_count": cross_summary[
                "candidate_cross_skill_closed_row_count"
            ],
            "operator_approved_text_mode_unit_count": promotion_summary[
                "operator_approved_unit_count"
            ],
            "text_mode_pilot_eligible_row_count": promotion_summary[
                "text_mode_pilot_eligible_row_count"
            ],
            "text_mode_item_count": package_manifest["item_count"],
            "text_mode_reading_item_count": package_manifest["reading_item_count"],
            "text_mode_writing_item_count": package_manifest["writing_item_count"],
            "synthetic_pass_unit_count": synthetic_inventory[
                "synthetic_pass_unit_count"
            ],
            "synthetic_gap_unit_count": synthetic_inventory[
                "synthetic_gap_unit_count"
            ],
            "historical_human_pilot_sampled_unit_count": synthetic_inventory[
                "historical_human_pilot_sampled_unit_count"
            ],
            "rendered_listening_audio_asset_count": promotion_summary[
                "rendered_listening_audio_asset_count"
            ],
            "captured_speaking_audio_asset_count": promotion_summary[
                "captured_speaking_audio_asset_count"
            ],
        },
        "identity_checks": identity_checks,
        "milestone_status_counts": status_counts,
        "milestones": milestones,
        "claim_boundaries": {
            "m00_baseline_complete": True,
            "candidate_four_skill_paths_are_real_skill_evidence": False,
            "synthetic_pipeline_is_learner_mastery": False,
            "full_four_skill_release_complete": False,
            "retention_confirmed": False,
            "a1_a1plus_v1_closeout_complete": False,
            "a2_a2plus_in_scope": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
        },
        "private_evidence_boundary": {
            "repo_recheck_does_not_read_private_local_learner_state": True,
            "historical_public_sample_marker_count": synthetic_inventory[
                "historical_human_pilot_sampled_unit_count"
            ],
            "new_human_evidence_requested": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
