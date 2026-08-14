#!/usr/bin/env python3
"""Runtime- and session-capacity-aware U01QB09 allocation repair for U01QB14R1.

Given a validated U01QB14R1 31-scene rotation and an active U01QB12 474-item
runtime, choose each scene's task angles only from the ordinary U01QB09 support
profile candidates that are executable against the real catalog under U01QB13's
lexical/context binding rules. Selection is solved per form/skill with a
bipartite item-capacity check, so eight Reading/Writing activities (or four
Speaking activities) always have distinct runtime items available inside the
existing ten-item U01QB02 session container.

This is allocation repair, not a second planner: it preserves the validated
U01QB08 rotation, the U01QB09 schema and support progression, 12 forms / 48 scene
exposures / 240 activities, and the same U01QB13/U01QB02/M3/M6 execution path.
"""
from __future__ import annotations

import itertools
import json
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u01qb13
from ulga.builders import build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as u01qb14r1
from ulga.validators import validate_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Deterministic task-angle selection and distinct-item capacity proof over an existing validated 474-item Unit01 runtime; no learner content, QuestionBank, scoring, scene, planner, or learner-state authority is created."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB14R1_RuntimeTaskAwareSceneAllocationRepair"
PASS_STATUS = "PASS_A1FS_V1_U01QB14R1_RUNTIME_TASK_AWARE_SCENE_ALLOCATION_REPAIR"
EXPECTED_RUNTIME_ITEMS = 474


class RuntimeTaskAwareAllocationError(ValueError):
    pass


def _catalog(database: Path) -> dict[str, list[dict[str, Any]]]:
    # sqlite3.Connection.__exit__ commits/rolls back but does not close. This
    # helper is called from the U16C product migration during disposable Form01
    # materialization, so explicitly close the read connection for Windows.
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        required = {"u01qb02_item_catalog", "u01qb12_metadata"}
        missing = sorted(required - tables)
        if missing:
            raise RuntimeTaskAwareAllocationError("RUNTIME_TABLES_MISSING:" + ",".join(missing))
        count = int(connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0])
        if count != EXPECTED_RUNTIME_ITEMS:
            raise RuntimeTaskAwareAllocationError(f"RUNTIME_ITEM_COUNT_INVALID:{count}")
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


def _candidate_item_ids(
    *,
    skill: str,
    angle: str,
    anchors: set[str],
    situation_family: str,
    catalog: Mapping[str, list[dict[str, Any]]],
    scene_ref_id: str | None = None,
) -> tuple[str, ...]:
    families = set(_families(skill, angle))
    if not families:
        return ()
    result: list[str] = []
    for row in catalog.get(skill, []):
        if str(row["pattern_family_id"]) not in families:
            continue
        item = json.loads(str(row["private_item_json"]))
        noun = str((item.get("lexical_slots") or {}).get("noun") or "").casefold()
        if noun not in anchors:
            continue
        if skill != "SPEAKING" and not u01qb13._context_matches(
            item,
            situation_family,
            scene_ref_id=scene_ref_id,
        ):
            continue
        result.append(str(row["item_id"]))
    return tuple(sorted(set(result)))


def _perfect_matching_exists(candidate_sets: Sequence[Sequence[str]]) -> bool:
    """Return whether every activity can receive a distinct runtime item."""
    ordered = sorted(
        [tuple(dict.fromkeys(row)) for row in candidate_sets],
        key=lambda row: (len(row), row),
    )
    if any(not row for row in ordered):
        return False
    owner_by_item: dict[str, int] = {}

    def augment(activity_index: int, seen: set[str]) -> bool:
        for item_id in ordered[activity_index]:
            if item_id in seen:
                continue
            seen.add(item_id)
            previous = owner_by_item.get(item_id)
            if previous is None or augment(previous, seen):
                owner_by_item[item_id] = activity_index
                return True
        return False

    return all(augment(index, set()) for index in range(len(ordered)))


def _scene_options(
    *,
    support: str,
    skill: str,
    previous: set[str],
    count: int,
    anchors: set[str],
    situation_family: str,
    catalog: Mapping[str, list[dict[str, Any]]],
    scene_ref_id: str,
) -> list[tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]]:
    profile = list(u01qb09.SUPPORT_PROFILES[support]["candidates"][skill])
    compatible: list[tuple[str, tuple[str, ...]]] = []
    for angle in profile:
        if angle in previous:
            continue
        item_ids = _candidate_item_ids(
            skill=skill,
            angle=angle,
            anchors=anchors,
            situation_family=situation_family,
            catalog=catalog,
            scene_ref_id=scene_ref_id,
        )
        if item_ids:
            compatible.append((angle, item_ids))

    options: list[tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]] = []
    for indexes in itertools.combinations(range(len(compatible)), count):
        angles = tuple(compatible[index][0] for index in indexes)
        candidate_sets = tuple(compatible[index][1] for index in indexes)
        if _perfect_matching_exists(candidate_sets):
            options.append((angles, candidate_sets))
    if not options:
        available = [angle for angle, _items in compatible]
        raise RuntimeTaskAwareAllocationError(
            "SCENE_RUNTIME_TASK_ANGLE_CAPACITY_INSUFFICIENT:"
            f"{scene_ref_id}:{support}:{skill}:need={count}:"
            f"available_unrepeated={','.join(available)}"
        )
    return options


