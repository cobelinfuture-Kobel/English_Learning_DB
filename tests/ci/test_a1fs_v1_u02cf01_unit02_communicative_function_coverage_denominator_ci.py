from ulga.builders import (
    build_a1fs_v1_u02cf01_unit02_communicative_function_coverage_denominator
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02cf01_unit02_communicative_function_coverage_denominator
    as validator,
)


def validated_payload():
    value = builder.payload()
    report = validator.validate_payload(value)
    assert report["error_count"] == 0
    return value, report


def test_u02cf01_uses_exact_three_family_unit02_scope_without_global_cf_registry():
    value, report = validated_payload()
    rows = value["communicative_function_denominator"]

    assert [row["function_family"] for row in rows] == [
        "IDENTIFY",
        "DESCRIBE",
        "QUANTITY_PLURALITY",
    ]
    assert report["function_family_count"] == 3
    assert value["source_authority"][
        "global_communicative_function_authority_present"
    ] is False
    assert value["taxonomy_boundaries"]["global_canonical_cf_registry_created"] is False


def test_u02cf01_reuses_identify_and_describe_from_all_current_unit01_scenes():
    value, _ = validated_payload()
    rows = {
        row["function_family"]: row
        for row in value["communicative_function_denominator"]
    }

    for family in ("IDENTIFY", "DESCRIBE"):
        row = rows[family]
        assert row["coverage_role"] == "REUSE"
        assert row["coverage_status"] == "COVERED_BY_EXISTING_UNIT01_SCENE_FUNCTION"
        assert row["evidence"]["covered_scene_count"] == 32
        assert len(row["evidence"]["covered_scene_refs"]) == 32
        assert len(set(row["evidence"]["covered_scene_refs"])) == 32


def test_u02cf01_adds_quantity_plurality_from_approved_plural_meaning_and_q7_support():
    value, _ = validated_payload()
    row = next(
        row
        for row in value["communicative_function_denominator"]
        if row["function_family"] == "QUANTITY_PLURALITY"
    )
    evidence = row["evidence"]

    assert row["coverage_role"] == "ADD"
    assert (
        evidence["approved_meaning_function"]
        == "refer to more than one countable person, animal, place, or thing"
    )
    assert evidence["operator_approval_status"] == "APPROVED_TEXT_MODE"
    assert evidence["q7_unit02_vocabulary_surface_count"] == 162
    assert evidence["q7_existing_scene_reuse_target_count"] == 26
    assert evidence["q7_new_structural_scene_candidate_count"] == 109
    assert evidence["q7_gated_non_scene_count"] == 27
    assert evidence["q7_remaining_direct_scene_gap_count"] == 0
    assert evidence[
        "all_new_structural_scene_candidates_support_plural_contrast"
    ] is True
    assert evidence[
        "structural_scene_support_is_not_learner_facing_scene_authority"
    ] is True


def test_u02cf01_closes_q8_three_of_three_without_promoting_pattern_affordances():
    value, _ = validated_payload()
    counts = value["coverage_denominators"]

    assert counts == {
        "communicative_function_family_count": 3,
        "reuse_function_family_count": 2,
        "unit02_added_function_family_count": 1,
        "covered_function_family_count": 3,
        "missing_function_family_count": 0,
        "missing_function_families": [],
    }
    assert value["taxonomy_boundaries"][
        "unit02sc01_pattern_affordances_not_promoted_to_cf_denominator"
    ] == list(builder.u02sc01.PATTERN_ELIGIBILITY_KEYS)
    assert value["question8_communicative_function_coverage_contract"][
        "q8_communicative_function_denominator_resolved"
    ] is True


def test_u02cf01_preserves_scope_and_stops_before_q9_task_angle_question_type():
    value, _ = validated_payload()

    assert value["claim_boundaries"] == {
        "canonical_graph_mutated": False,
        "global_communicative_function_authority_created": False,
        "unit01_scene_authority_mutated": False,
        "unit02_q7_authority_mutated": False,
        "unit02_vocabulary_authority_mutated": False,
        "learner_facing_content_created": False,
        "questionbank_mutated": False,
        "learner_runtime_connected": False,
        "a2_unlocked": False,
    }
    assert value["next_scope"] == {
        "coverage_denominator_number": 9,
        "coverage_denominator": "TASK_ANGLE_QUESTION_TYPE",
        "scope_status": "OUTSIDE_APPROVED_Q8_SCOPE",
    }
    assert (
        value["next_short_step"]
        == "A1FS-V1-U02TA01_Unit02TaskAngleQuestionTypeCoverageDenominator"
    )
