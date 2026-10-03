#!/usr/bin/env python3
"""Expand all 62 Q04R1 YLE-backed Unit06 ability verbs into reviewed multiword functional chunks."""
from __future__ import annotations
import hashlib, json, re, unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u06_q07_life_skill_micro_scenes as q07_builder

REPO_ROOT=Path(__file__).resolve().parents[2]
CONTRACT_PATH=REPO_ROOT/"ulga/contracts/a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion.json"
SEED_PATH=REPO_ROOT/"ulga/reports/a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion_seed.json"
Q04R1_PATH=REPO_ROOT/"ulga/contracts/a1fs_v1_u06_q04r1_yle_can_ability_chunk_expansion.json"
U05_Q07_PATH=REPO_ROOT/"ulga/contracts/a1fs_v1_u05_q07_life_skill_micro_scenes.json"
TASK_ID="A1FS-V1-U06Q07R1_YLEAbilityVerbFunctionalChunkSemanticExpansion"
DECISION_REF="OPERATOR_APPROVAL:2026-10-03:U06Q07R1_YLE_ABILITY_VERB_FUNCTIONAL_CHUNK_EXPANSION"
A1FS_CONTENT_POLICY_MODE="POLICY_BOUND"
PASS_STATUS="PASS_A1FS_V1_U06Q07R1_YLE_ABILITY_VERB_FUNCTIONAL_CHUNK_SEMANTIC_EXPANSION"
ALLOWED_DECISIONS={"APPROVE","SCENE_GROUNDED_APPROVE"}

