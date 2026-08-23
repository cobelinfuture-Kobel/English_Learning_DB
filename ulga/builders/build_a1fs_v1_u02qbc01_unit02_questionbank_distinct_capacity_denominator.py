#!/usr/bin/env python3
"""Resolve the Unit02 cumulative QuestionBank distinct-capacity denominator.

U02QBC01 is a read-only capacity audit. It deliberately does not inherit the
Unit01 12-Form / 240-activity learner rotation. The Unit02 project-source target
is the larger cumulative model: 16 Forms x 40 activity slots = 640 activity
occurrences, with Unit01 review assets retained and Unit02 task families added.

This milestone distinguishes aggregate inventory size from proved selectable
capacity. The current Unit01 runtime base and the approved U02QB02 pool may be
counted as cumulative inventory evidence, but capacity is not closed until the
Q9 task-family gaps are materialized and a per-slot candidate matrix proves
sufficient learner-visible distinct alternatives.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from ulga.builders import (
    build_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as u02qb02,
)
from ulga.builders import (
    build_a1fs_v1_u02ta01_unit02_task_angle_question_type_coverage_denominator
    as u02ta01,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only Unit02 QuestionBank distinct-capacity denominator over the existing "
    "Unit01 474-item reusable runtime base, approved U02QB02 candidate pool, and "
    "U02TA01 task-family audit; it authors no QuestionBank item, Form, activity, "
    "runtime allocation, learner content, canonical graph node, learner state, or A2 content."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02QBC01_Unit02QuestionBankDistinctCapacityDenominator"
SCHEMA_VERSION = "a1fs.v1.u02qbc01.unit02_questionbank_distinct_capacity_denominator.v1"
PASS_STATUS = "PASS_A1FS_V1_U02QBC01_UNIT02_QUESTIONBANK_DISTINCT_CAPACITY_DENOMINATOR"
UNIT_ID = "GRAMMAR_REGULAR_PLURAL_NOUNS"
LEVEL_SCOPE = ["A1"]
DECISION_REF = (
    "PROJECT_SOURCE+OPERATOR_RECONFIRMATION:2026-08-23:"
    "UNIT02_V2_16_FORMS_X_40_ACTIVITIES_CAPACITY_MODEL"
)

FORM_COUNT_TARGET = 16
ACTIVITIES_PER_FORM_TARGET = 40
TOTAL_ACTIVITY_CAPACITY_TARGET = 640
MIN_LEGAL_CANDIDATES_PER_SLOT = 3
MIN_SLOT_CANDIDATE_BINDING_CAPACITY = (
    TOTAL_ACTIVITY_CAPACITY_TARGET * MIN_LEGAL_CANDIDATES_PER_SLOT
)

EXPECTED_UNIT01_REUSABLE_RUNTIME_ITEMS = 474
EXPECTED_UNIT02_APPROVED_ITEMS = 658
EXPECTED_PROJECTED_CUMULATIVE_APPROVED_ITEMS = (
    EXPECTED_UNIT01_REUSABLE_RUNTIME_ITEMS + EXPECTED_UNIT02_APPROVED_ITEMS
)
EXPECTED_Q9_TASK_ROLE_COUNT = 5
EXPECTED_Q9_TASK_FAMILY_COUNT = 10
EXPECTED_Q9_FULL_FAMILY_COUNT = 5
EXPECTED_Q9_PARTIAL_FAMILY_COUNT = 3
EXPECTED_Q9_GAP_FAMILY_COUNT = 2
EXPECTED_Q9_GAP_IDS = ("ERROR_CORRECTION", "U01_U02_INTEGRATION")
EXPECTED_Q9_PARTIAL_IDS = ("ERROR_DETECTION", "CONTEXT_GAP", "TRANSFER")

NEXT_SHORT_STEP = (
    "A1FS-V1-U02QBC02_"
    "Unit02QuestionBankGapMaterializationAndPerSlotDistinctCapacityProof"
)
NEXT_SCOPE_STATUS = "OUTSIDE_APPROVED_Q10_DENOMINATOR_SCOPE"


class Unit02QuestionBankCapacityError(ValueError):
    """Fail-closed Unit02 QuestionBank capacity denominator error."""


def _u02qb02_evidence() -> dict[str, Any]:
    approved = u02qb02.admit_candidate(u02qb02.build_candidate())
    payload = approved.get("payload", {})
    bank = payload.get("bank_identity", {})
    readback = payload.get("admission_readback", {})
    approved_items = payload.get("approved_items", [])

    u01_count = int(bank.get("unit01_runtime_base_item_count") or 0)
    u02_count = int(readback.get("approved_count") or 0)
    if u01_count != EXPECTED_UNIT01_REUSABLE_RUNTIME_ITEMS:
        raise Unit02QuestionBankCapacityError(
            f"UNIT01_REUSABLE_RUNTIME_COUNT_DRIFT:{u01_count}"
        )
    if u02_count != EXPECTED_UNIT02_APPROVED_ITEMS:
        raise Unit02QuestionBankCapacityError(
            f"UNIT02_APPROVED_ITEM_COUNT_DRIFT:{u02_count}"
        )
    if len(approved_items) != EXPECTED_UNIT02_APPROVED_ITEMS:
        raise Unit02QuestionBankCapacityError(
            f"UNIT02_APPROVED_ITEM_PAYLOAD_COUNT_DRIFT:{len(approved_items)}"
        )
    item_ids = [str(row.get("item_id")) for row in approved_items]
    signatures = [str(row.get("semantic_signature")) for row in approved_items]
    if len(item_ids) != len(set(item_ids)):
        raise Unit02QuestionBankCapacityError("UNIT02_APPROVED_ITEM_ID_DUPLICATE")
    if len(signatures) != len(set(signatures)):
        raise Unit02QuestionBankCapacityError(
            "UNIT02_APPROVED_SEMANTIC_SIGNATURE_DUPLICATE"
        )
    if bank.get("unit01_runtime_base_reused") is not True:
        raise Unit02QuestionBankCapacityError("UNIT01_RUNTIME_BASE_NOT_REUSED")
    if bank.get("parallel_questionbank_created") is not False:
        raise Unit02QuestionBankCapacityError("PARALLEL_QUESTIONBANK_DETECTED")
    if bank.get("runtime_status") != "NOT_CONNECTED":
        raise Unit02QuestionBankCapacityError(
            f"UNIT02_RUNTIME_STATUS_DRIFT:{bank.get('runtime_status')}"
        )
    if any(row.get("learner_delivery_status") != "NOT_RUNTIME_CONNECTED" for row in approved_items):
        raise Unit02QuestionBankCapacityError(
            "UNIT02_APPROVED_ITEM_RUNTIME_CONNECTION_DRIFT"
        )

    family_counts = dict(
        sorted(Counter(str(row.get("pattern_family_id")) for row in approved_items).items())
    )
    question_type_counts = dict(
        sorted(Counter(str(row.get("question_type")) for row in approved_items).items())
    )
    skill_counts = dict(
        sorted(Counter(str(row.get("skill")) for row in approved_items).items())
    )

    return {
        "source_task_id": u02qb02.TASK_ID,
        "unit01_reusable_runtime_item_count": u01_count,
        "unit02_approved_item_count": u02_count,
        "projected_cumulative_approved_item_count": u01_count + u02_count,
        "current_runtime_connected_unit02_item_count": 0,
        "current_runtime_cumulative_item_count": u01_count,
        "unit02_runtime_status": bank["runtime_status"],
        "unit02_approved_item_ids_unique": True,
        "unit02_approved_semantic_signatures_unique": True,
        "unit02_pattern_family_counts": family_counts,
        "unit02_question_type_counts": question_type_counts,
        "unit02_skill_counts": skill_counts,
    }


def _q9_evidence() -> dict[str, Any]:
    q9 = u02ta01.payload()
    counts = q9.get("coverage_denominators", {})
    expected = {
        "task_role_count": EXPECTED_Q9_TASK_ROLE_COUNT,
        "task_family_count": EXPECTED_Q9_TASK_FAMILY_COUNT,
        "task_family_full_count": EXPECTED_Q9_FULL_FAMILY_COUNT,
        "task_family_partial_count": EXPECTED_Q9_PARTIAL_FAMILY_COUNT,
        "task_family_gap_count": EXPECTED_Q9_GAP_FAMILY_COUNT,
    }
    for key, value in expected.items():
        actual = counts.get(key)
        if actual != value:
            raise Unit02QuestionBankCapacityError(
                f"Q9_DENOMINATOR_DRIFT:{key}:{actual}:{value}"
            )
    gap_ids = tuple(counts.get("task_family_gap_ids", []))
    partial_ids = tuple(counts.get("task_family_partial_ids", []))
    if gap_ids != EXPECTED_Q9_GAP_IDS:
        raise Unit02QuestionBankCapacityError(f"Q9_GAP_ID_DRIFT:{gap_ids}")
    if partial_ids != EXPECTED_Q9_PARTIAL_IDS:
        raise Unit02QuestionBankCapacityError(
            f"Q9_PARTIAL_ID_DRIFT:{partial_ids}"
        )
    if q9.get("question9_contract", {}).get("distinct_capacity_not_claimed") is not True:
        raise Unit02QuestionBankCapacityError(
            "Q9_DISTINCT_CAPACITY_BOUNDARY_NOT_PRESERVED"
        )

    return {
        "source_task_id": u02ta01.TASK_ID,
        "task_role_count": counts["task_role_count"],
        "task_family_count": counts["task_family_count"],
        "task_family_full_count": counts["task_family_full_count"],
        "task_family_partial_count": counts["task_family_partial_count"],
        "task_family_gap_count": counts["task_family_gap_count"],
        "task_family_gap_ids": list(gap_ids),
        "task_family_partial_ids": list(partial_ids),
        "task_family_rows": deepcopy(q9.get("task_question_family_denominator", [])),
        "pedagogical_role_rows": deepcopy(q9.get("pedagogical_task_role_denominator", [])),
    }


def _family_capacity_rows(q9: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for source in q9["task_family_rows"]:
        status = str(source.get("coverage_status"))
        if status == "GAP":
            capacity_status = "HARD_GAP"
            blocker = "TASK_FAMILY_NOT_MATERIALIZED"
        elif status == "PARTIAL":
            capacity_status = "NOT_PROVEN"
            blocker = "EXACT_DISTINCT_CAPACITY_NOT_PROVEN"
        elif status == "FULL":
            capacity_status = "STRUCTURAL_SUPPORT_PRESENT_CAPACITY_NOT_PROVEN"
            blocker = "PER_SLOT_CANDIDATE_MATRIX_NOT_MATERIALIZED"
        else:
            raise Unit02QuestionBankCapacityError(
                f"UNKNOWN_Q9_COVERAGE_STATUS:{status}"
            )
        rows.append(
            {
                "task_family": str(source["task_family"]),
                "q9_coverage_status": status,
                "q9_gap": source.get("gap"),
                "capacity_status": capacity_status,
                "capacity_blocker": blocker,
                "minimum_legal_candidates_per_slot": MIN_LEGAL_CANDIDATES_PER_SLOT,
                "exact_eligible_item_count_by_slot_known": False,
                "learner_visible_distinctness_proven": False,
            }
        )
    if len(rows) != EXPECTED_Q9_TASK_FAMILY_COUNT:
        raise Unit02QuestionBankCapacityError(
            f"TASK_FAMILY_CAPACITY_ROW_COUNT_INVALID:{len(rows)}"
        )
    return rows


def payload() -> dict[str, Any]:
    inventory = _u02qb02_evidence()
    q9 = _q9_evidence()
    family_rows = _family_capacity_rows(q9)

    projected = inventory["projected_cumulative_approved_item_count"]
    if projected != EXPECTED_PROJECTED_CUMULATIVE_APPROVED_ITEMS:
        raise Unit02QuestionBankCapacityError(
            f"PROJECTED_CUMULATIVE_ITEM_COUNT_DRIFT:{projected}"
        )

    hard_gaps = [row["task_family"] for row in family_rows if row["capacity_status"] == "HARD_GAP"]
    if hard_gaps != list(EXPECTED_Q9_GAP_IDS):
        raise Unit02QuestionBankCapacityError(
            f"HARD_GAP_RECONCILIATION_INVALID:{hard_gaps}"
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "level_scope": list(LEVEL_SCOPE),
        "decision_ref": DECISION_REF,
        "unit02_capacity_target": {
            "form_count_target": FORM_COUNT_TARGET,
            "activities_per_form_target": ACTIVITIES_PER_FORM_TARGET,
            "total_activity_capacity_target": TOTAL_ACTIVITY_CAPACITY_TARGET,
            "minimum_legal_candidates_per_slot": MIN_LEGAL_CANDIDATES_PER_SLOT,
            "minimum_slot_candidate_binding_capacity": MIN_SLOT_CANDIDATE_BINDING_CAPACITY,
            "unit01_12_forms_240_activities_inherited_as_unit02_target": False,
            "target_is_cumulative_unit02_model": True,
            "forms_are_capacity_containers_not_single_session_length_claims": True,
        },
        "inventory_evidence": inventory,
        "q9_task_family_evidence": {
            key: value
            for key, value in q9.items()
            if key not in {"task_family_rows", "pedagogical_role_rows"}
        },
        "task_family_capacity_rows": family_rows,
        "aggregate_capacity_readback": {
            "unit01_reusable_runtime_items": EXPECTED_UNIT01_REUSABLE_RUNTIME_ITEMS,
            "unit02_approved_not_runtime_connected_items": EXPECTED_UNIT02_APPROVED_ITEMS,
            "projected_cumulative_approved_items": projected,
            "projected_items_per_activity_slot": projected / TOTAL_ACTIVITY_CAPACITY_TARGET,
            "aggregate_inventory_exceeds_activity_slot_count": (
                projected > TOTAL_ACTIVITY_CAPACITY_TARGET
            ),
            "aggregate_inventory_alone_proves_distinct_capacity": False,
            "minimum_slot_candidate_binding_capacity": MIN_SLOT_CANDIDATE_BINDING_CAPACITY,
            "exact_slot_candidate_matrix_materialized": False,
            "learner_visible_distinctness_proven_for_unit02_640_slot_model": False,
        },
        "capacity_verdict": {
            "denominator_resolved": True,
            "distinct_capacity_status": "NOT_PROVEN",
            "unit02_640_slot_capacity_closed": False,
            "hard_task_family_gap_count": len(hard_gaps),
            "hard_task_family_gap_ids": hard_gaps,
            "partial_task_family_count": EXPECTED_Q9_PARTIAL_FAMILY_COUNT,
            "partial_task_family_ids": list(EXPECTED_Q9_PARTIAL_IDS),
            "required_before_capacity_pass": [
                "MATERIALIZE_Q9_HARD_GAP_TASK_FAMILIES",
                "RECONCILE_Q9_PARTIAL_TASK_FAMILIES",
                "BUILD_UNIT02_640_SLOT_TO_CANDIDATE_MATRIX",
                "PROVE_AT_LEAST_3_LEGAL_CANDIDATES_PER_SLOT",
                "PROVE_LEARNER_VISIBLE_DISTINCTNESS_WITHIN_SELECTION_SCOPE",
                "CONNECT_ONLY_ADMITTED_UNIT02_ITEMS_THROUGH_EXISTING_CUMULATIVE_RUNTIME",
            ],
        },
        "claim_boundaries": {
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
        },
        "next_scope": {
            "scope_status": NEXT_SCOPE_STATUS,
            "next_short_step": NEXT_SHORT_STEP,
            "requires_content_materialization": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def build() -> dict[str, Any]:
    return payload()


def main() -> int:
    value = payload()
    counts = value["aggregate_capacity_readback"]
    verdict = value["capacity_verdict"]
    print(f"STATUS={value['status']}")
    print(
        "UNIT02_TARGET="
        f"{FORM_COUNT_TARGET}x{ACTIVITIES_PER_FORM_TARGET}="
        f"{TOTAL_ACTIVITY_CAPACITY_TARGET}"
    )
    print(
        "PROJECTED_CUMULATIVE_APPROVED_ITEMS="
        f"{counts['projected_cumulative_approved_items']}"
    )
    print(
        "MIN_SLOT_CANDIDATE_BINDING_CAPACITY="
        f"{counts['minimum_slot_candidate_binding_capacity']}"
    )
    print(f"DISTINCT_CAPACITY_STATUS={verdict['distinct_capacity_status']}")
    print(
        "HARD_TASK_FAMILY_GAPS="
        + ",".join(verdict["hard_task_family_gap_ids"])
    )
    print(f"NEXT_SHORT_STEP={value['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
