#!/usr/bin/env python3
"""Validate the Unit01 32-scene to Unit02 applicability projection."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u02sc02_unit01_canonical_scene_to_unit02_applicability_projection
    as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U02SC02_UNIT01_CANONICAL_SCENE_TO_UNIT02_APPLICABILITY_PROJECTION_VALIDATOR"


class Unit02SceneApplicabilityValidationError(ValueError):
    """Fail-closed U02SC02 validation error."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Unit02SceneApplicabilityValidationError(code)


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")
    require(payload.get("level_scope") == ["A1"], "LEVEL_SCOPE_INVALID")

    scenes = payload.get("scene_rows")
    require(isinstance(scenes, list), "SCENE_ROWS_NOT_LIST")
    require(len(scenes) == builder.EXPECTED_SCENE_COUNT, "SCENE_COUNT_INVALID")
    scene_refs = [str(row.get("scene_ref_id") or "") for row in scenes]
    require(all(scene_refs), "SCENE_REF_EMPTY")
    require(len(scene_refs) == len(set(scene_refs)), "SCENE_REF_DUPLICATE")

    source_counts = Counter(str(row.get("source") or "") for row in scenes)
    require(
        source_counts["CANONICAL_CONTEXT"] == builder.EXPECTED_CANONICAL_SCENE_COUNT,
        "CANONICAL_SCENE_COUNT_INVALID",
    )
    require(
        source_counts["MODEL_AUTHORED_APPROVED_SCENE"] == builder.EXPECTED_MODEL_SCENE_COUNT,
        "MODEL_SCENE_COUNT_INVALID",
    )
    deferred = sorted(
        str(row["scene_ref_id"])
        for row in scenes
        if row.get("unit01_runtime_bindable") is False
    )
    require(
        deferred == list(builder.EXPECTED_DEFERRED_SCENE_REFS),
        "DEFERRED_SCENE_SET_INVALID",
    )
    for scene in scenes:
        require(isinstance(scene.get("objects"), list), "SCENE_OBJECTS_INVALID")
        require(isinstance(scene.get("anchors"), list), "SCENE_ANCHORS_INVALID")
        require(bool(scene.get("setting")), "SCENE_SETTING_EMPTY")
        families = scene.get("u02_scene_families")
        require(isinstance(families, list) and families, "SCENE_U02_FAMILY_INVALID")
        require(
            all(value in builder.u02sc01.SCENE_FAMILIES for value in families),
            "SCENE_U02_FAMILY_UNKNOWN",
        )

    require(scenes == builder.canonical_scene_rows(), "CURRENT_SCENE_AUTHORITY_DRIFT")

    relations = payload.get("relations")
    require(isinstance(relations, list), "RELATIONS_NOT_LIST")
    require(len(relations) == builder.EXPECTED_RELATION_COUNT, "RELATION_COUNT_INVALID")
    pair_keys = {
        (str(row.get("scene_ref_id") or ""), str(row.get("singular") or ""))
        for row in relations
    }
    require(
        len(pair_keys) == builder.EXPECTED_RELATION_COUNT,
        "RELATION_CARTESIAN_IDENTITY_INVALID",
    )
    require(
        all(row.get("classification") in builder.CLASSIFICATIONS for row in relations),
        "RELATION_CLASSIFICATION_INVALID",
    )
    require(
        all(isinstance(row.get("semantic_match_evidence"), list) for row in relations),
        "RELATION_EVIDENCE_INVALID",
    )
    require(
        all(isinstance(row.get("family_compatible"), bool) for row in relations),
        "RELATION_FAMILY_FLAG_INVALID",
    )

    vocabulary_rows = builder.u02sc01.build_rows()
    vocab_by_singular = {str(row["singular"]): row for row in vocabulary_rows}
    scene_by_ref = {str(row["scene_ref_id"]): row for row in scenes}
    for relation in relations:
        ref = str(relation["scene_ref_id"])
        singular = str(relation["singular"])
        require(ref in scene_by_ref, f"RELATION_SCENE_UNKNOWN:{ref}")
        require(singular in vocab_by_singular, f"RELATION_VOCAB_UNKNOWN:{singular}")
        expected = builder.classify_relation(scene_by_ref[ref], vocab_by_singular[singular])
        require(relation["classification"] == expected[0], f"CLASSIFICATION_DRIFT:{ref}:{singular}")
        require(relation["reason_codes"] == expected[1], f"REASON_DRIFT:{ref}:{singular}")
        require(
            relation["semantic_match_evidence"] == expected[2],
            f"EVIDENCE_DRIFT:{ref}:{singular}",
        )
        require(
            relation["family_compatible"] == expected[3],
            f"FAMILY_COMPATIBILITY_DRIFT:{ref}:{singular}",
        )

    summaries = payload.get("vocabulary_summary")
    require(isinstance(summaries, list), "VOCABULARY_SUMMARY_NOT_LIST")
    require(
        len(summaries) == builder.EXPECTED_VOCABULARY_COUNT,
        "VOCABULARY_SUMMARY_COUNT_INVALID",
    )
    require(
        {str(row.get("singular") or "") for row in summaries} == set(vocab_by_singular),
        "VOCABULARY_SUMMARY_COVERAGE_INVALID",
    )

    relations_by_singular: dict[str, list[Mapping[str, Any]]] = {}
    for relation in relations:
        relations_by_singular.setdefault(str(relation["singular"]), []).append(relation)
    for summary in summaries:
        singular = str(summary["singular"])
        source = vocab_by_singular[singular]
        related = relations_by_singular[singular]
        direct = sorted(
            str(row["scene_ref_id"])
            for row in related
            if row["classification"] == "DIRECT_U02"
        )
        reproject = sorted(
            str(row["scene_ref_id"])
            for row in related
            if row["classification"] == "REPROJECTION_REQUIRED"
        )
        semantic = sorted(set(direct) | set(reproject))
        family = sorted(
            str(row["scene_ref_id"]) for row in related if row["family_compatible"]
        )
        require(summary["direct_scene_refs"] == direct, f"DIRECT_SUMMARY_DRIFT:{singular}")
        require(
            summary["reprojection_scene_refs"] == reproject,
            f"REPROJECTION_SUMMARY_DRIFT:{singular}",
        )
        require(
            summary["semantic_reuse_scene_refs"] == semantic,
            f"SEMANTIC_REUSE_SUMMARY_DRIFT:{singular}",
        )
        require(
            summary["family_compatible_scene_refs"] == family,
            f"FAMILY_SUMMARY_DRIFT:{singular}",
        )
        expected_missing = source["scene_gate"] == "DIRECT_SCENE_ELIGIBLE" and not semantic
        require(
            summary["genuine_missing_new_unit02_scene_need"] is expected_missing,
            f"MISSING_GAP_CLAIM_DRIFT:{singular}",
        )
        if source["scene_gate"] != "DIRECT_SCENE_ELIGIBLE":
            require(
                summary["genuine_missing_new_unit02_scene_need"] is False,
                f"GATED_ROW_FALSE_GAP_REQUIRED:{singular}",
            )

    counts = payload.get("coverage_denominators", {})
    classification_counts = Counter(str(row["classification"]) for row in relations)
    require(
        counts.get("unit01_cumulative_scene_count") == builder.EXPECTED_SCENE_COUNT,
        "DENOMINATOR_SCENE_COUNT_INVALID",
    )
    require(
        counts.get("unit02_vocabulary_surface_count") == builder.EXPECTED_VOCABULARY_COUNT,
        "DENOMINATOR_VOCAB_COUNT_INVALID",
    )
    require(
        counts.get("scene_vocabulary_relation_count") == builder.EXPECTED_RELATION_COUNT,
        "DENOMINATOR_RELATION_COUNT_INVALID",
    )
    require(
        counts.get("classification_counts") == dict(sorted(classification_counts.items())),
        "CLASSIFICATION_COUNTS_INVALID",
    )
    missing = [
        str(row["singular"])
        for row in summaries
        if row["genuine_missing_new_unit02_scene_need"]
    ]
    require(
        counts.get("genuine_missing_new_unit02_scene_need_count") == len(missing),
        "MISSING_SCENE_COUNT_INVALID",
    )
    require(
        counts.get("genuine_missing_new_unit02_scene_need_singulars") == missing,
        "MISSING_SCENE_SET_INVALID",
    )

    source = payload.get("source_authority", {})
    require(
        source.get("unit01_cumulative_scene_task_id") == builder.u01qb07.TASK_ID,
        "UNIT01_SOURCE_TASK_INVALID",
    )
    require(
        source.get("unit01_resolver_module") == builder.u01_scene_resolver.__name__,
        "UNIT01_RESOLVER_MODULE_INVALID",
    )
    require(
        source.get("unit01_resolver_function") == "tolerant_scene_semantic_index",
        "UNIT01_RESOLVER_FUNCTION_INVALID",
    )
    require(
        source.get("unit01_cumulative_scene_count") == builder.EXPECTED_SCENE_COUNT,
        "UNIT01_SOURCE_COUNT_INVALID",
    )
    require(
        source.get("unit01_runtime_bindable_scene_count")
        == builder.EXPECTED_UNIT01_BINDABLE_SCENE_COUNT,
        "UNIT01_BINDABLE_SOURCE_COUNT_INVALID",
    )
    require(
        source.get("unit01_deferred_scene_refs") == list(builder.EXPECTED_DEFERRED_SCENE_REFS),
        "UNIT01_DEFERRED_SOURCE_INVALID",
    )
    require(
        source.get("unit02_scene_matrix_task_id") == builder.u02sc01.TASK_ID,
        "UNIT02_SOURCE_TASK_INVALID",
    )

    contract = payload.get("projection_contract", {})
    for key in (
        "u01qb07_is_cumulative_scene_authority",
        "u01qb14r1_resolver_is_reused_not_reimplemented",
        "all_32_cumulative_scenes_including_unit01_deferred_scene_are_projected",
        "family_compatibility_alone_does_not_claim_scene_reuse",
        "semantic_presence_is_required_for_direct_or_reprojection_reuse",
        "unit02_new_scene_need_is_claimed_only_for_direct_eligible_uncovered_nouns",
        "sense_check_support_only_and_pedagogical_defer_rows_do_not_create_gap_claims",
    ):
        require(contract.get(key) is True, f"PROJECTION_CONTRACT_INVALID:{key}")

    boundaries = payload.get("claim_boundaries", {})
    for key in (
        "canonical_scene_authority_mutated",
        "unit01_scene_authority_mutated",
        "unit02_vocabulary_authority_mutated",
        "new_scene_created",
        "questionbank_mutated",
        "learner_runtime_connected",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")

    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_SHORT_STEP_INVALID")

    return {
        "status": builder.PASS_STATUS,
        "error_count": 0,
        "errors": [],
        "unit01_scene_count": len(scenes),
        "unit02_vocabulary_count": len(summaries),
        "relation_count": len(relations),
        "classification_counts": dict(sorted(classification_counts.items())),
        "genuine_missing_new_unit02_scene_need_count": len(missing),
    }


def main() -> int:
    report = validate_payload(builder.payload())
    print(f"STATUS={report['status']}")
    print(f"UNIT01_SCENES={report['unit01_scene_count']}")
    print(f"UNIT02_VOCABULARY={report['unit02_vocabulary_count']}")
    print(f"RELATIONS={report['relation_count']}")
    print(f"CLASSIFICATIONS={report['classification_counts']}")
    print(
        "GENUINE_MISSING_NEW_UNIT02_SCENE_NEEDS="
        f"{report['genuine_missing_new_unit02_scene_need_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
