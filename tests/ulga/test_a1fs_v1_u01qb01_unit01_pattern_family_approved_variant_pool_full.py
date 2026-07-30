from copy import deepcopy

import pytest

from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as seed,
)
from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool_full as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool_full as validator,
)


def test_u01qb01_full_builds_308_authority_grounded_variants():
    payload = builder.candidate_payload()
    assert payload["design_space_capacity"] == {
        "theoretical_raw_combinatorial_capacity": 944,
        "seed_authority_grounded_count": 109,
        "expansion_authority_grounded_count": 199,
        "authority_grounded_candidate_count": 308,
        "theoretical_candidates_not_admitted_without_additional_authority": 636,
        "approved_direct_adjective_phrase_count": 6,
        "approved_very_adjective_phrase_count": 3,
        "excluded_space_reason": (
            "NO_APPROVED_ADJECTIVE_NOUN_COMPATIBILITY_MATRIX_OR_CONTEXT_REALIZATION_AUTHORITY"
        ),
    }
    assert len(payload["candidate_items"]) == 308
    assert len(payload["pattern_family_contracts"]) == 33
    assert payload["distribution_counts"]["skill"] == {
        "READING": 123,
        "SPEAKING": 50,
        "WRITING": 135,
    }


def test_u01qb01_full_preserves_seed_and_adds_199_distinct_items():
    seed_ids = {row["item_id"] for row in seed.build_items()}
    full_ids = {row["item_id"] for row in builder.build_items()}
    assert seed_ids < full_ids
    assert len(seed_ids) == 109
    assert len(full_ids - seed_ids) == 199


def test_u01qb01_full_keeps_authority_and_coverage_boundaries():
    payload = builder.candidate_payload()
    coverage = payload["coverage_denominators"]
    assert coverage["active_evp_sense_count"] == 22
    assert coverage["exercise_covered_egp_row_count"] == 3
    assert coverage["learner_mastery_claimed"] is False
    assert coverage["ket_canonical_prerequisite_node_claimed"] is False
    patterns = {
        pattern
        for item in payload["candidate_items"]
        for pattern in item["unit_pattern_ids"]
    }
    assert patterns == {
        builder.PATTERN_NOUN,
        builder.PATTERN_ADJECTIVE,
        builder.PATTERN_VERY,
    }
    assert not patterns.intersection(builder.FORBIDDEN_DEMONSTRATIVE_PATTERN_IDS)


def test_u01qb01_full_candidate_and_approved_round_trip():
    candidate = builder.build_candidate()
    receipt = validator.validate_candidate(candidate)
    assert receipt["status"] == "PASS"
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["status"] == "PASS"
    assert report["error_count"] == 0
    assert report["approved_variant_count"] == 308
    assert report["pattern_family_count"] == 33


def test_u01qb01_full_validator_rejects_duplicate_signature():
    candidate = builder.build_candidate()
    broken = deepcopy(candidate)
    broken["payload"]["candidate_items"][1]["semantic_signature"] = (
        broken["payload"]["candidate_items"][0]["semantic_signature"]
    )
    broken["artifact_sha256"] = builder.policy_artifact.digest(
        {key: value for key, value in broken.items() if key != "artifact_sha256"}
    )
    with pytest.raises(
        validator.FullVariantPoolValidationError,
        match="DUPLICATE_SEMANTIC_SIGNATURE",
    ):
        validator.validate_candidate(broken)


def test_u01qb01_full_validator_rejects_demonstrative_leak():
    candidate = builder.build_candidate()
    broken = deepcopy(candidate)
    expansion = next(
        row
        for row in broken["payload"]["candidate_items"]
        if row["pattern_family_id"] in {
            item["family_id"] for item in builder.EXPANSION_FAMILY_CONTRACTS
        }
    )
    expansion["unit_pattern_ids"] = ["SP_000016"]
    expansion["semantic_signature"] = validator.expected_signature(expansion)
    broken["artifact_sha256"] = builder.policy_artifact.digest(
        {key: value for key, value in broken.items() if key != "artifact_sha256"}
    )
    with pytest.raises(validator.FullVariantPoolValidationError):
        validator.validate_candidate(broken)
