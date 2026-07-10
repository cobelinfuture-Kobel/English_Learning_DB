#!/usr/bin/env python3
"""Build deterministic pre-review decisions for A1/A1+ text-mode promotion.

The review is intentionally fail-closed. It does not fabricate operator approval.
It records delegated pedagogical QA recommendations and applies NEEDS_REVISION
when any required content or Reading/Writing evidence dimension is not learner-ready.
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

from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (
    PILOT_UNIT_IDS,
    build_and_validate_from_repo as build_candidate_source,
)
from ulga.builders.build_a1_grammar_text_mode_review_gate import (
    apply_review_decisions,
    build_and_validate_from_repo as build_review_gate_source,
)

TASK_ID = "R7-M105J_A1A1PlusOperatorReviewDecisionIntake"
PROGRAM_ID = "R7-M105_A1A1PlusGrammarLearningClosedLoop"
NEXT_SHORT_STEP = "R7-M105K_A1A1PlusTextModePracticeItemFullFix"
OUTPUT_PATH = REPO_ROOT / "ulga/reviews/a1_grammar_text_mode_review_decisions.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1_grammar_operator_review_decision_intake_validation.json"

GENERIC_PROMPTS = {
    "Choose the option that uses the target grammar correctly.",
    "Choose the target form that matches the short context.",
    "Identify the correctly formed target example.",
    "Complete the target form.",
    "Put the words in the correct order.",
    "Write a sentence for the context using the target grammar.",
    "Select the correct target sentence or phrase.",
    "Produce one sentence or phrase with the target grammar.",
}
PLACEHOLDER_OPTIONS = {
    "Not the target form",
    "Incorrect contrast",
    "Incorrect form",
}


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _activity_findings(unit: Mapping[str, Any]) -> list[str]:
    findings: set[str] = set()
    items = list(unit.get("practice_items", [])) + list(unit.get("assessment_items", []))
    if len(items) != 8:
        findings.add("RW_ACTIVITY_SET_NOT_6_PRACTICE_PLUS_2_ASSESSMENT")
    for item in items:
        prompt = item.get("prompt")
        task_type = item.get("task_type")
        response_mode = item.get("response_mode")
        options = item.get("options", [])
        if prompt in GENERIC_PROMPTS:
            findings.add("RW_PROMPT_IS_GENERIC_TEMPLATE")
        if PLACEHOLDER_OPTIONS.intersection(options):
            findings.add("RW_OPTIONS_CONTAIN_PLACEHOLDER_DISTRACTORS")
        if task_type == "context_match" and not item.get("context"):
            findings.add("RW_CONTEXT_MATCH_HAS_NO_CONTEXT_PAYLOAD")
        if task_type == "gap_fill" and not item.get("gap_spec"):
            findings.add("RW_GAP_FILL_HAS_NO_GAP_SPEC")
        if task_type == "word_order" and not item.get("token_sequence"):
            findings.add("RW_WORD_ORDER_HAS_NO_TOKEN_SEQUENCE")
        if task_type in {"guided_sentence", "checkpoint_write"} and not item.get("scoring_rubric"):
            findings.add("RW_PRODUCTIVE_TASK_HAS_NO_SCORING_RUBRIC")
        if response_mode == "short_text" and not item.get("accepted_variation_policy"):
            findings.add("RW_SHORT_TEXT_HAS_NO_ACCEPTED_VARIATION_POLICY")
    return sorted(findings)


def _content_findings(unit: Mapping[str, Any]) -> list[str]:
    grammar_id = unit["grammar_unit_id"]
    findings: set[str] = set()
    if grammar_id not in PILOT_UNIT_IDS:
        objectives = unit.get("learning_objectives", [])
        if objectives and all(
            value.startswith(("Recognize the form and meaning of", "Produce a controlled A1/A1+ example of"))
            for value in objectives
        ):
            findings.add("LEARNING_OBJECTIVES_ARE_GENERIC_DERIVATIONS")
        explanations = [item.get("explanation", "") for item in unit.get("positive_examples", [])]
        if explanations and all(value.startswith("Validated example of") for value in explanations):
            findings.add("POSITIVE_EXPLANATIONS_ARE_GENERIC_DERIVATIONS")
        diagnoses = [item.get("diagnosis", "") for item in unit.get("common_error_tags", [])]
        if any("does not satisfy the canonical target pattern" in value.lower() for value in diagnoses):
            findings.add("ERROR_DIAGNOSIS_IS_GENERIC_NON_MATCH")
        findings.add("DERIVED_UNIT_REQUIRES_UNIT_SPECIFIC_PEDAGOGICAL_REWRITE")
    if grammar_id == "GRAMMAR_ARTICLES_BASIC":
        findings.add("ARTICLE_NEGATIVE_EXAMPLES_REQUIRE_DISCOURSE_CONTEXT")
        findings.add("DEFINITE_ARTICLE_USE_REQUIRES_IDENTIFIABILITY_CONTEXT")
    return sorted(findings)


def review_unit(unit: Mapping[str, Any]) -> dict[str, Any]:
    grammar_id = unit["grammar_unit_id"]
    content_findings = _content_findings(unit)
    activity_findings = _activity_findings(unit)
    all_findings = sorted(set(content_findings + activity_findings))
    return {
        "grammar_unit_id": grammar_id,
        "decision": "NEEDS_REVISION" if all_findings else "APPROVE_TEXT_MODE",
        "decision_origin": "DELEGATED_PEDAGOGICAL_QA_RECOMMENDATION_NOT_OPERATOR_APPROVAL",
        "reviewer_ref": "assistant:delegated_pedagogical_qa",
        "evidence_ref": f"repo://ulga/reviews/a1_grammar_text_mode_review_decisions.json#{grammar_id}",
        "source_class": "CURATED_PILOT" if grammar_id in PILOT_UNIT_IDS else "RULE_PRIMITIVE_DERIVED",
        "content_findings": content_findings,
        "reading_writing_findings": activity_findings,
        "blocking_findings": all_findings,
        "operator_confirmation_required": True,
    }


def build_artifact(candidate: Mapping[str, Any], review_gate: Mapping[str, Any]) -> dict[str, Any]:
    units = candidate.get("learning_units", [])
    queue = review_gate.get("review_queue", [])
    if len(units) != 24 or len(queue) != 24:
        raise ValueError("source_review_unit_count_not_24")
    unit_ids = {unit["grammar_unit_id"] for unit in units}
    queue_ids = {item["grammar_unit_id"] for item in queue}
    if unit_ids != queue_ids:
        raise ValueError("candidate_review_queue_identity_mismatch")
    decisions = [review_unit(unit) for unit in sorted(units, key=lambda item: item["grammar_unit_id"])]
    decision_map = {
        item["grammar_unit_id"]: {
            "decision": item["decision"],
            "reviewer_ref": item["reviewer_ref"],
            "evidence_ref": item["evidence_ref"],
        }
        for item in decisions
    }
    applied = apply_review_decisions(dict(review_gate), decision_map)
    canonical_rows = set(candidate.get("by_egp_row_id", {}))
    decision_by_id = {item["grammar_unit_id"]: item for item in decisions}
    blocked_rows = {
        row_id
        for unit in units
        if decision_by_id[unit["grammar_unit_id"]]["decision"] != "APPROVE_TEXT_MODE"
        for row_id in unit.get("canonical_egp_row_ids", [])
    }
    summary = {
        "reviewed_unit_count": len(decisions),
        "approved_text_mode_unit_count": sum(item["decision"] == "APPROVE_TEXT_MODE" for item in decisions),
        "needs_revision_unit_count": sum(item["decision"] == "NEEDS_REVISION" for item in decisions),
        "rejected_unit_count": sum(item["decision"] == "REJECT" for item in decisions),
        "canonical_row_count": len(canonical_rows),
        "blocked_row_count": len(blocked_rows),
        "text_mode_pilot_eligible_row_count": len(canonical_rows - blocked_rows),
        "curated_pilot_needs_revision_count": sum(item["source_class"] == "CURATED_PILOT" and item["decision"] == "NEEDS_REVISION" for item in decisions),
        "derived_unit_needs_revision_count": sum(item["source_class"] == "RULE_PRIMITIVE_DERIVED" and item["decision"] == "NEEDS_REVISION" for item in decisions),
    }
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "artifact_id": "a1_grammar_text_mode_review_decisions",
        "artifact_type": "delegated_pedagogical_qa_decision_intake_not_operator_approval",
        "schema_version": "a1_grammar_text_mode_review_decisions.v1",
        "decision_policy": {
            "fail_closed": True,
            "operator_confirmation_required": True,
            "audio_scope": "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE",
            "approval_requires_zero_blocking_findings": True,
        },
        "coverage_summary": summary,
        "decisions": decisions,
        "decision_application_preview": {
            "text_mode_private_pilot_gate": applied["release_gates"]["text_mode_private_pilot_gate"]["status"],
            "audio_scope_gate": applied["release_gates"]["audio_scope_gate"]["status"],
            "full_four_skill_release_complete": applied["claim_boundaries"]["full_four_skill_release_complete"],
        },
        "claim_boundaries": {
            "delegated_qa_complete": True,
            "operator_review_complete": False,
            "operator_approval_fabricated": False,
            "text_mode_private_pilot_eligible": False,
            "audio_scope_complete": False,
            "no_a2_a2plus_expansion": True,
            "no_persistent_learner_state_write": True,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def validate_artifact(artifact: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    decisions = artifact.get("decisions", [])
    summary = artifact.get("coverage_summary", {})
    expected_units = {unit["grammar_unit_id"] for unit in candidate.get("learning_units", [])}
    decision_ids = {item.get("grammar_unit_id") for item in decisions}
    if len(decisions) != 24 or decision_ids != expected_units:
        errors.append("decision_set_not_24_canonical_units")
    if summary.get("canonical_row_count") != 109:
        errors.append("decision_intake_not_109_rows")
    if summary.get("approved_text_mode_unit_count") != 0:
        errors.append("unexpected_text_mode_approval")
    if summary.get("needs_revision_unit_count") != 24:
        errors.append("expected_all_units_needs_revision")
    if summary.get("blocked_row_count") != 109 or summary.get("text_mode_pilot_eligible_row_count") != 0:
        errors.append("text_mode_rows_not_fail_closed")
    for item in decisions:
        if item.get("decision") != "NEEDS_REVISION":
            errors.append(f"unexpected_decision:{item.get('grammar_unit_id')}")
        if not item.get("blocking_findings"):
            errors.append(f"missing_blocking_findings:{item.get('grammar_unit_id')}")
        if item.get("operator_confirmation_required") is not True:
            errors.append(f"operator_confirmation_not_required:{item.get('grammar_unit_id')}")
    boundaries = artifact.get("claim_boundaries", {})
    if boundaries.get("operator_review_complete") is not False:
        errors.append("false_operator_review_complete")
    if boundaries.get("operator_approval_fabricated") is not False:
        errors.append("operator_approval_fabricated")
    preview = artifact.get("decision_application_preview", {})
    if preview.get("text_mode_private_pilot_gate") != "BLOCKED_PENDING_FULL_TEXT_REVIEW_APPROVAL":
        errors.append("text_mode_gate_not_blocked")
    if preview.get("audio_scope_gate") != "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE":
        errors.append("audio_defer_policy_drift")
    status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "validation_status": status,
        "coverage_summary": summary,
        "gate_checks": {
            "decisions_24_of_24": len(decisions) == 24,
            "rows_109_of_109": summary.get("canonical_row_count") == 109,
            "all_needs_revision": summary.get("needs_revision_unit_count") == 24,
            "text_mode_gate_blocked": preview.get("text_mode_private_pilot_gate") == "BLOCKED_PENDING_FULL_TEXT_REVIEW_APPROVAL",
            "audio_remains_deferred": preview.get("audio_scope_gate") == "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE",
            "operator_approval_not_fabricated": boundaries.get("operator_approval_fabricated") is False,
        },
        "errors": errors,
        "stop_reason": "NONE" if status == "PASS" else "VALIDATION_FAILURE",
        "next_short_step": NEXT_SHORT_STEP if status == "PASS" else None,
        "validation_mode": "LOCAL_DETERMINISTIC_CI_NOT_VERIFIED",
    }


def build_and_validate_from_repo() -> tuple[dict[str, Any], dict[str, Any]]:
    candidate, candidate_report = build_candidate_source()
    review_gate, review_gate_report = build_review_gate_source()
    if candidate_report.get("validation_status") != "PASS":
        raise RuntimeError("candidate_source_validation_failed")
    if review_gate_report.get("validation_status") != "PASS":
        raise RuntimeError("review_gate_source_validation_failed")
    artifact = build_artifact(candidate, review_gate)
    report = validate_artifact(artifact, candidate)
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
