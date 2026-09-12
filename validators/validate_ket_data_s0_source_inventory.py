from __future__ import annotations
import json, re
from collections import Counter
from pathlib import Path

TASK_ID = "KET_Data_S0R1_ExactKET_S0ContractFullFix"
STATUS = "PASS_KET_DATA_S0R1_EXACT_KET_S0_CONTRACT"
EXPECTED_COUNT = 34
COLS = [
    "source_id", "drive_file_id", "file_name", "source_family", "exam_family",
    "variant", "year", "media_type", "authority_class", "allowed_use", "scan_status",
]
AUTHORITY_CONTRACT = [
    "VERIFIED_OFFICIAL_EXAM", "OFFICIAL_SCORING_REFERENCE",
    "PUBLISHER_COURSE_MATERIAL", "TEACHER_RESOURCE", "THIRD_PARTY_PREP",
    "REFERENCE_ANSWER_MATERIAL", "UNVERIFIED",
]
EXPECTED_AUTHORITY_COUNTS = {
    "PUBLISHER_COURSE_MATERIAL": 6,
    "REFERENCE_ANSWER_MATERIAL": 2,
    "TEACHER_RESOURCE": 2,
    "THIRD_PARTY_PREP": 10,
    "UNVERIFIED": 14,
}
EXPECTED_FAMILY_COUNTS = {
    "OFFICIAL_EXAM": 4,
    "OFFICIAL_SCORING_REFERENCE": 10,
    "PUBLISHER_COURSE_MATERIAL": 6,
    "REFERENCE_ANSWER_MATERIAL": 2,
    "TEACHER_RESOURCE": 2,
    "THIRD_PARTY_PREP": 10,
}

class KETDataS0ValidationError(ValueError):
    pass


def _path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "ket" / "ket_source_manifest.json"


def validate(path=None):
    with Path(path or _path()).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    errors = []
    if payload.get("schema") != "ket.data.source_manifest.s0.v2":
        errors.append("SCHEMA_DRIFT")
    if payload.get("task_id") != TASK_ID:
        errors.append("TASK_ID_DRIFT")
    if payload.get("contract_source") != "KET_S0.txt":
        errors.append("CONTRACT_SOURCE_DRIFT")
    if payload.get("source_columns") != COLS:
        errors.append("SOURCE_COLUMNS_NOT_EXACT_KET_S0")
    if payload.get("authority_class_contract") != AUTHORITY_CONTRACT:
        errors.append("AUTHORITY_CLASS_CONTRACT_DRIFT")

    rows = payload.get("sources") or []
    if len(rows) != EXPECTED_COUNT:
        errors.append(f"SOURCE_COUNT:{len(rows)}")

    source_ids, drive_ids = [], []
    authority_counts, family_counts = Counter(), Counter()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, list) or len(row) != len(COLS):
            errors.append(f"ROW_SHAPE:{index}")
            continue
        record = dict(zip(COLS, row))
        sid = record["source_id"]
        source_ids.append(sid)
        drive_ids.append(record["drive_file_id"])
        if sid != f"KET_SRC_{index:06d}" or not re.fullmatch(r"KET_SRC_\d{6}", sid or ""):
            errors.append(f"SOURCE_ID:{index}")
        for required in ("drive_file_id", "file_name", "source_family", "exam_family", "media_type", "authority_class", "scan_status"):
            if record.get(required) in (None, ""):
                errors.append(f"REQUIRED_EMPTY:{sid}:{required}")
        if record["exam_family"] != "A2_KEY":
            errors.append(f"EXAM_FAMILY_DRIFT:{sid}")
        if record["media_type"] not in {"PDF", "DOCX"}:
            errors.append(f"MEDIA_TYPE_INVALID:{sid}")
        if record["authority_class"] not in AUTHORITY_CONTRACT:
            errors.append(f"AUTHORITY_OUTSIDE_KET_S0:{sid}")
        if not isinstance(record["allowed_use"], list) or not record["allowed_use"]:
            errors.append(f"ALLOWED_USE_EMPTY:{sid}")
        if record["scan_status"] != "PENDING":
            errors.append(f"SCAN_STATUS_NOT_PENDING:{sid}")
        if record["source_family"] in {"OFFICIAL_EXAM", "OFFICIAL_SCORING_REFERENCE"} and record["authority_class"] != "UNVERIFIED":
            errors.append(f"UNPROVEN_AUTHORITY_PROMOTED:{sid}")
        authority_counts[record["authority_class"]] += 1
        family_counts[record["source_family"]] += 1

    if len(source_ids) != len(set(source_ids)):
        errors.append("SOURCE_ID_NOT_UNIQUE")
    if len(drive_ids) != len(set(drive_ids)):
        errors.append("DRIVE_FILE_ID_NOT_UNIQUE")
    if dict(sorted(authority_counts.items())) != EXPECTED_AUTHORITY_COUNTS:
        errors.append("AUTHORITY_COUNTS_DRIFT")
    if dict(sorted(family_counts.items())) != EXPECTED_FAMILY_COUNTS:
        errors.append("SOURCE_FAMILY_COUNTS_DRIFT")
    if authority_counts.get("VERIFIED_OFFICIAL_EXAM", 0) != 0:
        errors.append("PREMATURE_VERIFIED_OFFICIAL_EXAM")
    if authority_counts.get("OFFICIAL_SCORING_REFERENCE", 0) != 0:
        errors.append("PREMATURE_OFFICIAL_SCORING_REFERENCE")

    if errors:
        raise KETDataS0ValidationError("\n".join(errors))
    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "contract_source": "KET_S0.txt",
        "source_object_count": EXPECTED_COUNT,
        "required_field_count": len(COLS),
        "required_source_fields": COLS,
        "authority_class_contract": AUTHORITY_CONTRACT,
        "authority_class_counts": dict(sorted(authority_counts.items())),
        "source_family_counts": dict(sorted(family_counts.items())),
        "all_scan_status_pending": True,
    }

if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
