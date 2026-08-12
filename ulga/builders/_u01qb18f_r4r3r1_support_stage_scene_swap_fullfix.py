"""Repair single-exposure Unit01 scene/support-stage runtime capacity mismatches.

Actual R4 replay proved that a legal single-exposure scene can be assigned to a
support stage where the 474-item runtime cannot provide the required two Reading
activities. This is different from the R4R3 reused-scene case: the failing scene
may have exposure_count == 1, so replacing it outright would incorrectly remove
one canonical Unit01 scene from the 31-scene runtime world.

R4R3R1 therefore performs a deterministic same-family package swap between the
current still-unbound form and a later still-unbound form. Both scene identities
remain present exactly once, global scene/exposure counts stay unchanged, and
per-form situation-family composition is preserved. A swap is admitted only if
the resulting current and donor forms have runtime-capacity solutions for
Reading, Writing and Speaking under the frozen no-repeat task-angle contract.
Reading/Writing task-angle mutation remains owned by U16C/R4R2; this adapter only
moves scene identity/anchors and updates Speaking because no downstream Speaking
migration exists.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb18f_r4r3_runtime_capacity_aware_reuse_scene_migration as r4r3
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u09
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13
from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_allocation

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Learner-state-safe deterministic same-family scene-package permutation across "
    "already-approved Unit01 scenes and the existing 474-item runtime. It authors no "
    "content, changes no QuestionBank/scoring/runtime/planner authority, preserves "
    "bound learner evidence, Unit02-24, audio, Speaking scoring and the A2 lock."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R3R1_SupportStageSceneAssignmentRuntimeCapacityFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R3R1_SUPPORT_STAGE_SCENE_ASSIGNMENT_RUNTIME_CAPACITY_FULLFIX"
NEXT_SHORT_STEP = r4r3.NEXT_SHORT_STEP

MIGRATION_TABLE = "u01qb18f_r4r3r1_support_stage_scene_swaps"
METADATA_TABLE = "u01qb18f_r4r3r1_metadata"


class SupportStageSceneSwapError(ValueError):
    """Fail-closed support-stage scene assignment migration error."""


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
          partner_form_ordinal INTEGER NOT NULL,
          original_scene_ref_id TEXT NOT NULL,
          effective_scene_ref_id TEXT NOT NULL,
          original_activity_digest TEXT NOT NULL,
          effective_activity_digest TEXT NOT NULL,
          applied_at TEXT NOT NULL,
          migration_session_id TEXT NOT NULL
        );
        """
    )


def _prior_angles_from_rows(
    rows: Sequence[Mapping[str, Any]], *, form_ordinal: int
) -> dict[str, dict[str, set[str]]]:
    prior: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in rows:
        if int(row["form_ordinal"]) >= int(form_ordinal):
            continue
        prior[str(row["scene_ref_id"])][str(row["skill"])].add(str(row["task_angle"]))
    return prior


def _form_rows_from_all(
    rows: Sequence[Mapping[str, Any]], form_ordinal: int
) -> list[dict[str, Any]]:
    return [dict(row) for row in rows if int(row["form_ordinal"]) == int(form_ordinal)]


def _scene_identity(rows: Sequence[Mapping[str, Any]], ref: str) -> dict[str, str]:
    matches = [row for row in rows if str(row["scene_ref_id"]) == str(ref)]
    if not matches:
        raise SupportStageSceneSwapError(f"SCENE_IDENTITY_MISSING:{ref}")
    identities = {
        (
            str(row["situation_family"]),
            str(row["setting"]),
            str(row["scene_anchors_json"]),
        )
        for row in matches
    }
    if len(identities) != 1:
        raise SupportStageSceneSwapError(f"SCENE_IDENTITY_DRIFT:{ref}")
    family, setting, anchors_json = next(iter(identities))
    return {
        "scene_ref_id": str(ref),
        "situation_family": family,
        "setting": setting,
        "scene_anchors_json": anchors_json,
    }


