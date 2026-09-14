from __future__ import annotations

import base64
import hashlib
import json
import lzma
from collections import Counter, defaultdict
from pathlib import Path

TASK_ID = 'KET_Data_S1R2_M03_RehydrateExactLegacy629Map_ThenFullCorpusLineageMaterialization'
STATUS = 'PASS_KET_DATA_S1R2_M03_FULL_CORPUS_LINEAGE'
S1_XZ_SHA = 'b557257b09693a65069e42885c4cbe76347a27e5f54c8090b9b94646252d6a04'
S1_JSON_SHA = 'b915a0af67a57ae8b6b2b3ac7f16d8f2a6466b18bd6a3b41f50d6aa02a232480'

class M03Error(ValueError):
    pass

def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])

def _load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def _load_xz_b64(path: Path):
    raw = lzma.decompress(base64.b64decode(path.read_text(encoding='ascii').strip()), format=lzma.FORMAT_XZ)
    return json.loads(raw)

def _load_s1(root: Path):
    base = root / 'data' / 'ket'
    b64 = ''.join((base / f'ket_page_media_segmentation.json.xz.b64.part{i}').read_text(encoding='ascii').strip() for i in (0,1))
    xz = base64.b64decode(b64, validate=True)
    if hashlib.sha256(xz).hexdigest() != S1_XZ_SHA: raise M03Error('S1_XZ_SHA256_DRIFT')
    raw = lzma.decompress(xz, format=lzma.FORMAT_XZ)
    if hashlib.sha256(raw).hexdigest() != S1_JSON_SHA: raise M03Error('S1_JSON_SHA256_DRIFT')
    return json.loads(raw)

def _page_map(s1):
    ss = s1['ss']; out = {}
    for row in s1['ps']:
        pid, si, pn, w, h, tm, regs, istart, qstart, labels, bits = row
        sid, drive = ss[si][0], ss[si][1]
        images = [f'KET_IMG_{istart+i:06d}' for i in range(len(regs[5]))] if istart is not None else []
        out[pid] = {'source_id':sid,'drive_file_id':drive,'page_number':pn,'question_boxes':regs[2],'question_start':qstart,'labels':labels,'image_ids':images,'media_bits':bits}
    return out

def rehydrate_legacy629(s1):
    pages = _page_map(s1); legacy = []
    for pid,p in pages.items():
        qstart, boxes, labels = p['question_start'], p['question_boxes'], p['labels']
        if qstart is None:
            if boxes or labels: raise M03Error(f'LEGACY_PAGE_QSTART_MISSING:{pid}')
            continue
        if len(boxes) != len(labels): raise M03Error(f'LEGACY_BOX_LABEL_COUNT:{pid}')
        for off,(bbox,label) in enumerate(zip(boxes,labels)):
            n=qstart+off
            legacy.append({'item_id':f'KET_ITEM_{n:06d}','item_num':n,'source_id':p['source_id'],'drive_file_id':p['drive_file_id'],'page_id':pid,'page_number':p['page_number'],'source_local_item_label':label,'question_candidate_bbox':bbox,'image_ids':list(p['image_ids']),'media_bits':p['media_bits']})
    legacy.sort(key=lambda x:x['item_num'])
    if [x['item_num'] for x in legacy] != list(range(1,630)): raise M03Error('LEGACY629_SEQUENCE_DRIFT')
    return legacy,pages

def _expand_exam(plan):
    specs={x['id']:x for x in plan['official_exam_contract']['profile_specs']}; rows=[]
    for sid,src in sorted(plan['official_exam_contract']['sources'].items()):
        for t in range(1,5):
            if sid=='KET_SRC_000004' and t==1: continue
            rw=src['rw_start']+16*(t-1); li=src['listening_start']+16*(t-1); sp=src['speaking_start']+3*(t-1); visual=src['visual_pages'][t-1]; answer=src['answer_key_pages'][t-1]
            for pid in [f'KET_S2_TASK_{i:03d}' for i in range(1,15)]:
                spec=specs[pid]; base=rw if spec['paper']=='READING_AND_WRITING' else li if spec['paper']=='LISTENING' else sp
                nums=[visual if off=='VISUAL' else base+int(off) for off in spec['page_offsets']]; pids=[f'{sid}_P{x:03d}' for x in nums]
                for ordinal,label in enumerate(spec['labels'],1):
                    rows.append({'kind':'CANONICAL_EXAM','source_id':sid,'test_index':t,'task_profile_id':pid,'paper':spec['paper'],'source_local_item_label':str(label),'legacy_numeric_label':label if isinstance(label,int) else None,'page_ids':pids,'answer_key_page_id':f'{sid}_P{answer:03d}','stable_order':[int(sid[-6:]),t,int(pid[-3:]),ordinal]})
    return rows

