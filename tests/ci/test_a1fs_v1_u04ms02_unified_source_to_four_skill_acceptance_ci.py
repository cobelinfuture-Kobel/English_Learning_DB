import json
from collections import Counter, defaultdict

from product.a1fs_v1_2_1.u04ms02a_raz_aw_multi_sentence_micro_scene_capability import (
    build_unit04_raz_aw_multi_sentence_micro_scene_capability,
    compact_readback as m2a_compact_readback,
)
from product.a1fs_v1_2_1.u04ms02b_ket99_dialogue_prompt_remediation_transfer_overlay import (
    build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay,
    compact_readback as m2b_compact_readback,
)
from product.a1fs_v1_2_1.u04ms02c_ket_four_skill_task_assessment_projection import (
    FORMAL_KET_AUTHORITY_ROLE,
    SKILLS,
    TASK_SHAPES,
    build_unit04_ket_four_skill_task_assessment_projection,
    compact_readback as m2c_compact_readback,
)


M2A = build_unit04_raz_aw_multi_sentence_micro_scene_capability()
M2B = build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay()
M2C = build_unit04_ket_four_skill_task_assessment_projection()


def test_u04ms02_unified_a_b_c_authority_and_count_contract() -> None:
    a = m2a_compact_readback(M2A)
    b = m2b_compact_readback(M2B)
    c = m2c_compact_readback(M2C)

    assert a["capability_count"] == 36
    assert a["sentence_count_distribution"] == {"2": 9, "3": 9, "4": 9, "5": 9}
    assert a["complete_inventory_unit_count"] == 41964
    assert a["complete_inventory_max_sentence_count"] == 635
    assert a["unit04_direct_projection_eligible_page_count_2_to_5"] == 4634
    assert a["unit04_extension_reference_total_gt_5"] == 4746
    assert a["review_record_count"] == 7957
    assert a["reading_authority_bridge_record_count"] == 7957
    assert a["linkage_record_count"] == 58590

    assert b["ket99_transcript_count"] == 99
    assert b["overlay_count"] == 36
    assert b["interaction_stage_count"] == 144
    assert b["semantic_compatible_stage_count"] == 144
    assert b["semantic_incompatible_stage_count"] == 0
    assert set(b["stage_pool_counts"]) == {
        "GUIDED_DIALOGUE",
        "FOLLOW_UP_PROMPT",
        "ERROR_REPAIR",
        "TRANSFER_PROMPT",
    }
    assert all(int(value) > 0 for value in b["stage_pool_counts"].values())
    assert b["raw_ket99_transcript_text_copied"] is False
    assert b["evidence_item_wording_copied_to_output"] is False
    assert b["a2_plus_unlock_count"] == 0

    assert c["task_projection_count"] == 144
    assert c["unit04_capability_count"] == 36
    assert c["skill_distribution"] == {skill: 36 for skill in SKILLS}
    assert c["m2b_stage_pool_counts"] == b["stage_pool_counts"]
    assert c["m2b_semantic_compatible_stage_count"] == 144
    assert c["m2b_semantic_incompatible_stage_count"] == 0
    assert c["formal_ket_authority_role"] == FORMAL_KET_AUTHORITY_ROLE
    assert c["formal_ket_source_text_copied"] is False
    assert c["forms_modified"] is False
    assert c["canonical_authority_mutated"] is False
    assert c["a2_plus_unlock_count"] == 0


def test_u04ms02_unified_lineage_is_exact_from_m2a_through_m2b_to_all_four_skills() -> None:
    capabilities = {row["capability_id"]: row for row in M2A["capabilities"]}
    overlays = {row["unit04_capability_id"]: row for row in M2B["overlays"]}
    tasks_by_capability = defaultdict(list)
    for row in M2C["task_projections"]:
        tasks_by_capability[row["unit04_capability_id"]].append(row)

    assert len(capabilities) == 36
    assert set(overlays) == set(capabilities)
    assert set(tasks_by_capability) == set(capabilities)

    for capability_id, capability in capabilities.items():
        overlay = overlays[capability_id]
        assert overlay["unit04_scene_ref_ids"] == capability["unit04_scene_ref_ids"]
        assert overlay["unit04_sentence_ids"] == capability["unit04_sentence_ids"]
        assert capability["authority_boundary"]["raz_is_learner_facing_authority"] is False
        assert capability["authority_boundary"]["raz_canonical_promotion_allowed"] is False
        assert capability["authority_boundary"]["raz_raw_text_copied"] is False
        assert capability["authority_boundary"]["a2_unlocked"] is False

        stage_by_role = {
            stage["stage_role"]: stage for stage in overlay["interaction_stages"]
        }
        assert set(stage_by_role) == {
            "GUIDED_DIALOGUE",
            "FOLLOW_UP_PROMPT",
            "ERROR_REPAIR",
            "TRANSFER_PROMPT",
        }
        assert all(stage["semantic_compatibility"] == "PASS" for stage in stage_by_role.values())

        tasks = tasks_by_capability[capability_id]
        assert len(tasks) == 4
        assert {row["skill"] for row in tasks} == set(SKILLS)
        for task in tasks:
            skill = task["skill"]
            shape = TASK_SHAPES[skill]
            assert task["unit04_scene_ref_ids"] == capability["unit04_scene_ref_ids"]
            assert task["unit04_sentence_ids"] == capability["unit04_sentence_ids"]
            assert task["m2b_overlay_id"] == overlay["overlay_id"]
            assert task["task_family"] == shape["task_family"]
            assert task["assessment_operation"] == shape["assessment_operation"]
            assert task["teacher_delivery_stage_roles"] == shape["teacher_delivery_stage_roles"]
            expected_refs = [stage_by_role[role]["ket99_evidence_ref_id"] for role in shape["teacher_delivery_stage_roles"]]
            assert task["teacher_delivery_evidence_refs"] == expected_refs
            assert task["teacher_delivery_semantic_compatibility"] == ["PASS"] * len(expected_refs)
            assert task["formal_ket_authority_role"] == FORMAL_KET_AUTHORITY_ROLE
            assert task["task_shape_authority"] == "UNIT04_PROJECTED_SHAPE_NOT_OFFICIAL_KET_ITEM_FORMAT"
            boundary = task["authority_boundary"]
            assert boundary["learner_language_authority"] == "UNIT04_Q07_VIA_M2A"
            assert boundary["formal_ket_is_learner_facing_authority"] is False
            assert boundary["formal_ket_canonical_promotion_allowed"] is False
            assert boundary["ket99_teacher_delivery_is_learner_facing_authority"] is False
            assert boundary["new_learner_facing_wording_authored"] is False
            assert boundary["formal_ket_source_text_copied"] is False
            assert boundary["a2_unlocked"] is False


