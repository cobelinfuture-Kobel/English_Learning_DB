"""Repair unbound Unit01 Writing blueprint rows against the formal product selector.

R4 production evidence exposed a historical allocation/product-execution parity gap:
U01QB14R1 proved Writing task capacity with family + noun/context + item identity,
while the current product selector additionally requires canonical response-contract
scoring class, learner-content quality, and learner-visible distinctness.

This product-scoped adapter changes no QuestionBank item and no bound learner evidence.
Immediately before an unbound Writing component is assembled, it first proves the
persisted eight Writing activities against the *current* formal selector predicates.
Only when that exact form is no longer executable does it deterministically choose a
replacement pair of already-approved U01QB09 Writing task angles per scene, preserving
support, scene, activity identity, scoring/assessment flags, prior-scene angle
progression and whole-form learner-visible distinctness.  The migration is fail-closed,
ledgered, and never touches a Writing form once any Writing activity in that form has
been bound.
"""
from __future__ import annotations

import itertools
import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as visible
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb18c_form01_learner_quality_adapter as quality
from ulga.builders import (
    build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u09,
)
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Learner-state-safe product selector parity repair over existing Unit01 Writing "
    "blueprint rows. It uses only existing U01QB09 task angles and the existing 474-item "
    "QuestionBank, canonical response contracts, learner-quality gate, scene/context "
    "binding and learner-visible distinct matcher; it authors no content, changes no "
    "bound evidence, creates no planner/runtime/scoring/database authority, modifies no "
    "Unit02-24 content, enables no audio/Speaking score, and unlocks no A2."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R2_Unit01UnboundWritingFormalSelectorParityFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R2_UNBOUND_WRITING_FORMAL_SELECTOR_PARITY_FULLFIX"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18F-R4_ActualTwelveFormFullSemanticLanguagePedagogicalReplay"

MIGRATION_TABLE = "u01qb18f_r4r2_unbound_writing_migrations"
METADATA_TABLE = "u01qb18f_r4r2_metadata"
_INSTALLED = False
_ORIGINAL_ASSEMBLE = None


class WritingSelectorParityError(ValueError):
    """Fail-closed unbound-Writing selector parity error."""


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
            "u01qb02_item_exposures",
            "u01qb13_blueprint_activities",
            "u01qb13_session_bindings",
            "u01qb02_item_catalog",
            "response_contracts",
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
) -> dict[str, Any] | None:
    row = connection.execute(
        """SELECT session_id,learner_id,lesson_id,skill
           FROM learning_sessions
           WHERE session_id=? AND learner_id=?""",
        (session_id, learner_id),
    ).fetchone()
    return dict(row) if row is not None else None


def _form_writing_rows(
    connection: sqlite3.Connection,
    form_ordinal: int,
) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """SELECT activity_id,form_id,form_ordinal,scene_ref_id,situation_family,
                      setting,skill,task_angle,support_level,scored,
                      assessment_candidate,pattern_family_ids_json,
                      scene_anchors_json,activity_digest
               FROM u01qb13_blueprint_activities
               WHERE form_ordinal=? AND skill='WRITING'
               ORDER BY scene_ref_id,activity_id""",
            (form_ordinal,),
        )
    ]


def _writing_form_is_bound(connection: sqlite3.Connection, form_ordinal: int) -> bool:
    return connection.execute(
        """SELECT 1
           FROM u01qb13_session_bindings b
           JOIN u01qb13_blueprint_activities a ON a.activity_id=b.activity_id
           WHERE a.form_ordinal=? AND a.skill='WRITING'
           LIMIT 1""",
        (form_ordinal,),
    ).fetchone() is not None


def _migration_already_applied(
    connection: sqlite3.Connection, form_ordinal: int
) -> bool:
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
        prior[str(row["scene_ref_id"])][str(row["skill"])].add(
            str(row["task_angle"])
        )
    return prior


def _runtime_state(
    connection: sqlite3.Connection,
    *,
    learner_id: str,
    session_id: str,
    lesson_id: str,
) -> tuple[
    list[dict[str, Any]],
    dict[str, str],
    set[str],
    set[str],
]:
    catalog = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM u01qb02_item_catalog WHERE lesson_id=? ORDER BY item_id",
            (lesson_id,),
        )
    ]
    scoring = matching.load_runtime_item_scoring_classes(
        connection, lesson_id=lesson_id
    )
    if set(scoring) != {str(row["item_id"]) for row in catalog}:
        raise WritingSelectorParityError(
            "RUNTIME_SCORING_CLASS_CATALOG_IDENTITY_MISMATCH"
        )
    exposed = {
        str(row[0])
        for row in connection.execute(
            "SELECT DISTINCT item_id FROM u01qb02_item_exposures WHERE learner_id=?",
            (learner_id,),
        )
    }
    recent = {
        str(row[0])
        for row in connection.execute(
            """SELECT item_id FROM u01qb02_item_exposures
               WHERE learner_id=? ORDER BY exposure_seq DESC LIMIT ?""",
            (learner_id, u13.qb02.RECENT_EXPOSURE_WINDOW),
        )
    }
    return catalog, scoring, exposed, recent


