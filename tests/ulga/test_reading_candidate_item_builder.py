import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.builders import build_reading_candidate_items as builder


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


def synthetic_index_payload():
    return {
        "schema_version": "RAZ_READING_AUTHORITY_INTAKE_QUERY_INDEX_V1",
        "items": [
            source_item("SRC_WHO", "The boy runs."),
            source_item("SRC_WHAT", "The girl has a kite."),
            source_item("SRC_WHERE", "The cat is on the bed."),
            source_item("SRC_CLOZE", "I eat rice."),
            source_item("SRC_ORDER", "I get up.\nI eat breakfast.\nI go to school.", "page_unit", 3),
        ],
    }


def test_builder_generates_all_v1_question_types_from_synthetic_sources():
    payload = builder.build_candidate_items(
        index_payload=synthetic_index_payload(),
        limit_per_question_type=1,
        write_outputs=False,
    )
    assert {item["question_type"] for item in payload["items"]} == set(builder.QUESTION_TYPES)
    assert payload["summary"]["total_items"] == 6
    assert payload["summary"]["status"] == "PASS"


def test_generated_items_follow_candidate_lifecycle_boundary():
    payload = builder.build_candidate_items(
        index_payload=synthetic_index_payload(),
        limit_per_question_type=1,
        write_outputs=False,
    )
    for item in payload["items"]:
        assert item["schema_version"] == "READING_PRACTICE_ITEM_V1"
        assert item["generation_task"] == builder.BUILDER_TASK
        assert item["status"] == "candidate_generated"
        assert item["skill"] == "reading"
        assert item["source"]["source_intake_id"]
        assert item["source"]["source_record_id"]
        assert item["source"]["generated_content"] is False
        assert item["lifecycle"]["authority_status"] == "candidate_only"
        assert item["lifecycle"]["promotion_status"] == "not_promoted"
        assert item["lifecycle"]["learner_facing"] is False
        assert item["validation"]["validator_status"] == "not_run"


def test_answer_models_are_compatible_with_question_types():
    payload = builder.build_candidate_items(
        index_payload=synthetic_index_payload(),
        limit_per_question_type=1,
        write_outputs=False,
    )
    answer_type_by_question_type = {item["question_type"]: item["answer_model"]["answer_type"] for item in payload["items"]}
    assert answer_type_by_question_type["literal_who"] == "single_choice"
    assert answer_type_by_question_type["literal_what"] == "single_choice"
    assert answer_type_by_question_type["literal_where"] == "single_choice"
    assert answer_type_by_question_type["true_false"] == "true_false"
    assert answer_type_by_question_type["sentence_ordering"] == "ordered_sequence"
    assert answer_type_by_question_type["cloze_vocabulary"] == "cloze_text"
