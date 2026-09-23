from __future__ import annotations

from product.a1fs_v1_2_1 import u05far6_full1632_materialization_preflight as far6


REPORT = far6.build_report()


def test_u05_far6_revalidates_full_denominator_and_lineage():
    assert REPORT["status"] == far6.STATUS
    assert REPORT["practice_slot_denominator"] == 1632
    assert REPORT["unique_slot_id_count"] == 1632
    assert REPORT["practice_set_count"] == 97
    assert REPORT["reader_lineage_missing_count"] == 0


def test_u05_far6_revalidates_authoring_and_asset_boundary():
    assert REPORT["gpt56_authoring_ready_slot_count"] == 1632
    assert REPORT["external_asset_free_after_authoring_count"] == 816
    assert REPORT["external_asset_required_for_execution_count"] == 816
    assert REPORT["multi_source_bundle_review_required_count"] == 96


def test_u05_far6_preserves_preflight_only_boundary():
    assert REPORT["learner_facing_items_materialized_in_far6"] == 0
    assert REPORT["next_short_step"] == far6.NEXT_SHORT_STEP
