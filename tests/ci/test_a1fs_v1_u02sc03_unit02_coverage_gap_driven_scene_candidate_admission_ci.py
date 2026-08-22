from ulga.builders import (
    build_a1fs_v1_u02sc03_unit02_coverage_gap_driven_scene_candidate_admission
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02sc03_unit02_coverage_gap_driven_scene_candidate_admission
    as validator,
)


def validated_candidate():
    candidate = builder.build_candidate_artifact()
    report = validator.validate_candidate(candidate)
    assert report["error_count"] == 0
    return candidate, report


def test_u02sc03_candidate_set_matches_exact_u02sc02_genuine_gap_denominator():
    candidate, report = validated_candidate()
    payload = candidate["payload"]
    gaps = builder.genuine_gap_singulars()

    assert gaps
    assert report["candidate_count"] == len(gaps)
    assert payload["admission_denominators"]["source_genuine_gap_count"] == len(gaps)
    assert payload["admission_denominators"]["candidate_count"] == len(gaps)
    assert payload["admission_denominators"]["one_candidate_per_genuine_gap"] is True
    assert payload["admission_denominators"]["candidate_target_singulars"] == gaps
    assert [row["target_singular"] for row in payload["candidates"]] == gaps


def test_u02sc03_admits_only_direct_eligible_semantically_uncovered_targets():
    candidate, _ = validated_candidate()
    summaries, vocabulary = builder.source_maps()

    for row in candidate["payload"]["candidates"]:
        singular = row["target_singular"]
        assert vocabulary[singular]["scene_gate"] == "DIRECT_SCENE_ELIGIBLE"
        assert summaries[singular]["semantic_reuse_scene_refs"] == []
        assert summaries[singular]["genuine_missing_new_unit02_scene_need"] is True

    candidate_targets = {row["target_singular"] for row in candidate["payload"]["candidates"]}
    assert "beer" not in candidate_targets
    assert "answer" not in candidate_targets
    assert "ice cream" not in candidate_targets


def test_u02sc03_preserves_family_compatible_but_semantically_missing_candidates():
    candidate, _ = validated_candidate()
    by_target = {
        row["target_singular"]: row for row in candidate["payload"]["candidates"]
    }

    assert "train" in by_target
    assert by_target["train"]["source_gap_evidence"]["semantic_reuse_scene_refs"] == []

    assert "chair" in by_target
    assert by_target["chair"]["source_gap_evidence"]["family_compatible_scene_refs"]
    assert by_target["chair"]["source_gap_evidence"]["semantic_reuse_scene_refs"] == []


def test_u02sc03_candidate_semantic_contract_is_structural_not_learner_facing_scene_text():
    candidate, _ = validated_candidate()

    for row in candidate["payload"]["candidates"]:
        contract = row["candidate_semantic_contract"]
        assert contract["required_object_surface"] == row["target_singular"]
        assert contract["required_plural_surface"] == row["target_plural"]
        assert contract["preferred_scene_families"][0] == row["primary_scene_family"]
        assert contract["must_support_unit02_plural_contrast"] is True
        assert row["canonical_scene_identity_assigned"] is False
        assert row["learner_facing"] is False
        assert row["source_equivalence_claimed"] is False


def test_u02sc03_independent_validation_admits_policy_bound_candidate_without_scene_authority_write():
    candidate, report = validated_candidate()
    approved = builder.admit_validated_candidate(candidate, report)
    approved_report = validator.validate_approved(approved, report)

    assert candidate["artifact_role"] == builder.content_policy.CANDIDATE_ROLE
    assert approved["artifact_role"] == builder.content_policy.APPROVED_ROLE
    assert approved["admission"]["status"] == "APPROVED"
    assert approved["learner_facing"] is False
    assert approved_report["error_count"] == 0
    assert approved["payload"]["claim_boundaries"]["canonical_scene_created"] is False
    assert approved["payload"]["claim_boundaries"]["canonical_scene_authority_mutated"] is False


def test_u02sc03_remains_q7_only_and_does_not_mutate_runtime_questionbank_or_a2():
    candidate, _ = validated_candidate()
    payload = candidate["payload"]

    assert payload["artifact_semantics"] == (
        "APPROVED_SCENE_AUTHORING_CANDIDATE_SET_NOT_CANONICAL_SCENE_AUTHORITY"
    )
    assert payload["claim_boundaries"] == {
        "canonical_scene_authority_mutated": False,
        "unit01_scene_authority_mutated": False,
        "unit02_vocabulary_authority_mutated": False,
        "canonical_scene_created": False,
        "learner_facing_scene_created": False,
        "questionbank_mutated": False,
        "learner_runtime_connected": False,
        "a2_unlocked": False,
    }
    assert payload["next_short_step"] == builder.NEXT_SHORT_STEP
