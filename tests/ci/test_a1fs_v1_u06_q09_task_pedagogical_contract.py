from __future__ import annotations
import json
from pathlib import Path
from ulga.builders import build_a1fs_v1_u06_q06_sentence_assets as q06_builder
from ulga.builders import build_a1fs_v1_u06_q07_life_skill_micro_scenes as q07_builder
from ulga.builders import build_a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion as q07r1_builder

ROOT=Path(__file__).resolve().parents[2]
REUSABLE=ROOT/"ulga/contracts/a1fs_v1_reusable_unit_production_contract.json"
Q08=ROOT/"ulga/contracts/a1fs_v1_u06_q08_communicative_function_authority.json"
Q09=ROOT/"ulga/contracts/a1fs_v1_u06_q09_task_pedagogical_contract.json"

EXPECTED_TASK_FAMILIES={
 "CAN_FORM_RECOGNITION","BASE_VERB_FORM_SELECTION","ABILITY_MEANING_DISCRIMINATION",
 "FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE","CHUNK_TO_COMPLETE_SENTENCE","ERROR_DETECTION_AND_CORRECTION",
 "SCENE_BOUND_CONTEXT_GAP","U01_U05_CUMULATIVE_INTEGRATION","PRODUCTIVE_ABILITY_RESPONSE","TRANSFER",
}
EXPECTED_FUNCTION_IDS={
 "U06-CF01_STATE_ABILITY_OR_CAPABILITY","U06-CF02_DESCRIBE_CAPABILITY_IN_SCENE","U06-CF03_REQUEST_ABILITY_INFORMATION",
 "U06-CF04_CONFIRM_ABILITY_INFORMATION","U06-CF05_IDENTIFY_ENTITY_BY_ABILITY","U06-CF06_IDENTIFY_ACTION_OR_CAPABILITY_FROM_CONTEXT",
}
EXPECTED_FRAMES={"U06-CF-ABILITY-INTRANSITIVE","U06-CF-ABILITY-OBJECT","U06-CF-ABILITY-PREDICATE-TAIL"}
EXPECTED_PROGRESSIONS={"GUIDED","REDUCED_SUPPORT","INDEPENDENT","TRANSFER","RETENTION"}

def load(path): return json.loads(path.read_text(encoding="utf-8"))

def test_u06_q09_is_exact_task_and_pedagogical_contract_slot():
    reusable=load(REUSABLE); q09=load(Q09)
    slot=next(row for row in reusable["authority_pipeline"]["required_slots"] if row["q"]=="Q09")
    assert slot["role"]=="TASK_AND_PEDAGOGICAL_CONTRACT"
    assert q09["task_id"]=="A1FS-V1-U06Q09_Unit06TaskAndPedagogicalContract"
    assert q09["authority_role"]=="Q09_TASK_AND_PEDAGOGICAL_CONTRACT"
    assert q09["status"]=="PASS_A1FS_V1_U06Q09_TASK_AND_PEDAGOGICAL_CONTRACT"
    assert q09["acceptance"]["status"]==q09["status"]

def test_u06_q09_task_inventory_sections_and_progression_are_exact():
    q09=load(Q09); rows=q09["task_families"]; names={x["family_name"] for x in rows}; ids=[x["task_family_id"] for x in rows]
    assert len(rows)==10; assert len(ids)==len(set(ids))==10; assert names==EXPECTED_TASK_FAMILIES
    assert len(q09["section_architecture"])==5
    assert {x["progression_role"] for x in q09["progression_contract"]}==EXPECTED_PROGRESSIONS
    assert q09["acceptance"]["task_family_count"]==10
    assert q09["acceptance"]["section_role_count"]==5
    assert q09["acceptance"]["progression_role_count"]==5

def test_u06_q09_all_q08_functions_and_q05_frames_have_task_coverage():
    q09=load(Q09); q08=load(Q08); rows=q09["task_families"]
    covered={f for row in rows for f in row["allowed_function_ids"]}
    assert set(q09["scope"]["q08_communicative_function_ids"])==EXPECTED_FUNCTION_IDS
    assert {x["function_id"] for x in q08["communicative_functions"]}==EXPECTED_FUNCTION_IDS
    assert covered==EXPECTED_FUNCTION_IDS
    assert set(q09["scope"]["q05_frame_ids"])==EXPECTED_FRAMES
    assert q09["acceptance"]["q08_communicative_function_task_coverage"]=="6/6"
    assert q09["acceptance"]["q05_frame_task_contract_coverage"]=="3/3"

