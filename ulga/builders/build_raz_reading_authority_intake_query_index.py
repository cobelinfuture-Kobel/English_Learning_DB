import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

INDEX_PATH = BASE_DIR / "ulga" / "graph" / "raz_reading_authority_intake_query_index.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_query_index_summary.json"

SCHEMA_VERSION = "RAZ_READING_AUTHORITY_INTAKE_QUERY_INDEX_V1"
SUMMARY_SCHEMA_VERSION = "RAZ_READING_AUTHORITY_INTAKE_QUERY_INDEX_SUMMARY_V1"
BUILDER_TASK = "RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexBuilderImplementation"

QUERY_INDEX_KEYS = [
    "by_level",
    "by_book_id",
    "by_level_and_book",
    "by_source_type",
    "by_reusability_tag",
    "by_authority_status",
    "by_promotion_status",
    "by_sentence_count_bucket",
    "by_multi_sentence_status",
    "by_theme_hint",
    "by_grammar_tag",
    "by_pattern_tag",
    "by_vocabulary_tag",
]

SOURCE_ROOTS = [
    BASE_DIR / "work" / "raz",
    BASE_DIR / "raz_output_jsons",
    BASE_DIR / "output" / "raz",
    BASE_DIR / "ulga" / "graph",
    BASE_DIR / "ulga" / "reports",
]

ALLOWED_SOURCE_TYPES = {
    "sentence_candidate",
    "page_unit",
    "reuse_unit_candidate",
    "normalized_reading_unit",
    "enriched_reading_unit",
}


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def read_json_or_jsonl(path):
    if path.suffix == ".jsonl":
        records = []
        with path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path.as_posix()}:{line_number}: {exc}") from exc
        return records

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def relative_path(path):
    return path.relative_to(BASE_DIR).as_posix()


def discover_source_paths():
    candidates = []
    excluded = {
        INDEX_PATH.resolve(),
        SUMMARY_PATH.resolve(),
    }

    for root in SOURCE_ROOTS:
        if not root.exists():
            continue
        for suffix in ("*.json", "*.jsonl"):
            for path in root.rglob(suffix):
                resolved = path.resolve()
                if resolved in excluded:
                    continue
                text = path.as_posix().lower()
                if "raz_reading_authority_intake_query_index" in text:
                    continue
                if "raz" not in text and "level_" not in text:
                    continue
                candidates.append(path)

    return sorted(set(candidates), key=lambda p: relative_path(p))


def classify_source_type(path, record):
    text = path.as_posix().lower()
    explicit = str(record.get("source_type") or record.get("unit_type") or "").strip().lower()
    if explicit in ALLOWED_SOURCE_TYPES:
        return explicit

    if "reuse" in text or "reusability" in text:
        return "reuse_unit_candidate"
    if "page_unit" in text or "page-units" in text or "page_units" in text:
        return "page_unit"
    if "sentence_candidate" in text or "sentence-candidates" in text or "sentence_candidates" in text:
        return "sentence_candidate"
    if "enriched" in text:
        return "enriched_reading_unit"
    if "normalized" in text:
        return "normalized_reading_unit"
    if "sentence" in text:
        return "sentence_candidate"
    if "page" in text:
        return "page_unit"
    return "normalized_reading_unit"


def normalize_scalar(value):
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def normalize_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        output = []
        for item in value:
            if isinstance(item, dict):
                item = (
                    item.get("id")
                    or item.get("tag")
                    or item.get("value")
                    or item.get("name")
                    or item.get("text")
                    or item.get("word")
                    or item.get("pattern")
                )
            normalized = normalize_scalar(item)
            if normalized:
                output.append(normalized)
        return sorted(dict.fromkeys(output))
    normalized = normalize_scalar(value)
    return [normalized] if normalized else []


def get_first(record, keys):
    for key in keys:
        if key in record and record[key] not in (None, "", []):
            return record[key]
    return None


def extract_text_from_sentence_item(item):
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        value = get_first(item, ["clean_text", "sentence", "text", "content", "raw_text"])
        if isinstance(value, str):
            return value.strip()
    return ""


def extract_clean_text(record):
    value = get_first(
        record,
        [
            "clean_text",
            "reading_text",
            "page_text",
            "passage_text",
            "normalized_text",
            "text",
            "content",
            "sentence",
            "raw_text",
        ],
    )
    if isinstance(value, str):
        return value.strip()

    sentences = get_first(record, ["sentences", "sentence_candidates", "source_sentences", "lines"])
    if isinstance(sentences, list):
        parts = [extract_text_from_sentence_item(item) for item in sentences]
        return "\n".join(part for part in parts if part).strip()

    return ""


