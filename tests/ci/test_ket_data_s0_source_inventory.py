import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "ket_s0",
    ROOT / "validators" / "validate_ket_data_s0_source_inventory.py",
)
assert SPEC and SPEC.loader
target = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(target)


def test_ket_data_s0r1_exact_ket_s0_contract():
    report = target.validate()
    assert report["status"] == target.STATUS
    assert report["contract_source"] == "KET_S0.txt"
    assert report["source_object_count"] == 34
    assert report["required_field_count"] == 11
    assert report["required_source_fields"] == [
        "source_id", "drive_file_id", "file_name", "source_family", "exam_family",
        "variant", "year", "media_type", "authority_class", "allowed_use", "scan_status",
    ]
    assert report["authority_class_contract"] == [
        "VERIFIED_OFFICIAL_EXAM", "OFFICIAL_SCORING_REFERENCE",
        "PUBLISHER_COURSE_MATERIAL", "TEACHER_RESOURCE", "THIRD_PARTY_PREP",
        "REFERENCE_ANSWER_MATERIAL", "UNVERIFIED",
    ]
    assert report["authority_class_counts"] == {
        "PUBLISHER_COURSE_MATERIAL": 6,
        "REFERENCE_ANSWER_MATERIAL": 2,
        "TEACHER_RESOURCE": 2,
        "THIRD_PARTY_PREP": 10,
        "UNVERIFIED": 14,
    }
    assert report["source_family_counts"] == {
        "OFFICIAL_EXAM": 4,
        "OFFICIAL_SCORING_REFERENCE": 10,
        "PUBLISHER_COURSE_MATERIAL": 6,
        "REFERENCE_ANSWER_MATERIAL": 2,
        "TEACHER_RESOURCE": 2,
        "THIRD_PARTY_PREP": 10,
    }
    assert report["all_scan_status_pending"] is True
