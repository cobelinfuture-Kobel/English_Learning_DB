#!/usr/bin/env python3
"""Materialize Unit06 Q07 life-skill micro-scenes from GPT-5.6-authored cumulative scene rows."""
from __future__ import annotations
import hashlib, json, re, unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u06_q06_sentence_assets as q06_builder

REPO_ROOT=Path(__file__).resolve().parents[2]
CONTRACT_PATH=REPO_ROOT/"ulga/contracts/a1fs_v1_u06_q07_life_skill_micro_scenes.json"
SEED_PATH=REPO_ROOT/"ulga/reports/a1fs_v1_u06_q07_authored_scene_seed.json"
PILOT_PATH=REPO_ROOT/"ulga/contracts/a1fs_v1_u06_q07p1_cumulative_scene_pilot.json"
Q04R1_PATH=REPO_ROOT/"ulga/contracts/a1fs_v1_u06_q04r1_yle_can_ability_chunk_expansion.json"
U05_Q07_PATH=REPO_ROOT/"ulga/contracts/a1fs_v1_u05_q07_life_skill_micro_scenes.json"
TASK_ID="A1FS-V1-U06Q07_Unit06LifeSkillMicroSceneMaterializationAndSentenceBinding"
DECISION_REF="OPERATOR_APPROVAL:2026-10-03:U06Q07_FULL_CUMULATIVE_SCENE_MATERIALIZATION"
A1FS_CONTENT_POLICY_MODE="POLICY_BOUND"
PASS_STATUS="PASS_A1FS_V1_U06Q07_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING"
SKILLS={"U01_ARTICLES_BASIC","U02_REGULAR_PLURAL_NOUNS","U03_SUBJECT_PRONOUNS","U04_BASIC_PREPOSITIONS_PLACE","U05_BE_VERB_BASIC","U06_CAN_STATEMENT"}
PRONOUN_SUBJECT_CLASSES={"I","you","he","she","it","we","they"}
CONTEXT_PRONOUN_LABEL={"he":"He","she":"She","it":"It","they":"They"}

