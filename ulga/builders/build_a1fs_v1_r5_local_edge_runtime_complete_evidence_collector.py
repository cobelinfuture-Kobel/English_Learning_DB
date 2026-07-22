#!/usr/bin/env python3
"""Private local edge runtime and complete objective evidence collector for A1FS V1.

Task: A1FS-V1-R5_LocalEdgeRuntimeAndCompleteEvidenceCollector

The runtime extends an existing M3 learner-profile SQLite database, consumes only
R4-admitted items, reuses the M6 deterministic scorer, and writes hash-chained
breadth events. It does not implement mastery, remediation, GPT analysis, Qwen,
public delivery, or A2 access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import sys
import uuid
import webbrowser
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_r1_evidence_validity_system_error_governance as r1
from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4
from ulga.builders import build_a1fs_v1_shared_learner_stimulus_contract_renderer as stimulus

TASK_ID = "A1FS-V1-R5_LocalEdgeRuntimeAndCompleteEvidenceCollector"
SCHEMA_VERSION = "a1fs.v1.r5.local_edge_runtime.sqlite.v1"
PACKAGE_SCHEMA_VERSION = "a1fs.v1.r5.edge_evidence_package.v1"
SAFE_SCHEMA_VERSION = "a1fs.v1.r5.edge_evidence_safe_summary.v1"
STATUS = "PASS_A1FS_V1_R5_LOCAL_EDGE_RUNTIME_COMPLETE_EVIDENCE_COLLECTOR"
M3_STATUS = "PASS_A1FS_V1_M3_LEARNER_PROFILE_SESSION_STATE_STORAGE_READY"
NEXT_SHORT_STEP = "A1FS-V1-R6_GPTDiagnosticPackageAndControlledRecommendationGate"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Captures local runtime attempts and scoring evidence only; does not produce canonical or four-skill content."
ASSIGNABLE_CELL_STATUS = "READY_FOR_LOCAL_SELECTION"
SESSION_STATES = {"ACTIVE", "PAUSED", "COMPLETED", "ABANDONED"}
ASSIGNMENT_STATES = {"ASSIGNED", "SUBMITTED", "SKIPPED"}
RESOLVED_OUTCOMES = {"AUTO_PASS", "AUTO_FAIL", "HUMAN_APPROVE", "HUMAN_REJECT"}
UNRESOLVED_OUTCOMES = {"PENDING_HUMAN_REVIEW", "HUMAN_DEFER"}
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
FAIL_OUTCOMES = {"AUTO_FAIL", "HUMAN_REJECT"}
VALIDITY_STATES = r1.VALIDITY_STATUSES
INVALID_VALIDITY_STATES = r1.INVALID_STATUSES | {r1.PENDING}
REVIEW_CRITERIA = {"grammar_target_match", "meaning_matches_context", "complete_response"}
LOOPBACK_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
STIMULUS_CAPTURE_STATUSES = {"CAPTURED", "LEGACY_UNAVAILABLE"}
TELEMETRY_CAPTURE_STATUSES = {
    "CAPTURED_RUNTIME",
    "CAPTURED_RUNTIME_PRE_STIMULUS_REFERENCE",
    "NOT_CAPTURED_LEGACY_ZERO_FILLED",
}

SCORING_CONTRACT_SQL = """
CREATE TABLE IF NOT EXISTS edge_scoring_contract_snapshots(
 scoring_contract_digest TEXT PRIMARY KEY,item_id TEXT NOT NULL REFERENCES edge_runtime_items(item_id),
 contract_json TEXT NOT NULL,contract_version TEXT NOT NULL,created_at TEXT NOT NULL,
 source_type TEXT NOT NULL,remediation_sha256 TEXT);
CREATE TABLE IF NOT EXISTS edge_runtime_scoring_contract_overrides(
 item_id TEXT PRIMARY KEY REFERENCES edge_runtime_items(item_id),base_contract_digest TEXT NOT NULL,
 effective_contract_digest TEXT NOT NULL REFERENCES edge_scoring_contract_snapshots(scoring_contract_digest),
 override_contract_json TEXT NOT NULL,override_version TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN('ACTIVE','RETIRED')),applied_at TEXT NOT NULL,
 remediation_sha256 TEXT NOT NULL);
"""

SQL = """
CREATE TABLE IF NOT EXISTS r5_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS edge_runtime_items(
 item_id TEXT PRIMARY KEY,breadth_cell_id TEXT NOT NULL,capability_id TEXT NOT NULL,
 life_task_id TEXT NOT NULL,domain TEXT NOT NULL,level TEXT NOT NULL CHECK(level IN('A1','A1_PLUS')),
 skill TEXT NOT NULL,purpose TEXT NOT NULL,stimulus_fingerprint TEXT NOT NULL,
 template_family TEXT NOT NULL,item_json TEXT NOT NULL,item_digest TEXT NOT NULL UNIQUE,
 admission_status TEXT NOT NULL CHECK(admission_status='APPROVED'),media_payload_state TEXT NOT NULL);
