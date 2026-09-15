from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from builders.build_ket_data_s8_task_origin_governance import materialize
from validators.validate_ket_data_s8_task_origin_governance import STATUS, validate

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def s8():
    return materialize(ROOT)


def test_ket_data_s8_core_origin_governance_acceptance():
    r = validate(ROOT)
    assert r["status"] == STATUS
    assert r["governed_record_count"] == 1440
    assert r["source_exact_count"] == 1360
    assert r["a1fs_derived_count"] == 80
    assert r["derived_a1_count"] == 75
    assert r["derived_a1_plus_count"] == 5
    assert r["supplementary_practice_excluded_count"] == 92
    assert r["derived_image_asset_count"] == 15
    assert r["derived_source_task_copy_count"] == 0
    assert r["derived_source_wording_copy_count"] == 0
    assert r["derived_current_ket_canonical_promotion_count"] == 0
    assert r["learner_facing_count"] == 0
    assert r["question_bank_item_count"] == 0
    assert r["new_image_identity_count"] == 0
    assert r["new_language_identity_count"] == 0
    assert r["live_model_call_count"] == 0


def test_ket_data_s8_source_exact_is_reference_only_and_never_mislabeled_derived(s8):
    exact = [x for x in s8["origin_records"] if x["task_origin"] == "SOURCE_EXACT"]
    assert len(exact) == 1360
    assert len({x["source_item_id"] for x in exact}) == 1360
    for row in exact:
        assert row["source_item_id"]
        assert row["derived_from"] == []
        assert row["source_task_reference_only"] is True
        assert row["source_task_copied"] is False
        assert row["source_wording_copied"] is False
        assert row["generation_model"] is None
        assert row["generation_method"] is None
        assert row["target_level"] is None
        assert row["authority_scope"] == "CURRENT_KET_CANONICAL_MECHANIC"
        assert row["current_ket_canonical_mechanic"] is True


def test_ket_data_s8_a1fs_derived_is_reauthored_from_image_evidence_not_source_task_copy(s8):
    derived = [x for x in s8["origin_records"] if x["task_origin"] == "A1FS_DERIVED"]
    assert len(derived) == 80
    assert Counter(x["target_level"] for x in derived) == Counter({"A1": 75, "A1_plus": 5})
    assert len({x["s7_task_shell_id"] for x in derived}) == 80
    assert len({x["derived_from"][0] for x in derived}) == 15
    for row in derived:
        assert row["source_item_id"] is None
        assert len(row["derived_from"]) == 1
        assert row["derived_from"][0].startswith("KET_IMG_")
        assert row["source_task_reference_only"] is False
        assert row["source_task_copied"] is False
        assert row["source_wording_copied"] is False
        assert row["generation_model"] is None
        assert row["generation_method"] == "DETERMINISTIC_S7_PROJECTION"
        assert row["authority_validation"] == "REQUIRED"
        assert row["authority_validation_status"] == "PASS"
        assert row["authority_scope"] == "A1FS_DERIVED_FROM_KET_IMAGE_EVIDENCE"
        assert row["current_ket_canonical_mechanic"] is False
        assert row["authority_lineage"]["image_asset_id"] == row["derived_from"][0]
        assert row["authority_lineage"]["language_asset_id"] == row["source_language_asset_id"]


def test_ket_data_s8_supplementary_practice_stays_outside_binary_registry_and_build_is_deterministic(s8):
    assert len(s8["excluded_supplementary_practice_item_ids"]) == 92
    assert len(set(s8["excluded_supplementary_practice_item_ids"])) == 92
    exact_ids = {x["source_item_id"] for x in s8["origin_records"] if x["task_origin"] == "SOURCE_EXACT"}
    assert exact_ids.isdisjoint(s8["excluded_supplementary_practice_item_ids"])
    assert {x["task_origin"] for x in s8["origin_records"]} == {"SOURCE_EXACT", "A1FS_DERIVED"}
    assert materialize(ROOT) == s8
