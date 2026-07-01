from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
DERIVED_ROOT = BASE_DIR / "raz_output_jsons" / "derived"
INVENTORY_PATH = BASE_DIR / "ulga" / "graph" / "raz_level_discovery_inventory.json"
OUTPUT_PATH = BASE_DIR / "ulga" / "graph" / "raz_reading_authority_intake_candidates.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_builder_summary.json"
VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_builder_validation.json"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_raz_reading_authority_intake_schema import (  # noqa: E402
    SCHEMA_VERSION,
    UNIT_TYPES,
    validate_payload,
)


ALLOWED_REUSABILITY_TAGS = {
    "short_reading_seed",
    "writing_model_seed",
    "dialogue_rewrite_seed",
    "exercise_seed",
    "sequencing_seed",
    "picture_prompt_seed",
    "listening_audio_seed",
    "comprehension_question_seed",
    "grammar_pattern_seed",
    "vocabulary_exposure_seed",
    "assessment_seed",
    "future_unknown_use",
    "sentence_only",
}

LEGACY_TAG_MAPPINGS = {
    "page_unit": "short_reading_seed",
    "short_unit": "short_reading_seed",
    "multi_sentence_unit": "short_reading_seed",
}

LEGACY_USE_CASE_TAGS = {
    "reading": "short_reading_seed",
    "exercise": "exercise_seed",
}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stable_path(path: Path) -> str:
    try:
        return path.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_record_list(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return payload["records"]
    raise ValueError(f"unsupported record payload: {path}")


def resolve_existing(*paths: Path) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def simple_word_count(text: str) -> int:
    return len(text.split())


def _extract_numeric_suffix(value: str, pattern: str) -> str:
    match = re.search(pattern, value, re.IGNORECASE)
    if not match:
        raise ValueError(f"could not extract numeric suffix from {value}")
    return match.group(1).zfill(6)


def make_intake_id(level: str, book_id: str, unit_type: str, source_id: str) -> str:
    prefix = {
        "sentence": "SENT",
        "page_unit": "PAGE",
        "reuse_unit": "REUSE",
    }[unit_type]
    pattern = {
        "sentence": r"(?:CAND_|_s)(\d+)$",
        "page_unit": r"(?:P|_p)(\d+)$",
        "reuse_unit": r"(?:REUSE_|_r)(\d+)$",
    }[unit_type]
    ordinal = _extract_numeric_suffix(source_id, pattern)
    return f"RAZ_{level}_{book_id}_{prefix}_{ordinal}"


def _filter_reusability_tags(tags: list[str], *, fallback: list[str] | None = None) -> tuple[list[str], list[str]]:
    mapped: list[str] = []
    warnings: list[str] = []
    fallback = fallback or []

    for tag in tags:
        if tag in ALLOWED_REUSABILITY_TAGS:
            mapped.append(tag)
        elif tag in LEGACY_TAG_MAPPINGS:
            mapped.append(LEGACY_TAG_MAPPINGS[tag])
            warnings.append(f"mapped_legacy_reusability_tag:{tag}->{LEGACY_TAG_MAPPINGS[tag]}")
        else:
            warnings.append(f"unsupported_reusability_tag:{tag}")

    if not mapped:
        mapped.extend(fallback)
    if not mapped:
        mapped.append("future_unknown_use")
        warnings.append("fallback_reusability_tag:future_unknown_use")
    return sorted(set(mapped)), sorted(set(warnings))


def _normalize_theme_tags(record: dict[str, Any]) -> list[str]:
    theme_tags = record.get("theme_tags") or {}
    values = []
    for key in ["mapped_theme", "primary_theme"]:
        value = theme_tags.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value.strip().lower().replace(" ", "_"))
    return sorted(set(values))


def _normalize_vocab_tags(record: dict[str, Any]) -> list[str]:
    vocab_tags = ((record.get("linguistic_tags") or {}).get("vocabulary_tags")) or []
    values = []
    for item in vocab_tags:
        if isinstance(item, dict):
            value = item.get("normalized_word") or item.get("word")
            if isinstance(value, str) and value.strip():
                values.append(value.strip().lower())
        elif isinstance(item, str) and item.strip():
            values.append(item.strip().lower())
    return sorted(set(values))


def _normalize_grammar_tags(record: dict[str, Any]) -> list[str]:
    values = ((record.get("linguistic_tags") or {}).get("grammar_tags")) or []
    return sorted({value for value in values if isinstance(value, str) and value.strip()})


