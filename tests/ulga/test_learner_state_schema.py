import json
import subprocess
import sys
from pathlib import Path

import pytest

from ulga.validators.validate_learner_state_schema import (
    SAMPLE_PATH,
    SCHEMA_PATH,
    ValidationError,
    load_json,
    validate_learner_state_collection,
    validate_paths,
)


BASE_DIR = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_learner_state_schema.py"


def clone_sample():
    return json.loads(json.dumps(load_json(SAMPLE_PATH)))


def test_valid_sample_learner_state_passes():
    validate_paths()


def test_missing_learner_id_fails():
    sample = clone_sample()
    del sample["learner_state_records"][0]["learner_id"]
    with pytest.raises(ValidationError, match="learner_id"):
        validate_learner_state_collection(sample)


def test_invalid_node_type_fails():
    sample = clone_sample()
    sample["learner_state_records"][0]["node_type"] = "planner"
    with pytest.raises(ValidationError, match="node_type"):
        validate_learner_state_collection(sample)


def test_invalid_mastery_band_fails():
    sample = clone_sample()
    sample["learner_state_records"][0]["mastery_band"] = "expert"
    with pytest.raises(ValidationError, match="mastery_band"):
        validate_learner_state_collection(sample)


def test_mastery_score_outside_range_fails():
    sample = clone_sample()
    sample["learner_state_records"][0]["mastery_score"] = 1.2
    with pytest.raises(ValidationError, match="mastery_score"):
        validate_learner_state_collection(sample)


def test_decay_adjusted_score_outside_range_fails():
    sample = clone_sample()
    sample["learner_state_records"][0]["decay_adjusted_score"] = -0.1
    with pytest.raises(ValidationError, match="decay_adjusted_score"):
        validate_learner_state_collection(sample)


def test_mastery_band_mismatch_fails():
    sample = clone_sample()
    sample["learner_state_records"][0]["mastery_score"] = 0.45
    with pytest.raises(ValidationError, match="mastery_band does not match mastery_score range"):
        validate_learner_state_collection(sample)


def test_exposure_count_negative_fails():
    sample = clone_sample()
    sample["learner_state_records"][0]["exposure_count"] = -1
    with pytest.raises(ValidationError, match="exposure_count"):
        validate_learner_state_collection(sample)


def test_counts_exceed_exposure_fails():
    sample = clone_sample()
    sample["learner_state_records"][0]["correct_count"] = 10
    sample["learner_state_records"][0]["incorrect_count"] = 10
    sample["learner_state_records"][0]["exposure_count"] = 12
    with pytest.raises(ValidationError, match="must not exceed exposure_count"):
        validate_learner_state_collection(sample)


def test_confidence_outside_range_fails():
    sample = clone_sample()
    sample["learner_state_records"][0]["confidence"]["value"] = 1.1
    with pytest.raises(ValidationError, match="confidence.value"):
        validate_learner_state_collection(sample)


def test_invalid_source_authority_name_fails():
    sample = clone_sample()
    sample["learner_state_records"][0]["source"]["authority_name"] = "PlannerAuthority"
    with pytest.raises(ValidationError, match="source.authority_name"):
        validate_learner_state_collection(sample)


def test_duplicate_learner_node_pair_fails():
    sample = clone_sample()
    sample["learner_state_records"][1]["learner_id"] = sample["learner_state_records"][0]["learner_id"]
    sample["learner_state_records"][1]["node_id"] = sample["learner_state_records"][0]["node_id"]
    with pytest.raises(ValidationError, match="duplicate learner_id \\+ node_id"):
        validate_learner_state_collection(sample)


def test_duplicate_processing_idempotency_key_fails():
    sample = clone_sample()
    sample["learner_state_records"][1]["processing_idempotency_key"] = sample["learner_state_records"][0]["processing_idempotency_key"]
    with pytest.raises(ValidationError, match="duplicate processing_idempotency_key"):
        validate_learner_state_collection(sample)


def test_cold_start_unknown_record_passes():
    sample = clone_sample()
    cold_start_record = sample["learner_state_records"][3]
    assert cold_start_record["mastery_band"] == "unknown"
    validate_learner_state_collection(
        {
            "contract_version": sample["contract_version"],
            "learner_state_records": [cold_start_record],
        }
    )


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
