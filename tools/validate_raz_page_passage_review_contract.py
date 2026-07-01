#!/usr/bin/env python3
"""Validate S4A/S4A1 RAZ page/passage review candidates.

S4B contract:
- Read local review candidate artifacts under raz_output_jsons/review.
- Read sanitized S4A/S4A1 summary under reports/raz.
- Do not mutate raw corpus, derived corpus, linkage view, or review artifacts.
- Do not promote authority records.
- Emit a sanitized QA report under reports/raz.
- Do not write sentence/page text or full candidate records into the QA report.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
REVIEW_SCHEMA_VERSION = "raz_page_passage_review_contract.v1"
CANONICAL_PAGE_UNIT_SOURCE_KIND = "normalized_page_units"
CANONICAL_PAGE_UNIT_SUFFIX = f"::{CANONICAL_PAGE_UNIT_SOURCE_KIND}"
SUMMARY_NAME = "raz_page_passage_review_contract_summary.json"
QA_REPORT_NAME = "raz_page_passage_review_contract_qa.json"
FORBIDDEN_REPORT_KEYS = {
    "text",
    "raw_text",
    "page_text",
    "clean_text",
    "full_raw_json",
    "full_derived_record",
    "sentence_candidates",
    "page_units",
    "reuse_unit_candidates",
    "records",
}
REQUIRED_FIELDS = (
    "review_candidate_uid",
    "source_linkage_uid",
    "unit_type",
    "canonical_source_kind",
    "level",
    "book_uid",
    "book_id",
    "page_number",
    "source_traceability",
    "authority_status",
    "promotion_status",
    "review_state",
    "review_status",
    "required_review_before_promotion",
    "allowed_bridge_targets",
    "blocked_bridge_targets",
    "review_checks",
    "contains_text_values",
)
REQUIRED_TRACE_FIELDS = (
    "source_type",
    "source_level",
    "source_book_id",
    "source_book_uid",
    "source_page_number",
    "source_page_unit_id",
    "source_sentence_candidate_ids",
    "derived_from_original_text",
    "generated_content",
    "trace_confidence",
)
ALLOWED_BRIDGE_TARGETS = {"ReadingAuthorityBridge", "ContentQueryLayer"}
REQUIRED_BLOCKED_BRIDGE_TARGETS = {
    "LearningOpportunityBinding",
    "AssessmentAuthority",
    "DialogueAuthority",
    "WritingAuthority",
    "ExerciseAuthority",
}


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("top_level_json_is_not_object")
    return payload


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scan_forbidden_keys(value: Any, path: str = "$", hits: Optional[List[str]] = None) -> List[str]:
    if hits is None:
        hits = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_REPORT_KEYS:
                hits.append(f"{path}.{key}")
            scan_forbidden_keys(child, f"{path}.{key}", hits)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            scan_forbidden_keys(child, f"{path}[{idx}]", hits)
    return hits


def collect_review_files(review_root: Path) -> List[Tuple[str, Path]]:
    result: List[Tuple[str, Path]] = []
    for level in EXPECTED_LEVELS:
        path = review_root / f"Level_{level}" / f"raz_{level}_page_passage_review_candidates.json"
        if path.exists():
            result.append((level, path))
    return result


def list_of_strings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def add_sample(samples: List[Dict[str, str]], *, level: str, uid: str, issue_code: str, field: Optional[str] = None) -> None:
    if len(samples) >= 100:
        return
    item = {"level": level, "uid": uid, "issue_code": issue_code}
    if field:
        item["field"] = field
    samples.append(item)


def validate_summary(summary: Dict[str, Any], issues: Counter, samples: List[Dict[str, str]]) -> None:
    expected = {
        "status": "PAGE_PASSAGE_REVIEW_PRECHECK_PASS",
        "sanitized": True,
        "contains_text_values": False,
        "raw_mutation": False,
        "derived_mutation": False,
        "linkage_mutation": False,
        "authority_promotion": False,
        "learner_facing_content_enabled": False,
        "canonical_page_unit_source_kind": CANONICAL_PAGE_UNIT_SOURCE_KIND,
    }
    for field, expected_value in expected.items():
        if summary.get(field) != expected_value:
            issues["RAZ_PAGE_PASSAGE_SUMMARY_FIELD_INVALID"] += 1
            add_sample(samples, level="SUMMARY", uid="SUMMARY", issue_code="RAZ_PAGE_PASSAGE_SUMMARY_FIELD_INVALID", field=field)
    if not isinstance(summary.get("review_candidates_emitted_count"), int) or summary.get("review_candidates_emitted_count") <= 0:
        issues["RAZ_PAGE_PASSAGE_SUMMARY_CANDIDATE_COUNT_INVALID"] += 1
        add_sample(samples, level="SUMMARY", uid="SUMMARY", issue_code="RAZ_PAGE_PASSAGE_SUMMARY_CANDIDATE_COUNT_INVALID", field="review_candidates_emitted_count")
    if summary.get("issue_counts") not in ({}, None):
        issues["RAZ_PAGE_PASSAGE_SUMMARY_ISSUES_PRESENT"] += 1
        add_sample(samples, level="SUMMARY", uid="SUMMARY", issue_code="RAZ_PAGE_PASSAGE_SUMMARY_ISSUES_PRESENT", field="issue_counts")
    if summary.get("blockers") not in ([], None):
        issues["RAZ_PAGE_PASSAGE_SUMMARY_BLOCKERS_PRESENT"] += 1
        add_sample(samples, level="SUMMARY", uid="SUMMARY", issue_code="RAZ_PAGE_PASSAGE_SUMMARY_BLOCKERS_PRESENT", field="blockers")


def validate_trace(candidate: Dict[str, Any], *, level: str, uid: str, issues: Counter, samples: List[Dict[str, str]]) -> None:
    trace = candidate.get("source_traceability")
    if not isinstance(trace, dict):
        issues["RAZ_PAGE_PASSAGE_TRACE_MISSING"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_TRACE_MISSING", field="source_traceability")
        return
    for field in REQUIRED_TRACE_FIELDS:
        if field not in trace:
            issues["RAZ_PAGE_PASSAGE_TRACE_FIELD_MISSING"] += 1
            add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_TRACE_FIELD_MISSING", field=f"source_traceability.{field}")
    if trace.get("source_type") != "raz":
        issues["RAZ_PAGE_PASSAGE_TRACE_SOURCE_TYPE_INVALID"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_TRACE_SOURCE_TYPE_INVALID", field="source_traceability.source_type")
    if trace.get("source_level") != level or candidate.get("level") != level:
        issues["RAZ_PAGE_PASSAGE_LEVEL_INCONSISTENT"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_LEVEL_INCONSISTENT", field="level")
    if trace.get("source_book_uid") != candidate.get("book_uid"):
        issues["RAZ_PAGE_PASSAGE_BOOK_UID_INCONSISTENT"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_BOOK_UID_INCONSISTENT", field="book_uid")
    if trace.get("source_book_id") != candidate.get("book_id"):
        issues["RAZ_PAGE_PASSAGE_BOOK_ID_INCONSISTENT"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_BOOK_ID_INCONSISTENT", field="book_id")
    if not isinstance(candidate.get("page_number"), int) or trace.get("source_page_number") != candidate.get("page_number"):
        issues["RAZ_PAGE_PASSAGE_PAGE_NUMBER_INVALID"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_PAGE_NUMBER_INVALID", field="page_number")
    if not isinstance(trace.get("source_page_unit_id"), str) or not trace.get("source_page_unit_id"):
        issues["RAZ_PAGE_PASSAGE_SOURCE_PAGE_UNIT_ID_INVALID"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_SOURCE_PAGE_UNIT_ID_INVALID", field="source_traceability.source_page_unit_id")
    if not list_of_strings(trace.get("source_sentence_candidate_ids")):
        issues["RAZ_PAGE_PASSAGE_SOURCE_SENTENCE_IDS_EMPTY"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_SOURCE_SENTENCE_IDS_EMPTY", field="source_traceability.source_sentence_candidate_ids")
    if trace.get("derived_from_original_text") is not True:
        issues["RAZ_PAGE_PASSAGE_TRACE_DERIVED_FROM_ORIGINAL_TEXT_NOT_TRUE"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_TRACE_DERIVED_FROM_ORIGINAL_TEXT_NOT_TRUE", field="source_traceability.derived_from_original_text")
    if trace.get("generated_content") is not False:
        issues["RAZ_PAGE_PASSAGE_TRACE_GENERATED_CONTENT_NOT_FALSE"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_TRACE_GENERATED_CONTENT_NOT_FALSE", field="source_traceability.generated_content")


def validate_candidate(candidate: Any, *, level: str, issues: Counter, samples: List[Dict[str, str]], counters: Dict[str, Counter], seen_uids: set[str]) -> None:
    if not isinstance(candidate, dict):
        issues["RAZ_PAGE_PASSAGE_CANDIDATE_NOT_OBJECT"] += 1
        add_sample(samples, level=level, uid="UNKNOWN", issue_code="RAZ_PAGE_PASSAGE_CANDIDATE_NOT_OBJECT")
        return
    uid = candidate.get("review_candidate_uid") if isinstance(candidate.get("review_candidate_uid"), str) else "UNKNOWN"
    source_uid = candidate.get("source_linkage_uid") if isinstance(candidate.get("source_linkage_uid"), str) else "UNKNOWN"

    if uid in seen_uids:
        issues["RAZ_PAGE_PASSAGE_DUPLICATE_REVIEW_CANDIDATE_UID"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_DUPLICATE_REVIEW_CANDIDATE_UID", field="review_candidate_uid")
    seen_uids.add(uid)

    for field in REQUIRED_FIELDS:
        if field not in candidate:
            issues["RAZ_PAGE_PASSAGE_REQUIRED_FIELD_MISSING"] += 1
            add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_REQUIRED_FIELD_MISSING", field=field)

    if not uid.endswith("::page_passage_review_v1"):
        issues["RAZ_PAGE_PASSAGE_REVIEW_UID_INVALID"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_REVIEW_UID_INVALID", field="review_candidate_uid")
    if not source_uid.endswith(CANONICAL_PAGE_UNIT_SUFFIX):
        issues["RAZ_PAGE_PASSAGE_SOURCE_LINKAGE_UID_NOT_CANONICAL"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_SOURCE_LINKAGE_UID_NOT_CANONICAL", field="source_linkage_uid")
    if candidate.get("canonical_source_kind") != CANONICAL_PAGE_UNIT_SOURCE_KIND:
        issues["RAZ_PAGE_PASSAGE_CANONICAL_SOURCE_KIND_INVALID"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_CANONICAL_SOURCE_KIND_INVALID", field="canonical_source_kind")
    if candidate.get("unit_type") != "page_unit":
        issues["RAZ_PAGE_PASSAGE_UNIT_TYPE_INVALID"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_UNIT_TYPE_INVALID", field="unit_type")
    if candidate.get("authority_status") != "candidate_only":
        issues["RAZ_PAGE_PASSAGE_AUTHORITY_STATUS_NOT_CANDIDATE_ONLY"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_AUTHORITY_STATUS_NOT_CANDIDATE_ONLY", field="authority_status")
    if candidate.get("promotion_status") != "promotion_blocked":
        issues["RAZ_PAGE_PASSAGE_PROMOTION_STATUS_NOT_BLOCKED"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_PROMOTION_STATUS_NOT_BLOCKED", field="promotion_status")
    if candidate.get("review_state") != "ready_for_review":
        issues["RAZ_PAGE_PASSAGE_REVIEW_STATE_NOT_READY"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_REVIEW_STATE_NOT_READY", field="review_state")
    if candidate.get("review_status") != "pending":
        issues["RAZ_PAGE_PASSAGE_REVIEW_STATUS_NOT_PENDING"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_REVIEW_STATUS_NOT_PENDING", field="review_status")
    if candidate.get("required_review_before_promotion") != "page_unit_review":
        issues["RAZ_PAGE_PASSAGE_REQUIRED_REVIEW_INVALID"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_REQUIRED_REVIEW_INVALID", field="required_review_before_promotion")
    if candidate.get("contains_text_values") is not False:
        issues["RAZ_PAGE_PASSAGE_TEXT_FLAG_NOT_FALSE"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_TEXT_FLAG_NOT_FALSE", field="contains_text_values")

    allowed = set(list_of_strings(candidate.get("allowed_bridge_targets")))
    blocked = set(list_of_strings(candidate.get("blocked_bridge_targets")))
    if allowed != ALLOWED_BRIDGE_TARGETS:
        issues["RAZ_PAGE_PASSAGE_ALLOWED_BRIDGE_TARGETS_INVALID"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_ALLOWED_BRIDGE_TARGETS_INVALID", field="allowed_bridge_targets")
    if not REQUIRED_BLOCKED_BRIDGE_TARGETS.issubset(blocked):
        issues["RAZ_PAGE_PASSAGE_BLOCKED_BRIDGE_TARGETS_INCOMPLETE"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_BLOCKED_BRIDGE_TARGETS_INCOMPLETE", field="blocked_bridge_targets")
    if allowed.intersection(blocked):
        issues["RAZ_PAGE_PASSAGE_BRIDGE_TARGET_CONFLICT"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_BRIDGE_TARGET_CONFLICT", field="allowed_bridge_targets")

    checks = candidate.get("review_checks")
    if not isinstance(checks, dict):
        issues["RAZ_PAGE_PASSAGE_REVIEW_CHECKS_MISSING"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_REVIEW_CHECKS_MISSING", field="review_checks")
    else:
        false_checks = [key for key, value in checks.items() if value is not True]
        if false_checks:
            issues["RAZ_PAGE_PASSAGE_REVIEW_CHECK_FAILED"] += 1
            add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_REVIEW_CHECK_FAILED", field=false_checks[0])
        if checks.get("canonical_source_kind_is_normalized_page_units") is not True:
            issues["RAZ_PAGE_PASSAGE_CANONICAL_CHECK_MISSING_OR_FALSE"] += 1
            add_sample(samples, level=level, uid=uid, issue_code="RAZ_PAGE_PASSAGE_CANONICAL_CHECK_MISSING_OR_FALSE", field="review_checks.canonical_source_kind_is_normalized_page_units")

    validate_trace(candidate, level=level, uid=uid, issues=issues, samples=samples)

    counters["review_state_counts"][str(candidate.get("review_state"))] += 1
    counters["authority_status_counts"][str(candidate.get("authority_status"))] += 1
    counters["promotion_status_counts"][str(candidate.get("promotion_status"))] += 1
    counters["review_status_counts"][str(candidate.get("review_status"))] += 1
    counters["canonical_source_kind_counts"][str(candidate.get("canonical_source_kind"))] += 1
    counters["unit_type_counts"][str(candidate.get("unit_type"))] += 1


def validate(review_root: Path, reports_dir: Path, summary_path: Path) -> Dict[str, Any]:
    issues: Counter = Counter()
    samples: List[Dict[str, str]] = []
    warnings: List[str] = []
    blockers: List[str] = []
    parse_failures: List[Dict[str, str]] = []
    level_counts: Dict[str, Dict[str, int]] = {}
    counters: Dict[str, Counter] = {
        "review_state_counts": Counter(),
        "authority_status_counts": Counter(),
        "promotion_status_counts": Counter(),
        "review_status_counts": Counter(),
        "canonical_source_kind_counts": Counter(),
        "unit_type_counts": Counter(),
    }
    seen_uids: set[str] = set()

    if not review_root.exists() or not review_root.is_dir():
        blockers.append("review_root_missing_or_not_directory")
    files = collect_review_files(review_root)
    if not files:
        blockers.append("review_candidate_files_missing")

    summary: Dict[str, Any] = {}
    if not summary_path.exists():
        blockers.append("s4a_summary_missing")
    else:
        try:
            summary = read_json(summary_path)
            validate_summary(summary, issues, samples)
        except Exception as exc:
            blockers.append("s4a_summary_parse_failure")
            parse_failures.append({"level": "SUMMARY", "file": summary_path.name, "error_type": type(exc).__name__})

    records_scanned_count = 0
    for level, path in files:
        try:
            payload = read_json(path)
        except Exception as exc:
            parse_failures.append({"level": level, "file": path.name, "error_type": type(exc).__name__})
            continue
        if payload.get("schema_version") != REVIEW_SCHEMA_VERSION:
            issues["RAZ_PAGE_PASSAGE_REVIEW_SCHEMA_VERSION_INVALID"] += 1
            add_sample(samples, level=level, uid=f"FILE:{path.name}", issue_code="RAZ_PAGE_PASSAGE_REVIEW_SCHEMA_VERSION_INVALID", field="schema_version")
            continue
        candidate_records = payload.get("records")
        if not isinstance(candidate_records, list):
            issues["RAZ_PAGE_PASSAGE_REVIEW_RECORDS_NOT_LIST"] += 1
            add_sample(samples, level=level, uid=f"FILE:{path.name}", issue_code="RAZ_PAGE_PASSAGE_REVIEW_RECORDS_NOT_LIST", field="records")
            continue
        level_record_count = 0
        for candidate in candidate_records:
            validate_candidate(candidate, level=level, issues=issues, samples=samples, counters=counters, seen_uids=seen_uids)
            level_record_count += 1
            records_scanned_count += 1
        expected_level_count = None
        if isinstance(summary.get("level_counts"), dict) and isinstance(summary["level_counts"].get(level), dict):
            expected_level_count = summary["level_counts"][level].get("page_passage_review_candidates_emitted")
        if isinstance(expected_level_count, int) and expected_level_count != level_record_count:
            issues["RAZ_PAGE_PASSAGE_LEVEL_COUNT_MISMATCH"] += 1
            add_sample(samples, level=level, uid=f"FILE:{path.name}", issue_code="RAZ_PAGE_PASSAGE_LEVEL_COUNT_MISMATCH", field="level_counts")
        level_counts[level] = {"review_candidates_scanned": level_record_count}

    expected_total = summary.get("review_candidates_emitted_count")
    if isinstance(expected_total, int) and expected_total != records_scanned_count:
        issues["RAZ_PAGE_PASSAGE_TOTAL_COUNT_MISMATCH"] += 1
        add_sample(samples, level="SUMMARY", uid="SUMMARY", issue_code="RAZ_PAGE_PASSAGE_TOTAL_COUNT_MISMATCH", field="review_candidates_emitted_count")

    if parse_failures:
        blockers.append("page_passage_review_parse_failures")
    if records_scanned_count == 0:
        blockers.append("no_review_candidates_scanned")
    if issues:
        blockers.append("page_passage_review_contract_qa_violations")

    status = "PAGE_PASSAGE_REVIEW_QA_PASS" if not blockers else "PAGE_PASSAGE_REVIEW_QA_BLOCKED"
    report = {
        "task_id": "RAZ-AW-S4B_PagePassageUnitReviewContract_QA",
        "report_type": "raz_page_passage_review_contract_qa",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "raw_mutation": False,
        "derived_mutation": False,
        "linkage_mutation": False,
        "review_artifact_mutation": False,
        "authority_promotion": False,
        "learner_facing_content_enabled": False,
        "input_review_root": str(review_root),
        "input_summary_path": str(summary_path),
        "files_scanned_count": len(files),
        "review_candidates_scanned_count": records_scanned_count,
        "summary_expected_candidate_count": expected_total if isinstance(expected_total, int) else None,
        "level_counts": level_counts,
        "review_state_counts": dict(sorted(counters["review_state_counts"].items())),
        "authority_status_counts": dict(sorted(counters["authority_status_counts"].items())),
        "promotion_status_counts": dict(sorted(counters["promotion_status_counts"].items())),
        "review_status_counts": dict(sorted(counters["review_status_counts"].items())),
        "canonical_source_kind_counts": dict(sorted(counters["canonical_source_kind_counts"].items())),
        "unit_type_counts": dict(sorted(counters["unit_type_counts"].items())),
        "issue_counts": dict(sorted(issues.items())),
        "parse_failure_count": len(parse_failures),
        "parse_failures_sample": parse_failures[:20],
        "sample_issues": samples,
        "warnings": sorted(set(warnings)),
        "blockers": sorted(set(blockers)),
        "qa_assertions": [
            "review candidate files are present",
            "review candidate schema version is raz_page_passage_review_contract.v1",
            "candidate count matches S4A/S4A1 summary",
            "all candidates are unit_type=page_unit",
            "all candidates use canonical_source_kind=normalized_page_units",
            "all source_linkage_uid values end with ::normalized_page_units",
            "all candidates are ready_for_review",
            "all promotion_status values remain promotion_blocked",
            "all authority_status values remain candidate_only",
            "LearningOpportunityBinding remains blocked",
            "AssessmentAuthority remains blocked",
            "report contains no candidate records or text values",
        ],
    }
    hits = scan_forbidden_keys(report)
    if hits:
        raise ValueError(f"unsafe_qa_report_key_emitted:{hits[:5]}")
    write_json(reports_dir / QA_REPORT_NAME, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate S4A/S4A1 RAZ page/passage review candidates.")
    parser.add_argument("--review-root", default="raz_output_jsons/review", help="Local review root containing Level_*/raz_*_page_passage_review_candidates.json files.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Sanitized QA report output directory.")
    parser.add_argument("--summary", default="reports/raz/raz_page_passage_review_contract_summary.json", help="S4A/S4A1 sanitized summary path.")
    args = parser.parse_args()
    report = validate(Path(args.review_root).resolve(), Path(args.reports_dir).resolve(), Path(args.summary).resolve())
    print(json.dumps({
        "status": report["status"],
        "files_scanned_count": report["files_scanned_count"],
        "review_candidates_scanned_count": report["review_candidates_scanned_count"],
        "summary_expected_candidate_count": report["summary_expected_candidate_count"],
        "review_state_counts": report["review_state_counts"],
        "canonical_source_kind_counts": report["canonical_source_kind_counts"],
        "promotion_status_counts": report["promotion_status_counts"],
        "authority_status_counts": report["authority_status_counts"],
        "issue_counts": report["issue_counts"],
        "warnings": report["warnings"],
        "blockers": report["blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PAGE_PASSAGE_REVIEW_QA_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
