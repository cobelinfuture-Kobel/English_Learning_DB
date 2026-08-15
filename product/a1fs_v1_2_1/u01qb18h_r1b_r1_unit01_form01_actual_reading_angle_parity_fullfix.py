#!/usr/bin/env python3
"""Reconcile R1B Form01 learner-safe presentation with actual production evidence.

This layer remains presentation-only. It preserves the 474-item QuestionBank,
U01QB09 allocation authority, U01QB13/U16/U18 runtime selection, scoring, scenes,
learner state, and Unit02+.

It performs two learner-facing reconciliations proven necessary by actual Form01:
1. resolve Reading task-angle semantics from learner-safe prompt/stimulus text before
   falling back to historical position-based attribution;
2. suppress a later learner-visible ``Example:`` segment when it reproduces the
   complete token set of an earlier learner-visible ordered-token task in the same
   Form, preventing one exercise from demonstrating another exercise's answer.

The materialization manifest is also stamped with this latest FullFix task identity
and current next step so SHA-bound human review cannot be attached to stale R1A
provenance. No answer/private field is read.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18h_r1b_unit01_form01_reading_task_angle_answer_position_and_orphan_heading_fullfix
    as r1b,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Presentation-only actual-row and human-review FullFix over the existing "
    "U01QB18H-R1B print consumer and unchanged 474-item QuestionBank. It uses only "
    "learner-safe prompt/stimulus and ordered-token text to reconcile Reading task "
    "semantics, suppress a later learner-visible example that reproduces an earlier "
    "learner-visible token phrase, and stamp the existing private materialization "
    "manifest with current FullFix provenance. It never reads or exports correct "
    "answers/private_item_json and creates no QuestionBank item, selector, planner, "
    "runtime, database, scoring authority, scene, Unit02-24 content, audio/Speaking "
    "score, or A2 content."
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
_ORIGINAL_R1B_RENDER = r1b.render_form_html
_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


class Form01ActualReadingAngleParityError(ValueError):
    """Fail-closed learner-safe presentation reconciliation error."""


def _learner_safe_reading_angle(
    activity: Mapping[str, Any],
    *,
    positional_fallback: str,
) -> str:
    """Resolve only semantics that are explicit in learner-visible text."""
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
        row["task_angle"] = _learner_safe_reading_angle(
            row,
            positional_fallback=fallback,
        )
    return enriched


def _reading_guided_cue_actual(activity: Mapping[str, Any]) -> str:
    if str(activity.get("skill") or "").upper() != "READING":
        return ""
    angle = str(activity.get("task_angle") or "")
    if angle == "FIRST_MENTION_CONTEXT":
        return "First mention: choose the article for something introduced now."
    return _ORIGINAL_READING_CUE(activity)


def _words(value: Any) -> list[str]:
    return [word.casefold() for word in _WORD_RE.findall(str(value or ""))]


def _ordered_token_signature(activity: Mapping[str, Any]) -> Counter[str]:
    if str(activity.get("response_mode") or "") != "ordered_tokens":
        return Counter()
    tokens = r1b.base._ordered_tokens(activity)
    words: list[str] = []
    for token in tokens:
        words.extend(_words(token))
    return Counter(words)


def _example_reproduces_signature(
    segment: str,
    signature: Counter[str],
) -> bool:
    text = str(segment or "").strip()
    if not text.casefold().startswith("example:") or not signature:
        return False
    words = Counter(_words(text.split(":", 1)[1] if ":" in text else text))
    return all(words[word] >= count for word, count in signature.items())


def _sanitize_cross_activity_answer_demonstrations(
    student: Mapping[str, Any],
) -> tuple[dict[str, Any], int]:
    """Remove only later examples that reproduce an earlier visible token phrase.

    The check uses learner-visible ordered tokens only. It does not decide the correct
    order or inspect answer/scoring metadata.
    """
    value = deepcopy(dict(student))
    if int(value.get("form_ordinal", 0) or 0) != 1:
        return value, 0

    prior_signatures: list[Counter[str]] = []
    suppressed = 0
    activities: list[dict[str, Any]] = []

    for source in value.get("activities") or []:
        row = dict(source)
        raw = str(row.get("stimulus") or "")
        segments = [part.strip() for part in raw.split("|") if part.strip()]
        kept: list[str] = []
        for segment in segments:
            if any(
                _example_reproduces_signature(segment, signature)
                for signature in prior_signatures
            ):
                suppressed += 1
                continue
            kept.append(segment)
        row["stimulus"] = " | ".join(kept)

        signature = _ordered_token_signature(row)
        if signature:
            prior_signatures.append(signature)
        activities.append(row)

    value["activities"] = activities
    return value, suppressed


def _render_sanitized_with_current_install(student: Mapping[str, Any]) -> str:
    sanitized, _ = _sanitize_cross_activity_answer_demonstrations(student)
    return _ORIGINAL_R1B_RENDER(sanitized)


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


def _stamp_manifest_provenance(manifest_path: Path) -> dict[str, Any]:
    path = Path(manifest_path).resolve(strict=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Form01ActualReadingAngleParityError("MANIFEST_OBJECT_REQUIRED")
    if str(value.get("task_id") or "") != r1b.base.TASK_ID:
        raise Form01ActualReadingAngleParityError("MANIFEST_OWNER_TASK_ID_INVALID")
    value["latest_fullfix_task_id"] = TASK_ID
    value["latest_fullfix_validation_status"] = PASS_STATUS
    value["next_short_step"] = NEXT_SHORT_STEP
    r1b.base._atomic_json(path, value)
    return value


def render_form_html(student: Mapping[str, Any]) -> str:
    previous = _install()
    try:
        return _render_sanitized_with_current_install(student)
    finally:
        _restore(previous)


def materialize_twelve_form_pdfs(**kwargs: Any) -> dict[str, Any]:
    previous = _install()
    previous_render = r1b.render_form_html
    r1b.render_form_html = _render_sanitized_with_current_install
    try:
        value = r1b.materialize_twelve_form_pdfs(**kwargs)
    finally:
        r1b.render_form_html = previous_render
        _restore(previous)

    output_root = Path(kwargs["output_root"]).resolve()
    stamped = _stamp_manifest_provenance(output_root / r1b.base.MANIFEST_NAME)
    value.update(
        {
            "latest_fullfix_task_id": stamped["latest_fullfix_task_id"],
            "latest_fullfix_validation_status": stamped[
                "latest_fullfix_validation_status"
            ],
            "next_short_step": stamped["next_short_step"],
        }
    )
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = r1b.base._build_parser().parse_args(argv)
    previous = _install()
    previous_render = r1b.render_form_html
    r1b.render_form_html = _render_sanitized_with_current_install
    try:
        result = r1b.main(argv)
    finally:
        r1b.render_form_html = previous_render
        _restore(previous)

    if result == 0 and args.record_review_form is None:
        manifest_path = Path(args.output_root).resolve() / r1b.base.MANIFEST_NAME
        stamped = _stamp_manifest_provenance(manifest_path)
        print(f"R1B_R1_STATUS={PASS_STATUS}")
        print(
            "R1B_R1_LATEST_FULLFIX_TASK_ID="
            f"{stamped['latest_fullfix_task_id']}"
        )
        print(f"R1B_R1_NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    elif result == 0:
        print(f"R1B_R1_STATUS={PASS_STATUS}")
        print(f"R1B_R1_NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
