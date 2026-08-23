#!/usr/bin/env python3
"""Validate the read-only U02CH02 cumulative chunk/phrase reconciliation."""
from __future__ import annotations

from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u02ch02_unit01_unit02_cumulative_chunk_coverage_recheck as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U02CH02_CUMULATIVE_CHUNK_COVERAGE_RECHECK_VALIDATOR"


class U02CH02ValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise U02CH02ValidationError(code)


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    require(report.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(report.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(report.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    counts = report.get("coverage_denominators", {})

    expected = {
        "unit01_reference_inventory_rows": builder.EXPECTED_UNIT01_INVENTORY,
        "unit01_canonical_chunk_rows": 3,
        "unit01_instructional_phrase_rows": 21,
        "unit01_direct_or_instructional_surface_rows": builder.EXPECTED_UNIT01_DIRECT_OR_INSTRUCTIONAL,
        "unit01_receptive_only_surface_rows": builder.EXPECTED_UNIT01_RECEPTIVE_ONLY,
        "unit02_native_surface_rows": builder.EXPECTED_UNIT02_NATIVE,
        "unit02_unit_admitted_phrase_rows": 23,
        "unit02_derived_unit_form_rows": 3,
        "cross_unit_exact_surface_overlap_count": builder.EXPECTED_CROSS_UNIT_SURFACE_OVERLAP,
        "cumulative_distinct_surface_rows": builder.EXPECTED_CUMULATIVE_DISTINCT_SURFACES,
        "cumulative_direct_or_instructional_surface_rows": builder.EXPECTED_CUMULATIVE_DIRECT_OR_INSTRUCTIONAL,
        "cumulative_receptive_only_surface_rows": builder.EXPECTED_CUMULATIVE_RECEPTIVE_ONLY,
        "referenced_global_canonical_parent_id_count": builder.EXPECTED_CANONICAL_PARENT_IDS,
    }
    for key, value in expected.items():
        require(counts.get(key) == value, f"COUNT_INVALID:{key}:{counts.get(key)}:{value}")

    reconciliation = report.get("surface_reconciliation", {})
    require(reconciliation.get("cross_unit_exact_surface_overlap") == [], "SURFACE_OVERLAP_NOT_EMPTY")
    require(reconciliation.get("unit01_receptive_only_surfaces") == ["ice cream"], "RECEPTIVE_ONLY_DRIFT")
    require(
        reconciliation.get("referenced_global_canonical_parent_ids")
        == ["EVP_CHUNK_000003", "EVP_CHUNK_000030", "EVP_CHUNK_000054", "EVP_CHUNK_000075"],
        "CANONICAL_PARENT_ID_DRIFT",
    )

    boundaries = report.get("claim_boundaries", {})
    require(boundaries.get("unit01_assets_auto_admitted_to_unit02") is False, "UNIT01_AUTO_ADMITTED")
    for key in (
        "global_chunk_authority_mutated",
        "unit01_assets_mutated",
        "unit02_native_assets_mutated",
        "questionbank_mutated",
        "runtime_connected",
        "canonical_scene_claimed",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")

    require(report.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_STEP_INVALID")
    return {"status": builder.PASS_STATUS, "validator_id": VALIDATOR_ID, "error_count": 0, "errors": []}
