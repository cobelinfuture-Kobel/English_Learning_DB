"""Read-only Unit03 Q1-Q10 final-package reconciliation over current authority."""
from __future__ import annotations
import csv, hashlib, json
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence
from product.a1fs_v1_2_1 import u03q9q10r1r1_unit03_successor_twenty_form_learner_facing_acceptance as learner
from ulga.builders import build_a1fs_v1_u03q02q04r1_vocabulary_chunk_provenance_recheck as q24
from ulga.builders import build_a1fs_v1_u03q05r1_unit03_exact_lesson_sentence_pattern_binding_crosscheck as q5
from ulga.builders import build_a1fs_v1_u03q9q10r1_unit03_form_pedagogical_contract_20x40_6_10_10_8_6 as successor

A1FS_CONTENT_POLICY_MODE="NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION=("Read-only Unit03 Q1-Q10 final-package reconciliation/export. It binds current "
 "Q2/Q4/Q5/Q9/Q10 GitHub authorities, preserves Q1/Q3/Q6/Q7/Q8 handoff provenance, "
 "and creates no content, authority, selector, runtime, renderer, state, scoring, PDF, Q11, Unit04, or A2.")
PROGRAM_ID="A1FS-V1"; UNIT_ID="GRAMMAR_SUBJECT_PRONOUNS"
TASK_ID="A1FS-V1-U03FP01_Unit03Q1Q10FinalPackageSuccessorReconciliation"
PASS_STATUS="PASS_A1FS_V1_U03FP01_UNIT03_Q1_Q10_FINAL_PACKAGE_SUCCESSOR_RECONCILIATION"
NEXT_SHORT_STEP="A1FS-V1-U03FP02_Unit03FinalWorkingPackageCurrentAuthorityMaterialization"
SCHEMA_VERSION="a1fs.v1.u03fp01.q1_q10_final_package_successor_reconciliation.v1"
Q1_SHA="17caac2569739a52a64db40dc0fc28e383d1489ffdffb114de0391ca308c52dd"
Q3_SHA="bb4e5f2d4251af2c4765780a40ce0048ec637cbd0f3a84c5dbce187e78770b17"
Q6_SHA="117779b952e567a636fd98b6296655f014bc43b8f0f79a3f6415b2b72580c923"
Q8_FUNCTIONS=["IDENTIFY","DESCRIBE","QUANTITY_PLURALITY","REFERENCE_TRACKING"]
Q09_JSON="Unit03_Q09_Task_Angle_Question_Type.json"; Q09_CSV="Unit03_Q09_Task_Families.csv"
Q10I_JSON="Unit03_Q10_Successor_QuestionBank_Inventory.json"; Q10I_CSV="Unit03_Q10_Successor_QuestionBank_Inventory.csv"
Q10R_JSON="Unit03_Q10_Successor_Runtime_Form_Plan.json"; Q10R_CSV="Unit03_Q10_Successor_Runtime_Form_Plan.csv"
MANIFEST="Unit03_Q01_Q10_Current_Manifest.json"
EXPORT_FILENAMES=(Q09_JSON,Q09_CSV,Q10I_JSON,Q10I_CSV,Q10R_JSON,Q10R_CSV,MANIFEST)

class U03FP01Error(ValueError): pass

def _digest(v:Any)->str:
 return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def _cell(v:Any)->str:
 if v is None:return ""
 return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")) if isinstance(v,(dict,list,tuple)) else str(v)

@lru_cache(maxsize=1)
def _sources():
 r24=q24.build_report(); q24.validate(r24)
 r5=q5.build_report(); q5.validate(r5)
 s=successor.build_export_payload()
 l=learner.build_acceptance_report()
 if s.get("status")!=successor.PASS_STATUS or l.get("validation_status")!=learner.PASS_STATUS: raise U03FP01Error("CURRENT_SOURCE_STATUS_INVALID")
 return r24,r5,s,l

