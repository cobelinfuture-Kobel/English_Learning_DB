import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('s2b', ROOT/'validators'/'validate_ket_data_s2b_item_semantic_projection.py')
assert SPEC and SPEC.loader
s2b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s2b)


def test_ket_data_s2b_s1_item_semantic_projection():
    r = s2b.validate(ROOT)
    assert r['status'] == s2b.STATUS
    assert r['s1_confirmed_item_count'] == 1452
    assert r['canonical_exam_projected_count'] == 1360
    assert r['practice_deferred_count'] == 92
    assert r['task_profile_count'] == 14
    assert r['reading_projected_count'] == 480
    assert r['writing_projected_count'] == 32
    assert r['listening_projected_count'] == 400
    assert r['speaking_projected_count'] == 448
    assert r['missing_task_profile_count'] == 0
    assert r['missing_semantic_dimension_count'] == 0
    assert r['generic_mcq_label_count'] == 0
    assert r['item_identity_mutation_count'] == 0
    assert r['broken_source_lineage_count'] == 0
    assert r['broken_media_lineage_count'] == 0
    assert r['canonical_exam_projection'] == 'PASS'
    assert r['practice_projection'] == 'DEFERRED_REQUIRES_MULTIMODAL_SEMANTIC_ADMISSION'
    assert r['s1_identity_preserved'] is True
    assert r['s2a_taxonomy_preserved'] is True
    assert r['s3_started'] is False
