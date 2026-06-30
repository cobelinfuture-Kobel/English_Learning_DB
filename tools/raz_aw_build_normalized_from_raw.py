#!/usr/bin/env python3
"""Build RAZ A-W normalized candidate artifacts from local raw JSON.

S3C1 contract:
- Reads local raw mirror only.
- Writes full text-bearing normalized artifacts under raz_output_jsons/derived.
- Writes only sanitized summaries to reports/raz for GitHub commit.
- Does not promote content/tag/authority status.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

EXPECTED_LEVELS = list("ABCDEFGHIJKLMNOPQRSTUVW")
RAW_FILE_RE = re.compile(r"^raz_([A-W])_([0-9]+)_audio_timeline_extract\.json$")
EXPECTED_EXTRACTOR_VERSION = "raz_audio_timeline_to_content_authority_v3_story_filter"
FORBIDDEN_GITHUB_REPORT_KEYS = {
    "sentence_candidates",
    "page_units",
    "reuse_unit_candidates",
    "legacy_story_sentences",
    "audio_trace",
    "word_trace",
    "raw_text",
    "page_text",
    "full_raw_json",
}
TEXT_KEY_PRIORITY = (
    "normalized_text",
    "clean_text",
    "story_text",
    "sentence_text",
    "text",
    "sentence",
    "content",
)
PAGE_KEY_PRIORITY = (
    "page_number",
    "story_page_number",
    "page",
    "page_index",
)


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"top_level_json_is_not_object: {path}")
    return data


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_text(value: Any) -> Tuple[Optional[str], Optional[str]]:
    if not isinstance(value, str):
        return None, "text_missing_or_not_string"
    text = unicodedata.normalize("NFC", value)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None, "empty_text"
    if "\ufffd" in text:
        return None, "replacement_character"
    if re.search(r"\b(?:start|end|duration|timestamp|audio|offset)\s*[:=]\s*\d", text, re.I):
        return None, "raw_timing_token_leakage"
    if re.search(r"<[^>]+>", text):
        return None, "raw_markup_artifact"
    symbol_count = sum(1 for ch in text if not ch.isalnum() and not ch.isspace() and ch not in ".,!?;:'\"-()")
    if len(text) >= 8 and symbol_count / max(len(text), 1) > 0.25:
        return None, "abnormal_symbol_density"
    return text, None


def first_scalar(d: Dict[str, Any], keys: Iterable[str]) -> Optional[Any]:
    for key in keys:
        value = d.get(key)
        if isinstance(value, (str, int, float, bool)):
            return value
    return None


def find_text(candidate: Any) -> Tuple[Optional[str], Optional[str]]:
    if isinstance(candidate, str):
        return normalize_text(candidate)
    if not isinstance(candidate, dict):
        return None, "candidate_not_object_or_string"
    value = first_scalar(candidate, TEXT_KEY_PRIORITY)
    if value is None:
        # One-level conservative fallback only; do not recurse into audio/word traces.
        for nested_key in ("data", "payload", "item"):
            nested = candidate.get(nested_key)
            if isinstance(nested, dict):
                value = first_scalar(nested, TEXT_KEY_PRIORITY)
                if value is not None:
                    break
    return normalize_text(value)


def find_page_number(candidate: Any, default: int = 0) -> int:
    if not isinstance(candidate, dict):
        return default
    value = first_scalar(candidate, PAGE_KEY_PRIORITY)
    try:
        return int(value) if value is not None else default
    except Exception:
        return default


def make_source_ref(raw_root: Path, raw_path: Path, layer: str, ref: str) -> Dict[str, str]:
    out = {
        "raw_file_relative_path": raw_path.relative_to(raw_root).as_posix(),
        "source_layer": layer,
        "deterministic_index_ref": ref,
    }
    if layer in {"raw_sentence_candidate", "raw_reuse_unit_candidate"}:
        out["raw_candidate_ref"] = ref
    if layer == "raw_page_unit":
        out["raw_page_ref"] = ref
    return out


def story_page_count(book: Dict[str, Any], clean: Dict[str, Any]) -> int:
    for value in (book.get("story_page_count"), clean.get("actual_story_page_count")):
        try:
            if value is not None:
                return int(value)
        except Exception:
            pass
    return 0


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def level_files(raw_root: Path, level: str) -> List[Tuple[int, Path]]:
    level_dir = raw_root / f"Level_{level}"
    if not level_dir.exists():
        return []
    found: List[Tuple[int, Path]] = []
    for path in level_dir.glob("*.json"):
        match = RAW_FILE_RE.match(path.name)
        if not match:
            continue
        file_level, book_id = match.groups()
        if file_level == level:
            found.append((int(book_id), path))
    return sorted(found, key=lambda item: item[0])


def build_book_record(raw_root: Path, raw_path: Path, level: str, book_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    book = data.get("book_metadata") if isinstance(data.get("book_metadata"), dict) else {}
    clean = data.get("clean_summary") if isinstance(data.get("clean_summary"), dict) else {}
    book_uid = f"raz_{level}_{book_id}"
    title = str(book.get("title") or clean.get("title") or "UNTITLED")
    return {
        "book_uid": book_uid,
        "source": "RAZ",
        "level": level,
        "book_id": book_id,
        "title": title,
        "source_type": str(data.get("source_type") or "raz_audio_timeline"),
        "extraction_method": str(data.get("extraction_method") or "bookAudioContent"),
        "extractor_version": str(data.get("extractor_version") or EXPECTED_EXTRACTOR_VERSION),
        "story_page_start": as_int(book.get("story_page_start"), 0),
        "story_page_end": as_int(book.get("story_page_end"), 0),
        "story_page_count": story_page_count(book, clean),
        "allowed_text_types": book.get("allowed_text_types", []) if isinstance(book.get("allowed_text_types"), list) else [],
        "min_story_page_number": as_int(book.get("min_story_page_number"), 0),
        "source_ref": make_source_ref(raw_root, raw_path, "raw_book_metadata", "book_metadata"),
        "authority_status": "candidate_only",
        "normalization_status": "candidate_normalized",
        "content_authority_status": "not_promoted",
        "review_status": "pending",
    }


def build_sentence_records(raw_root: Path, raw_path: Path, level: str, book_id: str, data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Counter, Dict[int, List[str]]]:
    raw_candidates = data.get("sentence_candidates")
    if not isinstance(raw_candidates, list):
        return [], Counter({"sentence_candidates_missing_or_not_list": 1}), {}
    records: List[Dict[str, Any]] = []
    exclusions: Counter = Counter()
    by_page: Dict[int, List[str]] = defaultdict(list)
    sentence_index = 0
    book_uid = f"raz_{level}_{book_id}"
    for raw_index, candidate in enumerate(raw_candidates, start=1):
        text, reason = find_text(candidate)
        if reason:
            exclusions[reason] += 1
            continue
        sentence_index += 1
        page_number = find_page_number(candidate, 0)
        sentence_uid = f"{book_uid}_s{sentence_index:04d}"
        by_page[page_number].append(sentence_uid)
        records.append({
            "sentence_uid": sentence_uid,
            "book_uid": book_uid,
            "level": level,
            "book_id": book_id,
            "page_number": page_number,
            "sentence_index_in_book": sentence_index,
            "text": text,
            "source_ref": make_source_ref(raw_root, raw_path, "raw_sentence_candidate", f"sentence_candidates[{raw_index}]"),
            "authority_status": "candidate_only",
            "normalization_status": "candidate_normalized",
            "content_authority_status": "not_promoted",
            "review_status": "pending",
        })
    return records, exclusions, by_page


def build_page_unit_records(raw_root: Path, raw_path: Path, level: str, book_id: str, data: Dict[str, Any], by_page: Dict[int, List[str]]) -> Tuple[List[Dict[str, Any]], Counter]:
    raw_units = data.get("page_units")
    if not isinstance(raw_units, list):
        return [], Counter({"page_units_missing_or_not_list": 1})
    records: List[Dict[str, Any]] = []
    exclusions: Counter = Counter()
    book_uid = f"raz_{level}_{book_id}"
    for idx, unit in enumerate(raw_units, start=1):
        page_number = find_page_number(unit, idx)
        records.append({
            "page_unit_uid": f"{book_uid}_p{idx:04d}",
            "book_uid": book_uid,
            "level": level,
            "book_id": book_id,
            "page_number": page_number,
            "sentence_uids": by_page.get(page_number, []),
            "source_ref": make_source_ref(raw_root, raw_path, "raw_page_unit", f"page_units[{idx}]"),
            "authority_status": "candidate_only",
            "normalization_status": "candidate_normalized",
            "content_authority_status": "not_promoted",
            "review_status": "pending",
        })
    return records, exclusions


def build_reuse_unit_records(raw_root: Path, raw_path: Path, level: str, book_id: str, data: Dict[str, Any], all_sentence_uids: List[str]) -> Tuple[List[Dict[str, Any]], Counter]:
    raw_units = data.get("reuse_unit_candidates")
    if not isinstance(raw_units, list):
        return [], Counter({"reuse_unit_candidates_missing_or_not_list": 1})
    records: List[Dict[str, Any]] = []
    exclusions: Counter = Counter()
    book_uid = f"raz_{level}_{book_id}"
    for idx, unit in enumerate(raw_units, start=1):
        page_number = find_page_number(unit, 0)
        page_range = [page_number, page_number] if page_number else [0, 0]
        records.append({
            "reuse_unit_uid": f"{book_uid}_r{idx:04d}",
            "book_uid": book_uid,
            "level": level,
            "book_id": book_id,
            "page_range": page_range,
            "sentence_uids": all_sentence_uids,
            "reuse_candidate_type": "reading_unit_candidate",
            "source_ref": make_source_ref(raw_root, raw_path, "raw_reuse_unit_candidate", f"reuse_unit_candidates[{idx}]"),
            "authority_status": "candidate_only",
            "normalization_status": "candidate_normalized",
            "content_authority_status": "not_promoted",
            "review_status": "pending",
        })
    return records, exclusions


def check_forbidden_keys(payload: Any, forbidden: set[str], path: str = "$", hits: Optional[List[str]] = None) -> List[str]:
    if hits is None:
        hits = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in forbidden:
                hits.append(f"{path}.{key}")
            check_forbidden_keys(value, forbidden, f"{path}.{key}", hits)
    elif isinstance(payload, list):
        for idx, value in enumerate(payload):
            check_forbidden_keys(value, forbidden, f"{path}[{idx}]", hits)
    return hits


def build(raw_root: Path, derived_root: Path, reports_dir: Path) -> Dict[str, Any]:
    total = Counter()
    level_counts: Dict[str, Dict[str, int]] = {}
    exclusion_counts: Counter = Counter()
    parse_failures: List[Dict[str, str]] = []
    source_counts = Counter()

    for level in EXPECTED_LEVELS:
        books: List[Dict[str, Any]] = []
        sentences: List[Dict[str, Any]] = []
        page_units: List[Dict[str, Any]] = []
        reuse_units: List[Dict[str, Any]] = []
        files = level_files(raw_root, level)
        for book_id_int, raw_path in files:
            book_id = str(book_id_int)
            try:
                data = read_json(raw_path)
            except Exception as exc:
                parse_failures.append({"level": level, "filename": raw_path.name, "error_type": type(exc).__name__})
                continue
            source_counts[str(data.get("source_type") or "MISSING")] += 1
            book_record = build_book_record(raw_root, raw_path, level, book_id, data)
            sentence_records, sentence_exclusions, by_page = build_sentence_records(raw_root, raw_path, level, book_id, data)
            page_records, page_exclusions = build_page_unit_records(raw_root, raw_path, level, book_id, data, by_page)
            all_sentence_uids = [r["sentence_uid"] for r in sentence_records]
            reuse_records, reuse_exclusions = build_reuse_unit_records(raw_root, raw_path, level, book_id, data, all_sentence_uids)
            books.append(book_record)
            sentences.extend(sentence_records)
            page_units.extend(page_records)
            reuse_units.extend(reuse_records)
            exclusion_counts.update(sentence_exclusions)
            exclusion_counts.update(page_exclusions)
            exclusion_counts.update(reuse_exclusions)

        out_dir = derived_root / f"Level_{level}" / "normalized"
        write_json(out_dir / f"raz_{level}_normalized_books.json", {"schema_version": "raz_normalized_books.v1", "records": books})
        write_json(out_dir / f"raz_{level}_normalized_sentences.json", {"schema_version": "raz_normalized_sentences.v1", "records": sentences})
        write_json(out_dir / f"raz_{level}_normalized_page_units.json", {"schema_version": "raz_normalized_page_units.v1", "records": page_units})
        write_json(out_dir / f"raz_{level}_normalized_reuse_units.json", {"schema_version": "raz_normalized_reuse_units.v1", "records": reuse_units})
        level_counts[level] = {
            "raw_file_count": len(files),
            "normalized_book_count": len(books),
            "normalized_sentence_count": len(sentences),
            "normalized_page_unit_count": len(page_units),
            "normalized_reuse_unit_count": len(reuse_units),
        }
        total.update(level_counts[level])

    status = "PASS"
    warnings: List[str] = []
    blockers: List[str] = []
    if parse_failures:
        status = "PASS_WITH_WARNINGS"
        warnings.append("one_or_more_raw_json_parse_failures")
    if total["normalized_book_count"] != 1959:
        status = "PASS_WITH_WARNINGS"
        warnings.append("normalized_book_count_differs_from_s2f_expected_1959")
    if total["normalized_sentence_count"] == 0:
        status = "BLOCKED"
        blockers.append("no_normalized_sentences_generated")

    summary = {
        "task_id": "RAZ-AW-S3C1_NormalizedBuilderImplementation",
        "report_type": "raz_aw_normalized_build_summary",
        "status": status,
        "sanitized": True,
        "contains_raw_text": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "derived_root": str(derived_root),
        "github_text_bearing_artifacts_committed": False,
        "authority_promotion": False,
        "tag_authority_promotion": False,
        "normalization_status": "candidate_normalized",
        "content_authority_status": "not_promoted",
        "review_status": "pending",
        "expected_book_count_from_s2f": 1959,
        "total_counts": dict(total),
        "level_counts": level_counts,
        "source_type_counts": dict(sorted(source_counts.items())),
        "exclusion_reason_counts": dict(sorted(exclusion_counts.items())),
        "parse_failure_count": len(parse_failures),
        "parse_failures_sample": parse_failures[:20],
        "warnings": warnings,
        "blockers": blockers,
    }
    safety = {
        "task_id": "RAZ-AW-S3C1_NormalizedBuilderImplementation",
        "report_type": "raz_aw_normalized_safety_report",
        "status": "PASS" if status != "BLOCKED" else "BLOCKED",
        "sanitized": True,
        "contains_raw_text": False,
        "raw_payload_keys_in_github_reports": [],
        "raw_audio_trace_emitted": False,
        "word_trace_emitted": False,
        "full_raw_json_emitted": False,
        "approved_or_promoted_status_emitted": False,
        "full_text_bearing_derived_artifacts_location": str(derived_root),
        "full_text_bearing_derived_artifacts_committed_to_github": False,
    }
    reconciliation = {
        "task_id": "RAZ-AW-S3C1_NormalizedBuilderImplementation",
        "report_type": "raz_aw_normalized_count_reconciliation_summary",
        "status": status,
        "expected_book_count_from_s2f": 1959,
        "actual_normalized_book_count": total["normalized_book_count"],
        "book_count_match": total["normalized_book_count"] == 1959,
        "level_counts": level_counts,
        "exclusion_reason_counts": dict(sorted(exclusion_counts.items())),
        "warnings": warnings,
        "blockers": blockers,
    }
    for payload in (summary, safety, reconciliation):
        hits = check_forbidden_keys(payload, FORBIDDEN_GITHUB_REPORT_KEYS)
        if hits:
            raise ValueError(f"forbidden GitHub report key emitted: {hits[:5]}")
    write_json(reports_dir / "raz_aw_normalized_build_summary.json", summary)
    write_json(reports_dir / "raz_aw_normalized_safety_report.json", safety)
    write_json(reports_dir / "raz_aw_normalized_count_reconciliation_summary.json", reconciliation)
    write_json(derived_root / "reports" / "raz_aw_normalized_local_manifest.json", {
        "schema_version": "raz_aw_normalized_local_manifest.v1",
        "derived_root": str(derived_root),
        "level_counts": level_counts,
    })
    write_json(derived_root / "reports" / "raz_aw_normalized_count_reconciliation.json", reconciliation)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build RAZ A-W normalized candidate artifacts from local raw JSON.")
    parser.add_argument("--raw-root", default="raz_output_jsons", help="Local raz_output_jsons root.")
    parser.add_argument("--derived-root", default="raz_output_jsons/derived", help="Derived output root.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Sanitized GitHub report directory.")
    args = parser.parse_args()
    raw_root = Path(args.raw_root).resolve()
    derived_root = Path(args.derived_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    if not raw_root.exists() or not raw_root.is_dir():
        payload = {
            "task_id": "RAZ-AW-S3C1_NormalizedBuilderImplementation",
            "status": "BLOCKED",
            "sanitized": True,
            "contains_raw_text": False,
            "blockers": ["raw_root_missing_or_not_directory"],
            "raw_root": str(raw_root),
        }
        write_json(reports_dir / "raz_aw_normalized_build_summary.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    summary = build(raw_root, derived_root, reports_dir)
    print(json.dumps({
        "status": summary["status"],
        "expected_book_count_from_s2f": summary["expected_book_count_from_s2f"],
        "normalized_book_count": summary["total_counts"].get("normalized_book_count", 0),
        "normalized_sentence_count": summary["total_counts"].get("normalized_sentence_count", 0),
        "normalized_page_unit_count": summary["total_counts"].get("normalized_page_unit_count", 0),
        "normalized_reuse_unit_count": summary["total_counts"].get("normalized_reuse_unit_count", 0),
        "warnings": summary["warnings"],
        "blockers": summary["blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if summary["status"] != "BLOCKED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
