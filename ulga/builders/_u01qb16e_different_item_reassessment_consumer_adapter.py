"""Consume U01QB16D different-item candidates through the existing Unit01 runtime.

U01QB16D closes the diagnostic identity and nominates a learner-visible-distinct
existing QuestionBank item.  This adapter makes that nomination executable while
keeping M3, M6 and M7 as the only session, scoring and mastery authorities.

The production behavior is deliberately bounded:
- a scored Unit01 item is attempted at most once inside one form session;
- a form may complete with AUTO_FAIL/HUMAN_REJECT evidence once every scored item
  has an outcome, so canonical M7 can diagnose the failure instead of forcing an
  immediate same-item retry;
- a pending M7 reassessment blocks the next ordinary Unit01 form;
- after remediation acknowledgement, one U01QB16D candidate is placed in an
  ordinary U01QB02 ten-slot container, with only that U01QB13-bound item exposed;
- the candidate must not be the failed item, a learner-visible equivalent, a
  recently exposed item, or a reassessment signature already used for the same
  diagnosis;
- response capture delegates to U01QB02/M6 and completion delegates to the
  existing recovery-safe product completion path, which rebuilds canonical M7/M8.

No QuestionBank content, answer, scoring contract, M7 queue identity, mastery
policy, Unit02-24 content, audio, Speaking scoring or A2 state is created here.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as u16
from ulga.builders import _u01qb16d_questionbank_diagnosis_remediation_identity_adapter as u16d
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Runtime consumer over existing U01QB16D candidates, U01QB13 activity identity, "
    "M3 sessions and M6 scoring. It prevents same-item retry and materializes a "
    "single different existing-bank reassessment item without generating content, "
    "rewriting answers/scores/M7 queues/mastery policy, enabling Speaking scoring, "
    "modifying Unit02-24 or unlocking A2."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB16E_Unit01DifferentItemReassessmentConsumerIntegration"
PASS_STATUS = "PASS_A1FS_V1_U01QB16E_UNIT01_DIFFERENT_ITEM_REASSESSMENT_CONSUMER_INTEGRATION"
NEXT_SHORT_STEP = "A1FS-V1-U01QB16F_Unit01AdaptiveLoopLearnerFacingAcceptanceAndPedagogicalQualityCloseout"
SESSION_TABLE = "u01qb16e_reassessment_sessions"
SESSION_SQL = f"""
CREATE TABLE IF NOT EXISTS {SESSION_TABLE}(
  session_id TEXT PRIMARY KEY REFERENCES learning_sessions(session_id),
  diagnosis_id TEXT NOT NULL,
  learner_id TEXT NOT NULL,
  reassessment_ids_json TEXT NOT NULL,
  failed_item_id TEXT NOT NULL,
  reassessment_item_id TEXT NOT NULL,
  activity_id TEXT NOT NULL,
  reassessment_learner_visible_signature TEXT NOT NULL,
  consumer_state TEXT NOT NULL CHECK(consumer_state IN('ACTIVE','COMPLETED')),
  final_outcome TEXT,
  attempt_id TEXT,
  created_at TEXT NOT NULL,
  completed_at TEXT,
  consumer_digest TEXT NOT NULL UNIQUE
);
"""

_RUNTIME_IMPL: Any = None
_ORIGINAL_READINESS: Any = None
_ORIGINAL_SUBMIT_FORM_RESPONSE: Any = None
_ORIGINAL_START_FORM: Any = None
_ORIGINAL_HANDLER_GET: Any = None
_ORIGINAL_HANDLER_POST: Any = None
_INSTALLED = False


class DifferentItemReassessmentError(ValueError):
    pass


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _session_version(database: Path, session_id: str) -> int:
    with sqlite3.connect(Path(database)) as connection:
        row = connection.execute(
            "SELECT session_version FROM learning_sessions WHERE session_id=?", (session_id,)
        ).fetchone()
    if not row:
        raise DifferentItemReassessmentError("REASSESSMENT_SESSION_NOT_FOUND")
    return int(row[0])


def _pending_rows(connection: sqlite3.Connection, *, learner_id: str) -> list[dict[str, Any]]:
    if not all(
        _table_exists(connection, table)
        for table in (u16d.LINK_TABLE, "error_diagnoses", "reassessment_queue", "u01qb02_item_catalog")
    ):
        return []
    rows = connection.execute(
        f"""SELECT l.*,d.diagnosis_state
            FROM {u16d.LINK_TABLE} l
            JOIN error_diagnoses d USING(diagnosis_id)
            WHERE l.learner_id=? AND l.candidate_state='READY'
              AND d.diagnosis_state='OPEN'
            ORDER BY l.form_ordinal,l.diagnosis_id""",
        (learner_id,),
    ).fetchall()
    result: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        try:
            linked_ids = [str(value) for value in json.loads(str(row["reassessment_ids_json"]))]
        except json.JSONDecodeError as exc:
            raise DifferentItemReassessmentError("REASSESSMENT_IDS_INVALID") from exc
        pending_ids: list[str] = []
        for reassessment_id in linked_ids:
            queue = connection.execute(
                "SELECT queue_state FROM reassessment_queue WHERE reassessment_id=? AND learner_id=?",
                (reassessment_id, learner_id),
            ).fetchone()
            if queue and str(queue[0]) == "PENDING":
                pending_ids.append(reassessment_id)
        if not pending_ids:
            continue
        candidate = connection.execute(
            """SELECT item_id,asset_key,lesson_id,skill,pattern_family_id,support_level,
                      capture_enabled,private_item_json
               FROM u01qb02_item_catalog WHERE item_id=?""",
            (str(row["different_item_id"]),),
        ).fetchone()
        if not candidate:
            raise DifferentItemReassessmentError(
                f"REASSESSMENT_CANDIDATE_MISSING:{row['diagnosis_id']}"
            )
        candidate_row = dict(candidate)
        if int(candidate_row["capture_enabled"]) != 1 or str(candidate_row["skill"]) == "SPEAKING":
            raise DifferentItemReassessmentError(
                f"REASSESSMENT_CANDIDATE_NOT_SCORED:{row['diagnosis_id']}"
            )
        result.append(
            {
                **row,
                "pending_reassessment_ids": pending_ids,
                "candidate": candidate_row,
            }
        )
    return result


def pending_reassessments(database_path: Path, *, learner_id: str) -> list[dict[str, Any]]:
    with sqlite3.connect(Path(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = _pending_rows(connection, learner_id=learner_id)
        active_by_diagnosis: set[str] = set()
        if _table_exists(connection, SESSION_TABLE):
            active_by_diagnosis = {
                str(row[0])
                for row in connection.execute(
                    f"SELECT diagnosis_id FROM {SESSION_TABLE} WHERE learner_id=? AND consumer_state='ACTIVE'",
                    (learner_id,),
                ).fetchall()
            }
    return [
        {
            "diagnosis_id": str(row["diagnosis_id"]),
            "skill": str(row["skill"]),
            "form_ordinal": int(row["form_ordinal"]),
            "capability_class": str(row["capability_class"]),
            "targeted_error_tag": str(row["targeted_error_tag"]),
            "targeted_remediation_strategy": str(row["targeted_remediation_strategy"]),
            "pending_reassessment_ids": list(row["pending_reassessment_ids"]),
            "candidate_state": "READY",
            "active_reassessment_session": str(row["diagnosis_id"]) in active_by_diagnosis,
        }
        for row in rows
    ]


def _safe_item(row: Mapping[str, Any], *, activity: Mapping[str, Any]) -> dict[str, Any]:
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(Path("."))
    item = runtime._learner_item(row, position=1, reason="REMEDIATION")
    item.update(
        {
            "task_angle": str(activity["task_angle"]),
            "situation_family": str(activity["situation_family"]),
            "setting": str(activity["setting"]),
            "assessment_candidate": True,
            "reassessment": True,
        }
    )
    return item


def _select_pending(
    connection: sqlite3.Connection,
    *,
    learner_id: str,
    diagnosis_id: str,
) -> dict[str, Any]:
    matches = [
        row
        for row in _pending_rows(connection, learner_id=learner_id)
        if str(row["diagnosis_id"]) == diagnosis_id
    ]
    if len(matches) != 1:
        raise DifferentItemReassessmentError(
            f"PENDING_REASSESSMENT_DIAGNOSIS_NOT_UNIQUE:{diagnosis_id}:{len(matches)}"
        )
    return matches[0]


def materialize_reassessment_session(
    database_path: Path,
    *,
    learner_id: str,
    diagnosis_id: str,
    session_id: str,
    selected_at: str | None = None,
) -> dict[str, Any]:
    database_path = Path(database_path)
    selected_at = qb02.timestamp(selected_at)
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database_path)
    with runtime.write() as connection:
        connection.row_factory = sqlite3.Row
        for table in (
            "u01qb02_metadata",
            "u01qb02_item_catalog",
            "u01qb02_session_plans",
            "u01qb02_session_items",
            "u01qb02_item_exposures",
            "u01qb13_blueprint_activities",
            "u01qb13_session_bindings",
        ):
            if not _table_exists(connection, table):
                raise DifferentItemReassessmentError(f"REQUIRED_TABLE_MISSING:{table}")
        connection.executescript(SESSION_SQL)
        if connection.execute(
            f"SELECT 1 FROM {SESSION_TABLE} WHERE diagnosis_id=? AND consumer_state='ACTIVE'",
            (diagnosis_id,),
        ).fetchone():
            raise DifferentItemReassessmentError("REASSESSMENT_ALREADY_ACTIVE")
        pending = _select_pending(connection, learner_id=learner_id, diagnosis_id=diagnosis_id)
        session = runtime._active_session(connection, learner_id=learner_id, session_id=session_id)
        candidate = dict(pending["candidate"])
        if str(session["skill"]) != str(pending["skill"]) or str(session["lesson_id"]) != str(candidate["lesson_id"]):
            raise DifferentItemReassessmentError("REASSESSMENT_SESSION_SKILL_OR_LESSON_MISMATCH")
        if connection.execute(
            "SELECT 1 FROM u01qb02_session_plans WHERE session_id=?", (session_id,)
        ).fetchone():
            raise DifferentItemReassessmentError("REASSESSMENT_SESSION_ALREADY_PLANNED")

        candidate_signature = u16.learner_visible_signature(candidate)
        if str(candidate["item_id"]) == str(pending["item_id"]):
            raise DifferentItemReassessmentError("FAILED_ITEM_REPLAY_FORBIDDEN")
        if candidate_signature == str(pending["failed_learner_visible_signature"]):
            raise DifferentItemReassessmentError("FAILED_VISIBLE_SIGNATURE_REPLAY_FORBIDDEN")
        recent = {
            str(row[0])
            for row in connection.execute(
                "SELECT item_id FROM u01qb02_item_exposures WHERE learner_id=? ORDER BY exposure_seq DESC LIMIT ?",
                (learner_id, qb02.RECENT_EXPOSURE_WINDOW),
            ).fetchall()
        }
        if str(candidate["item_id"]) in recent:
            raise DifferentItemReassessmentError("REASSESSMENT_CANDIDATE_RECENTLY_EXPOSED")
        prior_signatures = {
            str(row[0])
            for row in connection.execute(
                f"SELECT reassessment_learner_visible_signature FROM {SESSION_TABLE} WHERE diagnosis_id=?",
                (diagnosis_id,),
            ).fetchall()
        }
        if candidate_signature in prior_signatures:
            raise DifferentItemReassessmentError("REASSESSMENT_VISIBLE_SIGNATURE_ALREADY_USED")

        activity = connection.execute(
            "SELECT * FROM u01qb13_blueprint_activities WHERE activity_id=?",
            (str(pending["activity_id"]),),
        ).fetchone()
        if not activity or str(activity["skill"]) != str(session["skill"]):
            raise DifferentItemReassessmentError("REASSESSMENT_ACTIVITY_IDENTITY_INVALID")
        activity_row = dict(activity)

        fillers = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM u01qb02_item_catalog WHERE lesson_id=? AND item_id NOT IN (?,?) ORDER BY item_id",
                (session["lesson_id"], candidate["item_id"], pending["item_id"]),
            ).fetchall()
            if str(row["item_id"]) not in recent
        ]
        if len(fillers) < qb02.SESSION_SIZE - 1:
            fillers = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM u01qb02_item_catalog WHERE lesson_id=? AND item_id NOT IN (?,?) ORDER BY item_id",
                    (session["lesson_id"], candidate["item_id"], pending["item_id"]),
                ).fetchall()
            ]
        fillers = runtime._stable_order(learner_id, session_id, "FALLBACK", fillers)
        if len(fillers) < qb02.SESSION_SIZE - 1:
            raise DifferentItemReassessmentError("REASSESSMENT_SUPPORT_CONTAINER_CAPACITY_INSUFFICIENT")
        selected = [(candidate, "REMEDIATION"), *[(row, "FALLBACK") for row in fillers[: qb02.SESSION_SIZE - 1]]]
        metadata = dict(connection.execute("SELECT key,value FROM u01qb02_metadata"))
        source_sha = str(metadata.get("source_bank_artifact_sha256") or "")
        if not source_sha:
            raise DifferentItemReassessmentError("SOURCE_BANK_IDENTITY_MISSING")
        plan_core = {
            "session_id": session_id,
            "learner_id": learner_id,
            "lesson_id": session["lesson_id"],
            "skill": session["skill"],
            "selected_at": selected_at,
            "recent_exposure_window": qb02.RECENT_EXPOSURE_WINDOW,
            "purpose": "U01QB16E_DIFFERENT_ITEM_REASSESSMENT",
            "diagnosis_id": diagnosis_id,
            "items": [
                {"position": index, "item_id": row["item_id"], "reason": reason}
                for index, (row, reason) in enumerate(selected, 1)
            ],
            "source_bank_sha256": source_sha,
        }
        connection.execute(
            "INSERT INTO u01qb02_session_plans VALUES(?,?,?,?,?,?,?,?,?)",
            (
                session_id,
                learner_id,
                session["lesson_id"],
                session["skill"],
                qb02.SESSION_SIZE,
                selected_at,
                qb02.RECENT_EXPOSURE_WINDOW,
                source_sha,
                qb02.digest(plan_core),
            ),
        )
        connection.executemany(
            "INSERT INTO u01qb02_session_items(session_id,item_position,item_id,selection_reason) VALUES(?,?,?,?)",
            [
                (session_id, index, row["item_id"], reason)
                for index, (row, reason) in enumerate(selected, 1)
            ],
        )
        connection.execute(
            """INSERT INTO u01qb13_session_bindings
               (session_id,activity_id,item_id,item_position,binding_quality,is_assessment_evidence)
               VALUES(?,?,?,?,?,1)""",
            (
                session_id,
                pending["activity_id"],
                candidate["item_id"],
                1,
                "U01QB16E_DIFFERENT_ITEM_REASSESSMENT",
            ),
        )
        core = {
            "session_id": session_id,
            "diagnosis_id": diagnosis_id,
            "learner_id": learner_id,
            "reassessment_ids": list(pending["pending_reassessment_ids"]),
            "failed_item_id": str(pending["item_id"]),
            "reassessment_item_id": str(candidate["item_id"]),
            "activity_id": str(pending["activity_id"]),
            "reassessment_learner_visible_signature": candidate_signature,
            "created_at": selected_at,
        }
        connection.execute(
            f"""INSERT INTO {SESSION_TABLE}
               (session_id,diagnosis_id,learner_id,reassessment_ids_json,failed_item_id,
                reassessment_item_id,activity_id,reassessment_learner_visible_signature,
                consumer_state,final_outcome,attempt_id,created_at,completed_at,consumer_digest)
               VALUES(?,?,?,?,?,?,?,?,'ACTIVE',NULL,NULL,?,NULL,?)""",
            (
                session_id,
                diagnosis_id,
                learner_id,
                json.dumps(core["reassessment_ids"], separators=(",", ":")),
                core["failed_item_id"],
                core["reassessment_item_id"],
                core["activity_id"],
                candidate_signature,
                selected_at,
                qb02.digest(core),
            ),
        )
        item_payload = _safe_item(candidate, activity=activity_row)
    return {
        "validation_status": PASS_STATUS,
        "task_id": TASK_ID,
        "diagnosis_id": diagnosis_id,
        "reassessment_ids": list(pending["pending_reassessment_ids"]),
        "targeted_error_tag": str(pending["targeted_error_tag"]),
        "targeted_remediation_strategy": str(pending["targeted_remediation_strategy"]),
        "session_id": session_id,
        "skill": str(session["skill"]),
        "lesson_id": str(session["lesson_id"]),
        "failed_item_id": str(pending["item_id"]),
        "item": item_payload,
        "failed_item_replayed": False,
        "learner_visible_signature_replayed": False,
        "support_fillers_exposed_to_learner": False,
        "questionbank_modified": False,
        "scoring_modified": False,
        "a2_unlocked": False,
    }


def _active_payload(database_path: Path, *, learner_id: str) -> dict[str, Any] | None:
    database_path = Path(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        if not _table_exists(connection, SESSION_TABLE):
            return None
        row = connection.execute(
            f"""SELECT r.*,s.lesson_id,s.skill,s.session_version
                FROM {SESSION_TABLE} r JOIN learning_sessions s USING(session_id)
                WHERE r.learner_id=? AND r.consumer_state='ACTIVE' AND s.session_state='ACTIVE'
                ORDER BY r.created_at DESC LIMIT 1""",
            (learner_id,),
        ).fetchone()
        if not row:
            return None
        catalog = connection.execute(
            "SELECT * FROM u01qb02_item_catalog WHERE item_id=?",
            (row["reassessment_item_id"],),
        ).fetchone()
        activity = connection.execute(
            "SELECT * FROM u01qb13_blueprint_activities WHERE activity_id=?",
            (row["activity_id"],),
        ).fetchone()
        link = connection.execute(
            f"SELECT targeted_error_tag,targeted_remediation_strategy FROM {u16d.LINK_TABLE} WHERE diagnosis_id=?",
            (row["diagnosis_id"],),
        ).fetchone()
        if not catalog or not activity or not link:
            raise DifferentItemReassessmentError("ACTIVE_REASSESSMENT_LINEAGE_INCOMPLETE")
        return {
            "validation_status": PASS_STATUS,
            "task_id": TASK_ID,
            "diagnosis_id": str(row["diagnosis_id"]),
            "reassessment_ids": json.loads(str(row["reassessment_ids_json"])),
            "targeted_error_tag": str(link["targeted_error_tag"]),
            "targeted_remediation_strategy": str(link["targeted_remediation_strategy"]),
            "session_id": str(row["session_id"]),
            "session_version": int(row["session_version"]),
            "skill": str(row["skill"]),
            "lesson_id": str(row["lesson_id"]),
            "failed_item_id": str(row["failed_item_id"]),
            "item": _safe_item(dict(catalog), activity=dict(activity)),
            "failed_item_replayed": False,
            "support_fillers_exposed_to_learner": False,
        }


def _completion_readiness_attempt_once(database: Path, session_id: str) -> dict[str, Any]:
    value = dict(_ORIGINAL_READINESS(database, session_id))
    if str(value.get("skill") or "").upper() == "SPEAKING":
        return value
    assets = list(value.get("assets") or [])
    not_attempted = sum(row.get("completion_state") == "NOT_ATTEMPTED" for row in assets)
    pending_human = sum(row.get("completion_state") == "PENDING_HUMAN_REVIEW" for row in assets)
    failed = sum(row.get("completion_state") == "RETRY_REQUIRED" for row in assets)
    value.update(
        {
            "gate_mode": "U01QB16E_ATTEMPT_ONCE_THEN_DIAGNOSE_REASSESS",
            "completion_allowed": not_attempted == 0 and pending_human == 0,
            "same_item_retry_allowed": False,
            "different_item_reassessment_required_count": failed,
        }
    )
    return value


def _submit_form_response_attempt_once(self, payload: Mapping[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "")
    item_id = str(payload.get("item_id") or "")
    if session_id and item_id:
        with sqlite3.connect(self.database_path) as connection:
            prior = int(
                connection.execute(
                    """SELECT COUNT(*) FROM response_attempts a
                       JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
                       WHERE a.session_id=? AND c.item_id=?""",
                    (session_id, item_id),
                ).fetchone()[0]
            )
        if prior:
            raise DifferentItemReassessmentError("UNIT01_SAME_ITEM_RETRY_FORBIDDEN")
    return _ORIGINAL_SUBMIT_FORM_RESPONSE(self, payload)


def _start_form_after_reassessment_gate(self, payload: Mapping[str, Any]) -> dict[str, Any]:
    pending = pending_reassessments(self.database_path, learner_id=self.default_learner_id)
    if pending:
        raise DifferentItemReassessmentError(
            f"UNIT01_PENDING_DIFFERENT_ITEM_REASSESSMENT:{pending[0]['diagnosis_id']}"
        )
    return _ORIGINAL_START_FORM(self, payload)


def _pending_api(self) -> dict[str, Any]:
    rows = pending_reassessments(self.database_path, learner_id=self.default_learner_id)
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "pending": bool(rows),
        "count": len(rows),
        "reassessments": rows,
        "questionbank_modified": False,
        "a2_unlocked": False,
    }


def _start_reassessment_api(self, payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("remediation_acknowledged") is not True:
        raise DifferentItemReassessmentError("REMEDIATION_ACKNOWLEDGEMENT_REQUIRED")
    diagnosis_id = str(payload.get("diagnosis_id") or "")
    if not diagnosis_id:
        raise DifferentItemReassessmentError("DIAGNOSIS_ID_REQUIRED")
    pending = pending_reassessments(self.database_path, learner_id=self.default_learner_id)
    target = next((row for row in pending if row["diagnosis_id"] == diagnosis_id), None)
    if target is None:
        raise DifferentItemReassessmentError("PENDING_REASSESSMENT_NOT_FOUND")
    if target["active_reassessment_session"]:
        raise DifferentItemReassessmentError("REASSESSMENT_ALREADY_ACTIVE")
    skill = str(target["skill"]).upper()
    lesson_id = qb02.UNIT01_LESSONS[skill]
    session_id = str(payload.get("session_id") or f"U01QB16E:{skill}:{uuid.uuid4().hex}")
    store = m3.LearnerStateStore(self.database_path)
    started = store.start_session(
        learner_id=self.default_learner_id,
        lesson_id=lesson_id,
        session_id=session_id,
        at=str(payload.get("at")) if payload.get("at") else None,
    )
    try:
        materialized = materialize_reassessment_session(
            self.database_path,
            learner_id=self.default_learner_id,
            diagnosis_id=diagnosis_id,
            session_id=session_id,
            selected_at=str(payload.get("at")) if payload.get("at") else None,
        )
        exposed = qb02.Unit01ApprovedVariantSessionRuntime(self.database_path).record_item_exposure(
            session_id=session_id,
            item_id=str(materialized["item"]["item_id"]),
            expected_session_version=int(started["session_version"]),
            at=str(payload.get("at")) if payload.get("at") else None,
        )
    except Exception:
        try:
            version = _session_version(self.database_path, session_id)
            store.end_session(
                session_id=session_id,
                outcome="ABANDONED",
                expected_session_version=version,
            )
        except Exception:
            pass
        raise
    return {
        **materialized,
        "session_version": int(exposed["session_version"]),
        "remediation_acknowledged": True,
        "candidate_exposure_recorded": True,
    }


def _submit_reassessment_api(self, payload: Mapping[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "")
    if not session_id:
        raise DifferentItemReassessmentError("REASSESSMENT_SESSION_ID_REQUIRED")
    with sqlite3.connect(self.database_path) as connection:
        connection.row_factory = sqlite3.Row
        if not _table_exists(connection, SESSION_TABLE):
            raise DifferentItemReassessmentError("REASSESSMENT_SESSION_TABLE_MISSING")
        row = connection.execute(
            f"SELECT * FROM {SESSION_TABLE} WHERE session_id=? AND learner_id=? AND consumer_state='ACTIVE'",
            (session_id, self.default_learner_id),
        ).fetchone()
        if not row:
            raise DifferentItemReassessmentError("ACTIVE_REASSESSMENT_SESSION_NOT_FOUND")
        item_id = str(row["reassessment_item_id"])
    result = qb02.Unit01ApprovedVariantSessionRuntime(self.database_path).capture_response(
        learner_id=self.default_learner_id,
        session_id=session_id,
        item_id=item_id,
        response=payload.get("response"),
        expected_session_version=int(payload.get("expected_session_version")),
    )
    current_version = _session_version(self.database_path, session_id)
    completed = self.complete_session(
        {
            "session_id": session_id,
            "expected_session_version": current_version,
            **({"at": str(payload["at"])} if payload.get("at") else {}),
        }
    )
    with sqlite3.connect(self.database_path) as connection:
        connection.execute(
            f"""UPDATE {SESSION_TABLE}
                SET consumer_state='COMPLETED',final_outcome=?,attempt_id=?,completed_at=CURRENT_TIMESTAMP
                WHERE session_id=?""",
            (str(result.get("outcome") or ""), str(result.get("attempt_id") or ""), session_id),
        )
        connection.commit()
    return {
        **result,
        "validation_status": PASS_STATUS,
        "task_id": TASK_ID,
        "reassessment_session_completed": True,
        "canonical_completion": completed,
        "failed_item_replayed": False,
        "questionbank_modified": False,
        "scoring_modified": False,
        "a2_unlocked": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def install_runtime(impl: Any) -> None:
    """Patch the already-active U01QB15 runtime in place, idempotently."""
    global _RUNTIME_IMPL, _ORIGINAL_READINESS, _ORIGINAL_SUBMIT_FORM_RESPONSE
    global _ORIGINAL_START_FORM, _ORIGINAL_HANDLER_GET, _ORIGINAL_HANDLER_POST, _INSTALLED
    if _INSTALLED:
        return
    _RUNTIME_IMPL = impl
    _ORIGINAL_READINESS = impl.u01qb15_completion_readiness
    _ORIGINAL_SUBMIT_FORM_RESPONSE = impl.U01QB15ProductApplication.submit_u01qb15_response
    _ORIGINAL_START_FORM = impl.U01QB15ProductApplication.start_u01qb15_form
    _ORIGINAL_HANDLER_GET = impl.U01QB15ProductHandler.do_GET
    _ORIGINAL_HANDLER_POST = impl.U01QB15ProductHandler.do_POST

    impl.u01qb15_completion_readiness = _completion_readiness_attempt_once
    impl.U01QB15ProductApplication.submit_u01qb15_response = _submit_form_response_attempt_once
    impl.U01QB15ProductApplication.start_u01qb15_form = _start_form_after_reassessment_gate
    impl.U01QB15ProductApplication.u01qb16e_pending_reassessments = _pending_api
    impl.U01QB15ProductApplication.start_u01qb16e_reassessment = _start_reassessment_api
    impl.U01QB15ProductApplication.submit_u01qb16e_reassessment = _submit_reassessment_api
    impl.U01QB15ProductApplication.active_u01qb16e_reassessment = lambda self: (
        {"active": True, "reassessment": value}
        if (value := _active_payload(self.database_path, learner_id=self.default_learner_id))
        else {"active": False}
    )

    def do_get(handler: Any) -> None:
        path = impl.urlparse(handler.path).path
        routes = {
            "/api/u01qb16e/reassessment/pending": handler.u01qb15_app.u01qb16e_pending_reassessments,
            "/api/u01qb16e/reassessment/active": handler.u01qb15_app.active_u01qb16e_reassessment,
        }
        action = routes.get(path)
        if action is None:
            _ORIGINAL_HANDLER_GET(handler)
            return
        if not handler._transport_valid():
            return
        if handler._claims() is None:
            handler._json(401, {"error": "authentication_required"})
            return
        try:
            handler._json(200, action())
        except (DifferentItemReassessmentError, qb02.SessionRuntimeError, sqlite3.Error, ValueError) as exc:
            handler._json(409, {"error": str(exc)})

    def do_post(handler: Any) -> None:
        path = impl.urlparse(handler.path).path
        routes = {
            "/api/u01qb16e/reassessment/start": handler.u01qb15_app.start_u01qb16e_reassessment,
            "/api/u01qb16e/reassessment/response": handler.u01qb15_app.submit_u01qb16e_reassessment,
        }
        action = routes.get(path)
        if action is None:
            _ORIGINAL_HANDLER_POST(handler)
            return
        if not handler._transport_valid() or not handler._origin_valid():
            return
        claims = handler._claims()
        if claims is None:
            handler._json(401, {"error": "authentication_required"})
            return
        if not handler._csrf_valid(claims):
            return
        try:
            handler._json(200, action(handler._read_json_body()))
        except (
            DifferentItemReassessmentError,
            qb02.SessionRuntimeError,
            m3.StateStoreError,
            sqlite3.Error,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            handler._json(409, {"error": str(exc)})

    impl.U01QB15ProductHandler.do_GET = do_get
    impl.U01QB15ProductHandler.do_POST = do_post
    _INSTALLED = True


def installed() -> bool:
    return bool(_INSTALLED)