def is_candidate_record(path, record):
    if not isinstance(record, dict):
        return False
    if "raz_reading_authority_intake_query_index" in path.as_posix().lower():
        return False
    if extract_clean_text(record):
        return True

    candidate_keys = {
        "sentence_count",
        "source_sentence_candidate_ids",
        "reusability_tags",
        "reuse_unit_id",
        "page_unit_id",
        "sentence_candidate_id",
    }
    return bool(candidate_keys & set(record))


def iter_candidate_records(data, path):
    if isinstance(data, list):
        for item in data:
            yield from iter_candidate_records(item, path)
    elif isinstance(data, dict):
        if is_candidate_record(path, data):
            yield data
            return
        for value in data.values():
            if isinstance(value, (dict, list)):
                yield from iter_candidate_records(value, path)


def extract_level(record, path):
    value = get_first(record, ["level", "raz_level", "reading_level", "source_level"])
    if value is not None:
        return str(value).strip().upper()

    rel = relative_path(path)
    patterns = [
        r"Level[_\-/ ]([A-Z]{1,3})",
        r"level[_\-/ ]([A-Z]{1,3})",
        r"raz[_\-/]([A-Z]{1,3})[_\-/]",
        r"raz_([a-z]{1,3})_",
    ]
    for pattern in patterns:
        match = re.search(pattern, rel, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()

    return "UNKNOWN"


def extract_book_id(record, path):
    value = get_first(record, ["book_id", "source_book_id", "book_key", "book", "title_id"])
    if value is not None:
        return str(value).strip()

    stem = path.stem
    match = re.search(r"(raz[_-]?[A-Za-z]+[_-]?\d+)", stem, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper().replace("-", "_")
    return stem


def extract_page_number(record, path):
    value = get_first(record, ["page_number", "page", "page_index", "source_page_number"])
    if value is not None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    match = re.search(r"(?:page|p)[_-]?(\d+)", path.stem, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def extract_sentence_candidate_ids(record):
    ids = get_first(
        record,
        [
            "source_sentence_candidate_ids",
            "sentence_candidate_ids",
            "sentence_ids",
            "source_sentence_ids",
        ],
    )
    return normalize_list(ids)


def estimate_sentence_count(clean_text):
    if not clean_text:
        return 0
    line_count = len([line for line in clean_text.splitlines() if line.strip()])
    punctuation_count = len(re.findall(r"[.!?]+(?:\s|$)", clean_text))
    return max(1, line_count, punctuation_count)


def extract_sentence_count(record, clean_text):
    value = get_first(record, ["sentence_count", "sentences_count"])
    if value is not None:
        try:
            count = int(value)
            return max(0, count)
        except (TypeError, ValueError):
            pass

    sentences = get_first(record, ["sentences", "sentence_candidates", "source_sentences", "lines"])
    if isinstance(sentences, list) and sentences:
        non_empty_count = sum(1 for item in sentences if extract_text_from_sentence_item(item))
        if non_empty_count:
            return non_empty_count

    return estimate_sentence_count(clean_text)


def sentence_count_bucket(sentence_count):
    if sentence_count is None or sentence_count <= 0:
        return "unknown"
    if sentence_count == 1:
        return "single_sentence"
    if sentence_count == 2:
        return "two_sentences"
    if 3 <= sentence_count <= 5:
        return "three_to_five_sentences"
    return "six_plus_sentences"


def extract_source_id(record):
    return normalize_scalar(
        get_first(
            record,
            [
                "reuse_unit_id",
                "page_unit_id",
                "sentence_candidate_id",
                "reading_id",
                "id",
                "source_id",
                "unit_id",
            ],
        )
    )


def extract_reusability_tags(record):
    tags = []
    for key in ["reusability_tags", "future_reuse_candidates", "reuse_tags", "tags"]:
        tags.extend(normalize_list(record.get(key)))

    boolean_to_tag = {
        "short_reading_seed": "short_reading_seed",
        "writing_model_seed": "writing_model_seed",
        "dialogue_seed": "dialogue_rewrite_seed",
        "dialogue_rewrite_seed": "dialogue_rewrite_seed",
        "exercise_seed": "exercise_seed",
        "sequencing_seed": "sequencing_seed",
        "picture_prompt_seed": "picture_prompt_seed",
        "listening_audio_seed": "listening_audio_seed",
        "assessment_seed": "assessment_seed",
    }
    for key, tag in boolean_to_tag.items():
        if record.get(key) is True:
            tags.append(tag)

    return sorted(dict.fromkeys(tag for tag in tags if tag))


def extract_derivation_potential(record):
    value = record.get("derivation_potential")
    if isinstance(value, dict):
        return {str(k): v for k, v in sorted(value.items())}
    return {}


def extract_tags(record, keys):
    tags = []
    for key in keys:
        tags.extend(normalize_list(record.get(key)))
    return sorted(dict.fromkeys(tags))


def make_item(sequence_number, path, record):
    clean_text = extract_clean_text(record)
    sentence_count = extract_sentence_count(record, clean_text)
    source_type = classify_source_type(path, record)
    level = extract_level(record, path)
    book_id = extract_book_id(record, path)
    page_number = extract_page_number(record, path)
    sentence_ids = extract_sentence_candidate_ids(record)
    reusability_tags = extract_reusability_tags(record)
    derivation_potential = extract_derivation_potential(record)
    source_id = extract_source_id(record)

    theme_hints = extract_tags(record, ["theme_hints", "theme_hint", "themes", "theme", "topic"])
    grammar_tags = extract_tags(record, ["grammar_tags", "grammar", "grammar_ids", "grammar_nodes"])
    pattern_tags = extract_tags(record, ["pattern_tags", "patterns", "pattern_ids", "sentence_patterns"])
    vocabulary_tags = extract_tags(record, ["vocabulary_tags", "vocabulary", "words", "word_tags", "vocab"])

    source_traceability = {
        "source_type": source_type,
        "source_path": relative_path(path),
        "source_record_id": source_id,
        "derived_from_original_text": bool(record.get("derived_from_original_text", True)),
        "generated_content": bool(record.get("generated_content", record.get("generated", False))),
    }

    has_multi_sentence_unit = sentence_count > 1
    return {
        "intake_id": f"RAZ_AW_S11_INTAKE_{sequence_number:06d}",
        "source_type": source_type,
        "level": level,
        "book_id": book_id,
        "page_number": page_number,
        "sentence_count": sentence_count,
        "clean_text": clean_text,
        "sentence_candidate_ids": sentence_ids,
        "source_page_unit_id": normalize_scalar(record.get("source_page_unit_id") or record.get("page_unit_id")),
        "source_reuse_unit_id": normalize_scalar(record.get("source_reuse_unit_id") or record.get("reuse_unit_id")),
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "generated_content": bool(source_traceability["generated_content"]),
        "source_traceability": source_traceability,
        "query_tags": {
            "level": level,
            "book_id": book_id,
            "theme_hints": theme_hints,
            "grammar_tags": grammar_tags,
            "pattern_tags": pattern_tags,
            "vocabulary_tags": vocabulary_tags,
            "reusability_tags": reusability_tags,
            "derivation_potential": derivation_potential,
            "has_multi_sentence_unit": has_multi_sentence_unit,
            "is_short_reading_seed": "short_reading_seed" in reusability_tags,
            "is_writing_model_seed": "writing_model_seed" in reusability_tags,
            "is_dialogue_rewrite_seed": "dialogue_rewrite_seed" in reusability_tags
            or "dialogue_seed" in reusability_tags,
            "is_exercise_seed": "exercise_seed" in reusability_tags,
        },
        "quality_flags": [],
        "notes": ["candidate_only_preserved", f"source_path={relative_path(path)}"],
    }


def add_index(indexes, index_name, key, intake_id):
    if key is None:
        return
    key = str(key).strip()
    if not key:
        return
    indexes[index_name][key].append(intake_id)


def build_query_indexes(items):
    indexes = {key: defaultdict(list) for key in QUERY_INDEX_KEYS}

    for item in items:
        intake_id = item["intake_id"]
        query_tags = item["query_tags"]
        level = item["level"]
        book_id = item["book_id"]

        add_index(indexes, "by_level", level, intake_id)
        add_index(indexes, "by_book_id", book_id, intake_id)
        add_index(indexes, "by_level_and_book", f"{level}::{book_id}", intake_id)
        add_index(indexes, "by_source_type", item["source_type"], intake_id)
        add_index(indexes, "by_authority_status", item["authority_status"], intake_id)
        add_index(indexes, "by_promotion_status", item["promotion_status"], intake_id)
        add_index(indexes, "by_sentence_count_bucket", sentence_count_bucket(item["sentence_count"]), intake_id)
        add_index(
            indexes,
            "by_multi_sentence_status",
            "multi_sentence" if query_tags["has_multi_sentence_unit"] else "single_or_unknown",
            intake_id,
        )

        for tag in query_tags["reusability_tags"]:
            add_index(indexes, "by_reusability_tag", tag, intake_id)
        for tag in query_tags["theme_hints"]:
            add_index(indexes, "by_theme_hint", tag, intake_id)
        for tag in query_tags["grammar_tags"]:
            add_index(indexes, "by_grammar_tag", tag, intake_id)
        for tag in query_tags["pattern_tags"]:
            add_index(indexes, "by_pattern_tag", tag, intake_id)
        for tag in query_tags["vocabulary_tags"]:
            add_index(indexes, "by_vocabulary_tag", tag, intake_id)

    return {
        index_name: {
            key: sorted(dict.fromkeys(values))
            for key, values in sorted(index.items())
        }
        for index_name, index in indexes.items()
    }


def summarize(items, levels_discovered, levels_missing_sources, warnings, errors):
    by_source_type = Counter(item["source_type"] for item in items)
    by_level = Counter(item["level"] for item in items)
    by_sentence_bucket = Counter(sentence_count_bucket(item["sentence_count"]) for item in items)
    reusability_counter = Counter()
    for item in items:
        reusability_counter.update(item["query_tags"]["reusability_tags"])

    promoted_count = sum(1 for item in items if item["promotion_status"] == "promoted")
    candidate_only_count = sum(1 for item in items if item["authority_status"] == "candidate_only")

    if errors:
        status = "FAIL"
    elif warnings:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"

    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": status,
        "total_items": len(items),
        "levels_discovered": sorted(levels_discovered),
        "levels_indexed": sorted(level for level, count in by_level.items() if level != "UNKNOWN" and count > 0),
        "levels_missing_sources": sorted(levels_missing_sources),
        "by_source_type": dict(sorted(by_source_type.items())),
        "by_level": dict(sorted(by_level.items())),
        "by_sentence_count_bucket": dict(sorted(by_sentence_bucket.items())),
        "by_reusability_tag": dict(sorted(reusability_counter.items())),
        "multi_sentence_item_count": sum(1 for item in items if item["sentence_count"] > 1),
        "candidate_only_count": candidate_only_count,
        "promoted_count": promoted_count,
        "warnings": sorted(dict.fromkeys(warnings)),
        "errors": sorted(dict.fromkeys(errors)),
    }


def build_index():
    warnings = []
    errors = []
    items = []
    levels_discovered = set()
    levels_missing_sources = set()

    source_paths = discover_source_paths()
    if not source_paths:
        warnings.append("no_raz_source_json_or_jsonl_files_discovered")

    sequence_number = 1
    for path in source_paths:
        try:
            data = read_json_or_jsonl(path)
        except Exception as exc:
            warnings.append(f"source_parse_skipped:{relative_path(path)}:{exc}")
            continue

        record_count_before_file = len(items)
        for record in iter_candidate_records(data, path):
            item = make_item(sequence_number, path, record)
            if not item["clean_text"]:
                continue
            items.append(item)
            levels_discovered.add(item["level"])
            sequence_number += 1

        if len(items) == record_count_before_file:
            warnings.append(f"no_candidate_records_found:{relative_path(path)}")

    items.sort(
        key=lambda item: (
            item["level"],
            item["book_id"],
            item["page_number"] if item["page_number"] is not None else 10**9,
            item["source_type"],
            item["clean_text"],
            item["intake_id"],
        )
    )

    # Reassign IDs after sorting to keep IDs deterministic and ordered by query-relevant fields.
    for index, item in enumerate(items, 1):
        item["intake_id"] = f"RAZ_AW_S11_INTAKE_{index:06d}"

    if not items:
        levels_missing_sources.add("UNKNOWN")

    query_indexes = build_query_indexes(items)
    summary = summarize(items, levels_discovered, levels_missing_sources, warnings, errors)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "builder_task": BUILDER_TASK,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_policy": {
            "offline_static_only": True,
            "generated_content": False,
            "authority_promotion": False,
            "candidate_only_preserved": True,
        },
        "levels": sorted(levels_discovered),
        "items": items,
        "query_indexes": query_indexes,
        "summary": summary,
    }

    write_json(INDEX_PATH, payload)
    write_json(SUMMARY_PATH, summary)

    print(f"Built RAZ Reading Authority Intake Query Index: {len(items)} items")
    print(f"Wrote {INDEX_PATH.relative_to(BASE_DIR).as_posix()}")
    print(f"Wrote {SUMMARY_PATH.relative_to(BASE_DIR).as_posix()}")
    print(f"Status: {summary['status']}")
    return payload


if __name__ == "__main__":
    build_index()
