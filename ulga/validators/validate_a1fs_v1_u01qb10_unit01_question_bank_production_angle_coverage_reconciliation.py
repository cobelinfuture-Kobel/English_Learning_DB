#!/usr/bin/env python3
"""Validate the Unit01 count-preserving production-angle QuestionBank revision."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as seed
from ulga.builders import build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as builder

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB10_UNIT01_QUESTION_BANK_PRODUCTION_ANGLE_COVERAGE_RECONCILIATION_VALIDATOR"
EXPECTED_FAMILY_COUNTS = {
    "U01-PF01-AAN-NOUN-GAP": 16,
    "U01-PF02-AAN-ADJ-NOUN-GAP": 6,
    "U01-PF03-VERY-ADJ-NOUN-GAP": 3,
    "U01-PF04-FIRST-MENTION-CONTEXT": 35,
    "U01-PF05-KNOWN-REFERENCE-CONTEXT": 35,
    "U01-PF06-ERROR-DISCRIMINATION": 25,
    "U01-PF07-WORD-ORDER": 25,
    "U01-PF08-TRANSFER-FIRST-MENTION": 35,
    "U01-PF09-TRANSFER-KNOWN-REFERENCE": 35,
    "U01-PF10-SPEAK-NOUN": 16,
    "U01-PF11-SPEAK-ADJ-NOUN": 6,
    "U01-PF12-SPEAK-VERY-ADJ-NOUN": 3,
    builder.PF13: 12,
    builder.PF14: 24,
    builder.PF15: 12,
}


class ReconciliationValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ReconciliationValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def _seed_items() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    approved, items = builder.seed_bank()
    return approved, items


def _expected_removed(seed_items: list[dict[str, Any]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for source_family, (count, _replacement_family) in builder.REPLACEMENT_PLAN.items():
        rows = sorted(
            (row for row in seed_items if row.get("pattern_family_id") == source_family),
            key=lambda row: str(row["item_id"]),
        )
        result[source_family] = [str(row["item_id"]) for row in rows[:count]]
    return result


def _validate_reconciliation_digest(payload: Mapping[str, Any]) -> None:
    unsigned = dict(payload)
    actual = unsigned.pop("reconciliation_sha256", None)
    require(actual == policy_artifact.digest(unsigned), "RECONCILIATION_DIGEST_INVALID")


def _validate_production_item(item: Mapping[str, Any]) -> None:
    item_id = str(item.get("item_id") or "")
    family = str(item.get("pattern_family_id") or "")
    require(item.get("unit_id") == builder.UNIT_ID, f"PRODUCTION_UNIT_INVALID:{item_id}")
    require(item.get("skill") == "WRITING", f"PRODUCTION_SKILL_INVALID:{item_id}")
    require(item.get("learner_visible_capable") is True, f"PRODUCTION_VISIBILITY_INVALID:{item_id}")
    require(item.get("assessment_eligible") is True, f"PRODUCTION_ASSESSMENT_INVALID:{item_id}")
    require(item.get("reassessment_eligible") is True, f"PRODUCTION_REASSESSMENT_INVALID:{item_id}")
    require(item.get("audio_required") is False, f"PRODUCTION_AUDIO_INVALID:{item_id}")
    require(item.get("speaking_capture_enabled") is False, f"PRODUCTION_SPEAKING_INVALID:{item_id}")
    require(item.get("runtime_generation_used") is False, f"PRODUCTION_RUNTIME_GENERATION_INVALID:{item_id}")
    require(item.get("learner_delivery_status") == "NOT_RUNTIME_CONNECTED", f"PRODUCTION_RUNTIME_STATUS_INVALID:{item_id}")
    require(bool(item.get("reconciliation_source_item_id")), f"PRODUCTION_SOURCE_ITEM_MISSING:{item_id}")
    response = item.get("response_contract")
    require(isinstance(response, Mapping), f"PRODUCTION_RESPONSE_MISSING:{item_id}")
    require(response.get("capture_enabled") is True, f"PRODUCTION_CAPTURE_INVALID:{item_id}")
    require(response.get("response_type") == "string", f"PRODUCTION_RESPONSE_TYPE_INVALID:{item_id}")
    require(item.get("correct_answer") in response.get("accepted_texts", []), f"PRODUCTION_MODEL_ANSWER_INVALID:{item_id}")
    require(response.get("accepted_sequence") == [], f"PRODUCTION_SEQUENCE_INVALID:{item_id}")

    if family == builder.PF13:
        require(item.get("question_type") == "error_correction", f"PF13_TYPE_INVALID:{item_id}")
        require(item.get("task_angle") == "ERROR_CHECK", f"PF13_ANGLE_INVALID:{item_id}")
        require(item.get("scoring_mode") == "NORMALIZED_TEXT", f"PF13_MODE_INVALID:{item_id}")
        require(response.get("scoring_mode") == "NORMALIZED_TEXT", f"PF13_RESPONSE_MODE_INVALID:{item_id}")
        require(response.get("human_review_fallback") is False, f"PF13_HUMAN_REVIEW_INVALID:{item_id}")
        require(item.get("human_review_required") is False, f"PF13_REVIEW_FLAG_INVALID:{item_id}")
    elif family == builder.PF14:
        require(item.get("question_type") == "complete_sentence_production", f"PF14_TYPE_INVALID:{item_id}")
        require(item.get("task_angle") == "COMPLETE_SENTENCE_PRODUCTION", f"PF14_ANGLE_INVALID:{item_id}")
        require(item.get("scoring_mode") == "FEATURE_RUBRIC", f"PF14_MODE_INVALID:{item_id}")
        require(response.get("scoring_mode") == "FEATURE_RUBRIC", f"PF14_RESPONSE_MODE_INVALID:{item_id}")
        require(response.get("human_review_fallback") is True, f"PF14_HUMAN_REVIEW_INVALID:{item_id}")
        require(item.get("human_review_required") is True, f"PF14_REVIEW_FLAG_INVALID:{item_id}")
        rubric = response.get("rubric") or {}
        require("first_mention_article" in rubric.get("concept_features", []), f"PF14_ARTICLE_RUBRIC_MISSING:{item_id}")
        require("sentence_complete" in rubric.get("concept_features", []), f"PF14_SENTENCE_RUBRIC_MISSING:{item_id}")
        require(rubric.get("minor_surface_error_does_not_zero_concept") is True, f"PF14_SURFACE_POLICY_INVALID:{item_id}")
    elif family == builder.PF15:
        require(item.get("question_type") == "connected_sentence_production", f"PF15_TYPE_INVALID:{item_id}")
        require(item.get("task_angle") == "CONNECTED_SENTENCE_PRODUCTION", f"PF15_ANGLE_INVALID:{item_id}")
        require(item.get("scoring_mode") == "FEATURE_RUBRIC", f"PF15_MODE_INVALID:{item_id}")
        require(response.get("scoring_mode") == "FEATURE_RUBRIC", f"PF15_RESPONSE_MODE_INVALID:{item_id}")
        require(response.get("human_review_fallback") is True, f"PF15_HUMAN_REVIEW_INVALID:{item_id}")
        require(item.get("human_review_required") is True, f"PF15_REVIEW_FLAG_INVALID:{item_id}")
        rubric = response.get("rubric") or {}
        required_features = {
            "first_mention_article",
            "known_reference_article",
            "same_referent_preserved",
            "sentence_1_complete",
            "sentence_2_complete",
        }
        require(required_features <= set(rubric.get("concept_features", [])), f"PF15_RUBRIC_INCOMPLETE:{item_id}")
        require(rubric.get("minor_surface_error_does_not_zero_concept") is True, f"PF15_SURFACE_POLICY_INVALID:{item_id}")
    else:
        raise ReconciliationValidationError(f"UNKNOWN_PRODUCTION_FAMILY:{item_id}:{family}")


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("program_id") == builder.PROGRAM_ID, "PROGRAM_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")
    _validate_reconciliation_digest(payload)

    approved_seed, seed_items = _seed_items()
    source = payload.get("source_identity") or {}
    require(source.get("seed_task_id") == seed.TASK_ID, "SEED_TASK_INVALID")
    require(source.get("seed_bank_artifact_sha256") == approved_seed["artifact_sha256"], "SEED_ARTIFACT_INVALID")
    require(source.get("seed_approved_item_count") == builder.EXPECTED_APPROVED_COUNT, "SEED_COUNT_INVALID")
    require(source.get("approved_contract_sha256") == builder.APPROVED_CONTRACT_SHA256, "CONTRACT_IDENTITY_INVALID")

    identity = payload.get("bank_identity") or {}
    require(identity.get("bank_id") == seed.BANK_ID, "BANK_ID_INVALID")
    require(identity.get("bank_version") == seed.BANK_VERSION, "BANK_VERSION_INVALID")
    require(identity.get("canonical_revision") == builder.CANONICAL_REVISION, "REVISION_INVALID")
    require(identity.get("second_question_bank_created") is False, "SECOND_BANK_CREATED")
    require(identity.get("supersedes_runtime_activation") is False, "RUNTIME_SUPERSESSION_INVALID")

    counts = payload.get("count_preservation") or {}
    require(counts.get("seed_base_count") == 288, "SEED_BASE_COUNT_INVALID")
    require(counts.get("retained_base_count") == 240, "RETAINED_COUNT_INVALID")
    require(counts.get("removed_base_count") == 48, "REMOVED_COUNT_INVALID")
    require(counts.get("production_items_added") == 48, "ADDED_COUNT_INVALID")
    require(counts.get("reconciled_base_count") == 288, "RECONCILED_COUNT_INVALID")
    require(counts.get("unchanged_real62_extension_count") == 186, "EXTENSION_COUNT_INVALID")
    require(counts.get("projected_runtime_total_count") == 474, "PROJECTED_RUNTIME_COUNT_INVALID")
    require(counts.get("runtime_activation_completed") is False, "RUNTIME_ACTIVATION_INVALID")

    expected_removed = _expected_removed(seed_items)
    plan = payload.get("replacement_plan")
    require(isinstance(plan, list) and len(plan) == 4, "REPLACEMENT_PLAN_INVALID")
    plan_by_source = {str(row.get("source_pattern_family_id")): row for row in plan}
    require(set(plan_by_source) == set(builder.REPLACEMENT_PLAN), "REPLACEMENT_SOURCE_FAMILIES_INVALID")
    for source_family, (count, replacement_family) in builder.REPLACEMENT_PLAN.items():
        row = plan_by_source[source_family]
        require(row.get("removed_count") == count, f"REPLACEMENT_COUNT_INVALID:{source_family}")
        require(row.get("replacement_pattern_family_id") == replacement_family, f"REPLACEMENT_FAMILY_INVALID:{source_family}")
        require(row.get("replacement_source_item_ids") == expected_removed[source_family], f"REPLACEMENT_SOURCE_IDS_INVALID:{source_family}")

    items = payload.get("reconciled_items")
    require(isinstance(items, list) and len(items) == 288, "RECONCILED_ITEMS_INVALID")
    require(len({str(row.get("item_id")) for row in items}) == 288, "DUPLICATE_ITEM_ID")
    require(len({str(row.get("semantic_signature")) for row in items}) == 288, "DUPLICATE_SEMANTIC_SIGNATURE")

    family_counts = dict(sorted(Counter(str(row["pattern_family_id"]) for row in items).items()))
    skill_counts = dict(sorted(Counter(str(row["skill"]) for row in items).items()))
    require(family_counts == EXPECTED_FAMILY_COUNTS, "FAMILY_DISTRIBUTION_INVALID")
    require(skill_counts == builder.EXPECTED_SKILL_COUNTS, "SKILL_DISTRIBUTION_INVALID")
    distributions = payload.get("distribution_counts") or {}
    require(distributions.get("family") == family_counts, "FAMILY_READBACK_INVALID")
    require(distributions.get("skill") == skill_counts, "SKILL_READBACK_INVALID")

    seed_by_id = {str(row["item_id"]): row for row in seed_items}
    removed_ids = {item_id for ids in expected_removed.values() for item_id in ids}
    retained_ids = set(seed_by_id) - removed_ids
    result_by_id = {str(row["item_id"]): row for row in items}
    require(retained_ids <= set(result_by_id), "RETAINED_ITEMS_MISSING")
    for item_id in retained_ids:
        require(result_by_id[item_id] == seed_by_id[item_id], f"RETAINED_ITEM_DRIFT:{item_id}")
    require(not (removed_ids & set(result_by_id)), "REMOVED_ITEM_STILL_PRESENT")

    production_items = [row for row in items if row.get("pattern_family_id") in {builder.PF13, builder.PF14, builder.PF15}]
    require(len(production_items) == 48, "PRODUCTION_ITEM_COUNT_INVALID")
    require(
        {str(row.get("reconciliation_source_item_id")) for row in production_items} == removed_ids,
        "PRODUCTION_SOURCE_LINEAGE_INVALID",
    )
    for item in production_items:
        _validate_production_item(item)

    seed_speaking = sorted(
        (row for row in seed_items if row.get("skill") == "SPEAKING"),
        key=lambda row: str(row["item_id"]),
    )
    reconciled_speaking = sorted(
        (row for row in items if row.get("skill") == "SPEAKING"),
        key=lambda row: str(row["item_id"]),
    )
    require(reconciled_speaking == seed_speaking, "SPEAKING_BANK_DRIFT")
    require(all((row.get("response_contract") or {}).get("capture_enabled") is False for row in reconciled_speaking), "SPEAKING_CAPTURE_DRIFT")

    seed_evp = {sense for row in seed_items for sense in row.get("target_evp_sense_ids", [])}
    result_evp = {sense for row in items for sense in row.get("target_evp_sense_ids", [])}
    seed_egp = {row_id for row in seed_items for row_id in row.get("target_egp_row_ids", [])}
    result_egp = {row_id for row in items for row_id in row.get("target_egp_row_ids", [])}
    require(result_evp == seed_evp, "EVP_COVERAGE_DRIFT")
    require(result_egp == seed_egp, "EGP_COVERAGE_DRIFT")

    coverage = payload.get("production_angle_coverage") or {}
    require(coverage.get("scored_gap_count_before") == 48, "GAP_BEFORE_INVALID")
    require(coverage.get("scored_gap_count_after") == 0, "GAP_AFTER_INVALID")
    require(coverage.get("scored_partial_support_remaining") == 36, "PARTIAL_REMAINING_INVALID")
    require(coverage.get("writing_error_correction_slots_added") == 12, "ERROR_CORRECTION_SLOTS_INVALID")
    require(coverage.get("writing_complete_sentence_slots_added") == 24, "COMPLETE_SENTENCE_SLOTS_INVALID")
    require(coverage.get("writing_connected_sentence_slots_added") == 12, "CONNECTED_SENTENCE_SLOTS_INVALID")
    require(coverage.get("production_angle_alignment_ready") is True, "PRODUCTION_ALIGNMENT_INVALID")
    require(coverage.get("question_bank_full_alignment_ready") is False, "FULL_ALIGNMENT_CLAIM_INVALID")
    require(coverage.get("remaining_partial_angles") == ["READING_REFERENCE_EVIDENCE", "WRITING_PHRASE_CONSTRUCTION"], "REMAINING_PARTIAL_INVALID")

    scoring = payload.get("scoring_contract") or {}
    require(scoring.get("error_correction") == "NORMALIZED_TEXT", "ERROR_SCORING_INVALID")
    require(scoring.get("complete_sentence_production") == "FEATURE_RUBRIC", "COMPLETE_SCORING_INVALID")
    require(scoring.get("connected_sentence_production") == "FEATURE_RUBRIC", "CONNECTED_SCORING_INVALID")
    require(scoring.get("feature_rubric_routes_to_human_review") is True, "HUMAN_REVIEW_ROUTE_INVALID")
    require(scoring.get("minor_surface_error_does_not_zero_concept") is True, "SURFACE_ERROR_POLICY_INVALID")
    require(scoring.get("speaking_scoring_enabled") is False, "SPEAKING_SCORING_DRIFT")

    boundaries = payload.get("boundaries") or {}
    for key in (
        "new_scene_authored",
        "question_bank_total_expanded",
        "second_question_bank_created",
        "runtime_migrated",
        "real62_extension_modified",
        "learner_state_modified",
        "speaking_scoring_enabled",
        "unit02_to_unit24_modified",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")
    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_STEP_INVALID")
    return validation_receipt(payload)


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "CANDIDATE_ROLE_INVALID")
    require(candidate.get("learner_facing") is False, "CANDIDATE_LEARNER_FACING_INVALID")
    policy_artifact.verify_artifact_digest(candidate)
    source = candidate.get("source_bindings") or {}
    require(source.get("seed_task_id") == seed.TASK_ID, "SOURCE_SEED_TASK_INVALID")
    require(source.get("seed_bank_id") == seed.BANK_ID, "SOURCE_BANK_ID_INVALID")
    require(source.get("seed_bank_version") == seed.BANK_VERSION, "SOURCE_BANK_VERSION_INVALID")
    require(source.get("canonical_revision") == builder.CANONICAL_REVISION, "SOURCE_REVISION_INVALID")
    require(source.get("count_preserving") is True, "SOURCE_COUNT_PRESERVING_INVALID")
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "CANDIDATE_PAYLOAD_MISSING")
    return validate_payload(payload)


def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        receipt = validate_candidate(candidate)
        require(approved.get("artifact_role") == policy_artifact.APPROVED_ROLE, "APPROVED_ROLE_INVALID")
        require(approved.get("learner_facing") is False, "APPROVED_LEARNER_FACING_INVALID")
        require((approved.get("admission") or {}).get("status") == "APPROVED", "APPROVED_STATUS_INVALID")
        require((approved.get("admission") or {}).get("decision_ref") == builder.DECISION_REF, "DECISION_INVALID")
        require(approved.get("payload") == candidate.get("payload"), "APPROVED_PAYLOAD_DRIFT")
        require(
            (approved.get("source_bindings") or {}).get("candidate_artifact_sha256") == candidate.get("artifact_sha256"),
            "CANDIDATE_BINDING_INVALID",
        )
        require(
            approved.get("validation_receipts") == [
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
        ReconciliationValidationError,
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
        "reconciled_base_count": (payload.get("count_preservation") or {}).get("reconciled_base_count", 0),
        "projected_runtime_total_count": (payload.get("count_preservation") or {}).get("projected_runtime_total_count", 0),
        "scored_gap_count_after": (payload.get("production_angle_coverage") or {}).get("scored_gap_count_after"),
        "runtime_migrated": (payload.get("boundaries") or {}).get("runtime_migrated"),
    }
