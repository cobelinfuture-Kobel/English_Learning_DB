#!/usr/bin/env python3
"""Sanitized RAZ sentence candidate shape probe.

This tool inspects structural key paths only. It never emits raw sentence text.
Use it when normalized sentence extraction returns zero records.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
RAW_FILE_RE = re.compile(r"^raz_([A-W])_([0-9]+)_audio_timeline_extract\.json$")
SKIP_KEYS = {"audio_trace", "word_trace", "audio_timeline", "timeline", "timings", "timestamps", "full_raw_json"}


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("top_level_json_is_not_object")
    return data


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def level_files(raw_root: Path, level: str) -> List[Tuple[int, Path]]:
    level_dir = raw_root / f"Level_{level}"
    if not level_dir.exists():
        return []
    found: List[Tuple[int, Path]] = []
    for path in level_dir.glob("*.json"):
        match = RAW_FILE_RE.match(path.name)
        if match and match.group(1) == level:
            found.append((int(match.group(2)), path))
    return sorted(found, key=lambda item: item[0])


def value_type(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if value is None:
        return "null"
    return type(value).__name__


def walk_shape(value: Any, path: str, counter: Counter, string_path_counter: Counter, depth: int = 0, max_depth: int = 5) -> None:
    if depth > max_depth:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            key_str = str(key)
            key_lower = key_str.lower()
            if key_lower in SKIP_KEYS or any(skip in key_lower for skip in ("audio", "timing", "timestamp", "bbox", "image")):
                counter[f"{path}.{key_str}:skipped"] += 1
                continue
            child_path = f"{path}.{key_str}"
            typ = value_type(child)
            counter[f"{child_path}:{typ}"] += 1
            if isinstance(child, str):
                string_path_counter[child_path] += 1
            elif isinstance(child, (dict, list)):
                walk_shape(child, child_path, counter, string_path_counter, depth + 1, max_depth)
    elif isinstance(value, list):
        counter[f"{path}:array_len_bucket_{min(len(value), 20)}"] += 1
        for item in value[:3]:
            typ = value_type(item)
            counter[f"{path}[]:{typ}"] += 1
            if isinstance(item, str):
                string_path_counter[f"{path}[]"] += 1
            elif isinstance(item, (dict, list)):
                walk_shape(item, f"{path}[]", counter, string_path_counter, depth + 1, max_depth)


def build_probe(raw_root: Path, sample_per_level: int) -> Dict[str, Any]:
    shape_counter: Counter = Counter()
    string_path_counter: Counter = Counter()
    sampled_files: List[Dict[str, str]] = []
    candidate_count_by_level: Dict[str, int] = {}
    sampled_candidate_count_by_level: Dict[str, int] = {}
    parse_failures: List[Dict[str, str]] = []

    for level in EXPECTED_LEVELS:
        files = level_files(raw_root, level)
        selected = []
        if files:
            selected = files[:sample_per_level]
        total_candidates = 0
        sampled_candidates = 0
        for _, path in files:
            try:
                data = read_json(path)
            except Exception:
                continue
            candidates = data.get("sentence_candidates")
            if isinstance(candidates, list):
                total_candidates += len(candidates)
        for _, path in selected:
            try:
                data = read_json(path)
            except Exception as exc:
                parse_failures.append({"level": level, "filename": path.name, "error_type": type(exc).__name__})
                continue
            sampled_files.append({"level": level, "filename": path.name})
            candidates = data.get("sentence_candidates")
            if not isinstance(candidates, list):
                shape_counter["sentence_candidate_root:not_list"] += 1
                continue
            sampled_candidates += len(candidates[:10])
            for candidate in candidates[:10]:
                walk_shape(candidate, "candidate", shape_counter, string_path_counter)
        candidate_count_by_level[level] = total_candidates
        sampled_candidate_count_by_level[level] = sampled_candidates

    return {
        "task_id": "RAZ-AW-S3C1A_NormalizedSentenceExtractionMappingFix",
        "report_type": "sentence_candidate_shape_probe",
        "status": "PASS",
        "sanitized": True,
        "contains_raw_text": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "sample_per_level": sample_per_level,
        "sampled_files": sampled_files,
        "candidate_count_by_level": candidate_count_by_level,
        "sampled_candidate_count_by_level": sampled_candidate_count_by_level,
        "top_shape_paths": dict(shape_counter.most_common(200)),
        "top_string_paths": dict(string_path_counter.most_common(100)),
        "parse_failures": parse_failures[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe RAZ sentence candidate shape without emitting raw text.")
    parser.add_argument("--raw-root", default="raz_output_jsons")
    parser.add_argument("--reports-dir", default="reports/raz")
    parser.add_argument("--sample-per-level", type=int, default=2)
    args = parser.parse_args()
    raw_root = Path(args.raw_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    if not raw_root.exists():
        payload = {
            "task_id": "RAZ-AW-S3C1A_NormalizedSentenceExtractionMappingFix",
            "status": "BLOCKED",
            "sanitized": True,
            "contains_raw_text": False,
            "blockers": ["raw_root_missing"],
        }
        write_json(reports_dir / "raz_aw_sentence_candidate_shape_probe.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    payload = build_probe(raw_root, args.sample_per_level)
    write_json(reports_dir / "raz_aw_sentence_candidate_shape_probe.json", payload)
    print(json.dumps({
        "status": payload["status"],
        "sampled_file_count": len(payload["sampled_files"]),
        "top_string_paths": dict(list(payload["top_string_paths"].items())[:10]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
