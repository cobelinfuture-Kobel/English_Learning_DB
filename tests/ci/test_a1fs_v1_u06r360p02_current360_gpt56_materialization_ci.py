from functools import lru_cache

from product.a1fs_v1_2_1 import u06r360p02_current360_gpt56_materialization as p02


@lru_cache(maxsize=1)
def report():
    return p02.build_report()


def test_u06_p02r2_full360_exact_unique_and_gpt56_reviewed():
    r = report()
    assert r["status"] == p02.STATUS
    assert r["episode_count"] == 360
    assert r["unique_paragraph_count"] == 360
    assert r["learner_facing_language_author"] == "GPT-5.6 Sol"
    assert r["python_may_generate_or_rewrite_learner_facing_english"] is False


def test_u06_p02r2_requires_six_to_eight_sentences():
    r = report()
    assert 6 <= r["sentence_count_min"] <= r["sentence_count_max"] <= 8
    assert sum(r["sentence_count_distribution"].values()) == 360
    assert set(r["sentence_count_distribution"]) <= {6, 7, 8}


def test_u06_p02r2_preserves_unit01_to06_grammar_and_target_authority():
    r = report()
    assert r["unit01_to_unit06_grammar_ceiling"] is True
    assert r["functional_chunk_realization_coverage"] == "182/182"
    assert r["scene_family_count"] == 12
    assert all(v > 0 for v in r["scene_family_episode_counts"].values())
    for row in r["episodes"]:
        assert 1 <= len(row["target_chunk_surfaces"]) <= 2
        paragraph = row["paragraph"].casefold()
        assert all(chunk.casefold() in paragraph for chunk in row["target_chunk_surfaces"])
        assert row["gpt56_semantic_review"] == "PASS"
        assert row["natural_style_review"] == "PASS"
        assert row["ket_flyers_lowered_shape_review"] == "PASS"


def test_u06_p02r2_requires_ket_flyers_lowered_text_shape_diversity():
    r = report()
    assert r["ket_flyers_lowered_text_shape_policy"] is True
    assert r["reader_shape_count"] >= 250
    assert r["reader_shape_max_share"] <= 0.05


def test_u06_p02r2_preserves_scene_diversity_and_future_scope_lock():
    r = report()
    assert r["scene_diversity_reservoir_count"] > r["predecessor_scene_diversity_count"]
    assert r["scene_diversity_growth_over_predecessor"] >= 24
    assert all(value is False for value in r["scope_safety"].values())
    assert r["next_short_step"] == p02.NEXT_SHORT_STEP
