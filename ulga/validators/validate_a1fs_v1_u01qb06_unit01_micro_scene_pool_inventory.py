#!/usr/bin/env python3
"""Independent validation for repaired Unit01 semantic micro-scene inventory."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as builder

PASS_STATUS = "PASS_A1FS_V1_U01QB06R1_UNIT01_SEMANTIC_SCENE_IDENTITY_AND_GENUINE_LIFE_SCENE_GATE_VALIDATION"


class InventoryValidationError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryValidationError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise InventoryValidationError("INVENTORY_OBJECT_REQUIRED")
    return value


def validate(inventory: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if inventory.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if inventory.get("task_id") != builder.TASK_ID:
        errors.append("task_id_invalid")
    if inventory.get("status") != builder.PASS_STATUS:
        errors.append("status_invalid")
    if inventory.get("unit_id") != builder.UNIT_ID:
        errors.append("unit_id_invalid")

    expected_scope = {
        "unit01_only": True,
        "question_bank_modified": False,
        "parallel_question_bank_created": False,
        "parallel_scoring_created": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }
    if inventory.get("scope") != expected_scope:
        errors.append("scope_boundary_invalid")

    expected_policy = {
        "semantic_scene_signature_version": builder.SEMANTIC_SCENE_SIGNATURE_VERSION,
        "source_identity_in_semantic_signature": False,
        "source_or_pedagogic_role_in_semantic_signature": False,
        "theme_in_semantic_signature": False,
        "project_authored_gap_completion_counts_as_genuine_scene": False,
        "under_specified_object_only_asset_counts_as_genuine_scene": False,
        "setting_only_identification_counts_as_genuine_scene": False,
        "canonical_context_semantics_extracted_from_context_text": True,
        "canonical_unit01_context_counts_only_if_genuine_scene_gate_passes": True,
    }
    if inventory.get("inventory_policy") != expected_policy:
        errors.append("semantic_scene_policy_invalid")

    expected_taxonomy = {
        "large_class": "SITUATION_FAMILY",
        "medium_class": "SETTING",
        "small_class": "MICRO_SCENE_EVENT",
        "theme_is_separate_from_situation_family": True,
        "situation_family_derived_from_setting_only": True,
    }
    if inventory.get("scene_taxonomy_policy") != expected_taxonomy:
        errors.append("scene_taxonomy_policy_invalid")
    if inventory.get("scene_growth_policy") != builder.SCENE_GROWTH_POLICY:
        errors.append("scene_growth_policy_invalid")
    if inventory.get("model_enrichment_policy") != builder.MODEL_ENRICHMENT_POLICY:
        errors.append("model_enrichment_policy_invalid")

    expected_rotation = {
        "form_count": builder.FORM_COUNT,
        "scenes_per_form": builder.SCENES_PER_FORM,
        "total_scene_slots": builder.TOTAL_SCENE_SLOTS,
        "max_exposures_per_exact_micro_scene": builder.MAX_EXPOSURES_PER_EXACT_SCENE,
        "hard_min_distinct_micro_scenes": builder.HARD_MIN_DISTINCT_MICRO_SCENES,
        "target_distinct_micro_scenes": [builder.TARGET_DISTINCT_MICRO_SCENES_MIN, builder.TARGET_DISTINCT_MICRO_SCENES_MAX],
        "min_pool_situation_families": builder.MIN_POOL_SITUATION_FAMILIES,
        "min_form_situation_families": builder.MIN_FORM_SITUATION_FAMILIES,
        "max_form_scenes_from_same_family": builder.MAX_FORM_SCENES_FROM_SAME_FAMILY,
        "min_form_gap_before_exact_scene_reuse": builder.MIN_FORM_GAP_BEFORE_EXACT_SCENE_REUSE,
        "reused_scene_min_changed_dimensions": builder.REUSED_SCENE_MIN_CHANGED_DIMENSIONS,
        "same_scene_same_skill_same_task_angle_repeat_allowed": False,
    }
    if inventory.get("rotation_policy") != expected_rotation:
        errors.append("rotation_policy_invalid")

    rows = inventory.get("scene_rows") if isinstance(inventory.get("scene_rows"), list) else []
    unique = inventory.get("unique_rotation_scenes") if isinstance(inventory.get("unique_rotation_scenes"), list) else []
    if "scene_rows" not in inventory or "unique_rotation_scenes" not in inventory:
        errors.append("scene_arrays_invalid")

    forbidden_core_keys = {
        "source_record_id",
        "semantic_identity",
        "content_asset_id",
        "scene_ref_id",
        "legacy_semantic_scene_id",
        "context_role",
        "source_role",
        "theme_id",
        "situation_family",
        "unit_id",
        "grammar_target",
    }
    for row in rows:
        if not isinstance(row, Mapping):
            errors.append("scene_row_not_object")
            continue
        core = row.get("semantic_scene_core")
        if not isinstance(core, Mapping):
            errors.append("semantic_scene_core_missing")
            continue
        if forbidden_core_keys & set(core):
            errors.append("nonsemantic_identity_leaked_into_semantic_core")
        if row.get("semantic_scene_signature_v2") != builder.digest(core):
            errors.append("semantic_scene_signature_v2_mismatch")

        expected_taxonomy_row = builder.scene_taxonomy(core)
        if row.get("scene_taxonomy") != expected_taxonomy_row:
            errors.append("scene_taxonomy_mismatch")
        if row.get("situation_family") != builder.situation_family(str(core.get("setting") or "")):
            errors.append("situation_family_not_setting_derived")
        if row.get("situation_family") != expected_taxonomy_row["large_situation_family"]:
            errors.append("situation_family_taxonomy_mismatch")

        if row.get("lineage_mode") == "PROJECT_AUTHORED_CONTRACT_COMPLETION" and row.get("counts_toward_scene_rotation") is not False:
            errors.append("project_completion_counted_as_genuine_scene")

        gate_reasons = builder.genuine_scene_reason_codes(core)
        if row.get("counts_toward_scene_rotation") is True and gate_reasons:
            errors.append("rotation_ready_scene_fails_genuine_life_scene_gate")
        if row.get("rotation_class") == "ROTATION_READY" and gate_reasons:
            errors.append("rotation_class_ready_but_gate_failed")
        if row.get("rotation_class") in {"SCENE_SEED_NEEDS_ENRICHMENT", "CANONICAL_CONTEXT_NEEDS_ENRICHMENT"} and not gate_reasons:
            errors.append("scene_seed_class_without_gate_reason")

    recomputed_unique = builder.unique_rotation_scenes(rows)
    if recomputed_unique != unique:
        errors.append("unique_rotation_scene_recompute_mismatch")
    if builder.duplicate_groups(rows) != inventory.get("semantic_duplicate_groups"):
        errors.append("semantic_duplicate_group_recompute_mismatch")

    distinct = len(recomputed_unique)
    families = {
        row["situation_family"]
        for row in recomputed_unique
        if row.get("situation_family") != "UNCLASSIFIED_OBJECT"
    }
    ready = distinct >= builder.HARD_MIN_DISTINCT_MICRO_SCENES and len(families) >= builder.MIN_POOL_SITUATION_FAMILIES
    expected_readiness = {
        "genuine_distinct_micro_scene_count": distinct,
        "non_unclassified_situation_family_count": len(families),
        "maximum_scene_slots_at_two_uses_each": distinct * builder.MAX_EXPOSURES_PER_EXACT_SCENE,
        "required_scene_slots": builder.TOTAL_SCENE_SLOTS,
        "hard_distinct_scene_capacity_pass": distinct >= builder.HARD_MIN_DISTINCT_MICRO_SCENES,
        "situation_family_capacity_pass": len(families) >= builder.MIN_POOL_SITUATION_FAMILIES,
        "twelve_form_rotation_ready": ready,
        "scene_shortfall_to_hard_min": max(0, builder.HARD_MIN_DISTINCT_MICRO_SCENES - distinct),
        "scene_shortfall_to_target_min": max(0, builder.TARGET_DISTINCT_MICRO_SCENES_MIN - distinct),
        "family_shortfall": max(0, builder.MIN_POOL_SITUATION_FAMILIES - len(families)),
        "release_classification": "READY_FOR_12_FORM_ROTATION" if ready else "NOT_READY_SCENE_POOL_SUPPLEMENTATION_REQUIRED",
    }
    if inventory.get("rotation_readiness") != expected_readiness:
        errors.append("rotation_readiness_recompute_mismatch")

    unsigned = deepcopy(dict(inventory))
    declared = unsigned.pop("inventory_sha256", None)
    if declared != builder.digest(unsigned):
        errors.append("inventory_sha256_invalid")

    boundaries = inventory.get("boundaries") or {}
    if any(
        boundaries.get(key) is not False
        for key in (
            "content_assets_mutated",
            "canonical_contexts_mutated",
            "question_items_mutated",
            "learner_state_mutated",
            "scoring_mutated",
            "mastery_claimed",
        )
    ):
        errors.append("mutation_boundary_invalid")

    report = {
        "schema_version": "a1fs.v1.u01qb06.unit01_micro_scene_pool_inventory.validation.v2",
        "task_id": builder.TASK_ID,
        "status": PASS_STATUS if not errors else "FAIL_A1FS_V1_U01QB06R1_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "genuine_distinct_micro_scene_count": distinct,
        "situation_family_count": len(families),
        "twelve_form_rotation_ready": ready,
        "scene_shortfall_to_hard_min": max(0, builder.HARD_MIN_DISTINCT_MICRO_SCENES - distinct),
    }
    if errors:
        raise InventoryValidationError("|".join(errors))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = validate(read_json(args.inventory))
    except (InventoryValidationError, KeyError, TypeError, ValueError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB06R1_UNIT01_SEMANTIC_SCENE_IDENTITY_AND_GENUINE_LIFE_SCENE_GATE_VALIDATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    print(f"GENUINE_DISTINCT_MICRO_SCENES={report['genuine_distinct_micro_scene_count']}")
    print(f"SITUATION_FAMILIES={report['situation_family_count']}")
    print(f"TWELVE_FORM_ROTATION_READY={report['twelve_form_rotation_ready']}")
    print(f"SCENE_SHORTFALL_TO_24={report['scene_shortfall_to_hard_min']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
