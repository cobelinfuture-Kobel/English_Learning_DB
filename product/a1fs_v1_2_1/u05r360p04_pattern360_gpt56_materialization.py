from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validation-only loader for a static GPT-5.6-authored Unit05 Pattern360 corpus. "
    "Python may load, join, count, and validate learner-facing examples, but may not "
    "generate, rewrite, paraphrase, or repair learner-facing English."
)

TASK_ID = "A1FS-V1-U05R360P04_Pattern360GPT56SentenceFamilyMaterialization"
STATUS = "PASS_A1FS_V1_U05R360P04_PATTERN360_GPT56_ADAPTIVE_CORE_FAMILY_360"
REVISION = "UNIT05_PATTERN360_GPT56_ADAPTIVE_CORE_FAMILY_V1"
NEXT_SHORT_STEP = "A1FS-V1-U05R360P05_ContextualActiveRuntimeCutover"

REPO_ROOT = Path(__file__).resolve().parents[2]
CURRENT360_PATH = REPO_ROOT / "product/a1fs_v1_2_1/data/unit05_current360_360.json"
DATA_PATHS = tuple(
    REPO_ROOT / f"product/a1fs_v1_2_1/data/u05r360p04_pattern360_gpt56_e{start:03d}_e{start+29:03d}.json"
    for start in range(1, 361, 30)
)

FAMILY_NAMES = {
    "A": "PRIMARY_CORE_BE_FAMILY",
    "B": "SECONDARY_BE_FAMILY",
    "C": "LOCATION_COMPLEMENT_FAMILY",
    "D": "SUBJECT_PRONOUN_BE_AGREEMENT_SHIFT",
    "E": "AFFIRMATIVE_NEGATIVE_CONTRAST",
    "F": "CONNECTED_BE_SENTENCE_FAMILY",
    "G": "CONTROLLED_CONTEXTUAL_TRANSFER",
}
EVIDENCE_MODES = {
    "SOURCE_GROUNDED",
    "CONTROLLED_SEMANTIC_INFERENCE",
    "CONTROLLED_TRANSFER_NOT_SOURCE_FACT",
}
CORE_SELECTIONS = {"IDENTITY_CATEGORY", "STATE_DESCRIPTION", "PLACE"}

FORBIDDEN_THERE_BE = re.compile(r"\bthere\s+(?:is|are)\b", re.IGNORECASE)
FORBIDDEN_PAST_BE = re.compile(r"\b(?:was|were)\b", re.IGNORECASE)
PRESENT_CONTINUOUS_SHAPE = re.compile(r"\b(?:am|is|are)\s+([A-Za-z]+ing)\b", re.IGNORECASE)


