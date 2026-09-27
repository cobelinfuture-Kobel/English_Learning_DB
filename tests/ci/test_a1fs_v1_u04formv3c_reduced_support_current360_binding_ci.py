from product.a1fs_v1_2_1 import u04formv3c_reduced_support_current360_binding_validator as target


def test_unit04_form05_08_reduced_support_current360_binding():
    report = target.validate_binding()
    assert report["status"] == target.STATUS
    assert report["form_count"] == 4
    assert report["context_count"] == 24
    assert report["unique_episode_count"] == 24
    assert report["guided_overlap_count"] == 0
    assert report["current360_passages_exact"] is True
    assert report["all_forms_cover_all_target_relations"] is True
    assert report["source_sentence_count_preference_pass"] is True
    assert report["picture_interaction_active"] is False
    assert report["listening_modified"] is False
    assert report["a2_a2plus_unlocked"] is False
    assert [row["form_number"] for row in report["forms"]] == [5, 6, 7, 8]
    for row in report["forms"]:
        assert len(row["episode_ids"]) == 6
        assert len(set(row["episode_ids"])) == 6
        assert set(row["target_relation_coverage"]) == {"at", "behind", "between", "in", "inside", "near", "on", "under"}
        assert set(row["sentence_count_distribution"]).issubset({3, 4})
