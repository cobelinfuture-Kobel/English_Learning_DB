#!/usr/bin/env python3
"""Independently validate M11 candidate review and private promotion outputs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m11_candidate_content_review as builder  # noqa: E402

PASS_STATUSES = {
    builder.PENDING_STATUS,
    builder.PARTIAL_STATUS,
    builder.COMPLETE_STATUS,
}
DEFAULT_VALIDATION_PATH = builder.DEFAULT_OUTPUT_ROOT / "candidate_unit_review_validation.json"


def validate(output_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        root = builder._safe_output_root(output_root)
        queue = builder.read_json(root / "candidate_unit_review_queue.private.json")
        decision_path = root / "candidate_unit_operator_decisions.private.json"
        if not decision_path.exists():
            decision_path = root / "candidate_unit_operator_decisions.template.json"
        decisions = builder.read_json(decision_path)
        bank = builder.read_json(root / "reviewed_private_learning_unit_bank.json")
        report = builder.read_json(root / "candidate_unit_review_safe_report.json")

        builder._assert_schema("e4s_a1v1_candidate_unit_review_queue.schema.json", queue)
        builder._assert_schema("e4s_a1v1_candidate_unit_operator_decisions.schema.json", decisions)
        builder._assert_schema("e4s_a1v1_reviewed_private_learning_unit_bank.schema.json", bank)
        builder._assert_schema("e4s_a1v1_candidate_unit_review_safe_report.schema.json", report)
        builder._safe_scan(report, name="candidate_review_safe_report")

        source, _ = builder._source_candidate()
        expected_queue = builder.build_review_queue(source)
        if expected_queue != queue:
            errors.append("review_queue_not_reproducible")
        expected_bank, expected_report = builder.build_review_artifacts(
            queue,
            decisions,
            source,
            report_mode=report.get("report_mode", "PREPARE_REVIEW"),
        )
        if expected_bank != bank:
            errors.append("reviewed_private_bank_not_reproducible")
        if expected_report != report:
            errors.append("candidate_review_safe_report_not_reproducible")

        entries = queue.get("review_entries", [])
        if len(entries) != 24 or len({entry.get("review_entry_id") for entry in entries}) != 24:
            errors.append("review_queue_identity_not_24")
        if len({entry.get("grammar_unit_id") for entry in entries}) != 24:
            errors.append("review_queue_unit_identity_not_24")
        rows = {
            row_id
            for entry in entries
            for row_id in entry.get("canonical_egp_row_ids", [])
        }
        if len(rows) != 109:
            errors.append("review_queue_row_coverage_not_109")
        if any(entry.get("automated_prechecks", {}).get("overall_status") == "BLOCK" for entry in entries):
            errors.append("review_queue_contains_blocked_candidate")

        decision_rows = decisions.get("decisions", [])
        if len(decision_rows) != 24 or len({row.get("review_entry_id") for row in decision_rows}) != 24:
            errors.append("decision_identity_not_24")
        if sum(report.get("decision_counts", {}).values()) != 24:
            errors.append("decision_accounting_not_24")
        if report.get("candidate_unit_count") != 24:
            errors.append("report_candidate_count_not_24")
        if report.get("canonical_egp_row_count") != 109:
            errors.append("report_row_count_not_109")
        if report.get("reviewed_unit_count") != bank.get("reviewed_unit_count"):
            errors.append("reviewed_unit_count_drift")
        if report.get("reviewed_row_count") != bank.get("canonical_egp_row_count"):
            errors.append("reviewed_row_count_drift")
        if report.get("validation_status") not in PASS_STATUSES:
            errors.append("report_status_invalid")
        pending = report.get("decision_counts", {}).get("PENDING", 0)
        expected_stop = "OPERATOR_CONTENT_REVIEW_DECISIONS_REQUIRED" if pending else "NONE"
        if report.get("stop_reason") != expected_stop:
            errors.append("stop_reason_drift")
        if report.get("next_resume_task") != builder.NEXT_RESUME_TASK:
            errors.append("next_resume_task_drift")

        boundaries = bank.get("claim_boundaries", {})
        expected_bank_boundaries = {
            "private_local_only": True,
            "must_not_be_committed": True,
            "canonical_authority_promotion": False,
            "public_delivery": False,
            "learner_mastery_claimed": False,
            "persistent_learner_state_write": False,
            "a2_a2plus_in_scope": False,
        }
        if boundaries != expected_bank_boundaries:
            errors.append("bank_claim_boundaries_drift")
        for row in bank.get("reviewed_units", []):
            if row.get("status") != "REVIEWED_PRIVATE_LEARNING_UNIT":
                errors.append(f"reviewed_unit_status_invalid:{row.get('grammar_unit_id')}")
            if row.get("private_learning_ready") is not True:
                errors.append(f"private_learning_ready_false:{row.get('grammar_unit_id')}")
            if row.get("mastery_trackable") is not False:
                errors.append(f"false_mastery_trackable:{row.get('grammar_unit_id')}")
            if row.get("canonical_authority_promotion") is not False:
                errors.append(f"false_authority_promotion:{row.get('grammar_unit_id')}")
    except (
        builder.CandidateReviewError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
        queue = {}
        decisions = {}
        bank = {}
        report = {}

    status = report.get("validation_status") if not errors else "FAIL"
    return {
        "task_id": builder.TASK_ID,
        "validation_status": status,
        "error_count": len(errors),
        "errors": errors,
        "candidate_unit_count": queue.get("review_entry_count", 0),
        "canonical_egp_row_count": report.get("canonical_egp_row_count", 0),
        "pending_decision_count": report.get("decision_counts", {}).get("PENDING", 0),
        "reviewed_unit_count": bank.get("reviewed_unit_count", 0),
        "reviewed_row_count": bank.get("canonical_egp_row_count", 0),
        "canonical_authority_promotion": False,
        "learner_mastery_claimed": False,
        "audio_or_recording_processed": False,
        "stop_reason": report.get("stop_reason", "VALIDATION_FAILURE"),
        "next_resume_task": builder.NEXT_RESUME_TASK,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--validation-report", type=Path, default=DEFAULT_VALIDATION_PATH)
    args = parser.parse_args(argv)
    result = validate(args.output_root)
    builder.write_json_atomic(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
