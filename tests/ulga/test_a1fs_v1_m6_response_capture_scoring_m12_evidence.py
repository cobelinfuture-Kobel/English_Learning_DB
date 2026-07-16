from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ulga.builders.build_a1fs_v1_m6_response_capture_scoring_m12_evidence import ResponseEvidenceError, ResponseEvidenceStore
from ulga.validators.validate_a1fs_v1_m6_response_capture_scoring_m12_evidence import validate


def _digest(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()


def _fixture(tmp_path: Path):
    legacy = "a" * 64
    assets = [
        ("R1", "READING", "A1", "CHK", {"question": "How does Mia travel?", "answer": "bus", "m12_item_id": "M08_R1", "m12_session_bank_sha256": legacy}),
        ("R2", "READING", "A1", "PRD", {"prompt": "Put the words in order.", "accepted_sequence": ["Mia", "travels", "by", "bus"], "m12_item_id": "M08_R2", "m12_session_bank_sha256": legacy}),
        ("S1", "SPEAKING", "A1", "PRD", {"prompt": "Say one sentence about school.", "scoring_rubric": {"grammar": "present simple"}, "m12_item_id": "M08_S1", "m12_session_bank_sha256": legacy}),
        ("L1", "LISTENING", "A1", "AUD", {"question": "What time?", "answer": "eight"}),
        ("L2", "LISTENING", "A1", "CHK", {"question": "Choose the time.", "accepted_texts": ["eight"]}),
        ("A2", "READING", "A2", "CHK", {"question": "locked", "answer": "locked"}),
    ]
    records, catalog = [], []
    for lesson, skill, level, role, payload in assets:
        key = f"{lesson}:{role}"; digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        records.append({"asset_key": key, "asset_id": key, "lesson_id": lesson, "skill": skill, "level": level, "role": role, "payload": payload, "content_digest": digest})
        catalog.append({"lesson_id": lesson, "lesson_node_id": f"LESSON:{lesson}", "skill": skill, "level": level, "roles": [role], "requirement_node_ids": [], "asset_keys": [key]})
    consumer = {"validation_status": "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY", "lesson_catalog": catalog, "asset_records": records,
                "counts": {"lesson_count": len(catalog), "asset_record_count": len(records)}}
    consumer_path = tmp_path / "consumer.json"; consumer_path.write_text(json.dumps(consumer), encoding="utf-8")
    db = tmp_path / "state.sqlite"
    with sqlite3.connect(db) as connection:
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
        metadata={"validation_status":"PASS_A1FS_V1_M3_LEARNER_PROFILE_SESSION_STATE_STORAGE_READY","consumer_sha256":_digest(consumer_path.read_bytes()),"mastery_write_enabled":"false"}
        connection.executemany("INSERT INTO metadata VALUES(?,?)",metadata.items())
        for row in catalog:
            connection.execute("INSERT INTO lesson_catalog VALUES(?,?,?,?,?,?,?)",(row["lesson_id"],row["lesson_node_id"],row["skill"],row["level"],json.dumps(row["roles"]),json.dumps(row["requirement_node_ids"]),int(row["level"] in {"A1","A1+"})))
        for row in records:
            connection.execute("INSERT INTO lesson_assets VALUES(?,?,?,?,?)",(row["asset_key"],row["asset_id"],row["lesson_id"],row["role"],row["content_digest"]))
    state = db
    def bundle(lesson: str) -> Path:
        cat = next(row for row in catalog if row["lesson_id"] == lesson); asset = next(row for row in records if row["lesson_id"] == lesson)
        value = {"validation_status": "PASS_A1FS_V1_M5_FOUR_SKILL_RENDERER_LEARNER_UI_READY", "source_consumer_sha256": _digest(consumer_path.read_bytes()),
                 "lesson": {k: cat[k] for k in ("lesson_id", "lesson_node_id", "skill", "level", "roles", "requirement_node_ids")},
                 "assets": [{"asset_key": asset["asset_key"], "role": asset["role"]}]}
        path = tmp_path / f"{lesson}.bundle.json"; path.write_text(json.dumps(value), encoding="utf-8"); return path
    return consumer_path, db, state, bundle


def _active(state: Path, learner: str, lesson: str, session: str):
    with sqlite3.connect(state) as connection:
        row=connection.execute("SELECT skill,level FROM lesson_catalog WHERE lesson_id=?",(lesson,)).fetchone()
        connection.execute("INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)",(learner,learner,"zh-TW","Asia/Taipei","ACTIVE",1,"2026-07-16T00:00:00Z","2026-07-16T00:00:00Z"))
        connection.execute("INSERT INTO learning_sessions VALUES(?,?,?,?,?,?,?,?,?)",(session,learner,lesson,row[0],row[1],"ACTIVE",1,"2026-07-16T00:00:00Z",None))
    return {"session_id":session,"session_version":1}


def _end(state: Path, session: str, expected_version: int):
    with sqlite3.connect(state) as connection:
        version=connection.execute("SELECT session_version FROM learning_sessions WHERE session_id=?",(session,)).fetchone()[0]
        assert version==expected_version
        connection.execute("UPDATE learning_sessions SET session_state='COMPLETED',session_version=session_version+1,ended_at='2026-07-16T00:10:00Z' WHERE session_id=?",(session,))


def test_deterministic_capture_sequence_export_and_validation(tmp_path: Path) -> None:
    consumer, db, state, bundle = _fixture(tmp_path); store = ResponseEvidenceStore(db)
    store.initialize(consumer_path=consumer, lesson_bundle_path=bundle("R1")); store.initialize(consumer_path=consumer, lesson_bundle_path=bundle("R2"))
    session = _active(state, "learner-r", "R1", "session-r1")
    result = store.capture_response(learner_id="learner-r", session_id="session-r1", asset_key="R1:CHK", response="Bus.", expected_session_version=session["session_version"])
    assert result["outcome"] == "AUTO_PASS" and result["score"] == 1.0
    _end(state, "session-r1", session["session_version"] + 1)
    with sqlite3.connect(state) as connection:
        connection.execute("INSERT INTO learning_sessions VALUES(?,?,?,?,?,?,?,?,?)",("session-r2","learner-r","R2","READING","A1","ACTIVE",1,"2026-07-16T00:20:00Z",None))
    sequence = store.capture_response(learner_id="learner-r", session_id="session-r2", asset_key="R2:PRD", response=["Mia", "travels", "by", "bus"], expected_session_version=1)
    assert sequence["outcome"] == "AUTO_PASS"
    exported = store.export_evidence(session_id="session-r2", output_root=tmp_path / "evidence")
    assert exported["legacy_allowlist_import_ready"] is True
    schema = json.loads(Path("ulga/schemas/a1fs_v1_m6_evidence_registry.schema.json").read_text())
    registry = json.loads(Path(exported["registry_path"]).read_text())
    assert not list(Draft202012Validator(schema).iter_errors(registry))
    report = validate(db, Path(exported["registry_path"]), Path(exported["m12_registry_path"]))
    assert report["error_count"] == 0, report["errors"]


def test_productive_response_requires_human_review(tmp_path: Path) -> None:
    consumer, db, state, bundle = _fixture(tmp_path); store = ResponseEvidenceStore(db)
    store.initialize(consumer_path=consumer, lesson_bundle_path=bundle("S1")); session = _active(state, "learner-s", "S1", "session-s")
    captured = store.capture_response(learner_id="learner-s", session_id="session-s", asset_key="S1:PRD", response="I like my school.", expected_session_version=session["session_version"])
    assert captured["outcome"] == "PENDING_HUMAN_REVIEW" and captured["score"] is None
    reviewed = store.review_response(attempt_id=captured["attempt_id"], decision="APPROVE", reviewer_id="teacher-01",
                                     criteria={"grammar_target_match": True, "meaning_matches_context": True, "complete_response": True})
    assert reviewed["outcome"] == "HUMAN_APPROVE" and reviewed["score"] == 1.0


def test_deterministic_review_override_is_forbidden(tmp_path: Path) -> None:
    consumer, db, state, bundle = _fixture(tmp_path); store = ResponseEvidenceStore(db)
    store.initialize(consumer_path=consumer, lesson_bundle_path=bundle("R1")); session = _active(state, "learner", "R1", "session")
    captured = store.capture_response(learner_id="learner", session_id="session", asset_key="R1:CHK", response="train", expected_session_version=session["session_version"])
    with pytest.raises(ResponseEvidenceError, match="deterministic_item_review_override_forbidden"):
        store.review_response(attempt_id=captured["attempt_id"], decision="APPROVE", reviewer_id="teacher",
                              criteria={"grammar_target_match": True, "meaning_matches_context": True, "complete_response": True})


def test_unfinished_audio_and_a2_are_fail_closed(tmp_path: Path) -> None:
    consumer, db, state, bundle = _fixture(tmp_path); store = ResponseEvidenceStore(db)
    init = store.initialize(consumer_path=consumer, lesson_bundle_path=bundle("L1")); assert init["capture_contract_count"] == 0
    session = _active(state, "listener", "L1", "listen-session")
    with pytest.raises(ResponseEvidenceError, match="response_capture_not_enabled_for_asset"):
        store.capture_response(learner_id="listener", session_id="listen-session", asset_key="L1:AUD", response="eight", expected_session_version=session["session_version"])
    with pytest.raises(ResponseEvidenceError, match="A2_RESPONSE_CAPTURE_LOCKED"):
        store.initialize(consumer_path=consumer, lesson_bundle_path=bundle("A2"))


def test_wrong_asset_and_session_version_rollback(tmp_path: Path) -> None:
    consumer, db, state, bundle = _fixture(tmp_path); store = ResponseEvidenceStore(db)
    store.initialize(consumer_path=consumer, lesson_bundle_path=bundle("R1")); store.initialize(consumer_path=consumer, lesson_bundle_path=bundle("L2"))
    session = _active(state, "learner", "R1", "session")
    with pytest.raises(ResponseEvidenceError, match="asset_not_in_session_lesson"):
        store.capture_response(learner_id="learner", session_id="session", asset_key="L2:CHK", response="eight", expected_session_version=session["session_version"])
    with pytest.raises(ResponseEvidenceError, match="session_version_conflict"):
        store.capture_response(learner_id="learner", session_id="session", asset_key="R1:CHK", response="bus", expected_session_version=99)


def test_validator_detects_score_tampering(tmp_path: Path) -> None:
    consumer, db, state, bundle = _fixture(tmp_path); store = ResponseEvidenceStore(db)
    store.initialize(consumer_path=consumer, lesson_bundle_path=bundle("R1")); session = _active(state, "learner", "R1", "session")
    captured = store.capture_response(learner_id="learner", session_id="session", asset_key="R1:CHK", response="bus", expected_session_version=session["session_version"])
    with sqlite3.connect(db) as connection: connection.execute("UPDATE scoring_results SET outcome='AUTO_FAIL',score=0 WHERE attempt_id=?", (captured["attempt_id"],))
    report = validate(db)
    assert any(error.startswith("score_mismatch:") for error in report["errors"])
