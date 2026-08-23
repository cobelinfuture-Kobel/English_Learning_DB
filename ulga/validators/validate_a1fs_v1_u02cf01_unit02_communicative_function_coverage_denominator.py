#!/usr/bin/env python3
"""Validate the Unit02 communicative-function coverage denominator."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u02cf01_unit02_communicative_function_coverage_denominator
    as builder,
)

VALIDATION_PASS_STATUS = (
    "PASS_A1FS_V1_U02CF01_UNIT02_COMMUNICATIVE_FUNCTION_COVERAGE_VALIDATION"
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def validate_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if value.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("SCHEMA_VERSION_INVALID")
    if value.get("task_id") != builder.TASK_ID:
        errors.append("TASK_ID_INVALID")
    if value.get("status") != builder.PASS_STATUS:
        errors.append("STATUS_INVALID")
    if value.get("unit_id") != builder.UNIT_ID:
        errors.append("UNIT_ID_INVALID")

    source = value.get("source_authority", {})
    if source.get("global_communicative_function_authority_present") is not False:
        errors.append("GLOBAL_CF_AUTHORITY_BOUNDARY_INVALID")
    if source.get("unit02_q7_source_task_id") != builder.u02sc04.TASK_ID:
        errors.append("Q7_SOURCE_TASK_ID_INVALID")

    rows = value.get("communicative_function_denominator")
    if not isinstance(rows, list):
        errors.append("FUNCTION_DENOMINATOR_LIST_REQUIRED")
        rows = []
    by_family = {
        str(row.get("function_family")): row
        for row in rows
        if isinstance(row, Mapping) and row.get("function_family")
    }
    if tuple(row.get("function_family") for row in rows) != builder.FUNCTION_FAMILIES:
        errors.append("FUNCTION_FAMILY_ORDER_OR_IDENTITY_INVALID")
    if set(by_family) != set(builder.FUNCTION_FAMILIES):
        errors.append("FUNCTION_FAMILY_SET_INVALID")

    for family in builder.REUSE_FUNCTIONS:
        row = by_family.get(family, {})
        evidence = row.get("evidence", {})
        if row.get("coverage_role") != "REUSE":
            errors.append(f"REUSE_ROLE_INVALID:{family}")
        if row.get("coverage_status") != "COVERED_BY_EXISTING_UNIT01_SCENE_FUNCTION":
            errors.append(f"REUSE_COVERAGE_STATUS_INVALID:{family}")
        if evidence.get("source_function_id") != family:
            errors.append(f"REUSE_SOURCE_FUNCTION_INVALID:{family}")
        if evidence.get("covered_scene_count") != builder.EXPECTED_UNIT01_SCENE_COUNT:
            errors.append(f"REUSE_SCENE_COUNT_INVALID:{family}")
        refs = evidence.get("covered_scene_refs", [])
        if (
            not isinstance(refs, list)
            or len(refs) != builder.EXPECTED_UNIT01_SCENE_COUNT
            or len(refs) != len(set(refs))
        ):
            errors.append(f"REUSE_SCENE_REFS_INVALID:{family}")

    quantity = by_family.get(builder.ADDED_FUNCTION, {})
    q_evidence = quantity.get("evidence", {})
    if quantity.get("coverage_role") != "ADD":
        errors.append("QUANTITY_PLURALITY_ROLE_INVALID")
    if (
        quantity.get("coverage_status")
        != "COVERED_BY_UNIT02_APPROVED_GRAMMAR_AND_Q7_SUPPORT"
    ):
        errors.append("QUANTITY_PLURALITY_COVERAGE_STATUS_INVALID")
    if q_evidence.get("grammar_unit_id") != builder.UNIT_ID:
        errors.append("QUANTITY_PLURALITY_GRAMMAR_UNIT_INVALID")
    if q_evidence.get("approved_meaning_function") != builder.PLURAL_MEANING_FUNCTION:
        errors.append("QUANTITY_PLURALITY_MEANING_EVIDENCE_INVALID")
    if q_evidence.get("operator_approval_status") != "APPROVED_TEXT_MODE":
        errors.append("QUANTITY_PLURALITY_APPROVAL_INVALID")
    expected_q7 = {
        "q7_unit02_vocabulary_surface_count": builder.EXPECTED_UNIT02_VOCABULARY_COUNT,
        "q7_existing_scene_reuse_target_count": (
            builder.EXPECTED_Q7_EXISTING_SCENE_REUSE_TARGET_COUNT
        ),
        "q7_new_structural_scene_candidate_count": (
            builder.EXPECTED_Q7_STRUCTURAL_CANDIDATE_COUNT
        ),
        "q7_gated_non_scene_count": builder.EXPECTED_Q7_GATED_NON_SCENE_COUNT,
        "q7_remaining_direct_scene_gap_count": 0,
    }
    for field, expected in expected_q7.items():
        if q_evidence.get(field) != expected:
            errors.append(f"QUANTITY_PLURALITY_Q7_EVIDENCE_INVALID:{field}")
    if (
        q_evidence.get("all_new_structural_scene_candidates_support_plural_contrast")
        is not True
    ):
        errors.append("QUANTITY_PLURALITY_SCENE_SUPPORT_INVALID")

    counts = value.get("coverage_denominators", {})
    expected_counts = {
        "communicative_function_family_count": 3,
        "reuse_function_family_count": 2,
        "unit02_added_function_family_count": 1,
        "covered_function_family_count": 3,
        "missing_function_family_count": 0,
    }
    for field, expected in expected_counts.items():
        if counts.get(field) != expected:
            errors.append(f"COVERAGE_COUNT_INVALID:{field}")
    if counts.get("missing_function_families") != []:
        errors.append("MISSING_FUNCTION_FAMILIES_NOT_EMPTY")

    taxonomy = value.get("taxonomy_boundaries", {})
    if taxonomy.get("function_families") != list(builder.FUNCTION_FAMILIES):
        errors.append("TAXONOMY_FUNCTION_FAMILIES_INVALID")
    if taxonomy.get(
        "unit02sc01_pattern_affordances_not_promoted_to_cf_denominator"
    ) != list(builder.u02sc01.PATTERN_ELIGIBILITY_KEYS):
        errors.append("PATTERN_AFFORDANCE_BOUNDARY_INVALID")
    if taxonomy.get("global_canonical_cf_registry_created") is not False:
        errors.append("GLOBAL_CF_REGISTRY_FALSE_CLAIM")

    q8 = value.get("question8_communicative_function_coverage_contract", {})
    for field in (
        "identify_reused_from_unit01",
        "describe_reused_from_unit01",
        "quantity_plurality_added_for_unit02",
        "all_three_function_families_have_current_evidence",
        "remaining_function_gap_is_zero",
        "q8_communicative_function_denominator_resolved",
    ):
        if q8.get(field) is not True:
            errors.append(f"Q8_CONTRACT_INVALID:{field}")

    boundaries = value.get("claim_boundaries", {})
    if any(boundaries.get(field) is not False for field in (
        "canonical_graph_mutated",
        "global_communicative_function_authority_created",
        "unit01_scene_authority_mutated",
        "unit02_q7_authority_mutated",
        "unit02_vocabulary_authority_mutated",
        "learner_facing_content_created",
        "questionbank_mutated",
        "learner_runtime_connected",
        "a2_unlocked",
    )):
        errors.append("CLAIM_BOUNDARY_INVALID")

    next_scope = value.get("next_scope", {})
    if next_scope != {
        "coverage_denominator_number": 9,
        "coverage_denominator": "TASK_ANGLE_QUESTION_TYPE",
        "scope_status": builder.NEXT_SCOPE_STATUS,
    }:
        errors.append("NEXT_SCOPE_INVALID")
    if value.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("NEXT_SHORT_STEP_INVALID")

    report = {
        "status": VALIDATION_PASS_STATUS if not errors else "FAIL_A1FS_V1_U02CF01_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "function_family_count": len(rows),
        "covered_function_family_count": counts.get("covered_function_family_count"),
        "missing_function_family_count": counts.get("missing_function_family_count"),
        "payload_sha256": _digest(value),
    }
    report["report_sha256"] = _digest(report)
    return report


def main() -> int:
    value = builder.payload()
    report = validate_payload(value)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
