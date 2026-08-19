#!/usr/bin/env python3
"""Validate Unit01 sentence-pool-driven 48-slot production reconciliation."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
    as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = (
    "A1FS_V1_U01QB18H_R2R2_"
    "UNIT01_SENTENCE_POOL_DRIVEN_PRODUCTION_CAPACITY_RECONCILIATION_VALIDATOR"
)


class SentencePoolCapacityValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise SentencePoolCapacityValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def _validate_digest(payload: Mapping[str, Any]) -> None:
    unsigned = dict(payload)
    actual = unsigned.pop("reconciliation_sha256", None)
    require(
        actual == policy_artifact.digest(unsigned),
        "RECONCILIATION_DIGEST_INVALID",
    )


def _validate_item(item: Mapping[str, Any]) -> None:
    item_id = str(item.get("item_id") or "")
    family = str(item.get("pattern_family_id") or "")
    require(bool(item_id), "ITEM_ID_MISSING")
    require(item.get("unit_id") == builder.u10.UNIT_ID, f"ITEM_UNIT_INVALID:{item_id}")
    require(item.get("skill") == "WRITING", f"ITEM_SKILL_INVALID:{item_id}")
    require(
        family in builder.EXPECTED_PRODUCTION_FAMILY_COUNTS,
        f"ITEM_FAMILY_INVALID:{item_id}:{family}",
    )
    require(
        bool(item.get("production_scene_ref_id")),
        f"ITEM_PRODUCTION_SCENE_MISSING:{item_id}",
    )
    require(
        bool(item.get("production_activity_id")),
        f"ITEM_PRODUCTION_ACTIVITY_MISSING:{item_id}",
    )
    require(
        isinstance(item.get("target_sentence_ids"), list)
        and bool(item.get("target_sentence_ids")),
        f"ITEM_SENTENCE_LINEAGE_MISSING:{item_id}",
    )
    require(
        item.get("target_sentence_ids") == item.get("source_sentence_ids"),
        f"ITEM_SENTENCE_LINEAGE_DRIFT:{item_id}",
    )
    require(
        isinstance(item.get("target_pattern_ids"), list)
        and bool(item.get("target_pattern_ids")),
        f"ITEM_TARGET_PATTERN_MISSING:{item_id}",
    )
    require(
        item.get("sentence_pool_source_task_id") == builder.SOURCE_TASK_ID,
        f"ITEM_SENTENCE_SOURCE_TASK_INVALID:{item_id}",
    )
    require(
        bool(item.get("sentence_pool_capability_index_sha256")),
        f"ITEM_SENTENCE_POOL_SHA_MISSING:{item_id}",
    )
    require(
        item.get("learner_visible_capable") is True,
        f"ITEM_LEARNER_VISIBILITY_INVALID:{item_id}",
    )
    require(
        item.get("assessment_eligible") is True,
        f"ITEM_ASSESSMENT_INVALID:{item_id}",
    )
    require(
        item.get("reassessment_eligible") is True,
        f"ITEM_REASSESSMENT_INVALID:{item_id}",
    )
    require(item.get("audio_required") is False, f"ITEM_AUDIO_INVALID:{item_id}")
    require(
        item.get("speaking_capture_enabled") is False,
        f"ITEM_SPEAKING_CAPTURE_INVALID:{item_id}",
    )
    require(
        item.get("runtime_generation_used") is False,
        f"ITEM_RUNTIME_GENERATION_INVALID:{item_id}",
    )
    require(
        isinstance(item.get("unit_pattern_ids"), list)
        and len(item.get("unit_pattern_ids")) == 1,
        f"ITEM_INTERNAL_PATTERN_INVALID:{item_id}",
    )
    require(
        isinstance(item.get("target_egp_row_ids"), list)
        and bool(item.get("target_egp_row_ids")),
        f"ITEM_EGP_LINEAGE_MISSING:{item_id}",
    )
    require(
        isinstance(item.get("target_evp_sense_ids"), list)
        and len(item.get("target_evp_sense_ids")) == 1,
        f"ITEM_EVP_LINEAGE_MISSING:{item_id}",
    )
    response = item.get("response_contract")
    require(isinstance(response, Mapping), f"ITEM_RESPONSE_CONTRACT_MISSING:{item_id}")
    require(response.get("capture_enabled") is True, f"ITEM_CAPTURE_INVALID:{item_id}")
    require(
        response.get("response_type") == "string",
        f"ITEM_RESPONSE_TYPE_INVALID:{item_id}",
    )
    require(
        item.get("correct_answer") in response.get("accepted_texts", []),
        f"ITEM_MODEL_ANSWER_INVALID:{item_id}",
    )
    require(
        response.get("accepted_sequence") == [],
        f"ITEM_SEQUENCE_INVALID:{item_id}",
    )

    if family == builder.u10.PF13:
        require(item.get("task_angle") == "ERROR_CHECK", f"PF13_ANGLE_INVALID:{item_id}")
        require(
            item.get("question_type") == "error_correction",
            f"PF13_TYPE_INVALID:{item_id}",
        )
        require(
            item.get("scoring_mode") == "NORMALIZED_TEXT",
            f"PF13_SCORING_INVALID:{item_id}",
        )
        require(
            response.get("scoring_mode") == "NORMALIZED_TEXT",
            f"PF13_RESPONSE_SCORING_INVALID:{item_id}",
        )
        require(
            item.get("human_review_required") is False,
            f"PF13_HUMAN_REVIEW_INVALID:{item_id}",
        )
        require(
            len(item.get("target_sentence_ids")) == 1,
            f"PF13_SENTENCE_SOURCE_COUNT_INVALID:{item_id}",
        )
    elif family == builder.u10.PF14:
        require(
            item.get("task_angle") == "COMPLETE_SENTENCE_PRODUCTION",
            f"PF14_ANGLE_INVALID:{item_id}",
        )
        require(
            item.get("question_type") == "complete_sentence_production",
            f"PF14_TYPE_INVALID:{item_id}",
        )
        require(
            item.get("scoring_mode") == "FEATURE_RUBRIC",
            f"PF14_SCORING_INVALID:{item_id}",
        )
        require(
            response.get("human_review_fallback") is True,
            f"PF14_HUMAN_REVIEW_INVALID:{item_id}",
        )
        rubric = response.get("rubric") or {}
        require(
            {"first_mention_article", "target_noun_present", "sentence_complete"}
            <= set(rubric.get("concept_features") or []),
            f"PF14_RUBRIC_INCOMPLETE:{item_id}",
        )
        require(
            len(item.get("target_sentence_ids")) == 1,
            f"PF14_SENTENCE_SOURCE_COUNT_INVALID:{item_id}",
        )
    elif family == builder.u10.PF15:
        require(
            item.get("task_angle") == "CONNECTED_SENTENCE_PRODUCTION",
            f"PF15_ANGLE_INVALID:{item_id}",
        )
        require(
            item.get("question_type") == "connected_sentence_production",
            f"PF15_TYPE_INVALID:{item_id}",
        )
        require(
            item.get("scoring_mode") == "FEATURE_RUBRIC",
            f"PF15_SCORING_INVALID:{item_id}",
        )
        require(
            response.get("human_review_fallback") is True,
            f"PF15_HUMAN_REVIEW_INVALID:{item_id}",
        )
        rubric = response.get("rubric") or {}
        require(
            {
                "first_mention_article",
                "known_reference_article",
                "same_referent_preserved",
                "sentence_1_complete",
                "sentence_2_complete",
            }
            <= set(rubric.get("concept_features") or []),
            f"PF15_RUBRIC_INCOMPLETE:{item_id}",
        )
        require(
            len(item.get("target_sentence_ids")) == 2,
            f"PF15_SENTENCE_SOURCE_COUNT_INVALID:{item_id}",
        )


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("program_id") == builder.PROGRAM_ID, "PROGRAM_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.u10.UNIT_ID, "UNIT_INVALID")
    _validate_digest(payload)

    source = payload.get("source_identity") or {}
    require(
        source.get("sentence_pool_task_id") == builder.SOURCE_TASK_ID,
        "SOURCE_SENTENCE_POOL_TASK_INVALID",
    )
    require(
        source.get("sentence_pool_total") == builder.EXPECTED_SENTENCE_POOL_TOTAL,
        "SOURCE_SENTENCE_POOL_TOTAL_INVALID",
    )
    require(
        bool(source.get("sentence_pool_capability_index_sha256")),
        "SOURCE_SENTENCE_POOL_SHA_MISSING",
    )
    require(
        source.get("blueprint_task_id") == builder.u13.TASK_ID,
        "SOURCE_BLUEPRINT_TASK_INVALID",
    )
    require(
        source.get("blueprint_activity_count")
        == builder.EXPECTED_BLUEPRINT_ACTIVITY_COUNT,
        "SOURCE_BLUEPRINT_ACTIVITY_COUNT_INVALID",
    )

    requirements = payload.get("production_requirements") or {}
    require(
        requirements.get("requirement_count")
        == builder.EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
        "PRODUCTION_REQUIREMENT_COUNT_INVALID",
    )
    require(
        requirements.get("family_counts")
        == builder.EXPECTED_PRODUCTION_FAMILY_COUNTS,
        "PRODUCTION_REQUIREMENT_FAMILY_COUNTS_INVALID",
    )
    require(
        requirements.get("all_requirements_exact_scene_bound") is True,
        "PRODUCTION_REQUIREMENT_SCENE_BINDING_INVALID",
    )

    assignments = payload.get("assignments")
    items = payload.get("materialized_items")
    require(
        isinstance(assignments, list)
        and len(assignments) == builder.EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
        "ASSIGNMENTS_INVALID",
    )
    require(
        isinstance(items, list)
        and len(items) == builder.EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
        "MATERIALIZED_ITEMS_INVALID",
    )
    require(
        len({str(row.get("activity_id")) for row in assignments})
        == builder.EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
        "ASSIGNMENT_ACTIVITY_DUPLICATE",
    )
    require(
        len({str(row.get("item_id")) for row in assignments})
        == builder.EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
        "ASSIGNMENT_ITEM_DUPLICATE",
    )
    item_by_id = {str(item.get("item_id")): item for item in items}
    require(
        set(item_by_id)
        == {str(row.get("item_id")) for row in assignments},
        "ASSIGNMENT_ITEM_SET_DRIFT",
    )
    assignment_counts = Counter(
        str(row.get("pattern_family_id")) for row in assignments
    )
    item_counts = Counter(str(row.get("pattern_family_id")) for row in items)
    require(
        dict(assignment_counts) == builder.EXPECTED_PRODUCTION_FAMILY_COUNTS,
        "ASSIGNMENT_FAMILY_DISTRIBUTION_INVALID",
    )
    require(
        dict(item_counts) == builder.EXPECTED_PRODUCTION_FAMILY_COUNTS,
        "ITEM_FAMILY_DISTRIBUTION_INVALID",
    )
    for assignment in assignments:
        item = item_by_id[str(assignment["item_id"])]
        require(
            item.get("production_activity_id") == assignment.get("activity_id"),
            f"ASSIGNMENT_ACTIVITY_LINEAGE_DRIFT:{assignment.get('activity_id')}",
        )
        require(
            item.get("production_scene_ref_id") == assignment.get("scene_ref_id"),
            f"ASSIGNMENT_SCENE_LINEAGE_DRIFT:{assignment.get('activity_id')}",
        )
        require(
            item.get("pattern_family_id") == assignment.get("pattern_family_id"),
            f"ASSIGNMENT_FAMILY_LINEAGE_DRIFT:{assignment.get('activity_id')}",
        )
        require(
            item.get("source_sentence_ids") == assignment.get("source_sentence_ids"),
            f"ASSIGNMENT_SENTENCE_LINEAGE_DRIFT:{assignment.get('activity_id')}",
        )
        require(
            item.get("target_pattern_ids") == assignment.get("target_pattern_ids"),
            f"ASSIGNMENT_PATTERN_LINEAGE_DRIFT:{assignment.get('activity_id')}",
        )
        _validate_item(item)

    usage = payload.get("sentence_usage") or {}
    require(
        int(usage.get("distinct_sentence_count") or 0) > 0,
        "SENTENCE_USAGE_DISTINCT_INVALID",
    )
    require(
        int(usage.get("sentence_reference_count") or 0)
        >= builder.EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
        "SENTENCE_USAGE_REFERENCE_COUNT_INVALID",
    )
    require(
        int(usage.get("max_reuse_count") or 0) > 0,
        "SENTENCE_USAGE_REUSE_READBACK_INVALID",
    )

    counts = payload.get("count_preservation") or {}
    require(
        counts.get("base_count_before") == builder.EXPECTED_BASE_COUNT,
        "BASE_COUNT_BEFORE_INVALID",
    )
    require(
        counts.get("retired_production_item_count")
        == builder.EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
        "RETIRED_PRODUCTION_COUNT_INVALID",
    )
    require(
        counts.get("materialized_production_item_count")
        == builder.EXPECTED_PRODUCTION_REQUIREMENT_COUNT,
        "MATERIALIZED_PRODUCTION_COUNT_INVALID",
    )
    require(
        counts.get("base_count_after") == builder.EXPECTED_BASE_COUNT,
        "BASE_COUNT_AFTER_INVALID",
    )
    require(
        counts.get("real62_extension_count") == builder.EXPECTED_EXTENSION_COUNT,
        "REAL62_COUNT_INVALID",
    )
    require(
        counts.get("runtime_count_after") == builder.EXPECTED_RUNTIME_COUNT,
        "RUNTIME_COUNT_INVALID",
    )
    require(
        counts.get("question_bank_total_expanded") is False,
        "QUESTIONBANK_EXPANSION_INVALID",
    )

    boundaries = payload.get("boundaries") or {}
    for key in (
        "source_sentence_text_mutated",
        "human_sentence_review_decision_mutated",
        "scoring_architecture_changed",
        "second_question_bank_created",
        "second_runtime_created",
        "source_database_mutated",
        "real62_extension_modified",
        "m3_learner_state_rewritten",
        "m6_attempts_or_scoring_deleted",
        "speaking_scoring_enabled",
        "unit02_to_unit24_modified",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")
    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_STEP_INVALID")
    return validation_receipt(payload)


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(
        candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE,
        "CANDIDATE_ROLE_INVALID",
    )
    require(candidate.get("learner_facing") is False, "CANDIDATE_LEARNER_FACING_INVALID")
    policy_artifact.verify_artifact_digest(candidate)
    source = candidate.get("source_bindings") or {}
    require(
        source.get("sentence_pool_task_id") == builder.SOURCE_TASK_ID,
        "CANDIDATE_SOURCE_SENTENCE_POOL_TASK_INVALID",
    )
    require(
        bool(source.get("sentence_pool_capability_index_sha256")),
        "CANDIDATE_SOURCE_SENTENCE_POOL_SHA_MISSING",
    )
    require(
        source.get("blueprint_task_id") == builder.u13.TASK_ID,
        "CANDIDATE_SOURCE_BLUEPRINT_TASK_INVALID",
    )
    require(source.get("count_preserving") is True, "CANDIDATE_COUNT_PRESERVING_INVALID")
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "CANDIDATE_PAYLOAD_MISSING")
    return validate_payload(payload)


def validate_approved(
    candidate: Mapping[str, Any],
    approved: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        receipt = validate_candidate(candidate)
        require(
            approved.get("artifact_role") == policy_artifact.APPROVED_ROLE,
            "APPROVED_ROLE_INVALID",
        )
        require(
            approved.get("learner_facing") is False,
            "APPROVED_LEARNER_FACING_INVALID",
        )
        require(
            (approved.get("admission") or {}).get("status") == "APPROVED",
            "APPROVED_STATUS_INVALID",
        )
        require(
            (approved.get("admission") or {}).get("decision_ref")
            == builder.DECISION_REF,
            "APPROVED_DECISION_INVALID",
        )
        require(
            approved.get("payload") == candidate.get("payload"),
            "APPROVED_PAYLOAD_DRIFT",
        )
        require(
            (approved.get("source_bindings") or {}).get(
                "candidate_artifact_sha256"
            )
            == candidate.get("artifact_sha256"),
            "APPROVED_CANDIDATE_BINDING_INVALID",
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
            "APPROVED_RECEIPT_INVALID",
        )
        policy_artifact.verify_artifact_digest(approved)
        validate_payload(approved["payload"])
    except (
        SentencePoolCapacityValidationError,
        policy_artifact.ContentPolicyBuildError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    payload = approved.get("payload") or {}
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "candidate_artifact_sha256": candidate.get("artifact_sha256"),
        "approved_artifact_sha256": approved.get("artifact_sha256"),
        "production_requirement_count": (
            payload.get("production_requirements") or {}
        ).get("requirement_count", 0),
        "materialized_item_count": len(payload.get("materialized_items") or []),
        "runtime_count_after": (payload.get("count_preservation") or {}).get(
            "runtime_count_after", 0
        ),
    }
