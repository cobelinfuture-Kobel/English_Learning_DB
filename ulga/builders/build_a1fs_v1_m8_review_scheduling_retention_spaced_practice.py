#!/usr/bin/env python3
"""A1FS V1 M8 deterministic spaced-review scheduling and retention evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

TASK_ID = "A1FS-V1-M8_ReviewSchedulingRetentionAndSpacedPractice"
SCHEMA_VERSION = "a1fs.v1.m8.review_retention.v1"
STATUS = "PASS_A1FS_V1_M8_REVIEW_SCHEDULING_RETENTION_SPACED_PRACTICE"
GRAPH_STATUS = "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE"
M7_STATUS = "PASS_A1FS_V1_M7_MASTERY_REMEDIATION_REASSESSMENT"
NEXT_SHORT_STEP = "A1FS-V1-M9_TeacherDashboardProgressReportingAndExport"
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
FAIL_OUTCOMES = {"AUTO_FAIL", "HUMAN_REJECT"}
INTERVAL_DAYS = {1: 1, 2: 3, 3: 7}
OVERDUE_GRACE_DAYS = 7
RETAINED_PASS_COUNT = 3


class ReviewRetentionError(ValueError):
    """Fail-closed M8 error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_at(value: str | None = None) -> datetime:
    value = value or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewRetentionError("timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise ReviewRetentionError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewRetentionError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ReviewRetentionError(f"{code}_not_object")
    return value, raw


def write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    os.chmod(path, 0o600)


SQL = """
CREATE TABLE IF NOT EXISTS m8_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS review_schedules(
  schedule_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  sequence_index INTEGER NOT NULL CHECK(sequence_index >= 1),
  spacing_stage INTEGER NOT NULL CHECK(spacing_stage BETWEEN 1 AND 3),
  interval_days INTEGER NOT NULL CHECK(interval_days IN (1,3,7)),
  due_at TEXT NOT NULL,
  schedule_state TEXT NOT NULL CHECK(schedule_state IN('PENDING','DUE','OVERDUE','PASSED','FAILED')),
  source_m7_snapshot_digest TEXT NOT NULL,
  evidence_attempt_id TEXT,
  reviewed_at TEXT,
  created_at TEXT NOT NULL,
  schedule_digest TEXT NOT NULL UNIQUE,
  UNIQUE(learner_id,node_id,sequence_index)
);
CREATE TABLE IF NOT EXISTS review_events(
  review_event_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  schedule_id TEXT NOT NULL REFERENCES review_schedules(schedule_id),
  attempt_id TEXT NOT NULL,
  attempt_outcome TEXT NOT NULL CHECK(attempt_outcome IN('AUTO_PASS','AUTO_FAIL','HUMAN_APPROVE','HUMAN_REJECT')),
  review_result TEXT NOT NULL CHECK(review_result IN('PASS','FAIL')),
  attempted_at TEXT NOT NULL,
  due_at TEXT NOT NULL,
  event_digest TEXT NOT NULL UNIQUE,
  UNIQUE(schedule_id),
  UNIQUE(learner_id,node_id,attempt_id)
);
CREATE TABLE IF NOT EXISTS retention_states(
  learner_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  consecutive_delayed_passes INTEGER NOT NULL CHECK(consecutive_delayed_passes BETWEEN 0 AND 3),
  retention_state TEXT NOT NULL CHECK(retention_state IN('REVIEW_PENDING','RETAINED','LAPSED')),
  next_spacing_stage INTEGER,
  next_due_at TEXT,
  last_review_at TEXT,
  last_review_result TEXT,
  source_m7_snapshot_digest TEXT NOT NULL,
  state_digest TEXT NOT NULL,
  PRIMARY KEY(learner_id,node_id)
);
CREATE TABLE IF NOT EXISTS retention_snapshots(
  snapshot_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL,
  source_graph_sha256 TEXT NOT NULL,
  source_m7_snapshot_digest TEXT NOT NULL,
  snapshot_json TEXT NOT NULL,
  snapshot_digest TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);
"""


class ReviewRetentionEngine:
    def __init__(self, *, database_path: Path, graph_path: Path, m7_snapshot_path: Path):
        self.database_path = Path(database_path)
        self.graph_path = Path(graph_path)
        self.m7_snapshot_path = Path(m7_snapshot_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def sources(self) -> tuple[dict[str, Any], bytes, dict[str, Any], bytes]:
        graph, graph_raw = load_json(self.graph_path, "graph")
        snapshot, snapshot_raw = load_json(self.m7_snapshot_path, "m7_snapshot")
        if graph.get("validation_status") != GRAPH_STATUS:
            raise ReviewRetentionError("graph_status_invalid")
        if snapshot.get("validation_status") != M7_STATUS:
            raise ReviewRetentionError("m7_snapshot_status_invalid")
        if snapshot.get("source_graph_sha256") != digest(graph_raw):
            raise ReviewRetentionError("m7_snapshot_graph_binding_mismatch")
        required = set(graph.get("a2_lock_contract", {}).get("required_mastery_node_ids", []))
        if set(snapshot.get("mastered_node_ids", [])) | set(snapshot.get("missing_mastery_node_ids", [])) != required:
            raise ReviewRetentionError("m7_snapshot_mastery_partition_invalid")
        return graph, graph_raw, snapshot, snapshot_raw

    def initialize(self) -> dict[str, Any]:
        graph, graph_raw, snapshot, _ = self.sources()
        snapshot_digest = digest(snapshot)
        with self.connect() as connection:
            stored = connection.execute(
                "SELECT created_at FROM mastery_snapshots WHERE learner_id=? AND snapshot_digest=?",
                (snapshot["learner_id"], snapshot_digest),
            ).fetchone()
            if not stored:
                raise ReviewRetentionError("m7_snapshot_not_persisted")
            connection.executescript(SQL)
            values = {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": STATUS,
                "source_graph_sha256": digest(graph_raw),
                "source_m7_snapshot_digest": snapshot_digest,
                "interval_policy": canonical(INTERVAL_DAYS),
                "retained_pass_count": str(RETAINED_PASS_COUNT),
                "overdue_grace_days": str(OVERDUE_GRACE_DAYS),
                "a2_payload_access_granted": "false",
                "a2_session_start_granted": "false",
                "next_short_step": NEXT_SHORT_STEP,
            }
            connection.executemany("INSERT OR REPLACE INTO m8_metadata VALUES(?,?)", values.items())
            connection.commit()
        return {
            "validation_status": STATUS,
            "mastered_node_count": len(snapshot["mastered_node_ids"]),
            "required_mastery_node_count": len(graph["a2_lock_contract"]["required_mastery_node_ids"]),
            "next_short_step": NEXT_SHORT_STEP,
        }

    @staticmethod
    def _schedule_core(
        *, learner_id: str, node_id: str, sequence_index: int, spacing_stage: int,
        due_at: str, source_digest: str, created_at: str,
    ) -> dict[str, Any]:
        return {
            "learner_id": learner_id,
            "node_id": node_id,
            "sequence_index": sequence_index,
            "spacing_stage": spacing_stage,
            "interval_days": INTERVAL_DAYS[spacing_stage],
            "due_at": due_at,
            "source_m7_snapshot_digest": source_digest,
            "created_at": created_at,
        }

    def _insert_schedule(
        self,
        connection: sqlite3.Connection,
        *, learner_id: str, node_id: str, sequence_index: int, spacing_stage: int,
        due_at: datetime, source_digest: str, created_at: datetime,
    ) -> str:
        core = self._schedule_core(
            learner_id=learner_id,
            node_id=node_id,
            sequence_index=sequence_index,
            spacing_stage=spacing_stage,
            due_at=iso(due_at),
            source_digest=source_digest,
            created_at=iso(created_at),
        )
        schedule_id = f"M8_SCHEDULE:{digest(core)[:24]}"
        connection.execute(
            "INSERT INTO review_schedules VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                schedule_id, learner_id, node_id, sequence_index, spacing_stage,
                INTERVAL_DAYS[spacing_stage], iso(due_at), "PENDING", source_digest,
                None, None, iso(created_at), digest(core),
            ),
        )
        return schedule_id

    def build_schedule(self, *, learner_id: str, as_of: str | None = None) -> dict[str, Any]:
        _, _, snapshot, _ = self.sources()
        if snapshot["learner_id"] != learner_id:
            raise ReviewRetentionError("snapshot_learner_mismatch")
        now = parse_at(as_of)
        source_digest = digest(snapshot)
        mastered = set(snapshot["mastered_node_ids"])
        with self.connect() as connection:
            metadata = dict(connection.execute("SELECT key,value FROM m8_metadata"))
            if metadata.get("validation_status") != STATUS or metadata.get("source_m7_snapshot_digest") != source_digest:
                raise ReviewRetentionError("m8_not_initialized_for_snapshot")
            stored = connection.execute(
                "SELECT created_at FROM mastery_snapshots WHERE learner_id=? AND snapshot_digest=?",
                (learner_id, source_digest),
            ).fetchone()
            if not stored:
                raise ReviewRetentionError("m7_snapshot_not_persisted")
            anchor = parse_at(stored["created_at"])
            for node_id in sorted(mastered):
                existing = connection.execute(
                    "SELECT 1 FROM review_schedules WHERE learner_id=? AND node_id=?",
                    (learner_id, node_id),
                ).fetchone()
                if not existing:
                    due = anchor + timedelta(days=INTERVAL_DAYS[1])
                    self._insert_schedule(
                        connection,
                        learner_id=learner_id,
                        node_id=node_id,
                        sequence_index=1,
                        spacing_stage=1,
                        due_at=due,
                        source_digest=source_digest,
                        created_at=now,
                    )
                    state_core = {
                        "learner_id": learner_id,
                        "node_id": node_id,
                        "consecutive_delayed_passes": 0,
                        "retention_state": "REVIEW_PENDING",
                        "next_spacing_stage": 1,
                        "next_due_at": iso(due),
                        "last_review_at": None,
                        "last_review_result": None,
                        "source_m7_snapshot_digest": source_digest,
                    }
                    connection.execute(
                        "INSERT INTO retention_states VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (
                            learner_id, node_id, 0, "REVIEW_PENDING", 1, iso(due),
                            None, None, source_digest, digest(state_core),
                        ),
                    )
            rows = connection.execute(
                "SELECT schedule_id,due_at,schedule_state FROM review_schedules WHERE learner_id=? AND schedule_state IN('PENDING','DUE','OVERDUE')",
                (learner_id,),
            ).fetchall()
            for row in rows:
                due = parse_at(row["due_at"])
                state = "OVERDUE" if now > due + timedelta(days=OVERDUE_GRACE_DAYS) else "DUE" if now >= due else "PENDING"
                if state != row["schedule_state"]:
                    connection.execute(
                        "UPDATE review_schedules SET schedule_state=? WHERE schedule_id=?",
                        (state, row["schedule_id"]),
                    )
            connection.commit()
        return self.export_snapshot(learner_id=learner_id, output_root=None, as_of=iso(now))

    def _attempt_for_node(
        self,
        connection: sqlite3.Connection,
        *, learner_id: str, node_id: str, attempt_id: str, graph: Mapping[str, Any],
    ) -> sqlite3.Row:
        row = connection.execute(
            """SELECT a.attempt_id,a.learner_id,a.lesson_id,a.asset_key,a.submitted_at,l.asset_id,c.skill,s.outcome,ls.session_state
            FROM response_attempts a JOIN lesson_assets l USING(asset_key) JOIN response_contracts c USING(asset_key)
            JOIN scoring_results s USING(attempt_id) JOIN learning_sessions ls USING(session_id)
            WHERE a.attempt_id=?""",
            (attempt_id,),
        ).fetchone()
        if not row:
            raise ReviewRetentionError("review_attempt_not_found")
        if row["learner_id"] != learner_id:
            raise ReviewRetentionError("review_attempt_learner_mismatch")
        if row["session_state"] != "COMPLETED":
            raise ReviewRetentionError("review_attempt_session_not_completed")
        node = next((item for item in graph["nodes"] if item["node_id"] == node_id), None)
        if not node:
            raise ReviewRetentionError("review_node_not_in_graph")
        if node_id.startswith("LESSON:"):
            mapped = row["lesson_id"] == node["source_ref"] and row["skill"] == node["skill"]
        else:
            coverage = next((item for item in graph["coverage"] if item["node_id"] == node_id), None)
            mapped = bool(coverage and row["asset_id"] in coverage["asset_body_ids"])
        if not mapped:
            raise ReviewRetentionError("review_attempt_node_mapping_invalid")
        if row["outcome"] not in PASS_OUTCOMES | FAIL_OUTCOMES:
            raise ReviewRetentionError("review_attempt_outcome_unresolved")
        return row

    def record_review(self, *, learner_id: str, node_id: str, attempt_id: str) -> dict[str, Any]:
        graph, _, snapshot, _ = self.sources()
        if snapshot["learner_id"] != learner_id:
            raise ReviewRetentionError("snapshot_learner_mismatch")
        source_digest = digest(snapshot)
        if not any(item["node_id"] == node_id for item in graph["nodes"]):
            raise ReviewRetentionError("review_node_not_in_graph")
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            schedule = connection.execute(
                """SELECT * FROM review_schedules WHERE learner_id=? AND node_id=? AND schedule_state IN('PENDING','DUE','OVERDUE')
                ORDER BY sequence_index LIMIT 1""",
                (learner_id, node_id),
            ).fetchone()
            if not schedule:
                raise ReviewRetentionError("open_review_schedule_not_found")
            attempt = self._attempt_for_node(
                connection,
                learner_id=learner_id,
                node_id=node_id,
                attempt_id=attempt_id,
                graph=graph,
            )
            attempted_at = parse_at(attempt["submitted_at"])
            due_at = parse_at(schedule["due_at"])
            if attempted_at < due_at:
                raise ReviewRetentionError("review_attempt_before_due")
            passed = attempt["outcome"] in PASS_OUTCOMES
            result = "PASS" if passed else "FAIL"
            connection.execute(
                "UPDATE review_schedules SET schedule_state=?,evidence_attempt_id=?,reviewed_at=? WHERE schedule_id=?",
                ("PASSED" if passed else "FAILED", attempt_id, iso(attempted_at), schedule["schedule_id"]),
            )
            event_core = {
                "learner_id": learner_id,
                "node_id": node_id,
                "schedule_id": schedule["schedule_id"],
                "attempt_id": attempt_id,
                "attempt_outcome": attempt["outcome"],
                "review_result": result,
                "attempted_at": iso(attempted_at),
                "due_at": schedule["due_at"],
            }
            connection.execute(
                "INSERT INTO review_events VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    f"M8_EVENT:{digest(event_core)[:24]}", learner_id, node_id,
                    schedule["schedule_id"], attempt_id, attempt["outcome"], result,
                    iso(attempted_at), schedule["due_at"], digest(event_core),
                ),
            )
            retention = connection.execute(
                "SELECT * FROM retention_states WHERE learner_id=? AND node_id=?",
                (learner_id, node_id),
            ).fetchone()
            if not retention:
                raise ReviewRetentionError("retention_state_missing")
            consecutive = min(RETAINED_PASS_COUNT, retention["consecutive_delayed_passes"] + 1) if passed else 0
            retained = consecutive >= RETAINED_PASS_COUNT
            retention_state = "RETAINED" if retained else "REVIEW_PENDING" if passed else "LAPSED"
            next_stage = None if retained else min(RETAINED_PASS_COUNT, consecutive + 1) if passed else 1
            next_due = None
            if next_stage is not None:
                next_due_dt = attempted_at + timedelta(days=INTERVAL_DAYS[next_stage])
                next_due = iso(next_due_dt)
                next_sequence = connection.execute(
                    "SELECT COALESCE(MAX(sequence_index),0)+1 FROM review_schedules WHERE learner_id=? AND node_id=?",
                    (learner_id, node_id),
                ).fetchone()[0]
                self._insert_schedule(
                    connection,
                    learner_id=learner_id,
                    node_id=node_id,
                    sequence_index=next_sequence,
                    spacing_stage=next_stage,
                    due_at=next_due_dt,
                    source_digest=source_digest,
                    created_at=attempted_at,
                )
            state_core = {
                "learner_id": learner_id,
                "node_id": node_id,
                "consecutive_delayed_passes": consecutive,
                "retention_state": retention_state,
                "next_spacing_stage": next_stage,
                "next_due_at": next_due,
                "last_review_at": iso(attempted_at),
                "last_review_result": result,
                "source_m7_snapshot_digest": source_digest,
            }
            connection.execute(
                """UPDATE retention_states SET consecutive_delayed_passes=?,retention_state=?,next_spacing_stage=?,next_due_at=?,last_review_at=?,last_review_result=?,state_digest=? WHERE learner_id=? AND node_id=?""",
                (
                    consecutive, retention_state, next_stage, next_due, iso(attempted_at),
                    result, digest(state_core), learner_id, node_id,
                ),
            )
            connection.commit()
        return {
            "validation_status": STATUS,
            "node_id": node_id,
            "review_result": result,
            "consecutive_delayed_passes": consecutive,
            "retention_state": retention_state,
            "next_due_at": next_due,
            "node_retention_confirmed": retained,
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
            "next_short_step": NEXT_SHORT_STEP,
        }

    def export_snapshot(
        self,
        *, learner_id: str, output_root: Path | None, as_of: str | None = None,
    ) -> dict[str, Any]:
        graph, graph_raw, snapshot, _ = self.sources()
        if snapshot["learner_id"] != learner_id:
            raise ReviewRetentionError("snapshot_learner_mismatch")
        now = parse_at(as_of)
        source_digest = digest(snapshot)
        required = set(graph["a2_lock_contract"]["required_mastery_node_ids"])
        with self.connect() as connection:
            schedules = [
                dict(row) for row in connection.execute(
                    "SELECT * FROM review_schedules WHERE learner_id=? ORDER BY node_id,sequence_index",
                    (learner_id,),
                )
            ]
            states = [
                dict(row) for row in connection.execute(
                    "SELECT * FROM retention_states WHERE learner_id=? ORDER BY node_id",
                    (learner_id,),
                )
            ]
            events = [
                dict(row) for row in connection.execute(
                    "SELECT * FROM review_events WHERE learner_id=? ORDER BY attempted_at,review_event_id",
                    (learner_id,),
                )
            ]
        retained = sorted(row["node_id"] for row in states if row["retention_state"] == "RETAINED")
        all_required_retained = set(retained) == required
        value = {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": STATUS,
            "learner_id": learner_id,
            "source_graph_sha256": digest(graph_raw),
            "source_m7_snapshot_digest": source_digest,
            "as_of": iso(now),
            "required_mastery_node_count": len(required),
            "mastered_node_count": len(snapshot["mastered_node_ids"]),
            "scheduled_node_count": len(states),
            "retained_required_count": len(set(retained) & required),
            "retained_node_ids": retained,
            "retention_confirmed": all_required_retained,
            "review_schedules": schedules,
            "review_events": events,
            "retention_states": states,
            "interval_policy_days": {str(key): interval for key, interval in INTERVAL_DAYS.items()},
            "claim_boundaries": {
                "a2_payload_access_granted": False,
                "a2_session_start_granted": False,
                "public_delivery": False,
                "human_pilot_claimed": False,
                "audio_evidence_used": False,
                "speaking_recording_used": False,
            },
            "next_short_step": NEXT_SHORT_STEP,
        }
        snapshot_digest = digest(value)
        with self.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO retention_snapshots VALUES(?,?,?,?,?,?,?)",
                (
                    str(uuid.uuid4()), learner_id, digest(graph_raw), source_digest,
                    canonical(value), snapshot_digest, iso(now),
                ),
            )
            connection.commit()
        if output_root is not None:
            path = Path(output_root) / "a1fs_v1_m8_retention_snapshot.private.json"
            write_private(path, value)
            value = {**value, "snapshot_path": str(path), "snapshot_sha256": snapshot_digest}
        return value


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--database", type=Path, required=True)
    init.add_argument("--graph", type=Path, required=True)
    init.add_argument("--m7-snapshot", type=Path, required=True)
    schedule = commands.add_parser("schedule")
    schedule.add_argument("--database", type=Path, required=True)
    schedule.add_argument("--graph", type=Path, required=True)
    schedule.add_argument("--m7-snapshot", type=Path, required=True)
    schedule.add_argument("--learner-id", required=True)
    schedule.add_argument("--as-of")
    review = commands.add_parser("record-review")
    review.add_argument("--database", type=Path, required=True)
    review.add_argument("--graph", type=Path, required=True)
    review.add_argument("--m7-snapshot", type=Path, required=True)
    review.add_argument("--learner-id", required=True)
    review.add_argument("--node-id", required=True)
    review.add_argument("--attempt-id", required=True)
    export = commands.add_parser("export")
    export.add_argument("--database", type=Path, required=True)
    export.add_argument("--graph", type=Path, required=True)
    export.add_argument("--m7-snapshot", type=Path, required=True)
    export.add_argument("--learner-id", required=True)
    export.add_argument("--output-root", type=Path, required=True)
    export.add_argument("--as-of")
    args = parser.parse_args()
    engine = ReviewRetentionEngine(
        database_path=args.database,
        graph_path=args.graph,
        m7_snapshot_path=args.m7_snapshot,
    )
    if args.command == "init":
        result = engine.initialize()
    elif args.command == "schedule":
        result = engine.build_schedule(learner_id=args.learner_id, as_of=args.as_of)
    elif args.command == "record-review":
        result = engine.record_review(
            learner_id=args.learner_id,
            node_id=args.node_id,
            attempt_id=args.attempt_id,
        )
    else:
        result = engine.export_snapshot(
            learner_id=args.learner_id,
            output_root=args.output_root,
            as_of=args.as_of,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
