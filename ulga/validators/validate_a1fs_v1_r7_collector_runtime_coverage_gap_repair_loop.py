#!/usr/bin/env python3
"""Independent exact-rebuild validator for the R7 gap repair loop."""
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

from ulga.builders import build_a1fs_v1_r7_collector_runtime_coverage_gap_repair_loop as r7


def _safe_errors(value: Any) -> list[str]:
    try:
        r7.safe_scan(value)
    except r7.RepairLoopError as exc:
        return [str(exc)]
    return []


def _validate_queue_shape(queue: Mapping[str, Any], errors: list[str]) -> None:
    core = {key: value for key, value in queue.items() if key != "queue_sha256"}
    if queue.get("queue_sha256") != r7.digest(core):
        errors.append("queue_digest_invalid")
    if queue.get("task_id") != r7.TASK_ID:
        errors.append("queue_task_invalid")
    if queue.get("schema_version") not in {r7.QUEUE_SCHEMA_VERSION, r7.CLOSED_SCHEMA_VERSION}:
        errors.append("queue_schema_invalid")
    if queue.get("validation_status") != r7.STATUS or queue.get("private_local_only") is not True:
        errors.append("queue_status_or_privacy_invalid")
    findings = queue.get("findings", [])
    work = queue.get("work_items", [])
    finding_ids = [row.get("finding_id") for row in findings]
    work_ids = [row.get("work_item_id") for row in work]
    if len(finding_ids) != len(set(finding_ids)) or None in finding_ids:
        errors.append("finding_identity_invalid")
    if len(work_ids) != len(set(work_ids)) or None in work_ids:
        errors.append("work_identity_invalid")
    if queue.get("counts", {}).get("finding_count") != len(findings):
        errors.append("finding_count_invalid")
    if queue.get("counts", {}).get("work_item_count") != len(work):
        errors.append("work_item_count_invalid")
    finding_by_id = {row.get("finding_id"): row for row in findings}
    for row in work:
        finding = finding_by_id.get(row.get("finding_id"))
        if not finding:
            errors.append(f"work_finding_missing:{row.get('work_item_id')}")
            continue
        expected_route = r7.ROUTE_BY_FINDING.get(row.get("finding_type"))
        if row.get("route") != expected_route or row.get("finding_type") != finding.get("finding_type"):
            errors.append(f"work_route_invalid:{row.get('work_item_id')}")
        if row.get("required_gates") != r7.REQUIRED_GATES.get(row.get("route")):
            errors.append(f"work_gate_denominator_invalid:{row.get('work_item_id')}")
        if row.get("allowed_path_patterns") != r7.ALLOWED_PATHS.get(row.get("finding_type")):
            errors.append(f"work_allowed_paths_invalid:{row.get('work_item_id')}")
        if row.get("forbidden_path_patterns") != r7.FORBIDDEN_PATHS:
            errors.append(f"work_forbidden_paths_invalid:{row.get('work_item_id')}")
        if row.get("work_state") not in r7.WORK_STATES:
            errors.append(f"work_state_invalid:{row.get('work_item_id')}")
        replay = row.get("replay_contract", {})
        if replay.get("preserve_raw_evidence") is not True or replay.get("a2_lock_required") is not True:
            errors.append(f"work_replay_boundary_invalid:{row.get('work_item_id')}")
    counts = queue.get("counts", {})
    if counts.get("finding_type_counts") != dict(sorted(Counter(row.get("finding_type") for row in findings).items())):
        errors.append("finding_type_counts_invalid")
    if counts.get("route_counts") != dict(sorted(Counter(row.get("route") for row in work).items())):
        errors.append("route_counts_invalid")
    boundaries = queue.get("claim_boundaries", {})
    for key in (
        "code_modified", "github_issue_created", "canonical_authority_modified",
        "practice_bank_modified", "planner_policy_modified", "mastery_modified",
        "a2_unlocked", "gpt_candidate_executed_directly",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"queue_claim_boundary_broken:{key}")


