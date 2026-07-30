#!/usr/bin/env python3
"""Validate full Unit01 candidate generation and approved variant admission."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB01_UNIT01_PATTERN_FAMILY_APPROVED_VARIANT_POOL_VALIDATOR"
EXPECTED_REASONS = {
    builder.REJECT_ADJ: 270,
    builder.REJECT_CONTEXT: 132,
    builder.REJECT_VERY: 183,
}
EXPECTED_APPROVED_SKILLS = {"READING": 166, "SPEAKING": 25, "WRITING": 97}
EXPECTED_APPROVED_PATTERNS = {
    builder.PATTERN_NOUN: 252,
    builder.PATTERN_ADJECTIVE: 24,
    builder.PATTERN_VERY: 12,
}


class VariantPoolValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise VariantPoolValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def expected_signature(item: Mapping[str, Any]) -> str:
    return builder.digest(
        {
            "family": item["pattern_family_id"],
            "structure": item["candidate_structure"],
            "context": item["context_id"],
            "slots": item["lexical_slots"],
            "prompt": item["prompt"],
            "stimulus": item["stimulus"],
            "options": item["options"],
            "answer": item["correct_answer"],
        }
    )


def independent_decision(item: Mapping[str, Any]) -> dict[str, Any]:
    structure = str(item["candidate_structure"])
    slots = item["lexical_slots"]
    noun = str(slots["noun"])
    adjective = str(slots.get("adjective") or "")
    family_id = str(item["pattern_family_id"])
    context_id = item.get("context_id")
    if structure == "ADJECTIVE":
        approved = (adjective, noun) in builder.direct_pairs()
        return {
            "status": "AUTO_APPROVED" if approved else "AUTO_REJECTED",
            "reason_codes": [
                "APPROVED_CONTRACT_ADJECTIVE_NOUN_PAIR" if approved else builder.REJECT_ADJ
            ],
        }
    if structure == "VERY":
        approved = (adjective, noun) in builder.very_pairs()
        return {
            "status": "AUTO_APPROVED" if approved else "AUTO_REJECTED",
            "reason_codes": [
                "APPROVED_CONTRACT_VERY_ADJECTIVE_NOUN_PAIR"
                if approved
                else builder.REJECT_VERY
            ],
        }
    if context_id:
        approved = str(context_id) in builder.CONTEXT_APPROVALS[noun]
        return {
            "status": "AUTO_APPROVED" if approved else "AUTO_REJECTED",
            "reason_codes": [
                "UNIT01_CONTEXT_NOUN_COMPATIBILITY_APPROVED"
                if approved
                else builder.REJECT_CONTEXT
            ],
        }
    reason = (
        "APPROVED_CONTRACT_NOUN_PHRASE"
        if family_id == "U01-PF10-SPEAK-NOUN"
        else "ACTIVE_NOUN_AUTHORITY_BOUND"
    )
    return {"status": "AUTO_APPROVED", "reason_codes": [reason]}


def expected_pattern_egp(structure: str) -> tuple[str, str]:
    if structure == "NOUN":
        return builder.PATTERN_NOUN, builder.contract.CORE_EGP_ROWS[0]
    if structure == "ADJECTIVE":
        return builder.PATTERN_ADJECTIVE, builder.contract.CORE_EGP_ROWS[1]
    if structure == "VERY":
        return builder.PATTERN_VERY, builder.contract.GUIDED_EGP_ROWS[0]
    raise VariantPoolValidationError(f"UNKNOWN_STRUCTURE:{structure}")


def validate_response(item: Mapping[str, Any], approved: bool) -> None:
    item_id = str(item["item_id"])
    response = item.get("response_contract")
    require(isinstance(response, Mapping), f"RESPONSE_CONTRACT_MISSING:{item_id}")
    speaking = item["skill"] == "SPEAKING"
    require(response.get("capture_enabled") is (not speaking), f"CAPTURE_MODE_INVALID:{item_id}")
    require(item.get("assessment_eligible") is (approved and not speaking), f"ASSESSMENT_FLAG_INVALID:{item_id}")
    require(item.get("reassessment_eligible") is (approved and not speaking), f"REASSESSMENT_FLAG_INVALID:{item_id}")
    if speaking:
        require(item.get("correct_answer") is None, f"SPEAKING_ANSWER_FORBIDDEN:{item_id}")
        require(bool(item.get("accepted_answers")), f"SPEAKING_MODEL_MISSING:{item_id}")
        require(response.get("scoring_mode") == "FEATURE_RUBRIC", f"SPEAKING_MODE_INVALID:{item_id}")
        require(response.get("rubric", {}).get("practice_only") is True, f"SPEAKING_BOUNDARY_INVALID:{item_id}")
    elif item["scoring_mode"] == "EXACT_SEQUENCE":
        require(response.get("accepted_sequence") == item["correct_answer"], f"SEQUENCE_INVALID:{item_id}")
        require(response.get("accepted_texts") == [], f"SEQUENCE_TEXT_INVALID:{item_id}")
    else:
        require(item["correct_answer"] in response.get("accepted_texts", []), f"TEXT_ANSWER_INVALID:{item_id}")
        require(response.get("accepted_sequence") == [], f"TEXT_SEQUENCE_INVALID:{item_id}")


def validate_item(
    item: Mapping[str, Any],
    *,
    family_by_id: Mapping[str, Mapping[str, Any]],
    noun_senses: Mapping[str, str],
    adjective_senses: Mapping[str, str],
) -> None:
    item_id = str(item.get("item_id") or "")
    require(item.get("unit_id") == builder.UNIT_ID, f"ITEM_UNIT_INVALID:{item_id}")
    family = family_by_id.get(str(item.get("pattern_family_id") or ""))
    require(family is not None, f"ITEM_FAMILY_UNKNOWN:{item_id}")
    require(item.get("skill") == family["skill"], f"ITEM_SKILL_INVALID:{item_id}")
    require(item.get("question_type") == family["question_type"], f"ITEM_TYPE_INVALID:{item_id}")
    structure = str(item.get("candidate_structure") or "")
    pattern, egp = expected_pattern_egp(structure)
    require(item.get("unit_pattern_ids") == [pattern], f"ITEM_PATTERN_INVALID:{item_id}")
    require(item.get("target_egp_row_ids") == [egp], f"ITEM_EGP_INVALID:{item_id}")
    require(
        not set(item.get("unit_pattern_ids", [])).intersection(
            builder.FORBIDDEN_DEMONSTRATIVE_PATTERN_IDS
        ),
        f"DEMONSTRATIVE_PATTERN_LEAK:{item_id}",
    )
    slots = item.get("lexical_slots")
    require(isinstance(slots, Mapping), f"LEXICAL_SLOTS_INVALID:{item_id}")
    noun = str(slots.get("noun") or "")
    require(noun in noun_senses, f"NOUN_OUTSIDE_ACTIVE_CONTRACT:{item_id}")
    senses = set(item.get("target_evp_sense_ids", []))
    require(noun_senses[noun] in senses, f"NOUN_SENSE_MISSING:{item_id}")
    adjective = str(slots.get("adjective") or "")
    if structure in {"ADJECTIVE", "VERY"}:
        require(adjective in adjective_senses, f"ADJECTIVE_OUTSIDE_ACTIVE_CONTRACT:{item_id}")
        require(adjective_senses[adjective] in senses, f"ADJECTIVE_SENSE_MISSING:{item_id}")
        require(len(senses) == 2, f"ADJECTIVE_SENSE_SHAPE_INVALID:{item_id}")
    else:
        require(not adjective, f"NOUN_ITEM_ADJECTIVE_LEAK:{item_id}")
        require(len(senses) == 1, f"NOUN_SENSE_SHAPE_INVALID:{item_id}")
    require(item.get("semantic_signature") == expected_signature(item), f"SIGNATURE_INVALID:{item_id}")
    require(item.get("runtime_generation_used") is False, f"RUNTIME_GENERATION_USED:{item_id}")
    require(item.get("audio_required") is False, f"AUDIO_INVALID:{item_id}")
    require(item.get("human_review_required") is False, f"HUMAN_REVIEW_INVALID:{item_id}")
    require(item.get("learner_delivery_status") == "NOT_RUNTIME_CONNECTED", f"RUNTIME_STATUS_INVALID:{item_id}")
    decision = independent_decision(item)
    require(item.get("admission_proposal") == decision, f"ADMISSION_DECISION_INVALID:{item_id}")
    approved = decision["status"] == "AUTO_APPROVED"
    require(item.get("learner_visible_capable") is approved, f"LEARNER_FLAG_INVALID:{item_id}")
    validate_response(item, approved)


def distribution(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        "family": dict(sorted(Counter(row["pattern_family_id"] for row in rows).items())),
        "skill": dict(sorted(Counter(row["skill"] for row in rows).items())),
        "question_type": dict(sorted(Counter(row["question_type"] for row in rows).items())),
        "unit_pattern": dict(
            sorted(Counter(pattern for row in rows for pattern in row["unit_pattern_ids"]).items())
        ),
    }


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    identity = payload.get("bank_identity", {})
    require(identity.get("bank_id") == builder.BANK_ID, "BANK_INVALID")
    require(identity.get("bank_version") == builder.BANK_VERSION, "BANK_VERSION_INVALID")
    require(identity.get("level_scope") == ["A1"], "LEVEL_INVALID")
    require(identity.get("learner_runtime_free_generation_allowed") is False, "FREE_GENERATION_ALLOWED")
    require(payload.get("design_space_capacity") == builder.design_space_capacity(), "CAPACITY_INVALID")
    baseline = payload.get("baseline_bank_contract", {})
    require(baseline.get("baseline_activity_count") == 24, "BASELINE_INVALID")
    require(baseline.get("baseline_items_copied_into_variant_pool") is False, "BASELINE_COPY_INVALID")
    families = payload.get("pattern_family_contracts")
    require(families == builder.family_rows(), "FAMILY_CONTRACT_INVALID")
    family_by_id = {row["family_id"]: row for row in families}
    candidates = payload.get("candidate_items")
    approved = payload.get("approved_items")
    require(isinstance(candidates, list) and len(candidates) == 873, "CANDIDATE_COUNT_INVALID")
    require(isinstance(approved, list) and len(approved) == 288, "APPROVED_COUNT_INVALID")
    require(len({row["item_id"] for row in candidates}) == 873, "DUPLICATE_ITEM_ID")
    require(len({row["semantic_signature"] for row in candidates}) == 873, "DUPLICATE_SIGNATURE")
    noun_senses = {
        lemma: sense
        for lemma, sense, _gloss, _indefinite, _definite, _group in builder.contract.ACTIVE_NOUNS
    }
    adjective_senses = {
        lemma: sense
        for lemma, sense, _guide, _row, _gloss, _memory, _group
        in builder.contract.ACTIVE_ADJECTIVES
    }
    for item in candidates:
        validate_item(
            item,
            family_by_id=family_by_id,
            noun_senses=noun_senses,
            adjective_senses=adjective_senses,
        )
    independently_approved = [
        row for row in candidates if independent_decision(row)["status"] == "AUTO_APPROVED"
    ]
    require(approved == independently_approved, "APPROVED_SUBSET_DRIFT")
    rejected = [
        row for row in candidates if independent_decision(row)["status"] == "AUTO_REJECTED"
    ]
    reason_counts = dict(
        sorted(
            Counter(
                code
                for row in rejected
                for code in independent_decision(row)["reason_codes"]
            ).items()
        )
    )
    require(reason_counts == EXPECTED_REASONS, "REJECTION_REASON_INVALID")
    readback = payload.get("admission_readback", {})
    require(readback.get("candidate_count") == 873, "READBACK_CANDIDATE_INVALID")
    require(readback.get("approved_count") == 288, "READBACK_APPROVED_INVALID")
    require(readback.get("rejected_count") == 585, "READBACK_REJECTED_INVALID")
    require(readback.get("human_review_count") == 0, "READBACK_HUMAN_INVALID")
    require(readback.get("rejection_reason_counts") == reason_counts, "READBACK_REASONS_INVALID")
    distributions = payload.get("distribution_counts", {})
    require(distributions.get("candidate") == distribution(candidates), "CANDIDATE_DISTRIBUTION_INVALID")
    require(distributions.get("approved") == distribution(approved), "APPROVED_DISTRIBUTION_INVALID")
    require(distributions["approved"]["skill"] == EXPECTED_APPROVED_SKILLS, "SKILL_DISTRIBUTION_INVALID")
    require(distributions["approved"]["unit_pattern"] == EXPECTED_APPROVED_PATTERNS, "PATTERN_DISTRIBUTION_INVALID")
    counts = payload.get("count_semantics", {})
    require(counts.get("canonical_language_asset_combination_count") == 25, "LANGUAGE_COUNT_INVALID")
    require(counts.get("canonical_approved_task_count") == 288, "TASK_COUNT_INVALID")
    require(counts.get("runtime_variant_count") == 0, "RUNTIME_COUNT_INVALID")
    coverage = payload.get("coverage_denominators", {})
    all_active = set(noun_senses.values()) | set(adjective_senses.values())
    actual_evp = {sense for row in approved for sense in row["target_evp_sense_ids"]}
    actual_egp = {row_id for row in approved for row_id in row["target_egp_row_ids"]}
    require(actual_evp == all_active and coverage.get("active_evp_sense_count") == 22, "EVP_COVERAGE_INVALID")
    require(len(actual_egp) == 3 and coverage.get("exercise_covered_egp_row_count") == 3, "EGP_COVERAGE_INVALID")
    require(coverage.get("learner_mastery_claimed") is False, "MASTERY_CLAIM_INVALID")
    session = payload.get("session_assembly_metadata", {})
    require(session.get("runtime_status") == "NOT_CONNECTED_METADATA_ONLY", "SESSION_RUNTIME_INVALID")
    require(session.get("pool_source") == "VALIDATOR_APPROVED_ITEMS_ONLY", "SESSION_SOURCE_INVALID")
    require(sum(session.get("selection_quota", {}).values()) == 10, "SESSION_QUOTA_INVALID")
    admission = payload.get("admission_policy", {})
    for key in (
        "independent_validation_required",
        "semantic_dedup_required",
        "complete_strict_candidate_space_required",
        "rejected_candidates_retained_with_reason_codes",
        "approved_contract_phrases_only_for_adjective_combinations",
        "approved_context_noun_matrix_required",
        "approved_bank_required_before_runtime",
    ):
        require(admission.get(key) is True, f"ADMISSION_POLICY_INVALID:{key}")
    require(admission.get("unvalidated_variant_delivery_allowed") is False, "UNVALIDATED_ALLOWED")
    require(admission.get("learner_time_generation_allowed") is False, "LEARNER_GENERATION_ALLOWED")
    boundaries = payload.get("claim_boundaries", {})
    for key in (
        "global_pattern_authority_modified",
        "existing_pattern_ids_redefined",
        "demonstrative_patterns_in_unit01",
        "unit02_to_unit24_modified",
        "learner_database_written",
        "runtime_bundle_written",
        "runtime_variants_materialized",
        "audio_enabled",
        "speaking_capture_enabled",
        "a2_unlocked",
        "learner_mastery_claimed",
        "ket_granular_node_claimed",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")
    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_STEP_INVALID")
    return validation_receipt(payload)


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "CANDIDATE_ROLE_INVALID")
    require(candidate.get("learner_facing") is False, "CANDIDATE_LEARNER_FACING_INVALID")
    policy_artifact.verify_artifact_digest(candidate)
    source = candidate.get("source_bindings", {})
    require(
        source.get("unit01_approved_contract_sha256") == builder.APPROVED_CONTRACT_SHA256,
        "SOURCE_CONTRACT_INVALID",
    )
    require(source.get("u01data05b_task_id") == builder.pattern_authority.TASK_ID, "SOURCE_PATTERN_INVALID")
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "CANDIDATE_PAYLOAD_MISSING")
    return validate_payload(payload)


def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        receipt = validate_candidate(candidate)
        require(approved.get("artifact_role") == policy_artifact.APPROVED_ROLE, "APPROVED_ROLE_INVALID")
        require(approved.get("learner_facing") is False, "APPROVED_LEARNER_FACING_INVALID")
        require(approved.get("admission", {}).get("status") == "APPROVED", "APPROVED_STATUS_INVALID")
        require(approved.get("admission", {}).get("decision_ref") == builder.DECISION_REF, "DECISION_INVALID")
        require(approved.get("payload") == candidate.get("payload"), "APPROVED_PAYLOAD_DRIFT")
        require(
            approved.get("source_bindings", {}).get("candidate_artifact_sha256")
            == candidate.get("artifact_sha256"),
            "CANDIDATE_BINDING_INVALID",
        )
        require(
            approved.get("validation_receipts")
            == [
                {
                    "validator_id": receipt["validator_id"],
                    "status": "PASS",
                    "receipt_sha256": receipt["receipt_sha256"],
                }
            ],
            "RECEIPT_INVALID",
        )
        policy_artifact.verify_artifact_digest(approved)
        validate_payload(approved["payload"])
    except (
        VariantPoolValidationError,
        policy_artifact.ContentPolicyBuildError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    payload = approved.get("payload", {})
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "candidate_artifact_sha256": candidate.get("artifact_sha256"),
        "approved_artifact_sha256": approved.get("artifact_sha256"),
        "candidate_count": len(payload.get("candidate_items", [])),
        "approved_variant_count": len(payload.get("approved_items", [])),
        "rejected_candidate_count": payload.get("admission_readback", {}).get("rejected_count", 0),
        "pattern_family_count": len(payload.get("pattern_family_contracts", [])),
    }
