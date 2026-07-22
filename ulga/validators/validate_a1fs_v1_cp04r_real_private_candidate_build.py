#!/usr/bin/env python3
"""Independently validate the CP04R private pipeline count readback."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp03_unified_existing_24_unit_binding as cp03  # noqa: E402
from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as cp04  # noqa: E402
from ulga.builders import run_a1fs_v1_cp04r_private_production as runner  # noqa: E402


def _safe_scan(value: Any) -> list[str]:
    forbidden = {
        "text",
        "title",
        "payload",
        "prompt",
        "prompt_text",
        "answer",
        "answer_key",
        "accepted_texts",
        "transcript",
        "transcript_text",
        "learner_response",
    }
    errors: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden:
                    errors.append(f"private_or_learner_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return errors


def _expected_unit_readback(
    cp03_artifact: Mapping[str, Any], cp04_artifact: Mapping[str, Any], errors: list[str]
) -> list[dict[str, Any]]:
    cp03_units = cp03_artifact.get("learning_units")
    cp04_units = cp04_artifact.get("learning_units")
    if not isinstance(cp03_units, list) or len(cp03_units) != 24:
        errors.append("cp03_learning_unit_count_not_24")
        cp03_units = []
    if not isinstance(cp04_units, list) or len(cp04_units) != 24:
        errors.append("cp04_learning_unit_count_not_24")
        cp04_units = []
    cp03_by_sequence = {
        row.get("sequence_index"): row
        for row in cp03_units
        if isinstance(row, Mapping)
    }
    cp04_by_sequence = {
        row.get("sequence_index"): row
        for row in cp04_units
        if isinstance(row, Mapping)
    }
    if set(cp03_by_sequence) != set(range(1, 25)):
        errors.append("cp03_sequence_set_mismatch")
    if set(cp04_by_sequence) != set(range(1, 25)):
        errors.append("cp04_sequence_set_mismatch")

    expected: list[dict[str, Any]] = []
    for sequence_index in range(1, 25):
        cp03_row = cp03_by_sequence.get(sequence_index)
        cp04_row = cp04_by_sequence.get(sequence_index)
        if not isinstance(cp03_row, Mapping) or not isinstance(cp04_row, Mapping):
            continue
        identity = (
            cp03_row.get("learning_unit_id"),
            cp03_row.get("grammar_unit_id"),
            cp03_row.get("internal_stage"),
            cp03_row.get("canonical_egp_row_ids"),
        )
        actual_identity = (
            cp04_row.get("learning_unit_id"),
            cp04_row.get("grammar_unit_id"),
            cp04_row.get("internal_stage"),
            cp04_row.get("canonical_egp_row_ids"),
        )
        if identity != actual_identity:
            errors.append(f"unit_identity_drift:{sequence_index}")
        cp04_counts = cp04_row.get("candidate_counts")
        if not isinstance(cp04_counts, Mapping):
            errors.append(f"candidate_counts_missing:{sequence_index}")
            continue
        expected.append(
            {
                "learning_unit_id": cp04_row.get("learning_unit_id"),
                "grammar_unit_id": cp04_row.get("grammar_unit_id"),
                "sequence_index": sequence_index,
                "internal_stage": cp04_row.get("internal_stage"),
                "canonical_egp_row_count": len(cp04_row.get("canonical_egp_row_ids", [])),
                "m11b_reviewed_content_item_count": cp03_row.get(
                    "m11b_reviewed_content_binding", {}
                ).get("admitted_item_count"),
                "raz_material_binding_count": cp03_row.get(
                    "raz_admitted_asset_binding", {}
                ).get("material_count"),
                "content_candidate_count": cp04_counts.get("content_candidate_count"),
                "exercise_candidate_count": cp04_counts.get("exercise_candidate_count"),
                "ready_reuse_exercise_candidate_count": cp04_counts.get(
                    "ready_reuse_exercise_candidate_count"
                ),
                "pending_raz_exercise_derivation_candidate_count": cp04_counts.get(
                    "pending_raz_exercise_derivation_candidate_count"
                ),
                "scene_candidate_count": cp04_counts.get("scene_candidate_count"),
                "candidate_population_status": cp04_row.get(
                    "candidate_population_status"
                ),
            }
        )
    return expected


def validate_artifact(
    artifact: Mapping[str, Any],
    cp03_artifact: Mapping[str, Any],
    cp04_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if artifact.get("task_id") != runner.TASK_ID:
        errors.append("task_id_mismatch")
    if artifact.get("schema_version") != runner.SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY":
        errors.append("scope_mismatch")
    if artifact.get("execution_mode") not in runner.EXECUTION_MODES:
        errors.append("execution_mode_invalid")

    expected_contract = {
        "stages": [cp03.TASK_ID, cp04.TASK_ID, runner.TASK_ID],
        "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
        "new_unit_creation_allowed": False,
        "private_source_payload_in_readback_allowed": False,
        "learner_facing_publication_allowed": False,
    }
    if artifact.get("pipeline_contract") != expected_contract:
        errors.append("pipeline_contract_mismatch")

    expected_source_identity = {
        "cp03_task_id": cp03_artifact.get("task_id"),
        "cp03_sha256": cp04._sha256_value(cp03_artifact),
        "cp04_task_id": cp04_artifact.get("task_id"),
        "cp04_sha256": cp04._sha256_value(cp04_artifact),
        "raz_registry_package_sha256": cp03_artifact.get("source_identity", {}).get(
            "raz_registry_package_sha256"
        ),
    }
    if artifact.get("source_identity") != expected_source_identity:
        errors.append("source_identity_mismatch")

    cp03_summary = cp03_artifact.get("coverage_summary", {})
    cp04_summary = cp04_artifact.get("coverage_summary", {})
    expected_summary = {
        "existing_learning_unit_count": 24,
        "new_learning_unit_count": 0,
        "m11b_reviewed_content_item_count": cp03_summary.get(
            "m11b_reviewed_content_item_count"
        ),
        "raz_promoted_material_input_count": cp03_summary.get(
            "raz_promoted_material_input_count"
        ),
        "raz_distinct_bound_material_count": cp03_summary.get(
            "raz_distinct_bound_material_count"
        ),
        "raz_material_unit_binding_count": cp03_summary.get(
            "raz_material_unit_binding_count"
        ),
        "raz_covered_existing_unit_count": cp03_summary.get(
            "raz_covered_existing_unit_count"
        ),
        "content_candidate_count": cp04_summary.get("content_candidate_count"),
        "exercise_candidate_count": cp04_summary.get("exercise_candidate_count"),
        "ready_reuse_exercise_candidate_count": cp04_summary.get(
            "ready_reuse_exercise_candidate_count"
        ),
        "pending_raz_exercise_derivation_candidate_count": cp04_summary.get(
            "pending_raz_exercise_derivation_candidate_count"
        ),
        "scene_candidate_count": cp04_summary.get("scene_candidate_count"),
        "authority_backed_scene_unit_count": cp04_summary.get(
            "authority_backed_scene_unit_count"
        ),
        "scene_authority_gap_unit_count": cp04_summary.get(
            "scene_authority_gap_unit_count"
        ),
        "candidate_envelope_complete_unit_count": cp04_summary.get(
            "candidate_envelope_complete_unit_count"
        ),
    }
    if artifact.get("coverage_summary") != expected_summary:
        errors.append("coverage_summary_not_reconciled")
    if expected_summary["raz_promoted_material_input_count"] != expected_summary[
        "raz_distinct_bound_material_count"
    ]:
        errors.append("not_every_promoted_raz_material_bound")
    if expected_summary["raz_material_unit_binding_count"] != cp04_summary.get(
        "raz_material_binding_candidate_count"
    ):
        errors.append("cp03_cp04_raz_binding_count_mismatch")

    expected_units = _expected_unit_readback(cp03_artifact, cp04_artifact, errors)
    if artifact.get("unit_count_readback") != expected_units:
        errors.append("unit_count_readback_not_reconciled")

    expected_delta = {
        "cp03_private_binding_rebuilt_and_validated": True,
        "cp04_private_candidate_envelopes_built_and_validated": True,
        "exact_24_unit_counts_emitted": True,
        "existing_24_unit_curriculum_preserved": True,
    }
    if artifact.get("capability_delta") != expected_delta:
        errors.append("capability_delta_mismatch")

    expected_boundaries = {
        "canonical_authority_write_performed": False,
        "private_source_payload_included": False,
        "learner_facing_content_created": False,
        "candidate_admission_decision_created": False,
        "runtime_publication_claimed": False,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "a2_a2plus_in_scope": False,
    }
    if artifact.get("claim_boundaries") != expected_boundaries:
        errors.append("claim_boundaries_mismatch")
    errors.extend(_safe_scan(artifact))
    if artifact.get("stop_reason") != "NONE":
        errors.append("stop_reason_mismatch")
    if artifact.get("next_short_step") != runner.NEXT_SHORT_STEP:
        errors.append("next_short_step_mismatch")

    return {
        "task_id": runner.TASK_ID,
        "validation_status": runner.PASS_STATUS if not errors else "FAIL",
        "errors": errors,
        "validation_counts": expected_summary,
        "exact_24_unit_count_readback_validated": not errors,
        "private_or_learner_content_absent": not _safe_scan(artifact),
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": runner.NEXT_SHORT_STEP if not errors else None,
    }


def main() -> int:
    try:
        cp03_artifact = runner._read(cp03.OUTPUT_PATH)
        cp04_artifact = runner._read(cp04.OUTPUT_PATH)
        artifact = runner._read(runner.READBACK_PATH)
        report = validate_artifact(artifact, cp03_artifact, cp04_artifact)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["validation_status"] == runner.PASS_STATUS else 1
    except (OSError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
