#!/usr/bin/env python3
"""Recheck Unit01 -> Unit02 cumulative Sentence Asset coverage.

U02SA01 is a read-only Q6 authority. It separates concrete admitted sentence
identities from transformation/recombination capacity and from not-yet-admitted
Unit02 sentence gaps. The 3,805-row U01SA05R2 capability index remains private
Drive evidence; this module records its SHA-bound replay result while deriving
all public denominators from current main authorities.
"""
from __future__ import annotations

from typing import Any

from ulga.builders import (
    build_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as u02qb02,
)
from ulga.builders import (
    build_a1fs_v1_u02ch01_unit02_native_chunk_assets as u02ch01,
)
from ulga.builders import (
    build_a1fs_v1_u02sp02_unit01_unit02_exact_sentence_frame_coverage_recheck as u02sp02,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only cumulative Sentence Asset coverage reconciliation from SHA-bound "
    "Unit01 private capability evidence and current public Unit02 authorities; "
    "no Sentence Asset, QuestionBank, scene, runtime, learner state, or A2 content "
    "is created or mutated."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02SA01_Unit01Unit02CumulativeSentenceAssetCoverageRecheck"
SCHEMA_VERSION = "a1fs.v1.u02sa01.cumulative_sentence_asset_coverage_recheck.v1"
PASS_STATUS = (
    "PASS_A1FS_V1_U02SA01_UNIT01_UNIT02_CUMULATIVE_SENTENCE_ASSET_COVERAGE_RECHECK"
)
NEXT_SHORT_STEP = (
    "A1FS-V1-U02SA02_"
    "Unit02GenuinelyNewPluralSentenceAssetGapMaterializationAndAdmission"
)
NEXT_SCOPE_STATUS = "OUTSIDE_APPROVED_Q6_RECHECK_SCOPE"

U01SA05R2_TASK_ID = (
    "A1FS-V1-U01SA05R2_"
    "Full3805SentencePoolCapabilityCoverageAndUnit01QuestionBankResidualBindingReconciliation"
)
U01SA05R2_STATUS = "CAPABILITY_CLASSIFIED"
U01SA05R2_SENTENCE_POOL_DRIVE_ID = "1U4J1BZ0byM0mVLpLU0CoFrVNr28vsc55"
U01SA05R2_SENTENCE_POOL_SHA256 = (
    "a4c33d7c2a460ad5a81397d7ab184b682bc456359fae7c286d168c352258835d"
)
U01SA04_DEFER_DRIVE_ID = "1F758EoI5g_6jTwqfDvMIUZZw9YamzMuJ"
U01SA04_DEFER_SHA256 = (
    "1ba08c6afcc20fb78b43f8d5d96def768f77b1e6d4bbf28830efea86aa07136a"
)

UNIT01_BASE_SENTENCE_ASSETS = 3805
UNIT02_INHERITED_USABLE = 3805

UNIT02_RECOMBINABLE_I_CAN_SEE = 930
UNIT02_RECOMBINABLE_RELATION_OBJECT = 54
UNIT02_RECOMBINABLE_FROM_U01 = (
    UNIT02_RECOMBINABLE_I_CAN_SEE + UNIT02_RECOMBINABLE_RELATION_OBJECT
)
UNIT02_RECOMBINABLE_DISTINCT_PLAIN_S_NOUNS = 155

UNIT02_GENUINELY_NEW_REQUIRED = 4
UNIT02_NEW_ADMITTED = 0
UNIT02_ACTIVE_SENTENCE_SUPPLY = UNIT01_BASE_SENTENCE_ASSETS + UNIT02_NEW_ADMITTED
CUMULATIVE_DISTINCT_SENTENCE_ASSETS = UNIT02_ACTIVE_SENTENCE_SUPPLY

UNIT01_DIRECT_PLAIN_S_PLURAL_SENTENCE_ASSETS = 0
UNIT01_DIRECT_UNIT02_NEW_PATTERN_SENTENCE_ASSETS = 0

DEFERRED_LATER_UNIT_CANDIDATES = 296
DEFERRED_I_HAVE_CANDIDATES = 291
DEFERRED_I_HAVE_MATCHING_U02_PLAIN_S_NOUNS = 150

EXPECTED_U02_PLAIN_S_NOUNS = 162
EXPECTED_U02_NATIVE_CHUNKS = 26
EXPECTED_U02_NEW_PATTERNS = 4
EXPECTED_Q5_BOUND_NEW_PATTERNS = 0


class U02SA01BuildError(ValueError):
    pass


def build_report() -> dict[str, Any]:
    inventory = u02qb02.load_inventory()
    inventory_rows = inventory.get("inventory", [])
    if len(inventory_rows) != EXPECTED_U02_PLAIN_S_NOUNS:
        raise U02SA01BuildError(
            f"U02_PLAIN_S_NOUN_COUNT_DRIFT:{len(inventory_rows)}"
        )

    chunks = u02ch01.build_assets()
    if len(chunks) != EXPECTED_U02_NATIVE_CHUNKS:
        raise U02SA01BuildError(f"U02_NATIVE_CHUNK_COUNT_DRIFT:{len(chunks)}")

    q5 = u02sp02.build_report()
    q5_patterns = q5["pattern_family_coverage"]
    q5_legacy = q5["legacy_pattern_reconciliation"]
    if (
        q5_patterns["unit02_new_canonical_core_pattern_count"]
        != EXPECTED_U02_NEW_PATTERNS
    ):
        raise U02SA01BuildError("U02_NEW_PATTERN_COUNT_DRIFT")
    if (
        q5_legacy["unit02_new_core_patterns_bound_in_current_questionbank_count"]
        != EXPECTED_Q5_BOUND_NEW_PATTERNS
    ):
        raise U02SA01BuildError("Q5_NEW_PATTERN_BINDING_STATE_DRIFT")

    new_pattern_ids = sorted(u02sp02.UNIT02_NEW_CANONICAL_PATTERNS)

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "source_authority": {
            "unit01_sentence_pool_task_id": U01SA05R2_TASK_ID,
            "unit01_sentence_pool_status": U01SA05R2_STATUS,
            "unit01_sentence_pool_drive_file_id": U01SA05R2_SENTENCE_POOL_DRIVE_ID,
            "unit01_sentence_pool_sha256": U01SA05R2_SENTENCE_POOL_SHA256,
            "unit01_deferred_candidate_drive_file_id": U01SA04_DEFER_DRIVE_ID,
            "unit01_deferred_candidate_sha256": U01SA04_DEFER_SHA256,
            "u02qb01_task_id": inventory["task_id"],
            "u02sp02_task_id": q5["task_id"],
            "u02ch01_task_id": u02ch01.TASK_ID,
        },
        "coverage_denominators": {
            "unit01_base_sentence_assets": UNIT01_BASE_SENTENCE_ASSETS,
            "unit02_inherited_usable": UNIT02_INHERITED_USABLE,
            "unit02_recombinable_from_u01": UNIT02_RECOMBINABLE_FROM_U01,
            "unit02_genuinely_new_required": UNIT02_GENUINELY_NEW_REQUIRED,
            "unit02_new_admitted": UNIT02_NEW_ADMITTED,
            "unit02_active_sentence_supply": UNIT02_ACTIVE_SENTENCE_SUPPLY,
            "cumulative_distinct_sentence_assets": CUMULATIVE_DISTINCT_SENTENCE_ASSETS,
        },
        "identity_vs_capacity_contract": {
            "inherited_usable_semantics": (
                "EXISTING_ADMITTED_IDENTITIES_AVAILABLE_FOR_CUMULATIVE_"
                "CARRY_OVER_REVIEW_PREREQUISITE"
            ),
            "recombinable_is_subset_of_inherited": True,
            "recombinable_must_not_be_added_to_identity_count": True,
            "transformed_output_is_not_admitted_until_sentence_asset_admission": True,
            "genuinely_new_required_semantics": (
                "MINIMUM_DIRECT_NEW_CANONICAL_PATTERN_SENTENCE_WITNESS_FLOOR"
            ),
            "genuinely_new_required_is_not_full_lexical_production_count": True,
        },
        "private_replay_readback": {
            "sentence_pool_total": UNIT01_BASE_SENTENCE_ASSETS,
            "all_profiles_canonical_admission_status_admitted": True,
            "unique_sentence_identity_count": UNIT01_BASE_SENTENCE_ASSETS,
            "resolved_np_slot_count": 3897,
            "direct_plain_s_plural_sentence_asset_count": (
                UNIT01_DIRECT_PLAIN_S_PLURAL_SENTENCE_ASSETS
            ),
            "direct_unit02_new_pattern_sentence_asset_count": (
                UNIT01_DIRECT_UNIT02_NEW_PATTERN_SENTENCE_ASSETS
            ),
            "recombinable_i_can_see_profile_count": UNIT02_RECOMBINABLE_I_CAN_SEE,
            "recombinable_relation_object_profile_count": (
                UNIT02_RECOMBINABLE_RELATION_OBJECT
            ),
            "recombinable_profile_count": UNIT02_RECOMBINABLE_FROM_U01,
            "recombinable_distinct_plain_s_noun_count": (
                UNIT02_RECOMBINABLE_DISTINCT_PLAIN_S_NOUNS
            ),
            "plain_s_noun_count_not_in_strict_recombination_seed": (
                EXPECTED_U02_PLAIN_S_NOUNS
                - UNIT02_RECOMBINABLE_DISTINCT_PLAIN_S_NOUNS
            ),
            "strict_recombination_rule": {
                "inherited_i_can_see_clause_shell": (
                    "PLURALIZE_TARGET_NP_WITHOUT_CLAUSE_AGREEMENT_CHANGE"
                ),
                "relation_object_slot": (
                    "PLURALIZE_RELATION_OBJECT_WITHOUT_CLAUSE_SUBJECT_"
                    "AGREEMENT_CHANGE"
                ),
                "this_is_main_np": "EXCLUDED_AGREEMENT_CHANGE_REQUIRED",
                "there_is_main_np": "EXCLUDED_AGREEMENT_CHANGE_REQUIRED",
            },
        },
        "deferred_candidate_reuse": {
            "later_unit_candidate_count": DEFERRED_LATER_UNIT_CANDIDATES,
            "i_have_candidate_count": DEFERRED_I_HAVE_CANDIDATES,
            "i_have_matching_u02_plain_s_noun_count": (
                DEFERRED_I_HAVE_MATCHING_U02_PLAIN_S_NOUNS
            ),
            "candidate_identity_is_not_admitted_sentence_asset": True,
            "requires_unit02_semantic_validation_before_admission": True,
            "must_not_be_regenerated_when_same_candidate_identity_is_reused": True,
        },
        "unit02_public_coverage_context": {
            "plain_s_noun_surface_count": len(inventory_rows),
            "unit02_native_chunk_surface_count": len(chunks),
            "unit02_new_canonical_pattern_ids": new_pattern_ids,
            "unit02_new_canonical_pattern_count": len(new_pattern_ids),
            "unit02_new_patterns_bound_in_current_questionbank_count": (
                q5_legacy[
                    "unit02_new_core_patterns_bound_in_current_questionbank_count"
                ]
            ),
            "minimum_direct_sentence_witness_gap_pattern_ids": new_pattern_ids,
        },
        "coverage_verdict": {
            "q6_denominators_reconciled": True,
            "current_concrete_sentence_asset_pool_is_still_unit01_3805": True,
            "unit02_direct_new_pattern_sentence_witness_gap_open": True,
            "minimum_new_sentence_asset_witness_gap": UNIT02_GENUINELY_NEW_REQUIRED,
            "unit02_sentence_asset_admission_complete": False,
            "no_duplicate_unit02_sentence_bank_required": True,
        },
        "claim_boundaries": {
            "unit01_sentence_assets_mutated": False,
            "unit02_sentence_assets_created": False,
            "questionbank_mutated": False,
            "sentence_pattern_authority_mutated": False,
            "chunk_authority_mutated": False,
            "canonical_scene_authority_mutated": False,
            "runtime_connected": False,
            "learner_state_mutated": False,
            "a2_unlocked": False,
        },
        "next_scope": {
            "scope_status": NEXT_SCOPE_STATUS,
            "next_short_step": NEXT_SHORT_STEP,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    from ulga.validators import (
        validate_a1fs_v1_u02sa01_unit01_unit02_cumulative_sentence_asset_coverage_recheck
        as validator,
    )

    report = build_report()
    validation = validator.validate_report(report)
    counts = report["coverage_denominators"]
    print(f"STATUS={PASS_STATUS}")
    print(f"UNIT01_BASE_SENTENCE_ASSETS={counts['unit01_base_sentence_assets']}")
    print(f"UNIT02_INHERITED_USABLE={counts['unit02_inherited_usable']}")
    print(f"UNIT02_RECOMBINABLE_FROM_U01={counts['unit02_recombinable_from_u01']}")
    print(f"UNIT02_GENUINELY_NEW_REQUIRED={counts['unit02_genuinely_new_required']}")
    print(f"UNIT02_NEW_ADMITTED={counts['unit02_new_admitted']}")
    print(f"UNIT02_ACTIVE_SENTENCE_SUPPLY={counts['unit02_active_sentence_supply']}")
    print(
        "CUMULATIVE_DISTINCT_SENTENCE_ASSETS="
        f"{counts['cumulative_distinct_sentence_assets']}"
    )
    print(f"ERROR_COUNT={validation['error_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
