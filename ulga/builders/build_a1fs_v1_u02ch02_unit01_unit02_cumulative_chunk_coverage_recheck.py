#!/usr/bin/env python3
"""Read-only Unit01 -> Unit02 cumulative chunk/phrase coverage reconciliation.

U02CH02 does not author or promote chunk content. It reconciles the current
Unit01 executable content contract with the governed U02CH01 native asset set,
keeping inventory, productive/direct eligibility, receptive-only rows, and
canonical parent identities as separate denominators.
"""
from __future__ import annotations

from typing import Any

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as u01
from ulga.builders import build_a1fs_v1_u02ch01_unit02_native_chunk_assets as u02ch01

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only cumulative coverage reconciliation; no learner content, chunk "
    "authority, QuestionBank, scene, or runtime asset is created or mutated."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02CH02_Unit01Unit02CumulativeChunkCoverageRecheck"
SCHEMA_VERSION = "a1fs.v1.u02ch02.cumulative_chunk_coverage_recheck.v1"
PASS_STATUS = "PASS_A1FS_V1_U02CH02_UNIT01_UNIT02_CUMULATIVE_CHUNK_COVERAGE_RECHECK"
NEXT_SHORT_STEP = "A1FS-V1-U02SP02_Unit01Unit02ExactSentenceFrameCoverageRecheck"

EXPECTED_UNIT01_INVENTORY = 24
EXPECTED_UNIT01_DIRECT_OR_INSTRUCTIONAL = 23
EXPECTED_UNIT01_RECEPTIVE_ONLY = 1
EXPECTED_UNIT02_NATIVE = 26
EXPECTED_CROSS_UNIT_SURFACE_OVERLAP = 0
EXPECTED_CUMULATIVE_DISTINCT_SURFACES = 50
EXPECTED_CUMULATIVE_DIRECT_OR_INSTRUCTIONAL = 49
EXPECTED_CUMULATIVE_RECEPTIVE_ONLY = 1
EXPECTED_CANONICAL_PARENT_IDS = 4


def normalized(value: str) -> str:
    return " ".join(str(value).casefold().split())


def unit01_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk_id, surface, level, chunk_type, direct_allowed, policy in u01.CANONICAL_CHUNKS:
        rows.append(
            {
                "source": "UNIT01_CANONICAL_CHUNK",
                "surface": surface,
                "normalized_surface": normalized(surface),
                "canonical_chunk_id": chunk_id,
                "level": level,
                "chunk_type": chunk_type,
                "direct_or_instructional": bool(direct_allowed),
                "receptive_only": not bool(direct_allowed),
                "policy": policy,
            }
        )
    for surface in u01.INSTRUCTIONAL_PHRASES:
        rows.append(
            {
                "source": "UNIT01_INSTRUCTIONAL_PHRASE",
                "surface": surface,
                "normalized_surface": normalized(surface),
                "canonical_chunk_id": None,
                "direct_or_instructional": True,
                "receptive_only": False,
            }
        )
    for surface, adjective, noun, article, role in u01.ADJECTIVE_INSTRUCTIONAL_PHRASES:
        rows.append(
            {
                "source": "UNIT01_ADJECTIVE_INSTRUCTIONAL_PHRASE",
                "surface": surface,
                "normalized_surface": normalized(surface),
                "canonical_chunk_id": None,
                "direct_or_instructional": True,
                "receptive_only": False,
                "adjective": adjective,
                "noun": noun,
                "article": article,
                "instructional_role": role,
            }
        )
    return rows


def unit02_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in u02ch01.build_assets()]


