#!/usr/bin/env python3
"""Build the Unit02 task-angle / question-type coverage denominator.

U02TA01 is a read-only coverage audit. It binds the operator-approved Unit02
task/activity model to current Unit01 task-angle evidence and current Unit02
text-mode PracticeItem question types. It does not author QuestionBank items,
change runtime allocation, or claim distinct-item capacity.

The target model has two layers:
- pedagogical roles: REVIEW, NEW, INTEGRATION, VARIATION, TRANSFER;
- ten task/question families used as the Unit02 coverage denominator.

Coverage may be FULL, PARTIAL, or GAP. A PASS status means the denominator and
current gaps are deterministically resolved, not that all ten families are
already materialized in the canonical QuestionBank.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from functools import lru_cache
from typing import Any, Mapping

from ulga.builders import (
    build_a1_grammar_text_mode_practice_item_fullfix as practice_source,
)
from ulga.builders import (
    build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09,
)
from ulga.builders import (
    build_a1fs_v1_u02cf01_unit02_communicative_function_coverage_denominator as u02cf01,
)
from ulga.query import a1_a1plus_authority_scope_query as authority_query

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only Unit02 task-angle/question-type coverage audit over existing Unit01 task-angle, Unit02 text-mode PracticeItem, Q8 communicative-function, and global question-type authority evidence; no QuestionBank item, learner content, runtime allocation, canonical graph node, learner state, or A2 content is created or mutated."

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U02TA01_Unit02TaskAngleQuestionTypeCoverageDenominator"
SCHEMA_VERSION = "a1fs.v1.u02ta01.unit02_task_angle_question_type_coverage_denominator.v1"
PASS_STATUS = "PASS_A1FS_V1_U02TA01_UNIT02_TASK_ANGLE_QUESTION_TYPE_COVERAGE_DENOMINATOR"
UNIT_ID = "GRAMMAR_REGULAR_PLURAL_NOUNS"
LEVEL_SCOPE = ["A1"]

TASK_ROLES = ("REVIEW", "NEW", "INTEGRATION", "VARIATION", "TRANSFER")
TASK_FAMILIES = (
    "RECOGNITION",
    "MEANING_DISCRIMINATION",
    "FORM_SELECTION",
    "MORPHOLOGY_CONSTRUCTION",
    "ERROR_DETECTION",
    "ERROR_CORRECTION",
    "CONTEXT_GAP",
    "U01_U02_INTEGRATION",
    "PRODUCTIVE_RESPONSE",
    "TRANSFER",
)

EXPECTED_UNIT02_ITEM_COUNT = 8
EXPECTED_UNIT02_TASK_TYPES = (
    "context_choice",
    "form_choice",
    "guided_contextual_writing",
    "structured_gap_fill",
    "structured_morphology_build",
    "text_mode_writing_checkpoint",
)
EXPECTED_UNIT02_RESPONSE_MODES = (
    "ordered_morphemes",
    "select_one",
    "short_text",
)

NEXT_SHORT_STEP = "A1FS-V1-U02QBC01_Unit02QuestionBankDistinctCapacityDenominator"
NEXT_SCOPE_STATUS = "OUTSIDE_APPROVED_Q9_SCOPE"


class Unit02TaskAngleCoverageError(ValueError):
    """Fail-closed Unit02 task-angle / question-type audit error."""


@lru_cache(maxsize=1)
def _practice_artifact() -> dict[str, Any]:
    artifact, report = practice_source.build_and_validate_from_repo()
    if report.get("validation_status") != "PASS":
        raise Unit02TaskAngleCoverageError(
            f"UNIT02_PRACTICE_SOURCE_NOT_VALID:{report.get('validation_status')}"
        )
    return artifact


def unit02_items() -> list[dict[str, Any]]:
    artifact = _practice_artifact()
    rows = [
        deepcopy(item)
        for item in artifact.get("item_bank", [])
        if item.get("content_binding", {}).get("grammar_focus") == [UNIT_ID]
    ]
    rows.sort(key=lambda row: str(row.get("item_id")))
    if len(rows) != EXPECTED_UNIT02_ITEM_COUNT:
        raise Unit02TaskAngleCoverageError(
            f"UNIT02_ITEM_COUNT_DRIFT:{len(rows)}:{EXPECTED_UNIT02_ITEM_COUNT}"
        )
    task_types = tuple(sorted({str(row.get("task_type")) for row in rows}))
    if task_types != EXPECTED_UNIT02_TASK_TYPES:
        raise Unit02TaskAngleCoverageError(
            f"UNIT02_TASK_TYPE_DRIFT:{task_types}"
        )
    response_modes = tuple(sorted({str(row.get("response_mode")) for row in rows}))
    if response_modes != EXPECTED_UNIT02_RESPONSE_MODES:
        raise Unit02TaskAngleCoverageError(
            f"UNIT02_RESPONSE_MODE_DRIFT:{response_modes}"
        )
    if any(
        len(item.get("content_binding", {}).get("grammar_focus", [])) != 1
        for item in rows
    ):
        raise Unit02TaskAngleCoverageError("UNIT02_CURRENT_ITEMS_NOT_SINGLE_GRAMMAR_FOCUS")
    return rows


@lru_cache(maxsize=1)
def _global_question_type_task_values() -> set[str]:
    scope = authority_query.build_scope("A1")
    rows = scope.get("authorities", {}).get("question_type", [])
    values = {
        str(row.get("question_type"))
        for row in rows
        if row.get("source_field") == "task_type"
    }
    if not values:
        raise Unit02TaskAngleCoverageError("GLOBAL_QUESTION_TYPE_TASK_VALUES_EMPTY")
    return values


@lru_cache(maxsize=1)
def current_question_type_evidence() -> dict[str, Any]:
    rows = unit02_items()
    task_types = sorted({str(row["task_type"]) for row in rows})
    authority_values = _global_question_type_task_values()
    missing_from_global = sorted(set(task_types) - authority_values)
    if missing_from_global:
        raise Unit02TaskAngleCoverageError(
            f"UNIT02_TASK_TYPES_MISSING_FROM_GLOBAL_QUESTION_TYPE_AUTHORITY:{missing_from_global}"
        )
    return {
        "source_task_id": practice_source.TASK_ID,
        "global_question_type_authority_task_id": authority_query.TASK_ID,
        "unit02_item_count": len(rows),
        "unique_task_type_count": len(task_types),
        "task_types": task_types,
        "response_modes": sorted({str(row["response_mode"]) for row in rows}),
        "evidence_dimensions": sorted(
            {str(row["evidence_dimension"]) for row in rows}
        ),
        "item_roles": sorted({str(row["item_role"]) for row in rows}),
        "all_unit02_task_types_present_in_global_question_type_authority": True,
        "all_current_unit02_items_single_grammar_focus": True,
    }


def _items_matching(
    rows: list[dict[str, Any]],
    *,
    task_types: set[str] | None = None,
    dimensions: set[str] | None = None,
    roles: set[str] | None = None,
) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        if task_types is not None and str(row.get("task_type")) not in task_types:
            continue
        if dimensions is not None and str(row.get("evidence_dimension")) not in dimensions:
            continue
        if roles is not None and str(row.get("item_role")) not in roles:
            continue
        result.append(row)
    return result


def _evidence_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "item_count": len(rows),
        "item_ids": [str(row["item_id"]) for row in rows],
        "task_types": sorted({str(row["task_type"]) for row in rows}),
        "evidence_dimensions": sorted(
            {str(row["evidence_dimension"]) for row in rows}
        ),
        "response_modes": sorted({str(row["response_mode"]) for row in rows}),
    }


def task_family_rows() -> list[dict[str, Any]]:
    rows = unit02_items()

    recognition = _items_matching(rows, dimensions={"recognition"})
    meaning = _items_matching(rows, dimensions={"meaning"})
    form_selection = _items_matching(
        rows, task_types={"form_choice"}, dimensions={"recognition", "contrast"}
    )
    morphology = _items_matching(rows, task_types={"structured_morphology_build"})
    error_detection = [
        row
        for row in rows
        if row.get("evidence_dimension") == "contrast"
        and isinstance(row.get("distractor_error_tags"), Mapping)
        and row.get("distractor_error_tags")
    ]
    structured_gap = _items_matching(rows, task_types={"structured_gap_fill"})
    productive = _items_matching(
        rows,
        task_types={"guided_contextual_writing", "text_mode_writing_checkpoint"},
    )
    assessments = _items_matching(rows, roles={"assessment"})
    integration = [
        row
        for row in rows
        if len(row.get("content_binding", {}).get("grammar_focus", [])) > 1
        or "GRAMMAR_ARTICLES_BASIC"
        in row.get("content_binding", {}).get("grammar_focus", [])
    ]

    family_rows = [
        {
            "task_family": "RECOGNITION",
            "coverage_status": "FULL",
            "current_support": _evidence_summary(recognition),
            "coverage_reason": "Current Unit02 recognition item uses form_choice/select_one.",
        },
        {
            "task_family": "MEANING_DISCRIMINATION",
            "coverage_status": "FULL",
            "current_support": _evidence_summary(meaning),
            "coverage_reason": "Current Unit02 meaning item uses a context_choice.",
        },
        {
            "task_family": "FORM_SELECTION",
            "coverage_status": "FULL",
            "current_support": _evidence_summary(form_selection),
            "coverage_reason": "Current Unit02 form_choice items require target-form selection.",
        },
        {
            "task_family": "MORPHOLOGY_CONSTRUCTION",
            "coverage_status": "FULL",
            "current_support": _evidence_summary(morphology),
            "coverage_reason": "Regular-plural Unit02 P05 resolves to structured_morphology_build.",
        },
        {
            "task_family": "ERROR_DETECTION",
            "coverage_status": "PARTIAL",
            "current_support": _evidence_summary(error_detection),
            "coverage_reason": "Contrast choices carry distractor_error_tags, but no explicit find-the-error response is required.",
            "gap": "EXPLICIT_ERROR_DETECTION_RESPONSE_NOT_MATERIALIZED",
        },
        {
            "task_family": "ERROR_CORRECTION",
            "coverage_status": "GAP",
            "current_support": _evidence_summary([]),
            "coverage_reason": "Current Unit02 fixed items do not ask the learner to correct an erroneous plural form.",
            "gap": "ERROR_CORRECTION_TASK_TYPE_MISSING",
        },
        {
            "task_family": "CONTEXT_GAP",
            "coverage_status": "PARTIAL",
            "current_support": _evidence_summary(structured_gap),
            "coverage_reason": "A structured gap exists, but the regular-plural cue is source-form morphology rather than a scene/context gap.",
            "gap": "SCENE_BOUND_CONTEXT_GAP_NOT_MATERIALIZED",
        },
        {
            "task_family": "U01_U02_INTEGRATION",
            "coverage_status": "GAP",
            "current_support": _evidence_summary(integration),
            "coverage_reason": "All current Unit02 text-mode items have a single grammar focus, so Articles + Plurals are not jointly measured.",
            "gap": "CROSS_UNIT_GRAMMAR_INTEGRATION_TASK_MISSING",
        },
        {
            "task_family": "PRODUCTIVE_RESPONSE",
            "coverage_status": "FULL",
            "current_support": _evidence_summary(productive),
            "coverage_reason": "Current Unit02 includes guided contextual writing and a productive checkpoint.",
        },
        {
            "task_family": "TRANSFER",
            "coverage_status": "PARTIAL",
            "current_support": _evidence_summary(assessments),
            "coverage_reason": "Assessment items provide contextual checkpoints, but no explicit cumulative unseen-scene U01+U02 transfer binding exists.",
            "gap": "EXPLICIT_CUMULATIVE_TRANSFER_BINDING_NOT_MATERIALIZED",
        },
    ]
    if tuple(row["task_family"] for row in family_rows) != TASK_FAMILIES:
        raise Unit02TaskAngleCoverageError("TASK_FAMILY_DENOMINATOR_IDENTITY_DRIFT")
    return family_rows


def task_role_rows(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_family = {row["task_family"]: row for row in families}
    reusable_u01_angles = sorted(
        {
            angle
            for angle in u01qb09.TASK_ANGLES
            if angle
            in {
                "PHRASE_CONSTRUCTION",
                "WORD_ORDER",
                "ERROR_CHECK",
                "COMPLETE_SENTENCE_PRODUCTION",
                "CONNECTED_SENTENCE_PRODUCTION",
                "SCENE_DESCRIPTION",
                "TRANSFER_DECISION",
            }
        }
    )
    if not reusable_u01_angles:
        raise Unit02TaskAngleCoverageError("UNIT01_REUSABLE_TASK_ANGLE_EVIDENCE_EMPTY")

    roles = [
        {
            "task_role": "REVIEW",
            "coverage_status": "FULL",
            "source_layer": "UNIT01_TASK_ANGLE_SYSTEM",
            "evidence": {
                "source_task_id": u01qb09.TASK_ID,
                "reusable_generic_task_angles": reusable_u01_angles,
            },
            "coverage_reason": "Unit01 validated task-angle assets can be reused for spiral review without pretending they teach Unit02 plurals.",
        },
        {
            "task_role": "NEW",
            "coverage_status": "FULL",
            "source_layer": "UNIT02_TEXT_MODE_ITEMS",
            "evidence": current_question_type_evidence(),
            "coverage_reason": "Current Unit02 has direct plural-focused recognition, meaning, form, morphology and production items.",
        },
        {
            "task_role": "INTEGRATION",
            "coverage_status": "GAP",
            "source_layer": "UNIT02_TASK_FAMILY_AUDIT",
            "evidence": {"task_family": "U01_U02_INTEGRATION"},
            "coverage_reason": "No current item jointly measures Unit01 Articles and Unit02 Plurals.",
            "gap": by_family["U01_U02_INTEGRATION"]["gap"],
        },
        {
            "task_role": "VARIATION",
            "coverage_status": "PARTIAL",
            "source_layer": "UNIT02_TEXT_MODE_ITEMS",
            "evidence": {
                "unique_task_type_count": len(current_question_type_evidence()["task_types"]),
                "task_types": current_question_type_evidence()["task_types"],
            },
            "coverage_reason": "Multiple task types exist, but the current fixed eight-item package does not encode an explicit variation role or capacity guarantee.",
            "gap": "EXPLICIT_VARIATION_ROLE_AND_CAPACITY_NOT_PROVEN",
        },
        {
            "task_role": "TRANSFER",
            "coverage_status": "PARTIAL",
            "source_layer": "UNIT02_TASK_FAMILY_AUDIT",
            "evidence": {"task_family": "TRANSFER"},
            "coverage_reason": "Contextual assessment exists, but cumulative unseen-scene transfer is not explicitly bound.",
            "gap": by_family["TRANSFER"]["gap"],
        },
    ]
    if tuple(row["task_role"] for row in roles) != TASK_ROLES:
        raise Unit02TaskAngleCoverageError("TASK_ROLE_DENOMINATOR_IDENTITY_DRIFT")
    return roles


def payload() -> dict[str, Any]:
    q8 = u02cf01.payload()
    if q8.get("coverage_denominators", {}).get("missing_function_family_count") != 0:
        raise Unit02TaskAngleCoverageError("Q8_COMMUNICATIVE_FUNCTION_COVERAGE_NOT_CLOSED")
    families = task_family_rows()
    roles = task_role_rows(families)

    family_counts = Counter(row["coverage_status"] for row in families)
    role_counts = Counter(row["coverage_status"] for row in roles)
    task_type_evidence = current_question_type_evidence()

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "level_scope": LEVEL_SCOPE,
        "artifact_semantics": "UNIT02_SCOPED_TASK_ANGLE_QUESTION_TYPE_COVERAGE_AUDIT_NOT_QUESTIONBANK_MATERIALIZATION",
        "source_authority": {
            "q8_source_task_id": u02cf01.TASK_ID,
            "unit01_task_angle_source_task_id": u01qb09.TASK_ID,
            "unit02_practice_item_source_task_id": practice_source.TASK_ID,
            "global_question_type_authority_task_id": authority_query.TASK_ID,
        },
        "pedagogical_task_role_denominator": roles,
        "task_question_family_denominator": families,
        "current_unit02_question_type_evidence": task_type_evidence,
        "coverage_denominators": {
            "task_role_count": len(roles),
            "task_role_full_count": role_counts["FULL"],
            "task_role_partial_count": role_counts["PARTIAL"],
            "task_role_gap_count": role_counts["GAP"],
            "task_family_count": len(families),
            "task_family_full_count": family_counts["FULL"],
            "task_family_partial_count": family_counts["PARTIAL"],
            "task_family_gap_count": family_counts["GAP"],
            "task_family_gap_ids": [
                row["task_family"] for row in families if row["coverage_status"] == "GAP"
            ],
            "task_family_partial_ids": [
                row["task_family"] for row in families if row["coverage_status"] == "PARTIAL"
            ],
            "current_unit02_item_count": task_type_evidence["unit02_item_count"],
            "current_unit02_unique_task_type_count": task_type_evidence["unique_task_type_count"],
        },
        "question9_contract": {
            "target_task_roles": list(TASK_ROLES),
            "target_task_families": list(TASK_FAMILIES),
            "denominator_resolved": True,
            "all_task_families_materialized": family_counts["GAP"] == 0 and family_counts["PARTIAL"] == 0,
            "gaps_must_feed_questionbank_gap_materialization": True,
            "distinct_capacity_not_claimed": True,
        },
        "claim_boundaries": {
            "canonical_graph_mutated": False,
            "questionbank_mutated": False,
            "new_question_items_authored": 0,
            "runtime_allocation_mutated": False,
            "learner_facing_content_created": False,
            "learner_state_joined": False,
            "distinct_item_capacity_claimed": False,
            "a2_unlocked": False,
        },
        "next_scope": {
            "coverage_denominator_number": 10,
            "coverage_denominator": "QUESTIONBANK_DISTINCT_CAPACITY",
            "scope_status": NEXT_SCOPE_STATUS,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    value = payload()
    counts = value["coverage_denominators"]
    print(f"STATUS={PASS_STATUS}")
    print(f"TASK_ROLES={counts['task_role_count']}")
    print(f"TASK_ROLE_FULL={counts['task_role_full_count']}")
    print(f"TASK_ROLE_PARTIAL={counts['task_role_partial_count']}")
    print(f"TASK_ROLE_GAP={counts['task_role_gap_count']}")
    print(f"TASK_FAMILIES={counts['task_family_count']}")
    print(f"TASK_FAMILY_FULL={counts['task_family_full_count']}")
    print(f"TASK_FAMILY_PARTIAL={counts['task_family_partial_count']}")
    print(f"TASK_FAMILY_GAP={counts['task_family_gap_count']}")
    print(f"CURRENT_UNIT02_ITEMS={counts['current_unit02_item_count']}")
    print(f"CURRENT_UNIT02_UNIQUE_TASK_TYPES={counts['current_unit02_unique_task_type_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
