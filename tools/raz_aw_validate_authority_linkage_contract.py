#!/usr/bin/env python3
"""Validate RAZ authority-linkage contract compliance locally.

S3G1 contract:
- Read local derived normalized/enriched artifacts under raz_output_jsons/derived.
- Emit sanitized report only to reports/raz/raz_authority_linkage_contract_validation.json.
- Do not modify raw corpus.
- Do not modify derived corpus.
- Do not promote any authority.
- Fail closed for missing contract fields and unsafe promotion states.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
FORBIDDEN_REPORT_KEYS = {
    "text",
    "raw_text",
    "page_text",
    "full_raw_json",
    "full_derived_record",
    "sentence_candidates",
    "page_units",
    "reuse_unit_candidates",
}
CONTRACT_REQUIRED_FIELDS = [
    "generated_content",
    "derived_from_original_text",
]
ALLOWED_AUTHORITY_STATUS = {
    "raw_reference",
    "candidate_only",
    "validated_candidate",
    "reviewed_candidate",
    "promoted_authority",
    "rejected",
    "deprecated",
}
ALLOWED_PROMOTION_STATUS = {
    "not_promoted",
    "promotion_blocked",
    "eligible_after_review",
    "eligible_after_validation",
    "eligible_after_contract_patch",
    "promoted",
    "rejected",
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
BOOL_OR_UNKNOWN = {True, False, "unknown"}
TRACE_CONFIDENCE = {"high", "medium", "low", "unknown"}
RAW_REL_PATH_RE = re.compile(r"^(?:raz_output_jsons/)?Level_([A-W])/raz_([A-W])_([0-9]+)_audio_timeline_extract\.json$")


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("top_level_json_is_not_object")
    return data


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scan_report_keys(value: Any, path: str = "$", hits: Optional[List[str]] = None) -> List[str]:
    if hits is None:
        hits = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_REPORT_KEYS:
                hits.append(f"{path}.{key}")
            scan_report_keys(child, f"{path}.{key}", hits)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            scan_report_keys(child, f"{path}[{idx}]", hits)
    return hits


def add_sample(
    sample_issues: List[Dict[str, str]],
    *,
    level: str,
    artifact_type: str,
    file_path: Path,
    uid: str,
    issue_code: str,
    field: Optional[str] = None,
) -> None:
    if len(sample_issues) >= 80:
        return
    item = {
        "level": level,
        "artifact_type": artifact_type,
        "file": file_path.name,
        "uid": uid,
        "issue_code": issue_code,
    }
    if field:
        item["field"] = field
    sample_issues.append(item)


def normalize_review_status(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    if value == "pending":
        return "pending"
    if value == "needs_review":
        return "needs_review"
    if value == "rejected":
        return "rejected"
    return value


def infer_artifact_type(filename: str) -> Optional[str]:
    name = filename.lower()
    if "normalized_books" in name:
        return "normalized_books"
    if "normalized_sentences" in name:
        return "normalized_sentences"
    if "normalized_page_units" in name:
        return "normalized_page_units"
    if "normalized_reuse_units" in name:
        return "normalized_reuse_units"
    if "enriched_books" in name:
        return "enriched_books"
    if "enriched_sentences" in name:
        return "enriched_sentences"
    if "enriched_units" in name:
        return "enriched_units"
    return None


def infer_uid(record: Dict[str, Any], artifact_type: str) -> str:
    for key in (
        "record_uid",
        "sentence_uid",
        "page_unit_uid",
        "reuse_unit_uid",
        "unit_uid",
        "book_uid",
    ):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return f"UNKNOWN_UID:{artifact_type}"


def infer_artifact_layer(record: Dict[str, Any], artifact_type: str) -> str:
    explicit = record.get("artifact_layer")
    if isinstance(explicit, str):
        return explicit
    if artifact_type == "normalized_sentences":
        return "sentence_normalized"
    if artifact_type == "enriched_sentences":
        return "sentence_enriched"
    if artifact_type == "normalized_page_units":
        return "page_unit"
    if artifact_type == "normalized_reuse_units":
        return "reuse_unit_candidate"
    if artifact_type == "enriched_units":
        if record.get("unit_type") == "reuse_unit":
            return "reuse_unit_candidate"
        return "page_unit"
    return "raw_source_reference"


def infer_authority_status(record: Dict[str, Any]) -> Optional[str]:
    if isinstance(record.get("authority_status"), str):
        return record["authority_status"]
    linkage_status = record.get("authority_linkage_status")
    if linkage_status == "candidate_only":
        return "candidate_only"
    return None


def collect_json_files(derived_root: Path) -> List[Tuple[str, Path, str]]:
    files: List[Tuple[str, Path, str]] = []
    for level in EXPECTED_LEVELS:
        for layer in ("normalized", "enriched"):
            layer_dir = derived_root / f"Level_{level}" / layer
            if not layer_dir.exists():
                continue
            for path in sorted(layer_dir.glob("*.json")):
                artifact_type = infer_artifact_type(path.name)
                if artifact_type:
                    files.append((level, path, artifact_type))
    return files


def validate_source_traceability(
    trace: Any,
    *,
    level: str,
    artifact_type: str,
    file_path: Path,
    uid: str,
    issue_counts: Counter,
    sample_issues: List[Dict[str, str]],
) -> None:
    if not isinstance(trace, dict):
        issue_counts["RAZ_LINK_MISSING_SOURCE_TRACEABILITY"] += 1
        add_sample(
            sample_issues,
            level=level,
            artifact_type=artifact_type,
            file_path=file_path,
            uid=uid,
            issue_code="RAZ_LINK_MISSING_SOURCE_TRACEABILITY",
            field="source_traceability",
        )
        return

    required = (
        "source_type",
        "source_level",
        "source_book_id",
        "source_book_uid",
        "derived_from_original_text",
        "generated_content",
        "trace_confidence",
    )
    for field in required:
        if field not in trace:
            issue_counts["RAZ_LINK_SOURCE_TRACEABILITY_FIELD_MISSING"] += 1
            add_sample(
                sample_issues,
                level=level,
                artifact_type=artifact_type,
                file_path=file_path,
                uid=uid,
                issue_code="RAZ_LINK_SOURCE_TRACEABILITY_FIELD_MISSING",
                field=field,
            )

    if trace.get("source_type") != "raz":
        issue_counts["RAZ_LINK_SOURCE_TYPE_INVALID"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_SOURCE_TYPE_INVALID", field="source_type")
    if trace.get("source_level") != level:
        issue_counts["RAZ_LINK_SOURCE_LEVEL_INVALID"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_SOURCE_LEVEL_INVALID", field="source_level")
    raw_path = trace.get("raw_file_relative_path")
    if raw_path is not None:
        if not isinstance(raw_path, str) or not RAW_REL_PATH_RE.match(raw_path):
            issue_counts["RAZ_LINK_RAW_FILE_RELATIVE_PATH_INVALID"] += 1
            add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_RAW_FILE_RELATIVE_PATH_INVALID", field="raw_file_relative_path")
    if trace.get("derived_from_original_text") not in BOOL_OR_UNKNOWN:
        issue_counts["RAZ_LINK_DERIVED_FROM_ORIGINAL_TEXT_INVALID"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_DERIVED_FROM_ORIGINAL_TEXT_INVALID", field="source_traceability.derived_from_original_text")
    if trace.get("generated_content") not in BOOL_OR_UNKNOWN:
        issue_counts["RAZ_LINK_GENERATED_CONTENT_INVALID"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_GENERATED_CONTENT_INVALID", field="source_traceability.generated_content")
    if trace.get("trace_confidence") not in TRACE_CONFIDENCE:
        issue_counts["RAZ_LINK_TRACE_CONFIDENCE_INVALID"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_TRACE_CONFIDENCE_INVALID", field="source_traceability.trace_confidence")


def validate_targets(
    value: Any,
    *,
    field_name: str,
    level: str,
    artifact_type: str,
    file_path: Path,
    uid: str,
    issue_counts: Counter,
    sample_issues: List[Dict[str, str]],
) -> List[str]:
    if not isinstance(value, list):
        issue_counts[f"RAZ_LINK_{field_name.upper()}_MISSING_OR_NOT_LIST"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code=f"RAZ_LINK_{field_name.upper()}_MISSING_OR_NOT_LIST", field=field_name)
        return []
    result: List[str] = []
    for item in value:
        if not isinstance(item, str) or item not in ALLOWED_TARGETS:
            issue_counts[f"RAZ_LINK_{field_name.upper()}_INVALID_TARGET"] += 1
            add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code=f"RAZ_LINK_{field_name.upper()}_INVALID_TARGET", field=field_name)
            continue
        result.append(item)
    if len(set(result)) != len(result):
        issue_counts[f"RAZ_LINK_{field_name.upper()}_DUPLICATE_TARGET"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code=f"RAZ_LINK_{field_name.upper()}_DUPLICATE_TARGET", field=field_name)
    return result


def validate_record(
    record: Dict[str, Any],
    *,
    level: str,
    file_path: Path,
    artifact_type: str,
    issue_counts: Counter,
    sample_issues: List[Dict[str, str]],
    file_record_counts: Counter,
) -> None:
    uid = infer_uid(record, artifact_type)
    artifact_layer = infer_artifact_layer(record, artifact_type)
    authority_status = infer_authority_status(record)
    review_status = normalize_review_status(record.get("review_status"))

    file_record_counts["records_scanned"] += 1
    file_record_counts[f"artifact_layer:{artifact_layer}"] += 1

    if artifact_layer not in ALLOWED_ARTIFACT_LAYERS:
        issue_counts["RAZ_LINK_ARTIFACT_LAYER_INVALID"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_ARTIFACT_LAYER_INVALID", field="artifact_layer")

    for field in CONTRACT_REQUIRED_FIELDS:
        if field not in record:
            issue_counts[f"RAZ_LINK_MISSING_{field.upper()}"] += 1
            add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code=f"RAZ_LINK_MISSING_{field.upper()}", field=field)

    if "source_traceability" not in record:
        issue_counts["RAZ_LINK_MISSING_SOURCE_TRACEABILITY"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_MISSING_SOURCE_TRACEABILITY", field="source_traceability")
    if "source_traceability" in record:
        validate_source_traceability(
            record.get("source_traceability"),
            level=level,
            artifact_type=artifact_type,
            file_path=file_path,
            uid=uid,
            issue_counts=issue_counts,
            sample_issues=sample_issues,
        )

    if authority_status is None:
        issue_counts["RAZ_LINK_MISSING_AUTHORITY_STATUS"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_MISSING_AUTHORITY_STATUS", field="authority_status")
    elif authority_status not in ALLOWED_AUTHORITY_STATUS:
        issue_counts["RAZ_LINK_INVALID_AUTHORITY_STATUS"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_INVALID_AUTHORITY_STATUS", field="authority_status")

    promotion_status = record.get("promotion_status")
    if promotion_status is None:
        issue_counts["RAZ_LINK_MISSING_PROMOTION_STATUS"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_MISSING_PROMOTION_STATUS", field="promotion_status")
    elif promotion_status not in ALLOWED_PROMOTION_STATUS:
        issue_counts["RAZ_LINK_INVALID_PROMOTION_STATUS"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_INVALID_PROMOTION_STATUS", field="promotion_status")

    if review_status is None:
        issue_counts["RAZ_LINK_MISSING_REVIEW_STATUS"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_MISSING_REVIEW_STATUS", field="review_status")
    elif review_status not in ALLOWED_REVIEW_STATUS:
        issue_counts["RAZ_LINK_INVALID_REVIEW_STATUS"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_INVALID_REVIEW_STATUS", field="review_status")

    required_review = record.get("required_review_before_promotion")
    if required_review is None:
        issue_counts["RAZ_LINK_MISSING_REQUIRED_REVIEW_BEFORE_PROMOTION"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_MISSING_REQUIRED_REVIEW_BEFORE_PROMOTION", field="required_review_before_promotion")
    elif required_review not in ALLOWED_REQUIRED_REVIEW:
        issue_counts["RAZ_LINK_INVALID_REQUIRED_REVIEW_BEFORE_PROMOTION"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_INVALID_REQUIRED_REVIEW_BEFORE_PROMOTION", field="required_review_before_promotion")

    generated_content = record.get("generated_content")
    derived_from_original_text = record.get("derived_from_original_text")
    if generated_content is not None and generated_content not in BOOL_OR_UNKNOWN:
        issue_counts["RAZ_LINK_GENERATED_CONTENT_INVALID"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_GENERATED_CONTENT_INVALID", field="generated_content")
    if derived_from_original_text is not None and derived_from_original_text not in BOOL_OR_UNKNOWN:
        issue_counts["RAZ_LINK_DERIVED_FROM_ORIGINAL_TEXT_INVALID"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_DERIVED_FROM_ORIGINAL_TEXT_INVALID", field="derived_from_original_text")

    if record.get("trace_confidence") is not None and record.get("trace_confidence") not in TRACE_CONFIDENCE:
        issue_counts["RAZ_LINK_TRACE_CONFIDENCE_INVALID"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_TRACE_CONFIDENCE_INVALID", field="trace_confidence")

    if "allowed_authority_targets" not in record:
        issue_counts["RAZ_LINK_MISSING_ALLOWED_AUTHORITY_TARGETS"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_MISSING_ALLOWED_AUTHORITY_TARGETS", field="allowed_authority_targets")
    if "allowed_authority_targets" in record:
        allowed_targets = validate_targets(
            record.get("allowed_authority_targets"),
            field_name="allowed_authority_targets",
            level=level,
            artifact_type=artifact_type,
            file_path=file_path,
            uid=uid,
            issue_counts=issue_counts,
            sample_issues=sample_issues,
        )
    else:
        allowed_targets = []
    if "blocked_authority_targets" not in record:
        issue_counts["RAZ_LINK_MISSING_BLOCKED_AUTHORITY_TARGETS"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_MISSING_BLOCKED_AUTHORITY_TARGETS", field="blocked_authority_targets")
    if "blocked_authority_targets" in record:
        blocked_targets = validate_targets(
            record.get("blocked_authority_targets"),
            field_name="blocked_authority_targets",
            level=level,
            artifact_type=artifact_type,
            file_path=file_path,
            uid=uid,
            issue_counts=issue_counts,
            sample_issues=sample_issues,
        )
    else:
        blocked_targets = []
    overlap = sorted(set(allowed_targets).intersection(blocked_targets))
    if overlap:
        issue_counts["RAZ_LINK_TARGET_ALLOW_BLOCK_CONFLICT"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_TARGET_ALLOW_BLOCK_CONFLICT", field="allowed_authority_targets")

    if authority_status == "candidate_only" and promotion_status == "promoted":
        issue_counts["RAZ_LINK_CANDIDATE_DIRECT_PROMOTION"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_CANDIDATE_DIRECT_PROMOTION")

    if artifact_layer == "reuse_unit_candidate" and promotion_status == "promoted":
        issue_counts["RAZ_LINK_REUSE_UNIT_DIRECT_PROMOTION"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_REUSE_UNIT_DIRECT_PROMOTION")

    if generated_content is True and promotion_status == "promoted" and review_status != "passed":
        issue_counts["RAZ_LINK_GENERATED_CONTENT_PROMOTED_WITHOUT_REVIEW"] += 1
        add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code="RAZ_LINK_GENERATED_CONTENT_PROMOTED_WITHOUT_REVIEW")

    if "AssessmentAuthority" in allowed_targets:
        for field in ("answer_key", "scoring_rule", "error_type", "error_detail", "remediation_tag"):
            if field not in record:
                issue_counts[f"RAZ_LINK_ASSESSMENT_MISSING_{field.upper()}"] += 1
                add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=file_path, uid=uid, issue_code=f"RAZ_LINK_ASSESSMENT_MISSING_{field.upper()}", field=field)


def validate(derived_root: Path, reports_dir: Path, schema_path: Path) -> Dict[str, Any]:
    issue_counts: Counter = Counter()
    level_counts: Dict[str, Dict[str, int]] = {level: {} for level in EXPECTED_LEVELS}
    sample_issues: List[Dict[str, str]] = []
    parse_failures: List[Dict[str, str]] = []
    missing_layer_dirs: List[str] = []
    scanned_files: List[str] = []
    file_summaries: List[Dict[str, Any]] = []
    artifact_counts: Counter = Counter()
    legacy_gap_counts: Counter = Counter()

    if not schema_path.exists():
        raise FileNotFoundError(f"schema_missing:{schema_path}")
    schema_payload = read_json(schema_path)
    if schema_payload.get("title") != "RAZ Authority Linkage Contract":
        issue_counts["RAZ_LINK_CONTRACT_SCHEMA_VERSION_UNEXPECTED"] += 1

    for level in EXPECTED_LEVELS:
        for layer in ("normalized", "enriched"):
            layer_dir = derived_root / f"Level_{level}" / layer
            if not layer_dir.exists():
                missing_layer_dirs.append(str(layer_dir))

    for level, path, artifact_type in collect_json_files(derived_root):
        scanned_files.append(str(path))
        try:
            payload = read_json(path)
        except Exception as exc:
            parse_failures.append({
                "level": level,
                "file": path.name,
                "artifact_type": artifact_type,
                "error_type": type(exc).__name__,
            })
            issue_counts["RAZ_LINK_FILE_PARSE_FAILURE"] += 1
            continue

        records = payload.get("records")
        if not isinstance(records, list):
            issue_counts["RAZ_LINK_RECORDS_NOT_LIST"] += 1
            add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=path, uid=f"FILE:{path.name}", issue_code="RAZ_LINK_RECORDS_NOT_LIST", field="records")
            continue

        file_counter: Counter = Counter()
        for item in records:
            if not isinstance(item, dict):
                issue_counts["RAZ_LINK_RECORD_NOT_OBJECT"] += 1
                add_sample(sample_issues, level=level, artifact_type=artifact_type, file_path=path, uid=f"FILE:{path.name}", issue_code="RAZ_LINK_RECORD_NOT_OBJECT")
                continue
            validate_record(
                item,
                level=level,
                file_path=path,
                artifact_type=artifact_type,
                issue_counts=issue_counts,
                sample_issues=sample_issues,
                file_record_counts=file_counter,
            )
            artifact_counts[artifact_type] += 1

        level_counts[level][artifact_type] = file_counter["records_scanned"]
        summary = {
            "level": level,
            "file": path.name,
            "artifact_type": artifact_type,
            "records_scanned": file_counter["records_scanned"],
        }
        artifact_layer_counts = {k: v for k, v in sorted(file_counter.items()) if k.startswith("artifact_layer:")}
        if artifact_layer_counts:
            summary["artifact_layer_counts"] = artifact_layer_counts
        file_summaries.append(summary)

    for key, value in issue_counts.items():
        if key.startswith("RAZ_LINK_MISSING_") or "ASSESSMENT_MISSING" in key:
            legacy_gap_counts[key] = value

    blockers: List[str] = []
    warnings: List[str] = []
    if parse_failures:
        blockers.append("authority_linkage_contract_parse_failures")
    if missing_layer_dirs:
        warnings.append("some_level_layer_directories_missing")
    if issue_counts:
        blockers.append("authority_linkage_contract_violations")

    status = "IMPLEMENTED_PASS"
    if blockers:
        if legacy_gap_counts:
            status = "IMPLEMENTED_WITH_BLOCKED_LEGACY_GAPS"
        else:
            status = "BLOCKED"

    report = {
        "task_id": "RAZ-AW-S3G1_AuthorityLinkageContractValidator_LocalImplementation",
        "report_type": "raz_authority_linkage_contract_validation",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "raw_mutation": False,
        "derived_mutation": False,
        "authority_promotion": False,
        "runtime_api_integration": False,
        "contract_schema_path": str(schema_path),
        "derived_root": str(derived_root),
        "files_scanned_count": len(scanned_files),
        "files_scanned_sample": scanned_files[:30],
        "artifact_record_counts": dict(sorted(artifact_counts.items())),
        "level_counts": level_counts,
        "file_summaries_sample": file_summaries[:30],
        "issue_counts": dict(sorted(issue_counts.items())),
        "legacy_gap_counts": dict(sorted(legacy_gap_counts.items())),
        "missing_layer_dir_count": len(missing_layer_dirs),
        "missing_layer_dirs_sample": missing_layer_dirs[:20],
        "parse_failure_count": len(parse_failures),
        "parse_failures_sample": parse_failures[:20],
        "sample_issues": sample_issues,
        "warnings": sorted(set(warnings)),
        "blockers": sorted(set(blockers)),
        "fail_closed_checks": [
            "missing source_traceability",
            "missing promotion_status",
            "missing generated_content",
            "missing derived_from_original_text",
            "missing allowed_authority_targets",
            "missing blocked_authority_targets",
            "candidate_only marked promoted",
            "reuse_unit_candidate direct promotion",
            "generated content promoted without review",
            "AssessmentAuthority allowed without answer_key / scoring_rule / error diagnosis fields",
        ],
    }

    hits = scan_report_keys(report)
    if hits:
        raise ValueError(f"unsafe_report_key_emitted: {hits[:5]}")
    write_json(reports_dir / "raz_authority_linkage_contract_validation.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate local RAZ authority-linkage contract compliance.")
    parser.add_argument("--derived-root", default="raz_output_jsons/derived", help="Derived root containing Level_*/normalized and Level_*/enriched.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Sanitized report output directory.")
    parser.add_argument("--schema", default="schemas/raz/raz_authority_linkage_contract.schema.json", help="Authority linkage contract schema path.")
    args = parser.parse_args()

    derived_root = Path(args.derived_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    schema_path = Path(args.schema).resolve()

    if not derived_root.exists() or not derived_root.is_dir():
        payload = {
            "task_id": "RAZ-AW-S3G1_AuthorityLinkageContractValidator_LocalImplementation",
            "report_type": "raz_authority_linkage_contract_validation",
            "status": "BLOCKED",
            "sanitized": True,
            "contains_text_values": False,
            "raw_mutation": False,
            "derived_mutation": False,
            "authority_promotion": False,
            "blockers": ["derived_root_missing_or_not_directory"],
            "derived_root": str(derived_root),
        }
        write_json(reports_dir / "raz_authority_linkage_contract_validation.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    try:
        report = validate(derived_root, reports_dir, schema_path)
    except FileNotFoundError as exc:
        payload = {
            "task_id": "RAZ-AW-S3G1_AuthorityLinkageContractValidator_LocalImplementation",
            "report_type": "raz_authority_linkage_contract_validation",
            "status": "BLOCKED",
            "sanitized": True,
            "contains_text_values": False,
            "raw_mutation": False,
            "derived_mutation": False,
            "authority_promotion": False,
            "blockers": [str(exc)],
        }
        write_json(reports_dir / "raz_authority_linkage_contract_validation.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps({
        "status": report["status"],
        "files_scanned_count": report["files_scanned_count"],
        "artifact_record_counts": report["artifact_record_counts"],
        "issue_counts": report["issue_counts"],
        "warnings": report["warnings"],
        "blockers": report["blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "IMPLEMENTED_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
