#!/usr/bin/env python3
"""Learner-facing U01QB15 adapter over the existing recovery-safe V1.2.1 runtime.

This module does not create another product runtime, planner, learner database,
QuestionBank, or scoring authority. It patches the already-active U01QB15
application with deterministic ordered form progression, a recovery-safe
post-completion M7/M8 refresh boundary, Unit01 browser routing, and the U01QB16E
different-item reassessment consumer. Unit02-24 continue to use legacy routes.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import u01qb15_runtime_server_recovery as recovery
from ulga.builders import _u01qb16e_different_item_reassessment_consumer_adapter as u16e

impl = recovery.impl

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Learner-facing route adapter over the already-approved U01QB15-R1 product "
    "consumer. It adds only ordered per-skill form progression metadata, Unit01 "
    "UI routing, an operational post-completion refresh-recovery marker, authenticated "
    "delivery of the packaged learner adapter, and the bounded U01QB16E different-item "
    "reassessment consumer; no learner content, QuestionBank, planner, database "
    "authority, scoring authority, Unit02-24 content, audio, speaking scoring, or A2 "
    "content is created."
)
PROGRAM_ID = impl.PROGRAM_ID
TASK_ID = "A1FS-V1-U01QB15_LearnerFacingE2EAcceptance"
PASS_STATUS = "PASS_A1FS_V1_U01QB15_LEARNER_FACING_E2E_ACCEPTANCE_IMPLEMENTED"
MODULE = "product.a1fs_v1_2_1.u01qb15_runtime_server_e2e"
FORM_SELECTION_MODE = "ORDERED_PER_SKILL_COMPLETION"
NEXT_SHORT_STEP = "A1FS-V1-U01QB15_LearnerFacingE2EPrivateBrowserReadback"
REFRESH_RECOVERY_TABLE = "u01qb15_post_completion_refresh_recovery"

_ORIGINAL_BOOTSTRAP = impl.U01QB15ProductApplication.bootstrap
_ORIGINAL_START_FORM = impl.U01QB15ProductApplication.start_u01qb15_form
_ORIGINAL_COMPLETE_SESSION = impl.U01QB15ProductApplication.complete_session
_ORIGINAL_HANDLER_GET = impl.U01QB15ProductHandler.do_GET


class LearnerFacingE2EError(impl.ProductCutoverError):
    """Fail-closed learner-facing form progression/recovery error."""


def _ensure_refresh_recovery_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS {REFRESH_RECOVERY_TABLE}(
            session_id TEXT PRIMARY KEY,
            learner_id TEXT NOT NULL,
            session_version INTEGER NOT NULL,
            refresh_state TEXT NOT NULL CHECK(refresh_state IN ('PASS','RECOVERY_REQUIRED')),
            original_error_type TEXT,
            recovery_error_type TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )


def _session_terminal_state(database, session_id: str) -> dict[str, Any] | None:
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """SELECT learner_id,session_id,lesson_id,skill,session_state,session_version
               FROM learning_sessions WHERE session_id=?""",
            (session_id,),
        ).fetchone()
    return None if row is None else dict(row)


def _record_refresh_state(
    database,
    *,
    session_id: str,
    learner_id: str,
    session_version: int,
    refresh_state: str,
    original_error_type: str | None = None,
    recovery_error_type: str | None = None,
) -> None:
    if refresh_state not in {"PASS", "RECOVERY_REQUIRED"}:
        raise LearnerFacingE2EError(f"REFRESH_RECOVERY_STATE_INVALID:{refresh_state}")
    with closing(sqlite3.connect(database)) as connection:
        _ensure_refresh_recovery_table(connection)
        connection.execute(
            f"""INSERT INTO {REFRESH_RECOVERY_TABLE}
                (session_id,learner_id,session_version,refresh_state,original_error_type,recovery_error_type,updated_at)
                VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                  learner_id=excluded.learner_id,
                  session_version=excluded.session_version,
                  refresh_state=excluded.refresh_state,
                  original_error_type=excluded.original_error_type,
                  recovery_error_type=excluded.recovery_error_type,
                  updated_at=CURRENT_TIMESTAMP""",
            (
                session_id,
                learner_id,
                int(session_version),
                refresh_state,
                original_error_type,
                recovery_error_type,
            ),
        )
        connection.commit()


def _pending_refresh_rows(database, learner_id: str) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        _ensure_refresh_recovery_table(connection)
        rows = connection.execute(
            f"""SELECT session_id,learner_id,session_version,original_error_type,recovery_error_type
                FROM {REFRESH_RECOVERY_TABLE}
                WHERE learner_id=? AND refresh_state='RECOVERY_REQUIRED'
                ORDER BY updated_at,session_id""",
            (learner_id,),
        ).fetchall()
        connection.commit()
    return [dict(row) for row in rows]


def _reconcile_pending_refresh(self) -> int:
    """Replay only derived M7/M8 refreshes before a later Unit01 form may start."""
    pending = _pending_refresh_rows(self.database_path, self.default_learner_id)
    for row in pending:
        try:
            self.refresh_canonical_learning(learner_id=str(row["learner_id"]))
        except Exception as exc:
            _record_refresh_state(
                self.database_path,
                session_id=str(row["session_id"]),
                learner_id=str(row["learner_id"]),
                session_version=int(row["session_version"]),
                refresh_state="RECOVERY_REQUIRED",
                original_error_type=str(row.get("original_error_type") or ""),
                recovery_error_type=type(exc).__name__,
            )
            raise LearnerFacingE2EError(
                "UNIT01_CANONICAL_REFRESH_RECOVERY_PENDING:"
                f"{row['session_id']}:{type(exc).__name__}"
            ) from exc
        _record_refresh_state(
            self.database_path,
            session_id=str(row["session_id"]),
            learner_id=str(row["learner_id"]),
            session_version=int(row["session_version"]),
            refresh_state="PASS",
            original_error_type=str(row.get("original_error_type") or ""),
            recovery_error_type=None,
        )
    return len(pending)


def next_form_ordinal(database, *, learner_id: str, skill: str) -> int | None:
    skill = str(skill).upper()
    if skill not in impl.qb02.UNIT01_LESSONS:
        raise LearnerFacingE2EError(f"UNIT01_SKILL_INVALID:{skill}")
    with closing(sqlite3.connect(database)) as connection:
        if not impl._table_exists(connection, "u01qb13_session_bindings"):
            raise LearnerFacingE2EError("U01QB13_SESSION_BINDINGS_TABLE_MISSING")
        completed = int(
            connection.execute(
                """SELECT COUNT(DISTINCT s.session_id)
                   FROM learning_sessions s
                   JOIN u01qb13_session_bindings b USING(session_id)
                   WHERE s.learner_id=? AND s.skill=? AND s.session_state='COMPLETED'
                     AND s.session_id NOT LIKE 'U01QB16E:%'""",
                (learner_id, skill),
            ).fetchone()[0]
        )
    if completed < 0 or completed > impl.EXPECTED_FORMS:
        raise LearnerFacingE2EError(f"UNIT01_COMPLETED_FORM_COUNT_INVALID:{skill}:{completed}")
    return None if completed == impl.EXPECTED_FORMS else completed + 1


def _bootstrap_with_u01qb15_e2e(self) -> dict[str, Any]:
    value = _ORIGINAL_BOOTSTRAP(self)
    semantics = value.setdefault("learner_product_semantics", {})
    cutover_active = bool(semantics.get("unit01_u01qb15_consumer_cutover_active"))
    pending_refresh_count = len(
        _pending_refresh_rows(self.database_path, self.default_learner_id)
    ) if cutover_active else 0
    semantics.update(
        {
            "unit01_questionbank_lesson_ids": dict(impl.qb02.UNIT01_LESSONS),
            "unit01_questionbank_form_selection_mode": FORM_SELECTION_MODE,
            "unit01_questionbank_browser_route_active": cutover_active,
            "unit01_questionbank_support_fillers_exposed_to_learner": False,
            "unit01_post_completion_refresh_recovery_pending_count": pending_refresh_count,
            "unit01_different_item_reassessment_active": u16e.installed(),
            "unit01_same_item_retry_allowed": False,
        }
    )
    semantics["unit01_next_form_ordinal_by_skill"] = (
        {
            skill: next_form_ordinal(
                self.database_path,
                learner_id=self.default_learner_id,
                skill=skill,
            )
            for skill in impl.qb02.UNIT01_LESSONS
        }
        if cutover_active
        else {skill: None for skill in impl.qb02.UNIT01_LESSONS}
    )
    return value


def _start_u01qb15_form_ordered(
    self, payload: Mapping[str, Any]
) -> dict[str, Any]:
    recovered_refresh_count = _reconcile_pending_refresh(self)
    skill = str(payload.get("skill") or "").upper()
    expected = next_form_ordinal(
        self.database_path,
        learner_id=self.default_learner_id,
        skill=skill,
    )
    if expected is None:
        raise LearnerFacingE2EError(f"UNIT01_TWELVE_FORM_SEQUENCE_COMPLETE:{skill}")

    requested_raw = payload.get("form_ordinal")
    if requested_raw not in (None, "", 0, "0"):
        requested = int(requested_raw)
        if requested != expected:
            raise LearnerFacingE2EError(
                f"UNIT01_FORM_SEQUENCE_OUT_OF_ORDER:{skill}:{requested}:{expected}"
            )

    normalized = dict(payload)
    normalized["skill"] = skill
    normalized["form_ordinal"] = expected
    result = _ORIGINAL_START_FORM(self, normalized)
    result["form_selection_mode"] = FORM_SELECTION_MODE
    result["ordered_form_ordinal"] = expected
    result["recovered_pending_canonical_refresh_count"] = recovered_refresh_count
    result["twelve_form_sequence_complete_after_this_session"] = (
        expected == impl.EXPECTED_FORMS
    )
    result["next_short_step"] = NEXT_SHORT_STEP
    return result


def _complete_session_recovery_safe(self, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Never misreport a committed Unit01 completion as an active learner session."""
    session_id = str(payload.get("session_id") or "")
    if not session_id or not impl._is_u01qb15_session(self.database_path, session_id):
        return _ORIGINAL_COMPLETE_SESSION(self, payload)
    try:
        completed = dict(_ORIGINAL_COMPLETE_SESSION(self, payload))
    except Exception as original_exc:
        terminal = _session_terminal_state(self.database_path, session_id)
        if not terminal or str(terminal.get("session_state")) != "COMPLETED":
            raise
        refresh_status = "RECOVERY_REQUIRED"
        recovery_error_type: str | None = None
        recovered_learning: Mapping[str, Any] | None = None
        try:
            recovered_learning = self.refresh_canonical_learning(
                learner_id=str(terminal["learner_id"])
            )
            refresh_status = "RECOVERED_AFTER_COMMIT"
        except Exception as recovery_exc:
            recovery_error_type = type(recovery_exc).__name__
        _record_refresh_state(
            self.database_path,
            session_id=session_id,
            learner_id=str(terminal["learner_id"]),
            session_version=int(terminal["session_version"]),
            refresh_state="PASS" if refresh_status == "RECOVERED_AFTER_COMMIT" else "RECOVERY_REQUIRED",
            original_error_type=type(original_exc).__name__,
            recovery_error_type=recovery_error_type,
        )
        return {
            **terminal,
            "completion_committed": True,
            "canonical_refresh_status": refresh_status,
            "canonical_refresh_recovery_required": refresh_status == "RECOVERY_REQUIRED",
            "canonical_learning_refresh": recovered_learning,
            "post_completion_error_type": type(original_exc).__name__,
            "post_completion_recovery_error_type": recovery_error_type,
            "frontend_state_must_reconcile_to_backend": True,
        }

    _record_refresh_state(
        self.database_path,
        session_id=session_id,
        learner_id=str(completed["learner_id"]),
        session_version=int(completed["session_version"]),
        refresh_state="PASS",
    )
    completed.update(
        {
            "completion_committed": True,
            "canonical_refresh_status": "PASS",
            "canonical_refresh_recovery_required": False,
            "frontend_state_must_reconcile_to_backend": True,
        }
    )
    return completed


