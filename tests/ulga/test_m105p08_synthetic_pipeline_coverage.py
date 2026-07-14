import pytest

from ulga.builders.build_a1_private_pilot_synthetic_pipeline_coverage import (
    ROWLESS_STRUCTURAL_UNITS,
    STRUCTURAL_PASS_STATUS,
    build_report,
    validate_synthetic_unit_coverage,
)
from ulga.validators.a1_a1plus_delivery_coverage_gate import PASS_STATUS


def test_all_a1_a1plus_units_pass_engineering_pipeline_without_mastery_claims():
    report = build_report()
    assert report["validation_status"] == "PASS"
    assert report["scope"] == "A1_A1_PLUS_ONLY"
    assert report["unit_count"] == 24
    assert report["pipeline_pass_unit_count"] == 24
    assert report["coverage_gated_unit_count"] == 24
    assert report["direct_canonical_gate_unit_count"] == 23
    assert report["rowless_structural_gate_unit_count"] == 1
    assert report["rowless_structural_unit_ids"] == ["GRAMMAR_DEMONSTRATIVES_CONTRAST"]
    assert report["human_pilot_sampled_unit_count"] == 3
    assert report["synthetic_only_unit_count"] == 21
    assert report["failed_unit_ids"] == []
    assert report["claims"] == {
        "learner_evidence_created": False,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
    }
    assert all(unit["synthetic_engineering_probe"] is True for unit in report["units"])
    assert all(unit["checks"]["coverage_gate"] is True for unit in report["units"])
    assert all(unit["projection_status"] == "MASTERY_CANDIDATE_PENDING_RETENTION" for unit in report["units"])
    assert all(all(unit["checks"].values()) for unit in report["units"])

    direct = [row for row in report["units"] if row["coverage_gate_mode"] == "DIRECT_CANONICAL_ROWS"]
    structural = [
        row for row in report["units"]
        if row["coverage_gate_mode"] == "PACKAGE_CANONICAL_SET_FOR_ROWLESS_STRUCTURAL_UNIT"
    ]
    assert len(direct) == 23
    assert all(row["canonical_egp_row_ids"] for row in direct)
    assert all(row["coverage_gate_status"] == PASS_STATUS for row in direct)
    assert structural == [
        next(row for row in report["units"] if row["grammar_unit_id"] == "GRAMMAR_DEMONSTRATIVES_CONTRAST")
    ]
    assert structural[0]["canonical_egp_row_ids"] == []
    assert structural[0]["coverage_gate_status"] == STRUCTURAL_PASS_STATUS
    assert structural[0]["package_canonical_row_count"] == 109


def test_rowless_structural_gate_is_explicit_and_fails_closed():
    coverage = {
        "validation_status": "PASS",
        "canonical_row_count": 109,
        "covered_row_count": 109,
        "missing_row_count": 0,
        "draft_only_row_count": 0,
        "unexpected_row_count": 0,
    }
    allowed = validate_synthetic_unit_coverage(
        {"grammar_unit_id": "GRAMMAR_DEMONSTRATIVES_CONTRAST", "canonical_egp_row_ids": []},
        coverage_report=coverage,
    )
    assert allowed["status"] == STRUCTURAL_PASS_STATUS
    assert allowed["canonical_egp_row_ids"] == []
    assert ROWLESS_STRUCTURAL_UNITS == {"GRAMMAR_DEMONSTRATIVES_CONTRAST"}

    with pytest.raises(ValueError, match="synthetic_pipeline_unapproved_rowless_unit"):
        validate_synthetic_unit_coverage(
            {"grammar_unit_id": "GRAMMAR_UNEXPECTED_ROWLESS", "canonical_egp_row_ids": []},
            coverage_report=coverage,
        )

    incomplete = dict(coverage, covered_row_count=108, missing_row_count=1)
    with pytest.raises(ValueError, match="synthetic_pipeline_package_coverage_incomplete"):
        validate_synthetic_unit_coverage(
            {"grammar_unit_id": "GRAMMAR_DEMONSTRATIVES_CONTRAST", "canonical_egp_row_ids": []},
            coverage_report=incomplete,
        )


def test_human_sample_is_exact_and_synthetic_results_are_not_learner_evidence():
    report = build_report()
    sampled = {row["grammar_unit_id"] for row in report["units"] if row["human_pilot_sampled"]}
    assert sampled == {
        "GRAMMAR_ARTICLES_BASIC",
        "GRAMMAR_REGULAR_PLURAL_NOUNS",
        "GRAMMAR_SUBJECT_PRONOUNS",
    }
    assert report["next_short_step"] == "R7-M105P09_A1A1PlusSyntheticCoverageGapReviewAndHumanPilotMinimumSet"
