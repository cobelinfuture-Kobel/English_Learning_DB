#!/usr/bin/env python3
"""Stream and calibrate RAZ S11 candidates for A1FS Unit 01 and Unit 02."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence, TextIO

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Calibration reports only; no learner content, scoring, state, audio, A2, or runtime authority is written."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-RAZQ01A_Unit01Unit02LocalQueryIndexFilterCalibrationPilot"
SCHEMA_VERSION = "a1fs.v1.razq01a.unit01_unit02_filter_calibration.v1"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01A_UNIT01_UNIT02_FILTER_CALIBRATION_READY_FOR_REVIEW"
NEXT_SHORT_STEP = "A1FS-V1-RAZQ01A_FilterThresholdOperatorReviewAndPilotReplay"
RUNTIME_RELATIVE_ROOT = Path("product/a1fs_v1_2_1/runtime")
DIRECT_USE_LEVELS = frozenset("ABCDEFGHI")
REWRITE_ONLY_LEVELS = frozenset("JKLMNOPQRSTUVW")
VALID_SOURCE_TYPES = frozenset({
    "normalized_reading_unit", "enriched_reading_unit", "page_unit", "reuse_unit_candidate",
})
SOURCE_PRIORITY = {
    "normalized_reading_unit": 1,
    "enriched_reading_unit": 2,
    "page_unit": 3,
    "reuse_unit_candidate": 4,
}
TEXT_KEYS = (
    "normalized_text", "enriched_text", "reading_text", "passage_text", "page_text",
    "unit_text", "clean_text", "source_text", "sentence_text", "text", "sentence",
    "sentences", "passage", "body", "content",
)
LEVEL_KEYS = ("source_level", "raz_level", "level")
SOURCE_TYPE_KEYS = ("source_type", "record_type", "candidate_type")
SOURCE_PATH_KEYS = ("source_path", "source_file", "path")
TAG_KEYS = ("reusability_tags", "future_reuse_candidates", "reuse_tags", "tags")
LINEAGE_KEYS = (
    "reading_intake_id", "query_item_id", "source_record_id", "record_id",
    "candidate_id", "page_unit_id", "reuse_unit_id",
)
WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)?")
ARTICLE_NP_RE = re.compile(r"\b(?:a|an|the)\s+[a-z][a-z'’-]*\b", re.I)
INDEFINITE_NP_RE = re.compile(r"\b(?:a|an)\s+[a-z][a-z'’-]*\b", re.I)
DEFINITE_NP_RE = re.compile(r"\bthe\s+[a-z][a-z'’-]*\b", re.I)
PLURAL_CONTEXT_RE = re.compile(
    r"\b(?:two|three|four|five|six|seven|eight|nine|ten|many|some|these|those|several|both)\s+"
    r"([a-z][a-z'’-]*(?:s|es))\b",
    re.I,
)
PLURAL_AGREEMENT_RE = re.compile(
    r"\b([a-z][a-z'’-]*(?:s|es))\s+(?:are|have|can|do|were)\b", re.I,
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
PLURAL_FALSE_POSITIVES = frozenset({
    "is", "was", "has", "does", "this", "his", "yes", "class", "glass",
    "grass", "bus", "news",
})


class CalibrationError(ValueError):
    """Fail-closed pilot input or schema error."""


@dataclass(frozen=True)
class UnitProfile:
    unit_id: str
    sequence_order: int
    level: str
    lesson_ids: tuple[str, ...]
    skills: tuple[str, ...]
    question_types: tuple[str, ...]
    communicative_goals: tuple[str, ...]
    grammar_clues: tuple[str, ...]
    context_ids: tuple[str, ...]
    target_evp_sense_ids: tuple[str, ...]
    target_egp_row_ids: tuple[str, ...]
    target_chunk_ids: tuple[str, ...]
    target_pattern_ids: tuple[str, ...]
    lexical_cues: tuple[str, ...]
    provisional_filter_rule: str

    def as_dict(self) -> dict[str, Any]:
        return {
            name: list(value) if isinstance(value, tuple) else value
            for name, value in vars(self).items()
        }


@dataclass
class UnitAccumulator:
    profile: UnitProfile
    sample_limit: int
    counts: Counter[str] = field(default_factory=Counter)
    rejection_reasons: Counter[str] = field(default_factory=Counter)
    skill_counts: Counter[str] = field(default_factory=Counter)
    tag_counts: Counter[str] = field(default_factory=Counter)
    level_counts: Counter[str] = field(default_factory=Counter)
    source_type_counts: Counter[str] = field(default_factory=Counter)
    seen_projection: set[str] = field(default_factory=set)
    best_by_semantic: dict[str, dict[str, Any]] = field(default_factory=dict)
    reject_samples: list[dict[str, Any]] = field(default_factory=list)

    def admit(self, result: dict[str, Any]) -> None:
        projection = str(result.get("projection_identity") or "")
        if projection and projection in self.seen_projection:
            self.counts["projection_duplicate_count"] += 1
            return
        if projection:
            self.seen_projection.add(projection)
        self.counts["eligible_projection_distinct_count"] += 1
        semantic = str(result.get("semantic_identity") or "")
        incumbent = self.best_by_semantic.get(semantic)
        if incumbent is None:
            self.best_by_semantic[semantic] = result
            return
        self.counts["semantic_duplicate_count"] += 1
        rank = {"BORDERLINE": 1, "PASS": 2}
        old_key = (
            rank.get(str(incumbent.get("classification")), 0),
            SOURCE_PRIORITY.get(str(incumbent.get("source_type")), 0),
            int(incumbent.get("score") or 0),
        )
        new_key = (
            rank.get(str(result.get("classification")), 0),
            SOURCE_PRIORITY.get(str(result.get("source_type")), 0),
            int(result.get("score") or 0),
        )
        if new_key > old_key:
            self.best_by_semantic[semantic] = result

    def finalize(self) -> dict[str, list[dict[str, Any]]]:
        self.counts["eligible_semantic_distinct_count"] = len(self.best_by_semantic)
        samples: dict[str, list[dict[str, Any]]] = {
            "PASS": [], "BORDERLINE": [], "REJECT": self.reject_samples,
        }
        for result in self.best_by_semantic.values():
            classification = str(result["classification"])
            self.counts[f"{classification.lower()}_count"] += 1
            self.level_counts[str(result.get("source_level") or "UNKNOWN")] += 1
            self.source_type_counts[str(result.get("source_type") or "UNKNOWN")] += 1
            self.tag_counts.update(result.get("reusability_tags", []))
            self.skill_counts.update(result.get("skill_affordances", []))
            samples[classification].append(_sample(result))
        for classification in ("PASS", "BORDERLINE"):
            samples[classification].sort(
                key=lambda row: (-int(row.get("score") or 0), str(row.get("semantic_identity") or ""))
            )
            samples[classification] = samples[classification][: self.sample_limit]
        return samples


class _JsonReader:
    """Incremental JSON reader that retains only the current value in memory."""

    def __init__(self, handle: TextIO, chunk_size: int) -> None:
        self.handle = handle
        self.chunk_size = chunk_size
        self.buffer = ""
        self.position = 0
        self.eof = False
        self.decoder = json.JSONDecoder()

    def _read_more(self) -> bool:
        if self.eof:
            return False
        self.buffer = self.buffer[self.position :]
        self.position = 0
        chunk = self.handle.read(self.chunk_size)
        if not chunk:
            self.eof = True
            return False
        self.buffer += chunk
        return True

    def skip_ws(self) -> None:
        while True:
            while self.position < len(self.buffer) and self.buffer[self.position].isspace():
                self.position += 1
            if self.position < len(self.buffer) or not self._read_more():
                return

    def peek(self) -> str:
        self.skip_ws()
        if self.position >= len(self.buffer):
            raise CalibrationError("QUERY_INDEX_TRUNCATED_OR_INVALID_JSON")
        return self.buffer[self.position]

    def expect(self, token: str) -> None:
        if self.peek() != token:
            raise CalibrationError(f"QUERY_INDEX_EXPECTED_TOKEN={token}")
        self.position += 1

    def value(self) -> Any:
        while True:
            self.skip_ws()
            try:
                value, end = self.decoder.raw_decode(self.buffer, self.position)
            except json.JSONDecodeError as exc:
                if self._read_more():
                    continue
                raise CalibrationError("QUERY_INDEX_TRUNCATED_OR_INVALID_JSON") from exc
            self.position = end
            return value


def _iter_array(reader: _JsonReader) -> Iterator[Mapping[str, Any]]:
    reader.expect("[")
    first = True
    while True:
        token = reader.peek()
        if token == "]":
            reader.position += 1
            return
        if not first:
            reader.expect(",")
        value = reader.value()
        if not isinstance(value, Mapping):
            raise CalibrationError("QUERY_INDEX_ITEM_MUST_BE_OBJECT")
        yield value
        first = False


def _iter_object_items(reader: _JsonReader) -> Iterator[Mapping[str, Any]]:
    reader.expect("{")
    first = True
    found_items = False
    while True:
        token = reader.peek()
        if token == "}":
            reader.position += 1
            break
        if not first:
            reader.expect(",")
        key = reader.value()
        if not isinstance(key, str):
            raise CalibrationError("QUERY_INDEX_OBJECT_KEY_MUST_BE_STRING")
        reader.expect(":")
        if key == "items":
            if found_items:
                raise CalibrationError("QUERY_INDEX_ITEMS_KEY_DUPLICATED")
            if reader.peek() != "[":
                raise CalibrationError("QUERY_INDEX_ITEMS_FIELD_MUST_BE_ARRAY")
            found_items = True
            yield from _iter_array(reader)
        else:
            reader.value()
        first = False
    if not found_items:
        raise CalibrationError("QUERY_INDEX_ITEMS_FIELD_MISSING")


def iter_query_index(path: Path, chunk_size: int = 4 * 1024 * 1024) -> Iterator[Mapping[str, Any]]:
    if not path.is_file():
        raise CalibrationError(f"QUERY_INDEX_MISSING={path}")
    with path.open("r", encoding="utf-8-sig") as handle:
        reader = _JsonReader(handle, chunk_size)
        token = reader.peek()
        if token == "[":
            yield from _iter_array(reader)
        elif token == "{":
            yield from _iter_object_items(reader)
        else:
            raise CalibrationError("QUERY_INDEX_TOP_LEVEL_MUST_BE_ARRAY_OR_OBJECT")
        reader.skip_ws()
        if reader.position < len(reader.buffer) or reader._read_more():
            reader.skip_ws()
            if reader.position < len(reader.buffer):
                raise CalibrationError("QUERY_INDEX_TRAILING_CONTENT")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CalibrationError(f"REQUIRED_FILE_MISSING={path}") from exc
    except json.JSONDecodeError as exc:
        raise CalibrationError(f"INVALID_JSON={path}:{exc.lineno}:{exc.colno}") from exc


def _walk(value: Any, keys: Sequence[str]) -> Iterator[Any]:
    if isinstance(value, Mapping):
        for key in keys:
            if key in value:
                yield value[key]
        for child in value.values():
            if isinstance(child, (Mapping, list, tuple)):
                yield from _walk(child, keys)
    elif isinstance(value, (list, tuple)):
        for child in value:
            if isinstance(child, (Mapping, list, tuple)):
                yield from _walk(child, keys)


def _first(record: Mapping[str, Any], keys: Sequence[str]) -> str:
    for value in _walk(record, keys):
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value).strip()
    return ""


def _text_parts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [part for child in value for part in _text_parts(child)]
    if isinstance(value, Mapping):
        return [part for key in TEXT_KEYS if key in value for part in _text_parts(value[key])]
    return []


def extract_text(record: Mapping[str, Any]) -> str:
    for value in _walk(record, TEXT_KEYS):
        parts = _text_parts(value)
        if parts:
            return " ".join(parts)
    return ""


def extract_tags(record: Mapping[str, Any]) -> tuple[str, ...]:
    tags: set[str] = set()
    for value in _walk(record, TAG_KEYS):
        if isinstance(value, str) and value.strip():
            tags.add(value.strip())
        elif isinstance(value, (list, tuple, set)):
            tags.update(str(item).strip() for item in value if str(item).strip())
    return tuple(sorted(tags))


def normalize_text(text: str) -> str:
    return " ".join(token.lower().replace("’", "'") for token in WORD_RE.findall(text))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def projection_identity(record: Mapping[str, Any], text: str) -> str:
    identity = _first(record, LINEAGE_KEYS) or _first(record, SOURCE_PATH_KEYS)
    source_type = _first(record, SOURCE_TYPE_KEYS)
    return _hash("|".join((identity, source_type, normalize_text(text))))


def _collect(value: Any, key: str) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        raw = value.get(key)
        if isinstance(raw, str):
            found.add(raw)
        elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
            found.update(str(item) for item in raw if str(item).strip())
        for child in value.values():
            if isinstance(child, (Mapping, list, tuple)):
                found.update(_collect(child, key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            found.update(_collect(child, key))
    return found


def _cue(ref: str) -> str:
    if ref.startswith("vocabulary:"):
        parts = ref.split(":")
        return parts[1].replace("_", " ") if len(parts) > 1 else ""
    if ref.startswith("chunk:"):
        return ref.split(":", 1)[1].replace("_", " ")
    return ""


def build_unit_profiles(repo_root: Path, unit_limit: int = 2) -> list[UnitProfile]:
    runtime = repo_root / RUNTIME_RELATIVE_ROOT
    sequence = _load_json(runtime / "sequence.json")
    bundles = _load_json(runtime / "bundles.json")
    if not isinstance(sequence, Mapping) or not isinstance(bundles, Mapping):
        raise CalibrationError("RUNTIME_AUTHORITY_SHAPE_INVALID")
    selected = sorted(
        ((str(unit), int(order)) for unit, order in sequence.items()), key=lambda row: row[1]
    )[:unit_limit]
    if len(selected) != unit_limit:
        raise CalibrationError(f"UNIT_PROFILE_COUNT_INVALID={len(selected)}")
    profiles: list[UnitProfile] = []
    for unit_id, order in selected:
        relevant = {
            key: value for key, value in bundles.items()
            if isinstance(key, str) and f":{unit_id}:" in key and isinstance(value, Mapping)
        }
        if not relevant:
            raise CalibrationError(f"UNIT_RUNTIME_BUNDLES_MISSING={unit_id}")
        assets = [
            asset for bundle in relevant.values() for asset in bundle.get("assets", [])
            if isinstance(asset, Mapping)
        ]
        levels = sorted({
            str(bundle.get("lesson", {}).get("level") or "") for bundle in relevant.values()
        } - {""})
        target_evp = tuple(sorted(_collect(assets, "target_evp_sense_ids")))
        target_chunks = tuple(sorted(_collect(assets, "target_chunk_ids")))
        if unit_id == "GRAMMAR_ARTICLES_BASIC":
            rule = "ARTICLE_NOUN_PHRASE: require a/an/the + noun; lexical overlap ranks only"
        elif unit_id == "GRAMMAR_REGULAR_PLURAL_NOUNS":
            rule = "REGULAR_PLURAL_CONTEXT: require plural noun with determiner/number or plural agreement"
        else:
            raise CalibrationError(f"PILOT_UNIT_NOT_SUPPORTED={unit_id}")
        profiles.append(UnitProfile(
            unit_id=unit_id,
            sequence_order=order,
            level=levels[0] if len(levels) == 1 else "/".join(levels),
            lesson_ids=tuple(sorted(relevant)),
            skills=tuple(sorted({
                str(bundle.get("lesson", {}).get("skill") or "") for bundle in relevant.values()
            } - {""})),
            question_types=tuple(sorted(_collect(assets, "question_type"))),
            communicative_goals=tuple(sorted(_collect(assets, "communicative_goal"))),
            grammar_clues=tuple(sorted(_collect(assets, "grammar_clue"))),
            context_ids=tuple(sorted(_collect(assets, "context_id"))),
            target_evp_sense_ids=target_evp,
            target_egp_row_ids=tuple(sorted(_collect(assets, "target_egp_row_ids"))),
            target_chunk_ids=target_chunks,
            target_pattern_ids=tuple(sorted(_collect(assets, "target_pattern_ids"))),
            lexical_cues=tuple(sorted({
                cue for ref in (*target_evp, *target_chunks) if (cue := _cue(ref))
            })),
            provisional_filter_rule=rule,
        ))
    return profiles


def _grammar_hits(unit_id: str, text: str) -> tuple[int, dict[str, int]]:
    if unit_id == "GRAMMAR_ARTICLES_BASIC":
        article = len(ARTICLE_NP_RE.findall(text))
        indefinite = len(INDEFINITE_NP_RE.findall(text))
        definite = len(DEFINITE_NP_RE.findall(text))
        return article, {
            "article_np": article,
            "indefinite_np": indefinite,
            "definite_np": definite,
        }
    words = [*PLURAL_CONTEXT_RE.findall(text), *PLURAL_AGREEMENT_RE.findall(text)]
    count = sum(word.lower() not in PLURAL_FALSE_POSITIVES for word in words)
    return count, {"regular_plural_context": count}


def _lexical_hits(profile: UnitProfile, text: str) -> list[str]:
    normalized = f" {normalize_text(text)} "
    return [cue for cue in profile.lexical_cues if f" {normalize_text(cue)} " in normalized]


def _skills(tags: Sequence[str], text: str, grammar_hits: int) -> list[str]:
    tag_set = set(tags)
    words = len(WORD_RE.findall(text))
    skills: set[str] = set()
    if words >= 3:
        skills.add("READING")
    if "listening_audio_seed" in tag_set and words <= 100:
        skills.add("LISTENING_SCRIPT_CANDIDATE")
    if tag_set & {"dialogue_rewrite_seed", "picture_prompt_seed", "retelling_seed"} or grammar_hits:
        skills.add("SPEAKING_PROMPT_CANDIDATE")
    if tag_set & {"grammar_pattern_seed", "vocabulary_exposure_seed", "exercise_seed"} or grammar_hits:
        skills.add("WRITING_SEED_CANDIDATE")
    return sorted(skills)


def classify_record(record: Mapping[str, Any], profile: UnitProfile) -> dict[str, Any]:
    text = extract_text(record)
    level = _first(record, LEVEL_KEYS).upper()
    source_type = _first(record, SOURCE_TYPE_KEYS)
    tags = extract_tags(record)
    words = len(WORD_RE.findall(text))
    sentences = max(1, len([
        part for part in SENTENCE_SPLIT_RE.split(text) if part.strip()
    ])) if text else 0
    grammar_hits, evidence = _grammar_hits(profile.unit_id, text)
    lexical_hits = _lexical_hits(profile, text)
    skills = _skills(tags, text, grammar_hits) if text else []
    reasons: list[str] = []
    if not _first(record, LINEAGE_KEYS):
        reasons.append("SOURCE_LINEAGE_ID_MISSING")
    if level not in DIRECT_USE_LEVELS | REWRITE_ONLY_LEVELS:
        reasons.append("SOURCE_LEVEL_INVALID")
    if source_type not in VALID_SOURCE_TYPES:
        reasons.append("SOURCE_TYPE_INVALID")
    if not text:
        reasons.append("TEXT_MISSING")
    if words and words < 3:
        reasons.append("TEXT_TOO_SHORT")
    classification = "REJECT"
    if not reasons:
        if grammar_hits and skills:
            if level in DIRECT_USE_LEVELS and words <= 120 and sentences <= 6:
                classification, reasons = "PASS", ["DIRECT_LEVEL_AND_GRAMMAR_MATCH"]
            else:
                classification = "BORDERLINE"
                if level in REWRITE_ONLY_LEVELS:
                    reasons.append("REWRITE_ONLY_SOURCE_LEVEL")
                if words > 120 or sentences > 6:
                    reasons.append("DIRECT_TEXT_COMPLEXITY_EXCEEDS_PILOT_LIMIT")
        elif lexical_hits and skills:
            classification, reasons = "BORDERLINE", ["LEXICAL_OR_CONTEXT_MATCH_WITHOUT_TARGET_GRAMMAR"]
        else:
            reasons.append("NO_UNIT_GRAMMAR_OR_LEXICAL_MATCH")
    score = grammar_hits * 10 + min(len(lexical_hits), 5) * 2 + min(len(skills), 4)
    score += 3 if level in DIRECT_USE_LEVELS else 0
    score += SOURCE_PRIORITY.get(source_type, 0)
    return {
        "classification": classification,
        "reasons": reasons,
        "score": score,
        "reading_intake_id": _first(record, ("reading_intake_id", "query_item_id")),
        "source_record_id": _first(record, LINEAGE_KEYS),
        "source_level": level,
        "source_type": source_type,
        "source_path": _first(record, SOURCE_PATH_KEYS),
        "text": text,
        "word_count": words,
        "sentence_count": sentences,
        "grammar_hits": grammar_hits,
        "grammar_evidence": evidence,
        "lexical_hits": lexical_hits,
        "reusability_tags": list(tags),
        "skill_affordances": skills,
        "semantic_identity": _hash(normalize_text(text)) if text else "",
        "projection_identity": projection_identity(record, text) if text else "",
    }


def _sample(result: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "classification", "reasons", "score", "reading_intake_id", "source_record_id",
        "source_level", "source_type", "source_path", "word_count", "sentence_count",
        "grammar_hits", "grammar_evidence", "lexical_hits", "reusability_tags",
        "skill_affordances", "semantic_identity",
    )
    return {key: result.get(key) for key in keys} | {
        "text_excerpt": str(result.get("text") or "")[:600]
    }


def run_calibration(
    *,
    repo_root: Path,
    index_path: Path,
    output_dir: Path,
    max_records: int | None = None,
    sample_limit: int = 30,
    progress_every: int = 50_000,
) -> dict[str, Any]:
    profiles = build_unit_profiles(repo_root)
    accumulators = {
        profile.unit_id: UnitAccumulator(profile, sample_limit) for profile in profiles
    }
    scanned = 0
    for record in iter_query_index(index_path):
        scanned += 1
        for accumulator in accumulators.values():
            accumulator.counts["raw_records_scanned"] += 1
            result = classify_record(record, accumulator.profile)
            classification = str(result["classification"])
            accumulator.counts[f"pre_dedup_{classification.lower()}_count"] += 1
            if classification == "REJECT":
                accumulator.counts["reject_count"] += 1
                accumulator.rejection_reasons.update(result["reasons"])
                if len(accumulator.reject_samples) < sample_limit:
                    accumulator.reject_samples.append(_sample(result))
            else:
                accumulator.admit(result)
        if progress_every and scanned % progress_every == 0:
            print(f"PROGRESS_RECORDS_SCANNED={scanned}")
        if max_records is not None and scanned >= max_records:
            break
    if not scanned:
        raise CalibrationError("QUERY_INDEX_EMPTY")

    units: list[dict[str, Any]] = []
    for profile in profiles:
        accumulator = accumulators[profile.unit_id]
        samples = accumulator.finalize()
        units.append({
            "unit_profile": profile.as_dict(),
            "filter_funnel": dict(sorted(accumulator.counts.items())),
            "rejection_reasons": dict(accumulator.rejection_reasons.most_common()),
            "skill_capacity": dict(accumulator.skill_counts.most_common()),
            "reusability_tag_capacity": dict(accumulator.tag_counts.most_common()),
            "source_level_distribution": dict(sorted(accumulator.level_counts.items())),
            "source_type_distribution": dict(accumulator.source_type_counts.most_common()),
            "samples": samples,
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "a1fs_v1_razq01a_unit01_unit02_filter_calibration.json"
    validation_path = output_dir / "a1fs_v1_razq01a_unit01_unit02_filter_validation.json"
    matrix_path = output_dir / "a1fs_v1_razq01a_unit01_unit02_distinct_capacity_matrix.csv"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "scope": {
            "allowed_units": [profile.unit_id for profile in profiles],
            "blocked_units": "UNIT_03_TO_UNIT_24",
            "a2_status": "LOCKED",
            "canonical_promotion": False,
            "learner_facing_content_write": False,
        },
        "inputs": {
            "query_index_path": str(index_path),
            "repo_root": str(repo_root),
            "runtime_authority_root": str(repo_root / RUNTIME_RELATIVE_ROOT),
            "accepted_query_index_envelopes": [
                "TOP_LEVEL_ARRAY", "TOP_LEVEL_OBJECT_ITEMS_ARRAY",
            ],
        },
        "provisional_policy": {
            "direct_use_source_levels": sorted(DIRECT_USE_LEVELS),
            "rewrite_only_source_levels": sorted(REWRITE_ONLY_LEVELS),
            "direct_word_limit": 120,
            "direct_sentence_limit": 6,
            "theme_only_match_is_pass": False,
            "lexical_only_match_classification": "BORDERLINE",
            "vocabulary_authority_gate": "NOT_YET_APPLIED_REQUIRES_OPERATOR_CALIBRATION",
            "admission_status": "CALIBRATION_ONLY_NOT_PROMOTED",
        },
        "records_scanned": scanned,
        "partial_scan": max_records is not None and scanned >= max_records,
        "units": units,
        "validation": {
            "unit_count": len(units),
            "expected_unit_count": 2,
            "all_units_have_profiles": all(unit["unit_profile"] for unit in units),
            "all_units_have_samples": all(
                any(unit["samples"][name] for name in ("PASS", "BORDERLINE", "REJECT"))
                for unit in units
            ),
            "canonical_content_modified": False,
        },
        "outputs": {
            "report": str(report_path),
            "validation": str(validation_path),
            "capacity_matrix": str(matrix_path),
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    validation_path.write_text(
        json.dumps({
            "schema_version": SCHEMA_VERSION,
            "task_id": TASK_ID,
            "status": PASS_STATUS,
            "records_scanned": scanned,
            "validation": report["validation"],
            "next_short_step": NEXT_SHORT_STEP,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    fields = [
        "unit_id", "sequence_order", "level", "raw_records_scanned",
        "eligible_projection_distinct_count", "eligible_semantic_distinct_count",
        "pass_count", "borderline_count", "reject_count", "reading_capacity",
        "listening_script_capacity", "speaking_prompt_capacity", "writing_seed_capacity",
    ]
    with matrix_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for unit in units:
            profile = unit["unit_profile"]
            funnel = unit["filter_funnel"]
            skills = unit["skill_capacity"]
            writer.writerow({
                "unit_id": profile["unit_id"],
                "sequence_order": profile["sequence_order"],
                "level": profile["level"],
                "raw_records_scanned": funnel.get("raw_records_scanned", 0),
                "eligible_projection_distinct_count": funnel.get("eligible_projection_distinct_count", 0),
                "eligible_semantic_distinct_count": funnel.get("eligible_semantic_distinct_count", 0),
                "pass_count": funnel.get("pass_count", 0),
                "borderline_count": funnel.get("borderline_count", 0),
                "reject_count": funnel.get("reject_count", 0),
                "reading_capacity": skills.get("READING", 0),
                "listening_script_capacity": skills.get("LISTENING_SCRIPT_CANDIDATE", 0),
                "speaking_prompt_capacity": skills.get("SPEAKING_PROMPT_CANDIDATE", 0),
                "writing_seed_capacity": skills.get("WRITING_SEED_CANDIDATE", 0),
            })
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--index-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-records", type=int)
    parser.add_argument("--sample-limit", type=int, default=30)
    parser.add_argument("--progress-every", type=int, default=50_000)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = run_calibration(
            repo_root=args.repo_root.resolve(),
            index_path=args.index_path.resolve(),
            output_dir=args.output_dir.resolve(),
            max_records=args.max_records,
            sample_limit=args.sample_limit,
            progress_every=args.progress_every,
        )
    except CalibrationError as exc:
        print(f"STATUS=FAIL_A1FS_V1_RAZQ01A_FILTER_CALIBRATION\nERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    print(f"RECORDS_SCANNED={report['records_scanned']}")
    for unit in report["units"]:
        funnel = unit["filter_funnel"]
        profile = unit["unit_profile"]
        print(
            f"UNIT={profile['unit_id']} "
            f"PASS={funnel.get('pass_count', 0)} "
            f"BORDERLINE={funnel.get('borderline_count', 0)} "
            f"REJECT={funnel.get('reject_count', 0)}"
        )
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
