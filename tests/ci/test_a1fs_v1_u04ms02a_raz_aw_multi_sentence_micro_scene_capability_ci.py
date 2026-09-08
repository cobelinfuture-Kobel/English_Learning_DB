from __future__ import annotations

import json
from pathlib import Path

from product.a1fs_v1_2_1.u04ms02a_raz_aw_multi_sentence_micro_scene_capability import (
    CAPABILITY_COUNT, RAZ_SNAPSHOT, SENTENCE_COUNT_PATTERN, STATUS,
    build_unit04_raz_aw_multi_sentence_micro_scene_capability, compact_readback,
)

ROOT = Path(__file__).resolve().parents[2]
PROJECTION = build_unit04_raz_aw_multi_sentence_micro_scene_capability(ROOT)


def test_u04ms02a_r1_complete_inventory_is_text_free_unbounded_and_reconciled() -> None:
    s = json.loads((ROOT / RAZ_SNAPSHOT).read_text(encoding="utf-8"))
    p = s["snapshot_policy"]; aw = s["a_w_complete_inventory"]
    assert p["raw_raz_text_included"] is False
    assert p["candidate_rows_promoted"] is False
    assert p["raz_level_used_as_cefr_equivalence"] is False
    assert p["source_sentence_count_not_prelimited"] is True
    assert aw["total_unit_count"] == 41964
    assert aw["page_unit_count"] == 22632
    assert aw["reuse_unit_count"] == 19332
    assert aw["max_sentence_count"] == 635
    assert sum(r["total_unit_count"] for r in aw["per_level"].values()) == 41964
    assert set(aw["per_level"]) == set("ABCDEFGHIJKLMNOPQRSTUVW")
    assert sum(aw["bucket_counts"].values()) == 41964
    assert len(aw["full_inventory_digest_sha256"]) == 64
    assert len(aw["exact_sentence_count_distribution_sha256"]) == 64
    serialized = json.dumps(s, ensure_ascii=False, sort_keys=True)
    for token in ('"clean_text":', '"source_text":', '"book_title":', '"title":'):
        assert token not in serialized


def test_u04ms02a_r1_a_i_review_bridge_linkage_gate_is_fully_hydrated() -> None:
    s = json.loads((ROOT / RAZ_SNAPSHOT).read_text(encoding="utf-8"))
    g = s["a1_a1plus_observational_gate_scope"]
    h = s["review_bridge_linkage_hydration"]
    assert g["levels"] == "A-I"
    assert g["raz_level_is_not_cefr_equivalence"] is True
    assert g["page_unit_count"] == 7957
    assert g["reuse_unit_count_structural_reference_only"] == 4690
    assert g["unit04_direct_projection_eligible_page_count_2_to_5"] == 4634
    assert g["unit04_direct_projection_exact_sentence_count_distribution"] == {"2": 2643, "3": 1240, "4": 575, "5": 176}
    assert g["unit04_extension_reference_total_gt_5"] == 4746
    assert h["review"]["record_count"] == 7957
    assert h["reading_authority_bridge"]["record_count"] == 7957
    assert h["linkage"]["record_count"] == 58590
    assert all(h["cross_layer_checks"].values())
    assert all(all(r["cross_layer_checks"].values()) for r in g["per_level"].values())
    assert s["source_file_manifest_digest"]["file_count"] == 50


def test_u04ms02a_r1_materializes_36_direct_capabilities_with_hydrated_evidence() -> None:
    assert PROJECTION["status"] == STATUS
    assert len(PROJECTION["capabilities"]) == CAPABILITY_COUNT == 36
    assert PROJECTION["capability_summary"]["sentence_count_distribution"] == {"2": 9, "3": 9, "4": 9, "5": 9}
    expected = [SENTENCE_COUNT_PATTERN[i % len(SENTENCE_COUNT_PATTERN)] for i in range(CAPABILITY_COUNT)]
    assert [r["sentence_count"] for r in PROJECTION["capabilities"]] == expected
    for r in PROJECTION["capabilities"]:
        e = r["raz_structural_evidence"]
        assert r["projection_lane"] == "UNIT04_DIRECT_PROJECTION_ELIGIBLE"
        assert e["source_level"] in "ABCDEFGHI"
        assert e["source_sentence_count_band"] == "2-5"
        assert e["cross_layer_gate_hydrated"] is True
        assert e["authority_status"] == "candidate_only"
        assert e["promotion_status"] == "promotion_blocked"


