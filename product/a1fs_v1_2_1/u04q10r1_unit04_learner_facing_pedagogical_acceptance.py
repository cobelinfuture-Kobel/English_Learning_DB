#!/usr/bin/env python3
"""Unit04 Q10R1 learner-facing pedagogical acceptance over locked Q10 identity."""
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
from ulga.builders import (
    build_a1fs_v1_u04q10_questionbank_form_materialization as source,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only learner-facing acceptance consumer over the approved Unit04 Q10 "
    "20x40 runtime. It preserves all 800 QuestionBank/runtime selected and "
    "candidate identities, suppresses engineering-only metadata from learner "
    "presentation, reuses the accepted Unit01 learner activity HTML renderer, "
    "and creates no new QuestionBank item, selector, sentence, scene, grammar, "
    "scoring, PDF, motion-directional, Unit05, or A2 authority."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U04Q10R1_Unit04LearnerFacingPedagogicalAcceptance"
SCHEMA_VERSION = "a1fs.v1.u04.q10r1.learner_facing_pedagogical_acceptance.v1"
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
    "answerability_basis", "evidence_mode", "evidence_role", "authority",
    "licensed", "admitted", "human-reviewable", "fabricated_scene_ref",
    "q03", "q07", "q08", "q09", "q10",
)
RELATION_CUES = {
    "in": "The thing is within the boundaries of the place or container.",
    "inside": "The thing is within an enclosing container or bounded place.",
    "on": "The thing touches and is supported by a surface.",
    "near": "The thing is a short distance from the landmark.",
    "at": "The person or thing is connected with one general place.",
    "under": "The thing is in a lower position than the landmark.",
    "behind": "The thing is at the back of the landmark.",
    "between": "The thing is in the space separating two different landmarks.",
}
STAGE_PREFIX = {
    "GUIDED": "Use the clue. ",
    "REDUCED_SUPPORT": "Read the context carefully. ",
    "INDEPENDENT": "",
    "TRANSFER": "Use the new context. ",
    "RETENTION": "Remember what you have learned. ",
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
    if payload.get("status") != source.PASS_STATUS:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_STATUS_INVALID")
    if payload.get("next_short_step") != TASK_ID:
        raise Unit04LearnerFacingAcceptanceError(
            f"SOURCE_NEXT_STEP_INVALID:{payload.get('next_short_step')}"
        )
    contract = dict(payload.get("materialization_contract") or {})
    expected = {
        "form_count": FORM_COUNT,
        "questions_per_form": ACTIVITIES_PER_FORM,
        "questionbank_item_count": TOTAL_ACTIVITIES,
        "runtime_occurrence_count": TOTAL_ACTIVITIES,
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
    if coverage.get("task_family_coverage") != "10/10":
        raise Unit04LearnerFacingAcceptanceError("SOURCE_TASK_FAMILY_COVERAGE_INVALID")
    if coverage.get("target_relation_coverage") != "8/8":
        raise Unit04LearnerFacingAcceptanceError("SOURCE_RELATION_COVERAGE_INVALID")
    if coverage.get("communicative_function_coverage") != "6/6":
        raise Unit04LearnerFacingAcceptanceError("SOURCE_FUNCTION_COVERAGE_INVALID")
    if int(coverage.get("exact_semantic_duplicate_count", -1)) != 0:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_SEMANTIC_DUPLICATE_DRIFT")
    if int(coverage.get("at_scene_ref_count", -1)) != 0:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_AT_SCENE_REF_DRIFT")
    if int(coverage.get("fabricated_scene_ref_count", -1)) != 0:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_FABRICATED_SCENE_REF_DRIFT")
    if int(coverage.get("support_relation_item_count", -1)) != 0:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_SUPPORT_RELATION_PROMOTION_DRIFT")
    boundaries = dict(payload.get("boundaries") or {})
    if not boundaries or any(value is not False for value in boundaries.values()):
        raise Unit04LearnerFacingAcceptanceError("SOURCE_BOUNDARY_DRIFT")


def _sentence_case(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text or text.startswith("I "):
        return text
    return text[0].upper() + text[1:]


def _subject(item: Mapping[str, Any]) -> str:
    text = str(item.get("source_sentence_text") or "").strip().rstrip(".?!")
    relation = str(item.get("relation_surface") or "").strip()
    match = re.search(rf"\b{re.escape(relation)}\b", text, flags=re.I) if text and relation else None
    head = text[:match.start()].strip() if match else text
    head = re.sub(r"\b(?:am|is|are)\s*$", "", head, flags=re.I).strip()
    return _sentence_case(head or "the thing")


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
        raise Unit04LearnerFacingAcceptanceError(
            f"RELATION_MASK_FAILED:{item.get('item_id')}:{relation}:{text}"
        )
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
    if relation not in RELATION_CUES:
        raise Unit04LearnerFacingAcceptanceError(f"RELATION_CUE_MISSING:{relation}")
    return RELATION_CUES[relation]


def _prompt(item: Mapping[str, Any]) -> str:
    family = str(item["task_family_id"])
    relation = str(item["relation_surface"])
    cf = str(item["communicative_function_id"])
    stage = str(item["progression_role"])
    if stage not in STAGE_PREFIX:
        raise Unit04LearnerFacingAcceptanceError(f"STAGE_PROMPT_SUPPORT_MISSING:{stage}")
    prefix = STAGE_PREFIX[stage]
    if family == "U04-TF01_RECOGNITION":
        core = "Which place word matches the position clue?"
    elif family == "U04-TF02_MEANING_DISCRIMINATION":
        core = "Which place word best describes the position?"
    elif family == "U04-TF03_FORM_SELECTION":
        core = "Choose the correct place word for the sentence."
    elif family == "U04-TF04_PLACE_PHRASE_CONSTRUCTION":
        core = f"Use {relation} and the place shown to write the complete place phrase."
    elif family == "U04-TF05_ERROR_DETECTION":
        core = "Does the place phrase match the position? Choose MATCHES or DOES NOT MATCH."
    elif family == "U04-TF06_ERROR_CORRECTION":
        core = "Rewrite the place phrase so it matches the position."
    elif family == "U04-TF07_CONTEXT_GAP":
        core = "Write the missing place phrase."
    elif family == "U04-TF08_U01_U02_U03_INTEGRATION":
        core = "Choose the place word that still describes the position."
    elif family == "U04-TF09_PRODUCTIVE_RESPONSE":
        subject = _subject(item)
        if cf == "U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION":
            core = f"Ask a natural question about where {subject} is."
        elif relation == "at":
            core = f"Write one natural sentence saying {subject} is at the park."
        else:
            core = f"Write one complete sentence describing where {subject} is."
    elif family == "U04-TF10_TRANSFER":
        subject = _subject(item)
        if cf == "U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION":
            core = f"Ask a natural question about where {subject} is in this new context."
        elif list(item.get("options") or []):
            core = "Choose the place word that matches the new context."
        else:
            core = f"Write one complete sentence for the new context about {subject}."
    else:
        raise Unit04LearnerFacingAcceptanceError(f"UNSUPPORTED_TASK_FAMILY:{family}")
    return f"{prefix}{core}".strip()


def _stimulus(item: Mapping[str, Any]) -> str:
    family = str(item["task_family_id"])
    relation = str(item["relation_surface"])
    cf = str(item["communicative_function_id"])
    raw = dict(item.get("stimulus") or {})
    cue = _cue(item)
    complement = _complement(item)
    subject = _subject(item)
    if family in {"U04-TF01_RECOGNITION", "U04-TF02_MEANING_DISCRIMINATION", "U04-TF03_FORM_SELECTION"}:
        return f"Context: {_mask_relation_sentence(item)} | Position clue: {cue}"
    if family == "U04-TF05_ERROR_DETECTION":
        candidate = str(raw.get("candidate_place_phrase") or "").strip()
        if not candidate:
            raise Unit04LearnerFacingAcceptanceError(f"CANDIDATE_PHRASE_MISSING:{item.get('item_id')}")
        return f"Place phrase: {candidate} | Position clue: {cue}"
    if family == "U04-TF04_PLACE_PHRASE_CONSTRUCTION":
        return f"Place word: {relation} | Place: {complement}"
    if family == "U04-TF06_ERROR_CORRECTION":
        incorrect = str(raw.get("incorrect_place_phrase") or "").strip()
        if not incorrect:
            raise Unit04LearnerFacingAcceptanceError(f"INCORRECT_PHRASE_MISSING:{item.get('item_id')}")
        return f"Incorrect phrase: {incorrect} | Place: {complement} | Position clue: {cue}"
    if family == "U04-TF07_CONTEXT_GAP":
        return f"Context: {_mask_place_phrase_sentence(item)} | Position clue: {cue}"
    if family == "U04-TF08_U01_U02_U03_INTEGRATION":
        one = str(raw.get("unit01_article_carrier") or "").strip()
        two = str(raw.get("unit02_plural_carrier") or "").strip()
        reference = str(raw.get("unit03_reference_carrier") or "").strip()
        if not one or not two or not reference:
            raise Unit04LearnerFacingAcceptanceError(f"CUMULATIVE_CARRIER_MISSING:{item.get('item_id')}")
        return f"One: {one} | Two: {two} | Reference: {reference} | Position clue: {cue}"
    if family == "U04-TF09_PRODUCTIVE_RESPONSE":
        if cf == "U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION":
            return f"Person or thing: {subject}"
        if relation == "at":
            if item.get("scene_ref_id") is not None:
                raise Unit04LearnerFacingAcceptanceError(f"AT_SCENE_REF_PRESENT:{item.get('item_id')}")
            return f"Subject: {subject} | Place: the park"
        return f"Subject: {subject} | Place or object: {complement} | Position clue: {cue}"
    if family == "U04-TF10_TRANSFER":
        if cf == "U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION":
            return f"Person or thing: {subject} | New context: location question"
        if list(item.get("options") or []):
            return f"Context: {_mask_relation_sentence(item)} | Position clue: {cue}"
        return f"Subject: {subject} | Place or object: {complement} | Position clue: {cue}"
    raise Unit04LearnerFacingAcceptanceError(f"UNSUPPORTED_STIMULUS_FAMILY:{family}")


def _learner_activity(number: int, item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "question_number": f"Q{number:02d}",
        "skill": "Grammar",
        "stimulus": _stimulus(item),
        "prompt": _prompt(item),
        "options": [str(value) for value in item.get("options") or []],
        "response_mode": "select_one" if list(item.get("options") or []) else "short_text",
        "capture_enabled": True,
        "practice_only": False,
    }


def _assert_no_engineering_markers(activity: Mapping[str, Any], form_number: int, question_number: int) -> None:
    text = " ".join([
        str(activity.get("stimulus") or ""), str(activity.get("prompt") or ""),
        " ".join(str(value) for value in activity.get("options") or []),
    ]).casefold()
    for marker in FORBIDDEN_LEARNER_MARKERS:
        if marker.casefold() in text:
            raise Unit04LearnerFacingAcceptanceError(
                f"ENGINEERING_MARKER_VISIBLE:F{form_number:02d}:Q{question_number:02d}:{marker}"
            )


def _project_forms(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = list(payload.get("questionbank_items") or [])
    runtime = list(payload.get("runtime_bindings") or [])
    source_forms = list(payload.get("forms") or [])
    if len(items) != TOTAL_ACTIVITIES or len(runtime) != TOTAL_ACTIVITIES or len(source_forms) != FORM_COUNT:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_DENOMINATOR_INVALID")
    item_index = {str(row["item_id"]): row for row in items}
    runtime_index = {str(row["selected_item_id"]): row for row in runtime}
    if len(item_index) != TOTAL_ACTIVITIES or len(runtime_index) != TOTAL_ACTIVITIES:
        raise Unit04LearnerFacingAcceptanceError("SOURCE_SELECTED_IDENTITY_COLLISION")
    forms = []
    for form_number in range(1, FORM_COUNT + 1):
        source_form = source_forms[form_number - 1]
        if int(source_form.get("form_number", -1)) != form_number:
            raise Unit04LearnerFacingAcceptanceError(f"SOURCE_FORM_SEQUENCE_INVALID:F{form_number:02d}")
        activities = []
        sections = []
        section_item_ids = dict(source_form.get("section_item_ids") or {})
        for section in SECTION_ORDER:
            ids = [str(value) for value in section_item_ids.get(section) or []]
            if len(ids) != SECTION_COUNTS[section]:
                raise Unit04LearnerFacingAcceptanceError(f"SOURCE_SECTION_COUNT_INVALID:F{form_number:02d}:{section}")
            for item_id in ids:
                item = item_index.get(item_id)
                runtime_row = runtime_index.get(item_id)
                if item is None or runtime_row is None:
                    raise Unit04LearnerFacingAcceptanceError(f"SOURCE_SELECTED_ITEM_UNRESOLVED:{item_id}")
                if int(item.get("form_number", -1)) != form_number or str(item.get("section") or "") != section:
                    raise Unit04LearnerFacingAcceptanceError(f"ITEM_SCOPE_DRIFT:{item_id}")
                if int(runtime_row.get("form_number", -1)) != form_number or str(runtime_row.get("section") or "") != section:
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
            "section_count": len(SECTION_ORDER),
            "learner_visible_activity_count": len(activities),
            "sections": sections,
            "activities": activities,
        }
        u01_learner._assert_no_answer_leak(form)
        forms.append(form)
    return forms


def _word_present(text: str, value: str) -> bool:
    return re.search(rf"\b{re.escape(value)}\b", text, flags=re.I) is not None


def _validate_learner_forms(forms: Sequence[Mapping[str, Any]], payload: Mapping[str, Any]) -> dict[str, Any]:
    if len(forms) != FORM_COUNT:
        raise Unit04LearnerFacingAcceptanceError(f"FORM_COUNT_INVALID:{len(forms)}")
    items = {str(row["item_id"]): row for row in payload["questionbank_items"]}
    source_forms = list(payload["forms"])
    stage_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    function_counts: Counter[str] = Counter()
    response_counts: Counter[str] = Counter()
    rendered = 0
    at_count = 0
    answer_leaks = 0
    for form_number, form in enumerate(forms, start=1):
        if int(form.get("form_ordinal", -1)) != form_number:
            raise Unit04LearnerFacingAcceptanceError(f"FORM_SEQUENCE_INVALID:{form_number}")
        if int(form.get("learner_visible_activity_count", -1)) != ACTIVITIES_PER_FORM:
            raise Unit04LearnerFacingAcceptanceError(f"ACTIVITY_COUNT_INVALID:F{form_number:02d}")
        sections = list(form.get("sections") or [])
        if [str(row.get("section") or "") for row in sections] != list(SECTION_ORDER):
            raise Unit04LearnerFacingAcceptanceError(f"SECTION_ORDER_INVALID:F{form_number:02d}")
        if {str(row["section"]): int(row["activity_count"]) for row in sections} != SECTION_COUNTS:
            raise Unit04LearnerFacingAcceptanceError(f"SECTION_DENOMINATOR_INVALID:F{form_number:02d}")
        activities = list(form.get("activities") or [])
        stage_counts[str(form.get("progression_stage") or "")] += len(activities)
        source_ids = [str(value) for value in source_forms[form_number - 1]["item_ids"]]
        for question_number, (activity, item_id) in enumerate(zip(activities, source_ids), start=1):
            item = items[item_id]
            if activity.get("question_number") != f"Q{question_number:02d}":
                raise Unit04LearnerFacingAcceptanceError(f"QUESTION_SEQUENCE_INVALID:F{form_number:02d}:Q{question_number:02d}")
            if not str(activity.get("prompt") or "").strip() or not str(activity.get("stimulus") or "").strip():
                raise Unit04LearnerFacingAcceptanceError(f"LEARNER_TEXT_MISSING:{item_id}")
            mode = str(activity.get("response_mode") or "")
            if mode not in ALLOWED_RESPONSE_MODES:
                raise Unit04LearnerFacingAcceptanceError(f"RESPONSE_MODE_INVALID:{item_id}:{mode}")
            response_counts[mode] += 1
            source_options = [str(value) for value in item.get("options") or []]
            learner_options = [str(value) for value in activity.get("options") or []]
            if learner_options != source_options or len(learner_options) != len(set(learner_options)):
                raise Unit04LearnerFacingAcceptanceError(f"OPTION_IDENTITY_INVALID:{item_id}")
            if learner_options:
                if str(item.get("correct_answer") or "") not in learner_options or mode != "select_one":
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
                if item.get("scene_ref_id") is not None or family not in source.AT_ALLOWED_FAMILIES or cf != source.AT_CF or learner_options:
                    raise Unit04LearnerFacingAcceptanceError(f"AT_ROUTE_INVALID:{item_id}")
            selected_relation = family in SELECTED_RELATION_FAMILIES or (family == "U04-TF10_TRANSFER" and bool(learner_options))
            if selected_relation and _word_present(str(activity["stimulus"]) + " " + str(activity["prompt"]), relation):
                answer_leaks += 1
            if family == "U04-TF07_CONTEXT_GAP" and "___" not in str(activity["stimulus"]):
                raise Unit04LearnerFacingAcceptanceError(f"CONTEXT_GAP_NOT_VISIBLE:{item_id}")
            if family == "U04-TF08_U01_U02_U03_INTEGRATION":
                text = str(activity["stimulus"])
                if any(marker not in text for marker in ("One:", "Two:", "Reference:", "Position clue:")):
                    raise Unit04LearnerFacingAcceptanceError(f"CUMULATIVE_CARRIER_NOT_VISIBLE:{item_id}")
            _assert_no_engineering_markers(activity, form_number, question_number)
            u01_pdf._activity_html(activity, question_number)
            rendered += 1
        u01_learner._assert_no_answer_leak(form)
    expected_stage_counts = {"GUIDED": 160, "REDUCED_SUPPORT": 160, "INDEPENDENT": 160, "TRANSFER": 160, "RETENTION": 160}
    if dict(stage_counts) != expected_stage_counts:
        raise Unit04LearnerFacingAcceptanceError(f"STAGE_ACTIVITY_COUNTS_INVALID:{dict(stage_counts)}")
    if answer_leaks:
        raise Unit04LearnerFacingAcceptanceError(f"SELECTED_RELATION_ANSWER_LEAKS:{answer_leaks}")
    if set(family_counts) != set(source._families()):
        raise Unit04LearnerFacingAcceptanceError("LEARNER_TASK_FAMILY_COVERAGE_INVALID")
    if set(relation_counts) != set(source.TARGET_RELATIONS):
        raise Unit04LearnerFacingAcceptanceError("LEARNER_RELATION_COVERAGE_INVALID")
    q08_ids = {str(row["function_id"]) for row in source._sources()["q08"]["communicative_functions"]}
    if set(function_counts) != q08_ids:
        raise Unit04LearnerFacingAcceptanceError("LEARNER_FUNCTION_COVERAGE_INVALID")
    if at_count != 40 or rendered != TOTAL_ACTIVITIES:
        raise Unit04LearnerFacingAcceptanceError(f"LEARNER_DENOMINATOR_DRIFT:AT={at_count}:RENDERED={rendered}")
    return {
        "form_count": FORM_COUNT,
        "activity_count": TOTAL_ACTIVITIES,
        "rendered_activity_count": rendered,
        "stage_activity_counts": dict(stage_counts),
        "response_mode_counts": dict(response_counts),
        "task_family_coverage": "10/10",
        "target_relation_coverage": "8/8",
        "communicative_function_coverage": "6/6",
        "at_text_bound_activity_count": at_count,
        "at_scene_ref_render_count": 0,
        "selected_relation_answer_leak_count": 0,
    }


def render_form_html(form: Mapping[str, Any]) -> str:
    ordinal = int(form.get("form_ordinal", 0))
    activities = list(form.get("activities") or [])
    sections = list(form.get("sections") or [])
    if len(activities) != ACTIVITIES_PER_FORM:
        raise Unit04LearnerFacingAcceptanceError(f"RENDER_FORM_COUNT_INVALID:F{ordinal:02d}")
    blocks = []
    position = 0
    for section in sections:
        count = int(section["activity_count"])
        rows = activities[position:position + count]
        cards = "".join(
            u01_pdf._activity_html(activity, position + local_index)
            for local_index, activity in enumerate(rows, start=1)
        )
        blocks.append(
            '<section class="unit04-section">'
            f'<h2>{u01_pdf._safe_text(str(section["section_name"]))}</h2>'
            f'{cards}</section>'
        )
        position += count
    document = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f'<title>Unit 4 Form {ordinal:02d}</title></head><body>'
        f'<h1>Unit 4 · Form {ordinal:02d}</h1>'
        f'<p>{u01_pdf._safe_text(str(form.get("progression_stage") or "").replace("_", " ").title())}</p>'
        + "".join(blocks) + '</body></html>'
    )
    if document.count('<article class="activity">') != ACTIVITIES_PER_FORM:
        raise Unit04LearnerFacingAcceptanceError(f"HTML_ACTIVITY_COUNT_INVALID:F{ordinal:02d}")
    lowered = document.casefold()
    for marker in FORBIDDEN_LEARNER_MARKERS:
        if marker.casefold() in lowered:
            raise Unit04LearnerFacingAcceptanceError(f"HTML_ENGINEERING_MARKER_VISIBLE:F{ordinal:02d}:{marker}")
    return document


def build_acceptance_report(source_payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(source_payload or source.build_export_payload())
    _source_contract(payload)
    source_snapshot = _digest(payload)
    runtime_identity = _runtime_identity(payload["runtime_bindings"])
    item_identity = _item_identity(payload["questionbank_items"])
    forms = _project_forms(payload)
    acceptance = _validate_learner_forms(forms, payload)
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
        "source_snapshot_sha256": source_snapshot,
        "source_runtime_identity_sha256": runtime_identity,
        "source_item_identity_sha256": item_identity,
        "acceptance": acceptance,
        "learner_forms": forms,
        "html_form_count": len(rendered),
        "html_activity_count": sum(html.count('<article class="activity">') for html in rendered),
        "renderer_reuse": "product.a1fs_v1_2_1.u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization._activity_html",
        "presentation_fixes": {
            "engineering_prompt_projection_count": TOTAL_ACTIVITIES,
            "engineering_stimulus_metadata_suppression_count": TOTAL_ACTIVITIES,
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
