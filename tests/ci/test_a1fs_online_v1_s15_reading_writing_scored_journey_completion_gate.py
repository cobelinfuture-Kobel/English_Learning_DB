from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import _a1fs_online_v1_s15_scored_journey_acceptance as acceptance
from ulga.builders import build_a1fs_online_v1_s15_reading_writing_scored_journey_completion_gate as s15


LESSON_ID = "A1FS_ONLINE_V1:GRAMMAR_ARTICLES_BASIC:READING"
SESSION_ID = "TEST:S15:READING"
ASSET_KEYS = [f"ASSET:{index}" for index in range(1, 5)]
WRITING_LESSON_ID = "A1FS_ONLINE_V1:GRAMMAR_ARTICLES_BASIC:WRITING"
WRITING_ASSET_KEYS = [f"WRITING_ASSET:{index}" for index in range(1, 5)]


def _application(database: Path) -> s15.ScoredJourneyApplication:
    app = object.__new__(s15.ScoredJourneyApplication)
    app.database_path = database
    app.lesson_bundles = {
        LESSON_ID: {
            "lesson": {"lesson_id": LESSON_ID, "skill": "READING", "level": "A1"},
            "assets": [{"asset_key": key} for key in ASSET_KEYS],
        }
    }
    app.default_learner_id = "LEARNER"
    return app


def _database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE learning_sessions(
              session_id TEXT PRIMARY KEY, learner_id TEXT, lesson_id TEXT, skill TEXT,
              level TEXT, session_state TEXT, session_version INTEGER
            );
            CREATE TABLE response_contracts(
              asset_key TEXT PRIMARY KEY, lesson_id TEXT, contract_json TEXT, capture_enabled INTEGER
            );
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY, learner_id TEXT, session_id TEXT, lesson_id TEXT,
              asset_key TEXT, attempt_sequence INTEGER, submitted_at TEXT
            );
            CREATE TABLE scoring_results(
              attempt_id TEXT PRIMARY KEY, outcome TEXT, score REAL, human_review_required INTEGER
            );
            """
        )
        connection.execute(
            "INSERT INTO learning_sessions VALUES(?,?,?,?,?,?,?)",
            (SESSION_ID, "LEARNER", LESSON_ID, "READING", "A1", "ACTIVE", 8),
        )
        for key in ASSET_KEYS:
            contract = {
                "scoring_mode": "NORMALIZED_TEXT",
                "human_review_fallback": False,
            }
            connection.execute(
                "INSERT INTO response_contracts VALUES(?,?,?,1)",
                (key, LESSON_ID, json.dumps(contract)),
            )
        attempts = [
            ("A1", ASSET_KEYS[0], 1, "AUTO_FAIL"),
            ("A2", ASSET_KEYS[0], 2, "AUTO_PASS"),
            ("A3", ASSET_KEYS[1], 1, "AUTO_PASS"),
            ("A4", ASSET_KEYS[2], 1, "PENDING_HUMAN_REVIEW"),
        ]
        for attempt_id, asset_key, sequence, outcome in attempts:
            connection.execute(
                "INSERT INTO response_attempts VALUES(?,?,?,?,?,?,?)",
                (attempt_id, "LEARNER", SESSION_ID, LESSON_ID, asset_key, sequence, "2026-01-01T00:00:00Z"),
            )
            connection.execute(
                "INSERT INTO scoring_results VALUES(?,?,?,?)",
                (attempt_id, outcome, None, int(outcome == "PENDING_HUMAN_REVIEW")),
            )
        connection.commit()


def _writing_contract_database(path: Path, *, existing_feature_rubric: bool) -> dict[str, dict]:
    bundles = {
        WRITING_LESSON_ID: {
            "lesson": {"lesson_id": WRITING_LESSON_ID, "skill": "WRITING", "level": "A1"},
            "assets": [{"asset_key": key} for key in WRITING_ASSET_KEYS],
        }
    }
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE response_contracts(
                   asset_key TEXT PRIMARY KEY,
                   lesson_id TEXT NOT NULL,
                   contract_json TEXT NOT NULL,
                   contract_digest TEXT NOT NULL,
                   capture_enabled INTEGER NOT NULL
               )"""
        )
        for index, key in enumerate(WRITING_ASSET_KEYS):
            feature = existing_feature_rubric and index == 0
            contract = {
                "asset_key": key,
                "lesson_id": WRITING_LESSON_ID,
                "skill": "WRITING",
                "role": "PRD",
                "prompt": "Write one sentence.",
                "capture_enabled": True,
                "response_type": "string",
                "scoring_mode": "FEATURE_RUBRIC" if feature else "NORMALIZED_TEXT",
                "accepted_texts": [] if feature else ["This is correct."],
                "accepted_sequence": [],
                "case_insensitive": True,
                "punctuation_tolerance": True,
                "human_review_fallback": feature,
                "rubric": {"complete_response": True} if feature else {},
                "m12_item_id": f"A1FS_ASSET:{key}",
                "m12_session_bank_sha256": None,
            }
            connection.execute(
                "INSERT INTO response_contracts VALUES(?,?,?,?,1)",
                (key, WRITING_LESSON_ID, s15.m6.canonical(contract), s15.m6.sha(contract)),
            )
        connection.commit()
    return bundles


