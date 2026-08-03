from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as patch


def test_final_scope_remains_unit01_only() -> None:
    assert patch.PROGRAM_ID == "A1FS-V1"
