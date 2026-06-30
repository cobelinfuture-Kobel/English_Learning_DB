import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from ulga.validators.validate_learner_event_log import (
    load_schema,
    validate_event_schema,
    validate_event_collection,
    normalize_timestamp_to_utc,
    main,
)

BASE_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = BASE_DIR / "ulga" / "schemas" / "learner_event_log_schema.json"

@pytest.fixture(scope="module")
def schema():
    return load_schema(SCHEMA_PATH)

def make_valid_event(event_id="evt_001", occurred_at="2026-06-18T11:10:52Z"):
    return {
        "event_id": event_id,
        "learner_id": "learner:usr_001",
        "session_id": "sess_20260618_91823ab",
        "event_type": "answer_submitted",
        "occurred_at": occurred_at,
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
            "validator_version": "ULGA-Val-S9Z4",
        },
    }

def test_valid_collection_passes(schema):
    events = [
        make_valid_event("evt_001", "2026-06-18T11:10:52Z"),
        make_valid_event("evt_002", "2026-06-18T11:11:15Z"),
    ]
    report = validate_event_collection(events, schema)
    assert report["status"] == "PASS"
    assert report["summary"]["total_events"] == 2
    assert report["summary"]["valid_events"] == 2
    assert report["summary"]["invalid_events"] == 0
    assert len(report["normalized_events"]) == 2
    assert report["normalized_events"][0]["event_id"] == "evt_001"
    assert report["normalized_events"][0]["occurred_at_utc"] == "2026-06-18T11:10:52Z"

def test_wrapper_object_with_events_passes(schema, tmp_path):
    events_wrapper = {
        "events": [
            make_valid_event("evt_001", "2026-06-18T11:10:52Z"),
            make_valid_event("evt_002", "2026-06-18T11:11:15Z"),
        ]
    }
    input_file = tmp_path / "events.json"
    with input_file.open("w", encoding="utf-8") as f:
        json.dump(events_wrapper, f)
        
    test_args = ["validate_learner_event_log.py", "--input", str(input_file), "--schema", str(SCHEMA_PATH)]
    with patch.object(sys, "argv", test_args):
        exit_code = main()
    assert exit_code == 0

def test_invalid_single_event_schema_collected_as_error(schema):
    event = make_valid_event("evt_001")
    event["learner_id"] = "invalid_id_format"  # Fails schema regex
    
    report = validate_event_collection([event], schema)
    assert report["status"] == "FAIL"
    assert report["summary"]["invalid_events"] == 1
    assert len(report["errors"]) > 0
    assert report["errors"][0]["event_index"] == 0
    assert report["errors"][0]["event_id"] == "evt_001"
    assert report["errors"][0]["code"] == "schema_validation_failed"
    assert "learner_id" in report["errors"][0]["path"]

def test_duplicate_event_id_inside_collection_fails(schema):
    events = [
        make_valid_event("evt_dup"),
        make_valid_event("evt_dup"),
    ]
    report = validate_event_collection(events, schema)
    assert report["status"] == "FAIL"
    assert report["summary"]["invalid_events"] == 1  # The second is invalid
    assert report["summary"]["valid_events"] == 1  # The first is valid
    assert "evt_dup" in report["summary"]["duplicate_event_ids"]
    
    dup_errors = [e for e in report["errors"] if e["code"] == "duplicate_event_id"]
    assert len(dup_errors) == 1
    assert dup_errors[0]["event_index"] == 1
    assert dup_errors[0]["event_id"] == "evt_dup"
    assert dup_errors[0]["duplicate_event_id"] == "evt_dup"

def test_existing_index_duplicate_fails(schema):
    events = [
        make_valid_event("evt_existing"),
    ]
    report = validate_event_collection(events, schema, existing_event_ids={"evt_existing"})
    assert report["status"] == "FAIL"
    assert report["summary"]["invalid_events"] == 1
    
    existing_errors = [e for e in report["errors"] if e["code"] == "event_id_already_exists"]
    assert len(existing_errors) == 1
    assert existing_errors[0]["event_index"] == 0
    assert existing_errors[0]["event_id"] == "evt_existing"

def test_timezone_offset_normalized_to_utc(schema):
    # Test individual normalization
    assert normalize_timestamp_to_utc("2026-06-18T19:10:52+08:00") == "2026-06-18T11:10:52Z"
    assert normalize_timestamp_to_utc("2026-06-18T11:10:52Z") == "2026-06-18T11:10:52Z"
    
    # Test inside collection report
    events = [
        make_valid_event("evt_001", "2026-06-18T19:10:52+08:00"),
    ]
    report = validate_event_collection(events, schema)
    assert report["status"] == "PASS"
    assert report["normalized_events"][0]["occurred_at_utc"] == "2026-06-18T11:10:52Z"

