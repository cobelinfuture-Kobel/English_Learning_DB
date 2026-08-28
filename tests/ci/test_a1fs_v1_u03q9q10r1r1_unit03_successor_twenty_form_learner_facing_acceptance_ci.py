from functools import lru_cache

from product.a1fs_v1_2_1 import (
    u03q9q10r1r1_unit03_successor_twenty_form_learner_facing_acceptance as acceptance,
)
from ulga.builders import (
    build_a1fs_v1_u03q9q10r1_unit03_form_pedagogical_contract_20x40_6_10_10_8_6
    as source,
)


@lru_cache(maxsize=1)
def _report():
    return acceptance.build_acceptance_report()


def test_successor_source_identity_and_scope_are_preserved():
    report = _report()
    assert report["validation_status"] == acceptance.PASS_STATUS
    assert report["source_task_id"] == source.TASK_ID
    assert report["source_status"] == source.PASS_STATUS
    assert len(report["source_package_sha256"]) == 64
    assert len(report["source_runtime_identity_sha256"]) == 64


def test_twenty_forms_and_exact_a_b_c_d_e_denominators_are_learner_visible():
    report = _report()
    assert report["acceptance"]["form_count"] == 20
    assert report["acceptance"]["activity_count"] == 800
    assert report["acceptance"]["rendered_activity_count"] == 800
    forms = report["learner_forms"]
    assert len(forms) == 20
    for form in forms:
        assert form["learner_visible_activity_count"] == 40
        assert {row["section"]: row["activity_count"] for row in form["sections"]} == {
            "A": 6, "B": 10, "C": 10, "D": 8, "E": 6,
        }


def test_progression_stage_denominator_and_passage_lengths_are_exact():
    report = _report()
    assert report["acceptance"]["stage_activity_counts"] == {
        "GUIDED": 160,
        "REDUCED_SUPPORT": 160,
        "INDEPENDENT": 160,
        "TRANSFER": 160,
        "RETENTION": 160,
    }
    per_form = report["pedagogical_acceptance"]["per_form"]
    for form_number in range(1, 21):
        expected = source.PASSAGE_SENTENCE_COUNT_BY_STAGE[source._stage(form_number)]
        assert per_form[form_number]["section_e_passage_sentence_count"] == expected


def test_b_c_e_core_pedagogical_acceptance_is_proven_for_every_form():
    pedagogy = _report()["pedagogical_acceptance"]
    assert pedagogy["forms_validated"] == 20
    assert pedagogy["section_b_all_forms_proven"] is True
    assert pedagogy["section_c_all_items_same_question_integrated"] is True
    assert pedagogy["section_e_connected_passage_questions"] == 120
    for row in pedagogy["per_form"].values():
        assert set(row["section_b_evidence"]) >= {
            "sentence_manipulation", "sentence_correction", "sentence_production",
        }
        assert row["section_c_integrated_item_count"] == 10
        assert row["section_e_connected_question_count"] == 6


def test_all_twenty_forms_render_via_existing_unit01_activity_renderer():
    report = _report()
    assert report["html_form_count"] == 20
    assert report["html_activity_count"] == 800
    for form in report["learner_forms"]:
        html = acceptance.render_form_html(form)
        assert html.count('<article class="activity">') == 40
        lowered = html.casefold()
        for marker in acceptance.FORBIDDEN_LEARNER_MARKERS:
            assert marker.casefold() not in lowered


def test_source_authority_is_read_only_and_pdf_q11_unit04_a2_remain_closed():
    boundaries = _report()["claim_boundaries"]
    assert all(value is False for value in boundaries.values())


def test_next_step_is_final_package_reconciliation_outside_current_acceptance():
    assert _report()["next_short_step"] == acceptance.NEXT_SHORT_STEP
