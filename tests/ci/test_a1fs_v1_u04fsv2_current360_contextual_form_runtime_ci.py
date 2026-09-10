from __future__ import annotations

from product.a1fs_v1_2_1 import (
    u04fsv2_current360_contextual_form_runtime as fsv2,
)


REPORT = fsv2.build_unit04_fsv2_current360_contextual_form_runtime()


def test_u04fsv2_materializes_one_active_20x40_runtime() -> None:
    assert REPORT["status"] == fsv2.STATUS
    assert REPORT["revision"] == fsv2.REVISION
    contract = REPORT["materialization_contract"]
    assert contract["form_count"] == 20
    assert contract["activities_per_form"] == 40
    assert contract["activity_count"] == 800
    assert contract["section_counts_per_form"] == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
    assert contract["controlled_foundation_activity_count"] == 120
    assert contract["current360_contextual_activity_count"] == 680
    assert contract["task_variant_count"] == 27
    assert len(REPORT["forms"]) == 20
    assert len(REPORT["active_items"]) == 800
    assert len(REPORT["runtime_bindings"]) == 800
    assert len({row["active_item_id"] for row in REPORT["active_items"]}) == 800


def test_u04fsv2_cutover_supersedes_old_fixed_learner_runtime_without_deleting_lineage() -> None:
    cutover = REPORT["cutover_contract"]
    assert cutover["active_form_runtime_authority"] == fsv2.TASK_ID
    assert cutover["parallel_active_form_runtime_allowed"] is False
    assert cutover["legacy_q10_role"] == "LINEAGE_AND_CONTROL_FOUNDATION_ONLY"
    assert cutover["legacy_q10r1_role"] == "SUPERSEDED_AS_ACTIVE_LEARNER_FACING_RUNTIME"
    assert cutover["current360_role"] == "NATURAL_PASSAGE_AUTHORITY"
    assert cutover["a1_language_more_mature_tasks"] is True
    assert cutover["official_cambridge_item_format_claimed"] is False
    assert REPORT["safety"]["q10_source_authority_deleted"] is False
    assert REPORT["safety"]["q10_source_identity_reused_as_lineage"] is True
    assert REPORT["safety"]["q10r1_legacy_active_runtime_retained"] is False


def test_u04fsv2_uses_current360_for_contextual_sections_and_keeps_a_controlled() -> None:
    items = REPORT["active_items"]
    controlled = [row for row in items if row["section"] == "A"]
    contextual = [row for row in items if row["section"] in {"B", "C", "D", "E"}]
    assert len(controlled) == 120
    assert len(contextual) == 680
    assert all(row["current360_episode_lineage"] is None for row in controlled)
    assert all(row["current360_episode_lineage"] for row in contextual)
    assert all(row["current360_episode_lineage"]["passage"] for row in contextual)
    assert all(row["source_q10_lineage"]["source_q10_item_id"] for row in items)


def test_u04fsv2_has_diverse_section_task_variants_and_cambridge_prerequisite_alignment() -> None:
    coverage = REPORT["coverage"]
    assert coverage["task_variant_count"] == 27
    variants = {row["task_variant"] for row in REPORT["active_items"]}
    assert variants == {
        variant
        for values in fsv2.TASK_VARIANTS.values()
        for variant in values
    }
    assert coverage["section_skill_counts"] == {
        "GRAMMAR": 120,
        "READING": 360,
        "READING_WRITING": 200,
        "SPEAKING_WRITING": 120,
    }
    for row in REPORT["active_items"]:
        alignment = row["cambridge_prerequisite_alignment"]
        assert alignment["claim"] == fsv2.CAMBRIDGE_CLAIM
        assert alignment["grammar_ceiling"] == "A1"
        assert alignment["a2_grammar_introduced"] is False


def test_u04fsv2_seen_unseen_progression_and_scaffold_fading_are_explicit() -> None:
    forms = REPORT["forms"]
    assert [row["progression_stage"] for row in forms] == (
        ["GUIDED"] * 4
        + ["REDUCED_SUPPORT"] * 4
        + ["INDEPENDENT"] * 4
        + ["TRANSFER"] * 4
        + ["RETENTION"] * 4
    )
    assert [row["support_level"] for row in forms] == (
        ["HIGH"] * 4
        + ["MEDIUM"] * 4
        + ["LOW"] * 4
        + ["MINIMAL"] * 4
        + ["CUMULATIVE"] * 4
    )
    assert all(row["context_exposure"].startswith("SEEN") for row in forms[:12])
    assert all(row["context_exposure"].startswith("UNSEEN") for row in forms[12:])
    coverage = REPORT["coverage"]
    assert coverage["seen_selected_episode_count"] > 0
    assert coverage["unseen_selected_episode_count"] > 0
    assert coverage["selected_seen_unseen_overlap_count"] == 0


