from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validation-only loader for a static GPT-5.6-authored Unit05 Spoken360 corpus. "
    "Python may load, join, count, deduplicate, and validate learner-facing dialogue, "
    "but may not generate, rewrite, paraphrase, or repair it."
)

TASK_ID = "A1FS-V1-U05R360P03_Spoken360GPT56DialogueMaterialization"
STATUS = "PASS_A1FS_V1_U05R360P03_SPOKEN360_GPT56_INTERACTION_LINK_360"
REVISION = "UNIT05_SPOKEN360_GPT56_INTERACTION_LINK_V1"
NEXT_SHORT_STEP = "A1FS-V1-U05R360P04_Pattern360GPT56SentenceFamilyMaterialization"

REPO_ROOT = Path(__file__).resolve().parents[2]
CURRENT360_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_current360_360.json"
DATA_PATHS = tuple(
    REPO_ROOT / f"product/a1fs_v1_2_1/data/u05r360p03_spoken360_gpt56_e{start:03d}_e{start+59:03d}.json"
    for start in (1, 61, 121, 181, 241, 301)
)

FORBIDDEN_THERE_BE = re.compile(r"\bthere\s+(?:is|are)\b", re.IGNORECASE)
FORBIDDEN_PAST_BE = re.compile(r"\b(?:was|were)\b", re.IGNORECASE)
PRESENT_CONTINUOUS_SHAPE = re.compile(r"\b(?:am|is|are)\s+([A-Za-z]+ing)\b", re.IGNORECASE)


