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
_PRIVATE_RUBRIC_KEYS = {
    "acceptance_rule",
    "answer_facts",
    "critical_failure",
    "diagnostic_route",
    "expected_evidence",
    "mark_scheme",
    "model_answer",
    "model_answers",
    "text_attested_examples",
}
_COMMON_CONTEXT_KEYS = {"context", "situation", "scenario"}
_PROMPT_KEYS = {
    "body_title",
    "instruction",
    "instructions",
    "launch_cue",
    "learner_prompt",
    "prompt",
    "question",
    "question_text",
    "student_prompt",
    "task_prompt",
    "task_title",
    "title",
}
_M6_PROMPT_KEYS = {"instruction", "launch_cue", "prompt", "question"}
_FIELD_MAP: dict[str, tuple[tuple[str, set[str]], ...]] = {
    "READING": (
        ("source_text", {"source_text", "passage", "text", "unseen_text", "reading_text", "article", "paragraph", "story"}),
        ("dialogue", {"dialogue", "conversation", "speaker_turns", "turns"}),
        ("image_ref", {"image_ref", "image_url", "image_id", "picture_ref", "picture_url"}),
        ("table", {"table", "data_table"}),
    ),
    "LISTENING": (
        (
            "audio_ref",
            {
                "audio",
                "audio_asset_ref",
                "audio_file",
                "audio_id",
                "audio_path",
                "audio_ref",
                "audio_url",
                "listening_audio_ref",
                "media_ref",
                "recording_ref",
                "recording_url",
                "source_audio_ref",
            },
        ),
        ("dialogue", {"learner_visible_dialogue", "dialogue_card", "conversation_card"}),
        ("image_ref", {"image_ref", "image_url", "image_id", "picture_ref", "picture_url"}),
    ),
    "SPEAKING": (
        ("source_text", {"role_card", "speaking_card", "prompt_card", "task_card", "body_text"}),
        ("dialogue", {"dialogue", "conversation", "speaker_turns", "turns"}),
        ("image_ref", {"image_ref", "image_url", "image_id", "picture_ref", "picture_url", "photo_ref"}),
    ),
    "WRITING": (
        ("source_text", {"source_text", "source_message", "received_message", "input_text", "notice", "form_text", "passage", "body_text"}),
        ("image_ref", {"image_ref", "image_url", "image_id", "picture_ref", "picture_url", "image_sequence_ref"}),
        ("table", {"table", "data_table", "form_fields"}),
    ),
}

_CONTEXT_SOURCE_ROLES: dict[str, tuple[str, ...]] = {
    "LISTENING": ("AUD", "CTX"),
    "SPEAKING": ("CTX",),
    "READING": ("TXT", "CTX"),
    "WRITING": ("CTX",),
}
_PRIVATE_EVIDENCE_ROLE_PRIORITY = ("EVD", "MOD", "ERR", "GDT", "NTC", "CHK", "PRD", "XFR")
_FORMAL_ROLES = frozenset(_core.m6.CAPTURE_ROLES)

_CURRENT_SKILL: contextvars.ContextVar[str] = contextvars.ContextVar(
    "a1fs_r3r4_current_skill", default=""
)
_ORIGINAL_TASK_PROJECTION = _core._task_projection
_ORIGINAL_MATERIALIZE = _core.materialize
_ORIGINAL_LOAD_SOURCES = _core._load_sources


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


def _walk_private_named(value: Any, names: set[str]) -> list[tuple[str, Any]]:
    result: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).casefold()
            if key in names and _nonempty_visible(child):
                result.append((key, deepcopy(child)))
            result.extend(_walk_private_named(child, names))
    elif isinstance(value, list):
        for child in value:
            result.extend(_walk_private_named(child, names))
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


def _prompt(payload: Any) -> str | None:
    value = _first_visible(payload, _PROMPT_KEYS)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _private_rubric(payload: Any) -> dict[str, Any] | None:
    criteria: dict[str, Any] = {}
    for key, value in _walk_private_named(payload, _PRIVATE_RUBRIC_KEYS):
        criteria.setdefault(key, value)
    if not criteria:
        return None
    return {
        "authority_source": "EXISTING_ASSET_BODY_PRIVATE_REVIEW_EVIDENCE",
        "criteria": criteria,
    }


