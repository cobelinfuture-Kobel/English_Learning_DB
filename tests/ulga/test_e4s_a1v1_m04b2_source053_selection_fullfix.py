from __future__ import annotations

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


def test_source_053_uses_integrity_consistent_level_f_travel_candidate():
    index, shards = load_from_repo()
    report = validate_selected_manifest(index, shards)
    assert report["validation_status"] == "PASS_SELECTED_READING_SOURCE_MANIFEST"

    records = [dict(zip(EXPECTED_FIELDS, row)) for row in shards["F"]["records"]]
    source = next(row for row in records if row["selection_id"] == "E4S_A1V1_READING_SOURCE_053")

    assert source["source_unit_ref"] == "RAZ_F_663_P005"
    assert source["source_level"] == "F"
    assert source["book_id"] == "663"
    assert source["page_number"] == 5
    assert source["sentence_count"] == 4
    assert source["word_count"] == 18
    assert source["character_count"] == 87
    assert source["e4s_situation_domain"] == "travel_transport_weather"
    assert source["source_theme"] == "Travel"
    assert source["theme_confidence"] == 0.78
    assert "sentence_ordering" in source["candidate_question_types"]
    assert source["content_sha256"] == "ed7a2fc2b920611ac52c34f7b0ac0d89fd762a4ce17af55684467f6fe13a17c0"
    assert source["record_sha256"] == "ce459d7926d91466810092b6dca7c8bab209535095729953c03ee2b2e6e585c7"


def test_ambiguous_source_053_is_not_selected_anymore():
    _, shards = load_from_repo()
    all_source_refs = {
        dict(zip(EXPECTED_FIELDS, row))["source_unit_ref"]
        for shard in shards.values()
        for row in shard["records"]
    }
    assert "RAZ_F_97_P007" not in all_source_refs
