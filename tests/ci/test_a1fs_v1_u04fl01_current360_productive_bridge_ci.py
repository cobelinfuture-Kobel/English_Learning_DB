from product.a1fs_v1_2_1 import u04fl01_current360_productive_bridge as fl


def test_unit04_functional_language_core_and_current360_productive_bridge():
    report = fl.build_unit04_current360_productive_bridge()

    assert report["status"] == fl.STATUS
    assert report["unit_number"] == 4
    assert report["goal_chain"] == [
        "WORD_RECOGNITION",
        "SPATIAL_CHUNK_RETRIEVAL",
        "SENTENCE_BUILDING",
        "NATURAL_SPOKEN_INTERACTION",
        "KET_STYLE_TRANSFER_WITHOUT_A2_GRAMMAR_UNLOCK",
    ]

    summary = report["summary"]
    assert summary["episode_count"] == 360
    assert summary["functional_chunk_authority_count"] == 24
    assert summary["communicative_function_count"] == 6
    assert summary["q08_communicative_function_authority_count"] == 6
    assert summary["functional_move_count"] == 12
    assert summary["dialogue_skeleton_count"] == 5
    assert summary["production_ladder_count"] == 2
    assert summary["episodes_with_q05_frame_routes"] == 360
    assert summary["episodes_pending_gpt5_6_functional_selection"] == 360
    assert summary["minimum_selected_functional_chunks_per_episode"] == 0
    assert summary["episodes_with_selected_q08_functions"] == 0
    assert summary["episodes_with_selected_functional_chunks"] == 0
    assert summary["episodes_with_selected_dialogue_skeletons"] == 0
    assert summary["episodes_with_selected_production_ladders"] == 0
    assert summary["episodes_with_selected_ket_seed_routes"] == 0
    assert summary["episode_specific_functional_selection_count"] == 0
    assert summary["episode_specific_instantiated_dialogue_count"] == 0
    assert summary["current360_passage_rewrite_count"] == 0
    assert summary["python_composed_learner_english_count"] == 0
    assert summary["python_selected_functional_language_count"] == 0

    rows = report["episode_productive_routes"]
    assert len(rows) == 360
    assert len({row["episode_id"] for row in rows}) == 360
    assert all(row["q05_sentence_frame_routes"] for row in rows)
    assert all(row["q08_communicative_function_refs"] == [] for row in rows)
    assert all(row["functional_chunk_refs"] == [] for row in rows)
    assert all(row["dialogue_skeleton_refs"] == [] for row in rows)
    assert all(row["production_ladder_refs"] == [] for row in rows)
    assert all(row["ket_seed_routes"] == [] for row in rows)
    assert all(len(row["q08_communicative_function_candidate_pool"]) == 6 for row in rows)
    assert all(len(row["functional_chunk_candidate_pool"]) == 24 for row in rows)
    assert all(len(row["dialogue_skeleton_candidate_pool"]) == 5 for row in rows)
    assert all(len(row["production_ladder_candidate_pool"]) == 2 for row in rows)
    assert all(len(row["ket_seed_candidate_routes"]) == 3 for row in rows)
    assert all(row["functional_selection_status"] == "PENDING_GPT5_6_EPISODE_SEMANTIC_REVIEW" for row in rows)
    assert all(row["functional_selection_contract"]["minimum_selected_functional_chunks"] == 0 for row in rows)
    assert all(row["functional_selection_contract"]["fixed_quota"] is False for row in rows)
    assert all(row["functional_selection_contract"]["no_selection_is_valid"] is True for row in rows)
    assert all(row["functional_selection_contract"]["relation_label_must_not_trigger_automatic_insertion"] is True for row in rows)
    assert all(row["language_generation_policy"]["current360_passage_rewritten"] is False for row in rows)
    assert all(row["language_generation_policy"]["python_composed_learner_english"] is False for row in rows)
    assert all(row["language_generation_policy"]["python_selected_functional_language"] is False for row in rows)
    assert all(row["language_generation_policy"]["episode_specific_functional_selection_materialized"] is False for row in rows)
    assert all(row["language_generation_policy"]["episode_specific_instantiated_dialogue_materialized"] is False for row in rows)

    assert report["functional_language_core"]["selection_authority"] == "GPT5_6_EPISODE_SEMANTIC_REVIEW"
    assert report["scope_safety"] == {
        "q03_modified": False,
        "q04_spatial_chunks_modified": False,
        "q05_modified": False,
        "q06_modified": False,
        "q07_modified": False,
        "q08_semantic_authority_modified": False,
        "parallel_communicative_function_authority_created": False,
        "current360_passages_modified": False,
        "functional_chunks_forced_into_current360": False,
        "form01_20_modified": False,
        "unit05_plus_opened": False,
        "a2_a2plus_unlocked": False,
    }