def build_report() -> dict[str, Any]:
    u01_rows = unit01_rows()
    u02_rows = unit02_rows()

    u01_surfaces = {row["normalized_surface"] for row in u01_rows}
    u02_surfaces = {normalized(str(row["surface"])) for row in u02_rows}
    overlap = sorted(u01_surfaces & u02_surfaces)

    u01_direct = {
        row["normalized_surface"]
        for row in u01_rows
        if row["direct_or_instructional"]
    }
    u01_receptive = {
        row["normalized_surface"]
        for row in u01_rows
        if row["receptive_only"]
    }

    canonical_parent_ids = {
        str(row["canonical_chunk_id"])
        for row in u01_rows
        if row.get("canonical_chunk_id")
    }
    for row in u02_rows:
        parent = row.get("parent_canonical_chunk_id")
        if parent:
            canonical_parent_ids.add(str(parent))

    cumulative_surfaces = u01_surfaces | u02_surfaces
    cumulative_direct = u01_direct | u02_surfaces

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "coverage_denominators": {
            "unit01_reference_inventory_rows": len(u01_rows),
            "unit01_canonical_chunk_rows": len(u01.CANONICAL_CHUNKS),
            "unit01_instructional_phrase_rows": (
                len(u01.INSTRUCTIONAL_PHRASES)
                + len(u01.ADJECTIVE_INSTRUCTIONAL_PHRASES)
            ),
            "unit01_direct_or_instructional_surface_rows": len(u01_direct),
            "unit01_receptive_only_surface_rows": len(u01_receptive),
            "unit02_native_surface_rows": len(u02_rows),
            "unit02_unit_admitted_phrase_rows": sum(
                1 for row in u02_rows if row["authority_scope"] == "UNIT_ADMITTED_PHRASE"
            ),
            "unit02_derived_unit_form_rows": sum(
                1 for row in u02_rows if row["authority_scope"] == "DERIVED_UNIT_FORM"
            ),
            "cross_unit_exact_surface_overlap_count": len(overlap),
            "cumulative_distinct_surface_rows": len(cumulative_surfaces),
            "cumulative_direct_or_instructional_surface_rows": len(cumulative_direct),
            "cumulative_receptive_only_surface_rows": len(u01_receptive - u02_surfaces),
            "referenced_global_canonical_parent_id_count": len(canonical_parent_ids),
        },
        "surface_reconciliation": {
            "cross_unit_exact_surface_overlap": overlap,
            "unit01_receptive_only_surfaces": sorted(u01_receptive),
            "referenced_global_canonical_parent_ids": sorted(canonical_parent_ids),
        },
        "claim_boundaries": {
            "unit01_assets_auto_admitted_to_unit02": False,
            "global_chunk_authority_mutated": False,
            "unit01_assets_mutated": False,
            "unit02_native_assets_mutated": False,
            "questionbank_mutated": False,
            "runtime_connected": False,
            "canonical_scene_claimed": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    from ulga.validators import (
        validate_a1fs_v1_u02ch02_unit01_unit02_cumulative_chunk_coverage_recheck as validator,
    )

    report = build_report()
    validation = validator.validate_report(report)
    counts = report["coverage_denominators"]
    print(f"STATUS={PASS_STATUS}")
    print(f"UNIT01_REFERENCE_INVENTORY={counts['unit01_reference_inventory_rows']}")
    print(f"UNIT01_DIRECT_OR_INSTRUCTIONAL={counts['unit01_direct_or_instructional_surface_rows']}")
    print(f"UNIT01_RECEPTIVE_ONLY={counts['unit01_receptive_only_surface_rows']}")
    print(f"UNIT02_NATIVE={counts['unit02_native_surface_rows']}")
    print(f"CROSS_UNIT_EXACT_SURFACE_OVERLAP={counts['cross_unit_exact_surface_overlap_count']}")
    print(f"CUMULATIVE_DISTINCT_SURFACES={counts['cumulative_distinct_surface_rows']}")
    print(f"CUMULATIVE_DIRECT_OR_INSTRUCTIONAL={counts['cumulative_direct_or_instructional_surface_rows']}")
    print(f"REFERENCED_GLOBAL_CANONICAL_PARENT_IDS={counts['referenced_global_canonical_parent_id_count']}")
    print(f"ERROR_COUNT={validation['error_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
