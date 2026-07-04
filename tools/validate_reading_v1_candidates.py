"""Validate E4S Reading V1 candidate artifacts.

Validator boundary: validates schema-shaped, metadata-only Reading V1 candidates.
It never creates learner-facing output, learner state, adaptive recommendations,
worksheet exports, source payload copies, or source/content authority upgrades.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "READING_V1_VALIDATION_REPORT_V1"
PHASE_ID = "E4S-P1_ReadingV1SourceGroundedPractice"
TASK_ID = "E4S-P1-S12_ReadingV1_CandidateValidator_Implementation"
VALIDATOR_ID = "validate_reading_v1_candidates"
VALIDATOR_VERSION = "1.0.0"
NEXT_SHORTEST_STEP = "E4S-P1-S13_ReadingV1_CandidateValidationReport_ReadbackQA"

PASS = "PASS"
PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"

ALLOWED_QUESTION_TYPES = {
    "literal_who",
    "literal_what",
    "literal_where",
    "literal_when",
    "literal_yes_no",
    "literal_count",
    "literal_color",
    "literal_action",
    "sequence_order",
    "main_idea_simple",
    "vocabulary_in_context_basic",
}

ALLOWED_SOURCE_ROLES = {
    "RAZ_READING_CORPUS_A_T_CANDIDATE": ("raz_reading_corpus", "reading_corpus_candidate"),
    "RAZ_WORDLIST_A_T_EVIDENCE": ("raz_wordlist", "evidence_only"),
    "EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE": ("grammar_profile", "reference_only"),
    "EVP_SOURCE_ENGLISH_VOCABULARY_PROFILE_ONLINE": ("vocabulary_profile", "reference_only"),
    "NGSL_SOURCE_FREQUENCY_PROFILE": ("frequency_profile", "reference_only"),
    "CHUNK_SAFE_LAYER_REFERENCE": ("chunk_authority", "reference_only"),
}

BLOCKED_OUTPUT_FIELDS = {
    "learner_facing_output_created",
    "student_html_created",
    "worksheet_created",
    "learner_event_created",
    "learner_state_updated",
    "adaptive_recommendation_created",
    "authority_promotion_performed",
    "large_scale_generation_performed",
}

TOP_LEVEL_REQUIRED = {
    "reading_candidate_id",
    "schema_version",
    "phase_id",
    "task_id",
    "candidate_status",
    "source_trace",
    "source_policy",
    "reading_payload_ref",
    "question_model",
    "answer_model",
    "evidence_model",
    "level_metadata",
    "situation_metadata",
    "skill_metadata",
    "constraint_refs",
    "validation_state",
    "manual_review_state",
    "blocked_output_state",
    "audit_trail",
}


class ValidationIssue(dict):
    def __init__(self, code: str, severity: str, candidate_id: str | None, field_path: str, message: str, blocking: bool, recommended_action: str) -> None:
        super().__init__(
            code=code,
            severity=severity,
            candidate_id=candidate_id,
            field_path=field_path,
            message=message,
            blocking=blocking,
            recommended_action=recommended_action,
        )


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_candidates(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    raise ValueError("candidate_path must contain a JSON object or JSON list")


def load_manifest_ids(path: Path) -> set[str]:
    payload = load_json(path)
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise ValueError("manifest must contain records list")
    return {str(record.get("source_id")) for record in records if isinstance(record, dict)}


def add_issue(issues: list[ValidationIssue], code: str, candidate_id: str | None, field_path: str, message: str, action: str = "Fix candidate or block before next gate.") -> None:
    issues.append(ValidationIssue(code, "high", candidate_id, field_path, message, True, action))


def add_warning(warnings: list[ValidationIssue], code: str, candidate_id: str | None, field_path: str, message: str, action: str = "Review before learner-facing use.") -> None:
    warnings.append(ValidationIssue(code, "medium", candidate_id, field_path, message, False, action))


def validate_schema_structure(candidate: dict[str, Any], issues: list[ValidationIssue]) -> None:
    candidate_id = str(candidate.get("reading_candidate_id", "UNKNOWN"))
    missing = sorted(TOP_LEVEL_REQUIRED - set(candidate))
    if missing:
        add_issue(issues, "READING_V1_SCHEMA_INVALID", candidate_id, "$", f"Missing top-level fields: {missing}")

    if candidate.get("schema_version") != "READING_V1_CANDIDATE_SCHEMA_V1":
        add_issue(issues, "READING_V1_SCHEMA_INVALID", candidate_id, "schema_version", "Invalid schema_version.")
    if candidate.get("phase_id") != PHASE_ID:
        add_issue(issues, "READING_V1_SCHEMA_INVALID", candidate_id, "phase_id", "Invalid phase_id.")

    required_objects = [
        "source_trace",
        "source_policy",
        "reading_payload_ref",
        "question_model",
        "answer_model",
        "evidence_model",
        "level_metadata",
        "situation_metadata",
        "skill_metadata",
        "constraint_refs",
        "validation_state",
        "manual_review_state",
        "blocked_output_state",
        "audit_trail",
    ]
    for name in required_objects:
        if not isinstance(candidate.get(name), dict):
            add_issue(issues, "READING_V1_SCHEMA_INVALID", candidate_id, name, "Required object is missing or not an object.")


def validate_source(candidate: dict[str, Any], manifest_ids: set[str], issues: list[ValidationIssue]) -> None:
    candidate_id = str(candidate.get("reading_candidate_id", "UNKNOWN"))
    trace = candidate.get("source_trace", {}) if isinstance(candidate.get("source_trace"), dict) else {}
    source_id = str(trace.get("source_id", ""))
    family = str(trace.get("source_family", ""))
    role = str(trace.get("authority_role", ""))

    required = ["source_id", "source_family", "authority_role", "source_path_ref", "source_license_status", "source_review_status", "source_trace_required", "source_payload_copied"]
    for field in required:
        if field not in trace or trace.get(field) in {"", None}:
            add_issue(issues, "READING_V1_SOURCE_TRACE_MISSING", candidate_id, f"source_trace.{field}", "Source trace field is missing.")

    if source_id not in manifest_ids:
        add_issue(issues, "READING_V1_UNKNOWN_SOURCE_ID", candidate_id, "source_trace.source_id", "Source id is not present in manifest.")
    if source_id not in ALLOWED_SOURCE_ROLES:
        add_issue(issues, "READING_V1_INELIGIBLE_SOURCE", candidate_id, "source_trace.source_id", "Source id is not eligible for Reading V1.")
        return

    expected_family, expected_role = ALLOWED_SOURCE_ROLES[source_id]
    if family != expected_family:
        add_issue(issues, "READING_V1_SOURCE_FAMILY_MISMATCH", candidate_id, "source_trace.source_family", "Source family does not match contract.")
    if role != expected_role:
        add_issue(issues, "READING_V1_AUTHORITY_ROLE_MISMATCH", candidate_id, "source_trace.authority_role", "Authority role does not match contract.")
    if source_id == "RAZ_READING_CORPUS_A_T_CANDIDATE" and role != "reading_corpus_candidate":
        add_issue(issues, "READING_V1_DIRECT_READING_AUTHORITY", candidate_id, "source_trace.authority_role", "RAZ reading corpus must remain candidate, not direct authority.")
    if source_id == "RAZ_WORDLIST_A_T_EVIDENCE" and role != "evidence_only":
        add_issue(issues, "READING_V1_RAZ_WORDLIST_AS_VOCAB_AUTHORITY", candidate_id, "source_trace.authority_role", "RAZ wordlist must remain evidence only.")
    if trace.get("source_payload_copied") is not False:
        add_issue(issues, "READING_V1_SOURCE_PAYLOAD_COPIED", candidate_id, "source_trace.source_payload_copied", "Source payload copied must remain false.")


def validate_policy(candidate: dict[str, Any], issues: list[ValidationIssue]) -> None:
    candidate_id = str(candidate.get("reading_candidate_id", "UNKNOWN"))
    policy = candidate.get("source_policy", {}) if isinstance(candidate.get("source_policy"), dict) else {}
    if policy.get("public_distribution_allowed") is not False:
        add_issue(issues, "READING_V1_PUBLIC_DISTRIBUTION_ALLOWED", candidate_id, "source_policy.public_distribution_allowed", "Public distribution must remain false.")
    if policy.get("learner_facing_allowed") is not False:
        add_issue(issues, "READING_V1_LEARNER_FACING_ALLOWED", candidate_id, "source_policy.learner_facing_allowed", "Learner-facing use must remain false.")
    if policy.get("authority_promotion_allowed") is not False:
        add_issue(issues, "READING_V1_AUTHORITY_PROMOTION_ALLOWED", candidate_id, "source_policy.authority_promotion_allowed", "Authority promotion must remain false.")


def validate_question_answer_evidence(candidate: dict[str, Any], issues: list[ValidationIssue]) -> None:
    candidate_id = str(candidate.get("reading_candidate_id", "UNKNOWN"))
    question = candidate.get("question_model", {}) if isinstance(candidate.get("question_model"), dict) else {}
    answer = candidate.get("answer_model", {}) if isinstance(candidate.get("answer_model"), dict) else {}
    evidence = candidate.get("evidence_model", {}) if isinstance(candidate.get("evidence_model"), dict) else {}
    payload = candidate.get("reading_payload_ref", {}) if isinstance(candidate.get("reading_payload_ref"), dict) else {}

    if question.get("question_type") not in ALLOWED_QUESTION_TYPES:
        add_issue(issues, "READING_V1_QUESTION_TYPE_BLOCKED", candidate_id, "question_model.question_type", "Question type is not allowed in Reading V1 pilot.")
    if question.get("requires_evidence") is not True:
        add_issue(issues, "READING_V1_QUESTION_NOT_EVIDENCE_REQUIRED", candidate_id, "question_model.requires_evidence", "Question must require evidence.")
    if not answer.get("answer_evidence_ref"):
        add_issue(issues, "READING_V1_ANSWER_EVIDENCE_MISSING", candidate_id, "answer_model.answer_evidence_ref", "Answer evidence ref is missing.")
    if not evidence.get("source_trace_ref") or not evidence.get("evidence_locator"):
        add_issue(issues, "READING_V1_EVIDENCE_TRACE_MISSING", candidate_id, "evidence_model", "Evidence source trace ref or locator is missing.")
    if evidence.get("evidence_text_allowed") is False and "evidence_text" in evidence:
        add_issue(issues, "READING_V1_SOURCE_PAYLOAD_COPIED", candidate_id, "evidence_model.evidence_text", "Evidence text present while evidence_text_allowed is false.")
    if payload.get("passage_excerpt_allowed") is False and "passage_excerpt" in payload:
        add_issue(issues, "READING_V1_SOURCE_PAYLOAD_COPIED", candidate_id, "reading_payload_ref.passage_excerpt", "Passage excerpt present while passage_excerpt_allowed is false.")


def validate_level_skill_and_blocked_outputs(candidate: dict[str, Any], issues: list[ValidationIssue]) -> None:
    candidate_id = str(candidate.get("reading_candidate_id", "UNKNOWN"))
    level = candidate.get("level_metadata", {}) if isinstance(candidate.get("level_metadata"), dict) else {}
    skill = candidate.get("skill_metadata", {}) if isinstance(candidate.get("skill_metadata"), dict) else {}
    blocked = candidate.get("blocked_output_state", {}) if isinstance(candidate.get("blocked_output_state"), dict) else {}

    if level.get("learner_placement_allowed") is not False:
        add_issue(issues, "READING_V1_LEVEL_AS_LEARNER_PLACEMENT", candidate_id, "level_metadata.learner_placement_allowed", "Level metadata cannot become learner placement.")
    if skill.get("skill_fit") != "reading_candidate" or skill.get("multi_skill_expansion_allowed") is not False:
        add_issue(issues, "READING_V1_MULTISKILL_EXPANSION", candidate_id, "skill_metadata", "Candidate must remain Reading-only.")

    for field in BLOCKED_OUTPUT_FIELDS:
        if blocked.get(field) is not False:
            code = {
                "learner_event_created": "READING_V1_LEARNER_EVENT_CREATED",
                "learner_state_updated": "READING_V1_LEARNER_STATE_UPDATED",
                "adaptive_recommendation_created": "READING_V1_ADAPTIVE_RECOMMENDATION_CREATED",
                "student_html_created": "READING_V1_STUDENT_HTML_CREATED",
                "worksheet_created": "READING_V1_WORKSHEET_CREATED",
                "large_scale_generation_performed": "READING_V1_LARGE_SCALE_GENERATION",
            }.get(field, "READING_V1_SCHEMA_INVALID")
            add_issue(issues, code, candidate_id, f"blocked_output_state.{field}", "Blocked output field must remain false.")


def validate_audit_and_warnings(candidate: dict[str, Any], issues: list[ValidationIssue], warnings: list[ValidationIssue]) -> None:
    candidate_id = str(candidate.get("reading_candidate_id", "UNKNOWN"))
    audit = candidate.get("audit_trail", {}) if isinstance(candidate.get("audit_trail"), dict) else {}
    manual = candidate.get("manual_review_state", {}) if isinstance(candidate.get("manual_review_state"), dict) else {}
    level = candidate.get("level_metadata", {}) if isinstance(candidate.get("level_metadata"), dict) else {}
    situation = candidate.get("situation_metadata", {}) if isinstance(candidate.get("situation_metadata"), dict) else {}

    for field in ["created_by_task", "created_from_contracts", "warnings", "deferred_issues"]:
        if field not in audit:
            add_issue(issues, "READING_V1_MISSING_AUDIT_TRAIL", candidate_id, f"audit_trail.{field}", "Audit field is missing.")
    if manual.get("manual_review_status") == "pending" or manual.get("manual_review_required") is True:
        add_warning(warnings, "READING_V1_MANUAL_REVIEW_PENDING", candidate_id, "manual_review_state", "Candidate requires manual review.")
    if level.get("normalized_level_band") in {None, "", "UNKNOWN"}:
        add_warning(warnings, "READING_V1_LEVEL_BAND_UNKNOWN", candidate_id, "level_metadata.normalized_level_band", "Normalized level band is unknown.")
    if not situation.get("situation_context"):
        add_warning(warnings, "READING_V1_SITUATION_CONTEXT_MISSING", candidate_id, "situation_metadata.situation_context", "Situation context is missing.")


def validate_candidate(candidate: dict[str, Any], manifest_ids: set[str]) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    validate_schema_structure(candidate, issues)
    validate_source(candidate, manifest_ids, issues)
    validate_policy(candidate, issues)
    validate_question_answer_evidence(candidate, issues)
    validate_level_skill_and_blocked_outputs(candidate, issues)
    validate_audit_and_warnings(candidate, issues, warnings)
    return issues, warnings


def build_report(candidates: list[dict[str, Any]], schema_path: Path, manifest_path: Path, candidate_path: Path, manifest_ids: set[str]) -> dict[str, Any]:
    all_issues: list[ValidationIssue] = []
    all_warnings: list[ValidationIssue] = []
    pass_count = 0
    fail_count = 0

    for candidate in candidates:
        issues, warnings = validate_candidate(candidate, manifest_ids)
        all_issues.extend(issues)
        all_warnings.extend(warnings)
        if issues:
            fail_count += 1
        else:
            pass_count += 1

    blocked_output_count = sum(1 for issue in all_issues if str(issue.get("code", "")).startswith("READING_V1_") and "OUTPUT" in str(issue.get("field_path", "")).upper())
    status = FAIL if all_issues else PASS_WITH_WARNINGS if all_warnings else PASS
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "validator_id": VALIDATOR_ID,
        "validator_version": VALIDATOR_VERSION,
        "input_candidate_path": str(candidate_path),
        "input_schema_path": str(schema_path),
        "input_manifest_path": str(manifest_path),
        "status": status,
        "summary": {
            "candidate_count": len(candidates),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "warning_count": len(all_warnings),
            "blocked_output_count": blocked_output_count,
            "learner_facing_output_created": False,
            "learner_state_updated": False,
            "authority_promotion_performed": False,
        },
        "issues": list(all_issues),
        "warnings": list(all_warnings),
        "candidate_count": len(candidates),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "warning_count": len(all_warnings),
        "blocked_output_count": blocked_output_count,
        "next_shortest_step": NEXT_SHORTEST_STEP,
    }


def build_error_report(candidate_path: Path, schema_path: Path, manifest_path: Path, code: str, message: str) -> dict[str, Any]:
    issue = ValidationIssue(code, "high", None, "$", message, True, "Fix input path or JSON before validation.")
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "validator_id": VALIDATOR_ID,
        "validator_version": VALIDATOR_VERSION,
        "input_candidate_path": str(candidate_path),
        "input_schema_path": str(schema_path),
        "input_manifest_path": str(manifest_path),
        "status": FAIL,
        "summary": {"candidate_count": 0, "pass_count": 0, "fail_count": 0, "warning_count": 0, "blocked_output_count": 0},
        "issues": [issue],
        "warnings": [],
        "candidate_count": 0,
        "pass_count": 0,
        "fail_count": 0,
        "warning_count": 0,
        "blocked_output_count": 0,
        "next_shortest_step": NEXT_SHORTEST_STEP,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Reading V1 candidate JSON artifacts.")
    parser.add_argument("--candidate-path", default="ulga/reports/reading_v1_pilot_candidates.json")
    parser.add_argument("--schema-path", default="ulga/schemas/reading_v1_candidate.schema.json")
    parser.add_argument("--manifest-path", default="ulga/graph/e4s_source_manifest.json")
    parser.add_argument("--output-report", default="ulga/reports/reading_v1_validation_report.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    candidate_path = Path(args.candidate_path)
    schema_path = Path(args.schema_path)
    manifest_path = Path(args.manifest_path)
    output_report = Path(args.output_report)

    try:
        candidates = load_candidates(candidate_path)
        _ = load_json(schema_path)
        manifest_ids = load_manifest_ids(manifest_path)
        report = build_report(candidates, schema_path, manifest_path, candidate_path, manifest_ids)
    except FileNotFoundError as exc:
        report = build_error_report(candidate_path, schema_path, manifest_path, "READING_V1_INPUT_MISSING", str(exc))
    except (json.JSONDecodeError, ValueError) as exc:
        report = build_error_report(candidate_path, schema_path, manifest_path, "READING_V1_SCHEMA_INVALID", str(exc))

    write_json(output_report, report)
    return 0 if report["status"] in {PASS, PASS_WITH_WARNINGS} else 1


if __name__ == "__main__":
    sys.exit(main())