def test_u04ms02_unified_task_shape_coverage_and_no_cross_scope_leak() -> None:
    tasks = M2C["task_projections"]
    assert Counter(row["skill"] for row in tasks) == Counter({skill: 36 for skill in SKILLS})
    assert Counter(row["task_family"] for row in tasks) == Counter({TASK_SHAPES[skill]["task_family"]: 36 for skill in SKILLS})
    assert all(row["response_authority"] == "UNIT04_Q07_VIA_M2A" for row in tasks)
    assert all(row["formal_ket_authority_role"] == FORMAL_KET_AUTHORITY_ROLE for row in tasks)
    assert all(row["task_shape_authority"] == "UNIT04_PROJECTED_SHAPE_NOT_OFFICIAL_KET_ITEM_FORMAT" for row in tasks)

    m2b_safety = M2B["safety"]
    assert m2b_safety["raw_ket99_transcript_text_copied"] is False
    assert m2b_safety["evidence_item_wording_copied_to_output"] is False
    assert m2b_safety["ket99_canonical_promotion_allowed"] is False
    assert m2b_safety["private_normalized_transcripts_read"] is False
    assert m2b_safety["all_selected_stage_bindings_semantically_compatible"] is True
    assert m2b_safety["unit05_plus_grammar_leak_count"] == 0
    assert m2b_safety["a2_plus_unlock_count"] == 0

    safety = M2C["safety"]
    assert safety["formal_ket_learner_facing_authority"] is False
    assert safety["formal_ket_canonical_promotion_allowed"] is False
    assert safety["formal_ket_source_text_copied"] is False
    assert safety["private_ket_body_read"] is False
    assert safety["all_tasks_resolve_to_existing_unit04_q07_via_m2a"] is True
    assert safety["m2b_teacher_delivery_semantic_gate_144_of_144"] is True
    assert safety["forms_modified"] is False
    assert safety["canonical_authority_mutated"] is False
    assert safety["unit05_plus_grammar_leak_count"] == 0
    assert safety["a2_plus_unlock_count"] == 0


def test_u04ms02_unified_deterministic_replay_and_machine_readback(capsys) -> None:
    replay = build_unit04_ket_four_skill_task_assessment_projection()
    assert replay == M2C

    a = m2a_compact_readback(M2A)
    b = m2b_compact_readback(M2B)
    c = m2c_compact_readback(M2C)
    readback = {
        "status": "PASS_A1FS_V1_U04MS02_UNIFIED_SOURCE_TO_FOUR_SKILL_ACCEPTANCE",
        "m2a_capability_count": a["capability_count"],
        "m2a_sentence_count_distribution": a["sentence_count_distribution"],
        "raz_aw_complete_inventory_units": a["complete_inventory_unit_count"],
        "raz_aw_max_sentence_count": a["complete_inventory_max_sentence_count"],
        "raz_ai_direct_2_to_5": a["unit04_direct_projection_eligible_page_count_2_to_5"],
        "raz_ai_extension_gt_5": a["unit04_extension_reference_total_gt_5"],
        "m2b_ket99_transcript_count": b["ket99_transcript_count"],
        "m2b_stage_pool_counts": b["stage_pool_counts"],
        "m2b_semantic_compatible_stage_count": b["semantic_compatible_stage_count"],
        "m2b_semantic_incompatible_stage_count": b["semantic_incompatible_stage_count"],
        "m2c_task_projection_count": c["task_projection_count"],
        "m2c_skill_distribution": c["skill_distribution"],
        "formal_ket_authority_role": c["formal_ket_authority_role"],
        "forms_modified": c["forms_modified"],
        "canonical_authority_mutated": c["canonical_authority_mutated"],
        "a2_plus_unlock_count": c["a2_plus_unlock_count"],
    }
    with capsys.disabled():
        print("U04MS02_UNIFIED_ACCEPTANCE_READBACK=" + json.dumps(readback, sort_keys=True))
