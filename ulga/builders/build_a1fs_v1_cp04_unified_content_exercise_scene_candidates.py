#!/usr/bin/env python3
"""Build metadata-only content, exercise, and scene candidates for 24 units.

CP04 consumes the CP03 dual-source binding and materializes deterministic
candidate envelopes only. Existing M11B reviewed shared items remain reusable
private exercise candidates. Promoted RAZ materials remain private-source
materialization candidates until their source payload and skill affordances are
resolved. Scene candidates are emitted only from CP02 source-proven
Theme/Situation authority refs. No source text, prompt, answer, transcript,
learner-facing content, new unit, or admission decision is produced here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp03_unified_existing_24_unit_binding as cp03  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Metadata-only candidate envelopes over existing admitted item IDs, promoted "
    "RAZ material IDs, and source-proven Theme/Situation refs; no learner content "
    "or private source payload is produced."
)

TASK_ID = "A1FS-V1-CP04_UnifiedContentExerciseAndSceneCandidateBuild"
PROGRAM_ID = cp03.PROGRAM_ID
SCHEMA_VERSION = "a1fs.v1.cp04.unified_content_exercise_scene_candidates.v1"
PASS_STATUS = "PASS_CP04_UNIFIED_CONTENT_EXERCISE_AND_SCENE_CANDIDATES_BUILT"
NEXT_SHORT_STEP = "A1FS-V1-CP05_PrivateCandidateMaterializationAndAdmission"

CP03_PATH = cp03.OUTPUT_PATH
OUTPUT_PATH = REPO_ROOT / ".local/a1fs_v1/cp04/unified_content_exercise_scene_candidates.safe.json"
REPORT_PATH = REPO_ROOT / ".local/a1fs_v1/cp04/unified_content_exercise_scene_candidates.validation.json"
SKILLS = cp03.SKILLS


class CandidateBuildError(ValueError):
    """Fail-closed CP03 lineage, candidate identity, or safe-output error."""


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_value(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _candidate_id(kind: str, *parts: str) -> str:
    if not kind or not parts or any(not part for part in parts):
        raise CandidateBuildError("candidate_identity_component_missing")
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"A1FS_CP04_{kind}_{digest}"


def _verify_cp03(artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if artifact.get("task_id") != cp03.TASK_ID:
        raise CandidateBuildError("cp03_task_id_mismatch")
    if artifact.get("schema_version") != cp03.SCHEMA_VERSION:
        raise CandidateBuildError("cp03_schema_version_mismatch")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY":
        raise CandidateBuildError("cp03_scope_mismatch")
    if artifact.get("stop_reason") != "NONE":
        raise CandidateBuildError("cp03_not_passed")
    if artifact.get("next_short_step") != TASK_ID:
        raise CandidateBuildError("cp03_next_short_step_mismatch")
    contract = artifact.get("binding_contract", {})
    if (
        contract.get("course_container") != "EXISTING_24_CANONICAL_UNITS_ONLY"
        or contract.get("new_unit_creation_allowed") is not False
        or contract.get("raz_specific_parallel_curriculum_allowed") is not False
        or contract.get("unpromoted_raz_asset_binding_allowed") is not False
    ):
        raise CandidateBuildError("cp03_binding_contract_invalid")
    summary = artifact.get("coverage_summary", {})
    if (
        summary.get("existing_learning_unit_count") != 24
        or summary.get("new_learning_unit_count") != 0
        or summary.get("parallel_curriculum_count") != 0
    ):
        raise CandidateBuildError("cp03_coverage_contract_invalid")
    units = artifact.get("learning_units")
    if not isinstance(units, list) or len(units) != 24:
        raise CandidateBuildError("cp03_learning_unit_count_not_24")
    grammar_ids = [str(unit.get("grammar_unit_id") or "") for unit in units]
    learning_ids = [str(unit.get("learning_unit_id") or "") for unit in units]
    if (
        "" in grammar_ids
        or "" in learning_ids
        or len(grammar_ids) != len(set(grammar_ids))
        or len(learning_ids) != len(set(learning_ids))
        or [unit.get("sequence_index") for unit in units] != list(range(1, 25))
    ):
        raise CandidateBuildError("cp03_learning_unit_identity_invalid")
    return units


def _m11b_candidates(
    unit: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    learning_unit_id = str(unit["learning_unit_id"])
    source = unit.get("m11b_reviewed_content_binding", {})
    by_skill = source.get("admitted_item_ids_by_skill", {})
    if not isinstance(by_skill, Mapping) or set(by_skill) != set(SKILLS):
        raise CandidateBuildError(f"m11b_skill_partition_invalid:{learning_unit_id}")
    content: list[dict[str, Any]] = []
    exercises: list[dict[str, Any]] = []
    seen: set[str] = set()
    for skill in SKILLS:
        item_ids = by_skill.get(skill)
        if not isinstance(item_ids, list) or len(item_ids) != len(set(item_ids)):
            raise CandidateBuildError(f"m11b_item_ids_invalid:{learning_unit_id}:{skill}")
        for item_id_value in item_ids:
            item_id = str(item_id_value or "")
            if not item_id or item_id in seen:
                raise CandidateBuildError(f"m11b_item_identity_invalid:{learning_unit_id}:{skill}")
            seen.add(item_id)
            content_id = _candidate_id("CONTENT_M11B", learning_unit_id, skill, item_id)
            exercise_id = _candidate_id("EXERCISE_M11B", learning_unit_id, skill, item_id)
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
                    "exercise_candidate_id": exercise_id,
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


def _raz_candidates(
    unit: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    learning_unit_id = str(unit["learning_unit_id"])
    grammar_unit_id = str(unit["grammar_unit_id"])
    source = unit.get("raz_admitted_asset_binding", {})
    materials = source.get("materials")
    if not isinstance(materials, list):
        raise CandidateBuildError(f"raz_material_partition_invalid:{learning_unit_id}")
    content: list[dict[str, Any]] = []
    exercises: list[dict[str, Any]] = []
    seen: set[str] = set()
    for material in materials:
        if not isinstance(material, Mapping):
            raise CandidateBuildError(f"raz_material_row_invalid:{learning_unit_id}")
        material_id = str(material.get("material_id") or "")
        scope = str(material.get("candidate_cefr_scope") or "")
        if (
            not material_id.startswith("RAZ_A1A1PLUS_MATERIAL_")
            or material_id in seen
            or material.get("grammar_authority_ref") != grammar_unit_id
            or material.get("registry_status")
            != "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY"
            or scope not in {"A1", "A1_PLUS"}
        ):
            raise CandidateBuildError(f"raz_material_binding_invalid:{learning_unit_id}:{material_id}")
        seen.add(material_id)
        content_id = _candidate_id("CONTENT_RAZ", learning_unit_id, material_id)
        exercise_id = _candidate_id("EXERCISE_RAZ", learning_unit_id, material_id)
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
                "exercise_candidate_id": exercise_id,
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


def _scene_candidates(unit: Mapping[str, Any]) -> list[dict[str, Any]]:
    learning_unit_id = str(unit["learning_unit_id"])
    binding = unit.get("cp02_authority_bindings", {}).get("theme_situation", {})
    refs = binding.get("selected_refs", [])
    status = binding.get("selection_status")
    if not isinstance(refs, list) or len(refs) != len(set(refs)):
        raise CandidateBuildError(f"scene_authority_refs_invalid:{learning_unit_id}")
    if refs and status != "SELECTED_AUTHORITY_BACKED":
        raise CandidateBuildError(f"scene_authority_status_invalid:{learning_unit_id}")
    if not refs and status != "PENDING_SOURCE_EVIDENCE":
        raise CandidateBuildError(f"scene_authority_gap_status_invalid:{learning_unit_id}")
    return [
        {
            "scene_candidate_id": _candidate_id("SCENE", learning_unit_id, str(ref)),
            "theme_situation_ref": str(ref),
            "candidate_state": "AUTHORITY_BACKED_METADATA_READY",
            "source_query_ref": binding.get("source_query_ref"),
            "scene_materialized": False,
        }
        for ref in refs
    ]


def _population_status(content_count: int, exercise_count: int, scene_count: int) -> str:
    if content_count and exercise_count and scene_count:
        return "CONTENT_EXERCISE_AND_SCENE_CANDIDATES_AVAILABLE"
    if content_count and exercise_count:
        return "CONTENT_AND_EXERCISE_CANDIDATES_AVAILABLE_SCENE_PENDING"
    if scene_count:
        return "SCENE_CANDIDATES_AVAILABLE_CONTENT_PENDING"
    return "NO_CANDIDATE_POPULATION"


def build_artifact(cp03_artifact: Mapping[str, Any]) -> dict[str, Any]:
    units = _verify_cp03(cp03_artifact)
    output_units: list[dict[str, Any]] = []
    all_content_ids: set[str] = set()
    all_exercise_ids: set[str] = set()
    all_scene_ids: set[str] = set()
    m11b_source_refs: set[str] = set()
    raz_source_refs: set[str] = set()
    m11b_count = 0
    raz_binding_count = 0
    scene_count = 0
    authority_backed_scene_unit_count = 0
    units_with_content = 0
    candidate_envelope_complete_unit_count = 0

    for unit in units:
        m11b_content, m11b_exercises = _m11b_candidates(unit)
        raz_content, raz_exercises = _raz_candidates(unit)
        scenes = _scene_candidates(unit)
        content = m11b_content + raz_content
        exercises = m11b_exercises + raz_exercises

        content_ids = {row["content_candidate_id"] for row in content}
        exercise_ids = {row["exercise_candidate_id"] for row in exercises}
        scene_ids = {row["scene_candidate_id"] for row in scenes}
        if (
            len(content_ids) != len(content)
            or len(exercise_ids) != len(exercises)
            or len(scene_ids) != len(scenes)
            or all_content_ids & content_ids
            or all_exercise_ids & exercise_ids
            or all_scene_ids & scene_ids
        ):
            raise CandidateBuildError("candidate_id_collision")
        all_content_ids |= content_ids
        all_exercise_ids |= exercise_ids
        all_scene_ids |= scene_ids

        m11b_refs = {row["source_ref"] for row in m11b_content}
        raz_refs = {row["source_ref"] for row in raz_content}
        if m11b_source_refs & m11b_refs:
            raise CandidateBuildError("m11b_source_ref_reused_across_units")
        m11b_source_refs |= m11b_refs
        raz_source_refs |= raz_refs

        m11b_count += len(m11b_content)
        raz_binding_count += len(raz_content)
        scene_count += len(scenes)
        authority_backed_scene_unit_count += bool(scenes)
        units_with_content += bool(content)
        candidate_envelope_complete_unit_count += bool(content and exercises and scenes)

        output_units.append(
            {
                "learning_unit_id": unit["learning_unit_id"],
                "grammar_unit_id": unit["grammar_unit_id"],
                "sequence_index": unit["sequence_index"],
                "internal_stage": unit["internal_stage"],
                "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
                "content_candidates": content,
                "exercise_candidates": exercises,
                "scene_candidates": scenes,
                "candidate_counts": {
                    "m11b_content_candidate_count": len(m11b_content),
                    "raz_content_candidate_count": len(raz_content),
                    "content_candidate_count": len(content),
                    "ready_reuse_exercise_candidate_count": len(m11b_exercises),
                    "pending_raz_exercise_derivation_candidate_count": len(raz_exercises),
                    "exercise_candidate_count": len(exercises),
                    "scene_candidate_count": len(scenes),
                },
                "candidate_population_status": _population_status(
                    len(content), len(exercises), len(scenes)
                ),
            }
        )

    cp03_summary = cp03_artifact["coverage_summary"]
    if m11b_count != cp03_summary.get("m11b_reviewed_content_item_count"):
        raise CandidateBuildError("m11b_candidate_count_not_reconciled")
    if raz_binding_count != cp03_summary.get("raz_material_unit_binding_count"):
        raise CandidateBuildError("raz_candidate_binding_count_not_reconciled")
    if len(raz_source_refs) != cp03_summary.get("raz_distinct_bound_material_count"):
        raise CandidateBuildError("raz_distinct_material_count_not_reconciled")

    summary = {
        "existing_learning_unit_count": 24,
        "new_learning_unit_count": 0,
        "m11b_reviewed_content_candidate_count": m11b_count,
        "raz_material_binding_candidate_count": raz_binding_count,
        "distinct_raz_material_source_count": len(raz_source_refs),
        "distinct_content_source_ref_count": len(m11b_source_refs | raz_source_refs),
        "content_candidate_count": len(all_content_ids),
        "exercise_candidate_count": len(all_exercise_ids),
        "ready_reuse_exercise_candidate_count": m11b_count,
        "pending_raz_exercise_derivation_candidate_count": raz_binding_count,
        "scene_candidate_count": scene_count,
        "authority_backed_scene_unit_count": authority_backed_scene_unit_count,
        "scene_authority_gap_unit_count": 24 - authority_backed_scene_unit_count,
        "units_with_any_content_candidate": units_with_content,
        "candidate_envelope_complete_unit_count": candidate_envelope_complete_unit_count,
    }
    artifact = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "metadata_only_unified_content_exercise_scene_candidate_envelopes",
        "scope": "A1_A1_PLUS_ONLY",
        "candidate_contract": {
            "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
            "source_binding_task_id": cp03.TASK_ID,
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
        },
        "source_identity": {
            "cp03_task_id": cp03_artifact["task_id"],
            "cp03_sha256": _sha256_value(cp03_artifact),
            "cp03_cp01_sha256": cp03_artifact["source_identity"]["cp01_sha256"],
            "cp03_cp02_sha256": cp03_artifact["source_identity"]["cp02_sha256"],
            "cp03_raz_registry_package_sha256": cp03_artifact["source_identity"][
                "raz_registry_package_sha256"
            ],
        },
        "coverage_summary": summary,
        "learning_units": output_units,
        "capability_delta": {
            "unified_content_candidate_envelopes_created": True,
            "exercise_candidate_envelopes_created": True,
            "authority_backed_scene_candidate_envelopes_created": True,
            "existing_24_unit_curriculum_preserved": True,
        },
        "claim_boundaries": {
            "canonical_unit_identity_changed": False,
            "canonical_egp_mapping_changed": False,
            "admission_decision_changed": False,
            "private_source_content_read": False,
            "learner_facing_content_created": False,
            "new_exercise_content_authored": False,
            "scene_content_authored": False,
            "runtime_publication_claimed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    _safe_scan(artifact)
    return artifact


def _safe_scan(value: Any) -> None:
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

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden:
                    raise CandidateBuildError(f"private_or_learner_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cp03", type=Path, default=CP03_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    try:
        cp03_artifact = _read(args.cp03)
        artifact = build_artifact(cp03_artifact)
        from ulga.validators.validate_a1fs_v1_cp04_unified_content_exercise_scene_candidates import validate_artifact

        report = validate_artifact(artifact, cp03_artifact)
        write_json(args.output, artifact)
        write_json(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (OSError, KeyError, TypeError, ValueError, CandidateBuildError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