def _form_skill_choices(
    *,
    all_rows: Sequence[Mapping[str, Any]],
    form_ordinal: int,
    skill: str,
    catalog: Mapping[str, list[dict[str, Any]]],
) -> dict[str, tuple[str, ...]]:
    form_rows = [
        dict(row)
        for row in all_rows
        if int(row["form_ordinal"]) == int(form_ordinal) and str(row["skill"]) == skill
    ]
    expected = u13.SPEAKING_PER_FORM if skill == "SPEAKING" else (
        u13.READING_PER_FORM if skill == "READING" else u13.WRITING_PER_FORM
    )
    if len(form_rows) != expected:
        raise SupportStageSceneSwapError(
            f"FORM_SKILL_ACTIVITY_DENOMINATOR_INVALID:F{form_ordinal:02d}:{skill}:{len(form_rows)}:{expected}"
        )
    supports = {str(row["support_level"]) for row in form_rows}
    if len(supports) != 1:
        raise SupportStageSceneSwapError(
            f"FORM_SUPPORT_DRIFT:F{form_ordinal:02d}:{skill}:{','.join(sorted(supports))}"
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in form_rows:
        grouped[str(row["scene_ref_id"])].append(row)
    expected_per_scene = 1 if skill == "SPEAKING" else 2
    if len(grouped) != u13.SCENES_PER_FORM or any(
        len(values) != expected_per_scene for values in grouped.values()
    ):
        raise SupportStageSceneSwapError(
            f"FORM_SCENE_SKILL_DENOMINATOR_INVALID:F{form_ordinal:02d}:{skill}"
        )
    scene_infos: list[dict[str, Any]] = []
    for ref in sorted(grouped):
        scene_rows = grouped[ref]
        families = {str(row["situation_family"]) for row in scene_rows}
        anchors = {
            str(anchor).casefold()
            for row in scene_rows
            for anchor in json.loads(str(row["scene_anchors_json"]))
        }
        if len(families) != 1 or not anchors:
            raise SupportStageSceneSwapError(f"FORM_SCENE_CONTRACT_INVALID:{ref}:{skill}")
        scene_infos.append(
            {
                "scene_ref_id": ref,
                "anchors": anchors,
                "situation_family": next(iter(families)),
            }
        )
    return runtime_allocation._solve_form_skill(
        support=next(iter(supports)),
        skill=skill,
        scene_infos=scene_infos,
        prior_angles=_prior_angles_from_rows(all_rows, form_ordinal=form_ordinal),
        catalog=catalog,
    )


def _swap_scene_packages_in_memory(
    all_rows: Sequence[Mapping[str, Any]],
    *,
    current_form: int,
    failing_ref: str,
    donor_form: int,
    donor_ref: str,
) -> list[dict[str, Any]]:
    failing_identity = _scene_identity(all_rows, failing_ref)
    donor_identity = _scene_identity(all_rows, donor_ref)
    values: list[dict[str, Any]] = []
    current_changed = 0
    donor_changed = 0
    for source in all_rows:
        row = dict(source)
        form = int(row["form_ordinal"])
        ref = str(row["scene_ref_id"])
        replacement: Mapping[str, str] | None = None
        if form == int(current_form) and ref == str(failing_ref):
            replacement = donor_identity
            current_changed += 1
        elif form == int(donor_form) and ref == str(donor_ref):
            replacement = failing_identity
            donor_changed += 1
        if replacement is not None:
            row["scene_ref_id"] = str(replacement["scene_ref_id"])
            row["situation_family"] = str(replacement["situation_family"])
            row["setting"] = str(replacement["setting"])
            row["scene_anchors_json"] = str(replacement["scene_anchors_json"])
        values.append(row)
    if current_changed != u13.ACTIVITIES_PER_SCENE or donor_changed != u13.ACTIVITIES_PER_SCENE:
        raise SupportStageSceneSwapError(
            f"SCENE_SWAP_ACTIVITY_DENOMINATOR_INVALID:{current_changed}:{donor_changed}"
        )
    return values


def _bound_form_ordinals(connection: sqlite3.Connection) -> set[int]:
    return {
        int(row[0])
        for row in connection.execute(
            """SELECT DISTINCT a.form_ordinal
               FROM u01qb13_session_bindings b
               JOIN u01qb13_blueprint_activities a ON a.activity_id=b.activity_id"""
        )
    }


def _candidate_swap(
    database: Path,
    *,
    current_form: int,
    failing_ref: str,
    all_rows: Sequence[Mapping[str, Any]],
    frozen_forms: set[int],
) -> tuple[int, str, list[dict[str, Any]], dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]] | None:
    usage = r4r3._scene_usage(all_rows)
    failing_usage = usage.get(str(failing_ref))
    if failing_usage is None:
        raise SupportStageSceneSwapError(f"FAILING_SCENE_USAGE_MISSING:{failing_ref}")
    if int(failing_usage["exposure_count"]) != 1:
        return None
    family = str(failing_usage["situation_family"])
    current_refs = {
        str(row["scene_ref_id"])
        for row in all_rows
        if int(row["form_ordinal"]) == int(current_form)
    }
    catalog = runtime_allocation._catalog(Path(database))
    ranked: list[
        tuple[
            tuple[Any, ...],
            tuple[int, str, list[dict[str, Any]], dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]],
        ]
    ] = []
    seen: set[tuple[int, str]] = set()
    for row in all_rows:
        donor_form = int(row["form_ordinal"])
        donor_ref = str(row["scene_ref_id"])
        key = (donor_form, donor_ref)
        if key in seen:
            continue
        seen.add(key)
        if donor_form <= int(current_form) or donor_form in frozen_forms:
            continue
        if donor_ref == str(failing_ref) or donor_ref in current_refs:
            continue
        donor_usage = usage.get(donor_ref)
        if donor_usage is None or int(donor_usage["exposure_count"]) != 1:
            continue
        if str(donor_usage["situation_family"]) != family:
            continue
        donor_form_refs = {
            str(value["scene_ref_id"])
            for value in all_rows
            if int(value["form_ordinal"]) == donor_form
        }
        if str(failing_ref) in donor_form_refs:
            continue
        simulated = _swap_scene_packages_in_memory(
            all_rows,
            current_form=current_form,
            failing_ref=failing_ref,
            donor_form=donor_form,
            donor_ref=donor_ref,
        )
        try:
            current_choices = {
                skill: _form_skill_choices(
                    all_rows=simulated,
                    form_ordinal=current_form,
                    skill=skill,
                    catalog=catalog,
                )
                for skill in ("READING", "WRITING", "SPEAKING")
            }
            donor_choices = {
                skill: _form_skill_choices(
                    all_rows=simulated,
                    form_ordinal=donor_form,
                    skill=skill,
                    catalog=catalog,
                )
                for skill in ("READING", "WRITING", "SPEAKING")
            }
        except runtime_allocation.RuntimeTaskAwareAllocationError:
            continue
        # Prefer the nearest future form, then stable scene identity. Both forms
        # already passed the complete per-skill distinct-item solver above.
        rank = (donor_form - int(current_form), donor_ref)
        ranked.append(
            (
                rank,
                (
                    donor_form,
                    donor_ref,
                    simulated,
                    current_choices["SPEAKING"],
                    donor_choices["SPEAKING"],
                ),
            )
        )
    if not ranked:
        return None
    ranked.sort(key=lambda value: value[0])
    return ranked[0][1]


