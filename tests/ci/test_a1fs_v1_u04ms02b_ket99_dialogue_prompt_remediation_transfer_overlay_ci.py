import json
from pathlib import Path

from product.a1fs_v1_2_1.u04ms02a_raz_aw_multi_sentence_micro_scene_capability import (
    build_unit04_raz_aw_multi_sentence_micro_scene_capability,
)
from product.a1fs_v1_2_1.u04ms02b_ket99_dialogue_prompt_remediation_transfer_overlay import (
    STAGE_ROLES,
    STATUS,
    build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay,
    compact_readback,
)

ROOT = Path(__file__).resolve().parents[2]
PROJECTION = build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay(ROOT)


def test_u04ms02b_ket99_public_evidence_inventory_is_complete_and_non_authoritative() -> None:
    inventory = PROJECTION["ket99_evidence_inventory"]
    assert inventory["transcript_count"] == 99
    assert inventory["expected_transcript_range"] == {"first": "P004", "last": "P102", "count": 99}
    records = inventory["records"]
    assert [row["transcript_id"] for row in records] == [f"P{n:03d}" for n in range(4, 103)]
    assert all(row["authority_status"] == "non_authoritative" for row in records)
    assert all(row["canonical_promotion_allowed"] is False for row in records)
    assert all(row["raw_text_included"] is False for row in records)
    assert all(row["admission"]["teacher_delivery"] == "approved" for row in records)
    assert all(row["admission"]["lesson_planner"] == "approved_with_constraints" for row in records)
    assert all(row["admission"]["canonical_grammar_authority"] == "denied" for row in records)
    assert all(row["admission"]["canonical_vocabulary_authority"] == "denied" for row in records)
    assert all(count > 0 for count in inventory["stage_pool_counts"].values())
    assert set(inventory["stage_pool_counts"]) == set(STAGE_ROLES)


def test_u04ms02b_materializes_four_stage_overlay_for_all_36_m2a_capabilities() -> None:
    assert PROJECTION["status"] == STATUS
    summary = PROJECTION["overlay_summary"]
    assert summary["overlay_count"] == 36
    assert summary["interaction_stage_count"] == 144
    assert summary["stage_role_distribution"] == {role: 36 for role in STAGE_ROLES}
    evidence_ids = {row["evidence_ref_id"] for row in PROJECTION["ket99_evidence_inventory"]["records"]}
    assert len(PROJECTION["overlays"]) == 36
    for row in PROJECTION["overlays"]:
        assert [stage["stage_role"] for stage in row["interaction_stages"]] == list(STAGE_ROLES)
        assert all(stage["ket99_evidence_ref_id"] in evidence_ids for stage in row["interaction_stages"])
        assert row["authority_boundary"]["ket99_is_learner_facing_authority"] is False
        assert row["authority_boundary"]["ket99_canonical_promotion_allowed"] is False
        assert row["authority_boundary"]["ket99_raw_transcript_text_copied"] is False
        assert row["authority_boundary"]["new_learner_facing_wording_authored"] is False
        assert row["authority_boundary"]["a2_unlocked"] is False


def test_u04ms02b_every_overlay_resolves_to_existing_m2a_and_transfer_target() -> None:
    m2a = build_unit04_raz_aw_multi_sentence_micro_scene_capability(ROOT)
    by_id = {row["capability_id"]: row for row in m2a["capabilities"]}
    assert len(by_id) == 36
    for row in PROJECTION["overlays"]:
        source = by_id[row["unit04_capability_id"]]
        assert row["unit04_scene_ref_ids"] == source["unit04_scene_ref_ids"]
        assert row["unit04_sentence_ids"] == source["unit04_sentence_ids"]
        transfer = row["interaction_stages"][-1]
        target = by_id[transfer["transfer_target_capability_id"]]
        assert transfer["transfer_target_scene_ref_ids"] == target["unit04_scene_ref_ids"]
    serialized = json.dumps(PROJECTION, ensure_ascii=False, sort_keys=True)
    for key in ("source_text", "transcript_text", "body_text", "clean_text", "evidence_items", "correct_answer", "answer_key", "learner_response", '"prompt":'):
        assert key not in serialized
    assert "unit04_sentence_texts" not in serialized


def test_u04ms02b_scope_safety_replay_and_readback_are_fail_closed() -> None:
    scope = PROJECTION["scope"]
    safety = PROJECTION["safety"]
    assert scope["structural_teacher_delivery_overlay_only"] is True
    assert scope["form01_20_modified"] is False
    assert scope["canonical_grammar_modified"] is False
    assert scope["canonical_vocabulary_modified"] is False
    assert scope["canonical_chunk_modified"] is False
    assert scope["new_learner_facing_wording_authored"] is False
    assert scope["raw_ket99_transcript_text_included"] is False
    assert scope["unit05_plus_grammar_opened"] is False
    assert scope["a2_unlocked"] is False
    assert safety["ket99_canonical_promotion_allowed"] is False
    assert safety["private_normalized_transcripts_read"] is False
    assert safety["raw_ket99_transcript_text_copied"] is False
    assert safety["unit05_plus_grammar_leak_count"] == 0
    assert safety["a2_plus_unlock_count"] == 0
    replay = build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay(ROOT)
    assert replay == PROJECTION
    assert len(PROJECTION["projection_sha256"]) == 64
    readback = compact_readback(PROJECTION)
    assert readback["ket99_transcript_count"] == 99
    assert readback["overlay_count"] == 36
    assert readback["interaction_stage_count"] == 144
    assert readback["stage_role_distribution"] == {role: 36 for role in STAGE_ROLES}
    assert readback["raw_ket99_transcript_text_copied"] is False
    assert readback["a2_plus_unlock_count"] == 0
    print("U04MS02B_KET99_READBACK=" + json.dumps(readback, sort_keys=True))
