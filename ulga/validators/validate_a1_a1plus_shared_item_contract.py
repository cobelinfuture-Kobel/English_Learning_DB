#!/usr/bin/env python3
"""Validate the common A1/A1+ four-skill item/answer/scoring/media envelope."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_shared_item_contract import (
    NEXT_SHORT_STEP,
    SCHEMA_PATH,
    SCHEMA_VERSION,
    SKILLS,
    SOURCE_COUNTS,
    build_artifact,
)

TASK_ID = "E4S-A1V1-M03_SharedItemAnswerScoringMediaContract"
PASS_STATUS = "PASS_SHARED_ITEM_ANSWER_SCORING_MEDIA_CONTRACT_VALIDATED"
REQUIRED_FIELDS = {
    "shared_item_id",
    "source_item_id",
    "schema_version",
    "learning_unit_id",
    "grammar_unit_id",
    "official_cefr_level",
    "internal_stage",
    "skill",
    "item_role",
    "evidence_dimension",
    "task_type",
    "prompt_contract",
    "response_contract",
    "answer_contract",
    "scoring_contract",
    "media_contract",
    "content_binding",
    "source_trace",
    "readiness",
    "claim_boundaries",
}
TEXT_MODES = {
    "DETERMINISTIC_OPTION",
    "DETERMINISTIC_NORMALIZED_TEXT",
    "DETERMINISTIC_SEQUENCE",
    "FEATURE_RUBRIC_CANDIDATE",
}


def _false_fields(
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
    if set(schema.get("required", [])) != REQUIRED_FIELDS:
        errors.append("schema_required_fields_mismatch")
    policy = schema.get("x_policy", {})
    for field in (
        "canonical_graph_write_allowed",
        "listening_audio_may_be_claimed_ready_without_rendered_asset",
        "speaking_scoring_may_be_claimed_ready_without_capture_or_transcript",
        "learner_mastery_claim_allowed",
        "retention_claim_allowed",
        "persistent_learner_state_write_allowed",
        "a2_a2plus_progression_allowed",
    ):
        if policy.get(field) is not False:
            errors.append(f"schema_policy_not_false:{field}")

    items = artifact.get("shared_items", [])
    if len(items) != 384:
        errors.append("shared_item_count_not_384")
    shared_ids = [item.get("shared_item_id") for item in items]
    source_ids = [item.get("source_item_id") for item in items]
    if len(set(shared_ids)) != 384 or None in shared_ids:
        errors.append("shared_item_ids_not_unique_384")
    if len(set(source_ids)) != 384 or None in source_ids:
        errors.append("source_item_ids_not_unique_384")

    by_skill = {skill: [] for skill in SKILLS}
    by_unit: dict[str, list[str]] = {}
    source_index: dict[str, str] = {}
    rowless_unit_ids: set[str] = set()
    direct_unit_ids: set[str] = set()

    for item in items:
        item_id = str(item.get("shared_item_id"))
        prefix = f"item:{item_id}:"
        if set(item) != REQUIRED_FIELDS:
            errors.append(prefix + "top_level_fields_mismatch")
        if item.get("schema_version") != SCHEMA_VERSION:
            errors.append(prefix + "schema_version_mismatch")
        if item_id != f"E4S_A1V1_ITEM:{item.get('source_item_id')}":
            errors.append(prefix + "shared_item_id_mismatch")
        if item.get("official_cefr_level") != "A1":
            errors.append(prefix + "official_level_not_a1")
        if item.get("internal_stage") not in {"A1", "A1_PLUS"}:
            errors.append(prefix + "internal_stage_invalid")
        skill = item.get("skill")
        if skill not in SKILLS:
            errors.append(prefix + "skill_invalid")
            continue
        by_skill[skill].append(item_id)
        grammar_id = str(item.get("grammar_unit_id"))
        by_unit.setdefault(grammar_id, []).append(item_id)
        source_index[str(item.get("source_item_id"))] = item_id
        if item.get("learning_unit_id") != f"E4S_A1V1_UNIT:{grammar_id}":
            errors.append(prefix + "learning_unit_id_mismatch")
        if item.get("item_role") not in {"practice", "assessment"}:
            errors.append(prefix + "item_role_invalid")
        if not item.get("evidence_dimension") or not item.get("task_type"):
            errors.append(prefix + "dimension_or_task_type_missing")

        prompt = item.get("prompt_contract", {})
        if not prompt.get("prompt_text"):
            errors.append(prefix + "prompt_text_missing")
        if prompt.get("prompt_status") != "PROJECT_AUTHORED_CANDIDATE":
            errors.append(prefix + "prompt_status_invalid")
        response = item.get("response_contract", {})
        if not response.get("response_mode"):
            errors.append(prefix + "response_mode_missing")
        if response.get("learner_input_required") is not True:
            errors.append(prefix + "learner_input_not_required")

        answer = item.get("answer_contract", {})
        scoring = item.get("scoring_contract", {})
        media = item.get("media_contract", {})
        mode = answer.get("answer_mode")
        if answer.get("answer_status") != "CANDIDATE_CONTRACT_AVAILABLE":
            errors.append(prefix + "answer_status_invalid")
        if scoring.get("scoring_mode") != mode:
            errors.append(prefix + "answer_scoring_mode_mismatch")
        if not isinstance(scoring.get("required_evidence"), list):
            errors.append(prefix + "required_evidence_not_list")

        binding = item.get("content_binding", {})
        if binding.get("grammar_focus") != [grammar_id]:
            errors.append(prefix + "grammar_focus_mismatch")
        rows = binding.get("canonical_egp_row_ids", [])
        coverage_mode = binding.get("coverage_mode")
        if coverage_mode == "DIRECT_CANONICAL_ROWS":
            direct_unit_ids.add(grammar_id)
            if not rows:
                errors.append(prefix + "direct_item_missing_rows")
        elif coverage_mode == "ROWLESS_STRUCTURAL_PACKAGE_GATE":
            rowless_unit_ids.add(grammar_id)
            if rows:
                errors.append(prefix + "rowless_item_has_rows")
            if grammar_id != "GRAMMAR_DEMONSTRATIVES_CONTRAST":
                errors.append(prefix + "unexpected_rowless_unit")
        else:
            errors.append(prefix + "coverage_mode_invalid")

        trace = item.get("source_trace", {})
        if trace.get("raw_external_source_text_copied") is not False:
            errors.append(prefix + "raw_external_text_copy_claim")
        if not trace.get("source_artifact_id") or not trace.get("source_builder_path"):
            errors.append(prefix + "source_trace_incomplete")

        if skill in {"reading", "writing"}:
            if trace.get("source_kind") != "READING_WRITING_TEXT_MODE":
                errors.append(prefix + "text_source_kind_mismatch")
            if mode not in TEXT_MODES:
                errors.append(prefix + "text_answer_mode_invalid")
            if mode == "FEATURE_RUBRIC_CANDIDATE":
                if scoring.get("deterministic_candidate") is not False:
                    errors.append(prefix + "feature_item_false_deterministic")
                if scoring.get("human_review_fallback") is not True:
                    errors.append(prefix + "feature_item_missing_human_review")
            else:
                if scoring.get("deterministic_candidate") is not True:
                    errors.append(prefix + "deterministic_text_item_not_deterministic")
            expected_media = {
                "text_status": "AVAILABLE",
                "audio_required": False,
                "audio_status": "NOT_REQUIRED",
                "transcript_required": False,
                "transcript_status": "NOT_REQUIRED",
                "image_required": False,
                "image_status": "NOT_REQUIRED",
                "learner_capture_required": False,
                "learner_capture_status": "NOT_REQUIRED",
            }
            if media != expected_media:
                errors.append(prefix + "text_media_contract_mismatch")
        elif skill == "listening":
            if trace.get("source_kind") != "LISTENING_CANDIDATE":
                errors.append(prefix + "listening_source_kind_mismatch")
            if mode != "TRANSCRIPT_BACKED_CANDIDATE":
                errors.append(prefix + "listening_answer_mode_invalid")
            if scoring.get("deterministic_candidate") is not True:
                errors.append(prefix + "listening_transcript_candidate_not_deterministic")
            if scoring.get("real_skill_scoring_ready") is not False:
                errors.append(prefix + "listening_false_real_scoring_ready")
            if scoring.get("human_review_fallback") is not True:
                errors.append(prefix + "listening_human_review_fallback_missing")
            if media != {
                "text_status": "AVAILABLE",
                "audio_required": True,
                "audio_status": "NOT_RENDERED",
                "transcript_required": True,
                "transcript_status": "CANDIDATE_AVAILABLE",
                "image_required": False,
                "image_status": "NOT_REQUIRED",
                "learner_capture_required": False,
                "learner_capture_status": "NOT_REQUIRED",
            }:
                errors.append(prefix + "listening_media_contract_mismatch")
            if not answer.get("transcript_text"):
                errors.append(prefix + "listening_transcript_text_missing")
        elif skill == "speaking":
            if trace.get("source_kind") != "SPEAKING_CANDIDATE":
                errors.append(prefix + "speaking_source_kind_mismatch")
            if mode != "FEATURE_RUBRIC_CANDIDATE":
                errors.append(prefix + "speaking_answer_mode_invalid")
            if answer.get("exact_text_match_required") is not False:
                errors.append(prefix + "speaking_exact_match_forbidden")
            if scoring.get("deterministic_candidate") is not False:
                errors.append(prefix + "speaking_false_deterministic")
            if scoring.get("real_skill_scoring_ready") is not False:
                errors.append(prefix + "speaking_false_real_scoring_ready")
            if scoring.get("human_review_fallback") is not True:
                errors.append(prefix + "speaking_human_review_fallback_missing")
            if media != {
                "text_status": "MODEL_TEXT_AVAILABLE",
                "audio_required": True,
                "audio_status": "NOT_IMPLEMENTED",
                "transcript_required": True,
                "transcript_status": "NOT_COLLECTED",
                "image_required": False,
                "image_status": "NOT_REQUIRED",
                "learner_capture_required": True,
                "learner_capture_status": "NOT_IMPLEMENTED",
            }:
                errors.append(prefix + "speaking_media_contract_mismatch")
            if not answer.get("model_texts") or not answer.get("grammar_evidence_required"):
                errors.append(prefix + "speaking_feature_answer_incomplete")

        readiness = item.get("readiness", {})
        for field in (
            "shared_item_contract_complete",
            "answer_contract_complete",
            "scoring_contract_complete",
            "media_contract_complete",
        ):
            if readiness.get(field) is not True:
                errors.append(prefix + f"contract_readiness_missing:{field}")
        if readiness.get("real_skill_delivery_complete") is not False:
            errors.append(prefix + "false_real_skill_delivery_complete")
        if readiness.get("actual_learner_evidence_complete") is not False:
            errors.append(prefix + "false_actual_evidence_complete")
        _false_fields(
            errors,
            prefix,
            item.get("claim_boundaries", {}),
            (
                "contract_completion_is_real_skill_completion",
                "learner_mastery_claimed",
                "retention_confirmed",
                "persistent_learner_state_write",
                "production_runtime_event",
                "a2_a2plus_in_scope",
            ),
        )

    skill_counts = {skill: len(by_skill[skill]) for skill in SKILLS}
    if skill_counts != SOURCE_COUNTS:
        errors.append(f"skill_item_counts_mismatch:{skill_counts}")
    unit_counts = {unit_id: len(item_ids) for unit_id, item_ids in by_unit.items()}
    if len(unit_counts) != 24 or set(unit_counts.values()) != {16}:
        errors.append("unit_item_distribution_not_24x16")
    if len(direct_unit_ids) != 23 or rowless_unit_ids != {"GRAMMAR_DEMONSTRATIVES_CONTRAST"}:
        errors.append("coverage_unit_distribution_not_23_plus_1")
    if artifact.get("by_skill") != by_skill:
        errors.append("by_skill_index_mismatch")
    if artifact.get("by_grammar_unit_id") != by_unit:
        errors.append("by_grammar_unit_id_index_mismatch")
    if artifact.get("by_source_item_id") != source_index:
        errors.append("by_source_item_id_index_mismatch")

    summary = artifact.get("coverage_summary", {})
    expected_assessment = {skill: 24 for skill in SKILLS}
    expected_practice = {skill: 72 for skill in SKILLS}
    if summary.get("learning_unit_count") != 24:
        errors.append("summary_learning_unit_count_not_24")
    if summary.get("canonical_egp_row_count") != 109:
        errors.append("summary_canonical_row_count_not_109")
    if summary.get("direct_canonical_unit_count") != 23:
        errors.append("summary_direct_unit_count_not_23")
    if summary.get("rowless_structural_unit_count") != 1:
        errors.append("summary_rowless_unit_count_not_1")
    if summary.get("shared_item_count") != 384 or summary.get("items_per_unit") != 16:
        errors.append("summary_item_identity_mismatch")
    if summary.get("skill_item_counts") != SOURCE_COUNTS:
        errors.append("summary_skill_counts_mismatch")
    if summary.get("skill_practice_counts") != expected_practice:
        errors.append("summary_practice_counts_mismatch")
    if summary.get("skill_assessment_counts") != expected_assessment:
        errors.append("summary_assessment_counts_mismatch")
    for field in (
        "rendered_listening_audio_count",
        "captured_speaking_audio_count",
        "collected_speaking_transcript_count",
    ):
        if summary.get(field) != 0:
            errors.append(f"summary_false_media_count:{field}")

    boundaries = artifact.get("claim_boundaries", {})
    for field in (
        "m03_shared_item_contract_complete",
        "answer_scoring_contract_complete",
        "media_contract_complete",
    ):
        if boundaries.get(field) is not True:
            errors.append(f"artifact_completion_boundary_missing:{field}")
    _false_fields(
        errors,
        "artifact:",
        boundaries,
        (
            "reading_v1_complete",
            "writing_v1_complete",
            "listening_audio_assets_complete",
            "speaking_capture_complete",
            "real_learner_evidence_complete",
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
            "shared_item_count": len(items),
            "learning_unit_count": len(by_unit),
            "skill_item_counts": skill_counts,
            "direct_canonical_unit_count": len(direct_unit_ids),
            "rowless_structural_unit_count": len(rowless_unit_ids),
        },
        "claim_boundaries": {
            "shared_contract_validated": not errors,
            "real_four_skill_delivery_complete": False,
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
