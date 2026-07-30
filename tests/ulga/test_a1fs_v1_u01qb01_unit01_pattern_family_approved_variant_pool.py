from copy import deepcopy

import pytest

from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as validator,
)


def test_u01qb01_builds_109_authority_grounded_variants():
    payload = builder.candidate_payload()
    assert payload["design_space_capacity"] == {
        "active_noun_count": 16,
        "active_adjective_count": 6,
        "context_count": 5,
        "safe_intensifier_adjective_count": 4,
        "raw_combinatorial_capacity": 944,
        "strict_prevalidation_capacity": 848,
        "materialized_authority_grounded_candidate_count": 109,
    }
    assert len(payload["pattern_family_contracts"]) == 10
    assert len(payload["candidate_items"]) == 109
    assert payload["distribution_counts"]["skill"] == {
        "READING": 40,
        "SPEAKING": 22,
        "WRITING": 47,
    }


def test_u01qb01_covers_all_active_evp_and_three_egp_rows_without_mastery_claim():
    payload = builder.candidate_payload()
    coverage = payload["coverage_denominators"]
    assert coverage["active_evp_sense_count"] == 22
    assert coverage["exercise_covered_egp_row_count"] == 3
    assert coverage["a1_egp_denominator"] == 109
    assert coverage["learner_mastery_claimed"] is False
    assert coverage["ket_canonical_prerequisite_node_claimed"] is False
    assert coverage["semantic_ket_prerequisite_capability"] == "ARTICLE_NOUN_PHRASE_CONTROL"


def test_u01qb01_keeps_np_structures_and_demonstratives_separate():
    payload = builder.candidate_payload()
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
    assert payload["distribution_counts"]["unit_pattern"] == {
        builder.PATTERN_ADJECTIVE: 18,
        builder.PATTERN_NOUN: 88,
        builder.PATTERN_VERY: 3,
    }


def test_u01qb01_adjective_variants_use_only_approved_contract_pairs():
    payload = builder.candidate_payload()
    direct_pairs = validator.direct_pair_sense_sets()
    very_pairs = validator.very_pair_sense_sets()
    for item in payload["candidate_items"]:
        pattern = item["unit_pattern_ids"][0]
        if pattern == builder.PATTERN_ADJECTIVE:
            assert frozenset(item["target_evp_sense_ids"]) in direct_pairs
        elif pattern == builder.PATTERN_VERY:
            assert frozenset(item["target_evp_sense_ids"]) in very_pairs


def test_u01qb01_session_metadata_is_exposure_aware_but_not_runtime_connected():
    session = builder.candidate_payload()["session_assembly_metadata"]
    assert session["runtime_status"] == "NOT_CONNECTED_METADATA_ONLY"
    assert session["session_size"] == 10
    assert sum(session["selection_quota"].values()) == 10
    assert session["recent_exposure_exclusion"] == {
        "same_item_within_session_forbidden": True,
        "exclude_last_n_item_exposures": 10,
        "assessment_prefers_unseen_items": True,
        "reassessment_replays_original_item_by_default": False,
    }


def test_u01qb01_candidate_and_approved_round_trip():
    candidate = builder.build_candidate()
    receipt = validator.validate_candidate(candidate)
    assert receipt["status"] == "PASS"
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["status"] == "PASS"
    assert report["error_count"] == 0
    assert report["approved_variant_count"] == 109
    assert report["pattern_family_count"] == 10


def test_u01qb01_validator_rejects_duplicate_semantic_signature():
    candidate = builder.build_candidate()
    broken = deepcopy(candidate)
    broken["payload"]["candidate_items"][1]["semantic_signature"] = (
        broken["payload"]["candidate_items"][0]["semantic_signature"]
    )
    broken["artifact_sha256"] = builder.policy_artifact.digest(
        {key: value for key, value in broken.items() if key != "artifact_sha256"}
    )
    with pytest.raises(validator.VariantPoolValidationError, match="DUPLICATE_SEMANTIC_SIGNATURE"):
        validator.validate_candidate(broken)


def test_u01qb01_validator_rejects_demonstrative_pattern_leak():
    candidate = builder.build_candidate()
    broken = deepcopy(candidate)
    broken["payload"]["candidate_items"][0]["unit_pattern_ids"] = ["SP_000016"]
    broken["payload"]["candidate_items"][0]["semantic_signature"] = validator.expected_signature(
        broken["payload"]["candidate_items"][0]
    )
    broken["artifact_sha256"] = builder.policy_artifact.digest(
        {key: value for key, value in broken.items() if key != "artifact_sha256"}
    )
    with pytest.raises(validator.VariantPoolValidationError):
        validator.validate_candidate(broken)
