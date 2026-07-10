import json
from pathlib import Path

from ulga.validators.validate_a1_canonical_executable_batch_01 import (
    CLASSIFIERS,
    build_report,
    validate_batch,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
BATCH_PATH = REPO_ROOT / "ulga/rules/a1_a1plus_rule_primitives_batch_01.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_canonical_executable_batch_01_validation.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_declared_batch_01_cases_pass_executable_classifiers():
    validation = validate_batch(load(BATCH_PATH))
    assert validation["grammar_id_set_status"] == "PASS"
    assert validation["node_count"] == 12
    assert validation["pass_node_count"] == 12
    assert validation["fail_node_count"] == 0
    assert validation["total_case_count"] == 70
    assert validation["pass_case_count"] == 70
    assert validation["fail_case_count"] == 0


def test_checked_in_report_is_deterministic():
    batch = load(BATCH_PATH)
    expected = build_report(batch, "ulga/rules/a1_a1plus_rule_primitives_batch_01.json")
    assert expected == load(REPORT_PATH)


def test_false_positive_gates_are_executable():
    cases = [
        ("GRAMMAR_ARTICLES_BASIC", "a apple", False),
        ("GRAMMAR_SUBJECT_PRONOUNS", "Her book is red.", False),
        ("GRAMMAR_OBJECT_PRONOUNS_BASIC", "They are friends.", False),
        ("GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC", "This is mine.", False),
        ("GRAMMAR_PRESENT_SIMPLE_NEGATIVES", "He doesn't likes milk.", False),
        ("GRAMMAR_THERE_IS", "There she is.", False),
        ("GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS", "He played football.", False),
        ("GRAMMAR_BE_VERB_BASIC", "She is playing.", False),
        ("GRAMMAR_BASIC_PREPOSITIONS_PLACE", "on Monday", False),
        ("GRAMMAR_REGULAR_PLURAL_NOUNS", "she likes", False),
        ("GRAMMAR_DEMONSTRATIVES_CONTRAST", "those is wrong", False),
        ("GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS", "Does she plays tennis?", False),
    ]
    for grammar_id, text, expected in cases:
        assert CLASSIFIERS[grammar_id](text).match is expected, (grammar_id, text)


def test_subject_pronoun_contradictory_negative_was_removed():
    batch = load(BATCH_PATH)
    subject_node = next(node for node in batch["batch_nodes"] if node["grammar_id"] == "GRAMMAR_SUBJECT_PRONOUNS")
    assert "I like her." not in subject_node["negative_test_cases"]
    assert "Her book is red." in subject_node["negative_test_cases"]
    assert CLASSIFIERS["GRAMMAR_SUBJECT_PRONOUNS"]("I like her.").match is True

