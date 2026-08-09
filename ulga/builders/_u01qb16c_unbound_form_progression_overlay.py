"""Safely migrate only unbound Unit01 Reading form activities to U01QB16B choices.

U01QB16B improves task-angle composition for newly materialized blueprints, but
an already-cut-over V1.2.1 learner database still contains the historical
U01QB13 activity rows. This adapter closes that product gap without rewriting
completed learner evidence.

Before the existing U01QB13 whole-form assembler binds a Reading session, the
adapter may migrate that form's still-unbound Reading blueprint rows to the
current runtime-capacity-aware U01QB16B allocation. A form is globally frozen as
soon as any of its Reading activity IDs has appeared in a session binding. The
migration preserves activity IDs, form/scene/support identity, scoring status,
assessment status, learner attempts, session bindings, QuestionBank items and
all Unit02-24 state. Every changed row has an immutable before/after ledger.
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16b_task_angle_progression_adapter as progression
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)
from ulga.builders import (
    build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_allocation,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Learner-state-safe migration of only never-bound Unit01 Reading blueprint rows to the already-approved runtime-capacity-aware task-angle allocation; preserves completed bindings, attempts, scoring, QuestionBank identity, Unit02-24 content, audio, speaking scoring, and A2 lock."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB16C_ExistingProductUnboundFormProgressionOverlayMigration"
PASS_STATUS = "PASS_A1FS_V1_U01QB16C_EXISTING_PRODUCT_UNBOUND_FORM_PROGRESSION_OVERLAY_MIGRATION"
NEXT_SHORT_STEP = "A1FS-V1-U01QB16D_Unit01QuestionBankErrorDiagnosisAndRemediationIdentityClosure"

MIGRATION_TABLE = "u01qb16c_unbound_activity_migrations"
METADATA_TABLE = "u01qb16c_metadata"
_ORIGINAL_ASSEMBLE = matching.assemble_form_component
_INSTALLED = False


class UnboundFormProgressionMigrationError(ValueError):
    pass


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _required_tables_present(connection: sqlite3.Connection) -> bool:
    return all(
        _table_exists(connection, table)
        for table in (
            "learning_sessions",
            "u01qb02_session_plans",
            "u01qb13_blueprint_activities",
            "u01qb13_session_bindings",
            "u01qb02_item_catalog",
        )
    )


def _ddl(connection: sqlite3.Connection) -> None:
    connection.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS {METADATA_TABLE}(
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE}(
          activity_id TEXT PRIMARY KEY,
          form_ordinal INTEGER NOT NULL,
          original_task_angle TEXT NOT NULL,
          effective_task_angle TEXT NOT NULL,
          original_pattern_family_ids_json TEXT NOT NULL,
          effective_pattern_family_ids_json TEXT NOT NULL,
          original_activity_digest TEXT NOT NULL,
          effective_activity_digest TEXT NOT NULL,
          applied_at TEXT NOT NULL,
          migration_session_id TEXT NOT NULL
        );
        """
    )


def _session_row(
    connection: sqlite3.Connection,
    *,
    learner_id: str,
    session_id: str,
) -> Mapping[str, Any] | None:
    row = connection.execute(
        "SELECT session_id,learner_id,skill FROM learning_sessions WHERE session_id=? AND learner_id=?",
        (session_id, learner_id),
    ).fetchone()
    return dict(row) if row is not None else None


def _form_reading_rows(
    connection: sqlite3.Connection,
    form_ordinal: int,
) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """SELECT activity_id,form_ordinal,scene_ref_id,situation_family,
                      task_angle,support_level,pattern_family_ids_json,
                      scene_anchors_json,activity_digest
               FROM u01qb13_blueprint_activities
               WHERE form_ordinal=? AND skill='READING'
               ORDER BY scene_ref_id,activity_id""",
            (form_ordinal,),
        )
    ]


def _form_is_bound(connection: sqlite3.Connection, form_ordinal: int) -> bool:
    return connection.execute(
        """SELECT 1
           FROM u01qb13_session_bindings b
           JOIN u01qb13_blueprint_activities a ON a.activity_id=b.activity_id
           WHERE a.form_ordinal=? AND a.skill='READING'
           LIMIT 1""",
        (form_ordinal,),
    ).fetchone() is not None


def _migration_already_applied(connection: sqlite3.Connection, form_ordinal: int) -> bool:
    if not _table_exists(connection, MIGRATION_TABLE):
        return False
    return connection.execute(
        f"SELECT 1 FROM {MIGRATION_TABLE} WHERE form_ordinal=? LIMIT 1",
        (form_ordinal,),
    ).fetchone() is not None


def _prior_angles(
    connection: sqlite3.Connection,
    *,
    form_ordinal: int,
) -> dict[str, dict[str, set[str]]]:
    prior: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in connection.execute(
        """SELECT scene_ref_id,skill,task_angle
           FROM u01qb13_blueprint_activities
           WHERE form_ordinal<?
           ORDER BY form_ordinal,activity_id""",
        (form_ordinal,),
    ):
        prior[str(row["scene_ref_id"])][str(row["skill"])].add(str(row["task_angle"]))
    return prior


