from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.validators.validate_a1_a1plus_selected_reading_source_manifest import (
    EXPECTED_FIELDS,
    load_from_repo,
    validate_selected_manifest,
)


def _fresh():
    index, shards = load_from_repo()
    return copy.deepcopy(index), copy.deepcopy(shards)


def _record(shards, level: str, index: int = 0):
    return dict(zip(EXPECTED_FIELDS, shards[level]["records"][index]))


def test_selected_manifest_passes_and_recomputes_expected_coverage():
    index, shards = _fresh()
    report = validate_selected_manifest(index, shards)
    assert report["validation_status"] == "PASS_SELECTED_READING_SOURCE_MANIFEST"
    assert report["error_count"] == 0
    assert report["summary"]["selected_record_count"] == 54
    assert report["summary"]["unique_book_count"] == 54
    assert report["summary"]["levels"] == {level: 9 for level in "ABCDEF"}
    assert set(report["summary"]["situation_domains"].values()) == {6}
    assert report["summary"]["candidate_question_types"]["cloze_vocabulary"] == 54
    assert report["summary"]["candidate_question_types"]["literal_what"] == 54
    assert report["summary"]["candidate_question_types"]["true_false"] == 54
    assert report["summary"]["candidate_question_types"]["sentence_ordering"] == 36
    assert report["m04b1_selection_complete"] is True
    assert report["m04b2_local_content_binding_complete"] is False
    assert report["reading_v1_complete"] is False


def test_every_level_has_all_nine_domains_and_no_embedded_content():
    index, shards = _fresh()
    for level in "ABCDEF":
        assert len(shards[level]["records"]) == 9
        domains = {_record(shards, level, idx)["e4s_situation_domain"] for idx in range(9)}
        assert len(domains) == 9
        policy = shards[level]["record_policy"]
        assert policy["metadata_and_hashes_only"] is True
        assert policy["content_access"] == "LOCAL_SOURCE_REQUIRED_NOT_EMBEDDED"
        assert policy["raw_source_text_included"] is False
        assert policy["full_passage_text_included"] is False
        assert policy["sentence_text_included"] is False
        assert policy["source_payload_copied"] is False


def test_summary_drift_fails_closed():
    index, shards = _fresh()
    index["summary"]["selected_record_count"] = 53
    report = validate_selected_manifest(index, shards)
    assert report["validation_status"] == "FAIL"
    assert "index_summary_drift" in report["errors"]


def test_unsafe_source_policy_fails_closed():
    index, shards = _fresh()
    shards["A"]["record_policy"]["raw_source_text_included"] = True
    report = validate_selected_manifest(index, shards)
    assert report["validation_status"] == "FAIL"
    assert "A:unsafe_policy:raw_source_text_included" in report["errors"]


def test_duplicate_selection_id_fails_closed():
    index, shards = _fresh()
    selection_index = EXPECTED_FIELDS.index("selection_id")
    shards["B"]["records"][1][selection_index] = shards["B"]["records"][0][selection_index]
    report = validate_selected_manifest(index, shards)
    assert report["validation_status"] == "FAIL"
    assert "duplicate_selection_id" in report["errors"]


def test_sentence_ordering_requires_multi_sentence_source():
    index, shards = _fresh()
    types_index = EXPECTED_FIELDS.index("candidate_question_types")
    sentence_count_index = EXPECTED_FIELDS.index("sentence_count")
    shards["A"]["records"][0][types_index].append("sentence_ordering")
    assert shards["A"]["records"][0][sentence_count_index] == 1
    report = validate_selected_manifest(index, shards)
    assert report["validation_status"] == "FAIL"
    assert any("sentence_ordering_without_multi_sentence_source" in error for error in report["errors"])


def test_forbidden_text_key_fails_closed():
    index, shards = _fresh()
    shards["C"]["clean_text"] = "This must never be persisted."
    report = validate_selected_manifest(index, shards)
    assert report["validation_status"] == "FAIL"
    assert any("forbidden_text_key" in error for error in report["errors"])