def validate_build(
    *, r3_path: Path, r4_path: Path, r5_path: Path, r6_queue_path: Path,
    r6_report_path: Path, queue_path: Path, report_path: Path,
    explicit_findings_path: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        queue = r7.read_json(queue_path, "queue")
        report = r7.read_json(report_path, "report")
        expected_queue, expected_report = r7.build_queue(
            r3_path=r3_path, r4_path=r4_path, r5_path=r5_path,
            r6_queue_path=r6_queue_path, r6_report_path=r6_report_path,
            explicit_findings_path=explicit_findings_path,
        )
    except (OSError, json.JSONDecodeError, r7.RepairLoopError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"build_rebuild_failed:{exc}"]}
    if queue != expected_queue:
        errors.append("queue_rebuild_drift")
    if report != expected_report:
        errors.append("report_rebuild_drift")
    _validate_queue_shape(queue, errors)
    report_core = {key: value for key, value in report.items() if key != "report_sha256"}
    if report.get("report_sha256") != r7.digest(report_core):
        errors.append("report_digest_invalid")
    if report.get("task_id") != r7.TASK_ID or report.get("schema_version") != r7.REPORT_SCHEMA_VERSION:
        errors.append("report_identity_invalid")
    if report.get("validation_status") != r7.STATUS:
        errors.append("report_status_invalid")
    if report.get("counts") != queue.get("counts"):
        errors.append("report_counts_drift")
    errors.extend(_safe_errors(report))
    return {
        "validation_status": r7.STATUS if not errors else "FAIL_A1FS_V1_R7_BUILD_VALIDATION",
        "error_count": len(errors), "errors": errors,
        "work_item_count": len(queue.get("work_items", [])),
        "next_short_step": r7.NEXT_SHORT_STEP if not errors else r7.TASK_ID,
    }


def validate_closure(
    *, queue_path: Path, results_path: Path, closed_queue_path: Path, report_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        source_queue = r7.read_json(queue_path, "source_queue")
        results = r7.read_json(results_path, "results")
        closed = r7.read_json(closed_queue_path, "closed_queue")
        report = r7.read_json(report_path, "report")
        expected_closed, expected_report = r7.apply_results(queue=source_queue, registry=results)
    except (OSError, json.JSONDecodeError, r7.RepairLoopError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"closure_rebuild_failed:{exc}"]}
    if closed != expected_closed:
        errors.append("closed_queue_rebuild_drift")
    if report != expected_report:
        errors.append("closure_report_rebuild_drift")
    _validate_queue_shape(closed, errors)
    if closed.get("schema_version") != r7.CLOSED_SCHEMA_VERSION:
        errors.append("closed_schema_invalid")
    state_counts = Counter(row.get("work_state") for row in closed.get("work_items", []))
    expected_states = {state: int(state_counts.get(state, 0)) for state in sorted(r7.WORK_STATES)}
    if closed.get("counts", {}).get("state_counts") != expected_states:
        errors.append("closed_state_counts_invalid")
    for row in closed.get("work_items", []):
        closure = row.get("closure")
        if row.get("work_state") == "CLOSED":
            if not isinstance(closure, Mapping) or closure.get("result_state") != "PASS":
                errors.append(f"closed_work_without_pass:{row.get('work_item_id')}")
        if row.get("work_state") == "BLOCKED":
            if not isinstance(closure, Mapping) or closure.get("result_state") != "BLOCKED":
                errors.append(f"blocked_work_without_blocked_result:{row.get('work_item_id')}")
    report_core = {key: value for key, value in report.items() if key != "report_sha256"}
    if report.get("report_sha256") != r7.digest(report_core):
        errors.append("closure_report_digest_invalid")
    errors.extend(_safe_errors(report))
    return {
        "validation_status": r7.STATUS if not errors else "FAIL_A1FS_V1_R7_CLOSURE_VALIDATION",
        "error_count": len(errors), "errors": errors,
        "closed_count": closed.get("counts", {}).get("closed_count", 0),
        "next_short_step": r7.NEXT_SHORT_STEP if not errors else r7.TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    build_cmd = commands.add_parser("build")
    build_cmd.add_argument("--r3", type=Path, required=True)
    build_cmd.add_argument("--r4", type=Path, required=True)
    build_cmd.add_argument("--r5", type=Path, required=True)
    build_cmd.add_argument("--r6-queue", type=Path, required=True)
    build_cmd.add_argument("--r6-report", type=Path, required=True)
    build_cmd.add_argument("--explicit-findings", type=Path)
    build_cmd.add_argument("--queue", type=Path, required=True)
    build_cmd.add_argument("--report", type=Path, required=True)
    close_cmd = commands.add_parser("closure")
    close_cmd.add_argument("--queue", type=Path, required=True)
    close_cmd.add_argument("--results", type=Path, required=True)
    close_cmd.add_argument("--closed-queue", type=Path, required=True)
    close_cmd.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        result = validate_build(
            r3_path=args.r3, r4_path=args.r4, r5_path=args.r5,
            r6_queue_path=args.r6_queue, r6_report_path=args.r6_report,
            explicit_findings_path=args.explicit_findings,
            queue_path=args.queue, report_path=args.report,
        )
    else:
        result = validate_closure(
            queue_path=args.queue, results_path=args.results,
            closed_queue_path=args.closed_queue, report_path=args.report,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
