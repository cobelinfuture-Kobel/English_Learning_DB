#!/usr/bin/env python3
"""Run one local delayed retention check for an M105Q mastery candidate.

The runner reads private baseline/projection files from ``.local/``. Before the
24-hour minimum interval it does not collect answers or create retention
evidence. That timing condition is a learner/unit measurement defer, not an
engineering stop: the runner returns a successful non-blocking workflow report
and routes work to the next private-pilot unit. Once eligible it presents the
candidate unit's reading and writing assessment items, writes a private
retention response source, and invokes the M105S intake.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_text_mode_private_pilot_evidence_intake import (
    load_json,
    write_json,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_package_source,
)
from ulga.builders.import_a1_grammar_text_mode_private_pilot_real_attempts import (
    OPEN_PRODUCTIVE_TASK_TYPES,
)
from ulga.builders.import_a1_grammar_text_mode_retention_evidence import (
    DEFAULT_BASELINE_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PROJECTION_PATH,
    DEFAULT_REPORT_PATH,
    DEFAULT_RESPONSES_PATH,
    RETENTION_POLICY,
    RETENTION_SCHEMA_VERSION,
    TASK_ID,
    run_retention_import,
)

WORKFLOW_PATCH_ID = "R7-M105S1_A1A1PlusRetentionGateNonBlockingWorkflowFullFix"
NEXT_PRIVATE_PILOT_TASK = (
    "R7-M105P03_A1A1PlusTextModePrivatePilotNextUnitExecution"
)
RETENTION_RESUME_TASK = (
    "R7-M105S_A1A1PlusTextModeRetentionEvidenceIntake_Execution"
)


def _parse_aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("retention_runner_timezone_required")
    return parsed


def _candidate_unit_ids(projection: Mapping[str, Any]) -> list[str]:
    return sorted(
        {
            route.get("grammar_unit_id")
            for route in projection.get("routing", {}).get("retention_check", [])
            if isinstance(route, Mapping)
            and route.get("route") == "RETENTION_CHECK_REQUIRED"
            and isinstance(route.get("grammar_unit_id"), str)
        }
    )


def build_deferred_report(
    *,
    grammar_unit_id: str,
    baseline_completed_at: datetime,
    retention_eligible_at: datetime,
    now: datetime,
) -> dict[str, Any]:
    """Return a non-blocking timing defer without creating learner evidence."""

    remaining_seconds = max(
        0,
        int((retention_eligible_at - now).total_seconds()),
    )
    return {
        "task_id": TASK_ID,
        "workflow_patch_id": WORKFLOW_PATCH_ID,
        "validation_status": "PASS",
        "retention_status": "DEFERRED_UNTIL_ELIGIBLE",
        "workflow_status": "NON_BLOCKING_CONTINUE_ALLOWED",
        "grammar_unit_id": grammar_unit_id,
        "baseline_completed_at": baseline_completed_at.isoformat(),
        "retention_eligible_at": retention_eligible_at.isoformat(),
        "remaining_seconds": remaining_seconds,
        "measurement_gate": "DEFERRED_MINIMUM_DELAY_NOT_REACHED",
        "engineering_progress_gate": "PASS_CONTINUE",
        "same_day_recheck_classification": "NOT_RETENTION_EVIDENCE",
        "retention_evidence_created": False,
        "final_mastery_claimed": False,
        "persistent_learner_state_write": False,
        "errors": [],
        "warnings": [
            "The learner/unit retention measurement is deferred until eligible.",
            "This defer does not block engineering work or the next A1 private-pilot unit.",
            "A same-day recheck must not be classified as retention evidence.",
        ],
        "stop_reason": "NONE",
        "next_task": NEXT_PRIVATE_PILOT_TASK,
        "retention_resume_task": RETENTION_RESUME_TASK,
    }


def build_no_candidate_report() -> dict[str, Any]:
    """Return a successful no-op when no unit currently needs retention."""

    return {
        "task_id": TASK_ID,
        "workflow_patch_id": WORKFLOW_PATCH_ID,
        "validation_status": "PASS",
        "retention_status": "NO_RETENTION_CANDIDATE",
        "workflow_status": "NON_BLOCKING_CONTINUE_ALLOWED",
        "measurement_gate": "NO_ACTION_REQUIRED",
        "engineering_progress_gate": "PASS_CONTINUE",
        "retention_evidence_created": False,
        "final_mastery_claimed": False,
        "persistent_learner_state_write": False,
        "errors": [],
        "warnings": [],
        "stop_reason": "NONE",
        "next_task": NEXT_PRIVATE_PILOT_TASK,
        "retention_resume_task": RETENTION_RESUME_TASK,
    }


def _display_item(item: Mapping[str, Any], number: int, total: int) -> None:
    print()
    print("-" * 72)
    print(
        f"[{number}/{total}] {item.get('skill')} / "
        f"{item.get('item_role')} / {item.get('task_type')}"
    )
    print(f"Item ID: {item.get('item_id')}")
    context = item.get("context")
    if context:
        print("Context:", json.dumps(context, ensure_ascii=False))
    print("Question:", item.get("prompt", ""))
    options = item.get("options", [])
    for option_number, option in enumerate(options, start=1):
        print(f"  {option_number}. {option}")


def _collect_response(
    item: Mapping[str, Any],
    *,
    operator_ref: str,
) -> dict[str, Any]:
    options = item.get("options", [])
    raw_answer = input("Learner answer: ").strip()
    response_text = raw_answer
    if options and raw_answer.isdigit():
        selected = int(raw_answer)
        if 1 <= selected <= len(options):
            response_text = str(options[selected - 1])

    record: dict[str, Any] = {
        "item_id": item["item_id"],
        "response_text": response_text,
        "submitted_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    if item.get("task_type") in OPEN_PRODUCTIVE_TASK_TYPES:
        threshold = float(
            item.get("scoring_rubric", {}).get("minimum_score", 1.0)
        )
        while True:
            raw_score = input(
                f"Operator score 0–1 (pass threshold {threshold}): "
            ).strip()
            try:
                score = float(raw_score)
            except ValueError:
                print("Please enter a number from 0 to 1.")
                continue
            if 0.0 <= score <= 1.0:
                break
            print("Please enter a number from 0 to 1.")
        passed = score >= threshold
        record.update(
            {
                "score": score,
                "passed": passed,
                "evaluator_type": "MANUAL",
                "evaluator_ref": operator_ref,
                "error_tags": (
                    []
                    if passed
                    else ["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"]
                ),
            }
        )
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE_PATH)
    parser.add_argument("--projection", type=Path, default=DEFAULT_PROJECTION_PATH)
    parser.add_argument("--responses", type=Path, default=DEFAULT_RESPONSES_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--unit", default=None)
    parser.add_argument("--operator-ref", default=None)
    args = parser.parse_args(argv)

    missing = [
        str(path)
        for path in (args.baseline, args.projection)
        if not path.exists()
    ]
    if missing:
        report = {
            "task_id": TASK_ID,
            "workflow_patch_id": WORKFLOW_PATCH_ID,
            "validation_status": "BLOCKED",
            "retention_status": "BASELINE_OR_PROJECTION_NOT_FOUND",
            "workflow_status": "RETENTION_INPUT_BLOCKED",
            "errors": ["retention_source_not_found:" + path for path in missing],
            "stop_reason": "RETENTION_EVIDENCE_REQUIRED",
            "next_task": NEXT_PRIVATE_PILOT_TASK,
        }
        write_json(args.report, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    package, package_report = build_package_source()
    if package_report.get("validation_status") != "PASS":
        print(json.dumps(package_report, ensure_ascii=False, indent=2))
        return 1
    baseline = load_json(args.baseline)
    projection = load_json(args.projection)

    candidate_ids = _candidate_unit_ids(projection)
    if not candidate_ids:
        report = build_no_candidate_report()
        write_json(args.report, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    unit_index = {
        unit["grammar_unit_id"]: unit
        for unit in package["learning_units"]
    }
    if args.unit is not None:
        if args.unit not in candidate_ids:
            report = {
                "task_id": TASK_ID,
                "workflow_patch_id": WORKFLOW_PATCH_ID,
                "validation_status": "FAIL",
                "retention_status": "REQUESTED_UNIT_NOT_A_RETENTION_CANDIDATE",
                "errors": [f"retention_unit_not_candidate:{args.unit}"],
                "stop_reason": "VALIDATION_FAILURE",
            }
            write_json(args.report, report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2
        grammar_id = args.unit
    else:
        grammar_id = min(
            candidate_ids,
            key=lambda value: unit_index[value]["sequence_index"],
        )

    baseline_session = baseline.get("session", {})
    baseline_completed = _parse_aware(baseline_session["completed_at"])
    eligible_at = baseline_completed + timedelta(
        hours=RETENTION_POLICY["minimum_delay_hours"]
    )
    now = datetime.now().astimezone()
    if now < eligible_at:
        report = build_deferred_report(
            grammar_unit_id=grammar_id,
            baseline_completed_at=baseline_completed,
            retention_eligible_at=eligible_at,
            now=now,
        )
        write_json(args.report, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    item_index = {
        item["item_id"]: item
        for item in package["item_bank"]
    }
    unit = unit_index[grammar_id]
    assessment_ids = list(unit["delivery_plan"]["assessment_item_ids"])
    if len(assessment_ids) != 2:
        raise RuntimeError("retention_runner_assessment_count_not_2")

    operator_ref = (
        args.operator_ref
        or baseline_session.get("operator_ref")
        or "operator:cobelinfuture-Kobel"
    )
    learner_ref = baseline_session["learner_ref"]
    started_at = datetime.now().astimezone()
    stamp = started_at.strftime("%Y%m%dT%H%M%S")
    session_id = f"session:A1_RETENTION_{stamp}"

    print()
    print("=" * 72)
    print(f"Retention unit: {grammar_id}")
    print(
        "Title:",
        unit.get("learning_content", {}).get("title_en", grammar_id),
    )
    print(f"Assessment items: {len(assessment_ids)}")
    print(f"Baseline session: {baseline_session.get('session_id')}")
    print(f"Eligible since: {eligible_at.isoformat()}")
    print("=" * 72)

    responses = []
    for number, item_id in enumerate(assessment_ids, start=1):
        item = item_index[item_id]
        _display_item(item, number, len(assessment_ids))
        responses.append(
            _collect_response(item, operator_ref=operator_ref)
        )

    completed_at = datetime.now().astimezone()
    source = {
        "retention_schema_version": RETENTION_SCHEMA_VERSION,
        "baseline_session_id": baseline_session["session_id"],
        "grammar_unit_ids": [grammar_id],
        "session": {
            "session_id": session_id,
            "learner_ref": learner_ref,
            "operator_ref": operator_ref,
            "started_at": started_at.isoformat(timespec="seconds"),
            "completed_at": completed_at.isoformat(timespec="seconds"),
            "evidence_source_ref": f"local_private_pilot://{session_id}",
        },
        "responses": responses,
    }
    write_json(args.responses, source)
    artifact, report = run_retention_import(
        source,
        baseline,
        projection,
        package=package,
    )
    report["workflow_patch_id"] = WORKFLOW_PATCH_ID
    write_json(args.output, artifact)
    write_json(args.report, report)
    print()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("validation_status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
