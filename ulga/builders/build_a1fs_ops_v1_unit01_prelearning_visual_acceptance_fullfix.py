#!/usr/bin/env python3
"""Close Unit01 Pre-Learning learner-facing visual acceptance residuals.

This adapter is intentionally narrow. It reuses the approved V2 payload and the
Windows-safe Edge/Chromium materialization path, then removes system-only wording
from the learner projection, aligns the location frame with admitted support
language, and improves printed choice/writing readability. It does not change
QuestionBank authority, runtime items, Real62, teacher-private files, Unit02-24,
A2, scoring, learner state, or production activation.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_questionbank_student_package_phrase_to_sentence
    as student_builder,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_windows_chromium_render_fullfix as windows_fullfix,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reprojects only the already approved Unit01 Pre-Learning V2 learner HTML/CSS "
    "for final visual acceptance. It removes system-only labels, aligns one child "
    "frame with already admitted support language, and improves print spacing. It "
    "creates no canonical content, question, answer, QuestionBank, learner state, "
    "score, teacher output, audio, A2 content, Unit02-24 artifact, or production "
    "activation."
)
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = "A1FS-OPS-V1_Unit01PreLearningVisualAcceptanceFullFix"
PASS_STATUS = (
    "PASS_A1FS_OPS_V1_UNIT01_PRELEARNING_VISUAL_ACCEPTANCE_FULLFIX"
)

VISUAL_ACCEPTANCE_CSS = """
/* UNIT01_PRELEARNING_VISUAL_ACCEPTANCE */
.guided-check span{display:inline-block;margin-right:24px}
.guided-check span:last-child{margin-right:0}
.writing-step .answer-line{min-height:26px}
.reference-grid{grid-template-columns:.95fr .95fr 1.20fr}
"""

FORBIDDEN_LEARNER_MARKERS = (
    "authority frames",
    "placeholder",
    "PRELEARNING_READY",
    "mastery",
)
REQUIRED_LEARNER_MARKERS = (
    "Ready Check｜我準備好了嗎？",
    "The ______ is in/on/near the ______.",
    "不是數量很多",
)


def _learner_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    projected = dict(payload)

    degree = dict(projected.get("degree_intensifier") or {})
    degree["guide"] = "放在形容詞前面，表示程度更強，意思是很／非常；不是數量很多。"
    projected["degree_intensifier"] = degree

    frames = [dict(row) for row in projected.get("learner_frames") or []]
    for row in frames:
        if row.get("frame_id") == "LEARNER_FRAME_04":
            row["model"] = "The ______ is in/on/near the ______."
    projected["learner_frames"] = frames
    return projected


def _learner_html(base_html, payload: Mapping[str, Any]) -> str:
    html = str(base_html(_learner_payload(payload)))
    html = html.replace(
        "同一個名詞先用a/an介紹，再用the說同一個東西。",
        "第一次介紹一個東西時常用a/an；再次說同一個、已知道的東西時常用the。",
    )
    html = re.sub(
        r'<p class="teacher-system-note">.*?</p>',
        "",
        html,
        flags=re.DOTALL,
    )
    html = html.replace(
        "<strong>PRELEARNING_READY</strong>",
        "<strong>Ready Check｜我準備好了嗎？</strong>",
    )
    html = html.replace(
        "這只代表可以進入正式QuestionBank，不代表已經mastery。",
        "這只代表可以進入正式QuestionBank，不代表已經完全熟練。",
    )
    errors = validate_learner_projection(html)
    if errors:
        raise ValueError(
            "prelearning_visual_acceptance_contract_failed:" + ",".join(errors)
        )
    return html


def validate_learner_projection(rendered_html: str) -> list[str]:
    html = str(rendered_html or "")
    errors: list[str] = []
    for marker in FORBIDDEN_LEARNER_MARKERS:
        if marker in html:
            errors.append("system_marker_exposed:" + marker)
    for marker in REQUIRED_LEARNER_MARKERS:
        if marker not in html:
            errors.append("learner_marker_missing:" + marker)
    if html.count('class="print-page"') != 7:
        errors.append("print_section_count_invalid")
    return errors


def install_fullfix() -> dict[str, Any]:
    """Install V2, then close only final learner-facing visual residuals."""
    windows_fullfix.prelearning_v2.install_fullfix()
    base_html = student_builder._prelearning_html
    previous = {
        "html": base_html,
        "css": student_builder.STUDENT_CSS,
    }

    def projected_html(payload: Mapping[str, Any]) -> str:
        return _learner_html(base_html, payload)

    student_builder._prelearning_html = projected_html
    if "UNIT01_PRELEARNING_VISUAL_ACCEPTANCE" not in student_builder.STUDENT_CSS:
        student_builder.STUDENT_CSS += "\n" + VISUAL_ACCEPTANCE_CSS
    return previous


def main(argv: Sequence[str] | None = None) -> int:
    install_fullfix()
    windows_fullfix.install_fullfix()
    return windows_fullfix.local_operator.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
