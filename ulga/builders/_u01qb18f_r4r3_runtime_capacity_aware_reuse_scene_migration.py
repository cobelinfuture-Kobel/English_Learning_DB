"""Repair an unbound Unit01 reused scene when its frozen task-angle contract is runtime-unsatisfiable.

U01QB08/U14R1 selected spiral-reuse scenes before the final 474-item runtime was
known.  U01QB09 correctly forbids same-scene / same-skill / same-task-angle
replay, so a scene selected for two exposures must have enough executable task
angles for both exposures.  Actual Forms01..12 replay exposed a legal scene
(U01-MA-SHOP-04) whose second Reading exposure had only one unused executable
angle although two are required.

This product migration does not relax the no-repeat pedagogy and does not author
questions or scenes.  Before the first binding in an otherwise-unbound form it
may transfer that *second-exposure slot* to an already-existing, same-family,
single-exposure Unit01 scene with sufficient runtime capacity.  The failing
scene remains in the course once; the replacement becomes the reused scene, so
total exposures, distinct scene identity and family composition are preserved.
Reading and Writing task-angle replanning remains owned by U16C/R4R2.  This
migration only changes the scene package and, for Speaking (which has no later
migration), selects one executable unrepeated speaking angle.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u08
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u09
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13
from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_allocation

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Learner-state-safe reuse-slot migration over already-approved Unit01 scenes and "
    "the existing 474-item runtime. It preserves the frozen no-repeat pedagogy, scene "
    "authority, QuestionBank, scoring/runtime/planner/database authorities, bound "
    "learner evidence, Unit02-24, audio, Speaking scoring and A2 lock; no content is authored."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R3_RuntimeCapacityAwareReuseSceneRotationFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R3_RUNTIME_CAPACITY_AWARE_REUSE_SCENE_ROTATION_FULLFIX"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18F-R4_ActualTwelveFormFullSemanticLanguagePedagogicalReplay"

MIGRATION_TABLE = "u01qb18f_r4r3_reuse_scene_migrations"
METADATA_TABLE = "u01qb18f_r4r3_metadata"
_CAPACITY_PREFIX = "SCENE_RUNTIME_TASK_ANGLE_CAPACITY_INSUFFICIENT:"


class RuntimeReuseSceneMigrationError(ValueError):
    """Fail-closed runtime-capacity-aware scene reuse migration error."""


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
            "u01qb12_metadata",
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
          original_scene_ref_id TEXT NOT NULL,
          effective_scene_ref_id TEXT NOT NULL,
          original_activity_digest TEXT NOT NULL,
          effective_activity_digest TEXT NOT NULL,
          applied_at TEXT NOT NULL,
          migration_session_id TEXT NOT NULL
        );
        """
    )


def _session_exists(
    connection: sqlite3.Connection, *, learner_id: str, session_id: str
) -> bool:
    return connection.execute(
        "SELECT 1 FROM learning_sessions WHERE session_id=? AND learner_id=?",
        (session_id, learner_id),
    ).fetchone() is not None


def _form_has_binding(connection: sqlite3.Connection, form_ordinal: int) -> bool:
    return connection.execute(
        """SELECT 1
           FROM u01qb13_session_bindings b
           JOIN u01qb13_blueprint_activities a ON a.activity_id=b.activity_id
           WHERE a.form_ordinal=? LIMIT 1""",
        (form_ordinal,),
    ).fetchone() is not None


def _session_is_planned(connection: sqlite3.Connection, session_id: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM u01qb02_session_plans WHERE session_id=? LIMIT 1",
        (session_id,),
    ).fetchone() is not None


def _migration_already_applied(connection: sqlite3.Connection, form_ordinal: int) -> bool:
    if not _table_exists(connection, MIGRATION_TABLE):
        return False
    return connection.execute(
        f"SELECT 1 FROM {MIGRATION_TABLE} WHERE form_ordinal=? LIMIT 1",
        (form_ordinal,),
    ).fetchone() is not None


def _form_rows(connection: sqlite3.Connection, form_ordinal: int) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """SELECT activity_id,form_id,form_ordinal,scene_ref_id,situation_family,
                      setting,skill,task_angle,support_level,scored,
                      assessment_candidate,pattern_family_ids_json,scene_anchors_json,
                      practice_projection_json,activity_digest
               FROM u01qb13_blueprint_activities
               WHERE form_ordinal=? ORDER BY activity_id""",
            (form_ordinal,),
        )
    ]


