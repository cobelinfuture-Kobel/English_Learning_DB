import json
import subprocess
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.builders import build_raz_reading_authority_intake_query_index as builder

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_raz_reading_authority_intake_query_index.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_raz_reading_authority_intake_query_index_builder_output.py"
INDEX_PATH = BASE_DIR / "ulga" / "graph" / "raz_reading_authority_intake_query_index.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_query_index_summary.json"

REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "builder_task",
    "generated_at",
    "source_policy",
    "levels",
    "items",
    "query_indexes",
    "summary",
}
REQUIRED_INDEX_KEYS = {
    "by_level",
    "by_book_id",
    "by_level_and_book",
    "by_source_type",
    "by_reusability_tag",
    "by_authority_status",
    "by_promotion_status",
    "by_sentence_count_bucket",
    "by_multi_sentence_status",
    "by_theme_hint",
    "by_grammar_tag",
    "by_pattern_tag",
    "by_vocabulary_tag",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


@pytest.fixture(scope="session")
def payload():
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert INDEX_PATH.exists()
    assert SUMMARY_PATH.exists()
    return load_json(INDEX_PATH)


@pytest.fixture(scope="session")
def summary():
    return load_json(SUMMARY_PATH)


@pytest.fixture(scope="session")
def sample_items(payload):
    items = payload["items"]
    if len(items) <= 300:
        return items
    return items[:100] + items[len(items) // 2 : len(items) // 2 + 100] + items[-100:]


def test_builder_writes_expected_files(payload):
    assert isinstance(payload, dict)
    assert INDEX_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_passes(payload):
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_top_level_contract(payload):
    assert REQUIRED_TOP_LEVEL_KEYS <= set(payload)
    assert payload["schema_version"] == "RAZ_READING_AUTHORITY_INTAKE_QUERY_INDEX_V1"


def test_source_policy_and_summary_boundary(payload, summary):
    assert payload["source_policy"] == {
        "offline_static_only": True,
        "generated_content": False,
        "authority_promotion": False,
        "candidate_only_preserved": True,
    }
    assert payload["summary"] == summary
    assert summary["total_items"] == len(payload["items"])
    assert summary["candidate_only_count"] == summary["total_items"]
    assert summary["promoted_count"] == 0


def test_required_query_indexes_exist(payload):
    assert REQUIRED_INDEX_KEYS <= set(payload["query_indexes"])
    for key in REQUIRED_INDEX_KEYS:
        assert isinstance(payload["query_indexes"][key], dict)


def test_sampled_items_preserve_no_promotion_boundary(sample_items):
    for item in sample_items:
        assert item["authority_status"] == "candidate_only"
        assert item["promotion_status"] == "not_promoted"
        assert item["generated_content"] is False
        assert item["source_traceability"]["source_path"]


def test_sampled_ids_are_indexed(payload, sample_items):
    sample_ids = {item["intake_id"] for item in sample_items}
    seen_ids = set()
    for index in payload["query_indexes"].values():
        for values in index.values():
            seen_ids.update(value for value in values if value in sample_ids)
    assert sample_ids <= seen_ids


def test_sentence_count_buckets_for_samples(payload, sample_items):
    bucket_index = payload["query_indexes"]["by_sentence_count_bucket"]
    for item in sample_items:
        count = item["sentence_count"]
        if count == 1:
            bucket = "single_sentence"
        elif count == 2:
            bucket = "two_sentences"
        elif 3 <= count <= 5:
            bucket = "three_to_five_sentences"
        elif count >= 6:
            bucket = "six_plus_sentences"
        else:
            bucket = "unknown"
        assert item["intake_id"] in bucket_index.get(bucket, [])


def test_extract_level_preserves_s10a_source_and_normalized_level():
    record = {
        "reading_intake_id": "RID-1",
        "source_level": "g",
        "normalized_level": "G",
        "text": {"clean_text": "Billy chases the red kite."},
    }
    level = builder.extract_level(record, BASE_DIR / "ulga" / "graph" / "raz_reading_authority_intake_candidates.json")
    assert level == "G"


def test_make_item_propagates_s10a_reading_intake_id_to_source_traceability():
    record = {
        "reading_intake_id": "RAZ_A_1001_SENT_000001",
        "source_level": "A",
        "normalized_level": "A",
        "text": {"clean_text": "I see a cat.", "sentence_count": 1},
        "tags": {"reusability_tags": ["sentence_only", "short_reading_seed"]},
        "artifact_pointer": {"source_record_id": "SHOULD_NOT_WIN"},
    }
    item = builder.make_item(1, BASE_DIR / "ulga" / "graph" / "raz_reading_authority_intake_candidates.json", record)
    assert item["level"] == "A"
    assert item["source_traceability"]["source_record_id"] == "RAZ_A_1001_SENT_000001"
    assert item["authority_status"] == "candidate_only"
    assert item["promotion_status"] == "not_promoted"
    assert item["generated_content"] is False


def test_extract_reusability_tags_reads_nested_tags_only():
    record = {
        "tags": {
            "reusability_tags": ["sentence_only", "short_reading_seed"],
            "grammar_tags": ["simple_present"],
        }
    }
    assert builder.extract_reusability_tags(record) == ["sentence_only", "short_reading_seed"]


def test_dict_shaped_tags_object_is_not_stringified_into_reusability_tags():
    record = {
        "tags": {
            "theme_tags": ["animals"],
            "grammar_tags": ["simple_present"],
        }
    }
    tags = builder.extract_reusability_tags(record)
    assert tags == []
    assert not any("{" in tag or "}" in tag for tag in tags)


def test_structured_s10a_record_is_detected_without_descending_to_nested_text_only():
    record = {
        "reading_intake_id": "RAZ_A_1001_SENT_000001",
        "source_level": "A",
        "normalized_level": "A",
        "text": {"clean_text": "I see a cat.", "sentence_count": 1},
    }
    assert builder.is_structured_intake_record(record) is True
    assert builder.is_candidate_record(BASE_DIR / "ulga" / "graph" / "raz_reading_authority_intake_candidates.json", record) is True


def test_s10a_derived_items_preserve_level_and_source_record_id(payload):
    s10a_items = [
        item
        for item in payload["items"]
        if item["source_traceability"]["source_path"] == "ulga/graph/raz_reading_authority_intake_candidates.json"
    ]
    assert s10a_items
    assert all(item["level"] != "UNKNOWN" for item in s10a_items)
    assert all(item["source_traceability"]["source_record_id"] for item in s10a_items)


def test_reusability_tag_index_has_no_dict_stringified_keys(payload, summary):
    bad_index_keys = [
        key for key in payload["query_indexes"]["by_reusability_tag"] if "{" in key or "}" in key
    ]
    bad_summary_keys = [
        key for key in summary["by_reusability_tag"] if "{" in key or "}" in key
    ]
    assert bad_index_keys == []
    assert bad_summary_keys == []
