#!/usr/bin/env python3
"""Build S5A RAZ ReadingAuthorityBridge candidates from S4B review candidates.

S5A contract:
- Read local S4A/S4B page-passage review candidate artifacts under raz_output_jsons/review.
- Do not mutate raw corpus, derived corpus, linkage view, or review candidate artifacts.
- Do not promote authority records.
- Do not create learner-facing content.
- Do not create LearningOpportunityBinding or AssessmentAuthority.
- Emit local-only bridge candidate artifacts under raz_output_jsons/bridge/reading_authority.
- Emit a sanitized aggregate summary under reports/raz.
- Do not write sentence/page text or full bridge records into the sanitized summary.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
INPUT_REVIEW_SCHEMA_VERSION = "raz_page_passage_review_contract.v1"
OUTPUT_BRIDGE_SCHEMA_VERSION = "raz_reading_authority_bridge_contract.v1"
SUMMARY_REPORT_NAME = "raz_reading_authority_bridge_summary.json"
REVIEW_CANDIDATE_SUFFIX = "page_passage_review_candidates"
BRIDGE_CANDIDATE_SUFFIX = "reading_authority_bridge_candidates"
CANONICAL_SOURCE_KIND = "normalized_page_units"
CANONICAL_SOURCE_SUFFIX = f"::{CANONICAL_SOURCE_KIND}"
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
ALLOWED_AUTHORITY_TARGETS = ["ReadingAuthority", "ContentQueryLayer"]
BLOCKED_AUTHORITY_TARGETS = [
    "LearningOpportunityBinding",
    "AssessmentAuthority",
    "DialogueAuthority",
    "WritingAuthority",
    "ExerciseAuthority",
    "SentenceAuthority",
]


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


def review_file(review_root: Path, level: str) -> Path:
    return review_root / f"Level_{level}" / f"raz_{level}_{REVIEW_CANDIDATE_SUFFIX}.json"


def bridge_file(bridge_root: Path, level: str) -> Path:
    return bridge_root / f"Level_{level}" / f"raz_{level}_{BRIDGE_CANDIDATE_SUFFIX}.json"


def collect_review_files(review_root: Path) -> List[Tuple[str, Path]]:
    result: List[Tuple[str, Path]] = []
    for level in EXPECTED_LEVELS:
        path = review_file(review_root, level)
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


def trace(candidate: Dict[str, Any]) -> Dict[str, Any]:
    value = candidate.get("source_traceability")
    return value if isinstance(value, dict) else {}


def precheck(candidate: Dict[str, Any], level: str) -> Dict[str, bool]:
    source_trace = trace(candidate)
    allowed_bridge = set(list_of_strings(candidate.get("allowed_bridge_targets")))
    blocked_bridge = set(list_of_strings(candidate.get("blocked_bridge_targets")))
    source_uid = candidate.get("source_linkage_uid")
    checks = {
        "review_candidate_uid_present": isinstance(candidate.get("review_candidate_uid"), str) and bool(candidate.get("review_candidate_uid")),
        "source_linkage_uid_canonical": isinstance(source_uid, str) and source_uid.endswith(CANONICAL_SOURCE_SUFFIX),
        "unit_type_is_page_unit": candidate.get("unit_type") == "page_unit",
        "canonical_source_kind_valid": candidate.get("canonical_source_kind") == CANONICAL_SOURCE_KIND,
        "level_consistent": candidate.get("level") == level and source_trace.get("source_level") == level,
        "book_uid_consistent": isinstance(candidate.get("book_uid"), str) and candidate.get("book_uid") == source_trace.get("source_book_uid"),
        "book_id_consistent": isinstance(candidate.get("book_id"), str) and candidate.get("book_id") == source_trace.get("source_book_id"),
        "page_number_present_and_consistent": isinstance(candidate.get("page_number"), int) and candidate.get("page_number") == source_trace.get("source_page_number"),
        "source_traceability_present": isinstance(candidate.get("source_traceability"), dict),
        "source_type_is_raz": source_trace.get("source_type") == "raz",
        "source_page_unit_id_present": isinstance(source_trace.get("source_page_unit_id"), str) and bool(source_trace.get("source_page_unit_id")),
        "source_sentence_candidate_ids_non_empty": bool(list_of_strings(source_trace.get("source_sentence_candidate_ids"))),
        "trace_generated_content_false": source_trace.get("generated_content") is False,
        "trace_derived_from_original_text_true": source_trace.get("derived_from_original_text") is True,
        "review_state_ready_for_review": candidate.get("review_state") == "ready_for_review",
        "review_status_pending": candidate.get("review_status") == "pending",
        "promotion_status_blocked": candidate.get("promotion_status") == "promotion_blocked",
        "authority_status_candidate_only": candidate.get("authority_status") == "candidate_only",
        "contains_text_values_false": candidate.get("contains_text_values") is False,
        "learning_opportunity_binding_blocked": "LearningOpportunityBinding" in blocked_bridge,
        "assessment_authority_blocked": "AssessmentAuthority" in blocked_bridge,
        "bridge_target_allow_block_no_conflict": not allowed_bridge.intersection(blocked_bridge),
    }
    return checks


def build_bridge_candidate(candidate: Dict[str, Any], level: str, checks: Dict[str, bool]) -> Optional[Dict[str, Any]]:
    if not all(checks.values()):
        return None
    review_uid = candidate.get("review_candidate_uid")
    source_uid = candidate.get("source_linkage_uid")
    if not isinstance(review_uid, str) or not isinstance(source_uid, str):
        return None
    source_trace = trace(candidate)
    bridge_uid_base = review_uid.replace("::page_passage_review_v1", "")
    bridge_candidate = {
        "bridge_candidate_uid": f"{bridge_uid_base}::reading_authority_bridge_v1",
        "source_review_candidate_uid": review_uid,
        "source_linkage_uid": source_uid,
        "bridge_type": "ReadingAuthorityBridge",
        "unit_type": "page_unit",
        "canonical_source_kind": CANONICAL_SOURCE_KIND,
        "level": level,
        "book_uid": candidate.get("book_uid"),
        "book_id": candidate.get("book_id"),
        "page_number": candidate.get("page_number"),
        "source_traceability": source_trace,
        "authority_status": "candidate_only",
        "promotion_status": "promotion_blocked",
        "bridge_status": "bridge_candidate",
        "review_state": candidate.get("review_state"),
        "review_status": candidate.get("review_status"),
        "required_review_before_promotion": "reading_authority_review",
        "allowed_authority_targets": ALLOWED_AUTHORITY_TARGETS,
        "blocked_authority_targets": BLOCKED_AUTHORITY_TARGETS,
        "bridge_checks": checks,
        "bridge_decision": None,
        "contains_text_values": False,
        "content_hash": candidate.get("content_hash"),
        "clean_text_hash": candidate.get("clean_text_hash"),
    }
    return bridge_candidate


def validate_bridge_safety(bridge_candidate: Dict[str, Any], level: str, issues: Counter, samples: List[Dict[str, str]]) -> None:
    uid = bridge_candidate.get("bridge_candidate_uid") if isinstance(bridge_candidate.get("bridge_candidate_uid"), str) else "UNKNOWN"
    if bridge_candidate.get("bridge_type") != "ReadingAuthorityBridge":
        issues["RAZ_READING_BRIDGE_TYPE_INVALID"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_READING_BRIDGE_TYPE_INVALID", field="bridge_type")
    if bridge_candidate.get("authority_status") != "candidate_only":
        issues["RAZ_READING_BRIDGE_AUTHORITY_STATUS_NOT_CANDIDATE_ONLY"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_READING_BRIDGE_AUTHORITY_STATUS_NOT_CANDIDATE_ONLY", field="authority_status")
    if bridge_candidate.get("promotion_status") != "promotion_blocked":
        issues["RAZ_READING_BRIDGE_PROMOTION_STATUS_NOT_BLOCKED"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_READING_BRIDGE_PROMOTION_STATUS_NOT_BLOCKED", field="promotion_status")
    if bridge_candidate.get("bridge_status") != "bridge_candidate":
        issues["RAZ_READING_BRIDGE_STATUS_INVALID"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_READING_BRIDGE_STATUS_INVALID", field="bridge_status")
    if bridge_candidate.get("review_state") != "ready_for_review":
        issues["RAZ_READING_BRIDGE_REVIEW_STATE_NOT_READY"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_READING_BRIDGE_REVIEW_STATE_NOT_READY", field="review_state")
    if bridge_candidate.get("review_status") != "pending":
        issues["RAZ_READING_BRIDGE_REVIEW_STATUS_NOT_PENDING"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_READING_BRIDGE_REVIEW_STATUS_NOT_PENDING", field="review_status")
    if bridge_candidate.get("contains_text_values") is not False:
        issues["RAZ_READING_BRIDGE_TEXT_FLAG_NOT_FALSE"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_READING_BRIDGE_TEXT_FLAG_NOT_FALSE", field="contains_text_values")
    allowed = set(list_of_strings(bridge_candidate.get("allowed_authority_targets")))
    blocked = set(list_of_strings(bridge_candidate.get("blocked_authority_targets")))
    if allowed != set(ALLOWED_AUTHORITY_TARGETS):
        issues["RAZ_READING_BRIDGE_ALLOWED_TARGETS_INVALID"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_READING_BRIDGE_ALLOWED_TARGETS_INVALID", field="allowed_authority_targets")
    if not set(BLOCKED_AUTHORITY_TARGETS).issubset(blocked):
        issues["RAZ_READING_BRIDGE_BLOCKED_TARGETS_INCOMPLETE"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_READING_BRIDGE_BLOCKED_TARGETS_INCOMPLETE", field="blocked_authority_targets")
    if allowed.intersection(blocked):
        issues["RAZ_READING_BRIDGE_TARGET_ALLOW_BLOCK_CONFLICT"] += 1
        add_sample(samples, level=level, uid=uid, issue_code="RAZ_READING_BRIDGE_TARGET_ALLOW_BLOCK_CONFLICT", field="allowed_authority_targets")


def counter_update_from_checks(counter: Counter, checks: Dict[str, bool]) -> None:
    for key, value in checks.items():
        counter[f"{key}:{'pass' if value else 'fail'}"] += 1


def build(review_root: Path, bridge_root: Path, reports_dir: Path) -> Dict[str, Any]:
    files = collect_review_files(review_root)
    parse_failures: List[Dict[str, str]] = []
    warnings: List[str] = []
    blockers: List[str] = []
    samples: List[Dict[str, str]] = []
    issues: Counter = Counter()
    precheck_counts: Counter = Counter()
    bridge_status_counts: Counter = Counter()
    authority_status_counts: Counter = Counter()
    promotion_status_counts: Counter = Counter()
    review_status_counts: Counter = Counter()
    canonical_source_kind_counts: Counter = Counter()
    unit_type_counts: Counter = Counter()
    level_counts: Dict[str, Dict[str, int]] = {}
    files_read_count = 0
    review_candidates_read_count = 0
    bridge_candidates_emitted_count = 0

    if not review_root.exists() or not review_root.is_dir():
        blockers.append("review_root_missing_or_not_directory")
    if not files:
        blockers.append("review_candidate_files_missing")

    for level, path in files:
        files_read_count += 1
        try:
            payload = read_json(path)
        except Exception as exc:
            parse_failures.append({"level": level, "file": path.name, "error_type": type(exc).__name__})
            continue
        if payload.get("schema_version") != INPUT_REVIEW_SCHEMA_VERSION:
            issues["RAZ_READING_BRIDGE_INPUT_SCHEMA_VERSION_INVALID"] += 1
            add_sample(samples, level=level, uid=f"FILE:{path.name}", issue_code="RAZ_READING_BRIDGE_INPUT_SCHEMA_VERSION_INVALID", field="schema_version")
            continue
        review_records = payload.get("records")
        if not isinstance(review_records, list):
            issues["RAZ_READING_BRIDGE_INPUT_RECORDS_NOT_LIST"] += 1
            add_sample(samples, level=level, uid=f"FILE:{path.name}", issue_code="RAZ_READING_BRIDGE_INPUT_RECORDS_NOT_LIST", field="records")
            continue
        bridge_records: List[Dict[str, Any]] = []
        level_review_read = 0
        level_bridge_emitted = 0
        level_precheck_failed = 0
        for candidate in review_records:
            if not isinstance(candidate, dict):
                issues["RAZ_READING_BRIDGE_INPUT_RECORD_NOT_OBJECT"] += 1
                add_sample(samples, level=level, uid="UNKNOWN", issue_code="RAZ_READING_BRIDGE_INPUT_RECORD_NOT_OBJECT")
                continue
            level_review_read += 1
            review_candidates_read_count += 1
            checks = precheck(candidate, level)
            counter_update_from_checks(precheck_counts, checks)
            if not all(checks.values()):
                level_precheck_failed += 1
                source_uid = candidate.get("review_candidate_uid") if isinstance(candidate.get("review_candidate_uid"), str) else "UNKNOWN"
                add_sample(samples, level=level, uid=source_uid, issue_code="RAZ_READING_BRIDGE_PRECHECK_FAILED")
                continue
            bridge_candidate = build_bridge_candidate(candidate, level, checks)
            if bridge_candidate is None:
                issues["RAZ_READING_BRIDGE_CANDIDATE_BUILD_FAILED"] += 1
                source_uid = candidate.get("review_candidate_uid") if isinstance(candidate.get("review_candidate_uid"), str) else "UNKNOWN"
                add_sample(samples, level=level, uid=source_uid, issue_code="RAZ_READING_BRIDGE_CANDIDATE_BUILD_FAILED")
                continue
            validate_bridge_safety(bridge_candidate, level, issues, samples)
            bridge_records.append(bridge_candidate)
            bridge_candidates_emitted_count += 1
            level_bridge_emitted += 1
            bridge_status_counts[str(bridge_candidate.get("bridge_status"))] += 1
            authority_status_counts[str(bridge_candidate.get("authority_status"))] += 1
            promotion_status_counts[str(bridge_candidate.get("promotion_status"))] += 1
            review_status_counts[str(bridge_candidate.get("review_status"))] += 1
            canonical_source_kind_counts[str(bridge_candidate.get("canonical_source_kind"))] += 1
            unit_type_counts[str(bridge_candidate.get("unit_type"))] += 1
        if bridge_records:
            write_json(bridge_file(bridge_root, level), {"schema_version": OUTPUT_BRIDGE_SCHEMA_VERSION, "records": bridge_records})
        level_counts[level] = {
            "review_candidates_read": level_review_read,
            "bridge_candidates_emitted": level_bridge_emitted,
            "bridge_precheck_failed": level_precheck_failed,
        }

    if parse_failures:
        blockers.append("review_candidate_parse_failures")
    if bridge_candidates_emitted_count == 0:
        blockers.append("no_reading_authority_bridge_candidates_emitted")
    if any(count for key, count in precheck_counts.items() if key.endswith(":fail")):
        blockers.append("reading_authority_bridge_precheck_failures")
    if issues:
        blockers.append("reading_authority_bridge_contract_violations")

    status = "READING_AUTHORITY_BRIDGE_PRECHECK_PASS" if not blockers else "READING_AUTHORITY_BRIDGE_PRECHECK_BLOCKED"
    summary = {
        "task_id": "RAZ-AW-S5A_ReadingAuthorityBridge_Implementation",
        "report_type": "raz_reading_authority_bridge_summary",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "raw_mutation": False,
        "derived_mutation": False,
        "linkage_mutation": False,
        "review_artifact_mutation": False,
        "bridge_artifact_created": True,
        "authority_promotion": False,
        "learner_facing_content_enabled": False,
        "LearningOpportunityBinding_created": False,
        "AssessmentAuthority_created": False,
        "input_review_root": str(review_root),
        "output_bridge_root": str(bridge_root),
        "files_read_count": files_read_count,
        "review_candidates_read_count": review_candidates_read_count,
        "bridge_candidates_emitted_count": bridge_candidates_emitted_count,
        "input_review_schema_version": INPUT_REVIEW_SCHEMA_VERSION,
        "output_bridge_schema_version": OUTPUT_BRIDGE_SCHEMA_VERSION,
        "canonical_source_kind": CANONICAL_SOURCE_KIND,
        "level_counts": level_counts,
        "bridge_status_counts": dict(sorted(bridge_status_counts.items())),
        "authority_status_counts": dict(sorted(authority_status_counts.items())),
        "promotion_status_counts": dict(sorted(promotion_status_counts.items())),
        "review_status_counts": dict(sorted(review_status_counts.items())),
        "canonical_source_kind_counts": dict(sorted(canonical_source_kind_counts.items())),
        "unit_type_counts": dict(sorted(unit_type_counts.items())),
        "precheck_counts": dict(sorted(precheck_counts.items())),
        "issue_counts": dict(sorted(issues.items())),
        "parse_failure_count": len(parse_failures),
        "parse_failures_sample": parse_failures[:20],
        "sample_issues": samples,
        "warnings": sorted(set(warnings)),
        "blockers": sorted(set(blockers)),
        "bridge_interpretation": {
            "bridge_candidates_are_reading_authority": False,
            "bridge_candidates_are_learner_facing": False,
            "promotion_required_future_task": True,
            "qa_required_future_task": "RAZ-AW-S5B_ReadingAuthorityBridge_QA",
        },
        "safety_assertions": [
            "S5A consumes S4B page-unit review candidates only",
            "bridge candidates use canonical_source_kind=normalized_page_units",
            "bridge candidates remain candidate_only",
            "bridge candidates remain promotion_blocked",
            "bridge candidates are not learner-facing",
            "LearningOpportunityBinding is not created",
            "AssessmentAuthority is not created",
            "raw corpus is not modified",
            "derived corpus is not modified",
            "linkage view is not modified",
            "review artifacts are not modified",
            "sanitized summary contains no records or text values",
        ],
    }
    hits = scan_forbidden_keys(summary)
    if hits:
        raise ValueError(f"unsafe_summary_key_emitted:{hits[:5]}")
    write_json(reports_dir / SUMMARY_REPORT_NAME, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build RAZ ReadingAuthorityBridge candidates from S4B page-unit review candidates.")
    parser.add_argument("--review-root", default="raz_output_jsons/review", help="Local review root containing Level_*/raz_*_page_passage_review_candidates.json files.")
    parser.add_argument("--bridge-root", default="raz_output_jsons/bridge/reading_authority", help="Local-only ReadingAuthorityBridge artifact output root.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Sanitized summary output directory.")
    args = parser.parse_args()
    summary = build(Path(args.review_root).resolve(), Path(args.bridge_root).resolve(), Path(args.reports_dir).resolve())
    print(json.dumps({
        "status": summary["status"],
        "files_read_count": summary["files_read_count"],
        "review_candidates_read_count": summary["review_candidates_read_count"],
        "bridge_candidates_emitted_count": summary["bridge_candidates_emitted_count"],
        "bridge_status_counts": summary["bridge_status_counts"],
        "canonical_source_kind_counts": summary["canonical_source_kind_counts"],
        "promotion_status_counts": summary["promotion_status_counts"],
        "authority_status_counts": summary["authority_status_counts"],
        "issue_counts": summary["issue_counts"],
        "warnings": summary["warnings"],
        "blockers": summary["blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "READING_AUTHORITY_BRIDGE_PRECHECK_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
