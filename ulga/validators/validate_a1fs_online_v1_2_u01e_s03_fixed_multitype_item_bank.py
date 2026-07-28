#!/usr/bin/env python3
"""Validate the fixed Unit 01 multi-type candidate and approved item bank."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s03_fixed_multitype_item_bank as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_ONLINE_V1_2_U01E_S03_FIXED_MULTITYPE_ITEM_BANK_VALIDATOR"


class S03ValidationError(ValueError):
    """Fail-closed S03 item-bank validation error."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise S03ValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def expected_signature(item: Mapping[str, Any]) -> str:
    signature_payload = {
        "skill": item["skill"],
        "question_type": item["question_type"],
        "context_id": item["context_id"],
        "prompt": builder.normalized_text(item["prompt"]),
        "target_evp_sense_ids": item["target_evp_sense_ids"],
        "target_egp_row_ids": item["target_egp_row_ids"],
        "target_chunk_ids": item["target_chunk_ids"],
        "target_context_phrase_ids": item["target_context_phrase_ids"],
        "target_sentence_ids": item["target_sentence_ids"],
        "target_pattern_ids": item["target_pattern_ids"],
    }
    return builder.digest(signature_payload)


def validate_response_contract(item: Mapping[str, Any]) -> None:
    question_type = str(item["question_type"])
    skill = str(item["skill"])
    contract = item.get("response_contract")
    require(isinstance(contract, Mapping), f"response_contract_missing:{item['candidate_item_id']}")
    expected = builder.QUESTION_TYPE_CONTRACTS[question_type]
    require(
        item.get("interaction_contract") == expected,
        f"interaction_contract_invalid:{item['candidate_item_id']}",
    )
    if skill == "SPEAKING":
        require(item.get("correct_answer") is None, f"speaking_correct_answer_forbidden:{item['candidate_item_id']}")
        require(contract.get("capture_enabled") is False, f"speaking_capture_enabled:{item['candidate_item_id']}")
        require(contract.get("scoring_mode") == "FEATURE_RUBRIC", f"speaking_scoring_mode_invalid:{item['candidate_item_id']}")
        require(contract.get("rubric", {}).get("practice_only") is True, f"speaking_practice_boundary_invalid:{item['candidate_item_id']}")
        require(bool(item.get("acceptable_variants")), f"speaking_model_missing:{item['candidate_item_id']}")
        return
    require(contract.get("capture_enabled") is True, f"response_capture_disabled:{item['candidate_item_id']}")
    if question_type == "checkpoint_write":
        require(item.get("correct_answer") is None, f"checkpoint_write_exact_answer_forbidden:{item['candidate_item_id']}")
        require(contract.get("scoring_mode") == "FEATURE_RUBRIC", f"checkpoint_write_mode_invalid:{item['candidate_item_id']}")
        require(contract.get("human_review_fallback") is True, f"checkpoint_write_review_missing:{item['candidate_item_id']}")
        rubric = contract.get("rubric", {})
        for key in ("grammar_target_match", "meaning_matches_context", "complete_response"):
            require(rubric.get(key) is True, f"checkpoint_write_rubric_invalid:{item['candidate_item_id']}:{key}")
        return
    mode = str(expected["scoring_mode"])
    require(contract.get("scoring_mode") == mode, f"scoring_mode_invalid:{item['candidate_item_id']}")
    if mode == "EXACT_SEQUENCE":
        require(isinstance(item.get("correct_answer"), list), f"sequence_answer_invalid:{item['candidate_item_id']}")
        require(contract.get("accepted_sequence") == item.get("correct_answer"), f"accepted_sequence_invalid:{item['candidate_item_id']}")
        require(contract.get("accepted_texts") == [], f"sequence_accepted_text_forbidden:{item['candidate_item_id']}")
    else:
        require(isinstance(item.get("correct_answer"), str), f"text_answer_invalid:{item['candidate_item_id']}")
        require(item.get("correct_answer") in contract.get("accepted_texts", []), f"accepted_text_missing:{item['candidate_item_id']}")
        require(contract.get("accepted_sequence") == [], f"text_sequence_forbidden:{item['candidate_item_id']}")


