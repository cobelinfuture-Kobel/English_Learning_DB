import json,importlib.util
from collections import Counter
from pathlib import Path
TASK_ID='KET_Data_S1R2_M04_ExactCompletenessValidator_CI_Merge_Closeout'; STATUS='PASS_KET_DATA_S1R2_M04_EXACT_COMPLETENESS_S1_CLOSEOUT'
class M04Error(ValueError): pass
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def m03(root):
 p=root/'validators/validate_ket_data_s1r2_m03_full_corpus_lineage.py'; s=importlib.util.spec_from_file_location('m03',p)
 if not s or not s.loader: raise M04Error('M03_IMPORT')
 m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def validate(root=None):
 root=Path(root or Path(__file__).resolve().parents[1]); a=load(root/'data/ket/ket_s1r2_m04_final_acceptance.json'); m=m03(root); mr=m.validate(root); x=m.materialize(root)
 if mr.get('status')!=m.STATUS: raise M04Error('M03_NOT_PASS')
 items=x['resolved_items']; ls=x['legacy_status']; sm=x['summary']; plan=x['plan']; ids=[i['item_id'] for i in items]
 if len(items)!=1452 or len(ids)!=len(set(ids)): raise M04Error('ITEM_TOTAL_OR_DUP')
 lc=Counter(v['status'] for v in ls.values())
 if sum(lc.values())!=629 or lc['UNRESOLVED']!=0: raise M04Error('LEGACY')
 if any((v['status']=='CONFIRMED_CANONICAL_ITEM')!=(iid in set(ids)) for iid,v in ls.items()): raise M04Error('LEGACY_RESOLUTION')
 exam=[i for i in items if i.get('task_profile_id')]; practice=[i for i in items if i.get('practice_part')]
 if (len(exam),len(practice))!=(1360,92): raise M04Error('INVENTORY')
 pc=Counter(i['task_profile_id'] for i in exam); expected=[96,112,80,96,96,16,16,80,80,80,80,80,256,192]
 if [pc[f'KET_S2_TASK_{n:03d}'] for n in range(1,15)]!=expected: raise M04Error('PROFILE_COUNTS')
 if tuple(map(sum,(expected[:7],expected[7:12],expected[12:])))!=(512,400,448): raise M04Error('SKILL_COUNTS')
 for k in ['duplicate_item_identity_count','ambiguous_legacy_match_count','broken_item_page_source_drive_lineage_count','new_image_identity_count','legacy_unresolved_count']:
  if sm.get(k)!=0: raise M04Error(k)
 s2=load(root/'data/ket/ket_s2_semantic_task_profiles.json'); profiles=s2.get('task_profiles') or []
 if len(profiles)!=14 or s2.get('scope',{}).get('s1_item_level_projection')!='NEXT_S2_MILESTONE': raise M04Error('S1_S2_BOUNDARY')
 if any(len(v.get('answer_key_pages') or [])!=4 for v in plan['official_exam_contract']['sources'].values()): raise M04Error('ANSWER_KEYS')
 inv={'source_count':34,'pdf_source_count':33,'page_count':1398,'image_identity_count':1572,'legacy_identity_count':629,'canonical_exam_item_count':1360,'practice_item_count':92,'total_confirmed_item_count':1452,'reading_writing_exam_item_count':512,'listening_exam_item_count':400,'speaking_exam_item_count':448,'canonical_task_profile_count':14}
 if a.get('expected_inventory')!=inv: raise M04Error('INVENTORY_CONTRACT')
 g=a.get('required_gates') or {}
 if any(g.get(k) is not True for k in ['PAGE_SEGMENTATION_COMPLETE','MEDIA_SEGMENTATION_COMPLETE','CANONICAL_ITEM_IDENTITY_COMPLETE','CANONICAL_EXAM_ITEM_COMPLETENESS','FULL_ITEM_BEARING_SOURCE_COMPLETENESS','ITEM_FALSE_POSITIVE_CLEAN','LISTENING_ITEM_COMPLETENESS','SPEAKING_ITEM_COMPLETENESS','REVERSE_LOOKUP_COMPLETE','S1_S2_BOUNDARY','S2_ITEM_PROJECTION_READINESS']): raise M04Error('BOOLEAN_GATES')
 for k in ['MISSING_CANONICAL_EXAM_ITEM_COUNT','UNRESOLVED_CANONICAL_EXAM_ITEM_COUNT','FALSE_POSITIVE_CONFIRMED_ITEM_COUNT','ORPHAN_CONFIRMED_ITEM_COUNT','BROKEN_ITEM_PAGE_SOURCE_LINEAGE','DUPLICATE_ITEM_IDENTITY_COUNT','AMBIGUOUS_LEGACY_MATCH_COUNT','NEW_IMAGE_IDENTITY_COUNT']:
  if g.get(k)!=0: raise M04Error('ZERO_GATE:'+k)
 return {'task_id':TASK_ID,'status':STATUS,**inv,'legacy_confirmed_count':lc['CONFIRMED_CANONICAL_ITEM'],'legacy_deprecated_non_item_count':lc['DEPRECATED_NON_ITEM'],'legacy_unresolved_count':0,'s1_exact_contract_pass':True,'s2_item_projection_readiness':True,'s2_item_projection_materialized':False,'s3_started':False,'next_milestone':'KET_Data_S2B_S1ItemSemanticProjection'}
if __name__=='__main__': print(json.dumps(validate(),ensure_ascii=False,indent=2))
