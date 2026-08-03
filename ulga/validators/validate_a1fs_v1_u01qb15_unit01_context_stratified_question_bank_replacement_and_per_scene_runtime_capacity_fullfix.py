#!/usr/bin/env python3
"""Validate U01QB15 context-stratified QuestionBank and scene capacity proof."""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix as builder

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB15_CONTEXT_STRATIFIED_QUESTION_BANK_FULLFIX_VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_U01QB15_CONTEXT_STRATIFIED_QUESTION_BANK_FULLFIX_VALIDATION"


class U01QB15ValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise U01QB15ValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def _pair(row: Mapping[str, Any]) -> tuple[str, str]:
    return builder._pair_key(row)


def _context_counts(rows: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(_pair(row)[0] for row in rows)
    return {context: counts.get(context, 0) for context in builder.u01qb10.seed.CONTEXT_IDS}


def _validate_digest(payload: Mapping[str, Any]) -> None:
    unsigned = dict(payload)
    actual = unsigned.pop("reconciliation_sha256", None)
    require(actual == policy_artifact.digest(unsigned), "RECONCILIATION_DIGEST_INVALID")


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("program_id") == builder.PROGRAM_ID, "PROGRAM_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")
    _validate_digest(payload)

    identity = payload.get("bank_identity") or {}
    require(identity.get("bank_id") == builder.BANK_ID, "BANK_ID_INVALID")
    require(identity.get("bank_version") == builder.BANK_VERSION, "BANK_VERSION_INVALID")
    require(identity.get("canonical_revision") == builder.CANONICAL_REVISION, "REVISION_INVALID")
    require(identity.get("historical_task_identity_rewritten") is False, "HISTORICAL_IDENTITY_REWRITE_INVALID")
    require(identity.get("second_question_bank_created") is False, "SECOND_BANK_CREATED")

    counts = payload.get("count_preservation") or {}
    require(counts.get("base_item_count") == builder.EXPECTED_BASE_COUNT, "BASE_COUNT_INVALID")
    require(counts.get("u01qb10_retired_and_added") == builder.EXPECTED_U01QB10_RETIRED, "U01QB10_DELTA_INVALID")
    require(counts.get("u01qb12_retired_and_added") == builder.EXPECTED_U01QB12_RETIRED, "U01QB12_DELTA_INVALID")
    require(counts.get("unchanged_real62_extension_count") == builder.EXPECTED_EXTENSION_COUNT, "REAL62_COUNT_INVALID")
    require(counts.get("projected_runtime_total_count") == builder.EXPECTED_RUNTIME_COUNT, "RUNTIME_COUNT_INVALID")

    seed_approved, seed_items = builder.u01qb10.seed_bank()
    replacements = builder.context_stratified_u01qb10_replacement_sources(seed_items)
    replacement = payload.get("u01qb10_context_stratified_replacement") or {}
    require(replacement.get("context_quota") == builder.U01QB10_CONTEXT_QUOTA, "U01QB10_CONTEXT_QUOTA_INVALID")
    require(replacement.get("reading_retired_context_noun_pairs_unique") is True, "READING_RETIREMENT_UNIQUENESS_NOT_DECLARED")
    require(replacement.get("reading_retired_pair_count") == 36, "READING_RETIRED_PAIR_COUNT_INVALID")
    declared_by_family = replacement.get("replacement_source_ids_by_family") or {}
    require(set(declared_by_family) == set(builder.u01qb10.REPLACEMENT_PLAN), "REPLACEMENT_FAMILY_SET_INVALID")
    for family, rows in replacements.items():
        require(
            declared_by_family.get(family) == [str(row["item_id"]) for row in rows],
            f"REPLACEMENT_SOURCE_IDS_INVALID:{family}",
        )
        require(_context_counts(rows) == builder.U01QB10_CONTEXT_QUOTA, f"REPLACEMENT_CONTEXT_COUNTS_INVALID:{family}")

    reading_pairs = [
        _pair(row)
        for family in builder.READING_REPLACEMENT_FAMILIES
        for row in replacements[family]
    ]
    require(len(reading_pairs) == len(set(reading_pairs)) == 36, "READING_CONTEXT_NOUN_RETIREMENT_OVERLAP")

    intermediate = builder.build_context_stratified_u01qb10_items()[1]
    expected_reference = builder.context_stratified_u01qb12_reference_sources(intermediate)
    reference = payload.get("u01qb12_context_stratified_reference_replacement") or {}
    require(reference.get("replacement_count") == 24, "REFERENCE_COUNT_INVALID")
    require(reference.get("context_quota") == builder.U01QB12_REFERENCE_CONTEXT_QUOTA, "REFERENCE_CONTEXT_QUOTA_INVALID")
    require(reference.get("replacement_family_id") == builder.u01qb12.PF16, "REFERENCE_FAMILY_INVALID")
    require(reference.get("source_item_ids") == [str(row["item_id"]) for row in expected_reference], "REFERENCE_SOURCE_IDS_INVALID")
    require(_context_counts(expected_reference) == builder.U01QB12_REFERENCE_CONTEXT_QUOTA, "REFERENCE_CONTEXT_COUNTS_INVALID")

    items = payload.get("reconciled_items")
    require(isinstance(items, list) and len(items) == builder.EXPECTED_BASE_COUNT, "RECONCILED_ITEMS_INVALID")
    require(len({str(row.get("item_id")) for row in items}) == builder.EXPECTED_BASE_COUNT, "DUPLICATE_ITEM_ID")
    require(len({str(row.get("semantic_signature")) for row in items}) == builder.EXPECTED_BASE_COUNT, "DUPLICATE_SEMANTIC_SIGNATURE")
    family_counts = dict(sorted(Counter(str(row["pattern_family_id"]) for row in items).items()))
    skill_counts = dict(sorted(Counter(str(row["skill"]) for row in items).items()))
    require(family_counts == builder.EXPECTED_FINAL_FAMILY_COUNTS, "FINAL_FAMILY_DISTRIBUTION_INVALID")
    require(skill_counts == builder.EXPECTED_FINAL_SKILL_COUNTS, "FINAL_SKILL_DISTRIBUTION_INVALID")
    distribution = payload.get("distribution_counts") or {}
    require(distribution.get("family") == family_counts, "FAMILY_READBACK_INVALID")
    require(distribution.get("skill") == skill_counts, "SKILL_READBACK_INVALID")

    # Every original legal context+noun pair must keep at least two context-bound
    # Reading identities after U01QB10 replacement and PF05→PF16 conversion.
    tracked = {*builder.READING_REPLACEMENT_FAMILIES, builder.u01qb12.PF16}
    by_pair: Counter[tuple[str, str]] = Counter()
    for row in items:
        if str(row.get("pattern_family_id")) in tracked:
            pair = _pair(row)
            if pair[0] and pair[1]:
                by_pair[pair] += 1
    seed_pairs = {
        _pair(row)
        for row in seed_items
        if row.get("pattern_family_id") == builder.READING_REPLACEMENT_FAMILIES[0]
    }
    require(len(seed_pairs) == 47, "SEED_CONTEXT_NOUN_PAIR_COUNT_INVALID")
    require(all(by_pair[pair] >= 2 for pair in seed_pairs), "READING_CONTEXT_NOUN_SURVIVAL_BELOW_TWO")
    survival = payload.get("reading_context_noun_survival") or {}
    require(survival.get("approved_context_noun_pair_count") == 47, "SURVIVAL_PAIR_COUNT_INVALID")
    require(survival.get("minimum_surviving_context_bound_reading_identities_per_pair") >= 2, "SURVIVAL_MINIMUM_INVALID")
    require(survival.get("all_pairs_retain_at_least_two_context_bound_reading_identities") is True, "SURVIVAL_PASS_INVALID")

    capacity = payload.get("per_scene_runtime_capacity") or {}
    require(capacity.get("proof_mode") == "FINAL_288_BASE_ONLY_NO_REAL62_ASSISTANCE", "CAPACITY_PROOF_MODE_INVALID")
    require(capacity.get("base_item_count") == 288, "CAPACITY_BASE_COUNT_INVALID")
    require(capacity.get("cumulative_scene_world_count") == 32, "CAPACITY_SCENE_WORLD_INVALID")
    require(capacity.get("runtime_bindable_scene_count") == 31, "CAPACITY_BINDABLE_SCENES_INVALID")
    require(capacity.get("deferred_scene_refs") == ["U01-MA-FOOD-04"], "CAPACITY_DEFERRED_SCENE_INVALID")
    require(capacity.get("form_count") == 12, "CAPACITY_FORM_COUNT_INVALID")
    require(capacity.get("skill_session_count") == 36, "CAPACITY_SESSION_COUNT_INVALID")
    require(capacity.get("verified_activity_count") == 240, "CAPACITY_ACTIVITY_COUNT_INVALID")
    require(capacity.get("all_36_skill_sessions_distinct_item_capacity_proven") is True, "CAPACITY_MATCHING_NOT_PROVEN")
    require(capacity.get("real62_used_for_capacity_proof") is False, "REAL62_MASKED_BASE_DEFICIT")

    boundaries = payload.get("boundaries") or {}
    for key in (
        "question_bank_total_expanded",
        "real62_extension_modified",
        "new_scene_authored",
        "second_planner_created",
        "second_runtime_created",
        "parallel_database_created",
        "parallel_scoring_created",
        "speaking_capture_enabled",
        "speaking_scoring_enabled",
        "unit02_to_unit24_modified",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")

    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_SHORT_STEP_INVALID")
    return validation_receipt(payload)


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as policy_validator

    policy_validator.validate_artifact(candidate, expected_role=policy_artifact.CANDIDATE_ROLE)
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "CANDIDATE_PAYLOAD_MISSING")
    return validate_payload(payload)


def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as policy_validator

    errors: list[str] = []
    try:
        candidate_receipt = validate_candidate(candidate)
        policy_validator.validate_artifact(approved, expected_role=policy_artifact.APPROVED_ROLE)
        require(approved.get("payload") == candidate.get("payload"), "APPROVED_PAYLOAD_DRIFT")
        receipts = approved.get("validation_receipts") or []
        require(any(row.get("receipt_sha256") == candidate_receipt["receipt_sha256"] for row in receipts), "APPROVED_RECEIPT_MISSING")
        validate_payload(approved["payload"])
    except Exception as exc:
        errors.append(str(exc))
    return {
        "validation_status": PASS_STATUS if not errors else "FAIL_A1FS_V1_U01QB15_CONTEXT_STRATIFIED_QUESTION_BANK_FULLFIX_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "base_item_count": len((approved.get("payload") or {}).get("reconciled_items") or []),
        "projected_runtime_total_count": ((approved.get("payload") or {}).get("count_preservation") or {}).get("projected_runtime_total_count"),
    }
