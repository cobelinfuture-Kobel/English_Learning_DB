#!/usr/bin/env python3
"""Local RAZ A-W hydration level QA.

This tool reads selected full RAZ levels from a local raz_output_jsons mirror,
shallow-parses every matching raw JSON in those levels, and writes sanitized QA
reports. It does not emit sentence/page/audio raw text.

Default usage from repository root:
    python tools/raz_aw_local_hydration_level_qa.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons --levels A W
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
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


def normalize_levels(raw_levels: List[str]) -> List[str]:
    levels: List[str] = []
    for item in raw_levels:
        level = item.strip().upper()
        if level not in EXPECTED_LEVELS:
            raise ValueError(f"Invalid level: {item}. Expected A-W.")
        if level not in levels:
            levels.append(level)
    return levels


def find_level_files(raw_root: Path, level: str) -> List[Tuple[int, Path]]:
    level_dir = raw_root / f"Level_{level}"
    if not level_dir.exists():
        return []
    files: List[Tuple[int, Path]] = []
    for path in level_dir.glob("*.json"):
        match = RAW_FILE_RE.match(path.name)
        if not match:
            continue
        filename_level, book_id = match.groups()
        if filename_level != level:
            continue
        files.append((int(book_id), path))
    files.sort(key=lambda item: item[0])
    return files


def validate_no_forbidden_keys(payload: Any, path: str = "$") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in FORBIDDEN_OUTPUT_KEYS:
                raise ValueError(f"Forbidden raw payload key emitted at {path}.{key}: {key}")
            validate_no_forbidden_keys(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            validate_no_forbidden_keys(value, f"{path}[{index}]")


def build_report(raw_root: Path, levels: List[str]) -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    file_count_by_level: Dict[str, int] = {}
    missing_levels: List[str] = []

    for level in levels:
        files = find_level_files(raw_root, level)
        file_count_by_level[level] = len(files)
        if not files:
            missing_levels.append(level)
            continue
        for book_id, path in files:
            records.append(shallow_parse(path, raw_root, level, str(book_id)))

    parse_counts = Counter(record.get("json_parse_status", "UNKNOWN") for record in records)
    record_count_by_level = Counter(record.get("level") for record in records)
    fetch_success_count = sum(1 for record in records if record.get("json_parse_status") == "PASS")
    level_json_mismatch_count = sum(
        1 for record in records
        if record.get("level_from_json") and record.get("level_from_json") != record.get("level")
    )
    generated_true_count = sum(1 for record in records if record.get("generated_content") is True)

    warnings: List[str] = []
    blockers: List[str] = []
    status = "PASS"
    if missing_levels:
        status = "PASS_WITH_WARNINGS"
        warnings.append("one_or_more_requested_levels_missing")
    if parse_counts.get("FAIL", 0):
        status = "PASS_WITH_WARNINGS"
        warnings.append("one_or_more_level_json_parse_failures")
    if level_json_mismatch_count:
        status = "PASS_WITH_WARNINGS"
        warnings.append("one_or_more_level_metadata_mismatches")
    if not records:
        status = "BLOCKED"
        blockers.append("no_level_records_selected")

    return {
        "task_id": "RAZ-AW-S2E_LocalHydrationLevelQA",
        "report_type": "local_hydration_level_qa_report",
        "status": status,
        "sanitized": True,
        "contains_raw_text": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "authority_promotion": False,
        "tag_registry_promotion": False,
        "source_surface": "local_raw_mirror",
        "raw_root": str(raw_root),
        "requested_levels": levels,
        "levels_missing": missing_levels,
        "file_count_by_level": file_count_by_level,
        "record_count_by_level": {level: record_count_by_level[level] for level in levels},
        "selected_record_count": len(records),
        "fetch_success_count": fetch_success_count,
        "json_parse_status_counts": dict(sorted(parse_counts.items())),
        "level_json_mismatch_count": level_json_mismatch_count,
        "generated_content_true_count": generated_true_count,
        "warnings": warnings,
        "blockers": blockers,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local RAZ A-W full-level hydration QA.")
    parser.add_argument("--raw-root", default="raz_output_jsons", help="Local raz_output_jsons root.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Output report directory.")
    parser.add_argument("--levels", nargs="+", default=["A", "W"], help="One or more levels A-W. Default: A W.")
    args = parser.parse_args()

    raw_root = Path(args.raw_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    levels = normalize_levels(args.levels)

    if not raw_root.exists() or not raw_root.is_dir():
        payload = {
            "task_id": "RAZ-AW-S2E_LocalHydrationLevelQA",
            "report_type": "local_hydration_level_qa_status",
            "status": "BLOCKED",
            "sanitized": True,
            "contains_raw_text": False,
            "raw_root": str(raw_root),
            "requested_levels": levels,
            "blockers": ["raw_root_missing_or_not_directory"],
        }
        write_json(reports_dir / "local_hydration_level_qa_report.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    report = build_report(raw_root, levels)
    validate_no_forbidden_keys(report)
    write_json(reports_dir / "local_hydration_level_qa_report.json", report)
    write_json(reports_dir / "local_hydration_level_qa_summary.json", {
        key: value for key, value in report.items() if key != "records"
    })
    print(json.dumps({
        "status": report["status"],
        "requested_levels": report["requested_levels"],
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
