#!/usr/bin/env python3
"""Build and validate the structural A1/A1+ grammar learning-unit core."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "R7-M105A_A1A1PlusGrammarLearningUnitCore"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_SHORT_STEP = "R7-M105B_A1GrammarRepresentativeVerticalSlice"

CANONICAL_PATH = REPO_ROOT / "ulga/graph/a1_egp_canonical_mappings.json"
QUERY_PATH = REPO_ROOT / "ulga/graph/grammar_query_index.json"
RULE_PATH = REPO_ROOT / "ulga/graph/a1_canonical_rule_validator_index.json"
AUTHORITY_PATH = REPO_ROOT / "ulga/contracts/a1_grammar_learning_content_authority.json"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_grammar_learning_units.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_grammar_learning_unit_validation.json"

SECTIONS = (
    "learning_objectives", "form_rules", "meaning_functions",
    "usage_conditions", "positive_examples", "negative_examples",
    "common_error_tags", "contrast_unit_ids",
)

A1_UNITS = {
    "GRAMMAR_ARTICLES_BASIC", "GRAMMAR_SUBJECT_PRONOUNS",
    "GRAMMAR_OBJECT_PRONOUNS_BASIC", "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC",
    "GRAMMAR_CAN_STATEMENT", "GRAMMAR_PRESENT_SIMPLE_NEGATIVES",
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS", "GRAMMAR_THERE_IS",
    "GRAMMAR_BE_INTERROGATIVES_A1", "GRAMMAR_CAN_NEGATIVE_A1",
    "GRAMMAR_REGULAR_PLURAL_NOUNS", "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS", "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_DEMONSTRATIVES_CONTRAST",
}

PREREQUISITES = {
    "GRAMMAR_ARTICLES_BASIC": [],
    "GRAMMAR_SUBJECT_PRONOUNS": [],
    "GRAMMAR_OBJECT_PRONOUNS_BASIC": ["GRAMMAR_SUBJECT_PRONOUNS"],
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": ["GRAMMAR_SUBJECT_PRONOUNS"],
    "GRAMMAR_CAN_STATEMENT": ["GRAMMAR_SUBJECT_PRONOUNS"],
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES": ["GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS"],
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS": [
        "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
        "GRAMMAR_PRESENT_SIMPLE_NEGATIVES",
    ],
    "GRAMMAR_THERE_IS": [
        "GRAMMAR_ARTICLES_BASIC", "GRAMMAR_BE_VERB_BASIC",
        "GRAMMAR_REGULAR_PLURAL_NOUNS",
    ],
    "GRAMMAR_BE_INTERROGATIVES_A1": [
        "GRAMMAR_BE_VERB_BASIC", "GRAMMAR_SUBJECT_PRONOUNS",
    ],
    "GRAMMAR_CAN_NEGATIVE_A1": ["GRAMMAR_CAN_STATEMENT"],
    "GRAMMAR_WILL_FUTURE_A1": ["GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS"],
    "GRAMMAR_PAST_SIMPLE_A1": ["GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS"],
    "GRAMMAR_REGULAR_PLURAL_NOUNS": [],
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": ["GRAMMAR_ARTICLES_BASIC"],
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS": ["GRAMMAR_SUBJECT_PRONOUNS"],
    "GRAMMAR_BE_VERB_BASIC": ["GRAMMAR_SUBJECT_PRONOUNS"],
    "GRAMMAR_ADJECTIVE_PHRASES_A1": [
        "GRAMMAR_ARTICLES_BASIC", "GRAMMAR_BE_VERB_BASIC",
    ],
    "GRAMMAR_COORDINATION_A1": ["GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS"],
    "GRAMMAR_BECAUSE_REASON_CLAUSES_A1": [
        "GRAMMAR_COORDINATION_A1", "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
    ],
    "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1": [
        "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
    ],
    "GRAMMAR_ADVERB_PHRASES_A1": ["GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS"],
    "GRAMMAR_NOUN_PHRASES_A1": [
        "GRAMMAR_ADJECTIVE_PHRASES_A1", "GRAMMAR_ARTICLES_BASIC",
        "GRAMMAR_REGULAR_PLURAL_NOUNS",
    ],
    "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1": [
        "GRAMMAR_BE_VERB_BASIC", "GRAMMAR_CAN_STATEMENT",
        "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
    ],
    "GRAMMAR_DEMONSTRATIVES_CONTRAST": [
        "GRAMMAR_ARTICLES_BASIC", "GRAMMAR_REGULAR_PLURAL_NOUNS",
    ],
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def unique(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value})


def assert_acyclic(graph: dict[str, list[str]]) -> None:
    state = {node: 0 for node in graph}
    stack: list[str] = []

    def visit(node: str) -> None:
        if state[node] == 2:
            return
        if state[node] == 1:
            start = stack.index(node)
            raise ValueError(
                "prerequisite_cycle:" + "->".join(stack[start:] + [node])
            )
        state[node] = 1
        stack.append(node)
        for dependency in graph[node]:
            if dependency not in graph:
                raise ValueError(f"unknown_prerequisite:{node}:{dependency}")
            visit(dependency)
        stack.pop()
        state[node] = 2

    for node in graph:
        visit(node)


def source_sets(
    canonical: dict[str, Any],
    query: dict[str, Any],
    rules: dict[str, Any],
    authority: dict[str, Any],
) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    if canonical.get("canonical_status") != "ACTIVE":
        raise ValueError("canonical_overlay_not_active")
    if canonical.get("official_level") != "A1":
        raise ValueError("canonical_overlay_not_a1")
    if authority.get("authority_status") != "ACTIVE_FOR_STRUCTURAL_LEARNING_CONTENT":
        raise ValueError("content_authority_not_active")
    if authority.get("claim_boundaries", {}).get("teaching_content_complete") is not False:
        raise ValueError("authority_false_teaching_claim")

    unit_ids = canonical.get("canonical_mapping_units", [])
    query_a1 = query.get("canonical_a1", {})
    query_units = query_a1.get("by_grammar_id", {})
    rule_units = rules.get("by_grammar_id", {})
    expected = set(unit_ids)
    if len(unit_ids) != 24 or len(expected) != 24:
        raise ValueError("canonical_unit_count_not_24")
    if expected != set(query_units) or expected != set(rule_units):
        raise ValueError("canonical_source_unit_set_mismatch")
    if expected != set(PREREQUISITES):
        raise ValueError("prerequisite_unit_set_mismatch")
    if query_a1.get("canonical_unique_egp_row_count") != 109:
        raise ValueError("canonical_row_count_not_109")
    assert_acyclic(PREREQUISITES)
    return unit_ids, query_units, rule_units


def build_artifact(
    canonical: dict[str, Any],
    query: dict[str, Any],
    rules: dict[str, Any],
    authority: dict[str, Any],
) -> dict[str, Any]:
    unit_ids, query_units, rule_units = source_sets(
        canonical, query, rules, authority
    )
    mastery = deepcopy(authority["mastery_policy"])
    row_bindings: dict[str, list[tuple[str, str]]] = defaultdict(list)
    units = []

    for index, grammar_id in enumerate(unit_ids, 1):
        stage = "A1" if grammar_id in A1_UNITS else "A1+"
        row_ids = unique(query_units[grammar_id].get("egp_row_ids", []))
        rule = rule_units[grammar_id]
        for row_id in row_ids:
            row_bindings[row_id].append((grammar_id, stage))
        units.append({
            "sequence_index": index,
            "grammar_unit_id": grammar_id,
            "official_egp_level": "A1",
            "internal_stage": stage,
            "stage_assignment_status": (
                "PROVISIONAL_SYSTEM_SEQUENCE_NOT_OFFICIAL_EGP_LEVEL"
            ),
            "canonical_mapping_status": query_units[grammar_id].get(
                "mapping_reference_status",
                "VERIFIED_CANONICAL_MAPPING" if row_ids
                else "CANONICAL_UNIT_NO_COVERAGE_INCREMENT",
            ),
            "canonical_egp_row_ids": row_ids,
            "canonical_egp_row_count": len(row_ids),
            "prerequisite_unit_ids": unique(PREREQUISITES[grammar_id]),
            "prerequisite_status": "PROVISIONAL_VALIDATED_ACYCLIC",
            "source_trace": {
                "canonical_mapping_overlay_path": rel(CANONICAL_PATH),
                "canonical_query_index_path": rel(QUERY_PATH),
                "rule_validator_index_path": rel(RULE_PATH),
                "rule_source_path": rule.get("rule_source_path"),
                "rule_artifact_id": rule.get("rule_artifact_id"),
                "sentence_validator_path": rule.get("sentence_validator_path"),
                "sentence_validator_mode": rule.get("sentence_validator_mode"),
                "runtime_validator_status": rule.get("runtime_validator_status"),
            },
            "content_authority": {
                "authority_contract_path": rel(AUTHORITY_PATH),
                "authority_contract_id": authority["artifact_id"],
                "authority_status": "STRUCTURAL_SCAFFOLD",
                "content_origin_requirement": (
                    "PROJECT_AUTHORED_OR_OPERATOR_REVIEWED_DERIVED_CONTENT"
                ),
                "official_egp_text_copied": False,
                "raw_external_source_text_copied": False,
                "restricted_source_payload_persisted": False,
            },
            "learning_content": {
                **{section: [] for section in SECTIONS},
                "mastery_requirements": deepcopy(mastery),
            },
            "content_section_status": {
                section: "NOT_STARTED" for section in SECTIONS
            },
            "readiness": {
                "structural_learning_unit_status": "READY",
                "teaching_content_status": "NOT_STARTED",
                "practice_content_status": "NOT_STARTED",
                "assessment_content_status": "NOT_STARTED",
                "mastery_runtime_status": "NOT_IMPLEMENTED",
                "teachable": False,
                "practice_ready": False,
                "assessment_ready": False,
                "mastery_trackable": False,
            },
        })

    by_row = {}
    for row_id, bindings in sorted(row_bindings.items()):
        grammar_ids = unique(item[0] for item in bindings)
        stages = unique(item[1] for item in bindings)
        by_row[row_id] = {
            "egp_row_id": row_id,
            "grammar_unit_ids": grammar_ids,
            "internal_stages": stages,
            "effective_internal_stage": "A1" if "A1" in stages else "A1+",
            "traceability_status": (
                "TRACEABLE_TO_CANONICAL_GRAMMAR_LEARNING_UNIT"
            ),
            "official_egp_text_copied": False,
        }

    canonical_rows = set(query["canonical_a1"]["canonical_egp_row_ids"])
    if set(by_row) != canonical_rows or len(by_row) != 109:
        raise ValueError("built_row_set_not_109_canonical_rows")

    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_learning_units",
        "artifact_type": "a1_a1plus_structural_grammar_learning_unit_authority",
        "schema_version": "a1_grammar_learning_units.v1",
        "official_level": "A1",
        "internal_stages": ["A1", "A1+"],
        "authority_contract_path": rel(AUTHORITY_PATH),
        "source_paths": {
            "canonical_mapping_overlay": rel(CANONICAL_PATH),
            "canonical_query_index": rel(QUERY_PATH),
            "rule_validator_index": rel(RULE_PATH),
        },
        "stage_policy": {
            "A1": "core_a1_sequence",
            "A1+": "internal_bridge_sequence_not_official_egp_level",
            "assignment_status": (
                "PROVISIONAL_SYSTEM_SEQUENCE_SUBJECT_TO_VERTICAL_SLICE_QA"
            ),
        },
        "coverage_summary": {
            "canonical_grammar_unit_count": 24,
            "structural_learning_unit_count": 24,
            "canonical_unique_egp_row_count": 109,
            "traceable_unique_egp_row_count": 109,
            "units_with_unique_row_increment": sum(
                bool(unit["canonical_egp_row_ids"]) for unit in units
            ),
            "units_without_unique_row_increment": sum(
                not unit["canonical_egp_row_ids"] for unit in units
            ),
            "teaching_ready_unit_count": 0,
            "practice_ready_unit_count": 0,
            "assessment_ready_unit_count": 0,
            "mastery_trackable_unit_count": 0,
            "structural_unit_coverage_percent": 100.0,
            "row_traceability_percent": 100.0,
            "teachable_unit_coverage_percent": 0.0,
        },
        "learning_units": units,
        "by_egp_row_id": by_row,
        "claim_boundaries": {
            "canonical_mapping_complete": True,
            "structural_learning_units_complete": True,
            "teaching_content_complete": False,
            "practice_content_complete": False,
            "assessment_content_complete": False,
            "learner_mastery_runtime_complete": False,
            "production_runtime_validation_complete": False,
            "a1_plus_is_internal_bridge_not_official_egp_level": True,
            "no_a2_a2plus_expansion": True,
            "no_learner_state_write": True,
            "no_external_nlp_dependency": True,
            "no_restricted_source_payload_copy": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def validate_artifact(
    artifact: dict[str, Any],
    canonical: dict[str, Any],
    query: dict[str, Any],
    rules: dict[str, Any],
    authority: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        unit_ids, query_units, rule_units = source_sets(
            canonical, query, rules, authority
        )
    except ValueError as exc:
        return {
            "task_id": TASK_ID,
            "validation_status": "FAIL",
            "errors": [str(exc)],
            "next_short_step": None,
        }

    units = artifact.get("learning_units", [])
    by_id = {
        unit.get("grammar_unit_id"): unit
        for unit in units if unit.get("grammar_unit_id")
    }
    if len(units) != 24 or set(by_id) != set(unit_ids):
        errors.append("learning_unit_set_not_24_canonical_units")

    graph = {}
    row_bindings: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for grammar_id, unit in by_id.items():
        stage = unit.get("internal_stage")
        if stage not in {"A1", "A1+"}:
            errors.append(f"invalid_internal_stage:{grammar_id}")
        expected_rows = unique(query_units[grammar_id].get("egp_row_ids", []))
        actual_rows = unit.get("canonical_egp_row_ids", [])
        if actual_rows != expected_rows:
            errors.append(f"row_set_mismatch:{grammar_id}")
        if unit.get("canonical_egp_row_count") != len(actual_rows):
            errors.append(f"row_count_mismatch:{grammar_id}")
        for row_id in actual_rows:
            row_bindings[row_id].append((grammar_id, stage))

        graph[grammar_id] = unit.get("prerequisite_unit_ids", [])
        rule = rule_units[grammar_id]
        trace = unit.get("source_trace", {})
        for field in (
            "rule_source_path", "rule_artifact_id",
            "sentence_validator_path", "sentence_validator_mode",
            "runtime_validator_status",
        ):
            if trace.get(field) != rule.get(field):
                errors.append(f"source_trace_mismatch:{grammar_id}:{field}")

        content = unit.get("learning_content", {})
        section_status = unit.get("content_section_status", {})
        if any(content.get(section) != [] for section in SECTIONS):
            errors.append(f"unreviewed_content_in_scaffold:{grammar_id}")
        if any(section_status.get(section) != "NOT_STARTED" for section in SECTIONS):
            errors.append(f"invalid_section_status:{grammar_id}")
        readiness = unit.get("readiness", {})
        if readiness.get("structural_learning_unit_status") != "READY":
            errors.append(f"structural_unit_not_ready:{grammar_id}")
        if any(readiness.get(field) is not False for field in (
            "teachable", "practice_ready", "assessment_ready",
            "mastery_trackable",
        )):
            errors.append(f"false_readiness_claim:{grammar_id}")

    try:
        assert_acyclic(graph)
    except ValueError as exc:
        errors.append(str(exc))

    canonical_rows = set(query["canonical_a1"]["canonical_egp_row_ids"])
    if set(row_bindings) != canonical_rows or len(row_bindings) != 109:
        errors.append("row_traceability_not_109_of_109")
    if set(artifact.get("by_egp_row_id", {})) != canonical_rows:
        errors.append("row_index_not_109_of_109")

    summary = artifact.get("coverage_summary", {})
    required_summary = {
        "canonical_grammar_unit_count": 24,
        "structural_learning_unit_count": 24,
        "canonical_unique_egp_row_count": 109,
        "traceable_unique_egp_row_count": 109,
        "teaching_ready_unit_count": 0,
        "practice_ready_unit_count": 0,
        "assessment_ready_unit_count": 0,
        "mastery_trackable_unit_count": 0,
        "structural_unit_coverage_percent": 100.0,
        "row_traceability_percent": 100.0,
        "teachable_unit_coverage_percent": 0.0,
    }
    if any(summary.get(key) != value for key, value in required_summary.items()):
        errors.append("coverage_summary_mismatch")

    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("teaching_content_complete") is not False:
        errors.append("false_teaching_completion_claim")
    for field in (
        "no_a2_a2plus_expansion", "no_learner_state_write",
        "no_external_nlp_dependency", "no_restricted_source_payload_copy",
    ):
        if boundaries.get(field) is not True:
            errors.append(f"scope_boundary_missing:{field}")

    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_learning_unit_validation",
        "validation_status": status,
        "coverage_summary": required_summary,
        "gate_checks": {
            "content_authority_active": (
                authority.get("authority_status")
                == "ACTIVE_FOR_STRUCTURAL_LEARNING_CONTENT"
            ),
            "canonical_units_24_of_24": len(by_id) == 24,
            "canonical_rows_109_of_109": len(row_bindings) == 109,
            "prerequisite_graph_acyclic": not any(
                error.startswith("prerequisite_cycle") for error in errors
            ),
            "mapping_teaching_claim_separated": (
                summary.get("teachable_unit_coverage_percent") == 0.0
            ),
            "no_a2plus_scope": boundaries.get("no_a2_a2plus_expansion") is True,
            "no_learner_state_write": boundaries.get("no_learner_state_write") is True,
        },
        "errors": errors,
        "warnings": [
            "GRAMMAR_DEMONSTRATIVES_CONTRAST adds no unique-row increment.",
            "This is structural 24-unit/109-row coverage, not teaching readiness.",
        ],
        "stop_reason": "NONE" if status == "PASS" else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if status == "PASS" else None,
        "validation_mode": "LOCAL_DETERMINISTIC_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    canonical = load_json(CANONICAL_PATH)
    query = load_json(QUERY_PATH)
    rules = load_json(RULE_PATH)
    authority = load_json(AUTHORITY_PATH)
    artifact = build_artifact(canonical, query, rules, authority)
    report = validate_artifact(artifact, canonical, query, rules, authority)
    return artifact, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    artifact, report = build_and_validate_from_repo()
    write_json(args.output, artifact)
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
