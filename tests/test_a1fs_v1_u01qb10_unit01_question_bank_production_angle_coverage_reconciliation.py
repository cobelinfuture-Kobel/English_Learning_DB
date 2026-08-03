from __future__ import annotations

from copy import deepcopy

from ulga.builders import build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as builder
from ulga.validators import validate_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as validator


def payload() -> dict:
    return builder.reconciled_payload()


def test_count_preserving_revision_keeps_288_base_and_474_projected_total() -> None:
    result = payload()
    validator.validate_payload(result)
    counts = result["count_preservation"]
    assert counts == {
        "seed_base_count": 288,
        "retained_base_count": 240,
        "removed_base_count": 48,
        "production_items_added": 48,
        "reconciled_base_count": 288,
        "unchanged_real62_extension_count": 186,
        "projected_runtime_total_count": 474,
        "runtime_activation_completed": False,
    }


def test_distribution_rebalances_reading_writing_without_touching_speaking() -> None:
    result = payload()
    assert result["distribution_counts"]["skill"] == {
        "READING": 130,
        "SPEAKING": 25,
        "WRITING": 133,
    }
    families = result["distribution_counts"]["family"]
    assert families["U01-PF04-FIRST-MENTION-CONTEXT"] == 35
    assert families["U01-PF05-KNOWN-REFERENCE-CONTEXT"] == 35
    assert families["U01-PF08-TRANSFER-FIRST-MENTION"] == 35
    assert families["U01-PF09-TRANSFER-KNOWN-REFERENCE"] == 35
    assert families[builder.PF13] == 12
    assert families[builder.PF14] == 24
    assert families[builder.PF15] == 12


def test_production_gap_is_closed_but_partial_alignment_remains_visible() -> None:
    coverage = payload()["production_angle_coverage"]
    assert coverage["scored_gap_count_before"] == 48
    assert coverage["scored_gap_count_after"] == 0
    assert coverage["scored_partial_support_remaining"] == 36
    assert coverage["production_angle_alignment_ready"] is True
    assert coverage["question_bank_full_alignment_ready"] is False
    assert coverage["remaining_partial_angles"] == [
        "READING_REFERENCE_EVIDENCE",
        "WRITING_PHRASE_CONSTRUCTION",
    ]


def test_complete_and_connected_sentence_production_use_feature_rubric() -> None:
    items = payload()["reconciled_items"]
    complete = [row for row in items if row["pattern_family_id"] == builder.PF14]
    connected = [row for row in items if row["pattern_family_id"] == builder.PF15]
    assert len(complete) == 24
    assert len(connected) == 12
    for row in [*complete, *connected]:
        assert row["scoring_mode"] == "FEATURE_RUBRIC"
        assert row["human_review_required"] is True
        assert row["response_contract"]["capture_enabled"] is True
        assert row["response_contract"]["human_review_fallback"] is True
        assert row["response_contract"]["rubric"]["minor_surface_error_does_not_zero_concept"] is True
    for row in connected:
        features = set(row["response_contract"]["rubric"]["concept_features"])
        assert {
            "first_mention_article",
            "known_reference_article",
            "same_referent_preserved",
            "sentence_1_complete",
            "sentence_2_complete",
        } <= features


def test_speaking_boundary_and_runtime_boundary_remain_locked() -> None:
    result = payload()
    speaking = [row for row in result["reconciled_items"] if row["skill"] == "SPEAKING"]
    assert len(speaking) == 25
    assert all(row["response_contract"]["capture_enabled"] is False for row in speaking)
    assert all(row["assessment_eligible"] is False for row in speaking)
    assert result["boundaries"] == {
        "new_scene_authored": False,
        "question_bank_total_expanded": False,
        "second_question_bank_created": False,
        "runtime_migrated": False,
        "real62_extension_modified": False,
        "learner_state_modified": False,
        "speaking_scoring_enabled": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }


def test_validator_rejects_false_runtime_activation_claim() -> None:
    result = payload()
    drifted = deepcopy(result)
    drifted["boundaries"]["runtime_migrated"] = True
    unsigned = deepcopy(drifted)
    unsigned.pop("reconciliation_sha256", None)
    drifted["reconciliation_sha256"] = builder.policy_artifact.digest(unsigned)
    try:
        validator.validate_payload(drifted)
    except validator.ReconciliationValidationError as exc:
        assert "BOUNDARY_INVALID:runtime_migrated" in str(exc)
    else:
        raise AssertionError("validator accepted false runtime migration claim")


def test_policy_bound_candidate_and_approved_artifact_validate() -> None:
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["status"] == "PASS"
    assert report["error_count"] == 0
    assert report["reconciled_base_count"] == 288
    assert report["projected_runtime_total_count"] == 474
    assert report["scored_gap_count_after"] == 0
    assert report["runtime_migrated"] is False
