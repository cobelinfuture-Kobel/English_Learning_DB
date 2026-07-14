#!/usr/bin/env python3
"""Validate local private Reading candidates against their metadata-only safe report."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_local_reading_practice_bank import (
    EXPECTED_ORDERING_COUNT,
    EXPECTED_SOURCE_COUNT,
    FORBIDDEN_SAFE_KEYS,
    PRIVATE_SCHEMA,
    SAFE_REPORT_SCHEMA,
    TASK_ID,
)

ALLOWED_GRAMMAR_STATUSES = {
    "UNIQUE_CANONICAL_MATCH_CANDIDATE",
    "MULTIPLE_CANONICAL_MATCHES_REVIEW_REQUIRED",
    "NO_CANONICAL_MATCH_REVIEW_REQUIRED",
}
FALSE_CLAIMS = {
    "reading_v1_complete",
    "items_promoted",
    "learner_evidence_created",
    "mastery_claimed",
    "retention_confirmed",
    "persistent_learner_state_write",
    "production_runtime_event",
    "a2_a2plus_in_scope",
}


def _scan_forbidden(value: Any, errors: list[str], path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in FORBIDDEN_SAFE_KEYS:
                errors.append(f"safe_report_forbidden_text_key:{path}.{key}")
            _scan_forbidden(child, errors, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_forbidden(child, errors, f"{path}[{index}]")


def validate_materialization(
    private_output: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    *,
    require_full_selection: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    if private_output.get("task_id") != TASK_ID or safe_report.get("task_id") != TASK_ID:
        errors.append("task_id_mismatch")
    if private_output.get("schema_version") != PRIVATE_SCHEMA:
        errors.append("private_schema_mismatch")
    if safe_report.get("schema_version") != SAFE_REPORT_SCHEMA:
        errors.append("safe_report_schema_mismatch")
    policy = private_output.get("policy", {})
    for key in ("private_local_only", "must_not_be_committed", "not_for_public_export", "operator_review_required"):
        if policy.get(key) is not True:
            errors.append(f"private_policy_not_true:{key}")
    if policy.get("authority_status") != "candidate_only":
        errors.append("private_authority_status_invalid")
    if policy.get("promotion_status") != "not_promoted":
        errors.append("private_promotion_status_invalid")

    for owner, boundaries in (
        ("private", private_output.get("claim_boundaries", {})),
        ("safe", safe_report.get("claim_boundaries", {})),
    ):
        for key in FALSE_CLAIMS:
            if boundaries.get(key) is not False:
                errors.append(f"{owner}_false_claim_invalid:{key}")
    safe_boundaries = safe_report.get("claim_boundaries", {})
    if safe_boundaries.get("metadata_and_hashes_only") is not True:
        errors.append("safe_report_metadata_only_missing")
    for key in (
        "raw_source_text_included",
        "full_passage_text_included",
        "sentence_text_included",
        "source_payload_copied",
    ):
        if safe_boundaries.get(key) is not False:
            errors.append(f"safe_report_payload_boundary_invalid:{key}")

    private_records = private_output.get("records")
    safe_records = safe_report.get("records")
    if not isinstance(private_records, list):
        errors.append("private_records_not_list")
        private_records = []
    if not isinstance(safe_records, list):
        errors.append("safe_records_not_list")
        safe_records = []
    if len(private_records) != len(safe_records):
        errors.append("private_safe_record_count_mismatch")
    if require_full_selection and len(safe_records) != EXPECTED_SOURCE_COUNT:
        errors.append(f"safe_record_count_not_{EXPECTED_SOURCE_COUNT}")

    private_by_id: dict[str, Mapping[str, Any]] = {}
    for index, record in enumerate(private_records):
        selection = record.get("selection") if isinstance(record, Mapping) else None
        selection_id = selection.get("selection_id") if isinstance(selection, Mapping) else None
        if not isinstance(selection_id, str) or not selection_id:
            errors.append(f"private:{index}:selection_id_missing")
            continue
        if selection_id in private_by_id:
            errors.append(f"private:{index}:duplicate_selection_id")
        private_by_id[selection_id] = record
        if not isinstance(record.get("source_text"), str) or not record.get("source_text", "").strip():
            errors.append(f"private:{selection_id}:source_text_missing")
        sentences = record.get("source_sentences")
        if not isinstance(sentences, list) or not sentences:
            errors.append(f"private:{selection_id}:source_sentences_missing")
        integrity = record.get("source_integrity", {})
        if integrity.get("status") != "PASS" or integrity.get("errors") != []:
            errors.append(f"private:{selection_id}:source_integrity_failed")
        grammar = record.get("grammar_analysis", {})
        if grammar.get("binding_status") not in ALLOWED_GRAMMAR_STATUSES:
            errors.append(f"private:{selection_id}:grammar_status_invalid")
        if grammar.get("operator_review_required") is not True:
            errors.append(f"private:{selection_id}:grammar_review_boundary_missing")
        items = record.get("deterministic_items")
        if not isinstance(items, list):
            errors.append(f"private:{selection_id}:items_not_list")
            items = []
        types = {item.get("question_type") for item in items if isinstance(item, Mapping)}
        if not {"true_false", "cloze_vocabulary"} <= types:
            errors.append(f"private:{selection_id}:required_deterministic_items_missing")
        for item in items:
            if not isinstance(item, Mapping):
                errors.append(f"private:{selection_id}:item_not_object")
                continue
            if item.get("status") != "PRIVATE_REVIEW_CANDIDATE":
                errors.append(f"private:{selection_id}:item_status_invalid")
            if item.get("deterministic_scoring_ready") is not True:
                errors.append(f"private:{selection_id}:deterministic_scoring_not_ready")
        literal = record.get("literal_review_candidates")
        if not isinstance(literal, list):
            errors.append(f"private:{selection_id}:literal_candidates_not_list")
            literal = []
        for candidate in literal:
            if candidate.get("status") != "PENDING_OPERATOR_QUESTION_AND_ANSWER_REVIEW":
                errors.append(f"private:{selection_id}:literal_status_invalid")
            if candidate.get("auto_answer_generated") is not False:
                errors.append(f"private:{selection_id}:literal_auto_answer_not_false")

    safe_ids: set[str] = set()
    for index, record in enumerate(safe_records):
        if not isinstance(record, Mapping):
            errors.append(f"safe:{index}:record_not_object")
            continue
        selection_id = record.get("selection_id")
        if not isinstance(selection_id, str) or not selection_id:
            errors.append(f"safe:{index}:selection_id_missing")
            continue
        if selection_id in safe_ids:
            errors.append(f"safe:{selection_id}:duplicate_selection_id")
        safe_ids.add(selection_id)
        if selection_id not in private_by_id:
            errors.append(f"safe:{selection_id}:private_record_missing")
        if record.get("source_integrity_status") != "PASS" or record.get("source_integrity_errors") != []:
            errors.append(f"safe:{selection_id}:source_integrity_failed")
        if record.get("grammar_binding_status") not in ALLOWED_GRAMMAR_STATUSES:
            errors.append(f"safe:{selection_id}:grammar_status_invalid")
        if record.get("operator_review_required") is not True:
            errors.append(f"safe:{selection_id}:operator_review_boundary_missing")
        item_types = record.get("deterministic_item_types", {})
        if item_types.get("true_false") != 1 or item_types.get("cloze_vocabulary") != 1:
            errors.append(f"safe:{selection_id}:required_item_accounting_invalid")

    if private_output.get("summary") != safe_report.get("summary"):
        errors.append("private_safe_summary_mismatch")
    summary = safe_report.get("summary", {})
    if summary.get("selected_source_count") != len(safe_records):
        errors.append("summary_selected_source_count_mismatch")
    if summary.get("source_integrity_pass_count") != len(safe_records):
        errors.append("summary_integrity_count_mismatch")
    deterministic = summary.get("deterministic_item_counts", {})
    if deterministic.get("true_false") != len(safe_records):
        errors.append("summary_true_false_count_mismatch")
    if deterministic.get("cloze_vocabulary") != len(safe_records):
        errors.append("summary_cloze_count_mismatch")
    if require_full_selection and deterministic.get("sentence_ordering") != EXPECTED_ORDERING_COUNT:
        errors.append(f"summary_sentence_ordering_count_not_{EXPECTED_ORDERING_COUNT}")

    if safe_report.get("validation_status") != "PASS_LOCAL_READING_BINDING_EXECUTED":
        errors.append("safe_report_execution_not_pass")
    if safe_report.get("error_count") != 0 or safe_report.get("errors") != []:
        errors.append("safe_report_contains_execution_errors")
    if safe_report.get("m04b2_local_binding_execution_complete") is not True:
        errors.append("m04b2_execution_not_complete")
    if safe_report.get("m04b3_operator_review_complete") is not False:
        errors.append("m04b3_review_false_boundary_missing")
    if safe_report.get("next_resume_task") != "E4S-A1V1-M04B3_SourceGroundedReadingCandidateReviewAndPromotion":
        errors.append("next_resume_task_invalid")

    _scan_forbidden(safe_report, errors)
    return {
        "task_id": TASK_ID,
        "validation_status": "PASS_LOCAL_READING_PRACTICE_BANK" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "selected_source_count": len(safe_records),
        "m04b2_complete": not errors,
        "m04b3_operator_review_complete": False,
        "reading_v1_complete": False,
        "next_resume_task": "E4S-A1V1-M04B3_SourceGroundedReadingCandidateReviewAndPromotion",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-input", type=Path, required=True)
    parser.add_argument("--safe-report", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path)
    args = parser.parse_args(argv)
    private_output = json.loads(args.private_input.read_text(encoding="utf-8"))
    safe_report = json.loads(args.safe_report.read_text(encoding="utf-8"))
    report = validate_materialization(private_output, safe_report)
    if args.validation_report:
        args.validation_report.parent.mkdir(parents=True, exist_ok=True)
        args.validation_report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == "PASS_LOCAL_READING_PRACTICE_BANK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
