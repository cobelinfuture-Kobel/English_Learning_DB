from functools import lru_cache

from ulga.builders import (
    build_a1fs_v1_u02qbc02_unit02_questionbank_gap_materialization_and_per_slot_distinct_capacity_proof
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02qbc02_unit02_questionbank_gap_materialization_and_per_slot_distinct_capacity_proof
    as validator,
)


@lru_cache(maxsize=1)
def approved_payload():
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["validation_status"] == "PASS"
    assert report["error_count"] == 0
    return approved["payload"], report


def test_u02qbc02_materializes_exact_gap_only_inventory_without_parallel_bank():
    value, report = approved_payload()
    inventory = value["questionbank_inventory"]
    assert inventory["unit01_reusable_runtime_items"] == 474
    assert inventory["unit02_existing_approved_items"] == 658
    assert inventory["unit02_new_gap_materialized_items"] == 336
    assert inventory["unit02_approved_items_after_qbc02"] == 994
    assert inventory["cumulative_approved_items_after_qbc02"] == 1468
    assert inventory["parallel_questionbank_created"] is False
    assert report["new_item_count"] == 336


def test_u02qbc02_materializes_seven_questionbank_capacity_families_at_48_each():
    value, _ = approved_payload()
    assert value["materialization_contract"]["materialized_task_families"] == list(
        builder.MATERIALIZED_TASK_FAMILIES
    )
    counts = {}
    for row in value["new_approved_items"]:
        counts[row["task_family"]] = counts.get(row["task_family"], 0) + 1
    assert counts == {family: 48 for family in builder.MATERIALIZED_TASK_FAMILIES}
    assert all(row["canonical_scene_ref_id"] is None for row in value["new_approved_items"])
    assert all(row["scene_authority_claimed"] is False for row in value["new_approved_items"])


def test_u02qbc02_closes_hard_partial_and_practice_only_questionbank_capacity_gaps():
    value, _ = approved_payload()
    verdict = value["capacity_verdict"]
    assert verdict["q9_hard_gaps_materialized"] is True
    assert verdict["q9_partial_families_reconciled"] is True
    assert verdict["practice_only_full_families_reconciled_into_questionbank_capacity"] == [
        "MEANING_DISCRIMINATION",
        "PRODUCTIVE_RESPONSE",
    ]
    assert set(value["task_family_pools"]) == set(builder.TASK_FAMILIES)
    assert min(value["task_family_pool_counts"].values()) >= 48


def test_u02qbc02_proves_exact_16x4x10_640_slot_matrix_and_1920_bindings():
    value, report = approved_payload()
    model = value["capacity_model"]
    assert model == {
        "form_count": 16,
        "scene_slots_per_form": 4,
        "task_family_count": 10,
        "activities_per_form": 40,
        "total_capacity_slots": 640,
        "minimum_candidates_per_slot": 3,
        "slot_candidate_binding_count": 1920,
        "all_ten_task_families_have_at_least_48_candidates": True,
    }
    assert len(value["capacity_slot_matrix"]) == 640
    assert report["capacity_slots"] == 640
    assert report["slot_candidate_bindings"] == 1920


def test_u02qbc02_proves_three_distinct_candidates_per_slot_and_no_within_form_family_reuse():
    value, _ = approved_payload()
    matrix = value["capacity_slot_matrix"]
    for row in matrix:
        assert len(row["candidate_ids"]) == 3
        assert len(set(row["candidate_ids"])) == 3
        assert row["learner_visible_distinct_candidates"] is True
        assert row["canonical_scene_bound"] is False
        assert row["runtime_selection_materialized"] is False
    for form_number in range(1, 17):
        for family in builder.TASK_FAMILIES:
            ids = [
                cid
                for row in matrix
                if row["form_number"] == form_number and row["task_family"] == family
                for cid in row["candidate_ids"]
            ]
            assert len(ids) == 12
            assert len(set(ids)) == 12


def test_u02qbc02_closes_distinct_capacity_but_stops_before_runtime_and_final_forms():
    value, _ = approved_payload()
    assert value["capacity_verdict"]["distinct_capacity_status"] == "PROVEN"
    assert value["capacity_verdict"]["unit02_640_slot_capacity_closed"] is True
    assert value["claim_boundaries"] == {
        "unit01_questionbank_mutated": False,
        "parallel_questionbank_created": False,
        "unit02_runtime_connected": False,
        "final_forms_materialized": False,
        "learner_sessions_materialized": False,
        "canonical_scene_authority_mutated": False,
        "learner_state_mutated": False,
        "a2_unlocked": False,
    }
    assert value["next_scope"] == {
        "scope_status": "OUTSIDE_APPROVED_QBC02_SCOPE",
        "next_short_step": "A1FS-V1-U02QB03_Unit02CumulativeQuestionBankRuntimeIntegration",
        "requires_runtime_integration": True,
    }
