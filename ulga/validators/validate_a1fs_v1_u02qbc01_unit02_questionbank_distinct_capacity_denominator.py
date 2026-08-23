#!/usr/bin/env python3
"""Validate the Unit02 QuestionBank distinct-capacity denominator."""
from __future__ import annotations

from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u02qbc01_unit02_questionbank_distinct_capacity_denominator
    as builder,
)


class Unit02QuestionBankCapacityValidationError(ValueError):
    pass


def _require(condition: bool, code: str, errors: list[str]) -> None:
    if not condition:
        errors.append(code)


def validate_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    target = value.get("unit02_capacity_target", {})
    inventory = value.get("inventory_evidence", {})
    q9 = value.get("q9_task_family_evidence", {})
    rows = value.get("task_family_capacity_rows", [])
    aggregate = value.get("aggregate_capacity_readback", {})
    verdict = value.get("capacity_verdict", {})
    boundaries = value.get("claim_boundaries", {})
    next_scope = value.get("next_scope", {})

    _require(value.get("task_id") == builder.TASK_ID, "TASK_ID_INVALID", errors)
    _require(value.get("status") == builder.PASS_STATUS, "STATUS_INVALID", errors)
    _require(value.get("unit_id") == builder.UNIT_ID, "UNIT_ID_INVALID", errors)

    _require(target.get("form_count_target") == 16, "UNIT02_FORM_TARGET_INVALID", errors)
    _require(
        target.get("activities_per_form_target") == 40,
        "UNIT02_ACTIVITIES_PER_FORM_TARGET_INVALID",
        errors,
    )
    _require(
        target.get("total_activity_capacity_target") == 640,
        "UNIT02_TOTAL_ACTIVITY_CAPACITY_INVALID",
        errors,
    )
    _require(
        target.get("minimum_legal_candidates_per_slot") == 3,
        "MIN_CANDIDATE_DEPTH_INVALID",
        errors,
    )
    _require(
        target.get("minimum_slot_candidate_binding_capacity") == 1920,
        "MIN_SLOT_CANDIDATE_BINDING_CAPACITY_INVALID",
        errors,
    )
    _require(
        target.get("unit01_12_forms_240_activities_inherited_as_unit02_target") is False,
        "UNIT01_FORM_MODEL_LEAKED_INTO_UNIT02",
        errors,
    )

    _require(
        inventory.get("unit01_reusable_runtime_item_count") == 474,
        "UNIT01_REUSABLE_ITEM_COUNT_INVALID",
        errors,
    )
    _require(
        inventory.get("unit02_approved_item_count") == 658,
        "UNIT02_APPROVED_ITEM_COUNT_INVALID",
        errors,
    )
    _require(
        inventory.get("projected_cumulative_approved_item_count") == 1132,
        "PROJECTED_CUMULATIVE_ITEM_COUNT_INVALID",
        errors,
    )
    _require(
        inventory.get("current_runtime_connected_unit02_item_count") == 0,
        "UNIT02_RUNTIME_CONNECTED_COUNT_INVALID",
        errors,
    )
    _require(
        inventory.get("unit02_runtime_status") == "NOT_CONNECTED",
        "UNIT02_RUNTIME_STATUS_INVALID",
        errors,
    )

    _require(q9.get("task_role_count") == 5, "Q9_TASK_ROLE_COUNT_INVALID", errors)
    _require(q9.get("task_family_count") == 10, "Q9_TASK_FAMILY_COUNT_INVALID", errors)
    _require(q9.get("task_family_full_count") == 5, "Q9_FULL_COUNT_INVALID", errors)
    _require(q9.get("task_family_partial_count") == 3, "Q9_PARTIAL_COUNT_INVALID", errors)
    _require(q9.get("task_family_gap_count") == 2, "Q9_GAP_COUNT_INVALID", errors)
    _require(
        q9.get("task_family_gap_ids")
        == ["ERROR_CORRECTION", "U01_U02_INTEGRATION"],
        "Q9_GAP_IDS_INVALID",
        errors,
    )
    _require(
        q9.get("task_family_partial_ids")
        == ["ERROR_DETECTION", "CONTEXT_GAP", "TRANSFER"],
        "Q9_PARTIAL_IDS_INVALID",
        errors,
    )

    _require(len(rows) == 10, "TASK_FAMILY_CAPACITY_ROW_COUNT_INVALID", errors)
    row_ids = [row.get("task_family") for row in rows]
    _require(
        row_ids == list(builder.u02ta01.TASK_FAMILIES),
        "TASK_FAMILY_ORDER_INVALID",
        errors,
    )
    _require(
        all(row.get("minimum_legal_candidates_per_slot") == 3 for row in rows),
        "TASK_FAMILY_MIN_CANDIDATE_DEPTH_INVALID",
        errors,
    )
    _require(
        all(row.get("exact_eligible_item_count_by_slot_known") is False for row in rows),
        "UNPROVEN_SLOT_CAPACITY_OVERCLAIMED",
        errors,
    )
    _require(
        all(row.get("learner_visible_distinctness_proven") is False for row in rows),
        "LEARNER_VISIBLE_DISTINCTNESS_OVERCLAIMED",
        errors,
    )

    _require(
        aggregate.get("projected_cumulative_approved_items") == 1132,
        "AGGREGATE_PROJECTED_ITEMS_INVALID",
        errors,
    )
    _require(
        aggregate.get("aggregate_inventory_exceeds_activity_slot_count") is True,
        "AGGREGATE_SIZE_RELATION_INVALID",
        errors,
    )
    _require(
        aggregate.get("aggregate_inventory_alone_proves_distinct_capacity") is False,
        "AGGREGATE_CAPACITY_OVERCLAIMED",
        errors,
    )
    _require(
        aggregate.get("minimum_slot_candidate_binding_capacity") == 1920,
        "AGGREGATE_MIN_BINDING_CAPACITY_INVALID",
        errors,
    )
    _require(
        aggregate.get("exact_slot_candidate_matrix_materialized") is False,
        "SLOT_MATRIX_OVERCLAIMED",
        errors,
    )

    _require(verdict.get("denominator_resolved") is True, "DENOMINATOR_NOT_RESOLVED", errors)
    _require(
        verdict.get("distinct_capacity_status") == "NOT_PROVEN",
        "DISTINCT_CAPACITY_STATUS_INVALID",
        errors,
    )
    _require(
        verdict.get("unit02_640_slot_capacity_closed") is False,
        "UNIT02_CAPACITY_FALSE_PASS",
        errors,
    )
    _require(
        verdict.get("hard_task_family_gap_ids")
        == ["ERROR_CORRECTION", "U01_U02_INTEGRATION"],
        "HARD_GAP_RECONCILIATION_INVALID",
        errors,
    )

    expected_boundaries = {
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
    _require(boundaries == expected_boundaries, "CLAIM_BOUNDARIES_INVALID", errors)
    _require(
        next_scope.get("scope_status") == builder.NEXT_SCOPE_STATUS,
        "NEXT_SCOPE_STATUS_INVALID",
        errors,
    )
    _require(
        next_scope.get("next_short_step") == builder.NEXT_SHORT_STEP,
        "NEXT_SHORT_STEP_INVALID",
        errors,
    )
    _require(
        next_scope.get("requires_content_materialization") is True,
        "NEXT_SCOPE_IMPLEMENTATION_BOUNDARY_INVALID",
        errors,
    )

    return {
        "validation_status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "form_count_target": target.get("form_count_target"),
        "activities_per_form_target": target.get("activities_per_form_target"),
        "total_activity_capacity_target": target.get("total_activity_capacity_target"),
        "unit01_reusable_runtime_items": inventory.get("unit01_reusable_runtime_item_count"),
        "unit02_approved_items": inventory.get("unit02_approved_item_count"),
        "projected_cumulative_approved_items": inventory.get(
            "projected_cumulative_approved_item_count"
        ),
        "task_family_count": q9.get("task_family_count"),
        "hard_task_family_gap_count": verdict.get("hard_task_family_gap_count"),
        "distinct_capacity_status": verdict.get("distinct_capacity_status"),
    }


def validate() -> dict[str, Any]:
    return validate_payload(builder.payload())


def main() -> int:
    report = validate()
    print(f"STATUS={report['validation_status']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(
        "UNIT02_TARGET="
        f"{report['form_count_target']}x{report['activities_per_form_target']}="
        f"{report['total_activity_capacity_target']}"
    )
    print(
        "PROJECTED_CUMULATIVE_APPROVED_ITEMS="
        f"{report['projected_cumulative_approved_items']}"
    )
    print(f"DISTINCT_CAPACITY_STATUS={report['distinct_capacity_status']}")
    if report["errors"]:
        for error in report["errors"]:
            print(f"ERROR={error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
