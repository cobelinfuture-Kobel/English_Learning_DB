#!/usr/bin/env python3
"""Independent validator for A1FS V1 M7 mastery/remediation snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-M7_MasteryErrorDiagnosisRemediationAndReassessment"
STATUS = "PASS_A1FS_V1_M7_MASTERY_REMEDIATION_REASSESSMENT"
GRAPH_STATUS = "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE"
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
FAIL_OUTCOMES = {"AUTO_FAIL", "HUMAN_REJECT"}
UNRESOLVED_OUTCOMES = {"PENDING_HUMAN_REVIEW", "HUMAN_DEFER"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode() if isinstance(value, str) else canonical(value).encode()
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes(); value = json.loads(raw)
    if not isinstance(value, dict): raise ValueError("json_not_object")
    return value, raw


def validate(database_path: Path, graph_path: Path, snapshot_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        graph, graph_raw = load(graph_path); snapshot, _ = load(snapshot_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"source_unreadable:{exc}"]}
    graph_sha = digest(graph_raw)
    if graph.get("validation_status") != GRAPH_STATUS: errors.append("graph_status_invalid")
    if snapshot.get("task_id") != TASK_ID or snapshot.get("validation_status") != STATUS: errors.append("snapshot_identity_invalid")
    if snapshot.get("source_graph_sha256") != graph_sha: errors.append("snapshot_graph_binding_mismatch")
    required = set(graph.get("a2_lock_contract", {}).get("required_mastery_node_ids", []))
    mastered = set(snapshot.get("mastered_node_ids", [])); missing = set(snapshot.get("missing_mastery_node_ids", []))
    if mastered & missing or mastered | missing != required: errors.append("mastery_partition_invalid")
    if snapshot.get("required_mastery_node_count") != len(required): errors.append("required_count_mismatch")
    if snapshot.get("mastered_required_count") != len(mastered): errors.append("mastered_count_mismatch")
    if snapshot.get("a2_lock_state") != ("HANDOFF_READY" if mastered == required else "LOCKED"): errors.append("a2_lock_state_mismatch")
    boundaries = snapshot.get("claim_boundaries", {})
    for key in ("a2_payload_access_granted", "a2_session_start_granted", "retention_confirmed", "public_delivery", "human_pilot_claimed", "audio_evidence_used", "speaking_recording_used"):
        if boundaries.get(key) is not False: errors.append(f"claim_boundary_broken:{key}")
    expected_policy = {"minimum_resolved_attempts": 2, "minimum_pass_count": 2, "minimum_pass_rate": 0.8, "unresolved_allowed": 0, "recovery_after_failure_required": True, "lesson_session_must_be_completed": True}
    if snapshot.get("mastery_policy") != expected_policy: errors.append("mastery_policy_invalid")
    state_rows = snapshot.get("node_states", [])
    if len(state_rows) != len(required) or {row.get("node_id") for row in state_rows} != required: errors.append("node_state_denominator_invalid")
    state_by_node = {row.get("node_id"): row for row in state_rows}
    try:
        connection = sqlite3.connect(database_path); connection.row_factory = sqlite3.Row; connection.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error as exc:
        errors.append(f"database_unreadable:{exc}"); connection = None
    if connection:
        with connection:
            metadata = dict(connection.execute("SELECT key,value FROM m7_metadata"))
            if metadata.get("validation_status") != STATUS or metadata.get("source_graph_sha256") != graph_sha: errors.append("m7_metadata_binding_invalid")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok": errors.append("sqlite_integrity_failed")
            if connection.execute("PRAGMA foreign_key_check").fetchall(): errors.append("foreign_key_check_failed")
            attempt_rows = {row["attempt_id"]: dict(row) for row in connection.execute("""SELECT a.attempt_id,a.lesson_id,a.asset_key,l.asset_id,c.skill,s.outcome,ls.session_state
                FROM response_attempts a JOIN lesson_assets l USING(asset_key) JOIN response_contracts c USING(asset_key)
                JOIN scoring_results s USING(attempt_id) JOIN learning_sessions ls USING(session_id)
                WHERE a.learner_id=?""", (snapshot.get("learner_id"),))}
            node_lookup = {row["node_id"]: row for row in graph.get("nodes", [])}
            coverage = {row["node_id"]: row for row in graph.get("coverage", [])}
            for node_id, state in state_by_node.items():
                evidence_ids = state.get("evidence_attempt_ids", []); evidence = [attempt_rows.get(attempt_id) for attempt_id in evidence_ids]
                if any(row is None for row in evidence): errors.append(f"unknown_node_evidence:{node_id}"); continue
                for row in evidence:
                    mapped = row["lesson_id"] == node_lookup[node_id]["source_ref"] and row["skill"] == node_lookup[node_id]["skill"] if node_id.startswith("LESSON:") else row["asset_id"] in coverage.get(node_id, {}).get("asset_body_ids", [])
                    if not mapped or row["session_state"] != "COMPLETED": errors.append(f"node_evidence_mapping_invalid:{node_id}:{row['attempt_id']}")
                pass_count = sum(row["outcome"] in PASS_OUTCOMES for row in evidence)
                fail_count = sum(row["outcome"] in FAIL_OUTCOMES for row in evidence)
                unresolved_count = sum(row["outcome"] in UNRESOLVED_OUTCOMES for row in evidence)
                resolved = pass_count + fail_count; pass_rate = round(pass_count / resolved, 6) if resolved else 0.0
                if (state.get("pass_count"), state.get("fail_count"), state.get("unresolved_count"), state.get("resolved_attempt_count"), state.get("pass_rate")) != (pass_count, fail_count, unresolved_count, resolved, pass_rate): errors.append(f"node_state_counts_invalid:{node_id}")
                mastered_expected = state.get("lesson_completion_gate_satisfied") is True and resolved >= 2 and pass_count >= 2 and pass_rate >= 0.8 and unresolved_count == 0 and state.get("recovered_after_last_failure") is True
                if (state.get("mastery_state") == "MASTERED") != mastered_expected: errors.append(f"node_mastery_rebuild_mismatch:{node_id}")
            failures = {attempt_id for attempt_id, row in attempt_rows.items() if row["session_state"] == "COMPLETED" and row["outcome"] in FAIL_OUTCOMES}
            diagnoses = snapshot.get("error_diagnoses", [])
            if {row.get("attempt_id") for row in diagnoses} != failures: errors.append("failure_diagnosis_coverage_invalid")
            for row in diagnoses:
                if not row.get("node_ids") or not set(row["node_ids"]) <= required: errors.append(f"diagnosis_node_mapping_invalid:{row.get('diagnosis_id')}")
                expected_state = "RESOLVED_BY_REASSESSMENT" if all(node in mastered for node in row["node_ids"]) else "OPEN"
                if row.get("diagnosis_state") != expected_state: errors.append(f"diagnosis_state_invalid:{row.get('diagnosis_id')}")
            remediation = {row.get("node_id"): row for row in snapshot.get("remediation_assignments", [])}
            reassessment = {row.get("node_id"): row for row in snapshot.get("reassessment_queue", [])}
            diagnosed_nodes = {node for row in diagnoses for node in row.get("node_ids", [])}
            if set(remediation) != diagnosed_nodes or set(reassessment) != diagnosed_nodes: errors.append("remediation_reassessment_coverage_invalid")
            for node_id in diagnosed_nodes:
                completed = node_id in mastered
                if remediation[node_id].get("assignment_state") != ("COMPLETED" if completed else "OPEN"): errors.append(f"remediation_state_invalid:{node_id}")
                if reassessment[node_id].get("queue_state") != ("COMPLETED" if completed else "PENDING"): errors.append(f"reassessment_state_invalid:{node_id}")
            stored = connection.execute("SELECT snapshot_json,snapshot_digest FROM mastery_snapshots WHERE learner_id=? AND snapshot_digest=?", (snapshot.get("learner_id"), digest(snapshot))).fetchone()
            if not stored or json.loads(stored["snapshot_json"]) != snapshot: errors.append("snapshot_not_persisted_or_drifted")
        connection.close()
    return {"validation_status": STATUS if not errors else "FAIL_A1FS_V1_M7_VALIDATION", "error_count": len(errors), "errors": errors,
            "required_mastery_node_count": len(required), "mastered_required_count": len(mastered), "missing_mastery_count": len(missing),
            "a2_lock_state": snapshot.get("a2_lock_state"), "next_short_step": snapshot.get("next_short_step") if not errors else TASK_ID}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--database", type=Path, required=True); parser.add_argument("--graph", type=Path, required=True); parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args(); report = validate(args.database, args.graph, args.snapshot)
    print(json.dumps(report, ensure_ascii=False, indent=2)); return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__": raise SystemExit(main())
