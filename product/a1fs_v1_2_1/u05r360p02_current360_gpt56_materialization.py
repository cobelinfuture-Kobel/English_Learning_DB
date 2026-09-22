from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u05r360p01_natural360_source_projection as p01

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validation-only loader for a static GPT-5.6-authored Unit05 Current360 corpus. "
    "Python may load, join, count, deduplicate, and validate learner-facing English, "
    "but may not generate, rewrite, paraphrase, or repair it."
)

TASK_ID = "A1FS-V1-U05R360P02_Current360GPT56NaturalEpisodeMaterialization"
STATUS = "PASS_A1FS_V1_U05R360P02_CURRENT360_GPT56_NATURAL_EPISODE_MATERIALIZATION"
REVISION = "UNIT05_CURRENT360_GPT56_36_CLUSTER_360_PARAGRAPH_V1"
NEXT_SHORT_STEP = "A1FS-V1-U05R360P03_Spoken360GPT56DialogueMaterialization"

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATHS = tuple(
    REPO_ROOT / f"product/a1fs_v1_2_1/data/u05r360p02_current360_gpt56_e{start:03d}_e{start+59:03d}.json"
    for start in (1, 61, 121, 181, 241, 301)
)
DISCOURSE_FAMILIES = p01.DISCOURSE_FAMILIES
FORBIDDEN_THERE_BE = re.compile(r"\bthere\s+(?:is|are)\b", re.IGNORECASE)
FORBIDDEN_PAST_BE = re.compile(r"\b(?:was|were)\b", re.IGNORECASE)
PRESENT_CONTINUOUS_SHAPE = re.compile(r"\b(?:am|is|are)\s+([A-Za-z]+ing)\b", re.IGNORECASE)


class U05Current360MaterializationError(ValueError):
    pass


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _sentence_count(text: str) -> int:
    return len(re.findall(r"[^.!?]+[.!?]", text))


