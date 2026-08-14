"""Reconcile canonical Unit01 scene anchors before unbound product execution.

Actual R4 production replay isolated U01-MA-SHOP-04 as formal Reading capacity
zero after R4R3R4. The approved scene contains ``ROBOT`` and ``SHOP_WINDOW``
but both the R2 resolver and historical U01QB13 semantic index treated compound
object labels as one case-folded token. ``SHOP_WINDOW`` therefore failed to
contribute the already-approved Unit01 noun ``window`` and the persisted
blueprint carried only ``shop``. U18C then correctly rejected learner-invalid
``shop in the shop`` contextual rows, leaving no two-angle formal Reading
solution.

R4R3R5 fixes that cross-layer authority drift without authoring content. It
normalizes compound object labels with the canonical word tokenizer, keeps the
32-scene / 31-bindable / FOOD-04-deferred scope unchanged, and reconciles only a
completely unbound Form's persisted scene anchors before the existing R4R3R1,
R4R3, R4R2 and U16C migration chain executes. Once any activity in a Form is
bound, the Form remains frozen.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import _u01qb18f_r2_canonical_micro_scene_authority_fullfix as authority
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Learner-state-safe canonical anchor reconciliation over already-approved Unit01 "
    "scenes and existing blueprint rows. It authors no content or scene, changes no "
    "QuestionBank, bound learner evidence, scoring/runtime/planner authority, Unit02-24, "
    "audio, Speaking score, or A2 state."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R3R5_CanonicalSceneAnchorReconciliationFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R3R5_CANONICAL_SCENE_ANCHOR_RECONCILIATION_FULLFIX"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18F-R4_ActualTwelveFormFullSemanticLanguagePedagogicalReplay"
MIGRATION_TABLE = "u01qb18f_r4r3r5_scene_anchor_migrations"
METADATA_TABLE = "u01qb18f_r4r3r5_metadata"
SHOP04_REF = "U01-MA-SHOP-04"
EXPECTED_SHOP04_ANCHORS = ("shop", "window")

_ORIGINAL_UNIT01_BINDABILITY = authority._unit01_bindability
_ORIGINAL_U13_SCENE_INDEX = u13._scene_semantic_index
_INSTALLED = False


class CanonicalSceneAnchorReconciliationError(ValueError):
    """Fail-closed canonical scene-anchor reconciliation error."""


def _tokenized_unit01_bindability(
    core: Mapping[str, Any],
) -> tuple[bool, list[str], str]:
    active = authority._active_unit01_nouns()
    object_words: set[str] = set()
    for value in core.get("objects") or []:
        object_words.update(authority._words(value))
    anchors = sorted((object_words | authority._words(core.get("setting"))) & active)
    return (
        (True, anchors, "UNIT_ACTIVE_NOUN_ANCHOR_PRESENT")
        if anchors
        else (False, [], "UNIT_ACTIVE_NOUN_ANCHOR_MISSING_DEFER_FOR_LATER_UNIT")
    )


def _canonical_u13_scene_semantic_index() -> dict[str, dict[str, Any]]:
    """Project U13's row shape directly from the canonical R2 authority.

    Do not delegate to historical U13 here: that legacy builder intentionally
    fails when any committed model scene lacks a Unit01 anchor, while the current
    canonical authority deliberately retains FOOD-04 as a dereferenceable but
    deferred scene. Rotation never consumes that deferred ref.
    """
    values: dict[str, dict[str, Any]] = {}
    for ref, package in authority.canonical_micro_scene_authority().items():
        core = package.get("scene_core")
        if not isinstance(core, Mapping):
            raise CanonicalSceneAnchorReconciliationError(
                f"CANONICAL_SCENE_CORE_MISSING:{ref}"
            )
        anchors = [str(value) for value in package.get("anchors") or []]
        if package.get("unit_runtime_bindable") is True and not anchors:
            raise CanonicalSceneAnchorReconciliationError(
                f"CANONICAL_SCENE_ANCHORS_MISSING:{ref}"
            )
        origin = str(package.get("scene_origin") or "")
        source = (
            "CANONICAL_CONTEXT"
            if origin == "CANONICAL_UNIT01_CONTEXT"
            else "MODEL_AUTHORED_APPROVED_SCENE"
        )
        values[str(ref)] = {
            "scene_ref_id": str(ref),
            "objects": sorted(
                str(value).casefold() for value in core.get("objects") or []
            ),
            "anchors": anchors,
            "setting": str(package.get("setting") or core.get("setting") or ""),
            "source": source,
            "event": str(package.get("event") or ""),
            "action": list(core.get("actions") or []),
            "relations": list(core.get("relations") or []),
            "communicative_goal": str(package.get("communicative_goal") or ""),
        }
    if len(values) != authority.EXPECTED_SCENE_COUNT:
        raise CanonicalSceneAnchorReconciliationError(
            f"U13_CANONICAL_SCENE_COUNT_INVALID:{len(values)}"
        )
    return values


def install() -> None:
    """Install tokenizer + future-blueprint anchor parity atomically."""
    global _INSTALLED
    if installed():
        _INSTALLED = True
        return
    if authority._unit01_bindability not in (
        _ORIGINAL_UNIT01_BINDABILITY,
        _tokenized_unit01_bindability,
    ):
        raise CanonicalSceneAnchorReconciliationError(
            "R2_UNIT01_BINDABILITY_OWNER_DRIFT"
        )
    if u13._scene_semantic_index not in (
        _ORIGINAL_U13_SCENE_INDEX,
        _canonical_u13_scene_semantic_index,
    ):
        raise CanonicalSceneAnchorReconciliationError(
            "U13_SCENE_SEMANTIC_INDEX_OWNER_DRIFT"
        )

    previous_bindability = authority._unit01_bindability
    previous_u13_index = u13._scene_semantic_index
    authority._unit01_bindability = _tokenized_unit01_bindability
    authority._authority_cached.cache_clear()
    try:
        report = authority.require_authority_pass()
        package = authority.canonical_scene_package(SHOP04_REF)
        index = _canonical_u13_scene_semantic_index()
        if tuple(package.get("anchors") or ()) != EXPECTED_SHOP04_ANCHORS:
            raise CanonicalSceneAnchorReconciliationError(
                "SHOP04_CANONICAL_ANCHOR_TOKENIZATION_INVALID:"
                + ",".join(str(value) for value in package.get("anchors") or [])
            )
        if (
            report.get("unit01_runtime_bindable_scene_count")
            != authority.EXPECTED_UNIT01_BINDABLE_COUNT
            or tuple(report.get("deferred_scene_refs") or ())
            != authority.EXPECTED_DEFERRED_REFS
        ):
            raise CanonicalSceneAnchorReconciliationError(
                "CANONICAL_SCENE_SCOPE_DRIFT_AFTER_TOKENIZATION"
            )
        if tuple(index[SHOP04_REF].get("anchors") or ()) != EXPECTED_SHOP04_ANCHORS:
            raise CanonicalSceneAnchorReconciliationError(
                "U13_SHOP04_ANCHOR_PARITY_INVALID"
            )
        for deferred_ref in authority.EXPECTED_DEFERRED_REFS:
            if deferred_ref not in index:
                raise CanonicalSceneAnchorReconciliationError(
                    f"U13_DEFERRED_SCENE_DEREFERENCE_MISSING:{deferred_ref}"
                )
            if index[deferred_ref].get("anchors"):
                raise CanonicalSceneAnchorReconciliationError(
                    f"U13_DEFERRED_SCENE_UNEXPECTED_UNIT01_ANCHORS:{deferred_ref}"
                )
        u13._scene_semantic_index = _canonical_u13_scene_semantic_index
        _INSTALLED = True
    except Exception:
        authority._unit01_bindability = previous_bindability
        authority._authority_cached.cache_clear()
        u13._scene_semantic_index = previous_u13_index
        _INSTALLED = False
        raise


def installed() -> bool:
    if not _INSTALLED:
        return False
    try:
        shop = authority.canonical_scene_package(SHOP04_REF)
    except Exception:
        return False
    return (
        authority._unit01_bindability is _tokenized_unit01_bindability
        and u13._scene_semantic_index is _canonical_u13_scene_semantic_index
        and tuple(shop.get("anchors") or ()) == EXPECTED_SHOP04_ANCHORS
    )


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _required_tables_present(connection: sqlite3.Connection) -> bool:
    return all(
        _table_exists(connection, table)
        for table in (
            "learning_sessions",
            "u01qb02_session_plans",
            "u01qb13_blueprint_activities",
            "u01qb13_session_bindings",
        )
    )


def _form_has_binding(connection: sqlite3.Connection, form_ordinal: int) -> bool:
    return connection.execute(
        """SELECT 1
           FROM u01qb13_session_bindings b
           JOIN u01qb13_blueprint_activities a ON a.activity_id=b.activity_id
           WHERE a.form_ordinal=? LIMIT 1""",
        (int(form_ordinal),),
    ).fetchone() is not None


def _session_is_planned(connection: sqlite3.Connection, session_id: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM u01qb02_session_plans WHERE session_id=? LIMIT 1",
        (str(session_id),),
    ).fetchone() is not None


def _session_exists(
    connection: sqlite3.Connection,
    *,
    learner_id: str,
    session_id: str,
) -> bool:
    return connection.execute(
        "SELECT 1 FROM learning_sessions WHERE learner_id=? AND session_id=?",
        (str(learner_id), str(session_id)),
    ).fetchone() is not None


def _canonical_anchors(scene_ref_id: str) -> list[str]:
    package = authority.canonical_scene_package(str(scene_ref_id))
    if package.get("unit_runtime_bindable") is not True:
        raise CanonicalSceneAnchorReconciliationError(
            f"DEFERRED_SCENE_IN_RUNTIME_BLUEPRINT:{scene_ref_id}"
        )
    anchors = sorted(
        {
            str(value).strip().casefold()
            for value in package.get("anchors") or []
            if str(value).strip()
        }
    )
    if not anchors:
        raise CanonicalSceneAnchorReconciliationError(
            f"CANONICAL_SCENE_ANCHORS_MISSING:{scene_ref_id}"
        )
    return anchors


def _canonical_json(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def _normalized_anchor_json(raw: str) -> str:
    try:
        values = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise CanonicalSceneAnchorReconciliationError(
            "BLUEPRINT_SCENE_ANCHOR_JSON_INVALID"
        ) from exc
    if not isinstance(values, list):
        raise CanonicalSceneAnchorReconciliationError(
            "BLUEPRINT_SCENE_ANCHOR_ARRAY_REQUIRED"
        )
    return _canonical_json(
        sorted(
            {
                str(value).strip().casefold()
                for value in values
                if str(value).strip()
            }
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
          scene_ref_id TEXT NOT NULL,
          original_scene_anchors_json TEXT NOT NULL,
          effective_scene_anchors_json TEXT NOT NULL,
          original_activity_digest TEXT NOT NULL,
          effective_activity_digest TEXT NOT NULL,
          applied_at TEXT NOT NULL,
          migration_session_id TEXT NOT NULL
        );
        """
    )