def _all_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """SELECT activity_id,form_ordinal,scene_ref_id,situation_family,setting,
                      skill,task_angle,support_level,pattern_family_ids_json,
                      scene_anchors_json,practice_projection_json,activity_digest
               FROM u01qb13_blueprint_activities ORDER BY form_ordinal,activity_id"""
        )
    ]


def _scene_usage(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    forms_by_ref: dict[str, set[int]] = {}
    identity: dict[str, dict[str, Any]] = {}
    for row in rows:
        ref = str(row["scene_ref_id"])
        forms_by_ref.setdefault(ref, set()).add(int(row["form_ordinal"]))
        current = {
            "scene_ref_id": ref,
            "situation_family": str(row["situation_family"]),
            "setting": str(row["setting"]),
            "scene_anchors_json": str(row["scene_anchors_json"]),
        }
        previous = identity.get(ref)
        if previous is not None and previous != current:
            raise RuntimeReuseSceneMigrationError(f"SCENE_IDENTITY_DRIFT:{ref}")
        identity[ref] = current
    return {
        ref: {
            **identity[ref],
            "form_ordinals": sorted(forms),
            "exposure_count": len(forms),
        }
        for ref, forms in forms_by_ref.items()
    }


def _reading_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows if str(row["skill"]) == "READING"]


def _capacity_failure_scene(
    database: Path,
    *,
    form_ordinal: int,
    rows: Sequence[Mapping[str, Any]],
    prior: Mapping[str, Mapping[str, set[str]]],
) -> str:
    try:
        u16c._migration_plan(
            Path(database),
            form_ordinal=form_ordinal,
            rows=_reading_rows(rows),
            prior=prior,
        )
        return ""
    except runtime_allocation.RuntimeTaskAwareAllocationError as exc:
        text = str(exc)
        if not text.startswith(_CAPACITY_PREFIX):
            raise RuntimeReuseSceneMigrationError(
                "READING_RUNTIME_CAPACITY_FAILURE_NOT_SCENE_LOCAL:" + text
            ) from exc
        tail = text[len(_CAPACITY_PREFIX) :]
        ref = tail.split(":", 1)[0].strip()
        if not ref:
            raise RuntimeReuseSceneMigrationError(
                "READING_RUNTIME_CAPACITY_FAILURE_SCENE_REF_MISSING"
            ) from exc
        return ref


def _replace_scene_in_memory(
    rows: Sequence[Mapping[str, Any]],
    *,
    original_ref: str,
    replacement: Mapping[str, Any],
) -> list[dict[str, Any]]:
    anchors_json = str(replacement["scene_anchors_json"])
    values: list[dict[str, Any]] = []
    replaced = 0
    for source in rows:
        row = dict(source)
        if str(row["scene_ref_id"]) == original_ref:
            row["scene_ref_id"] = str(replacement["scene_ref_id"])
            row["situation_family"] = str(replacement["situation_family"])
            row["setting"] = str(replacement["setting"])
            row["scene_anchors_json"] = anchors_json
            replaced += 1
        values.append(row)
    if replaced != u13.ACTIVITIES_PER_SCENE:
        raise RuntimeReuseSceneMigrationError(
            f"SCENE_ACTIVITY_DENOMINATOR_INVALID:{original_ref}:{replaced}"
        )
    return values


def _raw_skill_options(
    *,
    support: str,
    skill: str,
    replacement: Mapping[str, Any],
    prior: Mapping[str, Mapping[str, set[str]]],
    catalog: Mapping[str, list[dict[str, Any]]],
):
    ref = str(replacement["scene_ref_id"])
    anchors = {str(value).casefold() for value in json.loads(str(replacement["scene_anchors_json"]))}
    return runtime_allocation._scene_options(
        support=support,
        skill=skill,
        previous=set(prior.get(ref, {}).get(skill, set())),
        count=1 if skill == "SPEAKING" else 2,
        anchors=anchors,
        situation_family=str(replacement["situation_family"]),
        catalog=catalog,
        scene_ref_id=ref,
    )


