#!/usr/bin/env python3
"""Independently validate the CP01 24-unit existing-content backfill."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1_a1plus_cross_skill_learning_units as m02
from ulga.builders import build_a1_a1plus_shared_item_contract as m03
from ulga.builders import build_e4s_a1v1_m11b_authority_exception_resolution as m11b
from ulga.builders.build_a1fs_v1_cp01_existing_24_unit_curriculum_backfill import (
    FOLLOWUP_POOLS,
    M11B_PASS_STATUS,
    NEXT_SHORT_STEP,
    PASS_STATUS,
    PENDING_AUTHORITIES,
    SKILLS,
    SPIRAL_ROLES,
    TASK_ID,
)


def validate_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    source_units = m02.build_artifact()
    source_items = m03.build_artifact()["shared_items"]
    _, bank, admission_report = m11b.build_artifacts()
    units = artifact.get("learning_units", [])

    expected_unit_ids = [row["grammar_unit_id"] for row in source_units["learning_units"]]
    actual_unit_ids = [str(row.get("grammar_unit_id")) for row in units]
    if actual_unit_ids != expected_unit_ids:
        errors.append("canonical_unit_identity_or_order_drift")
    expected_rows = {
        row["grammar_unit_id"]: list(row["canonical_egp_row_ids"])
        for row in source_units["learning_units"]
    }
    if {row_id for ids in expected_rows.values() for row_id in ids} != {
        row_id for row in units for row_id in row.get("canonical_egp_row_ids", [])
    }:
        errors.append("canonical_egp_row_union_drift")

    candidates_by_unit_skill: Counter[tuple[str, str]] = Counter()
    candidate_ids: set[str] = set()
    shared_by_source: dict[str, str] = {}
    for item in source_items:
        key = (str(item["grammar_unit_id"]), str(item["skill"]))
        candidates_by_unit_skill[key] += 1
        candidate_ids.add(str(item["shared_item_id"]))
        shared_by_source[str(item["source_item_id"])] = str(item["shared_item_id"])

    expected_admitted_units: set[str] = set()
    for reviewed in bank["reviewed_units"]:
        unit_id = str(reviewed["grammar_unit_id"])
        expected_admitted_units.add(unit_id)
    expected_admitted = {
        str(item["shared_item_id"])
        for item in source_items
        if item["grammar_unit_id"] in expected_admitted_units
        and item["skill"] in {"reading", "writing"}
    }

    seen_candidates: set[str] = set()
    seen_admitted: set[str] = set()
    admitted_lane_count = 0
    for row in units:
        grammar_id = str(row.get("grammar_unit_id"))
        if row.get("canonical_egp_row_ids") != expected_rows.get(grammar_id):
            errors.append(f"unit_egp_binding_drift:{grammar_id}")
        bindings = row.get("authority_bindings", {})
        grammar = bindings.get("grammar", {})
        if grammar.get("selection_status") != "SELECTED" or grammar.get("selected_refs") != [grammar_id]:
            errors.append(f"grammar_binding_drift:{grammar_id}")
        for authority in PENDING_AUTHORITIES:
            binding = bindings.get(authority, {})
            if binding.get("selection_status") != "PENDING_CONTENT_BINDING" or binding.get("selected_refs") != []:
                errors.append(f"unproven_authority_binding_selected:{grammar_id}:{authority}")

        lanes = row.get("skill_lanes", {})
        if set(lanes) != set(SKILLS):
            errors.append(f"skill_lane_set_drift:{grammar_id}")
            continue
        for skill in SKILLS:
            lane = lanes[skill]
            candidate = lane.get("candidate_item_ids", [])
            admitted = lane.get("admitted_item_ids", [])
            if len(candidate) != candidates_by_unit_skill[(grammar_id, skill)] or len(candidate) != 4:
                errors.append(f"candidate_lane_count_drift:{grammar_id}:{skill}")
            if not set(admitted) <= set(candidate):
                errors.append(f"admitted_not_subset_of_candidate:{grammar_id}:{skill}")
            if admitted:
                admitted_lane_count += 1
                if lane.get("admission_state") != "ADMITTED_PRIVATE_BY_UNIT_ALLOWLIST":
                    errors.append(f"admitted_lane_state_drift:{grammar_id}:{skill}")
                if lane.get("admission_basis") != (
                    "M11B_AUTHORITY_REVIEWED_UNIT_ALLOWLIST_M11C_RUNTIME_PROJECTION"
                ):
                    errors.append(f"admission_basis_drift:{grammar_id}:{skill}")
            elif lane.get("admission_state") != "CANDIDATE_ONLY":
                errors.append(f"candidate_lane_state_drift:{grammar_id}:{skill}")
            elif lane.get("admission_basis") is not None:
                errors.append(f"candidate_lane_false_admission_basis:{grammar_id}:{skill}")
            if set(lane.get("spiral_role_bindings", {})) != set(SPIRAL_ROLES):
                errors.append(f"spiral_role_set_drift:{grammar_id}:{skill}")
            elif any(value != "MISSING_EXPLICIT_ACTIVITY_ROLE_BINDING" for value in lane["spiral_role_bindings"].values()):
                errors.append(f"false_spiral_role_binding:{grammar_id}:{skill}")
            seen_candidates.update(candidate)
            seen_admitted.update(admitted)
        pools = row.get("followup_content_pools", {})
        if set(pools) != set(FOLLOWUP_POOLS) or any(
            value != "MISSING_EXPLICIT_CONTENT_POOL_BINDING" for value in pools.values()
        ):
            errors.append(f"false_followup_pool_binding:{grammar_id}")
        expected_status = (
            "PARTIAL_ADMITTED_PRIVATE"
            if grammar_id in expected_admitted_units
            else "CANDIDATE_ONLY_DEFERRED"
        )
        if row.get("unit_population_status") != expected_status:
            errors.append(f"unit_population_status_drift:{grammar_id}")
        if row.get("four_skill_admitted_population_complete") is not False:
            errors.append(f"false_four_skill_population_complete:{grammar_id}")

    if seen_candidates != candidate_ids:
        errors.append("candidate_item_partition_drift")
    if seen_admitted != expected_admitted:
        errors.append("admitted_item_partition_drift")

    summary = artifact.get("coverage_summary", {})
    expected_summary = {
        "learning_unit_count": 24,
        "canonical_egp_row_count": 109,
        "candidate_item_count": 384,
        "unit_assigned_candidate_item_count": 384,
        "admitted_private_item_count": 184,
        "candidate_only_item_count": 200,
        "admitted_private_unit_count": 23,
        "deferred_unit_count": 1,
        "skill_lane_count": 96,
        "admitted_skill_lane_count": 46,
        "admission_gap_skill_lane_count": 50,
        "four_skill_admitted_unit_count": 0,
        "pending_content_authority_binding_count": 96,
        "explicit_spiral_role_binding_count": 0,
        "missing_spiral_role_binding_count": 96,
        "explicit_followup_content_pool_binding_count": 0,
        "missing_followup_content_pool_binding_count": 72,
        "admitted_private_item_counts_by_skill": {
            "reading": 92,
            "writing": 92,
            "listening": 0,
            "speaking": 0,
        },
    }
    if summary != expected_summary:
        errors.append("coverage_summary_drift")
    if admitted_lane_count != 46:
        errors.append("admitted_lane_count_drift")
    if admission_report.get("validation_status") != M11B_PASS_STATUS:
        errors.append("admission_source_not_pass")

    boundaries = artifact.get("claim_boundaries", {})
    if any(value is not False for value in boundaries.values()):
        errors.append("claim_boundary_falsehood")
    if artifact.get("next_short_step") != NEXT_SHORT_STEP:
        errors.append("next_short_step_drift")

    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "learning_unit_count": len(units),
        "canonical_egp_row_count": len(
            {row_id for row in units for row_id in row.get("canonical_egp_row_ids", [])}
        ),
        "candidate_item_count": len(seen_candidates),
        "admitted_private_item_count": len(seen_admitted),
        "admission_gap_skill_lane_count": 96 - admitted_lane_count,
        "four_skill_admitted_unit_count": sum(
            row.get("four_skill_admitted_population_complete") is True for row in units
        ),
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if not errors else None,
    }