def _scene_infos(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["scene_ref_id"])].append(row)
    if len(grouped) != 4 or any(len(scene_rows) != 2 for scene_rows in grouped.values()):
        raise UnboundFormProgressionMigrationError(
            "READING_FORM_SCENE_ACTIVITY_DENOMINATOR_INVALID"
        )
    result: list[dict[str, Any]] = []
    for ref in sorted(grouped):
        scene_rows = grouped[ref]
        families = {str(row["situation_family"]) for row in scene_rows}
        supports = {str(row["support_level"]) for row in scene_rows}
        anchors = {
            str(anchor).casefold()
            for row in scene_rows
            for anchor in json.loads(str(row["scene_anchors_json"]))
        }
        if len(families) != 1 or len(supports) != 1 or not anchors:
            raise UnboundFormProgressionMigrationError(
                f"READING_FORM_SCENE_CONTRACT_INVALID:{ref}"
            )
        result.append(
            {
                "scene_ref_id": ref,
                "anchors": anchors,
                "situation_family": next(iter(families)),
            }
        )
    return result


def _migration_plan(
    database: Path,
    *,
    form_ordinal: int,
    rows: list[dict[str, Any]],
    prior: Mapping[str, Mapping[str, set[str]]],
) -> list[dict[str, str]]:
    supports = {str(row["support_level"]) for row in rows}
    if len(supports) != 1:
        raise UnboundFormProgressionMigrationError("READING_FORM_SUPPORT_DRIFT")
    support = next(iter(supports))
    catalog = runtime_allocation._catalog(Path(database))
    choices = runtime_allocation._solve_form_skill(
        support=support,
        skill="READING",
        scene_infos=_scene_infos(rows),
        prior_angles=prior,
        catalog=catalog,
    )

    by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_scene[str(row["scene_ref_id"])].append(row)

    plan: list[dict[str, str]] = []
    for ref in sorted(by_scene):
        activity_rows = sorted(by_scene[ref], key=lambda row: str(row["activity_id"]))
        angles = tuple(choices[ref])
        if len(angles) != len(activity_rows):
            raise UnboundFormProgressionMigrationError(
                f"READING_SCENE_CHOICE_DENOMINATOR_INVALID:{ref}"
            )
        for row, angle in zip(activity_rows, angles):
            families = tuple(u13.EXACT_SCORED_BINDINGS.get(("READING", str(angle)), ()))
            if not families:
                raise UnboundFormProgressionMigrationError(
                    f"READING_EFFECTIVE_ANGLE_BINDING_MISSING:{angle}"
                )
            effective_families_json = u13.canonical(list(families))
            original_angle = str(row["task_angle"])
            original_families_json = str(row["pattern_family_ids_json"])
            if original_angle == str(angle) and original_families_json == effective_families_json:
                continue
            effective_digest = u13.digest(
                {
                    "migration_task_id": TASK_ID,
                    "base_activity_id": str(row["activity_id"]),
                    "base_activity_digest": str(row["activity_digest"]),
                    "effective_task_angle": str(angle),
                    "effective_pattern_family_ids": list(families),
                }
            )
            plan.append(
                {
                    "activity_id": str(row["activity_id"]),
                    "original_task_angle": original_angle,
                    "effective_task_angle": str(angle),
                    "original_pattern_family_ids_json": original_families_json,
                    "effective_pattern_family_ids_json": effective_families_json,
                    "original_activity_digest": str(row["activity_digest"]),
                    "effective_activity_digest": effective_digest,
                }
            )
    return plan


