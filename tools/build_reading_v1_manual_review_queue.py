"""Build a machine-readable manual review queue for Reading V1.

This follow-up builder converts the validated metadata-only tiny pilot into a
manual review queue artifact. It does not approve learner-facing output, create
HTML/worksheet exports, mutate learner state, read source payloads, or promote
source/content authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "READING_V1_MANUAL_REVIEW_QUEUE_V1"
SUMMARY_SCHEMA_VERSION = "READING_V1_MANUAL_REVIEW_QUEUE_SUMMARY_V1"
PHASE_ID = "E4S-P1_ReadingV1SourceGroundedPractice"
TASK_ID = "E4S-P1-FU-A_ManualReviewQueueArtifact_Implementation"
NEXT_SHORTEST_STEP = "SourcePayloadDisplayPolicy_DesignScan"

DEFAULT_CANDIDATE_PATH = "ulga/reports/reading_v1_pilot_candidates.json"
DEFAULT_VALIDATION_REPORT_PATH = "ulga/reports/reading_v1_validation_report.json"
DEFAULT_QUEUE_PATH = "ulga/reports/reading_v1_manual_review_queue.json"
DEFAULT_SUMMARY_PATH = "ulga/reports/reading_v1_manual_review_queue_summary.json"

ALLOWED_REVIEW_STATUSES = {
    "not_started",
    "pending",
    "in_review",
    "needs_revision",
    "passed_internal_review",
    "failed_review",
    "blocked_by_policy",
    "rejected",
}

ALLOWED_DECISIONS = {
    "pending",
    "approve_for_internal_validated_pool",
    "needs_metadata_revision",
    "needs_evidence_locator_revision",
    "needs_level_review",
    "needs_question_answer_revision",
    "reject_candidate",
    "block_candidate",
}

BLOCKED_OUTPUT_FIELDS = {
    "learner_facing_output_created",
    "student_html_created",
    "worksheet_created",
    "learner_event_created",
    "learner_state_updated",
    "adaptive_recommendation_created",
    "authority_promotion_performed",
    "large_scale_generation_performed",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_candidates(path: Path) -> list[dict[str, Any]]:
    loaded = load_json(path)
    if not isinstance(loaded, list):
        raise ValueError("candidate artifact must be a JSON list")
    candidates = [item for item in loaded if isinstance(item, dict)]
    if len(candidates) != len(loaded):
        raise ValueError("candidate artifact contains non-object records")
    return candidates


def validation_warnings_by_candidate(validation_report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for warning in validation_report.get("warnings", []):
        if not isinstance(warning, dict):
            continue
        candidate_id = str(warning.get("candidate_id", ""))
        if candidate_id:
            grouped.setdefault(candidate_id, []).append(warning)
    return grouped


def determine_priority(warnings: list[dict[str, Any]]) -> str:
    codes = {str(warning.get("code")) for warning in warnings}
    if "READING_V1_LEVEL_BAND_UNKNOWN" in codes or "READING_V1_MANUAL_REVIEW_PENDING" in codes:
        return "P2_level_or_metadata_review"
    return "P3_normal_manual_review"


def make_review_dimension(status: str, notes: list[str]) -> dict[str, Any]:
    return {
        "status": status,
        "notes": notes,
        "learner_facing_authorized": False,
        "requires_human_confirmation": True,
    }


def build_queue_item(
    candidate: dict[str, Any],
    validation_report_path: Path,
    candidate_path: Path,
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_id = str(candidate["reading_candidate_id"])
    warning_refs = [
        {
            "code": warning.get("code"),
            "field_path": warning.get("field_path"),
            "message": warning.get("message"),
            "severity": warning.get("severity"),
        }
        for warning in warnings
    ]
    level_unknown = any(warning.get("code") == "READING_V1_LEVEL_BAND_UNKNOWN" for warning in warnings)
    manual_pending = any(warning.get("code") == "READING_V1_MANUAL_REVIEW_PENDING" for warning in warnings)

    return {
        "review_queue_item_id": f"review:{candidate_id}",
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "candidate_id": candidate_id,
        "candidate_artifact_ref": str(candidate_path),
        "validation_report_ref": str(validation_report_path),
        "validator_status": "PASS_WITH_WARNINGS",
        "validator_issue_refs": [],
        "validator_warning_refs": warning_refs,
        "review_priority": determine_priority(warnings),
        "review_status": "pending",
        "reviewer_fields": {
            "reviewer_id": None,
            "review_started_at": None,
            "review_completed_at": None,
            "review_round": 1,
            "review_notes": [
                "Pending manual review. Metadata-only candidate; source payload not inspected.",
                "No learner private data or learner answer history is included in this queue item.",
            ],
            "review_decision_reason": None,
            "review_evidence_refs": [
                str(validation_report_path),
                str(candidate_path),
                candidate.get("source_trace", {}).get("source_id"),
                candidate.get("evidence_model", {}).get("evidence_locator"),
            ],
        },
        "source_trace_review": make_review_dimension(
            "pending",
            [
                f"source_id={candidate.get('source_trace', {}).get('source_id')}",
                f"source_payload_copied={candidate.get('source_trace', {}).get('source_payload_copied')}",
            ],
        ),
        "payload_policy_review": make_review_dimension(
            "pending",
            [
                f"passage_excerpt_allowed={candidate.get('reading_payload_ref', {}).get('passage_excerpt_allowed')}",
                f"evidence_text_allowed={candidate.get('evidence_model', {}).get('evidence_text_allowed')}",
            ],
        ),
        "question_review": make_review_dimension(
            "pending",
            [
                f"question_type={candidate.get('question_model', {}).get('question_type')}",
                "Question text remains metadata-only and is not learner-ready.",
            ],
        ),
        "answer_review": make_review_dimension(
            "pending",
            [
                f"answer_evidence_ref={candidate.get('answer_model', {}).get('answer_evidence_ref')}",
                "Expected answer requires human review from locator.",
            ],
        ),
        "evidence_review": make_review_dimension(
            "pending",
            [
                f"evidence_locator={candidate.get('evidence_model', {}).get('evidence_locator')}",
                "Evidence is locator-only; source text display remains blocked.",
            ],
        ),
        "level_review": make_review_dimension(
            "needs_review" if level_unknown else "pending",
            [
                f"normalized_level_band={candidate.get('level_metadata', {}).get('normalized_level_band')}",
                "Level band must not be used for learner placement.",
            ],
        ),
        "situation_skill_review": make_review_dimension(
            "pending",
            [
                f"situation_domain={candidate.get('situation_metadata', {}).get('situation_domain')}",
                f"skill_fit={candidate.get('skill_metadata', {}).get('skill_fit')}",
                f"multi_skill_expansion_allowed={candidate.get('skill_metadata', {}).get('multi_skill_expansion_allowed')}",
            ],
        ),
        "blocked_output_review": make_review_dimension(
            "pass",
            [f"{field}={candidate.get('blocked_output_state', {}).get(field)}" for field in sorted(BLOCKED_OUTPUT_FIELDS)],
        ),
        "decision": "pending",
        "handoff_gate": "manual_review_pending",
        "learner_facing_allowed": False,
        "worksheet_allowed": False,
        "public_preview_allowed": False,
        "authority_upgrade_allowed": False,
        "review_audit": {
            "created_by_task": TASK_ID,
            "created_from_candidate_status": candidate.get("candidate_status"),
            "created_from_validator_status": "PASS_WITH_WARNINGS",
            "manual_review_pending": manual_pending,
            "level_band_unknown": level_unknown,
            "no_learner_private_data": True,
            "no_learner_answer_history": True,
            "no_output_approval": True,
        },
    }


def build_queue(candidates: list[dict[str, Any]], validation_report: dict[str, Any], candidate_path: Path, validation_report_path: Path) -> dict[str, Any]:
    warnings_by_candidate = validation_warnings_by_candidate(validation_report)
    items = [
        build_queue_item(
            candidate,
            validation_report_path,
            candidate_path,
            warnings_by_candidate.get(str(candidate.get("reading_candidate_id")), []),
        )
        for candidate in candidates
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "source_candidate_artifact_ref": str(candidate_path),
        "source_validation_report_ref": str(validation_report_path),
        "candidate_count": len(candidates),
        "queue_item_count": len(items),
        "review_status_allowed_values": sorted(ALLOWED_REVIEW_STATUSES),
        "decision_allowed_values": sorted(ALLOWED_DECISIONS),
        "items": items,
        "learner_facing_allowed": False,
        "worksheet_allowed": False,
        "public_preview_allowed": False,
        "authority_upgrade_allowed": False,
        "next_shortest_step": NEXT_SHORTEST_STEP,
    }


def build_summary(queue: dict[str, Any], output_path: Path, validation_report: dict[str, Any]) -> dict[str, Any]:
    items = queue.get("items", [])
    pending_count = sum(1 for item in items if item.get("review_status") == "pending")
    in_review_count = sum(1 for item in items if item.get("review_status") == "in_review")
    passed_internal_review_count = sum(1 for item in items if item.get("review_status") == "passed_internal_review")
    failed_review_count = sum(1 for item in items if item.get("review_status") == "failed_review")
    blocked_count = sum(1 for item in items if item.get("review_status") == "blocked_by_policy")
    rejected_count = sum(1 for item in items if item.get("review_status") == "rejected")
    p2_count = sum(1 for item in items if item.get("review_priority") == "P2_level_or_metadata_review")

    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "task_id": TASK_ID,
        "manual_review_queue_ref": str(output_path),
        "source_validation_report_ref": queue["source_validation_report_ref"],
        "candidate_count": queue["candidate_count"],
        "queue_item_count": queue["queue_item_count"],
        "pending_count": pending_count,
        "in_review_count": in_review_count,
        "passed_internal_review_count": passed_internal_review_count,
        "failed_review_count": failed_review_count,
        "blocked_count": blocked_count,
        "rejected_count": rejected_count,
        "p2_level_or_metadata_review_count": p2_count,
        "validation_status": validation_report.get("status"),
        "validation_issue_count": len(validation_report.get("issues", [])),
        "validation_warning_count": len(validation_report.get("warnings", [])),
        "learner_facing_allowed": False,
        "worksheet_allowed": False,
        "public_preview_allowed": False,
        "authority_upgrade_allowed": False,
        "status": "PASS_WITH_WARNINGS",
        "warnings": [
            {
                "code": "READING_V1_REVIEW_QUEUE_PENDING",
                "severity": "medium",
                "message": "Manual review queue artifact exists, but review decisions remain pending.",
                "blocking": False,
            },
            {
                "code": "READING_V1_OUTPUT_STILL_BLOCKED",
                "severity": "medium",
                "message": "Queue artifact does not authorize learner-facing output, worksheet export, public preview, or authority upgrade.",
                "blocking": False,
            },
        ],
        "issues": [],
        "next_shortest_step": NEXT_SHORTEST_STEP,
    }


def validate_queue(queue: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if queue.get("learner_facing_allowed") is not False:
        errors.append("queue learner_facing_allowed must be false")
    if queue.get("worksheet_allowed") is not False:
        errors.append("queue worksheet_allowed must be false")
    if queue.get("authority_upgrade_allowed") is not False:
        errors.append("queue authority_upgrade_allowed must be false")
    for item in queue.get("items", []):
        if item.get("review_status") not in ALLOWED_REVIEW_STATUSES:
            errors.append(f"invalid review_status: {item.get('review_status')}")
        if item.get("decision") not in ALLOWED_DECISIONS:
            errors.append(f"invalid decision: {item.get('decision')}")
        for field in ["learner_facing_allowed", "worksheet_allowed", "public_preview_allowed", "authority_upgrade_allowed"]:
            if item.get(field) is not False:
                errors.append(f"{item.get('candidate_id')} {field} must be false")
        reviewer_fields = item.get("reviewer_fields", {})
        serialized = json.dumps(reviewer_fields, ensure_ascii=False).lower()
        if "learner_answer" in serialized or "private" in serialized and "no learner private" not in serialized:
            errors.append(f"{item.get('candidate_id')} reviewer fields may include learner private data")
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Reading V1 manual review queue artifact.")
    parser.add_argument("--candidate-path", default=DEFAULT_CANDIDATE_PATH)
    parser.add_argument("--validation-report-path", default=DEFAULT_VALIDATION_REPORT_PATH)
    parser.add_argument("--queue-output", default=DEFAULT_QUEUE_PATH)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    candidate_path = Path(args.candidate_path)
    validation_report_path = Path(args.validation_report_path)
    queue_output = Path(args.queue_output)
    summary_output = Path(args.summary_output)

    candidates = load_candidates(candidate_path)
    validation_report = load_json(validation_report_path)
    queue = build_queue(candidates, validation_report, candidate_path, validation_report_path)
    errors = validate_queue(queue)
    summary = build_summary(queue, queue_output, validation_report)

    if errors:
        summary["status"] = "FAIL"
        summary["issues"] = [{"code": "READING_V1_MANUAL_REVIEW_QUEUE_INVALID", "message": error, "blocking": True} for error in errors]

    write_json(queue_output, queue)
    write_json(summary_output, summary)
    return 0 if summary["status"] == "PASS_WITH_WARNINGS" else 1


if __name__ == "__main__":
    sys.exit(main())
