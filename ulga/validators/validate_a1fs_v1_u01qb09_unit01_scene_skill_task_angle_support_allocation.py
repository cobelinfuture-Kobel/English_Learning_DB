#!/usr/bin/env python3
"""Independently validate U01QB09 scene/skill/task/support allocation."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as scene_policy
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as builder

PASS_STATUS = "PASS_A1FS_V1_U01QB09_UNIT01_SCENE_SKILL_TASK_ANGLE_SUPPORT_ALLOCATION_VALIDATION"


class AllocationValidationError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AllocationValidationError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise AllocationValidationError("ALLOCATION_OBJECT_REQUIRED")
    return value


def validate(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if value.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if value.get("task_id") != builder.TASK_ID or value.get("status") != builder.PASS_STATUS or value.get("unit_id") != builder.UNIT_ID:
        errors.append("identity_invalid")

    source = value.get("source_identity") or {}
    if source.get("rotation_task_id") != "A1FS-V1-U01QB08_Unit01TwelveFormSceneRotationMaterialization":
        errors.append("rotation_source_task_invalid")
    for key in ("rotation_sha256", "approved_scene_artifact_sha256"):
        if not isinstance(source.get(key), str) or len(source.get(key)) != 64:
            errors.append(f"source_sha_invalid:{key}")

    expected_policy = {
        "scene_exposure_count": builder.EXPECTED_SCENE_EXPOSURES,
        "activities_per_scene": builder.ACTIVITIES_PER_SCENE,
        "reading_per_scene": 2,
        "writing_per_scene": 2,
        "speaking_practice_per_scene": 1,
        "scored_activities_per_form": 16,
        "speaking_practice_per_form": 4,
        "speaking_assessment_eligible": False,
        "same_scene_same_skill_same_task_angle_repeat_allowed": False,
        "reused_scene_min_changed_dimensions": 2,
        "support_progression": {support: profile["form_ordinals"] for support, profile in builder.SUPPORT_PROFILES.items()},
        "task_angle_ids": list(builder.TASK_ANGLES),
    }
    if value.get("allocation_policy") != expected_policy:
        errors.append("allocation_policy_invalid")

    expected_bindings = [
        {"skill": skill, "task_angle": angle, **deepcopy(binding)}
        for (skill, angle), binding in sorted(builder.BANK_BINDINGS.items())
    ]
    if value.get("task_angle_bank_bindings") != expected_bindings:
        errors.append("task_angle_bank_bindings_invalid")

    forms = value.get("forms") if isinstance(value.get("forms"), list) else []
    if len(forms) != 12:
        errors.append("form_count_invalid")

    seen_scene_packages: dict[str, dict[str, Any]] = {}
    seen_scene_count: Counter[str] = Counter()
    coverage_counts: Counter[str] = Counter()
    coverage_by_skill: dict[str, Counter[str]] = defaultdict(Counter)
    gap_angles: Counter[str] = Counter()
    angle_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    support_scene_counts: Counter[str] = Counter()
    total_scene_exposures = 0
    total_activities = 0
    total_scored = 0
    total_speaking = 0
    scored_partial = 0
    scored_gap = 0

    for expected_ordinal, form in enumerate(forms, start=1):
        if not isinstance(form, Mapping):
            errors.append("form_not_object")
            continue
        support = builder.support_for_form(expected_ordinal)
        profile = builder.SUPPORT_PROFILES[support]
        if form.get("form_id") != f"U01-FORM-{expected_ordinal:02d}" or form.get("form_ordinal") != expected_ordinal:
            errors.append("form_identity_invalid")
        if form.get("support_level") != support or form.get("purpose") != profile["purpose"]:
            errors.append("form_support_or_purpose_invalid")
        scenes = form.get("scene_packages") if isinstance(form.get("scene_packages"), list) else []
        if len(scenes) != 4 or form.get("scene_count") != 4:
            errors.append("scene_package_count_invalid")
        if form.get("activity_count") != 20 or form.get("scored_activity_count") != 16 or form.get("speaking_practice_count") != 4:
            errors.append("form_activity_counts_invalid")

        for scene in scenes:
            if not isinstance(scene, Mapping):
                errors.append("scene_package_not_object")
                continue
            total_scene_exposures += 1
            ref = str(scene.get("scene_ref_id") or "")
            if not ref:
                errors.append("scene_ref_missing")
                continue
            seen_scene_count[ref] += 1
            if scene.get("exposure_ordinal") != seen_scene_count[ref]:
                errors.append("scene_exposure_ordinal_invalid")
            if scene.get("support_level") != support or scene.get("purpose") != profile["purpose"] or scene.get("prompt_perspective") != profile["prompt_perspective"] or scene.get("evidence_class") != profile["evidence_class"]:
                errors.append("scene_profile_invalid")
            support_scene_counts[support] += 1

            activities = scene.get("activities") if isinstance(scene.get("activities"), list) else []
            if len(activities) != 5 or scene.get("activity_count") != 5:
                errors.append("scene_activity_count_invalid")
                continue
            skill_counter = Counter(str(row.get("skill")) for row in activities if isinstance(row, Mapping))
            if skill_counter != Counter({"READING": 2, "WRITING": 2, "SPEAKING": 1}):
                errors.append("scene_skill_distribution_invalid")

            pairs: set[tuple[str, str]] = set()
            for expected_activity, activity in enumerate(activities, start=1):
                total_activities += 1
                if not isinstance(activity, Mapping):
                    errors.append("activity_not_object")
                    continue
                skill = str(activity.get("skill") or "")
                angle = str(activity.get("task_angle") or "")
                if activity.get("activity_ordinal") != expected_activity:
                    errors.append("activity_ordinal_invalid")
                if angle not in builder.TASK_ANGLES:
                    errors.append("task_angle_invalid")
                if activity.get("support_level") != support or activity.get("purpose") != profile["purpose"] or activity.get("prompt_perspective") != profile["prompt_perspective"] or activity.get("evidence_class") != profile["evidence_class"]:
                    errors.append("activity_profile_invalid")
                expected_binding = builder.bank_binding(skill, angle)
                if activity.get("current_bank_support") != expected_binding["status"] or activity.get("pattern_family_ids") != expected_binding["pattern_family_ids"]:
                    errors.append("activity_bank_binding_invalid")
                if skill == "SPEAKING":
                    total_speaking += 1
                    if activity.get("scored") is not False or activity.get("practice_only") is not True or activity.get("assessment_candidate") is not False:
                        errors.append("speaking_boundary_invalid")
                else:
                    total_scored += 1
                    if activity.get("scored") is not True or activity.get("practice_only") is not False:
                        errors.append("scored_activity_boundary_invalid")
                    if activity.get("assessment_candidate") is not (support == "TRANSFER"):
                        errors.append("assessment_candidate_invalid")
                coverage = str(activity.get("current_bank_support") or "")
                coverage_counts[coverage] += 1
                coverage_by_skill[skill][coverage] += 1
                angle_counts[angle] += 1
                skill_counts[skill] += 1
                if coverage == "GAP":
                    gap_angles[angle] += 1
                    if skill != "SPEAKING":
                        scored_gap += 1
                elif coverage == "PARTIAL" and skill != "SPEAKING":
                    scored_partial += 1
                pairs.add((skill, angle))

            previous = seen_scene_packages.get(ref)
            changes = list(scene.get("reuse_change_dimensions") or [])
            if previous is None:
                if changes:
                    errors.append("first_exposure_change_dimensions_present")
            else:
                previous_pairs = {(str(row["skill"]), str(row["task_angle"])) for row in previous["activities"]}
                if previous_pairs & pairs:
                    errors.append("same_scene_same_skill_task_angle_repeated")
                recomputed_changes: list[str] = []
                if previous["support_level"] != scene["support_level"]:
                    recomputed_changes.append("SUPPORT_LEVEL")
                if previous["prompt_perspective"] != scene["prompt_perspective"]:
                    recomputed_changes.append("PROMPT_PERSPECTIVE")
                if previous_pairs != pairs:
                    recomputed_changes.append("TASK_ANGLE")
                if changes != recomputed_changes:
                    errors.append("reuse_change_dimensions_mismatch")
                if len(changes) < 2:
                    errors.append("reuse_change_dimensions_below_min")
            seen_scene_packages[ref] = deepcopy(dict(scene))

    expected_metrics = {
        "form_count": len(forms),
        "scene_exposure_count": total_scene_exposures,
        "activity_slot_count": total_activities,
        "scored_activity_slot_count": total_scored,
        "speaking_practice_slot_count": total_speaking,
        "skill_slot_counts": dict(sorted(skill_counts.items())),
        "support_scene_counts": dict(sorted(support_scene_counts.items())),
        "task_angle_slot_counts": dict(sorted(angle_counts.items())),
        "current_bank_support_counts": dict(sorted(coverage_counts.items())),
        "current_bank_support_by_skill": {skill: dict(sorted(counts.items())) for skill, counts in sorted(coverage_by_skill.items())},
        "scored_partial_support_count": scored_partial,
        "scored_gap_count": scored_gap,
        "gap_task_angle_counts": dict(sorted(gap_angles.items())),
        "question_bank_full_alignment_ready": scored_gap == 0 and scored_partial == 0,
        "question_bank_reconciliation_required": scored_gap > 0 or scored_partial > 0,
    }
    if value.get("allocation_metrics") != expected_metrics:
        errors.append("allocation_metrics_mismatch")
    if total_scene_exposures != builder.EXPECTED_SCENE_EXPOSURES:
        errors.append("scene_exposure_total_invalid")
    if total_activities != builder.EXPECTED_ACTIVITY_SLOTS:
        errors.append("activity_slot_total_invalid")
    if total_scored != builder.EXPECTED_SCORED_SLOTS:
        errors.append("scored_slot_total_invalid")
    if total_speaking != builder.EXPECTED_SPEAKING_SLOTS:
        errors.append("speaking_slot_total_invalid")

    expected_boundaries = {
        "scene_authority_modified": False,
        "new_scene_authored": False,
        "question_bank_modified": False,
        "question_items_materialized": False,
        "scoring_modified": False,
        "learner_state_modified": False,
        "speaking_scoring_enabled": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }
    if value.get("boundaries") != expected_boundaries:
        errors.append("boundary_invalid")

    unsigned = deepcopy(dict(value))
    declared = unsigned.pop("allocation_sha256", None)
    if declared != scene_policy.digest(unsigned):
        errors.append("allocation_sha256_invalid")

    report = {
        "status": PASS_STATUS if not errors else "FAIL_A1FS_V1_U01QB09_UNIT01_SCENE_SKILL_TASK_ANGLE_SUPPORT_ALLOCATION_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "form_count": len(forms),
        "scene_exposure_count": total_scene_exposures,
        "activity_slot_count": total_activities,
        "scored_activity_slot_count": total_scored,
        "speaking_practice_slot_count": total_speaking,
        "scored_partial_support_count": scored_partial,
        "scored_gap_count": scored_gap,
        "question_bank_full_alignment_ready": scored_gap == 0 and scored_partial == 0,
    }
    if errors:
        raise AllocationValidationError("|".join(errors))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allocation", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = validate(read_json(args.allocation))
    except (AllocationValidationError, KeyError, TypeError, ValueError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB09_UNIT01_SCENE_SKILL_TASK_ANGLE_SUPPORT_ALLOCATION_VALIDATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    print(f"FORMS={report['form_count']}")
    print(f"SCENE_EXPOSURES={report['scene_exposure_count']}")
    print(f"ACTIVITY_SLOTS={report['activity_slot_count']}")
    print(f"SCORED_SLOTS={report['scored_activity_slot_count']}")
    print(f"SPEAKING_PRACTICE_SLOTS={report['speaking_practice_slot_count']}")
    print(f"SCORED_PARTIAL_SUPPORT={report['scored_partial_support_count']}")
    print(f"SCORED_GAPS={report['scored_gap_count']}")
    print(f"QUESTION_BANK_FULL_ALIGNMENT_READY={report['question_bank_full_alignment_ready']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
