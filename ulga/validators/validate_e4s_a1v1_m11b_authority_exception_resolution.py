#!/usr/bin/env python3
"""Independently validate M11B Authority exception resolution outputs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m11b_authority_exception_resolution as builder  # noqa: E402

PASS_STATUS = "PASS_M11B_AUTHORITY_EXCEPTIONS_RESOLVED"
DEFAULT_VALIDATION_PATH = builder.DEFAULT_OUTPUT_ROOT / "authority_exception_resolution_validation.json"


def validate(output_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    matrix: dict[str, Any] = {}
    bank: dict[str, Any] = {}
    report: dict[str, Any] = {}
    try:
        root = builder._safe_output_root(output_root)
        matrix = builder.read_json(root / "authority_exception_resolution_matrix.private.json")
        bank = builder.read_json(root / "reviewed_private_learning_unit_bank.json")
        report = builder.read_json(root / "authority_exception_resolution_safe_report.json")
        builder._assert_schema("e4s_a1v1_m11b_exception_resolution_matrix.schema.json", matrix)
        builder._assert_schema("e4s_a1v1_m11b_reviewed_private_learning_unit_bank.schema.json", bank)
        builder._assert_schema("e4s_a1v1_m11b_exception_resolution_safe_report.schema.json", report)
        builder.m11a._safe_scan(report, name="m11b_exception_resolution_safe_report")

        expected_matrix, expected_bank, expected_report = builder.build_artifacts()
        if matrix != expected_matrix:
            errors.append("exception_resolution_matrix_not_reproducible")
        if bank != expected_bank:
            errors.append("reviewed_private_bank_not_reproducible")
        if report != expected_report:
            errors.append("exception_resolution_safe_report_not_reproducible")

        records = matrix.get("records", [])
        if len(records) != 4 or {row.get("grammar_unit_id") for row in records} != builder.EXPECTED_EXCEPTION_IDS:
            errors.append("exception_resolution_identity_not_4")
        for record in records:
            value = dict(record)
            claimed = value.pop("record_sha256", None)
            if claimed != builder.sha256_value(value):
                errors.append(f"exception_record_hash_drift:{record.get('grammar_unit_id')}")
            if not builder._metrics_pass(record.get("revalidation", {})):
                errors.append(f"exception_revalidation_not_pass:{record.get('grammar_unit_id')}")

        revised_ids = {
            row.get("grammar_unit_id")
            for row in records
            if row.get("resolution_status") == "RESOLVED_AUTO_PASS"
        }
        if revised_ids != {
            "GRAMMAR_COORDINATION_A1",
            "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1",
            "GRAMMAR_ADVERB_PHRASES_A1",
        }:
            errors.append("resolved_revision_unit_set_drift")
        deferred = [row for row in records if row.get("resolution_status") == "DEFERRED_CAMBRIDGE_CEILING"]
        if len(deferred) != 1 or deferred[0].get("grammar_unit_id") != "GRAMMAR_WILL_FUTURE_A1":
            errors.append("will_ceiling_defer_resolution_missing")
        if deferred and deferred[0].get("before_payload_sha256") != deferred[0].get("after_payload_sha256"):
            errors.append("will_deferred_payload_was_modified")

        reviewed_ids = {row.get("grammar_unit_id") for row in bank.get("reviewed_units", [])}
        if len(reviewed_ids) != 23 or "GRAMMAR_WILL_FUTURE_A1" in reviewed_ids:
            errors.append("private_ready_unit_set_not_23_without_will")
        if not revised_ids.issubset(reviewed_ids):
            errors.append("revised_units_missing_from_private_bank")
        deferred_units = bank.get("deferred_units", [])
        if len(deferred_units) != 1 or deferred_units[0].get("status") != "DEFERRED_CAMBRIDGE_FLYERS_A2_CEILING":
            errors.append("private_bank_ceiling_deferred_record_invalid")
        if deferred_units and deferred_units[0].get("canonical_egp_mapping_preserved") is not True:
            errors.append("canonical_egp_mapping_not_preserved")

        expected_reviewed_rows = {
            row_id
            for row in bank.get("reviewed_units", [])
            for row_id in row.get("canonical_egp_row_ids", [])
        }
        if bank.get("canonical_egp_row_count") != len(expected_reviewed_rows):
            errors.append("private_ready_row_accounting_drift")
        if report.get("private_ready_row_count") != len(expected_reviewed_rows):
            errors.append("safe_report_private_row_accounting_drift")
        if report.get("resolution_counts") != {
            "RESOLVED_AUTO_PASS": 3,
            "DEFERRED_CAMBRIDGE_CEILING": 1,
            "UNRESOLVED": 0,
        }:
            errors.append("resolution_count_drift")
        if report.get("unresolved_exception_count") != 0:
            errors.append("unresolved_exception_not_zero")
        if report.get("stop_reason") != "NONE":
            errors.append("m11b_stop_reason_not_none")
        if report.get("next_short_step") != builder.NEXT_SHORT_STEP:
            errors.append("m11b_next_short_step_drift")

        boundaries = report.get("claim_boundaries", {})
        for key in (
            "private_candidate_content_included",
            "raw_cambridge_source_included",
            "canonical_egp_mapping_changed",
            "canonical_authority_promotion",
            "public_delivery",
            "learner_mastery_claimed",
            "a2_content_promoted",
            "manual_checkbox_approval_required",
        ):
            if boundaries.get(key) is not False:
                errors.append(f"claim_boundary_drift:{key}")
    except (
        builder.AuthorityExceptionError,
        builder.m11a.AuthorityEvidenceError,
        builder.m11a.m11.CandidateReviewError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))

    return {
        "task_id": builder.TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "candidate_unit_count": report.get("candidate_unit_count", 0),
        "canonical_egp_row_count": report.get("canonical_egp_row_count", 0),
        "resolution_counts": report.get("resolution_counts", {}),
        "private_ready_unit_count": bank.get("reviewed_unit_count", 0),
        "private_ready_row_count": bank.get("canonical_egp_row_count", 0),
        "deferred_unit_count": bank.get("deferred_unit_count", 0),
        "unresolved_exception_count": report.get("unresolved_exception_count", 0),
        "canonical_egp_mapping_changed": False,
        "canonical_authority_promotion": False,
        "learner_mastery_claimed": False,
        "a2_content_promoted": False,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--validation-report", type=Path, default=DEFAULT_VALIDATION_PATH)
    args = parser.parse_args(argv)
    result = validate(args.output_root)
    builder.write_json_atomic(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
