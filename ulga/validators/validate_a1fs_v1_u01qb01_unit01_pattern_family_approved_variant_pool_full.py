#!/usr/bin/env python3
"""Validate the Unit01 full V2 approved variant pool."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as seed,
)
from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool_full as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as seed_validator,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB01_UNIT01_PATTERN_FAMILY_APPROVED_VARIANT_POOL_FULL_V2_VALIDATOR"

class FullVariantPoolValidationError(ValueError):
    """Fail-closed Unit01 full-pool validation error."""

def require(condition: bool, code: str) -> None:
    if not condition:
        raise FullVariantPoolValidationError(code)

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
            "pattern": item["unit_pattern_ids"][0],
            "prompt": item["prompt"],
            "stimulus": item["stimulus"],
            "options": item["options"],
            "correct_answer": item["correct_answer"],
            "evp": item["target_evp_sense_ids"],
            "egp": item["target_egp_row_ids"],
        }
    )

def allowed_active_senses() -> set[str]:
    nouns = {row["evp_sense_id"] for row in seed.active_nouns()}
    adjectives = {
        sense
        for _lemma, sense, _guideword, _row, _gloss, _memory, _group
        in seed.contract_builder.ACTIVE_ADJECTIVES
    }
    return nouns | adjectives

def direct_pairs() -> set[frozenset[str]]:
    return seed_validator.direct_pair_sense_sets()

def very_pairs() -> set[frozenset[str]]:
    return seed_validator.very_pair_sense_sets()

def validate_response_contract(item: Mapping[str, Any]) -> None:
    item_id = str(item["item_id"])
    contract = item.get("response_contract")
    require(isinstance(contract, Mapping), f"RESPONSE_CONTRACT_MISSING:{item_id}")
    speaking = item.get("skill") == "SPEAKING"
    require(contract.get("capture_enabled") is (not speaking), f"CAPTURE_MODE_INVALID:{item_id}")
    require(item.get("speaking_capture_enabled") is False, f"SPEAKING_CAPTURE_FLAG_INVALID:{item_id}")
    if speaking:
        require(item.get("correct_answer") is None, f"SPEAKING_EXACT_ANSWER_FORBIDDEN:{item_id}")
        require(bool(item.get("accepted_answers")), f"SPEAKING_MODEL_MISSING:{item_id}")
        require(contract.get("scoring_mode") == "FEATURE_RUBRIC", f"SPEAKING_MODE_INVALID:{item_id}")
        require(contract.get("rubric", {}).get("practice_only") is True, f"SPEAKING_PRACTICE_INVALID:{item_id}")
        require(item.get("assessment_eligible") is False, f"SPEAKING_ASSESSMENT_INVALID:{item_id}")
        require(item.get("reassessment_eligible") is False, f"SPEAKING_REASSESSMENT_INVALID:{item_id}")
        return
    require(item.get("assessment_eligible") is True, f"ASSESSMENT_ELIGIBILITY_INVALID:{item_id}")
    require(item.get("reassessment_eligible") is True, f"REASSESSMENT_ELIGIBILITY_INVALID:{item_id}")
    mode = str(item.get("scoring_mode") or "")
    require(contract.get("scoring_mode") == mode, f"SCORING_MODE_DRIFT:{item_id}")
    if mode == "EXACT_SEQUENCE":
        require(isinstance(item.get("correct_answer"), list), f"SEQUENCE_ANSWER_INVALID:{item_id}")
        require(contract.get("accepted_sequence") == item.get("correct_answer"), f"SEQUENCE_CONTRACT_INVALID:{item_id}")
        require(contract.get("accepted_texts") == [], f"SEQUENCE_TEXT_FORBIDDEN:{item_id}")
    else:
        require(isinstance(item.get("correct_answer"), str), f"TEXT_ANSWER_INVALID:{item_id}")
        require(item.get("correct_answer") in contract.get("accepted_texts", []), f"TEXT_ANSWER_NOT_ACCEPTED:{item_id}")
        require(contract.get("accepted_sequence") == [], f"TEXT_SEQUENCE_FORBIDDEN:{item_id}")

def validate_expansion_item(item: Mapping[str, Any]) -> None:
    item_id = str(item["item_id"])
    family_id = str(item["pattern_family_id"])
    family = next(
        (row for row in builder.EXPANSION_FAMILY_CONTRACTS if row["family_id"] == family_id),
        None,
    )
    require(family is not None, f"EXPANSION_FAMILY_UNKNOWN:{item_id}")
    require(item.get("skill") == family["skill"], f"ITEM_SKILL_INVALID:{item_id}")
    require(item.get("question_type") == family["question_type"], f"ITEM_TYPE_INVALID:{item_id}")
    require(item.get("unit_pattern_ids") == [family["pattern_id"]], f"ITEM_PATTERN_INVALID:{item_id}")
    require(not set(item["unit_pattern_ids"]).intersection(builder.FORBIDDEN_DEMONSTRATIVE_PATTERN_IDS), f"DEMONSTRATIVE_PATTERN_LEAK:{item_id}")
    require(set(item.get("target_evp_sense_ids", [])).issubset(allowed_active_senses()), f"EVP_TARGET_OUTSIDE_ACTIVE_UNIT01:{item_id}")
    require(bool(item.get("target_evp_sense_ids")), f"EVP_TARGET_MISSING:{item_id}")
    require(item.get("runtime_generation_used") is False, f"RUNTIME_GENERATION_USED:{item_id}")
    require(item.get("audio_required") is False, f"AUDIO_REQUIREMENT_INVALID:{item_id}")
    require(item.get("human_review_required") is False, f"HUMAN_REVIEW_UNEXPECTED:{item_id}")
    require(item.get("learner_delivery_status") == "NOT_RUNTIME_CONNECTED", f"RUNTIME_STATUS_INVALID:{item_id}")
    require(item.get("semantic_signature") == expected_signature(item), f"SEMANTIC_SIGNATURE_INVALID:{item_id}")
    validate_response_contract(item)

    pattern = family["pattern_id"]
    if pattern == builder.PATTERN_NOUN:
        require(len(item["target_evp_sense_ids"]) == 1, f"NOUN_SENSE_SHAPE_INVALID:{item_id}")
        require(item["target_egp_row_ids"] == [seed.contract_builder.CORE_EGP_ROWS[0]], f"NOUN_EGP_INVALID:{item_id}")
        noun = next(
            row for row in seed.active_nouns()
            if row["evp_sense_id"] == item["target_evp_sense_ids"][0]
        )
        lemma = noun["lemma"]
        phrase = noun["indefinite_phrase"]
        article = seed.article_from_phrase(phrase)
        searchable = " ".join(
            [
                str(item.get("prompt") or ""),
                str(item.get("stimulus") or ""),
                " ".join(str(value) for value in item.get("options", [])),
                " ".join(str(value) for value in item.get("correct_answer", []))
                if isinstance(item.get("correct_answer"), list)
                else str(item.get("correct_answer") or ""),
                " ".join(str(value) for value in item.get("accepted_answers", [])),
            ]
        ).lower()
        require(lemma in searchable, f"NOUN_LEMMA_NOT_REALIZED:{item_id}")
        if "KNOWN" in family_id:
            require(item.get("transfer_eligible") is True, f"KNOWN_TRANSFER_INVALID:{item_id}")
            require(phrase in str(item.get("stimulus") or ""), f"FIRST_MENTION_MISSING:{item_id}")
            require(
                item.get("correct_answer") in {"the", noun["definite_phrase"]},
                f"KNOWN_ANSWER_INVALID:{item_id}",
            )
        elif item.get("skill") == "SPEAKING":
            require(
                any(phrase in str(value).lower() for value in item.get("accepted_answers", [])),
                f"NOUN_SPEAKING_MODEL_INVALID:{item_id}",
            )
        elif item.get("scoring_mode") == "EXACT_SEQUENCE":
            sequence = [str(value).lower() for value in item.get("correct_answer", [])]
            require(article in sequence and lemma in sequence, f"NOUN_SEQUENCE_INVALID:{item_id}")
        else:
            require(item.get("correct_answer") == article, f"NOUN_ARTICLE_ANSWER_INVALID:{item_id}")
    elif pattern == builder.PATTERN_ADJECTIVE:
        require(len(item["target_evp_sense_ids"]) == 2, f"ADJ_SENSE_SHAPE_INVALID:{item_id}")
        require(frozenset(item["target_evp_sense_ids"]) in direct_pairs(), f"ADJ_PAIR_NOT_APPROVED:{item_id}")
        require(item["target_egp_row_ids"] == [seed.contract_builder.CORE_EGP_ROWS[1]], f"ADJ_EGP_INVALID:{item_id}")
    else:
        require(len(item["target_evp_sense_ids"]) == 2, f"VERY_SENSE_SHAPE_INVALID:{item_id}")
        require(frozenset(item["target_evp_sense_ids"]) in very_pairs(), f"VERY_PAIR_NOT_APPROVED:{item_id}")
        require(item["target_egp_row_ids"] == [seed.contract_builder.GUIDED_EGP_ROWS[0]], f"VERY_EGP_INVALID:{item_id}")

def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_VERSION_INVALID")
    require(payload.get("program_id") == builder.PROGRAM_ID, "PROGRAM_ID_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_ID_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")

    identity = payload.get("bank_identity", {})
    require(identity.get("bank_id") == builder.BANK_ID, "BANK_ID_INVALID")
    require(identity.get("bank_version") == builder.BANK_VERSION, "BANK_VERSION_INVALID")
    require(identity.get("unit_id") == builder.UNIT_ID, "UNIT_ID_INVALID")
    require(identity.get("level_scope") == ["A1"], "LEVEL_SCOPE_INVALID")
    require(identity.get("learner_runtime_free_generation_allowed") is False, "RUNTIME_GENERATION_ALLOWED")

    source_seed = payload.get("source_seed_contract", {})
    require(source_seed.get("seed_task_id") == seed.TASK_ID, "SEED_TASK_INVALID")
    require(source_seed.get("seed_item_count") == 109, "SEED_COUNT_INVALID")
    require(source_seed.get("seed_is_runtime_authority") is False, "SEED_RUNTIME_AUTHORITY_INVALID")
    require(source_seed.get("full_v2_bank_is_runtime_candidate_authority") is True, "FULL_AUTHORITY_FLAG_INVALID")

    capacity = payload.get("design_space_capacity", {})
    require(capacity == builder.design_space_capacity(), "CAPACITY_READBACK_INVALID")
    require(capacity.get("theoretical_raw_combinatorial_capacity") == 944, "RAW_CAPACITY_INVALID")
    require(capacity.get("seed_authority_grounded_count") == 109, "SEED_CAPACITY_INVALID")
    require(capacity.get("expansion_authority_grounded_count") == 199, "EXPANSION_CAPACITY_INVALID")
    require(capacity.get("authority_grounded_candidate_count") == 308, "FULL_CAPACITY_INVALID")
    require(capacity.get("theoretical_candidates_not_admitted_without_additional_authority") == 636, "EXCLUDED_CAPACITY_INVALID")

    families = payload.get("pattern_family_contracts")
    require(isinstance(families, list), "FAMILY_CONTRACTS_NOT_LIST")
    family_counts_expected = {
        row["family_id"]: row["expected_count"]
        for row in builder.FAMILY_CONTRACTS
    }
    require(len(family_counts_expected) == 32, "FAMILY_COUNT_INVALID")

    items = payload.get("candidate_items")
    require(isinstance(items, list) and len(items) == 308, "ITEM_COUNT_INVALID")
    ids = [str(row.get("item_id") or "") for row in items]
    signatures = [str(row.get("semantic_signature") or "") for row in items]
    require(len(set(ids)) == len(items), "DUPLICATE_ITEM_ID")
    require(len(set(signatures)) == len(items), "DUPLICATE_SEMANTIC_SIGNATURE")

    seed_ids = {row["item_id"] for row in seed.build_items()}
    full_ids = set(ids)
    require(seed_ids.issubset(full_ids), "SEED_ITEMS_NOT_PRESERVED")
    require(len(full_ids - seed_ids) == 199, "EXPANSION_ID_COUNT_INVALID")

    actual_family_counts = dict(sorted(Counter(row["pattern_family_id"] for row in items).items()))
    require(actual_family_counts == dict(sorted(family_counts_expected.items())), "FAMILY_DISTRIBUTION_INVALID")
    skill_counts = dict(sorted(Counter(row["skill"] for row in items).items()))
    require(skill_counts == {"READING": 123, "SPEAKING": 50, "WRITING": 135}, "SKILL_DISTRIBUTION_INVALID")
    type_counts = dict(sorted(Counter(row["question_type"] for row in items).items()))
    require(
        type_counts
        == {
            "context_match": 16,
            "error_discrimination": 41,
            "gap_fill": 66,
            "guided_sentence": 50,
            "multiple_choice": 66,
            "word_order": 69,
        },
        "QUESTION_TYPE_DISTRIBUTION_INVALID",
    )
    pattern_counts = dict(
        sorted(Counter(pattern for row in items for pattern in row["unit_pattern_ids"]).items())
    )
    require(
        pattern_counts
        == {
            builder.PATTERN_ADJECTIVE: 60,
            builder.PATTERN_NOUN: 224,
            builder.PATTERN_VERY: 24,
        },
        "PATTERN_DISTRIBUTION_INVALID",
    )

    seed_items = [row for row in items if row["item_id"] in seed_ids]
    seed_payload = seed.candidate_payload()
    seed_payload["candidate_items"] = seed_items
    seed_payload["distribution_counts"] = {
        "family": dict(sorted(Counter(row["pattern_family_id"] for row in seed_items).items())),
        "skill": dict(sorted(Counter(row["skill"] for row in seed_items).items())),
        "question_type": dict(sorted(Counter(row["question_type"] for row in seed_items).items())),
        "unit_pattern": dict(sorted(Counter(p for row in seed_items for p in row["unit_pattern_ids"]).items())),
    }
    seed_validator.validate_payload(seed_payload)

    for item in items:
        if item["item_id"] not in seed_ids:
            validate_expansion_item(item)

    distributions = payload.get("distribution_counts", {})
    require(distributions.get("family") == actual_family_counts, "FAMILY_READBACK_INVALID")
    require(distributions.get("skill") == skill_counts, "SKILL_READBACK_INVALID")
    require(distributions.get("question_type") == type_counts, "TYPE_READBACK_INVALID")
    require(distributions.get("unit_pattern") == pattern_counts, "PATTERN_READBACK_INVALID")

    coverage = payload.get("coverage_denominators", {})
    actual_evp = sorted({sense for row in items for sense in row["target_evp_sense_ids"]})
    actual_egp = sorted({target for row in items for target in row["target_egp_row_ids"]})
    require(coverage.get("active_evp_sense_count") == 22, "EVP_COUNT_INVALID")
    require(coverage.get("active_evp_sense_ids") == actual_evp, "EVP_IDS_INVALID")
    require(set(actual_evp) == allowed_active_senses(), "EVP_COVERAGE_INCOMPLETE")
    require(coverage.get("exercise_covered_egp_row_count") == 3, "EGP_COUNT_INVALID")
    require(coverage.get("exercise_covered_egp_row_ids") == actual_egp, "EGP_IDS_INVALID")
    require(coverage.get("a1_egp_denominator") == 109, "EGP_DENOMINATOR_INVALID")
    require(coverage.get("learner_mastery_claimed") is False, "LEARNER_MASTERY_CLAIMED")
    require(coverage.get("ket_canonical_prerequisite_node_claimed") is False, "KET_NODE_CLAIMED")

    session = payload.get("session_assembly_metadata", {})
    require(session.get("runtime_status") == "NOT_CONNECTED_METADATA_ONLY", "SESSION_STATUS_INVALID")
    require(session.get("session_size") == 10, "SESSION_SIZE_INVALID")
    require(session.get("pool_source") == "APPROVED_FULL_V2_VARIANTS_ONLY", "SESSION_POOL_INVALID")
    require(sum(session.get("selection_quota", {}).values()) == 10, "SESSION_QUOTA_INVALID")

    boundaries = payload.get("claim_boundaries", {})
    for key in (
        "global_pattern_authority_modified",
        "existing_pattern_ids_redefined",
        "demonstrative_patterns_in_unit01",
        "unit02_to_unit24_modified",
        "learner_database_written",
        "runtime_bundle_written",
        "audio_enabled",
        "speaking_capture_enabled",
        "a2_unlocked",
        "learner_mastery_claimed",
        "ket_granular_node_claimed",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")
    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_SHORT_STEP_INVALID")
    return validation_receipt(payload)

def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "CANDIDATE_ROLE_INVALID")
    require(candidate.get("learner_facing") is False, "CANDIDATE_LEARNER_FACING_FORBIDDEN")
    policy_artifact.verify_artifact_digest(candidate)
    source = candidate.get("source_bindings", {})
    require(source.get("seed_task_id") == seed.TASK_ID, "SOURCE_SEED_TASK_INVALID")
    require(source.get("seed_item_count") == 109, "SOURCE_SEED_COUNT_INVALID")
    require(source.get("unit01_approved_contract_sha256") == builder.APPROVED_CONTRACT_SHA256, "SOURCE_CONTRACT_INVALID")
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
        require(approved.get("admission", {}).get("decision_ref") == builder.DECISION_REF, "APPROVED_DECISION_INVALID")
        require(approved.get("payload") == candidate.get("payload"), "APPROVED_PAYLOAD_DRIFT")
        require(
            approved.get("source_bindings", {}).get("candidate_artifact_sha256")
            == candidate.get("artifact_sha256"),
            "APPROVED_CANDIDATE_BINDING_INVALID",
        )
        require(
            approved.get("validation_receipts")
            == [{"validator_id": receipt["validator_id"], "status": "PASS", "receipt_sha256": receipt["receipt_sha256"]}],
            "APPROVED_RECEIPT_INVALID",
        )
        policy_artifact.verify_artifact_digest(approved)
        validate_payload(approved["payload"])
    except (
        FullVariantPoolValidationError,
        seed_validator.VariantPoolValidationError,
        policy_artifact.ContentPolicyBuildError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "candidate_artifact_sha256": candidate.get("artifact_sha256"),
        "approved_artifact_sha256": approved.get("artifact_sha256"),
        "approved_variant_count": len(approved.get("payload", {}).get("candidate_items", [])),
        "pattern_family_count": len(approved.get("payload", {}).get("pattern_family_contracts", [])),
    }
