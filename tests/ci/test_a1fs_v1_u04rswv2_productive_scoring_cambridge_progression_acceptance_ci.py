from __future__ import annotations

from product.a1fs_v1_2_1 import (
    u04rswv2_productive_scoring_cambridge_progression_acceptance as rswv2,
)


REPORT = rswv2.build_unit04_rswv2_productive_scoring_cambridge_progression_acceptance()


def test_u04rswv2_accepts_only_the_current_active_runtimes() -> None:
    assert REPORT["status"] == rswv2.STATUS
    assert REPORT["revision"] == rswv2.REVISION
    assert REPORT["source_runtime"]["active_form_runtime"] == rswv2.fsv2.TASK_ID
    assert REPORT["source_runtime"]["active_speaking_runtime"] == rswv2.spv2.TASK_ID
    assert REPORT["safety"]["fsv2_runtime_modified"] is False
    assert REPORT["safety"]["spv2_runtime_modified"] is False


def test_u04rswv2_fsv2_productive_scoring_is_semantic_and_paraphrase_aware() -> None:
    acceptance = REPORT["acceptance"]["fsv2_productive_scoring"]
    assert acceptance["productive_response_count"] > 0
    assert set(acceptance["productive_section_counts"]) >= {"B", "C", "D", "E"}
    assert set(acceptance["productive_stage_counts"]) == set(rswv2.STAGE_ORDER)
    assert acceptance["scoring_mode"] == "HUMAN_OR_SEMANTIC_REVIEW"
    assert acceptance["single_answer_required"] is False
    assert acceptance["reference_response_nonexclusive"] is True
    assert acceptance["acceptable_paraphrase"] is True
    assert set(acceptance["dimensions"]) == set(rswv2.fsv2.PRODUCTIVE_SCORING_DIMENSIONS)


def test_u04rswv2_spv2_scores_all_bridge_and_layer2_tasks_productively() -> None:
    acceptance = REPORT["acceptance"]["spv2_productive_scoring"]
    assert acceptance["bridge_task_count"] == 80
    assert acceptance["layer2_task_count"] == 160
    assert acceptance["productive_speaking_task_count"] == 240
    assert acceptance["distinct_speaking_mode_count"] == 11
    assert acceptance["scoring_mode"] == "HUMAN_OR_SEMANTIC_REVIEW"
    assert acceptance["single_answer_required"] is False
    assert acceptance["reference_response_nonexclusive"] is True
    assert acceptance["acceptable_paraphrase"] is True
    assert acceptance["audio_pronunciation_machine_score_required"] is False
    assert set(acceptance["dimensions"]) == set(rswv2.spv2.SPEAKING_SCORING_DIMENSIONS)


def test_u04rswv2_preserves_five_stage_cambridge_a1_progression() -> None:
    progression = REPORT["acceptance"]["cambridge_progression"]
    assert progression["form_count"] == 20
    assert progression["stage_order"] == list(rswv2.STAGE_ORDER)
    assert progression["stage_form_counts"] == {stage: 4 for stage in rswv2.STAGE_ORDER}
    assert progression["seen_to_unseen_boundary_form"] == 13
    assert progression["grammar_ceiling"] == "A1"
    assert progression["a2_grammar_introduced_count"] == 0
    assert progression["cambridge_claim"] == rswv2.CAMBRIDGE_BOUNDARY_CLAIM
    assert progression["official_cambridge_item_format_claimed"] is False
    assert set(progression["cambridge_section_alignment"]) == {"A", "B", "C", "D", "E"}


def test_u04rswv2_preserves_formal_ket_as_prerequisite_evidence_only() -> None:
    boundary = REPORT["acceptance"]["formal_ket_boundary"]
    assert boundary["formal_ket_authority_role"] == rswv2.m2c.FORMAL_KET_AUTHORITY_ROLE
    assert boundary["formal_ket_task_projection_count"] == 144
    assert boundary["skill_distribution"] == {skill: 36 for skill in rswv2.m2c.SKILLS}
    assert boundary["task_shape_authority"] == rswv2.FORMAL_KET_TASK_SHAPE_AUTHORITY
    assert boundary["learner_facing_authority"] is False
    assert boundary["canonical_promotion_allowed"] is False
    assert boundary["formal_ket_source_text_copied"] is False
    assert boundary["a2_unlocked"] is False
    assert set(boundary["formal_prerequisite_signals"]) == {
        "LISTENING_STRATEGY",
        "READING_STRATEGY",
        "SPEAKING_FUNCTION",
        "WRITING_STRATEGY",
    }


def test_u04rswv2_spv2_lineage_resolves_to_fsv2_without_seen_unseen_overlap() -> None:
    lineage = REPORT["acceptance"]["cross_runtime_lineage"]
    assert lineage["fsv2_active_item_count"] == 800
    assert lineage["speaking_source_ref_occurrence_count"] == 240
    assert lineage["distinct_speaking_source_ref_count"] > 0
    assert lineage["missing_speaking_source_ref_count"] == 0
    assert lineage["fsv2_seen_unseen_overlap_count"] == 0
    assert lineage["spv2_seen_unseen_overlap_count"] == 0


def test_u04rswv2_keeps_a1_and_support_relation_boundaries_closed() -> None:
    requirements = REPORT["approved_requirements_10_of_10"]
    assert requirements["07_a1_grammar_ceiling_preserved"]["status"] == "PASS"
    assert requirements["08_support_language_remains_non_assessed"]["status"] == "PASS"
    assert REPORT["safety"]["support_relations_promoted_to_assessed_target"] is False
    assert REPORT["safety"]["a2_a2plus_unlocked"] is False
    assert REPORT["safety"]["listening_modified"] is False
    assert REPORT["safety"]["other_units_modified"] is False


def test_u04rswv2_does_not_false_close_visual_acceptance() -> None:
    requirements = REPORT["approved_requirements_10_of_10"]
    assert len(requirements) == 10
    assert all(
        requirements[key]["status"] == "PASS"
        for key in requirements
        if key != "10_learner_facing_visual_pedagogical_acceptance"
    )
    assert (
        requirements["10_learner_facing_visual_pedagogical_acceptance"]["status"]
        == "PENDING_NEXT_SHORT_STEP"
    )
    assert REPORT["next_short_step"] == rswv2.NEXT_SHORT_STEP


def test_u04rswv2_is_deterministic() -> None:
    replay = rswv2.build_unit04_rswv2_productive_scoring_cambridge_progression_acceptance()
    assert replay == REPORT
