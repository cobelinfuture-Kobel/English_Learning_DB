from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_handoff as builder,
)
from ulga.validators import (
    validate_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_handoff as validator,
)


def test_razq01d_ci_contract_constants_and_boundaries():
    assert builder.A1FS_CONTENT_POLICY_MODE == "POLICY_BOUND"
    assert validator.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert builder.TARGET_BANK_ID == "A1FS_V1_UNIT01_APPROVED_VARIANT_POOL"
    assert builder.CONTENT_KINDS == {
        "MICRO_SCENE",
        "SHORT_PASSAGE",
        "SHORT_DIALOGUE",
    }
    assert builder.NEXT_SHORT_STEP == (
        "A1FS-V1-RAZQ01D-OPS_RealPrivateCandidateAndReviewDecisionMaterialization"
    )
