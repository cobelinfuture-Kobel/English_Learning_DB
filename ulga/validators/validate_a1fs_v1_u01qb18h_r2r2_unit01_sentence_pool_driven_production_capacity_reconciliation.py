#!/usr/bin/env python3
"""Validate blueprint-authoritative R2R2 sentence-pool production reconciliation."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
    as builder,
)
from ulga.validators import _u01qb18h_r2r2_fixed48_legacy_validator as legacy_validator

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


def _normalized_family_counts(values: Mapping[str, int] | Counter[str]) -> dict[str, int]:
    return {
        family: int(values.get(family, 0))
        for family in builder.HISTORICAL_PRODUCTION_FAMILY_COUNTS
    }


def _validate_dynamic_family_counts(counts: Mapping[str, int], requirement_count: int) -> None:
    normalized = _normalized_family_counts(counts)
    require(sum(normalized.values()) == requirement_count, "PRODUCTION_FAMILY_COUNT_SUM_INVALID")
    for family, historical_capacity in builder.HISTORICAL_PRODUCTION_FAMILY_COUNTS.items():
        requested = normalized[family]
        require(
            0 <= requested <= int(historical_capacity),
            f"PRODUCTION_FAMILY_CAPACITY_INVALID:{family}:{requested}:{historical_capacity}",
        )


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("program_id") == builder.PROGRAM_ID, "PROGRAM_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.u10.UNIT_ID, "UNIT_INVALID")
    unsigned = dict(payload)
    actual_digest = unsigned.pop("reconciliation_sha256", None)
    require(actual_digest == policy_artifact.digest(unsigned), "RECONCILIATION_DIGEST_INVALID")

    source = payload.get("source_identity") or {}
    require(source.get("sentence_pool_task_id") == builder.SOURCE_TASK_ID, "SOURCE_SENTENCE_POOL_TASK_INVALID")
    require(source.get("sentence_pool_total") == builder.EXPECTED_SENTENCE_POOL_TOTAL, "SOURCE_SENTENCE_POOL_TOTAL_INVALID")
    require(bool(source.get("sentence_pool_capability_index_sha256")), "SOURCE_SENTENCE_POOL_SHA_MISSING")
    require(source.get("blueprint_task_id") == builder.u13.TASK_ID, "SOURCE_BLUEPRINT_TASK_INVALID")
    require(source.get("blueprint_activity_count") == builder.EXPECTED_BLUEPRINT_ACTIVITY_COUNT, "SOURCE_BLUEPRINT_ACTIVITY_COUNT_INVALID")
    require(
        source.get("historical_production_inventory_count")
        == builder.HISTORICAL_PRODUCTION_INVENTORY_COUNT,
        "HISTORICAL_PRODUCTION_INVENTORY_COUNT_INVALID",
    )

    requirements = payload.get("production_requirements") or {}
    requirement_count = int(requirements.get("requirement_count") or 0)
    require(
        0 < requirement_count <= builder.HISTORICAL_PRODUCTION_INVENTORY_COUNT,
        f"PRODUCTION_REQUIREMENT_COUNT_INVALID:{requirement_count}",
    )
    require(
        requirements.get("denominator_authority") == "U01QB13_BLUEPRINT_ACTIVITIES",
        "PRODUCTION_DENOMINATOR_AUTHORITY_INVALID",
    )
    family_counts = _normalized_family_counts(requirements.get("family_counts") or {})
    _validate_dynamic_family_counts(family_counts, requirement_count)
    require(requirements.get("all_requirements_exact_scene_bound") is True, "PRODUCTION_REQUIREMENT_SCENE_BINDING_INVALID")

    assignments = payload.get("assignments")
    items = payload.get("materialized_items")
    require(isinstance(assignments, list) and len(assignments) == requirement_count, "ASSIGNMENTS_INVALID")
    require(isinstance(items, list) and len(items) == requirement_count, "MATERIALIZED_ITEMS_INVALID")
    require(len({str(row.get("activity_id")) for row in assignments}) == requirement_count, "ASSIGNMENT_ACTIVITY_DUPLICATE")
    require(len({str(row.get("item_id")) for row in assignments}) == requirement_count, "ASSIGNMENT_ITEM_DUPLICATE")
    item_by_id = {str(item.get("item_id")): item for item in items}
    require(set(item_by_id) == {str(row.get("item_id")) for row in assignments}, "ASSIGNMENT_ITEM_SET_DRIFT")
    assignment_counts = _normalized_family_counts(
        Counter(str(row.get("pattern_family_id")) for row in assignments)
    )
    item_counts = _normalized_family_counts(
        Counter(str(item.get("pattern_family_id")) for item in items)
    )
    require(assignment_counts == family_counts, "ASSIGNMENT_FAMILY_DISTRIBUTION_INVALID")
    require(item_counts == family_counts, "ITEM_FAMILY_DISTRIBUTION_INVALID")

    for assignment in assignments:
        item = item_by_id[str(assignment["item_id"])]
        require(item.get("production_activity_id") == assignment.get("activity_id"), f"ASSIGNMENT_ACTIVITY_LINEAGE_DRIFT:{assignment.get('activity_id')}")
        require(item.get("production_scene_ref_id") == assignment.get("scene_ref_id"), f"ASSIGNMENT_SCENE_LINEAGE_DRIFT:{assignment.get('activity_id')}")
        require(item.get("pattern_family_id") == assignment.get("pattern_family_id"), f"ASSIGNMENT_FAMILY_LINEAGE_DRIFT:{assignment.get('activity_id')}")
        require(item.get("source_sentence_ids") == assignment.get("source_sentence_ids"), f"ASSIGNMENT_SENTENCE_LINEAGE_DRIFT:{assignment.get('activity_id')}")
        require(item.get("target_pattern_ids") == assignment.get("target_pattern_ids"), f"ASSIGNMENT_PATTERN_LINEAGE_DRIFT:{assignment.get('activity_id')}")
        legacy_validator._validate_item(item)

    usage = payload.get("sentence_usage") or {}
    require(int(usage.get("distinct_sentence_count") or 0) > 0, "SENTENCE_USAGE_DISTINCT_INVALID")
    require(int(usage.get("sentence_reference_count") or 0) >= requirement_count, "SENTENCE_USAGE_REFERENCE_COUNT_INVALID")
    require(int(usage.get("max_reuse_count") or 0) > 0, "SENTENCE_USAGE_REUSE_READBACK_INVALID")

    counts = payload.get("count_preservation") or {}
    require(counts.get("base_count_before") == builder.EXPECTED_BASE_COUNT, "BASE_COUNT_BEFORE_INVALID")
    require(counts.get("retired_production_item_count") == requirement_count, "RETIRED_PRODUCTION_COUNT_INVALID")
    require(counts.get("materialized_production_item_count") == requirement_count, "MATERIALIZED_PRODUCTION_COUNT_INVALID")
    require(counts.get("base_count_after") == builder.EXPECTED_BASE_COUNT, "BASE_COUNT_AFTER_INVALID")
    require(counts.get("real62_extension_count") == builder.EXPECTED_EXTENSION_COUNT, "REAL62_COUNT_INVALID")
    require(counts.get("runtime_count_after") == builder.EXPECTED_RUNTIME_COUNT, "RUNTIME_COUNT_INVALID")
    require(counts.get("question_bank_total_expanded") is False, "QUESTIONBANK_EXPANSION_INVALID")

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
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "CANDIDATE_ROLE_INVALID")
    require(candidate.get("learner_facing") is False, "CANDIDATE_LEARNER_FACING_INVALID")
    policy_artifact.verify_artifact_digest(candidate)
    source = candidate.get("source_bindings") or {}
    require(source.get("sentence_pool_task_id") == builder.SOURCE_TASK_ID, "CANDIDATE_SOURCE_SENTENCE_POOL_TASK_INVALID")
    require(bool(source.get("sentence_pool_capability_index_sha256")), "CANDIDATE_SOURCE_SENTENCE_POOL_SHA_MISSING")
    require(source.get("blueprint_task_id") == builder.u13.TASK_ID, "CANDIDATE_SOURCE_BLUEPRINT_TASK_INVALID")
    require(source.get("count_preserving") is True, "CANDIDATE_COUNT_PRESERVING_INVALID")
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
        require((approved.get("admission") or {}).get("decision_ref") == builder.DECISION_REF, "APPROVED_DECISION_INVALID")
        require(approved.get("payload") == candidate.get("payload"), "APPROVED_PAYLOAD_DRIFT")
        require(
            (approved.get("source_bindings") or {}).get("candidate_artifact_sha256")
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
