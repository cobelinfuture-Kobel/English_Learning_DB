#!/usr/bin/env python3
"""Independently reconstruct and validate M04B3 review and promotion artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_source_grounded_reading_review_promotion import (  # noqa: E402
    CLAIM_BOUNDARIES,
    DECISION_VALUES,
    EXPECTED_DETERMINISTIC,
    EXPECTED_LITERAL,
    EXPECTED_SOURCE_COUNT,
    PromotionBuildError,
    _schema,
    apply_artifacts,
    prepare_artifacts,
    read_json,
    is_forbidden_safe_key,
    sha256_file,
    sha256_value,
)

TASK_ID = "E4S-A1V1-M04B3_SourceGroundedReadingCandidateReviewAndPromotion"
PASS = "PASS_PENDING_OPERATOR_REVIEW"


def safe_scan(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if is_forbidden_safe_key(key):
                errors.append(f"forbidden_safe_key:{path}.{key}")
            errors.extend(safe_scan(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(safe_scan(child, f"{path}[{index}]"))
    return errors


def _schema_errors(filename: str, payload: Mapping[str, Any]) -> list[str]:
    return [
        f"schema:{filename}:{'.'.join(map(str, error.absolute_path)) or '$'}:{error.message}"
        for error in _schema(filename).iter_errors(payload)
    ]


def _identity_errors(queue: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    entries = queue.get("review_entries", [])
    ids = [row.get("review_entry_id") for row in entries if isinstance(row, Mapping)]
    candidates = [row.get("candidate_id") for row in entries if isinstance(row, Mapping)]
    if len(entries) != 281:
        errors.append(f"review_entry_count_not_281:{len(entries)}")
    if len(ids) != len(set(ids)):
        errors.append("duplicate_review_entry")
    if len(candidates) != len(set(candidates)):
        errors.append("duplicate_candidate")
    if queue.get("review_entry_count") != len(entries):
        errors.append("queue_count_drift")
    if queue.get("review_entries_sha256") != sha256_value(entries):
        errors.append("queue_hash_drift")
    return errors


def validate_prepare(
    queue: Mapping[str, Any], template: Mapping[str, Any], report: Mapping[str, Any],
    m04b2_private: Mapping[str, Any], m04b2_safe: Mapping[str, Any],
    s12d_private: Mapping[str, Any], s12d_safe: Mapping[str, Any],
    upstream_hashes: Mapping[str, str],
) -> dict[str, Any]:
    errors = _schema_errors("e4s_a1v1_reading_review_queue.schema.json", queue)
    errors.extend(_schema_errors("e4s_a1v1_reading_operator_decisions.schema.json", template))
    errors.extend(_schema_errors("e4s_a1v1_reading_review_promotion_safe_report.schema.json", report))
    errors.extend(_identity_errors(queue))
    errors.extend(safe_scan(report))
    try:
        expected_queue, expected_template, expected_report = prepare_artifacts(
            m04b2_private, m04b2_safe, s12d_private, s12d_safe, upstream_hashes,
        )
        if queue != expected_queue:
            errors.append("review_queue_independent_reconstruction_mismatch")
        if template != expected_template:
            errors.append("decision_template_independent_reconstruction_mismatch")
        if report != expected_report:
            errors.append("prepare_safe_report_independent_reconstruction_mismatch")
    except (PromotionBuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"independent_prepare_reconstruction_failed:{exc}")
    decisions = template.get("decisions", [])
    if any(row.get("decision") != "PENDING" for row in decisions if isinstance(row, Mapping)):
        errors.append("template_contains_nonpending_decision")
    return {
        "task_id": TASK_ID, "validation_status": PASS if not errors else "FAIL",
        "error_count": len(errors), "errors": errors, "mode": "PREPARE_REVIEW",
        "selected_source_count": EXPECTED_SOURCE_COUNT, "review_entry_count": len(queue.get("review_entries", [])),
        "missing_entry_count": 0 if not errors else None, "extra_entry_count": 0 if not errors else None,
        "duplicate_entry_count": len(queue.get("review_entries", [])) - len({row.get("review_entry_id") for row in queue.get("review_entries", []) if isinstance(row, Mapping)}),
        "source_hash_drift_count": sum("source" in error and "drift" in error for error in errors),
        "candidate_hash_drift_count": sum("candidate" in error and "drift" in error for error in errors),
        "s12d_join_error_count": sum("s12d" in error and ("join" in error or "binding" in error) for error in errors),
        "safe_leakage_count": sum("safe" in error and ("forbidden" in error or "leakage" in error) for error in errors),
    }


def validate_apply(
    queue: Mapping[str, Any], decisions: Mapping[str, Any],
    bank: Mapping[str, Any], report: Mapping[str, Any],
) -> dict[str, Any]:
    errors = _schema_errors("e4s_a1v1_reading_review_queue.schema.json", queue)
    errors.extend(_schema_errors("e4s_a1v1_reading_operator_decisions.schema.json", decisions))
    errors.extend(_schema_errors("e4s_a1v1_reviewed_reading_practice_bank.schema.json", bank))
    errors.extend(_schema_errors("e4s_a1v1_reading_review_promotion_safe_report.schema.json", report))
    errors.extend(_identity_errors(queue))
    errors.extend(safe_scan(report))
    try:
        expected_bank, expected_report = apply_artifacts(queue, decisions)
        if bank != expected_bank:
            errors.append("reviewed_bank_independent_reconstruction_mismatch")
        if report != expected_report:
            errors.append("promotion_safe_report_independent_reconstruction_mismatch")
    except (PromotionBuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"independent_apply_reconstruction_failed:{exc}")
    items = bank.get("reviewed_items", [])
    item_ids = [row.get("reviewed_item_id") for row in items if isinstance(row, Mapping)]
    if len(item_ids) != len(set(item_ids)):
        errors.append("duplicate_reviewed_item")
    if bank.get("reviewed_item_count") != len(items):
        errors.append("reviewed_item_count_drift")
    if bank.get("reviewed_items_sha256") != sha256_value(items):
        errors.append("reviewed_items_hash_drift")
    if any(row.get("canonical_authority_promotion") is not False for row in items if isinstance(row, Mapping)):
        errors.append("canonical_authority_promotion_claim")
    if report.get("claim_boundaries") != CLAIM_BOUNDARIES:
        errors.append("claim_boundary_drift")
    status = report.get("validation_status") if not errors else "FAIL"
    return {
        "task_id": TASK_ID, "validation_status": status, "error_count": len(errors), "errors": errors,
        "mode": "APPLY_DECISIONS", "review_entry_count": len(queue.get("review_entries", [])),
        "pending_decision_count": report.get("decision_counts", {}).get("PENDING", 0),
        "approved_decision_count": sum(report.get("decision_counts", {}).get(key, 0) for key in ("APPROVE_AS_IS", "APPROVE_WITH_REVISION")),
        "rejected_decision_count": report.get("decision_counts", {}).get("REJECT", 0),
        "deferred_decision_count": report.get("decision_counts", {}).get("DEFER", 0),
        "reviewed_item_count": len(items), "promotion_claim_count": report.get("promotion_claim_count"),
        "safe_leakage_count": sum("safe" in error and ("forbidden" in error or "leakage" in error) for error in errors),
        "authority_write_count": sum("authority" in error for error in errors),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    prepare = sub.add_parser("prepare-review")
    prepare.add_argument("--review-queue", type=Path, required=True)
    prepare.add_argument("--decisions-template", type=Path, required=True)
    prepare.add_argument("--safe-report", type=Path, required=True)
    prepare.add_argument("--m04b2-private", type=Path, required=True)
    prepare.add_argument("--m04b2-safe", type=Path, required=True)
    prepare.add_argument("--s12d-private", type=Path, required=True)
    prepare.add_argument("--s12d-safe", type=Path, required=True)
    prepare.add_argument("--validation-report", type=Path)
    apply = sub.add_parser("apply-decisions")
    apply.add_argument("--review-queue", type=Path, required=True)
    apply.add_argument("--decisions", type=Path, required=True)
    apply.add_argument("--reviewed-bank", type=Path, required=True)
    apply.add_argument("--safe-report", type=Path, required=True)
    apply.add_argument("--validation-report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.mode == "prepare-review":
            paths = (args.m04b2_private, args.m04b2_safe, args.s12d_private, args.s12d_safe)
            hashes = {
                "m04b2_private_sha256": sha256_file(paths[0]), "m04b2_safe_sha256": sha256_file(paths[1]),
                "s12d_private_sha256": sha256_file(paths[2]), "s12d_safe_sha256": sha256_file(paths[3]),
            }
            result = validate_prepare(
                read_json(args.review_queue), read_json(args.decisions_template), read_json(args.safe_report),
                read_json(paths[0]), read_json(paths[1]), read_json(paths[2]), read_json(paths[3]), hashes,
            )
        else:
            result = validate_apply(
                read_json(args.review_queue), read_json(args.decisions),
                read_json(args.reviewed_bank), read_json(args.safe_report),
            )
    except (PromotionBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        result = {"task_id": TASK_ID, "validation_status": "FAIL", "error_count": 1, "errors": [str(exc)]}
    if args.validation_report:
        args.validation_report.parent.mkdir(parents=True, exist_ok=True)
        args.validation_report.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] in {"PASS", PASS} else 1


if __name__ == "__main__":
    raise SystemExit(main())
