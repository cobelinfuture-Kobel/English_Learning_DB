#!/usr/bin/env python3
"""Independent validator for A1FS V1 M8 review and retention state."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-M8_ReviewSchedulingRetentionAndSpacedPractice"
STATUS = "PASS_A1FS_V1_M8_REVIEW_SCHEDULING_RETENTION_SPACED_PRACTICE"
M7_STATUS = "PASS_A1FS_V1_M7_MASTERY_REMEDIATION_REASSESSMENT"
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
FAIL_OUTCOMES = {"AUTO_FAIL", "HUMAN_REJECT"}
INTERVAL_DAYS = {1: 1, 2: 3, 3: 7}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode() if isinstance(value, str) else canonical(value).encode()
    return hashlib.sha256(raw).hexdigest()


def parse_at(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone_required")
    return parsed.astimezone(timezone.utc)


def load(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("json_not_object")
    return value, raw


def validate(
    database_path: Path,
    graph_path: Path,
    m7_snapshot_path: Path,
    retention_snapshot_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        graph, graph_raw = load(graph_path)
        m7, _ = load(m7_snapshot_path)
        snapshot, _ = load(retention_snapshot_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"source_unreadable:{exc}"]}
    graph_sha = digest(graph_raw)
    m7_digest = digest(m7)
    if m7.get("validation_status") != M7_STATUS:
        errors.append("m7_status_invalid")
    if snapshot.get("task_id") != TASK_ID or snapshot.get("validation_status") != STATUS:
        errors.append("snapshot_identity_invalid")
    if snapshot.get("source_graph_sha256") != graph_sha or snapshot.get("source_m7_snapshot_digest") != m7_digest:
        errors.append("snapshot_source_binding_invalid")
    required = set(graph.get("a2_lock_contract", {}).get("required_mastery_node_ids", []))
    retained = set(snapshot.get("retained_node_ids", []))
    if not retained <= required:
        errors.append("retained_nodes_outside_required_denominator")
    if snapshot.get("retention_confirmed") != (retained == required):
        errors.append("global_retention_flag_invalid")
    if snapshot.get("retained_required_count") != len(retained):
        errors.append("retained_count_invalid")
    if snapshot.get("interval_policy_days") != {"1": 1, "2": 3, "3": 7}:
        errors.append("interval_policy_invalid")
    for key, value in snapshot.get("claim_boundaries", {}).items():
        if value is not False:
            errors.append(f"claim_boundary_broken:{key}")
    try:
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error as exc:
        errors.append(f"database_unreadable:{exc}")
        connection = None
    if connection:
        with connection:
            metadata = dict(connection.execute("SELECT key,value FROM m8_metadata"))
            if (
                metadata.get("validation_status") != STATUS
                or metadata.get("source_graph_sha256") != graph_sha
                or metadata.get("source_m7_snapshot_digest") != m7_digest
            ):
                errors.append("m8_metadata_binding_invalid")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                errors.append("sqlite_integrity_failed")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                errors.append("foreign_key_check_failed")
            schedules = [
                dict(row) for row in connection.execute(
                    "SELECT * FROM review_schedules WHERE learner_id=? ORDER BY node_id,sequence_index",
                    (snapshot.get("learner_id"),),
                )
            ]
            events = [
                dict(row) for row in connection.execute(
                    "SELECT * FROM review_events WHERE learner_id=? ORDER BY attempted_at,review_event_id",
                    (snapshot.get("learner_id"),),
                )
            ]
            states = [
                dict(row) for row in connection.execute(
                    "SELECT * FROM retention_states WHERE learner_id=? ORDER BY node_id",
                    (snapshot.get("learner_id"),),
                )
            ]
            if (
                schedules != snapshot.get("review_schedules")
                or events != snapshot.get("review_events")
                or states != snapshot.get("retention_states")
            ):
                errors.append("snapshot_database_projection_drift")
            schedule_by_id = {row["schedule_id"]: row for row in schedules}
            events_by_node: dict[str, list[dict[str, Any]]] = {}
            for event in events:
                events_by_node.setdefault(event["node_id"], []).append(event)
                schedule = schedule_by_id.get(event["schedule_id"])
                if not schedule or schedule["evidence_attempt_id"] != event["attempt_id"]:
                    errors.append(f"event_schedule_binding_invalid:{event['review_event_id']}")
                if parse_at(event["attempted_at"]) < parse_at(event["due_at"]):
                    errors.append(f"review_before_due:{event['review_event_id']}")
                attempt = connection.execute(
                    """SELECT a.learner_id,a.submitted_at,l.asset_id,c.skill,a.lesson_id,s.outcome,ls.session_state
                    FROM response_attempts a JOIN lesson_assets l USING(asset_key) JOIN response_contracts c USING(asset_key)
                    JOIN scoring_results s USING(attempt_id) JOIN learning_sessions ls USING(session_id)
                    WHERE a.attempt_id=?""",
                    (event["attempt_id"],),
                ).fetchone()
                if (
                    not attempt
                    or attempt["learner_id"] != snapshot.get("learner_id")
                    or attempt["session_state"] != "COMPLETED"
                    or attempt["submitted_at"] != event["attempted_at"]
                    or attempt["outcome"] != event["attempt_outcome"]
                ):
                    errors.append(f"review_attempt_binding_invalid:{event['review_event_id']}")
                expected_result = "PASS" if event["attempt_outcome"] in PASS_OUTCOMES else "FAIL"
                if event["review_result"] != expected_result:
                    errors.append(f"review_result_invalid:{event['review_event_id']}")
            for node_id, state in {row["node_id"]: row for row in states}.items():
                consecutive = 0
                expected_state = "REVIEW_PENDING"
                last_at = None
                last_result = None
                for event in events_by_node.get(node_id, []):
                    last_at = event["attempted_at"]
                    last_result = event["review_result"]
                    if event["review_result"] == "PASS":
                        consecutive = min(3, consecutive + 1)
                        expected_state = "RETAINED" if consecutive == 3 else "REVIEW_PENDING"
                    else:
                        consecutive = 0
                        expected_state = "LAPSED"
                if (
                    state["consecutive_delayed_passes"] != consecutive
                    or state["retention_state"] != expected_state
                    or state["last_review_at"] != last_at
                    or state["last_review_result"] != last_result
                ):
                    errors.append(f"retention_state_rebuild_mismatch:{node_id}")
                if state["retention_state"] == "RETAINED" and (
                    state["next_due_at"] is not None or state["next_spacing_stage"] is not None
                ):
                    errors.append(f"retained_state_has_next_due:{node_id}")
                if state["retention_state"] != "RETAINED" and (
                    state["next_due_at"] is None or state["next_spacing_stage"] not in INTERVAL_DAYS
                ):
                    errors.append(f"pending_state_missing_next_due:{node_id}")
            stored = connection.execute(
                "SELECT 1 FROM retention_snapshots WHERE learner_id=? AND snapshot_digest=?",
                (snapshot.get("learner_id"), digest(snapshot)),
            ).fetchone()
            if not stored:
                errors.append("retention_snapshot_not_persisted")
        connection.close()
    return {
        "validation_status": STATUS if not errors else "FAIL_A1FS_V1_M8_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "retained_required_count": len(retained),
        "required_mastery_node_count": len(required),
        "retention_confirmed": snapshot.get("retention_confirmed"),
        "next_short_step": snapshot.get("next_short_step") if not errors else TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--m7-snapshot", type=Path, required=True)
    parser.add_argument("--retention-snapshot", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.database, args.graph, args.m7_snapshot, args.retention_snapshot)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
