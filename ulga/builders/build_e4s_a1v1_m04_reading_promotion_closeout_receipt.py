#!/usr/bin/env python3
"""Build a metadata-only receipt that closes M04 Reading promotion.

The detailed review queue, decisions, revisions, and reviewed bank remain private.
This tool verifies them locally, then emits only hashes, counts, completion flags,
and claim boundaries that are safe to write back to the repository.
"""
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

TASK_ID = "E4S-A1V1-M04B3_ReadingPromotionCloseoutAndM04Completion"
EPIC_ID = "E4S-A1V1_A1A1PlusCompleteFourSkillLearningSystem"
PASS_STATUS = "PASS_M04_READING_PROMOTION_CLOSEOUT_RECEIPT"
NEXT_SHORT_STEP = "E4S-A1V1-M05_ListeningV1CompletionAndIntegration"
EXPECTED_DECISIONS = {
    "PENDING": 0,
    "APPROVE_AS_IS": 77,
    "APPROVE_WITH_REVISION": 4,
    "REJECT": 62,
    "DEFER": 138,
}
EXPECTED_REVIEW_ENTRY_COUNT = 281
EXPECTED_SELECTED_SOURCE_COUNT = 54
EXPECTED_REVIEWED_ITEM_COUNT = 81


class ReadingCloseoutError(ValueError):
    """Fail-closed M04 Reading closeout error."""


def _decision_counts(registry: Mapping[str, Any]) -> dict[str, int]:
    rows = registry.get("decisions")
    if not isinstance(rows, list):
        raise ReadingCloseoutError("decision_rows_missing")
    counts = Counter(str(row.get("decision")) for row in rows if isinstance(row, Mapping))
    return {key: counts[key] for key in DECISION_VALUES}


