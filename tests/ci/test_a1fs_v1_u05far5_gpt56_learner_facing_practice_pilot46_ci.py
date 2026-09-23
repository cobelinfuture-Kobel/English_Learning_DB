from __future__ import annotations

from product.a1fs_v1_2_1 import u05far5_gpt56_learner_facing_practice_pilot46 as far5


REPORT = far5.build_report()


def test_u05_far5_materializes_exact_operator_accepted_pilot46():
    assert REPORT["status"] == far5.STATUS
    assert REPORT["pilot_item_count"] == 46
    assert REPORT["core_count"] == 12
    assert REPORT["ket_count"] == 28
    assert REPORT["dictation_count"] == 6
    assert REPORT["operator_review"] == "PASS"


def test_u05_far5_preserves_coverage_and_asset_boundary():
    assert REPORT["core_frame_count"] == 6
    assert REPORT["ket_family_count"] == 14
    assert REPORT["text_executable_count"] == 26
    assert REPORT["asset_pending_count"] == 20
    assert REPORT["late_asset_dependent_item_count"] == 14
    assert REPORT["final_retention_item_count"] == 6


def test_u05_far5_locks_final_integrated_productive_output():
    assert REPORT["final_integrated_productive_item_count"] == 4
    assert REPORT["next_short_step"] == far5.NEXT_SHORT_STEP
