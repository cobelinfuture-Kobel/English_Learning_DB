#!/usr/bin/env python3
"""Unit06 Reader360 P03: GPT-5.6 Spoken360 dialogue materialization.

Static learner-facing dialogue is authored and semantically reviewed by GPT-5.6 Sol.
Python only loads, joins, counts, validates and reports the corpus.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u06r360p02_current360_gpt56_materialization as p02

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validation-only loader for a static GPT-5.6-authored Unit06 Spoken360 corpus. "
    "Python may load, join, count, deduplicate, and validate learner-facing dialogue, "
    "but may not generate, rewrite, paraphrase, or repair it."
)

TASK_ID = "A1FS-V1-U06R360P03_Spoken360GPT56DialogueMaterialization"
STATUS = "PASS_A1FS_V1_U06R360P03_SPOKEN360_GPT56_INTERACTION_LINK_360"
REVISION = "UNIT06_SPOKEN360_GPT56_AFFIRMATIVE_ABILITY_INTERACTION_LINK_V1"
NEXT_SHORT_STEP = "A1FS-V1-U06R360P04_Pattern360GPT56SentenceFamilyMaterialization"

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATHS = tuple(
    REPO_ROOT / f"product/a1fs_v1_2_1/data/u06r360p03_spoken360_gpt56_e{start:03d}_e{start+59:03d}.json"
    for start in (1, 61, 121, 181, 241, 301)
)

FORBIDDEN_THERE_BE = re.compile(r"\bthere\s+(?:is|are)\b", re.IGNORECASE)
FORBIDDEN_PAST_BE = re.compile(r"\b(?:was|were)\b", re.IGNORECASE)
FORBIDDEN_CAN_NEGATIVE = re.compile(r"\b(?:cannot|can\s+not|can't)\b", re.IGNORECASE)
PRESENT_CONTINUOUS = re.compile(r"\b(?:am|is|are)\s+([A-Za-z]+ing)\b", re.IGNORECASE)


class U06Spoken360MaterializationError(ValueError):
    pass


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().casefold()


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U06Spoken360MaterializationError(f"DATA_FILE_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("task_id") != TASK_ID:
        raise U06Spoken360MaterializationError(f"TASK_ID_DRIFT:{path.name}")
    if value.get("learner_facing_language_author") != "GPT-5.6 Sol":
        raise U06Spoken360MaterializationError(f"AUTHOR_DRIFT:{path.name}")
    if value.get("python_may_generate_or_rewrite_learner_facing_english") is not False:
        raise U06Spoken360MaterializationError(f"PYTHON_AUTHORING_NOT_DISABLED:{path.name}")
    contract = value.get("interaction_contract") or {}
    for key in (
        "same_current360_semantic_situation",
        "statement_led_interaction_no_questions",
        "turn_to_turn_dependency_required",
        "confirmation_reminder_or_reaction_required",
        "coherent_closing_state_required",
        "target_ability_realization_required",
        "paragraph_line_by_line_recitation_forbidden",
    ):
        if contract.get(key) is not True:
            raise U06Spoken360MaterializationError(
                f"INTERACTION_CONTRACT_DRIFT:{path.name}:{key}"
            )
    if contract.get("turn_range") != "5_TO_7":
        raise U06Spoken360MaterializationError(
            f"TURN_RANGE_CONTRACT_DRIFT:{path.name}:{contract.get('turn_range')}"
        )
    return value


def build_report() -> dict[str, Any]:
    current = p02.build_report()
    if current.get("status") != p02.STATUS:
        raise U06Spoken360MaterializationError("CURRENT360_NOT_PASS")
    current_rows = list(current.get("episodes") or [])
    if len(current_rows) != 360:
        raise U06Spoken360MaterializationError(
            f"CURRENT360_COUNT_DRIFT:{len(current_rows)}"
        )
    current_by_id = {str(row["episode_id"]): row for row in current_rows}

    shards = [_load(path) for path in DATA_PATHS]
    entries = [row for shard in shards for row in shard.get("entries") or []]
    if len(entries) != 360:
        raise U06Spoken360MaterializationError(f"ENTRY_COUNT_DRIFT:{len(entries)}")
    if len({row["reader_entry_id"] for row in entries}) != 360:
        raise U06Spoken360MaterializationError("READER_ENTRY_ID_COLLISION")
    if len({row["source_episode_id"] for row in entries}) != 360:
        raise U06Spoken360MaterializationError("SOURCE_EPISODE_ID_COLLISION")

    dialogue_keys: list[str] = []
    turn_counts: list[int] = []
    speaker_counts: list[int] = []
    output: list[dict[str, Any]] = []

    for index, entry in enumerate(entries, start=1):
        suffix = f"{index:03d}"
        reader_id = f"U06-SPOKEN360-E{suffix}"
        source_id = f"U06-NEB-E{suffix}"
        slot_id = f"U06-N360-S{suffix}"

        if entry.get("reader_entry_id") != reader_id:
            raise U06Spoken360MaterializationError(
                f"READER_ID_ORDER_DRIFT:{entry.get('reader_entry_id')}:{reader_id}"
            )
        if entry.get("source_episode_id") != source_id:
            raise U06Spoken360MaterializationError(
                f"SOURCE_ID_ORDER_DRIFT:{entry.get('source_episode_id')}:{source_id}"
            )
        if entry.get("source_episode_slot_id") != slot_id:
            raise U06Spoken360MaterializationError(
                f"SOURCE_SLOT_ORDER_DRIFT:{entry.get('source_episode_slot_id')}:{slot_id}"
            )

        source = current_by_id.get(source_id)
        if source is None:
            raise U06Spoken360MaterializationError(f"CURRENT360_SOURCE_MISSING:{source_id}")
        if list(entry.get("target_chunk_surfaces") or []) != list(
            source.get("target_chunk_surfaces") or []
        ):
            raise U06Spoken360MaterializationError(
                f"TARGET_LINEAGE_DRIFT:{reader_id}"
            )

        expected_start = ((index - 1) // 60) * 60 + 1
        expected_ref = (
            "product/a1fs_v1_2_1/data/"
            f"u06r360p02_current360_gpt56_e{expected_start:03d}_e{expected_start+59:03d}.json"
        )
        if entry.get("source_current360_ref") != expected_ref:
            raise U06Spoken360MaterializationError(
                f"SOURCE_REF_DRIFT:{reader_id}:{entry.get('source_current360_ref')}"
            )

        if not str(entry.get("interaction_trigger") or "").strip():
            raise U06Spoken360MaterializationError(
                f"INTERACTION_TRIGGER_EMPTY:{reader_id}"
            )
        if entry.get("author_model") != "GPT-5.6 Sol":
            raise U06Spoken360MaterializationError(f"EPISODE_AUTHOR_DRIFT:{reader_id}")
        for field in (
            "gpt56_semantic_review",
            "interaction_link_review",
            "target_ability_realization_review",
        ):
            if entry.get(field) != "PASS":
                raise U06Spoken360MaterializationError(
                    f"REVIEW_NOT_PASS:{reader_id}:{field}"
                )

        turns = list(entry.get("dialogue_turns") or [])
        turn_counts.append(len(turns))
        if not 5 <= len(turns) <= 7:
            raise U06Spoken360MaterializationError(
                f"TURN_COUNT_OUT_OF_RANGE:{reader_id}:{len(turns)}"
            )
        speakers = {
            str(turn.get("speaker") or "").strip()
            for turn in turns
            if str(turn.get("speaker") or "").strip()
        }
        speaker_counts.append(len(speakers))
        if len(speakers) < 2:
            raise U06Spoken360MaterializationError(
                f"INTERACTION_REQUIRES_MULTIPLE_SPEAKERS:{reader_id}"
            )

        parts: list[str] = []
        dialogue_texts: list[str] = []
        for turn in turns:
            speaker = str(turn.get("speaker") or "").strip()
            text = str(turn.get("text") or "").strip()
            if not speaker or not text:
                raise U06Spoken360MaterializationError(
                    f"EMPTY_DIALOGUE_TURN:{reader_id}"
                )
            if "?" in text:
                raise U06Spoken360MaterializationError(
                    f"CAN_INTERROGATIVE_BOUNDARY_LEAKAGE:{reader_id}"
                )
            if FORBIDDEN_CAN_NEGATIVE.search(text):
                raise U06Spoken360MaterializationError(
                    f"CAN_NEGATIVE_BOUNDARY_LEAKAGE:{reader_id}"
                )
            if FORBIDDEN_THERE_BE.search(text):
                raise U06Spoken360MaterializationError(
                    f"EXISTENTIAL_THERE_BE_LEAKAGE:{reader_id}"
                )
            if FORBIDDEN_PAST_BE.search(text):
                raise U06Spoken360MaterializationError(
                    f"PAST_BE_LEAKAGE:{reader_id}"
                )
            continuous_hits = [
                match.group(1).casefold()
                for match in PRESENT_CONTINUOUS.finditer(text)
                if match.group(1).casefold() != "morning"
            ]
            if continuous_hits:
                raise U06Spoken360MaterializationError(
                    f"PRESENT_CONTINUOUS_LEAKAGE:{reader_id}:{continuous_hits}"
                )
            parts.append(f"{speaker}:{_normalise(text)}")
            dialogue_texts.append(text)

        joined = _normalise(" ".join(dialogue_texts))
        for target in source.get("target_chunk_surfaces") or []:
            if _normalise(target) not in joined:
                raise U06Spoken360MaterializationError(
                    f"TARGET_ABILITY_NOT_REALIZED:{reader_id}:{target}"
                )

        source_sentences = [
            _normalise(sentence)
            for sentence in re.findall(r"[^.!?]+[.!?]", str(source.get("paragraph") or ""))
        ]
        turn_norms = {_normalise(text) for text in dialogue_texts}
        if source_sentences and all(sentence in turn_norms for sentence in source_sentences):
            raise U06Spoken360MaterializationError(
                f"PARAGRAPH_LINE_BY_LINE_RECITATION:{reader_id}"
            )

        dialogue_keys.append("|".join(parts))
        output.append(
            {
                **entry,
                "cluster_id": source.get("cluster_id"),
                "scene_family": source.get("scene_family"),
            }
        )

    duplicate_dialogues = [
        key for key, count in Counter(dialogue_keys).items() if count > 1
    ]
    if duplicate_dialogues:
        raise U06Spoken360MaterializationError(
            f"DIALOGUE_DUPLICATE_GROUPS:{len(duplicate_dialogues)}"
        )

    return {
        "schema_version": "a1fs.v1.u06.r360.spoken360_gpt56_materialization.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "source_current360_episode_count": len(current_rows),
        "entry_count": len(entries),
        "unique_reader_entry_count": len({row["reader_entry_id"] for row in entries}),
        "unique_source_episode_count": len({row["source_episode_id"] for row in entries}),
        "unique_dialogue_count": len(set(dialogue_keys)),
        "turn_count_min": min(turn_counts),
        "turn_count_max": max(turn_counts),
        "speaker_count_min": min(speaker_counts),
        "learner_facing_language_author": "GPT-5.6 Sol",
        "python_may_generate_or_rewrite_learner_facing_english": False,
        "gpt56_semantic_review_pass_count": sum(
            row["gpt56_semantic_review"] == "PASS" for row in entries
        ),
        "interaction_link_review_pass_count": sum(
            row["interaction_link_review"] == "PASS" for row in entries
        ),
        "target_ability_realization_review_pass_count": sum(
            row["target_ability_realization_review"] == "PASS" for row in entries
        ),
        "source_lineage_valid": True,
        "scope_safety": {
            "q01_q10_modified": False,
            "current360_modified": False,
            "python_generated_learner_facing_dialogue": False,
            "python_rewrote_learner_facing_dialogue": False,
            "pattern360_materialized": False,
            "far_materialized": False,
            "pdf_materialized": False,
            "can_interrogative_mastery_unlocked": False,
            "can_negative_mastery_unlocked": False,
            "permission_request_offer_possibility_can_unlocked": False,
            "present_continuous_mastery_unlocked": False,
            "a2_a2plus_unlocked": False,
        },
        "entries": output,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    report = build_report()
    print(f"STATUS={report['status']}")
    print(f"ENTRIES={report['entry_count']}")
    print(f"UNIQUE_DIALOGUES={report['unique_dialogue_count']}")
    print(f"TURN_RANGE={report['turn_count_min']}-{report['turn_count_max']}")
    print(f"GPT56_REVIEW_PASS={report['gpt56_semantic_review_pass_count']}")
    print(f"INTERACTION_LINK_PASS={report['interaction_link_review_pass_count']}")
    print(f"TARGET_REALIZATION_PASS={report['target_ability_realization_review_pass_count']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
