import pytest

from ulga.builders import build_e4s_a1v1_current_state_recheck as builder


@pytest.fixture(scope="module")
def report():
    return builder.build_report()


def test_m00_recomputes_current_a1_a1plus_baseline(report):
    assert report["validation_status"] == builder.PASS_STATUS
    assert report["scope"] == "A1_A1_PLUS_ONLY"
    assert report["current_position"] == "M00_COMPLETE_M01_NEXT"

    coverage = report["coverage_summary"]
    assert coverage["canonical_row_count"] == 109
    assert coverage["covered_row_count"] == 109
    assert coverage["draft_only_row_count"] == 0
    assert coverage["missing_row_count"] == 0
    assert coverage["unexpected_row_count"] == 0
    assert coverage["coverage_percent"] == 100.0
    assert coverage["canonical_unit_count"] == 24
    assert coverage["candidate_four_skill_closed_row_count"] == 109
    assert coverage["operator_approved_text_mode_unit_count"] == 24
    assert coverage["text_mode_pilot_eligible_row_count"] == 109
    assert coverage["text_mode_item_count"] == 192
    assert coverage["text_mode_reading_item_count"] == 96
    assert coverage["text_mode_writing_item_count"] == 96
    assert coverage["synthetic_pass_unit_count"] == 24
    assert coverage["synthetic_gap_unit_count"] == 0
    assert coverage["historical_human_pilot_sampled_unit_count"] == 3
    assert coverage["rendered_listening_audio_asset_count"] == 0
    assert coverage["captured_speaking_audio_asset_count"] == 0


def test_m00_classifies_all_epic_milestones_without_false_closeout(report):
    milestones = {row["milestone"]: row for row in report["milestones"]}
    assert list(milestones) == [f"M{index:02d}" for index in range(19)]
    assert milestones["M00"]["status"] == "COMPLETE"
    assert milestones["M01"]["status"] == "PARTIAL"
    assert milestones["M05"]["status"] == "PARTIAL"
    assert milestones["M06"]["status"] == "PARTIAL"
    assert milestones["M08"]["status"] == "NOT_STARTED"
    assert milestones["M18"]["status"] == "NOT_STARTED"
    assert report["milestone_status_counts"] == {
        "COMPLETE": 1,
        "PARTIAL": 14,
        "NOT_STARTED": 4,
    }

    boundaries = report["claim_boundaries"]
    assert boundaries["m00_baseline_complete"] is True
    assert boundaries["candidate_four_skill_paths_are_real_skill_evidence"] is False
    assert boundaries["synthetic_pipeline_is_learner_mastery"] is False
    assert boundaries["full_four_skill_release_complete"] is False
    assert boundaries["retention_confirmed"] is False
    assert boundaries["a1_a1plus_v1_closeout_complete"] is False
    assert boundaries["a2_a2plus_in_scope"] is False
    assert boundaries["persistent_learner_state_write"] is False
    assert boundaries["production_runtime_event"] is False


def test_m00_advances_directly_to_m01(report):
    assert report["stop_reason"] == "NONE"
    assert report["next_short_step"] == (
        "E4S-A1V1-M01_AuthorityScopeAndQueryCompleteness"
    )
    assert all(report["identity_checks"].values())
    assert report["private_evidence_boundary"] == {
        "repo_recheck_does_not_read_private_local_learner_state": True,
        "historical_public_sample_marker_count": 3,
        "new_human_evidence_requested": False,
    }


def test_m00_source_validation_fails_closed():
    with pytest.raises(
        RuntimeError,
        match="m00_source_validation_failed:tampered:FAIL",
    ):
        builder._require_source_pass(
            "tampered",
            {"validation_status": "FAIL"},
        )
