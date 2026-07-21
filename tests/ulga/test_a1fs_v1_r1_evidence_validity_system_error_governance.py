from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ulga.builders import build_a1fs_v1_r1_evidence_validity_system_error_governance as r1
from ulga.builders.build_a1fs_v1_m3_learner_profile_session_state_storage import LearnerStateStore
from ulga.builders.build_a1fs_v1_m6_response_capture_scoring_m12_evidence import ResponseEvidenceStore
from ulga.builders.build_a1fs_v1_m7_mastery_error_remediation_reassessment import MasteryRemediationEngine
from ulga.builders.build_a1fs_v1_m8_review_scheduling_retention_spaced_practice import (
    ReviewRetentionEngine,
    ReviewRetentionError,
)
from ulga.builders.build_a1fs_v1_r1_evidence_validity_system_error_governance import (
    EvidenceGovernanceError,
    build_governed_overlay,
    initialize,
    set_validity,
)
from ulga.validators.validate_a1fs_v1_m6_response_capture_scoring_m12_evidence import validate as validate_m6
from ulga.validators.validate_a1fs_v1_r1_evidence_validity_system_error_governance import validate as validate_r1


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fixture(tmp_path: Path):
    payload = {
        "question": "How does Mia travel?",
        "answer": "bus",
        "m12_item_id": "R1_ITEM",
        "m12_session_bank_sha256": "a" * 64,
    }
    asset = {
        "asset_key": "R1:CHK",
        "asset_id": "A-R1-CHK",
        "lesson_id": "R1",
        "skill": "READING",
        "level": "A1",
        "role": "CHK",
        "payload": payload,
        "content_digest": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
    }
    catalog = {
        "lesson_id": "R1",
        "lesson_node_id": "LESSON:READING:R1",
        "skill": "READING",
        "level": "A1",
        "roles": ["CHK"],
        "requirement_node_ids": ["REF:READING:C1"],
        "asset_keys": ["R1:CHK"],
    }
    graph = {
        "task_id": "A1FS-V1-M1_A1A1PlusPrerequisiteGraphAndCoverage",
        "schema_version": "a1fs.v1.m1.prerequisite_graph_and_coverage.v1",
        "validation_status": "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE",
        "source_baseline_sha256": "b" * 64,
        "nodes": [
            {
                "node_id": "LESSON:READING:R1",
                "node_type": "LESSON",
                "skill": "READING",
                "level": "A1",
                "source_ref": "R1",
                "mastery_required_before_a2": True,
            },
            {
                "node_id": "REF:READING:C1",
                "node_type": "CAPABILITY",
                "skill": "READING",
                "level": "A1",
                "source_ref": "C1",
                "mastery_required_before_a2": True,
            },
            {
                "node_id": "GATE:A1FS:A2_LOCK",
                "node_type": "A2_LOCK",
                "skill": "FOUR_SKILL",
                "level": "A2",
                "source_ref": "A2_ENTRY",
                "mastery_required_before_a2": False,
            },
        ],
        "edges": [
            {"from_node_id": "REF:READING:C1", "to_node_id": "LESSON:READING:R1", "edge_type": "TAUGHT_BY"},
            {"from_node_id": "LESSON:READING:R1", "to_node_id": "GATE:A1FS:A2_LOCK", "edge_type": "UNLOCK_REQUIRES"},
            {"from_node_id": "REF:READING:C1", "to_node_id": "GATE:A1FS:A2_LOCK", "edge_type": "UNLOCK_REQUIRES"},
        ],
        "coverage": [
            {
                "node_id": "REF:READING:C1",
                "skill": "READING",
                "source_ref": "C1",
                "coverage_class": "MASTERY",
                "levels": ["A1"],
                "lesson_ids": ["R1"],
                "asset_body_ids": ["A-R1-CHK"],
                "roles": ["CHK"],
                "coverage_status": "COVERED",
            }
        ],
        "counts": {
            "node_count": 3,
            "edge_count": 3,
            "coverage_record_count": 1,
            "lesson_count": 1,
            "lesson_count_by_level": {"A1": 1, "A1+": 0, "A2": 0},
            "required_mastery_node_count": 2,
            "a2_handoff_lesson_count": 0,
            "uncovered_required_node_count": 0,
        },
        "a2_lock_contract": {
            "gate_node_id": "GATE:A1FS:A2_LOCK",
            "state": "LOCKED_BY_DESIGN",
            "required_mastery_node_ids": ["LESSON:READING:R1", "REF:READING:C1"],
            "a2_handoff_lesson_node_ids": [],
            "unlock_rule": "ALL_REQUIRED_MASTERY_NODES_MUST_BE_MASTERED",
            "runtime_unlock_implemented": False,
        },
        "claim_boundaries": {
            "source_packages_committed": False,
            "asset_body_content_modified": False,
            "learner_release_approved": False,
            "mastery_claimed": False,
            "a2_unlocked": False,
            "runtime_planner_implemented": False,
            "human_pilot_claimed": False,
            "listening_audio_complete": False,
        },
        "errors": [],
        "next_short_step": "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery",
    }
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    consumer = {
        "validation_status": "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY",
        "source_graph_sha256": _digest(graph_path.read_bytes()),
        "lesson_catalog": [catalog],
        "asset_records": [asset],
        "counts": {"lesson_count": 1, "asset_record_count": 1, "learning_lesson_count": 1},
    }
    consumer_path = tmp_path / "consumer.json"
    consumer_path.write_text(json.dumps(consumer), encoding="utf-8")
    bundle = {
        "validation_status": "PASS_A1FS_V1_M5_FOUR_SKILL_RENDERER_LEARNER_UI_READY",
        "source_consumer_sha256": _digest(consumer_path.read_bytes()),
        "lesson": {key: catalog[key] for key in ("lesson_id", "lesson_node_id", "skill", "level", "roles", "requirement_node_ids")},
        "assets": [{"asset_key": "R1:CHK", "role": "CHK"}],
    }
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    database = tmp_path / "source.sqlite3"
    state = LearnerStateStore(database)
    state.initialize(consumer_path)
    state.create_profile(
        learner_id="learner",
        display_label="Learner",
        at="2026-07-01T00:00:00Z",
    )
    state.start_session(
        learner_id="learner",
        lesson_id="R1",
        session_id="session-r1",
        at="2026-07-01T00:00:00Z",
    )
    evidence = ResponseEvidenceStore(database)
    evidence.initialize(consumer_path=consumer_path, lesson_bundle_path=bundle_path)
    attempts = []
    for index, response in enumerate(("train", "bus", "Bus."), start=1):
        attempts.append(
            evidence.capture_response(
                learner_id="learner",
                session_id="session-r1",
                asset_key="R1:CHK",
                response=response,
                expected_session_version=index,
                attempt_id=f"attempt-{index}",
                submitted_at=f"2026-07-01T00:0{index}:00Z",
            )
        )
    state.end_session(
        session_id="session-r1",
        outcome="COMPLETED",
        expected_session_version=4,
        at="2026-07-01T00:10:00Z",
    )
    return database, graph_path, attempts


