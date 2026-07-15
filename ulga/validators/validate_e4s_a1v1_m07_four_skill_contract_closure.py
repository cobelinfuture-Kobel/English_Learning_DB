#!/usr/bin/env python3
"""Independently validate the M07 metadata-only four-skill closure."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m07_four_skill_contract_closure as builder  # noqa: E402

PASS_STATUS = builder.PASS_STATUS
DEFAULT_VALIDATION_PATH = (
    REPO_ROOT / "ulga/reports/e4s_a1v1_m07_four_skill_contract_closure_validation.json"
)


def _validate_invariants(artifact: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = artifact.get("closure_summary", {})
    expected_top = {
        "learning_unit_count": 24,
        "canonical_egp_row_count": 109,
        "shared_item_count": 384,
        "items_per_unit": 16,
        "units_with_all_four_skills": 24,
        "rows_with_all_four_skills": 109,
    }
    for key, expected in expected_top.items():
        if summary.get(key) != expected:
            errors.append(f"summary_{key}:expected={expected}:actual={summary.get(key)!r}")

    for key, expected in (
        ("skill_item_counts", builder.EXPECTED_SKILL_COUNTS),
        ("skill_practice_counts", builder.EXPECTED_PRACTICE_COUNTS),
        ("skill_assessment_counts", builder.EXPECTED_ASSESSMENT_COUNTS),
    ):
        if summary.get(key) != expected:
            errors.append(f"summary_{key}_mismatch")

    units = artifact.get("by_grammar_unit_id")
    if not isinstance(units, list) or len(units) != 24:
        errors.append("unit_matrix_not_24")
    else:
        seen: set[str] = set()
        for row in units:
            grammar_id = str(row.get("grammar_unit_id"))
            if grammar_id in seen:
                errors.append(f"duplicate_grammar_unit:{grammar_id}")
            seen.add(grammar_id)
            if row.get("shared_item_count") != 16:
                errors.append(f"unit_item_count:{grammar_id}")
            if row.get("skill_item_counts") != {
                skill: 4 for skill in builder.SKILLS
            }:
                errors.append(f"unit_skill_counts:{grammar_id}")
            if row.get("skill_practice_counts") != {
                skill: 3 for skill in builder.SKILLS
            }:
                errors.append(f"unit_practice_counts:{grammar_id}")
            if row.get("skill_assessment_counts") != {
                skill: 1 for skill in builder.SKILLS
            }:
                errors.append(f"unit_assessment_counts:{grammar_id}")

    rows = artifact.get("by_canonical_egp_row_id")
    if not isinstance(rows, list) or len(rows) != 109:
        errors.append("row_matrix_not_109")
    else:
        seen_rows: set[str] = set()
        for row in rows:
            row_id = str(row.get("canonical_egp_row_id"))
            if row_id in seen_rows:
                errors.append(f"duplicate_canonical_row:{row_id}")
            seen_rows.add(row_id)
            counts = row.get("skill_item_counts")
            if not isinstance(counts, Mapping):
                errors.append(f"row_skill_counts_missing:{row_id}")
                continue
            if set(counts) != set(builder.SKILLS):
                errors.append(f"row_skill_names:{row_id}")
                continue
            values = [counts[skill] for skill in builder.SKILLS]
            if any(not isinstance(value, int) or value <= 0 for value in values):
                errors.append(f"row_skill_missing:{row_id}")
            if len(set(values)) != 1:
                errors.append(f"row_skill_unbalanced:{row_id}")

    skill_states = artifact.get("skill_states")
    if not isinstance(skill_states, Mapping) or set(skill_states) != set(builder.SKILLS):
        errors.append("skill_states_incomplete")
    else:
        for skill in builder.SKILLS:
            state = skill_states[skill]
            if state.get("contract_item_count") != 96:
                errors.append(f"skill_contract_count:{skill}")
            if state.get("practice_item_count") != 72:
                errors.append(f"skill_practice_count:{skill}")
            if state.get("assessment_item_count") != 24:
                errors.append(f"skill_assessment_count:{skill}")
            if state.get("actual_learner_evidence_count") != 0:
                errors.append(f"skill_false_evidence_claim:{skill}")

        speaking = skill_states["speaking"]
        if speaking.get("real_audio_evidence_state") != "DEFERRED_BY_OPERATOR":
            errors.append("speaking_audio_not_operator_deferred")
        if speaking.get("real_audio_evidence_blocks_m07") is not False:
            errors.append("speaking_audio_incorrectly_blocks_m07")
        if speaking.get("captured_audio_count") != 0:
            errors.append("speaking_captured_audio_false_claim")

    gate = artifact.get("system_gate", {})
    expected_gate = {
        "four_skill_contract_matrix_complete": True,
        "four_skill_structure_complete": True,
        "reading_v1_completion_gate": True,
        "writing_contract_completion_gate": True,
        "listening_local_delivery_gate": True,
        "speaking_contract_and_engine_gate": True,
        "speaking_real_audio_evidence_required_for_m07": False,
        "speaking_real_audio_evidence_state": "DEFERRED_BY_OPERATOR",
        "actual_learner_evidence_complete": False,
        "learner_mastery_claimed": False,
        "m08_progression_allowed": True,
    }
    if gate != expected_gate:
        errors.append("system_gate_mismatch")

    boundaries = artifact.get("claim_boundaries", {})
    expected_boundaries = {
        "metadata_only_artifact": True,
        "private_content_included": False,
        "audio_bytes_included": False,
        "learner_responses_included": False,
        "canonical_authority_writes": 0,
        "public_delivery_count": 0,
        "persistent_learner_state_writes": 0,
        "actual_learner_evidence_complete": False,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "production_runtime_enabled": False,
        "a2_a2plus_in_scope": False,
    }
    if boundaries != expected_boundaries:
        errors.append("claim_boundaries_mismatch")

    if artifact.get("stop_reason") != "NONE":
        errors.append("stop_reason_not_none")
    if artifact.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("next_short_step_mismatch")
    return errors


def validate(
    artifact: Mapping[str, Any],
    report: Mapping[str, Any],
    *,
    rebuild: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        builder.safe_scan(artifact, name="m07_closure")
        builder.safe_scan(report, name="m07_report")
    except (builder.FourSkillClosureError, ValueError) as exc:
        errors.append(str(exc))

    errors.extend(_validate_invariants(artifact))

    expected_report = builder.build_report(artifact)
    if report != expected_report:
        errors.append("m07_report_not_reproducible")

    if rebuild:
        try:
            expected_artifact = builder.build_artifact()
            if artifact != expected_artifact:
                errors.append("m07_closure_not_reproducible")
        except (builder.FourSkillClosureError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"m07_rebuild_failed:{exc}")

    return {
        "task_id": builder.TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "shared_item_count": artifact.get("closure_summary", {}).get(
            "shared_item_count", 0
        ),
        "learning_unit_count": artifact.get("closure_summary", {}).get(
            "learning_unit_count", 0
        ),
        "canonical_egp_row_count": artifact.get("closure_summary", {}).get(
            "canonical_egp_row_count", 0
        ),
        "skills_closed": len(artifact.get("skill_states", {})),
        "speaking_real_audio_evidence_state": artifact.get("system_gate", {}).get(
            "speaking_real_audio_evidence_state"
        ),
        "m08_progression_allowed": artifact.get("system_gate", {}).get(
            "m08_progression_allowed", False
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=builder.OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=builder.REPORT_PATH)
    parser.add_argument(
        "--validation-report",
        type=Path,
        default=DEFAULT_VALIDATION_PATH,
    )
    parser.add_argument(
        "--no-rebuild",
        action="store_true",
        help="Validate structure without rebuilding upstream artifacts.",
    )
    args = parser.parse_args(argv)
    artifact = builder.read_json(args.artifact)
    report = builder.read_json(args.report)
    result = validate(artifact, report, rebuild=not args.no_rebuild)
    builder.write_json(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
