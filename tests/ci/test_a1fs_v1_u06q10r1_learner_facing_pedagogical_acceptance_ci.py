import json
from functools import lru_cache

from product.a1fs_v1_2_1 import (
    u06q10r1_unit06_learner_facing_pedagogical_acceptance as acceptance,
)
from ulga.builders import build_a1fs_v1_u06q10_questionbank_form_materialization as source

@lru_cache(maxsize=1)
def report():
    return acceptance.build_acceptance_report()

def test_u06_q10r1_accepts_exact_ten_forms_and_three_hundred_learner_activities():
    r=report(); a=r["acceptance"]
    assert r["status"]==acceptance.PASS_STATUS
    assert r["source_task_id"]==source.TASK_ID
    assert r["source_status"]==source.PASS_STATUS
    assert a["form_count"]==10
    assert a["activity_count"]==300
    assert a["rendered_activity_count"]==300
    assert a["answer_key_binding_count"]==300
    assert len(r["learner_forms"])==10
    assert len(r["answer_key_bindings"])==300
    assert r["html_form_count"]==10
    assert r["html_activity_count"]==300
    assert len({(x["form_number"],x["question_number"]) for x in r["answer_key_bindings"]})==300

def test_u06_q10r1_preserves_q10_item_and_form_identity_without_redoing_q10():
    r=report(); p=source.build_export_payload()
    assert r["source_item_identity_sha256"]==acceptance._item_identity(p["questionbank_items"])
    assert r["source_form_identity_sha256"]==acceptance._form_identity(p["forms"])
    assert r["claim_boundaries"]["source_questionbank_items_mutated"] is False
    assert r["claim_boundaries"]["source_forms_mutated"] is False
    assert r["claim_boundaries"]["q10_redone"] is False

def test_u06_q10r1_preserves_a6_b6_c8_d4_e6_and_generic_renderer():
    r=report()
    assert "u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization._activity_html" in r["renderer_reuse"]
    for form in r["learner_forms"]:
        assert form["section_count"]==5
        assert [x["section"] for x in form["sections"]]==["A","B","C","D","E"]
        assert {x["section"]:x["activity_count"] for x in form["sections"]}=={"A":6,"B":6,"C":8,"D":4,"E":6}
        assert len(form["activities"])==30
        acceptance.u01_learner._assert_no_answer_leak(form)
        html=acceptance.render_form_html(form)
        assert html.count('<article class="activity">')==30
        lowered=html.casefold()
        for marker in acceptance.FORBIDDEN_LEARNER_MARKERS:
            assert marker.casefold() not in lowered

def test_u06_q10r1_keeps_all_authority_dimensions_learner_representable():
    a=report()["acceptance"]
    assert a["task_family_coverage"]=="10/10"
    assert a["communicative_function_coverage"]=="6/6"
    assert a["frame_coverage"]=="3/3"
    assert a["q06_sentence_coverage"]=="129/129"
    assert a["q07_scene_coverage"]=="17/17"
    assert a["q07r1_functional_chunk_coverage"]=="182/182"
    assert a["q07r1_source_verb_coverage"]=="62/62"
    assert a["source_route_counts"]=={"Q06_CANONICAL_SENTENCE":129,"Q07R1_CHUNK_CONTROLLED_REALIZATION":171}
    assert a["engineering_marker_visible_count"]==0

def test_u06_q10r1_progression_is_visible_and_balanced():
    r=report(); a=r["acceptance"]
    expected={"GUIDED":60,"REDUCED_SUPPORT":60,"INDEPENDENT":60,"TRANSFER":60,"RETENTION":60}
    assert a["stage_activity_counts"]==expected
    assert a["stage_visible_support_counts"]==expected
    assert a["stage_support_levels"]=={
        "GUIDED":"HIGH","REDUCED_SUPPORT":"MEDIUM","INDEPENDENT":"LOW","TRANSFER":"MINIMAL","RETENTION":"CUMULATIVE"
    }
    for form in r["learner_forms"]:
        marker=acceptance.STAGE_VISIBLE_MARKERS[form["progression_stage"]]
        assert all(marker in row["stimulus"] for row in form["activities"])

