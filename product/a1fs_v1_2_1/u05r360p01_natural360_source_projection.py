from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u05_q07_life_skill_micro_scenes as q07_builder
from ulga.builders import build_a1fs_v1_u05q10_questionbank_form_materialization as q10_builder

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only Unit05 Natural360 source-routing milestone. It consumes Unit05 Q07 "
    "scene truth plus Q08/Q09 authority and the existing Q10 baseline only to build "
    "36 source clusters and 360 GPT-5.6 authoring slots. Python does not compose, "
    "paraphrase, repair, or select learner-facing English. Unit04 modules are "
    "architecture/alignment references only and are not imported as Unit05 content."
)

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BE_VERB_BASIC"
TASK_ID = "A1FS-V1-U05R360P01_Natural360SourceProjection"
STATUS = "PASS_A1FS_V1_U05R360P01_NATURAL360_SOURCE_PROJECTION"
REVISION = "UNIT05_OWN_AUTHORITY_36_CLUSTER_360_SLOT_SOURCE_PROJECTION_V1"
NEXT_SHORT_STEP = "A1FS-V1-U05R360P02_Current360GPT56NaturalEpisodeMaterialization"

REPO_ROOT = Path(__file__).resolve().parents[2]
Q08_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u05_q08_communicative_function_authority.json"
Q09_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u05_q09_task_pedagogical_contract.json"

SOURCE_CLUSTER_COUNT = 36
EPISODES_PER_CLUSTER = 10
TARGET_EPISODE_COUNT = SOURCE_CLUSTER_COUNT * EPISODES_PER_CLUSTER

DISCOURSE_FAMILIES = (
    "SCENE_DESCRIPTION",
    "PERSON_OR_THING_PROFILE",
    "IDENTITY_AND_CATEGORY_CONTEXT",
    "STATE_AND_DESCRIPTION_CONTEXT",
    "STATIC_LOCATION_CONTEXT",
    "CORRECTION_OR_CONTRAST_CONTEXT",
    "DAILY_LIFE_CONNECTED_CONTEXT",
    "PICTURE_OR_SITUATION_OBSERVATION",
    "PERSONAL_OR_SOCIAL_TRANSFER",
    "CUMULATIVE_REVIEW_CONTEXT",
)

UNIT04_ALIGNMENT_REFERENCES = {
    "current360": "product/a1fs_v1_2_1/u04neb02_natural_episode_bank_360.py",
    "contextual_form_runtime": "product/a1fs_v1_2_1/u04fsv2_current360_contextual_form_runtime.py",
    "speaking_cutover": "product/a1fs_v1_2_1/u04spv2_current360_speaking_cutover.py",
    "productive_scoring": "product/a1fs_v1_2_1/u04rswv2_productive_scoring_cambridge_progression_acceptance.py",
    "visual_acceptance": "product/a1fs_v1_2_1/u04vav2_current360_learner_facing_visual_pedagogical_acceptance.py",
    "spoken360": "product/a1fs_v1_2_1/u04reader360_spoken_dialogue_reader_partial.json",
    "pattern360": "product/a1fs_v1_2_1/u04reader360_pattern_sentence_family_reader_partial.json",
}

AUTHORING_CONTRACT = {
    "learner_facing_language_author": "GPT-5.6 Sol",
    "python_may_compose_learner_facing_english": False,
    "source_content_authority": "UNIT05_Q06_Q07_Q08_Q09_ONLY",
    "unit04_content_authority_consumed": False,
    "unit04_role": "ARCHITECTURE_AND_ACCEPTANCE_ALIGNMENT_ONLY",
    "q10_role": "PRE_CUTOVER_BASELINE_ONLY",
    "current360_target_episode_count": 360,
    "source_cluster_count": 36,
    "episodes_per_source_cluster": 10,
    "episode_sentence_target": "2_TO_4_CONNECTED_A1_SENTENCES",
    "truth_fact_target_per_episode": "2_TO_5_COMPATIBLE_Q07_TRUTH_FACTS",
    "pronoun_antecedent_required": True,
    "negative_truth_requires_explicit_positive_contrast": True,
    "be_interrogative_mastery_unlocked": False,
    "past_be_unlocked": False,
    "existential_there_be_unlocked": False,
    "present_continuous_mastery_unlocked": False,
    "a2_a2plus_unlocked": False,
}


