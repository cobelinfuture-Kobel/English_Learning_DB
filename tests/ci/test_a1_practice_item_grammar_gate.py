from __future__ import annotations

from copy import deepcopy

from ulga.builders.build_reading_v1_practice_bank import build_synthetic_practice_bank
from ulga.query.a1_practice_item_grammar_gate import (
    ERR_FOCUS_TARGET_MISMATCH,
    ERR_GATE_MISSING,
    ERR_NO_MATCH,
    ERR_UNKNOWN_GRAMMAR_ID,
    validate_practice_item,
    validate_practice_items,
)
from ulga.validators.validate_reading_v1_practice_bank import validate_package


def _error_codes(report):
    return {error["code"] for error in report["errors"]}


def test_synthetic_practice_bank_passes_policy_and_all_grammar_gates():
    package = build_synthetic_practice_bank()

    policy_report = validate_package(package)
    grammar_report = validate_practice_items(package["items"])

    assert policy_report["validator_status"] == "PASS"
    assert grammar_report["all_items_pass"] is True
    assert grammar_report["item_count"] == 6
    assert grammar_report["pass_count"] == 6
    assert grammar_report["fail_count"] == 0
    assert all(report["matched_target_count"] == 1 for report in grammar_report["item_reports"])
    assert grammar_report["production_runtime_validator"] is False
    assert grammar_report["learner_state_write"] is False


def test_unknown_grammar_id_fails_closed():
    item = build_synthetic_practice_bank()["items"][0]
    item["content_binding"]["grammar_focus"] = ["GRAMMAR_UNKNOWN_A1"]
    item["grammar_gate"]["validation_targets"][0]["grammar_id"] = "GRAMMAR_UNKNOWN_A1"

    report = validate_practice_item(item)

    assert report["gate_status"] == "FAIL"
    assert ERR_UNKNOWN_GRAMMAR_ID in _error_codes(report)
    assert report["dispatcher_results"][0]["dispatch_status"] == "UNKNOWN_GRAMMAR_ID_FAIL_CLOSED"
    assert report["practice_item_gate_pass"] is False


def test_declared_grammar_that_does_not_match_text_is_blocked():
    item = build_synthetic_practice_bank()["items"][0]
    item["grammar_gate"]["validation_targets"][0]["text"] = "She is playing tennis."

    report = validate_practice_item(item)

    assert report["gate_status"] == "FAIL"
    assert ERR_NO_MATCH in _error_codes(report)
    assert report["matched_target_count"] == 0


def test_grammar_focus_and_target_set_must_match_exactly():
    item = build_synthetic_practice_bank()["items"][0]
    item["content_binding"]["grammar_focus"] = [
        "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
        "GRAMMAR_ARTICLES_BASIC",
    ]

    report = validate_practice_item(item)

    assert report["gate_status"] == "FAIL"
    assert ERR_FOCUS_TARGET_MISMATCH in _error_codes(report)


def test_missing_grammar_gate_is_blocked():
    item = build_synthetic_practice_bank()["items"][0]
    del item["grammar_gate"]

    report = validate_practice_item(item)

    assert report["gate_status"] == "FAIL"
    assert ERR_GATE_MISSING in _error_codes(report)


def test_gate_validation_does_not_mutate_practice_item():
    item = build_synthetic_practice_bank()["items"][0]
    before = deepcopy(item)

    report = validate_practice_item(item)

    assert report["gate_status"] == "PASS"
    assert report["input_mutated"] is False
    assert item == before
