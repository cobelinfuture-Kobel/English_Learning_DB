#!/usr/bin/env python3
"""Private learner profile, session and exposure-state storage for A1FS V1.

Task: A1FS-V1-M3_LearnerProfileSessionAndStateStorage
The store deliberately has no scoring or mastery-write API.  A2 lessons are
catalogued as handoff metadata but cannot be used to start learner sessions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

TASK_ID = "A1FS-V1-M3_LearnerProfileSessionAndStateStorage"
SCHEMA_VERSION = "a1fs.v1.m3.learner_state.sqlite.v1"
STATUS = "PASS_A1FS_V1_M3_LEARNER_PROFILE_SESSION_STATE_STORAGE_READY"
CONSUMER_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
NEXT_SHORT_STEP = "A1FS-V1-M4_LessonPlannerSelectionAndA2Lock"
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class StateStoreError(ValueError):
    """Fail-closed state storage error."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp(value: str | None) -> str:
    value = value or _utc_now()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StateStoreError("timestamp_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise StateStoreError("timestamp_must_be_utc")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _identifier(value: str, code: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise StateStoreError(f"{code}_invalid")
    return value


def _read_consumer(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes(); value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise StateStoreError(f"consumer_unreadable:{exc}") from exc
    if not isinstance(value, dict) or value.get("validation_status") != CONSUMER_STATUS:
        raise StateStoreError("consumer_status_invalid")
    assets = value.get("asset_records"); lessons = value.get("lesson_catalog")
    if not isinstance(assets, list) or not isinstance(lessons, list) or not assets or not lessons:
        raise StateStoreError("consumer_catalog_invalid")
    return value, raw


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lesson_catalog (
  lesson_id TEXT PRIMARY KEY,
  lesson_node_id TEXT NOT NULL UNIQUE,
  skill TEXT NOT NULL CHECK(skill IN ('LISTENING','SPEAKING','READING','WRITING')),
  level TEXT NOT NULL CHECK(level IN ('A1','A1+','A2')),
  roles_json TEXT NOT NULL,
  requirement_node_ids_json TEXT NOT NULL,
  payload_access_allowed INTEGER NOT NULL CHECK(payload_access_allowed IN (0,1))
);
CREATE TABLE IF NOT EXISTS lesson_assets (
  asset_key TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL,
  lesson_id TEXT NOT NULL REFERENCES lesson_catalog(lesson_id),
  role TEXT NOT NULL,
  content_digest TEXT NOT NULL,
  UNIQUE(lesson_id, asset_key)
);
CREATE TABLE IF NOT EXISTS learner_profiles (
  learner_id TEXT PRIMARY KEY,
  display_label TEXT NOT NULL,
  locale TEXT NOT NULL,
  timezone_name TEXT NOT NULL,
  profile_state TEXT NOT NULL CHECK(profile_state IN ('ACTIVE','INACTIVE')),
  profile_version INTEGER NOT NULL CHECK(profile_version >= 1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learning_sessions (
  session_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL REFERENCES learner_profiles(learner_id),
  lesson_id TEXT NOT NULL REFERENCES lesson_catalog(lesson_id),
  skill TEXT NOT NULL,
  level TEXT NOT NULL CHECK(level IN ('A1','A1+')),
  session_state TEXT NOT NULL CHECK(session_state IN ('ACTIVE','COMPLETED','ABANDONED')),
  session_version INTEGER NOT NULL CHECK(session_version >= 1),
  started_at TEXT NOT NULL,
  ended_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_session_per_learner
ON learning_sessions(learner_id) WHERE session_state = 'ACTIVE';
CREATE TABLE IF NOT EXISTS lesson_progress (
  learner_id TEXT NOT NULL REFERENCES learner_profiles(learner_id),
  lesson_id TEXT NOT NULL REFERENCES lesson_catalog(lesson_id),
  skill TEXT NOT NULL,
  level TEXT NOT NULL CHECK(level IN ('A1','A1+')),
  progress_state TEXT NOT NULL CHECK(progress_state IN ('NOT_STARTED','IN_PROGRESS','PAUSED')),
  exposure_count INTEGER NOT NULL CHECK(exposure_count >= 0),
  progress_version INTEGER NOT NULL CHECK(progress_version >= 1),
  first_seen_at TEXT,
  last_seen_at TEXT,
  PRIMARY KEY(learner_id, lesson_id)
);
CREATE TABLE IF NOT EXISTS state_events (
  event_seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  learner_id TEXT NOT NULL,
  session_id TEXT,
  event_type TEXT NOT NULL CHECK(event_type IN ('PROFILE_CREATED','PROFILE_DEACTIVATED','SESSION_STARTED','ASSET_EXPOSED','SESSION_ENDED')),
  event_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  previous_hash TEXT NOT NULL,
  event_hash TEXT NOT NULL UNIQUE
);
"""


class LearnerStateStore:
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback(); raise
        finally:
            connection.close()

    def initialize(self, consumer_path: Path) -> dict[str, Any]:
        consumer, raw = _read_consumer(consumer_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._write() as connection:
            connection.executescript(SCHEMA_SQL)
            current = connection.execute("SELECT value FROM metadata WHERE key='consumer_sha256'").fetchone()
            digest = _sha256(raw)
            if current and current[0] != digest:
                raise StateStoreError("database_consumer_binding_mismatch")
            metadata = {
                "task_id": TASK_ID, "schema_version": SCHEMA_VERSION,
                "validation_status": STATUS, "consumer_sha256": digest,
                "scoring_write_enabled": "false", "mastery_write_enabled": "false",
                "a2_session_enabled": "false", "learner_release_approved": "false",
                "next_short_step": NEXT_SHORT_STEP,
            }
            connection.executemany("INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)", metadata.items())
            for lesson in consumer["lesson_catalog"]:
                connection.execute(
                    """INSERT OR IGNORE INTO lesson_catalog
                    (lesson_id,lesson_node_id,skill,level,roles_json,requirement_node_ids_json,payload_access_allowed)
                    VALUES(?,?,?,?,?,?,?)""",
                    (lesson["lesson_id"], lesson["lesson_node_id"], lesson["skill"], lesson["level"],
                     _canonical(sorted(lesson["roles"])), _canonical(sorted(lesson["requirement_node_ids"])),
                     int(lesson["level"] in {"A1", "A1+"})),
                )
            for asset in consumer["asset_records"]:
                connection.execute(
                    """INSERT OR IGNORE INTO lesson_assets
                    (asset_key,asset_id,lesson_id,role,content_digest) VALUES(?,?,?,?,?)""",
                    (asset["asset_key"], asset["asset_id"], asset["lesson_id"], asset["role"], asset["content_digest"]),
                )
            lesson_count = connection.execute("SELECT COUNT(*) FROM lesson_catalog").fetchone()[0]
            asset_count = connection.execute("SELECT COUNT(*) FROM lesson_assets").fetchone()[0]
            if lesson_count != consumer["counts"]["lesson_count"] or asset_count != consumer["counts"]["asset_record_count"]:
                raise StateStoreError("database_catalog_count_mismatch")
        try:
            os.chmod(self.database_path, 0o600)
        except OSError as exc:
            raise StateStoreError(f"database_private_permissions_failed:{exc}") from exc
        return {"validation_status": STATUS, "database": str(self.database_path), "lesson_count": lesson_count, "asset_count": asset_count, "next_short_step": NEXT_SHORT_STEP}

    @staticmethod
    def _append_event(connection: sqlite3.Connection, *, learner_id: str, session_id: str | None,
                      event_type: str, event_at: str, payload: dict[str, Any], event_id: str | None = None) -> str:
        event_id = event_id or str(uuid.uuid4())
        previous = connection.execute("SELECT event_hash FROM state_events ORDER BY event_seq DESC LIMIT 1").fetchone()
        previous_hash = previous[0] if previous else "0" * 64
        core = {"event_id": event_id, "learner_id": learner_id, "session_id": session_id,
                "event_type": event_type, "event_at": event_at, "payload": payload}
        event_hash = _sha256((previous_hash + _canonical(core)).encode("utf-8"))
        connection.execute(
            "INSERT INTO state_events(event_id,learner_id,session_id,event_type,event_at,payload_json,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?,?)",
            (event_id, learner_id, session_id, event_type, event_at, _canonical(payload), previous_hash, event_hash),
        )
        return event_id

    def create_profile(self, *, learner_id: str, display_label: str, locale: str = "zh-TW",
                       timezone_name: str = "Asia/Taipei", at: str | None = None) -> dict[str, Any]:
        learner_id = _identifier(learner_id, "learner_id"); at = _timestamp(at)
        display_label = str(display_label).strip(); locale = str(locale).strip(); timezone_name = str(timezone_name).strip()
        if not display_label or len(display_label) > 80: raise StateStoreError("display_label_invalid")
        if not locale or len(locale) > 35 or not timezone_name or len(timezone_name) > 64: raise StateStoreError("profile_locale_or_timezone_invalid")
        with self._write() as connection:
            if connection.execute("SELECT 1 FROM learner_profiles WHERE learner_id=?", (learner_id,)).fetchone():
                raise StateStoreError("learner_profile_exists")
            connection.execute("INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)", (learner_id, display_label, locale, timezone_name, "ACTIVE", 1, at, at))
            self._append_event(connection, learner_id=learner_id, session_id=None, event_type="PROFILE_CREATED", event_at=at,
                               payload={"display_label": display_label, "locale": locale, "timezone_name": timezone_name})
        return self.profile_snapshot(learner_id)

    def start_session(self, *, learner_id: str, lesson_id: str, session_id: str | None = None,
                      expected_profile_version: int | None = None, at: str | None = None) -> dict[str, Any]:
        learner_id = _identifier(learner_id, "learner_id"); lesson_id = _identifier(lesson_id, "lesson_id")
        session_id = _identifier(session_id or str(uuid.uuid4()), "session_id"); at = _timestamp(at)
        with self._write() as connection:
            profile = connection.execute("SELECT * FROM learner_profiles WHERE learner_id=?", (learner_id,)).fetchone()
            if not profile or profile["profile_state"] != "ACTIVE": raise StateStoreError("learner_profile_not_active")
            if expected_profile_version is not None and profile["profile_version"] != expected_profile_version: raise StateStoreError("profile_version_conflict")
            lesson = connection.execute("SELECT * FROM lesson_catalog WHERE lesson_id=?", (lesson_id,)).fetchone()
            if not lesson: raise StateStoreError("lesson_not_found")
            if lesson["level"] == "A2" or lesson["payload_access_allowed"] != 1: raise StateStoreError("A2_SESSION_LOCKED")
            if connection.execute("SELECT 1 FROM learning_sessions WHERE learner_id=? AND session_state='ACTIVE'", (learner_id,)).fetchone():
                raise StateStoreError("active_session_exists")
            connection.execute("INSERT INTO learning_sessions VALUES(?,?,?,?,?,?,?,?,?)", (session_id, learner_id, lesson_id, lesson["skill"], lesson["level"], "ACTIVE", 1, at, None))
            connection.execute(
                """INSERT INTO lesson_progress(learner_id,lesson_id,skill,level,progress_state,exposure_count,progress_version,first_seen_at,last_seen_at)
                VALUES(?,?,?,?,?,0,1,NULL,NULL) ON CONFLICT(learner_id,lesson_id) DO UPDATE SET
                progress_state='IN_PROGRESS', progress_version=lesson_progress.progress_version+1""",
                (learner_id, lesson_id, lesson["skill"], lesson["level"], "IN_PROGRESS"),
            )
            self._append_event(connection, learner_id=learner_id, session_id=session_id, event_type="SESSION_STARTED", event_at=at,
                               payload={"lesson_id": lesson_id, "skill": lesson["skill"], "level": lesson["level"]})
        return self.session_snapshot(session_id)

    def record_exposure(self, *, session_id: str, asset_key: str, expected_session_version: int,
                        at: str | None = None) -> dict[str, Any]:
        session_id = _identifier(session_id, "session_id"); asset_key = _identifier(asset_key, "asset_key"); at = _timestamp(at)
        with self._write() as connection:
            session = connection.execute("SELECT * FROM learning_sessions WHERE session_id=?", (session_id,)).fetchone()
            if not session or session["session_state"] != "ACTIVE": raise StateStoreError("session_not_active")
            if session["session_version"] != expected_session_version: raise StateStoreError("session_version_conflict")
            asset = connection.execute("SELECT * FROM lesson_assets WHERE asset_key=?", (asset_key,)).fetchone()
            if not asset or asset["lesson_id"] != session["lesson_id"]: raise StateStoreError("asset_not_in_session_lesson")
            connection.execute("UPDATE learning_sessions SET session_version=session_version+1 WHERE session_id=?", (session_id,))
            connection.execute(
                """UPDATE lesson_progress SET progress_state='IN_PROGRESS', exposure_count=exposure_count+1,
                progress_version=progress_version+1, first_seen_at=COALESCE(first_seen_at,?), last_seen_at=?
                WHERE learner_id=? AND lesson_id=?""",
                (at, at, session["learner_id"], session["lesson_id"]),
            )
            self._append_event(connection, learner_id=session["learner_id"], session_id=session_id, event_type="ASSET_EXPOSED", event_at=at,
                               payload={"lesson_id": session["lesson_id"], "asset_key": asset_key, "role": asset["role"], "content_digest": asset["content_digest"]})
        return self.session_snapshot(session_id)

    def end_session(self, *, session_id: str, outcome: str, expected_session_version: int,
                    at: str | None = None) -> dict[str, Any]:
        session_id = _identifier(session_id, "session_id"); at = _timestamp(at)
        if outcome not in {"COMPLETED", "ABANDONED"}: raise StateStoreError("session_outcome_invalid")
        with self._write() as connection:
            session = connection.execute("SELECT * FROM learning_sessions WHERE session_id=?", (session_id,)).fetchone()
            if not session or session["session_state"] != "ACTIVE": raise StateStoreError("session_not_active")
            if session["session_version"] != expected_session_version: raise StateStoreError("session_version_conflict")
            connection.execute("UPDATE learning_sessions SET session_state=?,session_version=session_version+1,ended_at=? WHERE session_id=?", (outcome, at, session_id))
            connection.execute("UPDATE lesson_progress SET progress_state='PAUSED',progress_version=progress_version+1 WHERE learner_id=? AND lesson_id=?", (session["learner_id"], session["lesson_id"]))
            self._append_event(connection, learner_id=session["learner_id"], session_id=session_id, event_type="SESSION_ENDED", event_at=at,
                               payload={"lesson_id": session["lesson_id"], "outcome": outcome})
        return self.session_snapshot(session_id)

    def deactivate_profile(self, *, learner_id: str, expected_profile_version: int, at: str | None = None) -> dict[str, Any]:
        learner_id = _identifier(learner_id, "learner_id"); at = _timestamp(at)
        with self._write() as connection:
            profile = connection.execute("SELECT * FROM learner_profiles WHERE learner_id=?", (learner_id,)).fetchone()
            if not profile or profile["profile_state"] != "ACTIVE": raise StateStoreError("learner_profile_not_active")
            if profile["profile_version"] != expected_profile_version: raise StateStoreError("profile_version_conflict")
            if connection.execute("SELECT 1 FROM learning_sessions WHERE learner_id=? AND session_state='ACTIVE'", (learner_id,)).fetchone(): raise StateStoreError("active_session_exists")
            connection.execute("UPDATE learner_profiles SET profile_state='INACTIVE',profile_version=profile_version+1,updated_at=? WHERE learner_id=?", (at, learner_id))
            self._append_event(connection, learner_id=learner_id, session_id=None, event_type="PROFILE_DEACTIVATED", event_at=at, payload={})
        return self.profile_snapshot(learner_id)

    def session_snapshot(self, session_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM learning_sessions WHERE session_id=?", (session_id,)).fetchone()
            if not row: raise StateStoreError("session_not_found")
            return dict(row)

    def profile_snapshot(self, learner_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            profile = connection.execute("SELECT * FROM learner_profiles WHERE learner_id=?", (learner_id,)).fetchone()
            if not profile: raise StateStoreError("learner_profile_not_found")
            sessions = [dict(row) for row in connection.execute("SELECT * FROM learning_sessions WHERE learner_id=? ORDER BY started_at,session_id", (learner_id,))]
            progress = [dict(row) for row in connection.execute("SELECT * FROM lesson_progress WHERE learner_id=? ORDER BY skill,level,lesson_id", (learner_id,))]
            return {"profile": dict(profile), "sessions": sessions, "progress": progress,
                    "claim_boundaries": {"scoring_recorded": False, "mastery_recorded": False, "a2_unlocked": False}}


def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init"); init.add_argument("--database", type=Path, required=True); init.add_argument("--consumer", type=Path, required=True)
    create = sub.add_parser("create-profile"); create.add_argument("--database", type=Path, required=True); create.add_argument("--learner-id", required=True); create.add_argument("--display-label", required=True); create.add_argument("--locale", default="zh-TW"); create.add_argument("--timezone", default="Asia/Taipei")
    start = sub.add_parser("start-session"); start.add_argument("--database", type=Path, required=True); start.add_argument("--learner-id", required=True); start.add_argument("--lesson-id", required=True); start.add_argument("--session-id")
    expose = sub.add_parser("record-exposure"); expose.add_argument("--database", type=Path, required=True); expose.add_argument("--session-id", required=True); expose.add_argument("--asset-key", required=True); expose.add_argument("--expected-session-version", type=int, required=True)
    end = sub.add_parser("end-session"); end.add_argument("--database", type=Path, required=True); end.add_argument("--session-id", required=True); end.add_argument("--outcome", required=True); end.add_argument("--expected-session-version", type=int, required=True)
    snap = sub.add_parser("snapshot"); snap.add_argument("--database", type=Path, required=True); snap.add_argument("--learner-id", required=True)
    args = parser.parse_args(); store = LearnerStateStore(args.database)
    if args.command == "init": result = store.initialize(args.consumer)
    elif args.command == "create-profile": result = store.create_profile(learner_id=args.learner_id, display_label=args.display_label, locale=args.locale, timezone_name=args.timezone)
    elif args.command == "start-session": result = store.start_session(learner_id=args.learner_id, lesson_id=args.lesson_id, session_id=args.session_id)
    elif args.command == "record-exposure": result = store.record_exposure(session_id=args.session_id, asset_key=args.asset_key, expected_session_version=args.expected_session_version)
    elif args.command == "end-session": result = store.end_session(session_id=args.session_id, outcome=args.outcome, expected_session_version=args.expected_session_version)
    else: result = store.profile_snapshot(args.learner_id)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
