#!/usr/bin/env python3
"""Validate U02FORM03R3 Q09/Q10 pedagogical FullFix successor authority."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u02form03r3_source_authority_pedagogical_fullfix_and_global_distinct_runtime
    as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U02FORM03R3_SOURCE_AUTHORITY_PEDAGOGICAL_FULLFIX_VALIDATOR"


class U02Form03R3ValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise U02Form03R3ValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_ID_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")

    preservation = payload.get("q01_q08_preservation", {})
    require(preservation.get("preserved") is True, "Q01_Q08_NOT_PRESERVED")
    require(
        preservation.get("baseline_sha256") == preservation.get("r3_sha256"),
        "Q01_Q08_DIGEST_DRIFT",
    )

    q9 = payload.get("q9_task_angle_question_type", {})
    summary = q9.get("post_materialization_summary", {})
    require(summary.get("task_family_count") == 10, "Q9_FAMILY_COUNT_INVALID")
    require(
        summary.get("all_ten_task_family_pools_have_at_least_64_runtime_eligible_items")
        is True,
        "Q9_POOL_DEPTH_NOT_PROVEN",
    )
    require(
        summary.get("global_640_distinct_runtime_question_proof") is True,
        "Q9_GLOBAL_DISTINCTNESS_NOT_PROVEN",
    )

    q10 = payload.get("q10_questionbank_capacity_runtime", {})
    inventory = q10.get("inventory_summary", {})
    require(
        inventory.get("unit01_reference_only_item_count")
        == builder.EXPECTED_UNIT01_REFERENCE_ITEMS,
        "UNIT01_COUNT_INVALID",
    )
    require(
        inventory.get("unit02_approved_item_count")
        == builder.EXPECTED_UNIT02_APPROVED_ITEMS,
        "UNIT02_COUNT_INVALID",
    )
    require(
        inventory.get("cumulative_catalog_item_count")
        == builder.EXPECTED_CUMULATIVE_ITEMS,
        "CUMULATIVE_COUNT_INVALID",
    )
    require(inventory.get("legacy_qbc02_items_deleted") is False, "LEGACY_ITEMS_DELETED")
    require(inventory.get("parallel_questionbank_created") is False, "PARALLEL_BANK_CREATED")

    items = q10.get("unit02_approved_items")
    require(
        isinstance(items, list)
        and len(items) == builder.EXPECTED_UNIT02_APPROVED_ITEMS,
        "APPROVED_ITEM_LIST_INVALID",
    )
    require(
        len({row["item_id"] for row in items}) == len(items),
        "APPROVED_ITEM_ID_COLLISION",
    )
    r3_items = [
        row for row in items if str(row["item_id"]).startswith("U02FORM03R3-")
    ]
    require(len(r3_items) == builder.R3_NEW_ITEMS, "R3_NEW_ITEM_COUNT_INVALID")
    require(
        Counter(row["task_family"] for row in r3_items)
        == Counter(
            {
                family: builder.R3_CONTEXTS_PER_MATERIALIZED_FAMILY
                for family in builder.R3_MATERIALIZED_FAMILIES
            }
        ),
        "R3_NEW_ITEM_FAMILY_DISTRIBUTION_INVALID",
    )
    require(
        len({row["semantic_signature"] for row in r3_items}) == len(r3_items),
        "R3_NEW_ITEM_SIGNATURE_COLLISION",
    )

    runtime = q10.get("runtime_occurrences")
    require(
        isinstance(runtime, list)
        and len(runtime) == builder.TOTAL_RUNTIME_OCCURRENCES,
        "RUNTIME_COUNT_INVALID",
    )
    require(
        len({row["runtime_occurrence_id"] for row in runtime}) == 640,
        "RUNTIME_ID_COLLISION",
    )
    require(
        len({row["selected_item_id"] for row in runtime}) == 640,
        "RUNTIME_SELECTED_ITEM_COLLISION",
    )
    require(
        Counter(row["task_family"] for row in runtime)
        == Counter({family: 64 for family in builder.TASK_FAMILIES}),
        "RUNTIME_FAMILY_DISTRIBUTION_INVALID",
    )
    require(
        all(len(row["candidate_ids"]) == 3 for row in runtime),
        "RUNTIME_CANDIDATE_COUNT_INVALID",
    )
    require(
        all(len(set(row["candidate_ids"])) == 3 for row in runtime),
        "RUNTIME_CANDIDATE_DISTINCTNESS_INVALID",
    )
    require(
        all(row["selected_item_id"] == row["candidate_ids"][0] for row in runtime),
        "RUNTIME_SELECTION_RULE_INVALID",
    )
    require(
        all(
            str(row["target_singular"]).casefold()
            not in builder.RUNTIME_RESTRICTED_SURFACES
            for row in runtime
        ),
        "RESTRICTED_SURFACE_SELECTED",
    )
    require(
        not any(
            str(row["selected_item_id"]).startswith("U02QBC02-")
            for row in runtime
        ),
        "LEGACY_QBC02_ITEM_SELECTED",
    )

    proof = q10.get("global_distinctness_proof", {})
    require(proof.get("runtime_occurrence_count") == 640, "PROOF_RUNTIME_COUNT_INVALID")
    require(
        proof.get("distinct_runtime_occurrence_ids") == 640,
        "PROOF_RUNTIME_ID_DISTINCTNESS_INVALID",
    )
    require(
        proof.get("distinct_selected_item_ids") == 640,
        "PROOF_SELECTED_ID_DISTINCTNESS_INVALID",
    )
    require(
        proof.get("distinct_visible_signatures") == 640,
        "PROOF_VISIBLE_DISTINCTNESS_INVALID",
    )
    require(
        proof.get("distinct_effective_signatures") == 640,
        "PROOF_EFFECTIVE_DISTINCTNESS_INVALID",
    )
    require(
        proof.get("distinct_semantic_signatures") == 640,
        "PROOF_SEMANTIC_DISTINCTNESS_INVALID",
    )
    require(proof.get("exact_duplicate_groups") == 0, "EXACT_DUPLICATES_PRESENT")
    require(
        proof.get("normalized_duplicate_groups") == 0,
        "NORMALIZED_DUPLICATES_PRESENT",
    )
    require(
        proof.get("semantic_duplicate_groups") == 0,
        "SEMANTIC_DUPLICATES_PRESENT",
    )
    require(
        proof.get("same_visible_different_answer_groups") == 0,
        "VISIBLE_ANSWER_COLLISION_PRESENT",
    )
    require(proof.get("within_form_duplicates") == 0, "WITHIN_FORM_DUPLICATES_PRESENT")
    require(proof.get("cross_form_duplicates") == 0, "CROSS_FORM_DUPLICATES_PRESENT")
    require(
        proof.get("prior_activity_direct_answer_leaks") == 0,
        "PRIOR_ACTIVITY_ANSWER_LEAK_PRESENT",
    )
    require(
        proof.get("global_640_distinct_runtime_question_proof") is True,
        "GLOBAL_640_DISTINCT_PROOF_NOT_PROVEN",
    )
    per_family = proof.get("per_family", {})
    require(set(per_family) == set(builder.TASK_FAMILIES), "PER_FAMILY_PROOF_KEYS_INVALID")
    for family, row in per_family.items():
        require(row["runtime_occurrences"] == 64, f"FAMILY_RUNTIME_COUNT:{family}")
        require(
            row["distinct_selected_item_ids"] == 64,
            f"FAMILY_SELECTED_DISTINCT:{family}",
        )
        require(
            row["distinct_visible_signatures"] == 64,
            f"FAMILY_VISIBLE_DISTINCT:{family}",
        )
        require(
            row["distinct_effective_signatures"] == 64,
            f"FAMILY_EFFECTIVE_DISTINCT:{family}",
        )
        require(
            row["distinct_semantic_signatures"] == 64,
            f"FAMILY_SEMANTIC_DISTINCT:{family}",
        )

    form_contract = q10.get("runtime_form_contract", {})
    require(form_contract.get("form_count") == 16, "FORM_COUNT_INVALID")
    require(form_contract.get("scene_slots_per_form") == 4, "SCENE_COUNT_INVALID")
    require(form_contract.get("task_family_count") == 10, "TASK_FAMILY_COUNT_INVALID")
    require(form_contract.get("activities_per_form") == 40, "FORM_ACTIVITY_COUNT_INVALID")
    require(form_contract.get("runtime_occurrence_count") == 640, "RUNTIME_FORM_COUNT_INVALID")
    require(
        form_contract.get("global_same_task_family_selected_item_reuse") is False,
        "GLOBAL_FAMILY_REUSE_PRESENT",
    )
    require(
        form_contract.get("global_640_distinct_runtime_question_proof") is True,
        "FORM_CONTRACT_GLOBAL_PROOF_INVALID",
    )

    bound = [
        row
        for row in runtime
        if row["sentence_asset_binding"]["status"]
        == "BOUND_CANONICAL_Q6_SENTENCE_ASSET"
    ]
    require(len(bound) == 128, "Q6_BOUND_COUNT_INVALID")
    require(
        Counter(row["task_family"] for row in bound)
        == Counter({"PRODUCTIVE_RESPONSE": 64, "TRANSFER": 64}),
        "Q6_BOUND_FAMILY_COUNT_INVALID",
    )

    progression = q10.get("progression_support_contract", {})
    notes = progression.get("learner_support_notes_by_stage", {})
    require(notes == builder.SUPPORT_NOTE_BY_STAGE, "PROGRESSION_SUPPORT_NOTES_INVALID")
    require(progression.get("support_reduction_proven") is True, "PROGRESSION_NOT_PROVEN")

    boundaries = payload.get("claim_boundaries", {})
    require(boundaries.get("q01_q08_mutated") is False, "Q01_Q08_MUTATED")
    require(boundaries.get("questionbank_items_created") is True, "R3_ITEMS_NOT_DECLARED")
    require(
        boundaries.get("runtime_authority_successor_created") is True,
        "R3_RUNTIME_SUCCESSOR_NOT_DECLARED",
    )
    require(boundaries.get("legacy_qbc02_items_deleted") is False, "LEGACY_DELETE_OVERCLAIM")
    require(boundaries.get("sentence_assets_created") is False, "SENTENCE_ASSET_MUTATION")
    require(
        boundaries.get("canonical_scene_authority_created") is False,
        "SCENE_AUTHORITY_MUTATION",
    )
    require(boundaries.get("learner_state_mutated") is False, "LEARNER_STATE_MUTATION")
    require(boundaries.get("scoring_authority_created") is False, "SCORING_MUTATION")
    require(boundaries.get("a2_unlocked") is False, "A2_UNLOCKED")

    return {
        "validation_status": "PASS",
        "error_count": 0,
        "q01_q08_preserved": True,
        "r3_new_items": len(r3_items),
        "runtime_occurrences": len(runtime),
        "distinct_visible_signatures": proof["distinct_visible_signatures"],
        "global_640_distinct_runtime_question_proof": True,
    }


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(
        candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE,
        "CANDIDATE_ROLE_INVALID",
    )
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "CANDIDATE_PAYLOAD_INVALID")
    validate_payload(payload)
    return validation_receipt(payload)


def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    require(
        approved.get("artifact_role") == policy_artifact.APPROVED_ROLE,
        "APPROVED_ROLE_INVALID",
    )
    require(approved.get("payload") == candidate.get("payload"), "APPROVED_PAYLOAD_DRIFT")
    return validate_payload(approved["payload"])


def main() -> int:
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validate_approved(candidate, approved)
    print(f"STATUS={report['validation_status']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"R3_NEW_ITEMS={report['r3_new_items']}")
    print(f"RUNTIME_OCCURRENCES={report['runtime_occurrences']}")
    print(
        "GLOBAL_640_DISTINCT_RUNTIME_QUESTION_PROOF="
        f"{report['global_640_distinct_runtime_question_proof']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
