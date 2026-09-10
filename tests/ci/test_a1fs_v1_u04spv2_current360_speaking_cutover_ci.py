from __future__ import annotations

from product.a1fs_v1_2_1 import u04spv2_current360_speaking_cutover as spv2


REPORT = spv2.build_unit04_spv2_speaking_layer1_bridge_layer2_cutover()


def test_u04spv2_materializes_layer1_bridge_and_layer2() -> None:
    assert REPORT["status"] == spv2.STATUS
    assert REPORT["revision"] == spv2.REVISION
    contract = REPORT["materialization_contract"]
    assert contract["layer1_atomic_sentence_count"] == 121
    assert contract["bridge_task_count"] == 80
    assert contract["bridge_tasks_per_form"] == 4
    assert contract["layer2_task_count"] == 160
    assert contract["layer2_tasks_per_form"] == 8
    assert len(REPORT["layer1_atomic_speaking_pool"]) == 121
    assert len(REPORT["bridge_tasks"]) == 80
    assert len(REPORT["layer2_connected_speaking"]) == 160


def test_u04spv2_is_the_only_active_connected_speaking_runtime() -> None:
    cutover = REPORT["cutover_contract"]
    assert cutover["active_speaking_runtime_authority"] == spv2.TASK_ID
    assert cutover["parallel_active_speaking_runtime_allowed"] is False
    assert cutover["legacy_sp01_layer1_role"] == "REUSED_ATOMIC_POOL_AND_LINEAGE"
    assert cutover["legacy_sp01_layer2_role"] == "SUPERSEDED_NOT_ACTIVE"
    assert cutover["current360_passage_split_is_layer2_model"] is False
    assert cutover["a1_language_more_mature_tasks"] is True


def test_u04spv2_bridge_has_four_distinct_progression_modes_per_form() -> None:
    assert REPORT["coverage"]["bridge_mode_counts"] == {
        mode: 20 for mode in spv2.BRIDGE_MODES
    }
    for form_number in range(1, 21):
        rows = [
            row for row in REPORT["bridge_tasks"] if row["form_number"] == form_number
        ]
        assert len(rows) == 4
        assert [row["speaking_mode"] for row in rows] == list(spv2.BRIDGE_MODES)
        assert all(row["layer"] == "BRIDGE" for row in rows)


def test_u04spv2_layer2_is_not_description_only() -> None:
    assert REPORT["coverage"]["layer2_mode_counts"] == {
        mode: 20 for mode in spv2.LAYER2_MODES
    }
    assert set(spv2.LAYER2_MODES) == {
        "LOCATION_QA",
        "TWO_FACT_CHAIN",
        "ASK_AND_ANSWER",
        "SCENE_DESCRIPTION",
        "SHORT_RETELL",
        "DIALOGUE_FOLLOW_UP",
        "REPAIR_CLARIFY",
        "TRANSFER_CHANGED_LOCATION",
    }
    for form_number in range(1, 21):
        rows = [
            row
            for row in REPORT["layer2_connected_speaking"]
            if row["form_number"] == form_number
        ]
        assert len(rows) == 8
        assert [row["speaking_mode"] for row in rows] == list(spv2.LAYER2_MODES)


def test_u04spv2_layer2_uses_current360_form_context_without_passage_split_model() -> None:
    for row in REPORT["layer2_connected_speaking"]:
        assert row["current360_episode_lineage"]["episode_id"]
        assert row["current360_episode_lineage"]["passage"]
        assert row["source_form_runtime_lineage"]["fsv2_active_item_id"]
        assert row["source_form_runtime_lineage"]["section"] == "D"
        assert row["passage_split_as_model_utterances"] is False
    assert REPORT["coverage"]["passage_split_model_utterance_count"] == 0


def test_u04spv2_seen_unseen_and_scaffold_progression_are_preserved() -> None:
    rows = REPORT["layer2_connected_speaking"]
    assert all(row["context_exposure"].startswith("SEEN") for row in rows if row["form_number"] <= 12)
    assert all(row["context_exposure"].startswith("UNSEEN") for row in rows if row["form_number"] >= 13)
    assert REPORT["coverage"]["seen_layer2_episode_count"] > 0
    assert REPORT["coverage"]["unseen_layer2_episode_count"] > 0
    assert REPORT["coverage"]["seen_unseen_overlap_count"] == 0
    expected_support = {
        range(1, 5): "GUIDED",
        range(5, 9): "REDUCED_SUPPORT",
        range(9, 13): "INDEPENDENT",
        range(13, 17): "TRANSFER",
        range(17, 21): "RETENTION",
    }
    for form_range, stage in expected_support.items():
        assert all(
            row["progression_stage"] == stage
            for row in rows
            if row["form_number"] in form_range
        )


def test_u04spv2_speaking_scoring_accepts_semantically_valid_paraphrases() -> None:
    contract = REPORT["speaking_scoring_contract"]
    assert contract["scoring_mode"] == "HUMAN_OR_SEMANTIC_REVIEW"
    assert contract["single_answer_required"] is False
    assert contract["acceptable_paraphrase"] is True
    assert set(contract["dimensions"]) == set(spv2.SPEAKING_SCORING_DIMENSIONS)
    for row in REPORT["bridge_tasks"] + REPORT["layer2_connected_speaking"]:
        scoring = row["scoring_contract"]
        assert scoring["single_answer_required"] is False
        assert scoring["acceptable_paraphrase"] is True
        assert scoring["required_dimensions"]


def test_u04spv2_keeps_unit04_boundary_and_distribution_guards() -> None:
    coverage = REPORT["coverage"]
    assert coverage["layer2_target_relation_coverage"] == "8/8"
    assert set(coverage["layer2_target_relation_counts"]) == set(spv2.fsv2.TARGET_RELATIONS)
    assert coverage["support_relation_assessed_count"] == 0
    assert coverage["a2_grammar_introduced_count"] == 0
    assert REPORT["safety"]["support_relations_promoted_to_assessed_target"] is False
    assert REPORT["safety"]["a2_a2plus_unlocked"] is False
    assert REPORT["safety"]["other_units_modified"] is False


def test_u04spv2_closes_approved_requirements_05_and_06_without_false_visual_closeout() -> None:
    requirements = REPORT["approved_requirements_10_of_10"]
    assert len(requirements) == 10
    assert requirements["05_layer1_to_layer2_bridge"]["status"] == "PASS"
    assert requirements["06_speaking_not_description_only"]["status"] == "PASS"
    assert (
        requirements["10_learner_facing_visual_pedagogical_acceptance"]["status"]
        == "PENDING_LATER_MILESTONE"
    )
    assert REPORT["next_short_step"] == spv2.NEXT_SHORT_STEP


def test_u04spv2_is_deterministic() -> None:
    replay = spv2.build_unit04_spv2_speaking_layer1_bridge_layer2_cutover()
    assert replay == REPORT
