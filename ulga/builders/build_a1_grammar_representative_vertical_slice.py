#!/usr/bin/env python3
"""Build and validate the six-unit A1/A1+ grammar learning vertical slice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.query.a1_canonical_validator_dispatcher import validate as dispatch_validate
from ulga.query.a1_practice_item_grammar_gate import validate_practice_item

TASK_ID = "R7-M105B_A1GrammarRepresentativeVerticalSlice"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_SHORT_STEP = "R7-M105C_A1A1PlusFullTeachableCoverage"

QUERY_PATH = REPO_ROOT / "ulga/graph/grammar_query_index.json"
RULE_INDEX_PATH = REPO_ROOT / "ulga/graph/a1_canonical_rule_validator_index.json"
AUTHORITY_PATH = REPO_ROOT / "ulga/contracts/a1_grammar_learning_content_authority.json"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_grammar_representative_vertical_slice.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_grammar_representative_vertical_slice_validation.json"

PILOT_UNIT_IDS = (
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES",
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS",
    "GRAMMAR_PAST_SIMPLE_A1",
)

UNIT_SPECS: dict[str, dict[str, Any]] = {
    "GRAMMAR_BE_VERB_BASIC": {
        "stage": "A1",
        "title_en": "Basic be-verb statements",
        "title_zh_tw": "be 動詞基本陳述句",
        "objectives": [
            "Choose am, is, or are to agree with the subject.",
            "Use be to identify, describe, or locate a person or thing.",
        ],
        "form_rules": [
            {"rule": "I + am + complement", "pattern": "I am happy."},
            {"rule": "singular subject + is + complement", "pattern": "She is a student."},
            {"rule": "plural/you subject + are + complement", "pattern": "They are in the park."},
        ],
        "meaning_functions": ["identification", "description", "location/state"],
        "usage_conditions": [
            "Use be before a noun phrase, adjective phrase, or place phrase.",
            "Do not classify progressive be + -ing as this unit.",
        ],
        "positive": [
            {"text": "I am happy.", "explanation": "am agrees with I and links to an adjective."},
            {"text": "She is a student.", "explanation": "is agrees with a singular subject and identifies her."},
            {"text": "They are in the park.", "explanation": "are agrees with a plural subject and gives location."},
        ],
        "negative": [
            {"text": "She is playing.", "error_tag": "ERR_BE_PROGRESSIVE_NOT_COPULA", "correction": "Use this under present continuous, not basic copular be."},
            {"text": "I was happy.", "error_tag": "ERR_PAST_BE_OUT_OF_UNIT", "correction": "Use am for present basic be: I am happy."},
            {"text": "They play football.", "error_tag": "ERR_LEXICAL_VERB_NOT_BE", "correction": "This is a lexical present-simple statement."},
        ],
        "error_tags": [
            {"tag": "ERR_BE_SUBJECT_AGREEMENT", "diagnosis": "am/is/are does not agree with the subject."},
            {"tag": "ERR_BE_MISSING", "diagnosis": "The linking be verb is missing."},
            {"tag": "ERR_BE_EXTRA_LEXICAL_VERB", "diagnosis": "A basic be clause incorrectly combines be with a base lexical verb."},
        ],
        "contrasts": ["GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS", "GRAMMAR_BE_INTERROGATIVES_A1"],
        "targets": ["I am happy.", "She is a student.", "They are in the park."],
    },
    "GRAMMAR_ARTICLES_BASIC": {
        "stage": "A1",
        "title_en": "Basic articles a, an, and the",
        "title_zh_tw": "基本冠詞 a、an、the",
        "objectives": [
            "Use a or an before one non-specific singular count noun.",
            "Use the before a noun phrase when the referent is identifiable in context.",
        ],
        "form_rules": [
            {"rule": "a + singular count noun before a consonant sound", "pattern": "a cat"},
            {"rule": "an + singular count noun before a vowel sound", "pattern": "an apple"},
            {"rule": "the + identifiable noun phrase", "pattern": "the book"},
        ],
        "meaning_functions": ["introducing one non-specific item", "referring to an identifiable item"],
        "usage_conditions": [
            "Choose a/an by the following sound, not only the written letter.",
            "Do not use a/an directly before a plural noun.",
        ],
        "positive": [
            {"text": "a cat", "explanation": "a introduces one singular count noun before a consonant sound."},
            {"text": "an apple", "explanation": "an introduces one singular count noun before a vowel sound."},
            {"text": "the book", "explanation": "the marks an identifiable noun phrase."},
        ],
        "negative": [
            {"text": "apple", "error_tag": "ERR_ARTICLE_MISSING", "correction": "Use an apple when introducing one apple."},
            {"text": "two cats", "error_tag": "ERR_INDEFINITE_ARTICLE_WITH_PLURAL", "correction": "Do not add a/an before two cats."},
            {"text": "John", "error_tag": "ERR_ARTICLE_WITH_PROPER_NAME", "correction": "A basic personal proper name normally has no article."},
        ],
        "error_tags": [
            {"tag": "ERR_ARTICLE_MISSING", "diagnosis": "A required article is absent."},
            {"tag": "ERR_A_AN_SOUND_CHOICE", "diagnosis": "a/an does not match the following sound."},
            {"tag": "ERR_ARTICLE_NUMBER_MISMATCH", "diagnosis": "a/an is used with a plural noun."},
        ],
        "contrasts": ["GRAMMAR_REGULAR_PLURAL_NOUNS", "GRAMMAR_DEMONSTRATIVES_CONTRAST"],
        "targets": ["a cat", "an apple", "the book"],
    },
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS": {
        "stage": "A1",
        "title_en": "Present-simple affirmative statements",
        "title_zh_tw": "現在簡單式肯定句",
        "objectives": [
            "Use the present simple for routines, repeated actions, and simple facts.",
            "Apply third-person singular agreement in affirmative statements.",
        ],
        "form_rules": [
            {"rule": "I/you/we/they + base verb", "pattern": "They go to school."},
            {"rule": "he/she/it + third-person singular verb", "pattern": "She plays tennis."},
        ],
        "meaning_functions": ["routine", "habit", "simple fact or preference"],
        "usage_conditions": [
            "Use a lexical present verb, not be + -ing.",
            "Use -s/-es with a third-person singular subject in an affirmative statement.",
        ],
        "positive": [
            {"text": "I like apples.", "explanation": "I takes the base form like."},
            {"text": "She plays tennis.", "explanation": "She requires third-person singular plays."},
            {"text": "They go to school.", "explanation": "They takes the base form go."},
        ],
        "negative": [
            {"text": "She is playing tennis.", "error_tag": "ERR_PRESENT_CONTINUOUS_NOT_SIMPLE", "correction": "For a routine, use She plays tennis."},
            {"text": "I can swim.", "error_tag": "ERR_MODAL_NOT_PRESENT_SIMPLE_LEXICAL", "correction": "This belongs to the can statement unit."},
            {"text": "He played football.", "error_tag": "ERR_PAST_NOT_PRESENT", "correction": "For a present routine, use He plays football."},
        ],
        "error_tags": [
            {"tag": "ERR_THIRD_PERSON_S_MISSING", "diagnosis": "A third-person singular affirmative verb lacks -s/-es."},
            {"tag": "ERR_THIRD_PERSON_S_EXTRA", "diagnosis": "-s/-es is added with I/you/we/they."},
            {"tag": "ERR_TENSE_MISMATCH", "diagnosis": "The verb tense does not match the present routine/fact context."},
        ],
        "contrasts": ["GRAMMAR_BE_VERB_BASIC", "GRAMMAR_PRESENT_SIMPLE_NEGATIVES", "GRAMMAR_PAST_SIMPLE_A1"],
        "targets": ["I like apples.", "She plays tennis.", "They go to school."],
    },
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES": {
        "stage": "A1",
        "title_en": "Present-simple negative statements",
        "title_zh_tw": "現在簡單式否定句",
        "objectives": [
            "Use do not or does not to make a lexical present-simple statement negative.",
            "Use the base verb after do not, does not, don't, or doesn't.",
        ],
        "form_rules": [
            {"rule": "I/you/we/they + do not/don't + base verb", "pattern": "They don't eat meat."},
            {"rule": "he/she/it + does not/doesn't + base verb", "pattern": "She does not play tennis."},
        ],
        "meaning_functions": ["denying a routine, preference, possession, or simple fact"],
        "usage_conditions": [
            "Use do/does with lexical verbs, not with basic be negatives.",
            "Remove third-person -s from the main verb after does not.",
        ],
        "positive": [
            {"text": "I do not like milk.", "explanation": "I takes do not plus the base verb like."},
            {"text": "She does not play tennis.", "explanation": "does carries agreement; play stays in the base form."},
            {"text": "They don't eat meat.", "explanation": "don't is the contraction of do not."},
        ],
        "negative": [
            {"text": "I am not happy.", "error_tag": "ERR_BE_NEGATIVE_NOT_LEXICAL", "correction": "This is a be-verb negative, not do-support."},
            {"text": "She can't swim.", "error_tag": "ERR_MODAL_NEGATIVE_NOT_PRESENT_SIMPLE", "correction": "This belongs to the negative can unit."},
            {"text": "He doesn't likes milk.", "error_tag": "ERR_BASE_VERB_REQUIRED_AFTER_DOES", "correction": "Use He doesn't like milk."},
        ],
        "error_tags": [
            {"tag": "ERR_AUXILIARY_DO_MISSING", "diagnosis": "A lexical present negative lacks do/does."},
            {"tag": "ERR_DO_DOES_AGREEMENT", "diagnosis": "do/does does not agree with the subject."},
            {"tag": "ERR_BASE_VERB_REQUIRED_AFTER_DOES", "diagnosis": "The main verb incorrectly keeps third-person -s after does not."},
        ],
        "contrasts": ["GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS", "GRAMMAR_CAN_NEGATIVE_A1", "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1"],
        "targets": ["I do not like milk.", "She does not play tennis.", "They don't eat meat."],
    },
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS": {
        "stage": "A1",
        "title_en": "Present-simple yes/no questions",
        "title_zh_tw": "現在簡單式 Yes/No 問句",
        "objectives": [
            "Place do or does before the subject to ask a present-simple yes/no question.",
            "Use the base verb after the subject in a do/does question.",
        ],
        "form_rules": [
            {"rule": "Do + I/you/we/they + base verb?", "pattern": "Do you like apples?"},
            {"rule": "Does + he/she/it + base verb?", "pattern": "Does she play tennis?"},
        ],
        "meaning_functions": ["asking whether a routine, preference, or simple fact is true"],
        "usage_conditions": [
            "Use do/does for lexical verbs, not be-fronting questions.",
            "Keep the main verb in the base form after does.",
        ],
        "positive": [
            {"text": "Do you like apples?", "explanation": "Do precedes you and like remains the base form."},
            {"text": "Does she play tennis?", "explanation": "Does carries agreement and play remains the base form."},
        ],
        "negative": [
            {"text": "Where do you live?", "error_tag": "ERR_WH_QUESTION_NOT_YES_NO", "correction": "This is a wh-question, not a yes/no question."},
            {"text": "Are you happy?", "error_tag": "ERR_BE_QUESTION_NOT_DO_QUESTION", "correction": "This is a be-fronting question."},
            {"text": "She plays tennis.", "error_tag": "ERR_STATEMENT_NOT_QUESTION", "correction": "Use Does she play tennis?"},
        ],
        "error_tags": [
            {"tag": "ERR_AUXILIARY_DO_MISSING_IN_QUESTION", "diagnosis": "The yes/no question lacks initial do/does."},
            {"tag": "ERR_QUESTION_WORD_ORDER", "diagnosis": "The auxiliary, subject, and verb are in statement order."},
            {"tag": "ERR_BASE_VERB_REQUIRED_AFTER_DOES_QUESTION", "diagnosis": "The main verb incorrectly keeps -s after does."},
        ],
        "contrasts": ["GRAMMAR_BE_INTERROGATIVES_A1", "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS"],
        "targets": ["Do you like apples?", "Does she play tennis?"],
    },
    "GRAMMAR_PAST_SIMPLE_A1": {
        "stage": "A1+",
        "title_en": "Past-simple affirmative statements",
        "title_zh_tw": "過去簡單式肯定句",
        "objectives": [
            "Use a past-simple verb to describe a completed past event.",
            "Connect the past verb with a finished-time context such as yesterday.",
        ],
        "form_rules": [
            {"rule": "subject + regular past verb", "pattern": "I played football yesterday."},
            {"rule": "subject + irregular past verb", "pattern": "She went to school."},
        ],
        "meaning_functions": ["completed event at a finished past time"],
        "usage_conditions": [
            "Use the past form for a finished event, not the present form.",
            "Do not classify have + past participle as this basic past-simple unit.",
        ],
        "positive": [
            {"text": "I played football yesterday.", "explanation": "played marks a completed action at a finished past time."},
            {"text": "She went to school.", "explanation": "went is the irregular past form of go."},
        ],
        "negative": [
            {"text": "I play football.", "error_tag": "ERR_PRESENT_NOT_PAST", "correction": "For yesterday, use I played football."},
            {"text": "She is playing.", "error_tag": "ERR_PRESENT_CONTINUOUS_NOT_PAST", "correction": "Use a past form for a completed event."},
            {"text": "I have played.", "error_tag": "ERR_PRESENT_PERFECT_NOT_PAST_SIMPLE", "correction": "This is present perfect, not basic past simple."},
        ],
        "error_tags": [
            {"tag": "ERR_PAST_FORM_MISSING", "diagnosis": "The verb remains in the present form in a finished-past context."},
            {"tag": "ERR_IRREGULAR_PAST_FORM", "diagnosis": "The irregular past form is incorrect."},
            {"tag": "ERR_PAST_TIME_TENSE_MISMATCH", "diagnosis": "The tense conflicts with a finished-time expression."},
        ],
        "contrasts": ["GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS", "GRAMMAR_WILL_FUTURE_A1"],
        "targets": ["I played football yesterday.", "She went to school."],
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _gate(grammar_id: str, text: str, role: str) -> dict[str, Any]:
    return {
        "gate_version": "a1_practice_item_grammar_gate.v1",
        "validation_targets": [{"grammar_id": grammar_id, "text": text, "target_role": role}],
        "require_all_focus_matches": True,
        "validator_mode": "OFFLINE_STATIC_PROTOTYPE",
        "production_runtime_validator": False,
        "learner_state_write": False,
    }


def _activity(
    grammar_id: str,
    code: str,
    skill: str,
    dimension: str,
    task_type: str,
    prompt: str,
    target: str,
    response_mode: str,
    options: list[str] | None = None,
) -> dict[str, Any]:
    item_id = f"{grammar_id}__{code}"
    return {
        "item_id": item_id,
        "skill": skill,
        "evidence_dimension": dimension,
        "task_type": task_type,
        "prompt": prompt,
        "response_mode": response_mode,
        "options": options or [],
        "answer_key": {"accepted_texts": [target]},
        "content_binding": {"grammar_focus": [grammar_id]},
        "grammar_gate": _gate(grammar_id, target, f"pilot_{skill}_{dimension}"),
        "source_trace": {
            "source_family": "project_authored_derived_content",
            "raw_external_source_text_copied": False,
            "restricted_source_payload_persisted": False,
        },
    }


def _activities(grammar_id: str, targets: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    first, second = targets[0], targets[1]
    third = targets[2] if len(targets) > 2 else targets[0]
    practice = [
        _activity(grammar_id, "P01", "reading", "recognition", "multiple_choice", "Choose the option that uses the target grammar correctly.", first, "select_one", [first, "Not the target form"]),
        _activity(grammar_id, "P02", "reading", "meaning", "context_match", "Choose the target form that matches the short context.", second, "select_one", [second, first]),
        _activity(grammar_id, "P03", "reading", "contrast", "error_discrimination", "Identify the correctly formed target example.", third, "select_one", [third, "Incorrect contrast"]),
        _activity(grammar_id, "P04", "writing", "controlled_production", "gap_fill", "Complete the target form.", first, "short_text"),
        _activity(grammar_id, "P05", "writing", "controlled_production", "word_order", "Put the words in the correct order.", second, "short_text"),
        _activity(grammar_id, "P06", "writing", "contextual_production", "guided_sentence", "Write a sentence for the context using the target grammar.", third, "short_text"),
    ]
    assessment = [
        _activity(grammar_id, "A01", "reading", "receptive_checkpoint", "checkpoint_choice", "Select the correct target sentence or phrase.", first, "select_one", [first, "Incorrect form"]),
        _activity(grammar_id, "A02", "writing", "productive_checkpoint", "checkpoint_write", "Produce one sentence or phrase with the target grammar.", second, "short_text"),
    ]
    return practice, assessment


def build_artifact(query: dict[str, Any], rule_index: dict[str, Any], authority: dict[str, Any]) -> dict[str, Any]:
    canonical = query["canonical_a1"]["by_grammar_id"]
    rule_units = rule_index["by_grammar_id"]
    units = []
    for grammar_id in PILOT_UNIT_IDS:
        spec = UNIT_SPECS[grammar_id]
        practice, assessment = _activities(grammar_id, spec["targets"])
        units.append({
            "grammar_unit_id": grammar_id,
            "official_egp_level": "A1",
            "internal_stage": spec["stage"],
            "canonical_egp_row_ids": canonical[grammar_id]["egp_row_ids"],
            "canonical_egp_row_count": len(canonical[grammar_id]["egp_row_ids"]),
            "content_authority_status": "PROJECT_AUTHORED_CANDIDATE",
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
                "teaching_content_status": "PROJECT_AUTHORED_CANDIDATE_READY",
                "practice_content_status": "PILOT_READY",
                "assessment_content_status": "PILOT_READY",
                "mastery_runtime_status": "NOT_IMPLEMENTED",
                "teachable": True,
                "practice_ready": True,
                "assessment_ready": True,
                "mastery_trackable": False,
            },
        })

    all_rows = {row for unit in units for row in unit["canonical_egp_row_ids"]}
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_representative_vertical_slice",
        "artifact_type": "a1_a1plus_project_authored_pilot_learning_content",
        "schema_version": "a1_grammar_representative_vertical_slice.v1",
        "official_level": "A1",
        "internal_stages": ["A1", "A1+"],
        "authority_contract_path": "ulga/contracts/a1_grammar_learning_content_authority.json",
        "pilot_unit_ids": list(PILOT_UNIT_IDS),
        "coverage_summary": {
            "pilot_unit_count": len(units),
            "pilot_unique_egp_row_count": len(all_rows),
            "teaching_ready_unit_count": sum(unit["readiness"]["teachable"] for unit in units),
            "practice_ready_unit_count": sum(unit["readiness"]["practice_ready"] for unit in units),
            "assessment_ready_unit_count": sum(unit["readiness"]["assessment_ready"] for unit in units),
            "practice_item_count": sum(len(unit["practice_items"]) for unit in units),
            "assessment_item_count": sum(len(unit["assessment_items"]) for unit in units),
            "mastery_trackable_unit_count": 0,
        },
        "learning_units": units,
        "claim_boundaries": {
            "representative_vertical_slice_complete": True,
            "full_24_unit_teachable_coverage_complete": False,
            "full_109_row_teachable_coverage_complete": False,
            "learner_mastery_runtime_complete": False,
            "production_runtime_validation_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_learner_state_write": True,
            "no_external_nlp_dependency": True,
            "no_restricted_source_payload_copy": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def validate_artifact(artifact: dict[str, Any], query: dict[str, Any], rule_index: dict[str, Any], authority: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    canonical = query.get("canonical_a1", {}).get("by_grammar_id", {})
    rule_units = rule_index.get("by_grammar_id", {})
    if authority.get("authority_status") != "ACTIVE_FOR_STRUCTURAL_LEARNING_CONTENT":
        errors.append("content_authority_not_active")
    units = artifact.get("learning_units", [])
    by_id = {unit.get("grammar_unit_id"): unit for unit in units if unit.get("grammar_unit_id")}
    if len(units) != 6 or set(by_id) != set(PILOT_UNIT_IDS):
        errors.append("pilot_unit_set_mismatch")

    item_ids: set[str] = set()
    positive_count = negative_count = gate_target_count = 0
    for grammar_id in PILOT_UNIT_IDS:
        unit = by_id.get(grammar_id)
        if not unit:
            continue
        expected_rows = canonical.get(grammar_id, {}).get("egp_row_ids", [])
        if unit.get("canonical_egp_row_ids") != expected_rows:
            errors.append(f"canonical_row_mismatch:{grammar_id}")
        if unit.get("source_trace", {}).get("rule_source_path") != rule_units.get(grammar_id, {}).get("rule_source_path"):
            errors.append(f"rule_source_mismatch:{grammar_id}")
        if unit.get("internal_stage") != UNIT_SPECS[grammar_id]["stage"]:
            errors.append(f"stage_mismatch:{grammar_id}")
        for field, minimum in (("learning_objectives", 2), ("form_rules", 2), ("meaning_functions", 1), ("usage_conditions", 2), ("positive_examples", 2), ("negative_examples", 3), ("common_error_tags", 3), ("practice_items", 6), ("assessment_items", 2)):
            if len(unit.get(field, [])) < minimum:
                errors.append(f"content_minimum_not_met:{grammar_id}:{field}")

        for example in unit.get("positive_examples", []):
            positive_count += 1
            decision = dispatch_validate(grammar_id, example.get("text", ""))
            if decision.get("dispatch_status") != "VALIDATOR_EXECUTED" or decision.get("match") is not True:
                errors.append(f"positive_example_gate_fail:{grammar_id}:{example.get('text')}")
        for example in unit.get("negative_examples", []):
            negative_count += 1
            decision = dispatch_validate(grammar_id, example.get("text", ""))
            if decision.get("dispatch_status") != "VALIDATOR_EXECUTED" or decision.get("match") is not False:
                errors.append(f"negative_example_gate_fail:{grammar_id}:{example.get('text')}")

        activities = unit.get("practice_items", []) + unit.get("assessment_items", [])
        skills = {item.get("skill") for item in activities}
        dimensions = {item.get("evidence_dimension") for item in activities}
        if skills != {"reading", "writing"}:
            errors.append(f"reading_writing_skill_gap:{grammar_id}")
        if "receptive_checkpoint" not in dimensions or "productive_checkpoint" not in dimensions:
            errors.append(f"assessment_dimension_gap:{grammar_id}")
        for item in activities:
            item_id = item.get("item_id")
            if not item_id or item_id in item_ids:
                errors.append(f"duplicate_or_missing_item_id:{grammar_id}:{item_id}")
            item_ids.add(item_id)
            gate = validate_practice_item(item)
            gate_target_count += gate.get("validation_target_count", 0)
            if gate.get("gate_status") != "PASS":
                errors.append(f"practice_item_grammar_gate_fail:{item_id}")
            source = item.get("source_trace", {})
            if source.get("raw_external_source_text_copied") is not False or source.get("restricted_source_payload_persisted") is not False:
                errors.append(f"unsafe_source_payload:{item_id}")

        readiness = unit.get("readiness", {})
        if not all(readiness.get(field) is True for field in ("teachable", "practice_ready", "assessment_ready")):
            errors.append(f"pilot_readiness_false:{grammar_id}")
        if readiness.get("mastery_trackable") is not False:
            errors.append(f"false_mastery_runtime_claim:{grammar_id}")

    expected_summary = {
        "pilot_unit_count": 6,
        "pilot_unique_egp_row_count": len({row for unit in units for row in unit.get("canonical_egp_row_ids", [])}),
        "teaching_ready_unit_count": 6,
        "practice_ready_unit_count": 6,
        "assessment_ready_unit_count": 6,
        "practice_item_count": 36,
        "assessment_item_count": 12,
        "mastery_trackable_unit_count": 0,
    }
    if artifact.get("coverage_summary") != expected_summary:
        errors.append("coverage_summary_mismatch")
    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("full_24_unit_teachable_coverage_complete") is not False or boundaries.get("full_109_row_teachable_coverage_complete") is not False:
        errors.append("false_full_coverage_claim")
    for field in ("no_a2_a2plus_expansion", "no_learner_state_write", "no_external_nlp_dependency", "no_restricted_source_payload_copy"):
        if boundaries.get(field) is not True:
            errors.append(f"scope_boundary_missing:{field}")

    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_representative_vertical_slice_validation",
        "validation_status": status,
        "coverage_summary": expected_summary,
        "validation_counts": {
            "positive_example_count": positive_count,
            "negative_example_count": negative_count,
            "practice_and_assessment_grammar_gate_target_count": gate_target_count,
            "unique_item_id_count": len(item_ids),
        },
        "gate_checks": {
            "pilot_units_6_of_6": len(by_id) == 6,
            "canonical_row_bindings_match": not any(error.startswith("canonical_row_mismatch") for error in errors),
            "positive_examples_match": not any(error.startswith("positive_example_gate_fail") for error in errors),
            "negative_examples_rejected": not any(error.startswith("negative_example_gate_fail") for error in errors),
            "practice_item_grammar_gates_pass": not any(error.startswith("practice_item_grammar_gate_fail") for error in errors),
            "reading_writing_evidence_present": not any(error.startswith("reading_writing_skill_gap") for error in errors),
            "mapping_teaching_scope_separated": boundaries.get("full_24_unit_teachable_coverage_complete") is False,
            "no_a2plus_scope": boundaries.get("no_a2_a2plus_expansion") is True,
            "no_learner_state_write": boundaries.get("no_learner_state_write") is True,
        },
        "errors": errors,
        "warnings": [
            "Only 6 representative units are teaching/practice/assessment ready.",
            "Mastery tracking remains unavailable until the learner evidence loop is implemented.",
        ],
        "stop_reason": "NONE" if status == "PASS" else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if status == "PASS" else None,
        "validation_mode": "LOCAL_DETERMINISTIC_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    query = load_json(QUERY_PATH)
    rules = load_json(RULE_INDEX_PATH)
    authority = load_json(AUTHORITY_PATH)
    artifact = build_artifact(query, rules, authority)
    report = validate_artifact(artifact, query, rules, authority)
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
