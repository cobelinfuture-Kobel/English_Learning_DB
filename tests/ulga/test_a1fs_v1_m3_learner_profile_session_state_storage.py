from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.validators import validate_a1fs_v1_m3_learner_profile_session_state_storage as validator


def _consumer(path: Path, suffix: str = "") -> Path:
    lessons = [
        {"lesson_id": "L-A1", "lesson_node_id": "LESSON:LISTENING:L-A1", "skill": "LISTENING", "level": "A1", "asset_keys": ["A-A1"], "roles": ["EVD"], "requirement_node_ids": ["REF:LISTENING:R1"], "release_scope": "PRIVATE_INTERNAL_D0"},
        {"lesson_id": "S-A1P", "lesson_node_id": "LESSON:SPEAKING:S-A1P", "skill": "SPEAKING", "level": "A1+", "asset_keys": ["A-A1P"], "roles": ["PRD"], "requirement_node_ids": ["REF:SPEAKING:R2"], "release_scope": "PRIVATE_INTERNAL_D0"},
        {"lesson_id": "R-A2", "lesson_node_id": "LESSON:READING:R-A2", "skill": "READING", "level": "A2", "asset_keys": ["A-A2"], "roles": ["TXT"], "requirement_node_ids": ["REF:READING:R3"], "release_scope": "PRIVATE_INTERNAL_D0"},
    ]
    assets = []
    for lesson in lessons:
        key = lesson["asset_keys"][0]
        assets.append({"asset_key": key, "asset_id": key, "lesson_id": lesson["lesson_id"], "skill": lesson["skill"], "level": lesson["level"], "role": lesson["roles"][0], "payload": {"text": key + suffix}, "content_digest": (key[-1] * 64), "release_scope": "PRIVATE_INTERNAL_D0"})
    value = {"validation_status": m3.CONSUMER_STATUS, "asset_records": assets, "lesson_catalog": lessons, "counts": {"asset_record_count": 3, "lesson_count": 3, "learning_lesson_count": 2, "a2_handoff_lesson_count": 1}}
    path.write_text(json.dumps(value), encoding="utf-8"); return path


def _store(tmp_path: Path) -> tuple[m3.LearnerStateStore, Path, Path]:
    consumer = _consumer(tmp_path / "consumer.json"); database = tmp_path / "state.sqlite3"
    store = m3.LearnerStateStore(database); store.initialize(consumer)
    return store, database, consumer


def test_initializes_private_catalog_bound_state_store(tmp_path: Path) -> None:
    store, database, consumer = _store(tmp_path)
    report = validator.validate(database, consumer)
    assert report["error_count"] == 0, report["errors"]
    assert report["lesson_count"] == 3 and report["asset_count"] == 3
    if os.name != "nt": assert database.stat().st_mode & 0o077 == 0


def test_profile_session_exposure_and_end_round_trip(tmp_path: Path) -> None:
    store, database, consumer = _store(tmp_path)
    store.create_profile(learner_id="learner-1", display_label="Learner", at="2026-01-01T00:00:00Z")
    session = store.start_session(learner_id="learner-1", lesson_id="L-A1", session_id="session-1", at="2026-01-01T00:01:00Z")
    assert session["session_version"] == 1
    session = store.record_exposure(session_id="session-1", asset_key="A-A1", expected_session_version=1, at="2026-01-01T00:02:00Z")
    assert session["session_version"] == 2
    session = store.end_session(session_id="session-1", outcome="COMPLETED", expected_session_version=2, at="2026-01-01T00:03:00Z")
    assert session["session_state"] == "COMPLETED"
    snapshot = store.profile_snapshot("learner-1")
    assert snapshot["progress"][0]["exposure_count"] == 1
    assert snapshot["progress"][0]["progress_state"] == "PAUSED"
    assert snapshot["claim_boundaries"] == {"scoring_recorded": False, "mastery_recorded": False, "a2_unlocked": False}
    assert validator.validate(database, consumer)["error_count"] == 0


def test_a2_session_is_locked_fail_closed(tmp_path: Path) -> None:
    store, _, _ = _store(tmp_path); store.create_profile(learner_id="learner-1", display_label="Learner")
    with pytest.raises(m3.StateStoreError, match="A2_SESSION_LOCKED"):
        store.start_session(learner_id="learner-1", lesson_id="R-A2", session_id="session-a2")


def test_only_one_active_session_per_learner(tmp_path: Path) -> None:
    store, _, _ = _store(tmp_path); store.create_profile(learner_id="learner-1", display_label="Learner")
    store.start_session(learner_id="learner-1", lesson_id="L-A1", session_id="session-1")
    with pytest.raises(m3.StateStoreError, match="active_session_exists"):
        store.start_session(learner_id="learner-1", lesson_id="S-A1P", session_id="session-2")


def test_optimistic_session_version_conflict_rolls_back(tmp_path: Path) -> None:
    store, database, _ = _store(tmp_path); store.create_profile(learner_id="learner-1", display_label="Learner")
    store.start_session(learner_id="learner-1", lesson_id="L-A1", session_id="session-1")
    with pytest.raises(m3.StateStoreError, match="session_version_conflict"):
        store.record_exposure(session_id="session-1", asset_key="A-A1", expected_session_version=9)
    assert store.session_snapshot("session-1")["session_version"] == 1
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM state_events WHERE event_type='ASSET_EXPOSED'").fetchone()[0] == 0


def test_cross_lesson_asset_exposure_is_rejected(tmp_path: Path) -> None:
    store, _, _ = _store(tmp_path); store.create_profile(learner_id="learner-1", display_label="Learner")
    store.start_session(learner_id="learner-1", lesson_id="L-A1", session_id="session-1")
    with pytest.raises(m3.StateStoreError, match="asset_not_in_session_lesson"):
        store.record_exposure(session_id="session-1", asset_key="A-A1P", expected_session_version=1)


def test_profile_deactivation_requires_no_active_session(tmp_path: Path) -> None:
    store, _, _ = _store(tmp_path); store.create_profile(learner_id="learner-1", display_label="Learner")
    store.start_session(learner_id="learner-1", lesson_id="L-A1", session_id="session-1")
    with pytest.raises(m3.StateStoreError, match="active_session_exists"):
        store.deactivate_profile(learner_id="learner-1", expected_profile_version=1)
    store.end_session(session_id="session-1", outcome="ABANDONED", expected_session_version=1)
    snapshot = store.deactivate_profile(learner_id="learner-1", expected_profile_version=1)
    assert snapshot["profile"]["profile_state"] == "INACTIVE"


def test_database_consumer_drift_is_rejected(tmp_path: Path) -> None:
    store, _, consumer = _store(tmp_path); _consumer(consumer, suffix="drift")
    with pytest.raises(m3.StateStoreError, match="database_consumer_binding_mismatch"):
        store.initialize(consumer)


def test_validator_detects_event_chain_tampering(tmp_path: Path) -> None:
    store, database, consumer = _store(tmp_path); store.create_profile(learner_id="learner-1", display_label="Learner")
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE state_events SET payload_json='{}' WHERE event_seq=1"); connection.commit()
    report = validator.validate(database, consumer)
    assert any(error.startswith("event_chain_invalid:") for error in report["errors"])


def test_non_utc_timestamp_is_rejected(tmp_path: Path) -> None:
    store, _, _ = _store(tmp_path)
    with pytest.raises(m3.StateStoreError, match="timestamp_must_be_utc"):
        store.create_profile(learner_id="learner-1", display_label="Learner", at="2026-01-01T08:00:00+08:00")
