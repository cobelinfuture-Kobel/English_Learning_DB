from __future__ import annotations

import json
from pathlib import Path

from product.a1fs_v1_2_1.u04ms02c_ket_four_skill_task_assessment_projection import (
    FORMAL_KET_AUTHORITY_ROLE,
    FORMAL_KET_SOURCE_ID,
    SKILLS,
    STATUS,
    TASK_SHAPES,
    build_unit04_ket_four_skill_task_assessment_projection,
    compact_readback,
)

ROOT = Path(__file__).resolve().parents[2]
PROJECTION = build_unit04_ket_four_skill_task_assessment_projection(ROOT)


def _all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_keys(child)


def test_u04ms02c_identity_and_formal_ket_authority_boundary() -> None:
    assert PROJECTION["status"] == STATUS
    assert PROJECTION["unit_number"] == 4
    assert PROJECTION["unit_id"] == "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
    formal = PROJECTION["formal_ket_reference"]
    assert formal["source_id"] == FORMAL_KET_SOURCE_ID
    assert formal["authority_role"] == FORMAL_KET_AUTHORITY_ROLE
    assert formal["learner_facing_authority"] is False
    assert formal["canonical_promotion_allowed"] is False
    assert formal["integration_anchor_resolved"] is True
    assert formal["anchor_validation"]["source_body_emitted"] is False
    assert set(formal["anchor_validation"]["required_signals"]) == {
        "READING_STRATEGY", "LISTENING_STRATEGY", "SPEAKING_FUNCTION", "WRITING_STRATEGY",
    }


def test_u04ms02c_materializes_36x4_exact_four_skill_projection() -> None:
    summary = PROJECTION["projection_summary"]
    assert summary["unit04_capability_count"] == 36
    assert summary["task_projection_count"] == 144
    assert summary["skill_count"] == 4
    assert summary["skill_distribution"] == {skill: 36 for skill in SKILLS}
    tasks = PROJECTION["task_projections"]
    assert len(tasks) == 144
    assert len({row["task_projection_id"] for row in tasks}) == 144
    per_capability = {}
    for row in tasks:
        per_capability.setdefault(row["unit04_capability_id"], set()).add(row["skill"])
    assert len(per_capability) == 36
    assert all(skills == set(SKILLS) for skills in per_capability.values())


def test_u04ms02c_every_task_resolves_to_existing_unit04_lineage_and_m2b_semantic_stage() -> None:
    for row in PROJECTION["task_projections"]:
        assert row["unit04_scene_ref_ids"]
        assert row["unit04_sentence_ids"]
        assert len(row["unit04_scene_ref_ids"]) == len(row["unit04_sentence_ids"])
        assert row["m2b_overlay_id"].startswith("U04-MS02B-KET99-")
        assert row["teacher_delivery_stage_roles"] == TASK_SHAPES[row["skill"]]["teacher_delivery_stage_roles"]
        assert len(row["teacher_delivery_evidence_refs"]) == len(row["teacher_delivery_stage_roles"])
        assert row["teacher_delivery_semantic_compatibility"] == ["PASS"] * len(row["teacher_delivery_stage_roles"])
        assert row["task_shape_authority"] == "UNIT04_PROJECTED_SHAPE_NOT_OFFICIAL_KET_ITEM_FORMAT"
        assert row["response_authority"] == "UNIT04_Q07_VIA_M2A"
        boundary = row["authority_boundary"]
        assert boundary["learner_language_authority"] == "UNIT04_Q07_VIA_M2A"
        assert boundary["formal_ket_is_learner_facing_authority"] is False
        assert boundary["formal_ket_canonical_promotion_allowed"] is False
        assert boundary["ket99_teacher_delivery_is_learner_facing_authority"] is False
        assert boundary["new_learner_facing_wording_authored"] is False
        assert boundary["formal_ket_source_text_copied"] is False
        assert boundary["a2_unlocked"] is False


def test_u04ms02c_preserves_pass_b_semantic_gate_and_reports_actual_stage_pool_counts() -> None:
    summary = PROJECTION["projection_summary"]
    assert summary["m2b_interaction_stage_count"] == 144
    assert summary["m2b_semantic_compatible_stage_count"] == 144
    assert summary["m2b_semantic_incompatible_stage_count"] == 0
    pools = summary["m2b_stage_pool_counts"]
    assert set(pools) == {"GUIDED_DIALOGUE", "FOLLOW_UP_PROMPT", "ERROR_REPAIR", "TRANSFER_PROMPT"}
    assert all(isinstance(value, int) and value > 0 for value in pools.values())
    readback = compact_readback(PROJECTION)
    assert readback["m2b_stage_pool_counts"] == pools
    assert readback["m2b_semantic_compatible_stage_count"] == 144
    assert readback["m2b_semantic_incompatible_stage_count"] == 0
    print("U04MS02C_ACCEPTANCE_READBACK=" + json.dumps(readback, ensure_ascii=False, sort_keys=True))


def test_u04ms02c_does_not_copy_formal_ket_or_private_content_and_does_not_unlock_scope() -> None:
    forbidden_exact_keys = {
        "source_text", "transcript_text", "body_text", "raw_text", "clean_text", "prompt",
        "correct_answer", "answer_key", "learner_response", "audio_bytes", "recording",
    }
    assert not (set(_all_keys(PROJECTION)) & forbidden_exact_keys)
    assert PROJECTION["scope"] == {
        "four_skill_task_assessment_projection_only": True,
        "form01_20_modified": False,
        "canonical_grammar_modified": False,
        "canonical_vocabulary_modified": False,
        "canonical_chunk_modified": False,
        "new_learner_facing_wording_authored": False,
        "formal_ket_source_text_included": False,
        "private_ket_body_read": False,
        "unit05_plus_grammar_opened": False,
        "a2_unlocked": False,
    }
    safety = PROJECTION["safety"]
    assert safety["formal_ket_source_text_copied"] is False
    assert safety["private_ket_body_read"] is False
    assert safety["all_tasks_resolve_to_existing_unit04_q07_via_m2a"] is True
    assert safety["m2b_teacher_delivery_semantic_gate_144_of_144"] is True
    assert safety["forms_modified"] is False
    assert safety["canonical_authority_mutated"] is False
    assert safety["unit05_plus_grammar_leak_count"] == 0
    assert safety["a2_plus_unlock_count"] == 0


def test_u04ms02c_is_deterministic() -> None:
    replay = build_unit04_ket_four_skill_task_assessment_projection(ROOT)
    assert replay["projection_sha256"] == PROJECTION["projection_sha256"]
    assert replay["task_projections"] == PROJECTION["task_projections"]
    assert len(PROJECTION["projection_sha256"]) == 64