def migrate_unbound_reading_form(
    database: Path,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    applied_at: str | None = None,
) -> dict[str, Any]:
    database = Path(database)
    if form_ordinal < 1 or form_ordinal > u13.FORM_COUNT:
        raise UnboundFormProgressionMigrationError("FORM_ORDINAL_INVALID")
    if not database.is_file():
        return {"status": PASS_STATUS, "action": "SKIP_DATABASE_MISSING", "changed": 0}

    # sqlite3.Connection's own context manager commits/rolls back but does not
    # close the connection.  Pair it with closing() so early-return paths cannot
    # retain a Windows handle on disposable learner DB snapshots.
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        if not _required_tables_present(connection):
            return {"status": PASS_STATUS, "action": "SKIP_SCHEMA_NOT_READY", "changed": 0}
        session = _session_row(
            connection, learner_id=learner_id, session_id=session_id
        )
        if session is None or str(session["skill"]).upper() != "READING":
            return {"status": PASS_STATUS, "action": "SKIP_NON_READING_OR_UNKNOWN_SESSION", "changed": 0}
        if connection.execute(
            "SELECT 1 FROM u01qb13_session_bindings WHERE session_id=? LIMIT 1",
            (session_id,),
        ).fetchone() is not None:
            return {"status": PASS_STATUS, "action": "SKIP_SESSION_ALREADY_BOUND", "changed": 0}
        if connection.execute(
            "SELECT 1 FROM u01qb02_session_plans WHERE session_id=? LIMIT 1",
            (session_id,),
        ).fetchone() is not None:
            return {"status": PASS_STATUS, "action": "SKIP_SESSION_ALREADY_PLANNED", "changed": 0}
        if _form_is_bound(connection, form_ordinal):
            return {"status": PASS_STATUS, "action": "SKIP_FORM_FROZEN_BY_PRIOR_BINDING", "changed": 0}
        if _migration_already_applied(connection, form_ordinal):
            return {"status": PASS_STATUS, "action": "REUSE_EXISTING_MIGRATION", "changed": 0}
        rows = _form_reading_rows(connection, form_ordinal)
        if len(rows) != u13.READING_PER_FORM:
            return {"status": PASS_STATUS, "action": "SKIP_BLUEPRINT_NOT_READY", "changed": 0}
        prior = _prior_angles(connection, form_ordinal=form_ordinal)

    plan = _migration_plan(
        database,
        form_ordinal=form_ordinal,
        rows=rows,
        prior=prior,
    )
    if not plan:
        return {"status": PASS_STATUS, "action": "NO_CHANGE_REQUIRED", "changed": 0}

    applied_at = u13.timestamp(applied_at)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        if _form_is_bound(connection, form_ordinal):
            connection.rollback()
            return {"status": PASS_STATUS, "action": "SKIP_FORM_FROZEN_BY_PRIOR_BINDING", "changed": 0}
        if connection.execute(
            "SELECT 1 FROM u01qb02_session_plans WHERE session_id=? LIMIT 1",
            (session_id,),
        ).fetchone() is not None:
            connection.rollback()
            return {"status": PASS_STATUS, "action": "SKIP_SESSION_ALREADY_PLANNED", "changed": 0}
        _ddl(connection)
        if _migration_already_applied(connection, form_ordinal):
            connection.rollback()
            return {"status": PASS_STATUS, "action": "REUSE_EXISTING_MIGRATION", "changed": 0}

        changed = 0
        for change in plan:
            cursor = connection.execute(
                """UPDATE u01qb13_blueprint_activities
                   SET task_angle=?,pattern_family_ids_json=?,activity_digest=?
                   WHERE activity_id=? AND activity_digest=?""",
                (
                    change["effective_task_angle"],
                    change["effective_pattern_family_ids_json"],
                    change["effective_activity_digest"],
                    change["activity_id"],
                    change["original_activity_digest"],
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise UnboundFormProgressionMigrationError(
                    f"BLUEPRINT_ACTIVITY_CONCURRENT_DRIFT:{change['activity_id']}"
                )
            connection.execute(
                f"""INSERT INTO {MIGRATION_TABLE}
                (activity_id,form_ordinal,original_task_angle,effective_task_angle,
                 original_pattern_family_ids_json,effective_pattern_family_ids_json,
                 original_activity_digest,effective_activity_digest,applied_at,migration_session_id)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    change["activity_id"],
                    form_ordinal,
                    change["original_task_angle"],
                    change["effective_task_angle"],
                    change["original_pattern_family_ids_json"],
                    change["effective_pattern_family_ids_json"],
                    change["original_activity_digest"],
                    change["effective_activity_digest"],
                    applied_at,
                    session_id,
                ),
            )
            changed += 1

        metadata = {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "base_blueprint_validation_status": u13.PASS_STATUS,
            "last_migrated_form_ordinal": str(form_ordinal),
            "last_changed_activity_count": str(changed),
            "completed_or_bound_activities_modified": "false",
            "learner_attempts_modified": "false",
            "questionbank_modified": "false",
            "unit02_to_unit24_modified": "false",
            "a2_unlocked": "false",
            "next_short_step": NEXT_SHORT_STEP,
        }
        connection.executemany(
            f"INSERT OR REPLACE INTO {METADATA_TABLE}(key,value) VALUES(?,?)",
            metadata.items(),
        )
        connection.commit()

    return {
        "status": PASS_STATUS,
        "action": "MIGRATED_UNBOUND_READING_FORM",
        "form_ordinal": form_ordinal,
        "changed": len(plan),
        "completed_or_bound_activities_modified": False,
        "learner_attempts_modified": False,
        "questionbank_modified": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def assemble_form_component(
    database,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    selected_at: str | None = None,
):
    migrate_unbound_reading_form(
        Path(database),
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=form_ordinal,
        applied_at=selected_at,
    )
    return _ORIGINAL_ASSEMBLE(
        database,
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=form_ordinal,
        selected_at=selected_at,
    )


def install() -> None:
    """Patch the existing matcher assembler so matching.install() keeps this wrapper."""
    global _INSTALLED
    if matching.assemble_form_component is assemble_form_component:
        _INSTALLED = True
        return
    if matching.assemble_form_component is not _ORIGINAL_ASSEMBLE:
        raise UnboundFormProgressionMigrationError(
            "U01QB13_MATCHER_ASSEMBLER_ALREADY_PATCHED_BY_OTHER_AUTHORITY"
        )
    matching.assemble_form_component = assemble_form_component
    _INSTALLED = True


def installed() -> bool:
    return _INSTALLED and matching.assemble_form_component is assemble_form_component
