#!/usr/bin/env python3
"""Independent validation for Unit01 cumulative model-authored micro-scene expansion."""
from __future__ import annotations
import argparse,json
from copy import deepcopy
from pathlib import Path
from typing import Any,Mapping,Sequence
from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as r1
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as builder
PASS_STATUS="PASS_A1FS_V1_U01QB07_UNIT01_MICRO_SCENE_SEED_ENRICHMENT_VALIDATION"
class SceneEnrichmentValidationError(ValueError):pass

def read_json(p:Path)->dict[str,Any]:
 try:v=json.loads(p.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError) as e:raise SceneEnrichmentValidationError(f"UNREADABLE_JSON:{p}:{e}") from e
 if not isinstance(v,dict):raise SceneEnrichmentValidationError("OBJECT_REQUIRED")
 return v
def validate(pool:Mapping[str,Any])->dict[str,Any]:
 e=[]
 if pool.get("schema_version")!=builder.SCHEMA_VERSION:e.append("schema_version_invalid")
 if pool.get("task_id")!=builder.TASK_ID or pool.get("status")!=builder.PASS_STATUS or pool.get("unit_id")!=builder.UNIT_ID:e.append("identity_invalid")
 if pool.get("scene_growth_policy")!=r1.SCENE_GROWTH_POLICY:e.append("scene_growth_policy_invalid")
 model=pool.get("model_authored_scenes") if isinstance(pool.get("model_authored_scenes"),list) else []
 combined=pool.get("cumulative_unique_scenes") if isinstance(pool.get("cumulative_unique_scenes"),list) else []
 if len(model)!=builder.EXPECTED_SUPPLEMENT_COUNT:e.append("model_authored_count_invalid")
 sigs=[]
 for row in model:
  if not isinstance(row,Mapping):e.append("model_scene_not_object");continue
  core=row.get("semantic_scene_core") or {};sigs.append(str(row.get("semantic_scene_signature_v2")))
  if row.get("semantic_scene_signature_v2")!=r1.digest(core):e.append("semantic_signature_invalid")
  if r1.genuine_scene_reason_codes(core):e.append("model_scene_fails_genuine_gate")
  if row.get("scene_taxonomy")!=r1.scene_taxonomy(core):e.append("taxonomy_invalid")
  if row.get("lineage_mode")!="MODEL_AUTHORED_FROM_APPROVED_SEEDS":e.append("lineage_mode_invalid")
  p=row.get("provenance") or {}
  if not p.get("resolved_seed_scene_ref_ids") or p.get("source_equivalence_claimed") is not False:e.append("seed_provenance_invalid")
  if row.get("counts_toward_scene_rotation") is not True:e.append("model_scene_not_rotation_ready")
 if len(sigs)!=len(set(sigs)):e.append("model_semantic_duplicate")
 combined_sigs=[str(x.get("semantic_scene_signature_v2")) for x in combined if isinstance(x,Mapping)]
 if len(combined_sigs)!=len(set(combined_sigs)):e.append("combined_semantic_duplicate")
 cap=pool.get("rotation_capacity") or {};total=len(combined);families={str(x.get("situation_family")) for x in combined if isinstance(x,Mapping) and x.get("situation_family")!="UNCLASSIFIED_OBJECT"}
 expected={"genuine_distinct_micro_scene_count":total,"target_range":[builder.TARGET_MIN,builder.TARGET_MAX],"target_range_pass":builder.TARGET_MIN<=total<=builder.TARGET_MAX,"hard_min_24_pass":total>=24,"situation_family_count":len(families),"situation_family_min_5_pass":len(families)>=5,"maximum_scene_slots_at_two_uses_each":total*2,"required_scene_slots":48,"twelve_form_rotation_ready":total>=24 and len(families)>=5}
 if cap!=expected:e.append("rotation_capacity_invalid")
 if not expected["target_range_pass"]:e.append("target_range_not_met")
 if not expected["twelve_form_rotation_ready"]:e.append("twelve_form_capacity_not_met")
 b=pool.get("boundaries") or {}
 if b!={"source_equivalence_claimed":False,"question_items_mutated":False,"scoring_mutated":False,"learner_state_mutated":False,"mastery_claimed":False}:e.append("boundaries_invalid")
 unsigned=deepcopy(dict(pool));declared=unsigned.pop("pool_sha256",None)
 if declared!=r1.digest(unsigned):e.append("pool_sha256_invalid")
 report={"status":PASS_STATUS if not e else "FAIL_A1FS_V1_U01QB07_VALIDATION","error_count":len(e),"errors":e,"cumulative_distinct_scene_count":total,"situation_family_count":len(families),"twelve_form_rotation_ready":expected["twelve_form_rotation_ready"]}
 if e:raise SceneEnrichmentValidationError("|".join(e))
 return report
def main(argv:Sequence[str]|None=None)->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--pool",type=Path,required=True);a=p.parse_args(argv)
 try:r=validate(read_json(a.pool))
 except (SceneEnrichmentValidationError,KeyError,TypeError,ValueError) as e:print("STATUS=FAIL_A1FS_V1_U01QB07_UNIT01_MICRO_SCENE_SEED_ENRICHMENT_VALIDATION");print(f"ERROR={e}");return 1
 print(f"STATUS={r['status']}");print(f"CUMULATIVE_DISTINCT_SCENES={r['cumulative_distinct_scene_count']}");print(f"SITUATION_FAMILIES={r['situation_family_count']}");print(f"TWELVE_FORM_ROTATION_READY={r['twelve_form_rotation_ready']}");return 0
if __name__=="__main__":raise SystemExit(main())
