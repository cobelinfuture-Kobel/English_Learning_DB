#!/usr/bin/env python3
"""Unit06 Reading360 R3 pilot15 validator.

Learner-facing English is GPT-5.6 Sol authored.
Python validates only; it does not generate or rewrite learner-facing text.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-U06R360R3_Reading360Pilot15_KETFlyersLoweredRealLife"
STATUS = "PASS_A1FS_V1_U06R360R3_READING360_PILOT15"
ROOT = Path(__file__).resolve().parents[2]
PILOT_PATH = ROOT / "product/a1fs_v1_2_1/data/u06_reading360_r3_pilot15.json"
CURRENT360_PATH = ROOT / "product/a1fs_v1_2_1/data/unit06_current360_360.json"

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
            r"\b(?:has|does|goes|comes|puts|looks|enters|carries|likes|wants|needs|makes|"
            r"reads|writes|sits|stands|helps|plays|sings|runs|walks|eats|drinks|washes|"
            r"closes|opens|moves|finds|sees|talks|waits|works|studies|takes|throws|"
            r"catches|kicks|rides|swims|climbs|flies|paints|draws|gives|calls|emails|"
            r"phones|texts|says|tells|spells|answers|asks|teaches|understands|brings|"
            r"builds|cleans|cooks|dries|changes|listens|shows|holds|points|sends|uses)\b",
            re.I,
        ),
        "LEXICAL_PRESENT_SIMPLE_3SG",
    ),
)

EXPECTED_FAMILIES = {
    "PERSONAL_MESSAGE",
    "MINI_EMAIL",
    "SCHOOL_NOTICE",
    "EVENT_INFORMATION",
    "SHORT_PROFILE",
    "PICTURE_LINKED_DESCRIPTION",
    "MAP_ROUTE_INFORMATION",
    "DAILY_LIFE_NOTE",
    "CLASS_INFORMATION",
    "SHORT_FACTUAL_TEXT",
    "TWO_PERSON_INFORMATION",
    "FAMILY_PLAN",
    "SPORTS_ACTIVITY_INFORMATION",
    "SIMPLE_CONNECTED_STORY",
    "PROBLEM_SOLUTION",
}


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

    if pilot.get("task_id") != TASK_ID:
        raise U06ReadingPilotError("TASK_ID_DRIFT")
    if pilot.get("learner_facing_language_author") != "GPT-5.6 Sol":
        raise U06ReadingPilotError("AUTHOR_DRIFT")

    scope = pilot.get("scope") or {}
    expected_scope = {
        "pilot_entry_count": 15,
        "full360_materialized": False,
        "writing360_modified": False,
        "spoken360_modified": False,
        "pattern360_modified": False,
        "unit01_to_unit06_grammar_ceiling": True,
        "ket_flyers_use": "LOWERED_TEXT_TYPE_AND_READING_PURPOSE_ONLY",
        "ielts_inspired_use": "REAL_LIFE_CONTEXT_AND_COMMUNICATIVE_PURPOSE_ONLY",
        "a2_a2plus_unlocked": False,
    }
    for key, expected in expected_scope.items():
        if scope.get(key) != expected:
            raise U06ReadingPilotError(f"SCOPE_DRIFT:{key}:{scope.get(key)}:{expected}")

    source_rows = {
        str(row["episode_id"]): row for row in (current.get("episodes") or [])
    }
    entries = list(pilot.get("entries") or [])
    if len(entries) != 15:
        raise U06ReadingPilotError(f"ENTRY_COUNT_DRIFT:{len(entries)}")

    families = [str(e.get("family_id") or "") for e in entries]
    if set(families) != EXPECTED_FAMILIES or len(set(families)) != 15:
        raise U06ReadingPilotError("FAMILY_COVERAGE_DRIFT")

    source_ids: set[str] = set()
    pilot_ids: set[str] = set()
    sentence_counts: list[int] = []
    text_keys: set[str] = set()
    shell_forms: set[tuple[Any, ...]] = set()

    for index, entry in enumerate(entries, start=1):
        expected_pilot_id = f"U06-R360R3-P{index:02d}"
        if entry.get("pilot_id") != expected_pilot_id:
            raise U06ReadingPilotError(
                f"PILOT_ID_ORDER_DRIFT:{entry.get('pilot_id')}:{expected_pilot_id}"
            )
        if expected_pilot_id in pilot_ids:
            raise U06ReadingPilotError(f"PILOT_ID_COLLISION:{expected_pilot_id}")
        pilot_ids.add(expected_pilot_id)

        source_id = str(entry.get("source_episode_id") or "")
        if source_id in source_ids:
            raise U06ReadingPilotError(f"SOURCE_REUSE_IN_PILOT:{source_id}")
        source_ids.add(source_id)
        source = source_rows.get(source_id)
        if source is None:
            raise U06ReadingPilotError(f"SOURCE_MISSING:{source_id}")
        if entry.get("source_episode_slot_id") != source.get("episode_slot_id"):
            raise U06ReadingPilotError(f"SOURCE_SLOT_DRIFT:{expected_pilot_id}")
        if list(entry.get("target_chunk_surfaces") or []) != list(
            source.get("target_chunk_surfaces") or []
        ):
            raise U06ReadingPilotError(f"TARGET_LINEAGE_DRIFT:{expected_pilot_id}")

        sentences = [str(x).strip() for x in (entry.get("body_sentences") or [])]
        if not 6 <= len(sentences) <= 8:
            raise U06ReadingPilotError(
                f"SENTENCE_RANGE_FAIL:{expected_pilot_id}:{len(sentences)}"
            )
        sentence_counts.append(len(sentences))
        text = " ".join(sentences)
        text_key = _norm(text)
        if text_key in text_keys:
            raise U06ReadingPilotError(f"TEXT_DUPLICATE:{expected_pilot_id}")
        text_keys.add(text_key)

        for regex, label in FORBIDDEN:
            if regex.search(text):
                raise U06ReadingPilotError(
                    f"{label}_LEAKAGE:{expected_pilot_id}:{regex.findall(text)[:4]}"
                )
        for target in entry.get("target_chunk_surfaces") or []:
            if _norm(target) not in _norm(text):
                raise U06ReadingPilotError(
                    f"TARGET_NOT_REALIZED:{expected_pilot_id}:{target}"
                )

        purpose = str(entry.get("reading_purpose") or "").strip()
        if not purpose:
            raise U06ReadingPilotError(f"READING_PURPOSE_MISSING:{expected_pilot_id}")
        shell = entry.get("display_shell") or {}
        shell_forms.add(
            (
                bool(shell.get("greeting")),
                bool(shell.get("title")),
                bool(shell.get("signoff")),
                str(shell.get("label") or ""),
            )
        )

    distribution = dict(sorted(Counter(sentence_counts).items()))
    if distribution != {6: 5, 7: 5, 8: 5}:
        raise U06ReadingPilotError(f"SENTENCE_DISTRIBUTION_DRIFT:{distribution}")
    if len(shell_forms) < 10:
        raise U06ReadingPilotError(f"FORMAT_SHELL_DIVERSITY_TOO_LOW:{len(shell_forms)}")

    return {
        "schema_version": "a1fs.v1.u06.reading360.r3.pilot15.validation.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "entry_count": 15,
        "family_count": 15,
        "family_coverage": "15/15",
        "unique_source_episode_count": 15,
        "unique_text_count": 15,
        "sentence_distribution": distribution,
        "sentence_min": min(sentence_counts),
        "sentence_max": max(sentence_counts),
        "format_shell_variant_count": len(shell_forms),
        "unit01_to_unit06_grammar_ceiling": True,
        "target_lineage_exact": True,
        "ket_flyers_lowered_text_type_policy": True,
        "ielts_inspired_real_life_policy": True,
        "full360_materialized": False,
        "writing360_modified": False,
        "spoken360_modified": False,
        "pattern360_modified": False,
        "a2_a2plus_unlocked": False,
        "human_review_required": True,
    }


def main() -> int:
    report = build_report()
    for key in (
        "status",
        "entry_count",
        "family_coverage",
        "sentence_distribution",
        "format_shell_variant_count",
    ):
        print(f"{key.upper()}={report[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
