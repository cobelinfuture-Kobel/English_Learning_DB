#!/usr/bin/env python3
"""Independently validate Unit01 12-form scene rotation materialization."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as scene_policy
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as builder

PASS_STATUS = "PASS_A1FS_V1_U01QB08_UNIT01_TWELVE_FORM_SCENE_ROTATION_VALIDATION"


class SceneRotationValidationError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SceneRotationValidationError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise SceneRotationValidationError("ROTATION_OBJECT_REQUIRED")
    return value


def validate(rotation: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if rotation.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if (
        rotation.get("task_id") != builder.TASK_ID
        or rotation.get("status") != builder.PASS_STATUS
        or rotation.get("unit_id") != builder.UNIT_ID
    ):
        errors.append("identity_invalid")
    source = rotation.get("source_identity") or {}
    if (
        source.get("approved_scene_artifact_role") != "APPROVED_CANONICAL_JSON"
        or source.get("approved_scene_task_id")
        != "A1FS-V1-U01QB07_Unit01MicroSceneSeedEnrichmentAndRotationCapacityExpansion"
        or not isinstance(source.get("approved_scene_artifact_sha256"), str)
        or len(source.get("approved_scene_artifact_sha256")) != 64
    ):
        errors.append("approved_source_binding_invalid")

    expected_policy = {
        "form_count": builder.FORM_COUNT,
        "scenes_per_form": builder.SCENES_PER_FORM,
        "total_scene_slots": builder.TOTAL_SLOTS,
        "max_exposures_per_exact_micro_scene": builder.MAX_EXPOSURES,
        "min_form_situation_families": builder.MIN_FORM_FAMILIES,
        "max_form_scenes_from_same_family": builder.MAX_SCENES_SAME_FAMILY,
        "min_form_gap_before_exact_scene_reuse": builder.MIN_REPEAT_FORM_DELTA,
        "reused_scene_min_changed_dimensions": builder.REUSED_SCENE_CHANGED_DIMENSIONS_MIN,
        "same_scene_same_skill_same_task_angle_repeat_allowed": False,
    }
    if rotation.get("rotation_policy") != expected_policy:
        errors.append("rotation_policy_invalid")
    if rotation.get("scene_growth_policy") != scene_policy.SCENE_GROWTH_POLICY:
        errors.append("scene_growth_policy_invalid")

    forms = rotation.get("forms") if isinstance(rotation.get("forms"), list) else []
    if len(forms) != builder.FORM_COUNT:
        errors.append("form_count_invalid")

    scene_forms: dict[str, list[int]] = defaultdict(list)
    seen_signatures_by_ref: dict[str, str] = {}
    total_slots = 0
    family_slot_counts: Counter[str] = Counter()
    for expected_ordinal, form in enumerate(forms, start=1):
        if not isinstance(form, Mapping):
            errors.append("form_not_object")
            continue
        if (
            form.get("form_id") != f"U01-FORM-{expected_ordinal:02d}"
            or form.get("form_ordinal") != expected_ordinal
        ):
            errors.append("form_identity_invalid")
        expected_week = 1 if expected_ordinal <= 6 else 2
        expected_day = expected_ordinal if expected_ordinal <= 6 else expected_ordinal - 6
        if form.get("week") != expected_week or form.get("day_in_week") != expected_day:
            errors.append("two_week_day_mapping_invalid")
        slots = form.get("scene_slots") if isinstance(form.get("scene_slots"), list) else []
        if len(slots) != builder.SCENES_PER_FORM or form.get("scene_count") != builder.SCENES_PER_FORM:
            errors.append("scenes_per_form_invalid")
            continue
        refs = [str(slot.get("scene_ref_id")) for slot in slots if isinstance(slot, Mapping)]
        if len(refs) != len(set(refs)):
            errors.append("duplicate_scene_within_form")
        families = Counter(str(slot.get("situation_family")) for slot in slots if isinstance(slot, Mapping))
        if len(families) < builder.MIN_FORM_FAMILIES:
            errors.append("form_family_diversity_below_min")
        if any(count > builder.MAX_SCENES_SAME_FAMILY for count in families.values()):
            errors.append("form_family_concentration_above_max")
        if form.get("distinct_situation_family_count") != len(families):
            errors.append("form_family_count_mismatch")
        if form.get("family_counts") != dict(sorted(families.items())):
            errors.append("form_family_breakdown_mismatch")

        for expected_slot, slot in enumerate(slots, start=1):
            total_slots += 1
            if not isinstance(slot, Mapping):
                errors.append("scene_slot_not_object")
                continue
            if slot.get("slot") != expected_slot:
                errors.append("slot_ordinal_invalid")
            ref = str(slot.get("scene_ref_id") or "")
            signature = str(slot.get("semantic_scene_signature_v2") or "")
            family = str(slot.get("situation_family") or "")
            if not ref or not signature or not family:
                errors.append("scene_slot_identity_missing")
                continue
            prior_forms = scene_forms[ref]
            expected_exposure = len(prior_forms) + 1
            expected_prior = prior_forms[-1] if prior_forms else None
            if slot.get("exposure_ordinal") != expected_exposure:
                errors.append("exposure_ordinal_invalid")
            if slot.get("prior_form_ordinal") != expected_prior:
                errors.append("prior_form_ordinal_invalid")
            if expected_prior is None:
                if slot.get("repeat_form_delta") is not None or slot.get("downstream_reuse_obligation") is not None:
                    errors.append("first_exposure_repeat_metadata_invalid")
            else:
                delta = expected_ordinal - expected_prior
                if slot.get("repeat_form_delta") != delta or delta < builder.MIN_REPEAT_FORM_DELTA:
                    errors.append("repeat_form_gap_invalid")
                obligation = slot.get("downstream_reuse_obligation")
                if not isinstance(obligation, Mapping):
                    errors.append("repeat_obligation_missing")
                elif (
                    obligation.get("changed_dimensions_min") != builder.REUSED_SCENE_CHANGED_DIMENSIONS_MIN
                    or obligation.get("same_skill_same_task_angle_repeat_allowed") is not False
                ):
                    errors.append("repeat_obligation_invalid")
            scene_forms[ref].append(expected_ordinal)
            if ref in seen_signatures_by_ref and seen_signatures_by_ref[ref] != signature:
                errors.append("scene_signature_drift_across_forms")
            seen_signatures_by_ref[ref] = signature
            family_slot_counts[family] += 1

    if total_slots != builder.TOTAL_SLOTS:
        errors.append("total_scene_slots_invalid")
    if any(len(form_ordinals) > builder.MAX_EXPOSURES for form_ordinals in scene_forms.values()):
        errors.append("scene_exposure_above_max")

    usage = rotation.get("scene_usage_summary") if isinstance(rotation.get("scene_usage_summary"), list) else []
    usage_by_ref = {str(row.get("scene_ref_id")): row for row in usage if isinstance(row, Mapping)}
    if set(usage_by_ref) != set(scene_forms):
        errors.append("scene_usage_summary_identity_mismatch")
    for ref, ordinals in scene_forms.items():
        row = usage_by_ref.get(ref, {})
        expected_delta = ordinals[1] - ordinals[0] if len(ordinals) == 2 else None
        if (
            row.get("exposure_count") != len(ordinals)
            or row.get("form_ordinals") != ordinals
            or row.get("repeat_form_delta") != expected_delta
            or row.get("selected_for_spiral_reuse") is not (len(ordinals) == 2)
        ):
            errors.append("scene_usage_summary_mismatch")

    repeat_deltas = [ordinals[1] - ordinals[0] for ordinals in scene_forms.values() if len(ordinals) == 2]
    metrics = rotation.get("rotation_metrics") or {}
    expected_metrics = {
        "distinct_scene_count": len(scene_forms),
        "scene_slot_count": total_slots,
        "reused_scene_count": sum(len(ordinals) == 2 for ordinals in scene_forms.values()),
        "single_exposure_scene_count": sum(len(ordinals) == 1 for ordinals in scene_forms.values()),
        "max_exposure_count": max((len(ordinals) for ordinals in scene_forms.values()), default=0),
        "min_repeat_form_delta": min(repeat_deltas) if repeat_deltas else None,
        "situation_family_count": len(family_slot_counts),
        "family_slot_counts": dict(sorted(family_slot_counts.items())),
        "all_12_forms_materialized": len(forms) == builder.FORM_COUNT,
        "all_48_slots_materialized": total_slots == builder.TOTAL_SLOTS,
    }
    if metrics != expected_metrics:
        errors.append("rotation_metrics_mismatch")

    boundaries = rotation.get("boundaries") or {}
    if boundaries != {
        "new_scene_authored": False,
        "question_bank_modified": False,
        "skill_assignment_materialized": False,
        "task_angle_assignment_materialized": False,
        "scoring_modified": False,
        "learner_state_modified": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }:
        errors.append("boundary_invalid")

    unsigned = deepcopy(dict(rotation))
    declared = unsigned.pop("rotation_sha256", None)
    if declared != scene_policy.digest(unsigned):
        errors.append("rotation_sha256_invalid")

    report = {
        "status": PASS_STATUS if not errors else "FAIL_A1FS_V1_U01QB08_UNIT01_TWELVE_FORM_SCENE_ROTATION_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "form_count": len(forms),
        "scene_slot_count": total_slots,
        "distinct_scene_count": len(scene_forms),
        "reused_scene_count": sum(len(ordinals) == 2 for ordinals in scene_forms.values()),
        "min_repeat_form_delta": min(repeat_deltas) if repeat_deltas else None,
    }
    if errors:
        raise SceneRotationValidationError("|".join(errors))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rotation", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = validate(read_json(args.rotation))
    except (SceneRotationValidationError, KeyError, TypeError, ValueError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB08_UNIT01_TWELVE_FORM_SCENE_ROTATION_VALIDATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    print(f"FORM_COUNT={report['form_count']}")
    print(f"SCENE_SLOTS={report['scene_slot_count']}")
    print(f"DISTINCT_SCENES={report['distinct_scene_count']}")
    print(f"REUSED_SCENES={report['reused_scene_count']}")
    print(f"MIN_REPEAT_FORM_DELTA={report['min_repeat_form_delta']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
