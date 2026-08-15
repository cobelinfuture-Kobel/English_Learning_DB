#!/usr/bin/env python3
"""Reconcile R1B Form01 Reading task-angle attribution with actual learner-safe rows.

The R1B presentation adapter originally reconstructed Form01 Reading task angles by
activity position. Actual production evidence proved that a later runtime/materialized
row can carry a different learner-facing operation: Q07 is explicitly a first-mention
article task even though positional reconstruction labeled it KNOWN_REFERENCE_CONTEXT.

R1B-R1 does not change the 474-item QuestionBank, U01QB09 allocation authority,
U01QB13/U16/U18 runtime selection, scoring, scenes, learner state, or Unit02+.
It only reconciles the private printable projection from learner-safe prompt/stimulus
semantics before R1B renders its cue text. No answer/private field is read.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18h_r1b_unit01_form01_reading_task_angle_answer_position_and_orphan_heading_fullfix
    as r1b,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Presentation-only actual-row parity FullFix over the existing U01QB18H-R1B "
    "print consumer and unchanged 474-item QuestionBank. It uses only learner-safe "
    "prompt/stimulus semantics to distinguish FIRST_MENTION_CONTEXT from the prior "
    "positional fallback, never reads or exports correct answers/private_item_json, "
    "and creates no QuestionBank item, selector, planner, runtime, database, scoring "
    "authority, scene, Unit02-24 content, audio/Speaking score, or A2 content."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U01QB18H-R1B-R1_"
    "Unit01Form01ActualReadingTaskAngleParityFullFix"
)
PASS_STATUS = (
    "PASS_A1FS_V1_U01QB18H_R1B_R1_"
    "UNIT01_FORM01_ACTUAL_READING_TASK_ANGLE_PARITY_FULLFIX"
)
NEXT_SHORT_STEP = r1b.NEXT_SHORT_STEP

_ORIGINAL_ENRICH = r1b._enrich_form01_task_angles
_ORIGINAL_READING_CUE = r1b._reading_guided_cue


class Form01ActualReadingAngleParityError(ValueError):
    """Fail-closed learner-safe task-angle reconciliation error."""


def _learner_safe_reading_angle(
    activity: Mapping[str, Any],
    *,
    positional_fallback: str,
) -> str:
    """Resolve only semantics that are explicit in learner-visible text.

    We intentionally do not infer scoring truth. The exact phrase ``first mention``
    is emitted by the selected learner-facing task itself and is therefore stronger
    evidence than R1B's historical position-based reconstruction. Known-reference
    semantics are accepted only when the row already contains recoverable first-
    mention context, which is the same evidence R1B requires before rendering that cue.
    Otherwise the existing R1B positional fallback is preserved.
    """
    if str(activity.get("skill") or "").upper() != "READING":
        return positional_fallback

    prompt = str(activity.get("prompt") or "").strip().casefold()
    stimulus = str(activity.get("stimulus") or "").strip().casefold()
    learner_text = f"{prompt} {stimulus}"

    if "first mention" in learner_text:
        return "FIRST_MENTION_CONTEXT"

    if any(
        marker in learner_text
        for marker in (
            "same thing again",
            "same thing",
            "already mentioned",
            "known reference",
            "second mention",
            "mentioned before",
        )
    ):
        return "KNOWN_REFERENCE_CONTEXT"

    probe = dict(activity)
    probe["task_angle"] = "KNOWN_REFERENCE_CONTEXT"
    if r1b._known_reference_context(probe):
        return "KNOWN_REFERENCE_CONTEXT"

    return positional_fallback


def _enrich_form01_task_angles_actual(
    student: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep R1B structure/count guards, then reconcile actual Reading semantics."""
    enriched = deepcopy(_ORIGINAL_ENRICH(student))
    if int(enriched.get("form_ordinal", 0) or 0) != 1:
        return enriched

    for row in enriched.get("activities") or []:
        if str(row.get("skill") or "").upper() != "READING":
            continue
        fallback = str(row.get("task_angle") or "")
        resolved = _learner_safe_reading_angle(
            row,
            positional_fallback=fallback,
        )
        row["task_angle"] = resolved
    return enriched


def _reading_guided_cue_actual(activity: Mapping[str, Any]) -> str:
    if str(activity.get("skill") or "").upper() != "READING":
        return ""
    angle = str(activity.get("task_angle") or "")
    if angle == "FIRST_MENTION_CONTEXT":
        return "First mention: choose the article for something introduced now."
    return _ORIGINAL_READING_CUE(activity)


def _install() -> tuple[Any, Any]:
    previous_enrich = r1b._enrich_form01_task_angles
    previous_cue = r1b._reading_guided_cue
    r1b._enrich_form01_task_angles = _enrich_form01_task_angles_actual
    r1b._reading_guided_cue = _reading_guided_cue_actual
    return previous_enrich, previous_cue


def _restore(previous: tuple[Any, Any]) -> None:
    previous_enrich, previous_cue = previous
    r1b._enrich_form01_task_angles = previous_enrich
    r1b._reading_guided_cue = previous_cue


def render_form_html(student: Mapping[str, Any]) -> str:
    previous = _install()
    try:
        return r1b.render_form_html(student)
    finally:
        _restore(previous)


def materialize_twelve_form_pdfs(**kwargs: Any) -> dict[str, Any]:
    previous = _install()
    try:
        return r1b.materialize_twelve_form_pdfs(**kwargs)
    finally:
        _restore(previous)


def main(argv: Sequence[str] | None = None) -> int:
    previous = _install()
    try:
        result = r1b.main(argv)
    finally:
        _restore(previous)
    if result == 0:
        print(f"R1B_R1_STATUS={PASS_STATUS}")
        print(f"R1B_R1_NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
