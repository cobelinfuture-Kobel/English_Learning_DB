import json
from pathlib import Path

from ulga.validators.validate_a1_canonical_executable_batch_02 import (
    CLASSIFIERS,
    build_report,
    validate_batch,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
BATCH_PATH = REPO_ROOT / "ulga/rules/a1_unbucketed_rule_primitives_batch_02.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_canonical_executable_batch_02_validation.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_declared_batch_02_cases_pass_executable_classifiers():
    validation = validate_batch(load(BATCH_PATH))
    assert validation["grammar_id_set_status"] == "PASS"
    assert validation["node_count"] == 11
    assert validation["pass_node_count"] == 11
    assert validation["fail_node_count"] == 0
    assert validation["total_case_count"] == 66
    assert validation["pass_case_count"] == 66
    assert validation["fail_case_count"] == 0


def test_checked_in_report_is_deterministic():
    batch = load(BATCH_PATH)
    expected = build_report(batch, "ulga/rules/a1_unbucketed_rule_primitives_batch_02.json")
    assert expected == load(REPORT_PATH)


def test_batch_02_false_positive_gates_are_executable():
    cases = [
        ("GRAMMAR_ADJECTIVE_PHRASES_A1", "cats and dogs", False),
        ("GRAMMAR_ADVERB_PHRASES_A1", "There is a book.", False),
        ("GRAMMAR_COORDINATION_A1", "But I like it.", False),
        ("GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1", "I cannot swim.", False),
        ("GRAMMAR_BE_INTERROGATIVES_A1", "Where are you?", False),
        ("GRAMMAR_BECAUSE_REASON_CLAUSES_A1", "Because I am happy.", False),
        ("GRAMMAR_WILL_FUTURE_A1", "Will is my friend.", False),
        ("GRAMMAR_CAN_NEGATIVE_A1", "I have a can.", False),
        ("GRAMMAR_NOUN_PHRASES_A1", "quickly", False),
        ("GRAMMAR_PAST_SIMPLE_A1", "I have played.", False),
        ("GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1", "I would go.", False),
    ]
    for grammar_id, text, expected in cases:
        assert CLASSIFIERS[grammar_id](text).match is expected, (grammar_id, text)


def test_batch_02_positive_surface_samples_remain_queryable():
    samples = [
        ("GRAMMAR_ADJECTIVE_PHRASES_A1", "my best friend"),
        ("GRAMMAR_ADVERB_PHRASES_A1", "I sometimes play tennis."),
        ("GRAMMAR_COORDINATION_A1", "It is small but nice."),
        ("GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1", "She is not tired."),
        ("GRAMMAR_BE_INTERROGATIVES_A1", "Are you happy?"),
        ("GRAMMAR_BECAUSE_REASON_CLAUSES_A1", "I like it because it is fun."),
        ("GRAMMAR_WILL_FUTURE_A1", "She'll call you."),
        ("GRAMMAR_CAN_NEGATIVE_A1", "I can't swim."),
        ("GRAMMAR_NOUN_PHRASES_A1", "The boy likes apples."),
        ("GRAMMAR_PAST_SIMPLE_A1", "She went to school."),
        ("GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1", "I like swimming."),
    ]
    for grammar_id, text in samples:
        assert CLASSIFIERS[grammar_id](text).match is True, (grammar_id, text)