def validate_payload(payload: Mapping[str, Any], safe_pack: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("item_bank_id") == builder.ITEM_BANK_ID, "item_bank_id_invalid")
    require(payload.get("item_bank_version") == builder.ITEM_BANK_VERSION, "item_bank_version_invalid")
    require(payload.get("unit_id") == builder.s02.s01.m01.UNIT_ID, "unit_identity_invalid")
    require(payload.get("level_scope") == ["A1"], "level_scope_invalid")
    require(payload.get("generation_mode") == "FIXED_OFFLINE_CANDIDATE_BANK", "generation_mode_invalid")
    require(payload.get("existing_activity_count") == builder.s02.EXISTING_ACTIVITY_COUNT, "existing_activity_count_invalid")
    require(payload.get("new_candidate_item_count") == builder.s02.NEW_CANDIDATE_TARGET_COUNT, "new_item_count_invalid")
    require(payload.get("target_total_activity_count") == builder.s02.TARGET_TOTAL_ACTIVITY_COUNT, "total_activity_count_invalid")
    require(payload.get("question_type_contracts") == builder.QUESTION_TYPE_CONTRACTS, "question_type_contracts_invalid")

    source = payload.get("source_context_pack", {})
    require(source.get("task_id") == builder.s02.TASK_ID, "source_context_task_invalid")
    require(source.get("safe_pack_sha256") == safe_pack.get("pack_sha256"), "source_safe_pack_binding_invalid")
    require(
        source.get("s01_approved_sha256")
        == safe_pack.get("source_identity", {}).get("s01_approved_sha256"),
        "source_s01_binding_invalid",
    )
    require(
        source.get("existing_semantic_signatures")
        == safe_pack.get("existing_semantic_signatures"),
        "source_existing_signatures_invalid",
    )

    items = payload.get("candidate_items")
    require(isinstance(items, list) and len(items) == builder.s02.NEW_CANDIDATE_TARGET_COUNT, "candidate_items_invalid")
    identities = [str(row.get("candidate_item_id") or "") for row in items]
    signatures = [str(row.get("semantic_signature") or "") for row in items]
    require(len(set(identities)) == len(items), "candidate_identity_duplicate")
    require(len(set(signatures)) == len(items), "candidate_signature_duplicate")
    require(not set(signatures).intersection(safe_pack.get("existing_semantic_signatures", [])), "existing_signature_collision")

    expected_fields = set(builder.s02.REQUIRED_CANDIDATE_OUTPUT_FIELDS)
    inventory = safe_pack.get("target_inventory", {})
    target_allowed = {
        "target_evp_sense_ids": set(inventory.get("evp_sense_ids", [])),
        "target_egp_row_ids": set(inventory.get("egp_row_ids", [])),
        "target_chunk_ids": set(inventory.get("canonical_chunk_ids", [])),
        "target_context_phrase_ids": set(inventory.get("context_phrase_ids", [])),
        "target_sentence_ids": set(inventory.get("sentence_ids", [])),
        "target_pattern_ids": set(inventory.get("pattern_ids", [])),
        "target_ket_prerequisite_node_ids": set(inventory.get("ket_prerequisite_node_ids", [])),
    }
    context_ids = {
        str(row["context_id"])
        for row in safe_pack.get("approved_contexts", [])
    }
    allowed_types = set(
        safe_pack.get("generation_policy", {}).get("allowed_question_types", [])
    )
    sentence_text_by_id = {
        str(row["sentence_id"]): str(row["text"])
        for row in safe_pack.get("approved_language_targets", {}).get("sentences", [])
    }
    for item in items:
        item_id = str(item.get("candidate_item_id") or "")
        require(expected_fields.issubset(item), f"required_item_field_missing:{item_id}")
        require(item.get("question_type") in allowed_types, f"question_type_not_allowed:{item_id}")
        require(item.get("context_id") in context_ids, f"context_not_approved:{item_id}")
        require(item.get("cambridge_stage") == "STARTERS", f"cambridge_stage_invalid:{item_id}")
        require(item.get("cambridge_capability_refs") == [], f"unproven_cambridge_capability_ref:{item_id}")
        require(item.get("assessment_pattern_ref") == item.get("question_type"), f"assessment_pattern_mismatch:{item_id}")
        require(item.get("target_ket_prerequisite_node_ids") == [], f"unproven_ket_node_ref:{item_id}")
        require(item.get("learner_delivery_status") == "CANDIDATE_NOT_RUNTIME", f"learner_delivery_status_invalid:{item_id}")
        require(item.get("runtime_generation_used") is False, f"runtime_generation_used:{item_id}")
        require(item.get("semantic_signature") == expected_signature(item), f"semantic_signature_invalid:{item_id}")
        for field, allowed in target_allowed.items():
            refs = item.get(field)
            require(isinstance(refs, list), f"target_field_not_list:{item_id}:{field}")
            require(set(refs).issubset(allowed), f"target_ref_outside_inventory:{item_id}:{field}")
        require(bool(item.get("target_evp_sense_ids")), f"evp_target_missing:{item_id}")
        require(bool(item.get("target_egp_row_ids")), f"egp_target_missing:{item_id}")
        require(bool(item.get("target_pattern_ids")), f"pattern_target_missing:{item_id}")
        evidence = item.get("answerability_evidence", {})
        sentence_id = str(evidence.get("evidence_sentence_id") or "")
        sentence_text = str(evidence.get("evidence_sentence") or "")
        require(sentence_id in item.get("target_sentence_ids", []), f"evidence_sentence_not_targeted:{item_id}")
        require(sentence_text_by_id.get(sentence_id) == sentence_text, f"evidence_sentence_identity_invalid:{item_id}")
        require(sentence_text in str(item.get("stimulus", {}).get("body") or ""), f"evidence_not_in_stimulus:{item_id}")
        require(evidence.get("answer_present_in_supplied_context") is True, f"answerability_flag_invalid:{item_id}")
        require(isinstance(item.get("source_refs"), list) and len(item["source_refs"]) == 2, f"source_refs_invalid:{item_id}")
        validate_response_contract(item)

    actual_counts = {
        "skill": dict(sorted(Counter(row["skill"] for row in items).items())),
        "context": dict(sorted(Counter(row["context_id"] for row in items).items())),
        "question_type": dict(sorted(Counter(row["question_type"] for row in items).items())),
        "learning_role": dict(sorted(Counter(row["learning_role"] for row in items).items())),
        "support_level": dict(sorted(Counter(row["support_level"] for row in items).items())),
    }
    require(actual_counts == payload.get("distribution_counts"), "distribution_readback_invalid")
    require(actual_counts["skill"] == builder.s02.NEW_SKILL_DISTRIBUTION, "skill_distribution_invalid")
    require(actual_counts["context"] == builder.s02.NEW_CONTEXT_DISTRIBUTION, "context_distribution_invalid")
    require(actual_counts["question_type"] == builder.s02.NEW_QUESTION_TYPE_DISTRIBUTION, "question_type_distribution_invalid")
    require(actual_counts["learning_role"] == builder.s02.LEARNING_ROLE_DISTRIBUTION, "learning_role_distribution_invalid")
    require(actual_counts["support_level"] == builder.s02.SUPPORT_LEVEL_DISTRIBUTION, "support_level_distribution_invalid")

    admission = payload.get("admission_policy", {})
    require(admission.get("candidate_only") is True, "candidate_only_invalid")
    require(admission.get("independent_validation_required") is True, "independent_validation_not_required")
    require(admission.get("approved_bank_required_before_runtime") is True, "approved_bank_not_required")
    require(admission.get("runtime_free_generation_allowed") is False, "runtime_free_generation_allowed")
    boundaries = payload.get("claim_boundaries", {})
    for key in (
        "learner_private_state_used",
        "learner_database_written",
        "response_contract_database_written",
        "runtime_bundle_written",
        "existing_asset_identity_changed",
        "generated_at_learner_runtime",
        "ket_coverage_claimed",
        "cambridge_granular_capability_claimed",
        "unit02_modified",
        "audio_enabled",
        "speaking_capture_enabled",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"boundary_invalid:{key}")
    encoded = json.dumps(payload, ensure_ascii=False).casefold()
    for forbidden in ('"learner_id"', '"attempt_id"', '"response_json"', '"raw_raz_text"', '"raw_ket_text"'):
        require(forbidden not in encoded, f"private_or_raw_source_leak:{forbidden}")
    return validation_receipt(payload)