""" + SCORING_CONTRACT_SQL + """
CREATE TABLE IF NOT EXISTS edge_cell_supply(
 breadth_cell_id TEXT PRIMARY KEY,supply_status TEXT NOT NULL,max_recent_reuse INTEGER,
 approved_item_ids_json TEXT NOT NULL,required_skills_json TEXT NOT NULL,source_report_digest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS edge_sessions(
 session_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL REFERENCES learner_profiles(learner_id),
 breadth_cell_id TEXT NOT NULL REFERENCES edge_cell_supply(breadth_cell_id),purpose TEXT NOT NULL,
 session_state TEXT NOT NULL CHECK(session_state IN('ACTIVE','PAUSED','COMPLETED','ABANDONED')),
 session_version INTEGER NOT NULL CHECK(session_version>=1),planned_item_count INTEGER NOT NULL CHECK(planned_item_count>=1),
 access_token_hash TEXT NOT NULL,started_at TEXT NOT NULL,updated_at TEXT NOT NULL,ended_at TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_edge_session_per_learner
 ON edge_sessions(learner_id) WHERE session_state IN('ACTIVE','PAUSED');
CREATE TABLE IF NOT EXISTS edge_assignments(
 session_id TEXT NOT NULL REFERENCES edge_sessions(session_id),item_id TEXT NOT NULL REFERENCES edge_runtime_items(item_id),
 assignment_sequence INTEGER NOT NULL CHECK(assignment_sequence>=1),assignment_state TEXT NOT NULL CHECK(assignment_state IN('ASSIGNED','SUBMITTED','SKIPPED')),
 assigned_at TEXT NOT NULL,submitted_at TEXT,PRIMARY KEY(session_id,item_id),UNIQUE(session_id,assignment_sequence));
CREATE TABLE IF NOT EXISTS edge_attempts(
 attempt_id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES edge_sessions(session_id),
 learner_id TEXT NOT NULL REFERENCES learner_profiles(learner_id),item_id TEXT NOT NULL REFERENCES edge_runtime_items(item_id),
 response_json TEXT NOT NULL,response_time_ms INTEGER NOT NULL CHECK(response_time_ms>=0),
 hint_count INTEGER NOT NULL CHECK(hint_count>=0),revision_count INTEGER NOT NULL CHECK(revision_count>=0),
 submitted_at TEXT NOT NULL,validity_status TEXT NOT NULL,previous_hash TEXT NOT NULL,attempt_hash TEXT NOT NULL UNIQUE,
 UNIQUE(session_id,item_id));
CREATE TABLE IF NOT EXISTS edge_scoring_results(
 attempt_id TEXT PRIMARY KEY REFERENCES edge_attempts(attempt_id),scoring_mode TEXT NOT NULL,
 outcome TEXT NOT NULL,score REAL,human_review_required INTEGER NOT NULL CHECK(human_review_required IN(0,1)),
 scored_at TEXT NOT NULL,scoring_contract_digest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS edge_review_queue(
 attempt_id TEXT PRIMARY KEY REFERENCES edge_attempts(attempt_id),decision TEXT NOT NULL,
 reviewer_id TEXT,reviewed_at TEXT,criteria_json TEXT NOT NULL,notes TEXT);
CREATE TABLE IF NOT EXISTS edge_validity_events(
 event_seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT NOT NULL UNIQUE,
 attempt_id TEXT NOT NULL REFERENCES edge_attempts(attempt_id),previous_status TEXT NOT NULL,
 new_status TEXT NOT NULL,reason_code TEXT NOT NULL,detail_json TEXT NOT NULL,actor_id TEXT NOT NULL,
 occurred_at TEXT NOT NULL,previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS edge_runtime_events(
 event_seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT NOT NULL UNIQUE,
 learner_id TEXT NOT NULL,session_id TEXT,event_type TEXT NOT NULL,event_at TEXT NOT NULL,
 payload_json TEXT NOT NULL,previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS edge_exports(
 export_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL,exported_at TEXT NOT NULL,
 package_digest TEXT NOT NULL,safe_summary_digest TEXT NOT NULL,jsonl_digest TEXT NOT NULL);
"""


class LocalEdgeRuntimeError(ValueError):
    """Fail-closed local edge runtime error."""


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
        raise LocalEdgeRuntimeError("timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise LocalEdgeRuntimeError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def store_scoring_contract_snapshot(
    connection: sqlite3.Connection, *, item_id: str, contract: Mapping[str, Any],
    contract_version: str, created_at: str, source_type: str,
    remediation_sha256: str | None = None,
) -> str:
    """Store one immutable contract body per digest; repeated bodies are shared safely."""
    contract_body = dict(contract)
    contract_digest = digest(contract_body)
    existing = connection.execute(
        "SELECT contract_json FROM edge_scoring_contract_snapshots WHERE scoring_contract_digest=?",
        (contract_digest,),
    ).fetchone()
    if existing:
        try:
            existing_body = json.loads(existing["contract_json"])
        except (json.JSONDecodeError, TypeError) as exc:
            raise LocalEdgeRuntimeError("scoring_snapshot_json_invalid") from exc
        if existing_body != contract_body or digest(existing_body) != contract_digest:
            raise LocalEdgeRuntimeError("scoring_snapshot_digest_mismatch")
        return contract_digest
    connection.execute(
        """INSERT INTO edge_scoring_contract_snapshots
        (scoring_contract_digest,item_id,contract_json,contract_version,created_at,source_type,remediation_sha256)
        VALUES(?,?,?,?,?,?,?)""",
        (
            contract_digest, item_id, canonical(contract_body), str(contract_version), utc(created_at),
            str(source_type), remediation_sha256,
        ),
    )
    return contract_digest


def historical_scoring_contract(connection: sqlite3.Connection, contract_digest: str) -> dict[str, Any]:
    """Load an immutable historical contract, failing closed on absence or corruption."""
    row = connection.execute(
        "SELECT contract_json FROM edge_scoring_contract_snapshots WHERE scoring_contract_digest=?",
        (contract_digest,),
    ).fetchone()
    if not row:
        raise LocalEdgeRuntimeError(f"scoring_snapshot_missing:{contract_digest}")
    try:
        contract = json.loads(row["contract_json"])
    except (json.JSONDecodeError, TypeError) as exc:
        raise LocalEdgeRuntimeError(f"scoring_snapshot_json_invalid:{contract_digest}") from exc
    if not isinstance(contract, dict) or digest(contract) != contract_digest:
        raise LocalEdgeRuntimeError(f"scoring_snapshot_digest_mismatch:{contract_digest}")
    return contract


def effective_scoring_contract(
    connection: sqlite3.Connection, *, item_id: str, item: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    """Resolve a future-only override without permitting base-contract drift."""
    base = item.get("private_scoring_contract")
    if not isinstance(base, Mapping):
        raise LocalEdgeRuntimeError(f"private_scoring_contract_missing:{item_id}")
    base_contract = dict(base)
    base_digest = digest(base_contract)
    try:
        row = connection.execute(
            """SELECT * FROM edge_runtime_scoring_contract_overrides
            WHERE item_id=? AND status='ACTIVE'""",
            (item_id,),
        ).fetchone()
    except sqlite3.OperationalError as exc:
        raise LocalEdgeRuntimeError("scoring_contract_registry_not_migrated") from exc
    if not row:
        return base_contract, base_digest
    if row["base_contract_digest"] != base_digest:
        raise LocalEdgeRuntimeError(f"scoring_override_base_digest_mismatch:{item_id}")
    try:
        override = json.loads(row["override_contract_json"])
    except (json.JSONDecodeError, TypeError) as exc:
        raise LocalEdgeRuntimeError(f"scoring_override_json_invalid:{item_id}") from exc
    effective_digest = digest(override)
    if effective_digest != row["effective_contract_digest"] or effective_digest == base_digest:
        raise LocalEdgeRuntimeError(f"scoring_override_effective_digest_invalid:{item_id}")
    snapshot = historical_scoring_contract(connection, effective_digest)
    if snapshot != override:
        raise LocalEdgeRuntimeError(f"scoring_override_snapshot_mismatch:{item_id}")
    return override, effective_digest


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalEdgeRuntimeError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise LocalEdgeRuntimeError(f"{code}_not_object")
    return value


def write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _token() -> str:
    return secrets.token_urlsafe(32)


def _safe_item(item: Mapping[str, Any]) -> dict[str, Any]:
    learner = item.get("learner_contract")
    scoring = item.get("private_scoring_contract")
    if not isinstance(learner, Mapping) or not isinstance(scoring, Mapping):
        raise LocalEdgeRuntimeError(f"source_item_contract_missing:{item.get('item_id')}")
    try:
        validated_learner = stimulus.ensure_learner_contract(
  item_id=str(item.get("item_id") or ""),
  task_type=str(item.get("task_type") or ""),
  learner=learner,
  scoring=scoring,
  media_payload_state=str(item.get("media_payload_state") or "NOT_REQUIRED"),
        )
    except stimulus.StimulusContractError as exc:
        raise LocalEdgeRuntimeError(
  f"SESSION_ITEM_NOT_ANSWERABLE:{item.get('item_id')}:{exc}"
        ) from exc
    return {
        "item_id": item["item_id"],
        "breadth_cell_id": item["breadth_cell_id"],
        "capability_id": item["capability_id"],
        "life_task_id": item["life_task_id"],
        "domain": item["domain"],
        "level": item["level"],
        "skill": item["skill"],
        "purpose": item["purpose"],
        "task_type": item["task_type"],
        "support_level": item["support_level"],
        "initiative_level": item["initiative_level"],
        "interaction_variation": item["interaction_variation"],
        "transfer_distance": item["transfer_distance"],
        "template_family": item["template_family"],
        "stimulus_fingerprint": item["stimulus_fingerprint"],
        "media_payload_state": item["media_payload_state"],
        "learner_contract": validated_learner,
    }



def legacy_rendered_stimulus_reference() -> dict[str, Any]:
    core = {
        "capture_status": "LEGACY_UNAVAILABLE",
        "reason_code": "RUNTIME_EVENT_PREDATES_STIMULUS_REFERENCE_CAPTURE",
    }
    return {**core, "reference_sha256": digest(core)}


def rendered_stimulus_reference(item: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_item(item)
    learner = safe["learner_contract"]
    core = {
        "capture_status": "CAPTURED",
        "item_id": str(item.get("item_id") or ""),
        "item_digest": digest(item),
        "learner_contract_sha256": digest(learner),
        "prompt_sha256": digest(str(learner.get("prompt") or "")),
        "stimulus_render_manifest_sha256": str(
            learner.get("stimulus_render_manifest_sha256") or digest([])
        ),
        "response_mode": str(learner.get("response_mode") or ""),
    }
    if not core["item_id"] or not core["response_mode"]:
        raise LocalEdgeRuntimeError("rendered_stimulus_reference_identity_missing")
    return {**core, "reference_sha256": digest(core)}


def validate_rendered_stimulus_reference(
    reference: Mapping[str, Any], *, item: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(reference, Mapping):
        raise LocalEdgeRuntimeError("rendered_stimulus_reference_not_object")
    value = dict(reference)
    status = value.get("capture_status")
    if status not in STIMULUS_CAPTURE_STATUSES:
        raise LocalEdgeRuntimeError("rendered_stimulus_reference_status_invalid")
    core = {key: child for key, child in value.items() if key != "reference_sha256"}
    if value.get("reference_sha256") != digest(core):
        raise LocalEdgeRuntimeError("rendered_stimulus_reference_digest_invalid")
    if status == "LEGACY_UNAVAILABLE":
        if set(value) != {"capture_status", "reason_code", "reference_sha256"}:
            raise LocalEdgeRuntimeError("legacy_rendered_stimulus_reference_shape_invalid")
        return value
    required = {
        "capture_status", "item_id", "item_digest", "learner_contract_sha256",
        "prompt_sha256", "stimulus_render_manifest_sha256", "response_mode",
        "reference_sha256",
    }
    if set(value) != required:
        raise LocalEdgeRuntimeError("rendered_stimulus_reference_shape_invalid")
    if item is not None:
        safe = _safe_item(item)
        learner = safe["learner_contract"]
        expected = {
            "item_id": str(item.get("item_id") or ""),
            "item_digest": digest(item),
            "learner_contract_sha256": digest(learner),
            "prompt_sha256": digest(str(learner.get("prompt") or "")),
            "stimulus_render_manifest_sha256": str(
                learner.get("stimulus_render_manifest_sha256") or digest([])
            ),
            "response_mode": str(learner.get("response_mode") or ""),
        }
        for key, child in expected.items():
            if value.get(key) != child:
                raise LocalEdgeRuntimeError(
                    f"rendered_stimulus_reference_item_binding_invalid:{key}"
                )
    return value


class LocalEdgeRuntime:
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection, *, learner_id: str, session_id: str | None,
        event_type: str, event_at: str, payload: Mapping[str, Any], event_id: str | None = None,
    ) -> str:
        event_id = event_id or f"R5_EVENT:{uuid.uuid4()}"
        prior = connection.execute("SELECT event_hash FROM edge_runtime_events ORDER BY event_seq DESC LIMIT 1").fetchone()
        previous_hash = prior[0] if prior else "0" * 64
        core = {
            "event_id": event_id, "learner_id": learner_id, "session_id": session_id,
            "event_type": event_type, "event_at": event_at, "payload": dict(payload),
        }
        event_hash = digest(previous_hash + canonical(core))
        connection.execute(
            "INSERT INTO edge_runtime_events(event_id,learner_id,session_id,event_type,event_at,payload_json,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?,?)",
            (event_id, learner_id, session_id, event_type, event_at, canonical(dict(payload)), previous_hash, event_hash),
        )
        return event_id

    def initialize(
        self, *, bank_path: Path, supply_report_path: Path,
        allow_bank_rebind: bool = False,
    ) -> dict[str, Any]:
        bank = read_json(bank_path, "bank")
        report = read_json(supply_report_path, "supply_report")
        if bank.get("task_id") != r4.TASK_ID or bank.get("schema_version") != r4.BANK_SCHEMA_VERSION:
            raise LocalEdgeRuntimeError("bank_identity_invalid")
        if bank.get("validation_status") != r4.STATUS or bank.get("private_local_only") is not True:
            raise LocalEdgeRuntimeError("bank_status_or_privacy_invalid")
        bank_core = {key: value for key, value in bank.items() if key != "bank_sha256"}
        if bank.get("bank_sha256") != r4.digest(bank_core):
            raise LocalEdgeRuntimeError("bank_digest_invalid")
        report_core = {key: value for key, value in report.items() if key != "report_sha256"}
        if report.get("task_id") != r4.TASK_ID or report.get("schema_version") != r4.SCHEMA_VERSION:
            raise LocalEdgeRuntimeError("supply_report_identity_invalid")
        if report.get("report_sha256") != r4.digest(report_core):
            raise LocalEdgeRuntimeError("supply_report_digest_invalid")
        if bank.get("source_bindings") != report.get("source_bindings"):
            raise LocalEdgeRuntimeError("bank_report_binding_mismatch")
        items = bank.get("items")
        if not isinstance(items, list) or bank.get("item_count") != len(items):
            raise LocalEdgeRuntimeError("bank_item_denominator_invalid")
        cell_rows = report.get("cell_supply")
        if not isinstance(cell_rows, list):
            raise LocalEdgeRuntimeError("cell_supply_invalid")
        with self.write() as connection:
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            if metadata.get("validation_status") != M3_STATUS:
                raise LocalEdgeRuntimeError("m3_database_status_invalid")
            connection.executescript(SQL)
            existing_bank = dict(connection.execute("SELECT key,value FROM r5_metadata")).get("source_bank_sha256")
            bank_rebound = bool(existing_bank and existing_bank != bank["bank_sha256"])
            if bank_rebound:
                if not allow_bank_rebind:
                    raise LocalEdgeRuntimeError("runtime_bank_binding_mismatch")
                open_sessions = connection.execute(
                    "SELECT COUNT(*) FROM edge_sessions WHERE session_state IN('ACTIVE','PAUSED')"
                ).fetchone()[0]
                if open_sessions:
                    raise LocalEdgeRuntimeError("runtime_bank_rebind_open_session")
                self._append_event(
                    connection, learner_id="SYSTEM", session_id=None,
                    event_type="EDGE_RUNTIME_BANK_REBOUND", event_at=utc(),
                    payload={
                        "previous_bank_sha256": existing_bank,
                        "new_bank_sha256": bank["bank_sha256"],
                        "new_supply_report_sha256": report["report_sha256"],
                    },
                )
            for item in items:
                if item.get("admission", {}).get("status") != "APPROVED":
                    raise LocalEdgeRuntimeError(f"unapproved_bank_item:{item.get('item_id')}")
                item = dict(item)
                item["learner_contract"] = _safe_item(item)["learner_contract"]
                item_digest = digest(item)
                connection.execute(
                    """INSERT INTO edge_runtime_items
                    (item_id,breadth_cell_id,capability_id,life_task_id,domain,level,skill,purpose,
                     stimulus_fingerprint,template_family,item_json,item_digest,admission_status,media_payload_state)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(item_id) DO UPDATE SET item_json=excluded.item_json,item_digest=excluded.item_digest""",
                    (
                        item["item_id"], item["breadth_cell_id"], item["capability_id"], item["life_task_id"],
                        item["domain"], item["level"], item["skill"], item["purpose"],
                        item["stimulus_fingerprint"], item["template_family"], canonical(item), item_digest,
                        "APPROVED", item["media_payload_state"],
                    ),
                )
            for cell in cell_rows:
                cell_id = str(cell.get("breadth_cell_id") or "")
                if not cell_id:
                    raise LocalEdgeRuntimeError("cell_supply_identity_missing")
                connection.execute(
                    """INSERT OR REPLACE INTO edge_cell_supply
                    (breadth_cell_id,supply_status,max_recent_reuse,approved_item_ids_json,
                     required_skills_json,source_report_digest) VALUES(?,?,?,?,?,?)""",
                    (
                        cell_id, cell["supply_status"], cell.get("max_recent_reuse"),
                        canonical(cell.get("approved_item_ids", [])),
                        canonical(cell.get("skill_projection", {}).get("required", [])),
                        report["report_sha256"],
                    ),
                )
            values = {
                "task_id": TASK_ID, "schema_version": SCHEMA_VERSION,
                "validation_status": STATUS, "source_bank_sha256": bank["bank_sha256"],
                "source_supply_report_sha256": report["report_sha256"],
                "qwen_required": "false", "network_submission_enabled": "false",
                "mastery_write_enabled": "false", "a2_session_enabled": "false",
                "next_short_step": NEXT_SHORT_STEP,
            }
            connection.executemany("INSERT OR REPLACE INTO r5_metadata(key,value) VALUES(?,?)", values.items())
        return {
            "validation_status": STATUS,
            "item_count": len(items),
            "assignable_cell_count": sum(row.get("supply_status") == ASSIGNABLE_CELL_STATUS for row in cell_rows),
            "source_bank_sha256": bank["bank_sha256"],
            "source_supply_report_sha256": report["report_sha256"],
            "bank_rebound": bank_rebound,
            "qwen_required": False,
            "next_short_step": NEXT_SHORT_STEP,
        }

    def _profile(self, connection: sqlite3.Connection, learner_id: str) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM learner_profiles WHERE learner_id=?", (learner_id,)).fetchone()
        if not row or row["profile_state"] != "ACTIVE":
            raise LocalEdgeRuntimeError("learner_profile_not_active")
        return row

    def start_session(
        self, *, learner_id: str, breadth_cell_id: str, purpose: str,
        planned_item_count: int, session_id: str | None = None,
        started_at: str | None = None,
    ) -> dict[str, Any]:
        if purpose not in r4.PURPOSES:
            raise LocalEdgeRuntimeError("purpose_invalid")
        if planned_item_count < 1:
            raise LocalEdgeRuntimeError("planned_item_count_invalid")
        session_id = session_id or f"R5_SESSION:{uuid.uuid4()}"
        at, access_token = utc(started_at), _token()
        with self.write() as connection:
            self._profile(connection, learner_id)
            if connection.execute(
                "SELECT 1 FROM edge_sessions WHERE learner_id=? AND session_state IN('ACTIVE','PAUSED')",
                (learner_id,),
            ).fetchone():
                raise LocalEdgeRuntimeError("open_edge_session_exists")
            cell = connection.execute("SELECT * FROM edge_cell_supply WHERE breadth_cell_id=?", (breadth_cell_id,)).fetchone()
            if not cell:
                raise LocalEdgeRuntimeError("breadth_cell_not_found")
            if cell["supply_status"] != ASSIGNABLE_CELL_STATUS:
                raise LocalEdgeRuntimeError(f"breadth_cell_not_assignable:{cell['supply_status']}")
            approved_ids = set(json.loads(cell["approved_item_ids_json"]))
            items = connection.execute(
                "SELECT * FROM edge_runtime_items WHERE breadth_cell_id=? AND purpose=? ORDER BY item_id",
                (breadth_cell_id, purpose),
            ).fetchall()
            items = [row for row in items if row["item_id"] in approved_ids]
            if len(items) < planned_item_count:
                raise LocalEdgeRuntimeError(
                    f"CONTENT_CAPACITY_INSUFFICIENT:required={planned_item_count}:available={len(items)}"
                )
            recent_window = max(planned_item_count - 1, 1)
            recent = connection.execute(
                """SELECT a.item_id FROM edge_assignments a JOIN edge_sessions s USING(session_id)
                WHERE s.learner_id=? AND s.breadth_cell_id=? ORDER BY a.assigned_at DESC,a.assignment_sequence DESC LIMIT ?""",
                (learner_id, breadth_cell_id, recent_window),
            ).fetchall()
            recent_counts = Counter(row[0] for row in recent)
            max_recent_reuse = int(cell["max_recent_reuse"] if cell["max_recent_reuse"] is not None else 0)
            usage = {
                row["item_id"]: connection.execute(
                    """SELECT COUNT(*),MAX(a.assigned_at) FROM edge_assignments a
                    JOIN edge_sessions s USING(session_id) WHERE s.learner_id=? AND a.item_id=?""",
                    (learner_id, row["item_id"]),
                ).fetchone()
                for row in items
            }
            eligible = [row for row in items if recent_counts[row["item_id"]] <= max_recent_reuse]
            eligible.sort(key=lambda row: (usage[row["item_id"]][0], usage[row["item_id"]][1] or "", row["item_id"]))
            if len(eligible) < planned_item_count:
                raise LocalEdgeRuntimeError(
                    f"CONTENT_CAPACITY_INSUFFICIENT_RECENT_REUSE:required={planned_item_count}:eligible={len(eligible)}"
                )
            selected = eligible[:planned_item_count]
            connection.execute(
                "INSERT INTO edge_sessions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    session_id, learner_id, breadth_cell_id, purpose, "ACTIVE", 1,
                    planned_item_count, digest(access_token), at, at, None,
                ),
            )
            for index, item in enumerate(selected, start=1):
                connection.execute(
                    "INSERT INTO edge_assignments VALUES(?,?,?,?,?,?)",
                    (session_id, item["item_id"], index, "ASSIGNED", at, None),
                )
            self._append_event(
                connection, learner_id=learner_id, session_id=session_id,
                event_type="EDGE_SESSION_STARTED", event_at=at,
                payload={
                    "breadth_cell_id": breadth_cell_id, "purpose": purpose,
                    "planned_item_count": planned_item_count,
                    "item_ids": [row["item_id"] for row in selected],
                },
            )
        result = self.session_payload(session_id=session_id, access_token=access_token)
        result["access_token"] = access_token
        return result

    def _session(self, connection: sqlite3.Connection, session_id: str) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM edge_sessions WHERE session_id=?", (session_id,)).fetchone()
        if not row:
            raise LocalEdgeRuntimeError("edge_session_not_found")
        return row

    @staticmethod
    def _auth(session: sqlite3.Row, access_token: str) -> None:
        if digest(access_token) != session["access_token_hash"]:
            raise LocalEdgeRuntimeError("edge_session_access_denied")

    def session_payload(self, *, session_id: str, access_token: str) -> dict[str, Any]:
        with self.connect() as connection:
            session = self._session(connection, session_id)
            self._auth(session, access_token)
            rows = connection.execute(
                """SELECT a.*,i.item_json FROM edge_assignments a JOIN edge_runtime_items i USING(item_id)
                WHERE a.session_id=? ORDER BY a.assignment_sequence""",
                (session_id,),
            ).fetchall()
            assignments = []
            for row in rows:
                item = json.loads(row["item_json"])
                assignments.append({
                    "assignment_sequence": row["assignment_sequence"],
                    "assignment_state": row["assignment_state"],
                    "item": _safe_item(item),
                })
            return {
                "validation_status": STATUS,
                "session": {
                    "session_id": session["session_id"], "learner_id": session["learner_id"],
                    "breadth_cell_id": session["breadth_cell_id"], "purpose": session["purpose"],
                    "session_state": session["session_state"], "session_version": session["session_version"],
                    "planned_item_count": session["planned_item_count"],
                    "started_at": session["started_at"], "updated_at": session["updated_at"],
                },
                "assignments": assignments,
                "next_short_step": NEXT_SHORT_STEP,
            }

    def submit_response(
        self, *, session_id: str, access_token: str, item_id: str, response: Any,
        response_time_ms: int, hint_count: int, revision_count: int,
        expected_session_version: int, attempt_id: str | None = None,
        submitted_at: str | None = None,
    ) -> dict[str, Any]:
        if min(response_time_ms, hint_count, revision_count) < 0:
            raise LocalEdgeRuntimeError("objective_metric_negative")
        attempt_id, at = attempt_id or f"R5_ATTEMPT:{uuid.uuid4()}", utc(submitted_at)
        with self.write() as connection:
            session = self._session(connection, session_id)
            self._auth(session, access_token)
            if session["session_state"] != "ACTIVE":
                raise LocalEdgeRuntimeError("edge_session_not_active")
            if session["session_version"] != expected_session_version:
                raise LocalEdgeRuntimeError("edge_session_version_conflict")
            assignment = connection.execute(
                "SELECT * FROM edge_assignments WHERE session_id=? AND item_id=?",
                (session_id, item_id),
            ).fetchone()
            if not assignment or assignment["assignment_state"] != "ASSIGNED":
                raise LocalEdgeRuntimeError("item_not_assignable_in_session")
            item_row = connection.execute("SELECT item_json,item_digest FROM edge_runtime_items WHERE item_id=?", (item_id,)).fetchone()
            item = json.loads(item_row["item_json"])
            scoring, scoring_digest = effective_scoring_contract(
                connection, item_id=item_id, item=item,
            )
            stored_digest = store_scoring_contract_snapshot(
                connection, item_id=item_id, contract=scoring,
                contract_version="RUNTIME_EFFECTIVE_V1", created_at=at,
                source_type="RUNTIME_SUBMISSION",
            )
            if stored_digest != scoring_digest:
                raise LocalEdgeRuntimeError(f"scoring_snapshot_write_mismatch:{item_id}")
            stimulus_ref = rendered_stimulus_reference(item)
            outcome, score = m6.ResponseEvidenceStore.score(scoring, response)
            prior = connection.execute("SELECT attempt_hash FROM edge_attempts ORDER BY rowid DESC LIMIT 1").fetchone()
            previous_hash = prior[0] if prior else "0" * 64
            core = {
                "attempt_id": attempt_id, "session_id": session_id, "learner_id": session["learner_id"],
                "item_id": item_id, "response": response, "response_time_ms": response_time_ms,
                "hint_count": hint_count, "revision_count": revision_count, "submitted_at": at,
            }
            attempt_hash = digest(previous_hash + canonical(core))
            connection.execute(
                "INSERT INTO edge_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    attempt_id, session_id, session["learner_id"], item_id, canonical(response),
                    response_time_ms, hint_count, revision_count, at, r1.VALID, previous_hash, attempt_hash,
                ),
            )
            connection.execute(
                "INSERT INTO edge_scoring_results VALUES(?,?,?,?,?,?,?)",
                (
                    attempt_id, scoring["scoring_mode"], outcome, score,
                    int(outcome == "PENDING_HUMAN_REVIEW"), at, scoring_digest,
                ),
            )
            criteria = {key: None for key in sorted(REVIEW_CRITERIA)}
            connection.execute(
                "INSERT INTO edge_review_queue VALUES(?,?,?,?,?,?)",
                (attempt_id, "PENDING", None, None, canonical(criteria), None),
            )
            connection.execute(
                "UPDATE edge_assignments SET assignment_state='SUBMITTED',submitted_at=? WHERE session_id=? AND item_id=?",
                (at, session_id, item_id),
            )
            connection.execute(
                "UPDATE edge_sessions SET session_version=session_version+1,updated_at=? WHERE session_id=?",
                (at, session_id),
            )
            self._append_event(
                connection, learner_id=session["learner_id"], session_id=session_id,
                event_type="EDGE_RESPONSE_CAPTURED", event_at=at,
                payload={
                    "attempt_id": attempt_id, "item_id": item_id, "breadth_cell_id": item["breadth_cell_id"],
                    "capability_id": item["capability_id"], "life_task_id": item["life_task_id"],
                    "domain": item["domain"], "skill": item["skill"],
                    "support_level": item["support_level"], "initiative_level": item["initiative_level"],
                    "interaction_variation": item["interaction_variation"],
                    "transfer_distance": item["transfer_distance"], "purpose": item["purpose"],
                    "response_sha256": digest(response), "response_time_ms": response_time_ms,
                    "hint_count": hint_count, "revision_count": revision_count,
                    "learner_rendered_stimulus_reference": stimulus_ref,
                    "telemetry_status": "CAPTURED_RUNTIME",
                    "outcome": outcome, "score": score, "validity_status": r1.VALID,
                },
            )
        return {
            "attempt_id": attempt_id, "outcome": outcome, "score": score,
            "human_review_required": outcome == "PENDING_HUMAN_REVIEW",
            "session_version": expected_session_version + 1,
            "mastery_claimed": False,
        }

    def review_response(
        self, *, attempt_id: str, decision: str, reviewer_id: str,
        criteria: Mapping[str, Any], notes: str | None = None,
        reviewed_at: str | None = None,
    ) -> dict[str, Any]:
        if decision not in m6.REVIEW_DECISIONS:
            raise LocalEdgeRuntimeError("review_decision_invalid")
        if not str(reviewer_id).strip():
            raise LocalEdgeRuntimeError("reviewer_id_required")
        if set(criteria) != REVIEW_CRITERIA or any(criteria[key] not in {True, False} for key in REVIEW_CRITERIA):
            raise LocalEdgeRuntimeError("review_criteria_invalid")
        if decision == "APPROVE" and not all(criteria.values()):
            raise LocalEdgeRuntimeError("approved_review_criteria_not_all_true")
        at = utc(reviewed_at)
        with self.write() as connection:
            row = connection.execute(
                """SELECT s.scoring_mode,a.learner_id,a.session_id FROM edge_scoring_results s
                JOIN edge_attempts a USING(attempt_id) WHERE attempt_id=?""",
                (attempt_id,),
            ).fetchone()
            if not row:
                raise LocalEdgeRuntimeError("attempt_not_found")
            if row["scoring_mode"] != "FEATURE_RUBRIC":
                raise LocalEdgeRuntimeError("deterministic_item_review_override_forbidden")
            outcome = {"APPROVE": "HUMAN_APPROVE", "REJECT": "HUMAN_REJECT", "DEFER": "HUMAN_DEFER"}[decision]
            score = 1.0 if decision == "APPROVE" else 0.0 if decision == "REJECT" else None
            connection.execute(
                "UPDATE edge_review_queue SET decision=?,reviewer_id=?,reviewed_at=?,criteria_json=?,notes=? WHERE attempt_id=?",
                (decision, reviewer_id, at, canonical(dict(criteria)), notes, attempt_id),
            )
            connection.execute(
                "UPDATE edge_scoring_results SET outcome=?,score=?,human_review_required=0,scored_at=? WHERE attempt_id=?",
                (outcome, score, at, attempt_id),
            )
            self._append_event(
                connection, learner_id=row["learner_id"], session_id=row["session_id"],
                event_type="EDGE_RESPONSE_REVIEWED", event_at=at,
                payload={"attempt_id": attempt_id, "decision": decision, "outcome": outcome, "score": score},
            )
        return {"attempt_id": attempt_id, "outcome": outcome, "score": score, "mastery_claimed": False}

    def set_attempt_validity(
        self, *, attempt_id: str, new_status: str, reason_code: str, actor_id: str,
        detail: Mapping[str, Any] | None = None, occurred_at: str | None = None,
    ) -> dict[str, Any]:
        if new_status not in VALIDITY_STATES - {r1.VALID}:
            raise LocalEdgeRuntimeError("validity_status_invalid")
        if not str(reason_code).strip() or not str(actor_id).strip():
            raise LocalEdgeRuntimeError("validity_reason_or_actor_missing")
        at, detail_value = utc(occurred_at), dict(detail or {})
        with self.write() as connection:
            attempt = connection.execute("SELECT * FROM edge_attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
            if not attempt:
                raise LocalEdgeRuntimeError("attempt_not_found")
            previous_status = attempt["validity_status"]
            if previous_status in r1.TERMINAL_STATUSES:
                raise LocalEdgeRuntimeError("terminal_validity_status_cannot_change")
            if previous_status == r1.PENDING and new_status == r1.PENDING:
                raise LocalEdgeRuntimeError("duplicate_pending_validity_transition")
            prior = connection.execute("SELECT event_hash FROM edge_validity_events ORDER BY event_seq DESC LIMIT 1").fetchone()
            previous_hash = prior[0] if prior else "0" * 64
            event_id = f"R5_VALIDITY:{uuid.uuid4()}"
            core = {
                "event_id": event_id, "attempt_id": attempt_id, "previous_status": previous_status,
                "new_status": new_status, "reason_code": reason_code, "detail": detail_value,
                "actor_id": actor_id, "occurred_at": at,
            }
            event_hash = digest(previous_hash + canonical(core))
            connection.execute(
                "INSERT INTO edge_validity_events VALUES(NULL,?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id, attempt_id, previous_status, new_status, reason_code,
                    canonical(detail_value), actor_id, at, previous_hash, event_hash,
                ),
            )
            connection.execute("UPDATE edge_attempts SET validity_status=? WHERE attempt_id=?", (new_status, attempt_id))
            self._append_event(
                connection, learner_id=attempt["learner_id"], session_id=attempt["session_id"],
                event_type="EDGE_EVIDENCE_VALIDITY_CHANGED", event_at=at,
                payload={
                    "attempt_id": attempt_id, "previous_status": previous_status,
                    "new_status": new_status, "reason_code": reason_code,
                },
            )
        return {
            "attempt_id": attempt_id, "previous_status": previous_status,
            "new_status": new_status, "mastery_eligible": new_status == r1.VALID,
        }

    def _transition(
        self, *, session_id: str, access_token: str, expected_session_version: int,
        new_state: str, at: str | None = None,
    ) -> dict[str, Any]:
        at = utc(at)
        if new_state not in SESSION_STATES:
            raise LocalEdgeRuntimeError("session_state_invalid")
        with self.write() as connection:
            session = self._session(connection, session_id)
            self._auth(session, access_token)
            if session["session_version"] != expected_session_version:
                raise LocalEdgeRuntimeError("edge_session_version_conflict")
            current = session["session_state"]
            allowed = {
                "ACTIVE": {"PAUSED", "COMPLETED", "ABANDONED"},
                "PAUSED": {"ACTIVE", "ABANDONED"},
                "COMPLETED": set(), "ABANDONED": set(),
            }
            if new_state not in allowed[current]:
                raise LocalEdgeRuntimeError(f"session_transition_invalid:{current}:{new_state}")
            if new_state == "COMPLETED":
                pending = connection.execute(
                    "SELECT COUNT(*) FROM edge_assignments WHERE session_id=? AND assignment_state!='SUBMITTED'",
                    (session_id,),
                ).fetchone()[0]
                unresolved = connection.execute(
                    """SELECT COUNT(*) FROM edge_attempts a JOIN edge_scoring_results s USING(attempt_id)
                    WHERE a.session_id=? AND s.outcome IN('PENDING_HUMAN_REVIEW','HUMAN_DEFER')""",
                    (session_id,),
                ).fetchone()[0]
                if pending:
                    raise LocalEdgeRuntimeError("session_assignments_incomplete")
                if unresolved:
                    raise LocalEdgeRuntimeError("session_reviews_unresolved")
            ended = at if new_state in {"COMPLETED", "ABANDONED"} else None
            connection.execute(
                "UPDATE edge_sessions SET session_state=?,session_version=session_version+1,updated_at=?,ended_at=? WHERE session_id=?",
                (new_state, at, ended, session_id),
            )
            self._append_event(
                connection, learner_id=session["learner_id"], session_id=session_id,
                event_type=f"EDGE_SESSION_{new_state}", event_at=at,
                payload={"previous_state": current, "new_state": new_state},
            )
        if new_state == "ABANDONED":
            return {
                "validation_status": STATUS,
                "session": {
                    "session_id": session_id,
                    "learner_id": session["learner_id"],
                    "breadth_cell_id": session["breadth_cell_id"],
                    "purpose": session["purpose"],
                    "session_state": "ABANDONED",
                    "session_version": expected_session_version + 1,
                    "planned_item_count": session["planned_item_count"],
                    "started_at": session["started_at"],
                    "updated_at": at,
                },
                "assignments": [],
                "next_short_step": NEXT_SHORT_STEP,
            }
        return self.session_payload(session_id=session_id, access_token=access_token)

    def pause_session(self, **kwargs: Any) -> dict[str, Any]:
        return self._transition(new_state="PAUSED", **kwargs)

    def resume_session(self, **kwargs: Any) -> dict[str, Any]:
        return self._transition(new_state="ACTIVE", **kwargs)

    def complete_session(self, **kwargs: Any) -> dict[str, Any]:
        return self._transition(new_state="COMPLETED", **kwargs)

    def abandon_session(self, **kwargs: Any) -> dict[str, Any]:
        return self._transition(new_state="ABANDONED", **kwargs)

    def export_evidence(
        self, *, learner_id: str, output_root: Path, exported_at: str | None = None,
    ) -> dict[str, Any]:
        at, root = utc(exported_at), Path(output_root)
        root.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            self._profile(connection, learner_id)
            rows = connection.execute(
                """SELECT a.*,s.scoring_mode,s.outcome,s.score,s.human_review_required,
                q.decision,q.reviewer_id,q.reviewed_at,q.criteria_json,q.notes,
                i.item_json,se.session_state FROM edge_attempts a
                JOIN edge_scoring_results s USING(attempt_id)
                JOIN edge_review_queue q USING(attempt_id)
                JOIN edge_runtime_items i USING(item_id)
                JOIN edge_sessions se USING(session_id)
                WHERE a.learner_id=? ORDER BY a.submitted_at,a.attempt_id""",
                (learner_id,),
            ).fetchall()
            observability_by_attempt: dict[str, dict[str, Any]] = {}
            for event in connection.execute(
                "SELECT event_type,payload_json FROM edge_runtime_events "
                "WHERE event_type='EDGE_RESPONSE_CAPTURED' ORDER BY event_seq"
            ):
                try:
                    payload = json.loads(event["payload_json"])
                except json.JSONDecodeError as exc:
                    raise LocalEdgeRuntimeError("response_event_payload_invalid") from exc
                attempt_id = str(payload.get("attempt_id") or "")
                if not attempt_id or attempt_id in observability_by_attempt:
                    raise LocalEdgeRuntimeError("response_event_attempt_identity_invalid")
                reference = payload.get("learner_rendered_stimulus_reference")
                telemetry_status = payload.get("telemetry_status")
                if reference is not None:
                    reference = validate_rendered_stimulus_reference(reference)
                    if telemetry_status != "CAPTURED_RUNTIME":
                        raise LocalEdgeRuntimeError("captured_reference_telemetry_status_invalid")
                elif telemetry_status is not None and telemetry_status not in TELEMETRY_CAPTURE_STATUSES:
                    raise LocalEdgeRuntimeError("response_event_telemetry_status_invalid")
                observability_by_attempt[attempt_id] = {
                    "learner_rendered_stimulus_reference": reference,
                    "telemetry_status": telemetry_status,
                }

            entries: list[dict[str, Any]] = []
            for row in rows:
                item = json.loads(row["item_json"])
                observation = observability_by_attempt.get(str(row["attempt_id"]), {})
                stimulus_ref = observation.get("learner_rendered_stimulus_reference")
                telemetry_status = observation.get("telemetry_status")
                if stimulus_ref is None:
                    stimulus_ref = legacy_rendered_stimulus_reference()
                    telemetry_status = "CAPTURED_RUNTIME_PRE_STIMULUS_REFERENCE"
                entries.append({
                    "attempt_id": row["attempt_id"], "session_id": row["session_id"],
                    "item_id": row["item_id"], "breadth_cell_id": item["breadth_cell_id"],
                    "capability_id": item["capability_id"], "life_task_id": item["life_task_id"],
                    "domain": item["domain"], "level": item["level"], "skill": item["skill"],
                    "purpose": item["purpose"], "task_type": item["task_type"],
                    "support_level": item["support_level"], "initiative_level": item["initiative_level"],
                    "interaction_variation": item["interaction_variation"],
                    "transfer_distance": item["transfer_distance"],
                    "template_family": item["template_family"],
                    "stimulus_fingerprint": item["stimulus_fingerprint"],
                    "learner_rendered_stimulus_reference": stimulus_ref,
                    "telemetry_status": telemetry_status,
                    "response": json.loads(row["response_json"]),
                    "response_sha256": digest(json.loads(row["response_json"])),
                    "response_time_ms": row["response_time_ms"], "hint_count": row["hint_count"],
                    "revision_count": row["revision_count"], "submitted_at": row["submitted_at"],
                    "session_state": row["session_state"], "scoring_mode": row["scoring_mode"],
                    "outcome": row["outcome"], "score": row["score"],
                    "human_review_required": bool(row["human_review_required"]),
                    "operator_review": {
                        "decision": row["decision"], "reviewer_id": row["reviewer_id"],
                        "reviewed_at": row["reviewed_at"], "criteria": json.loads(row["criteria_json"]),
                        "notes": row["notes"],
                    },
                    "validity_status": row["validity_status"],
                    "attempt_hash": row["attempt_hash"],
                })
            valid = [row for row in entries if row["validity_status"] == r1.VALID]
            resolved = [row for row in valid if row["outcome"] in RESOLVED_OUTCOMES]
            grouped: dict[str, Counter[str]] = defaultdict(Counter)
            for row in valid:
                grouped[row["breadth_cell_id"]]["attempts"] += 1
                grouped[row["breadth_cell_id"]]["passes"] += int(row["outcome"] in PASS_OUTCOMES)
                grouped[row["breadth_cell_id"]]["failures"] += int(row["outcome"] in FAIL_OUTCOMES)
                grouped[row["breadth_cell_id"]]["unresolved"] += int(row["outcome"] in UNRESOLVED_OUTCOMES)
            objective_summary = {
                cell_id: dict(sorted(counts.items()))
                for cell_id, counts in sorted(grouped.items())
            }
            package_core = {
                "task_id": TASK_ID, "schema_version": PACKAGE_SCHEMA_VERSION,
                "validation_status": STATUS, "private_local_only": True,
                "learner_id": learner_id, "exported_at": at,
                "database_binding_sha256": file_digest(self.database_path),
                "attempt_count": len(entries), "valid_attempt_count": len(valid),
                "resolved_valid_attempt_count": len(resolved),
                "entries": entries, "entries_sha256": digest(entries),
                "objective_summary": objective_summary,
                "claim_boundaries": {
                    "mastery_written": False, "retention_confirmed": False,
                    "gpt_analysis_performed": False, "qwen_used": False,
                    "a2_unlocked": False, "public_delivery": False,
                },
                "next_short_step": NEXT_SHORT_STEP,
            }
            package = {**package_core, "package_sha256": digest(package_core)}
            safe_entries = [{
                key: value for key, value in row.items()
                if key not in {"response", "operator_review"}
            } for row in entries]
            safe_core = {
                "task_id": TASK_ID, "schema_version": SAFE_SCHEMA_VERSION,
                "validation_status": STATUS, "learner_ref_sha256": digest(learner_id),
                "exported_at": at, "attempt_count": len(entries),
                "valid_attempt_count": len(valid), "resolved_valid_attempt_count": len(resolved),
                "outcome_counts": dict(sorted(Counter(row["outcome"] for row in entries).items())),
                "validity_counts": dict(sorted(Counter(row["validity_status"] for row in entries).items())),
                "objective_summary": objective_summary, "entries": safe_entries,
                "entries_sha256": digest(safe_entries),
                "claim_boundaries": package_core["claim_boundaries"],
                "next_short_step": NEXT_SHORT_STEP,
            }
            safe = {**safe_core, "summary_sha256": digest(safe_core)}
        package_path = root / "a1fs_v1_r5_edge_evidence.private.json"
        safe_path = root / "a1fs_v1_r5_edge_evidence.safe.json"
        jsonl_path = root / "a1fs_v1_r5_edge_events.private.jsonl"
        write_private(package_path, package)
        write_private(safe_path, safe)
        jsonl_path.write_text("".join(canonical(row) + "\n" for row in entries), encoding="utf-8")
        try:
            os.chmod(jsonl_path, 0o600)
        except OSError:
            pass
        with self.write() as connection:
            connection.execute(
                "INSERT INTO edge_exports VALUES(?,?,?,?,?,?)",
                (str(uuid.uuid4()), learner_id, at, package["package_sha256"], safe["summary_sha256"], file_digest(jsonl_path)),
            )
        return {
            "validation_status": STATUS,
            "package_path": str(package_path), "safe_summary_path": str(safe_path),
            "jsonl_path": str(jsonl_path), "attempt_count": len(entries),
            "next_short_step": NEXT_SHORT_STEP,
        }

    def backup(self, *, backup_path: Path, manifest_path: Path, created_at: str | None = None) -> dict[str, Any]:
        at = utc(created_at)
        backup_path, manifest_path = Path(backup_path), Path(manifest_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = backup_path.with_suffix(backup_path.suffix + ".tmp")
        temporary.unlink(missing_ok=True)
        source = self.connect()
        target = sqlite3.connect(temporary)
        try:
            source.backup(target)
            target.commit()
        finally:
            target.close()
            source.close()
        check = sqlite3.connect(temporary)
        try:
            if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise LocalEdgeRuntimeError("backup_integrity_failed")
        finally:
            check.close()
        os.replace(temporary, backup_path)
        manifest_core = {
            "task_id": TASK_ID, "schema_version": SCHEMA_VERSION,
            "created_at": at, "backup_sha256": file_digest(backup_path),
            "source_database_sha256": file_digest(self.database_path),
        }
        manifest = {**manifest_core, "manifest_sha256": digest(manifest_core)}
        write_private(manifest_path, manifest)
        return {"backup_path": str(backup_path), "manifest_path": str(manifest_path), **manifest}

    @staticmethod
    def restore(*, backup_path: Path, manifest_path: Path, target_path: Path) -> dict[str, Any]:
        manifest = read_json(manifest_path, "backup_manifest")
        core = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
        if manifest.get("task_id") != TASK_ID or manifest.get("manifest_sha256") != digest(core):
            raise LocalEdgeRuntimeError("backup_manifest_invalid")
        if manifest.get("backup_sha256") != file_digest(backup_path):
            raise LocalEdgeRuntimeError("backup_hash_mismatch")
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = target_path.with_suffix(target_path.suffix + ".tmp")
        shutil.copy2(backup_path, temporary)
        connection = sqlite3.connect(temporary)
        try:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise LocalEdgeRuntimeError("restored_database_integrity_failed")
        finally:
            connection.close()
        os.replace(temporary, target_path)
        return {"validation_status": STATUS, "target_path": str(target_path), "restored_sha256": file_digest(target_path)}


def learner_html() -> str:
    return """<!doctype html><html lang='zh-Hant'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>A1FS Local Edge Learning</title><style>body{font-family:system-ui;max-width:860px;margin:auto;padding:24px}article{border:1px solid #aaa;border-radius:8px;padding:18px}.stimulus{background:#f3f5f7;border-left:4px solid #666;padding:12px;margin:12px 0;white-space:pre-wrap}.stimulus pre{white-space:pre-wrap}.stimulus img{max-width:100%;height:auto}.tokens span{display:inline-block;border:1px solid #777;border-radius:5px;padding:5px 8px;margin:3px}button,input,textarea,select{font:inherit;padding:8px;margin:6px 0}textarea,select{width:100%;box-sizing:border-box}.status{font-weight:700}</style>
    <body><h1>A1/A1+ 本地學習</h1><p class='status' id='status'>Loading…</p><main id='root'></main><script>""" + stimulus.JS_RENDERER + """
    const q=new URLSearchParams(location.search),sid=q.get('session_id'),token=q.get('token');let payload,started;
    async function load(){const r=await fetch('/api/session?session_id='+encodeURIComponent(sid)+'&token='+encodeURIComponent(token));payload=await r.json();render()}
    function render(){const root=document.getElementById('root');root.innerHTML='';document.getElementById('status').textContent=payload.session.session_state+' · '+payload.session.breadth_cell_id;const a=payload.assignments.find(x=>x.assignment_state==='ASSIGNED');if(!a){root.textContent='本次題目已完成。';const b=document.createElement('button');b.textContent='完成課程';b.onclick=complete;root.appendChild(b);return}started=Date.now();const item=a.item,l=item.learner_contract,box=document.createElement('article');const h=document.createElement('h2');h.textContent=l.prompt;box.appendChild(h);renderA1FSStimulus(box,l);let input;if(l.response_mode==='select_one'){input=document.createElement('select');const empty=document.createElement('option');empty.value='';empty.textContent='請選擇';input.appendChild(empty);l.options.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;input.appendChild(o)})}else if(l.response_mode==='ordered_tokens'||l.response_mode==='ordered_morphemes'){input=document.createElement('textarea');input.placeholder='以 | 分隔選取順序';input.dataset.array='1'}else{input=document.createElement('textarea')}box.appendChild(input);const b=document.createElement('button');b.textContent='提交';b.onclick=()=>submit(item.item_id,input);box.appendChild(b);root.appendChild(box)}
    async function submit(item,input){let response=input.value;if(input.dataset.array)response=response.split('|').map(x=>x.trim()).filter(Boolean);const body={session_id:sid,token,item_id:item,response:response,response_time_ms:Date.now()-started,hint_count:0,revision_count:0,expected_session_version:payload.session.session_version};const r=await fetch('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const x=await r.json();if(!r.ok){alert(x.error);return}await load()}
    async function complete(){const r=await fetch('/api/complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sid,token:token,expected_session_version:payload.session.session_version})});const x=await r.json();if(!r.ok){alert(x.error);return}payload=x;render()}
    load();</script></body></html>"""


def serve(runtime: LocalEdgeRuntime, *, session_id: str, access_token: str, port: int = DEFAULT_PORT, open_browser: bool = True) -> None:
    if port < 1024 or port > 65535:
        raise LocalEdgeRuntimeError("port_out_of_range")
    runtime.session_payload(session_id=session_id, access_token=access_token)

    class Handler(BaseHTTPRequestHandler):
        def _json(self, status: int, value: Mapping[str, Any]) -> None:
            data = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                data = learner_html().encode("utf-8")
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
            if parsed.path == "/api/session":
                query = parse_qs(parsed.query)
                try:
                    value = runtime.session_payload(session_id=query.get("session_id", [""])[0], access_token=query.get("token", [""])[0])
                except LocalEdgeRuntimeError as exc:
                    self._json(400, {"error": str(exc)}); return
                self._json(200, value); return
            self._json(404, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            try:
                length = int(self.headers.get("Content-Length", "0")); body = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/api/submit":
                    runtime.submit_response(
                        session_id=body["session_id"], access_token=body["token"], item_id=body["item_id"],
                        response=body["response"], response_time_ms=int(body.get("response_time_ms", 0)),
                        hint_count=int(body.get("hint_count", 0)), revision_count=int(body.get("revision_count", 0)),
                        expected_session_version=int(body["expected_session_version"]),
                    )
                    value = runtime.session_payload(session_id=body["session_id"], access_token=body["token"])
                elif self.path == "/api/complete":
                    value = runtime.complete_session(
                        session_id=body["session_id"], access_token=body["token"],
                        expected_session_version=int(body["expected_session_version"]),
                    )
                else:
                    self._json(404, {"error": "not_found"}); return
            except (KeyError, ValueError, json.JSONDecodeError, LocalEdgeRuntimeError) as exc:
                self._json(400, {"error": str(exc)}); return
            self._json(200, value)

        def log_message(self, format: str, *args: Any) -> None:
            return

    url = f"http://{LOOPBACK_HOST}:{port}/?session_id={session_id}&token={access_token}"
    server = ThreadingHTTPServer((LOOPBACK_HOST, port), Handler)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def write_windows_launcher(*, path: Path, database_path: Path, session_id: str, access_token: str, port: int = DEFAULT_PORT) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve()
    content = "@echo off\r\n" + f'python "{script}" serve --database "{Path(database_path).resolve()}" --session-id "{session_id}" --token "{access_token}" --port {port}\r\n'
    path.write_text(content, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init"); init.add_argument("--database", type=Path, required=True); init.add_argument("--bank", type=Path, required=True); init.add_argument("--report", type=Path, required=True); init.add_argument("--allow-bank-rebind", action="store_true")
    start = commands.add_parser("start"); start.add_argument("--database", type=Path, required=True); start.add_argument("--learner-id", required=True); start.add_argument("--cell-id", required=True); start.add_argument("--purpose", required=True); start.add_argument("--count", type=int, required=True)
    submit = commands.add_parser("submit"); submit.add_argument("--database", type=Path, required=True); submit.add_argument("--session-id", required=True); submit.add_argument("--token", required=True); submit.add_argument("--item-id", required=True); submit.add_argument("--response-json", required=True); submit.add_argument("--response-time-ms", type=int, default=0); submit.add_argument("--hint-count", type=int, default=0); submit.add_argument("--revision-count", type=int, default=0); submit.add_argument("--expected-version", type=int, required=True)
    complete = commands.add_parser("complete"); complete.add_argument("--database", type=Path, required=True); complete.add_argument("--session-id", required=True); complete.add_argument("--token", required=True); complete.add_argument("--expected-version", type=int, required=True)
    export = commands.add_parser("export"); export.add_argument("--database", type=Path, required=True); export.add_argument("--learner-id", required=True); export.add_argument("--output-root", type=Path, required=True)
    serve_cmd = commands.add_parser("serve"); serve_cmd.add_argument("--database", type=Path, required=True); serve_cmd.add_argument("--session-id", required=True); serve_cmd.add_argument("--token", required=True); serve_cmd.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(); runtime = LocalEdgeRuntime(args.database)
    if args.command == "init": result = runtime.initialize(bank_path=args.bank, supply_report_path=args.report, allow_bank_rebind=args.allow_bank_rebind)
    elif args.command == "start": result = runtime.start_session(learner_id=args.learner_id, breadth_cell_id=args.cell_id, purpose=args.purpose, planned_item_count=args.count)
    elif args.command == "submit": result = runtime.submit_response(session_id=args.session_id, access_token=args.token, item_id=args.item_id, response=json.loads(args.response_json), response_time_ms=args.response_time_ms, hint_count=args.hint_count, revision_count=args.revision_count, expected_session_version=args.expected_version)
    elif args.command == "complete": result = runtime.complete_session(session_id=args.session_id, access_token=args.token, expected_session_version=args.expected_version)
    elif args.command == "export": result = runtime.export_evidence(learner_id=args.learner_id, output_root=args.output_root)
    else:
        serve(runtime, session_id=args.session_id, access_token=args.token, port=args.port); return 0
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
