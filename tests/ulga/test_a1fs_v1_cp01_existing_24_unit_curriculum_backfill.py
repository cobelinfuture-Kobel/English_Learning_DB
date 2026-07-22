from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_cp01_existing_24_unit_curriculum_backfill as builder
from ulga.validators import validate_a1fs_v1_cp01_existing_24_unit_curriculum_backfill as validator


@pytest.fixture(scope="module")
def artifact():
    return builder.build_artifact()


def test_cp01_backfills_only_existing_admitted_items(artifact):
    summary = artifact["coverage_summary"]
    assert summary["learning_unit_count"] == 24
    assert summary["canonical_egp_row_count"] == 109
    assert summary["candidate_item_count"] == 384
    assert summary["unit_assigned_candidate_item_count"] == 384
    assert summary["admitted_private_item_count"] == 184
    assert summary["candidate_only_item_count"] == 200
    assert summary["admitted_private_item_counts_by_skill"] == {
        "reading": 92,
        "writing": 92,
        "listening": 0,
        "speaking": 0,
    }


def test_cp01_preserves_real_unit_and_lane_gaps(artifact):
    summary = artifact["coverage_summary"]
    assert summary["admitted_private_unit_count"] == 23
    assert summary["deferred_unit_count"] == 1
    assert summary["admitted_skill_lane_count"] == 46
    assert summary["admission_gap_skill_lane_count"] == 50
    assert summary["four_skill_admitted_unit_count"] == 0
    assert summary["pending_content_authority_binding_count"] == 96
    assert summary["missing_spiral_role_binding_count"] == 96
    assert summary["missing_followup_content_pool_binding_count"] == 72


def test_cp01_does_not_invent_authority_or_followup_bindings(artifact):
    for unit in artifact["learning_units"]:
        assert unit["authority_bindings"]["grammar"]["selected_refs"] == [
            unit["grammar_unit_id"]
        ]
        for authority in builder.PENDING_AUTHORITIES:
            binding = unit["authority_bindings"][authority]
            assert binding["selection_status"] == "PENDING_CONTENT_BINDING"
            assert binding["selected_refs"] == []
        assert all(
            value == "MISSING_EXPLICIT_CONTENT_POOL_BINDING"
            for value in unit["followup_content_pools"].values()
        )
        assert unit["four_skill_admitted_population_complete"] is False


def test_cp01_keeps_deferred_will_unit_candidate_only(artifact):
    unit = next(
        row
        for row in artifact["learning_units"]
        if row["grammar_unit_id"] == builder.DEFERRED_GRAMMAR_ID
    )
    assert unit["unit_population_status"] == "CANDIDATE_ONLY_DEFERRED"
    assert unit["deferred_reason"] == "DEFERRED_CAMBRIDGE_CEILING"
    assert all(lane["admitted_item_count"] == 0 for lane in unit["skill_lanes"].values())


def test_cp01_validator_passes(artifact):
    report = validator.validate_artifact(artifact)
    assert report["validation_status"] == builder.PASS_STATUS
    assert report["errors"] == []
    assert report["candidate_item_count"] == 384
    assert report["admitted_private_item_count"] == 184
    assert report["four_skill_admitted_unit_count"] == 0
    assert report["next_short_step"] == builder.NEXT_SHORT_STEP


def test_cp01_validator_fails_on_false_admission(artifact):
    tampered = deepcopy(artifact)
    lane = tampered["learning_units"][0]["skill_lanes"]["listening"]
    lane["admitted_item_ids"] = [lane["candidate_item_ids"][0]]
    lane["admitted_item_count"] = 1
    lane["admission_state"] = "ADMITTED_PRIVATE"
    report = validator.validate_artifact(tampered)
    assert report["validation_status"] == "FAIL"
    assert "admitted_item_partition_drift" in report["errors"]


def test_cp01_is_metadata_only_policy_exempt_builder():
    assert builder.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert builder.A1FS_CONTENT_POLICY_EXEMPTION
