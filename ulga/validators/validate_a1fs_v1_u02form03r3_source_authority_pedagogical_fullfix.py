#!/usr/bin/env python3
"""Validate the Unit02 R4R1 Transfer-stage pedagogical FullFix."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u02form03r3_source_authority_pedagogical_fullfix_and_global_distinct_runtime
    as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U02FORM03R4R1_TRANSFER_STAGE_FULLFIX_VALIDATOR"


class U02Form03R4R1ValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise U02Form03R4R1ValidationError(code)


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
    require(preservation.get("baseline_sha256") == preservation.get("r3_sha256"), "Q01_Q08_DIGEST_DRIFT")

    identity = payload.get("forms01_12_runtime_identity_preservation", {})
    require(identity.get("preserved") is True, "FORMS01_12_NOT_PRESERVED")
    require(identity.get("runtime_occurrence_count") == 480, "FORMS01_12_COUNT_INVALID")
    require(identity.get("baseline_sha256") == identity.get("r4r1_sha256"), "FORMS01_12_IDENTITY_DIGEST_DRIFT")

    q9 = payload.get("q9_task_angle_question_type", {})
    summary = q9.get("post_materialization_summary", {})
    require(summary.get("task_family_count") == 10, "Q9_FAMILY_COUNT_INVALID")
    require(summary.get("global_640_distinct_runtime_question_proof") is True, "Q9_GLOBAL_DISTINCTNESS_NOT_PROVEN")
    require(summary.get("forms01_12_runtime_identity_preserved") is True, "Q9_FORMS01_12_NOT_PRESERVED")
    require(summary.get("forms13_16_task_specific_transfer_instruction_proven") is True, "Q9_TRANSFER_INSTRUCTION_NOT_PROVEN")
    require(summary.get("forms13_16_real_transfer_demand_proven") is True, "Q9_TRANSFER_DEMAND_NOT_PROVEN")

    q10 = payload.get("q10_questionbank_capacity_runtime", {})
    inventory = q10.get("inventory_summary", {})
    require(inventory.get("unit01_reference_only_item_count") == builder.EXPECTED_UNIT01_REFERENCE_ITEMS, "UNIT01_COUNT_INVALID")
    require(inventory.get("unit02_approved_item_count") == builder.EXPECTED_UNIT02_APPROVED_ITEMS, "UNIT02_COUNT_INVALID")
    require(inventory.get("cumulative_catalog_item_count") == builder.EXPECTED_CUMULATIVE_ITEMS, "CUMULATIVE_COUNT_INVALID")
    require(inventory.get("r4r1_transfer_stage_policy_bound_items") == builder.R4R1_TRANSFER_ITEM_COUNT, "R4R1_ITEM_COUNT_SUMMARY_INVALID")
    require(inventory.get("legacy_qbc02_items_deleted") is False, "LEGACY_ITEMS_DELETED")
    require(inventory.get("parallel_questionbank_created") is False, "PARALLEL_BANK_CREATED")

    items = q10.get("unit02_approved_items")
    require(isinstance(items, list) and len(items) == builder.EXPECTED_UNIT02_APPROVED_ITEMS, "APPROVED_ITEM_LIST_INVALID")
    require(len({row["item_id"] for row in items}) == len(items), "APPROVED_ITEM_ID_COLLISION")

    r3_items = [row for row in items if str(row["item_id"]).startswith("U02FORM03R3-")]
    require(len(r3_items) == builder.R3_NEW_ITEMS, "R3_HISTORY_ITEM_COUNT_INVALID")

    r4_items = [row for row in items if str(row["item_id"]).startswith("U02FORM03R4R1-")]
    require(len(r4_items) == builder.R4R1_TRANSFER_ITEM_COUNT, "R4R1_TRANSFER_ITEM_COUNT_INVALID")
    require(Counter(row["task_family"] for row in r4_items) == Counter({family: builder.R4R1_TRANSFER_ITEMS_PER_FAMILY for family in builder.TASK_FAMILIES}), "R4R1_TRANSFER_ITEM_FAMILY_DISTRIBUTION_INVALID")
    require(len({row["semantic_signature"] for row in r4_items}) == len(r4_items), "R4R1_TRANSFER_ITEM_SIGNATURE_COLLISION")
    require(all(row.get("r4r1_transfer_demand") == "NEW_CONTEXT_APPLICATION" for row in r4_items), "R4R1_TRANSFER_DEMAND_MARKER_INVALID")
    require(all(row.get("support_level") == "TRANSFER_NEW_CONTEXT_NO_RULE_HINT" for row in r4_items), "R4R1_TRANSFER_SUPPORT_LEVEL_INVALID")

    runtime = q10.get("runtime_occurrences")
    require(isinstance(runtime, list) and len(runtime) == 640, "RUNTIME_COUNT_INVALID")
    require(len({row["runtime_occurrence_id"] for row in runtime}) == 640, "RUNTIME_ID_COLLISION")
    require(len({row["selected_item_id"] for row in runtime}) == 640, "RUNTIME_SELECTED_ITEM_COLLISION")
    require(Counter(row["task_family"] for row in runtime) == Counter({family: 64 for family in builder.TASK_FAMILIES}), "RUNTIME_FAMILY_DISTRIBUTION_INVALID")
    require(all(len(row["candidate_ids"]) == 3 for row in runtime), "RUNTIME_CANDIDATE_COUNT_INVALID")
    require(all(len(set(row["candidate_ids"])) == 3 for row in runtime), "RUNTIME_CANDIDATE_DISTINCTNESS_INVALID")
    require(all(row["selected_item_id"] == row["candidate_ids"][0] for row in runtime), "RUNTIME_SELECTION_RULE_INVALID")
    require(all(str(row["target_singular"]).casefold() not in builder.RUNTIME_RESTRICTED_SURFACES for row in runtime), "RESTRICTED_SURFACE_SELECTED")
    require(not any(str(row["selected_item_id"]).startswith("U02QBC02-") for row in runtime), "LEGACY_QBC02_ITEM_SELECTED")

    forms01_12 = [row for row in runtime if int(row["form_number"]) <= 12]
    transfer_runtime = [row for row in runtime if int(row["form_number"]) in builder.R4R1_TRANSFER_FORMS]
    require(len(forms01_12) == 480, "FORMS01_12_RUNTIME_COUNT_INVALID")
    require(len(transfer_runtime) == 160, "TRANSFER_RUNTIME_COUNT_INVALID")
    require(not any(str(row["selected_item_id"]).startswith("U02FORM03R4R1-") for row in forms01_12), "R4R1_ITEM_LEAKED_TO_FORMS01_12")
    require(all(str(row["selected_item_id"]).startswith("U02FORM03R4R1-") for row in transfer_runtime), "TRANSFER_RUNTIME_NOT_FULLY_CUT_OVER")
    require(Counter(row["task_family"] for row in transfer_runtime) == Counter({family: 16 for family in builder.TASK_FAMILIES}), "TRANSFER_RUNTIME_FAMILY_COUNT_INVALID")
    require({family: {row["learner_support_note"] for row in transfer_runtime if row["task_family"] == family} for family in builder.TASK_FAMILIES} == {family: {builder.TRANSFER_NOTE_BY_FAMILY[family]} for family in builder.TASK_FAMILIES}, "TRANSFER_TASK_SPECIFIC_NOTES_INVALID")
    require("Apply the plural rule in a new sentence without a hint." not in {row["learner_support_note"] for row in transfer_runtime}, "STALE_GENERIC_TRANSFER_NOTE_PRESENT")

    proof = q10.get("global_distinctness_proof", {})
    for key in ("runtime_occurrence_count", "distinct_runtime_occurrence_ids", "distinct_selected_item_ids", "distinct_visible_signatures", "distinct_effective_signatures", "distinct_semantic_signatures"):
        require(proof.get(key) == 640, f"GLOBAL_PROOF_COUNT_INVALID:{key}")
    for key in ("exact_duplicate_groups", "normalized_duplicate_groups", "semantic_duplicate_groups", "same_visible_different_answer_groups", "within_form_duplicates", "cross_form_duplicates", "prior_activity_direct_answer_leaks"):
        require(proof.get(key) == 0, f"GLOBAL_PROOF_NONZERO:{key}")
    require(proof.get("global_640_distinct_runtime_question_proof") is True, "GLOBAL_640_DISTINCT_PROOF_NOT_PROVEN")
    for family, row in proof.get("per_family", {}).items():
        require(row["runtime_occurrences"] == 64, f"FAMILY_RUNTIME_COUNT:{family}")
        require(row["distinct_selected_item_ids"] == 64, f"FAMILY_SELECTED_DISTINCT:{family}")
        require(row["distinct_visible_signatures"] == 64, f"FAMILY_VISIBLE_DISTINCT:{family}")
        require(row["distinct_effective_signatures"] == 64, f"FAMILY_EFFECTIVE_DISTINCT:{family}")
        require(row["distinct_semantic_signatures"] == 64, f"FAMILY_SEMANTIC_DISTINCT:{family}")

    bound = [row for row in runtime if row["sentence_asset_binding"]["status"] == "BOUND_CANONICAL_Q6_SENTENCE_ASSET"]
    require(len(bound) == 128, "Q6_BOUND_COUNT_INVALID")
    require(Counter(row["task_family"] for row in bound) == Counter({"PRODUCTIVE_RESPONSE": 64, "TRANSFER": 64}), "Q6_BOUND_FAMILY_COUNT_INVALID")

    progression = q10.get("progression_support_contract", {})
    require(progression.get("transfer_task_specific_notes_by_family") == builder.TRANSFER_NOTE_BY_FAMILY, "TRANSFER_NOTE_MAP_INVALID")
    require(progression.get("support_reduction_proven") is True, "SUPPORT_REDUCTION_NOT_PROVEN")
    require(progression.get("transfer_demand_proven") is True, "TRANSFER_DEMAND_NOT_PROVEN")
    require(progression.get("independent_transfer_topology_distinct") is True, "TRANSFER_TOPOLOGY_NOT_DISTINCT")
    require(progression.get("transfer_stage_topology_change_count") == 160, "TRANSFER_TOPOLOGY_CHANGE_COUNT_INVALID")

    transfer_summary = payload.get("r4r1_transfer_fullfix", {})
    require(transfer_summary.get("transfer_runtime_occurrences") == 160, "TRANSFER_SUMMARY_RUNTIME_INVALID")
    require(transfer_summary.get("transfer_new_items") == builder.R4R1_TRANSFER_ITEM_COUNT, "TRANSFER_SUMMARY_ITEM_COUNT_INVALID")
    require(transfer_summary.get("task_specific_instruction_count") == 10, "TRANSFER_SUMMARY_NOTE_COUNT_INVALID")
    require(transfer_summary.get("task_topology_change_count") == 160, "TRANSFER_SUMMARY_TOPOLOGY_INVALID")
    require(transfer_summary.get("real_transfer_demand_proven") is True, "TRANSFER_SUMMARY_DEMAND_NOT_PROVEN")

    boundaries = payload.get("claim_boundaries", {})
    require(boundaries.get("q01_q08_mutated") is False, "Q01_Q08_MUTATED")
    require(boundaries.get("forms01_12_runtime_identity_mutated") is False, "FORMS01_12_MUTATED")
    require(boundaries.get("forms13_16_runtime_identity_mutated") is True, "FORMS13_16_NOT_DECLARED_MUTATED")
    require(boundaries.get("sentence_assets_created") is False, "SENTENCE_ASSET_MUTATION")
    require(boundaries.get("canonical_scene_authority_created") is False, "SCENE_AUTHORITY_MUTATION")
    require(boundaries.get("learner_state_mutated") is False, "LEARNER_STATE_MUTATION")
    require(boundaries.get("scoring_authority_created") is False, "SCORING_MUTATION")
    require(boundaries.get("a2_unlocked") is False, "A2_UNLOCKED")

    return {
        "validation_status": "PASS",
        "error_count": 0,
        "q01_q08_preserved": True,
        "forms01_12_runtime_identity_preserved": True,
        "r4r1_transfer_items": len(r4_items),
        "transfer_runtime_occurrences": len(transfer_runtime),
        "transfer_topology_change_count": progression["transfer_stage_topology_change_count"],
        "global_640_distinct_runtime_question_proof": True,
    }


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "CANDIDATE_ROLE_INVALID")
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "CANDIDATE_PAYLOAD_INVALID")
    validate_payload(payload)
    return validation_receipt(payload)


def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    require(approved.get("artifact_role") == policy_artifact.APPROVED_ROLE, "APPROVED_ROLE_INVALID")
    require(approved.get("payload") == candidate.get("payload"), "APPROVED_PAYLOAD_DRIFT")
    return validate_payload(approved["payload"])


def main() -> int:
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validate_approved(candidate, approved)
    print(f"STATUS={report['validation_status']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"R4R1_TRANSFER_ITEMS={report['r4r1_transfer_items']}")
    print("FORMS01_12_RUNTIME_IDENTITY_PRESERVED=" f"{report['forms01_12_runtime_identity_preserved']}")
    print("TRANSFER_RUNTIME_OCCURRENCES=" f"{report['transfer_runtime_occurrences']}")
    print("TRANSFER_TOPOLOGY_CHANGE_COUNT=" f"{report['transfer_topology_change_count']}")
    print("GLOBAL_640_DISTINCT_RUNTIME_QUESTION_PROOF=" f"{report['global_640_distinct_runtime_question_proof']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
