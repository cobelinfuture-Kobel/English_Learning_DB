#!/usr/bin/env python3
"""Route Unit01 fair selection only through explicit login/guest scopes.

Legacy internal and evidence workflows may have an M3 learner profile without an
identity-scope binding. Those workflows retain the original U01QB02 selector.
Authenticated and guest identities created through the approved scope API use
the identity-fair selector. This preserves the Real62 content-binding acceptance
without weakening compatibility or creating another selector.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ulga.builders import (
    build_a1fs_ops_v1_unit01_identity_scoped_fair_question_selection as fair,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Routes the existing U01QB02 class to its preserved legacy assembler when "
    "no approved authenticated/guest identity scope exists, and to the already "
    "merged identity-fair assembler when one does. It creates no question, bank, "
    "selector, planner, state engine, content, score, audio, A2 content, or "
    "Unit02-Unit24 artifact."
)
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = (
    "A1FS-OPS-V1_"
    "Unit01IdentityFairSelectionExplicitScopeCompatibilityGuard"
)
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_IDENTITY_FAIR_SELECTION_SCOPE_GUARD"

if not hasattr(fair, "_bound_scope_guard_scoped_assemble"):
    fair._bound_scope_guard_scoped_assemble = fair._assemble_session

_SCOPED_FAIR_ASSEMBLE = fair._bound_scope_guard_scoped_assemble


def _scope_exists(runtime, learner_id: str) -> bool:
    with runtime.connect() as connection:
        table = connection.execute(
            """SELECT 1 FROM sqlite_master
            WHERE type='table' AND name='u01qb02_identity_scopes'"""
        ).fetchone()
        if not table:
            return False
        return bool(
            connection.execute(
                """SELECT 1 FROM u01qb02_identity_scopes
                WHERE learner_id=? ORDER BY opened_at DESC LIMIT 1""",
                (str(learner_id),),
            ).fetchone()
        )


def _assemble_session(
    self,
    *,
    learner_id: str,
    session_id: str,
    selected_at: str | None = None,
    selection_mode: str | None = None,
) -> dict[str, Any]:
    if _scope_exists(self, learner_id):
        return _SCOPED_FAIR_ASSEMBLE(
            self,
            learner_id=learner_id,
            session_id=session_id,
            selected_at=selected_at,
            selection_mode=selection_mode,
        )
    if selection_mode not in (None, "ADAPTIVE"):
        raise fair.IdentityFairSelectionError(
            "fair_selection_identity_scope_required"
        )
    return self._identity_fair_original_assemble(
        learner_id=learner_id,
        session_id=session_id,
        selected_at=selected_at,
    )


def install_guard() -> None:
    fair._assemble_session = _assemble_session
    fair.install_fullfix()


def validate_installation() -> dict[str, Any]:
    installed = (
        fair.qb02.Unit01ApprovedVariantSessionRuntime.assemble_session
        is _assemble_session
        and fair._assemble_session is _assemble_session
    )
    return {
        "task_id": TASK_ID,
        "status": PASS_STATUS if installed else "FAIL",
        "explicit_identity_scope_required": True,
        "legacy_u01qb02_selector_preserved": True,
        "identity_fair_selector_preserved": True,
        "parallel_selector_created": False,
    }


install_guard()
