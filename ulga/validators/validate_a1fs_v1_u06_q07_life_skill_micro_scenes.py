from __future__ import annotations
from collections import Counter
from typing import Any, Mapping
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u06_q07_life_skill_micro_scenes as builder
VALIDATOR_ID="validate_a1fs_v1_u06_q07_life_skill_micro_scenes_v1"
SKILLS={"U01_ARTICLES_BASIC","U02_REGULAR_PLURAL_NOUNS","U03_SUBJECT_PRONOUNS","U04_BASIC_PREPOSITIONS_PLACE","U05_BE_VERB_BASIC","U06_CAN_STATEMENT"}

def _validate_payload(p:Mapping[str,Any])->list[str]:
    e=[]
    try:
        if p.get("status")!=builder.PASS_STATUS:e.append("STATUS_INVALID")
        scenes=list(p.get("micro_scenes",[])); bindings=list(p.get("sentence_scene_bindings",[])); support=list(p.get("scene_local_support_sentences",[]))
        inv=list(p.get("functional_chunk_inventory",[])); new=list(p.get("unit06_scene_derived_functional_chunks",[])); reuse=list(p.get("q04r1_exact_can_functional_reuse",[])); cv=p.get("coverage",{})
        if len(scenes)!=17 or sum(len(s.get("lines",[])) for s in scenes)!=102:e.append("FULL_SCENE_OR_SENTENCE_COUNT_INVALID")
        if len(bindings)!=49 or len({x.get("q06_sentence_id") for x in bindings})!=49:e.append("Q06_CONTEXT_BINDING_CARDINALITY_INVALID")
        if len(support)!=53:e.append("SCENE_LOCAL_SUPPORT_COUNT_INVALID")
        if any(x.get("canonical_sentence_asset") is not False or x.get("scene_local_only") is not True or x.get("target_unit_new_content") is not False for x in support):e.append("SCENE_LOCAL_SUPPORT_AUTHORITY_LEAK")
        for s in scenes:
            if s.get("canonical_scene_scope")!="UNIT06_LOCAL_AUTHORITATIVE_INSTANCE" or s.get("new_global_scene_identity_created") is not False:e.append("SCENE_SCOPE_INVALID");break
            if set(s.get("scene_skill_coverage",[]))!=SKILLS:e.append("SCENE_U01_U06_COVERAGE_INVALID");break
            if s.get("semantic_review_status")!="PASS" or not s.get("semantic_naturalness_reason"):e.append("SCENE_SEMANTIC_REVIEW_INVALID");break
        if cv.get("skill_scene_coverage_counts")!={k:17 for k in sorted(SKILLS)}:e.append("ALL_SIX_SKILLS_COVERAGE_INVALID")
        expected={"full_scene_count":17,"full_sentence_count":102,"q06_context_bound_target_occurrence_count":49,"scene_local_cumulative_support_sentence_count":53,
                  "q06_unbound_context_required_sentence_count":0,"q06_standalone_sentence_count":80,"q06_standalone_forced_binding_count":0,"q06_deferred_retained_count":6,
                  "distinct_can_functional_chunk_count":33,"q04r1_exact_can_functional_reuse_count":16,"q07_scene_derived_new_can_functional_count":17,
                  "new_global_scene_identity_count":0,"new_global_sentence_authority_count":0,"new_global_chunk_identity_count":0}
        for k,v in expected.items():
            if cv.get(k)!=v:e.append(f"COVERAGE_INVALID:{k}");break
        if cv.get("used_scene_family_count",0)<10:e.append("SCENE_FAMILY_BREADTH_INVALID")
        can=[x for x in inv if x.get("kind")=="CAN_ABILITY"]
        if len(can)!=33 or len(reuse)!=16 or len(new)!=17:e.append("CAN_FUNCTIONAL_SPLIT_INVALID")
        if {x.get("normalized_surface") for x in reuse}&{x.get("normalized_surface") for x in new}:e.append("CAN_FUNCTIONAL_SPLIT_OVERLAP")
        if any(x.get("admission_status")!="ADMITTED_UNIT06_SCENE_DERIVED_FUNCTIONAL_CHUNK" or x.get("authority_scope")!="UNIT06_LOCAL_FUNCTIONAL_CHUNK_AUTHORITY" or x.get("new_global_chunk_identity_created") is not False for x in new):e.append("SCENE_DERIVED_CHUNK_AUTHORITY_INVALID")
        if len(p.get("q06_deferred_candidates_preserved",[]))!=6 or any(x.get("decision")!="DEFER" for x in p.get("q06_deferred_candidates_preserved",[])):e.append("Q06_DEFERRED_NOT_PRESERVED")
        b=p.get("q07_boundaries",{})
        locked=("q01_mutated","q02_mutated","q03_mutated","q04_q04r1_mutated","q05_mutated","q06_mutated","global_scene_ontology_mutated","global_sentence_authority_mutated","global_chunk_identity_mutated","global_sentence_pattern_authority_mutated","communicative_function_authority_materialized","questionbank_materialized","forms_materialized","reader360_materialized","can_question_target_activated","can_negative_target_activated","non_ability_can_meaning_activated","a2_a2plus_grammar_unlocked")
        if any(b.get(k) is not False for k in locked):e.append("Q07_BOUNDARY_UNLOCK")
        if p.get("pilot_review",{}).get("operator_review_decision")!="PASS_EXPAND_TO_FULL_Q07":e.append("PILOT_EXPANSION_DECISION_INVALID")
        if p.get("next_short_step")!="A1FS-V1-U06Q08_Unit06CommunicativeFunctionAuthority":e.append("NEXT_SHORT_STEP_INVALID")
    except Exception as ex:e.append(f"PAYLOAD_VALIDATION_EXCEPTION:{type(ex).__name__}:{ex}")
    return e

