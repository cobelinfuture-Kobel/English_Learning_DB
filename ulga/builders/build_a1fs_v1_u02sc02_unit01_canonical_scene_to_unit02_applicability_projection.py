#!/usr/bin/env python3
"""Project the approved Unit01 32-scene world onto Unit02 vocabulary applicability.

U02SC02 is read-only. It reuses the current Unit01 cumulative-scene resolver
(U01QB14R1 over the U01QB07 approved scene world) and the governed U02SC01
162-noun matrix. It does not author scenes, mutate canonical identity, or connect
learner runtime.
"""
from __future__ import annotations

import re
from collections import Counter
from copy import deepcopy
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as u01qb06
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u01qb07
from ulga.builders import (
    build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix
    as u01_scene_resolver,
)
from ulga.builders import build_a1fs_v1_u02sc01_unit02_vocabulary_scene_coverage_matrix as u02sc01

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only cross-unit applicability projection over the approved Unit01 cumulative scene world and governed Unit02 vocabulary matrix; no canonical or learner-facing content is authored."

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02SC02_Unit01CanonicalSceneToUnit02ApplicabilityProjection"
SCHEMA_VERSION = "a1fs.v1.u02sc02.unit01_scene_to_unit02_applicability_projection.v1"
PASS_STATUS = "PASS_A1FS_V1_U02SC02_UNIT01_CANONICAL_SCENE_TO_UNIT02_APPLICABILITY_PROJECTION"
UNIT_ID = u02sc01.UNIT_ID
LEVEL_SCOPE = ["A1"]

EXPECTED_SCENE_COUNT = u01_scene_resolver.EXPECTED_CUMULATIVE_SCENE_WORLD_COUNT
EXPECTED_UNIT01_BINDABLE_SCENE_COUNT = u01_scene_resolver.EXPECTED_UNIT01_BINDABLE_SCENE_COUNT
EXPECTED_DEFERRED_SCENE_REFS = u01_scene_resolver.EXPECTED_DEFERRED_SCENE_REFS
EXPECTED_MODEL_SCENE_COUNT = u01qb07.EXPECTED_SUPPLEMENT_COUNT
EXPECTED_CANONICAL_SCENE_COUNT = EXPECTED_SCENE_COUNT - EXPECTED_MODEL_SCENE_COUNT
EXPECTED_VOCABULARY_COUNT = u02sc01.EXPECTED_NOUN_COUNT
EXPECTED_RELATION_COUNT = EXPECTED_SCENE_COUNT * EXPECTED_VOCABULARY_COUNT

CLASSIFICATIONS = ("DIRECT_U02", "REPROJECTION_REQUIRED", "NOT_APPLICABLE")

CANONICAL_SCENE_U02_FAMILIES: dict[str, tuple[str, ...]] = {
    "U01-C1-CLASSROOM-BAG": ("SCHOOL_CLASSROOM_LEARNING",),
    "U01-C2-HOME-TOY-BOX": ("HOME_BEDROOM_LIVING",),
    "U01-C3-PICNIC-FOOD": ("FOOD_CAFE_PICNIC", "PARK_GARDEN_NATURE"),
    "U01-C4-TOY-SHOP": ("SHOP_MONEY_SERVICES",),
    "U01-C5-PARK-BIRTHDAY": ("PARK_GARDEN_NATURE", "FAMILY_PEOPLE_SOCIAL"),
}
MODEL_FAMILY_TO_U02_FAMILIES: dict[str, tuple[str, ...]] = {
    "SCHOOL": ("SCHOOL_CLASSROOM_LEARNING",),
    "HOME": ("HOME_BEDROOM_LIVING",),
    "SHOPPING": ("SHOP_MONEY_SERVICES",),
    "OUTDOORS": ("PARK_GARDEN_NATURE",),
    "FOOD_SOCIAL": ("FOOD_CAFE_PICNIC",),
    "OUTDOORS_SOCIAL": ("PARK_GARDEN_NATURE", "FAMILY_PEOPLE_SOCIAL"),
}

NEXT_SHORT_STEP = "A1FS-V1-U02SC03_Unit02CoverageGapDrivenSceneCandidateAdmission"


class Unit02SceneApplicabilityBuildError(ValueError):
    """Fail-closed U02SC02 construction error."""