def test_s15_completion_gate_uses_latest_attempt_and_blocks_missing_or_pending(tmp_path: Path) -> None:
    database = tmp_path / "gate.sqlite3"
    _database(database)
    app = _application(database)

    gate = app.completion_readiness(SESSION_ID)
    assert gate["required_response_count"] == 4
    assert gate["attempted_response_count"] == 3
    assert gate["passed_response_count"] == 2
    assert gate["not_attempted_count"] == 1
    assert gate["pending_human_review_count"] == 1
    assert gate["retry_required_count"] == 0
    assert gate["completion_allowed"] is False
    assert set(gate["blocking_reason_codes"]) == {
        "REQUIRED_RESPONSE_NOT_ATTEMPTED",
        "HUMAN_REVIEW_PENDING",
    }
    first = gate["assets"][0]
    assert first["attempt_count"] == 2
    assert first["latest_outcome"] == "AUTO_PASS"
    assert first["completion_state"] == "PASSED"

    with pytest.raises(s15.ScoredJourneyError, match="completion_gate_blocked"):
        app.complete_session({"session_id": SESSION_ID, "expected_session_version": 8})


def test_s15_completion_gate_allows_human_approval_and_final_required_attempt(tmp_path: Path) -> None:
    database = tmp_path / "gate.sqlite3"
    _database(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE scoring_results SET outcome='HUMAN_APPROVE',score=1.0,human_review_required=0 WHERE attempt_id='A4'"
        )
        connection.execute(
            "INSERT INTO response_attempts VALUES(?,?,?,?,?,?,?)",
            ("A5", "LEARNER", SESSION_ID, LESSON_ID, ASSET_KEYS[3], 1, "2026-01-01T00:01:00Z"),
        )
        connection.execute("INSERT INTO scoring_results VALUES('A5','AUTO_PASS',1.0,0)")
        connection.commit()
    app = _application(database)

    gate = app.completion_readiness(SESSION_ID)
    assert gate["attempted_response_count"] == 4
    assert gate["passed_response_count"] == 4
    assert gate["blocking_reason_codes"] == []
    assert gate["completion_allowed"] is True
    assert gate["mastery_claimed"] is False


def test_s15_acceptance_overlays_one_review_contract_when_production_writing_is_deterministic(tmp_path: Path) -> None:
    database = tmp_path / "writing.sqlite3"
    bundles = _writing_contract_database(database, existing_feature_rubric=False)

    result = acceptance._prepare_writing_review_acceptance(database=database, bundles=bundles)

    assert result["lesson_id"] == WRITING_LESSON_ID
    assert result["production_feature_rubric_contract_count"] == 0
    assert result["production_writing_scoring_mode_counts"] == {"NORMALIZED_TEXT": 4}
    assert result["acceptance_review_overlay_used"] is True
    assert result["acceptance_review_overlay_asset_key"] == WRITING_ASSET_KEYS[0]
    modes = [row["scoring_mode"] for row in result["contracts"]]
    assert modes.count("FEATURE_RUBRIC") == 1
    assert modes.count("NORMALIZED_TEXT") == 3


