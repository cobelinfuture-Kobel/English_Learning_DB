from product.a1fs_v1_2_1 import u04formv3_direct_authoring_contract as contract
from product.a1fs_v1_2_1 import u04formv3a_direct_authored_form01_04_validator as target


def test_u04_formv3a_direct_authored_form01_04_mechanical_validation():
    report = target.build_unit04_formv3a_validation()

    assert report["status"] == target.STATUS
    assert report["source_authority"]["formv3_contract"] == contract.TASK_ID
    assert report["form_count"] == 4
    assert report["question_count"] == 160
    assert report["distinct_current360_episode_count"] == 24
    assert report["cross_form_episode_reuse_count"] == 0
    assert report["exact_prompt_duplicate_count"] == 0
    assert report["python_learner_content_authoring_used"] is False
    assert report["legacy_python_task_builder_used"] is False
    assert report["current360_passage_mutation_used"] is False
    assert report["next_short_step"] == target.NEXT_SHORT_STEP

    assert report["answer_diversity"] == {
        "identical_select_answer_sequence_across_forms": False,
        "identical_family_sequence_across_forms": False,
        "fixed_select_position_across_all_four_forms": False,
        "python_post_authoring_shuffle_used": False,
    }
    assert report["activation"] == {
        "formv3_pilot_active_runtime": False,
        "legacy_fsv2_remains_active": True,
        "parallel_form_runtime_created": False,
    }
    assert report["scope_safety"] == {
        "current360_modified": False,
        "listening_modified": False,
        "a2_a2plus_unlocked": False,
    }

    expected_families = contract.STAGE_FAMILY_QUOTAS["GUIDED"]
    for form in report["forms"]:
        assert form["stage"] == "GUIDED"
        assert form["context_count"] == 6
        assert form["question_count"] == 40
        assert form["section_counts"] == contract.SECTION_COUNTS
        assert form["select_one_count"] == 10
        assert form["correct_option_position_max_delta"] <= 1
        assert set(form["target_relation_coverage"]) == set(contract.TARGET_RELATIONS)
        for section in contract.SECTION_ORDER:
            assert form["family_counts"][section] == expected_families[section]
