from ulga.validators import validate_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as validator


def test_runtime_task_aware_validator_identity() -> None:
    assert validator.A1FS_CONTENT_POLICY_MODE == "POLICY_ENFORCER"
    assert validator.PASS_STATUS.startswith("PASS_A1FS_V1_U01QB14R1_")