def _normalize_phrase(value: Any) -> str:
    text = str(value or "").casefold().replace("_", " ").replace("-", " ")
    return " ".join(re.findall(r"\w+", text, flags=re.UNICODE))


def _phrase_matches(target: str, surface: str) -> bool:
    target_norm = _normalize_phrase(target)
    surface_norm = _normalize_phrase(surface)
    if not target_norm or not surface_norm:
        return False
    if target_norm == surface_norm:
        return True
    target_tokens = set(target_norm.split())
    surface_tokens = set(surface_norm.split())
    return bool(target_tokens) and target_tokens <= surface_tokens


def _model_candidate_index() -> dict[str, dict[str, Any]]:
    supplement = u01_scene_resolver._read_supplement()
    rows = u01qb07.candidates(supplement)
    result = {str(row["candidate_id"]): deepcopy(row) for row in rows}
    if len(result) != EXPECTED_MODEL_SCENE_COUNT:
        raise Unit02SceneApplicabilityBuildError(f"MODEL_SCENE_COUNT_DRIFT:{len(result)}")
    return result


def _canonical_context_index() -> dict[str, dict[str, Any]]:
    result = {
        str(row["context_id"]): deepcopy(row)
        for row in u01_scene_resolver.s01.CONTEXTS
    }
    if len(result) != EXPECTED_CANONICAL_SCENE_COUNT:
        raise Unit02SceneApplicabilityBuildError(
            f"CANONICAL_CONTEXT_COUNT_DRIFT:{len(result)}"
        )
    return result


def _scene_family_projection(
    ref: str,
    source: str,
    model_candidate: Mapping[str, Any] | None,
) -> list[str]:
    if source == "CANONICAL_CONTEXT":
        values = CANONICAL_SCENE_U02_FAMILIES.get(ref)
        if values is None:
            raise Unit02SceneApplicabilityBuildError(
                f"CANONICAL_SCENE_FAMILY_MAPPING_MISSING:{ref}"
            )
        return list(values)
    if source == "MODEL_AUTHORED_APPROVED_SCENE":
        if model_candidate is None:
            raise Unit02SceneApplicabilityBuildError(f"MODEL_SCENE_CANDIDATE_MISSING:{ref}")
        family = str(model_candidate.get("large_situation_family") or "")
        values = MODEL_FAMILY_TO_U02_FAMILIES.get(family)
        if values is None:
            raise Unit02SceneApplicabilityBuildError(
                f"MODEL_SCENE_FAMILY_MAPPING_MISSING:{ref}:{family}"
            )
        return list(values)
    raise Unit02SceneApplicabilityBuildError(f"UNKNOWN_SCENE_SOURCE:{ref}:{source}")


