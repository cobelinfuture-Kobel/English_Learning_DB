#!/usr/bin/env python3
"""Build the A1/A1+ operator-review intake and text-mode release gate.

Audio rendering, audio capture, ASR, and pronunciation/fluency evidence are
explicitly deferred by operator decision. They cannot be inferred as complete
and they do not block an independently reviewed Reading/Writing text-mode pilot.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_cross_skill_closure import (
    build_and_validate_from_repo as build_cross_skill_source,
)
from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (
    build_and_validate_from_repo as build_candidate_source,
)

TASK_ID = "R7-M105I_A1A1PlusOperatorReviewTextModeGateImplementation"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_RESUME_TASK = "R7-M105J_A1A1PlusOperatorReviewDecisionIntake"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_grammar_text_mode_review_gate.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_grammar_text_mode_review_gate_validation.json"

REVIEW_DIMENSIONS = (
    "learning_objectives",
    "form_rules",
    "meaning_functions",
    "usage_conditions",
    "positive_examples",
    "negative_examples",
    "common_error_tags",
    "reading_writing_activities_and_assessments",
)
DECISIONS = {"APPROVE_TEXT_MODE", "NEEDS_REVISION", "REJECT"}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _require_pass(name: str, report: Mapping[str, Any]) -> None:
    if report.get("validation_status") != "PASS":
        raise ValueError(f"source_validation_failed:{name}")


def _candidate_units(candidate: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    units = {
        unit["grammar_unit_id"]: unit
        for unit in candidate.get("learning_units", [])
        if unit.get("grammar_unit_id")
    }
    if len(units) != 24:
        raise ValueError("candidate_unit_set_not_24")
    return units


def build_artifact(
    candidate: dict[str, Any],
    cross_skill: dict[str, Any],
) -> dict[str, Any]:
    units = _candidate_units(candidate)
    closure_units = cross_skill.get("by_grammar_unit_id", {})
    if set(units) != set(closure_units) or len(closure_units) != 24:
        raise ValueError("candidate_cross_skill_unit_identity_mismatch")

    canonical_rows = set(candidate.get("by_egp_row_id", {}))
    closure_rows = set(cross_skill.get("by_egp_row_id", {}))
    if canonical_rows != closure_rows or len(canonical_rows) != 109:
        raise ValueError("candidate_cross_skill_row_identity_mismatch")

    review_queue: list[dict[str, Any]] = []
    for grammar_id in sorted(units):
        unit = units[grammar_id]
        closure = closure_units[grammar_id]
        reading = closure["skill_paths"]["reading"]
        writing = closure["skill_paths"]["writing"]
        review_queue.append(
            {
                "review_unit_id": f"TEXT_REVIEW:{grammar_id}",
                "grammar_unit_id": grammar_id,
                "official_egp_level": "A1",
                "internal_stage": unit["internal_stage"],
                "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
                "canonical_egp_row_count": len(unit["canonical_egp_row_ids"]),
                "content_authority_status": unit["content_authority_status"],
                "review_dimensions": {
                    dimension: {
                        "status": "PENDING_OPERATOR_REVIEW",
                        "reviewer_ref": None,
                        "evidence_ref": None,
                    }
                    for dimension in REVIEW_DIMENSIONS
                },
                "text_mode_evidence": {
                    "reading_activity_ids": list(reading["activity_ids"]),
                    "reading_assessment_ids": list(reading["assessment_ids"]),
                    "writing_activity_ids": list(writing["activity_ids"]),
                    "writing_assessment_ids": list(writing["assessment_ids"]),
                    "reading_writing_gate_status": "CANDIDATE_READY_FOR_REVIEW",
                },
                "deferred_skill_policy": {
                    "listening": "TRANSCRIPT_CANDIDATE_RETAINED_AUDIO_DEFERRED",
                    "speaking": "PROMPT_CANDIDATE_RETAINED_AUDIO_ASR_DEFERRED",
                    "audio_is_required_for_text_mode_review": False,
                    "audio_is_required_for_full_four_skill_release": True,
                },
                "decision_status": "PENDING",
                "operator_review_complete": False,
                "text_mode_pilot_eligible": False,
                "private_learning_promoted": False,
            }
        )

    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_text_mode_review_gate",
        "artifact_type": "a1_a1plus_operator_review_intake_and_text_mode_gate",
        "schema_version": "a1_grammar_text_mode_review_gate.v1",
        "official_level": "A1",
        "internal_stages": ["A1", "A1+"],
        "source_artifact_ids": [candidate["artifact_id"], cross_skill["artifact_id"]],
        "operator_scope_decision": {
            "decision": "SKIP_AUDIO_FOR_CURRENT_PROGRAM_PHASE",
            "decision_date": "2026-07-10",
            "text_mode_scope": ["teaching_content", "reading", "writing"],
            "deferred_scope": [
                "listening_audio_rendering",
                "speaking_audio_capture",
                "asr",
                "pronunciation_scoring",
                "fluency_scoring",
            ],
            "deferred_scope_is_not_complete": True,
        },
        "coverage_summary": {
            "canonical_unit_count": 24,
            "canonical_unique_egp_row_count": 109,
            "text_mode_review_queue_unit_count": 24,
            "text_mode_review_queue_row_count": 109,
            "pending_operator_review_unit_count": 24,
            "approved_text_mode_unit_count": 0,
            "needs_revision_unit_count": 0,
            "rejected_unit_count": 0,
            "text_mode_pilot_eligible_unit_count": 0,
            "text_mode_pilot_eligible_row_count": 0,
            "rendered_listening_audio_asset_count": 0,
            "captured_speaking_audio_asset_count": 0,
            "asr_or_manual_speaking_transcript_count": 0,
            "actual_learner_attempt_count": 0,
        },
        "review_dimensions": list(REVIEW_DIMENSIONS),
        "review_queue": review_queue,
        "release_gates": {
            "canonical_authority_gate": {"status": "PASS"},
            "candidate_text_content_gate": {"status": "PASS"},
            "reading_writing_candidate_path_gate": {"status": "PASS"},
            "audio_scope_gate": {
                "status": "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE",
                "blocks_text_mode": False,
                "blocks_full_four_skill_release": True,
            },
            "operator_text_review_gate": {"status": "BLOCKED_PENDING_DECISIONS"},
            "text_mode_private_pilot_gate": {"status": "BLOCKED_PENDING_REVIEW"},
            "actual_learner_evidence_gate": {"status": "BLOCKED"},
            "full_four_skill_release_gate": {"status": "BLOCKED_AUDIO_DEFERRED"},
            "production_runtime_gate": {"status": "BLOCKED"},
        },
        "claim_boundaries": {
            "text_mode_review_intake_complete": True,
            "audio_scope_deferred_by_operator": True,
            "audio_scope_complete": False,
            "operator_text_review_complete": False,
            "text_mode_private_pilot_eligible": False,
            "actual_learner_evidence_complete": False,
            "full_four_skill_release_complete": False,
            "production_runtime_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_persistent_learner_state_write": True,
            "no_external_nlp_dependency": True,
            "no_restricted_source_payload_copy": True,
        },
        "continuation_gate": {
            "status": "BLOCKED_REQUIRES_OPERATOR_REVIEW_DECISIONS",
            "blocker_type": "OPERATOR_CONTENT_REVIEW_DECISIONS_REQUIRED",
            "next_resume_task": NEXT_RESUME_TASK,
        },
    }


def validate_decisions(
    decisions: Mapping[str, Mapping[str, Any]],
    expected_unit_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    if set(decisions) != expected_unit_ids:
        missing = sorted(expected_unit_ids - set(decisions))
        extra = sorted(set(decisions) - expected_unit_ids)
        errors.append(f"review_decision_unit_set_mismatch:missing={missing}:extra={extra}")
        return errors
    for grammar_id, decision in decisions.items():
        value = decision.get("decision")
        if value not in DECISIONS:
            errors.append(f"invalid_review_decision:{grammar_id}:{value}")
        reviewer_ref = decision.get("reviewer_ref")
        evidence_ref = decision.get("evidence_ref")
        if not isinstance(reviewer_ref, str) or not reviewer_ref.strip():
            errors.append(f"reviewer_ref_missing:{grammar_id}")
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            errors.append(f"review_evidence_ref_missing:{grammar_id}")
    return errors


def apply_review_decisions(
    artifact: dict[str, Any],
    decisions: Mapping[str, Mapping[str, Any]],
    *,
    simulation: bool = False,
) -> dict[str, Any]:
    result = deepcopy(artifact)
    expected = {item["grammar_unit_id"] for item in result["review_queue"]}
    errors = validate_decisions(decisions, expected)
    if errors:
        raise ValueError(";".join(errors))

    counts = {"APPROVE_TEXT_MODE": 0, "NEEDS_REVISION": 0, "REJECT": 0}
    approved_rows: set[str] = set()
    for item in result["review_queue"]:
        grammar_id = item["grammar_unit_id"]
        decision = decisions[grammar_id]
        value = decision["decision"]
        counts[value] += 1
        item["decision_status"] = value
        item["operator_review_complete"] = True
        item["text_mode_pilot_eligible"] = value == "APPROVE_TEXT_MODE"
        item["decision_evidence"] = {
            "reviewer_ref": decision["reviewer_ref"],
            "evidence_ref": decision["evidence_ref"],
            "simulation": simulation,
        }
        for dimension in REVIEW_DIMENSIONS:
            item["review_dimensions"][dimension] = {
                "status": value,
                "reviewer_ref": decision["reviewer_ref"],
                "evidence_ref": decision["evidence_ref"],
            }
        if value == "APPROVE_TEXT_MODE":
            approved_rows.update(item["canonical_egp_row_ids"])

    summary = result["coverage_summary"]
    summary["pending_operator_review_unit_count"] = 0
    summary["approved_text_mode_unit_count"] = counts["APPROVE_TEXT_MODE"]
    summary["needs_revision_unit_count"] = counts["NEEDS_REVISION"]
    summary["rejected_unit_count"] = counts["REJECT"]
    summary["text_mode_pilot_eligible_unit_count"] = counts["APPROVE_TEXT_MODE"]
    summary["text_mode_pilot_eligible_row_count"] = len(approved_rows)

    all_approved = counts["APPROVE_TEXT_MODE"] == 24
    result["release_gates"]["operator_text_review_gate"]["status"] = (
        "PASS" if all_approved else "BLOCKED_REVISIONS_OR_REJECTIONS"
    )
    result["release_gates"]["text_mode_private_pilot_gate"]["status"] = (
        "PASS_READY_FOR_OPERATOR_CONTROLLED_PILOT"
        if all_approved
        else "BLOCKED_PENDING_FULL_TEXT_REVIEW_APPROVAL"
    )
    result["claim_boundaries"]["operator_text_review_complete"] = True
    result["claim_boundaries"]["text_mode_private_pilot_eligible"] = all_approved
    result["decision_application"] = {
        "mode": "SIMULATION" if simulation else "OPERATOR_EVIDENCE",
        "all_24_units_approved": all_approved,
        "audio_scope_remains_deferred": True,
        "full_four_skill_release_complete": False,
    }
    result["continuation_gate"] = {
        "status": (
            "TEXT_MODE_PILOT_ELIGIBLE"
            if all_approved
            else "BLOCKED_REQUIRES_CONTENT_REVISION"
        ),
        "blocker_type": (
            None if all_approved else "OPERATOR_CONTENT_REVISION_REQUIRED"
        ),
        "next_resume_task": (
            "R7-M105K_A1A1PlusTextModePrivatePilotIntegration"
            if all_approved
            else "R7-M105J_A1A1PlusOperatorReviewDecisionIntake"
        ),
    }
    return result


def validate_artifact(
    artifact: dict[str, Any],
    candidate: dict[str, Any],
    cross_skill: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    expected_units = set(_candidate_units(candidate))
    expected_rows = set(candidate.get("by_egp_row_id", {}))
    queue = artifact.get("review_queue", [])
    queue_ids = {item.get("grammar_unit_id") for item in queue}
    queue_rows = {
        row_id
        for item in queue
        for row_id in item.get("canonical_egp_row_ids", [])
    }
    if len(queue) != 24 or queue_ids != expected_units:
        errors.append("review_queue_not_24_canonical_units")
    if queue_rows != expected_rows or len(queue_rows) != 109:
        errors.append("review_queue_not_109_canonical_rows")
    for item in queue:
        grammar_id = item.get("grammar_unit_id")
        if set(item.get("review_dimensions", {})) != set(REVIEW_DIMENSIONS):
            errors.append(f"review_dimension_set_mismatch:{grammar_id}")
        if item.get("decision_status") != "PENDING":
            errors.append(f"false_review_decision_claim:{grammar_id}")
        if item.get("operator_review_complete") is not False:
            errors.append(f"false_operator_review_completion:{grammar_id}")
        if item.get("text_mode_pilot_eligible") is not False:
            errors.append(f"false_text_mode_eligibility:{grammar_id}")
        policy = item.get("deferred_skill_policy", {})
        if policy.get("audio_is_required_for_text_mode_review") is not False:
            errors.append(f"audio_incorrectly_blocks_text_mode:{grammar_id}")
        if policy.get("audio_is_required_for_full_four_skill_release") is not True:
            errors.append(f"audio_full_release_boundary_missing:{grammar_id}")

    summary = artifact.get("coverage_summary", {})
    expected_summary = {
        "canonical_unit_count": 24,
        "canonical_unique_egp_row_count": 109,
        "text_mode_review_queue_unit_count": 24,
        "text_mode_review_queue_row_count": 109,
        "pending_operator_review_unit_count": 24,
        "approved_text_mode_unit_count": 0,
        "needs_revision_unit_count": 0,
        "rejected_unit_count": 0,
        "text_mode_pilot_eligible_unit_count": 0,
        "text_mode_pilot_eligible_row_count": 0,
        "rendered_listening_audio_asset_count": 0,
        "captured_speaking_audio_asset_count": 0,
        "asr_or_manual_speaking_transcript_count": 0,
        "actual_learner_attempt_count": 0,
    }
    if summary != expected_summary:
        errors.append("coverage_summary_mismatch")

    gates = artifact.get("release_gates", {})
    audio_gate = gates.get("audio_scope_gate", {})
    if audio_gate.get("status") != "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE":
        errors.append("audio_scope_not_deferred")
    if audio_gate.get("blocks_text_mode") is not False:
        errors.append("audio_scope_blocks_text_mode")
    if gates.get("operator_text_review_gate", {}).get("status") != (
        "BLOCKED_PENDING_DECISIONS"
    ):
        errors.append("operator_review_gate_not_blocked")
    if gates.get("text_mode_private_pilot_gate", {}).get("status") != (
        "BLOCKED_PENDING_REVIEW"
    ):
        errors.append("text_mode_gate_forged_open")

    boundaries = artifact.get("claim_boundaries", {})
    required_false = (
        "audio_scope_complete",
        "operator_text_review_complete",
        "text_mode_private_pilot_eligible",
        "actual_learner_evidence_complete",
        "full_four_skill_release_complete",
        "production_runtime_complete",
    )
    for field in required_false:
        if boundaries.get(field) is not False:
            errors.append(f"false_completion_claim:{field}")
    for field in (
        "text_mode_review_intake_complete",
        "audio_scope_deferred_by_operator",
        "no_a2_a2plus_expansion",
        "no_persistent_learner_state_write",
        "no_external_nlp_dependency",
        "no_restricted_source_payload_copy",
    ):
        if boundaries.get(field) is not True:
            errors.append(f"scope_boundary_missing:{field}")

    synthetic_decisions = {
        grammar_id: {
            "decision": "APPROVE_TEXT_MODE",
            "reviewer_ref": "SYNTHETIC_OPERATOR_REVIEWER",
            "evidence_ref": f"synthetic-review://{grammar_id}",
        }
        for grammar_id in expected_units
    }
    simulated = apply_review_decisions(
        artifact, synthetic_decisions, simulation=True
    )
    simulation_pass = (
        simulated["coverage_summary"]["approved_text_mode_unit_count"] == 24
        and simulated["coverage_summary"]["text_mode_pilot_eligible_row_count"]
        == 109
        and simulated["release_gates"]["text_mode_private_pilot_gate"][
            "status"
        ]
        == "PASS_READY_FOR_OPERATOR_CONTROLLED_PILOT"
        and simulated["claim_boundaries"]["full_four_skill_release_complete"]
        is False
    )
    if not simulation_pass:
        errors.append("synthetic_all_approved_transition_failed")

    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_text_mode_review_gate_validation",
        "validation_status": status,
        "coverage_summary": expected_summary,
        "gate_checks": {
            "review_queue_24_of_24": len(queue_ids) == 24,
            "review_queue_rows_109_of_109": len(queue_rows) == 109,
            "audio_deferred_non_blocking_for_text_mode": (
                audio_gate.get("blocks_text_mode") is False
            ),
            "actual_operator_decisions_not_fabricated": (
                summary.get("approved_text_mode_unit_count") == 0
            ),
            "synthetic_24_approval_transition": simulation_pass,
            "full_four_skill_release_still_blocked": (
                boundaries.get("full_four_skill_release_complete") is False
            ),
            "no_a2plus_scope": boundaries.get("no_a2_a2plus_expansion")
            is True,
            "no_learner_state_write": boundaries.get(
                "no_persistent_learner_state_write"
            )
            is True,
        },
        "errors": errors,
        "warnings": [
            "Audio, recording, ASR, pronunciation, and fluency work are deferred by operator decision.",
            "Text-mode review may proceed, but no operator approval has been fabricated.",
            "Listening/Speaking remain candidate transcript/prompt paths and are excluded from text-mode promotion evidence.",
        ],
        "stop_reason": (
            "OPERATOR_CONTENT_REVIEW_DECISIONS_REQUIRED"
            if status == "PASS"
            else "VALIDATION_FAILURE"
        ),
        "next_resume_task": NEXT_RESUME_TASK if status == "PASS" else None,
        "validation_mode": "LOCAL_DETERMINISTIC_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    candidate, candidate_report = build_candidate_source()
    cross_skill, cross_skill_report = build_cross_skill_source()
    _require_pass("candidate", candidate_report)
    _require_pass("cross_skill", cross_skill_report)
    artifact = build_artifact(candidate, cross_skill)
    report = validate_artifact(artifact, candidate, cross_skill)
    return artifact, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    artifact, report = build_and_validate_from_repo()
    write_json(args.output, artifact)
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
