from __future__ import annotations

from product.a1fs_v1_2_1 import (
    u04r360_ket99_four_skill_capability_coverage_projection as projection,
)


def test_u04_reader360_ket99_four_skill_coverage_projection() -> None:
    result = projection.build_coverage_projection()

    assert result["status"] == projection.STATUS
    assert result["unit_number"] == 4
    assert result["unit_id"] == "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
    assert result["scope"] == {
        "coverage_projection_only": True,
        "classification_set": ["COVERED", "MISSING", "LATER_UNIT"],
        "new_reader_created": False,
        "reader360_content_modified": False,
        "questionbank_modified": False,
        "forms_modified": False,
        "runtime_modified": False,
        "audio_materialized": False,
        "unit05_plus_opened": False,
        "a2_a2plus_unlocked": False,
    }

    source = result["source_readback"]
    assert source["reader360"]["current360_episode_count"] == 360
    assert source["reader360"]["spoken360_entry_count"] == 360
    assert source["reader360"]["pattern360_entry_count"] == 360
    assert source["reader360"]["spoken_relation_alignment_count"] == 360
    assert source["reader360"]["pattern_family_semantic_count"] == 2520

    assert source["ket99"]["interaction_stage_count"] == 144
    assert source["ket99"]["semantic_compatible_stage_count"] == 144
    assert source["ket99"]["semantic_incompatible_stage_count"] == 0
    assert source["ket99"]["private_transcript_body_read"] is False
    assert source["ket99"]["source_text_copied"] is False

    assert source["formal_ket_four_skill"]["task_projection_count"] == 144
    assert source["formal_ket_four_skill"]["skill_distribution"] == {
        "READING": 36,
        "LISTENING": 36,
        "SPEAKING": 36,
        "WRITING": 36,
    }
    assert "NO_AUDIO_BODY" in source["formal_ket_four_skill"]["listening_resource_mode"]

    summary = result["coverage_summary"]
    assert summary["capability_row_count"] == 13
    assert summary["unit04_expected_now_count"] == 8
    assert summary["covered_count"] == 8
    assert summary["missing_count"] == 0
    assert summary["later_unit_count"] == 5
    assert summary["true_unit04_missing_count"] == 0
    assert summary["source_family_distribution"] == {
        "FORMAL_KET_FOUR_SKILL": 8,
        "KET99_SRT_SEMANTIC_DELIVERY": 5,
    }
    assert summary["unit04_reader360_sufficient_for_current_constraint_layer"] is True

    rows = {row["capability_id"]: row for row in result["coverage_rows"]}
    assert len(rows) == 13

    assert rows["KET4_READING_DETAIL_LOCATION_EXTRACTION"]["disposition"] == "COVERED"
    assert rows["KET4_READING_DETAIL_LOCATION_EXTRACTION"]["direct_reader_carriers"] == [
        "CURRENT360"
    ]

    assert rows["KET4_LISTENING_DIALOGUE_LANGUAGE_PRECURSOR"]["disposition"] == "COVERED"
    assert rows["KET4_LISTENING_DIALOGUE_LANGUAGE_PRECURSOR"]["direct_reader_carriers"] == [
        "SPOKEN360"
    ]
    assert rows["KET4_LISTENING_AUDIO_LOCATION_EXTRACTION"]["disposition"] == "LATER_UNIT"

    assert rows["KET4_SPEAKING_LOCATION_QA"]["disposition"] == "COVERED"
    assert rows["KET4_SPEAKING_LOCATION_QA"]["direct_reader_carriers"] == [
        "PATTERN360",
        "SPOKEN360",
    ]
    assert rows["KET4_SPEAKING_ALTERNATE_SCENE_TRANSFER"]["disposition"] == "LATER_UNIT"

    assert rows["KET4_WRITING_CONTROLLED_LOCATION_DESCRIPTION"]["disposition"] == "COVERED"
    assert rows["KET4_WRITING_CONTROLLED_LOCATION_DESCRIPTION"]["direct_reader_carriers"] == [
        "PATTERN360"
    ]
    assert rows["KET4_WRITING_INDEPENDENT_SHORT_RESPONSE"]["disposition"] == "LATER_UNIT"

    assert rows["KET99_GUIDED_DIALOGUE_LOCATION_QA"]["disposition"] == "COVERED"
    assert rows["KET99_FOLLOW_UP_SCENE_DESCRIPTION_DETAIL_EXPANSION"]["disposition"] == "COVERED"
    assert rows["KET99_RELATION_CONTRAST_DISCRIMINATION"]["disposition"] == "COVERED"
    assert rows["KET99_ERROR_CORRECTION_RETRY_LOOP"]["disposition"] == "LATER_UNIT"
    assert rows["KET99_ALTERNATE_SCENE_TRANSFER_PROMPT"]["disposition"] == "LATER_UNIT"

    assert all(row["disposition"] != "MISSING" for row in result["coverage_rows"])
    assert result["next_short_step"] == "U04_READER360_COVERAGE_CLOSEOUT_NO_NEW_READER"

    boundaries = result["claim_boundaries"]
    assert boundaries["full_ket_four_skill_completion_claimed"] is False
    assert boundaries["listening_audio_completion_claimed"] is False
    assert boundaries["independent_writing_completion_claimed"] is False
    assert boundaries["exam_simulation_completion_claimed"] is False
