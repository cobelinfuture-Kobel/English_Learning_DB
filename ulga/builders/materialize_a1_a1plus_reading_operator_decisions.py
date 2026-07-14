#!/usr/bin/env python3
"""Materialize an explicitly approved M04B3 AI-assisted triage batch.

The AI triage registry is never treated as approval by itself.  This tool
requires an operator approval token, reviewer identity, and timezone-aware
review timestamp.  Entries proposed as APPROVE_WITH_REVISION remain PENDING
until a complete private revision exists; all other approved dispositions are
materialized and passed through the existing M04B3 promotion gate.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_source_grounded_reading_review_promotion import (  # noqa: E402
    DECISION_VALUES,
    LITERAL_TYPES,
    PromotionBuildError,
    _assert_schema,
    apply_artifacts,
    read_json,
    sha256_value,
    write_json_atomic,
)

TASK_ID = "E4S-A1V1-M04B3_OperatorDecisionMaterializationAndPromotionGate"
APPROVAL_TOKEN = TASK_ID
EXPECTED_PROPOSALS = {
    "APPROVE_AS_IS": 77,
    "APPROVE_WITH_REVISION": 4,
    "REJECT": 62,
    "DEFER": 138,
}
EXPECTED_MATERIALIZED = {
    "PENDING": 4,
    "APPROVE_AS_IS": 77,
    "APPROVE_WITH_REVISION": 0,
    "REJECT": 62,
    "DEFER": 138,
}
NOTE_RE = re.compile(
    r"^AI_ASSISTED_TRIAGE_ONLY;PROPOSED_DECISION="
    r"(?P<decision>APPROVE_AS_IS|APPROVE_WITH_REVISION|REJECT|DEFER);"
    r"REASON_CODES=(?P<reasons>[A-Z0-9_,]+);NOT_OPERATOR_APPROVAL$"
)
REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class MaterializationError(ValueError):
    """Fail-closed operator materialization error."""


def _parse_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MaterializationError("reviewed_at_invalid") from exc
    if parsed.tzinfo is None:
        raise MaterializationError("reviewed_at_timezone_required")
    return value


def _parse_note(note: Any) -> tuple[str, list[str]]:
    if not isinstance(note, str):
        raise MaterializationError("triage_review_note_missing")
    match = NOTE_RE.fullmatch(note)
    if match is None:
        raise MaterializationError("triage_review_note_contract_invalid")
    reasons = match.group("reasons").split(",")
    if not reasons or len(reasons) != len(set(reasons)) or any(not REASON_RE.fullmatch(item) for item in reasons):
        raise MaterializationError("triage_reason_codes_invalid")
    return match.group("decision"), reasons


def _validate_identity(queue: Mapping[str, Any], triage: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    _assert_schema("e4s_a1v1_reading_review_queue.schema.json", queue)
    _assert_schema("e4s_a1v1_reading_operator_decisions.schema.json", triage)
    entries = queue.get("review_entries", [])
    if len(entries) != 281 or queue.get("review_entry_count") != 281:
        raise MaterializationError("review_queue_count_not_281")
    if queue.get("review_entries_sha256") != sha256_value(entries):
        raise MaterializationError("review_queue_hash_drift")
    if triage.get("review_queue_sha256") != sha256_value(queue):
        raise MaterializationError("triage_queue_hash_mismatch")
    decisions = triage.get("decisions", [])
    if not isinstance(decisions, list) or len(decisions) != 281:
        raise MaterializationError("triage_decision_count_not_281")
    by_id: dict[str, Mapping[str, Any]] = {}
    for row in decisions:
        entry_id = row.get("review_entry_id")
        if not isinstance(entry_id, str) or entry_id in by_id:
            raise MaterializationError("duplicate_or_invalid_triage_decision")
        if row.get("decision") != "PENDING":
            raise MaterializationError("triage_contains_formal_decision")
        if row.get("reviewer_id") is not None or row.get("reviewed_at") is not None:
            raise MaterializationError("triage_contains_reviewer_evidence")
        if row.get("revision") is not None or row.get("criteria") != {}:
            raise MaterializationError("triage_contains_revision_or_criteria")
        by_id[entry_id] = row
    expected_ids = {entry["review_entry_id"] for entry in entries}
    if set(by_id) != expected_ids:
        raise MaterializationError("triage_review_entry_set_mismatch")
    return entries, by_id


def materialize(
    queue: Mapping[str, Any],
    triage: Mapping[str, Any],
    *,
    reviewer_id: str,
    reviewed_at: str,
    approval_token: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return formal decisions, reviewed bank, promotion report, and safe summary."""
    if approval_token != APPROVAL_TOKEN:
        raise MaterializationError("explicit_operator_approval_token_required")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise MaterializationError("reviewer_id_required")
    reviewed_at = _parse_timestamp(reviewed_at)
    entries, triage_by_id = _validate_identity(queue, triage)

    proposal_counts: Counter[str] = Counter()
    parsed: dict[str, tuple[str, list[str]]] = {}
    for entry in entries:
        triage_row = triage_by_id[entry["review_entry_id"]]
        if triage_row.get("candidate_id") != entry.get("candidate_id"):
            raise MaterializationError(f"candidate_join_mismatch:{entry['review_entry_id']}")
        if triage_row.get("source_content_sha256") != entry.get("source_integrity", {}).get("content_sha256"):
            raise MaterializationError(f"source_hash_drift:{entry['review_entry_id']}")
        if triage_row.get("candidate_payload_sha256") != entry.get("candidate_payload_sha256"):
            raise MaterializationError(f"candidate_hash_drift:{entry['review_entry_id']}")
        proposal, reasons = _parse_note(triage_row.get("review_notes"))
        proposal_counts[proposal] += 1
        parsed[entry["review_entry_id"]] = (proposal, reasons)
    if dict(proposal_counts) != EXPECTED_PROPOSALS:
        raise MaterializationError(
            "proposal_distribution_mismatch:"
            + json.dumps(dict(sorted(proposal_counts.items())), sort_keys=True)
        )

    output = copy.deepcopy(triage)
    output_by_id = {row["review_entry_id"]: row for row in output["decisions"]}
    pending_revision_ids: list[str] = []
    reason_counts: Counter[str] = Counter()
    for entry in entries:
        row = output_by_id[entry["review_entry_id"]]
        proposal, reasons = parsed[entry["review_entry_id"]]
        reason_counts.update(reasons)
        if proposal == "APPROVE_WITH_REVISION":
            pending_revision_ids.append(entry["review_entry_id"])
            row.update(
                decision="PENDING",
                reviewer_id=None,
                reviewed_at=None,
                criteria={},
                revision=None,
                rejection_reasons=[],
                review_notes=(
                    "OPERATOR_BATCH_DISPOSITION_ACKNOWLEDGED;"
                    "TARGET_DECISION=APPROVE_WITH_REVISION;"
                    f"REASON_CODES={','.join(reasons)};"
                    "REVISION_EVIDENCE_REQUIRED;NOT_YET_FORMALLY_APPROVED"
                ),
            )
            continue
        if proposal == "APPROVE_AS_IS":
            if entry.get("question_type") in LITERAL_TYPES:
                raise MaterializationError(f"literal_approve_as_is_forbidden:{entry['review_entry_id']}")
            if entry.get("automated_prechecks", {}).get("overall_status") == "BLOCK":
                raise MaterializationError(f"block_precheck_cannot_be_approved:{entry['review_entry_id']}")
        row.update(
            decision=proposal,
            reviewer_id=reviewer_id,
            reviewed_at=reviewed_at,
            criteria={key: True for key in entry.get("review_requirements", [])},
            revision=None,
            rejection_reasons=reasons if proposal in {"REJECT", "DEFER"} else [],
            review_notes=(
                "OPERATOR_BATCH_DECISION_MATERIALIZED;"
                f"SOURCE=AI_ASSISTED_TRIAGE;DECISION={proposal};"
                f"REASON_CODES={','.join(reasons)}"
            ),
        )

    _assert_schema("e4s_a1v1_reading_operator_decisions.schema.json", output)
    materialized_counts = Counter(row["decision"] for row in output["decisions"])
    closed_counts = {key: materialized_counts[key] for key in DECISION_VALUES}
    if closed_counts != EXPECTED_MATERIALIZED:
        raise MaterializationError(f"materialized_distribution_mismatch:{closed_counts}")

    bank, promotion_report = apply_artifacts(queue, output)
    if bank.get("reviewed_item_count") != 77:
        raise MaterializationError(f"reviewed_item_count_not_77:{bank.get('reviewed_item_count')}")
    if promotion_report.get("decision_counts") != EXPECTED_MATERIALIZED:
        raise MaterializationError("promotion_report_decision_distribution_drift")
    if promotion_report.get("validation_status") != "PASS_PENDING_OPERATOR_REVIEW":
        raise MaterializationError("promotion_status_not_pending_revision_evidence")

    safe = {
        "task_id": TASK_ID,
        "artifact_type": "operator_decision_materialization_safe_report",
        "review_queue_sha256": sha256_value(queue),
        "triage_registry_sha256": sha256_value(triage),
        "materialized_registry_sha256": sha256_value(output),
        "reviewed_bank_sha256": sha256_value(bank),
        "proposal_counts": dict(EXPECTED_PROPOSALS),
        "materialized_decision_counts": dict(EXPECTED_MATERIALIZED),
        "reviewed_item_count": bank["reviewed_item_count"],
        "pending_revision_evidence_count": len(pending_revision_ids),
        "pending_revision_entry_ids_sha256": sha256_value(sorted(pending_revision_ids)),
        "reason_code_counts": dict(sorted(reason_counts.items())),
        "operator_identity_recorded": True,
        "operator_timestamp_recorded": True,
        "automatic_approval_performed": False,
        "canonical_authority_write_performed": False,
        "public_learner_delivery_performed": False,
        "validation_status": "PASS_77_PROMOTED_4_REVISION_EVIDENCE_PENDING",
        "errors": [],
        "next_resume_task": "E4S-A1V1-M04B3_PrivateRevisionEvidenceCompletion",
    }
    return output, bank, promotion_report, safe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument("--triage-registry", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--reviewed-at", required=True)
    parser.add_argument("--approval-token", required=True)
    args = parser.parse_args(argv)
    try:
        decisions, bank, promotion, safe = materialize(
            read_json(args.review_queue),
            read_json(args.triage_registry),
            reviewer_id=args.reviewer_id,
            reviewed_at=args.reviewed_at,
            approval_token=args.approval_token,
        )
        write_json_atomic(args.output_root / "operator_decisions.materialized.json", decisions)
        write_json_atomic(args.output_root / "reviewed_private_reading_practice_bank.json", bank)
        write_json_atomic(args.output_root / "promotion_safe_report.json", promotion)
        write_json_atomic(args.output_root / "operator_materialization_safe_report.json", safe)
        print(json.dumps({
            "reviewed_items": bank["reviewed_item_count"],
            "pending_revision_evidence": safe["pending_revision_evidence_count"],
            "validation_status": safe["validation_status"],
        }, sort_keys=True))
        return 0
    except (MaterializationError, PromotionBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
