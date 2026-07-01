#!/usr/bin/env python3
"""Validate S3J RAZ authority-linkage view artifacts.

S3K contract:
- Read local linkage-view artifacts under raz_output_jsons/linkage.
- Do not read or emit sentence/page text.
- Do not mutate raw corpus, derived corpus, or linkage artifacts.
- Confirm all linkage-view records remain promotion-blocked.
- Emit a sanitized QA report under reports/raz.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
SCHEMA_VERSION = "raz_authority_linkage_contract.v1"
REPORT_NAME = "raz_authority_linkage_view_validation.json"
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
REQUIRED_RECORD_FIELDS = (
    "record_uid",
    "artifact_layer",
    "source_traceability",
    "authority_status",
    "promotion_status",
    "review_status",
    "required_review_before_promotion",
    "allowed_authority_targets",
    "blocked_authority_targets",
    "generated_content",
    "derived_from_original_text",
    "trace_confidence",
)
REQUIRED_TRACE_FIELDS = (
    "source_type",
    "source_level",
    "source_book_id",
    "source_book_uid",
    "derived_from_original_text",
    "generated_content",
    "trace_confidence",
)
ALLOWED_ARTIFACT_LAYERS = {
    "raw_source_reference",
    "sentence_candidate",
    "sentence_normalized",
    "sentence_enriched",
    "sentence_final_candidate",
    "page_unit",
    "passage_unit",
    "reuse_unit_candidate",
    "derived_dialogue_candidate",
    "writing_model_seed",
    "exercise_seed",
    "assessment_seed",
    "summary_report",
    "validation_report",
    "bridge_candidate",
    "formal_authority_record",
}
ALLOWED_AUTHORITY_STATUS = {
    "raw_reference",
    "candidate_only",
    "validated_candidate",
    "reviewed_candidate",
    "promoted_authority",
    "rejected",
    "deprecated",
}
ALLOWED_REVIEW_STATUS = {
    "not_required",
    "pending",
    "in_review",
    "passed",
    "failed",
    "needs_revision",
    "needs_review",
    "rejected",
}
ALLOWED_REQUIRED_REVIEW = {
    "none",
    "sentence_validation",
    "page_unit_review",
    "reading_authority_review",
    "dialogue_rewrite_review",
    "writing_template_review",
    "exercise_schema_review",
    "assessment_contract_review",
    "human_review_required",
}
ALLOWED_TARGETS = {
    "SentenceAuthority",
    "ReadingAuthority",
    "DialogueAuthority",
    "WritingAuthority",
    "ExerciseAuthority",
    "AssessmentAuthority",
    "ContentQueryLayer",
    "LearningOpportunityBinding",
    "None",
}
BOOL_OR_UNKNOWN = {True, False, "unknown"}
TRACE_CONFIDENCE = {"high", "medium", "low", "unknown"}
LEVEL_FILE_RE = re.compile(r"raz_([A-W])_authority_linkage_view\.json$")
RAW_REL_PATH_RE = re.compile(r"^(?:raz_output_jsons/)?Level_([A-W])/raz_([A-W])_([0-9]+)_audio_timeline_extract\.json$")


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


def collect_linkage_files(linkage_root: Path) -> List[Tuple[str, Path]]:
    result: List[Tuple[str, Path]] = []
    for level in EXPECTED_LEVELS:
        path = linkage_root / f"Level_{level}" / f"raz_{level}_authority_linkage_view.json"
        if path.exists():
            result.append((level, path))
    return result


def add_sample(samples: List[Dict[str, str]], *, level: str, file_path: Path, uid: str, issue_code: str, field: Optional[str] = None) -> None:
    if len(samples) >= 100:
        return
    item = {
        "level": level,
        "file": file_path.name,
        "uid": uid,
        "issue_code": issue_code,
    }
    if field:
        item["field"] = field
    samples.append(item)


def list_targets(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def validate_trace(trace: Any, *, level: str, file_path: Path, uid: str, issues: Counter, samples: List[Dict[str, str]]) -> None:
    if not isinstance(trace, dict):
        issues["RAZ_LINK_VIEW_MISSING_SOURCE_TRACEABILITY"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_MISSING_SOURCE_TRACEABILITY", field="source_traceability")
        return
    for field in REQUIRED_TRACE_FIELDS:
        if field not in trace:
            issues["RAZ_LINK_VIEW_SOURCE_TRACEABILITY_FIELD_MISSING"] += 1
            add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_SOURCE_TRACEABILITY_FIELD_MISSING", field=f"source_traceability.{field}")
    if trace.get("source_type") != "raz":
        issues["RAZ_LINK_VIEW_SOURCE_TYPE_INVALID"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_SOURCE_TYPE_INVALID", field="source_traceability.source_type")
    if trace.get("source_level") != level:
        issues["RAZ_LINK_VIEW_SOURCE_LEVEL_INVALID"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_SOURCE_LEVEL_INVALID", field="source_traceability.source_level")
    if trace.get("derived_from_original_text") is not True:
        issues["RAZ_LINK_VIEW_TRACE_DERIVED_FROM_ORIGINAL_TEXT_NOT_TRUE"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_TRACE_DERIVED_FROM_ORIGINAL_TEXT_NOT_TRUE", field="source_traceability.derived_from_original_text")
    if trace.get("generated_content") is not False:
        issues["RAZ_LINK_VIEW_TRACE_GENERATED_CONTENT_NOT_FALSE"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_TRACE_GENERATED_CONTENT_NOT_FALSE", field="source_traceability.generated_content")
    if trace.get("trace_confidence") not in TRACE_CONFIDENCE:
        issues["RAZ_LINK_VIEW_TRACE_CONFIDENCE_INVALID"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_TRACE_CONFIDENCE_INVALID", field="source_traceability.trace_confidence")
    raw_path = trace.get("raw_file_relative_path")
    if raw_path is not None and (not isinstance(raw_path, str) or not RAW_REL_PATH_RE.match(raw_path)):
        issues["RAZ_LINK_VIEW_RAW_FILE_RELATIVE_PATH_INVALID"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_RAW_FILE_RELATIVE_PATH_INVALID", field="source_traceability.raw_file_relative_path")


def validate_record(record: Any, *, level: str, file_path: Path, issues: Counter, samples: List[Dict[str, str]], counters: Dict[str, Counter]) -> None:
    if not isinstance(record, dict):
        issues["RAZ_LINK_VIEW_RECORD_NOT_OBJECT"] += 1
        add_sample(samples, level=level, file_path=file_path, uid="UNKNOWN", issue_code="RAZ_LINK_VIEW_RECORD_NOT_OBJECT")
        return
    uid = record.get("record_uid") if isinstance(record.get("record_uid"), str) else "UNKNOWN"
    for field in REQUIRED_RECORD_FIELDS:
        if field not in record:
            issues["RAZ_LINK_VIEW_REQUIRED_FIELD_MISSING"] += 1
            add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_REQUIRED_FIELD_MISSING", field=field)
    artifact_layer = record.get("artifact_layer")
    authority_status = record.get("authority_status")
    promotion_status = record.get("promotion_status")
    review_status = record.get("review_status")
    required_review = record.get("required_review_before_promotion")
    generated_content = record.get("generated_content")
    derived_from_original_text = record.get("derived_from_original_text")
    trace_confidence = record.get("trace_confidence")
    allowed = list_targets(record.get("allowed_authority_targets"))
    blocked = list_targets(record.get("blocked_authority_targets"))

    if artifact_layer not in ALLOWED_ARTIFACT_LAYERS:
        issues["RAZ_LINK_VIEW_ARTIFACT_LAYER_INVALID"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_ARTIFACT_LAYER_INVALID", field="artifact_layer")
    if authority_status not in ALLOWED_AUTHORITY_STATUS:
        issues["RAZ_LINK_VIEW_AUTHORITY_STATUS_INVALID"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_AUTHORITY_STATUS_INVALID", field="authority_status")
    if authority_status == "promoted_authority":
        issues["RAZ_LINK_VIEW_AUTHORITY_PROMOTED"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_AUTHORITY_PROMOTED", field="authority_status")
    if promotion_status != "promotion_blocked":
        issues["RAZ_LINK_VIEW_PROMOTION_STATUS_NOT_BLOCKED"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_PROMOTION_STATUS_NOT_BLOCKED", field="promotion_status")
    if review_status not in ALLOWED_REVIEW_STATUS:
        issues["RAZ_LINK_VIEW_REVIEW_STATUS_INVALID"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_REVIEW_STATUS_INVALID", field="review_status")
    if required_review not in ALLOWED_REQUIRED_REVIEW:
        issues["RAZ_LINK_VIEW_REQUIRED_REVIEW_INVALID"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_REQUIRED_REVIEW_INVALID", field="required_review_before_promotion")
    if generated_content is not False:
        issues["RAZ_LINK_VIEW_GENERATED_CONTENT_NOT_FALSE"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_GENERATED_CONTENT_NOT_FALSE", field="generated_content")
    if derived_from_original_text is not True:
        issues["RAZ_LINK_VIEW_DERIVED_FROM_ORIGINAL_TEXT_NOT_TRUE"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_DERIVED_FROM_ORIGINAL_TEXT_NOT_TRUE", field="derived_from_original_text")
    if trace_confidence not in TRACE_CONFIDENCE:
        issues["RAZ_LINK_VIEW_TRACE_CONFIDENCE_INVALID"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_TRACE_CONFIDENCE_INVALID", field="trace_confidence")

    if not isinstance(record.get("allowed_authority_targets"), list):
        issues["RAZ_LINK_VIEW_ALLOWED_TARGETS_NOT_LIST"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_ALLOWED_TARGETS_NOT_LIST", field="allowed_authority_targets")
    if not isinstance(record.get("blocked_authority_targets"), list):
        issues["RAZ_LINK_VIEW_BLOCKED_TARGETS_NOT_LIST"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_BLOCKED_TARGETS_NOT_LIST", field="blocked_authority_targets")
    for target in allowed:
        if target not in ALLOWED_TARGETS:
            issues["RAZ_LINK_VIEW_ALLOWED_TARGET_INVALID"] += 1
            add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_ALLOWED_TARGET_INVALID", field="allowed_authority_targets")
    for target in blocked:
        if target not in ALLOWED_TARGETS:
            issues["RAZ_LINK_VIEW_BLOCKED_TARGET_INVALID"] += 1
            add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_BLOCKED_TARGET_INVALID", field="blocked_authority_targets")
    if set(allowed).intersection(blocked):
        issues["RAZ_LINK_VIEW_TARGET_ALLOW_BLOCK_CONFLICT"] += 1
        add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code="RAZ_LINK_VIEW_TARGET_ALLOW_BLOCK_CONFLICT", field="allowed_authority_targets")
    if "AssessmentAuthority" in allowed:
        for field in ("answer_key", "scoring_rule", "error_type", "error_detail", "remediation_tag"):
            if field not in record:
                issues[f"RAZ_LINK_VIEW_ASSESSMENT_MISSING_{field.upper()}"] += 1
                add_sample(samples, level=level, file_path=file_path, uid=uid, issue_code=f"RAZ_LINK_VIEW_ASSESSMENT_MISSING_{field.upper()}", field=field)

    validate_trace(record.get("source_traceability"), level=level, file_path=file_path, uid=uid, issues=issues, samples=samples)

    counters["artifact_layer_counts"][str(artifact_layer)] += 1
    counters["promotion_status_counts"][str(promotion_status)] += 1
    counters["authority_status_counts"][str(authority_status)] += 1
    counters["review_status_counts"][str(review_status)] += 1
    counters["required_review_counts"][str(required_review)] += 1
    counters["trace_confidence_counts"][str(trace_confidence)] += 1
    for target in allowed:
        counters["allowed_target_counts"][target] += 1
    for target in blocked:
        counters["blocked_target_counts"][target] += 1


def validate(linkage_root: Path, reports_dir: Path, schema_path: Path) -> Dict[str, Any]:
    issues: Counter = Counter()
    samples: List[Dict[str, str]] = []
    warnings: List[str] = []
    blockers: List[str] = []
    parse_failures: List[Dict[str, str]] = []
    level_counts: Dict[str, Dict[str, int]] = {}
    file_summaries: List[Dict[str, Any]] = []
    counters: Dict[str, Counter] = {
        "artifact_layer_counts": Counter(),
        "promotion_status_counts": Counter(),
        "authority_status_counts": Counter(),
        "review_status_counts": Counter(),
        "required_review_counts": Counter(),
        "allowed_target_counts": Counter(),
        "blocked_target_counts": Counter(),
        "trace_confidence_counts": Counter(),
    }

    if not schema_path.exists():
        blockers.append("contract_schema_missing")
    else:
        schema_payload = read_json(schema_path)
        if schema_payload.get("title") != "RAZ Authority Linkage Contract":
            issues["RAZ_LINK_VIEW_CONTRACT_SCHEMA_UNEXPECTED"] += 1

    files = collect_linkage_files(linkage_root)
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
        if payload.get("schema_version") != SCHEMA_VERSION:
            issues["RAZ_LINK_VIEW_SCHEMA_VERSION_INVALID"] += 1
            add_sample(samples, level=level, file_path=path, uid=f"FILE:{path.name}", issue_code="RAZ_LINK_VIEW_SCHEMA_VERSION_INVALID", field="schema_version")
        record_list = payload.get("records")
        if not isinstance(record_list, list):
            issues["RAZ_LINK_VIEW_RECORDS_NOT_LIST"] += 1
            add_sample(samples, level=level, file_path=path, uid=f"FILE:{path.name}", issue_code="RAZ_LINK_VIEW_RECORDS_NOT_LIST", field="records")
            continue
        records_scanned = 0
        for record in record_list:
            validate_record(record, level=level, file_path=path, issues=issues, samples=samples, counters=counters)
            records_scanned += 1
        level_counts[level] = {"records_scanned": records_scanned}
        file_summaries.append({"level": level, "file": path.name, "records_scanned": records_scanned})

    if parse_failures:
        blockers.append("linkage_view_parse_failures")
    if issues:
        blockers.append("linkage_view_contract_violations")

    status = "LINKAGE_VIEW_VALIDATION_PASS" if not blockers else "LINKAGE_VIEW_VALIDATION_BLOCKED"
    report = {
        "task_id": "RAZ-AW-S3K_AuthorityLinkageViewValidator_QA",
        "report_type": "raz_authority_linkage_view_validation",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "raw_mutation": False,
        "derived_mutation": False,
        "linkage_mutation": False,
        "authority_promotion": False,
        "input_linkage_root": str(linkage_root),
        "contract_schema_path": str(schema_path),
        "files_scanned_count": len(files),
        "records_scanned_count": sum(item["records_scanned"] for item in level_counts.values()),
        "level_counts": level_counts,
        "file_summaries_sample": file_summaries[:30],
        "artifact_layer_counts": dict(sorted(counters["artifact_layer_counts"].items())),
        "promotion_status_counts": dict(sorted(counters["promotion_status_counts"].items())),
        "authority_status_counts": dict(sorted(counters["authority_status_counts"].items())),
        "review_status_counts": dict(sorted(counters["review_status_counts"].items())),
        "required_review_counts": dict(sorted(counters["required_review_counts"].items())),
        "allowed_target_counts": dict(sorted(counters["allowed_target_counts"].items())),
        "blocked_target_counts": dict(sorted(counters["blocked_target_counts"].items())),
        "trace_confidence_counts": dict(sorted(counters["trace_confidence_counts"].items())),
        "issue_counts": dict(sorted(issues.items())),
        "parse_failure_count": len(parse_failures),
        "parse_failures_sample": parse_failures[:20],
        "sample_issues": samples,
        "warnings": sorted(set(warnings)),
        "blockers": sorted(set(blockers)),
        "qa_assertions": [
            "linkage view files are present",
            "records package uses raz_authority_linkage_contract.v1",
            "required S3G fields are present",
            "source_traceability is present and level-consistent",
            "promotion_status remains promotion_blocked",
            "authority_status is never promoted_authority",
            "generated_content remains false for deterministic RAZ linkage view",
            "derived_from_original_text remains true",
            "allowed/blocked authority targets do not conflict",
            "report contains no text values",
        ],
    }
    hits = scan_forbidden_keys(report)
    if hits:
        raise ValueError(f"unsafe_report_key_emitted:{hits[:5]}")
    write_json(reports_dir / REPORT_NAME, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated RAZ authority-linkage view artifacts.")
    parser.add_argument("--linkage-root", default="raz_output_jsons/linkage", help="Local linkage root containing Level_*/raz_*_authority_linkage_view.json files.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Sanitized report output directory.")
    parser.add_argument("--schema", default="schemas/raz/raz_authority_linkage_contract.schema.json", help="Authority linkage contract schema path.")
    args = parser.parse_args()
    report = validate(Path(args.linkage_root).resolve(), Path(args.reports_dir).resolve(), Path(args.schema).resolve())
    print(json.dumps({
        "status": report["status"],
        "files_scanned_count": report["files_scanned_count"],
        "records_scanned_count": report["records_scanned_count"],
        "promotion_status_counts": report["promotion_status_counts"],
        "authority_status_counts": report["authority_status_counts"],
        "issue_counts": report["issue_counts"],
        "warnings": report["warnings"],
        "blockers": report["blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "LINKAGE_VIEW_VALIDATION_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
