#!/usr/bin/env python3
"""Validate the Unit02 task-angle / question-type coverage denominator."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_u02ta01_unit02_task_angle_question_type_coverage_denominator
    as builder,
)

PASS_STATUS = "PASS_A1FS_V1_U02TA01_UNIT02_TASK_ANGLE_QUESTION_TYPE_COVERAGE_DENOMINATOR_VALIDATION"


def _require(condition: bool, errors: list[str], code: str) -> None:
    if not condition:
        errors.append(code)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, list) else []


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    _require(payload.get("status") == builder.PASS_STATUS, errors, "status_invalid")
    _require(payload.get("unit_id") == builder.UNIT_ID, errors, "unit_id_invalid")
    _require(payload.get("level_scope") == ["A1"], errors, "level_scope_invalid")

    roles = list(_sequence(payload.get("pedagogical_task_role_denominator")))
    families = list(_sequence(payload.get("task_question_family_denominator")))
    counts = _mapping(payload.get("coverage_denominators"))
    evidence = _mapping(payload.get("current_unit02_question_type_evidence"))

    _require(
        [row.get("task_role") for row in roles] == list(builder.TASK_ROLES),
        errors,
        "task_role_identity_invalid",
    )
    _require(
        [row.get("task_family") for row in families] == list(builder.TASK_FAMILIES),
        errors,
        "task_family_identity_invalid",
    )
    _require(len(roles) == 5, errors, "task_role_count_not_5")
    _require(len(families) == 10, errors, "task_family_count_not_10")

    role_statuses = [row.get("coverage_status") for row in roles]
    family_statuses = [row.get("coverage_status") for row in families]
    allowed = {"FULL", "PARTIAL", "GAP"}
    _require(set(role_statuses).issubset(allowed), errors, "task_role_status_invalid")
    _require(set(family_statuses).issubset(allowed), errors, "task_family_status_invalid")

    expected_role_status = {
        "REVIEW": "FULL",
        "NEW": "FULL",
        "INTEGRATION": "GAP",
        "VARIATION": "PARTIAL",
        "TRANSFER": "PARTIAL",
    }
    for row in roles:
        role = row.get("task_role")
        _require(
            row.get("coverage_status") == expected_role_status.get(role),
            errors,
            f"task_role_status_drift:{role}",
        )

    expected_family_status = {
        "RECOGNITION": "FULL",
        "MEANING_DISCRIMINATION": "FULL",
        "FORM_SELECTION": "FULL",
        "MORPHOLOGY_CONSTRUCTION": "FULL",
        "ERROR_DETECTION": "PARTIAL",
        "ERROR_CORRECTION": "GAP",
        "CONTEXT_GAP": "PARTIAL",
        "U01_U02_INTEGRATION": "GAP",
        "PRODUCTIVE_RESPONSE": "FULL",
        "TRANSFER": "PARTIAL",
    }
    for row in families:
        family = row.get("task_family")
        _require(
            row.get("coverage_status") == expected_family_status.get(family),
            errors,
            f"task_family_status_drift:{family}",
        )

    _require(counts.get("task_role_count") == 5, errors, "task_role_count_invalid")
    _require(counts.get("task_role_full_count") == 2, errors, "task_role_full_count_invalid")
    _require(counts.get("task_role_partial_count") == 2, errors, "task_role_partial_count_invalid")
    _require(counts.get("task_role_gap_count") == 1, errors, "task_role_gap_count_invalid")
    _require(counts.get("task_family_count") == 10, errors, "task_family_count_invalid")
    _require(counts.get("task_family_full_count") == 5, errors, "task_family_full_count_invalid")
    _require(counts.get("task_family_partial_count") == 3, errors, "task_family_partial_count_invalid")
    _require(counts.get("task_family_gap_count") == 2, errors, "task_family_gap_count_invalid")
    _require(
        counts.get("task_family_gap_ids") == ["ERROR_CORRECTION", "U01_U02_INTEGRATION"],
        errors,
        "task_family_gap_ids_invalid",
    )
    _require(
        counts.get("task_family_partial_ids")
        == ["ERROR_DETECTION", "CONTEXT_GAP", "TRANSFER"],
        errors,
        "task_family_partial_ids_invalid",
    )
    _require(
        counts.get("current_unit02_item_count") == builder.EXPECTED_UNIT02_ITEM_COUNT,
        errors,
        "unit02_item_count_invalid",
    )
    _require(
        counts.get("current_unit02_unique_task_type_count")
        == len(builder.EXPECTED_UNIT02_TASK_TYPES),
        errors,
        "unit02_unique_task_type_count_invalid",
    )
    _require(
        evidence.get("task_types") == list(builder.EXPECTED_UNIT02_TASK_TYPES),
        errors,
        "current_task_types_invalid",
    )
    _require(
        evidence.get("response_modes") == list(builder.EXPECTED_UNIT02_RESPONSE_MODES),
        errors,
        "current_response_modes_invalid",
    )
    _require(
        evidence.get("all_unit02_task_types_present_in_global_question_type_authority") is True,
        errors,
        "global_question_type_authority_binding_missing",
    )
    _require(
        evidence.get("all_current_unit02_items_single_grammar_focus") is True,
        errors,
        "single_grammar_focus_boundary_invalid",
    )

    contract = _mapping(payload.get("question9_contract"))
    _require(contract.get("denominator_resolved") is True, errors, "q9_denominator_not_resolved")
    _require(
        contract.get("all_task_families_materialized") is False,
        errors,
        "q9_false_full_materialization_claim",
    )
    _require(
        contract.get("gaps_must_feed_questionbank_gap_materialization") is True,
        errors,
        "q9_gap_handoff_missing",
    )
    _require(
        contract.get("distinct_capacity_not_claimed") is True,
        errors,
        "q9_distinct_capacity_boundary_missing",
    )

    boundaries = _mapping(payload.get("claim_boundaries"))
    expected_boundaries = {
        "canonical_graph_mutated": False,
        "questionbank_mutated": False,
        "new_question_items_authored": 0,
        "runtime_allocation_mutated": False,
        "learner_facing_content_created": False,
        "learner_state_joined": False,
        "distinct_item_capacity_claimed": False,
        "a2_unlocked": False,
    }
    _require(dict(boundaries) == expected_boundaries, errors, "claim_boundaries_invalid")

    _require(
        payload.get("next_scope")
        == {
            "coverage_denominator_number": 10,
            "coverage_denominator": "QUESTIONBANK_DISTINCT_CAPACITY",
            "scope_status": "OUTSIDE_APPROVED_Q9_SCOPE",
        },
        errors,
        "next_scope_invalid",
    )
    _require(
        payload.get("next_short_step") == builder.NEXT_SHORT_STEP,
        errors,
        "next_short_step_invalid",
    )

    return {
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "task_role_count": len(roles),
        "task_family_count": len(families),
        "task_family_gap_count": sum(
            row.get("coverage_status") == "GAP" for row in families
        ),
        "task_family_partial_count": sum(
            row.get("coverage_status") == "PARTIAL" for row in families
        ),
    }


def main() -> int:
    report = validate_payload(builder.payload())
    print(f"VALIDATION_STATUS={report['validation_status']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"TASK_ROLES={report['task_role_count']}")
    print(f"TASK_FAMILIES={report['task_family_count']}")
    print(f"TASK_FAMILY_GAPS={report['task_family_gap_count']}")
    print(f"TASK_FAMILY_PARTIAL={report['task_family_partial_count']}")
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
