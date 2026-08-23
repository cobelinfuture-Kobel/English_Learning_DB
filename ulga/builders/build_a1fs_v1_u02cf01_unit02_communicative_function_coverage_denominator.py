#!/usr/bin/env python3
"""Build the Unit02 communicative-function coverage denominator.

U02CF01 is a bounded read-only coverage projection. It does not create a
global communicative-function authority. The operator-approved Unit02
cumulative-content contract is:
- identify / describe: reuse existing Unit01 scene functions;
- quantity / plurality: add from the approved Unit02 regular-plural meaning.

The projection binds those three function families to current GitHub evidence
and intentionally does not promote broader U02SC01 pattern affordances into
communicative-function authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from ulga.builders import build_a1_a1plus_cross_skill_learning_units as learning_units
from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as u01qb06
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u01qb07
from ulga.builders import (
    build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix
    as u01_scene_resolver,
)
from ulga.builders import (
    build_a1fs_v1_u02sc01_unit02_vocabulary_scene_coverage_matrix as u02sc01,
)
from ulga.builders import (
    build_a1fs_v1_u02sc02_unit01_canonical_scene_to_unit02_applicability_projection
    as u02sc02,
)
from ulga.builders import (
    build_a1fs_v1_u02sc04_unit02_admitted_scene_candidate_materialization_and_coverage_recheck
    as u02sc04,
)
from ulga.query import a1_a1plus_authority_scope_query as authority_query

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only Unit02 communicative-function coverage denominator over existing approved learning-unit, Unit01 scene, and U02 Q7 evidence; no canonical function registry, learner-facing content, QuestionBank item, or graph node is created."

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02CF01_Unit02CommunicativeFunctionCoverageDenominator"
SCHEMA_VERSION = "a1fs.v1.u02cf01.unit02_communicative_function_coverage_denominator.v1"
PASS_STATUS = "PASS_A1FS_V1_U02CF01_UNIT02_COMMUNICATIVE_FUNCTION_COVERAGE_DENOMINATOR"
UNIT_ID = u02sc04.UNIT_ID
LEVEL_SCOPE = ["A1"]

OPERATOR_SCOPE_CONTRACT = (
    "UNIT02_CUMULATIVE_CF_IDENTIFY_DESCRIBE_REUSE_QUANTITY_PLURALITY_ADD"
)
FUNCTION_FAMILIES = ("IDENTIFY", "DESCRIBE", "QUANTITY_PLURALITY")
REUSE_FUNCTIONS = ("IDENTIFY", "DESCRIBE")
ADDED_FUNCTION = "QUANTITY_PLURALITY"
PLURAL_MEANING_FUNCTION = (
    "refer to more than one countable person, animal, place, or thing"
)

EXPECTED_UNIT01_SCENE_COUNT = 32
EXPECTED_UNIT02_VOCABULARY_COUNT = 162
EXPECTED_Q7_EXISTING_SCENE_REUSE_TARGET_COUNT = 26
EXPECTED_Q7_STRUCTURAL_CANDIDATE_COUNT = 109
EXPECTED_Q7_GATED_NON_SCENE_COUNT = 27

NEXT_SHORT_STEP = "A1FS-V1-U02TA01_Unit02TaskAngleQuestionTypeCoverageDenominator"
NEXT_SCOPE_STATUS = "OUTSIDE_APPROVED_Q8_SCOPE"


class Unit02CommunicativeFunctionCoverageError(ValueError):
    """Fail-closed U02CF01 construction error."""


def _unit01_scene_function_index() -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}

    for context in u01_scene_resolver.s01.CONTEXTS:
        scene = u01qb06.canonical_context_scene_row(context)
        ref = str(scene["scene_ref_id"])
        functions = {
            str(value)
            for value in scene["semantic_scene_core"]["communicative_function_ids"]
        }
        result[ref] = functions

    supplement = u01_scene_resolver._read_supplement()
    for candidate in u01qb07.candidates(supplement):
        ref = str(candidate["candidate_id"])
        functions = {str(value) for value in candidate["communicative_function_ids"]}
        if ref in result:
            raise Unit02CommunicativeFunctionCoverageError(
                f"DUPLICATE_UNIT01_SCENE_REF:{ref}"
            )
        result[ref] = functions

    current_scene_refs = {
        str(row["scene_ref_id"]) for row in u02sc02.canonical_scene_rows()
    }
    if set(result) != current_scene_refs:
        missing = sorted(current_scene_refs - set(result))
        extra = sorted(set(result) - current_scene_refs)
        raise Unit02CommunicativeFunctionCoverageError(
            f"UNIT01_SCENE_FUNCTION_IDENTITY_DRIFT:missing={missing}:extra={extra}"
        )
    if len(result) != EXPECTED_UNIT01_SCENE_COUNT:
        raise Unit02CommunicativeFunctionCoverageError(
            f"UNIT01_SCENE_COUNT_DRIFT:{len(result)}"
        )
    return result


def _reuse_function_evidence(function_family: str) -> dict[str, Any]:
    if function_family not in REUSE_FUNCTIONS:
        raise Unit02CommunicativeFunctionCoverageError(
            f"UNKNOWN_REUSE_FUNCTION:{function_family}"
        )
    index = _unit01_scene_function_index()
    refs = sorted(ref for ref, functions in index.items() if function_family in functions)
    if len(refs) != EXPECTED_UNIT01_SCENE_COUNT:
        raise Unit02CommunicativeFunctionCoverageError(
            f"UNIT01_REUSE_FUNCTION_COVERAGE_DRIFT:{function_family}:{len(refs)}"
        )
    return {
        "source_layer": "UNIT01_CUMULATIVE_SCENE_WORLD",
        "source_function_id": function_family,
        "covered_scene_count": len(refs),
        "covered_scene_refs": refs,
        "current_cumulative_scene_world_count": EXPECTED_UNIT01_SCENE_COUNT,
        "reuse_without_new_function_authoring": True,
    }


def _approved_plural_learning_unit() -> dict[str, Any]:
    artifact = learning_units.build_artifact()
    rows = [
        row
        for row in artifact.get("learning_units", [])
        if row.get("grammar_unit_id") == UNIT_ID
    ]
    if len(rows) != 1:
        raise Unit02CommunicativeFunctionCoverageError(
            f"UNIT02_LEARNING_UNIT_IDENTITY_INVALID:{len(rows)}"
        )
    unit = deepcopy(rows[0])
    approval = unit.get("source_evidence", {}).get("operator_approval_status")
    if approval != "APPROVED_TEXT_MODE":
        raise Unit02CommunicativeFunctionCoverageError(
            f"UNIT02_LEARNING_UNIT_NOT_OPERATOR_APPROVED:{approval}"
        )
    meanings = list(unit.get("learning_content", {}).get("meaning_functions", []))
    if PLURAL_MEANING_FUNCTION not in meanings:
        raise Unit02CommunicativeFunctionCoverageError(
            "UNIT02_PLURAL_MEANING_FUNCTION_MISSING"
        )
    return unit


def _quantity_plurality_evidence() -> dict[str, Any]:
    unit = _approved_plural_learning_unit()
    q7 = u02sc04.build_payload()
    counts = q7["coverage_denominators"]
    materialized = q7["materialized_scene_candidates"]

    expected_counts = {
        "unit02_vocabulary_surface_count": EXPECTED_UNIT02_VOCABULARY_COUNT,
        "direct_eligible_covered_by_existing_scene_count": (
            EXPECTED_Q7_EXISTING_SCENE_REUSE_TARGET_COUNT
        ),
        "direct_eligible_covered_by_admitted_candidate_count": (
            EXPECTED_Q7_STRUCTURAL_CANDIDATE_COUNT
        ),
        "gated_non_scene_gap_count": EXPECTED_Q7_GATED_NON_SCENE_COUNT,
        "candidate_adjusted_remaining_direct_scene_gap_count": 0,
    }
    for field, expected in expected_counts.items():
        if counts.get(field) != expected:
            raise Unit02CommunicativeFunctionCoverageError(
                f"Q7_COUNT_DRIFT:{field}:{counts.get(field)}:{expected}"
            )

    if len(materialized) != EXPECTED_Q7_STRUCTURAL_CANDIDATE_COUNT:
        raise Unit02CommunicativeFunctionCoverageError(
            f"Q7_MATERIALIZED_COUNT_DRIFT:{len(materialized)}"
        )
    if not all(
        row.get("scene_semantic_core", {}).get("plural_contrast_supported") is True
        for row in materialized
    ):
        raise Unit02CommunicativeFunctionCoverageError(
            "Q7_PLURAL_CONTRAST_SUPPORT_INCOMPLETE"
        )

    return {
        "source_layer": "UNIT02_APPROVED_GRAMMAR_PLUS_Q7_STRUCTURAL_SCENE_SUPPORT",
        "grammar_unit_id": UNIT_ID,
        "approved_meaning_function": PLURAL_MEANING_FUNCTION,
        "operator_approval_status": unit["source_evidence"]["operator_approval_status"],
        "q7_unit02_vocabulary_surface_count": counts["unit02_vocabulary_surface_count"],
        "q7_existing_scene_reuse_target_count": (
            counts["direct_eligible_covered_by_existing_scene_count"]
        ),
        "q7_new_structural_scene_candidate_count": (
            counts["direct_eligible_covered_by_admitted_candidate_count"]
        ),
        "q7_gated_non_scene_count": counts["gated_non_scene_gap_count"],
        "q7_remaining_direct_scene_gap_count": (
            counts["candidate_adjusted_remaining_direct_scene_gap_count"]
        ),
        "all_new_structural_scene_candidates_support_plural_contrast": True,
        "structural_scene_support_is_not_learner_facing_scene_authority": True,
    }


def function_rows() -> list[dict[str, Any]]:
    rows = [
        {
            "function_family": "IDENTIFY",
            "coverage_role": "REUSE",
            "coverage_status": "COVERED_BY_EXISTING_UNIT01_SCENE_FUNCTION",
            "evidence": _reuse_function_evidence("IDENTIFY"),
        },
        {
            "function_family": "DESCRIBE",
            "coverage_role": "REUSE",
            "coverage_status": "COVERED_BY_EXISTING_UNIT01_SCENE_FUNCTION",
            "evidence": _reuse_function_evidence("DESCRIBE"),
        },
        {
            "function_family": ADDED_FUNCTION,
            "coverage_role": "ADD",
            "coverage_status": "COVERED_BY_UNIT02_APPROVED_GRAMMAR_AND_Q7_SUPPORT",
            "evidence": _quantity_plurality_evidence(),
        },
    ]
    if tuple(row["function_family"] for row in rows) != FUNCTION_FAMILIES:
        raise Unit02CommunicativeFunctionCoverageError(
            "COMMUNICATIVE_FUNCTION_DENOMINATOR_IDENTITY_DRIFT"
        )
    return rows


def payload() -> dict[str, Any]:
    if "communicative_function" in authority_query.AUTHORITIES:
        raise Unit02CommunicativeFunctionCoverageError(
            "GLOBAL_COMMUNICATIVE_FUNCTION_AUTHORITY_NOW_EXISTS_RECONCILIATION_REQUIRED"
        )

    rows = function_rows()
    covered = [row for row in rows if row["coverage_status"].startswith("COVERED_BY_")]
    missing = [row for row in rows if not row["coverage_status"].startswith("COVERED_BY_")]
    if len(covered) != len(rows) or missing:
        raise Unit02CommunicativeFunctionCoverageError(
            "UNIT02_COMMUNICATIVE_FUNCTION_COVERAGE_NOT_CLOSED"
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "level_scope": LEVEL_SCOPE,
        "artifact_semantics": (
            "UNIT02_SCOPED_COMMUNICATIVE_FUNCTION_COVERAGE_DENOMINATOR_"
            "NOT_GLOBAL_CANONICAL_FUNCTION_AUTHORITY"
        ),
        "operator_scope_contract": OPERATOR_SCOPE_CONTRACT,
        "source_authority": {
            "global_authority_query_task_id": authority_query.TASK_ID,
            "global_authority_types": list(authority_query.AUTHORITIES),
            "global_communicative_function_authority_present": False,
            "unit01_scene_source_task_id": u01qb07.TASK_ID,
            "unit02_learning_unit_source_task_id": learning_units.TASK_ID,
            "unit02_q7_source_task_id": u02sc04.TASK_ID,
        },
        "communicative_function_denominator": rows,
        "coverage_denominators": {
            "communicative_function_family_count": len(rows),
            "reuse_function_family_count": sum(
                row["coverage_role"] == "REUSE" for row in rows
            ),
            "unit02_added_function_family_count": sum(
                row["coverage_role"] == "ADD" for row in rows
            ),
            "covered_function_family_count": len(covered),
            "missing_function_family_count": len(missing),
            "missing_function_families": [
                row["function_family"] for row in missing
            ],
        },
        "taxonomy_boundaries": {
            "function_families": list(FUNCTION_FAMILIES),
            "unit02sc01_pattern_affordances_not_promoted_to_cf_denominator": list(
                u02sc01.PATTERN_ELIGIBILITY_KEYS
            ),
            "u02sc04_observation_identification_tags_are_structural_support_not_new_global_cf_ids": True,
            "grammar_meaning_function_is_evidence_for_quantity_plurality_not_a_global_registry": True,
            "global_canonical_cf_registry_created": False,
        },
        "question8_communicative_function_coverage_contract": {
            "identify_reused_from_unit01": True,
            "describe_reused_from_unit01": True,
            "quantity_plurality_added_for_unit02": True,
            "all_three_function_families_have_current_evidence": True,
            "remaining_function_gap_is_zero": True,
            "q8_communicative_function_denominator_resolved": True,
        },
        "claim_boundaries": {
            "canonical_graph_mutated": False,
            "global_communicative_function_authority_created": False,
            "unit01_scene_authority_mutated": False,
            "unit02_q7_authority_mutated": False,
            "unit02_vocabulary_authority_mutated": False,
            "learner_facing_content_created": False,
            "questionbank_mutated": False,
            "learner_runtime_connected": False,
            "a2_unlocked": False,
        },
        "next_scope": {
            "coverage_denominator_number": 9,
            "coverage_denominator": "TASK_ANGLE_QUESTION_TYPE",
            "scope_status": NEXT_SCOPE_STATUS,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    value = payload()
    counts = value["coverage_denominators"]
    print(f"STATUS={PASS_STATUS}")
    print(
        "COMMUNICATIVE_FUNCTION_FAMILIES="
        f"{counts['communicative_function_family_count']}"
    )
    print(f"REUSE_FUNCTION_FAMILIES={counts['reuse_function_family_count']}")
    print(
        "UNIT02_ADDED_FUNCTION_FAMILIES="
        f"{counts['unit02_added_function_family_count']}"
    )
    print(f"COVERED_FUNCTION_FAMILIES={counts['covered_function_family_count']}")
    print(f"MISSING_FUNCTION_FAMILIES={counts['missing_function_family_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
