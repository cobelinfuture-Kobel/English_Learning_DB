#!/usr/bin/env python3
"""Independently validate CP04 candidate envelopes against the CP03 binding."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as builder  # noqa: E402


def _candidate_id(kind: str, *parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"A1FS_CP04_{kind}_{digest}"


def _safe_scan(value: Any) -> list[str]:
    forbidden = {
        "text",
        "title",
        "payload",
        "prompt",
        "prompt_text",
        "answer",
        "answer_key",
        "accepted_texts",
        "transcript",
        "transcript_text",
        "learner_response",
    }
    errors: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden:
                    errors.append(f"private_or_learner_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return errors


def _expected_m11b(
    unit: Mapping[str, Any], errors: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    learning_unit_id = str(unit.get("learning_unit_id") or "")
    source = unit.get("m11b_reviewed_content_binding", {})
    by_skill = source.get("admitted_item_ids_by_skill", {})
    if not isinstance(by_skill, Mapping):
        errors.append(f"m11b_skill_partition_invalid:{learning_unit_id}")
        return [], []
    content: list[dict[str, Any]] = []
    exercises: list[dict[str, Any]] = []
    for skill in builder.SKILLS:
        item_ids = by_skill.get(skill, [])
        if not isinstance(item_ids, list):
            errors.append(f"m11b_item_ids_invalid:{learning_unit_id}:{skill}")
            continue
        for item_id_value in item_ids:
            item_id = str(item_id_value or "")
            content_id = _candidate_id("CONTENT_M11B", learning_unit_id, skill, item_id)
            content.append(
                {
                    "content_candidate_id": content_id,
                    "source_kind": "M11B_REVIEWED_SHARED_ITEM",
                    "source_ref": item_id,
                    "source_task_id": source.get("source_task_id"),
                    "skill": skill,
                    "candidate_state": "ADMITTED_PRIVATE_SOURCE_BOUND",
                    "private_source_access_required": True,
                }
            )
            exercises.append(
                {
                    "exercise_candidate_id": _candidate_id(
                        "EXERCISE_M11B", learning_unit_id, skill, item_id
                    ),
                    "content_candidate_id": content_id,
                    "source_kind": "M11B_REVIEWED_SHARED_ITEM",
                    "source_ref": item_id,
                    "target_skill_lanes": [skill],
                    "candidate_mode": "REUSE_EXISTING_REVIEWED_EXERCISE",
                    "candidate_state": "READY_FOR_PRIVATE_POPULATION",
                    "new_content_authoring_required": False,
                }
            )
    return content, exercises


def _expected_raz(
    unit: Mapping[str, Any], errors: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    learning_unit_id = str(unit.get("learning_unit_id") or "")
    grammar_unit_id = str(unit.get("grammar_unit_id") or "")
    materials = unit.get("raz_admitted_asset_binding", {}).get("materials", [])
    if not isinstance(materials, list):
        errors.append(f"raz_material_partition_invalid:{learning_unit_id}")
        return [], []
    content: list[dict[str, Any]] = []
    exercises: list[dict[str, Any]] = []
    for material in materials:
        if not isinstance(material, Mapping):
            errors.append(f"raz_material_row_invalid:{learning_unit_id}")
            continue
        material_id = str(material.get("material_id") or "")
        scope = str(material.get("candidate_cefr_scope") or "")
        content_id = _candidate_id("CONTENT_RAZ", learning_unit_id, material_id)
        content.append(
            {
                "content_candidate_id": content_id,
                "source_kind": "RAZ_PROMOTED_MATERIAL",
                "source_ref": material_id,
                "grammar_authority_ref": grammar_unit_id,
                "candidate_cefr_scope": scope,
                "candidate_state": "PRIVATE_SOURCE_MATERIALIZATION_REQUIRED",
                "private_source_access_required": True,
            }
        )
        exercises.append(
            {
                "exercise_candidate_id": _candidate_id(
                    "EXERCISE_RAZ", learning_unit_id, material_id
                ),
                "content_candidate_id": content_id,
                "source_kind": "RAZ_PROMOTED_MATERIAL",
                "source_ref": material_id,
                "target_skill_lanes": [],
                "candidate_mode": "DERIVE_FROM_PRIVATE_RAZ_SOURCE",
                "candidate_state": "PENDING_PRIVATE_SOURCE_AND_SKILL_AFFORDANCE",
                "new_content_authoring_required": True,
            }
        )
    return content, exercises


def _expected_scenes(unit: Mapping[str, Any]) -> list[dict[str, Any]]:
    learning_unit_id = str(unit.get("learning_unit_id") or "")
    binding = unit.get("cp02_authority_bindings", {}).get("theme_situation", {})
    return [
        {
            "scene_candidate_id": _candidate_id("SCENE", learning_unit_id, str(ref)),
            "theme_situation_ref": str(ref),
            "candidate_state": "AUTHORITY_BACKED_METADATA_READY",
            "source_query_ref": binding.get("source_query_ref"),
            "scene_materialized": False,
        }
        for ref in binding.get("selected_refs", [])
    ]


def _population_status(content_count: int, exercise_count: int, scene_count: int) -> str:
    if content_count and exercise_count and scene_count:
        return "CONTENT_EXERCISE_AND_SCENE_CANDIDATES_AVAILABLE"
    if content_count and exercise_count:
        return "CONTENT_AND_EXERCISE_CANDIDATES_AVAILABLE_SCENE_PENDING"
    if scene_count:
        return "SCENE_CANDIDATES_AVAILABLE_CONTENT_PENDING"
    return "NO_CANDIDATE_POPULATION"


def validate_artifact(
    artifact: Mapping[str, Any], cp03_artifact: Mapping[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    if artifact.get("task_id") != builder.TASK_ID:
        errors.append("task_id_mismatch")
    if artifact.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY":
        errors.append("scope_mismatch")

    expected_contract = {
        "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
        "source_binding_task_id": builder.cp03.TASK_ID,
        "content_sources": [
            "M11B_REVIEWED_SHARED_ITEMS",
            "RAZ_AI_ACL_S05_PROMOTED_MATERIALS",
        ],
        "m11b_exercise_handling": "REUSE_EXISTING_REVIEWED_SHARED_ITEM",
        "raz_exercise_handling": "PENDING_PRIVATE_SOURCE_AND_SKILL_AFFORDANCE",
        "scene_handling": "SOURCE_PROVEN_THEME_SITUATION_REFS_ONLY",
        "new_unit_creation_allowed": False,
        "private_source_read_performed": False,
        "learner_facing_publication_allowed": False,
    }
    if artifact.get("candidate_contract") != expected_contract:
        errors.append("candidate_contract_mismatch")

    source_units = cp03_artifact.get("learning_units", [])
    output_units = artifact.get("learning_units", [])
    if not isinstance(source_units, list) or len(source_units) != 24:
        errors.append("cp03_source_unit_count_not_24")
        source_units = []
    if not isinstance(output_units, list) or len(output_units) != 24:
        errors.append("output_learning_unit_count_not_24")
        output_units = []
    source_by_id = {
        str(row.get("learning_unit_id") or ""): row
        for row in source_units
        if isinstance(row, Mapping)
    }
    output_by_id = {
        str(row.get("learning_unit_id") or ""): row
        for row in output_units
        if isinstance(row, Mapping)
    }
    if len(source_by_id) != 24 or set(output_by_id) != set(source_by_id):
        errors.append("existing_24_unit_identity_set_mismatch")
    if [row.get("sequence_index") for row in output_units] != list(range(1, 25)):
        errors.append("unit_sequence_mismatch")

    all_content_ids: set[str] = set()
    all_exercise_ids: set[str] = set()
    all_scene_ids: set[str] = set()
    m11b_refs: set[str] = set()
    raz_refs: set[str] = set()
    m11b_count = 0
    raz_binding_count = 0
    scene_count = 0
    scene_units = 0
    units_with_content = 0
    candidate_envelope_complete_unit_count = 0

    for source in source_units:
        learning_unit_id = str(source.get("learning_unit_id") or "")
        row = output_by_id.get(learning_unit_id)
        if row is None:
            continue
        identity = (
            row.get("grammar_unit_id"),
            row.get("sequence_index"),
            row.get("internal_stage"),
            row.get("canonical_egp_row_ids"),
        )
        expected_identity = (
            source.get("grammar_unit_id"),
            source.get("sequence_index"),
            source.get("internal_stage"),
            source.get("canonical_egp_row_ids"),
        )
        if identity != expected_identity:
            errors.append(f"unit_identity_drift:{learning_unit_id}")

        expected_m11b_content, expected_m11b_exercises = _expected_m11b(source, errors)
        expected_raz_content, expected_raz_exercises = _expected_raz(source, errors)
        expected_content = expected_m11b_content + expected_raz_content
        expected_exercises = expected_m11b_exercises + expected_raz_exercises
        expected_scenes = _expected_scenes(source)

        if row.get("content_candidates") != expected_content:
            errors.append(f"content_candidate_drift:{learning_unit_id}")
        if row.get("exercise_candidates") != expected_exercises:
            errors.append(f"exercise_candidate_drift:{learning_unit_id}")
        if row.get("scene_candidates") != expected_scenes:
            errors.append(f"scene_candidate_drift:{learning_unit_id}")

        content_ids = {item["content_candidate_id"] for item in expected_content}
        exercise_ids = {item["exercise_candidate_id"] for item in expected_exercises}
        scene_ids = {item["scene_candidate_id"] for item in expected_scenes}
        if all_content_ids & content_ids:
            errors.append("content_candidate_id_collision")
        if all_exercise_ids & exercise_ids:
            errors.append("exercise_candidate_id_collision")
        if all_scene_ids & scene_ids:
            errors.append("scene_candidate_id_collision")
        all_content_ids |= content_ids
        all_exercise_ids |= exercise_ids
        all_scene_ids |= scene_ids

        unit_m11b_refs = {item["source_ref"] for item in expected_m11b_content}
        if m11b_refs & unit_m11b_refs:
            errors.append("m11b_source_ref_reused_across_units")
        m11b_refs |= unit_m11b_refs
        raz_refs |= {item["source_ref"] for item in expected_raz_content}

        expected_counts = {
            "m11b_content_candidate_count": len(expected_m11b_content),
            "raz_content_candidate_count": len(expected_raz_content),
            "content_candidate_count": len(expected_content),
            "ready_reuse_exercise_candidate_count": len(expected_m11b_exercises),
            "pending_raz_exercise_derivation_candidate_count": len(expected_raz_exercises),
            "exercise_candidate_count": len(expected_exercises),
            "scene_candidate_count": len(expected_scenes),
        }
        if row.get("candidate_counts") != expected_counts:
            errors.append(f"candidate_counts_mismatch:{learning_unit_id}")
        if row.get("candidate_population_status") != _population_status(
            len(expected_content), len(expected_exercises), len(expected_scenes)
        ):
            errors.append(f"candidate_population_status_mismatch:{learning_unit_id}")

        m11b_count += len(expected_m11b_content)
        raz_binding_count += len(expected_raz_content)
        scene_count += len(expected_scenes)
        scene_units += bool(expected_scenes)
        units_with_content += bool(expected_content)
        candidate_envelope_complete_unit_count += bool(
            expected_content and expected_exercises and expected_scenes
        )

    expected_summary = {
        "existing_learning_unit_count": 24,
        "new_learning_unit_count": 0,
        "m11b_reviewed_content_candidate_count": m11b_count,
        "raz_material_binding_candidate_count": raz_binding_count,
        "distinct_raz_material_source_count": len(raz_refs),
        "distinct_content_source_ref_count": len(m11b_refs | raz_refs),
        "content_candidate_count": len(all_content_ids),
        "exercise_candidate_count": len(all_exercise_ids),
        "ready_reuse_exercise_candidate_count": m11b_count,
        "pending_raz_exercise_derivation_candidate_count": raz_binding_count,
        "scene_candidate_count": scene_count,
        "authority_backed_scene_unit_count": scene_units,
        "scene_authority_gap_unit_count": 24 - scene_units,
        "units_with_any_content_candidate": units_with_content,
        "candidate_envelope_complete_unit_count": candidate_envelope_complete_unit_count,
    }
    if artifact.get("coverage_summary") != expected_summary:
        errors.append("coverage_summary_not_reconciled")
    cp03_summary = cp03_artifact.get("coverage_summary", {})
    if m11b_count != cp03_summary.get("m11b_reviewed_content_item_count"):
        errors.append("m11b_count_not_bound_to_cp03")
    if raz_binding_count != cp03_summary.get("raz_material_unit_binding_count"):
        errors.append("raz_binding_count_not_bound_to_cp03")
    if len(raz_refs) != cp03_summary.get("raz_distinct_bound_material_count"):
        errors.append("raz_distinct_count_not_bound_to_cp03")

    expected_source_identity = {
        "cp03_task_id": cp03_artifact.get("task_id"),
        "cp03_sha256": builder._sha256_value(cp03_artifact),
        "cp03_cp01_sha256": cp03_artifact.get("source_identity", {}).get("cp01_sha256"),
        "cp03_cp02_sha256": cp03_artifact.get("source_identity", {}).get("cp02_sha256"),
        "cp03_raz_registry_package_sha256": cp03_artifact.get("source_identity", {}).get(
            "raz_registry_package_sha256"
        ),
    }
    if artifact.get("source_identity") != expected_source_identity:
        errors.append("source_identity_mismatch")

    expected_delta = {
        "unified_content_candidate_envelopes_created": True,
        "exercise_candidate_envelopes_created": True,
        "authority_backed_scene_candidate_envelopes_created": True,
        "existing_24_unit_curriculum_preserved": True,
    }
    if artifact.get("capability_delta") != expected_delta:
        errors.append("capability_delta_mismatch")
    for key, value in artifact.get("claim_boundaries", {}).items():
        if value is not False:
            errors.append(f"false_claim_boundary:{key}")
    errors.extend(_safe_scan(artifact))
    if artifact.get("stop_reason") != "NONE":
        errors.append("stop_reason_mismatch")
    if artifact.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("next_short_step_mismatch")

    return {
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL",
        "errors": errors,
        "validation_counts": expected_summary,
        "existing_24_unit_curriculum_enforced": not errors,
        "private_or_learner_content_absent": not _safe_scan(artifact),
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else None,
    }


def main() -> int:
    try:
        cp03_artifact = builder._read(builder.CP03_PATH)
        artifact = builder._read(builder.OUTPUT_PATH)
        report = validate_artifact(artifact, cp03_artifact)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["validation_status"] == builder.PASS_STATUS else 1
    except (OSError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