def _expand_practice(plan):
    rows=[]
    for so,src in enumerate(plan['practice_contract']['sources'],1):
        sid=src['source_id']
        for go,g in enumerate(src['groups'],1):
            nums=g.get('pages') or [g['page']]; pids=[f'{sid}_P{x:03d}' for x in nums]
            for io,label in enumerate(g['labels'],1):
                rows.append({'kind':'PRACTICE_VARIATION','source_id':sid,'practice_part':g['part'],'source_local_item_label':f"{g['part']}:{label}",'legacy_numeric_label':label if isinstance(label,int) else None,'page_ids':pids,'answer_key_page_id':f'{sid}_P{max(nums)+1:03d}','stable_order':[100+so,go,io]})
    return rows

def _validate_plan(plan):
    expected={'canonical_exam_items':1360,'practice_items':92,'total_admitted_items':1452,'m02_preexisting_items':85,'remaining_items_to_resolve_in_m03':1367}
    if plan.get('schema')!='ket.data.s1r2.full_corpus_lineage_plan.m03.v1': raise M03Error('SCHEMA')
    if plan.get('task_id')!=TASK_ID: raise M03Error('TASK_ID')
    if plan.get('contract_source')!='KET_S1_revised.txt': raise M03Error('CONTRACT_SOURCE')
    if plan.get('expected_inventory')!=expected: raise M03Error('EXPECTED_INVENTORY')

def materialize(root=None):
    root=_root(root); base=root/'data'/'ket'
    plan=_load_json(base/'ket_s1r2_m03_full_corpus_lineage_plan.json'); _validate_plan(plan)
    state=_load_json(base/'ket_s1r2_item_identity_state.json'); m02=_load_xz_b64(base/'ket_s1r2_canonical_exam_items.json.xz.b64'); s0=_load_json(base/'ket_source_manifest.json'); s1=_load_s1(root)
    if state['contract_sha256']!=plan['contract_sha256']: raise M03Error('CONTRACT_SHA_MISMATCH')
    if m02['new_identity_range']['next_available_new_item_id']!='KET_ITEM_000715' or len(m02['items'])!=85: raise M03Error('M02_PREDECESSOR_DRIFT')
    legacy,pages=rehydrate_legacy629(s1)
    cols=s0['source_columns']; source_rows=[dict(zip(cols,row)) for row in s0['sources']]; source_by_id={x['source_id']:x for x in source_rows}; admitted=set(plan['scope']['identity_bearing_source_ids'])
    for sid in admitted:
        if sid not in source_by_id: raise M03Error(f'PLANNED_SOURCE_NOT_IN_S0:{sid}')
        uses=set(source_by_id[sid]['allowed_use'])
        if not uses.intersection(plan['scope']['identity_bearing_allowed_use']): raise M03Error(f'PLANNED_SOURCE_ROLE_NOT_AUTHORIZED:{sid}:{uses}')
    planned=_expand_exam(plan)+_expand_practice(plan)
    if len(planned)!=1367: raise M03Error(f'PLANNED_REMAINING_COUNT:{len(planned)}')
    planned.sort(key=lambda x:x['stable_order'])
    missing=sorted({pid for x in planned for pid in x['page_ids'] if pid not in pages})
    if missing: raise M03Error('PLANNED_PAGE_MISSING:'+','.join(missing[:20]))
    legacy_index=defaultdict(list)
    for x in legacy:
        lab=x['source_local_item_label']
        if isinstance(lab,int): legacy_index[(x['source_id'],lab)].append(x)
    for vals in legacy_index.values(): vals.sort(key=lambda x:(x['page_number'],x['question_candidate_bbox'][1],x['question_candidate_bbox'][0],x['item_num']))
    groups=defaultdict(list)
    for x in planned:
        if x['legacy_numeric_label'] is not None: groups[(x['source_id'],x['legacy_numeric_label'],tuple(sorted(x['page_ids'])))].append(x)
    reuse={}; used=set(); ambiguous=[]
    for sig,prows in groups.items():
        sid,label,pids=sig; candidates=[x for x in legacy_index.get((sid,label),[]) if x['page_id'] in pids and x['item_id'] not in used]
        if len(candidates)>len(prows): ambiguous.append({'signature':[sid,label,list(pids)],'planned_count':len(prows),'legacy_ids':[x['item_id'] for x in candidates]}); continue
        for prow,cand in zip(prows,candidates): reuse[id(prow)]=cand; used.add(cand['item_id'])
    if ambiguous: raise M03Error('AMBIGUOUS_LEGACY_MATCHES:'+json.dumps(ambiguous[:20],ensure_ascii=False))
    resolved=[]
    for x in m02['items']:
        pids=list(x['page_ids']); imgs=sorted({img for pid in pids for img in pages.get(pid,{}).get('image_ids',[])}); bits=0
        for pid in pids: bits |= pages.get(pid,{}).get('media_bits',0)
        resolved.append({'item_id':x['item_id'],'identity_origin':'M02_FIXED_CANONICAL_TEST1','identity_status':'CONFIRMED_CANONICAL_ITEM','source_id':x['source_id'],'drive_file_id':source_by_id[x['source_id']]['drive_file_id'],'source_local_item_label':x['source_local_item_label'],'task_profile_id':x['task_profile_id'],'page_ids':pids,'image_ids':imgs,'media_bits':bits,'legacy_question_candidate_bbox':None})
    next_new=715; reused=[]; new=[]
    for x in planned:
        cand=reuse.get(id(x))
        if cand is not None: iid=cand['item_id']; reused.append(iid); bbox=cand['question_candidate_bbox']; origin='REUSED_FROZEN_LEGACY_ID_EXACT_SOURCE_LABEL_PAGE_MATCH'
        else: iid=f'KET_ITEM_{next_new:06d}'; next_new+=1; new.append(iid); bbox=None; origin='NEW_M03_ID_NO_ADMISSIBLE_LEGACY_ID'
        pids=x['page_ids']; imgs=sorted({img for pid in pids for img in pages[pid]['image_ids']}); bits=0
        for pid in pids: bits |= pages[pid]['media_bits']
        resolved.append({'item_id':iid,'identity_origin':origin,'identity_status':'CONFIRMED_CANONICAL_ITEM','source_id':x['source_id'],'drive_file_id':source_by_id[x['source_id']]['drive_file_id'],'source_local_item_label':x['source_local_item_label'],'task_profile_id':x.get('task_profile_id'),'practice_part':x.get('practice_part'),'test_index':x.get('test_index'),'page_ids':pids,'answer_key_page_id':x.get('answer_key_page_id'),'image_ids':imgs,'media_bits':bits,'legacy_question_candidate_bbox':bbox})
    ids=[x['item_id'] for x in resolved]
    if len(ids)!=len(set(ids)): raise M03Error('DUPLICATE_RESOLVED_ITEM_IDS')
    if len(resolved)!=1452: raise M03Error(f'RESOLVED_TOTAL:{len(resolved)}')
    reused_set=set(reused); legacy_status={}
    for x in legacy:
        if x['item_id'] in reused_set: legacy_status[x['item_id']]={'status':'CONFIRMED_CANONICAL_ITEM','reason':'EXACT_M03_SOURCE_LABEL_PAGE_MATCH'}
        else:
            uses=source_by_id[x['source_id']]['allowed_use']; reason=('SOURCE_ROLE_NOT_ADMITTED_FOR_M03_ITEM_IDENTITY:'+'+'.join(uses)) if x['source_id'] not in admitted else 'LEGACY_CANDIDATE_NOT_IN_ADMITTED_SOURCE_TASK_PRACTICE_INVENTORY'
            legacy_status[x['item_id']]={'status':'DEPRECATED_NON_ITEM','reason':reason}
    sc=Counter(v['status'] for v in legacy_status.values()); broken=[]
    for x in resolved:
        if not x['drive_file_id'] or not x['page_ids']: broken.append(x['item_id']); continue
        for pid in x['page_ids']:
            if pid not in pages or pages[pid]['source_id']!=x['source_id']: broken.append(x['item_id']); break
    if broken: raise M03Error('BROKEN_ITEM_PAGE_SOURCE_DRIVE_LINEAGE:'+','.join(broken[:20]))
    return {'plan':plan,'legacy':legacy,'legacy_status':legacy_status,'resolved_items':resolved,'summary':{'legacy_rehydrated_count':629,'legacy_confirmed_reuse_count':sc['CONFIRMED_CANONICAL_ITEM'],'legacy_deprecated_non_item_count':sc['DEPRECATED_NON_ITEM'],'legacy_unresolved_count':sc['UNRESOLVED'],'m02_fixed_item_count':85,'m03_planned_remaining_count':1367,'m03_legacy_reused_count':len(reused),'m03_new_item_count':len(new),'total_confirmed_item_count':1452,'first_m03_new_item_id':new[0] if new else None,'last_m03_new_item_id':new[-1] if new else None,'next_available_new_item_id':f'KET_ITEM_{next_new:06d}','duplicate_item_identity_count':0,'ambiguous_legacy_match_count':0,'broken_item_page_source_drive_lineage_count':0,'new_image_identity_count':0}}

