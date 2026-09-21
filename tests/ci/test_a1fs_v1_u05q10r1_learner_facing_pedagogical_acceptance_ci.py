import json
from functools import lru_cache

import pytest

from product.a1fs_v1_2_1 import (
    u05q10r1_unit05_learner_facing_pedagogical_acceptance as acceptance,
)
from ulga.builders import build_a1fs_v1_u05q10_questionbank_form_materialization as source


@lru_cache(maxsize=1)
def report():
    return acceptance.build_acceptance_report()


def test_u05_q10r1_accepts_exact_twenty_forms_and_eight_hundred_learner_activities():
    r = report()
    a = r["acceptance"]
    assert r["status"] == acceptance.PASS_STATUS
    assert r["source_task_id"] == source.TASK_ID
    assert r["source_status"] == source.PASS_STATUS
    assert a["form_count"] == 20
    assert a["activity_count"] == 800
    assert a["rendered_activity_count"] == 800
    assert a["answer_key_binding_count"] == 800
    assert len(r["learner_forms"]) == 20
    assert len(r["answer_key_bindings"]) == 800
    assert r["html_form_count"] == 20
    assert r["html_activity_count"] == 800
    assert len({
        (row["form_number"], row["question_number"])
        for row in r["answer_key_bindings"]
    }) == 800


def test_u05_q10r1_uses_unit05_q10_as_content_source_and_unit04_only_as_alignment_reference():
    r = report()
    alignment = r["alignment_reference"]
    assert alignment["unit04_role"] == "COMPARISON_AND_ACCEPTANCE_PATTERN_ALIGNMENT_ONLY"
    assert alignment["unit04_content_authority_consumed"] is False
    assert alignment["unit04_sentence_or_scene_content_consumed"] is False
    assert alignment["unit04_function_or_task_identity_consumed"] is False
    assert alignment["unit05_q10_is_sole_direct_content_source"] is True
    assert r["claim_boundaries"]["unit04_used_as_unit05_content_authority"] is False
    assert r["acceptance"]["unit04_content_authority_consumed_count"] == 0


def test_u05_q10r1_preserves_locked_q10_runtime_item_and_candidate_identity():
    r = report()
    payload = source.build_export_payload()
    assert r["source_runtime_identity_sha256"] == acceptance._runtime_identity(
        payload["runtime_bindings"]
    )
    assert r["source_item_identity_sha256"] == acceptance._item_identity(
        payload["questionbank_items"]
    )
    assert len({row["selected_item_id"] for row in payload["runtime_bindings"]}) == 800
    assert all(len(row["candidate_ids"]) == 3 for row in payload["runtime_bindings"])
    assert r["claim_boundaries"]["source_800_runtime_rows_mutated"] is False
    assert r["claim_boundaries"]["source_selected_item_identities_mutated"] is False
    assert r["claim_boundaries"]["source_candidate_identities_mutated"] is False
    assert r["claim_boundaries"]["source_questionbank_items_mutated"] is False
    assert r["claim_boundaries"]["q10_redone"] is False


def test_u05_q10r1_keeps_a6_b10_c10_d8_e6_and_generic_renderer():
    r = report()
    assert "u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization._activity_html" in r["renderer_reuse"]
    for form in r["learner_forms"]:
        assert form["section_count"] == 5
        assert [row["section"] for row in form["sections"]] == ["A", "B", "C", "D", "E"]
        assert {row["section"]: row["activity_count"] for row in form["sections"]} == {
            "A": 6,
            "B": 10,
            "C": 10,
            "D": 8,
            "E": 6,
        }
        assert len(form["activities"]) == 40
        acceptance.u01_learner._assert_no_answer_leak(form)
        html = acceptance.render_form_html(form)
        assert html.count('<article class="activity">') == 40
        lowered = html.casefold()
        for marker in acceptance.FORBIDDEN_LEARNER_MARKERS:
            assert marker.casefold() not in lowered


def test_u05_q10r1_keeps_all_unit05_authority_dimensions_learner_representable():
    a = report()["acceptance"]
    assert a["task_family_coverage"] == "10/10"
    assert a["communicative_function_coverage"] == "7/7"
    assert a["frame_coverage"] == "6/6"
    assert a["subject_class_coverage"] == "9/9"
    assert a["context_bound_activity_count"] + a["standalone_activity_count"] == 800
    assert a["selected_response_activity_count"] + a["short_text_activity_count"] == 800
    assert a["engineering_marker_visible_count"] == 0


def test_u05_q10r1_progression_is_visible_and_not_only_metadata():
    r = report()
    a = r["acceptance"]
    assert a["stage_activity_counts"] == {
        "GUIDED": 160,
        "INDEPENDENT": 160,
        "REDUCED_SUPPORT": 160,
        "RETENTION": 160,
        "TRANSFER": 160,
    }
    assert a["stage_visible_support_counts"] == a["stage_activity_counts"]
    assert a["stage_support_levels"] == {
        "GUIDED": "HIGH",
        "REDUCED_SUPPORT": "MEDIUM",
        "INDEPENDENT": "LOW",
        "TRANSFER": "MINIMAL",
        "RETENTION": "CUMULATIVE",
    }

    for form in r["learner_forms"]:
        stage = form["progression_stage"]
        marker = acceptance.STAGE_VISIBLE_MARKERS[stage]
        assert all(marker in activity["stimulus"] for activity in form["activities"])


