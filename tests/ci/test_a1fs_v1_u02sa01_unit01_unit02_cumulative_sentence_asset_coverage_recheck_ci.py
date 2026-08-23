from ulga.builders import (
    build_a1fs_v1_u02sa01_unit01_unit02_cumulative_sentence_asset_coverage_recheck
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02sa01_unit01_unit02_cumulative_sentence_asset_coverage_recheck
    as validator,
)


def report():
    value = builder.build_report()
    result = validator.validate_report(value)
    assert result["error_count"] == 0
    return value


def test_u02sa01_closes_exact_current_sentence_asset_denominators_without_double_counting():
    counts = report()["coverage_denominators"]
    assert counts == {
        "unit01_base_sentence_assets": 3805,
        "unit02_inherited_usable": 3805,
        "unit02_recombinable_from_u01": 984,
        "unit02_genuinely_new_required": 4,
        "unit02_new_admitted": 0,
        "unit02_active_sentence_supply": 3805,
        "cumulative_distinct_sentence_assets": 3805,
    }


def test_u02sa01_keeps_recombination_capacity_as_subset_not_new_sentence_identity():
    value = report()
    replay = value["private_replay_readback"]
    contract = value["identity_vs_capacity_contract"]
    assert replay["recombinable_i_can_see_profile_count"] == 930
    assert replay["recombinable_relation_object_profile_count"] == 54
    assert replay["recombinable_profile_count"] == 984
    assert replay["recombinable_distinct_plain_s_noun_count"] == 155
    assert replay["plain_s_noun_count_not_in_strict_recombination_seed"] == 7
    assert contract["recombinable_is_subset_of_inherited"] is True
    assert contract["recombinable_must_not_be_added_to_identity_count"] is True
    assert contract["transformed_output_is_not_admitted_until_sentence_asset_admission"] is True


def test_u02sa01_exposes_four_new_pattern_witness_gap_without_inflating_lexical_production_count():
    value = report()
    public = value["unit02_public_coverage_context"]
    verdict = value["coverage_verdict"]
    assert public["plain_s_noun_surface_count"] == 162
    assert public["unit02_native_chunk_surface_count"] == 26
    assert public["unit02_new_canonical_pattern_count"] == 4
    assert public["unit02_new_patterns_bound_in_current_questionbank_count"] == 0
    assert len(public["minimum_direct_sentence_witness_gap_pattern_ids"]) == 4
    assert verdict["minimum_new_sentence_asset_witness_gap"] == 4
    assert verdict["unit02_sentence_asset_admission_complete"] is False


def test_u02sa01_preserves_later_unit_deferred_candidates_as_candidates_not_admitted_assets():
    deferred = report()["deferred_candidate_reuse"]
    assert deferred["later_unit_candidate_count"] == 296
    assert deferred["i_have_candidate_count"] == 291
    assert deferred["i_have_matching_u02_plain_s_noun_count"] == 150
    assert deferred["candidate_identity_is_not_admitted_sentence_asset"] is True
    assert deferred["requires_unit02_semantic_validation_before_admission"] is True


def test_u02sa01_is_read_only_and_stops_before_sentence_admission_runtime_and_a2():
    value = report()
    assert value["coverage_verdict"]["q6_denominators_reconciled"] is True
    assert value["coverage_verdict"]["no_duplicate_unit02_sentence_bank_required"] is True
    assert all(flag is False for flag in value["claim_boundaries"].values())
    assert value["next_scope"] == {
        "scope_status": "OUTSIDE_APPROVED_Q6_RECHECK_SCOPE",
        "next_short_step": (
            "A1FS-V1-U02SA02_"
            "Unit02GenuinelyNewPluralSentenceAssetGapMaterializationAndAdmission"
        ),
    }
