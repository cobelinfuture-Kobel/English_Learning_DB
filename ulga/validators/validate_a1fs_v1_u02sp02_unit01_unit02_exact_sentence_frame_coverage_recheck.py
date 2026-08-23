#!/usr/bin/env python3
"""Validate U02SP02 sentence-pattern lineage and exact-frame reconciliation."""
from __future__ import annotations

from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u02sp02_unit01_unit02_exact_sentence_frame_coverage_recheck as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U02SP02_UNIT01_UNIT02_EXACT_SENTENCE_FRAME_COVERAGE_RECHECK_VALIDATOR"


class U02SP02ValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise U02SP02ValidationError(code)


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    require(report.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(report.get("program_id") == builder.PROGRAM_ID, "PROGRAM_INVALID")
    require(report.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(report.get("status") == builder.PASS_STATUS, "STATUS_INVALID")

    patterns = report.get("pattern_family_coverage", {})
    require(patterns.get("unit01_inherited_pedagogical_core_family_count") == 3, "UNIT01_CORE_PATTERN_COUNT_INVALID")
    require(patterns.get("unit02_new_canonical_core_pattern_count") == 4, "UNIT02_NEW_PATTERN_COUNT_INVALID")
    require(patterns.get("cumulative_pedagogical_core_pattern_family_count") == 7, "CUMULATIVE_CORE_PATTERN_COUNT_INVALID")
    require(patterns.get("unit02_main_plural_sentence_generation_family_count") == 5, "PLURAL_GENERATION_FAMILY_COUNT_INVALID")
    generation = patterns.get("unit02_main_plural_sentence_generation_model", {})
    require(generation.get("inherited_plural_capable_family_count") == 1, "INHERITED_PLURAL_FAMILY_COUNT_INVALID")
    require(generation.get("newly_unlocked_family_count") == 4, "NEWLY_UNLOCKED_FAMILY_COUNT_INVALID")

    u01_families = patterns.get("unit01_inherited_pedagogical_core_families", [])
    require(len(u01_families) == 3, "UNIT01_CORE_PATTERN_ROWS_INVALID")
    require(
        [row.get("family_id") for row in u01_families] == ["U01-P1", "U01-P2", "U01-P3"],
        "UNIT01_CORE_PATTERN_IDENTITY_DRIFT",
    )
    require(
        u01_families[1].get("unit02_plural_role") == "INHERITED_CLAUSE_SHELL_PLURAL_NP_CAPABLE",
        "UNIT01_PLURAL_CAPABLE_FAMILY_DRIFT",
    )

    new_patterns = patterns.get("unit02_new_canonical_core_patterns", [])
    require(len(new_patterns) == 4, "UNIT02_NEW_PATTERN_ROWS_INVALID")
    actual_patterns = {
        str(row.get("source_record_id")): str(row.get("canonical_pattern"))
        for row in new_patterns
    }
    require(actual_patterns == dict(builder.UNIT02_NEW_CANONICAL_PATTERNS), "UNIT02_CANONICAL_PATTERN_AUTHORITY_DRIFT")
    require(all(row.get("review_status") == "accepted" for row in new_patterns), "UNIT02_CANONICAL_PATTERN_NOT_ACCEPTED")

    frames = report.get("exact_frame_coverage", {})
    require(frames.get("unit01_exact_frame_count") == 11, "UNIT01_EXACT_FRAME_COUNT_INVALID")
    require(frames.get("unit01_core_sentence_frame_count") == 6, "UNIT01_CORE_FRAME_COUNT_INVALID")
    require(frames.get("unit01_adjective_sentence_frame_count") == 3, "UNIT01_ADJECTIVE_FRAME_COUNT_INVALID")
    require(frames.get("unit01_scaffold_frame_count") == 2, "UNIT01_SCAFFOLD_FRAME_COUNT_INVALID")
    require(frames.get("unit02_new_canonical_exact_frame_count") == 4, "UNIT02_EXACT_FRAME_COUNT_INVALID")
    require(frames.get("cross_unit_exact_template_overlap_count") == 0, "CROSS_UNIT_EXACT_FRAME_OVERLAP")
    require(frames.get("cross_unit_exact_template_overlap") == [], "CROSS_UNIT_EXACT_FRAME_OVERLAP_ROWS")
    require(frames.get("cumulative_declared_exact_frame_count") == 15, "CUMULATIVE_EXACT_FRAME_COUNT_INVALID")
    require(len(frames.get("unit01_exact_frames", [])) == 11, "UNIT01_EXACT_FRAME_ROWS_INVALID")
    require(len(frames.get("unit02_new_canonical_exact_frames", [])) == 4, "UNIT02_EXACT_FRAME_ROWS_INVALID")

    i_have = report.get("i_have_lineage_reconciliation", {})
    require(i_have.get("unit01_contract_frame_id") == "U01-F02", "I_HAVE_U01_FRAME_ID_INVALID")
    require(i_have.get("unit01_contract_template") == "I have {ARTICLE} {THING}.", "I_HAVE_U01_TEMPLATE_INVALID")
    require(i_have.get("unit02_canonical_pattern_id") == "SP_000003", "I_HAVE_U02_PATTERN_ID_INVALID")
    require(i_have.get("unit02_canonical_pattern_template") == "I have {noun_phrase}.", "I_HAVE_U02_TEMPLATE_INVALID")
    require(i_have.get("exact_template_match") is False, "I_HAVE_EXACT_TEMPLATE_FALSELY_COLLAPSED")
    require(i_have.get("unit01_pedagogical_core_inherited") is False, "I_HAVE_FALSELY_INHERITED_AS_UNIT01_CORE")
    require(i_have.get("unit02_new_core_pattern") is True, "I_HAVE_NOT_CLASSIFIED_AS_UNIT02_NEW")
    require(
        i_have.get("classification") == "FRAME_PRESENT_IN_UNIT01_CONTRACT_BUT_PEDAGOGICALLY_DEFERRED_TO_UNIT02",
        "I_HAVE_LINEAGE_CLASS_INVALID",
    )

    legacy = report.get("legacy_pattern_reconciliation", {})
    require(legacy.get("legacy_invalid_pattern_id") == builder.LEGACY_INVALID_PATTERN_ID, "LEGACY_PATTERN_ID_INVALID")
    canonical_legacy = legacy.get("canonical_authority", {})
    require(canonical_legacy.get("canonical_pattern") == "My name is {name}.", "SP000002_CANONICAL_AUTHORITY_INVALID")
    require(canonical_legacy.get("label") == "My name is {name}.", "SP000002_LABEL_INVALID")
    require(legacy.get("raw_approved_u02_item_count") == 994, "RAW_U02_ITEM_COUNT_INVALID")
    require(legacy.get("raw_u02qb02_item_count") == 658, "RAW_U02QB02_COUNT_INVALID")
    require(legacy.get("raw_u02qbc02_new_item_count") == 336, "RAW_U02QBC02_COUNT_INVALID")
    require(
        legacy.get("raw_pattern_binding_distribution") == {builder.LEGACY_INVALID_PATTERN_ID: 994},
        "RAW_PATTERN_BINDING_DISTRIBUTION_INVALID",
    )
    require(legacy.get("raw_legacy_invalid_binding_count") == 994, "RAW_LEGACY_BINDING_COUNT_INVALID")
    require(legacy.get("reconciled_legacy_invalid_binding_count") == 0, "LEGACY_BINDING_NOT_REMOVED_BY_RECONCILIATION")
    require(legacy.get("reconciled_direct_canonical_sp_binding_count") == 0, "DIRECT_SP_BINDING_FALSELY_CREATED")
    require(legacy.get("unit02_new_core_patterns_bound_in_current_questionbank_count") == 0, "NEW_PATTERN_QB_BINDING_OVERCLAIM")
    require(legacy.get("inherited_clause_shell_recombination_item_count") == 96, "INHERITED_RECOMBINATION_COUNT_INVALID")
    require(legacy.get("future_runtime_must_consume_reconciled_projection") is True, "RUNTIME_PROJECTION_REQUIREMENT_MISSING")
    require(legacy.get("raw_pattern_ids_runtime_authoritative") is False, "RAW_PATTERN_IDS_FALSELY_AUTHORITATIVE")

    projection = report.get("reconciled_questionbank_pattern_projection", [])
    require(len(projection) == 13, "PROJECTION_FAMILY_COUNT_INVALID")
    require(sum(int(row.get("item_count", 0)) for row in projection) == 994, "PROJECTION_ITEM_COUNT_INVALID")
    require(all(row.get("raw_pattern_ids") == [builder.LEGACY_INVALID_PATTERN_ID] for row in projection), "PROJECTION_RAW_PATTERN_DRIFT")
    require(all(row.get("reconciled_direct_pattern_ids") == [] for row in projection), "PROJECTION_DIRECT_PATTERN_OVERCLAIM")
    require(all(row.get("runtime_may_consume_raw_pattern_ids") is False for row in projection), "PROJECTION_RAW_RUNTIME_LEAK")
    recombination = [
        row for row in projection
        if row.get("lineage_class") == "INHERITED_U01_CLAUSE_SHELL_WITH_UNIT02_PLURAL_NP"
    ]
    require(len(recombination) == 2, "RECOMBINATION_FAMILY_COUNT_INVALID")
    require({row.get("family_id") for row in recombination} == set(builder.RECOMBINATION_TASK_FAMILIES), "RECOMBINATION_FAMILY_IDENTITY_INVALID")
    require(sum(int(row.get("item_count", 0)) for row in recombination) == 96, "RECOMBINATION_ITEM_COUNT_INVALID")
    require(all(row.get("source_unit01_frame_id") == "U01-F06" for row in recombination), "RECOMBINATION_SOURCE_FRAME_INVALID")

    boundaries = report.get("claim_boundaries", {})
    expected_boundaries = {
        "historical_u02qb02_payload_mutated": False,
        "historical_u02qbc02_payload_mutated": False,
        "questionbank_item_identity_mutated": False,
        "answer_or_scoring_contract_mutated": False,
        "global_sentence_pattern_authority_mutated": False,
        "runtime_connected": False,
        "canonical_scene_authority_mutated": False,
        "new_learner_content_created": False,
        "a2_unlocked": False,
    }
    require(boundaries == expected_boundaries, "CLAIM_BOUNDARIES_INVALID")

    next_scope = report.get("next_scope", {})
    require(next_scope.get("scope_status") == builder.NEXT_SCOPE_STATUS, "NEXT_SCOPE_STATUS_INVALID")
    require(next_scope.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_SCOPE_TASK_INVALID")
    require(report.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_SHORT_STEP_INVALID")

    return {
        "status": builder.PASS_STATUS,
        "validator_id": VALIDATOR_ID,
        "error_count": 0,
        "errors": [],
        "cumulative_core_pattern_families": 7,
        "cumulative_declared_exact_frames": 15,
        "raw_invalid_sp000002_bindings": 994,
        "reconciled_invalid_sp000002_bindings": 0,
    }