def _q9_export(s:Mapping[str,Any])->dict[str,Any]:
 a=dict(s["q9_amendment"]); items=list(s["successor_questionbank_items"]); runtime=list(s["runtime_bindings"])
 types:dict[str,set[str]]=defaultdict(set); counts=Counter(str(x["task_family"]) for x in runtime)
 for x in items: types[str(x["task_family"])].add(str(x["question_type"]))
 families=[{"task_family":f,"form_sections":list(a["section_mapping"][f]),"current_question_types":sorted(types[f]),"runtime_occurrence_count":counts[f]} for f in successor.Q9_FAMILIES]
 return {"schema_version":"a1fs.unit03.final_package.q9.successor.v2","program_id":PROGRAM_ID,"unit_id":UNIT_ID,"q":"Q09","status":"CURRENT_SUCCESSOR_TASK_FAMILY_AND_SECTION_CONTRACT","source_task_id":successor.TASK_ID,"task_family_count":a["task_family_count"],"task_families":families,"family_11_created":a["family_11_created"],"section_mapping":a["section_mapping"],"connected_passage_question_types":a["connected_passage_question_types"],"runtime_materialized":True,"runtime_occurrence_count":len(runtime)}

def build_export_payload()->dict[str,Any]:
 r24,r5,s,l=_sources(); q2=r24["q2"]; q4=r24["q4"]; f=r5["q5_pattern_family_coverage"]; fr=r5["q5_exact_frame_coverage"]; rule=r5["subject_pronoun_rule_primitive"]
 q6=s["q6_preservation"]; b=s["claim_boundaries"]; c=s["q10_successor_form_contract"]; items=list(s["successor_questionbank_items"]); runtime=list(s["runtime_bindings"]); q9=_q9_export(s)
 qmap={
 "Q01":{"status":"CURRENT_RULE_VERIFIED_HANDOFF_NOT_PROMOTED","handoff_sha256":Q1_SHA,"pronoun_count":7,"egp_row_id":"1741163713868x463659211645272000","current_rule_id":rule["rule_id"],"current_rule_verified":rule["verified"],"canonical_promotion_claimed":False},
 "Q02":{"status":"CURRENT_GITHUB_MODULE_BOUND","source_task_id":q24.TASK_ID,"support_pool_count":q2["support_pool_count"],"unit03_definitely_new_vocabulary_claimed":q2["unit03_definitely_new_vocabulary_claimed"]},
 "Q03":{"status":"PROVENANCE_PRESERVED_CURRENT_DELIVERY_VERIFIED","handoff_sha256":Q3_SHA,"closed_subject_pronoun_form_count":7,"generated_inflection_count":0},
 "Q04":{"status":"CURRENT_GITHUB_MODULE_BOUND","source_task_id":q24.TASK_ID,"cumulative_distinct_surface_rows":q4["cumulative_distinct_surface_rows"],"unit03_new_admitted_surface_rows":q4["unit03_new_admitted_surface_rows"]},
 "Q05":{"status":"CURRENT_GITHUB_MODULE_BOUND","source_task_id":q5.TASK_ID,"current_pattern_family_count":f["cumulative_pattern_family_count"],"unit03_new_canonical_pattern_family_count":f["unit03_new_canonical_pattern_family_count"],"current_exact_frame_count":fr["cumulative_exact_frame_count"],"unit03_new_exact_frame_count":fr["unit03_new_exact_frame_count"],"old_eight_family_working_handoff_current":False},
 "Q06":{"status":"PROVENANCE_PRESERVED_BY_SUCCESSOR_NO_REGENERATION","handoff_json_sha256":Q6_SHA,"previous_cumulative":7531,"unit03_new_admitted":18983,"direct_admitted":16834,"context_bound_admitted":2149,"unit03_cumulative":26514,"successor_sentence_assets_created":q6["successor_sentence_assets_created"],"q6_regenerated":q6["q6_regenerated"],"q6_mutated":q6["q6_mutated"]},
 "Q07":{"status":"PROVENANCE_PRESERVED_DOWNSTREAM_MUTATION_FORBIDDEN","pronoun_scene_covered":7,"pronoun_scene_gap":0,"unit01_canonical_scene_worlds":32,"unit01_bindable_scenes":31,"unit01_scene_pronoun_projection_pairs":34,"unit02_structural_scene_candidates":109,"structural_pronoun_projection_rows":540,"unit03_new_canonical_scenes":0,"current_successor_q7_mutated":b["q7_mutated"]},
 "Q08":{"status":"PROVENANCE_PRESERVED_DOWNSTREAM_MUTATION_FORBIDDEN","functions":Q8_FUNCTIONS,"cumulative_function_count":4,"missing_function_count":0,"current_successor_q8_mutated":b["q8_mutated"]},
 "Q09":{"status":"CURRENT_SUCCESSOR_GITHUB_MODULE_BOUND","source_task_id":successor.TASK_ID,"task_family_count":q9["task_family_count"],"family_11_created":q9["family_11_created"],"connected_passage_question_type_count":len(q9["connected_passage_question_types"]),"runtime_occurrence_count":len(runtime)},
 "Q10":{"status":"CURRENT_SUCCESSOR_GITHUB_MODULE_BOUND","source_task_id":successor.TASK_ID,"materialization_identity":c["materialization_identity"],"form_count":c["form_count"],"activities_per_form":c["activities_per_form"],"runtime_occurrence_count":c["runtime_occurrence_count"],"candidate_count_per_slot":c["candidate_count_per_slot"],"section_counts_per_form":c["section_counts_per_form"],"selected_item_identity_count":c["selected_item_identity_count"],"global_800_distinct_selected_item_proof":c["global_800_distinct_selected_item_proof"]}}
 acc=l["acceptance"]; ped=l["pedagogical_acceptance"]
 inv={"schema_version":"a1fs.unit03.final_package.q10.successor_inventory.v1","status":"CURRENT_SUCCESSOR_QUESTIONBANK_INVENTORY","source_task_id":successor.TASK_ID,"materialization_identity":c["materialization_identity"],"item_count":len(items),"items":items}
 run={"schema_version":"a1fs.unit03.final_package.q10.successor_runtime.v1","status":"CURRENT_SUCCESSOR_RUNTIME_FORM_PLAN","source_task_id":successor.TASK_ID,"materialization_identity":c["materialization_identity"],"form_count":20,"activities_per_form":40,"runtime_occurrence_count":len(runtime),"section_counts_per_form":c["section_counts_per_form"],"runtime_occurrences":runtime}
 p={"schema_version":SCHEMA_VERSION,"program_id":PROGRAM_ID,"task_id":TASK_ID,"status":PASS_STATUS,"unit_id":UNIT_ID,"package_role":"READ_ONLY_CURRENT_AUTHORITY_RECONCILIATION_AND_HANDOFF_EXPORT","q01_q10_map":qmap,"learner_facing_current":{"task_id":learner.TASK_ID,"validation_status":l["validation_status"],"source_package_sha256":l["source_package_sha256"],"source_runtime_identity_sha256":l["source_runtime_identity_sha256"],"form_count":acc["form_count"],"activity_count":acc["activity_count"],"rendered_activity_count":acc["rendered_activity_count"],"connected_passage_question_count":ped["section_e_connected_passage_questions"],"section_b_all_forms_proven":ped["section_b_all_forms_proven"],"section_c_all_items_same_question_integrated":ped["section_c_all_items_same_question_integrated"]},"current_exports":{"q09":q9,"q10_inventory":inv,"q10_runtime":run},"historical_provenance":{"old_q10_runtime_count":640,"old_q10_current":False,"u03scfv2_runtime_count":800,"u03scfv2_current":False,"current_successor_identity":c["materialization_identity"],"current_successor_identity_is_new":True,"old_q05_eight_family_working_handoff_current":False},"export_contract":{"replacement_scope":"REPLACE_STALE_UNIT03_Q09_Q10_PACKAGE_FILES_ONLY","q01_q08_preserved":True,"q01_q08_reexported":False,"export_filenames":list(EXPORT_FILENAMES)},"claim_boundaries":{"q01_q08_reexported":False,"q01_q08_mutated":False,"q09_q10_read_only_export":True,"questionbank_or_runtime_authority_created":False,"sentence_assets_created":False,"second_selector_created":False,"second_renderer_created":False,"learner_state_mutated":False,"scoring_authority_mutated":False,"pdf_modified":False,"q11_opened":False,"unit04_opened":False,"a2_unlocked":False},"next_short_step":NEXT_SHORT_STEP}
 validate(p); p["package_sha256"]=_digest(p); return p

