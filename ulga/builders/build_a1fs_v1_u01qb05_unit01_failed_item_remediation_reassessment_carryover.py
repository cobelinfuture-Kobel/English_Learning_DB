#!/usr/bin/env python3
"""Prove Unit01 failure carry-over, remediation reassessment, and recent exclusion."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)
from ulga.builders import (
    build_a1fs_v1_u01qb04_unit01_ten_item_session_completion_evidence_export as qb04,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Consumes existing U01QB02 session history and U01QB04 completion to prove one failed Unit01 item is selected as remediation, passes reassessment, and is excluded from the immediately following recent-exposure window; no learner content, planner, database, scoring authority, mastery, retention, audio, A2 content, or Unit02-Unit24 content is produced."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB05_Unit01FailedItemRemediationReassessmentAndCarryOverAcceptance"
SCHEMA_VERSION = "a1fs.v1.u01qb05.unit01_remediation_reassessment_carryover.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB05_UNIT01_REMEDIATION_REASSESSMENT_CARRYOVER"
NEXT_SHORT_STEP = "RESELECT_A1FS_V1_MAINLINE_AFTER_UNIT01_QB_RUNTIME_CLOSEOUT"
READBACK_NAME = "a1fs_v1_u01qb05_remediation_reassessment_carryover_readback.json"
REASSESSMENT_OUTPUT_DIR = "reassessment_completion"
SAFE_BLOCKED_KEYS = {
    "accepted_answers", "accepted_sequence", "accepted_texts", "answer_contract",
    "contract_json", "entries", "private_item_json", "response", "response_json",
    "responses", "rubric",
}


class RemediationAcceptanceError(ValueError):
    """Fail-closed U01QB05 error."""


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def assert_safe(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in SAFE_BLOCKED_KEYS:
                raise RemediationAcceptanceError(f"private_key_in_safe_readback:{key}")
            assert_safe(child)
    elif isinstance(value, list):
        for child in value:
            assert_safe(child)


def artifact(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return {"file_name": Path(path).name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def latest_item_attempt(database: Path, *, learner_id: str, item_id: str) -> dict[str, Any]:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """SELECT a.attempt_id,a.session_id,a.submitted_at,r.outcome,r.score,c.lesson_id,c.skill
               FROM response_attempts a
               JOIN scoring_results r USING(attempt_id)
               JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
               WHERE a.learner_id=? AND c.item_id=? ORDER BY a.rowid DESC LIMIT 1""",
            (learner_id, item_id),
        ).fetchone()
    if not row:
        raise RemediationAcceptanceError("failed_item_attempt_missing")
    return dict(row)


def active_session(database: Path, learner_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM learning_sessions WHERE learner_id=? AND session_state='ACTIVE'",
            (learner_id,),
        ).fetchone()
    return dict(row) if row else None


def prepare_reassessment(
    *, database: Path, learner_id: str, failed_item_id: str, reassessment_session_id: str
) -> dict[str, Any]:
    database = Path(database)
    latest = latest_item_attempt(database, learner_id=learner_id, item_id=failed_item_id)
    if latest["outcome"] != "AUTO_FAIL":
        raise RemediationAcceptanceError(f"latest_failed_item_outcome_invalid:{latest['outcome']}")
    with sqlite3.connect(database) as connection:
        previous = connection.execute(
            "SELECT session_state,learner_id,lesson_id FROM learning_sessions WHERE session_id=?",
            (latest["session_id"],),
        ).fetchone()
    if not previous or previous[0] != "COMPLETED" or previous[1] != learner_id or previous[2] != latest["lesson_id"]:
        raise RemediationAcceptanceError("source_failure_session_not_completed")
    current = active_session(database, learner_id)
    if current:
        if current["session_id"] != reassessment_session_id or current["lesson_id"] != latest["lesson_id"]:
            raise RemediationAcceptanceError("unexpected_active_session")
    else:
        m3.LearnerStateStore(database).start_session(
            learner_id=learner_id,
            lesson_id=latest["lesson_id"],
            session_id=reassessment_session_id,
        )
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    plan = runtime.assemble_session(
        learner_id=learner_id,
        session_id=reassessment_session_id,
    )
    selected = next((row for row in plan["items"] if row["item_id"] == failed_item_id), None)
    if not selected:
        raise RemediationAcceptanceError("failed_item_not_selected_for_reassessment")
    if selected.get("selection_reason") != "REMEDIATION":
        raise RemediationAcceptanceError(
            f"failed_item_selection_reason_invalid:{selected.get('selection_reason')}"
        )
    return {
        **plan,
        "source_failure_session_id": latest["session_id"],
        "failed_item_id": failed_item_id,
        "failed_item_selection_reason": "REMEDIATION",
        "answer_keys_exposed": False,
    }


def complete_reassessment_and_carryover(
    *,
    database: Path,
    learner_id: str,
    failed_item_id: str,
    reassessment_session_id: str,
    responses: Mapping[str, Any],
    carryover_session_id: str,
    output_root: Path,
    completed_at: str | None = None,
    carryover_ended_at: str | None = None,
) -> dict[str, Any]:
    database = Path(database)
    output_root = Path(output_root)
    prepared = prepare_reassessment(
        database=database,
        learner_id=learner_id,
        failed_item_id=failed_item_id,
        reassessment_session_id=reassessment_session_id,
    )
    latest_before = latest_item_attempt(database, learner_id=learner_id, item_id=failed_item_id)
    if latest_before["outcome"] != "AUTO_FAIL":
        raise RemediationAcceptanceError("source_failure_outcome_changed_before_reassessment")
    completion_root = output_root / REASSESSMENT_OUTPUT_DIR
    completion = qb04.complete_session(
        database=database,
        learner_id=learner_id,
        session_id=reassessment_session_id,
        responses=responses,
        output_root=completion_root,
        completed_at=completed_at,
    )
    latest_after = latest_item_attempt(database, learner_id=learner_id, item_id=failed_item_id)
    if latest_after["outcome"] != "AUTO_PASS" or latest_after["session_id"] != reassessment_session_id:
        raise RemediationAcceptanceError(
            f"failed_item_reassessment_not_passed:{latest_after['session_id']}:{latest_after['outcome']}"
        )
    if active_session(database, learner_id):
        raise RemediationAcceptanceError("active_session_remained_after_reassessment")
    m3.LearnerStateStore(database).start_session(
        learner_id=learner_id,
        lesson_id=latest_after["lesson_id"],
        session_id=carryover_session_id,
    )
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    carryover_plan = runtime.assemble_session(
        learner_id=learner_id,
        session_id=carryover_session_id,
    )
    carryover_ids = {row["item_id"] for row in carryover_plan["items"]}
    if failed_item_id in carryover_ids:
        raise RemediationAcceptanceError("reassessed_item_immediately_reselected")
    ended = m3.LearnerStateStore(database).end_session(
        session_id=carryover_session_id,
        outcome="ABANDONED",
        expected_session_version=1,
        at=carryover_ended_at,
    )
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        history = [
            dict(row)
            for row in connection.execute(
                """SELECT a.session_id,a.attempt_seq,r.outcome,r.score
                   FROM response_attempts a
                   JOIN scoring_results r USING(attempt_id)
                   JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
                   WHERE a.learner_id=? AND c.item_id=? ORDER BY a.rowid""",
                (learner_id, failed_item_id),
            )
        ]
        recent = [
            row[0]
            for row in connection.execute(
                """SELECT item_id FROM u01qb02_item_exposures
                   WHERE learner_id=? ORDER BY exposure_seq DESC LIMIT ?""",
                (learner_id, qb02.RECENT_EXPOSURE_WINDOW),
            )
        ]
    if [row["outcome"] for row in history] != ["AUTO_FAIL", "AUTO_PASS"]:
        raise RemediationAcceptanceError(f"failed_item_history_invalid:{history}")
    if failed_item_id not in recent:
        raise RemediationAcceptanceError("reassessed_item_missing_from_recent_window")
    completion_readback_path = completion_root / qb04.READBACK_NAME
    readback = {
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "learner_id": learner_id,
        "failed_item": {
            "item_id": failed_item_id,
            "source_failure_session_id": prepared["source_failure_session_id"],
            "source_outcome": "AUTO_FAIL",
        },
        "reassessment": {
            "session_id": reassessment_session_id,
            "selection_reason": "REMEDIATION",
            "outcome": "AUTO_PASS",
            "session_state": completion["session"]["session_state"],
            "session_version": completion["session"]["session_version"],
            "completed_item_count": completion["counts"]["completed_item_count"],
        },
        "carryover": {
            "session_id": carryover_session_id,
            "session_state": ended["session_state"],
            "session_version": ended["session_version"],
            "failed_item_reselected": False,
            "exclusion_gate": "RECENT_EXPOSURE_WINDOW",
            "recent_exposure_window": qb02.RECENT_EXPOSURE_WINDOW,
            "carryover_plan_item_count": carryover_plan["item_count"],
        },
        "failed_item_outcome_history": [
            {"session_id": row["session_id"], "outcome": row["outcome"]}
            for row in history
        ],
        "reassessment_completion_artifact": artifact(completion_readback_path),
        "claim_boundaries": {
            "parallel_planner_created": False,
            "parallel_learner_database_created": False,
            "parallel_response_capture_created": False,
            "parallel_scoring_created": False,
            "parallel_remediation_engine_created": False,
            "unit02_to_unit24_modified": False,
            "speaking_capture_enabled": False,
            "mastery_written": False,
            "retention_confirmed": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    assert_safe(readback)
    readback_path = output_root / READBACK_NAME
    atomic_json(readback_path, readback)
    return {**readback, "readback_path": str(readback_path)}


def load_responses(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RemediationAcceptanceError(f"responses_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise RemediationAcceptanceError("responses_not_object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    complete = commands.add_parser("complete")
    for command in (prepare, complete):
        command.add_argument("--database", type=Path, required=True)
        command.add_argument("--learner-id", required=True)
        command.add_argument("--failed-item-id", required=True)
        command.add_argument("--reassessment-session-id", required=True)
    complete.add_argument("--responses", type=Path, required=True)
    complete.add_argument("--carryover-session-id", required=True)
    complete.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        result = prepare_reassessment(
            database=args.database,
            learner_id=args.learner_id,
            failed_item_id=args.failed_item_id,
            reassessment_session_id=args.reassessment_session_id,
        )
    else:
        result = complete_reassessment_and_carryover(
            database=args.database,
            learner_id=args.learner_id,
            failed_item_id=args.failed_item_id,
            reassessment_session_id=args.reassessment_session_id,
            responses=load_responses(args.responses),
            carryover_session_id=args.carryover_session_id,
            output_root=args.output_root,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