class U05Spoken360MaterializationError(ValueError):
    pass


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05Spoken360MaterializationError(f"DATA_FILE_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U05Spoken360MaterializationError(f"DATA_FILE_NOT_OBJECT:{path}")
    return value


def build_report() -> dict[str, Any]:
    current = _load_json(CURRENT360_PATH)
    current_rows = list(current.get("episodes") or [])
    if len(current_rows) != 360:
        raise U05Spoken360MaterializationError(
            f"CURRENT360_COUNT_DRIFT:{len(current_rows)}"
        )
    current_by_id = {row["episode_id"]: row for row in current_rows}

    shards = [_load_json(path) for path in DATA_PATHS]
    for path, shard in zip(DATA_PATHS, shards):
        if shard.get("learner_facing_language_author") != "GPT-5.6 Sol":
            raise U05Spoken360MaterializationError(f"AUTHOR_DRIFT:{path}")
        if shard.get("python_may_generate_or_rewrite_learner_facing_english") is not False:
            raise U05Spoken360MaterializationError(
                f"PYTHON_AUTHORING_NOT_DISABLED:{path}"
            )
        contract = shard.get("interaction_contract") or {}
        for key in (
            "same_current360_semantic_situation",
            "conversation_trigger_required",
            "turn_to_turn_dependency_required",
            "confirmation_correction_reminder_or_reaction_required",
            "coherent_closing_state_required",
            "paragraph_line_by_line_recitation_forbidden",
        ):
            if contract.get(key) is not True:
                raise U05Spoken360MaterializationError(
                    f"INTERACTION_CONTRACT_DRIFT:{path}:{key}"
                )

    entries = [row for shard in shards for row in shard["entries"]]
    if len(entries) != 360:
        raise U05Spoken360MaterializationError(f"ENTRY_COUNT_DRIFT:{len(entries)}")
    if len({row["reader_entry_id"] for row in entries}) != 360:
        raise U05Spoken360MaterializationError("READER_ENTRY_ID_COLLISION")
    if len({row["source_episode_id"] for row in entries}) != 360:
        raise U05Spoken360MaterializationError("SOURCE_EPISODE_ID_COLLISION")

    dialogue_keys: list[str] = []
    turn_counts: list[int] = []
    speaker_counts: list[int] = []

    for index, entry in enumerate(entries, start=1):
        suffix = f"{index:03d}"
        if entry["reader_entry_id"] != f"U05-SPOKEN360-E{suffix}":
            raise U05Spoken360MaterializationError(
                f"READER_ID_ORDER_DRIFT:{entry['reader_entry_id']}"
            )
        if entry["source_episode_id"] != f"U05-NEB-E{suffix}":
            raise U05Spoken360MaterializationError(
                f"SOURCE_ID_ORDER_DRIFT:{entry['source_episode_id']}"
            )

        source = current_by_id.get(entry["source_episode_id"])
        if source is None:
            raise U05Spoken360MaterializationError(
                f"CURRENT360_SOURCE_MISSING:{entry['source_episode_id']}"
            )
        if entry["scene_family"] != source["scene_family"]:
            raise U05Spoken360MaterializationError(
                f"SCENE_FAMILY_DRIFT:{entry['reader_entry_id']}"
            )
        if entry["discourse_family"] != source["discourse_family"]:
            raise U05Spoken360MaterializationError(
                f"DISCOURSE_FAMILY_DRIFT:{entry['reader_entry_id']}"
            )
        if entry["source_scene_refs"] != source["source_scene_refs"]:
            raise U05Spoken360MaterializationError(
                f"SOURCE_SCENE_LINEAGE_DRIFT:{entry['reader_entry_id']}"
            )

        if not str(entry.get("interaction_trigger") or "").strip():
            raise U05Spoken360MaterializationError(
                f"INTERACTION_TRIGGER_EMPTY:{entry['reader_entry_id']}"
            )
        if entry.get("author_model") != "GPT-5.6 Sol":
            raise U05Spoken360MaterializationError(
                f"EPISODE_AUTHOR_DRIFT:{entry['reader_entry_id']}"
            )
        if entry.get("gpt56_semantic_review") != "PASS":
            raise U05Spoken360MaterializationError(
                f"SEMANTIC_REVIEW_NOT_PASS:{entry['reader_entry_id']}"
            )
        if entry.get("interaction_link_review") != "PASS":
            raise U05Spoken360MaterializationError(
                f"INTERACTION_LINK_REVIEW_NOT_PASS:{entry['reader_entry_id']}"
            )

        turns = list(entry.get("dialogue_turns") or [])
        turn_counts.append(len(turns))
        if not 5 <= len(turns) <= 8:
            raise U05Spoken360MaterializationError(
                f"TURN_COUNT_OUT_OF_RANGE:{entry['reader_entry_id']}:{len(turns)}"
            )
        speakers = {str(turn.get("speaker") or "").strip() for turn in turns}
        speakers.discard("")
        speaker_counts.append(len(speakers))
        if len(speakers) < 2:
            raise U05Spoken360MaterializationError(
                f"INTERACTION_REQUIRES_MULTIPLE_SPEAKERS:{entry['reader_entry_id']}"
            )

        parts: list[str] = []
        for turn in turns:
            speaker = str(turn.get("speaker") or "").strip()
            text = str(turn.get("text") or "").strip()
            if not speaker or not text:
                raise U05Spoken360MaterializationError(
                    f"EMPTY_DIALOGUE_TURN:{entry['reader_entry_id']}"
                )
            if "?" in text:
                raise U05Spoken360MaterializationError(
                    f"BE_INTERROGATIVE_BOUNDARY_LEAKAGE:{entry['reader_entry_id']}"
                )
            if FORBIDDEN_THERE_BE.search(text):
                raise U05Spoken360MaterializationError(
                    f"EXISTENTIAL_THERE_BE_LEAKAGE:{entry['reader_entry_id']}"
                )
            if FORBIDDEN_PAST_BE.search(text):
                raise U05Spoken360MaterializationError(
                    f"PAST_BE_LEAKAGE:{entry['reader_entry_id']}"
                )
            continuous_hits = [
                match.group(1).casefold()
                for match in PRESENT_CONTINUOUS_SHAPE.finditer(text)
                if match.group(1).casefold() != "morning"
            ]
            if continuous_hits:
                raise U05Spoken360MaterializationError(
                    f"PRESENT_CONTINUOUS_LEAKAGE:{entry['reader_entry_id']}:{continuous_hits}"
                )
            parts.append(f"{speaker}:{_normalise(text)}")
        dialogue_keys.append("|".join(parts))

    duplicates = [key for key, count in Counter(dialogue_keys).items() if count > 1]
    if duplicates:
        raise U05Spoken360MaterializationError(
            f"DIALOGUE_DUPLICATE_GROUPS:{len(duplicates)}"
        )

    return {
        "schema_version": "a1fs.v1.u05.r360.spoken360_gpt56_materialization.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "source_authority": str(CURRENT360_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
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
        "source_lineage_valid": True,
        "scope_safety": {
            "current360_modified": False,
            "python_generated_learner_facing_dialogue": False,
            "python_rewrote_learner_facing_dialogue": False,
            "pattern360_materialized": False,
            "contextual_active_runtime_materialized": False,
            "pdf_materialized": False,
            "be_interrogative_mastery_unlocked": False,
            "past_be_unlocked": False,
            "existential_there_be_unlocked": False,
            "present_continuous_mastery_unlocked": False,
            "a2_a2plus_unlocked": False,
        },
        "entries": entries,
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
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
