from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest

from builders.build_ket_data_s7_image_multiple_task_family_projection import materialize
from validators.validate_ket_data_s7_image_multiple_task_family_projection import STATUS, validate

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def s7():
    return materialize(ROOT)


def test_ket_data_s7_core_projection_acceptance():
    r = validate(ROOT)
    assert r["status"] == STATUS
    assert r["source_language_asset_count"] == 16
    assert r["source_image_asset_count"] == 15
    assert r["task_shell_count"] == 80
    assert r["a1_task_shell_count"] == 75
    assert r["a1_plus_task_shell_count"] == 5
    assert r["response_mode_count"] == 5
    assert r["derived_task_family_count"] == 5
    assert r["s3_five_layer_handshake"] is True
    assert r["s6_authority_lineage_preserved"] is True
    assert r["canonical_task_family_promotion_count"] == 0
    assert r["learner_facing_task_count"] == 0
    assert r["question_bank_item_count"] == 0
    assert r["new_image_identity_count"] == 0
    assert r["new_language_identity_count"] == 0
    assert r["live_model_call_count"] == 0


def test_ket_data_s7_one_language_asset_projects_five_response_modes(s7):
    rows = [x for x in s7["task_shells"] if x["source_language_asset_id"] == "KET_S6_LANG_000001"]
    assert len(rows) == 5
    assert {x["s3_classification"]["response_mode"] for x in rows} == {
        "SELECT",
        "MATCH",
        "STRUCTURED_ENTRY",
        "TEXT_ENTRY",
        "SPEAK",
    }
    assert {x["derived_task_family"] for x in rows} == {
        "IMAGE_SENTENCE_SELECT",
        "IMAGE_SENTENCE_MATCH",
        "IMAGE_FACT_STRUCTURED_ENTRY",
        "IMAGE_DESCRIPTION_TEXT_ENTRY",
        "IMAGE_DESCRIPTION_SPEAK",
    }
    assert {x["source_image_asset_id"] for x in rows} == {"KET_IMG_001056"}
    assert {x["source_sentence"] for x in rows} == {"There is a table."}


def test_ket_data_s7_preserves_s3_taxonomy_boundary_without_false_canonical_promotion(s7):
    taxonomy = __import__("json").loads(
        (ROOT / "data" / "ket" / "ket_s3_unified_assessment_taxonomy.json").read_text(encoding="utf-8")
    )
    layers = taxonomy["layers"]
    response_modes = set(layers["response_mode"]["values"])
    modalities = set(layers["stimulus_modality"]["values"])
    capabilities = set(layers["assessment_capability"]["values"])
    response_formats = set(layers["response_format"]["values"])
    for row in s7["task_shells"]:
        c = row["s3_classification"]
        assert c["response_mode"] in response_modes
        assert c["stimulus_modality"] in modalities
        assert c["response_format"] in response_formats
        assert all(x in capabilities for x in c["assessment_capabilities"])
        assert c["task_family_ref"] is None
        assert c["task_family_binding_status"] == "UNBOUND_DERIVED_PRACTICE"
        assert row["current_ket_canonical_mechanic"] is False
        assert row["authority_scope"] == "DERIVED_PRACTICE_NOT_CURRENT_KET_CANONICAL"


def test_ket_data_s7_same_image_can_have_multiple_language_levels_and_task_shells(s7):
    by_image = defaultdict(list)
    for row in s7["task_shells"]:
        by_image[row["source_image_asset_id"]].append(row)
    bedroom = by_image["KET_IMG_001065"]
    assert len(bedroom) == 10
    assert {x["derivation_target_level"] for x in bedroom} == {"A1", "A1_plus"}
    assert {x["source_language_asset_id"] for x in bedroom} == {"KET_S6_LANG_000010", "KET_S6_LANG_000016"}
    assert {x["s3_classification"]["response_mode"] for x in bedroom} == {
        "SELECT",
        "MATCH",
        "STRUCTURED_ENTRY",
        "TEXT_ENTRY",
        "SPEAK",
    }


def test_ket_data_s7_lineage_and_nonlearner_boundary_are_deterministic(s7):
    again = materialize(ROOT)
    assert again == s7
    for row in s7["task_shells"]:
        lineage = row["authority_lineage"]
        assert lineage["image_asset_id"] == row["source_image_asset_id"]
        assert lineage["language_asset_id"] == row["source_language_asset_id"]
        assert lineage["fact_refs"]
        assert all(x.startswith(row["source_image_asset_id"] + "#") for x in lineage["fact_refs"])
        assert lineage["pattern_refs"]
        assert lineage["grammar_refs"]
        assert lineage["egp_source_refs"]
        assert lineage["vocabulary_refs"]
        assert row["learner_facing"] is False
        assert row["question_bank_item"] is False
        assert row["materialization_status"] == "TASK_SHELL_ONLY"