def _govern(tmp_path: Path):
    database, graph, attempts = _fixture(tmp_path)
    baseline_engine = MasteryRemediationEngine(database_path=database, graph_path=graph)
    baseline_engine.initialize()
    baseline = baseline_engine.build_snapshot(
        learner_id="learner",
        output_root=tmp_path / "baseline",
        created_at="2026-07-01T00:20:00Z",
    )
    initialize(database, initialized_at="2026-07-01T00:21:00Z")
    set_validity(
        database,
        attempt_id=attempts[0]["attempt_id"],
        new_status="INVALIDATED_SYSTEM_ERROR",
        reason_code="UI_RESPONSE_SERIALIZATION_FAILURE",
        actor_id="validator-r1",
        detail={"component": "ordered_response_capture"},
        occurred_at="2026-07-01T00:22:00Z",
        event_id="R1_VALIDITY:attempt-1",
    )
    governed = tmp_path / "governed.sqlite3"
    report = tmp_path / "governance.safe.json"
    build_governed_overlay(
        database,
        governed,
        report,
        built_at="2026-07-01T00:23:00Z",
    )
    return database, governed, graph, attempts, Path(baseline["snapshot_path"]), report


def test_system_error_is_excluded_without_rewriting_raw_attempt(tmp_path: Path) -> None:
    source, governed, graph, attempts, baseline_path, report = _govern(tmp_path)
    baseline = json.loads(baseline_path.read_text())
    assert all(row["fail_count"] == 1 for row in baseline["node_states"])
    assert len(baseline["error_diagnoses"]) == 1

    with sqlite3.connect(source) as connection:
        raw = connection.execute(
            "SELECT response_json,outcome,score FROM response_attempts JOIN scoring_results USING(attempt_id) WHERE attempt_id=?",
            (attempts[0]["attempt_id"],),
        ).fetchone()
        assert json.loads(raw[0]) == "train"
        assert raw[1:] == ("AUTO_FAIL", 0.0)
        assert connection.execute("SELECT COUNT(*) FROM response_attempts").fetchone()[0] == 3

    r1_report = validate_r1(source, governed, report)
    assert r1_report["error_count"] == 0, r1_report["errors"]

    governed_engine = MasteryRemediationEngine(database_path=governed, graph_path=graph)
    governed_engine.initialize()
    result = governed_engine.build_snapshot(
        learner_id="learner",
        output_root=tmp_path / "governed-output",
        created_at="2026-07-01T00:30:00Z",
    )
    snapshot = json.loads(Path(result["snapshot_path"]).read_text())
    assert snapshot["mastered_required_count"] == 2
    assert all(row["fail_count"] == 0 and row["pass_count"] == 2 for row in snapshot["node_states"])
    assert snapshot["error_diagnoses"] == []
    assert snapshot["remediation_assignments"] == []
    assert snapshot["reassessment_queue"] == []

    assert validate_m6(source)["error_count"] == 0
    assert validate_m6(governed)["error_count"] == 0
    schema = json.loads(Path("ulga/schemas/a1fs_v1_r1_evidence_validity_governance_report.schema.json").read_text())
    assert not list(Draft202012Validator(schema).iter_errors(json.loads(report.read_text())))


