from __future__ import annotations

from pathlib import Path

from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as m2


def _by_id(report):
    return {row["episode_id"]: row for row in report["effective_episodes"]}


def test_u04neb02_materializes_exact_current360_and_preserves_balanced_scene_domain_scope() -> None:
    report = m2.build_unit04_neb02_natural_episode_bank_360()
    assert report["status"] == m2.STATUS
    assert report["revision"] == "GPT5_6_SOL_M2_CURRENT360_OPERATOR_REPAIRED_V1"

    summary = report["summary"]
    assert summary["episode_count"] == 360
    assert summary["micro_scene_count"] == 36
    assert summary["episodes_per_micro_scene"] == 10
    assert summary["life_domain_count"] == 12
    assert summary["episodes_per_life_domain"] == 30
    assert summary["exact_duplicate_count"] == 0
    assert summary["normalized_duplicate_count"] == 0
    assert summary["blocked_pattern_count"] == 0
    assert set(summary["target_relation_distribution"]) == set(m2.TARGET_RELATIONS)


def test_u04neb02_freezes_the_operator_approved_43_existing_episode_repairs() -> None:
    report = m2.build_unit04_neb02_natural_episode_bank_360()
    episodes = _by_id(report)
    assert report["authority_contract"]["operator_approved_repair_count"] == 43
    assert set(report["authority_contract"]["operator_approved_repair_ids"]) == set(m2.OPERATOR_APPROVED_REPAIR_IDS)

    for episode_id in m2.OPERATOR_APPROVED_REPAIR_IDS:
        assert episodes[episode_id]["review_status"] == "PASS_GPT5_6_SOL_M2_OPERATOR_APPROVED_REPAIR"

    assert episodes["U04-NEB-E160"]["passage"] == (
        "Lily and her brother wait in front of the school. Their bags are near their feet, "
        "so both children can reach them. The bus is behind them."
    )
    assert episodes["U04-NEB-E335"]["passage"] == (
        "The children want to see the chickens. The chickens are between the barn and the fence, "
        "and the tractor is behind the barn. Ben points to the chickens."
    )
    assert episodes["U04-NEB-E358"]["passage"] == (
        "Olivia gets ready for bed. Her slippers are under the bed, and the night light is near the bed. "
        "Her school clothes are on the chair. She gets the slippers."
    )


def test_u04neb02_semantic_diversity_is_controlled_not_fake_cross_scene_duplication() -> None:
    report = m2.build_unit04_neb02_natural_episode_bank_360()
    summary = report["summary"]

    # Lexical similarity inside one source micro-scene is expected because source facts
    # are deliberately shared. Cross-scene high-similarity is the fail-closed signal.
    assert summary["tfidf_similarity_threshold"] == 0.80
    assert summary["tfidf_cross_scene_near_pair_count"] == 0
    assert summary["tfidf_near_pairs_are_same_scene_only"] is True
    assert all(value == 10 for value in summary["per_scene_raw_discourse_family_count"].values())

    five_w_one_h = summary["five_w_one_h_distribution"]
    assert five_w_one_h.get("WHO", 0) > 0
    assert five_w_one_h.get("WHAT", 0) > 0
    assert five_w_one_h.get("WHERE", 0) > 0
    assert five_w_one_h.get("WHEN", 0) > 0
    assert five_w_one_h.get("WHY", 0) > 0
    assert five_w_one_h.get("HOW", 0) > 0


def test_u04neb02_preserves_authorities_and_does_not_open_later_scope() -> None:
    report = m2.build_unit04_neb02_natural_episode_bank_360()
    assert report["scope_safety"] == {
        "q03_relation_authority_modified": False,
        "q07_semantic_authority_modified": False,
        "q10_form01_20_modified": False,
        "q10_800_activities_modified": False,
        "canonical_grammar_modified": False,
        "canonical_vocabulary_modified": False,
        "canonical_chunk_modified": False,
        "unit05_plus_opened": False,
        "a2_a2plus_unlocked": False,
        "listening_materialized": False,
        "additional_episode_generation_performed": False,
    }


def test_u04neb02_is_static_gpt_authored_content_not_python_language_composition() -> None:
    source = Path(m2.__file__).read_text(encoding="utf-8")
    assert 'def _compose' not in source
    assert 'def _natural_passage' not in source
    report = m2.build_unit04_neb02_natural_episode_bank_360()
    assert report["authority_contract"]["gpt_authored_learner_language"] is True
    assert report["authority_contract"]["python_sentence_composer_used"] is False
    assert report["authority_contract"]["extension_sha256"] == m2.EXPECTED_EXTENSION_SHA256
