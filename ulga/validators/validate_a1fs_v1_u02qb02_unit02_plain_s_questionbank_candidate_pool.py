#!/usr/bin/env python3
"""Validate the Unit02 plain-s QuestionBank candidate pool and admission."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U02QB02_UNIT02_PLAIN_S_QUESTIONBANK_CANDIDATE_POOL_VALIDATOR"

EXPECTED_APPROVED_SKILLS = {
    "READING": 162,
    "SPEAKING": 162,
    "WRITING": 334,
}
EXPECTED_APPROVED_EGP = {
    builder.KP011: 5,
    builder.KP012: 5,
    builder.KP013: 162,
    builder.KP014: 486,
}


class Unit02QuestionBankValidationError(ValueError):
    """Fail-closed U02QB02 validation error."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Unit02QuestionBankValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def inventory() -> dict[str, dict[str, Any]]:
    value = builder.load_inventory()
    return {str(row["singular"]): dict(row) for row in value["inventory"]}


def adjective_ids() -> dict[str, str]:
    return {
        lemma: str(sense).split(":")[-1]
        for lemma, sense, _guide, _row, _gloss, _memory, _group
        in builder.u01_contract.ACTIVE_ADJECTIVES
    }


def expected_signature(item: Mapping[str, Any]) -> str:
    return builder.digest(
        {
            "family_id": item["pattern_family_id"],
            "lexical_slots": item["lexical_slots"],
            "prompt": item["prompt"],
            "stimulus": item["stimulus"],
            "options": item["options"],
            "correct_answer": item["correct_answer"],
        }
    )


def independent_decision(item: Mapping[str, Any]) -> dict[str, Any]:
    family_id = str(item["pattern_family_id"])
    noun = str(item["lexical_slots"]["singular_noun"])
    if family_id in {
        "U02-PF03-ADJECTIVE-PLURAL-NOUN",
        "U02-PF04-NUMBER-ADJECTIVE-PLURAL-NOUN",
    } and noun not in inventory():
        return {
            "status": "AUTO_REJECTED",
            "reason_codes": [builder.REJECT_OUTSIDE_PLAIN_S],
        }
    reason = (
        "U01_APPROVED_ADJECTIVE_NOUN_PAIR_AND_U02QB01_PLAIN_S_NOUN"
        if family_id in {
            "U02-PF03-ADJECTIVE-PLURAL-NOUN",
            "U02-PF04-NUMBER-ADJECTIVE-PLURAL-NOUN",
        }
        else (
            "U02QB01_PLAIN_S_NOUN_WITH_A1_NUMERIC_DETERMINER"
            if family_id == "U02-PF05-NUMBER-PLURAL-NOUN"
            else "U02QB01_PLAIN_S_NOUN_AUTHORITY_BOUND"
        )
    )
    return {"status": "AUTO_APPROVED", "reason_codes": [reason]}


def validate_response(item: Mapping[str, Any], approved: bool) -> None:
    response = item.get("response_contract")
    item_id = str(item["item_id"])
    require(isinstance(response, Mapping), f"RESPONSE_CONTRACT_MISSING:{item_id}")
    speaking = item["skill"] == "SPEAKING"
    require(response.get("capture_enabled") is (not speaking), f"CAPTURE_MODE_INVALID:{item_id}")
    require(item.get("assessment_eligible") is (approved and not speaking), f"ASSESSMENT_INVALID:{item_id}")
    require(item.get("reassessment_eligible") is (approved and not speaking), f"REASSESSMENT_INVALID:{item_id}")
    if speaking:
        require(item["correct_answer"] is None, f"SPEAKING_KEY_FORBIDDEN:{item_id}")
        require(response.get("rubric", {}).get("practice_only") is True, f"SPEAKING_NOT_PRACTICE_ONLY:{item_id}")
        require(response.get("accepted_texts") == item["accepted_answers"], f"SPEAKING_MODEL_INVALID:{item_id}")
    elif item["scoring_mode"] == "EXACT_SEQUENCE":
        require(response.get("accepted_sequence") == item["correct_answer"], f"SEQUENCE_INVALID:{item_id}")
        require(response.get("accepted_texts") == [], f"SEQUENCE_TEXT_LEAK:{item_id}")
    else:
        require(item["correct_answer"] in response.get("accepted_texts", []), f"ANSWER_CONTRACT_INVALID:{item_id}")
        require(response.get("accepted_sequence") == [], f"TEXT_SEQUENCE_INVALID:{item_id}")


