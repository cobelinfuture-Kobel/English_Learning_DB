from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from ulga.builders import build_a1fs_v1_r7_collector_runtime_coverage_gap_repair_loop as r7
from ulga.builders import build_a1fs_v1_r7_route_batch_controller_and_next_step_governance as controller
from ulga.validators import validate_a1fs_v1_r7_route_batch_controller_and_next_step_governance as validator


def _write(path: Path, value) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _work(index: int, *, route: str, state: str = "OPEN") -> dict:
    finding_type = {
        "CODE_FULLFIX": "EVIDENCE_FIELD_MISSING",
        "AUTHORITY_REVIEW": "COVERAGE_REQUIREMENT_GAP",
        "PLANNER_REDEPLOY": "PEDAGOGICAL_EVIDENCE_INSUFFICIENT",
    }[route]
    return {
        "work_item_id": f"R7_WORK:{index:024x}",
        "finding_id": f"R7_FINDING:{index:024x}",
        "finding_type": finding_type,
        "route": route,
        "severity": "P1" if route != "PLANNER_REDEPLOY" else "P2",
        "breadth_cell_id": f"CELL_{index}",
        "summary_code": f"SUMMARY_{index}",
        "required_gates": list(r7.REQUIRED_GATES[route]),
        "work_state": state,
    }


def _source_values(*, state: str = "OPEN") -> tuple[dict, dict]:
    work_items = [
        _work(1, route="CODE_FULLFIX", state=state),
        _work(2, route="AUTHORITY_REVIEW", state=state),
        _work(3, route="AUTHORITY_REVIEW", state=state),
        _work(4, route="PLANNER_REDEPLOY", state=state),
        _work(5, route="PLANNER_REDEPLOY", state=state),
    ]
    state_counts = {
        work_state: sum(row["work_state"] == work_state for row in work_items)
        for work_state in sorted(r7.WORK_STATES)
    }
    counts = {
        "finding_count": len(work_items),
        "work_item_count": len(work_items),
        "finding_type_counts": {
            "COVERAGE_REQUIREMENT_GAP": 2,
            "EVIDENCE_FIELD_MISSING": 1,
            "PEDAGOGICAL_EVIDENCE_INSUFFICIENT": 2,
        },
        "route_counts": {
            "AUTHORITY_REVIEW": 2,
            "CODE_FULLFIX": 1,
            "PLANNER_REDEPLOY": 2,
        },
        "state_counts": state_counts,
    }
    source_bindings = {
        "r3_report_sha256": "1" * 64,
        "r4_report_sha256": "2" * 64,
        "r5_summary_sha256": "3" * 64,
        "r6_queue_sha256": "4" * 64,
        "r6_report_sha256": "5" * 64,
        "explicit_findings_sha256": None,
    }
    claim_boundaries = {
        "code_modified": False,
        "github_issue_created": False,
        "canonical_authority_modified": False,
        "practice_bank_modified": False,
        "planner_policy_modified": False,
        "mastery_modified": False,
        "a2_unlocked": False,
        "gpt_candidate_executed_directly": False,
    }
    queue_core = {
        "task_id": r7.TASK_ID,
        "schema_version": r7.CLOSED_SCHEMA_VERSION if state == "CLOSED" else r7.QUEUE_SCHEMA_VERSION,
        "validation_status": r7.STATUS,
        "private_local_only": True,
        "source_bindings": source_bindings,
        "counts": counts,
        "findings": [
            {"finding_id": row["finding_id"], "finding_type": row["finding_type"]}
            for row in work_items
        ],
        "work_items": work_items,
        "claim_boundaries": claim_boundaries,
        "next_short_step": r7.NEXT_SHORT_STEP,
    }
    queue = {**queue_core, "queue_sha256": r7.digest(queue_core)}
    report_core = {
        "task_id": r7.TASK_ID,
        "schema_version": r7.REPORT_SCHEMA_VERSION,
        "validation_status": r7.STATUS,
        "source_bindings": source_bindings,
        "counts": counts,
        "work_items": [
            {
                "work_item_id": row["work_item_id"],
                "finding_type": row["finding_type"],
                "route": row["route"],
                "severity": row["severity"],
                "breadth_cell_id": row["breadth_cell_id"],
                "summary_code": row["summary_code"],
                "work_state": row["work_state"],
            }
            for row in work_items
        ],
        "claim_boundaries": claim_boundaries,
        "next_short_step": r7.NEXT_SHORT_STEP,
    }
    report = {**report_core, "report_sha256": r7.digest(report_core)}
    return queue, report


