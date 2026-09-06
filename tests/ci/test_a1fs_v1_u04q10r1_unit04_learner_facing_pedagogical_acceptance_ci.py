import json
from functools import lru_cache

import pytest

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
    assert report["acceptance"]["answer_key_binding_count"] == 800
    assert len(report["answer_key_bindings"]) == 800
    assert len({
        (row["form_number"], row["question_number"])
        for row in report["answer_key_bindings"]
    }) == 800
    assert report["html_form_count"] == 20
    assert report["html_activity_count"] == 800


def test_u04_q10r1_preserves_q10_runtime_item_and_candidate_identity():
    report = _report()
    payload = source.build_export_payload()
    assert report["source_runtime_identity_sha256"] == acceptance._runtime_identity(
        payload["runtime_bindings"]
    )
    assert report["source_item_identity_sha256"] == acceptance._item_identity(
        payload["questionbank_items"]
    )
    assert len({row["selected_item_id"] for row in payload["runtime_bindings"]}) == 800
    assert all(len(row["candidate_ids"]) == 3 for row in payload["runtime_bindings"])
    assert report["claim_boundaries"]["source_800_runtime_rows_mutated"] is False
    assert report["claim_boundaries"]["source_selected_item_identities_mutated"] is False
    assert report["claim_boundaries"]["source_candidate_identities_mutated"] is False
    assert report["claim_boundaries"]["source_questionbank_items_mutated"] is False
    assert report["claim_boundaries"]["q10_redone"] is False


def test_u04_q10r1_preserves_a6_b10_c10_d8_e6_and_reuses_existing_renderer():
    report = _report()
    assert (
        "u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization._activity_html"
        in report["renderer_reuse"]
    )
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
    a = report["acceptance"]
    assert a["task_family_coverage"] == "10/10"
    assert a["target_relation_coverage"] == "8/8"
    assert a["communicative_function_coverage"] == "6/6"
    assert a["selected_relation_answer_leak_count"] == 0
    assert a["semantic_equivalent_distractor_count"] == 0
    assert a["duplicate_learner_visible_choice_count"] == 0
    assert report["presentation_fixes"]["engineering_prompt_projection_count"] == 800
    assert report["presentation_fixes"]["engineering_stimulus_metadata_suppression_count"] == 800
    assert report["presentation_fixes"]["selected_relation_answer_leak_count"] == 0


def test_u04_q10r1_reuses_q10_scene_answerability_validator_and_keeps_at_text_bound_only():
    report = _report()
    a = report["acceptance"]
    assert report["source_q10_validator_reused"]
    assert a["scene_bound_evidence_activity_count"] == 760
    assert a["at_text_bound_activity_count"] == 40
    assert a["at_scene_ref_render_count"] == 0
    assert a["fabricated_scene_ref_count"] == 0

    payload = source.build_export_payload()
    source_items = {row["item_id"]: row for row in payload["questionbank_items"]}
    for source_form in payload["forms"]:
        for item_id in source_form["item_ids"]:
            item = source_items[item_id]
            if item["relation_surface"] == "at":
                assert item["scene_ref_id"] is None
                assert item["source_scene_ref"] is None
                assert item["task_family_id"] in source.AT_ALLOWED_FAMILIES
                assert item["communicative_function_id"] == source.AT_CF
                assert item["options"] == []
            elif item["relation_surface"] == "between":
                landmarks = item["reference_landmarks"]
                assert len(landmarks) == 2
                assert len({value.casefold() for value in landmarks}) == 2


def test_u04_q10r1_progression_is_visible_and_not_only_a_stage_label():
    report = _report()
    a = report["acceptance"]
    assert a["stage_activity_counts"] == {
        "GUIDED": 160,
        "REDUCED_SUPPORT": 160,
        "INDEPENDENT": 160,
        "TRANSFER": 160,
        "RETENTION": 160,
    }
    assert a["stage_support_levels"] == {
        "GUIDED": "HIGH",
        "REDUCED_SUPPORT": "MEDIUM",
        "INDEPENDENT": "LOW",
        "TRANSFER": "MINIMAL",
        "RETENTION": "CUMULATIVE",
    }
    assert a["stage_visible_support_counts"] == {
        "GUIDED": 160,
        "REDUCED_SUPPORT": 160,
        "INDEPENDENT": 160,
        "TRANSFER": 160,
        "RETENTION": 160,
    }
    assert a["transfer_context_activity_count"] == 160
    assert a["retention_cumulative_carrier_activity_count"] == 16

    for form in report["learner_forms"]:
        stage = form["progression_stage"]
        marker = acceptance.STAGE_VISIBLE_MARKERS[stage]
        assert all(marker in activity["stimulus"] for activity in form["activities"])
        if stage == "GUIDED":
            assert all("Meaning help:" in row["stimulus"] for row in form["activities"])
        elif stage == "REDUCED_SUPPORT":
            assert all("Meaning help:" not in row["stimulus"] for row in form["activities"])
            assert all("Position fact:" in row["stimulus"] for row in form["activities"])
        elif stage == "INDEPENDENT":
            assert all("Meaning help:" not in row["stimulus"] for row in form["activities"])
            assert all("Position fact:" not in row["stimulus"] for row in form["activities"])
        elif stage == "TRANSFER":
            assert all("New situation:" in row["stimulus"] for row in form["activities"])
        elif stage == "RETENTION":
            assert all("Review evidence:" in row["stimulus"] for row in form["activities"])


