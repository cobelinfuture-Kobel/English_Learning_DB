#!/usr/bin/env python3
"""Independent reconstruction validator for the A1FS V1 R8 real-learner pilot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ulga.builders import build_a1fs_v1_r8_real_learner_breadth_transfer_repair_pilot as r8


def validate(
    report_path: Path, *, contract_path: Path, r5_package_path: Path,
    r5_safe_path: Path, r7_report_path: Path, attestation_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        report = r8.read_json(report_path, "report")
    except r8.RealLearnerPilotError as exc:
        return {"validation_status": "FAIL_A1FS_V1_R8_VALIDATION", "error_count": 1, "errors": [str(exc)]}
    if report.get("task_id") != r8.TASK_ID:
        errors.append("report_task_id_invalid")
    if report.get("schema_version") != r8.REPORT_SCHEMA_VERSION:
        errors.append("report_schema_version_invalid")
    if report.get("validation_status") != r8.STATUS:
        errors.append("report_status_invalid")
    try:
        r8.validate_digest(report, "report_sha256", "report_digest_invalid")
    except r8.RealLearnerPilotError as exc:
        errors.append(str(exc))
    if report.get("private_local_only") is not True:
        errors.append("report_privacy_invalid")
    if report.get("pilot_state") not in r8.PILOT_STATES:
        errors.append("pilot_state_invalid")
    counts = report.get("counts")
    cells = report.get("cells")
    if not isinstance(counts, dict) or not isinstance(cells, list):
        errors.append("report_counts_or_cells_invalid")
    else:
        if counts.get("complete_breadth_denominator_count") != len(cells):
            errors.append("report_denominator_mismatch")
        if counts.get("passed_required_cell_count") != sum(row.get("pilot_state") == "PASS" for row in cells if row.get("pilot_role") == "REAL_LEARNER_EVIDENCE_REQUIRED"):
            errors.append("report_passed_cell_count_mismatch")
        if counts.get("media_deferred_cell_count") != sum(row.get("pilot_role") == "MEDIA_DEFERRED_TO_R10" for row in cells):
            errors.append("report_media_deferred_count_mismatch")
    boundaries = report.get("claim_boundaries", {})
    forbidden_true = {
        "synthetic_fixture_accepted", "mastery_written", "retention_confirmed",
        "media_completion_claimed", "true_four_skill_release_claimed",
        "learner_release_approved", "a2_unlocked",
    }
    for key in forbidden_true:
        if boundaries.get(key) is not False:
            errors.append(f"claim_boundary_invalid:{key}")
    if boundaries.get("real_learner_pilot_claimed") is not (report.get("pilot_state") == "PASS"):
        errors.append("real_learner_claim_state_mismatch")
    expected_next = r8.NEXT_SHORT_STEP if report.get("pilot_state") == "PASS" else r8.EVIDENCE_COLLECTION_STEP
    if report.get("next_short_step") != expected_next:
        errors.append("next_short_step_invalid")
    try:
        rebuilt = r8.evaluate_pilot(
            contract_path=contract_path,
            r5_package_path=r5_package_path,
            r5_safe_path=r5_safe_path,
            r7_report_path=r7_report_path,
            attestation_path=attestation_path,
        )
    except r8.RealLearnerPilotError as exc:
        errors.append(f"reconstruction_failed:{exc}")
    else:
        if r8.canonical(rebuilt) != r8.canonical(report):
            errors.append("report_reconstruction_mismatch")
    gates = report.get("gates")
    if not isinstance(gates, dict) or any(value not in {True, False} for value in gates.values()):
        errors.append("gate_shape_invalid")
    elif report.get("pilot_state") == "PASS" and not all(gates.values()):
        errors.append("pass_report_gate_not_all_true")
    return {
        "validation_status": r8.STATUS if not errors else "FAIL_A1FS_V1_R8_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "pilot_state": report.get("pilot_state"),
        "real_learner_pilot_claimed": boundaries.get("real_learner_pilot_claimed", False),
        "next_short_step": report.get("next_short_step"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--r5-package", type=Path, required=True)
    parser.add_argument("--r5-safe", type=Path, required=True)
    parser.add_argument("--r7-report", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    args = parser.parse_args()
    result = validate(
        args.report, contract_path=args.contract, r5_package_path=args.r5_package,
        r5_safe_path=args.r5_safe, r7_report_path=args.r7_report,
        attestation_path=args.attestation,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
