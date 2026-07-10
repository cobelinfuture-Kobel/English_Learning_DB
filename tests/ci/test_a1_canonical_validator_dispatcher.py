import json
from pathlib import Path

from ulga.query.a1_canonical_validator_dispatcher import (
    TASK_ID,
    VALIDATOR_REGISTRY,
    available_grammar_ids,
    validate,
    validate_many,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def load(relative_path):
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def test_dispatcher_registry_matches_all_canonical_a1_units():
    overlay = load("ulga/graph/a1_egp_canonical_mappings.json")
    assert len(VALIDATOR_REGISTRY) == 24
    assert set(available_grammar_ids()) == set(overlay["canonical_mapping_units"])


def test_dispatcher_executes_all_148_declared_cases():
    requests = []
    can = load("ulga/rules/a1_can_statement_rule_primitives.json")
    for field in ("positive_test_cases", "negative_test_cases"):
        for case in can[field]:
            requests.append(("GRAMMAR_CAN_STATEMENT", case["text"], bool(case["expected_match"])))

    for path in (
        "ulga/rules/a1_a1plus_rule_primitives_batch_01.json",
        "ulga/rules/a1_unbucketed_rule_primitives_batch_02.json",
    ):
        batch = load(path)
        for node in batch["batch_nodes"]:
            requests.extend((node["grammar_id"], text, True) for text in node["positive_test_cases"])
            requests.extend((node["grammar_id"], text, False) for text in node["negative_test_cases"])

    assert len(requests) == 148
    for grammar_id, text, expected in requests:
        result = validate(grammar_id, text)
        assert result["dispatch_status"] == "VALIDATOR_EXECUTED"
        assert result["match"] is expected, (grammar_id, text, result)
        assert result["production_runtime_validator"] is False
        assert result["learner_state_write"] is False


def test_unknown_grammar_id_fails_closed_without_exception():
    result = validate("GRAMMAR_UNKNOWN_A1", "I like apples.")
    assert result == {
        "task_id": TASK_ID,
        "grammar_id": "GRAMMAR_UNKNOWN_A1",
        "text": "I like apples.",
        "dispatch_status": "UNKNOWN_GRAMMAR_ID_FAIL_CLOSED",
        "match": False,
        "primitive_id": None,
        "reason": "unknown_canonical_a1_grammar_id",
        "validator_mode": "OFFLINE_STATIC_PROTOTYPE",
        "production_runtime_validator": False,
        "learner_state_write": False,
    }


def test_batch_dispatch_reports_executed_unknown_and_match_counts():
    result = validate_many([
        {"grammar_id": "GRAMMAR_ARTICLES_BASIC", "text": "a cat"},
        {"grammar_id": "GRAMMAR_ARTICLES_BASIC", "text": "two cats"},
        {"grammar_id": "GRAMMAR_UNKNOWN_A1", "text": "anything"},
    ])
    assert result["request_count"] == 3
    assert result["executed_count"] == 2
    assert result["unknown_count"] == 1
    assert result["match_count"] == 1
    assert result["learner_state_write"] is False

