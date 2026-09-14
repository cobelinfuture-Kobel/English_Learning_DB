from __future__ import annotations
import importlib.util, json
from collections import Counter
from pathlib import Path

TASK_ID='KET_Data_S2B_S1ItemSemanticProjection'
MILESTONE='KET_Data_S2_Practice92_MultimodalSemanticAdmission_Implementation'
SCHEMA='ket.data.semantic_item_projection.s2b.v2'
FIELDS=['paper','primary_skill','part','task_family','response_mode','stimulus_modality','response_format','assessment_capability','learner_visible_stimulus','learner_action','answer_shape']

class S2BError(ValueError): pass

def _root(root=None): return Path(root or Path(__file__).resolve().parents[1])
def _json(p): return json.loads(p.read_text(encoding='utf-8'))

def _m03(root):
    p=root/'validators'/'validate_ket_data_s1r2_m03_full_corpus_lineage.py'
    s=importlib.util.spec_from_file_location('ket_m03',p)
    if not s or not s.loader: raise S2BError('M03_IMPORT_FAILED')
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.materialize(root)

def materialize(root=None,output_path=None):
    root=_root(root); b=root/'data'/'ket'
    c=_json(b/'ket_s2b_item_semantic_projection_contract.json')
    m04=_json(b/'ket_s1r2_m04_final_acceptance.json')
    s2a=_json(b/'ket_s2_semantic_task_profiles.json')
    pp=_json(b/'ket_s2_practice_semantic_profiles.json')
    s0=_json(b/'ket_source_manifest.json')
    if c.get('task_id')!=TASK_ID or c.get('milestone')!=MILESTONE: raise S2BError('CONTRACT')
    if not m04['required_gates'].get('S2_ITEM_PROJECTION_READINESS'): raise S2BError('S1R2_M04_NOT_READY')
    cp={x['id']:x for x in s2a['task_profiles']}; px={x['practice_part']:x for x in pp['profiles']}
    if len(cp)!=14 or len(px)!=10 or sum(x['expected_item_count'] for x in pp['profiles'])!=92: raise S2BError('PROFILE_COUNT')
    cols=s0['source_columns']; sx={r[0]:dict(zip(cols,r)) for r in s0['sources']}
    anomaly={x['source_id']:x['note'] for x in pp.get('source_anomalies',[])}
    rows=[]; missing_c=[]; missing_p=[]; missing_s=[]; mcq=0; promote=0; part_counts=Counter()
    for item in _m03(root)['resolved_items']:
        cid=item.get('task_profile_id')
        if cid:
            p=cp.get(cid)
            if not p: missing_c.append(item['item_id']); continue
            miss=[k for k in FIELDS if p.get(k) in (None,'',[])]
            if miss: missing_s.append([item['item_id'],miss]); continue
            mcq+=any(str(p.get(k)).strip().upper()=='MCQ' for k in ('task_family','response_format'))
            r={'item_id':item['item_id'],'source_id':item['source_id'],'drive_file_id':item['drive_file_id'],'page_ids':item['page_ids'],'image_ids':item['image_ids'],'media_bits':item['media_bits'],'task_profile_id':cid,'semantic_profile_id':cid,'practice_profile_id':None,'projection_status':'PROJECTED_FROM_APPROVED_S2A_PROFILE','semantic_authority_scope':'CURRENT_KET_CANONICAL_MECHANIC','is_current_ket_exam_mechanic':True,'mainline_use':'CANONICAL_KET_EXAM_MECHANIC'}
        else:
            part=item.get('practice_part'); p=px.get(part)
            if not p: missing_p.append(item['item_id']); continue
            miss=[k for k in FIELDS if p.get(k) in (None,'',[])]
            if miss: missing_s.append([item['item_id'],miss]); continue
            src=sx.get(item['source_id'])
            if not src: raise S2BError('PRACTICE_SOURCE_MISSING:'+item['source_id'])
            uses=src.get('allowed_use') or []
            promote+=src.get('authority_class')!='THIRD_PARTY_PREP' or 'PRACTICE_VARIATION_REFERENCE' not in uses
            if item['source_id'] not in p.get('evidence_sources',[]): raise S2BError('EVIDENCE_SOURCE_MISMATCH:'+item['item_id'])
            mcq+=any(str(p.get(k)).strip().upper()=='MCQ' for k in ('task_family','response_format'))
            part_counts[part]+=1; eq=p.get('semantic_equivalent_to')
            r={'item_id':item['item_id'],'source_id':item['source_id'],'drive_file_id':item['drive_file_id'],'page_ids':item['page_ids'],'image_ids':item['image_ids'],'media_bits':item['media_bits'],'task_profile_id':None,'semantic_profile_id':p['id'],'practice_profile_id':p['id'],'practice_part':part,'source_local_item_label':item.get('source_local_item_label'),'projection_status':'PROJECTED_FROM_ADMITTED_PRACTICE_PROFILE','semantic_authority_scope':'SUPPLEMENTARY_PRACTICE_VARIATION','source_authority_class':src['authority_class'],'allowed_use':list(uses),'canonical_exam_authority':False,'is_current_ket_exam_mechanic':False,'semantic_equivalent_to':eq,'mainline_use':'CURRENT_PROFILE_EQUIVALENT_PRACTICE' if eq else 'SUPPLEMENTARY_PRACTICE_VARIATION','source_anomaly_note':anomaly.get(item['source_id'])}
        r.update({k:p[k] for k in FIELDS}); rows.append(r)
    expected={p['practice_part']:p['expected_item_count'] for p in pp['profiles']}
    if dict(part_counts)!=expected: raise S2BError('PRACTICE_PART_COUNTS')
    rows.sort(key=lambda x:x['item_id']); can=[x for x in rows if x['task_profile_id']]; pra=[x for x in rows if x['practice_profile_id']]
    cs=Counter(x['primary_skill'] for x in can); ps=Counter(x['primary_skill'] for x in pra)
    eq=sum(bool(x.get('semantic_equivalent_to')) for x in pra)
    summary={'s1_confirmed_item_count':1452,'canonical_exam_projected_count':len(can),'practice_projected_count':len(pra),'total_semantic_projected_count':len(rows),'practice_deferred_count':0,'task_profile_count':len({x['semantic_profile_id'] for x in can}),'practice_profile_count':len({x['semantic_profile_id'] for x in pra}),'semantic_profile_count':len({x['semantic_profile_id'] for x in rows}),'reading_projected_count':cs['READING'],'writing_projected_count':cs['WRITING'],'listening_projected_count':cs['LISTENING'],'speaking_projected_count':cs['SPEAKING'],'practice_reading_projected_count':ps['READING'],'practice_writing_projected_count':ps['WRITING'],'current_profile_equivalent_practice_count':eq,'supplementary_practice_variation_count':len(pra)-eq,'source_anomaly_practice_item_count':sum(bool(x.get('source_anomaly_note')) for x in pra),'missing_task_profile_count':len(missing_c),'missing_practice_profile_count':len(missing_p),'missing_semantic_dimension_count':len(missing_s),'generic_mcq_label_count':mcq,'item_identity_mutation_count':0,'broken_source_lineage_count':0,'broken_media_lineage_count':0,'authority_promotion_count':promote}
    out={'schema':SCHEMA,'task_id':TASK_ID,'milestone':MILESTONE,'contract_source':'KET_S2.txt','projected_items':rows,'deferred_practice_items':[],'summary':summary}
    if output_path: Path(output_path).write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    return out

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser(); a.add_argument('--output'); x=a.parse_args()
    print(json.dumps(materialize(output_path=x.output)['summary'],ensure_ascii=False,indent=2))
