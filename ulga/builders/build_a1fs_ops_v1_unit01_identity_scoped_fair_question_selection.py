#!/usr/bin/env python3
"""FullFix the existing Unit01 selector with identity-scoped fair selection.

This module does not create another question bank or selector. It installs a
replacement for ``U01QB02.Unit01ApprovedVariantSessionRuntime.assemble_session``
on the same class and in the same SQLite database. Authenticated identities
reuse their persistent M3 learner_id. Guest identities receive one opaque,
expiring M3 learner_id derived from a random guest-login token; only a SHA-256
subject digest is persisted. A guest's generated plans count as already used
inside that guest login, so requesting another paper prefers fresh items even
before the first paper is answered.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Patches the existing U01QB02 session assembler in place and stores only "
    "identity-scope metadata in the same M3/U01QB02 SQLite database. It creates "
    "no question, answer, bank, planner, renderer, learner-state engine, scoring "
    "engine, audio, A2 content, or Unit02-Unit24 artifact."
)
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = (
    "A1FS-OPS-V1_"
    "Unit01IdentityScopedFairQuestionSelectionAndGuestSessionAcceptance"
)
SCHEMA_VERSION = "a1fs.ops.v1.unit01_identity_scoped_fair_selection.v1"
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_IDENTITY_SCOPED_FAIR_SELECTION"
NEXT_SHORT_STEP = (
    "A1FS-OPS-V1_"
    "Unit01QuestionBankStudentPackagePhraseToSentenceBuilderAndQA"
)
GUEST_LEARNER_PREFIX = "A1FS_GUEST_"
GUEST_DEFAULT_TTL_SECONDS = 24 * 60 * 60
IDENTITY_MODES = frozenset({"AUTHENTICATED", "GUEST"})
SELECTION_MODES = frozenset({"ADAPTIVE", "FRESH"})
HEX64 = re.compile(r"^[0-9a-f]{64}$")

IDENTITY_SQL = """
CREATE TABLE IF NOT EXISTS u01qb02_identity_scopes(
  scope_id TEXT PRIMARY KEY,
  learner_id TEXT NOT NULL REFERENCES learner_profiles(learner_id),
  identity_mode TEXT NOT NULL CHECK(identity_mode IN ('AUTHENTICATED','GUEST')),
  subject_digest TEXT NOT NULL UNIQUE,
  opened_at TEXT NOT NULL,
  expires_at TEXT,
  closed_at TEXT,
  CHECK(
    (identity_mode='AUTHENTICATED' AND expires_at IS NULL)
    OR (identity_mode='GUEST' AND expires_at IS NOT NULL)
  )
);
CREATE INDEX IF NOT EXISTS u01qb02_identity_scope_learner
ON u01qb02_identity_scopes(learner_id,identity_mode,closed_at);
"""

PEDAGOGICAL_FAMILY_ORDER: dict[str, dict[str, int]] = {
    "READING": {
        "U01-PF04-FIRST-MENTION-CONTEXT": 10,
        "U01-PF05-KNOWN-REFERENCE-CONTEXT": 20,
        "U01-PF06-ERROR-DISCRIMINATION": 30,
        "U01-PF08-TRANSFER-FIRST-MENTION": 40,
    },
    "WRITING": {
        "U01-PF01-AAN-NOUN-GAP": 10,
        "U01-PF02-AAN-ADJ-NOUN-GAP": 20,
        "U01-PF03-VERY-ADJ-NOUN-GAP": 30,
        "U01-PF07-WORD-ORDER": 40,
        "U01-PF09-TRANSFER-KNOWN-REFERENCE": 50,
    },
    "SPEAKING": {
        "U01-PF10-SPEAK-NOUN": 10,
        "U01-PF11-SPEAK-ADJ-NOUN": 20,
        "U01-PF12-SPEAK-VERY-ADJ-NOUN": 30,
    },
}

if not hasattr(qb02.Unit01ApprovedVariantSessionRuntime, "_identity_fair_original_initialize"):
    qb02.Unit01ApprovedVariantSessionRuntime._identity_fair_original_initialize = (
        qb02.Unit01ApprovedVariantSessionRuntime.initialize
    )
if not hasattr(qb02.Unit01ApprovedVariantSessionRuntime, "_identity_fair_original_assemble"):
    qb02.Unit01ApprovedVariantSessionRuntime._identity_fair_original_assemble = (
        qb02.Unit01ApprovedVariantSessionRuntime.assemble_session
    )

_ORIGINAL_INITIALIZE = (
    qb02.Unit01ApprovedVariantSessionRuntime._identity_fair_original_initialize
)


class IdentityFairSelectionError(qb02.SessionRuntimeError):
    """Fail-closed identity or fair-selection error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise IdentityFairSelectionError("identity_scope_timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise IdentityFairSelectionError("identity_scope_timestamp_timezone_required")
    return parsed.astimezone(timezone.utc)


def _time(value: str | None = None) -> str:
    return qb02.timestamp(value)


def _subject_digest(mode: str, subject_key: str) -> str:
    mode = str(mode).strip().upper()
    value = str(subject_key)
    if mode not in IDENTITY_MODES:
        raise IdentityFairSelectionError("identity_mode_invalid")
    if len(value) < 16 or len(value) > 1024:
        raise IdentityFairSelectionError("identity_subject_key_invalid")
    return hashlib.sha256(f"{TASK_ID}:{mode}:{value}".encode("utf-8")).hexdigest()


def _ensure_identity_schema(runtime: qb02.Unit01ApprovedVariantSessionRuntime) -> None:
    with runtime.write() as connection:
        connection.executescript(IDENTITY_SQL)


def _profile_exists(runtime: qb02.Unit01ApprovedVariantSessionRuntime, learner_id: str) -> bool:
    with runtime.connect() as connection:
        return bool(
            connection.execute(
                "SELECT 1 FROM learner_profiles WHERE learner_id=?",
                (learner_id,),
            ).fetchone()
        )


def _create_profile(
    runtime: qb02.Unit01ApprovedVariantSessionRuntime,
    *,
    learner_id: str,
    display_label: str,
    at: str,
) -> None:
    if _profile_exists(runtime, learner_id):
        return
    m3.LearnerStateStore(runtime.database_path).create_profile(
        learner_id=learner_id,
        display_label=display_label,
        locale="zh-TW",
        timezone_name="Asia/Taipei",
        at=at,
    )


def bind_authenticated_identity(
    runtime: qb02.Unit01ApprovedVariantSessionRuntime,
    *,
    learner_id: str,
    subject_key: str,
    display_label: str = "Learner",
    at: str | None = None,
) -> dict[str, Any]:
    opened_at = _time(at)
    learner_id = str(learner_id).strip()
    if not learner_id or learner_id.startswith(GUEST_LEARNER_PREFIX):
        raise IdentityFairSelectionError("authenticated_learner_id_invalid")
    _ensure_identity_schema(runtime)
    _create_profile(
        runtime,
        learner_id=learner_id,
        display_label=str(display_label).strip() or "Learner",
        at=opened_at,
    )
    digest = _subject_digest("AUTHENTICATED", subject_key)
    scope_id = f"U01QB02-AUTH-{digest[:24]}"
    with runtime.write() as connection:
        existing = connection.execute(
            "SELECT * FROM u01qb02_identity_scopes WHERE subject_digest=?",
            (digest,),
        ).fetchone()
        if existing:
            if (
                existing["identity_mode"] != "AUTHENTICATED"
                or existing["learner_id"] != learner_id
            ):
                raise IdentityFairSelectionError("authenticated_subject_binding_conflict")
            return {
                "scope_id": str(existing["scope_id"]),
                "learner_id": learner_id,
                "identity_mode": "AUTHENTICATED",
                "identity_reused": True,
                "history_persistence": "CROSS_LOGIN",
            }
        connection.execute(
            """INSERT INTO u01qb02_identity_scopes
            (scope_id,learner_id,identity_mode,subject_digest,opened_at,expires_at,closed_at)
            VALUES(?,?,?,?,?,NULL,NULL)""",
            (scope_id, learner_id, "AUTHENTICATED", digest, opened_at),
        )
    return {
        "scope_id": scope_id,
        "learner_id": learner_id,
        "identity_mode": "AUTHENTICATED",
        "identity_reused": False,
        "history_persistence": "CROSS_LOGIN",
    }


def open_guest_identity(
    runtime: qb02.Unit01ApprovedVariantSessionRuntime,
    *,
    guest_token: str,
    display_label: str = "Guest",
    ttl_seconds: int = GUEST_DEFAULT_TTL_SECONDS,
    at: str | None = None,
) -> dict[str, Any]:
    if not (60 <= int(ttl_seconds) <= 7 * 24 * 60 * 60):
        raise IdentityFairSelectionError("guest_ttl_invalid")
    opened_at = _time(at)
    digest = _subject_digest("GUEST", guest_token)
    scope_id = f"U01QB02-GUEST-{digest[:24]}"
    learner_id = f"{GUEST_LEARNER_PREFIX}{digest[:24].upper()}"
    expires_at = (
        _parse_time(opened_at) + timedelta(seconds=int(ttl_seconds))
    ).isoformat().replace("+00:00", "Z")
    _ensure_identity_schema(runtime)
    with runtime.connect() as connection:
        existing = connection.execute(
            "SELECT * FROM u01qb02_identity_scopes WHERE subject_digest=?",
            (digest,),
        ).fetchone()
    if existing:
        if existing["identity_mode"] != "GUEST" or existing["learner_id"] != learner_id:
            raise IdentityFairSelectionError("guest_subject_binding_conflict")
        if existing["closed_at"] is not None:
            raise IdentityFairSelectionError("guest_scope_closed_new_token_required")
        if _parse_time(str(existing["expires_at"])) <= _parse_time(opened_at):
            raise IdentityFairSelectionError("guest_scope_expired_new_token_required")
        return {
            "scope_id": str(existing["scope_id"]),
            "learner_id": learner_id,
            "identity_mode": "GUEST",
            "identity_reused": True,
            "expires_at": str(existing["expires_at"]),
            "history_persistence": "CURRENT_GUEST_LOGIN_ONLY",
        }
    _create_profile(
        runtime,
        learner_id=learner_id,
        display_label=str(display_label).strip() or "Guest",
        at=opened_at,
    )
    with runtime.write() as connection:
        connection.execute(
            """INSERT INTO u01qb02_identity_scopes
            (scope_id,learner_id,identity_mode,subject_digest,opened_at,expires_at,closed_at)
            VALUES(?,?,?,?,?,?,NULL)""",
            (scope_id, learner_id, "GUEST", digest, opened_at, expires_at),
        )
    return {
        "scope_id": scope_id,
        "learner_id": learner_id,
        "identity_mode": "GUEST",
        "identity_reused": False,
        "expires_at": expires_at,
        "history_persistence": "CURRENT_GUEST_LOGIN_ONLY",
    }


def close_guest_identity(
    runtime: qb02.Unit01ApprovedVariantSessionRuntime,
    *,
    scope_id: str,
    at: str | None = None,
) -> dict[str, Any]:
    closed_at = _time(at)
    _ensure_identity_schema(runtime)
    with runtime.write() as connection:
        row = connection.execute(
            "SELECT * FROM u01qb02_identity_scopes WHERE scope_id=?",
            (str(scope_id),),
        ).fetchone()
        if not row or row["identity_mode"] != "GUEST":
            raise IdentityFairSelectionError("guest_scope_not_found")
        if row["closed_at"] is None:
            connection.execute(
                "UPDATE u01qb02_identity_scopes SET closed_at=? WHERE scope_id=?",
                (closed_at, str(scope_id)),
            )
    return {
        "scope_id": str(scope_id),
        "learner_id": str(row["learner_id"]),
        "identity_mode": "GUEST",
        "closed": True,
        "history_reused_after_close": False,
    }


def resolve_identity_scope(
    runtime: qb02.Unit01ApprovedVariantSessionRuntime,
    *,
    scope_id: str,
    at: str | None = None,
) -> dict[str, Any]:
    moment = _time(at)
    _ensure_identity_schema(runtime)
    with runtime.connect() as connection:
        row = connection.execute(
            "SELECT * FROM u01qb02_identity_scopes WHERE scope_id=?",
            (str(scope_id),),
        ).fetchone()
    if not row:
        raise IdentityFairSelectionError("identity_scope_not_found")
    if row["identity_mode"] == "GUEST":
        if row["closed_at"] is not None:
            raise IdentityFairSelectionError("guest_scope_closed")
        if _parse_time(str(row["expires_at"])) <= _parse_time(moment):
            raise IdentityFairSelectionError("guest_scope_expired")
    return {
        "scope_id": str(row["scope_id"]),
        "learner_id": str(row["learner_id"]),
        "identity_mode": str(row["identity_mode"]),
        "expires_at": row["expires_at"],
        "history_persistence": (
            "CURRENT_GUEST_LOGIN_ONLY"
            if row["identity_mode"] == "GUEST"
            else "CROSS_LOGIN"
        ),
    }


def _guest_scope_active(
    connection: sqlite3.Connection,
    *,
    learner_id: str,
    at: str,
) -> bool:
    if not str(learner_id).startswith(GUEST_LEARNER_PREFIX):
        return False
    row = connection.execute(
        """SELECT expires_at,closed_at FROM u01qb02_identity_scopes
        WHERE learner_id=? AND identity_mode='GUEST'
        ORDER BY opened_at DESC LIMIT 1""",
        (learner_id,),
    ).fetchone()
    if not row or row["closed_at"] is not None:
        raise IdentityFairSelectionError("guest_scope_not_active")
    if _parse_time(str(row["expires_at"])) <= _parse_time(at):
        raise IdentityFairSelectionError("guest_scope_expired")
    return True


def _initialize(self: qb02.Unit01ApprovedVariantSessionRuntime) -> dict[str, Any]:
    result = _ORIGINAL_INITIALIZE(self)
    _ensure_identity_schema(self)
    return {
        **result,
        "identity_scope_support": True,
        "guest_history_current_login_only": True,
        "fair_selection_fullfix_installed": True,
    }


def _history(
    connection: sqlite3.Connection,
    *,
    learner_id: str,
    lesson_id: str,
) -> tuple[dict[str, dict[str, Any]], set[str], set[str], dict[str, int]]:
    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "plan_count": 0,
            "exposure_count": 0,
            "last_selected_at": "",
            "last_exposure_seq": -1,
        }
    )
    for row in connection.execute(
        """SELECT si.item_id,COUNT(*) AS plan_count,MAX(sp.selected_at) AS last_selected_at
        FROM u01qb02_session_items si
        JOIN u01qb02_session_plans sp USING(session_id)
        WHERE sp.learner_id=? AND sp.lesson_id=?
        GROUP BY si.item_id""",
        (learner_id, lesson_id),
    ):
        stats[str(row["item_id"])].update(
            {
                "plan_count": int(row["plan_count"]),
                "last_selected_at": str(row["last_selected_at"] or ""),
            }
        )
    for row in connection.execute(
        """SELECT e.item_id,COUNT(*) AS exposure_count,MAX(e.exposure_seq) AS last_exposure_seq
        FROM u01qb02_item_exposures e
        JOIN u01qb02_item_catalog c USING(item_id)
        WHERE e.learner_id=? AND c.lesson_id=?
        GROUP BY e.item_id""",
        (learner_id, lesson_id),
    ):
        stats[str(row["item_id"])].update(
            {
                "exposure_count": int(row["exposure_count"]),
                "last_exposure_seq": int(row["last_exposure_seq"]),
            }
        )
    planned = {item_id for item_id, value in stats.items() if value["plan_count"] > 0}
    recent_rows = connection.execute(
        """SELECT si.item_id
        FROM u01qb02_session_items si
        JOIN u01qb02_session_plans sp USING(session_id)
        WHERE sp.learner_id=? AND sp.lesson_id=?
        ORDER BY sp.selected_at DESC,si.item_position DESC
        LIMIT ?""",
        (learner_id, lesson_id, qb02.RECENT_EXPOSURE_WINDOW),
    ).fetchall()
    recent = {str(row[0]) for row in recent_rows}
    family_counts = {
        str(row["pattern_family_id"]): int(row["use_count"])
        for row in connection.execute(
            """SELECT c.pattern_family_id,COUNT(*) AS use_count
            FROM u01qb02_session_items si
            JOIN u01qb02_session_plans sp USING(session_id)
            JOIN u01qb02_item_catalog c USING(item_id)
            WHERE sp.learner_id=? AND sp.lesson_id=?
            GROUP BY c.pattern_family_id""",
            (learner_id, lesson_id),
        )
    }
    return dict(stats), planned, recent, family_counts


