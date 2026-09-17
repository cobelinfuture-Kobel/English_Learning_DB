from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as neb360

TASK_ID = "A1FS-V1-U04FL01_Unit04FunctionalLanguageCoreAndCurrent360ProductiveBridge"
STATUS = "PASS_A1FS_V1_U04FL01_CURRENT360_PRODUCTIVE_BRIDGE"
REVISION = "CURRENT360_GPT5_6_OPTIONAL_FUNCTIONAL_LANGUAGE_ROUTING_V1_2"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Consumes the authored Unit04 functional-language surface pool, Q08 semantic communicative-function "
    "authority, approved Q05 frame routing, and merged Current360. Python preserves candidate pools and "
    "validates authority identity only; GPT-5.6 performs episode-level semantic selection later. Python "
    "must not force, select, compose, paraphrase, repair, or rewrite learner-facing English."
)

FUNCTIONAL_CORE_PATH = "ulga/contracts/a1fs_v1_u04_fl01_functional_language_core.json"
Q05_PATH = "ulga/contracts/a1fs_v1_u04_q05_core_sentence_frame_authority.json"
Q08_PATH = "ulga/contracts/a1fs_v1_u04_q08_communicative_function_authority.json"
FUNCTIONAL_CORE_STATUS = "PASS_U04FL01_FUNCTIONAL_LANGUAGE_CORE"
Q05_STATUS = "PASS_Q05_UNIT04_CORE_SENTENCE_FRAME_AUTHORITY"
Q08_STATUS = "PASS_Q08_UNIT04_COMMUNICATIVE_FUNCTION_AUTHORITY"
EXPECTED_EPISODE_COUNT = 360
Q08_FUNCTION_IDS = (
    "U04-CF01_STATE_ENTITY_LOCATION",
    "U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION",
    "U04-CF03_IDENTIFY_ENTITY_BY_LOCATION",
    "U04-CF04_CONFIRM_LOCATION_RELATION",
    "U04-CF05_DESCRIBE_SPATIAL_SCENE",
    "U04-CF06_DISTINGUISH_SPATIAL_RELATION",
)
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