def _solve_form_skill(
    *,
    support: str,
    skill: str,
    scene_infos: Sequence[Mapping[str, Any]],
    prior_angles: Mapping[str, Mapping[str, set[str]]],
    catalog: Mapping[str, list[dict[str, Any]]],
) -> dict[str, tuple[str, ...]]:
    count = 1 if skill == "SPEAKING" else 2
    options_by_ref: dict[str, list[tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]]] = {}
    for scene in scene_infos:
        ref = str(scene["scene_ref_id"])
        options_by_ref[ref] = _scene_options(
            support=support,
            skill=skill,
            previous=set(prior_angles.get(ref, {}).get(skill, set())),
            count=count,
            anchors=set(scene["anchors"]),
            situation_family=str(scene["situation_family"]),
            catalog=catalog,
            scene_ref_id=ref,
        )

    chosen: dict[str, tuple[str, ...]] = {}
    accumulated_candidate_sets: list[tuple[str, ...]] = []

    def solve(scene_index: int) -> bool:
        if scene_index == len(scene_infos):
            return _perfect_matching_exists(accumulated_candidate_sets)
        ref = str(scene_infos[scene_index]["scene_ref_id"])
        for angles, candidate_sets in options_by_ref[ref]:
            start = len(accumulated_candidate_sets)
            accumulated_candidate_sets.extend(candidate_sets)
            if _perfect_matching_exists(accumulated_candidate_sets):
                chosen[ref] = angles
                if solve(scene_index + 1):
                    return True
                chosen.pop(ref, None)
            del accumulated_candidate_sets[start:]
        return False

    if not solve(0):
        detail = ";".join(
            f"{ref}=" + "/".join("+".join(option[0]) for option in options)
            for ref, options in options_by_ref.items()
        )
        raise RuntimeTaskAwareAllocationError(
            f"FORM_SESSION_DISTINCT_ITEM_CAPACITY_UNSAT:{support}:{skill}:{detail}"
        )
    return chosen


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
        scene_infos: list[dict[str, Any]] = []
        for scene_slot in form["scene_slots"]:
            ref = str(scene_slot["scene_ref_id"])
            semantic = semantics.get(ref)
            if semantic is None:
                raise RuntimeTaskAwareAllocationError(f"SCENE_SEMANTICS_MISSING:{ref}")
            anchors = {str(row).casefold() for row in semantic.get("anchors") or []}
            if not anchors:
                raise RuntimeTaskAwareAllocationError(f"ROTATION_SCENE_ANCHORS_MISSING:{ref}")
            scene_infos.append(
                {
                    "scene_ref_id": ref,
                    "scene_slot": scene_slot,
                    "anchors": anchors,
                    "situation_family": str(scene_slot["situation_family"]),
                }
            )

        choices = {
            skill: _solve_form_skill(
                support=support,
                skill=skill,
                scene_infos=scene_infos,
                prior_angles=prior_angles,
                catalog=catalog,
            )
            for skill in ("READING", "WRITING", "SPEAKING")
        }

        scene_packages: list[dict[str, Any]] = []
        for scene_info in scene_infos:
            scene_slot = scene_info["scene_slot"]
            ref = str(scene_info["scene_ref_id"])
            anchors = set(scene_info["anchors"])
            family = str(scene_info["situation_family"])
            reading = list(choices["READING"][ref])
            writing = list(choices["WRITING"][ref])
            speaking = list(choices["SPEAKING"][ref])
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
                candidate_item_ids = _candidate_item_ids(
                    skill=skill,
                    angle=angle,
                    anchors=anchors,
                    situation_family=family,
                    catalog=catalog,
                    scene_ref_id=ref,
                )
                if not candidate_item_ids:
                    raise RuntimeTaskAwareAllocationError(
                        f"RUNTIME_COMPATIBILITY_DRIFT:{ref}:{skill}:{angle}"
                    )
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
                        "runtime_compatible_item_count": len(candidate_item_ids),
                    }
                )

            for skill, angles in (("READING", reading), ("WRITING", writing), ("SPEAKING", speaking)):
                prior_angles[ref][skill].update(angles)

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
                if len(change_dimensions) < u01qb09.rotation_builder.REUSED_SCENE_CHANGED_DIMENSIONS_MIN:
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
            "all_36_skill_sessions_distinct_item_capacity_proven": True,
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
