import importlib.util
import json
import subprocess
import sys
from pathlib import Path


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


def load_builder_module():
    spec = importlib.util.spec_from_file_location("raz_s11_builder", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_can_run_offline():
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert INDEX_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_index_json_exists_and_parses():
    payload = load_json(INDEX_PATH)
    assert isinstance(payload, dict)
    assert REQUIRED_TOP_LEVEL_KEYS <= set(payload)


def test_source_policy_preserves_candidate_only_no_promotion_boundary():
    payload = load_json(INDEX_PATH)
    assert payload["source_policy"]["offline_static_only"] is True
    assert payload["source_policy"]["generated_content"] is False
    assert payload["source_policy"]["authority_promotion"] is False
    assert payload["source_policy"]["candidate_only_preserved"] is True

    for item in payload["items"]:
        assert item["authority_status"] == "candidate_only"
        assert item["promotion_status"] == "not_promoted"
        assert item["generated_content"] is False


def test_required_query_indexes_exist_even_when_empty():
    payload = load_json(INDEX_PATH)
    assert REQUIRED_INDEX_KEYS <= set(payload["query_indexes"])
    for key in REQUIRED_INDEX_KEYS:
        assert isinstance(payload["query_indexes"][key], dict)


def test_query_indexes_reference_only_valid_intake_ids():
    payload = load_json(INDEX_PATH)
    valid_ids = {item["intake_id"] for item in payload["items"]}

    for index in payload["query_indexes"].values():
        for ids in index.values():
            assert isinstance(ids, list)
            for intake_id in ids:
                assert intake_id in valid_ids


def test_summary_counts_match_output_items():
    payload = load_json(INDEX_PATH)
    summary = load_json(SUMMARY_PATH)

    assert payload["summary"] == summary
    assert summary["total_items"] == len(payload["items"])
    assert summary["candidate_only_count"] == sum(
        1 for item in payload["items"] if item["authority_status"] == "candidate_only"
    )
    assert summary["promoted_count"] == 0
    assert summary["multi_sentence_item_count"] == sum(
        1 for item in payload["items"] if item["sentence_count"] > 1
    )


def test_sentence_count_bucket_logic_is_deterministic():
    builder = load_builder_module()
    assert builder.sentence_count_bucket(0) == "unknown"
    assert builder.sentence_count_bucket(1) == "single_sentence"
    assert builder.sentence_count_bucket(2) == "two_sentences"
    assert builder.sentence_count_bucket(3) == "three_to_five_sentences"
    assert builder.sentence_count_bucket(5) == "three_to_five_sentences"
    assert builder.sentence_count_bucket(6) == "six_plus_sentences"


def test_multi_sentence_bucket_matches_items():
    payload = load_json(INDEX_PATH)
    bucket_index = payload["query_indexes"]["by_sentence_count_bucket"]

    for item in payload["items"]:
        count = item["sentence_count"]
        if count == 1:
            expected_bucket = "single_sentence"
        elif count == 2:
            expected_bucket = "two_sentences"
        elif 3 <= count <= 5:
            expected_bucket = "three_to_five_sentences"
        elif count >= 6:
            expected_bucket = "six_plus_sentences"
        else:
            expected_bucket = "unknown"

        assert item["intake_id"] in bucket_index.get(expected_bucket, [])


def test_reusability_tags_are_indexed_when_present():
    payload = load_json(INDEX_PATH)
    reusability_index = payload["query_indexes"]["by_reusability_tag"]

    for item in payload["items"]:
        for tag in item["query_tags"]["reusability_tags"]:
            assert item["intake_id"] in reusability_index.get(tag, [])
