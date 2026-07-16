from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ulga.builders.build_a1fs_v1_m8_review_scheduling_retention_spaced_practice import (
    ReviewRetentionEngine,
    ReviewRetentionError,
)
from ulga.validators.validate_a1fs_v1_m8_review_scheduling_retention_spaced_practice import validate


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fixture(tmp_path: Path):
    graph = {
        "validation_status": "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE",
        "nodes": [
            {"node_id": "LESSON:READING:R1", "node_type": "LESSON", "skill": "READING", "level": "A1", "source_ref": "R1", "mastery_required_before_a2": True},
            {"node_id": "REF:READING:C1", "node_type": "CAPABILITY", "skill": "READING", "level": "A1", "source_ref": "C1", "mastery_required_before_a2": True},
        ],
        "coverage": [
            {"node_id": "REF:READING:C1", "skill": "READING", "source_ref": "C1", "asset_body_ids": ["A-R1-CHK"], "lesson_ids": ["R1"]}
        ],
        "a2_lock_contract": {
            "required_mastery_node_ids": ["LESSON:READING:R1", "REF:READING:C1"]
        },
    }
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    m7 = {
        "task_id": "A1FS-V1-M7_MasteryErrorDiagnosisRemediationAndReassessment",
        "validation_status": "PASS_A1FS_V1_M7_MASTERY_REMEDIATION_REASSESSMENT",
        "learner_id": "learner",
        "source_graph_sha256": _digest(graph_path.read_bytes()),
        "mastered_node_ids": ["LESSON:READING:R1", "REF:READING:C1"],
        "missing_mastery_node_ids": [],
    }
    m7_path = tmp_path / "m7.json"
    m7_path.write_text(json.dumps(m7), encoding="utf-8")
    database = tmp_path / "state.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys=ON;
            CREATE TABLE lesson_assets(asset_key TEXT PRIMARY KEY,asset_id TEXT,lesson_id TEXT,role TEXT,content_digest TEXT);
            CREATE TABLE learner_profiles(learner_id TEXT PRIMARY KEY,display_label TEXT,locale TEXT,timezone_name TEXT,profile_state TEXT,profile_version INTEGER,created_at TEXT,updated_at TEXT);
            CREATE TABLE learning_sessions(session_id TEXT PRIMARY KEY,learner_id TEXT,lesson_id TEXT,skill TEXT,level TEXT,session_state TEXT,session_version INTEGER,started_at TEXT,ended_at TEXT);
            CREATE TABLE response_contracts(asset_key TEXT PRIMARY KEY,lesson_id TEXT,skill TEXT,role TEXT,contract_json TEXT,contract_digest TEXT,capture_enabled INTEGER);
            CREATE TABLE response_attempts(attempt_id TEXT PRIMARY KEY,learner_id TEXT,session_id TEXT,lesson_id TEXT,asset_key TEXT,attempt_sequence INTEGER,response_json TEXT,submitted_at TEXT,previous_hash TEXT,attempt_hash TEXT);
            CREATE TABLE scoring_results(attempt_id TEXT PRIMARY KEY,scoring_mode TEXT,outcome TEXT,score REAL,human_review_required INTEGER,scored_at TEXT,contract_digest TEXT);
            CREATE TABLE mastery_snapshots(snapshot_id TEXT PRIMARY KEY,learner_id TEXT,source_graph_sha256 TEXT,snapshot_json TEXT,snapshot_digest TEXT UNIQUE,created_at TEXT);
            """
        )
        connection.execute(
            "INSERT INTO lesson_assets VALUES(?,?,?,?,?)",
            ("R1:CHK", "A-R1-CHK", "R1", "CHK", "d" * 64),
        )
        connection.execute(
            "INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)",
            ("learner", "Learner", "zh-TW", "Asia/Taipei", "ACTIVE", 1, "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
        )
        contract = {"skill": "READING", "role": "CHK"}
        connection.execute(
            "INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)",
            (
                "R1:CHK", "R1", "READING", "CHK", json.dumps(contract),
                hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest(), 1,
            ),
        )
        connection.execute(
            "INSERT INTO mastery_snapshots VALUES(?,?,?,?,?,?)",
            (
                "m7", "learner", _digest(graph_path.read_bytes()), json.dumps(m7),
                hashlib.sha256(json.dumps(m7, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "2026-07-01T00:00:00Z",
            ),
        )
    engine = ReviewRetentionEngine(
        database_path=database,
        graph_path=graph_path,
        m7_snapshot_path=m7_path,
    )
    engine.initialize()
    return database, graph_path, m7_path, engine


def _attempt(
    database: Path,
    attempt_id: str,
    submitted_at: str,
    outcome: str,
    *,
    session_state: str = "COMPLETED",
) -> None:
    session_id = f"session-{attempt_id}"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO learning_sessions VALUES(?,?,?,?,?,?,?,?,?)",
            (
                session_id, "learner", "R1", "READING", "A1", session_state, 1,
                submitted_at, submitted_at if session_state == "COMPLETED" else None,
            ),
        )
        connection.execute(
            "INSERT INTO response_attempts VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                attempt_id, "learner", session_id, "R1", "R1:CHK", 1,
                json.dumps("bus"), submitted_at, "0" * 64,
                attempt_id.ljust(64, "0")[:64],
            ),
        )
        score = 1.0 if outcome in {"AUTO_PASS", "HUMAN_APPROVE"} else 0.0 if outcome in {"AUTO_FAIL", "HUMAN_REJECT"} else None
        connection.execute(
            "INSERT INTO scoring_results VALUES(?,?,?,?,?,?,?)",
            (
                attempt_id, "NORMALIZED_TEXT", outcome, score,
                int(outcome == "PENDING_HUMAN_REVIEW"), submitted_at, "c" * 64,
            ),
        )


def test_initial_schedule_transitions_to_due(tmp_path: Path) -> None:
    _, _, _, engine = _fixture(tmp_path)
    early = engine.build_schedule(learner_id="learner", as_of="2026-07-01T12:00:00Z")
    assert early["scheduled_node_count"] == 2
    assert {row["schedule_state"] for row in early["review_schedules"]} == {"PENDING"}
    due = engine.build_schedule(learner_id="learner", as_of="2026-07-02T00:00:00Z")
    assert {row["schedule_state"] for row in due["review_schedules"]} == {"DUE"}
    assert due["retention_confirmed"] is False


def test_review_before_due_fails_closed(tmp_path: Path) -> None:
    database, _, _, engine = _fixture(tmp_path)
    engine.build_schedule(learner_id="learner", as_of="2026-07-01T00:00:00Z")
    _attempt(database, "a1", "2026-07-01T12:00:00Z", "AUTO_PASS")
    with pytest.raises(ReviewRetentionError, match="review_attempt_before_due"):
        engine.record_review(
            learner_id="learner",
            node_id="LESSON:READING:R1",
            attempt_id="a1",
        )


def test_three_delayed_passes_confirm_retention(tmp_path: Path) -> None:
    database, graph, m7, engine = _fixture(tmp_path)
    engine.build_schedule(learner_id="learner", as_of="2026-07-02T00:00:00Z")
    for attempt_id, submitted_at in (
        ("a1", "2026-07-02T00:00:00Z"),
        ("a2", "2026-07-05T00:00:00Z"),
        ("a3", "2026-07-12T00:00:00Z"),
    ):
        _attempt(database, attempt_id, submitted_at, "AUTO_PASS")
        for node_id in ("LESSON:READING:R1", "REF:READING:C1"):
            result = engine.record_review(
                learner_id="learner",
                node_id=node_id,
                attempt_id=attempt_id,
            )
    assert result["retention_state"] == "RETAINED"
    assert result["node_retention_confirmed"] is True
    exported = engine.export_snapshot(
        learner_id="learner",
        output_root=tmp_path / "out",
        as_of="2026-07-12T00:00:00Z",
    )
    assert exported["retention_confirmed"] is True
    assert exported["retained_required_count"] == 2
    snapshot_path = Path(exported["snapshot_path"])
    schema = json.loads(Path("ulga/schemas/a1fs_v1_m8_retention_snapshot.schema.json").read_text())
    assert not list(Draft202012Validator(schema).iter_errors(json.loads(snapshot_path.read_text())))
    report = validate(database, graph, m7, snapshot_path)
    assert report["error_count"] == 0, report["errors"]


def test_failure_resets_spacing_and_marks_lapsed(tmp_path: Path) -> None:
    database, _, _, engine = _fixture(tmp_path)
    engine.build_schedule(learner_id="learner", as_of="2026-07-02T00:00:00Z")
    _attempt(database, "a1", "2026-07-02T00:00:00Z", "AUTO_PASS")
    engine.record_review(learner_id="learner", node_id="LESSON:READING:R1", attempt_id="a1")
    _attempt(database, "a2", "2026-07-05T00:00:00Z", "AUTO_FAIL")
    result = engine.record_review(
        learner_id="learner",
        node_id="LESSON:READING:R1",
        attempt_id="a2",
    )
    assert result["retention_state"] == "LAPSED"
    assert result["consecutive_delayed_passes"] == 0
    assert result["next_due_at"] == "2026-07-06T00:00:00Z"


def test_unresolved_or_active_attempt_cannot_satisfy_review(tmp_path: Path) -> None:
    database, _, _, engine = _fixture(tmp_path)
    engine.build_schedule(learner_id="learner", as_of="2026-07-02T00:00:00Z")
    _attempt(database, "pending", "2026-07-02T00:00:00Z", "PENDING_HUMAN_REVIEW")
    with pytest.raises(ReviewRetentionError, match="review_attempt_outcome_unresolved"):
        engine.record_review(
            learner_id="learner",
            node_id="LESSON:READING:R1",
            attempt_id="pending",
        )
    _attempt(database, "active", "2026-07-02T00:00:00Z", "AUTO_PASS", session_state="ACTIVE")
    with pytest.raises(ReviewRetentionError, match="review_attempt_session_not_completed"):
        engine.record_review(
            learner_id="learner",
            node_id="LESSON:READING:R1",
            attempt_id="active",
        )


def test_wrong_node_and_snapshot_tamper_fail_closed(tmp_path: Path) -> None:
    database, graph, m7, engine = _fixture(tmp_path)
    engine.build_schedule(learner_id="learner", as_of="2026-07-02T00:00:00Z")
    _attempt(database, "a1", "2026-07-02T00:00:00Z", "AUTO_PASS")
    with pytest.raises(ReviewRetentionError, match="review_node_not_in_graph"):
        engine.record_review(
            learner_id="learner",
            node_id="REF:WRITING:X",
            attempt_id="a1",
        )
    exported = engine.export_snapshot(
        learner_id="learner",
        output_root=tmp_path / "out",
        as_of="2026-07-02T00:00:00Z",
    )
    path = Path(exported["snapshot_path"])
    value = json.loads(path.read_text())
    value["retention_confirmed"] = True
    path.write_text(json.dumps(value))
    report = validate(database, graph, m7, path)
    assert report["error_count"] > 0
