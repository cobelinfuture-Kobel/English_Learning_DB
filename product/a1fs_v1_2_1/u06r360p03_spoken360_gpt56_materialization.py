#!/usr/bin/env python3
"""Unit06 Reader360 P03R2: GPT-5.6 Spoken360 6-8 turn KET/Flyers-seeded rewrite.

Learner-facing dialogue is static GPT-5.6 Sol authored/reviewed content.
Python only loads, joins, validates, counts and reports.
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
    "Validation-only loader for static GPT-5.6-authored Unit06 Spoken360. "
    "Python may load, join, count, deduplicate and validate but may not generate, "
    "rewrite, paraphrase or repair learner-facing dialogue."
)
TASK_ID = "A1FS-V1-U06R360P03R2_Spoken360SixToEightTurnKETFlyersSeededRewrite"
STATUS = "PASS_A1FS_V1_U06R360P03R2_SPOKEN360_360_UNIT01_TO_06_KET_FLYERS_SEEDED"
REVISION = "UNIT06_SPOKEN360_GPT56_6_TO_8_KET_FLYERS_SEEDED_R2"
NEXT_SHORT_STEP = "A1FS-V1-U06R360P04_Pattern360GPT56SentenceFamilyMaterialization"

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATHS = tuple(
    REPO_ROOT / f"product/a1fs_v1_2_1/data/u06r360p03_spoken360_gpt56_e{start:03d}_e{start+59:03d}.json"
    for start in (1, 61, 121, 181, 241, 301)
)

FORBIDDEN_THERE_BE = re.compile(r"\bthere\s+(?:is|are)\b", re.I)
FORBIDDEN_PAST_BE = re.compile(r"\b(?:was|were)\b", re.I)
FORBIDDEN_CAN_NEGATIVE = re.compile(r"\b(?:cannot|can\s+not|can't)\b", re.I)
FORBIDDEN_CAN_NONABILITY = re.compile(r"\bcan\s+(?:be|have)\b", re.I)
PRESENT_CONTINUOUS = re.compile(r"\b(?:am|is|are)\s+([A-Za-z]+ing)\b", re.I)
FORBIDDEN_GERUND_LINK = re.compile(r"\b(?:after|before|without|by)\s+[A-Za-z]+ing\b", re.I)
FORBIDDEN_SIMPLE_3SG = re.compile(
    r"\b(?:has|does|goes|comes|puts|looks|enters|carries|likes|wants|needs|makes|"
    r"reads|writes|sits|stands|helps|plays|sings|runs|walks|eats|drinks|washes|"
    r"closes|opens|moves|finds|sees|talks|waits|works|studies|takes|throws|"
    r"catches|kicks|rides|swims|climbs|flies|paints|draws|gives|calls|emails|"
    r"phones|texts|says|tells|spells|answers|asks|teaches|understands|brings|"
    r"builds|cleans|cooks|dries|changes|listens|shows|holds|points|sends|uses)\b",
    re.I,
)
FORBIDDEN_SIMPLE_PLURAL = re.compile(
    r"\b(?:i|you|we|they)\s+(?:have|do|go|come|put|look|enter|carry|like|want|"
    r"need|make|read|write|sit|stand|help|play|sing|run|walk|eat|drink|wash|"
    r"close|open|move|find|see|talk|wait|work|study|take|throw|catch|kick|ride|"
    r"swim|climb|fly|paint|draw|give|call|email|phone|text|say|tell|spell|answer|"
    r"ask|teach|understand|bring|build|clean|cook|dry|change|listen|show|hold|"
    r"point|send|use)\b",
    re.I,
)


class U06Spoken360MaterializationError(ValueError):
    pass


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().casefold()


def _sentence_norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", str(text).casefold()).strip()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("task_id") != TASK_ID:
        raise U06Spoken360MaterializationError(f"TASK_ID_DRIFT:{path.name}")
    if value.get("learner_facing_language_author") != "GPT-5.6 Sol":
        raise U06Spoken360MaterializationError(f"AUTHOR_DRIFT:{path.name}")
    if value.get("python_may_generate_or_rewrite_learner_facing_english") is not False:
        raise U06Spoken360MaterializationError(f"PYTHON_AUTHORING_NOT_DISABLED:{path.name}")
    contract = value.get("interaction_contract") or {}
    expected_true = (
        "same_current360_semantic_situation",
        "statement_led_interaction_no_questions",
        "turn_to_turn_dependency_required",
        "confirmation_reminder_reaction_or_handoff_required",
        "coherent_closing_state_required",
        "target_ability_realization_required",
        "paragraph_line_by_line_recitation_forbidden",
        "interaction_shape_diversity_required",
    )
    for key in expected_true:
        if contract.get(key) is not True:
            raise U06Spoken360MaterializationError(
                f"INTERACTION_CONTRACT_DRIFT:{path.name}:{key}"
            )
    if contract.get("turn_range") != "6_TO_8":
        raise U06Spoken360MaterializationError(
            f"TURN_RANGE_CONTRACT_DRIFT:{path.name}:{contract.get('turn_range')}"
        )
    if contract.get("cumulative_grammar_ceiling") != "UNIT01_TO_UNIT06_ONLY":
        raise U06Spoken360MaterializationError(f"GRAMMAR_CEILING_DRIFT:{path.name}")
    if contract.get("ket_flyers_use") != "LOWERED_INTERACTION_PURPOSE_AND_INFORMATION_FLOW_ONLY":
        raise U06Spoken360MaterializationError(f"KET_FLYERS_BOUNDARY_DRIFT:{path.name}")
    return value


def _validate_text(reader_id: str, text: str) -> None:
    for regex, label in (
        (FORBIDDEN_THERE_BE, "THERE_BE"),
        (FORBIDDEN_PAST_BE, "PAST_BE"),
        (FORBIDDEN_CAN_NEGATIVE, "CAN_NEGATIVE"),
        (FORBIDDEN_CAN_NONABILITY, "NONABILITY_CAN"),
        (PRESENT_CONTINUOUS, "PRESENT_CONTINUOUS"),
        (FORBIDDEN_GERUND_LINK, "GERUND_LINK"),
        (FORBIDDEN_SIMPLE_3SG, "LEXICAL_PRESENT_SIMPLE_3SG"),
        (FORBIDDEN_SIMPLE_PLURAL, "LEXICAL_PRESENT_SIMPLE_PLURAL"),
    ):
        if regex.search(text):
            raise U06Spoken360MaterializationError(
                f"{label}_LEAKAGE:{reader_id}:{regex.findall(text)[:4]}"
            )
    if "?" in text:
        raise U06Spoken360MaterializationError(f"INTERROGATIVE_LEAKAGE:{reader_id}")


def build_report() -> dict[str, Any]:
    current = p02.build_report()
    if current.get("status") != p02.STATUS:
        raise U06Spoken360MaterializationError("CURRENT360_NOT_PASS")
    current_rows = list(current.get("episodes") or [])
    if len(current_rows) != 360:
        raise U06Spoken360MaterializationError(f"CURRENT360_COUNT_DRIFT:{len(current_rows)}")
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
    interaction_shape_counts = Counter()
    output: list[dict[str, Any]] = []
    recitation_risk_count = 0

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
            raise U06Spoken360MaterializationError(f"TARGET_LINEAGE_DRIFT:{reader_id}")

        expected_start = ((index - 1) // 60) * 60 + 1
        expected_ref = (
            "product/a1fs_v1_2_1/data/"
            f"u06r360p02_current360_gpt56_e{expected_start:03d}_e{expected_start+59:03d}.json"
        )
        if entry.get("source_current360_ref") != expected_ref:
            raise U06Spoken360MaterializationError(
                f"SOURCE_REF_DRIFT:{reader_id}:{entry.get('source_current360_ref')}"
            )
        if entry.get("source_current360_revision") != "U06R360P02R2_6_TO_8_KET_FLYERS_SEEDED":
            raise U06Spoken360MaterializationError(f"SOURCE_REVISION_DRIFT:{reader_id}")

        turns = list(entry.get("dialogue_turns") or [])
        if not 6 <= len(turns) <= 8:
            raise U06Spoken360MaterializationError(f"TURN_COUNT_DRIFT:{reader_id}:{len(turns)}")
        speakers = {str(t.get("speaker") or "").strip() for t in turns}
        if "" in speakers or len(speakers) < 2:
            raise U06Spoken360MaterializationError(f"SPEAKER_COUNT_DRIFT:{reader_id}:{len(speakers)}")
        dialogue_text = " ".join(str(t.get("text") or "").strip() for t in turns)
        _validate_text(reader_id, dialogue_text)
        for target in entry.get("target_chunk_surfaces") or []:
            if _norm(target) not in _norm(dialogue_text):
                raise U06Spoken360MaterializationError(
                    f"TARGET_ABILITY_NOT_REALIZED:{reader_id}:{target}"
                )

        for field in (
            "interaction_trigger",
            "interaction_shape",
            "gpt56_semantic_review",
            "interaction_link_review",
            "target_ability_realization_review",
            "ket_flyers_lowered_interaction_review",
        ):
            if not str(entry.get(field) or "").strip():
                raise U06Spoken360MaterializationError(f"R2_METADATA_MISSING:{reader_id}:{field}")
        if entry.get("author_model") != "GPT-5.6 Sol":
            raise U06Spoken360MaterializationError(f"AUTHOR_MODEL_DRIFT:{reader_id}")
        for field in (
            "gpt56_semantic_review",
            "interaction_link_review",
            "target_ability_realization_review",
            "ket_flyers_lowered_interaction_review",
        ):
            if entry.get(field) != "PASS":
                raise U06Spoken360MaterializationError(f"REVIEW_NOT_PASS:{reader_id}:{field}")

        current_sentences = [
            _sentence_norm(x)
            for x in re.split(r"(?<=[.!?])\s+", str(source["paragraph"]))
            if str(x).strip()
        ]
        turn_set = {_sentence_norm(t["text"]) for t in turns}
        exact_shared = sum(1 for s in current_sentences if s in turn_set)
        if exact_shared >= 5:
            recitation_risk_count += 1
            raise U06Spoken360MaterializationError(
                f"LINE_BY_LINE_RECITATION_RISK:{reader_id}:{exact_shared}/{len(current_sentences)}"
            )

        dialogue_key = "|".join(
            f"{t['speaker']}:{_norm(t['text'])}" for t in turns
        )
        dialogue_keys.append(dialogue_key)
        turn_counts.append(len(turns))
        speaker_counts.append(len(speakers))
        interaction_shape_counts[str(entry["interaction_shape"])] += 1
        output.append({
            **entry,
            "cluster_id": source["cluster_id"],
            "scene_family": source["scene_family"],
            "current360_reader_shape": source["reader_shape"],
        })

    if len(set(dialogue_keys)) != 360:
        raise U06Spoken360MaterializationError("DIALOGUE_DUPLICATE")
    if len(interaction_shape_counts) < 300:
        raise U06Spoken360MaterializationError(
            f"INTERACTION_SHAPE_DIVERSITY_TOO_LOW:{len(interaction_shape_counts)}"
        )
    max_shape_count = max(interaction_shape_counts.values())
    max_shape_share = max_shape_count / 360
    if max_shape_share > 0.02:
        raise U06Spoken360MaterializationError(
            f"INTERACTION_SHAPE_DOMINANCE:{max_shape_count}:{max_shape_share:.4f}"
        )

    return {
        "schema_version": "a1fs.v1.u06.r360.spoken360_gpt56_materialization.v3",
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "entry_count": 360,
        "unique_reader_entry_count": 360,
        "unique_source_episode_count": 360,
        "unique_dialogue_count": 360,
        "source_current360_episode_count": 360,
        "source_lineage_valid": True,
        "learner_facing_language_author": "GPT-5.6 Sol",
        "python_may_generate_or_rewrite_learner_facing_english": False,
        "turn_count_distribution": dict(sorted(Counter(turn_counts).items())),
        "turn_count_min": min(turn_counts),
        "turn_count_max": max(turn_counts),
        "speaker_count_min": min(speaker_counts),
        "interaction_shape_count": len(interaction_shape_counts),
        "interaction_shape_max_count": max_shape_count,
        "interaction_shape_max_share": max_shape_share,
        "line_by_line_recitation_risk_count": recitation_risk_count,
        "gpt56_semantic_review_pass_count": 360,
        "interaction_link_review_pass_count": 360,
        "target_ability_realization_review_pass_count": 360,
        "ket_flyers_lowered_interaction_review_pass_count": 360,
        "unit01_to_unit06_grammar_ceiling": True,
        "scope_safety": {
            "q01_q10_modified": False,
            "python_generated_learner_facing_dialogue": False,
            "python_rewrote_learner_facing_dialogue": False,
            "can_interrogative_mastery_unlocked": False,
            "can_negative_mastery_unlocked": False,
            "permission_request_offer_possibility_can_unlocked": False,
            "present_continuous_mastery_unlocked": False,
            "a2_a2plus_unlocked": False,
            "pattern360_materialized": False,
            "far_materialized": False,
        },
        "entries": output,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    r = build_report()
    print(f"STATUS={r['status']}")
    print(f"ENTRIES={r['entry_count']}")
    print(f"TURNS={r['turn_count_distribution']}")
    print(f"INTERACTION_SHAPES={r['interaction_shape_count']}")
    print(f"RECITATION_RISK={r['line_by_line_recitation_risk_count']}")
    print(f"NEXT_SHORT_STEP={r['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
