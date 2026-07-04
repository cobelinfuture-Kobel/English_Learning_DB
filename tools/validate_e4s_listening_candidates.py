#!/usr/bin/env python3
"""Validate E4S P5 listening candidate packages.

Scope:
- E4S-P5-I1 metadata/package validator implementation.
- Validates candidate package JSON against the P5-S1/S2/S3 contracts.
- Reads source manifest metadata for cross-reference checks.
- Produces a deterministic validation report.
- Does not generate audio, TTS, timing, questions, UI, learner state, or source/content promotion.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_PACKAGE_PATH = REPO_ROOT / "ulga" / "listening" / "candidates" / "e4s_listening_candidate_package.json"
DEFAULT_SOURCE_MANIFEST_PATH = REPO_ROOT / "ulga" / "graph" / "e4s_source_manifest.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "ulga" / "listening" / "reports" / "e4s_listening_validator_report.json"

EXPECTED_SCHEMA_VERSION = "E4S_LISTENING_CANDIDATE_PACKAGE_V1"
EXPECTED_REPORT_SCHEMA_VERSION = "E4S_LISTENING_VALIDATION_REPORT_V1"
EXPECTED_VALIDATOR_CONTRACT_VERSION = "E4S_P5_LISTENING_VALIDATOR_CONTRACT_V1"
EXPECTED_AUDIO_POLICY_VERSION = "E4S_P5_LISTENING_AUDIO_POLICY_V1"
EXPECTED_EPIC_ID = "E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem"
EXPECTED_PHASE_ID = "E4S-P5_ListeningPracticeSystem"
TASK_ID = "E4S-P5-I1_ListeningValidatorImplementation"

REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "epic_id",
    "phase_id",
    "task_id",
    "package_id",
    "package_policy",
    "source_manifest_ref",
    "validator_contract_ref",
    "audio_policy_ref",
    "public_distribution_policy",
    "learner_state_policy",
    "candidate_counts",
    "candidates",
}

REQUIRED_PACKAGE_POLICY_FIELDS = {
    "package_scope",
    "candidate_only",
    "audio_generation_status",
    "tts_generation_status",
    "timing_generation_status",
    "question_generation_status",
    "learner_facing_output_status",
    "validator_required",
    "source_promotion_status",
    "content_promotion_status",
    "public_distribution_default",
}

REQUIRED_SOURCE_MANIFEST_REF_FIELDS = {
    "manifest_path",
    "manifest_schema_version",
    "manifest_phase_id",
    "manifest_record_count",
    "manifest_hash_or_commit_ref",
    "source_manifest_contract_path",
}

REQUIRED_VALIDATOR_CONTRACT_REF_FIELDS = {
    "validator_contract_path",
    "validator_contract_task_id",
    "validator_contract_version",
    "required_report_schema_version",
    "required_error_code_set",
    "strict_mode_default",
}

REQUIRED_AUDIO_POLICY_REF_FIELDS = {
    "audio_policy_path",
    "audio_policy_task_id",
    "audio_policy_version",
    "audio_generation_default",
    "tts_generation_default",
    "timing_generation_default",
    "playback_ui_default",
    "voice_policy_required",
    "storage_policy_required",
}

REQUIRED_PUBLIC_DISTRIBUTION_POLICY_FIELDS = {
    "public_distribution_status",
    "license_clearance_status",
    "source_attribution_status",
    "derivative_audio_permission_status",
    "child_safety_status",
    "privacy_status",
}

REQUIRED_LEARNER_STATE_POLICY_FIELDS = {
    "learner_state_update_status",
    "learner_response_capture_status",
    "adaptive_assignment_status",
    "review_scheduling_status",
    "mastery_score_status",
    "weakness_tag_status",
    "placement_status",
}

REQUIRED_CANDIDATE_FIELDS = {
    "candidate_id",
    "candidate_type",
    "eligibility_class",
    "candidate_status",
    "source_trace",
    "source_text",
    "source_metadata",
    "level_situation_metadata",
    "listening_policy",
    "audio_policy",
    "tts_policy",
    "voice_policy",
    "storage_policy",
    "timing_policy",
    "public_distribution_policy",
    "learner_state_policy",
    "validator_handoff",
    "created_by_task_id",
}

REQUIRED_SOURCE_TRACE_FIELDS = {
    "source_id",
    "source_family",
    "authority_role",
    "source_path_or_reference",
    "source_record_hash_or_stable_ref",
    "source_unit_id",
    "source_unit_type",
    "source_unit_ref",
    "license_status",
    "review_status",
    "promotion_rule",
    "allowed_use",
    "blocked_use",
    "manual_review_status",
    "public_distribution_status",
}

REQUIRED_SOURCE_TEXT_FIELDS = {
    "source_text_raw",
    "source_text_normalized",
    "text_language",
    "text_normalization_policy",
    "text_segmentation_policy",
    "text_review_status",
    "sensitive_content_review_status",
    "child_suitability_review_status",
}

REQUIRED_SOURCE_METADATA_FIELDS = {
    "source_title_or_display_name",
    "source_level_system",
    "raw_level_code",
    "normalized_level_band",
    "level_claim_status",
    "source_owner_or_origin",
    "source_license_note",
    "source_review_owner",
    "source_review_date_or_ref",
}

REQUIRED_LEVEL_SITUATION_FIELDS = {
    "normalized_level_band",
    "level_claim_status",
    "situation_domain",
    "situation_context",
    "communicative_function",
    "interaction_mode",
    "skill_fit",
    "situation_claim_status",
    "situation_sensitivity_flag",
}

REQUIRED_LISTENING_POLICY_FIELDS = {
    "listening_item_type_candidates",
    "listening_item_generation_status",
    "question_generation_status",
    "answer_generation_status",
    "distractor_generation_status",
    "scoring_status",
    "student_facing_status",
}

REQUIRED_AUDIO_POLICY_FIELDS = {
    "audio_generation_status",
    "audio_asset_id",
    "audio_asset_path",
    "audio_policy_version",
    "human_audio_permission_status",
}

REQUIRED_TTS_POLICY_FIELDS = {
    "tts_permission_status",
    "tts_generation_status",
    "tts_provider",
    "tts_voice_id",
    "tts_policy_version",
}

REQUIRED_VOICE_POLICY_FIELDS = {
    "voice_policy_status",
    "voice_policy_version",
    "accent_label",
    "speed_profile",
    "speaker_role_mapping_status",
    "pronunciation_override_policy_status",
}

REQUIRED_STORAGE_POLICY_FIELDS = {
    "storage_policy_status",
    "storage_policy_version",
    "intended_storage_layer",
    "public_storage_status",
    "asset_naming_policy_status",
}

REQUIRED_TIMING_POLICY_FIELDS = {
    "timing_policy_status",
    "timing_policy_version",
    "timing_required_status",
    "timing_metadata_path",
    "timing_alignment_method",
}

REQUIRED_VALIDATOR_HANDOFF_FIELDS = {
    "validator_required",
    "validator_contract_path",
    "validator_contract_version",
    "expected_report_path",
    "blocking_error_codes_ref",
    "warning_codes_ref",
    "pass_fail_gate_ref",
    "candidate_order_key",
}

CANDIDATE_TYPES = {
    "sentence_listening_candidate",
    "dialogue_listening_candidate",
    "passage_listening_candidate",
}

BLOCKED_CANDIDATE_TYPES = {
    "word_only_audio_candidate",
    "phonics_drill_candidate",
    "pronunciation_assessment_candidate",
    "open_speaking_candidate",
    "asr_response_candidate",
    "adaptive_review_candidate",
    "learner_specific_assignment_candidate",
}

ELIGIBILITY_CLASSES = {
    "P5_ELIGIBLE_VERIFIED_SENTENCE",
    "P5_ELIGIBLE_VERIFIED_DIALOGUE",
    "P5_ELIGIBLE_VERIFIED_PASSAGE",
    "P5_DESIGN_CANDIDATE_ONLY",
    "P5_REFERENCE_ONLY",
    "P5_BLOCKED_STATUS_ARTIFACT",
    "P5_BLOCKED_GENERATED_UNREVIEWED",
    "P5_BLOCKED_LICENSE_OR_DISTRIBUTION",
    "P5_BLOCKED_UNKNOWN_TRACE",
}

ELIGIBLE_CLASSES = {
    "P5_ELIGIBLE_VERIFIED_SENTENCE",
    "P5_ELIGIBLE_VERIFIED_DIALOGUE",
    "P5_ELIGIBLE_VERIFIED_PASSAGE",
}

P5_ELIGIBLE_FAMILY_ROLES = {
    "raz_reading_corpus": {"reading_corpus_candidate"},
    "story_dialogue_corpus": {"dialogue_corpus_candidate"},
    "parent_functional_sentence_corpus": {"functional_sentence_corpus"},
}

REFERENCE_ONLY_FAMILIES = {
    "grammar_profile",
    "vocabulary_profile",
    "frequency_profile",
    "chunk_authority",
    "cambridge_vocabulary",
    "writing_template_corpus",
    "assessment_pattern_corpus",
}

GOVERNANCE_FAMILIES = {"governance", "roadmap"}
PUBLIC_VALUES = {"public", "public_allowed", "allowed", "cleared", "public_distribution_allowed"}
UNKNOWN_PUBLIC_VALUES = {"", "unknown", "unknown_pending_review", "not_set", "missing", None}
FORBIDDEN_VALUES = {"forbidden", "blocked", "not_allowed", "forbidden_until_later_approval"}
LEARNER_FORBIDDEN_STATUSES = {"forbidden", "blocked", "not_allowed", "forbidden_until_later_approval"}

BLOCKING_CODES = {
    "P5_MISSING_SOURCE_TRACE",
    "P5_UNKNOWN_SOURCE_ID",
    "P5_UNKNOWN_SOURCE_FAMILY",
    "P5_UNAPPROVED_AUTHORITY_ROLE",
    "P5_STATUS_ARTIFACT_USED_AS_CONTENT",
    "P5_GOVERNANCE_ARTIFACT_USED_AS_CONTENT",
    "P5_GENERATED_UNREVIEWED_CONTENT",
    "P5_RAZ_WORDLIST_USED_AS_AUDIO_SOURCE",
    "P5_REFERENCE_ONLY_USED_AS_CONTENT",
    "P5_LICENSE_PUBLIC_DISTRIBUTION_UNKNOWN",
    "P5_RESTRICTED_SOURCE_MARKED_PUBLIC",
    "P5_MISSING_REVIEW_STATUS",
    "P5_MISSING_TEXT_UNIT_ID",
    "P5_MISSING_SOURCE_TEXT_NORMALIZED",
    "P5_BAD_SEGMENTATION_POLICY",
    "P5_DIALOGUE_MISSING_TURN_MODEL",
    "P5_PASSAGE_MISSING_SENTENCE_ORDER",
    "P5_SENTENCE_MISSING_CONTEXT_REF",
    "P5_MISSING_AUDIO_POLICY_VERSION",
    "P5_MISSING_TTS_PERMISSION",
    "P5_TTS_ENABLED_WITHOUT_POLICY",
    "P5_MISSING_VOICE_POLICY",
    "P5_MISSING_STORAGE_POLICY",
    "P5_PUBLIC_AUDIO_WITHOUT_LICENSE_CLEARANCE",
    "P5_TIMING_PRESENT_WITHOUT_POLICY",
    "P5_LEARNER_FACING_OUTPUT_WITHOUT_APPROVAL",
    "P5_LEARNER_STATE_UPDATE_ATTEMPT",
    "P5_ADAPTIVE_ASSIGNMENT_ATTEMPT",
    "P5_CONTENT_PROMOTION_ATTEMPT",
    "P5_NON_DETERMINISTIC_ORDER",
    "P5_DUPLICATE_CANDIDATE_ID",
    "P5_BAD_PACKAGE_PHASE",
    "P5_BAD_SCHEMA_VERSION",
}

WARNING_CODES = {
    "P5_WARN_INTERNAL_ONLY_SOURCE",
    "P5_WARN_TIMING_OPTIONAL_MISSING",
    "P5_WARN_LEVEL_BAND_UNVERIFIED",
    "P5_WARN_SITUATION_METADATA_COARSE",
    "P5_WARN_AUDIO_POLICY_PLACEHOLDER",
    "P5_WARN_P4_HANDOFF_PENDING",
    "P5_WARN_P1_HANDOFF_PENDING",
    "P5_WARN_CHILD_SUITABILITY_REVIEW_PENDING",
    "P5_WARN_PUBLIC_ATTRIBUTION_PENDING",
    "P5_WARN_PRONUNCIATION_POLICY_PENDING",
}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: str
    candidate_id: str | None
    source_id: str | None
    field: str
    message: str
    required_handling: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "candidate_id": self.candidate_id,
            "source_id": self.source_id,
            "field": self.field,
            "message": self.message,
            "required_handling": self.required_handling,
        }


def _issue(
    code: str,
    field: str,
    message: str,
    *,
    candidate_id: str | None = None,
    source_id: str | None = None,
    severity: str = "error",
    required_handling: str = "fail",
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        severity=severity,
        candidate_id=candidate_id,
        source_id=source_id,
        field=field,
        message=message,
        required_handling=required_handling,
    )


def load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise SystemExit(f"{label} root must be a JSON object.")
    return payload


def validate_package(package: dict[str, Any], source_manifest: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    source_records = _source_records_by_id(source_manifest, issues)

    _validate_top_level_package(package, issues)
    candidates = package.get("candidates")
    if not isinstance(candidates, list):
        issues.append(_issue("P5_BAD_SCHEMA_VERSION", "$.candidates", "candidates must be an array."))
        return _sorted_issues(issues)

    _validate_candidate_collection(candidates, issues)
    for index, candidate in enumerate(candidates):
        _validate_candidate(candidate, index, source_records, issues)

    _validate_candidate_counts(package.get("candidate_counts"), candidates, issues)
    return _sorted_issues(issues)


def _source_records_by_id(source_manifest: dict[str, Any], issues: list[ValidationIssue]) -> dict[str, dict[str, Any]]:
    records = source_manifest.get("records")
    if not isinstance(records, list):
        issues.append(_issue("P5_BAD_SCHEMA_VERSION", "$.source_manifest.records", "Source manifest records must be an array."))
        return {}

    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        if isinstance(record, dict) and isinstance(record.get("source_id"), str):
            by_id[record["source_id"]] = record
    return by_id


def _validate_top_level_package(package: dict[str, Any], issues: list[ValidationIssue]) -> None:
    _require_fields(package, REQUIRED_TOP_LEVEL_FIELDS, "$", issues, "P5_BAD_SCHEMA_VERSION")

    if package.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        issues.append(_issue("P5_BAD_SCHEMA_VERSION", "$.schema_version", f"Expected {EXPECTED_SCHEMA_VERSION}."))
    if package.get("epic_id") != EXPECTED_EPIC_ID:
        issues.append(_issue("P5_BAD_SCHEMA_VERSION", "$.epic_id", f"Expected {EXPECTED_EPIC_ID}."))
    if package.get("phase_id") != EXPECTED_PHASE_ID:
        issues.append(_issue("P5_BAD_PACKAGE_PHASE", "$.phase_id", f"Expected {EXPECTED_PHASE_ID}."))

    _validate_object(package, "package_policy", REQUIRED_PACKAGE_POLICY_FIELDS, "$.package_policy", issues)
    _validate_object(package, "source_manifest_ref", REQUIRED_SOURCE_MANIFEST_REF_FIELDS, "$.source_manifest_ref", issues)
    _validate_object(package, "validator_contract_ref", REQUIRED_VALIDATOR_CONTRACT_REF_FIELDS, "$.validator_contract_ref", issues)
    _validate_object(package, "audio_policy_ref", REQUIRED_AUDIO_POLICY_REF_FIELDS, "$.audio_policy_ref", issues)
    _validate_object(package, "public_distribution_policy", REQUIRED_PUBLIC_DISTRIBUTION_POLICY_FIELDS, "$.public_distribution_policy", issues)
    _validate_object(package, "learner_state_policy", REQUIRED_LEARNER_STATE_POLICY_FIELDS, "$.learner_state_policy", issues)

    package_policy = package.get("package_policy")
    if isinstance(package_policy, dict):
        if package_policy.get("source_promotion_status") != "forbidden" or package_policy.get("content_promotion_status") != "forbidden":
            issues.append(_issue("P5_CONTENT_PROMOTION_ATTEMPT", "$.package_policy", "Package policy must not promote source or content authority."))
        for field in ("audio_generation_status", "tts_generation_status", "timing_generation_status", "question_generation_status", "learner_facing_output_status"):
            if package_policy.get(field) not in FORBIDDEN_VALUES:
                issues.append(_issue("P5_LEARNER_FACING_OUTPUT_WITHOUT_APPROVAL", f"$.package_policy.{field}", f"{field} must remain forbidden or blocked."))
        if package_policy.get("public_distribution_default") not in {"blocked", "forbidden", "internal_only"}:
            issues.append(_issue("P5_LICENSE_PUBLIC_DISTRIBUTION_UNKNOWN", "$.package_policy.public_distribution_default", "Public distribution must be blocked by default."))

    validator_ref = package.get("validator_contract_ref")
    if isinstance(validator_ref, dict) and validator_ref.get("validator_contract_version") != EXPECTED_VALIDATOR_CONTRACT_VERSION:
        issues.append(_issue("P5_BAD_SCHEMA_VERSION", "$.validator_contract_ref.validator_contract_version", f"Expected {EXPECTED_VALIDATOR_CONTRACT_VERSION}."))

    audio_ref = package.get("audio_policy_ref")
    if isinstance(audio_ref, dict):
        if audio_ref.get("audio_policy_version") != EXPECTED_AUDIO_POLICY_VERSION:
            issues.append(_issue("P5_MISSING_AUDIO_POLICY_VERSION", "$.audio_policy_ref.audio_policy_version", f"Expected {EXPECTED_AUDIO_POLICY_VERSION}."))
        for field in ("audio_generation_default", "tts_generation_default", "timing_generation_default", "playback_ui_default"):
            if audio_ref.get(field) != "forbidden":
                issues.append(_issue("P5_TTS_ENABLED_WITHOUT_POLICY", f"$.audio_policy_ref.{field}", f"{field} must be forbidden in the package schema baseline."))

    _validate_package_learner_state_policy(package.get("learner_state_policy"), "$.learner_state_policy", None, None, issues)


def _validate_candidate_collection(candidates: list[Any], issues: list[ValidationIssue]) -> None:
    candidate_ids: list[str] = []
    for candidate in candidates:
        if isinstance(candidate, dict) and isinstance(candidate.get("candidate_id"), str):
            candidate_ids.append(candidate["candidate_id"])

    seen: set[str] = set()
    for candidate_id in candidate_ids:
        if candidate_id in seen:
            issues.append(_issue("P5_DUPLICATE_CANDIDATE_ID", "$.candidates", f"Duplicate candidate_id: {candidate_id}.", candidate_id=candidate_id))
        seen.add(candidate_id)

    if candidate_ids != sorted(candidate_ids):
        issues.append(_issue("P5_NON_DETERMINISTIC_ORDER", "$.candidates", "Candidates must be sorted by candidate_id."))


def _validate_candidate(candidate: Any, index: int, source_records: dict[str, dict[str, Any]], issues: list[ValidationIssue]) -> None:
    path = f"$.candidates[{index}]"
    if not isinstance(candidate, dict):
        issues.append(_issue("P5_BAD_SCHEMA_VERSION", path, "Candidate record must be an object."))
        return

    candidate_id = candidate.get("candidate_id") if isinstance(candidate.get("candidate_id"), str) else None
    source_trace = candidate.get("source_trace")
    source_id = source_trace.get("source_id") if isinstance(source_trace, dict) and isinstance(source_trace.get("source_id"), str) else None

    _require_fields(candidate, REQUIRED_CANDIDATE_FIELDS, path, issues, "P5_BAD_SCHEMA_VERSION", candidate_id=candidate_id, source_id=source_id)

    candidate_type = candidate.get("candidate_type")
    eligibility = candidate.get("eligibility_class")
    if candidate_type not in CANDIDATE_TYPES:
        code = "P5_BAD_SCHEMA_VERSION" if candidate_type not in BLOCKED_CANDIDATE_TYPES else "P5_UNAPPROVED_AUTHORITY_ROLE"
        issues.append(_issue(code, f"{path}.candidate_type", f"Unsupported candidate_type: {candidate_type!r}.", candidate_id=candidate_id, source_id=source_id))
    if eligibility not in ELIGIBILITY_CLASSES:
        issues.append(_issue("P5_BAD_SCHEMA_VERSION", f"{path}.eligibility_class", f"Unsupported eligibility_class: {eligibility!r}.", candidate_id=candidate_id, source_id=source_id))

    if not isinstance(source_trace, dict):
        issues.append(_issue("P5_MISSING_SOURCE_TRACE", f"{path}.source_trace", "source_trace must be an object.", candidate_id=candidate_id, source_id=source_id))
        return

    _validate_object(candidate, "source_trace", REQUIRED_SOURCE_TRACE_FIELDS, f"{path}.source_trace", issues, candidate_id=candidate_id, source_id=source_id, missing_code="P5_MISSING_SOURCE_TRACE")
    _validate_object(candidate, "source_text", REQUIRED_SOURCE_TEXT_FIELDS, f"{path}.source_text", issues, candidate_id=candidate_id, source_id=source_id)
    _validate_object(candidate, "source_metadata", REQUIRED_SOURCE_METADATA_FIELDS, f"{path}.source_metadata", issues, candidate_id=candidate_id, source_id=source_id)
    _validate_object(candidate, "level_situation_metadata", REQUIRED_LEVEL_SITUATION_FIELDS, f"{path}.level_situation_metadata", issues, candidate_id=candidate_id, source_id=source_id)
    _validate_object(candidate, "listening_policy", REQUIRED_LISTENING_POLICY_FIELDS, f"{path}.listening_policy", issues, candidate_id=candidate_id, source_id=source_id)
    _validate_object(candidate, "audio_policy", REQUIRED_AUDIO_POLICY_FIELDS, f"{path}.audio_policy", issues, candidate_id=candidate_id, source_id=source_id)
    _validate_object(candidate, "tts_policy", REQUIRED_TTS_POLICY_FIELDS, f"{path}.tts_policy", issues, candidate_id=candidate_id, source_id=source_id)
    _validate_object(candidate, "voice_policy", REQUIRED_VOICE_POLICY_FIELDS, f"{path}.voice_policy", issues, candidate_id=candidate_id, source_id=source_id)
    _validate_object(candidate, "storage_policy", REQUIRED_STORAGE_POLICY_FIELDS, f"{path}.storage_policy", issues, candidate_id=candidate_id, source_id=source_id)
    _validate_object(candidate, "timing_policy", REQUIRED_TIMING_POLICY_FIELDS, f"{path}.timing_policy", issues, candidate_id=candidate_id, source_id=source_id)
    _validate_object(candidate, "public_distribution_policy", REQUIRED_PUBLIC_DISTRIBUTION_POLICY_FIELDS, f"{path}.public_distribution_policy", issues, candidate_id=candidate_id, source_id=source_id)
    _validate_object(candidate, "learner_state_policy", REQUIRED_LEARNER_STATE_POLICY_FIELDS, f"{path}.learner_state_policy", issues, candidate_id=candidate_id, source_id=source_id)
    _validate_object(candidate, "validator_handoff", REQUIRED_VALIDATOR_HANDOFF_FIELDS, f"{path}.validator_handoff", issues, candidate_id=candidate_id, source_id=source_id)

    record = _validate_source_trace(candidate, path, source_trace, source_records, candidate_id, issues)
    _validate_candidate_text_and_segmentation(candidate, path, candidate_id, source_id, issues)
    _validate_candidate_policies(candidate, path, candidate_id, source_id, issues)
    _validate_candidate_variant(candidate, path, candidate_type, candidate_id, source_id, issues)
    _validate_family_role_rules(candidate, path, record, candidate_id, source_id, issues)
    _add_warnings(candidate, path, record, candidate_id, source_id, issues)


def _validate_source_trace(
    candidate: dict[str, Any],
    path: str,
    source_trace: dict[str, Any],
    source_records: dict[str, dict[str, Any]],
    candidate_id: str | None,
    issues: list[ValidationIssue],
) -> dict[str, Any] | None:
    source_id = source_trace.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        issues.append(_issue("P5_MISSING_SOURCE_TRACE", f"{path}.source_trace.source_id", "source_id is required.", candidate_id=candidate_id))
        return None

    record = source_records.get(source_id)
    if record is None:
        issues.append(_issue("P5_UNKNOWN_SOURCE_ID", f"{path}.source_trace.source_id", f"source_id not found in source manifest: {source_id}.", candidate_id=candidate_id, source_id=source_id))
        return None

    manifest_family = record.get("source_family")
    manifest_role = record.get("authority_role")
    family = source_trace.get("source_family")
    role = source_trace.get("authority_role")
    if not isinstance(family, str) or family != manifest_family:
        issues.append(_issue("P5_UNKNOWN_SOURCE_FAMILY", f"{path}.source_trace.source_family", "source_family must match source manifest.", candidate_id=candidate_id, source_id=source_id))
    if not isinstance(role, str) or role != manifest_role:
        issues.append(_issue("P5_UNAPPROVED_AUTHORITY_ROLE", f"{path}.source_trace.authority_role", "authority_role must match source manifest.", candidate_id=candidate_id, source_id=source_id))

    if not source_trace.get("source_unit_id"):
        issues.append(_issue("P5_MISSING_TEXT_UNIT_ID", f"{path}.source_trace.source_unit_id", "source_unit_id is required.", candidate_id=candidate_id, source_id=source_id))
    if source_trace.get("review_status") in {None, "", "not_reviewed"} or source_trace.get("manual_review_status") in {None, ""}:
        issues.append(_issue("P5_MISSING_REVIEW_STATUS", f"{path}.source_trace", "review_status and manual_review_status are required.", candidate_id=candidate_id, source_id=source_id))

    return record


def _validate_family_role_rules(
    candidate: dict[str, Any],
    path: str,
    record: dict[str, Any] | None,
    candidate_id: str | None,
    source_id: str | None,
    issues: list[ValidationIssue],
) -> None:
    if record is None:
        return

    family = record.get("source_family")
    role = record.get("authority_role")
    license_status = record.get("license_status")
    eligibility = candidate.get("eligibility_class")
    source_trace = candidate.get("source_trace", {}) if isinstance(candidate.get("source_trace"), dict) else {}
    public_policy = candidate.get("public_distribution_policy", {}) if isinstance(candidate.get("public_distribution_policy"), dict) else {}
    public_status = public_policy.get("public_distribution_status", source_trace.get("public_distribution_status"))

    if family == "status_artifact":
        issues.append(_issue("P5_STATUS_ARTIFACT_USED_AS_CONTENT", f"{path}.source_trace.source_family", "Status artifacts must never be listening content.", candidate_id=candidate_id, source_id=source_id))
    if family in GOVERNANCE_FAMILIES:
        issues.append(_issue("P5_GOVERNANCE_ARTIFACT_USED_AS_CONTENT", f"{path}.source_trace.source_family", "Governance or roadmap artifacts must never be listening content.", candidate_id=candidate_id, source_id=source_id))
    if family == "raz_wordlist":
        issues.append(_issue("P5_RAZ_WORDLIST_USED_AS_AUDIO_SOURCE", f"{path}.source_trace.source_family", "RAZ word list evidence must not be direct audio/listening source.", candidate_id=candidate_id, source_id=source_id))
    if family in REFERENCE_ONLY_FAMILIES and eligibility in ELIGIBLE_CLASSES:
        issues.append(_issue("P5_REFERENCE_ONLY_USED_AS_CONTENT", f"{path}.source_trace.source_family", "Reference-only sources cannot become eligible listening content.", candidate_id=candidate_id, source_id=source_id))
    if family == "generated_content_candidate":
        manual_review_status = source_trace.get("manual_review_status")
        if eligibility in ELIGIBLE_CLASSES or manual_review_status not in {"validator_reviewed", "promotion_reviewed"}:
            issues.append(_issue("P5_GENERATED_UNREVIEWED_CONTENT", f"{path}.source_trace.source_family", "Generated content cannot be listening content without review and promotion evidence.", candidate_id=candidate_id, source_id=source_id))

    if eligibility in ELIGIBLE_CLASSES and role not in P5_ELIGIBLE_FAMILY_ROLES.get(str(family), set()):
        issues.append(_issue("P5_UNAPPROVED_AUTHORITY_ROLE", f"{path}.source_trace.authority_role", f"authority_role={role!r} is not approved for eligible P5 content from {family!r}.", candidate_id=candidate_id, source_id=source_id))

    if public_status in UNKNOWN_PUBLIC_VALUES:
        issues.append(_issue("P5_LICENSE_PUBLIC_DISTRIBUTION_UNKNOWN", f"{path}.public_distribution_policy.public_distribution_status", "Public distribution status must be explicit.", candidate_id=candidate_id, source_id=source_id))
    if license_status == "restricted_reference_only" and public_status in PUBLIC_VALUES:
        issues.append(_issue("P5_RESTRICTED_SOURCE_MARKED_PUBLIC", f"{path}.public_distribution_policy.public_distribution_status", "restricted_reference_only sources must not be marked public.", candidate_id=candidate_id, source_id=source_id))
    if public_status in PUBLIC_VALUES and public_policy.get("license_clearance_status") not in {"cleared", "public_cleared"}:
        issues.append(_issue("P5_PUBLIC_AUDIO_WITHOUT_LICENSE_CLEARANCE", f"{path}.public_distribution_policy.license_clearance_status", "Public audio/output requires license clearance.", candidate_id=candidate_id, source_id=source_id))


def _validate_candidate_text_and_segmentation(candidate: dict[str, Any], path: str, candidate_id: str | None, source_id: str | None, issues: list[ValidationIssue]) -> None:
    source_text = candidate.get("source_text", {}) if isinstance(candidate.get("source_text"), dict) else {}
    candidate_type = candidate.get("candidate_type")
    normalized = source_text.get("source_text_normalized")
    if not isinstance(normalized, str) or not normalized.strip():
        issues.append(_issue("P5_MISSING_SOURCE_TEXT_NORMALIZED", f"{path}.source_text.source_text_normalized", "source_text_normalized must be non-empty.", candidate_id=candidate_id, source_id=source_id))

    segmentation = source_text.get("text_segmentation_policy")
    expected_keywords = {
        "sentence_listening_candidate": "sentence",
        "dialogue_listening_candidate": "dialogue",
        "passage_listening_candidate": "passage",
    }
    expected = expected_keywords.get(str(candidate_type))
    if expected and (not isinstance(segmentation, str) or expected not in segmentation):
        issues.append(_issue("P5_BAD_SEGMENTATION_POLICY", f"{path}.source_text.text_segmentation_policy", f"Segmentation policy must match candidate type: {expected}.", candidate_id=candidate_id, source_id=source_id))


def _validate_candidate_policies(candidate: dict[str, Any], path: str, candidate_id: str | None, source_id: str | None, issues: list[ValidationIssue]) -> None:
    audio_policy = candidate.get("audio_policy", {}) if isinstance(candidate.get("audio_policy"), dict) else {}
    tts_policy = candidate.get("tts_policy", {}) if isinstance(candidate.get("tts_policy"), dict) else {}
    voice_policy = candidate.get("voice_policy", {}) if isinstance(candidate.get("voice_policy"), dict) else {}
    storage_policy = candidate.get("storage_policy", {}) if isinstance(candidate.get("storage_policy"), dict) else {}
    timing_policy = candidate.get("timing_policy", {}) if isinstance(candidate.get("timing_policy"), dict) else {}
    listening_policy = candidate.get("listening_policy", {}) if isinstance(candidate.get("listening_policy"), dict) else {}

    if not audio_policy.get("audio_policy_version"):
        issues.append(_issue("P5_MISSING_AUDIO_POLICY_VERSION", f"{path}.audio_policy.audio_policy_version", "audio_policy_version is required.", candidate_id=candidate_id, source_id=source_id))
    if not tts_policy.get("tts_permission_status"):
        issues.append(_issue("P5_MISSING_TTS_PERMISSION", f"{path}.tts_policy.tts_permission_status", "tts_permission_status is required.", candidate_id=candidate_id, source_id=source_id))
    if tts_policy.get("tts_generation_status") not in FORBIDDEN_VALUES and tts_policy.get("tts_permission_status") not in {"allowed", "approved"}:
        issues.append(_issue("P5_TTS_ENABLED_WITHOUT_POLICY", f"{path}.tts_policy", "TTS cannot be enabled without explicit permission policy.", candidate_id=candidate_id, source_id=source_id))
    if not voice_policy.get("voice_policy_status"):
        issues.append(_issue("P5_MISSING_VOICE_POLICY", f"{path}.voice_policy.voice_policy_status", "voice_policy_status is required.", candidate_id=candidate_id, source_id=source_id))
    if not storage_policy.get("storage_policy_status"):
        issues.append(_issue("P5_MISSING_STORAGE_POLICY", f"{path}.storage_policy.storage_policy_status", "storage_policy_status is required.", candidate_id=candidate_id, source_id=source_id))
    if timing_policy.get("timing_metadata_path") and not timing_policy.get("timing_policy_version"):
        issues.append(_issue("P5_TIMING_PRESENT_WITHOUT_POLICY", f"{path}.timing_policy", "Timing metadata path requires timing_policy_version.", candidate_id=candidate_id, source_id=source_id))
    if listening_policy.get("student_facing_status") not in LEARNER_FORBIDDEN_STATUSES:
        issues.append(_issue("P5_LEARNER_FACING_OUTPUT_WITHOUT_APPROVAL", f"{path}.listening_policy.student_facing_status", "Student-facing output is not approved.", candidate_id=candidate_id, source_id=source_id))

    _validate_package_learner_state_policy(candidate.get("learner_state_policy"), f"{path}.learner_state_policy", candidate_id, source_id, issues)


def _validate_candidate_variant(candidate: dict[str, Any], path: str, candidate_type: Any, candidate_id: str | None, source_id: str | None, issues: list[ValidationIssue]) -> None:
    source_trace = candidate.get("source_trace", {}) if isinstance(candidate.get("source_trace"), dict) else {}
    source_unit_type = source_trace.get("source_unit_type")

    if candidate_type == "sentence_listening_candidate":
        _require_fields(candidate, {"sentence_id", "sentence_boundary_policy", "sentence_context_ref", "sentence_order_ref", "sentence_audio_scope"}, path, issues, "P5_SENTENCE_MISSING_CONTEXT_REF", candidate_id=candidate_id, source_id=source_id)
        if source_unit_type != "sentence":
            issues.append(_issue("P5_BAD_SEGMENTATION_POLICY", f"{path}.source_trace.source_unit_type", "sentence candidate requires source_unit_type=sentence.", candidate_id=candidate_id, source_id=source_id))
    elif candidate_type == "dialogue_listening_candidate":
        _require_fields(candidate, {"dialogue_id", "dialogue_turns", "turn_count", "speaker_roles", "speaker_order_policy", "multi_speaker_audio_policy", "p4_handoff_status"}, path, issues, "P5_DIALOGUE_MISSING_TURN_MODEL", candidate_id=candidate_id, source_id=source_id)
        turns = candidate.get("dialogue_turns")
        if not isinstance(turns, list) or not turns:
            issues.append(_issue("P5_DIALOGUE_MISSING_TURN_MODEL", f"{path}.dialogue_turns", "dialogue_turns must be a non-empty array.", candidate_id=candidate_id, source_id=source_id))
        else:
            orders: list[int] = []
            for turn_index, turn in enumerate(turns):
                if not isinstance(turn, dict):
                    issues.append(_issue("P5_DIALOGUE_MISSING_TURN_MODEL", f"{path}.dialogue_turns[{turn_index}]", "Dialogue turn must be an object.", candidate_id=candidate_id, source_id=source_id))
                    continue
                _require_fields(turn, {"turn_id", "speaker_role", "speaker_order", "turn_text", "turn_boundary_policy"}, f"{path}.dialogue_turns[{turn_index}]", issues, "P5_DIALOGUE_MISSING_TURN_MODEL", candidate_id=candidate_id, source_id=source_id)
                if isinstance(turn.get("speaker_order"), int):
                    orders.append(turn["speaker_order"])
            if orders != sorted(orders):
                issues.append(_issue("P5_BAD_SEGMENTATION_POLICY", f"{path}.dialogue_turns", "dialogue_turns must be sorted by speaker_order.", candidate_id=candidate_id, source_id=source_id))
        if source_unit_type != "dialogue":
            issues.append(_issue("P5_BAD_SEGMENTATION_POLICY", f"{path}.source_trace.source_unit_type", "dialogue candidate requires source_unit_type=dialogue.", candidate_id=candidate_id, source_id=source_id))
    elif candidate_type == "passage_listening_candidate":
        _require_fields(candidate, {"passage_id", "sentence_ids", "sentence_order", "paragraph_or_page_ref", "passage_boundary_policy", "p1_handoff_status"}, path, issues, "P5_PASSAGE_MISSING_SENTENCE_ORDER", candidate_id=candidate_id, source_id=source_id)
        sentence_ids = candidate.get("sentence_ids")
        sentence_order = candidate.get("sentence_order")
        if not isinstance(sentence_ids, list) or not sentence_ids or not isinstance(sentence_order, list) or len(sentence_ids) != len(sentence_order):
            issues.append(_issue("P5_PASSAGE_MISSING_SENTENCE_ORDER", f"{path}.sentence_ids", "passage candidates require aligned sentence_ids and sentence_order arrays.", candidate_id=candidate_id, source_id=source_id))
        elif sentence_order != sorted(sentence_order):
            issues.append(_issue("P5_BAD_SEGMENTATION_POLICY", f"{path}.sentence_order", "sentence_order must be deterministic and sorted.", candidate_id=candidate_id, source_id=source_id))
        if source_unit_type != "passage":
            issues.append(_issue("P5_BAD_SEGMENTATION_POLICY", f"{path}.source_trace.source_unit_type", "passage candidate requires source_unit_type=passage.", candidate_id=candidate_id, source_id=source_id))


def _add_warnings(candidate: dict[str, Any], path: str, record: dict[str, Any] | None, candidate_id: str | None, source_id: str | None, issues: list[ValidationIssue]) -> None:
    if record and record.get("license_status") in {"restricted_reference_only", "not_redistributable"}:
        public_policy = candidate.get("public_distribution_policy", {}) if isinstance(candidate.get("public_distribution_policy"), dict) else {}
        if public_policy.get("public_distribution_status") in {"blocked", "internal_only", "forbidden"}:
            issues.append(_issue("P5_WARN_INTERNAL_ONLY_SOURCE", f"{path}.public_distribution_policy.public_distribution_status", "Candidate appears internal-only / not public.", candidate_id=candidate_id, source_id=source_id, severity="warning", required_handling="allow_if_public_distribution_blocked"))

    timing_policy = candidate.get("timing_policy", {}) if isinstance(candidate.get("timing_policy"), dict) else {}
    if timing_policy.get("timing_required_status") in {"optional", "not_required"} and not timing_policy.get("timing_metadata_path"):
        issues.append(_issue("P5_WARN_TIMING_OPTIONAL_MISSING", f"{path}.timing_policy.timing_metadata_path", "Timing metadata is absent but optional.", candidate_id=candidate_id, source_id=source_id, severity="warning", required_handling="allow"))

    level_meta = candidate.get("level_situation_metadata", {}) if isinstance(candidate.get("level_situation_metadata"), dict) else {}
    if level_meta.get("level_claim_status") in {"provisional", "unverified"}:
        issues.append(_issue("P5_WARN_LEVEL_BAND_UNVERIFIED", f"{path}.level_situation_metadata.level_claim_status", "Level band is provisional.", candidate_id=candidate_id, source_id=source_id, severity="warning", required_handling="candidate_only"))


def _validate_candidate_counts(candidate_counts: Any, candidates: list[Any], issues: list[ValidationIssue]) -> None:
    if not isinstance(candidate_counts, dict):
        issues.append(_issue("P5_BAD_SCHEMA_VERSION", "$.candidate_counts", "candidate_counts must be an object."))
        return

    valid_candidates = [candidate for candidate in candidates if isinstance(candidate, dict)]
    expected_total = len(valid_candidates)
    if candidate_counts.get("total_candidates") != expected_total:
        issues.append(_issue("P5_BAD_SCHEMA_VERSION", "$.candidate_counts.total_candidates", f"Expected total_candidates={expected_total}."))

    count_specs = {
        "by_candidate_type": Counter(candidate.get("candidate_type") for candidate in valid_candidates),
        "by_eligibility_class": Counter(candidate.get("eligibility_class") for candidate in valid_candidates),
        "by_source_family": Counter(_nested(candidate, "source_trace", "source_family") for candidate in valid_candidates),
        "by_public_distribution_status": Counter(_nested(candidate, "public_distribution_policy", "public_distribution_status") for candidate in valid_candidates),
        "by_learner_facing_status": Counter(_nested(candidate, "listening_policy", "student_facing_status") for candidate in valid_candidates),
        "by_audio_generation_status": Counter(_nested(candidate, "audio_policy", "audio_generation_status") for candidate in valid_candidates),
        "by_validator_readiness": Counter(_nested(candidate, "validator_handoff", "validator_required") for candidate in valid_candidates),
    }

    for field, expected_counter in count_specs.items():
        provided = candidate_counts.get(field)
        if provided is None:
            continue
        normalized_expected = {str(key): value for key, value in sorted(expected_counter.items(), key=lambda item: str(item[0]))}
        if provided != normalized_expected:
            issues.append(_issue("P5_BAD_SCHEMA_VERSION", f"$.candidate_counts.{field}", f"Expected derived counts {normalized_expected!r}."))


def _validate_package_learner_state_policy(policy: Any, path: str, candidate_id: str | None, source_id: str | None, issues: list[ValidationIssue]) -> None:
    if not isinstance(policy, dict):
        return
    learner_fields = {
        "learner_state_update_status",
        "learner_response_capture_status",
        "review_scheduling_status",
        "mastery_score_status",
        "weakness_tag_status",
        "placement_status",
    }
    for field in learner_fields:
        if field in policy and policy.get(field) not in LEARNER_FORBIDDEN_STATUSES:
            issues.append(_issue("P5_LEARNER_STATE_UPDATE_ATTEMPT", f"{path}.{field}", f"{field} must remain forbidden.", candidate_id=candidate_id, source_id=source_id))
    if policy.get("adaptive_assignment_status") not in LEARNER_FORBIDDEN_STATUSES and "adaptive_assignment_status" in policy:
        issues.append(_issue("P5_ADAPTIVE_ASSIGNMENT_ATTEMPT", f"{path}.adaptive_assignment_status", "adaptive_assignment_status must remain forbidden.", candidate_id=candidate_id, source_id=source_id))


def _validate_object(
    parent: dict[str, Any],
    field: str,
    required_fields: set[str],
    path: str,
    issues: list[ValidationIssue],
    *,
    candidate_id: str | None = None,
    source_id: str | None = None,
    missing_code: str = "P5_BAD_SCHEMA_VERSION",
) -> None:
    value = parent.get(field)
    if not isinstance(value, dict):
        issues.append(_issue(missing_code, path, f"{field} must be an object.", candidate_id=candidate_id, source_id=source_id))
        return
    _require_fields(value, required_fields, path, issues, missing_code, candidate_id=candidate_id, source_id=source_id)


def _require_fields(
    obj: dict[str, Any],
    required_fields: set[str],
    path: str,
    issues: list[ValidationIssue],
    code: str,
    *,
    candidate_id: str | None = None,
    source_id: str | None = None,
) -> None:
    missing = sorted(required_fields - set(obj))
    for field in missing:
        issues.append(_issue(code, f"{path}.{field}", f"Missing required field: {field}.", candidate_id=candidate_id, source_id=source_id))


def _nested(obj: dict[str, Any], parent: str, child: str) -> Any:
    value = obj.get(parent)
    if isinstance(value, dict):
        return value.get(child)
    return None


def _sorted_issues(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    return sorted(
        issues,
        key=lambda issue: (
            issue.candidate_id or "",
            issue.code,
            issue.field,
            issue.source_id or "",
            issue.severity,
        ),
    )


def _issue_codes(issues: list[ValidationIssue], *, severity: str | None = None) -> set[str]:
    if severity is None:
        return {issue.code for issue in issues}
    return {issue.code for issue in issues if issue.severity == severity}


def build_report(package: dict[str, Any], issues: list[ValidationIssue], *, strict_mode: bool = False) -> dict[str, Any]:
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    strict_warning_failure = strict_mode and bool(warnings)

    if errors or strict_warning_failure:
        status = "FAIL_BLOCKING_ERRORS"
    elif warnings:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"

    candidates = package.get("candidates") if isinstance(package.get("candidates"), list) else []
    candidate_dicts = [candidate for candidate in candidates if isinstance(candidate, dict)]
    public_statuses = [_nested(candidate, "public_distribution_policy", "public_distribution_status") for candidate in candidate_dicts]
    learner_facing_statuses = [_nested(candidate, "listening_policy", "student_facing_status") for candidate in candidate_dicts]

    return {
        "schema_version": EXPECTED_REPORT_SCHEMA_VERSION,
        "validator_contract_version": EXPECTED_VALIDATOR_CONTRACT_VERSION,
        "epic_id": EXPECTED_EPIC_ID,
        "phase_id": EXPECTED_PHASE_ID,
        "task_id": TASK_ID,
        "status": status,
        "issue_count": len(issues),
        "blocking_issue_count": len(errors) + (len(warnings) if strict_mode else 0),
        "warning_count": len(warnings),
        "source_record_count": len({issue.source_id for issue in issues if issue.source_id}),
        "candidate_count": len(candidate_dicts),
        "eligible_candidate_count": sum(1 for candidate in candidate_dicts if candidate.get("eligibility_class") in ELIGIBLE_CLASSES),
        "blocked_candidate_count": sum(1 for candidate in candidate_dicts if str(candidate.get("eligibility_class", "")).startswith("P5_BLOCKED") or candidate.get("eligibility_class") in {"P5_REFERENCE_ONLY", "P5_DESIGN_CANDIDATE_ONLY"}),
        "public_distribution_candidate_count": sum(1 for status_value in public_statuses if status_value in PUBLIC_VALUES),
        "internal_only_candidate_count": sum(1 for status_value in public_statuses if status_value in {"blocked", "internal_only", "forbidden"}),
        "learner_facing_candidate_count": sum(1 for status_value in learner_facing_statuses if status_value not in LEARNER_FORBIDDEN_STATUSES),
        "learner_state_attempt_count": sum(1 for issue in issues if issue.code == "P5_LEARNER_STATE_UPDATE_ATTEMPT"),
        "adaptive_attempt_count": sum(1 for issue in issues if issue.code == "P5_ADAPTIVE_ASSIGNMENT_ATTEMPT"),
        "issues": [issue.as_dict() for issue in issues if issue.severity == "error"],
        "warnings": [issue.as_dict() for issue in issues if issue.severity == "warning"],
        "gate_metrics": _build_gate_metrics(issues),
        "next_shortest_step": "E4S-P5-I2_ListeningCandidatePackageBuilderImplementation" if status in {"PASS", "PASS_WITH_WARNINGS"} else "FIX_P5_LISTENING_CANDIDATE_PACKAGE",
    }


def _build_gate_metrics(issues: list[ValidationIssue]) -> dict[str, str]:
    error_codes = _issue_codes(issues, severity="error")

    def gate(*codes: str) -> str:
        return "FAIL" if any(code in error_codes for code in codes) else "PASS"

    return {
        "schema_version_valid": gate("P5_BAD_SCHEMA_VERSION", "P5_BAD_PACKAGE_PHASE"),
        "candidate_ids_unique": gate("P5_DUPLICATE_CANDIDATE_ID"),
        "candidate_order_deterministic": gate("P5_NON_DETERMINISTIC_ORDER"),
        "source_trace_complete": gate("P5_MISSING_SOURCE_TRACE", "P5_MISSING_TEXT_UNIT_ID"),
        "source_manifest_cross_refs_valid": gate("P5_UNKNOWN_SOURCE_ID", "P5_UNKNOWN_SOURCE_FAMILY"),
        "authority_roles_allowed": gate("P5_UNAPPROVED_AUTHORITY_ROLE"),
        "status_artifacts_blocked": gate("P5_STATUS_ARTIFACT_USED_AS_CONTENT", "P5_GOVERNANCE_ARTIFACT_USED_AS_CONTENT"),
        "generated_unreviewed_blocked": gate("P5_GENERATED_UNREVIEWED_CONTENT"),
        "raz_wordlist_audio_blocked": gate("P5_RAZ_WORDLIST_USED_AS_AUDIO_SOURCE"),
        "license_public_distribution_checked": gate("P5_LICENSE_PUBLIC_DISTRIBUTION_UNKNOWN", "P5_RESTRICTED_SOURCE_MARKED_PUBLIC", "P5_PUBLIC_AUDIO_WITHOUT_LICENSE_CLEARANCE"),
        "audio_policy_checked": gate("P5_MISSING_AUDIO_POLICY_VERSION"),
        "tts_policy_checked": gate("P5_MISSING_TTS_PERMISSION", "P5_TTS_ENABLED_WITHOUT_POLICY"),
        "voice_policy_checked": gate("P5_MISSING_VOICE_POLICY"),
        "storage_policy_checked": gate("P5_MISSING_STORAGE_POLICY"),
        "timing_policy_checked": gate("P5_TIMING_PRESENT_WITHOUT_POLICY"),
        "learner_facing_output_blocked": gate("P5_LEARNER_FACING_OUTPUT_WITHOUT_APPROVAL"),
        "learner_state_update_blocked": gate("P5_LEARNER_STATE_UPDATE_ATTEMPT"),
        "adaptive_assignment_blocked": gate("P5_ADAPTIVE_ASSIGNMENT_ATTEMPT"),
        "content_promotion_blocked": gate("P5_CONTENT_PROMOTION_ATTEMPT"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate E4S P5 listening candidate packages.")
    parser.add_argument("--candidate-package", type=Path, default=DEFAULT_CANDIDATE_PACKAGE_PATH)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST_PATH)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--strict-mode", action="store_true", help="Treat warnings as blocking failures.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package = load_json(args.candidate_package, label="Candidate package")
    source_manifest = load_json(args.source_manifest, label="Source manifest")
    issues = validate_package(package, source_manifest)
    report = build_report(package, issues, strict_mode=args.strict_mode)

    if args.report_output:
        args.report_output.parent.mkdir(parents=True, exist_ok=True)
        args.report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"PASS", "PASS_WITH_WARNINGS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
