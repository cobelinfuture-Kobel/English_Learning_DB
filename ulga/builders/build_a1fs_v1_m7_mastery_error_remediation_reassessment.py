#!/usr/bin/env python3
"""Build graph-bound A1/A1+ mastery, diagnosis, remediation, and reassessment state."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

TASK_ID = "A1FS-V1-M7_MasteryErrorDiagnosisRemediationAndReassessment"
SCHEMA_VERSION = "a1fs.v1.m7.mastery_remediation_reassessment.v1"
STATUS = "PASS_A1FS_V1_M7_MASTERY_REMEDIATION_REASSESSMENT"
GRAPH_STATUS = "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE"
M6_STATUS = "PASS_A1FS_V1_M6_RESPONSE_CAPTURE_SCORING_M12_EVIDENCE_READY"
NEXT_SHORT_STEP = "A1FS-V1-M8_ReviewSchedulingRetentionAndSpacedPractice"
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
FAIL_OUTCOMES = {"AUTO_FAIL", "HUMAN_REJECT"}
UNRESOLVED_OUTCOMES = {"PENDING_HUMAN_REVIEW", "HUMAN_DEFER"}
MIN_RESOLVED_ATTEMPTS = 2
MIN_PASS_COUNT = 2
MIN_PASS_RATE = 0.80


class MasteryError(ValueError):
    """Fail-closed M7 error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def timestamp(value: str | None = None) -> str:
    value = value or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MasteryError("timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise MasteryError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, code: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes(); value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise MasteryError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise MasteryError(f"{code}_not_object")
    return value, raw


def write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path); os.chmod(path, 0o600)


SQL = """
CREATE TABLE IF NOT EXISTS m7_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS error_diagnoses(
  diagnosis_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
  node_ids_json TEXT NOT NULL, error_tags_json TEXT NOT NULL, severity TEXT NOT NULL,
  diagnosis_state TEXT NOT NULL CHECK(diagnosis_state IN('OPEN','RESOLVED_BY_REASSESSMENT')),
  created_at TEXT NOT NULL, diagnosis_digest TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS remediation_assignments(
  remediation_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, node_id TEXT NOT NULL,
  source_attempt_ids_json TEXT NOT NULL, strategy TEXT NOT NULL, priority TEXT NOT NULL,
  assignment_state TEXT NOT NULL CHECK(assignment_state IN('OPEN','COMPLETED')),
  created_at TEXT NOT NULL, assignment_digest TEXT NOT NULL UNIQUE,
  UNIQUE(learner_id,node_id)
);
CREATE TABLE IF NOT EXISTS reassessment_queue(
  reassessment_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, node_id TEXT NOT NULL,
  source_remediation_id TEXT NOT NULL, lesson_ids_json TEXT NOT NULL, asset_keys_json TEXT NOT NULL,
  queue_state TEXT NOT NULL CHECK(queue_state IN('PENDING','COMPLETED')),
  created_at TEXT NOT NULL, queue_digest TEXT NOT NULL UNIQUE,
  UNIQUE(learner_id,node_id)
);
CREATE TABLE IF NOT EXISTS mastery_snapshots(
  snapshot_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, source_graph_sha256 TEXT NOT NULL,
  snapshot_json TEXT NOT NULL, snapshot_digest TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL
);
"""


def _diagnostic_tags(row: Mapping[str, Any]) -> list[str]:
    tags = [f"skill_{str(row['skill']).casefold()}"]
    mode = row["scoring_mode"]
    if mode == "EXACT_SEQUENCE": tags.append("sequence_order_error")
    elif mode in {"EXACT_OPTION", "NORMALIZED_TEXT"}: tags.append("response_mismatch")
    else:
        criteria = json.loads(row["criteria_json"])
        mapping = {
            "grammar_target_match": "grammar_target_mismatch",
            "meaning_matches_context": "meaning_context_mismatch",
            "complete_response": "incomplete_response",
        }
        tags.extend(mapping[key] for key, value in criteria.items() if value is False)
        if len(tags) == 1: tags.append("rubric_rejection")
    return sorted(set(tags))


def _strategy(tags: set[str]) -> str:
    if "sequence_order_error" in tags: return "REBUILD_SEQUENCE_WITH_GUIDED_ORDER"
    if "grammar_target_mismatch" in tags: return "RETEACH_GRAMMAR_WITH_MINIMAL_PAIRS"
    if "meaning_context_mismatch" in tags: return "RECONTEXTUALIZE_MEANING_AND_RETRY"
    if "incomplete_response" in tags: return "MODEL_COMPLETE_RESPONSE_THEN_RETRY"
    return "RETEACH_TARGET_WITH_CONTRAST_AND_RETRY"


