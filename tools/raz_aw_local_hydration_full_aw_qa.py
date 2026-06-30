#!/usr/bin/env python3
"""Local RAZ A-W full hydration QA.

This tool reads all A-W raw JSON files from a local raz_output_jsons mirror,
shallow-parses every matching raw JSON file, and writes sanitized QA reports.
It does not emit sentence/page/audio raw text and does not modify raw files.

Default usage from repository root:
    python tools/raz_aw_local_hydration_full_aw_qa.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
EXPECTED_RAW_LEVEL_FILE_COUNT = 1959
RAW_FILE_RE = re.compile(r"^raz_([A-W])_([0-9]+)_audio_timeline_extract\.json$")
FORBIDDEN_OUTPUT_KEYS = {
    "sentence_candidates",
    "page_units",
    "reuse_unit_candidates",
    "legacy_story_sentences",
    "text",
    "sentence",
    "sentences",
    "page_text",
    "raw_text",
    "audio_trace",
    "word_trace",
    "audio_timeline",
}


def read_json(path: Path) -> Tuple[str, Optional[Dict[str, Any]], Optional[str]]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except Exception as exc:
        return "FAIL", None, f"{type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return "FAIL", None, "top_level_json_is_not_object"
    return "PASS", data, None


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scalar(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return None


def count_list(data: Dict[str, Any], key: str) -> Optional[int]:
    value = data.get(key)
    return len(value) if isinstance(value, list) else None


def shallow_parse(path: Path, raw_root: Path, expected_level: str, book_id_from_filename: str) -> Dict[str, Any]:
    status, data, error = read_json(path)
    record: Dict[str, Any] = {
        "level": expected_level,
        "book_id_from_filename": book_id_from_filename,
        "filename": path.name,
        "relative_path": path.relative_to(raw_root).as_posix(),
        "size_bytes": path.stat().st_size,
        "json_parse_status": status,
        "raw_text_in_report": False,
    }
    if error:
        record["json_parse_error"] = error
    if data is None:
        return record

    book = data.get("book_metadata") if isinstance(data.get("book_metadata"), dict) else {}
    clean = data.get("clean_summary") if isinstance(data.get("clean_summary"), dict) else {}
    record.update({
        "source_type": scalar(data.get("source_type")),
        "extraction_method": scalar(data.get("extraction_method")),
        "extractor_version": scalar(data.get("extractor_version")),
        "level_from_json": scalar(book.get("level") or clean.get("level")),
        "book_id": scalar(book.get("book_id") or clean.get("book_id")),
        "book_title": scalar(book.get("title") or clean.get("title")),
        "story_page_start": scalar(book.get("story_page_start")),
        "story_page_end": scalar(book.get("story_page_end")),
        "story_page_count": scalar(book.get("story_page_count") or clean.get("actual_story_page_count")),
        "sentence_candidate_count": count_list(data, "sentence_candidates"),
        "page_unit_count": count_list(data, "page_units"),
        "reuse_candidate_count": count_list(data, "reuse_unit_candidates"),
        "excluded_item_count": count_list(data, "excluded_items"),
        "legacy_story_sentence_count": count_list(data, "legacy_story_sentences"),
        "authority_status": scalar(clean.get("authority_status")),
        "generated_content": clean.get("generated_content") if isinstance(clean.get("generated_content"), bool) else None,
        "raw_audio_fields_preserved": clean.get("raw_audio_fields_preserved") if isinstance(clean.get("raw_audio_fields_preserved"), bool) else None,
        "final_should_remove_audio_fields": clean.get("final_should_remove_audio_fields") if isinstance(clean.get("final_should_remove_audio_fields"), bool) else None,
    })
    return {key: value for key, value in record.items() if value is not None}


def find_all_raw_files(raw_root: Path) -> Tuple[Dict[str, List[Tuple[int, Path]]], List[Dict[str, Any]]]:
    by_level: Dict[str, List[Tuple[int, Path]]] = {level: [] for level in EXPECTED_LEVELS}
    ignored_json_files: List[Dict[str, Any]] = []

    for level in EXPECTED_LEVELS:
        level_dir = raw_root / f"Level_{level}"
        if not level_dir.exists():
            continue
        for path in level_dir.glob("*.json"):
            match = RAW_FILE_RE.match(path.name)
            if not match:
                ignored_json_files.append({
                    "level_folder": level,
                    "filename": path.name,
                    "relative_path": path.relative_to(raw_root).as_posix(),
                    "reason": "filename_does_not_match_raw_audio_timeline_pattern",
                })
                continue
            filename_level, book_id = match.groups()
            if filename_level != level:
                ignored_json_files.append({
                    "level_folder": level,
                    "filename": path.name,
                    "relative_path": path.relative_to(raw_root).as_posix(),
                    "reason": "filename_level_does_not_match_folder_level",
                })
                continue
            by_level[level].append((int(book_id), path))
        by_level[level].sort(key=lambda item: item[0])
    return by_level, ignored_json_files


def validate_no_forbidden_keys(payload: Any, path: str = "$") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in FORBIDDEN_OUTPUT_KEYS:
                raise ValueError(f"Forbidden raw payload key emitted at {path}.{key}: {key}")
            validate_no_forbidden_keys(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            validate_no_forbidden_keys(value, f"{path}[{index}]")


def build_report(raw_root: Path) -> Dict[str, Any]:
    files_by_level, ignored_json_files = find_all_raw_files(raw_root)
    records: List[Dict[str, Any]] = []

    for level in EXPECTED_LEVELS:
        for book_id, path in files_by_level[level]:
            records.append(shallow_parse(path, raw_root, level, str(book_id)))

    file_count_by_level = {level: len(files_by_level[level]) for level in EXPECTED_LEVELS}
    parse_counts = Counter(record.get("json_parse_status", "UNKNOWN") for record in records)
    record_count_by_level = Counter(record.get("level") for record in records)
    fetch_success_count = sum(1 for record in records if record.get("json_parse_status") == "PASS")
    levels_missing = [level for level in EXPECTED_LEVELS if file_count_by_level[level] == 0]
    level_json_mismatch_count = sum(
        1 for record in records
        if record.get("level_from_json") and record.get("level_from_json") != record.get("level")
    )
    book_id_mismatch_count = sum(
        1 for record in records
        if record.get("book_id") and record.get("book_id") != record.get("book_id_from_filename")
    )
    generated_true_count = sum(1 for record in records if record.get("generated_content") is True)
    authority_status_counts = Counter(record.get("authority_status", "MISSING") for record in records)
    extractor_version_counts = Counter(record.get("extractor_version", "MISSING") for record in records)
    source_type_counts = Counter(record.get("source_type", "MISSING") for record in records)
    extraction_method_counts = Counter(record.get("extraction_method", "MISSING") for record in records)

    warnings: List[str] = []
    blockers: List[str] = []
    status = "PASS"
    if levels_missing:
        status = "PASS_WITH_WARNINGS"
        warnings.append("one_or_more_levels_missing")
    if len(records) != EXPECTED_RAW_LEVEL_FILE_COUNT:
        status = "PASS_WITH_WARNINGS"
        warnings.append("raw_level_file_count_differs_from_s2b_manifest_expected_count")
    if parse_counts.get("FAIL", 0):
        status = "PASS_WITH_WARNINGS"
        warnings.append("one_or_more_raw_json_parse_failures")
    if level_json_mismatch_count:
        status = "PASS_WITH_WARNINGS"
        warnings.append("one_or_more_level_metadata_mismatches")
    if book_id_mismatch_count:
        status = "PASS_WITH_WARNINGS"
        warnings.append("one_or_more_book_id_metadata_mismatches")
    if generated_true_count:
        status = "PASS_WITH_WARNINGS"
        warnings.append("one_or_more_records_mark_generated_content_true")
    if ignored_json_files:
        status = "PASS_WITH_WARNINGS"
        warnings.append("one_or_more_ignored_json_files_in_level_folders")
    if not records:
        status = "BLOCKED"
        blockers.append("no_raw_level_records_selected")

    return {
        "task_id": "RAZ-AW-S2F_LocalHydrationFullAWQA",
        "report_type": "local_hydration_full_aw_qa_report",
        "status": status,
        "sanitized": True,
        "contains_raw_text": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "authority_promotion": False,
        "tag_registry_promotion": False,
        "source_surface": "local_raw_mirror",
        "raw_root": str(raw_root),
        "expected_raw_level_file_count_from_s2b": EXPECTED_RAW_LEVEL_FILE_COUNT,
        "expected_levels": EXPECTED_LEVELS,
        "levels_missing": levels_missing,
        "file_count_by_level": file_count_by_level,
        "record_count_by_level": {level: record_count_by_level[level] for level in EXPECTED_LEVELS},
        "selected_record_count": len(records),
        "fetch_success_count": fetch_success_count,
        "json_parse_status_counts": dict(sorted(parse_counts.items())),
        "level_json_mismatch_count": level_json_mismatch_count,
        "book_id_mismatch_count": book_id_mismatch_count,
        "generated_content_true_count": generated_true_count,
        "authority_status_counts": dict(sorted(authority_status_counts.items())),
        "source_type_counts": dict(sorted(source_type_counts.items())),
        "extraction_method_counts": dict(sorted(extraction_method_counts.items())),
        "extractor_version_counts": dict(sorted(extractor_version_counts.items())),
        "ignored_json_file_count": len(ignored_json_files),
        "ignored_json_files": ignored_json_files[:50],
        "warnings": warnings,
        "blockers": blockers,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local RAZ A-W full hydration QA.")
    parser.add_argument("--raw-root", default="raz_output_jsons", help="Local raz_output_jsons root.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Output report directory.")
    args = parser.parse_args()

    raw_root = Path(args.raw_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()

    if not raw_root.exists() or not raw_root.is_dir():
        payload = {
            "task_id": "RAZ-AW-S2F_LocalHydrationFullAWQA",
            "report_type": "local_hydration_full_aw_qa_status",
            "status": "BLOCKED",
            "sanitized": True,
            "contains_raw_text": False,
            "raw_root": str(raw_root),
            "blockers": ["raw_root_missing_or_not_directory"],
        }
        write_json(reports_dir / "local_hydration_full_aw_qa_report.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    report = build_report(raw_root)
    validate_no_forbidden_keys(report)
    write_json(reports_dir / "local_hydration_full_aw_qa_report.json", report)
    write_json(reports_dir / "local_hydration_full_aw_qa_summary.json", {
        key: value for key, value in report.items() if key != "records"
    })
    print(json.dumps({
        "status": report["status"],
        "selected_record_count": report["selected_record_count"],
        "fetch_success_count": report["fetch_success_count"],
        "json_parse_status_counts": report["json_parse_status_counts"],
        "levels_missing": report["levels_missing"],
        "warnings": report["warnings"],
        "blockers": report["blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] != "BLOCKED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