def _candidate_replacements(
    *,
    failing_ref: str,
    form_ordinal: int,
    form_rows: Sequence[Mapping[str, Any]],
    usage: Mapping[str, Mapping[str, Any]],
    prior: Mapping[str, Mapping[str, set[str]]],
    catalog: Mapping[str, list[dict[str, Any]]],
) -> list[tuple[tuple[Any, ...], dict[str, Any]]]:
    failing = usage.get(failing_ref)
    if failing is None:
        raise RuntimeReuseSceneMigrationError(f"FAILING_SCENE_USAGE_MISSING:{failing_ref}")
    if int(failing["exposure_count"]) != 2:
        raise RuntimeReuseSceneMigrationError(
            f"FAILING_SCENE_NOT_SECOND_EXPOSURE:{failing_ref}:{failing['exposure_count']}"
        )
    family = str(failing["situation_family"])
    support = u09.support_for_form(form_ordinal)
    current_refs = {str(row["scene_ref_id"]) for row in form_rows}
    choices: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for ref, source in sorted(usage.items()):
        if ref == failing_ref or ref in current_refs:
            continue
        if str(source["situation_family"]) != family:
            continue
        if int(source["exposure_count"]) != 1:
            continue
        ordinals = list(source["form_ordinals"])
        if len(ordinals) != 1 or int(ordinals[0]) >= form_ordinal:
            continue
        repeat_delta = form_ordinal - int(ordinals[0])
        if repeat_delta < u08.MIN_REPEAT_FORM_DELTA:
            continue
        candidate = deepcopy(dict(source))
        try:
            reading_options = _raw_skill_options(
                support=support,
                skill="READING",
                replacement=candidate,
                prior=prior,
                catalog=catalog,
            )
            writing_options = _raw_skill_options(
                support=support,
                skill="WRITING",
                replacement=candidate,
                prior=prior,
                catalog=catalog,
            )
            speaking_options = _raw_skill_options(
                support=support,
                skill="SPEAKING",
                replacement=candidate,
                prior=prior,
                catalog=catalog,
            )
        except runtime_allocation.RuntimeTaskAwareAllocationError:
            continue
        candidate["speaking_effective_angle"] = str(speaking_options[0][0][0])
        candidate["prior_form_ordinal"] = int(ordinals[0])
        candidate["repeat_form_delta"] = repeat_delta
        # Prefer the candidate with the broadest remaining scored-angle option space,
        # then the largest repeat gap, then stable scene identity.
        rank = (
            -(len(reading_options) + len(writing_options)),
            -repeat_delta,
            ref,
        )
        choices.append((rank, candidate))
    choices.sort(key=lambda row: row[0])
    return choices


