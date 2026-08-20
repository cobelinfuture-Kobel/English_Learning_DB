from __future__ import annotations

import json

from product.a1fs_v1_2_1 import (
    u01qb18h_r2r2_unit01_sentence_pool_driven_full240_closeout as product,
)
from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import (
    build_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
    as builder,
)


def _activity(activity_id: str = "U01-FORM-12-S03-A04", scene: str = "SCENE-X") -> dict[str, object]:
    return {
        "activity_id": activity_id,
        "scene_ref_id": scene,
        "skill": "WRITING",
        "task_angle": "COMPLETE_SENTENCE_PRODUCTION",
        "scored": 1,
    }


def _item(activity_id: str = "U01-FORM-12-S03-A04", scene: str = "SCENE-X") -> dict[str, object]:
    return {
        "item_id": "R2R2-EXACT-PF14",
        "pattern_family_id": builder.u10.PF14,
        "production_activity_id": activity_id,
        "production_scene_ref_id": scene,
        "lexical_slots": {"noun": "book", "context_id": "U01-C2-HOME-TOY-BOX"},
        "stimulus": "item: a book | scene: HOME",
        "prompt": "Write one complete sentence about this item in the scene.",
        "options": [],
        "scoring_mode": "FEATURE_RUBRIC",
        "response_contract": {
            "scoring_mode": "FEATURE_RUBRIC",
            "capture_enabled": True,
            "human_review_fallback": True,
        },
    }


def _row(item: dict[str, object]) -> dict[str, object]:
    return {
        "item_id": str(item["item_id"]),
        "skill": "WRITING",
        "pattern_family_id": str(item["pattern_family_id"]),
        "capture_enabled": 1,
        "private_item_json": json.dumps(item),
    }


def _exact_families() -> set[str]:
    values = set(builder.EXPECTED_PRODUCTION_FAMILY_COUNTS)
    if hasattr(builder, "PF09_FAMILY"):
        values.add(str(builder.PF09_FAMILY))
    return values


def test_exact_slot_lineage_accepts_only_its_materialized_activity_and_scene() -> None:
    families = _exact_families()
    item = _item()
    assert product._r2r2_exact_slot_lineage_matches(
        _activity(), item, exact_scene_families=families
    ) is True
    assert product._r2r2_exact_slot_lineage_matches(
        _activity(activity_id="U01-FORM-12-S03-A03"),
        item,
        exact_scene_families=families,
    ) is False
    assert product._r2r2_exact_slot_lineage_matches(
        _activity(scene="SCENE-Y"), item, exact_scene_families=families
    ) is False


def test_legacy_exact_family_row_without_activity_lineage_fails_closed() -> None:
    item = _item()
    item.pop("production_activity_id")
    assert product._r2r2_exact_slot_lineage_matches(
        _activity(), item, exact_scene_families=_exact_families()
    ) is False


def test_non_r2r2_family_is_not_constrained_by_exact_activity_lineage() -> None:
    item = _item()
    item["pattern_family_id"] = builder.u13.PF07
    item.pop("production_activity_id")
    item.pop("production_scene_ref_id")
    assert product._r2r2_exact_slot_lineage_matches(
        _activity(), item, exact_scene_families=_exact_families()
    ) is True


def test_acceptance_context_applies_lineage_after_canonical_human_review_scoring_and_restores() -> None:
    before = matching.candidate_preserves_scoring_class
    item = _item()
    row = _row(item)
    scoring = {str(item["item_id"]): matching.SCORING_CLASS_HUMAN_REVIEW}

    with product.r2r2_candidate_compatibility_hooks():
        active = matching.candidate_preserves_scoring_class
        assert active is not before
        assert active(_activity(), row, scoring) is True
        assert (
            active(
                _activity(activity_id="U01-FORM-12-S03-A03"),
                row,
                scoring,
            )
            is False
        )

    assert matching.candidate_preserves_scoring_class is before
