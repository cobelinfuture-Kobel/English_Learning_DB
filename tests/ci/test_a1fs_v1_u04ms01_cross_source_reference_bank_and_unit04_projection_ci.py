from __future__ import annotations

import json
from pathlib import Path

from product.a1fs_v1_2_1.u04ms01_cross_source_reference_bank_and_unit04_projection import (
    STATUS,
    build_unit04_reference_projection,
    compact_readback,
)

ROOT = Path(__file__).resolve().parents[2]
PROJECTION = build_unit04_reference_projection(ROOT)


def test_u04ms01_cross_source_registry_is_resolved_and_roles_are_bounded() -> None:
    assert PROJECTION["status"] == STATUS
    assert PROJECTION["source_resolution"]["unresolved_public_integration_anchor_count"] == 0
    registry = {row["source_id"]: row for row in PROJECTION["source_registry"]}
    assert set(registry) == {
        "EGP",
        "EVP",
        "NGSL_SFI",
        "GLOBAL_CHUNK_AUTHORITY",
        "CAMBRIDGE_OFFICIAL",
        "IELTS_OFFICIAL",
        "KET_FOUR_SKILL_PREREQUISITE",
        "KET99_SRT",
        "RAZ_AW",
        "UNIT01_04_AUTHORITY",
    }
    assert registry["EGP"]["authority_role"] == "GRAMMAR_CEFR_AUTHORITY"
    assert registry["EVP"]["authority_role"] == "LEXICAL_SENSE_CEFR_AUTHORITY"
    assert registry["NGSL_SFI"]["canonical_promotion_allowed"] is False
    assert registry["KET99_SRT"]["canonical_promotion_allowed"] is False
    assert registry["RAZ_AW"]["canonical_promotion_allowed"] is False
    assert registry["IELTS_OFFICIAL"]["authority_role"] == "TASK_MECHANICS_REFERENCE_ONLY"
    assert registry["UNIT01_04_AUTHORITY"]["learner_facing_authority"] is True


def test_u04ms01_current_unit_authoritative_denominators_are_exact() -> None:
    assets = PROJECTION["unit04_authoritative_asset_roles"]
    assert assets["vocabulary"]["direct_active_location_carriers"] == 29
    assert assets["vocabulary"]["new_global_vocabulary_identities"] == 0
    assert assets["vocabulary"]["cumulative_learned_vocabulary_denominator"] is None

    assert assets["chunk_surfaces"] == {
        "DIRECT_ACTIVE": 40,
        "REVIEW_REUSE": 50,
        "CUMULATIVE": 90,
    }
    assert assets["place_phrases"]["TARGET_CURRENT_POOL"] == 37
    assert assets["place_phrases"]["SUPPORT_CURRENT_POOL"] == 8
    assert assets["place_phrases"]["CURRENT_TOTAL"] == 45

    assert assets["exact_sentence_frames"]["DIRECT_ACTIVE"] == 8
    assert assets["exact_sentence_frames"]["REVIEW_REUSE"] == 15
    assert assets["exact_sentence_frames"]["CUMULATIVE"] == 23
    assert assets["exact_sentence_frames"]["CANONICAL_PATTERN_FAMILIES"] == 7

    assert assets["sentence_assets"]["DIRECT_ACTIVE"] == 96
    assert assets["sentence_assets"]["REVIEW_REUSE"] == 26514
    assert assets["sentence_assets"]["CUMULATIVE"] == 26610
    assert assets["sentence_assets"]["TARGET_NEW"] == 64
    assert assets["sentence_assets"]["SUPPORT_NEW"] == 32


def test_u04ms01_reference_pools_are_queryable_but_not_misreported_as_learned() -> None:
    reference = PROJECTION["reference_only_pools"]
    vocab = reference["vocabulary"]
    chunks = reference["chunks"]
    assert vocab["active_row_count"] > 0
    assert vocab["a1_reference_row_count"] > 0
    assert sum(vocab["requested_pos_counts"].values()) > 0
    assert chunks["generator_safe_row_count"] > 0
    assert chunks["a1_reference_row_count"] > 0
    assert chunks["requested_category_proxies"]["noun_phrases"]["count"] > 0
    assert chunks["requested_category_proxies"]["time_phrases"]["count"] > 0
    assert "not all noun phrases" in chunks["requested_category_proxies"]["noun_phrases"]["rule"]
    assert "not all verb phrases" in chunks["requested_category_proxies"]["verb_phrases"]["rule"]
    assert PROJECTION["scope"]["reference_counts_are_additive"] is False


def test_u04ms01_fails_closed_on_curriculum_promotion_and_is_deterministic() -> None:
    boundaries = PROJECTION["reference_authority_boundaries"]
    assert PROJECTION["scope"]["a2_unlocked"] is False
    assert PROJECTION["scope"]["unit05_plus_grammar_learner_facing_allowed"] is False
    assert PROJECTION["scope"]["canonical_authority_mutated"] is False
    assert PROJECTION["scope"]["learner_content_authored"] is False
    assert boundaries["unit05_plus_grammar_leak_count"] == 0
    assert boundaries["a2_plus_unlock_count"] == 0
    assert boundaries["ielts_language_import_allowed"] is False
    assert boundaries["ket99_srt_canonical_promotion_allowed"] is False
    assert boundaries["raz_aw_canonical_promotion_allowed"] is False

    replay = build_unit04_reference_projection(ROOT)
    assert replay == PROJECTION
    assert len(PROJECTION["projection_sha256"]) == 64
    readback = compact_readback(PROJECTION)
    assert readback["cumulative_sentence_assets"] == 26610
    assert readback["cumulative_chunks"] == 90
    assert readback["cumulative_exact_frames"] == 23
    assert readback["unresolved_sources"] == 0
    print("U04MS01_REFERENCE_PROJECTION_READBACK=" + json.dumps(readback, sort_keys=True))
