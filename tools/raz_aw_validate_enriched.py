#!/usr/bin/env python3
"""Validate RAZ A-W enriched candidate artifacts.

S3D2 contract:
- Reads local/Drive-derived enriched artifacts under raz_output_jsons/derived.
- Emits only sanitized validation reports to reports/raz.
- Does not emit sentence text values to GitHub reports.
- Does not promote content/tag/authority status.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
EXPECTED_COUNTS = {
    "book_count": 1959,
    "sentence_count": 201993,
    "unit_count": 41964,
}
EXPECTED_SCHEMA_VERSIONS = {
    "books": "raz_enriched_books.v1",
    "sentences": "raz_enriched_sentences.v1",
    "units": "raz_enriched_units.v1",
}
ENRICHED_FILENAMES = {
    "books": "raz_{level}_enriched_books.json",
    "sentences": "raz_{level}_enriched_sentences.json",
    "units": "raz_{level}_enriched_units.json",
}
BOOK_UID_RE = re.compile(r"^raz_([A-W])_([0-9]+)$")
SENTENCE_UID_RE = re.compile(r"^raz_([A-W])_([0-9]+)_s([0-9]{4})$")
UNIT_UID_RE = re.compile(r"^raz_([A-W])_([0-9]+)_([pr])([0-9]{4})$")
FORBIDDEN_STATUS_VALUES = {
    "approved",
    "promoted",
    "final_authority",
    "learner_facing_approved",
}
FORBIDDEN_REPORT_KEYS = {
    "text",
    "raw_text",
    "page_text",
    "full_raw_json",
    "sentence_candidates",
    "audio_trace",
    "word_trace",
}
ALLOWED_AUTHORITY_LINKAGE_STATUS = {"candidate_only", "not_evaluated"}
ALLOWED_REVIEW_STATUS = {"pending", "needs_review", "rejected"}
ALLOWED_VALIDATION_STATUS = {"not_evaluated", "pass", "pass_with_warnings", "fail"}
ALLOWED_LENGTH_BUCKET = {"not_evaluated", "very_short", "short", "medium", "long", "very_long"}
ALLOWED_COMPLEXITY_BUCKET = {"not_evaluated", "very_low", "low", "medium", "high", "very_high"}
ALLOWED_TERMINAL_PUNCTUATION = {".", "?", "!", "none", "other"}
ALLOWED_UNIT_TYPE = {"page_unit", "reuse_unit", "sentence_cluster"}
ALLOWED_USE_CASES = {"reading", "dialogue", "exercise", "assessment", "review"}


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("top_level_json_is_not_object")
    return data


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def records(payload: Dict[str, Any], kind: str, issue_counts: Counter, sample: List[Dict[str, str]], filename: str) -> List[Dict[str, Any]]:
    if payload.get("schema_version") != EXPECTED_SCHEMA_VERSIONS[kind]:
        issue_counts[f"schema_version_mismatch:{kind}"] += 1
        add_sample(sample, filename, f"schema_version_mismatch:{kind}")
    value = payload.get("records")
    if not isinstance(value, list):
        issue_counts[f"records_not_list:{kind}"] += 1
        add_sample(sample, filename, f"records_not_list:{kind}")
        return []
    return [item for item in value if isinstance(item, dict)]


def add_sample(sample: List[Dict[str, str]], uid: Any, issue: str, level: Optional[str] = None) -> None:
    if len(sample) >= 40:
        return
    item = {"uid": str(uid), "issue": issue}
    if level:
        item["level"] = level
    sample.append(item)


def require_fields(record: Dict[str, Any], fields: Iterable[str], uid: str, issue_counts: Counter, sample: List[Dict[str, str]], level: str) -> None:
    for field in fields:
        if field not in record:
            issue_counts[f"missing_field:{field}"] += 1
            add_sample(sample, uid, f"missing_field:{field}", level)


def scan_forbidden_status(value: Any, counter: Counter) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, str) and child in FORBIDDEN_STATUS_VALUES:
                counter[f"{key}:{child}"] += 1
            scan_forbidden_status(child, counter)
    elif isinstance(value, list):
        for item in value:
            scan_forbidden_status(item, counter)


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


def is_number_between(value: Any, low: float, high: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and low <= float(value) <= high


def validate_book(book: Dict[str, Any], level: str, issue_counts: Counter, sample: List[Dict[str, str]]) -> Optional[str]:
    uid = str(book.get("book_uid", "MISSING_BOOK_UID"))
    require_fields(book, [
        "book_uid", "level", "book_id", "title", "sentence_count", "page_unit_count", "reuse_unit_count",
        "estimated_text_complexity_bucket", "candidate_theme_tags", "candidate_content_unit_tags",
        "candidate_pedagogical_tags", "authority_linkage_status", "enrichment_status", "review_status", "validation_status",
    ], uid, issue_counts, sample, level)
    match = BOOK_UID_RE.match(uid)
    if not match:
        issue_counts["book_uid_pattern_invalid"] += 1
        add_sample(sample, uid, "book_uid_pattern_invalid", level)
        return None
    uid_level, uid_book_id = match.groups()
    if uid_level != level or book.get("level") != level or str(book.get("book_id")) != uid_book_id:
        issue_counts["book_identity_mismatch"] += 1
        add_sample(sample, uid, "book_identity_mismatch", level)
    if not isinstance(book.get("title"), str) or not book.get("title"):
        issue_counts["book_title_missing_or_empty"] += 1
        add_sample(sample, uid, "book_title_missing_or_empty", level)
    for count_field in ("sentence_count", "page_unit_count", "reuse_unit_count"):
        if not isinstance(book.get(count_field), int) or book.get(count_field) < 0:
            issue_counts[f"book_{count_field}_invalid"] += 1
            add_sample(sample, uid, f"book_{count_field}_invalid", level)
    if book.get("estimated_text_complexity_bucket") not in ALLOWED_COMPLEXITY_BUCKET:
        issue_counts["book_complexity_bucket_invalid"] += 1
        add_sample(sample, uid, "book_complexity_bucket_invalid", level)
    for tag_field in ("candidate_theme_tags", "candidate_content_unit_tags", "candidate_pedagogical_tags"):
        if not isinstance(book.get(tag_field), list) or any(not isinstance(item, str) or not item for item in book.get(tag_field, [])):
            issue_counts[f"book_{tag_field}_invalid"] += 1
            add_sample(sample, uid, f"book_{tag_field}_invalid", level)
    validate_status_fields(book, uid, level, issue_counts, sample, prefix="book")
    return uid


def validate_status_fields(record: Dict[str, Any], uid: str, level: str, issue_counts: Counter, sample: List[Dict[str, str]], prefix: str) -> None:
    if record.get("authority_linkage_status") not in ALLOWED_AUTHORITY_LINKAGE_STATUS:
        issue_counts[f"{prefix}_authority_linkage_status_invalid"] += 1
        add_sample(sample, uid, f"{prefix}_authority_linkage_status_invalid", level)
    if record.get("enrichment_status") != "candidate_enriched":
        issue_counts[f"{prefix}_enrichment_status_invalid"] += 1
        add_sample(sample, uid, f"{prefix}_enrichment_status_invalid", level)
    if record.get("review_status") not in ALLOWED_REVIEW_STATUS:
        issue_counts[f"{prefix}_review_status_invalid"] += 1
        add_sample(sample, uid, f"{prefix}_review_status_invalid", level)
    if record.get("validation_status") not in ALLOWED_VALIDATION_STATUS:
        issue_counts[f"{prefix}_validation_status_invalid"] += 1
        add_sample(sample, uid, f"{prefix}_validation_status_invalid", level)


def validate_sentence(sentence: Dict[str, Any], level: str, book_uids: Set[str], issue_counts: Counter, sample: List[Dict[str, str]]) -> Optional[str]:
    uid = str(sentence.get("sentence_uid", "MISSING_SENTENCE_UID"))
    require_fields(sentence, [
        "sentence_uid", "book_uid", "level", "text", "normalized_token_count", "candidate_vocab_refs",
        "candidate_grammar_refs", "candidate_pattern_refs", "sentence_length_bucket", "punctuation_profile",
        "dialogue_candidate_flag", "reading_sentence_candidate_flag", "authority_linkage_status", "enrichment_status",
        "review_status", "validation_status",
    ], uid, issue_counts, sample, level)
    match = SENTENCE_UID_RE.match(uid)
    if not match:
        issue_counts["sentence_uid_pattern_invalid"] += 1
        add_sample(sample, uid, "sentence_uid_pattern_invalid", level)
        return None
    uid_level, uid_book_id, _ = match.groups()
    expected_book_uid = f"raz_{uid_level}_{uid_book_id}"
    if uid_level != level or sentence.get("level") != level or sentence.get("book_uid") != expected_book_uid:
        issue_counts["sentence_identity_mismatch"] += 1
        add_sample(sample, uid, "sentence_identity_mismatch", level)
    if sentence.get("book_uid") not in book_uids:
        issue_counts["sentence_book_ref_unresolved"] += 1
        add_sample(sample, uid, "sentence_book_ref_unresolved", level)
    if not isinstance(sentence.get("text"), str) or not sentence.get("text").strip():
        issue_counts["sentence_text_missing_or_empty"] += 1
        add_sample(sample, uid, "sentence_text_missing_or_empty", level)
    if not isinstance(sentence.get("normalized_token_count"), int) or sentence.get("normalized_token_count") < 0:
        issue_counts["sentence_token_count_invalid"] += 1
        add_sample(sample, uid, "sentence_token_count_invalid", level)
    for refs_field in ("candidate_vocab_refs", "candidate_grammar_refs", "candidate_pattern_refs"):
        refs = sentence.get(refs_field)
        if not isinstance(refs, list):
            issue_counts[f"sentence_{refs_field}_not_list"] += 1
            add_sample(sample, uid, f"sentence_{refs_field}_not_list", level)
        else:
            for ref in refs:
                if not isinstance(ref, dict) or ref.get("authority_status") != "candidate_only":
                    issue_counts[f"sentence_{refs_field}_invalid_candidate_ref"] += 1
                    add_sample(sample, uid, f"sentence_{refs_field}_invalid_candidate_ref", level)
                    break
    if sentence.get("sentence_length_bucket") not in ALLOWED_LENGTH_BUCKET:
        issue_counts["sentence_length_bucket_invalid"] += 1
        add_sample(sample, uid, "sentence_length_bucket_invalid", level)
    profile = sentence.get("punctuation_profile")
    if not isinstance(profile, dict) or profile.get("terminal_punctuation") not in ALLOWED_TERMINAL_PUNCTUATION:
        issue_counts["sentence_punctuation_profile_invalid"] += 1
        add_sample(sample, uid, "sentence_punctuation_profile_invalid", level)
    else:
        for bool_key in ("contains_comma", "contains_question_mark", "contains_exclamation_mark", "contains_quote_mark"):
            if not isinstance(profile.get(bool_key), bool):
                issue_counts[f"sentence_punctuation_{bool_key}_invalid"] += 1
                add_sample(sample, uid, f"sentence_punctuation_{bool_key}_invalid", level)
    if not isinstance(sentence.get("dialogue_candidate_flag"), bool):
        issue_counts["sentence_dialogue_flag_invalid"] += 1
        add_sample(sample, uid, "sentence_dialogue_flag_invalid", level)
    if not isinstance(sentence.get("reading_sentence_candidate_flag"), bool):
        issue_counts["sentence_reading_flag_invalid"] += 1
        add_sample(sample, uid, "sentence_reading_flag_invalid", level)
    validate_status_fields(sentence, uid, level, issue_counts, sample, prefix="sentence")
    return uid


def validate_unit(unit: Dict[str, Any], level: str, book_uids: Set[str], sentence_uids: Set[str], issue_counts: Counter, sample: List[Dict[str, str]]) -> Optional[str]:
    uid = str(unit.get("unit_uid", "MISSING_UNIT_UID"))
    require_fields(unit, [
        "unit_uid", "unit_type", "book_uid", "level", "sentence_uids", "unit_sentence_count", "unit_token_count",
        "candidate_use_cases", "candidate_reuse_tags", "reading_usefulness_score_candidate",
        "dialogue_usefulness_score_candidate", "exercise_usefulness_score_candidate", "authority_linkage_status",
        "enrichment_status", "review_status", "validation_status",
    ], uid, issue_counts, sample, level)
    match = UNIT_UID_RE.match(uid)
    if not match:
        issue_counts["unit_uid_pattern_invalid"] += 1
        add_sample(sample, uid, "unit_uid_pattern_invalid", level)
        return None
    uid_level, uid_book_id, kind, _ = match.groups()
    expected_book_uid = f"raz_{uid_level}_{uid_book_id}"
    expected_unit_type = "page_unit" if kind == "p" else "reuse_unit"
    if uid_level != level or unit.get("level") != level or unit.get("book_uid") != expected_book_uid:
        issue_counts["unit_identity_mismatch"] += 1
        add_sample(sample, uid, "unit_identity_mismatch", level)
    if unit.get("book_uid") not in book_uids:
        issue_counts["unit_book_ref_unresolved"] += 1
        add_sample(sample, uid, "unit_book_ref_unresolved", level)
    if unit.get("unit_type") not in ALLOWED_UNIT_TYPE or unit.get("unit_type") != expected_unit_type:
        issue_counts["unit_type_invalid"] += 1
        add_sample(sample, uid, "unit_type_invalid", level)
    refs = unit.get("sentence_uids")
    if not isinstance(refs, list):
        issue_counts["unit_sentence_uids_not_list"] += 1
        add_sample(sample, uid, "unit_sentence_uids_not_list", level)
        refs = []
    else:
        unresolved = [ref for ref in refs if ref not in sentence_uids]
        if unresolved:
            issue_counts["unit_sentence_ref_unresolved"] += len(unresolved)
            add_sample(sample, uid, "unit_sentence_ref_unresolved", level)
    if unit.get("unit_sentence_count") != len(refs):
        issue_counts["unit_sentence_count_mismatch"] += 1
        add_sample(sample, uid, "unit_sentence_count_mismatch", level)
    if not isinstance(unit.get("unit_token_count"), int) or unit.get("unit_token_count") < 0:
        issue_counts["unit_token_count_invalid"] += 1
        add_sample(sample, uid, "unit_token_count_invalid", level)
    use_cases = unit.get("candidate_use_cases")
    if not isinstance(use_cases, list) or any(item not in ALLOWED_USE_CASES for item in use_cases):
        issue_counts["unit_candidate_use_cases_invalid"] += 1
        add_sample(sample, uid, "unit_candidate_use_cases_invalid", level)
    tags = unit.get("candidate_reuse_tags")
    if not isinstance(tags, list) or any(not isinstance(item, str) or not item for item in tags):
        issue_counts["unit_candidate_reuse_tags_invalid"] += 1
        add_sample(sample, uid, "unit_candidate_reuse_tags_invalid", level)
    for score_field in ("reading_usefulness_score_candidate", "dialogue_usefulness_score_candidate", "exercise_usefulness_score_candidate"):
        if not is_number_between(unit.get(score_field), 0, 1):
            issue_counts[f"unit_{score_field}_invalid"] += 1
            add_sample(sample, uid, f"unit_{score_field}_invalid", level)
    validate_status_fields(unit, uid, level, issue_counts, sample, prefix="unit")
    return uid


def validate(derived_root: Path, reports_dir: Path, build_summary_path: Path) -> Dict[str, Any]:
    issue_counts: Counter = Counter()
    forbidden_status_counts: Counter = Counter()
    sample: List[Dict[str, str]] = []
    level_counts: Dict[str, Dict[str, int]] = {}
    totals: Counter = Counter()
    missing_files: List[str] = []
    parse_failures: List[Dict[str, str]] = []

    build_summary = None
    if build_summary_path.exists():
        try:
            build_summary = read_json(build_summary_path)
        except Exception as exc:
            parse_failures.append({"filename": str(build_summary_path), "error_type": type(exc).__name__})
            issue_counts["build_summary_parse_failure"] += 1
    else:
        issue_counts["build_summary_missing"] += 1

    for level in EXPECTED_LEVELS:
        level_dir = derived_root / f"Level_{level}" / "enriched"
        payloads: Dict[str, Dict[str, Any]] = {}
        for kind, pattern in ENRICHED_FILENAMES.items():
            path = level_dir / pattern.format(level=level)
            if not path.exists():
                missing_files.append(str(path))
                issue_counts[f"missing_file:{kind}"] += 1
                continue
            try:
                payload = read_json(path)
                payloads[kind] = payload
                scan_forbidden_status(payload, forbidden_status_counts)
            except Exception as exc:
                parse_failures.append({"level": level, "kind": kind, "filename": path.name, "error_type": type(exc).__name__})
                issue_counts[f"parse_failure:{kind}"] += 1

        book_records = records(payloads.get("books", {}), "books", issue_counts, sample, f"{level}:books")
        sentence_records = records(payloads.get("sentences", {}), "sentences", issue_counts, sample, f"{level}:sentences")
        unit_records = records(payloads.get("units", {}), "units", issue_counts, sample, f"{level}:units")
        book_uids: Set[str] = set()
        sentence_uids: Set[str] = set()

        for book in book_records:
            uid = validate_book(book, level, issue_counts, sample)
            if uid:
                if uid in book_uids:
                    issue_counts["duplicate_book_uid"] += 1
                    add_sample(sample, uid, "duplicate_book_uid", level)
                book_uids.add(uid)
        for sentence in sentence_records:
            uid = validate_sentence(sentence, level, book_uids, issue_counts, sample)
            if uid:
                if uid in sentence_uids:
                    issue_counts["duplicate_sentence_uid"] += 1
                    add_sample(sample, uid, "duplicate_sentence_uid", level)
                sentence_uids.add(uid)
        for unit in unit_records:
            validate_unit(unit, level, book_uids, sentence_uids, issue_counts, sample)

        counts = {
            "book_count": len(book_records),
            "sentence_count": len(sentence_records),
            "unit_count": len(unit_records),
        }
        level_counts[level] = counts
        totals.update(counts)

    blockers: List[str] = []
    warnings: List[str] = []
    if missing_files:
        blockers.append("missing_enriched_files")
    if parse_failures:
        blockers.append("enriched_file_parse_failures")
    for key, expected in EXPECTED_COUNTS.items():
        if totals[key] != expected:
            blockers.append(f"{key}_mismatch")
    if issue_counts:
        blockers.append("enriched_contract_violations")
    if forbidden_status_counts:
        blockers.append("forbidden_status_values_in_enriched_artifacts")

    expected_from_build_summary: Dict[str, Any] = {}
    if isinstance(build_summary, dict):
        actual_counts = build_summary.get("actual_counts") if isinstance(build_summary.get("actual_counts"), dict) else {}
        expected_from_build_summary = {
            "book_count": actual_counts.get("book_count"),
            "sentence_count": actual_counts.get("sentence_count"),
            "unit_count": actual_counts.get("unit_count"),
        }
        for key, expected in expected_from_build_summary.items():
            if isinstance(expected, int) and totals[key] != expected:
                blockers.append(f"count_mismatch_against_build_summary:{key}")
    else:
        warnings.append("build_summary_not_available_for_count_reconciliation")

    status = "PASS" if not blockers else "BLOCKED"
    report = {
        "task_id": "RAZ-AW-S3D2_EnrichedValidatorQA",
        "report_type": "raz_aw_enriched_validator_qa_report",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "derived_root": str(derived_root),
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "text_bearing_enriched_artifacts_committed_to_github": False,
        "authority_promotion": False,
        "tag_authority_promotion": False,
        "generation_approved": False,
        "runtime_api_integration": False,
        "actual_counts": dict(totals),
        "expected_counts": EXPECTED_COUNTS,
        "expected_from_build_summary": expected_from_build_summary,
        "level_counts": level_counts,
        "issue_counts": dict(sorted(issue_counts.items())),
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
        "task_id": "RAZ-AW-S3D2_EnrichedValidatorQA",
        "report_type": "raz_aw_enriched_schema_validation_summary",
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
        "task_id": "RAZ-AW-S3D2_EnrichedValidatorQA",
        "report_type": "raz_aw_enriched_reference_validation_summary",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "actual_counts": dict(totals),
        "expected_from_build_summary": expected_from_build_summary,
        "reference_issue_counts": {k: v for k, v in sorted(issue_counts.items()) if "ref" in k or "identity" in k or "uid" in k or "count" in k},
        "blockers": sorted(set(blockers)),
    }
    safety_report = {
        "task_id": "RAZ-AW-S3D2_EnrichedValidatorQA",
        "report_type": "raz_aw_enriched_validator_safety_report",
        "status": "PASS" if not forbidden_status_counts else "BLOCKED",
        "sanitized": True,
        "contains_text_values": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "forbidden_status_counts": dict(sorted(forbidden_status_counts.items())),
        "text_bearing_enriched_artifacts_committed_to_github": False,
        "authority_promotion": False,
        "tag_authority_promotion": False,
        "generation_approved": False,
    }
    for payload in (report, schema_summary, reference_summary, safety_report):
        hits = scan_report_keys(payload)
        if hits:
            raise ValueError(f"unsafe_report_key_emitted: {hits[:5]}")
    write_json(reports_dir / "raz_aw_enriched_validator_qa_report.json", report)
    write_json(reports_dir / "raz_aw_enriched_schema_validation_summary.json", schema_summary)
    write_json(reports_dir / "raz_aw_enriched_reference_validation_summary.json", reference_summary)
    write_json(reports_dir / "raz_aw_enriched_validator_safety_report.json", safety_report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate RAZ A-W enriched candidate artifacts.")
    parser.add_argument("--derived-root", default="raz_output_jsons/derived", help="Derived root containing Level_<LEVEL>/enriched folders.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Sanitized GitHub report directory.")
    parser.add_argument("--build-summary", default="reports/raz/raz_aw_enriched_build_summary.json", help="Sanitized enriched build summary for count reconciliation.")
    args = parser.parse_args()
    derived_root = Path(args.derived_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    build_summary = Path(args.build_summary).resolve()
    if not derived_root.exists() or not derived_root.is_dir():
        payload = {
            "task_id": "RAZ-AW-S3D2_EnrichedValidatorQA",
            "status": "BLOCKED",
            "sanitized": True,
            "contains_text_values": False,
            "blockers": ["derived_root_missing_or_not_directory"],
            "derived_root": str(derived_root),
        }
        write_json(reports_dir / "raz_aw_enriched_validator_qa_report.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    report = validate(derived_root, reports_dir, build_summary)
    print(json.dumps({
        "status": report["status"],
        "actual_counts": report["actual_counts"],
        "issue_counts": report["issue_counts"],
        "warnings": report["warnings"],
        "blockers": report["blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
