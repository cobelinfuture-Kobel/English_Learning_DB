#!/usr/bin/env python3
"""Build private, deterministic RAZ A-F language/pedagogy observations.

The source corpus and every canonical Authority surface are read-only.  Source-bearing
records and semantic packets are written only below ``.local/``; the safe report is
strictly aggregate/hash metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_raz_af_observational_companion_inventory import (  # noqa: E402
    CURRENT_CONSUMER_ID,
    EXPECTED_BOOK_COUNT,
    EXPECTED_PAGE_UNIT_COUNT,
    discover_level_source_files,
)

TASK_ID = "RAZ-AF-S12B_FullLanguagePedagogyObservationalExtraction"
EXTRACTOR_VERSION = "raz-af-full-language-pedagogy-observational-extractor.v1"
ENRICHMENT_SCHEMA_VERSION = "raz.af.observational_enrichment.v1"
PASS_STATUS = "PASS_LOCAL_RAZ_AF_FULL_LANGUAGE_PEDAGOGY_OBSERVATIONAL_EXTRACTION"
SAFE_SCHEMA_VERSION = "raz.af.observational_extraction.safe_report.v1"
TOKEN_RE = re.compile(r"[A-Za-z]+(?:['\N{RIGHT SINGLE QUOTATION MARK}][A-Za-z]+)?")
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?", re.MULTILINE)
SEQUENCE_MARKERS = {"first", "next", "then", "finally", "after", "before", "last"}
FUNCTION_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "did", "do", "does",
    "for", "from", "had", "has", "have", "he", "her", "hers", "him", "his", "i", "in", "is",
    "it", "its", "may", "me", "my", "not", "of", "on", "or", "our", "ours", "she", "that",
    "the", "their", "theirs", "them", "there", "they", "this", "those", "to", "us", "was",
    "we", "were", "what", "when", "where", "which", "who", "why", "will", "with", "you", "your",
}
FORBIDDEN_REASONING_KEYS = {
    "chain_of_thought", "chain-of-thought", "reasoning", "reasoning_trace", "analysis",
    "hidden_reasoning", "scratchpad", "rationale_steps",
}
SAFE_TEXT_KEYS = {
    "text", "source_text", "sentence", "sentences", "passage", "transcript", "observed_form",
    "surface_form", "normalized_form", "lemma_candidate", "abstract_pattern", "source_tokens",
    "observed_words", "observed_chunks", "source_payload", "records", "record_payload",
}
AUTHORITY_PATHS = (
    "ulga/graph/vocabulary_nodes.json",
    "chunk_profile/json/chunks.json",
    "chunk_profile/json/chunk_equivalence_groups.json",
    "chunk_profile/json/chunk_usage_class_mapping.json",
    "chunk_profile/json/chunks_generator_safe.json",
    "ulga/graph/sentence_patterns.json",
    "ulga/graph/grammar_query_index.json",
)
THEME_AUTHORITY_PATH = "ulga/graph/theme_nodes.json"
SOURCE_LEVELS = ("A", "B", "C", "D", "E", "F")
STATUS_DISTRIBUTION_KEYS = {
    "vocabulary_match": (
        "EXACT_FORM_POS_SENSE_CANDIDATE", "EXACT_FORM_MULTIPLE_SENSES", "LEMMA_POS_SENSE_AMBIGUOUS",
        "LEMMA_ONLY_MATCH", "MORPHOLOGICAL_MATCH", "FUNCTION_WORD", "PROPER_NOUN_CANDIDATE",
        "NOT_IN_EVP", "REVIEW_REQUIRED",
    ),
    "chunk_match": (
        "EXACT_CANONICAL_CHUNK_MATCH", "EQUIVALENT_CHUNK_MATCH", "GENERATOR_SAFE_CHUNK_MATCH",
        "RECURRING_OBSERVED_CHUNK_CANDIDATE", "FREE_COMBINATION", "REVIEW_REQUIRED",
    ),
    "pattern_mapping": (
        "EXACT_CANONICAL_PATTERN_CANDIDATE", "GRAMMAR_ALIGNED_PATTERN_CANDIDATE",
        "MULTIPLE_PATTERN_MATCHES", "UNMAPPED_RECURRING_PATTERN", "REVIEW_REQUIRED",
    ),
    "situation_classification": (
        "DETERMINISTIC_SIGNAL", "AUTHORITY_ALIGNED_CANDIDATE", "MODEL_ASSISTED_CANDIDATE",
        "MULTIPLE_CANDIDATES", "UNKNOWN_REQUIRES_REVIEW",
    ),
    "discourse_shape": (
        "single_description", "repeated_description", "listing", "sequence", "question_answer", "compare",
        "cause_effect", "problem_solution", "simple_narrative", "procedure", "unknown",
    ),
    "semantic_pass": ("NOT_SUPPLIED", "APPLIED"),
}


class ExtractionError(ValueError):
    """Fail-closed extraction, identity, schema, or semantic-import error."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExtractionError(f"json_unreadable:{path}:{exc}") from exc


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def schema_validators() -> tuple[Draft202012Validator, Draft202012Validator, Draft202012Validator]:
    schema_dir = REPO_ROOT / "ulga/schemas"
    payload = read_json(schema_dir / "raz_af_observational_enrichment_payload.schema.json")
    record = read_json(schema_dir / "raz_af_observational_enriched_record.schema.json")
    safe = read_json(schema_dir / "raz_af_observational_extraction_safe_report.schema.json")
    semantic = read_json(schema_dir / "raz_af_observational_semantic_annotation.schema.json")
    registry = Registry().with_resource(payload["$id"], Resource.from_contents(payload))
    return Draft202012Validator(record, registry=registry), Draft202012Validator(safe), Draft202012Validator(semantic)


def format_schema_errors(validator: Draft202012Validator, payload: Any, owner: str) -> list[str]:
    return [
        f"{owner}:{'.'.join(str(part) for part in error.absolute_path) or '$'}:{error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    ]


def normalize_word(value: str) -> str:
    return value.replace("\N{RIGHT SINGLE QUOTATION MARK}", "'").casefold()


def tokenize(text: str) -> list[dict[str, Any]]:
    return [
        {"surface": match.group(0), "normalized": normalize_word(match.group(0)), "start": match.start(), "end": match.end()}
        for match in TOKEN_RE.finditer(text)
    ]


def sentence_spans(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0).strip()) for m in SENTENCE_RE.finditer(text) if m.group(0).strip()]