def build_unit04_current360_productive_bridge(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    core = _load_json(root / FUNCTIONAL_CORE_PATH)
    q05 = _load_json(root / Q05_PATH)
    q08 = _load_json(root / Q08_PATH)

    if core.get("status") != FUNCTIONAL_CORE_STATUS:
        raise Unit04FunctionalBridgeError("functional_core_status_drift")
    if q05.get("status") != Q05_STATUS:
        raise Unit04FunctionalBridgeError("q05_status_drift")
    if q08.get("status") != Q08_STATUS:
        raise Unit04FunctionalBridgeError("q08_status_drift")
    binding = core.get("q08_semantic_authority_binding", {})
    if binding.get("semantic_communicative_function_authority_remains_q08_only") is not True:
        raise Unit04FunctionalBridgeError("parallel_communicative_authority_not_blocked")

    contract = core.get("current360_bridge_contract", {})
    if contract.get("functional_selection_authority") != "GPT5_6_EPISODE_SEMANTIC_REVIEW":
        raise Unit04FunctionalBridgeError("gpt5_6_selection_authority_missing")
    if contract.get("minimum_selected_functional_chunks_per_episode") != 0:
        raise Unit04FunctionalBridgeError("functional_minimum_must_be_zero")
    if contract.get("python_must_not_auto_select_functional_chunks_from_relation_labels") is not True:
        raise Unit04FunctionalBridgeError("python_auto_selection_not_blocked")

    chunks = {row["chunk_id"]: dict(row) for row in core.get("functional_chunks", [])}
    dialogues = {row["dialogue_id"]: dict(row) for row in core.get("dialogue_skeletons", [])}
    ladders = {row["ladder_id"]: dict(row) for row in core.get("production_ladders", [])}
    moves = {row["move_id"]: dict(row) for row in core.get("functional_moves", [])}
    q08_functions = {row["function_id"]: dict(row) for row in q08.get("communicative_functions", [])}

    if len(chunks) != 24:
        raise Unit04FunctionalBridgeError("functional_chunk_count_drift")
    if set(DIALOGUE_IDS) != set(dialogues):
        raise Unit04FunctionalBridgeError("dialogue_identity_drift")
    if set(LADDER_IDS) != set(ladders):
        raise Unit04FunctionalBridgeError("ladder_identity_drift")
    if len(moves) != 12:
        raise Unit04FunctionalBridgeError("functional_move_count_drift")
    if set(q08_functions) != set(Q08_FUNCTION_IDS):
        raise Unit04FunctionalBridgeError("q08_function_identity_drift")
    for row in list(moves.values()) + list(chunks.values()):
        if not set(row.get("q08_function_refs", [])).issubset(q08_functions):
            raise Unit04FunctionalBridgeError("functional_surface_q08_ref_invalid")

    q05_routes = {
        **q05["q06_primary_generation_routing"].get("target_relations", {}),
        **q05["q06_primary_generation_routing"].get("support_relations", {}),
    }

    current = neb360.build_unit04_neb02_natural_episode_bank_360(root)
    if current.get("status") != neb360.STATUS:
        raise Unit04FunctionalBridgeError("current360_status_drift")
    episodes = [dict(row) for row in current.get("effective_episodes", [])]
    if len(episodes) != EXPECTED_EPISODE_COUNT:
        raise Unit04FunctionalBridgeError(f"current360_count_drift:{len(episodes)}")

    chunk_candidate_pool = list(chunks)
    q08_candidate_pool = list(Q08_FUNCTION_IDS)
    dialogue_candidate_pool = list(DIALOGUE_IDS)
    ladder_candidate_pool = list(LADDER_IDS)
    ket_candidate_pool = list(KET_SEED_ROUTES)

    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for episode in episodes:
        declared = [part.strip() for part in str(episode["target_relations"]).split(",") if part.strip()]
        frame_routes = [
            {"relation_surface": relation, "frame_id": q05_routes[relation]}
            for relation in declared
            if relation in q05_routes
        ]
        if not frame_routes:
            raise Unit04FunctionalBridgeError(f"episode_without_q05_frame_route:{episode['episode_id']}")

        passage = str(episode["passage"])
        row = {
            "episode_id": episode["episode_id"],
            "micro_scene_id": episode["micro_scene_id"],
            "life_domain": episode["life_domain"],
            "governed_scene_family": episode["governed_scene_family"],
            "target_relations": declared,
            "passage": passage,
            "passage_sha256": _sha_text(passage),
            "q05_sentence_frame_routes": frame_routes,
            "q08_communicative_function_refs": [],
            "q08_communicative_function_candidate_pool": q08_candidate_pool,
            "functional_chunk_refs": [],
            "functional_chunk_candidate_pool": chunk_candidate_pool,
            "dialogue_skeleton_refs": [],
            "dialogue_skeleton_candidate_pool": dialogue_candidate_pool,
            "production_ladder_refs": [],
            "production_ladder_candidate_pool": ladder_candidate_pool,
            "ket_seed_routes": [],
            "ket_seed_candidate_routes": ket_candidate_pool,
            "functional_selection_status": "PENDING_GPT5_6_EPISODE_SEMANTIC_REVIEW",
            "functional_selection_contract": {
                "selection_authority": "GPT5_6_EPISODE_SEMANTIC_REVIEW",
                "minimum_selected_functional_chunks": 0,
                "fixed_quota": False,
                "no_selection_is_valid": True,
                "selection_must_be_contextually_justified": True,
                "relation_label_must_not_trigger_automatic_insertion": True,
            },
            "productive_sequence": [
                "RECOGNIZE_WORDS_IN_EPISODE",
                "RETRIEVE_SPATIAL_CHUNK",
                "COMPLETE_Q05_SENTENCE_FRAME",
                "OPTIONALLY_USE_GPT5_6_SELECTED_FUNCTIONAL_LANGUAGE",
                "OPTIONALLY_RUN_NATURAL_SHORT_INTERACTION",
                "OPTIONALLY_PERSONAL_TRANSFER",
                "OPTIONALLY_KET_STYLE_TRANSFER",
            ],
            "language_generation_policy": {
                "current360_passage_rewritten": False,
                "python_composed_learner_english": False,
                "python_selected_functional_language": False,
                "semantic_communicative_function_authority": Q08_PATH,
                "functional_english_source": FUNCTIONAL_CORE_PATH,
                "episode_semantics_source": "CURRENT360_EXISTING_PASSAGE_AND_DECLARED_RELATIONS",
                "episode_specific_functional_selection_materialized": False,
                "episode_specific_instantiated_dialogue_materialized": False,
            },
        }
        rows.append(row)
        counts["episodes_with_q05_frame_routes"] += 1
        counts["episodes_pending_gpt5_6_functional_selection"] += 1

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
            "communicative_function_count": len(q08_functions),
            "q08_communicative_function_authority_count": len(q08_functions),
            "functional_move_count": len(moves),
            "dialogue_skeleton_count": len(dialogues),
            "production_ladder_count": len(ladders),
            **counts,
            "minimum_selected_functional_chunks_per_episode": 0,
            "episodes_with_selected_q08_functions": 0,
            "episodes_with_selected_functional_chunks": 0,
            "episodes_with_selected_dialogue_skeletons": 0,
            "episodes_with_selected_production_ladders": 0,
            "episodes_with_selected_ket_seed_routes": 0,
            "episode_specific_functional_selection_count": 0,
            "episode_specific_instantiated_dialogue_count": 0,
            "current360_passage_rewrite_count": 0,
            "python_composed_learner_english_count": 0,
            "python_selected_functional_language_count": 0,
        },
        "functional_language_core": {
            "surface_authority_ref": FUNCTIONAL_CORE_PATH,
            "semantic_authority_ref": Q08_PATH,
            "selection_authority": "GPT5_6_EPISODE_SEMANTIC_REVIEW",
            "functional_moves": list(moves.values()),
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
            "q08_semantic_authority_modified": False,
            "parallel_communicative_function_authority_created": False,
            "current360_passages_modified": False,
            "functional_chunks_forced_into_current360": False,
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
