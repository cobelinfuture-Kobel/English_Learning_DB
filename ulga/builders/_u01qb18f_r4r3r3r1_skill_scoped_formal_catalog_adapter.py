"""Scope the R4R3R3 formal capacity probe to the runtime's skill lessons.

Actual production R4 replay proved that Unit01 does not have one monolithic
lesson_id in ``u01qb02_item_catalog``.  The canonical runtime materializes one
lesson per skill, e.g. ``...:READING``, ``...:WRITING`` and ``...:SPEAKING``.
R4R3R3 incorrectly required the whole Unit01 catalog to contain exactly one
lesson_id before its formal donor probe could start.

This adapter changes only that private probe assumption.  Reading formal
capacity is evaluated against the Reading lesson catalog/scoring authority and
Writing against the Writing lesson catalog/scoring authority.  Speaking remains
covered by the existing task-capacity gate and is not passed through U16's
learner-visible scored-item matcher.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb18f_r4r3r3_formal_learner_visible_donor_admission_fullfix as r4r3r3

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Skill-scoped read-only runtime catalog adapter for the existing R4R3R3 formal "
    "donor probe. It authors no content and changes no QuestionBank, scene, learner "
    "evidence, scoring/runtime/planner authority, Unit02-24, audio, Speaking scoring, "
    "or A2 state."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R3R3R1_SkillScopedFormalCatalogDenominatorFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R3R3R1_SKILL_SCOPED_FORMAL_CATALOG_DENOMINATOR_FULLFIX"
NEXT_SHORT_STEP = r4r3r3.NEXT_SHORT_STEP

_FORMAL_SKILLS = ("READING", "WRITING")
_KNOWN_SKILLS = frozenset({"READING", "WRITING", "SPEAKING"})
_ORIGINAL_FORMAL_RUNTIME_STATE = r4r3r3._formal_runtime_state
_ORIGINAL_FORMAL_PAIR_PASSES = r4r3r3._formal_pair_passes
_INSTALLED = False


class SkillScopedFormalCatalogError(ValueError):
    """Fail-closed skill-scoped formal catalog error."""


def _lesson_skill(lesson_id: str) -> str | None:
    suffix = str(lesson_id).rsplit(":", 1)[-1].upper()
    return suffix if suffix in _KNOWN_SKILLS else None


def _skill_scoped_formal_runtime_state(
    database: Path,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, str]]]:
    """Load one formal catalog/scoring authority per canonical skill lesson."""
    catalog_by_skill: dict[str, list[dict[str, Any]]] = {}
    scoring_by_skill: dict[str, dict[str, str]] = {}
    lesson_by_skill: dict[str, str] = {}

    with closing(sqlite3.connect(Path(database))) as connection:
        connection.row_factory = sqlite3.Row
        lesson_ids = [
            str(row[0])
            for row in connection.execute(
                "SELECT DISTINCT lesson_id FROM u01qb02_item_catalog ORDER BY lesson_id"
            )
        ]
        for lesson_id in lesson_ids:
            skill = _lesson_skill(lesson_id)
            if skill is None:
                continue
            if skill in lesson_by_skill:
                raise SkillScopedFormalCatalogError(
                    f"R4R3R3R1_SKILL_LESSON_DENOMINATOR_INVALID:{skill}:"
                    f"{lesson_by_skill[skill]},{lesson_id}"
                )
            lesson_by_skill[skill] = lesson_id
            catalog = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM u01qb02_item_catalog WHERE lesson_id=? ORDER BY item_id",
                    (lesson_id,),
                )
            ]
            scoring = matching.load_runtime_item_scoring_classes(
                connection,
                lesson_id=lesson_id,
            )
            if not catalog or set(scoring) != {
                str(row["item_id"]) for row in catalog
            }:
                raise SkillScopedFormalCatalogError(
                    f"R4R3R3R1_RUNTIME_SCORING_CLASS_CATALOG_IDENTITY_MISMATCH:{skill}"
                )
            catalog_by_skill[skill] = catalog
            scoring_by_skill[skill] = scoring

    missing = [skill for skill in _FORMAL_SKILLS if skill not in catalog_by_skill]
    if missing:
        raise SkillScopedFormalCatalogError(
            "R4R3R3R1_REQUIRED_SKILL_LESSON_MISSING:" + ",".join(missing)
        )
    return catalog_by_skill, scoring_by_skill


def _skill_scoped_formal_pair_passes(
    *,
    simulated: Sequence[Mapping[str, Any]],
    current_form: int,
    donor_form: int,
    current_choices: Mapping[str, Mapping[str, tuple[str, ...]]],
    donor_choices: Mapping[str, Mapping[str, tuple[str, ...]]],
    catalog: Mapping[str, Sequence[Mapping[str, Any]]],
    scoring: Mapping[str, Mapping[str, str]],
) -> bool:
    """Apply the exact formal matcher using the catalog for each scored skill."""
    reading_catalog = catalog.get("READING")
    reading_scoring = scoring.get("READING")
    writing_catalog = catalog.get("WRITING")
    writing_scoring = scoring.get("WRITING")
    if reading_catalog is None or reading_scoring is None:
        raise SkillScopedFormalCatalogError("R4R3R3R1_READING_FORMAL_STATE_MISSING")
    if writing_catalog is None or writing_scoring is None:
        raise SkillScopedFormalCatalogError("R4R3R3R1_WRITING_FORMAL_STATE_MISSING")

    current_reading = r4r3r3._effective_reading_rows(
        simulated,
        form_ordinal=current_form,
        choices=current_choices["READING"],
    )
    donor_reading = r4r3r3._effective_reading_rows(
        simulated,
        form_ordinal=donor_form,
        choices=donor_choices["READING"],
    )
    if not r4r3r3._formal_assignment_exists(
        current_reading,
        catalog=reading_catalog,
        scoring=reading_scoring,
        form_ordinal=current_form,
        skill="READING",
    ):
        return False
    if not r4r3r3._formal_assignment_exists(
        donor_reading,
        catalog=reading_catalog,
        scoring=reading_scoring,
        form_ordinal=donor_form,
        skill="READING",
    ):
        return False
    if not r4r3r3._writing_form_exists(
        simulated,
        form_ordinal=current_form,
        catalog=writing_catalog,
        scoring=writing_scoring,
    ):
        return False
    if not r4r3r3._writing_form_exists(
        simulated,
        form_ordinal=donor_form,
        catalog=writing_catalog,
        scoring=writing_scoring,
    ):
        return False
    return True


def install() -> None:
    global _INSTALLED
    if installed():
        _INSTALLED = True
        return
    if r4r3r3._formal_runtime_state is not _ORIGINAL_FORMAL_RUNTIME_STATE:
        raise SkillScopedFormalCatalogError("R4R3R3_FORMAL_RUNTIME_STATE_OWNER_DRIFT")
    if r4r3r3._formal_pair_passes is not _ORIGINAL_FORMAL_PAIR_PASSES:
        raise SkillScopedFormalCatalogError("R4R3R3_FORMAL_PAIR_OWNER_DRIFT")
    r4r3r3._formal_runtime_state = _skill_scoped_formal_runtime_state
    r4r3r3._formal_pair_passes = _skill_scoped_formal_pair_passes
    _INSTALLED = True


def installed() -> bool:
    return (
        _INSTALLED
        and r4r3r3._formal_runtime_state is _skill_scoped_formal_runtime_state
        and r4r3r3._formal_pair_passes is _skill_scoped_formal_pair_passes
    )
