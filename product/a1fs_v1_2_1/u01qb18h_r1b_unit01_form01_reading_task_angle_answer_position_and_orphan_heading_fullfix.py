#!/usr/bin/env python3
"""FullFix the three human-review blockers proven by the actual Unit01 Form01 PDF.

R1B is a presentation-only adapter over the already-merged U01QB18H-R1/R1A PDF
materializer. It does not change the 474-item QuestionBank, U01QB09 allocation,
U01QB13/U16/U18 selection, scoring, scenes, runtime, learner state, or Unit02+.

The actual Form01 human review proved three defects:
* VISUAL_ORPHAN_SCENE_HEADING
* READING_CORRECT_OPTION_COLLAPSE
* READING_TASK_ANGLE_COLLAPSE

R1B resolves them without answer-side access. Form01 task angles are derived from
the existing U01QB09 GUIDED allocation owner, learner-facing Reading cues express
the already-approved task-angle distinction without exposing engineering IDs,
multiple-choice options are deterministically rotated by question ordinal to
remove fixed-position answer bias while preserving the exact option set, and each
scene heading is kept with its first activity for print pagination.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as base,
)
from ulga.builders import (
    build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Presentation-only Form01 human-review FullFix over the existing U01QB18H-R1/R1A "
    "print consumer. It derives task-angle identity from the existing U01QB09 GUIDED "
    "allocation owner, changes only learner-facing cue wording, option display order, "
    "and print pagination structure, never reads or exports correct answers, and creates "
    "no QuestionBank item, selector, planner, runtime, database, scoring authority, scene, "
    "Unit02-24 content, audio/Speaking score, or A2 content."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U01QB18H-R1B_"
    "Unit01Form01ReadingTaskAngleAndAnswerDiversityPlusOrphanHeadingFullFix"
)
PASS_STATUS = (
    "PASS_A1FS_V1_U01QB18H_R1B_"
    "UNIT01_FORM01_READING_TASK_ANGLE_ANSWER_POSITION_ORPHAN_HEADING_FULLFIX"
)
NEXT_SHORT_STEP = (
    "A1FS-V1-U01QB18H-R1C_"
    "Unit01Form01ActualRerenderHumanVisualAndPedagogicalReacceptance"
)

_FORM01_ORDINAL = 1
_EXPECTED_PER_SCENE = {"READING": 2, "WRITING": 2, "SPEAKING": 1}
_ORIGINAL_RENDER_FORM_HTML = base.render_form_html
_ORIGINAL_CLEAN_STIMULUS = base._clean_stimulus
_ORIGINAL_RESPONSE_HTML = base._response_html


class Form01PdfR1BError(ValueError):
    """Fail-closed R1B projection error."""


def _guided_angle_plan() -> dict[str, tuple[str, ...]]:
    support = u01qb09.support_for_form(_FORM01_ORDINAL)
    if support != "GUIDED":
        raise Form01PdfR1BError(f"FORM01_SUPPORT_DRIFT:{support}")
    plan = {
        skill: tuple(
            u01qb09.choose_angles(
                support,
                skill,
                set(),
                count,
            )
        )
        for skill, count in _EXPECTED_PER_SCENE.items()
    }
    expected = {
        "READING": ("ARTICLE_CONTROL", "FIRST_MENTION_CONTEXT"),
        "WRITING": ("PHRASE_CONSTRUCTION", "WORD_ORDER"),
        "SPEAKING": ("SCENE_DESCRIPTION",),
    }
    if plan != expected:
        raise Form01PdfR1BError(f"FORM01_GUIDED_ANGLE_PLAN_DRIFT:{plan}:{expected}")
    return plan


def _enrich_form01_task_angles(student: Mapping[str, Any]) -> dict[str, Any]:
    """Attach existing U01QB09 task-angle identity to the private review projection.

    The R4 student_form intentionally strips answer/private scoring metadata and also
    omits task_angle. For Form01 the exact task-angle order is deterministic in U01QB09:
    every first exposure receives the same GUIDED per-skill angle sequence. R1B derives
    that identity from U01QB09 rather than creating a second allocation authority.
    """
    value = deepcopy(dict(student))
    if int(value.get("form_ordinal", 0) or 0) != _FORM01_ORDINAL:
        return value

    scenes = [str(row.get("scene_ref_id") or "") for row in value.get("scenes") or []]
    if len(scenes) != base.EXPECTED_SCENE_COUNT or len(set(scenes)) != len(scenes):
        raise Form01PdfR1BError(f"FORM01_SCENE_IDENTITY_INVALID:{scenes}")
    plan = _guided_angle_plan()
    by_scene_skill: dict[str, Counter[str]] = defaultdict(Counter)
    enriched: list[dict[str, Any]] = []

    for source in value.get("activities") or []:
        row = dict(source)
        ref = str(row.get("scene_ref_id") or "")
        skill = str(row.get("skill") or "").upper()
        if ref not in scenes or skill not in plan:
            raise Form01PdfR1BError(
                f"FORM01_ACTIVITY_IDENTITY_INVALID:{row.get('question_number')}:{ref}:{skill}"
            )
        index = int(by_scene_skill[ref][skill])
        angles = plan[skill]
        if index >= len(angles):
            raise Form01PdfR1BError(
                f"FORM01_SKILL_ACTIVITY_OVERFLOW:{ref}:{skill}:{index}:{len(angles)}"
            )
        row["task_angle"] = angles[index]
        by_scene_skill[ref][skill] += 1
        enriched.append(row)

    for ref in scenes:
        actual = dict(by_scene_skill[ref])
        if actual != _EXPECTED_PER_SCENE:
            raise Form01PdfR1BError(
                f"FORM01_SCENE_SKILL_COUNTS_INVALID:{ref}:{actual}:{_EXPECTED_PER_SCENE}"
            )
    value["activities"] = enriched
    return value


def _reading_guided_cue(activity: Mapping[str, Any]) -> str:
    if str(activity.get("skill") or "").upper() != "READING":
        return ""
    angle = str(activity.get("task_angle") or "")
    if angle == "ARTICLE_CONTROL":
        return "Phrase check: choose the article that fits this phrase."
    if angle == "FIRST_MENTION_CONTEXT":
        return "First mention: this is a new thing in the scene."
    raise Form01PdfR1BError(
        f"FORM01_READING_TASK_ANGLE_INVALID:{activity.get('question_number')}:{angle}"
    )


def _clean_stimulus_r1b(activity: Mapping[str, Any]) -> str:
    value = _ORIGINAL_CLEAN_STIMULUS(activity)
    cue = _reading_guided_cue(activity)
    if not cue:
        return value
    return f"{cue} · {value}" if value else cue


def _question_ordinal(activity: Mapping[str, Any]) -> int:
    match = re.fullmatch(r"Q(\d{2})", str(activity.get("question_number") or ""))
    if not match:
        raise Form01PdfR1BError(
            f"FORM01_QUESTION_NUMBER_INVALID:{activity.get('question_number')}"
        )
    return int(match.group(1))


def _rotate_reading_options(activity: Mapping[str, Any]) -> dict[str, Any]:
    """Rotate display positions without reading answer-side metadata or changing values."""
    value = dict(activity)
    if (
        str(value.get("skill") or "").upper() != "READING"
        or str(value.get("response_mode") or "") != "select_one"
    ):
        return value
    options = list(value.get("options") or [])
    if len(options) < 2:
        raise Form01PdfR1BError(
            f"FORM01_READING_OPTIONS_INVALID:{value.get('question_number')}:{options}"
        )
    offset = (_question_ordinal(value) - 1) % len(options)
    value["options"] = options[offset:] + options[:offset]
    return value


def _response_html_r1b(activity: Mapping[str, Any]) -> str:
    return _ORIGINAL_RESPONSE_HTML(_rotate_reading_options(activity))


def _bind_scene_heading_to_first_activity(document: str) -> str:
    pattern = re.compile(
        r'(<section class="scene-section">)'
        r'(<div class="scene-heading">.*?</div>)'
        r'(<article class="activity">.*?</article>)',
        flags=re.S,
    )

    def replacement(match: re.Match[str]) -> str:
        return (
            match.group(1)
            + '<div class="scene-lead">'
            + match.group(2)
            + match.group(3)
            + "</div>"
        )

    value, count = pattern.subn(replacement, document)
    if count != base.EXPECTED_SCENE_COUNT:
        raise Form01PdfR1BError(
            f"FORM01_SCENE_LEAD_WRAP_COUNT_INVALID:{count}:{base.EXPECTED_SCENE_COUNT}"
        )
    css = (
        "\n.scene-lead{break-inside:avoid;page-break-inside:avoid}\n"
        ".scene-heading{break-inside:avoid;page-break-inside:avoid;"
        "break-after:avoid-page;page-break-after:avoid}\n"
    )
    if "</style>" not in value:
        raise Form01PdfR1BError("FORM01_STYLE_BLOCK_MISSING")
    return value.replace("</style>", css + "</style>", 1)


def render_form_html(student: Mapping[str, Any]) -> str:
    """Delegate the established R1 renderer, strengthening Form01 only."""
    if int(student.get("form_ordinal", 0) or 0) != _FORM01_ORDINAL:
        return _ORIGINAL_RENDER_FORM_HTML(student)

    enriched = _enrich_form01_task_angles(student)
    previous_clean = base._clean_stimulus
    previous_response = base._response_html
    base._clean_stimulus = _clean_stimulus_r1b
    base._response_html = _response_html_r1b
    try:
        document = _ORIGINAL_RENDER_FORM_HTML(enriched)
    finally:
        base._clean_stimulus = previous_clean
        base._response_html = previous_response

    document = _bind_scene_heading_to_first_activity(document)
    lowered = document.casefold()
    for engineering_id in ("article_control", "first_mention_context"):
        if engineering_id in lowered:
            raise Form01PdfR1BError(
                f"FORM01_ENGINEERING_TASK_ANGLE_LEAK:{engineering_id}"
            )
    return document


def materialize_twelve_form_pdfs(**kwargs: Any) -> dict[str, Any]:
    """Use the existing R1/R1A materializer with the Form01 R1B renderer installed."""
    previous = base.render_form_html
    base.render_form_html = render_form_html
    try:
        return base.materialize_twelve_form_pdfs(**kwargs)
    finally:
        base.render_form_html = previous


def main(argv: Sequence[str] | None = None) -> int:
    previous = base.render_form_html
    base.render_form_html = render_form_html
    try:
        result = base.main(argv)
    finally:
        base.render_form_html = previous
    if result == 0:
        print(f"R1B_STATUS={PASS_STATUS}")
        print(f"R1B_NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
