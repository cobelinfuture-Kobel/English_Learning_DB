#!/usr/bin/env python3
"""Executable offline sentence validators for canonical A1 batch 01.

The classifiers implement the declared batch-01 gates and false-positive
filters with deterministic regex and small closed lexical policies. They are
offline prototypes, not a production parser and not a runtime service.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


TASK_ID = "R7-M104E21B_A1CanonicalExecutableValidatorBatch01Implementation"
EXPECTED_GRAMMAR_IDS = [
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_SUBJECT_PRONOUNS",
    "GRAMMAR_OBJECT_PRONOUNS_BASIC",
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC",
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES",
    "GRAMMAR_THERE_IS",
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
    "GRAMMAR_REGULAR_PLURAL_NOUNS",
    "GRAMMAR_DEMONSTRATIVES_CONTRAST",
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS",
]

SUBJECT_PRONOUNS = {"i", "you", "he", "she", "it", "we", "they"}
OBJECT_PRONOUNS = {"me", "you", "him", "her", "it", "us", "them"}
POSSESSIVE_DETERMINERS = {"my", "your", "his", "her", "its", "our", "their"}
THIRD_SINGULAR_SUBJECTS = {"he", "she", "it"}
BE_FORMS = {"am", "is", "are"}
MODALS = {"can", "could", "may", "might", "must", "shall", "should", "will", "would"}
IRREGULAR_PLURALS = {"children", "people", "men", "women", "feet", "teeth", "mice", "geese"}
TIME_WORDS = {
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "morning", "afternoon", "evening",
}


@dataclass(frozen=True)
class Decision:
    match: bool
    primitive_id: str | None
    reason: str


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+|\d+", text.lower())


def yes(primitive_id: str, reason: str) -> Decision:
    return Decision(True, primitive_id, reason)


def no(reason: str) -> Decision:
    return Decision(False, None, reason)


def classify_articles(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 2 or tokens[0] not in {"a", "an", "the"}:
        return no("missing_article_noun_phrase")
    article, head = tokens[0], tokens[1]
    if article == "a" and head[0] in "aeiou":
        return no("a_an_phonology_gate")
    if article == "an" and head[0] not in "aeiou":
        return no("a_an_phonology_gate")
    primitive = "ARTICLE_DEFINITE_THE_NOUN_PHRASE" if article == "the" else "ARTICLE_INDEFINITE_A_AN_SINGULAR_COUNT_NOUN"
    return yes(primitive, "article_plus_noun_phrase")


def classify_subject_pronouns(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 2 or tokens[0] not in SUBJECT_PRONOUNS:
        return no("closed_subject_pronoun_not_in_subject_position")
    if tokens[1] in OBJECT_PRONOUNS | POSSESSIVE_DETERMINERS:
        return no("finite_verb_gate")
    return yes("SUBJECT_PRONOUN_CLOSED_LIST_BEFORE_VERB", "subject_pronoun_before_finite_predicate")


def classify_object_pronouns(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 2:
        return no("missing_object_position")
    for index, token in enumerate(tokens[1:], start=1):
        if token in OBJECT_PRONOUNS and tokens[index - 1] not in BE_FORMS:
            return yes("OBJECT_PRONOUN_AFTER_VERB_OR_PREPOSITION", "object_pronoun_after_head")
    return no("closed_object_pronoun_not_in_object_position")


def classify_possessive_adjectives(text: str) -> Decision:
    tokens = words(text)
    for index, token in enumerate(tokens[:-1]):
        if token in POSSESSIVE_DETERMINERS and tokens[index + 1] not in BE_FORMS:
            return yes("POSSESSIVE_DETERMINER_BEFORE_NOUN", "possessive_determiner_before_noun")
    return no("possessive_determiner_not_before_noun")


def classify_present_simple_negatives(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 4:
        return no("missing_do_negative_pattern")
    subject = tokens[0]
    contracted = tokens[1] in {"don't", "doesn't"}
    expanded = len(tokens) >= 5 and tokens[1] in {"do", "does"} and tokens[2] == "not"
    if not contracted and not expanded:
        return no("aux_do_negative_gate")
    aux = tokens[1]
    verb_index = 2 if contracted else 3
    if verb_index >= len(tokens):
        return no("missing_base_verb")
    verb = tokens[verb_index]
    is_third = subject in THIRD_SINGULAR_SUBJECTS
    if (is_third and aux not in {"does", "doesn't"}) or (not is_third and aux not in {"do", "don't"}):
        return no("subject_agreement_gate")
    if verb.endswith("s") and verb not in {"is"}:
        return no("base_verb_gate")
    return yes("PRESENT_SIMPLE_DO_DOES_NOT_BASE_VERB", "do_negative_base_verb")


def classify_there_is(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 3 or tokens[0] != "there" or tokens[1] not in {"is", "are"}:
        return no("missing_expletive_there_be_pattern")
    if tokens[2] in SUBJECT_PRONOUNS:
        return no("deictic_there_filter")
    return yes("EXISTENTIAL_THERE_BE_NOUN_PHRASE", "expletive_there_be_noun_phrase")


def classify_present_simple_statements(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 2 or text.strip().endswith("?"):
        return no("statement_mode_gate")
    subject, verb = tokens[0], tokens[1]
    if subject not in SUBJECT_PRONOUNS:
        return no("subject_gate")
    if verb in BE_FORMS | MODALS or verb.endswith("ed") or verb.endswith("ing"):
        return no("lexical_present_verb_gate")
    is_third = subject in THIRD_SINGULAR_SUBJECTS
    if is_third and not verb.endswith("s"):
        return no("third_person_agreement_gate")
    if not is_third and verb.endswith("s"):
        return no("non_third_person_agreement_gate")
    return yes("PRESENT_SIMPLE_AFFIRMATIVE_LEXICAL_VERB", "affirmative_present_lexical_statement")


def classify_be_verb(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 3 or tokens[0] not in SUBJECT_PRONOUNS or tokens[1] not in BE_FORMS:
        return no("be_copula_pattern_missing")
    subject, be_form = tokens[0], tokens[1]
    expected = "am" if subject == "i" else "are" if subject in {"you", "we", "they"} else "is"
    if be_form != expected:
        return no("subject_agreement_gate")
    if tokens[2].endswith("ing"):
        return no("be_aux_progressive_filter")
    return yes("BE_COPULA_SUBJECT_COMPLEMENT", "be_copula_with_complement")


def classify_place_prepositions(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 2:
        return no("place_preposition_phrase_missing")
    start = "next to" if tokens[:2] == ["next", "to"] else tokens[0]
    object_tokens = tokens[2:] if start == "next to" else tokens[1:]
    if start not in {"in", "on", "under", "next to"} or not object_tokens:
        return no("place_preposition_gate")
    if any(token in TIME_WORDS or token.isdigit() for token in object_tokens):
        return no("time_preposition_filter")
    return yes("PLACE_PREPOSITION_PHRASE_BASIC", "place_preposition_with_object")


def classify_regular_plural_nouns(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) != 1:
        return no("single_noun_form_gate")
    token = tokens[0]
    if token in IRREGULAR_PLURALS or not token.endswith("s") or token.endswith("'s"):
        return no("regular_plural_form_gate")
    return yes("REGULAR_PLURAL_NOUN_S_ES", "regular_plural_s_es_form")


def classify_demonstratives(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 2 or tokens[0] not in {"this", "that", "these", "those"}:
        return no("demonstrative_noun_phrase_missing")
    determiner, noun = tokens[0], tokens[1]
    if noun in BE_FORMS:
        return no("this_is_identification_filter")
    plural = noun.endswith("s")
    if determiner in {"this", "that"} and plural:
        return no("singular_plural_agreement_gate")
    if determiner in {"these", "those"} and not plural:
        return no("singular_plural_agreement_gate")
    return yes("DEMONSTRATIVE_THIS_THAT_THESE_THOSE_NP", "demonstrative_noun_phrase")


def classify_present_simple_questions(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 3 or not text.strip().endswith("?") or tokens[0] not in {"do", "does"}:
        return no("yes_no_question_mode_gate")
    aux, subject, verb = tokens[0], tokens[1], tokens[2]
    is_third = subject in THIRD_SINGULAR_SUBJECTS
    if (is_third and aux != "does") or (not is_third and aux != "do"):
        return no("subject_agreement_gate")
    if verb.endswith("s"):
        return no("base_verb_gate")
    return yes("PRESENT_SIMPLE_DO_DOES_YES_NO_QUESTION", "do_yes_no_question")


CLASSIFIERS: dict[str, Callable[[str], Decision]] = {
    "GRAMMAR_ARTICLES_BASIC": classify_articles,
    "GRAMMAR_SUBJECT_PRONOUNS": classify_subject_pronouns,
    "GRAMMAR_OBJECT_PRONOUNS_BASIC": classify_object_pronouns,
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": classify_possessive_adjectives,
    "GRAMMAR_PRESENT_SIMPLE_NEGATIVES": classify_present_simple_negatives,
    "GRAMMAR_THERE_IS": classify_there_is,
    "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS": classify_present_simple_statements,
    "GRAMMAR_BE_VERB_BASIC": classify_be_verb,
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": classify_place_prepositions,
    "GRAMMAR_REGULAR_PLURAL_NOUNS": classify_regular_plural_nouns,
    "GRAMMAR_DEMONSTRATIVES_CONTRAST": classify_demonstratives,
    "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS": classify_present_simple_questions,
}


def validate_batch(batch: dict) -> dict:
    node_results = []
    total_pass = 0
    total_fail = 0
    actual_ids = [node.get("grammar_id") for node in batch.get("batch_nodes", [])]
    set_error = None if actual_ids == EXPECTED_GRAMMAR_IDS else f"batch grammar ids mismatch: {actual_ids}"

    for node in batch.get("batch_nodes", []):
        grammar_id = node["grammar_id"]
        classifier = CLASSIFIERS[grammar_id]
        case_results = []
        pass_count = 0
        fail_count = 0
        for polarity, expected, cases in (
            ("positive", True, node.get("positive_test_cases", [])),
            ("negative", False, node.get("negative_test_cases", [])),
        ):
            for text in cases:
                decision = classifier(text)
                passed = decision.match is expected
                pass_count += int(passed)
                fail_count += int(not passed)
                case_results.append({
                    "polarity": polarity,
                    "text": text,
                    "expected_match": expected,
                    "actual_match": decision.match,
                    "primitive_id": decision.primitive_id,
                    "reason": decision.reason,
                    "status": "PASS" if passed else "FAIL",
                })
        total_pass += pass_count
        total_fail += fail_count
        node_results.append({
            "grammar_id": grammar_id,
            "positive_test_count": len(node.get("positive_test_cases", [])),
            "negative_test_count": len(node.get("negative_test_cases", [])),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "status": "PASS" if fail_count == 0 else "FAIL",
            "case_results": case_results,
        })

    return {
        "grammar_id_set_status": "PASS" if set_error is None else "FAIL",
        "grammar_id_set_error": set_error,
        "node_count": len(node_results),
        "pass_node_count": sum(result["status"] == "PASS" for result in node_results),
        "fail_node_count": sum(result["status"] == "FAIL" for result in node_results),
        "total_case_count": total_pass + total_fail,
        "pass_case_count": total_pass,
        "fail_case_count": total_fail,
        "node_results": node_results,
    }


def build_report(batch: dict, source_path: str) -> dict:
    validation = validate_batch(batch)
    status = "PASS" if validation["grammar_id_set_status"] == "PASS" and validation["fail_node_count"] == 0 else "FAIL"
    return {
        "task_id": TASK_ID,
        "artifact_id": "a1_canonical_executable_batch_01_validation",
        "artifact_type": "offline_executable_sentence_validator_report",
        "source_rule_artifact": source_path,
        "validator_mode": "offline_deterministic_regex_and_closed_lexical_policy",
        "validation_summary": {
            key: validation[key]
            for key in (
                "grammar_id_set_status", "node_count", "pass_node_count", "fail_node_count",
                "total_case_count", "pass_case_count", "fail_case_count",
            )
        } | {"status": status},
        "node_results": validation["node_results"],
        "prototype_limits": {
            "not_a_production_parser": True,
            "not_a_runtime_service": True,
            "no_external_nlp_dependency": True,
            "no_learner_state_write": True,
            "no_practicebank_generation": True,
            "coverage_claim_scope": "declared_batch_01_positive_and_negative_cases_only",
        },
        "result_status": {
            "offline_sentence_validator_status": "IMPLEMENTED" if status == "PASS" else "FAILED",
            "production_runtime_validator_status": "NOT_IMPLEMENTED",
            "rule_authority_status": "CANDIDATE_NOT_PROMOTED",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-artifact", default="ulga/rules/a1_a1plus_rule_primitives_batch_01.json")
    parser.add_argument("--output", default="ulga/reports/a1_canonical_executable_batch_01_validation.json")
    args = parser.parse_args()
    batch = json.loads(Path(args.batch_artifact).read_text(encoding="utf-8"))
    report = build_report(batch, args.batch_artifact)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"A1 canonical executable batch 01: {report['validation_summary']['status']}")
    print(f"Nodes: {report['validation_summary']['pass_node_count']}/{report['validation_summary']['node_count']}")
    print(f"Cases: {report['validation_summary']['pass_case_count']}/{report['validation_summary']['total_case_count']}")
    return 0 if report["validation_summary"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
