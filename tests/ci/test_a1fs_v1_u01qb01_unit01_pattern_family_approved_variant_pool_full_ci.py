from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool_full as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool_full as validator,
)


def test_u01qb01_full_ci_gate_exact_readback():
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    payload = approved["payload"]

    assert report["status"] == "PASS"
    assert report["error_count"] == 0
    assert report["approved_variant_count"] == 308
    assert report["pattern_family_count"] == 32
    assert payload["design_space_capacity"][
        "theoretical_raw_combinatorial_capacity"
    ] == 944
    assert payload["design_space_capacity"][
        "authority_grounded_candidate_count"
    ] == 308
    assert payload["design_space_capacity"][
        "theoretical_candidates_not_admitted_without_additional_authority"
    ] == 636
    assert payload["distribution_counts"]["skill"] == {
        "READING": 123,
        "SPEAKING": 50,
        "WRITING": 135,
    }
    assert payload["coverage_denominators"]["active_evp_sense_count"] == 22
    assert payload["coverage_denominators"]["exercise_covered_egp_row_count"] == 3
    assert payload["coverage_denominators"]["learner_mastery_claimed"] is False
    assert payload["claim_boundaries"]["demonstrative_patterns_in_unit01"] is False
    assert payload["claim_boundaries"]["unit02_to_unit24_modified"] is False
    assert payload["claim_boundaries"]["a2_unlocked"] is False
