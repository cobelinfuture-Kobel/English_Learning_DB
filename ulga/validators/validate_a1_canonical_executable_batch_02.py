#!/usr/bin/env python3
"""Executable offline sentence validators for canonical A1 batch 02."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.validators.validate_a1_canonical_executable_batch_01 import (
    BE_FORMS,
    MODALS,
    SUBJECT_PRONOUNS,
    Decision,
    no,
    words,
    yes,
)


TASK_ID = "R7-M104E21C_A1CanonicalExecutableValidatorBatch02Implementation"
EXPECTED_GRAMMAR_IDS = [
    "GRAMMAR_ADJECTIVE_PHRASES_A1",
    "GRAMMAR_ADVERB_PHRASES_A1",
    "GRAMMAR_COORDINATION_A1",
    "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1",
    "GRAMMAR_BE_INTERROGATIVES_A1",
    "GRAMMAR_BECAUSE_REASON_CLAUSES_A1",
    "GRAMMAR_WILL_FUTURE_A1",
    "GRAMMAR_CAN_NEGATIVE_A1",
    "GRAMMAR_NOUN_PHRASES_A1",
    "GRAMMAR_PAST_SIMPLE_A1",
    "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1",
]

COMMON_ADJECTIVES = {
    "big", "small", "nice", "friendly", "happy", "sad", "good", "bad", "red", "blue",
    "beautiful", "young", "old", "new", "funny", "tall", "short", "tired", "sunny", "best",
}
TIME_ADVERBS = {"soon", "today", "tomorrow", "yesterday", "now", "later", "early", "late"}
FREQUENCY_ADVERBS = {"always", "usually", "often", "sometimes", "never"}
IRREGULAR_PAST = {"went", "was", "were", "had", "did", "saw", "ate", "came", "got", "made", "took", "gave"}
LICENSED_TO_INFINITIVE_VERBS = {"want", "wants", "need", "needs", "plan", "plans", "hope", "hopes", "try", "tries"}
A1_COMPLEMENT_MODALS = {"can", "will", "must", "should", "may"}


def classify_adjective_phrases(text: str) -> Decision:
    tokens = words(text)
    if tokens == ["my", "best", "friend"]:
        return yes("MY_BEST_FRIEND_CHUNK_A1", "fixed_my_best_friend_chunk")
    if len(tokens) == 2 and tokens[0] == "very" and tokens[1] in COMMON_ADJECTIVES - {"best"}:
        return yes("VERY_ADJECTIVE_A1", "very_gradable_adjective")
    if len(tokens) == 3 and tokens[1] == "and" and tokens[0] in COMMON_ADJECTIVES and tokens[2] in COMMON_ADJECTIVES:
        return yes("ADJECTIVE_AND_COORDINATION_A1", "coordinated_common_adjectives")
    if len(tokens) >= 3 and tokens[0] in {"a", "an", "the"} and tokens[1] in COMMON_ADJECTIVES - {"best"}:
        return yes("ATTRIBUTIVE_ADJECTIVE_BEFORE_NOUN_A1", "attributive_adjective_before_noun")
    if len(tokens) == 2 and tokens[0] in COMMON_ADJECTIVES - {"best"}:
        return yes("ATTRIBUTIVE_ADJECTIVE_BEFORE_NOUN_A1", "attributive_adjective_before_noun")
    return no("no_declared_adjective_phrase_pattern")


def classify_adverb_phrases(text: str) -> Decision:
    tokens = words(text)
    if not tokens or tokens[:2] == ["there", "is"] or tokens[:2] == ["there", "are"]:
        return no("existential_or_missing_adverb_pattern")
    if tokens[0] in TIME_ADVERBS or tokens[-1] in TIME_ADVERBS:
        return yes("TIME_ADVERB_END_OR_FRONT_A1", "time_adverb_front_or_end")
    if tokens[-1] in {"here", "there"} and len(tokens) >= 2:
        return yes("PLACE_ADVERB_HERE_THERE_A1", "place_adverb_end_position")
    if len(tokens) >= 3 and tokens[0] in SUBJECT_PRONOUNS and tokens[1] in FREQUENCY_ADVERBS:
        return yes("FREQUENCY_ADVERB_MID_POSITION_A1", "frequency_adverb_mid_position")
    if len(tokens) >= 3 and tokens[0] in SUBJECT_PRONOUNS and tokens[1] == "really":
        return yes("DEGREE_ADVERB_MODIFICATION_A1", "really_modifies_predicate")
    if "very" in tokens and "much" in tokens:
        return yes("DEGREE_ADVERB_MODIFICATION_A1", "very_much_degree_modification")
    return no("no_declared_adverb_phrase_pattern")


def classify_coordination(text: str) -> Decision:
    stripped = text.strip()
    tokens = words(stripped)
    if not tokens or tokens[0] in {"and", "but", "or", "because"}:
        return no("subordinator_or_discourse_marker_filter")
    conjunctions = [index for index, token in enumerate(tokens) if token in {"and", "but", "or"}]
    if not conjunctions:
        return no("coordinating_conjunction_gate")
    index = conjunctions[-1]
    if index == 0 or index == len(tokens) - 1:
        return no("compatible_unit_gate")
    if "," in stripped and tokens[index] in {"and", "or"}:
        return yes("LIST_FINAL_AND_OR_A1", "list_final_conjunction")
    if tokens[index] == "but":
        return yes("BUT_CONCESSIVE_A1", "internal_but_contrast")
    return yes("WORD_PHRASE_CLAUSE_COORDINATION_A1", "compatible_units_coordinated")


def classify_declarative_clauses(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 2 or text.strip().endswith("?"):
        return no("question_mode_filter")
    if any(token in {"cannot", "can't"} for token in tokens) or any(
        tokens[index] in MODALS and index + 1 < len(tokens) and tokens[index + 1] == "not"
        for index in range(len(tokens))
    ):
        return no("modal_negative_filter")
    if len(tokens) >= 4 and tokens[1] in BE_FORMS and tokens[2] == "not":
        return yes("BE_NEGATIVE_DECLARATIVE_A1", "be_negative_declarative")
    if len(tokens) >= 4 and tokens[1] in {"do", "does", "don't", "doesn't"}:
        return yes("LEXICAL_NEGATIVE_DECLARATIVE_A1", "lexical_negative_declarative")
    if tokens[1] in MODALS:
        return yes("MODAL_AFFIRMATIVE_DECLARATIVE_A1", "modal_affirmative_declarative")
    return yes("AFFIRMATIVE_DECLARATIVE_BASIC_A1", "affirmative_subject_predicate")


def classify_be_interrogatives(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 3 or not text.strip().endswith("?") or tokens[0] not in BE_FORMS:
        return no("be_fronting_question_gate")
    return yes("BE_YES_NO_QUESTION_A1", "fronted_be_yes_no_question")


def classify_because_reason(text: str) -> Decision:
    tokens = words(text)
    if "because" not in tokens:
        return no("because_subordinator_gate")
    index = tokens.index("because")
    if index < 2 or len(tokens) - index - 1 < 2:
        return no("because_fragment_filter")
    return yes("BECAUSE_SUBORDINATE_REASON_CLAUSE_A1", "main_clause_plus_finite_because_clause")


def classify_will_future(text: str) -> Decision:
    stripped = text.strip()
    tokens = words(stripped)
    if len(tokens) >= 3 and tokens[0] in SUBJECT_PRONOUNS and tokens[1] == "will":
        return yes("WILL_AFFIRMATIVE_FUTURE_A1", "will_auxiliary_plus_base_verb")
    if re.match(r"^\s*(I|you|he|she|it|we|they)'ll\s+[A-Za-z]+", stripped, re.IGNORECASE):
        return yes("WILL_AFFIRMATIVE_FUTURE_A1", "contracted_will_plus_base_verb")
    return no("will_auxiliary_gate")


def classify_can_negative(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 3 or text.strip().endswith("?") or tokens[0] not in SUBJECT_PRONOUNS:
        return no("can_negative_statement_gate")
    if tokens[1] in {"can't", "cannot"}:
        return yes("CAN_NOT_NEGATIVE_A1", "contracted_or_fused_can_negative")
    if len(tokens) >= 4 and tokens[1:3] == ["can", "not"]:
        return yes("CAN_NOT_NEGATIVE_A1", "expanded_can_not_negative")
    return no("negative_not_gate")


def classify_noun_phrases(text: str) -> Decision:
    tokens = words(text)
    if not tokens or tokens[0] in {"is", "are", "am", "very"} or tokens[0].endswith("ly"):
        return no("noun_gate")
    if len(tokens) == 1 and text.strip()[:1].isupper():
        return yes("COMMON_AND_PROPER_NOUNS_A1", "proper_noun")
    if len(tokens) == 2 and all(token.isalpha() for token in tokens):
        return yes("NOUN_PREMODIFIER_NOUN_A1", "noun_premodifier_plus_head_noun")
    if len(tokens) >= 4 and tokens[0] in {"a", "an", "the", "this", "that", "these", "those", "my", "your", "his", "her", "our", "their"}:
        return yes("NOUN_PHRASE_AS_SUBJECT_OBJECT_ADJUNCT_A1", "noun_phrase_in_clause_function")
    return no("no_declared_noun_phrase_pattern")


def classify_past_simple(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 2 or text.strip().endswith("?") or tokens[0] not in SUBJECT_PRONOUNS:
        return no("past_simple_statement_gate")
    if len(tokens) >= 3 and tokens[1] in {"have", "has", "had"} and (tokens[2].endswith("ed") or tokens[2] in IRREGULAR_PAST):
        return no("present_perfect_filter")
    verb = tokens[1]
    if verb.endswith("ed") or verb in IRREGULAR_PAST:
        return yes("PAST_SIMPLE_AFFIRMATIVE_A1", "affirmative_past_simple_verb")
    return no("past_simple_verb_gate")


def classify_verb_complements(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 3 or tokens[0] not in SUBJECT_PRONOUNS:
        return no("subject_complement_pattern_gate")
    if len(tokens) >= 5 and tokens[1:4] == ["would", "like", "to"]:
        return yes("WOULD_LIKE_TO_A1", "would_like_to_chunk")
    if tokens[1] in LICENSED_TO_INFINITIVE_VERBS and len(tokens) >= 4 and tokens[2] == "to":
        return yes("VERB_TO_INFINITIVE_A1", "licensed_verb_to_infinitive")
    if tokens[1] in {"like", "likes"} and (tokens[2] == "to" or tokens[2].endswith("ing")):
        return yes("LIKE_TO_OR_ING_A1", "like_with_to_infinitive_or_ing")
    if tokens[1] in A1_COMPLEMENT_MODALS:
        return yes("MODAL_AUXILIARY_VERBS_A1", "a1_modal_auxiliary_plus_base_verb")
    return no("no_licensed_verb_complement_pattern")


CLASSIFIERS: dict[str, Callable[[str], Decision]] = {
    "GRAMMAR_ADJECTIVE_PHRASES_A1": classify_adjective_phrases,
    "GRAMMAR_ADVERB_PHRASES_A1": classify_adverb_phrases,
    "GRAMMAR_COORDINATION_A1": classify_coordination,
    "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1": classify_declarative_clauses,
    "GRAMMAR_BE_INTERROGATIVES_A1": classify_be_interrogatives,
    "GRAMMAR_BECAUSE_REASON_CLAUSES_A1": classify_because_reason,
    "GRAMMAR_WILL_FUTURE_A1": classify_will_future,
    "GRAMMAR_CAN_NEGATIVE_A1": classify_can_negative,
    "GRAMMAR_NOUN_PHRASES_A1": classify_noun_phrases,
    "GRAMMAR_PAST_SIMPLE_A1": classify_past_simple,
    "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1": classify_verb_complements,
}


def validate_batch(batch: dict) -> dict:
    actual_ids = [node.get("grammar_id") for node in batch.get("batch_nodes", [])]
    node_results = []
    pass_cases = 0
    fail_cases = 0
    for node in batch.get("batch_nodes", []):
        grammar_id = node["grammar_id"]
        classifier = CLASSIFIERS[grammar_id]
        case_results = []
        node_pass = 0
        node_fail = 0
        for polarity, expected, cases in (
            ("positive", True, node.get("positive_test_cases", [])),
            ("negative", False, node.get("negative_test_cases", [])),
        ):
            for text in cases:
                decision = classifier(text)
                passed = decision.match is expected
                node_pass += int(passed)
                node_fail += int(not passed)
                case_results.append({
                    "polarity": polarity,
                    "text": text,
                    "expected_match": expected,
                    "actual_match": decision.match,
                    "primitive_id": decision.primitive_id,
                    "reason": decision.reason,
                    "status": "PASS" if passed else "FAIL",
                })
        pass_cases += node_pass
        fail_cases += node_fail
        node_results.append({
            "grammar_id": grammar_id,
            "positive_test_count": len(node.get("positive_test_cases", [])),
            "negative_test_count": len(node.get("negative_test_cases", [])),
            "pass_count": node_pass,
            "fail_count": node_fail,
            "status": "PASS" if node_fail == 0 else "FAIL",
            "case_results": case_results,
        })
    return {
        "grammar_id_set_status": "PASS" if actual_ids == EXPECTED_GRAMMAR_IDS else "FAIL",
        "node_count": len(node_results),
        "pass_node_count": sum(node["status"] == "PASS" for node in node_results),
        "fail_node_count": sum(node["status"] == "FAIL" for node in node_results),
        "total_case_count": pass_cases + fail_cases,
        "pass_case_count": pass_cases,
        "fail_case_count": fail_cases,
        "node_results": node_results,
    }


def build_report(batch: dict, source_path: str) -> dict:
    validation = validate_batch(batch)
    status = "PASS" if validation["grammar_id_set_status"] == "PASS" and validation["fail_node_count"] == 0 else "FAIL"
    return {
        "task_id": TASK_ID,
        "artifact_id": "a1_canonical_executable_batch_02_validation",
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
            "coverage_claim_scope": "declared_batch_02_positive_and_negative_cases_only",
        },
        "result_status": {
            "offline_sentence_validator_status": "IMPLEMENTED" if status == "PASS" else "FAILED",
            "production_runtime_validator_status": "NOT_IMPLEMENTED",
            "rule_authority_status": "CANDIDATE_NOT_PROMOTED",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-artifact", default="ulga/rules/a1_unbucketed_rule_primitives_batch_02.json")
    parser.add_argument("--output", default="ulga/reports/a1_canonical_executable_batch_02_validation.json")
    args = parser.parse_args()
    batch = json.loads(Path(args.batch_artifact).read_text(encoding="utf-8"))
    report = build_report(batch, args.batch_artifact)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"A1 canonical executable batch 02: {report['validation_summary']['status']}")
    print(f"Nodes: {report['validation_summary']['pass_node_count']}/{report['validation_summary']['node_count']}")
    print(f"Cases: {report['validation_summary']['pass_case_count']}/{report['validation_summary']['total_case_count']}")
    return 0 if report["validation_summary"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
