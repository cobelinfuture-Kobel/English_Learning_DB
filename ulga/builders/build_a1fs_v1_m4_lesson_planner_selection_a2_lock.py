#!/usr/bin/env python3
"""Deterministic four-skill lesson planner and fail-closed A2 lock.

Task: A1FS-V1-M4_LessonPlannerSelectionAndA2Lock
The planner sequences A1/A1+ exposure.  It can declare an A2 handoff ready
only from a graph-bound M7 mastery snapshot; it never returns A2 payload or
starts an A2 session.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-M4_LessonPlannerSelectionAndA2Lock"
SCHEMA_VERSION = "a1fs.v1.m4.lesson_planner.v1"
STATUS = "PASS_A1FS_V1_M4_LESSON_PLANNER_AND_A2_LOCK_READY"
GRAPH_STATUS = "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE"
CONSUMER_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
STATE_STATUS = "PASS_A1FS_V1_M3_LEARNER_PROFILE_SESSION_STATE_STORAGE_READY"
MASTERY_SNAPSHOT_STATUS = "PASS_A1FS_V1_M7_MASTERY_REMEDIATION_REASSESSMENT"
NEXT_SHORT_STEP = "A1FS-V1-M5_FourSkillRendererAndLearnerUI"
SKILL_ORDER = {"LISTENING": 0, "SPEAKING": 1, "READING": 2, "WRITING": 3}
LEVEL_ORDER = {"A1": 0, "A1+": 1}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class PlannerError(ValueError):
    """Fail-closed planner error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes(); value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise PlannerError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict): raise PlannerError(f"{code}_not_object")
    return value, raw


def _at(value: str | None = None) -> str:
    if value is None: return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise PlannerError("timestamp_invalid") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed): raise PlannerError("timestamp_must_be_utc")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _id(value: str, code: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value): raise PlannerError(f"{code}_invalid")
    return value


PLANNER_SQL = """
CREATE TABLE IF NOT EXISTS planner_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS planner_decisions(
  decision_seq INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_id TEXT NOT NULL UNIQUE,
  learner_id TEXT NOT NULL,
  plan_status TEXT NOT NULL CHECK(plan_status IN ('RESUME_ACTIVE_SESSION','PLAN_LEARNING_LESSON','AWAITING_MASTERY_EVIDENCE','A2_HANDOFF_READY')),
  selected_lesson_id TEXT,
  selected_skill TEXT,
  selected_level TEXT,
  a2_lock_state TEXT NOT NULL CHECK(a2_lock_state IN ('LOCKED','HANDOFF_READY')),
  required_mastery_count INTEGER NOT NULL,
  missing_mastery_count INTEGER NOT NULL,
  state_snapshot_digest TEXT NOT NULL,
  rationale_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  previous_hash TEXT NOT NULL,
  decision_hash TEXT NOT NULL UNIQUE
);
"""