def validate_family_shape(item: Mapping[str, Any]) -> None:
    family_id = str(item["pattern_family_id"])
    slots = item["lexical_slots"]
    singular = str(slots["singular_noun"])
    plural = str(slots["plural_noun"])
    adjective = slots.get("adjective")

    if family_id == "U02-PF01-PLURAL-FORM-PRODUCTION":
        require(item["target_egp_row_ids"] == [builder.KP014], "PF01_EGP_INVALID")
        require(item["correct_answer"] == plural, "PF01_ANSWER_INVALID")
        require(item["options"] == [], "PF01_OPTIONS_INVALID")
    elif family_id == "U02-PF02-PLURAL-FORM-CHOICE":
        require(item["target_egp_row_ids"] == [builder.KP014], "PF02_EGP_INVALID")
        require(item["correct_answer"] == plural, "PF02_ANSWER_INVALID")
        require(item["options"] == [plural, singular], "PF02_OPTIONS_INVALID")
    elif family_id == "U02-PF03-ADJECTIVE-PLURAL-NOUN":
        require(item["target_egp_row_ids"] == [builder.KP011], "PF03_EGP_INVALID")
        require(bool(adjective), "PF03_ADJECTIVE_MISSING")
        require(item["correct_answer"] == [adjective, plural], "PF03_SEQUENCE_INVALID")
        require(item["prerequisite_egp_row_ids"] == [], "PF03_PREREQ_INVALID")
    elif family_id == "U02-PF04-NUMBER-ADJECTIVE-PLURAL-NOUN":
        require(item["target_egp_row_ids"] == [builder.KP012], "PF04_EGP_INVALID")
        require(bool(adjective), "PF04_ADJECTIVE_MISSING")
        require(slots.get("determiner") == builder.DETERMINER, "PF04_DETERMINER_INVALID")
        require(
            item["correct_answer"] == [builder.DETERMINER, adjective, plural],
            "PF04_SEQUENCE_INVALID",
        )
        require(
            item["prerequisite_egp_row_ids"] == [builder.PREREQUISITE_KP009],
            "PF04_PREREQ_INVALID",
        )
    elif family_id == "U02-PF05-NUMBER-PLURAL-NOUN":
        require(item["target_egp_row_ids"] == [builder.KP013], "PF05_EGP_INVALID")
        require(slots.get("determiner") == builder.DETERMINER, "PF05_DETERMINER_INVALID")
        require(item["correct_answer"] == [builder.DETERMINER, plural], "PF05_SEQUENCE_INVALID")
        require(
            item["prerequisite_egp_row_ids"] == [builder.PREREQUISITE_KP009],
            "PF05_PREREQ_INVALID",
        )
    elif family_id == "U02-PF06-SPEAK-PLURAL-FORM":
        require(item["target_egp_row_ids"] == [builder.KP014], "PF06_EGP_INVALID")
        require(item["accepted_answers"] == [plural], "PF06_MODEL_INVALID")
    else:
        raise Unit02QuestionBankValidationError(f"UNKNOWN_FAMILY:{family_id}")


