#!/usr/bin/env python3
"""Build sanitized hydration plans from a Drive file-id manifest.

This tool does not fetch Google Drive files. It consumes a locally downloaded
manifest.json with this shape:

    {
      "last_updated": "...",
      "target_folder_id": "...",
      "files": {
        "raz_output_jsons/Level_A/raz_A_6_audio_timeline_extract.json": "drive_file_id"
      }
    }

It writes sanitized planning reports only. No raw RAZ text is read or emitted.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
RAW_PATH_RE = re.compile(r"^raz_output_jsons/Level_([A-W])/raz_([A-W])_([0-9]+)_audio_timeline_extract\.json$")


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} top-level JSON is not an object")
    return data


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def drive_url(file_id: str) -> str:
    return f"https://drive.google.com/file/d/{file_id}/view"


def classify_entry(relative_path: str, file_id: str) -> Dict[str, Any]:
    match = RAW_PATH_RE.match(relative_path)
    if match:
        level_from_folder, level_from_filename, book_id = match.groups()
        return {
            "entry_type": "raw_level_json",
            "level": level_from_folder,
            "level_from_filename": level_from_filename,
            "book_id": book_id,
            "relative_path": relative_path,
            "filename": relative_path.rsplit("/", 1)[-1],
            "drive_file_id": file_id,
            "drive_url": drive_url(file_id),
            "filename_pattern_status": "PASS" if level_from_folder == level_from_filename else "FAIL",
        }
    if relative_path.startswith("raz_output_jsons/derived/"):
        entry_type = "derived_json" if relative_path.endswith(".json") else "derived_non_json"
    elif relative_path in {"raz_output_jsons/run_failed_items.json", "raz_output_jsons/run_summary.json"}:
        entry_type = "special_report_json"
    else:
        entry_type = "other"
    return {
        "entry_type": entry_type,
        "relative_path": relative_path,
        "filename": relative_path.rsplit("/", 1)[-1],
        "drive_file_id": file_id,
        "drive_url": drive_url(file_id),
    }


def choose_samples(raw_records: List[Dict[str, Any]], sample_per_level: int) -> List[Dict[str, Any]]:
    by_level: Dict[str, List[Dict[str, Any]]] = {level: [] for level in EXPECTED_LEVELS}
    for record in raw_records:
        level = record.get("level")
        if level in by_level:
            by_level[level].append(record)

    samples: List[Dict[str, Any]] = []
    for level in EXPECTED_LEVELS:
        records = sorted(by_level[level], key=lambda rec: int(rec.get("book_id", 0)))
        if not records:
            continue
        if sample_per_level <= 1:
            indices = [0]
        elif sample_per_level == 2:
            indices = [0, len(records) - 1]
        else:
            indices = sorted(set([0, len(records) // 2, len(records) - 1]))[:sample_per_level]
        samples.extend(records[index] for index in indices)
    return samples


def build_plan(manifest: Dict[str, Any], sample_per_level: int) -> Dict[str, Any]:
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("manifest missing files mapping")

    records = [classify_entry(str(path), str(file_id)) for path, file_id in sorted(files.items())]
    raw_records = [record for record in records if record["entry_type"] == "raw_level_json"]
    sample_records = choose_samples(raw_records, sample_per_level=sample_per_level)

    counts_by_type = Counter(record["entry_type"] for record in records)
    counts_by_level = Counter(record.get("level") for record in raw_records if record.get("level"))
    levels_present = [level for level in EXPECTED_LEVELS if counts_by_level[level] > 0]
    levels_missing = [level for level in EXPECTED_LEVELS if counts_by_level[level] == 0]
    duplicate_file_ids = len(files.values()) - len(set(files.values()))
    filename_mismatch_count = sum(1 for rec in raw_records if rec.get("filename_pattern_status") != "PASS")

    return {
        "task_id": "RAZ-AW-S2C_DriveManifestHydrationTooling",
        "report_type": "drive_manifest_hydration_plan",
        "status": "PASS" if not levels_missing and not duplicate_file_ids and not filename_mismatch_count else "PASS_WITH_WARNINGS",
        "sanitized": True,
        "contains_raw_text": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "source_surface": "downloaded_drive_file_id_manifest",
        "manifest_last_updated": manifest.get("last_updated"),
        "target_folder_id": manifest.get("target_folder_id"),
        "manifest_file_count_total": len(records),
        "counts_by_entry_type": dict(sorted(counts_by_type.items())),
        "raw_level_json_file_count": len(raw_records),
        "file_count_by_level": {level: counts_by_level[level] for level in EXPECTED_LEVELS},
        "levels_present": levels_present,
        "levels_missing": levels_missing,
        "duplicate_drive_file_id_count": duplicate_file_ids,
        "raw_filename_pattern_mismatch_count": filename_mismatch_count,
        "hydration_modes": {
            "sample": "fetch only generated sample_records by file_id",
            "level": "fetch records for one selected level by file_id",
            "full": "fetch all raw_level_json records by file_id"
        },
        "sample_strategy": f"up_to_{sample_per_level}_records_per_level_first_middle_last",
        "sample_records": sample_records,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a sanitized Drive manifest hydration plan.")
    parser.add_argument("--manifest", default="scratch/raz/manifest.json", help="Local downloaded Drive manifest.json path.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Output report directory.")
    parser.add_argument("--sample-per-level", type=int, default=3, help="Sample count per A-W level. 1=first, 2=first/last, 3=first/middle/last.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    reports_dir = Path(args.reports_dir)
    if not manifest_path.exists():
        status = {
            "task_id": "RAZ-AW-S2C_DriveManifestHydrationTooling",
            "report_type": "drive_manifest_hydration_plan_status",
            "status": "BLOCKED",
            "sanitized": True,
            "contains_raw_text": False,
            "blockers": ["manifest_file_missing"],
            "expected_manifest_path": str(manifest_path),
        }
        write_json(reports_dir / "drive_manifest_hydration_plan.status.json", status)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 2

    manifest = read_json(manifest_path)
    plan = build_plan(manifest, sample_per_level=args.sample_per_level)
    write_json(reports_dir / "drive_manifest_hydration_plan.json", plan)
    write_json(reports_dir / "drive_manifest_hydration_sample_urls.json", {
        "task_id": "RAZ-AW-S2C_DriveManifestHydrationTooling",
        "report_type": "drive_manifest_hydration_sample_urls",
        "status": plan["status"],
        "sanitized": True,
        "contains_raw_text": False,
        "sample_count": len(plan["sample_records"]),
        "records": [
            {
                "level": rec.get("level"),
                "book_id": rec.get("book_id"),
                "relative_path": rec.get("relative_path"),
                "drive_file_id": rec.get("drive_file_id"),
                "drive_url": rec.get("drive_url"),
            }
            for rec in plan["sample_records"]
        ],
    })

    print(json.dumps({
        "status": plan["status"],
        "manifest_file_count_total": plan["manifest_file_count_total"],
        "raw_level_json_file_count": plan["raw_level_json_file_count"],
        "levels_missing": plan["levels_missing"],
        "sample_count": len(plan["sample_records"]),
    }, ensure_ascii=False, indent=2))
    return 0 if plan["status"] != "BLOCKED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
