#!/usr/bin/env python3
"""Build RAZ A-W enriched candidate artifacts from normalized candidates.

S3D1 contract:
- Reads local/Drive-derived normalized artifacts under raz_output_jsons/derived.
- Writes full text-bearing enriched artifacts under raz_output_jsons/derived.
- Writes only sanitized summaries to reports/raz for GitHub commit.
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
EXPECTED_COUNTS = {
    "book_count": 1959,
    "sentence_count": 201993,
    "page_unit_count": 22632,
    "reuse_unit_count": 19332,
}
NORMALIZED_FILENAMES = {
    "books": "raz_{level}_normalized_books.json",
    "sentences": "raz_{level}_normalized_sentences.json",
    "page_units": "raz_{level}_normalized_page_units.json",
    "reuse_units": "raz_{level}_normalized_reuse_units.json",
}
ENRICHED_FILENAMES = {
    "books": "raz_{level}_enriched_books.json",
    "sentences": "raz_{level}_enriched_sentences.json",
    "units": "raz_{level}_enriched_units.json",
}
FORBIDDEN_GITHUB_REPORT_KEYS = {
    "text",
    "raw_text",
    "page_text",
    "full_raw_json",
    "sentence_candidates",
    "legacy_story_sentences",
    "audio_trace",
    "word_trace",
}
TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?")


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("top_level_json_is_not_object")
    return data


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    value = payload.get("records")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def tokenize(value: Any) -> List[str]:
    if not isinstance(value, str):
        return []
    return TOKEN_RE.findall(value)


def length_bucket(token_count: int) -> str:
    if token_count <= 0:
        return "not_evaluated"
    if token_count <= 4:
        return "very_short"
    if token_count <= 8:
        return "short"
    if token_count <= 16:
        return "medium"
    if token_count <= 28:
        return "long"
    return "very_long"


def complexity_bucket(avg_tokens: float) -> str:
    if avg_tokens <= 0:
        return "not_evaluated"
    if avg_tokens <= 5:
        return "very_low"
    if avg_tokens <= 9:
        return "low"
    if avg_tokens <= 15:
        return "medium"
    if avg_tokens <= 25:
        return "high"
    return "very_high"


def punctuation_profile(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    terminal = "none"
    if stripped:
        last = stripped[-1]
        if last in ".?!":
            terminal = last
        elif not last.isalnum():
            terminal = "other"
    return {
        "terminal_punctuation": terminal,
        "contains_comma": "," in text,
        "contains_question_mark": "?" in text,
        "contains_exclamation_mark": "!" in text,
        "contains_quote_mark": any(mark in text for mark in ['"', "'", "“", "”", "‘", "’"]),
    }


def is_dialogue_candidate(text: str, profile: Dict[str, Any]) -> bool:
    lowered = text.lower()
    if profile["contains_quote_mark"]:
        return True
    if profile["contains_question_mark"] or profile["contains_exclamation_mark"]:
        return True
    if re.match(r"^(he|she|they|i|we|you)\s+(said|asked|told|shouted|called)\b", lowered):
        return True
    return False


def score_unit(unit_type: str, sentence_count: int, token_count: int, dialogue_count: int, question_count: int) -> Tuple[float, float, float, List[str], List[str]]:
    if sentence_count <= 0:
        return 0.0, 0.0, 0.0, [], []
    reading = min(1.0, 0.35 + min(sentence_count, 10) * 0.05 + min(token_count, 120) / 600)
    dialogue = min(1.0, dialogue_count / max(sentence_count, 1) + question_count * 0.05)
    exercise = min(1.0, 0.2 + min(sentence_count, 8) * 0.04 + min(token_count, 80) / 300)
    use_cases = ["reading"]
    if dialogue >= 0.25:
        use_cases.append("dialogue")
    if exercise >= 0.35:
        use_cases.append("exercise")
    if sentence_count <= 3:
        use_cases.append("review")
    tags = [unit_type]
    if sentence_count == 1:
        tags.append("single_sentence")
    elif sentence_count <= 4:
        tags.append("short_unit")
    else:
        tags.append("multi_sentence_unit")
    return round(reading, 4), round(dialogue, 4), round(exercise, 4), sorted(set(use_cases)), sorted(set(tags))


def check_report_safety(payload: Any, path: str = "$", hits: Optional[List[str]] = None) -> List[str]:
    if hits is None:
        hits = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in FORBIDDEN_GITHUB_REPORT_KEYS:
                hits.append(f"{path}.{key}")
            check_report_safety(value, f"{path}.{key}", hits)
    elif isinstance(payload, list):
        for idx, value in enumerate(payload):
            check_report_safety(value, f"{path}[{idx}]", hits)
    return hits


def load_level_normalized(derived_root: Path, level: str) -> Dict[str, List[Dict[str, Any]]]:
    root = derived_root / f"Level_{level}" / "normalized"
    loaded: Dict[str, List[Dict[str, Any]]] = {}
    for kind, pattern in NORMALIZED_FILENAMES.items():
        loaded[kind] = records(read_json(root / pattern.format(level=level)))
    return loaded


def build_level(level: str, normalized: Dict[str, List[Dict[str, Any]]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    books = normalized["books"]
    sentences = normalized["sentences"]
    page_units = normalized["page_units"]
    reuse_units = normalized["reuse_units"]

    sentence_by_uid: Dict[str, Dict[str, Any]] = {str(item.get("sentence_uid")): item for item in sentences}
    sentences_by_book: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    page_units_by_book: Counter = Counter()
    reuse_units_by_book: Counter = Counter()

    enriched_sentences: List[Dict[str, Any]] = []
    token_count_by_sentence: Dict[str, int] = {}
    dialogue_by_sentence: Dict[str, bool] = {}
    question_by_sentence: Dict[str, bool] = {}
    sentence_bucket_counts: Counter = Counter()
    punctuation_counts: Counter = Counter()

    for sentence in sentences:
        uid = str(sentence.get("sentence_uid"))
        book_uid = str(sentence.get("book_uid"))
        text = str(sentence.get("text") or "")
        tokens = tokenize(text)
        token_count = len(tokens)
        profile = punctuation_profile(text)
        dialogue_flag = is_dialogue_candidate(text, profile)
        bucket = length_bucket(token_count)
        token_count_by_sentence[uid] = token_count
        dialogue_by_sentence[uid] = dialogue_flag
        question_by_sentence[uid] = profile["contains_question_mark"]
        sentences_by_book[book_uid].append(sentence)
        sentence_bucket_counts[bucket] += 1
        punctuation_counts[profile["terminal_punctuation"]] += 1
        enriched_sentences.append({
            "sentence_uid": uid,
            "book_uid": book_uid,
            "level": level,
            "text": text,
            "normalized_token_count": token_count,
            "candidate_vocab_refs": [],
            "candidate_grammar_refs": [],
            "candidate_pattern_refs": [],
            "sentence_length_bucket": bucket,
            "punctuation_profile": profile,
            "dialogue_candidate_flag": dialogue_flag,
            "reading_sentence_candidate_flag": True,
            "authority_linkage_status": "not_evaluated",
            "enrichment_status": "candidate_enriched",
            "review_status": "pending",
            "validation_status": "not_evaluated",
        })

    for unit in page_units:
        page_units_by_book[str(unit.get("book_uid"))] += 1
    for unit in reuse_units:
        reuse_units_by_book[str(unit.get("book_uid"))] += 1

    enriched_books: List[Dict[str, Any]] = []
    complexity_counts: Counter = Counter()
    for book in books:
        book_uid = str(book.get("book_uid"))
        book_sentences = sentences_by_book.get(book_uid, [])
        sentence_count = len(book_sentences)
        total_tokens = sum(token_count_by_sentence.get(str(s.get("sentence_uid")), 0) for s in book_sentences)
        avg_tokens = total_tokens / sentence_count if sentence_count else 0
        complexity = complexity_bucket(avg_tokens)
        complexity_counts[complexity] += 1
        candidate_pedagogical_tags: List[str] = []
        if any(dialogue_by_sentence.get(str(s.get("sentence_uid")), False) for s in book_sentences):
            candidate_pedagogical_tags.append("dialogue_candidate")
        if any(question_by_sentence.get(str(s.get("sentence_uid")), False) for s in book_sentences):
            candidate_pedagogical_tags.append("question_practice_candidate")
        enriched_books.append({
            "book_uid": book_uid,
            "level": level,
            "book_id": str(book.get("book_id")),
            "title": str(book.get("title") or "UNTITLED"),
            "sentence_count": sentence_count,
            "page_unit_count": int(page_units_by_book[book_uid]),
            "reuse_unit_count": int(reuse_units_by_book[book_uid]),
            "estimated_text_complexity_bucket": complexity,
            "candidate_theme_tags": [],
            "candidate_content_unit_tags": ["raz_book_candidate"],
            "candidate_pedagogical_tags": sorted(set(candidate_pedagogical_tags)),
            "authority_linkage_status": "not_evaluated",
            "enrichment_status": "candidate_enriched",
            "review_status": "pending",
            "validation_status": "not_evaluated",
        })

    enriched_units: List[Dict[str, Any]] = []
    unit_type_counts: Counter = Counter()
    use_case_counts: Counter = Counter()

    def enrich_unit(unit: Dict[str, Any], uid_field: str, unit_type: str) -> None:
        refs = [ref for ref in unit.get("sentence_uids", []) if isinstance(ref, str)]
        unique_refs = sorted(set(refs), key=refs.index)
        unit_token_count = sum(token_count_by_sentence.get(ref, 0) for ref in unique_refs)
        dialogue_count = sum(1 for ref in unique_refs if dialogue_by_sentence.get(ref, False))
        question_count = sum(1 for ref in unique_refs if question_by_sentence.get(ref, False))
        reading, dialogue, exercise, use_cases, tags = score_unit(unit_type, len(unique_refs), unit_token_count, dialogue_count, question_count)
        unit_type_counts[unit_type] += 1
        for use_case in use_cases:
            use_case_counts[use_case] += 1
        enriched_units.append({
            "unit_uid": str(unit.get(uid_field)),
            "unit_type": unit_type,
            "book_uid": str(unit.get("book_uid")),
            "level": level,
            "sentence_uids": unique_refs,
            "unit_sentence_count": len(unique_refs),
            "unit_token_count": unit_token_count,
            "candidate_use_cases": use_cases,
            "candidate_reuse_tags": tags,
            "reading_usefulness_score_candidate": reading,
            "dialogue_usefulness_score_candidate": dialogue,
            "exercise_usefulness_score_candidate": exercise,
            "authority_linkage_status": "not_evaluated",
            "enrichment_status": "candidate_enriched",
            "review_status": "pending",
            "validation_status": "not_evaluated",
        })

    for unit in page_units:
        enrich_unit(unit, "page_unit_uid", "page_unit")
    for unit in reuse_units:
        enrich_unit(unit, "reuse_unit_uid", "reuse_unit")

    stats = {
        "sentence_length_bucket_counts": dict(sentence_bucket_counts),
        "terminal_punctuation_counts": dict(punctuation_counts),
        "book_complexity_bucket_counts": dict(complexity_counts),
        "unit_type_counts": dict(unit_type_counts),
        "candidate_use_case_counts": dict(use_case_counts),
    }
    return enriched_books, enriched_sentences, enriched_units, stats


def build(derived_root: Path, reports_dir: Path) -> Dict[str, Any]:
    totals: Counter = Counter()
    level_counts: Dict[str, Dict[str, int]] = {}
    aggregate_stats: Dict[str, Counter] = {
        "sentence_length_bucket_counts": Counter(),
        "terminal_punctuation_counts": Counter(),
        "book_complexity_bucket_counts": Counter(),
        "unit_type_counts": Counter(),
        "candidate_use_case_counts": Counter(),
    }
    missing_input_files: List[str] = []
    parse_failures: List[Dict[str, str]] = []

    for level in EXPECTED_LEVELS:
        try:
            normalized = load_level_normalized(derived_root, level)
            enriched_books, enriched_sentences, enriched_units, stats = build_level(level, normalized)
        except FileNotFoundError as exc:
            missing_input_files.append(str(exc.filename))
            continue
        except Exception as exc:
            parse_failures.append({"level": level, "error_type": type(exc).__name__})
            continue

        out_dir = derived_root / f"Level_{level}" / "enriched"
        write_json(out_dir / ENRICHED_FILENAMES["books"].format(level=level), {"schema_version": "raz_enriched_books.v1", "records": enriched_books})
        write_json(out_dir / ENRICHED_FILENAMES["sentences"].format(level=level), {"schema_version": "raz_enriched_sentences.v1", "records": enriched_sentences})
        write_json(out_dir / ENRICHED_FILENAMES["units"].format(level=level), {"schema_version": "raz_enriched_units.v1", "records": enriched_units})

        counts = {
            "book_count": len(enriched_books),
            "sentence_count": len(enriched_sentences),
            "unit_count": len(enriched_units),
        }
        level_counts[level] = counts
        totals.update(counts)
        for key, values in stats.items():
            aggregate_stats[key].update(values)

    blockers: List[str] = []
    warnings: List[str] = []
    if missing_input_files:
        blockers.append("missing_normalized_input_files")
    if parse_failures:
        blockers.append("normalized_input_parse_or_build_failure")
    if totals["book_count"] != EXPECTED_COUNTS["book_count"]:
        blockers.append("book_count_mismatch")
    if totals["sentence_count"] != EXPECTED_COUNTS["sentence_count"]:
        blockers.append("sentence_count_mismatch")
    expected_units = EXPECTED_COUNTS["page_unit_count"] + EXPECTED_COUNTS["reuse_unit_count"]
    if totals["unit_count"] != expected_units:
        blockers.append("unit_count_mismatch")
    status = "PASS" if not blockers else "BLOCKED"

    aggregate_stats_out = {key: dict(counter) for key, counter in aggregate_stats.items()}
    summary = {
        "task_id": "RAZ-AW-S3D1_EnrichedBuilderImplementation",
        "report_type": "raz_aw_enriched_build_summary",
        "status": status,
        "sanitized": True,
        "contains_text_values": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "text_bearing_enriched_artifacts_committed_to_github": False,
        "derived_root": str(derived_root),
        "authority_promotion": False,
        "tag_authority_promotion": False,
        "generation_approved": False,
        "runtime_api_integration": False,
        "expected_counts": {**EXPECTED_COUNTS, "unit_count": expected_units},
        "actual_counts": dict(totals),
        "level_counts": level_counts,
        "aggregate_feature_counts": aggregate_stats_out,
        "missing_input_file_count": len(missing_input_files),
        "missing_input_files_sample": missing_input_files[:20],
        "parse_failure_count": len(parse_failures),
        "parse_failures_sample": parse_failures[:20],
        "warnings": warnings,
        "blockers": blockers,
    }
    safety = {
        "task_id": "RAZ-AW-S3D1_EnrichedBuilderImplementation",
        "report_type": "raz_aw_enriched_safety_report",
        "status": "PASS" if not blockers else "BLOCKED",
        "sanitized": True,
        "contains_text_values": False,
        "raw_mutation": False,
        "raw_commit_allowed": False,
        "text_bearing_enriched_artifacts_location": str(derived_root),
        "text_bearing_enriched_artifacts_committed_to_github": False,
        "content_authority_promotion": False,
        "tag_authority_promotion": False,
        "approved_linkage_emitted": False,
    }
    reconciliation = {
        "task_id": "RAZ-AW-S3D1_EnrichedBuilderImplementation",
        "report_type": "raz_aw_enriched_count_reconciliation_summary",
        "status": status,
        "expected_counts": {**EXPECTED_COUNTS, "unit_count": expected_units},
        "actual_counts": dict(totals),
        "level_counts": level_counts,
        "warnings": warnings,
        "blockers": blockers,
    }
    for payload in (summary, safety, reconciliation):
        hits = check_report_safety(payload)
        if hits:
            raise ValueError(f"unsafe_github_report_key_emitted: {hits[:5]}")

    write_json(reports_dir / "raz_aw_enriched_build_summary.json", summary)
    write_json(reports_dir / "raz_aw_enriched_safety_report.json", safety)
    write_json(reports_dir / "raz_aw_enriched_count_reconciliation_summary.json", reconciliation)
    write_json(derived_root / "reports" / "raz_aw_enriched_local_manifest.json", {
        "schema_version": "raz_aw_enriched_local_manifest.v1",
        "derived_root": str(derived_root),
        "level_counts": level_counts,
    })
    write_json(derived_root / "reports" / "raz_aw_enriched_count_reconciliation.json", reconciliation)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build RAZ A-W enriched candidate artifacts from normalized artifacts.")
    parser.add_argument("--derived-root", default="raz_output_jsons/derived", help="Derived root containing Level_<LEVEL>/normalized folders.")
    parser.add_argument("--reports-dir", default="reports/raz", help="Sanitized GitHub report directory.")
    args = parser.parse_args()
    derived_root = Path(args.derived_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    if not derived_root.exists() or not derived_root.is_dir():
        payload = {
            "task_id": "RAZ-AW-S3D1_EnrichedBuilderImplementation",
            "status": "BLOCKED",
            "sanitized": True,
            "contains_text_values": False,
            "blockers": ["derived_root_missing_or_not_directory"],
            "derived_root": str(derived_root),
        }
        write_json(reports_dir / "raz_aw_enriched_build_summary.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    summary = build(derived_root, reports_dir)
    print(json.dumps({
        "status": summary["status"],
        "actual_counts": summary["actual_counts"],
        "warnings": summary["warnings"],
        "blockers": summary["blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
