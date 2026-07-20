#!/usr/bin/env python3
"""Independent exact-rebuild validator for the R7 route-batch controller."""
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
from ulga.builders import build_a1fs_v1_r7_route_batch_controller_and_next_step_governance as controller


def _safe_errors(value: Any) -> list[str]:
    try:
        r7.safe_scan(value)
    except r7.RepairLoopError as exc:
        return [str(exc)]
    return []


def validate(
    *, queue_path: Path, report_path: Path, controller_path: Path, safe_report_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        actual_controller = controller.read_json(controller_path, "controller")
        actual_report = controller.read_json(safe_report_path, "safe_report")
        expected_controller, expected_report = controller.build_controller(
            queue_path=queue_path,
            report_path=report_path,
        )
    except (OSError, json.JSONDecodeError, controller.RouteBatchControllerError) as exc:
        return {
            "validation_status": "FAIL_A1FS_V1_R7_ROUTE_BATCH_CONTROLLER_VALIDATION",
            "error_count": 1,
            "errors": [f"exact_rebuild_failed:{exc}"],
            "next_short_step": controller.TASK_ID,
        }

    if actual_controller != expected_controller:
        errors.append("controller_exact_rebuild_drift")
    if actual_report != expected_report:
        errors.append("safe_report_exact_rebuild_drift")

    controller_core = {
        key: value for key, value in actual_controller.items() if key != "controller_sha256"
    }
    if actual_controller.get("controller_sha256") != controller.digest(controller_core):
        errors.append("controller_digest_invalid")
    if (
        actual_controller.get("task_id") != controller.TASK_ID
        or actual_controller.get("schema_version") != controller.CONTROLLER_SCHEMA_VERSION
        or actual_controller.get("validation_status") != controller.STATUS
        or actual_controller.get("private_local_only") is not True
    ):
        errors.append("controller_identity_or_status_invalid")

    batches = actual_controller.get("route_batches", [])
    if not isinstance(batches, list):
        errors.append("route_batches_invalid")
        batches = []
    if len(batches) > controller.MAX_ROUTE_BATCH_COUNT:
        errors.append("route_batch_count_exceeds_maximum")
    if actual_controller.get("counts", {}).get("route_batch_count") != len(batches):
        errors.append("route_batch_count_invalid")

    routes = [row.get("route") for row in batches if isinstance(row, Mapping)]
    if len(routes) != len(set(routes)) or any(route not in r7.ROUTES for route in routes):
        errors.append("route_batch_route_partition_invalid")

    covered_ids: list[str] = []
    for row in batches:
        if not isinstance(row, Mapping):
            errors.append("route_batch_not_object")
            continue
        route = row.get("route")
        state = row.get("work_state")
        work_ids = row.get("work_item_ids")
        core = {key: value for key, value in row.items() if key != "route_batch_sha256"}
        if row.get("route_batch_sha256") != controller.digest(core):
            errors.append(f"route_batch_digest_invalid:{row.get('route_batch_id')}")
        if state not in r7.WORK_STATES:
            errors.append(f"route_batch_state_invalid:{row.get('route_batch_id')}")
        if not isinstance(work_ids, list) or len(work_ids) != row.get("work_item_count"):
            errors.append(f"route_batch_work_count_invalid:{row.get('route_batch_id')}")
            continue
        if row.get("required_gates") != r7.REQUIRED_GATES.get(route):
            errors.append(f"route_batch_gate_denominator_invalid:{row.get('route_batch_id')}")
        covered_ids.extend(str(work_id) for work_id in work_ids)

    if len(covered_ids) != len(set(covered_ids)):
        errors.append("route_batch_duplicate_work_item")
    if len(covered_ids) != actual_controller.get("counts", {}).get("work_item_count"):
        errors.append("route_batch_work_item_denominator_invalid")

    state_counts = actual_controller.get("counts", {}).get("source_state_counts", {})
    expected_next = controller._next_short_step(state_counts)
    if actual_controller.get("next_short_step") != expected_next:
        errors.append("controller_next_short_step_invalid")
    if actual_report.get("next_short_step") != expected_next:
        errors.append("safe_report_next_short_step_invalid")

    report_core = {key: value for key, value in actual_report.items() if key != "report_sha256"}
    if actual_report.get("report_sha256") != controller.digest(report_core):
        errors.append("safe_report_digest_invalid")
    if (
        actual_report.get("task_id") != controller.TASK_ID
        or actual_report.get("schema_version") != controller.REPORT_SCHEMA_VERSION
        or actual_report.get("validation_status") != controller.STATUS
    ):
        errors.append("safe_report_identity_or_status_invalid")
    if actual_report.get("source_bindings") != actual_controller.get("source_bindings"):
        errors.append("controller_report_source_binding_mismatch")
    if actual_report.get("counts") != actual_controller.get("counts"):
        errors.append("controller_report_counts_mismatch")
    errors.extend(_safe_errors(actual_report))

    boundaries = actual_controller.get("claim_boundaries", {})
    for key in (
        "source_finding_denominator_modified",
        "source_work_items_modified",
        "candidate_executed_directly",
        "code_modified",
        "canonical_authority_modified",
        "practice_bank_modified",
        "planner_policy_modified",
        "mastery_modified",
        "learner_evidence_modified",
        "a2_unlocked",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"claim_boundary_broken:{key}")

    return {
        "validation_status": controller.STATUS if not errors else "FAIL_A1FS_V1_R7_ROUTE_BATCH_CONTROLLER_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "finding_count": actual_controller.get("counts", {}).get("finding_count", 0),
        "work_item_count": actual_controller.get("counts", {}).get("work_item_count", 0),
        "route_batch_count": len(batches),
        "route_batch_work_item_counts": actual_controller.get("counts", {}).get("route_batch_work_item_counts", {}),
        "route_batch_state_counts": dict(sorted(Counter(row.get("work_state") for row in batches if isinstance(row, Mapping)).items())),
        "next_short_step": expected_next if not errors else controller.TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--controller", type=Path, required=True)
    parser.add_argument("--safe-report", type=Path, required=True)
    args = parser.parse_args()

    result = validate(
        queue_path=args.queue,
        report_path=args.report,
        controller_path=args.controller,
        safe_report_path=args.safe_report,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
