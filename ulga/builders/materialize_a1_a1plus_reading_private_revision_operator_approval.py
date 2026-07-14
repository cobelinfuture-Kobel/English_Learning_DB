#!/usr/bin/env python3
"""Materialize explicit operator approval for the four M04B3 private revisions.

This tool never treats generated revision evidence as approval. It requires an exact
operator approval token, reviewer identity, and timezone-aware timestamp. It rebuilds
the complete private reviewed bank through the existing promotion gate and verifies
that the prior 77 reviewed items remain byte-for-byte equivalent at item level.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_reading_private_revision_evidence import (  # noqa: E402
    validate_revision_evidence,
)
from ulga.builders.build_a1_a1plus_source_grounded_reading_review_promotion import (  # noqa: E402
    DECISION_VALUES,
    PromotionBuildError,
    _assert_schema,
    _safe_scan,
    apply_artifacts,
    read_json,
    sha256_value,
    write_json_atomic,
)

TASK_ID = "E4S-A1V1-M04B3_PrivateRevisionOperatorReviewAndApproval"
APPROVAL_TOKEN = TASK_ID
EXPECTED_BEFORE = {
    "PENDING": 4,
    "APPROVE_AS_IS": 77,
    "APPROVE_WITH_REVISION": 0,
    "REJECT": 62,
    "DEFER": 138,
}
EXPECTED_AFTER = {
    "PENDING": 0,
    "APPROVE_AS_IS": 77,
    "APPROVE_WITH_REVISION": 4,
    "REJECT": 62,
    "DEFER": 138,
}
TARGET_NOTE = "TARGET_DECISION=APPROVE_WITH_REVISION"


class RevisionApprovalError(ValueError):
    """Fail-closed private revision approval error."""


def _parse_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RevisionApprovalError("reviewed_at_invalid") from exc
    if parsed.tzinfo is None:
        raise RevisionApprovalError("reviewed_at_timezone_required")
    return value


def _decision_counts(registry: Mapping[str, Any]) -> dict[str, int]:
    rows = registry.get("decisions")
    if not isinstance(rows, list):
        raise RevisionApprovalError("decision_rows_missing")
    counts = Counter(str(row.get("decision")) for row in rows if isinstance(row, Mapping))
    return {key: counts[key] for key in DECISION_VALUES}


def _validate_inputs(
    queue: Mapping[str, Any],
    prior_decisions: Mapping[str, Any],
    prior_bank: Mapping[str, Any],
    revision_private: Mapping[str, Any],
    revision_safe: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    _assert_schema("e4s_a1v1_reading_review_queue.schema.json", queue)
    _assert_schema("e4s_a1v1_reading_operator_decisions.schema.json", prior_decisions)
    _assert_schema("e4s_a1v1_reviewed_reading_practice_bank.schema.json", prior_bank)

    entries = queue.get("review_entries")
    if not isinstance(entries, list) or len(entries) != 281:
        raise RevisionApprovalError("review_queue_count_not_281")
    if queue.get("review_entry_count") != 281 or queue.get("review_entries_sha256") != sha256_value(entries):
        raise RevisionApprovalError("review_queue_accounting_or_hash_drift")
    if prior_decisions.get("review_queue_sha256") != sha256_value(queue):
        raise RevisionApprovalError("prior_registry_queue_hash_mismatch")
    if _decision_counts(prior_decisions) != EXPECTED_BEFORE:
        raise RevisionApprovalError(f"prior_decision_distribution_drift:{_decision_counts(prior_decisions)}")

    if prior_bank.get("reviewed_item_count") != 77:
        raise RevisionApprovalError("prior_reviewed_item_count_not_77")
    if prior_bank.get("source_review_queue_sha256") != sha256_value(queue):
        raise RevisionApprovalError("prior_bank_queue_hash_mismatch")
    if prior_bank.get("source_decisions_sha256") != sha256_value(prior_decisions):
        raise RevisionApprovalError("prior_bank_registry_hash_mismatch")
    if prior_bank.get("reviewed_items_sha256") != sha256_value(prior_bank.get("reviewed_items", [])):
        raise RevisionApprovalError("prior_bank_item_hash_drift")

    revision_validation = validate_revision_evidence(revision_private, revision_safe)
    if revision_validation.get("validation_status") != "PASS_PRIVATE_REVISION_EVIDENCE_READY_FOR_OPERATOR_REVIEW":
        raise RevisionApprovalError(f"revision_evidence_not_ready:{revision_validation.get('errors', [])}")
    if revision_validation.get("revision_entry_count") != 4 or revision_validation.get("ready_for_operator_review_count") != 4:
        raise RevisionApprovalError("revision_evidence_count_not_four_ready")

    entry_by_id = {str(row.get("review_entry_id")): row for row in entries if isinstance(row, Mapping)}
    decision_rows = prior_decisions.get("decisions")
    if not isinstance(decision_rows, list) or len(decision_rows) != 281:
        raise RevisionApprovalError("prior_decision_count_not_281")
    decision_by_id = {str(row.get("review_entry_id")): row for row in decision_rows if isinstance(row, Mapping)}
    if len(decision_by_id) != 281 or set(decision_by_id) != set(entry_by_id):
        raise RevisionApprovalError("prior_decision_entry_set_drift")

    revision_rows = revision_private.get("revision_entries")
    if not isinstance(revision_rows, list) or len(revision_rows) != 4:
        raise RevisionApprovalError("private_revision_entry_count_not_4")
    revision_by_id: dict[str, Mapping[str, Any]] = {}
    for row in revision_rows:
        if not isinstance(row, Mapping):
            raise RevisionApprovalError("private_revision_row_invalid")
        entry_id = row.get("review_entry_id")
        if not isinstance(entry_id, str) or entry_id in revision_by_id:
            raise RevisionApprovalError("private_revision_id_invalid_or_duplicate")
        entry = entry_by_id.get(entry_id)
        decision = decision_by_id.get(entry_id)
        if entry is None or decision is None:
            raise RevisionApprovalError(f"private_revision_join_missing:{entry_id}")
        if decision.get("decision") != "PENDING" or TARGET_NOTE not in str(decision.get("review_notes", "")):
            raise RevisionApprovalError(f"target_decision_not_pending_revision:{entry_id}")
        if row.get("revision_status") != "READY_FOR_OPERATOR_REVIEW" or row.get("formal_decision") != "PENDING":
            raise RevisionApprovalError(f"private_revision_not_ready_or_already_approved:{entry_id}")
        if row.get("operator_approval_recorded") is not False:
            raise RevisionApprovalError(f"private_revision_claims_prior_approval:{entry_id}")
        for left, right, code in (
            (row.get("candidate_id"), entry.get("candidate_id"), "candidate"),
            (row.get("selection_id"), entry.get("selection_id"), "selection"),
            (row.get("question_type"), entry.get("question_type"), "question_type"),
            (row.get("source_content_sha256"), entry.get("source_integrity", {}).get("content_sha256"), "source_hash"),
            (row.get("candidate_payload_sha256"), entry.get("candidate_payload_sha256"), "candidate_hash"),
        ):
            if left != right:
                raise RevisionApprovalError(f"private_revision_{code}_drift:{entry_id}")
        revision = row.get("proposed_revision")
        if not isinstance(revision, Mapping):
            raise RevisionApprovalError(f"private_revision_payload_missing:{entry_id}")
        revision_by_id[entry_id] = row

    pending_ids = {
        entry_id
        for entry_id, decision in decision_by_id.items()
        if decision.get("decision") == "PENDING"
    }
    if set(revision_by_id) != pending_ids:
        raise RevisionApprovalError("private_revision_set_does_not_equal_pending_set")
    return entries, decision_by_id, revision_by_id


def approve_private_revisions(
    queue: Mapping[str, Any],
    prior_decisions: Mapping[str, Any],
    prior_bank: Mapping[str, Any],
    revision_private: Mapping[str, Any],
    revision_safe: Mapping[str, Any],
    *,
    reviewer_id: str,
    reviewed_at: str,
    approval_token: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if approval_token != APPROVAL_TOKEN:
        raise RevisionApprovalError("explicit_private_revision_approval_token_required")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise RevisionApprovalError("reviewer_id_required")
    reviewed_at = _parse_timestamp(reviewed_at)

    entries, _prior_by_id, revision_by_id = _validate_inputs(
        queue, prior_decisions, prior_bank, revision_private, revision_safe
    )
    final_decisions = copy.deepcopy(prior_decisions)
    final_by_id = {row["review_entry_id"]: row for row in final_decisions["decisions"]}
    entry_by_id = {row["review_entry_id"]: row for row in entries}

    for entry_id, revision_row in revision_by_id.items():
        entry = entry_by_id[entry_id]
        final_by_id[entry_id].update(
            decision="APPROVE_WITH_REVISION",
            reviewer_id=reviewer_id,
            reviewed_at=reviewed_at,
            criteria={key: True for key in entry.get("review_requirements", [])},
            revision=copy.deepcopy(revision_row["proposed_revision"]),
            rejection_reasons=[],
            review_notes=(
                "OPERATOR_PRIVATE_REVISION_APPROVED;"
                "SOURCE=PRIVATE_REVISION_EVIDENCE;"
                "DECISION=APPROVE_WITH_REVISION"
            ),
        )

    _assert_schema("e4s_a1v1_reading_operator_decisions.schema.json", final_decisions)
    if _decision_counts(final_decisions) != EXPECTED_AFTER:
        raise RevisionApprovalError(f"final_decision_distribution_drift:{_decision_counts(final_decisions)}")

    final_bank, promotion = apply_artifacts(queue, final_decisions)
    if final_bank.get("reviewed_item_count") != 81:
        raise RevisionApprovalError(f"final_reviewed_item_count_not_81:{final_bank.get('reviewed_item_count')}")
    if promotion.get("decision_counts") != EXPECTED_AFTER:
        raise RevisionApprovalError("final_promotion_decision_distribution_drift")
    if promotion.get("validation_status") != "PASS":
        raise RevisionApprovalError("final_promotion_status_not_pass")

    prior_items = {row["reviewed_item_id"]: row for row in prior_bank.get("reviewed_items", [])}
    final_items = {row["reviewed_item_id"]: row for row in final_bank.get("reviewed_items", [])}
    if len(prior_items) != 77 or len(final_items) != 81:
        raise RevisionApprovalError("reviewed_item_identity_count_drift")
    for item_id, prior_item in prior_items.items():
        if final_items.get(item_id) != prior_item:
            raise RevisionApprovalError(f"prior_reviewed_item_changed:{item_id}")

    safe = {
        "task_id": TASK_ID,
        "artifact_type": "private_revision_operator_approval_safe_report",
        "review_queue_sha256": sha256_value(queue),
        "prior_registry_sha256": sha256_value(prior_decisions),
        "prior_bank_sha256": sha256_value(prior_bank),
        "revision_evidence_sha256": sha256_value(revision_private),
        "final_registry_sha256": sha256_value(final_decisions),
        "final_bank_sha256": sha256_value(final_bank),
        "decision_counts_before": dict(EXPECTED_BEFORE),
        "decision_counts_after": dict(EXPECTED_AFTER),
        "revised_decision_count": 4,
        "prior_reviewed_item_preserved_count": 77,
        "final_reviewed_item_count": 81,
        "pending_decision_count": 0,
        "operator_identity_recorded": True,
        "operator_timestamp_recorded": True,
        "automatic_approval_performed": False,
        "canonical_authority_write_count": 0,
        "public_delivery_count": 0,
        "validation_status": "PASS_PRIVATE_REVISION_OPERATOR_APPROVAL_COMPLETE",
        "errors": [],
        "next_resume_task": "E4S-A1V1-M04B3_ReadingPromotionCloseoutAndM04Completion",
    }
    _safe_scan(safe)
    return final_decisions, final_bank, promotion, safe


def validate_approval_outputs(
    queue: Mapping[str, Any],
    prior_bank: Mapping[str, Any],
    final_decisions: Mapping[str, Any],
    final_bank: Mapping[str, Any],
    promotion: Mapping[str, Any],
    safe: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        _assert_schema("e4s_a1v1_reading_review_queue.schema.json", queue)
        _assert_schema("e4s_a1v1_reading_operator_decisions.schema.json", final_decisions)
        _assert_schema("e4s_a1v1_reviewed_reading_practice_bank.schema.json", final_bank)
        _assert_schema("e4s_a1v1_reading_review_promotion_safe_report.schema.json", promotion)
        rebuilt_bank, rebuilt_promotion = apply_artifacts(queue, final_decisions)
        if rebuilt_bank != final_bank:
            errors.append("final_bank_not_reproducible")
        if rebuilt_promotion != promotion:
            errors.append("promotion_report_not_reproducible")
        if _decision_counts(final_decisions) != EXPECTED_AFTER:
            errors.append("final_decision_distribution_invalid")
        if final_bank.get("reviewed_item_count") != 81:
            errors.append("final_reviewed_item_count_not_81")
        prior_items = {row["reviewed_item_id"]: row for row in prior_bank.get("reviewed_items", [])}
        final_items = {row["reviewed_item_id"]: row for row in final_bank.get("reviewed_items", [])}
        if len(prior_items) != 77 or any(final_items.get(key) != value for key, value in prior_items.items()):
            errors.append("prior_reviewed_items_not_preserved")
        expected_safe_hashes = {
            "review_queue_sha256": sha256_value(queue),
            "prior_bank_sha256": sha256_value(prior_bank),
            "final_registry_sha256": sha256_value(final_decisions),
            "final_bank_sha256": sha256_value(final_bank),
        }
        for key, expected in expected_safe_hashes.items():
            if safe.get(key) != expected:
                errors.append(f"safe_hash_drift:{key}")
        if safe.get("validation_status") != "PASS_PRIVATE_REVISION_OPERATOR_APPROVAL_COMPLETE":
            errors.append("safe_validation_status_invalid")
        if safe.get("pending_decision_count") != 0 or safe.get("final_reviewed_item_count") != 81:
            errors.append("safe_completion_counts_invalid")
        _safe_scan(safe)
    except (PromotionBuildError, RevisionApprovalError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return {
        "task_id": TASK_ID,
        "approved_as_is_count": _decision_counts(final_decisions).get("APPROVE_AS_IS", 0) if isinstance(final_decisions, Mapping) else 0,
        "approved_with_revision_count": _decision_counts(final_decisions).get("APPROVE_WITH_REVISION", 0) if isinstance(final_decisions, Mapping) else 0,
        "rejected_count": _decision_counts(final_decisions).get("REJECT", 0) if isinstance(final_decisions, Mapping) else 0,
        "deferred_count": _decision_counts(final_decisions).get("DEFER", 0) if isinstance(final_decisions, Mapping) else 0,
        "pending_count": _decision_counts(final_decisions).get("PENDING", 0) if isinstance(final_decisions, Mapping) else 0,
        "reviewed_item_count": final_bank.get("reviewed_item_count") if isinstance(final_bank, Mapping) else None,
        "authority_write_count": 0,
        "public_delivery_count": 0,
        "error_count": len(errors),
        "errors": errors,
        "validation_status": "PASS_PRIVATE_REVISION_OPERATOR_APPROVAL_COMPLETE" if not errors else "FAIL_PRIVATE_REVISION_OPERATOR_APPROVAL",
        "next_resume_task": "E4S-A1V1-M04B3_ReadingPromotionCloseoutAndM04Completion",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument("--prior-decisions", type=Path, required=True)
    parser.add_argument("--prior-reviewed-bank", type=Path, required=True)
    parser.add_argument("--private-revision-evidence", type=Path, required=True)
    parser.add_argument("--revision-safe-report", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--reviewed-at", required=True)
    parser.add_argument("--approval-token", required=True)
    args = parser.parse_args(argv)
    try:
        decisions, bank, promotion, safe = approve_private_revisions(
            read_json(args.review_queue),
            read_json(args.prior_decisions),
            read_json(args.prior_reviewed_bank),
            read_json(args.private_revision_evidence),
            read_json(args.revision_safe_report),
            reviewer_id=args.reviewer_id,
            reviewed_at=args.reviewed_at,
            approval_token=args.approval_token,
        )
        write_json_atomic(args.output_root / "operator_decisions.final.json", decisions)
        write_json_atomic(args.output_root / "reviewed_private_reading_practice_bank.final.json", bank)
        write_json_atomic(args.output_root / "promotion_safe_report.final.json", promotion)
        write_json_atomic(args.output_root / "private_revision_operator_approval_safe_report.json", safe)
        print(json.dumps({
            "approved_with_revision": 4,
            "pending": 0,
            "reviewed_items": 81,
            "validation_status": safe["validation_status"],
        }, sort_keys=True))
        return 0
    except (RevisionApprovalError, PromotionBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
