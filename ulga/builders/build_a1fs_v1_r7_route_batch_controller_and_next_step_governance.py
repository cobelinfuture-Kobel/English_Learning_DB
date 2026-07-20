#!/usr/bin/env python3
"""Collapse the R7 finding denominator into route-level execution batches.

Task: A1FS-V1-R7_RouteBatchControllerAndNextStepGovernanceFullFix

The existing R7 repair queue remains the authoritative finding denominator. This
consumer prevents one milestone per finding by grouping every work item into at
most one batch per route. It also keeps the automatic next step inside R7 until
all source work items are closed. It never executes a candidate or modifies code,
Authority, PracticeBank, planner policy, mastery, learner evidence, or A2 state.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r7_collector_runtime_coverage_gap_repair_loop as r7

TASK_ID = "A1FS-V1-R7_RouteBatchControllerAndNextStepGovernanceFullFix"
CONTROLLER_SCHEMA_VERSION = "a1fs.v1.r7.route_batch_controller.v1"
REPORT_SCHEMA_VERSION = "a1fs.v1.r7.route_batch_controller_safe_report.v1"
STATUS = "PASS_A1FS_V1_R7_ROUTE_BATCH_CONTROLLER_AND_NEXT_STEP_GOVERNANCE"
EXECUTION_NEXT_SHORT_STEP = "A1FS-V1-R7_RouteBatchExecutionAndReplayClosure"
R8_NEXT_SHORT_STEP = r7.NEXT_SHORT_STEP
MAX_ROUTE_BATCH_COUNT = len(r7.ROUTES)


class RouteBatchControllerError(ValueError):
    """Fail-closed route-batch controller error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return r7.digest(value)


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RouteBatchControllerError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise RouteBatchControllerError(f"{code}_not_object")
    return value


def write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _validate_digest(value: Mapping[str, Any], digest_key: str, code: str) -> None:
    core = {key: child for key, child in value.items() if key != digest_key}
    if value.get(digest_key) != digest(core):
        raise RouteBatchControllerError(code)


def _validate_source(queue: Mapping[str, Any], report: Mapping[str, Any]) -> list[dict[str, Any]]:
    if (
        queue.get("task_id") != r7.TASK_ID
        or queue.get("schema_version") not in {r7.QUEUE_SCHEMA_VERSION, r7.CLOSED_SCHEMA_VERSION}
        or queue.get("validation_status") != r7.STATUS
        or queue.get("private_local_only") is not True
    ):
        raise RouteBatchControllerError("r7_queue_identity_or_status_invalid")
    _validate_digest(queue, "queue_sha256", "r7_queue_digest_invalid")

    if (
        report.get("task_id") != r7.TASK_ID
        or report.get("schema_version") != r7.REPORT_SCHEMA_VERSION
        or report.get("validation_status") != r7.STATUS
    ):
        raise RouteBatchControllerError("r7_report_identity_or_status_invalid")
    _validate_digest(report, "report_sha256", "r7_report_digest_invalid")

    if queue.get("source_bindings") != report.get("source_bindings"):
        raise RouteBatchControllerError("r7_queue_report_source_binding_mismatch")
    if queue.get("counts") != report.get("counts"):
        raise RouteBatchControllerError("r7_queue_report_counts_mismatch")

    work_items = queue.get("work_items")
    if not isinstance(work_items, list):
        raise RouteBatchControllerError("r7_work_items_invalid")
    if queue.get("counts", {}).get("work_item_count") != len(work_items):
        raise RouteBatchControllerError("r7_work_item_count_invalid")

    work_ids: list[str] = []
    for row in work_items:
        if not isinstance(row, Mapping):
            raise RouteBatchControllerError("r7_work_item_not_object")
        work_id = str(row.get("work_item_id") or "")
        route = str(row.get("route") or "")
        state = str(row.get("work_state") or "")
        if not work_id or route not in r7.ROUTES or state not in r7.WORK_STATES:
            raise RouteBatchControllerError(f"r7_work_item_identity_invalid:{work_id}")
        if row.get("required_gates") != r7.REQUIRED_GATES[route]:
            raise RouteBatchControllerError(f"r7_work_item_gate_denominator_invalid:{work_id}")
        work_ids.append(work_id)
    if len(work_ids) != len(set(work_ids)):
        raise RouteBatchControllerError("r7_work_item_duplicate_id")

    expected_state_counts = {
        state: int(Counter(str(row["work_state"]) for row in work_items).get(state, 0))
        for state in sorted(r7.WORK_STATES)
    }
    if queue.get("counts", {}).get("state_counts") != expected_state_counts:
        raise RouteBatchControllerError("r7_state_counts_invalid")
    return [deepcopy(dict(row)) for row in work_items]


def _batch_state(rows: Sequence[Mapping[str, Any]]) -> str:
    states = {str(row["work_state"]) for row in rows}
    if "BLOCKED" in states:
        return "BLOCKED"
    if "OPEN" in states:
        return "OPEN"
    return "CLOSED"