class U06Q07BuildError(ValueError): pass
def _load(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def canonical(v:Any)->str: return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def digest(v:Any)->str: return hashlib.sha256(canonical(v).encode("utf-8")).hexdigest()
def normalize(v:Any)->str:
    t=unicodedata.normalize("NFKC",str(v)).replace("’","'").replace("‘","'").replace("“",'"').replace("”",'"')
    t=re.sub(r"\s+"," ",t).strip().casefold(); t=re.sub(r"\s+([,.!?;:])",r"\1",t)
    return re.sub(r"[.!?]+$","",t).strip()
def _scene_id(key:str)->str: return "U06-SCENE-"+hashlib.sha256(key.encode()).hexdigest()[:20].upper()
def _line_id(scene_id:str,text:str)->str: return "U06-SCENE-LINE-"+hashlib.sha256(f"{scene_id}|{normalize(text)}".encode()).hexdigest()[:20].upper()
def _target_chunk(row:Mapping[str,Any])->str:
    exact=row.get("source_functional_chunk_surface")
    if exact: return str(exact)
    m=re.search(r"\bcan\b\s+(.+?)[.!?]?$",str(row["text"]),flags=re.I)
    if not m: raise U06Q07BuildError("CAN_TARGET_CHUNK_EXTRACTION_FAILED")
    return "can "+m.group(1).strip()
def _q04r1_functional_surfaces(q04:Mapping[str,Any])->set[str]:
    g=q04["q04r1_chunk_expansion"]["non_scene_functional_chunks"]
    rows=set(g["source_grounded_or_controlled_surfaces"])
    inherited={"can drink from a cup","can eat an apple","can go to school","can make a box","can play with a ball","can run fast","can sit on a chair","can study at school","can swim fast","can walk to school","can work at home"}
    rows |= inherited
    if len(rows)!=41: raise U06Q07BuildError(f"Q04R1_FUNCTIONAL_DENOMINATOR_DRIFT:{len(rows)}")
    return rows

def _build_payload()->dict[str,Any]:
    c=_load(CONTRACT_PATH); seed=_load(SEED_PATH); pilot=_load(PILOT_PATH); q04=_load(Q04R1_PATH); prior_scene=_load(U05_Q07_PATH)
    if c["status"]!=PASS_STATUS: raise U06Q07BuildError("CONTRACT_STATUS_DRIFT")
    if pilot.get("status")!="PASS_A1FS_V1_U06Q07P1_CUMULATIVE_SCENE_PILOT": raise U06Q07BuildError("PILOT_STATUS_DRIFT")
    if c["pilot_review"]["operator_review_decision"]!="PASS_EXPAND_TO_FULL_Q07": raise U06Q07BuildError("PILOT_OPERATOR_DECISION_MISSING")
    if seed.get("authoring_model")!="GPT-5.6 Sol" or seed.get("python_builder_may_author_learner_english") is not False: raise U06Q07BuildError("AUTHORING_POLICY_DRIFT")
    q06=q06_builder.build_report()
    assets=list(q06["new_sentence_assets"]); deferred=list(q06["excluded_candidates"])
    if len(assets)!=129 or len(deferred)!=6: raise U06Q07BuildError("Q06_DENOMINATOR_DRIFT")
    context=[x for x in assets if x["requires_context_binding"] is True]; standalone=[x for x in assets if x["requires_context_binding"] is False]
    if (len(context),len(standalone))!=(49,80): raise U06Q07BuildError("Q06_CONTEXT_SPLIT_DRIFT")
    q06map={normalize(x["text"]):x for x in assets}; context_norm={normalize(x["text"]) for x in context}
    governed=set(prior_scene["prior_scene_authority"]["governed_scene_families"])
    if len(governed)!=17: raise U06Q07BuildError("SCENE_ONTOLOGY_DRIFT")
    q04surfaces=_q04r1_functional_surfaces(q04)

    scenes=[]; bindings=[]; support_lines=[]; chunk_occ=[]; seen_target_norm=[]
    skill_scene_counts=Counter(); family_counts=Counter()
    for src in seed.get("scenes",[]):
        if src.get("scene_family") not in governed: raise U06Q07BuildError("UNGOVERNED_SCENE_FAMILY")
        if src.get("semantic_review_status")!="PASS" or not src.get("semantic_naturalness_reason"): raise U06Q07BuildError("SCENE_SEMANTIC_REVIEW_MISSING")
        if len(src.get("lines",[]))!=6: raise U06Q07BuildError("FULL_SCENE_MUST_HAVE_SIX_LINES")
        sid=_scene_id(src["scene_key"]); out=[]; skills=set()
        for pos,line in enumerate(src["lines"],start=1):
            text=str(line["text"]); n=normalize(text); role=line["role"]; lid=_line_id(sid,text)
            if "?" in text or re.search(r"\b(?:cannot|can't|can\s+not|was|were)\b",text,re.I) or re.search(r"\b(?:am|is|are)\s+\w+ing\b",text,re.I):
                raise U06Q07BuildError(f"GRAMMAR_BOUNDARY_LEAK:{text}")
            if role=="Q06_CAN_TARGET":
                row=q06map.get(n)
                if not row or row.get("requires_context_binding") is not True or row.get("semantic_admission_class")!="CONTEXT_BOUND_APPROVE":
                    raise U06Q07BuildError(f"Q06_CONTEXT_TARGET_LINEAGE_INVALID:{text}")
                seen_target_norm.append(n)
                subject_class=str(row.get("subject_class",""))
                if subject_class.casefold() in CONTEXT_PRONOUN_LABEL:
                    label=CONTEXT_PRONOUN_LABEL[subject_class.casefold()]
                    if label not in src.get("antecedent_bindings",{}): raise U06Q07BuildError(f"PRONOUN_ANTECEDENT_MISSING:{text}")
                target_skills={"U06_CAN_STATEMENT"}
                if subject_class in PRONOUN_SUBJECT_CLASSES: target_skills.add("U03_SUBJECT_PRONOUNS")
                skills |= target_skills
                chunk=_target_chunk(row)
                outrow={"line_number":pos,"scene_line_id":lid,"role":role,"text":text,"normalized_text":n,"skill_tags":sorted(target_skills),
                        "q06_sentence_id":row["sentence_id"],"q06_semantic_admission_class":row["semantic_admission_class"],
                        "q06_requires_context_binding":True,"canonical_sentence_asset":True,"scene_local_only":False,
                        "sentence_authority_role":"EXISTING_Q06_ADMITTED_CONTEXT_BOUND_ASSET","functional_chunk_surface":chunk,"functional_chunk_kind":"CAN_ABILITY"}
                bindings.append({"q06_sentence_id":row["sentence_id"],"sentence_text":text,"scene_ref_id":sid,"scene_line_id":lid,"context_binding_satisfied":True,"binding_cardinality_role":"EXACTLY_ONCE"})
                chunk_occ.append({"scene_ref_id":sid,"scene_line_id":lid,"sentence_role":role,"surface":chunk,"normalized_surface":normalize(chunk),"kind":"CAN_ABILITY","q06_sentence_id":row["sentence_id"]})
            elif role=="CUMULATIVE_SUPPORT":
                if re.search(r"\bcan\b",text,re.I): raise U06Q07BuildError("SUPPORT_CAN_LEAK")
                tags=set(line.get("skill_tags",[]))
                if not tags or not tags <= (SKILLS-{"U06_CAN_STATEMENT"}): raise U06Q07BuildError("SUPPORT_SKILL_TAG_INVALID")
                skills |= tags
                chunk=str(line.get("functional_chunk_surface","")).strip()
                if not chunk: raise U06Q07BuildError("SUPPORT_FUNCTIONAL_CHUNK_MISSING")
                outrow={"line_number":pos,"scene_line_id":lid,"role":role,"text":text,"normalized_text":n,"skill_tags":sorted(tags),
                        "canonical_sentence_asset":False,"scene_local_only":True,"target_unit_new_content":False,
                        "sentence_authority_role":"GPT56_REVIEWED_SCENE_LOCAL_CUMULATIVE_SUPPORT","semantic_review_status":"APPROVED_FULL_Q07_SCENE_SUPPORT",
                        "functional_chunk_surface":chunk,"functional_chunk_kind":str(line.get("functional_chunk_kind","CUMULATIVE_SUPPORT"))}
                support_lines.append(outrow)
                chunk_occ.append({"scene_ref_id":sid,"scene_line_id":lid,"sentence_role":role,"surface":chunk,"normalized_surface":normalize(chunk),"kind":outrow["functional_chunk_kind"],"q06_sentence_id":None})
            else: raise U06Q07BuildError("UNKNOWN_LINE_ROLE")
            out.append(outrow)
        if skills!=SKILLS: raise U06Q07BuildError(f"SCENE_U01_U06_COVERAGE_GAP:{src['scene_key']}:{sorted(SKILLS-skills)}")
        for k in skills: skill_scene_counts[k]+=1
        family_counts[src["scene_family"]]+=1
        scenes.append({"scene_ref_id":sid,"scene_key":src["scene_key"],"unit_id":"GRAMMAR_CAN_STATEMENT","unit_number":6,
                       "canonical_scene_scope":"UNIT06_LOCAL_AUTHORITATIVE_INSTANCE","scene_family":src["scene_family"],"medium_setting":src["medium_setting"],
                       "semantic_review_status":"PASS","semantic_naturalness_reason":src["semantic_naturalness_reason"],
                       "antecedent_bindings":src.get("antecedent_bindings",{}),"scene_skill_coverage":sorted(skills),"lines":out,
                       "new_global_scene_identity_created":False})

    if len(scenes)!=17: raise U06Q07BuildError("FULL_SCENE_COUNT_DRIFT")
    if len(seen_target_norm)!=49 or set(seen_target_norm)!=context_norm or len(set(seen_target_norm))!=49:
        raise U06Q07BuildError("Q06_CONTEXT_BOUND_BINDING_SET_MISMATCH")
    if len(bindings)!=49 or len({x["q06_sentence_id"] for x in bindings})!=49: raise U06Q07BuildError("Q06_BINDING_CARDINALITY_INVALID")
    if len(support_lines)!=53: raise U06Q07BuildError("SUPPORT_SENTENCE_COUNT_DRIFT")
    if any(x["normalized_text"] in context_norm for x in support_lines): raise U06Q07BuildError("SUPPORT_COLLIDES_WITH_CONTEXT_TARGET")

    groups=defaultdict(list)
    for x in chunk_occ: groups[(x["kind"],x["normalized_surface"])].append(x)
    inventory=[]
    for (kind,n),rows in sorted(groups.items()):
        inventory.append({"surface":rows[0]["surface"],"normalized_surface":n,"kind":kind,"occurrence_count":len(rows),
                          "scene_count":len({r["scene_ref_id"] for r in rows}),"q06_sentence_ids":sorted({r["q06_sentence_id"] for r in rows if r["q06_sentence_id"]}),
                          "global_chunk_identity_created":False})
    can_inv=[x for x in inventory if x["kind"]=="CAN_ABILITY"]
    can_surfaces={x["normalized_surface"] for x in can_inv}
    q04_norm={normalize(x) for x in q04surfaces}
    reused=[x for x in can_inv if x["normalized_surface"] in q04_norm]
    new=[{**x,"admission_status":"ADMITTED_UNIT06_SCENE_DERIVED_FUNCTIONAL_CHUNK","authority_scope":"UNIT06_LOCAL_FUNCTIONAL_CHUNK_AUTHORITY",
          "source_claim":"Q07_ADMITTED_SCENE_PLUS_Q06_CONTEXT_BOUND_SENTENCE","new_global_chunk_identity_created":False}
         for x in can_inv if x["normalized_surface"] not in q04_norm]
    if (len(can_inv),len(reused),len(new))!=(33,16,17): raise U06Q07BuildError(f"CAN_FUNCTIONAL_SPLIT_DRIFT:{len(can_inv)}:{len(reused)}:{len(new)}")

    coverage={"full_scene_count":len(scenes),"full_sentence_count":sum(len(s["lines"]) for s in scenes),
              "q06_context_bound_target_occurrence_count":len(bindings),"scene_local_cumulative_support_sentence_count":len(support_lines),
              "q06_unbound_context_required_sentence_count":0,"q06_standalone_sentence_count":80,"q06_standalone_forced_binding_count":0,
              "q06_deferred_retained_count":len(deferred),"used_scene_family_count":len(family_counts),"used_scene_family_counts":dict(sorted(family_counts.items())),
              "skill_scene_coverage_counts":dict(sorted(skill_scene_counts.items())),"functional_chunk_occurrence_count":len(chunk_occ),
              "functional_chunk_distinct_count":len(inventory),"distinct_can_functional_chunk_count":len(can_inv),
              "q04r1_exact_can_functional_reuse_count":len(reused),"q07_scene_derived_new_can_functional_count":len(new),
              "new_global_scene_identity_count":0,"new_global_sentence_authority_count":0,"new_global_chunk_identity_count":0}
    a=c["acceptance_targets"]
    checks={"full_scene_count":17,"full_sentence_count":102,"q06_context_bound_target_occurrence_count":49,
            "scene_local_cumulative_support_sentence_count":53,"q06_unbound_context_required_sentence_count":0,
            "q06_standalone_forced_binding_count":0,"q06_deferred_retained_count":6,"distinct_can_functional_chunk_count":33,
            "q04r1_exact_can_functional_reuse_count":16,"q07_scene_derived_new_can_functional_count":17}
    for k,v in checks.items():
        if coverage[k]!=v or a[k]!=v: raise U06Q07BuildError(f"ACCEPTANCE_TARGET_DRIFT:{k}:{coverage[k]}:{a[k]}")
    if coverage["used_scene_family_count"]<a["minimum_used_scene_family_count"]: raise U06Q07BuildError("SCENE_FAMILY_BREADTH_TOO_LOW")
    if coverage["skill_scene_coverage_counts"]!={k:17 for k in sorted(SKILLS)}: raise U06Q07BuildError("ALL_SIX_SKILLS_NOT_IN_ALL_SCENES")

    return {**c,"micro_scenes":scenes,"sentence_scene_bindings":bindings,
            "scene_local_support_sentences":support_lines,"functional_chunk_occurrences":chunk_occ,
            "functional_chunk_inventory":inventory,"q04r1_exact_can_functional_reuse":reused,
            "unit06_scene_derived_functional_chunks":new,
            "q06_deferred_candidates_preserved":[{"candidate_id":x["candidate_id"],"text":x["text"],"semantic_admission_reason":x["semantic_admission_reason"],"decision":x["decision"]} for x in deferred],
            "coverage":coverage,
            "integrity":{"scene_digest":digest(scenes),"binding_digest":digest(bindings),"functional_chunk_inventory_digest":digest(inventory),
                         "scene_derived_can_chunk_digest":digest(new)},
            "acceptance":{"q06_context_required_sentence_bindings":"49/49","q06_unbound_context_required_sentence_count":0,
                          "all_six_skills_scene_coverage":"17/17","distinct_can_functional_chunks":33,
                          "q04r1_exact_can_functional_reuse":16,"q07_scene_derived_new_can_functional_chunks":17,
                          "q06_deferred_candidates_retained":"6/6","status":PASS_STATUS}}

def build_candidate()->dict[str,Any]:
    p=_build_payload()
    return policy_artifact.build_candidate(payload=p,producer_id=TASK_ID,level_scope=["A1"],source_bindings={
        "q06_task_id":q06_builder.TASK_ID,"q06_usable_sentence_supply_count":129,"q06_context_bound_sentence_count":49,
        "q07_seed_path":str(SEED_PATH.relative_to(REPO_ROOT)).replace("\\","/"),"full_scene_count":17,
        "q07_scene_derived_new_can_functional_count":p["coverage"]["q07_scene_derived_new_can_functional_count"]})
def admit_candidate(candidate:Mapping[str,Any])->dict[str,Any]:
    from ulga.validators import validate_a1fs_v1_u06_q07_life_skill_micro_scenes as validator
    return policy_artifact.admit_candidate(candidate,validation_receipts=[validator.validate_candidate(candidate)],decision_ref=DECISION_REF,producer_id=TASK_ID)
def build_report()->dict[str,Any]: return admit_candidate(build_candidate())["payload"]
def main()->int:
    from ulga.validators import validate_a1fs_v1_u06_q07_life_skill_micro_scenes as validator
    c=build_candidate(); a=admit_candidate(c); r=validator.validate_approved(c,a); p=a["payload"]; cv=p["coverage"]
    print(f"STATUS={p['status']}"); print(f"SCENES={cv['full_scene_count']}"); print(f"SENTENCES={cv['full_sentence_count']}")
    print(f"BOUND_CONTEXT_Q06={cv['q06_context_bound_target_occurrence_count']}"); print(f"SCENE_LOCAL_SUPPORT={cv['scene_local_cumulative_support_sentence_count']}")
    print(f"CAN_CHUNKS={cv['distinct_can_functional_chunk_count']}"); print(f"Q07_NEW_SCENE_CAN_CHUNKS={cv['q07_scene_derived_new_can_functional_count']}")
    print(f"ERROR_COUNT={r['error_count']}"); print(f"NEXT_SHORT_STEP={p['next_short_step']}")
    return 0 if r["error_count"]==0 else 1
if __name__=="__main__": raise SystemExit(main())
