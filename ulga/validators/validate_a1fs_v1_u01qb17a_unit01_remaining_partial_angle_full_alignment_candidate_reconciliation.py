#!/usr/bin/env python3
"""Validate U01QB17A count-preserving full-alignment candidate reconciliation."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u01qb17a_unit01_remaining_partial_angle_full_alignment_candidate_reconciliation as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB17A_UNIT01_REMAINING_PARTIAL_ANGLE_FULL_ALIGNMENT_CANDIDATE_RECONCILIATION_VALIDATOR"


class FullAlignmentValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise FullAlignmentValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def _source() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return builder.source_bank()


def _expected_sources(items: list[dict[str, Any]], family_id: str) -> list[dict[str, Any]]:
    return sorted(
        (row for row in items if row.get("pattern_family_id") == family_id),
        key=lambda row: str(row["item_id"]),
    )[: builder.REPLACEMENTS_PER_FAMILY]


def _validate_digest(payload: Mapping[str, Any]) -> None:
    unsigned = dict(payload)
    actual = unsigned.pop("reconciliation_sha256", None)
    require(actual == policy_artifact.digest(unsigned), "RECONCILIATION_DIGEST_INVALID")


def _validate_pf16(item: Mapping[str, Any]) -> None:
    item_id = str(item.get("item_id") or "")
    require(item.get("skill") == "READING", f"PF16_SKILL_INVALID:{item_id}")
    require(item.get("question_type") == "reference_evidence", f"PF16_TYPE_INVALID:{item_id}")
    require(item.get("task_angle") == "REFERENCE_EVIDENCE", f"PF16_ANGLE_INVALID:{item_id}")
    require(item.get("scoring_mode") == "EXACT_TEXT", f"PF16_MODE_INVALID:{item_id}")
    require(item.get("support_level") in {"REDUCED_SUPPORT", "INDEPENDENT"}, f"PF16_SUPPORT_INVALID:{item_id}")
    response = item.get("response_contract") or {}
    require(response.get("scoring_mode") == "EXACT_TEXT", f"PF16_RESPONSE_MODE_INVALID:{item_id}")
    require(response.get("capture_enabled") is True, f"PF16_CAPTURE_INVALID:{item_id}")
    require(response.get("human_review_fallback") is False, f"PF16_REVIEW_INVALID:{item_id}")
    require(item.get("correct_answer") in item.get("options", []), f"PF16_ANSWER_OPTION_INVALID:{item_id}")
    require(str(item.get("correct_answer") or "").startswith("The "), f"PF16_REFERENCE_EVIDENCE_INVALID:{item_id}")


def _validate_pf17(item: Mapping[str, Any]) -> None:
    item_id = str(item.get("item_id") or "")
    require(item.get("skill") == "WRITING", f"PF17_SKILL_INVALID:{item_id}")
    require(item.get("question_type") == "phrase_construction", f"PF17_TYPE_INVALID:{item_id}")
    require(item.get("task_angle") == "PHRASE_CONSTRUCTION", f"PF17_ANGLE_INVALID:{item_id}")
    require(item.get("scoring_mode") == "NORMALIZED_TEXT", f"PF17_MODE_INVALID:{item_id}")
    require(item.get("support_level") in {"GUIDED", "REDUCED_SUPPORT"}, f"PF17_SUPPORT_INVALID:{item_id}")
    require(item.get("options") == [], f"PF17_OPTIONS_INVALID:{item_id}")
    response = item.get("response_contract") or {}
    require(response.get("scoring_mode") == "NORMALIZED_TEXT", f"PF17_RESPONSE_MODE_INVALID:{item_id}")
    require(response.get("capture_enabled") is True, f"PF17_CAPTURE_INVALID:{item_id}")
    require(response.get("human_review_fallback") is False, f"PF17_REVIEW_INVALID:{item_id}")
    model = str(item.get("correct_answer") or "")
    require(bool(model), f"PF17_MODEL_MISSING:{item_id}")
    require(model in response.get("accepted_texts", []), f"PF17_MODEL_BINDING_INVALID:{item_id}")


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("program_id") == builder.PROGRAM_ID, "PROGRAM_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")
    _validate_digest(payload)

    approved_source, source_items = _source()
    source = payload.get("source_identity") or {}
    require(source.get("source_task_id") == builder.u10.TASK_ID, "SOURCE_TASK_INVALID")
    require(source.get("source_canonical_revision") == builder.u10.CANONICAL_REVISION, "SOURCE_REVISION_INVALID")
    require(source.get("source_approved_artifact_sha256") == approved_source["artifact_sha256"], "SOURCE_ARTIFACT_INVALID")
    require(source.get("source_base_count") == builder.EXPECTED_BASE_COUNT, "SOURCE_COUNT_INVALID")

    identity = payload.get("bank_identity") or {}
    require(identity.get("bank_id") == builder.BANK_ID, "BANK_ID_INVALID")
    require(identity.get("bank_version") == builder.BANK_VERSION, "BANK_VERSION_INVALID")
    require(identity.get("canonical_revision") == builder.CANONICAL_REVISION, "REVISION_INVALID")
    require(identity.get("second_question_bank_created") is False, "SECOND_BANK_INVALID")

    counts = payload.get("count_preservation") or {}
    require(counts.get("source_base_count") == 288, "SOURCE_BASE_COUNT_INVALID")
    require(counts.get("retained_base_count") == 264, "RETAINED_COUNT_INVALID")
    require(counts.get("removed_base_count") == 24, "REMOVED_COUNT_INVALID")
    require(counts.get("full_alignment_items_added") == 24, "ADDED_COUNT_INVALID")
    require(counts.get("reconciled_base_count") == 288, "RECONCILED_COUNT_INVALID")
    require(counts.get("unchanged_real62_extension_count") == 186, "EXTENSION_COUNT_INVALID")
    require(counts.get("projected_runtime_total_count") == 474, "PROJECTED_RUNTIME_COUNT_INVALID")
    require(counts.get("runtime_activation_completed") is False, "RUNTIME_ACTIVATION_INVALID")

    expected_reference = _expected_sources(source_items, builder.SOURCE_REFERENCE_FAMILY)
    expected_phrase = _expected_sources(source_items, builder.SOURCE_PHRASE_FAMILY)
    expected_removed = {str(row["item_id"]) for row in [*expected_reference, *expected_phrase]}
    plan = payload.get("replacement_plan") or []
    require(len(plan) == 2, "REPLACEMENT_PLAN_INVALID")
    by_source = {str(row.get("source_pattern_family_id")): row for row in plan}
    require(set(by_source) == {builder.SOURCE_REFERENCE_FAMILY, builder.SOURCE_PHRASE_FAMILY}, "REPLACEMENT_SOURCES_INVALID")
    require(by_source[builder.SOURCE_REFERENCE_FAMILY].get("replacement_pattern_family_id") == builder.PF16, "PF16_REPLACEMENT_INVALID")
    require(by_source[builder.SOURCE_PHRASE_FAMILY].get("replacement_pattern_family_id") == builder.PF17, "PF17_REPLACEMENT_INVALID")
    require(by_source[builder.SOURCE_REFERENCE_FAMILY].get("replacement_count") == 12, "PF16_COUNT_INVALID")
    require(by_source[builder.SOURCE_PHRASE_FAMILY].get("replacement_count") == 12, "PF17_COUNT_INVALID")

    items = payload.get("reconciled_items")
    require(isinstance(items, list) and len(items) == 288, "ITEMS_INVALID")
    require(len({str(row.get("item_id")) for row in items}) == 288, "DUPLICATE_ITEM_ID")
    require(len({str(row.get("semantic_signature")) for row in items}) == 288, "DUPLICATE_SEMANTIC_SIGNATURE")
    source_by_id = {str(row["item_id"]): row for row in source_items}
    result_by_id = {str(row["item_id"]): row for row in items}
    retained_ids = set(source_by_id) - expected_removed
    require(retained_ids <= set(result_by_id), "RETAINED_ITEM_MISSING")
    for item_id in retained_ids:
        require(result_by_id[item_id] == source_by_id[item_id], f"RETAINED_ITEM_DRIFT:{item_id}")
    require(not (expected_removed & set(result_by_id)), "REMOVED_ITEM_STILL_PRESENT")

    pf16 = [row for row in items if row.get("pattern_family_id") == builder.PF16]
    pf17 = [row for row in items if row.get("pattern_family_id") == builder.PF17]
    require(len(pf16) == len(pf17) == 12, "FULL_ALIGNMENT_FAMILY_COUNT_INVALID")
    require({str(row.get("reconciliation_source_item_id")) for row in [*pf16, *pf17]} == expected_removed, "SOURCE_LINEAGE_INVALID")
    for item in pf16:
        _validate_pf16(item)
    for item in pf17:
        _validate_pf17(item)
    require(Counter(row["support_level"] for row in pf16) == Counter({"REDUCED_SUPPORT": 6, "INDEPENDENT": 6}), "PF16_SUPPORT_PROGRESSION_INVALID")
    require(Counter(row["support_level"] for row in pf17) == Counter({"GUIDED": 6, "REDUCED_SUPPORT": 6}), "PF17_SUPPORT_PROGRESSION_INVALID")

    source_family_counts = Counter(str(row["pattern_family_id"]) for row in source_items)
    result_family_counts = Counter(str(row["pattern_family_id"]) for row in items)
    expected_family_counts = source_family_counts.copy()
    expected_family_counts[builder.SOURCE_REFERENCE_FAMILY] -= 12
    expected_family_counts[builder.SOURCE_PHRASE_FAMILY] -= 12
    expected_family_counts[builder.PF16] += 12
    expected_family_counts[builder.PF17] += 12
    require(result_family_counts == expected_family_counts, "FAMILY_DISTRIBUTION_INVALID")
    require((payload.get("distribution_counts") or {}).get("family") == dict(sorted(result_family_counts.items())), "FAMILY_READBACK_INVALID")

    alignment = payload.get("partial_angle_alignment") or {}
    require(alignment.get("scored_partial_support_slots_before") == 36, "PARTIAL_BEFORE_INVALID")
    require(alignment.get("remaining_partial_angles_before") == list(builder.EXPECTED_PARTIAL_ANGLES_BEFORE), "PARTIAL_IDENTITY_BEFORE_INVALID")
    require(alignment.get("explicit_full_support_families_added") == [builder.PF16, builder.PF17], "FULL_SUPPORT_FAMILIES_INVALID")
    require(alignment.get("remaining_partial_angles_after_candidate_reconciliation") == [], "PARTIAL_AFTER_INVALID")
    require(alignment.get("content_contract_full_alignment_candidate_ready") is True, "CONTENT_ALIGNMENT_READY_INVALID")
    require(alignment.get("runtime_capacity_replay_pending") is True, "RUNTIME_REPLAY_PENDING_INVALID")
    require(alignment.get("runtime_full_alignment_claimed") is False, "RUNTIME_ALIGNMENT_PREMATURE_CLAIM")

    boundaries = payload.get("boundaries") or {}
    for key in (
        "question_bank_total_expanded",
        "second_question_bank_created",
        "runtime_migrated",
        "real62_extension_modified",
        "learner_state_modified",
        "completed_attempts_modified",
        "speaking_scoring_enabled",
        "audio_enabled",
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
    require(source.get("source_task_id") == builder.u10.TASK_ID, "BINDING_SOURCE_TASK_INVALID")
    require(source.get("source_canonical_revision") == builder.u10.CANONICAL_REVISION, "BINDING_REVISION_INVALID")
    require(source.get("bank_id") == builder.BANK_ID, "BINDING_BANK_INVALID")
    require(source.get("bank_version") == builder.BANK_VERSION, "BINDING_VERSION_INVALID")
    require(source.get("count_preserving") is True, "BINDING_COUNT_INVALID")
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
        require((approved.get("source_bindings") or {}).get("candidate_artifact_sha256") == candidate.get("artifact_sha256"), "CANDIDATE_BINDING_INVALID")
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
        FullAlignmentValidationError,
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
        "remaining_partial_angle_count": len((payload.get("partial_angle_alignment") or {}).get("remaining_partial_angles_after_candidate_reconciliation", [])),
        "runtime_migrated": (payload.get("boundaries") or {}).get("runtime_migrated"),
    }