def _normalize_pattern_tags(record: dict[str, Any]) -> list[str]:
    values = ((record.get("linguistic_tags") or {}).get("sentence_pattern_tags")) or ((record.get("linguistic_tags") or {}).get("candidate_pattern_refs")) or []
    return sorted({value for value in values if isinstance(value, str) and value.strip()})


def _canonical_book_title(record: dict[str, Any]) -> str | None:
    source_tags = record.get("source_tags") or {}
    title = source_tags.get("book_title") or record.get("title")
    return title if isinstance(title, str) and title.strip() else None


class LevelContext:
    def __init__(self, level: str, derived_root: Path) -> None:
        self.level = level
        self.level_dir = derived_root / f"Level_{level}"
        self.enriched_sentence_path = resolve_existing(
            self.level_dir / "enriched" / f"raz_{level}_sentence_enriched.jsonl",
            self.level_dir / "enriched" / f"raz_{level}_enriched_sentences.json",
        )
        self.enriched_page_path = resolve_existing(
            self.level_dir / "enriched" / f"raz_{level}_page_unit_enriched.json",
            self.level_dir / "enriched" / f"raz_{level}_enriched_units.json",
        )
        self.enriched_reuse_path = resolve_existing(
            self.level_dir / "enriched" / f"raz_{level}_reuse_unit_enriched.json",
            self.level_dir / "enriched" / f"raz_{level}_enriched_units.json",
        )
        self.normalized_sentence_path = resolve_existing(
            self.level_dir / "normalized" / f"raz_{level}_sentence_normalized.jsonl",
            self.level_dir / "normalized" / f"raz_{level}_normalized_sentences.json",
        )
        self.normalized_page_path = resolve_existing(
            self.level_dir / "normalized" / f"raz_{level}_page_unit_normalized.json",
            self.level_dir / "normalized" / f"raz_{level}_normalized_page_units.json",
        )
        self.normalized_reuse_path = resolve_existing(
            self.level_dir / "normalized" / f"raz_{level}_reuse_unit_normalized.json",
            self.level_dir / "normalized" / f"raz_{level}_normalized_reuse_units.json",
        )

        self.enriched_sentence_records = self._load_records(self.enriched_sentence_path)
        self.enriched_page_records = self._load_records(self.enriched_page_path, unit_type="page_unit")
        self.enriched_reuse_records = self._load_records(self.enriched_reuse_path, unit_type="reuse_unit")
        self.normalized_sentence_records = self._load_records(self.normalized_sentence_path)
        self.normalized_page_records = self._load_records(self.normalized_page_path)
        self.normalized_reuse_records = self._load_records(self.normalized_reuse_path)

        self.normalized_sentence_by_id = {
            str(
                record.get("sentence_uid")
                or record.get("candidate_id")
                or record.get("sentence_id")
            ): record
            for record in self.normalized_sentence_records
        }
        self.normalized_page_by_id = {
            str(
                record.get("page_unit_uid")
                or record.get("page_unit_id")
                or record.get("unit_uid")
            ): record
            for record in self.normalized_page_records
        }
        self.normalized_reuse_by_id = {
            str(
                record.get("reuse_unit_uid")
                or record.get("reuse_unit_id")
                or record.get("unit_uid")
            ): record
            for record in self.normalized_reuse_records
        }
        self.page_unit_id_by_sentence_id = self._build_page_unit_lookup()
        self.sentence_text_by_id = self._build_sentence_text_lookup()

    def _load_records(self, path: Path | None, unit_type: str | None = None) -> list[dict[str, Any]]:
        if path is None or not path.exists():
            return []
        if path.suffix == ".jsonl":
            return load_jsonl_records(path)
        records = load_record_list(path)
        if unit_type and path.name.endswith("_enriched_units.json"):
            return [record for record in records if record.get("unit_type") == unit_type]
        return records

    def _build_page_unit_lookup(self) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for record in self.normalized_page_records:
            page_unit_id = str(record.get("page_unit_uid") or record.get("page_unit_id") or "")
            sentence_ids = record.get("sentence_uids") or record.get("sentence_candidate_ids") or []
            for sentence_id in sentence_ids:
                if isinstance(sentence_id, str) and sentence_id:
                    lookup[sentence_id] = page_unit_id
        return lookup

    def _build_sentence_text_lookup(self) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for record in self.enriched_sentence_records:
            key = str(record.get("candidate_id") or record.get("sentence_uid") or "")
            text = record.get("text")
            if key and isinstance(text, str) and text.strip():
                lookup[key] = text.strip()
        for record in self.normalized_sentence_records:
            key = str(record.get("candidate_id") or record.get("sentence_uid") or "")
            text = record.get("text")
            if key and isinstance(text, str) and text.strip() and key not in lookup:
                lookup[key] = text.strip()
        return lookup


