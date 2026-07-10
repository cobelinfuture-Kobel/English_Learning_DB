#!/usr/bin/env python3
"""Re-review the full-fixed A1/A1+ text-mode content without fabricating approval."""

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

from ulga.builders.build_a1_grammar_derived_pedagogy_fullfix import (
    build_and_validate_from_repo as build_fullfix_source,
)
from ulga.builders.build_a1_grammar_text_mode_practice_item_fullfix import (
    GENERIC_PROMPTS,
    PLACEHOLDER_OPTIONS,
)

TASK_ID = "R7-M105M_A1A1PlusTextModeReReviewAndPromotionGate"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_RESUME_TASK = "R7-M105N_A1A1PlusOperatorConfirmationAndTextModePrivatePilotIntegration"
OUTPUT_PATH = REPO_ROOT / "ulga/reviews/a1_grammar_text_mode_rereview_recommendations.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_grammar_text_mode_rereview_gate_validation.json"

RECOMMEND_APPROVE = "RECOMMEND_APPROVE_TEXT_MODE"
RECOMMEND_MANUAL = "RECOMMEND_OPERATOR_MANUAL_REVIEW"
RECOMMEND_REVISION = "RECOMMEND_NEEDS_REVISION"


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _item_blockers(item: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    item_id = item.get("item_id", "UNKNOWN")
    if item.get("prompt") in GENERIC_PROMPTS:
        blockers.append(f"GENERIC_PROMPT_REMAINS:{item_id}")
    if PLACEHOLDER_OPTIONS.intersection(item.get("options", [])):
        blockers.append(f"PLACEHOLDER_OPTION_REMAINS:{item_id}")
    task_type = item.get("task_type")
    if task_type == "context_choice" and not item.get("context"):
        blockers.append(f"CONTEXT_PAYLOAD_MISSING:{item_id}")
    if task_type == "structured_gap_fill" and not item.get("gap_spec"):
        blockers.append(f"GAP_SPEC_MISSING:{item_id}")
    if task_type == "structured_word_order" and not item.get("token_sequence"):
        blockers.append(f"TOKEN_SEQUENCE_MISSING:{item_id}")
    if task_type == "structured_morphology_build" and not item.get("morphology_parts"):
        blockers.append(f"MORPHOLOGY_PARTS_MISSING:{item_id}")
    if item.get("skill") == "writing" and not item.get("accepted_variation_policy"):
        blockers.append(f"ACCEPTED_VARIATION_POLICY_MISSING:{item_id}")
    if task_type in {"guided_contextual_writing", "text_mode_writing_checkpoint"} and not item.get("scoring_rubric"):
        blockers.append(f"SCORING_RUBRIC_MISSING:{item_id}")
    source = item.get("source_trace", {})
    if source.get("raw_external_source_text_copied") is not False:
        blockers.append(f"RAW_EXTERNAL_TEXT_BOUNDARY_UNSAFE:{item_id}")
    if source.get("restricted_source_payload_persisted") is not False:
        blockers.append(f"RESTRICTED_SOURCE_BOUNDARY_UNSAFE:{item_id}")
    return blockers


def audit_unit(unit: Mapping[str, Any], known_gaps: list[Mapping[str, Any]]) -> dict[str, Any]:
    grammar_id = unit["grammar_unit_id"]
    blockers: list[str] = []
    objectives = unit.get("learning_objectives", [])
    if len(objectives) < 2:
        blockers.append("LEARNING_OBJECTIVE_MINIMUM_NOT_MET")
    if any(value.startswith("Recognize the form and meaning of") for value in objectives):
        blockers.append("GENERIC_LEARNING_OBJECTIVE_REMAINS")
    if len(unit.get("form_rules", [])) < 1:
        blockers.append("FORM_RULE_MISSING")
    if len(unit.get("meaning_functions", [])) < 1:
        blockers.append("MEANING_FUNCTION_MISSING")
    if len(unit.get("usage_conditions", [])) < 2:
        blockers.append("USAGE_CONDITION_MINIMUM_NOT_MET")
    if len(unit.get("positive_examples", [])) < 2:
        blockers.append("POSITIVE_EXAMPLE_MINIMUM_NOT_MET")
    if len(unit.get("negative_examples", [])) < 3:
        blockers.append("NEGATIVE_EXAMPLE_MINIMUM_NOT_MET")
    if len(unit.get("common_error_tags", [])) < 3:
        blockers.append("COMMON_ERROR_TAG_MINIMUM_NOT_MET")
    for example in unit.get("positive_examples", []):
        if example.get("explanation", "").startswith("Validated example of"):
            blockers.append("GENERIC_POSITIVE_EXPLANATION_REMAINS")
    for error in unit.get("common_error_tags", []):
        if "does not satisfy the canonical target pattern" in error.get("diagnosis", "").lower():
            blockers.append("GENERIC_ERROR_DIAGNOSIS_REMAINS")
    practice = unit.get("practice_items", [])
    assessments = unit.get("assessment_items", [])
    if len(practice) != 6:
        blockers.append("PRACTICE_ITEM_COUNT_NOT_6")
    if len(assessments) != 2:
        blockers.append("ASSESSMENT_ITEM_COUNT_NOT_2")
    for item in practice + assessments:
        blockers.extend(_item_blockers(item))

    manual_reasons = [
        gap["gap_id"]
        for gap in known_gaps
        if gap.get("grammar_unit_id") == grammar_id
    ]
    if blockers:
        recommendation = RECOMMEND_REVISION
    elif manual_reasons:
        recommendation = RECOMMEND_MANUAL
    else:
        recommendation = RECOMMEND_APPROVE
    return {
        "grammar_unit_id": grammar_id,
        "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
        "recommendation": recommendation,
        "remediation_blockers": sorted(set(blockers)),
        "manual_review_reasons": manual_reasons,
        "evidence_refs": {
            "pedagogy_fullfix": f"repo://ulga/graph/a1_grammar_derived_pedagogy_fullfix.json#{grammar_id}",
            "text_mode_items": [item["item_id"] for item in practice + assessments],
        },
        "operator_decision": None,
        "operator_reviewer_ref": None,
        "operator_evidence_ref": None,
        "operator_confirmation_required": True,
    }


def build_artifact(fullfix: Mapping[str, Any]) -> dict[str, Any]:
    units = fullfix.get("learning_units", [])
    rows = fullfix.get("by_egp_row_id", {})
    if len(units) != 24 or len(rows) != 109:
        raise ValueError("rereview_source_not_24_units_109_rows")
    known_gaps = list(fullfix.get("known_validator_gaps", []))
    recommendations = [
        audit_unit(unit, known_gaps)
        for unit in sorted(units, key=lambda item: item["grammar_unit_id"])
    ]
    counts = {
        RECOMMEND_APPROVE: sum(item["recommendation"] == RECOMMEND_APPROVE for item in recommendations),
        RECOMMEND_MANUAL: sum(item["recommendation"] == RECOMMEND_MANUAL for item in recommendations),
        RECOMMEND_REVISION: sum(item["recommendation"] == RECOMMEND_REVISION for item in recommendations),
    }
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_text_mode_rereview_recommendations",
        "artifact_type": "delegated_rereview_recommendations_not_operator_decisions",
        "schema_version": "a1_grammar_text_mode_rereview_recommendations.v1",
        "coverage_summary": {
            "canonical_unit_count": 24,
            "canonical_row_count": 109,
            "recommend_approve_unit_count": counts[RECOMMEND_APPROVE],
            "recommend_manual_review_unit_count": counts[RECOMMEND_MANUAL],
            "recommend_revision_unit_count": counts[RECOMMEND_REVISION],
            "operator_confirmed_unit_count": 0,
            "operator_approved_unit_count": 0,
            "text_mode_pilot_eligible_row_count": 0,
            "known_validator_gap_count": len(known_gaps),
        },
        "recommendations": recommendations,
        "release_gates": {
            "fullfix_remediation_gate": {
                "status": "PASS" if counts[RECOMMEND_REVISION] == 0 else "BLOCKED",
            },
            "delegated_rereview_gate": {"status": "PASS"},
            "operator_confirmation_gate": {
                "status": "BLOCKED_PENDING_OPERATOR_DECISIONS",
            },
            "text_mode_private_pilot_gate": {
                "status": "BLOCKED_PENDING_OPERATOR_CONFIRMATION",
            },
            "audio_scope_gate": {
                "status": "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE",
                "blocks_text_mode": False,
                "blocks_full_four_skill_release": True,
            },
            "full_four_skill_release_gate": {
                "status": "BLOCKED_AUDIO_AND_REAL_EVIDENCE_DEFERRED",
            },
        },
        "claim_boundaries": {
            "delegated_rereview_complete": True,
            "fullfix_remediation_complete": counts[RECOMMEND_REVISION] == 0,
            "operator_review_complete": False,
            "operator_approval_fabricated": False,
            "text_mode_private_pilot_eligible": False,
            "audio_scope_deferred": True,
            "audio_scope_complete": False,
            "full_four_skill_release_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_persistent_learner_state_write": True,
        },
        "continuation_gate": {
            "status": "BLOCKED_REQUIRES_OPERATOR_CONFIRMATION",
            "blocker_type": "HUMAN_REVIEW_EVIDENCE_REQUIRED",
            "next_resume_task": NEXT_RESUME_TASK,
        },
    }