def validate(p:Mapping[str,Any])->None:
 q=p["q01_q10_map"]
 if list(q)!=[f"Q{i:02d}" for i in range(1,11)]: raise U03FP01Error("Q_MAP_SEQUENCE_INVALID")
 if q["Q02"]["support_pool_count"]!=40 or q["Q04"]["cumulative_distinct_surface_rows"]!=50: raise U03FP01Error("Q2_Q4_INVALID")
 if (q["Q05"]["current_pattern_family_count"],q["Q05"]["current_exact_frame_count"],q["Q05"]["old_eight_family_working_handoff_current"])!=(7,15,False): raise U03FP01Error("Q5_INVALID")
 if (q["Q06"]["unit03_new_admitted"],q["Q06"]["unit03_cumulative"],q["Q06"]["successor_sentence_assets_created"],q["Q06"]["q6_regenerated"])!=(18983,26514,0,False): raise U03FP01Error("Q6_INVALID")
 if (q["Q07"]["pronoun_scene_covered"],q["Q07"]["structural_pronoun_projection_rows"],q["Q07"]["unit03_new_canonical_scenes"],q["Q07"]["current_successor_q7_mutated"])!=(7,540,0,False): raise U03FP01Error("Q7_INVALID")
 if q["Q08"]["functions"]!=Q8_FUNCTIONS or q["Q08"]["current_successor_q8_mutated"] is not False: raise U03FP01Error("Q8_INVALID")
 if q["Q09"]["task_family_count"]!=10 or q["Q09"]["family_11_created"] is not False: raise U03FP01Error("Q9_INVALID")
 if (q["Q10"]["form_count"],q["Q10"]["activities_per_form"],q["Q10"]["runtime_occurrence_count"],q["Q10"]["section_counts_per_form"],q["Q10"]["selected_item_identity_count"])!=(20,40,800,{"A":6,"B":10,"C":10,"D":8,"E":6},800): raise U03FP01Error("Q10_INVALID")
 l=p["learner_facing_current"]
 if (l["form_count"],l["activity_count"],l["connected_passage_question_count"])!=(20,800,120): raise U03FP01Error("LEARNER_INVALID")
 for k,v in p["claim_boundaries"].items():
  if k=="q09_q10_read_only_export":
   if v is not True: raise U03FP01Error(k)
  elif v is not False: raise U03FP01Error(k)

