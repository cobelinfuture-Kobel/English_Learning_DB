#!/usr/bin/env python3
"""Validate U01QB12 count-preserving exact-support reconciliation and runtime replay."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as u01qb10
from ulga.builders import build_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as builder

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB12_UNIT01_REFERENCE_EVIDENCE_AND_PHRASE_CONSTRUCTION_PARTIAL_COVERAGE_FULLFIX_VALIDATOR"
EXPECTED_FAMILY_COUNTS = {
    "U01-PF01-AAN-NOUN-GAP": 16,
    "U01-PF02-AAN-ADJ-NOUN-GAP": 6,
    "U01-PF03-VERY-ADJ-NOUN-GAP": 3,
    "U01-PF04-FIRST-MENTION-CONTEXT": 35,
    "U01-PF05-KNOWN-REFERENCE-CONTEXT": 11,
    "U01-PF06-ERROR-DISCRIMINATION": 25,
    "U01-PF07-WORD-ORDER": 13,
    "U01-PF08-TRANSFER-FIRST-MENTION": 35,
    "U01-PF09-TRANSFER-KNOWN-REFERENCE": 35,
    "U01-PF10-SPEAK-NOUN": 16,
    "U01-PF11-SPEAK-ADJ-NOUN": 6,
    "U01-PF12-SPEAK-VERY-ADJ-NOUN": 3,
    u01qb10.PF13: 12,
    u01qb10.PF14: 24,
    u01qb10.PF15: 12,
    builder.PF16: 24,
    builder.PF17: 12,
}


class PartialCoverageFullFixValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise PartialCoverageFullFixValidationError(code)


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
    require(actual == policy_artifact.digest(unsigned), "RECONCILIATION_DIGEST_INVALID")


def _source_authority() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return builder._u01qb10_authority()


def _expected_sources(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return builder._reference_sources(items), builder._phrase_sources(items)


def _validate_pf16(item: Mapping[str, Any]) -> None:
    item_id = str(item.get("item_id") or "")
    require(item.get("skill") == "READING", f"PF16_SKILL_INVALID:{item_id}")
    require(item.get("question_type") == "reference_evidence", f"PF16_TYPE_INVALID:{item_id}")
    require(item.get("task_angle") == "REFERENCE_EVIDENCE", f"PF16_ANGLE_INVALID:{item_id}")
    require(item.get("scoring_mode") == "EXACT_OPTION", f"PF16_MODE_INVALID:{item_id}")
    require(item.get("support_level") in set(builder.REFERENCE_SUPPORT_SEQUENCE), f"PF16_SUPPORT_INVALID:{item_id}")
    require(item.get("assessment_eligible") is True, f"PF16_ASSESSMENT_INVALID:{item_id}")
    require(item.get("reassessment_eligible") is True, f"PF16_REASSESSMENT_INVALID:{item_id}")
    require(item.get("human_review_required") is False, f"PF16_REVIEW_INVALID:{item_id}")
    require(item.get("audio_required") is False, f"PF16_AUDIO_INVALID:{item_id}")
    require(item.get("speaking_capture_enabled") is False, f"PF16_SPEAKING_INVALID:{item_id}")
    answer = str(item.get("correct_answer") or "")
    require(answer.startswith("the "), f"PF16_REFERENCE_ANSWER_INVALID:{item_id}")
    require(answer in list(item.get("options") or []), f"PF16_OPTION_ANSWER_MISSING:{item_id}")
    require(len(list(item.get("options") or [])) == 2, f"PF16_OPTIONS_INVALID:{item_id}")
    response = item.get("response_contract") or {}
    require(response.get("scoring_mode") == "EXACT_OPTION", f"PF16_RESPONSE_MODE_INVALID:{item_id}")
    require(response.get("response_type") == "string", f"PF16_RESPONSE_TYPE_INVALID:{item_id}")
    require(response.get("capture_enabled") is True, f"PF16_CAPTURE_INVALID:{item_id}")
    require(response.get("human_review_fallback") is False, f"PF16_HUMAN_REVIEW_INVALID:{item_id}")
    require(response.get("accepted_texts") == [answer], f"PF16_ACCEPTED_TEXT_INVALID:{item_id}")
    require(bool(item.get("reconciliation_source_item_id")), f"PF16_SOURCE_MISSING:{item_id}")


def _validate_pf17(item: Mapping[str, Any]) -> None:
    item_id = str(item.get("item_id") or "")
    require(item.get("skill") == "WRITING", f"PF17_SKILL_INVALID:{item_id}")
    require(item.get("question_type") == "phrase_construction", f"PF17_TYPE_INVALID:{item_id}")
    require(item.get("task_angle") == "PHRASE_CONSTRUCTION", f"PF17_ANGLE_INVALID:{item_id}")
    require(item.get("scoring_mode") == "NORMALIZED_TEXT", f"PF17_MODE_INVALID:{item_id}")
    require(item.get("support_level") in set(builder.PHRASE_SUPPORT_SEQUENCE), f"PF17_SUPPORT_INVALID:{item_id}")
    require(item.get("assessment_eligible") is True, f"PF17_ASSESSMENT_INVALID:{item_id}")
    require(item.get("reassessment_eligible") is True, f"PF17_REASSESSMENT_INVALID:{item_id}")
    require(item.get("human_review_required") is False, f"PF17_REVIEW_INVALID:{item_id}")
    require(item.get("audio_required") is False, f"PF17_AUDIO_INVALID:{item_id}")
    require(item.get("speaking_capture_enabled") is False, f"PF17_SPEAKING_INVALID:{item_id}")
    answer = str(item.get("correct_answer") or "")
    require(bool(answer) and " " in answer, f"PF17_MODEL_ANSWER_INVALID:{item_id}")
    require(item.get("options") == [], f"PF17_OPTIONS_INVALID:{item_id}")
    response = item.get("response_contract") or {}
    require(response.get("scoring_mode") == "NORMALIZED_TEXT", f"PF17_RESPONSE_MODE_INVALID:{item_id}")
    require(response.get("response_type") == "string", f"PF17_RESPONSE_TYPE_INVALID:{item_id}")
    require(response.get("capture_enabled") is True, f"PF17_CAPTURE_INVALID:{item_id}")
    require(response.get("human_review_fallback") is False, f"PF17_HUMAN_REVIEW_INVALID:{item_id}")
    require(response.get("accepted_texts") == [answer], f"PF17_ACCEPTED_TEXT_INVALID:{item_id}")
    require(bool(item.get("reconciliation_source_item_id")), f"PF17_SOURCE_MISSING:{item_id}")


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("program_id") == builder.PROGRAM_ID, "PROGRAM_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")
    _validate_digest(payload)

    approved_source, source_items = _source_authority()
    source = payload.get("source_identity") or {}
    require(source.get("u01qb10_task_id") == u01qb10.TASK_ID, "SOURCE_TASK_INVALID")
    require(source.get("u01qb10_artifact_sha256") == approved_source["artifact_sha256"], "SOURCE_ARTIFACT_INVALID")
    require(source.get("u01qb10_base_item_count") == 288, "SOURCE_BASE_COUNT_INVALID")

    identity = payload.get("bank_identity") or {}
    require(identity.get("bank_id") == builder.BANK_ID, "BANK_ID_INVALID")
    require(identity.get("bank_version") == builder.BANK_VERSION, "BANK_VERSION_INVALID")
    require(identity.get("canonical_revision") == builder.CANONICAL_REVISION, "REVISION_INVALID")
    require(identity.get("supersedes_revision") == u01qb10.CANONICAL_REVISION, "SUPERSEDES_INVALID")
    require(identity.get("second_question_bank_created") is False, "SECOND_BANK_CREATED")

    counts = payload.get("count_preservation") or {}
    require(counts.get("source_base_count") == 288, "SOURCE_COUNT_INVALID")
    require(counts.get("retained_base_count") == 252, "RETAINED_COUNT_INVALID")
    require(counts.get("retired_partial_support_count") == 36, "RETIRED_COUNT_INVALID")
    require(counts.get("exact_support_items_added") == 36, "ADDED_COUNT_INVALID")
    require(counts.get("reconciled_base_count") == 288, "RECONCILED_COUNT_INVALID")
    require(counts.get("unchanged_real62_extension_count") == 186, "EXTENSION_COUNT_INVALID")
    require(counts.get("projected_runtime_total_count") == 474, "RUNTIME_COUNT_INVALID")

    reference_sources, phrase_sources = _expected_sources(source_items)
    expected_reference_ids = [str(row["item_id"]) for row in reference_sources]
    expected_phrase_ids = [str(row["item_id"]) for row in phrase_sources]
    plan = payload.get("replacement_plan") or {}
    ref_plan = plan.get("reading_reference_evidence") or {}
    phrase_plan = plan.get("writing_phrase_construction") or {}
    require(ref_plan.get("source_pattern_family_id") == builder.SOURCE_REFERENCE_FAMILY, "REFERENCE_SOURCE_FAMILY_INVALID")
    require(ref_plan.get("retired_count") == 24, "REFERENCE_RETIRED_COUNT_INVALID")
    require(ref_plan.get("replacement_pattern_family_id") == builder.PF16, "REFERENCE_REPLACEMENT_FAMILY_INVALID")
    require(ref_plan.get("source_item_ids") == expected_reference_ids, "REFERENCE_SOURCE_IDS_INVALID")
    require(phrase_plan.get("source_pattern_family_id") == builder.SOURCE_PHRASE_FAMILY, "PHRASE_SOURCE_FAMILY_INVALID")
    require(phrase_plan.get("retired_count") == 12, "PHRASE_RETIRED_COUNT_INVALID")
    require(phrase_plan.get("replacement_pattern_family_id") == builder.PF17, "PHRASE_REPLACEMENT_FAMILY_INVALID")
    require(phrase_plan.get("source_item_ids") == expected_phrase_ids, "PHRASE_SOURCE_IDS_INVALID")

    items = payload.get("reconciled_items")
    require(isinstance(items, list) and len(items) == 288, "RECONCILED_ITEMS_INVALID")
    require(len({str(row.get("item_id")) for row in items}) == 288, "DUPLICATE_ITEM_ID")
    require(len({str(row.get("semantic_signature")) for row in items}) == 288, "DUPLICATE_SEMANTIC_SIGNATURE")
    family_counts = dict(sorted(Counter(str(row["pattern_family_id"]) for row in items).items()))
    require(family_counts == EXPECTED_FAMILY_COUNTS, "FAMILY_DISTRIBUTION_INVALID")
    skill_counts = dict(sorted(Counter(str(row["skill"]) for row in items).items()))
    require(skill_counts == u01qb10.EXPECTED_SKILL_COUNTS, "BASE_SKILL_DISTRIBUTION_INVALID")
    distributions = payload.get("distribution_counts") or {}
    require(distributions.get("family") == family_counts, "FAMILY_READBACK_INVALID")
    require(distributions.get("skill") == skill_counts, "SKILL_READBACK_INVALID")

    source_by_id = {str(row["item_id"]): row for row in source_items}
    retired_ids = set(expected_reference_ids + expected_phrase_ids)
    result_by_id = {str(row["item_id"]): row for row in items}
    retained_ids = set(source_by_id) - retired_ids
    require(retained_ids <= set(result_by_id), "RETAINED_ITEMS_MISSING")
    for item_id in retained_ids:
        require(result_by_id[item_id] == source_by_id[item_id], f"RETAINED_ITEM_DRIFT:{item_id}")
    require(not (retired_ids & set(result_by_id)), "RETIRED_ITEM_STILL_ACTIVE")

    pf16 = [row for row in items if row.get("pattern_family_id") == builder.PF16]
    pf17 = [row for row in items if row.get("pattern_family_id") == builder.PF17]
    require(len(pf16) == 24, "PF16_COUNT_INVALID")
    require(len(pf17) == 12, "PF17_COUNT_INVALID")
    require({str(row.get("reconciliation_source_item_id")) for row in pf16} == set(expected_reference_ids), "PF16_LINEAGE_INVALID")
    require({str(row.get("reconciliation_source_item_id")) for row in pf17} == set(expected_phrase_ids), "PF17_LINEAGE_INVALID")
    for row in pf16:
        _validate_pf16(row)
    for row in pf17:
        _validate_pf17(row)
    require(Counter(row["support_level"] for row in pf16) == Counter({"REDUCED_SUPPORT": 8, "INDEPENDENT": 8, "TRANSFER": 8}), "PF16_SUPPORT_DISTRIBUTION_INVALID")
    require(Counter(row["support_level"] for row in pf17) == Counter({"GUIDED": 3, "REDUCED_SUPPORT": 3, "INDEPENDENT": 3, "TRANSFER": 3}), "PF17_SUPPORT_DISTRIBUTION_INVALID")
    require(Counter(row["candidate_structure"] for row in pf17) == Counter(builder.PHRASE_STRUCTURE_QUOTA), "PF17_STRUCTURE_DISTRIBUTION_INVALID")

    source_speaking = sorted((row for row in source_items if row.get("skill") == "SPEAKING"), key=lambda row: str(row["item_id"]))
    result_speaking = sorted((row for row in items if row.get("skill") == "SPEAKING"), key=lambda row: str(row["item_id"]))
    require(result_speaking == source_speaking, "SPEAKING_BANK_DRIFT")
    require(all((row.get("response_contract") or {}).get("capture_enabled") is False for row in result_speaking), "SPEAKING_CAPTURE_DRIFT")

    source_evp = {sense for row in source_items for sense in row.get("target_evp_sense_ids", [])}
    result_evp = {sense for row in items for sense in row.get("target_evp_sense_ids", [])}
    source_egp = {row_id for row in source_items for row_id in row.get("target_egp_row_ids", [])}
    result_egp = {row_id for row in items for row_id in row.get("target_egp_row_ids", [])}
    require(result_evp == source_evp, "EVP_COVERAGE_DRIFT")
    require(result_egp == source_egp, "EGP_COVERAGE_DRIFT")

    coverage = payload.get("scored_task_angle_coverage") or {}
    require(coverage.get("scored_gap_count_after_u01qb10") == 0, "SCORED_GAP_INVALID")
    require(coverage.get("scored_partial_support_before") == 36, "PARTIAL_BEFORE_INVALID")
    require(coverage.get("reading_reference_evidence_partial_before") == 24, "REFERENCE_PARTIAL_BEFORE_INVALID")
    require(coverage.get("writing_phrase_construction_partial_before") == 12, "PHRASE_PARTIAL_BEFORE_INVALID")
    require(coverage.get("reading_reference_evidence_exact_support_after") == 24, "REFERENCE_FULLFIX_INVALID")
    require(coverage.get("writing_phrase_construction_exact_support_after") == 12, "PHRASE_FULLFIX_INVALID")
    require(coverage.get("scored_partial_support_after") == 0, "PARTIAL_AFTER_INVALID")
    require(coverage.get("remaining_scored_gap_angles") == [], "REMAINING_GAPS_INVALID")
    require(coverage.get("remaining_scored_partial_angles") == [], "REMAINING_PARTIALS_INVALID")
    require(coverage.get("scored_question_bank_full_alignment_ready") is True, "FULL_ALIGNMENT_NOT_READY")
    require(coverage.get("speaking_practice_alignment_unchanged") is True, "SPEAKING_ALIGNMENT_CLAIM_INVALID")
    require(coverage.get("speaking_scoring_enabled") is False, "SPEAKING_SCORING_DRIFT")

    boundaries = payload.get("boundaries") or {}
    for key in (
        "new_scene_authored", "question_bank_total_expanded", "second_question_bank_created",
        "real62_extension_modified", "m3_learner_state_rewritten", "m6_attempts_or_scoring_deleted",
        "speaking_scoring_enabled", "unit02_to_unit24_modified", "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")
    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_STEP_INVALID")
    return validation_receipt(payload)


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "CANDIDATE_ROLE_INVALID")
    require(candidate.get("learner_facing") is False, "CANDIDATE_LEARNER_FACING_INVALID")
    policy_artifact.verify_artifact_digest(candidate)
    source = candidate.get("source_bindings") or {}
    require(source.get("u01qb10_task_id") == u01qb10.TASK_ID, "SOURCE_BINDING_TASK_INVALID")
    require(source.get("bank_id") == builder.BANK_ID, "SOURCE_BINDING_BANK_INVALID")
    require(source.get("bank_version") == builder.BANK_VERSION, "SOURCE_BINDING_VERSION_INVALID")
    require(source.get("canonical_revision") == builder.CANONICAL_REVISION, "SOURCE_BINDING_REVISION_INVALID")
    require(source.get("count_preserving") is True, "SOURCE_BINDING_COUNT_INVALID")
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
                {"validator_id": receipt["validator_id"], "status": "PASS", "receipt_sha256": receipt["receipt_sha256"]}
            ],
            "RECEIPT_INVALID",
        )
        policy_artifact.verify_artifact_digest(approved)
        validate_payload(approved["payload"])
    except (
        PartialCoverageFullFixValidationError,
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
        "scored_partial_support_after": (payload.get("scored_task_angle_coverage") or {}).get("scored_partial_support_after"),
    }


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    require(report.get("schema_version") == builder.SCHEMA_VERSION, "REPORT_SCHEMA_INVALID")
    require(report.get("program_id") == builder.PROGRAM_ID, "REPORT_PROGRAM_INVALID")
    require(report.get("task_id") == builder.TASK_ID, "REPORT_TASK_INVALID")
    require(report.get("status") == builder.PASS_STATUS, "REPORT_STATUS_INVALID")
    unsigned = dict(report)
    actual = unsigned.pop("readback_sha256", None)
    require(actual == builder.digest(unsigned), "REPORT_DIGEST_INVALID")
    approval = report.get("approval_validation") or {}
    require(approval.get("status") == "PASS" and approval.get("error_count") == 0, "APPROVAL_VALIDATION_INVALID")
    migration = report.get("migration") or {}
    require(migration.get("validation_status") == builder.PASS_STATUS, "MIGRATION_STATUS_INVALID")
    require(migration.get("base_item_count") == 288, "MIGRATION_BASE_COUNT_INVALID")
    require(migration.get("extension_item_count") == 186, "MIGRATION_EXTENSION_COUNT_INVALID")
    require(migration.get("combined_runtime_item_count") == 474, "MIGRATION_RUNTIME_COUNT_INVALID")
    if migration.get("already_migrated") is True:
        require(migration.get("retired_partial_support_item_count") == 0, "IDEMPOTENT_RETIRED_COUNT_INVALID")
        require(migration.get("exact_support_item_added_count") == 0, "IDEMPOTENT_ADDED_COUNT_INVALID")
    else:
        require(migration.get("retired_partial_support_item_count") == 36, "MIGRATION_RETIRED_COUNT_INVALID")
        require(migration.get("exact_support_item_added_count") == 36, "MIGRATION_ADDED_COUNT_INVALID")
    require(migration.get("m3_learner_state_rewritten") is False, "M3_REWRITE_INVALID")
    require(migration.get("m6_attempts_or_scoring_deleted") is False, "M6_HISTORY_INVALID")
    require(migration.get("historical_retired_response_contracts_preserved") is True, "HISTORY_PRESERVATION_INVALID")

    replay = report.get("replay_474") or {}
    require(replay.get("runtime_item_count") == 474, "REPLAY_RUNTIME_COUNT_INVALID")
    require(replay.get("base_item_count") == 288, "REPLAY_BASE_COUNT_INVALID")
    require(replay.get("extension_item_count") == 186, "REPLAY_EXTENSION_COUNT_INVALID")
    require(replay.get("skill_distribution") == builder.EXPECTED_SKILL_COUNTS, "REPLAY_SKILL_COUNTS_INVALID")
    require(replay.get("capture_enabled_item_count") == 387, "REPLAY_CAPTURE_COUNT_INVALID")
    require(replay.get("deterministic_auto_pass_replay_count") == 351, "REPLAY_AUTO_PASS_INVALID")
    require(replay.get("feature_rubric_pending_human_replay_count") == 36, "REPLAY_PENDING_HUMAN_INVALID")
    require(replay.get("speaking_practice_only_count") == 87, "REPLAY_SPEAKING_INVALID")
    require(replay.get("exact_support_family_counts") == {builder.PF16: 24, builder.PF17: 12}, "REPLAY_EXACT_SUPPORT_COUNTS_INVALID")
    require(replay.get("scored_partial_support_after") == 0, "REPLAY_PARTIAL_INVALID")
    require(replay.get("scored_question_bank_full_alignment_ready") is True, "REPLAY_ALIGNMENT_INVALID")

    canary = report.get("exact_support_attempt_canary") or {}
    require(canary.get("attempt_count") == 2, "CANARY_ATTEMPT_COUNT_INVALID")
    require(canary.get("all_auto_pass") is True, "CANARY_OUTCOME_INVALID")
    results = canary.get("results") or []
    require({row.get("family") for row in results} == {builder.PF16, builder.PF17}, "CANARY_FAMILIES_INVALID")
    require(all(row.get("outcome") == "AUTO_PASS" for row in results), "CANARY_AUTO_PASS_INVALID")
    require(canary.get("speaking_capture_or_scoring_used") is False, "CANARY_SPEAKING_INVALID")

    coverage = report.get("coverage_closeout") or {}
    require(coverage.get("reading_reference_evidence") == "FULL", "REFERENCE_CLOSEOUT_INVALID")
    require(coverage.get("writing_phrase_construction") == "FULL", "PHRASE_CLOSEOUT_INVALID")
    require(coverage.get("scored_gap_count") == 0, "CLOSEOUT_GAP_INVALID")
    require(coverage.get("scored_partial_support_count") == 0, "CLOSEOUT_PARTIAL_INVALID")
    require(coverage.get("scored_question_bank_full_alignment_ready") is True, "CLOSEOUT_ALIGNMENT_INVALID")
    require(coverage.get("speaking_practice_alignment_unchanged") is True, "CLOSEOUT_SPEAKING_INVALID")

    boundaries = report.get("boundaries") or {}
    require(boundaries.get("question_bank_total_expanded") is False, "REPORT_BANK_EXPANSION_INVALID")
    require(boundaries.get("second_question_bank_created") is False, "REPORT_SECOND_BANK_INVALID")
    require(boundaries.get("existing_u01qb02_runtime_reused") is True, "REPORT_RUNTIME_REUSE_INVALID")
    require(boundaries.get("existing_real62_extension_reused") is True, "REPORT_REAL62_REUSE_INVALID")
    require(boundaries.get("m3_learner_state_rewritten") is False, "REPORT_M3_INVALID")
    require(boundaries.get("m6_attempts_or_scoring_deleted") is False, "REPORT_M6_INVALID")
    require(boundaries.get("speaking_scoring_enabled") is False, "REPORT_SPEAKING_INVALID")
    require(boundaries.get("unit02_to_unit24_modified") is False, "REPORT_UNIT_SCOPE_INVALID")
    require(boundaries.get("a2_unlocked") is False, "REPORT_A2_INVALID")
    require(report.get("next_short_step") == builder.NEXT_SHORT_STEP, "REPORT_NEXT_STEP_INVALID")
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "runtime_item_count": 474,
        "scored_partial_support_after": 0,
        "exact_support_attempt_canary_executed": True,
    }
