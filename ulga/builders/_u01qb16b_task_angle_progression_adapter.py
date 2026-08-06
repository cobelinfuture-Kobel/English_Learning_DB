"""Pedagogical task-angle progression guard for Unit01 twelve-form allocation.

U01QB09 already defines the four support bands (GUIDED, REDUCED_SUPPORT,
INDEPENDENT, TRANSFER), but several Reading angles are only different labels for
the same learner capability. In particular ARTICLE_CONTROL,
FIRST_MENTION_CONTEXT and TRANSFER_DECISION all measure first-mention article
selection. Real Form01 use showed that choosing two such labels in one scene can
produce eight near-identical a/an/the questions despite a formally diverse
blueprint.

This adapter preserves the existing scene rotation, support bands, 474-item
QuestionBank, pattern families, scoring contracts and learner state. It
strengthens the existing U01QB09/U01QB14R1 allocation boundary only where the
current bank has proven capacity: the two Reading activities inside one scene
must be different pedagogical capability classes. Reused scenes continue to use
the existing exact-task-angle replay prohibition plus support/perspective change
contract; cross-exposure capability-class novelty is not imposed because the
current 288-base capacity proof demonstrates that some reused scenes cannot
safely satisfy that stronger rule.
"""
from __future__ import annotations

from typing import Any, Sequence

from ulga.builders import (
    build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09,
)
from ulga.builders import (
    build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_allocation,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Deterministic pedagogical-capability diversity guard over the existing U01QB09/U01QB14R1 task-angle allocation; no learner content, scene, QuestionBank, scoring, planner, database, Unit02-24 content, audio, speaking scoring, or A2 content is created or mutated."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB16B_Unit01TwelveFormTaskAngleAndSupportProgressionReconciliation"
PASS_STATUS = "PASS_A1FS_V1_U01QB16B_UNIT01_TWELVE_FORM_TASK_ANGLE_AND_SUPPORT_PROGRESSION_RECONCILIATION"
NEXT_SHORT_STEP = "A1FS-V1-U01QB16C_ExistingProductUnboundFormProgressionOverlayMigration"

FIRST_MENTION_SELECTION = "FIRST_MENTION_SELECTION"
KNOWN_REFERENCE_USE = "KNOWN_REFERENCE_USE"
ERROR_DISCRIMINATION = "ERROR_DISCRIMINATION"
REFERENCE_EVIDENCE = "REFERENCE_EVIDENCE"

READING_CAPABILITY_CLASS = {
    "ARTICLE_CONTROL": FIRST_MENTION_SELECTION,
    "FIRST_MENTION_CONTEXT": FIRST_MENTION_SELECTION,
    "TRANSFER_DECISION": FIRST_MENTION_SELECTION,
    "KNOWN_REFERENCE_CONTEXT": KNOWN_REFERENCE_USE,
    "ERROR_CHECK": ERROR_DISCRIMINATION,
    "REFERENCE_EVIDENCE": REFERENCE_EVIDENCE,
}

_ORIGINAL_CHOOSE_ANGLES = u01qb09.choose_angles
_ORIGINAL_SCENE_OPTIONS = runtime_allocation._scene_options
_INSTALLED = False


class TaskAngleProgressionError(u01qb09.AllocationError):
    pass


def capability_class(skill: str, angle: str) -> str:
    if str(skill).upper() != "READING":
        return str(angle)
    return READING_CAPABILITY_CLASS.get(str(angle), str(angle))


def _reading_classes(angles: Sequence[str]) -> tuple[str, ...]:
    return tuple(capability_class("READING", angle) for angle in angles)


def choose_angles(
    support: str,
    skill: str,
    previous: set[str],
    count: int,
) -> list[str]:
    """Choose Reading angles with distinct capability classes per exposure."""
    skill = str(skill).upper()
    if skill != "READING":
        return _ORIGINAL_CHOOSE_ANGLES(support, skill, previous, count)

    candidates = list(u01qb09.SUPPORT_PROFILES[support]["candidates"][skill])
    selected: list[str] = []
    selected_classes: set[str] = set()
    for angle in candidates:
        if angle in previous:
            continue
        angle_class = capability_class(skill, angle)
        if angle_class in selected_classes:
            continue
        selected.append(angle)
        selected_classes.add(angle_class)
        if len(selected) == count:
            return selected

    raise TaskAngleProgressionError(
        f"READING_PEDAGOGICAL_CAPABILITY_CAPACITY_INSUFFICIENT:{support}:{count}"
    )


def scene_options(*args: Any, **kwargs: Any):
    """Filter runtime-capable options to distinct Reading capability classes."""
    options = _ORIGINAL_SCENE_OPTIONS(*args, **kwargs)
    skill = str(kwargs.get("skill") or "").upper()
    if skill != "READING":
        return options

    filtered = []
    for option in options:
        angles, _candidate_sets = option
        classes = _reading_classes(angles)
        if len(classes) != len(set(classes)):
            continue
        filtered.append(option)
    if filtered:
        return filtered

    support = str(kwargs.get("support") or "")
    scene_ref_id = str(kwargs.get("scene_ref_id") or "")
    raise runtime_allocation.RuntimeTaskAwareAllocationError(
        "SCENE_READING_PEDAGOGICAL_CAPABILITY_CAPACITY_INSUFFICIENT:"
        f"{scene_ref_id}:{support}"
    )


def install() -> None:
    global _INSTALLED
    if (
        u01qb09.choose_angles is choose_angles
        and runtime_allocation._scene_options is scene_options
    ):
        _INSTALLED = True
        return
    if u01qb09.choose_angles is not _ORIGINAL_CHOOSE_ANGLES:
        raise TaskAngleProgressionError(
            "U01QB09_CHOOSE_ANGLES_ALREADY_PATCHED_BY_OTHER_AUTHORITY"
        )
    if runtime_allocation._scene_options is not _ORIGINAL_SCENE_OPTIONS:
        raise TaskAngleProgressionError(
            "U01QB14R1_SCENE_OPTIONS_ALREADY_PATCHED_BY_OTHER_AUTHORITY"
        )
    u01qb09.choose_angles = choose_angles
    runtime_allocation._scene_options = scene_options
    _INSTALLED = True


def installed() -> bool:
    return (
        _INSTALLED
        and u01qb09.choose_angles is choose_angles
        and runtime_allocation._scene_options is scene_options
    )
