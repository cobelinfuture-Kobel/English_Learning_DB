#!/usr/bin/env python3
"""Admit model-authored Unit01 life scenes from approved semantic anchors."""
from __future__ import annotations
import argparse, json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence
from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as r1

A1FS_CONTENT_POLICY_MODE="POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION=""
PROGRAM_ID="A1FS-V1"
TASK_ID="A1FS-V1-U01QB07_Unit01MicroSceneSeedEnrichmentAndRotationCapacityExpansion"
SCHEMA_VERSION="a1fs.v1.u01qb07.unit01_cumulative_scene_pool.v1"
SPEC_SCHEMA_VERSION="a1fs.v1.u01qb07.unit01_model_authored_scene_supplement.v1"
PASS_STATUS="PASS_A1FS_V1_U01QB07_UNIT01_MICRO_SCENE_SEED_ENRICHMENT_AND_ROTATION_CAPACITY_EXPANSION"
UNIT_ID="GRAMMAR_ARTICLES_BASIC"
TARGET_MIN=28; TARGET_MAX=36; EXPECTED_SUPPLEMENT_COUNT=27
DEFAULT_SPEC=Path("ulga/contracts/a1fs_v1_u01qb07_unit01_model_authored_scene_supplement.json")
DEFAULT_OUTPUT=Path("ulga/reports/a1fs_v1_u01qb07_unit01_cumulative_scene_pool.json")
NEXT_SHORT_STEP="A1FS-V1-U01QB08_Unit01TwelveFormSceneRotationMaterialization"

class SceneEnrichmentError(ValueError):pass

def read_json(p:Path)->Any:
 try:return json.loads(p.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError) as e:raise SceneEnrichmentError(f"UNREADABLE_JSON:{p}:{e}") from e