def _node_state(node_id: str, evidence: list[Mapping[str, Any]], lesson_completed: bool) -> dict[str, Any]:
    completed = [row for row in evidence if row["session_state"] == "COMPLETED"]
    passes = [row for row in completed if row["outcome"] in PASS_OUTCOMES]
    failures = [row for row in completed if row["outcome"] in FAIL_OUTCOMES]
    unresolved = [row for row in completed if row["outcome"] in UNRESOLVED_OUTCOMES]
    resolved = passes + failures
    pass_rate = len(passes) / len(resolved) if resolved else 0.0
    last_failure_index = max((index for index, row in enumerate(completed) if row["outcome"] in FAIL_OUTCOMES), default=-1)
    recovered = last_failure_index < 0 or any(index > last_failure_index and row["outcome"] in PASS_OUTCOMES for index, row in enumerate(completed))
    lesson_gate = lesson_completed if node_id.startswith("LESSON:") else True
    mastered = lesson_gate and len(resolved) >= MIN_RESOLVED_ATTEMPTS and len(passes) >= MIN_PASS_COUNT and pass_rate >= MIN_PASS_RATE and not unresolved and recovered
    return {
        "node_id": node_id, "mastery_state": "MASTERED" if mastered else "NOT_MASTERED",
        "resolved_attempt_count": len(resolved), "pass_count": len(passes), "fail_count": len(failures),
        "unresolved_count": len(unresolved), "pass_rate": round(pass_rate, 6),
        "lesson_completion_gate_satisfied": lesson_gate, "recovered_after_last_failure": recovered,
        "evidence_attempt_ids": [row["attempt_id"] for row in completed],
        "failure_attempt_ids": [row["attempt_id"] for row in failures],
    }


