#!/usr/bin/env python3
"""Unit06 Reading360 R3 Pilot15 R2 lexical-diversity validator.

Learner-facing English is GPT-5.6 Sol authored. Python validates only.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-U06R360R3_Reading360Pilot15R2_LexicalDiversityRepair"
STATUS = "PASS_A1FS_V1_U06R360R3_READING360_PILOT15_R2_LEXICAL_DIVERSITY"
ROOT = Path(__file__).resolve().parents[2]
PILOT_PATH = ROOT / "product/a1fs_v1_2_1/data/u06_reading360_r3_pilot15.json"
CURRENT360_PATH = ROOT / "product/a1fs_v1_2_1/data/unit06_current360_360.json"
Q02_PATH = ROOT / "ulga/contracts/a1fs_v1_u06_q02_vocabulary_carrier_authority.json"

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


def build_report() -> dict[str, Any]:
    pilot = _load(PILOT_PATH)
    current = _load(CURRENT360_PATH)
    q02 = _load(Q02_PATH)

    if pilot.get("task_id") != TASK_ID:
        raise U06ReadingPilotError("TASK_ID_DRIFT")
    if pilot.get("learner_facing_language_author") != "GPT-5.6 Sol":
        raise U06ReadingPilotError("AUTHOR_DRIFT")

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

    q02_objects = {
        _norm(row["surface"]) for row in q02.get("matrix", [])
        if row.get("carrier_class") == "OBJECT"
    }
    q02_places = {
        _norm(row["surface"]) for row in q02.get("matrix", [])
        if row.get("carrier_class") == "PLACE"
    }
    current_rows = {
        str(row["episode_id"]): row for row in current.get("episodes", [])
    }

    entries = list(pilot.get("entries") or [])
    if len(entries) != 15:
        raise U06ReadingPilotError(f"ENTRY_COUNT_DRIFT:{len(entries)}")
    if {str(e.get("family_id")) for e in entries} != EXPECTED_FAMILIES:
        raise U06ReadingPilotError("FAMILY_COVERAGE_DRIFT")

    sentence_counts: list[int] = []
    source_ids: set[str] = set()
    primary_objects: list[str] = []
    primary_places: list[str] = []
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

        lp = entry.get("lexical_profile") or {}
        place = _norm(lp.get("primary_place") or "")
        if place not in q02_places:
            raise U06ReadingPilotError(f"PRIMARY_PLACE_NOT_Q02:{pid}:{place}")
        primary_places.append(place)

        primary_object = lp.get("primary_object")
        authority = str(lp.get("primary_object_authority") or "")
        if primary_object is not None:
            pobj = _norm(primary_object)
            if authority == "Q02_OBJECT" and pobj not in q02_objects:
                raise U06ReadingPilotError(f"PRIMARY_OBJECT_NOT_Q02:{pid}:{pobj}")
            if authority == "SOURCE_EPISODE_SUPPORT" and pobj not in _norm(source.get("paragraph") or ""):
                raise U06ReadingPilotError(f"SOURCE_SUPPORT_OBJECT_NOT_IN_SOURCE:{pid}:{pobj}")
            if authority not in {"Q02_OBJECT","SOURCE_EPISODE_SUPPORT"}:
                raise U06ReadingPilotError(f"PRIMARY_OBJECT_AUTHORITY_INVALID:{pid}:{authority}")
            primary_objects.append(pobj)
        elif authority != "NONE_REQUIRED":
            raise U06ReadingPilotError(f"NULL_PRIMARY_OBJECT_AUTHORITY_INVALID:{pid}")

        supporting = tuple(sorted(_norm(x) for x in lp.get("supporting_objects") or []))
        for obj in supporting:
            if obj not in q02_objects:
                raise U06ReadingPilotError(f"SUPPORTING_OBJECT_NOT_Q02:{pid}:{obj}")
        bundle_key = (_norm(primary_object or "NONE"), supporting)
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
    if distribution != {6:5, 7:5, 8:5}:
        raise U06ReadingPilotError(f"SENTENCE_DISTRIBUTION_DRIFT:{distribution}")
    if len(set(primary_objects)) < 13:
        raise U06ReadingPilotError(f"PRIMARY_OBJECT_DIVERSITY_TOO_LOW:{len(set(primary_objects))}")
    if len(primary_objects) != len(set(primary_objects)):
        raise U06ReadingPilotError("PRIMARY_OBJECT_REPEAT_IN_PILOT")
    if len(set(primary_places)) < 10:
        raise U06ReadingPilotError(f"PRIMARY_PLACE_DIVERSITY_TOO_LOW:{len(set(primary_places))}")
    if number_entry_count != 5:
        raise U06ReadingPilotError(f"NUMBER_ENTRY_COUNT_DRIFT:{number_entry_count}")
    if any(v > 2 for v in number_counts.values()):
        raise U06ReadingPilotError(f"NUMBER_SURFACE_DOMINANCE:{dict(number_counts)}")

    return {
        "schema_version":"a1fs.v1.u06.reading360.r3.pilot15.validation.v2",
        "task_id":TASK_ID,
        "status":STATUS,
        "entry_count":15,
        "family_count":15,
        "unique_source_episode_count":15,
        "sentence_distribution":distribution,
        "unique_primary_object_count":len(set(primary_objects)),
        "unique_primary_place_count":len(set(primary_places)),
        "number_bearing_entry_count":number_entry_count,
        "number_surface_counts":dict(sorted(number_counts.items())),
        "declared_regular_plural_surfaces":sorted(declared_plurals),
        "irregular_plural_count":0,
        "object_bundle_duplicate_count":0,
        "unit01_to_unit06_grammar_ceiling":True,
        "target_lineage_exact":True,
        "full360_materialized":False,
        "writing360_modified":False,
        "spoken360_modified":False,
        "pattern360_modified":False,
        "a2_a2plus_unlocked":False,
        "human_review_required":True,
    }


if __name__ == "__main__":
    r = build_report()
    for k in (
        "status","entry_count","sentence_distribution","unique_primary_object_count",
        "unique_primary_place_count","number_surface_counts","declared_regular_plural_surfaces"
    ):
        print(f"{k.upper()}={r[k]}")
