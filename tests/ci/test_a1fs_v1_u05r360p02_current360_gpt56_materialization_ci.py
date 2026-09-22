from __future__ import annotations

from collections import Counter

from product.a1fs_v1_2_1 import u05r360p02_current360_gpt56_materialization as p02


def report():
    return p02.build_report()


def test_u05_r360_p02_materializes_exact_360_gpt56_authored_paragraphs():
    r = report()
    assert r["status"] == p02.STATUS
    assert r["episode_count"] == 360
    assert r["unique_paragraph_count"] == 360
    assert r["gpt56_semantic_review_pass_count"] == 360
    assert r["learner_facing_language_author"] == "GPT-5.6 Sol"
    assert r["python_may_generate_or_rewrite_learner_facing_english"] is False


def test_u05_r360_p02_preserves_exact_p01_slot_cluster_and_discourse_identity():
    r = report()
    rows = r["episodes"]
    assert len({row["episode_id"] for row in rows}) == 360
    assert len({row["episode_slot_id"] for row in rows}) == 360
    assert Counter(row["cluster_id"] for row in rows) == {
        f"U05-N360-C{index:02d}": 10 for index in range(1, 37)
    }
    for index, row in enumerate(rows, start=1):
        assert row["episode_id"] == f"U05-NEB-E{index:03d}"
        assert row["episode_slot_id"] == f"U05-N360-S{index:03d}"
        assert row["discourse_family"] == p02.DISCOURSE_FAMILIES[(index - 1) % 10]
        assert row["source_scene_refs"]


def test_u05_r360_p02_uses_natural_paragraph_length_and_valid_q07_lineage():
    r = report()
    assert r["sentence_count_min"] >= 5
    assert r["sentence_count_max"] <= 8
    assert r["source_scene_lineage_valid"] is True
    for row in r["episodes"]:
        assert len(row["paragraph"].strip()) > 0
        assert row["author_model"] == "GPT-5.6 Sol"
        assert row["gpt56_semantic_review"] == "PASS"


def test_u05_r360_p02_keeps_python_non_authoring_and_future_grammar_locked():
    r = report()
    safety = r["scope_safety"]
    assert safety["python_generated_learner_facing_english"] is False
    assert safety["python_rewrote_learner_facing_english"] is False
    assert safety["be_interrogative_mastery_unlocked"] is False
    assert safety["past_be_unlocked"] is False
    assert safety["existential_there_be_unlocked"] is False
    assert safety["present_continuous_mastery_unlocked"] is False
    assert safety["a2_a2plus_unlocked"] is False


def test_u05_r360_p02_does_not_claim_spoken_pattern_runtime_or_pdf_cutover():
    r = report()
    safety = r["scope_safety"]
    assert safety["spoken360_materialized"] is False
    assert safety["pattern360_materialized"] is False
    assert safety["contextual_active_runtime_materialized"] is False
    assert safety["pdf_materialized"] is False
    assert r["next_short_step"] == p02.NEXT_SHORT_STEP