def test_u06_q09_preserves_q06_sentence_route_and_q07_context_route():
    q09=load(Q09); q06=q06_builder.build_report(); q07=q07_builder.build_report()
    assert len(q06["new_sentence_assets"])==129
    assert len([x for x in q06["new_sentence_assets"] if x["requires_context_binding"]])==49
    assert len([x for x in q06["new_sentence_assets"] if not x["requires_context_binding"]])==80
    assert len(q07["sentence_scene_bindings"])==49
    route=q09["sentence_realization_routes"]["canonical_q06_sentence_route"]
    assert route["available_sentence_count"]==129 and route["context_bound_count"]==49 and route["standalone_count"]==80
    assert q09["acceptance"]["q06_sentence_path_coverage"]=="129/129"
    assert q09["acceptance"]["q07_context_binding_contract_coverage"]=="49/49"

def test_u06_q09_chunk_controlled_sentence_realization_path_covers_182_chunks_and_62_verbs_without_second_sentence_authority():
    q09=load(Q09); q07r1=q07r1_builder.build_report()
    base=set(q07r1["existing_chunk_baseline"]["normalized_surfaces"]); new=q07r1["new_unit06_functional_chunks"]
    all_chunks=base|{x["normalized_surface"] for x in new}; verbs={x["base_verb"] for x in new}
    assert len(all_chunks)==182; assert len(verbs)==62
    route=q09["sentence_realization_routes"]["q07r1_chunk_controlled_route"]
    assert route["distinct_chunk_count"]==182; assert route["source_verb_count"]==62
    assert route["learner_visible_complete_sentence_may_be_materialized_in_q10"] is True
    assert route["result_identity_scope"]=="Q10_ITEM_LOCAL_SENTENCE_REALIZATION"
    assert route["result_promoted_to_q06_or_global_sentence_asset"] is False
    assert route["semantic_review_or_validator_gate_required"] is True
    policy=q09["task_authority_policy"]
    assert policy["q07r1_chunk_controlled_realization_path_allowed"] is True
    assert policy["q07r1_chunk_surface_alone_is_not_sentence_authority"] is True
    assert policy["q10_item_local_sentence_realization_does_not_promote_global_sentence_asset"] is True
    assert q09["acceptance"]["q07r1_functional_chunk_task_contract_coverage"]=="182/182"
    assert q09["acceptance"]["q07r1_source_verb_task_contract_coverage"]=="62/62"

def test_u06_q09_q10_is_coverage_driven_and_must_bind_all_chunks_and_verbs():
    q09=load(Q09); req=q09["q10_materialization_requirements"]
    assert req["all_ten_task_families_require_nonzero_materialized_coverage"] is True
    assert req["all_three_q05_frames_require_materialized_coverage"] is True
    assert req["all_six_q08_communicative_functions_require_task_compatibility_coverage"] is True
    assert req["all_182_q07r1_functional_chunks_require_nonzero_questionbank_binding_coverage"] is True
    assert req["all_62_q07r1_source_verbs_require_nonzero_questionbank_binding_coverage"] is True
    assert req["q07r1_chunk_to_sentence_item_local_realization_requires_semantic_validation"] is True
    assert req["q07r1_item_local_realizations_must_not_be_promoted_to_canonical_sentence_assets"] is True
    assert req["capacity_policy"]=="COVERAGE_DRIVEN_NOT_FIXED_BY_LEGACY_FORM_COUNT"
    assert req["questionbank_capacity"]=="DETERMINED_BY_182_CHUNK_62_VERB_10_TASK_FAMILY_COVERAGE_AND_ACCEPTANCE"

def test_u06_q09_does_not_unlock_can_question_negative_or_nonability_meanings():
    q09=load(Q09); req=q09["q10_materialization_requirements"]; b=q09["q09_boundaries"]
    assert req["can_interrogative_question_surface_as_unit06_target_allowed"] is False
    assert req["can_negative_target_allowed"] is False
    assert req["permission_offer_request_possibility_target_allowed"] is False
    for k in ("can_interrogative_mastery_activated","can_negative_mastery_activated","permission_can_activated","offer_can_activated","request_can_activated","possibility_can_activated","a2_a2plus_unlocked"):
        assert b[k] is False
    assert all(x["creates_new_grammar_authority"] is False for x in q09["task_families"])

def test_u06_q09_materializes_no_q10_items_forms_or_new_authorities():
    q09=load(Q09); p=q09["task_authority_policy"]; b=q09["q09_boundaries"]
    assert p["learner_visible_question_items_materialized_by_q09"] is False
    assert p["learner_visible_prompt_templates_materialized_by_q09"] is False
    for k in ("learner_visible_prompt_templates_materialized","learner_visible_question_items_materialized","questionbank_items_materialized","forms_materialized","q10_numeric_form_parameters_materialized","new_grammar_authority_created","new_vocabulary_identity_created","new_sentence_identity_created","new_scene_identity_created","new_functional_chunk_identity_created","new_communicative_function_identity_created"):
        assert b[k] is False
    assert q09["acceptance"]["q10_items_materialized"]==0
    assert q09["acceptance"]["q10_forms_materialized"]==0
    assert q09["next_short_step"]=="A1FS-V1-U06Q10_Unit06QuestionBankAndFormMaterialization"
