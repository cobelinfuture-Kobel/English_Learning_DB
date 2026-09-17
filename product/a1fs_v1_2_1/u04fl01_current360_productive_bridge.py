from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as neb360


TASK_ID = "A1FS-V1-U04FL01_Unit04FunctionalLanguageCoreAndCurrent360ProductiveBridge"
STATUS = "PASS_A1FS_V1_U04FL01_CURRENT360_PRODUCTIVE_BRIDGE"
REVISION = "CURRENT360_FUNCTIONAL_LANGUAGE_PRODUCTIVE_ROUTING_V1"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Consumes the authored Unit04 functional-language core, approved Q05 frame routing, "
    "and merged Current360. Python only validates and attaches authority references; "
    "it does not compose, paraphrase, repair, or rewrite learner-facing English."
)

FUNCTIONAL_CORE_PATH = "ulga/contracts/a1fs_v1_u04_fl01_functional_language_core.json"
Q05_PATH = "ulga/contracts/a1fs_v1_u04_q05_core_sentence_frame_authority.json"
FUNCTIONAL_CORE_STATUS = "PASS_U04FL01_FUNCTIONAL_LANGUAGE_CORE"
Q05_STATUS = "PASS_Q05_UNIT04_CORE_SENTENCE_FRAME_AUTHORITY"
EXPECTED_EPISODE_COUNT = 360

BASE_FUNCTIONAL_CHUNK_IDS = (
    "U04-FL-ASK-01",
    "U04-FL-ASK-02",
    "U04-FL-ASK-03",
    "U04-FL-REPORT-01",
    "U04-FL-SEARCH-01",
    "U04-FL-SEARCH-02",
    "U04-FL-HELP-01",
    "U04-FL-HELP-02",
    "U04-FL-CHECK-01",
    "U04-FL-CHECK-02",
    "U04-FL-VERIFY-01",
    "U04-FL-UNCERTAIN-01",
    "U04-FL-CONFIRM-01",
    "U04-FL-CONFIRM-02",
    "U04-FL-DISCOVER-01",
    "U04-FL-DISCOVER-02",
    "U04-FL-PERSONAL-01",
    "U04-FL-PERSONAL-02",
)
RELATION_SUPPORT_CHUNKS = {
    "under": "U04-FL-ATTEND-03",
    "behind": "U04-FL-ATTEND-04",
    "in": "U04-FL-ATTEND-05",
}
DIALOGUE_IDS = (
    "U04-DLG-SEARCH-HELP",
    "U04-DLG-LOCATE-CHECK",
    "U04-DLG-THINK-CHECK",
    "U04-DLG-DISCOVER",
    "U04-DLG-PERSONAL",
)
LADDER_IDS = ("U04-LADDER-LOCATION", "U04-LADDER-SEARCH")
KET_SEED_ROUTES = (
    "SHORT_DIALOGUE_COMPLETION",
    "CONNECTED_TEXT_LOCATION_COMPREHENSION",
    "PERSONAL_LOCATION_RESPONSE",
)


class Unit04FunctionalBridgeError(ValueError):
    pass


