from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.build_a1fs_v1_m11_non_audio_human_pilot_evidence_review import (  # noqa: E402
    NonAudioHumanPilotEvidenceReview,
    PilotEvidenceError,
)
from ulga.validators.validate_a1fs_v1_m11_non_audio_human_pilot_evidence_review import (  # noqa: E402
    validate,
)


def digest(value) -> str:
    if isinstance(value, bytes):
        raw = value
    else:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def attestations() -> dict[str, bool]:
    return {
        "real_learner_participated": True,
        "facilitator_observed": True,
        "learner_ui_used": True,
        "raw_response_not_exported": True,
        "audio_deferred": True,
        "speaking_recording_deferred": True,
        "privacy_review_completed": True,
    }


def fixture(tmp_path: Path):
    graph = {
        "validation_status": "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE",
        "a2_lock_contract": {"state": "LOCKED_BY_DESIGN"},
    }
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    graph_sha = digest(graph_path.read_bytes())
    m7 = {
        "validation_status": "PASS_A1FS_V1_M7_MASTERY_REMEDIATION_REASSESSMENT",
        "learner_id": "learner-1",
        "source_graph_sha256": graph_sha,
        "mastered_required_count": 0,
        "a2_lock_state": "LOCKED",
    }
    m7_path = tmp_path / "m7.json"
    m7_path.write_text(json.dumps(m7), encoding="utf-8")
    m8 = {
        "validation_status": "PASS_A1FS_V1_M8_REVIEW_SCHEDULING_RETENTION_SPACED_PRACTICE",
        "learner_id": "learner-1",
        "source_graph_sha256": graph_sha,
        "source_m7_snapshot_digest": digest(m7),
        "retention_confirmed": False,
    }
    m8_path = tmp_path / "m8.json"
    m8_path.write_text(json.dumps(m8), encoding="utf-8")
    m9 = {
        "validation_status": "PASS_A1FS_V1_M9_TEACHER_DASHBOARD_PROGRESS_REPORTING_EXPORT",
        "source_bindings": {
            "graph_sha256": graph_sha,
            "m7_snapshot_digest": digest(m7),
            "m8_snapshot_digest": digest(m8),
        },
        "learner": {"learner_id": "learner-1", "profile_state": "ACTIVE"},
        "four_skill_progress": [
            {"skill": "LISTENING", "completed_session_count": 0, "attempt_count": 0},
            {"skill": "SPEAKING", "completed_session_count": 0, "attempt_count": 0},
            {"skill": "READING", "completed_session_count": 1, "attempt_count": 1},
            {"skill": "WRITING", "completed_session_count": 1, "attempt_count": 1},
        ],
    }
    m9_path = tmp_path / "m9.json"
    m9_path.write_text(json.dumps(m9), encoding="utf-8")
    database = tmp_path / "state.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE m7_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE m8_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE m9_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE learner_profiles(learner_id TEXT PRIMARY KEY,profile_state TEXT NOT NULL);
            CREATE TABLE learning_sessions(
              session_id TEXT PRIMARY KEY,learner_id TEXT,lesson_id TEXT,skill TEXT,level TEXT,
              session_state TEXT,started_at TEXT,ended_at TEXT
            );
            CREATE TABLE response_contracts(
              asset_key TEXT PRIMARY KEY,skill TEXT,role TEXT
            );
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY,learner_id TEXT,session_id TEXT,asset_key TEXT,submitted_at TEXT
            );
            CREATE TABLE scoring_results(
              attempt_id TEXT PRIMARY KEY,scoring_mode TEXT,outcome TEXT,human_review_required INTEGER
            );
            CREATE TABLE human_review_queue(
              attempt_id TEXT PRIMARY KEY,decision TEXT
            );
            CREATE TABLE mastery_snapshots(
              snapshot_id TEXT PRIMARY KEY,learner_id TEXT,snapshot_digest TEXT,created_at TEXT
            );
            CREATE TABLE retention_snapshots(
              snapshot_id TEXT PRIMARY KEY,learner_id TEXT,snapshot_digest TEXT,created_at TEXT
            );
            CREATE TABLE dashboard_exports(
              export_id TEXT PRIMARY KEY,learner_id TEXT,exported_at TEXT,report_digest TEXT
            );
            """
        )
        connection.executemany(
            "INSERT INTO metadata VALUES(?,?)",
            [("m6_validation_status", "PASS_A1FS_V1_M6_RESPONSE_CAPTURE_SCORING_M12_EVIDENCE_READY")],
        )
        connection.execute(
            "INSERT INTO m7_metadata VALUES('validation_status','PASS_A1FS_V1_M7_MASTERY_REMEDIATION_REASSESSMENT')"
        )
        connection.execute(
            "INSERT INTO m8_metadata VALUES('validation_status','PASS_A1FS_V1_M8_REVIEW_SCHEDULING_RETENTION_SPACED_PRACTICE')"
        )
        connection.execute(
            "INSERT INTO m9_metadata VALUES('validation_status','PASS_A1FS_V1_M9_TEACHER_DASHBOARD_PROGRESS_REPORTING_EXPORT')"
        )
        connection.execute("INSERT INTO learner_profiles VALUES('learner-1','ACTIVE')")
        connection.executemany(
            "INSERT INTO learning_sessions VALUES(?,?,?,?,?,?,?,?)",
            [
                ("session-r", "learner-1", "R1", "READING", "A1", "COMPLETED", "2026-07-17T00:02:00Z", "2026-07-17T00:10:00Z"),
                ("session-w", "learner-1", "W1", "WRITING", "A1", "COMPLETED", "2026-07-17T00:12:00Z", "2026-07-17T00:25:00Z"),
            ],
        )
        connection.executemany(
            "INSERT INTO response_contracts VALUES(?,?,?)",
            [("R1:CHK", "READING", "CHK"), ("W1:PRD", "WRITING", "PRD")],
        )
        connection.executemany(
            "INSERT INTO response_attempts VALUES(?,?,?,?,?)",
            [
                ("attempt-r", "learner-1", "session-r", "R1:CHK", "2026-07-17T00:06:00Z"),
                ("attempt-w", "learner-1", "session-w", "W1:PRD", "2026-07-17T00:20:00Z"),
            ],
        )
        connection.executemany(
            "INSERT INTO scoring_results VALUES(?,?,?,?)",
            [
                ("attempt-r", "NORMALIZED_TEXT", "AUTO_PASS", 0),
                ("attempt-w", "FEATURE_RUBRIC", "HUMAN_APPROVE", 1),
            ],
        )
        connection.executemany(
            "INSERT INTO human_review_queue VALUES(?,?)",
            [("attempt-r", "PENDING"), ("attempt-w", "APPROVE")],
        )
        connection.execute(
            "INSERT INTO mastery_snapshots VALUES('m7-row','learner-1',?,'2026-07-17T00:31:00Z')",
            (digest(m7),),
        )
        connection.execute(
            "INSERT INTO retention_snapshots VALUES('m8-row','learner-1',?,'2026-07-17T00:32:00Z')",
            (digest(m8),),
        )
        connection.execute(
            "INSERT INTO dashboard_exports VALUES('m9-row','learner-1','2026-07-17T00:33:00Z',?)",
            (digest(m9),),
        )
    engine = NonAudioHumanPilotEvidenceReview(
        database_path=database,
        graph_path=graph_path,
        m7_snapshot_path=m7_path,
        m8_snapshot_path=m8_path,
        m9_report_path=m9_path,
    )
    engine.initialize()
    return database, graph_path, m7_path, m8_path, m9_path, engine


def register(engine, output_root: Path, **overrides):
    values = {
        "learner_id": "learner-1",
        "facilitator_id": "facilitator-1",
        "session_ids": ["session-r", "session-w"],
        "started_at": "2026-07-17T00:00:00Z",
        "ended_at": "2026-07-17T00:30:00Z",
        "recorded_at": "2026-07-17T00:35:00Z",
        "attestations": attestations(),
        "output_root": output_root,
    }
    values.update(overrides)
    return engine.register_pilot(**values)


def test_valid_real_pilot_evidence_package_and_independent_validation(tmp_path: Path) -> None:
    database, graph, m7, m8, m9, engine = fixture(tmp_path)
    result = register(engine, tmp_path / "out")
    package_path = Path(result["package_path"])
    package = json.loads(package_path.read_text())
    assert package["validation_status"] == "PASS_A1FS_V1_M11_NON_AUDIO_HUMAN_PILOT"
    assert package["claim_boundaries"]["four_skill_human_pilot_claimed"] is False
    assert package["workflow_evidence"]["audio_evidence_used"] is False
    schema = json.loads((ROOT / "ulga/schemas/a1fs_v1_m11_non_audio_human_pilot.schema.json").read_text())
    assert not list(Draft202012Validator(schema).iter_errors(package))
    report = validate(database, graph, m7, m8, m9, package_path)
    assert report["error_count"] == 0, report["errors"]


def test_unresolved_attempt_is_rejected(tmp_path: Path) -> None:
    database, _, _, _, _, engine = fixture(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE scoring_results SET outcome='PENDING_HUMAN_REVIEW' WHERE attempt_id='attempt-w'")
        connection.execute("UPDATE human_review_queue SET decision='PENDING' WHERE attempt_id='attempt-w'")
    with pytest.raises(PilotEvidenceError, match="unresolved_pilot_attempt_forbidden"):
        register(engine, tmp_path / "out")


def test_listening_or_speaking_session_is_rejected(tmp_path: Path) -> None:
    database, _, _, _, _, engine = fixture(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE learning_sessions SET skill='LISTENING' WHERE session_id='session-r'")
    with pytest.raises(PilotEvidenceError, match="audio_or_speaking_session_forbidden"):
        register(engine, tmp_path / "out")


def test_stale_post_pilot_dashboard_is_rejected(tmp_path: Path) -> None:
    database, _, _, _, _, engine = fixture(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE dashboard_exports SET exported_at='2026-07-16T23:59:00Z'")
    with pytest.raises(PilotEvidenceError, match="m9_report_not_refreshed_after_pilot"):
        register(engine, tmp_path / "out")


def test_incomplete_operator_attestation_is_rejected(tmp_path: Path) -> None:
    _, _, _, _, _, engine = fixture(tmp_path)
    values = attestations()
    values["real_learner_participated"] = False
    with pytest.raises(PilotEvidenceError, match="operator_attestations_incomplete"):
        register(engine, tmp_path / "out", attestations=values)


def test_package_tampering_is_detected(tmp_path: Path) -> None:
    database, graph, m7, m8, m9, engine = fixture(tmp_path)
    result = register(engine, tmp_path / "out")
    package_path = Path(result["package_path"])
    package = json.loads(package_path.read_text())
    package["outcome_summary"]["pass_count"] = 99
    package_path.write_text(json.dumps(package), encoding="utf-8")
    report = validate(database, graph, m7, m8, m9, package_path)
    assert report["error_count"] > 0
    assert "pilot_package_not_persisted" in report["errors"]
    assert "outcome_summary_mismatch" in report["errors"]