def _merge_context(target: dict[str, Any], source: Mapping[str, Any]) -> None:
    for key in ("audio_ref", "source_text", "dialogue", "image_ref", "table"):
        value = source.get(key)
        if key not in target and _nonempty_visible(value):
            target[key] = deepcopy(value)


def _lesson_shared_context(skill: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    shared: dict[str, Any] = {}
    for role in _CONTEXT_SOURCE_ROLES.get(skill, ()):
        for row in rows:
            if str(row.get("role") or "") != role:
                continue
            context = _learner_context(skill, row.get("payload"))
            if context:
                _merge_context(shared, context)
    return shared or None


def _lesson_private_rubric(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    criteria: dict[str, Any] = {}
    by_role: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_role.setdefault(str(row.get("role") or ""), []).append(row)
    for role in _PRIVATE_EVIDENCE_ROLE_PRIORITY:
        for row in by_role.get(role, []):
            rubric = _private_rubric(row.get("payload"))
            if rubric:
                for key, value in rubric["criteria"].items():
                    criteria.setdefault(key, value)
            if role == "MOD":
                model_text = _first_visible(row.get("payload"), {"body_text", "text", "model_text"})
                if _nonempty_visible(model_text):
                    criteria.setdefault("model_reference", model_text)
    if not criteria:
        return None
    return {
        "authority_source": "EXISTING_LESSON_PRIVATE_REVIEW_EVIDENCE",
        "criteria": criteria,
    }


def _projection_consumer(consumer: Mapping[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(dict(consumer))
    rows = normalized.get("asset_records")
    if not isinstance(rows, list):
        return normalized

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        grouped.setdefault(
            (str(row.get("lesson_id") or ""), str(row.get("skill") or "")),
            [],
        ).append(row)

    for (_lesson_id, skill), lesson_rows in grouped.items():
        shared_context = _lesson_shared_context(skill, lesson_rows)
        shared_rubric = _lesson_private_rubric(lesson_rows)

        for asset in lesson_rows:
            role = str(asset.get("role") or "")
            if role not in _FORMAL_ROLES:
                continue
            payload = asset.get("payload")
            if not isinstance(payload, Mapping):
                continue
            mutable_payload = deepcopy(dict(payload))

            existing_m6_prompt = _first_visible(mutable_payload, _M6_PROMPT_KEYS)
            if not (isinstance(existing_m6_prompt, str) and existing_m6_prompt.strip()):
                resolved_prompt = _prompt(mutable_payload)
                if resolved_prompt:
                    mutable_payload["prompt"] = resolved_prompt

            own_context = _learner_context(skill, mutable_payload)
            if shared_context and not own_context:
                mutable_payload["context"] = deepcopy(shared_context)

            probe = dict(asset)
            probe["payload"] = mutable_payload
            derived = _core.m6.derive_contract(probe)
            needs_rubric = (
                derived.get("scoring_mode") == "NONE"
                or (
                    derived.get("scoring_mode") == "FEATURE_RUBRIC"
                    and not derived.get("rubric")
                )
            )
            if needs_rubric:
                rubric = _private_rubric(mutable_payload) or shared_rubric
                if rubric:
                    existing = mutable_payload.get("private_scoring_contract")
                    contract = deepcopy(dict(existing)) if isinstance(existing, Mapping) else {}
                    contract["scoring_mode"] = "FEATURE_RUBRIC"
                    contract["rubric"] = deepcopy(rubric)
                    mutable_payload["private_scoring_contract"] = contract

            asset["payload"] = mutable_payload

    return normalized


def _load_sources(ontology_path, graph_path, consumer_path):
    ontology, graph, consumer = _ORIGINAL_LOAD_SOURCES(
        ontology_path,
        graph_path,
        consumer_path,
    )
    return ontology, graph, _projection_consumer(consumer)


def materialize(*args: Any, **kwargs: Any):
    _core.REPO_ROOT = globals().get("REPO_ROOT", _core.REPO_ROOT)
    return _ORIGINAL_MATERIALIZE(*args, **kwargs)


_core._walk_named = _safe_walk_named
_core._context = _context
_core._task_projection = _task_projection
_core._load_sources = _load_sources
_core.materialize = materialize

if __name__ == "__main__":
    raise SystemExit(_core.main())