class U05Natural360SourceProjectionError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05Natural360SourceProjectionError(f"SOURCE_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U05Natural360SourceProjectionError(f"SOURCE_NOT_OBJECT:{path}")
    return value


def _validate_sources() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    q07 = q07_builder.build_report()
    if q07.get("status") != (
        "PASS_A1FS_V1_U05Q07_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING"
    ):
        raise U05Natural360SourceProjectionError("Q07_SOURCE_NOT_PASS")
    scenes = list(q07.get("micro_scenes") or [])
    bindings = list(q07.get("sentence_scene_bindings") or [])
    if not (SOURCE_CLUSTER_COUNT < len(scenes) < len(bindings) == 478):
        raise U05Natural360SourceProjectionError(
            f"Q07_SCENE_DENOMINATOR_INVALID:{len(scenes)}:{len(bindings)}"
        )
    if q07.get("coverage", {}).get("q06_unbound_context_required_sentence_count") != 0:
        raise U05Natural360SourceProjectionError("Q07_UNBOUND_CONTEXT_REQUIRED_NONZERO")

    q08 = _load_object(Q08_PATH)
    if q08.get("status") != "PASS_A1FS_V1_U05Q08_COMMUNICATIVE_FUNCTION_AUTHORITY":
        raise U05Natural360SourceProjectionError("Q08_SOURCE_NOT_PASS")
    if len(q08.get("communicative_functions") or []) != 7:
        raise U05Natural360SourceProjectionError("Q08_FUNCTION_DENOMINATOR_INVALID")
    if set((q08.get("frame_function_compatibility") or {}).keys()) != {
        "U05-BF-NP-AFF",
        "U05-BF-ADJ-AFF",
        "U05-BF-PLACE-AFF",
        "U05-BF-NP-NEG",
        "U05-BF-ADJ-NEG",
        "U05-BF-PLACE-NEG",
    }:
        raise U05Natural360SourceProjectionError("Q08_FRAME_COMPATIBILITY_DRIFT")

    q09 = _load_object(Q09_PATH)
    if q09.get("status") != "PASS_A1FS_V1_U05Q09_TASK_AND_PEDAGOGICAL_CONTRACT":
        raise U05Natural360SourceProjectionError("Q09_SOURCE_NOT_PASS")
    if len(q09.get("task_families") or []) != 10:
        raise U05Natural360SourceProjectionError("Q09_TASK_FAMILY_DENOMINATOR_INVALID")

    q10 = q10_builder.build_export_payload()
    if q10.get("status") != q10_builder.PASS_STATUS:
        raise U05Natural360SourceProjectionError("Q10_BASELINE_NOT_PASS")
    if len(q10.get("questionbank_items") or []) != 800:
        raise U05Natural360SourceProjectionError("Q10_BASELINE_ITEM_DENOMINATOR_INVALID")
    if len(q10.get("forms") or []) != 20:
        raise U05Natural360SourceProjectionError("Q10_BASELINE_FORM_DENOMINATOR_INVALID")
    return q07, q08, q09, q10


def _allocate_cluster_counts(by_family: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, int]:
    families = sorted(by_family)
    if not families:
        raise U05Natural360SourceProjectionError("Q07_SCENE_FAMILY_EMPTY")
    if len(families) > SOURCE_CLUSTER_COUNT:
        raise U05Natural360SourceProjectionError(
            f"SCENE_FAMILY_COUNT_EXCEEDS_CLUSTER_BUDGET:{len(families)}"
        )

    allocations = {family: 1 for family in families}
    remaining = SOURCE_CLUSTER_COUNT - len(families)
    counts = {family: len(by_family[family]) for family in families}

    # Deterministic proportional apportionment. Each used family gets one cluster;
    # remaining clusters are assigned by highest scenes-per-current-cluster ratio.
    for _ in range(remaining):
        family = max(
            families,
            key=lambda value: (
                counts[value] / allocations[value],
                counts[value],
                value,
            ),
        )
        allocations[family] += 1

    if sum(allocations.values()) != SOURCE_CLUSTER_COUNT:
        raise U05Natural360SourceProjectionError("CLUSTER_ALLOCATION_SUM_DRIFT")
    if any(allocations[family] > counts[family] for family in families):
        raise U05Natural360SourceProjectionError("CLUSTER_ALLOCATION_EXCEEDS_SCENE_COUNT")
    return allocations


def _scene_sort_key(scene: Mapping[str, Any]) -> tuple[str, ...]:
    return (
        str(scene.get("semantic_frame_id") or ""),
        str(scene.get("polarity") or ""),
        str(scene.get("subject_class") or ""),
        str(scene.get("subject_surface") or ""),
        str(scene.get("complement_surface") or ""),
        str(scene.get("relation_surface") or ""),
        str(scene.get("scene_ref_id") or ""),
    )


def _compact_truth(scene: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "scene_ref_id": str(scene["scene_ref_id"]),
        "scene_family": str(scene["scene_family"]),
        "medium_setting": str(scene["medium_setting"]),
        "semantic_frame_id": str(scene["semantic_frame_id"]),
        "polarity": str(scene["polarity"]),
        "subject_surface": str(scene["subject_surface"]),
        "subject_class": str(scene["subject_class"]),
        "complement_surface": str(scene["complement_surface"]),
        "relation_surface": scene.get("relation_surface"),
        "referent_binding_spec": dict(scene["referent_binding_spec"]),
        "truth_evidence_spec": dict(scene["truth_evidence_spec"]),
        "bound_q06_identities": list(scene["bound_q06_identities"]),
        "surface_variants": list(scene["surface_variants"]),
    }


def _build_clusters(q07: Mapping[str, Any]) -> list[dict[str, Any]]:
    scenes = [dict(row) for row in q07["micro_scenes"]]
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for scene in scenes:
        by_family[str(scene["scene_family"])].append(scene)

    allocations = _allocate_cluster_counts(by_family)
    clusters: list[dict[str, Any]] = []
    ordinal = 0
    for family in sorted(by_family):
        rows = sorted(by_family[family], key=_scene_sort_key)
        bucket_count = allocations[family]
        buckets: list[list[dict[str, Any]]] = [[] for _ in range(bucket_count)]
        # Round-robin after deterministic sorting keeps every Q07 truth once while
        # spreading frames/polarities/subjects across same-family cluster reservoirs.
        for index, row in enumerate(rows):
            buckets[index % bucket_count].append(row)

        for family_bucket_ordinal, bucket in enumerate(buckets, start=1):
            if not bucket:
                raise U05Natural360SourceProjectionError(
                    f"EMPTY_CLUSTER_BUCKET:{family}:{family_bucket_ordinal}"
                )
            ordinal += 1
            frame_ids = sorted({str(row["semantic_frame_id"]) for row in bucket})
            polarities = sorted({str(row["polarity"]) for row in bucket})
            subject_classes = sorted({str(row["subject_class"]) for row in bucket})
            relations = sorted(
                {
                    str(row["relation_surface"])
                    for row in bucket
                    if row.get("relation_surface")
                }
            )
            clusters.append(
                {
                    "cluster_id": f"U05-N360-C{ordinal:02d}",
                    "cluster_ordinal": ordinal,
                    "scene_family": family,
                    "medium_setting": str(bucket[0]["medium_setting"]),
                    "family_cluster_ordinal": family_bucket_ordinal,
                    "family_cluster_count": bucket_count,
                    "source_scene_count": len(bucket),
                    "source_scene_refs": [str(row["scene_ref_id"]) for row in bucket],
                    "candidate_truth_facts": [_compact_truth(row) for row in bucket],
                    "coverage": {
                        "frame_ids": frame_ids,
                        "polarities": polarities,
                        "subject_classes": subject_classes,
                        "direct_place_relations": relations,
                        "q06_identity_count": len(
                            {
                                str(qid)
                                for row in bucket
                                for qid in row["bound_q06_identities"]
                            }
                        ),
                    },
                }
            )

    if len(clusters) != SOURCE_CLUSTER_COUNT:
        raise U05Natural360SourceProjectionError(
            f"CLUSTER_COUNT_DRIFT:{len(clusters)}:{SOURCE_CLUSTER_COUNT}"
        )

    assigned = [
        scene_ref
        for cluster in clusters
        for scene_ref in cluster["source_scene_refs"]
    ]
    source_refs = [str(row["scene_ref_id"]) for row in scenes]
    if len(assigned) != len(source_refs):
        raise U05Natural360SourceProjectionError("SCENE_ASSIGNMENT_COUNT_DRIFT")
    if len(set(assigned)) != len(assigned):
        raise U05Natural360SourceProjectionError("SCENE_ASSIGNED_TO_MULTIPLE_CLUSTERS")
    if set(assigned) != set(source_refs):
        raise U05Natural360SourceProjectionError("SCENE_ASSIGNMENT_SET_DRIFT")
    return clusters


def _function_pool(frame_id: str, q08: Mapping[str, Any]) -> list[str]:
    values = list((q08["frame_function_compatibility"] or {}).get(frame_id) or [])
    if not values:
        raise U05Natural360SourceProjectionError(f"FRAME_FUNCTION_POOL_EMPTY:{frame_id}")
    return [str(value) for value in values]


def _task_pool(function_ids: Sequence[str], q09: Mapping[str, Any]) -> list[str]:
    function_set = set(function_ids)
    values = [
        str(row["task_family_id"])
        for row in q09["task_families"]
        if function_set.intersection(row.get("allowed_function_ids") or [])
    ]
    if not values:
        raise U05Natural360SourceProjectionError(
            f"TASK_POOL_EMPTY:{','.join(sorted(function_set))}"
        )
    return values


def _build_episode_slots(
    clusters: Sequence[Mapping[str, Any]],
    q08: Mapping[str, Any],
    q09: Mapping[str, Any],
) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    episode_ordinal = 0
    for cluster in clusters:
        frame_function_map = {
            frame_id: _function_pool(frame_id, q08)
            for frame_id in cluster["coverage"]["frame_ids"]
        }
        all_functions = sorted(
            {
                function_id
                for values in frame_function_map.values()
                for function_id in values
            }
        )
        all_tasks = sorted(_task_pool(all_functions, q09))

        for local_ordinal, discourse_family in enumerate(DISCOURSE_FAMILIES, start=1):
            episode_ordinal += 1
            slots.append(
                {
                    "episode_slot_id": f"U05-N360-S{episode_ordinal:03d}",
                    "target_current360_episode_id": f"U05-NEB-E{episode_ordinal:03d}",
                    "cluster_id": str(cluster["cluster_id"]),
                    "cluster_ordinal": int(cluster["cluster_ordinal"]),
                    "episode_within_cluster": local_ordinal,
                    "discourse_family": discourse_family,
                    "scene_family": str(cluster["scene_family"]),
                    "medium_setting": str(cluster["medium_setting"]),
                    "candidate_source_scene_refs": list(cluster["source_scene_refs"]),
                    "candidate_frame_function_map": frame_function_map,
                    "candidate_communicative_function_ids": all_functions,
                    "candidate_task_family_ids": all_tasks,
                    "authoring_constraints": {
                        "author": "GPT-5.6 Sol",
                        "select_only_semantically_compatible_truth_facts": True,
                        "truth_fact_count_target": "2_TO_5",
                        "source_scene_lineage_required": True,
                        "source_q06_lineage_required": True,
                        "pronoun_antecedent_required": True,
                        "negative_truth_must_include_explicit_positive_contrast": True,
                        "do_not_turn_q07_truth_directive_into_learner_prompt": True,
                        "do_not_copy_unit04_learner_content": True,
                        "do_not_use_unit04_reader360_as_unit05_authority": True,
                        "unit05_target_grammar_only": "PRESENT_BE_DECLARATIVE_AFFIRMATIVE_NEGATIVE",
                        "be_interrogative_mastery_unlocked": False,
                        "past_be_unlocked": False,
                        "existential_there_be_unlocked": False,
                        "present_continuous_mastery_unlocked": False,
                        "a2_a2plus_unlocked": False,
                    },
                }
            )

    if len(slots) != TARGET_EPISODE_COUNT:
        raise U05Natural360SourceProjectionError(
            f"EPISODE_SLOT_COUNT_DRIFT:{len(slots)}:{TARGET_EPISODE_COUNT}"
        )
    if len({row["episode_slot_id"] for row in slots}) != TARGET_EPISODE_COUNT:
        raise U05Natural360SourceProjectionError("EPISODE_SLOT_ID_COLLISION")
    if len({row["target_current360_episode_id"] for row in slots}) != TARGET_EPISODE_COUNT:
        raise U05Natural360SourceProjectionError("TARGET_EPISODE_ID_COLLISION")
    return slots


def build_unit05_natural360_source_projection() -> dict[str, Any]:
    q07, q08, q09, q10 = _validate_sources()
    clusters = _build_clusters(q07)
    slots = _build_episode_slots(clusters, q08, q09)

    cluster_scene_family_counts = Counter(row["scene_family"] for row in clusters)
    source_scene_family_counts = Counter(
        str(row["scene_family"]) for row in q07["micro_scenes"]
    )
    all_frames = sorted(
        {
            frame_id
            for cluster in clusters
            for frame_id in cluster["coverage"]["frame_ids"]
        }
    )
    all_polarities = sorted(
        {
            value
            for cluster in clusters
            for value in cluster["coverage"]["polarities"]
        }
    )
    all_subject_classes = sorted(
        {
            value
            for cluster in clusters
            for value in cluster["coverage"]["subject_classes"]
        }
    )
    all_relations = sorted(
        {
            value
            for cluster in clusters
            for value in cluster["coverage"]["direct_place_relations"]
        }
    )
    all_functions = sorted(
        {
            value
            for row in slots
            for value in row["candidate_communicative_function_ids"]
        }
    )
    all_tasks = sorted(
        {
            value
            for row in slots
            for value in row["candidate_task_family_ids"]
        }
    )

    if len(all_frames) != 6:
        raise U05Natural360SourceProjectionError(
            f"FRAME_COVERAGE_INCOMPLETE:{all_frames}"
        )
    if all_polarities != ["AFFIRMATIVE", "NEGATIVE"]:
        raise U05Natural360SourceProjectionError(
            f"POLARITY_COVERAGE_INCOMPLETE:{all_polarities}"
        )
    if len(all_subject_classes) != 9:
        raise U05Natural360SourceProjectionError(
            f"SUBJECT_CLASS_COVERAGE_INCOMPLETE:{all_subject_classes}"
        )
    if set(all_relations) != {
        "in",
        "inside",
        "on",
        "near",
        "at",
        "under",
        "behind",
        "between",
    }:
        raise U05Natural360SourceProjectionError(
            f"PLACE_RELATION_COVERAGE_INCOMPLETE:{all_relations}"
        )
    if len(all_functions) != 7:
        raise U05Natural360SourceProjectionError(
            f"FUNCTION_COVERAGE_INCOMPLETE:{all_functions}"
        )
    if len(all_tasks) != 10:
        raise U05Natural360SourceProjectionError(
            f"TASK_FAMILY_COVERAGE_INCOMPLETE:{all_tasks}"
        )

    return {
        "schema_version": "a1fs.v1.u05.r360.natural360_source_projection.v1",
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "unit_number": 5,
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "route_lock": {
            "approved_route": [
                "U05_Q01_TO_Q09_CANONICAL_AUTHORITY",
                "U05_NATURAL360_RESERVOIR",
                "U05_CURRENT360",
                "U05_SPOKEN360",
                "U05_PATTERN360",
                "U05_CONTEXTUAL_ACTIVE_RUNTIME",
                "U05_20_FORMS_X_40",
                "U05_LEARNER_PDF_AFTER_RUNTIME_CUTOVER",
            ],
            "existing_q10_q10r1_q10r2_role": "PRE_CUTOVER_BASELINE_ONLY",
            "actual_pdf_path_paused_until_contextual_runtime_cutover": True,
        },
        "source_authorities": {
            "q07_task_id": str(q07["task_id"]),
            "q07_status": str(q07["status"]),
            "q07_scene_instance_count": len(q07["micro_scenes"]),
            "q07_sentence_scene_binding_count": len(q07["sentence_scene_bindings"]),
            "q08_task_id": str(q08["task_id"]),
            "q08_status": str(q08["status"]),
            "q08_communicative_function_count": len(q08["communicative_functions"]),
            "q09_task_id": str(q09["task_id"]),
            "q09_status": str(q09["status"]),
            "q09_task_family_count": len(q09["task_families"]),
            "q10_task_id": str(q10["task_id"]),
            "q10_status": str(q10["status"]),
            "q10_questionbank_item_count": len(q10["questionbank_items"]),
            "q10_form_count": len(q10["forms"]),
            "q10_runtime_role": "PRE_CUTOVER_BASELINE_ONLY",
        },
        "unit04_alignment": {
            "role": "ARCHITECTURE_AND_ACCEPTANCE_ALIGNMENT_ONLY",
            "content_authority_consumed": False,
            "learner_sentence_consumed": False,
            "scene_content_consumed": False,
            "reader_entry_consumed": False,
            "references": dict(UNIT04_ALIGNMENT_REFERENCES),
        },
        "authoring_contract": dict(AUTHORING_CONTRACT),
        "coverage": {
            "source_scene_count": len(q07["micro_scenes"]),
            "source_scene_assigned_count": sum(
                cluster["source_scene_count"] for cluster in clusters
            ),
            "source_scene_family_count": len(source_scene_family_counts),
            "source_scene_family_counts": dict(sorted(source_scene_family_counts.items())),
            "source_cluster_count": len(clusters),
            "cluster_scene_family_counts": dict(sorted(cluster_scene_family_counts.items())),
            "episode_slot_count": len(slots),
            "episodes_per_cluster": EPISODES_PER_CLUSTER,
            "discourse_family_count": len(DISCOURSE_FAMILIES),
            "frame_coverage": f"{len(all_frames)}/6",
            "polarity_coverage": f"{len(all_polarities)}/2",
            "subject_class_coverage": f"{len(all_subject_classes)}/9",
            "direct_place_relation_coverage": f"{len(all_relations)}/8",
            "communicative_function_coverage": f"{len(all_functions)}/7",
            "task_family_coverage": f"{len(all_tasks)}/10",
        },
        "source_clusters": clusters,
        "episode_authoring_slots": slots,
        "integrity": {
            "source_cluster_digest": _digest(clusters),
            "episode_slot_digest": _digest(slots),
            "q07_scene_ref_digest": _digest(
                sorted(str(row["scene_ref_id"]) for row in q07["micro_scenes"])
            ),
        },
        "scope_safety": {
            "q06_modified": False,
            "q07_modified": False,
            "q08_modified": False,
            "q09_modified": False,
            "q10_modified": False,
            "q10_active_runtime_claimed": False,
            "q10r1_final_runtime_claimed": False,
            "q10r2_final_pdf_claimed": False,
            "unit04_used_as_unit05_content_authority": False,
            "learner_facing_english_materialized": False,
            "current360_materialized": False,
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
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    report = build_unit05_natural360_source_projection()
    print(f"STATUS={report['status']}")
    print(f"SOURCE_SCENES={report['coverage']['source_scene_count']}")
    print(f"CLUSTERS={report['coverage']['source_cluster_count']}")
    print(f"EPISODE_SLOTS={report['coverage']['episode_slot_count']}")
    print(f"FRAMES={report['coverage']['frame_coverage']}")
    print(f"SUBJECTS={report['coverage']['subject_class_coverage']}")
    print(f"FUNCTIONS={report['coverage']['communicative_function_coverage']}")
    print(f"TASK_FAMILIES={report['coverage']['task_family_coverage']}")
    print(f"Q10_ROLE={report['source_authorities']['q10_runtime_role']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
