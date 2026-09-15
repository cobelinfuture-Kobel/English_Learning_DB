from __future__ import annotations

import json
from collections import Counter

from builders.build_ket_data_s10_coverage_matrix import (
    EXPECTED_ROW_IDS,
    EXPECTED_STATUS_COUNTS,
    PASS_STATUS,
    materialize,
)


def validate(root=None) -> dict:
    payload = materialize(root)
    rows = payload.get("coverage_rows") or []
    errors: list[str] = []

    if payload.get("status") != "MATERIALIZED":
        errors.append("STATUS")
    if [row.get("coverage_id") for row in rows] != EXPECTED_ROW_IDS:
        errors.append("ROW_ID_SEQUENCE")
    if len(rows) != 7:
        errors.append("ROW_COUNT")

    digests = [row.get("coverage_digest") for row in rows]
    if len(set(digests)) != len(digests) or any(
        not isinstance(value, str) or not value.startswith("sha256:")
        for value in digests
    ):
        errors.append("ROW_DIGESTS")

    status_counts = Counter(str(row.get("U04_current")) for row in rows)
    actual_status_counts = {
        key: status_counts.get(key, 0)
        for key in ("missing", "weak", "partial", "strong")
    }
    if actual_status_counts != EXPECTED_STATUS_COUNTS:
        errors.append("STATUS_COUNTS")

    for row in rows:
        refs = row.get("ket_reference") or []
        if not refs:
            errors.append(f"KET_REFERENCE_EMPTY:{row.get('coverage_id')}")
            continue
        if any(ref.get("NATIVE_LEVEL") != "A2_KET" for ref in refs):
            errors.append(f"NATIVE_LEVEL:{row.get('coverage_id')}")
        if any(ref.get("ADAPTABLE_DOWN") is not True for ref in refs):
            errors.append(f"ADAPTABLE_DOWN:{row.get('coverage_id')}")
        if any(ref.get("MIN_ADAPTED_LEVEL") != "A1" for ref in refs):
            errors.append(f"MIN_ADAPTED_LEVEL:{row.get('coverage_id')}")
        evidence = row.get("u04_evidence") or {}
        if evidence.get("supports_status") != row.get("U04_current"):
            errors.append(f"U04_EVIDENCE_STATUS:{row.get('coverage_id')}")

    summary = payload.get("summary") or {}
    if summary.get("coverage_row_count") != 7:
        errors.append("SUMMARY_ROW_COUNT")
    if summary.get("status_counts") != EXPECTED_STATUS_COUNTS:
        errors.append("SUMMARY_STATUS_COUNTS")
    for key in (
        "learner_facing_task_count",
        "question_bank_item_count",
        "new_content_count",
        "a2_or_a2_plus_unlock_count",
        "live_model_call_count",
    ):
        if summary.get(key) != 0:
            errors.append(f"BOUNDARY:{key}")

    governance = payload.get("governance") or {}
    for key in (
        "learner_facing_generation_allowed",
        "question_bank_generation_allowed",
        "new_image_generation_allowed",
        "new_language_asset_generation_allowed",
        "a2_or_a2_plus_unlock_allowed",
        "live_model_call_in_ci",
        "new_summary_document_allowed",
    ):
        if governance.get(key) is not False:
            errors.append(f"GOVERNANCE:{key}")

    result = {
        "validation_status": PASS_STATUS if not errors else "FAIL_KET_DATA_S10_COVERAGE_MATRIX",
        "error_count": len(errors),
        "errors": errors,
        "coverage_row_count": len(rows),
        "status_counts": actual_status_counts,
        "unique_ket_reference_profile_count": summary.get("unique_ket_reference_profile_count"),
        "u04_evidence_module_count": summary.get("u04_evidence_module_count"),
        "matrix_digest": payload.get("matrix_digest"),
    }
    if errors:
        raise ValueError(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
