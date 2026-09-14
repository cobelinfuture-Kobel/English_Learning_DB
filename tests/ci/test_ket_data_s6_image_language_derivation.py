from __future__ import annotations

from pathlib import Path

import pytest

from builders.build_ket_data_s6_image_language_derivation import materialize
from validators.validate_ket_data_s6_image_language_derivation import STATUS, validate

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def s6():
    return materialize(ROOT)


def test_ket_data_s6_core_bridge_acceptance():
    r = validate(ROOT)
    assert r["status"] == STATUS
    assert r["scene_source_count"] == 15
    assert r["scene_images_with_a1_asset"] == 15
    assert r["language_asset_count"] == 16
    assert r["a1_asset_count"] == 15
    assert r["a1_plus_asset_count"] == 1
    assert r["s5_fact_lineage"] is True
    assert r["grammar_dual_identity_bridge"] is True
    assert r["vocabulary_authority_binding"] is True
    assert r["live_model_call_count"] == 0
    assert r["new_image_identity_count"] == 0
    assert r["learner_facing"] is False


def test_ket_data_s6_semantic_key_fact_refs_and_plural_transform(s6):
    rows = {x["language_asset_id"]: x for x in s6["language_assets"]}
    table = rows["KET_S6_LANG_000001"]
    assert table["image_asset_id"] == "KET_IMG_001056"
    assert table["sentence"] == "There is a table."
    assert table["fact_refs"] == ["KET_IMG_001056#object:table"]
    child = rows["KET_S6_LANG_000004"]
    assert child["sentence"] == "There is a child."
    assert child["fact_refs"] == ["KET_IMG_001059#participant:children"]
    assert child["vocabulary_bindings"][0]["transform"] == "PLURAL_TO_SINGULAR_MEMBER"
    assert child["vocabulary_bindings"][0]["surface"] == "child"
    assert all("[" not in ref and "]" not in ref for row in rows.values() for ref in row["fact_refs"])


def test_ket_data_s6_grammar_egp_vocab_and_level_binding(s6):
    for row in s6["language_assets"]:
        assert row["pattern_refs"]
        assert row["grammar_refs"]
        assert row["egp_source_refs"]
        assert len(row["grammar_refs"]) == len(row["egp_source_refs"])
        assert row["vocabulary_refs"]
        assert all(binding["vocabulary_refs"] for binding in row["vocabulary_bindings"])
        assert all(binding["vocabulary_levels"] == ["A1"] for binding in row["vocabulary_bindings"])
    plus = [x for x in s6["language_assets"] if x["derivation_target_level"] == "A1_plus"]
    assert len(plus) == 1
    assert plus[0]["image_asset_id"] == "KET_IMG_001065"
    assert plus[0]["sentence"] == "There is a man on the bed."
    assert "KET_IMG_001065#relation:man|on|bed" in plus[0]["fact_refs"]
    assert plus[0]["sentence_word_count"] == 7


def test_ket_data_s6_frozen_gpt56_reproducibility_and_nonlearner_boundary(s6):
    again = materialize(ROOT)
    assert again == s6
    assert s6["semantic_engine_contract"]["model"] == "GPT-5.6 Sol"
    assert s6["semantic_engine_contract"]["prompt_contract_version"] == "KET_S6_V1"
    assert s6["semantic_engine_contract"]["live_model_call_in_ci"] is False
    assert s6["semantic_engine_contract"]["frozen_candidate_required"] is True
    assert s6["language_asset_policy"]["learner_facing"] is False
    assert s6["language_asset_policy"]["question_generation_allowed"] is False
    assert all(row["candidate_source"] == "GPT-5.6_SOL_FROZEN_CANDIDATE" for row in s6["language_assets"])
    assert all(row["learner_facing"] is False for row in s6["language_assets"])
