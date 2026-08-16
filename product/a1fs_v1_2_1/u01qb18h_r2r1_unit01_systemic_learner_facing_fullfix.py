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
NEXT_SHORT_STEP = "A1FS-V1-U01QB18H-R2R1_ActualTwelveFormPdfHumanVisualPedagogicalReacceptance"
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


_BASE_CLEAN_STIMULUS = presentation.r1b.base._clean_stimulus
_R1B_CLEAN_STIMULUS = presentation.r1b._clean_stimulus_r1b


def _source_context(activity: Mapping[str, Any]) -> str:
    """Extract only natural discourse already present in the source stimulus."""
    raw = str(activity.get("stimulus") or "").strip()
    target = presentation.r1b.base._target_phrase(raw)
    if not raw or not target:
        return ""
    marker = re.search(r"target\s+phrase\s*:", raw, flags=re.I)
    before_target = raw[: marker.start()] if marker else raw
    parts: list[str] = []
    for segment in before_target.split("|"):
        value = segment.strip()
        if not value:
            continue
        labeled = re.findall(
            r"\b(?:guide|learner)\s*:\s*(.*?)(?=\s+(?:guide|learner)\s*:|$)",
            value,
            flags=re.I,
        )
        if labeled:
            parts.extend(part.strip() for part in labeled if part.strip())
            continue
        if re.match(
            r"^(?:scene|scene\s+words|relationship|action|event|task\s+focus|guide|target\s+phrase|example|use|noun|word|words)\s*:",
            value,
            flags=re.I,
        ):
            continue
        if value.casefold().startswith("learner:"):
            value = value.split(":", 1)[1].strip()
        if value:
            parts.append(value)
    context = " ".join(parts).strip()
    target_words = re.escape(target)
    if not re.search(
        rf"\b(?:a|an)\s+(?:[a-z]+\s+)*{target_words}\b"
        rf"|\bthere\s+is\s+(?:a|an|the)?\s*(?:[a-z]+\s+)*{target_words}\b",
        context,
        flags=re.I,
    ):
        return ""
    return context


def _preserve_source_context(
    activity: Mapping[str, Any],
    cleaned: str,
) -> str:
    context = _source_context(activity)
    if not context or _normalized(context) in _normalized(cleaned):
        return cleaned
    return " | ".join(value for value in (context, cleaned) if value).strip()


def _projected_stimulus(activity: Mapping[str, Any]) -> str:
    return _preserve_source_context(activity, _BASE_CLEAN_STIMULUS(activity))


