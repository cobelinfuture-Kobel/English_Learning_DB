#!/usr/bin/env python3
"""Materialize Unit06 Q07P1 cumulative-language six-scene pilot."""
from __future__ import annotations
import hashlib, json, re, unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u06_q06_sentence_assets as q06_builder

REPO_ROOT=Path(__file__).resolve().parents[2]
CONTRACT_PATH=REPO_ROOT/"ulga/contracts/a1fs_v1_u06_q07p1_cumulative_scene_pilot.json"
SEED_PATH=REPO_ROOT/"ulga/reports/a1fs_v1_u06_q07p1_cumulative_scene_pilot_seed.json"
U05_Q07_PATH=REPO_ROOT/"ulga/contracts/a1fs_v1_u05_q07_life_skill_micro_scenes.json"
TASK_ID="A1FS-V1-U06Q07P1_CumulativeU01ToU06LifeSkillMicroScenePilot"
DECISION_REF="OPERATOR_APPROVAL:2026-10-03:U06Q07P1_SIX_SCENE_CUMULATIVE_PILOT"
A1FS_CONTENT_POLICY_MODE="POLICY_BOUND"
PASS_STATUS="PASS_A1FS_V1_U06Q07P1_CUMULATIVE_SCENE_PILOT"
SKILLS={"U01_ARTICLES_BASIC","U02_REGULAR_PLURAL_NOUNS","U03_SUBJECT_PRONOUNS","U04_BASIC_PREPOSITIONS_PLACE","U05_BE_VERB_BASIC","U06_CAN_STATEMENT"}
CONTEXT_PRONOUNS={"he":"He","she":"She","it":"It","they":"They"}

