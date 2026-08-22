from ulga.builders import (
    build_a1fs_v1_u02sc04_unit02_admitted_scene_candidate_materialization_and_coverage_recheck
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02sc04_unit02_admitted_scene_candidate_materialization_and_coverage_recheck
    as validator,
)


def validated_candidate():
    candidate = builder.build_candidate_artifact()
    report = validator.validate_candidate(candidate)
    assert report["error_count"] == 0
    return candidate, report


def test_u02sc04_materializes_exactly_one_structural_scene_candidate_per_u02sc03_gap():
    candidate, report = validated_candidate()
    payload = candidate["payload"]
    gaps = builder.u02sc03.genuine_gap_singulars()
    rows = payload["materialized_scene_candidates"]

    assert gaps
    assert len(rows) == len(gaps)
    assert report["materialized_scene_candidate_count"] == len(gaps)
    assert [row["target_singular"] for row in rows] == gaps
    assert len({row["materialization_id"] for row in rows}) == len(rows)
    assert len({row["scene_candidate_signature_sha256"] for row in rows}) == len(rows)


def test_u02sc04_materialized_semantics_remain_noncanonical_nonruntime_and_nonlearner_facing():
    candidate, _ = validated_candidate()

    for row in candidate["payload"]["materialized_scene_candidates"]:
        core = row["scene_semantic_core"]
        assert row["canonical_scene_identity_assigned"] is False
        assert row["canonical_scene_ref_id"] is None
        assert row["runtime_bindable"] is False
        assert row["learner_facing"] is False
        assert row["source_equivalence_claimed"] is False
        assert core["target_object_lemma"] == row["target_singular"]
        assert core["object_surfaces"] == [row["target_singular"], row["target_plural"]]
        assert core["plural_contrast_supported"] is True
        assert "setting_code" in core
        assert "sentence" not in row
        assert "sentences" not in row
        assert "prompt" not in row
        assert "learner_text" not in row


def test_u02sc04_candidate_adjusted_coverage_recheck_closes_all_direct_scene_gaps():
    candidate, _ = validated_candidate()
    payload = candidate["payload"]
    counts = payload["coverage_denominators"]

    assert counts["current_canonical_scene_world_count"] == 32
    assert counts["new_unit02_scene_candidate_count"] == len(
        builder.u02sc03.genuine_gap_singulars()
    )
    assert counts["projected_cumulative_scene_world_count_if_candidates_promoted"] == (
        32 + counts["new_unit02_scene_candidate_count"]
    )
    assert counts["direct_eligible_covered_by_admitted_candidate_count"] == (
        counts["new_unit02_scene_candidate_count"]
    )
    assert counts["candidate_adjusted_remaining_direct_scene_gap_count"] == 0
    assert counts["candidate_adjusted_remaining_direct_scene_gap_singulars"] == []


def test_u02sc04_train_and_chair_are_candidate_covered_while_non_scene_gates_stay_gated():
    candidate, _ = validated_candidate()
    rows = {
        row["singular"]: row for row in candidate["payload"]["coverage_recheck"]
    }

    assert rows["train"]["coverage_status"] == "COVERED_BY_ADMITTED_U02_SCENE_CANDIDATE"
    assert rows["train"]["materialization_id"]
    assert rows["chair"]["coverage_status"] == "COVERED_BY_ADMITTED_U02_SCENE_CANDIDATE"
    assert rows["chair"]["materialization_id"]

    assert rows["beer"]["coverage_status"] == "GATED_NON_SCENE_GAP"
    assert rows["answer"]["coverage_status"] == "GATED_NON_SCENE_GAP"
    assert rows["ice cream"]["coverage_status"] == "GATED_NON_SCENE_GAP"
    assert rows["beer"]["materialization_id"] is None
    assert rows["answer"]["materialization_id"] is None
    assert rows["ice cream"]["materialization_id"] is None


def test_u02sc04_existing_semantic_reuse_is_preserved_and_not_reauthored():
    candidate, _ = validated_candidate()
    rows = {
        row["singular"]: row for row in candidate["payload"]["coverage_recheck"]
    }

    assert rows["book"]["coverage_status"] == "COVERED_BY_EXISTING_U01_SCENE_SEMANTICS"
    assert rows["book"]["existing_semantic_reuse_scene_refs"]
    assert rows["book"]["materialization_id"] is None
    assert rows["book"]["source_u02sc02_genuine_gap"] is False


def test_u02sc04_independent_validation_admits_q7_materialization_without_canonical_scene_write():
    candidate, report = validated_candidate()
    approved = builder.admit_validated_candidate(candidate, report)
    approved_report = validator.validate_approved(approved, report)

    assert candidate["artifact_role"] == builder.content_policy.CANDIDATE_ROLE
    assert approved["artifact_role"] == builder.content_policy.APPROVED_ROLE
    assert approved["admission"]["status"] == "APPROVED"
    assert approved["learner_facing"] is False
    assert approved_report["remaining_direct_scene_gap_count"] == 0
    assert approved["payload"]["claim_boundaries"] == {
        "canonical_scene_authority_mutated": False,
        "unit01_scene_authority_mutated": False,
        "unit02_vocabulary_authority_mutated": False,
        "canonical_scene_created": False,
        "canonical_scene_promoted": False,
        "learner_facing_scene_created": False,
        "questionbank_mutated": False,
        "learner_runtime_connected": False,
        "a2_unlocked": False,
    }


def test_u02sc04_closes_q7_micro_scene_denominator_and_stops_before_q8_communicative_function():
    candidate, _ = validated_candidate()
    payload = candidate["payload"]

    contract = payload["question7_micro_scene_coverage_contract"]
    assert contract["q7_micro_scene_denominator_resolved"] is True
    assert contract["candidate_adjusted_remaining_direct_scene_gap_is_zero"] is True
    assert payload["next_scope"] == {
        "coverage_denominator_number": 8,
        "coverage_denominator": "COMMUNICATIVE_FUNCTION",
        "scope_status": "OUTSIDE_APPROVED_Q7_SCOPE",
    }
    assert payload["next_short_step"] == (
        "A1FS-V1-U02CF01_Unit02CommunicativeFunctionCoverageDenominator"
    )