def _plan_swaps(
    database: Path,
    *,
    form_ordinal: int,
    rows: Sequence[Mapping[str, Any]],
    all_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    working = [dict(row) for row in rows]
    usage = _scene_usage(all_rows)
    prior = u16c._prior_angles_from_rows(all_rows, form_ordinal=form_ordinal) if hasattr(u16c, "_prior_angles_from_rows") else None
    if prior is None:
        # Preserve U16C's canonical prior-angle calculation without changing its API.
        with closing(sqlite3.connect(database)) as connection:
            connection.row_factory = sqlite3.Row
            prior = u16c._prior_angles(connection, form_ordinal=form_ordinal)
    catalog = runtime_allocation._catalog(Path(database))
    swaps: list[dict[str, Any]] = []

    for _ in range(u13.SCENES_PER_FORM):
        failing_ref = _capacity_failure_scene(
            database,
            form_ordinal=form_ordinal,
            rows=working,
            prior=prior,
        )
        if not failing_ref:
            return working, swaps
        candidates = _candidate_replacements(
            failing_ref=failing_ref,
            form_ordinal=form_ordinal,
            form_rows=working,
            usage=usage,
            prior=prior,
            catalog=catalog,
        )
        selected: dict[str, Any] | None = None
        for _rank, candidate in candidates:
            proposed = _replace_scene_in_memory(
                working,
                original_ref=failing_ref,
                replacement=candidate,
            )
            # The replacement itself is capacity-valid. Let the loop detect any
            # additional failing scene; do not require unrelated scenes to be fixed
            # before this deterministic same-family transfer is selected.
            selected = candidate
            working = proposed
            break
        if selected is None:
            raise RuntimeReuseSceneMigrationError(
                f"RUNTIME_CAPACITY_AWARE_REUSE_REPLACEMENT_NOT_FOUND:{failing_ref}:F{form_ordinal:02d}"
            )
        usage[failing_ref] = {**dict(usage[failing_ref]), "exposure_count": 1}
        usage[str(selected["scene_ref_id"])] = {
            **dict(usage[str(selected["scene_ref_id"])]),
            "exposure_count": 2,
            "form_ordinals": sorted(
                list(usage[str(selected["scene_ref_id"])] ["form_ordinals"]) + [form_ordinal]
            ),
        }
        swaps.append(
            {
                "original_scene_ref_id": failing_ref,
                "effective_scene_ref_id": str(selected["scene_ref_id"]),
                "situation_family": str(selected["situation_family"]),
                "setting": str(selected["setting"]),
                "scene_anchors_json": str(selected["scene_anchors_json"]),
                "speaking_effective_angle": str(selected["speaking_effective_angle"]),
                "prior_form_ordinal": int(selected["prior_form_ordinal"]),
                "repeat_form_delta": int(selected["repeat_form_delta"]),
            }
        )

    failing = _capacity_failure_scene(
        database,
        form_ordinal=form_ordinal,
        rows=working,
        prior=prior,
    )
    if failing:
        raise RuntimeReuseSceneMigrationError(
            f"RUNTIME_CAPACITY_AWARE_REUSE_REPAIR_DID_NOT_CONVERGE:{failing}:F{form_ordinal:02d}"
        )
    return working, swaps


def migrate_unbound_form_reuse_scene(
    database: Path,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    applied_at: str | None = None,
) -> dict[str, Any]:
    database = Path(database)
    if not 1 <= int(form_ordinal) <= u13.FORM_COUNT:
        raise RuntimeReuseSceneMigrationError("FORM_ORDINAL_INVALID")
    if not database.is_file():
        return {"status": PASS_STATUS, "action": "SKIP_DATABASE_MISSING", "changed": 0}

    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        if not _required_tables_present(connection):
            return {"status": PASS_STATUS, "action": "SKIP_SCHEMA_NOT_READY", "changed": 0}
        if not _session_exists(connection, learner_id=learner_id, session_id=session_id):
            return {"status": PASS_STATUS, "action": "SKIP_UNKNOWN_SESSION", "changed": 0}
        if _session_is_planned(connection, session_id):
            return {"status": PASS_STATUS, "action": "SKIP_SESSION_ALREADY_PLANNED", "changed": 0}
        if _form_has_binding(connection, form_ordinal):
            return {"status": PASS_STATUS, "action": "SKIP_FORM_FROZEN_BY_PRIOR_BINDING", "changed": 0}
        if _migration_already_applied(connection, form_ordinal):
            return {"status": PASS_STATUS, "action": "REUSE_EXISTING_MIGRATION", "changed": 0}
        rows = _form_rows(connection, form_ordinal)
        all_rows = _all_rows(connection)
    if len(rows) != u13.ACTIVITIES_PER_FORM:
        return {"status": PASS_STATUS, "action": "SKIP_BLUEPRINT_NOT_READY", "changed": 0}

    _working, swaps = _plan_swaps(
        database,
        form_ordinal=form_ordinal,
        rows=rows,
        all_rows=all_rows,
    )
    if not swaps:
        return {
            "status": PASS_STATUS,
            "action": "RUNTIME_REUSE_SCENE_CAPACITY_ALREADY_PASS",
            "form_ordinal": form_ordinal,
            "changed": 0,
        }

    applied_at = u13.timestamp(applied_at)
    swaps_by_original = {str(row["original_scene_ref_id"]): row for row in swaps}
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        if _form_has_binding(connection, form_ordinal) or _session_is_planned(connection, session_id):
            connection.rollback()
            return {"status": PASS_STATUS, "action": "SKIP_FORM_BECAME_FROZEN", "changed": 0}
        _ddl(connection)
        if _migration_already_applied(connection, form_ordinal):
            connection.rollback()
            return {"status": PASS_STATUS, "action": "REUSE_EXISTING_MIGRATION", "changed": 0}

        changed = 0
        for source in rows:
            original_ref = str(source["scene_ref_id"])
            swap = swaps_by_original.get(original_ref)
            if swap is None:
                continue
            skill = str(source["skill"])
            angle = str(source["task_angle"])
            families_json = str(source["pattern_family_ids_json"])
            projection_json = str(source["practice_projection_json"])
            anchors = json.loads(str(swap["scene_anchors_json"]))
            if skill == "SPEAKING":
                angle = str(swap["speaking_effective_angle"])
                families_json = u13.canonical(list(u13.SPEAKING_LEXICAL_FAMILIES))
                projection_json = u13.canonical(
                    u13._practice_projection(angle, {"anchors": anchors})
                )
            effective_digest = u13.digest(
                {
                    "migration_task_id": TASK_ID,
                    "base_activity_id": str(source["activity_id"]),
                    "base_activity_digest": str(source["activity_digest"]),
                    "effective_scene_ref_id": str(swap["effective_scene_ref_id"]),
                    "effective_scene_anchors": anchors,
                    "effective_task_angle": angle,
                    "effective_pattern_family_ids": json.loads(families_json),
                    "practice_projection": json.loads(projection_json),
                }
            )
            cursor = connection.execute(
                """UPDATE u01qb13_blueprint_activities
                   SET scene_ref_id=?,situation_family=?,setting=?,scene_anchors_json=?,
                       task_angle=?,pattern_family_ids_json=?,practice_projection_json=?,
                       activity_digest=?
                   WHERE activity_id=? AND activity_digest=?""",
                (
                    str(swap["effective_scene_ref_id"]),
                    str(swap["situation_family"]),
                    str(swap["setting"]),
                    str(swap["scene_anchors_json"]),
                    angle,
                    families_json,
                    projection_json,
                    effective_digest,
                    str(source["activity_id"]),
                    str(source["activity_digest"]),
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise RuntimeReuseSceneMigrationError(
                    f"BLUEPRINT_ACTIVITY_CONCURRENT_DRIFT:{source['activity_id']}"
                )
            connection.execute(
                f"""INSERT INTO {MIGRATION_TABLE}
                (activity_id,form_ordinal,original_scene_ref_id,effective_scene_ref_id,
                 original_activity_digest,effective_activity_digest,applied_at,migration_session_id)
                VALUES(?,?,?,?,?,?,?,?)""",
                (
                    str(source["activity_id"]),
                    int(form_ordinal),
                    original_ref,
                    str(swap["effective_scene_ref_id"]),
                    str(source["activity_digest"]),
                    effective_digest,
                    applied_at,
                    session_id,
                ),
            )
            changed += 1

        if changed != len(swaps) * u13.ACTIVITIES_PER_SCENE:
            connection.rollback()
            raise RuntimeReuseSceneMigrationError(
                f"MIGRATED_ACTIVITY_DENOMINATOR_INVALID:{changed}:{len(swaps) * u13.ACTIVITIES_PER_SCENE}"
            )

        # Same-family 2->1 / 1->2 transfers preserve all global denominators.
        after_rows = _all_rows(connection)
        exposure_counts = Counter(
            (int(row["form_ordinal"]), str(row["scene_ref_id"])) for row in after_rows
        )
        if any(value != u13.ACTIVITIES_PER_SCENE for value in exposure_counts.values()):
            connection.rollback()
            raise RuntimeReuseSceneMigrationError("POST_MIGRATION_SCENE_ACTIVITY_DENOMINATOR_DRIFT")
        distinct_refs = {str(row["scene_ref_id"]) for row in after_rows}
        if len(distinct_refs) != len({str(row["scene_ref_id"]) for row in all_rows}):
            connection.rollback()
            raise RuntimeReuseSceneMigrationError("POST_MIGRATION_DISTINCT_SCENE_COUNT_DRIFT")
        form_families_before = Counter(str(row["situation_family"]) for row in rows)
        form_families_after = Counter(
            str(row["situation_family"])
            for row in after_rows
            if int(row["form_ordinal"]) == int(form_ordinal)
        )
        if form_families_before != form_families_after:
            connection.rollback()
            raise RuntimeReuseSceneMigrationError("POST_MIGRATION_FORM_FAMILY_COMPOSITION_DRIFT")

        metadata = {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "last_migrated_form_ordinal": str(form_ordinal),
            "last_scene_swap_count": str(len(swaps)),
            "last_changed_activity_count": str(changed),
            "same_scene_same_skill_same_task_angle_repeat_allowed": "false",
            "bound_activities_modified": "false",
            "questionbank_modified": "false",
            "new_scene_authored": "false",
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
        "action": "MIGRATED_UNBOUND_FORM_REUSE_SCENE_TO_RUNTIME_CAPACITY",
        "form_ordinal": int(form_ordinal),
        "scene_swap_count": len(swaps),
        "changed": changed,
        "swaps": [
            {
                "from": str(row["original_scene_ref_id"]),
                "to": str(row["effective_scene_ref_id"]),
                "situation_family": str(row["situation_family"]),
                "prior_form_ordinal": int(row["prior_form_ordinal"]),
                "repeat_form_delta": int(row["repeat_form_delta"]),
            }
            for row in swaps
        ],
        "same_scene_same_skill_same_task_angle_repeat_allowed": False,
        "bound_activities_modified": False,
        "questionbank_modified": False,
        "new_scene_authored": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