def test_u04ms02a_r1_every_materialized_sentence_resolves_exactly_to_q07() -> None:
    q07 = json.loads((ROOT / "ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json").read_text(encoding="utf-8"))
    by_scene = {r["scene_ref_id"]: r for r in q07["micro_scenes"]}
    slots = 0
    for r in PROJECTION["capabilities"]:
        n = r["sentence_count"]
        assert len(r["unit04_scene_ref_ids"]) == len(r["unit04_sentence_ids"]) == len(r["unit04_sentence_texts"]) == n
        assert len(set(r["unit04_scene_ref_ids"])) == n
        for ref, sid, text in zip(r["unit04_scene_ref_ids"], r["unit04_sentence_ids"], r["unit04_sentence_texts"], strict=True):
            src = by_scene[ref]
            assert src["bound_sentence_id"] == sid
            assert src["bound_sentence_text"] == text
            assert src["scene_family"] == r["scene_family"]
            assert src["a2_unlocked"] is False
        slots += n
    assert slots == 126


def test_u04ms02a_r1_scope_safety_and_replay_are_fail_closed_and_deterministic() -> None:
    scope, safety = PROJECTION["scope"], PROJECTION["safety"]
    assert scope["complete_multi_sentence_evidence_inventory"] is True
    assert scope["source_sentence_count_prelimited"] is False
    assert scope["form01_20_modified"] is False
    assert scope["canonical_grammar_modified"] is False
    assert scope["canonical_vocabulary_modified"] is False
    assert scope["canonical_chunk_modified"] is False
    assert scope["new_sentence_text_authored"] is False
    assert scope["raz_raw_text_included"] is False
    assert scope["raz_candidate_promoted"] is False
    assert scope["unit05_plus_grammar_opened"] is False
    assert scope["a2_unlocked"] is False
    assert safety["raw_raz_text_copied"] is False
    assert safety["source_inventory_sentence_cap_applied"] is False
    assert safety["raz_level_used_as_cefr_equivalence"] is False
    assert safety["reuse_unit_promoted_as_admission_gated_page_unit"] is False
    assert safety["unit05_plus_grammar_leak_count"] == 0
    assert safety["a2_plus_unlock_count"] == 0
    assert PROJECTION["extension_reference_summary"]["total_reference_count_gt_5"] == 4746
    assert PROJECTION["extension_reference_summary"]["direct_learner_language_materialized_in_this_revision"] is False
    replay = build_unit04_raz_aw_multi_sentence_micro_scene_capability(ROOT)
    assert replay == PROJECTION
    rb = compact_readback(PROJECTION)
    assert rb["complete_inventory_unit_count"] == 41964
    assert rb["complete_inventory_max_sentence_count"] == 635
    assert rb["unit04_direct_projection_eligible_page_count_2_to_5"] == 4634
    assert rb["unit04_extension_reference_total_gt_5"] == 4746
    assert rb["review_record_count"] == 7957
    assert rb["reading_authority_bridge_record_count"] == 7957
    assert rb["linkage_record_count"] == 58590
    assert rb["source_manifest_file_count"] == 50
    assert rb["raz_raw_text_copied"] is False
    assert rb["a2_plus_unlock_count"] == 0
    assert len(rb["projection_sha256"]) == 64
    print("U04MS02A_R1_READBACK=" + json.dumps(rb, sort_keys=True))
