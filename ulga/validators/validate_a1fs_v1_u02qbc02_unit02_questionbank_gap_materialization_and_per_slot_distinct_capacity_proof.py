#!/usr/bin/env python3
"""Validate U02QBC02 gap materialization and per-slot distinct-capacity proof."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u02qbc02_unit02_questionbank_gap_materialization_and_per_slot_distinct_capacity_proof
    as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U02QBC02_GAP_MATERIALIZATION_PER_SLOT_CAPACITY_VALIDATOR"


class Unit02QBC02ValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Unit02QBC02ValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def validate_new_item(item: Mapping[str, Any]) -> None:
    task_family = str(item.get("task_family") or "")
    require(task_family in builder.MATERIALIZED_TASK_FAMILIES, f"UNKNOWN_TASK_FAMILY:{task_family}")
    require(item.get("unit_id") == builder.UNIT_ID, "UNIT_ID_INVALID")
    require(item.get("learner_visible_capable") is True, "LEARNER_VISIBLE_FLAG_INVALID")
    require(item.get("learner_delivery_status") == "NOT_RUNTIME_CONNECTED", "RUNTIME_STATUS_INVALID")
    require(item.get("runtime_generation_used") is False, "RUNTIME_GENERATION_FORBIDDEN")
    require(item.get("canonical_scene_ref_id") is None, "CANONICAL_SCENE_REF_FORBIDDEN")
    require(item.get("scene_authority_claimed") is False, "SCENE_AUTHORITY_OVERCLAIM")
    require(item.get("target_egp_row_ids") == [builder.u02qb02.KP014], "TARGET_EGP_INVALID")
    require(
        item.get("correct_answer") in item.get("response_contract", {}).get("accepted_texts", []),
        "RESPONSE_CONTRACT_INVALID",
    )
    require(
        item.get("question_type") == builder.QUESTION_TYPE_BY_FAMILY[task_family],
        "QUESTION_TYPE_INVALID",
    )
    require(
        item.get("semantic_signature")
        == policy_artifact.digest(
            {
                "task_family": task_family,
                "lexical_slots": item["lexical_slots"],
                "prompt": item["prompt"],
                "stimulus": item["stimulus"],
                "options": item["options"],
                "correct_answer": item["correct_answer"],
            }
        ),
        "SEMANTIC_SIGNATURE_INVALID",
    )
    if task_family == "U01_U02_INTEGRATION":
        require(
            item.get("grammar_target_ids")
            == ["GRAMMAR_ARTICLES_BASIC", "REGULAR_PLURAL_NOUNS"],
            "INTEGRATION_GRAMMAR_TARGET_INVALID",
        )
        require(
            set(builder.u01_contract.CORE_EGP_ROWS).issubset(
                set(item.get("prerequisite_egp_row_ids", []))
            ),
            "UNIT01_ARTICLE_PREREQUISITE_MISSING",
        )
    else:
        require(
            item.get("grammar_target_ids") == ["REGULAR_PLURAL_NOUNS"],
            "GRAMMAR_TARGET_INVALID",
        )


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_ID_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")

    inventory = payload.get("questionbank_inventory", {})
    require(inventory.get("unit01_reusable_runtime_items") == 474, "UNIT01_COUNT_INVALID")
    require(inventory.get("unit02_existing_approved_items") == 658, "BASE_U02_COUNT_INVALID")
    require(inventory.get("unit02_new_gap_materialized_items") == 336, "NEW_ITEM_COUNT_INVALID")
    require(inventory.get("unit02_approved_items_after_qbc02") == 994, "UNIT02_TOTAL_INVALID")
    require(inventory.get("cumulative_approved_items_after_qbc02") == 1468, "CUMULATIVE_TOTAL_INVALID")
    require(inventory.get("parallel_questionbank_created") is False, "PARALLEL_BANK_CREATED")
    require(inventory.get("runtime_status") == "NOT_CONNECTED", "RUNTIME_STATUS_OVERCLAIM")

    new_items = payload.get("new_approved_items")
    require(isinstance(new_items, list) and len(new_items) == 336, "NEW_ITEMS_SHAPE_INVALID")
    require(len({row["item_id"] for row in new_items}) == 336, "DUPLICATE_NEW_ITEM_ID")
    require(
        len({row["semantic_signature"] for row in new_items}) == 336,
        "DUPLICATE_NEW_SIGNATURE",
    )
    counts = Counter(row["task_family"] for row in new_items)
    require(
        counts == Counter({family: 48 for family in builder.MATERIALIZED_TASK_FAMILIES}),
        "NEW_TASK_FAMILY_DISTRIBUTION_INVALID",
    )
    for item in new_items:
        validate_new_item(item)

    pools = payload.get("task_family_pools", {})
    require(set(pools) == set(builder.TASK_FAMILIES), "TASK_FAMILY_POOL_KEYS_INVALID")
    require(all(len(ids) >= 48 for ids in pools.values()), "TASK_FAMILY_POOL_DEPTH_INVALID")

    model = payload.get("capacity_model", {})
    require(model.get("form_count") == 16, "FORM_COUNT_INVALID")
    require(model.get("scene_slots_per_form") == 4, "SCENE_SLOT_COUNT_INVALID")
    require(model.get("task_family_count") == 10, "TASK_FAMILY_COUNT_INVALID")
    require(model.get("activities_per_form") == 40, "ACTIVITIES_PER_FORM_INVALID")
    require(model.get("total_capacity_slots") == 640, "TOTAL_SLOT_COUNT_INVALID")
    require(model.get("minimum_candidates_per_slot") == 3, "MIN_CANDIDATE_DEPTH_INVALID")
    require(model.get("slot_candidate_binding_count") == 1920, "BINDING_COUNT_INVALID")
    require(
        model.get("all_ten_task_families_have_at_least_48_candidates") is True,
        "POOL_DEPTH_PROOF_INVALID",
    )

    matrix = payload.get("capacity_slot_matrix")
    require(isinstance(matrix, list) and len(matrix) == 640, "MATRIX_SIZE_INVALID")
    require(len({row["slot_id"] for row in matrix}) == 640, "DUPLICATE_SLOT_ID")
    require(
        sum(len(row["candidate_ids"]) for row in matrix) == 1920,
        "MATRIX_BINDING_COUNT_INVALID",
    )
    pool_sets = {family: set(ids) for family, ids in pools.items()}
    for row in matrix:
        require(row.get("canonical_scene_bound") is False, "CAPACITY_SLOT_CANONICAL_SCENE_OVERCLAIM")
        require(row.get("runtime_selection_materialized") is False, "RUNTIME_SELECTION_OVERCLAIM")
        require(row.get("legal_candidate_count") == 3, "SLOT_DEPTH_INVALID")
        require(len(row.get("candidate_ids", [])) == 3, "SLOT_CANDIDATE_COUNT_INVALID")
        require(len(set(row["candidate_ids"])) == 3, "SLOT_CANDIDATES_NOT_DISTINCT")
        require(row.get("learner_visible_distinct_candidates") is True, "SLOT_DISTINCT_FLAG_INVALID")
        family = row["task_family"]
        require(
            all(candidate_id in pool_sets[family] for candidate_id in row["candidate_ids"]),
            "SLOT_CANDIDATE_OUTSIDE_POOL",
        )

    for form_number in range(1, 17):
        form_rows = [row for row in matrix if row["form_number"] == form_number]
        require(len(form_rows) == 40, f"FORM_SLOT_COUNT_INVALID:{form_number}")
        for family in builder.TASK_FAMILIES:
            ids = [
                cid
                for row in form_rows
                if row["task_family"] == family
                for cid in row["candidate_ids"]
            ]
            require(
                len(ids) == 12 and len(set(ids)) == 12,
                f"WITHIN_FORM_FAMILY_DISTINCTNESS_INVALID:{form_number}:{family}",
            )

    verdict = payload.get("capacity_verdict", {})
    require(verdict.get("q9_hard_gaps_materialized") is True, "Q9_HARD_GAPS_NOT_CLOSED")
    require(verdict.get("q9_partial_families_reconciled") is True, "Q9_PARTIAL_NOT_RECONCILED")
    require(verdict.get("exact_slot_candidate_matrix_materialized") is True, "SLOT_MATRIX_NOT_MATERIALIZED")
    require(
        verdict.get("all_640_slots_have_at_least_3_legal_candidates") is True,
        "SLOT_CAPACITY_NOT_PROVEN",
    )
    require(
        verdict.get("all_slot_candidate_sets_are_learner_visible_distinct") is True,
        "LEARNER_VISIBLE_DISTINCTNESS_NOT_PROVEN",
    )
    require(
        verdict.get("within_form_same_task_family_candidate_reuse") is False,
        "WITHIN_FORM_REUSE_PRESENT",
    )
    require(verdict.get("distinct_capacity_status") == "PROVEN", "DISTINCT_CAPACITY_NOT_PROVEN")
    require(verdict.get("unit02_640_slot_capacity_closed") is True, "UNIT02_CAPACITY_NOT_CLOSED")

    boundaries = payload.get("claim_boundaries", {})
    require(
        boundaries
        == {
            "unit01_questionbank_mutated": False,
            "parallel_questionbank_created": False,
            "unit02_runtime_connected": False,
            "final_forms_materialized": False,
            "learner_sessions_materialized": False,
            "canonical_scene_authority_mutated": False,
            "learner_state_mutated": False,
            "a2_unlocked": False,
        },
        "CLAIM_BOUNDARIES_INVALID",
    )

    return {
        "validation_status": "PASS",
        "error_count": 0,
        "new_item_count": len(new_items),
        "unit02_approved_items": inventory["unit02_approved_items_after_qbc02"],
        "cumulative_approved_items": inventory["cumulative_approved_items_after_qbc02"],
        "capacity_slots": len(matrix),
        "slot_candidate_bindings": sum(len(row["candidate_ids"]) for row in matrix),
        "distinct_capacity_status": verdict["distinct_capacity_status"],
    }


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(
        candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE,
        "CANDIDATE_ROLE_INVALID",
    )
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "CANDIDATE_PAYLOAD_INVALID")
    validate_payload(payload)
    receipt = validation_receipt(payload)
    require(
        receipt["validated_payload_sha256"] == policy_artifact.digest(payload),
        "RECEIPT_HASH_INVALID",
    )
    return receipt


def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    require(
        approved.get("artifact_role") == policy_artifact.APPROVED_ROLE,
        "APPROVED_ROLE_INVALID",
    )
    require(approved.get("payload") == candidate.get("payload"), "APPROVED_PAYLOAD_DRIFT")
    report = validate_payload(approved["payload"])
    report["candidate_artifact_sha256"] = candidate.get("artifact_sha256")
    report["approved_artifact_sha256"] = approved.get("artifact_sha256")
    return report


def main() -> int:
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validate_approved(candidate, approved)
    print(f"STATUS={report['validation_status']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"NEW_ITEM_COUNT={report['new_item_count']}")
    print(f"CAPACITY_SLOTS={report['capacity_slots']}")
    print(f"SLOT_CANDIDATE_BINDINGS={report['slot_candidate_bindings']}")
    print(f"DISTINCT_CAPACITY_STATUS={report['distinct_capacity_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
