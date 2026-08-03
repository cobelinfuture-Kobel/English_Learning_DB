from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as patch


def test_runtime_task_aware_patch_does_not_expand_scope() -> None:
    assert patch.EXPECTED_RUNTIME_ITEMS == 474
    assert patch.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