def _record_is_generated(record: dict[str, Any]) -> bool:
    checks = [
        record.get("generated_content"),
        (record.get("source_tags") or {}).get("generated_content"),
        (record.get("qa_tags") or {}).get("generated_content"),
        (record.get("source_traceability") or {}).get("generated_content"),
    ]
    return any(value is True for value in checks)


def _build_text_from_sentences(sentence_ids: list[str], context: LevelContext) -> str:
    parts = [context.sentence_text_by_id.get(sentence_id, "").strip() for sentence_id in sentence_ids]
    parts = [part for part in parts if part]
    return " ".join(parts).strip()


def _warning_list(*items: list[str]) -> list[str]:
    flattened: list[str] = []
    for group in items:
        flattened.extend(group)
    return sorted(set(item for item in flattened if item))


def build_sentence_candidate(record: dict[str, Any], level_row: dict[str, Any], context: LevelContext) -> tuple[dict[str, Any] | None, list[str]]:
    if _record_is_generated(record):
        return None, ["generated_content_flagged"]

    canonical = "candidate_id" in record
    source_tags = record.get("source_tags") or {}
    normalized = None
    source_id = str(record.get("candidate_id") or record.get("sentence_uid") or "")
    if canonical:
        book_id = str(source_tags.get("book_id") or "")
        page_number = source_tags.get("page_number")
        page_unit_id = source_tags.get("page_unit_id")
        book_title = _canonical_book_title(record)
        sentence_ids = [source_id]
        clean_text = str(record.get("text") or "").strip()
        reusability_tags, tag_warnings = _filter_reusability_tags(
            list(((record.get("reuse_tags") or {}).get("reusability_tags")) or []),
            fallback=["sentence_only"],
        )
        theme_tags = _normalize_theme_tags(record)
        vocabulary_tags = _normalize_vocab_tags(record)
        grammar_tags = _normalize_grammar_tags(record)
        pattern_tags = _normalize_pattern_tags(record)
        cefr_estimate = ((record.get("linguistic_tags") or {}).get("cefr_estimate"))
    else:
        normalized = context.normalized_sentence_by_id.get(source_id) or {}
        book_id = str(normalized.get("book_id") or source_id.split("_")[2])
        page_number = normalized.get("page_number")
        page_unit_id = context.page_unit_id_by_sentence_id.get(source_id)
        book_title = None
        sentence_ids = [source_id]
        clean_text = str(record.get("text") or normalized.get("text") or "").strip()
        reusability_tags, tag_warnings = _filter_reusability_tags([], fallback=["sentence_only"])
        theme_tags = []
        vocabulary_tags = [str(item).lower() for item in (record.get("candidate_vocab_refs") or []) if str(item).strip()]
        grammar_tags = [str(item) for item in (record.get("candidate_grammar_refs") or []) if str(item).strip()]
        pattern_tags = [str(item) for item in (record.get("candidate_pattern_refs") or []) if str(item).strip()]
        cefr_estimate = None

    if not book_id:
        return None, ["missing_book_id"]
    if not clean_text:
        return None, ["missing_clean_text"]

    intake_id = make_intake_id(context.level, book_id, "sentence", source_id)
    candidate = {
        "reading_intake_id": intake_id,
        "schema_version": SCHEMA_VERSION,
        "source": "RAZ",
        "source_level": context.level,
        "normalized_level": context.level,
        "unit_type": "sentence",
        "source_traceability": {
            "source_type": "raz_enriched_sentence",
            "source_artifact_path": stable_path(context.enriched_sentence_path),
            "source_record_id": source_id,
            "book_id": book_id,
            "book_title": book_title,
            "page_number": page_number,
            "page_unit_id": page_unit_id,
            "source_sentence_candidate_ids": sentence_ids,
            "derived_from_original_text": True,
            "generated_content": False,
        },
        "text": {
            "clean_text": clean_text,
            "sentence_count": 1,
            "word_count": simple_word_count(clean_text),
            "text_language": "en",
            "text_role": "reading_source_text",
        },
        "pedagogical_tags": {
            "raz_level": context.level,
            "cefr_estimate": cefr_estimate,
            "theme_tags": theme_tags,
            "vocabulary_tags": sorted(set(vocabulary_tags)),
            "grammar_tags": sorted(set(grammar_tags)),
            "pattern_tags": sorted(set(pattern_tags)),
            "skill_area": ["reading"],
            "reusability_tags": reusability_tags,
        },
        "authority": {
            "authority_status": "candidate_only",
            "promotion_status": "not_promoted",
            "promotion_allowed": False,
            "requires_review": True,
            "review_status": "pending",
            "final_eligible": False,
        },
        "qa": {
            "blocked": False,
            "block_reasons": [],
            "warnings": _warning_list(tag_warnings, list((((record.get("qa_tags") or {}).get("warnings")) or []))),
            "source_integrity_status": "pass",
            "generated_content_block_status": "pass",
        },
        "query_layer_ready": bool(level_row.get("query_layer_ready")),
        "query_layer_approved": bool(level_row.get("query_layer_approved")),
    }
    return candidate, []