def write_json(p:Path,v:Mapping[str,Any])->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(dict(v),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def inventory_rows(inv:Mapping[str,Any])->list[dict[str,Any]]:
 rows=inv.get("scene_rows")
 if not isinstance(rows,list) or not all(isinstance(x,Mapping) for x in rows):raise SceneEnrichmentError("R1_SCENE_ROWS_REQUIRED")
 return [deepcopy(dict(x)) for x in rows]
def candidates(spec:Mapping[str,Any])->list[dict[str,Any]]:
 if spec.get("schema_version")!=SPEC_SCHEMA_VERSION or spec.get("task_id")!=TASK_ID or spec.get("unit_id")!=UNIT_ID:raise SceneEnrichmentError("SUPPLEMENT_SPEC_IDENTITY_INVALID")
 rows=spec.get("candidates")
 if not isinstance(rows,list) or len(rows)!=EXPECTED_SUPPLEMENT_COUNT or not all(isinstance(x,Mapping) for x in rows):raise SceneEnrichmentError("SUPPLEMENT_27_CANDIDATES_REQUIRED")
 return [deepcopy(dict(x)) for x in rows]
def eligible_anchor_rows(rows:Sequence[Mapping[str,Any]])->list[Mapping[str,Any]]:
 return [x for x in rows if x.get("scene_origin")=="CANONICAL_UNIT01_CONTEXT" or (x.get("scene_origin")=="REAL62_CONTENT_ASSET" and x.get("lineage_mode")!="PROJECT_AUTHORED_CONTRACT_COMPLETION")]
def resolve_anchor_refs(objects:set[str],anchors:Sequence[Mapping[str,Any]])->list[str]:
 remaining=set(objects); chosen=[]
 while remaining:
  ranked=sorted(((len(remaining & set(r.get("semantic_scene_core",{}).get("objects") or [])),str(r.get("scene_ref_id") or ""),r) for r in anchors),key=lambda x:(-x[0],x[1]))
  if not ranked or ranked[0][0]==0:raise SceneEnrichmentError("UNBACKED_MODEL_OBJECTS:"+",".join(sorted(remaining)))
  _,ref,row=ranked[0];chosen.append(ref);remaining-=set(row.get("semantic_scene_core",{}).get("objects") or [])
 return chosen
def model_scene_row(c:Mapping[str,Any],anchors:Sequence[Mapping[str,Any]])->dict[str,Any]:
 required={"candidate_id","introduced_unit_id","source_class","large_situation_family","medium_setting","small_micro_scene_event","participants","objects","actions","relations","information_structure","communicative_function_ids","communicative_goal","source_claim"}
 if required-set(c):raise SceneEnrichmentError("CANDIDATE_FIELDS_MISSING:"+str(c.get("candidate_id")))
 if c["source_class"]!="MODEL_AUTHORED_FROM_APPROVED_SEEDS" or c["source_claim"]!="SEED_ANCHORED_MODEL_AUTHORED_NOT_SOURCE_EQUIVALENT":raise SceneEnrichmentError("MODEL_PROVENANCE_INVALID:"+str(c["candidate_id"]))
 if c["introduced_unit_id"]!=UNIT_ID:raise SceneEnrichmentError("INTRODUCED_UNIT_INVALID:"+str(c["candidate_id"]))
 core=r1.semantic_scene_core(setting=str(c["medium_setting"]),participants=c["participants"],objects=c["objects"],descriptors=c.get("descriptors") or [],actions=c["actions"],relations=c["relations"],information_structure=c["information_structure"],communicative_functions=c["communicative_function_ids"])
 reasons=r1.genuine_scene_reason_codes(core)
 if reasons:raise SceneEnrichmentError("MODEL_SCENE_GATE_FAIL:"+str(c["candidate_id"])+":"+",".join(reasons))
 tax=r1.scene_taxonomy(core)
 if tax["large_situation_family"]!=c["large_situation_family"]:raise SceneEnrichmentError("MODEL_SCENE_FAMILY_MISMATCH:"+str(c["candidate_id"]))
 refs=resolve_anchor_refs(set(core["objects"]),anchors)
 return {"scene_origin":"MODEL_AUTHORED_SCENE_ENRICHMENT","scene_ref_id":str(c["candidate_id"]),"introduced_unit_id":UNIT_ID,"semantic_scene_signature_v2":r1.digest(core),"semantic_scene_core":core,"scene_taxonomy":tax,"situation_family":tax["large_situation_family"],"small_micro_scene_event":str(c["small_micro_scene_event"]),"communicative_goal":str(c["communicative_goal"]),"lineage_mode":"MODEL_AUTHORED_FROM_APPROVED_SEEDS","source_authority":"PROJECT_MODEL_AUTHORED_SCENE_ENRICHMENT","provenance":{"resolved_seed_scene_ref_ids":refs,"source_claim":str(c["source_claim"]),"source_equivalence_claimed":False},"rotation_class":"ROTATION_READY","rotation_reason_codes":[],"counts_toward_scene_rotation":True}
def unique_combined(existing:Sequence[Mapping[str,Any]],model:Sequence[Mapping[str,Any]])->list[dict[str,Any]]:
 seen={};
 for row in list(existing)+list(model):
  sig=str(row["semantic_scene_signature_v2"])
  if sig in seen:raise SceneEnrichmentError(f"SEMANTIC_SCENE_DUPLICATE:{sig}:{seen[sig]}:{row.get('scene_ref_id')}")
  seen[sig]=str(row.get("scene_ref_id"));seen_row={"semantic_scene_signature_v2":sig,"scene_ref_id":str(row.get("scene_ref_id")),"situation_family":str(row.get("situation_family")),"setting":str(row.get("semantic_scene_core",{}).get("setting")),"micro_scene_event_id":str((row.get("scene_taxonomy") or {}).get("small_micro_scene_event_id")),"scene_origin":str(row.get("scene_origin"))};yield seen_row

def build_pool(r1_inventory:Mapping[str,Any],spec:Mapping[str,Any])->dict[str,Any]:
 rows=inventory_rows(r1_inventory);existing=[x for x in rows if x.get("counts_toward_scene_rotation") is True];anchors=eligible_anchor_rows(rows);cs=candidates(spec);ids=[str(x["candidate_id"]) for x in cs]
 if len(ids)!=len(set(ids)):raise SceneEnrichmentError("DUPLICATE_CANDIDATE_ID")
 model=[model_scene_row(x,anchors) for x in cs];combined=list(unique_combined(existing,model));families=Counter(x["situation_family"] for x in combined);total=len(combined);family_count=len([k for k,v in families.items() if v and k!="UNCLASSIFIED_OBJECT"]);target=TARGET_MIN<=total<=TARGET_MAX;rotation=total>=r1.HARD_MIN_DISTINCT_MICRO_SCENES and family_count>=r1.MIN_POOL_SITUATION_FAMILIES
 if not target:raise SceneEnrichmentError(f"TARGET_SCENE_RANGE_FAIL:{total}")
 out={"schema_version":SCHEMA_VERSION,"program_id":PROGRAM_ID,"task_id":TASK_ID,"status":PASS_STATUS,"unit_id":UNIT_ID,"scope":{"unit01_only":True,"question_bank_modified":False,"parallel_question_bank_created":False,"scoring_modified":False,"learner_state_modified":False,"unit02_to_unit24_modified":False,"a2_unlocked":False},"scene_growth_policy":deepcopy(r1.SCENE_GROWTH_POLICY),"source_counts":{"r1_scene_row_count":len(rows),"existing_rotation_ready_scene_count":len(existing),"eligible_anchor_row_count":len(anchors),"model_authored_supplement_count":len(model)},"model_authored_scenes":model,"cumulative_unique_scenes":combined,"situation_family_counts":dict(sorted(families.items())),"rotation_capacity":{"genuine_distinct_micro_scene_count":total,"target_range":[TARGET_MIN,TARGET_MAX],"target_range_pass":target,"hard_min_24_pass":total>=24,"situation_family_count":family_count,"situation_family_min_5_pass":family_count>=5,"maximum_scene_slots_at_two_uses_each":total*2,"required_scene_slots":48,"twelve_form_rotation_ready":rotation},"boundaries":{"source_equivalence_claimed":False,"question_items_mutated":False,"scoring_mutated":False,"learner_state_mutated":False,"mastery_claimed":False},"next_short_step":NEXT_SHORT_STEP};out["pool_sha256"]=r1.digest(out);return out
def main(argv:Sequence[str]|None=None)->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--r1-inventory",type=Path,required=True);p.add_argument("--supplement-spec",type=Path,default=DEFAULT_SPEC);p.add_argument("--output",type=Path,default=DEFAULT_OUTPUT);a=p.parse_args(argv)
 try:o=build_pool(read_json(a.r1_inventory),read_json(a.supplement_spec));write_json(a.output,o)
 except (SceneEnrichmentError,KeyError,TypeError,ValueError,OSError) as e:print("STATUS=FAIL_A1FS_V1_U01QB07_UNIT01_MICRO_SCENE_SEED_ENRICHMENT");print(f"ERROR={e}");return 1
 c=o["rotation_capacity"];print(f"STATUS={PASS_STATUS}");print(f"EXISTING_SCENES={o['source_counts']['existing_rotation_ready_scene_count']}");print(f"MODEL_AUTHORED_SCENES={o['source_counts']['model_authored_supplement_count']}");print(f"CUMULATIVE_DISTINCT_SCENES={c['genuine_distinct_micro_scene_count']}");print(f"SITUATION_FAMILIES={c['situation_family_count']}");print(f"TWELVE_FORM_ROTATION_READY={c['twelve_form_rotation_ready']}");print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}");return 0
if __name__=="__main__":raise SystemExit(main())
