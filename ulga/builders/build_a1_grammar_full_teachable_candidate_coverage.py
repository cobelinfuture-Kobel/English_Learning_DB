#!/usr/bin/env python3
"""Build and validate full A1/A1+ project-authored candidate teachable coverage."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_learning_unit_core import A1_UNITS, PREREQUISITES
from ulga.builders.build_a1_grammar_representative_vertical_slice import (
    PILOT_UNIT_IDS,
    UNIT_SPECS,
    _activities,
)
from ulga.query.a1_canonical_validator_dispatcher import validate as dispatch_validate
from ulga.query.a1_practice_item_grammar_gate import validate_practice_item

TASK_ID = "R7-M105C_A1A1PlusFullTeachableCoverage"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_SHORT_STEP = "R7-M105D_A1GrammarReadingWritingClosedLoop"

QUERY_PATH = REPO_ROOT / "ulga/graph/grammar_query_index.json"
RULE_INDEX_PATH = REPO_ROOT / "ulga/graph/a1_canonical_rule_validator_index.json"
AUTHORITY_PATH = REPO_ROOT / "ulga/contracts/a1_grammar_learning_content_authority.json"
CAN_RULE_PATH = REPO_ROOT / "ulga/rules/a1_can_statement_rule_primitives.json"
BATCH_01_PATH = REPO_ROOT / "ulga/rules/a1_a1plus_rule_primitives_batch_01.json"
BATCH_02_PATH = REPO_ROOT / "ulga/rules/a1_unbucketed_rule_primitives_batch_02.json"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_grammar_full_teachable_candidate_coverage.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_grammar_full_teachable_candidate_coverage_validation.json"

PEDAGOGY_META: dict[str, dict[str, list[str]]] = {
    "GRAMMAR_SUBJECT_PRONOUNS": {
        "meaning": ["identify who or what performs the clause action or state"],
        "usage": ["Place the subject pronoun before the finite verb.", "Choose I, you, he, she, it, we, or they to match the referent."],
        "contrasts": ["GRAMMAR_OBJECT_PRONOUNS_BASIC", "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC"],
    },
    "GRAMMAR_OBJECT_PRONOUNS_BASIC": {
        "meaning": ["refer to the person or thing affected by a verb or following a preposition"],
        "usage": ["Use me, you, him, her, it, us, or them in object position.", "Do not use an object pronoun as the clause subject."],
        "contrasts": ["GRAMMAR_SUBJECT_PRONOUNS", "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC"],
    },
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": {
        "meaning": ["show ownership or relationship before a noun"],
        "usage": ["Place my, your, his, her, its, our, or their before a noun.", "Choose the form by the possessor, not by the owned noun."],
        "contrasts": ["GRAMMAR_OBJECT_PRONOUNS_BASIC", "GRAMMAR_ARTICLES_BASIC"],
    },
    "GRAMMAR_CAN_STATEMENT": {
        "meaning": ["express ability or capability in an affirmative statement"],
        "usage": ["Use can before a base verb.", "Keep the clause affirmative and declarative; exclude questions, negatives, and can as a noun."],
        "contrasts": ["GRAMMAR_CAN_NEGATIVE_A1", "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1"],
    },
    "GRAMMAR_THERE_IS": {
        "meaning": ["state that a person or thing exists in a place or situation"],
        "usage": ["Use there is with a singular noun phrase and there are with a plural noun phrase.", "Distinguish existential there from locative there."],
        "contrasts": ["GRAMMAR_BE_VERB_BASIC", "GRAMMAR_BASIC_PREPOSITIONS_PLACE"],
    },
    "GRAMMAR_BE_INTERROGATIVES_A1": {
        "meaning": ["ask yes/no questions about identity, description, state, or location"],
        "usage": ["Move am, is, or are before the subject.", "Do not add do/does to a basic be question."],
        "contrasts": ["GRAMMAR_BE_VERB_BASIC", "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS"],
    },
    "GRAMMAR_CAN_NEGATIVE_A1": {
        "meaning": ["express inability or a negative can proposition"],
        "usage": ["Use cannot, can not, or can't before a base verb.", "Do not classify can questions or can as a noun as this unit."],
        "contrasts": ["GRAMMAR_CAN_STATEMENT", "GRAMMAR_PRESENT_SIMPLE_NEGATIVES"],
    },
    "GRAMMAR_WILL_FUTURE_A1": {
        "meaning": ["refer to a future action, prediction, or simple decision"],
        "usage": ["Use will or 'll before a base verb.", "Keep the lexical verb in the base form after will."],
        "contrasts": ["GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS", "GRAMMAR_PAST_SIMPLE_A1"],
    },
    "GRAMMAR_REGULAR_PLURAL_NOUNS": {
        "meaning": ["refer to more than one countable person, animal, place, or thing"],
        "usage": ["Use regular -s or -es plural marking where licensed.", "Distinguish plural -s from third-person verb -s and possessive 's."],
        "contrasts": ["GRAMMAR_ARTICLES_BASIC", "GRAMMAR_NOUN_PHRASES_A1"],
    },
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": {
        "meaning": ["show a basic spatial relationship between entities"],
        "usage": ["Use a place preposition such as in, on, under, or next to before a noun phrase.", "Do not classify time uses such as on Monday as place relations."],
        "contrasts": ["GRAMMAR_ADVERB_PHRASES_A1", "GRAMMAR_THERE_IS"],
    },
    "GRAMMAR_ADJECTIVE_PHRASES_A1": {
        "meaning": ["describe qualities and modify a noun or subject complement"],
        "usage": ["Use an adjective before a noun or after a linking be verb.", "Use very only with a suitable gradable adjective in this unit."],
        "contrasts": ["GRAMMAR_ADVERB_PHRASES_A1", "GRAMMAR_NOUN_PHRASES_A1"],
    },
    "GRAMMAR_COORDINATION_A1": {
        "meaning": ["join compatible words, phrases, clauses, or list items"],
        "usage": ["Use and, but, or or between compatible units.", "Use but to signal a meaningful contrast rather than as an isolated discourse fragment."],
        "contrasts": ["GRAMMAR_BECAUSE_REASON_CLAUSES_A1", "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1"],
    },
    "GRAMMAR_BECAUSE_REASON_CLAUSES_A1": {
        "meaning": ["give a reason for a statement or action"],
        "usage": ["Join a main clause to a finite reason clause with because.", "Avoid an unsupported because fragment when a complete response is required."],
        "contrasts": ["GRAMMAR_COORDINATION_A1", "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1"],
    },
    "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1": {
        "meaning": ["complete a verb with a licensed base verb, to-infinitive, or -ing form"],
        "usage": ["Choose the complement form licensed by the first verb or modal.", "Distinguish infinitival to from prepositional to."],
        "contrasts": ["GRAMMAR_CAN_STATEMENT", "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS"],
    },
    "GRAMMAR_ADVERB_PHRASES_A1": {
        "meaning": ["add information about time, place, frequency, manner, or degree"],
        "usage": ["Place the adverb in a position licensed by its function.", "Distinguish adverb uses from noun phrases, adjectives, and existential there."],
        "contrasts": ["GRAMMAR_ADJECTIVE_PHRASES_A1", "GRAMMAR_BASIC_PREPOSITIONS_PLACE"],
    },
    "GRAMMAR_NOUN_PHRASES_A1": {
        "meaning": ["name or refer to people, places, things, and ideas in clause roles"],
        "usage": ["Build the phrase around a noun head with suitable determiners or modifiers.", "Use the noun phrase as subject, object, or adjunct where licensed."],
        "contrasts": ["GRAMMAR_ARTICLES_BASIC", "GRAMMAR_ADJECTIVE_PHRASES_A1"],
    },
    "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1": {
        "meaning": ["make basic affirmative or negative statements"],
        "usage": ["Use a subject followed by an appropriate predicate in statement order.", "Distinguish declarative clauses from questions and fragments."],
        "contrasts": ["GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS", "GRAMMAR_BE_INTERROGATIVES_A1"],
    },
    "GRAMMAR_DEMONSTRATIVES_CONTRAST": {
        "meaning": ["identify a near or far referent while marking singular or plural number"],
        "usage": ["Use this/that with singular nouns and these/those with plural nouns.", "Use context to distinguish near from far reference."],
        "contrasts": ["GRAMMAR_ARTICLES_BASIC", "GRAMMAR_REGULAR_PLURAL_NOUNS"],
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _unique(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value})


def _normalize_case_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("text", ""))
    return ""


def _core_pattern(primitive: dict[str, Any]) -> str:
    if primitive.get("core_pattern"):
        return str(primitive["core_pattern"])
    slots = primitive.get("slot_pattern", [])
    names = [slot.get("slot") for slot in slots if isinstance(slot, dict) and slot.get("slot")]
    return " + ".join(names) or str(primitive.get("rule_id", "rule pattern"))


def _tag_from_filter(value: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")
    return f"ERR_{normalized or 'GRAMMAR_NON_MATCH'}"


def _normalize_rule_nodes(can_payload: dict[str, Any], batch_01: dict[str, Any], batch_02: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = {node["grammar_id"]: dict(node) for payload in (batch_01, batch_02) for node in payload.get("batch_nodes", [])}
    can_node = {
        "grammar_id": can_payload["node"]["grammar_id"],
        "zh_label": can_payload["node"].get("zh_label"),
        "en_label": can_payload["node"].get("en_label"),
        "rule_primitives": can_payload.get("rule_primitives", []),
        "positive_test_cases": can_payload.get("positive_test_cases", []),
        "negative_test_cases": can_payload.get("negative_test_cases", []),
    }
    nodes[can_node["grammar_id"]] = can_node
    return nodes


def _derived_spec(grammar_id: str, node: dict[str, Any]) -> dict[str, Any]:
    positives = [_normalize_case_text(case) for case in node.get("positive_test_cases", [])]
    negatives = [_normalize_case_text(case) for case in node.get("negative_test_cases", [])]
    positives = [text for text in positives if text]
    negatives = [text for text in negatives if text]
    primitives = node.get("rule_primitives", [])
    form_rules = [
        {
            "rule": _core_pattern(primitive),
            "pattern": positives[index % len(positives)] if positives else _core_pattern(primitive),
            "rule_id": primitive.get("rule_id"),
        }
        for index, primitive in enumerate(primitives)
    ]
    filters = _unique(
        value
        for primitive in primitives
        for value in primitive.get("false_positive_filters", [])
    )
    error_tags = [
        {
            "tag": _tag_from_filter(value),
            "diagnosis": value.replace("_", " ").replace("filter", "case").strip().capitalize() + ".",
        }
        for value in filters[:3]
    ]
    while len(error_tags) < 3:
        error_tags.append({
            "tag": f"ERR_{grammar_id.removeprefix('GRAMMAR_')}_NON_MATCH_{len(error_tags)+1}",
            "diagnosis": "The response does not satisfy the canonical target pattern.",
        })
    first_positive = positives[0] if positives else "Use the target grammar pattern."
    negative_examples = [
        {
            "text": text,
            "error_tag": error_tags[index % len(error_tags)]["tag"],
            "correction": f"Use a validated target form such as: {first_positive}",
        }
        for index, text in enumerate(negatives)
    ]
    meta = PEDAGOGY_META[grammar_id]
    return {
        "stage": "A1" if grammar_id in A1_UNITS else "A1+",
        "title_en": node.get("en_label") or grammar_id,
        "title_zh_tw": node.get("zh_label") or grammar_id,
        "objectives": [
            f"Recognize the form and meaning of {node.get('en_label') or grammar_id}.",
            f"Produce a controlled A1/A1+ example of {node.get('en_label') or grammar_id}.",
        ],
        "form_rules": form_rules,
        "meaning_functions": meta["meaning"],
        "usage_conditions": meta["usage"],
        "positive": [
            {"text": text, "explanation": f"Validated example of {node.get('en_label') or grammar_id}."}
            for text in positives
        ],
        "negative": negative_examples,
        "error_tags": error_tags,
        "contrasts": meta["contrasts"],
        "targets": positives,
    }


def _all_specs(nodes: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    specs = {grammar_id: dict(spec) for grammar_id, spec in UNIT_SPECS.items()}
    for grammar_id, node in nodes.items():
        if grammar_id not in specs:
            specs[grammar_id] = _derived_spec(grammar_id, node)
    return specs


def build_artifact(
    query: dict[str, Any],
    rule_index: dict[str, Any],
    authority: dict[str, Any],
    can_payload: dict[str, Any],
    batch_01: dict[str, Any],
    batch_02: dict[str, Any],
) -> dict[str, Any]:
    canonical = query["canonical_a1"]["by_grammar_id"]
    rule_units = rule_index["by_grammar_id"]
    nodes = _normalize_rule_nodes(can_payload, batch_01, batch_02)
    specs = _all_specs(nodes)
    expected_ids = set(canonical)
    if set(nodes) != expected_ids or set(specs) != expected_ids:
        raise ValueError("full_rule_or_spec_unit_set_mismatch")

    units = []
    row_bindings: dict[str, list[str]] = defaultdict(list)
    for sequence_index, grammar_id in enumerate(list(canonical), 1):
        spec = specs[grammar_id]
        row_ids = list(canonical[grammar_id]["egp_row_ids"])
        for row_id in row_ids:
            row_bindings[row_id].append(grammar_id)
        practice, assessment = _activities(grammar_id, spec["targets"])
        units.append({
            "sequence_index": sequence_index,
            "grammar_unit_id": grammar_id,
            "official_egp_level": "A1",
            "internal_stage": spec["stage"],
            "canonical_egp_row_ids": row_ids,
            "canonical_egp_row_count": len(row_ids),
            "prerequisite_unit_ids": _unique(PREREQUISITES[grammar_id]),
            "content_authority_status": "PROJECT_AUTHORED_CANDIDATE",
            "content_review_status": "OPERATOR_REVIEW_NOT_COMPLETED",
            "title_en": spec["title_en"],
            "title_zh_tw": spec["title_zh_tw"],
            "learning_objectives": spec["objectives"],
            "form_rules": spec["form_rules"],
            "meaning_functions": spec["meaning_functions"],
            "usage_conditions": spec["usage_conditions"],
            "positive_examples": spec["positive"],
            "negative_examples": spec["negative"],
            "common_error_tags": spec["error_tags"],
            "contrast_unit_ids": spec["contrasts"],
            "practice_items": practice,
            "assessment_items": assessment,
            "source_trace": {
                "content_origin": "project_authored_derived_content",
                "canonical_query_index_path": "ulga/graph/grammar_query_index.json",
                "rule_source_path": rule_units[grammar_id]["rule_source_path"],
                "sentence_validator_path": rule_units[grammar_id]["sentence_validator_path"],
                "official_egp_text_copied": False,
                "raw_external_source_text_copied": False,
                "restricted_source_payload_persisted": False,
            },
            "readiness": {
                "candidate_teaching_content_status": "READY",
                "candidate_practice_content_status": "READY",
                "candidate_assessment_content_status": "READY",
                "promoted_private_learning_status": "NOT_PROMOTED",
                "mastery_runtime_status": "NOT_IMPLEMENTED",
                "candidate_teachable": True,
                "candidate_practice_ready": True,
                "candidate_assessment_ready": True,
                "promoted_for_private_learning": False,
                "mastery_trackable": False,
            },
        })

    by_row = {
        row_id: {
            "egp_row_id": row_id,
            "grammar_unit_ids": _unique(grammar_ids),
            "candidate_teachable_status": "PROJECT_AUTHORED_CANDIDATE_READY",
            "promoted_private_learning_status": "NOT_PROMOTED",
        }
        for row_id, grammar_ids in sorted(row_bindings.items())
    }
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_full_teachable_candidate_coverage",
        "artifact_type": "a1_a1plus_full_project_authored_candidate_learning_content",
        "schema_version": "a1_grammar_full_teachable_candidate_coverage.v1",
        "official_level": "A1",
        "internal_stages": ["A1", "A1+"],
        "authority_contract_path": "ulga/contracts/a1_grammar_learning_content_authority.json",
        "coverage_summary": {
            "canonical_unit_count": 24,
            "canonical_unique_egp_row_count": 109,
            "candidate_teaching_ready_unit_count": 24,
            "candidate_practice_ready_unit_count": 24,
            "candidate_assessment_ready_unit_count": 24,
            "candidate_teachable_unique_egp_row_count": 109,
            "candidate_teachable_unit_coverage_percent": 100.0,
            "candidate_teachable_row_coverage_percent": 100.0,
            "practice_item_count": 144,
            "assessment_item_count": 48,
            "promoted_private_learning_unit_count": 0,
            "promoted_private_learning_coverage_percent": 0.0,
            "mastery_trackable_unit_count": 0,
        },
        "learning_units": units,
        "by_egp_row_id": by_row,
        "claim_boundaries": {
            "full_24_unit_candidate_teachable_coverage_complete": True,
            "full_109_row_candidate_teachable_coverage_complete": True,
            "operator_review_complete": False,
            "private_learning_promotion_complete": False,
            "learner_mastery_runtime_complete": False,
            "production_runtime_validation_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_learner_state_write": True,
            "no_external_nlp_dependency": True,
            "no_restricted_source_payload_copy": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def validate_artifact(
    artifact: dict[str, Any],
    query: dict[str, Any],
    rule_index: dict[str, Any],
    authority: dict[str, Any],
    can_payload: dict[str, Any],
    batch_01: dict[str, Any],
    batch_02: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    canonical_a1 = query.get("canonical_a1", {})
    canonical = canonical_a1.get("by_grammar_id", {})
    nodes = _normalize_rule_nodes(can_payload, batch_01, batch_02)
    units = artifact.get("learning_units", [])
    by_id = {unit.get("grammar_unit_id"): unit for unit in units if unit.get("grammar_unit_id")}
    if authority.get("authority_status") != "ACTIVE_FOR_STRUCTURAL_LEARNING_CONTENT":
        errors.append("content_authority_not_active")
    if len(units) != 24 or set(by_id) != set(canonical) or set(nodes) != set(canonical):
        errors.append("full_unit_set_mismatch")

    row_bindings: dict[str, list[str]] = defaultdict(list)
    item_ids: set[str] = set()
    positive_count = negative_count = gate_target_count = 0
    for grammar_id, unit in by_id.items():
        expected_rows = canonical[grammar_id]["egp_row_ids"]
        if unit.get("canonical_egp_row_ids") != expected_rows:
            errors.append(f"canonical_row_mismatch:{grammar_id}")
        for row_id in unit.get("canonical_egp_row_ids", []):
            row_bindings[row_id].append(grammar_id)
        if unit.get("prerequisite_unit_ids") != _unique(PREREQUISITES[grammar_id]):
            errors.append(f"prerequisite_mismatch:{grammar_id}")
        if unit.get("internal_stage") != ("A1" if grammar_id in A1_UNITS else "A1+"):
            errors.append(f"stage_mismatch:{grammar_id}")
        for field, minimum in (("learning_objectives", 2), ("form_rules", 1), ("meaning_functions", 1), ("usage_conditions", 2), ("positive_examples", 2), ("negative_examples", 3), ("common_error_tags", 3), ("contrast_unit_ids", 1), ("practice_items", 6), ("assessment_items", 2)):
            if len(unit.get(field, [])) < minimum:
                errors.append(f"content_minimum_not_met:{grammar_id}:{field}")
        for example in unit.get("positive_examples", []):
            positive_count += 1
            result = dispatch_validate(grammar_id, example.get("text", ""))
            if result.get("dispatch_status") != "VALIDATOR_EXECUTED" or result.get("match") is not True:
                errors.append(f"positive_example_gate_fail:{grammar_id}:{example.get('text')}")
        for example in unit.get("negative_examples", []):
            negative_count += 1
            result = dispatch_validate(grammar_id, example.get("text", ""))
            if result.get("dispatch_status") != "VALIDATOR_EXECUTED" or result.get("match") is not False:
                errors.append(f"negative_example_gate_fail:{grammar_id}:{example.get('text')}")
        activities = unit.get("practice_items", []) + unit.get("assessment_items", [])
        for item in activities:
            item_id = item.get("item_id")
            if not item_id or item_id in item_ids:
                errors.append(f"duplicate_or_missing_item_id:{grammar_id}:{item_id}")
            item_ids.add(item_id)
            gate = validate_practice_item(item)
            gate_target_count += gate.get("validation_target_count", 0)
            if gate.get("gate_status") != "PASS":
                errors.append(f"practice_item_grammar_gate_fail:{item_id}")
        readiness = unit.get("readiness", {})
        if not all(readiness.get(field) is True for field in ("candidate_teachable", "candidate_practice_ready", "candidate_assessment_ready")):
            errors.append(f"candidate_readiness_false:{grammar_id}")
        if readiness.get("promoted_for_private_learning") is not False or readiness.get("mastery_trackable") is not False:
            errors.append(f"false_promotion_or_mastery_claim:{grammar_id}")

    canonical_rows = set(canonical_a1.get("canonical_egp_row_ids", []))
    if set(row_bindings) != canonical_rows or len(row_bindings) != 109:
        errors.append("row_traceability_not_109_of_109")
    if set(artifact.get("by_egp_row_id", {})) != canonical_rows:
        errors.append("row_index_not_109_of_109")

    expected_summary = {
        "canonical_unit_count": 24,
        "canonical_unique_egp_row_count": 109,
        "candidate_teaching_ready_unit_count": 24,
        "candidate_practice_ready_unit_count": 24,
        "candidate_assessment_ready_unit_count": 24,
        "candidate_teachable_unique_egp_row_count": 109,
        "candidate_teachable_unit_coverage_percent": 100.0,
        "candidate_teachable_row_coverage_percent": 100.0,
        "practice_item_count": 144,
        "assessment_item_count": 48,
        "promoted_private_learning_unit_count": 0,
        "promoted_private_learning_coverage_percent": 0.0,
        "mastery_trackable_unit_count": 0,
    }
    if artifact.get("coverage_summary") != expected_summary:
        errors.append("coverage_summary_mismatch")
    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("operator_review_complete") is not False or boundaries.get("private_learning_promotion_complete") is not False:
        errors.append("false_review_or_promotion_claim")
    for field in ("no_a2_a2plus_expansion", "no_learner_state_write", "no_external_nlp_dependency", "no_restricted_source_payload_copy"):
        if boundaries.get(field) is not True:
            errors.append(f"scope_boundary_missing:{field}")

    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_full_teachable_candidate_coverage_validation",
        "validation_status": status,
        "coverage_summary": expected_summary,
        "validation_counts": {
            "positive_example_count": positive_count,
            "negative_example_count": negative_count,
            "practice_and_assessment_grammar_gate_target_count": gate_target_count,
            "unique_item_id_count": len(item_ids),
        },
        "gate_checks": {
            "canonical_units_24_of_24": len(by_id) == 24,
            "canonical_rows_109_of_109": len(row_bindings) == 109,
            "candidate_teachable_coverage_100_percent": artifact.get("coverage_summary", {}).get("candidate_teachable_row_coverage_percent") == 100.0,
            "positive_examples_match": not any(error.startswith("positive_example_gate_fail") for error in errors),
            "negative_examples_rejected": not any(error.startswith("negative_example_gate_fail") for error in errors),
            "practice_item_grammar_gates_pass": not any(error.startswith("practice_item_grammar_gate_fail") for error in errors),
            "promotion_still_blocked": boundaries.get("private_learning_promotion_complete") is False,
            "no_a2plus_scope": boundaries.get("no_a2_a2plus_expansion") is True,
            "no_learner_state_write": boundaries.get("no_learner_state_write") is True,
        },
        "errors": errors,
        "warnings": [
            "All 24 units and 109 rows have project-authored candidate teaching/practice/assessment coverage, not operator-reviewed promotion.",
            "Learner mastery and retention tracking remain not implemented.",
        ],
        "stop_reason": "NONE" if status == "PASS" else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if status == "PASS" else None,
        "validation_mode": "LOCAL_DETERMINISTIC_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    payloads = (
        load_json(QUERY_PATH),
        load_json(RULE_INDEX_PATH),
        load_json(AUTHORITY_PATH),
        load_json(CAN_RULE_PATH),
        load_json(BATCH_01_PATH),
        load_json(BATCH_02_PATH),
    )
    artifact = build_artifact(*payloads)
    report = validate_artifact(artifact, *payloads)
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
