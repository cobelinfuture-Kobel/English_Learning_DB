from __future__ import annotations

from product.a1fs_v1_2_1 import u06r360p03_spoken360_gpt56_materialization as p03


def report():
    return p03.build_report()


def test_u06_r360_p03_materializes_exact_360_spoken_dialogues():
    r = report()
    assert r["status"] == p03.STATUS
    assert r["entry_count"] == 360
    assert r["unique_reader_entry_count"] == 360
    assert r["unique_source_episode_count"] == 360
    assert r["unique_dialogue_count"] == 360


def test_u06_r360_p03_is_gpt56_authored_and_interaction_reviewed():
    r = report()
    assert r["learner_facing_language_author"] == "GPT-5.6 Sol"
    assert r["python_may_generate_or_rewrite_learner_facing_english"] is False
    assert r["gpt56_semantic_review_pass_count"] == 360
    assert r["interaction_link_review_pass_count"] == 360
    assert r["target_ability_realization_review_pass_count"] == 360
    assert r["speaker_count_min"] >= 2
    assert 5 <= r["turn_count_min"] <= r["turn_count_max"] <= 7


def test_u06_r360_p03_preserves_current360_identity_target_and_scene_lineage():
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
        assert row["interaction_trigger"]
        assert 5 <= len(row["dialogue_turns"]) <= 7


def test_u06_r360_p03_keeps_affirmative_ability_and_future_grammar_locked():
    r = report()
    safety = r["scope_safety"]
    assert safety["q01_q10_modified"] is False
    assert safety["current360_modified"] is False
    assert safety["python_generated_learner_facing_dialogue"] is False
    assert safety["python_rewrote_learner_facing_dialogue"] is False
    assert safety["can_interrogative_mastery_unlocked"] is False
    assert safety["can_negative_mastery_unlocked"] is False
    assert safety["permission_request_offer_possibility_can_unlocked"] is False
    assert safety["present_continuous_mastery_unlocked"] is False
    assert safety["a2_a2plus_unlocked"] is False


def test_u06_r360_p03_does_not_claim_pattern_far_or_pdf():
    r = report()
    safety = r["scope_safety"]
    assert safety["pattern360_materialized"] is False
    assert safety["far_materialized"] is False
    assert safety["pdf_materialized"] is False
    assert r["next_short_step"] == p03.NEXT_SHORT_STEP
