from product.a1fs_v1_2_1 import a1fs_v1_core_response_mode_contract as core_contract
from product.a1fs_v1_2_1 import u04formv3c_core_response_mode_projection_validator as target


def test_core_six_response_mode_contract_unit01_to_unit24():
    report = core_contract.validate_contract()
    assert report["status"] == core_contract.STATUS
    assert report["unit_scope"] == list(range(1, 25))
    assert report["core_response_mode_count"] == 6
    assert report["core_response_modes"] == [
        "SELECT",
        "MATCH",
        "TEXT_ENTRY",
        "STRUCTURED_ENTRY",
        "ORDER",
        "SPEAK",
    ]
    assert report["picture_interaction_active"] is False
    assert report["task_family_separate"] is True
    assert report["assessment_capability_separate"] is True
    assert report["response_format_separate"] is True


def test_unit04_form01_08_projects_to_six_core_response_modes_with_core_native_form05_08():
    report = target.validate_form01_08_core_projection()
    assert report["status"] == target.STATUS
    assert report["form_count"] == 8
    assert report["task_count"] == 320
    assert report["core_native_task_count"] == 160
    assert report["core_native_form_numbers"] == [5, 6, 7, 8]
    assert report["core_response_mode_count"] == 6
    assert set(report["core_response_mode_counts"]) == set(core_contract.CORE_RESPONSE_MODES)
    assert report["deferred_picture_task_count"] == 10
    assert report["picture_interaction_active"] is False
    assert report["learner_content_changed_by_projection"] is False
    assert report["task_family_changed_by_projection"] is False
    assert report["assessment_capability_changed_by_projection"] is False

    assert [row["form_number"] for row in report["forms"]] == list(range(1, 9))
    for row in report["forms"]:
        assert row["non_picture_task_count"] + row["deferred_picture_task_count"] == 40
        assert row["core_response_mode_coverage_count"] >= 5
    for row in report["forms"][:4]:
        assert row["deferred_picture_task_count"] == 0
        assert row["non_picture_task_count"] == 40
    for row in report["forms"][4:]:
        assert row["core_native_response_mode_schema"] is True
