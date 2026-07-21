from copy import deepcopy
from pathlib import Path

import pytest

from ulga.validators import validate_a1fs_v1_canonical_content_production_policy as governance


REPO_ROOT = Path(__file__).resolve().parents[2]


def committed_policy():
    return governance.load_policy(REPO_ROOT / governance.POLICY_REL)


def test_committed_governance_contract_and_repository_wiring_pass():
    report = governance.validate_repository(REPO_ROOT)
    assert report["validation_status"] == "PASS_A1FS_V1_CANONICAL_CONTENT_PRODUCTION_GOVERNANCE"
    assert report["canonical_source"] == "APPROVED_CANONICAL_JSON"
    assert report["four_skill_source"] == "VALIDATED_APPROVED_JSON"
    assert report["excel_role"] == "DERIVED_REFERENCE_ONLY"
    assert report["excel_writeback_allowed"] is False
    assert report["policy_bound_artifact_required"] is True
    assert report["a2_unlocked"] is False
    assert report["error_count"] == 0


def test_excel_cannot_become_canonical_source():
    policy = deepcopy(committed_policy())
    policy["authoritative_source"] = "EXCEL"
    with pytest.raises(governance.GovernanceValidationError, match="canonical_source_invalid"):
        governance.validate_policy(policy)


def test_excel_writeback_cannot_be_enabled():
    policy = deepcopy(committed_policy())
    policy["excel"]["canonical_writeback_allowed"] = True
    with pytest.raises(governance.GovernanceValidationError, match="excel_writeback_forbidden"):
        governance.validate_policy(policy)


def test_validator_cannot_generate_candidate_content():
    policy = deepcopy(committed_policy())
    policy["candidate_generation"]["validator_may_generate_candidate_content"] = True
    with pytest.raises(
        governance.GovernanceValidationError,
        match="validator_candidate_generation_forbidden",
    ):
        governance.validate_policy(policy)


def test_unvalidated_candidate_cannot_be_learner_facing():
    policy = deepcopy(committed_policy())
    policy["candidate_generation"]["learner_facing_before_admission"] = True
    with pytest.raises(governance.GovernanceValidationError, match="candidate_learners_forbidden"):
        governance.validate_policy(policy)


def test_text_pipeline_order_is_immutable():
    policy = deepcopy(committed_policy())
    pipeline = policy["text_pipeline"]
    approved_index = pipeline.index("APPROVED_CANONICAL_JSON")
    projection_index = pipeline.index("FOUR_SKILL_PROJECTION_JSON")
    pipeline[approved_index], pipeline[projection_index] = (
        pipeline[projection_index],
        pipeline[approved_index],
    )
    with pytest.raises(governance.GovernanceValidationError, match="text_pipeline_order_invalid"):
        governance.validate_policy(policy)


def test_image_generation_requires_semantic_answerability_and_visualizability_pass():
    policy = deepcopy(committed_policy())
    policy["image_generation_gate"]["required_statuses"].remove("SEMANTIC_PASS")
    with pytest.raises(governance.GovernanceValidationError, match="image_generation_gate_invalid"):
        governance.validate_policy(policy)


def test_generated_image_cannot_bypass_scene_consistency_validation():
    policy = deepcopy(committed_policy())
    policy["multimodal_pipeline"].remove("IMAGE_SCENE_CONSISTENCY_VALIDATION")
    with pytest.raises(governance.GovernanceValidationError, match="multimodal_pipeline_order_invalid"):
        governance.validate_policy(policy)


def test_all_four_skills_must_share_the_approved_json_source():
    policy = deepcopy(committed_policy())
    policy["four_skill_projections"].remove("SPEAKING")
    with pytest.raises(governance.GovernanceValidationError, match="four_skill_projection_set_invalid"):
        governance.validate_policy(policy)


def test_a2_cannot_be_unlocked_by_this_policy():
    policy = deepcopy(committed_policy())
    policy["a2_unlocked"] = True
    with pytest.raises(governance.GovernanceValidationError, match="a2_must_remain_locked"):
        governance.validate_policy(policy)


def test_artifact_binding_paths_are_immutable():
    policy = deepcopy(committed_policy())
    policy["artifact_binding"]["builder"] = "ulga/builders/other.py"
    with pytest.raises(governance.GovernanceValidationError, match="artifact_builder_path_invalid"):
        governance.validate_policy(policy)


def test_changed_protected_builder_requires_policy_mode():
    policy = committed_policy()
    with pytest.raises(
        governance.GovernanceValidationError,
        match="builder_policy_mode_missing",
    ):
        governance.validate_builder_source_binding(
            path="ulga/builders/build_a1fs_v1_new_content.py",
            source="def build():\n    return {}\n",
            policy=policy,
        )


def test_policy_bound_builder_requires_transition_import_and_call():
    policy = committed_policy()
    source = 'A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"\n'
    with pytest.raises(
        governance.GovernanceValidationError,
        match="policy_bound_builder_import_missing",
    ):
        governance.validate_builder_source_binding(
            path="ulga/builders/build_e4s_a1v1_new_content.py",
            source=source,
            policy=policy,
        )

    source += (
        "from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy\n"
    )
    with pytest.raises(
        governance.GovernanceValidationError,
        match="policy_bound_builder_transition_missing",
    ):
        governance.validate_builder_source_binding(
            path="ulga/builders/build_e4s_a1v1_new_content.py",
            source=source,
            policy=policy,
        )


def test_non_content_builder_requires_explicit_exemption():
    policy = committed_policy()
    source = 'A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"\n'
    with pytest.raises(
        governance.GovernanceValidationError,
        match="builder_policy_exemption_missing",
    ):
        governance.validate_builder_source_binding(
            path="ulga/builders/build_a1_a1plus_coverage_recheck.py",
            source=source,
            policy=policy,
        )

    governance.validate_builder_source_binding(
        path="ulga/builders/build_a1_a1plus_coverage_recheck.py",
        source=(
            'A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"\n'
            'A1FS_CONTENT_POLICY_EXEMPTION = "REPORT_ONLY_NO_CONTENT_ARTIFACT_OUTPUT"\n'
        ),
        policy=policy,
    )


def test_policy_bound_builder_with_transition_call_passes():
    policy = committed_policy()
    governance.validate_builder_source_binding(
        path="ulga/builders/build_a1fs_v1_new_content.py",
        source=(
            'A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"\n'
            'from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy\n'
            'def build(payload):\n'
            '    return content_policy.build_candidate(payload=payload)\n'
        ),
        policy=policy,
    )
