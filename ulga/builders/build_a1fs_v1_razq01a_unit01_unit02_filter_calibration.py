#!/usr/bin/env python3
"""Calibrate RAZ S11 query-index filters for A1FS Unit 01 and Unit 02.

The builder reads the existing V1.2.1 runtime authority to derive the first two
unit profiles, streams the local RAZ S11 query index without loading it into
memory, applies explicit provisional gates, and writes only calibration
reports. It does not promote or overwrite learner-facing content.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Mapping, MutableMapping, Sequence

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Streams a local RAZ candidate query index and emits Unit01/Unit02 filter "
    "calibration statistics and bounded samples only. It does not create, "
    "promote, overwrite, score, or deliver learner-facing content, and it does "
    "not modify curriculum, learner state, audio, A2, or runtime authority."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-RAZQ01A_Unit01Unit02LocalQueryIndexFilterCalibrationPilot"
SCHEMA_VERSION = "a1fs.v1.razq01a.unit01_unit02_filter_calibration.v1"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01A_UNIT01_UNIT02_FILTER_CALIBRATION_READY_FOR_REVIEW"
NEXT_SHORT_STEP = "A1FS-V1-RAZQ01A_FilterThresholdOperatorReviewAndPilotReplay"

RUNTIME_RELATIVE_ROOT = Path("product/a1fs_v1_2_1/runtime")
SEQUENCE_NAME = "sequence.json"
BUNDLES_NAME = "bundles.json"

DIRECT_USE_LEVELS = frozenset("ABCDEFGHI")
REWRITE_ONLY_LEVELS = frozenset("JKLMNOPQRSTUVW")
VALID_SOURCE_TYPES = frozenset(
    {
        "normalized_reading_unit",
        "enriched_reading_unit",
        "page_unit",
        "reuse_unit_candidate",
    }
)
SOURCE_PRIORITY = {
    "normalized_reading_unit": 1,
    "enriched_reading_unit": 2,
    "page_unit": 3,
    "reuse_unit_candidate": 4,
}

TEXT_KEYS = (
    "normalized_text",
    "enriched_text",
    "reading_text",
    "passage_text",
    "page_text",
    "unit_text",
    "source_text",
    "sentence_text",
    "text",
    "sentence",
    "sentences",
    "passage",
    "body",
    "content",
)
LEVEL_KEYS = ("source_level", "raz_level", "level")
SOURCE_TYPE_KEYS = ("source_type", "record_type", "candidate_type")
SOURCE_PATH_KEYS = ("source_path", "source_file", "path")
TAG_KEYS = ("reusability_tags", "future_reuse_candidates", "reuse_tags", "tags")

WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)?")
ARTICLE_NP_RE = re.compile(r"\b(?:a|an|the)\s+[a-z][a-z'’-]*\b", re.IGNORECASE)
INDEFINITE_NP_RE = re.compile(r"\b(?:a|an)\s+[a-z][a-z'’-]*\b", re.IGNORECASE)
DEFINITE_NP_RE = re.compile(r"\bthe\s+[a-z][a-z'’-]*\b", re.IGNORECASE)
PLURAL_CONTEXT_RE = re.compile(
    r"\b(?:two|three|four|five|six|seven|eight|nine|ten|many|some|these|those|several|both)\s+"
    r"([a-z][a-z'’-]*(?:s|es))\b",
    re.IGNORECASE,
)
PLURAL_AGREEMENT_RE = re.compile(
    r"\b([a-z][a-z'’-]*(?:s|es))\s+(?:are|have|can|do|were)\b",
    re.IGNORECASE,
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

PLURAL_FALSE_POSITIVES = frozenset(
    {
        "is",
        "was",
        "has",
        "does",
        "this",
        "his",
        "yes",
        "class",
        "glass",
        "grass",
        "bus",
        "news",
    }
)


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
            "unit_id": self.unit_id,
            "sequence_order": self.sequence_order,
            "level": self.level,
            "lesson_ids": list(self.lesson_ids),
            "skills": list(self.skills),
            "question_types": list(self.question_types),
            "communicative_goals": list(self.communicative_goals),
            "grammar_clues": list(self.grammar_clues),
            "context_ids": list(self.context_ids),
            "target_evp_sense_ids": list(self.target_evp_sense_ids),
            "target_egp_row_ids": list(self.target_egp_row_ids),
            "target_chunk_ids": list(self.target_chunk_ids),
            "target_pattern_ids": list(self.target_pattern_ids),
            "lexical_cues": list(self.lexical_cues),
            "provisional_filter_rule": self.provisional_filter_rule,
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

    def add_reject_sample(self, sample: dict[str, Any]) -> None:
        if len(self.reject_samples) < self.sample_limit:
            self.reject_samples.append(sample)

    def admit_eligible(self, result: dict[str, Any]) -> None:
        projection = str(result.get("projection_identity") or "")
        if projection and projection in self.seen_projection:
            self.counts["projection_duplicate_count"] += 1
            return
        if projection:
            self.seen_projection.add(projection)
        self.counts["eligible_projection_distinct_count"] += 1

        semantic = str(result.get("semantic_identity") or "")
        if not semantic:
            return
        incumbent = self.best_by_semantic.get(semantic)
        if incumbent is None:
            self.best_by_semantic[semantic] = result
            return
        self.counts["semantic_duplicate_count"] += 1
        rank = {"BORDERLINE": 1, "PASS": 2}
        incumbent_key = (
            rank.get(str(incumbent.get("classification")), 0),
            SOURCE_PRIORITY.get(str(incumbent.get("source_type")), 0),
            int(incumbent.get("score") or 0),
        )
        challenger_key = (
            rank.get(str(result.get("classification")), 0),
            SOURCE_PRIORITY.get(str(result.get("source_type")), 0),
            int(result.get("score") or 0),
        )
        if challenger_key > incumbent_key:
            self.best_by_semantic[semantic] = result

    def finalize(self) -> dict[str, list[dict[str, Any]]]:
        self.counts["eligible_semantic_distinct_count"] = len(self.best_by_semantic)
        pass_rows: list[dict[str, Any]] = []
        borderline_rows: list[dict[str, Any]] = []
        for result in self.best_by_semantic.values():
            classification = str(result["classification"])
            self.counts[classification.lower() + "_count"] += 1
            self.level_counts[str(result.get("source_level") or "UNKNOWN")] += 1
            self.source_type_counts[str(result.get("source_type") or "UNKNOWN")] += 1
            for tag in result.get("reusability_tags", []):
                self.tag_counts[str(tag)] += 1
            for skill in result.get("skill_affordances", []):
                self.skill_counts[str(skill)] += 1
            sample = _sample_payload(result)
            if classification == "PASS":
                pass_rows.append(sample)
            else:
                borderline_rows.append(sample)
        pass_rows.sort(
            key=lambda row: (
                -int(row.get("score") or 0),
                str(row.get("semantic_identity") or ""),
            )
        )
        borderline_rows.sort(
            key=lambda row: (
                -int(row.get("score") or 0),
                str(row.get("semantic_identity") or ""),
            )
        )
        return {
            "PASS": pass_rows[: self.sample_limit],
            "BORDERLINE": borderline_rows[: self.sample_limit],
            "REJECT": self.reject_samples,
        }


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise CalibrationError(f"REQUIRED_FILE_MISSING={path}") from exc
    except json.JSONDecodeError as exc:
        raise CalibrationError(f"INVALID_JSON={path}:{exc.lineno}:{exc.colno}") from exc


def _iter_top_level_array(
    path: Path,
    *,
    chunk_size: int = 4 * 1024 * 1024,
) -> Iterator[Mapping[str, Any]]:
    """Yield objects from a top-level JSON array using only the stdlib."""
    decoder = json.JSONDecoder()
    with path.open("r", encoding="utf-8-sig") as handle:
        buffer = ""
        position = 0
        started = False
        finished = False
        while not finished:
            chunk = handle.read(chunk_size)
            eof = not chunk
            buffer = buffer[position:] + chunk
            position = 0

            while True:
                while position < len(buffer) and buffer[position].isspace():
                    position += 1
                if not started:
                    if position >= len(buffer):
                        break
                    if buffer[position] != "[":
                        raise CalibrationError("QUERY_INDEX_TOP_LEVEL_MUST_BE_ARRAY")
                    started = True
                    position += 1
                    continue

                while position < len(buffer) and (
                    buffer[position].isspace() or buffer[position] == ","
                ):
                    position += 1
                if position >= len(buffer):
                    break
                if buffer[position] == "]":
                    finished = True
                    position += 1
                    break
                try:
                    value, end = decoder.raw_decode(buffer, position)
                except json.JSONDecodeError:
                    if eof:
                        raise CalibrationError("QUERY_INDEX_TRUNCATED_OR_INVALID_JSON")
                    break
                if not isinstance(value, Mapping):
                    raise CalibrationError("QUERY_INDEX_ITEM_MUST_BE_OBJECT")
                yield value
                position = end

            if eof:
                if not finished:
                    trailing = buffer[position:].strip()
                    if trailing:
                        raise CalibrationError("QUERY_INDEX_TRUNCATED_OR_INVALID_JSON")
                    raise CalibrationError("QUERY_INDEX_ARRAY_NOT_CLOSED")
                break


def iter_query_index(path: Path) -> Iterator[Mapping[str, Any]]:
    if not path.is_file():
        raise CalibrationError(f"QUERY_INDEX_MISSING={path}")
    yield from _iter_top_level_array(path)


def _walk_values(value: Any, keys: Sequence[str]) -> Iterator[Any]:
    if isinstance(value, Mapping):
        for key in keys:
            if key in value:
                yield value[key]
        for child in value.values():
            if isinstance(child, (Mapping, list, tuple)):
                yield from _walk_values(child, keys)
    elif isinstance(value, (list, tuple)):
        for child in value:
            if isinstance(child, (Mapping, list, tuple)):
                yield from _walk_values(child, keys)


def _first_scalar(record: Mapping[str, Any], keys: Sequence[str]) -> str:
    for value in _walk_values(record, keys):
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value).strip()
    return ""


def _flatten_text(value: Any) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple)):
        parts: list[str] = []
        for child in value:
            parts.extend(_flatten_text(child))
        return parts
    if isinstance(value, Mapping):
        parts: list[str] = []
        for key in TEXT_KEYS:
            if key in value:
                parts.extend(_flatten_text(value[key]))
        return parts
    return []


def extract_text(record: Mapping[str, Any]) -> str:
    for value in _walk_values(record, TEXT_KEYS):
        parts = _flatten_text(value)
        if parts:
            return " ".join(parts).strip()
    return ""


def extract_tags(record: Mapping[str, Any]) -> tuple[str, ...]:
    tags: set[str] = set()
    for value in _walk_values(record, TAG_KEYS):
        if isinstance(value, str):
            tags.add(value.strip())
        elif isinstance(value, (list, tuple, set)):
            tags.update(str(item).strip() for item in value if str(item).strip())
    return tuple(sorted(tags))


def normalize_text(text: str) -> str:
    return " ".join(token.lower().replace("’", "'") for token in WORD_RE.findall(text))


def semantic_identity(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def projection_identity(record: Mapping[str, Any], text: str) -> str:
    intake_id = _first_scalar(record, ("reading_intake_id",))
    source_record_id = _first_scalar(record, ("source_record_id", "record_id"))
    source_path = _first_scalar(record, SOURCE_PATH_KEYS)
    source_type = _first_scalar(record, SOURCE_TYPE_KEYS)
    stable_source_identity = intake_id or source_record_id or source_path
    material = "|".join(
        (stable_source_identity, source_type, source_path, normalize_text(text))
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _collect_strings(value: Any, key: str) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        if key in value:
            raw = value[key]
            if isinstance(raw, str):
                result.add(raw)
            elif isinstance(raw, Sequence) and not isinstance(
                raw,
                (str, bytes, bytearray),
            ):
                result.update(str(item) for item in raw if str(item).strip())
        for child in value.values():
            if isinstance(child, (Mapping, list, tuple)):
                result.update(_collect_strings(child, key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            result.update(_collect_strings(child, key))
    return result


def _lexical_cue_from_ref(ref: str) -> str:
    if ref.startswith("vocabulary:"):
        parts = ref.split(":")
        return parts[1].replace("_", " ") if len(parts) >= 2 else ""
    if ref.startswith("chunk:"):
        return ref.split(":", 1)[1].replace("_", " ")
    return ""


def build_unit_profiles(repo_root: Path, unit_limit: int = 2) -> list[UnitProfile]:
    runtime_root = repo_root / RUNTIME_RELATIVE_ROOT
    sequence = _load_json(runtime_root / SEQUENCE_NAME)
    bundles = _load_json(runtime_root / BUNDLES_NAME)
    if not isinstance(sequence, Mapping) or not isinstance(bundles, Mapping):
        raise CalibrationError("RUNTIME_AUTHORITY_SHAPE_INVALID")
    ordered_units = sorted(
        ((str(unit), int(order)) for unit, order in sequence.items()),
        key=lambda row: row[1],
    )
    selected = ordered_units[:unit_limit]
    if len(selected) != unit_limit:
        raise CalibrationError(f"UNIT_PROFILE_COUNT_INVALID={len(selected)}")

    profiles: list[UnitProfile] = []
    for unit_id, order in selected:
        relevant = {
            key: value
            for key, value in bundles.items()
            if isinstance(key, str)
            and f":{unit_id}:" in key
            and isinstance(value, Mapping)
        }
        if not relevant:
            raise CalibrationError(f"UNIT_RUNTIME_BUNDLES_MISSING={unit_id}")
        lesson_ids = sorted(relevant)
        skills = sorted(
            {
                str(bundle.get("lesson", {}).get("skill") or "")
                for bundle in relevant.values()
                if isinstance(bundle.get("lesson"), Mapping)
            }
            - {""}
        )
        levels = sorted(
            {
                str(bundle.get("lesson", {}).get("level") or "")
                for bundle in relevant.values()
                if isinstance(bundle.get("lesson"), Mapping)
            }
            - {""}
        )
        level = levels[0] if len(levels) == 1 else "/".join(levels)
        assets: list[Mapping[str, Any]] = []
        for bundle in relevant.values():
            raw_assets = bundle.get("assets")
            if isinstance(raw_assets, list):
                assets.extend(
                    asset for asset in raw_assets if isinstance(asset, Mapping)
                )

        question_types = sorted(_collect_strings(assets, "question_type"))
        communicative_goals = sorted(_collect_strings(assets, "communicative_goal"))
        grammar_clues = sorted(_collect_strings(assets, "grammar_clue"))
        context_ids = sorted(_collect_strings(assets, "context_id"))
        target_evp = sorted(_collect_strings(assets, "target_evp_sense_ids"))
        target_egp = sorted(_collect_strings(assets, "target_egp_row_ids"))
        target_chunks = sorted(_collect_strings(assets, "target_chunk_ids"))
        target_patterns = sorted(_collect_strings(assets, "target_pattern_ids"))
        lexical_cues = sorted(
            {
                cue
                for ref in [*target_evp, *target_chunks]
                if (cue := _lexical_cue_from_ref(ref))
            }
        )
        if unit_id == "GRAMMAR_ARTICLES_BASIC":
            rule = (
                "ARTICLE_NOUN_PHRASE: require at least one a/an/the + noun phrase; "
                "lexical overlap ranks only"
            )
        elif unit_id == "GRAMMAR_REGULAR_PLURAL_NOUNS":
            rule = (
                "REGULAR_PLURAL_CONTEXT: require plural noun in numeric/determiner "
                "or plural-agreement context"
            )
        else:
            raise CalibrationError(f"PILOT_UNIT_NOT_SUPPORTED={unit_id}")
        profiles.append(
            UnitProfile(
                unit_id=unit_id,
                sequence_order=order,
                level=level,
                lesson_ids=tuple(lesson_ids),
                skills=tuple(skills),
                question_types=tuple(question_types),
                communicative_goals=tuple(communicative_goals),
                grammar_clues=tuple(grammar_clues),
                context_ids=tuple(context_ids),
                target_evp_sense_ids=tuple(target_evp),
                target_egp_row_ids=tuple(target_egp),
                target_chunk_ids=tuple(target_chunks),
                target_pattern_ids=tuple(target_patterns),
                lexical_cues=tuple(lexical_cues),
                provisional_filter_rule=rule,
            )
        )
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
    if unit_id == "GRAMMAR_REGULAR_PLURAL_NOUNS":
        candidates = [
            *PLURAL_CONTEXT_RE.findall(text),
            *PLURAL_AGREEMENT_RE.findall(text),
        ]
        filtered = [
            word for word in candidates if word.lower() not in PLURAL_FALSE_POSITIVES
        ]
        return len(filtered), {"regular_plural_context": len(filtered)}
    return 0, {}


def _lexical_hits(profile: UnitProfile, text: str) -> list[str]:
    normalized = f" {normalize_text(text)} "
    return [
        cue
        for cue in profile.lexical_cues
        if f" {normalize_text(cue)} " in normalized
    ]


def _skill_affordances(
    tags: Sequence[str],
    text: str,
    grammar_hits: int,
) -> list[str]:
    tag_set = set(tags)
    words = len(WORD_RE.findall(text))
    sentences = max(
        1,
        len([part for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]),
    )
    skills: set[str] = set()
    if words >= 3 and (
        tag_set
        & {
            "short_reading_seed",
            "comprehension_question_seed",
            "sequencing_seed",
            "assessment_seed",
            "sentence_only",
            "exercise_seed",
        }
        or sentences >= 1
    ):
        skills.add("READING")
    if "listening_audio_seed" in tag_set and words <= 100:
        skills.add("LISTENING_SCRIPT_CANDIDATE")
    if (
        tag_set
        & {"dialogue_rewrite_seed", "picture_prompt_seed", "retelling_seed"}
        or grammar_hits
    ):
        skills.add("SPEAKING_PROMPT_CANDIDATE")
    if (
        tag_set
        & {"grammar_pattern_seed", "vocabulary_exposure_seed", "exercise_seed"}
        or grammar_hits
    ):
        skills.add("WRITING_SEED_CANDIDATE")
    return sorted(skills)


def classify_record(
    record: Mapping[str, Any],
    profile: UnitProfile,
) -> dict[str, Any]:
    text = extract_text(record)
    level = _first_scalar(record, LEVEL_KEYS).upper()
    source_type = _first_scalar(record, SOURCE_TYPE_KEYS)
    source_path = _first_scalar(record, SOURCE_PATH_KEYS)
    reading_intake_id = _first_scalar(record, ("reading_intake_id",))
    source_record_id = _first_scalar(record, ("source_record_id", "record_id"))
    tags = extract_tags(record)
    words = len(WORD_RE.findall(text))
    sentences = (
        max(
            0,
            len([part for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]),
        )
        if text
        else 0
    )
    grammar_hits, grammar_evidence = _grammar_hits(profile.unit_id, text)
    lexical_hits = _lexical_hits(profile, text)
    skills = _skill_affordances(tags, text, grammar_hits) if text else []

    reasons: list[str] = []
    classification = "REJECT"
    if not reading_intake_id and not source_record_id:
        reasons.append("SOURCE_LINEAGE_ID_MISSING")
    if level not in DIRECT_USE_LEVELS | REWRITE_ONLY_LEVELS:
        reasons.append("SOURCE_LEVEL_INVALID")
    if source_type not in VALID_SOURCE_TYPES:
        reasons.append("SOURCE_TYPE_INVALID")
    if not text:
        reasons.append("TEXT_MISSING")
    if words and words < 3:
        reasons.append("TEXT_TOO_SHORT")

    hard_invalid = bool(reasons)
    if not hard_invalid:
        if grammar_hits > 0 and skills:
            if level in DIRECT_USE_LEVELS and words <= 120 and sentences <= 6:
                classification = "PASS"
                reasons.append("DIRECT_LEVEL_AND_GRAMMAR_MATCH")
            else:
                classification = "BORDERLINE"
                if level in REWRITE_ONLY_LEVELS:
                    reasons.append("REWRITE_ONLY_SOURCE_LEVEL")
                if words > 120 or sentences > 6:
                    reasons.append("DIRECT_TEXT_COMPLEXITY_EXCEEDS_PILOT_LIMIT")
        elif lexical_hits and skills:
            classification = "BORDERLINE"
            reasons.append("LEXICAL_OR_CONTEXT_MATCH_WITHOUT_TARGET_GRAMMAR")
        else:
            reasons.append("NO_UNIT_GRAMMAR_OR_LEXICAL_MATCH")

    score = grammar_hits * 10 + min(len(lexical_hits), 5) * 2 + min(len(skills), 4)
    if level in DIRECT_USE_LEVELS:
        score += 3
    if source_type:
        score += SOURCE_PRIORITY.get(source_type, 0)

    return {
        "classification": classification,
        "reasons": reasons,
        "score": score,
        "reading_intake_id": reading_intake_id,
        "source_record_id": source_record_id,
        "source_level": level,
        "source_type": source_type,
        "source_path": source_path,
        "text": text,
        "word_count": words,
        "sentence_count": sentences,
        "grammar_hits": grammar_hits,
        "grammar_evidence": grammar_evidence,
        "lexical_hits": lexical_hits,
        "reusability_tags": list(tags),
        "skill_affordances": skills,
        "semantic_identity": semantic_identity(text) if text else "",
        "projection_identity": projection_identity(record, text) if text else "",
    }


def _sample_payload(result: Mapping[str, Any]) -> dict[str, Any]:
    text = str(result.get("text") or "")
    return {
        key: result.get(key)
        for key in (
            "classification",
            "reasons",
            "score",
            "reading_intake_id",
            "source_record_id",
            "source_level",
            "source_type",
            "source_path",
            "word_count",
            "sentence_count",
            "grammar_hits",
            "grammar_evidence",
            "lexical_hits",
            "reusability_tags",
            "skill_affordances",
            "semantic_identity",
        )
    } | {"text_excerpt": text[:600]}


def run_calibration(
    *,
    repo_root: Path,
    index_path: Path,
    output_dir: Path,
    max_records: int | None = None,
    sample_limit: int = 30,
    progress_every: int = 50_000,
) -> dict[str, Any]:
    profiles = build_unit_profiles(repo_root, unit_limit=2)
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
            accumulator.counts["pre_dedup_" + classification.lower() + "_count"] += 1
            if classification == "REJECT":
                accumulator.counts["reject_count"] += 1
                for reason in result.get("reasons", []):
                    accumulator.rejection_reasons[str(reason)] += 1
                accumulator.add_reject_sample(_sample_payload(result))
            else:
                accumulator.admit_eligible(result)
        if progress_every > 0 and scanned % progress_every == 0:
            print(f"PROGRESS_RECORDS_SCANNED={scanned}")
        if max_records is not None and scanned >= max_records:
            break

    if scanned == 0:
        raise CalibrationError("QUERY_INDEX_EMPTY")

    units: list[dict[str, Any]] = []
    for profile in profiles:
        accumulator = accumulators[profile.unit_id]
        samples = accumulator.finalize()
        units.append(
            {
                "unit_profile": profile.as_dict(),
                "filter_funnel": dict(sorted(accumulator.counts.items())),
                "rejection_reasons": dict(
                    accumulator.rejection_reasons.most_common()
                ),
                "skill_capacity": dict(accumulator.skill_counts.most_common()),
                "reusability_tag_capacity": dict(
                    accumulator.tag_counts.most_common()
                ),
                "source_level_distribution": dict(
                    sorted(accumulator.level_counts.items())
                ),
                "source_type_distribution": dict(
                    accumulator.source_type_counts.most_common()
                ),
                "samples": samples,
            }
        )

    report = {
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
        },
        "provisional_policy": {
            "direct_use_source_levels": sorted(DIRECT_USE_LEVELS),
            "rewrite_only_source_levels": sorted(REWRITE_ONLY_LEVELS),
            "direct_word_limit": 120,
            "direct_sentence_limit": 6,
            "theme_only_match_is_pass": False,
            "lexical_only_match_classification": "BORDERLINE",
            "vocabulary_authority_gate": (
                "NOT_YET_APPLIED_REQUIRES_OPERATOR_CALIBRATION"
            ),
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
                any(
                    unit["samples"][name]
                    for name in ("PASS", "BORDERLINE", "REJECT")
                )
                for unit in units
            ),
            "canonical_content_modified": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = (
        output_dir / "a1fs_v1_razq01a_unit01_unit02_filter_calibration.json"
    )
    validation_path = (
        output_dir / "a1fs_v1_razq01a_unit01_unit02_filter_validation.json"
    )
    matrix_path = (
        output_dir / "a1fs_v1_razq01a_unit01_unit02_distinct_capacity_matrix.csv"
    )
    report["outputs"] = {
        "report": str(report_path),
        "validation": str(validation_path),
        "capacity_matrix": str(matrix_path),
    }
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with validation_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "schema_version": SCHEMA_VERSION,
                "task_id": TASK_ID,
                "status": PASS_STATUS,
                "records_scanned": scanned,
                "validation": report["validation"],
                "next_short_step": NEXT_SHORT_STEP,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")
    with matrix_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "unit_id",
            "sequence_order",
            "level",
            "raw_records_scanned",
            "eligible_projection_distinct_count",
            "eligible_semantic_distinct_count",
            "pass_count",
            "borderline_count",
            "reject_count",
            "reading_capacity",
            "listening_script_capacity",
            "speaking_prompt_capacity",
            "writing_seed_capacity",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for unit in units:
            profile = unit["unit_profile"]
            funnel = unit["filter_funnel"]
            skills = unit["skill_capacity"]
            writer.writerow(
                {
                    "unit_id": profile["unit_id"],
                    "sequence_order": profile["sequence_order"],
                    "level": profile["level"],
                    "raw_records_scanned": funnel.get("raw_records_scanned", 0),
                    "eligible_projection_distinct_count": funnel.get(
                        "eligible_projection_distinct_count",
                        0,
                    ),
                    "eligible_semantic_distinct_count": funnel.get(
                        "eligible_semantic_distinct_count",
                        0,
                    ),
                    "pass_count": funnel.get("pass_count", 0),
                    "borderline_count": funnel.get("borderline_count", 0),
                    "reject_count": funnel.get("reject_count", 0),
                    "reading_capacity": skills.get("READING", 0),
                    "listening_script_capacity": skills.get(
                        "LISTENING_SCRIPT_CANDIDATE",
                        0,
                    ),
                    "speaking_prompt_capacity": skills.get(
                        "SPEAKING_PROMPT_CANDIDATE",
                        0,
                    ),
                    "writing_seed_capacity": skills.get(
                        "WRITING_SEED_CANDIDATE",
                        0,
                    ),
                }
            )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--index-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-records", type=int, default=None)
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
        profile = unit["unit_profile"]
        funnel = unit["filter_funnel"]
        print(
            "UNIT="
            f"{profile['unit_id']} PASS={funnel.get('pass_count', 0)} "
            f"BORDERLINE={funnel.get('borderline_count', 0)} "
            f"REJECT={funnel.get('reject_count', 0)}"
        )
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
