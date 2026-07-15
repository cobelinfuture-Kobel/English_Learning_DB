#!/usr/bin/env python3
"""Independently validate M11A authority/Cambridge evidence outputs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m11a_authority_evidence_review as builder  # noqa: E402

PASS_STATUSES = {
    "PASS_AUTHORITY_EVIDENCE_REVIEW_COMPLETE",
    "PASS_WITH_AUTHORITY_EXCEPTIONS",
}
DEFAULT_VALIDATION_PATH = builder.DEFAULT_OUTPUT_ROOT / "authority_review_validation.json"


def validate(output_root: Path, source_root: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    matrix: dict[str, Any] = {}
    bank: dict[str, Any] = {}
    report: dict[str, Any] = {}
    try:
        root = builder._safe_output_root(output_root)
        matrix = builder.read_json(root / "authority_evidence_matrix.private.json")
        bank = builder.read_json(root / "reviewed_private_learning_unit_bank.json")
        report = builder.read_json(root / "authority_review_safe_report.json")
        builder._assert_schema("e4s_a1v1_m11a_authority_evidence_matrix.schema.json", matrix)
        builder._assert_schema("e4s_a1v1_m11a_reviewed_private_learning_unit_bank.schema.json", bank)
        builder._assert_schema("e4s_a1v1_m11a_authority_review_safe_report.schema.json", report)
        builder._safe_scan(report, name="m11a_authority_review_safe_report")

        expected_matrix, expected_bank, expected_report = builder.build_artifacts(source_root)
        if matrix != expected_matrix:
            errors.append("authority_evidence_matrix_not_reproducible")
        if bank != expected_bank:
            errors.append("reviewed_private_bank_not_reproducible")
        if report != expected_report:
            errors.append("authority_review_safe_report_not_reproducible")

        entries = matrix.get("entries", [])
        if len(entries) != 24 or len({row.get("grammar_unit_id") for row in entries}) != 24:
            errors.append("authority_evidence_unit_identity_not_24")
        rows = {value for entry in entries for value in entry.get("canonical_egp_row_ids", [])}
        if len(rows) != 109:
            errors.append("authority_evidence_row_union_not_109")
        if any(set(entry.get("criteria", {})) != set(builder.CRITERIA) for entry in entries):
            errors.append("authority_evidence_criteria_contract_drift")
        for entry in entries:
            record = dict(entry)
            claimed = record.pop("evidence_record_sha256", None)
            if claimed != builder.sha256_value(record):
                errors.append(f"evidence_record_hash_drift:{entry.get('grammar_unit_id')}")

        counts = {decision: 0 for decision in builder.DECISIONS}
        for entry in entries:
            decision = entry.get("automated_decision")
            if decision not in counts:
                errors.append(f"unknown_automated_decision:{decision}")
            else:
                counts[decision] += 1
        if counts != report.get("decision_counts"):
            errors.append("automated_decision_accounting_drift")
        if counts != {"AUTO_PASS": 20, "REVISION_REQUIRED": 3, "AUTHORITY_CONFLICT": 1, "SOURCE_EVIDENCE_MISSING": 0}:
            errors.append("automated_decision_distribution_unexpected")

        will_rows = [row for row in entries if row.get("grammar_unit_id") == "GRAMMAR_WILL_FUTURE_A1"]
        if len(will_rows) != 1 or will_rows[0].get("automated_decision") != "AUTHORITY_CONFLICT":
            errors.append("will_future_cambridge_ceiling_conflict_missing")
        if set(
            row.get("grammar_unit_id")
            for row in entries
            if row.get("automated_decision") == "REVISION_REQUIRED"
        ) != {
            "GRAMMAR_COORDINATION_A1",
            "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1",
            "GRAMMAR_ADVERB_PHRASES_A1",
        }:
            errors.append("revision_required_unit_set_drift")

        auto_pass_ids = {
            row.get("grammar_unit_id")
            for row in entries
            if row.get("automated_decision") == "AUTO_PASS"
        }
        bank_ids = {row.get("grammar_unit_id") for row in bank.get("reviewed_units", [])}
        if bank_ids != auto_pass_ids or bank.get("reviewed_unit_count") != 20:
            errors.append("auto_pass_private_bank_join_drift")
        if report.get("reviewed_unit_count") != bank.get("reviewed_unit_count"):
            errors.append("reviewed_unit_count_drift")
        if report.get("reviewed_row_count") != bank.get("canonical_egp_row_count"):
            errors.append("reviewed_row_count_drift")
        if report.get("stop_reason") != "NONE":
            errors.append("m11a_stop_reason_not_none")
        if report.get("next_short_step") != builder.NEXT_SHORT_STEP:
            errors.append("m11a_next_short_step_drift")

        boundaries = report.get("claim_boundaries", {})
        expected_false = (
            "private_candidate_content_included",
            "raw_cambridge_source_included",
            "manual_checkbox_approval_required",
            "canonical_authority_promotion",
            "public_delivery",
            "learner_mastery_claimed",
            "audio_or_recording_processed",
            "a2_content_promoted",
        )
        if any(boundaries.get(key) is not False for key in expected_false):
            errors.append("safe_report_claim_boundary_drift")
    except (
        builder.AuthorityEvidenceError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))

    status = report.get("validation_status") if not errors else "FAIL"
    return {
        "task_id": builder.TASK_ID,
        "validation_status": status,
        "error_count": len(errors),
        "errors": errors,
        "candidate_unit_count": matrix.get("unit_count", 0),
        "canonical_egp_row_count": matrix.get("canonical_egp_row_count", 0),
        "decision_counts": report.get("decision_counts", {}),
        "reviewed_unit_count": bank.get("reviewed_unit_count", 0),
        "reviewed_row_count": bank.get("canonical_egp_row_count", 0),
        "source_verification": matrix.get("source_verification"),
        "manual_checkbox_approval_required": False,
        "canonical_authority_promotion": False,
        "learner_mastery_claimed": False,
        "a2_content_promoted": False,
        "stop_reason": report.get("stop_reason", "VALIDATION_FAILURE") if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--cambridge-source-root", type=Path)
    parser.add_argument("--validation-report", type=Path, default=DEFAULT_VALIDATION_PATH)
    args = parser.parse_args(argv)
    result = validate(args.output_root, args.cambridge_source_root)
    builder.write_json_atomic(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
