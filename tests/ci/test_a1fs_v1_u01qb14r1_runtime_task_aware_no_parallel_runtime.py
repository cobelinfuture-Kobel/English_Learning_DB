from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_private_replay_fullfix as runner


def test_runner_is_orchestrator_not_parallel_runtime() -> None:
    assert "no second planner" in runner.__doc__.casefold()
    assert "no second runtime" in runner.A1FS_CONTENT_POLICY_EXEMPTION.casefold()
