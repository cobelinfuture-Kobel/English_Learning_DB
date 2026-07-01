import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from ulga.validators.validate_raz_reading_authority_intake_query_index import (
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
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_raz_reading_authority_intake_query_index.py"
SCHEMA = load_json(SCHEMA_PATH)
VALIDATOR = Draft202012Validator(SCHEMA)
SAMPLE = load_json(SAMPLE_PATH)


def clone_record(index: int) -> dict:
    return json.loads(json.dumps(SAMPLE["records"][index]))


def test_sample_fixture_validates():
    validate_paths()


def test_af_approved_candidate_is_accepted():
    result = validate_payload(clone_record(0))
    assert result["status"] == "PASS"
    assert result["records_checked"] == 1


def test_gw_approved_candidate_is_rejected():
    record = clone_record(3)
    record["query_status"] = "approved_candidate"
    record["query_layer_ready"] = True
    record["query_layer_approved"] = True
    with pytest.raises(ValidationError, match="approved_candidate"):
        validate_record_semantics(record)


def test_promotion_allowed_true_is_rejected():
    record = clone_record(0)
    record["authority"]["promotion_allowed"] = True
    with pytest.raises(JsonSchemaValidationError, match="False was expected"):
        VALIDATOR.validate(record)


def test_final_eligible_true_is_rejected():
    record = clone_record(0)
    record["authority"]["final_eligible"] = True
    with pytest.raises(JsonSchemaValidationError, match="False was expected"):
        VALIDATOR.validate(record)


def test_authority_status_not_candidate_only_is_rejected():
    record = clone_record(0)
    record["authority"]["authority_status"] = "promoted"
    with pytest.raises(JsonSchemaValidationError, match="candidate_only"):
        VALIDATOR.validate(record)


def test_unknown_warning_family_is_rejected():
    record = clone_record(0)
    record["warnings"]["families"] = ["UNKNOWN_WARNING"]
    record["warnings"]["count"] = 1
    with pytest.raises(JsonSchemaValidationError, match="UNKNOWN_WARNING"):
        VALIDATOR.validate(record)


def test_warnings_remain_non_blocking():
    record = clone_record(4)
    VALIDATOR.validate(record)
    validate_record_semantics(record)
    assert record["warnings"]["blocking"] is False


def test_validator_cli_produces_pass_on_sample_fixture():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "ulga/schemas/sample_raz_reading_authority_intake_query_index.json"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"status": "PASS"' in result.stdout
    validation = load_json(VALIDATION_PATH)
    assert validation["status"] == "PASS"
