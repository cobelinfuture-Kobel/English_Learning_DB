#!/usr/bin/env python3
"""Unit04 Q10R1 learner-facing pedagogical acceptance over locked Q10 identity.

Consumes the exact merged Unit04 Q10 20x40 runtime, preserves every source
QuestionBank/runtime/candidate identity, projects learner-safe activities, and
validates learner-facing answerability, evidence, progression, and variety.
PDF/visual acceptance remains Q10R2.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18a_form01_fresh_learner_materialization_export as u01_learner,
)
from product.a1fs_v1_2_1 import (
    u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as u01_pdf,
)
from ulga.builders import build_a1fs_v1_u04q10_questionbank_form_materialization as source
from ulga.validators import (
    validate_a1fs_v1_u04q10_questionbank_form_materialization as source_validator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only learner-facing acceptance consumer over the approved Unit04 Q10 "
    "20x40 runtime. It preserves all 800 QuestionBank/runtime selected and "
    "candidate identities, suppresses engineering-only metadata, reuses the "
    "accepted Unit01 learner activity HTML renderer and the merged Q10 validator, "
    "and creates no new content authority, selector, sentence, scene, scoring, "
    "PDF, Unit05, or A2 authority."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U04Q10R1_Unit04LearnerFacingPedagogicalAcceptance"
SCHEMA_VERSION = "a1fs.v1.u04.q10r1.learner_facing_pedagogical_acceptance.v2"
PASS_STATUS = "PASS_A1FS_V1_U04Q10R1_UNIT04_LEARNER_FACING_PEDAGOGICAL_ACCEPTANCE"
NEXT_SHORT_STEP = "A1FS-V1-U04Q10R2_Unit04LearnerPDFMaterializationAndVisualAcceptance"

FORM_COUNT = 20
ACTIVITIES_PER_FORM = 40
TOTAL_ACTIVITIES = 800
SECTION_ORDER = ("A", "B", "C", "D", "E")
SECTION_COUNTS = {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
SECTION_TITLES = {
    "A": "Choose the place word",
    "B": "Understand the position",
    "C": "Build and fix place phrases",
    "D": "Use place words in context",
    "E": "Write and use what you know",
}
ALLOWED_RESPONSE_MODES = frozenset({"select_one", "short_text"})
SELECTED_RELATION_FAMILIES = frozenset({
    "U04-TF01_RECOGNITION",
    "U04-TF02_MEANING_DISCRIMINATION",
    "U04-TF03_FORM_SELECTION",
    "U04-TF08_U01_U02_U03_INTEGRATION",
})
FORBIDDEN_LEARNER_MARKERS = (
    "scene_ref_id", "source_scene_ref", "source_sentence_id", "selected_item_id",
    "candidate_ids", "runtime_occurrence_id", "questionbank_item_id",
    "semantic_signature", "response_contract", "correct_answer",
    "answerability_basis", "evidence_mode", "evidence_role", "fabricated_scene_ref",
    "human-reviewable", "licensed", "admitted", "authority",
    "a1fs-v1", "a1fs_v1", "u04-tf", "u04-cf", "u04q10", "u04_q10", "u04-q10", "pass_a1fs",
)
RELATION_CUES = {
    "in": "The located thing is within the place boundaries.",
    "inside": "The place fully encloses the located thing.",
    "on": "The located thing touches and is supported by a surface.",
    "near": "The located thing and landmark are a short distance apart.",
    "at": "The person or thing is connected with one general place.",
    "under": "The located thing is lower than the landmark.",
    "behind": "The located thing is farther back than the landmark.",
    "between": "The located thing is in the space separating two different landmarks.",
}
STAGE_PREFIX = {
    "GUIDED": "Use the meaning help. ",
    "REDUCED_SUPPORT": "Use the position fact. ",
    "INDEPENDENT": "",
    "TRANSFER": "Apply the evidence to this new situation. ",
    "RETENTION": "Use what you remember. ",
}
STAGE_VISIBLE_MARKERS = {
    "GUIDED": "Meaning help:",
    "REDUCED_SUPPORT": "Position fact:",
    "INDEPENDENT": "Evidence:",
    "TRANSFER": "New situation:",
    "RETENTION": "Review evidence:",
}
STAGE_SUPPORT_LEVEL = {
    "GUIDED": "HIGH",
    "REDUCED_SUPPORT": "MEDIUM",
    "INDEPENDENT": "LOW",
    "TRANSFER": "MINIMAL",
    "RETENTION": "CUMULATIVE",
}
TRANSFER_FRAMES = {
    "U04-CF01_STATE_ENTITY_LOCATION": "Write where the person or thing is.",
    "U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION": "Ask where the person or thing is.",
    "U04-CF03_IDENTIFY_ENTITY_BY_LOCATION": "Use the place information to find the right person or thing.",
    "U04-CF04_CONFIRM_LOCATION_RELATION": "Check whether the place information is right.",
    "U04-CF05_DESCRIBE_SPATIAL_SCENE": "Tell someone what the static place looks like.",
    "U04-CF06_DISTINGUISH_SPATIAL_RELATION": "Use the place information to choose the right place word.",
}


class Unit04LearnerFacingAcceptanceError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _runtime_identity(runtime: Sequence[Mapping[str, Any]]) -> str:
    return _digest([
        {
            "slot_id": row["slot_id"],
            "form_number": row["form_number"],
            "progression_role": row["progression_role"],
            "section": row["section"],
            "section_activity_ordinal": row["section_activity_ordinal"],
            "task_family_id": row["task_family_id"],
            "selected_item_id": row["selected_item_id"],
            "candidate_ids": list(row["candidate_ids"]),
        }
        for row in runtime
    ])


def _item_identity(items: Sequence[Mapping[str, Any]]) -> str:
    return _digest([
        {
            "item_id": row["item_id"],
            "semantic_signature": row["semantic_signature"],
            "form_number": row["form_number"],
            "section": row["section"],
            "task_family_id": row["task_family_id"],
            "relation_surface": row["relation_surface"],
            "communicative_function_id": row["communicative_function_id"],
        }
        for row in items
    ])


def _source_contract(payload: Mapping[str, Any]) -> None:
    source_validator.validate_payload(payload)
    if payload.get("status") != source.PASS_STATUS:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_STATUS_INVALID")
    if payload.get("next_short_step") != TASK_ID:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_NEXT_STEP_INVALID")
    contract = dict(payload.get("materialization_contract") or {})
    expected = {
        "form_count": 20,
        "questions_per_form": 40,
        "questionbank_item_count": 800,
        "runtime_occurrence_count": 800,
        "candidate_count_per_slot": 3,
        "section_counts_per_form": SECTION_COUNTS,
        "task_family_count": 10,
        "target_relation_count": 8,
        "communicative_function_count": 6,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            raise Unit04LearnerFacingAcceptanceError(
                f"SOURCE_CONTRACT_DRIFT:{key}:{contract.get(key)}:{value}"
            )
    coverage = dict(payload.get("coverage") or {})
    expected_coverage = {
        "task_family_coverage": "10/10",
        "target_relation_coverage": "8/8",
        "communicative_function_coverage": "6/6",
        "exact_semantic_duplicate_count": 0,
        "at_scene_ref_count": 0,
        "fabricated_scene_ref_count": 0,
        "support_relation_item_count": 0,
    }
    for key, value in expected_coverage.items():
        if coverage.get(key) != value:
            raise Unit04LearnerFacingAcceptanceError(
                f"SOURCE_COVERAGE_DRIFT:{key}:{coverage.get(key)}:{value}"
            )
    boundaries = dict(payload.get("boundaries") or {})
    if not boundaries or any(value is not False for value in boundaries.values()):
        raise Unit04LearnerFacingAcceptanceError("SOURCE_BOUNDARY_DRIFT")


def _subject(item: Mapping[str, Any]) -> str:
    text = str(item.get("source_sentence_text") or "").strip().rstrip(".?!")
    relation = str(item.get("relation_surface") or "").strip()
    match = re.search(rf"\b{re.escape(relation)}\b", text, flags=re.I) if text and relation else None
    head = text[:match.start()].strip() if match else text
    head = re.sub(r"\b(?:am|is|are)\s*$", "", head, flags=re.I).strip()
    if not head:
        return "the thing"
    return "I" if head.casefold() == "i" else head[:1].lower() + head[1:]


def _complement(item: Mapping[str, Any]) -> str:
    phrase = str(item.get("place_phrase") or "").strip()
    relation = str(item.get("relation_surface") or "").strip()
    prefix = f"{relation} "
    value = phrase[len(prefix):].strip() if phrase.casefold().startswith(prefix.casefold()) else phrase
    if not value:
        raise Unit04LearnerFacingAcceptanceError(f"PLACE_COMPLEMENT_MISSING:{item.get('item_id')}")
    return value


def _mask_relation_sentence(item: Mapping[str, Any]) -> str:
    text = str(item.get("source_sentence_text") or "").strip()
    relation = str(item.get("relation_surface") or "").strip()
    masked, count = re.subn(rf"\b{re.escape(relation)}\b", "___", text, count=1, flags=re.I)
    if count != 1:
        raise Unit04LearnerFacingAcceptanceError(f"RELATION_MASK_FAILED:{item.get('item_id')}")
    return masked


def _mask_place_phrase_sentence(item: Mapping[str, Any]) -> str:
    text = str(item.get("source_sentence_text") or "").strip()
    phrase = str(item.get("place_phrase") or "").strip()
    if text and phrase:
        masked, count = re.subn(re.escape(phrase), "___", text, count=1, flags=re.I)
        if count == 1:
            return masked
    return _mask_relation_sentence(item)


def _cue(item: Mapping[str, Any]) -> str:
    relation = str(item.get("relation_surface") or "")
    try:
        return RELATION_CUES[relation]
    except KeyError as exc:
        raise Unit04LearnerFacingAcceptanceError(f"RELATION_CUE_MISSING:{relation}") from exc


def _position_fact(item: Mapping[str, Any]) -> str:
    relation = str(item.get("relation_surface") or "")
    complement = _complement(item)
    if relation == "in":
        return f"{complement} contains the located thing within its boundaries."
    if relation == "inside":
        return f"{complement} encloses the located thing."
    if relation == "on":
        return f"The located thing touches and is supported by {complement}."
    if relation == "near":
        return f"The located thing and {complement} are a short distance apart."
    if relation == "at":
        return f"The general place is {complement}."
    if relation == "under":
        return f"The located thing is lower than {complement}."
    if relation == "behind":
        return f"The located thing is farther back than {complement}."
    if relation == "between":
        landmarks = [str(value).strip() for value in item.get("reference_landmarks") or []]
        if len(landmarks) != 2 or len(set(value.casefold() for value in landmarks)) != 2:
            raise Unit04LearnerFacingAcceptanceError(
                f"BETWEEN_LANDMARK_INVALID:{item.get('item_id')}"
            )
        return f"The located thing is in the space separating {landmarks[0]} and {landmarks[1]}."
    raise Unit04LearnerFacingAcceptanceError(f"POSITION_FACT_MISSING:{relation}")


def _transfer_frame(item: Mapping[str, Any]) -> str:
    cf = str(item.get("communicative_function_id") or "")
    try:
        return TRANSFER_FRAMES[cf]
    except KeyError as exc:
        raise Unit04LearnerFacingAcceptanceError(f"TRANSFER_FRAME_MISSING:{cf}") from exc


def _support_text(item: Mapping[str, Any]) -> str:
    stage = str(item.get("progression_role") or "")
    if stage == "GUIDED":
        return f"Meaning help: {_cue(item)}"
    if stage == "REDUCED_SUPPORT":
        return f"Position fact: {_position_fact(item)}"
    if stage == "INDEPENDENT":
        return f"Evidence: {_position_fact(item)}"
    if stage == "TRANSFER":
        return f"New situation: {_transfer_frame(item)} | Evidence: {_position_fact(item)}"
    if stage == "RETENTION":
        return f"Review evidence: {_position_fact(item)}"
    raise Unit04LearnerFacingAcceptanceError(f"STAGE_SUPPORT_MISSING:{stage}")


def _prompt(item: Mapping[str, Any]) -> str:
    family = str(item["task_family_id"])
    relation = str(item["relation_surface"])
    cf = str(item["communicative_function_id"])
    stage = str(item["progression_role"])
    if stage not in STAGE_PREFIX:
        raise Unit04LearnerFacingAcceptanceError(f"STAGE_PROMPT_SUPPORT_MISSING:{stage}")
    if family == "U04-TF01_RECOGNITION":
        core = "Which place word matches the position evidence?"
    elif family == "U04-TF02_MEANING_DISCRIMINATION":
        core = "Which place word best describes the position?"
    elif family == "U04-TF03_FORM_SELECTION":
        core = "Choose the correct place word for the sentence."
    elif family == "U04-TF04_PLACE_PHRASE_CONSTRUCTION":
        core = f"Use {relation} and the place information to write the complete place phrase."
    elif family == "U04-TF05_ERROR_DETECTION":
        core = "Does the place phrase match the position? Choose MATCHES or DOES NOT MATCH."
    elif family == "U04-TF06_ERROR_CORRECTION":
        core = "Rewrite the place phrase so it matches the position."
    elif family == "U04-TF07_CONTEXT_GAP":
        core = "Write the missing place phrase."
    elif family == "U04-TF08_U01_U02_U03_INTEGRATION":
        core = "Choose the place word that still describes the position."
    elif family == "U04-TF09_PRODUCTIVE_RESPONSE":
        if cf == "U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION":
            core = "Ask a natural question about the location."
        elif relation == "at":
            core = "Use the subject and place information to write one natural sentence."
        else:
            core = "Write one complete sentence describing the location."
    elif family == "U04-TF10_TRANSFER":
        if cf == "U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION":
            core = "Ask a natural location question for this context."
        elif list(item.get("options") or []):
            core = "Choose the place word that matches this context."
        else:
            core = "Write one complete location sentence for this context."
    else:
        raise Unit04LearnerFacingAcceptanceError(f"UNSUPPORTED_TASK_FAMILY:{family}")
    return f"{STAGE_PREFIX[stage]}{core}".strip()


def _stimulus(item: Mapping[str, Any]) -> str:
    family = str(item["task_family_id"])
    relation = str(item["relation_surface"])
    cf = str(item["communicative_function_id"])
    raw = dict(item.get("stimulus") or {})
    support = _support_text(item)
    complement = _complement(item)
    subject = _subject(item)
    context = _mask_relation_sentence(item)

    if family in {"U04-TF01_RECOGNITION", "U04-TF02_MEANING_DISCRIMINATION", "U04-TF03_FORM_SELECTION"}:
        return f"Context: {context} | {support}"
    if family == "U04-TF05_ERROR_DETECTION":
        candidate = str(raw.get("candidate_place_phrase") or "").strip()
        if not candidate:
            raise Unit04LearnerFacingAcceptanceError(f"CANDIDATE_PHRASE_MISSING:{item.get('item_id')}")
        return f"Context: {context} | Place phrase: {candidate} | {support}"
    if family == "U04-TF04_PLACE_PHRASE_CONSTRUCTION":
        return f"Context: {context} | Place word: {relation} | Place: {complement} | {support}"
    if family == "U04-TF06_ERROR_CORRECTION":
        incorrect = str(raw.get("incorrect_place_phrase") or "").strip()
        if not incorrect:
            raise Unit04LearnerFacingAcceptanceError(f"INCORRECT_PHRASE_MISSING:{item.get('item_id')}")
        return f"Context: {context} | Incorrect phrase: {incorrect} | {support}"
    if family == "U04-TF07_CONTEXT_GAP":
        return f"Context: {_mask_place_phrase_sentence(item)} | {support}"
    if family == "U04-TF08_U01_U02_U03_INTEGRATION":
        one = str(raw.get("unit01_article_carrier") or "").strip()
        two = str(raw.get("unit02_plural_carrier") or "").strip()
        reference = str(raw.get("unit03_reference_carrier") or "").strip()
        if not one or not two or not reference:
            raise Unit04LearnerFacingAcceptanceError(f"CUMULATIVE_CARRIER_MISSING:{item.get('item_id')}")
        return (
            f"One: {one} | Two: {two} | Reference: {reference} | "
            f"Context: {context} | {support}"
        )
    if family == "U04-TF09_PRODUCTIVE_RESPONSE":
        if cf == "U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION":
            return f"Subject: {subject} | {support}"
        if relation == "at":
            if item.get("scene_ref_id") is not None:
                raise Unit04LearnerFacingAcceptanceError(f"AT_SCENE_REF_PRESENT:{item.get('item_id')}")
            return (
                f"Text context: {context} | Subject: {subject} | "
                f"Place word: at | Place: the park | {support}"
            )
        return f"Context: {context} | Place or object: {complement} | {support}"
    if family == "U04-TF10_TRANSFER":
        if cf == "U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION":
            return f"Subject: {subject} | {support}"
        if list(item.get("options") or []):
            return f"Context: {context} | {support}"
        return f"Context: {context} | Place or object: {complement} | {support}"
    raise Unit04LearnerFacingAcceptanceError(f"UNSUPPORTED_STIMULUS_FAMILY:{family}")


def _learner_activity(number: int, item: Mapping[str, Any]) -> dict[str, Any]:
    options = [str(value) for value in item.get("options") or []]
    return {
        "question_number": f"Q{number:02d}",
        "skill": "Grammar",
        "stimulus": _stimulus(item),
        "prompt": _prompt(item),
        "options": options,
        "response_mode": "select_one" if options else "short_text",
        "capture_enabled": True,
        "practice_only": False,
    }


def _assert_no_engineering_markers(
    activity: Mapping[str, Any], form_number: int, question_number: int
) -> None:
    text = " ".join((
        str(activity.get("stimulus") or ""),
        str(activity.get("prompt") or ""),
        " ".join(str(value) for value in activity.get("options") or []),
    )).casefold()
    for marker in FORBIDDEN_LEARNER_MARKERS:
        if marker.casefold() in text:
            raise Unit04LearnerFacingAcceptanceError(
                f"ENGINEERING_MARKER_VISIBLE:F{form_number:02d}:Q{question_number:02d}:{marker}"
            )


def _project_forms(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = list(payload.get("questionbank_items") or [])
    runtime = list(payload.get("runtime_bindings") or [])
    source_forms = list(payload.get("forms") or [])
    if (len(items), len(runtime), len(source_forms)) != (800, 800, 20):
        raise Unit04LearnerFacingAcceptanceError("SOURCE_DENOMINATOR_INVALID")
    item_index = {str(row["item_id"]): row for row in items}
    runtime_index = {str(row["selected_item_id"]): row for row in runtime}
    if len(item_index) != 800 or len(runtime_index) != 800:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_SELECTED_IDENTITY_COLLISION")

    forms = []
    for form_number in range(1, 21):
        source_form = source_forms[form_number - 1]
        if int(source_form.get("form_number", -1)) != form_number:
            raise Unit04LearnerFacingAcceptanceError(f"SOURCE_FORM_SEQUENCE_INVALID:F{form_number:02d}")
        activities = []
        sections = []
        section_item_ids = dict(source_form.get("section_item_ids") or {})
        for section in SECTION_ORDER:
            ids = [str(value) for value in section_item_ids.get(section) or []]
            if len(ids) != SECTION_COUNTS[section]:
                raise Unit04LearnerFacingAcceptanceError(
                    f"SOURCE_SECTION_COUNT_INVALID:F{form_number:02d}:{section}"
                )
            for item_id in ids:
                item = item_index.get(item_id)
                runtime_row = runtime_index.get(item_id)
                if item is None or runtime_row is None:
                    raise Unit04LearnerFacingAcceptanceError(f"SOURCE_SELECTED_ITEM_UNRESOLVED:{item_id}")
                if int(item["form_number"]) != form_number or str(item["section"]) != section:
                    raise Unit04LearnerFacingAcceptanceError(f"ITEM_SCOPE_DRIFT:{item_id}")
                if int(runtime_row["form_number"]) != form_number or str(runtime_row["section"]) != section:
                    raise Unit04LearnerFacingAcceptanceError(f"RUNTIME_SCOPE_DRIFT:{item_id}")
                activity = _learner_activity(len(activities) + 1, item)
                _assert_no_engineering_markers(activity, form_number, len(activities) + 1)
                activities.append(activity)
            sections.append({
                "section": section,
                "section_name": SECTION_TITLES[section],
                "activity_count": SECTION_COUNTS[section],
            })
        form = {
            "unit_id": source.UNIT_ID,
            "unit_ordinal": 4,
            "form_id": f"U04Q10R1-F{form_number:02d}",
            "form_ordinal": form_number,
            "progression_stage": str(source_form["progression_role"]),
            "section_count": 5,
            "learner_visible_activity_count": 40,
            "sections": sections,
            "activities": activities,
        }
        u01_learner._assert_no_answer_leak(form)
        forms.append(form)
    return forms


def _word_present(text: str, value: str) -> bool:
    return re.search(rf"\b{re.escape(value)}\b", text, flags=re.I) is not None


def _normalize_visible(value: Any) -> str:
    text = str(value or "").casefold()
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _visible_payload(activity: Mapping[str, Any], normalized: bool = False) -> dict[str, Any]:
    norm = _normalize_visible if normalized else lambda value: str(value or "").strip()
    return {
        "stimulus": norm(activity.get("stimulus")),
        "prompt": norm(activity.get("prompt")),
        "options": [norm(value) for value in activity.get("options") or []],
        "response_mode": str(activity.get("response_mode") or ""),
    }


def _duplicate_excess(signatures: Sequence[str]) -> int:
    return sum(count - 1 for count in Counter(signatures).values() if count > 1)


def _validate_overlap_distractors(item: Mapping[str, Any], options: Sequence[str]) -> None:
    normalized = {_normalize_visible(value) for value in options}
    relation = str(item["relation_surface"])
    if relation == "in" and "inside" in normalized:
        raise Unit04LearnerFacingAcceptanceError(f"IN_INSIDE_FALSE_CONTRAST:{item['item_id']}")
    if relation == "inside" and "in" in normalized:
        raise Unit04LearnerFacingAcceptanceError(f"INSIDE_IN_FALSE_CONTRAST:{item['item_id']}")
    if relation == "at" and normalized:
        raise Unit04LearnerFacingAcceptanceError(f"AT_SELECTED_RESPONSE_FORBIDDEN:{item['item_id']}")
    if relation == "near" and "next to" in normalized:
        raise Unit04LearnerFacingAcceptanceError(f"NEAR_NEXT_TO_FALSE_CONTRAST:{item['item_id']}")
    if "next to" in normalized or "in front of" in normalized:
        raise Unit04LearnerFacingAcceptanceError(f"SUPPORT_RELATION_PROMOTED:{item['item_id']}")


def _validate_learner_forms(
    forms: Sequence[Mapping[str, Any]], payload: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len(forms) != 20:
        raise Unit04LearnerFacingAcceptanceError(f"FORM_COUNT_INVALID:{len(forms)}")

    items = {str(row["item_id"]): row for row in payload["questionbank_items"]}
    source_forms = list(payload["forms"])
    stage_counts: Counter[str] = Counter()
    stage_marker_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    function_counts: Counter[str] = Counter()
    response_counts: Counter[str] = Counter()
    exact_signatures: list[str] = []
    normalized_signatures: list[str] = []
    prompt_answer_signatures: list[str] = []
    answer_key_bindings: list[dict[str, Any]] = []
    rendered = 0
    at_count = 0
    scene_bound_count = 0
    answer_leaks = 0
    semantic_equivalent_distractors = 0
    within_form_exact_duplicates = 0
    within_form_normalized_duplicates = 0
    min_distinct_prompts_per_form = 40
    max_same_prompt_per_form = 0
    retention_carrier_count = 0
    transfer_context_count = 0

    for form_number, form in enumerate(forms, start=1):
        if int(form.get("form_ordinal", -1)) != form_number:
            raise Unit04LearnerFacingAcceptanceError(f"FORM_SEQUENCE_INVALID:F{form_number:02d}")
        if int(form.get("learner_visible_activity_count", -1)) != 40:
            raise Unit04LearnerFacingAcceptanceError(f"FORM_DENOMINATOR_INVALID:F{form_number:02d}")
        sections = list(form.get("sections") or [])
        if [str(row.get("section") or "") for row in sections] != list(SECTION_ORDER):
            raise Unit04LearnerFacingAcceptanceError(f"SECTION_ORDER_INVALID:F{form_number:02d}")
        if {str(row["section"]): int(row["activity_count"]) for row in sections} != SECTION_COUNTS:
            raise Unit04LearnerFacingAcceptanceError(f"SECTION_COUNTS_INVALID:F{form_number:02d}")

        stage = str(form.get("progression_stage") or "")
        marker = STAGE_VISIBLE_MARKERS.get(stage)
        if marker is None:
            raise Unit04LearnerFacingAcceptanceError(f"STAGE_INVALID:F{form_number:02d}:{stage}")

        activities = list(form.get("activities") or [])
        stage_counts[stage] += len(activities)
        source_ids = [str(value) for value in source_forms[form_number - 1]["item_ids"]]
        if len(source_ids) != 40 or len(activities) != 40:
            raise Unit04LearnerFacingAcceptanceError(f"FORM_BINDING_COUNT_INVALID:F{form_number:02d}")

        form_exact: list[str] = []
        form_normalized: list[str] = []
        form_prompt_counter: Counter[str] = Counter()

        for question_number, (activity, item_id) in enumerate(zip(activities, source_ids), start=1):
            item = items[item_id]
            if activity.get("question_number") != f"Q{question_number:02d}":
                raise Unit04LearnerFacingAcceptanceError(f"QUESTION_SEQUENCE_INVALID:{item_id}")
            if not str(activity.get("prompt") or "").strip() or not str(activity.get("stimulus") or "").strip():
                raise Unit04LearnerFacingAcceptanceError(f"LEARNER_TEXT_MISSING:{item_id}")
            if marker not in str(activity["stimulus"]):
                raise Unit04LearnerFacingAcceptanceError(
                    f"PROGRESSION_SUPPORT_NOT_VISIBLE:F{form_number:02d}:Q{question_number:02d}:{stage}"
                )
            stage_marker_counts[stage] += 1

            mode = str(activity.get("response_mode") or "")
            if mode not in ALLOWED_RESPONSE_MODES:
                raise Unit04LearnerFacingAcceptanceError(f"RESPONSE_MODE_INVALID:{item_id}:{mode}")
            response_counts[mode] += 1

            source_options = [str(value) for value in item.get("options") or []]
            learner_options = [str(value) for value in activity.get("options") or []]
            if learner_options != source_options:
                raise Unit04LearnerFacingAcceptanceError(f"OPTION_IDENTITY_INVALID:{item_id}")
            normalized_options = [_normalize_visible(value) for value in learner_options]
            if len(normalized_options) != len(set(normalized_options)):
                raise Unit04LearnerFacingAcceptanceError(f"NORMALIZED_OPTION_DUPLICATION:{item_id}")
            _validate_overlap_distractors(item, learner_options)

            correct_answer = item.get("correct_answer")
            if learner_options:
                if correct_answer not in learner_options or mode != "select_one":
                    raise Unit04LearnerFacingAcceptanceError(f"SELECTED_RESPONSE_INVALID:{item_id}")
            elif mode != "short_text":
                raise Unit04LearnerFacingAcceptanceError(f"CONSTRUCTED_RESPONSE_INVALID:{item_id}")

            family = str(item["task_family_id"])
            relation = str(item["relation_surface"])
            cf = str(item["communicative_function_id"])
            family_counts[family] += 1
            relation_counts[relation] += 1
            function_counts[cf] += 1

            if relation == "at":
                at_count += 1
                if (
                    item.get("scene_ref_id") is not None
                    or item.get("source_scene_ref") is not None
                    or family not in source.AT_ALLOWED_FAMILIES
                    or cf != source.AT_CF
                    or learner_options
                ):
                    raise Unit04LearnerFacingAcceptanceError(f"AT_ROUTE_INVALID:{item_id}")
            else:
                if not str(item.get("scene_ref_id") or "").strip():
                    raise Unit04LearnerFacingAcceptanceError(f"SCENE_REF_UNRESOLVED:{item_id}")
                scene_bound_count += 1

            if relation == "between":
                landmarks = [str(value) for value in item.get("reference_landmarks") or []]
                if len(landmarks) != 2 or len(set(value.casefold() for value in landmarks)) != 2:
                    raise Unit04LearnerFacingAcceptanceError(f"BETWEEN_LANDMARK_INVALID:{item_id}")

            selected_relation = (
                family in SELECTED_RELATION_FAMILIES
                or (family == "U04-TF10_TRANSFER" and bool(learner_options))
            )
            if selected_relation and _word_present(
                str(activity["stimulus"]) + " " + str(activity["prompt"]), relation
            ):
                answer_leaks += 1

            if family == "U04-TF07_CONTEXT_GAP" and "___" not in str(activity["stimulus"]):
                raise Unit04LearnerFacingAcceptanceError(f"CONTEXT_GAP_NOT_VISIBLE:{item_id}")
            if family == "U04-TF08_U01_U02_U03_INTEGRATION":
                text = str(activity["stimulus"])
                if any(value not in text for value in ("One:", "Two:", "Reference:")):
                    raise Unit04LearnerFacingAcceptanceError(f"CUMULATIVE_CARRIER_NOT_VISIBLE:{item_id}")
                if stage == "RETENTION":
                    retention_carrier_count += 1
            if stage == "TRANSFER":
                if "New situation:" not in str(activity["stimulus"]):
                    raise Unit04LearnerFacingAcceptanceError(f"TRANSFER_CONTEXT_NOT_VISIBLE:{item_id}")
                transfer_context_count += 1

            _assert_no_engineering_markers(activity, form_number, question_number)
            u01_pdf._activity_html(activity, question_number)
            rendered += 1

            exact = _canonical(_visible_payload(activity, normalized=False))
            normalized = _canonical(_visible_payload(activity, normalized=True))
            form_exact.append(exact)
            form_normalized.append(normalized)
            exact_signatures.append(exact)
            normalized_signatures.append(normalized)
            prompt_sig = _normalize_visible(activity.get("prompt"))
            form_prompt_counter[prompt_sig] += 1
            prompt_answer_signatures.append(_canonical({
                "prompt": prompt_sig,
                "answer": _normalize_visible(correct_answer) if correct_answer is not None else "<human-review>",
                "scoring_mode": str((item.get("response_contract") or {}).get("scoring_mode") or ""),
            }))
            answer_key_bindings.append({
                "form_number": form_number,
                "question_number": f"Q{question_number:02d}",
                "source_item_id": item_id,
                "response_mode": mode,
                "scoring_mode": str((item.get("response_contract") or {}).get("scoring_mode") or ""),
                "reference_answer": correct_answer,
            })

        within_form_exact_duplicates += _duplicate_excess(form_exact)
        within_form_normalized_duplicates += _duplicate_excess(form_normalized)
        min_distinct_prompts_per_form = min(min_distinct_prompts_per_form, len(form_prompt_counter))
        max_same_prompt_per_form = max(
            max_same_prompt_per_form,
            max(form_prompt_counter.values(), default=0),
        )
        u01_learner._assert_no_answer_leak(form)

    expected_stages = {
        "GUIDED": 160,
        "REDUCED_SUPPORT": 160,
        "INDEPENDENT": 160,
        "TRANSFER": 160,
        "RETENTION": 160,
    }
    if dict(stage_counts) != expected_stages or dict(stage_marker_counts) != expected_stages:
        raise Unit04LearnerFacingAcceptanceError(
            f"STAGE_COUNTS_INVALID:{dict(stage_counts)}:{dict(stage_marker_counts)}"
        )
    if answer_leaks:
        raise Unit04LearnerFacingAcceptanceError(f"SELECTED_RELATION_ANSWER_LEAKS:{answer_leaks}")
    if within_form_exact_duplicates or within_form_normalized_duplicates:
        raise Unit04LearnerFacingAcceptanceError(
            "WITHIN_FORM_VISIBLE_DUPLICATION:"
            f"EXACT={within_form_exact_duplicates}:NORMALIZED={within_form_normalized_duplicates}"
        )
    if min_distinct_prompts_per_form < 10 or max_same_prompt_per_form > 7:
        raise Unit04LearnerFacingAcceptanceError(
            f"WITHIN_FORM_TEMPLATE_CONCENTRATION:"
            f"MIN_DISTINCT={min_distinct_prompts_per_form}:MAX_REPEAT={max_same_prompt_per_form}"
        )
    if set(family_counts) != set(source._families()):
        raise Unit04LearnerFacingAcceptanceError("TASK_FAMILY_COVERAGE_INVALID")
    if set(relation_counts) != set(source.TARGET_RELATIONS):
        raise Unit04LearnerFacingAcceptanceError("RELATION_COVERAGE_INVALID")
    q08_ids = {
        str(row["function_id"])
        for row in source._sources()["q08"]["communicative_functions"]
    }
    if set(function_counts) != q08_ids:
        raise Unit04LearnerFacingAcceptanceError("FUNCTION_COVERAGE_INVALID")
    if at_count != 40 or scene_bound_count != 760 or rendered != 800:
        raise Unit04LearnerFacingAcceptanceError(
            f"LEARNER_DENOMINATOR_DRIFT:AT={at_count}:SCENE={scene_bound_count}:RENDERED={rendered}"
        )
    if len(answer_key_bindings) != 800:
        raise Unit04LearnerFacingAcceptanceError(
            f"ANSWER_KEY_BINDING_COUNT_INVALID:{len(answer_key_bindings)}"
        )
    if transfer_context_count != 160:
        raise Unit04LearnerFacingAcceptanceError(
            f"TRANSFER_CONTEXT_COUNT_INVALID:{transfer_context_count}"
        )
    if retention_carrier_count != 16:
        raise Unit04LearnerFacingAcceptanceError(
            f"RETENTION_CARRIER_COUNT_INVALID:{retention_carrier_count}:16"
        )

    exact_duplicates = _duplicate_excess(exact_signatures)
    normalized_duplicates = _duplicate_excess(normalized_signatures)
    prompt_answer_duplicates = _duplicate_excess(prompt_answer_signatures)

    acceptance = {
        "form_count": 20,
        "activity_count": 800,
        "rendered_activity_count": rendered,
        "answer_key_binding_count": len(answer_key_bindings),
        "stage_activity_counts": dict(stage_counts),
        "stage_support_levels": STAGE_SUPPORT_LEVEL,
        "stage_visible_support_counts": dict(stage_marker_counts),
        "transfer_context_activity_count": transfer_context_count,
        "retention_cumulative_carrier_activity_count": retention_carrier_count,
        "response_mode_counts": dict(response_counts),
        "task_family_coverage": "10/10",
        "target_relation_coverage": "8/8",
        "communicative_function_coverage": "6/6",
        "scene_bound_evidence_activity_count": scene_bound_count,
        "at_text_bound_activity_count": at_count,
        "at_scene_ref_render_count": 0,
        "fabricated_scene_ref_count": 0,
        "semantic_equivalent_distractor_count": semantic_equivalent_distractors,
        "duplicate_learner_visible_choice_count": 0,
        "selected_relation_answer_leak_count": 0,
        "learner_visible_exact_duplicate_count": exact_duplicates,
        "learner_visible_normalized_duplicate_count": normalized_duplicates,
        "same_visible_prompt_same_answer_duplicate_count": prompt_answer_duplicates,
        "within_form_exact_duplicate_count": within_form_exact_duplicates,
        "within_form_normalized_duplicate_count": within_form_normalized_duplicates,
        "minimum_distinct_prompts_per_form": min_distinct_prompts_per_form,
        "maximum_same_prompt_count_per_form": max_same_prompt_per_form,
    }
    return acceptance, answer_key_bindings


def render_form_html(form: Mapping[str, Any]) -> str:
    ordinal = int(form.get("form_ordinal", 0))
    activities = list(form.get("activities") or [])
    sections = list(form.get("sections") or [])
    if len(activities) != 40:
        raise Unit04LearnerFacingAcceptanceError(f"RENDER_FORM_COUNT_INVALID:F{ordinal:02d}")
    blocks = []
    position = 0
    for section in sections:
        count = int(section["activity_count"])
        rows = activities[position:position + count]
        cards = "".join(
            u01_pdf._activity_html(activity, position + index)
            for index, activity in enumerate(rows, start=1)
        )
        blocks.append(
            '<section class="unit04-section">'
            + f'<h2>{u01_pdf._safe_text(str(section["section_name"]))}</h2>'
            + cards
            + "</section>"
        )
        position += count
    document = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<title>Unit 4 Form {ordinal:02d}</title></head><body>"
        f"<h1>Unit 4 · Form {ordinal:02d}</h1>"
        f'<p>{u01_pdf._safe_text(str(form.get("progression_stage") or "").replace("_", " ").title())}</p>'
        + "".join(blocks)
        + "</body></html>"
    )
    if document.count('<article class="activity">') != 40:
        raise Unit04LearnerFacingAcceptanceError(f"HTML_ACTIVITY_COUNT_INVALID:F{ordinal:02d}")
    lowered = document.casefold()
    for marker in FORBIDDEN_LEARNER_MARKERS:
        if marker.casefold() in lowered:
            raise Unit04LearnerFacingAcceptanceError(
                f"HTML_ENGINEERING_MARKER_VISIBLE:F{ordinal:02d}:{marker}"
            )
    return document


def build_acceptance_report(source_payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(source_payload or source.build_export_payload())
    _source_contract(payload)
    source_snapshot = _digest(payload)
    runtime_identity = _runtime_identity(payload["runtime_bindings"])
    item_identity = _item_identity(payload["questionbank_items"])
    forms = _project_forms(payload)
    acceptance, answer_key_bindings = _validate_learner_forms(forms, payload)
    rendered = [render_form_html(form) for form in forms]

    if _digest(payload) != source_snapshot:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_PAYLOAD_MUTATED")
    if _runtime_identity(payload["runtime_bindings"]) != runtime_identity:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_RUNTIME_IDENTITY_MUTATED")
    if _item_identity(payload["questionbank_items"]) != item_identity:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_ITEM_IDENTITY_MUTATED")

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "source_task_id": source.TASK_ID,
        "source_status": source.PASS_STATUS,
        "source_q10_validator_reused": source_validator.VALIDATOR_ID,
        "source_snapshot_sha256": source_snapshot,
        "source_runtime_identity_sha256": runtime_identity,
        "source_item_identity_sha256": item_identity,
        "acceptance": acceptance,
        "answer_key_bindings": answer_key_bindings,
        "answer_key_binding_identity_sha256": _digest(answer_key_bindings),
        "learner_forms": forms,
        "html_form_count": len(rendered),
        "html_activity_count": sum(
            html.count('<article class="activity">') for html in rendered
        ),
        "renderer_reuse": (
            "product.a1fs_v1_2_1."
            "u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization._activity_html"
        ),
        "presentation_fixes": {
            "engineering_prompt_projection_count": 800,
            "engineering_stimulus_metadata_suppression_count": 800,
            "progression_support_projection_count": 800,
            "selected_relation_answer_leak_count": 0,
            "at_scene_ref_render_count": 0,
        },
        "claim_boundaries": {
            "source_800_runtime_rows_mutated": False,
            "source_selected_item_identities_mutated": False,
            "source_candidate_identities_mutated": False,
            "source_questionbank_items_mutated": False,
            "q03_mutated": False,
            "q07_mutated": False,
            "q08_mutated": False,
            "q09_mutated": False,
            "q07_q09_r1_repair_mutated": False,
            "q10_redone": False,
            "second_questionbank_authority_created": False,
            "second_selector_created": False,
            "second_renderer_created": False,
            "new_sentence_identity_created": False,
            "new_scene_identity_created": False,
            "pdf_materialized": False,
            "learner_state_mutated": False,
            "scoring_authority_mutated": False,
            "motion_directional_from_into_to_activated": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


if __name__ == "__main__":
    print(json.dumps(build_acceptance_report(), ensure_ascii=False, indent=2))