class LessonPlanner:
    def __init__(self, *, database_path: Path, consumer_path: Path, graph_path: Path):
        self.database_path = Path(database_path); self.consumer_path = Path(consumer_path); self.graph_path = Path(graph_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path); connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON"); connection.execute("PRAGMA busy_timeout=5000"); return connection

    def _sources(self) -> tuple[dict[str, Any], bytes, dict[str, Any], bytes]:
        consumer, consumer_raw = _load(self.consumer_path, "consumer"); graph, graph_raw = _load(self.graph_path, "graph")
        if consumer.get("validation_status") != CONSUMER_STATUS: raise PlannerError("consumer_status_invalid")
        if graph.get("validation_status") != GRAPH_STATUS: raise PlannerError("graph_status_invalid")
        if consumer.get("source_graph_sha256") != _sha(graph_raw): raise PlannerError("consumer_graph_binding_invalid")
        return consumer, consumer_raw, graph, graph_raw

    def initialize(self) -> dict[str, Any]:
        consumer, consumer_raw, graph, graph_raw = self._sources()
        if not self.database_path.is_file(): raise PlannerError("state_database_missing")
        connection = self._connect()
        try:
            metadata = {row[0]: row[1] for row in connection.execute("SELECT key,value FROM metadata")}
            if metadata.get("validation_status") != STATE_STATUS or metadata.get("consumer_sha256") != _sha(consumer_raw):
                raise PlannerError("state_consumer_binding_invalid")
            connection.executescript(PLANNER_SQL)
            values = {"task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": STATUS,
                      "consumer_sha256": _sha(consumer_raw), "graph_sha256": _sha(graph_raw),
                      "a2_payload_access_granted": "false", "a2_session_start_granted": "false", "next_short_step": NEXT_SHORT_STEP}
            connection.executemany("INSERT OR REPLACE INTO planner_metadata(key,value) VALUES(?,?)", values.items()); connection.commit()
        finally: connection.close()
        return {"validation_status": STATUS, "required_mastery_node_count": graph["counts"]["required_mastery_node_count"],
                "learning_lesson_count": consumer["counts"]["learning_lesson_count"], "next_short_step": NEXT_SHORT_STEP}

    def evaluate_a2_lock(self, *, learner_id: str, mastery_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        learner_id = _id(learner_id, "learner_id"); _, _, graph, graph_raw = self._sources()
        required = set(graph["a2_lock_contract"]["required_mastery_node_ids"])
        mastered: set[str] = set(); authority_valid = False
        if mastery_snapshot is not None:
            authority_valid = (
                mastery_snapshot.get("validation_status") == MASTERY_SNAPSHOT_STATUS
                and mastery_snapshot.get("learner_id") == learner_id
                and mastery_snapshot.get("source_graph_sha256") == _sha(graph_raw)
                and isinstance(mastery_snapshot.get("mastered_node_ids"), list)
            )
            if authority_valid: mastered = set(mastery_snapshot["mastered_node_ids"]) & required
        missing = sorted(required - mastered)
        ready = authority_valid and not missing
        return {
            "learner_id": learner_id, "a2_lock_state": "HANDOFF_READY" if ready else "LOCKED",
            "mastery_authority_valid": authority_valid, "required_mastery_count": len(required),
            "mastered_required_count": len(mastered), "missing_mastery_count": len(missing),
            "missing_mastery_node_ids": missing,
            "unlock_rule": "ALL_REQUIRED_MASTERY_NODES_MUST_BE_MASTERED",
            "a2_payload_access_granted": False, "a2_session_start_granted": False,
        }

    @staticmethod
    def _sequence_rank(graph: dict[str, Any]) -> dict[str, int]:
        lessons = {row["node_id"]: row for row in graph["nodes"] if row.get("node_type") == "LESSON" and row.get("level") in {"A1", "A1+"}}
        predecessors: dict[str, set[str]] = {node: set() for node in lessons}
        successors: dict[str, set[str]] = {node: set() for node in lessons}
        for edge in graph["edges"]:
            if edge["edge_type"] == "PRECEDES" and edge["from_node_id"] in lessons and edge["to_node_id"] in lessons:
                predecessors[edge["to_node_id"]].add(edge["from_node_id"]); successors[edge["from_node_id"]].add(edge["to_node_id"])
        queue = sorted((node for node, incoming in predecessors.items() if not incoming), key=lambda n: (SKILL_ORDER[lessons[n]["skill"]], n))
        ranks: dict[str, int] = {}; index = 0
        while queue:
            node = queue.pop(0); ranks[node] = index; index += 1
            for target in sorted(successors[node]):
                predecessors[target].discard(node)
                if not predecessors[target]: queue.append(target)
            queue.sort(key=lambda n: (SKILL_ORDER[lessons[n]["skill"]], n))
        if len(ranks) != len(lessons): raise PlannerError("learning_graph_not_acyclic")
        return ranks

    def plan_next(self, *, learner_id: str, preferred_skill: str | None = None,
                  mastery_snapshot: dict[str, Any] | None = None, plan_id: str | None = None,
                  at: str | None = None) -> dict[str, Any]:
        learner_id = _id(learner_id, "learner_id"); plan_id = _id(plan_id or str(uuid.uuid4()), "plan_id"); at = _at(at)
        if preferred_skill is not None and preferred_skill not in SKILL_ORDER: raise PlannerError("preferred_skill_invalid")
        consumer, _, graph, _ = self._sources(); lock = self.evaluate_a2_lock(learner_id=learner_id, mastery_snapshot=mastery_snapshot)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            profile = connection.execute("SELECT * FROM learner_profiles WHERE learner_id=?", (learner_id,)).fetchone()
            if not profile or profile["profile_state"] != "ACTIVE": raise PlannerError("learner_profile_not_active")
            active = connection.execute("SELECT * FROM learning_sessions WHERE learner_id=? AND session_state='ACTIVE'", (learner_id,)).fetchone()
            completed = {row[0] for row in connection.execute("SELECT DISTINCT lesson_id FROM learning_sessions WHERE learner_id=? AND session_state='COMPLETED'", (learner_id,))}
            progress = {row["lesson_id"]: dict(row) for row in connection.execute("SELECT * FROM lesson_progress WHERE learner_id=?", (learner_id,))}
            session_counts = {skill: 0 for skill in SKILL_ORDER}
            for row in connection.execute("SELECT skill,COUNT(*) count FROM learning_sessions WHERE learner_id=? AND session_state='COMPLETED' GROUP BY skill", (learner_id,)):
                session_counts[row["skill"]] = row["count"]
            selected: dict[str, Any] | None = None; rationale: dict[str, Any]
            if active:
                plan_status = "RESUME_ACTIVE_SESSION"
                selected = next(row for row in consumer["lesson_catalog"] if row["lesson_id"] == active["lesson_id"])
                rationale = {"reason": "ACTIVE_SESSION_MUST_RESUME", "session_id": active["session_id"]}
            elif lock["a2_lock_state"] == "HANDOFF_READY":
                plan_status = "A2_HANDOFF_READY"
                handoff = [row for row in consumer["lesson_catalog"] if row["level"] == "A2" and (preferred_skill is None or row["skill"] == preferred_skill)]
                handoff.sort(key=lambda row: (SKILL_ORDER[row["skill"]], row["lesson_id"]))
                selected = handoff[0] if handoff else None
                rationale = {"reason": "ALL_REQUIRED_MASTERY_NODES_MASTERED", "handoff_metadata_only": True}
            else:
                learning = [row for row in consumer["lesson_catalog"] if row["level"] in {"A1", "A1+"}]
                graph_node_by_lesson = {row["source_ref"]: row["node_id"] for row in graph["nodes"] if row.get("node_type") == "LESSON"}
                predecessor_lessons: dict[str, set[str]] = {row["lesson_id"]: set() for row in learning}
                node_to_lesson = {node: lesson for lesson, node in graph_node_by_lesson.items()}
                for edge in graph["edges"]:
                    if edge["edge_type"] == "PRECEDES" and edge["to_node_id"] in node_to_lesson and edge["from_node_id"] in node_to_lesson:
                        target = node_to_lesson[edge["to_node_id"]]; source = node_to_lesson[edge["from_node_id"]]
                        if target in predecessor_lessons: predecessor_lessons[target].add(source)
                eligible = [row for row in learning if row["lesson_id"] not in completed and predecessor_lessons[row["lesson_id"]] <= completed]
                if preferred_skill is not None: eligible = [row for row in eligible if row["skill"] == preferred_skill]
                ranks = self._sequence_rank(graph)
                eligible.sort(key=lambda row: (
                    0 if progress.get(row["lesson_id"], {}).get("exposure_count", 0) > 0 else 1,
                    session_counts[row["skill"]], SKILL_ORDER[row["skill"]], LEVEL_ORDER[row["level"]],
                    ranks[graph_node_by_lesson[row["lesson_id"]]], row["lesson_id"],
                ))
                if eligible:
                    plan_status = "PLAN_LEARNING_LESSON"; selected = eligible[0]
                    rationale = {"reason": "PREREQUISITES_SATISFIED_BALANCED_SKILL_SELECTION",
                                 "predecessor_lesson_ids": sorted(predecessor_lessons[selected["lesson_id"]]),
                                 "completed_session_counts_by_skill": session_counts,
                                 "resume_exposed_lesson": progress.get(selected["lesson_id"], {}).get("exposure_count", 0) > 0}
                else:
                    plan_status = "AWAITING_MASTERY_EVIDENCE"
                    rationale = {"reason": "NO_UNSEEN_ELIGIBLE_LESSON_A2_STILL_LOCKED", "completed_learning_lesson_count": len(completed)}
            selected_id = selected["lesson_id"] if selected else None
            selected_skill = selected["skill"] if selected else None; selected_level = selected["level"] if selected else None
            snapshot_core = {"learner_id": learner_id, "completed": sorted(completed), "progress": progress,
                             "session_counts": session_counts, "active_session_id": active["session_id"] if active else None,
                             "a2_lock_state": lock["a2_lock_state"], "missing_mastery_count": lock["missing_mastery_count"]}
            snapshot_digest = _sha(_canonical(snapshot_core).encode("utf-8"))
            previous_row = connection.execute("SELECT decision_hash FROM planner_decisions ORDER BY decision_seq DESC LIMIT 1").fetchone()
            previous_hash = previous_row[0] if previous_row else "0" * 64
            decision_core = {"plan_id": plan_id, "learner_id": learner_id, "plan_status": plan_status,
                             "selected_lesson_id": selected_id, "selected_skill": selected_skill, "selected_level": selected_level,
                             "a2_lock_state": lock["a2_lock_state"], "required_mastery_count": lock["required_mastery_count"],
                             "missing_mastery_count": lock["missing_mastery_count"], "state_snapshot_digest": snapshot_digest,
                             "rationale": rationale, "created_at": at}
            decision_hash = _sha((previous_hash + _canonical(decision_core)).encode("utf-8"))
            connection.execute("""INSERT INTO planner_decisions
                (plan_id,learner_id,plan_status,selected_lesson_id,selected_skill,selected_level,a2_lock_state,required_mastery_count,missing_mastery_count,state_snapshot_digest,rationale_json,created_at,previous_hash,decision_hash)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (plan_id, learner_id, plan_status, selected_id, selected_skill, selected_level, lock["a2_lock_state"],
                 lock["required_mastery_count"], lock["missing_mastery_count"], snapshot_digest, _canonical(rationale), at, previous_hash, decision_hash))
            connection.commit()
        except Exception:
            connection.rollback(); raise
        finally: connection.close()
        selected_metadata = None if not selected else {key: selected[key] for key in ("lesson_id", "lesson_node_id", "skill", "level", "roles", "requirement_node_ids")}
        return {"task_id": TASK_ID, "validation_status": STATUS, "plan_id": plan_id, "learner_id": learner_id,
                "plan_status": plan_status, "selected_lesson": selected_metadata, "rationale": rationale,
                "a2_lock": lock, "a2_payload_included": False, "a2_session_started": False,
                "next_short_step": NEXT_SHORT_STEP}


def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "plan", "lock-status"):
        item = sub.add_parser(command); item.add_argument("--database", type=Path, required=True); item.add_argument("--consumer", type=Path, required=True); item.add_argument("--graph", type=Path, required=True)
        if command != "init": item.add_argument("--learner-id", required=True); item.add_argument("--mastery-snapshot", type=Path)
        if command == "plan": item.add_argument("--preferred-skill"); item.add_argument("--plan-id")
    args = parser.parse_args(); planner = LessonPlanner(database_path=args.database, consumer_path=args.consumer, graph_path=args.graph)
    if args.command == "init": result = planner.initialize()
    else:
        mastery = _load(args.mastery_snapshot, "mastery_snapshot")[0] if args.mastery_snapshot else None
        result = planner.evaluate_a2_lock(learner_id=args.learner_id, mastery_snapshot=mastery) if args.command == "lock-status" else planner.plan_next(learner_id=args.learner_id, preferred_skill=args.preferred_skill, mastery_snapshot=mastery, plan_id=args.plan_id)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
