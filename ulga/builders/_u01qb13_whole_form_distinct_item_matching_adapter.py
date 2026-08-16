"""Whole-form distinct-item reservation adapter for U01QB13 runtime execution.

U01QB14R1 already proves that every form/skill activity set has a distinct-item
matching in the active 474-item catalog.  U01QB13 historically selected items
activity-by-activity with a greedy rank, which can consume an item needed by a
later activity even when a full matching exists.  This adapter preserves the
existing U01QB13 session-plan, item-selection rank, exposure, filler, response,
and scoring paths; it only reserves one distinct runtime item per blueprint
activity before delegating back to the canonical assembler.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u01qb13

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Runtime selection adapter over the existing U01QB13/U01QB02 catalog and session authority; it changes only greedy item assignment into whole-form distinct matching and creates no content, bank, planner, runtime, scoring, or learner-state authority."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB13_WholeFormDistinctItemMatchingRuntimeFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB13_WHOLE_FORM_DISTINCT_ITEM_MATCHING_RUNTIME_FULLFIX"


class WholeFormDistinctItemMatchingError(ValueError):
    pass


_ORIGINAL_ASSEMBLE = u01qb13.assemble_form_component
_ORIGINAL_CANDIDATE_RANK = u01qb13._candidate_rank
_INSTALLED = False
_ACTIVE_RESERVATIONS: dict[str, str] | None = None


def _solve_distinct_reservations(
    candidates_by_activity: Mapping[str, Sequence[tuple[tuple[Any, ...], str]]],
) -> dict[str, str]:
    """Find one deterministic distinct item per activity or fail closed."""
    normalized: dict[str, tuple[tuple[tuple[Any, ...], str], ...]] = {}
    for activity_id, rows in candidates_by_activity.items():
        ordered = tuple(sorted(rows, key=lambda row: (row[0], row[1])))
        if not ordered:
            raise WholeFormDistinctItemMatchingError(
                f"WHOLE_FORM_ACTIVITY_HAS_NO_RUNTIME_CANDIDATE:{activity_id}"
            )
        normalized[str(activity_id)] = ordered

    activity_order = sorted(
        normalized,
        key=lambda activity_id: (len(normalized[activity_id]), activity_id),
    )
    reservations: dict[str, str] = {}
    used: set[str] = set()

    def solve(index: int) -> bool:
        if index == len(activity_order):
            return True
        activity_id = activity_order[index]
        for _rank, item_id in normalized[activity_id]:
            if item_id in used:
                continue
            used.add(item_id)
            reservations[activity_id] = item_id
            if solve(index + 1):
                return True
            reservations.pop(activity_id, None)
            used.remove(item_id)
        return False

    if not solve(0):
        detail = ";".join(
            f"{activity_id}=" + ",".join(item_id for _rank, item_id in normalized[activity_id])
            for activity_id in activity_order
        )
        raise WholeFormDistinctItemMatchingError(
            "WHOLE_FORM_DISTINCT_ITEM_MATCHING_UNSAT:" + detail
        )
    return dict(sorted(reservations.items()))


def _reserved_candidate_rank(
    *,
    row: Mapping[str, Any],
    anchors: set[str],
    situation_family: str,
    learner_id: str,
    session_id: str,
    activity_id: str,
    exposed: set[str],
    recent: set[str],
    assessment: bool,
    scene_ref_id: str | None = None,
    task_angle: str | None = None,
) -> tuple[Any, ...] | None:
    if _ACTIVE_RESERVATIONS is not None:
        reserved = _ACTIVE_RESERVATIONS.get(str(activity_id))
        if reserved is not None and str(row["item_id"]) != reserved:
            return None
    rank = _ORIGINAL_CANDIDATE_RANK(
        row=row,
        anchors=anchors,
        situation_family=situation_family,
        learner_id=learner_id,
        session_id=session_id,
        activity_id=activity_id,
        exposed=exposed,
        recent=recent,
        assessment=assessment,
        scene_ref_id=scene_ref_id,
        task_angle=task_angle,
    )
    if rank is None and _ACTIVE_RESERVATIONS is not None:
        # A systemic consumer guard may reject a pre-reserved candidate after
        # the formal probe. Release only this activity's reservation so the
        # existing distinct matcher can choose the next legal catalog item.
        _ACTIVE_RESERVATIONS.pop(str(activity_id), None)
    return rank


def _reservation_map(
    database,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
) -> dict[str, str] | None:
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    with runtime.write() as connection:
        connection.row_factory = __import__("sqlite3").Row
        session = runtime._active_session(
            connection,
            learner_id=learner_id,
            session_id=session_id,
        )
        skill = str(session["skill"])
        existing = connection.execute(
            "SELECT 1 FROM u01qb13_session_bindings WHERE session_id=? LIMIT 1",
            (session_id,),
        ).fetchone()
        if existing:
            return None
        if connection.execute(
            "SELECT 1 FROM u01qb02_session_plans WHERE session_id=?",
            (session_id,),
        ).fetchone():
            return None

        activities = [
            dict(row)
            for row in connection.execute(
                """SELECT * FROM u01qb13_blueprint_activities
                   WHERE form_ordinal=? AND skill=? ORDER BY activity_id""",
                (form_ordinal, skill),
            )
        ]
        expected_count = {
            "READING": u01qb13.READING_PER_FORM,
            "WRITING": u01qb13.WRITING_PER_FORM,
            "SPEAKING": u01qb13.SPEAKING_PER_FORM,
        }[skill]
        if len(activities) != expected_count:
            raise WholeFormDistinctItemMatchingError(
                f"WHOLE_FORM_ACTIVITY_COUNT_INVALID:{skill}:{len(activities)}:{expected_count}"
            )

        catalog = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM u01qb02_item_catalog WHERE lesson_id=? ORDER BY item_id",
                (session["lesson_id"],),
            )
        ]
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
                "SELECT item_id FROM u01qb02_item_exposures WHERE learner_id=? ORDER BY exposure_seq DESC LIMIT ?",
                (learner_id, qb02.RECENT_EXPOSURE_WINDOW),
            )
        }

        candidates_by_activity: dict[str, list[tuple[tuple[Any, ...], str]]] = {}
        for activity in activities:
            activity_id = str(activity["activity_id"])
            allowed = set(json.loads(str(activity["pattern_family_ids_json"])))
            anchors = {
                str(value).casefold()
                for value in json.loads(str(activity["scene_anchors_json"]))
            }
            rows: list[tuple[tuple[Any, ...], str]] = []
            for row in catalog:
                if str(row["pattern_family_id"]) not in allowed:
                    continue
                rank = _ORIGINAL_CANDIDATE_RANK(
                    row=row,
                    anchors=anchors,
                    situation_family=str(activity["situation_family"]),
                    learner_id=learner_id,
                    session_id=session_id,
                    activity_id=activity_id,
                    exposed=exposed,
                    recent=recent,
                    assessment=bool(activity["assessment_candidate"]),
                    scene_ref_id=str(activity["scene_ref_id"]),
                    task_angle=str(activity["task_angle"]),
                )
                if rank is not None:
                    rows.append((rank, str(row["item_id"])))
            candidates_by_activity[activity_id] = rows

    return _solve_distinct_reservations(candidates_by_activity)


def assemble_form_component_whole_form_matching(
    database,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    selected_at: str | None = None,
):
    global _ACTIVE_RESERVATIONS
    reservations = _reservation_map(
        database,
        learner_id=learner_id,
        session_id=session_id,
        form_ordinal=form_ordinal,
    )
    previous = _ACTIVE_RESERVATIONS
    _ACTIVE_RESERVATIONS = reservations
    try:
        return _ORIGINAL_ASSEMBLE(
            database,
            learner_id=learner_id,
            session_id=session_id,
            form_ordinal=form_ordinal,
            selected_at=selected_at,
        )
    finally:
        _ACTIVE_RESERVATIONS = previous


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    if u01qb13.assemble_form_component is not _ORIGINAL_ASSEMBLE:
        # Another explicit runtime adapter already owns this selector boundary.
        # Do not silently stack selector authorities.
        raise WholeFormDistinctItemMatchingError(
            "U01QB13_ASSEMBLER_ALREADY_PATCHED_BY_OTHER_AUTHORITY"
        )
    u01qb13._candidate_rank = _reserved_candidate_rank
    u01qb13.assemble_form_component = assemble_form_component_whole_form_matching
    _INSTALLED = True


def installed() -> bool:
    return (
        _INSTALLED
        and u01qb13._candidate_rank is _reserved_candidate_rank
        and u01qb13.assemble_form_component is assemble_form_component_whole_form_matching
    )