def canonical_scene_rows() -> list[dict[str, Any]]:
    """Resolve all 32 current Unit01 scene identities and full semantic surfaces."""
    semantics = u01_scene_resolver.tolerant_scene_semantic_index()
    bindability = u01_scene_resolver.scene_bindability_index()
    canonical_contexts = _canonical_context_index()
    model_candidates = _model_candidate_index()

    expected_refs = set(canonical_contexts) | set(model_candidates)
    if set(semantics) != expected_refs:
        missing = sorted(expected_refs - set(semantics))
        extra = sorted(set(semantics) - expected_refs)
        raise Unit02SceneApplicabilityBuildError(
            f"SEMANTIC_RESOLVER_IDENTITY_DRIFT:missing={missing}:extra={extra}"
        )
    if set(bindability) != expected_refs:
        raise Unit02SceneApplicabilityBuildError("BINDABILITY_RESOLVER_IDENTITY_DRIFT")
    if len(expected_refs) != EXPECTED_SCENE_COUNT:
        raise Unit02SceneApplicabilityBuildError(
            f"CUMULATIVE_SCENE_COUNT_DRIFT:{len(expected_refs)}"
        )

    rows: list[dict[str, Any]] = []
    for ref in sorted(expected_refs):
        semantic = semantics[ref]
        gate = bindability[ref]
        source = str(semantic.get("source") or "")
        model_candidate = model_candidates.get(ref)
        if source == "CANONICAL_CONTEXT":
            context = canonical_contexts.get(ref)
            if context is None:
                raise Unit02SceneApplicabilityBuildError(
                    f"CANONICAL_CONTEXT_RESOLUTION_MISSING:{ref}"
                )
            extracted = u01qb06.extract_context_semantics(context["sentences"])
            objects = [_normalize_phrase(value) for value in extracted["objects"]]
            actions = [_normalize_phrase(value) for value in extracted["actions"]]
            relations = [_normalize_phrase(value) for value in extracted["relations"]]
            setting = str(context["setting"])
            event = str(context["title"])
            communicative_goal = ""
            scene_origin = "CANONICAL_UNIT01_CONTEXT"
        elif source == "MODEL_AUTHORED_APPROVED_SCENE":
            if model_candidate is None:
                raise Unit02SceneApplicabilityBuildError(
                    f"MODEL_SCENE_RESOLUTION_MISSING:{ref}"
                )
            objects = [_normalize_phrase(value) for value in model_candidate.get("objects", [])]
            actions = [_normalize_phrase(value) for value in model_candidate.get("actions", [])]
            relations = [_normalize_phrase(value) for value in model_candidate.get("relations", [])]
            setting = str(model_candidate.get("medium_setting") or "")
            event = str(model_candidate.get("small_micro_scene_event") or "")
            communicative_goal = str(model_candidate.get("communicative_goal") or "")
            scene_origin = "MODEL_AUTHORED_SCENE_ENRICHMENT"
        else:
            raise Unit02SceneApplicabilityBuildError(
                f"SCENE_SOURCE_RESOLUTION_INVALID:{ref}:{source}"
            )

        if bool(semantic.get("unit_runtime_bindable")) != bool(gate["runtime_bindable"]):
            raise Unit02SceneApplicabilityBuildError(f"SCENE_BINDABILITY_DRIFT:{ref}")
        anchors = sorted(_normalize_phrase(value) for value in gate.get("anchors", []))
        rows.append(
            {
                "scene_ref_id": ref,
                "scene_origin": scene_origin,
                "source": source,
                "objects": sorted(set(objects)),
                "anchors": anchors,
                "setting": setting,
                "event": event,
                "actions": sorted(set(actions)),
                "relations": sorted(set(relations)),
                "communicative_goal": communicative_goal,
                "unit01_runtime_bindable": bool(gate["runtime_bindable"]),
                "unit01_gate_reason": str(gate["gate_reason"]),
                "u02_scene_families": _scene_family_projection(ref, source, model_candidate),
            }
        )

    if len(rows) != EXPECTED_SCENE_COUNT:
        raise Unit02SceneApplicabilityBuildError(
            f"RESOLVED_SCENE_COUNT_INVALID:{len(rows)}"
        )
    deferred = sorted(
        row["scene_ref_id"] for row in rows if not row["unit01_runtime_bindable"]
    )
    if tuple(deferred) != EXPECTED_DEFERRED_SCENE_REFS:
        raise Unit02SceneApplicabilityBuildError(f"DEFERRED_SCENE_SET_DRIFT:{deferred}")
    return rows


def semantic_match_evidence(scene: Mapping[str, Any], singular: str) -> list[str]:
    evidence: list[str] = []
    for value in scene.get("objects") or []:
        if _phrase_matches(singular, str(value)):
            evidence.append(f"OBJECT:{_normalize_phrase(value)}")
    for key in ("setting", "event"):
        value = str(scene.get(key) or "")
        if _phrase_matches(singular, value):
            evidence.append(f"{key.upper()}:{_normalize_phrase(value)}")
    return sorted(set(evidence))


def anchor_match(scene: Mapping[str, Any], singular: str) -> bool:
    return any(
        _phrase_matches(singular, str(value)) for value in scene.get("anchors") or []
    )


def family_compatible(scene: Mapping[str, Any], vocab_row: Mapping[str, Any]) -> bool:
    allowed = {
        str(vocab_row["primary_scene_family"]),
        *[str(value) for value in vocab_row.get("secondary_scene_families") or []],
    }
    return bool(set(scene.get("u02_scene_families") or []) & allowed)


