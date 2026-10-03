from __future__ import annotations
import json
from pathlib import Path
from ulga.builders import build_a1fs_v1_u06_q06_sentence_assets as q06_builder
from ulga.builders import build_a1fs_v1_u06_q07_life_skill_micro_scenes as q07_builder
from ulga.builders import build_a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion as q07r1_builder

ROOT=Path(__file__).resolve().parents[2]
Q08=ROOT/"ulga/contracts/a1fs_v1_u06_q08_communicative_function_authority.json"
REUSABLE=ROOT/"ulga/contracts/a1fs_v1_reusable_unit_production_contract.json"

EXPECTED_FUNCTION_IDS={
 "U06-CF01_STATE_ABILITY_OR_CAPABILITY",
 "U06-CF02_DESCRIBE_CAPABILITY_IN_SCENE",
 "U06-CF03_REQUEST_ABILITY_INFORMATION",
 "U06-CF04_CONFIRM_ABILITY_INFORMATION",
 "U06-CF05_IDENTIFY_ENTITY_BY_ABILITY",
 "U06-CF06_IDENTIFY_ACTION_OR_CAPABILITY_FROM_CONTEXT",
}
EXPECTED_FRAMES={"U06-CF-ABILITY-INTRANSITIVE","U06-CF-ABILITY-OBJECT","U06-CF-ABILITY-PREDICATE-TAIL"}

def load(path): return json.loads(path.read_text(encoding="utf-8"))

def test_u06_q08_is_exact_communicative_function_authority_slot():
    q08=load(Q08); reusable=load(REUSABLE)
    slot=next(row for row in reusable["authority_pipeline"]["required_slots"] if row["q"]=="Q08")
    assert slot["role"]=="COMMUNICATIVE_FUNCTION_AUTHORITY"
    assert q08["task_id"]=="A1FS-V1-U06Q08_Unit06CommunicativeFunctionAuthority"
    assert q08["authority_role"]=="Q08_COMMUNICATIVE_FUNCTION_AUTHORITY"
    assert q08["status"]=="PASS_A1FS_V1_U06Q08_COMMUNICATIVE_FUNCTION_AUTHORITY"
    assert q08["acceptance"]["status"]==q08["status"]

def test_u06_q08_function_inventory_is_unique_bounded_and_four_skill_compatible():
    q08=load(Q08); funcs=q08["communicative_functions"]; ids=[x["function_id"] for x in funcs]
    assert len(funcs)==6; assert len(ids)==len(set(ids))==6; assert set(ids)==EXPECTED_FUNCTION_IDS
    assert q08["coverage"]["communicative_function_count"]==6; assert q08["acceptance"]["communicative_function_authority"]=="6/6"
    assert {s for row in funcs for s in row["skill_compatibility"]}=={"READING","WRITING","LISTENING","SPEAKING"}
    assert all(row["accepted_sentence_required"] is True for row in funcs)
    assert all(row["accepted_scene_required_when_q06_context_bound"] is True for row in funcs)
    assert all(row["creates_new_grammar_authority"] is False for row in funcs)

def test_u06_q08_exactly_covers_all_three_q05_frames_and_all_129_q06_sentences():
    q08=load(Q08); matrix=q08["frame_function_compatibility"]; q06=q06_builder.build_report()
    assert set(q08["scope"]["q05_frame_ids"])==EXPECTED_FRAMES; assert set(matrix)==EXPECTED_FRAMES
    assert all(set(matrix[f])==EXPECTED_FUNCTION_IDS for f in EXPECTED_FRAMES)
    rows=q06["new_sentence_assets"]; assert len(rows)==129
    assert all(row["frame_id"] in matrix and matrix[row["frame_id"]] for row in rows)
    context=[x for x in rows if x["requires_context_binding"] is True]; standalone=[x for x in rows if x["requires_context_binding"] is False]
    assert len(context)==49; assert len(standalone)==80
    assert q08["coverage"]["q06_usable_sentence_function_coverage"]=="129/129"
    assert q08["coverage"]["q07_context_required_sentence_function_coverage"]=="49/49"
    assert q08["coverage"]["q06_standalone_sentence_function_coverage"]=="80/80"