def validate_candidate(candidate:Mapping[str,Any])->dict[str,Any]:
    e=[]
    try:policy_artifact.verify_artifact_digest(candidate)
    except Exception as ex:e.append(f"CANDIDATE_DIGEST:{ex}")
    if candidate.get("artifact_role")!="CANDIDATE_JSON":e.append("CANDIDATE_ROLE_INVALID")
    if candidate.get("producer_id")!=builder.TASK_ID:e.append("PRODUCER_ID_INVALID")
    if candidate.get("level_scope")!=["A1"]:e.append("LEVEL_SCOPE_INVALID")
    e+=_validate_payload(candidate.get("payload",{}))
    if e:raise ValueError(";".join(e))
    core={"validator_id":VALIDATOR_ID,"status":"PASS","candidate_artifact_sha256":candidate.get("artifact_sha256")}
    return {"validator_id":VALIDATOR_ID,"status":"PASS","receipt_sha256":builder.digest(core)}
def validate_approved(candidate:Mapping[str,Any],approved:Mapping[str,Any])->dict[str,Any]:
    e=[]
    try:policy_artifact.verify_artifact_digest(candidate);policy_artifact.verify_artifact_digest(approved)
    except Exception as ex:e.append(f"ARTIFACT_DIGEST:{ex}")
    if approved.get("artifact_role")!="APPROVED_CANONICAL_JSON":e.append("APPROVED_ROLE_INVALID")
    if approved.get("producer_id")!=builder.TASK_ID:e.append("APPROVED_PRODUCER_ID_INVALID")
    if approved.get("admission",{}).get("decision_ref")!=builder.DECISION_REF:e.append("DECISION_REF_INVALID")
    if approved.get("payload")!=candidate.get("payload"):e.append("APPROVED_PAYLOAD_DRIFT")
    e+=_validate_payload(approved.get("payload",{}))
    return {"validator_id":VALIDATOR_ID,"status":"PASS" if not e else "FAIL","error_count":len(e),"errors":e}