class U06Q07R1BuildError(ValueError): pass
def _load(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def canonical(v:Any)->str: return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def digest(v:Any)->str: return hashlib.sha256(canonical(v).encode("utf-8")).hexdigest()
def normalize(v:Any)->str:
    t=unicodedata.normalize("NFKC",str(v)).replace("’","'").replace("‘","'").replace("“",'"').replace("”",'"')
    t=re.sub(r"\s+"," ",t).strip().casefold()
    return re.sub(r"[.!?]+$","",t).strip()

def _q04r1_verbs(q04:Mapping[str,Any])->list[str]:
    g=q04["q04r1_chunk_expansion"]["can_base_verb"]
    rows=[*g["prior_surfaces"],*g["newly_admitted_surfaces"]]
    if len(rows)!=62 or len(set(rows))!=62: raise U06Q07R1BuildError("Q04R1_VERB_DENOMINATOR_DRIFT")
    return [x.removeprefix("can ") for x in rows]

def _q04r1_functional(q04:Mapping[str,Any])->set[str]:
    g=q04["q04r1_chunk_expansion"]["non_scene_functional_chunks"]
    rows=set(g["source_grounded_or_controlled_surfaces"])
    rows |= {"can drink from a cup","can eat an apple","can go to school","can make a box","can play with a ball","can run fast","can sit on a chair","can study at school","can swim fast","can walk to school","can work at home"}
    if len(rows)!=41: raise U06Q07R1BuildError(f"Q04R1_FUNCTIONAL_BASELINE_DRIFT:{len(rows)}")
    return rows

def _existing_baseline(q04:Mapping[str,Any])->set[str]:
    q04_rows={normalize(x) for x in _q04r1_functional(q04)}
    q07=q07_builder.build_report()
    if q07["status"]!="PASS_A1FS_V1_U06Q07_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING":
        raise U06Q07R1BuildError("Q07_STATUS_DRIFT")
    q07_can={x["normalized_surface"] for x in q07["functional_chunk_inventory"] if x["kind"]=="CAN_ABILITY"}
    merged=q04_rows|q07_can
    if len(q07_can)!=33 or len(merged)!=58: raise U06Q07R1BuildError(f"EXISTING_CAN_CHUNK_BASELINE_DRIFT:{len(q07_can)}:{len(merged)}")
    return merged

def _build_payload()->dict[str,Any]:
    c=_load(CONTRACT_PATH); seed=_load(SEED_PATH); q04=_load(Q04R1_PATH); prior_scene=_load(U05_Q07_PATH)
    if c["status"]!=PASS_STATUS: raise U06Q07R1BuildError("CONTRACT_STATUS_DRIFT")
    if seed.get("authoring_model")!="GPT-5.6 Sol" or seed.get("python_builder_may_author_learner_english") is not False:
        raise U06Q07R1BuildError("AUTHORING_POLICY_DRIFT")
    verbs=_q04r1_verbs(q04); verb_set=set(verbs); baseline=_existing_baseline(q04)
    governed=set(prior_scene["prior_scene_authority"]["governed_scene_families"])
    if len(governed)!=17: raise U06Q07R1BuildError("SCENE_FAMILY_ONTOLOGY_DRIFT")
    rows=list(seed.get("candidates",[]))
    if len(rows)!=124: raise U06Q07R1BuildError("CANDIDATE_COUNT_DRIFT")
    by_verb=defaultdict(list); normalized=[]
    for row in rows:
        verb=str(row["base_verb"]); surface=str(row["functional_chunk_surface"]); n=normalize(surface)
        if verb not in verb_set or row.get("source_can_base_surface")!=f"can {verb}": raise U06Q07R1BuildError("SOURCE_VERB_LINEAGE_INVALID")
        if row.get("decision") not in ALLOWED_DECISIONS: raise U06Q07R1BuildError("DECISION_INVALID")
        if not n.startswith(f"can {verb} "): raise U06Q07R1BuildError(f"NOT_MULTIWORD_EXPANSION:{surface}")
        if "?" in surface or re.search(r"\b(?:cannot|can't|can\s+not)\b",surface,re.I): raise U06Q07R1BuildError("NEGATIVE_OR_QUESTION_LEAK")
        sg=row.get("scene_grounding",{})
        if sg.get("scene_family") not in governed or sg.get("ability_reading_required") is not True or sg.get("permission_availability_reading_blocked") is not True:
            raise U06Q07R1BuildError("SCENE_GROUNDING_INVALID")
        if row["decision"]=="SCENE_GROUNDED_APPROVE" and not sg.get("grounding_directive"): raise U06Q07R1BuildError("SCENE_GROUNDED_DIRECTIVE_MISSING")
        if row.get("creates_new_global_vocabulary_identity") is not False or row.get("creates_new_global_chunk_identity") is not False:
            raise U06Q07R1BuildError("GLOBAL_IDENTITY_LEAK")
        if n in baseline: raise U06Q07R1BuildError(f"EXPANSION_OVERLAPS_EXISTING_BASELINE:{surface}")
        by_verb[verb].append(row); normalized.append(n)
    if len(set(normalized))!=124: raise U06Q07R1BuildError("EXPANSION_DUPLICATE")
    if set(by_verb)!=verb_set or any(len(by_verb[v])!=2 for v in verbs): raise U06Q07R1BuildError("PER_VERB_TWO_CANDIDATES_REQUIRED")

    admitted=[]
    for row in rows:
        n=normalize(row["functional_chunk_surface"])
        admitted.append({
            "chunk_id":"U06-FCH-"+hashlib.sha256(n.encode("utf-8")).hexdigest()[:20].upper(),
            "unit_id":"GRAMMAR_CAN_STATEMENT","unit_number":6,"level":"A1",
            "surface":row["functional_chunk_surface"],"normalized_surface":n,
            "base_verb":row["base_verb"],"source_can_base_surface":row["source_can_base_surface"],
            "semantic_admission_class":row["decision"],"semantic_review_reason":row["semantic_review_reason"],
            "scene_grounding":row["scene_grounding"],"authority_scope":"UNIT06_LOCAL_FUNCTIONAL_CHUNK_AUTHORITY",
            "source_claim":"Q04R1_YLE_ABILITY_VERB_PLUS_GPT56_SEMANTIC_MULTIWORD_EXPANSION_AND_SCENE_GROUNDING",
            "creates_new_global_chunk_identity":False,"creates_new_global_vocabulary_identity":False
        })

    decision_counts=Counter(x["semantic_admission_class"] for x in admitted)
    family_counts=Counter(x["scene_grounding"]["scene_family"] for x in admitted)
    per_verb={v:len(by_verb[v]) for v in sorted(verbs)}
    coverage={
        "source_verb_count":len(verbs),"candidate_count":len(rows),
        "approve_count":decision_counts["APPROVE"],"scene_grounded_approve_count":decision_counts["SCENE_GROUNDED_APPROVE"],
        "existing_distinct_can_chunk_baseline":len(baseline),"admitted_new_distinct_chunk_count":len(admitted),
        "cumulative_distinct_can_chunk_count_after_q07r1":len(baseline)+len(admitted),
        "source_verbs_with_at_least_two_new_chunks":sum(1 for v in verbs if len(by_verb[v])>=2),
        "source_verbs_with_zero_new_chunks":sum(1 for v in verbs if not by_verb[v]),
        "per_verb_new_chunk_counts":per_verb,"scene_family_chunk_counts":dict(sorted(family_counts.items())),
        "new_global_chunk_identity_count":0,"new_global_vocabulary_identity_count":0
    }
    for k,v in c["acceptance_targets"].items():
        if k in coverage and coverage[k]!=v: raise U06Q07R1BuildError(f"ACCEPTANCE_TARGET_DRIFT:{k}:{coverage[k]}:{v}")
    return {**c,"existing_chunk_baseline":{
                "q04r1_distinct_functional_chunks":41,
                "q07_distinct_context_bound_can_chunks":33,
                "q04r1_plus_q07_distinct_union":58,
                "normalized_surfaces":sorted(baseline)},
            "new_unit06_functional_chunks":admitted,
            "coverage_report":coverage,
            "integrity":{"new_chunk_digest":digest(admitted),"coverage_digest":digest(coverage)},
            "acceptance":{**coverage,"status":PASS_STATUS}}

def build_candidate()->dict[str,Any]:
    p=_build_payload()
    return policy_artifact.build_candidate(payload=p,producer_id=TASK_ID,level_scope=["A1"],source_bindings={
        "q04r1_path":str(Q04R1_PATH.relative_to(REPO_ROOT)).replace("\\","/"),
        "q07_task_id":q07_builder.TASK_ID,"q07r1_seed_path":str(SEED_PATH.relative_to(REPO_ROOT)).replace("\\","/"),
        "source_verb_count":62,"candidate_count":124,"existing_chunk_baseline":58})
def admit_candidate(candidate:Mapping[str,Any])->dict[str,Any]:
    from ulga.validators import validate_a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion as validator
    return policy_artifact.admit_candidate(candidate,validation_receipts=[validator.validate_candidate(candidate)],decision_ref=DECISION_REF,producer_id=TASK_ID)
def build_report()->dict[str,Any]: return admit_candidate(build_candidate())["payload"]
def main()->int:
    from ulga.validators import validate_a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion as validator
    c=build_candidate(); a=admit_candidate(c); r=validator.validate_approved(c,a); p=a["payload"]; cv=p["coverage_report"]
    print(f"STATUS={p['status']}"); print(f"SOURCE_VERBS={cv['source_verb_count']}"); print(f"NEW_CHUNKS={cv['admitted_new_distinct_chunk_count']}")
    print(f"EXISTING_BASELINE={cv['existing_distinct_can_chunk_baseline']}"); print(f"CUMULATIVE_CAN_CHUNKS={cv['cumulative_distinct_can_chunk_count_after_q07r1']}")
    print(f"ERROR_COUNT={r['error_count']}"); print(f"NEXT_SHORT_STEP={p['next_short_step']}")
    return 0 if r["error_count"]==0 else 1
if __name__=="__main__": raise SystemExit(main())
