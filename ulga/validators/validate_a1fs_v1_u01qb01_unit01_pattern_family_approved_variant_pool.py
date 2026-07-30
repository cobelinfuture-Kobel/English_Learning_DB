#!/usr/bin/env python3
"""Validate the Unit01 pattern-family approved variant pool."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB01_UNIT01_PATTERN_FAMILY_APPROVED_VARIANT_POOL_VALIDATOR"


class VariantPoolValidationError(ValueError):
    """Fail-closed Unit01 variant-pool validation error."""


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
    signature_payload = {
        "family": item["pattern_family_id"],
        "pattern": item["unit_pattern_ids"][0],
        "prompt": item["prompt"],
        "stimulus": item["stimulus"],
        "options": item["options"],
        "correct_answer": item["correct_answer"],
        "evp": item["target_evp_sense_ids"],
        "egp": item["target_egp_row_ids"],
    }
    return builder.digest(signature_payload)


def noun_rows() -> dict[str, dict[str, str]]:
    return {row["evp_sense_id"]: row for row in builder.active_nouns()}


def adjective_rows() -> dict[str, dict[str, str]]:
    return {
        sense: {"lemma": lemma, "evp_sense_id": sense, "memory_phrase": memory}
        for lemma, sense, _guideword, _row, _gloss, memory, _group
        in builder.contract_builder.ACTIVE_ADJECTIVES
    }


def direct_pair_sense_sets() -> set[frozenset[str]]:
    return {
        frozenset({row["adjective_evp_sense_id"], row["noun_evp_sense_id"]})
        for row in builder.direct_adjective_phrases()
    }


def very_pair_sense_sets() -> set[frozenset[str]]:
    return {
        frozenset({row["adjective_evp_sense_id"], row["noun_evp_sense_id"]})
        for row in builder.very_adjective_phrases()
    }


def validate_response_contract(item: Mapping[str, Any]) -> None:
    item_id = str(item["item_id"])
    contract = item.get("response_contract")
    require(isinstance(contract, Mapping), f"RESPONSE_CONTRACT_MISSING:{item_id}")
    require(
        contract.get("capture_enabled") is (item.get("skill") != "SPEAKING"),
        f"CAPTURE_MODE_INVALID:{item_id}",
    )
    require(item.get("speaking_capture_enabled") is False, f"SPEAKING_CAPTURE_FLAG_INVALID:{item_id}")
    if item.get("skill") == "SPEAKING":
        require(item.get("correct_answer") is None, f"SPEAKING_EXACT_ANSWER_FORBIDDEN:{item_id}")
        require(bool(item.get("accepted_answers")), f"SPEAKING_MODEL_MISSING:{item_id}")
        require(contract.get("scoring_mode") == "FEATURE_RUBRIC", f"SPEAKING_MODE_INVALID:{item_id}")
        require(contract.get("rubric", {}).get("practice_only") is True, f"SPEAKING_PRACTICE_BOUNDARY_INVALID:{item_id}")
        require(item.get("assessment_eligible") is False, f"SPEAKING_ASSESSMENT_INVALID:{item_id}")
        require(item.get("reassessment_eligible") is False, f"SPEAKING_REASSESSMENT_INVALID:{item_id}")
        return
    require(item.get("assessment_eligible") is True, f"ASSESSMENT_ELIGIBILITY_INVALID:{item_id}")
    require(item.get("reassessment_eligible") is True, f"REASSESSMENT_ELIGIBILITY_INVALID:{item_id}")
    scoring_mode = str(item.get("scoring_mode") or "")
    require(contract.get("scoring_mode") == scoring_mode, f"SCORING_MODE_DRIFT:{item_id}")
    if scoring_mode == "EXACT_SEQUENCE":
        require(isinstance(item.get("correct_answer"), list), f"SEQUENCE_ANSWER_INVALID:{item_id}")
        require(contract.get("accepted_sequence") == item.get("correct_answer"), f"SEQUENCE_CONTRACT_INVALID:{item_id}")
        require(contract.get("accepted_texts") == [], f"SEQUENCE_TEXT_FORBIDDEN:{item_id}")
    else:
        require(isinstance(item.get("correct_answer"), str), f"TEXT_ANSWER_INVALID:{item_id}")
        require(item.get("correct_answer") in contract.get("accepted_texts", []), f"TEXT_ANSWER_NOT_ACCEPTED:{item_id}")
        require(contract.get("accepted_sequence") == [], f"TEXT_SEQUENCE_FORBIDDEN:{item_id}")


def validate_noun_family(item: Mapping[str, Any], noun_by_sense: Mapping[str, Mapping[str, str]]) -> None:
    item_id = str(item["item_id"])
    senses = item.get("target_evp_sense_ids")
    require(isinstance(senses, list) and len(senses) == 1, f"NOUN_SENSE_SHAPE_INVALID:{item_id}")
    noun = noun_by_sense.get(str(senses[0]))
    require(noun is not None, f"NOUN_SENSE_OUTSIDE_ACTIVE_CONTRACT:{item_id}")
    lemma = str(noun["lemma"])
    phrase = str(noun["indefinite_phrase"])
    article = builder.article_from_phrase(phrase)
    family = str(item["pattern_family_id"])
    if family == "U01-PF01-AAN-NOUN-GAP":
        require(item["correct_answer"] == article, f"NOUN_GAP_ANSWER_INVALID:{item_id}")
        require(item["prompt"] == f"Complete with a or an: ___ {lemma}", f"NOUN_GAP_PROMPT_INVALID:{item_id}")
    elif family == "U01-PF02-AAN-NOUN-CHOICE":
        require(item["stimulus"] == f"___ {lemma}", f"NOUN_CHOICE_STIMULUS_INVALID:{item_id}")
        require(item["options"] == ["a", "an"], f"NOUN_CHOICE_OPTIONS_INVALID:{item_id}")
        require(item["correct_answer"] == article, f"NOUN_CHOICE_ANSWER_INVALID:{item_id}")
    elif family == "U01-PF03-AAN-NOUN-ERROR":
        require(item["correct_answer"] == phrase, f"NOUN_ERROR_ANSWER_INVALID:{item_id}")
        require(
            set(item["options"]) == {phrase, f"{builder.wrong_indefinite(article)} {lemma}"},
            f"NOUN_ERROR_OPTIONS_INVALID:{item_id}",
        )
    elif family == "U01-PF04-ARTICLE-NOUN-ORDER":
        require(item["correct_answer"] == [article, lemma], f"NOUN_ORDER_ANSWER_INVALID:{item_id}")
    elif family == "U01-PF08-FIRST-TO-KNOWN-THE":
        require(lemma in builder.DISCOURSE_NOUNS, f"DISCOURSE_NOUN_NOT_CURATED:{item_id}")
        require(item["correct_answer"] == "the", f"DISCOURSE_THE_ANSWER_INVALID:{item_id}")
        require(item["transfer_eligible"] is True, f"DISCOURSE_TRANSFER_FLAG_INVALID:{item_id}")
        require(phrase in item["stimulus"], f"DISCOURSE_FIRST_MENTION_MISSING:{item_id}")
        require(f"___ {lemma}" in item["stimulus"], f"DISCOURSE_SECOND_MENTION_MISSING:{item_id}")
    elif family == "U01-PF09-SPEAK-AAN-NOUN":
        require(item["accepted_answers"] == [phrase], f"NOUN_SPEAKING_MODEL_INVALID:{item_id}")
    else:
        raise VariantPoolValidationError(f"UNEXPECTED_NOUN_FAMILY:{item_id}:{family}")


def validate_adjective_family(
    item: Mapping[str, Any], *, allowed_pairs: set[frozenset[str]], very: bool
) -> None:
    item_id = str(item["item_id"])
    senses = item.get("target_evp_sense_ids")
    require(isinstance(senses, list) and len(senses) == 2, f"ADJECTIVE_SENSE_SHAPE_INVALID:{item_id}")
    require(
        frozenset(str(value) for value in senses) in allowed_pairs,
        f"ADJECTIVE_NOUN_PAIR_NOT_APPROVED:{item_id}",
    )
    if very:
        require(item["unit_pattern_ids"] == [builder.PATTERN_VERY], f"VERY_PATTERN_INVALID:{item_id}")
        require(item["target_egp_row_ids"] == [builder.contract_builder.GUIDED_EGP_ROWS[0]], f"VERY_EGP_INVALID:{item_id}")
        require(item["scoring_mode"] == "EXACT_SEQUENCE", f"VERY_SCORING_INVALID:{item_id}")
        require(item["correct_answer"][0:2] == ["a", "very"], f"VERY_SEQUENCE_INVALID:{item_id}")
    else:
        require(item["unit_pattern_ids"] == [builder.PATTERN_ADJECTIVE], f"ADJECTIVE_PATTERN_INVALID:{item_id}")
        require(item["target_egp_row_ids"] == [builder.contract_builder.CORE_EGP_ROWS[1]], f"ADJECTIVE_EGP_INVALID:{item_id}")


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

    capacity = payload.get("design_space_capacity", {})
    require(capacity == builder.design_space_capacity(), "DESIGN_SPACE_CAPACITY_INVALID")
    require(capacity.get("raw_combinatorial_capacity") == 944, "RAW_CAPACITY_INVALID")
    require(capacity.get("strict_prevalidation_capacity") == 848, "STRICT_CAPACITY_INVALID")
    require(capacity.get("materialized_authority_grounded_candidate_count") == 109, "MATERIALIZED_CAPACITY_INVALID")

    baseline = payload.get("baseline_bank_contract", {})
    require(baseline.get("baseline_activity_count") == 24, "BASELINE_COUNT_INVALID")
    require(baseline.get("baseline_items_copied_into_variant_pool") is False, "BASELINE_COPY_DETECTED")
    require(baseline.get("routine_session_delivery_uses_baseline_by_default") is False, "BASELINE_RUNTIME_DEFAULT_INVALID")

    family_rows = payload.get("pattern_family_contracts")
    require(family_rows == [deepcopy(row) for row in builder.FAMILY_CONTRACTS], "FAMILY_CONTRACT_DRIFT")
    family_by_id = {str(row["family_id"]): row for row in family_rows}
    require(len(family_by_id) == 10, "FAMILY_COUNT_INVALID")

    items = payload.get("candidate_items")
    require(isinstance(items, list) and len(items) == builder.EXPECTED_ITEM_COUNT, "ITEM_COUNT_INVALID")
    identities = [str(row.get("item_id") or "") for row in items]
    signatures = [str(row.get("semantic_signature") or "") for row in items]
    require(len(set(identities)) == len(items), "DUPLICATE_ITEM_ID")
    require(len(set(signatures)) == len(items), "DUPLICATE_SEMANTIC_SIGNATURE")

    expected_family_counts = {row["family_id"]: row["expected_count"] for row in builder.FAMILY_CONTRACTS}
    actual_family_counts = dict(sorted(Counter(row["pattern_family_id"] for row in items).items()))
    require(actual_family_counts == dict(sorted(expected_family_counts.items())), "FAMILY_DISTRIBUTION_INVALID")
    actual_skill_counts = dict(sorted(Counter(row["skill"] for row in items).items()))
    require(actual_skill_counts == {"READING": 40, "SPEAKING": 22, "WRITING": 47}, "SKILL_DISTRIBUTION_INVALID")
    actual_type_counts = dict(sorted(Counter(row["question_type"] for row in items).items()))
    require(
        actual_type_counts
        == {
            "context_match": 8,
            "error_discrimination": 16,
            "gap_fill": 22,
            "guided_sentence": 22,
            "multiple_choice": 16,
            "word_order": 25,
        },
        "QUESTION_TYPE_DISTRIBUTION_INVALID",
    )
    actual_pattern_counts = dict(
        sorted(Counter(pattern for row in items for pattern in row["unit_pattern_ids"]).items())
    )
    require(
        actual_pattern_counts
        == {builder.PATTERN_ADJECTIVE: 18, builder.PATTERN_NOUN: 88, builder.PATTERN_VERY: 3},
        "PATTERN_DISTRIBUTION_INVALID",
    )

    noun_by_sense = noun_rows()
    adjective_by_sense = adjective_rows()
    allowed_active_senses = set(noun_by_sense) | set(adjective_by_sense)
    direct_pairs = direct_pair_sense_sets()
    very_pairs = very_pair_sense_sets()
    expected_patterns = {builder.PATTERN_NOUN, builder.PATTERN_ADJECTIVE, builder.PATTERN_VERY}
    for item in items:
        item_id = str(item.get("item_id") or "")
        require(item.get("unit_id") == builder.UNIT_ID, f"ITEM_UNIT_INVALID:{item_id}")
        family_id = str(item.get("pattern_family_id") or "")
        family = family_by_id.get(family_id)
        require(family is not None, f"ITEM_FAMILY_UNKNOWN:{item_id}")
        require(item.get("skill") == family["skill"], f"ITEM_SKILL_INVALID:{item_id}")
        require(item.get("question_type") == family["question_type"], f"ITEM_TYPE_INVALID:{item_id}")
        require(item.get("unit_pattern_ids") == [family["pattern_id"]], f"ITEM_PATTERN_FAMILY_MISMATCH:{item_id}")
        require(set(item.get("unit_pattern_ids", [])).issubset(expected_patterns), f"ITEM_PATTERN_OUTSIDE_UNIT_LOCAL_AUTHORITY:{item_id}")
        require(
            not set(item.get("unit_pattern_ids", [])).intersection(builder.FORBIDDEN_DEMONSTRATIVE_PATTERN_IDS),
            f"DEMONSTRATIVE_PATTERN_LEAK:{item_id}",
        )
        require(set(item.get("target_evp_sense_ids", [])).issubset(allowed_active_senses), f"EVP_TARGET_OUTSIDE_ACTIVE_UNIT01:{item_id}")
        require(bool(item.get("target_evp_sense_ids")), f"EVP_TARGET_MISSING:{item_id}")
        require(item.get("runtime_generation_used") is False, f"RUNTIME_GENERATION_USED:{item_id}")
        require(item.get("audio_required") is False, f"AUDIO_REQUIREMENT_INVALID:{item_id}")
        require(item.get("human_review_required") is False, f"HUMAN_REVIEW_UNEXPECTED:{item_id}")
        require(item.get("learner_delivery_status") == "NOT_RUNTIME_CONNECTED", f"RUNTIME_STATUS_INVALID:{item_id}")
        require(item.get("semantic_signature") == expected_signature(item), f"SEMANTIC_SIGNATURE_INVALID:{item_id}")
        validate_response_contract(item)
        if family["pattern_id"] == builder.PATTERN_NOUN:
            require(item.get("target_egp_row_ids") == [builder.contract_builder.CORE_EGP_ROWS[0]], f"NOUN_EGP_INVALID:{item_id}")
            validate_noun_family(item, noun_by_sense)
        elif family["pattern_id"] == builder.PATTERN_ADJECTIVE:
            validate_adjective_family(item, allowed_pairs=direct_pairs, very=False)
        elif family["pattern_id"] == builder.PATTERN_VERY:
            validate_adjective_family(item, allowed_pairs=very_pairs, very=True)

    distributions = payload.get("distribution_counts", {})
    require(distributions.get("family") == actual_family_counts, "FAMILY_READBACK_INVALID")
    require(distributions.get("skill") == actual_skill_counts, "SKILL_READBACK_INVALID")
    require(distributions.get("question_type") == actual_type_counts, "QUESTION_TYPE_READBACK_INVALID")
    require(distributions.get("unit_pattern") == actual_pattern_counts, "PATTERN_READBACK_INVALID")

    coverage = payload.get("coverage_denominators", {})
    actual_evp = sorted({sense for row in items for sense in row["target_evp_sense_ids"]})
    actual_egp = sorted({egp for row in items for egp in row["target_egp_row_ids"]})
    require(coverage.get("active_evp_sense_count") == 22, "ACTIVE_EVP_COUNT_INVALID")
    require(coverage.get("active_evp_sense_ids") == actual_evp, "ACTIVE_EVP_IDS_INVALID")
    require(set(actual_evp) == allowed_active_senses, "ACTIVE_EVP_COVERAGE_INCOMPLETE")
    require(coverage.get("exercise_covered_egp_row_count") == 3, "EGP_COVERAGE_COUNT_INVALID")
    require(coverage.get("exercise_covered_egp_row_ids") == actual_egp, "EGP_COVERAGE_IDS_INVALID")
    require(
        set(actual_egp)
        == {
            builder.contract_builder.CORE_EGP_ROWS[0],
            builder.contract_builder.CORE_EGP_ROWS[1],
            builder.contract_builder.GUIDED_EGP_ROWS[0],
        },
        "EGP_TARGET_SET_INVALID",
    )
    require(coverage.get("a1_egp_denominator") == 109, "EGP_DENOMINATOR_INVALID")
    require(coverage.get("learner_mastery_claimed") is False, "LEARNER_MASTERY_CLAIMED")
    require(coverage.get("ket_canonical_prerequisite_node_claimed") is False, "KET_NODE_CLAIMED")
    require(coverage.get("semantic_ket_prerequisite_capability") == "ARTICLE_NOUN_PHRASE_CONTROL", "KET_SEMANTIC_CAPABILITY_INVALID")

    session = payload.get("session_assembly_metadata", {})
    require(session.get("runtime_status") == "NOT_CONNECTED_METADATA_ONLY", "SESSION_RUNTIME_STATUS_INVALID")
    require(session.get("session_size") == 10, "SESSION_SIZE_INVALID")
    require(session.get("pool_source") == "APPROVED_VARIANTS_ONLY", "SESSION_POOL_SOURCE_INVALID")
    quota = session.get("selection_quota", {})
    require(
        quota == {"new_or_unseen": 4, "remediation": 2, "scheduled_review": 2, "transfer": 1, "guided_extension": 1},
        "SESSION_QUOTA_INVALID",
    )
    require(sum(quota.values()) == 10, "SESSION_QUOTA_SUM_INVALID")
    exposure = session.get("recent_exposure_exclusion", {})
    require(exposure.get("same_item_within_session_forbidden") is True, "WITHIN_SESSION_REPEAT_ALLOWED")
    require(exposure.get("exclude_last_n_item_exposures") == 10, "RECENT_EXPOSURE_WINDOW_INVALID")
    require(exposure.get("assessment_prefers_unseen_items") is True, "ASSESSMENT_UNSEEN_POLICY_INVALID")
    require(exposure.get("reassessment_replays_original_item_by_default") is False, "REASSESSMENT_REPLAY_POLICY_INVALID")

    admission = payload.get("admission_policy", {})
    for key in (
        "independent_validation_required",
        "semantic_dedup_required",
        "approved_contract_phrases_only_for_adjective_combinations",
        "approved_bank_required_before_runtime",
    ):
        require(admission.get(key) is True, f"ADMISSION_POLICY_INVALID:{key}")
    require(admission.get("unvalidated_variant_delivery_allowed") is False, "UNVALIDATED_DELIVERY_ALLOWED")
    require(admission.get("learner_time_generation_allowed") is False, "LEARNER_TIME_GENERATION_ALLOWED")

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
    require(source.get("unit01_approved_contract_sha256") == builder.APPROVED_CONTRACT_SHA256, "SOURCE_CONTRACT_DIGEST_INVALID")
    require(source.get("u01data05b_task_id") == builder.pattern_authority.TASK_ID, "SOURCE_PATTERN_TASK_INVALID")
    require(
        source.get("unit_local_pattern_ids")
        == [builder.PATTERN_NOUN, builder.PATTERN_ADJECTIVE, builder.PATTERN_VERY],
        "SOURCE_PATTERN_IDS_INVALID",
    )
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "CANDIDATE_PAYLOAD_MISSING")
    return validate_payload(payload)


def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        receipt = validate_candidate(candidate)
        require(approved.get("artifact_role") == policy_artifact.APPROVED_ROLE, "APPROVED_ROLE_INVALID")
        require(approved.get("learner_facing") is False, "APPROVED_TOP_LEVEL_LEARNER_FACING_INVALID")
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
        VariantPoolValidationError,
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
