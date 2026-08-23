from ulga.builders import (
    build_a1fs_v1_u02qbc01_unit02_questionbank_distinct_capacity_denominator
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02qbc01_unit02_questionbank_distinct_capacity_denominator
    as validator,
)


def validated_payload():
    value = builder.payload()
    report = validator.validate_payload(value)
    assert report["error_count"] == 0
    assert report["validation_status"] == "PASS"
    return value, report


def test_u02qbc01_uses_unit02_16x40_640_capacity_target_not_unit01_12x20():
    value, report = validated_payload()
    target = value["unit02_capacity_target"]
    assert target["form_count_target"] == 16
    assert target["activities_per_form_target"] == 40
    assert target["total_activity_capacity_target"] == 640
    assert target["unit01_12_forms_240_activities_inherited_as_unit02_target"] is False
    assert target["minimum_legal_candidates_per_slot"] == 3
    assert target["minimum_slot_candidate_binding_capacity"] == 1920
    assert report["total_activity_capacity_target"] == 640


def test_u02qbc01_reconciles_474_reuse_plus_658_approved_without_false_runtime_claim():
    value, report = validated_payload()
    evidence = value["inventory_evidence"]
    assert evidence["unit01_reusable_runtime_item_count"] == 474
    assert evidence["unit02_approved_item_count"] == 658
    assert evidence["projected_cumulative_approved_item_count"] == 1132
    assert evidence["current_runtime_connected_unit02_item_count"] == 0
    assert evidence["current_runtime_cumulative_item_count"] == 474
    assert evidence["unit02_runtime_status"] == "NOT_CONNECTED"
    assert evidence["unit02_approved_item_ids_unique"] is True
    assert evidence["unit02_approved_semantic_signatures_unique"] is True
    assert report["projected_cumulative_approved_items"] == 1132


def test_u02qbc01_consumes_q9_ten_family_denominator_and_preserves_exact_gaps():
    value, report = validated_payload()
    q9 = value["q9_task_family_evidence"]
    assert q9 == {
        "source_task_id": builder.u02ta01.TASK_ID,
        "task_role_count": 5,
        "task_family_count": 10,
        "task_family_full_count": 5,
        "task_family_partial_count": 3,
        "task_family_gap_count": 2,
        "task_family_gap_ids": ["ERROR_CORRECTION", "U01_U02_INTEGRATION"],
        "task_family_partial_ids": ["ERROR_DETECTION", "CONTEXT_GAP", "TRANSFER"],
    }
    assert report["task_family_count"] == 10
    assert report["hard_task_family_gap_count"] == 2


def test_u02qbc01_does_not_equate_1132_aggregate_items_with_distinct_capacity_pass():
    value, _ = validated_payload()
    aggregate = value["aggregate_capacity_readback"]
    verdict = value["capacity_verdict"]
    assert aggregate["projected_cumulative_approved_items"] == 1132
    assert aggregate["aggregate_inventory_exceeds_activity_slot_count"] is True
    assert aggregate["aggregate_inventory_alone_proves_distinct_capacity"] is False
    assert aggregate["exact_slot_candidate_matrix_materialized"] is False
    assert aggregate["learner_visible_distinctness_proven_for_unit02_640_slot_model"] is False
    assert verdict["denominator_resolved"] is True
    assert verdict["distinct_capacity_status"] == "NOT_PROVEN"
    assert verdict["unit02_640_slot_capacity_closed"] is False


def test_u02qbc01_marks_hard_partial_and_unproven_per_family_capacity():
    value, _ = validated_payload()
    rows = {row["task_family"]: row for row in value["task_family_capacity_rows"]}
    assert rows["ERROR_CORRECTION"]["capacity_status"] == "HARD_GAP"
    assert rows["U01_U02_INTEGRATION"]["capacity_status"] == "HARD_GAP"
    for family in ["ERROR_DETECTION", "CONTEXT_GAP", "TRANSFER"]:
        assert rows[family]["capacity_status"] == "NOT_PROVEN"
    for row in rows.values():
        assert row["minimum_legal_candidates_per_slot"] == 3
        assert row["exact_eligible_item_count_by_slot_known"] is False
        assert row["learner_visible_distinctness_proven"] is False


def test_u02qbc01_is_read_only_and_stops_before_content_materialization():
    value, _ = validated_payload()
    assert value["claim_boundaries"] == {
        "unit01_questionbank_mutated": False,
        "unit02_questionbank_items_authored": 0,
        "unit02_runtime_connected": False,
        "parallel_questionbank_created": False,
        "forms_materialized": False,
        "activities_materialized": False,
        "slot_candidate_matrix_materialized": False,
        "learner_facing_content_created": False,
        "canonical_graph_mutated": False,
        "learner_state_mutated": False,
        "a2_unlocked": False,
    }
    assert value["next_scope"] == {
        "scope_status": "OUTSIDE_APPROVED_Q10_DENOMINATOR_SCOPE",
        "next_short_step": (
            "A1FS-V1-U02QBC02_"
            "Unit02QuestionBankGapMaterializationAndPerSlotDistinctCapacityProof"
        ),
        "requires_content_materialization": True,
    }
