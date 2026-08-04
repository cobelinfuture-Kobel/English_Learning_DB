"""Runtime-capacity-aware spiral reuse selector for Unit01 U01QB14R1 rotations.

This module does not create a second rotation planner.  It delegates the actual
12-form scheduling to U01QB08 and the Unit01 bindability projection to U01QB14R1,
while allowing exact scenes that fail downstream task-angle/distinct-item
capacity to remain single-exposure rather than being selected for spiral reuse.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08
from ulga.builders import (
    build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix
    as u01qb14r1,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Selection adapter over the existing U01QB08/U01QB14R1 rotation authority; "
    "it changes only spiral-reuse eligibility and creates no scene, planner, "
    "QuestionBank, runtime, scoring, or learner-state authority."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U01QB14R2_"
    "Unit01RuntimeCapacityAwareSpiralReuseSelectionAndU01QB15FinalAcceptanceFullFix"
)
PASS_STATUS = (
    "PASS_A1FS_V1_U01QB14R2_UNIT01_RUNTIME_CAPACITY_AWARE_SPIRAL_REUSE_SELECTION"
)
EXPECTED_BINDABLE_SCENE_COUNT = u01qb14r1.EXPECTED_UNIT01_BINDABLE_SCENE_COUNT
REQUIRED_REUSE_SCENE_COUNT = u01qb08.TOTAL_SLOTS - EXPECTED_BINDABLE_SCENE_COUNT
MAX_REUSE_EXCLUSIONS = EXPECTED_BINDABLE_SCENE_COUNT - REQUIRED_REUSE_SCENE_COUNT


class RuntimeCapacitySpiralReuseError(ValueError):
    pass


def _ref(row: Mapping[str, Any]) -> str:
    return str(row.get("scene_ref_id") or "")


def _filtered_reuse_refs(
    rows: Sequence[Mapping[str, Any]],
    extra_slots: int,
    *,
    excluded_refs: set[str],
    original_selector,
) -> set[str]:
    eligible = [row for row in rows if _ref(row) not in excluded_refs]
    if len(eligible) < extra_slots:
        raise RuntimeCapacitySpiralReuseError(
            f"RUNTIME_CAPACITY_REUSE_ELIGIBILITY_INSUFFICIENT:{len(eligible)}:{extra_slots}"
        )
    selected = set(original_selector(eligible, extra_slots))
    if len(selected) != extra_slots:
        raise RuntimeCapacitySpiralReuseError(
            f"RUNTIME_CAPACITY_REUSE_SELECTION_COUNT_INVALID:{len(selected)}:{extra_slots}"
        )
    if selected & excluded_refs:
        raise RuntimeCapacitySpiralReuseError("RUNTIME_CAPACITY_EXCLUDED_SCENE_RESELECTED")
    return selected


def rematerialize_rotation(
    rotation: Mapping[str, Any],
    *,
    reuse_excluded_refs: Sequence[str] = (),
) -> dict[str, Any]:
    """Re-run the existing scheduler while keeping excluded scenes single-use."""
    projection = u01qb14r1.project_existing_rotation(rotation)
    runtime_refs = {_ref(row) for row in projection["runtime_rows"]}
    excluded = {str(value) for value in reuse_excluded_refs if str(value)}
    unknown = sorted(excluded - runtime_refs)
    if unknown:
        raise RuntimeCapacitySpiralReuseError(
            "RUNTIME_CAPACITY_REUSE_EXCLUSION_NOT_BINDABLE:" + ",".join(unknown)
        )
    if len(excluded) > MAX_REUSE_EXCLUSIONS:
        raise RuntimeCapacitySpiralReuseError(
            f"RUNTIME_CAPACITY_REUSE_EXCLUSION_LIMIT_EXCEEDED:{len(excluded)}:{MAX_REUSE_EXCLUSIONS}"
        )

    original_selector = u01qb08.choose_reuse_scene_refs

    def selector(rows: Sequence[Mapping[str, Any]], extra_slots: int) -> set[str]:
        return _filtered_reuse_refs(
            rows,
            extra_slots,
            excluded_refs=excluded,
            original_selector=original_selector,
        )

    u01qb08.choose_reuse_scene_refs = selector
    try:
        rebuilt = u01qb14r1.rematerialize_rotation(rotation)
    finally:
        u01qb08.choose_reuse_scene_refs = original_selector

    usage = {
        str(row["scene_ref_id"]): row
        for row in rebuilt.get("scene_usage_summary") or []
    }
    selected_reuse = sorted(
        ref
        for ref, row in usage.items()
        if bool(row.get("selected_for_spiral_reuse"))
    )
    if len(selected_reuse) != REQUIRED_REUSE_SCENE_COUNT:
        raise RuntimeCapacitySpiralReuseError(
            f"RUNTIME_CAPACITY_REUSE_COUNT_INVALID:{len(selected_reuse)}:{REQUIRED_REUSE_SCENE_COUNT}"
        )
    for ref in sorted(excluded):
        row = usage.get(ref)
        if row is None or int(row.get("exposure_count") or 0) != 1:
            raise RuntimeCapacitySpiralReuseError(
                f"RUNTIME_CAPACITY_EXCLUDED_SCENE_NOT_SINGLE_EXPOSURE:{ref}"
            )

    rebuilt["rotation_policy"]["runtime_capacity_aware_spiral_reuse_selection"] = True
    rebuilt["runtime_capacity_spiral_reuse_projection"] = {
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "bindable_scene_count": EXPECTED_BINDABLE_SCENE_COUNT,
        "required_reuse_scene_count": REQUIRED_REUSE_SCENE_COUNT,
        "reuse_excluded_scene_refs": sorted(excluded),
        "reuse_excluded_scene_count": len(excluded),
        "reuse_eligible_scene_count": EXPECTED_BINDABLE_SCENE_COUNT - len(excluded),
        "selected_reuse_scene_refs": selected_reuse,
        "selected_reuse_scene_count": len(selected_reuse),
        "excluded_scenes_retained_as_single_exposure": True,
        "cumulative_scene_authority_mutated": False,
        "new_scene_authored": False,
        "question_bank_modified": False,
        "runtime_item_total_modified": False,
        "second_planner_created": False,
        "second_runtime_created": False,
        "scoring_modified": False,
    }
    rebuilt["rotation_sha256"] = u01qb08.scene_policy.digest(
        {key: deepcopy(value) for key, value in rebuilt.items() if key != "rotation_sha256"}
    )
    u01qb14r1.u01qb08_validator.validate(rebuilt)
    u01qb14r1.validate_rotation_runtime_bindability(rebuilt)
    return rebuilt
