import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('ket_s2',ROOT/'validators'/'validate_ket_data_s2_semantic_scan.py')
assert SPEC and SPEC.loader
target=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(target)

def test_ket_data_s2a_canonical_semantic_scan_contract():
    r=target.validate()
    assert r['status']==target.STATUS
    assert r['contract_source']=='KET_S2.txt'
    assert r['task_profile_count']==14
    assert r['skill_counts']=={'READING':5,'WRITING':2,'LISTENING':5,'SPEAKING':2}
    assert r['response_modes_used']==['MATCH','SELECT','SPEAK','STRUCTURED_ENTRY','TEXT_ENTRY']
    assert r['primary_source_id']=='KET_SRC_000004'
    assert r['cross_variant_source_id']=='KET_SRC_000011'
    assert r['s1_predecessor']=='PASS'
    assert r['generic_mcq_labels']==0
    assert r['semantic_dimensions_complete'] is True
