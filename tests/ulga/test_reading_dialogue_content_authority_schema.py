import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from ulga.validators.validate_reading_dialogue_content_authority_schema import (
    DIALOGUE_SAMPLE_PATH,
    DIALOGUE_SCHEMA_PATH,
    READING_SAMPLE_PATH,
    READING_SCHEMA_PATH,
    ValidationError,
    load_json,
    validate_dialogue_semantics,
    validate_paths,
    validate_reading_semantics,
)


BASE_DIR = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_reading_dialogue_content_authority_schema.py"

READING_SCHEMA = load_json(READING_SCHEMA_PATH)
DIALOGUE_SCHEMA = load_json(DIALOGUE_SCHEMA_PATH)
READING_VALIDATOR = Draft202012Validator(READING_SCHEMA)
DIALOGUE_VALIDATOR = Draft202012Validator(DIALOGUE_SCHEMA)


def clone_reading_sample():
    return json.loads(json.dumps(load_json(READING_SAMPLE_PATH)))


def clone_dialogue_sample():
    return json.loads(json.dumps(load_json(DIALOGUE_SAMPLE_PATH)))


def test_valid_schema_and_samples_pass():
    validate_paths()


def test_reading_sample_has_linkage_fields():
    sample = clone_reading_sample()
    assert sample["source_seed_refs"] == []
    assert sample["authority_refs"]["grammar_refs"] == ["GN_have_has"]
    assert sample["authority_status"] == "candidate_only"
    assert sample["promotion_status"] == "not_promoted"
    assert sample["final_eligible"] is False


def test_dialogue_sample_has_linkage_fields():
    sample = clone_dialogue_sample()
    assert sample["source_seed_refs"] == []
    assert sample["authority_refs"]["grammar_refs"] == ["GN_would_like"]
    assert sample["authority_status"] == "candidate_only"
    assert sample["promotion_status"] == "not_promoted"
    assert sample["final_eligible"] is False


def test_reading_missing_text_fails():
    sample = clone_reading_sample()
    del sample["text"]
    with pytest.raises(JsonSchemaValidationError, match="text"):
        READING_VALIDATOR.validate(sample)


def test_reading_invalid_content_type_fails():
    sample = clone_reading_sample()
    sample["content_type"] = "dialogue"
    with pytest.raises(JsonSchemaValidationError, match="reading"):
        READING_VALIDATOR.validate(sample)


def test_reading_additional_property_fails():
    sample = clone_reading_sample()
    sample["runtime_status"] = "approved_for_delivery"
    with pytest.raises(JsonSchemaValidationError, match="Additional properties are not allowed"):
        READING_VALIDATOR.validate(sample)


def test_missing_source_seed_refs_fails():
    sample = clone_reading_sample()
    del sample["source_seed_refs"]
    with pytest.raises(JsonSchemaValidationError, match="source_seed_refs"):
        READING_VALIDATOR.validate(sample)


def test_missing_authority_refs_fails():
    sample = clone_reading_sample()
    del sample["authority_refs"]
    with pytest.raises(JsonSchemaValidationError, match="authority_refs"):
        READING_VALIDATOR.validate(sample)


def test_missing_unresolved_authority_refs_fails():
    sample = clone_dialogue_sample()
    del sample["unresolved_authority_refs"]
    with pytest.raises(JsonSchemaValidationError, match="unresolved_authority_refs"):
        DIALOGUE_VALIDATOR.validate(sample)


def test_reading_sentence_count_zero_fails():
    sample = clone_reading_sample()
    sample["sentence_count"] = 0
    with pytest.raises(JsonSchemaValidationError, match="minimum"):
        READING_VALIDATOR.validate(sample)


def test_dialogue_turn_count_mismatch_fails_semantic_validator():
    sample = clone_dialogue_sample()
    sample["turn_count"] = 3
    with pytest.raises(ValidationError, match="turn_count must match turns length"):
        validate_dialogue_semantics(sample)


def test_dialogue_too_few_turns_fails_schema():
    sample = clone_dialogue_sample()
    sample["turns"] = sample["turns"][:1]
    sample["turn_count"] = 1
    with pytest.raises(JsonSchemaValidationError, match="is too short"):
        DIALOGUE_VALIDATOR.validate(sample)


def test_dialogue_invalid_source_type_fails():
    sample = clone_dialogue_sample()
    sample["source_type"] = "generator_live"
    with pytest.raises(JsonSchemaValidationError, match="source_type"):
        DIALOGUE_VALIDATOR.validate(sample)


def test_invalid_authority_linkage_status_fails():
    sample = clone_reading_sample()
    sample["authority_linkage_status"] = "done"
    with pytest.raises(JsonSchemaValidationError, match="authority_linkage_status"):
        READING_VALIDATOR.validate(sample)


def test_dialogue_additional_property_fails():
    sample = clone_dialogue_sample()
    sample["delivery_ready"] = True
    with pytest.raises(JsonSchemaValidationError, match="Additional properties are not allowed"):
        DIALOGUE_VALIDATOR.validate(sample)


def test_reading_word_count_less_than_sentence_count_fails_semantic_validator():
    sample = clone_reading_sample()
    sample["word_count"] = 2
    sample["sentence_count"] = 3
    with pytest.raises(ValidationError, match="word_count must match simple whitespace token count"):
        validate_reading_semantics(sample)


def test_candidate_final_eligible_true_fails():
    sample = clone_reading_sample()
    sample["final_eligible"] = True
    with pytest.raises(ValidationError, match="final_eligible false"):
        validate_reading_semantics(sample)


def test_candidate_promotion_status_promoted_fails():
    sample = clone_dialogue_sample()
    sample["promotion_status"] = "promoted"
    with pytest.raises(ValidationError, match="promotion_status not_promoted"):
        validate_dialogue_semantics(sample)


def test_fully_linked_with_unresolved_refs_fails():
    sample = clone_reading_sample()
    sample["authority_linkage_status"] = "fully_linked"
    sample["unresolved_authority_refs"]["grammar"] = [
        {
            "source_field": "grammar_refs",
            "unresolved_value": "GN_unknown",
            "reason": "not_mapped",
        }
    ]
    with pytest.raises(ValidationError, match="fully_linked payload cannot keep unresolved_authority_refs.grammar"):
        validate_reading_semantics(sample)


def test_source_seed_ref_accepts_future_raz_level_g():
    sample = clone_reading_sample()
    sample["source_seed_refs"] = [
        {
            "seed_id": "RAZ_G_1001_REUSE_000001",
            "seed_type": "reuse_unit",
            "source": "RAZ",
            "source_level": "G",
            "source_book_id": "1001",
            "source_page_number": 3,
        }
    ]
    READING_VALIDATOR.validate(sample)
    validate_reading_semantics(sample)


def test_additional_properties_still_rejected_after_patch():
    sample = clone_reading_sample()
    sample["unexpected_linkage_flag"] = True
    with pytest.raises(JsonSchemaValidationError, match="Additional properties are not allowed"):
        READING_VALIDATOR.validate(sample)


def test_dialogue_turn_count_still_checked():
    sample = clone_dialogue_sample()
    sample["turn_count"] = 1
    with pytest.raises(ValidationError, match="turn_count must match turns length|turn_count must be >= 2"):
        validate_dialogue_semantics(sample)


def test_validator_script_passes():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