def test_u05_q10r1_humanizes_engineering_meaning_and_polarity_options():
    r = report()
    forbidden_visible_options = {
        "IDENTITY_OR_CATEGORY",
        "DESCRIPTION_OR_STATE",
        "STATIC_LOCATION",
        "AFFIRMATIVE",
        "NEGATIVE",
    }
    seen_meaning = False
    seen_polarity = False
    for form in r["learner_forms"]:
        for activity in form["activities"]:
            options = set(activity["options"])
            assert not (options & forbidden_visible_options)
            if options & set(acceptance.MEANING_OPTIONS.values()):
                seen_meaning = True
            if options & set(acceptance.POLARITY_OPTIONS.values()):
                seen_polarity = True
    assert seen_meaning
    assert seen_polarity


def test_u05_q10r1_context_gap_is_scene_bound_without_exposing_scene_ids():
    r = report()
    payload = source.build_export_payload()
    items = {row["item_id"]: row for row in payload["questionbank_items"]}
    source_forms = payload["forms"]
    count = 0
    for form, source_form in zip(r["learner_forms"], source_forms):
        for activity, item_id in zip(form["activities"], source_form["item_ids"]):
            item = items[item_id]
            if item["task_family_id"] != "U05-TF07_CONTEXT_GAP":
                continue
            count += 1
            assert item["requires_context_binding"] is True
            assert item["scene_ref_id"] is not None
            assert "___" in activity["stimulus"]
            assert "Scene fact:" in activity["stimulus"]
            assert "scene_ref_id" not in activity["stimulus"].casefold()
            if item["subject_class"] in {"he", "she"}:
                assert "Person:" in activity["stimulus"]
            elif item["subject_class"] in {"it", "they"}:
                assert "Referent:" in activity["stimulus"]
    assert count > 0


def test_u05_q10r1_information_request_does_not_create_unit05_question_grammar():
    r = report()
    payload = source.build_export_payload()
    items = {row["item_id"]: row for row in payload["questionbank_items"]}
    source_forms = payload["forms"]
    count = 0
    for form, source_form in zip(r["learner_forms"], source_forms):
        for activity, item_id in zip(form["activities"], source_form["item_ids"]):
            item = items[item_id]
            if item["communicative_function_id"] != "U05-CF05_REQUEST_BASIC_BE_INFORMATION":
                continue
            count += 1
            assert item["be_interrogative_mastery_activated"] is False
            assert "question pattern you already know" in activity["prompt"]
            assert activity["response_mode"] == "short_text"
    assert count > 0
    assert r["claim_boundaries"]["be_interrogative_mastery_activated"] is False


def test_u05_q10r1_rejects_within_form_visible_duplication_and_keeps_variety():
    a = report()["acceptance"]
    assert a["within_form_exact_duplicate_count"] == 0
    assert a["within_form_normalized_duplicate_count"] == 0
    assert a["minimum_distinct_prompts_per_form"] >= 8
    assert a["maximum_same_prompt_count_per_form"] <= 10
    assert a["learner_visible_normalized_duplicate_count"] >= a["learner_visible_exact_duplicate_count"]


def test_u05_q10r1_scope_boundaries_and_next_step_are_locked():
    r = report()
    assert all(value is False for value in r["claim_boundaries"].values())
    assert r["next_short_step"] == acceptance.NEXT_SHORT_STEP
    assert r["claim_boundaries"]["pdf_materialized"] is False
    assert r["claim_boundaries"]["unit05_current360_materialized"] is False
    assert r["claim_boundaries"]["unit05_spoken360_materialized"] is False
    assert r["claim_boundaries"]["unit05_pattern360_materialized"] is False
    assert r["claim_boundaries"]["a2_a2plus_unlocked"] is False


def test_u05_q10r1_emits_focused_acceptance_readback(capfd):
    a = report()["acceptance"]
    readback = {
        "forms": a["form_count"],
        "activities": a["activity_count"],
        "answers": a["answer_key_binding_count"],
        "tasks": a["task_family_coverage"],
        "functions": a["communicative_function_coverage"],
        "frames": a["frame_coverage"],
        "subjects": a["subject_class_coverage"],
        "context_bound": a["context_bound_activity_count"],
        "standalone": a["standalone_activity_count"],
        "within_form_exact_duplicates": a["within_form_exact_duplicate_count"],
        "within_form_normalized_duplicates": a["within_form_normalized_duplicate_count"],
        "unit04_content_authority": a["unit04_content_authority_consumed_count"],
    }
    with capfd.disabled():
        print("U05Q10R1_ACCEPTANCE_READBACK=" + json.dumps(readback, sort_keys=True), flush=True)
