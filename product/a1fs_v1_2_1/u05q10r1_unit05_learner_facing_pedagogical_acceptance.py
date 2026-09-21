#!/usr/bin/env python3
"""Unit05 Q10R1 learner-facing pedagogical acceptance.

Consumes the exact approved Unit05 Q10 20x40 runtime and projects learner-safe
activities without changing QuestionBank/runtime/candidate/source identities.
Unit04 is an architectural comparison/alignment reference only; no Unit04
content authority, sentence, scene, function, task or learner item is consumed.
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
from ulga.builders import build_a1fs_v1_u05q10_questionbank_form_materialization as source
from ulga.validators import (
    validate_a1fs_v1_u05q10_questionbank_form_materialization as source_validator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only learner-facing acceptance consumer over the approved Unit05 Q10 "
    "20x40 runtime. It preserves all Q10 source/runtime/candidate identities, "
    "projects only learner-visible presentation, reuses the existing generic "
    "learner activity renderer, and creates no new grammar, vocabulary, sentence, "
    "scene, communicative-function, selector, scoring, Reader360, PDF, Unit06, "
    "A2 or A2+ authority. Unit04 is comparison/alignment evidence only and is "
    "not a Unit05 content source."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U05Q10R1_Unit05LearnerFacingPedagogicalAcceptance"
SCHEMA_VERSION = "a1fs.v1.u05.q10r1.learner_facing_pedagogical_acceptance.v1"
PASS_STATUS = "PASS_A1FS_V1_U05Q10R1_LEARNER_FACING_PEDAGOGICAL_ACCEPTANCE"
NEXT_SHORT_STEP = "A1FS-V1-U05Q10R2_Unit05LearnerPDFMaterializationAndVisualAcceptance"

FORM_COUNT = 20
ACTIVITIES_PER_FORM = 40
TOTAL_ACTIVITIES = 800
SECTION_ORDER = ("A", "B", "C", "D", "E")
SECTION_COUNTS = {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
SECTION_TITLES = {
    "A": "Choose the be form",
    "B": "Understand the meaning",
    "C": "Build and fix be sentences",
    "D": "Use be in context",
    "E": "Write and use what you know",
}
STAGE_VISIBLE_MARKERS = {
    "GUIDED": "Help:",
    "REDUCED_SUPPORT": "Clue:",
    "INDEPENDENT": "Evidence:",
    "TRANSFER": "New situation:",
    "RETENTION": "Review:",
}
STAGE_SUPPORT_LEVEL = {
    "GUIDED": "HIGH",
    "REDUCED_SUPPORT": "MEDIUM",
    "INDEPENDENT": "LOW",
    "TRANSFER": "MINIMAL",
    "RETENTION": "CUMULATIVE",
}
FORBIDDEN_LEARNER_MARKERS = (
    "scene_ref_id",
    "q06_identity",
    "source_scene_ref",
    "selected_item_id",
    "candidate_ids",
    "slot_id",
    "questionbank_item",
    "semantic_signature",
    "response_contract",
    "correct_answer",
    "answerability_basis",
    "evidence_mode",
    "source_claim",
    "human_review",
    "licensed",
    "admitted",
    "authority",
    "a1fs-v1",
    "a1fs_v1",
    "u05-tf",
    "u05-cf",
    "u05q10",
    "u05_q10",
    "pass_a1fs",
)
MEANING_OPTIONS = {
    "IDENTITY_OR_CATEGORY": "who or what it is",
    "DESCRIPTION_OR_STATE": "what it is like or how it feels",
    "STATIC_LOCATION": "where it is",
}
POLARITY_OPTIONS = {
    "AFFIRMATIVE": "It says the idea is true.",
    "NEGATIVE": "It says the idea is not true.",
}


class Unit05LearnerFacingAcceptanceError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _normalize_visible(value: Any) -> str:
    text = str(value or "").casefold()
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip()


def _runtime_identity(runtime: Sequence[Mapping[str, Any]]) -> str:
    return _digest([
        {
            "slot_id": row["slot_id"],
            "form_number": row["form_number"],
            "section": row["section"],
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
            "item_semantic_signature": row["item_semantic_signature"],
            "form_number": row["form_number"],
            "section": row["section"],
            "task_family_id": row["task_family_id"],
            "communicative_function_id": row["communicative_function_id"],
            "frame_id": row["frame_id"],
            "q06_identity": row["q06_identity"],
        }
        for row in items
    ])


def _source_contract(payload: Mapping[str, Any]) -> None:
    source_validator.validate_payload(payload)
    if payload.get("status") != source.PASS_STATUS:
        raise Unit05LearnerFacingAcceptanceError("SOURCE_STATUS_INVALID")
    if payload.get("next_short_step") != TASK_ID:
        raise Unit05LearnerFacingAcceptanceError("SOURCE_NEXT_STEP_INVALID")
    contract = dict(payload.get("materialization_contract") or {})
    expected = {
        "form_count": 20,
        "questions_per_form": 40,
        "questionbank_item_count": 800,
        "runtime_occurrence_count": 800,
        "candidate_count_per_slot": 3,
        "section_counts_per_form": SECTION_COUNTS,
        "task_family_count": 10,
        "communicative_function_count": 7,
        "frame_count": 6,
        "subject_class_count": 9,
        "polarity_count": 2,
        "complement_class_count": 3,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            raise Unit05LearnerFacingAcceptanceError(
                f"SOURCE_CONTRACT_DRIFT:{key}:{contract.get(key)}:{value}"
            )
    coverage = dict(payload.get("coverage") or {})
    expected_coverage = {
        "task_family_coverage": "10/10",
        "communicative_function_coverage": "7/7",
        "frame_coverage": "6/6",
        "subject_class_coverage": "9/9",
        "polarity_coverage": "2/2",
        "complement_class_coverage": "3/3",
        "context_required_unbound_item_count": 0,
        "standalone_item_forced_scene_count": 0,
    }
    for key, value in expected_coverage.items():
        if coverage.get(key) != value:
            raise Unit05LearnerFacingAcceptanceError(
                f"SOURCE_COVERAGE_DRIFT:{key}:{coverage.get(key)}:{value}"
            )


def _frame_base(item: Mapping[str, Any]) -> str:
    frame = str(item["frame_id"])
    if "-NP-" in frame:
        return "NP"
    if "-ADJ-" in frame:
        return "ADJ"
    if "-PLACE-" in frame:
        return "PLACE"
    raise Unit05LearnerFacingAcceptanceError(f"FRAME_BASE_UNRESOLVED:{frame}")


def _sentence_gap(item: Mapping[str, Any]) -> str:
    subject = str(item["subject_surface"])
    complement = str(item["complement_surface"])
    subject = subject[:1].upper() + subject[1:] if subject else subject
    return f"{subject} ___ {complement}."


def _referent_clue(item: Mapping[str, Any], scene_index: Mapping[str, Mapping[str, Any]]) -> str:
    scene_ref = item.get("scene_ref_id")
    if not scene_ref:
        return ""
    scene = scene_index.get(str(scene_ref))
    if scene is None:
        raise Unit05LearnerFacingAcceptanceError(
            f"SCENE_REFERENCE_UNRESOLVED:{item.get('item_id')}:{scene_ref}"
        )
    ref = dict(scene.get("referent_binding_spec") or {})
    if not ref.get("required"):
        return ""
    label = str(ref.get("anchor_label") or "").strip()
    if not label:
        raise Unit05LearnerFacingAcceptanceError(
            f"REFERENT_LABEL_MISSING:{item.get('item_id')}"
        )
    subject_class = str(item["subject_class"])
    if subject_class == "he":
        return f"Person: {label}."
    if subject_class == "she":
        return f"Person: {label}."
    if subject_class == "it":
        return "Referent: the item shown."
    if subject_class == "they":
        return "Referent: the group shown."
    return ""


def _truth_clue(item: Mapping[str, Any]) -> str:
    base = _frame_base(item)
    polarity = str(item["polarity"])
    if base == "NP" and polarity == "AFFIRMATIVE":
        return "Scene fact: the person or thing matches the role or kind shown."
    if base == "NP":
        return "Scene fact: the person or thing has a different role or kind."
    if base == "ADJ" and polarity == "AFFIRMATIVE":
        return "Scene fact: the description or state matches."
    if base == "ADJ":
        return "Scene fact: the scene shows a different description or state."
    if base == "PLACE" and polarity == "AFFIRMATIVE":
        return "Scene fact: the shown location matches the place phrase."
    return "Scene fact: the subject is clearly in a different location."


def _stage_support(item: Mapping[str, Any], scene_index: Mapping[str, Mapping[str, Any]]) -> str:
    stage = str(item["progression_role"])
    marker = STAGE_VISIBLE_MARKERS.get(stage)
    if marker is None:
        raise Unit05LearnerFacingAcceptanceError(f"STAGE_INVALID:{stage}")
    base = _frame_base(item)
    meaning = {
        "NP": "who or what someone or something is",
        "ADJ": "what someone or something is like or how it feels",
        "PLACE": "where someone or something is",
    }[base]
    if stage == "GUIDED":
        body = f"Use the subject and the meaning clue: {meaning}."
    elif stage == "REDUCED_SUPPORT":
        body = f"Use the subject and the {base.lower()} meaning."
    elif stage == "INDEPENDENT":
        body = _truth_clue(item) if item["requires_context_binding"] else "Use the sentence information."
    elif stage == "TRANSFER":
        body = "Apply the same present-be pattern to this new example."
    elif stage == "RETENTION":
        body = "Keep the earlier article, plural, pronoun or place knowledge and focus on present be."
    else:
        raise Unit05LearnerFacingAcceptanceError(f"STAGE_INVALID:{stage}")
    referent = _referent_clue(item, scene_index)
    return f"{marker} {referent + ' ' if referent else ''}{body}".strip()


def _prompt(item: Mapping[str, Any]) -> str:
    family = str(item["task_family_id"])
    cf = str(item["communicative_function_id"])
    if family == "U05-TF01_BE_FORM_RECOGNITION":
        return "Choose the present-be form that completes the sentence."
    if family == "U05-TF02_SUBJECT_BE_AGREEMENT_SELECTION":
        return "Choose the be form that agrees with the subject."
    if family == "U05-TF03_COMPLEMENT_MEANING_DISCRIMINATION":
        return "What does the part after be tell you?"
    if family == "U05-TF04_AFFIRMATIVE_NEGATIVE_INTERPRETATION":
        return "Does the sentence say the idea is true or not true?"
    if family == "U05-TF05_SENTENCE_CONSTRUCTION":
        return "Write one complete present-be sentence from the information."
    if family == "U05-TF06_ERROR_DETECTION_AND_CORRECTION":
        return "Fix the be form. Write the correct sentence."
    if family == "U05-TF07_CONTEXT_GAP":
        return "Use the context to complete the sentence with the correct present-be meaning."
    if family == "U05-TF08_U01_U04_CUMULATIVE_INTEGRATION":
        return "Keep the earlier-unit words unchanged and choose the present-be form."
    if family == "U05-TF09_PRODUCTIVE_RESPONSE":
        if cf == "U05-CF05_REQUEST_BASIC_BE_INFORMATION":
            return "Ask for the missing information using a question pattern you already know."
        return "Write one complete present-be sentence that matches the information."
    if family == "U05-TF10_TRANSFER":
        if cf == "U05-CF05_REQUEST_BASIC_BE_INFORMATION":
            return "In this new situation, ask for the needed information using a question pattern you already know."
        return "Use present be to write one sentence for this new situation."
    raise Unit05LearnerFacingAcceptanceError(f"TASK_FAMILY_UNSUPPORTED:{family}")


def _project_options(item: Mapping[str, Any]) -> tuple[list[str], Any]:
    options = [str(value) for value in item.get("options") or []]
    correct = item.get("correct_answer")
    family = str(item["task_family_id"])
    if family == "U05-TF03_COMPLEMENT_MEANING_DISCRIMINATION":
        projected = [MEANING_OPTIONS[value] for value in options]
        return projected, MEANING_OPTIONS[str(correct)]
    if family == "U05-TF04_AFFIRMATIVE_NEGATIVE_INTERPRETATION":
        projected = [POLARITY_OPTIONS[value] for value in options]
        return projected, POLARITY_OPTIONS[str(correct)]
    return options, correct


def _stimulus(item: Mapping[str, Any], scene_index: Mapping[str, Mapping[str, Any]]) -> str:
    family = str(item["task_family_id"])
    support = _stage_support(item, scene_index)
    gap = _sentence_gap(item)
    raw = dict(item.get("stimulus") or {})
    subject = str(item["subject_surface"])
    complement = str(item["complement_surface"])
    polarity = str(item["polarity"]).lower()

    if family in {"U05-TF01_BE_FORM_RECOGNITION", "U05-TF02_SUBJECT_BE_AGREEMENT_SELECTION"}:
        return f"{support} Sentence: {gap}"

    if family == "U05-TF03_COMPLEMENT_MEANING_DISCRIMINATION":
        sentence = str(raw.get("sentence_text") or "").strip()
        if not sentence:
            raise Unit05LearnerFacingAcceptanceError(f"MEANING_SENTENCE_MISSING:{item.get('item_id')}")
        return f"{support} Sentence: {sentence}"

    if family == "U05-TF04_AFFIRMATIVE_NEGATIVE_INTERPRETATION":
        sentence = str(raw.get("sentence_text") or "").strip()
        if not sentence:
            raise Unit05LearnerFacingAcceptanceError(f"POLARITY_SENTENCE_MISSING:{item.get('item_id')}")
        return f"{support} Sentence: {sentence}"

    if family == "U05-TF05_SENTENCE_CONSTRUCTION":
        return (
            f"{support} Subject: {subject}. Meaning: {complement}. "
            f"Make a {polarity} sentence."
        )

    if family == "U05-TF06_ERROR_DETECTION_AND_CORRECTION":
        incorrect = str(raw.get("incorrect_sentence") or "").strip()
        if not incorrect:
            raise Unit05LearnerFacingAcceptanceError(f"INCORRECT_SENTENCE_MISSING:{item.get('item_id')}")
        return f"{support} Sentence to fix: {incorrect}"

    if family == "U05-TF07_CONTEXT_GAP":
        if item.get("scene_ref_id") is None:
            raise Unit05LearnerFacingAcceptanceError(f"TF07_SCENE_REQUIRED:{item.get('item_id')}")
        return f"{support} {_truth_clue(item)} Sentence: {gap}"

    if family == "U05-TF08_U01_U04_CUMULATIVE_INTEGRATION":
        sentence = str(raw.get("sentence_without_be") or gap).strip()
        return f"{support} Review sentence: {sentence}"

    if family == "U05-TF09_PRODUCTIVE_RESPONSE":
        if item["communicative_function_id"] == "U05-CF05_REQUEST_BASIC_BE_INFORMATION":
            return f"{support} Topic: {subject}. Find out about {complement}."
        return f"{support} Subject: {subject}. Meaning: {complement}. Polarity: {polarity}."

    if family == "U05-TF10_TRANSFER":
        if item["communicative_function_id"] == "U05-CF05_REQUEST_BASIC_BE_INFORMATION":
            return f"{support} New topic: {subject}. Find out about {complement}."
        return f"{support} New subject: {subject}. Meaning: {complement}. Polarity: {polarity}."

    raise Unit05LearnerFacingAcceptanceError(f"STIMULUS_FAMILY_UNSUPPORTED:{family}")


def _learner_activity(
    number: int,
    item: Mapping[str, Any],
    scene_index: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    options, projected_correct = _project_options(item)
    activity = {
        "question_number": f"Q{number:02d}",
        "skill": "Grammar",
        "stimulus": _stimulus(item, scene_index),
        "prompt": _prompt(item),
        "options": options,
        "response_mode": "select_one" if options else "short_text",
        "capture_enabled": True,
        "practice_only": False,
    }
    answer_binding = {
        "question_number": f"Q{number:02d}",
        "source_item_id": str(item["item_id"]),
        "task_family_id": str(item["task_family_id"]),
        "response_mode": activity["response_mode"],
        "reference_answer": projected_correct,
        "source_scoring_mode": str(item["response_contract"]["scoring_mode"]),
        "reference_response_nonexclusive": bool(
            item["response_contract"].get("reference_response_nonexclusive")
        ),
    }
    return activity, answer_binding


def _assert_no_engineering_markers(
    activity: Mapping[str, Any],
    form_number: int,
    question_number: int,
) -> None:
    text = " ".join((
        str(activity.get("stimulus") or ""),
        str(activity.get("prompt") or ""),
        " ".join(str(value) for value in activity.get("options") or []),
    )).casefold()
    for marker in FORBIDDEN_LEARNER_MARKERS:
        if marker.casefold() in text:
            raise Unit05LearnerFacingAcceptanceError(
                f"ENGINEERING_MARKER_VISIBLE:F{form_number:02d}:Q{question_number:02d}:{marker}"
            )


def _project_forms(payload: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items = list(payload.get("questionbank_items") or [])
    runtime = list(payload.get("runtime_bindings") or [])
    source_forms = list(payload.get("forms") or [])
    if (len(items), len(runtime), len(source_forms)) != (800, 800, 20):
        raise Unit05LearnerFacingAcceptanceError("SOURCE_DENOMINATOR_INVALID")

    src = source._sources()
    scene_index = {
        str(row["scene_ref_id"]): row for row in src["q07"]["micro_scenes"]
    }
    item_index = {str(row["item_id"]): row for row in items}
    runtime_index = {str(row["selected_item_id"]): row for row in runtime}
    if len(item_index) != 800 or len(runtime_index) != 800:
        raise Unit05LearnerFacingAcceptanceError("SOURCE_SELECTED_IDENTITY_COLLISION")

    forms: list[dict[str, Any]] = []
    answer_bindings: list[dict[str, Any]] = []
    for form_number in range(1, 21):
        source_form = source_forms[form_number - 1]
        if int(source_form.get("form_number", -1)) != form_number:
            raise Unit05LearnerFacingAcceptanceError(
                f"SOURCE_FORM_SEQUENCE_INVALID:F{form_number:02d}"
            )
        ordered_ids = [str(value) for value in source_form.get("item_ids") or []]
        if len(ordered_ids) != 40:
            raise Unit05LearnerFacingAcceptanceError(
                f"SOURCE_FORM_ITEM_COUNT_INVALID:F{form_number:02d}"
            )
        activities: list[dict[str, Any]] = []
        sections: list[dict[str, Any]] = []
        for section in SECTION_ORDER:
            section_ids = [
                item_id for item_id in ordered_ids
                if str(item_index[item_id]["section"]) == section
            ]
            if len(section_ids) != SECTION_COUNTS[section]:
                raise Unit05LearnerFacingAcceptanceError(
                    f"SOURCE_SECTION_COUNT_INVALID:F{form_number:02d}:{section}"
                )
            for item_id in section_ids:
                item = item_index[item_id]
                runtime_row = runtime_index.get(item_id)
                if runtime_row is None:
                    raise Unit05LearnerFacingAcceptanceError(
                        f"SOURCE_RUNTIME_ITEM_UNRESOLVED:{item_id}"
                    )
                if int(item["form_number"]) != form_number or str(item["section"]) != section:
                    raise Unit05LearnerFacingAcceptanceError(f"ITEM_SCOPE_DRIFT:{item_id}")
                if int(runtime_row["form_number"]) != form_number or str(runtime_row["section"]) != section:
                    raise Unit05LearnerFacingAcceptanceError(f"RUNTIME_SCOPE_DRIFT:{item_id}")
                activity, answer = _learner_activity(
                    len(activities) + 1,
                    item,
                    scene_index,
                )
                _assert_no_engineering_markers(
                    activity,
                    form_number,
                    len(activities) + 1,
                )
                activities.append(activity)
                answer_bindings.append({
                    "form_number": form_number,
                    **answer,
                })
            sections.append({
                "section": section,
                "section_name": SECTION_TITLES[section],
                "activity_count": SECTION_COUNTS[section],
            })
        form = {
            "unit_id": source.UNIT_ID,
            "unit_ordinal": 5,
            "form_id": f"U05Q10R1-F{form_number:02d}",
            "form_ordinal": form_number,
            "progression_stage": str(source_form["progression_role"]),
            "section_count": 5,
            "learner_visible_activity_count": 40,
            "sections": sections,
            "activities": activities,
        }
        u01_learner._assert_no_answer_leak(form)
        forms.append(form)
    return forms, answer_bindings


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


def _validate_learner_forms(
    forms: Sequence[Mapping[str, Any]],
    answer_bindings: Sequence[Mapping[str, Any]],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if len(forms) != 20:
        raise Unit05LearnerFacingAcceptanceError("FORM_COUNT_INVALID")
    if len(answer_bindings) != 800:
        raise Unit05LearnerFacingAcceptanceError("ANSWER_BINDING_COUNT_INVALID")
    items = {str(row["item_id"]): row for row in payload["questionbank_items"]}
    all_exact: list[str] = []
    all_normalized: list[str] = []
    within_exact = 0
    within_normalized = 0
    minimum_distinct_prompts = 999
    maximum_same_prompt = 0
    stage_counts: Counter[str] = Counter()
    stage_visible_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    function_counts: Counter[str] = Counter()
    frame_counts: Counter[str] = Counter()
    subject_counts: Counter[str] = Counter()
    context_bound = 0
    standalone = 0

    for form in forms:
        ordinal = int(form["form_ordinal"])
        activities = list(form["activities"])
        if len(activities) != 40:
            raise Unit05LearnerFacingAcceptanceError(
                f"FORM_ACTIVITY_COUNT_INVALID:F{ordinal:02d}"
            )
        stage = str(form["progression_stage"])
        marker = STAGE_VISIBLE_MARKERS[stage]
        exact = [_canonical(_visible_payload(row, normalized=False)) for row in activities]
        normalized = [_canonical(_visible_payload(row, normalized=True)) for row in activities]
        within_exact += _duplicate_excess(exact)
        within_normalized += _duplicate_excess(normalized)
        all_exact.extend(exact)
        all_normalized.extend(normalized)
        prompts = [str(row["prompt"]) for row in activities]
        minimum_distinct_prompts = min(minimum_distinct_prompts, len(set(prompts)))
        maximum_same_prompt = max(
            maximum_same_prompt,
            max(Counter(prompts).values()),
        )
        stage_counts[stage] += len(activities)
        stage_visible_counts[stage] += sum(
            1 for row in activities if marker in str(row["stimulus"])
        )

        source_form = payload["forms"][ordinal - 1]
        for item_id in source_form["item_ids"]:
            item = items[str(item_id)]
            family_counts[str(item["task_family_id"])] += 1
            function_counts[str(item["communicative_function_id"])] += 1
            frame_counts[str(item["frame_id"])] += 1
            subject_counts[str(item["subject_class"])] += 1
            if item["requires_context_binding"]:
                context_bound += 1
            else:
                standalone += 1

    if within_exact != 0 or within_normalized != 0:
        raise Unit05LearnerFacingAcceptanceError(
            f"WITHIN_FORM_VISIBLE_DUPLICATION:{within_exact}:{within_normalized}"
        )
    if minimum_distinct_prompts < 8:
        raise Unit05LearnerFacingAcceptanceError(
            f"PROMPT_VARIETY_TOO_LOW:{minimum_distinct_prompts}"
        )
    if set(family_counts) != {
        "U05-TF01_BE_FORM_RECOGNITION",
        "U05-TF02_SUBJECT_BE_AGREEMENT_SELECTION",
        "U05-TF03_COMPLEMENT_MEANING_DISCRIMINATION",
        "U05-TF04_AFFIRMATIVE_NEGATIVE_INTERPRETATION",
        "U05-TF05_SENTENCE_CONSTRUCTION",
        "U05-TF06_ERROR_DETECTION_AND_CORRECTION",
        "U05-TF07_CONTEXT_GAP",
        "U05-TF08_U01_U04_CUMULATIVE_INTEGRATION",
        "U05-TF09_PRODUCTIVE_RESPONSE",
        "U05-TF10_TRANSFER",
    }:
        raise Unit05LearnerFacingAcceptanceError("TASK_FAMILY_LEARNER_COVERAGE_INVALID")
    if len(function_counts) != 7:
        raise Unit05LearnerFacingAcceptanceError("FUNCTION_LEARNER_COVERAGE_INVALID")
    if len(frame_counts) != 6:
        raise Unit05LearnerFacingAcceptanceError("FRAME_LEARNER_COVERAGE_INVALID")
    if len(subject_counts) != 9:
        raise Unit05LearnerFacingAcceptanceError("SUBJECT_LEARNER_COVERAGE_INVALID")

    selected_response_count = sum(
        1 for form in forms for row in form["activities"]
        if row["response_mode"] == "select_one"
    )
    short_text_count = TOTAL_ACTIVITIES - selected_response_count

    return {
        "form_count": 20,
        "activity_count": 800,
        "answer_key_binding_count": 800,
        "task_family_coverage": "10/10",
        "communicative_function_coverage": "7/7",
        "frame_coverage": "6/6",
        "subject_class_coverage": "9/9",
        "stage_activity_counts": dict(sorted(stage_counts.items())),
        "stage_support_levels": STAGE_SUPPORT_LEVEL,
        "stage_visible_support_counts": dict(sorted(stage_visible_counts.items())),
        "context_bound_activity_count": context_bound,
        "standalone_activity_count": standalone,
        "selected_response_activity_count": selected_response_count,
        "short_text_activity_count": short_text_count,
        "learner_visible_exact_duplicate_count": _duplicate_excess(all_exact),
        "learner_visible_normalized_duplicate_count": _duplicate_excess(all_normalized),
        "within_form_exact_duplicate_count": within_exact,
        "within_form_normalized_duplicate_count": within_normalized,
        "minimum_distinct_prompts_per_form": minimum_distinct_prompts,
        "maximum_same_prompt_count_per_form": maximum_same_prompt,
        "engineering_marker_visible_count": 0,
        "unit04_content_authority_consumed_count": 0,
    }


def render_form_html(form: Mapping[str, Any]) -> str:
    ordinal = int(form["form_ordinal"])
    activities = list(form["activities"])
    position = 0
    blocks: list[str] = []
    for section in form["sections"]:
        count = int(section["activity_count"])
        rows = activities[position:position + count]
        cards = "".join(
            u01_pdf._activity_html(activity, position + offset + 1)
            for offset, activity in enumerate(rows)
        )
        blocks.append(
            '<section class="unit05-section">'
            + f'<h2>{u01_pdf._safe_text(str(section["section_name"]))}</h2>'
            + cards
            + "</section>"
        )
        position += count
    document = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<title>Unit 5 Form {ordinal:02d}</title></head><body>"
        f"<h1>Unit 5 · Form {ordinal:02d}</h1>"
        f'<p>{u01_pdf._safe_text(str(form["progression_stage"]).replace("_", " ").title())}</p>'
        + "".join(blocks)
        + "</body></html>"
    )
    if document.count('<article class="activity">') != 40:
        raise Unit05LearnerFacingAcceptanceError(
            f"HTML_ACTIVITY_COUNT_INVALID:F{ordinal:02d}"
        )
    lowered = document.casefold()
    for marker in FORBIDDEN_LEARNER_MARKERS:
        if marker.casefold() in lowered:
            raise Unit05LearnerFacingAcceptanceError(
                f"HTML_ENGINEERING_MARKER_VISIBLE:F{ordinal:02d}:{marker}"
            )
    return document


def build_acceptance_report(
    source_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(source_payload or source.build_export_payload())
    _source_contract(payload)
    source_snapshot = _digest(payload)
    runtime_identity = _runtime_identity(payload["runtime_bindings"])
    item_identity = _item_identity(payload["questionbank_items"])
    forms, answer_bindings = _project_forms(payload)
    acceptance = _validate_learner_forms(forms, answer_bindings, payload)
    rendered = [render_form_html(form) for form in forms]

    if _digest(payload) != source_snapshot:
        raise Unit05LearnerFacingAcceptanceError("SOURCE_PAYLOAD_MUTATED")
    if _runtime_identity(payload["runtime_bindings"]) != runtime_identity:
        raise Unit05LearnerFacingAcceptanceError("SOURCE_RUNTIME_IDENTITY_MUTATED")
    if _item_identity(payload["questionbank_items"]) != item_identity:
        raise Unit05LearnerFacingAcceptanceError("SOURCE_ITEM_IDENTITY_MUTATED")

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
        "acceptance": {
            **acceptance,
            "rendered_activity_count": sum(
                html.count('<article class="activity">') for html in rendered
            ),
        },
        "answer_key_bindings": answer_bindings,
        "answer_key_binding_identity_sha256": _digest(answer_bindings),
        "learner_forms": forms,
        "html_form_count": len(rendered),
        "html_activity_count": sum(
            html.count('<article class="activity">') for html in rendered
        ),
        "renderer_reuse": (
            "product.a1fs_v1_2_1."
            "u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization._activity_html"
        ),
        "alignment_reference": {
            "unit04_role": "COMPARISON_AND_ACCEPTANCE_PATTERN_ALIGNMENT_ONLY",
            "unit04_content_authority_consumed": False,
            "unit04_sentence_or_scene_content_consumed": False,
            "unit04_function_or_task_identity_consumed": False,
            "unit05_q10_is_sole_direct_content_source": True,
            "aligned_dimensions": [
                "20x40 learner-form denominator",
                "A6/B10/C10/D8/E6 section architecture",
                "visible five-stage progression",
                "source identity immutability",
                "engineering metadata suppression",
                "learner answerability and duplicate checks",
                "generic learner renderer reuse",
            ],
        },
        "presentation_fixes": {
            "engineering_prompt_projection_count": 800,
            "engineering_stimulus_metadata_suppression_count": 800,
            "progression_support_projection_count": 800,
            "meaning_option_humanization_enabled": True,
            "polarity_option_humanization_enabled": True,
            "unit05_scene_evidence_projection_enabled": True,
        },
        "claim_boundaries": {
            "unit04_used_as_unit05_content_authority": False,
            "source_800_runtime_rows_mutated": False,
            "source_selected_item_identities_mutated": False,
            "source_candidate_identities_mutated": False,
            "source_questionbank_items_mutated": False,
            "q06_mutated": False,
            "q07_mutated": False,
            "q08_mutated": False,
            "q09_mutated": False,
            "q10_redone": False,
            "second_questionbank_authority_created": False,
            "second_selector_created": False,
            "second_renderer_created": False,
            "new_grammar_authority_created": False,
            "new_vocabulary_identity_created": False,
            "new_sentence_identity_created": False,
            "new_scene_identity_created": False,
            "new_communicative_function_identity_created": False,
            "unit05_current360_materialized": False,
            "unit05_spoken360_materialized": False,
            "unit05_pattern360_materialized": False,
            "pdf_materialized": False,
            "be_interrogative_mastery_activated": False,
            "past_be_activated": False,
            "existential_there_be_activated": False,
            "present_continuous_mastery_activated": False,
            "a2_a2plus_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


if __name__ == "__main__":
    print(json.dumps(build_acceptance_report(), ensure_ascii=False, indent=2))
