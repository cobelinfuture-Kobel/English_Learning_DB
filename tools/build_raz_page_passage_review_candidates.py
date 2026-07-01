#!/usr/bin/env python3
"""Build S4A RAZ page/passage review candidates from the S3J linkage view.

S4A contract:
- Read local authority-linkage view artifacts under raz_output_jsons/linkage.
- Do not mutate raw corpus, legacy derived corpus, or linkage-view artifacts.
- Do not promote authority records.
- Emit local-only page/passage review candidate artifacts under raz_output_jsons/review.
- Emit a sanitized aggregate summary under reports/raz.
- Do not write sentence/page text into the sanitized summary.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
INPUT_SCHEMA_VERSION = "raz_authority_linkage_contract.v1"
OUTPUT_SCHEMA_VERSION = "raz_page_passage_review_contract.v1"
REPORT_NAME = "raz_page_passage_review_contract_summary.json"
REVIEW_OUTPUT_SUFFIX = "page_passage_review_candidates"
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
ALLOWED_BRIDGE_TARGETS = ["ReadingAuthorityBridge", "ContentQueryLayer"]
BLOCKED_BRIDGE_TARGETS = [
    "LearningOpportunityBinding",
    "AssessmentAuthority",
    "DialogueAuthority",
    "WritingAuthority",
    "ExerciseAuthority",
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


def linkage_file(linkage_root: Path, level: str) -> Path:
    return linkage_root / f"Level_{level}" / f"raz_{level}_authority_linkage_view.json"


def review_file(review_root: Path, level: str) -> Path:
    return review_root / f"Level_{level}" / f"raz_{level}_{REVIEW_OUTPUT_SUFFIX}.json"


def collect_linkage_files(linkage_root: Path) -> List[Tuple[str, Path]]:
    result: List[Tuple[str, Path]] = []
    for level in EXPECTED_LEVELS:
        path = linkage_file(linkage_root, level)
        if path.exists():
            result.append((level, path))
    return result


def list_of_strings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def trace_value(record: Dict[str, Any], key: str) -> Any:
    trace = record.get("source_traceability")
    if isinstance(trace, dict):
        return trace.get(key)
    return None


def page_number(record: Dict[str, Any]) -> Optional[int]:
    value = trace_value(record, "source_page_number")
    if isinstance(value, int):
        return value
    return None


def source_sentence_ids(record: Dict[str, Any]) -> List[str]:
    trace = record.get("source_traceability")
    if not isinstance(trace, dict):
        return []
    return list_of_strings(trace.get("source_sentence_candidate_ids"))


def source_page_unit_id(record: Dict[str, Any]) -> Optional[str]:
    value = trace_value(record, "source_page_unit_id")
    return value if isinstance(value, str) and value else None


def check_preconditions(record: Dict[str, Any], level: str) -> Dict[str, bool]:
    trace = record.get("source_traceability")
    allowed_targets = set(list_of_strings(record.get("allowed_authority_targets")))
    blocked_targets = set(list_of_strings(record.get("blocked_authority_targets")))
    checks = {
        "artifact_layer_is_page_unit": record.get("artifact_layer") == "page_unit",
        "source_traceability_present": isinstance(trace, dict),
        "source_level_present_and_consistent": trace_value(record, "source_level") == level,
        "source_book_uid_present": isinstance(trace_value(record, "source_book_uid"), str) and bool(trace_value(record, "source_book_uid")),
        "source_book_id_present": isinstance(trace_value(record, "source_book_id"), str) and bool(trace_value(record, "source_book_id")),
        "source_page_unit_id_present": source_page_unit_id(record) is not None,
        "source_sentence_candidate_ids_non_empty": bool(source_sentence_ids(record)),
        "page_number_present": page_number(record) is not None,
        "promotion_status_blocked": record.get("promotion_status") == "promotion_blocked",
        "authority_status_candidate_only": record.get("authority_status") == "candidate_only",
        "review_status_pending_family": record.get("review_status") in {"pending", "needs_review", "not_required"},
        "required_review_is_page_unit_review": record.get("required_review_before_promotion") == "page_unit_review",
        "generated_content_false": record.get("generated_content") is False,
        "derived_from_original_text_true": record.get("derived_from_original_text") is True,
        "target_allow_block_no_conflict": not allowed_targets.intersection(blocked_targets),
        "learning_opportunity_binding_blocked": "LearningOpportunityBinding" in blocked_targets,
        "assessment_authority_blocked": "AssessmentAuthority" in blocked_targets,
    }
    return checks


def review_candidate(record: Dict[str, Any], level: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, bool]]:
    checks = check_preconditions(record, level)
    if record.get("artifact_layer") != "page_unit":
        return None, checks
    uid = record.get("record_uid")
    if not isinstance(uid, str) or not uid:
        return None, checks
    trace = record.get("source_traceability") if isinstance(record.get("source_traceability"), dict) else {}
    candidate = {
        "review_candidate_uid": f"{uid}::page_passage_review_v1",
        "source_linkage_uid": uid,
        "unit_type": "page_unit",
        "level": level,
        "book_uid": trace.get("source_book_uid"),
        "book_id": trace.get("source_book_id"),
        "page_number": trace.get("source_page_number"),
        "source_traceability": trace,
        "authority_status": "candidate_only",
        "promotion_status": "promotion_blocked",
        "review_state": "ready_for_review" if all(checks.values()) else "precheck_failed",
        "review_status": "pending",
        "required_review_before_promotion": "page_unit_review",
        "allowed_bridge_targets": ALLOWED_BRIDGE_TARGETS,
        "blocked_bridge_targets": BLOCKED_BRIDGE_TARGETS,
        "review_checks": checks,
        "review_decision": None,
        "reviewer_notes_ref": None,
        "contains_text_values": False,
        "content_hash": record.get("content_hash"),
        "clean_text_hash": record.get("clean_text_hash"),
    }
    return candidate, checks


def update_counter_from_checks(counter: Counter, checks: Dict[str, bool]) -> None:
    for key, passed in checks.items():
        if passed:
            counter[f"{key}:pass"] += 1
        else:
            counter[f"{key}:fail"] += 1


def add_sample(samples: List[Dict[str, str]], *, level: str, source_uid: str, issue_code: str, field: Optional[str] = None) -> None:
    if len(samples) >= 100:
        return
    item = {"level": level, "source_linkage_uid": source_uid, "issue_code": issue_code}
    if field:
        item["field"] = field
    samples.append(item)


def validate_candidate_safety(candidate: Dict[str, Any], level: str, issues: Counter, samples: List[Dict[str, str]]) -> None:
    source_uid = candidate.get("source_linkage_uid") if isinstance(candidate.get("source_linkage_uid"), str) else "UNKNOWN"
    if candidate.get("authority_status") != "candidate_only":
        issues["RAZ_REVIEW_CANDIDATE_AUTHORITY_STATUS_NOT_CANDIDATE_ONLY"] += 1
        add_sample(samples, level=level, source_uid=source_uid, issue_code="RAZ_REVIEW_CANDIDATE_AUTHORITY_STATUS_NOT_CANDIDATE_ONLY", field="authority_status")
    if candidate.get("promotion_status") != "promotion_blocked":
        issues["RAZ_REVIEW_CANDIDATE_PROMOTION_STATUS_NOT_BLOCKED"] += 1
        add_sample(samples, level=level, source_uid=source_uid, issue_code="RAZ_REVIEW_CANDIDATE_PROMOTION_STATUS_NOT_BLOCKED", field="promotion_status")
    if candidate.get("review_state") not in {"ready_for_review", "precheck_failed"}:
        issues["RAZ_REVIEW_CANDIDATE_REVIEW_STATE_INVALID"] += 1
        add_sample(samples, level=level, source_uid=source_uid, issue_code="RAZ_REVIEW_CANDIDATE_REVIEW_STATE_INVALID", field="review_state")
    if candidate.get("contains_text_values") is not False:
        issues["RAZ_REVIEW_CANDIDATE_TEXT_FLAG_NOT_FALSE"] += 1
        add_sample(samples, level=level, source_uid=source_uid, issue_code="RAZ_REVIEW_CANDIDATE_TEXT_FLAG_NOT_FALSE", field="contains_text_values")
    allowed = set(list_of_strings(candidate.get("allowed_bridge_targets")))
    blocked = set(list_of_strings(candidate.get("blocked_bridge_targets")))
    if allowed.intersection(blocked):
        issues["RAZ_REVIEW_CANDIDATE_BRIDGE_TARGET_CONFLICT"] += 1
        add_sample(samples, level=level, source_uid=source_uid, issue_code="RAZ_REVIEW_CANDIDATE_BRIDGE_TARGET_CONFLICT", field="allowed_bridge_targets")
    if "LearningOpportunityBinding" not in blocked:
        issues["RAZ_REVIEW_CANDIDATE_LEARNING_OPPORTUNITY_NOT_BLOCKED"] += 1
        add_sample(samples, level=level, source_uid=source_uid, issue_code="RAZ_REVIEW_CANDIDATE_LEARNING_OPPORTUNITY_NOT_BLOCKED", field="blocked_bridge_targets")
    if "AssessmentAuthority" not in blocked:
        issues["RAZ_REVIEW_CANDIDATE_ASSESSMENT_NOT_BLOCKED"] += 1
        add_sample(samples, level=level, source_uid=source_uid, issue_code="RAZ_REVIEW_CANDIDATE_ASSESSMENT_NOT_BLOCKED", field="blocked_bridge_targets")


def build(linkage_root: Path, review_root: Path, reports_dir: Path) -> Dict[str, Any]:
    files = collect_linkage_files(linkage_root)
    parse_failures: List[Dict[str, str]] = []
    blockers: List[str] = []
    warnings: List[str] = []
    samples: List[Dict[str, str]] = []
    issues: Counter = Counter()
    artifact_layer_counts: Counter = Counter()
    review_state_counts: Counter = Counter()
    level_counts: Dict[str, Dict[str, int]] = {}
    precheck_counts: Counter = Counter()
    skipped_layer_counts: Counter = Counter()
    records_read_count = 0
    candidates_emitted_count = 0

    if not linkage_root.exists() or not linkage_root.is_dir():
        blockers.append("linkage_root_missing_or_not_directory")
    if not files:
        blockers.append("linkage_view_files_missing")

    for level, path in files:
        try:
            payload = read_json(path)
        except Exception as exc:
            parse_failures.append({"level": level, "file": path.name, "error_type": type(exc).__name__})
            continue
        if payload.get("schema_version") != INPUT_SCHEMA_VERSION:
            issues["RAZ_PAGE_PASSAGE_INPUT_SCHEMA_VERSION_INVALID"] += 1
            add_sample(samples, level=level, source_uid=f"FILE:{path.name}", issue_code="RAZ_PAGE_PASSAGE_INPUT_SCHEMA_VERSION_INVALID", field="schema_version")
            continue
        input_records = payload.get("records")
        if not isinstance(input_records, list):
            issues["RAZ_PAGE_PASSAGE_INPUT_RECORDS_NOT_LIST"] += 1
            add_sample(samples, level=level, source_uid=f"FILE:{path.name}", issue_code="RAZ_PAGE_PASSAGE_INPUT_RECORDS_NOT_LIST", field="records")
            continue
        output_candidates: List[Dict[str, Any]] = []
        level_records_read = 0
        level_candidates = 0
        for item in input_records:
            if not isinstance(item, dict):
                issues["RAZ_PAGE_PASSAGE_INPUT_RECORD_NOT_OBJECT"] += 1
                add_sample(samples, level=level, source_uid="UNKNOWN", issue_code="RAZ_PAGE_PASSAGE_INPUT_RECORD_NOT_OBJECT")
                continue
            level_records_read += 1
            records_read_count += 1
            layer = item.get("artifact_layer") if isinstance(item.get("artifact_layer"), str) else "UNKNOWN"
            artifact_layer_counts[layer] += 1
            if layer != "page_unit":
                skipped_layer_counts[layer] += 1
                continue
            candidate, checks = review_candidate(item, level)
            update_counter_from_checks(precheck_counts, checks)
            if candidate is None:
                issues["RAZ_PAGE_PASSAGE_PAGE_UNIT_CANDIDATE_BUILD_FAILED"] += 1
                source_uid = item.get("record_uid") if isinstance(item.get("record_uid"), str) else "UNKNOWN"
                add_sample(samples, level=level, source_uid=source_uid, issue_code="RAZ_PAGE_PASSAGE_PAGE_UNIT_CANDIDATE_BUILD_FAILED")
                continue
            validate_candidate_safety(candidate, level, issues, samples)
            output_candidates.append(candidate)
            level_candidates += 1
            candidates_emitted_count += 1
            review_state_counts[candidate["review_state"]] += 1
        if output_candidates:
            write_json(review_file(review_root, level), {"schema_version": OUTPUT_SCHEMA_VERSION, "records": output_candidates})
        level_counts[level] = {
            "records_read": level_records_read,
            "page_passage_review_candidates_emitted": level_candidates,
        }

    if parse_failures:
        blockers.append("linkage_view_parse_failures")
    if candidates_emitted_count == 0:
        blockers.append("no_page_unit_review_candidates_emitted")
    if review_state_counts.get("precheck_failed", 0):
        blockers.append("page_passage_precheck_failures")
    if issues:
        blockers.append("page_passage_review_contract_violations")

    status = "PAGE_PASSAGE_REVIEW_PRECHECK_PASS" if not blockers else "PAGE_PASSAGE_REVIEW_PRECHECK_BLOCKED"
    summary = {
        "task_id": "RAZ-AW-S4A_PagePassageUnitReviewContract_Implementation",
        "report_type": "raz_page_passage_review_contract_summary",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "raw_mutation": False,
        "derived_mutation": False,
        "linkage_mutation": False,
        "review_artifact_created": True,
        "authority_promotion": False,
        "learner_facing_content_enabled": False,
        "input_linkage_root": str(linkage_root),
        "output_review_root": str(review_root),
        "files_read_count": len(files),
        "records_read_count": records_read_count,
        "review_candidates_emitted_count": candidates_emitted_count,
        "artifact_layer_counts": dict(sorted(artifact_layer_counts.items())),
        "skipped_layer_counts": dict(sorted(skipped_layer_counts.items())),
        "review_state_counts": dict(sorted(review_state_counts.items())),
        "precheck_counts": dict(sorted(precheck_counts.items())),
        "level_counts": level_counts,
        "issue_counts": dict(sorted(issues.items())),
        "parse_failure_count": len(parse_failures),
        "parse_failures_sample": parse_failures[:20],
        "sample_issues": samples,
        "warnings": sorted(set(warnings)),
        "blockers": sorted(set(blockers)),
        "bridge_eligibility": {
            "eligible_now_count": 0,
            "reason": "S4A creates ready_for_review candidates only. Human/QA review and S4B validation are required before PAGE_PASSAGE_REVIEW_BRIDGE_ELIGIBLE.",
        },
        "safety_assertions": [
            "page_unit candidates only",
            "reuse_unit_candidate is skipped by default",
            "passage_unit remains future-contract only",
            "promotion_status remains promotion_blocked",
            "authority_status remains candidate_only",
            "LearningOpportunityBinding remains blocked",
            "AssessmentAuthority remains blocked",
            "no learner-facing content enabled",
            "sanitized summary contains no text values",
        ],
    }
    hits = scan_forbidden_keys(summary)
    if hits:
        raise ValueError(f"unsafe_summary_key_emitted:{hits[:5]}")
    write_json(reports_dir / REPORT_NAME, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build RAZ page/passage review candidates from the S3J linkage view.")
    parser.add_argument("--linkage-root", default="raz_output_jsons/linkage", help="Local linkage root containing Level_*/raz_*_authority_linkage_view.json files.")
    parser.add_argument("--review-root", default="raz_output_jsons/review", help="Local-only review artifact output root.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Sanitized summary output directory.")
    args = parser.parse_args()
    summary = build(Path(args.linkage_root).resolve(), Path(args.review_root).resolve(), Path(args.reports_dir).resolve())
    print(json.dumps({
        "status": summary["status"],
        "files_read_count": summary["files_read_count"],
        "records_read_count": summary["records_read_count"],
        "review_candidates_emitted_count": summary["review_candidates_emitted_count"],
        "review_state_counts": summary["review_state_counts"],
        "issue_counts": summary["issue_counts"],
        "warnings": summary["warnings"],
        "blockers": summary["blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PAGE_PASSAGE_REVIEW_PRECHECK_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
