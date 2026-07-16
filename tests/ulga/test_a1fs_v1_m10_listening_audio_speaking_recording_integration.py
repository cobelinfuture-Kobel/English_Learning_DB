from __future__ import annotations

import hashlib
import json
import sqlite3
import wave
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ulga.builders.build_a1fs_v1_m10_listening_audio_speaking_recording_integration import (
    MediaIntegrationError,
    PrivateMediaRegistry,
)
from ulga.validators.validate_a1fs_v1_m10_listening_audio_speaking_recording_integration import validate


def make_wav(path: Path, milliseconds: int = 500, sample_rate: int = 16000) -> None:
    frame_count = int(sample_rate * milliseconds / 1000)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\0\0" * frame_count)


def fixture(tmp_path: Path):
    consumer = {"validation_status": "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"}
    consumer_path = tmp_path / "consumer.json"
    consumer_path.write_text(json.dumps(consumer))
    consumer_sha = hashlib.sha256(consumer_path.read_bytes()).hexdigest()
    database = tmp_path / "state.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
            CREATE TABLE m9_metadata(key TEXT PRIMARY KEY,value TEXT);
            CREATE TABLE lesson_catalog(lesson_id TEXT PRIMARY KEY,skill TEXT,level TEXT);
            CREATE TABLE lesson_assets(asset_key TEXT PRIMARY KEY,asset_id TEXT,lesson_id TEXT,role TEXT,content_digest TEXT);
            CREATE TABLE learner_profiles(learner_id TEXT PRIMARY KEY);
            CREATE TABLE response_attempts(attempt_id TEXT PRIMARY KEY,learner_id TEXT,lesson_id TEXT,asset_key TEXT);
            CREATE TABLE scoring_results(attempt_id TEXT PRIMARY KEY,scoring_mode TEXT,outcome TEXT);
            """
        )
        connection.execute("INSERT INTO metadata VALUES('consumer_sha256',?)", (consumer_sha,))
        connection.execute(
            "INSERT INTO m9_metadata VALUES('validation_status','PASS_A1FS_V1_M9_TEACHER_DASHBOARD_PROGRESS_REPORTING_EXPORT')"
        )
        for row in (
            ("L1", "LISTENING", "A1"),
            ("S1", "SPEAKING", "A1"),
            ("R1", "READING", "A1"),
            ("A2", "LISTENING", "A2"),
        ):
            connection.execute("INSERT INTO lesson_catalog VALUES(?,?,?)", row)
        for row in (
            ("L1:AUD", "la", "L1", "AUD", "d"),
            ("S1:PRD", "sp", "S1", "PRD", "d"),
            ("R1:CHK", "r", "R1", "CHK", "d"),
            ("A2:AUD", "a2", "A2", "AUD", "d"),
        ):
            connection.execute("INSERT INTO lesson_assets VALUES(?,?,?,?,?)", row)
        connection.execute("INSERT INTO learner_profiles VALUES('learner')")
        connection.execute(
            "INSERT INTO response_attempts VALUES('attempt','learner','S1','S1:PRD')"
        )
        connection.execute(
            "INSERT INTO scoring_results VALUES('attempt','FEATURE_RUBRIC','PENDING_HUMAN_REVIEW')"
        )
    registry = PrivateMediaRegistry(
        database_path=database,
        consumer_path=consumer_path,
        media_root=tmp_path / "media",
    )
    registry.initialize()
    return database, consumer_path, registry


def test_register_listening_and_manifest_validation(tmp_path: Path) -> None:
    database, _, registry = fixture(tmp_path)
    path = tmp_path / "listening.wav"
    make_wav(path)
    result = registry.register_listening(asset_key="L1:AUD", wav_path=path)
    assert result["duration_ms"] == 500
    exported = registry.export(output_root=tmp_path / "out")
    manifest = json.loads(Path(exported["manifest_path"]).read_text())
    assert manifest["listening_audio"] == {
        "required_aud_asset_count": 1,
        "registered_aud_asset_count": 1,
        "complete": True,
    }
    schema = json.loads(Path("ulga/schemas/a1fs_v1_m10_private_media_manifest.schema.json").read_text())
    assert not list(Draft202012Validator(schema).iter_errors(manifest))
    report = validate(database, Path(exported["manifest_path"]))
    assert not report["errors"]


def test_wrong_role_and_a2_are_rejected(tmp_path: Path) -> None:
    _, _, registry = fixture(tmp_path)
    path = tmp_path / "audio.wav"
    make_wav(path)
    with pytest.raises(MediaIntegrationError, match="listening_audio_requires_aud_asset"):
        registry.register_listening(asset_key="R1:CHK", wav_path=path)
    with pytest.raises(MediaIntegrationError, match="A2_MEDIA_LOCKED"):
        registry.register_listening(asset_key="A2:AUD", wav_path=path)


def test_recording_requires_explicit_consent(tmp_path: Path) -> None:
    _, _, registry = fixture(tmp_path)
    path = tmp_path / "speaking.wav"
    make_wav(path)
    with pytest.raises(MediaIntegrationError, match="speaking_recording_consent_required"):
        registry.register_recording(
            learner_id="learner",
            attempt_id="attempt",
            wav_path=path,
            consent_granted=False,
        )


def test_recording_stays_human_review_only(tmp_path: Path) -> None:
    database, _, registry = fixture(tmp_path)
    path = tmp_path / "speaking.wav"
    make_wav(path)
    result = registry.register_recording(
        learner_id="learner",
        attempt_id="attempt",
        wav_path=path,
        consent_granted=True,
    )
    assert result["human_review_required"] is True
    assert result["automatic_score_written"] is False
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT outcome FROM scoring_results WHERE attempt_id='attempt'"
        ).fetchone()[0] == "PENDING_HUMAN_REVIEW"


def test_invalid_or_too_short_wav_fails_closed(tmp_path: Path) -> None:
    _, _, registry = fixture(tmp_path)
    invalid = tmp_path / "invalid.wav"
    invalid.write_text("not wav")
    with pytest.raises(MediaIntegrationError, match="wav_invalid"):
        registry.register_listening(asset_key="L1:AUD", wav_path=invalid)
    short = tmp_path / "short.wav"
    make_wav(short, milliseconds=100)
    with pytest.raises(MediaIntegrationError, match="wav_metadata_out_of_bounds"):
        registry.register_listening(asset_key="L1:AUD", wav_path=short)


def test_media_tamper_is_detected(tmp_path: Path) -> None:
    database, _, registry = fixture(tmp_path)
    path = tmp_path / "listening.wav"
    make_wav(path)
    registry.register_listening(asset_key="L1:AUD", wav_path=path)
    exported = registry.export(output_root=tmp_path / "out")
    manifest = json.loads(Path(exported["manifest_path"]).read_text())
    stored = Path(manifest["records"][0]["stored_path"])
    stored.write_bytes(stored.read_bytes() + b"x")
    report = validate(database, Path(exported["manifest_path"]))
    assert report["error_count"] > 0
