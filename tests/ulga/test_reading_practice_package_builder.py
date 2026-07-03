import copy
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.builders import build_reading_candidate_items as item_builder
from ulga.builders import build_reading_practice_package as package_builder


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


def valid_items_payload():
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
    return item_builder.build_candidate_items(index_payload=index_payload, limit_per_question_type=1, write_outputs=False)


def test_package_builder_packages_valid_candidate_items():
    items_payload = valid_items_payload()
    payload = package_builder.build_package(items_payload=items_payload, items_summary=items_payload["summary"], max_items=20, write_outputs=False)
    assert payload["schema_version"] == "READING_PRACTICE_PACKAGE_CANDIDATE_V1"
    assert payload["summary"]["status"] == "PASS"
    assert payload["package"]["item_count"] == 6
    assert payload["package"]["authority_status"] == "candidate_only"
    assert payload["package"]["promotion_status"] == "not_promoted"
    assert payload["package"]["learner_facing"] is False
    assert len(payload["package"]["answer_key"]) == 6


def test_package_builder_preserves_item_traceability_and_lifecycle():
    items_payload = valid_items_payload()
    payload = package_builder.build_package(items_payload=items_payload, items_summary=items_payload["summary"], max_items=2, write_outputs=False)
    assert payload["package"]["item_count"] == 2
    for item in payload["package"]["items"]:
        assert item["source"]["source_intake_id"]
        assert item["source"]["source_record_id"]
        assert item["source"]["source_path"]
        assert item["source"]["generated_content"] is False
        assert item["lifecycle"]["authority_status"] == "candidate_only"
        assert item["lifecycle"]["promotion_status"] == "not_promoted"
        assert item["lifecycle"]["learner_facing"] is False


def test_package_builder_blocks_invalid_items_when_validation_gate_fails():
    items_payload = valid_items_payload()
    items_payload = copy.deepcopy(items_payload)
    items_payload["items"][0]["answer_model"]["correct_answer"] = "a dragon"
    payload = package_builder.build_package(items_payload=items_payload, items_summary=items_payload["summary"], max_items=20, write_outputs=False)
    assert payload["summary"]["status"] == "FAIL"
    assert payload["package"]["item_count"] == 0
    assert "validation_gate_failed_no_items_packaged" in payload["summary"]["warnings"]


def test_package_builder_allows_empty_candidate_package_with_warning():
    items_payload = {
        "schema_version": "READING_PRACTICE_ITEMS_CANDIDATE_OUTPUT_V1",
        "item_schema_version": "READING_PRACTICE_ITEM_V1",
        "builder_task": "RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation",
        "source_policy": {},
        "generation_policy": {},
        "items": [],
        "summary": {"schema_version": "READING_PRACTICE_ITEMS_CANDIDATE_SUMMARY_V1", "total_items": 0},
    }
    payload = package_builder.build_package(items_payload=items_payload, items_summary=items_payload["summary"], max_items=20, write_outputs=False)
    assert payload["summary"]["status"] == "PASS_WITH_WARNINGS"
    assert payload["package"]["status"] == "empty_candidate_package"
    assert payload["package"]["item_count"] == 0
    assert "no_items_packaged" in payload["summary"]["warnings"]