def test_u06_q10r1_humanizes_ability_meaning_without_teaching_blocked_can_meanings():
    r=report()
    forbidden={"permission or a request","possibility","ability or capability"}
    seen=False
    for form in r["learner_forms"]:
        for activity in form["activities"]:
            options=set(activity["options"])
            assert not (options & forbidden)
            if "what someone or something is able to do" in options:
                seen=True
    assert seen
    assert r["presentation_fixes"]["ability_meaning_option_humanization_enabled"] is True

def test_u06_q10r1_tf07_scene_projection_does_not_repeat_target_sentence_in_stimulus():
    r=report(); p=source.build_export_payload()
    items={x["item_id"]:x for x in p["questionbank_items"]}
    count=0
    for form,source_form in zip(r["learner_forms"],p["forms"]):
        for activity,item_id in zip(form["activities"],source_form["item_ids"]):
            item=items[item_id]
            if item["task_family_id"]!="U06-TF07_SCENE_BOUND_CONTEXT_GAP":
                continue
            count+=1
            assert item["scene_ref_id"] is not None
            assert "Scene:" in activity["stimulus"]
            assert "Target:" in activity["stimulus"]
            assert "Action:" in activity["stimulus"]
            assert str(item["correct_answer"]) not in activity["stimulus"]
    assert count==40
    assert r["presentation_fixes"]["tf07_scene_target_sentence_leak_suppressed"] is True

def test_u06_q10r1_preserves_item_local_sentence_boundary_and_deferred_chunk_guard():
    r=report(); a=r["acceptance"]; p=source.build_export_payload()
    assert a["item_local_sentence_activity_count"]>0
    assert a["item_local_sentence_promoted_to_canonical_asset_count"]==0
    assert a["restricted_deferred_chunk_sentence_realization_count"]==0
    restricted=[x for x in p["questionbank_items"] if x.get("functional_chunk_binding") in {"can go to school","can study at school"}]
    assert restricted
    assert all(x["item_local_sentence_realization"] is False for x in restricted)
    assert r["claim_boundaries"]["item_local_sentence_promoted_to_canonical_asset"] is False

def test_u06_q10r1_has_no_within_form_visible_duplicates_and_keeps_prompt_variety():
    a=report()["acceptance"]
    assert a["within_form_exact_duplicate_count"]==0
    assert a["within_form_normalized_duplicate_count"]==0
    assert a["minimum_distinct_prompts_per_form"]>=10
    assert a["maximum_same_prompt_count_per_form"]<=3

def test_u06_q10r1_scope_boundaries_and_next_step_are_locked():
    r=report()
    assert all(value is False for value in r["claim_boundaries"].values())
    assert r["claim_boundaries"]["pdf_materialized"] is False
    assert r["claim_boundaries"]["can_interrogative_mastery_activated"] is False
    assert r["claim_boundaries"]["can_negative_mastery_activated"] is False
    assert r["claim_boundaries"]["a2_a2plus_unlocked"] is False
    assert r["next_short_step"]==acceptance.NEXT_SHORT_STEP

def test_u06_q10r1_emits_focused_acceptance_readback(capfd):
    a=report()["acceptance"]
    readback={
        "forms":a["form_count"],"activities":a["activity_count"],"answers":a["answer_key_binding_count"],
        "tasks":a["task_family_coverage"],"functions":a["communicative_function_coverage"],"frames":a["frame_coverage"],
        "q06":a["q06_sentence_coverage"],"scenes":a["q07_scene_coverage"],"chunks":a["q07r1_functional_chunk_coverage"],
        "verbs":a["q07r1_source_verb_coverage"],"within_form_exact_duplicates":a["within_form_exact_duplicate_count"],
        "within_form_normalized_duplicates":a["within_form_normalized_duplicate_count"],
    }
    with capfd.disabled():
        print("U06Q10R1_ACCEPTANCE_READBACK="+json.dumps(readback,sort_keys=True),flush=True)