def build_page_unit_candidate(record: dict[str, Any], level_row: dict[str, Any], context: LevelContext) -> tuple[dict[str, Any] | None, list[str]]:
    if _record_is_generated(record):
        return None, ["generated_content_flagged"]

    canonical = "page_unit_id" in record
    source_tags = record.get("source_tags") or {}
    source_id = str(record.get("page_unit_id") or record.get("unit_uid") or record.get("page_unit_uid") or "")
    if canonical:
        book_id = str(record.get("book_id") or source_tags.get("book_id") or "")
        page_number = record.get("page_number") or source_tags.get("page_number")
        page_unit_id = str(record.get("page_unit_id") or "")
        sentence_ids = list(record.get("sentence_candidate_ids") or [])
        clean_text = str(record.get("text") or "").strip()
        book_title = _canonical_book_title(record)
        source_path = context.enriched_page_path
        raw_tags = list(((record.get("reuse_tags") or {}).get("reusability_tags")) or [])
        fallback = ["short_reading_seed"]
        theme_tags = _normalize_theme_tags(record)
        vocabulary_tags = []
        grammar_tags = []
        pattern_tags = []
        cefr_estimate = None
    else:
        normalized = context.normalized_page_by_id.get(source_id) or {}
        book_id = str(normalized.get("book_id") or record.get("book_id") or source_id.split("_")[2])
        page_number = normalized.get("page_number")
        page_unit_id = source_id
        sentence_ids = list(record.get("sentence_uids") or normalized.get("sentence_uids") or [])
        clean_text = _build_text_from_sentences(sentence_ids, context)
        book_title = None
        source_path = context.enriched_page_path
        raw_tags = list(record.get("candidate_reuse_tags") or [])
        raw_tags.extend(
            LEGACY_USE_CASE_TAGS.get(use_case, "")
            for use_case in (record.get("candidate_use_cases") or [])
            if LEGACY_USE_CASE_TAGS.get(use_case)
        )
        fallback = ["short_reading_seed"]
        theme_tags = []
        vocabulary_tags = []
        grammar_tags = []
        pattern_tags = []
        cefr_estimate = None

    if not book_id:
        return None, ["missing_book_id"]
    if page_number is None:
        return None, ["missing_page_number"]
    if not sentence_ids:
        return None, ["missing_source_sentence_candidate_ids"]
    if not clean_text:
        return None, ["missing_clean_text"]

    reusability_tags, tag_warnings = _filter_reusability_tags([tag for tag in raw_tags if isinstance(tag, str) and tag], fallback=fallback)
    intake_id = make_intake_id(context.level, book_id, "page_unit", page_unit_id)
    candidate = {
        "reading_intake_id": intake_id,
        "schema_version": SCHEMA_VERSION,
        "source": "RAZ",
        "source_level": context.level,
        "normalized_level": context.level,
        "unit_type": "page_unit",
        "source_traceability": {
            "source_type": "raz_enriched_page_unit",
            "source_artifact_path": stable_path(source_path),
            "source_record_id": source_id,
            "book_id": book_id,
            "book_title": book_title,
            "page_number": page_number,
            "page_unit_id": page_unit_id,
            "source_sentence_candidate_ids": sentence_ids,
            "derived_from_original_text": True,
            "generated_content": False,
        },
        "text": {
            "clean_text": clean_text,
            "sentence_count": int(record.get("sentence_count") or record.get("unit_sentence_count") or len(sentence_ids)),
            "word_count": simple_word_count(clean_text),
            "text_language": "en",
            "text_role": "reading_source_text",
        },
        "pedagogical_tags": {
            "raz_level": context.level,
            "cefr_estimate": cefr_estimate,
            "theme_tags": theme_tags,
            "vocabulary_tags": vocabulary_tags,
            "grammar_tags": grammar_tags,
            "pattern_tags": pattern_tags,
            "skill_area": ["reading"],
            "reusability_tags": reusability_tags,
        },
        "authority": {
            "authority_status": "candidate_only",
            "promotion_status": "not_promoted",
            "promotion_allowed": False,
            "requires_review": True,
            "review_status": "pending",
            "final_eligible": False,
        },
        "qa": {
            "blocked": False,
            "block_reasons": [],
            "warnings": _warning_list(tag_warnings, list((((record.get("qa_tags") or {}).get("warnings")) or []))),
            "source_integrity_status": "pass",
            "generated_content_block_status": "pass",
        },
        "query_layer_ready": bool(level_row.get("query_layer_ready")),
        "query_layer_approved": bool(level_row.get("query_layer_approved")),
    }
    return candidate, []