def test_s15_acceptance_preserves_real_review_contract_without_overlay(tmp_path: Path) -> None:
    database = tmp_path / "writing.sqlite3"
    bundles = _writing_contract_database(database, existing_feature_rubric=True)

    result = acceptance._prepare_writing_review_acceptance(database=database, bundles=bundles)

    assert result["production_feature_rubric_contract_count"] == 1
    assert result["acceptance_review_overlay_used"] is False
    assert result["acceptance_review_overlay_asset_key"] == ""
    assert [row["scoring_mode"] for row in result["contracts"]].count("FEATURE_RUBRIC") == 1


def test_s15_bootstrap_marks_only_reading_and_writing_as_scored_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    source = {
        "task_id": s15.s14.TASK_ID,
        "schema_version": s15.s14.SCHEMA_VERSION,
        "validation_status": s15.s14.PASS_STATUS,
        "product_status": s15.s14.PRODUCT_STATUS,
        "release_profile": s15.RELEASE_PROFILE,
        "units": [{
            "lanes": [
                {"skill": "READING"},
                {"skill": "WRITING"},
                {"skill": "SPEAKING"},
            ]
        }],
        "learner_product_semantics": {
            "session_completion_implies_unit_completion": False,
            "session_completion_implies_mastery": False,
        },
    }
    monkeypatch.setattr(s15.s14.LearnerFacingApplication, "bootstrap", lambda self: source)
    app = object.__new__(s15.ScoredJourneyApplication)
    value = app.bootstrap()
    lanes = {lane["skill"]: lane for lane in value["units"][0]["lanes"]}
    assert lanes["READING"]["completion_gate_required"] is True
    assert lanes["WRITING"]["completion_gate_required"] is True
    assert lanes["SPEAKING"]["completion_gate_required"] is False
    assert value["learner_product_semantics"]["latest_attempt_controls_completion"] is True
    assert value["learner_product_semantics"]["pending_human_review_blocks_completion"] is True
    assert value["learner_product_semantics"]["session_completion_implies_mastery"] is False


def test_s15_secure_static_surfaces_gate_attempt_history_and_review_states(tmp_path: Path) -> None:
    learner = tmp_path / "learner"
    secure = tmp_path / "secure"
    s15._write_scored_static(learner)
    s15.s11._write_secure_static(learner, secure)
    index = (secure / "index.html").read_text(encoding="utf-8")
    app = (secure / "app.js").read_text(encoding="utf-8")
    assert "本次學習完成條件" in index
    assert "最新作答皆通過或經人工核准" in index
    assert "completion_gate" in app
    assert "attempt_count" in app
    assert "PENDING_HUMAN_REVIEW" in app
    assert "HUMAN_APPROVE" in app
    assert "complete.disabled=!gate.completion_allowed" in app
    assert "innerHTML" not in app


def test_s15_launch_bundle_is_secret_free_and_bound_to_s15(tmp_path: Path) -> None:
    outputs = s15._write_launch_bundle(
        target_root=tmp_path / "launch",
        receipt_path=tmp_path / "receipt.private.json",
        auth_state_db=tmp_path / "s14_auth.sqlite3",
    )
    start = Path(outputs["start_script_path"]).read_text(encoding="utf-8")
    stop = Path(outputs["stop_script_path"]).read_text(encoding="utf-8")
    contract = s15.read_json(Path(outputs["launch_contract_path"]), "contract")
    assert "build_a1fs_online_v1_s15_reading_writing_scored_journey_completion_gate" in start
    assert s15.CANARY_PASSWORD not in start
    assert s15.CANARY_SESSION_SECRET not in start
    assert "PID_OWNERSHIP_MISMATCH" in stop
    assert contract["reading_writing_completion_gate_enabled"] is True
    assert contract["external_network_binding_allowed"] is False
    assert contract["cloudflare_enabled"] is False
    assert contract["audio_enabled"] is False