def validate_item(item: Mapping[str, Any]) -> None:
    item_id = str(item.get("item_id") or "")
    family_id = str(item.get("pattern_family_id") or "")
    fam = builder.family(family_id)
    slots = item.get("lexical_slots")
    require(isinstance(slots, Mapping), f"LEXICAL_SLOTS_INVALID:{item_id}")
    singular = str(slots.get("singular_noun") or "")
    plural = str(slots.get("plural_noun") or "")
    inv = inventory()
    decision = independent_decision(item)
    approved = decision["status"] == "AUTO_APPROVED"

    require(item.get("unit_id") == builder.UNIT_ID, f"UNIT_INVALID:{item_id}")
    require(item.get("unit_pattern_ids") == [builder.DIRECT_PATTERN_ID], f"PATTERN_INVALID:{item_id}")
    require(item.get("grammar_target_ids") == ["REGULAR_PLURAL_NOUNS"], f"GRAMMAR_TARGET_INVALID:{item_id}")
    require(item.get("skill") == fam["skill"], f"SKILL_INVALID:{item_id}")
    require(item.get("question_type") == fam["question_type"], f"QUESTION_TYPE_INVALID:{item_id}")
    require(item.get("target_egp_row_ids") == [fam["egp_row_id"]], f"EGP_INVALID:{item_id}")
    require(item.get("semantic_signature") == expected_signature(item), f"SIGNATURE_INVALID:{item_id}")
    require(item.get("admission_proposal") == decision, f"ADMISSION_INVALID:{item_id}")
    require(item.get("learner_visible_capable") is approved, f"LEARNER_FLAG_INVALID:{item_id}")
    require(item.get("runtime_generation_used") is False, f"RUNTIME_GENERATION_USED:{item_id}")
    require(item.get("learner_delivery_status") == "NOT_RUNTIME_CONNECTED", f"RUNTIME_STATUS_INVALID:{item_id}")
    require(item.get("audio_required") is False, f"AUDIO_INVALID:{item_id}")
    require(item.get("speaking_capture_enabled") is False, f"SPEAKING_CAPTURE_INVALID:{item_id}")

    if approved:
        require(singular in inv, f"NOUN_NOT_IN_INVENTORY:{item_id}")
        require(plural == singular + "s", f"NON_PLAIN_S:{item_id}")
        require(plural == inv[singular]["plural"], f"PLURAL_DRIFT:{item_id}")
        noun_ids = set(inv[singular]["vocabulary_ids"])
        actual_ids = set(item["target_evp_sense_ids"])
        require(noun_ids.issubset(actual_ids), f"NOUN_AUTHORITY_MISSING:{item_id}")
        adjective = slots.get("adjective")
        if adjective:
            require(
                adjective_ids().get(str(adjective)) in actual_ids,
                f"ADJECTIVE_AUTHORITY_MISSING:{item_id}",
            )
    else:
        require(
            family_id in {
                "U02-PF03-ADJECTIVE-PLURAL-NOUN",
                "U02-PF04-NUMBER-ADJECTIVE-PLURAL-NOUN",
            },
            f"UNEXPECTED_REJECTION:{item_id}",
        )
        require(singular == "box", f"REJECTED_NOUN_INVALID:{item_id}")
        require(plural == "boxs", f"REJECTED_CANDIDATE_SHAPE_INVALID:{item_id}")

    validate_family_shape(item)
    validate_response(item, approved)


