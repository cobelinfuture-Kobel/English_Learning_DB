#!/usr/bin/env python3
"""Contextually place RAZ A-I Theme gaps and source topic labels.

This consumer upgrades the evidence-only review package into deterministic,
context-aware candidate placement.  It reads the verified A-W matching package
and the private A-I enriched page units, evaluates each source label in its
same-book previous/current/next-page context, and emits only text-free
placement evidence.

It never writes canonical Authority, fabricates human approval, emits RAZ
source text, opens A2/A2+, or populates learner-facing Learning Units.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI_ContextualThemeTopicPlacement"
SCHEMA_VERSION = "raz.ai.contextual_theme_topic_placement.v2"
PASS_STATUS = "PASS_RAZ_AI_CONTEXTUAL_THEME_TOPIC_PLACEMENT"

CONTEXT_LEVELS = tuple(chr(code) for code in range(ord("A"), ord("I") + 1))
EXPECTED_PAGE_UNIT_COUNT = 22632
EXPECTED_BOOK_COUNT = 1959
EXPECTED_CONTEXT_PAGE_UNIT_COUNT = 7957
EXPECTED_GAP_FAMILY_COUNT = 10
EXPECTED_UNVERIFIED_TOPIC_LABEL_COUNT = 240

DEFAULT_INPUT = (
    REPO_ROOT
    / ".local/raz_aw/theme_authority_candidate_matching/"
    / "theme_authority_candidate_matching.safe.json"
)
DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / ".local/raz_aw/theme_gap_evidence_topic_review/"
    / "theme_gap_evidence_topic_review.safe.json"
)

# The ten source families were proven by the corrected private replay.  These
# are placement decisions, not canonical Authority mutations.
GAP_FAMILY_PLACEMENTS: dict[str, dict[str, Any]] = {
    "animals_and_habitats": {
        "primary_placement_layer": "THEME_AUTHORITY",
        "placement_disposition": "NEW_A1_THEME_CANDIDATE",
        "candidate_target_refs": ["theme_candidate:a1_animals_and_habitats"],
        "canonical_action": "HUMAN_THEME_AUTHORITY_DECISION_REQUIRED",
    },
    "pets_and_animal_care": {
        "primary_placement_layer": "THEME_TOPIC_TAXONOMY",
        "placement_disposition": "CHILD_TOPIC_OF_ANIMALS_THEME",
        "candidate_target_refs": [
            "theme_candidate:a1_animals_and_habitats",
            "theme_topic:pets_and_animal_care",
        ],
        "canonical_action": "DEPENDENT_ON_PARENT_THEME_DECISION",
    },
    "nature_and_environment": {
        "primary_placement_layer": "THEME_AUTHORITY",
        "placement_disposition": "NEW_A1_THEME_CANDIDATE",
        "candidate_target_refs": ["theme_candidate:a1_nature_and_environment"],
        "canonical_action": "HUMAN_THEME_AUTHORITY_DECISION_REQUIRED",
    },
    "holidays_and_culture": {
        "primary_placement_layer": "THEME_AUTHORITY",
        "placement_disposition": "NEW_A1_THEME_CANDIDATE",
        "candidate_target_refs": ["theme_candidate:a1_holidays_and_culture"],
        "canonical_action": "HUMAN_THEME_AUTHORITY_DECISION_REQUIRED",
    },
    "feelings_character_and_social_emotional": {
        "primary_placement_layer": "THEME_AUTHORITY_AND_SEL_TAXONOMY",
        "placement_disposition": "EXPAND_EXISTING_THEME_AND_SPLIT_SEL_SKILLS",
        "candidate_target_refs": [
            "theme:a1_personal_information_and_greetings",
            "sel_domain:social_emotional_learning",
        ],
        "canonical_action": "HUMAN_THEME_AUTHORITY_DECISION_REQUIRED",
    },
    "math_and_concepts": {
        "primary_placement_layer": "CONTENT_DOMAIN_TAXONOMY",
        "placement_disposition": "RECLASSIFY_OUTSIDE_THEME_AUTHORITY",
        "candidate_target_refs": ["content_domain:mathematics_and_early_concepts"],
        "canonical_action": "NO_THEME_AUTHORITY_ACTION_RECLASSIFIED",
    },
    "science_and_nature_nonfiction": {
        "primary_placement_layer": "CONTENT_DOMAIN_AND_GENRE_TAXONOMY",
        "placement_disposition": "RECLASSIFY_OUTSIDE_THEME_AUTHORITY",
        "candidate_target_refs": [
            "content_domain:science_and_nature",
            "text_genre:nonfiction",
        ],
        "canonical_action": "NO_THEME_AUTHORITY_ACTION_RECLASSIFIED",
    },
    "history_and_civics": {
        "primary_placement_layer": "CONTENT_DOMAIN_TAXONOMY",
        "placement_disposition": "RECLASSIFY_OUTSIDE_THEME_AUTHORITY",
        "candidate_target_refs": ["content_domain:history_and_civics"],
        "canonical_action": "NO_THEME_AUTHORITY_ACTION_RECLASSIFIED",
    },
    "fairy_tales_and_folktales": {
        "primary_placement_layer": "TEXT_GENRE_TAXONOMY",
        "placement_disposition": "RECLASSIFY_OUTSIDE_THEME_AUTHORITY",
        "candidate_target_refs": [
            "text_genre:fairy_tale",
            "text_genre:folktale",
        ],
        "canonical_action": "NO_THEME_AUTHORITY_ACTION_RECLASSIFIED",
    },
    "fantasy_fable_and_moral_stories": {
        "primary_placement_layer": "TEXT_GENRE_AND_SKILL_TAXONOMY",
        "placement_disposition": "RECLASSIFY_OUTSIDE_THEME_AUTHORITY",
        "candidate_target_refs": [
            "text_genre:fantasy",
            "text_genre:fable",
            "text_genre:moral_story",
            "sel_skill:moral_reasoning",
        ],
        "canonical_action": "NO_THEME_AUTHORITY_ACTION_RECLASSIFIED",
    },
}

TEXT_GENRE_LABELS = {
    "animal_story",
    "biography",
    "fable",
    "fairy_tale",
    "fantasy",
    "folktale",
    "holiday_story",
    "monster_story",
    "moral_story",
    "nonfiction",
    "story",
}
ENTITY_TYPE_LABELS = {"imaginary_character", "royalty"}
SEL_SKILL_LABELS = {
    "character_trait",
    "feelings",
    "friendship",
    "identity",
    "manners",
    "moral_choice",
    "problem_solving",
    "relationships",
    "self_regulation",
    "social_emotional",
}
CONTENT_DOMAIN_LABELS = {
    "adaptation",
    "body_parts",
    "civics",
    "concept_words",
    "history",
    "landforms",
    "math",
    "physical_science",
    "preservation",
    "science",
    "structures",
    "symbols",
}
SITUATION_LABELS = {
    "animal_care",
    "camping",
    "celebration",
    "everyday_life",
    "food_preparation",
    "gift_giving",
    "lost_found",
    "outing",
    "pet_fish",
}
ENTITY_REGISTRY_LABELS = {"jupe"}

FORM_NORMALIZATIONS = {
    "aching": "ache",
    "airplanes": "airplane",
    "ate": "eat",
    "athletes": "athlete",
    "bears": "bear",
    "bees": "bee",
    "blocks": "block",
    "bones": "bone",
    "cards": "card",
    "caves": "cave",
    "coins": "coin",
    "cookies": "cookie",
    "costs": "cost",
    "counting": "count",
    "dinosaurs": "dinosaur",
    "doubling": "double",
    "dreams": "dream",
    "ducks": "duck",
    "earthworms": "earthworm",
    "feet": "foot",
    "fossils": "fossil",
    "grandparents": "grandparent",
    "helpers": "helper",
    "insects": "insect",
    "jumps": "jump",
    "landmarks": "landmark",
    "mammals": "mammal",
    "mountains": "mountain",
    "moves": "move",
    "moving": "move",
    "mummies": "mummy",
    "muscles": "muscle",
    "neighbors": "neighbor",
    "pennies": "penny",
    "pirates": "pirate",
    "pumpkins": "pumpkin",
    "rabbits": "rabbit",
    "relationships": "relationship",
    "reptiles": "reptile",
    "rocks": "rock",
    "running": "run",
    "saves": "save",
    "seasons": "season",
    "shapes": "shape",
    "sleds": "sled",
    "sneezing": "sneeze",
    "socks": "sock",
    "sounds": "sound",
    "spending": "spend",
    "structures": "structure",
    "symbols": "symbol",
    "tastes": "taste",
    "teeth": "tooth",
    "trucks": "truck",
    "wheels": "wheel",
    "workers": "worker",
    "worms": "worm",
}

GENRE_TARGETS = {
    "animal_story": "text_genre:animal_story",
    "biography": "text_genre:biography",
    "fable": "text_genre:fable",
    "fairy_tale": "text_genre:fairy_tale",
    "fantasy": "text_genre:fantasy",
    "folktale": "text_genre:folktale",
    "holiday_story": "text_genre:holiday_story",
    "monster_story": "text_genre:fantasy_monster_story",
    "moral_story": "text_genre:moral_story",
    "nonfiction": "text_genre:nonfiction",
    "story": "text_genre:narrative_story",
}
ENTITY_TYPE_TARGETS = {
    "imaginary_character": "entity_type:imaginary_character",
    "royalty": "entity_type:royalty",
}
SEL_TARGETS = {
    "character_trait": "sel_skill:character_traits",
    "feelings": "sel_skill:feelings_and_emotions",
    "friendship": "sel_skill:friendship",
    "identity": "sel_skill:identity",
    "manners": "sel_skill:manners",
    "moral_choice": "sel_skill:moral_choice",
    "problem_solving": "sel_skill:problem_solving",
    "relationships": "sel_skill:relationships",
    "self_regulation": "sel_skill:self_regulation",
    "social_emotional": "sel_domain:social_emotional_learning",
}
CONTENT_TARGETS = {
    "adaptation": "content_concept:biological_adaptation",
    "body_parts": "content_domain:body_and_senses",
    "civics": "content_domain:history_and_civics",
    "concept_words": "content_domain:early_concepts",
    "history": "content_domain:history_and_civics",
    "landforms": "content_domain:earth_science_landforms",
    "math": "content_domain:mathematics",
    "physical_science": "content_domain:physical_science",
    "preservation": "content_domain:environmental_preservation",
    "science": "content_domain:science",
    "structures": "content_domain:structures_and_engineering",
    "symbols": "content_domain:symbols_and_representation",
}
SITUATION_TARGETS = {
    "animal_care": "situation:animal_care",
    "camping": "situation:camping",
    "celebration": "situation:celebration",
    "everyday_life": "situation:everyday_life",
    "food_preparation": "situation:food_preparation",
    "gift_giving": "situation:gift_giving",
    "lost_found": "situation:lost_and_found",
    "outing": "situation:outing",
    "pet_fish": "situation:pet_fish_care",
}
ENTITY_REGISTRY_TARGETS = {"jupe": "entity_registry:character:jupe"}

PRIMARY_THEME_DESTINATIONS = {
    "Actions and Movement": ["activity_domain:actions_and_movement"],
    "Animal Nonfiction": [
        "theme_candidate:a1_animals_and_habitats",
        "content_domain:science_and_nature",
        "text_genre:nonfiction",
    ],
    "Animals": ["theme_candidate:a1_animals_and_habitats"],
    "Body and Senses": ["theme:a1_health_and_medical"],
    "Clothing": ["theme:a1_shopping_and_basic_transactions"],
    "Community": ["theme:a1_homes_and_neighborhoods"],
    "Culture and Holiday Traditions": ["theme_candidate:a1_holidays_and_culture"],
    "Daily Routine": ["theme:a1_daily_life_and_routines"],
    "Fairy Tale": ["text_genre:fairy_tale"],
    "Fantasy and Monster Story": ["text_genre:fantasy"],
    "Feelings and Character": [
        "theme:a1_personal_information_and_greetings",
        "sel_domain:social_emotional_learning",
    ],
    "Folktale and Fairy Tale": [
        "text_genre:folktale",
        "text_genre:fairy_tale",
    ],
    "Food": ["theme:a1_food_and_dining"],
    "Health": ["theme:a1_health_and_medical"],
    "History and Civics": ["content_domain:history_and_civics"],
    "Hobbies": ["theme:a1_interests_and_abilities"],
    "Holidays and Events": ["theme_candidate:a1_holidays_and_culture"],
    "Home": ["theme:a1_homes_and_neighborhoods"],
    "Math and Concepts": ["content_domain:mathematics_and_early_concepts"],
    "Math and Geometry": ["content_domain:mathematics_and_geometry"],
    "Math and Numbers": ["content_domain:mathematics_and_numbers"],
    "Money and Finance": ["theme:a1_shopping_and_basic_transactions"],
    "Nature": ["theme_candidate:a1_nature_and_environment"],
    "Personal": ["theme:a1_personal_information_and_greetings"],
    "Pets and Animal Care": [
        "theme_candidate:a1_animals_and_habitats",
        "theme_topic:pets_and_animal_care",
    ],
    "School": ["theme:a1_school_and_classroom"],
    "Science": ["content_domain:science"],
    "Science and Nature Nonfiction": [
        "content_domain:science_and_nature",
        "text_genre:nonfiction",
    ],
    "Shopping": ["theme:a1_shopping_and_basic_transactions"],
    "Social and Emotional Learning": [
        "theme:a1_personal_information_and_greetings",
        "sel_domain:social_emotional_learning",
    ],
    "Sports": ["theme:a1_interests_and_abilities"],
    "Transportation": ["theme:a1_travel_and_weather"],
    "Travel": ["theme:a1_travel_and_weather"],
    "Weather and Seasons": ["theme:a1_travel_and_weather"],
    "Unknown": ["context_destination:unresolved"],
}

FORBIDDEN_SAFE_KEYS = set(matching.FORBIDDEN_SAFE_KEYS)
CLAIM_BOUNDARIES = {
    "candidate_matching_package_read_performed": True,
    "raz_a_i_private_context_read_performed": True,
    "same_book_previous_current_next_context_used": True,
    "source_text_included_in_safe_output": False,
    "source_title_included_in_safe_output": False,
    "ai_contextual_candidate_adjudication_performed": True,
    "human_semantic_review_performed": False,
    "human_decision_fabricated": False,
    "canonical_authority_write_performed": False,
    "authority_promotion_performed": False,
    "learning_unit_population_performed": False,
    "learner_facing_content_created": False,
    "a2_a2plus_opened": False,
}


class ThemeGapEvidenceError(ValueError):
    """Fail-closed input, context, identity, accounting, or leakage error."""


def _verify_input(
    package: Mapping[str, Any],
    *,
    expected_page_unit_count: int,
    expected_book_count: int,
) -> tuple[list[Mapping[str, Any]], set[str], set[str]]:
    if package.get("task_id") != matching.TASK_ID:
        raise ThemeGapEvidenceError("matching_task_id_mismatch")
    if package.get("validation_status") != matching.PASS_STATUS:
        raise ThemeGapEvidenceError("matching_validation_status_not_pass")
    if package.get("errors") != []:
        raise ThemeGapEvidenceError("matching_errors_not_empty")
    gate = package.get("matching_gate")
    if not isinstance(gate, Mapping) or gate.get("decision") != (
        "THEME_AUTHORITY_CANDIDATES_READY_FOR_LOCAL_VALIDATION"
    ):
        raise ThemeGapEvidenceError("matching_gate_not_ready")

    claimed_hash = package.get("package_sha256")
    if not isinstance(claimed_hash, str) or len(claimed_hash) != 64:
        raise ThemeGapEvidenceError("matching_package_sha256_invalid")
    reconstructed = dict(package)
    reconstructed.pop("package_sha256", None)
    if deep.sha256_value(reconstructed) != claimed_hash:
        raise ThemeGapEvidenceError("matching_package_sha256_mismatch")

    identity = package.get("input_material_identity")
    if not isinstance(identity, Mapping):
        raise ThemeGapEvidenceError("input_material_identity_missing")
    if identity.get("page_unit_count") != expected_page_unit_count:
        raise ThemeGapEvidenceError("page_unit_count_mismatch")
    if identity.get("book_count") != expected_book_count:
        raise ThemeGapEvidenceError("book_count_mismatch")

    rows = package.get("theme_subtheme_candidates")
    if not isinstance(rows, list) or not all(
        isinstance(row, Mapping) for row in rows
    ):
        raise ThemeGapEvidenceError("candidate_rows_invalid")
    if len(rows) != expected_page_unit_count:
        raise ThemeGapEvidenceError("candidate_row_count_mismatch")
    refs = [str(row.get("source_unit_ref") or "") for row in rows]
    if any(not ref for ref in refs) or len(refs) != len(set(refs)):
        raise ThemeGapEvidenceError("candidate_ref_invalid_or_duplicate")

    family_rows = package.get("source_macro_theme_family_candidates")
    if not isinstance(family_rows, list):
        raise ThemeGapEvidenceError(
            "source_macro_theme_family_candidates_missing"
        )
    gap_ids = {
        str(row.get("source_macro_theme_family_id"))
        for row in family_rows
        if isinstance(row, Mapping)
        and row.get("coverage_status") == "AUTHORITY_GAP_CANDIDATE"
    }

    topic = package.get("source_topic_label_classification")
    if not isinstance(topic, Mapping):
        raise ThemeGapEvidenceError("source_topic_label_classification_missing")
    unverified = topic.get("unverified_source_topic_labels")
    if not isinstance(unverified, list) or not all(
        isinstance(value, str) for value in unverified
    ):
        raise ThemeGapEvidenceError("unverified_source_topic_labels_invalid")

    leakage = matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise ThemeGapEvidenceError(
            "matching_package_safe_output_leakage:" + ";".join(leakage[:20])
        )
    return rows, gap_ids, set(unverified)


def _discover_context_file(source_root: Path, level: str) -> Path:
    candidates = [
        source_root / f"raz_{level}_page_unit_enriched.json",
        source_root / "derived" / f"Level_{level}" / "enriched"
        / f"raz_{level}_page_unit_enriched.json",
        source_root / f"Level_{level}" / "enriched"
        / f"raz_{level}_page_unit_enriched.json",
    ]
    present = [path for path in candidates if path.is_file()]
    if not present:
        present = list(
            source_root.rglob(f"raz_{level}_page_unit_enriched.json")
        )
    unique = {path.resolve() for path in present}
    if len(unique) != 1:
        raise ThemeGapEvidenceError(
            f"context_file_resolution_not_unique:{level}:{len(unique)}"
        )
    return next(iter(unique))


def load_context_rows(
    source_root: Path,
    *,
    levels: Sequence[str] = CONTEXT_LEVELS,
    expected_context_page_unit_count: int = EXPECTED_CONTEXT_PAGE_UNIT_COUNT,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    source_index: list[dict[str, Any]] = []
    seen: set[str] = set()
    for level in levels:
        path = _discover_context_file(source_root, level)
        payload = deep.read_json(path)
        if not isinstance(payload, list):
            raise ThemeGapEvidenceError(f"context_payload_not_list:{level}")
        level_books: set[str] = set()
        for item in payload:
            if not isinstance(item, Mapping):
                raise ThemeGapEvidenceError(f"context_row_not_object:{level}")
            ref = str(item.get("page_unit_id") or "")
            book_id = str(item.get("book_id") or "")
            page_number = item.get("page_number")
            source_text = item.get("text")
            if (
                not ref
                or ref in seen
                or item.get("level") != level
                or not book_id
                or not isinstance(page_number, int)
                or not isinstance(source_text, str)
                or not source_text.strip()
            ):
                raise ThemeGapEvidenceError(
                    f"context_identity_or_content_invalid:{level}:{ref}"
                )
            rows.append(dict(item))
            seen.add(ref)
            level_books.add(book_id)
        source_index.append(
            {
                "level": level,
                "source_path": path.relative_to(source_root).as_posix()
                if path.is_relative_to(source_root)
                else str(path),
                "source_page_unit_count": len(payload),
                "source_book_count": len(level_books),
                "source_sha256": deep.sha256_file(path),
            }
        )
    if len(rows) != expected_context_page_unit_count:
        raise ThemeGapEvidenceError(
            "context_page_unit_count_mismatch:"
            f"{len(rows)}:{expected_context_page_unit_count}"
        )
    return rows, source_index


def _theme_tags(row: Mapping[str, Any]) -> Mapping[str, Any]:
    value = row.get("theme_tags")
    return value if isinstance(value, Mapping) else {}


def _primary_theme(row: Mapping[str, Any]) -> str:
    tags = _theme_tags(row)
    value = tags.get("primary_theme") or tags.get("mapped_theme") or "Unknown"
    return str(value) if value else "Unknown"


def _source_subthemes(row: Mapping[str, Any]) -> set[str]:
    value = _theme_tags(row).get("subthemes")
    if not isinstance(value, list):
        return set()
    return {
        str(item)
        for item in value
        if isinstance(item, str) and item.strip()
    }


def _book_context_index(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[
    dict[str, Mapping[str, Any]],
    dict[str, tuple[Mapping[str, Any] | None, Mapping[str, Any] | None]],
]:
    by_ref: dict[str, Mapping[str, Any]] = {}
    by_book: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        ref = str(row["page_unit_id"])
        by_ref[ref] = row
        by_book[(str(row["level"]), str(row["book_id"]))].append(row)

    neighbors: dict[
        str,
        tuple[Mapping[str, Any] | None, Mapping[str, Any] | None],
    ] = {}
    for book_rows in by_book.values():
        ordered = sorted(
            book_rows,
            key=lambda item: (
                int(item.get("page_number") or 0),
                str(item.get("page_unit_id") or ""),
            ),
        )
        for index, row in enumerate(ordered):
            previous = ordered[index - 1] if index > 0 else None
            following = (
                ordered[index + 1] if index + 1 < len(ordered) else None
            )
            neighbors[str(row["page_unit_id"])] = (previous, following)
    return by_ref, neighbors


def _private_context(
    current: Mapping[str, Any],
    neighbors: tuple[
        Mapping[str, Any] | None, Mapping[str, Any] | None
    ],
) -> str:
    previous, following = neighbors
    parts: list[str] = []
    for row in (previous, current, following):
        if not isinstance(row, Mapping):
            continue
        for key in ("title", "text"):
            value = row.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
    return " ".join(parts)


def _context_destinations(primary_theme: str) -> set[str]:
    return set(
        PRIMARY_THEME_DESTINATIONS.get(
            primary_theme, ["context_destination:unresolved"]
        )
    )


def _building_candidate_targets(
    current_private_context: str,
    three_page_private_context: str,
    primary_theme: str,
) -> set[str]:
    current = current_private_context.casefold()
    action = bool(
        re.search(
            r"\b(?:am|is|are|was|were|be|been|being|start|starts|started|"
            r"keep|keeps|kept)\s+building\b",
            current,
        )
        or re.search(r"\bbuilding\s+(?:a|an|the|with)\b", current)
    )
    entity = bool(
        re.search(
            r"\b(?:a|an|the|this|that|my|your|our|their)\s+"
            r"(?:[a-z]+\s+){0,2}building\b",
            current,
        )
        or re.search(r"\bbuilding\s+(?:is|was|has|had)\b", current)
    )
    targets: set[str] = set()
    if action:
        targets.add("vocabulary_candidate:build")
    if entity:
        targets.add("vocabulary_candidate:building")
    if targets:
        return targets

    broader = three_page_private_context.casefold()
    if re.search(r"\bbuilding\s+(?:a|an|the|with)\b", broader):
        targets.add("vocabulary_candidate:build")
    if re.search(
        r"\b(?:a|an|the|this|that|my|your|our|their)\s+"
        r"(?:[a-z]+\s+){0,2}building\b",
        broader,
    ):
        targets.add("vocabulary_candidate:building")
    if not targets:
        targets.add(
            "vocabulary_candidate:build"
            if primary_theme == "Actions and Movement"
            else "vocabulary_candidate:building"
        )
    return targets


def _placement_for_occurrence(
    label: str,
    *,
    primary_theme: str,
    current_private_context: str,
    three_page_private_context: str,
) -> dict[str, Any]:
    destinations = _context_destinations(primary_theme)

    if label in TEXT_GENRE_LABELS:
        return {
            "primary_placement_layer": "TEXT_GENRE_TAXONOMY",
            "placement_status": "CONTEXT_CONFIRMED_SPECIALIZED_PLACEMENT",
            "candidate_target_refs": {GENRE_TARGETS[label]},
            "context_destination_refs": destinations,
        }
    if label in ENTITY_TYPE_LABELS:
        return {
            "primary_placement_layer": "ENTITY_TYPE_TAXONOMY",
            "placement_status": "CONTEXT_CONFIRMED_SPECIALIZED_PLACEMENT",
            "candidate_target_refs": {ENTITY_TYPE_TARGETS[label]},
            "context_destination_refs": destinations,
        }
    if label in SEL_SKILL_LABELS:
        return {
            "primary_placement_layer": "SOCIAL_EMOTIONAL_SKILL_TAXONOMY",
            "placement_status": "CONTEXT_CONFIRMED_SPECIALIZED_PLACEMENT",
            "candidate_target_refs": {SEL_TARGETS[label]},
            "context_destination_refs": destinations,
        }
    if label in CONTENT_DOMAIN_LABELS:
        return {
            "primary_placement_layer": "CONTENT_DOMAIN_TAXONOMY",
            "placement_status": "CONTEXT_CONFIRMED_SPECIALIZED_PLACEMENT",
            "candidate_target_refs": {CONTENT_TARGETS[label]},
            "context_destination_refs": destinations,
        }
    if label in SITUATION_LABELS:
        return {
            "primary_placement_layer": "SITUATION_TAXONOMY",
            "placement_status": "CONTEXT_CONFIRMED_SPECIALIZED_PLACEMENT",
            "candidate_target_refs": {SITUATION_TARGETS[label]},
            "context_destination_refs": destinations,
        }
    if label in ENTITY_REGISTRY_LABELS:
        return {
            "primary_placement_layer": "ENTITY_REGISTRY",
            "placement_status": "CONTEXT_CONFIRMED_SPECIALIZED_PLACEMENT",
            "candidate_target_refs": {ENTITY_REGISTRY_TARGETS[label]},
            "context_destination_refs": destinations,
        }
    if label == "carrier":
        return {
            "primary_placement_layer": "VOCABULARY_AUTHORITY",
            "placement_status": "CONTEXT_CONFIRMED_SPECIALIZED_PLACEMENT",
            "candidate_target_refs": {
                "vocabulary_phrase_candidate:mail_carrier"
            },
            "context_destination_refs": destinations,
        }
    if label == "building":
        return {
            "primary_placement_layer": "VOCABULARY_AUTHORITY",
            "placement_status": "CONTEXT_CONFIRMED_SPECIALIZED_PLACEMENT",
            "candidate_target_refs": _building_candidate_targets(
                current_private_context,
                three_page_private_context,
                primary_theme,
            ),
            "context_destination_refs": destinations,
        }

    lemma = FORM_NORMALIZATIONS.get(label, label)
    status = (
        "NORMALIZE_INFLECTED_OR_PLURAL_FORM"
        if label in FORM_NORMALIZATIONS
        else "LEMMA_CANDIDATE"
    )
    candidate = f"vocabulary_candidate:{matching._normal_label(lemma).replace(' ', '_')}"
    if label == "sink" and primary_theme == "Home":
        candidate = "vocabulary_candidate:sink_fixture"
    return {
        "primary_placement_layer": "VOCABULARY_AUTHORITY",
        "placement_status": status,
        "candidate_target_refs": {candidate},
        "context_destination_refs": destinations,
    }


def _assert_theme_targets_exist(
    authorities: Mapping[str, Any],
    gap_family_placements: Mapping[str, Mapping[str, Any]],
) -> None:
    themes = authorities.get("themes")
    if not isinstance(themes, Mapping):
        raise ThemeGapEvidenceError("theme_authority_missing")
    ids = themes.get("ids")
    if not isinstance(ids, set):
        ids = {
            str(row.get("id"))
            for row in themes.get("rows", [])
            if isinstance(row, Mapping) and isinstance(row.get("id"), str)
        }
    existing_targets = {
        target
        for placement in gap_family_placements.values()
        for target in placement["candidate_target_refs"]
        if target.startswith("theme:")
    }
    if not existing_targets <= ids:
        raise ThemeGapEvidenceError(
            "existing_theme_target_missing:"
            + ",".join(sorted(existing_targets - ids))
        )


def build_package(
    matching_package: Mapping[str, Any],
    context_rows: Sequence[Mapping[str, Any]],
    context_source_index: Sequence[Mapping[str, Any]],
    authorities: Mapping[str, Any],
    *,
    expected_page_unit_count: int = EXPECTED_PAGE_UNIT_COUNT,
    expected_book_count: int = EXPECTED_BOOK_COUNT,
    expected_context_page_unit_count: int = EXPECTED_CONTEXT_PAGE_UNIT_COUNT,
    expected_gap_family_count: int = EXPECTED_GAP_FAMILY_COUNT,
    expected_unverified_topic_label_count: int = (
        EXPECTED_UNVERIFIED_TOPIC_LABEL_COUNT
    ),
    gap_family_placements: Mapping[str, Mapping[str, Any]] = (
        GAP_FAMILY_PLACEMENTS
    ),
) -> dict[str, Any]:
    _, gap_ids, unverified_labels = _verify_input(
        matching_package,
        expected_page_unit_count=expected_page_unit_count,
        expected_book_count=expected_book_count,
    )
    if len(context_rows) != expected_context_page_unit_count:
        raise ThemeGapEvidenceError(
            "context_page_unit_count_mismatch:"
            f"{len(context_rows)}:{expected_context_page_unit_count}"
        )
    if gap_ids != set(gap_family_placements):
        raise ThemeGapEvidenceError(
            "gap_family_contract_mismatch:"
            + ",".join(sorted(gap_ids ^ set(gap_family_placements)))
        )
    if len(unverified_labels) != expected_unverified_topic_label_count:
        raise ThemeGapEvidenceError(
            "unverified_topic_label_count_mismatch:"
            f"{len(unverified_labels)}:{expected_unverified_topic_label_count}"
        )
    _assert_theme_targets_exist(authorities, gap_family_placements)

    by_ref, neighbor_index = _book_context_index(context_rows)
    context_refs = set(by_ref)
    if len(context_refs) != len(context_rows):
        raise ThemeGapEvidenceError("context_ref_duplicate")

    family_state: dict[str, dict[str, Any]] = {
        family: {
            "levels": set(),
            "books": set(),
            "units": set(),
            "source_labels": set(),
            "topic_labels": set(),
            "primary_theme_counts": Counter(),
            "destination_counts": Counter(),
        }
        for family in gap_ids
    }
    topic_state: dict[str, dict[str, Any]] = {
        label: {
            "levels": set(),
            "books": set(),
            "units": set(),
            "primary_themes": set(),
            "layers": set(),
            "statuses": set(),
            "targets": set(),
            "destination_counts": Counter(),
            "context_span_page_counts": Counter(),
        }
        for label in unverified_labels
    }
    occurrence_rows: list[dict[str, Any]] = []

    observed_context_labels: set[str] = set()
    for ref, row in by_ref.items():
        primary = _primary_theme(row)
        source_labels = _source_subthemes(row)
        relevant_labels = source_labels & unverified_labels
        family: str | None = None
        if primary != "Unknown":
            try:
                family = matching._source_macro_family(primary)
            except matching.ThemeAuthorityCandidateMatchingError as exc:
                raise ThemeGapEvidenceError(
                    f"context_primary_theme_unrecognized:{ref}:{primary}"
                ) from exc

        if family in family_state:
            state = family_state[family]
            state["levels"].add(str(row["level"]))
            state["books"].add(f"{row['level']}:{row['book_id']}")
            state["units"].add(ref)
            state["source_labels"].add(primary)
            state["topic_labels"].update(source_labels)
            state["primary_theme_counts"][primary] += 1
            for destination in _context_destinations(primary):
                state["destination_counts"][destination] += 1

        if not relevant_labels:
            continue

        three_page_private_context = _private_context(
            row, neighbor_index[ref]
        )
        current_private_context = " ".join(
            str(row.get(key) or "")
            for key in ("title", "text")
        )
        previous, following = neighbor_index[ref]
        context_span_page_count = 1 + int(previous is not None) + int(
            following is not None
        )
        for label in sorted(relevant_labels):
            observed_context_labels.add(label)
            placement = _placement_for_occurrence(
                label,
                primary_theme=primary,
                current_private_context=current_private_context,
                three_page_private_context=three_page_private_context,
            )
            state = topic_state[label]
            state["levels"].add(str(row["level"]))
            state["books"].add(f"{row['level']}:{row['book_id']}")
            state["units"].add(ref)
            state["primary_themes"].add(primary)
            state["layers"].add(placement["primary_placement_layer"])
            state["statuses"].add(placement["placement_status"])
            state["targets"].update(placement["candidate_target_refs"])
            state["context_span_page_counts"][context_span_page_count] += 1
            for destination in placement["context_destination_refs"]:
                state["destination_counts"][destination] += 1
            occurrence_rows.append(
                {
                    "source_unit_ref": ref,
                    "source_level": str(row["level"]),
                    "source_book_id": str(row["book_id"]),
                    "source_topic_label": label,
                    "source_primary_theme": primary,
                    "primary_placement_layer": placement[
                        "primary_placement_layer"
                    ],
                    "placement_status": placement["placement_status"],
                    "candidate_target_refs": sorted(
                        placement["candidate_target_refs"]
                    ),
                    "context_destination_refs": sorted(
                        placement["context_destination_refs"]
                    ),
                    "context_span_page_count": context_span_page_count,
                    "source_context_status": (
                        "PRIVATE_PREVIOUS_CURRENT_NEXT_CONTEXT_CONSUMED"
                    ),
                }
            )

    if observed_context_labels != unverified_labels:
        raise ThemeGapEvidenceError(
            "context_topic_labels_not_reconciled:"
            + ",".join(sorted(observed_context_labels ^ unverified_labels))
        )

    family_rows: list[dict[str, Any]] = []
    for family in sorted(gap_ids):
        state = family_state[family]
        placement = gap_family_placements[family]
        family_rows.append(
            {
                "source_macro_theme_family_id": family,
                "source_macro_theme_labels": sorted(state["source_labels"]),
                "source_level_count": len(state["levels"]),
                "source_levels": sorted(state["levels"]),
                "source_book_count": len(state["books"]),
                "source_unit_count": len(state["units"]),
                "associated_source_topic_label_count": len(
                    state["topic_labels"]
                ),
                "source_primary_theme_counts": dict(
                    sorted(state["primary_theme_counts"].items())
                ),
                "context_destination_counts": dict(
                    sorted(state["destination_counts"].items())
                ),
                "primary_placement_layer": placement[
                    "primary_placement_layer"
                ],
                "placement_disposition": placement[
                    "placement_disposition"
                ],
                "candidate_target_refs": list(
                    placement["candidate_target_refs"]
                ),
                "canonical_action": placement["canonical_action"],
                "ai_contextual_placement_status": (
                    "CONTEXTUALLY_PLACED_CANDIDATE"
                ),
                "authority_status": "candidate_only",
                "review_status": "ai_contextual_adjudicated",
                "promotion_status": "promotion_blocked",
            }
        )

    topic_rows: list[dict[str, Any]] = []
    for label in sorted(unverified_labels):
        state = topic_state[label]
        if not state["units"]:
            raise ThemeGapEvidenceError(
                f"contextual_topic_evidence_missing:{label}"
            )
        topic_rows.append(
            {
                "source_topic_label": label,
                "source_level_count": len(state["levels"]),
                "source_levels": sorted(state["levels"]),
                "source_book_count": len(state["books"]),
                "source_unit_count": len(state["units"]),
                "source_primary_themes": sorted(state["primary_themes"]),
                "primary_placement_layers": sorted(state["layers"]),
                "placement_statuses": sorted(state["statuses"]),
                "candidate_target_refs": sorted(state["targets"]),
                "context_destination_counts": dict(
                    sorted(state["destination_counts"].items())
                ),
                "context_span_page_counts": {
                    str(key): value
                    for key, value in sorted(
                        state["context_span_page_counts"].items()
                    )
                },
                "context_variant_count": len(
                    {
                        (
                            row["primary_placement_layer"],
                            tuple(row["candidate_target_refs"]),
                            tuple(row["context_destination_refs"]),
                        )
                        for row in occurrence_rows
                        if row["source_topic_label"] == label
                    }
                ),
                "manual_placement_required": False,
                "ai_contextual_placement_status": (
                    "CONTEXTUALLY_PLACED_CANDIDATE"
                ),
                "authority_status": "candidate_only",
                "review_status": "ai_contextual_adjudicated",
                "promotion_status": "promotion_blocked",
            }
        )

    layer_counts = Counter(
        row["primary_placement_layers"][0]
        if len(row["primary_placement_layers"]) == 1
        else "MULTI_LAYER_CONTEXT_SPLIT"
        for row in topic_rows
    )
    status_counts = Counter(
        row["placement_statuses"][0]
        if len(row["placement_statuses"]) == 1
        else "MULTI_STATUS_CONTEXT_SPLIT"
        for row in topic_rows
    )
    canonical_theme_action_count = sum(
        row["canonical_action"]
        == "HUMAN_THEME_AUTHORITY_DECISION_REQUIRED"
        for row in family_rows
    )
    dependent_topic_count = sum(
        row["canonical_action"] == "DEPENDENT_ON_PARENT_THEME_DECISION"
        for row in family_rows
    )
    reclassified_gap_count = sum(
        row["canonical_action"]
        == "NO_THEME_AUTHORITY_ACTION_RECLASSIFIED"
        for row in family_rows
    )

    expected_canonical_theme_action_count = sum(
        placement["canonical_action"]
        == "HUMAN_THEME_AUTHORITY_DECISION_REQUIRED"
        for placement in gap_family_placements.values()
    )
    expected_dependent_topic_count = sum(
        placement["canonical_action"] == "DEPENDENT_ON_PARENT_THEME_DECISION"
        for placement in gap_family_placements.values()
    )
    expected_reclassified_gap_count = sum(
        placement["canonical_action"]
        == "NO_THEME_AUTHORITY_ACTION_RECLASSIFIED"
        for placement in gap_family_placements.values()
    )

    checks = {
        "context_page_unit_count_exact": (
            len(context_rows) == expected_context_page_unit_count
        ),
        "gap_family_count_exact": (
            len(family_rows) == expected_gap_family_count
        ),
        "topic_label_count_exact": (
            len(topic_rows) == expected_unverified_topic_label_count
        ),
        "all_gap_families_have_context_evidence": all(
            row["source_unit_count"] > 0 and row["source_book_count"] > 0
            for row in family_rows
        ),
        "all_topic_labels_have_context_evidence": all(
            row["source_unit_count"] > 0 and row["source_book_count"] > 0
            for row in topic_rows
        ),
        "all_topic_labels_have_placement": all(
            row["primary_placement_layers"]
            and row["candidate_target_refs"]
            and row["context_destination_counts"]
            and not row["manual_placement_required"]
            for row in topic_rows
        ),
        "all_occurrences_have_three_page_context_contract": all(
            row["context_span_page_count"] in {1, 2, 3}
            and row["source_context_status"]
            == "PRIVATE_PREVIOUS_CURRENT_NEXT_CONTEXT_CONSUMED"
            for row in occurrence_rows
        ),
        "canonical_theme_action_count_exact": (
            canonical_theme_action_count
            == expected_canonical_theme_action_count
        ),
        "dependent_theme_topic_count_exact": (
            dependent_topic_count == expected_dependent_topic_count
        ),
        "non_theme_reclassified_gap_count_exact": (
            reclassified_gap_count == expected_reclassified_gap_count
        ),
        "candidate_boundaries_preserved": all(
            row["authority_status"] == "candidate_only"
            and row["review_status"] == "ai_contextual_adjudicated"
            and row["promotion_status"] == "promotion_blocked"
            for row in family_rows + topic_rows
        ),
    }
    ready = all(checks.values())

    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_matching_identity": {
            "task_id": matching_package["task_id"],
            "package_sha256": matching_package["package_sha256"],
            "page_unit_count": expected_page_unit_count,
            "book_count": expected_book_count,
        },
        "private_context_source": {
            "levels": list(CONTEXT_LEVELS),
            "page_unit_count": len(context_rows),
            "source_files": [dict(row) for row in context_source_index],
            "context_contract": "SAME_BOOK_PREVIOUS_CURRENT_NEXT_PAGE",
            "source_text_included_in_output": False,
        },
        "contextual_theme_family_placements": family_rows,
        "contextual_source_topic_placements": topic_rows,
        "contextual_occurrence_placements": sorted(
            occurrence_rows,
            key=lambda row: (
                row["source_topic_label"],
                row["source_unit_ref"],
            ),
        ),
        "aggregate_summary": {
            "contextual_theme_family_placement_count": len(family_rows),
            "contextual_source_topic_placement_count": len(topic_rows),
            "contextual_occurrence_placement_count": len(occurrence_rows),
            "canonical_theme_action_family_count": (
                canonical_theme_action_count
            ),
            "dependent_theme_topic_family_count": dependent_topic_count,
            "non_theme_reclassified_gap_family_count": (
                reclassified_gap_count
            ),
            "manual_topic_placement_required_count": sum(
                row["manual_placement_required"] for row in topic_rows
            ),
            "topic_primary_placement_layer_counts": dict(
                sorted(layer_counts.items())
            ),
            "topic_placement_status_counts": dict(
                sorted(status_counts.items())
            ),
        },
        "placement_gate": {
            "source_checks": checks,
            "decision": (
                "CONTEXTUAL_THEME_AND_TOPIC_PLACEMENTS_READY"
                if ready
                else "BLOCKED_CONTEXTUAL_THEME_OR_TOPIC_PLACEMENT"
            ),
            "human_theme_authority_decision_required": (
                canonical_theme_action_count > 0
            ),
            "human_topic_placement_required": False,
            "ready_for_canonical_promotion": False,
            "ready_for_learning_unit_population": False,
            "next_short_step": (
                "RAZ-AI_ContextualPlacementCoverageRecheck"
            ),
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    leakage = matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise ThemeGapEvidenceError(
            "safe_output_leakage:" + ";".join(leakage[:20])
        )
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _readback(package: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "decision": package["placement_gate"]["decision"],
        **package["aggregate_summary"],
        "package_sha256": package["package_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matching-package", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        source = deep.read_json(args.matching_package)
        if not isinstance(source, Mapping):
            raise ThemeGapEvidenceError("matching_package_not_object")
        context_rows, context_source_index = load_context_rows(
            args.source_root
        )
        package = build_package(
            source,
            context_rows,
            context_source_index,
            deep.load_authorities(),
        )
        deep.write_json_atomic(args.output, package)
        print(json.dumps(_readback(package), sort_keys=True))
        return 0
    except (
        ThemeGapEvidenceError,
        matching.ThemeAuthorityCandidateMatchingError,
        deep.AlignmentError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