def _candidate_pairs(
    activity: Mapping[str, Any],
    *,
    catalog: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, str],
    learner_id: str,
    session_id: str,
    exposed: set[str],
    recent: set[str],
) -> list[tuple[tuple[Any, ...], Mapping[str, Any]]]:
    allowed = set(json.loads(str(activity["pattern_family_ids_json"])))
    anchors = {
        str(value).casefold()
        for value in json.loads(str(activity["scene_anchors_json"]))
    }
    result: list[tuple[tuple[Any, ...], Mapping[str, Any]]] = []
    for row in catalog:
        if str(row["pattern_family_id"]) not in allowed:
            continue
        if not matching.candidate_preserves_scoring_class(activity, row, scoring):
            continue
        rank = u13._candidate_rank(
            row=row,
            anchors=anchors,
            situation_family=str(activity["situation_family"]),
            learner_id=learner_id,
            session_id=session_id,
            activity_id=str(activity["activity_id"]),
            exposed=exposed,
            recent=recent,
            assessment=bool(activity["assessment_candidate"]),
            scene_ref_id=str(activity["scene_ref_id"]),
        )
        if rank is not None:
            result.append((tuple(rank), row))
    return result


def _formal_assignment_exists(
    activities: Sequence[Mapping[str, Any]],
    *,
    catalog: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, str],
    learner_id: str,
    session_id: str,
    exposed: set[str],
    recent: set[str],
) -> bool:
    candidates: dict[str, list[tuple[tuple[Any, ...], Mapping[str, Any]]]] = {}
    for activity in activities:
        pairs = _candidate_pairs(
            activity,
            catalog=catalog,
            scoring=scoring,
            learner_id=learner_id,
            session_id=session_id,
            exposed=exposed,
            recent=recent,
        )
        if not pairs:
            return False
        candidates[str(activity["activity_id"])] = pairs
    try:
        matching.solve_distinct_activity_assignment(candidates)
    except matching.DistinctItemMatchingError:
        return False
    return True


def _angle_row(source: Mapping[str, Any], angle: str) -> dict[str, Any]:
    families = tuple(u13.EXACT_SCORED_BINDINGS.get(("WRITING", str(angle)), ()))
    if not families:
        raise WritingSelectorParityError(
            f"WRITING_EFFECTIVE_ANGLE_BINDING_MISSING:{angle}"
        )
    value = dict(source)
    value["task_angle"] = str(angle)
    value["pattern_family_ids_json"] = u13.canonical(list(families))
    return value


def _scene_options(
    rows: Sequence[Mapping[str, Any]],
    *,
    prior: set[str],
) -> list[list[dict[str, Any]]]:
    if len(rows) != 2:
        raise WritingSelectorParityError("WRITING_SCENE_ACTIVITY_DENOMINATOR_INVALID")
    supports = {str(row["support_level"]) for row in rows}
    if len(supports) != 1:
        raise WritingSelectorParityError("WRITING_SCENE_SUPPORT_DRIFT")
    support = next(iter(supports))
    profile = [
        str(angle)
        for angle in u09.SUPPORT_PROFILES[support]["candidates"]["WRITING"]
        if str(angle) not in prior
        and u13.EXACT_SCORED_BINDINGS.get(("WRITING", str(angle)))
    ]
    if len(profile) < 2:
        raise WritingSelectorParityError(
            f"WRITING_UNREPEATED_ANGLE_CAPACITY_INSUFFICIENT:{support}"
        )
    ordered_rows = sorted((dict(row) for row in rows), key=lambda row: str(row["activity_id"]))
    profile_index = {angle: index for index, angle in enumerate(profile)}
    options: list[tuple[tuple[Any, ...], list[dict[str, Any]]]] = []
    for angles in itertools.combinations(profile, 2):
        for assignment in itertools.permutations(angles):
            proposed = [
                _angle_row(row, angle)
                for row, angle in zip(ordered_rows, assignment)
            ]
            changed = sum(
                str(before["task_angle"]) != str(after["task_angle"])
                for before, after in zip(ordered_rows, proposed)
            )
            key = (
                changed,
                tuple(profile_index[str(after["task_angle"])] for after in proposed),
                tuple(str(after["task_angle"]) for after in proposed),
            )
            options.append((key, proposed))
    options.sort(key=lambda row: row[0])
    return [rows for _key, rows in options]


