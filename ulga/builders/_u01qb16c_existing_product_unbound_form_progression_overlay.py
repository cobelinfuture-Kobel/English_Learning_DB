"""Migrate only unbound Unit01 Reading blueprint rows to U01QB16B progression.

Already-cut-over A1FS V1.2.1 learner databases contain the U01QB13 twelve-form
blueprint. U01QB16B improves task-angle composition for newly materialized
blueprints, but a database cut over before U01QB16B still carries its older
persisted rows. This migration reconciles only Reading form components that have
never been bound to a learner session. Any form component with historical
U01QB13 bindings is preserved byte-for-byte at the activity-row level so
completed/active learner evidence keeps its original pedagogical interpretation.

The migration does not rebuild the 474-item QuestionBank, author content, replace
the U01QB13 runtime, change scoring, or rewrite learner-owned state. It reuses
the existing U01QB14R1 runtime-capacity solver with the installed U01QB16B
capacity-preserving capability preference.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb16b_task_angle_progression_adapter as u16b
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13,
)
from ulga.builders import (
    build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_allocation,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Deterministic in-place migration of only previously unbound U01QB13 Reading blueprint rows in an already-cut-over existing product database; historical bound activities, learner attempts, scoring, QuestionBank items, scenes, Unit02-24 content, audio, speaking scoring, and A2 state are preserved."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB16C_ExistingProductUnboundFormProgressionOverlayMigration"
PASS_STATUS = "PASS_A1FS_V1_U01QB16C_EXISTING_PRODUCT_UNBOUND_FORM_PROGRESSION_OVERLAY_MIGRATION"
NEXT_SHORT_STEP = "A1FS-V1-U01QB16_ProductionProgressionFullFixCloseout"

CUTOVER_TABLE = "u01qb15_product_consumer_cutover"
CUTOVER_PASS_STATUS = "PASS_A1FS_V1_U01QB15_PRODUCTION_CONSUMER_CUTOVER_AND_LEARNER_RUNTIME_INTEGRATION"
METADATA_TABLE = "u01qb16c_progression_overlay_metadata"
DETAIL_TABLE = "u01qb16c_progression_overlay_rows"
EXPECTED_RUNTIME_ITEMS = 474
EXPECTED_BLUEPRINT_ACTIVITIES = 240
EXPECTED_READING_ACTIVITIES = 96
EXPECTED_FORMS = 12

MIGRATION_SQL = f"""
CREATE TABLE IF NOT EXISTS {METADATA_TABLE}(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS {DETAIL_TABLE}(
  activity_id TEXT PRIMARY KEY,
  form_ordinal INTEGER NOT NULL,
  scene_ref_id TEXT NOT NULL,
  previous_task_angle TEXT NOT NULL,
  effective_task_angle TEXT NOT NULL,
  migration_state TEXT NOT NULL CHECK(migration_state IN ('PRESERVED_BOUND','UPDATED_UNBOUND','UNCHANGED_UNBOUND')),
  previous_activity_digest TEXT NOT NULL,
  effective_activity_digest TEXT NOT NULL,
  capability_class TEXT NOT NULL,
  migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class UnboundProgressionOverlayError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _table_digest(connection: sqlite3.Connection, table: str) -> str | None:
    if not _table_exists(connection, table):
        return None
    rows = [tuple(row) for row in connection.execute(f"SELECT * FROM {table}").fetchall()]
    rows.sort(key=repr)
    return digest(rows)


def _learner_owned_snapshot(connection: sqlite3.Connection) -> dict[str, str | None]:
    return {
        table: _table_digest(connection, table)
        for table in (
            "learner_profiles",
            "learning_sessions",
            "state_events",
            "response_attempts",
            "scoring_results",
            "human_review_queue",
        )
    }


def migration_applicable(database: Path) -> bool:
    path = Path(database)
    if not path.is_file():
        return False
    with closing(sqlite3.connect(path)) as connection:
        if not _table_exists(connection, CUTOVER_TABLE):
            return False
        metadata = dict(connection.execute(f"SELECT key,value FROM {CUTOVER_TABLE}"))
        return metadata.get("validation_status") == CUTOVER_PASS_STATUS


def migration_status(database: Path) -> dict[str, Any]:
    path = Path(database)
    if not path.is_file():
        return {"active": False, "reason": "DATABASE_MISSING"}
    with closing(sqlite3.connect(path)) as connection:
        if not _table_exists(connection, METADATA_TABLE):
            return {"active": False, "reason": "MIGRATION_METADATA_MISSING"}
        metadata = dict(connection.execute(f"SELECT key,value FROM {METADATA_TABLE}"))
    active = metadata.get("validation_status") == PASS_STATUS
    result: dict[str, Any] = {
        "active": active,
        "reason": "PASS" if active else "MIGRATION_STATUS_NOT_PASS",
        "validation_status": metadata.get("validation_status"),
    }
    for key in (
        "reading_activity_count",
        "preserved_bound_reading_activity_count",
        "updated_unbound_reading_activity_count",
        "unchanged_unbound_reading_activity_count",
        "preserved_bound_form_count",
        "migrated_unbound_form_count",
    ):
        if key in metadata:
            result[key] = int(metadata[key])
    return result


def _require_ready_database(connection: sqlite3.Connection) -> None:
    for table in (
        CUTOVER_TABLE,
        "u01qb02_item_catalog",
        "u01qb13_metadata",
        "u01qb13_blueprint_activities",
        "u01qb13_session_bindings",
    ):
        if not _table_exists(connection, table):
            raise UnboundProgressionOverlayError(f"REQUIRED_TABLE_MISSING:{table}")
    cutover = dict(connection.execute(f"SELECT key,value FROM {CUTOVER_TABLE}"))
    if cutover.get("validation_status") != CUTOVER_PASS_STATUS:
        raise UnboundProgressionOverlayError("U01QB15_CUTOVER_NOT_ACTIVE")
    u13_metadata = dict(connection.execute("SELECT key,value FROM u01qb13_metadata"))
    if u13_metadata.get("validation_status") != u13.PASS_STATUS:
        raise UnboundProgressionOverlayError("U01QB13_BLUEPRINT_NOT_ACTIVE")
    runtime_count = int(connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0])
    activity_count = int(connection.execute("SELECT COUNT(*) FROM u01qb13_blueprint_activities").fetchone()[0])
    form_count = int(
        connection.execute(
            "SELECT COUNT(DISTINCT form_ordinal) FROM u01qb13_blueprint_activities"
        ).fetchone()[0]
    )
    reading_count = int(
        connection.execute(
            "SELECT COUNT(*) FROM u01qb13_blueprint_activities WHERE skill='READING'"
        ).fetchone()[0]
    )
    if runtime_count != EXPECTED_RUNTIME_ITEMS:
        raise UnboundProgressionOverlayError(f"RUNTIME_ITEM_COUNT_INVALID:{runtime_count}")
    if activity_count != EXPECTED_BLUEPRINT_ACTIVITIES:
        raise UnboundProgressionOverlayError(f"BLUEPRINT_ACTIVITY_COUNT_INVALID:{activity_count}")
    if form_count != EXPECTED_FORMS:
        raise UnboundProgressionOverlayError(f"BLUEPRINT_FORM_COUNT_INVALID:{form_count}")
    if reading_count != EXPECTED_READING_ACTIVITIES:
        raise UnboundProgressionOverlayError(f"READING_ACTIVITY_COUNT_INVALID:{reading_count}")


def _reading_rows(connection: sqlite3.Connection, form_ordinal: int) -> list[dict[str, Any]]:
    connection.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in connection.execute(
            """SELECT * FROM u01qb13_blueprint_activities
               WHERE form_ordinal=? AND skill='READING'
               ORDER BY activity_id""",
            (form_ordinal,),
        ).fetchall()
    ]
    if len(rows) != 8:
        raise UnboundProgressionOverlayError(
            f"FORM_READING_ACTIVITY_COUNT_INVALID:{form_ordinal}:{len(rows)}"
        )
    return rows


