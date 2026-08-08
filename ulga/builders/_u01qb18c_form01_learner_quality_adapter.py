"""Learner-facing Unit01 Form quality adapter over the existing U01QB13/U01QB15 path.

The exact fresh Form01 learner review exposed three product defects that are not
QuestionBank-capacity failures:

* WORD_ORDER items carried their token bank in ``options`` and were therefore
  rendered/scored as single-choice before the WORD_ORDER response contract could
  apply;
* Speaking prompts projected ``scene_anchors[0]`` instead of the lexical noun of
  the item actually selected by the canonical matcher, and Form01 asked a fresh
  learner for unsupported spontaneous production;
* contextual items such as ``park in the park`` were lexically/contextually
  eligible even though the resulting learner sentence was tautological.

This adapter keeps the current 474-item QuestionBank, U01QB13 blueprint,
whole-form distinct matcher, M3/M6 state/scoring, and learner database authority.
It only strengthens candidate admission and learner-facing projection.  It does
not write the canonical graph, author assessed QuestionBank items, add a planner,
add a runtime, modify Unit02-24, enable audio/Speaking scoring, or unlock A2.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as target,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Learner-facing projection and candidate-quality guard over the existing "
    "U01QB13/U01QB15 authority. It reinterprets existing WORD_ORDER option tokens, "
    "derives Speaking scaffolds from the already-selected item's lexical noun and "
    "existing scene anchors, and rejects tautological contextual bindings; it creates "
    "no assessed QuestionBank content, planner, runtime, scoring authority, learner "
    "database, Unit02-24 content, audio, Speaking score, or A2 content."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18C_Unit01Form01LearnerFacingInteractionSceneAndContentFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18C_UNIT01_FORM01_LEARNER_FACING_INTERACTION_SCENE_AND_CONTENT_FULLFIX"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18D_Unit01Form01FreshLearnerRematerializationAndLearnerPdfReacceptance"

FORM01_SCAFFOLD_STAGE = "MODEL_FRAME_TARGET_WORD"
FORM02_SCAFFOLD_STAGE = "FRAME_TARGET_WORD"
FORM03_SCAFFOLD_STAGE = "TARGET_WORD_ONLY"
FORM04_PLUS_SCAFFOLD_STAGE = "SCENE_PROMPT_ONLY"
WORD_ORDER_INTERACTION = "ORDERED_TOKENS_TEXT_ENTRY"

_ORIGINAL_CANDIDATE_RANK = target._candidate_rank
_ORIGINAL_FORM_COMPONENT_PAYLOAD = target.form_component_payload
_INSTALLED = False


class LearnerQualityProjectionError(ValueError):
    """Fail-closed U01QB18C learner projection error."""


def _private_item(row: Mapping[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(str(row["private_item_json"]))
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise LearnerQualityProjectionError("PRIVATE_ITEM_JSON_INVALID") from exc
    if not isinstance(value, Mapping):
        raise LearnerQualityProjectionError("PRIVATE_ITEM_PAYLOAD_INVALID")
    return dict(value)


def lexical_noun(item: Mapping[str, Any]) -> str:
    slots = item.get("lexical_slots")
    if not isinstance(slots, Mapping):
        return ""
    return str(slots.get("noun") or "").strip().casefold()


def _setting_words(setting: str) -> set[str]:
    return set(re.findall(r"[a-z]+", str(setting).casefold().replace("_", " ")))


def has_self_location_tautology(item: Mapping[str, Any]) -> bool:
    """Reject generic noun/location collisions such as ``park in the park``."""
    noun = lexical_noun(item)
    if not noun:
        return False
    text = " ".join(str(item.get("stimulus") or "").casefold().split())
    if not text:
        return False
    escaped = re.escape(noun)
    pattern = rf"\b{escaped}\b\s+(?:in|at|on|near)\s+(?:a|an|the)\s+\b{escaped}\b"
    return re.search(pattern, text) is not None


def learner_content_quality_ok(item: Mapping[str, Any]) -> bool:
    return not has_self_location_tautology(item)


def candidate_rank_with_learner_quality_gate(*args: Any, **kwargs: Any):
    row = kwargs.get("row")
    if row is None and args:
        row = args[0]
    if not isinstance(row, Mapping):
        raise LearnerQualityProjectionError("CANDIDATE_ROW_MISSING")
    if not learner_content_quality_ok(_private_item(row)):
        return None
    return _ORIGINAL_CANDIDATE_RANK(*args, **kwargs)


def _indefinite_article(noun: str) -> str:
    noun = str(noun).strip().casefold()
    return "an" if noun[:1] in {"a", "e", "i", "o", "u"} else "a"


def _model_noun(
    *,
    target_noun: str,
    scene_anchors: Sequence[str],
    setting: str,
) -> str:
    setting_words = _setting_words(setting)
    candidates = sorted(
        {
            str(value).strip().casefold()
            for value in scene_anchors
            if str(value).strip()
            and str(value).strip().casefold() != target_noun
            and str(value).strip().casefold() not in setting_words
        }
    )
    if candidates:
        return candidates[0]
    for fallback in ("book", "bag", "cat"):
        if fallback != target_noun:
            return fallback
    raise LearnerQualityProjectionError("SPEAKING_MODEL_NOUN_UNAVAILABLE")


def _speaking_prompt(task_angle: str, target_noun: str) -> str:
    if task_angle == "SCENE_DESCRIPTION":
        return f"Say one short sentence about the {target_noun}."
    if task_angle == "COMPLETE_SENTENCE_PRODUCTION":
        return f"Say one complete sentence with the word {target_noun}."
    if task_angle == "CONNECTED_SENTENCE_PRODUCTION":
        return f"Say two connected sentences with the word {target_noun}."
    raise LearnerQualityProjectionError(f"SPEAKING_ANGLE_UNSUPPORTED:{task_angle}")


def _sentence_frame(task_angle: str) -> str:
    if task_angle == "CONNECTED_SENTENCE_PRODUCTION":
        return "This is ___ ______. The ______ is here."
    return "This is ___ ______."


def speaking_scaffold(
    *,
    form_ordinal: int,
    task_angle: str,
    target_noun: str,
    scene_anchors: Sequence[str],
    setting: str,
) -> dict[str, str]:
    """Progressively withdraw support without changing the assessed denominator."""
    target_noun = str(target_noun).strip().casefold()
    if not target_noun:
        raise LearnerQualityProjectionError("SPEAKING_TARGET_NOUN_MISSING")
    prompt = _speaking_prompt(task_angle, target_noun)
    frame = _sentence_frame(task_angle)

    if form_ordinal == 1:
        model_noun = _model_noun(
            target_noun=target_noun,
            scene_anchors=scene_anchors,
            setting=setting,
        )
        model = f"This is {_indefinite_article(model_noun)} {model_noun}."
        if task_angle == "CONNECTED_SENTENCE_PRODUCTION":
            model += f" The {model_noun} is here."
        stimulus = (
            f"Example: {model} | Your turn: {frame} | Word: {target_noun}"
        )
        stage = FORM01_SCAFFOLD_STAGE
        prompt = "Complete the sentence frame, then say it aloud."
    elif form_ordinal == 2:
        stimulus = f"Your turn: {frame} | Word: {target_noun}"
        stage = FORM02_SCAFFOLD_STAGE
        prompt = "Complete the sentence frame, then say it aloud."
    elif form_ordinal == 3:
        stimulus = f"Word: {target_noun}"
        stage = FORM03_SCAFFOLD_STAGE
    else:
        stimulus = ""
        stage = FORM04_PLUS_SCAFFOLD_STAGE

    return {
        "stage": stage,
        "prompt": prompt,
        "stimulus": stimulus,
        "target_word": target_noun,
        "sentence_frame": frame if form_ordinal <= 2 else "",
    }


def _word_order_example(tokens: Sequence[str]) -> str:
    # A different worked example teaches the ordering rule without reproducing
    # the target phrase itself. The target token bank remains unchanged.
    if len(tokens) >= 3:
        return "a small book"
    return "a book"


def repair_learner_item(
    item: Mapping[str, Any],
    *,
    private_item: Mapping[str, Any],
    form_ordinal: int,
    scene_anchors: Sequence[str],
    setting: str,
) -> dict[str, Any]:
    value = dict(item)
    skill = str(value.get("skill") or "").upper()
    task_angle = str(value.get("task_angle") or "")

    if task_angle == "WORD_ORDER":
        tokens = [str(token) for token in value.get("options") or []]
        if len(tokens) < 2:
            raise LearnerQualityProjectionError("WORD_ORDER_TOKEN_BANK_INVALID")
        value["ordered_tokens"] = tokens
        value["options"] = []
        value["stimulus"] = (
            f"Example: {_word_order_example(tokens)} | Words: "
            + " | ".join(tokens)
        )
        value["word_order_interaction"] = WORD_ORDER_INTERACTION

    if skill == "SPEAKING":
        noun = lexical_noun(private_item)
        if not noun:
            raise LearnerQualityProjectionError(
                f"SPEAKING_SELECTED_ITEM_NOUN_MISSING:{value.get('item_id')}"
            )
        scaffold = speaking_scaffold(
            form_ordinal=form_ordinal,
            task_angle=task_angle,
            target_noun=noun,
            scene_anchors=scene_anchors,
            setting=setting,
        )
        value["prompt"] = scaffold["prompt"]
        value["stimulus"] = scaffold["stimulus"]
        value["speaking_scaffold_stage"] = scaffold["stage"]
        value["target_word"] = scaffold["target_word"]
        value["sentence_frame"] = scaffold["sentence_frame"]

    return value


def form_component_payload_with_learner_quality(
    connection,
    *,
    session_id: str,
) -> dict[str, Any]:
    value = _ORIGINAL_FORM_COMPONENT_PAYLOAD(connection, session_id=session_id)
    rows = connection.execute(
        """SELECT b.activity_id,a.form_ordinal,a.scene_anchors_json,a.setting,
                  c.private_item_json
           FROM u01qb13_session_bindings b
           JOIN u01qb13_blueprint_activities a USING(activity_id)
           JOIN u01qb02_item_catalog c USING(item_id)
           WHERE b.session_id=?""",
        (session_id,),
    ).fetchall()
    metadata = {
        str(row["activity_id"]): {
            "form_ordinal": int(row["form_ordinal"]),
            "scene_anchors": json.loads(str(row["scene_anchors_json"])),
            "setting": str(row["setting"]),
            "private_item": _private_item(row),
        }
        for row in rows
    }
    repaired = []
    for source in value.get("items") or []:
        activity_id = str(source.get("activity_id") or "")
        meta = metadata.get(activity_id)
        if meta is None:
            raise LearnerQualityProjectionError(
                f"FORM_COMPONENT_ACTIVITY_METADATA_MISSING:{activity_id}"
            )
        repaired.append(
            repair_learner_item(
                source,
                private_item=meta["private_item"],
                form_ordinal=int(meta["form_ordinal"]),
                scene_anchors=list(meta["scene_anchors"]),
                setting=str(meta["setting"]),
            )
        )
    value["items"] = repaired
    value["learner_quality_fullfix"] = PASS_STATUS
    return value


def install() -> None:
    global _INSTALLED
    if (
        target._candidate_rank is candidate_rank_with_learner_quality_gate
        and target.form_component_payload is form_component_payload_with_learner_quality
    ):
        _INSTALLED = True
        return
    if target._candidate_rank is not _ORIGINAL_CANDIDATE_RANK:
        raise LearnerQualityProjectionError(
            "U01QB13_CANDIDATE_RANK_ALREADY_PATCHED_BY_OTHER_AUTHORITY"
        )
    if target.form_component_payload is not _ORIGINAL_FORM_COMPONENT_PAYLOAD:
        raise LearnerQualityProjectionError(
            "U01QB13_FORM_COMPONENT_PAYLOAD_ALREADY_PATCHED_BY_OTHER_AUTHORITY"
        )
    target._candidate_rank = candidate_rank_with_learner_quality_gate
    target.form_component_payload = form_component_payload_with_learner_quality
    _INSTALLED = True


def installed() -> bool:
    return (
        _INSTALLED
        and target._candidate_rank is candidate_rank_with_learner_quality_gate
        and target.form_component_payload is form_component_payload_with_learner_quality
    )
