from product.a1fs_v1_2_1 import a1fs_v1_core_response_mode_contract as core_contract
from product.a1fs_v1_2_1 import u04formv3c_direct_authored_form05_08_validator as target


def test_form05_08_current360_direct_authoring_core6_picture_deferred():
    report = target.validate_form05_08()
    assert report["status"] == target.STATUS
    assert report["form_count"] == 4
    assert report["task_count"] == 160
    assert report["current360_context_count"] == 24
    assert report["current360_exact_passage_count"] == 24
    assert report["form01_04_episode_reuse_count"] == 0
    assert report["form05_08_cross_form_episode_reuse_count"] == 0
    assert report["normalized_prompt_duplicate_count"] == 0
    assert set(report["core_response_mode_counts"]) == set(core_contract.CORE_RESPONSE_MODES)
    assert report["deferred_picture_task_count"] == 10
    assert report["picture_interaction_active"] is False
    assert report["blueprint_task_family_preserved"] is True
    assert report["blueprint_assessment_capability_preserved"] is True
    assert report["blueprint_quota_family_preserved"] is True
    assert report["learner_content_direct_authored"] is True

    assert [row["form_number"] for row in report["forms"]] == [5, 6, 7, 8]
    for row in report["forms"]:
        assert row["task_count"] == 40
        assert len(row["episode_ids"]) == 6
        assert len(set(row["episode_ids"])) == 6
        assert set(row["target_relation_coverage"]) == {
            "at", "behind", "between", "in", "inside", "near", "on", "under"
        }
        assert row["core_response_mode_coverage_count"] >= 5
        assert max(row["choice_position_counts"]) - min(row["choice_position_counts"]) <= 1

    scope = report["scope_safety"]
    assert scope["form01_04_learner_content_modified"] is False
    assert scope["q10_800_activity_authority_modified"] is False
    assert scope["current360_authority_modified"] is False
    assert scope["picture_interaction_activated"] is False
    assert scope["form09_plus_opened"] is False
    assert scope["a2_a2plus_unlocked"] is False