def _require_equal(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise ReadingCloseoutError(f"{code}:expected={expected!r}:actual={actual!r}")


def _validate_inputs(
    queue: Mapping[str, Any],
    final_decisions: Mapping[str, Any],
    final_bank: Mapping[str, Any],
    promotion: Mapping[str, Any],
    approval_safe: Mapping[str, Any],
    approval_validation: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _assert_schema("e4s_a1v1_reading_review_queue.schema.json", queue)
    _assert_schema("e4s_a1v1_reading_operator_decisions.schema.json", final_decisions)
    _assert_schema("e4s_a1v1_reviewed_reading_practice_bank.schema.json", final_bank)
    _assert_schema("e4s_a1v1_reading_review_promotion_safe_report.schema.json", promotion)

    entries = queue.get("review_entries")
    if not isinstance(entries, list):
        raise ReadingCloseoutError("review_entries_missing")
    _require_equal(len(entries), EXPECTED_REVIEW_ENTRY_COUNT, "review_entry_count")
    _require_equal(queue.get("review_entry_count"), EXPECTED_REVIEW_ENTRY_COUNT, "declared_review_entry_count")
    _require_equal(queue.get("review_entries_sha256"), sha256_value(entries), "review_entries_hash")

    selection_ids = {
        str(row.get("selection_id"))
        for row in entries
        if isinstance(row, Mapping) and isinstance(row.get("selection_id"), str)
    }
    _require_equal(len(selection_ids), EXPECTED_SELECTED_SOURCE_COUNT, "selected_source_count")
    _require_equal(final_decisions.get("review_queue_sha256"), sha256_value(queue), "final_registry_queue_hash")
    _require_equal(_decision_counts(final_decisions), EXPECTED_DECISIONS, "final_decision_distribution")

    rebuilt_bank, rebuilt_promotion = apply_artifacts(queue, final_decisions)
    _require_equal(final_bank, rebuilt_bank, "final_bank_not_reproducible")
    _require_equal(promotion, rebuilt_promotion, "promotion_report_not_reproducible")
    _require_equal(final_bank.get("reviewed_item_count"), EXPECTED_REVIEWED_ITEM_COUNT, "reviewed_item_count")
    _require_equal(
        final_bank.get("reviewed_items_sha256"),
        sha256_value(final_bank.get("reviewed_items", [])),
        "reviewed_item_hash",
    )
    _require_equal(promotion.get("decision_counts"), EXPECTED_DECISIONS, "promotion_decision_distribution")
    _require_equal(promotion.get("reviewed_item_count"), EXPECTED_REVIEWED_ITEM_COUNT, "promotion_reviewed_item_count")
    _require_equal(promotion.get("promotion_claim_count"), 0, "promotion_claim_count")
    _require_equal(promotion.get("validation_status"), "PASS", "promotion_validation_status")

    _require_equal(
        approval_safe.get("validation_status"),
        "PASS_PRIVATE_REVISION_OPERATOR_APPROVAL_COMPLETE",
        "approval_safe_status",
    )
    _require_equal(approval_safe.get("review_queue_sha256"), sha256_value(queue), "approval_queue_hash")
    _require_equal(
        approval_safe.get("final_registry_sha256"),
        sha256_value(final_decisions),
        "approval_registry_hash",
    )
    _require_equal(approval_safe.get("final_bank_sha256"), sha256_value(final_bank), "approval_bank_hash")
    _require_equal(approval_safe.get("decision_counts_after"), EXPECTED_DECISIONS, "approval_decision_counts")
    _require_equal(approval_safe.get("final_reviewed_item_count"), EXPECTED_REVIEWED_ITEM_COUNT, "approval_item_count")
    _require_equal(approval_safe.get("pending_decision_count"), 0, "approval_pending_count")
    _require_equal(approval_safe.get("canonical_authority_write_count"), 0, "approval_authority_write_count")
    _require_equal(approval_safe.get("public_delivery_count"), 0, "approval_public_delivery_count")
    _require_equal(approval_safe.get("automatic_approval_performed"), False, "automatic_approval_flag")

    _require_equal(
        approval_validation.get("validation_status"),
        "PASS_PRIVATE_REVISION_OPERATOR_APPROVAL_COMPLETE",
        "approval_validation_status",
    )
    validation_expectations = {
        "approved_as_is_count": 77,
        "approved_with_revision_count": 4,
        "rejected_count": 62,
        "deferred_count": 138,
        "pending_count": 0,
        "reviewed_item_count": EXPECTED_REVIEWED_ITEM_COUNT,
        "authority_write_count": 0,
        "public_delivery_count": 0,
        "error_count": 0,
    }
    for key, expected in validation_expectations.items():
        _require_equal(approval_validation.get(key), expected, f"approval_validation_{key}")

    claim_boundaries = promotion.get("claim_boundaries")
    if not isinstance(claim_boundaries, Mapping):
        raise ReadingCloseoutError("promotion_claim_boundaries_missing")
    for key in (
        "canonical_authority_promotion",
        "public_learner_delivery",
        "source_text_public_export",
        "m04b1_m04b2_mutated",
    ):
        _require_equal(claim_boundaries.get(key), False, f"promotion_boundary_{key}")

    return rebuilt_bank, rebuilt_promotion


def build_receipt(
    queue: Mapping[str, Any],
    final_decisions: Mapping[str, Any],
    final_bank: Mapping[str, Any],
    promotion: Mapping[str, Any],
    approval_safe: Mapping[str, Any],
    approval_validation: Mapping[str, Any],
) -> dict[str, Any]:
    rebuilt_bank, rebuilt_promotion = _validate_inputs(
        queue,
        final_decisions,
        final_bank,
        promotion,
        approval_safe,
        approval_validation,
    )

    entries = queue["review_entries"]
    reviewed_items = rebuilt_bank["reviewed_items"]
    item_type_counts = Counter(str(row.get("question_type")) for row in reviewed_items)
    selected_sources = {str(row["selection_id"]) for row in entries}
    reviewed_sources = {str(row.get("selection_id")) for row in reviewed_items}

    receipt = {
        "task_id": TASK_ID,
        "epic_id": EPIC_ID,
        "artifact_type": "metadata_only_m04_reading_promotion_closeout_receipt",
        "scope": "A1_A1_PLUS_ONLY",
        "validation_status": PASS_STATUS,
        "input_hashes": {
            "review_queue_sha256": sha256_value(queue),
            "final_registry_sha256": sha256_value(final_decisions),
            "final_bank_sha256": sha256_value(final_bank),
            "promotion_report_sha256": sha256_value(promotion),
            "approval_report_sha256": sha256_value(approval_safe),
            "approval_validation_sha256": sha256_value(approval_validation),
        },
        "reading_completion": {
            "review_entry_count": len(entries),
            "selected_source_count": len(selected_sources),
            "reviewed_source_count": len(reviewed_sources),
            "reviewed_item_count": len(reviewed_items),
            "item_type_counts": dict(sorted(item_type_counts.items())),
            "final_decision_counts": dict(EXPECTED_DECISIONS),
            "pending_count": 0,
            "reproducible_private_bank": final_bank == rebuilt_bank,
            "reproducible_promotion_report": promotion == rebuilt_promotion,
        },
        "m04_gate": {
            "grammar_reading_bank_integrated": True,
            "reading_v1_six_type_contract_healthy": True,
            "source_grounded_review_bank_complete": True,
            "reading_v1_complete": True,
            "m05_progression_allowed": True,
        },
        "claim_boundaries": {
            "metadata_only_receipt": True,
            "private_source_material_committed": False,
            "private_reviewed_bank_committed": False,
            "canonical_authority_write_count": 0,
            "public_delivery_count": 0,
            "automatic_approval_performed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE",
        "blocker_type": None,
        "last_completed_status": "M04_READING_V1_COMPLETE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    _safe_scan(receipt)
    return receipt


def validate_receipt(
    queue: Mapping[str, Any],
    final_decisions: Mapping[str, Any],
    final_bank: Mapping[str, Any],
    promotion: Mapping[str, Any],
    approval_safe: Mapping[str, Any],
    approval_validation: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        rebuilt = build_receipt(
            queue,
            final_decisions,
            final_bank,
            promotion,
            approval_safe,
            approval_validation,
        )
        if rebuilt != receipt:
            errors.append("closeout_receipt_not_reproducible")
        _safe_scan(receipt)
    except (ReadingCloseoutError, PromotionBuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL_M04_READING_PROMOTION_CLOSEOUT_RECEIPT",
        "error_count": len(errors),
        "errors": errors,
        "reading_v1_complete": not errors,
        "m05_progression_allowed": not errors,
        "reviewed_item_count": receipt.get("reading_completion", {}).get("reviewed_item_count"),
        "pending_count": receipt.get("reading_completion", {}).get("pending_count"),
        "authority_write_count": receipt.get("claim_boundaries", {}).get("canonical_authority_write_count"),
        "public_delivery_count": receipt.get("claim_boundaries", {}).get("public_delivery_count"),
        "next_short_step": NEXT_SHORT_STEP if not errors else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument("--final-decisions", type=Path, required=True)
    parser.add_argument("--final-reviewed-bank", type=Path, required=True)
    parser.add_argument("--promotion-safe-report", type=Path, required=True)
    parser.add_argument("--approval-safe-report", type=Path, required=True)
    parser.add_argument("--approval-validation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = build_receipt(
            read_json(args.review_queue),
            read_json(args.final_decisions),
            read_json(args.final_reviewed_bank),
            read_json(args.promotion_safe_report),
            read_json(args.approval_safe_report),
            read_json(args.approval_validation),
        )
        write_json_atomic(args.output, receipt)
        print(json.dumps({
            "reviewed_items": receipt["reading_completion"]["reviewed_item_count"],
            "pending": receipt["reading_completion"]["pending_count"],
            "reading_v1_complete": receipt["m04_gate"]["reading_v1_complete"],
            "m05_progression_allowed": receipt["m04_gate"]["m05_progression_allowed"],
            "validation_status": receipt["validation_status"],
            "next_short_step": receipt["next_short_step"],
        }, sort_keys=True))
        return 0
    except (ReadingCloseoutError, PromotionBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
