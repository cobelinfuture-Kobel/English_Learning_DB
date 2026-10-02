from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q00_unit05_successor_baseline.json"


def test_u06_q00_unit05_successor_baseline() -> None:
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert data["status"] == "PASS_A1FS_V1_U06Q00_UNIT05_SUCCESSOR_BASELINE"
    assert data["unit_number"] == 6
    assert data["predecessor_unit_number"] == 5
    assert data["predecessor_unit_id"] == "GRAMMAR_BE_VERB_BASIC"
    assert data["source_main_sha"] == "cc992771ddbd89c865d72ae0c2976951bb670ee1"

    scope = data["scope"]
    assert scope["unit05_final_main_read_complete"] is True
    assert scope["unit05_reader360_read_complete"] is True
    assert scope["unit05_full1632_read_complete"] is True
    assert scope["unit01_to_unit05_cumulative_language_assets_read_complete"] is True
    assert scope["unit05_functional_chunk_carry_forward_locked"] is True
    assert scope["unit06_canonical_target_selected"] is False
    assert scope["unit06_new_learner_content_materialized"] is False
    assert scope["unit06_new_vocabulary_materialized"] is False
    assert scope["unit06_new_chunks_materialized"] is False
    assert scope["unit06_new_sentence_assets_materialized"] is False
    assert scope["unit06_reader360_materialized"] is False
    assert scope["unit06_practice_materialized"] is False
    assert scope["a2_a2plus_unlocked"] is False
    assert scope["no_new_design_docs"] is True

    capabilities = data["predecessor_capabilities"]
    assert capabilities["cumulative_unit01_to_unit05"] == [
        "GRAMMAR_ARTICLES_BASIC",
        "GRAMMAR_REGULAR_PLURAL_NOUNS",
        "GRAMMAR_SUBJECT_PRONOUNS",
        "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "GRAMMAR_BE_VERB_BASIC",
    ]
    assert capabilities["unit05_media_release_complete"] is False
    assert capabilities["unit05_deferred_media_activity_count"] == 816
    assert capabilities["unit05_executable_text_activity_count"] == 816

    denominator = data["exact_predecessor_denominator"]
    assert denominator["sentence_assets"]["unit01_to_unit04_cumulative"] == 26610
    assert denominator["sentence_assets"]["unit05_new_admitted"] == 761
    assert denominator["sentence_assets"]["unit05_validated_predecessor_reuse_bindings"] == 94
    assert denominator["sentence_assets"]["unit01_to_unit05_cumulative_unique"] == 27371
    assert denominator["chunks"]["unit04_cumulative_chunk_surfaces"] == 90
    assert denominator["chunks"]["unit05_q04_new_chunk_surfaces"] == 66
    assert denominator["chunks"]["unit01_to_unit05_cumulative_chunk_surfaces"] == 156
    assert denominator["exact_sentence_frames"]["unit01_to_unit05_cumulative_exact_frames"] == 29
    assert denominator["course_pattern_families"]["unit01_to_unit05_cumulative_course_pattern_families"] == 8
    assert denominator["vocabulary"]["unit05_new_global_vocabulary_identity_count"] == 0
    assert denominator["vocabulary"]["cumulative_unit01_to_unit05_unique_vocabulary_identity_count"] is None

    readers = data["reader360_denominator"]
    assert readers["current360"]["entry_count"] == 360
    assert readers["spoken360"]["entry_count"] == 360
    assert readers["spoken360"]["dialogue_turn_count"] == 2160
    assert readers["pattern360"]["entry_count"] == 360
    assert readers["pattern360"]["family_group_count"] == 2520
    assert readers["pattern360"]["example_count"] == 4675

    far = data["full1632_denominator"]
    assert far["full_identity_count"] == 1632
    assert far["core480"] == 480
    assert far["ket672"] == 672
    assert far["delayed_dictation480"] == 480
    assert far["executable_text_activity_count"] == 816
    assert far["external_asset_pending_activity_count"] == 816
    assert far["media_pending_breakdown"] == {
        "ket_media_pending": 336,
        "dictation_audio_pending": 480,
    }

    carry = data["unit05_functional_chunk_carry_forward"]
    assert carry["origin_unit"] == "U05"
    assert carry["source_q04_new_chunk_surface_count"] == 66
    assert carry["source_scene_functional_candidate_count"] == 874
    assert carry["source_scene_functional_occurrence_count"] == 2246
    assert carry["q05_individual_candidate_promoted_count"] == 0
    assert carry["q05_actual_usage_record_count"] == 0
    assert carry["q06_scene_functional_candidate_promoted_count"] == 0
    assert carry["q06_functional_candidate_usage_ledger_entry_count"] == 0
    assert carry["u05_downstream_consumption_result"] == "ZERO_Q05_Q06_DOWNSTREAM_CONSUMPTION_PROVEN"
    assert "U06_NATIVE_FUNCTIONAL_CHUNKS" in carry["unit06_q04_requirement"]
    assert carry["unit06_q05_q06_requirement"] == "TRACK_EXPLICIT_CONSUMPTION_FOR_BOTH_U05_INHERITED_AND_U06_NATIVE_CHUNKS"
    assert set(carry["allowed_dispositions"]) == {
        "CONSUMED_IN_U06",
        "DEFERRED_TO_LATER_UNIT",
        "NOT_ELIGIBLE",
        "PENDING_REVIEW",
    }

    gap = data["unit06_gap_preparation"]
    assert gap["unit06_real_gap_computable"] is False
    assert gap["current_sequence_candidate_hint"] == "GRAMMAR_CAN_STATEMENT"
    assert gap["current_sequence_candidate_row_count_hint"] == 12
    assert gap["q00_does_not_admit_unit06_target"] is True
    assert gap["next_short_step"] == "A1FS-V1-U06Q01_Unit06CanonicalTargetAndGapProjection"

    acceptance = data["acceptance"]
    assert acceptance["cumulative_sentence_asset_count"] == 27371
    assert acceptance["cumulative_chunk_surface_count"] == 156
    assert acceptance["cumulative_exact_sentence_frame_count"] == 29
    assert acceptance["cumulative_course_pattern_family_count"] == 8
    assert acceptance["reader360_json_sets"] == "360/360/360"
    assert acceptance["full1632_identity_count"] == 1632
    assert acceptance["unit05_functional_chunk_carry_forward_count"] == 66
    assert acceptance["unit05_functional_chunk_q05_q06_explicit_consumption_count"] == 0
    assert acceptance["unit06_new_learner_content_count"] == 0
    assert acceptance["unit06_target_not_admitted_in_q00"] is True
    assert acceptance["a2_a2plus_unlocked"] is False

    assert data["next_short_step"] == "A1FS-V1-U06Q01_Unit06CanonicalTargetAndGapProjection"
