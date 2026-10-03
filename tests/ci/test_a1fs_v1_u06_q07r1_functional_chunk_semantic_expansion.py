from __future__ import annotations
from collections import Counter
from ulga.builders import build_a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion as builder
def report(): return builder.build_report()
def test_q07r1_expands_all_62_yle_ability_verbs_with_two_reviewed_chunks_each():
    r=report(); rows=r["new_unit06_functional_chunks"]; c=Counter(x["base_verb"] for x in rows)
    assert len(rows)==124; assert len(c)==62; assert set(c.values())=={2}; assert r["coverage_report"]["source_verbs_with_zero_new_chunks"]==0
def test_q07r1_exact_dedup_extends_58_baseline_to_182_distinct_can_chunks():
    r=report(); base=set(r["existing_chunk_baseline"]["normalized_surfaces"]); new={x["normalized_surface"] for x in r["new_unit06_functional_chunks"]}
    assert len(base)==58; assert len(new)==124; assert not (base & new); assert len(base|new)==182; assert r["coverage_report"]["cumulative_distinct_can_chunk_count_after_q07r1"]==182
def test_q07r1_scene_grounding_and_semantic_decisions_are_explicit():
    r=report(); rows=r["new_unit06_functional_chunks"]; c=Counter(x["semantic_admission_class"] for x in rows)
    assert c=={"APPROVE":88,"SCENE_GROUNDED_APPROVE":36}
    assert all(x["scene_grounding"]["ability_reading_required"] is True and x["scene_grounding"]["permission_availability_reading_blocked"] is True and x["scene_grounding"]["grounding_directive"] for x in rows)
def test_q07r1_is_unit06_local_and_does_not_rewrite_prior_authorities():
    r=report(); assert all(x["authority_scope"]=="UNIT06_LOCAL_FUNCTIONAL_CHUNK_AUTHORITY" for x in r["new_unit06_functional_chunks"])
    assert r["coverage_report"]["new_global_chunk_identity_count"]==0; assert r["coverage_report"]["new_global_vocabulary_identity_count"]==0
    b=r["q07r1_boundaries"]; assert all(b[k] is False for k in b)
def test_q07r1_policy_bound_transition_and_next_step():
    c=builder.build_candidate(); a=builder.admit_candidate(c); assert c["artifact_role"]=="CANDIDATE_JSON"; assert a["artifact_role"]=="APPROVED_CANONICAL_JSON"; assert a["admission"]["decision_ref"]==builder.DECISION_REF; assert a["content_governance"]["a2_unlocked"] is False
    assert a["payload"]["next_short_step"]=="A1FS-V1-U06Q08_Unit06CommunicativeFunctionAuthority"