def distribution(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    return builder.distribution(rows)


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_ID_INVALID")
    require(payload.get("level_scope") == ["A1"], "LEVEL_SCOPE_INVALID")

    bank = payload.get("bank_identity", {})
    require(bank.get("unit01_runtime_base_item_count") == 474, "UNIT01_BASE_COUNT_INVALID")
    require(bank.get("unit01_runtime_base_reused") is True, "UNIT01_BASE_REUSE_INVALID")
    require(bank.get("parallel_questionbank_created") is False, "PARALLEL_BANK_CREATED")
    require(bank.get("runtime_status") == "NOT_CONNECTED", "RUNTIME_STATUS_INVALID")

    authority = payload.get("grammar_authority", {})
    require(authority.get("target_egp_row_ids") == list(builder.TARGET_EGP_ROWS), "EGP_AUTHORITY_INVALID")
    require(authority.get("direct_pattern_ids") == [builder.DIRECT_PATTERN_ID], "PATTERN_AUTHORITY_INVALID")
    require(
        authority.get("numeric_determiner_prerequisite_egp_row_ids")
        == [builder.PREREQUISITE_KP009],
        "DETERMINER_PREREQ_INVALID",
    )
    require(authority.get("numeric_determiner_used") == "two", "DETERMINER_INVALID")

    source_inventory = payload.get("source_inventory", {})
    require(source_inventory.get("plain_s_denominator") == 162, "SOURCE_DENOMINATOR_INVALID")
    require(source_inventory.get("exact_active_vocabulary_ref_count") == 171, "SOURCE_REF_COUNT_INVALID")

    families = payload.get("pattern_family_contracts")
    require(families == list(builder.FAMILIES), "FAMILY_CONTRACT_INVALID")
    candidates = payload.get("candidate_items")
    approved = payload.get("approved_items")
    require(isinstance(candidates, list) and len(candidates) == 660, "CANDIDATE_COUNT_INVALID")
    require(isinstance(approved, list) and len(approved) == 658, "APPROVED_COUNT_INVALID")
    require(len({row["item_id"] for row in candidates}) == 660, "DUPLICATE_ITEM_ID")
    require(len({row["semantic_signature"] for row in candidates}) == 660, "DUPLICATE_SIGNATURE")

    for item in candidates:
        validate_item(item)

    independently_approved = [
        row for row in candidates if independent_decision(row)["status"] == "AUTO_APPROVED"
    ]
    require(approved == independently_approved, "APPROVED_SUBSET_DRIFT")

    rejected = [
        row for row in candidates if independent_decision(row)["status"] == "AUTO_REJECTED"
    ]
    require(len(rejected) == 2, "REJECTED_COUNT_INVALID")
    require(
        {row["lexical_slots"]["singular_noun"] for row in rejected} == {"box"},
        "REJECTED_IDENTITY_INVALID",
    )
    require(
        Counter(row["pattern_family_id"] for row in rejected)
        == Counter({
            "U02-PF03-ADJECTIVE-PLURAL-NOUN": 1,
            "U02-PF04-NUMBER-ADJECTIVE-PLURAL-NOUN": 1,
        }),
        "REJECTED_FAMILY_INVALID",
    )

    readback = payload.get("admission_readback", {})
    require(readback.get("candidate_count") == 660, "READBACK_CANDIDATE_INVALID")
    require(readback.get("approved_count") == 658, "READBACK_APPROVED_INVALID")
    require(readback.get("rejected_count") == 2, "READBACK_REJECTED_INVALID")
    require(
        readback.get("rejection_reason_counts") == {builder.REJECT_OUTSIDE_PLAIN_S: 2},
        "READBACK_REASON_INVALID",
    )
    require(readback.get("human_review_count") == 0, "HUMAN_REVIEW_INVALID")

    distributions = payload.get("distribution_counts", {})
    require(distributions.get("candidate") == distribution(candidates), "CANDIDATE_DISTRIBUTION_INVALID")
    require(distributions.get("approved") == distribution(approved), "APPROVED_DISTRIBUTION_INVALID")
    require(distributions["approved"]["skill"] == EXPECTED_APPROVED_SKILLS, "SKILL_DISTRIBUTION_INVALID")
    require(distributions["approved"]["egp_row"] == EXPECTED_APPROVED_EGP, "EGP_DISTRIBUTION_INVALID")

    coverage = payload.get("coverage_denominators", {})
    require(coverage.get("plain_s_noun_surface_count") == 162, "COVERAGE_NOUN_INVALID")
    require(coverage.get("plain_s_exact_active_vocabulary_ref_count") == 171, "COVERAGE_REF_INVALID")
    require(coverage.get("covered_target_egp_row_count") == 4, "COVERAGE_EGP_COUNT_INVALID")
    require(
        coverage.get("covered_target_egp_row_ids") == sorted(builder.TARGET_EGP_ROWS),
        "COVERAGE_EGP_IDS_INVALID",
    )
    require(coverage.get("learner_mastery_claimed") is False, "MASTERY_CLAIM_INVALID")

    per_family_nouns: dict[str, set[str]] = defaultdict(set)
    for row in approved:
        per_family_nouns[row["pattern_family_id"]].add(row["lexical_slots"]["singular_noun"])
    for family_id in (
        "U02-PF01-PLURAL-FORM-PRODUCTION",
        "U02-PF02-PLURAL-FORM-CHOICE",
        "U02-PF05-NUMBER-PLURAL-NOUN",
        "U02-PF06-SPEAK-PLURAL-FORM",
    ):
        require(len(per_family_nouns[family_id]) == 162, f"NOUN_COVERAGE_INVALID:{family_id}")
    require(per_family_nouns["U02-PF03-ADJECTIVE-PLURAL-NOUN"] == {"bag", "book"}, "PF03_NOUN_SET_INVALID")
    require(per_family_nouns["U02-PF04-NUMBER-ADJECTIVE-PLURAL-NOUN"] == {"bag", "book"}, "PF04_NOUN_SET_INVALID")

    policy = payload.get("admission_policy", {})
    for key in (
        "u02qb01_plain_s_inventory_required",
        "plain_s_only",
        "unit01_adjective_pair_reuse_requires_u02_noun_admission",
        "rejected_source_pairs_retained_with_reason",
        "independent_validation_required",
        "semantic_dedup_required",
    ):
        require(policy.get(key) is True, f"ADMISSION_POLICY_INVALID:{key}")
    require(policy.get("learner_time_generation_allowed") is False, "LEARNER_TIME_GENERATION_ALLOWED")

    boundaries = payload.get("claim_boundaries", {})
    for key in (
        "unit01_questionbank_mutated",
        "unit01_item_identity_mutated",
        "learner_database_written",
        "runtime_bundle_written",
        "runtime_connected",
        "parallel_runtime_created",
        "new_scene_created",
        "audio_enabled",
        "speaking_capture_enabled",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")

    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_STEP_INVALID")
    return {
        "status": builder.PASS_STATUS,
        "candidate_count": len(candidates),
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "plain_s_noun_surface_count": 162,
        "covered_target_egp_row_count": 4,
    }


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(candidate)
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "CANDIDATE_ROLE_INVALID")
    require(candidate.get("producer_id") == builder.TASK_ID, "CANDIDATE_PRODUCER_INVALID")
    require(candidate.get("level_scope") == ["A1"], "CANDIDATE_LEVEL_INVALID")
    validate_payload(candidate["payload"])
    return validation_receipt(candidate["payload"])


def validate_approved(
    candidate: Mapping[str, Any], approved: Mapping[str, Any]
) -> dict[str, Any]:
    validate_candidate(candidate)
    policy_artifact.verify_artifact_digest(approved)
    require(approved.get("artifact_role") == policy_artifact.APPROVED_ROLE, "APPROVED_ROLE_INVALID")
    require(approved.get("producer_id") == builder.TASK_ID, "APPROVED_PRODUCER_INVALID")
    require(approved.get("payload") == candidate.get("payload"), "APPROVED_PAYLOAD_DRIFT")
    require(approved.get("admission", {}).get("status") == "APPROVED", "APPROVED_STATUS_INVALID")
    require(
        approved.get("admission", {}).get("decision_ref") == builder.DECISION_REF,
        "DECISION_REF_INVALID",
    )
    require(len(approved.get("validation_receipts", [])) == 1, "RECEIPT_COUNT_INVALID")
    require(
        approved["validation_receipts"][0]["validator_id"] == VALIDATOR_ID,
        "RECEIPT_VALIDATOR_INVALID",
    )
    summary = validate_payload(approved["payload"])
    return {
        **summary,
        "error_count": 0,
        "errors": [],
        "candidate_artifact_sha256": candidate["artifact_sha256"],
        "approved_artifact_sha256": approved["artifact_sha256"],
    }
