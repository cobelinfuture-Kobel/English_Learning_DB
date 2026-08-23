#!/usr/bin/env python3
"""Validate U02SA01 cumulative Sentence Asset coverage reconciliation."""
from __future__ import annotations

from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u02sa01_unit01_unit02_cumulative_sentence_asset_coverage_recheck
    as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U02SA01_CUMULATIVE_SENTENCE_ASSET_COVERAGE_RECHECK_VALIDATOR"


class U02SA01ValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise U02SA01ValidationError(code)


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    require(report.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(report.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(report.get("status") == builder.PASS_STATUS, "STATUS_INVALID")

    source = report.get("source_authority", {})
    require(
        source.get("unit01_sentence_pool_task_id") == builder.U01SA05R2_TASK_ID,
        "U01SA05R2_TASK_ID_INVALID",
    )
    require(
        source.get("unit01_sentence_pool_sha256")
        == builder.U01SA05R2_SENTENCE_POOL_SHA256,
        "U01SA05R2_SHA_INVALID",
    )
    require(
        source.get("unit01_deferred_candidate_sha256")
        == builder.U01SA04_DEFER_SHA256,
        "DEFER_SHA_INVALID",
    )

    counts = report.get("coverage_denominators", {})
    expected = {
        "unit01_base_sentence_assets": 3805,
        "unit02_inherited_usable": 3805,
        "unit02_recombinable_from_u01": 984,
        "unit02_genuinely_new_required": 4,
        "unit02_new_admitted": 0,
        "unit02_active_sentence_supply": 3805,
        "cumulative_distinct_sentence_assets": 3805,
    }
    require(counts == expected, f"DENOMINATOR_DRIFT:{counts}")

    contract = report.get("identity_vs_capacity_contract", {})
    require(
        contract.get("recombinable_is_subset_of_inherited") is True,
        "RECOMBINABLE_SUBSET_CONTRACT_INVALID",
    )
    require(
        contract.get("recombinable_must_not_be_added_to_identity_count") is True,
        "RECOMBINABLE_ADDITIVE_OVERCOUNT_RISK",
    )
    require(
        contract.get("transformed_output_is_not_admitted_until_sentence_asset_admission")
        is True,
        "TRANSFORMED_OUTPUT_ADMISSION_OVERCLAIM",
    )
    require(
        contract.get("genuinely_new_required_semantics")
        == "MINIMUM_DIRECT_NEW_CANONICAL_PATTERN_SENTENCE_WITNESS_FLOOR",
        "NEW_REQUIRED_SEMANTICS_INVALID",
    )

    replay = report.get("private_replay_readback", {})
    require(replay.get("sentence_pool_total") == 3805, "PRIVATE_POOL_COUNT_INVALID")
    require(
        replay.get("all_profiles_canonical_admission_status_admitted") is True,
        "PRIVATE_POOL_NOT_ALL_ADMITTED",
    )
    require(
        replay.get("unique_sentence_identity_count") == 3805,
        "PRIVATE_POOL_IDENTITY_COUNT_INVALID",
    )
    require(replay.get("resolved_np_slot_count") == 3897, "NP_SLOT_COUNT_INVALID")
    require(
        replay.get("direct_plain_s_plural_sentence_asset_count") == 0,
        "UNEXPECTED_DIRECT_PLURAL_ASSET",
    )
    require(
        replay.get("direct_unit02_new_pattern_sentence_asset_count") == 0,
        "UNEXPECTED_NEW_PATTERN_ASSET",
    )
    require(
        replay.get("recombinable_i_can_see_profile_count") == 930,
        "I_CAN_SEE_RECOMBINATION_COUNT_INVALID",
    )
    require(
        replay.get("recombinable_relation_object_profile_count") == 54,
        "RELATION_RECOMBINATION_COUNT_INVALID",
    )
    require(
        replay.get("recombinable_profile_count") == 984,
        "RECOMBINATION_COUNT_INVALID",
    )
    require(
        replay.get("recombinable_distinct_plain_s_noun_count") == 155,
        "RECOMBINABLE_NOUN_COUNT_INVALID",
    )
    require(
        replay.get("plain_s_noun_count_not_in_strict_recombination_seed") == 7,
        "STRICT_RECOMBINATION_NOUN_GAP_INVALID",
    )

    deferred = report.get("deferred_candidate_reuse", {})
    require(
        deferred.get("later_unit_candidate_count") == 296,
        "DEFERRED_COUNT_INVALID",
    )
    require(
        deferred.get("i_have_candidate_count") == 291,
        "DEFERRED_I_HAVE_COUNT_INVALID",
    )
    require(
        deferred.get("i_have_matching_u02_plain_s_noun_count") == 150,
        "DEFERRED_I_HAVE_U02_NOUN_COUNT_INVALID",
    )
    require(
        deferred.get("candidate_identity_is_not_admitted_sentence_asset") is True,
        "DEFERRED_CANDIDATE_ADMISSION_OVERCLAIM",
    )
    require(
        deferred.get("requires_unit02_semantic_validation_before_admission") is True,
        "DEFERRED_SEMANTIC_GATE_MISSING",
    )

    public = report.get("unit02_public_coverage_context", {})
    require(public.get("plain_s_noun_surface_count") == 162, "U02_NOUN_COUNT_INVALID")
    require(public.get("unit02_native_chunk_surface_count") == 26, "U02_CHUNK_COUNT_INVALID")
    require(public.get("unit02_new_canonical_pattern_count") == 4, "U02_PATTERN_COUNT_INVALID")
    require(
        public.get("unit02_new_patterns_bound_in_current_questionbank_count") == 0,
        "NEW_PATTERN_QB_BINDING_OVERCLAIM",
    )
    require(
        len(public.get("minimum_direct_sentence_witness_gap_pattern_ids", [])) == 4,
        "NEW_PATTERN_WITNESS_GAP_INVALID",
    )

    verdict = report.get("coverage_verdict", {})
    require(verdict.get("q6_denominators_reconciled") is True, "Q6_NOT_RECONCILED")
    require(
        verdict.get("current_concrete_sentence_asset_pool_is_still_unit01_3805")
        is True,
        "CURRENT_POOL_IDENTITY_INVALID",
    )
    require(
        verdict.get("unit02_direct_new_pattern_sentence_witness_gap_open") is True,
        "NEW_PATTERN_GAP_NOT_OPEN",
    )
    require(
        verdict.get("minimum_new_sentence_asset_witness_gap") == 4,
        "MINIMUM_NEW_WITNESS_GAP_INVALID",
    )
    require(
        verdict.get("unit02_sentence_asset_admission_complete") is False,
        "UNIT02_ADMISSION_OVERCLAIM",
    )
    require(
        verdict.get("no_duplicate_unit02_sentence_bank_required") is True,
        "DUPLICATE_SENTENCE_BANK_ALLOWED",
    )

    boundaries = report.get("claim_boundaries", {})
    for key in (
        "unit01_sentence_assets_mutated",
        "unit02_sentence_assets_created",
        "questionbank_mutated",
        "sentence_pattern_authority_mutated",
        "chunk_authority_mutated",
        "canonical_scene_authority_mutated",
        "runtime_connected",
        "learner_state_mutated",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")

    require(report.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_STEP_INVALID")
    return {
        "status": builder.PASS_STATUS,
        "validator_id": VALIDATOR_ID,
        "error_count": 0,
        "errors": [],
    }
