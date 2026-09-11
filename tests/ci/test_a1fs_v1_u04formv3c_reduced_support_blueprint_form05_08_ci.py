from collections import Counter

from product.a1fs_v1_2_1 import u04formv3_direct_authoring_contract as contract
from product.a1fs_v1_2_1 import u04formv3c_reduced_support_blueprint_form05_08_validator as target


def test_u04_formv3c_reduced_support_blueprint_form05_08():
    report = target.validate_blueprint_form05_08()

    assert report["status"] == target.STATUS
    assert report["stage"] == "REDUCED_SUPPORT"
    assert report["support_level"] == "MEDIUM"
    assert report["form_count"] == 4
    assert report["task_count"] == 160
    assert report["response_mode_coverage_count"] == 22
    assert report["fixed_response_mode_slot_count"] == 0
    assert report["max_pairwise_same_slot_mode_ratio"] <= 0.25
    assert report["python_blueprint_generation_used"] is False
    assert report["python_response_mode_assignment_used"] is False
    assert report["python_task_family_assignment_used"] is False
    assert report["python_learner_content_authoring_used"] is False
    assert report["legacy_python_task_builder_used"] is False
    assert report["a2_a2plus_unlocked"] is False
    assert report["listening_modified"] is False

    assert [row["form_number"] for row in report["forms"]] == [5, 6, 7, 8]
    for row in report["forms"]:
        assert row["distinct_response_mode_count"] >= 20
        assert row["distinct_task_family_count"] >= 21
        assert row["distinct_capability_count"] >= 20
        assert row["response_field_count"] > 40
        assert row["picture_task_count"] >= 2


def test_u04_formv3c_reduced_support_quota_families_match_production_contract():
    for form_number in target.EXPECTED_FORMS:
        payload = target._load_form(None, form_number)
        tasks = payload["form"]["tasks"]
        for section in contract.SECTION_ORDER:
            actual = Counter(task["quota_family"] for task in tasks if task["section"] == section)
            assert dict(actual) == contract.STAGE_FAMILY_QUOTAS["REDUCED_SUPPORT"][section]
