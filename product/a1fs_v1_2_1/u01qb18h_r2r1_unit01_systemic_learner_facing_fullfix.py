#!/usr/bin/env python3
"""Unit01-only systemic learner-facing FullFix adapter.

This module is a read-only consumer/compatibility/presentation adapter over the
existing U01QB13 selector and the accepted 474-item runtime. It does not author,
replace, or promote QuestionBank content. The selector guard rejects items whose
learner-visible evidence cannot support the requested operation, whose scene
relation is self-contradictory, or whose learner-visible identity would duplicate
another item in the same scene. The presentation hook applies a deterministic
option permutation while scoring continues to compare the selected semantic value
with the canonical response contract.

For actual learner-facing reacceptance, the CLI installs these hooks, reruns the
existing U01QB18F-R4 twelve-form replay against the supplied disposable/production
Unit01 database, and only then materializes the learner-safe PDFs from that fresh
R4 report. This prevents a stale pre-hook R4 JSON from bypassing the FullFix.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18f_r4_full_semantic_language_pedagogical_replay as r4,
)
from product.a1fs_v1_2_1 import (
    u01qb18h_r1b_r1_unit01_form01_actual_reading_angle_parity_fullfix as presentation,
)
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Unit01-only read-only selector/compatibility/presentation adapter over the "
    "approved 474-item runtime; it creates no content, QuestionBank item, scene, "
    "planner, scoring authority, learner state, Unit02-24 content, audio score, "
    "or A2 authority."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U01QB18H-R2R1_"
    "Unit01TwelveFormSystemicLearnerFacingDefectFullFix"
)
PASS_STATUS = (
    "PASS_A1FS_V1_U01QB18H_R2R1_"
    "UNIT01_SYSTEMIC_LEARNER_FACING_FULLFIX"
)
NEXT_SHORT_STEP = "A1FS-V1-U01QB18H-R2R1_ExactHeadCIAndActualTwelveFormReacceptance"
OPTION_PERMUTATION_CONTRACT_VERSION = "A1FS-V1-OPTION-PERMUTATION-V1"
DEFAULT_REPLAY_LEARNER_ID = "U01QB18H_R2R1_ACTUAL_TWELVE_FORM_REACCEPTANCE"
ARTICLE_OPTIONS = ("a", "an", "the")

_WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.I)
_ARTICLE_RE = re.compile(r"\b(?:a|an|the)\s+([a-z]+(?:\s+[a-z]+){0,3})", re.I)
_ANGLE_FAMILIES = {
    "ARTICLE_CONTROL": {"U01-PF04-FIRST-MENTION-CONTEXT", "U01-PF08-TRANSFER-FIRST-MENTION"},
    "FIRST_MENTION_CONTEXT": {"U01-PF04-FIRST-MENTION-CONTEXT", "U01-PF08-TRANSFER-FIRST-MENTION"},
    "TRANSFER_DECISION": {"U01-PF04-FIRST-MENTION-CONTEXT", "U01-PF08-TRANSFER-FIRST-MENTION"},
    "KNOWN_REFERENCE_CONTEXT": {"U01-PF05-KNOWN-REFERENCE-CONTEXT", "U01-PF09-TRANSFER-KNOWN-REFERENCE"},
    "ERROR_CHECK": {"U01-PF06-ERROR-DISCRIMINATION", "U01-PF13-ERROR-CHECK"},
    "REFERENCE_EVIDENCE": {"U01-PF16-REFERENCE-EVIDENCE"},
}


class SystemicLearnerFacingFullFixError(ValueError):
    """Fail-closed Unit01 systemic learner-facing defect."""


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def visible_signature(*, item: Mapping[str, Any]) -> str:
    """Identity of the learner-visible stimulus, prompt, and option set."""
    visible = {
        "stimulus": _normalized(item.get("stimulus")),
        "prompt": _normalized(item.get("prompt")),
        "options": sorted(_normalized(value) for value in item.get("options") or []),
    }
    raw = json.dumps(visible, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _words(value: Any) -> list[str]:
    return [match.group(0).casefold() for match in _WORD_RE.finditer(str(value or ""))]


def _noun(item: Mapping[str, Any]) -> str:
    slots = item.get("lexical_slots") or {}
    for key in ("noun", "target_noun", "item", "target"):
        value = slots.get(key) if isinstance(slots, Mapping) else None
        value = value or item.get(key)
        if str(value or "").strip():
            return _words(value)[-1] if _words(value) else ""
    return ""


def has_prior_reference(item: Mapping[str, Any]) -> bool:
    """Return whether a learner can see a prior indefinite mention."""
    stimulus = str(item.get("stimulus") or "")
    target = _noun(item)
    if not target:
        return False
    blank_at = min(
        [position for position in (stimulus.find("___"), stimulus.casefold().find("blank")) if position >= 0]
        or [len(stimulus)]
    )
    before = stimulus[:blank_at]
    return re.search(rf"\b(?:a|an)\s+(?:[a-z]+\s+)*{re.escape(target)}\b", before, re.I) is not None


def has_first_mention_evidence(item: Mapping[str, Any]) -> bool:
    stimulus = str(item.get("stimulus") or "")
    prompt = str(item.get("prompt") or "")
    if re.search(r"\b(first\s+mention|introduc(?:e|ed|ing))\b", f"{prompt} {stimulus}", re.I):
        return True
    target = _noun(item)
    if not target:
        return False
    blank = stimulus.find("___")
    if blank < 0:
        return False
    before = stimulus[:blank]
    # “There is ___ noun” is an explicit first-introduction frame.
    return re.search(r"\bthere\s+is\s*$", before, re.I) is not None


def semantic_compatible(item: Mapping[str, Any], *, scene_ref_id: str = "", situation_family: str = "") -> bool:
    """Reject the tautological item/container relation exposed by PDF review."""
    noun = _noun(item)
    if not noun:
        return False
    slots = item.get("lexical_slots") or {}
    container = ""
    for key in ("place", "container", "location", "scene_place"):
        value = slots.get(key) if isinstance(slots, Mapping) else None
        value = value or item.get(key)
        if str(value or "").strip():
            container = _words(value)[-1] if _words(value) else ""
            break
    stimulus = str(item.get("stimulus") or "")
    same_noun_in_container = re.search(
        rf"(?:___\s+|\b(?:a|an|the)\s+){re.escape(noun)}\b\s+in\s+the\s+{re.escape(noun)}\b",
        stimulus,
        re.I,
    )
    if same_noun_in_container or container == noun:
        return False
    return True


def candidate_guard(
    item: Mapping[str, Any],
    *,
    task_angle: str,
    scene_ref_id: str = "",
    situation_family: str = "",
) -> bool:
    """Fail closed when learner-visible semantics cannot support the activity."""
    if not semantic_compatible(item, scene_ref_id=scene_ref_id, situation_family=situation_family):
        return False
    family = str(item.get("pattern_family_id") or "")
    allowed_families = _ANGLE_FAMILIES.get(str(task_angle or ""))
    if allowed_families and family and family not in allowed_families:
        return False
    prompt = _normalized(item.get("prompt"))
    stimulus = str(item.get("stimulus") or "")
    if "known_reference" in str(task_angle).casefold() or family.endswith("KNOWN-REFERENCE-CONTEXT"):
        return "___" in stimulus and has_prior_reference(item)
    if str(task_angle) in {"ARTICLE_CONTROL", "FIRST_MENTION_CONTEXT", "TRANSFER_DECISION"}:
        return "___" in stimulus and (has_prior_reference(item) or has_first_mention_evidence(item))
    if str(task_angle) == "ERROR_CHECK":
        return "error" in prompt or "incorrect" in prompt or len(item.get("options") or []) >= 2
    return True


class _CandidateGuard:
    def __call__(self, item: Mapping[str, Any], **kwargs: Any) -> bool:
        return candidate_guard(item, **kwargs)

    @staticmethod
    def visible_signature(*, item: Mapping[str, Any]) -> str:
        return visible_signature(item=item)


def deterministic_option_permutation(
    options: Sequence[Any],
    *,
    canonical_answer: Any,
    form_id: str,
    question_identity: str,
    contract_version: str = OPTION_PERMUTATION_CONTRACT_VERSION,
) -> list[str]:
    """Return a stable display order while preserving semantic answer values.

    The per-form rotation is deliberately derived only from ``form_id`` and the
    contract version. Question/activity identity determines the slot within that
    fixed form rotation. Therefore eight three-option activities always yield a
    deterministic 3/3/2 target-position distribution for every Form instead of
    allowing a per-question digest to accidentally skew one Form.
    """
    values = [str(value) for value in options]
    if len(values) < 2:
        return values
    # Ordered-token banks use ``options`` as a visible token bank but their
    # canonical answer is a sequence. They are not select_one choices and
    # must retain their existing token affordance.
    if isinstance(canonical_answer, (list, tuple)):
        return values
    answer = str(canonical_answer or "")
    if answer not in values:
        raise SystemicLearnerFacingFullFixError(
            f"CANONICAL_OPTION_NOT_IN_DISPLAY_OPTIONS:{answer}:{values}"
        )
    fallback_digest = hashlib.sha256(
        f"{form_id}|{question_identity}|{contract_version}".encode("utf-8")
    ).digest()
    form_digest = hashlib.sha256(
        f"{form_id}|{contract_version}".encode("utf-8")
    ).digest()
    activity_match = re.search(r"S(\d+)-A(\d+)$", str(question_identity), re.I)
    question_match = re.search(r"(?:Q|A)(\d+)$", str(question_identity), re.I)
    if activity_match:
        slot = (int(activity_match.group(1)) - 1) * 2 + int(activity_match.group(2)) - 1
        form_offset = form_digest[0] % len(values)
        target = (slot % len(values) + form_offset) % len(values)
    elif question_match:
        question_number = int(question_match.group(1))
        form_offset = form_digest[0] % len(values)
        target = ((question_number - 1) % len(values) + form_offset) % len(values)
    else:
        target = fallback_digest[0] % len(values)
    ordered = [value for value in values if value != answer]
    ordered.insert(target, answer)
    return ordered


def score_semantic_option(*, selected_value: Any, canonical_answer: Any) -> bool:
    """Scoring contract: compare semantic value, never display position."""
    return _normalized(selected_value) == _normalized(canonical_answer)


def install() -> None:
    u13.install_systemic_candidate_guard(_CandidateGuard())
    u13.install_systemic_option_permuter(deterministic_option_permutation)


def uninstall() -> None:
    u13.install_systemic_candidate_guard(None)
    u13.install_systemic_option_permuter(None)


def _review_fields(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(source.get(key))
        for key in (
            "human_visual_review",
            "human_pedagogical_review",
            "human_review_defect_codes",
            "human_review_evidence_pdf_sha256",
            "human_reviewed_at",
        )
        if key in source
    }


def materialize_twelve_form_pdfs(
    *,
    database: Path | None = None,
    replay_learner_id: str = DEFAULT_REPLAY_LEARNER_ID,
    **kwargs: Any,
) -> dict[str, Any]:
    """Rerun actual R4 under the hooks, then materialize through the existing renderer.

    ``database`` is optional for focused unit tests and compatibility callers. The
    operator CLI requires it, because actual twelve-form reacceptance is not allowed
    to rely on a stale R4 report that may predate these hooks.
    """
    r4_report_path = Path(
        kwargs.get("r4_report_path") or presentation.r1b.base.DEFAULT_R4_REPORT
    )
    replay: Mapping[str, Any] | None = None
    install()
    try:
        if database is not None:
            replay = r4.materialize_full_replay(
                database=Path(database),
                output=r4_report_path,
                learner_id=str(replay_learner_id),
            )
            if (
                str(replay.get("validation_status") or "") != r4.PASS_STATUS
                or int(replay.get("error_count") or 0) != 0
                or len(replay.get("forms") or []) != 12
            ):
                raise SystemicLearnerFacingFullFixError(
                    "ACTUAL_R4_REPLAY_NOT_ACCEPTED:"
                    f"{replay.get('validation_status')}:"
                    f"{replay.get('error_count')}:"
                    f"{len(replay.get('forms') or [])}"
                )
        value = presentation.materialize_twelve_form_pdfs(**kwargs)
    finally:
        uninstall()
    value["latest_fullfix_task_id"] = TASK_ID
    value["latest_fullfix_validation_status"] = PASS_STATUS
    value["next_short_step"] = NEXT_SHORT_STEP
    value["actual_r4_replay_executed"] = replay is not None
    if replay is not None:
        value["actual_r4_replay_task_id"] = str(replay.get("task_id") or "")
        value["actual_r4_replay_validation_status"] = str(
            replay.get("validation_status") or ""
        )
        value["actual_r4_replay_form_count"] = len(replay.get("forms") or [])
        value["actual_r4_replay_activity_count"] = sum(
            int((form.get("student_form") or {}).get("learner_visible_activity_count") or 0)
            for form in replay.get("forms") or []
            if isinstance(form, Mapping)
        )
    return value


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--r4-report", type=Path, default=presentation.r1b.base.DEFAULT_R4_REPORT)
    parser.add_argument("--output-root", type=Path, default=presentation.r1b.base.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--chromium-path", type=Path)
    parser.add_argument("--learner-id", default=DEFAULT_REPLAY_LEARNER_ID)
    args = parser.parse_args(argv)
    try:
        value = materialize_twelve_form_pdfs(
            database=args.database,
            replay_learner_id=str(args.learner_id),
            r4_report_path=args.r4_report,
            output_root=args.output_root,
            chromium_path=args.chromium_path,
        )
    except (Exception,) as exc:
        print(f"STATUS=FAIL_{TASK_ID}")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={PASS_STATUS}")
    print(f"R4_REPLAY_EXECUTED={value['actual_r4_replay_executed']}")
    print(f"R4_REPLAY_STATUS={value.get('actual_r4_replay_validation_status')}")
    print(f"R4_REPLAY_FORMS={value.get('actual_r4_replay_form_count')}")
    print(f"R4_REPLAY_ACTIVITIES={value.get('actual_r4_replay_activity_count')}")
    print(f"FORMS={value['form_count']}")
    print(f"PDF_FILES={value['materialized_pdf_count']}")
    print(f"MACHINE_PREFLIGHT_PASS={value['machine_preflight_pass_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
