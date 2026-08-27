from functools import lru_cache

from product.a1fs_v1_2_1 import (
    u03scfv2r1_unit03_twenty_form_learner_facing_acceptance as acceptance,
)
from ulga.builders import (
    build_a1fs_v1_u03scfv2_unit03_sentence_competence_forms_v2_800_materialization
    as source,
)


@lru_cache(maxsize=1)
def _report():
    return acceptance.build_acceptance_report()


def test_u03scfv2r1_accepts_all_twenty_forms_and_eight_hundred_learner_activities():
    report = _report()
    assert report["validation_status"] == acceptance.PASS_STATUS
    assert report["source_task_id"] == source.TASK_ID
    assert report["source_status"] == source.PASS_STATUS
    assert report["acceptance"]["form_count"] == 20
    assert report["acceptance"]["activity_count"] == 800
    assert report["acceptance"]["rendered_activity_count"] == 800
    assert report["acceptance"]["stage_activity_counts"] == {
        "GUIDED": 160,
        "REDUCED_SUPPORT": 160,
        "INDEPENDENT": 160,
        "TRANSFER": 160,
        "RETENTION": 160,
    }
    assert report["html_form_count"] == 20
    assert report["html_activity_count"] == 800


def test_u03scfv2r1_fixes_reference_chain_answer_leak_without_reselecting_runtime():
    report = _report()
    assert report["presentation_fixes"]["reference_chain_answer_leak_fixes"] == 80
    forms = report["learner_forms"]
    source_payload = source.build_export_payload()
    runtime = source_payload["runtime_bindings"]
    items = {
        row["item_id"]: row
        for row in source_payload["questionbank_delta"]["unit03_new_items"]
    }
    checked = 0
    for form in forms:
        rows = [row for row in runtime if row["form_number"] == form["form_ordinal"]]
        for activity, runtime_row in zip(form["activities"], rows):
            if runtime_row["questionbank_source"] != "UNIT03_DELTA":
                continue
            item = items[runtime_row["selected_item_id"]]
            if item["task_family"] != "TWO_SENTENCE_REFERENCE_CHAIN":
                continue
            assert "___ " in activity["stimulus"]
            assert item["correct_answer"] in activity["options"]
            assert "completes the second sentence" in activity["prompt"]
            checked += 1
    assert checked == 80


def test_u03scfv2r1_removes_semantically_duplicate_referent_choices():
    report = _report()
    assert report["presentation_fixes"]["referent_semantic_duplicate_fixes"] == 35
    source_payload = source.build_export_payload()
    runtime = source_payload["runtime_bindings"]
    items = {
        row["item_id"]: row
        for row in source_payload["questionbank_delta"]["unit03_new_items"]
    }
    checked = 0
    for form in report["learner_forms"]:
        rows = [row for row in runtime if row["form_number"] == form["form_ordinal"]]
        for activity, runtime_row in zip(form["activities"], rows):
            if runtime_row["questionbank_source"] != "UNIT03_DELTA":
                continue
            item = items[runtime_row["selected_item_id"]]
            if item["task_family"] != "PRONOUN_REFERENT_MATCH":
                continue
            keys = [acceptance._referent_key(value) for value in activity["options"]]
            assert len(keys) == len(set(keys))
            assert item["correct_answer"] in activity["options"]
            assert len(activity["options"]) >= 3
            checked += 1
    assert checked == 80


def test_u03scfv2r1_preserves_sections_stage_support_and_existing_renderer_reuse():
    report = _report()
    assert "_activity_html" in report["renderer_reuse"]
    forms = report["learner_forms"]
    assert [form["form_ordinal"] for form in forms] == list(range(1, 21))
    for form in forms:
        assert form["section_count"] == 5
        assert [section["section"] for section in form["sections"]] == acceptance.SECTION_ORDER
        assert all(section["activity_count"] == 8 for section in form["sections"])
        assert len(form["activities"]) == 40
        source.u01_learner._assert_no_answer_leak(form)
        html = acceptance.render_form_html(form)
        assert html.count('<article class="activity">') == 40
        lowered = html.casefold()
        for marker in acceptance.FORBIDDEN_LEARNER_MARKERS:
            assert marker.casefold() not in lowered


def test_u03scfv2r1_does_not_mutate_source_authorities_or_redo_q6_q9_q10():
    report = _report()
    assert report["claim_boundaries"] == {
        "source_800_runtime_rows_mutated": False,
        "source_selected_item_identities_mutated": False,
        "source_candidate_identities_mutated": False,
        "source_questionbank_items_mutated": False,
        "source_sentence_assets_mutated": False,
        "q6_redone": False,
        "q9_redone": False,
        "q10_redone": False,
        "second_questionbank_authority_created": False,
        "second_selector_created": False,
        "second_renderer_created": False,
        "parallel_sentence_asset_schema_created": False,
        "learner_state_mutated": False,
        "scoring_authority_mutated": False,
        "a2_unlocked": False,
    }
    assert report["source_package_sha256"] == source.build_export_payload()["package_sha256"]