def migrate_unbound_form_scene_anchors(
    database: Path,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    applied_at: str | None = None,
) -> dict[str, Any]:
    """Reconcile all activities in a Form only before its first binding/plan."""
    if not installed():
        raise CanonicalSceneAnchorReconciliationError(
            "R4R3R5_INSTALL_REQUIRED"
        )
    database = Path(database)
    if not 1 <= int(form_ordinal) <= u13.FORM_COUNT:
        raise CanonicalSceneAnchorReconciliationError("FORM_ORDINAL_INVALID")
    if not database.is_file():
        return {"status": PASS_STATUS, "action": "SKIP_DATABASE_MISSING", "changed": 0}

    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        if not _required_tables_present(connection):
            return {"status": PASS_STATUS, "action": "SKIP_SCHEMA_NOT_READY", "changed": 0}
        if not _session_exists(
            connection,
            learner_id=learner_id,
            session_id=session_id,
        ):
            return {"status": PASS_STATUS, "action": "SKIP_UNKNOWN_SESSION", "changed": 0}
        if _session_is_planned(connection, session_id):
            return {"status": PASS_STATUS, "action": "SKIP_SESSION_ALREADY_PLANNED", "changed": 0}
        if _form_has_binding(connection, int(form_ordinal)):
            return {"status": PASS_STATUS, "action": "SKIP_FORM_FROZEN_BY_PRIOR_BINDING", "changed": 0}
        rows = [
            dict(row)
            for row in connection.execute(
                """SELECT activity_id,form_ordinal,scene_ref_id,scene_anchors_json,
                          activity_digest
                   FROM u01qb13_blueprint_activities
                   WHERE form_ordinal=? ORDER BY activity_id""",
                (int(form_ordinal),),
            )
        ]
    if len(rows) != u13.ACTIVITIES_PER_FORM:
        return {"status": PASS_STATUS, "action": "SKIP_BLUEPRINT_NOT_READY", "changed": 0}

    plan: list[dict[str, str]] = []
    for row in rows:
        anchors = _canonical_anchors(str(row["scene_ref_id"]))
        effective_json = _canonical_json(anchors)
        original_json = _normalized_anchor_json(str(row["scene_anchors_json"]))
        if original_json == effective_json:
            continue
        effective_digest = u13.digest(
            {
                "migration_task_id": TASK_ID,
                "base_activity_id": str(row["activity_id"]),
                "base_activity_digest": str(row["activity_digest"]),
                "effective_scene_anchors": anchors,
            }
        )
        plan.append(
            {
                "activity_id": str(row["activity_id"]),
                "scene_ref_id": str(row["scene_ref_id"]),
                "original_scene_anchors_json": original_json,
                "effective_scene_anchors_json": effective_json,
                "original_activity_digest": str(row["activity_digest"]),
                "effective_activity_digest": effective_digest,
            }
        )
    if not plan:
        return {
            "status": PASS_STATUS,
            "action": "CANONICAL_SCENE_ANCHORS_ALREADY_CURRENT",
            "changed": 0,
        }

    applied_at = u13.timestamp(applied_at)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        if _session_is_planned(connection, session_id) or _form_has_binding(
            connection, int(form_ordinal)
        ):
            connection.rollback()
            return {"status": PASS_STATUS, "action": "SKIP_FORM_BECAME_FROZEN", "changed": 0}
        _ddl(connection)
        changed = 0
        for change in plan:
            cursor = connection.execute(
                """UPDATE u01qb13_blueprint_activities
                   SET scene_anchors_json=?,activity_digest=?
                   WHERE activity_id=? AND activity_digest=?""",
                (
                    change["effective_scene_anchors_json"],
                    change["effective_activity_digest"],
                    change["activity_id"],
                    change["original_activity_digest"],
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise CanonicalSceneAnchorReconciliationError(
                    f"BLUEPRINT_ACTIVITY_CONCURRENT_DRIFT:{change['activity_id']}"
                )
            connection.execute(
                f"""INSERT INTO {MIGRATION_TABLE}
                (activity_id,form_ordinal,scene_ref_id,original_scene_anchors_json,
                 effective_scene_anchors_json,original_activity_digest,
                 effective_activity_digest,applied_at,migration_session_id)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    change["activity_id"],
                    int(form_ordinal),
                    change["scene_ref_id"],
                    change["original_scene_anchors_json"],
                    change["effective_scene_anchors_json"],
                    change["original_activity_digest"],
                    change["effective_activity_digest"],
                    applied_at,
                    str(session_id),
                ),
            )
            changed += 1
        connection.executemany(
            f"INSERT OR REPLACE INTO {METADATA_TABLE}(key,value) VALUES(?,?)",
            {
                "task_id": TASK_ID,
                "validation_status": PASS_STATUS,
                "last_form_ordinal": str(int(form_ordinal)),
                "last_changed_activity_count": str(changed),
                "questionbank_modified": "false",
                "new_scene_authored": "false",
                "bound_evidence_modified": "false",
                "next_short_step": NEXT_SHORT_STEP,
            }.items(),
        )
        connection.commit()

    return {
        "status": PASS_STATUS,
        "action": "MIGRATED_UNBOUND_FORM_TO_CANONICAL_SCENE_ANCHORS",
        "form_ordinal": int(form_ordinal),
        "changed": changed,
        "questionbank_modified": False,
        "new_scene_authored": False,
        "bound_evidence_modified": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
