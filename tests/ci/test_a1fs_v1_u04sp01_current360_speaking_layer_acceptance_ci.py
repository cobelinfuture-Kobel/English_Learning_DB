from __future__ import annotations

from product.a1fs_v1_2_1 import u04sp01_current360_speaking_layer_acceptance as sp01


REPORT = sp01.build_unit04_current360_speaking_layer_acceptance()


def test_unit04_sp01_materializes_atomic_layer1_with_all_target_relations() -> None:
    assert REPORT["status"] == sp01.STATUS
    layer1 = REPORT["layer1_acceptance"]
    assert layer1["atomic_sentence_count"] == 121
    assert layer1["target_atomic_sentence_count"] == 89
    assert layer1["support_atomic_sentence_count"] == 32
    assert layer1["exact_unique_sentence_count"] == 121
    assert layer1["exact_duplicate_occurrences"] == 0
    assert layer1["source_lineage_validity"] == "PASS"
    assert layer1["grammar_target_form_coverage"] == "8/8"
    assert layer1["target_relation_distribution"] == sp01.EXPECTED_TARGET_DISTRIBUTION
    assert layer1["support_relation_distribution"] == sp01.EXPECTED_SUPPORT_DISTRIBUTION
    assert layer1["reference_mode_counts"]["TEXT_BOUND_POINT_PLACE"] == 6


def test_unit04_sp01_layer2_uses_current360_and_preserves_dual_lineage() -> None:
    rows = REPORT["layer2_connected_speaking"]
    assert len(rows) == 36
    assert all(row["response_authority"] == sp01.CURRENT360_AUTHORITY for row in rows)
    assert all(len(row["model_utterances"]) >= 2 for row in rows)
    assert all(row["current360_episode_lineage"]["passage"] for row in rows)
    assert all(row["q07_m2a_fact_lineage"]["unit04_sentence_ids"] for row in rows)
    assert all(row["shared_visible_relation_surfaces"] for row in rows)
    assert all(row["atomic_relation_lineage"] for row in rows)
    assert all(row["lineage_alignment"]["family_equivalence_claimed"] is False for row in rows)


def test_unit04_sp01_layer2_required_metrics_and_zero_anomaly_gate() -> None:
    layer2 = REPORT["layer2_acceptance"]
    assert layer2["connected_set_count"] == 36
    assert layer2["utterance_count"] >= 72
    assert layer2["distinct_lexical_payload_word_forms"] > 0
    assert 0.0 <= layer2["top1_lexical_payload_share"] <= 1.0
    assert 0.0 <= layer2["top10_lexical_payload_concentration"] <= 1.0
    assert 0.0 <= layer2["top20_lexical_payload_concentration"] <= 1.0
    assert layer2["selected_distinct_np_surfaces"] > 0
    assert layer2["scene_coverage"]["task_projection_count"] == 36
    assert layer2["predicate_distribution"]
    assert layer2["semantic_anomaly_zero_counts"] == {
        "missing_dual_lineage_count": 0,
        "missing_atomic_relation_lineage_count": 0,
        "incomplete_connected_set_count": 0,
        "family_equivalence_claim_count": 0,
    }


def test_unit04_sp01_is_read_only_and_keeps_listening_a2_locked() -> None:
    assert REPORT["scope_safety"] == {
        "q01_q10_modified": False,
        "q06_sentence_authority_modified": False,
        "q07_scene_authority_modified": False,
        "current360_episode_content_modified": False,
        "ms03_consumer_modified": False,
        "new_learner_facing_wording_authored": False,
        "second_sentence_authority_created": False,
        "second_scene_authority_created": False,
        "listening_modified": False,
        "a2_a2plus_unlocked": False,
    }
    assert REPORT["next_short_step"] == sp01.NEXT_SHORT_STEP


def test_unit04_sp01_is_deterministic() -> None:
    replay = sp01.build_unit04_current360_speaking_layer_acceptance()
    assert replay == REPORT