def test_overlay_closes_every_sqlite_connection_before_atomic_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, _, _ = _fixture(tmp_path)
    governed = tmp_path / "governed.sqlite3"
    report = tmp_path / "governance.safe.json"
    temporary = governed.with_suffix(governed.suffix + ".tmp")
    tracked: list[TrackingConnection] = []
    replace_checked = False
    real_connect = sqlite3.connect
    real_replace = r1.os.replace

    class TrackingConnection(sqlite3.Connection):
        closed = False

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            tracked.append(self)

        def close(self) -> None:
            self.closed = True
            super().close()

    def tracking_connect(*args, **kwargs):
        return real_connect(*args, **kwargs, factory=TrackingConnection)

    def assert_closed_before_replace(source, destination) -> None:
        nonlocal replace_checked
        if Path(source) == temporary and Path(destination) == governed:
            assert len(tracked) == 4
            assert all(connection.closed for connection in tracked)
            replace_checked = True
        real_replace(source, destination)

    monkeypatch.setattr(r1.sqlite3, "connect", tracking_connect)
    monkeypatch.setattr(r1.os, "replace", assert_closed_before_replace)

    r1.build_governed_overlay(
        database,
        governed,
        report,
        built_at="2026-07-01T00:23:00Z",
    )

    assert governed.exists()
    assert not temporary.exists()
    assert report.exists()
    assert replace_checked
    validation = validate_r1(database, governed, report)
    assert validation["error_count"] == 0, validation["errors"]