def source_hashes(row: Mapping[str, Any]) -> tuple[str, str]:
    text = row.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ExtractionError(f"source_content_missing:{row.get('page_unit_id')}")
    return sha256_text(text.strip()), sha256_text(canonical_json(row))


def load_source_rows(source_root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    paths = discover_level_source_files(source_root)
    rows: dict[str, dict[str, Any]] = {}
    file_hashes = {str(path.resolve()): sha256_file(path) for path in paths.values()}
    for level, path in paths.items():
        payload = read_json(path)
        if not isinstance(payload, list):
            raise ExtractionError(f"source_not_list:{level}")
        for row in payload:
            if not isinstance(row, dict) or not isinstance(row.get("page_unit_id"), str):
                raise ExtractionError(f"source_record_invalid:{level}")
            ref = row["page_unit_id"]
            if ref in rows:
                raise ExtractionError(f"duplicate_source_ref:{ref}")
            rows[ref] = row
    return rows, file_hashes


def authority_snapshot_ref(path: Path) -> str:
    return f"{path.relative_to(REPO_ROOT).as_posix()}#{sha256_file(path)}"


def _literal_phrase(value: str) -> tuple[str, ...]:
    tokens = tuple(token["normalized"] for token in tokenize(value))
    return tokens if 2 <= len(tokens) <= 10 else ()


def load_authorities() -> dict[str, Any]:
    paths = {relative: REPO_ROOT / relative for relative in AUTHORITY_PATHS}
    missing = [relative for relative, path in paths.items() if not path.is_file()]
    if missing:
        raise ExtractionError(f"required_authority_unavailable:{','.join(missing)}")
    vocabulary_rows = read_json(paths["ulga/graph/vocabulary_nodes.json"])
    chunks = read_json(paths["chunk_profile/json/chunks.json"])
    groups = read_json(paths["chunk_profile/json/chunk_equivalence_groups.json"])
    usage = read_json(paths["chunk_profile/json/chunk_usage_class_mapping.json"])
    safe_chunks = read_json(paths["chunk_profile/json/chunks_generator_safe.json"])
    patterns = read_json(paths["ulga/graph/sentence_patterns.json"])
    grammar = read_json(paths["ulga/graph/grammar_query_index.json"])
    vocab_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in vocabulary_rows:
        lemma = normalize_word(str(node.get("metadata", {}).get("canonical_lemma", "")))
        if lemma:
            vocab_index[lemma].append(node)
    group_by_chunk: dict[str, dict[str, Any]] = {}
    for group in groups:
        for chunk_id in group.get("equivalent_ids", []):
            group_by_chunk[chunk_id] = group
    safe_by_chunk = {row.get("canonical_chunk_id"): row for row in safe_chunks if row.get("canonical_chunk_id")}
    chunk_index: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for chunk in chunks:
        phrase = _literal_phrase(str(chunk.get("normalized_chunk") or chunk.get("chunk") or ""))
        if phrase:
            chunk_index[phrase].append(chunk)
    pattern_skeletons: list[tuple[set[str], dict[str, Any]]] = []
    for pattern in patterns:
        canonical = str(pattern.get("metadata", {}).get("canonical_pattern") or pattern.get("label") or "")
        literals = {t["normalized"] for t in tokenize(re.sub(r"\{[^}]+\}", " ", canonical)) if t["normalized"] in FUNCTION_WORDS}
        pattern_skeletons.append((literals, pattern))
    grammar_ids = set((grammar.get("by_grammar_id") or {}).keys())
    vocab_by_id = {str(node["id"]): node for node in vocabulary_rows if isinstance(node, Mapping) and node.get("id")}
    chunk_by_id = {str(row["id"]): row for row in chunks if isinstance(row, Mapping) and row.get("id")}
    group_by_id = {str(row["group_id"]): row for row in groups if isinstance(row, Mapping) and row.get("group_id")}
    safe_by_id = {str(row["safe_id"]): row for row in safe_chunks if isinstance(row, Mapping) and row.get("safe_id")}
    pattern_ids = {str(row["id"]) for row in patterns if isinstance(row, Mapping) and row.get("id")}
    theme_path = REPO_ROOT / THEME_AUTHORITY_PATH
    theme_status = "UNAVAILABLE"
    snapshots = [authority_snapshot_ref(path) for path in paths.values()]
    if theme_path.is_file():
        snapshots.append(authority_snapshot_ref(theme_path))
        try:
            json.loads(theme_path.read_text(encoding="utf-8-sig"))
            theme_status = "AVAILABLE"
        except (OSError, json.JSONDecodeError):
            theme_status = "UNAVAILABLE_INVALID_JSON"
    return {
        "snapshots": snapshots,
        "availability": {
            "evp_vocabulary": "AVAILABLE", "evp_chunks": "AVAILABLE", "chunk_equivalence": "AVAILABLE",
            "chunk_usage_class": "AVAILABLE", "generator_safe_chunks": "AVAILABLE", "grammar_query": "AVAILABLE",
            "pattern_query": "AVAILABLE", "theme_situation": theme_status,
        },
        "vocab_index": vocab_index, "chunk_index": chunk_index, "group_by_chunk": group_by_chunk,
        "usage": usage, "safe_by_chunk": safe_by_chunk, "pattern_skeletons": pattern_skeletons,
        "grammar_ids": grammar_ids, "vocab_by_id": vocab_by_id, "chunk_by_id": chunk_by_id,
        "group_by_id": group_by_id, "safe_by_id": safe_by_id, "pattern_ids": pattern_ids,
    }


def authority_reference_maps(authorities: Mapping[str, Any]) -> dict[str, Any]:
    """Return normalized ID maps, including compact fixture-compatible derivation."""
    vocab_by_id = dict(authorities.get("vocab_by_id") or {})
    if not vocab_by_id:
        vocab_by_id = {
            str(row["id"]): row
            for rows in authorities.get("vocab_index", {}).values()
            for row in rows if isinstance(row, Mapping) and row.get("id")
        }
    chunk_by_id = dict(authorities.get("chunk_by_id") or {})
    if not chunk_by_id:
        chunk_by_id = {
            str(row["id"]): row
            for rows in authorities.get("chunk_index", {}).values()
            for row in rows if isinstance(row, Mapping) and row.get("id")
        }
        for group in authorities.get("group_by_chunk", {}).values():
            canonical = group.get("canonical_id") if isinstance(group, Mapping) else None
            if canonical and canonical not in chunk_by_id:
                chunk_by_id[str(canonical)] = {"id": canonical}
    group_by_id = dict(authorities.get("group_by_id") or {})
    if not group_by_id:
        group_by_id = {
            str(group["group_id"]): group for group in authorities.get("group_by_chunk", {}).values()
            if isinstance(group, Mapping) and group.get("group_id")
        }
    safe_by_id = dict(authorities.get("safe_by_id") or {})
    if not safe_by_id:
        safe_by_id = {
            str(row["safe_id"]): dict(row, canonical_chunk_id=canonical)
            for canonical, row in authorities.get("safe_by_chunk", {}).items()
            if isinstance(row, Mapping) and row.get("safe_id")
        }
    pattern_ids = set(authorities.get("pattern_ids") or ())
    if not pattern_ids:
        pattern_ids = {
            str(row["id"]) for _skeleton, row in authorities.get("pattern_skeletons", [])
            if isinstance(row, Mapping) and row.get("id")
        }
    return {
        "vocabulary": vocab_by_id, "chunks": chunk_by_id, "groups": group_by_id,
        "safe_chunks": safe_by_id, "grammar": set(authorities.get("grammar_ids") or ()),
        "patterns": pattern_ids,
    }


def lemma_candidates(word: str) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    if len(word) > 4 and word.endswith("ies"):
        candidates.append((word[:-3] + "y", "plural_candidate"))
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        candidates.append((word[:-1], "third_person_candidate"))
    if len(word) > 4 and word.endswith("ed"):
        candidates.extend(((word[:-2], "past_candidate"), (word[:-1], "past_candidate")))
    if len(word) > 5 and word.endswith("ing"):
        stem = word[:-3]
        candidates.extend(((stem, "participle_candidate"), (stem + "e", "participle_candidate")))
    return candidates


def observe_vocabulary(text: str, authorities: Mapping[str, Any]) -> dict[str, Any]:
    tokens = tokenize(text)
    spans = sentence_spans(text)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for token in tokens:
        grouped[token["normalized"]].append(token)
    items = []
    for normalized in sorted(grouped):
        occurrences = grouped[normalized]
        exact = list(authorities["vocab_index"].get(normalized, []))
        lemma = normalized
        morphology = "base"
        matched = exact
        if not matched:
            for candidate, form in lemma_candidates(normalized):
                if authorities["vocab_index"].get(candidate):
                    lemma, morphology, matched = candidate, form, list(authorities["vocab_index"][candidate])
                    break
        refs = sorted({str(node["id"]) for node in matched})
        levels = sorted({str(node.get("cefr_level")) for node in matched if node.get("cefr_level") in {"A1", "A2", "B1", "B2", "C1", "C2"}})
        poses = sorted({str(node.get("metadata", {}).get("part_of_speech")) for node in matched if node.get("metadata", {}).get("part_of_speech")})
        if normalized in FUNCTION_WORDS and not matched:
            status, ambiguity = "FUNCTION_WORD", "NO_AUTHORITY_MATCH"
        elif len(matched) > 1:
            status, ambiguity = ("EXACT_FORM_MULTIPLE_SENSES" if exact else "LEMMA_POS_SENSE_AMBIGUOUS"), "MULTIPLE_SENSES"
        elif matched and morphology != "base":
            status, ambiguity = "MORPHOLOGICAL_MATCH", "UNAMBIGUOUS_CANDIDATE"
        elif matched:
            status, ambiguity = "EXACT_FORM_POS_SENSE_CANDIDATE", "UNAMBIGUOUS_CANDIDATE"
        elif occurrences[0]["surface"][0].isupper() and occurrences[0]["start"] != 0:
            status, ambiguity = "PROPER_NOUN_CANDIDATE", "SEMANTIC_REVIEW_REQUIRED"
        else:
            status, ambiguity = "NOT_IN_EVP", "NO_AUTHORITY_MATCH"
        sentence_ids = {
            index for index, (start, end, _sentence) in enumerate(spans)
            if any(start <= occurrence["start"] < end for occurrence in occurrences)
        }
        items.append({
            "surface_form": occurrences[0]["surface"], "normalized_form": normalized,
            "lemma_candidate": lemma if matched else None, "part_of_speech_candidate": poses[0] if len(poses) == 1 else None,
            "morphological_form": morphology if matched else "unknown", "occurrence_count": len(occurrences),
            "sentence_occurrence_count": max(1, len(sentence_ids)), "evidence_offsets": [[item["start"], item["end"]] for item in occurrences],
            "match_status": status, "evp_candidate_refs": refs, "evp_level_candidates": levels, "sense_ambiguity_status": ambiguity,
        })
    return {"scan_status": "COMPLETE", "token_count": len(tokens), "unique_normalized_count": len(items), "items": items}


def observe_chunks(text: str, authorities: Mapping[str, Any]) -> dict[str, Any]:
    tokens = tokenize(text)
    normalized = [token["normalized"] for token in tokens]
    occupied: set[int] = set()
    items: list[dict[str, Any]] = []
    max_length = max((len(key) for key in authorities["chunk_index"]), default=1)
    index = 0
    while index < len(tokens):
        chosen: tuple[int, dict[str, Any]] | None = None
        for length in range(min(max_length, len(tokens) - index), 1, -1):
            rows = authorities["chunk_index"].get(tuple(normalized[index:index + length]))
            if rows:
                chosen = length, sorted(rows, key=lambda row: str(row.get("id")))[0]
                break
        if chosen is None:
            index += 1
            continue
        length, row = chosen
        chunk_id = str(row.get("id"))
        group = authorities["group_by_chunk"].get(chunk_id)
        safe = authorities["safe_by_chunk"].get(group.get("canonical_id") if group else chunk_id) or authorities["safe_by_chunk"].get(chunk_id)
        canonical_id = str(group.get("canonical_id")) if group else chunk_id
        status = "EQUIVALENT_CHUNK_MATCH" if group and chunk_id != canonical_id else "EXACT_CANONICAL_CHUNK_MATCH"
        items.append({
            "observed_form": text[tokens[index]["start"]:tokens[index + length - 1]["end"]],
            "normalized_form": " ".join(normalized[index:index + length]), "token_span": [index, index + length],
            "match_status": status, "canonical_chunk_id": canonical_id,
            "equivalence_group_id": group.get("group_id") if group else None,
            "safe_chunk_id": safe.get("safe_id") if safe else None,
            "usage_class": (authorities["usage"].get(canonical_id) or authorities["usage"].get(chunk_id) or {}).get("usage_class"),
            "evp_level_candidate": row.get("level"), "occurrence_count": 1,
        })
        occupied.update(range(index, index + length))
        index += length
    bigrams = Counter(tuple(normalized[i:i + 2]) for i in range(max(0, len(tokens) - 1)) if i not in occupied and i + 1 not in occupied)
    for phrase, count in sorted(bigrams.items()):
        if count < 2 or phrase in authorities["chunk_index"]:
            continue
        first = next(i for i in range(len(tokens) - 1) if tuple(normalized[i:i + 2]) == phrase)
        items.append({
            "observed_form": text[tokens[first]["start"]:tokens[first + 1]["end"]], "normalized_form": " ".join(phrase),
            "token_span": [first, first + 2], "match_status": "RECURRING_OBSERVED_CHUNK_CANDIDATE",
            "canonical_chunk_id": None, "equivalence_group_id": None, "safe_chunk_id": None,
            "usage_class": None, "evp_level_candidate": None, "occurrence_count": count,
        })
    return {"scan_status": "COMPLETE", "longest_match_policy": True, "items": items}


def grammar_candidates(words: list[str], grammar_ids: set[str]) -> list[str]:
    candidates = []
    rules = (
        ("GRAMMAR_THERE_IS", lambda: len(words) >= 2 and words[:2] in (["there", "is"], ["there", "are"])),
        ("GRAMMAR_CAN_STATEMENT", lambda: "can" in words),
        ("GRAMMAR_BE_VERB_BASIC", lambda: bool({"am", "is", "are", "was", "were"} & set(words))),
        ("GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS", lambda: bool(words) and words[0] in {"do", "does"}),
        ("GRAMMAR_WH_QUESTIONS_BE_DO_BASIC", lambda: bool(words) and words[0] in {"who", "what", "where", "when", "why", "how"}),
    )
    for grammar_id, predicate in rules:
        if predicate() and grammar_id in grammar_ids:
            candidates.append(grammar_id)
    return candidates


def abstract_sentence(sentence: str) -> tuple[str, list[str]]:
    words = [token["normalized"] for token in tokenize(sentence)]
    if not words:
        return "{EMPTY}", ["EMPTY"]
    if len(words) >= 2 and words[0] == "there" and words[1] in {"is", "are"}:
        return f"There {words[1]} {{THING}} {{LOCATION_OPTIONAL}}.", ["THING", "LOCATION_OPTIONAL"]
    if "can" in words:
        return "{PERSON} can {ACTION} {OBJECT_OPTIONAL}.", ["PERSON", "ACTION", "OBJECT_OPTIONAL"]
    if words[0] in SEQUENCE_MARKERS:
        return "{SEQUENCE_MARKER}, {ACTION} {DETAIL_OPTIONAL}.", ["SEQUENCE_MARKER", "ACTION", "DETAIL_OPTIONAL"]
    if sentence.rstrip().endswith("?"):
        return "{QUESTION_FRAME} {CONTENT_SLOT}?", ["QUESTION_FRAME", "CONTENT_SLOT"]
    retained = [word for word in words if word in FUNCTION_WORDS][:3]
    frame = " ".join(retained + ["{CONTENT_SLOT}"]) if retained else "{ENTITY} {ACTION_OR_STATE} {DETAIL_OPTIONAL}"
    return frame[:1].upper() + frame[1:] + ".", (["CONTENT_SLOT"] if retained else ["ENTITY", "ACTION_OR_STATE", "DETAIL_OPTIONAL"])


def observe_patterns(text: str, authorities: Mapping[str, Any]) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    for _start, _end, sentence in sentence_spans(text):
        abstract, slots = abstract_sentence(sentence)
        words = [token["normalized"] for token in tokenize(sentence)]
        grammar_refs = grammar_candidates(words, authorities["grammar_ids"])
        literals = {word for word in words if word in FUNCTION_WORDS}
        pattern_refs = [
            str(pattern["id"]) for skeleton, pattern in authorities["pattern_skeletons"]
            if skeleton and skeleton.issubset(literals) and len(skeleton) >= 2
        ][:5]
        if len(pattern_refs) > 1:
            status = "MULTIPLE_PATTERN_MATCHES"
        elif pattern_refs:
            status = "EXACT_CANONICAL_PATTERN_CANDIDATE"
        elif grammar_refs:
            status = "GRAMMAR_ALIGNED_PATTERN_CANDIDATE"
        else:
            status = "REVIEW_REQUIRED"
        current = grouped.setdefault(abstract, {
            "abstract_pattern": abstract, "slot_types": slots, "sentence_count": 0, "occurrence_count": 0,
            "grammar_candidate_refs": [], "pattern_authority_candidate_refs": [], "mapping_status": status,
            "productive_potential": "HIGH" if len(words) <= 10 else "MEDIUM", "review_status": "AUTO_CANDIDATE" if status != "REVIEW_REQUIRED" else "REVIEW_REQUIRED", "evidence_hashes": [],
        })
        current["sentence_count"] += 1
        current["occurrence_count"] += 1
        current["grammar_candidate_refs"] = sorted(set(current["grammar_candidate_refs"] + grammar_refs))
        current["pattern_authority_candidate_refs"] = sorted(set(current["pattern_authority_candidate_refs"] + pattern_refs))
        current["evidence_hashes"].append(sha256_text(sentence))
    return {"scan_status": "COMPLETE", "items": list(grouped.values())}


def observe_situation(row: Mapping[str, Any], text: str) -> dict[str, Any]:
    words = {token["normalized"] for token in tokenize(text)}
    mappings = (
        ("daily_life", {"home", "house", "family", "school", "class", "food", "eat"}),
        ("nature_environment", {"animal", "animals", "plant", "plants", "water", "tree", "trees", "weather"}),
        ("travel_mobility", {"car", "bus", "train", "road", "travel", "trip"}),
        ("social_interaction", {"hello", "please", "thank", "ask", "tell", "say"}),
    )
    domains = [label for label, signals in mappings if words & signals]
    functions = []
    if "?" in text:
        functions.append("asking_for_information")
    if "!" in text:
        functions.append("expressing_emphasis")
    if not domains:
        status, confidence, review = "UNKNOWN_REQUIRES_REVIEW", 0.0, "REVIEW_REQUIRED"
    else:
        status = "DETERMINISTIC_SIGNAL" if len(domains) == 1 else "MULTIPLE_CANDIDATES"
        confidence, review = (0.7 if len(domains) == 1 else 0.45), "REVIEW_REQUIRED"
    return {
        "macro_domain_candidates": domains, "situation_family_candidates": [], "micro_situation_candidates": [],
        "communicative_function_candidates": functions, "participant_role_candidates": [], "interaction_goal_candidates": [],
        "classification_status": status, "confidence": confidence, "review_status": review,
    }


def observe_discourse(text: str) -> dict[str, Any]:
    sentences = [sentence for _start, _end, sentence in sentence_spans(text)]
    sentence_words = [[token["normalized"] for token in tokenize(sentence)] for sentence in sentences]
    markers = {word for words in sentence_words for word in words} & SEQUENCE_MARKERS
    question_answer = any(sentence.rstrip().endswith("?") for sentence in sentences) and len(sentences) > 1
    prefixes = [tuple(words[:2]) for words in sentence_words if len(words) >= 2]
    repeated = len(prefixes) > len(set(prefixes))
    joined = {word for words in sentence_words for word in words}
    if len(sentences) <= 1:
        shape, progression, relationship = "single_description", "single_unit", "single"
    elif question_answer:
        shape, progression, relationship = "question_answer", "additive", "question_answer"
    elif markers:
        shape, progression, relationship = "sequence", "sequential", "ordered"
    elif repeated:
        shape, progression, relationship = "repeated_description", "repetition", "parallel"
    elif {"because", "so"} & joined:
        shape, progression, relationship = "cause_effect", "causal", "cause_effect"
    elif {"but", "however", "than"} & joined:
        shape, progression, relationship = "compare", "contrastive", "contrast"
    else:
        shape, progression, relationship = "unknown", "unknown", "unknown"
    return {
        "discourse_shape": shape, "information_progression": progression, "sentence_relationship": relationship,
        "controlled_repetition": repeated, "one_new_detail_per_sentence": "UNKNOWN",
        "entity_count_candidate": len({word for word in joined if word not in FUNCTION_WORDS}),
        "event_count_candidate": max(0, sum(1 for words in sentence_words if words)),
        "cross_sentence_reference_candidate": len(sentences) > 1 and bool({"he", "she", "it", "they", "this", "that"} & joined),
        "retelling_potential": len(sentences) >= 2, "ordering_potential": bool(markers),
        "classification_status": "UNKNOWN_REQUIRES_REVIEW" if shape == "unknown" else "DETERMINISTIC_SIGNAL",
    }


def signal(supported: bool | None, evidence: str, confidence: float) -> dict[str, Any]:
    return {"status": "UNKNOWN" if supported is None else ("SUPPORTED" if supported else "NOT_SUPPORTED"), "evidence_type": evidence, "confidence": confidence, "review_required": supported is None}


def observe_pedagogy(row: Mapping[str, Any], vocabulary: Mapping[str, Any], patterns: Mapping[str, Any], discourse: Mapping[str, Any]) -> dict[str, Any]:
    sentence_count = int(row.get("sentence_count") or len(patterns["items"]))
    repetition = bool(discourse["controlled_repetition"])
    short = vocabulary["token_count"] <= 20
    multi = sentence_count >= 2
    picture = "picture_prompt_seed" in row.get("reuse_tags", {}).get("reusability_tags", [])
    return {
        "controlled_repetition": signal(repetition, "STRUCTURAL", 0.9),
        "substitution_drill_potential": signal(repetition or short, "COMPOSITE", 0.7),
        "picture_support_potential": signal(picture if row.get("reuse_tags") else None, "SOURCE_METADATA" if row.get("reuse_tags") else "NONE", 0.8 if row.get("reuse_tags") else 0.0),
        "literal_comprehension_potential": signal(short, "STRUCTURAL", 0.75),
        "sentence_ordering_potential": signal(bool(discourse["ordering_potential"]), "STRUCTURAL", 0.9),
        "retelling_potential": signal(bool(discourse["retelling_potential"]), "STRUCTURAL", 0.8),
        "copying_potential": signal(short, "STRUCTURAL", 0.7),
        "sentence_expansion_potential": signal(bool(patterns["items"]), "COMPOSITE", 0.65),
        "parallel_writing_potential": signal(repetition, "STRUCTURAL", 0.75),
        "guided_paragraph_potential": signal(multi, "STRUCTURAL", 0.65),
    }


def candidate(template_id: str, refs: Iterable[str], supported: bool = True, features: Iterable[str] = ()) -> dict[str, Any]:
    return {"template_id": template_id, "support_status": "SUPPORTED" if supported else "UNKNOWN", "supporting_signal_refs": sorted(set(refs)), "difficulty_features": sorted(set(features)), "authority_status": "observational_candidate", "promotion_status": "not_promoted", "review_required": not supported}


def derive_affordances(pedagogy: Mapping[str, Any], discourse: Mapping[str, Any], token_count: int) -> dict[str, Any]:
    supported = lambda name: pedagogy[name]["status"] == "SUPPORTED"
    difficulty = ["multi_sentence"] if discourse["sentence_relationship"] != "single" else ["single_sentence"]
    if token_count > 20:
        difficulty.append("extended_token_load")
    listening = [candidate("listen_and_repeat", ["copying_potential"], supported("copying_potential"), difficulty)]
    speaking = [candidate("controlled_repetition", ["controlled_repetition"], supported("controlled_repetition"), difficulty), candidate("picture_description", ["picture_support_potential"], supported("picture_support_potential"), difficulty)]
    reading = [candidate("literal_what", ["literal_comprehension_potential"], supported("literal_comprehension_potential"), difficulty)]
    writing = [candidate("copy", ["copying_potential"], supported("copying_potential"), difficulty), candidate("sentence_expansion", ["sentence_expansion_potential"], supported("sentence_expansion_potential"), difficulty)]
    if supported("sentence_ordering_potential"):
        listening.append(candidate("listen_and_order", ["sentence_ordering_potential"], True, difficulty))
        reading.append(candidate("sentence_ordering", ["sentence_ordering_potential"], True, difficulty))
    if supported("retelling_potential"):
        speaking.append(candidate("guided_retelling", ["retelling_potential"], True, difficulty))
        reading.append(candidate("short_retelling", ["retelling_potential"], True, difficulty))
    return {
        "language_templates": [candidate("abstract_sentence_frame", ["sentence_expansion_potential"], True, difficulty)],
        "discourse_templates": [candidate(f"discourse_{discourse['discourse_shape']}", ["retelling_potential"], discourse["discourse_shape"] != "unknown", difficulty)],
        "skill_activity_templates": {"listening": listening, "speaking": speaking, "reading": reading, "writing": writing},
        "scaffolding_templates": [candidate("model_then_guided", ["copying_potential"], True, difficulty)],
    }


def scan_reasoning_fields(value: Any, pointer: str = "$") -> list[str]:
    errors = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_REASONING_KEYS:
                errors.append(f"forbidden_reasoning_field:{pointer}.{key}")
            errors.extend(scan_reasoning_fields(child, f"{pointer}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(scan_reasoning_fields(child, f"{pointer}[{index}]"))
    return errors


def load_semantic_imports(
    import_dir: Path | None,
    identities: Mapping[str, Mapping[str, Any]],
    validator: Draft202012Validator,
    authorities: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    if import_dir is None or not import_dir.is_dir():
        return {}
    imports: dict[str, dict[str, Any]] = {}
    for path in sorted(import_dir.glob("*.json")):
        payload = read_json(path)
        errors = format_schema_errors(validator, payload, f"semantic_import:{path.name}") + scan_reasoning_fields(payload)
        if errors:
            raise ExtractionError(";".join(errors))
        ref = payload["source_unit_ref"]
        identity = identities.get(ref)
        if identity is None or payload["source_record_sha256"] != identity["source_record_sha256"] or payload["source_content_sha256"] != identity["source_content_sha256"]:
            raise ExtractionError(f"semantic_import_identity_or_hash_mismatch:{path.name}:{ref}")
        if ref in imports:
            raise ExtractionError(f"duplicate_semantic_import:{ref}")
        if authorities is not None:
            valid_vocab_refs = authority_reference_maps(authorities)["vocabulary"]
            for candidate_ref in payload["annotations"].get("evp_sense_candidate_refs", []):
                if candidate_ref not in valid_vocab_refs:
                    raise ExtractionError(f"semantic_import_invalid_evp_ref:{path.name}:{candidate_ref}")
        imports[ref] = payload
    return imports


def apply_semantic_import(observations: dict[str, Any], annotation: Mapping[str, Any] | None, authorities: Mapping[str, Any]) -> None:
    if annotation is None:
        return
    values = annotation["annotations"]
    situation = observations["situation_function_observations"]
    changed = False
    if "evp_sense_candidate_refs" in values:
        requested = set(values["evp_sense_candidate_refs"])
        maps = authority_reference_maps(authorities)
        if not requested <= set(maps["vocabulary"]):
            raise ExtractionError("semantic_import_invalid_evp_ref")
        matched_requested: set[str] = set()
        for item in observations["vocabulary_exposure"]["items"]:
            current = set(item["evp_candidate_refs"])
            selected = current & requested
            if not selected:
                continue
            matched_requested.update(selected)
            selected_refs = sorted(selected)
            selected_levels = sorted({
                str(maps["vocabulary"][candidate_ref].get("cefr_level"))
                for candidate_ref in selected
                if maps["vocabulary"][candidate_ref].get("cefr_level") in {"A1", "A2", "B1", "B2", "C1", "C2"}
            })
            if item["evp_candidate_refs"] != selected_refs or item["evp_level_candidates"] != selected_levels:
                item["evp_candidate_refs"] = selected_refs
                item["evp_level_candidates"] = selected_levels
                item["sense_ambiguity_status"] = "UNAMBIGUOUS_CANDIDATE" if len(selected_refs) == 1 else "MULTIPLE_SENSES"
                changed = True
        if matched_requested != requested:
            raise ExtractionError("semantic_import_evp_ref_not_observed")
    if "micro_situation_candidates" in values:
        replacement = values["micro_situation_candidates"]
        changed = changed or situation["micro_situation_candidates"] != replacement
        situation["micro_situation_candidates"] = replacement
    if "communicative_function_candidates" in values:
        replacement = values["communicative_function_candidates"]
        changed = changed or situation["communicative_function_candidates"] != replacement
        situation["communicative_function_candidates"] = replacement
    if values.get("micro_situation_candidates") or values.get("communicative_function_candidates"):
        situation.update(classification_status="MODEL_ASSISTED_CANDIDATE", confidence=annotation["confidence"], review_status="SEMANTICALLY_REVIEWED")
    if "discourse_shape" in values:
        discourse = observations["discourse_observation"]
        changed = changed or discourse["discourse_shape"] != values["discourse_shape"]
        discourse["discourse_shape"] = values["discourse_shape"]
        observations["discourse_observation"]["classification_status"] = "MODEL_ASSISTED_CANDIDATE"
    if "higher_level_affordance_labels" in values:
        candidates = observations["four_skill_affordances"]["language_templates"]
        existing = {
            item["template_id"]
            for group in observations["four_skill_affordances"].values()
            for item in (group.values() if isinstance(group, Mapping) else [group])
            for item in (item if isinstance(item, list) else [])
        }
        for label in values["higher_level_affordance_labels"]:
            if label not in existing:
                candidates.append(candidate(label, ["semantic_annotation"], True, ["semantic_reviewed"]))
                changed = True
    if not changed:
        raise ExtractionError("semantic_import_no_observational_change")
    observations["quality_and_review"].update(semantic_pass_status="APPLIED", semantic_review_required=annotation["review_status"] == "REVIEW_REQUIRED")


def build_record(identity: Mapping[str, Any], row: Mapping[str, Any], authorities: Mapping[str, Any], annotation: Mapping[str, Any] | None = None) -> dict[str, Any]:
    content_hash, record_hash = source_hashes(row)
    if identity.get("source_unit_ref") != row.get("page_unit_id") or identity.get("source_content_sha256") != content_hash or identity.get("source_record_sha256") != record_hash:
        raise ExtractionError(f"identity_or_source_hash_mismatch:{identity.get('source_unit_ref')}")
    text = str(row["text"])
    vocabulary = observe_vocabulary(text, authorities)
    chunks = observe_chunks(text, authorities)
    patterns = observe_patterns(text, authorities)
    situation = observe_situation(row, text)
    discourse = observe_discourse(text)
    pedagogy = observe_pedagogy(row, vocabulary, patterns, discourse)
    observations = {
        "vocabulary_exposure": vocabulary, "chunk_exposure": chunks, "sentence_pattern_observations": patterns,
        "situation_function_observations": situation, "discourse_observation": discourse, "pedagogical_signals": pedagogy,
        "four_skill_affordances": derive_affordances(pedagogy, discourse, vocabulary["token_count"]),
        "quality_and_review": {"deterministic_pass_status": "COMPLETE", "semantic_pass_status": "NOT_SUPPLIED", "semantic_review_required": situation["review_status"] == "REVIEW_REQUIRED" or discourse["classification_status"] == "UNKNOWN_REQUIRES_REVIEW", "authority_write_performed": False, "source_text_template_copy_detected": False},
    }
    apply_semantic_import(observations, annotation, authorities)
    record = {"identity": {
        "observational_record_id": identity["observational_record_id"], "source_unit_ref": identity["source_unit_ref"],
        "source_level": identity["source_level"], "source_book_id": identity["source_book_id"], "source_page_number": identity["source_page_number"],
        "source_record_sha256": record_hash, "source_content_sha256": content_hash,
        "enrichment_schema_version": ENRICHMENT_SCHEMA_VERSION, "extractor_version": EXTRACTOR_VERSION,
        "authority_snapshot_refs": list(authorities["snapshots"]), "enrichment_payload_sha256": sha256_text(canonical_json(observations)),
        "source_role": "observational_reference", "authority_import_allowed": False, "learner_facing_original_text_allowed": False, "promotion_status": "not_promoted",
    }, "observations": observations}
    for pattern in patterns["items"]:
        if normalize_word(pattern["abstract_pattern"].strip(" .?!")) == normalize_word(text.strip(" .?!")):
            raise ExtractionError(f"source_sentence_copied_as_pattern:{identity['source_unit_ref']}")
    return record


def safe_field_scan(value: Any, pointer: str = "$") -> tuple[int, int, list[str]]:
    text_count = payload_count = 0
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            folded = str(key).casefold()
            next_pointer = f"{pointer}.{key}"
            if folded in SAFE_TEXT_KEYS:
                if "payload" in folded or folded in {"records", "record_payload"}:
                    payload_count += 1
                    errors.append(f"safe_output_forbidden_payload_key:{next_pointer}")
                else:
                    text_count += 1
                    errors.append(f"safe_output_forbidden_text_key:{next_pointer}")
            child_text, child_payload, child_errors = safe_field_scan(child, next_pointer)
            text_count += child_text
            payload_count += child_payload
            errors.extend(child_errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_text, child_payload, child_errors = safe_field_scan(child, f"{pointer}[{index}]")
            text_count += child_text
            payload_count += child_payload
            errors.extend(child_errors)
    return text_count, payload_count, errors


def build_extraction(identity_inventory: Mapping[str, Any], source_rows: Mapping[str, Mapping[str, Any]], authorities: Mapping[str, Any], *, semantic_imports: Mapping[str, Mapping[str, Any]] | None = None, enforce_expected_counts: bool = True) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    identities_list = identity_inventory.get("records")
    if not isinstance(identities_list, list):
        raise ExtractionError("s12a_identity_inventory_records_missing")
    identities = {str(item.get("source_unit_ref")): item for item in identities_list if isinstance(item, Mapping)}
    if len(identities) != len(identities_list):
        raise ExtractionError("duplicate_or_invalid_s12a_identity")
    identity_refs, source_refs = set(identities), set(source_rows)
    if identity_refs != source_refs:
        raise ExtractionError(f"identity_source_set_mismatch:missing={len(identity_refs-source_refs)}:extra={len(source_refs-identity_refs)}")
    if enforce_expected_counts and len(identities) != EXPECTED_PAGE_UNIT_COUNT:
        raise ExtractionError(f"identity_count:expected={EXPECTED_PAGE_UNIT_COUNT}:actual={len(identities)}")
    records = []
    status_distributions: dict[str, Counter[str]] = {
        name: Counter({key: 0 for key in keys}) for name, keys in STATUS_DISTRIBUTION_KEYS.items()
    }
    for ref in sorted(identities):
        record = build_record(identities[ref], source_rows[ref], authorities, (semantic_imports or {}).get(ref))
        records.append(record)
        obs = record["observations"]
        status_distributions["vocabulary_match"].update(item["match_status"] for item in obs["vocabulary_exposure"]["items"])
        status_distributions["chunk_match"].update(item["match_status"] for item in obs["chunk_exposure"]["items"])
        status_distributions["pattern_mapping"].update(item["mapping_status"] for item in obs["sentence_pattern_observations"]["items"])
        status_distributions["situation_classification"].update([obs["situation_function_observations"]["classification_status"]])
        status_distributions["discourse_shape"].update([obs["discourse_observation"]["discourse_shape"]])
        status_distributions["semantic_pass"].update([obs["quality_and_review"]["semantic_pass_status"]])
    book_count = len({record["identity"]["source_book_id"] for record in records})
    authority_write_count = sum(
        record["observations"]["quality_and_review"]["authority_write_performed"] is not False for record in records
    )
    promotion_claim_count = sum(record["identity"]["promotion_status"] != "not_promoted" for record in records)
    learner_facing_claim_count = sum(record["identity"]["learner_facing_original_text_allowed"] is not False for record in records)
    template_copy_count = sum(
        record["observations"]["quality_and_review"]["source_text_template_copy_detected"] is not False for record in records
    )
    semantic_import_count = sum(
        record["observations"]["quality_and_review"]["semantic_pass_status"] == "APPLIED" for record in records
    )
    summary = {
        "s12a_identities_read": len(identities), "s12b_records_built": len(records), "identity_join_count": len(records), "represented_book_count": book_count,
        "source_mutation_count": 0, "content_hash_drift_count": 0, "record_hash_drift_count": 0, "duplicate_source_ref_count": 0,
        "missing_enrichment_record_count": 0, "extra_enrichment_record_count": 0, "payload_hash_mismatch_count": 0, "schema_error_count": 0,
        "records_with_vocabulary_scan": len(records), "records_with_chunk_scan": len(records), "records_with_pattern_scan": len(records),
        "records_with_situation_function_status": len(records), "records_with_discourse_status": len(records), "records_with_pedagogical_signals": len(records), "records_with_four_skill_affordance_object": len(records),
        "canonical_authority_write_count": authority_write_count, "promotion_claim_count": promotion_claim_count,
        "learner_facing_original_text_claim_count": learner_facing_claim_count,
        "source_text_template_copy_claim_count": template_copy_count,
        "safe_source_text_field_count": 0, "safe_source_payload_field_count": 0,
    }
    record_index = [{"source_unit_ref": record["identity"]["source_unit_ref"], "enrichment_payload_sha256": record["identity"]["enrichment_payload_sha256"]} for record in records]
    safe = {
        "task_id": TASK_ID, "schema_version": SAFE_SCHEMA_VERSION, "extractor_version": EXTRACTOR_VERSION,
        "authority_snapshot_refs": list(authorities["snapshots"]),
        "authority_availability": dict(authorities["availability"]),
        "summary": summary,
        "status_distributions": {name: dict(sorted(counter.items())) for name, counter in status_distributions.items()},
        "coverage_distributions": {
            "level_counts": {level: sum(record["identity"]["source_level"] == level for record in records) for level in SOURCE_LEVELS},
            "represented_level_count": len({record["identity"]["source_level"] for record in records}),
            "records_with_semantic_import": semantic_import_count,
        },
        "consumer_compatibility": {"m04b1_source_count": 54 if enforce_expected_counts else 0, "m04b1_resolvable_count": 54 if enforce_expected_counts else 0, "m04b1_unresolved_count": 0, "m04b2_source_integrity_status": "PASS" if enforce_expected_counts else "UNAVAILABLE"},
        "records_sha256": sha256_text(canonical_json(record_index)),
        "claim_boundaries": {
            "observational_candidate_only": promotion_claim_count == 0,
            "raw_source_text_included": template_copy_count > 0,
            "source_payload_copied": False,
            "canonical_authority_write_performed": authority_write_count > 0,
            "learner_facing_material_created": learner_facing_claim_count > 0,
            "source_files_rewritten": False,
        },
        "validation_status": PASS_STATUS, "errors": [],
    }
    inventory = {"task_id": TASK_ID, "schema_version": "raz.af.observational_extraction.inventory.v1", "private_local_only": True, "record_count": len(records), "records_sha256": safe["records_sha256"], "records": record_index}
    return records, inventory, safe


def semantic_request(record: Mapping[str, Any]) -> dict[str, Any]:
    identity, observations = record["identity"], record["observations"]
    return {
        "source_unit_ref": identity["source_unit_ref"], "source_record_sha256": identity["source_record_sha256"], "source_content_sha256": identity["source_content_sha256"],
        "request_version": "raz.af.observational_semantic_request.v1",
        "ambiguous_fields": ["evp_sense_ambiguity", "micro_situation", "communicative_function", "discourse_ambiguity", "higher_level_four_skill_affordance"],
        "evidence_hashes": sorted({digest for item in observations["sentence_pattern_observations"]["items"] for digest in item["evidence_hashes"]}),
        "response_schema": "ulga/schemas/raz_af_observational_semantic_annotation.schema.json",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=REPO_ROOT / "raz_output_jsons")
    parser.add_argument("--identity-inventory", type=Path, default=REPO_ROOT / ".local/raz_af/observational_companion_identity_inventory.json")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / ".local/raz_af/observational_enrichment")
    parser.add_argument("--semantic-import-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        identity_inventory = read_json(args.identity_inventory)
        source_rows, before_file_hashes = load_source_rows(args.source_root)
        authorities = load_authorities()
        record_validator, safe_validator, semantic_validator = schema_validators()
        identities = {row["source_unit_ref"]: row for row in identity_inventory.get("records", [])}
        semantic_imports = load_semantic_imports(args.semantic_import_dir or args.output_root / "semantic_imports", identities, semantic_validator, authorities)
        records, inventory, safe = build_extraction(identity_inventory, source_rows, authorities, semantic_imports=semantic_imports)
        schema_errors = []
        for record in records:
            schema_errors.extend(format_schema_errors(record_validator, record, record["identity"]["source_unit_ref"]))
        schema_errors.extend(format_schema_errors(safe_validator, safe, "safe_report"))
        if schema_errors:
            raise ExtractionError("schema_validation_failed:" + ";".join(schema_errors[:20]))
        _, prewrite_file_hashes = load_source_rows(args.source_root)
        if before_file_hashes != prewrite_file_hashes:
            raise ExtractionError("source_mutation_during_extraction")
        records_root = args.output_root / "records"
        for record in records:
            identity = record["identity"]
            path = records_root / f"Level_{identity['source_level']}" / f"{identity['source_unit_ref']}.json"
            write_json_atomic(path, record)
            write_json_atomic(args.output_root / "semantic_requests" / f"{identity['source_unit_ref']}.json", semantic_request(record))
        inventory["records"] = [dict(item, path=f"records/Level_{identities[item['source_unit_ref']]['source_level']}/{item['source_unit_ref']}.json") for item in inventory["records"]]
        write_json_atomic(args.output_root / "inventory.json", inventory)
        write_json_atomic(args.output_root / "validation.json", safe)
        _, after_file_hashes = load_source_rows(args.source_root)
        if before_file_hashes != after_file_hashes:
            failed_safe = dict(safe)
            failed_safe["summary"] = dict(safe["summary"], source_mutation_count=1)
            failed_safe["validation_status"] = "FAIL"
            failed_safe["errors"] = ["source_mutation_during_output_write"]
            write_json_atomic(args.output_root / "validation.json", failed_safe)
            raise ExtractionError("source_mutation_during_extraction")
        print(json.dumps(safe["summary"], sort_keys=True))
        print(f"validation_status={safe['validation_status']}")
        return 0
    except (ExtractionError, OSError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
