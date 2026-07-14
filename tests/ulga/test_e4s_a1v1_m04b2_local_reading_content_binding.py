from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_local_reading_practice_bank import (
    _canonical_json,
    materialize_local_reading_bank,
)
from ulga.validators.validate_a1_a1plus_local_reading_practice_bank import (
    validate_materialization,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fixture(text: str = "The boy is at school. He reads a book."):
    source = {
        "page_unit_id": "RAZ_A_100_P003",
        "book_id": "100",
        "level": "A",
        "title": "School Day",
        "page_number": 3,
        "sentence_candidate_ids": ["RAZ_A_100_CAND_000001", "RAZ_A_100_CAND_000002"],
        "sentence_count": 2,
        "text": text,
        "source_tags": {"source": "RAZ", "source_type": "raz_audio_timeline"},
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "review_status": "pending",
        "content_unit_tags": {
            "content_unit_type": "page_unit",
            "sentence_count": 2,
            "has_multi_sentence_unit": True,
        },
        "theme_tags": {"mapped_theme": "School", "theme_confidence": 0.92},
        "pedagogical_tags": {
            "question_type_candidates": [
                "fill_blank",
                "reading_comprehension",
                "word_ordering",
                "sentence_ordering",
            ]
        },
        "qa_tags": {
            "needs_human_review": False,
            "warnings": [],
        },
    }
    selected = {
        "selection_id": "E4S_A1V1_READING_SOURCE_TEST_001",
        "source_unit_ref": source["page_unit_id"],
        "drive_file_id": "fixture-drive-id",
        "source_level": "A",
        "book_id": "100",
        "page_number": 3,
        "sentence_count": 2,
        "word_count": 9,
        "character_count": len(text),
        "e4s_situation_domain": "school",
        "source_theme": "School",
        "theme_confidence": 0.92,
        "candidate_question_types": [
            "cloze_vocabulary",
            "literal_what",
            "literal_where",
            "literal_who",
            "sentence_ordering",
            "true_false",
        ],
        "content_sha256": _sha(text),
        "record_sha256": _sha(_canonical_json(source)),
    }
    return selected, source


def _build(text: str = "The boy is at school. He reads a book."):
    selected, source = _fixture(text)
    return materialize_local_reading_bank(
        [selected],
        {"A": {source["page_unit_id"]: source}},
        {"A": "derived/Level_A/enriched/raz_A_page_unit_enriched.json"},
        require_full_selection=False,
    )


def test_local_materialization_keeps_text_private_and_safe_report_text_free():
    private_output, safe_report = _build()
    assert safe_report["validation_status"] == "PASS_LOCAL_READING_BINDING_EXECUTED"
    assert private_output["records"][0]["source_text"] == "The boy is at school. He reads a book."
    serialized_safe = json.dumps(safe_report, ensure_ascii=False)
    assert "The boy is at school." not in serialized_safe
    assert "He reads a book." not in serialized_safe
    assert safe_report["claim_boundaries"]["metadata_and_hashes_only"] is True
    assert safe_report["claim_boundaries"]["reading_v1_complete"] is False


def test_deterministic_items_and_literal_review_boundaries_are_materialized():
    private_output, safe_report = _build()
    record = private_output["records"][0]
    by_type = {item["question_type"]: item for item in record["deterministic_items"]}
    assert set(by_type) == {"true_false", "cloze_vocabulary", "sentence_ordering"}
    assert by_type["true_false"]["answer_model"]["answer_key"] is True
    assert by_type["cloze_vocabulary"]["answer_model"]["answer_key"] == "boy"
    assert by_type["sentence_ordering"]["answer_model"]["answer_key"] == ["S1", "S2"]
    literal_types = {candidate["question_type"] for candidate in record["literal_review_candidates"]}
    assert literal_types == {"literal_who", "literal_what", "literal_where"}
    assert all(candidate["auto_answer_generated"] is False for candidate in record["literal_review_candidates"])
    assert safe_report["m04b3_operator_review_complete"] is False


def test_private_and_safe_outputs_pass_cross_validator_in_reduced_fixture_mode():
    private_output, safe_report = _build()
    report = validate_materialization(
        private_output,
        safe_report,
        require_full_selection=False,
    )
    assert report["validation_status"] == "PASS_LOCAL_READING_PRACTICE_BANK"
    assert report["error_count"] == 0
    assert report["m04b2_complete"] is True
    assert report["reading_v1_complete"] is False


def test_content_hash_mismatch_fails_closed():
    selected, source = _fixture()
    selected["content_sha256"] = "0" * 64
    private_output, safe_report = materialize_local_reading_bank(
        [selected],
        {"A": {source["page_unit_id"]: source}},
        {"A": "fixture.json"},
        require_full_selection=False,
    )
    assert safe_report["validation_status"] == "FAIL"
    assert "one_or_more_selected_sources_failed_integrity" in safe_report["errors"]
    assert private_output["records"][0]["deterministic_items"] == []


def test_record_hash_mismatch_fails_closed():
    selected, source = _fixture()
    source["title"] = "Changed after selection"
    private_output, safe_report = materialize_local_reading_bank(
        [selected],
        {"A": {source["page_unit_id"]: source}},
        {"A": "fixture.json"},
        require_full_selection=False,
    )
    assert safe_report["validation_status"] == "FAIL"
    assert private_output["records"][0]["source_integrity"]["status"] == "FAIL"
    assert any("record_sha256" in error for error in private_output["records"][0]["source_integrity"]["errors"])


def test_missing_selected_source_fails_closed_without_private_text_record():
    selected, source = _fixture()
    private_output, safe_report = materialize_local_reading_bank(
        [selected],
        {"A": {}},
        {"A": "fixture.json"},
        require_full_selection=False,
    )
    assert safe_report["validation_status"] == "FAIL"
    assert private_output["records"] == []
    assert safe_report["records"][0]["source_integrity_errors"] == ["selected_source_record_missing"]


def test_one_sentence_source_does_not_create_ordering_item():
    text = "The cat sleeps."
    selected, source = _fixture(text)
    source["sentence_count"] = 1
    source["sentence_candidate_ids"] = ["RAZ_A_100_CAND_000001"]
    source["content_unit_tags"]["sentence_count"] = 1
    source["content_unit_tags"]["has_multi_sentence_unit"] = False
    selected["sentence_count"] = 1
    selected["word_count"] = 3
    selected["character_count"] = len(text)
    selected["content_sha256"] = _sha(text)
    selected["record_sha256"] = _sha(_canonical_json(source))
    private_output, safe_report = materialize_local_reading_bank(
        [selected],
        {"A": {source["page_unit_id"]: source}},
        {"A": "fixture.json"},
        require_full_selection=False,
    )
    types = {item["question_type"] for item in private_output["records"][0]["deterministic_items"]}
    assert types == {"true_false", "cloze_vocabulary"}
    assert "sentence_ordering" not in safe_report["summary"]["deterministic_item_counts"]


def test_forbidden_text_key_in_safe_report_is_rejected():
    private_output, safe_report = _build()
    mutated = copy.deepcopy(safe_report)
    mutated["records"][0]["clean_text"] = "Unsafe text"
    report = validate_materialization(
        private_output,
        mutated,
        require_full_selection=False,
    )
    assert report["validation_status"] == "FAIL"
    assert any("safe_report_forbidden_text_key" in error for error in report["errors"])


def test_false_promotion_or_completion_claim_is_rejected():
    private_output, safe_report = _build()
    mutated_private = copy.deepcopy(private_output)
    mutated_private["policy"]["promotion_status"] = "promoted"
    mutated_safe = copy.deepcopy(safe_report)
    mutated_safe["claim_boundaries"]["reading_v1_complete"] = True
    report = validate_materialization(
        mutated_private,
        mutated_safe,
        require_full_selection=False,
    )
    assert report["validation_status"] == "FAIL"
    assert "private_promotion_status_invalid" in report["errors"]
    assert "safe_false_claim_invalid:reading_v1_complete" in report["errors"]
