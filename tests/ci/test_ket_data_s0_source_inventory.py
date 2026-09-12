import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location("ket_s0",ROOT/"validators"/"validate_ket_data_s0_source_inventory.py")
assert SPEC and SPEC.loader
target=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(target)

def test_ket_data_s0_closeout_rules():
    r=target.validate()
    assert r["status"]==target.STATUS
    assert r["source_object_count"]==34
    assert r["authority_class_counts"]=={
        "PUBLISHER_COURSE_MATERIAL":8,"REFERENCE_ANSWER_MATERIAL":2,"THIRD_PARTY_PREP":10,
        "UNVERIFIED_OFFICIAL_EXAM_CANDIDATE":4,"UNVERIFIED_SCORING_REFERENCE_CANDIDATE":10}
    assert r["duplicate_candidate_group_count"]==5
    assert r["duplicate_candidate_object_count"]==10
    assert r["verified_official_exam_count"]==0
    assert r["page_semantic_scan_started"] is False
    assert r["image_extraction_started"] is False
    assert r["unit04_modified"] is False
    assert r["raw_asset_publication_allowed"] is False
