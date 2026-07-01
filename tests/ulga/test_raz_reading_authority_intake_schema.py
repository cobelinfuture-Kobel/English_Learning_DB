import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from ulga.validators.validate_raz_reading_authority_intake_schema import (
    SAMPLE_PATH,
    SCHEMA_PATH,
    VALIDATION_PATH,
    ValidationError,
    load_json,
    validate_paths,
    validate_payload,
    validate_record_semantics,
)


BASE_DIR = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_raz_reading_authority_intake_schema.py"
SCHEMA = load_json(SCHEMA_PATH)
VALIDATOR = Draft202012Validator(SCHEMA)
SAMPLE = load_json(SAMPLE_PATH)


def clone_record(index: int) -> dict:
    return json.loads(json.dumps(SAMPLE["records"][index]))


def test_valid_schema_and_samples_pass():
    validate_paths()


def test_valid_sentence_candidate_passes():
    result = validate_payload(clone_record(0))
    assert result["status"] == "PASS"
    assert result["records_checked"] == 1


def test_valid_page_unit_candidate_passes():
    result = validate_payload(clone_record(1))
    assert result["status"] == "PASS"


def test_valid_reuse_unit_candidate_passes():
    result = validate_payload(clone_record(2))
    assert result["status"] == "PASS"


def test_generated_content_true_is_blocked():
    record = clone_record(0)
    record["source_traceability"]["generated_content"] = True
    with pytest.raises(JsonSchemaValidationError, match="False was expected"):
        VALIDATOR.validate(record)


def test_promotion_allowed_true_is_blocked():
    record = clone_record(0)
    record["authority"]["promotion_allowed"] = True
    with pytest.raises(JsonSchemaValidationError, match="False was expected"):
        VALIDATOR.validate(record)


def test_authority_status_not_candidate_only_is_blocked():
    record = clone_record(0)
    record["authority"]["authority_status"] = "promoted"
    with pytest.raises(JsonSchemaValidationError, match="candidate_only"):
        VALIDATOR.validate(record)


def test_missing_source_traceability_is_blocked():
    record = clone_record(0)
    del record["source_traceability"]
    with pytest.raises(JsonSchemaValidationError, match="source_traceability"):
        VALIDATOR.validate(record)


def test_missing_clean_text_is_blocked():
    record = clone_record(0)
    del record["text"]["clean_text"]
    with pytest.raises(JsonSchemaValidationError, match="clean_text"):
        VALIDATOR.validate(record)


def test_invalid_source_level_is_blocked():
    record = clone_record(0)
    record["source_level"] = "Z"
    with pytest.raises(JsonSchemaValidationError, match="source_level"):
        VALIDATOR.validate(record)


def test_query_layer_ready_false_is_not_schema_blocker():
    record = clone_record(2)
    record["query_layer_ready"] = False
    VALIDATOR.validate(record)
    warnings = validate_record_semantics(record)
    assert "query_layer_ready false for G-W is not a schema blocker" in warnings


def test_object_records_payload_is_accepted():
    result = validate_payload(load_json(SAMPLE_PATH))
    assert result["status"] == "PASS"
    assert result["records_checked"] == 3


def test_list_payload_is_accepted():
    result = validate_payload(load_json(SAMPLE_PATH)["records"])
    assert result["status"] == "PASS"
    assert result["records_checked"] == 3


def test_unit_type_conflicts_with_source_type_is_blocked():
    record = clone_record(1)
    record["source_traceability"]["source_type"] = "raz_enriched_sentence"
    with pytest.raises(ValidationError, match="unit_type conflicts with source_type"):
        validate_record_semantics(record)


def test_empty_clean_text_is_blocked_semantically():
    record = clone_record(0)
    record["text"]["clean_text"] = "   "
    with pytest.raises(ValidationError, match="empty clean_text"):
        validate_record_semantics(record)


def test_validator_script_passes_and_writes_reports():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    validation = load_json(VALIDATION_PATH)
    assert validation["status"] == "PASS"
