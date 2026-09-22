from __future__ import annotations

from product.a1fs_v1_2_1 import u05r360p04_pattern360_gpt56_materialization as p04


def report():
    return p04.build_report()


def test_u05_r360_p04_materializes_exact_360_pattern_entries():
    r = report()
    assert r["status"] == p04.STATUS
    assert r["entry_count"] == 360
    assert r["unique_reader_entry_count"] == 360
    assert r["unique_source_episode_count"] == 360
    assert r["family_group_count"] == 2520
    assert r["example_count"] > 4000


def test_u05_r360_p04_preserves_current360_lineage_and_family_contract():
    r = report()
    assert r["source_current360_episode_count"] == 360
    assert r["source_lineage_valid"] is True
    for index, row in enumerate(r["entries"], start=1):
        suffix = f"{index:03d}"
        assert row["reader_entry_id"] == f"U05-PATTERN360-E{suffix}"
        assert row["source_episode_id"] == f"U05-NEB-E{suffix}"
        assert set(row["families"]) == set(p04.FAMILY_NAMES)
        for family_id, family_name in p04.FAMILY_NAMES.items():
            assert row["families"][family_id]["name"] == family_name
            assert row["families"][family_id]["examples"]


def test_u05_r360_p04_uses_per_example_provenance_and_controlled_g_transfer():
    r = report()
    counts = r["evidence_mode_counts"]
    assert counts["SOURCE_GROUNDED"] > 0
    assert counts["CONTROLLED_SEMANTIC_INFERENCE"] > 0
    assert counts["CONTROLLED_TRANSFER_NOT_SOURCE_FACT"] > 0
    for row in r["entries"]:
        assert all(
            example["evidence_mode"] == "CONTROLLED_TRANSFER_NOT_SOURCE_FACT"
            for example in row["families"]["G"]["examples"]
        )


def test_u05_r360_p04_is_gpt56_authored_and_python_validation_only():
    r = report()
    assert r["learner_facing_language_author"] == "GPT-5.6 Sol"
    assert r["python_may_generate_or_rewrite_learner_facing_english"] is False
    safety = r["scope_safety"]
    assert safety["python_generated_learner_facing_examples"] is False
    assert safety["python_rewrote_learner_facing_examples"] is False


def test_u05_r360_p04_keeps_future_grammar_runtime_and_pdf_locked():
    r = report()
    safety = r["scope_safety"]
    assert safety["current360_modified"] is False
    assert safety["spoken360_modified"] is False
    assert safety["contextual_active_runtime_materialized"] is False
    assert safety["pdf_materialized"] is False
    assert safety["be_interrogative_mastery_unlocked"] is False
    assert safety["past_be_unlocked"] is False
    assert safety["existential_there_be_unlocked"] is False
    assert safety["present_continuous_mastery_unlocked"] is False
    assert safety["a2_a2plus_unlocked"] is False
    assert r["next_short_step"] == p04.NEXT_SHORT_STEP
