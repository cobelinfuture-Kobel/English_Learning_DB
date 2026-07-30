from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as validator,
)


def test_u01qb01_ci_gate_full_candidate_admission_readback():
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    payload = approved["payload"]

    assert report["status"] == "PASS"
    assert report["error_count"] == 0
    assert report["candidate_count"] == 873
    assert report["approved_variant_count"] == 288
    assert report["rejected_candidate_count"] == 585
    assert report["pattern_family_count"] == 12

    assert payload["design_space_capacity"]["strict_prevalidation_capacity"] == 848
    assert payload["design_space_capacity"]["materialized_candidate_count"] == 873
    assert payload["admission_readback"]["approved_count"] == 288
    assert payload["admission_readback"]["rejected_count"] == 585
    assert payload["count_semantics"]["canonical_language_asset_combination_count"] == 25
    assert payload["count_semantics"]["canonical_approved_task_count"] == 288
    assert payload["count_semantics"]["runtime_variant_count"] == 0
    assert payload["coverage_denominators"]["active_evp_sense_count"] == 22
    assert payload["coverage_denominators"]["exercise_covered_egp_row_count"] == 3
    assert payload["coverage_denominators"]["learner_mastery_claimed"] is False
    assert payload["claim_boundaries"]["demonstrative_patterns_in_unit01"] is False
    assert payload["claim_boundaries"]["unit02_to_unit24_modified"] is False
    assert payload["claim_boundaries"]["a2_unlocked"] is False