def _choose_form_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    prior: Mapping[str, Mapping[str, set[str]]],
    catalog: Sequence[Mapping[str, Any]],
    scoring: Mapping[str, str],
    learner_id: str,
    session_id: str,
    exposed: set[str],
    recent: set[str],
) -> list[dict[str, Any]]:
    current = [dict(row) for row in rows]
    if _formal_assignment_exists(
        current,
        catalog=catalog,
        scoring=scoring,
        learner_id=learner_id,
        session_id=session_id,
        exposed=exposed,
        recent=recent,
    ):
        return current

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in current:
        grouped[str(row["scene_ref_id"])].append(row)
    if len(grouped) != u13.SCENES_PER_FORM or any(
        len(scene_rows) != 2 for scene_rows in grouped.values()
    ):
        raise WritingSelectorParityError(
            "WRITING_FORM_SCENE_ACTIVITY_DENOMINATOR_INVALID"
        )

    scene_refs = sorted(grouped)
    options_by_scene = {
        ref: _scene_options(
            grouped[ref],
            prior=set(prior.get(ref, {}).get("WRITING", set())),
        )
        for ref in scene_refs
    }
    chosen: list[dict[str, Any]] = []

    def solve(index: int) -> bool:
        if index == len(scene_refs):
            return _formal_assignment_exists(
                chosen,
                catalog=catalog,
                scoring=scoring,
                learner_id=learner_id,
                session_id=session_id,
                exposed=exposed,
                recent=recent,
            )
        ref = scene_refs[index]
        for option in options_by_scene[ref]:
            start = len(chosen)
            chosen.extend(option)
            if _formal_assignment_exists(
                chosen,
                catalog=catalog,
                scoring=scoring,
                learner_id=learner_id,
                session_id=session_id,
                exposed=exposed,
                recent=recent,
            ) and solve(index + 1):
                return True
            del chosen[start:]
        return False

    if not solve(0):
        detail = ";".join(
            f"{ref}={len(options_by_scene[ref])}" for ref in scene_refs
        )
        raise WritingSelectorParityError(
            "UNBOUND_WRITING_FORM_FORMAL_SELECTOR_CAPACITY_UNSAT:" + detail
        )
    return sorted(chosen, key=lambda row: str(row["activity_id"]))


def _migration_plan(
    database: Path,
    *,
    learner_id: str,
    session_id: str,
    rows: Sequence[Mapping[str, Any]],
    prior: Mapping[str, Mapping[str, set[str]]],
) -> list[dict[str, str]]:
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        session = _session_row(
            connection, learner_id=learner_id, session_id=session_id
        )
        if session is None:
            raise WritingSelectorParityError("WRITING_SESSION_NOT_FOUND")
        catalog, scoring, exposed, recent = _runtime_state(
            connection,
            learner_id=learner_id,
            session_id=session_id,
            lesson_id=str(session["lesson_id"]),
        )

    chosen = _choose_form_rows(
        rows,
        prior=prior,
        catalog=catalog,
        scoring=scoring,
        learner_id=learner_id,
        session_id=session_id,
        exposed=exposed,
        recent=recent,
    )
    original_by_id = {str(row["activity_id"]): dict(row) for row in rows}
    plan: list[dict[str, str]] = []
    for effective in chosen:
        activity_id = str(effective["activity_id"])
        original = original_by_id[activity_id]
        original_angle = str(original["task_angle"])
        effective_angle = str(effective["task_angle"])
        original_families = str(original["pattern_family_ids_json"])
        effective_families = str(effective["pattern_family_ids_json"])
        if original_angle == effective_angle and original_families == effective_families:
            continue
        effective_digest = u13.digest(
            {
                "migration_task_id": TASK_ID,
                "base_activity_id": activity_id,
                "base_activity_digest": str(original["activity_digest"]),
                "effective_task_angle": effective_angle,
                "effective_pattern_family_ids": json.loads(effective_families),
            }
        )
        plan.append(
            {
                "activity_id": activity_id,
                "original_task_angle": original_angle,
                "effective_task_angle": effective_angle,
                "original_pattern_family_ids_json": original_families,
                "effective_pattern_family_ids_json": effective_families,
                "original_activity_digest": str(original["activity_digest"]),
                "effective_activity_digest": effective_digest,
            }
        )
    return sorted(plan, key=lambda row: row["activity_id"])


