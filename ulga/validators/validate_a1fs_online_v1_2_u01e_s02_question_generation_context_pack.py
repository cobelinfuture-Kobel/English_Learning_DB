#!/usr/bin/env python3
"""Validate Unit 01 safe and private question-generation context packs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s02_question_generation_context_pack as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_ONLINE_V1_2_U01E_S02_QUESTION_GENERATION_CONTEXT_PACK_VALIDATOR"


class S02ValidationError(ValueError):
    """Fail-closed S02 context-pack validation error."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise S02ValidationError(code)


def verify_pack_digest(pack: Mapping[str, Any], code: str) -> None:
    actual = pack.get("pack_sha256")
    require(isinstance(actual, str) and len(actual) == 64, f"{code}_digest_invalid")
    core = {key: value for key, value in pack.items() if key != "pack_sha256"}
    require(actual == builder.digest(core), f"{code}_digest_mismatch")


def validate_safe_pack(
    safe_pack: Mapping[str, Any], approved: Mapping[str, Any], safe_prompt: str
) -> None:
    verify_pack_digest(safe_pack, "safe_pack")
    policy_artifact.verify_artifact_digest(approved)
    require(approved.get("artifact_role") == policy_artifact.APPROVED_ROLE, "approved_role_invalid")
    require(safe_pack.get("task_id") == builder.TASK_ID, "safe_task_invalid")
    require(safe_pack.get("validation_status") == builder.PASS_STATUS, "safe_status_invalid")
    require(safe_pack.get("pack_role") == builder.SAFE_PACK_ROLE, "safe_role_invalid")
    require(safe_pack.get("private") is False, "safe_private_flag_invalid")
    require(
        safe_pack.get("source_identity", {}).get("s01_approved_sha256")
        == approved.get("artifact_sha256"),
        "safe_s01_binding_invalid",
    )
    require(
        safe_pack.get("source_identity", {}).get("s01_decision_ref")
        == builder.s01.DECISION_REF,
        "safe_s01_decision_invalid",
    )
    payload = approved.get("payload", {})
    require(
        safe_pack.get("approved_language_targets") == payload.get("language_targets"),
        "safe_language_target_drift",
    )
    require(
        safe_pack.get("target_inventory") == builder.target_inventory(payload),
        "safe_target_inventory_invalid",
    )
    assets = safe_pack.get("existing_asset_target_index")
    require(isinstance(assets, list) and len(assets) == builder.EXISTING_ACTIVITY_COUNT, "safe_asset_count_invalid")
    signatures = safe_pack.get("existing_semantic_signatures")
    require(isinstance(signatures, list) and len(signatures) == builder.EXISTING_ACTIVITY_COUNT, "safe_signature_count_invalid")
    require(len(set(signatures)) == len(signatures), "safe_signature_duplicate")
    require(
        signatures == sorted(row.get("semantic_signature") for row in assets),
        "safe_signature_binding_invalid",
    )

    policy = safe_pack.get("generation_policy", {})
    require(policy.get("generation_mode") == "OFFLINE_CANDIDATE_ONLY", "generation_mode_invalid")
    require(policy.get("existing_activity_count") == builder.EXISTING_ACTIVITY_COUNT, "existing_activity_count_invalid")
    require(policy.get("target_total_activity_count") == builder.TARGET_TOTAL_ACTIVITY_COUNT, "target_activity_count_invalid")
    require(policy.get("requested_new_candidate_count") == builder.NEW_CANDIDATE_TARGET_COUNT, "new_candidate_count_invalid")
    require(policy.get("skill_distribution") == builder.NEW_SKILL_DISTRIBUTION, "skill_distribution_invalid")
    require(policy.get("context_distribution") == builder.NEW_CONTEXT_DISTRIBUTION, "context_distribution_invalid")
    require(policy.get("question_type_distribution") == builder.NEW_QUESTION_TYPE_DISTRIBUTION, "question_type_distribution_invalid")
    require(policy.get("learning_role_distribution") == builder.LEARNING_ROLE_DISTRIBUTION, "learning_role_distribution_invalid")
    require(policy.get("support_level_distribution") == builder.SUPPORT_LEVEL_DISTRIBUTION, "support_level_distribution_invalid")
    randomization = policy.get("randomization_policy", {})
    require(randomization.get("approved_item_selection_allowed") is True, "approved_selection_invalid")
    require(randomization.get("free_runtime_generation_allowed") is False, "free_runtime_generation_allowed")
    require(randomization.get("unvalidated_variant_delivery_allowed") is False, "unvalidated_variant_delivery_allowed")

    output = safe_pack.get("output_contract", {})
    require(output.get("candidate_only") is True, "candidate_only_invalid")
    require(output.get("canonical_write_allowed") is False, "canonical_write_allowed")
    require(output.get("learner_delivery_allowed") is False, "learner_delivery_allowed")
    require(
        output.get("required_item_fields") == builder.REQUIRED_CANDIDATE_OUTPUT_FIELDS,
        "required_output_fields_invalid",
    )
    gaps = safe_pack.get("authority_gaps", {})
    require(
        gaps.get("ket_activity_bridge_status")
        == "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE",
        "ket_gap_invalid",
    )
    require(
        gaps.get("cambridge_granular_capability_status")
        == "UNRESOLVED_COMMITTED_DENOMINATOR_NOT_AVAILABLE",
        "cambridge_gap_invalid",
    )
    require(gaps.get("flyers_or_a2_blocked") is True, "flyers_a2_block_invalid")

    encoded = json.dumps(safe_pack, ensure_ascii=False).casefold()
    for forbidden in (
        '"learner_id"',
        '"attempt_id"',
        '"outcome_counts"',
        '"response_json"',
        '"accepted_texts"',
        '"accepted_sequence"',
        '"correct_answer"',
        '"candidate_items"',
    ):
        require(forbidden not in encoded, f"safe_private_or_generated_content_leak:{forbidden}")
    boundaries = safe_pack.get("claim_boundaries", {})
    require(boundaries.get("learner_private_data_included") is False, "safe_learner_private_boundary_invalid")
    require(boundaries.get("generated_questions_included") is False, "safe_generated_question_boundary_invalid")
    require(boundaries.get("canonical_write_allowed") is False, "safe_canonical_write_boundary_invalid")
    require(safe_prompt == builder.render_prompt(safe_pack), "safe_prompt_not_deterministic")
    require(f"CONTEXT_PACK_SHA256={safe_pack['pack_sha256']}" in safe_prompt, "safe_prompt_digest_missing")
    require("Return exactly one JSON object" in safe_prompt, "safe_prompt_output_instruction_missing")


