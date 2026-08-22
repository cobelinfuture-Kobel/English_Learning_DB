#!/usr/bin/env python3
"""Build the deterministic Unit02 vocabulary-to-scene coverage matrix.

U02SC01 is a read-only pedagogical projection over the governed U02QB01
162-noun plain-s authority. It does not create canonical scenes, learner-facing
content, QuestionBank items, or new vocabulary/chunk authority.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from ulga.builders import (
    build_a1fs_v1_u02qb02_unit02_plain_s_questionbank_candidate_pool as u02qb02,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only vocabulary-to-scene coverage projection over already-governed "
    "Unit02 vocabulary; no learner-facing content or canonical scene is authored."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02SC01_Unit02VocabularySceneCoverageMatrix"
SCHEMA_VERSION = "a1fs.v1.u02sc01.unit02_vocabulary_scene_coverage_matrix.v1"
PASS_STATUS = "PASS_A1FS_V1_U02SC01_UNIT02_VOCABULARY_SCENE_COVERAGE_MATRIX"
UNIT_ID = u02qb02.UNIT_ID
LEVEL_SCOPE = ["A1"]
EXPECTED_NOUN_COUNT = u02qb02.EXPECTED_NOUN_SURFACES
EXPECTED_EXACT_VOCABULARY_REFS = u02qb02.EXPECTED_EXACT_NOUN_REFS

PATTERN_ELIGIBILITY_KEYS = (
    "observation",
    "possession",
    "preference_positive",
    "preference_negative",
    "request",
    "governed_adjective_contrast",
)

SCENE_GATES = (
    "DIRECT_SCENE_ELIGIBLE",
    "SUPPORT_ONLY",
    "SENSE_CHECK_REQUIRED",
    "PEDAGOGICAL_DEFER",
    "SEMANTICALLY_INAPPLICABLE",
)

PRIMARY_FAMILY_MEMBERS = {'SCHOOL_CLASSROOM_LEARNING': ('answer',
                               'bag',
                               'book',
                               'chair',
                               'colour',
                               'computer',
                               'course',
                               'desk',
                               'language',
                               'lesson',
                               'number',
                               'page',
                               'pen',
                               'pencil',
                               'question',
                               'school',
                               'sentence',
                               'student',
                               'subject',
                               'table',
                               'test',
                               'word'),
 'HOME_BEDROOM_LIVING': ('bed',
                         'bedroom',
                         'door',
                         'flat',
                         'floor',
                         'home',
                         'house',
                         'key',
                         'living room',
                         'room',
                         'wall',
                         'window'),
 'BATHROOM_SELF_CARE': ('bath', 'bathroom', 'shower', 'toilet'),
 'KITCHEN_DINING': ('dining room', 'kitchen', 'cup', 'meal', 'plate'),
 'FOOD_CAFE_PICNIC': ('apple',
                      'banana',
                      'bar',
                      'beer',
                      'biscuit',
                      'café',
                      'cake',
                      'chip',
                      'chocolate',
                      'coffee',
                      'drink',
                      'egg',
                      'fruit',
                      'ice cream',
                      'juice',
                      'orange',
                      'picnic',
                      'pizza',
                      'soup',
                      'tea',
                      'vegetable'),
 'FAMILY_PEOPLE_SOCIAL': ('adult',
                          'boy',
                          'brother',
                          'dad',
                          'daughter',
                          'father',
                          'friend',
                          'girl',
                          'group',
                          'husband',
                          'mother',
                          'mum',
                          'parent',
                          'sister',
                          'son',
                          'birthday'),
 'BODY_APPEARANCE': ('arm',
                     'beard',
                     'bottom',
                     'ear',
                     'eye',
                     'face',
                     'hand',
                     'head',
                     'leg',
                     'mouth',
                     'nose'),
 'CLOTHING_PERSONAL_ITEMS': ('coat', 'hat', 'jacket', 'shirt', 'shoe', 'skirt', 'T-shirt'),
 'PETS_FARM_ZOO': ('animal', 'bird', 'cat', 'cow', 'dog', 'farm', 'horse', 'pet', 'pig', 'zoo'),
 'PARK_GARDEN_NATURE': ('flower', 'garden', 'park', 'plant', 'river', 'sea', 'sun', 'tree'),
 'SPORTS_PLAY': ('ball', 'basketball', 'doll', 'football', 'game', 'player', 'sport'),
 'MUSIC_DANCE': ('band', 'dance', 'guitar'),
 'MEDIA_ENTERTAINMENT_TECH': ('camera',
                              'CD',
                              'CD player',
                              'DVD',
                              'film',
                              'movie',
                              'newspaper',
                              'photo',
                              'picture',
                              'radio',
                              'television',
                              'website'),
 'TOWN_PUBLIC_PLACES': ('cinema', 'museum', 'place', 'town', 'village'),
 'SHOP_MONEY_SERVICES': ('bank', 'dollar'),
 'TRANSPORT_TRAVEL': ('boat',
                      'car',
                      'holiday',
                      'plane',
                      'road',
                      'station',
                      'stop',
                      'street',
                      'taxi',
                      'train'),
 'COMMUNICATION_WRITING': ('conversation', 'letter', 'message', 'name', 'note'),
 'CONTEXT_DEPENDENT': ('end', 'job')}

SCENE_FAMILIES = tuple(PRIMARY_FAMILY_MEMBERS)
EXPECTED_FAMILY_COUNTS = {
    family: len(members) for family, members in PRIMARY_FAMILY_MEMBERS.items()
}

SUPPORT_ONLY_NOUNS = frozenset(['answer',
 'colour',
 'conversation',
 'course',
 'language',
 'lesson',
 'message',
 'name',
 'note',
 'number',
 'question',
 'sentence',
 'subject',
 'test',
 'word'])
SENSE_CHECK_NOUNS = frozenset(['coffee', 'end', 'fruit', 'ice cream', 'job', 'juice', 'place', 'soup', 'tea'])
PEDAGOGICAL_DEFER_NOUNS = frozenset(['bar', 'beer', 'sun'])
CHILD_UNSUITABLE_NOUNS = frozenset(['bar', 'beer'])
SENSE_CHECK_EXTRA_NOUNS = frozenset(['bar'])

OBSERVATION_FALSE_NOUNS = frozenset(['answer',
 'birthday',
 'conversation',
 'course',
 'dance',
 'end',
 'holiday',
 'job',
 'language',
 'lesson',
 'meal',
 'message',
 'name',
 'sport',
 'subject',
 'test'])
POSSESSION_ELIGIBLE_NOUNS = frozenset(['CD',
 'CD player',
 'DVD',
 'T-shirt',
 'answer',
 'apple',
 'arm',
 'bag',
 'ball',
 'banana',
 'basketball',
 'bed',
 'bird',
 'book',
 'brother',
 'cake',
 'camera',
 'car',
 'cat',
 'chair',
 'chip',
 'chocolate',
 'coat',
 'computer',
 'cow',
 'cup',
 'dad',
 'daughter',
 'desk',
 'dog',
 'doll',
 'dollar',
 'drink',
 'ear',
 'egg',
 'eye',
 'father',
 'film',
 'flower',
 'football',
 'friend',
 'game',
 'guitar',
 'hand',
 'hat',
 'horse',
 'house',
 'ice cream',
 'jacket',
 'juice',
 'key',
 'leg',
 'letter',
 'meal',
 'message',
 'mother',
 'movie',
 'mum',
 'newspaper',
 'note',
 'orange',
 'page',
 'parent',
 'pen',
 'pencil',
 'pet',
 'photo',
 'picture',
 'pig',
 'pizza',
 'plant',
 'plate',
 'radio',
 'room',
 'shirt',
 'shoe',
 'sister',
 'skirt',
 'son',
 'soup',
 'table',
 'tea',
 'television',
 'tree',
 'vegetable',
 'window'])
PREFERENCE_ELIGIBLE_NOUNS = frozenset(['CD',
 'CD player',
 'DVD',
 'T-shirt',
 'animal',
 'apple',
 'ball',
 'banana',
 'band',
 'basketball',
 'bird',
 'biscuit',
 'boat',
 'book',
 'cake',
 'camera',
 'car',
 'cat',
 'chip',
 'chocolate',
 'cinema',
 'coat',
 'coffee',
 'colour',
 'computer',
 'cow',
 'dance',
 'dog',
 'doll',
 'drink',
 'film',
 'flower',
 'football',
 'fruit',
 'game',
 'garden',
 'guitar',
 'hat',
 'holiday',
 'horse',
 'ice cream',
 'jacket',
 'juice',
 'language',
 'meal',
 'movie',
 'museum',
 'newspaper',
 'orange',
 'park',
 'pet',
 'photo',
 'picnic',
 'picture',
 'pig',
 'pizza',
 'place',
 'plane',
 'plant',
 'radio',
 'river',
 'school',
 'sea',
 'shirt',
 'shoe',
 'skirt',
 'soup',
 'sport',
 'subject',
 'tea',
 'television',
 'town',
 'train',
 'tree',
 'vegetable',
 'village',
 'website',
 'zoo'])
REQUEST_ELIGIBLE_NOUNS = frozenset(['CD',
 'CD player',
 'DVD',
 'T-shirt',
 'apple',
 'bag',
 'ball',
 'banana',
 'basketball',
 'biscuit',
 'book',
 'cake',
 'camera',
 'chair',
 'chip',
 'chocolate',
 'coat',
 'coffee',
 'computer',
 'cup',
 'doll',
 'dollar',
 'drink',
 'egg',
 'flower',
 'football',
 'game',
 'guitar',
 'hat',
 'ice cream',
 'jacket',
 'juice',
 'key',
 'meal',
 'newspaper',
 'orange',
 'pen',
 'pencil',
 'photo',
 'picture',
 'pizza',
 'plate',
 'radio',
 'shirt',
 'shoe',
 'skirt',
 'soup',
 'tea',
 'television',
 'vegetable'])
GOVERNED_ADJECTIVE_CONTRAST_NOUNS = frozenset(['bag', 'book'])

DEFAULT_SECONDARY_BY_PRIMARY = {'BATHROOM_SELF_CARE': ('HOME_BEDROOM_LIVING',),
 'KITCHEN_DINING': ('HOME_BEDROOM_LIVING',),
 'FOOD_CAFE_PICNIC': ('KITCHEN_DINING',),
 'FAMILY_PEOPLE_SOCIAL': ('HOME_BEDROOM_LIVING',),
 'BODY_APPEARANCE': ('FAMILY_PEOPLE_SOCIAL',),
 'CLOTHING_PERSONAL_ITEMS': ('SHOP_MONEY_SERVICES',),
 'PETS_FARM_ZOO': ('PARK_GARDEN_NATURE',),
 'SPORTS_PLAY': ('PARK_GARDEN_NATURE',),
 'MUSIC_DANCE': ('SCHOOL_CLASSROOM_LEARNING',),
 'MEDIA_ENTERTAINMENT_TECH': ('HOME_BEDROOM_LIVING',),
 'TOWN_PUBLIC_PLACES': ('TRANSPORT_TRAVEL',),
 'SHOP_MONEY_SERVICES': ('TOWN_PUBLIC_PLACES',),
 'TRANSPORT_TRAVEL': ('TOWN_PUBLIC_PLACES',),
 'COMMUNICATION_WRITING': ('SCHOOL_CLASSROOM_LEARNING',)}
SECONDARY_OVERRIDES = {'bag': ('SHOP_MONEY_SERVICES',),
 'book': ('SHOP_MONEY_SERVICES', 'HOME_BEDROOM_LIVING'),
 'computer': ('MEDIA_ENTERTAINMENT_TECH', 'HOME_BEDROOM_LIVING'),
 'school': ('TOWN_PUBLIC_PLACES',),
 'table': ('KITCHEN_DINING', 'HOME_BEDROOM_LIVING'),
 'park': ('TOWN_PUBLIC_PLACES',),
 'garden': ('HOME_BEDROOM_LIVING',),
 'farm': ('TOWN_PUBLIC_PLACES',),
 'zoo': ('TOWN_PUBLIC_PLACES', 'TRANSPORT_TRAVEL'),
 'camera': ('FAMILY_PEOPLE_SOCIAL', 'TRANSPORT_TRAVEL'),
 'photo': ('FAMILY_PEOPLE_SOCIAL',),
 'picture': ('FAMILY_PEOPLE_SOCIAL', 'SCHOOL_CLASSROOM_LEARNING'),
 'website': ('SCHOOL_CLASSROOM_LEARNING',),
 'holiday': ('FAMILY_PEOPLE_SOCIAL',),
 'picnic': ('PARK_GARDEN_NATURE', 'FAMILY_PEOPLE_SOCIAL'),
 'café': ('TOWN_PUBLIC_PLACES',),
 'bank': ('TOWN_PUBLIC_PLACES',)}

NEXT_SHORT_STEP = (
    "A1FS-V1-U02SC02_"
    "Unit01CanonicalSceneToUnit02ApplicabilityProjection"
)


class Unit02SceneCoverageBuildError(ValueError):
    """Fail-closed U02SC01 construction error."""


def inventory_by_singular() -> dict[str, dict[str, Any]]:
    return u02qb02.inventory_by_singular()


def primary_family_by_singular() -> dict[str, str]:
    result: dict[str, str] = {}
    for family, members in PRIMARY_FAMILY_MEMBERS.items():
        for singular in members:
            if singular in result:
                raise Unit02SceneCoverageBuildError(
                    f"DUPLICATE_PRIMARY_FAMILY_ASSIGNMENT:{singular}"
                )
            result[singular] = family
    return result


def secondary_families(singular: str, primary_family: str) -> list[str]:
    values = SECONDARY_OVERRIDES.get(
        singular,
        DEFAULT_SECONDARY_BY_PRIMARY.get(primary_family, ()),
    )
    result: list[str] = []
    for value in values:
        if value == primary_family:
            continue
        if value not in SCENE_FAMILIES:
            raise Unit02SceneCoverageBuildError(
                f"UNKNOWN_SECONDARY_SCENE_FAMILY:{singular}:{value}"
            )
        if value not in result:
            result.append(value)
    return result


def scene_gate(singular: str) -> str:
    if singular in PEDAGOGICAL_DEFER_NOUNS:
        return "PEDAGOGICAL_DEFER"
    if singular in SENSE_CHECK_NOUNS:
        return "SENSE_CHECK_REQUIRED"
    if singular in SUPPORT_ONLY_NOUNS:
        return "SUPPORT_ONLY"
    return "DIRECT_SCENE_ELIGIBLE"


def notes_for(singular: str, gate: str) -> list[str]:
    notes: list[str] = []
    if gate == "SUPPORT_ONLY":
        notes.append("ABSTRACT_OR_META_LANGUAGE_SUPPORT_NOT_PRIMARY_SCENE_DRIVER")
    if singular == "bar":
        notes.append("AMBIGUOUS_OR_ADULT_CONTEXT_REQUIRES_SENSE_REVIEW")
    if singular == "beer":
        notes.append("CHILD_UNSUITABLE_AS_LEARNER_TARGET_RETAIN_SOURCE_AUTHORITY_ONLY")
    if singular == "sun":
        notes.append("PLURAL_SUNS_NOT_NATURAL_A1_EVERYDAY_SCENE")
    if singular in {"coffee", "fruit", "ice cream", "juice", "soup", "tea"}:
        notes.append("PLURAL_REQUIRES_SERVING_OR_TYPE_SENSE_REVIEW")
    if singular in {"end", "job", "place"}:
        notes.append("CONTEXT_OR_SENSE_REQUIRED_BEFORE_SCENE_BINDING")
    if singular in GOVERNED_ADJECTIVE_CONTRAST_NOUNS:
        notes.append("U02CH01_GOVERNED_ADJECTIVE_PLURAL_CONTRAST_AVAILABLE")
    return notes


def pattern_eligibility(singular: str) -> dict[str, bool]:
    preference = singular in PREFERENCE_ELIGIBLE_NOUNS
    child_ok = singular not in CHILD_UNSUITABLE_NOUNS
    gate = scene_gate(singular)
    direct_pattern_use = gate not in {"PEDAGOGICAL_DEFER", "SEMANTICALLY_INAPPLICABLE"}
    return {
        "observation": direct_pattern_use and singular not in OBSERVATION_FALSE_NOUNS,
        "possession": direct_pattern_use and singular in POSSESSION_ELIGIBLE_NOUNS,
        "preference_positive": direct_pattern_use and child_ok and preference,
        "preference_negative": direct_pattern_use and child_ok and preference,
        "request": direct_pattern_use and child_ok and singular in REQUEST_ELIGIBLE_NOUNS,
        "governed_adjective_contrast": (
            direct_pattern_use and singular in GOVERNED_ADJECTIVE_CONTRAST_NOUNS
        ),
    }


def build_rows() -> list[dict[str, Any]]:
    inventory = inventory_by_singular()
    primary = primary_family_by_singular()
    source_singulars = set(inventory)
    mapped_singulars = set(primary)
    if source_singulars != mapped_singulars:
        missing = sorted(source_singulars - mapped_singulars)
        extra = sorted(mapped_singulars - source_singulars)
        raise Unit02SceneCoverageBuildError(
            f"PRIMARY_SCENE_COVERAGE_DRIFT:missing={missing}:extra={extra}"
        )
    rows: list[dict[str, Any]] = []
    for singular in sorted(inventory, key=str.casefold):
        source = inventory[singular]
        family = primary[singular]
        gate = scene_gate(singular)
        rows.append(
            {
                "singular": singular,
                "plural": str(source["plural"]),
                "vocabulary_ids": list(source["vocabulary_ids"]),
                "primary_scene_family": family,
                "secondary_scene_families": secondary_families(singular, family),
                "pattern_eligibility": pattern_eligibility(singular),
                "scene_gate": gate,
                "child_suitable": singular not in CHILD_UNSUITABLE_NOUNS,
                "sense_check_required": (
                    gate == "SENSE_CHECK_REQUIRED"
                    or singular in SENSE_CHECK_EXTRA_NOUNS
                ),
                "notes": notes_for(singular, gate),
            }
        )
    if len(rows) != EXPECTED_NOUN_COUNT:
        raise Unit02SceneCoverageBuildError(f"ROW_COUNT_INVALID:{len(rows)}")
    return rows


def rows_by_singular() -> dict[str, dict[str, Any]]:
    return {row["singular"]: row for row in build_rows()}


def payload() -> dict[str, Any]:
    rows = build_rows()
    family_counts = Counter(row["primary_scene_family"] for row in rows)
    gate_counts = Counter(row["scene_gate"] for row in rows)
    eligibility_counts = {
        key: sum(bool(row["pattern_eligibility"][key]) for row in rows)
        for key in PATTERN_ELIGIBILITY_KEYS
    }
    exact_refs = sum(len(row["vocabulary_ids"]) for row in rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "level_scope": LEVEL_SCOPE,
        "source_authority": {
            "task_id": "A1FS-V1-U02QB01_ExactPlainSActiveVocabularyInventory",
            "builder_module": u02qb02.__name__,
            "plain_s_noun_surface_count": EXPECTED_NOUN_COUNT,
            "exact_vocabulary_ref_count": EXPECTED_EXACT_VOCABULARY_REFS,
        },
        "scene_families": list(SCENE_FAMILIES),
        "rows": rows,
        "coverage_denominators": {
            "vocabulary_surface_count": len(rows),
            "exact_vocabulary_ref_count": exact_refs,
            "primary_scene_family_count": len(SCENE_FAMILIES),
            "primary_scene_family_counts": dict(sorted(family_counts.items())),
            "scene_gate_counts": dict(sorted(gate_counts.items())),
            "pattern_eligibility_counts": eligibility_counts,
        },
        "projection_contract": {
            "scene_family_is_pedagogical_projection_not_canonical_scene_identity": True,
            "secondary_family_is_context_eligibility_not_duplicate_primary_assignment": True,
            "morphological_eligibility_does_not_imply_learner_scene_admission": True,
            "sense_check_rows_require_later_semantic_admission": True,
            "unit01_scene_identity_reuse_preferred_before_unit02_scene_creation": True,
            "unit02_new_scene_count_is_coverage_gap_driven_not_preallocated": True,
        },
        "claim_boundaries": {
            "canonical_scene_authority_mutated": False,
            "unit01_scene_authority_mutated": False,
            "vocabulary_authority_mutated": False,
            "chunk_authority_mutated": False,
            "questionbank_mutated": False,
            "learner_runtime_connected": False,
            "new_scene_created": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    value = payload()
    counts = value["coverage_denominators"]
    print(f"STATUS={PASS_STATUS}")
    print(f"VOCABULARY_SURFACES={counts['vocabulary_surface_count']}")
    print(f"SCENE_FAMILIES={counts['primary_scene_family_count']}")
    print(f"SCENE_GATES={counts['scene_gate_counts']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
