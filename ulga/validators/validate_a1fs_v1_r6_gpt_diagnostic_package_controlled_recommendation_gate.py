#!/usr/bin/env python3
"""Independent validator for R6 diagnostic requests, responses, and gated queue."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r6_gpt_diagnostic_package_controlled_recommendation_gate as r6


def _safe_errors(value: Any) -> list[str]:
    try:
        r6.safe_scan(value)
    except r6.DiagnosticGateError as exc:
        return [str(exc)]
    return []


def validate_request(
    *, evidence_package_path: Path, evidence_safe_path: Path, bank_path: Path,
    coverage_path: Path, request_path: Path, safe_request_path: Path,
    max_representatives_per_cell: int = 6,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        request = r6.read_json(request_path, "request")
        safe = r6.read_json(safe_request_path, "safe_request")
        expected_request, expected_safe = r6.build_request(
            evidence_package_path=evidence_package_path,
            evidence_safe_path=evidence_safe_path,
            bank_path=bank_path,
            coverage_path=coverage_path,
            max_representatives_per_cell=max_representatives_per_cell,
        )
    except (OSError, json.JSONDecodeError, r6.DiagnosticGateError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"request_rebuild_failed:{exc}"]}
    if request != expected_request:
        errors.append("request_rebuild_drift")
    if safe != expected_safe:
        errors.append("safe_request_rebuild_drift")
    request_core = {key: value for key, value in request.items() if key != "request_sha256"}
    safe_core = {key: value for key, value in safe.items() if key != "summary_sha256"}
    if request.get("request_sha256") != r6.digest(request_core):
        errors.append("request_digest_invalid")
    if safe.get("summary_sha256") != r6.digest(safe_core):
        errors.append("safe_request_digest_invalid")
    if request.get("task_id") != r6.TASK_ID or request.get("schema_version") != r6.REQUEST_SCHEMA_VERSION:
        errors.append("request_identity_invalid")
    if safe.get("task_id") != r6.TASK_ID or safe.get("schema_version") != r6.SAFE_SCHEMA_VERSION:
        errors.append("safe_request_identity_invalid")
    if request.get("analysis_role") != "DIAGNOSTIC_CANDIDATE_ONLY":
        errors.append("analysis_role_invalid")
    if request.get("private_local_only") is not True:
        errors.append("request_privacy_invalid")
    if request.get("learner_ref_sha256") != safe.get("learner_ref_sha256"):
        errors.append("learner_hash_binding_invalid")
    evidence = request.get("representative_evidence", [])
    refs = [row.get("evidence_ref") for row in evidence]
    if len(refs) != len(set(refs)) or None in refs:
        errors.append("evidence_ref_identity_invalid")
    if request.get("analysis_window", {}).get("representative_evidence_count") != len(evidence):
        errors.append("representative_count_invalid")
    if safe.get("representative_evidence_refs") != refs:
        errors.append("safe_evidence_ref_drift")
    if safe.get("representative_evidence_hashes") != [r6.digest(row) for row in evidence]:
        errors.append("safe_evidence_hash_drift")
    prohibited = request.get("prohibited_actions", {})
    required_prohibited = {
        "mastery_write", "score_override", "canonical_authority_write",
        "practice_bank_write", "active_planner_policy_write", "a2_unlock",
    }
    if set(prohibited) != required_prohibited or any(prohibited.get(key) is not True for key in required_prohibited):
        errors.append("prohibited_actions_invalid")
    boundaries = safe.get("claim_boundaries", {})
    for key in (
        "raw_response_included", "prompt_included", "expected_answer_included",
        "learner_identity_included", "model_invoked", "mastery_written",
        "canonical_written", "a2_unlocked",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"safe_claim_boundary_broken:{key}")
    errors.extend(_safe_errors(safe))
    return {
        "validation_status": r6.STATUS if not errors else "FAIL_A1FS_V1_R6_REQUEST_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "representative_evidence_count": len(evidence),
        "next_short_step": r6.NEXT_SHORT_STEP if not errors else r6.TASK_ID,
    }


def validate_response_files(*, request_path: Path, response_path: Path, coverage_path: Path) -> dict[str, Any]:
    try:
        request = r6.read_json(request_path, "request")
        response = r6.read_json(response_path, "response")
        coverage = r6._load_coverage(coverage_path)
    except r6.DiagnosticGateError as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"response_source_invalid:{exc}"]}
    return r6.validate_response(request=request, response=response, coverage=coverage)


def validate_gate(
    *, request_path: Path, response_path: Path, decisions_path: Path,
    coverage_path: Path, queue_path: Path, report_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        request = r6.read_json(request_path, "request")
        response = r6.read_json(response_path, "response")
        decisions = r6.read_json(decisions_path, "decisions")
        coverage = r6._load_coverage(coverage_path)
        queue = r6.read_json(queue_path, "queue")
        report = r6.read_json(report_path, "report")
        expected_queue, expected_report = r6.apply_gate(
            request=request, response=response, decisions=decisions, coverage=coverage,
        )
    except (OSError, json.JSONDecodeError, r6.DiagnosticGateError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"gate_rebuild_failed:{exc}"]}
    if queue != expected_queue:
        errors.append("queue_rebuild_drift")
    if report != expected_report:
        errors.append("report_rebuild_drift")
    queue_core = {key: value for key, value in queue.items() if key != "queue_sha256"}
    report_core = {key: value for key, value in report.items() if key != "report_sha256"}
    if queue.get("queue_sha256") != r6.digest(queue_core):
        errors.append("queue_digest_invalid")
    if report.get("report_sha256") != r6.digest(report_core):
        errors.append("report_digest_invalid")
    if queue.get("task_id") != r6.TASK_ID or queue.get("schema_version") != r6.QUEUE_SCHEMA_VERSION:
        errors.append("queue_identity_invalid")
    if report.get("task_id") != r6.TASK_ID or report.get("schema_version") != r6.REPORT_SCHEMA_VERSION:
        errors.append("report_identity_invalid")
    if queue.get("validation_status") != r6.STATUS or report.get("validation_status") != r6.STATUS:
        errors.append("gate_status_invalid")
    if queue.get("private_local_only") is not True:
        errors.append("queue_privacy_invalid")
    candidates = queue.get("candidates", [])
    candidate_ids = [row.get("recommendation_id") for row in candidates]
    if queue.get("candidate_count") != len(candidates) or len(candidate_ids) != len(set(candidate_ids)):
        errors.append("candidate_denominator_invalid")
    for row in candidates:
        if row.get("activation_state") != "CANDIDATE_ONLY_NOT_ACTIVE":
            errors.append(f"candidate_activation_state_invalid:{row.get('recommendation_id')}")
        gate = row.get("gate", {})
        if gate.get("decision") != "APPROVE_AS_CANDIDATE":
            errors.append(f"candidate_gate_decision_invalid:{row.get('recommendation_id')}")
        criteria = gate.get("criteria", {})
        if set(criteria) != r6.GATE_CRITERIA or not all(criteria.values()):
            errors.append(f"candidate_gate_criteria_invalid:{row.get('recommendation_id')}")
        errors.extend(f"{row.get('recommendation_id')}:{error}" for error in r6._recursive_forbidden(row.get("action_payload", {})))
    activation = queue.get("activation_contract", {})
    for key in (
        "active_policy_written", "planner_mutated", "mastery_written",
        "canonical_authority_written", "practice_bank_written",
    ):
        if activation.get(key) is not False:
            errors.append(f"activation_boundary_broken:{key}")
    if activation.get("separate_downstream_promotion_required") is not True:
        errors.append("downstream_promotion_gate_missing")
    counts = report.get("counts", {})
    if counts.get("candidate_count") != len(candidates):
        errors.append("report_candidate_count_invalid")
    if report.get("candidate_ids") != candidate_ids:
        errors.append("report_candidate_ids_invalid")
    boundaries = report.get("claim_boundaries", {})
    for key in (
        "raw_response_included", "diagnostic_explanation_included", "action_payload_included",
        "reviewer_identity_included", "mastery_written", "canonical_written",
        "practice_bank_written", "active_policy_written", "a2_unlocked",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"report_claim_boundary_broken:{key}")
    errors.extend(_safe_errors(report))
    return {
        "validation_status": r6.STATUS if not errors else "FAIL_A1FS_V1_R6_GATE_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "candidate_count": len(candidates),
        "next_short_step": r6.NEXT_SHORT_STEP if not errors else r6.TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    request_cmd = commands.add_parser("request")
    request_cmd.add_argument("--evidence-package", type=Path, required=True)
    request_cmd.add_argument("--evidence-safe", type=Path, required=True)
    request_cmd.add_argument("--bank", type=Path, required=True)
    request_cmd.add_argument("--coverage", type=Path, required=True)
    request_cmd.add_argument("--request", type=Path, required=True)
    request_cmd.add_argument("--safe-request", type=Path, required=True)
    request_cmd.add_argument("--max-per-cell", type=int, default=6)
    response_cmd = commands.add_parser("response")
    response_cmd.add_argument("--request", type=Path, required=True)
    response_cmd.add_argument("--response", type=Path, required=True)
    response_cmd.add_argument("--coverage", type=Path, required=True)
    gate_cmd = commands.add_parser("gate")
    gate_cmd.add_argument("--request", type=Path, required=True)
    gate_cmd.add_argument("--response", type=Path, required=True)
    gate_cmd.add_argument("--decisions", type=Path, required=True)
    gate_cmd.add_argument("--coverage", type=Path, required=True)
    gate_cmd.add_argument("--queue", type=Path, required=True)
    gate_cmd.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "request":
        result = validate_request(
            evidence_package_path=args.evidence_package,
            evidence_safe_path=args.evidence_safe,
            bank_path=args.bank,
            coverage_path=args.coverage,
            request_path=args.request,
            safe_request_path=args.safe_request,
            max_representatives_per_cell=args.max_per_cell,
        )
    elif args.command == "response":
        result = validate_response_files(
            request_path=args.request, response_path=args.response, coverage_path=args.coverage,
        )
    else:
        result = validate_gate(
            request_path=args.request, response_path=args.response, decisions_path=args.decisions,
            coverage_path=args.coverage, queue_path=args.queue, report_path=args.report,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