def _write_json(path:Path,v:Any)->None: path.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def _write_csv(path:Path,rows:Sequence[Mapping[str,Any]],fields:Sequence[str])->None:
 with path.open("w",encoding="utf-8-sig",newline="") as h:
  w=csv.DictWriter(h,fieldnames=list(fields)); w.writeheader()
  for r in rows:w.writerow({f:_cell(r.get(f)) for f in fields})
def write_exports(output_dir:Path)->dict[str,Path]:
 d=Path(output_dir); d.mkdir(parents=True,exist_ok=True); p=build_export_payload(); e=p["current_exports"]; q9=e["q09"]; inv=e["q10_inventory"]; run=e["q10_runtime"]; paths={n:d/n for n in EXPORT_FILENAMES}
 _write_json(paths[Q09_JSON],q9); _write_csv(paths[Q09_CSV],q9["task_families"],("task_family","form_sections","current_question_types","runtime_occurrence_count"))
 _write_json(paths[Q10I_JSON],inv); _write_csv(paths[Q10I_CSV],inv["items"],("item_id","form_number","progression_stage","section","section_activity_ordinal","task_family","question_type","skill","stimulus","prompt","options","correct_answer","grammar_targets","source_sentence_asset_ids","connected_passage","passage_id","passage_sentence_count","semantic_signature"))
 _write_json(paths[Q10R_JSON],run); _write_csv(paths[Q10R_CSV],run["runtime_occurrences"],("runtime_occurrence_id","slot_id","form_number","progression_stage","section","task_family","question_type","selected_item_id","candidate_ids","runtime_selection_rule","source_identity"))
 m={k:v for k,v in p.items() if k!="current_exports"}; m.update({"exported_q09_sha256":_digest(q9),"exported_q10_inventory_sha256":_digest(inv),"exported_q10_runtime_sha256":_digest(run)}); _write_json(paths[MANIFEST],m); return paths

def main()->int:
 p=build_export_payload(); q=p["q01_q10_map"]; print(f"STATUS={PASS_STATUS}"); print(f"Q5={q['Q05']['current_pattern_family_count']}/15"); print(f"Q6={q['Q06']['unit03_new_admitted']}"); print(f"Q7={q['Q07']['structural_pronoun_projection_rows']}"); print(f"Q8={q['Q08']['cumulative_function_count']}"); print(f"Q9={q['Q09']['task_family_count']}"); print(f"Q10={q['Q10']['runtime_occurrence_count']}"); print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}"); return 0
if __name__=="__main__": raise SystemExit(main())