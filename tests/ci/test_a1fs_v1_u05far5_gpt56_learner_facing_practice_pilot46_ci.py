from __future__ import annotations

from product.a1fs_v1_2_1 import u05far5_gpt56_learner_facing_practice_pilot46_validator as far5


REPORT = far5.build_report()


def test_u05_far5_operator_accepted_pilot46_counts_and_reviews():
    assert REPORT["status"] == far5.STATUS
    assert REPORT["item_count"] == 46
    assert REPORT["core_count"] == 12
    assert REPORT["ket_count"] == 28
    assert REPORT["dictation_count"] == 6
    assert REPORT["review_pass_count"] == 46


def test_u05_far5_execution_gates_preserve_asset_boundary():
    assert REPORT["text_executable_count"] == 26
    assert REPORT["asset_pending_count"] == 20


def test_u05_far5_productive_scaffold_ends_in_integrated_output():
    assert REPORT["final_integrated_productive_count"] == 4
    assert REPORT["ket_family_count"] == 14
    assert REPORT["core_frame_count"] == 6


def test_u05_far5_stops_before_full_1632_materialization():
    assert REPORT["next_short_step"] == far5.NEXT_SHORT_STEP
