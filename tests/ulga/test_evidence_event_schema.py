import json
import subprocess
import sys
from pathlib import Path

import pytest

from ulga.validators.validate_evidence_event_schema import (
    SAMPLE_PATH,
    SCHEMA_PATH,
    ValidationError,
    load_json,
    validate_event_collection,
    validate_paths,
)


BASE_DIR = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_evidence_event_schema.py"


def clone_sample():
    return json.loads(json.dumps(load_json(SAMPLE_PATH)))


def test_valid_sample_events_pass():
    validate_paths()


def test_missing_required_event_id_fails():
    sample = clone_sample()
    del sample["events"][0]["event_id"]
    with pytest.raises(ValidationError, match="event_id"):
        validate_event_collection(sample)


def test_invalid_event_type_fails():
    sample = clone_sample()
    sample["events"][0]["event_type"] = "flashcard"
    with pytest.raises(ValidationError, match="event_type"):
        validate_event_collection(sample)


def test_empty_node_refs_fails():
    sample = clone_sample()
    sample["events"][0]["node_refs"] = []
    with pytest.raises(ValidationError, match="node_refs"):
        validate_event_collection(sample)


def test_invalid_node_type_fails():
    sample = clone_sample()
    sample["events"][0]["node_refs"][0]["node_type"] = "planner"
    with pytest.raises(ValidationError, match="node_type"):
        validate_event_collection(sample)


def test_invalid_node_ref_role_fails():
    sample = clone_sample()
    sample["events"][0]["node_refs"][0]["role"] = "ranking_signal"
    with pytest.raises(ValidationError, match="role"):
        validate_event_collection(sample)


def test_node_ref_weight_outside_range_fails():
    sample = clone_sample()
    sample["events"][0]["node_refs"][0]["weight"] = 1.5
    with pytest.raises(ValidationError, match="weight"):
        validate_event_collection(sample)


def test_score_outside_range_fails():
    sample = clone_sample()
    sample["events"][0]["score"] = -0.1
    with pytest.raises(ValidationError, match="score"):
        validate_event_collection(sample)


def test_confidence_outside_range_fails():
    sample = clone_sample()
    sample["events"][0]["confidence"]["value"] = 1.2
    with pytest.raises(ValidationError, match="confidence.value"):
        validate_event_collection(sample)


def test_duplicate_event_id_fails():
    sample = clone_sample()
    sample["events"][1]["event_id"] = sample["events"][0]["event_id"]
    with pytest.raises(ValidationError, match="duplicate event_id"):
        validate_event_collection(sample)


def test_duplicate_processing_idempotency_key_fails():
    sample = clone_sample()
    sample["events"][1]["processing_idempotency_key"] = sample["events"][0]["processing_idempotency_key"]
    with pytest.raises(ValidationError, match="duplicate processing_idempotency_key"):
        validate_event_collection(sample)


def test_validator_script_passes():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_schema_and_sample_files_exist():
    assert SCHEMA_PATH.exists()
    assert SAMPLE_PATH.exists()
