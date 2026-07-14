#!/usr/bin/env python3
"""Validate the 24 shared A1/A1+ cross-skill LearningUnit envelopes."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_cross_skill_learning_units import (
    NEXT_SHORT_STEP,
    ROWLESS_STRUCTURAL_UNIT_ID,
    SCHEMA_PATH,
    SCHEMA_VERSION,
    SKILLS,
    build_artifact,
)
from ulga.query.a1_a1plus_authority_scope_query import build_scope

TASK_ID = "E4S-A1V1-M02_CrossSkillLearningUnitContractAndBuilder"
PASS_STATUS = "PASS_CROSS_SKILL_LEARNING_UNIT_CONTRACT_VALIDATED"
PENDING_AUTHORITIES = ("vocabulary", "chunk", "pattern", "theme_situation")
REQUIRED_TOP_LEVEL_FIELDS = {
    "learning_unit_id",
    "grammar_unit_id",
    "schema_version",
    "official_cefr_level",
    "internal_stage",
    "sequence_index",
    "status",
    "canonical_egp_row_ids",
    "coverage_binding",
    "prerequisite_unit_ids",
    "learning_content",
    "authority_bindings",
    "skill_bindings",
    "assessment_binding",
    "answer_scoring_binding",
    "media_binding",
    "error_remediation_binding",
    "source_evidence",
    "readiness",
    "claim_boundaries",
}


def _scope_for_stage(stage: str) -> Mapping[str, Any]:
    return build_scope(stage)


def _check_false_fields(
    errors: list[str], prefix: str, payload: Mapping[str, Any], fields: tuple[str, ...]
) -> None:
    for field in fields:
        if payload.get(field) is not False:
            errors.append(prefix + f"false_claim:{field}")


def validate_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if schema.get("additionalProperties") is not False:
        errors.append("schema_top_level_not_closed")
    if set(schema.get("required", [])) != REQUIRED_TOP_LEVEL_FIELDS:
        errors.append("schema_required_fields_mismatch")
    policy = schema.get("x_policy", {})
    if policy.get("a2_a2plus_progression_allowed") is not False:
        errors.append("schema_a2_scope_not_blocked")
    if policy.get("rowless_structural_unit_id") != ROWLESS_STRUCTURAL_UNIT_ID:
        errors.append("schema_rowless_structural_unit_id_mismatch")

    units = artifact.get("learning_units", [])
    if len(units) != 24:
        errors.append("learning_unit_count_not_24")
    unit_ids = [unit.get("learning_unit_id") for unit in units]
    grammar_ids = [unit.get("grammar_unit_id") for unit in units]
    sequence = [unit.get("sequence_index") for unit in units]
    if len(set(unit_ids)) != 24 or None in unit_ids:
        errors.append("learning_unit_ids_not_unique_24")
    if len(set(grammar_ids)) != 24 or None in grammar_ids:
        errors.append("grammar_unit_ids_not_unique_24")
    if sequence != list(range(1, 25)):
        errors.append("learning_unit_sequence_not_1_to_24")

    row_bindings: dict[str, list[str]] = {}
    stage_counts = {"A1": 0, "A1_PLUS": 0}
    rowless_ids: list[str] = []
    direct_ids: list[str] = []

    for unit in units:
        unit_id = unit.get("learning_unit_id")
        grammar_id = unit.get("grammar_unit_id")
        prefix = f"unit:{grammar_id}:"
        if set(unit) != REQUIRED_TOP_LEVEL_FIELDS:
            errors.append(prefix + "top_level_fields_mismatch")
        if unit_id != f"E4S_A1V1_UNIT:{grammar_id}":
            errors.append(prefix + "learning_unit_id_mismatch")
        if unit.get("schema_version") != SCHEMA_VERSION:
            errors.append(prefix + "schema_version_mismatch")
        if unit.get("official_cefr_level") != "A1":
            errors.append(prefix + "official_level_not_a1")

        stage = unit.get("internal_stage")
        if stage not in stage_counts:
            errors.append(prefix + "internal_stage_invalid")
            continue
        stage_counts[stage] += 1
        scope = _scope_for_stage(stage)

        rows = unit.get("canonical_egp_row_ids", [])
        if len(rows) != len(set(rows)):
            errors.append(prefix + "canonical_rows_duplicate")
        coverage = unit.get("coverage_binding", {})
        mode = coverage.get("mode")
        if coverage.get("package_canonical_row_count") != 109:
            errors.append(prefix + "package_canonical_row_count_not_109")
        if coverage.get("package_coverage_status") != (
            "PASS_ALL_CANONICAL_ROWS_COVERED"
        ):
            errors.append(prefix + "package_coverage_status_not_pass")
        if rows:
            direct_ids.append(grammar_id)
            if mode != "DIRECT_CANONICAL_ROWS":
                errors.append(prefix + "direct_rows_coverage_mode_mismatch")
            if coverage.get("structural_unit") is not False:
                errors.append(prefix + "direct_rows_false_structural_flag")
        else:
            rowless_ids.append(grammar_id)
            if grammar_id != ROWLESS_STRUCTURAL_UNIT_ID:
                errors.append(prefix + "unexpected_rowless_unit")
            if mode != "ROWLESS_STRUCTURAL_PACKAGE_GATE":
                errors.append(prefix + "rowless_coverage_mode_mismatch")
            if coverage.get("structural_unit") is not True:
                errors.append(prefix + "rowless_structural_flag_missing")
        for row_id in rows:
            row_bindings.setdefault(row_id, []).append(unit_id)

        content = unit.get("learning_content", {})
        minimums = {
            "learning_objectives": 2,
            "form_rules": 1,
            "meaning_functions": 1,
            "usage_conditions": 1,
            "positive_examples": 1,
            "negative_examples": 1,
            "common_error_tags": 1,
        }
        if not content.get("title_en") or not content.get("title_zh_tw"):
            errors.append(prefix + "titles_missing")
        for field, minimum in minimums.items():
            if len(content.get(field, [])) < minimum:
                errors.append(prefix + f"content_minimum_not_met:{field}")

        bindings = unit.get("authority_bindings", {})
        if set(bindings) != {
            "grammar",
            "vocabulary",
            "chunk",
            "pattern",
            "theme_situation",
        }:
            errors.append(prefix + "authority_binding_set_mismatch")
        grammar_binding = bindings.get("grammar", {})
        if grammar_binding.get("selection_status") != "SELECTED":
            errors.append(prefix + "grammar_not_selected")
        if grammar_binding.get("selected_refs") != [grammar_id]:
            errors.append(prefix + "grammar_selected_ref_mismatch")
        if grammar_binding.get("allowed_pool_count") != scope["counts"]["grammar"]:
            errors.append(prefix + "grammar_allowed_pool_count_mismatch")

        source_authority_map = {
            "vocabulary": "vocabulary",
            "chunk": "chunk",
            "pattern": "pattern",
            "theme_situation": "theme",
        }
        for binding_name in PENDING_AUTHORITIES:
            binding = bindings.get(binding_name, {})
            authority = source_authority_map[binding_name]
            expected_refs = [row["id"] for row in scope["authorities"][authority]]
            if binding.get("selection_status") != "PENDING_CONTENT_BINDING":
                errors.append(prefix + f"{binding_name}_not_pending")
            if binding.get("selected_refs") != []:
                errors.append(prefix + f"{binding_name}_invented_selected_refs")
            if binding.get("allowed_pool_count") != len(expected_refs):
                errors.append(prefix + f"{binding_name}_pool_count_mismatch")
            if binding.get("allowed_pool_refs") != expected_refs:
                errors.append(prefix + f"{binding_name}_pool_refs_mismatch")
            if binding.get("reason") != (
                "NO_DIRECT_PER_UNIT_SOURCE_EVIDENCE_DO_NOT_INVENT_MAPPING"
            ):
                errors.append(prefix + f"{binding_name}_pending_reason_mismatch")

        paths = unit.get("skill_bindings", {})
        if set(paths) != set(SKILLS):
            errors.append(prefix + "skill_set_mismatch")
        for skill in SKILLS:
            path = paths.get(skill, {})
            if len(path.get("activity_ids", [])) != 4:
                errors.append(prefix + f"{skill}_activity_count_not_4")
            if len(path.get("assessment_ids", [])) != 1:
                errors.append(prefix + f"{skill}_assessment_count_not_1")
            if path.get("actual_evidence_status") != "NOT_COLLECTED":
                errors.append(prefix + f"{skill}_false_actual_evidence")
        if paths.get("listening", {}).get("audio_asset_status") != "NOT_RENDERED":
            errors.append(prefix + "listening_audio_false_ready")
        if paths.get("speaking", {}).get("audio_capture_status") != "NOT_IMPLEMENTED":
            errors.append(prefix + "speaking_capture_false_ready")
        if paths.get("speaking", {}).get("asr_status") != "NOT_IMPLEMENTED":
            errors.append(prefix + "speaking_asr_false_ready")

        assessment = unit.get("assessment_binding", {})
        if assessment.get("mixed_assessment_status") != "M08_NOT_CERTIFIED":
            errors.append(prefix + "mixed_assessment_false_complete")
        if set(assessment.get("assessment_ids_by_skill", {})) != set(SKILLS):
            errors.append(prefix + "assessment_skill_set_mismatch")

        scoring = unit.get("answer_scoring_binding", {})
        if scoring.get("shared_contract_status") != "M03_NOT_CERTIFIED":
            errors.append(prefix + "shared_item_contract_false_complete")
        if not scoring.get("current_item_source_refs"):
            errors.append(prefix + "current_item_source_refs_empty")

        expected_media = {
            "text_mode_status": "AVAILABLE",
            "listening_audio_status": "NOT_RENDERED",
            "speaking_capture_status": "NOT_IMPLEMENTED",
            "image_asset_status": "NOT_REQUIRED_BY_CURRENT_SOURCE_PATH",
        }
        if unit.get("media_binding") != expected_media:
            errors.append(prefix + "media_binding_mismatch")

        error_binding = unit.get("error_remediation_binding", {})
        if not error_binding.get("error_tags"):
            errors.append(prefix + "error_tags_empty")
        if error_binding.get("remediation_refs") != []:
            errors.append(prefix + "invented_remediation_refs")
        if error_binding.get("remediation_status") != "M13_NOT_CERTIFIED":
            errors.append(prefix + "remediation_false_complete")

        evidence = unit.get("source_evidence", {})
        if len(evidence.get("source_artifact_ids", [])) < 3:
            errors.append(prefix + "source_artifact_refs_insufficient")
        if len(evidence.get("source_paths", [])) < 3:
            errors.append(prefix + "source_paths_insufficient")
        if not evidence.get("operator_approval_status"):
            errors.append(prefix + "operator_approval_status_missing")

        readiness = unit.get("readiness", {})
        if readiness.get("learning_unit_contract_complete") is not True:
            errors.append(prefix + "learning_unit_contract_not_complete")
        if readiness.get("candidate_four_skill_paths_complete") is not True:
            errors.append(prefix + "candidate_four_skill_paths_not_complete")
        _check_false_fields(
            errors,
            prefix,
            readiness,
            (
                "selected_content_authority_bindings_complete",
                "shared_item_contract_complete",
                "learner_delivery_complete",
                "actual_learner_evidence_complete",
            ),
        )
        _check_false_fields(
            errors,
            prefix,
            unit.get("claim_boundaries", {}),
            (
                "candidate_paths_are_real_skill_evidence",
                "learner_mastery_claimed",
                "retention_confirmed",
                "persistent_learner_state_write",
                "production_runtime_event",
                "a2_a2plus_in_scope",
            ),
        )

    if len(row_bindings) != 109:
        errors.append("canonical_row_union_not_109")
    if rowless_ids != [ROWLESS_STRUCTURAL_UNIT_ID]:
        errors.append("rowless_structural_unit_set_mismatch")
    if len(direct_ids) != 23:
        errors.append("direct_canonical_unit_count_not_23")
    if artifact.get("by_egp_row_id") != {
        row_id: sorted(unit_ids) for row_id, unit_ids in sorted(row_bindings.items())
    }:
        errors.append("by_egp_row_id_mismatch")
    if artifact.get("by_grammar_unit_id") != {
        unit["grammar_unit_id"]: unit["learning_unit_id"] for unit in units
    }:
        errors.append("by_grammar_unit_id_mismatch")
    if sum(stage_counts.values()) != 24 or not all(stage_counts.values()):
        errors.append("internal_stage_distribution_invalid")

    expected_summary = {
        "learning_unit_count": 24,
        "canonical_egp_row_count": 109,
        "direct_canonical_unit_count": 23,
        "rowless_structural_unit_count": 1,
        "candidate_four_skill_path_complete_unit_count": 24,
        "operator_approved_text_mode_unit_count": 24,
        "selected_grammar_binding_unit_count": 24,
        "pending_content_authority_binding_unit_count": 24,
    }
    if artifact.get("coverage_summary") != expected_summary:
        errors.append("coverage_summary_mismatch")

    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("m02_learning_unit_contract_complete") is not True:
        errors.append("m02_completion_boundary_missing")
    if boundaries.get("rowless_structural_unit_preserved_without_fake_row") is not True:
        errors.append("rowless_structural_boundary_missing")
    _check_false_fields(
        errors,
        "artifact:",
        boundaries,
        (
            "per_unit_content_authority_selection_complete",
            "shared_item_contract_complete",
            "candidate_paths_are_real_skill_evidence",
            "learner_mastery_claimed",
            "retention_confirmed",
            "persistent_learner_state_write",
            "production_runtime_event",
            "a2_a2plus_in_scope",
        ),
    )

    status = PASS_STATUS if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "validation_status": status,
        "errors": errors,
        "validation_counts": {
            "learning_unit_count": len(units),
            "canonical_egp_row_count": len(row_bindings),
            "direct_canonical_unit_count": len(direct_ids),
            "rowless_structural_unit_count": len(rowless_ids),
            "a1_unit_count": stage_counts["A1"],
            "a1_plus_unit_count": stage_counts["A1_PLUS"],
        },
        "claim_boundaries": {
            "learning_unit_contract_validated": not errors,
            "rowless_structural_unit_preserved_without_fake_row": not errors,
            "per_unit_content_authority_selection_complete": False,
            "shared_item_contract_complete": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if not errors else None,
    }


def validate() -> dict[str, Any]:
    return validate_artifact(build_artifact())


def main() -> int:
    report = validate()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
