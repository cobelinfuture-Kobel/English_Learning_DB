from __future__ import annotations

from typing import Any

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Shared learner-interaction taxonomy only. This module classifies already-authored task "
    "response actions; it does not author prompts, answers, distractors, passages, or tasks."
)

TASK_ID = "A1FS-V1-CoreResponseModeContract"
STATUS = "PASS_A1FS_V1_CORE_SIX_RESPONSE_MODE_CONTRACT"
REVISION = "UNIT01_TO_UNIT24_CORE_RESPONSE_MODE_V1"
UNIT_SCOPE = tuple(range(1, 25))

# Stable learner interaction primitives approved for Unit01-Unit24.
# These describe only what the learner physically/observably does to answer.
CORE_RESPONSE_MODES = (
    "SELECT",
    "MATCH",
    "TEXT_ENTRY",
    "STRUCTURED_ENTRY",
    "ORDER",
    "SPEAK",
)

# Picture interaction is intentionally not part of the approved six-mode no-picture core.
# It remains deferred until a later image-generation and picture-task acceptance milestone.
DEFERRED_PICTURE_RESPONSE_MODES = frozenset(
    {"PICTURE_POSITION", "PICTURE_LABEL", "PICTURE_DIFFERENCE"}
)
PICTURE_INTERACTION_ACTIVE = False

LEGACY_MODE_TO_CORE = {
    "SELECT_ONE": "SELECT",
    "GIST_BEST_TITLE": "SELECT",
    "MATCHING": "MATCH",
    "MULTIPLE_MATCHING": "MATCH",
    "REFERENCE_MATCHING": "MATCH",
    "ONE_WORD_GAP": "TEXT_ENTRY",
    "ONE_TO_THREE_WORDS": "TEXT_ENTRY",
    "SHORT_ANSWER": "TEXT_ENTRY",
    "SENTENCE_COMPLETION": "TEXT_ENTRY",
    "WRITE_SENTENCE": "TEXT_ENTRY",
    "FACT_CORRECTION": "TEXT_ENTRY",
    "RECONSTRUCTION": "TEXT_ENTRY",
    "ASK_A_QUESTION": "TEXT_ENTRY",
    "NOTE_COMPLETION": "STRUCTURED_ENTRY",
    "TABLE_COMPLETION": "STRUCTURED_ENTRY",
    "ORDER_SEQUENCE": "ORDER",
    "SPEAK_SHORT_RESPONSE": "SPEAK",
    "SHORT_RETELL": "SPEAK",
}


class CoreResponseModeContractError(ValueError):
    pass


def project_core_response_mode(task: dict[str, Any]) -> str | None:
    """Project an already-authored task onto the approved core response taxonomy.

    Returns None only for currently deferred picture-response modes.
    DIALOGUE_RESPONSE is resolved from the learner's actual response action:
    select-one dialogue -> SELECT; written dialogue response -> TEXT_ENTRY.
    """

    legacy_mode = str(task.get("response_mode") or "")
    if legacy_mode in DEFERRED_PICTURE_RESPONSE_MODES:
        return None
    if legacy_mode == "DIALOGUE_RESPONSE":
        dialogue_mode = str(task.get("dialogue_mode") or "short_text")
        if dialogue_mode == "select_one":
            return "SELECT"
        if dialogue_mode == "short_text":
            return "TEXT_ENTRY"
        raise CoreResponseModeContractError(
            f"UNKNOWN_DIALOGUE_RESPONSE_ACTION:{dialogue_mode}"
        )
    core = LEGACY_MODE_TO_CORE.get(legacy_mode)
    if core is None:
        raise CoreResponseModeContractError(f"UNMAPPED_RESPONSE_MODE:{legacy_mode}")
    return core


def validate_contract() -> dict[str, Any]:
    if UNIT_SCOPE != tuple(range(1, 25)):
        raise CoreResponseModeContractError("UNIT_SCOPE_DRIFT")
    if len(CORE_RESPONSE_MODES) != 6 or len(set(CORE_RESPONSE_MODES)) != 6:
        raise CoreResponseModeContractError("CORE_MODE_COUNT_DRIFT")
    if set(LEGACY_MODE_TO_CORE.values()) - set(CORE_RESPONSE_MODES):
        raise CoreResponseModeContractError("LEGACY_MAPPING_TARGET_OUTSIDE_CORE")
    if PICTURE_INTERACTION_ACTIVE is not False:
        raise CoreResponseModeContractError("PICTURE_INTERACTION_PREMATURELY_ACTIVE")
    if DEFERRED_PICTURE_RESPONSE_MODES & set(LEGACY_MODE_TO_CORE):
        raise CoreResponseModeContractError("PICTURE_MODE_MAPPED_INTO_SIX_MODE_CORE")
    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "unit_scope": list(UNIT_SCOPE),
        "core_response_modes": list(CORE_RESPONSE_MODES),
        "core_response_mode_count": 6,
        "picture_interaction_active": False,
        "deferred_picture_response_modes": sorted(DEFERRED_PICTURE_RESPONSE_MODES),
        "definition": "LEARNER_OBSERVABLE_RESPONSE_ACTION",
        "task_family_separate": True,
        "assessment_capability_separate": True,
        "response_format_separate": True,
    }
