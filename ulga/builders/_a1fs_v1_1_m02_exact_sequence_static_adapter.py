#!/usr/bin/env python3
"""Patch the learner UI to serialize controlled word-order responses as token lists."""
from __future__ import annotations

from pathlib import Path

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Adapts learner-entered text into the existing EXACT_SEQUENCE transport shape only for "
    "controlled-sequence Writing assets. It creates no content, answer, scoring rule, state, "
    "mastery, audio, A2, external route, or parallel authority."
)

SOURCE_RESPONSE_FOR = (
    "function responseFor(card,asset){const options=asset.learner_payload.options||[];"
    "if(options.length){const checked=card.querySelector('input[type=radio]:checked');"
    "if(!checked)throw new Error('請先選擇答案');return checked.value}"
    "const area=card.querySelector('textarea');if(!area||!area.value.trim())"
    "throw new Error('請先輸入答案');return area.value}"
)

SERIALIZER = (
    "const serializeTextResponse=(asset,value)=>{const trimmed=value.trim();"
    "if(asset.learner_payload.writing_stage==='CONTROLLED_SEQUENCE')"
    "return trimmed.split(/\\s+/);return value};"
)

TARGET_RESPONSE_FOR = (
    SERIALIZER
    + "function responseFor(card,asset){const options=asset.learner_payload.options||[];"
    "if(options.length){const checked=card.querySelector('input[type=radio]:checked');"
    "if(!checked)throw new Error('請先選擇答案');return checked.value}"
    "const area=card.querySelector('textarea');if(!area||!area.value.trim())"
    "throw new Error('請先輸入答案');return serializeTextResponse(asset,area.value)}"
)


class ExactSequenceStaticAdapterError(ValueError):
    """Fail-closed static adapter error."""


def validate_app_js(path: Path) -> dict[str, object]:
    path = Path(path)
    if not path.is_file():
        raise ExactSequenceStaticAdapterError(f"app_js_missing:{path}")
    text = path.read_text(encoding="utf-8")
    if TARGET_RESPONSE_FOR not in text:
        raise ExactSequenceStaticAdapterError("exact_sequence_serializer_missing")
    if SOURCE_RESPONSE_FOR in text:
        raise ExactSequenceStaticAdapterError("legacy_text_only_response_serializer_still_present")
    if "accepted_sequence" in text or "answer_key" in text:
        raise ExactSequenceStaticAdapterError("private_answer_contract_leaked_to_static")
    return {
        "validation_status": "PASS_EXACT_SEQUENCE_STATIC_ADAPTER",
        "controlled_sequence_serializes_to_token_list": True,
        "ordinary_text_remains_text": True,
        "private_answer_contract_exposed": False,
    }


def patch_app_js(path: Path) -> dict[str, object]:
    path = Path(path)
    if not path.is_file():
        raise ExactSequenceStaticAdapterError(f"app_js_missing:{path}")
    text = path.read_text(encoding="utf-8")
    if TARGET_RESPONSE_FOR in text:
        result = validate_app_js(path)
        return {**result, "patched": False, "already_patched": True}
    count = text.count(SOURCE_RESPONSE_FOR)
    if count != 1:
        raise ExactSequenceStaticAdapterError(f"legacy_response_serializer_match_count_invalid:{count}")
    path.write_text(text.replace(SOURCE_RESPONSE_FOR, TARGET_RESPONSE_FOR, 1), encoding="utf-8")
    result = validate_app_js(path)
    return {**result, "patched": True, "already_patched": False}
