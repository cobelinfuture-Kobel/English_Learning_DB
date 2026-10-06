#!/usr/bin/env python3
"""Unit06 Reading360 R3 Pilot15 lexical rebalance validator.

Learner-facing English is GPT-5.6 Sol authored. Python validates lineage,
lexical authority, concentration, sentence density and frozen grammar scope.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-U06R360R3_Pilot15LexicalRebalanceMinimalRepairAndHumanReview"
STATUS = "PASS_A1FS_V1_U06R360R3_PILOT15_LEXICAL_REBALANCE_HUMAN_REVIEW"
ROOT = Path(__file__).resolve().parents[2]
PILOT_PATH = ROOT / "product/a1fs_v1_2_1/data/u06_reading360_r3_pilot15.json"
CURRENT360_PATH = ROOT / "product/a1fs_v1_2_1/data/unit06_current360_360.json"
CAPACITY_PATH = ROOT / "product/a1fs_v1_2_1/data/u06_reading360_u01_u06_lexical_capacity.json"

EXPECTED_FAMILIES = {
    "PERSONAL_MESSAGE","MINI_EMAIL","SCHOOL_NOTICE","EVENT_INFORMATION",
    "SHORT_PROFILE","PICTURE_LINKED_DESCRIPTION","MAP_ROUTE_INFORMATION",
    "DAILY_LIFE_NOTE","CLASS_INFORMATION","SHORT_FACTUAL_TEXT",
    "TWO_PERSON_INFORMATION","FAMILY_PLAN","SPORTS_ACTIVITY_INFORMATION",
    "SIMPLE_CONNECTED_STORY","PROBLEM_SOLUTION",
}
ALLOWED_NUMBERS = {"one","two","three"}
ALLOWED_REGULAR_PLURALS = {
    "balls","shoes","hands","students","cups","cards","numbers","tasks","books"
}
FORBIDDEN_IRREGULAR_OR_NONREGULAR_PLURALS = {
    "children","men","women","people","feet","teeth","mice","geese",
    "clothes","trousers","pants","shorts",
}
FORBIDDEN = (
    (re.compile(r"\?"), "QUESTION"),
    (re.compile(r"\b(?:cannot|can\s+not|can't)\b", re.I), "CAN_NEGATIVE"),
    (re.compile(r"\bthere\s+(?:is|are)\b", re.I), "THERE_BE"),
    (re.compile(r"\b(?:was|were)\b", re.I), "PAST_BE"),
    (re.compile(r"\b(?:am|is|are)\s+[A-Za-z]+ing\b", re.I), "PRESENT_CONTINUOUS"),
    (re.compile(r"\b(?:after|before|without|by)\s+[A-Za-z]+ing\b", re.I), "GERUND_LINK"),
    (re.compile(r"\bcan\s+(?:be|have)\b", re.I), "NONABILITY_CAN_RISK"),
    (
        re.compile(
            r"\b(?:has|does|goes|comes|puts|looks|enters|carries|likes|wants|needs|"
            r"makes|reads|writes|sits|stands|helps|plays|sings|runs|walks|eats|"
            r"drinks|washes|closes|opens|moves|finds|sees|talks|waits|works|"
            r"studies|takes|throws|catches|kicks|rides|swims|climbs|flies|paints|"
            r"draws|gives|calls|emails|phones|texts|says|tells|spells|answers|asks|"
            r"teaches|understands|brings|builds|cleans|cooks|dries|changes|listens|"
            r"shows|holds|points|sends|uses)\b",
            re.I,
        ),
        "LEXICAL_PRESENT_SIMPLE_3SG",
    ),
)


class U06ReadingPilotError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U06ReadingPilotError(f"NOT_OBJECT:{path}")
    return value


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def _regular_plural(surface: str) -> str | None:
    if " " in surface:
        return None
    if re.search(r"[^aeiou]y$", surface, re.I):
        return surface[:-1] + "ies"
    if re.search(r"(?:s|x|z|ch|sh)$", surface, re.I):
        return surface + "es"
    return surface + "s"


def _occurrence_count(text: str, surface: str, allow_regular_plural: bool = False) -> int:
    forms = [surface]
    if allow_regular_plural:
        plural = _regular_plural(surface)
        if plural:
            forms.append(plural)
    body = "|".join(re.escape(x) for x in forms)
    return len(re.findall(rf"(?<![A-Za-z])(?:{body})(?![A-Za-z])", text, re.I))


def _category_counts(entries: list[dict[str, Any]], surfaces: set[str], allow_regular_plural: bool) -> Counter[str]:
    counts: Counter[str] = Counter()
    for entry in entries:
        text = " ".join(str(x) for x in entry.get("body_sentences") or [])
        for surface in surfaces:
            n = _occurrence_count(text, surface, allow_regular_plural)
            if n:
                counts[surface] += n
    return counts


def build_report() -> dict[str, Any]:
    pilot = _load(PILOT_PATH)
    current = _load(CURRENT360_PATH)
    capacity = _load(CAPACITY_PATH)

    if pilot.get("task_id") != TASK_ID:
        raise U06ReadingPilotError("TASK_ID_DRIFT")
    if pilot.get("status") != "PASS_PILOT15_HUMAN_REVIEW_R2_NATURALIZED":
        raise U06ReadingPilotError("PILOT_STATUS_DRIFT")
    if pilot.get("learner_facing_language_author") != "GPT-5.6 Sol":
        raise U06ReadingPilotError("AUTHOR_DRIFT")

    human = pilot.get("human_review") or {}
    if human.get("status") != "PASS" or human.get("reviewed_entry_count") != 15:
        raise U06ReadingPilotError("HUMAN_REVIEW_NOT_PASS")

    scope = pilot.get("scope") or {}
    for key, expected in {
        "pilot_entry_count":15,
        "full360_materialized":False,
        "writing360_modified":False,
        "spoken360_modified":False,
        "pattern360_modified":False,
        "unit01_to_unit06_grammar_ceiling":True,
        "regular_plural_only":True,
        "irregular_plural_unlocked":False,
        "a2_a2plus_unlocked":False,
    }.items():
        if scope.get(key) != expected:
            raise U06ReadingPilotError(f"SCOPE_DRIFT:{key}:{scope.get(key)}:{expected}")

    direct = capacity.get("direct_legal_now") or {}
    object_surfaces = {_norm(x) for x in direct["object_carrier_subset"]["surfaces"]}
    place_surfaces = {_norm(x) for x in direct["place_carrier_subset"]["surfaces"]}
    person_surfaces = {_norm(x) for x in direct["person_role_carrier_subset"]["surfaces"]}
    adjective_surfaces = {_norm(x) for x in direct["adjective_surfaces"]["surfaces"]}
    action_surfaces = {_norm(x) for x in direct["ability_action_verb_surfaces"]["surfaces"]}
    noun_surfaces = {_norm(x) for x in direct["noun_like"]["surfaces"]}

    current_rows = {str(row["episode_id"]): row for row in current.get("episodes", [])}
    entries = list(pilot.get("entries") or [])
    if len(entries) != 15:
        raise U06ReadingPilotError(f"ENTRY_COUNT_DRIFT:{len(entries)}")
    if {str(e.get("family_id")) for e in entries} != EXPECTED_FAMILIES:
        raise U06ReadingPilotError("FAMILY_COVERAGE_DRIFT")

    sentence_counts: list[int] = []
    source_ids: set[str] = set()
    primary_objects: list[str] = []
    primary_places: list[str] = []
    direct_object_episode_presence: Counter[str] = Counter()
    number_counts: Counter[str] = Counter()
    number_entry_count = 0
    declared_plurals: set[str] = set()
    text_keys: set[str] = set()
    object_bundle_keys: set[tuple[str, tuple[str, ...]]] = set()

    for index, entry in enumerate(entries, start=1):
        pid = f"U06-R360R3-P{index:02d}"
        if entry.get("pilot_id") != pid:
            raise U06ReadingPilotError(f"PILOT_ID_ORDER_DRIFT:{entry.get('pilot_id')}:{pid}")

        source_id = str(entry.get("source_episode_id") or "")
        if source_id in source_ids:
            raise U06ReadingPilotError(f"SOURCE_REUSE:{source_id}")
        source_ids.add(source_id)
        source = current_rows.get(source_id)
        if source is None:
            raise U06ReadingPilotError(f"SOURCE_MISSING:{source_id}")
        if entry.get("source_episode_slot_id") != source.get("episode_slot_id"):
            raise U06ReadingPilotError(f"SOURCE_SLOT_DRIFT:{pid}")
        if list(entry.get("target_chunk_surfaces") or []) != list(source.get("target_chunk_surfaces") or []):
            raise U06ReadingPilotError(f"TARGET_LINEAGE_DRIFT:{pid}")

        sentences = [str(x).strip() for x in entry.get("body_sentences") or []]
        if not 6 <= len(sentences) <= 8:
            raise U06ReadingPilotError(f"SENTENCE_RANGE_FAIL:{pid}:{len(sentences)}")
        sentence_counts.append(len(sentences))
        text = " ".join(sentences)
        norm_text = _norm(text)
        if norm_text in text_keys:
            raise U06ReadingPilotError(f"TEXT_DUPLICATE:{pid}")
        text_keys.add(norm_text)

        for regex, label in FORBIDDEN:
            if regex.search(text):
                raise U06ReadingPilotError(f"{label}_LEAKAGE:{pid}:{regex.findall(text)[:4]}")
        for form in FORBIDDEN_IRREGULAR_OR_NONREGULAR_PLURALS:
            if re.search(rf"\b{re.escape(form)}\b", text, re.I):
                raise U06ReadingPilotError(f"IRREGULAR_OR_NONREGULAR_PLURAL:{pid}:{form}")
        for target in entry.get("target_chunk_surfaces") or []:
            if _norm(target) not in norm_text:
                raise U06ReadingPilotError(f"TARGET_NOT_REALIZED:{pid}:{target}")

        for obj in object_surfaces:
            if _occurrence_count(text, obj, True):
                direct_object_episode_presence[obj] += 1

        lp = entry.get("lexical_profile") or {}
        place = _norm(lp.get("primary_place") or "")
        if place not in place_surfaces:
            raise U06ReadingPilotError(f"PRIMARY_PLACE_NOT_DIRECT_LEGAL:{pid}:{place}")
        primary_places.append(place)

        primary_object = lp.get("primary_object")
        authority = str(lp.get("primary_object_authority") or "")
        if primary_object is not None:
            pobj = _norm(primary_object)
            if pobj not in object_surfaces:
                raise U06ReadingPilotError(f"PRIMARY_OBJECT_NOT_DIRECT_LEGAL:{pid}:{pobj}")
            if authority != "Q02_OBJECT":
                raise U06ReadingPilotError(f"PRIMARY_OBJECT_AUTHORITY_NOT_DIRECT:{pid}:{authority}")
            if _occurrence_count(text, pobj, True) == 0:
                raise U06ReadingPilotError(f"PRIMARY_OBJECT_NOT_REALIZED:{pid}:{pobj}")
            primary_objects.append(pobj)
        elif authority != "NONE_REQUIRED":
            raise U06ReadingPilotError(f"NULL_PRIMARY_OBJECT_AUTHORITY_INVALID:{pid}")

        supporting = tuple(sorted(_norm(x) for x in lp.get("supporting_objects") or []))
        for obj in supporting:
            if obj not in object_surfaces:
                raise U06ReadingPilotError(f"SUPPORTING_OBJECT_NOT_DIRECT_LEGAL:{pid}:{obj}")
            if _occurrence_count(text, obj, True) == 0:
                raise U06ReadingPilotError(f"SUPPORTING_OBJECT_NOT_REALIZED:{pid}:{obj}")
        if primary_object is not None:
            bundle_key = (_norm(primary_object), supporting)
            if bundle_key in object_bundle_keys:
                raise U06ReadingPilotError(f"OBJECT_BUNDLE_DUPLICATE:{pid}:{bundle_key}")
            object_bundle_keys.add(bundle_key)

        numbers = [_norm(x) for x in lp.get("number_surfaces") or []]
        if numbers:
            number_entry_count += 1
        for number in numbers:
            if number not in ALLOWED_NUMBERS:
                raise U06ReadingPilotError(f"NUMBER_NOT_ALLOWED:{pid}:{number}")
            if not re.search(rf"\b{re.escape(number)}\b", text, re.I):
                raise U06ReadingPilotError(f"DECLARED_NUMBER_NOT_IN_TEXT:{pid}:{number}")
            number_counts[number] += 1

        plurals = {_norm(x) for x in lp.get("plural_surfaces") or []}
        if not plurals <= ALLOWED_REGULAR_PLURALS:
            raise U06ReadingPilotError(f"PLURAL_NOT_REGULAR_ALLOWLIST:{pid}:{sorted(plurals-ALLOWED_REGULAR_PLURALS)}")
        for plural in plurals:
            if not re.search(rf"\b{re.escape(plural)}\b", text, re.I):
                raise U06ReadingPilotError(f"DECLARED_PLURAL_NOT_IN_TEXT:{pid}:{plural}")
        declared_plurals.update(plurals)

    distribution = dict(sorted(Counter(sentence_counts).items()))
    final_sentences = [_norm((entry.get("body_sentences") or [""])[-1]) for entry in entries]
    ready_occurrence_count = sum(
        len(re.findall(r"\bready\b", " ".join(str(x) for x in entry.get("body_sentences") or []), re.I))
        for entry in entries
    )
    ready_closure_count = sum(1 for sentence in final_sentences if re.search(r"\bready\b", sentence, re.I))
    if ready_occurrence_count != 0 or ready_closure_count != 0:
        raise U06ReadingPilotError(f"READY_CLOSURE_CONCENTRATION:{ready_occurrence_count}:{ready_closure_count}")
    if len(set(final_sentences)) != 15:
        raise U06ReadingPilotError(f"FINAL_SENTENCE_DUPLICATE:{len(set(final_sentences))}")

    if distribution != {6:5, 7:5, 8:5}:
        raise U06ReadingPilotError(f"SENTENCE_DISTRIBUTION_DRIFT:{distribution}")
    if len(primary_objects) != 13 or len(set(primary_objects)) != 13:
        raise U06ReadingPilotError(f"PRIMARY_OBJECT_DIVERSITY_DRIFT:{len(primary_objects)}:{len(set(primary_objects))}")
    if len(set(primary_places)) < 10:
        raise U06ReadingPilotError(f"PRIMARY_PLACE_DIVERSITY_TOO_LOW:{len(set(primary_places))}")
    max_object_presence = max(direct_object_episode_presence.values(), default=0)
    if max_object_presence > 2:
        raise U06ReadingPilotError(f"DIRECT_OBJECT_EPISODE_PRESENCE_TOO_HIGH:{max_object_presence}")
    if number_entry_count != 5:
        raise U06ReadingPilotError(f"NUMBER_ENTRY_COUNT_DRIFT:{number_entry_count}")
    if any(v > 2 for v in number_counts.values()):
        raise U06ReadingPilotError(f"NUMBER_SURFACE_DOMINANCE:{dict(number_counts)}")

    person_counts = _category_counts(entries, person_surfaces, True)
    adjective_counts = _category_counts(entries, adjective_surfaces, False)
    action_counts = _category_counts(entries, action_surfaces, False)
    noun_counts = _category_counts(entries, noun_surfaces, True)
    object_counts = _category_counts(entries, object_surfaces, True)
    place_counts = _category_counts(entries, place_surfaces, True)

    person_total = sum(person_counts.values())
    friend_count = person_counts.get("friend", 0)
    friend_share = round(friend_count / person_total, 3) if person_total else 0.0

    if len(person_counts) < 9:
        raise U06ReadingPilotError(f"PERSON_ROLE_BREADTH_TOO_LOW:{len(person_counts)}")
    if friend_count > 6 or friend_share > 0.36:
        raise U06ReadingPilotError(f"FRIEND_DOMINANCE:{friend_count}:{friend_share}")
    if len(adjective_counts) < 10:
        raise U06ReadingPilotError(f"ADJECTIVE_BREADTH_TOO_LOW:{len(adjective_counts)}")
    if len(action_counts) < 18:
        raise U06ReadingPilotError(f"ACTION_BREADTH_REGRESSION:{len(action_counts)}")
    if len(object_counts) < 20:
        raise U06ReadingPilotError(f"OBJECT_BREADTH_REGRESSION:{len(object_counts)}")

    return {
        "schema_version":"a1fs.v1.u06.reading360.r3.pilot15.validation.v3",
        "task_id":TASK_ID,
        "status":STATUS,
        "entry_count":15,
        "family_count":15,
        "unique_source_episode_count":15,
        "sentence_distribution":distribution,
        "unique_primary_object_count":len(set(primary_objects)),
        "unique_primary_place_count":len(set(primary_places)),
        "primary_objects_outside_direct_legal_reservoir":[],
        "direct_object_unique_surface_count":len(object_counts),
        "direct_place_unique_surface_count":len(place_counts),
        "noun_like_unique_surface_count":len(noun_counts),
        "person_role_unique_surface_count":len(person_counts),
        "person_role_total_occurrences":person_total,
        "friend_occurrences":friend_count,
        "friend_occurrence_share":friend_share,
        "adjective_unique_surface_count":len(adjective_counts),
        "action_unique_surface_count":len(action_counts),
        "max_direct_object_episode_presence":max_object_presence,
        "number_bearing_entry_count":number_entry_count,
        "number_surface_counts":dict(sorted(number_counts.items())),
        "declared_regular_plural_surfaces":sorted(declared_plurals),
        "irregular_plural_count":0,
        "object_bundle_duplicate_count":0,
        "unit01_to_unit06_grammar_ceiling":True,
        "target_lineage_exact":True,
        "human_review_pass":True,
        "ready_occurrence_count":ready_occurrence_count,
        "ready_closure_count":ready_closure_count,
        "unique_final_sentence_count":len(set(final_sentences)),
        "exact_final_sentence_duplicate_count":15-len(set(final_sentences)),
        "full360_materialized":False,
        "full360_expansion_allowed":True,
        "writing360_modified":False,
        "spoken360_modified":False,
        "pattern360_modified":False,
        "a2_a2plus_unlocked":False,
    }


if __name__ == "__main__":
    r = build_report()
    for key in (
        "status","entry_count","sentence_distribution","unique_primary_object_count",
        "person_role_unique_surface_count","friend_occurrence_share",
        "adjective_unique_surface_count","action_unique_surface_count",
        "full360_expansion_allowed",
    ):
        print(f"{key.upper()}={r[key]}")
