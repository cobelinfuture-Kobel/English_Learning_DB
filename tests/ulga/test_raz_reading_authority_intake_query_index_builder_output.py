import json
import subprocess
import sys
from pathlib import Path

import pytest


BASE_DIR = Path(__file__).resolve().parents[2]
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
