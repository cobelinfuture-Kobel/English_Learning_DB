#!/usr/bin/env python3
"""Generate a sanitized RAZ A-W raw JSON manifest from a local mirror.

This tool is intentionally read-only with respect to raw RAZ files. It writes
sanitized manifest/report files only and never emits full sentence/page text.

Default usage from repository root:
    python tools/raz_aw_drive_manifest_from_local_mirror.py --raw-root raz_output_jsons

Typical Windows usage:
    python tools\raz_aw_drive_manifest_from_local_mirror.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
MEDIA_EXTENSIONS = {".pdf", ".mp3", ".mp4", ".wav", ".m4a", ".jpg", ".jpeg", ".png", ".webp"}
ARCHIVE_EXTENSIONS = {".zip", ".7z", ".rar", ".tar", ".gz"}
RAW_TEXT_KEYS_FORBIDDEN_IN_REPORTS = {
    "text",
    "sentence",
    "sentences",
    "cleaned_candidate",
    "candidate_text",
    "legacy_story_sentences",
    "page_text",
    "raw_text",
    "word_trace",
    "audio_trace",
    "audio_timeline",
    "page_units",
    "sentence_candidates",
    "reuse_unit_candidates",
}


def _safe_read_json(path: Path, max_parse_bytes: int) -> Tuple[str, Optional[Dict[str, Any]], Optional[str]]:
    """Read JSON when it is small enough. Returns status, object, error."""
    if path.stat().st_size > max_parse_bytes:
        return "SKIPPED_TOO_LARGE", None, None
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except Exception as exc:  # pragma: no cover - explicit diagnostic path
        return "FAIL", None, f"{type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return "FAIL", None, "top_level_json_is_not_object"
    return "PASS", data, None


def _count_list(data: Dict[str, Any], key: str) -> Optional[int]:
    value = data.get(key)
    return len(value) if isinstance(value, list) else None


def _as_bool_or_none(value: Any) -> Optional[bool]:
    return value if isinstance(value, bool) else None


def _safe_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return None


def _infer_level_from_path(path: Path, raw_root: Path) -> Optional[str]:
    try:
        parts = path.relative_to(raw_root).parts
    except ValueError:
        parts = path.parts
    for part in parts:
        match = re.fullmatch(r"Level_([A-W])", part)
        if match:
            return match.group(1)
    match = re.search(r"raz_([A-W])_", path.name)
    return match.group(1) if match else None


def _source_bucket(path: Path, raw_root: Path) -> str:
    parts = set(path.relative_to(raw_root).parts)
    if "derived" in parts:
        return "derived"
    if any(re.fullmatch(r"Level_[A-W]", part) for part in parts):
        return "raw_level"
    return "unknown"


def _shallow_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    book_metadata = data.get("book_metadata") if isinstance(data.get("book_metadata"), dict) else {}
    clean_summary = data.get("clean_summary") if isinstance(data.get("clean_summary"), dict) else {}

    summary: Dict[str, Any] = {
        "source_type": _safe_str(data.get("source_type")),
        "extraction_method": _safe_str(data.get("extraction_method")),
        "extractor_version": _safe_str(data.get("extractor_version")),
        "book_id": _safe_str(book_metadata.get("book_id") or clean_summary.get("book_id")),
        "book_title": _safe_str(book_metadata.get("title") or clean_summary.get("title")),
        "level_from_json": _safe_str(book_metadata.get("level") or clean_summary.get("level")),
        "story_page_start": book_metadata.get("story_page_start"),
        "story_page_end": book_metadata.get("story_page_end"),
        "story_page_count": book_metadata.get("story_page_count") or clean_summary.get("actual_story_page_count"),
        "sentence_candidate_count": _count_list(data, "sentence_candidates"),
        "page_unit_count": _count_list(data, "page_units"),
        "reuse_candidate_count": _count_list(data, "reuse_unit_candidates"),
        "excluded_item_count": _count_list(data, "excluded_items"),
        "legacy_story_sentence_count": _count_list(data, "legacy_story_sentences"),
        "authority_status": _safe_str(clean_summary.get("authority_status")),
        "generated_content": _as_bool_or_none(clean_summary.get("generated_content")),
        "raw_audio_fields_preserved": _as_bool_or_none(clean_summary.get("raw_audio_fields_preserved")),
        "final_should_remove_audio_fields": _as_bool_or_none(clean_summary.get("final_should_remove_audio_fields")),
        "top_level_keys": sorted(str(key) for key in data.keys()),
    }

    return {key: value for key, value in summary.items() if value is not None}


def _hash_relative_path(relative_path: str) -> str:
    return hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16]


def _iter_files(raw_root: Path, include_derived: bool) -> Iterable[Path]:
    for path in sorted(raw_root.rglob("*")):
        if not path.is_file():
            continue
        try:
            relative_parts = path.relative_to(raw_root).parts
        except ValueError:
            relative_parts = path.parts
        if not include_derived and "derived" in relative_parts:
            continue
        yield path


def build_manifest(raw_root: Path, include_derived: bool, max_parse_mb: float) -> Dict[str, Any]:
    max_parse_bytes = int(max_parse_mb * 1024 * 1024)
    records: List[Dict[str, Any]] = []
    unexpected_files: List[Dict[str, Any]] = []
    media_files: List[Dict[str, Any]] = []
    archive_files: List[Dict[str, Any]] = []
    large_files: List[Dict[str, Any]] = []
    over_hard_limit_files: List[Dict[str, Any]] = []
    parse_status_counts: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()

    for file_path in _iter_files(raw_root, include_derived=include_derived):
        rel = file_path.relative_to(raw_root).as_posix()
        suffix = file_path.suffix.lower()
        size_bytes = file_path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 4)
        level = _infer_level_from_path(file_path, raw_root)
        base_info = {
            "relative_path": rel,
            "relative_path_hash": _hash_relative_path(rel),
            "filename": file_path.name,
            "extension": suffix,
            "size_bytes": size_bytes,
            "size_mb": size_mb,
            "level": level,
            "source_bucket": _source_bucket(file_path, raw_root),
        }

        if size_bytes > 50 * 1024 * 1024:
            large_files.append(base_info)
        if size_bytes > 100 * 1024 * 1024:
            over_hard_limit_files.append(base_info)
        if suffix in MEDIA_EXTENSIONS:
            media_files.append(base_info)
            continue
        if suffix in ARCHIVE_EXTENSIONS:
            archive_files.append(base_info)
            continue
        if suffix != ".json":
            unexpected_files.append(base_info)
            continue

        json_status, parsed, error = _safe_read_json(file_path, max_parse_bytes=max_parse_bytes)
        parse_status_counts[json_status] += 1
        if level:
            level_counts[level] += 1

        record: Dict[str, Any] = {
            "level": level,
            "folder_title": f"Level_{level}" if level else None,
            "filename": file_path.name,
            "relative_path": rel,
            "relative_path_hash": _hash_relative_path(rel),
            "drive_file_id": None,
            "drive_url": None,
            "size_bytes": size_bytes,
            "size_mb": size_mb,
            "mime_type": "application/json",
            "json_parse_status": json_status,
            "json_parse_error": error,
            "source_bucket": _source_bucket(file_path, raw_root),
            "raw_text_in_manifest": False,
        }
        if parsed is not None:
            record.update(_shallow_summary(parsed))
        records.append({key: value for key, value in record.items() if value is not None})

    levels_present = sorted(level for level in EXPECTED_LEVELS if level_counts.get(level, 0) > 0)
    levels_missing = sorted(level for level in EXPECTED_LEVELS if level_counts.get(level, 0) == 0)

    return {
        "task_id": "RAZ-AW-S1C_RawAWDriveManifestGeneration",
        "manifest_type": "local_mirror_sanitized_manifest",
        "manifest_status": "GENERATED",
        "sanitized": True,
        "contains_raw_text": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "source_surface": "local_mirror",
        "raw_root": str(raw_root),
        "include_derived": include_derived,
        "levels_requested": EXPECTED_LEVELS,
        "levels_present": levels_present,
        "levels_missing": levels_missing,
        "file_count_total": len(records),
        "file_count_by_level": {level: level_counts.get(level, 0) for level in EXPECTED_LEVELS},
        "json_parse_status_counts": dict(parse_status_counts),
        "large_file_count_over_50mb": len(large_files),
        "large_file_count_over_100mb": len(over_hard_limit_files),
        "unexpected_file_count": len(unexpected_files),
        "media_file_count": len(media_files),
        "archive_file_count": len(archive_files),
        "forbidden_raw_text_keys_not_emitted": sorted(RAW_TEXT_KEYS_FORBIDDEN_IN_REPORTS),
        "records": records,
    }


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_aux_reports(manifest: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    large_records = [
        {
            "level": rec.get("level"),
            "filename": rec.get("filename"),
            "relative_path_hash": rec.get("relative_path_hash"),
            "size_bytes": rec.get("size_bytes"),
            "size_mb": rec.get("size_mb"),
        }
        for rec in manifest["records"]
        if rec.get("size_bytes", 0) > 50 * 1024 * 1024
    ]
    hard_limit_records = [rec for rec in large_records if rec.get("size_bytes", 0) > 100 * 1024 * 1024]

    safety_status = "PASS"
    blockers: List[str] = []
    warnings: List[str] = []
    if manifest["levels_missing"]:
        safety_status = "PASS_WITH_WARNINGS"
        warnings.append("some_A_W_levels_missing")
    if manifest["media_file_count"] or manifest["archive_file_count"]:
        safety_status = "BLOCKED"
        blockers.append("media_or_archive_files_detected_under_raw_root")
    if hard_limit_records:
        safety_status = "PASS_WITH_WARNINGS"
        warnings.append("files_over_100mb_detected_but_not_committed")

    safety_report = {
        "task_id": "RAZ-AW-S1C_RawAWDriveManifestGeneration",
        "report_type": "raw_aw_manifest_generation_safety_report",
        "status": safety_status,
        "sanitized": True,
        "contains_raw_text": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "levels_present": manifest["levels_present"],
        "levels_missing": manifest["levels_missing"],
        "file_count_total": manifest["file_count_total"],
        "safe_to_commit_manifest": safety_status != "BLOCKED",
        "safe_to_commit_raw_files": False,
        "warnings": warnings,
        "blockers": blockers,
    }

    large_file_report = {
        "task_id": "RAZ-AW-S1C_RawAWDriveManifestGeneration",
        "report_type": "raw_aw_large_file_report",
        "status": "PASS" if not large_records else "PASS_WITH_WARNINGS",
        "sanitized": True,
        "contains_raw_text": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "size_threshold_mb": 50,
        "github_hard_limit_mb": 100,
        "files_over_github_warning_threshold": large_records,
        "files_over_github_hard_limit": hard_limit_records,
        "commit_raw_files_allowed": False,
    }
    return safety_report, large_file_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sanitized RAZ A-W raw JSON manifest from a local mirror.")
    parser.add_argument("--raw-root", default="raz_output_jsons", help="Path to local raz_output_jsons root.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Output report directory.")
    parser.add_argument("--include-derived", action="store_true", help="Include raz_output_jsons/derived files.")
    parser.add_argument("--max-parse-mb", type=float, default=50.0, help="Maximum JSON file size to parse for shallow schema counts.")
    args = parser.parse_args()

    raw_root = Path(args.raw_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    if not raw_root.exists() or not raw_root.is_dir():
        error_report = {
            "task_id": "RAZ-AW-S1C_RawAWDriveManifestGeneration",
            "manifest_status": "BLOCKED",
            "sanitized": True,
            "contains_raw_text": False,
            "raw_root": str(raw_root),
            "blockers": ["raw_root_missing_or_not_directory"],
        }
        write_json(reports_dir / "raw_aw_drive_file_manifest.status.json", error_report)
        print("BLOCKED: raw root does not exist or is not a directory")
        return 2

    manifest = build_manifest(raw_root, include_derived=args.include_derived, max_parse_mb=args.max_parse_mb)
    safety_report, large_file_report = build_aux_reports(manifest)

    write_json(reports_dir / "raw_aw_drive_file_manifest.json", manifest)
    write_json(reports_dir / "raw_aw_manifest_generation_safety_report.json", safety_report)
    write_json(reports_dir / "raw_aw_large_file_report.json", large_file_report)

    print(json.dumps({
        "status": safety_report["status"],
        "file_count_total": manifest["file_count_total"],
        "levels_present": manifest["levels_present"],
        "levels_missing": manifest["levels_missing"],
        "large_files_over_50mb": large_file_report["files_over_github_warning_threshold"],
    }, ensure_ascii=False, indent=2))
    return 0 if safety_report["status"] != "BLOCKED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
