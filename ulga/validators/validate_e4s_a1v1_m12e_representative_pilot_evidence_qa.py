#!/usr/bin/env python3
"""Independently validate M12E representative evidence QA outputs."""
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

from ulga.builders import build_e4s_a1v1_m12e_representative_pilot_evidence_qa as builder  # noqa: E402

DEFAULT_VALIDATION_PATH = builder.DEFAULT_OUTPUT_ROOT / "representative_evidence_qa_validation.json"


def validate(
    input_root: Path,
    qa_root: Path,
    representative_root: Path,
    output_root: Path,
    *,
    expected_origin: str,
) -> dict[str, Any]:
    errors: list[str] = []
    report: dict[str, Any] = {}
    rebuild_root: Path | None = None
    try:
        target = builder._safe_root(output_root)
        report = builder.read_json(target / "representative_evidence_qa_safe_report.json")
        queue_file = builder.read_json(target / "coverage_expansion_queue.json")
        builder._assert_schema(report)
        builder._safe_scan(report)
        if queue_file != report.get("coverage_expansion_queue"):
            errors.append("coverage_queue_file_report_drift")

        representative = builder._safe_root(representative_root)
        m12d_report = builder.read_json(representative / "representative_pilot_expansion_safe_report.json")
        ledger = builder.read_json(representative / "cumulative_progress_ledger.private.json")
        query = builder.read_json(representative / "cumulative_progress_query_index.json")
        manifest = builder.read_json(representative / "representative_batch_manifest.private.json")

        if report.get("evidence_origin") != expected_origin:
            errors.append("evidence_origin_drift")
        if report.get("representative_batch", {}).get("batch_attempt_count") != 8:
            errors.append("representative_batch_not_8")
        if report.get("representative_batch", {}).get("complete") is not True:
            errors.append("representative_batch_not_complete")
        if report.get("representative_batch", {}).get("skill_counts") != {"reading": 4, "writing": 4}:
            errors.append("representative_skill_distribution_drift")
        if report.get("representative_batch", {}).get("role_counts") != {"practice": 4, "assessment": 4}:
            errors.append("representative_role_distribution_drift")
        if report.get("representative_batch", {}).get("batch_row_count") != manifest.get("batch_selection", {}).get("canonical_egp_row_count"):
            errors.append("representative_batch_row_count_drift")

        entries = list(ledger.get("entries", []))
        attempted_ids = {str(row.get("item_id")) for row in entries}
        attempted_units = {str(row.get("grammar_unit_id")) for row in entries}
        attempted_rows = {str(row_id) for row in entries for row_id in row.get("canonical_egp_row_ids", [])}
        summary = report.get("evidence_summary", {})
        if summary.get("attempt_count") != len(entries):
            errors.append("evidence_attempt_count_drift")
        if summary.get("attempted_unit_count") != len(attempted_units):
            errors.append("evidence_unit_count_drift")
        if summary.get("attempted_row_count") != len(attempted_rows):
            errors.append("evidence_row_count_drift")
        if m12d_report.get("cumulative_attempt_count") != len(entries):
            errors.append("m12d_report_ledger_attempt_drift")
        if report.get("coverage_progress", {}).get("delta", {}).get("items") != 8:
            errors.append("coverage_item_delta_not_8")
        current = report.get("coverage_progress", {}).get("current", {})
        remaining = report.get("coverage_progress", {}).get("remaining", {})
        if current.get("items", 0) + remaining.get("items", 0) != 184:
            errors.append("coverage_item_partition_drift")
        if current.get("units", 0) + remaining.get("units", 0) != 23:
            errors.append("coverage_unit_partition_drift")
        if current.get("rows", 0) + remaining.get("rows", 0) != 107:
            errors.append("coverage_row_partition_drift")
        if report.get("coverage_progress", {}).get("representative_pilot_completed") is not True:
            errors.append("representative_pilot_completion_missing")

        queue = report.get("coverage_expansion_queue", {})
        queue_items = list(queue.get("items", []))
        queue_ids = [str(row.get("item_id")) for row in queue_items]
        if queue.get("candidate_count") != len(queue_items):
            errors.append("queue_count_drift")
        if len(queue_ids) != len(set(queue_ids)):
            errors.append("queue_duplicate_item")
        if any(item_id in attempted_ids for item_id in queue_ids):
            errors.append("queue_contains_attempted_item")
        if any(item_id.startswith(builder.DEFERRED_GRAMMAR_ID) for item_id in queue_ids):
            errors.append("queue_contains_deferred_will")
        query_by_id = {str(row.get("item_id")): row for row in query.get("items", [])}
        for row in queue_items:
            item_id = str(row.get("item_id"))
            source_row = query_by_id.get(item_id)
            if source_row is None:
                errors.append(f"queue_unknown_item:{item_id}")
                continue
            for field in ("grammar_unit_id", "canonical_egp_row_ids", "internal_stage", "skill", "item_role", "evidence_dimension", "task_type"):
                if row.get(field) != source_row.get(field):
                    errors.append(f"queue_source_drift:{item_id}:{field}")
        coverage_complete = report.get("coverage_progress", {}).get("coverage_complete") is True
        if coverage_complete and queue_items:
            errors.append("coverage_complete_queue_not_empty")
        if not coverage_complete and len(queue_items) != 8:
            errors.append("coverage_incomplete_queue_not_8")

        quality = report.get("quality_gate", {})
        pending = int(summary.get("pending_human_review_count", 0))
        remediation = int(summary.get("auto_fail_count", 0)) + int(summary.get("outcome_counts", {}).get("HUMAN_REJECT", 0))
        if quality.get("human_review_required") != (pending > 0):
            errors.append("human_review_gate_drift")
        if quality.get("remediation_required") != (remediation > 0):
            errors.append("remediation_gate_drift")
        if pending > 0:
            if report.get("stop_reason") != "HUMAN_REVIEW_DECISIONS_REQUIRED":
                errors.append("pending_review_stop_reason_drift")
        elif report.get("stop_reason") != "NONE":
            errors.append("nonpending_stop_reason_drift")

        boundaries = report.get("claim_boundaries", {})
        for key in (
            "private_responses_included", "learner_identity_included",
            "test_fixture_counted_as_real_evidence", "canonical_authority_write",
            "canonical_egp_mapping_changed", "public_delivery",
            "production_runtime_enabled", "a2_content_promoted",
            "audio_or_recording_processed", "learner_mastery_claimed",
            "retention_confirmed",
        ):
            if boundaries.get(key) is not False:
                errors.append(f"claim_boundary_drift:{key}")

        rebuild_root = target.parent / f"m12e-rebuild-{uuid.uuid4().hex}"
        rebuilt = builder.build_qa(
            input_root,
            qa_root,
            representative_root,
            rebuild_root,
            expected_origin=expected_origin,
        )
        if rebuilt != report:
            errors.append("representative_evidence_qa_not_reproducible")
        if builder.read_json(rebuild_root / "coverage_expansion_queue.json") != queue_file:
            errors.append("coverage_expansion_queue_not_reproducible")
    except (
        builder.RepresentativeEvidenceQAError,
        builder.m12.PilotCaptureError,
        builder.m12c.EvidenceQAError,
        builder.m12d.RepresentativePilotError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    finally:
        if rebuild_root is not None:
            shutil.rmtree(rebuild_root, ignore_errors=True)

    expected_status = builder.REAL_STATUS if expected_origin == "REAL_LEARNER" else builder.TEST_STATUS
    return {
        "task_id": builder.TASK_ID,
        "validation_status": expected_status if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "evidence_origin": report.get("evidence_origin"),
        "attempt_count": report.get("evidence_summary", {}).get("attempt_count", 0),
        "attempted_unit_count": report.get("evidence_summary", {}).get("attempted_unit_count", 0),
        "attempted_row_count": report.get("evidence_summary", {}).get("attempted_row_count", 0),
        "auto_pass_count": report.get("evidence_summary", {}).get("auto_pass_count", 0),
        "auto_fail_count": report.get("evidence_summary", {}).get("auto_fail_count", 0),
        "pending_human_review_count": report.get("evidence_summary", {}).get("pending_human_review_count", 0),
        "iteration_candidate_count": report.get("coverage_expansion_queue", {}).get("candidate_count", 0),
        "representative_pilot_completed": report.get("coverage_progress", {}).get("representative_pilot_completed", False),
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "public_delivery": False,
        "a2_content_promoted": False,
        "audio_or_recording_processed": False,
        "stop_reason": report.get("stop_reason", "VALIDATION_FAILURE") if not errors else "VALIDATION_FAILURE",
        "next_short_step": report.get("next_short_step") if not errors else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=builder.DEFAULT_INPUT_ROOT)
    parser.add_argument("--qa-root", type=Path, default=builder.DEFAULT_QA_ROOT)
    parser.add_argument("--representative-root", type=Path, default=builder.DEFAULT_REPRESENTATIVE_ROOT)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--expected-origin", choices=["REAL_LEARNER", "TEST_FIXTURE"], required=True)
    parser.add_argument("--validation-report", type=Path, default=DEFAULT_VALIDATION_PATH)
    args = parser.parse_args(argv)
    result = validate(
        args.input_root,
        args.qa_root,
        args.representative_root,
        args.output_root,
        expected_origin=args.expected_origin,
    )
    builder.write_json_atomic(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
