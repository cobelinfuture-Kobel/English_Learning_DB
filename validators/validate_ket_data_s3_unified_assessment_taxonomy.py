from __future__ import annotations
import importlib.util, json
from collections import Counter
from pathlib import Path

TASK_ID="KET_Data_S3_UnifiedFiveLayerAssessmentTaxonomy"
STATUS="PASS_KET_DATA_S3_UNIFIED_FIVE_LAYER_ASSESSMENT_TAXONOMY"
MODES=["SELECT","MATCH","TEXT_ENTRY","STRUCTURED_ENTRY","ORDER","SPEAK"]
LAYERS=["response_mode","task_family","stimulus_modality","assessment_capability","response_format"]
N=1452

def _load(path): return json.loads(path.read_text(encoding="utf-8"))
def _s2b(root):
    p=root/"builders"/"build_ket_data_s2b_item_semantic_projection.py"
    s=importlib.util.spec_from_file_location("ket_s2b_for_s3",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m.materialize(root)

def validate(root=None):
    root=Path(root or Path(__file__).resolve().parents[1])
    c=_load(root/"data"/"ket"/"ket_s3_unified_assessment_taxonomy.json"); out=_s2b(root); q=out["summary"]; errors=[]
    if c.get("schema_version")!="ket_data_s3_unified_assessment_taxonomy_v1" or c.get("task_id")!=TASK_ID: errors.append("CONTRACT_ID")
    if c.get("source_stage")!="KET_DATA_S2B" or c.get("output_stage")!="KET_DATA_S3": errors.append("STAGE_CHAIN")
    if c.get("layer_order")!=LAYERS or c.get("item_projection_denominator")!=N: errors.append("LAYER_OR_DENOMINATOR")
    layers=c.get("layers",{}); sets={k:set(layers.get(k,{}).get("values",[])) for k in LAYERS}
    if set(layers)!=set(LAYERS) or layers.get("response_mode",{}).get("values")!=MODES: errors.append("FIVE_LAYER_OR_SIX_MODE_CONTRACT")
    if any(not sets[k] or len(sets[k])!=len(layers[k]["values"]) for k in LAYERS): errors.append("LAYER_ENUM")
    for i,a in enumerate(LAYERS):
        for b in LAYERS[i+1:]:
            if sets[a]&sets[b]: errors.append(f"LAYER_MIXING:{a}:{b}:{sorted(sets[a]&sets[b])}")
    rules=c.get("profile_normalizations",[]); rx={r.get("semantic_profile_id"):r for r in rules}
    if len(rules)!=24 or len(rx)!=24 or None in rx: errors.append("PROFILE_RULE_COUNT")
    items=out.get("projected_items",[])
    if len(items)!=N or q.get("canonical_exam_projected_count")!=1360 or q.get("practice_projected_count")!=92: errors.append("S2B_DENOMINATOR")
    coverage=Counter(); missing=[]; mismatch=[]; invalid=[]; mode_mut=[]; promoted=[]
    for x in items:
        pid=x.get("semantic_profile_id"); r=rx.get(pid)
        if not r: missing.append([x.get("item_id"),pid]); continue
        src=r.get("source_values",{}); norm=r.get("normalized_values",{})
        for k in ("task_family","response_mode","stimulus_modality","response_format","assessment_capability"):
            if x.get(k)!=src.get(k): mismatch.append([x.get("item_id"),pid,k,x.get(k),src.get(k)])
        vals={"response_mode":norm.get("response_mode"),"task_family":norm.get("task_family"),"stimulus_modality":norm.get("stimulus_modality"),"response_format":norm.get("response_format")}
        caps=norm.get("assessment_capabilities") or []
        if vals["response_mode"]!=x.get("response_mode") or vals["response_mode"] not in sets["response_mode"]: mode_mut.append(x.get("item_id"))
        for k,v in vals.items():
            if k!="response_mode" and v not in sets[k]: invalid.append([x.get("item_id"),k,v])
        if not caps or any(v not in sets["assessment_capability"] for v in caps): invalid.append([x.get("item_id"),"assessment_capability",caps])
        if x.get("semantic_authority_scope")!=r.get("authority_scope"): mismatch.append([x.get("item_id"),pid,"authority_scope"])
        if x.get("practice_profile_id") and (x.get("canonical_exam_authority") is not False or x.get("source_authority_class")!="THIRD_PARTY_PREP"): promoted.append(x.get("item_id"))
        for k in LAYERS: coverage[k]+=1
    if missing: errors.append("MISSING_PROFILE:"+repr(missing[:3]))
    if mismatch: errors.append("SOURCE_DRIFT:"+repr(mismatch[:3]))
    if invalid: errors.append("INVALID_NORMALIZATION:"+repr(invalid[:3]))
    if mode_mut: errors.append("RESPONSE_MODE_MUTATION:"+repr(mode_mut[:3]))
    if promoted: errors.append("PRACTICE_AUTHORITY_PROMOTION:"+repr(promoted[:3]))
    if any(coverage[k]!=N for k in LAYERS): errors.append("FIVE_LAYER_COVERAGE:"+repr(dict(coverage)))
    if errors: raise ValueError("\n".join(errors))
    return {"task_id":TASK_ID,"status":STATUS,"s2b_item_count":N,"canonical_exam_item_count":1360,"supplementary_practice_item_count":92,"semantic_profile_count":24,"response_modes":MODES,"five_layer_coverage":{k:coverage[k] for k in LAYERS},"missing_profile_mapping_count":0,"source_value_mismatch_count":0,"invalid_normalized_value_count":0,"response_mode_mutation_count":0,"layer_token_mixing_count":0,"practice_authority_promotion_count":0,"source_semantics_preserved":True,"all_1452_items_resolve_to_five_layers":True}

if __name__=="__main__": print(json.dumps(validate(),ensure_ascii=False,indent=2))
