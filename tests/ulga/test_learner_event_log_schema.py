import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError


BASE_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = BASE_DIR / "ulga" / "schemas" / "learner_event_log_schema.json"


def load_schema():
    with SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


SCHEMA = load_schema()
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def make_valid_event():
    return {
        "event_id": "evt_20260618_00001a7d",
        "learner_id": "learner:usr_98124b",
        "session_id": "sess_20260618_91823ab",
        "event_type": "answer_submitted",
        "occurred_at": "2026-06-18T19:10:52Z",
        "source_type": "exercise",
        "source_id": "ex_vocab_match_a1",
        "item_id": "item_v_a1_042",
        "learning_opportunity_id": "LO_A1_000014",
        "target_nodes": {
            "vocabulary": ["vocab:banana"],
            "grammar": ["grammar:EGP_000142"],
            "pattern": ["pattern:PATTERN_NODE_000014"],
            "theme": ["theme:a1_food_and_drink"],
            "chunk": [],
        },
        "attempt": {
            "response": "banana",
            "expected_answer": "banana",
            "is_correct": True,
            "score": 1.0,
            "max_score": 1.0,
            "attempt_number": 1,
            "used_hint": False,
            "response_time_ms": 1420,
        },
        "evidence_flags": {
            "counts_as_exposure": True,
            "counts_as_practice": True,
            "counts_as_assessment": False,
            "counts_as_mastery_update": True,
            "counts_as_reinforcement": False,
        },
        "quality_flags": {
            "valid_event": True,
            "has_target_nodes": True,
            "has_score": True,
            "requires_review": False,
        },
        "metadata": {
            "level": "A1",
            "theme": "a1_food_and_drink",
            "generator_version": "ULGA-Gen-1.4.2",
            "validator_version": "ULGA-Val-S9Z3",
        },
    }


def assert_valid(event):
    VALIDATOR.validate(event)


def assert_invalid(event, match):
    with pytest.raises(ValidationError, match=match):
        VALIDATOR.validate(event)


def test_valid_answer_submitted_event_passes():
    assert_valid(make_valid_event())


def test_valid_exposure_seen_with_nullable_attempt_fields_passes():
    event = make_valid_event()
    event["event_type"] = "exposure_seen"
    event["source_type"] = "reading"
    event["attempt"] = {
        "response": None,
        "expected_answer": None,
        "is_correct": None,
        "score": None,
        "max_score": None,
        "attempt_number": None,
        "used_hint": False,
        "response_time_ms": None,
    }
    event["evidence_flags"] = {
        "counts_as_exposure": True,
        "counts_as_practice": False,
        "counts_as_assessment": False,
        "counts_as_mastery_update": False,
        "counts_as_reinforcement": False,
    }
    event["quality_flags"]["has_score"] = False
    assert_valid(event)


def test_valid_assessment_attempt_event_passes():
    event = make_valid_event()
    event["event_type"] = "assessment_attempt"
    event["source_type"] = "assessment"
    event["attempt"]["score"] = 0.8
    event["attempt"]["max_score"] = 1.0
    event["evidence_flags"]["counts_as_assessment"] = True
    assert_valid(event)


def test_invalid_unknown_event_type_fails():
    event = make_valid_event()
    event["event_type"] = "flashcard_completed"
    assert_invalid(event, "event_type")


def test_invalid_learner_id_format_fails():
    event = make_valid_event()
    event["learner_id"] = "usr_98124b"
    assert_invalid(event, "learner_id")


def test_invalid_timestamp_fails():
    event = make_valid_event()
    event["occurred_at"] = "not-a-timestamp"
    assert_invalid(event, "occurred_at")


def test_assessment_event_without_score_fails():
    event = make_valid_event()
    event["event_type"] = "assessment_attempt"
    event["source_type"] = "assessment"
    event["attempt"]["score"] = None
    event["attempt"]["max_score"] = 1.0
    event["evidence_flags"]["counts_as_assessment"] = True
    assert_invalid(event, "score")


def test_mastery_update_without_target_nodes_fails():
    event = make_valid_event()
    event["target_nodes"]["vocabulary"] = []
    event["target_nodes"]["grammar"] = []
    event["target_nodes"]["pattern"] = []
    event["target_nodes"]["chunk"] = []
    assert_invalid(event, "target_nodes")


def test_exposure_event_with_mastery_update_flag_fails():
    event = make_valid_event()
    event["event_type"] = "exposure_seen"
    event["source_type"] = "reading"
    event["attempt"] = {
        "response": None,
        "expected_answer": None,
        "is_correct": None,
        "score": None,
        "max_score": None,
        "attempt_number": None,
        "used_hint": False,
        "response_time_ms": None,
    }
    event["evidence_flags"] = {
        "counts_as_exposure": True,
        "counts_as_practice": False,
        "counts_as_assessment": False,
        "counts_as_mastery_update": True,
        "counts_as_reinforcement": False,
    }
    assert_invalid(event, "counts_as_mastery_update")


def test_hint_used_event_with_used_hint_false_fails():
    event = make_valid_event()
    event["event_type"] = "hint_used"
    event["attempt"]["used_hint"] = False
    assert_invalid(event, "used_hint")
