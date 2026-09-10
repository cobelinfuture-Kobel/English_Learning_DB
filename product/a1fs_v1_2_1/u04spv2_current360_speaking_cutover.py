from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping

from product.a1fs_v1_2_1 import (
    u04fsv2_current360_contextual_form_runtime as fsv2,
)
from product.a1fs_v1_2_1 import (
    u04sp01_current360_speaking_layer_acceptance as sp01,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
TASK_ID = "A1FS-V1-U04SPV2_SpeakingLayer1BridgeLayer2Cutover"
STATUS = "PASS_A1FS_V1_U04SPV2_SPEAKING_LAYER1_BRIDGE_LAYER2_CUTOVER"
REVISION = "CURRENT360_FORM_BOUND_SPEAKING_PROGRESSION_V2"
NEXT_SHORT_STEP = "A1FS-V1-U04RSWV2_ProductiveScoringAndCambridgeProgressionAcceptance"

FORM_COUNT = 20
BRIDGE_TASKS_PER_FORM = 4
LAYER2_TASKS_PER_FORM = 8
BRIDGE_TASK_COUNT = FORM_COUNT * BRIDGE_TASKS_PER_FORM
LAYER2_TASK_COUNT = FORM_COUNT * LAYER2_TASKS_PER_FORM

BRIDGE_MODES = (
    "CUE_TO_SENTENCE",
    "LOCATION_QA",
    "ASK_WHERE_QUESTION",
    "TWO_SENTENCE_CHAIN",
)

LAYER2_MODES = (
    "LOCATION_QA",
    "TWO_FACT_CHAIN",
    "ASK_AND_ANSWER",
    "SCENE_DESCRIPTION",
    "SHORT_RETELL",
    "DIALOGUE_FOLLOW_UP",
    "REPAIR_CLARIFY",
    "TRANSFER_CHANGED_LOCATION",
)

SPEAKING_PROMPTS = {
    "CUE_TO_SENTENCE": (
        "Use the passage and the place word. Say one complete location sentence that is true."
    ),
    "LOCATION_QA": (
        "Answer: Where is one person or thing in the passage? Use one complete sentence."
    ),
    "ASK_WHERE_QUESTION": (
        "Ask one Where question about a person or thing in the passage."
    ),
    "TWO_SENTENCE_CHAIN": (
        "Say two short location facts from the passage. Join them with and if it sounds natural."
    ),
    "TWO_FACT_CHAIN": (
        "Tell two location facts from the passage in two connected sentences."
    ),
    "ASK_AND_ANSWER": (
        "Ask one Where question about the passage, then answer it in a complete sentence."
    ),
    "SCENE_DESCRIPTION": (
        "Describe the scene in three short sentences. Include at least two location facts."
    ),
    "SHORT_RETELL": (
        "Retell the situation in two or three short sentences. Keep the location facts true."
    ),
    "DIALOGUE_FOLLOW_UP": (
        "Take turns. Ask a Where question, answer it, then ask one follow-up question."
    ),
    "REPAIR_CLARIFY": (
        "Say one location fact. If your partner asks 'Where?', say the location again more clearly."
    ),
    "TRANSFER_CHANGED_LOCATION": (
        "Change one location in the scene. Say what is different, then add one more sentence about the new scene."
    ),
}

STAGE_SUPPORT = {
    "GUIDED": "You may read the passage once and use one sentence as a model.",
    "REDUCED_SUPPORT": "Use the passage, but make your own complete answer.",
    "INDEPENDENT": "Read the passage, then speak without copying a full sentence.",
    "TRANSFER": "Use the new passage. Plan briefly, then speak.",
    "RETENTION": "Use what you know. Speak without a model sentence.",
}

SPEAKING_SCORING_DIMENSIONS = (
    "semantic_truth",
    "a1_grammar_target",
    "completeness",
    "reference_continuity",
    "interactional_fit",
    "question_formation",
    "clarification_repair",
    "intelligibility_human_review",
)

MODE_REQUIRED_DIMENSIONS = {
    "CUE_TO_SENTENCE": ("semantic_truth", "a1_grammar_target", "completeness"),
    "LOCATION_QA": ("semantic_truth", "a1_grammar_target", "completeness"),
    "ASK_WHERE_QUESTION": ("a1_grammar_target", "question_formation"),
    "TWO_SENTENCE_CHAIN": (
        "semantic_truth",
        "a1_grammar_target",
        "reference_continuity",
    ),
    "TWO_FACT_CHAIN": (
        "semantic_truth",
        "a1_grammar_target",
        "reference_continuity",
    ),
    "ASK_AND_ANSWER": (
        "semantic_truth",
        "a1_grammar_target",
        "question_formation",
        "interactional_fit",
    ),
    "SCENE_DESCRIPTION": (
        "semantic_truth",
        "a1_grammar_target",
        "completeness",
        "reference_continuity",
    ),
    "SHORT_RETELL": (
        "semantic_truth",
        "a1_grammar_target",
        "completeness",
        "reference_continuity",
    ),
    "DIALOGUE_FOLLOW_UP": (
        "semantic_truth",
        "a1_grammar_target",
        "question_formation",
        "interactional_fit",
    ),
    "REPAIR_CLARIFY": (
        "semantic_truth",
        "a1_grammar_target",
        "clarification_repair",
        "interactional_fit",
    ),
    "TRANSFER_CHANGED_LOCATION": (
        "a1_grammar_target",
        "completeness",
        "reference_continuity",
    ),
}


class Unit04SPV2Error(ValueError):
    pass


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _scoring(mode: str) -> dict[str, Any]:
    required = MODE_REQUIRED_DIMENSIONS[mode]
    return {
        "scoring_mode": "HUMAN_OR_SEMANTIC_REVIEW",
        "single_answer_required": False,
        "acceptable_paraphrase": True,
        "reference_response_nonexclusive": True,
        "dimensions": list(SPEAKING_SCORING_DIMENSIONS),
        "required_dimensions": list(required),
        "audio_pronunciation_machine_score_required": False,
    }


def _validate_sources() -> tuple[dict[str, Any], dict[str, Any]]:
    form_report = fsv2.build_unit04_fsv2_current360_contextual_form_runtime()
    if form_report.get("status") != fsv2.STATUS:
        raise Unit04SPV2Error("FSV2_SOURCE_NOT_PASS")
    if (
        form_report.get("cutover_contract", {}).get("active_form_runtime_authority")
        != fsv2.TASK_ID
    ):
        raise Unit04SPV2Error("FSV2_NOT_ACTIVE_FORM_RUNTIME")
    if form_report.get("materialization_contract", {}).get("form_count") != FORM_COUNT:
        raise Unit04SPV2Error("FSV2_FORM_COUNT_DRIFT")
    if len(form_report.get("active_items") or []) != 800:
        raise Unit04SPV2Error("FSV2_ACTIVE_ITEM_COUNT_DRIFT")

    speaking_report = sp01.build_unit04_current360_speaking_layer_acceptance()
    if speaking_report.get("status") != sp01.STATUS:
        raise Unit04SPV2Error("SP01_SOURCE_NOT_PASS")
    layer1 = speaking_report.get("layer1_atomic_speaking_pool") or []
    if len(layer1) != 121:
        raise Unit04SPV2Error("SP01_LAYER1_COUNT_DRIFT")
    return form_report, speaking_report


def _form_d_items(
    form_report: Mapping[str, Any], form_number: int
) -> list[dict[str, Any]]:
    rows = [
        dict(row)
        for row in form_report.get("active_items") or []
        if int(row["form_number"]) == form_number and row["section"] == "D"
    ]
    rows.sort(key=lambda row: int(row["section_activity_ordinal"]))
    if len(rows) != 8:
        raise Unit04SPV2Error(
            f"FORM_D_ITEM_COUNT_DRIFT:{form_number}:{len(rows)}"
        )
    return rows


def _learner_task(
    *,
    layer: str,
    mode: str,
    source_item: Mapping[str, Any],
    ordinal: int,
) -> dict[str, Any]:
    lineage = dict(source_item.get("current360_episode_lineage") or {})
    passage = str(lineage.get("passage") or "").strip()
    if not passage:
        raise Unit04SPV2Error(
            f"CURRENT360_PASSAGE_MISSING:{source_item.get('active_item_id')}"
        )
    stage = str(source_item["progression_stage"])
    if stage not in STAGE_SUPPORT:
        raise Unit04SPV2Error(f"UNKNOWN_STAGE:{stage}")
    relation = str(source_item["target_relation_surface"])
    if relation not in fsv2.TARGET_RELATIONS:
        raise Unit04SPV2Error(f"OUT_OF_SCOPE_TARGET_RELATION:{relation}")

    identity = {
        "layer": layer,
        "mode": mode,
        "form_number": int(source_item["form_number"]),
        "ordinal": ordinal,
        "source_active_item_id": str(source_item["active_item_id"]),
        "episode_id": str(lineage.get("episode_id") or ""),
        "relation": relation,
        "revision": REVISION,
    }
    task_id = (
        f"U04SPV2-F{int(source_item['form_number']):02d}-{layer}-"
        f"{ordinal:02d}-{_digest(identity)[:12].upper()}"
    )
    return {
        "speaking_task_id": task_id,
        "form_number": int(source_item["form_number"]),
        "progression_stage": stage,
        "support_level": str(source_item["support_level"]),
        "context_exposure": str(source_item["context_exposure"]),
        "layer": layer,
        "speaking_mode": mode,
        "learner_stimulus": {
            "passage": passage,
            "place_word": (
                relation if layer == "BRIDGE" and mode == "CUE_TO_SENTENCE" else None
            ),
            "support": STAGE_SUPPORT[stage],
        },
        "learner_prompt": SPEAKING_PROMPTS[mode],
        "scoring_contract": _scoring(mode),
        "target_relation_surface": relation,
        "target_relation_role": "ASSESSED_A1_UNIT04_TARGET",
        "support_relations_assessed": False,
        "current360_episode_lineage": lineage,
        "source_form_runtime_lineage": {
            "fsv2_active_item_id": str(source_item["active_item_id"]),
            "source_q10_item_id": str(
                source_item["source_q10_lineage"]["source_q10_item_id"]
            ),
            "source_task_family_id": str(
                source_item["source_q10_lineage"]["source_task_family_id"]
            ),
            "communicative_function_id": str(
                source_item["communicative_function_id"]
            ),
            "section": str(source_item["section"]),
            "section_activity_ordinal": int(source_item["section_activity_ordinal"]),
        },
        "a1_grammar_ceiling": True,
        "a2_grammar_introduced": False,
        "passage_split_as_model_utterances": False,
    }


def _materialize() -> dict[str, Any]:
    form_report, speaking_report = _validate_sources()
    layer1 = [dict(row) for row in speaking_report["layer1_atomic_speaking_pool"]]

    bridge_tasks: list[dict[str, Any]] = []
    layer2_tasks: list[dict[str, Any]] = []
    bridge_mode_counts: Counter[str] = Counter()
    layer2_mode_counts: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    scene_ids: set[str] = set()
    life_domains: set[str] = set()
    seen_episode_ids: set[str] = set()
    unseen_episode_ids: set[str] = set()

    for form_number in range(1, FORM_COUNT + 1):
        d_items = _form_d_items(form_report, form_number)

        for index, mode in enumerate(BRIDGE_MODES, start=1):
            task = _learner_task(
                layer="BRIDGE",
                mode=mode,
                source_item=d_items[index - 1],
                ordinal=index,
            )
            bridge_tasks.append(task)
            bridge_mode_counts[mode] += 1

        for index, mode in enumerate(LAYER2_MODES, start=1):
            source_item = d_items[index - 1]
            task = _learner_task(
                layer="LAYER2",
                mode=mode,
                source_item=source_item,
                ordinal=index,
            )
            layer2_tasks.append(task)
            layer2_mode_counts[mode] += 1
            relation_counts[task["target_relation_surface"]] += 1
            lineage = task["current360_episode_lineage"]
            scene_ids.add(str(lineage["micro_scene_id"]))
            life_domains.add(str(lineage["life_domain"]))
            if str(task["context_exposure"]).startswith("UNSEEN"):
                unseen_episode_ids.add(str(lineage["episode_id"]))
            else:
                seen_episode_ids.add(str(lineage["episode_id"]))

    if len(bridge_tasks) != BRIDGE_TASK_COUNT:
        raise Unit04SPV2Error(f"BRIDGE_TASK_COUNT_DRIFT:{len(bridge_tasks)}")
    if len(layer2_tasks) != LAYER2_TASK_COUNT:
        raise Unit04SPV2Error(f"LAYER2_TASK_COUNT_DRIFT:{len(layer2_tasks)}")
    if len({row["speaking_task_id"] for row in bridge_tasks + layer2_tasks}) != (
        BRIDGE_TASK_COUNT + LAYER2_TASK_COUNT
    ):
        raise Unit04SPV2Error("SPEAKING_TASK_ID_COLLISION")
    if dict(bridge_mode_counts) != {mode: FORM_COUNT for mode in BRIDGE_MODES}:
        raise Unit04SPV2Error(
            f"BRIDGE_MODE_DISTRIBUTION_DRIFT:{dict(bridge_mode_counts)}"
        )
    if dict(layer2_mode_counts) != {mode: FORM_COUNT for mode in LAYER2_MODES}:
        raise Unit04SPV2Error(
            f"LAYER2_MODE_DISTRIBUTION_DRIFT:{dict(layer2_mode_counts)}"
        )
    if set(relation_counts) != set(fsv2.TARGET_RELATIONS):
        raise Unit04SPV2Error(
            f"LAYER2_TARGET_RELATION_COVERAGE_DRIFT:{sorted(relation_counts)}"
        )
    if seen_episode_ids.intersection(unseen_episode_ids):
        raise Unit04SPV2Error("SPEAKING_SEEN_UNSEEN_OVERLAP")
    if any(row["a2_grammar_introduced"] for row in bridge_tasks + layer2_tasks):
        raise Unit04SPV2Error("A2_GRAMMAR_INTRODUCED")
    if any(row["support_relations_assessed"] for row in bridge_tasks + layer2_tasks):
        raise Unit04SPV2Error("SUPPORT_RELATION_PROMOTED")
    if any(row["passage_split_as_model_utterances"] for row in layer2_tasks):
        raise Unit04SPV2Error("PASSAGE_SPLIT_LAYER2_REINTRODUCED")

    requirements = dict(form_report["approved_requirements_10_of_10"])
    requirements["05_layer1_to_layer2_bridge"] = {
        "status": "PASS",
        "evidence": {
            "layer1_atomic_sentence_count": len(layer1),
            "bridge_task_count": len(bridge_tasks),
            "bridge_modes": list(BRIDGE_MODES),
        },
    }
    requirements["06_speaking_not_description_only"] = {
        "status": "PASS",
        "evidence": {
            "layer2_task_count": len(layer2_tasks),
            "layer2_modes": list(LAYER2_MODES),
            "description_only": False,
            "includes_question_asking": True,
            "includes_dialogue_follow_up": True,
            "includes_retell": True,
            "includes_repair_clarification": True,
            "includes_transfer": True,
        },
    }
    requirements["10_learner_facing_visual_pedagogical_acceptance"] = {
        "status": "PENDING_LATER_MILESTONE",
        "evidence": {
            "form_runtime_materialized": True,
            "speaking_runtime_materialized": True,
            "actual_visual_review_claimed": False,
        },
    }

    result = {
        "schema_version": "a1fs.v1.u04.spv2.current360_form_bound_speaking_cutover.v1",
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "unit_number": 4,
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "source_authority": {
            "active_form_runtime": fsv2.TASK_ID,
            "layer1_atomic_pool_source": sp01.TASK_ID,
            "current360_role": "NATURAL_PASSAGE_AUTHORITY_VIA_FSV2",
            "legacy_sp01_connected_layer2_role": (
                "SUPERSEDED_AS_ACTIVE_CONNECTED_SPEAKING"
            ),
            "formal_ket_role": "PREREQUISITE_TASK_SHAPE_EVIDENCE_ONLY",
            "ket99_role": "TEACHER_DELIVERY_REMEDIATION_TRANSFER_EVIDENCE_ONLY",
        },
        "cutover_contract": {
            "active_speaking_runtime_authority": TASK_ID,
            "parallel_active_speaking_runtime_allowed": False,
            "layer1_role": "ATOMIC_ACCURACY_AND_RETRIEVAL_FLUENCY",
            "bridge_role": "LAYER1_TO_LAYER2_CONTROLLED_TRANSFER",
            "layer2_role": "CURRENT360_FORM_BOUND_CONNECTED_SPEAKING",
            "legacy_sp01_layer1_role": "REUSED_ATOMIC_POOL_AND_LINEAGE",
            "legacy_sp01_layer2_role": "SUPERSEDED_NOT_ACTIVE",
            "current360_passage_split_is_layer2_model": False,
            "a1_language_more_mature_tasks": True,
        },
        "materialization_contract": {
            "layer1_atomic_sentence_count": len(layer1),
            "bridge_task_count": len(bridge_tasks),
            "bridge_tasks_per_form": BRIDGE_TASKS_PER_FORM,
            "layer2_task_count": len(layer2_tasks),
            "layer2_tasks_per_form": LAYER2_TASKS_PER_FORM,
            "bridge_mode_count": len(BRIDGE_MODES),
            "layer2_mode_count": len(LAYER2_MODES),
        },
        "layer1_atomic_speaking_pool": layer1,
        "bridge_tasks": bridge_tasks,
        "layer2_connected_speaking": layer2_tasks,
        "coverage": {
            "bridge_mode_counts": dict(bridge_mode_counts),
            "layer2_mode_counts": dict(layer2_mode_counts),
            "layer2_target_relation_coverage": f"{len(relation_counts)}/8",
            "layer2_target_relation_counts": {
                relation: relation_counts[relation]
                for relation in fsv2.TARGET_RELATIONS
            },
            "layer2_current360_micro_scene_count": len(scene_ids),
            "layer2_current360_life_domain_count": len(life_domains),
            "seen_layer2_episode_count": len(seen_episode_ids),
            "unseen_layer2_episode_count": len(unseen_episode_ids),
            "seen_unseen_overlap_count": 0,
            "support_relation_assessed_count": 0,
            "a2_grammar_introduced_count": 0,
            "passage_split_model_utterance_count": 0,
        },
        "speaking_scoring_contract": {
            "scoring_mode": "HUMAN_OR_SEMANTIC_REVIEW",
            "dimensions": list(SPEAKING_SCORING_DIMENSIONS),
            "single_answer_required": False,
            "acceptable_paraphrase": True,
            "audio_pronunciation_machine_score_required": False,
        },
        "approved_requirements_10_of_10": requirements,
        "safety": {
            "q01_q10_authority_modified": False,
            "fsv2_active_form_runtime_modified": False,
            "current360_episode_content_modified": False,
            "new_passage_authority_created": False,
            "second_sentence_authority_created": False,
            "support_relations_promoted_to_assessed_target": False,
            "a2_a2plus_unlocked": False,
            "listening_modified": False,
            "other_units_modified": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    result["deterministic_speaking_sha256"] = _digest(
        {
            "bridge_tasks": bridge_tasks,
            "layer2_connected_speaking": layer2_tasks,
            "cutover_contract": result["cutover_contract"],
            "coverage": result["coverage"],
        }
    )
    return result


def build_unit04_spv2_speaking_layer1_bridge_layer2_cutover() -> dict[str, Any]:
    return _materialize()


def compact_readback(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report["status"],
        "revision": report["revision"],
        "materialization_contract": report["materialization_contract"],
        "coverage": report["coverage"],
        "cutover_contract": report["cutover_contract"],
        "approved_requirements_10_of_10": report["approved_requirements_10_of_10"],
        "next_short_step": report["next_short_step"],
    }


def main() -> int:
    report = build_unit04_spv2_speaking_layer1_bridge_layer2_cutover()
    print(
        json.dumps(
            compact_readback(report),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
