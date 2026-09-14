import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('m03', ROOT/'validators'/'validate_ket_data_s1r2_m03_full_corpus_lineage.py')
assert SPEC and SPEC.loader
m03 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m03)


def test_s1r2_m03_exact_legacy629_rehydration_and_full_corpus_lineage():
    r = m03.validate(ROOT)
    assert r['status'] == m03.STATUS
    assert r['legacy_rehydrated_count'] == 629
    assert r['legacy_confirmed_reuse_count'] + r['legacy_deprecated_non_item_count'] == 629
    assert r['legacy_unresolved_count'] == 0
    assert r['m02_fixed_item_count'] == 85
    assert r['m03_planned_remaining_count'] == 1367
    assert r['m03_legacy_reused_count'] + r['m03_new_item_count'] == 1367
    assert r['total_confirmed_item_count'] == 1452
    assert r['duplicate_item_identity_count'] == 0
    assert r['ambiguous_legacy_match_count'] == 0
    assert r['broken_item_page_source_drive_lineage_count'] == 0
    assert r['new_image_identity_count'] == 0
    assert r['full_item_bearing_source_completeness'] == 'PASS_FOR_S0_TASK_MECHANIC_AND_PRACTICE_VARIATION_AUTHORIZED_SOURCES'
    assert r['s2_item_projection_readiness'] is False
    assert r['next_milestone'] == 'KET_Data_S1R2_M04_ExactCompletenessValidator_CI_Merge_Closeout'
