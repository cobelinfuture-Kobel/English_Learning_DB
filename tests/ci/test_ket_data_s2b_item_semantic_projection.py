import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
S=importlib.util.spec_from_file_location('s2b',ROOT/'validators'/'validate_ket_data_s2b_item_semantic_projection.py')
assert S and S.loader
s2b=importlib.util.module_from_spec(S); S.loader.exec_module(s2b)

def test_ket_data_s2b_s1_item_semantic_projection():
    r=s2b.validate(ROOT)
    assert r['status']==s2b.STATUS
    assert r['s1_confirmed_item_count']==1452
    assert r['canonical_exam_projected_count']==1360
    assert r['practice_projected_count']==92
    assert r['total_semantic_projected_count']==1452
    assert r['practice_deferred_count']==0
    assert r['task_profile_count']==14
    assert r['practice_profile_count']==10
    assert r['semantic_profile_count']==24
    assert r['current_profile_equivalent_practice_count']==12
    assert r['supplementary_practice_variation_count']==80
    assert r['missing_task_profile_count']==0
    assert r['missing_practice_profile_count']==0
    assert r['missing_semantic_dimension_count']==0
    assert r['generic_mcq_label_count']==0
    assert r['item_identity_mutation_count']==0
    assert r['broken_source_lineage_count']==0
    assert r['broken_media_lineage_count']==0
    assert r['authority_promotion_count']==0
    assert r['canonical_exam_projection']=='PASS'
    assert r['practice_projection']=='PASS_ADMITTED_SUPPLEMENTARY_PRACTICE'
    assert r['practice_authority']=='THIRD_PARTY_PREP_PRACTICE_VARIATION_REFERENCE'
    assert r['practice_deferred']=='NONE'
    assert r['s1_identity_preserved'] is True
    assert r['s2a_canonical_taxonomy_preserved'] is True
    assert r['authority_promotion'] is False
    assert r['s3_started'] is False
