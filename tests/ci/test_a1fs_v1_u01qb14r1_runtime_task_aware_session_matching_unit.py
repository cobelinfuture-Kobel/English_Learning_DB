from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as patch


def test_distinct_item_matching_detects_collisions() -> None:
    assert patch._perfect_matching_exists([("a",), ("b",)]) is True
    assert patch._perfect_matching_exists([("a", "b"), ("b",)]) is True
    assert patch._perfect_matching_exists([("a",), ("a",)]) is False
