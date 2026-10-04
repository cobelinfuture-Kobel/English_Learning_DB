from functools import lru_cache

from product.a1fs_v1_2_1 import u06r360p02_current360_gpt56_materialization as p02

@lru_cache(maxsize=1)
def report():
    return p02.build_report()

def test_u06_p02_full360_exact_unique_and_gpt56_reviewed():
    r=report()
    assert r["status"]==p02.STATUS
    assert r["episode_count"]==360
    assert r["unique_paragraph_count"]==360
    assert r["learner_facing_language_author"]=="GPT-5.6 Sol"
    assert r["python_may_generate_or_rewrite_learner_facing_english"] is False
    assert r["pilot_human_review_status"]=="APPROVED_BY_OPERATOR"

def test_u06_p02_natural_variable_length_is_not_fixed_five_sentences():
    r=report()
    assert r["sentence_count_min"]==4
    assert r["sentence_count_max"]==6
    assert set(r["sentence_count_distribution"])=={4,5,6}
    assert r["sentence_count_distribution"][4]>0
    assert r["sentence_count_distribution"][6]>0
    assert r["clusters_with_4_5_6_sentence_variety"]==13
    assert r["source_cluster_count"]==13
    assert r["dominant_sentence_count_share"]<=0.65
    assert r["maximum_allowed_single_sentence_count_share"]==0.65
    assert r["final_natural_length_distribution_decision"]=="ACCEPT_VARIABLE_4_TO_6_WITHOUT_FIXED_FIVE_SENTENCE_TEMPLATE"

def test_u06_p02_scene_first_support_and_no_chunk_stuffing_contract():
    r=report()
    assert r["scene_first_support"] is True
    assert r["chunk_stuffing_forbidden"] is True
    assert r["per_episode_preassigned_chunk_surface_realization_required"] is False
    assert r["functional_chunk_realization_coverage"]=="182/182"

def test_u06_p02_preserves_scene_diversity_growth_and_all_scene_families():
    r=report()
    assert r["scene_diversity_reservoir_count"]>r["predecessor_scene_diversity_count"]
    assert r["scene_diversity_growth_over_predecessor"]>=24
    assert r["scene_family_count"]==12
    assert all(v>0 for v in r["scene_family_episode_counts"].values())

def test_u06_p02_keeps_future_scope_closed():
    r=report()
    assert all(value is False for value in r["scope_safety"].values())
    assert r["next_short_step"]==p02.NEXT_SHORT_STEP

def test_u06_p02_episode_targets_are_naturalized_and_visible():
    r=report()
    for row in r["episodes"]:
        assert 1<=len(row["target_chunk_surfaces"])<=2
        paragraph=row["paragraph"].casefold()
        assert all(chunk.casefold() in paragraph for chunk in row["target_chunk_surfaces"])
        assert row["gpt56_semantic_review"]=="PASS"
        assert row["natural_style_review"]=="PASS"
        assert row["gpt56_length_style_review"].startswith("PASS_")
