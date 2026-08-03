#!/usr/bin/env python3
"""Runtime-aware U01QB09 allocation repair for U01QB14R1.

Given a validated U01QB14R1 31-scene rotation and an active U01QB12 474-item
runtime, choose each scene's task angles only from the ordinary U01QB09 support
profile candidates that are executable against the real catalog under U01QB13's
lexical/context binding rules. This preserves 12 forms / 48 scene exposures /
240 activities and the no-repeat task-angle rule without creating another
planner or QuestionBank.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u01qb13
from ulga.builders import build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as u01qb14r1
from ulga.validators import validate_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Deterministic task-angle selection over an existing validated 474-item Unit01 runtime; no learner content, QuestionBank, scoring, scene, planner, or learner-state authority is created."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB14R1_RuntimeTaskAwareSceneAllocationRepair"
PASS_STATUS = "PASS_A1FS_V1_U01QB14R1_RUNTIME_TASK_AWARE_SCENE_ALLOCATION_REPAIR"


class RuntimeTaskAwareAllocationError(ValueError):
    pass


def _catalog(database: Path) -> dict[str, list[dict[str, Any]]]:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "u01qb02_item_catalog" not in tables:
            raise RuntimeTaskAwareAllocationError("U01QB02_ITEM_CATALOG_MISSING")
        rows = [
            dict(row)
            for row in connection.execute(
                "SELECT item_id,skill,pattern_family_id,private_item_json FROM u01qb02_item_catalog ORDER BY item_id"
            )
        ]
    by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_skill[str(row["skill"])].append(row)
    return dict(by_skill)


def _families(skill: str, angle: str) -> tuple[str, ...]:
    if skill == "SPEAKING":
        return tuple(u01qb13.SPEAKING_LEXICAL_FAMILIES)
    return tuple(u01qb13.EXACT_SCORED_BINDINGS.get((skill, angle), ()))


def _runtime_angle_bindable(
    *,
    skill: str,
    angle: str,
    anchors: set[str],
    situation_family: str,
    catalog: Mapping[str, list[dict[str, Any]]],
) -> bool:
    families = set(_families(skill, angle))
    if not families:
        return False
    for row in catalog.get(skill, []):
        if str(row["pattern_family_id"]) not in families:
            continue
        item = json.loads(str(row["private_item_json"]))
        noun = str((item.get("lexical_slots") or {}).get("noun") or "").casefold()
        if noun not in anchors:
            continue
        if skill != "SPEAKING" and not u01qb13._context_matches(item, situation_family):
            continue
        return True
    return False


def _choose_runtime_angles(
    *,
    support: str,
    skill: str,
    previous: set[str],
    count: int,
    anchors: set[str],
    situation_family: str,
    catalog: Mapping[str, list[dict[str, Any]]],
    scene_ref_id: str,
) -> list[str]:
    profile_candidates = list(u01qb09.SUPPORT_PROFILES[support]["candidates"][skill])
    compatible = [
        angle
        for angle in profile_candidates
        if angle not in previous
        and _runtime_angle_bindable(
            skill=skill,
            angle=angle,
            anchors=anchors,
            situation_family=situation_family,
            catalog=catalog,
        )
    ]
    if len(compatible) < count:
        all_compatible = [
            angle
            for angle in profile_candidates
            if _runtime_angle_bindable(
                skill=skill,
                angle=angle,
                anchors=anchors,
                situation_family=situation_family,
                catalog=catalog,
            )
        ]
        raise RuntimeTaskAwareAllocationError(
            "SCENE_RUNTIME_TASK_ANGLE_CAPACITY_INSUFFICIENT:"
            f"{scene_ref_id}:{support}:{skill}:"
            f"need={count}:available_unrepeated={','.join(compatible)}:"
            f"available_total={','.join(all_compatible)}"
        )
    return compatible[:count]


def build_runtime_aware_allocation(
    rotation: Mapping[str, Any],
    database: Path,
) -> dict[str, Any]:
    u01qb14r1.validate_rotation_runtime_bindability(rotation)
    catalog = _catalog(Path(database))
    semantics = u01qb14r1.tolerant_scene_semantic_index()

    prior_angles: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    prior_package: dict[str, dict[str, Any]] = {}
    output_forms: list[dict[str, Any]] = []
    coverage_counts: Counter[str] = Counter()
    coverage_by_skill: dict[str, Counter[str]] = defaultdict(Counter)
    angle_counts: Counter[str] = Counter()
    support_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    gap_angles: Counter[str] = Counter()
    runtime_compatibility_counts: Counter[str] = Counter()

    for form in rotation["forms"]:
        form_ordinal = int(form["form_ordinal"])
        support = u01qb09.support_for_form(form_ordinal)
        profile = u01qb09.SUPPORT_PROFILES[support]
        scene_packages: list[dict[str, Any]] = []

        for scene_slot in form["scene_slots"]:
            ref = str(scene_slot["scene_ref_id"])
            semantic = semantics.get(ref)
            if semantic is None:
                raise RuntimeTaskAwareAllocationError(f"SCENE_SEMANTICS_MISSING:{ref}")
            anchors = {str(row).casefold() for row in semantic.get("anchors") or []}
            if not anchors:
                raise RuntimeTaskAwareAllocationError(f"ROTATION_SCENE_ANCHORS_MISSING:{ref}")
            family = str(scene_slot["situation_family"])
            previous_by_skill = prior_angles[ref]

            reading = _choose_runtime_angles(
                support=support, skill="READING", previous=previous_by_skill["READING"], count=2,
                anchors=anchors, situation_family=family, catalog=catalog, scene_ref_id=ref,
            )
            writing = _choose_runtime_angles(
                support=support, skill="WRITING", previous=previous_by_skill["WRITING"], count=2,
                anchors=anchors, situation_family=family, catalog=catalog, scene_ref_id=ref,
            )
            speaking = _choose_runtime_angles(
                support=support, skill="SPEAKING", previous=previous_by_skill["SPEAKING"], count=1,
                anchors=anchors, situation_family=family, catalog=catalog, scene_ref_id=ref,
            )

            assignments = (
                [("READING", angle) for angle in reading]
                + [("WRITING", angle) for angle in writing]
                + [("SPEAKING", angle) for angle in speaking]
            )
            activities: list[dict[str, Any]] = []
            for activity_index, (skill, angle) in enumerate(assignments, start=1):
                binding = u01qb09.bank_binding(skill, angle)
                scored = skill != "SPEAKING"
                coverage = str(binding["status"])
                coverage_counts[coverage] += 1
                coverage_by_skill[skill][coverage] += 1
                angle_counts[angle] += 1
                skill_counts[skill] += 1
                runtime_compatibility_counts[f"{skill}:{angle}"] += 1
                if coverage == "GAP":
                    gap_angles[angle] += 1
                activities.append(
                    {
                        "activity_id": f"{form['form_id']}-S{scene_slot['slot']:02d}-A{activity_index:02d}",
                        "activity_ordinal": activity_index,
                        "skill": skill,
                        "task_angle": angle,
                        "support_level": support,
                        "purpose": profile["purpose"],
                        "prompt_perspective": profile["prompt_perspective"],
                        "evidence_class": profile["evidence_class"],
                        "scored": scored,
                        "practice_only": skill == "SPEAKING",
                        "assessment_candidate": support == "TRANSFER" and scored,
                        "current_bank_support": coverage,
                        "pattern_family_ids": binding["pattern_family_ids"],
                    }
                )

            for skill, angles in (("READING", reading), ("WRITING", writing), ("SPEAKING", speaking)):
                previous_by_skill[skill].update(angles)

            previous = prior_package.get(ref)
            change_dimensions: list[str] = []
            if previous is not None:
                if previous["support_level"] != support:
                    change_dimensions.append("SUPPORT_LEVEL")
                if previous["prompt_perspective"] != profile["prompt_perspective"]:
                    change_dimensions.append("PROMPT_PERSPECTIVE")
                previous_pairs = {(row["skill"], row["task_angle"]) for row in previous["activities"]}
                current_pairs = {(row["skill"], row["task_angle"]) for row in activities}
                if previous_pairs != current_pairs:
                    change_dimensions.append("TASK_ANGLE")
                if previous_pairs & current_pairs:
                    raise RuntimeTaskAwareAllocationError(f"SAME_SCENE_SKILL_TASK_ANGLE_REPLAY:{ref}")
                if len(change_dimensions) < u01qb08.REUSED_SCENE_CHANGED_DIMENSIONS_MIN:
                    raise RuntimeTaskAwareAllocationError(f"REUSED_SCENE_CHANGE_DIMENSIONS_BELOW_MIN:{ref}")

            package = {
                "scene_slot": int(scene_slot["slot"]),
                "scene_ref_id": ref,
                "semantic_scene_signature_v2": str(scene_slot["semantic_scene_signature_v2"]),
                "situation_family": family,
                "setting": str(scene_slot["setting"]),
                "exposure_ordinal": int(scene_slot["exposure_ordinal"]),
                "support_level": support,
                "purpose": profile["purpose"],
                "prompt_perspective": profile["prompt_perspective"],
                "evidence_class": profile["evidence_class"],
                "reuse_change_dimensions": change_dimensions,
                "activity_count": len(activities),
                "scored_activity_count": sum(bool(row["scored"]) for row in activities),
                "speaking_practice_count": sum(row["skill"] == "SPEAKING" for row in activities),
                "runtime_scene_anchors": sorted(anchors),
                "runtime_task_bindability_verified": True,
                "activities": activities,
            }
            prior_package[ref] = deepcopy(package)
            scene_packages.append(package)
            support_counts[support] += 1

        output_forms.append(
            {
                "form_id": form["form_id"],
                "form_ordinal": form_ordinal,
                "week": form["week"],
                "day_in_week": form["day_in_week"],
                "support_level": support,
                "purpose": profile["purpose"],
                "scene_count": len(scene_packages),
                "activity_count": sum(row["activity_count"] for row in scene_packages),
                "scored_activity_count": sum(row["scored_activity_count"] for row in scene_packages),
                "speaking_practice_count": sum(row["speaking_practice_count"] for row in scene_packages),
                "scene_packages": scene_packages,
            }
        )

    scored_gap_count = sum(
        row["current_bank_support"] == "GAP" and row["scored"]
        for form in output_forms for scene in form["scene_packages"] for row in scene["activities"]
    )
    scored_partial_count = sum(
        row["current_bank_support"] == "PARTIAL" and row["scored"]
        for form in output_forms for scene in form["scene_packages"] for row in scene["activities"]
    )
    artifact: dict[str, Any] = {
        "schema_version": u01qb09.SCHEMA_VERSION,
        "program_id": u01qb09.PROGRAM_ID,
        "task_id": u01qb09.TASK_ID,
        "status": u01qb09.PASS_STATUS,
        "unit_id": u01qb09.UNIT_ID,
        "source_identity": {
            "rotation_task_id": rotation["task_id"],
            "rotation_sha256": rotation["rotation_sha256"],
            "approved_scene_artifact_sha256": rotation["source_identity"]["approved_scene_artifact_sha256"],
        },
        "allocation_policy": {
            "scene_exposure_count": u01qb09.EXPECTED_SCENE_EXPOSURES,
            "activities_per_scene": u01qb09.ACTIVITIES_PER_SCENE,
            "reading_per_scene": 2,
            "writing_per_scene": 2,
            "speaking_practice_per_scene": 1,
            "scored_activities_per_form": 16,
            "speaking_practice_per_form": 4,
            "speaking_assessment_eligible": False,
            "same_scene_same_skill_same_task_angle_repeat_allowed": False,
            "reused_scene_min_changed_dimensions": u01qb09.rotation_builder.REUSED_SCENE_CHANGED_DIMENSIONS_MIN,
            "support_progression": {support: profile["form_ordinals"] for support, profile in u01qb09.SUPPORT_PROFILES.items()},
            "task_angle_ids": list(u01qb09.TASK_ANGLES),
        },
        "task_angle_bank_bindings": [
            {"skill": skill, "task_angle": angle, **deepcopy(binding)}
            for (skill, angle), binding in sorted(u01qb09.BANK_BINDINGS.items())
        ],
        "forms": output_forms,
        "allocation_metrics": {
            "form_count": len(output_forms),
            "scene_exposure_count": sum(form["scene_count"] for form in output_forms),
            "activity_slot_count": sum(form["activity_count"] for form in output_forms),
            "scored_activity_slot_count": sum(form["scored_activity_count"] for form in output_forms),
            "speaking_practice_slot_count": sum(form["speaking_practice_count"] for form in output_forms),
            "skill_slot_counts": dict(sorted(skill_counts.items())),
            "support_scene_counts": dict(sorted(support_counts.items())),
            "task_angle_slot_counts": dict(sorted(angle_counts.items())),
            "current_bank_support_counts": dict(sorted(coverage_counts.items())),
            "current_bank_support_by_skill": {skill: dict(sorted(counts.items())) for skill, counts in sorted(coverage_by_skill.items())},
            "scored_partial_support_count": scored_partial_count,
            "scored_gap_count": scored_gap_count,
            "gap_task_angle_counts": dict(sorted(gap_angles.items())),
            "question_bank_full_alignment_ready": scored_gap_count == 0 and scored_partial_count == 0,
            "question_bank_reconciliation_required": scored_gap_count > 0 or scored_partial_count > 0,
        },
        "runtime_task_bindability": {
            "status": PASS_STATUS,
            "source_runtime_item_count": sum(len(rows) for rows in catalog.values()),
            "all_240_activities_runtime_compatible": True,
            "verified_activity_count": sum(runtime_compatibility_counts.values()),
            "verified_task_angle_counts": dict(sorted(runtime_compatibility_counts.items())),
        },
        "boundaries": {
            "scene_authority_modified": False,
            "new_scene_authored": False,
            "question_bank_modified": False,
            "question_items_materialized": False,
            "scoring_modified": False,
            "learner_state_modified": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": u01qb09.NEXT_SHORT_STEP,
    }
    artifact["allocation_sha256"] = u01qb09.scene_policy.digest(artifact)
    u01qb09_validator.validate(artifact)
    return artifact