def _apply_speaking_choice(
    row: dict[str, Any], *, choices: Mapping[str, tuple[str, ...]]
) -> dict[str, Any]:
    if str(row["skill"]) != "SPEAKING":
        return row
    ref = str(row["scene_ref_id"])
    angles = tuple(choices.get(ref, ()))
    if len(angles) != 1:
        raise SupportStageSceneSwapError(f"SPEAKING_CHOICE_MISSING:{ref}")
    angle = str(angles[0])
    anchors = json.loads(str(row["scene_anchors_json"]))
    row["task_angle"] = angle
    row["pattern_family_ids_json"] = u13.canonical(list(u13.SPEAKING_LEXICAL_FAMILIES))
    row["practice_projection_json"] = u13.canonical(
        u13._practice_projection(angle, {"anchors": anchors})
    )
    return row


def migrate_unbound_support_stage_scene_assignment(
    database: Path,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    applied_at: str | None = None,
) -> dict[str, Any]:
    database = Path(database)
    if not 1 <= int(form_ordinal) <= u13.FORM_COUNT:
        raise SupportStageSceneSwapError("FORM_ORDINAL_INVALID")
    if not database.is_file():
        return {"status": PASS_STATUS, "action": "SKIP_DATABASE_MISSING", "changed": 0}

    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        if not r4r3._required_tables_present(connection):
            return {"status": PASS_STATUS, "action": "SKIP_SCHEMA_NOT_READY", "changed": 0}
        if not r4r3._session_exists(connection, learner_id=learner_id, session_id=session_id):
            return {"status": PASS_STATUS, "action": "SKIP_UNKNOWN_SESSION", "changed": 0}
        if r4r3._session_is_planned(connection, session_id):
            return {"status": PASS_STATUS, "action": "SKIP_SESSION_ALREADY_PLANNED", "changed": 0}
        if r4r3._form_has_binding(connection, form_ordinal):
            return {"status": PASS_STATUS, "action": "SKIP_FORM_FROZEN_BY_PRIOR_BINDING", "changed": 0}
        all_rows = r4r3._all_rows(connection)
        rows = r4r3._form_rows(connection, form_ordinal)
        frozen_forms = _bound_form_ordinals(connection)
    if len(rows) != u13.ACTIVITIES_PER_FORM:
        return {"status": PASS_STATUS, "action": "SKIP_BLUEPRINT_NOT_READY", "changed": 0}

    prior = _prior_angles_from_rows(all_rows, form_ordinal=form_ordinal)
    failing_ref = r4r3._capacity_failure_scene(
        database,
        form_ordinal=form_ordinal,
        rows=rows,
        prior=prior,
    )
    if not failing_ref:
        return {
            "status": PASS_STATUS,
            "action": "SUPPORT_STAGE_SCENE_CAPACITY_ALREADY_PASS",
            "form_ordinal": int(form_ordinal),
            "changed": 0,
        }

    usage = r4r3._scene_usage(all_rows)
    failing_usage = usage.get(failing_ref)
    if failing_usage is None:
        raise SupportStageSceneSwapError(f"FAILING_SCENE_USAGE_MISSING:{failing_ref}")
    if int(failing_usage["exposure_count"]) != 1:
        return {
            "status": PASS_STATUS,
            "action": "DELEGATE_REUSED_SCENE_FAILURE_TO_R4R3",
            "form_ordinal": int(form_ordinal),
            "scene_ref_id": failing_ref,
            "changed": 0,
        }

    selected = _candidate_swap(
        database,
        current_form=form_ordinal,
        failing_ref=failing_ref,
        all_rows=all_rows,
        frozen_forms=frozen_forms,
    )
    if selected is None:
        raise SupportStageSceneSwapError(
            f"SUPPORT_STAGE_SCENE_SWAP_NOT_FOUND:{failing_ref}:F{form_ordinal:02d}"
        )
    donor_form, donor_ref, simulated, current_speaking, donor_speaking = selected
    before_usage_counts = Counter(
        (str(value["scene_ref_id"]), int(value["form_ordinal"])) for value in all_rows
    )
    simulated_rows = []
    for source in simulated:
        row = dict(source)
        form = int(row["form_ordinal"])
        if form == int(form_ordinal):
            row = _apply_speaking_choice(row, choices=current_speaking)
        elif form == int(donor_form):
            row = _apply_speaking_choice(row, choices=donor_speaking)
        simulated_rows.append(row)

    original_by_id = {str(row["activity_id"]): dict(row) for row in all_rows}
    effective_by_id = {str(row["activity_id"]): dict(row) for row in simulated_rows}
    changed_ids = sorted(
        activity_id
        for activity_id, source in original_by_id.items()
        if any(
            str(source.get(key)) != str(effective_by_id[activity_id].get(key))
            for key in (
                "scene_ref_id",
                "situation_family",
                "setting",
                "scene_anchors_json",
                "task_angle",
                "pattern_family_ids_json",
                "practice_projection_json",
            )
        )
    )
    expected_changed = 2 * u13.ACTIVITIES_PER_SCENE
    if len(changed_ids) != expected_changed:
        raise SupportStageSceneSwapError(
            f"SCENE_SWAP_CHANGED_ACTIVITY_DENOMINATOR_INVALID:{len(changed_ids)}:{expected_changed}"
        )

    applied_at = u13.timestamp(applied_at)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        if r4r3._form_has_binding(connection, form_ordinal) or r4r3._form_has_binding(connection, donor_form):
            connection.rollback()
            return {"status": PASS_STATUS, "action": "SKIP_SWAP_FORM_BECAME_FROZEN", "changed": 0}
        if r4r3._session_is_planned(connection, session_id):
            connection.rollback()
            return {"status": PASS_STATUS, "action": "SKIP_SESSION_ALREADY_PLANNED", "changed": 0}
        _ddl(connection)
        changed = 0
        for activity_id in changed_ids:
            source = original_by_id[activity_id]
            effective = effective_by_id[activity_id]
            effective_digest = u13.digest(
                {
                    "migration_task_id": TASK_ID,
                    "base_activity_id": activity_id,
                    "base_activity_digest": str(source["activity_digest"]),
                    "effective_scene_ref_id": str(effective["scene_ref_id"]),
                    "effective_situation_family": str(effective["situation_family"]),
                    "effective_setting": str(effective["setting"]),
                    "effective_scene_anchors": json.loads(str(effective["scene_anchors_json"])),
                    "effective_task_angle": str(effective["task_angle"]),
                    "effective_pattern_family_ids": json.loads(str(effective["pattern_family_ids_json"])),
                    "effective_practice_projection": json.loads(str(effective["practice_projection_json"])),
                }
            )
            cursor = connection.execute(
                """UPDATE u01qb13_blueprint_activities
                   SET scene_ref_id=?,situation_family=?,setting=?,scene_anchors_json=?,
                       task_angle=?,pattern_family_ids_json=?,practice_projection_json=?,
                       activity_digest=?
                   WHERE activity_id=? AND activity_digest=?""",
                (
                    str(effective["scene_ref_id"]),
                    str(effective["situation_family"]),
                    str(effective["setting"]),
                    str(effective["scene_anchors_json"]),
                    str(effective["task_angle"]),
                    str(effective["pattern_family_ids_json"]),
                    str(effective["practice_projection_json"]),
                    effective_digest,
                    activity_id,
                    str(source["activity_digest"]),
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise SupportStageSceneSwapError(f"BLUEPRINT_ACTIVITY_CONCURRENT_DRIFT:{activity_id}")
            partner_form = donor_form if int(source["form_ordinal"]) == int(form_ordinal) else int(form_ordinal)
            connection.execute(
                f"""INSERT INTO {MIGRATION_TABLE}
                (activity_id,form_ordinal,partner_form_ordinal,original_scene_ref_id,
                 effective_scene_ref_id,original_activity_digest,effective_activity_digest,
                 applied_at,migration_session_id)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    activity_id,
                    int(source["form_ordinal"]),
                    int(partner_form),
                    str(source["scene_ref_id"]),
                    str(effective["scene_ref_id"]),
                    str(source["activity_digest"]),
                    effective_digest,
                    applied_at,
                    session_id,
                ),
            )
            changed += 1

        after_rows = r4r3._all_rows(connection)
        if len(after_rows) != len(all_rows):
            connection.rollback()
            raise SupportStageSceneSwapError("POST_SWAP_ACTIVITY_COUNT_DRIFT")
        if len({str(row["scene_ref_id"]) for row in after_rows}) != len(
            {str(row["scene_ref_id"]) for row in all_rows}
        ):
            connection.rollback()
            raise SupportStageSceneSwapError("POST_SWAP_DISTINCT_SCENE_COUNT_DRIFT")
        before_exposure_counts = Counter(
            str(ref) for ref, _form in before_usage_counts
        )
        after_usage = r4r3._scene_usage(after_rows)
        after_exposure_counts = Counter(
            {ref: int(value["exposure_count"]) for ref, value in after_usage.items()}
        )
        if before_exposure_counts != after_exposure_counts:
            connection.rollback()
            raise SupportStageSceneSwapError("POST_SWAP_SCENE_EXPOSURE_COUNT_DRIFT")
        for target_form in (int(form_ordinal), int(donor_form)):
            before_families = Counter(
                str(row["situation_family"])
                for row in all_rows
                if int(row["form_ordinal"]) == target_form
            )
            after_families = Counter(
                str(row["situation_family"])
                for row in after_rows
                if int(row["form_ordinal"]) == target_form
            )
            if before_families != after_families:
                connection.rollback()
                raise SupportStageSceneSwapError(
                    f"POST_SWAP_FORM_FAMILY_COMPOSITION_DRIFT:F{target_form:02d}"
                )
        metadata = {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "last_current_form_ordinal": str(form_ordinal),
            "last_donor_form_ordinal": str(donor_form),
            "last_failing_scene_ref_id": str(failing_ref),
            "last_donor_scene_ref_id": str(donor_ref),
            "last_changed_activity_count": str(changed),
            "same_scene_same_skill_same_task_angle_repeat_allowed": "false",
            "questionbank_modified": "false",
            "new_scene_authored": "false",
            "bound_activities_modified": "false",
            "next_short_step": NEXT_SHORT_STEP,
        }
        connection.executemany(
            f"INSERT OR REPLACE INTO {METADATA_TABLE}(key,value) VALUES(?,?)",
            metadata.items(),
        )
        connection.commit()

    return {
        "status": PASS_STATUS,
        "action": "MIGRATED_SINGLE_EXPOSURE_SCENE_TO_RUNTIME_COMPATIBLE_SUPPORT_STAGE",
        "form_ordinal": int(form_ordinal),
        "failing_scene_ref_id": str(failing_ref),
        "donor_form_ordinal": int(donor_form),
        "donor_scene_ref_id": str(donor_ref),
        "changed": expected_changed,
        "questionbank_modified": False,
        "new_scene_authored": False,
        "bound_activities_modified": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
