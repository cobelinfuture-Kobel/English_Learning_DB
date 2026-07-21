#!/usr/bin/env python3
"""Deep, deterministic RAZ A-F semantic/material alignment.

Reads private A-F enriched page units and committed Authority files, but emits only
text-free aggregate/hash metadata. It does not promote Authority, create learner-
facing content, or read RAZ G-W.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AF_DeepSemanticMaterialAlignmentAndCoverageFullFix"
SCHEMA_VERSION = "raz.af.deep_semantic_material_alignment.v1"
PASS_STATUS = "PASS_RAZ_AF_DEEP_SEMANTIC_MATERIAL_ALIGNMENT"
LEVELS = ("A", "B", "C", "D", "E", "F")
EXPECTED_RECORD_COUNT = 4925
EXPECTED_BOOK_COUNT = 566
EXPECTED_UNIT_COUNT = 24
EXPECTED_GRAMMAR_ROW_COUNT = 109
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Private-source semantic/material observation with text-free safe output only."
)

DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_MANIFEST = REPO_ROOT / ".local/raz_af/a1_a1plus_reading_source_manifest.json"
DEFAULT_UNITS = REPO_ROOT / "ulga/graph/a1_grammar_full_teachable_candidate_coverage.json"
DEFAULT_OUTPUT = REPO_ROOT / ".local/raz_af/deep_semantic_alignment/deep_semantic_alignment.safe.json"

AUTHORITY_PATHS = {
    "vocabulary": REPO_ROOT / "ulga/graph/vocabulary_nodes.json",
    "chunks": REPO_ROOT / "chunk_profile/json/chunks_generator_safe.json",
    "patterns": REPO_ROOT / "ulga/graph/sentence_patterns.json",
    "themes": REPO_ROOT / "ulga/graph/theme_nodes.json",
}

THRESHOLDS = {
    "vocabulary_authority_coverage_rate": 0.85,
    "chunk_authority_coverage_rate": 0.75,
    "pattern_authority_coverage_rate": 0.80,
    "semantic_record_completion_rate": 0.95,
    "unit_record_count": 50,
    "unit_situation_family_count": 3,
    "unit_micro_situation_count": 5,
    "unit_communicative_function_count": 2,
    "unit_strict_core_seed_count": 8,
    "unit_passage_seed_count": 2,
}

CLAIM_BOUNDARIES = {
    "source_scope": "RAZ_A_F_ONLY",
    "g_w_read_performed": False,
    "private_source_text_read": True,
    "source_text_included_in_safe_output": False,
    "source_payload_included_in_safe_output": False,
    "learner_facing_material_created": False,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "core_sentence_candidate_created": False,
    "core_sentence_seed_count_only": True,
    "learning_unit_content_population_performed": False,
    "semantic_output_status": "DETERMINISTIC_CANDIDATE_NOT_HUMAN_REVIEWED",
    "a2_a2plus_in_scope": False,
}

TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?", re.MULTILINE)
FORBIDDEN_SAFE_KEYS = {
    "text", "source_text", "passage", "sentence", "sentences", "transcript",
    "source_payload", "learner_facing_text", "title",
}

UNIT_IDS = (
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_SUBJECT_PRONOUNS",
    "GRAMMAR_OBJECT_PRONOUNS_BASIC",
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC",
    "GRAMMAR_CAN_STATEMENT",
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES",
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS",
    "GRAMMAR_THERE_IS",
    "GRAMMAR_BE_INTERROGATIVES_A1",
    "GRAMMAR_CAN_NEGATIVE_A1",
    "GRAMMAR_WILL_FUTURE_A1",
    "GRAMMAR_PAST_SIMPLE_A1",
    "GRAMMAR_REGULAR_PLURAL_NOUNS",
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_ADJECTIVE_PHRASES_A1",
    "GRAMMAR_COORDINATION_A1",
    "GRAMMAR_BECAUSE_REASON_CLAUSES_A1",
    "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1",
    "GRAMMAR_ADVERB_PHRASES_A1",
    "GRAMMAR_NOUN_PHRASES_A1",
    "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1",
    "GRAMMAR_DEMONSTRATIVES_CONTRAST",
)

TAG_TO_UNITS = {
    "plural_noun": {"GRAMMAR_REGULAR_PLURAL_NOUNS", "GRAMMAR_NOUN_PHRASES_A1"},
    "pronoun_subject": {"GRAMMAR_SUBJECT_PRONOUNS"},
    "pronoun_object": {"GRAMMAR_OBJECT_PRONOUNS_BASIC"},
    "be_verb": {"GRAMMAR_BE_VERB_BASIC"},
    "preposition_place": {"GRAMMAR_BASIC_PREPOSITIONS_PLACE"},
    "past_simple": {"GRAMMAR_PAST_SIMPLE_A1"},
    "modal_can": {"GRAMMAR_CAN_STATEMENT"},
    "question_wh": {"GRAMMAR_BE_INTERROGATIVES_A1"},
    "question_yes_no": {"GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS"},
    "there_is": {"GRAMMAR_THERE_IS"},
    "there_are": {"GRAMMAR_THERE_IS"},
}

THEME_FAMILIES = {
    "Home": "home_objects_and_activities",
    "DailyRoutine": "daily_routines_and_time",
    "School": "school_and_classroom",
    "Food": "food_and_meals",
    "Shopping": "shopping_and_services",
    "Money": "money_and_prices",
    "Transportation": "transport_and_mobility",
    "Travel": "travel_and_places",
    "Animals": "animals_and_habitats",
    "Pets": "pets_and_care",
    "Nature": "nature_observation",
    "Weather": "weather_and_seasons",
    "Clothing": "clothes_and_getting_dressed",
    "Body": "body_and_senses",
    "Health": "health_and_wellbeing",
    "Feelings": "feelings_and_reactions",
    "Hobbies": "hobbies_and_free_time",
    "Sports": "sports_and_physical_activity",
    "Community": "community_and_public_places",
    "Personal": "personal_information",
    "Holidays": "celebrations_and_holidays",
    "Science": "science_observation",
    "Math": "numbers_shapes_and_counting",
    "Actions": "actions_and_instructions",
    "StoryFable": "story_problem_and_result",
}

KEYWORD_FAMILIES = (
    ("finding_and_locating_objects", {"find", "look", "where", "lost", "under", "behind", "inside"}),
    ("family_and_relationships", {"mother", "father", "mom", "dad", "sister", "brother", "family", "grandma", "grandpa"}),
    ("home_objects_and_activities", {"home", "house", "room", "bedroom", "kitchen", "bathroom", "table", "chair", "bed"}),
    ("school_and_classroom", {"school", "class", "teacher", "student", "pencil", "book", "lesson"}),
    ("food_and_meals", {"eat", "drink", "food", "breakfast", "lunch", "dinner", "apple", "cake"}),
    ("shopping_and_services", {"buy", "shop", "store", "price", "cost", "money", "dollar"}),
    ("transport_and_mobility", {"bus", "train", "car", "bike", "station", "ticket", "road"}),
    ("travel_and_places", {"trip", "travel", "hotel", "airport", "visit", "map"}),
    ("animals_and_habitats", {"animal", "animals", "bird", "fish", "cat", "dog", "zoo", "farm"}),
    ("nature_observation", {"tree", "plant", "flower", "pond", "river", "forest", "water"}),
    ("weather_and_seasons", {"weather", "rain", "snow", "sunny", "wind", "summer", "winter"}),
    ("clothes_and_getting_dressed", {"shirt", "dress", "shoes", "coat", "hat", "wear"}),
    ("body_and_senses", {"body", "hand", "head", "eye", "ear", "nose", "mouth"}),
    ("health_and_wellbeing", {"doctor", "sick", "hurt", "medicine", "healthy", "health"}),
    ("feelings_and_reactions", {"happy", "sad", "angry", "afraid", "scared", "excited"}),
    ("hobbies_and_free_time", {"play", "game", "music", "read", "draw", "dance", "swim"}),
    ("community_and_public_places", {"park", "library", "hospital", "museum", "town", "city"}),
    ("daily_routines_and_time", {"morning", "night", "every", "wake", "sleep", "today", "clock"}),
    ("celebrations_and_holidays", {"birthday", "party", "holiday", "christmas", "gift"}),
    ("numbers_shapes_and_counting", {"one", "two", "three", "four", "five", "number", "shape", "count"}),
    ("science_observation", {"science", "experiment", "measure", "earth", "space", "energy"}),
)

ROLE_RULES = (
    ("student_teacher", {"school", "teacher", "student", "class"}),
    ("child_parent", {"mother", "father", "mom", "dad", "parent"}),
    ("customer_shop_assistant", {"buy", "shop", "store", "price", "cost"}),
    ("traveler_transport_worker", {"ticket", "station", "airport", "bus", "train"}),
    ("patient_health_worker", {"doctor", "nurse", "medicine", "hospital"}),
    ("friend_friend", {"friend", "friends", "together"}),
    ("family_member_family_member", {"family", "sister", "brother", "grandma", "grandpa"}),
)

GOAL_RULES = (
    ("locate_or_identify", {"where", "find", "look", "who", "what"}),
    ("request_or_obtain", {"please", "give", "can", "may", "would", "buy"}),
    ("describe_entity_or_scene", {"is", "are", "has", "have", "see"}),
    ("count_or_compare", {"many", "more", "less", "than", "count"}),
    ("sequence_actions", {"first", "next", "then", "finally", "after", "before"}),
    ("express_preference", {"like", "love", "want", "favorite"}),
    ("report_past_event", {"was", "were", "had", "went", "saw", "did"}),
    ("plan_or_predict", {"will", "tomorrow", "next"}),
    ("explain_reason", {"because", "so"}),
    ("give_instruction", {"put", "take", "open", "close", "go", "come", "look"}),
)

FUNCTION_RULES = (
    ("asking_for_information", {"who", "what", "where", "when", "why", "how"}),
    ("answering_or_stating_information", {"is", "are", "am", "has", "have"}),
    ("describing_location", {"in", "on", "under", "behind", "near", "next"}),
    ("describing_quality", {"big", "small", "good", "bad", "happy", "sad", "red", "blue"}),
    ("expressing_possession", {"have", "has", "my", "your", "his", "her", "our", "their"}),
    ("expressing_ability", {"can"}),
    ("expressing_inability", {"cannot", "can't"}),
    ("expressing_preference", {"like", "love", "want", "favorite"}),
    ("narrating_past", {"was", "were", "had", "went", "saw", "did"}),
    ("referring_to_future", {"will", "tomorrow"}),
    ("giving_reason", {"because", "so"}),
    ("sequencing", {"first", "next", "then", "finally", "after", "before"}),
    ("counting_or_listing", {"one", "two", "three", "four", "five", "many"}),
    ("requesting", {"please", "may", "would"}),
)


class AlignmentError(ValueError):
    """Fail-closed source, authority, identity, or accounting error."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AlignmentError(f"json_unreadable:{path}:{exc}") from exc


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def normalize(value: str) -> str:
    value = value.replace("’", "'").casefold()
    return " ".join(token.group(0) for token in TOKEN_RE.finditer(value))


