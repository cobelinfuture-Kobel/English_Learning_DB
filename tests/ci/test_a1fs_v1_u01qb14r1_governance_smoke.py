from ulga.builders import build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as builder


def test_u01qb14r1_scope_and_policy_markers() -> None:
    assert builder.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert builder.A1FS_CONTENT_POLICY_EXEMPTION
    assert builder.EXPECTED_CUMULATIVE_SCENE_WORLD_COUNT == 32
    assert builder.EXPECTED_UNIT01_BINDABLE_SCENE_COUNT == 31
    assert builder.EXPECTED_DEFERRED_SCENE_REFS == ("U01-MA-FOOD-04",)