def _load_shard(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05Current360MaterializationError(f"DATA_SHARD_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U05Current360MaterializationError(f"DATA_SHARD_NOT_OBJECT:{path}")
    if value.get("learner_facing_language_author") != "GPT-5.6 Sol":
        raise U05Current360MaterializationError(f"AUTHOR_DRIFT:{path}")
    if value.get("python_may_generate_or_rewrite_learner_facing_english") is not False:
        raise U05Current360MaterializationError(f"PYTHON_AUTHORING_NOT_DISABLED:{path}")
    return value


def build_report() -> dict[str, Any]:
    projection = p01.build_unit05_natural360_source_projection()
    slots = list(projection["episode_authoring_slots"])
    clusters = {row["cluster_id"]: row for row in projection["source_clusters"]}

    shards = [_load_shard(path) for path in DATA_PATHS]
    episodes = [row for shard in shards for row in shard["episodes"]]
    if len(episodes) != 360:
        raise U05Current360MaterializationError(f"EPISODE_COUNT_DRIFT:{len(episodes)}")

    if len({row["episode_id"] for row in episodes}) != 360:
        raise U05Current360MaterializationError("EPISODE_ID_COLLISION")
    if len({row["episode_slot_id"] for row in episodes}) != 360:
        raise U05Current360MaterializationError("EPISODE_SLOT_ID_COLLISION")
    if len({_normalise(row["paragraph"]) for row in episodes}) != 360:
        raise U05Current360MaterializationError("PARAGRAPH_DUPLICATE")

    per_cluster = Counter()
    sentence_counts: list[int] = []
    for index, (episode, slot) in enumerate(zip(episodes, slots), start=1):
        expected_episode_id = f"U05-NEB-E{index:03d}"
        expected_slot_id = f"U05-N360-S{index:03d}"
        if episode["episode_id"] != expected_episode_id:
            raise U05Current360MaterializationError(
                f"EPISODE_ID_ORDER_DRIFT:{episode['episode_id']}:{expected_episode_id}"
            )
        if episode["episode_slot_id"] != expected_slot_id:
            raise U05Current360MaterializationError(
                f"SLOT_ID_ORDER_DRIFT:{episode['episode_slot_id']}:{expected_slot_id}"
            )
        if episode["cluster_id"] != slot["cluster_id"]:
            raise U05Current360MaterializationError(
                f"CLUSTER_LINEAGE_DRIFT:{episode['episode_id']}"
            )
        if episode["discourse_family"] != slot["discourse_family"]:
            raise U05Current360MaterializationError(
                f"DISCOURSE_FAMILY_DRIFT:{episode['episode_id']}"
            )
        if episode["scene_family"] != slot["scene_family"]:
            raise U05Current360MaterializationError(
                f"SCENE_FAMILY_DRIFT:{episode['episode_id']}"
            )
        refs = list(episode.get("source_scene_refs") or [])
        if not refs:
            raise U05Current360MaterializationError(
                f"SOURCE_SCENE_LINEAGE_EMPTY:{episode['episode_id']}"
            )
        allowed_refs = set(clusters[episode["cluster_id"]]["source_scene_refs"])
        if not set(refs).issubset(allowed_refs):
            raise U05Current360MaterializationError(
                f"SOURCE_SCENE_LINEAGE_INVALID:{episode['episode_id']}"
            )

        if episode.get("author_model") != "GPT-5.6 Sol":
            raise U05Current360MaterializationError(
                f"EPISODE_AUTHOR_DRIFT:{episode['episode_id']}"
            )
        if episode.get("gpt56_semantic_review") != "PASS":
            raise U05Current360MaterializationError(
                f"SEMANTIC_REVIEW_NOT_PASS:{episode['episode_id']}"
            )

        paragraph = str(episode["paragraph"]).strip()
        count = _sentence_count(paragraph)
        sentence_counts.append(count)
        if not 5 <= count <= 8:
            raise U05Current360MaterializationError(
                f"PARAGRAPH_SENTENCE_COUNT_OUT_OF_RANGE:{episode['episode_id']}:{count}"
            )
        if "?" in paragraph:
            raise U05Current360MaterializationError(
                f"BE_INTERROGATIVE_LEAKAGE:{episode['episode_id']}"
            )
        if FORBIDDEN_THERE_BE.search(paragraph):
            raise U05Current360MaterializationError(
                f"EXISTENTIAL_THERE_BE_LEAKAGE:{episode['episode_id']}"
            )
        if FORBIDDEN_PAST_BE.search(paragraph):
            raise U05Current360MaterializationError(
                f"PAST_BE_LEAKAGE:{episode['episode_id']}"
            )
        continuous_hits = [
            match.group(1).casefold()
            for match in PRESENT_CONTINUOUS_SHAPE.finditer(paragraph)
            if match.group(1).casefold() != "morning"
        ]
        if continuous_hits:
            raise U05Current360MaterializationError(
                f"PRESENT_CONTINUOUS_LEAKAGE:{episode['episode_id']}:{continuous_hits}"
            )
        per_cluster[episode["cluster_id"]] += 1

    if len(per_cluster) != 36 or set(per_cluster.values()) != {10}:
        raise U05Current360MaterializationError(
            f"CLUSTER_DISTRIBUTION_DRIFT:{dict(sorted(per_cluster.items()))}"
        )

    return {
        "schema_version": "a1fs.v1.u05.r360.current360_gpt56_materialization.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "learner_facing_language_author": "GPT-5.6 Sol",
        "python_may_generate_or_rewrite_learner_facing_english": False,
        "source_projection_task_id": projection["task_id"],
        "source_projection_status": projection["status"],
        "episode_count": len(episodes),
        "source_cluster_count": len(per_cluster),
        "episodes_per_cluster": 10,
        "discourse_family_count": len(DISCOURSE_FAMILIES),
        "sentence_count_min": min(sentence_counts),
        "sentence_count_max": max(sentence_counts),
        "unique_paragraph_count": len({_normalise(row["paragraph"]) for row in episodes}),
        "source_scene_lineage_valid": True,
        "gpt56_semantic_review_pass_count": sum(
            row["gpt56_semantic_review"] == "PASS" for row in episodes
        ),
        "scope_safety": {
            "python_generated_learner_facing_english": False,
            "python_rewrote_learner_facing_english": False,
            "q01_q09_modified": False,
            "old_q10_promoted_to_active_runtime": False,
            "spoken360_materialized": False,
            "pattern360_materialized": False,
            "contextual_active_runtime_materialized": False,
            "pdf_materialized": False,
            "be_interrogative_mastery_unlocked": False,
            "past_be_unlocked": False,
            "existential_there_be_unlocked": False,
            "present_continuous_mastery_unlocked": False,
            "a2_a2plus_unlocked": False,
        },
        "episodes": episodes,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    report = build_report()
    print(f"STATUS={report['status']}")
    print(f"EPISODES={report['episode_count']}")
    print(f"CLUSTERS={report['source_cluster_count']}")
    print(f"EPISODES_PER_CLUSTER={report['episodes_per_cluster']}")
    print(f"SENTENCE_RANGE={report['sentence_count_min']}-{report['sentence_count_max']}")
    print(f"UNIQUE_PARAGRAPHS={report['unique_paragraph_count']}")
    print(f"GPT56_REVIEW_PASS={report['gpt56_semantic_review_pass_count']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
