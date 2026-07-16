from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ulga.builders.build_a1fs_v1_m4_lesson_planner_selection_a2_lock import LessonPlanner
from ulga.builders.build_a1fs_v1_m6_response_capture_scoring_m12_evidence import ResponseEvidenceStore
from ulga.builders.build_a1fs_v1_m7_mastery_error_remediation_reassessment import MasteryError, MasteryRemediationEngine
from ulga.validators.validate_a1fs_v1_m7_mastery_error_remediation_reassessment import validate


def _hash(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()


def _fixture(tmp_path: Path):
    assets = [
        {"asset_key": "R1:CHK", "asset_id": "A-R1-CHK", "lesson_id": "R1", "skill": "READING", "level": "A1", "role": "CHK", "payload": {"question": "How does Mia travel?", "answer": "bus"}},
        {"asset_key": "R1:PRD", "asset_id": "A-R1-PRD", "lesson_id": "R1", "skill": "READING", "level": "A1", "role": "PRD", "payload": {"prompt": "Write one sentence.", "scoring_rubric": {"grammar": "present simple"}}},
    ]
    for asset in assets: asset["content_digest"] = hashlib.sha256(json.dumps(asset["payload"], sort_keys=True).encode()).hexdigest()
    catalog = [{"lesson_id": "R1", "lesson_node_id": "LESSON:READING:R1", "skill": "READING", "level": "A1", "roles": ["CHK", "PRD"], "requirement_node_ids": ["REF:READING:C1"], "asset_keys": ["R1:CHK", "R1:PRD"]}]
    graph = {
        "task_id": "A1FS-V1-M1_A1A1PlusPrerequisiteGraphAndCoverage", "schema_version": "a1fs.v1.m1.prerequisite_graph_and_coverage.v1",
        "validation_status": "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE", "source_baseline_sha256": "b" * 64,
        "nodes": [
            {"node_id": "LESSON:READING:R1", "node_type": "LESSON", "skill": "READING", "level": "A1", "source_ref": "R1", "mastery_required_before_a2": True},
            {"node_id": "REF:READING:C1", "node_type": "CAPABILITY", "skill": "READING", "level": "A1", "source_ref": "C1", "mastery_required_before_a2": True},
            {"node_id": "GATE:A1FS:A2_LOCK", "node_type": "A2_LOCK", "skill": "FOUR_SKILL", "level": "A2", "source_ref": "A2_ENTRY", "mastery_required_before_a2": False},
        ],
        "edges": [
            {"from_node_id": "REF:READING:C1", "to_node_id": "LESSON:READING:R1", "edge_type": "TAUGHT_BY"},
            {"from_node_id": "LESSON:READING:R1", "to_node_id": "GATE:A1FS:A2_LOCK", "edge_type": "UNLOCK_REQUIRES"},
            {"from_node_id": "REF:READING:C1", "to_node_id": "GATE:A1FS:A2_LOCK", "edge_type": "UNLOCK_REQUIRES"},
        ],
        "coverage": [{"node_id": "REF:READING:C1", "skill": "READING", "source_ref": "C1", "coverage_class": "MASTERY", "levels": ["A1"], "lesson_ids": ["R1"], "asset_body_ids": ["A-R1-CHK", "A-R1-PRD"], "roles": ["CHK", "PRD"], "coverage_status": "COVERED"}],
        "counts": {"node_count": 3, "edge_count": 3, "coverage_record_count": 1, "lesson_count": 1, "lesson_count_by_level": {"A1": 1, "A1+": 0, "A2": 0}, "required_mastery_node_count": 2, "a2_handoff_lesson_count": 0, "uncovered_required_node_count": 0},
        "a2_lock_contract": {"gate_node_id": "GATE:A1FS:A2_LOCK", "state": "LOCKED_BY_DESIGN", "required_mastery_node_ids": ["LESSON:READING:R1", "REF:READING:C1"], "a2_handoff_lesson_node_ids": [], "unlock_rule": "ALL_REQUIRED_MASTERY_NODES_MUST_BE_MASTERED", "runtime_unlock_implemented": False},
        "claim_boundaries": {"source_packages_committed": False, "asset_body_content_modified": False, "learner_release_approved": False, "mastery_claimed": False, "a2_unlocked": False, "runtime_planner_implemented": False, "human_pilot_claimed": False, "listening_audio_complete": False},
        "errors": [], "next_short_step": "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery",
    }
    graph_path = tmp_path / "graph.json"; graph_path.write_text(json.dumps(graph), encoding="utf-8")
    consumer = {"validation_status": "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY", "source_graph_sha256": _hash(graph_path.read_bytes()), "lesson_catalog": catalog, "asset_records": assets, "counts": {"lesson_count": 1, "asset_record_count": 2, "learning_lesson_count": 1}}
    consumer_path = tmp_path / "consumer.json"; consumer_path.write_text(json.dumps(consumer), encoding="utf-8")
    bundle = {"validation_status": "PASS_A1FS_V1_M5_FOUR_SKILL_RENDERER_LEARNER_UI_READY", "source_consumer_sha256": _hash(consumer_path.read_bytes()), "lesson": {key: catalog[0][key] for key in ("lesson_id", "lesson_node_id", "skill", "level", "roles", "requirement_node_ids")}, "assets": [{"asset_key": row["asset_key"], "role": row["role"]} for row in assets]}
    bundle_path = tmp_path / "bundle.json"; bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    database = tmp_path / "state.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE lesson_catalog(lesson_id TEXT PRIMARY KEY,lesson_node_id TEXT UNIQUE,skill TEXT,level TEXT,roles_json TEXT,requirement_node_ids_json TEXT,payload_access_allowed INTEGER);
        CREATE TABLE lesson_assets(asset_key TEXT PRIMARY KEY,asset_id TEXT,lesson_id TEXT REFERENCES lesson_catalog(lesson_id),role TEXT,content_digest TEXT);
        CREATE TABLE learner_profiles(learner_id TEXT PRIMARY KEY,display_label TEXT,locale TEXT,timezone_name TEXT,profile_state TEXT,profile_version INTEGER,created_at TEXT,updated_at TEXT);
        CREATE TABLE learning_sessions(session_id TEXT PRIMARY KEY,learner_id TEXT REFERENCES learner_profiles(learner_id),lesson_id TEXT REFERENCES lesson_catalog(lesson_id),skill TEXT,level TEXT,session_state TEXT,session_version INTEGER,started_at TEXT,ended_at TEXT);
        CREATE TABLE lesson_progress(learner_id TEXT,lesson_id TEXT,skill TEXT,level TEXT,progress_state TEXT,exposure_count INTEGER,progress_version INTEGER,first_seen_at TEXT,last_seen_at TEXT,PRIMARY KEY(learner_id,lesson_id));
        CREATE TABLE state_events(event_seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE,learner_id TEXT,session_id TEXT,event_type TEXT,event_at TEXT,payload_json TEXT,previous_hash TEXT,event_hash TEXT UNIQUE);
        """)
        connection.executemany("INSERT INTO metadata VALUES(?,?)", {"validation_status": "PASS_A1FS_V1_M3_LEARNER_PROFILE_SESSION_STATE_STORAGE_READY", "consumer_sha256": _hash(consumer_path.read_bytes()), "mastery_write_enabled": "false"}.items())
        connection.execute("INSERT INTO lesson_catalog VALUES(?,?,?,?,?,?,?)", ("R1", "LESSON:READING:R1", "READING", "A1", json.dumps(["CHK", "PRD"]), json.dumps(["REF:READING:C1"]), 1))
        for row in assets: connection.execute("INSERT INTO lesson_assets VALUES(?,?,?,?,?)", (row["asset_key"], row["asset_id"], "R1", row["role"], row["content_digest"]))
        connection.execute("INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)", ("learner", "Learner", "zh-TW", "Asia/Taipei", "ACTIVE", 1, "2026-07-16T00:00:00Z", "2026-07-16T00:00:00Z"))
    m6 = ResponseEvidenceStore(database); m6.initialize(consumer_path=consumer_path, lesson_bundle_path=bundle_path)
    m7 = MasteryRemediationEngine(database_path=database, graph_path=graph_path); m7.initialize()
    return database, graph_path, consumer_path, m6, m7


def _session(database: Path, session_id: str, state: str = "ACTIVE") -> None:
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO learning_sessions VALUES(?,?,?,?,?,?,?,?,?)", (session_id, "learner", "R1", "READING", "A1", state, 1, "2026-07-16T00:00:00Z", None if state == "ACTIVE" else "2026-07-16T00:10:00Z"))


def _complete(database: Path, session_id: str) -> None:
    with sqlite3.connect(database) as connection: connection.execute("UPDATE learning_sessions SET session_state='COMPLETED',ended_at='2026-07-16T00:10:00Z' WHERE session_id=?", (session_id,))


def test_two_passes_master_required_nodes_and_unlock_handoff_only(tmp_path: Path) -> None:
    database, graph, consumer, m6, m7 = _fixture(tmp_path); _session(database, "s1")
    m6.capture_response(learner_id="learner", session_id="s1", asset_key="R1:CHK", response="bus", expected_session_version=1, submitted_at="2026-07-16T00:01:00Z")
    m6.capture_response(learner_id="learner", session_id="s1", asset_key="R1:CHK", response="Bus.", expected_session_version=2, submitted_at="2026-07-16T00:02:00Z"); _complete(database, "s1")
    result = m7.build_snapshot(learner_id="learner", output_root=tmp_path / "out")
    snapshot = json.loads(Path(result["snapshot_path"]).read_text())
    assert snapshot["mastered_required_count"] == 2 and snapshot["a2_lock_state"] == "HANDOFF_READY"
    assert snapshot["claim_boundaries"]["a2_payload_access_granted"] is False
    planner = LessonPlanner(database_path=database, consumer_path=consumer, graph_path=graph)
    lock = planner.evaluate_a2_lock(learner_id="learner", mastery_snapshot=snapshot)
    assert lock["a2_lock_state"] == "HANDOFF_READY" and lock["a2_payload_access_granted"] is False
    schema = json.loads(Path("ulga/schemas/a1fs_v1_m7_mastery_snapshot.schema.json").read_text())
    assert not list(Draft202012Validator(schema).iter_errors(snapshot))
    report = validate(database, graph, Path(result["snapshot_path"])); assert report["error_count"] == 0, report["errors"]


def test_failure_creates_diagnosis_remediation_and_reassessment(tmp_path: Path) -> None:
    database, graph, _, m6, m7 = _fixture(tmp_path); _session(database, "s1")
    m6.capture_response(learner_id="learner", session_id="s1", asset_key="R1:CHK", response="train", expected_session_version=1, submitted_at="2026-07-16T00:01:00Z"); _complete(database, "s1")
    result = m7.build_snapshot(learner_id="learner", output_root=tmp_path / "out"); snapshot = json.loads(Path(result["snapshot_path"]).read_text())
    assert snapshot["mastered_required_count"] == 0 and len(snapshot["error_diagnoses"]) == 1
    assert {row["assignment_state"] for row in snapshot["remediation_assignments"]} == {"OPEN"}
    assert {row["queue_state"] for row in snapshot["reassessment_queue"]} == {"PENDING"}
    assert "response_mismatch" in snapshot["error_diagnoses"][0]["error_tags"]


def test_unresolved_productive_review_blocks_mastery(tmp_path: Path) -> None:
    database, _, _, m6, m7 = _fixture(tmp_path); _session(database, "s1")
    m6.capture_response(learner_id="learner", session_id="s1", asset_key="R1:CHK", response="bus", expected_session_version=1, submitted_at="2026-07-16T00:01:00Z")
    m6.capture_response(learner_id="learner", session_id="s1", asset_key="R1:CHK", response="bus", expected_session_version=2, submitted_at="2026-07-16T00:02:00Z")
    m6.capture_response(learner_id="learner", session_id="s1", asset_key="R1:PRD", response="Mia travels by bus.", expected_session_version=3, submitted_at="2026-07-16T00:03:00Z"); _complete(database, "s1")
    result = m7.build_snapshot(learner_id="learner", output_root=tmp_path / "out"); snapshot = json.loads(Path(result["snapshot_path"]).read_text())
    assert snapshot["mastered_required_count"] == 0
    assert all(row["unresolved_count"] == 1 for row in snapshot["node_states"])


def test_failure_then_four_passes_closes_remediation(tmp_path: Path) -> None:
    database, _, _, m6, m7 = _fixture(tmp_path); _session(database, "s1")
    responses = ["train", "bus", "bus", "bus", "bus"]
    for index, response in enumerate(responses, start=1):
        m6.capture_response(learner_id="learner", session_id="s1", asset_key="R1:CHK", response=response, expected_session_version=index, submitted_at=f"2026-07-16T00:0{index}:00Z")
    _complete(database, "s1")
    result = m7.build_snapshot(learner_id="learner", output_root=tmp_path / "out"); snapshot = json.loads(Path(result["snapshot_path"]).read_text())
    assert snapshot["mastered_required_count"] == 2
    assert {row["diagnosis_state"] for row in snapshot["error_diagnoses"]} == {"RESOLVED_BY_REASSESSMENT"}
    assert {row["assignment_state"] for row in snapshot["remediation_assignments"]} == {"COMPLETED"}
    assert {row["queue_state"] for row in snapshot["reassessment_queue"]} == {"COMPLETED"}


def test_active_session_evidence_is_not_decisive(tmp_path: Path) -> None:
    database, _, _, m6, m7 = _fixture(tmp_path); _session(database, "s1")
    m6.capture_response(learner_id="learner", session_id="s1", asset_key="R1:CHK", response="bus", expected_session_version=1)
    m6.capture_response(learner_id="learner", session_id="s1", asset_key="R1:CHK", response="bus", expected_session_version=2)
    result = m7.build_snapshot(learner_id="learner", output_root=tmp_path / "out"); snapshot = json.loads(Path(result["snapshot_path"]).read_text())
    assert snapshot["mastered_required_count"] == 0
    assert all(not row["evidence_attempt_ids"] for row in snapshot["node_states"])


def test_graph_drift_and_snapshot_tampering_fail_closed(tmp_path: Path) -> None:
    database, graph, _, m6, m7 = _fixture(tmp_path); _session(database, "s1")
    m6.capture_response(learner_id="learner", session_id="s1", asset_key="R1:CHK", response="bus", expected_session_version=1)
    m6.capture_response(learner_id="learner", session_id="s1", asset_key="R1:CHK", response="bus", expected_session_version=2); _complete(database, "s1")
    result = m7.build_snapshot(learner_id="learner", output_root=tmp_path / "out"); snapshot_path = Path(result["snapshot_path"])
    snapshot = json.loads(snapshot_path.read_text()); snapshot["a2_lock_state"] = "LOCKED"; snapshot_path.write_text(json.dumps(snapshot))
    report = validate(database, graph, snapshot_path); assert report["error_count"] > 0
    graph_value = json.loads(graph.read_text()); graph_value["source_baseline_sha256"] = "c" * 64; graph.write_text(json.dumps(graph_value))
    with pytest.raises(MasteryError, match="m7_not_initialized_for_graph"):
        m7.build_snapshot(learner_id="learner", output_root=tmp_path / "drift")
