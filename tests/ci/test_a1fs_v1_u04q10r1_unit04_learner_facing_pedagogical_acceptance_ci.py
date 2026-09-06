from functools import lru_cache

from product.a1fs_v1_2_1 import (
    u04q10r1_unit04_learner_facing_pedagogical_acceptance as acceptance,
)
from ulga.builders import build_a1fs_v1_u04q10_questionbank_form_materialization as source


@lru_cache(maxsize=1)
def _report():
    return acceptance.build_acceptance_report()


def test_u04_q10r1_accepts_exact_twenty_forms_and_eight_hundred_learner_activities():
    report = _report()
    assert report["status"] == acceptance.PASS_STATUS
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


def test_u04_q10r1_preserves_q10_runtime_item_and_candidate_identity():
    report = _report()
    payload = source.build_export_payload()
    assert report["source_runtime_identity_sha256"] == acceptance._runtime_identity(payload["runtime_bindings"])
    assert report["source_item_identity_sha256"] == acceptance._item_identity(payload["questionbank_items"])
    assert len({row["selected_item_id"] for row in payload["runtime_bindings"]}) == 800
    assert all(len(row["candidate_ids"]) == 3 for row in payload["runtime_bindings"])
    assert report["claim_boundaries"]["source_800_runtime_rows_mutated"] is False
    assert report["claim_boundaries"]["source_selected_item_identities_mutated"] is False
    assert report["claim_boundaries"]["source_candidate_identities_mutated"] is False
    assert report["claim_boundaries"]["source_questionbank_items_mutated"] is False
    assert report["claim_boundaries"]["q10_redone"] is False


def test_u04_q10r1_preserves_a6_b10_c10_d8_e6_and_reuses_existing_renderer():
    report = _report()
    assert "u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization._activity_html" in report["renderer_reuse"]
    for form in report["learner_forms"]:
        assert form["section_count"] == 5
        assert [row["section"] for row in form["sections"]] == ["A", "B", "C", "D", "E"]
        assert {row["section"]: row["activity_count"] for row in form["sections"]} == {
            "A": 6, "B": 10, "C": 10, "D": 8, "E": 6,
        }
        assert len(form["activities"]) == 40
        acceptance.u01_learner._assert_no_answer_leak(form)
        html = acceptance.render_form_html(form)
        assert html.count('<article class="activity">') == 40
        lowered = html.casefold()
        for marker in acceptance.FORBIDDEN_LEARNER_MARKERS:
            assert marker.casefold() not in lowered


def test_u04_q10r1_keeps_all_task_relation_and_function_coverage_learner_representable():
    report = _report()
    assert report["acceptance"]["task_family_coverage"] == "10/10"
    assert report["acceptance"]["target_relation_coverage"] == "8/8"
    assert report["acceptance"]["communicative_function_coverage"] == "6/6"
    assert report["acceptance"]["selected_relation_answer_leak_count"] == 0
    assert report["presentation_fixes"]["engineering_prompt_projection_count"] == 800
    assert report["presentation_fixes"]["engineering_stimulus_metadata_suppression_count"] == 800
    assert report["presentation_fixes"]["selected_relation_answer_leak_count"] == 0


def test_u04_q10r1_at_remains_text_bound_only_and_prompts_are_natural():
    report = _report()
    payload = source.build_export_payload()
    source_items = {row["item_id"]: row for row in payload["questionbank_items"]}
    source_forms = payload["forms"]
    at_count = 0
    for form, source_form in zip(report["learner_forms"], source_forms):
        for activity, item_id in zip(form["activities"], source_form["item_ids"]):
            item = source_items[item_id]
            if item["relation_surface"] != "at":
                continue
            at_count += 1
            assert item["scene_ref_id"] is None
            assert item["task_family_id"] in source.AT_ALLOWED_FAMILIES
            assert item["communicative_function_id"] == source.AT_CF
            assert activity["options"] == []
            learner_text = (activity["stimulus"] + " " + activity["prompt"]).casefold()
            assert "scene_ref" not in learner_text
            assert "human-reviewable" not in learner_text
            assert "i is" not in learner_text
            assert "you is" not in learner_text
            assert "we is" not in learner_text
            assert "they is" not in learner_text
    assert at_count == 40
    assert report["acceptance"]["at_text_bound_activity_count"] == 40
    assert report["acceptance"]["at_scene_ref_render_count"] == 0
    assert report["presentation_fixes"]["at_scene_ref_render_count"] == 0


def test_u04_q10r1_context_gap_and_cumulative_carriers_are_visible_without_answer_leak():
    report = _report()
    payload = source.build_export_payload()
    source_items = {row["item_id"]: row for row in payload["questionbank_items"]}
    source_forms = payload["forms"]
    gap_count = 0
    integration_count = 0
    for form, source_form in zip(report["learner_forms"], source_forms):
        for activity, item_id in zip(form["activities"], source_form["item_ids"]):
            item = source_items[item_id]
            if item["task_family_id"] == "U04-TF07_CONTEXT_GAP":
                gap_count += 1
                assert "___" in activity["stimulus"]
            if item["task_family_id"] == "U04-TF08_U01_U02_U03_INTEGRATION":
                integration_count += 1
                assert all(marker in activity["stimulus"] for marker in ("One:", "Two:", "Reference:", "Position clue:"))
    assert gap_count > 0
    assert integration_count > 0


def test_u04_q10r1_scope_boundaries_and_next_step_remain_locked():
    report = _report()
    assert all(value is False for value in report["claim_boundaries"].values())
    assert report["next_short_step"] == acceptance.NEXT_SHORT_STEP
    assert report["claim_boundaries"]["pdf_materialized"] is False
    assert report["claim_boundaries"]["motion_directional_from_into_to_activated"] is False
    assert report["claim_boundaries"]["a2_unlocked"] is False
