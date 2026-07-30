#!/usr/bin/env python3
"""Connect the Unit01 approved variant pool to the existing M3/M6 runtime.

U01QB02 does not create another planner, learner database, response table, or
scoring engine. M4 continues to select lessons. After an existing Unit01 lesson
session is active, this adapter registers U01QB01 approved items as ordinary
lesson assets and M6 response contracts in the same SQLite database, assembles a
deterministic exposure-aware ten-item session plan, records exposure through M3,
and delegates response capture/scoring to M6.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from ulga.builders import build_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as m01
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as bank,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Consumes the approved Unit01 question bank and existing M3/M6 runtime only; no new learner content, parallel planner, parallel state database, parallel response capture, parallel scoring, audio, A2 content, or Unit02-Unit24 content is produced."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB02_Unit01ApprovedVariantSessionAssemblerAndExposureHistoryRuntimeIntegration"
SCHEMA_VERSION = "a1fs.v1.u01qb02.unit01_approved_variant_session_runtime.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB02_UNIT01_APPROVED_VARIANT_SESSION_RUNTIME"
NEXT_SHORT_STEP = "A1FS-V1-U01QB03_Unit01ApprovedVariantLearnerRendererAndRealAttemptAcceptance"
SESSION_SIZE = 10
RECENT_EXPOSURE_WINDOW = 10
SELECTION_QUOTA = {
    "NEW_OR_UNSEEN": 4,
    "REMEDIATION": 2,
    "SCHEDULED_REVIEW": 2,
    "TRANSFER": 1,
    "GUIDED_EXTENSION": 1,
}
SELECTION_REASONS = frozenset((*SELECTION_QUOTA, "FALLBACK"))
FAIL_OUTCOMES = frozenset({"AUTO_FAIL", "HUMAN_REJECT"})
PASS_OUTCOMES = frozenset({"AUTO_PASS", "HUMAN_APPROVE"})
HEX64 = re.compile(r"^[0-9a-f]{64}$")

UNIT01_LESSONS = dict(m01.LESSON_IDS)
LESSON_TO_SKILL = {lesson_id: skill for skill, lesson_id in UNIT01_LESSONS.items()}

SQL = """
CREATE TABLE IF NOT EXISTS u01qb02_metadata(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS u01qb02_item_catalog(
  item_id TEXT PRIMARY KEY,
  asset_key TEXT NOT NULL UNIQUE REFERENCES lesson_assets(asset_key),
  lesson_id TEXT NOT NULL REFERENCES lesson_catalog(lesson_id),
  skill TEXT NOT NULL CHECK(skill IN ('READING','WRITING','SPEAKING')),
  pattern_family_id TEXT NOT NULL,
  unit_pattern_id TEXT NOT NULL,
  support_level TEXT NOT NULL,
  assessment_eligible INTEGER NOT NULL CHECK(assessment_eligible IN (0,1)),
  transfer_eligible INTEGER NOT NULL CHECK(transfer_eligible IN (0,1)),
  capture_enabled INTEGER NOT NULL CHECK(capture_enabled IN (0,1)),
  private_item_json TEXT NOT NULL,
  item_digest TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS u01qb02_session_plans(
  session_id TEXT PRIMARY KEY REFERENCES learning_sessions(session_id),
  learner_id TEXT NOT NULL REFERENCES learner_profiles(learner_id),
  lesson_id TEXT NOT NULL REFERENCES lesson_catalog(lesson_id),
  skill TEXT NOT NULL CHECK(skill IN ('READING','WRITING','SPEAKING')),
  item_count INTEGER NOT NULL CHECK(item_count = 10),
  selected_at TEXT NOT NULL,
  recent_exposure_window INTEGER NOT NULL CHECK(recent_exposure_window = 10),
  source_bank_sha256 TEXT NOT NULL,
  plan_digest TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS u01qb02_session_items(
  session_id TEXT NOT NULL REFERENCES u01qb02_session_plans(session_id),
  item_position INTEGER NOT NULL CHECK(item_position BETWEEN 1 AND 10),
  item_id TEXT NOT NULL REFERENCES u01qb02_item_catalog(item_id),
  selection_reason TEXT NOT NULL CHECK(selection_reason IN ('NEW_OR_UNSEEN','REMEDIATION','SCHEDULED_REVIEW','TRANSFER','GUIDED_EXTENSION','FALLBACK')),
  PRIMARY KEY(session_id,item_position),
  UNIQUE(session_id,item_id)
);
CREATE TABLE IF NOT EXISTS u01qb02_item_exposures(
  exposure_seq INTEGER PRIMARY KEY AUTOINCREMENT,
  exposure_id TEXT NOT NULL UNIQUE,
  learner_id TEXT NOT NULL REFERENCES learner_profiles(learner_id),
  session_id TEXT NOT NULL REFERENCES learning_sessions(session_id),
  item_id TEXT NOT NULL REFERENCES u01qb02_item_catalog(item_id),
  selection_reason TEXT NOT NULL CHECK(selection_reason IN ('NEW_OR_UNSEEN','REMEDIATION','SCHEDULED_REVIEW','TRANSFER','GUIDED_EXTENSION','FALLBACK')),
  exposure_at TEXT NOT NULL,
  previous_hash TEXT NOT NULL,
  exposure_hash TEXT NOT NULL UNIQUE,
  UNIQUE(session_id,item_id)
);
CREATE INDEX IF NOT EXISTS u01qb02_exposure_learner_order
ON u01qb02_item_exposures(learner_id,exposure_seq DESC);
"""


class SessionRuntimeError(ValueError):
    """Fail-closed U01QB02 runtime integration error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def timestamp(value: str | None = None) -> str:
    value = value or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SessionRuntimeError("timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise SessionRuntimeError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def asset_key(item_id: str) -> str:
    return f"U01QB02:{hashlib.sha256(item_id.encode('utf-8')).hexdigest()[:24]}"


def item_role(item: Mapping[str, Any]) -> str:
    if item.get("transfer_eligible"):
        return "XFR"
    if item.get("skill") == "READING":
        return "CHK"
    return "PRD"


def m6_contract(item: Mapping[str, Any], *, lesson_id: str, key: str) -> dict[str, Any]:
    source = item.get("response_contract")
    if not isinstance(source, Mapping):
        raise SessionRuntimeError(f"response_contract_missing:{item.get('item_id')}")
    mode = str(item.get("scoring_mode") or source.get("scoring_mode") or "")
    speaking = item.get("skill") == "SPEAKING"
    return {
        "asset_key": key,
        "lesson_id": lesson_id,
        "skill": str(item["skill"]),
        "role": item_role(item),
        "prompt": str(item["prompt"]),
        "capture_enabled": bool(source.get("capture_enabled")) and not speaking,
        "response_type": "string_array" if mode == "EXACT_SEQUENCE" else "string",
        "scoring_mode": mode,
        "accepted_texts": list(source.get("accepted_texts", [])),
        "accepted_sequence": list(source.get("accepted_sequence", [])),
        "case_insensitive": True,
        "punctuation_tolerance": True,
        "human_review_fallback": bool(source.get("human_review_fallback")),
        "rubric": dict(source.get("rubric", {})),
        "m12_item_id": str(item["item_id"]),
        "m12_session_bank_sha256": None,
    }


def approved_bank() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidate = bank.build_candidate()
    approved = bank.admit_candidate(candidate)
    from ulga.validators import (
        validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as validator,
    )
    report = validator.validate_approved(candidate, approved)
    if report.get("error_count"):
        raise SessionRuntimeError("u01qb01_approved_bank_invalid:" + "|".join(report["errors"]))
    items = approved.get("payload", {}).get("approved_items")
    if not isinstance(items, list) or len(items) != bank.EXPECTED_APPROVED_COUNT:
        raise SessionRuntimeError("u01qb01_approved_item_count_invalid")
    return approved, [dict(row) for row in items]


class Unit01ApprovedVariantSessionRuntime:
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
    def _require_table(connection: sqlite3.Connection, table: str) -> None:
        if not connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone():
            raise SessionRuntimeError(f"required_table_missing:{table}")

    def initialize(self) -> dict[str, Any]:
        if not self.database_path.is_file():
            raise SessionRuntimeError("learner_database_missing")
        approved, items = approved_bank()
        with self.write() as connection:
            for table in ("metadata", "lesson_catalog", "lesson_assets", "learner_profiles", "learning_sessions"):
                self._require_table(connection, table)
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            if metadata.get("validation_status") != m3.STATUS:
                raise SessionRuntimeError("m3_database_status_invalid")
            lessons = {
                row["lesson_id"]: dict(row)
                for row in connection.execute(
                    "SELECT lesson_id,skill,level,payload_access_allowed FROM lesson_catalog WHERE lesson_id IN (?,?,?)",
                    tuple(UNIT01_LESSONS.values()),
                )
            }
            if set(lessons) != set(UNIT01_LESSONS.values()):
                raise SessionRuntimeError("unit01_lesson_catalog_incomplete")
            for lesson_id, lesson in lessons.items():
                if lesson["skill"] != LESSON_TO_SKILL[lesson_id] or lesson["level"] != "A1" or lesson["payload_access_allowed"] != 1:
                    raise SessionRuntimeError(f"unit01_lesson_contract_invalid:{lesson_id}")
            connection.executescript(m6.SQL)
            connection.executescript(SQL)
            for item in items:
                item_id = str(item["item_id"])
                skill = str(item["skill"])
                lesson_id = UNIT01_LESSONS[skill]
                key = asset_key(item_id)
                private_json = canonical(item)
                item_digest = digest(item)
                role = item_role(item)
                response = m6_contract(item, lesson_id=lesson_id, key=key)
                contract_json = m6.canonical(response)
                contract_digest = m6.sha(response)
                existing_asset = connection.execute(
                    "SELECT asset_id,lesson_id,content_digest FROM lesson_assets WHERE asset_key=?", (key,)
                ).fetchone()
                if existing_asset and (
                    existing_asset["asset_id"] != item_id
                    or existing_asset["lesson_id"] != lesson_id
                    or existing_asset["content_digest"] != item_digest
                ):
                    raise SessionRuntimeError(f"lesson_asset_identity_drift:{item_id}")
                connection.execute(
                    "INSERT OR IGNORE INTO lesson_assets(asset_key,asset_id,lesson_id,role,content_digest) VALUES(?,?,?,?,?)",
                    (key, item_id, lesson_id, role, item_digest),
                )
                existing_contract = connection.execute(
                    "SELECT lesson_id,contract_digest FROM response_contracts WHERE asset_key=?", (key,)
                ).fetchone()
                if existing_contract and (
                    existing_contract["lesson_id"] != lesson_id
                    or existing_contract["contract_digest"] != contract_digest
                ):
                    raise SessionRuntimeError(f"response_contract_identity_drift:{item_id}")
                connection.execute(
                    """INSERT OR IGNORE INTO response_contracts
                    (asset_key,lesson_id,skill,role,contract_json,contract_digest,capture_enabled)
                    VALUES(?,?,?,?,?,?,?)""",
                    (key, lesson_id, skill, role, contract_json, contract_digest, int(response["capture_enabled"])),
                )
                existing_item = connection.execute(
                    "SELECT item_digest FROM u01qb02_item_catalog WHERE item_id=?", (item_id,)
                ).fetchone()
                if existing_item and existing_item["item_digest"] != item_digest:
                    raise SessionRuntimeError(f"item_catalog_identity_drift:{item_id}")
                connection.execute(
                    """INSERT OR IGNORE INTO u01qb02_item_catalog
                    (item_id,asset_key,lesson_id,skill,pattern_family_id,unit_pattern_id,support_level,
                     assessment_eligible,transfer_eligible,capture_enabled,private_item_json,item_digest)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        item_id, key, lesson_id, skill, item["pattern_family_id"], item["unit_pattern_ids"][0],
                        item["support_level"], int(item["assessment_eligible"]), int(item["transfer_eligible"]),
                        int(response["capture_enabled"]), private_json, item_digest,
                    ),
                )
            values = {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": PASS_STATUS,
                "source_bank_artifact_sha256": approved["artifact_sha256"],
                "approved_item_count": str(len(items)),
                "session_size": str(SESSION_SIZE),
                "recent_exposure_window": str(RECENT_EXPOSURE_WINDOW),
                "m4_remains_lesson_planner": "true",
                "m3_exposure_authority_reused": "true",
                "m6_attempt_scoring_authority_reused": "true",
                "parallel_runtime_created": "false",
                "a2_unlocked": "false",
                "next_short_step": NEXT_SHORT_STEP,
            }
            connection.executemany(
                "INSERT OR REPLACE INTO u01qb02_metadata(key,value) VALUES(?,?)", values.items()
            )
            count = connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0]
            contract_count = connection.execute(
                "SELECT COUNT(*) FROM response_contracts WHERE asset_key LIKE 'U01QB02:%'"
            ).fetchone()[0]
            if count != bank.EXPECTED_APPROVED_COUNT or contract_count != bank.EXPECTED_APPROVED_COUNT:
                raise SessionRuntimeError(f"runtime_registration_count_invalid:{count}:{contract_count}")
        return {
            "validation_status": PASS_STATUS,
            "registered_item_count": count,
            "response_contract_count": contract_count,
            "source_bank_artifact_sha256": approved["artifact_sha256"],
            "parallel_runtime_created": False,
            "a2_unlocked": False,
            "next_short_step": NEXT_SHORT_STEP,
        }

    @staticmethod
    def _stable_order(learner_id: str, session_id: str, reason: str, rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            (dict(row) for row in rows),
            key=lambda row: (
                hashlib.sha256(f"{learner_id}|{session_id}|{reason}|{row['item_id']}".encode("utf-8")).hexdigest(),
                row["pattern_family_id"],
                row["item_id"],
            ),
        )

    def _active_session(self, connection: sqlite3.Connection, *, learner_id: str, session_id: str) -> sqlite3.Row:
        session = connection.execute(
            "SELECT * FROM learning_sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        if not session or session["session_state"] != "ACTIVE":
            raise SessionRuntimeError("session_not_active")
        if session["learner_id"] != learner_id:
            raise SessionRuntimeError("session_learner_mismatch")
        expected_skill = LESSON_TO_SKILL.get(session["lesson_id"])
        if expected_skill is None or session["skill"] != expected_skill or session["level"] != "A1":
            raise SessionRuntimeError("session_not_unit01_supported_lesson")
        return session

    @staticmethod
    def _learner_item(row: Mapping[str, Any], *, position: int, reason: str) -> dict[str, Any]:
        item = json.loads(row["private_item_json"])
        return {
            "item_position": position,
            "item_id": row["item_id"],
            "asset_key": row["asset_key"],
            "skill": row["skill"],
            "pattern_family_id": row["pattern_family_id"],
            "unit_pattern_id": row["unit_pattern_id"],
            "question_type": item["question_type"],
            "prompt": item["prompt"],
            "stimulus": item["stimulus"],
            "options": list(item["options"]),
            "support_level": row["support_level"],
            "selection_reason": reason,
            "capture_enabled": bool(row["capture_enabled"]),
        }

    def _plan_payload(self, connection: sqlite3.Connection, session_id: str) -> dict[str, Any]:
        plan = connection.execute(
            "SELECT * FROM u01qb02_session_plans WHERE session_id=?", (session_id,)
        ).fetchone()
        if not plan:
            raise SessionRuntimeError("session_plan_not_found")
        rows = connection.execute(
            """SELECT s.item_position,s.selection_reason,c.*
            FROM u01qb02_session_items s JOIN u01qb02_item_catalog c USING(item_id)
            WHERE s.session_id=? ORDER BY s.item_position""",
            (session_id,),
        ).fetchall()
        return {
            "validation_status": PASS_STATUS,
            "session_id": session_id,
            "learner_id": plan["learner_id"],
            "lesson_id": plan["lesson_id"],
            "skill": plan["skill"],
            "item_count": len(rows),
            "items": [
                self._learner_item(row, position=row["item_position"], reason=row["selection_reason"])
                for row in rows
            ],
            "answer_keys_exposed": False,
            "source_bank_sha256": plan["source_bank_sha256"],
            "plan_digest": plan["plan_digest"],
            "a2_unlocked": False,
        }

    def assemble_session(
        self, *, learner_id: str, session_id: str, selected_at: str | None = None
    ) -> dict[str, Any]:
        selected_at = timestamp(selected_at)
        with self.write() as connection:
            metadata = dict(connection.execute("SELECT key,value FROM u01qb02_metadata"))
            if metadata.get("validation_status") != PASS_STATUS:
                raise SessionRuntimeError("u01qb02_not_initialized")
            session = self._active_session(connection, learner_id=learner_id, session_id=session_id)
            if connection.execute(
                "SELECT 1 FROM u01qb02_session_plans WHERE session_id=?", (session_id,)
            ).fetchone():
                return self._plan_payload(connection, session_id)
            catalog = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM u01qb02_item_catalog WHERE lesson_id=? ORDER BY item_id",
                    (session["lesson_id"],),
                )
            ]
            if len(catalog) < SESSION_SIZE:
                raise SessionRuntimeError("insufficient_approved_items_for_session")
            exposed = {
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT item_id FROM u01qb02_item_exposures WHERE learner_id=?",
                    (learner_id,),
                )
            }
            recent = {
                row[0]
                for row in connection.execute(
                    "SELECT item_id FROM u01qb02_item_exposures WHERE learner_id=? ORDER BY exposure_seq DESC LIMIT ?",
                    (learner_id, RECENT_EXPOSURE_WINDOW),
                )
            }
            latest_outcomes: dict[str, str] = {}
            for row in connection.execute(
                """SELECT c.item_id,r.outcome
                FROM response_attempts a
                JOIN scoring_results r USING(attempt_id)
                JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
                WHERE a.learner_id=? ORDER BY a.rowid DESC""",
                (learner_id,),
            ):
                latest_outcomes.setdefault(row["item_id"], row["outcome"])
            failed = {item_id for item_id, outcome in latest_outcomes.items() if outcome in FAIL_OUTCOMES}
            passed = {item_id for item_id, outcome in latest_outcomes.items() if outcome in PASS_OUTCOMES}
            selected: list[tuple[dict[str, Any], str]] = []
            selected_ids: set[str] = set()

            def take(reason: str, rows: Sequence[Mapping[str, Any]], count: int) -> None:
                ordered = self._stable_order(learner_id, session_id, reason, rows)
                for row in ordered:
                    if len([1 for _row, _reason in selected if _reason == reason]) >= count:
                        break
                    if row["item_id"] in selected_ids:
                        continue
                    selected.append((row, reason))
                    selected_ids.add(row["item_id"])

            take("REMEDIATION", [row for row in catalog if row["item_id"] in failed], SELECTION_QUOTA["REMEDIATION"])
            take(
                "SCHEDULED_REVIEW",
                [row for row in catalog if row["item_id"] in exposed and row["item_id"] not in failed and row["item_id"] not in recent and (not passed or row["item_id"] in passed)],
                SELECTION_QUOTA["SCHEDULED_REVIEW"],
            )
            take(
                "TRANSFER",
                [row for row in catalog if row["transfer_eligible"] and row["item_id"] not in exposed and row["item_id"] not in recent],
                SELECTION_QUOTA["TRANSFER"],
            )
            take(
                "GUIDED_EXTENSION",
                [row for row in catalog if row["support_level"] == "GUIDED_EXTENSION" and row["item_id"] not in exposed and row["item_id"] not in recent],
                SELECTION_QUOTA["GUIDED_EXTENSION"],
            )
            take(
                "NEW_OR_UNSEEN",
                [row for row in catalog if row["item_id"] not in exposed and row["item_id"] not in recent],
                SELECTION_QUOTA["NEW_OR_UNSEEN"],
            )
            if len(selected) < SESSION_SIZE:
                fallback = [
                    row for row in catalog
                    if row["item_id"] not in selected_ids and (row["item_id"] not in recent or row["item_id"] in failed)
                ]
                for row in self._stable_order(learner_id, session_id, "FALLBACK", fallback):
                    if len(selected) >= SESSION_SIZE:
                        break
                    selected.append((row, "FALLBACK"))
                    selected_ids.add(row["item_id"])
            if len(selected) != SESSION_SIZE:
                raise SessionRuntimeError(f"session_item_count_invalid:{len(selected)}")
            plan_core = {
                "session_id": session_id,
                "learner_id": learner_id,
                "lesson_id": session["lesson_id"],
                "skill": session["skill"],
                "selected_at": selected_at,
                "recent_exposure_window": RECENT_EXPOSURE_WINDOW,
                "items": [
                    {"position": index, "item_id": row["item_id"], "reason": reason}
                    for index, (row, reason) in enumerate(selected, 1)
                ],
                "source_bank_sha256": metadata["source_bank_artifact_sha256"],
            }
            plan_digest = digest(plan_core)
            connection.execute(
                "INSERT INTO u01qb02_session_plans VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    session_id, learner_id, session["lesson_id"], session["skill"], SESSION_SIZE,
                    selected_at, RECENT_EXPOSURE_WINDOW, metadata["source_bank_artifact_sha256"], plan_digest,
                ),
            )
            connection.executemany(
                "INSERT INTO u01qb02_session_items VALUES(?,?,?,?)",
                [
                    (session_id, index, row["item_id"], reason)
                    for index, (row, reason) in enumerate(selected, 1)
                ],
            )
            return self._plan_payload(connection, session_id)

    def record_item_exposure(
        self,
        *,
        session_id: str,
        item_id: str,
        expected_session_version: int,
        exposure_id: str | None = None,
        at: str | None = None,
    ) -> dict[str, Any]:
        at = timestamp(at)
        exposure_id = exposure_id or str(uuid.uuid4())
        with self.connect() as connection:
            selected = connection.execute(
                """SELECT p.learner_id,s.selection_reason,c.asset_key
                FROM u01qb02_session_items s
                JOIN u01qb02_session_plans p USING(session_id)
                JOIN u01qb02_item_catalog c USING(item_id)
                WHERE s.session_id=? AND s.item_id=?""",
                (session_id, item_id),
            ).fetchone()
            if not selected:
                raise SessionRuntimeError("item_not_selected_for_session")
            if connection.execute(
                "SELECT 1 FROM u01qb02_item_exposures WHERE session_id=? AND item_id=?",
                (session_id, item_id),
            ).fetchone():
                raise SessionRuntimeError("item_already_exposed_in_session")
        snapshot = m3.LearnerStateStore(self.database_path).record_exposure(
            session_id=session_id,
            asset_key=selected["asset_key"],
            expected_session_version=expected_session_version,
            at=at,
        )
        with self.write() as connection:
            previous = connection.execute(
                "SELECT exposure_hash FROM u01qb02_item_exposures ORDER BY exposure_seq DESC LIMIT 1"
            ).fetchone()
            previous_hash = previous[0] if previous else "0" * 64
            core = {
                "exposure_id": exposure_id,
                "learner_id": selected["learner_id"],
                "session_id": session_id,
                "item_id": item_id,
                "selection_reason": selected["selection_reason"],
                "exposure_at": at,
            }
            exposure_hash = hashlib.sha256((previous_hash + canonical(core)).encode("utf-8")).hexdigest()
            connection.execute(
                """INSERT INTO u01qb02_item_exposures
                (exposure_id,learner_id,session_id,item_id,selection_reason,exposure_at,previous_hash,exposure_hash)
                VALUES(?,?,?,?,?,?,?,?)""",
                (
                    exposure_id, selected["learner_id"], session_id, item_id,
                    selected["selection_reason"], at, previous_hash, exposure_hash,
                ),
            )
        return {
            "validation_status": PASS_STATUS,
            "session_id": session_id,
            "item_id": item_id,
            "asset_key": selected["asset_key"],
            "selection_reason": selected["selection_reason"],
            "exposure_id": exposure_id,
            "session_version": snapshot["session_version"],
            "m3_exposure_recorded": True,
            "mastery_claimed": False,
        }

    def capture_response(
        self,
        *,
        learner_id: str,
        session_id: str,
        item_id: str,
        response: Any,
        expected_session_version: int,
        attempt_id: str | None = None,
        submitted_at: str | None = None,
    ) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT c.asset_key,c.capture_enabled
                FROM u01qb02_session_items s JOIN u01qb02_item_catalog c USING(item_id)
                WHERE s.session_id=? AND s.item_id=?""",
                (session_id, item_id),
            ).fetchone()
            if not row:
                raise SessionRuntimeError("item_not_selected_for_session")
            if not connection.execute(
                "SELECT 1 FROM u01qb02_item_exposures WHERE session_id=? AND item_id=?",
                (session_id, item_id),
            ).fetchone():
                raise SessionRuntimeError("item_must_be_exposed_before_response")
            if row["capture_enabled"] != 1:
                raise SessionRuntimeError("item_response_capture_disabled")
        result = m6.ResponseEvidenceStore(self.database_path).capture_response(
            learner_id=learner_id,
            session_id=session_id,
            asset_key=row["asset_key"],
            response=response,
            expected_session_version=expected_session_version,
            attempt_id=attempt_id,
            submitted_at=submitted_at,
        )
        return {
            **result,
            "item_id": item_id,
            "asset_key": row["asset_key"],
            "m6_response_capture_reused": True,
            "parallel_scoring_created": False,
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--database", type=Path, required=True)
    assemble = commands.add_parser("assemble")
    assemble.add_argument("--database", type=Path, required=True)
    assemble.add_argument("--learner-id", required=True)
    assemble.add_argument("--session-id", required=True)
    expose = commands.add_parser("expose")
    expose.add_argument("--database", type=Path, required=True)
    expose.add_argument("--session-id", required=True)
    expose.add_argument("--item-id", required=True)
    expose.add_argument("--expected-session-version", type=int, required=True)
    capture = commands.add_parser("capture")
    capture.add_argument("--database", type=Path, required=True)
    capture.add_argument("--learner-id", required=True)
    capture.add_argument("--session-id", required=True)
    capture.add_argument("--item-id", required=True)
    capture.add_argument("--response-json", required=True)
    capture.add_argument("--expected-session-version", type=int, required=True)
    args = parser.parse_args(argv)
    runtime = Unit01ApprovedVariantSessionRuntime(args.database)
    if args.command == "init":
        result = runtime.initialize()
    elif args.command == "assemble":
        result = runtime.assemble_session(learner_id=args.learner_id, session_id=args.session_id)
    elif args.command == "expose":
        result = runtime.record_item_exposure(
            session_id=args.session_id,
            item_id=args.item_id,
            expected_session_version=args.expected_session_version,
        )
    else:
        result = runtime.capture_response(
            learner_id=args.learner_id,
            session_id=args.session_id,
            item_id=args.item_id,
            response=json.loads(args.response_json),
            expected_session_version=args.expected_session_version,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