def build_reuse_unit_candidate(record: dict[str, Any], level_row: dict[str, Any], context: LevelContext) -> tuple[dict[str, Any] | None, list[str]]:
    if _record_is_generated(record):
        return None, ["generated_content_flagged"]

    canonical = "reuse_unit_id" in record
    source_tags = record.get("source_tags") or {}
    source_id = str(record.get("reuse_unit_id") or record.get("unit_uid") or record.get("reuse_unit_uid") or "")
    if canonical:
        book_id = str(record.get("book_id") or source_tags.get("book_id") or "")
        page_number = record.get("page_number") or source_tags.get("page_number")
        page_unit_id = str(record.get("source_page_unit_id") or source_tags.get("page_unit_id") or "")
        sentence_ids = list(record.get("source_sentence_candidate_ids") or [])
        clean_text = str(record.get("clean_text") or record.get("text") or "").strip()
        book_title = _canonical_book_title(record)
        source_path = context.enriched_reuse_path
        raw_tags = list(((record.get("reuse_tags") or {}).get("reusability_tags")) or [])
        fallback = ["short_reading_seed"]
        theme_tags = _normalize_theme_tags(record)
        vocabulary_tags = []
        grammar_tags = []
        pattern_tags = []
        cefr_estimate = None
    else:
        normalized = context.normalized_reuse_by_id.get(source_id) or {}
        book_id = str(normalized.get("book_id") or record.get("book_id") or source_id.split("_")[2])
        page_range = normalized.get("page_range") or []
        page_number = page_range[0] if page_range else None
        sentence_ids = list(record.get("sentence_uids") or normalized.get("sentence_uids") or [])
        page_unit_id = ""
        for sentence_id in sentence_ids:
            page_unit_id = context.page_unit_id_by_sentence_id.get(sentence_id, "")
            if page_unit_id:
                break
        clean_text = str(_build_text_from_sentences(sentence_ids, context) or "").strip()
        book_title = None
        source_path = context.enriched_reuse_path
        raw_tags = list(record.get("candidate_reuse_tags") or [])
        raw_tags.extend(
            LEGACY_USE_CASE_TAGS.get(use_case, "")
            for use_case in (record.get("candidate_use_cases") or [])
            if LEGACY_USE_CASE_TAGS.get(use_case)
        )
        fallback = ["short_reading_seed"]
        theme_tags = []
        vocabulary_tags = []
        grammar_tags = []
        pattern_tags = []
        cefr_estimate = None

    if not book_id:
        return None, ["missing_book_id"]
    if page_number is None:
        return None, ["missing_page_number"]
    if not page_unit_id:
        return None, ["missing_page_unit_id"]
    if not sentence_ids:
        return None, ["missing_source_sentence_candidate_ids"]
    if not clean_text:
        return None, ["missing_clean_text"]

    reusability_tags, tag_warnings = _filter_reusability_tags([tag for tag in raw_tags if isinstance(tag, str) and tag], fallback=fallback)
    intake_id = make_intake_id(context.level, book_id, "reuse_unit", source_id)
    candidate = {
        "reading_intake_id": intake_id,
        "schema_version": SCHEMA_VERSION,
        "source": "RAZ",
        "source_level": context.level,
        "normalized_level": context.level,
        "unit_type": "reuse_unit",
        "source_traceability": {
            "source_type": "raz_enriched_reuse_unit",
            "source_artifact_path": stable_path(source_path),
            "source_record_id": source_id,
            "book_id": book_id,
            "book_title": book_title,
            "page_number": page_number,
            "page_unit_id": page_unit_id,
            "source_sentence_candidate_ids": sentence_ids,
            "derived_from_original_text": True,
            "generated_content": False,
        },
        "text": {
            "clean_text": clean_text,
            "sentence_count": int(record.get("sentence_count") or record.get("unit_sentence_count") or len(sentence_ids)),
            "word_count": simple_word_count(clean_text),
            "text_language": "en",
            "text_role": "reading_source_text",
        },
        "pedagogical_tags": {
            "raz_level": context.level,
            "cefr_estimate": cefr_estimate,
            "theme_tags": theme_tags,
            "vocabulary_tags": vocabulary_tags,
            "grammar_tags": grammar_tags,
            "pattern_tags": pattern_tags,
            "skill_area": ["reading"],
            "reusability_tags": reusability_tags,
        },
        "authority": {
            "authority_status": "candidate_only",
            "promotion_status": "not_promoted",
            "promotion_allowed": False,
            "requires_review": True,
            "review_status": "pending",
            "final_eligible": False,
        },
        "qa": {
            "blocked": False,
            "block_reasons": [],
            "warnings": _warning_list(tag_warnings, list((((record.get("qa_tags") or {}).get("warnings")) or []))),
            "source_integrity_status": "pass",
            "generated_content_block_status": "pass",
        },
        "query_layer_ready": bool(level_row.get("query_layer_ready")),
        "query_layer_approved": bool(level_row.get("query_layer_approved")),
    }
    return candidate, []