def test_u06_q08_preserves_q07_scene_bindings_and_q06_deferred_boundary():
    q08=load(Q08); q07=q07_builder.build_report(); q06=q06_builder.build_report()
    bindings=q07["sentence_scene_bindings"]; assert len(bindings)==49; assert len({x["q06_sentence_id"] for x in bindings})==49
    assert len(q07["micro_scenes"])==17; assert q07["coverage"]["q06_unbound_context_required_sentence_count"]==0
    assert len(q06["excluded_candidates"])==6; assert all(x["decision"]=="DEFER" for x in q06["excluded_candidates"])
    a=q08["sentence_scene_and_chunk_function_acceptance"]
    assert a["q07_context_required_sentence_function_coverage_required"]=="49/49"
    assert a["q07_scene_truth_remains_authoritative"] is True
    assert a["q07_referent_binding_remains_authoritative"] is True
    assert a["q07_ability_reading_remains_authoritative"] is True
    assert a["q06_deferred_candidates_remain_deferred"] is True

def test_u06_q08_covers_all_182_q07r1_chunks_without_promoting_them_to_sentence_or_global_authority():
    q08=load(Q08); q07r1=q07r1_builder.build_report()
    base=q07r1["existing_chunk_baseline"]["normalized_surfaces"]; new=q07r1["new_unit06_functional_chunks"]
    assert len(base)==58; assert len(new)==124; assert len(set(base)|{x["normalized_surface"] for x in new})==182
    compat=q08["functional_chunk_function_compatibility"]
    assert compat["distinct_can_functional_chunk_count"]==182
    assert compat["chunk_function_coverage_required"]=="182/182"
    assert set(compat["function_ids"])==EXPECTED_FUNCTION_IDS
    assert compat["chunk_surface_alone_creates_sentence_authority"] is False
    assert compat["q07r1_unit_local_scope_preserved"] is True
    assert compat["new_global_chunk_identity_count"]==0
    assert q08["coverage"]["q07r1_functional_chunk_function_coverage"]=="182/182"

def test_u06_q08_information_seeking_does_not_unlock_can_questions_requests_permission_or_other_meanings():
    q08=load(Q08); funcs={x["function_id"]:x for x in q08["communicative_functions"]}
    seek=funcs["U06-CF03_REQUEST_ABILITY_INFORMATION"]; check=funcs["U06-CF04_CONFIRM_ABILITY_INFORMATION"]
    for row in (seek,check):
        assert row["exact_question_form_materialized_here"] is False
        assert row["can_interrogative_mastery_unlocked"] is False
        assert row["creates_new_grammar_authority"] is False
    assert seek["request_to_perform_action_authorized"] is False
    assert seek["permission_request_authorized"] is False
    policy=q08["function_realization_policy"]
    assert policy["new_question_grammar_authorized_by_q08"] is False
    assert policy["information_seeking_or_checking_function_does_not_unlock_can_interrogative_mastery"] is True
    assert policy["requesting_information_about_ability_does_not_authorize_request_to_perform_action"] is True
    assert set(q08["excluded_communicative_meanings"])=={
      "REQUEST_TO_PERFORM_ACTION_WITH_CAN","ASK_PERMISSION_WITH_CAN","GIVE_PERMISSION_WITH_CAN",
      "MAKE_OFFER_WITH_CAN","EXPRESS_POSSIBILITY_WITH_CAN","CAN_AS_NOUN"
    }

def test_u06_q08_does_not_materialize_q09_q10_reader360_or_later_grammar():
    q08=load(Q08); p=q08["function_realization_policy"]; b=q08["q08_boundaries"]
    assert p["communicative_function_ids_are_semantic_intent_authority_only"] is True
    assert p["learner_visible_prompt_or_utterance_templates_materialized_by_q08"] is False
    assert p["new_sentence_pattern_family_authorized_by_q08"] is False
    assert p["new_vocabulary_identity_authorized_by_q08"] is False
    assert p["new_scene_identity_authorized_by_q08"] is False
    assert p["new_functional_chunk_identity_authorized_by_q08"] is False
    assert all(v is False for v in b.values())
    assert q08["coverage"]["new_grammar_authority_count"]==0
    assert q08["coverage"]["new_sentence_pattern_family_count"]==0
    assert q08["coverage"]["new_vocabulary_identity_count"]==0
    assert q08["coverage"]["new_scene_identity_count"]==0
    assert q08["coverage"]["new_functional_chunk_identity_count"]==0
    assert q08["next_short_step"]=="A1FS-V1-U06Q09_Unit06TaskAndPedagogicalContract"