def validate_artifact(artifact: Mapping[str, Any], fullfix: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    recommendations = artifact.get("recommendations", [])
    summary = artifact.get("coverage_summary", {})
    expected_units = {unit["grammar_unit_id"] for unit in fullfix.get("learning_units", [])}
    actual_units = {item.get("grammar_unit_id") for item in recommendations}
    if len(recommendations) != 24 or actual_units != expected_units:
        errors.append("rereview_recommendation_set_not_24")
    if summary.get("canonical_row_count") != 109:
        errors.append("rereview_row_count_not_109")
    if summary.get("recommend_approve_unit_count") != 23:
        errors.append("expected_23_approve_recommendations")
    if summary.get("recommend_manual_review_unit_count") != 1:
        errors.append("expected_1_manual_review_recommendation")
    if summary.get("recommend_revision_unit_count") != 0:
        errors.append("unexpected_remaining_revision_recommendation")
    for item in recommendations:
        if item.get("operator_confirmation_required") is not True:
            errors.append(f"operator_confirmation_not_required:{item.get('grammar_unit_id')}")
        if any(item.get(field) is not None for field in ("operator_decision", "operator_reviewer_ref", "operator_evidence_ref")):
            errors.append(f"operator_decision_fabricated:{item.get('grammar_unit_id')}")
        if item.get("recommendation") == RECOMMEND_REVISION and not item.get("remediation_blockers"):
            errors.append(f"revision_without_blockers:{item.get('grammar_unit_id')}")
        if item.get("recommendation") == RECOMMEND_MANUAL and not item.get("manual_review_reasons"):
            errors.append(f"manual_review_without_reason:{item.get('grammar_unit_id')}")
    article = next((item for item in recommendations if item.get("grammar_unit_id") == "GRAMMAR_ARTICLES_BASIC"), None)
    if not article or article.get("recommendation") != RECOMMEND_MANUAL:
        errors.append("articles_not_routed_to_manual_review")
    gates = artifact.get("release_gates", {})
    if gates.get("fullfix_remediation_gate", {}).get("status") != "PASS":
        errors.append("fullfix_remediation_gate_not_pass")
    if gates.get("operator_confirmation_gate", {}).get("status") != "BLOCKED_PENDING_OPERATOR_DECISIONS":
        errors.append("operator_confirmation_gate_not_blocked")
    if gates.get("text_mode_private_pilot_gate", {}).get("status") != "BLOCKED_PENDING_OPERATOR_CONFIRMATION":
        errors.append("text_mode_pilot_gate_forged_open")
    if gates.get("audio_scope_gate", {}).get("status") != "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE":
        errors.append("audio_defer_policy_drift")
    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("operator_review_complete") is not False:
        errors.append("false_operator_review_completion")
    if boundaries.get("operator_approval_fabricated") is not False:
        errors.append("operator_approval_fabricated")
    if boundaries.get("text_mode_private_pilot_eligible") is not False:
        errors.append("false_text_mode_pilot_eligibility")
    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "validation_status": status,
        "coverage_summary": summary,
        "gate_checks": {
            "recommendations_24_of_24": len(recommendations) == 24,
            "rows_109_of_109": summary.get("canonical_row_count") == 109,
            "remediation_blockers_cleared": summary.get("recommend_revision_unit_count") == 0,
            "approve_recommendations_23": summary.get("recommend_approve_unit_count") == 23,
            "articles_manual_review_required": article is not None and article.get("recommendation") == RECOMMEND_MANUAL,
            "operator_decisions_not_fabricated": boundaries.get("operator_approval_fabricated") is False,
            "text_mode_pilot_gate_blocked": gates.get("text_mode_private_pilot_gate", {}).get("status") == "BLOCKED_PENDING_OPERATOR_CONFIRMATION",
            "audio_remains_deferred": gates.get("audio_scope_gate", {}).get("status") == "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE",
        },
        "errors": errors,
        "warnings": [
            "Recommendations are delegated QA results, not operator decisions.",
            "GRAMMAR_ARTICLES_BASIC requires manual review because article-number agreement is not implemented in the offline validator.",
        ],
        "stop_reason": "OPERATOR_REVIEW_CONFIRMATION_REQUIRED" if status == "PASS" else "VALIDATION_FAILURE",
        "blocker_type": "HUMAN_REVIEW_EVIDENCE_REQUIRED" if status == "PASS" else "VALIDATION_FAILURE",
        "next_resume_task": NEXT_RESUME_TASK if status == "PASS" else None,
        "validation_mode": "STATIC_CONTRACT_REVIEW_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    fullfix, fullfix_report = build_fullfix_source()
    if fullfix_report.get("validation_status") not in {"PASS", "PASS_STATIC_CONTRACT_REVIEW"}:
        raise RuntimeError("fullfix_source_validation_failed")
    artifact = build_artifact(fullfix)
    report = validate_artifact(artifact, fullfix)
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
