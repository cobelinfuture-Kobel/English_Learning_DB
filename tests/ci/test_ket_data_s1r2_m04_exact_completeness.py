import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
S=importlib.util.spec_from_file_location('m04',ROOT/'validators/validate_ket_data_s1r2_m04_exact_completeness.py'); assert S and S.loader
m=importlib.util.module_from_spec(S); S.loader.exec_module(m)
def test_s1r2_m04_exact_closeout():
 r=m.validate(ROOT)
 assert r['status']==m.STATUS and r['s1_exact_contract_pass'] is True
 assert (r['page_count'],r['image_identity_count'],r['legacy_identity_count'])==(1398,1572,629)
 assert r['legacy_confirmed_count']+r['legacy_deprecated_non_item_count']==629 and r['legacy_unresolved_count']==0
 assert (r['canonical_exam_item_count'],r['practice_item_count'],r['total_confirmed_item_count'])==(1360,92,1452)
 assert (r['reading_writing_exam_item_count'],r['listening_exam_item_count'],r['speaking_exam_item_count'])==(512,400,448)
 assert r['canonical_task_profile_count']==14
 assert r['s2_item_projection_readiness'] is True and r['s2_item_projection_materialized'] is False
 assert r['s3_started'] is False and r['next_milestone']=='KET_Data_S2B_S1ItemSemanticProjection'