class MasteryRemediationEngine:
    def __init__(self, *, database_path: Path, graph_path: Path):
        self.database_path = Path(database_path); self.graph_path = Path(graph_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path); connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON"); connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _graph(self) -> tuple[dict[str, Any], bytes]:
        graph, raw = load_json(self.graph_path, "graph")
        if graph.get("validation_status") != GRAPH_STATUS: raise MasteryError("graph_status_invalid")
        required = graph.get("a2_lock_contract", {}).get("required_mastery_node_ids")
        if not isinstance(required, list) or len(required) != graph.get("counts", {}).get("required_mastery_node_count"):
            raise MasteryError("required_mastery_denominator_invalid")
        return graph, raw

    def initialize(self) -> dict[str, Any]:
        graph, graph_raw = self._graph()
        with self.connect() as connection:
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            if metadata.get("m6_validation_status") != M6_STATUS: raise MasteryError("m6_database_status_invalid")
            planner = dict(connection.execute("SELECT key,value FROM planner_metadata")) if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='planner_metadata'").fetchone() else {}
            if planner and planner.get("graph_sha256") != digest(graph_raw): raise MasteryError("planner_graph_binding_mismatch")
            connection.executescript(SQL)
            values = {
                "task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": STATUS,
                "source_graph_sha256": digest(graph_raw), "mastery_policy": canonical({"minimum_resolved_attempts": MIN_RESOLVED_ATTEMPTS, "minimum_pass_count": MIN_PASS_COUNT, "minimum_pass_rate": MIN_PASS_RATE, "unresolved_allowed": 0, "recovery_after_failure_required": True}),
                "a2_payload_access_granted": "false", "a2_session_start_granted": "false", "next_short_step": NEXT_SHORT_STEP,
            }
            connection.executemany("INSERT OR REPLACE INTO m7_metadata VALUES(?,?)", values.items()); connection.commit()
        return {"validation_status": STATUS, "required_mastery_node_count": len(graph["a2_lock_contract"]["required_mastery_node_ids"]), "next_short_step": NEXT_SHORT_STEP}

    def build_snapshot(self, *, learner_id: str, output_root: Path, created_at: str | None = None) -> dict[str, Any]:
        graph, graph_raw = self._graph(); created_at = timestamp(created_at)
        graph_sha = digest(graph_raw); required = set(graph["a2_lock_contract"]["required_mastery_node_ids"])
        nodes = {row["node_id"]: row for row in graph["nodes"]}
        coverage = {row["node_id"]: row for row in graph["coverage"]}
        asset_to_nodes: dict[str, set[str]] = defaultdict(set)
        for node_id, row in coverage.items():
            if node_id in required:
                for asset_id in row["asset_body_ids"]: asset_to_nodes[str(asset_id)].add(node_id)
        with self.connect() as connection:
            profile = connection.execute("SELECT profile_state FROM learner_profiles WHERE learner_id=?", (learner_id,)).fetchone()
            if not profile or profile[0] != "ACTIVE": raise MasteryError("learner_profile_not_active")
            meta = dict(connection.execute("SELECT key,value FROM m7_metadata"))
            if meta.get("validation_status") != STATUS or meta.get("source_graph_sha256") != graph_sha: raise MasteryError("m7_not_initialized_for_graph")
            attempts = [dict(row) for row in connection.execute("""SELECT a.attempt_id,a.lesson_id,a.asset_key,a.attempt_sequence,a.submitted_at,l.asset_id,
                c.skill,c.role,s.scoring_mode,s.outcome,s.score,q.criteria_json,ls.session_state
                FROM response_attempts a JOIN lesson_assets l USING(asset_key) JOIN response_contracts c USING(asset_key)
                JOIN scoring_results s USING(attempt_id) JOIN human_review_queue q USING(attempt_id)
                JOIN learning_sessions ls USING(session_id) WHERE a.learner_id=?
                ORDER BY a.submitted_at,a.attempt_sequence,a.attempt_id""", (learner_id,))]
            completed_lessons = {row[0] for row in connection.execute("SELECT DISTINCT lesson_id FROM learning_sessions WHERE learner_id=? AND session_state='COMPLETED'", (learner_id,))}
            evidence_by_node: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in attempts:
                lesson_node = f"LESSON:{row['skill']}:{row['lesson_id']}"
                if lesson_node in required: evidence_by_node[lesson_node].append(row)
                for node_id in asset_to_nodes.get(str(row["asset_id"]), set()): evidence_by_node[node_id].append(row)
            node_states = []
            for node_id in sorted(required):
                lesson_completed = nodes[node_id]["source_ref"] in completed_lessons if node_id.startswith("LESSON:") else True
                node_states.append(_node_state(node_id, evidence_by_node.get(node_id, []), lesson_completed))
            mastered = sorted(row["node_id"] for row in node_states if row["mastery_state"] == "MASTERED")
            state_by_node = {row["node_id"]: row for row in node_states}
            attempt_nodes: dict[str, set[str]] = defaultdict(set)
            for node_id, rows in evidence_by_node.items():
                for row in rows: attempt_nodes[row["attempt_id"]].add(node_id)
            diagnoses = []
            for row in attempts:
                if row["session_state"] != "COMPLETED" or row["outcome"] not in FAIL_OUTCOMES: continue
                linked = sorted(attempt_nodes[row["attempt_id"]]); tags = _diagnostic_tags(row)
                resolved = bool(linked) and all(state_by_node[node_id]["mastery_state"] == "MASTERED" for node_id in linked)
                core = {"learner_id": learner_id, "attempt_id": row["attempt_id"], "node_ids": linked, "error_tags": tags, "severity": "HIGH" if row["outcome"] == "HUMAN_REJECT" else "MEDIUM", "diagnosis_state": "RESOLVED_BY_REASSESSMENT" if resolved else "OPEN"}
                diagnoses.append({"diagnosis_id": f"M7_DIAG:{digest(core)[:24]}", **core, "created_at": created_at})
            remediation, reassessment = [], []
            open_failures: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for diagnosis in diagnoses:
                for node_id in diagnosis["node_ids"]: open_failures[node_id].append(diagnosis)
            for node_id in sorted(open_failures):
                state = state_by_node[node_id]; diagnosis_rows = open_failures[node_id]
                tags = {tag for row in diagnosis_rows for tag in row["error_tags"]}
                completed = state["mastery_state"] == "MASTERED"
                source_attempts = sorted({row["attempt_id"] for row in diagnosis_rows})
                core = {"learner_id": learner_id, "node_id": node_id, "source_attempt_ids": source_attempts, "strategy": _strategy(tags), "priority": "P0" if not completed else "P2_HISTORY", "assignment_state": "COMPLETED" if completed else "OPEN"}
                remediation_id = f"M7_REMED:{digest(core)[:24]}"; remediation.append({"remediation_id": remediation_id, **core, "created_at": created_at})
                coverage_row = coverage.get(node_id, {})
                lesson_ids = sorted(set(coverage_row.get("lesson_ids", [])) | ({nodes[node_id]["source_ref"]} if node_id.startswith("LESSON:") else set()))
                failed_asset_keys = sorted({row["asset_key"] for row in attempts if row["attempt_id"] in source_attempts})
                queue_core = {"learner_id": learner_id, "node_id": node_id, "source_remediation_id": remediation_id, "lesson_ids": lesson_ids, "asset_keys": failed_asset_keys, "queue_state": "COMPLETED" if completed else "PENDING"}
                reassessment.append({"reassessment_id": f"M7_REASSESS:{digest(queue_core)[:24]}", **queue_core, "created_at": created_at})
            snapshot = {
                "task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": STATUS,
                "learner_id": learner_id, "source_graph_sha256": graph_sha,
                "required_mastery_node_count": len(required), "mastered_required_count": len(mastered),
                "mastered_node_ids": mastered, "missing_mastery_node_ids": sorted(required - set(mastered)),
                "node_states": node_states, "error_diagnoses": diagnoses,
                "remediation_assignments": remediation, "reassessment_queue": reassessment,
                "a2_lock_state": "HANDOFF_READY" if len(mastered) == len(required) else "LOCKED",
                "mastery_policy": {"minimum_resolved_attempts": MIN_RESOLVED_ATTEMPTS, "minimum_pass_count": MIN_PASS_COUNT, "minimum_pass_rate": MIN_PASS_RATE, "unresolved_allowed": 0, "recovery_after_failure_required": True, "lesson_session_must_be_completed": True},
                "claim_boundaries": {"a2_payload_access_granted": False, "a2_session_start_granted": False, "retention_confirmed": False, "public_delivery": False, "human_pilot_claimed": False, "audio_evidence_used": False, "speaking_recording_used": False},
                "next_short_step": NEXT_SHORT_STEP,
            }
            snapshot_digest = digest(snapshot); snapshot_id = str(uuid.uuid4())
            connection.execute("DELETE FROM error_diagnoses WHERE learner_id=?", (learner_id,)); connection.execute("DELETE FROM reassessment_queue WHERE learner_id=?", (learner_id,)); connection.execute("DELETE FROM remediation_assignments WHERE learner_id=?", (learner_id,))
            for row in diagnoses:
                core = {key: row[key] for key in ("learner_id", "attempt_id", "node_ids", "error_tags", "severity", "diagnosis_state")}
                connection.execute("INSERT INTO error_diagnoses VALUES(?,?,?,?,?,?,?,?,?)", (row["diagnosis_id"], learner_id, row["attempt_id"], canonical(row["node_ids"]), canonical(row["error_tags"]), row["severity"], row["diagnosis_state"], created_at, digest(core)))
            for row in remediation:
                core = {key: row[key] for key in ("learner_id", "node_id", "source_attempt_ids", "strategy", "priority", "assignment_state")}
                connection.execute("INSERT INTO remediation_assignments VALUES(?,?,?,?,?,?,?,?,?)", (row["remediation_id"], learner_id, row["node_id"], canonical(row["source_attempt_ids"]), row["strategy"], row["priority"], row["assignment_state"], created_at, digest(core)))
            for row in reassessment:
                core = {key: row[key] for key in ("learner_id", "node_id", "source_remediation_id", "lesson_ids", "asset_keys", "queue_state")}
                connection.execute("INSERT INTO reassessment_queue VALUES(?,?,?,?,?,?,?,?,?)", (row["reassessment_id"], learner_id, row["node_id"], row["source_remediation_id"], canonical(row["lesson_ids"]), canonical(row["asset_keys"]), row["queue_state"], created_at, digest(core)))
            connection.execute("INSERT OR IGNORE INTO mastery_snapshots VALUES(?,?,?,?,?,?)", (snapshot_id, learner_id, graph_sha, canonical(snapshot), snapshot_digest, created_at)); connection.commit()
        output_path = Path(output_root) / "a1fs_v1_m7_mastery_snapshot.private.json"; write_private(output_path, snapshot)
        return {"validation_status": STATUS, "snapshot_path": str(output_path), "snapshot_sha256": snapshot_digest, "mastered_required_count": len(mastered), "missing_mastery_count": len(required) - len(mastered), "open_remediation_count": sum(row["assignment_state"] == "OPEN" for row in remediation), "pending_reassessment_count": sum(row["queue_state"] == "PENDING" for row in reassessment), "a2_lock_state": snapshot["a2_lock_state"], "next_short_step": NEXT_SHORT_STEP}


def main() -> int:
    parser = argparse.ArgumentParser(); commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init"); init.add_argument("--database", type=Path, required=True); init.add_argument("--graph", type=Path, required=True)
    build = commands.add_parser("build"); build.add_argument("--database", type=Path, required=True); build.add_argument("--graph", type=Path, required=True); build.add_argument("--learner-id", required=True); build.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(); engine = MasteryRemediationEngine(database_path=args.database, graph_path=args.graph)
    result = engine.initialize() if args.command == "init" else engine.build_snapshot(learner_id=args.learner_id, output_root=args.output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
