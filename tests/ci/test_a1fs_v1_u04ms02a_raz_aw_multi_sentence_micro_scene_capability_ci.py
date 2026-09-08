from __future__ import annotations

import json
from pathlib import Path

from product.a1fs_v1_2_1.u04ms02a_raz_aw_multi_sentence_micro_scene_capability import (
    CAPABILITY_COUNT,
    RAZ_SNAPSHOT,
    SENTENCE_COUNT_PATTERN,
    STATUS,
    build_unit04_raz_aw_multi_sentence_micro_scene_capability,
    compact_readback,
)

ROOT = Path(__file__).resolve().parents[2]
PROJECTION = build_unit04_raz_aw_multi_sentence_micro_scene_capability(ROOT)


def test_u04ms02a_raz_structural_evidence_is_text_free_and_non_authoritative() -> None:
    snapshot = json.loads((ROOT / RAZ_SNAPSHOT).read_text(encoding="utf-8"))
    assert snapshot["source_id"] == "RAZ_AW"
    assert snapshot["authority_role"] == "NON_AUTHORITATIVE_READING_CONTEXT_EXPOSURE_EVIDENCE"
    assert snapshot["canonical_promotion_allowed"] is False
    assert snapshot["learner_facing_authority"] is False
    assert snapshot["snapshot_policy"]["raw_raz_text_included"] is False
    assert snapshot["snapshot_policy"]["clean_text_included"] is False
    assert snapshot["snapshot_policy"]["source_titles_included"] is False
    assert snapshot["snapshot_policy"]["candidate_rows_promoted"] is False
    assert snapshot["snapshot_policy"]["structural_evidence_only"] is True
    assert len(snapshot["records"]) == 4
    forbidden = {"clean_text", "text", "title", "book_title", "source_text"}
    for row in snapshot["records"]:
        assert forbidden.isdisjoint(row)
        assert row["has_multi_sentence_unit"] is True
        assert row["sentence_count"] >= 2
        assert row["authority_status"] == "candidate_only"
        assert row["promotion_status"] == "not_promoted"


def test_u04ms02a_materializes_exact_36_capabilities_with_2_to_5_sentence_progression() -> None:
    assert PROJECTION["status"] == STATUS
    assert len(PROJECTION["capabilities"]) == CAPABILITY_COUNT == 36
    assert PROJECTION["capability_summary"]["sentence_count_distribution"] == {
        "2": 9,
        "3": 9,
        "4": 9,
        "5": 9,
    }
    expected_counts = [
        SENTENCE_COUNT_PATTERN[index % len(SENTENCE_COUNT_PATTERN)]
        for index in range(CAPABILITY_COUNT)
    ]
    assert [row["sentence_count"] for row in PROJECTION["capabilities"]] == expected_counts
    assert PROJECTION["capability_summary"]["min_sentences_per_capability"] == 2
    assert PROJECTION["capability_summary"]["max_sentences_per_capability"] == 5


def test_u04ms02a_every_materialized_sentence_resolves_exactly_to_q07_authority() -> None:
    q07 = json.loads(
        (ROOT / "ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json").read_text(
            encoding="utf-8"
        )
    )
    by_scene = {row["scene_ref_id"]: row for row in q07["micro_scenes"]}
    total_sentence_slots = 0
    for row in PROJECTION["capabilities"]:
        count = row["sentence_count"]
        assert len(row["unit04_scene_ref_ids"]) == count
        assert len(row["unit04_sentence_ids"]) == count
        assert len(row["unit04_sentence_texts"]) == count
        assert len(set(row["unit04_scene_ref_ids"])) == count
        assert row["coherence_basis"] in {
            "SCENE_FAMILY_AND_MEDIUM_SETTING",
            "SCENE_FAMILY",
        }
        for scene_ref, sentence_id, sentence_text in zip(
            row["unit04_scene_ref_ids"],
            row["unit04_sentence_ids"],
            row["unit04_sentence_texts"],
            strict=True,
        ):
            source = by_scene[scene_ref]
            assert source["bound_sentence_id"] == sentence_id
            assert source["bound_sentence_text"] == sentence_text
            assert source["scene_family"] == row["scene_family"]
            assert source["a2_unlocked"] is False
        total_sentence_slots += count
    assert total_sentence_slots == 126


def test_u04ms02a_scope_boundaries_and_replay_are_fail_closed_and_deterministic() -> None:
    scope = PROJECTION["scope"]
    safety = PROJECTION["safety"]
    assert scope["form01_20_modified"] is False
    assert scope["canonical_grammar_modified"] is False
    assert scope["canonical_vocabulary_modified"] is False
    assert scope["canonical_chunk_modified"] is False
    assert scope["new_sentence_text_authored"] is False
    assert scope["raz_raw_text_included"] is False
    assert scope["raz_candidate_promoted"] is False
    assert scope["unit05_plus_grammar_opened"] is False
    assert scope["a2_unlocked"] is False
    assert safety["raz_canonical_promotion_allowed"] is False
    assert safety["raw_raz_text_copied"] is False
    assert safety["new_global_scene_identity_count"] == 0
    assert safety["unit05_plus_grammar_leak_count"] == 0
    assert safety["a2_plus_unlock_count"] == 0
    assert PROJECTION["capability_summary"]["scene_family_count"] > 0
    assert PROJECTION["capability_summary"]["distinct_unit04_sentence_ids_used"] > 0

    replay = build_unit04_raz_aw_multi_sentence_micro_scene_capability(ROOT)
    assert replay == PROJECTION
    assert len(PROJECTION["projection_sha256"]) == 64
    readback = compact_readback(PROJECTION)
    assert readback["capability_count"] == 36
    assert readback["sentence_count_distribution"] == {"2": 9, "3": 9, "4": 9, "5": 9}
    assert readback["raz_structural_snapshot_record_count"] == 4
    assert readback["raz_raw_text_copied"] is False
    assert readback["a2_plus_unlock_count"] == 0
    print("U04MS02A_RAZ_AW_READBACK=" + json.dumps(readback, sort_keys=True))
