#!/usr/bin/env python3
"""Compatibility entrypoint with governed four-skill learner-stimulus normalization."""
from __future__ import annotations

import contextvars
from copy import deepcopy
from typing import Any, Mapping

from ulga.builders import _a1fs_v1_r3r4_authority_reviewed_production_population_core as _core

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Normalizes existing authority-reviewed four-skill stimuli without authoring content or creating a parallel runtime."

_PRIVATE_KEYS = {
    "acceptance_rule", "accepted_answer", "accepted_answers", "accepted_sequence",
    "accepted_text", "accepted_texts", "answer", "answer_facts", "answer_key",
    "answers", "critical_failure", "diagnostic_route", "expected_evidence",
    "mark_scheme", "model_answer", "model_answers", "private_scoring_contract",
    "rubric", "sample_answer", "sample_answers", "scoring", "scoring_contract",
    "teacher_delivery", "teacher_notes", "text_attested_examples",
}

_COMMON_CONTEXT_KEYS = {"context", "situation", "scenario"}
_FIELD_MAP: dict[str, tuple[tuple[str, set[str]], ...]] = {
    "READING": (
        ("source_text", {"source_text", "passage", "text", "unseen_text", "reading_text", "article", "paragraph", "story"}),
        ("dialogue", {"dialogue", "conversation", "speaker_turns", "turns"}),
        ("image_ref", {"image_ref", "image_url", "image_id", "picture_ref", "picture_url"}),
        ("table", {"table", "data_table"}),
    ),
    "LISTENING": (
        ("audio_ref", {"audio_ref", "audio_url", "audio_id", "listening_audio_ref", "recording_ref", "recording_url", "media_ref"}),
        ("dialogue", {"learner_visible_dialogue", "dialogue_card", "conversation_card"}),
        ("image_ref", {"image_ref", "image_url", "image_id", "picture_ref", "picture_url"}),
    ),
    "SPEAKING": (
        ("source_text", {"role_card", "speaking_card", "prompt_card", "task_card"}),
        ("dialogue", {"dialogue", "conversation", "speaker_turns", "turns"}),
        ("image_ref", {"image_ref", "image_url", "image_id", "picture_ref", "picture_url", "photo_ref"}),
    ),
    "WRITING": (
        ("source_text", {"source_text", "source_message", "received_message", "input_text", "notice", "form_text", "passage"}),
        ("image_ref", {"image_ref", "image_url", "image_id", "picture_ref", "picture_url", "image_sequence_ref"}),
        ("table", {"table", "data_table", "form_fields"}),
    ),
}

_CURRENT_SKILL: contextvars.ContextVar[str] = contextvars.ContextVar(
    "a1fs_r3r4_current_skill", default=""
)
_ORIGINAL_TASK_PROJECTION = _core._task_projection
_ORIGINAL_MATERIALIZE = _core.materialize


def _nonempty_visible(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value) and any(_nonempty_visible(child) for child in value.values())
    if isinstance(value, list):
        return bool(value) and any(_nonempty_visible(child) for child in value)
    return False


def _clean_visible(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        cleaned = {
            str(key): _clean_visible(child)
            for key, child in value.items()
            if str(key).casefold() not in _PRIVATE_KEYS and _nonempty_visible(child)
        }
        return {key: child for key, child in cleaned.items() if _nonempty_visible(child)}
    if isinstance(value, list):
        cleaned = [_clean_visible(child) for child in value if _nonempty_visible(child)]
        return [child for child in cleaned if _nonempty_visible(child)]
    return None


def _safe_walk_named(value: Any, names: set[str]) -> list[Any]:
    result: list[Any] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).casefold()
            if key in _PRIVATE_KEYS:
                continue
            if key in names and _nonempty_visible(child):
                result.append(child)
            result.extend(_safe_walk_named(child, names))
    elif isinstance(value, list):
        for child in value:
            result.extend(_safe_walk_named(child, names))
    return result


def _first_visible(value: Any, names: set[str]) -> Any:
    for candidate in _safe_walk_named(value, names):
        cleaned = _clean_visible(candidate)
        if _nonempty_visible(cleaned):
            return cleaned
    return None


def _learner_context(skill: str, payload: Any) -> dict[str, Any] | None:
    normalized_skill = str(skill or "").upper()
    direct_context = _first_visible(payload, _COMMON_CONTEXT_KEYS)
    if isinstance(direct_context, Mapping) and direct_context:
        return deepcopy(dict(direct_context))
    context: dict[str, Any] = {}
    if isinstance(direct_context, str) and direct_context.strip():
        context["source_text"] = direct_context.strip()
    for target, names in _FIELD_MAP.get(normalized_skill, ()):
        if target in context:
            continue
        candidate = _first_visible(payload, names)
        if _nonempty_visible(candidate):
            context[target] = candidate
    return context or None


def _context(payload: Any) -> dict[str, Any] | None:
    return _learner_context(_CURRENT_SKILL.get(), payload)


def _task_projection(asset: Mapping[str, Any], derived: Mapping[str, Any]):
    token = _CURRENT_SKILL.set(str(asset.get("skill") or ""))
    try:
        return _ORIGINAL_TASK_PROJECTION(asset, derived)
    finally:
        _CURRENT_SKILL.reset(token)


def materialize(*args: Any, **kwargs: Any):
    _core.REPO_ROOT = globals().get("REPO_ROOT", _core.REPO_ROOT)
    return _ORIGINAL_MATERIALIZE(*args, **kwargs)


_core._walk_named = _safe_walk_named
_core._context = _context
_core._task_projection = _task_projection
_core.materialize = materialize

if __name__ == "__main__":
    raise SystemExit(_core.main())
