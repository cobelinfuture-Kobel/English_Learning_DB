import copy
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.builders import build_reading_candidate_items as builder
from ulga.validators import validate_reading_practice_items as validator


def source_item(intake_id, text, source_type="sentence_candidate", sentence_count=1):
    return {
        "intake_id": intake_id,
        "source_type": source_type,
        "level": "A",
        "book_id": "RAZ_A_TEST_BOOK",
        "page_number": 1,
        "sentence_count": sentence_count,
        "clean_text": text,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "generated_content": False,
        "source_traceability": {
            "source_type": source_type,
            "source_path": "tests/fixtures/raz_a_test.json",
            "source_record_id": f"{intake_id}_SRC",
            "generated_content": False,
        },
        "query_tags": {
            "theme_hints": ["Test"],
            "grammar_tags": [],
            "pattern_tags": [],
            "vocabulary_tags": [],
            "reusability_tags": ["exercise_seed"],
        },
    }


def valid_candidate_payload():
    index_payload = {
        "schema_version": "RAZ_READING_AUTHORITY_INTAKE_QUERY_INDEX_V1",
        "items": [
            source_item("SRC_WHO", "The boy runs."),
            source_item("SRC_WHAT", "The girl has a kite."),
            source_item("SRC_WHERE", "The cat is on the bed."),
            source_item("SRC_CLOZE", "I eat rice."),
            source_item("SRC_ORDER", "I get up.\nI eat breakfast.\nI go to school.", "page_unit", 3),
        ],
    }
    return builder.build_candidate_items(index_payload=index_payload, limit_per_question_type=1, write_outputs=False)


def test_validator_passes_valid_s17_candidate_payload():
    payload = valid_candidate_payload()
    result = validator.validate_payload(payload, payload["summary"])
    assert result["status"] == "PASS"
    assert result["total_items_checked"] == 6
    assert result["errors"] == []


def test_validator_rejects_promoted_lifecycle():
    payload = valid_candidate_payload()
    payload = copy.deepcopy(payload)
    payload["items"][0]["lifecycle"]["promotion_status"] = "promoted"
    result = validator.validate_payload(payload, payload["summary"])
    assert result["status"] == "FAIL"
    assert any("lifecycle_promoted" in error for error in result["errors"])


def test_validator_rejects_unsupported_answer():
    payload = valid_candidate_payload()
    payload = copy.deepcopy(payload)
    item = next(item for item in payload["items"] if item["question_type"] == "literal_what")
    item["answer_model"]["correct_answer"] = "a dragon"
    result = validator.validate_payload(payload, payload["summary"])
    assert result["status"] == "FAIL"
    assert any("answer_not_supported_by_evidence" in error for error in result["errors"])


def test_validator_rejects_incompatible_answer_type():
    payload = valid_candidate_payload()
    payload = copy.deepcopy(payload)
    item = next(item for item in payload["items"] if item["question_type"] == "true_false")
    item["answer_model"]["answer_type"] = "single_choice"
    result = validator.validate_payload(payload, payload["summary"])
    assert result["status"] == "FAIL"
    assert any("answer_type_mismatch" in error for error in result["errors"])
