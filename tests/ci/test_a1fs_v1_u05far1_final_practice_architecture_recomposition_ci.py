from __future__ import annotations

from product.a1fs_v1_2_1 import u05far1_final_practice_architecture_recomposition as far1


REPORT = far1.build_report()


def test_u05_far1_removes_fixed_20x40_as_final_authority():
    assert REPORT["status"] == far1.STATUS
    assert REPORT["fixed_form_count"] is False
    assert REPORT["fixed_total_question_cap"] is False


def test_u05_far1_has_coverage_driven_practice_floor():
    assert REPORT["core_grammar_task_floor"] == 480
    assert REPORT["ket_family_count"] == 14
    assert REPORT["ket_adapted_task_floor"] == 672
    assert REPORT["dictation_event_floor"] == 480
    assert REPORT["minimum_total_practice_events"] == 1632


def test_u05_far1_keeps_all_reader360_study_reachable():
    assert REPORT["reader_study_episode_count"] == 360
    assert REPORT["reader_mode_touchpoint_floor"] == 1080


def test_u05_far1_keeps_a2_native_demand_locked():
    assert REPORT["a2_native_task_demand_unlocked"] is False
    assert REPORT["next_short_step"] == far1.NEXT_SHORT_STEP
