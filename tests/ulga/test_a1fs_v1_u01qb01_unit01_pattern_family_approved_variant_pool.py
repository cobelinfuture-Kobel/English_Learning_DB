from copy import deepcopy

import pytest

from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as validator,
)


def test_u01qb01_materializes_full_candidate_space_then_admits_validated_subset():
    payload = builder.candidate_payload()
    assert payload["design_space_capacity"] == {
        "active_noun_count": 16,
        "active_adjective_count": 6,
        "context_count": 5,
        "safe_intensifier_adjective_count": 4,
        "raw_combinatorial_capacity": 944,
        "strict_prevalidation_capacity": 848,
        "speaking_extension_candidate_count": 25,
        "materialized_candidate_count": 873,
        "validator_approved_count": 288,
        "validator_rejected_count": 585,
        "canonical_language_asset_combination_count": 25,
        "runtime_variant_count": 0,
    }
    assert len(payload["pattern_family_contracts"]) == 12
    assert len(payload["candidate_items"]) == 873
    assert len(payload["approved_items"]) == 288
    assert payload["admission_readback"] == {
        "candidate_count": 873,
        "approved_count": 288,
        "rejected_count": 585,
        "human_review_count": 0,
        "rejection_reason_counts": {
            "ADJECTIVE_NOUN_PAIR_NOT_IN_APPROVED_CONTRACT": 270,
            "CONTEXT_NOUN_PAIR_NOT_APPROVED": 132,
            "VERY_ADJECTIVE_NOUN_PAIR_NOT_IN_APPROVED_CONTRACT": 183,
        },
    }


def test_u01qb01_separates_language_assets_tasks_and_runtime_variants():
    assert builder.candidate_payload()["count_semantics"] == {
        "language_asset_count_is_not_task_count": True,
        "canonical_task_count_is_not_runtime_variant_count": True,
        "canonical_language_asset_combination_count": 25,
        "canonical_approved_task_count": 288,
        "runtime_variant_count": 0,
    }


def test_u01qb01_approved_distribution_and_coverage_are_exact():
    payload = builder.candidate_payload()
    approved = payload["distribution_counts"]["approved"]
    assert approved["skill"] == {"READING": 166, "SPEAKING": 25, "WRITING": 97}
    assert approved["unit_pattern"] == {
        builder.PATTERN_VERY: 12,
        builder.PATTERN_ADJECTIVE: 24,
        builder.PATTERN_NOUN: 252,
    }
    coverage = payload["coverage_denominators"]
    assert coverage["active_evp_sense_count"] == 22
    assert coverage["exercise_covered_egp_row_count"] == 3
    assert coverage["a1_egp_denominator"] == 109
    assert coverage["learner_mastery_claimed"] is False


def test_u01qb01_keeps_demonstratives_out_and_np_structures_separate():
    patterns = {
        pattern
        for item in builder.candidate_payload()["candidate_items"]
        for pattern in item["unit_pattern_ids"]
    }
    assert patterns == {
        builder.PATTERN_NOUN,
        builder.PATTERN_ADJECTIVE,
        builder.PATTERN_VERY,
    }
    assert not patterns.intersection(builder.FORBIDDEN_DEMONSTRATIVE_PATTERN_IDS)


def test_u01qb01_rejections_are_explicit_not_silently_dropped():
    payload = builder.candidate_payload()
    rejected = [
        row
        for row in payload["candidate_items"]
        if row["admission_proposal"]["status"] == "AUTO_REJECTED"
    ]
    approved_ids = {row["item_id"] for row in payload["approved_items"]}
    assert len(rejected) == 585
    assert all(row["admission_proposal"]["reason_codes"] for row in rejected)
    assert not any(row["item_id"] in approved_ids for row in rejected)


def test_u01qb01_candidate_and_approved_round_trip():
    candidate = builder.build_candidate()
    assert validator.validate_candidate(candidate)["status"] == "PASS"
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["status"] == "PASS"
    assert report["error_count"] == 0
    assert report["candidate_count"] == 873
    assert report["approved_variant_count"] == 288
    assert report["rejected_candidate_count"] == 585
    assert report["pattern_family_count"] == 12


def test_u01qb01_validator_rejects_unapproved_candidate_inside_approved_subset():
    candidate = builder.build_candidate()
    broken = deepcopy(candidate)
    rejected = next(
        row
        for row in broken["payload"]["candidate_items"]
        if row["admission_proposal"]["status"] == "AUTO_REJECTED"
    )
    broken["payload"]["approved_items"][0] = deepcopy(rejected)
    broken["artifact_sha256"] = builder.policy_artifact.digest(
        {key: value for key, value in broken.items() if key != "artifact_sha256"}
    )
    with pytest.raises(validator.VariantPoolValidationError):
        validator.validate_candidate(broken)


def test_u01qb01_validator_rejects_demonstrative_pattern_leak():
    candidate = builder.build_candidate()
    broken = deepcopy(candidate)
    item = broken["payload"]["candidate_items"][0]
    item["unit_pattern_ids"] = ["SP_000016"]
    item["semantic_signature"] = validator.expected_signature(item)
    broken["artifact_sha256"] = builder.policy_artifact.digest(
        {key: value for key, value in broken.items() if key != "artifact_sha256"}
    )
    with pytest.raises(validator.VariantPoolValidationError):
        validator.validate_candidate(broken)