def _route_batch(*, source_queue_sha256: str, route: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted((deepcopy(dict(row)) for row in rows), key=lambda row: str(row["work_item_id"]))
    work_item_ids = [str(row["work_item_id"]) for row in ordered]
    finding_ids = [str(row["finding_id"]) for row in ordered]
    core = {
        "route_batch_id": f"R7_ROUTE_BATCH:{digest([source_queue_sha256, route, work_item_ids])[:24]}",
        "route": route,
        "work_state": _batch_state(ordered),
        "work_item_count": len(ordered),
        "work_item_ids": work_item_ids,
        "finding_ids": finding_ids,
        "finding_type_counts": dict(sorted(Counter(str(row["finding_type"]) for row in ordered).items())),
        "severity_counts": dict(sorted(Counter(str(row["severity"]) for row in ordered).items())),
        "required_gates": list(r7.REQUIRED_GATES[route]),
        "execution_contract": {
            "single_route_milestone": True,
            "per_finding_milestone_prohibited": True,
            "all_source_work_items_must_close": True,
            "replay_required": route in {"CODE_FULLFIX", "CONTENT_EXPANSION", "PLANNER_REDEPLOY"},
            "raw_evidence_preservation_required": True,
            "a2_lock_required": True,
        },
    }
    return {**core, "route_batch_sha256": digest(core)}


def _next_short_step(state_counts: Mapping[str, Any]) -> str:
    if int(state_counts.get("OPEN", 0)) > 0 or int(state_counts.get("BLOCKED", 0)) > 0:
        return EXECUTION_NEXT_SHORT_STEP
    return R8_NEXT_SHORT_STEP


def build_controller(*, queue_path: Path, report_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    queue = read_json(queue_path, "r7_queue")
    report = read_json(report_path, "r7_report")
    work_items = _validate_source(queue, report)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in work_items:
        grouped[str(row["route"])].append(row)
    route_batches = [
        _route_batch(source_queue_sha256=str(queue["queue_sha256"]), route=route, rows=grouped[route])
        for route in sorted(grouped)
    ]
    if len(route_batches) > MAX_ROUTE_BATCH_COUNT:
        raise RouteBatchControllerError("route_batch_count_exceeds_route_denominator")

    covered_work_ids = [work_id for batch in route_batches for work_id in batch["work_item_ids"]]
    expected_work_ids = sorted(str(row["work_item_id"]) for row in work_items)
    if sorted(covered_work_ids) != expected_work_ids or len(covered_work_ids) != len(set(covered_work_ids)):
        raise RouteBatchControllerError("route_batch_work_item_partition_invalid")

    batch_state_counts = {
        state: int(Counter(str(row["work_state"]) for row in route_batches).get(state, 0))
        for state in sorted(r7.WORK_STATES)
    }
    next_short_step = _next_short_step(queue["counts"]["state_counts"])
    source_bindings = {
        "r7_queue_sha256": queue["queue_sha256"],
        "r7_report_sha256": report["report_sha256"],
    }
    counts = {
        "finding_count": int(queue["counts"]["finding_count"]),
        "work_item_count": len(work_items),
        "route_batch_count": len(route_batches),
        "route_counts": deepcopy(dict(queue["counts"]["route_counts"])),
        "source_state_counts": deepcopy(dict(queue["counts"]["state_counts"])),
        "route_batch_state_counts": batch_state_counts,
        "route_batch_work_item_counts": {
            row["route"]: int(row["work_item_count"]) for row in route_batches
        },
    }
    claim_boundaries = {
        "source_finding_denominator_modified": False,
        "source_work_items_modified": False,
        "candidate_executed_directly": False,
        "code_modified": False,
        "canonical_authority_modified": False,
        "practice_bank_modified": False,
        "planner_policy_modified": False,
        "mastery_modified": False,
        "learner_evidence_modified": False,
        "a2_unlocked": False,
    }
    controller_core = {
        "task_id": TASK_ID,
        "schema_version": CONTROLLER_SCHEMA_VERSION,
        "validation_status": STATUS,
        "private_local_only": True,
        "source_bindings": source_bindings,
        "counts": counts,
        "route_batches": route_batches,
        "governance_contract": {
            "authoritative_denominator": "SOURCE_R7_FINDINGS_AND_WORK_ITEMS",
            "execution_unit": "ONE_MILESTONE_PER_ACTIVE_ROUTE",
            "maximum_route_batch_count": MAX_ROUTE_BATCH_COUNT,
            "r8_entry_requires_open_zero": True,
            "r8_entry_requires_blocked_zero": True,
        },
        "claim_boundaries": claim_boundaries,
        "next_short_step": next_short_step,
    }
    controller = {**controller_core, "controller_sha256": digest(controller_core)}

    safe_core = {
        "task_id": TASK_ID,
        "schema_version": REPORT_SCHEMA_VERSION,
        "validation_status": STATUS,
        "source_bindings": source_bindings,
        "counts": counts,
        "route_batches": [
            {
                "route_batch_id": row["route_batch_id"],
                "route": row["route"],
                "work_state": row["work_state"],
                "work_item_count": row["work_item_count"],
                "finding_type_counts": row["finding_type_counts"],
                "severity_counts": row["severity_counts"],
                "required_gates": row["required_gates"],
            }
            for row in route_batches
        ],
        "governance_contract": controller_core["governance_contract"],
        "claim_boundaries": claim_boundaries,
        "next_short_step": next_short_step,
    }
    safe_report = {**safe_core, "report_sha256": digest(safe_core)}
    r7.safe_scan(safe_report)
    return controller, safe_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--controller-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    args = parser.parse_args()

    controller, safe_report = build_controller(queue_path=args.queue, report_path=args.report)
    write_private(args.controller_output, controller)
    write_private(args.report_output, safe_report)
    print(json.dumps({
        "validation_status": STATUS,
        "finding_count": controller["counts"]["finding_count"],
        "work_item_count": controller["counts"]["work_item_count"],
        "route_batch_count": controller["counts"]["route_batch_count"],
        "route_batch_work_item_counts": controller["counts"]["route_batch_work_item_counts"],
        "source_state_counts": controller["counts"]["source_state_counts"],
        "next_short_step": controller["next_short_step"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
