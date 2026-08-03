#!/usr/bin/env python3
"""Materialize deterministic 12-form Unit01 scene rotation from an approved cumulative scene pool."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as scene_policy
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as source_builder
from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as policy_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Deterministic rotation manifest over already-approved Unit01 scene authority; no new learner content or canonical content mutation."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB08_Unit01TwelveFormSceneRotationMaterialization"
SCHEMA_VERSION = "a1fs.v1.u01qb08.unit01_twelve_form_scene_rotation.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB08_UNIT01_TWELVE_FORM_SCENE_ROTATION_MATERIALIZATION"
UNIT_ID = "GRAMMAR_ARTICLES_BASIC"
FORM_COUNT = 12
SCENES_PER_FORM = 4
TOTAL_SLOTS = FORM_COUNT * SCENES_PER_FORM
MAX_EXPOSURES = 2
MIN_FORM_FAMILIES = 3
MAX_SCENES_SAME_FAMILY = 2
MIN_REPEAT_FORM_DELTA = 3
REUSED_SCENE_CHANGED_DIMENSIONS_MIN = 2
DEFAULT_OUTPUT = Path("ulga/reports/a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB09_Unit01SceneSkillTaskAngleSupportAllocation"


class SceneRotationError(ValueError):
    pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SceneRotationError(f"UNREADABLE_JSON:{path}:{exc}") from exc


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def approved_scene_rows(approved: Mapping[str, Any]) -> list[dict[str, Any]]:
    report = policy_validator.validate_artifact(
        approved,
        expected_role=content_policy.APPROVED_ROLE,
    )
    if report.get("validation_status") != policy_validator.PASS_STATUS:
        raise SceneRotationError("APPROVED_SCENE_ARTIFACT_POLICY_INVALID")
    payload = approved.get("payload")
    if not isinstance(payload, Mapping):
        raise SceneRotationError("APPROVED_SCENE_PAYLOAD_REQUIRED")
    if (
        payload.get("task_id") != source_builder.TASK_ID
        or payload.get("unit_id") != UNIT_ID
        or payload.get("status") != source_builder.PASS_STATUS
    ):
        raise SceneRotationError("APPROVED_SCENE_POOL_IDENTITY_INVALID")
    capacity = payload.get("rotation_capacity")
    if not isinstance(capacity, Mapping) or capacity.get("twelve_form_rotation_ready") is not True:
        raise SceneRotationError("SOURCE_SCENE_POOL_NOT_ROTATION_READY")
    rows = payload.get("cumulative_unique_scenes")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise SceneRotationError("CUMULATIVE_UNIQUE_SCENES_REQUIRED")
    if not (scene_policy.TARGET_DISTINCT_MICRO_SCENES_MIN <= len(rows) <= scene_policy.TARGET_DISTINCT_MICRO_SCENES_MAX):
        raise SceneRotationError(f"SCENE_POOL_OUTSIDE_TARGET_RANGE:{len(rows)}")
    normalized: list[dict[str, Any]] = []
    seen_refs: set[str] = set()
    seen_signatures: set[str] = set()
    for row in rows:
        ref = str(row.get("scene_ref_id") or "")
        signature = str(row.get("semantic_scene_signature_v2") or "")
        family = str(row.get("situation_family") or "")
        setting = str(row.get("setting") or "")
        if not ref or not signature or not family or not setting:
            raise SceneRotationError("SCENE_ROTATION_FIELDS_REQUIRED")
        if ref in seen_refs or signature in seen_signatures:
            raise SceneRotationError("SCENE_POOL_DUPLICATE_IDENTITY")
        seen_refs.add(ref)
        seen_signatures.add(signature)
        normalized.append(
            {
                "scene_ref_id": ref,
                "semantic_scene_signature_v2": signature,
                "situation_family": family,
                "setting": setting,
                "micro_scene_event_id": str(row.get("micro_scene_event_id") or ""),
                "scene_origin": str(row.get("scene_origin") or ""),
            }
        )
    return sorted(normalized, key=lambda row: (row["situation_family"], row["scene_ref_id"]))


def choose_reuse_scene_refs(rows: Sequence[Mapping[str, Any]], extra_slots: int) -> set[str]:
    by_family: dict[str, list[str]] = defaultdict(list)
    for row in sorted(rows, key=lambda item: (str(item["situation_family"]), str(item["scene_ref_id"]))):
        by_family[str(row["situation_family"])].append(str(row["scene_ref_id"]))
    families = sorted(by_family)
    indexes = {family: 0 for family in families}
    selected: list[str] = []
    while len(selected) < extra_slots:
        progressed = False
        for family in families:
            if len(selected) >= extra_slots:
                break
            index = indexes[family]
            if index < len(by_family[family]):
                selected.append(by_family[family][index])
                indexes[family] += 1
                progressed = True
        if not progressed:
            break
    if len(selected) != extra_slots:
        raise SceneRotationError("REUSE_TARGET_SELECTION_INCOMPLETE")
    return set(selected)


def schedule_forms(rows: Sequence[Mapping[str, Any]]) -> tuple[list[list[str]], set[str]]:
    if len(rows) > TOTAL_SLOTS or len(rows) * MAX_EXPOSURES < TOTAL_SLOTS:
        raise SceneRotationError("SCENE_POOL_CAPACITY_INVALID")
    scene_by_ref = {str(row["scene_ref_id"]): dict(row) for row in rows}
    extra_slots = TOTAL_SLOTS - len(rows)
    reuse_refs = choose_reuse_scene_refs(rows, extra_slots)
    remaining = {ref: (2 if ref in reuse_refs else 1) for ref in scene_by_ref}
    used_count = {ref: 0 for ref in scene_by_ref}
    last_form = {ref: -999 for ref in scene_by_ref}
    forms: list[list[str]] = []

    def solve_form(form_index: int) -> bool:
        return fill_slot(form_index, [], Counter())

    def fill_slot(form_index: int, selected: list[str], family_counts: Counter[str]) -> bool:
        if form_index == FORM_COUNT:
            return len(selected) == 0 and all(value == 0 for value in remaining.values())
        if len(selected) == SCENES_PER_FORM:
            if len(family_counts) < MIN_FORM_FAMILIES:
                return False
            forms.append(list(selected))
            if solve_form(form_index + 1):
                return True
            forms.pop()
            return False

        slots_left = SCENES_PER_FORM - len(selected)
        families_needed = max(0, MIN_FORM_FAMILIES - len(family_counts))
        if families_needed > slots_left:
            return False

        ranked: list[tuple[tuple[Any, ...], str]] = []
        for ref, remaining_count in remaining.items():
            if remaining_count <= 0 or ref in selected:
                continue
            if used_count[ref] > 0 and form_index - last_form[ref] < MIN_REPEAT_FORM_DELTA:
                continue
            family = scene_by_ref[ref]["situation_family"]
            if family_counts[family] >= MAX_SCENES_SAME_FAMILY:
                continue
            rank = (
                family in family_counts,
                used_count[ref] > 0,
                -remaining_count,
                last_form[ref],
                family,
                ref,
            )
            ranked.append((rank, ref))
        ranked.sort()

        for _, ref in ranked:
            family = scene_by_ref[ref]["situation_family"]
            previous_last = last_form[ref]
            remaining[ref] -= 1
            used_count[ref] += 1
            last_form[ref] = form_index
            selected.append(ref)
            family_counts[family] += 1
            if fill_slot(form_index, selected, family_counts):
                return True
            family_counts[family] -= 1
            if family_counts[family] == 0:
                del family_counts[family]
            selected.pop()
            last_form[ref] = previous_last
            used_count[ref] -= 1
            remaining[ref] += 1
        return False

    if not solve_form(0):
        raise SceneRotationError("DETERMINISTIC_ROTATION_SCHEDULING_FAILED")
    return forms, reuse_refs


def build_rotation(approved: Mapping[str, Any]) -> dict[str, Any]:
    rows = approved_scene_rows(approved)
    scene_by_ref = {row["scene_ref_id"]: row for row in rows}
    form_refs, reuse_refs = schedule_forms(rows)
    usage_forms: dict[str, list[int]] = defaultdict(list)
    forms: list[dict[str, Any]] = []

    for form_index, refs in enumerate(form_refs, start=1):
        family_counts = Counter(scene_by_ref[ref]["situation_family"] for ref in refs)
        slots: list[dict[str, Any]] = []
        for slot_index, ref in enumerate(refs, start=1):
            usage_forms[ref].append(form_index)
            exposure_ordinal = len(usage_forms[ref])
            prior_form = usage_forms[ref][-2] if exposure_ordinal == 2 else None
            slots.append(
                {
                    "slot": slot_index,
                    **deepcopy(scene_by_ref[ref]),
                    "exposure_ordinal": exposure_ordinal,
                    "prior_form_ordinal": prior_form,
                    "repeat_form_delta": form_index - prior_form if prior_form is not None else None,
                    "downstream_reuse_obligation": (
                        {
                            "changed_dimensions_min": REUSED_SCENE_CHANGED_DIMENSIONS_MIN,
                            "same_skill_same_task_angle_repeat_allowed": False,
                            "required_change_candidates": ["SUPPORT_LEVEL", "SKILL", "TASK_ANGLE", "PROMPT_PERSPECTIVE"],
                        }
                        if exposure_ordinal == 2
                        else None
                    ),
                }
            )
        forms.append(
            {
                "form_id": f"U01-FORM-{form_index:02d}",
                "form_ordinal": form_index,
                "week": 1 if form_index <= 6 else 2,
                "day_in_week": form_index if form_index <= 6 else form_index - 6,
                "scene_count": len(slots),
                "distinct_situation_family_count": len(family_counts),
                "family_counts": dict(sorted(family_counts.items())),
                "scene_slots": slots,
            }
        )

    usage_summary = []
    for ref in sorted(scene_by_ref):
        ordinals = usage_forms[ref]
        usage_summary.append(
            {
                "scene_ref_id": ref,
                "situation_family": scene_by_ref[ref]["situation_family"],
                "exposure_count": len(ordinals),
                "form_ordinals": ordinals,
                "repeat_form_delta": ordinals[1] - ordinals[0] if len(ordinals) == 2 else None,
                "selected_for_spiral_reuse": ref in reuse_refs,
            }
        )

    family_slot_counts = Counter(
        slot["situation_family"] for form in forms for slot in form["scene_slots"]
    )
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "source_identity": {
            "approved_scene_artifact_sha256": approved["artifact_sha256"],
            "approved_scene_artifact_role": approved["artifact_role"],
            "approved_scene_task_id": approved["payload"]["task_id"],
        },
        "rotation_policy": {
            "form_count": FORM_COUNT,
            "scenes_per_form": SCENES_PER_FORM,
            "total_scene_slots": TOTAL_SLOTS,
            "max_exposures_per_exact_micro_scene": MAX_EXPOSURES,
            "min_form_situation_families": MIN_FORM_FAMILIES,
            "max_form_scenes_from_same_family": MAX_SCENES_SAME_FAMILY,
            "min_form_gap_before_exact_scene_reuse": MIN_REPEAT_FORM_DELTA,
            "reused_scene_min_changed_dimensions": REUSED_SCENE_CHANGED_DIMENSIONS_MIN,
            "same_scene_same_skill_same_task_angle_repeat_allowed": False,
        },
        "scene_growth_policy": deepcopy(scene_policy.SCENE_GROWTH_POLICY),
        "forms": forms,
        "scene_usage_summary": usage_summary,
        "rotation_metrics": {
            "distinct_scene_count": len(rows),
            "scene_slot_count": sum(len(form["scene_slots"]) for form in forms),
            "reused_scene_count": len(reuse_refs),
            "single_exposure_scene_count": len(rows) - len(reuse_refs),
            "max_exposure_count": max(item["exposure_count"] for item in usage_summary),
            "min_repeat_form_delta": min(
                (item["repeat_form_delta"] for item in usage_summary if item["repeat_form_delta"] is not None),
                default=None,
            ),
            "situation_family_count": len(family_slot_counts),
            "family_slot_counts": dict(sorted(family_slot_counts.items())),
            "all_12_forms_materialized": len(forms) == FORM_COUNT,
            "all_48_slots_materialized": sum(len(form["scene_slots"]) for form in forms) == TOTAL_SLOTS,
        },
        "boundaries": {
            "new_scene_authored": False,
            "question_bank_modified": False,
            "skill_assignment_materialized": False,
            "task_angle_assignment_materialized": False,
            "scoring_modified": False,
            "learner_state_modified": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    artifact["rotation_sha256"] = scene_policy.digest(artifact)
    return artifact


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-scene-pool", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        artifact = build_rotation(read_json(args.approved_scene_pool))
        write_json(args.output, artifact)
    except (SceneRotationError, KeyError, TypeError, ValueError, OSError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB08_UNIT01_TWELVE_FORM_SCENE_ROTATION")
        print(f"ERROR={exc}")
        return 1
    metrics = artifact["rotation_metrics"]
    print(f"STATUS={PASS_STATUS}")
    print(f"DISTINCT_SCENES={metrics['distinct_scene_count']}")
    print(f"FORM_COUNT={len(artifact['forms'])}")
    print(f"SCENE_SLOTS={metrics['scene_slot_count']}")
    print(f"REUSED_SCENES={metrics['reused_scene_count']}")
    print(f"MIN_REPEAT_FORM_DELTA={metrics['min_repeat_form_delta']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