def test_u04_q10r1_context_gap_and_retention_cumulative_carriers_remain_visible():
    report = _report()
    payload = source.build_export_payload()
    source_items = {row["item_id"]: row for row in payload["questionbank_items"]}
    source_forms = payload["forms"]
    gap_count = 0
    retention_integration_count = 0
    for form, source_form in zip(report["learner_forms"], source_forms):
        for activity, item_id in zip(form["activities"], source_form["item_ids"]):
            item = source_items[item_id]
            if item["task_family_id"] == "U04-TF07_CONTEXT_GAP":
                gap_count += 1
                assert "___" in activity["stimulus"]
            if (
                form["progression_stage"] == "RETENTION"
                and item["task_family_id"] == "U04-TF08_U01_U02_U03_INTEGRATION"
            ):
                retention_integration_count += 1
                assert all(
                    marker in activity["stimulus"]
                    for marker in ("One:", "Two:", "Reference:", "Review evidence:")
                )
                assert item["relation_surface"] in source.TARGET_RELATIONS
    assert gap_count > 0
    assert retention_integration_count == 16


def test_u04_q10r1_measures_global_duplicates_and_rejects_within_form_duplication():
    report = _report()
    a = report["acceptance"]
    assert a["learner_visible_exact_duplicate_count"] >= 0
    assert a["learner_visible_normalized_duplicate_count"] >= a["learner_visible_exact_duplicate_count"]
    assert a["same_visible_prompt_same_answer_duplicate_count"] >= 0
    assert a["within_form_exact_duplicate_count"] == 0
    assert a["within_form_normalized_duplicate_count"] == 0
    assert a["minimum_distinct_prompts_per_form"] >= 10
    assert a["maximum_same_prompt_count_per_form"] <= 7


def test_u04_q10r1_question_number_q03_is_not_confused_with_authority_metadata():
    report = _report()
    form = report["learner_forms"][0]
    assert form["activities"][2]["question_number"] == "Q03"
    html = acceptance.render_form_html(form)
    assert "Q03" in html
    assert "q03" not in {marker.casefold() for marker in acceptance.FORBIDDEN_LEARNER_MARKERS}

    leaking_activity = dict(form["activities"][0])
    leaking_activity["prompt"] = "selected_item_id"
    with pytest.raises(
        acceptance.Unit04LearnerFacingAcceptanceError,
        match="ENGINEERING_MARKER_VISIBLE",
    ):
        acceptance._assert_no_engineering_markers(leaking_activity, 1, 1)


def test_u04_q10r1_scope_boundaries_and_next_step_remain_locked():
    report = _report()
    assert all(value is False for value in report["claim_boundaries"].values())
    assert report["next_short_step"] == acceptance.NEXT_SHORT_STEP
    assert report["claim_boundaries"]["pdf_materialized"] is False
    assert report["claim_boundaries"]["motion_directional_from_into_to_activated"] is False
    assert report["claim_boundaries"]["a2_unlocked"] is False


def test_u04_q10r1_emits_focused_acceptance_readback(capfd):
    report = _report()
    a = report["acceptance"]
    readback = {
        "forms": a["form_count"],
        "activities": a["activity_count"],
        "answer_key_bindings": a["answer_key_binding_count"],
        "exact_duplicates": a["learner_visible_exact_duplicate_count"],
        "normalized_duplicates": a["learner_visible_normalized_duplicate_count"],
        "same_prompt_same_answer_duplicates": a["same_visible_prompt_same_answer_duplicate_count"],
        "within_form_exact_duplicates": a["within_form_exact_duplicate_count"],
        "within_form_normalized_duplicates": a["within_form_normalized_duplicate_count"],
        "answer_leakage": a["selected_relation_answer_leak_count"],
        "scene_bound": a["scene_bound_evidence_activity_count"],
        "at_text_bound": a["at_text_bound_activity_count"],
        "fabricated_scene_ref": a["fabricated_scene_ref_count"],
        "min_distinct_prompts_per_form": a["minimum_distinct_prompts_per_form"],
        "max_same_prompt_per_form": a["maximum_same_prompt_count_per_form"],
    }
    with capfd.disabled():
        print("U04Q10R1_ACCEPTANCE_READBACK=" + json.dumps(readback, sort_keys=True), flush=True)