def classify_relation(
    scene: Mapping[str, Any],
    vocab_row: Mapping[str, Any],
) -> tuple[str, list[str], list[str], bool]:
    singular = str(vocab_row["singular"])
    gate = str(vocab_row["scene_gate"])
    evidence = semantic_match_evidence(scene, singular)
    compatible = family_compatible(scene, vocab_row)

    if gate in {"PEDAGOGICAL_DEFER", "SUPPORT_ONLY", "SEMANTICALLY_INAPPLICABLE"}:
        reason = (
            "U02SC01_PEDAGOGICAL_DEFER"
            if gate == "PEDAGOGICAL_DEFER"
            else "U02SC01_SUPPORT_OR_SEMANTIC_GATE_NOT_PRIMARY_SCENE_DRIVER"
        )
        return "NOT_APPLICABLE", [reason], evidence, compatible

    if not evidence:
        return (
            "NOT_APPLICABLE",
            ["TARGET_NOUN_NOT_PRESENT_IN_EXISTING_SCENE_SEMANTICS"],
            evidence,
            compatible,
        )

    if gate == "SENSE_CHECK_REQUIRED":
        return (
            "REPROJECTION_REQUIRED",
            ["U02SC01_SENSE_REVIEW_REQUIRED_BEFORE_DIRECT_BINDING"],
            evidence,
            compatible,
        )

    if scene.get("unit01_runtime_bindable") is True and anchor_match(scene, singular):
        return (
            "DIRECT_U02",
            ["EXISTING_SCENE_SEMANTICS_AND_UNIT01_LANGUAGE_ANCHOR_PRESENT"],
            evidence,
            compatible,
        )

    return (
        "REPROJECTION_REQUIRED",
        ["EXISTING_SCENE_SEMANTICS_PRESENT_BUT_UNIT01_LANGUAGE_ANCHOR_ABSENT"],
        evidence,
        compatible,
    )


