import hashlib
import json
from pathlib import Path

from product.a1fs_v1_2_1.u04ms02a_raz_aw_multi_sentence_micro_scene_capability import (
    build_unit04_raz_aw_multi_sentence_micro_scene_capability,
)
from product.a1fs_v1_2_1.u04ms02b_ket99_dialogue_prompt_remediation_transfer_overlay import (
    CONTENT_UNITS,
    FORBIDDEN_OUTPUT_KEYS,
    REVISION,
    STAGE_ROLES,
    STATUS,
    build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay,
    compact_readback,
)

ROOT = Path(__file__).resolve().parents[2]
PROJECTION = build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay(ROOT)


def _all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_keys(child)


def _content_units_by_id():
    rows = []
    for line in (ROOT / CONTENT_UNITS).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return {row["transcript_id"]: row for row in rows}


def test_u04ms02b_r1_reads_all_99_evidence_items_but_emits_only_abstract_semantic_mechanics() -> None:
    inventory = PROJECTION["ket99_evidence_inventory"]
    assert PROJECTION["revision"] == REVISION == "R1_KET99_SEMANTIC_DELIVERY_SUITABILITY_GATE"
    assert inventory["transcript_count"] == 99
    assert inventory["expected_transcript_range"] == {"first": "P004", "last": "P102", "count": 99}
    records = inventory["records"]
    assert [row["transcript_id"] for row in records] == [f"P{n:03d}" for n in range(4, 103)]
    source = _content_units_by_id()
    assert len(source) == 99
    for row in records:
        items = source[row["transcript_id"]]["evidence_items"]
        expected_digest = hashlib.sha256(
            json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        assert row["evidence_item_count"] == len(items)
        assert row["evidence_item_digest_sha256"] == expected_digest
        assert isinstance(row["mechanic_tags"], list)
        assert set(row["stage_semantic_acceptance"]) == set(STAGE_ROLES)
        assert set(row["stage_match_reasons"]) == set(STAGE_ROLES)
        assert row["authority_status"] == "non_authoritative"
        assert row["canonical_promotion_allowed"] is False
        assert row["raw_text_included"] is False
    assert FORBIDDEN_OUTPUT_KEYS.isdisjoint(set(_all_keys(PROJECTION)))
    assert "unit04_sentence_texts" not in set(_all_keys(PROJECTION))
    assert PROJECTION["scope"]["source_evidence_items_read_for_validation"] is True
    assert PROJECTION["scope"]["source_evidence_items_emitted"] is False


def test_u04ms02b_r1_known_ket99_mechanics_are_stage_specific_not_role_only() -> None:
    by_id = {row["transcript_id"]: row for row in PROJECTION["ket99_evidence_inventory"]["records"]}
    assert by_id["P012"]["stage_semantic_acceptance"]["ERROR_REPAIR"] is True
    assert by_id["P012"]["stage_semantic_acceptance"]["GUIDED_DIALOGUE"] is True
    assert by_id["P015"]["stage_semantic_acceptance"]["FOLLOW_UP_PROMPT"] is True
    assert by_id["P023"]["stage_semantic_acceptance"]["GUIDED_DIALOGUE"] is True
    assert by_id["P029"]["stage_semantic_acceptance"]["GUIDED_DIALOGUE"] is True
    assert by_id["P029"]["stage_semantic_acceptance"]["FOLLOW_UP_PROMPT"] is True
    for transcript_id in ("P018", "P024", "P052"):
        assert by_id[transcript_id]["stage_semantic_acceptance"]["ERROR_REPAIR"] is False
    assert all(count > 0 for count in PROJECTION["ket99_evidence_inventory"]["stage_pool_counts"].values())


def test_u04ms02b_r1_all_144_materialized_stage_bindings_have_semantic_fit_reasons() -> None:
    assert PROJECTION["status"] == STATUS
    summary = PROJECTION["overlay_summary"]
    assert summary["overlay_count"] == 36
    assert summary["interaction_stage_count"] == 144
    assert summary["semantic_compatible_stage_count"] == 144
    assert summary["semantic_incompatible_stage_count"] == 0
    assert summary["stage_role_distribution"] == {role: 36 for role in STAGE_ROLES}
    evidence = {row["evidence_ref_id"]: row for row in PROJECTION["ket99_evidence_inventory"]["records"]}
    for overlay in PROJECTION["overlays"]:
        assert [stage["stage_role"] for stage in overlay["interaction_stages"]] == list(STAGE_ROLES)
        for stage in overlay["interaction_stages"]:
            source = evidence[stage["ket99_evidence_ref_id"]]
            role = stage["stage_role"]
            assert source["stage_semantic_acceptance"][role] is True
            assert stage["semantic_compatibility"] == "PASS"
            assert stage["semantic_match_reasons"] == source["stage_match_reasons"][role]
            assert stage["semantic_match_reasons"]
            assert stage["unit04_target_operation"] == source["unit04_target_operations"][role]
            assert any(reason.startswith("MECHANIC_") for reason in stage["semantic_match_reasons"])
            assert any(reason.startswith("UNIT04_") and reason.endswith("_COMPATIBLE") for reason in stage["semantic_match_reasons"])


def test_u04ms02b_r1_every_overlay_resolves_to_existing_m2a_and_transfer_target() -> None:
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


def test_u04ms02b_r1_scope_safety_replay_and_readback_are_fail_closed() -> None:
    scope, safety = PROJECTION["scope"], PROJECTION["safety"]
    assert scope["semantic_delivery_suitability_gate"] is True
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
    assert safety["evidence_item_wording_copied_to_output"] is False
    assert safety["all_selected_stage_bindings_semantically_compatible"] is True
    assert safety["unit05_plus_grammar_leak_count"] == 0
    assert safety["a2_plus_unlock_count"] == 0
    replay = build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay(ROOT)
    assert replay == PROJECTION
    assert len(PROJECTION["projection_sha256"]) == 64
    readback = compact_readback(PROJECTION)
    assert readback["ket99_transcript_count"] == 99
    assert readback["overlay_count"] == 36
    assert readback["interaction_stage_count"] == 144
    assert readback["semantic_compatible_stage_count"] == 144
    assert readback["semantic_incompatible_stage_count"] == 0
    assert readback["raw_ket99_transcript_text_copied"] is False
    assert readback["evidence_item_wording_copied_to_output"] is False
    assert readback["a2_plus_unlock_count"] == 0
    print("U04MS02B_R1_READBACK=" + json.dumps(readback, sort_keys=True))
