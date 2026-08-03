#!/usr/bin/env python3
"""Validate U01QB14R1 cumulative-scene to Unit01-runtime bindability projection."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01
from ulga.builders import build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as u01qb01
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u01qb07
from ulga.builders import build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as builder
from ulga.validators import validate_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08_validator
from ulga.validators import validate_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09_validator

PASS_STATUS = "PASS_A1FS_V1_U01QB14R1_UNIT01_RUNTIME_BINDABILITY_GATE_VALIDATION"


class RuntimeBindabilityGateValidationError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeBindabilityGateValidationError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeBindabilityGateValidationError("JSON_OBJECT_REQUIRED")
    return value


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z]+", str(value).casefold().replace("_", " ")))


def _independent_bindability_index() -> dict[str, list[str]]:
    active = {str(row["lemma"]).casefold() for row in u01qb01.nouns()}
    result: dict[str, list[str]] = {}
    for context in s01.CONTEXTS:
        ref = str(context["context_id"])
        text = " ".join(str(row) for row in context["sentences"])
        result[ref] = sorted(_words(text) & active)

    try:
        supplement = json.loads(Path(u01qb07.DEFAULT_SPEC).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeBindabilityGateValidationError(f"SCENE_SUPPLEMENT_UNREADABLE:{exc}") from exc
    for candidate in u01qb07.candidates(supplement):
        ref = str(candidate["candidate_id"])
        object_words = {str(row).casefold() for row in candidate.get("objects", [])}
        setting_words = _words(str(candidate.get("medium_setting") or ""))
        result[ref] = sorted((object_words | setting_words) & active)
    return result


def validate(
    rotation: Mapping[str, Any],
    allocation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        u01qb08_validator.validate(rotation)
    except Exception as exc:
        errors.append(f"u01qb08_invalid:{exc}")

    projection = rotation.get("runtime_bindability_projection")
    if not isinstance(projection, Mapping):
        errors.append("runtime_bindability_projection_missing")
        projection = {}
    if (
        projection.get("schema_version") != builder.SCHEMA_VERSION
        or projection.get("task_id") != builder.TASK_ID
        or projection.get("status") != builder.PASS_STATUS
        or projection.get("unit_id") != builder.UNIT_ID
        or projection.get("gate_rule") != builder.GATE_RULE
    ):
        errors.append("projection_identity_invalid")

    index = _independent_bindability_index()
    expected_deferred = sorted(ref for ref, anchors in index.items() if not anchors)
    if expected_deferred != list(builder.EXPECTED_DEFERRED_SCENE_REFS):
        errors.append("independent_deferred_scene_set_invalid")
    if sorted(str(row) for row in projection.get("deferred_scene_refs") or []) != expected_deferred:
        errors.append("declared_deferred_scene_set_invalid")
    if projection.get("deferred_scenes_remain_in_cumulative_scene_world") is not True:
        errors.append("deferred_scene_preservation_not_declared")
    if projection.get("cumulative_scene_world_count") != builder.EXPECTED_CUMULATIVE_SCENE_WORLD_COUNT:
        errors.append("cumulative_scene_world_count_invalid")
    if projection.get("unit_runtime_bindable_scene_count") != builder.EXPECTED_UNIT01_BINDABLE_SCENE_COUNT:
        errors.append("unit_runtime_bindable_scene_count_invalid")
    if projection.get("unit_runtime_deferred_scene_count") != len(expected_deferred):
        errors.append("unit_runtime_deferred_scene_count_invalid")
    if projection.get("rotation_capacity_pass") is not True:
        errors.append("rotation_capacity_not_pass")

    used_refs: set[str] = set()
    total_slots = 0
    for form in rotation.get("forms") or []:
        for slot in form.get("scene_slots") or []:
            total_slots += 1
            ref = str(slot.get("scene_ref_id") or "")
            anchors = index.get(ref)
            if anchors is None:
                errors.append(f"scene_bindability_identity_missing:{ref}")
                continue
            if not anchors:
                errors.append(f"deferred_scene_leaked_into_rotation:{ref}")
            if list(slot.get("unit_runtime_anchors") or []) != anchors:
                errors.append(f"scene_anchor_projection_mismatch:{ref}")
            if slot.get("unit_runtime_bindable") is not True:
                errors.append(f"rotation_scene_not_declared_bindable:{ref}")
            if slot.get("runtime_bindability_gate_rule") != builder.GATE_RULE:
                errors.append(f"rotation_scene_gate_rule_invalid:{ref}")
            used_refs.add(ref)

    if total_slots != builder.REQUIRED_ROTATION_SLOTS:
        errors.append("rotation_slot_count_invalid")
    if len(used_refs) != builder.EXPECTED_UNIT01_BINDABLE_SCENE_COUNT:
        errors.append("rotation_distinct_bindable_scene_count_invalid")
    if used_refs & set(expected_deferred):
        errors.append("deferred_scene_used")

    allocation_metrics: Mapping[str, Any] = {}
    if allocation is not None:
        try:
            u01qb09_validator.validate(allocation)
        except Exception as exc:
            errors.append(f"u01qb09_invalid:{exc}")
        if allocation.get("source_identity", {}).get("rotation_sha256") != rotation.get("rotation_sha256"):
            errors.append("allocation_rotation_binding_invalid")
        allocation_metrics = allocation.get("allocation_metrics") or {}
        if allocation_metrics.get("form_count") != 12:
            errors.append("allocation_form_count_invalid")
        if allocation_metrics.get("scene_exposure_count") != 48:
            errors.append("allocation_scene_exposure_count_invalid")
        if allocation_metrics.get("activity_slot_count") != 240:
            errors.append("allocation_activity_slot_count_invalid")
        if allocation_metrics.get("scored_activity_slot_count") != 192:
            errors.append("allocation_scored_slot_count_invalid")
        if allocation_metrics.get("speaking_practice_slot_count") != 48:
            errors.append("allocation_speaking_slot_count_invalid")

    if errors:
        raise RuntimeBindabilityGateValidationError("|".join(errors))
    return {
        "status": PASS_STATUS,
        "cumulative_scene_world_count": builder.EXPECTED_CUMULATIVE_SCENE_WORLD_COUNT,
        "unit_runtime_bindable_scene_count": len(used_refs),
        "deferred_scene_refs": expected_deferred,
        "rotation_scene_slot_count": total_slots,
        "allocation_activity_slot_count": allocation_metrics.get("activity_slot_count") if allocation is not None else None,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rotation", type=Path, required=True)
    parser.add_argument("--allocation", type=Path)
    args = parser.parse_args(argv)
    try:
        report = validate(
            read_json(args.rotation),
            read_json(args.allocation) if args.allocation else None,
        )
    except (RuntimeBindabilityGateValidationError, KeyError, TypeError, ValueError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB14R1_UNIT01_RUNTIME_BINDABILITY_GATE_VALIDATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    print(f"CUMULATIVE_SCENE_WORLD={report['cumulative_scene_world_count']}")
    print(f"UNIT01_RUNTIME_BINDABLE_SCENES={report['unit_runtime_bindable_scene_count']}")
    print("DEFERRED_SCENE_REFS=" + ",".join(report["deferred_scene_refs"]))
    print(f"ROTATION_SCENE_SLOTS={report['rotation_scene_slot_count']}")
    if report["allocation_activity_slot_count"] is not None:
        print(f"ALLOCATION_ACTIVITY_SLOTS={report['allocation_activity_slot_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
