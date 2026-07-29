from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from ulga.builders import (
    build_a1fs_v1_razq01a_unit01_unit02_filter_calibration as pilot,
)


def _runtime(root: Path) -> None:
    runtime = root / "product" / "a1fs_v1_2_1" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "sequence.json").write_text(
        json.dumps(
            {
                "GRAMMAR_ARTICLES_BASIC": 1,
                "GRAMMAR_REGULAR_PLURAL_NOUNS": 2,
                "OTHER": 3,
            }
        ),
        encoding="utf-8",
    )
    bundles = {
        "A1FS_ONLINE_V1:GRAMMAR_ARTICLES_BASIC:READING": {
            "lesson": {"lesson_id": "U1:R", "skill": "READING", "level": "A1"},
            "assets": [
                {
                    "learner_payload": {
                        "question_type": "multiple_choice",
                        "context_id": "U01-C1",
                        "context": {
                            "communicative_goal": "introduce one item",
                            "grammar_clue": "Use a or an.",
                        },
                        "target_refs": {
                            "target_evp_sense_ids": [
                                "vocabulary:apple:v_1",
                                "vocabulary:cat:v_2",
                            ],
                            "target_egp_row_ids": ["egp-article"],
                            "target_chunk_ids": ["chunk:ice_cream"],
                            "target_pattern_ids": ["SP_ARTICLE"],
                        },
                    }
                }
            ],
        },
        "A1FS_ONLINE_V1:GRAMMAR_REGULAR_PLURAL_NOUNS:READING": {
            "lesson": {"lesson_id": "U2:R", "skill": "READING", "level": "A1"},
            "assets": [
                {
                    "learner_payload": {
                        "question_type": "gap_fill",
                        "context_id": "U02-C1",
                        "context": {
                            "communicative_goal": "refer to more than one item",
                            "grammar_clue": "Use regular -s or -es.",
                        },
                        "target_refs": {
                            "target_evp_sense_ids": [
                                "vocabulary:box:v_1",
                                "vocabulary:dog:v_2",
                            ],
                            "target_egp_row_ids": ["egp-plural"],
                            "target_chunk_ids": [],
                            "target_pattern_ids": ["SP_PLURAL"],
                        },
                    }
                }
            ],
        },
    }
    (runtime / "bundles.json").write_text(json.dumps(bundles), encoding="utf-8")


def _index(path: Path) -> None:
    records = [
        {
            "reading_intake_id": "r1",
            "source_level": "A",
            "source_type": "enriched_reading_unit",
            "source_path": "Level_A/enriched.json",
            "text": "A cat has an apple. The cat is near the door.",
            "reusability_tags": ["short_reading_seed", "grammar_pattern_seed"],
        },
        {
            "reading_intake_id": "r1",
            "source_level": "A",
            "source_type": "normalized_reading_unit",
            "source_path": "Level_A/normalized.json",
            "text": "A cat has an apple. The cat is near the door.",
            "reusability_tags": ["sentence_only"],
        },
        {
            "reading_intake_id": "r2",
            "source_level": "B",
            "source_type": "page_unit",
            "source_path": "Level_B/page.json",
            "text": "Two dogs are by three boxes.",
            "reusability_tags": [
                "short_reading_seed",
                "listening_audio_seed",
            ],
        },
        {
            "reading_intake_id": "r3",
            "source_level": "J",
            "source_type": "reuse_unit_candidate",
            "source_path": "Level_J/reuse.json",
            "text": "Many birds are living near the lakes.",
            "reusability_tags": ["dialogue_rewrite_seed"],
        },
        {
            "reading_intake_id": "r4",
            "source_level": "A",
            "source_type": "page_unit",
            "source_path": "Level_A/page.json",
            "text": "The apple is red.",
            "reusability_tags": ["picture_prompt_seed"],
        },
        {
            "source_level": "A",
            "source_type": "page_unit",
            "source_path": "Level_A/page.json",
            "text": "A cat is here.",
            "reusability_tags": ["sentence_only"],
        },
    ]
    path.write_text(json.dumps(records), encoding="utf-8")


def test_profiles_are_derived_from_existing_first_two_units(tmp_path: Path) -> None:
    _runtime(tmp_path)
    profiles = pilot.build_unit_profiles(tmp_path)
    assert [profile.unit_id for profile in profiles] == [
        "GRAMMAR_ARTICLES_BASIC",
        "GRAMMAR_REGULAR_PLURAL_NOUNS",
    ]
    assert "apple" in profiles[0].lexical_cues
    assert "box" in profiles[1].lexical_cues
    assert profiles[0].target_egp_row_ids == ("egp-article",)


def test_filter_classification_and_outputs(tmp_path: Path) -> None:
    _runtime(tmp_path)
    index = tmp_path / "index.json"
    output = tmp_path / "out"
    _index(index)
    report = pilot.run_calibration(
        repo_root=tmp_path,
        index_path=index,
        output_dir=output,
        sample_limit=20,
        progress_every=0,
    )
    assert report["status"] == pilot.PASS_STATUS
    assert report["records_scanned"] == 6
    units = {row["unit_profile"]["unit_id"]: row for row in report["units"]}
    article = units["GRAMMAR_ARTICLES_BASIC"]
    plural = units["GRAMMAR_REGULAR_PLURAL_NOUNS"]
    assert article["filter_funnel"]["pass_count"] >= 1
    assert article["filter_funnel"]["semantic_duplicate_count"] >= 1
    assert plural["filter_funnel"]["pass_count"] >= 1
    assert plural["filter_funnel"]["borderline_count"] >= 1
    assert plural["skill_capacity"]["LISTENING_SCRIPT_CANDIDATE"] >= 1
    assert (
        output / "a1fs_v1_razq01a_unit01_unit02_filter_calibration.json"
    ).is_file()
    assert (
        output / "a1fs_v1_razq01a_unit01_unit02_filter_validation.json"
    ).is_file()
    matrix = output / "a1fs_v1_razq01a_unit01_unit02_distinct_capacity_matrix.csv"
    with matrix.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2


def test_streaming_parser_fails_closed_on_non_array(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"items": []}', encoding="utf-8")
    with pytest.raises(pilot.CalibrationError, match="TOP_LEVEL_MUST_BE_ARRAY"):
        list(pilot.iter_query_index(path))


def test_main_canary_exit_code(tmp_path: Path) -> None:
    _runtime(tmp_path)
    index = tmp_path / "index.json"
    _index(index)
    code = pilot.main(
        [
            "--repo-root",
            str(tmp_path),
            "--index-path",
            str(index),
            "--output-dir",
            str(tmp_path / "out"),
            "--max-records",
            "3",
            "--progress-every",
            "0",
        ]
    )
    assert code == 0
