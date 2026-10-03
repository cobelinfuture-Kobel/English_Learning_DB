from __future__ import annotations
from collections import Counter
from typing import Any, Mapping
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion as builder
VALIDATOR_ID="validate_a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion_v1"

def _validate_payload(p:Mapping[str,Any])->list[str]:
    e=[]
    try:
        if p.get("status")!=builder.PASS_STATUS:e.append("STATUS_INVALID")
        rows=list(p.get("new_unit06_functional_chunks",[])); cv=p.get("coverage_report",{})
        if len(rows)!=124:e.append("NEW_CHUNK_COUNT_INVALID")
        if len({x.get("normalized_surface") for x in rows})!=124:e.append("NEW_CHUNK_NOT_DISTINCT")
        if len({x.get("chunk_id") for x in rows})!=124:e.append("CHUNK_ID_NOT_DISTINCT")
        counts=Counter(x.get("semantic_admission_class") for x in rows)
        if counts!={"APPROVE":88,"SCENE_GROUNDED_APPROVE":36}:e.append("DECISION_COUNTS_INVALID")
        per=Counter(x.get("base_verb") for x in rows)
        if len(per)!=62 or any(v!=2 for v in per.values()):e.append("PER_VERB_COVERAGE_INVALID")
        if any(x.get("authority_scope")!="UNIT06_LOCAL_FUNCTIONAL_CHUNK_AUTHORITY" or x.get("creates_new_global_chunk_identity") is not False or x.get("creates_new_global_vocabulary_identity") is not False for x in rows):e.append("AUTHORITY_SCOPE_INVALID")
        if any(not x.get("scene_grounding",{}).get("grounding_directive") or x.get("scene_grounding",{}).get("ability_reading_required") is not True for x in rows):e.append("SCENE_GROUNDING_MISSING")
        expected={"source_verb_count":62,"candidate_count":124,"approve_count":88,"scene_grounded_approve_count":36,
                  "existing_distinct_can_chunk_baseline":58,"admitted_new_distinct_chunk_count":124,
                  "cumulative_distinct_can_chunk_count_after_q07r1":182,"source_verbs_with_at_least_two_new_chunks":62,
                  "source_verbs_with_zero_new_chunks":0,"new_global_chunk_identity_count":0,"new_global_vocabulary_identity_count":0}
        for k,v in expected.items():
            if cv.get(k)!=v:e.append(f"COVERAGE_INVALID:{k}");break
        base=p.get("existing_chunk_baseline",{})
        if base.get("q04r1_distinct_functional_chunks")!=41 or base.get("q07_distinct_context_bound_can_chunks")!=33 or base.get("q04r1_plus_q07_distinct_union")!=58:e.append("BASELINE_INVALID")
        if set(base.get("normalized_surfaces",[])) & {x.get("normalized_surface") for x in rows}:e.append("NEW_CHUNK_OVERLAPS_BASELINE")
        b=p.get("q07r1_boundaries",{})
        locked=("q01_mutated","q02_mutated","q03_mutated","q04_q04r1_mutated","q05_mutated","q06_mutated","q07_mutated","sentence_assets_materialized","scenes_rewritten","global_scene_ontology_mutated","global_chunk_identity_mutated","global_vocabulary_identity_mutated","communicative_function_authority_materialized","questionbank_materialized","forms_materialized","reader360_materialized","can_question_target_activated","can_negative_target_activated","non_ability_can_meaning_activated","a2_a2plus_grammar_unlocked")
        if any(b.get(k) is not False for k in locked):e.append("Q07R1_BOUNDARY_UNLOCK")
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
