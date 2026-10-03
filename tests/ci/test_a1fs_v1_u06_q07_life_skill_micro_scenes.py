from __future__ import annotations
from collections import Counter
from ulga.builders import build_a1fs_v1_u06_q07_life_skill_micro_scenes as builder
def report(): return builder.build_report()
def test_u06_q07_binds_all_and_only_49_context_bound_q06_assets_once():
    r=report(); b=r["sentence_scene_bindings"]; assert len(b)==49; assert len({x["q06_sentence_id"] for x in b})==49; assert r["coverage"]["q06_unbound_context_required_sentence_count"]==0; assert r["coverage"]["q06_standalone_forced_binding_count"]==0; assert r["acceptance"]["q06_context_required_sentence_bindings"]=="49/49"
def test_u06_q07_full_cumulative_scene_shape_and_coverage():
    r=report(); assert len(r["micro_scenes"])==17; assert r["coverage"]["full_sentence_count"]==102; assert r["coverage"]["scene_local_cumulative_support_sentence_count"]==53
    expected={"U01_ARTICLES_BASIC","U02_REGULAR_PLURAL_NOUNS","U03_SUBJECT_PRONOUNS","U04_BASIC_PREPOSITIONS_PLACE","U05_BE_VERB_BASIC","U06_CAN_STATEMENT"}
    assert all(set(x["scene_skill_coverage"])==expected for x in r["micro_scenes"]); assert r["coverage"]["skill_scene_coverage_counts"]=={k:17 for k in sorted(expected)}; assert r["coverage"]["used_scene_family_count"]>=10
def test_u06_q07_support_is_scene_local_not_second_sentence_authority():
    r=report(); rows=r["scene_local_support_sentences"]; assert len(rows)==53; assert all(x["canonical_sentence_asset"] is False and x["scene_local_only"] is True and x["target_unit_new_content"] is False for x in rows); assert all(x["sentence_authority_role"]=="GPT56_REVIEWED_SCENE_LOCAL_CUMULATIVE_SUPPORT" for x in rows); assert r["coverage"]["new_global_sentence_authority_count"]==0
def test_u06_q07_functional_chunk_backfill_and_subject_dedup():
    r=report(); assert r["coverage"]["distinct_can_functional_chunk_count"]==33; assert len(r["q04r1_exact_can_functional_reuse"])==16; assert len(r["unit06_scene_derived_functional_chunks"])==17
    assert all(x["authority_scope"]=="UNIT06_LOCAL_FUNCTIONAL_CHUNK_AUTHORITY" and x["new_global_chunk_identity_created"] is False for x in r["unit06_scene_derived_functional_chunks"])
    inv={(x["kind"],x["normalized_surface"]):x for x in r["functional_chunk_inventory"]}; catch=inv[("CAN_ABILITY","can catch a ball")]; assert catch["occurrence_count"]==2
def test_u06_q07_preserves_six_q06_deferred_candidates():
    r=report(); assert len(r["q06_deferred_candidates_preserved"])==6; assert all(x["decision"]=="DEFER" for x in r["q06_deferred_candidates_preserved"]); assert r["coverage"]["q06_deferred_retained_count"]==6
def test_u06_q07_policy_bound_transition_boundaries_and_next_step():
    c=builder.build_candidate(); a=builder.admit_candidate(c); assert c["artifact_role"]=="CANDIDATE_JSON"; assert a["artifact_role"]=="APPROVED_CANONICAL_JSON"; assert a["admission"]["decision_ref"]==builder.DECISION_REF; assert a["content_governance"]["a2_unlocked"] is False
    r=a["payload"]; assert r["pilot_review"]["operator_review_decision"]=="PASS_EXPAND_TO_FULL_Q07"; assert r["coverage"]["new_global_scene_identity_count"]==0; assert r["coverage"]["new_global_chunk_identity_count"]==0; assert r["next_short_step"]=="A1FS-V1-U06Q08_Unit06CommunicativeFunctionAuthority"
