from __future__ import annotations

from product.a1fs_v1_2_1 import u05far3_learner_facing_practice_materialization_contract as far3


REPORT = far3.build_report()


def test_u05_far3_preserves_full_far2_denominator():
    assert REPORT["status"] == far3.STATUS
    assert REPORT["practice_slot_denominator"] == 1632
    assert REPORT["core_grammar_slot_count"] == 480
    assert REPORT["ket_adapted_slot_count"] == 672
    assert REPORT["dictation_slot_count"] == 480
    assert REPORT["reader_study_slot_count"] == 360


def test_u05_far3_contracts_all_fourteen_ket_families():
    assert REPORT["ket_family_contract_count"] == 14
    assert REPORT["audio_required_family_count"] == 5
    assert REPORT["visual_required_family_count"] == 3


def test_u05_far3_requires_gpt56_authorship_and_review_without_materializing_content():
    assert REPORT["required_gpt56_review_field_count"] == 6
    assert REPORT["learner_facing_items_materialized"] is False
    assert REPORT["python_learner_facing_authoring_allowed"] is False


def test_u05_far3_guards_against_artifact_proliferation():
    assert REPORT["final_learner_facing_authority_file_cap"] == 3


def test_u05_far3_stops_before_actual_learner_facing_materialization():
    assert REPORT["next_short_step"] == far3.NEXT_SHORT_STEP
