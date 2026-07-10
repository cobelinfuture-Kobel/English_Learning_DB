#!/usr/bin/env python3
"""Apply conditional operator approval after the article validator FullFix.

The resulting artifact opens only the Reading/Writing text-mode private-pilot
eligibility gate. Audio, real learner evidence, persistence, and production
runtime remain explicitly outside this milestone.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_derived_pedagogy_fullfix import (
    build_artifact as build_pedagogy_artifact,
)
from ulga.builders.build_a1_grammar_text_mode_practice_item_fullfix import (
    build_and_validate_from_repo as build_practice_source,
)
from ulga.query.a1_canonical_validator_dispatcher import validate as dispatch_validate

TASK_ID = "R7-M105N_A1A1PlusOperatorConfirmationAndTextModePrivatePilotIntegration"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_SHORT_STEP = "R7-M105O_A1A1PlusTextModePrivatePilotPackageIntegration"

RECOMMENDATIONS_PATH = (
    REPO_ROOT / "ulga/reviews/a1_grammar_text_mode_rereview_recommendations.json"
)
CONFIRMATIONS_PATH = (
    REPO_ROOT / "ulga/reviews/a1_grammar_text_mode_operator_confirmations.json"
)
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1_grammar_text_mode_pilot_promotion.json"
REPORT_PATH = (
    REPO_ROOT
    / "ulga/reports/a1_grammar_text_mode_operator_confirmation_validation.json"
)

ARTICLE_GRAMMAR_ID = "GRAMMAR_ARTICLES_BASIC"
ARTICLE_GATE_CASES = (
    ("a cat", True),
    ("an apple", True),
    ("the book", True),
    ("the books", True),
    ("a bus", True),
    ("a class", True),
    ("an address", True),
    ("a red book", True),
    ("a books", False),
    ("an apples", False),
    ("a children", False),
    ("a red books", False),
    ("apple", False),
    ("two cats", False),
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def article_gate_results() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for text, expected in ARTICLE_GATE_CASES:
        decision = dispatch_validate(ARTICLE_GRAMMAR_ID, text)
        passed = (
            decision.get("dispatch_status") == "VALIDATOR_EXECUTED"
            and decision.get("match") is expected
        )
        results.append(
            {
                "text": text,
                "expected_match": expected,
                "actual_match": decision.get("match"),
                "reason": decision.get("reason"),
                "dispatch_status": decision.get("dispatch_status"),
                "status": "PASS" if passed else "FAIL",
            }
        )
    return results


def _validated_sources() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    practice, practice_report = build_practice_source()
    if practice_report.get("validation_status") != "PASS":
        raise RuntimeError("practice_fullfix_source_validation_failed")
    pedagogy = build_pedagogy_artifact(practice)
    if len(pedagogy.get("learning_units", [])) != 24:
        raise RuntimeError("pedagogy_rebuild_not_24_units")
    if len(pedagogy.get("by_egp_row_id", {})) != 109:
        raise RuntimeError("pedagogy_rebuild_not_109_rows")
    return (
        pedagogy,
        load_json(RECOMMENDATIONS_PATH),
        load_json(CONFIRMATIONS_PATH),
    )


def _unit_ids(items: list[Mapping[str, Any]]) -> set[str]:
    return {
        item["grammar_unit_id"]
        for item in items
        if isinstance(item.get("grammar_unit_id"), str)
    }


def build_artifact(
    pedagogy: Mapping[str, Any],
    recommendations: Mapping[str, Any],
    confirmations: Mapping[str, Any],
) -> dict[str, Any]:
    units = pedagogy.get("learning_units", [])
    unit_ids = _unit_ids(units)
    row_ids = set(pedagogy.get("by_egp_row_id", {}))
    recommendation_items = recommendations.get("recommendations", [])
    recommendation_ids = _unit_ids(recommendation_items)
    approved_ids = set(confirmations.get("approved_unit_ids", []))

    if len(units) != 24 or len(unit_ids) != 24:
        raise ValueError("promotion_source_not_24_units")
    if len(row_ids) != 109:
        raise ValueError("promotion_source_not_109_rows")
    if recommendation_ids != unit_ids or approved_ids != unit_ids:
        raise ValueError("operator_confirmation_unit_identity_mismatch")
    if confirmations.get("decision") != (
        "APPROVE_TEXT_MODE_AFTER_ARTICLES_VALIDATOR_FULLFIX"
    ):
        raise ValueError("operator_confirmation_decision_invalid")
    if not confirmations.get("operator_reviewer_ref"):
        raise ValueError("operator_reviewer_ref_missing")
    if not confirmations.get("operator_evidence_ref"):
        raise ValueError("operator_evidence_ref_missing")

    gate_results = article_gate_results()
    failures = [item for item in gate_results if item["status"] != "PASS"]
    if failures:
        raise ValueError(
            "article_number_agreement_fullfix_precondition_failed:"
            + json.dumps(failures, ensure_ascii=False)
        )

    recommendation_by_id = {
        item["grammar_unit_id"]: item for item in recommendation_items
    }
    prior_article = recommendation_by_id[ARTICLE_GRAMMAR_ID]
    if "ARTICLE_NUMBER_AGREEMENT_GATE_NOT_IMPLEMENTED" not in prior_article.get(
        "manual_review_reasons", []
    ):
        raise ValueError("prior_article_validator_gap_not_traceable")

    approvals: list[dict[str, Any]] = []
    by_unit: dict[str, dict[str, Any]] = {}
    for unit in sorted(units, key=lambda value: value["grammar_unit_id"]):
        grammar_id = unit["grammar_unit_id"]
        approval: dict[str, Any] = {
            "grammar_unit_id": grammar_id,
            "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
            "delegated_recommendation_before_confirmation": (
                recommendation_by_id[grammar_id].get("recommendation")
            ),
            "operator_decision": "APPROVE_TEXT_MODE",
            "operator_reviewer_ref": confirmations["operator_reviewer_ref"],
            "operator_evidence_ref": confirmations["operator_evidence_ref"],
            "precondition_status": "PASS",
            "text_mode_private_pilot_eligible": True,
        }
        if grammar_id == ARTICLE_GRAMMAR_ID:
            approval["resolved_validator_gap"] = (
                "ARTICLE_NUMBER_AGREEMENT_GATE_NOT_IMPLEMENTED"
            )
            approval["resolution_status"] = (
                "RESOLVED_BY_CANONICAL_DISPATCHER_FULLFIX"
            )
        approvals.append(approval)
        by_unit[grammar_id] = {
            "grammar_unit_id": grammar_id,
            "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
            "operator_review_status": "APPROVED_TEXT_MODE",
            "text_mode_private_pilot_status": "ELIGIBLE_NOT_STARTED",
            "audio_scope_status": "DEFERRED",
        }

    by_row = {
        row_id: {
            "egp_row_id": row_id,
            "grammar_unit_ids": list(
                pedagogy["by_egp_row_id"][row_id]["grammar_unit_ids"]
            ),
            "operator_text_mode_approval_status": "APPROVED",
            "text_mode_private_pilot_status": "ELIGIBLE_NOT_STARTED",
            "actual_learner_evidence_status": "NOT_COLLECTED",
        }
        for row_id in sorted(row_ids)
    }

    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_text_mode_pilot_promotion",
        "artifact_type": "operator_confirmed_text_mode_private_pilot_gate",
        "schema_version": "a1_grammar_text_mode_pilot_promotion.v1",
        "operator_decision": {
            "operator_decision_id": confirmations["operator_decision_id"],
            "decision": confirmations["decision"],
            "operator_reviewer_ref": confirmations["operator_reviewer_ref"],
            "operator_evidence_ref": confirmations["operator_evidence_ref"],
            "preconditions_satisfied": True,
        },
        "article_validator_fullfix": {
            "grammar_unit_id": ARTICLE_GRAMMAR_ID,
            "canonical_dispatcher_route_status": "FULLFIX_ACTIVE",
            "previous_gap_count": 1,
            "remaining_gap_count": 0,
            "case_results": gate_results,
        },
        "coverage_summary": {
            "canonical_unit_count": 24,
            "canonical_row_count": 109,
            "operator_confirmed_unit_count": 24,
            "operator_approved_unit_count": 24,
            "text_mode_pilot_eligible_unit_count": 24,
            "text_mode_pilot_eligible_row_count": 109,
            "article_validator_case_count": len(gate_results),
            "article_validator_failed_case_count": 0,
            "known_validator_gap_count": 0,
            "actual_learner_attempt_count": 0,
            "actual_mastery_measured_row_count": 0,
            "rendered_listening_audio_asset_count": 0,
            "captured_speaking_audio_asset_count": 0,
        },
        "approvals": approvals,
        "by_grammar_unit_id": by_unit,
        "by_egp_row_id": by_row,
        "release_gates": {
            "article_number_agreement_validator_gate": "PASS",
            "delegated_rereview_gate": "PASS",
            "operator_confirmation_gate": "PASS",
            "text_mode_private_pilot_gate": (
                "PASS_READY_FOR_OPERATOR_CONTROLLED_PILOT"
            ),
            "actual_learner_evidence_gate": "BLOCKED_NOT_COLLECTED",
            "audio_scope_gate": "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE",
            "full_four_skill_release_gate": (
                "BLOCKED_AUDIO_AND_REAL_EVIDENCE_DEFERRED"
            ),
            "production_runtime_gate": "BLOCKED_NOT_APPROVED",
        },
        "claim_boundaries": {
            "article_number_agreement_validator_fullfix_complete": True,
            "operator_text_review_complete": True,
            "text_mode_private_pilot_eligible": True,
            "text_mode_private_pilot_started": False,
            "actual_learner_evidence_complete": False,
            "audio_scope_deferred": True,
            "audio_scope_complete": False,
            "full_four_skill_release_complete": False,
            "production_runtime_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_persistent_learner_state_write": True,
        },
        "continuation_gate": {
            "status": "TEXT_MODE_PRIVATE_PILOT_ELIGIBLE",
            "blocker_type": None,
            "next_short_step": NEXT_SHORT_STEP,
        },
    }


def validate_artifact(
    artifact: Mapping[str, Any],
    pedagogy: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    summary = artifact.get("coverage_summary", {})
    if len(artifact.get("by_grammar_unit_id", {})) != 24:
        errors.append("promotion_unit_index_not_24")
    if len(artifact.get("by_egp_row_id", {})) != 109:
        errors.append("promotion_row_index_not_109")
    if set(artifact.get("by_egp_row_id", {})) != set(
        pedagogy.get("by_egp_row_id", {})
    ):
        errors.append("promotion_row_identity_mismatch")
    if len(artifact.get("approvals", [])) != 24:
        errors.append("operator_approval_count_not_24")

    for approval in artifact.get("approvals", []):
        grammar_id = approval.get("grammar_unit_id")
        if approval.get("operator_decision") != "APPROVE_TEXT_MODE":
            errors.append(f"unit_not_operator_approved:{grammar_id}")
        if not approval.get("operator_reviewer_ref"):
            errors.append(f"unit_reviewer_ref_missing:{grammar_id}")
        if not approval.get("operator_evidence_ref"):
            errors.append(f"unit_evidence_ref_missing:{grammar_id}")
        if approval.get("text_mode_private_pilot_eligible") is not True:
            errors.append(f"unit_not_pilot_eligible:{grammar_id}")

    article_results = artifact.get("article_validator_fullfix", {}).get(
        "case_results", []
    )
    if len(article_results) != len(ARTICLE_GATE_CASES):
        errors.append("article_validator_case_count_mismatch")
    if any(item.get("status") != "PASS" for item in article_results):
        errors.append("article_validator_fullfix_case_failure")
    if summary.get("known_validator_gap_count") != 0:
        errors.append("article_validator_gap_not_cleared")
    if summary.get("operator_approved_unit_count") != 24:
        errors.append("operator_approved_unit_count_not_24")
    if summary.get("text_mode_pilot_eligible_row_count") != 109:
        errors.append("text_mode_pilot_eligible_row_count_not_109")

    gates = artifact.get("release_gates", {})
    if gates.get("article_number_agreement_validator_gate") != "PASS":
        errors.append("article_validator_gate_not_pass")
    if gates.get("operator_confirmation_gate") != "PASS":
        errors.append("operator_confirmation_gate_not_pass")
    if gates.get("text_mode_private_pilot_gate") != (
        "PASS_READY_FOR_OPERATOR_CONTROLLED_PILOT"
    ):
        errors.append("text_mode_private_pilot_gate_not_pass")
    if gates.get("audio_scope_gate") != (
        "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE"
    ):
        errors.append("audio_scope_defer_boundary_drift")

    boundaries = artifact.get("claim_boundaries", {})
    for field in (
        "article_number_agreement_validator_fullfix_complete",
        "operator_text_review_complete",
        "text_mode_private_pilot_eligible",
        "audio_scope_deferred",
        "no_a2_a2plus_expansion",
        "no_persistent_learner_state_write",
    ):
        if boundaries.get(field) is not True:
            errors.append(f"required_true_boundary_missing:{field}")
    for field in (
        "text_mode_private_pilot_started",
        "actual_learner_evidence_complete",
        "audio_scope_complete",
        "full_four_skill_release_complete",
        "production_runtime_complete",
    ):
        if boundaries.get(field) is not False:
            errors.append(f"false_completion_claim:{field}")

    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "validation_status": status,
        "coverage_summary": summary,
        "gate_checks": {
            "article_validator_fullfix_active": not any(
                item.get("status") != "PASS" for item in article_results
            ),
            "units_24_of_24_operator_approved": (
                summary.get("operator_approved_unit_count") == 24
            ),
            "rows_109_of_109_text_mode_pilot_eligible": (
                summary.get("text_mode_pilot_eligible_row_count") == 109
            ),
            "audio_remains_deferred": (
                boundaries.get("audio_scope_deferred") is True
                and boundaries.get("audio_scope_complete") is False
            ),
            "real_learner_evidence_not_claimed": (
                boundaries.get("actual_learner_evidence_complete") is False
            ),
        },
        "errors": errors,
        "warnings": [
            "Text-mode private pilot is eligible but has not started.",
            "Audio, persistence, and production runtime remain outside scope.",
        ],
        "stop_reason": "NONE" if status == "PASS" else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if status == "PASS" else None,
        "validation_mode": (
            "LOCAL_ISOLATED_LOGIC_AND_STATIC_INTEGRATION_REVIEW_CI_NOT_VERIFIED"
        ),
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    pedagogy, recommendations, confirmations = _validated_sources()
    artifact = build_artifact(pedagogy, recommendations, confirmations)
    report = validate_artifact(artifact, pedagogy)
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
