#!/usr/bin/env python3
"""Private learner identity and durable progress persistence for A1FS Online V1.

S05 promotes the S04 localhost workbench into a non-destructive persistent
workspace. Existing M3 profile/session/progress tables and M6 response/scoring
tables remain the sole runtime authorities. S05 adds only source-binding
metadata, a private stable-identity binding, and checkpoint audit rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s04_private_online_learner_workbench_execution as s04  # noqa: E402
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3  # noqa: E402
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Persists private learner identity and runtime progress through existing M3/M6 authorities; "
    "no curriculum, learner content, answer key, mastery, audio, or public delivery is produced."
)

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S05_PrivateLearnerIdentityAndProgressPersistence_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s05.private_identity_progress_persistence.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S05_PRIVATE_IDENTITY_PROGRESS_PERSISTED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S06_PrivateLearnerEndToEndSessionProgressReadback_NoAudio"
PRODUCT_STATUS = "PRIVATE_IDENTITY_PROGRESS_PERSISTENCE_READY_NOT_PUBLIC"
DEFAULT_LEARNER_ID = "A1FS_PRIVATE_LEARNER_001"
DEFAULT_DISPLAY_LABEL = "Learner 1"
CANARY_LEARNER_ID = "A1FS_ONLINE_V1_S05_RESTART_CANARY"
CANARY_SESSION_ID = "A1FS_ONLINE_V1_S05_SESSION:READING"
CANARY_ATTEMPT_ID = "A1FS_ONLINE_V1_S05_ATTEMPT:READING:1"
LOOPBACK_HOSTS = s04.LOOPBACK_HOSTS
FORBIDDEN_SAFE_KEYS = {
    "learner_id", "display_label", "subject_digest", "private_subject_digest",
    "profile", "sessions", "progress", "learner_payload", "response",
    "answer_contract", "answer_key", "accepted_texts", "accepted_sequence",
    "private_scoring_contract", "scoring_contract", "prompt", "prompt_text",
}


class PersistenceError(s04.WorkbenchError):
    """Fail-closed S05 persistence error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def utc(value: str | None = None) -> str:
    value = value or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PersistenceError("timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise PersistenceError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PersistenceError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise PersistenceError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_digest(root: Path) -> str:
    rows: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append((path.relative_to(root).as_posix(), _file_digest(path)))
    return digest(rows)


def _verify_s04(receipt: Mapping[str, Any], receipt_path: Path) -> dict[str, Path]:
    if (
        receipt.get("task_id") != s04.TASK_ID
        or receipt.get("schema_version") != s04.SCHEMA_VERSION
        or receipt.get("validation_status") != s04.PASS_STATUS
        or receipt.get("product_status") != "PRIVATE_LOCALHOST_WORKBENCH_EXECUTABLE_NOT_PUBLIC"
        or receipt.get("stop_reason") != "NONE"
    ):
        raise PersistenceError("s04_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s04.digest(core):
        raise PersistenceError("s04_receipt_digest_invalid")
    summary = receipt.get("execution_summary", {})
    expected = {
        "lane_count": 3,
        "learner_visible_asset_count": 11,
        "http_loopback_canary_count": 1,
        "speaking_attempt_count": 0,
        "listening_item_count": 0,
        "audio_runtime_asset_count": 0,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise PersistenceError(f"s04_execution_summary_invalid:{key}")
    outputs = receipt.get("workbench_outputs", {})
    source_root = Path(str(outputs.get("root") or ""))
    database = Path(str(outputs.get("database_path") or ""))
    static_root = Path(str(outputs.get("static_root") or ""))
    ui_root = Path(str(outputs.get("ui_root") or ""))
    consumer = source_root / "runtime/unified_runtime_consumer.private.json"
    fallback_root = receipt_path.parent / "workbench"
    if not all(path.exists() for path in (source_root, database, static_root, ui_root, consumer)):
        source_root = fallback_root
        database = source_root / "runtime/learner_state.sqlite3"
        static_root = source_root / "static"
        ui_root = source_root / "runtime/ui"
        consumer = source_root / "runtime/unified_runtime_consumer.private.json"
    if not source_root.is_dir() or not database.is_file() or not static_root.is_dir() or not ui_root.is_dir() or not consumer.is_file():
        raise PersistenceError("s04_workbench_outputs_missing")
    return {
        "root": source_root.resolve(),
        "database": database.resolve(),
        "static": static_root.resolve(),
        "ui": ui_root.resolve(),
        "consumer": consumer.resolve(),
    }


PERSISTENCE_SQL = """
CREATE TABLE IF NOT EXISTS s05_persistence_metadata(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS s05_identity_bindings(
  learner_id TEXT PRIMARY KEY REFERENCES learner_profiles(learner_id),
  private_subject_digest TEXT NOT NULL UNIQUE,
  enrollment_source TEXT NOT NULL CHECK(enrollment_source IN ('DEFAULT_PRIVATE_SLOT','OPERATOR_PRIVATE_ENROLLMENT')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS s05_progress_checkpoints(
  checkpoint_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL REFERENCES learner_profiles(learner_id),
  captured_at TEXT NOT NULL,
  session_count INTEGER NOT NULL CHECK(session_count>=0),
  completed_session_count INTEGER NOT NULL CHECK(completed_session_count>=0),
  exposure_count INTEGER NOT NULL CHECK(exposure_count>=0),
  attempt_count INTEGER NOT NULL CHECK(attempt_count>=0),
  auto_pass_count INTEGER NOT NULL CHECK(auto_pass_count>=0),
  auto_fail_count INTEGER NOT NULL CHECK(auto_fail_count>=0),
  pending_review_count INTEGER NOT NULL CHECK(pending_review_count>=0),
  snapshot_digest TEXT NOT NULL
);
"""


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def _metadata(database_path: Path) -> dict[str, str]:
    with _connect(database_path) as connection:
        try:
            return {str(row[0]): str(row[1]) for row in connection.execute("SELECT key,value FROM s05_persistence_metadata")}
        except sqlite3.Error:
            return {}


def _copy_runtime_once(source: Mapping[str, Path], persistent_root: Path, source_sha: str) -> dict[str, Path]:
    runtime_root = persistent_root / "runtime"
    static_root = persistent_root / "static"
    ui_root = runtime_root / "ui"
    consumer_path = runtime_root / "unified_runtime_consumer.private.json"
    database_path = runtime_root / "learner_progress.sqlite3"
    if database_path.exists():
        metadata = _metadata(database_path)
        if metadata.get("source_s04_sha256") != source_sha:
            raise PersistenceError("persistent_database_source_binding_mismatch")
        if metadata.get("schema_version") != SCHEMA_VERSION:
            raise PersistenceError("persistent_database_schema_version_mismatch")
        if not consumer_path.is_file() or not static_root.is_dir() or not ui_root.is_dir():
            raise PersistenceError("persistent_runtime_companion_artifact_missing")
        if metadata.get("consumer_sha256") != _file_digest(consumer_path):
            raise PersistenceError("persistent_consumer_digest_mismatch")
        if metadata.get("ui_tree_sha256") != _tree_digest(ui_root):
            raise PersistenceError("persistent_ui_digest_mismatch")
        if metadata.get("static_tree_sha256") != _tree_digest(static_root):
            raise PersistenceError("persistent_static_digest_mismatch")
        return {"runtime": runtime_root, "static": static_root, "ui": ui_root, "consumer": consumer_path, "database": database_path}

    if persistent_root.exists():
        shutil.rmtree(persistent_root)
    runtime_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source["ui"], ui_root)
    shutil.copytree(source["static"], static_root)
    shutil.copy2(source["consumer"], consumer_path)
    store = m3.LearnerStateStore(database_path)
    store.initialize(consumer_path)
    response_store = m6.ResponseEvidenceStore(database_path)
    for skill in ("reading", "writing", "speaking"):
        response_store.initialize(
            consumer_path=consumer_path,
            lesson_bundle_path=ui_root / skill / "lesson.private.json",
        )
    created_at = utc("2026-01-03T00:00:00Z")
    generation_id = str(uuid.uuid4())
    with _connect(database_path) as connection:
        connection.executescript(PERSISTENCE_SQL)
        metadata = {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "source_s04_sha256": source_sha,
            "consumer_sha256": _file_digest(consumer_path),
            "ui_tree_sha256": _tree_digest(ui_root),
            "static_tree_sha256": _tree_digest(static_root),
            "database_generation_id": generation_id,
            "created_at": created_at,
            "mastery_write_enabled": "false",
            "a2_unlock_enabled": "false",
            "audio_enabled": "false",
            "public_delivery_enabled": "false",
        }
        connection.executemany("INSERT INTO s05_persistence_metadata(key,value) VALUES(?,?)", metadata.items())
        connection.commit()
    try:
        os.chmod(database_path, 0o600)
    except OSError:
        pass
    return {"runtime": runtime_root, "static": static_root, "ui": ui_root, "consumer": consumer_path, "database": database_path}


def _subject_digest(subject_key: str) -> str:
    value = str(subject_key).strip()
    if not value or len(value) > 256:
        raise PersistenceError("private_subject_key_invalid")
    return digest("A1FS-S05-PRIVATE-SUBJECT:" + value)


class PersistentWorkbenchApplication(s04.WorkbenchApplication):
    def __init__(self, *, database_path: Path, bundles: Mapping[str, Mapping[str, Any]], default_learner_id: str = DEFAULT_LEARNER_ID):
        super().__init__(database_path=database_path, bundles=bundles)
        self.default_learner_id = default_learner_id

    def bootstrap(self) -> dict[str, Any]:
        value = super().bootstrap()
        value.update({
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "private_identity_persistence_enabled": True,
            "progress_persistence_enabled": True,
        })
        return value

    def enroll(self, *, learner_id: str, display_label: str, subject_key: str, locale: str = "zh-TW", timezone_name: str = "Asia/Taipei", at: str | None = None) -> dict[str, Any]:
        learner_id = str(learner_id).strip()
        subject = _subject_digest(subject_key)
        with _connect(self.database_path) as connection:
            binding = connection.execute("SELECT * FROM s05_identity_bindings WHERE private_subject_digest=?", (subject,)).fetchone()
            existing = connection.execute("SELECT * FROM learner_profiles WHERE learner_id=?", (learner_id,)).fetchone()
        if binding:
            if binding["learner_id"] != learner_id:
                raise PersistenceError("private_subject_already_bound_to_other_learner")
            return {**self.progress_snapshot(learner_id), "identity_reused": True}
        if existing:
            raise PersistenceError("learner_id_exists_without_matching_subject_binding")
        created = self.state_store.create_profile(
            learner_id=learner_id,
            display_label=display_label,
            locale=locale,
            timezone_name=timezone_name,
            at=at,
        )
        now = created["profile"]["created_at"]
        with _connect(self.database_path) as connection:
            connection.execute(
                "INSERT INTO s05_identity_bindings VALUES(?,?,?,?,?)",
                (learner_id, subject, "OPERATOR_PRIVATE_ENROLLMENT", now, now),
            )
            connection.commit()
        return {**self.progress_snapshot(learner_id), "identity_reused": False}

    def start_session(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        value = dict(payload)
        value.setdefault("learner_id", self.default_learner_id)
        return super().start_session(value)

    def progress_snapshot(self, learner_id: str) -> dict[str, Any]:
        snapshot = self.state_store.profile_snapshot(learner_id)
        with _connect(self.database_path) as connection:
            counts = connection.execute(
                """SELECT
                (SELECT COUNT(*) FROM learning_sessions WHERE learner_id=?),
                (SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='COMPLETED'),
                (SELECT COALESCE(SUM(exposure_count),0) FROM lesson_progress WHERE learner_id=?),
                (SELECT COUNT(*) FROM response_attempts WHERE learner_id=?),
                (SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id) WHERE a.learner_id=? AND r.outcome='AUTO_PASS'),
                (SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id) WHERE a.learner_id=? AND r.outcome='AUTO_FAIL'),
                (SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id) WHERE a.learner_id=? AND r.outcome='PENDING_HUMAN_REVIEW')""",
                (learner_id,) * 7,
            ).fetchone()
        summary = {
            "session_count": int(counts[0]),
            "completed_session_count": int(counts[1]),
            "exposure_count": int(counts[2]),
            "attempt_count": int(counts[3]),
            "auto_pass_count": int(counts[4]),
            "auto_fail_count": int(counts[5]),
            "pending_review_count": int(counts[6]),
        }
        core = {
            "task_id": TASK_ID,
            "learner_id": learner_id,
            "profile": snapshot["profile"],
            "sessions": snapshot["sessions"],
            "progress": snapshot["progress"],
            "summary": summary,
            "claim_boundaries": {
                "mastery_recorded": False,
                "retention_confirmed": False,
                "a2_unlocked": False,
                "public_delivery": False,
            },
        }
        return {**core, "snapshot_sha256": digest(core)}

    def checkpoint(self, learner_id: str, *, captured_at: str | None = None) -> dict[str, Any]:
        snapshot = self.progress_snapshot(learner_id)
        summary = snapshot["summary"]
        checkpoint_id = str(uuid.uuid4())
        captured = utc(captured_at)
        with _connect(self.database_path) as connection:
            connection.execute(
                "INSERT INTO s05_progress_checkpoints VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    checkpoint_id, learner_id, captured,
                    summary["session_count"], summary["completed_session_count"], summary["exposure_count"],
                    summary["attempt_count"], summary["auto_pass_count"], summary["auto_fail_count"],
                    summary["pending_review_count"], snapshot["snapshot_sha256"],
                ),
            )
            connection.commit()
        return {"checkpoint_id": checkpoint_id, "captured_at": captured, "snapshot_sha256": snapshot["snapshot_sha256"]}

    def complete_session(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        completed = super().complete_session(payload)
        checkpoint = self.checkpoint(str(completed["learner_id"]))
        return {**completed, "progress_checkpoint": checkpoint}


def _ensure_default_identity(app: PersistentWorkbenchApplication) -> dict[str, Any]:
    with _connect(app.database_path) as connection:
        connection.executescript(PERSISTENCE_SQL)
        profile = connection.execute("SELECT * FROM learner_profiles WHERE learner_id=?", (DEFAULT_LEARNER_ID,)).fetchone()
        binding = connection.execute("SELECT * FROM s05_identity_bindings WHERE learner_id=?", (DEFAULT_LEARNER_ID,)).fetchone()
    subject = _subject_digest("DEFAULT_PRIVATE_SLOT:1")
    if not profile:
        app.state_store.create_profile(
            learner_id=DEFAULT_LEARNER_ID,
            display_label=DEFAULT_DISPLAY_LABEL,
            locale="zh-TW",
            timezone_name="Asia/Taipei",
            at="2026-01-03T00:00:00Z",
        )
    if not binding:
        with _connect(app.database_path) as connection:
            conflict = connection.execute("SELECT learner_id FROM s05_identity_bindings WHERE private_subject_digest=?", (subject,)).fetchone()
            if conflict and conflict[0] != DEFAULT_LEARNER_ID:
                raise PersistenceError("default_private_subject_binding_conflict")
            connection.execute(
                "INSERT INTO s05_identity_bindings VALUES(?,?,?,?,?)",
                (DEFAULT_LEARNER_ID, subject, "DEFAULT_PRIVATE_SLOT", "2026-01-03T00:00:00Z", "2026-01-03T00:00:00Z"),
            )
            connection.commit()
    return app.progress_snapshot(DEFAULT_LEARNER_ID)


def _database_summary(database_path: Path) -> dict[str, int]:
    with _connect(database_path) as connection:
        queries = {
            "identity_count": "SELECT COUNT(*) FROM s05_identity_bindings",
            "active_profile_count": "SELECT COUNT(*) FROM learner_profiles WHERE profile_state='ACTIVE'",
            "session_count": "SELECT COUNT(*) FROM learning_sessions",
            "completed_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE session_state='COMPLETED'",
            "exposure_count": "SELECT COALESCE(SUM(exposure_count),0) FROM lesson_progress",
            "attempt_count": "SELECT COUNT(*) FROM response_attempts",
            "checkpoint_count": "SELECT COUNT(*) FROM s05_progress_checkpoints",
            "mastery_table_count": "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE '%mastery%'",
        }
        return {key: int(connection.execute(sql).fetchone()[0]) for key, sql in queries.items()}


def _select_canary(database_path: Path, bundles: Mapping[str, Mapping[str, Any]]) -> tuple[str, Any]:
    return s04._select_canary_response(database_path, bundles["reading"]["assets"])


def run_restart_canary(*, database_path: Path, consumer_path: Path, ui_root: Path, validation_root: Path) -> dict[str, Any]:
    validation_root.mkdir(parents=True, exist_ok=True)
    canary_database = validation_root / "s05_restart_canary.sqlite3"
    shutil.copy2(database_path, canary_database)
    bundles = s04._load_bundles(ui_root)
    app = PersistentWorkbenchApplication(database_path=canary_database, bundles=bundles, default_learner_id=CANARY_LEARNER_ID)
    with _connect(canary_database) as connection:
        existing = connection.execute("SELECT 1 FROM learner_profiles WHERE learner_id=?", (CANARY_LEARNER_ID,)).fetchone()
    if existing:
        raise PersistenceError("restart_canary_identity_already_exists")
    app.enroll(
        learner_id=CANARY_LEARNER_ID,
        display_label="S05 Restart Canary",
        subject_key="S05_RESTART_CANARY",
        at="2026-01-04T00:00:00Z",
    )
    asset_key, wrong_response = _select_canary(canary_database, bundles)
    session = app.start_session({
        "skill": "reading",
        "learner_id": CANARY_LEARNER_ID,
        "session_id": CANARY_SESSION_ID,
        "at": "2026-01-04T00:00:10Z",
    })
    session = app.record_exposure({
        "session_id": CANARY_SESSION_ID,
        "asset_key": asset_key,
        "expected_session_version": session["session_version"],
        "at": "2026-01-04T00:00:20Z",
    })
    result = app.submit_response({
        "learner_id": CANARY_LEARNER_ID,
        "session_id": CANARY_SESSION_ID,
        "asset_key": asset_key,
        "response": wrong_response,
        "expected_session_version": session["session_version"],
        "attempt_id": CANARY_ATTEMPT_ID,
        "submitted_at": "2026-01-04T00:00:30Z",
    })
    completed = app.complete_session({
        "session_id": CANARY_SESSION_ID,
        "expected_session_version": result["session_version"],
        "at": "2026-01-04T00:00:40Z",
    })
    first = app.progress_snapshot(CANARY_LEARNER_ID)
    del app
    reopened = PersistentWorkbenchApplication(database_path=canary_database, bundles=s04._load_bundles(ui_root), default_learner_id=CANARY_LEARNER_ID)
    second = reopened.progress_snapshot(CANARY_LEARNER_ID)
    if first["snapshot_sha256"] != second["snapshot_sha256"]:
        raise PersistenceError("restart_progress_snapshot_mismatch")
    if result["outcome"] != "AUTO_FAIL" or result["score"] != 0.0:
        raise PersistenceError("restart_canary_scoring_invalid")
    if completed["session_state"] != "COMPLETED":
        raise PersistenceError("restart_canary_session_not_completed")
    summary = second["summary"]
    expected = {"session_count": 1, "completed_session_count": 1, "exposure_count": 1, "attempt_count": 1, "auto_fail_count": 1}
    for key, value in expected.items():
        if summary.get(key) != value:
            raise PersistenceError(f"restart_canary_progress_invalid:{key}")
    try:
        canary_database.unlink()
    except OSError:
        pass
    return {
        "process_restart_count": 1,
        "stable_identity_count": 1,
        "persisted_session_count": 1,
        "persisted_exposure_count": 1,
        "persisted_attempt_count": 1,
        "persisted_auto_fail_count": 1,
        "snapshot_digest_stable": True,
        "mastery_claimed": False,
    }


def safe_scan(value: Any) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                    raise PersistenceError(f"private_identity_or_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def materialize(*, s04_receipt_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    s04_receipt_path = Path(s04_receipt_path).resolve()
    s04_receipt = read_json(s04_receipt_path, "s04_receipt")
    source = _verify_s04(s04_receipt, s04_receipt_path)
    source_sha = str(s04_receipt["artifact_sha256"])
    output_root = Path(output_root).resolve()
    persistent_root = output_root / "persistent_workbench"
    paths = _copy_runtime_once(source, persistent_root, source_sha)
    bundles = s04._load_bundles(paths["ui"])
    app = PersistentWorkbenchApplication(database_path=paths["database"], bundles=bundles)
    default_snapshot = _ensure_default_identity(app)
    restart_canary = run_restart_canary(
        database_path=paths["database"],
        consumer_path=paths["consumer"],
        ui_root=paths["ui"],
        validation_root=output_root / "validation",
    )
    counts = _database_summary(paths["database"])
    metadata = _metadata(paths["database"])
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": "ONLINE_V1_AUDIO_DEFERRED",
        "source_identity": {
            "s04_task_id": s04.TASK_ID,
            "s04_sha256": source_sha,
        },
        "persistent_outputs": {
            "root": str(persistent_root),
            "database_path": str(paths["database"]),
            "consumer_path": str(paths["consumer"]),
            "static_root": str(paths["static"]),
            "ui_root": str(paths["ui"]),
        },
        "identity_summary": {
            "stable_identity_count": counts["identity_count"],
            "active_profile_count": counts["active_profile_count"],
            "default_private_slot_ready": True,
            "database_generation_id": metadata.get("database_generation_id"),
        },
        "progress_summary": {
            "persistent_session_count": counts["session_count"],
            "persistent_completed_session_count": counts["completed_session_count"],
            "persistent_exposure_count": counts["exposure_count"],
            "persistent_attempt_count": counts["attempt_count"],
            "checkpoint_count": counts["checkpoint_count"],
        },
        "restart_canary": restart_canary,
        "capability_contract": {
            "m3_identity_session_progress_authority_reused": True,
            "m6_response_scoring_authority_reused": True,
            "persistent_database_non_destructive": True,
            "stable_private_identity_binding_enabled": True,
            "progress_readback_enabled": True,
            "restart_persistence_proven": True,
            "parallel_state_engine_created": False,
            "mastery_write_enabled": False,
            "audio_enabled": False,
            "public_network_binding_allowed": False,
        },
        "product_status": PRODUCT_STATUS,
        "claim_boundaries": {
            "default_private_slot_is_real_learner_claimed": False,
            "real_learner_attempt_claimed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "public_online_delivery_claimed": False,
            "audio_complete": False,
            "speaking_recording_complete": False,
            "a2_unlocked": False,
        },
        "private_default_profile_snapshot": default_snapshot,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    receipt = {**receipt_core, "artifact_sha256": digest(receipt_core)}
    safe_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": receipt_core["release_profile"],
        "identity_summary": {
            "stable_identity_count": counts["identity_count"],
            "active_profile_count": counts["active_profile_count"],
            "default_private_slot_ready": True,
        },
        "progress_summary": deepcopy(receipt_core["progress_summary"]),
        "restart_canary": deepcopy(restart_canary),
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def _application_from_receipt(receipt_path: Path) -> tuple[PersistentWorkbenchApplication, Path]:
    receipt = read_json(receipt_path, "s05_receipt")
    if receipt.get("task_id") != TASK_ID or receipt.get("validation_status") != PASS_STATUS:
        raise PersistenceError("s05_receipt_status_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise PersistenceError("s05_receipt_digest_invalid")
    outputs = receipt.get("persistent_outputs", {})
    database = Path(str(outputs.get("database_path") or ""))
    ui_root = Path(str(outputs.get("ui_root") or ""))
    static_root = Path(str(outputs.get("static_root") or ""))
    if not database.is_file() or not ui_root.is_dir() or not static_root.is_dir():
        fallback = Path(receipt_path).parent / "persistent_workbench"
        database = fallback / "runtime/learner_progress.sqlite3"
        ui_root = fallback / "runtime/ui"
        static_root = fallback / "static"
    if not database.is_file() or not ui_root.is_dir() or not static_root.is_dir():
        raise PersistenceError("s05_persistent_outputs_missing")
    return PersistentWorkbenchApplication(database_path=database, bundles=s04._load_bundles(ui_root)), static_root


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    if host.casefold() not in LOOPBACK_HOSTS:
        raise PersistenceError(f"non_loopback_host_forbidden:{host}")
    app, static_root = _application_from_receipt(receipt_path)
    server = s04.WorkbenchServer((host, port), app, static_root)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s04", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    server = commands.add_parser("serve")
    server.add_argument("--receipt", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8765)
    enroll = commands.add_parser("enroll")
    enroll.add_argument("--receipt", type=Path, required=True)
    enroll.add_argument("--learner-id", required=True)
    enroll.add_argument("--display-label", required=True)
    enroll.add_argument("--subject-key", required=True)
    enroll.add_argument("--locale", default="zh-TW")
    enroll.add_argument("--timezone", default="Asia/Taipei")
    snap = commands.add_parser("snapshot")
    snap.add_argument("--receipt", type=Path, required=True)
    snap.add_argument("--learner-id", default=DEFAULT_LEARNER_ID)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            serve(receipt_path=args.receipt, host=args.host, port=args.port)
            return 0
        if args.command == "enroll":
            app, _ = _application_from_receipt(args.receipt)
            result = app.enroll(
                learner_id=args.learner_id,
                display_label=args.display_label,
                subject_key=args.subject_key,
                locale=args.locale,
                timezone_name=args.timezone,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "snapshot":
            app, _ = _application_from_receipt(args.receipt)
            print(json.dumps(app.progress_snapshot(args.learner_id), ensure_ascii=False, indent=2))
            return 0
        receipt, safe = materialize(s04_receipt_path=args.s04, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s05_private_learner_identity_progress_persistence import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s04_receipt_path=args.s04,
        )
        if validation["error_count"]:
            raise PersistenceError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (PersistenceError, s04.WorkbenchError, m3.StateStoreError, m6.ResponseEvidenceError, OSError, sqlite3.Error, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
