#!/usr/bin/env python3
"""Append-only evidence validity governance for the A1FS M6→M7→M8 chain."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

TASK_ID = "A1FS-V1-R1_EvidenceValidityAndSystemErrorGovernance"
SCHEMA_VERSION = "a1fs.v1.r1.evidence_validity_governance.v1"
STATUS = "PASS_A1FS_V1_R1_EVIDENCE_VALIDITY_SYSTEM_ERROR_GOVERNANCE"
M6_STATUS = "PASS_A1FS_V1_M6_RESPONSE_CAPTURE_SCORING_M12_EVIDENCE_READY"
NEXT_SHORT_STEP = "A1FS-V1-R2_CompleteBreadthOntologyAndDeploymentContract"
VALID = "VALID"
PENDING = "PENDING_VALIDITY_REVIEW"
INVALID_STATUSES = {
    "INVALIDATED_SYSTEM_ERROR",
    "INVALIDATED_CONTENT_ERROR",
    "INVALIDATED_DUPLICATE_SUBMISSION",
}
VALIDITY_STATUSES = {VALID, PENDING, *INVALID_STATUSES}
TERMINAL_STATUSES = set(INVALID_STATUSES)
DERIVED_TABLES = (
    "review_events", "review_schedules", "retention_states", "retention_snapshots",
    "m8_metadata", "error_diagnoses", "reassessment_queue", "remediation_assignments",
    "mastery_snapshots", "m7_metadata",
)
SQL = """
CREATE TABLE IF NOT EXISTS evidence_validity_events(
 event_seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT NOT NULL UNIQUE,
 attempt_id TEXT NOT NULL REFERENCES response_attempts(attempt_id),previous_status TEXT NOT NULL,
 new_status TEXT NOT NULL,reason_code TEXT NOT NULL,detail_json TEXT NOT NULL,
 actor_id TEXT NOT NULL,occurred_at TEXT NOT NULL,source_attempt_hash TEXT NOT NULL,
 previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS evidence_validity(
 attempt_id TEXT PRIMARY KEY REFERENCES response_attempts(attempt_id),validity_status TEXT NOT NULL,
 latest_event_id TEXT REFERENCES evidence_validity_events(event_id),reason_code TEXT NOT NULL,
 detail_json TEXT NOT NULL,actor_id TEXT NOT NULL,updated_at TEXT NOT NULL,
 source_attempt_hash TEXT NOT NULL);
"""


class EvidenceGovernanceError(ValueError):
    """Fail-closed evidence governance error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc(value: str | None = None) -> str:
    value = value or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceGovernanceError("timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise EvidenceGovernanceError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _open(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(Path(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def _require_source(connection: sqlite3.Connection) -> None:
    metadata = dict(connection.execute("SELECT key,value FROM metadata"))
    if metadata.get("m6_validation_status") != M6_STATUS:
        raise EvidenceGovernanceError("m6_database_status_invalid")
    names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = {"response_attempts", "scoring_results", "human_review_queue"} - names
    if missing:
        raise EvidenceGovernanceError("source_tables_missing:" + ",".join(sorted(missing)))
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise EvidenceGovernanceError("source_database_integrity_failed")
    if connection.execute("PRAGMA foreign_key_check").fetchall():
        raise EvidenceGovernanceError("source_database_foreign_key_failed")


def initialize(database_path: Path, *, initialized_at: str | None = None) -> dict[str, Any]:
    at = utc(initialized_at)
    with _open(database_path) as connection:
        _require_source(connection)
        connection.executescript(SQL)
        attempts = connection.execute("SELECT attempt_id,attempt_hash FROM response_attempts ORDER BY rowid").fetchall()
        connection.executemany(
            """INSERT OR IGNORE INTO evidence_validity
            (attempt_id,validity_status,latest_event_id,reason_code,detail_json,actor_id,updated_at,source_attempt_hash)
            VALUES(?,?,?,?,?,?,?,?)""",
            [(row["attempt_id"], VALID, None, "CAPTURED_AS_VALID", "{}", "SYSTEM", at, row["attempt_hash"]) for row in attempts],
        )
        count = connection.execute("SELECT COUNT(*) FROM evidence_validity").fetchone()[0]
        if count != len(attempts):
            raise EvidenceGovernanceError("validity_projection_attempt_count_mismatch")
        metadata = {
            "r1_task_id": TASK_ID, "r1_schema_version": SCHEMA_VERSION,
            "r1_validation_status": STATUS, "r1_raw_attempt_rewrite_enabled": "false",
            "r1_invalid_evidence_mastery_eligible": "false", "r1_next_short_step": NEXT_SHORT_STEP,
        }
        connection.executemany("INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)", metadata.items())
        connection.commit()
    return {"validation_status": STATUS, "attempt_count": count, "raw_attempt_rewrite_enabled": False, "next_short_step": NEXT_SHORT_STEP}


def set_validity(
    database_path: Path, *, attempt_id: str, new_status: str, reason_code: str,
    actor_id: str, detail: Mapping[str, Any] | None = None,
    occurred_at: str | None = None, event_id: str | None = None,
) -> dict[str, Any]:
    if new_status not in VALIDITY_STATUSES - {VALID}:
        raise EvidenceGovernanceError("new_validity_status_invalid")
    reason_code, actor_id = str(reason_code).strip(), str(actor_id).strip()
    if not reason_code:
        raise EvidenceGovernanceError("reason_code_required")
    if not actor_id:
        raise EvidenceGovernanceError("actor_id_required")
    at, detail_value = utc(occurred_at), dict(detail or {})
    event_id = event_id or f"R1_VALIDITY:{uuid.uuid4()}"
    with _open(database_path) as connection:
        _require_source(connection)
        connection.executescript(SQL)
        attempt = connection.execute("SELECT attempt_hash FROM response_attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
        if not attempt:
            raise EvidenceGovernanceError("attempt_not_found")
        current = connection.execute("SELECT * FROM evidence_validity WHERE attempt_id=?", (attempt_id,)).fetchone()
        if not current:
            raise EvidenceGovernanceError("evidence_validity_not_initialized")
        previous_status = current["validity_status"]
        if previous_status in TERMINAL_STATUSES:
            raise EvidenceGovernanceError("terminal_validity_status_cannot_change")
        if previous_status == PENDING and new_status == PENDING:
            raise EvidenceGovernanceError("duplicate_pending_validity_transition")
        if attempt["attempt_hash"] != current["source_attempt_hash"]:
            raise EvidenceGovernanceError("source_attempt_hash_drift")
        prior = connection.execute("SELECT event_hash FROM evidence_validity_events ORDER BY event_seq DESC LIMIT 1").fetchone()
        previous_hash = prior[0] if prior else "0" * 64
        core = {
            "event_id": event_id, "attempt_id": attempt_id, "previous_status": previous_status,
            "new_status": new_status, "reason_code": reason_code, "detail": detail_value,
            "actor_id": actor_id, "occurred_at": at, "source_attempt_hash": attempt["attempt_hash"],
        }
        event_hash = digest(previous_hash + canonical(core))
        connection.execute(
            """INSERT INTO evidence_validity_events
            (event_id,attempt_id,previous_status,new_status,reason_code,detail_json,actor_id,
             occurred_at,source_attempt_hash,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (event_id, attempt_id, previous_status, new_status, reason_code, canonical(detail_value),
             actor_id, at, attempt["attempt_hash"], previous_hash, event_hash),
        )
        connection.execute(
            """UPDATE evidence_validity SET validity_status=?,latest_event_id=?,reason_code=?,detail_json=?,
            actor_id=?,updated_at=?,source_attempt_hash=? WHERE attempt_id=?""",
            (new_status, event_id, reason_code, canonical(detail_value), actor_id, at, attempt["attempt_hash"], attempt_id),
        )
        connection.commit()
    return {
        "validation_status": STATUS, "attempt_id": attempt_id, "previous_status": previous_status,
        "new_status": new_status, "event_id": event_id, "event_hash": event_hash,
        "mastery_eligible": False, "next_short_step": NEXT_SHORT_STEP,
    }


def _drop_derived(connection: sqlite3.Connection) -> None:
    for name in DERIVED_TABLES:
        connection.execute(f'DROP TABLE IF EXISTS "{name}"')


def _rebuild_attempt_chain(connection: sqlite3.Connection) -> None:
    previous_hash = "0" * 64
    for row in connection.execute("SELECT rowid,* FROM response_attempts ORDER BY rowid").fetchall():
        core = {
            "attempt_id": row["attempt_id"], "learner_id": row["learner_id"],
            "session_id": row["session_id"], "lesson_id": row["lesson_id"],
            "asset_key": row["asset_key"], "attempt_sequence": row["attempt_sequence"],
            "response": json.loads(row["response_json"]), "submitted_at": row["submitted_at"],
        }
        attempt_hash = digest(previous_hash + canonical(core))
        connection.execute("UPDATE response_attempts SET previous_hash=?,attempt_hash=? WHERE attempt_id=?", (previous_hash, attempt_hash, row["attempt_id"]))
        previous_hash = attempt_hash


def build_governed_overlay(
    database_path: Path, governed_database_path: Path, report_path: Path,
    *, built_at: str | None = None,
) -> dict[str, Any]:
    at = utc(built_at)
    initialize(database_path, initialized_at=at)
    source_path, governed_path, report_path = Path(database_path), Path(governed_database_path), Path(report_path)
    if governed_path.resolve() == source_path.resolve():
        raise EvidenceGovernanceError("governed_database_must_not_replace_source")
    governed_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = governed_path.with_suffix(governed_path.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    with _open(source_path) as source:
        _require_source(source)
        rows = source.execute(
            """SELECT v.attempt_id,v.validity_status,v.reason_code,v.detail_json,v.actor_id,
            v.updated_at,v.source_attempt_hash,a.attempt_hash FROM evidence_validity v
            JOIN response_attempts a USING(attempt_id) ORDER BY a.rowid"""
        ).fetchall()
        if any(row["source_attempt_hash"] != row["attempt_hash"] for row in rows):
            raise EvidenceGovernanceError("source_attempt_hash_drift")
        source_ids = [row["attempt_id"] for row in rows]
        effective_ids = [row["attempt_id"] for row in rows if row["validity_status"] == VALID]
        excluded = [row for row in rows if row["validity_status"] != VALID]
        with sqlite3.connect(temporary) as target:
            source.backup(target)
    with _open(temporary) as governed:
        _drop_derived(governed)
        governed.execute("DROP TABLE IF EXISTS evidence_validity")
        governed.execute("DROP TABLE IF EXISTS evidence_validity_events")
        for attempt_id in [row["attempt_id"] for row in excluded]:
            governed.execute("DELETE FROM human_review_queue WHERE attempt_id=?", (attempt_id,))
            governed.execute("DELETE FROM scoring_results WHERE attempt_id=?", (attempt_id,))
            governed.execute("DELETE FROM response_attempts WHERE attempt_id=?", (attempt_id,))
        governed.execute("DELETE FROM evidence_exports")
        _rebuild_attempt_chain(governed)
        metadata = {
            "r1_task_id": TASK_ID, "r1_schema_version": SCHEMA_VERSION,
            "r1_validation_status": STATUS, "r1_governed_overlay": "true",
            "r1_source_attempt_count": str(len(source_ids)),
            "r1_effective_attempt_count": str(len(effective_ids)),
            "r1_excluded_attempt_count": str(len(excluded)), "r1_next_short_step": NEXT_SHORT_STEP,
        }
        governed.executemany("INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)", metadata.items())
        if governed.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise EvidenceGovernanceError("governed_database_integrity_failed")
        if governed.execute("PRAGMA foreign_key_check").fetchall():
            raise EvidenceGovernanceError("governed_database_foreign_key_failed")
        governed.commit()
    os.replace(temporary, governed_path)
    try:
        os.chmod(governed_path, 0o600)
    except OSError:
        pass
    status_counts = {status: 0 for status in sorted(VALIDITY_STATUSES)}
    for row in rows:
        status_counts[row["validity_status"]] += 1
    report_core = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": STATUS,
        "private_local_only": True, "built_at": at,
        "source_database_sha256": file_digest(source_path),
        "governed_database_sha256": file_digest(governed_path),
        "source_attempt_count": len(source_ids), "effective_attempt_count": len(effective_ids),
        "excluded_attempt_count": len(excluded), "status_counts": status_counts,
        "source_attempt_ids_sha256": digest(source_ids),
        "effective_attempt_ids_sha256": digest(effective_ids),
        "excluded_attempts": [{
            "attempt_id": row["attempt_id"], "validity_status": row["validity_status"],
            "reason_code": row["reason_code"], "detail": json.loads(row["detail_json"]),
            "actor_id": row["actor_id"], "updated_at": row["updated_at"],
            "source_attempt_hash": row["source_attempt_hash"],
        } for row in excluded],
        "claim_boundaries": {
            "raw_attempts_rewritten": False, "scoring_outcomes_rewritten": False,
            "mastery_policy_relaxed": False, "canonical_graph_modified": False,
            "a2_unlocked": False, "qwen_required": False, "audio_population_required": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    report = {**report_core, "report_sha256": digest(report_core)}
    temporary_report = report_path.with_suffix(report_path.suffix + ".tmp")
    temporary_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary_report, report_path)
    try:
        os.chmod(report_path, 0o600)
    except OSError:
        pass
    return {
        "validation_status": STATUS, "governed_database_path": str(governed_path),
        "report_path": str(report_path), "source_attempt_count": len(source_ids),
        "effective_attempt_count": len(effective_ids), "excluded_attempt_count": len(excluded),
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init"); init.add_argument("--database", type=Path, required=True)
    change = commands.add_parser("set-validity")
    change.add_argument("--database", type=Path, required=True); change.add_argument("--attempt-id", required=True)
    change.add_argument("--status", required=True); change.add_argument("--reason-code", required=True)
    change.add_argument("--actor-id", required=True); change.add_argument("--detail-json", default="{}")
    overlay = commands.add_parser("build-overlay")
    overlay.add_argument("--database", type=Path, required=True)
    overlay.add_argument("--governed-database", type=Path, required=True); overlay.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "init":
        result = initialize(args.database)
    elif args.command == "set-validity":
        result = set_validity(args.database, attempt_id=args.attempt_id, new_status=args.status,
                              reason_code=args.reason_code, actor_id=args.actor_id,
                              detail=json.loads(args.detail_json))
    else:
        result = build_governed_overlay(args.database, args.governed_database, args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
