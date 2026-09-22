from __future__ import annotations

from product.a1fs_v1_2_1 import u05far4_gpt56_learner_facing_practice_materialization_preflight as far4


REPORT = far4.build_report()


def test_u05_far4_accounts_for_all_far2_slots():
    assert REPORT["status"] == far4.STATUS
    assert REPORT["practice_slot_denominator"] == 1632
    assert REPORT["gpt56_authoring_ready_slot_count"] == 1632
    assert REPORT["external_asset_free_slot_count"] == 816
    assert REPORT["external_asset_binding_required_count"] == 816
    assert REPORT["multi_source_bundle_review_required_count"] == 96


def test_u05_far4_locks_representative_pilot46():
    assert REPORT["pilot_item_count"] == 46
    assert REPORT["pilot_core_count"] == 12
    assert REPORT["pilot_ket_count"] == 28
    assert REPORT["pilot_dictation_count"] == 6
    assert REPORT["pilot_output_level_count"] == 4


def test_u05_far4_preserves_preflight_boundary():
    assert REPORT["learner_facing_item_count"] == 0
    assert REPORT["next_short_step"] == far4.NEXT_SHORT_STEP
