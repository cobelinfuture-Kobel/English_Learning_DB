from __future__ import annotations
from collections import Counter
from ulga.builders import build_a1fs_v1_u06_q07p1_cumulative_scene_pilot as builder
def report(): return builder.build_report()
def test_q07p1_exact_six_scene_cumulative_pilot():
    r=report(); assert r["coverage"]["scene_count"]==6; assert r["coverage"]["sentence_count"]==36
    assert all(set(s["scene_skill_coverage"])=={"U01_ARTICLES_BASIC","U02_REGULAR_PLURAL_NOUNS","U03_SUBJECT_PRONOUNS","U04_BASIC_PREPOSITIONS_PLACE","U05_BE_VERB_BASIC","U06_CAN_STATEMENT"} for s in r["pilot_scenes"])
def test_q07p1_q06_target_lineage_and_scene_local_support_boundary():
    lines=[x for s in report()["pilot_scenes"] for x in s["sentences"]]; target=[x for x in lines if x["role"]=="Q06_CAN_TARGET"]; support=[x for x in lines if x["role"]=="CUMULATIVE_SUPPORT"]
    assert len(target)==11==len({x["q06_sentence_id"] for x in target}); assert all(x["canonical_sentence_asset"] is True for x in target)
    assert len(support)==25; assert all(x["canonical_sentence_asset"] is False and x["scene_local_only"] is True and x["target_unit_new_content"] is False for x in support)
def test_q07p1_pronoun_be_article_plural_place_coverage():
    c=report()["coverage"]; assert set(c["pronoun_subjects"])=={"i","you","he","she","it","we","they"}; assert set(c["be_forms"])=={"am","is","are"}; assert set(c["article_surfaces"])=={"a","an","the"}; assert {"at","in","near","on","under"}<=set(c["place_relations"]); assert len(set(c["regular_plural_nouns"]))>=5
def test_q07p1_functional_chunk_dedup_across_subjects():
    r=report(); g=Counter((x["kind"],x["normalized_surface"]) for x in r["functional_chunk_occurrences"]); assert len(r["functional_chunk_occurrences"])==36; assert len(r["functional_chunk_inventory"])==28; assert g[("CAN_ABILITY","can catch a ball")]==2; catch=[x for x in r["functional_chunk_inventory"] if x["kind"]=="CAN_ABILITY" and x["normalized_surface"]=="can catch a ball"]; assert len(catch)==1 and catch[0]["occurrence_count"]==2; assert r["coverage"]["can_functional_chunk_distinct_count"]==10
def test_q07p1_policy_bound_transition_and_boundaries():
    c=builder.build_candidate(); a=builder.admit_candidate(c); assert c["artifact_role"]=="CANDIDATE_JSON"; assert a["artifact_role"]=="APPROVED_CANONICAL_JSON"; assert a["admission"]["decision_ref"]==builder.DECISION_REF; assert a["content_governance"]["a2_unlocked"] is False
    r=a["payload"]; assert r["coverage"]["new_global_sentence_authority_count"]==0; assert r["coverage"]["new_global_scene_identity_count"]==0; assert r["coverage"]["new_global_chunk_identity_count"]==0; assert r["next_short_step"]=="A1FS-V1-U06Q07P1_PilotSemanticHumanReviewAndFullQ07ExpansionDecision"