def _pedagogical_rank(skill: str, family_id: str) -> int:
    return PEDAGOGICAL_FAMILY_ORDER.get(str(skill), {}).get(str(family_id), 999)


def _fair_order(
    *,
    learner_id: str,
    session_id: str,
    reason: str,
    skill: str,
    rows: Sequence[Mapping[str, Any]],
    history: Mapping[str, Mapping[str, Any]],
    family_counts: Mapping[str, int],
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in rows:
        row = dict(source)
        item_id = str(row["item_id"])
        values = history.get(item_id) or {}
        row["_plan_count"] = int(values.get("plan_count") or 0)
        row["_last_selected_at"] = str(values.get("last_selected_at") or "")
        row["_last_exposure_seq"] = int(values.get("last_exposure_seq") or -1)
        groups[str(row["pattern_family_id"])].append(row)
    for family_rows in groups.values():
        family_rows.sort(
            key=lambda row: (
                row["_plan_count"],
                row["_last_selected_at"],
                row["_last_exposure_seq"],
                hashlib.sha256(
                    f"{learner_id}|{session_id}|{reason}|{row['item_id']}".encode("utf-8")
                ).hexdigest(),
                row["item_id"],
            )
        )
    family_order = sorted(
        groups,
        key=lambda family_id: (
            int(family_counts.get(family_id, 0)),
            _pedagogical_rank(skill, family_id),
            hashlib.sha256(
                f"{learner_id}|{session_id}|{reason}|{family_id}".encode("utf-8")
            ).hexdigest(),
            family_id,
        ),
    )
    ordered: list[dict[str, Any]] = []
    while True:
        added = False
        for family_id in family_order:
            if groups[family_id]:
                ordered.append(groups[family_id].pop(0))
                added = True
        if not added:
            break
    for row in ordered:
        for key in ("_plan_count", "_last_selected_at", "_last_exposure_seq"):
            row.pop(key, None)
    return ordered


def _assemble_session(
    self: qb02.Unit01ApprovedVariantSessionRuntime,
    *,
    learner_id: str,
    session_id: str,
    selected_at: str | None = None,
    selection_mode: str | None = None,
) -> dict[str, Any]:
    selected_at = _time(selected_at)
    _ensure_identity_schema(self)
    with self.write() as connection:
        metadata = dict(connection.execute("SELECT key,value FROM u01qb02_metadata"))
        if metadata.get("validation_status") != qb02.PASS_STATUS:
            raise IdentityFairSelectionError("u01qb02_not_initialized")
        session = self._active_session(connection, learner_id=learner_id, session_id=session_id)
        guest = _guest_scope_active(connection, learner_id=learner_id, at=selected_at)
        mode = str(selection_mode or ("FRESH" if guest else "ADAPTIVE")).upper()
        if mode not in SELECTION_MODES:
            raise IdentityFairSelectionError("selection_mode_invalid")
        if connection.execute(
            "SELECT 1 FROM u01qb02_session_plans WHERE session_id=?", (session_id,)
        ).fetchone():
            value = self._plan_payload(connection, session_id)
            value.update(
                {
                    "identity_mode": "GUEST" if guest else "AUTHENTICATED",
                    "selection_mode": mode,
                    "fair_selection_fullfix": True,
                }
            )
            return value
        catalog = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM u01qb02_item_catalog WHERE lesson_id=? ORDER BY item_id",
                (session["lesson_id"],),
            )
        ]
        if len(catalog) < qb02.SESSION_SIZE:
            raise IdentityFairSelectionError("insufficient_approved_items_for_session")
        history, planned, recent, family_counts = _history(
            connection,
            learner_id=learner_id,
            lesson_id=str(session["lesson_id"]),
        )
        latest_outcomes: dict[str, str] = {}
        for row in connection.execute(
            """SELECT c.item_id,r.outcome
            FROM response_attempts a
            JOIN scoring_results r USING(attempt_id)
            JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
            WHERE a.learner_id=? ORDER BY a.rowid DESC""",
            (learner_id,),
        ):
            latest_outcomes.setdefault(str(row["item_id"]), str(row["outcome"]))
        failed = {
            item_id
            for item_id, outcome in latest_outcomes.items()
            if outcome in qb02.FAIL_OUTCOMES
        }
        passed = {
            item_id
            for item_id, outcome in latest_outcomes.items()
            if outcome in qb02.PASS_OUTCOMES
        }
        selected: list[tuple[dict[str, Any], str, int]] = []
        selected_ids: set[str] = set()
        ordinal = 0

        def take(reason: str, candidates: Sequence[Mapping[str, Any]], count: int) -> None:
            nonlocal ordinal
            if count <= 0:
                return
            ordered = _fair_order(
                learner_id=learner_id,
                session_id=session_id,
                reason=reason,
                skill=str(session["skill"]),
                rows=candidates,
                history=history,
                family_counts=family_counts,
            )
            reason_count = 0
            for row in ordered:
                if reason_count >= count:
                    break
                item_id = str(row["item_id"])
                if item_id in selected_ids:
                    continue
                ordinal += 1
                selected.append((row, reason, ordinal))
                selected_ids.add(item_id)
                reason_count += 1

        if mode == "FRESH":
            take(
                "NEW_OR_UNSEEN",
                [row for row in catalog if row["item_id"] not in planned],
                qb02.SESSION_SIZE,
            )
        else:
            take(
                "REMEDIATION",
                [row for row in catalog if row["item_id"] in failed],
                qb02.SELECTION_QUOTA["REMEDIATION"],
            )
            take(
                "SCHEDULED_REVIEW",
                [
                    row
                    for row in catalog
                    if row["item_id"] in planned
                    and row["item_id"] not in failed
                    and row["item_id"] not in recent
                    and (row["item_id"] not in passed or row["item_id"] in passed)
                ],
                qb02.SELECTION_QUOTA["SCHEDULED_REVIEW"],
            )
            take(
                "TRANSFER",
                [
                    row
                    for row in catalog
                    if row["transfer_eligible"]
                    and row["item_id"] not in planned
                    and row["item_id"] not in recent
                ],
                qb02.SELECTION_QUOTA["TRANSFER"],
            )
            take(
                "GUIDED_EXTENSION",
                [
                    row
                    for row in catalog
                    if row["support_level"] == "GUIDED_EXTENSION"
                    and row["item_id"] not in planned
                    and row["item_id"] not in recent
                ],
                qb02.SELECTION_QUOTA["GUIDED_EXTENSION"],
            )
            take(
                "NEW_OR_UNSEEN",
                [
                    row
                    for row in catalog
                    if row["item_id"] not in planned
                    and row["item_id"] not in recent
                ],
                qb02.SELECTION_QUOTA["NEW_OR_UNSEEN"],
            )
        if len(selected) < qb02.SESSION_SIZE:
            unseen_exists = any(item["item_id"] not in planned for item in catalog)
            fallback = [
                row
                for row in catalog
                if row["item_id"] not in selected_ids
                and (
                    row["item_id"] not in recent
                    or row["item_id"] in failed
                    or not unseen_exists
                )
            ]
            take("FALLBACK", fallback, qb02.SESSION_SIZE - len(selected))
        if len(selected) != qb02.SESSION_SIZE:
            raise IdentityFairSelectionError(f"session_item_count_invalid:{len(selected)}")
        selected.sort(
            key=lambda value: (
                _pedagogical_rank(str(session["skill"]), str(value[0]["pattern_family_id"])),
                value[2],
                value[0]["item_id"],
            )
        )
        plan_core = {
            "session_id": session_id,
            "learner_id": learner_id,
            "lesson_id": session["lesson_id"],
            "skill": session["skill"],
            "selected_at": selected_at,
            "recent_exposure_window": qb02.RECENT_EXPOSURE_WINDOW,
            "items": [
                {"position": index, "item_id": row["item_id"], "reason": reason}
                for index, (row, reason, _ordinal) in enumerate(selected, 1)
            ],
            "source_bank_sha256": metadata["source_bank_artifact_sha256"],
        }
        plan_digest = qb02.digest(plan_core)
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
                metadata["source_bank_artifact_sha256"],
                plan_digest,
            ),
        )
        connection.executemany(
            "INSERT INTO u01qb02_session_items VALUES(?,?,?,?)",
            [
                (session_id, index, row["item_id"], reason)
                for index, (row, reason, _ordinal) in enumerate(selected, 1)
            ],
        )
        value = self._plan_payload(connection, session_id)
        value.update(
            {
                "identity_mode": "GUEST" if guest else "AUTHENTICATED",
                "selection_mode": mode,
                "fair_selection_fullfix": True,
                "planned_history_used": True,
                "phrase_before_sentence_order": True,
            }
        )
        return value


