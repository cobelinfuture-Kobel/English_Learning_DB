#!/usr/bin/env python3
"""Unit06 Reader360 P01: Natural360 source projection.

Read-only source-routing milestone that converts the already approved Unit06
Q07/Q07R1/Q08/Q09/Q10/Q10R1 authorities into 12 source reservoirs and 360
GPT-5.6 authoring slots. It does not author learner-facing English.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u06q10r1_unit06_learner_facing_pedagogical_acceptance as q10r1,
)
from ulga.builders import build_a1fs_v1_u06_q07_life_skill_micro_scenes as q07_builder
from ulga.builders import (
    build_a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion as q07r1_builder,
)
from ulga.builders import build_a1fs_v1_u06q10_questionbank_form_materialization as q10_builder

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only Unit06 Reader360 source projection. Python may route approved "
    "Q07 scene truth, Q07R1 functional chunks, Q08 functions, Q09 task families, "
    "and Q10/Q10R1 baseline lineage into deterministic GPT-5.6 authoring slots. "
    "It may not compose learner-facing passages, dialogue, pattern sentences, "
    "new scene truth, new canonical sentence assets, or unlock later grammar."
)

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_CAN_STATEMENT"
TASK_ID = "A1FS-V1-U06R360P01_Natural360SourceProjection"
STATUS = "PASS_A1FS_V1_U06R360P01_NATURAL360_SOURCE_PROJECTION"
REVISION = "UNIT06_Q07_Q07R1_12_RESERVOIR_360_SLOT_SOURCE_PROJECTION_V1"
NEXT_SHORT_STEP = "A1FS-V1-U06R360P01R1_SceneInstanceDiversityExpansionAndSuccessorRule"

REPO_ROOT = Path(__file__).resolve().parents[2]
Q08_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u06_q08_communicative_function_authority.json"
Q09_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u06_q09_task_pedagogical_contract.json"

FAMILY_CLUSTER_KIND = "SCENE_FAMILY_CHUNK_RESERVOIR"
CONTROLLED_CLUSTER_KIND = "Q04R1_CONTROLLED_CHUNK_RESERVOIR"
TARGET_EPISODE_COUNT = 360
EXPECTED_FAMILY_CLUSTER_COUNT = 12
EXPECTED_TOTAL_CLUSTER_COUNT = 13
BASE_EPISODES_PER_CLUSTER = TARGET_EPISODE_COUNT // EXPECTED_TOTAL_CLUSTER_COUNT
EXTRA_EPISODE_CLUSTER_COUNT = TARGET_EPISODE_COUNT % EXPECTED_TOTAL_CLUSTER_COUNT

DISCOURSE_FAMILIES = (
    "SCENE_DESCRIPTION",
    "PERSON_OR_THING_PROFILE",
    "ABILITY_PROFILE",
    "ACTION_AND_OBJECT_CONTEXT",
    "STATIC_LOCATION_PLUS_ABILITY",
    "DAILY_LIFE_CONNECTED_CONTEXT",
    "PICTURE_OR_SITUATION_OBSERVATION",
    "PERSONAL_OR_SOCIAL_TRANSFER",
    "CUMULATIVE_REVIEW_CONTEXT",
    "SHORT_CONNECTED_READING_CONTEXT",
)

AUTHORING_CONTRACT = {
    "learner_facing_language_author": "GPT-5.6 Sol",
    "python_may_compose_learner_facing_english": False,
    "source_content_authority": "UNIT06_Q07_SCENE_TRUTH_PLUS_Q07R1_FUNCTIONAL_CHUNKS",
    "q10_role": "PRE_READER360_COVERAGE_BASELINE_ONLY",
    "q10r1_role": "PRE_READER360_LEARNER_PRESENTATION_ACCEPTANCE_ONLY",
    "current360_target_episode_count": 360,
    "episode_sentence_target": "NATURAL_VARIABLE_LENGTH_4_TO_8_CONNECTED_A1_SENTENCES",
    "unit06_can_target_sentence_target": "NATURAL_1_TO_2_PER_EPISODE_NOT_FORCED",
    "cumulative_support_allowed": "U01_TO_U05_ALREADY_UNLOCKED_ONLY",
    "q07_scene_truth_may_be_rewritten": False,
    "q07r1_chunk_semantics_may_be_rewritten": False,
    "new_canonical_sentence_authority_created": False,
    "new_global_scene_identity_created": False,
    "can_interrogative_mastery_unlocked": False,
    "can_negative_mastery_unlocked": False,
    "permission_request_offer_possibility_can_unlocked": False,
    "a2_a2plus_unlocked": False,
}


class U06Natural360SourceProjectionError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U06Natural360SourceProjectionError(f"SOURCE_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U06Natural360SourceProjectionError(f"SOURCE_NOT_OBJECT:{path}")
    return value


def _validate_sources() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    q07 = q07_builder.build_report()
    q07r1 = q07r1_builder.build_report()
    q08 = _load_object(Q08_PATH)
    q09 = _load_object(Q09_PATH)
    q10 = q10_builder.build_export_payload()
    q10r1_report = q10r1.build_acceptance_report(q10)

    expected = (
        (q07, "PASS_A1FS_V1_U06Q07_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING"),
        (q07r1, "PASS_A1FS_V1_U06Q07R1_YLE_ABILITY_VERB_FUNCTIONAL_CHUNK_SEMANTIC_EXPANSION"),
        (q08, "PASS_A1FS_V1_U06Q08_COMMUNICATIVE_FUNCTION_AUTHORITY"),
        (q09, "PASS_A1FS_V1_U06Q09_TASK_AND_PEDAGOGICAL_CONTRACT"),
        (q10, q10_builder.PASS_STATUS),
        (q10r1_report, q10r1.PASS_STATUS),
    )
    for payload, status in expected:
        if payload.get("status") != status:
            raise U06Natural360SourceProjectionError(
                f"SOURCE_STATUS_DRIFT:{payload.get('task_id')}:{payload.get('status')}:{status}"
            )

    if len(q07.get("micro_scenes") or []) != 17:
        raise U06Natural360SourceProjectionError("Q07_SCENE_DENOMINATOR_DRIFT")
    if len(q07.get("sentence_scene_bindings") or []) != 49:
        raise U06Natural360SourceProjectionError("Q07_BINDING_DENOMINATOR_DRIFT")
    if q07.get("coverage", {}).get("q06_unbound_context_required_sentence_count") != 0:
        raise U06Natural360SourceProjectionError("Q07_UNBOUND_CONTEXT_REQUIRED_NONZERO")

    baseline = list(q07r1.get("existing_chunk_baseline", {}).get("normalized_surfaces") or [])
    new_chunks = list(q07r1.get("new_unit06_functional_chunks") or [])
    if (len(baseline), len(new_chunks)) != (58, 124):
        raise U06Natural360SourceProjectionError("Q07R1_CHUNK_DENOMINATOR_DRIFT")
    if len(set(baseline) | {str(x["normalized_surface"]) for x in new_chunks}) != 182:
        raise U06Natural360SourceProjectionError("Q07R1_DISTINCT_CHUNK_UNION_DRIFT")

    if len(q08.get("communicative_functions") or []) != 6:
        raise U06Natural360SourceProjectionError("Q08_FUNCTION_DENOMINATOR_DRIFT")
    if len(q09.get("task_families") or []) != 10:
        raise U06Natural360SourceProjectionError("Q09_TASK_FAMILY_DENOMINATOR_DRIFT")
    if len(q10.get("questionbank_items") or []) != 300 or len(q10.get("forms") or []) != 10:
        raise U06Natural360SourceProjectionError("Q10_BASELINE_DENOMINATOR_DRIFT")
    if q10r1_report.get("next_short_step") != TASK_ID:
        raise U06Natural360SourceProjectionError(
            f"Q10R1_NEXT_STEP_DRIFT:{q10r1_report.get('next_short_step')}"
        )
    return q07, q07r1, q08, q09, q10, q10r1_report


def _scene_family_maps(q07: Mapping[str, Any]) -> tuple[
    dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]
]:
    scene_by_ref = {str(row["scene_ref_id"]): dict(row) for row in q07["micro_scenes"]}
    if len(scene_by_ref) != 17:
        raise U06Natural360SourceProjectionError("Q07_SCENE_ID_COLLISION")
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for scene in scene_by_ref.values():
        by_family[str(scene["scene_family"])].append(scene)
    return scene_by_ref, by_family


def _q07_can_surface_families(
    q07: Mapping[str, Any], scene_by_ref: Mapping[str, Mapping[str, Any]]
) -> dict[str, list[str]]:
    values: dict[str, set[str]] = defaultdict(set)
    for row in q07["functional_chunk_occurrences"]:
        if str(row["kind"]) != "CAN_ABILITY":
            continue
        scene_ref = str(row["scene_ref_id"])
        scene = scene_by_ref.get(scene_ref)
        if scene is None:
            raise U06Natural360SourceProjectionError(f"CHUNK_SCENE_REF_MISSING:{scene_ref}")
        values[str(row["normalized_surface"])].add(str(scene["scene_family"]))
    if len(values) != 33:
        raise U06Natural360SourceProjectionError(f"Q07_CAN_SURFACE_COUNT_DRIFT:{len(values)}")
    return {surface: sorted(families) for surface, families in values.items()}


def _chunk_rows(
    q07: Mapping[str, Any], q07r1: Mapping[str, Any]
) -> list[dict[str, Any]]:
    scene_by_ref, _ = _scene_family_maps(q07)
    q07_families = _q07_can_surface_families(q07, scene_by_ref)
    rows: list[dict[str, Any]] = []

    for surface in q07r1["existing_chunk_baseline"]["normalized_surfaces"]:
        normalized = str(surface)
        families = list(q07_families.get(normalized) or [])
        if families:
            cluster_family = families[0]
            evidence_mode = "Q07_SCENE_BOUND_BASELINE_CHUNK"
        else:
            cluster_family = None
            evidence_mode = "Q04R1_CONTROLLED_BASELINE_CHUNK"
        pieces = normalized.split()
        base_verb = pieces[1] if len(pieces) >= 2 and pieces[0] == "can" else None
        rows.append(
            {
                "surface": normalized,
                "normalized_surface": normalized,
                "base_verb": base_verb,
                "source_kind": "Q04R1_OR_Q07_EXISTING_BASELINE",
                "semantic_admission_class": "BASELINE_ADMITTED",
                "scene_family": cluster_family,
                "candidate_scene_families": families,
                "evidence_mode": evidence_mode,
                "scene_grounding": None,
            }
        )

    for row in q07r1["new_unit06_functional_chunks"]:
        grounding = dict(row["scene_grounding"])
        family = str(grounding["scene_family"])
        rows.append(
            {
                "surface": str(row["surface"]),
                "normalized_surface": str(row["normalized_surface"]),
                "base_verb": str(row["base_verb"]),
                "source_kind": "Q07R1_NEW",
                "semantic_admission_class": str(row["semantic_admission_class"]),
                "scene_family": family,
                "candidate_scene_families": [family],
                "evidence_mode": "Q07R1_SCENE_GROUNDED_CHUNK",
                "scene_grounding": grounding,
            }
        )

    if len(rows) != 182 or len({x["normalized_surface"] for x in rows}) != 182:
        raise U06Natural360SourceProjectionError("CHUNK_ROW_DISTINCT_DENOMINATOR_DRIFT")
    return rows


def _build_clusters(
    q07: Mapping[str, Any], q07r1: Mapping[str, Any]
) -> list[dict[str, Any]]:
    scene_by_ref, scenes_by_family = _scene_family_maps(q07)
    chunks = _chunk_rows(q07, q07r1)
    chunks_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    controlled: list[dict[str, Any]] = []
    for row in chunks:
        family = row["scene_family"]
        if family is None:
            controlled.append(row)
        else:
            chunks_by_family[str(family)].append(row)

    family_names = sorted(set(chunks_by_family) | set(scenes_by_family))
    if len(family_names) != EXPECTED_FAMILY_CLUSTER_COUNT:
        raise U06Natural360SourceProjectionError(
            f"FAMILY_RESERVOIR_COUNT_DRIFT:{len(family_names)}:{family_names}"
        )
    if len(controlled) != 25:
        raise U06Natural360SourceProjectionError(
            f"CONTROLLED_BASELINE_CHUNK_COUNT_DRIFT:{len(controlled)}"
        )

    clusters: list[dict[str, Any]] = []
    ordinal = 0
    for family in family_names:
        ordinal += 1
        family_chunks = sorted(
            chunks_by_family.get(family, []),
            key=lambda x: (str(x["base_verb"]), str(x["normalized_surface"])),
        )
        family_scenes = sorted(
            scenes_by_family.get(family, []), key=lambda x: str(x["scene_ref_id"])
        )
        if not family_chunks:
            raise U06Natural360SourceProjectionError(f"FAMILY_CLUSTER_CHUNK_EMPTY:{family}")
        clusters.append(
            {
                "cluster_id": f"U06-N360-C{ordinal:02d}",
                "cluster_ordinal": ordinal,
                "cluster_kind": FAMILY_CLUSTER_KIND,
                "scene_family": family,
                "source_scene_count": len(family_scenes),
                "source_scene_refs": [str(x["scene_ref_id"]) for x in family_scenes],
                "functional_chunk_count": len(family_chunks),
                "functional_chunks": family_chunks,
                "base_verbs": sorted(
                    {str(x["base_verb"]) for x in family_chunks if x.get("base_verb")}
                ),
                "evidence_policy": (
                    "Use exact Q07 scene truth when a scene ref is selected; otherwise use "
                    "the Q07R1 scene-grounding directive and approved chunk semantics only."
                ),
            }
        )

    ordinal += 1
    clusters.append(
        {
            "cluster_id": f"U06-N360-C{ordinal:02d}",
            "cluster_ordinal": ordinal,
            "cluster_kind": CONTROLLED_CLUSTER_KIND,
            "scene_family": None,
            "source_scene_count": 0,
            "source_scene_refs": [],
            "functional_chunk_count": len(controlled),
            "functional_chunks": sorted(
                controlled, key=lambda x: (str(x["base_verb"]), str(x["normalized_surface"]))
            ),
            "base_verbs": sorted({str(x["base_verb"]) for x in controlled if x.get("base_verb")}),
            "evidence_policy": (
                "Q04R1 controlled-recombination chunks require fresh GPT-5.6 natural context "
                "grounding at Current360 authoring time; no new canonical scene truth is created."
            ),
        }
    )

    if len(clusters) != EXPECTED_TOTAL_CLUSTER_COUNT:
        raise U06Natural360SourceProjectionError(f"CLUSTER_COUNT_DRIFT:{len(clusters)}")
    assigned_scenes = [ref for row in clusters for ref in row["source_scene_refs"]]
    if len(assigned_scenes) != 17 or len(set(assigned_scenes)) != 17:
        raise U06Natural360SourceProjectionError("Q07_SCENE_CLUSTER_ASSIGNMENT_DRIFT")
    assigned_chunks = [
        row["normalized_surface"]
        for cluster in clusters
        for row in cluster["functional_chunks"]
    ]
    if len(assigned_chunks) != 182 or len(set(assigned_chunks)) != 182:
        raise U06Natural360SourceProjectionError("CHUNK_CLUSTER_ASSIGNMENT_DRIFT")
    return clusters


def _slot_chunk_buckets(chunks: Sequence[Mapping[str, Any]], slot_count: int) -> list[list[str]]:
    surfaces = [str(row["normalized_surface"]) for row in chunks]
    if not surfaces:
        raise U06Natural360SourceProjectionError("CLUSTER_CHUNK_EMPTY")
    if slot_count <= 0:
        raise U06Natural360SourceProjectionError("CLUSTER_SLOT_COUNT_INVALID")
    buckets: list[list[str]] = [[] for _ in range(slot_count)]
    # Give every authoring slot at least one approved chunk.
    for index in range(slot_count):
        buckets[index].append(surfaces[index % len(surfaces)])
    # If a cluster contains more chunks than slots, assign every remaining distinct chunk once.
    for index in range(slot_count, len(surfaces)):
        buckets[index % slot_count].append(surfaces[index])
    return buckets


def _build_episode_slots(
    clusters: Sequence[Mapping[str, Any]],
    q08: Mapping[str, Any],
    q09: Mapping[str, Any],
) -> list[dict[str, Any]]:
    functions = sorted(str(x["function_id"]) for x in q08["communicative_functions"])
    tasks = sorted(str(x["task_family_id"]) for x in q09["task_families"])
    if len(functions) != 6 or len(tasks) != 10:
        raise U06Natural360SourceProjectionError("FUNCTION_OR_TASK_DENOMINATOR_DRIFT")

    slots: list[dict[str, Any]] = []
    episode_ordinal = 0
    cluster_episode_counts: dict[str, int] = {}
    for cluster_index, cluster in enumerate(clusters):
        slot_count = BASE_EPISODES_PER_CLUSTER + (
            1 if cluster_index < EXTRA_EPISODE_CLUSTER_COUNT else 0
        )
        cluster_episode_counts[str(cluster["cluster_id"])] = slot_count
        chunk_buckets = _slot_chunk_buckets(cluster["functional_chunks"], slot_count)
        for local_ordinal in range(1, slot_count + 1):
            episode_ordinal += 1
            discourse_family = DISCOURSE_FAMILIES[(local_ordinal - 1) % len(DISCOURSE_FAMILIES)]
            variation_pass = ((local_ordinal - 1) // len(DISCOURSE_FAMILIES)) + 1
            evidence_mode = (
                "CONTROLLED_CHUNK_CONTEXT_GROUNDING"
                if cluster["cluster_kind"] == CONTROLLED_CLUSTER_KIND
                else (
                    "Q07_SCENE_OR_Q07R1_GROUNDING"
                    if cluster["source_scene_refs"]
                    else "Q07R1_GROUNDING_ONLY"
                )
            )
            slots.append(
                {
                    "episode_slot_id": f"U06-N360-S{episode_ordinal:03d}",
                    "target_current360_episode_id": f"U06-NEB-E{episode_ordinal:03d}",
                    "cluster_id": str(cluster["cluster_id"]),
                    "cluster_ordinal": int(cluster["cluster_ordinal"]),
                    "cluster_kind": str(cluster["cluster_kind"]),
                    "episode_within_cluster": local_ordinal,
                    "variation_pass": variation_pass,
                    "discourse_family": discourse_family,
                    "scene_family": cluster.get("scene_family"),
                    "candidate_source_scene_refs": list(cluster["source_scene_refs"]),
                    "required_functional_chunk_surfaces": list(chunk_buckets[local_ordinal - 1]),
                    "candidate_communicative_function_ids": functions,
                    "candidate_task_family_ids": tasks,
                    "evidence_mode": evidence_mode,
                    "authoring_constraints": {
                        "author": "GPT-5.6 Sol",
                        "source_lineage_required": True,
                        "realize_every_required_chunk_naturally": False,
                        "required_functional_chunk_surfaces_role": "CORPUS_COVERAGE_ROUTING_TARGET_NOT_EPISODE_MANDATE",
                        "scene_first_natural_support_over_chunk_stuffing": True,
                        "episode_may_realize_one_or_more_semantically_natural_target_chunks": True,
                        "full_182_chunk_coverage_required_at_corpus_level": True,
                        "select_only_semantically_compatible_subjects_objects_places_and_support": True,
                        "use_q07_scene_truth_exactly_when_scene_ref_selected": True,
                        "q04r1_controlled_chunk_requires_gpt56_context_grounding": True,
                        "pronoun_antecedent_required": True,
                        "unit06_target_grammar_only": "AFFIRMATIVE_DECLARATIVE_CAN_ABILITY",
                        "cumulative_support_units": ["U01", "U02", "U03", "U04", "U05"],
                        "new_canonical_sentence_identity_created": False,
                        "new_global_scene_identity_created": False,
                        "can_interrogative_mastery_unlocked": False,
                        "can_negative_mastery_unlocked": False,
                        "permission_request_offer_possibility_can_unlocked": False,
                        "a2_a2plus_unlocked": False,
                    },
                }
            )

    if len(slots) != TARGET_EPISODE_COUNT:
        raise U06Natural360SourceProjectionError(
            f"EPISODE_SLOT_COUNT_DRIFT:{len(slots)}:{TARGET_EPISODE_COUNT}"
        )
    if len({x["episode_slot_id"] for x in slots}) != TARGET_EPISODE_COUNT:
        raise U06Natural360SourceProjectionError("EPISODE_SLOT_ID_COLLISION")
    if len({x["target_current360_episode_id"] for x in slots}) != TARGET_EPISODE_COUNT:
        raise U06Natural360SourceProjectionError("TARGET_EPISODE_ID_COLLISION")
    return slots


def build_unit06_natural360_source_projection() -> dict[str, Any]:
    q07, q07r1, q08, q09, q10, q10r1_report = _validate_sources()
    clusters = _build_clusters(q07, q07r1)
    slots = _build_episode_slots(clusters, q08, q09)

    assigned_required_chunks = {
        surface for row in slots for surface in row["required_functional_chunk_surfaces"]
    }
    all_chunks = {
        row["normalized_surface"]
        for cluster in clusters
        for row in cluster["functional_chunks"]
    }
    if assigned_required_chunks != all_chunks:
        missing = sorted(all_chunks - assigned_required_chunks)
        raise U06Natural360SourceProjectionError(
            f"AUTHORING_SLOT_CHUNK_COVERAGE_GAP:{missing[:10]}"
        )
    q07r1_verbs = {
        str(row["base_verb"]) for row in q07r1["new_unit06_functional_chunks"]
    }
    if len(q07r1_verbs) != 62:
        raise U06Natural360SourceProjectionError("Q07R1_SOURCE_VERB_COUNT_DRIFT")

    family_clusters = [x for x in clusters if x["cluster_kind"] == FAMILY_CLUSTER_KIND]
    controlled_clusters = [x for x in clusters if x["cluster_kind"] == CONTROLLED_CLUSTER_KIND]
    cluster_kind_counts = Counter(x["cluster_kind"] for x in clusters)

    return {
        "schema_version": "a1fs.v1.u06.r360.natural360_source_projection.v1",
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "unit_number": 6,
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "route_lock": {
            "approved_route": [
                "U06_Q01_TO_Q09_CANONICAL_AUTHORITY",
                "U06_Q10_COVERAGE_BASELINE",
                "U06_Q10R1_BASELINE_LEARNER_ACCEPTANCE",
                "U06_NATURAL360_SOURCE_PROJECTION",
                "U06_READER360_SCENE_DIVERSITY_EXPANSION",
                "U06_CURRENT360",
                "U06_SPOKEN360",
                "U06_PATTERN360",
                "U06_CONTEXTUAL_ACTIVE_RUNTIME",
                "U06_FAR_KET_ADAPTED_FINAL_PRACTICE",
                "U06_MEDIA_AND_PDF_ONLY_AFTER_FINAL_PRACTICE_AUTHORITY",
            ],
            "q10_role": "PRE_READER360_COVERAGE_BASELINE_ONLY",
            "q10r1_role": "PRE_READER360_LEARNER_PRESENTATION_ACCEPTANCE_ONLY",
            "old_q10r2_pdf_route_paused": True,
            "final_forms_must_follow_reader360_and_far": True,
        },
        "source_authorities": {
            "q07_task_id": str(q07["task_id"]),
            "q07_scene_count": len(q07["micro_scenes"]),
            "q07_sentence_scene_binding_count": len(q07["sentence_scene_bindings"]),
            "q07r1_task_id": str(q07r1["task_id"]),
            "q07r1_distinct_chunk_count": 182,
            "q07r1_new_chunk_count": len(q07r1["new_unit06_functional_chunks"]),
            "q07r1_existing_baseline_chunk_count": len(
                q07r1["existing_chunk_baseline"]["normalized_surfaces"]
            ),
            "q07r1_source_verb_count": len(q07r1_verbs),
            "q08_task_id": str(q08["task_id"]),
            "q08_communicative_function_count": len(q08["communicative_functions"]),
            "q09_task_id": str(q09["task_id"]),
            "q09_task_family_count": len(q09["task_families"]),
            "q10_task_id": str(q10["task_id"]),
            "q10_questionbank_item_count": len(q10["questionbank_items"]),
            "q10_form_count": len(q10["forms"]),
            "q10_runtime_role": "PRE_READER360_COVERAGE_BASELINE_ONLY",
            "q10r1_task_id": str(q10r1_report["task_id"]),
            "q10r1_activity_count": int(q10r1_report["acceptance"]["activity_count"]),
            "q10r1_runtime_role": "PRE_READER360_LEARNER_PRESENTATION_ACCEPTANCE_ONLY",
        },
        "authoring_contract": dict(AUTHORING_CONTRACT),
        "coverage": {
            "source_scene_count": 17,
            "source_scene_assigned_count": sum(x["source_scene_count"] for x in clusters),
            "distinct_functional_chunk_count": len(all_chunks),
            "distinct_functional_chunk_slot_coverage": f"{len(assigned_required_chunks)}/182",
            "q07r1_source_verb_coverage": "62/62",
            "family_cluster_count": len(family_clusters),
            "controlled_baseline_cluster_count": len(controlled_clusters),
            "source_cluster_count": len(clusters),
            "cluster_kind_counts": dict(cluster_kind_counts),
            "episode_slot_count": len(slots),
            "cluster_episode_counts": dict(
                Counter(str(row["cluster_id"]) for row in slots)
            ),
            "minimum_episodes_per_cluster": min(
                Counter(str(row["cluster_id"]) for row in slots).values()
            ),
            "maximum_episodes_per_cluster": max(
                Counter(str(row["cluster_id"]) for row in slots).values()
            ),
            "extra_episode_cluster_count": sum(
                1
                for value in Counter(str(row["cluster_id"]) for row in slots).values()
                if value == BASE_EPISODES_PER_CLUSTER + 1
            ),
            "discourse_family_count": len(DISCOURSE_FAMILIES),
            "variation_pass_count": 3,
            "communicative_function_coverage": "6/6",
            "task_family_coverage": "10/10",
        },
        "source_clusters": clusters,
        "episode_authoring_slots": slots,
        "integrity": {
            "source_cluster_digest": _digest(clusters),
            "episode_slot_digest": _digest(slots),
            "source_scene_ref_digest": _digest(
                sorted(str(row["scene_ref_id"]) for row in q07["micro_scenes"])
            ),
            "functional_chunk_digest": _digest(sorted(all_chunks)),
        },
        "scope_safety": {
            "q06_modified": False,
            "q07_modified": False,
            "q07r1_modified": False,
            "q08_modified": False,
            "q09_modified": False,
            "q10_modified": False,
            "q10r1_modified": False,
            "learner_facing_english_materialized": False,
            "current360_materialized": False,
            "spoken360_materialized": False,
            "pattern360_materialized": False,
            "contextual_active_runtime_materialized": False,
            "far_final_practice_materialized": False,
            "pdf_materialized": False,
            "new_canonical_sentence_authority_created": False,
            "new_global_scene_identity_created": False,
            "can_interrogative_mastery_unlocked": False,
            "can_negative_mastery_unlocked": False,
            "permission_request_offer_possibility_can_unlocked": False,
            "a2_a2plus_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    report = build_unit06_natural360_source_projection()
    print(f"STATUS={report['status']}")
    print(f"SCENES={report['coverage']['source_scene_count']}")
    print(f"CHUNKS={report['coverage']['distinct_functional_chunk_count']}")
    print(f"VERBS={report['coverage']['q07r1_source_verb_coverage']}")
    print(f"CLUSTERS={report['coverage']['source_cluster_count']}")
    print(f"EPISODE_SLOTS={report['coverage']['episode_slot_count']}")
    print(f"FUNCTIONS={report['coverage']['communicative_function_coverage']}")
    print(f"TASK_FAMILIES={report['coverage']['task_family_coverage']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