def validate(root=None):
    s=materialize(root)['summary']; e=[]
    if s['legacy_rehydrated_count']!=629:e.append('LEGACY629')
    if s['legacy_unresolved_count']!=0:e.append(f"UNRESOLVED_LEGACY:{s['legacy_unresolved_count']}")
    if s['m02_fixed_item_count']!=85:e.append('M02_FIXED')
    if s['m03_planned_remaining_count']!=1367:e.append('M03_PLANNED')
    if s['total_confirmed_item_count']!=1452:e.append('TOTAL_CONFIRMED')
    if s['duplicate_item_identity_count'] or s['ambiguous_legacy_match_count'] or s['broken_item_page_source_drive_lineage_count'] or s['new_image_identity_count']:e.append('LINEAGE_GATE')
    if e: raise M03Error('\n'.join(e))
    return {'task_id':TASK_ID,'status':STATUS,**s,'full_item_bearing_source_completeness':'PASS_FOR_S0_TASK_MECHANIC_AND_PRACTICE_VARIATION_AUTHORIZED_SOURCES','s2_item_projection_readiness':False,'next_milestone':'KET_Data_S1R2_M04_ExactCompletenessValidator_CI_Merge_Closeout'}

if __name__=='__main__':
    print(json.dumps(validate(),ensure_ascii=False,indent=2))