def _do_get_with_u01qb15_static(self) -> None:
    """Serve the packaged Unit01 adapter through the existing S11 auth boundary."""
    path = impl.urlparse(self.path).path
    if path != "/u01qb15.js":
        _ORIGINAL_HANDLER_GET(self)
        return
    if not self._transport_valid():
        return
    claims = self._claims()
    if claims is None:
        self._json(401, {"error": "authentication_required"})
        return
    self._static(
        self.server.secure_static_root / "u01qb15.js",  # type: ignore[attr-defined]
        "application/javascript; charset=utf-8",
    )


# Patch the existing application/handler classes in place. The server,
# authenticated boundary, learner database, M3/M6/M7/M8 state and U01QB15 route
# handler remain the same objects used by the merged production consumer.
impl.U01QB15ProductApplication.bootstrap = _bootstrap_with_u01qb15_e2e
impl.U01QB15ProductApplication.start_u01qb15_form = _start_u01qb15_form_ordered
impl.U01QB15ProductApplication.complete_session = _complete_session_recovery_safe
impl.U01QB15ProductHandler.do_GET = _do_get_with_u01qb15_static

# U01QB16E wraps the already-patched ordered/recovery-safe methods above.  It
# therefore cannot replace M3/M6/M7 or bypass the post-completion refresh guard.
u16e.install_runtime(impl)

impl.MODULE = MODULE
impl.base.MODULE = MODULE


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return recovery.main(argv)
    except (LearnerFacingE2EError, u16e.DifferentItemReassessmentError) as exc:
        print(f"FAIL:{exc}", file=impl.os.sys.stderr)
        return 1


def __getattr__(name: str) -> Any:
    return getattr(recovery, name)


if __name__ == "__main__":
    raise SystemExit(main())
