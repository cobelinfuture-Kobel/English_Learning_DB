#!/usr/bin/env python3
"""Independently validate M12E1 human-review preparation/application."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m12e1_human_review_decision_materialization as builder  # noqa: E402

DEFAULT_VALIDATION_PATH = builder.DEFAULT_OUTPUT_ROOT / "human_review_materialization_validation.json"


def _attempt_without_review(attempt: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(attempt)
    value.pop("operator_review", None)
    return value


def validate(
    mode: str,
    input_root: Path,
    qa_root: Path,
    representative_root: Path,
    m12e_root: Path,
    output_root: Path,
    *,
    expected_origin: str,
) -> dict[str, Any]:
    errors: list[str] = []
    report: dict[str, Any] = {}
    queue: dict[str, Any] = {}
    rebuild_root: Path | None = None
    try:
        if mode not in {"prepare", "apply-decisions"}:
            raise builder.HumanReviewMaterializationError(
                f"validation_mode_invalid:{mode}"
            )
        root = builder._safe_root(output_root)
        queue = builder.read_json(root / "human_review_queue.private.json")
        report = builder.read_json(
            root / "human_review_materialization_safe_report.json"
        )
        builder._assert_schema(
            "e4s_a1v1_m12e1_human_review_queue.schema.json", queue
        )
        builder._assert_schema(
            "e4s_a1v1_m12e1_human_review_safe_report.schema.json", report
        )
        builder._safe_scan(report, name="m12e1_validation_safe_report")
        source = builder._load_sources(
            input_root,
            representative_root,
            m12e_root,
            expected_origin=expected_origin,
        )
        expected_queue = builder._build_queue(
            source, expected_origin=expected_origin
        )
        if queue != expected_queue:
            errors.append("human_review_queue_not_reproducible")
        if queue.get("pending_item_count") != len(queue.get("items", [])):
            errors.append("queue_pending_count_drift")
        ids = [str(row.get("item_id")) for row in queue.get("items", [])]
        if len(ids) != len(set(ids)):
            errors.append("queue_duplicate_item")
        for row in queue.get("items", []):
            if row.get("private_scoring_contract", {}).get("scoring_mode") != "FEATURE_RUBRIC":
                errors.append(f"queue_non_rubric_item:{row.get('item_id')}")
            if row.get("current_operator_review", {}).get("decision") != "PENDING":
                errors.append(f"queue_nonpending_review:{row.get('item_id')}")

        if report.get("source_pending_count") != queue.get("pending_item_count"):
            errors.append("safe_report_source_pending_drift")
        if report.get("evidence_origin") != expected_origin:
            errors.append("safe_report_origin_drift")
        boundaries = report.get("claim_boundaries", {})
        for key in (
            "private_responses_included",
            "learner_identity_included",
            "reviewer_identity_included",
            "deterministic_outcomes_overridden",
            "canonical_authority_write",
            "canonical_egp_mapping_changed",
            "public_delivery",
            "production_runtime_enabled",
            "a2_content_promoted",
            "audio_or_recording_processed",
            "learner_mastery_claimed",
            "retention_confirmed",
        ):
            if boundaries.get(key) is not False:
                errors.append(f"claim_boundary_drift:{key}")

        if mode == "prepare":
            if report.get("validation_status") != builder.PREPARE_STATUS:
                errors.append("prepare_status_drift")
            if report.get("materialized_decision_count") != 0:
                errors.append("prepare_materialized_not_zero")
            if report.get("remaining_pending_count") != queue.get("pending_item_count"):
                errors.append("prepare_remaining_count_drift")
            if report.get("stop_reason") != "HUMAN_REVIEW_DECISIONS_REQUIRED":
                errors.append("prepare_stop_reason_drift")
            if report.get("next_short_step") != builder.NEXT_SELF:
                errors.append("prepare_next_step_drift")
            template = builder.read_json(
                root / "human_review_decision_template.private.json"
            )
            builder._assert_schema(
                "e4s_a1v1_m12e1_human_review_decisions.schema.json",
                template,
            )
            if template.get("source_review_queue_sha256") != builder.sha256_value(queue):
                errors.append("decision_template_queue_hash_drift")
            if any(row.get("decision") != "PENDING" for row in template.get("decisions", [])):
                errors.append("decision_template_not_pending")
            rebuild_root = root.parent / f"m12e1-prepare-rebuild-{uuid.uuid4().hex}"
            rebuilt = builder.prepare_workbench(
                input_root,
                representative_root,
                m12e_root,
                rebuild_root,
                expected_origin=expected_origin,
            )
            if rebuilt["queue"] != queue:
                errors.append("prepare_queue_not_reproducible")
            if rebuilt["safe_report"] != report:
                errors.append("prepare_report_not_reproducible")
        else:
            decisions_path = root / "human_review_decisions.private.json"
            decisions = builder.read_json(decisions_path)
            reviews, materialized = builder._validate_decisions(queue, decisions)
            resolved_registry = builder.read_json(
                root / "resolved_representative/cumulative_attempt_registry.private.json"
            )
            resolved_ledger = builder.read_json(
                root / "resolved_representative/cumulative_progress_ledger.private.json"
            )
            resolved_query = builder.read_json(
                root / "resolved_representative/cumulative_progress_query_index.json"
            )
            resolved_m12e = builder.read_json(
                root / "resolved_m12e/representative_evidence_qa_safe_report.json"
            )
            original_attempts = {
                str(row["item_id"]): row for row in source["registry"]["attempts"]
            }
            resolved_attempts = {
                str(row["item_id"]): row for row in resolved_registry["attempts"]
            }
            if set(original_attempts) != set(resolved_attempts):
                errors.append("resolved_registry_item_set_drift")
            pending_ids = set(ids)
            for item_id, original in original_attempts.items():
                resolved = resolved_attempts[item_id]
                if _attempt_without_review(original) != _attempt_without_review(resolved):
                    errors.append(f"resolved_attempt_nonreview_drift:{item_id}")
                if item_id not in pending_ids and original.get("operator_review") != resolved.get("operator_review"):
                    errors.append(f"deterministic_or_nonpending_review_changed:{item_id}")
                if item_id in pending_ids and resolved.get("operator_review") != reviews[item_id]:
                    errors.append(f"pending_review_materialization_drift:{item_id}")
            expected_ledger, _, expected_query = builder.m08.build_progress_artifacts(
                source["bank"], resolved_registry
            )
            if expected_ledger != resolved_ledger:
                errors.append("resolved_ledger_not_reproducible")
            if expected_query != resolved_query:
                errors.append("resolved_query_not_reproducible")
            remaining = int(
                resolved_m12e.get("evidence_summary", {}).get(
                    "pending_human_review_count", -1
                )
            )
            if report.get("materialized_decision_count") != materialized:
                errors.append("materialized_count_drift")
            if report.get("remaining_pending_count") != remaining:
                errors.append("remaining_pending_count_drift")
            if materialized + remaining != queue.get("pending_item_count"):
                errors.append("decision_accounting_drift")
            if remaining:
                if report.get("validation_status") != builder.PARTIAL_STATUS:
                    errors.append("partial_status_drift")
                if report.get("stop_reason") != "HUMAN_REVIEW_DECISIONS_REQUIRED":
                    errors.append("partial_stop_reason_drift")
                if report.get("next_short_step") != builder.NEXT_SELF:
                    errors.append("partial_next_step_drift")
            else:
                if report.get("validation_status") != builder.COMPLETE_STATUS:
                    errors.append("complete_status_drift")
                if resolved_m12e.get("evidence_summary", {}).get("pending_human_review_count") != 0:
                    errors.append("complete_resolved_pending_not_zero")
                if report.get("next_short_step") != resolved_m12e.get("next_short_step"):
                    errors.append("complete_next_step_drift")
                if report.get("stop_reason") != resolved_m12e.get("stop_reason"):
                    errors.append("complete_stop_reason_drift")
            rebuild_root = root.parent / f"m12e1-apply-rebuild-{uuid.uuid4().hex}"
            rebuilt = builder.apply_decisions(
                input_root,
                qa_root,
                representative_root,
                m12e_root,
                rebuild_root,
                decisions_path,
                expected_origin=expected_origin,
            )
            if rebuilt["resolved_registry"] != resolved_registry:
                errors.append("apply_registry_not_reproducible")
            if rebuilt["resolved_ledger"] != resolved_ledger:
                errors.append("apply_ledger_not_reproducible")
            if rebuilt["resolved_query"] != resolved_query:
                errors.append("apply_query_not_reproducible")
            if rebuilt["resolved_m12e"] != resolved_m12e:
                errors.append("apply_m12e_not_reproducible")
            if rebuilt["safe_report"] != report:
                errors.append("apply_report_not_reproducible")
    except (
        builder.HumanReviewMaterializationError,
        builder.m08.TextModeSessionError,
        builder.m12.PilotCaptureError,
        builder.m12d.RepresentativePilotError,
        builder.m12e.RepresentativeEvidenceQAError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    finally:
        if rebuild_root is not None:
            shutil.rmtree(rebuild_root, ignore_errors=True)

    expected_status = (
        builder.PREPARE_STATUS
        if mode == "prepare"
        else report.get("validation_status", builder.PARTIAL_STATUS)
    )
    return {
        "task_id": builder.TASK_ID,
        "validation_mode": mode,
        "validation_status": expected_status if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "evidence_origin": report.get("evidence_origin"),
        "source_pending_count": report.get("source_pending_count", 0),
        "materialized_decision_count": report.get("materialized_decision_count", 0),
        "remaining_pending_count": report.get("remaining_pending_count", 0),
        "outcome_counts": report.get("outcome_counts", {}),
        "deterministic_outcomes_overridden": False,
        "canonical_authority_write": False,
        "canonical_egp_mapping_changed": False,
        "public_delivery": False,
        "a2_content_promoted": False,
        "audio_or_recording_processed": False,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "stop_reason": report.get("stop_reason", "VALIDATION_FAILURE") if not errors else "VALIDATION_FAILURE",
        "next_short_step": report.get("next_short_step") if not errors else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "apply-decisions"])
    parser.add_argument("--input-root", type=Path, default=builder.DEFAULT_INPUT_ROOT)
    parser.add_argument("--qa-root", type=Path, default=builder.DEFAULT_QA_ROOT)
    parser.add_argument("--representative-root", type=Path, default=builder.DEFAULT_REPRESENTATIVE_ROOT)
    parser.add_argument("--m12e-root", type=Path, default=builder.DEFAULT_M12E_ROOT)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--expected-origin", choices=["REAL_LEARNER", "TEST_FIXTURE"], required=True)
    parser.add_argument("--validation-report", type=Path, default=DEFAULT_VALIDATION_PATH)
    args = parser.parse_args(argv)
    result = validate(
        args.mode,
        args.input_root,
        args.qa_root,
        args.representative_root,
        args.m12e_root,
        args.output_root,
        expected_origin=args.expected_origin,
    )
    builder.write_json_atomic(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
