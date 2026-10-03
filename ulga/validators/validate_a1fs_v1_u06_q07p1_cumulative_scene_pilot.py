from __future__ import annotations
from collections import Counter
from typing import Any, Mapping
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u06_q07p1_cumulative_scene_pilot as builder
VALIDATOR_ID="validate_a1fs_v1_u06_q07p1_cumulative_scene_pilot_v1"
SKILLS={"U01_ARTICLES_BASIC","U02_REGULAR_PLURAL_NOUNS","U03_SUBJECT_PRONOUNS","U04_BASIC_PREPOSITIONS_PLACE","U05_BE_VERB_BASIC","U06_CAN_STATEMENT"}

def _validate_payload(p:Mapping[str,Any])->list[str]:
    e=[]
    try:
        if p.get("status")!=builder.PASS_STATUS:e.append("STATUS_INVALID")
        scenes=list(p.get("pilot_scenes",[])); lines=[x for s in scenes for x in s.get("sentences",[])]; occ=list(p.get("functional_chunk_occurrences",[])); inv=list(p.get("functional_chunk_inventory",[])); c=p.get("coverage",{})
        if len(scenes)!=6 or len(lines)!=36:e.append("PILOT_COUNT_INVALID")
        if len({s.get("scene_ref_id") for s in scenes})!=6 or len({x.get("scene_sentence_ref_id") for x in lines})!=36:e.append("IDENTITY_NOT_DISTINCT")
        for s in scenes:
            if s.get("canonical_scene_scope")!="UNIT06_LOCAL_PILOT_INSTANCE" or s.get("new_global_scene_identity_created") is not False or set(s.get("scene_skill_coverage",[]))!=SKILLS:e.append("SCENE_SCOPE_OR_SKILL_INVALID");break
        target=[x for x in lines if x.get("role")=="Q06_CAN_TARGET"]; support=[x for x in lines if x.get("role")=="CUMULATIVE_SUPPORT"]
        if len(target)!=11 or len({x.get("q06_sentence_id") for x in target})!=11:e.append("Q06_TARGET_LINEAGE_INVALID")
        if any(x.get("canonical_sentence_asset") is not True or x.get("sentence_authority_role")!="EXISTING_Q06_ADMITTED_ASSET" for x in target):e.append("Q06_TARGET_AUTHORITY_INVALID")
        if len(support)!=25 or any(x.get("canonical_sentence_asset") is not False or x.get("scene_local_only") is not True or x.get("target_unit_new_content") is not False for x in support):e.append("SUPPORT_SCOPE_INVALID")
        if any(x.get("sentence_authority_role")!="GPT56_REVIEWED_SCENE_LOCAL_CUMULATIVE_SUPPORT" for x in support):e.append("SUPPORT_AUTHORITY_ROLE_INVALID")
        expected={"scene_count":6,"sentence_count":36,"q06_target_sentence_occurrence_count":11,"q06_target_sentence_distinct_count":11,"functional_chunk_occurrence_count":36,"functional_chunk_distinct_count":28,"can_functional_chunk_distinct_count":10}
        for k,v in expected.items():
            if c.get(k)!=v:e.append(f"COVERAGE_INVALID:{k}");break
        if c.get("skill_scene_coverage_counts")!={k:6 for k in sorted(SKILLS)}:e.append("ALL_SIX_SKILLS_NOT_IN_ALL_SCENES")
        if set(c.get("pronoun_subjects",[]))!={"i","you","he","she","it","we","they"}:e.append("PRONOUN_7_OF_7_INVALID")
        if set(c.get("be_forms",[]))!={"am","is","are"}:e.append("BE_3_OF_3_INVALID")
        if set(c.get("article_surfaces",[]))!={"a","an","the"}:e.append("ARTICLE_3_OF_3_INVALID")
        if not {"at","in","near","on","under"}<=set(c.get("place_relations",[])):e.append("PLACE_COVERAGE_INVALID")
        if len(set(c.get("regular_plural_nouns",[])))<5:e.append("PLURAL_COVERAGE_INVALID")
        groups=Counter((x.get("kind"),x.get("normalized_surface")) for x in occ); idx={(x.get("kind"),x.get("normalized_surface")):x for x in inv}
        if len(occ)!=36 or len(groups)!=28 or set(groups)!=set(idx):e.append("FUNCTIONAL_INVENTORY_INVALID")
        else:
            for k,n in groups.items():
                if idx[k].get("occurrence_count")!=n or idx[k].get("global_chunk_identity_created") is not False:e.append("FUNCTIONAL_COUNT_OR_GLOBAL_ID_INVALID");break
        catch=idx.get(("CAN_ABILITY","can catch a ball"))
        if not catch or catch.get("occurrence_count")!=2:e.append("CATCH_DEDUP_INVALID")
        b=p.get("q07p1_boundaries",{})
        locked=("q01_mutated","q02_mutated","q03_mutated","q04_q04r1_mutated","q05_mutated","q06_mutated","global_scene_ontology_mutated","global_chunk_identity_mutated","global_sentence_pattern_authority_mutated","reader360_materialized","questionbank_materialized","forms_materialized","can_question_target_activated","can_negative_target_activated","non_ability_can_meaning_activated","a2_a2plus_grammar_unlocked")
        if any(b.get(k) is not False for k in locked):e.append("PILOT_BOUNDARY_UNLOCK")
        if c.get("new_global_sentence_authority_count")!=0 or c.get("new_global_scene_identity_count")!=0 or c.get("new_global_chunk_identity_count")!=0:e.append("GLOBAL_IDENTITY_NONZERO")
        if p.get("next_short_step")!="A1FS-V1-U06Q07P1_PilotSemanticHumanReviewAndFullQ07ExpansionDecision":e.append("NEXT_SHORT_STEP_INVALID")
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
