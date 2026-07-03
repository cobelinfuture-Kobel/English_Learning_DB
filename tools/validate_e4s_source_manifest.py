#!/usr/bin/env python3
"""Validate the E4S Source Manifest.

Scope:
- E4S-P0-S3 validator for the metadata-only source manifest.
- No source payload extraction.
- No learner-facing output.
- No source promotion.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "ulga" / "graph" / "e4s_source_manifest.json"

EXPECTED_SCHEMA_VERSION = "E4S_SOURCE_MANIFEST_V1"
EXPECTED_EPIC_ID = "E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem"
EXPECTED_PHASE_ID = "E4S-P0_SourceAuthorityAndCorpusRoadmap"
EXPECTED_CONTRACT_PATH = "docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md"

REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "epic_id",
    "phase_id",
    "task_id",
    "contract_path",
    "artifact_policy",
    "records",
}

REQUIRED_RECORD_FIELDS = {
    "source_id",
    "source_family",
    "source_type",
    "authority_role",
    "path",
    "format",
    "exists",
    "license_status",
    "review_status",
    "allowed_use",
    "blocked_use",
    "promotion_rule",
    "target_phase",
    "target_ulga_stage",
    "risk_flags",
    "notes",
}

SOURCE_FAMILY = {
    "governance",
    "roadmap",
    "grammar_profile",
    "vocabulary_profile",
    "frequency_profile",
    "chunk_authority",
    "morphology_authority",
    "theme_authority",
    "pattern_authority",
    "cambridge_vocabulary",
    "raz_wordlist",
    "raz_reading_corpus",
    "writing_template_corpus",
    "parent_functional_sentence_corpus",
    "story_dialogue_corpus",
    "assessment_pattern_corpus",
    "generated_content_candidate",
    "status_artifact",
    "google_drive_reference",
    "github_repository",
    "unknown",
}

SOURCE_TYPE = {
    "policy_doc",
    "roadmap_doc",
    "design_scan",
    "source_excel",
    "source_pdf",
    "source_text",
    "source_json",
    "source_jsonl",
    "source_markdown",
    "source_folder",
    "source_archive",
    "derived_json",
    "derived_report",
    "status_html",
    "status_snapshot",
    "external_reference",
    "generated_candidate_set",
    "unknown",
}

AUTHORITY_ROLE = {
    "primary_authority",
    "secondary_authority",
    "evidence_only",
    "candidate_only",
    "template_corpus",
    "functional_sentence_corpus",
    "dialogue_corpus_candidate",
    "reading_corpus_candidate",
    "assessment_pattern_candidate",
    "generated_candidate",
    "status_only",
    "governance_only",
    "reference_only",
    "unknown_pending_review",
}

FORMAT = {
    "markdown",
    "txt",
    "xlsx",
    "csv",
    "json",
    "jsonl",
    "pdf",
    "html",
    "folder",
    "archive",
    "url_reference",
    "repo_reference",
    "unknown",
}

LICENSE_STATUS = {
    "owned",
    "licensed_for_internal_use",
    "public_reference_only",
    "restricted_reference_only",
    "unknown_pending_review",
    "not_redistributable",
}

REVIEW_STATUS = {
    "not_reviewed",
    "metadata_reviewed",
    "content_sample_reviewed",
    "schema_reviewed",
    "validator_reviewed",
    "promotion_reviewed",
    "rejected",
}

ALLOWED_USE = {
    "register_in_manifest",
    "summarize_metadata",
    "source_trace_only",
    "internal_reference",
    "schema_design",
    "validator_design",
    "query_index_design",
    "candidate_query",
    "candidate_generation",
    "reading_candidate_selection",
    "reading_practice_candidate",
    "writing_template_candidate",
    "dialogue_candidate",
    "speaking_prompt_candidate",
    "listening_candidate",
    "assessment_pattern_design",
    "assessment_candidate",
    "manual_review",
    "promotion_review",
}

BLOCKED_USE = {
    "learner_facing_output",
    "public_distribution",
    "final_authority_promotion",
    "automatic_promotion",
    "direct_vocab_authority",
    "direct_grammar_authority",
    "direct_reading_authority",
    "direct_dialogue_authority",
    "direct_writing_authority",
    "direct_assessment_authority",
    "adaptive_recommendation",
    "learner_state_update",
    "large_scale_generation",
    "audio_generation",
    "image_generation",
    "app_runtime_use",
}

PROMOTION_RULE = {
    "never_promote",
    "candidate_only_until_review",
    "evidence_only_never_authority",
    "template_only_until_derivation_review",
    "requires_manual_review",
    "requires_validator_review",
    "requires_promotion_task",
    "already_governance_not_content",
    "status_artifact_never_content",
    "unknown_blocked",
}

TARGET_PHASE = {
    "E4S-P0_SourceAuthorityAndCorpusRoadmap",
    "E4S-P1_ReadingV1SourceGroundedPractice",
    "E4S-P2_AssessmentPatternExpansion",
    "E4S-P3_WritingPracticeSystem",
    "E4S-P4_DialogueSpeakingPromptSystem",
    "E4S-P5_ListeningPracticeSystem",
    "E4S-P6_ErrorTaggingAndWeakPointDiagnosis",
    "E4S-P7_AdaptiveLearningPathIntegration",
    "E4S-P8_FourSkillBridgeAndProductLayer",
    "DEFERRED",
    "UNKNOWN",
}

RISK_FLAGS = {
    "license_unknown",
    "source_trace_required",
    "not_for_public_distribution",
    "candidate_not_authority",
    "status_not_content",
    "large_file",
    "drive_only",
    "github_safe",
    "duplicate_risk",
    "schema_unknown",
    "level_mapping_risk",
    "promotion_risk",
    "learner_facing_blocked",
    "requires_manual_review",
}

ENUMS = {
    "source_family": SOURCE_FAMILY,
    "source_type": SOURCE_TYPE,
    "authority_role": AUTHORITY_ROLE,
    "format": FORMAT,
    "license_status": LICENSE_STATUS,
    "review_status": REVIEW_STATUS,
    "promotion_rule": PROMOTION_RULE,
    "target_phase": TARGET_PHASE,
}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str
    severity: str = "error"

    def as_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }


def _issue(code: str, path: str, message: str, severity: str = "error") -> ValidationIssue:
    return ValidationIssue(code=code, path=path, message=message, severity=severity)


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Manifest is not valid JSON: {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise SystemExit("Manifest root must be a JSON object.")
    return payload


def validate_manifest(manifest: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    _validate_top_level(manifest, issues)
    records = manifest.get("records")
    if not isinstance(records, list):
        issues.append(_issue("E4S_MANIFEST_RECORDS_NOT_ARRAY", "$.records", "records must be an array."))
        return issues

    _validate_record_collection(records, issues)
    for index, record in enumerate(records):
        _validate_record(record, index, issues)

    return issues


def _validate_top_level(manifest: dict[str, Any], issues: list[ValidationIssue]) -> None:
    missing = sorted(REQUIRED_TOP_LEVEL_FIELDS - set(manifest))
    for field in missing:
        issues.append(_issue("E4S_MANIFEST_MISSING_TOP_LEVEL_FIELD", f"$.{field}", f"Missing top-level field: {field}."))

    if manifest.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        issues.append(_issue("E4S_MANIFEST_BAD_SCHEMA_VERSION", "$.schema_version", f"Expected {EXPECTED_SCHEMA_VERSION}."))
    if manifest.get("epic_id") != EXPECTED_EPIC_ID:
        issues.append(_issue("E4S_MANIFEST_BAD_EPIC_ID", "$.epic_id", f"Expected {EXPECTED_EPIC_ID}."))
    if manifest.get("phase_id") != EXPECTED_PHASE_ID:
        issues.append(_issue("E4S_MANIFEST_BAD_PHASE_ID", "$.phase_id", f"Expected {EXPECTED_PHASE_ID}."))
    if manifest.get("contract_path") != EXPECTED_CONTRACT_PATH:
        issues.append(_issue("E4S_MANIFEST_BAD_CONTRACT_PATH", "$.contract_path", f"Expected {EXPECTED_CONTRACT_PATH}."))

    artifact_policy = manifest.get("artifact_policy")
    if not isinstance(artifact_policy, dict):
        issues.append(_issue("E4S_MANIFEST_ARTIFACT_POLICY_NOT_OBJECT", "$.artifact_policy", "artifact_policy must be an object."))
        return

    forbidden_expectations = {
        "source_payload_extraction": "forbidden",
        "learner_facing_output": "forbidden",
        "authority_promotion": "forbidden",
        "deterministic_order": "source_id",
    }
    for key, expected in forbidden_expectations.items():
        if artifact_policy.get(key) != expected:
            issues.append(_issue("E4S_MANIFEST_BAD_ARTIFACT_POLICY", f"$.artifact_policy.{key}", f"Expected {expected!r}."))


def _validate_record_collection(records: list[Any], issues: list[ValidationIssue]) -> None:
    source_ids: list[str] = []
    for record in records:
        if isinstance(record, dict) and isinstance(record.get("source_id"), str):
            source_ids.append(record["source_id"])

    seen: set[str] = set()
    for source_id in source_ids:
        if source_id in seen:
            issues.append(_issue("E4S_SOURCE_DUPLICATE_ID", "$.records", f"Duplicate source_id: {source_id}."))
        seen.add(source_id)

    if source_ids != sorted(source_ids):
        issues.append(_issue("E4S_SOURCE_NON_DETERMINISTIC_ORDER", "$.records", "Records must be sorted by source_id."))


def _validate_record(record: Any, index: int, issues: list[ValidationIssue]) -> None:
    path = f"$.records[{index}]"
    if not isinstance(record, dict):
        issues.append(_issue("E4S_SOURCE_RECORD_NOT_OBJECT", path, "Source record must be an object."))
        return

    source_id = record.get("source_id", f"<record:{index}>")
    record_path = f"{path}[{source_id}]"

    missing = sorted(REQUIRED_RECORD_FIELDS - set(record))
    for field in missing:
        issues.append(_issue("E4S_SOURCE_MISSING_REQUIRED_FIELD", f"{record_path}.{field}", f"Missing required field: {field}."))

    for field, allowed_values in ENUMS.items():
        if field in record and record[field] not in allowed_values:
            issues.append(_issue("E4S_SOURCE_UNKNOWN_ENUM", f"{record_path}.{field}", f"Unknown {field}: {record[field]!r}."))

    _validate_array_field(record, record_path, "allowed_use", ALLOWED_USE, issues, require_non_empty=True)
    _validate_array_field(record, record_path, "blocked_use", BLOCKED_USE, issues, require_non_empty=False)
    _validate_array_field(record, record_path, "risk_flags", RISK_FLAGS, issues, require_non_empty=False)
    _validate_notes(record, record_path, issues)

    allowed = set(record.get("allowed_use", [])) if isinstance(record.get("allowed_use"), list) else set()
    blocked = set(record.get("blocked_use", [])) if isinstance(record.get("blocked_use"), list) else set()
    conflict = sorted(allowed & blocked)
    if conflict:
        issues.append(_issue("E4S_SOURCE_ALLOWED_BLOCKED_CONFLICT", record_path, f"allowed_use and blocked_use conflict: {conflict}."))

    _validate_license_rules(record, record_path, issues)
    _validate_family_rules(record, record_path, issues)


def _validate_array_field(
    record: dict[str, Any],
    record_path: str,
    field: str,
    allowed_values: set[str],
    issues: list[ValidationIssue],
    *,
    require_non_empty: bool,
) -> None:
    value = record.get(field)
    if not isinstance(value, list):
        issues.append(_issue("E4S_SOURCE_BAD_ARRAY_FIELD", f"{record_path}.{field}", f"{field} must be an array."))
        return

    if require_non_empty and not value:
        issues.append(_issue("E4S_SOURCE_EMPTY_ALLOWED_USE", f"{record_path}.{field}", f"{field} must not be empty."))

    for item in value:
        if not isinstance(item, str):
            issues.append(_issue("E4S_SOURCE_BAD_ARRAY_ITEM", f"{record_path}.{field}", f"{field} entries must be strings."))
        elif item not in allowed_values:
            issues.append(_issue("E4S_SOURCE_UNKNOWN_ARRAY_ENUM", f"{record_path}.{field}", f"Unknown {field} value: {item!r}."))


def _validate_notes(record: dict[str, Any], record_path: str, issues: list[ValidationIssue]) -> None:
    notes = record.get("notes")
    if not isinstance(notes, list):
        issues.append(_issue("E4S_SOURCE_BAD_NOTES", f"{record_path}.notes", "notes must be an array."))
        return
    for note in notes:
        if not isinstance(note, str):
            issues.append(_issue("E4S_SOURCE_BAD_NOTES", f"{record_path}.notes", "notes entries must be strings."))


def _validate_license_rules(record: dict[str, Any], record_path: str, issues: list[ValidationIssue]) -> None:
    license_status = record.get("license_status")
    blocked = set(record.get("blocked_use", [])) if isinstance(record.get("blocked_use"), list) else set()
    risk_flags = set(record.get("risk_flags", [])) if isinstance(record.get("risk_flags"), list) else set()

    if license_status == "unknown_pending_review" and "license_unknown" not in risk_flags:
        issues.append(_issue("E4S_SOURCE_LICENSE_UNKNOWN_WITHOUT_FLAG", record_path, "unknown_pending_review requires risk_flags: license_unknown."))
    if license_status == "not_redistributable" and not {"public_distribution", "learner_facing_output"}.issubset(blocked):
        issues.append(_issue("E4S_SOURCE_NOT_REDISTRIBUTABLE_NOT_BLOCKED", record_path, "not_redistributable must block public_distribution and learner_facing_output."))
    if license_status == "restricted_reference_only" and "public_distribution" not in blocked:
        issues.append(_issue("E4S_SOURCE_RESTRICTED_WITHOUT_PUBLIC_BLOCK", record_path, "restricted_reference_only must block public_distribution."))


def _validate_family_rules(record: dict[str, Any], record_path: str, issues: list[ValidationIssue]) -> None:
    family = record.get("source_family")
    role = record.get("authority_role")
    promotion_rule = record.get("promotion_rule")
    allowed = set(record.get("allowed_use", [])) if isinstance(record.get("allowed_use"), list) else set()
    blocked = set(record.get("blocked_use", [])) if isinstance(record.get("blocked_use"), list) else set()
    risk_flags = set(record.get("risk_flags", [])) if isinstance(record.get("risk_flags"), list) else set()
    review_status = record.get("review_status")

    if family == "generated_content_candidate":
        _require_value(role == "generated_candidate", "E4S_GENERATED_BAD_AUTHORITY_ROLE", record_path, "generated_content_candidate must use authority_role=generated_candidate.", issues)
        _require_value("candidate_not_authority" in risk_flags, "E4S_GENERATED_MISSING_CANDIDATE_FLAG", record_path, "generated_content_candidate requires risk_flags: candidate_not_authority.", issues)
        _require_values({"automatic_promotion", "final_authority_promotion"}, blocked, "E4S_GENERATED_PROMOTION_NOT_BLOCKED", record_path, issues)
        if promotion_rule == "requires_promotion_task" and review_status not in {"validator_reviewed", "promotion_reviewed"}:
            issues.append(_issue("E4S_GENERATED_PROMOTION_REVIEW_TOO_WEAK", record_path, "Generated content cannot use requires_promotion_task before validator_reviewed or promotion_reviewed."))

    if family == "status_artifact":
        _require_value(role == "status_only", "E4S_STATUS_BAD_AUTHORITY_ROLE", record_path, "status_artifact must use authority_role=status_only.", issues)
        _require_value(promotion_rule == "status_artifact_never_content", "E4S_STATUS_BAD_PROMOTION_RULE", record_path, "status_artifact must use promotion_rule=status_artifact_never_content.", issues)
        _require_values({"learner_facing_output", "direct_reading_authority"}, blocked, "E4S_STATUS_CONTENT_NOT_BLOCKED", record_path, issues)

    if family == "raz_wordlist":
        _require_value(role == "evidence_only", "E4S_RAZ_WORDLIST_BAD_AUTHORITY_ROLE", record_path, "raz_wordlist must use authority_role=evidence_only.", issues)
        _require_value("direct_vocab_authority" in blocked, "E4S_RAZ_WORDLIST_DIRECT_VOCAB_NOT_BLOCKED", record_path, "raz_wordlist must block direct_vocab_authority.", issues)

    if family == "raz_reading_corpus":
        _require_value(role == "reading_corpus_candidate", "E4S_RAZ_READING_BAD_AUTHORITY_ROLE", record_path, "raz_reading_corpus must use authority_role=reading_corpus_candidate.", issues)
        _require_value("source_trace_required" in risk_flags, "E4S_RAZ_READING_MISSING_TRACE_FLAG", record_path, "raz_reading_corpus must preserve source trace.", issues)
        _require_value("learner_facing_output" in blocked, "E4S_RAZ_READING_LEARNER_OUTPUT_NOT_BLOCKED", record_path, "raz_reading_corpus must block learner_facing_output during P0.", issues)

    if family == "writing_template_corpus":
        _require_value("direct_reading_authority" not in allowed, "E4S_WRITING_DIRECT_READING_ALLOWED", record_path, "writing_template_corpus must not allow direct_reading_authority.", issues)

    if family == "parent_functional_sentence_corpus":
        _require_value("direct_dialogue_authority" not in allowed, "E4S_PARENT_FUNCTIONAL_DIRECT_DIALOGUE_ALLOWED", record_path, "parent_functional_sentence_corpus must not allow direct_dialogue_authority.", issues)

    if family == "story_dialogue_corpus" and review_status != "promotion_reviewed":
        _require_value(role == "dialogue_corpus_candidate", "E4S_STORY_DIALOGUE_BAD_AUTHORITY_ROLE", record_path, "story_dialogue_corpus must remain dialogue_corpus_candidate until promotion_reviewed.", issues)


def _require_value(condition: bool, code: str, path: str, message: str, issues: list[ValidationIssue]) -> None:
    if not condition:
        issues.append(_issue(code, path, message))


def _require_values(required_values: set[str], actual_values: set[str], code: str, path: str, issues: list[ValidationIssue]) -> None:
    missing = sorted(required_values - actual_values)
    if missing:
        issues.append(_issue(code, path, f"Missing required blocked_use values: {missing}."))


def build_report(issues: list[ValidationIssue]) -> dict[str, Any]:
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    return {
        "schema_version": "E4S_SOURCE_MANIFEST_VALIDATION_REPORT_V1",
        "task_id": "E4S-P0-S3_SourceManifestValidator_Implementation",
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": [issue.as_dict() for issue in issues],
        "gate_metrics": {
            "required_fields_checked": "PASS",
            "enum_values_checked": "PASS",
            "duplicate_source_id_checked": "PASS",
            "allowed_blocked_conflict_checked": "PASS",
            "license_rules_checked": "PASS",
            "family_rules_checked": "PASS",
            "source_payload_extraction": "NOT_PERFORMED",
            "learner_facing_output": "NOT_PERFORMED",
            "authority_promotion": "NOT_PERFORMED",
        },
        "next_shortest_step": "E4S-P0-S4_AuthorityMappingMatrix_DesignScan",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the E4S source manifest.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--report-output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    report = build_report(validate_manifest(manifest))

    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if args.report_output:
        args.report_output.parent.mkdir(parents=True, exist_ok=True)
        args.report_output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
