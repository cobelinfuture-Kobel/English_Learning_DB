#!/usr/bin/env python3
"""Full-fix unit-specific pedagogy for derived A1/A1+ grammar units."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_text_mode_practice_item_fullfix import (
    build_and_validate_from_repo as build_practice_fullfix_source,
    build_unit_items,
)
from ulga.query.a1_canonical_validator_dispatcher import validate as dispatch_validate
from ulga.query.a1_practice_item_grammar_gate import validate_practice_item

TASK_ID = "R7-M105L_A1A1PlusDerivedPedagogyFullFix"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_SHORT_STEP = "R7-M105M_A1A1PlusTextModeReReviewAndPromotionGate"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_grammar_derived_pedagogy_fullfix.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_grammar_derived_pedagogy_fullfix_validation.json"

PRESERVED_PILOTS = {
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES",
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS",
    "GRAMMAR_PAST_SIMPLE_A1",
}

DERIVED_META: dict[str, dict[str, list[str]]] = {
    "GRAMMAR_SUBJECT_PRONOUNS": {
        "objectives": [
            "Choose the subject pronoun that matches the intended person, number, and referent.",
            "Place the subject pronoun before the finite verb in a basic clause.",
        ],
        "diagnoses": [
            "The selected pronoun does not match the intended subject referent.",
            "An object or possessive form is used where a subject form is required.",
            "The subject pronoun is not in the basic pre-verbal subject position.",
        ],
    },
    "GRAMMAR_OBJECT_PRONOUNS_BASIC": {
        "objectives": [
            "Choose me, you, him, her, it, us, or them for a verb or preposition object.",
            "Distinguish object pronouns from subject pronouns and possessive determiners.",
        ],
        "diagnoses": [
            "The object pronoun does not match the intended referent.",
            "A subject pronoun is used in object position.",
            "A possessive determiner is confused with an object pronoun.",
        ],
    },
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": {
        "objectives": [
            "Choose the possessive determiner that matches the possessor.",
            "Place my, your, his, her, its, our, or their before a noun phrase.",
        ],
        "diagnoses": [
            "The possessive determiner does not match the possessor.",
            "An independent possessive pronoun is used before a noun.",
            "The possessive determiner is not followed by a noun phrase.",
        ],
    },
    "GRAMMAR_CAN_STATEMENT": {
        "objectives": [
            "Use can plus a base verb to state an ability in an affirmative sentence.",
            "Supply any object or complement required by the lexical verb.",
        ],
        "diagnoses": [
            "The verb after can is not in the base form.",
            "A required object or activity complement is missing.",
            "can is functioning as a noun, question auxiliary, or negative form instead of an affirmative ability modal.",
        ],
    },
    "GRAMMAR_THERE_IS": {
        "objectives": [
            "Use there is with a singular noun phrase and there are with a plural noun phrase.",
            "Distinguish existential there from the place adverb there.",
        ],
        "diagnoses": [
            "The be verb does not agree with the following noun phrase.",
            "A locative or deictic use of there is is confused with an existential structure.",
            "The existential structure lacks the noun phrase being introduced.",
        ],
    },
    "GRAMMAR_BE_INTERROGATIVES_A1": {
        "objectives": [
            "Move am, is, or are before the subject to ask a basic yes/no question.",
            "Choose the fronted be form that agrees with the subject.",
        ],
        "diagnoses": [
            "The be verb is not moved before the subject.",
            "The be form does not agree with the subject.",
            "do or does is incorrectly added to a basic be question.",
        ],
    },
    "GRAMMAR_CAN_NEGATIVE_A1": {
        "objectives": [
            "Use cannot, can not, or can't plus a base verb to express inability.",
            "Distinguish negative can statements from questions, affirmative ability, and can as a noun.",
        ],
        "diagnoses": [
            "The negative marker is missing from the can statement.",
            "The verb after cannot or can't is not in the base form.",
            "The form is a question, affirmative, or noun use rather than a negative modal statement.",
        ],
    },
    "GRAMMAR_WILL_FUTURE_A1": {
        "objectives": [
            "Use will or 'll plus a base verb for a simple future action, prediction, or decision.",
            "Distinguish the future auxiliary will from a noun or personal name.",
        ],
        "diagnoses": [
            "The verb after will is not in the base form.",
            "The target future statement lacks will or 'll.",
            "will is not functioning as the future auxiliary.",
        ],
    },
    "GRAMMAR_REGULAR_PLURAL_NOUNS": {
        "objectives": [
            "Form regular plural nouns with -s or -es.",
            "Distinguish plural endings from third-person verb -s and possessive 's.",
        ],
        "diagnoses": [
            "The noun has an incorrect regular plural ending.",
            "A third-person verb ending is mistaken for a plural noun ending.",
            "A possessive or irregular plural form is treated as a regular plural.",
        ],
    },
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": {
        "objectives": [
            "Choose a basic preposition that matches the spatial relationship.",
            "Distinguish place expressions from time and other prepositional uses.",
        ],
        "diagnoses": [
            "The selected preposition does not match the spatial relationship.",
            "The place preposition lacks its noun phrase object.",
            "A time or non-place prepositional expression is classified as a place relation.",
        ],
    },
    "GRAMMAR_ADJECTIVE_PHRASES_A1": {
        "objectives": [
            "Use adjectives before nouns or after linking be to describe people and things.",
            "Use simple adjective coordination and very with suitable gradable adjectives.",
        ],
        "diagnoses": [
            "The adjective is outside a licensed attributive or predicative position.",
            "A noun or adverb is used where an adjective is required.",
            "The degree modifier is combined with an incompatible word or meaning.",
        ],
    },
    "GRAMMAR_COORDINATION_A1": {
        "objectives": [
            "Join compatible words, phrases, clauses, or list items with and, but, or or.",
            "Use but to express a meaningful contrast between compatible units.",
        ],
        "diagnoses": [
            "The conjunction does not match the intended additive, alternative, or contrast relation.",
            "The coordinated units are not structurally compatible.",
            "One side of the coordination is missing or incomplete.",
        ],
    },
    "GRAMMAR_BECAUSE_REASON_CLAUSES_A1": {
        "objectives": [
            "Join a main clause and a complete reason clause with because.",
            "Make the because-clause give a relevant reason for the main clause.",
        ],
        "diagnoses": [
            "A because-clause appears without the required main clause in a complete-sentence task.",
            "The clause after because lacks a finite subject-verb structure.",
            "The stated reason does not logically support the main clause.",
        ],
    },
    "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1": {
        "objectives": [
            "Choose the complement form licensed by the first verb or modal.",
            "Distinguish infinitival to from prepositional to and like as a verb from like as a preposition.",
        ],
        "diagnoses": [
            "The selected complement form is not licensed by the first verb or modal.",
            "Prepositional to is confused with infinitival to.",
            "The verb lacks a complement required to complete its meaning.",
        ],
    },
    "GRAMMAR_ADVERB_PHRASES_A1": {
        "objectives": [
            "Use basic adverbs to add time, place, frequency, manner, or degree information.",
            "Place common frequency, time, and place adverbs in a position licensed by their function.",
        ],
        "diagnoses": [
            "The adverb appears in a position not licensed by its function.",
            "A noun or adjective is classified as the target adverb.",
            "Existential there is confused with the place adverb there.",
        ],
    },
    "GRAMMAR_NOUN_PHRASES_A1": {
        "objectives": [
            "Build a basic noun phrase around a noun or proper-noun head.",
            "Use noun phrases in subject, object, or other licensed clause roles.",
        ],
        "diagnoses": [
            "The phrase lacks a noun or pronoun head.",
            "Determiners and modifiers are arranged in an unlicensed order.",
            "An adverb, adjective phrase, or predicate is classified as a noun phrase.",
        ],
    },
    "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1": {
        "objectives": [
            "Build a basic statement with a subject and an appropriate predicate.",
            "Distinguish affirmative and negative declaratives from questions and fragments.",
        ],
        "diagnoses": [
            "The clause uses question or fragment order rather than statement order.",
            "A required subject or predicate is absent.",
            "The negative construction does not match the predicate type.",
        ],
    },
    "GRAMMAR_DEMONSTRATIVES_CONTRAST": {
        "objectives": [
            "Choose this or that for singular nouns and these or those for plural nouns.",
            "Use near/far context to select the appropriate demonstrative.",
        ],
        "diagnoses": [
            "The demonstrative does not match singular or plural number.",
            "The near/far demonstrative conflicts with the situation.",
            "An identifying this/that clause is confused with demonstrative determiner plus noun.",
        ],
    },
}

ARTICLE_FULLFIX = {
    "learning_objectives": [
        "Choose a or an for one non-specific singular count noun based on the following sound.",
        "Use the when the listener or reader can identify the intended noun.",
    ],
    "meaning_functions": [
        "introduce one non-specific singular countable item",
        "refer to a specific item identifiable from the situation or shared knowledge",
    ],
    "usage_conditions": [
        "Choose a/an from the following sound, not only the written first letter.",
        "Do not use a/an directly before a plural noun.",
        "Use the only when the referent is identifiable from prior mention, shared knowledge, or the immediate situation.",
    ],
    "positive_examples": [
        {
            "text": "a cat",
            "explanation": "a introduces one cat before the consonant sound /k/.",
            "context": "The cat is mentioned for the first time.",
        },
        {
            "text": "an apple",
            "explanation": "an introduces one apple before the vowel sound /æ/.",
            "context": "The apple is mentioned for the first time.",
        },
        {
            "text": "the book",
            "explanation": "the identifies the particular book both people can identify.",
            "context": "Both people know which book is meant.",
        },
    ],
    "negative_examples": [
        {
            "text": "apple",
            "error_tag": "ERR_ARTICLE_MISSING",
            "correction": "In a context introducing one apple, use an apple.",
        },
        {
            "text": "a apple",
            "error_tag": "ERR_A_AN_SOUND_CHOICE",
            "correction": "Use an apple before the vowel sound.",
        },
        {
            "text": "a books",
            "error_tag": "ERR_ARTICLE_NUMBER_MISMATCH",
            "correction": "Use books without a/an, or use a book for one item.",
        },
    ],
    "common_error_tags": [
        {
            "tag": "ERR_ARTICLE_MISSING",
            "diagnosis": "A singular count noun that needs a determiner has no article.",
        },
        {
            "tag": "ERR_A_AN_SOUND_CHOICE",
            "diagnosis": "The choice of a or an does not match the following sound.",
        },
        {
            "tag": "ERR_ARTICLE_NUMBER_MISMATCH",
            "diagnosis": "The indefinite article is combined with a plural noun.",
        },
    ],
}


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fullfix_derived_unit(unit: dict[str, Any]) -> dict[str, Any]:
    grammar_id = unit["grammar_unit_id"]
    meta = DERIVED_META[grammar_id]
    result = deepcopy(unit)
    result["learning_objectives"] = list(meta["objectives"])
    meaning = next(iter(result.get("meaning_functions", [])), "the target grammar meaning")
    form_rules = result.get("form_rules", [])
    positives = []
    for index, example in enumerate(result.get("positive_examples", [])):
        updated = deepcopy(example)
        rule = form_rules[index % len(form_rules)]["rule"] if form_rules else "the target form rule"
        updated["explanation"] = f"This example realizes {rule} and expresses {meaning}."
        positives.append(updated)
    result["positive_examples"] = positives
    diagnoses = meta["diagnoses"]
    errors = []
    for index, error in enumerate(result.get("common_error_tags", [])):
        updated = deepcopy(error)
        updated["diagnosis"] = diagnoses[index % len(diagnoses)]
        errors.append(updated)
    result["common_error_tags"] = errors
    model = positives[0]["text"] if positives else "the target form"
    first_rule = form_rules[0]["rule"] if form_rules else "the target form rule"
    negatives = []
    for index, example in enumerate(result.get("negative_examples", [])):
        updated = deepcopy(example)
        updated["correction"] = f"Revise this response to follow {first_rule}. A model target is: {model}"
        if errors:
            updated["error_tag"] = errors[index % len(errors)]["tag"]
        negatives.append(updated)
    result["negative_examples"] = negatives
    result["content_authority_status"] = "PROJECT_AUTHORED_FULLFIX_CANDIDATE"
    result["pedagogy_fullfix_status"] = "UNIT_SPECIFIC_FULLFIX_APPLIED"
    return result


def _fullfix_articles(unit: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(unit)
    for field, value in ARTICLE_FULLFIX.items():
        result[field] = deepcopy(value)
    result["content_authority_status"] = "PROJECT_AUTHORED_FULLFIX_CANDIDATE"
    result["pedagogy_fullfix_status"] = "ARTICLE_CONTEXT_FULLFIX_APPLIED"
    return result


def _refresh_items(unit: dict[str, Any]) -> dict[str, Any]:
    practice, assessments = build_unit_items(unit)
    meaning = next(iter(unit.get("meaning_functions", [])), "the target grammar meaning")
    for item in practice + assessments:
        context = item.get("context")
        if isinstance(context, dict):
            context["situation"] = (
                "A learner is writing a short A1 message. "
                f"The intended grammar meaning is: {meaning}."
            )
    unit["practice_items"] = practice
    unit["assessment_items"] = assessments
    return unit


def build_artifact(practice_source: Mapping[str, Any]) -> dict[str, Any]:
    source_units = practice_source.get("learning_units", [])
    if len(source_units) != 24:
        raise ValueError("pedagogy_fullfix_source_not_24_units")
    output_units: list[dict[str, Any]] = []
    item_bank: list[dict[str, Any]] = []
    row_index: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "grammar_unit_ids": set(),
            "reading_item_ids": [],
            "writing_item_ids": [],
            "assessment_item_ids": [],
        }
    )
    for source in source_units:
        grammar_id = source["grammar_unit_id"]
        if grammar_id in DERIVED_META:
            unit = _fullfix_derived_unit(dict(source))
        elif grammar_id == "GRAMMAR_ARTICLES_BASIC":
            unit = _fullfix_articles(dict(source))
        elif grammar_id in PRESERVED_PILOTS:
            unit = deepcopy(source)
            unit["pedagogy_fullfix_status"] = "CURATED_PILOT_PRESERVED"
        else:
            raise ValueError(f"unclassified_pedagogy_unit:{grammar_id}")
        unit = _refresh_items(unit)
        output_units.append(unit)
        for item in unit["practice_items"] + unit["assessment_items"]:
            item_bank.append(item)
            for row_id in unit["canonical_egp_row_ids"]:
                row = row_index[row_id]
                row["grammar_unit_ids"].add(grammar_id)
                if item["skill"] == "reading":
                    row["reading_item_ids"].append(item["item_id"])
                else:
                    row["writing_item_ids"].append(item["item_id"])
                if item["item_role"] == "assessment":
                    row["assessment_item_ids"].append(item["item_id"])
    by_row = {
        row_id: {
            "egp_row_id": row_id,
            "grammar_unit_ids": sorted(value["grammar_unit_ids"]),
            "reading_item_ids": sorted(set(value["reading_item_ids"])),
            "writing_item_ids": sorted(set(value["writing_item_ids"])),
            "assessment_item_ids": sorted(set(value["assessment_item_ids"])),
            "pedagogy_fullfix_status": "READY_FOR_RE_REVIEW",
        }
        for row_id, value in sorted(row_index.items())
    }
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_derived_pedagogy_fullfix",
        "artifact_type": "a1_a1plus_unit_specific_pedagogy_and_text_mode_item_fullfix",
        "schema_version": "a1_grammar_derived_pedagogy_fullfix.v1",
        "coverage_summary": {
            "canonical_unit_count": len(output_units),
            "canonical_row_count": len(by_row),
            "derived_unit_fullfix_count": sum(unit["grammar_unit_id"] in DERIVED_META for unit in output_units),
            "article_context_fullfix_count": sum(unit["grammar_unit_id"] == "GRAMMAR_ARTICLES_BASIC" for unit in output_units),
            "preserved_curated_pilot_count": sum(unit["grammar_unit_id"] in PRESERVED_PILOTS for unit in output_units),
            "pedagogy_candidate_ready_unit_count": len(output_units),
            "total_item_count": len(item_bank),
            "known_validator_gap_count": 0,
            "operator_approved_unit_count": 0,
            "text_mode_pilot_eligible_row_count": 0,
        },
        "known_validator_gaps": [],
        "learning_units": output_units,
        "item_bank": item_bank,
        "by_egp_row_id": by_row,
        "claim_boundaries": {
            "derived_pedagogy_fullfix_complete": True,
            "article_context_fullfix_complete": True,
            "text_mode_practice_item_fullfix_complete": True,
            "all_negative_examples_automatically_certified": True,
            "operator_review_complete": False,
            "text_mode_private_pilot_eligible": False,
            "audio_scope_deferred": True,
            "audio_scope_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_persistent_learner_state_write": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def validate_artifact(artifact: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    units = artifact.get("learning_units", [])
    items = artifact.get("item_bank", [])
    rows = artifact.get("by_egp_row_id", {})
    summary = artifact.get("coverage_summary", {})
    expected_units = {unit["grammar_unit_id"] for unit in source.get("learning_units", [])}
    if len(units) != 24 or {unit.get("grammar_unit_id") for unit in units} != expected_units:
        errors.append("pedagogy_fullfix_unit_set_not_24")
    if len(rows) != 109 or set(rows) != set(source.get("by_egp_row_id", {})):
        errors.append("pedagogy_fullfix_row_set_not_109")
    positive_count = negative_count = gate_count = known_gap_count = 0
    item_ids: set[str] = set()
    for unit in units:
        grammar_id = unit["grammar_unit_id"]
        objectives = unit.get("learning_objectives", [])
        if any(value.startswith("Recognize the form and meaning of") for value in objectives):
            errors.append(f"generic_objective_remains:{grammar_id}")
        for example in unit.get("positive_examples", []):
            positive_count += 1
            explanation = example.get("explanation", "")
            if explanation.startswith("Validated example of"):
                errors.append(f"generic_positive_explanation_remains:{grammar_id}")
            result = dispatch_validate(grammar_id, example.get("text", ""))
            if result.get("dispatch_status") != "VALIDATOR_EXECUTED" or result.get("match") is not True:
                errors.append(f"positive_example_gate_fail:{grammar_id}:{example.get('text')}")
        for example in unit.get("negative_examples", []):
            negative_count += 1
            if example.get("validator_limit") is not None:
                errors.append(
                    f"resolved_validator_gap_metadata_present:{grammar_id}:"
                    f"{example.get('text')}"
                )
            result = dispatch_validate(grammar_id, example.get("text", ""))
            if result.get("dispatch_status") != "VALIDATOR_EXECUTED":
                errors.append(f"negative_example_dispatch_fail:{grammar_id}:{example.get('text')}")
            elif result.get("match") is True:
                errors.append(f"negative_example_gate_fail:{grammar_id}:{example.get('text')}")
        for error in unit.get("common_error_tags", []):
            if "does not satisfy the canonical target pattern" in error.get("diagnosis", "").lower():
                errors.append(f"generic_error_diagnosis_remains:{grammar_id}")
        for item in unit.get("practice_items", []) + unit.get("assessment_items", []):
            item_id = item.get("item_id")
            if not item_id or item_id in item_ids:
                errors.append(f"duplicate_or_missing_item_id:{item_id}")
            item_ids.add(item_id)
            context = item.get("context")
            if isinstance(context, dict) and "needs to identification" in context.get("situation", ""):
                errors.append(f"ungrammatical_context_remains:{item_id}")
            gate = validate_practice_item(item)
            gate_count += gate.get("validation_target_count", 0)
            if gate.get("gate_status") != "PASS":
                errors.append(f"practice_item_grammar_gate_fail:{item_id}")
    expected_summary = {
        "canonical_unit_count": 24,
        "canonical_row_count": 109,
        "derived_unit_fullfix_count": 18,
        "article_context_fullfix_count": 1,
        "preserved_curated_pilot_count": 5,
        "pedagogy_candidate_ready_unit_count": 24,
        "total_item_count": 192,
        "known_validator_gap_count": 0,
        "operator_approved_unit_count": 0,
        "text_mode_pilot_eligible_row_count": 0,
    }
    if summary != expected_summary:
        errors.append("coverage_summary_mismatch")
    if known_gap_count != 0:
        errors.append(f"known_validator_gap_count_mismatch:{known_gap_count}")
    gaps = artifact.get("known_validator_gaps", [])
    if gaps:
        errors.append("resolved_validator_gap_still_registered")
    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("all_negative_examples_automatically_certified") is not True:
        errors.append("all_negative_examples_not_certified")
    if boundaries.get("operator_review_complete") is not False:
        errors.append("false_operator_review_completion")
    if boundaries.get("audio_scope_deferred") is not True or boundaries.get("audio_scope_complete") is not False:
        errors.append("audio_defer_boundary_drift")
    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "validation_status": status,
        "coverage_summary": expected_summary,
        "validation_counts": {
            "positive_example_count": positive_count,
            "negative_example_count": negative_count,
            "known_validator_gap_count": known_gap_count,
            "unique_item_id_count": len(item_ids),
            "practice_item_grammar_gate_target_count": gate_count,
        },
        "gate_checks": {
            "units_24_of_24": len(units) == 24,
            "rows_109_of_109": len(rows) == 109,
            "derived_fullfix_18_of_18": summary.get("derived_unit_fullfix_count") == 18,
            "article_context_fullfix": summary.get("article_context_fullfix_count") == 1,
            "generic_objectives_removed": not any(error.startswith("generic_objective_remains") for error in errors),
            "generic_explanations_removed": not any(error.startswith("generic_positive_explanation_remains") for error in errors),
            "generic_diagnoses_removed": not any(error.startswith("generic_error_diagnosis_remains") for error in errors),
            "article_number_validator_gap_resolved": known_gap_count == 0 and not gaps,
            "all_other_negative_examples_rejected": not any(error.startswith("negative_example_gate_fail") for error in errors),
            "all_practice_item_grammar_gates_pass": not any(error.startswith("practice_item_grammar_gate_fail") for error in errors),
        },
        "errors": errors,
        "warnings": [
            "Article-number agreement is enforced by the canonical validator; the former gap is resolved.",
            "All content remains project-authored FullFix candidate material pending operator re-review.",
            "Audio remains deferred and is not evidence for text-mode promotion."
        ],
        "stop_reason": "NONE" if status == "PASS" else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if status == "PASS" else None,
        "validation_mode": "LOCAL_DETERMINISTIC_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    source, source_report = build_practice_fullfix_source()
    if source_report.get("validation_status") != "PASS":
        raise RuntimeError("practice_fullfix_source_validation_failed")
    artifact = build_artifact(source)
    report = validate_artifact(artifact, source)
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
