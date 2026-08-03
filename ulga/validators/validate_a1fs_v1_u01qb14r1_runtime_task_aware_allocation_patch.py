#!/usr/bin/env python3
"""Validate U01QB14R1 runtime-task-aware allocation metadata."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as builder
from ulga.validators import validate_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09_validator

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
PASS_STATUS = "PASS_A1FS_V1_U01QB14R1_RUNTIME_TASK_AWARE_ALLOCATION_VALIDATION"


class RuntimeTaskAwareAllocationValidationError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeTaskAwareAllocationValidationError("ALLOCATION_OBJECT_REQUIRED")
    return value


def validate(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        base = u01qb09_validator.validate(value)
    except Exception as exc:
        raise RuntimeTaskAwareAllocationValidationError(f"U01QB09_INVALID:{exc}") from exc
    gate = value.get("runtime_task_bindability")
    if not isinstance(gate, Mapping):
        raise RuntimeTaskAwareAllocationValidationError("RUNTIME_TASK_BINDABILITY_MISSING")
    if gate.get("status") != builder.PASS_STATUS:
        raise RuntimeTaskAwareAllocationValidationError("RUNTIME_TASK_BINDABILITY_STATUS_INVALID")
    if gate.get("source_runtime_item_count") != builder.EXPECTED_RUNTIME_ITEMS:
        raise RuntimeTaskAwareAllocationValidationError("SOURCE_RUNTIME_ITEM_COUNT_INVALID")
    if gate.get("all_240_activities_runtime_compatible") is not True:
        raise RuntimeTaskAwareAllocationValidationError("ACTIVITY_RUNTIME_COMPATIBILITY_NOT_PROVEN")
    if gate.get("all_36_skill_sessions_distinct_item_capacity_proven") is not True:
        raise RuntimeTaskAwareAllocationValidationError("SESSION_DISTINCT_ITEM_CAPACITY_NOT_PROVEN")
    if gate.get("verified_activity_count") != 240:
        raise RuntimeTaskAwareAllocationValidationError("VERIFIED_ACTIVITY_COUNT_INVALID")
    for form in value.get("forms") or []:
        for scene in form.get("scene_packages") or []:
            if scene.get("runtime_task_bindability_verified") is not True:
                raise RuntimeTaskAwareAllocationValidationError(
                    f"SCENE_RUNTIME_BINDABILITY_NOT_VERIFIED:{scene.get('scene_ref_id')}"
                )
            for activity in scene.get("activities") or []:
                if int(activity.get("runtime_compatible_item_count") or 0) <= 0:
                    raise RuntimeTaskAwareAllocationValidationError(
                        f"ACTIVITY_RUNTIME_CANDIDATE_COUNT_INVALID:{activity.get('activity_id')}"
                    )
    return {
        "status": PASS_STATUS,
        "form_count": base["form_count"],
        "activity_slot_count": base["activity_slot_count"],
        "runtime_item_count": gate["source_runtime_item_count"],
        "verified_activity_count": gate["verified_activity_count"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allocation", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = validate(read_json(args.allocation))
    except (RuntimeTaskAwareAllocationValidationError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB14R1_RUNTIME_TASK_AWARE_ALLOCATION_VALIDATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    print(f"FORMS={report['form_count']}")
    print(f"ACTIVITY_SLOTS={report['activity_slot_count']}")
    print(f"RUNTIME_ITEMS={report['runtime_item_count']}")
    print(f"VERIFIED_ACTIVITIES={report['verified_activity_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