def final_visible_signature(
    *,
    item: Mapping[str, Any],
    stimulus: str | None = None,
) -> str:
    """Return final learner-visible identity; option order is not identity."""
    visible = {
        "stimulus": _normalized(
            _projected_stimulus(item) if stimulus is None else stimulus
        ),
        "prompt": _normalized(item.get("prompt")),
        "response_mode": _normalized(
            item.get("response_mode")
            or ("select_one" if item.get("options") else "short_text")
        ),
        "options": sorted(_normalized(value) for value in item.get("options") or []),
        "operation_identity": _normalized(
            item.get("operation_identity") or item.get("prompt")
        ),
    }
    raw = json.dumps(visible, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def visible_signature(*, item: Mapping[str, Any]) -> str:
    """Compatibility name for the final learner-visible identity."""
    return final_visible_signature(item=item)


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


def _item_context_id(item: Mapping[str, Any]) -> str:
    slots = item.get("lexical_slots") or {}
    return str(
        item.get("context_id")
        or (slots.get("context_id") if isinstance(slots, Mapping) else "")
        or ""
    )


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
    """Reject tautological item/container relations in the actual item schema."""
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
    if not container:
        place_match = re.search(
            r"\bplace\s*:\s*(?:in|on|at)\s+(?:the|a|an)?\s*([a-z]+)",
            stimulus,
            flags=re.I,
        )
        if place_match:
            container = place_match.group(1).casefold()
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
    """Compatibility helper for one item; actual production uses the form allocator."""
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
    if len(values) == 3:
        identities = [f"Q{index:02d}" for index in range(1, 9)]
        positions = _allocate_form_positions(
            form_id=form_id,
            activities=[
                {"activity_id": identity, "options": values, "canonical_answer": answer}
                for identity in identities
            ],
            contract_version=contract_version,
        )
        target = positions[identities[_identity_slot(question_identity)]]
    else:
        digest = hashlib.sha256(
            f"{form_id}|{question_identity}|{contract_version}".encode("utf-8")
        ).digest()
        target = digest[0] % len(values)
    return _display_order(
        values,
        answer=answer,
        target=target,
        identity=str(question_identity),
        contract_version=contract_version,
    )


def _identity_slot(identity: Any) -> int:
    activity_match = re.search(r"S(\d+)-A(\d+)$", str(identity), re.I)
    if activity_match:
        return (int(activity_match.group(1)) - 1) * 2 + int(activity_match.group(2)) - 1
    question_match = re.search(r"(?:Q|A)(\d+)$", str(identity), re.I)
    if question_match:
        return max(0, int(question_match.group(1)) - 1)
    return 0


def _form_low_position(form_id: str, contract_version: str) -> int:
    match = re.search(r"FORM-(\d+)", str(form_id), re.I)
    if match:
        return (int(match.group(1)) - 1) % 3
    digest = hashlib.sha256(f"{form_id}|{contract_version}".encode("utf-8")).digest()
    return digest[0] % 3


def _allocate_form_positions(
    *,
    form_id: str,
    activities: Sequence[Mapping[str, Any]],
    contract_version: str = OPTION_PERMUTATION_CONTRACT_VERSION,
) -> dict[str, int]:
    rows = sorted(activities, key=lambda row: str(row.get("activity_id") or ""))
    if len(rows) != 8:
        raise SystemicLearnerFacingFullFixError(
            f"FORM_OPTION_POSITION_ASSIGNMENT_IMPOSSIBLE:{form_id}:ACTIVITY_COUNT={len(rows)}"
        )
    legal: list[tuple[str, tuple[int, ...]]] = []
    for row in rows:
        options = list(row.get("options") or [])
        answer = _normalized(row.get("canonical_answer"))
        if len(options) not in (2, 3) or not answer:
            raise SystemicLearnerFacingFullFixError(
                f"FORM_OPTION_POSITION_ASSIGNMENT_IMPOSSIBLE:{form_id}:"
                f"{row.get('activity_id')}:OPTIONS={len(options)}"
            )
        if not any(_normalized(value) == answer for value in options):
            raise SystemicLearnerFacingFullFixError(
                f"FORM_OPTION_POSITION_ASSIGNMENT_IMPOSSIBLE:{form_id}:"
                f"{row.get('activity_id')}:ANSWER_NOT_IN_OPTIONS"
            )
        legal.append((str(row.get("activity_id") or ""), tuple(range(len(options)))))

    low_candidates = sorted(
        range(3),
        key=lambda position: hashlib.sha256(
            f"{form_id}|{contract_version}|LOW|{position}".encode("utf-8")
        ).hexdigest(),
    )
    sequence = None
    target_counts: dict[int, int] = {}
    for low in low_candidates:
        target_counts = {position: 3 for position in range(3)}
        target_counts[low] = 2
        memo: dict[tuple[int, tuple[int, int, int], int, int], tuple[int, ...] | None] = {}

        def search(index: int, remaining: tuple[int, int, int], previous: int, run: int):
            key = (index, remaining, previous, run)
            if key in memo:
                return memo[key]
            if index == len(legal):
                result = () if not any(remaining) else None
                memo[key] = result
                return result
            identity, allowed = legal[index]
            candidates = [position for position in allowed if remaining[position] > 0]
            candidates.sort(
                key=lambda position: (
                    position == previous and run >= 2,
                    hashlib.sha256(
                        f"{form_id}|{identity}|{position}|{contract_version}".encode("utf-8")
                    ).hexdigest(),
                    position,
                )
            )
            for position in candidates:
                next_run = run + 1 if position == previous else 1
                if next_run > 2:
                    continue
                next_remaining = list(remaining)
                next_remaining[position] -= 1
                suffix = search(index + 1, tuple(next_remaining), position, next_run)
                if suffix is not None:
                    result = (position,) + suffix
                    memo[key] = result
                    return result
            memo[key] = None
            return None

        sequence = search(0, tuple(target_counts[position] for position in range(3)), -1, 0)
        if sequence is not None:
            break
    if sequence is None:
        legal_summary = ",".join(
            f"{identity}:{list(allowed)}" for identity, allowed in legal
        )
        raise SystemicLearnerFacingFullFixError(
            f"FORM_OPTION_POSITION_ASSIGNMENT_IMPOSSIBLE:{form_id}:"
            f"TARGET={target_counts}:LEGAL={legal_summary}"
        )
    return {identity: int(position) for (identity, _), position in zip(legal, sequence)}


def _display_order(
    values: Sequence[Any],
    *,
    answer: str,
    target: int,
    identity: str,
    contract_version: str,
) -> list[str]:
    normalized_answer = _normalized(answer)
    answer_values = [str(value) for value in values]
    distractors = [
        value for value in answer_values if _normalized(value) != normalized_answer
    ]
    digest = hashlib.sha256(
        f"{identity}|{contract_version}|DISTRACTORS".encode("utf-8")
    ).digest()
    if digest[0] % 2:
        distractors.reverse()
    ordered = list(distractors)
    ordered.insert(max(0, min(int(target), len(ordered))), str(answer))
    return ordered


def allocate_form_option_orders(
    *,
    form_id: str,
    activities: Sequence[Mapping[str, Any]],
    contract_version: str = OPTION_PERMUTATION_CONTRACT_VERSION,
) -> dict[str, list[str]]:
    """Assign all selected Reading display orders in one constrained pass."""
    positions = _allocate_form_positions(
        form_id=form_id,
        activities=activities,
        contract_version=contract_version,
    )
    result: dict[str, list[str]] = {}
    for row in activities:
        identity = str(row.get("activity_id") or "")
        values = [str(value) for value in row.get("options") or []]
        result[identity] = _display_order(
            values,
            answer=str(row.get("canonical_answer") or ""),
            target=positions[identity],
            identity=identity,
            contract_version=contract_version,
        )
    return result


def score_semantic_option(*, selected_value: Any, canonical_answer: Any) -> bool:
    """Scoring contract: compare semantic value, never display position."""
    return _normalized(selected_value) == _normalized(canonical_answer)


def install() -> None:
    u13.install_systemic_candidate_guard(_CandidateGuard())
    u13.install_systemic_option_permuter(deterministic_option_permutation)
    u13.install_systemic_form_option_allocator(allocate_form_option_orders)


def uninstall() -> None:
    u13.install_systemic_candidate_guard(None)
    u13.install_systemic_option_permuter(None)
    u13.install_systemic_form_option_allocator(None)


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


def validate_final_learner_projection(student: Mapping[str, Any]) -> dict[str, int]:
    """Validate context preservation and duplicate identity after projection."""
    context_failures = 0
    duplicate_failures = 0
    seen: dict[tuple[str, str, str], str] = {}
    for activity in student.get("activities") or []:
        if not isinstance(activity, Mapping):
            continue
        if str(activity.get("skill") or "").upper() == "READING":
            source = _source_context(activity)
            final_stimulus = _projected_stimulus(activity)
            if source and _normalized(source) not in _normalized(final_stimulus):
                context_failures += 1
        else:
            final_stimulus = _projected_stimulus(activity)
        key = (
            str(activity.get("scene_ref_id") or ""),
            str(activity.get("skill") or "").upper(),
            final_visible_signature(item=activity, stimulus=final_stimulus),
        )
        if key in seen:
            duplicate_failures += 1
        else:
            seen[key] = str(activity.get("question_number") or "")
    if context_failures or duplicate_failures:
        raise SystemicLearnerFacingFullFixError(
            f"FINAL_LEARNER_PROJECTION_INVALID:CONTEXT={context_failures}:"
            f"DUPLICATES={duplicate_failures}"
        )
    return {
        "context_stripping_failures": context_failures,
        "final_visible_duplicates": duplicate_failures,
    }


def _install_projection_hooks() -> tuple[Any, Any, Any]:
    base = presentation.r1b.base
    r1b = presentation.r1b
    previous_base = base._clean_stimulus
    previous_r1b = r1b._clean_stimulus_r1b

    def clean(activity: Mapping[str, Any]) -> str:
        ordinal = int(activity.get("form_ordinal", 0) or 0)
        original = previous_r1b(activity) if ordinal == 1 else previous_base(activity)
        return _preserve_source_context(activity, original)

    base._clean_stimulus = clean
    r1b._clean_stimulus_r1b = clean
    return base, previous_base, previous_r1b


def _restore_projection_hooks(previous: tuple[Any, Any, Any]) -> None:
    base, previous_base, previous_r1b = previous
    base._clean_stimulus = previous_base
    presentation.r1b._clean_stimulus_r1b = previous_r1b


def _stamp_manifest_provenance(output_root: Path) -> dict[str, Any] | None:
    path = Path(output_root).resolve() / presentation.r1b.base.MANIFEST_NAME
    if not path.is_file():
        return None
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise SystemicLearnerFacingFullFixError("MANIFEST_OBJECT_REQUIRED")
    manifest.update(
        {
            "latest_fullfix_task_id": (
                "A1FS-V1-U01QB18H-R2R1_"
                "Unit01TwelveFormSystemicLearnerFacingDefectFullFix"
            ),
            "latest_fullfix_validation_status": PASS_STATUS,
            "next_short_step": NEXT_SHORT_STEP,
        }
    )
    presentation.r1b.base._atomic_json(path, manifest)
    return manifest


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
    projection_hooks = _install_projection_hooks()
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
            for form in replay.get("forms") or []:
                student = form.get("student_form") or {}
                if student.get("activities"):
                    validate_final_learner_projection(student)
        value = presentation.materialize_twelve_form_pdfs(**kwargs)
    finally:
        _restore_projection_hooks(projection_hooks)
        uninstall()
    stamped = _stamp_manifest_provenance(Path(kwargs["output_root"]))
    value["latest_fullfix_task_id"] = (
        str(stamped.get("latest_fullfix_task_id")) if stamped else TASK_ID
    )
    value["latest_fullfix_validation_status"] = (
        str(stamped.get("latest_fullfix_validation_status")) if stamped else PASS_STATUS
    )
    value["next_short_step"] = str(stamped.get("next_short_step")) if stamped else NEXT_SHORT_STEP
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