def build_relations(
    scenes: list[dict[str, Any]],
    vocabulary_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for scene in scenes:
        for vocab_row in vocabulary_rows:
            classification, reasons, evidence, compatible = classify_relation(
                scene, vocab_row
            )
            relations.append(
                {
                    "scene_ref_id": scene["scene_ref_id"],
                    "singular": vocab_row["singular"],
                    "classification": classification,
                    "reason_codes": reasons,
                    "semantic_match_evidence": evidence,
                    "family_compatible": compatible,
                }
            )
    if len(relations) != EXPECTED_RELATION_COUNT:
        raise Unit02SceneApplicabilityBuildError(
            f"RELATION_COUNT_INVALID:{len(relations)}"
        )
    return relations


def build_vocabulary_summary(
    vocabulary_rows: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_singular: dict[str, list[dict[str, Any]]] = {}
    for relation in relations:
        by_singular.setdefault(str(relation["singular"]), []).append(relation)

    summaries: list[dict[str, Any]] = []
    for vocab_row in vocabulary_rows:
        singular = str(vocab_row["singular"])
        related = by_singular.get(singular, [])
        direct = sorted(
            row["scene_ref_id"]
            for row in related
            if row["classification"] == "DIRECT_U02"
        )
        reproject = sorted(
            row["scene_ref_id"]
            for row in related
            if row["classification"] == "REPROJECTION_REQUIRED"
        )
        family_candidates = sorted(
            row["scene_ref_id"] for row in related if row["family_compatible"]
        )
        semantic_reuse = sorted(set(direct) | set(reproject))
        scene_gate = str(vocab_row["scene_gate"])
        missing = scene_gate == "DIRECT_SCENE_ELIGIBLE" and not semantic_reuse
        summaries.append(
            {
                "singular": singular,
                "scene_gate": scene_gate,
                "direct_scene_refs": direct,
                "reprojection_scene_refs": reproject,
                "semantic_reuse_scene_refs": semantic_reuse,
                "family_compatible_scene_refs": family_candidates,
                "genuine_missing_new_unit02_scene_need": missing,
                "missing_reason": (
                    "DIRECT_ELIGIBLE_NOUN_HAS_NO_SEMANTIC_MATCH_IN_CURRENT_32_SCENE_WORLD"
                    if missing
                    else ""
                ),
            }
        )
    if len(summaries) != EXPECTED_VOCABULARY_COUNT:
        raise Unit02SceneApplicabilityBuildError(
            f"VOCABULARY_SUMMARY_COUNT_INVALID:{len(summaries)}"
        )
    return summaries


def payload() -> dict[str, Any]:
    scenes = canonical_scene_rows()
    vocabulary_rows = u02sc01.build_rows()
    relations = build_relations(scenes, vocabulary_rows)
    summaries = build_vocabulary_summary(vocabulary_rows, relations)

    classification_counts = Counter(row["classification"] for row in relations)
    source_counts = Counter(row["source"] for row in scenes)
    missing = [
        row["singular"]
        for row in summaries
        if row["genuine_missing_new_unit02_scene_need"]
    ]
    direct_covered = sum(bool(row["direct_scene_refs"]) for row in summaries)
    reprojection_only = sum(
        not row["direct_scene_refs"] and bool(row["reprojection_scene_refs"])
        for row in summaries
    )
    gated_without_scene_claim = sum(
        not row["semantic_reuse_scene_refs"]
        and row["scene_gate"] != "DIRECT_SCENE_ELIGIBLE"
        for row in summaries
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "level_scope": LEVEL_SCOPE,
        "source_authority": {
            "unit01_cumulative_scene_task_id": u01qb07.TASK_ID,
            "unit01_resolver_module": u01_scene_resolver.__name__,
            "unit01_resolver_function": "tolerant_scene_semantic_index",
            "unit01_semantic_extractor_module": u01qb06.__name__,
            "unit01_cumulative_scene_count": EXPECTED_SCENE_COUNT,
            "unit01_canonical_context_count": EXPECTED_CANONICAL_SCENE_COUNT,
            "unit01_model_scene_count": EXPECTED_MODEL_SCENE_COUNT,
            "unit01_runtime_bindable_scene_count": EXPECTED_UNIT01_BINDABLE_SCENE_COUNT,
            "unit01_deferred_scene_refs": list(EXPECTED_DEFERRED_SCENE_REFS),
            "unit02_scene_matrix_task_id": u02sc01.TASK_ID,
            "unit02_vocabulary_surface_count": EXPECTED_VOCABULARY_COUNT,
        },
        "scene_rows": scenes,
        "relations": relations,
        "vocabulary_summary": summaries,
        "coverage_denominators": {
            "unit01_cumulative_scene_count": len(scenes),
            "unit02_vocabulary_surface_count": len(vocabulary_rows),
            "scene_vocabulary_relation_count": len(relations),
            "classification_counts": dict(sorted(classification_counts.items())),
            "scene_source_counts": dict(sorted(source_counts.items())),
            "direct_covered_vocabulary_count": direct_covered,
            "reprojection_only_vocabulary_count": reprojection_only,
            "genuine_missing_new_unit02_scene_need_count": len(missing),
            "genuine_missing_new_unit02_scene_need_singulars": missing,
            "gated_without_scene_gap_claim_count": gated_without_scene_claim,
        },
        "projection_contract": {
            "u01qb07_is_cumulative_scene_authority": True,
            "u01qb14r1_resolver_is_reused_not_reimplemented": True,
            "all_32_cumulative_scenes_including_unit01_deferred_scene_are_projected": True,
            "family_compatibility_alone_does_not_claim_scene_reuse": True,
            "semantic_presence_is_required_for_direct_or_reprojection_reuse": True,
            "unit02_new_scene_need_is_claimed_only_for_direct_eligible_uncovered_nouns": True,
            "sense_check_support_only_and_pedagogical_defer_rows_do_not_create_gap_claims": True,
        },
        "claim_boundaries": {
            "canonical_scene_authority_mutated": False,
            "unit01_scene_authority_mutated": False,
            "unit02_vocabulary_authority_mutated": False,
            "new_scene_created": False,
            "questionbank_mutated": False,
            "learner_runtime_connected": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    value = payload()
    counts = value["coverage_denominators"]
    print(f"STATUS={PASS_STATUS}")
    print(f"UNIT01_SCENES={counts['unit01_cumulative_scene_count']}")
    print(f"UNIT02_VOCABULARY={counts['unit02_vocabulary_surface_count']}")
    print(f"RELATIONS={counts['scene_vocabulary_relation_count']}")
    print(f"CLASSIFICATIONS={counts['classification_counts']}")
    print(
        "GENUINE_MISSING_NEW_UNIT02_SCENE_NEEDS="
        f"{counts['genuine_missing_new_unit02_scene_need_count']}"
    )
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
