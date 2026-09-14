from __future__ import annotations
import importlib.util, json
from pathlib import Path

TASK_ID='KET_Data_S2B_S1ItemSemanticProjection'
MILESTONE='KET_Data_S2_Practice92_MultimodalSemanticAdmission_Implementation'
STATUS='PASS_KET_DATA_S2_PRACTICE92_MULTIMODAL_SEMANTIC_ADMISSION'
EXPECTED={'s1_confirmed_item_count':1452,'canonical_exam_projected_count':1360,'practice_projected_count':92,'total_semantic_projected_count':1452,'practice_deferred_count':0,'task_profile_count':14,'practice_profile_count':10,'semantic_profile_count':24,'current_profile_equivalent_practice_count':12,'supplementary_practice_variation_count':80,'missing_task_profile_count':0,'missing_practice_profile_count':0,'missing_semantic_dimension_count':0,'generic_mcq_label_count':0,'item_identity_mutation_count':0,'broken_source_lineage_count':0,'broken_media_lineage_count':0,'authority_promotion_count':0}

def validate(root=None):
    root=Path(root or Path(__file__).resolve().parents[1]); p=root/'builders'/'build_ket_data_s2b_item_semantic_projection.py'
    s=importlib.util.spec_from_file_location('ket_s2b_builder',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    out=m.materialize(root); q=out['summary']; errors=[f'{k}:{q.get(k)}!={v}' for k,v in EXPECTED.items() if q.get(k)!=v]
    if out.get('milestone')!=MILESTONE or out.get('deferred_practice_items')!=[]: errors.append('CONTRACT_OR_DEFERRED')
    practice=[x for x in out['projected_items'] if x.get('practice_profile_id')]
    if any(x.get('source_authority_class')!='THIRD_PARTY_PREP' or x.get('canonical_exam_authority') is not False for x in practice): errors.append('PRACTICE_AUTHORITY')
    if errors: raise ValueError('\n'.join(errors))
    return {'task_id':TASK_ID,'milestone':MILESTONE,'status':STATUS,**q,'canonical_exam_projection':'PASS','practice_projection':'PASS_ADMITTED_SUPPLEMENTARY_PRACTICE','practice_authority':'THIRD_PARTY_PREP_PRACTICE_VARIATION_REFERENCE','practice_deferred':'NONE','s1_identity_preserved':True,'s2a_canonical_taxonomy_preserved':True,'authority_promotion':False,'s3_started':False}

if __name__=='__main__': print(json.dumps(validate(),ensure_ascii=False,indent=2))