def _scene_groups(rows: Sequence[Mapping[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    order: list[str] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for source in rows:
        row = dict(source)
        ref = str(row["scene_ref_id"])
        if ref not in grouped:
            order.append(ref)
            grouped[ref] = []
        grouped[ref].append(row)
    if len(order) != 4:
        raise UnboundProgressionOverlayError(f"FORM_READING_SCENE_COUNT_INVALID:{len(order)}")
    result = []
    for ref in order:
        scene_rows = grouped[ref]
        if len(scene_rows) != 2:
            raise UnboundProgressionOverlayError(
                f"SCENE_READING_ACTIVITY_COUNT_INVALID:{ref}:{len(scene_rows)}"
            )
        result.append((ref, scene_rows))
    return result


def _scene_infos(groups: Sequence[tuple[str, Sequence[Mapping[str, Any]]]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for ref, rows in groups:
        first = rows[0]
        anchors = {str(value).casefold() for value in json.loads(str(first["scene_anchors_json"]))}
        if not anchors:
            raise UnboundProgressionOverlayError(f"SCENE_ANCHORS_MISSING:{ref}")
        result.append(
            {
                "scene_ref_id": ref,
                "anchors": anchors,
                "situation_family": str(first["situation_family"]),
                "setting": str(first["setting"]),
            }
        )
    return result


def _bound_activity_ids(connection: sqlite3.Connection, activity_ids: Sequence[str]) -> set[str]:
    placeholders = ",".join("?" for _ in activity_ids)
    rows = connection.execute(
        f"SELECT DISTINCT activity_id FROM u01qb13_session_bindings WHERE activity_id IN ({placeholders})",
        tuple(activity_ids),
    ).fetchall()
    return {str(row[0]) for row in rows}


def _effective_activity_digest(row: Mapping[str, Any], *, angle: str, families_json: str) -> str:
    return digest(
        {
            "activity_id": str(row["activity_id"]),
            "form_id": str(row["form_id"]),
            "form_ordinal": int(row["form_ordinal"]),
            "scene_ref_id": str(row["scene_ref_id"]),
            "situation_family": str(row["situation_family"]),
            "setting": str(row["setting"]),
            "skill": str(row["skill"]),
            "task_angle": angle,
            "support_level": str(row["support_level"]),
            "scored": int(row["scored"]),
            "assessment_candidate": int(row["assessment_candidate"]),
            "pattern_family_ids_json": families_json,
            "scene_anchors_json": str(row["scene_anchors_json"]),
            "practice_projection_json": str(row["practice_projection_json"]),
        }
    )


def _record_detail(
    connection: sqlite3.Connection,
    *,
    row: Mapping[str, Any],
    effective_angle: str,
    migration_state: str,
    effective_digest: str,
) -> None:
    connection.execute(
        f"""INSERT OR REPLACE INTO {DETAIL_TABLE}
            (activity_id,form_ordinal,scene_ref_id,previous_task_angle,effective_task_angle,
             migration_state,previous_activity_digest,effective_activity_digest,capability_class,migrated_at)
            VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
        (
            str(row["activity_id"]),
            int(row["form_ordinal"]),
            str(row["scene_ref_id"]),
            str(row["task_angle"]),
            effective_angle,
            migration_state,
            str(row["activity_digest"]),
            effective_digest,
            u16b.capability_class("READING", effective_angle),
        ),
    )


def ensure_migrated(database: Path) -> dict[str, Any]:
    """Apply U01QB16B only to globally unbound Reading form components."""
    database = Path(database)
    existing = migration_status(database)
    if existing.get("active") is True:
        return {"validation_status": PASS_STATUS, "idempotent_reuse": True, **existing}
    if not migration_applicable(database):
        raise UnboundProgressionOverlayError("U01QB15_CUTOVER_NOT_ACTIVE")
    if not u16b.installed():
        u16b.install()

    # Build the active catalog before opening the migration write transaction.
    catalog = runtime_allocation._catalog(database)
    prior_angles: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    preserved_bound_activity_count = 0
    updated_unbound_activity_count = 0
    unchanged_unbound_activity_count = 0
    preserved_bound_form_count = 0
    migrated_unbound_form_count = 0

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        _require_ready_database(connection)
        learner_before = _learner_owned_snapshot(connection)
        connection.executescript(MIGRATION_SQL)
        connection.execute(f"DELETE FROM {DETAIL_TABLE}")

        for form_ordinal in range(1, EXPECTED_FORMS + 1):
            rows = _reading_rows(connection, form_ordinal)
            groups = _scene_groups(rows)
            activity_ids = [str(row["activity_id"]) for row in rows]
            bound_ids = _bound_activity_ids(connection, activity_ids)
            if bound_ids:
                if bound_ids != set(activity_ids):
                    raise UnboundProgressionOverlayError(
                        f"PARTIAL_READING_FORM_BINDING:{form_ordinal}:{len(bound_ids)}"
                    )
                preserved_bound_form_count += 1
                preserved_bound_activity_count += len(rows)
                for _ref, scene_rows in groups:
                    for row in scene_rows:
                        angle = str(row["task_angle"])
                        prior_angles[str(row["scene_ref_id"])]["READING"].add(angle)
                        _record_detail(
                            connection,
                            row=row,
                            effective_angle=angle,
                            migration_state="PRESERVED_BOUND",
                            effective_digest=str(row["activity_digest"]),
                        )
                continue

            support_levels = {str(row["support_level"]) for row in rows}
            if len(support_levels) != 1:
                raise UnboundProgressionOverlayError(
                    f"FORM_READING_SUPPORT_DRIFT:{form_ordinal}:{','.join(sorted(support_levels))}"
                )
            support = next(iter(support_levels))
            choices = runtime_allocation._solve_form_skill(
                support=support,
                skill="READING",
                scene_infos=_scene_infos(groups),
                prior_angles=prior_angles,
                catalog=catalog,
            )
            migrated_unbound_form_count += 1

            for ref, scene_rows in groups:
                selected = tuple(choices.get(ref) or ())
                if len(selected) != 2:
                    raise UnboundProgressionOverlayError(
                        f"FORM_READING_CHOICE_COUNT_INVALID:{form_ordinal}:{ref}:{len(selected)}"
                    )
                for row, angle in zip(scene_rows, selected):
                    families = tuple(u13.EXACT_SCORED_BINDINGS.get(("READING", angle), ()))
                    if not families:
                        raise UnboundProgressionOverlayError(
                            f"READING_EXACT_BINDING_MISSING:{form_ordinal}:{ref}:{angle}"
                        )
                    families_json = canonical(list(families))
                    effective_digest = _effective_activity_digest(
                        row, angle=angle, families_json=families_json
                    )
                    changed = (
                        str(row["task_angle"]) != angle
                        or str(row["pattern_family_ids_json"]) != families_json
                    )
                    if changed:
                        connection.execute(
                            """UPDATE u01qb13_blueprint_activities
                               SET task_angle=?,pattern_family_ids_json=?,activity_digest=?
                               WHERE activity_id=?""",
                            (angle, families_json, effective_digest, str(row["activity_id"])),
                        )
                        updated_unbound_activity_count += 1
                        state = "UPDATED_UNBOUND"
                    else:
                        unchanged_unbound_activity_count += 1
                        effective_digest = str(row["activity_digest"])
                        state = "UNCHANGED_UNBOUND"
                    _record_detail(
                        connection,
                        row=row,
                        effective_angle=angle,
                        migration_state=state,
                        effective_digest=effective_digest,
                    )
                    prior_angles[ref]["READING"].add(angle)

        migrated_total = (
            preserved_bound_activity_count
            + updated_unbound_activity_count
            + unchanged_unbound_activity_count
        )
        if migrated_total != EXPECTED_READING_ACTIVITIES:
            raise UnboundProgressionOverlayError(
                f"READING_MIGRATION_DENOMINATOR_INVALID:{migrated_total}"
            )
        if int(connection.execute(f"SELECT COUNT(*) FROM {DETAIL_TABLE}").fetchone()[0]) != EXPECTED_READING_ACTIVITIES:
            raise UnboundProgressionOverlayError("MIGRATION_DETAIL_DENOMINATOR_INVALID")
        learner_after = _learner_owned_snapshot(connection)
        if learner_after != learner_before:
            raise UnboundProgressionOverlayError("LEARNER_OWNED_STATE_CHANGED")

        metadata = {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "source_progression_task_id": u16b.TASK_ID,
            "reading_activity_count": str(EXPECTED_READING_ACTIVITIES),
            "preserved_bound_reading_activity_count": str(preserved_bound_activity_count),
            "updated_unbound_reading_activity_count": str(updated_unbound_activity_count),
            "unchanged_unbound_reading_activity_count": str(unchanged_unbound_activity_count),
            "preserved_bound_form_count": str(preserved_bound_form_count),
            "migrated_unbound_form_count": str(migrated_unbound_form_count),
            "learner_owned_state_unchanged": "true",
            "historical_bound_activities_preserved": "true",
            "questionbank_item_count": str(EXPECTED_RUNTIME_ITEMS),
            "blueprint_activity_count": str(EXPECTED_BLUEPRINT_ACTIVITIES),
            "unit02_to_unit24_modified": "false",
            "speaking_scoring_enabled": "false",
            "a2_unlocked": "false",
            "next_short_step": NEXT_SHORT_STEP,
        }
        connection.executemany(
            f"INSERT OR REPLACE INTO {METADATA_TABLE}(key,value) VALUES(?,?)",
            metadata.items(),
        )

    status = migration_status(database)
    if status.get("active") is not True:
        raise UnboundProgressionOverlayError("MIGRATION_POSTCHECK_NOT_ACTIVE")
    return {
        "validation_status": PASS_STATUS,
        "idempotent_reuse": False,
        **status,
        "learner_owned_state_unchanged": True,
        "historical_bound_activities_preserved": True,
        "questionbank_unchanged": True,
        "unit02_to_unit24_modified": False,
        "speaking_scoring_enabled": False,
        "a2_unlocked": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