def build_records_for_level(level_row: dict[str, Any], derived_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    level = level_row["normalized_level"]
    context = LevelContext(level, derived_root)
    records: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    warnings: list[str] = []

    for unit_type, source_records, mapper in [
        ("sentence", context.enriched_sentence_records, build_sentence_candidate),
        ("page_unit", context.enriched_page_records, build_page_unit_candidate),
        ("reuse_unit", context.enriched_reuse_records, build_reuse_unit_candidate),
    ]:
        for source_record in source_records:
            candidate, reasons = mapper(source_record, level_row, context)
            source_id = str(
                source_record.get("candidate_id")
                or source_record.get("page_unit_id")
                or source_record.get("reuse_unit_id")
                or source_record.get("sentence_uid")
                or source_record.get("unit_uid")
                or source_record.get("page_unit_uid")
                or source_record.get("reuse_unit_uid")
                or "<missing>"
            )
            if candidate is None:
                blocked.append({
                    "level": level,
                    "unit_type": unit_type,
                    "source_record_id": source_id,
                    "reasons": reasons,
                })
                continue
            warnings.extend(candidate["qa"]["warnings"])
            records.append(candidate)

    return records, blocked, sorted(set(warnings))


def build_and_write_artifacts(
    *,
    inventory_path: Path = INVENTORY_PATH,
    derived_root: Path = DERIVED_ROOT,
    output_path: Path = OUTPUT_PATH,
    summary_path: Path = SUMMARY_PATH,
    validation_path: Path = VALIDATION_PATH,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    inventory = load_json(inventory_path)
    levels = [row for row in inventory if row.get("normalized_level")]

    all_records: list[dict[str, Any]] = []
    blocked_records: list[dict[str, Any]] = []
    emitted_warnings: list[str] = []
    seen_ids: set[str] = set()
    duplicate_id_count = 0

    for level_row in levels:
        records, blocked, warnings = build_records_for_level(level_row, derived_root)
        blocked_records.extend(blocked)
        emitted_warnings.extend(warnings)
        for record in records:
            intake_id = record["reading_intake_id"]
            if intake_id in seen_ids:
                duplicate_id_count += 1
                blocked_records.append({
                    "level": record["source_level"],
                    "unit_type": record["unit_type"],
                    "source_record_id": record["source_traceability"]["source_record_id"],
                    "reasons": [f"duplicate_intake_id:{intake_id}"],
                })
                continue
            seen_ids.add(intake_id)
            all_records.append(record)

    payload = {
        "task": "RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation",
        "schema_version": SCHEMA_VERSION,
        "records": all_records,
    }
    write_json(output_path, payload)

    validation_result = validate_payload(payload, max_warnings=200)
    records_by_unit_type = Counter(record["unit_type"] for record in all_records)
    records_by_level: dict[str, dict[str, int]] = defaultdict(lambda: {unit_type: 0 for unit_type in UNIT_TYPES})
    for record in all_records:
        records_by_level[record["source_level"]][record["unit_type"]] += 1

    summary = {
        "task": "RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation",
        "status": "IMPLEMENTED" if validation_result["status"] == "PASS" else "BLOCKED",
        "schema_version": SCHEMA_VERSION,
        "levels_processed": [row["normalized_level"] for row in levels],
        "total_records": len(all_records),
        "records_by_unit_type": {
            "sentence": records_by_unit_type.get("sentence", 0),
            "page_unit": records_by_unit_type.get("page_unit", 0),
            "reuse_unit": records_by_unit_type.get("reuse_unit", 0),
        },
        "records_by_level": dict(sorted(records_by_level.items())),
        "query_layer_ready_levels": sorted({record["source_level"] for record in all_records if record.get("query_layer_ready") is True}),
        "authority_status": "candidate_only",
        "promotion_allowed": False,
        "generated_content_allowed": False,
        "blocked_record_count": len(blocked_records),
        "warning_count": validation_result["warning_count"] + len(set(emitted_warnings)),
        "recommended_next_task": "RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA",
    }

    promotion_violation_count = sum(1 for record in all_records if record["authority"]["promotion_allowed"] is not False or record["authority"]["authority_status"] != "candidate_only" or record["authority"]["final_eligible"] is not False)
    generated_content_violation_count = sum(1 for record in all_records if record["source_traceability"]["generated_content"] is not False or record["source_traceability"]["derived_from_original_text"] is not True)
    missing_traceability_count = sum(1 for record in all_records if not record.get("source_traceability"))
    validation = {
        "task": "RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation",
        "status": "PASS" if validation_result["status"] == "PASS" and duplicate_id_count == 0 and promotion_violation_count == 0 and generated_content_violation_count == 0 and missing_traceability_count == 0 else "FAIL",
        "schema_validation_status": validation_result["status"],
        "blocking_error_count": len(validation_result["blocking_errors"]) + len(blocked_records),
        "warning_count": validation_result["warning_count"] + len(set(emitted_warnings)),
        "records_checked": validation_result["records_checked"],
        "duplicate_id_count": duplicate_id_count,
        "promotion_violation_count": promotion_violation_count,
        "generated_content_violation_count": generated_content_violation_count,
        "missing_traceability_count": missing_traceability_count,
        "blocked_records": blocked_records,
        "warnings": sorted(set(validation_result["warnings"]) | set(emitted_warnings)),
    }

    write_json(summary_path, summary)
    write_json(validation_path, validation)
    return payload, summary, validation


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic RAZ reading authority intake candidate staging output.")
    parser.add_argument("--inventory-path", default=str(INVENTORY_PATH))
    parser.add_argument("--derived-root", default=str(DERIVED_ROOT))
    parser.add_argument("--output-path", default=str(OUTPUT_PATH))
    parser.add_argument("--summary-path", default=str(SUMMARY_PATH))
    parser.add_argument("--validation-path", default=str(VALIDATION_PATH))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload, summary, validation = build_and_write_artifacts(
        inventory_path=Path(args.inventory_path),
        derived_root=Path(args.derived_root),
        output_path=Path(args.output_path),
        summary_path=Path(args.summary_path),
        validation_path=Path(args.validation_path),
    )
    print(json.dumps({
        "output_path": stable_path(Path(args.output_path)),
        "summary_path": stable_path(Path(args.summary_path)),
        "validation_path": stable_path(Path(args.validation_path)),
        "total_records": len(payload["records"]),
        "records_by_unit_type": summary["records_by_unit_type"],
        "status": validation["status"],
    }, ensure_ascii=False, indent=2))
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