def tokens(value: str) -> list[str]:
    return [
        match.group(0).replace("’", "'").casefold()
        for match in TOKEN_RE.finditer(value)
    ]


def sentence_spans(value: str) -> list[str]:
    return [
        match.group(0).strip()
        for match in SENTENCE_RE.finditer(value)
        if match.group(0).strip()
    ]


def _rows(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, Mapping)]
    if isinstance(payload, Mapping):
        for key in ("nodes", "items", "records", "themes", "patterns", "chunks"):
            if isinstance(payload.get(key), list):
                return [row for row in payload[key] if isinstance(row, Mapping)]
    raise AlignmentError("authority_rows_unavailable")


def _row_id(row: Mapping[str, Any]) -> str | None:
    for key in (
        "id", "node_id", "safe_id", "canonical_chunk_id", "theme_id", "pattern_id"
    ):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _a1(row: Mapping[str, Any]) -> bool:
    meta = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {}
    values = (row.get("cefr_level"), row.get("level"), meta.get("cefr_level"))
    normalized = {
        str(value).upper().replace(" ", "")
        for value in values
        if value is not None
    }
    return not normalized or bool(normalized & {"A1", "A1+", "A1PLUS", "PRE-A1", "PREA1"})


def discover_page_unit_files(source_root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for level in LEVELS:
        candidates = [
            source_root / f"raz_{level}_page_unit_enriched.json",
            source_root / "derived" / f"Level_{level}" / "enriched"
            / f"raz_{level}_page_unit_enriched.json",
            source_root / f"Level_{level}" / "enriched"
            / f"raz_{level}_page_unit_enriched.json",
        ]
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is None:
            recursive = list(source_root.rglob(f"raz_{level}_page_unit_enriched.json"))
            if len(recursive) == 1:
                path = recursive[0]
        if path is None:
            raise AlignmentError(f"missing_page_unit_file:{level}")
        result[level] = path
    return result


def load_page_units(
    source_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files = discover_page_unit_files(source_root)
    rows: list[dict[str, Any]] = []
    file_index = []
    seen: set[str] = set()
    for level in LEVELS:
        path = files[level]
        payload = read_json(path)
        if not isinstance(payload, list):
            raise AlignmentError(f"page_unit_not_list:{level}")
        book_ids = set()
        for row in payload:
            if not isinstance(row, dict):
                raise AlignmentError(f"invalid_page_unit:{level}")
            ref = row.get("page_unit_id")
            if not isinstance(ref, str) or not ref or ref in seen:
                raise AlignmentError(f"invalid_or_duplicate_page_unit_id:{ref}")
            if row.get("level") != level:
                raise AlignmentError(f"page_unit_level_mismatch:{ref}")
            if not isinstance(row.get("text"), str) or not row["text"].strip():
                raise AlignmentError(f"page_unit_text_missing:{ref}")
            seen.add(ref)
            if isinstance(row.get("book_id"), str):
                book_ids.add(row["book_id"])
            rows.append(row)
        file_index.append({
            "level": level,
            "path": path.name,
            "page_unit_count": len(payload),
            "book_count": len(book_ids),
            "sha256": sha256_file(path),
        })
    return rows, file_index


def load_manifest_grammar_tags(path: Path | None) -> dict[str, set[str]]:
    if path is None or not path.is_file():
        return {}
    payload = read_json(path)
    records = payload.get("records") if isinstance(payload, Mapping) else None
    if not isinstance(records, list):
        raise AlignmentError("manifest_records_unavailable")
    result: dict[str, set[str]] = defaultdict(set)
    for row in records:
        if not isinstance(row, Mapping):
            continue
        ref = row.get("source_unit_ref")
        if not isinstance(ref, str) or not ref.startswith("RAZ_"):
            continue
        for tag in row.get("grammar_tags", []):
            if isinstance(tag, str) and tag:
                result[ref].add(tag)
    return result


def _literal_template(value: str) -> str:
    """Compile Authority chunk/pattern notation into a conservative regex."""
    raw = value.replace("’", "'").casefold().strip()
    raw = re.sub(r"\betc\.?", "", raw)
    raw = raw.replace("...", " {slot} ")
    raw = re.sub(r"\{[^{}]+\}", " {slot} ", raw)
    raw = re.sub(
        r"\b(sb|sth|swh|someone|somebody|something)\b", " {slot} ", raw
    )

    def optional_replacement(match: re.Match[str]) -> str:
        inner = match.group(1)
        if "{slot}" in inner or normalize(inner) in {
            "sb", "sth", "someone", "somebody", "something"
        }:
            return " {optional_slot} "
        return " {optional:" + normalize(inner).replace(" ", "_") + "} "

    raw = re.sub(r"\(([^()]+)\)", optional_replacement, raw)
    pieces: list[str] = []
    for part in re.split(r"(\{[^{}]+\})", raw):
        if not part:
            continue
        if part.startswith("{slot"):
            pieces.append(r"(?:[a-z][a-z']*(?:\s+[a-z][a-z']*){0,5})")
            continue
        if part.startswith("{optional_slot"):
            pieces.append(r"(?:[a-z][a-z']*(?:\s+[a-z][a-z']*){0,4})?")
            continue
        if part.startswith("{optional:"):
            words = part[len("{optional:"):-1].replace("_", " ")
            pieces.append(r"(?:" + r"\s+".join(map(re.escape, words.split())) + r")?")
            continue
        words = re.findall(
            r"[a-z]+(?:/[a-z]+)+|[a-z]+(?:'[a-z]+)?", part.casefold()
        )
        for word in words:
            if word == "be":
                pieces.append(r"(?:be|am|is|are|was|were)")
                continue
            if word == "do":
                pieces.append(r"(?:do|does|did)")
                continue
            alternatives = [re.escape(item) for item in word.split("/") if item]
            pieces.append(
                r"(?:" + "|".join(alternatives) + r")"
                if len(alternatives) > 1
                else alternatives[0]
            )
    if not pieces:
        return r"(?!x)x"
    return r"(?<![a-z'])" + r"\s+".join(pieces) + r"(?![a-z'])"


def load_authorities(paths: Mapping[str, Path] | None = None) -> dict[str, Any]:
    selected = dict(paths or AUTHORITY_PATHS)
    result: dict[str, Any] = {}
    for name, path in selected.items():
        rows = [row for row in _rows(read_json(path)) if _a1(row)]
        if name in {"chunks", "patterns"}:
            rows = [
                row for row in rows
                if (row.get("generator_allowed") is True)
                or (
                    isinstance(row.get("metadata"), Mapping)
                    and row["metadata"].get("generator_allowed") is True
                )
            ]
        prepared = []
        for row in rows:
            identifier = _row_id(row)
            if not identifier:
                continue
            metadata = (
                row.get("metadata")
                if isinstance(row.get("metadata"), Mapping)
                else {}
            )
            if name == "vocabulary":
                form = metadata.get("canonical_lemma") or row.get("label")
            elif name == "chunks":
                form = row.get("normalized_chunk") or row.get("chunk") or row.get("label")
            elif name == "patterns":
                form = metadata.get("canonical_pattern") or row.get("label")
            else:
                form = row.get("label") or metadata.get("canonical_theme")
            if not isinstance(form, str) or not form.strip():
                continue
            prepared.append({
                "id": identifier,
                "form": form,
                "normalized": normalize(form),
                "regex": _literal_template(form)
                if name in {"chunks", "patterns"}
                else None,
                "metadata": metadata,
            })
        result[name] = {
            "rows": prepared,
            "count": len(prepared),
            "ids": {row["id"] for row in prepared},
            "source_path": path.relative_to(REPO_ROOT).as_posix()
            if path.is_relative_to(REPO_ROOT)
            else str(path),
            "source_sha256": sha256_file(path),
        }
    return result


def vocabulary_forms(
    authority: Mapping[str, Any],
) -> tuple[dict[str, set[str]], list[tuple[str, str]]]:
    singles: dict[str, set[str]] = defaultdict(set)
    multi: list[tuple[str, str]] = []
    for row in authority["rows"]:
        form = row["normalized"]
        if not form:
            continue
        if " " in form:
            multi.append((row["id"], form))
        else:
            singles[form].add(row["id"])
    return singles, multi


def morphology_candidates(word: str) -> set[str]:
    result = {word}
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        result.add(word[:-1])
    if len(word) > 4 and word.endswith("ies"):
        result.add(word[:-3] + "y")
    if len(word) > 4 and word.endswith("ed"):
        result.update({word[:-2], word[:-1]})
    if len(word) > 5 and word.endswith("ing"):
        stem = word[:-3]
        result.update({stem, stem + "e"})
    if len(word) > 4 and word.endswith("er"):
        result.add(word[:-2])
    if len(word) > 5 and word.endswith("est"):
        result.add(word[:-3])
    return result


def match_vocabulary(text: str, authority: Mapping[str, Any]) -> set[str]:
    singles, multi = vocabulary_forms(authority)
    words = set(tokens(text))
    refs: set[str] = set()
    for word in words:
        for candidate in morphology_candidates(word):
            refs.update(singles.get(candidate, set()))
    normalized = normalize(text)
    for identifier, phrase in multi:
        if re.search(
            r"(?<![a-z'])" + re.escape(phrase).replace(r"\ ", r"\s+")
            + r"(?![a-z'])",
            normalized,
        ):
            refs.add(identifier)
    return refs


def match_template_authority(text: str, authority: Mapping[str, Any]) -> set[str]:
    normalized = normalize(text)
    refs = set()
    for row in authority["rows"]:
        regex = row.get("regex")
        if isinstance(regex, str) and re.search(regex, normalized):
            refs.add(row["id"])
    return refs


def semantic_alignment(row: Mapping[str, Any]) -> dict[str, set[str]]:
    text = str(row["text"])
    word_set = set(tokens(text))
    theme_tags = (
        row.get("theme_tags")
        if isinstance(row.get("theme_tags"), Mapping)
        else {}
    )
    mapped = theme_tags.get("mapped_theme") or theme_tags.get("primary_theme")
    families: set[str] = set()
    if isinstance(mapped, str) and mapped in THEME_FAMILIES:
        families.add(THEME_FAMILIES[mapped])
    for label, signals in KEYWORD_FAMILIES:
        if word_set & signals:
            families.add(label)
    if not families:
        families.add("general_child_friendly_context")

    functions = {
        label for label, signals in FUNCTION_RULES if word_set & signals
    }
    if "?" in text:
        functions.add("asking_for_information")
    if not functions:
        functions.add("stating_or_identifying")

    roles = {label for label, signals in ROLE_RULES if word_set & signals}
    content = (
        row.get("content_unit_tags")
        if isinstance(row.get("content_unit_tags"), Mapping)
        else {}
    )
    if content.get("has_direct_speech"):
        roles.add("speaker_listener")
    if not roles:
        roles.add("narrator_reader")

    goals = {label for label, signals in GOAL_RULES if word_set & signals}
    if not goals:
        goals.add("share_or_understand_information")

    micro: set[str] = set()
    for family in sorted(families):
        for goal in sorted(goals):
            micro.add(f"{family}__{goal}")
    macro = (
        {str(mapped).casefold().replace(" ", "_")}
        if isinstance(mapped, str) and mapped != "Unknown"
        else {"cross_theme_context"}
    )
    return {
        "macro_domains": macro,
        "situation_families": families,
        "micro_situations": micro,
        "communicative_functions": functions,
        "participant_roles": roles,
        "interaction_goals": goals,
    }


def grammar_units(text: str, manifest_tags: Iterable[str]) -> set[str]:
    normalized = normalize(text)
    words = tokens(text)
    word_set = set(words)
    units: set[str] = set()
    for tag in manifest_tags:
        units.update(TAG_TO_UNITS.get(tag, set()))

    if re.search(r"\b(a|an|the)\b", normalized):
        units.add("GRAMMAR_ARTICLES_BASIC")
    if word_set & {"i", "you", "he", "she", "it", "we", "they"}:
        units.add("GRAMMAR_SUBJECT_PRONOUNS")
    if word_set & {"me", "him", "her", "us", "them"}:
        units.add("GRAMMAR_OBJECT_PRONOUNS_BASIC")
    if word_set & {"my", "your", "his", "her", "its", "our", "their"}:
        units.add("GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC")
    if re.search(r"\bcan\s+(?!not\b)[a-z']+\b", normalized) and not normalized.startswith("can "):
        units.add("GRAMMAR_CAN_STATEMENT")
    if re.search(r"\b(can not|cannot|can't)\s+[a-z']+\b", normalized):
        units.add("GRAMMAR_CAN_NEGATIVE_A1")
    if re.search(r"\b(do not|don't|does not|doesn't)\s+[a-z']+\b", normalized):
        units.add("GRAMMAR_PRESENT_SIMPLE_NEGATIVES")
    if re.search(r"^(do|does)\s+[a-z']+", normalized):
        units.add("GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS")
    if re.search(r"\bthere\s+(is|are|was|were)\b", normalized):
        units.add("GRAMMAR_THERE_IS")
    if re.search(r"^(am|is|are)\s+(i|you|he|she|it|we|they|this|that|there)\b", normalized):
        units.add("GRAMMAR_BE_INTERROGATIVES_A1")
    if re.search(r"\bwill\s+[a-z']+\b", normalized):
        units.add("GRAMMAR_WILL_FUTURE_A1")
    if word_set & {"was", "were", "had", "went", "saw", "did", "made", "came", "got", "took"} or re.search(r"\b[a-z']+ed\b", normalized):
        units.add("GRAMMAR_PAST_SIMPLE_A1")
    if any(
        len(word) > 2
        and word.endswith("s")
        and word not in {"is", "was", "his", "this", "does"}
        for word in words
    ):
        units.add("GRAMMAR_REGULAR_PLURAL_NOUNS")
    if word_set & {"in", "on", "under", "behind", "between", "near", "inside", "outside", "above", "below"}:
        units.add("GRAMMAR_BASIC_PREPOSITIONS_PLACE")
    if word_set & {"am", "is", "are", "was", "were"}:
        units.add("GRAMMAR_BE_VERB_BASIC")
    if word_set & {"this", "that", "these", "those"}:
        units.add("GRAMMAR_DEMONSTRATIVES_CONTRAST")
    if word_set & {"and", "but", "or"}:
        units.add("GRAMMAR_COORDINATION_A1")
    if "because" in word_set:
        units.add("GRAMMAR_BECAUSE_REASON_CLAUSES_A1")
    if re.search(r"\b(like|love|want|need|try|start|stop|enjoy)\s+(to\s+)?[a-z']+(?:ing)?\b", normalized):
        units.add("GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1")
    if word_set & {"always", "usually", "often", "sometimes", "never", "today", "tomorrow", "yesterday", "quickly", "slowly", "very"}:
        units.add("GRAMMAR_ADVERB_PHRASES_A1")
    if re.search(r"\b(very|so|too)\s+[a-z']+\b", normalized):
        units.add("GRAMMAR_ADJECTIVE_PHRASES_A1")
    if re.search(r"\b(a|an|the|this|that|these|those|my|your|his|her|our|their)\s+[a-z']+", normalized):
        units.add("GRAMMAR_NOUN_PHRASES_A1")
    if any(not sentence.rstrip().endswith("?") for sentence in sentence_spans(text)):
        units.add("GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1")
    if re.search(r"\b(i|you|he|she|it|we|they)\s+(?:[a-z']+|am|is|are)\b", normalized):
        units.add("GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS")
    if re.search(r"\b(am|is|are|was|were)\s+(?:very\s+)?(?!a\b|an\b|the\b|in\b|on\b|at\b)[a-z']+\b", normalized):
        units.add("GRAMMAR_ADJECTIVE_PHRASES_A1")
    return units


def discourse_shape(row: Mapping[str, Any]) -> str:
    text = str(row["text"])
    normalized = normalize(text)
    content = (
        row.get("content_unit_tags")
        if isinstance(row.get("content_unit_tags"), Mapping)
        else {}
    )
    sentences = sentence_spans(text)
    if content.get("has_direct_speech") or ("?" in text and len(sentences) > 1):
        return "dialogue_or_question_answer"
    if content.get("has_sequence") or re.search(r"\b(first|next|then|finally|after|before)\b", normalized):
        return "sequence"
    if re.search(r"\bbecause\b|\bso\b", normalized):
        return "cause_effect"
    if re.search(r"\bbut\b|\bthan\b", normalized):
        return "comparison_or_contrast"
    if len(sentences) >= 2:
        return "simple_narrative_or_description"
    return "single_sentence"


def build_report(
    page_units: Sequence[Mapping[str, Any]],
    file_index: Sequence[Mapping[str, Any]],
    manifest_tags: Mapping[str, set[str]],
    authorities: Mapping[str, Any],
    learning_units: Mapping[str, Any],
    *,
    expected_record_count: int = EXPECTED_RECORD_COUNT,
    expected_book_count: int = EXPECTED_BOOK_COUNT,
) -> dict[str, Any]:
    units = [
        row for row in learning_units.get("learning_units", [])
        if isinstance(row, Mapping)
    ]
    unit_ids = {
        str(row.get("grammar_unit_id") or row.get("learning_unit_id") or row.get("id"))
        for row in units
    }
    grammar_rows = {
        str(row_id)
        for unit in units
        for row_id in unit.get("canonical_egp_row_ids", [])
        if isinstance(row_id, str)
    }

    asset_pages = {
        name: defaultdict(set) for name in ("vocabulary", "chunks", "patterns")
    }
    asset_books = {
        name: defaultdict(set) for name in ("vocabulary", "chunks", "patterns")
    }
    asset_levels = {
        name: defaultdict(set) for name in ("vocabulary", "chunks", "patterns")
    }
    semantic_sets = {name: set() for name in (
        "macro_domains", "situation_families", "micro_situations",
        "communicative_functions", "participant_roles", "interaction_goals",
    )}
    discourse_counts: Counter[str] = Counter()
    unit_acc: dict[str, dict[str, Any]] = {
        unit_id: {
            "refs": set(), "books": set(), "levels": set(),
            "vocabulary": set(), "chunks": set(), "patterns": set(),
            "families": set(), "micro": set(), "functions": set(),
            "roles": set(), "goals": set(),
            "strict_core_seed_refs": set(), "passage_seed_refs": set(),
            "dialogue_seed_refs": set(), "scene_seed_refs": set(),
        }
        for unit_id in UNIT_IDS
    }
    source_refs, books, level_counts = set(), set(), Counter()
    semantic_complete = 0
    broad_core_seeds = strict_core_seeds = 0
    passage_seeds = dialogue_seeds = scene_seeds = 0

    for row in page_units:
        ref = str(row["page_unit_id"])
        level = str(row["level"])
        book_id = str(row["book_id"])
        if ref in source_refs:
            raise AlignmentError(f"duplicate_page_unit_ref:{ref}")
        source_refs.add(ref)
        books.add((level, book_id))
        level_counts[level] += 1
        text = str(row["text"])

        vocab_refs = match_vocabulary(text, authorities["vocabulary"])
        chunk_refs = match_template_authority(text, authorities["chunks"])
        pattern_refs = match_template_authority(text, authorities["patterns"])
        semantic = semantic_alignment(row)
        detected_units = grammar_units(text, manifest_tags.get(ref, set()))
        shape = discourse_shape(row)
        discourse_counts[shape] += 1

        for name, refs in (
            ("vocabulary", vocab_refs),
            ("chunks", chunk_refs),
            ("patterns", pattern_refs),
        ):
            for asset_id in refs:
                asset_pages[name][asset_id].add(ref)
                asset_books[name][asset_id].add((level, book_id))
                asset_levels[name][asset_id].add(level)
        for name, values in semantic.items():
            semantic_sets[name].update(values)

        complete = all(semantic[name] for name in (
            "situation_families", "micro_situations", "communicative_functions",
            "participant_roles", "interaction_goals",
        ))
        semantic_complete += int(complete)
        known_semantic = (
            "general_child_friendly_context"
            not in semantic["situation_families"]
        )
        broad_seed = bool(detected_units and vocab_refs and known_semantic)
        strict_seed = bool(broad_seed and (chunk_refs or pattern_refs))
        passage_seed = int(row.get("sentence_count") or 0) >= 2
        content = (
            row.get("content_unit_tags")
            if isinstance(row.get("content_unit_tags"), Mapping)
            else {}
        )
        dialogue_seed = bool(
            content.get("has_direct_speech")
            or shape == "dialogue_or_question_answer"
        )
        reuse = (
            row.get("reuse_tags")
            if isinstance(row.get("reuse_tags"), Mapping)
            else {}
        )
        scene_seed = (
            "picture_prompt_seed" in reuse.get("reusability_tags", [])
            or known_semantic
        )

        broad_core_seeds += int(broad_seed)
        strict_core_seeds += int(strict_seed)
        passage_seeds += int(passage_seed)
        dialogue_seeds += int(dialogue_seed)
        scene_seeds += int(scene_seed)

        for unit_id in detected_units & set(UNIT_IDS):
            acc = unit_acc[unit_id]
            acc["refs"].add(ref)
            acc["books"].add((level, book_id))
            acc["levels"].add(level)
            acc["vocabulary"].update(vocab_refs)
            acc["chunks"].update(chunk_refs)
            acc["patterns"].update(pattern_refs)
            acc["families"].update(semantic["situation_families"])
            acc["micro"].update(semantic["micro_situations"])
            acc["functions"].update(semantic["communicative_functions"])
            acc["roles"].update(semantic["participant_roles"])
            acc["goals"].update(semantic["interaction_goals"])
            if strict_seed:
                acc["strict_core_seed_refs"].add(ref)
            if passage_seed:
                acc["passage_seed_refs"].add(ref)
            if dialogue_seed:
                acc["dialogue_seed_refs"].add(ref)
            if scene_seed:
                acc["scene_seed_refs"].add(ref)

    def coverage(name: str) -> dict[str, Any]:
        denominator = authorities[name]["ids"]
        observed = denominator & set(asset_pages[name])
        rate = round(len(observed) / len(denominator), 6) if denominator else 0.0
        distributions = Counter()
        for asset_id in denominator:
            page_count = len(asset_pages[name].get(asset_id, set()))
            book_count = len(asset_books[name].get(asset_id, set()))
            if page_count >= 10 and book_count >= 5:
                distributions["STRONG_RAZ_AF_SUPPORT"] += 1
            elif page_count >= 3 and book_count >= 2:
                distributions["ADEQUATE_RAZ_AF_SUPPORT"] += 1
            elif page_count >= 1:
                distributions["LIMITED_RAZ_AF_SUPPORT"] += 1
            else:
                distributions["NO_RAZ_AF_EVIDENCE"] += 1
        return {
            "authority_count": len(denominator),
            "observed_authority_count": len(observed),
            "coverage_rate": rate,
            "disposition_counts": dict(sorted(distributions.items())),
        }

    unit_reports = []
    for unit_id in UNIT_IDS:
        acc = unit_acc[unit_id]
        counts = {
            "record_count": len(acc["refs"]),
            "book_count": len(acc["books"]),
            "level_count": len(acc["levels"]),
            "vocabulary_ref_count": len(acc["vocabulary"]),
            "chunk_ref_count": len(acc["chunks"]),
            "pattern_ref_count": len(acc["patterns"]),
            "situation_family_count": len(acc["families"]),
            "micro_situation_count": len(acc["micro"]),
            "communicative_function_count": len(acc["functions"]),
            "participant_role_count": len(acc["roles"]),
            "interaction_goal_count": len(acc["goals"]),
            "strict_core_sentence_seed_count": len(acc["strict_core_seed_refs"]),
            "passage_seed_count": len(acc["passage_seed_refs"]),
            "dialogue_seed_count": len(acc["dialogue_seed_refs"]),
            "scene_seed_count": len(acc["scene_seed_refs"]),
        }
        checks = {
            "record_density": counts["record_count"] >= THRESHOLDS["unit_record_count"],
            "situation_family_density": counts["situation_family_count"] >= THRESHOLDS["unit_situation_family_count"],
            "micro_situation_density": counts["micro_situation_count"] >= THRESHOLDS["unit_micro_situation_count"],
            "communicative_function_density": counts["communicative_function_count"] >= THRESHOLDS["unit_communicative_function_count"],
            "core_sentence_seed_density": counts["strict_core_sentence_seed_count"] >= THRESHOLDS["unit_strict_core_seed_count"],
            "passage_seed_density": counts["passage_seed_count"] >= THRESHOLDS["unit_passage_seed_count"],
        }
        unit_reports.append({
            "grammar_unit_id": unit_id,
            **counts,
            "checks": checks,
            "sufficient": all(checks.values()),
        })

    vocabulary_coverage = coverage("vocabulary")
    chunk_coverage = coverage("chunks")
    pattern_coverage = coverage("patterns")
    semantic_rate = (
        round(semantic_complete / len(page_units), 6) if page_units else 0.0
    )
    source_checks = {
        "record_count_exact": len(page_units) == expected_record_count,
        "book_count_exact": len(books) == expected_book_count,
        "levels_exact": set(level_counts) == set(LEVELS),
        "learning_unit_count_exact": len(unit_ids) == EXPECTED_UNIT_COUNT,
        "learning_unit_id_set_exact": unit_ids == set(UNIT_IDS),
        "grammar_row_count_exact": len(grammar_rows) == EXPECTED_GRAMMAR_ROW_COUNT,
    }
    checks = {
        "source_integrity": all(source_checks.values()),
        "vocabulary_coverage": vocabulary_coverage["coverage_rate"]
        >= THRESHOLDS["vocabulary_authority_coverage_rate"],
        "chunk_coverage": chunk_coverage["coverage_rate"]
        >= THRESHOLDS["chunk_authority_coverage_rate"],
        "pattern_coverage": pattern_coverage["coverage_rate"]
        >= THRESHOLDS["pattern_authority_coverage_rate"],
        "semantic_alignment_complete": semantic_rate
        >= THRESHOLDS["semantic_record_completion_rate"],
        "all_24_units_sufficient": len(unit_reports) == EXPECTED_UNIT_COUNT
        and all(row["sufficient"] for row in unit_reports),
    }
    if not checks["source_integrity"]:
        decision = "BLOCKED_SOURCE_INTEGRITY"
    elif not checks["semantic_alignment_complete"]:
        decision = "DEEPEN_AF_SEMANTIC_EXTRACTION_BEFORE_GW"
    elif all(checks.values()):
        decision = "AF_SUFFICIENT_FOR_CONTENT_POPULATION"
    else:
        decision = "TARGETED_GW_EXPANSION_REQUIRED"

    authority_baselines = {
        name: {
            "count": value["count"],
            "source_path": value["source_path"],
            "source_sha256": value["source_sha256"],
        }
        for name, value in authorities.items()
    }
    weak_units = [
        {
            "grammar_unit_id": row["grammar_unit_id"],
            "failed_checks": sorted(
                key for key, passed in row["checks"].items() if not passed
            ),
        }
        for row in unit_reports
        if not row["sufficient"]
    ]
    report: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "source_scope": {
            "levels": list(LEVELS),
            "record_count": len(page_units),
            "book_count": len(books),
            "level_counts": {level: level_counts[level] for level in LEVELS},
            "source_files": list(file_index),
            "manifest_grammar_ref_count": len(manifest_tags),
            "g_w_read_performed": False,
        },
        "authority_baselines": authority_baselines,
        "material_alignment": {
            "vocabulary": vocabulary_coverage,
            "chunks": chunk_coverage,
            "sentence_patterns": pattern_coverage,
            "theme_situation": {
                "macro_domain_count": len(semantic_sets["macro_domains"]),
                "situation_family_count": len(semantic_sets["situation_families"]),
                "micro_situation_count": len(semantic_sets["micro_situations"]),
                "communicative_function_count": len(semantic_sets["communicative_functions"]),
                "participant_role_count": len(semantic_sets["participant_roles"]),
                "interaction_goal_count": len(semantic_sets["interaction_goals"]),
                "semantic_complete_record_count": semantic_complete,
                "semantic_record_completion_rate": semantic_rate,
                "semantic_status": "DETERMINISTIC_CANDIDATE_NOT_HUMAN_REVIEWED",
            },
            "grammar_usage": {
                "observed_unit_count": sum(
                    bool(unit_acc[unit_id]["refs"]) for unit_id in UNIT_IDS
                ),
                "unit_denominator": EXPECTED_UNIT_COUNT,
            },
            "discourse_shape_counts": dict(sorted(discourse_counts.items())),
            "seeds": {
                "broad_core_sentence_seed_record_count": broad_core_seeds,
                "strict_core_sentence_seed_record_count": strict_core_seeds,
                "short_passage_seed_record_count": passage_seeds,
                "dialogue_seed_record_count": dialogue_seeds,
                "scene_seed_record_count": scene_seeds,
            },
        },
        "learning_unit_suitability": sorted(
            unit_reports, key=lambda row: row["grammar_unit_id"]
        ),
        "sufficiency_gate": {
            "checks": checks,
            "source_checks": source_checks,
            "decision": decision,
            "af_sufficient_for_content_population": decision
            == "AF_SUFFICIENT_FOR_CONTENT_POPULATION",
            "targeted_gw_expansion_allowed": decision
            == "TARGETED_GW_EXPANSION_REQUIRED",
            "weak_unit_count": len(weak_units),
            "weak_units": weak_units,
            "next_short_step": (
                "RAZ-AF_ContentPopulationBinding"
                if decision == "AF_SUFFICIENT_FOR_CONTENT_POPULATION"
                else "RAZ-GW_TargetedGapSourceExpansion"
                if decision == "TARGETED_GW_EXPANSION_REQUIRED"
                else "RAZ-AF_DeepSemanticMaterialAlignmentAndCoverageFullFix"
            ),
        },
        "thresholds": dict(THRESHOLDS),
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    report["report_sha256"] = sha256_value(report)
    return report


def scan_forbidden_safe_keys(value: Any, pointer: str = "$") -> list[str]:
    errors = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                errors.append(f"forbidden_safe_key:{pointer}.{key}")
            errors.extend(scan_forbidden_safe_keys(child, f"{pointer}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(scan_forbidden_safe_keys(child, f"{pointer}[{index}]"))
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--learning-units", type=Path, default=DEFAULT_UNITS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        page_units, file_index = load_page_units(args.source_root)
        manifest_tags = load_manifest_grammar_tags(args.manifest)
        authorities = load_authorities()
        units = read_json(args.learning_units)
        report = build_report(
            page_units, file_index, manifest_tags, authorities, units
        )
        leakage = scan_forbidden_safe_keys(report)
        if leakage:
            raise AlignmentError("safe_output_leakage:" + ";".join(leakage[:10]))
        write_json_atomic(args.output, report)
        print(json.dumps({
            "task_id": TASK_ID,
            "decision": report["sufficiency_gate"]["decision"],
            "weak_unit_count": report["sufficiency_gate"]["weak_unit_count"],
            "report_sha256": report["report_sha256"],
        }, sort_keys=True))
        return 0
    except (AlignmentError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
