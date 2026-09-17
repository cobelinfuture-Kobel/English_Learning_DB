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
    assert summary["communicative_function_count"] == 12
    assert summary["dialogue_skeleton_count"] == 5
    assert summary["production_ladder_count"] == 2
    assert summary["episodes_with_functional_routes"] == 360
    assert summary["episodes_with_q05_frame_routes"] == 360
    assert summary["episodes_with_dialogue_routes"] == 360
    assert summary["episodes_with_personal_transfer"] == 360
    assert summary["episodes_with_ket_seed_routes"] == 360
    assert summary["current360_passage_rewrite_count"] == 0
    assert summary["python_composed_learner_english_count"] == 0

    rows = report["episode_productive_routes"]
    assert len(rows) == 360
    assert len({row["episode_id"] for row in rows}) == 360
    assert all(row["functional_chunk_refs"] for row in rows)
    assert all(row["q05_sentence_frame_routes"] for row in rows)
    assert all(row["dialogue_skeleton_refs"] for row in rows)
    assert all("U04-FL-PERSONAL-01" in row["functional_chunk_refs"] for row in rows)
    assert all("U04-FL-PERSONAL-02" in row["functional_chunk_refs"] for row in rows)
    assert all(row["ket_seed_routes"] == list(fl.KET_SEED_ROUTES) for row in rows)
    assert all(row["language_generation_policy"]["current360_passage_rewritten"] is False for row in rows)
    assert all(row["language_generation_policy"]["python_composed_learner_english"] is False for row in rows)

    assert report["scope_safety"] == {
        "q03_modified": False,
        "q04_spatial_chunks_modified": False,
        "q05_modified": False,
        "q06_modified": False,
        "q07_modified": False,
        "current360_passages_modified": False,
        "form01_20_modified": False,
        "unit05_plus_opened": False,
        "a2_a2plus_unlocked": False,
    }
