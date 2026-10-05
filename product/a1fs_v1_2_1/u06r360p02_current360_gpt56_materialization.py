#!/usr/bin/env python3
"""Unit06 Reader360 P02R2: GPT-5.6 Current360 6-8 sentence KET/Flyers-seeded rewrite.

Learner-facing English is static GPT-5.6 Sol authored/reviewed content.
Python only loads, joins, validates, counts and reports.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u06r360p01_natural360_source_projection as p01
from product.a1fs_v1_2_1 import u06r360p01_scene_diversity_expansion as p01r1

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validation-only loader for static GPT-5.6-authored Current360 JSON shards. "
    "Python may count, bind, deduplicate and validate but may not generate, rewrite, "
    "paraphrase or repair learner-facing English."
)
TASK_ID = "A1FS-V1-U06R360P02R2_Current360SixToEightSentenceKETFlyersSeededRewrite"
STATUS = "PASS_A1FS_V1_U06R360P02R2_CURRENT360_360_UNIT01_TO_06_KET_FLYERS_SEEDED"
NEXT_SHORT_STEP = "A1FS-V1-U06R360P03R2_Spoken360SixToEightTurnKETFlyersSeededRewrite"
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATHS = tuple(
    REPO_ROOT / f"product/a1fs_v1_2_1/data/u06r360p02_current360_gpt56_e{start:03d}_e{start+59:03d}.json"
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


class U06Current360Error(ValueError):
    pass


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def _sentence_count(value: str) -> int:
    return len(re.findall(r"[^.!?]+[.!?]", str(value)))


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("task_id") != TASK_ID:
        raise U06Current360Error(f"TASK_ID_DRIFT:{path.name}")
    if value.get("learner_facing_language_author") != "GPT-5.6 Sol":
        raise U06Current360Error(f"AUTHOR_DRIFT:{path.name}")
    if value.get("python_may_generate_or_rewrite_learner_facing_english") is not False:
        raise U06Current360Error(f"PYTHON_AUTHORING_NOT_DISABLED:{path.name}")
    contract = value.get("paragraph_contract") or {}
    if contract.get("sentence_range") != "6_TO_8":
        raise U06Current360Error(f"SENTENCE_RANGE_CONTRACT_DRIFT:{path.name}")
    if contract.get("cumulative_grammar_ceiling") != "UNIT01_TO_UNIT06_ONLY":
        raise U06Current360Error(f"GRAMMAR_CEILING_DRIFT:{path.name}")
    if contract.get("ket_flyers_use") != "LOWERED_TEXT_PURPOSE_AND_INFORMATION_STRUCTURE_ONLY":
        raise U06Current360Error(f"KET_FLYERS_BOUNDARY_DRIFT:{path.name}")
    if contract.get("text_shape_diversity_required") is not True:
        raise U06Current360Error(f"TEXT_SHAPE_DIVERSITY_NOT_REQUIRED:{path.name}")
    if contract.get("no_padding_sentences") is not True:
        raise U06Current360Error(f"NO_PADDING_CONTRACT_DRIFT:{path.name}")
    return value


def _validate_language(row: dict[str, Any]) -> int:
    eid = str(row["episode_id"])
    paragraph = str(row["paragraph"]).strip()
    count = _sentence_count(paragraph)
    if not 6 <= count <= 8:
        raise U06Current360Error(f"SENTENCE_RANGE_FAIL:{eid}:{count}")
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
        if regex.search(paragraph):
            raise U06Current360Error(f"{label}_LEAKAGE:{eid}:{regex.findall(paragraph)[:4]}")
    if "?" in paragraph:
        raise U06Current360Error(f"INTERROGATIVE_LEAKAGE:{eid}")
    targets = [_norm(x) for x in row.get("target_chunk_surfaces") or []]
    if not 1 <= len(targets) <= 2:
        raise U06Current360Error(f"TARGET_CHUNK_COUNT_INVALID:{eid}:{len(targets)}")
    norm = _norm(paragraph)
    for target in targets:
        if target not in norm:
            raise U06Current360Error(f"TARGET_CHUNK_NOT_REALIZED:{eid}:{target}")
    for field in (
        "reader_shape",
        "communicative_purpose",
        "gpt56_length_style_review",
        "ket_flyers_lowered_shape_review",
    ):
        if not str(row.get(field) or "").strip():
            raise U06Current360Error(f"R2_METADATA_MISSING:{eid}:{field}")
    if row.get("author_model") != "GPT-5.6 Sol":
        raise U06Current360Error(f"EPISODE_AUTHOR_DRIFT:{eid}")
    if row.get("gpt56_semantic_review") != "PASS":
        raise U06Current360Error(f"SEMANTIC_REVIEW_NOT_PASS:{eid}")
    if row.get("natural_style_review") != "PASS":
        raise U06Current360Error(f"NATURAL_STYLE_REVIEW_NOT_PASS:{eid}")
    if row.get("ket_flyers_lowered_shape_review") != "PASS":
        raise U06Current360Error(f"KET_FLYERS_REVIEW_NOT_PASS:{eid}")
    return count


def build_report() -> dict[str, Any]:
    projection = p01.build_unit06_natural360_source_projection()
    diversity = p01r1.build_unit06_scene_diversity_expansion()
    if projection.get("status") != p01.STATUS:
        raise U06Current360Error("P01_NOT_PASS")
    if diversity.get("status") != p01r1.STATUS:
        raise U06Current360Error("P01R1_NOT_PASS")

    shards = [_load(path) for path in DATA_PATHS]
    episodes = [row for shard in shards for row in shard["episodes"]]
    if len(episodes) != 360:
        raise U06Current360Error(f"EPISODE_COUNT_DRIFT:{len(episodes)}")
    if len({x["episode_id"] for x in episodes}) != 360:
        raise U06Current360Error("EPISODE_ID_COLLISION")
    if len({x["episode_slot_id"] for x in episodes}) != 360:
        raise U06Current360Error("EPISODE_SLOT_COLLISION")
    if len({_norm(x["paragraph"]) for x in episodes}) != 360:
        raise U06Current360Error("EXACT_PARAGRAPH_DUPLICATE")

    slots = list(projection["episode_authoring_slots"])
    if len(slots) != 360:
        raise U06Current360Error("P01_SLOT_DENOMINATOR_DRIFT")
    authorized = {
        _norm(chunk["normalized_surface"])
        for cluster in projection["source_clusters"]
        for chunk in cluster["functional_chunks"]
    }
    if len(authorized) != 182:
        raise U06Current360Error(f"AUTHORIZED_CHUNK_DENOMINATOR_DRIFT:{len(authorized)}")

    sentence_counts: list[int] = []
    corpus_targets: set[str] = set()
    scene_family_counts = Counter()
    reader_shape_counts = Counter()
    output: list[dict[str, Any]] = []
    controlled_chunk_family: dict[str, str] = {}
    for scene in diversity["reader360_local_scene_instances"]:
        controlled_chunk_family.setdefault(
            _norm(scene["functional_chunk_surface"]), str(scene["scene_family"])
        )

    for index, (row, slot) in enumerate(zip(episodes, slots), start=1):
        eid = f"U06-NEB-E{index:03d}"
        sid = f"U06-N360-S{index:03d}"
        if row["episode_id"] != eid or row["episode_slot_id"] != sid:
            raise U06Current360Error(
                f"IDENTITY_ORDER_DRIFT:{eid}:{row['episode_id']}:{row['episode_slot_id']}"
            )
        count = _validate_language(row)
        sentence_counts.append(count)
        targets = {_norm(x) for x in row["target_chunk_surfaces"]}
        if not targets <= authorized:
            raise U06Current360Error(
                f"UNAUTHORIZED_TARGET_CHUNK:{eid}:{sorted(targets-authorized)}"
            )
        corpus_targets.update(targets)
        family = slot.get("scene_family") or controlled_chunk_family.get(sorted(targets)[0])
        if not family:
            raise U06Current360Error(f"SCENE_FAMILY_LINEAGE_MISSING:{eid}")
        scene_family_counts[str(family)] += 1
        reader_shape_counts[str(row["reader_shape"])] += 1
        output.append({
            **row,
            "cluster_id": str(slot["cluster_id"]),
            "scene_family": str(family),
            "scene_lineage_mode": "P01R1_SCENE_FAMILY_PLUS_TARGET_CHUNK_SEMANTIC_LINEAGE",
        })

    if corpus_targets != authorized:
        raise U06Current360Error(
            f"CORPUS_CHUNK_COVERAGE_GAP:{len(corpus_targets)}/182:"
            f"{sorted(authorized-corpus_targets)[:20]}"
        )
    if len(scene_family_counts) != 12:
        raise U06Current360Error(f"SCENE_FAMILY_COVERAGE_DRIFT:{len(scene_family_counts)}")
    if len(reader_shape_counts) < 250:
        raise U06Current360Error(f"READER_SHAPE_DIVERSITY_TOO_LOW:{len(reader_shape_counts)}")
    max_shape_count = max(reader_shape_counts.values())
    max_shape_share = max_shape_count / 360
    if max_shape_share > 0.05:
        raise U06Current360Error(f"READER_SHAPE_DOMINANCE:{max_shape_count}:{max_shape_share:.4f}")

    predecessor = int(diversity["predecessor_distinct_scene_instance_count"])
    reservoir = int(diversity["current_distinct_scene_instance_count"])
    if reservoir <= predecessor:
        raise U06Current360Error("SCENE_DIVERSITY_MONOTONIC_RULE_BROKEN")

    distribution = dict(sorted(Counter(sentence_counts).items()))
    return {
        "schema_version": "a1fs.v1.u06.r360.current360_gpt56_materialization.v3",
        "task_id": TASK_ID,
        "status": STATUS,
        "episode_count": 360,
        "unique_paragraph_count": 360,
        "learner_facing_language_author": "GPT-5.6 Sol",
        "python_may_generate_or_rewrite_learner_facing_english": False,
        "sentence_count_policy": "UNIT06_6_TO_8_SENTENCES",
        "sentence_count_distribution": distribution,
        "sentence_count_min": min(sentence_counts),
        "sentence_count_max": max(sentence_counts),
        "source_cluster_count": len({str(x["cluster_id"]) for x in slots}),
        "scene_family_count": len(scene_family_counts),
        "scene_family_episode_counts": dict(sorted(scene_family_counts.items())),
        "functional_chunk_realization_coverage": "182/182",
        "reader_shape_count": len(reader_shape_counts),
        "reader_shape_max_count": max_shape_count,
        "reader_shape_max_share": max_shape_share,
        "ket_flyers_lowered_text_shape_policy": True,
        "unit01_to_unit06_grammar_ceiling": True,
        "scene_first_support": True,
        "chunk_stuffing_forbidden": True,
        "per_episode_preassigned_chunk_surface_realization_required": False,
        "scene_diversity_policy_id": diversity["scene_diversity_policy_id"],
        "scene_diversity_reservoir_count": reservoir,
        "predecessor_scene_diversity_count": predecessor,
        "scene_diversity_growth_over_predecessor": reservoir-predecessor,
        "scope_safety": {
            "q01_q10_modified": False,
            "q07_canonical_scene_authority_modified": False,
            "q07r1_chunk_semantics_modified": False,
            "new_global_scene_family_created": False,
            "pattern360_materialized": False,
            "far_materialized": False,
            "can_interrogative_mastery_unlocked": False,
            "can_negative_mastery_unlocked": False,
            "permission_request_offer_possibility_can_unlocked": False,
            "present_continuous_mastery_unlocked": False,
            "a2_a2plus_unlocked": False,
        },
        "episodes": output,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    r = build_report()
    print(f"STATUS={r['status']}")
    print(f"EPISODES={r['episode_count']}")
    print(f"SENTENCE_COUNTS={r['sentence_count_distribution']}")
    print(f"READER_SHAPES={r['reader_shape_count']}")
    print(f"CHUNKS={r['functional_chunk_realization_coverage']}")
    print(f"NEXT_SHORT_STEP={r['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
