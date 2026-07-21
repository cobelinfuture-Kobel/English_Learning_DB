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
    pipeline[pipeline.index("APPROVED_CANONICAL_JSON")], pipeline[pipeline.index("FOUR_SKILL_PROJECTION_JSON")] = (
        "FOUR_SKILL_PROJECTION_JSON",
        "APPROVED_CANONICAL_JSON",
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