def test_invalidation_is_append_only_and_terminal(tmp_path: Path) -> None:
    database, _, attempts = _fixture(tmp_path)
    initialize(database, initialized_at="2026-07-01T00:20:00Z")
    pending = set_validity(
        database,
        attempt_id=attempts[0]["attempt_id"],
        new_status="PENDING_VALIDITY_REVIEW",
        reason_code="SYSTEM_ERROR_SUSPECTED",
        actor_id="teacher",
        occurred_at="2026-07-01T00:21:00Z",
        event_id="R1_VALIDITY:pending",
    )
    assert pending["mastery_eligible"] is False
    invalidated = set_validity(
        database,
        attempt_id=attempts[0]["attempt_id"],
        new_status="INVALIDATED_CONTENT_ERROR",
        reason_code="AMBIGUOUS_ACCEPTED_ANSWER",
        actor_id="authority-reviewer",
        occurred_at="2026-07-01T00:22:00Z",
        event_id="R1_VALIDITY:invalidated",
    )
    assert invalidated["previous_status"] == "PENDING_VALIDITY_REVIEW"
    with pytest.raises(EvidenceGovernanceError, match="terminal_validity_status_cannot_change"):
        set_validity(
            database,
            attempt_id=attempts[0]["attempt_id"],
            new_status="PENDING_VALIDITY_REVIEW",
            reason_code="TRY_TO_REOPEN",
            actor_id="developer",
        )
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT previous_status,new_status,previous_hash,event_hash FROM evidence_validity_events ORDER BY event_seq"
        ).fetchall()
        assert [(row[0], row[1]) for row in rows] == [
            ("VALID", "PENDING_VALIDITY_REVIEW"),
            ("PENDING_VALIDITY_REVIEW", "INVALIDATED_CONTENT_ERROR"),
        ]
        assert rows[0][2] == "0" * 64
        assert rows[1][2] == rows[0][3]


def test_pending_validity_review_is_not_mastery_evidence(tmp_path: Path) -> None:
    database, graph, attempts = _fixture(tmp_path)
    initialize(database, initialized_at="2026-07-01T00:20:00Z")
    set_validity(
        database,
        attempt_id=attempts[2]["attempt_id"],
        new_status="PENDING_VALIDITY_REVIEW",
        reason_code="DUPLICATE_SUBMISSION_SUSPECTED",
        actor_id="validator-r1",
        occurred_at="2026-07-01T00:21:00Z",
    )
    governed = tmp_path / "governed.sqlite3"
    report = tmp_path / "report.json"
    build_governed_overlay(database, governed, report, built_at="2026-07-01T00:22:00Z")
    engine = MasteryRemediationEngine(database_path=governed, graph_path=graph)
    engine.initialize()
    result = engine.build_snapshot(
        learner_id="learner",
        output_root=tmp_path / "out",
        created_at="2026-07-01T00:30:00Z",
    )
    snapshot = json.loads(Path(result["snapshot_path"]).read_text())
    assert snapshot["mastered_required_count"] == 0
    assert all(row["resolved_attempt_count"] == 2 for row in snapshot["node_states"])
    assert all(row["pass_count"] == 1 and row["fail_count"] == 1 for row in snapshot["node_states"])


def test_m8_cannot_consume_invalidated_attempt(tmp_path: Path) -> None:
    source, governed, graph, attempts, _, report = _govern(tmp_path)
    assert validate_r1(source, governed, report)["error_count"] == 0
    m7 = MasteryRemediationEngine(database_path=governed, graph_path=graph)
    m7.initialize()
    result = m7.build_snapshot(
        learner_id="learner",
        output_root=tmp_path / "m7",
        created_at="2026-07-01T00:30:00Z",
    )
    m8 = ReviewRetentionEngine(
        database_path=governed,
        graph_path=graph,
        m7_snapshot_path=Path(result["snapshot_path"]),
    )
    m8.initialize()
    m8.build_schedule(learner_id="learner", as_of="2026-07-02T00:30:00Z")
    with pytest.raises(ReviewRetentionError, match="review_attempt_not_found"):
        m8.record_review(
            learner_id="learner",
            node_id="LESSON:READING:R1",
            attempt_id=attempts[0]["attempt_id"],
        )
