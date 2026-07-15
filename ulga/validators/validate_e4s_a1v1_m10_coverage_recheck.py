#!/usr/bin/env python3
"""Independently validate the M10 A1/A1+ coverage recheck."""
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

from ulga.builders import build_e4s_a1v1_m10_coverage_recheck as builder  # noqa: E402


def _invariant_errors(report: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != 109:
        errors.append("row_count_not_109")
        rows = []
    row_ids = [str(row.get("canonical_egp_row_id")) for row in rows]
    if len(set(row_ids)) != len(row_ids):
        errors.append("duplicate_row_id")
    if row_ids != sorted(row_ids):
        errors.append("row_order_not_deterministic")

    classifications = Counter(str(row.get("classification")) for row in rows)
    if any(value not in builder.CLASSIFICATIONS for value in classifications):
        errors.append("unknown_classification")
    summary = report.get("coverage_summary", {})
    expected_counts = {
        "covered_row_count": classifications["COVERED"],
        "draft_only_row_count": classifications["DRAFT_ONLY"],
        "missing_row_count": classifications["MISSING"],
    }
    for key, expected in expected_counts.items():
        if summary.get(key) != expected:
            errors.append(f"summary_count_drift:{key}")
    if sum(expected_counts.values()) != 109:
        errors.append("classification_accounting_not_109")

    for row in rows:
        row_id = str(row.get("canonical_egp_row_id"))
        layers = row.get("coverage_layers")
        if not isinstance(layers, Mapping) or set(layers) != set(builder.COVERAGE_LAYERS):
            errors.append(f"coverage_layers_invalid:{row_id}")
            continue
        if not all(isinstance(value, bool) for value in layers.values()):
            errors.append(f"coverage_layer_non_boolean:{row_id}")
        classification = row.get("classification")
        if classification == "COVERED" and not all(layers.values()):
            errors.append(f"covered_row_has_failed_layer:{row_id}")
        if classification == "MISSING" and layers.get("canonical_mapping") is True and all(
            layers.get(key) is True
            for key in (
                "teaching_candidate",
                "practice_candidate",
                "assessment_candidate",
                "four_skill_contract",
                "private_text_runtime",
            )
        ):
            errors.append(f"missing_row_has_complete_structure:{row_id}")
        skill_counts = row.get("four_skill_item_counts")
        if not isinstance(skill_counts, Mapping) or set(skill_counts) != set(builder.SKILLS):
            errors.append(f"four_skill_counts_invalid:{row_id}")
        text_counts = row.get("text_runtime_item_counts")
        if not isinstance(text_counts, Mapping) or set(text_counts) != {"reading", "writing"}:
            errors.append(f"text_runtime_counts_invalid:{row_id}")
        if row.get("learner_evidence_state") != "NOT_COLLECTED":
            errors.append(f"false_learner_evidence_state:{row_id}")
        if row.get("learner_mastery_state") != "NOT_CLAIMED":
            errors.append(f"false_mastery_state:{row_id}")
        if row.get("speaking_real_audio_evidence_state") != "DEFERRED_BY_OPERATOR":
            errors.append(f"speaking_audio_state_drift:{row_id}")

    layer_counts = report.get("coverage_layer_counts", {})
    for layer in builder.COVERAGE_LAYERS:
        expected = sum(bool(row.get("coverage_layers", {}).get(layer)) for row in rows)
        if layer_counts.get(layer) != expected:
            errors.append(f"layer_count_drift:{layer}")

    lists = report.get("classification_lists", {})
    for classification, key in (
        ("COVERED", "covered_row_ids"),
        ("DRAFT_ONLY", "draft_only_row_ids"),
        ("MISSING", "missing_row_ids"),
    ):
        expected = [
            row["canonical_egp_row_id"]
            for row in rows
            if row.get("classification") == classification
        ]
        if lists.get(key) != expected:
            errors.append(f"classification_list_drift:{key}")

    backlog = report.get("backlog", {})
    if backlog.get("structural_missing_row_ids") != lists.get("missing_row_ids"):
        errors.append("missing_backlog_drift")
    if backlog.get("draft_only_row_ids") != lists.get("draft_only_row_ids"):
        errors.append("draft_backlog_drift")
    all_rows = row_ids
    for key in (
        "actual_learner_evidence_pending_row_ids",
        "learner_mastery_unclaimed_row_ids",
        "speaking_real_audio_deferred_row_ids",
    ):
        if backlog.get(key) != all_rows:
            errors.append(f"evidence_backlog_drift:{key}")
    pending_units = backlog.get("operator_content_review_pending_unit_ids")
    if not isinstance(pending_units, list) or len(pending_units) != 24 or len(set(pending_units)) != 24:
        errors.append("operator_review_pending_units_not_24")
    reading_audit = backlog.get("source_grounded_reading_row_audit", {})
    if reading_audit.get("status") != "NOT_AUDITABLE_FROM_COMMITTED_METADATA":
        errors.append("reading_row_audit_status_drift")

    if summary.get("canonical_grammar_unit_count") != 24:
        errors.append("canonical_unit_count_not_24")
    if summary.get("canonical_egp_row_count") != 109:
        errors.append("canonical_row_count_not_109")
    if summary.get("actual_learner_evidence_row_coverage_percent") != 0.0:
        errors.append("false_learner_evidence_coverage")
    if summary.get("learner_mastery_row_coverage_percent") != 0.0:
        errors.append("false_mastery_coverage")
    if summary.get("operator_reviewed_candidate_unit_count") != 0:
        errors.append("false_operator_review_count")
    if summary.get("operator_review_pending_candidate_unit_count") != 24:
        errors.append("operator_review_pending_count_not_24")

    boundaries = report.get("claim_boundaries", {})
    expected_boundaries = {
        "metadata_only_report": True,
        "new_design_docs_created": False,
        "new_planning_docs_created": False,
        "canonical_graph_written": False,
        "a2_a2plus_in_scope": False,
        "private_content_included": False,
        "source_text_included": False,
        "audio_bytes_included": False,
        "recording_files_processed": False,
        "learner_responses_included": False,
        "canonical_authority_writes": 0,
        "public_delivery_count": 0,
        "actual_learner_evidence_complete": False,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
    }
    if boundaries != expected_boundaries:
        errors.append("claim_boundaries_drift")
    if report.get("validation_status") != builder.PASS_STATUS:
        errors.append("report_status_not_pass")
    if report.get("stop_reason") != "NONE":
        errors.append("stop_reason_not_none")
    if report.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("next_short_step_drift")
    return errors


def validate(report: Mapping[str, Any], *, rebuild: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    try:
        builder.safe_scan(report, name="m10_coverage_recheck")
        errors.extend(_invariant_errors(report))
        if rebuild:
            rebuilt = builder.build_report()
            if rebuilt != report:
                errors.append("coverage_report_not_reproducible")
    except (
        builder.CoverageRecheckError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))

    summary = report.get("coverage_summary", {})
    return {
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "canonical_grammar_unit_count": summary.get("canonical_grammar_unit_count", 0),
        "canonical_egp_row_count": summary.get("canonical_egp_row_count", 0),
        "covered_row_count": summary.get("covered_row_count", 0),
        "draft_only_row_count": summary.get("draft_only_row_count", 0),
        "missing_row_count": summary.get("missing_row_count", 0),
        "structural_coverage_percent": summary.get("structural_coverage_percent", 0.0),
        "actual_learner_evidence_row_coverage_percent": summary.get("actual_learner_evidence_row_coverage_percent", 0.0),
        "learner_mastery_row_coverage_percent": summary.get("learner_mastery_row_coverage_percent", 0.0),
        "operator_review_pending_candidate_unit_count": summary.get("operator_review_pending_candidate_unit_count", 0),
        "speaking_real_audio_evidence_state": "DEFERRED_BY_OPERATOR",
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=builder.OUTPUT_PATH)
    parser.add_argument("--validation-report", type=Path, default=builder.VALIDATION_PATH)
    parser.add_argument("--no-rebuild", action="store_true")
    args = parser.parse_args(argv)
    report = builder.read_json(args.report)
    result = validate(report, rebuild=not args.no_rebuild)
    builder.write_json(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