class U05Pattern360MaterializationError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05Pattern360MaterializationError(f"DATA_FILE_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U05Pattern360MaterializationError(f"DATA_FILE_NOT_OBJECT:{path}")
    return value


def build_report() -> dict[str, Any]:
    current = _load_json(CURRENT360_PATH)
    current_rows = list(current.get("episodes") or [])
    if len(current_rows) != 360:
        raise U05Pattern360MaterializationError(
            f"CURRENT360_COUNT_DRIFT:{len(current_rows)}"
        )
    current_by_id = {row["episode_id"]: row for row in current_rows}

    shards = [_load_json(path) for path in DATA_PATHS]
    for path, shard in zip(DATA_PATHS, shards):
        if shard.get("learner_facing_language_author") != "GPT-5.6 Sol":
            raise U05Pattern360MaterializationError(f"AUTHOR_DRIFT:{path}")
        if shard.get("python_may_generate_or_rewrite_learner_facing_english") is not False:
            raise U05Pattern360MaterializationError(f"PYTHON_AUTHORING_NOT_DISABLED:{path}")
        if shard.get("contract_revision") != REVISION:
            raise U05Pattern360MaterializationError(f"CONTRACT_REVISION_DRIFT:{path}")
        if shard.get("evidence_mode_assignment") != "PER_EXAMPLE":
            raise U05Pattern360MaterializationError(f"EVIDENCE_ASSIGNMENT_DRIFT:{path}")

    entries = [row for shard in shards for row in shard["entries"]]
    if len(entries) != 360:
        raise U05Pattern360MaterializationError(f"ENTRY_COUNT_DRIFT:{len(entries)}")
    if len({row["reader_entry_id"] for row in entries}) != 360:
        raise U05Pattern360MaterializationError("READER_ENTRY_ID_COLLISION")
    if len({row["source_episode_id"] for row in entries}) != 360:
        raise U05Pattern360MaterializationError("SOURCE_EPISODE_ID_COLLISION")

    evidence_counts: Counter[str] = Counter()
    example_count = 0

    for index, entry in enumerate(entries, start=1):
        suffix = f"{index:03d}"
        if entry["reader_entry_id"] != f"U05-PATTERN360-E{suffix}":
            raise U05Pattern360MaterializationError(
                f"READER_ID_ORDER_DRIFT:{entry['reader_entry_id']}"
            )
        if entry["source_episode_id"] != f"U05-NEB-E{suffix}":
            raise U05Pattern360MaterializationError(
                f"SOURCE_ID_ORDER_DRIFT:{entry['source_episode_id']}"
            )

        source = current_by_id.get(entry["source_episode_id"])
        if source is None:
            raise U05Pattern360MaterializationError(
                f"CURRENT360_SOURCE_MISSING:{entry['source_episode_id']}"
            )
        if entry["scene_family"] != source["scene_family"]:
            raise U05Pattern360MaterializationError(
                f"SCENE_FAMILY_DRIFT:{entry['reader_entry_id']}"
            )
        if entry["discourse_family"] != source["discourse_family"]:
            raise U05Pattern360MaterializationError(
                f"DISCOURSE_FAMILY_DRIFT:{entry['reader_entry_id']}"
            )
        if entry["source_scene_refs"] != source["source_scene_refs"]:
            raise U05Pattern360MaterializationError(
                f"SOURCE_SCENE_LINEAGE_DRIFT:{entry['reader_entry_id']}"
            )

        if entry.get("primary_core_selection") not in CORE_SELECTIONS:
            raise U05Pattern360MaterializationError(
                f"PRIMARY_CORE_SELECTION_DRIFT:{entry['reader_entry_id']}"
            )
        if entry.get("secondary_core_selection") not in CORE_SELECTIONS:
            raise U05Pattern360MaterializationError(
                f"SECONDARY_CORE_SELECTION_DRIFT:{entry['reader_entry_id']}"
            )

        families = entry.get("families") or {}
        if set(families) != set(FAMILY_NAMES):
            raise U05Pattern360MaterializationError(
                f"FAMILY_SET_DRIFT:{entry['reader_entry_id']}"
            )

        for family_id, expected_name in FAMILY_NAMES.items():
            family = families[family_id]
            if family.get("name") != expected_name:
                raise U05Pattern360MaterializationError(
                    f"FAMILY_NAME_DRIFT:{entry['reader_entry_id']}:{family_id}"
                )
            examples = list(family.get("examples") or [])
            if not examples:
                raise U05Pattern360MaterializationError(
                    f"FAMILY_EMPTY:{entry['reader_entry_id']}:{family_id}"
                )
            if family_id == "G" and any(
                example.get("evidence_mode") != "CONTROLLED_TRANSFER_NOT_SOURCE_FACT"
                for example in examples
            ):
                raise U05Pattern360MaterializationError(
                    f"G_TRANSFER_PROVENANCE_DRIFT:{entry['reader_entry_id']}"
                )

            for example in examples:
                text = str(example.get("text") or "").strip()
                mode = str(example.get("evidence_mode") or "")
                if not text:
                    raise U05Pattern360MaterializationError(
                        f"EMPTY_EXAMPLE:{entry['reader_entry_id']}:{family_id}"
                    )
                if mode not in EVIDENCE_MODES:
                    raise U05Pattern360MaterializationError(
                        f"EVIDENCE_MODE_DRIFT:{entry['reader_entry_id']}:{family_id}:{mode}"
                    )
                if "?" in text:
                    raise U05Pattern360MaterializationError(
                        f"BE_INTERROGATIVE_BOUNDARY_LEAKAGE:{entry['reader_entry_id']}"
                    )
                if FORBIDDEN_THERE_BE.search(text):
                    raise U05Pattern360MaterializationError(
                        f"EXISTENTIAL_THERE_BE_LEAKAGE:{entry['reader_entry_id']}"
                    )
                if FORBIDDEN_PAST_BE.search(text):
                    raise U05Pattern360MaterializationError(
                        f"PAST_BE_LEAKAGE:{entry['reader_entry_id']}"
                    )
                continuous_hits = [
                    match.group(1).casefold()
                    for match in PRESENT_CONTINUOUS_SHAPE.finditer(text)
                    if match.group(1).casefold() != "morning"
                ]
                if continuous_hits:
                    raise U05Pattern360MaterializationError(
                        f"PRESENT_CONTINUOUS_LEAKAGE:{entry['reader_entry_id']}:{continuous_hits}"
                    )
                evidence_counts[mode] += 1
                example_count += 1

    return {
        "schema_version": "a1fs.v1.u05.r360.pattern360_gpt56_materialization.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "source_current360_episode_count": len(current_rows),
        "entry_count": len(entries),
        "unique_reader_entry_count": len({row["reader_entry_id"] for row in entries}),
        "unique_source_episode_count": len({row["source_episode_id"] for row in entries}),
        "family_group_count": len(entries) * len(FAMILY_NAMES),
        "example_count": example_count,
        "evidence_mode_counts": dict(sorted(evidence_counts.items())),
        "learner_facing_language_author": "GPT-5.6 Sol",
        "python_may_generate_or_rewrite_learner_facing_english": False,
        "source_lineage_valid": True,
        "scope_safety": {
            "current360_modified": False,
            "spoken360_modified": False,
            "python_generated_learner_facing_examples": False,
            "python_rewrote_learner_facing_examples": False,
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
    print(f"FAMILY_GROUPS={report['family_group_count']}")
    print(f"EXAMPLES={report['example_count']}")
    print(f"EVIDENCE_MODE_COUNTS={report['evidence_mode_counts']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
