from product.a1fs_v1_2_1 import a1fs_v1_core_response_mode_contract as core_contract
from product.a1fs_v1_2_1 import u04formv3c_reduced_support_direct_authored_overlay_validator as target


def test_unit04_form05_08_reduced_support_direct_authored_no_picture_overlay():
    report = target.validate_form05_08()
    assert report["status"] == target.STATUS
    assert report["form_count"] == 4
    assert report["canonical_slot_count"] == 160
    assert report["active_no_picture_task_count"] == 150
    assert report["deferred_picture_task_count"] == 10
    assert set(report["core_response_modes"]) == set(core_contract.CORE_RESPONSE_MODES)
    assert set(report["core_response_mode_counts"]) == set(core_contract.CORE_RESPONSE_MODES)
    assert report["unique_active_prompt_count"] == 150
    assert report["support_relations_assessed"] is False
    assert report["learner_content_author"] == "GPT-5.6_SOL_DIRECT_AUTHORING"
    assert report["python_learner_authoring_used"] is False
    assert report["picture_interaction_active"] is False
    assert report["listening_modified"] is False
    assert report["a2_a2plus_unlocked"] is False
    expected = {
        5: (38, 2),
        6: (38, 2),
        7: (37, 3),
        8: (37, 3),
    }
    assert [row["form_number"] for row in report["forms"]] == [5, 6, 7, 8]
    for row in report["forms"]:
        active, deferred = expected[row["form_number"]]
        assert row["active_task_count"] == active
        assert row["deferred_picture_task_count"] == deferred
        assert set(row["core_response_mode_counts"]) == set(core_contract.CORE_RESPONSE_MODES)