def fairness_readback(
    database: Path,
    *,
    learner_id: str,
    skill: str,
) -> dict[str, Any]:
    lesson_id = qb02.UNIT01_LESSONS[str(skill).upper()]
    with sqlite3.connect(Path(database)) as connection:
        connection.row_factory = sqlite3.Row
        total = int(
            connection.execute(
                "SELECT COUNT(*) FROM u01qb02_item_catalog WHERE lesson_id=?",
                (lesson_id,),
            ).fetchone()[0]
        )
        planned = int(
            connection.execute(
                """SELECT COUNT(DISTINCT si.item_id)
                FROM u01qb02_session_items si
                JOIN u01qb02_session_plans sp USING(session_id)
                WHERE sp.learner_id=? AND sp.lesson_id=?""",
                (learner_id, lesson_id),
            ).fetchone()[0]
        )
        sessions = int(
            connection.execute(
                "SELECT COUNT(*) FROM u01qb02_session_plans WHERE learner_id=? AND lesson_id=?",
                (learner_id, lesson_id),
            ).fetchone()[0]
        )
        distribution = {
            str(row["pattern_family_id"]): int(row["item_count"])
            for row in connection.execute(
                """SELECT c.pattern_family_id,COUNT(DISTINCT si.item_id) AS item_count
                FROM u01qb02_session_items si
                JOIN u01qb02_session_plans sp USING(session_id)
                JOIN u01qb02_item_catalog c USING(item_id)
                WHERE sp.learner_id=? AND sp.lesson_id=?
                GROUP BY c.pattern_family_id ORDER BY c.pattern_family_id""",
                (learner_id, lesson_id),
            )
        }
    return {
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "learner_id": learner_id,
        "skill": str(skill).upper(),
        "available_item_count": total,
        "distinct_planned_item_count": planned,
        "unplanned_item_count": total - planned,
        "session_count": sessions,
        "pattern_family_distribution": distribution,
        "same_identity_history_tracked": True,
        "parallel_question_bank_created": False,
        "parallel_selector_created": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def install_fullfix() -> None:
    qb02.Unit01ApprovedVariantSessionRuntime.initialize = _initialize
    qb02.Unit01ApprovedVariantSessionRuntime.assemble_session = _assemble_session


install_fullfix()