def validate_private_pack(
    *,
    private_pack: Mapping[str, Any],
    safe_pack: Mapping[str, Any],
    database_path: Path,
    private_prompt: str,
) -> None:
    verify_pack_digest(private_pack, "private_pack")
    require(private_pack.get("task_id") == builder.TASK_ID, "private_task_invalid")
    require(private_pack.get("validation_status") == builder.PASS_STATUS, "private_status_invalid")
    require(private_pack.get("pack_role") == builder.PRIVATE_PACK_ROLE, "private_role_invalid")
    require(private_pack.get("private") is True, "private_flag_invalid")
    learner_id = str(private_pack.get("learner_id") or "")
    require(bool(learner_id), "private_learner_id_missing")
    require(
        private_pack.get("source_identity", {}).get("safe_pack_sha256")
        == safe_pack.get("pack_sha256"),
        "private_safe_pack_binding_invalid",
    )
    require(
        private_pack.get("source_identity", {}).get("learner_database_sha256")
        == builder.file_digest(database_path),
        "private_database_binding_invalid",
    )
    require(
        private_pack.get("safe_authoring_context") == safe_pack,
        "private_embedded_safe_context_drift",
    )
    expected = builder.build_private_pack(
        safe_pack=safe_pack,
        database_path=database_path,
        learner_id=learner_id,
    )
    require(private_pack == expected, "private_pack_not_reproducible")
    summary = private_pack.get("learner_attempt_summary", {})
    require(isinstance(summary.get("attempt_count"), int), "private_attempt_count_invalid")
    require(isinstance(summary.get("outcome_counts"), Mapping), "private_outcome_counts_invalid")
    state = private_pack.get("learner_target_state", {})
    require(
        state.get("stable_status") == "NOT_AVAILABLE_FROM_CURRENT_EVIDENCE",
        "private_stable_overclaim",
    )
    require(
        state.get("mastery_status") == "NOT_AVAILABLE_FROM_CURRENT_EVIDENCE",
        "private_mastery_overclaim",
    )
    require(state.get("stable_target_ids") == {}, "private_stable_targets_overclaim")
    require(state.get("mastered_target_ids") == {}, "private_mastered_targets_overclaim")
    boundaries = private_pack.get("claim_boundaries", {})
    for key in (
        "raw_responses_included",
        "hidden_answers_included",
        "attempt_ids_included",
        "learner_state_written",
        "mastery_inferred",
        "generated_questions_included",
        "canonical_write_allowed",
        "runtime_generation_allowed",
        "unit02_modified",
        "audio_enabled",
        "speaking_capture_enabled",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"private_boundary_invalid:{key}")
    encoded = json.dumps(private_pack, ensure_ascii=False).casefold()
    for forbidden in (
        '"attempt_id"',
        '"response_json"',
        '"accepted_texts"',
        '"accepted_sequence"',
        '"correct_answer"',
        '"candidate_items"',
    ):
        require(forbidden not in encoded, f"private_answer_response_or_generated_leak:{forbidden}")
    require(private_prompt == builder.render_prompt(private_pack), "private_prompt_not_deterministic")
    require(f"CONTEXT_PACK_SHA256={private_pack['pack_sha256']}" in private_prompt, "private_prompt_digest_missing")


def validate_packs(
    *,
    safe_pack: Mapping[str, Any],
    private_pack: Mapping[str, Any],
    approved: Mapping[str, Any],
    database_path: Path,
    safe_prompt: str,
    private_prompt: str,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_safe_pack(safe_pack, approved, safe_prompt)
        validate_private_pack(
            private_pack=private_pack,
            safe_pack=safe_pack,
            database_path=database_path,
            private_prompt=private_prompt,
        )
    except (
        S02ValidationError,
        builder.S02ContextPackError,
        policy_artifact.ContentPolicyBuildError,
        OSError,
        sqlite3.Error,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    return {
        "validator_id": VALIDATOR_ID,
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "safe_pack_sha256": safe_pack.get("pack_sha256"),
        "private_pack_sha256": private_pack.get("pack_sha256"),
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else builder.TASK_ID,
    }
