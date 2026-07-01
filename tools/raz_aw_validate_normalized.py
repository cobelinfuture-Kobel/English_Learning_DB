#!/usr/bin/env python3
"""Validate RAZ A-W normalized candidate artifacts.

S3C2 contract:
- Reads local/Drive-derived normalized artifacts under raz_output_jsons/derived.
- Emits only sanitized validation reports to reports/raz.
- Does not emit sentence text or raw payloads to GitHub reports.
- Does not promote content/tag/authority status.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
EXPECTED_BOOK_COUNT = 1959
EXPECTED_SCHEMA_VERSIONS = {
    "books": "raz_normalized_books.v1",
    "sentences": "raz_normalized_sentences.v1",
    "page_units": "raz_normalized_page_units.v1",
    "reuse_units": "raz_normalized_reuse_units.v1",
}
NORMALIZED_FILENAMES = {
    "books": "raz_{level}_normalized_books.json",
    "sentences": "raz_{level}_normalized_sentences.json",
    "page_units": "raz_{level}_normalized_page_units.json",
    "reuse_units": "raz_{level}_normalized_reuse_units.json",
}
FORBIDDEN_OUTPUT_KEYS = {
    "sentence_candidates",
    "page_units_raw_payload",
    "reuse_unit_candidates",
    "legacy_story_sentences",
    "audio_trace",
    "word_trace",
    "raw_text",
    "page_text",
    "full_raw_json",
}
FORBIDDEN_STATUS_VALUES = {
    "approved",
    "promoted",
    "final_authority",
    "learner_facing_approved",
}
BOOK_UID_RE = re.compile(r"^raz_([A-W])_([0-9]+)$")
SENTENCE_UID_RE = re.compile(r"^raz_([A-W])_([0-9]+)_s([0-9]{4})$")
PAGE_UID_RE = re.compile(r"^raz_([A-W])_([0-9]+)_p([0-9]{4})$")
REUSE_UID_RE = re.compile(r"^raz_([A-W])_([0-9]+)_r([0-9]{4})$")
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


def count_forbidden_keys(value: Any, counter: Counter, path: str = "$", sample: Optional[List[str]] = None) -> None:
    if sample is None:
        sample = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_OUTPUT_KEYS:
                counter[key] += 1
                if len(sample) < 20:
                    sample.append(path)
            count_forbidden_keys(child, counter, f"{path}.{key}", sample)
    elif isinstance(value, list):
        for item in value:
            count_forbidden_keys(item, counter, f"{path}[]", sample)


def has_forbidden_status(value: Any, counter: Counter) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, str) and child in FORBIDDEN_STATUS_VALUES:
                counter[f"{key}:{child}"] += 1
            has_forbidden_status(child, counter)
    elif isinstance(value, list):
        for item in value:
            has_forbidden_status(item, counter)


def safe_sample(uid: Any, issue: str, sample: List[Dict[str, str]], level: Optional[str] = None) -> None:
    if len(sample) >= 30:
        return
    item = {"issue": issue, "uid": str(uid)}
    if level:
        item["level"] = level
    sample.append(item)


def require_fields(record: Dict[str, Any], fields: Iterable[str], uid: str, issue_counts: Counter, sample: List[Dict[str, str]], level: str) -> bool:
    ok = True
    for field in fields:
        if field not in record:
            issue_counts[f"missing_field:{field}"] += 1
            safe_sample(uid, f"missing_field:{field}", sample, level)
            ok = False
    return ok


def validate_source_ref(record: Dict[str, Any], uid: str, expected_layer: str, issue_counts: Counter, sample: List[Dict[str, str]], level: str) -> None:
    source_ref = record.get("source_ref")
    if not isinstance(source_ref, dict):
        issue_counts["source_ref_missing_or_not_object"] += 1
        safe_sample(uid, "source_ref_missing_or_not_object", sample, level)
        return
    if source_ref.get("source_layer") != expected_layer:
        issue_counts[f"source_layer_mismatch:{expected_layer}"] += 1
        safe_sample(uid, f"source_layer_mismatch:{expected_layer}", sample, level)
    raw_path = source_ref.get("raw_file_relative_path")
    if not isinstance(raw_path, str) or not RAW_REL_PATH_RE.match(raw_path):
        issue_counts["raw_file_relative_path_invalid"] += 1
        safe_sample(uid, "raw_file_relative_path_invalid", sample, level)


def validate_book(record: Dict[str, Any], level: str, issue_counts: Counter, sample: List[Dict[str, str]]) -> Optional[str]:
    uid = str(record.get("book_uid", "MISSING_BOOK_UID"))
    required = [
        "book_uid",
        "source",
        "level",
        "book_id",
        "title",
        "source_type",
        "extraction_method",
        "extractor_version",
        "story_page_start",
        "story_page_end",
        "story_page_count",
        "source_ref",
        "authority_status",
        "normalization_status",
        "content_authority_status",
        "review_status",
    ]
    require_fields(record, required, uid, issue_counts, sample, level)
    match = BOOK_UID_RE.match(uid)
    if not match:
        issue_counts["book_uid_pattern_invalid"] += 1
        safe_sample(uid, "book_uid_pattern_invalid", sample, level)
        return None
    uid_level, uid_book_id = match.groups()
    if uid_level != level or record.get("level") != level or str(record.get("book_id")) != uid_book_id:
        issue_counts["book_identity_mismatch"] += 1
        safe_sample(uid, "book_identity_mismatch", sample, level)
    if record.get("source") != "RAZ":
        issue_counts["source_not_RAZ"] += 1
        safe_sample(uid, "source_not_RAZ", sample, level)
    if record.get("authority_status") != "candidate_only":
        issue_counts["book_authority_status_not_candidate_only"] += 1
        safe_sample(uid, "book_authority_status_not_candidate_only", sample, level)
    if record.get("normalization_status") != "candidate_normalized":
        issue_counts["book_normalization_status_invalid"] += 1
        safe_sample(uid, "book_normalization_status_invalid", sample, level)
    if record.get("content_authority_status") != "not_promoted":
        issue_counts["book_content_authority_status_invalid"] += 1
        safe_sample(uid, "book_content_authority_status_invalid", sample, level)
    validate_source_ref(record, uid, "raw_book_metadata", issue_counts, sample, level)
    return uid


def validate_sentence(record: Dict[str, Any], level: str, issue_counts: Counter, sample: List[Dict[str, str]]) -> Optional[str]:
    uid = str(record.get("sentence_uid", "MISSING_SENTENCE_UID"))
    required = [
        "sentence_uid",
        "book_uid",
        "level",
        "book_id",
        "page_number",
        "sentence_index_in_book",
        "text",
        "source_ref",
        "authority_status",
        "normalization_status",
        "content_authority_status",
        "review_status",
    ]
    require_fields(record, required, uid, issue_counts, sample, level)
    match = SENTENCE_UID_RE.match(uid)
    if not match:
        issue_counts["sentence_uid_pattern_invalid"] += 1
        safe_sample(uid, "sentence_uid_pattern_invalid", sample, level)
        return None
    uid_level, uid_book_id, _ = match.groups()
    expected_book_uid = f"raz_{uid_level}_{uid_book_id}"
    if uid_level != level or record.get("level") != level or str(record.get("book_id")) != uid_book_id or record.get("book_uid") != expected_book_uid:
        issue_counts["sentence_identity_mismatch"] += 1
        safe_sample(uid, "sentence_identity_mismatch", sample, level)
    text = record.get("text")
    if not isinstance(text, str) or not text.strip():
        issue_counts["sentence_text_missing_or_empty"] += 1
        safe_sample(uid, "sentence_text_missing_or_empty", sample, level)
    elif "\ufffd" in text:
        issue_counts["sentence_text_replacement_character"] += 1
        safe_sample(uid, "sentence_text_replacement_character", sample, level)
    if record.get("authority_status") != "candidate_only":
        issue_counts["sentence_authority_status_not_candidate_only"] += 1
        safe_sample(uid, "sentence_authority_status_not_candidate_only", sample, level)
    if record.get("normalization_status") != "candidate_normalized":
        issue_counts["sentence_normalization_status_invalid"] += 1
        safe_sample(uid, "sentence_normalization_status_invalid", sample, level)
    if record.get("content_authority_status") != "not_promoted":
        issue_counts["sentence_content_authority_status_invalid"] += 1
        safe_sample(uid, "sentence_content_authority_status_invalid", sample, level)
    validate_source_ref(record, uid, "raw_sentence_candidate", issue_counts, sample, level)
    return uid


def validate_unit(record: Dict[str, Any], level: str, unit_kind: str, sentence_uids: Set[str], issue_counts: Counter, sample: List[Dict[str, str]]) -> Optional[str]:
    uid_field = "page_unit_uid" if unit_kind == "page_units" else "reuse_unit_uid"
    uid = str(record.get(uid_field, f"MISSING_{uid_field.upper()}"))
    expected_re = PAGE_UID_RE if unit_kind == "page_units" else REUSE_UID_RE
    expected_layer = "raw_page_unit" if unit_kind == "page_units" else "raw_reuse_unit_candidate"
    required = [
        uid_field,
        "book_uid",
        "level",
        "book_id",
        "sentence_uids",
        "source_ref",
        "authority_status",
        "normalization_status",
        "content_authority_status",
        "review_status",
    ]
    if unit_kind == "page_units":
        required.append("page_number")
    else:
        required.extend(["page_range", "reuse_candidate_type"])
    require_fields(record, required, uid, issue_counts, sample, level)
    match = expected_re.match(uid)
    if not match:
        issue_counts[f"{unit_kind}_uid_pattern_invalid"] += 1
        safe_sample(uid, f"{unit_kind}_uid_pattern_invalid", sample, level)
        return None
    uid_level, uid_book_id, _ = match.groups()
    expected_book_uid = f"raz_{uid_level}_{uid_book_id}"
    if uid_level != level or record.get("level") != level or str(record.get("book_id")) != uid_book_id or record.get("book_uid") != expected_book_uid:
        issue_counts[f"{unit_kind}_identity_mismatch"] += 1
        safe_sample(uid, f"{unit_kind}_identity_mismatch", sample, level)
    refs = record.get("sentence_uids")
    if not isinstance(refs, list):
        issue_counts[f"{unit_kind}_sentence_uids_not_list"] += 1
        safe_sample(uid, f"{unit_kind}_sentence_uids_not_list", sample, level)
    else:
        unresolved = [ref for ref in refs if ref not in sentence_uids]
        if unresolved:
            issue_counts[f"{unit_kind}_unresolved_sentence_ref"] += len(unresolved)
            safe_sample(uid, f"{unit_kind}_unresolved_sentence_ref", sample, level)
    if record.get("authority_status") != "candidate_only":
        issue_counts[f"{unit_kind}_authority_status_not_candidate_only"] += 1
        safe_sample(uid, f"{unit_kind}_authority_status_not_candidate_only", sample, level)
    if record.get("normalization_status") != "candidate_normalized":
        issue_counts[f"{unit_kind}_normalization_status_invalid"] += 1
        safe_sample(uid, f"{unit_kind}_normalization_status_invalid", sample, level)
    if record.get("content_authority_status") != "not_promoted":
        issue_counts[f"{unit_kind}_content_authority_status_invalid"] += 1
        safe_sample(uid, f"{unit_kind}_content_authority_status_invalid", sample, level)
    validate_source_ref(record, uid, expected_layer, issue_counts, sample, level)
    return uid


def validate_collection(data: Dict[str, Any], kind: str, file_path: Path, issue_counts: Counter, sample: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    if data.get("schema_version") != EXPECTED_SCHEMA_VERSIONS[kind]:
        issue_counts[f"schema_version_mismatch:{kind}"] += 1
        safe_sample(file_path.name, f"schema_version_mismatch:{kind}", sample)
    records = data.get("records")
    if not isinstance(records, list):
        issue_counts[f"records_not_list:{kind}"] += 1
        safe_sample(file_path.name, f"records_not_list:{kind}", sample)
        return []
    return [item for item in records if isinstance(item, dict)]


def validate_normalized(derived_root: Path, reports_dir: Path, build_summary_path: Optional[Path]) -> Dict[str, Any]:
    issue_counts: Counter = Counter()
    forbidden_key_counts: Counter = Counter()
    forbidden_status_counts: Counter = Counter()
    sample: List[Dict[str, str]] = []
    level_counts: Dict[str, Dict[str, int]] = {}
    missing_files: List[str] = []
    parse_failures: List[Dict[str, str]] = []
    actual_totals: Counter = Counter()

    build_summary: Optional[Dict[str, Any]] = None
    if build_summary_path and build_summary_path.exists():
        try:
            build_summary = read_json(build_summary_path)
        except Exception as exc:
            issue_counts["build_summary_parse_failure"] += 1
            parse_failures.append({"filename": str(build_summary_path), "error_type": type(exc).__name__})

    for level in EXPECTED_LEVELS:
        level_dir = derived_root / f"Level_{level}" / "normalized"
        level_payloads: Dict[str, Dict[str, Any]] = {}
        for kind, pattern in NORMALIZED_FILENAMES.items():
            path = level_dir / pattern.format(level=level)
            if not path.exists():
                missing_files.append(str(path))
                issue_counts[f"missing_file:{kind}"] += 1
                continue
            try:
                payload = read_json(path)
                level_payloads[kind] = payload
                count_forbidden_keys(payload, forbidden_key_counts)
                has_forbidden_status(payload, forbidden_status_counts)
            except Exception as exc:
                parse_failures.append({"level": level, "kind": kind, "filename": path.name, "error_type": type(exc).__name__})
                issue_counts[f"parse_failure:{kind}"] += 1

        books = validate_collection(level_payloads.get("books", {}), "books", level_dir / NORMALIZED_FILENAMES["books"].format(level=level), issue_counts, sample)
        sentences = validate_collection(level_payloads.get("sentences", {}), "sentences", level_dir / NORMALIZED_FILENAMES["sentences"].format(level=level), issue_counts, sample)
        page_units = validate_collection(level_payloads.get("page_units", {}), "page_units", level_dir / NORMALIZED_FILENAMES["page_units"].format(level=level), issue_counts, sample)
        reuse_units = validate_collection(level_payloads.get("reuse_units", {}), "reuse_units", level_dir / NORMALIZED_FILENAMES["reuse_units"].format(level=level), issue_counts, sample)

        book_uids: Set[str] = set()
        sentence_uids: Set[str] = set()
        for book in books:
            uid = validate_book(book, level, issue_counts, sample)
            if uid:
                if uid in book_uids:
                    issue_counts["duplicate_book_uid"] += 1
                    safe_sample(uid, "duplicate_book_uid", sample, level)
                book_uids.add(uid)
        for sentence in sentences:
            uid = validate_sentence(sentence, level, issue_counts, sample)
            if uid:
                if uid in sentence_uids:
                    issue_counts["duplicate_sentence_uid"] += 1
                    safe_sample(uid, "duplicate_sentence_uid", sample, level)
                sentence_uids.add(uid)
                if sentence.get("book_uid") not in book_uids:
                    issue_counts["sentence_book_ref_unresolved"] += 1
                    safe_sample(uid, "sentence_book_ref_unresolved", sample, level)
        for unit in page_units:
            uid = validate_unit(unit, level, "page_units", sentence_uids, issue_counts, sample)
            if uid and unit.get("book_uid") not in book_uids:
                issue_counts["page_unit_book_ref_unresolved"] += 1
                safe_sample(uid, "page_unit_book_ref_unresolved", sample, level)
        for unit in reuse_units:
            uid = validate_unit(unit, level, "reuse_units", sentence_uids, issue_counts, sample)
            if uid and unit.get("book_uid") not in book_uids:
                issue_counts["reuse_unit_book_ref_unresolved"] += 1
                safe_sample(uid, "reuse_unit_book_ref_unresolved", sample, level)

        level_counts[level] = {
            "book_count": len(books),
            "sentence_count": len(sentences),
            "page_unit_count": len(page_units),
            "reuse_unit_count": len(reuse_units),
        }
        actual_totals.update({
            "book_count": len(books),
            "sentence_count": len(sentences),
            "page_unit_count": len(page_units),
            "reuse_unit_count": len(reuse_units),
        })

    blockers: List[str] = []
    warnings: List[str] = []
    if missing_files:
        blockers.append("missing_normalized_files")
    if parse_failures:
        blockers.append("normalized_file_parse_failures")
    if actual_totals["book_count"] != EXPECTED_BOOK_COUNT:
        blockers.append("normalized_book_count_mismatch_expected_1959")
    if actual_totals["sentence_count"] <= 0:
        blockers.append("normalized_sentence_count_zero")
    if issue_counts:
        blockers.append("normalized_contract_violations")
    if forbidden_key_counts:
        blockers.append("forbidden_payload_keys_in_normalized_artifacts")
    if forbidden_status_counts:
        blockers.append("forbidden_status_values_in_normalized_artifacts")

    expected_from_build_summary: Dict[str, Any] = {}
    if build_summary:
        summary_counts = build_summary.get("total_counts") if isinstance(build_summary.get("total_counts"), dict) else {}
        expected_from_build_summary = {
            "book_count": summary_counts.get("normalized_book_count"),
            "sentence_count": summary_counts.get("normalized_sentence_count"),
            "page_unit_count": summary_counts.get("normalized_page_unit_count"),
            "reuse_unit_count": summary_counts.get("normalized_reuse_unit_count"),
        }
        for key, expected_value in expected_from_build_summary.items():
            if isinstance(expected_value, int) and actual_totals.get(key, None) != expected_value:
                blockers.append(f"count_mismatch_against_build_summary:{key}")
        extraction_paths = build_summary.get("sentence_extraction_path_counts") if isinstance(build_summary.get("sentence_extraction_path_counts"), dict) else {}
        if extraction_paths and next(iter(extraction_paths.keys())) != "$.cleaned_candidate":
            blockers.append("dominant_sentence_extraction_path_not_cleaned_candidate")
    else:
        warnings.append("build_summary_not_available_for_count_reconciliation")

    status = "PASS" if not blockers else "BLOCKED"
    report = {
        "task_id": "RAZ-AW-S3C2_NormalizedValidatorQA",
        "report_type": "raz_aw_normalized_validator_qa_report",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "derived_root": str(derived_root),
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "text_bearing_derived_artifacts_committed_to_github": False,
        "content_authority_promotion": False,
        "tag_authority_promotion": False,
        "actual_totals": dict(actual_totals),
        "expected_from_build_summary": expected_from_build_summary,
        "level_counts": level_counts,
        "issue_counts": dict(sorted(issue_counts.items())),
        "forbidden_key_counts": dict(sorted(forbidden_key_counts.items())),
        "forbidden_status_counts": dict(sorted(forbidden_status_counts.items())),
        "missing_file_count": len(missing_files),
        "missing_files_sample": missing_files[:20],
        "parse_failure_count": len(parse_failures),
        "parse_failures_sample": parse_failures[:20],
        "sample_issues": sample,
        "warnings": warnings,
        "blockers": sorted(set(blockers)),
    }
    schema_summary = {
        "task_id": "RAZ-AW-S3C2_NormalizedValidatorQA",
        "report_type": "raz_aw_normalized_schema_validation_summary",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "expected_schema_versions": EXPECTED_SCHEMA_VERSIONS,
        "issue_counts": dict(sorted(issue_counts.items())),
        "missing_file_count": len(missing_files),
        "parse_failure_count": len(parse_failures),
        "blockers": sorted(set(blockers)),
    }
    reference_summary = {
        "task_id": "RAZ-AW-S3C2_NormalizedValidatorQA",
        "report_type": "raz_aw_normalized_reference_validation_summary",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "actual_totals": dict(actual_totals),
        "expected_from_build_summary": expected_from_build_summary,
        "reference_issue_counts": {k: v for k, v in sorted(issue_counts.items()) if "ref" in k or "source" in k or "identity" in k or "uid" in k},
        "blockers": sorted(set(blockers)),
    }
    safety_report = {
        "task_id": "RAZ-AW-S3C2_NormalizedValidatorQA",
        "report_type": "raz_aw_normalized_validator_safety_report",
        "status": "PASS" if not forbidden_key_counts and not forbidden_status_counts else "BLOCKED",
        "sanitized": True,
        "contains_text_values": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "forbidden_key_counts": dict(sorted(forbidden_key_counts.items())),
        "forbidden_status_counts": dict(sorted(forbidden_status_counts.items())),
        "text_bearing_derived_artifacts_committed_to_github": False,
        "content_authority_promotion": False,
        "tag_authority_promotion": False,
    }
    for output in (report, schema_summary, reference_summary, safety_report):
        # Safety self-check: do not allow exact raw text-bearing keys in sanitized reports.
        hits = []
        def scan_keys(value: Any, prefix: str = "$") -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {"text", "raw_text", "page_text", "full_raw_json"}:
                        hits.append(f"{prefix}.{key}")
                    scan_keys(child, f"{prefix}.{key}")
            elif isinstance(value, list):
                for child in value:
                    scan_keys(child, f"{prefix}[]")
        scan_keys(output)
        if hits:
            raise ValueError(f"unsafe_report_key_emitted: {hits[:5]}")
    write_json(reports_dir / "raz_aw_normalized_validator_qa_report.json", report)
    write_json(reports_dir / "raz_aw_normalized_schema_validation_summary.json", schema_summary)
    write_json(reports_dir / "raz_aw_normalized_reference_validation_summary.json", reference_summary)
    write_json(reports_dir / "raz_aw_normalized_validator_safety_report.json", safety_report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate RAZ A-W normalized candidate artifacts.")
    parser.add_argument("--derived-root", default="raz_output_jsons/derived", help="Derived output root containing Level_<LEVEL>/normalized folders.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Sanitized report output directory.")
    parser.add_argument("--build-summary", default="reports/raz/raz_aw_normalized_build_summary.json", help="Sanitized normalized build summary for count reconciliation.")
    args = parser.parse_args()
    derived_root = Path(args.derived_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    build_summary = Path(args.build_summary).resolve() if args.build_summary else None
    if not derived_root.exists() or not derived_root.is_dir():
        payload = {
            "task_id": "RAZ-AW-S3C2_NormalizedValidatorQA",
            "report_type": "raz_aw_normalized_validator_qa_report",
            "status": "BLOCKED",
            "sanitized": True,
            "contains_text_values": False,
            "derived_root": str(derived_root),
            "blockers": ["derived_root_missing_or_not_directory"],
        }
        write_json(reports_dir / "raz_aw_normalized_validator_qa_report.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    report = validate_normalized(derived_root, reports_dir, build_summary)
    print(json.dumps({
        "status": report["status"],
        "actual_totals": report["actual_totals"],
        "issue_counts": report["issue_counts"],
        "warnings": report["warnings"],
        "blockers": report["blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
