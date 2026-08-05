#!/usr/bin/env python3
"""Learner-facing U01QB15 adapter over the existing recovery-safe V1.2.1 runtime.

This module does not create another product runtime, planner, learner database,
QuestionBank, or scoring authority.  It patches the already-active U01QB15
application with deterministic ordered form progression, exposes the lesson
identity map needed by the existing learner UI to route Unit01 only through the
U01QB15 endpoints, and serves the already-packaged Unit01 adapter through the
same authenticated static boundary.  Unit02-24 continue to use the legacy
product routes.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import u01qb15_runtime_server_recovery as recovery

impl = recovery.impl

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Learner-facing route adapter over the already-approved U01QB15-R1 product "
    "consumer. It adds only ordered per-skill form progression metadata, Unit01 "
    "UI routing identity, and authenticated delivery of the already-packaged "
    "u01qb15.js adapter; no learner content, QuestionBank, planner, database, "
    "scoring authority, Unit02-24 content, audio, speaking scoring, or A2 content "
    "is created."
)
PROGRAM_ID = impl.PROGRAM_ID
TASK_ID = "A1FS-V1-U01QB15_LearnerFacingE2EAcceptance"
PASS_STATUS = "PASS_A1FS_V1_U01QB15_LEARNER_FACING_E2E_ACCEPTANCE_IMPLEMENTED"
MODULE = "product.a1fs_v1_2_1.u01qb15_runtime_server_e2e"
FORM_SELECTION_MODE = "ORDERED_PER_SKILL_COMPLETION"
NEXT_SHORT_STEP = "A1FS-V1-U01QB15_LearnerFacingE2EPrivateBrowserReadback"

_ORIGINAL_BOOTSTRAP = impl.U01QB15ProductApplication.bootstrap
_ORIGINAL_START_FORM = impl.U01QB15ProductApplication.start_u01qb15_form
_ORIGINAL_HANDLER_GET = impl.U01QB15ProductHandler.do_GET


class LearnerFacingE2EError(impl.ProductCutoverError):
    """Fail-closed learner-facing form progression error."""


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
                   WHERE s.learner_id=? AND s.skill=? AND s.session_state='COMPLETED'""",
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
    semantics.update(
        {
            "unit01_questionbank_lesson_ids": dict(impl.qb02.UNIT01_LESSONS),
            "unit01_questionbank_form_selection_mode": FORM_SELECTION_MODE,
            "unit01_questionbank_browser_route_active": cutover_active,
            "unit01_questionbank_support_fillers_exposed_to_learner": False,
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
    result["twelve_form_sequence_complete_after_this_session"] = (
        expected == impl.EXPECTED_FORMS
    )
    result["next_short_step"] = NEXT_SHORT_STEP
    return result


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


# Patch the existing application/handler classes in place.  The server,
# authenticated boundary, learner database, M3/M6/M7/M8 state and U01QB15 route
# handler remain the same objects used by the merged production consumer.
impl.U01QB15ProductApplication.bootstrap = _bootstrap_with_u01qb15_e2e
impl.U01QB15ProductApplication.start_u01qb15_form = _start_u01qb15_form_ordered
impl.U01QB15ProductHandler.do_GET = _do_get_with_u01qb15_static
impl.MODULE = MODULE
impl.base.MODULE = MODULE


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return recovery.main(argv)
    except LearnerFacingE2EError as exc:
        print(f"FAIL:{exc}", file=impl.os.sys.stderr)
        return 1


def __getattr__(name: str) -> Any:
    return getattr(recovery, name)


if __name__ == "__main__":
    raise SystemExit(main())
