#!/usr/bin/env python3
"""Read-only Unit01 semantic micro-scene inventory and rotation-capacity audit."""
from __future__ import annotations
import argparse, hashlib, json, re
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

A1FS_CONTENT_POLICY_MODE="NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION="Read-only Unit01 semantic scene identity, taxonomy, and rotation audit; no learner content or authority mutation."
PROGRAM_ID="A1FS-V1"
TASK_ID="A1FS-V1-U01QB06R1_Unit01SemanticSceneIdentityAndGenuineLifeSceneGateFullFix"
SCHEMA_VERSION="a1fs.v1.u01qb06.unit01_micro_scene_pool_inventory.v2"
SEMANTIC_SCENE_SIGNATURE_VERSION=3
PASS_STATUS="PASS_A1FS_V1_U01QB06R1_UNIT01_SEMANTIC_SCENE_IDENTITY_AND_GENUINE_LIFE_SCENE_GATE_FULLFIX"
UNIT_ID="GRAMMAR_ARTICLES_BASIC"
DEFAULT_OUTPUT=Path("ulga/reports/a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory.json")
NEXT_SHORT_STEP="A1FS-V1-U01QB07_Unit01MicroSceneSeedEnrichmentAndRotationCapacityExpansion"
FORM_COUNT=12; SCENES_PER_FORM=4; TOTAL_SCENE_SLOTS=48; MAX_EXPOSURES_PER_EXACT_SCENE=2
HARD_MIN_DISTINCT_MICRO_SCENES=24; TARGET_DISTINCT_MICRO_SCENES_MIN=28; TARGET_DISTINCT_MICRO_SCENES_MAX=36
MIN_POOL_SITUATION_FAMILIES=5; MIN_FORM_SITUATION_FAMILIES=3; MAX_FORM_SCENES_FROM_SAME_FAMILY=2
MIN_FORM_GAP_BEFORE_EXACT_SCENE_REUSE=3; REUSED_SCENE_MIN_CHANGED_DIMENSIONS=2
GENERIC_ACTIONS={"","A1_IMITATION","PROJECT_CONTRACT_COMPLETION","SEMANTIC_EQUIVALENT","HUMAN_EXCEPTION","IDENTIFY","DESCRIBE","CANONICAL_CONTEXT_USE"}
GENERIC_SETTINGS={"","UNIT01_OBJECT_SCENE","GENERAL","OBJECT_SCENE","UNSPECIFIED"}
RELATION_RE=re.compile(r"\b(in|on|near)\b",re.I); WORD_RE=re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
ARTICLE_TOKENS={"A","AN","THE"}
NP_BOUNDARIES=set("AND OR BUT IS ARE WAS WERE IN ON NEAR AT FOR WITH TO FROM OF HAS HAVE HAD PUT PUTS EAT EATS SEE SEES LOOK LOOKS FIND FINDS GET GETS TAKE TAKES GIVE GIVES".split())
DESCRIPTOR_WORDS=set("BIG BLUE BROWN GREEN NEW OLD ORANGE RED SMALL WHITE YELLOW".split())
ACTION_LEMMA_MAP={"HAS":"HAVE","HAVE":"HAVE","HAD":"HAVE","PUT":"PUT","PUTS":"PUT","EAT":"EAT","EATS":"EAT","SEE":"SEE","SEES":"SEE","LOOK":"LOOK","LOOKS":"LOOK","FIND":"FIND","FINDS":"FIND","GET":"GET","GETS":"GET","TAKE":"TAKE","TAKES":"TAKE","GIVE":"GIVE","GIVES":"GIVE","PLAY":"PLAY","PLAYS":"PLAY","OPEN":"OPEN","OPENS":"OPEN","CLOSE":"CLOSE","CLOSES":"CLOSE","BUY":"BUY","BUYS":"BUY","CHOOSE":"CHOOSE","CHOOSES":"CHOOSE"}
FAMILY_MAP={
 "CLASSROOM":"SCHOOL","SCHOOL":"SCHOOL","SCHOOL_LIBRARY":"SCHOOL","SCHOOL_ENTRANCE":"SCHOOL","SCHOOL_BAG_AREA":"SCHOOL",
 "HOME":"HOME","ROOM":"HOME","BEDROOM":"HOME","KITCHEN":"HOME","LIVING_ROOM":"HOME","DINING_ROOM":"HOME",
 "PARK":"OUTDOORS","PLAYGROUND":"OUTDOORS","GARDEN":"OUTDOORS","PICNIC_AREA":"OUTDOORS",
 "PARK_AND_BIRTHDAY":"OUTDOORS_SOCIAL","FOOD_AND_PICNIC":"FOOD_SOCIAL","PICNIC":"FOOD_SOCIAL","SNACK_TIME":"FOOD_SOCIAL","LUNCH":"FOOD_SOCIAL","BIRTHDAY_TABLE":"FOOD_SOCIAL",
 "SHOP":"SHOPPING","SHOPPING":"SHOPPING","TOY_SHOP":"SHOPPING","BOOKSHOP":"SHOPPING","FOOD_SHOP":"SHOPPING","MARKET":"SHOPPING"}
