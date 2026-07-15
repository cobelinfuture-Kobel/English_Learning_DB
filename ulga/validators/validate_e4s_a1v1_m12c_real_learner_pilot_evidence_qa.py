#!/usr/bin/env python3
"""Independently validate M12C evidence QA and deterministic iteration output."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m12c_real_learner_pilot_evidence_qa as builder  # noqa: E402


def validate(input_root: Path, output_root: Path, *, expected_origin: str) -> dict[str, Any]:
    errors: list[str] = []
    report: dict[str, Any] = {}
    rebuild_root: Path | None = None
    try:
        report = builder.read_json(output_root / "real_evidence_qa_safe_report.json")
        builder._assert_schema(report)
        builder._safe_scan(report)
        if report.get("evidence_origin") != expected_origin:
            errors.append("evidence_origin_drift")
        expected_status = builder.REAL_STATUS if expected_origin == "REAL_LEARNER" else builder.TEST_STATUS
        if report.get("validation_status") != expected_status:
            errors.append("validation_status_drift")
        summary = report.get("evidence_summary", {})
        coverage = report.get("coverage_progress", {})
        queue = report.get("iteration_queue", {})
        if summary.get("attempt_count", 0) < 1:
            errors.append("attempt_count_not_positive")
        if coverage.get("selectable_items") != 184 or coverage.get("private_ready_units") != 23 or coverage.get("private_ready_rows") != 107:
            errors.append("coverage_contract_drift")
        if coverage.get("pilot_completed") is not False:
            errors.append("pilot_completion_false_claim")
        if queue.get("candidate_count") != len(queue.get("items", [])):
            errors.append("iteration_candidate_count_drift")
        if len(queue.get("items", [])) > 8:
            errors.append("iteration_queue_too_large")
        item_ids = [row.get("item_id") for row in queue.get("items", [])]
        if len(set(item_ids)) != len(item_ids):
            errors.append("iteration_queue_duplicate_items")
        if any(row.get("grammar_unit_id") == builder.m12.DEFERRED_GRAMMAR_ID for row in queue.get("items", [])):
            errors.append("deferred_will_iteration_leak")
        boundaries = report.get("claim_boundaries", {})
        for key in (
            "private_responses_included",
            "learner_identity_included",
            "canonical_authority_write",
            "canonical_egp_mapping_changed",
            "public_delivery",
            "production_runtime_enabled",
            "a2_content_promoted",
            "audio_or_recording_processed",
            "learner_mastery_claimed",
            "retention_confirmed",
            "real_learner_pilot_completed",
            "test_fixture_counted_as_real_evidence",
        ):
            if boundaries.get(key) is not False:
                errors.append(f"claim_boundary_drift:{key}")
        if summary.get("pending_human_review_count", 0) > 0:
            if report.get("stop_reason") != "HUMAN_REVIEW_DECISIONS_REQUIRED":
                errors.append("pending_review_stop_reason_drift")
            if report.get("next_short_step") != "E4S-A1V1-M12C1_HumanReviewDecisionMaterialization":
                errors.append("pending_review_next_step_drift")
        else:
            if report.get("stop_reason") != "NONE":
                errors.append("nonpending_stop_reason_drift")
            if report.get("next_short_step") != "E4S-A1V1-M12D_RepresentativePilotExpansion":
                errors.append("nonpending_next_step_drift")

        rebuild_root = output_root.parent / f"m12c-validation-{uuid.uuid4().hex}"
        rebuilt = builder.build_qa(input_root, rebuild_root, expected_origin=expected_origin)
        if rebuilt != report:
            errors.append("qa_report_not_reproducible")
    except (builder.EvidenceQAError, OSError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    finally:
        if rebuild_root is not None:
            shutil.rmtree(rebuild_root, ignore_errors=True)

    return {
        "task_id": builder.TASK_ID,
        "validation_status": report.get("validation_status") if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "evidence_origin": report.get("evidence_origin"),
        "attempt_count": report.get("evidence_summary", {}).get("attempt_count", 0),
        "auto_pass_count": report.get("evidence_summary", {}).get("auto_pass_count", 0),
        "auto_fail_count": report.get("evidence_summary", {}).get("auto_fail_count", 0),
        "pending_human_review_count": report.get("evidence_summary", {}).get("pending_human_review_count", 0),
        "iteration_candidate_count": report.get("iteration_queue", {}).get("candidate_count", 0),
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "public_delivery": False,
        "a2_content_promoted": False,
        "audio_or_recording_processed": False,
        "stop_reason": report.get("stop_reason") if not errors else "VALIDATION_FAILURE",
        "next_short_step": report.get("next_short_step") if not errors else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-origin", choices=["REAL_LEARNER", "TEST_FIXTURE"], required=True)
    parser.add_argument("--validation-report", type=Path, required=True)
    args = parser.parse_args(argv)
    result = validate(args.input_root, args.output_root, expected_origin=args.expected_origin)
    builder.write_json_atomic(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
