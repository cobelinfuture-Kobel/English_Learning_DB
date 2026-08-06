from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as e2e


LEARNER_ID = "A1FS_V121_LOCAL_LEARNER"
SESSION_ID = "U01QB15:READING:postcommit-recovery"
LESSON_ID = "A1FS_ONLINE_V1:GRAMMAR_ARTICLES_BASIC:READING"


def _database(path: Path) -> Path:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE learning_sessions(
              learner_id TEXT NOT NULL,
              session_id TEXT PRIMARY KEY,
              lesson_id TEXT NOT NULL,
              skill TEXT NOT NULL,
              session_state TEXT NOT NULL,
              session_version INTEGER NOT NULL
            );
            CREATE TABLE u01qb13_session_bindings(
              session_id TEXT NOT NULL,
              item_id TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO learning_sessions VALUES(?,?,?,?,?,?)",
            (LEARNER_ID, SESSION_ID, LESSON_ID, "READING", "ACTIVE", 17),
        )
        connection.execute(
            "INSERT INTO u01qb13_session_bindings VALUES(?,?)",
            (SESSION_ID, "U01QB01-U01-PF04-TEST"),
        )
        connection.commit()
    return path


class _FakeApp:
    def __init__(self, database: Path, *, recovery_fails: bool = False) -> None:
        self.database_path = database
        self.default_learner_id = LEARNER_ID
        self.recovery_fails = recovery_fails
        self.refresh_calls = 0

    def refresh_canonical_learning(self, *, learner_id: str):
        assert learner_id == LEARNER_ID
        self.refresh_calls += 1
        if self.recovery_fails:
            raise OSError("simulated derived refresh failure")
        return {"m7": {"mastered_required_count": 0}, "m8": {"scheduled_node_count": 0}}


def _commit_then_raise(self, payload):
    with sqlite3.connect(self.database_path) as connection:
        connection.execute(
            "UPDATE learning_sessions SET session_state='COMPLETED',session_version=18 WHERE session_id=?",
            (payload["session_id"],),
        )
        connection.commit()
    raise OSError("simulated post-commit failure")


def _raise_before_commit(self, payload):
    raise OSError("simulated pre-commit failure")


def _refresh_row(database: Path):
    with sqlite3.connect(database) as connection:
        return connection.execute(
            f"SELECT refresh_state,original_error_type,recovery_error_type FROM {e2e.REFRESH_RECOVERY_TABLE} WHERE session_id=?",
            (SESSION_ID,),
        ).fetchone()


def test_postcommit_exception_preserves_completed_truth_and_recovers_derived_state(tmp_path: Path) -> None:
    database = _database(tmp_path / "learner.sqlite3")
    app = _FakeApp(database)
    original = e2e._ORIGINAL_COMPLETE_SESSION
    e2e._ORIGINAL_COMPLETE_SESSION = _commit_then_raise
    try:
        result = e2e._complete_session_recovery_safe(
            app,
            {"session_id": SESSION_ID, "expected_session_version": 17},
        )
    finally:
        e2e._ORIGINAL_COMPLETE_SESSION = original

    assert result["session_state"] == "COMPLETED"
    assert result["completion_committed"] is True
    assert result["canonical_refresh_status"] == "RECOVERED_AFTER_COMMIT"
    assert result["canonical_refresh_recovery_required"] is False
    assert result["post_completion_error_type"] == "OSError"
    assert app.refresh_calls == 1
    assert _refresh_row(database) == ("PASS", "OSError", None)


def test_failed_derived_recovery_is_durable_and_replayed_before_next_form(tmp_path: Path) -> None:
    database = _database(tmp_path / "learner.sqlite3")
    app = _FakeApp(database, recovery_fails=True)
    original = e2e._ORIGINAL_COMPLETE_SESSION
    e2e._ORIGINAL_COMPLETE_SESSION = _commit_then_raise
    try:
        result = e2e._complete_session_recovery_safe(
            app,
            {"session_id": SESSION_ID, "expected_session_version": 17},
        )
    finally:
        e2e._ORIGINAL_COMPLETE_SESSION = original

    assert result["session_state"] == "COMPLETED"
    assert result["completion_committed"] is True
    assert result["canonical_refresh_status"] == "RECOVERY_REQUIRED"
    assert result["canonical_refresh_recovery_required"] is True
    assert _refresh_row(database) == ("RECOVERY_REQUIRED", "OSError", "OSError")

    app.recovery_fails = False
    assert e2e._reconcile_pending_refresh(app) == 1
    assert app.refresh_calls == 2
    assert _refresh_row(database) == ("PASS", "OSError", None)


def test_precommit_failure_is_not_converted_into_false_completed_success(tmp_path: Path) -> None:
    database = _database(tmp_path / "learner.sqlite3")
    app = _FakeApp(database)
    original = e2e._ORIGINAL_COMPLETE_SESSION
    e2e._ORIGINAL_COMPLETE_SESSION = _raise_before_commit
    try:
        with pytest.raises(OSError, match="pre-commit"):
            e2e._complete_session_recovery_safe(
                app,
                {"session_id": SESSION_ID, "expected_session_version": 17},
            )
    finally:
        e2e._ORIGINAL_COMPLETE_SESSION = original

    with sqlite3.connect(database) as connection:
        state = connection.execute(
            "SELECT session_state FROM learning_sessions WHERE session_id=?",
            (SESSION_ID,),
        ).fetchone()[0]
    assert state == "ACTIVE"


def test_unit01_frontend_reconciles_transport_failure_to_backend_terminal_truth() -> None:
    source = Path("product/a1fs_v1_2_1/runtime/secure_static/u01qb15.js").read_text(
        encoding="utf-8"
    )
    assert "const u01qb15LegacyFinish = finish;" in source
    assert "async function u01qb15BackendTerminalTruth()" in source
    assert "truth.session_inactive&&truth.form_inactive" in source
    assert "frontend_reconciled_after_transport_failure:true" in source
    assert (
        "if(!u01qb15ActiveSession()||active.u01qb16e_reassessment)return u01qb15LegacyFinish(path);"
        in source
    )
