from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_private_replay_fullfix as runner


def test_runtime_task_aware_runner_scope() -> None:
    assert runner.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert runner.A1FS_CONTENT_POLICY_EXEMPTION
    assert runner.NEXT_SHORT_STEP == "A1FS-V1-U01QB14R1_ActualReal62TwelveFormAcceptanceReadback"
