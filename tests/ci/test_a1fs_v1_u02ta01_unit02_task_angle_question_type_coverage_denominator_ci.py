from ulga.builders import (
    build_a1fs_v1_u02ta01_unit02_task_angle_question_type_coverage_denominator
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02ta01_unit02_task_angle_question_type_coverage_denominator
    as validator,
)


def validated_payload():
    value = builder.payload()
    report = validator.validate_payload(value)
    assert report["error_count"] == 0
    return value, report


def test_u02ta01_resolves_exact_five_roles_and_ten_task_families():
    value, report = validated_payload()
    assert [row["task_role"] for row in value["pedagogical_task_role_denominator"]] == [
        "REVIEW",
        "NEW",
        "INTEGRATION",
        "VARIATION",
        "TRANSFER",
    ]
    assert [row["task_family"] for row in value["task_question_family_denominator"]] == [
        "RECOGNITION",
        "MEANING_DISCRIMINATION",
        "FORM_SELECTION",
        "MORPHOLOGY_CONSTRUCTION",
        "ERROR_DETECTION",
        "ERROR_CORRECTION",
        "CONTEXT_GAP",
        "U01_U02_INTEGRATION",
        "PRODUCTIVE_RESPONSE",
        "TRANSFER",
    ]
    assert report["task_role_count"] == 5
    assert report["task_family_count"] == 10


def test_u02ta01_reads_current_unit02_eight_items_and_six_exact_task_types():
    value, _ = validated_payload()
    evidence = value["current_unit02_question_type_evidence"]
    assert evidence["unit02_item_count"] == 8
    assert evidence["unique_task_type_count"] == 6
    assert evidence["task_types"] == [
        "context_choice",
        "form_choice",
        "guided_contextual_writing",
        "structured_gap_fill",
        "structured_morphology_build",
        "text_mode_writing_checkpoint",
    ]
    assert evidence["response_modes"] == [
        "ordered_morphemes",
        "select_one",
        "short_text",
    ]
    assert evidence["all_unit02_task_types_present_in_global_question_type_authority"] is True
    assert evidence["all_current_unit02_items_single_grammar_focus"] is True


def test_u02ta01_does_not_overclaim_proxy_error_or_context_gap_support():
    value, _ = validated_payload()
    rows = {row["task_family"]: row for row in value["task_question_family_denominator"]}
    assert rows["ERROR_DETECTION"]["coverage_status"] == "PARTIAL"
    assert rows["CONTEXT_GAP"]["coverage_status"] == "PARTIAL"
    assert rows["TRANSFER"]["coverage_status"] == "PARTIAL"
    assert rows["ERROR_CORRECTION"]["coverage_status"] == "GAP"
    assert rows["U01_U02_INTEGRATION"]["coverage_status"] == "GAP"


def test_u02ta01_preserves_review_reuse_but_requires_real_cross_unit_integration():
    value, _ = validated_payload()
    roles = {row["task_role"]: row for row in value["pedagogical_task_role_denominator"]}
    assert roles["REVIEW"]["coverage_status"] == "FULL"
    assert "ERROR_CHECK" in roles["REVIEW"]["evidence"]["reusable_generic_task_angles"]
    assert roles["NEW"]["coverage_status"] == "FULL"
    assert roles["INTEGRATION"]["coverage_status"] == "GAP"
    assert roles["VARIATION"]["coverage_status"] == "PARTIAL"
    assert roles["TRANSFER"]["coverage_status"] == "PARTIAL"


def test_u02ta01_reports_current_gap_inventory_for_q10_without_materializing_questions():
    value, _ = validated_payload()
    counts = value["coverage_denominators"]
    assert counts == {
        "task_role_count": 5,
        "task_role_full_count": 2,
        "task_role_partial_count": 2,
        "task_role_gap_count": 1,
        "task_family_count": 10,
        "task_family_full_count": 5,
        "task_family_partial_count": 3,
        "task_family_gap_count": 2,
        "task_family_gap_ids": ["ERROR_CORRECTION", "U01_U02_INTEGRATION"],
        "task_family_partial_ids": ["ERROR_DETECTION", "CONTEXT_GAP", "TRANSFER"],
        "current_unit02_item_count": 8,
        "current_unit02_unique_task_type_count": 6,
    }
    assert value["question9_contract"]["all_task_families_materialized"] is False
    assert value["question9_contract"]["gaps_must_feed_questionbank_gap_materialization"] is True
    assert value["question9_contract"]["distinct_capacity_not_claimed"] is True


def test_u02ta01_stops_before_q10_and_mutates_no_content_or_runtime():
    value, _ = validated_payload()
    assert value["claim_boundaries"] == {
        "canonical_graph_mutated": False,
        "questionbank_mutated": False,
        "new_question_items_authored": 0,
        "runtime_allocation_mutated": False,
        "learner_facing_content_created": False,
        "learner_state_joined": False,
        "distinct_item_capacity_claimed": False,
        "a2_unlocked": False,
    }
    assert value["next_scope"] == {
        "coverage_denominator_number": 10,
        "coverage_denominator": "QUESTIONBANK_DISTINCT_CAPACITY",
        "scope_status": "OUTSIDE_APPROVED_Q9_SCOPE",
    }
    assert value["next_short_step"] == (
        "A1FS-V1-U02QBC01_Unit02QuestionBankDistinctCapacityDenominator"
    )
