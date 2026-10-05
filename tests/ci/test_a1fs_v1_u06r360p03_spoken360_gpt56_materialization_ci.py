from functools import lru_cache

from product.a1fs_v1_2_1 import u06r360p03_spoken360_gpt56_materialization as p03


@lru_cache(maxsize=1)
def report():
    return p03.build_report()


def test_u06_p03r2_materializes_exact_360_unique_dialogues():
    r = report()
    assert r["status"] == p03.STATUS
    assert r["entry_count"] == 360
    assert r["unique_reader_entry_count"] == 360
    assert r["unique_source_episode_count"] == 360
    assert r["unique_dialogue_count"] == 360


def test_u06_p03r2_requires_six_to_eight_turns_and_two_speakers():
    r = report()
    assert 6 <= r["turn_count_min"] <= r["turn_count_max"] <= 8
    assert sum(r["turn_count_distribution"].values()) == 360
    assert r["speaker_count_min"] >= 2


def test_u06_p03r2_preserves_exact_current_lineage_and_targets():
    r = report()
    assert r["source_current360_episode_count"] == 360
    assert r["source_lineage_valid"] is True
    for index, row in enumerate(r["entries"], start=1):
        suffix = f"{index:03d}"
        assert row["reader_entry_id"] == f"U06-SPOKEN360-E{suffix}"
        assert row["source_episode_id"] == f"U06-NEB-E{suffix}"
        assert row["source_episode_slot_id"] == f"U06-N360-S{suffix}"
        assert row["target_chunk_surfaces"]
        assert row["scene_family"]
        assert row["cluster_id"]
        assert row["current360_reader_shape"]
        assert 6 <= len(row["dialogue_turns"]) <= 8


def test_u06_p03r2_requires_interaction_diversity_not_current_recitation():
    r = report()
    assert r["interaction_shape_count"] >= 300
    assert r["interaction_shape_max_share"] <= 0.02
    assert r["line_by_line_recitation_risk_count"] == 0
    assert r["ket_flyers_lowered_interaction_review_pass_count"] == 360


def test_u06_p03r2_keeps_unit01_to06_grammar_and_future_scope_locked():
    r = report()
    assert r["unit01_to_unit06_grammar_ceiling"] is True
    assert r["learner_facing_language_author"] == "GPT-5.6 Sol"
    assert r["python_may_generate_or_rewrite_learner_facing_english"] is False
    assert r["gpt56_semantic_review_pass_count"] == 360
    assert r["interaction_link_review_pass_count"] == 360
    assert r["target_ability_realization_review_pass_count"] == 360
    assert all(value is False for value in r["scope_safety"].values())
    assert r["next_short_step"] == p03.NEXT_SHORT_STEP
