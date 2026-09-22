from __future__ import annotations

from product.a1fs_v1_2_1 import u05r360p03_spoken360_gpt56_materialization as p03


def report():
    return p03.build_report()


def test_u05_r360_p03_materializes_exact_360_spoken_dialogues():
    r = report()
    assert r["status"] == p03.STATUS
    assert r["entry_count"] == 360
    assert r["unique_reader_entry_count"] == 360
    assert r["unique_source_episode_count"] == 360
    assert r["unique_dialogue_count"] == 360


def test_u05_r360_p03_is_gpt56_authored_and_interaction_reviewed():
    r = report()
    assert r["learner_facing_language_author"] == "GPT-5.6 Sol"
    assert r["python_may_generate_or_rewrite_learner_facing_english"] is False
    assert r["gpt56_semantic_review_pass_count"] == 360
    assert r["interaction_link_review_pass_count"] == 360
    assert r["speaker_count_min"] >= 2
    assert 5 <= r["turn_count_min"] <= r["turn_count_max"] <= 8


def test_u05_r360_p03_preserves_current360_lineage():
    r = report()
    assert r["source_current360_episode_count"] == 360
    assert r["source_lineage_valid"] is True
    for index, row in enumerate(r["entries"], start=1):
        suffix = f"{index:03d}"
        assert row["reader_entry_id"] == f"U05-SPOKEN360-E{suffix}"
        assert row["source_episode_id"] == f"U05-NEB-E{suffix}"
        assert row["source_scene_refs"]
        assert row["interaction_trigger"]
        assert len(row["dialogue_turns"]) >= 5


def test_u05_r360_p03_keeps_current360_and_future_grammar_locked():
    r = report()
    safety = r["scope_safety"]
    assert safety["current360_modified"] is False
    assert safety["python_generated_learner_facing_dialogue"] is False
    assert safety["python_rewrote_learner_facing_dialogue"] is False
    assert safety["be_interrogative_mastery_unlocked"] is False
    assert safety["past_be_unlocked"] is False
    assert safety["existential_there_be_unlocked"] is False
    assert safety["present_continuous_mastery_unlocked"] is False
    assert safety["a2_a2plus_unlocked"] is False


def test_u05_r360_p03_does_not_claim_pattern_runtime_or_pdf_cutover():
    r = report()
    safety = r["scope_safety"]
    assert safety["pattern360_materialized"] is False
    assert safety["contextual_active_runtime_materialized"] is False
    assert safety["pdf_materialized"] is False
    assert r["next_short_step"] == p03.NEXT_SHORT_STEP