SCENE_GROWTH_POLICY={"authority_scope":"CUMULATIVE_CROSS_UNIT_LIFE_WORLD","unit01_initializes_scene_pool":True,"later_units_may_add_new_scenes":True,"prior_unit_scenes_remain_reusable":True,"later_units_may_reproject_prior_scenes_with_new_language_targets":True,"scene_identity_includes_unit_target":False,"scene_identity_includes_theme":False,"scene_identity_includes_source_or_pedagogic_role":False}
MODEL_ENRICHMENT_POLICY={"allowed_candidate_class":"MODEL_AUTHORED_FROM_APPROVED_SEEDS","approved_seed_lineage_required":True,"model_may_complete":["SETTING","PARTICIPANT_ROLE","ACTION_OR_EVENT","RELATION","COMMUNICATIVE_GOAL"],"model_must_not_claim_source_equivalence":True,"semantic_dedup_required":True,"genuine_life_scene_gate_required":True,"validator_required_before_rotation_admission":True}
class InventoryBuildError(ValueError): pass

def canonical(v:Any)->str:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def digest(v:Any)->str:return hashlib.sha256(canonical(v).encode()).hexdigest()
def file_sha256(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def read_json(p:Path)->Any:
 try:return json.loads(p.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError) as e:raise InventoryBuildError(f"UNREADABLE_JSON:{p}:{e}") from e
def write_json(p:Path,v:Mapping[str,Any])->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(dict(v),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def norm_token(v:Any)->str:return re.sub(r"[^A-Z0-9]+","_",str(v or "").strip().upper()).strip("_")
def norm_strings(v:Iterable[Any]|None)->list[str]:return sorted({norm_token(x) for x in (v or []) if norm_token(x)})
def approved_assets(v:Mapping[str,Any])->list[dict[str,Any]]:
 p=v.get("payload") if isinstance(v.get("payload"),Mapping) else v; rows=p.get("content_assets") if isinstance(p,Mapping) else None
 if not isinstance(rows,list) or not rows or not all(isinstance(x,Mapping) for x in rows):raise InventoryBuildError("CONTENT_ASSETS_REQUIRED")
 return [deepcopy(dict(x)) for x in rows]
def canonical_context_rows(v:Any)->list[dict[str,Any]]:
 rows=v if isinstance(v,list) else (v.get("contexts") if isinstance(v,Mapping) else None)
 if rows is None and isinstance(v,Mapping):rows=(v.get("tables") or {}).get("contexts") or (v.get("payload") or {}).get("contexts")
 if not isinstance(rows,list) or not all(isinstance(x,Mapping) for x in rows):raise InventoryBuildError("CANONICAL_CONTEXT_ARRAY_MISSING")
 return [deepcopy(dict(x)) for x in rows]
def content_text(a:Mapping[str,Any])->str:
 c=a.get("content") or {}; parts=[str(x) for x in c.get("sentences") or [] if str(x).strip()] if isinstance(c,Mapping) else []
 if isinstance(c,Mapping):parts += [str(t["utterance"]) for t in c.get("dialogue_turns") or [] if isinstance(t,Mapping) and str(t.get("utterance") or "").strip()]
 return " ".join(parts)
def scene_relations_from_text(t:str)->list[str]:return sorted({m.group(1).upper() for m in RELATION_RE.finditer(str(t or ""))})
def situation_family(setting:str)->str:return FAMILY_MAP.get(norm_token(setting),"UNCLASSIFIED_OBJECT")
def extract_context_semantics(sentences:Sequence[Any])->dict[str,list[str]]:
 objects:set[str]=set(); descriptors:set[str]=set(); actions:set[str]=set(); relations:set[str]=set()
 for raw in sentences:
  text=str(raw or ""); relations.update(scene_relations_from_text(text)); tokens=[x.upper() for x in WORD_RE.findall(text)]
  actions.update(ACTION_LEMMA_MAP[x] for x in tokens if x in ACTION_LEMMA_MAP); i=0
  while i<len(tokens):
   if tokens[i] not in ARTICLE_TOKENS:i+=1;continue
   p=[];j=i+1
   while j<len(tokens) and len(p)<3 and tokens[j] not in ARTICLE_TOKENS|NP_BOUNDARIES:p.append(tokens[j]);j+=1
   while len(p)>1 and p[0] in DESCRIPTOR_WORDS:descriptors.add(p.pop(0))
   if p:objects.add("_".join(p))
   i=max(i+1,j)
 return {"objects":sorted(objects),"descriptors":sorted(descriptors),"actions":sorted(actions),"relations":sorted(relations)}
def semantic_scene_core(*,setting:str,participants:Iterable[Any],objects:Iterable[Any],descriptors:Iterable[Any],actions:Iterable[Any],information_structure:Iterable[Any],communicative_functions:Iterable[Any],relations:Iterable[Any]=())->dict[str,Any]:
 return {"setting":norm_token(setting) or "UNSPECIFIED","participants":norm_strings(participants),"objects":norm_strings(objects),"descriptors":norm_strings(descriptors),"actions":norm_strings(actions),"relations":norm_strings(relations),"information_structure":norm_strings(information_structure),"communicative_function_ids":norm_strings(communicative_functions)}
def concrete_scene_objects(c:Mapping[str,Any])->set[str]:
 setting=norm_token(c.get("setting")); parts=set(setting.split("_")); return {x for x in norm_strings(c.get("objects") or []) if x!=setting and x not in parts}
def genuine_scene_reason_codes(c:Mapping[str,Any])->list[str]:
 r=[]; setting=norm_token(c.get("setting")) or "UNSPECIFIED"; objs=concrete_scene_objects(c); acts=set(norm_strings(c.get("actions") or [])); rel=set(norm_strings(c.get("relations") or []))
 if setting in GENERIC_SETTINGS:r.append("GENERIC_OR_UNSPECIFIED_SETTING")
 if not objs:r.append("NO_CONCRETE_SCENE_OBJECT")
 if not (acts-GENERIC_ACTIONS or rel or len(objs)>=2):r.append("OBJECT_ONLY_OR_UNDER_SPECIFIED_EVENT")
 if not norm_strings(c.get("communicative_function_ids") or []):r.append("NO_COMMUNICATIVE_FUNCTION")
 return r
def micro_scene_event_id(c:Mapping[str,Any])->str:
 e={k:norm_strings(c.get(k) or []) for k in ("participants","objects","descriptors","actions","relations")};return "MS-EVT-"+digest(e)[:12].upper()
def scene_taxonomy(c:Mapping[str,Any])->dict[str,str]:
 s=norm_token(c.get("setting")) or "UNSPECIFIED";return {"large_situation_family":situation_family(s),"medium_setting":s,"small_micro_scene_event_id":micro_scene_event_id(c)}
def rotation_class_for_asset(a:Mapping[str,Any],c:Mapping[str,Any])->tuple[str,list[str]]:
 lin=a.get("source_lineage") or {}; mode=str(lin.get("lineage_mode") or "") if isinstance(lin,Mapping) else ""; adm=a.get("admission") or {}
 if mode=="PROJECT_AUTHORED_CONTRACT_COMPLETION":return "COVERAGE_COMPLETION_NOT_SCENE",["PROJECT_AUTHORED_GAP_COMPLETION"]
 if isinstance(adm,Mapping) and adm.get("template_only"):return "TEMPLATE_ONLY_NOT_SCENE",["TEMPLATE_ONLY"]
 r=genuine_scene_reason_codes(c);return ("SCENE_SEED_NEEDS_ENRICHMENT",r) if r else ("ROTATION_READY",[])
def asset_scene_row(a:Mapping[str,Any])->dict[str,Any]:
 s=a.get("scene_profile") or {}; al=a.get("target_alignment") or {}; lin=a.get("source_lineage") or {}
 if not isinstance(s,Mapping):raise InventoryBuildError(f"SCENE_PROFILE_REQUIRED:{a.get('content_asset_id')}")
 if not isinstance(al,Mapping):al={}
 c=semantic_scene_core(setting=str(s.get("setting") or al.get("situation_family_id") or ""),participants=s.get("participants") or [],objects=s.get("objects") or al.get("active_nouns") or [],descriptors=s.get("descriptors") or al.get("active_adjectives") or [],actions=s.get("actions") or [],relations=scene_relations_from_text(content_text(a)),information_structure=s.get("information_structure") or [],communicative_functions=s.get("communicative_function_ids") or al.get("communicative_function_ids") or [])
 klass,reasons=rotation_class_for_asset(a,c);tax=scene_taxonomy(c);mode=str(lin.get("lineage_mode") or "") if isinstance(lin,Mapping) else ""
 return {"scene_origin":"REAL62_CONTENT_ASSET","scene_ref_id":str(a.get("content_asset_id") or ""),"legacy_micro_situation_id":str(al.get("micro_situation_id") or ""),"legacy_semantic_scene_id":str(s.get("semantic_scene_id") or ""),"legacy_distinct_scene_signature":str(s.get("distinct_scene_signature") or ""),"semantic_scene_signature_v2":digest(c),"semantic_scene_core":c,"scene_taxonomy":tax,"situation_family":tax["large_situation_family"],"theme_id":str(al.get("theme_id") or ""),"content_kind":str(a.get("content_kind") or ""),"lineage_mode":mode,"source_authority":str(lin.get("source_authority") or "") if isinstance(lin,Mapping) else "","rotation_class":klass,"rotation_reason_codes":reasons,"counts_toward_scene_rotation":klass=="ROTATION_READY"}
def canonical_context_scene_row(row:Mapping[str,Any])->dict[str,Any]:
 cid=str(row.get("context_id") or "").strip(); setting=norm_token(row.get("setting"))
 if not cid or not setting:raise InventoryBuildError("CANONICAL_CONTEXT_ID_AND_SETTING_REQUIRED")
 x=row.get("scene_semantics") if isinstance(row.get("scene_semantics"),Mapping) else extract_context_semantics(row.get("sentences") or [])
 c=semantic_scene_core(setting=setting,participants=["LEARNER"],objects=x.get("objects") or [],descriptors=x.get("descriptors") or [],actions=x.get("actions") or [],relations=x.get("relations") or [],information_structure=["FIRST_MENTION","KNOWN_REFERENCE"],communicative_functions=["IDENTIFY","DESCRIBE"])
 reasons=genuine_scene_reason_codes(c); klass="ROTATION_READY" if not reasons else "CANONICAL_CONTEXT_NEEDS_ENRICHMENT";tax=scene_taxonomy(c)
 return {"scene_origin":"CANONICAL_UNIT01_CONTEXT","scene_ref_id":cid,"legacy_micro_situation_id":cid,"legacy_semantic_scene_id":"","legacy_distinct_scene_signature":"","semantic_scene_signature_v2":digest(c),"semantic_scene_core":c,"scene_taxonomy":tax,"situation_family":tax["large_situation_family"],"theme_id":str(row.get("theme_id") or ""),"content_kind":"CANONICAL_CONTEXT","lineage_mode":"EXISTING_UNIT01_CONTEXT_AUTHORITY","source_authority":str(row.get("source_role") or ""),"rotation_class":klass,"rotation_reason_codes":reasons,"counts_toward_scene_rotation":klass=="ROTATION_READY"}
def duplicate_groups(rows:Sequence[Mapping[str,Any]])->list[dict[str,Any]]:
 g=defaultdict(list)
 for r in rows:g[str(r["semantic_scene_signature_v2"])].append(r)
 return [{"semantic_scene_signature_v2":s,"member_count":len(m),"scene_ref_ids":sorted(str(x["scene_ref_id"]) for x in m),"rotation_ready_member_count":sum(bool(x["counts_toward_scene_rotation"]) for x in m)} for s,m in sorted(g.items()) if len(m)>1]
def unique_rotation_scenes(rows:Sequence[Mapping[str,Any]])->list[dict[str,Any]]:
 g=defaultdict(list)
 for r in rows:
  if r["counts_toward_scene_rotation"]:g[str(r["semantic_scene_signature_v2"])].append(r)
 out=[]
 for s,m in sorted(g.items()):
  r=m[0];t=r["scene_taxonomy"];out.append({"semantic_scene_signature_v2":s,"representative_scene_ref_id":str(r["scene_ref_id"]),"member_scene_ref_ids":sorted(str(x["scene_ref_id"]) for x in m),"situation_family":str(r["situation_family"]),"setting":str(r["semantic_scene_core"]["setting"]),"micro_scene_event_id":str(t["small_micro_scene_event_id"]),"origin_set":sorted({str(x["scene_origin"]) for x in m})})
 return out
def build_inventory(approved_content:Mapping[str,Any],canonical_context_input:Any,*,approved_content_sha256:str="",canonical_context_sha256:str="")->dict[str,Any]:
 assets=approved_assets(approved_content);contexts=canonical_context_rows(canonical_context_input);rows=[asset_scene_row(a) for a in assets]+[canonical_context_scene_row(c) for c in contexts];unique=unique_rotation_scenes(rows);families=Counter(r["situation_family"] for r in unique);classes=Counter(r["rotation_class"] for r in rows);modes=Counter(r["lineage_mode"] for r in rows if r["scene_origin"]=="REAL62_CONTENT_ASSET")
 source_count=sum(r["scene_origin"]=="REAL62_CONTENT_ASSET" and r["lineage_mode"]!="PROJECT_AUTHORED_CONTRACT_COMPLETION" for r in rows);project_count=sum(r["scene_origin"]=="REAL62_CONTENT_ASSET" and r["lineage_mode"]=="PROJECT_AUTHORED_CONTRACT_COMPLETION" for r in rows);distinct=len(unique);family_count=len([k for k,v in families.items() if v and k!="UNCLASSIFIED_OBJECT"]);hard=distinct>=24;family=family_count>=5;ready=hard and family
 inv={"schema_version":SCHEMA_VERSION,"program_id":PROGRAM_ID,"task_id":TASK_ID,"status":PASS_STATUS,"unit_id":UNIT_ID,"scope":{"unit01_only":True,"question_bank_modified":False,"parallel_question_bank_created":False,"parallel_scoring_created":False,"unit02_to_unit24_modified":False,"a2_unlocked":False},"source_identity":{"approved_content_sha256":approved_content_sha256,"canonical_context_sha256":canonical_context_sha256},"inventory_policy":{"semantic_scene_signature_version":SEMANTIC_SCENE_SIGNATURE_VERSION,"source_identity_in_semantic_signature":False,"source_or_pedagogic_role_in_semantic_signature":False,"theme_in_semantic_signature":False,"project_authored_gap_completion_counts_as_genuine_scene":False,"under_specified_object_only_asset_counts_as_genuine_scene":False,"setting_only_identification_counts_as_genuine_scene":False,"canonical_context_semantics_extracted_from_context_text":True,"canonical_unit01_context_counts_only_if_genuine_scene_gate_passes":True},"scene_taxonomy_policy":{"large_class":"SITUATION_FAMILY","medium_class":"SETTING","small_class":"MICRO_SCENE_EVENT","theme_is_separate_from_situation_family":True,"situation_family_derived_from_setting_only":True},"scene_growth_policy":deepcopy(SCENE_GROWTH_POLICY),"model_enrichment_policy":deepcopy(MODEL_ENRICHMENT_POLICY),"rotation_policy":{"form_count":12,"scenes_per_form":4,"total_scene_slots":48,"max_exposures_per_exact_micro_scene":2,"hard_min_distinct_micro_scenes":24,"target_distinct_micro_scenes":[28,36],"min_pool_situation_families":5,"min_form_situation_families":3,"max_form_scenes_from_same_family":2,"min_form_gap_before_exact_scene_reuse":3,"reused_scene_min_changed_dimensions":2,"same_scene_same_skill_same_task_angle_repeat_allowed":False},"raw_counts":{"approved_content_asset_count":len(assets),"source_derived_asset_count":source_count,"project_authored_completion_asset_count":project_count,"canonical_context_count":len(contexts),"inventory_row_count":len(rows)},"classification_counts":dict(sorted(classes.items())),"lineage_mode_counts":dict(sorted(modes.items())),"situation_family_counts":dict(sorted(families.items())),"semantic_duplicate_groups":duplicate_groups(rows),"unique_rotation_scenes":unique,"scene_rows":rows,"rotation_readiness":{"genuine_distinct_micro_scene_count":distinct,"non_unclassified_situation_family_count":family_count,"maximum_scene_slots_at_two_uses_each":distinct*2,"required_scene_slots":48,"hard_distinct_scene_capacity_pass":hard,"situation_family_capacity_pass":family,"twelve_form_rotation_ready":ready,"scene_shortfall_to_hard_min":max(0,24-distinct),"scene_shortfall_to_target_min":max(0,28-distinct),"family_shortfall":max(0,5-family_count),"release_classification":"READY_FOR_12_FORM_ROTATION" if ready else "NOT_READY_SCENE_POOL_SUPPLEMENTATION_REQUIRED"},"boundaries":{"content_assets_mutated":False,"canonical_contexts_mutated":False,"question_items_mutated":False,"learner_state_mutated":False,"scoring_mutated":False,"mastery_claimed":False},"next_short_step":NEXT_SHORT_STEP};inv["inventory_sha256"]=digest(inv);return inv
def main(argv:Sequence[str]|None=None)->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--approved-content",type=Path,required=True);p.add_argument("--canonical-contexts",type=Path,required=True);p.add_argument("--output",type=Path,default=DEFAULT_OUTPUT);a=p.parse_args(argv)
 try:inv=build_inventory(read_json(a.approved_content),read_json(a.canonical_contexts),approved_content_sha256=file_sha256(a.approved_content),canonical_context_sha256=file_sha256(a.canonical_contexts));write_json(a.output,inv)
 except (InventoryBuildError,KeyError,TypeError,ValueError,OSError) as e:print("STATUS=FAIL_A1FS_V1_U01QB06R1_UNIT01_SEMANTIC_SCENE_IDENTITY_AND_GENUINE_LIFE_SCENE_GATE_FULLFIX");print(f"ERROR={e}");return 1
 r=inv["rotation_readiness"];print(f"STATUS={PASS_STATUS}");print(f"APPROVED_CONTENT_ASSETS={inv['raw_counts']['approved_content_asset_count']}");print(f"CANONICAL_CONTEXTS={inv['raw_counts']['canonical_context_count']}");print(f"GENUINE_DISTINCT_MICRO_SCENES={r['genuine_distinct_micro_scene_count']}");print(f"SITUATION_FAMILIES={r['non_unclassified_situation_family_count']}");print(f"TWELVE_FORM_ROTATION_READY={r['twelve_form_rotation_ready']}");print(f"SCENE_SHORTFALL_TO_24={r['scene_shortfall_to_hard_min']}");print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}");return 0
if __name__=="__main__":raise SystemExit(main())