def _materialize(tmp_path: Path, *, state: str = "OPEN"):
    queue, report = _source_values(state=state)
    queue_path = _write(tmp_path / "r7_queue.json", queue)
    report_path = _write(tmp_path / "r7_report.json", report)
    value, safe = controller.build_controller(queue_path=queue_path, report_path=report_path)
    controller_path = _write(tmp_path / "route_controller.json", value)
    safe_path = _write(tmp_path / "route_controller.safe.json", safe)
    return queue_path, report_path, controller_path, safe_path, value, safe


def test_route_batches_preserve_five_findings_but_create_three_execution_units(tmp_path: Path) -> None:
    _, _, _, _, value, safe = _materialize(tmp_path)

    assert value["counts"]["finding_count"] == 5
    assert value["counts"]["work_item_count"] == 5
    assert value["counts"]["route_batch_count"] == 3
    assert value["counts"]["route_batch_work_item_counts"] == {
        "AUTHORITY_REVIEW": 2,
        "CODE_FULLFIX": 1,
        "PLANNER_REDEPLOY": 2,
    }
    assert {row["route"] for row in value["route_batches"]} == {
        "AUTHORITY_REVIEW",
        "CODE_FULLFIX",
        "PLANNER_REDEPLOY",
    }
    assert all(row["execution_contract"]["per_finding_milestone_prohibited"] for row in value["route_batches"])
    assert value["next_short_step"] == controller.EXECUTION_NEXT_SHORT_STEP
    assert safe["next_short_step"] == controller.EXECUTION_NEXT_SHORT_STEP
    assert value["claim_boundaries"]["source_finding_denominator_modified"] is False
    assert value["claim_boundaries"]["a2_unlocked"] is False
    r7.safe_scan(safe)


def test_r8_next_step_is_allowed_only_after_all_source_work_items_close(tmp_path: Path) -> None:
    _, _, _, _, value, safe = _materialize(tmp_path, state="CLOSED")

    assert value["counts"]["source_state_counts"] == {
        "BLOCKED": 0,
        "CLOSED": 5,
        "OPEN": 0,
    }
    assert value["counts"]["route_batch_state_counts"] == {
        "BLOCKED": 0,
        "CLOSED": 3,
        "OPEN": 0,
    }
    assert value["next_short_step"] == r7.NEXT_SHORT_STEP
    assert safe["next_short_step"] == r7.NEXT_SHORT_STEP


def test_exact_rebuild_validator_and_tamper_detection(tmp_path: Path) -> None:
    queue_path, report_path, controller_path, safe_path, _, _ = _materialize(tmp_path)

    valid = validator.validate(
        queue_path=queue_path,
        report_path=report_path,
        controller_path=controller_path,
        safe_report_path=safe_path,
    )
    assert valid["error_count"] == 0, valid["errors"]
    assert valid["route_batch_count"] == 3
    assert valid["next_short_step"] == controller.EXECUTION_NEXT_SHORT_STEP

    tampered = json.loads(controller_path.read_text(encoding="utf-8"))
    tampered["counts"]["route_batch_count"] = 523
    controller_path.write_text(json.dumps(tampered), encoding="utf-8")

    invalid = validator.validate(
        queue_path=queue_path,
        report_path=report_path,
        controller_path=controller_path,
        safe_report_path=safe_path,
    )
    assert invalid["error_count"] > 0
    assert "controller_exact_rebuild_drift" in invalid["errors"]