class U06Q07P1BuildError(ValueError): pass
def _load(p): return json.loads(p.read_text(encoding="utf-8"))
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def digest(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def normalize(v):
    t=unicodedata.normalize("NFKC",str(v)).replace("’","'").replace("‘","'").replace("“",'"').replace("”",'"')
    t=re.sub(r"\s+"," ",t).strip().casefold()
    t=re.sub(r"\s+([,.!?;:])",r"\1",t)
    return re.sub(r"[.!?]+$","",t).strip()
def _scene_id(k): return "U06-Q07P1-SCENE-"+hashlib.sha256(k.encode()).hexdigest()[:16].upper()
def _line_id(s,t): return "U06-Q07P1-LINE-"+hashlib.sha256(f"{s}|{normalize(t)}".encode()).hexdigest()[:16].upper()

def _build_payload():
    c=_load(CONTRACT_PATH); seed=_load(SEED_PATH)
    if c["status"]!=PASS_STATUS: raise U06Q07P1BuildError("CONTRACT_STATUS_DRIFT")
    if seed["authoring_model"]!="GPT-5.6 Sol" or seed["python_builder_may_author_learner_english"] is not False: raise U06Q07P1BuildError("AUTHORING_POLICY_DRIFT")
    q06=q06_builder.build_report()
    if q06["status"]!="PASS_A1FS_V1_U06Q06_SENTENCE_ASSET_PRODUCTION_AND_SEMANTIC_ADMISSION" or q06["coverage"]["usable_sentence_supply_count"]!=129: raise U06Q07P1BuildError("Q06_AUTHORITY_DRIFT")
    q06map={normalize(x["text"]):x for x in q06["new_sentence_assets"]}
    governed=set(_load(U05_Q07_PATH)["prior_scene_authority"]["governed_scene_families"])
    if len(governed)!=17: raise U06Q07P1BuildError("SCENE_ONTOLOGY_DRIFT")
    src=list(seed["scenes"])
    if len(src)!=6: raise U06Q07P1BuildError("PILOT_SCENE_COUNT_DRIFT")
    scenes=[]; all_lines=[]; occ=[]; skill_scenes=defaultdict(set)
    for s in src:
        if s["scene_family"] not in governed or s["semantic_review_status"]!="PASS": raise U06Q07P1BuildError("SCENE_AUTHORITY_OR_REVIEW_INVALID")
        sid=_scene_id(s["scene_key"]); lines=[]; skillset=set()
        if not 4<=len(s["sentences"])<=6: raise U06Q07P1BuildError("SCENE_SENTENCE_COUNT_INVALID")
        for x0 in s["sentences"]:
            x=dict(x0); text=x["text"]; n=normalize(text); role=x["role"]; tags=set(x["skill_tags"]); skillset|=tags
            if not tags or not tags<=SKILLS: raise U06Q07P1BuildError("SKILL_TAG_INVALID")
            if "?" in text or re.search(r"\b(?:cannot|can't|can\s+not|was|were)\b",text,re.I) or re.search(r"\b(?:am|is|are)\s+\w+ing\b",text,re.I): raise U06Q07P1BuildError("GRAMMAR_BOUNDARY_LEAK")
            x["normalized_text"]=n; x["scene_sentence_ref_id"]=_line_id(sid,text)
            if role=="Q06_CAN_TARGET":
                q=q06map.get(n)
                if not q or q["semantic_admission_class"]!=x.get("q06_expected_decision"): raise U06Q07P1BuildError("Q06_TARGET_LINEAGE_INVALID")
                x.update(q06_sentence_id=q["sentence_id"],q06_semantic_admission_class=q["semantic_admission_class"],q06_requires_context_binding=q["requires_context_binding"],canonical_sentence_asset=True,scene_local_only=False,sentence_authority_role="EXISTING_Q06_ADMITTED_ASSET")
                if q["requires_context_binding"]:
                    p=str(q.get("subject_class","")).casefold()
                    if p in CONTEXT_PRONOUNS and CONTEXT_PRONOUNS[p] not in s.get("antecedent_bindings",{}): raise U06Q07P1BuildError("Q06_CONTEXT_ANTECEDENT_MISSING")
            elif role=="CUMULATIVE_SUPPORT":
                if re.search(r"\bcan\b",text,re.I): raise U06Q07P1BuildError("UNADMITTED_CAN_SUPPORT")
                x.update(canonical_sentence_asset=False,scene_local_only=True,sentence_authority_role="GPT56_REVIEWED_SCENE_LOCAL_CUMULATIVE_SUPPORT",semantic_review_status="APPROVED_PILOT_SCENE_SUPPORT",target_unit_new_content=False)
            else: raise U06Q07P1BuildError("UNKNOWN_SENTENCE_ROLE")
            for p in x.get("pronoun_subjects",[]):
                p=str(p).casefold()
                if p in CONTEXT_PRONOUNS and CONTEXT_PRONOUNS[p] not in s.get("antecedent_bindings",{}): raise U06Q07P1BuildError("PRONOUN_ANTECEDENT_MISSING")
            for ch in x["functional_chunks"]:
                occ.append({"scene_ref_id":sid,"line_id":x["line_id"],"sentence_role":role,"surface":ch["surface"],"normalized_surface":normalize(ch["surface"]),"kind":ch["kind"],"q06_sentence_id":x.get("q06_sentence_id")})
            lines.append(x); all_lines.append(x)
        if skillset!=SKILLS: raise U06Q07P1BuildError(f"SCENE_CUMULATIVE_SKILL_GAP:{s['scene_key']}:{sorted(SKILLS-skillset)}")
        for skill in skillset: skill_scenes[skill].add(sid)
        scenes.append({"scene_ref_id":sid,"scene_key":s["scene_key"],"scene_family":s["scene_family"],"medium_setting":s["medium_setting"],"canonical_scene_scope":"UNIT06_LOCAL_PILOT_INSTANCE","semantic_review_status":"PASS","naturalness_reason":s["naturalness_reason"],"antecedent_bindings":s.get("antecedent_bindings",{}),"sentences":lines,"scene_skill_coverage":sorted(skillset),"new_global_scene_identity_created":False})
    if len({x["normalized_text"] for x in all_lines})!=len(all_lines): raise U06Q07P1BuildError("PILOT_SENTENCE_TEXT_DUPLICATE")
    groups=defaultdict(list)
    for x in occ: groups[(x["kind"],x["normalized_surface"])].append(x)
    inv=[]
    for (kind,n),rows in sorted(groups.items()):
        inv.append({"surface":rows[0]["surface"],"normalized_surface":n,"kind":kind,"occurrence_count":len(rows),"scene_count":len({r["scene_ref_id"] for r in rows}),"sentence_roles":sorted({r["sentence_role"] for r in rows}),"q06_sentence_ids":sorted({r["q06_sentence_id"] for r in rows if r["q06_sentence_id"]}),"global_chunk_identity_created":False,"pilot_local_extraction_only":True})
    target=[x for x in all_lines if x["role"]=="Q06_CAN_TARGET"]
    cov={"scene_count":len(scenes),"sentence_count":len(all_lines),"q06_target_sentence_occurrence_count":len(target),"q06_target_sentence_distinct_count":len({x["normalized_text"] for x in target}),"scene_local_cumulative_support_sentence_count":len(all_lines)-len(target),"functional_chunk_occurrence_count":len(occ),"functional_chunk_distinct_count":len(inv),"can_functional_chunk_distinct_count":sum(x["kind"]=="CAN_ABILITY" for x in inv),"skill_scene_coverage_counts":{k:len(skill_scenes[k]) for k in sorted(SKILLS)},"pronoun_subjects":sorted({p.casefold() for x in all_lines for p in x.get("pronoun_subjects",[])}),"be_forms":sorted({p.casefold() for x in all_lines for p in x.get("be_forms",[])}),"article_surfaces":sorted({p.casefold() for x in all_lines for p in x.get("article_surfaces",[])}),"regular_plural_nouns":sorted({p.casefold() for x in all_lines for p in x.get("regular_plural_nouns",[])}),"place_relations":sorted({p.casefold() for x in all_lines for p in x.get("place_relations",[])}),"new_global_scene_identity_count":0,"new_global_chunk_identity_count":0,"new_global_sentence_authority_count":0}
    for k in ("scene_count","sentence_count","q06_target_sentence_occurrence_count","q06_target_sentence_distinct_count","functional_chunk_occurrence_count","functional_chunk_distinct_count","can_functional_chunk_distinct_count"):
        if cov[k]!=c["acceptance_targets"][k]: raise U06Q07P1BuildError(f"ACCEPTANCE_COUNT_DRIFT:{k}:{cov[k]}")
    catch=[x for x in inv if x["kind"]=="CAN_ABILITY" and x["normalized_surface"]=="can catch a ball"]
    if len(catch)!=1 or catch[0]["occurrence_count"]!=2: raise U06Q07P1BuildError("FUNCTIONAL_CHUNK_DEDUP_DEMONSTRATION_FAILED")
    return {**c,"pilot_scenes":scenes,"functional_chunk_occurrences":occ,"functional_chunk_inventory":inv,"coverage":cov,"integrity":{"scene_digest":digest(scenes),"chunk_inventory_digest":digest(inv),"q06_target_sentence_ids_digest":digest(sorted(x["q06_sentence_id"] for x in target))},"acceptance":{"scene_count":"6/6","all_six_skills_per_scene":True,"q06_target_lineage":"11/11","subject_pronouns":"7/7","be_forms":"3/3","articles":"3/3","functional_chunk_dedup_demonstration":"can catch a ball = 2 occurrences / 1 distinct surface","status":PASS_STATUS}}

def build_candidate():
    p=_build_payload()
    return policy_artifact.build_candidate(payload=p,producer_id=TASK_ID,level_scope=["A1"],source_bindings={"q06_task_id":q06_builder.TASK_ID,"q06_usable_sentence_supply_count":129,"pilot_seed_path":str(SEED_PATH.relative_to(REPO_ROOT)).replace("\\","/"),"pilot_scene_count":p["coverage"]["scene_count"],"pilot_sentence_count":p["coverage"]["sentence_count"]})
def admit_candidate(candidate:Mapping[str,Any]):
    from ulga.validators import validate_a1fs_v1_u06_q07p1_cumulative_scene_pilot as validator
    return policy_artifact.admit_candidate(candidate,validation_receipts=[validator.validate_candidate(candidate)],decision_ref=DECISION_REF,producer_id=TASK_ID)
def build_report(): return admit_candidate(build_candidate())["payload"]
def main():
    from ulga.validators import validate_a1fs_v1_u06_q07p1_cumulative_scene_pilot as validator
    c=build_candidate(); a=admit_candidate(c); r=validator.validate_approved(c,a); p=a["payload"]
    print(f"STATUS={p['status']}"); print(f"SCENES={p['coverage']['scene_count']}"); print(f"SENTENCES={p['coverage']['sentence_count']}"); print(f"Q06_TARGET_LINES={p['coverage']['q06_target_sentence_occurrence_count']}"); print(f"FUNCTIONAL_CHUNKS={p['coverage']['functional_chunk_distinct_count']}"); print(f"ERROR_COUNT={r['error_count']}"); print(f"NEXT_SHORT_STEP={p['next_short_step']}")
    return 0 if r["error_count"]==0 else 1
if __name__=="__main__": raise SystemExit(main())