def test_non_chronological_event_order_warning(schema):
    events = [
        make_valid_event("evt_001", "2026-06-18T12:00:00Z"),
        make_valid_event("evt_002", "2026-06-18T11:00:00Z"), # Out of order!
        make_valid_event("evt_003", "2026-06-18T13:00:00Z"),
    ]
    report = validate_event_collection(events, schema)
    assert report["status"] == "PASS_WITH_WARNINGS"
    assert report["summary"]["warning_count"] == 1
    
    warnings = [w for w in report["warnings"] if w["code"] == "non_chronological_order"]
    assert len(warnings) == 1
    assert warnings[0]["out_of_order_indexes"] == [1]

def test_requires_review_produces_quarantine(schema):
    event = make_valid_event("evt_review")
    event["quality_flags"]["requires_review"] = True
    
    report = validate_event_collection([event], schema)
    assert report["status"] == "PASS_WITH_QUARANTINE"
    assert report["summary"]["quarantined_events"] == 1
    assert report["summary"]["valid_events"] == 0
    assert len(report["quarantine"]) == 1
    assert report["quarantine"][0]["event_index"] == 0
    assert report["quarantine"][0]["event_id"] == "evt_review"
    assert report["quarantine"][0]["code"] == "requires_review"

def test_valid_event_false_produces_warning(schema):
    event = make_valid_event("evt_invalid_prod")
    event["quality_flags"]["valid_event"] = False
    
    report = validate_event_collection([event], schema)
    assert report["status"] == "PASS_WITH_WARNINGS"
    assert report["summary"]["warning_count"] == 1
    
    warnings = [w for w in report["warnings"] if w["code"] == "producer_marked_event_invalid"]
    assert len(warnings) == 1
    assert warnings[0]["event_index"] == 0
    assert warnings[0]["event_id"] == "evt_invalid_prod"

def test_exposure_seen_invalid_evidence_flags_fails(schema):
    event = make_valid_event("evt_exposure")
    event["event_type"] = "exposure_seen"
    event["evidence_flags"]["counts_as_mastery_update"] = True  # Forbidden for exposure
    
    report = validate_event_collection([event], schema)
    assert report["status"] == "FAIL"
    assert any(e["code"] == "exposure_seen_invalid_evidence_flags" for e in report["errors"])

def test_hint_used_without_used_hint_fails(schema):
    event = make_valid_event("evt_hint")
    event["event_type"] = "hint_used"
    event["attempt"]["used_hint"] = False  # Must be true for hint_used
    
    report = validate_event_collection([event], schema)
    assert report["status"] == "FAIL"
    assert any(e["code"] == "hint_used_without_used_hint" for e in report["errors"])

def test_assessment_event_missing_score_fails(schema):
    event = make_valid_event("evt_assess")
    event["event_type"] = "assessment_attempt"
    event["attempt"]["score"] = None  # Score must be numeric for assessment
    event["evidence_flags"]["counts_as_assessment"] = True
    
    report = validate_event_collection([event], schema)
    assert report["status"] == "FAIL"
    assert any(e["code"] == "assessment_event_missing_score" for e in report["errors"])

def test_mastery_update_without_target_nodes_fails(schema):
    event = make_valid_event("evt_mastery")
    event["evidence_flags"]["counts_as_mastery_update"] = True
    # Make all target arrays empty
    event["target_nodes"]["vocabulary"] = []
    event["target_nodes"]["grammar"] = []
    event["target_nodes"]["pattern"] = []
    event["target_nodes"]["chunk"] = []
    
    report = validate_event_collection([event], schema)
    assert report["status"] == "FAIL"
    assert any(e["code"] == "mastery_update_without_target_nodes" for e in report["errors"])

def test_cli_writes_report_file(tmp_path):
    events = [make_valid_event("evt_cli")]
    input_file = tmp_path / "events.json"
    report_file = tmp_path / "report.json"
    
    with input_file.open("w", encoding="utf-8") as f:
        json.dump(events, f)
        
    test_args = [
        "validate_learner_event_log.py",
        "--input", str(input_file),
        "--schema", str(SCHEMA_PATH),
        "--report", str(report_file),
    ]
    with patch.object(sys, "argv", test_args):
        exit_code = main()
        
    assert exit_code == 0
    assert report_file.exists()
    
    with report_file.open("r", encoding="utf-8") as f:
        report_data = json.load(f)
    assert report_data["status"] == "PASS"

def test_cli_returns_exit_code_1_on_fail(tmp_path):
    # Create invalid event (invalid learner ID)
    event = make_valid_event("evt_cli_fail")
    event["learner_id"] = "invalid"
    
    input_file = tmp_path / "events.json"
    with input_file.open("w", encoding="utf-8") as f:
        json.dump([event], f)
        
    test_args = [
        "validate_learner_event_log.py",
        "--input", str(input_file),
        "--schema", str(SCHEMA_PATH),
    ]
    with patch.object(sys, "argv", test_args):
        exit_code = main()
        
    assert exit_code == 1
