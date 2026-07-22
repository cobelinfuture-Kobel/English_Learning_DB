from __future__ import annotations

from copy import deepcopy

from ulga.builders import build_a1fs_v1_cp02_per_unit_authority_bindings as builder
from ulga.validators import validate_a1fs_v1_cp02_per_unit_authority_bindings as validator


def test_cp02_builds_source_proven_partial_binding_matrix() -> None:
    artifact = builder.build_artifact()
    report = validator.validate_artifact(artifact)

    assert report["validation_status"] == builder.PASS_STATUS
    assert report["errors"] == []
    assert artifact["coverage_summary"] == validator.EXPECTED_SUMMARY
    assert len(artifact["learning_units"]) == 24
    assert artifact["next_short_step"] == (
        "A1FS-V1-CP03_M11BReviewedAndRAZAdmittedExisting24UnitBinding"
    )


def test_cp02_reduces_pending_lanes_without_false_completion() -> None:
    artifact = builder.build_artifact()
    summary = artifact["coverage_summary"]

    assert summary["selected_authority_lane_count"] == 57
    assert summary["pending_authority_lane_count"] == 39
    assert summary["selected_unit_counts_by_authority"] == {
        "vocabulary": 24,
        "chunk": 1,
        "pattern": 9,
        "theme_situation": 23,
    }
    assert summary["all_four_content_authorities_selected_unit_count"] == 0
    assert artifact["claim_boundaries"]["four_skill_population_claimed_complete"] is False
    assert artifact["claim_boundaries"]["content_admission_changed"] is False


def test_cp02_preserves_rowless_demonstratives_with_structural_pattern_evidence() -> None:
    artifact = builder.build_artifact()
    row = next(
        row
        for row in artifact["learning_units"]
        if row["grammar_unit_id"] == builder.ROWLESS_STRUCTURAL_UNIT_ID
    )

    assert row["canonical_egp_row_ids"] == []
    pattern = row["authority_bindings"]["pattern"]
    assert pattern["selection_status"] == "SELECTED_AUTHORITY_BACKED"
    assert pattern["selected_refs"] == ["SP_000016", "SP_000017"]
    assert {
        evidence["method"] for evidence in pattern["evidence"]
    } == {"ROWLESS_STRUCTURAL_EXAMPLE_TO_APPROVED_PATTERN_FAMILY"}


def test_cp02_keeps_unproven_chunk_lanes_pending() -> None:
    artifact = builder.build_artifact()
    pending = [
        row
        for row in artifact["learning_units"]
        if row["authority_bindings"]["chunk"]["selection_status"]
        == "PENDING_SOURCE_EVIDENCE"
    ]

    assert len(pending) == 23
    for row in pending:
        binding = row["authority_bindings"]["chunk"]
        assert binding["selected_refs"] == []
        assert binding["evidence"] == []
        assert "DO_NOT_INVENT_MAPPING" in binding["reason"]


def test_cp02_validator_rejects_selected_ref_without_evidence() -> None:
    artifact = deepcopy(builder.build_artifact())
    binding = artifact["learning_units"][0]["authority_bindings"]["vocabulary"]
    binding["evidence"] = binding["evidence"][1:]

    report = validator.validate_artifact(artifact)

    assert report["validation_status"] == "FAIL"
    assert any("evidence_ref_mismatch" in error for error in report["errors"])


def test_cp02_validator_rejects_ref_outside_stage_scope() -> None:
    artifact = deepcopy(builder.build_artifact())
    binding = artifact["learning_units"][0]["authority_bindings"]["chunk"]
    binding.update(
        {
            "selection_status": "SELECTED_AUTHORITY_BACKED",
            "selected_refs": ["chunk:insofar_as"],
            "selection_count": 1,
            "evidence": [
                {
                    "ref": "chunk:insofar_as",
                    "method": "EXACT_A1_GENERATOR_SAFE_CHUNK_IN_POSITIVE_EXAMPLE",
                    "positive_example_indices": [0],
                    "source_refs": ["ulga/graph/chunk_nodes.json"],
                }
            ],
            "reason": None,
        }
    )

    report = validator.validate_artifact(artifact)

    assert report["validation_status"] == "FAIL"
    assert any("ref_outside_scope" in error for error in report["errors"])


def test_cp02_validator_rejects_false_scope_or_completion_claim() -> None:
    artifact = deepcopy(builder.build_artifact())
    artifact["claim_boundaries"]["a2_a2plus_in_scope"] = True
    artifact["learning_units"][0]["all_four_content_authorities_selected"] = True

    report = validator.validate_artifact(artifact)

    assert report["validation_status"] == "FAIL"
    assert "false_claim_boundary:a2_a2plus_in_scope" in report["errors"]
    assert any("all_four_selection_flag_mismatch" in error for error in report["errors"])
