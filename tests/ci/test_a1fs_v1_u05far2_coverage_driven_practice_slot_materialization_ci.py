from __future__ import annotations

from product.a1fs_v1_2_1 import u05far2_coverage_driven_practice_slot_materialization as far2


REPORT = far2.build_report()


def test_u05_far2_materializes_exact_coverage_floor():
    assert REPORT["status"] == far2.STATUS
    assert REPORT["practice_slot_count"] == 1632
    assert REPORT["core_grammar_slot_count"] == 480
    assert REPORT["ket_adapted_slot_count"] == 672
    assert REPORT["delayed_dictation_slot_count"] == 480


def test_u05_far2_materializes_coverage_driven_sets_not_fixed_forms():
    assert REPORT["practice_set_count"] == 97
    assert REPORT["reader_study_set_count"] == 15
    assert REPORT["reader_study_slot_count"] == 360
    assert REPORT["reader_mode_touchpoint_count"] == 1080


def test_u05_far2_meets_core_and_ket_quantity_floors():
    assert REPORT["subject_class_minimum"] >= 48
    assert REPORT["place_relation_minimum"] >= 24
    assert REPORT["ket_family_minimum"] == 48


def test_u05_far2_materializes_spaced_dictation_coverage():
    assert REPORT["dictation_d1_episode_count"] == 360
    assert REPORT["dictation_d2_episode_count"] == 120


def test_u05_far2_remains_metadata_only():
    assert REPORT["learner_facing_question_text_materialized"] is False
    assert REPORT["next_short_step"] == far2.NEXT_SHORT_STEP
