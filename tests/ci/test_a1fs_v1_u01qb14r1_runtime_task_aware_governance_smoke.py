from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as patch
from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_private_replay_fullfix as runner


def test_runtime_task_aware_scope_markers() -> None:
    assert patch.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert patch.A1FS_CONTENT_POLICY_EXEMPTION
    assert runner.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert runner.A1FS_CONTENT_POLICY_EXEMPTION
    assert patch.EXPECTED_RUNTIME_ITEMS == 474
