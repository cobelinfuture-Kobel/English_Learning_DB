#!/usr/bin/env python3
"""Validate the deterministic Unit02 vocabulary-to-scene coverage matrix."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u02sc01_unit02_vocabulary_scene_coverage_matrix as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U02SC01_UNIT02_VOCABULARY_SCENE_COVERAGE_MATRIX_VALIDATOR"


class Unit02SceneCoverageValidationError(ValueError):
    """Fail-closed U02SC01 validation error."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Unit02SceneCoverageValidationError(code)


def validate_row(
    row: Mapping[str, Any],
    source: Mapping[str, Any],
) -> None:
    singular = str(row.get("singular") or "")
    require(singular == str(source["singular"]), f"SINGULAR_DRIFT:{singular}")
    require(row.get("plural") == source["plural"], f"PLURAL_DRIFT:{singular}")
    require(row.get("plural") == singular + "s", f"NON_PLAIN_S:{singular}")
    require(row.get("vocabulary_ids") == source["vocabulary_ids"], f"VOCAB_IDS_DRIFT:{singular}")

    primary = row.get("primary_scene_family")
    require(primary in builder.SCENE_FAMILIES, f"PRIMARY_FAMILY_INVALID:{singular}")
    secondary = row.get("secondary_scene_families")
    require(isinstance(secondary, list), f"SECONDARY_NOT_LIST:{singular}")
    require(len(secondary) == len(set(secondary)), f"SECONDARY_DUPLICATE:{singular}")
    require(primary not in secondary, f"SECONDARY_REPEATS_PRIMARY:{singular}")
    require(
        all(value in builder.SCENE_FAMILIES for value in secondary),
        f"SECONDARY_FAMILY_INVALID:{singular}",
    )

    eligibility = row.get("pattern_eligibility")
    require(isinstance(eligibility, dict), f"ELIGIBILITY_NOT_OBJECT:{singular}")
    require(
        tuple(eligibility) == builder.PATTERN_ELIGIBILITY_KEYS,
        f"ELIGIBILITY_KEYS_INVALID:{singular}",
    )
    require(
        all(isinstance(eligibility[key], bool) for key in builder.PATTERN_ELIGIBILITY_KEYS),
        f"ELIGIBILITY_VALUE_INVALID:{singular}",
    )

    gate = row.get("scene_gate")
    require(gate in builder.SCENE_GATES, f"SCENE_GATE_INVALID:{singular}")
    require(isinstance(row.get("child_suitable"), bool), f"CHILD_FLAG_INVALID:{singular}")
    require(
        isinstance(row.get("sense_check_required"), bool),
        f"SENSE_CHECK_FLAG_INVALID:{singular}",
    )
    require(isinstance(row.get("notes"), list), f"NOTES_INVALID:{singular}")

    expected_gate = builder.scene_gate(singular)
    require(gate == expected_gate, f"SCENE_GATE_DRIFT:{singular}")
    require(
        row["pattern_eligibility"] == builder.pattern_eligibility(singular),
        f"PATTERN_ELIGIBILITY_DRIFT:{singular}",
    )
    require(
        row["secondary_scene_families"]
        == builder.secondary_families(singular, str(primary)),
        f"SECONDARY_DRIFT:{singular}",
    )
    require(
        row["child_suitable"] == (singular not in builder.CHILD_UNSUITABLE_NOUNS),
        f"CHILD_FLAG_DRIFT:{singular}",
    )
    require(
        row["sense_check_required"]
        == (
            gate == "SENSE_CHECK_REQUIRED"
            or singular in builder.SENSE_CHECK_EXTRA_NOUNS
        ),
        f"SENSE_CHECK_FLAG_DRIFT:{singular}",
    )

    if singular in builder.GOVERNED_ADJECTIVE_CONTRAST_NOUNS:
        require(
            eligibility["governed_adjective_contrast"] is True,
            f"GOVERNED_ADJECTIVE_CONTRAST_MISSING:{singular}",
        )
    else:
        require(
            eligibility["governed_adjective_contrast"] is False,
            f"UNGOVERNED_ADJECTIVE_CONTRAST:{singular}",
        )

    if gate == "PEDAGOGICAL_DEFER":
        require(
            not any(
                eligibility[key]
                for key in (
                    "observation",
                    "possession",
                    "preference_positive",
                    "preference_negative",
                    "request",
                )
            ),
            f"DEFERRED_ROW_DIRECT_PATTERN_ENABLED:{singular}",
        )


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")
    require(payload.get("level_scope") == ["A1"], "LEVEL_SCOPE_INVALID")

    source_inventory = builder.u02qb02.load_inventory()
    source_rows = {
        str(row["singular"]): row for row in source_inventory["inventory"]
    }

    rows = payload.get("rows")
    require(isinstance(rows, list), "ROWS_NOT_LIST")
    require(len(rows) == builder.EXPECTED_NOUN_COUNT, "ROW_COUNT_INVALID")
    require(
        len({row["singular"] for row in rows}) == len(rows),
        "DUPLICATE_SINGULAR_ROW",
    )
    require(
        {row["singular"] for row in rows} == set(source_rows),
        "SOURCE_SINGULAR_COVERAGE_INVALID",
    )

    for row in rows:
        validate_row(row, source_rows[str(row["singular"])])

    primary_counts = Counter(str(row["primary_scene_family"]) for row in rows)
    require(
        dict(primary_counts) == builder.EXPECTED_FAMILY_COUNTS,
        "PRIMARY_FAMILY_COUNTS_INVALID",
    )

    counts = payload.get("coverage_denominators", {})
    require(
        counts.get("vocabulary_surface_count") == builder.EXPECTED_NOUN_COUNT,
        "VOCABULARY_SURFACE_COUNT_INVALID",
    )
    require(
        counts.get("exact_vocabulary_ref_count")
        == builder.EXPECTED_EXACT_VOCABULARY_REFS,
        "EXACT_VOCABULARY_REF_COUNT_INVALID",
    )
    require(
        counts.get("primary_scene_family_count") == len(builder.SCENE_FAMILIES),
        "SCENE_FAMILY_COUNT_INVALID",
    )
    require(
        counts.get("primary_scene_family_counts")
        == dict(sorted(builder.EXPECTED_FAMILY_COUNTS.items())),
        "SCENE_FAMILY_DENOMINATORS_INVALID",
    )

    gate_counts = Counter(str(row["scene_gate"]) for row in rows)
    require(
        counts.get("scene_gate_counts") == dict(sorted(gate_counts.items())),
        "SCENE_GATE_COUNTS_INVALID",
    )

    expected_eligibility_counts = {
        key: sum(bool(row["pattern_eligibility"][key]) for row in rows)
        for key in builder.PATTERN_ELIGIBILITY_KEYS
    }
    require(
        counts.get("pattern_eligibility_counts") == expected_eligibility_counts,
        "PATTERN_ELIGIBILITY_COUNTS_INVALID",
    )

    adjective_enabled = {
        str(row["singular"])
        for row in rows
        if row["pattern_eligibility"]["governed_adjective_contrast"]
    }
    require(
        adjective_enabled == set(builder.GOVERNED_ADJECTIVE_CONTRAST_NOUNS),
        "ADJECTIVE_CONTRAST_AUTHORITY_INVALID",
    )

    require(
        {
            str(row["singular"])
            for row in rows
            if row["scene_gate"] == "PEDAGOGICAL_DEFER"
        } == set(builder.PEDAGOGICAL_DEFER_NOUNS),
        "PEDAGOGICAL_DEFER_SET_INVALID",
    )
    require(
        {
            str(row["singular"])
            for row in rows
            if row["scene_gate"] == "SENSE_CHECK_REQUIRED"
        } == set(builder.SENSE_CHECK_NOUNS),
        "SENSE_CHECK_SET_INVALID",
    )
    require(
        {
            str(row["singular"])
            for row in rows
            if row["scene_gate"] == "SUPPORT_ONLY"
        } == set(builder.SUPPORT_ONLY_NOUNS),
        "SUPPORT_ONLY_SET_INVALID",
    )

    projection = payload.get("projection_contract", {})
    for key in (
        "scene_family_is_pedagogical_projection_not_canonical_scene_identity",
        "secondary_family_is_context_eligibility_not_duplicate_primary_assignment",
        "morphological_eligibility_does_not_imply_learner_scene_admission",
        "sense_check_rows_require_later_semantic_admission",
        "unit01_scene_identity_reuse_preferred_before_unit02_scene_creation",
        "unit02_new_scene_count_is_coverage_gap_driven_not_preallocated",
    ):
        require(projection.get(key) is True, f"PROJECTION_CONTRACT_INVALID:{key}")

    boundaries = payload.get("claim_boundaries", {})
    for key in (
        "canonical_scene_authority_mutated",
        "unit01_scene_authority_mutated",
        "vocabulary_authority_mutated",
        "chunk_authority_mutated",
        "questionbank_mutated",
        "learner_runtime_connected",
        "new_scene_created",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")

    require(
        payload.get("next_short_step") == builder.NEXT_SHORT_STEP,
        "NEXT_SHORT_STEP_INVALID",
    )

    return {
        "status": builder.PASS_STATUS,
        "error_count": 0,
        "errors": [],
        "vocabulary_surface_count": len(rows),
        "scene_family_count": len(primary_counts),
        "scene_gate_counts": dict(sorted(gate_counts.items())),
        "pattern_eligibility_counts": expected_eligibility_counts,
    }


def main() -> int:
    report = validate_payload(builder.payload())
    print(f"STATUS={report['status']}")
    print(f"VOCABULARY_SURFACES={report['vocabulary_surface_count']}")
    print(f"SCENE_FAMILIES={report['scene_family_count']}")
    print(f"SCENE_GATES={report['scene_gate_counts']}")
    print(f"PATTERN_ELIGIBILITY={report['pattern_eligibility_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