def test_u04fsv2_distribution_and_boundary_guards() -> None:
    coverage = REPORT["coverage"]
    assert coverage["target_relation_coverage"] == "8/8"
    assert set(coverage["target_relation_counts"]) == set(fsv2.TARGET_RELATIONS)
    assert coverage["communicative_function_coverage"] == "6/6"
    assert coverage["current360_micro_scene_coverage"] == "36/36"
    assert coverage["current360_life_domain_coverage"] == "12/12"
    assert coverage["assessed_support_relation_count"] == 0
    assert coverage["a2_grammar_introduced_count"] == 0
    assert REPORT["safety"]["support_relations_promoted_to_assessed_target"] is False
    assert REPORT["safety"]["a2_a2plus_unlocked"] is False
    assert REPORT["safety"]["other_units_modified"] is False


def test_u04fsv2_d_and_e_share_context_without_learner_answer_key_metadata_leakage() -> None:
    assert REPORT["materialization_contract"]["d_e_shared_context_pair_count"] == 120
    assert REPORT["coverage"]["learner_answer_key_metadata_leak_count"] == 0
    for form_number in range(1, 21):
        rows = [row for row in REPORT["active_items"] if row["form_number"] == form_number]
        d_rows = [row for row in rows if row["section"] == "D"]
        e_rows = [row for row in rows if row["section"] == "E"]
        assert len(d_rows) == 8
        assert len(e_rows) == 6
        for index, e_row in enumerate(e_rows):
            assert e_row["shared_context_from_d"] is True
            assert (
                e_row["current360_episode_lineage"]["episode_id"]
                == d_rows[index]["current360_episode_lineage"]["episode_id"]
            )
        for row in rows:
            activity = row["learner_activity"]
            assert "correct_answer" not in activity
            assert "reference_answer" not in activity
            assert "answer_key" not in activity
            assert "source_q10_item_id" not in activity


def test_u04fsv2_productive_scoring_is_semantic_and_paraphrase_aware() -> None:
    assert REPORT["coverage"]["productive_response_count"] > 0
    productive = [
        row for row in REPORT["active_items"]
        if row["scoring_contract"]["scoring_mode"] == "HUMAN_OR_SEMANTIC_REVIEW"
    ]
    assert productive
    for row in productive:
        scoring = row["scoring_contract"]
        assert scoring["single_answer_required"] is False
        assert scoring["reference_response_nonexclusive"] is True
        assert scoring["acceptable_paraphrase"] is True
        assert scoring["dimensions"] == list(fsv2.PRODUCTIVE_SCORING_DIMENSIONS)


def test_u04fsv2_tracks_all_ten_approved_requirements_without_false_closeout_claims() -> None:
    requirements = REPORT["approved_requirements_10_of_10"]
    assert len(requirements) == 10
    assert requirements["01_task_maturity_without_new_grammar"]["status"] == "PASS"
    assert requirements["02_current360_seen_unseen_split"]["status"] == "PASS"
    assert requirements["03_cross_skill_shared_passage_without_answer_leakage"]["status"] == "PASS"
    assert requirements["04_productive_response_scoring_contract"]["status"] == "PASS"
    assert requirements["05_layer1_to_layer2_bridge"]["status"] == "DEFERRED_TO_NEXT_SHORT_STEP"
    assert (
        requirements["06_speaking_not_description_only"]["status"]
        == "PARTIAL_FORM_E_PASS_NEXT_SPEAKING_CUTOVER_REQUIRED"
    )
    assert requirements["07_scaffold_fading"]["status"] == "PASS"
    assert requirements["08_distributional_coverage"]["status"] == "PASS"
    assert requirements["09_support_language_non_assessed"]["status"] == "PASS"
    assert (
        requirements["10_learner_facing_visual_pedagogical_acceptance"]["status"]
        == "PENDING_LATER_MILESTONE"
    )
    assert REPORT["next_short_step"] == fsv2.NEXT_SHORT_STEP


def test_u04fsv2_is_deterministic() -> None:
    replay = fsv2.build_unit04_fsv2_current360_contextual_form_runtime()
    assert replay == REPORT
