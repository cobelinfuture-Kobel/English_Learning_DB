#!/usr/bin/env python3
"""Recalculate the legal Unit01-Unit06 lexical capacity for Unit06 Reading360.

This is a read-only capacity calculator. It does not author learner-facing English.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ulga.builders import build_a1fs_v1_u03q02q04r1_vocabulary_chunk_provenance_recheck as u3

TASK_ID = "A1FS-V1-U06R360R3_U01ToU06ReadingLexicalCapacityRecheck"
STATUS = "PASS_A1FS_V1_U06R360R3_U01_U06_READING_LEXICAL_CAPACITY"
ROOT = Path(__file__).resolve().parents[2]

U02 = ROOT / "ulga/reports/a1fs_v1_u02qb01_exact_plain_s_active_vocabulary_inventory.json"
U04 = ROOT / "ulga/contracts/a1fs_v1_u04_q02_vocabulary_authority.json"
U05 = ROOT / "ulga/contracts/a1fs_v1_u05_q02_vocabulary_carrier_authority.json"
U06Q02 = ROOT / "ulga/contracts/a1fs_v1_u06_q02_vocabulary_carrier_authority.json"
U06Q04R1 = ROOT / "ulga/contracts/a1fs_v1_u06_q04r1_yle_can_ability_chunk_expansion.json"
CURRENT360 = ROOT / "product/a1fs_v1_2_1/data/unit06_current360_360.json"
VOCABULARY = ROOT / "vocabulary/json/vocabulary.json"

NUMBER_CANDIDATES = (
    "one","two","three","four","five","six","seven","eight","nine","ten",
    "eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen",
    "eighteen","nineteen","twenty",
)
EXTRA_IRREGULAR = {"child", "person"}
EXTRA_NONCOUNT = {"homework", "music"}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def admitted_u05(row: dict[str, Any]) -> bool:
    status = str(row.get("unit05_admission_status") or "")
    return status.startswith("ADMITTED") or status.startswith("SUPPORT_")


def canonical_a1_stats() -> dict[str, Any]:
    rows = load(VOCABULARY)
    a1 = [
        row for row in rows
        if str(row.get("level") or "").upper() == "A1"
    ]
    by_pos: dict[str, list[dict[str, Any]]] = {}
    for row in a1:
        by_pos.setdefault(norm(row.get("part_of_speech")), []).append(row)

    def pos_stats(pos: str) -> dict[str, int]:
        subset = by_pos.get(pos, [])
        return {
            "sense_rows": len(subset),
            "unique_base_words": len({norm(row.get("word")) for row in subset if norm(row.get("word"))}),
        }

    words = {norm(row.get("word")) for row in a1 if norm(row.get("word"))}
    return {
        "sense_rows": len(a1),
        "unique_base_words": len(words),
        "noun": pos_stats("noun"),
        "verb": pos_stats("verb"),
        "adjective": pos_stats("adjective"),
        "number_words": [n for n in NUMBER_CANDIDATES if n in words],
    }


def build_report() -> dict[str, Any]:
    u02 = load(U02)
    u04 = load(U04)
    u05 = load(U05)
    u06 = load(U06Q02)
    q04 = load(U06Q04R1)
    current = load(CURRENT360)

    u01_active = {norm(row["singular"]) for row in u02["inventory"]}
    regular = set(u01_active)
    irregular = set()

    for cls, values in u02["excluded_non_plain_s"].items():
        for value in values:
            surface = norm(value)
            u01_active.add(surface)
            if cls == "IRREGULAR_PLURAL":
                irregular.add(surface)
            else:
                regular.add(surface)

    u3rows = u3.q2_rows()
    u3_nouns = {norm(r["word"]) for r in u3rows if norm(r["part_of_speech"]) == "noun"}

    places = {
        norm(surface)
        for surfaces in u04["life_skill_place_carrier_pool"]["domains"].values()
        for surface in surfaces
    }

    admitted5 = [row for row in u05["matrix"] if admitted_u05(row)]
    objects = {norm(row["surface"]) for row in admitted5 if row["carrier_class"] == "NOUN"}
    u5_places = {norm(row["surface"]) for row in admitted5 if row["carrier_class"] == "PLACE"}
    persons = {
        norm(row["surface"])
        for row in admitted5
        if row["carrier_class"] in {"PERSON", "ROLE"}
    }

    nounlike = set().union(u01_active, u3_nouns, places, objects, u5_places, persons)
    extras = nounlike - u01_active
    for surface in extras:
        if surface in EXTRA_IRREGULAR:
            irregular.add(surface)
        elif surface not in EXTRA_NONCOUNT:
            regular.add(surface)

    irregular &= nounlike
    noncount = EXTRA_NONCOUNT & nounlike
    regular_allowed = nounlike - irregular - noncount

    u3_adjectives = {
        norm(r["word"]) for r in u3rows if norm(r["part_of_speech"]) == "adjective"
    }
    u5_adjectives = {
        norm(row["surface"])
        for row in admitted5
        if row["carrier_class"] in {"ADJECTIVE", "AGE_STATE"}
    }
    u6_adjectives = {
        norm(row["surface"])
        for row in u06["matrix"]
        if row["carrier_class"] == "MANNER_OR_SUPPORT"
        and str(row.get("unit06_admission_status") or "").startswith("ADMITTED")
    }
    direct_adjectives = u3_adjectives | u5_adjectives | u6_adjectives

    direct_actions = {
        norm(x)
        for x in q04["canonical_vocabulary_bridge"]["admitted_single_word_verbs"]
    }

    corpus = " ".join(str(e.get("paragraph") or "") for e in current["episodes"]).casefold()
    direct_numbers = [
        n for n in NUMBER_CANDIDATES
        if re.search(rf"\b{re.escape(n)}\b", corpus)
    ]

    a1 = canonical_a1_stats()

    report = {
        "schema_version": "a1fs.v1.u06.reading360.lexical_capacity.u01_u06.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "scope": {
            "unit_range": "U01-U06",
            "reading360_full_materialized": False,
            "writing360_modified": False,
            "spoken360_modified": False,
            "pattern360_modified": False,
            "grammar_ceiling": "UNIT01_TO_UNIT06_ONLY",
            "irregular_plural_unlocked": False,
            "a2_a2plus_grammar_unlocked": False,
        },
        "counting_policy": {
            "direct_legal_now": "Existing U01-U06 authority/admission or accepted learner-facing evidence.",
            "a1_candidate_ceiling": "Canonical A1 reference pool; active status and direct-use admission are not implied.",
            "noun_like": "Unique lexical surfaces with cumulative noun authority; semantic subtypes are subsets and must not be summed.",
            "regular_plural": "Project regular spelling classes are allowed; irregular plural forms remain blocked while singular lexemes remain available.",
            "number": "Only number surfaces evidenced in accepted U06 learner-facing reader are DIRECT_PROVEN; remaining active A1 number words are candidates only.",
        },
        "direct_legal_now": {
            "noun_like": {
                "unique_surface_count": len(nounlike),
                "surfaces": sorted(nounlike),
                "regular_plural_allowed_count": len(regular_allowed),
                "regular_plural_allowed_surfaces": sorted(regular_allowed),
                "singular_only_irregular_plural_count": len(irregular),
                "singular_only_irregular_plural_surfaces": sorted(irregular),
                "singular_only_noncount_count": len(noncount),
                "singular_only_noncount_surfaces": sorted(noncount),
            },
            "object_carrier_subset": {
                "count": len(objects),
                "surfaces": sorted(objects),
                "all_regular_plural_allowed": objects <= regular_allowed,
            },
            "place_carrier_subset": {
                "count": len(u5_places),
                "surfaces": sorted(u5_places),
                "all_regular_plural_allowed": u5_places <= regular_allowed,
            },
            "person_role_carrier_subset": {
                "count": len(persons),
                "surfaces": sorted(persons),
                "irregular_plural_singular_only": sorted(persons & irregular),
                "regular_plural_allowed": sorted(persons & regular_allowed),
            },
            "adjective_surfaces": {
                "count": len(direct_adjectives),
                "surfaces": sorted(direct_adjectives),
            },
            "ability_action_verb_surfaces": {
                "count": len(direct_actions),
                "surfaces": sorted(direct_actions),
            },
            "number_surfaces_direct_proven": {
                "count": len(direct_numbers),
                "surfaces": direct_numbers,
                "evidence": "unit06_current360_360 learner-facing paragraphs",
            },
        },
        "a1_candidate_ceiling": {
            "canonical_source": "vocabulary/json/vocabulary.json",
            "sense_rows": a1["sense_rows"],
            "unique_base_words": a1["unique_base_words"],
            "noun": a1["noun"],
            "verb": a1["verb"],
            "adjective": a1["adjective"],
            "number_words": {
                "count": len(a1["number_words"]),
                "surfaces": a1["number_words"],
            },
            "rule": "Candidate ceiling requires downstream semantic and pedagogical admission; it is not a claim that every A1 word is already taught.",
        },
        "yle_evidence": {
            "unit04_yle_place_extensions": {
                "count": u04["life_skill_place_carrier_pool"]["yle_active_eligible_extension_count"],
                "surfaces": sorted(
                    norm(x["surface"])
                    for x in u04["life_skill_place_carrier_pool"]["provenance"]["yle_active_eligible_extensions"]
                ),
            },
            "unit06_q04r1": {
                "official_starters_movers_source_entries_recovered": q04["acceptance"]["official_starters_movers_source_entries_recovered"],
                "direct_ability_source_entries": q04["acceptance"]["direct_ability_source_entries"],
                "contextual_ability_only_source_entries": q04["acceptance"]["contextual_ability_only_source_entries"],
                "admitted_single_word_ability_verbs": q04["acceptance"]["admitted_single_word_ability_verbs"],
                "deferred_single_word_ability_candidates": q04["acceptance"]["deferred_single_word_ability_candidates"],
                "flyers_entries_admitted": q04["acceptance"]["flyers_entries_admitted"],
            },
        },
    }
    validate(report)
    return report


def validate(report: dict[str, Any]) -> None:
    direct = report["direct_legal_now"]
    assert direct["noun_like"]["unique_surface_count"] == 202
    assert direct["noun_like"]["regular_plural_allowed_count"] == 192
    assert direct["noun_like"]["singular_only_irregular_plural_count"] == 8
    assert direct["noun_like"]["singular_only_noncount_count"] == 2
    assert direct["noun_like"]["singular_only_irregular_plural_surfaces"] == [
        "child","fish","foot","man","person","sheep","tooth","woman"
    ]
    assert direct["noun_like"]["singular_only_noncount_surfaces"] == ["homework","music"]
    assert direct["object_carrier_subset"]["count"] == 25
    assert direct["object_carrier_subset"]["all_regular_plural_allowed"] is True
    assert direct["place_carrier_subset"]["count"] == 29
    assert direct["place_carrier_subset"]["all_regular_plural_allowed"] is True
    assert direct["person_role_carrier_subset"]["count"] == 17
    assert len(direct["person_role_carrier_subset"]["regular_plural_allowed"]) == 13
    assert direct["person_role_carrier_subset"]["irregular_plural_singular_only"] == [
        "child","man","person","woman"
    ]
    assert direct["adjective_surfaces"]["count"] == 25
    assert direct["ability_action_verb_surfaces"]["count"] == 60
    assert direct["number_surfaces_direct_proven"]["surfaces"] == ["one","two","three"]

    a1 = report["a1_candidate_ceiling"]
    assert a1["sense_rows"] == 784
    assert a1["unique_base_words"] == 643
    assert a1["noun"] == {"sense_rows": 322, "unique_base_words": 304}
    assert a1["verb"] == {"sense_rows": 107, "unique_base_words": 85}
    assert a1["adjective"] == {"sense_rows": 93, "unique_base_words": 76}
    assert a1["number_words"]["count"] == 20
    assert a1["number_words"]["surfaces"] == list(NUMBER_CANDIDATES)

    yle = report["yle_evidence"]
    assert yle["unit04_yle_place_extensions"]["count"] == 5
    assert yle["unit06_q04r1"]["official_starters_movers_source_entries_recovered"] == "142/142"
    assert yle["unit06_q04r1"]["admitted_single_word_ability_verbs"] == 60
    assert yle["unit06_q04r1"]["flyers_entries_admitted"] == 0


def main() -> int:
    report = build_report()
    print(f"STATUS={report['status']}")
    print(f"NOUN_LIKE={report['direct_legal_now']['noun_like']['unique_surface_count']}")
    print(f"REGULAR_PLURAL_ALLOWED={report['direct_legal_now']['noun_like']['regular_plural_allowed_count']}")
    print(f"SINGULAR_ONLY_IRREGULAR={report['direct_legal_now']['noun_like']['singular_only_irregular_plural_count']}")
    print(f"SINGULAR_ONLY_NONCOUNT={report['direct_legal_now']['noun_like']['singular_only_noncount_count']}")
    print(f"OBJECTS={report['direct_legal_now']['object_carrier_subset']['count']}")
    print(f"PLACES={report['direct_legal_now']['place_carrier_subset']['count']}")
    print(f"PERSON_ROLE={report['direct_legal_now']['person_role_carrier_subset']['count']}")
    print(f"ADJECTIVES={report['direct_legal_now']['adjective_surfaces']['count']}")
    print(f"ACTIONS={report['direct_legal_now']['ability_action_verb_surfaces']['count']}")
    print(f"NUMBERS={report['direct_legal_now']['number_surfaces_direct_proven']['count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
