"""Build conservative Reading V1 manual review decision artifacts.

This follow-up builder turns pending review-queue items into recorded internal
review decisions. It intentionally does not approve learner-facing output,
HTML/worksheet export, public preview, learner state, adaptive behavior, source
payload display, or source/content authority promotion.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "READING_V1_MANUAL_REVIEW_DECISIONS_V1"
SUMMARY_SCHEMA_VERSION = "READING_V1_MANUAL_REVIEW_DECISION_SUMMARY_V1"
PHASE_ID = "E4S-P1_ReadingV1SourceGroundedPractice"
TASK_ID = "E4S-P1-FU-C_ManualReviewDecisionArtifact_Implementation"
NEXT_SHORTEST_STEP = "LearnerFacingOutputGate_Reopen_DesignScan"

DEFAULT_QUEUE_PATH = "ulga/reports/reading_v1_manual_review_queue.json"
DEFAULT_POLICY_REF = "docs/ulga/E4S_P1_READING_V1_SOURCE_PAYLOAD_DISPLAY_POLICY.md"
DEFAULT_DECISIONS_PATH = "ulga/reports/reading_v1_manual_review_decisions.json"
DEFAULT_SUMMARY_PATH = "ulga/reports/reading_v1_manual_review_decision_summary.json"

ALLOWED_DECISIONS = {
    "approve_for_internal_validated_pool",
    "needs_metadata_revision",
    "needs_evidence_locator_revision",
    "needs_level_review",
    "needs_question_answer_revision",
    "reject_candidate",
    "block_candidate",
}

ALLOWED_REVIEW_STATUSES = {
    "needs_revision",
    "passed_internal_review",
    "failed_review",
    "blocked_by_policy",
    "rejected",
}

DISPLAY_OUTCOMES = {
    "metadata_only_internal_review",
    "operator_authored_text_needed",
    "rewritten_replacement_text_needed",
    "source_payload_display_blocked",
    "source_permission_review_needed",
    "reject_for_display",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def warning_codes(item: dict[str, Any]) -> set[str]:
    return {str(warning.get("code")) for warning in item.get("validator_warning_refs", []) if isinstance(warning, dict)}


def choose_decision(item: dict[str, Any]) -> tuple[str, str, str, list[str]]:
    codes = warning_codes(item)
    reasons: list[str] = []
    display_outcome = "metadata_only_internal_review"

    if "READING_V1_LEVEL_BAND_UNKNOWN" in codes:
        reasons.append("Level band is UNKNOWN and must not be used for learner placement.")
    if "READING_V1_MANUAL_REVIEW_PENDING" in codes:
        reasons.append("Candidate still requires manual review before any content use.")

    evidence_review = item.get("evidence_review", {})
    payload_policy_review = item.get("payload_policy_review", {})
    question_review = item.get("question_review", {})

    serialized_policy = json.dumps([evidence_review, payload_policy_review, question_review], ensure_ascii=False).lower()
    if "source text display remains blocked" in serialized_policy or "passage_excerpt_allowed=false" in serialized_policy:
        display_outcome = "source_payload_display_blocked"
        reasons.append("Source payload, passage excerpt, and evidence text display remain blocked by policy.")

    if display_outcome == "source_payload_display_blocked":
        return "needs_revision", "needs_level_review", display_outcome, reasons
    if reasons:
        return "needs_revision", "needs_metadata_revision", display_outcome, reasons
    return "passed_internal_review", "approve_for_internal_validated_pool", display_outcome, ["No pending warnings detected."]


def build_decision(item: dict[str, Any], queue_ref: str, policy_ref: str) -> dict[str, Any]:
    review_status, decision, display_outcome, reasons = choose_decision(item)
    candidate_id = item["candidate_id"]
    source_blocked = display_outcome == "source_payload_display_blocked"
    return {
        "decision_id": f"decision:{candidate_id}",
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "candidate_id": candidate_id,
        "review_queue_item_ref": item.get("review_queue_item_id"),
        "manual_review_queue_ref": queue_ref,
        "source_payload_display_policy_ref": policy_ref,
        "review_status": review_status,
        "decision": decision,
        "display_outcome": display_outcome,
        "decision_reason": reasons,
        "review_round": item.get("reviewer_fields", {}).get("review_round", 1),
        "review_decision_source": "deterministic_policy_readback_from_queue_and_display_policy",
        "reviewer_id": "system_policy_readback",
        "review_completed": True,
        "review_completed_at": None,
        "candidate_can_remain_internal": decision in {"needs_level_review", "needs_metadata_revision", "needs_evidence_locator_revision", "needs_question_answer_revision", "approve_for_internal_validated_pool"},
        "candidate_requires_revision": decision.startswith("needs_"),
        "candidate_rejected": decision in {"reject_candidate", "block_candidate"},
        "source_payload_display_allowed": False,
        "source_excerpt_display_allowed": False,
        "evidence_text_display_allowed": False,
        "operator_authored_text_needed": True,
        "rewritten_replacement_text_needed": True,
        "source_payload_display_blocked": source_blocked,
        "learner_facing_allowed": False,
        "worksheet_allowed": False,
        "public_preview_allowed": False,
        "authority_upgrade_allowed": False,
        "next_gate_eligible": False,
        "next_gate_blockers": [
            "source_payload_display_blocked",
            "level_band_unknown",
            "learner_facing_gate_still_blocked",
            "display_ready_text_absent",
        ],
        "validator_warning_refs": item.get("validator_warning_refs", []),
        "evidence_refs": item.get("reviewer_fields", {}).get("review_evidence_refs", []),
        "audit": {
            "created_by_task": TASK_ID,
            "created_from_queue_item_status": item.get("review_status"),
            "created_from_queue_decision": item.get("decision"),
            "no_source_payload_copied": True,
            "no_learner_private_data": True,
            "no_learner_answer_history": True,
            "no_output_approval": True,
        },
    }


def build_decisions(queue: dict[str, Any], queue_ref: str, policy_ref: str) -> dict[str, Any]:
    decisions = [build_decision(item, queue_ref, policy_ref) for item in queue.get("items", [])]
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "manual_review_queue_ref": queue_ref,
        "source_payload_display_policy_ref": policy_ref,
        "candidate_count": queue.get("candidate_count", len(decisions)),
        "decision_count": len(decisions),
        "decisions": decisions,
        "learner_facing_allowed": False,
        "worksheet_allowed": False,
        "public_preview_allowed": False,
        "authority_upgrade_allowed": False,
        "source_payload_display_allowed": False,
        "evidence_text_display_allowed": False,
        "next_shortest_step": NEXT_SHORTEST_STEP,
    }


def build_summary(decisions_artifact: dict[str, Any], output_ref: str) -> dict[str, Any]:
    decisions = decisions_artifact.get("decisions", [])
    by_decision: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for decision in decisions:
        by_decision[decision.get("decision", "unknown")] = by_decision.get(decision.get("decision", "unknown"), 0) + 1
        by_status[decision.get("review_status", "unknown")] = by_status.get(decision.get("review_status", "unknown"), 0) + 1

    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "manual_review_decisions_ref": output_ref,
        "manual_review_queue_ref": decisions_artifact["manual_review_queue_ref"],
        "source_payload_display_policy_ref": decisions_artifact["source_payload_display_policy_ref"],
        "candidate_count": decisions_artifact["candidate_count"],
        "decision_count": decisions_artifact["decision_count"],
        "review_status_counts": by_status,
        "decision_counts": by_decision,
        "completed_decision_count": sum(1 for decision in decisions if decision.get("review_completed") is True),
        "passed_internal_review_count": by_status.get("passed_internal_review", 0),
        "needs_revision_count": by_status.get("needs_revision", 0),
        "learner_facing_allowed": False,
        "worksheet_allowed": False,
        "public_preview_allowed": False,
        "authority_upgrade_allowed": False,
        "source_payload_display_allowed": False,
        "evidence_text_display_allowed": False,
        "next_gate_eligible_count": sum(1 for decision in decisions if decision.get("next_gate_eligible") is True),
        "status": "PASS_WITH_WARNINGS",
        "issues": [],
        "warnings": [
            {
                "code": "READING_V1_DECISIONS_NEED_REVISION",
                "severity": "medium",
                "message": "Manual review decisions were recorded, but all current candidates still need revision before any output gate can approve learner-facing use.",
                "blocking": False,
            },
            {
                "code": "READING_V1_OUTPUT_STILL_BLOCKED",
                "severity": "medium",
                "message": "Decision artifact does not authorize learner-facing output, worksheet export, public preview, source payload display, or authority upgrade.",
                "blocking": False,
            },
        ],
        "next_shortest_step": NEXT_SHORTEST_STEP,
    }


def validate_decisions(decisions_artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ["learner_facing_allowed", "worksheet_allowed", "public_preview_allowed", "authority_upgrade_allowed", "source_payload_display_allowed", "evidence_text_display_allowed"]:
        if decisions_artifact.get(field) is not False:
            errors.append(f"top-level {field} must be false")
    for decision in decisions_artifact.get("decisions", []):
        if decision.get("decision") not in ALLOWED_DECISIONS:
            errors.append(f"invalid decision: {decision.get('decision')}")
        if decision.get("review_status") not in ALLOWED_REVIEW_STATUSES:
            errors.append(f"invalid review_status: {decision.get('review_status')}")
        if decision.get("display_outcome") not in DISPLAY_OUTCOMES:
            errors.append(f"invalid display_outcome: {decision.get('display_outcome')}")
        for field in ["learner_facing_allowed", "worksheet_allowed", "public_preview_allowed", "authority_upgrade_allowed", "source_payload_display_allowed", "evidence_text_display_allowed"]:
            if decision.get(field) is not False:
                errors.append(f"{decision.get('candidate_id')} {field} must be false")
        if decision.get("next_gate_eligible") is not False:
            errors.append(f"{decision.get('candidate_id')} next_gate_eligible must be false for current tiny pilot")
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Reading V1 manual review decision artifact.")
    parser.add_argument("--queue-path", default=DEFAULT_QUEUE_PATH)
    parser.add_argument("--policy-ref", default=DEFAULT_POLICY_REF)
    parser.add_argument("--decisions-output", default=DEFAULT_DECISIONS_PATH)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    queue_path = Path(args.queue_path)
    decisions_output = Path(args.decisions_output)
    summary_output = Path(args.summary_output)

    queue = load_json(queue_path)
    decisions = build_decisions(queue, str(queue_path), args.policy_ref)
    errors = validate_decisions(decisions)
    summary = build_summary(decisions, str(decisions_output))

    if errors:
        summary["status"] = "FAIL"
        summary["issues"] = [{"code": "READING_V1_MANUAL_REVIEW_DECISION_INVALID", "message": error, "blocking": True} for error in errors]

    write_json(decisions_output, decisions)
    write_json(summary_output, summary)
    return 0 if summary["status"] == "PASS_WITH_WARNINGS" else 1


if __name__ == "__main__":
    sys.exit(main())