def validate_candidate(
    candidate: Mapping[str, Any], safe_pack: Mapping[str, Any]
) -> dict[str, Any]:
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "candidate_role_invalid")
    require(candidate.get("learner_facing") is False, "candidate_learner_facing_forbidden")
    policy_artifact.verify_artifact_digest(candidate)
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "candidate_payload_missing")
    return validate_payload(payload, safe_pack)


def validate_approved(
    candidate: Mapping[str, Any],
    approved: Mapping[str, Any],
    safe_pack: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        receipt = validate_candidate(candidate, safe_pack)
        require(approved.get("artifact_role") == policy_artifact.APPROVED_ROLE, "approved_role_invalid")
        require(approved.get("learner_facing") is False, "approved_learner_facing_forbidden")
        require(approved.get("admission", {}).get("status") == "APPROVED", "approved_status_invalid")
        require(approved.get("admission", {}).get("decision_ref") == builder.DECISION_REF, "approved_decision_invalid")
        require(approved.get("payload") == candidate.get("payload"), "approved_payload_drift")
        require(
            approved.get("source_bindings", {}).get("candidate_artifact_sha256")
            == candidate.get("artifact_sha256"),
            "approved_candidate_binding_invalid",
        )
        require(
            receipt.get("receipt_sha256")
            in {row.get("receipt_sha256") for row in approved.get("validation_receipts", [])},
            "approved_validation_receipt_missing",
        )
        policy_artifact.verify_artifact_digest(approved)
    except (
        S03ValidationError,
        builder.S03ItemBankError,
        policy_artifact.ContentPolicyBuildError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    payload = candidate.get("payload", {})
    items = payload.get("candidate_items", []) if isinstance(payload, Mapping) else []
    return {
        "validator_id": VALIDATOR_ID,
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "item_bank_id": builder.ITEM_BANK_ID,
        "item_bank_version": builder.ITEM_BANK_VERSION,
        "new_candidate_item_count": len(items),
        "target_total_activity_count": builder.s02.TARGET_TOTAL_ACTIVITY_COUNT,
        "distribution_counts": deepcopy(payload.get("distribution_counts", {})) if isinstance(payload, Mapping) else {},
        "hidden_answers_in_safe_report": False,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else builder.TASK_ID,
    }