def migrate_unbound_writing_form(
    database: Path,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    applied_at: str | None = None,
) -> dict[str, Any]:
    database = Path(database)
    if form_ordinal < 1 or form_ordinal > u13.FORM_COUNT:
        raise WritingSelectorParityError("FORM_ORDINAL_INVALID")
    if not database.is_file():
        return {"status": PASS_STATUS, "action": "SKIP_DATABASE_MISSING", "changed": 0}

    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        if not _required_tables_present(connection):
            return {"status": PASS_STATUS, "action": "SKIP_SCHEMA_NOT_READY", "changed": 0}
        session = _session_row(
            connection, learner_id=learner_id, session_id=session_id
        )
        if session is None or str(session["skill"]).upper() != "WRITING":
            return {"status": PASS_STATUS, "action": "SKIP_NON_WRITING_OR_UNKNOWN_SESSION", "changed": 0}
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
        if _writing_form_is_bound(connection, form_ordinal):
            return {"status": PASS_STATUS, "action": "SKIP_WRITING_FORM_FROZEN_BY_PRIOR_BINDING", "changed": 0}
        if _migration_already_applied(connection, form_ordinal):
            return {"status": PASS_STATUS, "action": "REUSE_EXISTING_MIGRATION", "changed": 0}
        rows = _form_writing_rows(connection, form_ordinal)
        if len(rows) != u13.WRITING_PER_FORM:
            return {"status": PASS_STATUS, "action": "SKIP_BLUEPRINT_NOT_READY", "changed": 0}
        prior = _prior_angles(connection, form_ordinal=form_ordinal)

    plan = _migration_plan(
        database,
        learner_id=learner_id,
        session_id=session_id,
        rows=rows,
        prior=prior,
    )
    if not plan:
        return {
            "status": PASS_STATUS,
            "action": "FORMAL_SELECTOR_PARITY_ALREADY_PASS",
            "form_ordinal": form_ordinal,
            "changed": 0,
        }

    applied_at = u13.timestamp(applied_at)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        if _writing_form_is_bound(connection, form_ordinal):
            connection.rollback()
            return {"status": PASS_STATUS, "action": "SKIP_WRITING_FORM_FROZEN_BY_PRIOR_BINDING", "changed": 0}
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
                raise WritingSelectorParityError(
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
            "last_migrated_form_ordinal": str(form_ordinal),
            "last_changed_activity_count": str(changed),
            "formal_selector_predicates": "scoring_class+learner_quality+scene_context+learner_visible_distinctness",
            "bound_writing_activities_modified": "false",
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
        "action": "MIGRATED_UNBOUND_WRITING_FORM_TO_FORMAL_SELECTOR_PARITY",
        "form_ordinal": form_ordinal,
        "changed": len(plan),
        "changes": [
            {
                "activity_id": row["activity_id"],
                "from": row["original_task_angle"],
                "to": row["effective_task_angle"],
            }
            for row in plan
        ],
        "bound_writing_activities_modified": False,
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
    migrate_unbound_writing_form(
        Path(database),
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=form_ordinal,
        applied_at=selected_at,
    )
    if _ORIGINAL_ASSEMBLE is None:
        raise WritingSelectorParityError("ORIGINAL_ASSEMBLER_NOT_CAPTURED")
    return _ORIGINAL_ASSEMBLE(
        database,
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=form_ordinal,
        selected_at=selected_at,
    )


def install() -> None:
    """Wrap the existing U16C assembler after product quality gates are installed."""
    global _INSTALLED, _ORIGINAL_ASSEMBLE
    if matching.assemble_form_component is assemble_form_component:
        _INSTALLED = True
        return
    if not u16c.installed():
        raise WritingSelectorParityError("U01QB16C_REQUIRED_BEFORE_R4R2")
    if not visible.installed():
        raise WritingSelectorParityError("U01QB16_VISIBLE_DISTINCTNESS_REQUIRED_BEFORE_R4R2")
    if not quality.installed():
        raise WritingSelectorParityError("U01QB18C_LEARNER_QUALITY_REQUIRED_BEFORE_R4R2")
    if matching.assemble_form_component is not u16c.assemble_form_component:
        raise WritingSelectorParityError(
            "U01QB13_ASSEMBLER_ALREADY_PATCHED_BY_OTHER_AUTHORITY"
        )
    if (
        matching.candidate_preserves_scoring_class
        is not quality.candidate_preserves_scoring_class_with_learner_quality
    ):
        raise WritingSelectorParityError("FORMAL_CANDIDATE_QUALITY_GATE_NOT_ACTIVE")
    _ORIGINAL_ASSEMBLE = matching.assemble_form_component
    matching.assemble_form_component = assemble_form_component
    _INSTALLED = True


def installed() -> bool:
    return (
        _INSTALLED
        and _ORIGINAL_ASSEMBLE is u16c.assemble_form_component
        and matching.assemble_form_component is assemble_form_component
        and matching.candidate_preserves_scoring_class
        is quality.candidate_preserves_scoring_class_with_learner_quality
        and visible.installed()
        and quality.installed()
        and u16c.installed()
    )
