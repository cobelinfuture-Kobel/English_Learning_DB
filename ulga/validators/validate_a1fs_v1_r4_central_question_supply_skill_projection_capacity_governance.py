#!/usr/bin/env python3
"""Independent validator for R4 Approved PracticeBank and safe supply report."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4


def _safe_scan(value: Any, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in r4.PRIVATE_KEYS:
                errors.append(f"safe_report_private_field:{key}")
            _safe_scan(child, errors)
    elif isinstance(value, list):
        for child in value:
            _safe_scan(child, errors)
    elif isinstance(value, str):
        if Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":/", ":\\"}):
            errors.append("safe_report_absolute_path")


def validate(
    *, ontology_path: Path, coverage_path: Path, candidates_path: Path,
    policies_path: Path, bank_path: Path, report_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        bank = r4.read_json(bank_path, "bank")
        report = r4.read_json(report_path, "report")
        expected_bank, expected_report = r4.build(
            ontology_path=ontology_path,
            coverage_path=coverage_path,
            candidates_path=candidates_path,
            policies_path=policies_path,
        )
    except (OSError, json.JSONDecodeError, r4.QuestionSupplyError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"rebuild_failed:{exc}"]}
    if bank != expected_bank:
        errors.append("bank_rebuild_drift")
    if report != expected_report:
        errors.append("report_rebuild_drift")
    bank_core = {key: value for key, value in bank.items() if key != "bank_sha256"}
    report_core = {key: value for key, value in report.items() if key != "report_sha256"}
    if bank.get("bank_sha256") != r4.digest(bank_core):
        errors.append("bank_digest_invalid")
    if report.get("report_sha256") != r4.digest(report_core):
        errors.append("report_digest_invalid")
    if bank.get("task_id") != r4.TASK_ID or bank.get("schema_version") != r4.BANK_SCHEMA_VERSION:
        errors.append("bank_identity_invalid")
    if report.get("task_id") != r4.TASK_ID or report.get("schema_version") != r4.SCHEMA_VERSION:
        errors.append("report_identity_invalid")
    if bank.get("validation_status") != r4.STATUS or report.get("validation_status") != r4.STATUS:
        errors.append("validation_status_invalid")
    if bank.get("private_local_only") is not True:
        errors.append("bank_private_boundary_broken")
    items = bank.get("items", [])
    item_ids = [row.get("item_id") for row in items]
    if bank.get("item_count") != len(items) or len(item_ids) != len(set(item_ids)):
        errors.append("bank_item_denominator_invalid")
    fingerprints: dict[str, set[str]] = {}
    for row in items:
        if row.get("admission", {}).get("status") != "APPROVED":
            errors.append(f"unapproved_item_in_bank:{row.get('item_id')}")
        cell_id = str(row.get("breadth_cell_id"))
        bucket = fingerprints.setdefault(cell_id, set())
        fingerprint = str(row.get("stimulus_fingerprint"))
        if fingerprint in bucket:
            errors.append(f"duplicate_bank_stimulus:{cell_id}:{fingerprint}")
        bucket.add(fingerprint)
        if row.get("candidate_sha256") != r4.candidate_digest(row):
            errors.append(f"candidate_digest_drift:{row.get('item_id')}")
        if row.get("authority_review", {}).get("candidate_sha256") != row.get("candidate_sha256"):
            errors.append(f"authority_hash_binding_invalid:{row.get('item_id')}")
    selection = bank.get("selection_contract", {})
    for key in (
        "local_free_generation_enabled", "gpt_direct_item_admission_enabled",
        "qwen_direct_item_admission_enabled",
    ):
        if selection.get(key) is not False:
            errors.append(f"selection_boundary_broken:{key}")
    if selection.get("formal_item_requires_admission_approved") is not True:
        errors.append("formal_admission_gate_missing")
    counts = report.get("counts", {})
    decisions = report.get("admission_decisions", [])
    cells = report.get("cell_supply", [])
    if counts.get("candidate_count") != len(decisions):
        errors.append("candidate_count_invalid")
    if counts.get("approved_item_count") != len(items):
        errors.append("approved_item_count_invalid")
    if counts.get("rejected_or_pending_count") != len(decisions) - len(items):
        errors.append("rejected_pending_count_invalid")
    if counts.get("supply_status_counts") != dict(sorted(Counter(row.get("supply_status") for row in cells).items())):
        errors.append("supply_status_counts_invalid")
    if counts.get("admission_status_counts") != dict(sorted(Counter(row.get("status") for row in decisions).items())):
        errors.append("admission_status_counts_invalid")
    if any(row.get("status") not in r4.ADMISSION_STATUS for row in decisions):
        errors.append("unknown_admission_status")
    if any(row.get("supply_status") not in r4.CELL_SUPPLY_STATUS for row in cells):
        errors.append("unknown_cell_supply_status")
    for cell in cells:
        if cell.get("supply_status") == "READY_FOR_LOCAL_SELECTION":
            if not cell.get("capacity_policy_present"):
                errors.append(f"ready_without_policy:{cell.get('breadth_cell_id')}")
            if cell.get("skill_projection", {}).get("missing"):
                errors.append(f"ready_with_skill_gap:{cell.get('breadth_cell_id')}")
            if any(not row.get("capacity_pass") for row in cell.get("purpose_capacity", {}).values()):
                errors.append(f"ready_with_capacity_gap:{cell.get('breadth_cell_id')}")
        if cell.get("supply_status") == "CAPACITY_INSUFFICIENT":
            has_shortage = bool(cell.get("skill_projection", {}).get("missing")) or any(
                not row.get("capacity_pass") for row in cell.get("purpose_capacity", {}).values()
            )
            if not has_shortage:
                errors.append(f"capacity_insufficient_without_gap:{cell.get('breadth_cell_id')}")
    boundaries = report.get("claim_boundaries", {})
    for key in (
        "canonical_authority_modified", "m1_graph_modified", "r3_denominator_modified",
        "local_free_generation_enabled", "gpt_direct_admission_enabled", "qwen_required",
        "a2_content_admitted", "audio_files_required", "mastery_claimed",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"claim_boundary_broken:{key}")
    if report.get("next_short_step") != r4.NEXT_SHORT_STEP:
        errors.append("next_short_step_invalid")
    _safe_scan(report, errors)
    return {
        "validation_status": r4.STATUS if not errors else "FAIL_A1FS_V1_R4_QUESTION_SUPPLY_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "approved_item_count": len(items),
        "breadth_cell_count": len(cells),
        "next_short_step": r4.NEXT_SHORT_STEP if not errors else r4.TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ontology", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--policies", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = validate(
        ontology_path=args.ontology,
        coverage_path=args.coverage,
        candidates_path=args.candidates,
        policies_path=args.policies,
        bank_path=args.bank,
        report_path=args.report,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