def _root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Unit04FunctionalBridgeError(f"missing:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Unit04FunctionalBridgeError(f"not_object:{path}")
    return value


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_unit04_current360_productive_bridge(
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    root = _root(repo_root)
    core = _load_json(root / FUNCTIONAL_CORE_PATH)
    q05 = _load_json(root / Q05_PATH)

    if core.get("status") != FUNCTIONAL_CORE_STATUS:
        raise Unit04FunctionalBridgeError("functional_core_status_drift")
    if q05.get("status") != Q05_STATUS:
        raise Unit04FunctionalBridgeError("q05_status_drift")

    chunks = {row["chunk_id"]: dict(row) for row in core.get("functional_chunks", [])}
    dialogues = {row["dialogue_id"]: dict(row) for row in core.get("dialogue_skeletons", [])}
    ladders = {row["ladder_id"]: dict(row) for row in core.get("production_ladders", [])}
    functions = {row["function_id"]: dict(row) for row in core.get("communicative_functions", [])}

    required_chunk_ids = set(BASE_FUNCTIONAL_CHUNK_IDS) | set(RELATION_SUPPORT_CHUNKS.values())
    if not required_chunk_ids.issubset(chunks):
        raise Unit04FunctionalBridgeError("functional_chunk_identity_missing")
    if set(DIALOGUE_IDS) != set(dialogues):
        raise Unit04FunctionalBridgeError("dialogue_identity_drift")
    if set(LADDER_IDS) != set(ladders):
        raise Unit04FunctionalBridgeError("ladder_identity_drift")
    if len(functions) != 12:
        raise Unit04FunctionalBridgeError("communicative_function_count_drift")

    routes = {
        **q05["q06_primary_generation_routing"].get("target_relations", {}),
        **q05["q06_primary_generation_routing"].get("support_relations", {}),
    }

    current = neb360.build_unit04_neb02_natural_episode_bank_360(root)
    if current.get("status") != neb360.STATUS:
        raise Unit04FunctionalBridgeError("current360_status_drift")
    episodes = [dict(row) for row in current.get("effective_episodes", [])]
    if len(episodes) != EXPECTED_EPISODE_COUNT:
        raise Unit04FunctionalBridgeError(f"current360_count_drift:{len(episodes)}")

    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for episode in episodes:
        declared = [part.strip() for part in str(episode["target_relations"]).split(",") if part.strip()]
        frame_routes = [
            {"relation_surface": relation, "frame_id": routes[relation]}
            for relation in declared
            if relation in routes
        ]
        if not frame_routes:
            raise Unit04FunctionalBridgeError(
                f"episode_without_q05_frame_route:{episode['episode_id']}"
            )

        functional_ids = list(BASE_FUNCTIONAL_CHUNK_IDS)
        for relation in declared:
            support_id = RELATION_SUPPORT_CHUNKS.get(relation)
            if support_id and support_id not in functional_ids:
                functional_ids.append(support_id)

        if "U04-FL-PERSONAL-01" not in functional_ids or "U04-FL-PERSONAL-02" not in functional_ids:
            raise Unit04FunctionalBridgeError("personal_transfer_route_missing")

        passage = str(episode["passage"])
        row = {
            "episode_id": episode["episode_id"],
            "micro_scene_id": episode["micro_scene_id"],
            "life_domain": episode["life_domain"],
            "governed_scene_family": episode["governed_scene_family"],
            "target_relations": declared,
            "passage": passage,
            "passage_sha256": _sha_text(passage),
            "functional_chunk_refs": functional_ids,
            "q05_sentence_frame_routes": frame_routes,
            "dialogue_skeleton_refs": list(DIALOGUE_IDS),
            "production_ladder_refs": list(LADDER_IDS),
            "ket_seed_routes": list(KET_SEED_ROUTES),
            "productive_sequence": [
                "RECOGNIZE_WORDS_IN_EPISODE",
                "RETRIEVE_SPATIAL_CHUNK",
                "COMPLETE_Q05_SENTENCE_FRAME",
                "USE_FUNCTIONAL_CHUNK",
                "RUN_SHORT_DIALOGUE",
                "PERSONAL_TRANSFER",
                "KET_STYLE_TRANSFER"
            ],
            "language_generation_policy": {
                "current360_passage_rewritten": False,
                "python_composed_learner_english": False,
                "functional_english_source": FUNCTIONAL_CORE_PATH,
                "episode_semantics_source": "CURRENT360_EXISTING_PASSAGE_AND_DECLARED_RELATIONS",
            },
        }
        rows.append(row)
        counts["episodes_with_functional_routes"] += 1
        counts["episodes_with_q05_frame_routes"] += 1
        counts["episodes_with_dialogue_routes"] += 1
        counts["episodes_with_personal_transfer"] += 1
        counts["episodes_with_ket_seed_routes"] += 1

    if len({row["episode_id"] for row in rows}) != EXPECTED_EPISODE_COUNT:
        raise Unit04FunctionalBridgeError("duplicate_episode_id")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "unit_number": 4,
        "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "goal_chain": list(core["goal_chain"]),
        "summary": {
            "episode_count": len(rows),
            "functional_chunk_authority_count": len(chunks),
            "communicative_function_count": len(functions),
            "dialogue_skeleton_count": len(dialogues),
            "production_ladder_count": len(ladders),
            **counts,
            "current360_passage_rewrite_count": 0,
            "python_composed_learner_english_count": 0,
        },
        "functional_language_core": {
            "authority_ref": FUNCTIONAL_CORE_PATH,
            "functional_chunks": list(chunks.values()),
            "dialogue_skeletons": list(dialogues.values()),
            "production_ladders": list(ladders.values()),
        },
        "episode_productive_routes": rows,
        "scope_safety": {
            "q03_modified": False,
            "q04_spatial_chunks_modified": False,
            "q05_modified": False,
            "q06_modified": False,
            "q07_modified": False,
            "current360_passages_modified": False,
            "form01_20_modified": False,
            "unit05_plus_opened": False,
            "a2_a2plus_unlocked": False,
        },
    }


def main() -> int:
    print(json.dumps(build_unit04_current360_productive_bridge(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
