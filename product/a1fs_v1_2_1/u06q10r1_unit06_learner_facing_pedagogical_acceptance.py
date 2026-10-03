#!/usr/bin/env python3
"""Unit06 Q10R1 learner-facing pedagogical acceptance.

Consumes the exact approved Unit06 Q10 coverage-driven 300-item / 10-form
QuestionBank and projects learner-safe activities without changing Q10 item,
form, Q06 sentence, Q07 scene, Q07R1 chunk, Q08 function, or Q09 task identity.
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
from ulga.builders import build_a1fs_v1_u06q10_questionbank_form_materialization as source
from ulga.validators import (
    validate_a1fs_v1_u06q10_questionbank_form_materialization as source_validator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only learner-facing acceptance consumer over the approved Unit06 Q10 "
    "coverage-driven QuestionBank/forms. It preserves Q10 item/form and upstream "
    "sentence/scene/chunk/function/task identities, projects only learner-visible "
    "presentation, reuses the existing generic learner activity renderer, and "
    "creates no new grammar, vocabulary, sentence, scene, chunk, communicative-"
    "function, selector, scoring, Reader360, PDF, Unit07, A2 or A2+ authority."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U06Q10R1_Unit06LearnerFacingPedagogicalAcceptance"
SCHEMA_VERSION = "a1fs.v1.u06.q10r1.learner_facing_pedagogical_acceptance.v1"
PASS_STATUS = "PASS_A1FS_V1_U06Q10R1_LEARNER_FACING_PEDAGOGICAL_ACCEPTANCE"
NEXT_SHORT_STEP = "A1FS-V1-U06Q10R2_Unit06LearnerPDFMaterializationAndVisualAcceptance"

FORM_COUNT = 10
ACTIVITIES_PER_FORM = 30
TOTAL_ACTIVITIES = 300
SECTION_ORDER = ("A", "B", "C", "D", "E")
SECTION_COUNTS = {"A": 6, "B": 6, "C": 8, "D": 4, "E": 6}
SECTION_TITLES = {
    "A": "Use can with the action word",
    "B": "Understand ability meaning",
    "C": "Build and fix ability sentences",
    "D": "Use can in context",
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
    "q06_sentence_id",
    "source_route",
    "functional_chunk_binding",
    "task_family_id",
    "communicative_function_id",
    "frame_id",
    "item_id",
    "correct_answer",
    "response_contract",
    "semantic_admission",
    "source_kind",
    "source_claim",
    "scene_grounding",
    "authority",
    "admitted",
    "human_review",
    "q07r1",
    "u06-tf",
    "u06-cf",
    "u06q10",
    "u06_q10",
    "a1fs-v1",
    "a1fs_v1",
    "pass_a1fs",
)
ABILITY_MEANING_OPTIONS = {
    "ability or capability": "what someone or something is able to do",
    "permission or a request": "where someone or something is",
    "possibility": "what someone or something is like",
}

class Unit06LearnerFacingAcceptanceError(ValueError):
    pass

def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()

def _normalize_visible(value: Any) -> str:
    text = str(value or "").casefold()
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip()

def _item_identity(items: Sequence[Mapping[str, Any]]) -> str:
    return _digest([
        {
            "item_id": row["item_id"],
            "slot_id": row["slot_id"],
            "form_number": row["form_number"],
            "section": row["section"],
            "task_family_id": row["task_family_id"],
            "communicative_function_id": row["communicative_function_id"],
            "frame_id": row["frame_id"],
            "source_route": row["source_route"],
            "q06_sentence_id": row["q06_sentence_id"],
            "functional_chunk_binding": row["functional_chunk_binding"],
        }
        for row in items
    ])

def _form_identity(forms: Sequence[Mapping[str, Any]]) -> str:
    return _digest([
        {
            "form_id": row["form_id"],
            "form_number": row["form_number"],
            "progression_role": row["progression_role"],
            "section_counts": row["section_counts"],
            "item_ids": list(row["item_ids"]),
        }
        for row in forms
    ])

def _source_contract(payload: Mapping[str, Any]) -> None:
    source_validator.validate_payload(payload)
    if payload.get("status") != source.PASS_STATUS:
        raise Unit06LearnerFacingAcceptanceError("SOURCE_STATUS_INVALID")
    if payload.get("next_short_step") != TASK_ID:
        raise Unit06LearnerFacingAcceptanceError("SOURCE_NEXT_STEP_INVALID")
    contract = dict(payload.get("materialization_contract") or {})
    expected = {
        "capacity_policy": "COVERAGE_DRIVEN_NOT_FIXED_BY_LEGACY_20X40",
        "form_count": 10,
        "questions_per_form": 30,
        "total_items": 300,
        "section_counts_per_form": SECTION_COUNTS,
        "q06_canonical_sentence_route_item_count": 129,
        "q07r1_chunk_controlled_route_item_count": 171,
        "all_q06_sentences_materialized_once": True,
        "all_182_chunks_have_questionbank_binding": True,
        "all_62_q07r1_source_verbs_have_questionbank_binding": True,
        "all_17_q07_scenes_have_questionbank_binding": True,
        "item_local_sentence_realization_promoted_to_sentence_authority": False,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            raise Unit06LearnerFacingAcceptanceError(
                f"SOURCE_CONTRACT_DRIFT:{key}:{contract.get(key)}:{value}"
            )
    coverage = dict(payload.get("coverage") or {})
    expected_coverage = {
        "questionbank_item_count": 300,
        "form_count": 10,
        "questions_per_form": 30,
        "task_family_coverage": "10/10",
        "communicative_function_coverage": "6/6",
        "frame_coverage": "3/3",
        "q06_sentence_materialized_coverage": "129/129",
        "q06_context_required_sentence_materialized_coverage": "49/49",
        "q06_standalone_sentence_materialized_coverage": "80/80",
        "q07_scene_materialized_coverage": "17/17",
        "q07r1_functional_chunk_binding_coverage": "182/182",
        "q07r1_source_verb_binding_coverage": "62/62",
        "restricted_deferred_chunk_sentence_realization_count": 0,
        "item_local_sentence_promoted_to_canonical_asset_count": 0,
    }
    for key, value in expected_coverage.items():
        if coverage.get(key) != value:
            raise Unit06LearnerFacingAcceptanceError(
                f"SOURCE_COVERAGE_DRIFT:{key}:{coverage.get(key)}:{value}"
            )

def _stage_support(item: Mapping[str, Any]) -> str:
    stage = str(item["progression_role"])
    marker = STAGE_VISIBLE_MARKERS.get(stage)
    if marker is None:
        raise Unit06LearnerFacingAcceptanceError(f"STAGE_INVALID:{stage}")
    if stage == "GUIDED":
        body = "Focus on can and the action word."
    elif stage == "REDUCED_SUPPORT":
        body = "Use the sentence, phrase, or scene clue."
    elif stage == "INDEPENDENT":
        body = "Read the information carefully and decide."
    elif stage == "TRANSFER":
        body = "Use the same ability pattern in this new practice."
    elif stage == "RETENTION":
        body = "Use earlier-unit clues, but keep can ability as the main target."
    else:
        raise Unit06LearnerFacingAcceptanceError(f"STAGE_INVALID:{stage}")
    return f"{marker} {body}"

def _scene_index() -> dict[str, Mapping[str, Any]]:
    src = source._sources()
    return {str(row["scene_ref_id"]): row for row in src["q07"]["micro_scenes"]}

def _scene_support_text(scene_ref: Any, scenes: Mapping[str, Mapping[str, Any]]) -> str:
    if not scene_ref:
        return ""
    scene = scenes.get(str(scene_ref))
    if scene is None:
        raise Unit06LearnerFacingAcceptanceError(f"SCENE_UNRESOLVED:{scene_ref}")
    rows = [
        str(line["text"]) for line in scene.get("lines", [])
        if str(line.get("role")) == "CUMULATIVE_SUPPORT"
    ]
    if not rows:
        raise Unit06LearnerFacingAcceptanceError(f"SCENE_SUPPORT_EMPTY:{scene_ref}")
    return " ".join(rows)

def _project_options(item: Mapping[str, Any]) -> tuple[list[str], Any]:
    options = [str(value) for value in item.get("options") or []]
    correct = item.get("correct_answer")
    family = str(item["task_family_id"])
    if family == "U06-TF03_ABILITY_MEANING_DISCRIMINATION":
        projected = [ABILITY_MEANING_OPTIONS[value] for value in options]
        return projected, ABILITY_MEANING_OPTIONS[str(correct)]
    return options, correct

def _prompt(item: Mapping[str, Any]) -> str:
    family = str(item["task_family_id"])
    if family == "U06-TF01_CAN_FORM_RECOGNITION":
        return "Choose the word that completes the ability sentence."
    if family == "U06-TF02_BASE_VERB_FORM_SELECTION":
        return "Choose the action word form that comes after can."
    if family == "U06-TF03_ABILITY_MEANING_DISCRIMINATION":
        return "What does this phrase tell you?"
    if family == "U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE":
        return "Choose the CAN phrase that matches the action."
    if family == "U06-TF05_CHUNK_TO_COMPLETE_SENTENCE":
        return "Use the subject and CAN phrase to write one complete ability sentence."
    if family == "U06-TF06_ERROR_DETECTION_AND_CORRECTION":
        return "Fix the CAN form. Write the correct sentence."
    if family == "U06-TF07_SCENE_BOUND_CONTEXT_GAP":
        return "Use the scene clues to choose the ability sentence that matches."
    if family == "U06-TF08_U01_U05_CUMULATIVE_INTEGRATION":
        return "Use the review clues and write one complete Unit 6 ability sentence."
    if family == "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE":
        return "Write one complete affirmative sentence that gives the ability information."
    if family == "U06-TF10_TRANSFER":
        return "Use can to write one ability sentence for this new situation."
    raise Unit06LearnerFacingAcceptanceError(f"TASK_FAMILY_UNSUPPORTED:{family}")

def _stimulus(item: Mapping[str, Any], scenes: Mapping[str, Mapping[str, Any]]) -> str:
    family = str(item["task_family_id"])
    support = _stage_support(item)
    raw = dict(item.get("stimulus") or {})

    if family in {"U06-TF01_CAN_FORM_RECOGNITION", "U06-TF02_BASE_VERB_FORM_SELECTION"}:
        sentence = str(raw.get("sentence_with_gap") or "").strip()
        if not sentence:
            raise Unit06LearnerFacingAcceptanceError(f"SENTENCE_GAP_MISSING:{item['item_id']}")
        antecedent = str(raw.get("antecedent_cue") or "").strip()
        extra = f" Referent: {antecedent}" if antecedent else ""
        return f"{support} Sentence: {sentence}{extra}"

    if family == "U06-TF03_ABILITY_MEANING_DISCRIMINATION":
        phrase = str(raw.get("functional_chunk") or item.get("functional_chunk_binding") or "").strip()
        if not phrase:
            raise Unit06LearnerFacingAcceptanceError(f"MEANING_PHRASE_MISSING:{item['item_id']}")
        grounded = bool(item.get("functional_chunk_scene_grounding")) or phrase.casefold() in {
            "can go to school", "can study at school"
        }
        context = " Situation: we see the person or thing do this successfully." if grounded else ""
        return f"{support} Phrase: {phrase}.{context}"

    if family == "U06-TF04_FUNCTIONAL_CHUNK_TO_ACTION_OR_SCENE":
        action = str(raw.get("action_cue") or item.get("base_verb") or "").strip()
        if not action:
            raise Unit06LearnerFacingAcceptanceError(f"ACTION_CUE_MISSING:{item['item_id']}")
        return f"{support} Action: {action}."

    if family == "U06-TF05_CHUNK_TO_COMPLETE_SENTENCE":
        subject = str(raw.get("subject_cue") or "").strip()
        phrase = str(raw.get("functional_chunk") or "").strip()
        if not subject or not phrase:
            raise Unit06LearnerFacingAcceptanceError(f"CHUNK_SENTENCE_CUE_MISSING:{item['item_id']}")
        antecedent = str(raw.get("antecedent_cue") or "").strip()
        ref = f" Referent: {antecedent}." if antecedent else ""
        return f"{support} Subject: {subject}. CAN phrase: {phrase}.{ref}"

    if family == "U06-TF06_ERROR_DETECTION_AND_CORRECTION":
        incorrect = str(raw.get("incorrect_sentence") or "").strip()
        if not incorrect:
            raise Unit06LearnerFacingAcceptanceError(f"INCORRECT_SENTENCE_MISSING:{item['item_id']}")
        antecedent = str(raw.get("antecedent_cue") or "").strip()
        ref = f" Referent: {antecedent}." if antecedent else ""
        return f"{support} Sentence to fix: {incorrect}{ref}"

    if family == "U06-TF07_SCENE_BOUND_CONTEXT_GAP":
        scene_ref = item.get("scene_ref_id")
        scene_text = _scene_support_text(scene_ref, scenes)
        referent = str(raw.get("target_referent_cue") or "").strip()
        action = str(raw.get("target_action_cue") or "").strip()
        if not referent or not action:
            raise Unit06LearnerFacingAcceptanceError(f"TF07_TARGET_CUE_MISSING:{item['item_id']}")
        return f"{support} Scene: {scene_text} Target: {referent}. Action: {action}."

    if family == "U06-TF08_U01_U05_CUMULATIVE_INTEGRATION":
        subject = str(raw.get("subject_cue") or "").strip()
        phrase = str(raw.get("functional_chunk") or "").strip()
        if not subject or not phrase:
            raise Unit06LearnerFacingAcceptanceError(f"CUMULATIVE_TARGET_CUE_MISSING:{item['item_id']}")
        return (
            f"{support} Review clue: one person is ready; two things are nearby. "
            f"Target subject: {subject}. CAN phrase: {phrase}."
        )

    if family == "U06-TF09_PRODUCTIVE_ABILITY_RESPONSE":
        subject = str(raw.get("subject_cue") or item.get("learner_visible_reference_sentence", "")).strip()
        phrase = str(raw.get("functional_chunk") or raw.get("action_cue") or "").strip()
        if item["source_route"] == "Q06_CANONICAL_SENTENCE":
            subject = str(raw.get("subject_cue") or "").strip()
            phrase = str(raw.get("action_cue") or "").strip()
        if not subject or not phrase:
            raise Unit06LearnerFacingAcceptanceError(f"PRODUCTIVE_CUE_MISSING:{item['item_id']}")
        return f"{support} Person or thing: {subject}. Action: {phrase}."

    if family == "U06-TF10_TRANSFER":
        subject = str(raw.get("source_subject_cue") or "").strip()
        action = str(raw.get("action_cue") or "").strip()
        if not subject or not action:
            raise Unit06LearnerFacingAcceptanceError(f"TRANSFER_CUE_MISSING:{item['item_id']}")
        return (
            f"{support} This person or group is showing what they can do. "
            f"Person or group: {subject}. Action: {action}."
        )

    raise Unit06LearnerFacingAcceptanceError(f"STIMULUS_FAMILY_UNSUPPORTED:{family}")

def _learner_activity(
    number: int,
    item: Mapping[str, Any],
    scenes: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    options, projected_correct = _project_options(item)
    activity = {
        "question_number": f"Q{number:02d}",
        "skill": "Grammar",
        "stimulus": _stimulus(item, scenes),
        "prompt": _prompt(item),
        "options": options,
        "response_mode": "select_one" if options else "short_text",
        "capture_enabled": True,
        "practice_only": False,
    }
    answer = {
        "question_number": f"Q{number:02d}",
        "source_item_id": str(item["item_id"]),
        "source_route": str(item["source_route"]),
        "task_family_id": str(item["task_family_id"]),
        "response_mode": activity["response_mode"],
        "reference_answer": projected_correct,
        "source_scoring_mode": str(item["response_contract"]["scoring_mode"]),
        "reference_response_nonexclusive": bool(
            item["response_contract"].get("reference_response_nonexclusive")
        ),
    }
    return activity, answer

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
            raise Unit06LearnerFacingAcceptanceError(
                f"ENGINEERING_MARKER_VISIBLE:F{form_number:02d}:Q{question_number:02d}:{marker}"
            )

def _project_forms(payload: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items = list(payload.get("questionbank_items") or [])
    source_forms = list(payload.get("forms") or [])
    if (len(items), len(source_forms)) != (300, 10):
        raise Unit06LearnerFacingAcceptanceError("SOURCE_DENOMINATOR_INVALID")
    scenes = _scene_index()
    item_index = {str(row["item_id"]): row for row in items}
    if len(item_index) != 300:
        raise Unit06LearnerFacingAcceptanceError("SOURCE_ITEM_IDENTITY_COLLISION")

    forms: list[dict[str, Any]] = []
    answers: list[dict[str, Any]] = []
    for form_number in range(1, 11):
        source_form = source_forms[form_number - 1]
        if int(source_form.get("form_number", -1)) != form_number:
            raise Unit06LearnerFacingAcceptanceError(f"SOURCE_FORM_SEQUENCE_INVALID:F{form_number:02d}")
        ordered_ids = [str(x) for x in source_form.get("item_ids") or []]
        if len(ordered_ids) != 30:
            raise Unit06LearnerFacingAcceptanceError(f"SOURCE_FORM_ITEM_COUNT_INVALID:F{form_number:02d}")
        activities: list[dict[str, Any]] = []
        sections: list[dict[str, Any]] = []
        for section in SECTION_ORDER:
            section_ids = [x for x in ordered_ids if str(item_index[x]["section"]) == section]
            if len(section_ids) != SECTION_COUNTS[section]:
                raise Unit06LearnerFacingAcceptanceError(
                    f"SOURCE_SECTION_COUNT_INVALID:F{form_number:02d}:{section}"
                )
            for item_id in section_ids:
                item = item_index[item_id]
                if int(item["form_number"]) != form_number or str(item["section"]) != section:
                    raise Unit06LearnerFacingAcceptanceError(f"ITEM_SCOPE_DRIFT:{item_id}")
                activity, answer = _learner_activity(len(activities) + 1, item, scenes)
                _assert_no_engineering_markers(activity, form_number, len(activities) + 1)
                activities.append(activity)
                answers.append({"form_number": form_number, **answer})
            sections.append({
                "section": section,
                "section_name": SECTION_TITLES[section],
                "activity_count": SECTION_COUNTS[section],
            })
        form = {
            "unit_id": source.UNIT_ID,
            "unit_ordinal": 6,
            "form_id": f"U06Q10R1-F{form_number:02d}",
            "form_ordinal": form_number,
            "progression_stage": str(source_form["progression_role"]),
            "section_count": 5,
            "learner_visible_activity_count": 30,
            "sections": sections,
            "activities": activities,
        }
        u01_learner._assert_no_answer_leak(form)
        forms.append(form)
    return forms, answers

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
    answers: Sequence[Mapping[str, Any]],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if len(forms) != 10:
        raise Unit06LearnerFacingAcceptanceError("FORM_COUNT_INVALID")
    if len(answers) != 300:
        raise Unit06LearnerFacingAcceptanceError("ANSWER_BINDING_COUNT_INVALID")
    items = {str(row["item_id"]): row for row in payload["questionbank_items"]}
    all_exact: list[str] = []
    all_normalized: list[str] = []
    within_exact = 0
    within_normalized = 0
    min_distinct_prompts = 999
    max_same_prompt = 0
    stage_counts: Counter[str] = Counter()
    stage_visible: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    function_counts: Counter[str] = Counter()
    frame_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    chunk_bindings: set[str] = set()
    source_verbs: set[str] = set()
    scene_refs: set[str] = set()
    item_local = 0
    selected_count = 0

    for form in forms:
        ordinal = int(form["form_ordinal"])
        activities = list(form["activities"])
        if len(activities) != 30:
            raise Unit06LearnerFacingAcceptanceError(f"FORM_ACTIVITY_COUNT_INVALID:F{ordinal:02d}")
        stage = str(form["progression_stage"])
        marker = STAGE_VISIBLE_MARKERS[stage]
        exact = [_canonical(_visible_payload(row, normalized=False)) for row in activities]
        normalized = [_canonical(_visible_payload(row, normalized=True)) for row in activities]
        within_exact += _duplicate_excess(exact)
        within_normalized += _duplicate_excess(normalized)
        all_exact.extend(exact)
        all_normalized.extend(normalized)
        prompts = [str(row["prompt"]) for row in activities]
        min_distinct_prompts = min(min_distinct_prompts, len(set(prompts)))
        max_same_prompt = max(max_same_prompt, max(Counter(prompts).values()))
        stage_counts[stage] += len(activities)
        stage_visible[stage] += sum(1 for row in activities if marker in str(row["stimulus"]))
        selected_count += sum(1 for row in activities if row["response_mode"] == "select_one")

        source_form = payload["forms"][ordinal - 1]
        for item_id in source_form["item_ids"]:
            item = items[str(item_id)]
            family_counts[str(item["task_family_id"])] += 1
            function_counts[str(item["communicative_function_id"])] += 1
            frame_counts[str(item["frame_id"])] += 1
            route_counts[str(item["source_route"])] += 1
            if item.get("functional_chunk_binding"):
                chunk_bindings.add(str(item["functional_chunk_binding"]))
            if item["source_route"] == "Q07R1_CHUNK_CONTROLLED_REALIZATION" and item.get("q07r1_source_verb_member"):
                source_verbs.add(str(item["base_verb"]))
            if item.get("scene_ref_id"):
                scene_refs.add(str(item["scene_ref_id"]))
            if item.get("item_local_sentence_realization"):
                item_local += 1

    if within_exact != 0 or within_normalized != 0:
        raise Unit06LearnerFacingAcceptanceError(
            f"WITHIN_FORM_VISIBLE_DUPLICATION:{within_exact}:{within_normalized}"
        )
    if min_distinct_prompts < 10:
        raise Unit06LearnerFacingAcceptanceError(f"PROMPT_VARIETY_TOO_LOW:{min_distinct_prompts}")
    expected_stages = {
        "GUIDED": 60,
        "REDUCED_SUPPORT": 60,
        "INDEPENDENT": 60,
        "TRANSFER": 60,
        "RETENTION": 60,
    }
    if dict(sorted(stage_counts.items())) != dict(sorted(expected_stages.items())):
        raise Unit06LearnerFacingAcceptanceError(f"STAGE_COUNTS_INVALID:{stage_counts}")
    if stage_visible != stage_counts:
        raise Unit06LearnerFacingAcceptanceError("STAGE_SUPPORT_NOT_VISIBLE_ON_ALL_ACTIVITIES")
    if len(family_counts) != 10:
        raise Unit06LearnerFacingAcceptanceError("TASK_FAMILY_LEARNER_COVERAGE_INVALID")
    if len(function_counts) != 6:
        raise Unit06LearnerFacingAcceptanceError("FUNCTION_LEARNER_COVERAGE_INVALID")
    if len(frame_counts) != 3:
        raise Unit06LearnerFacingAcceptanceError("FRAME_LEARNER_COVERAGE_INVALID")
    if route_counts != Counter({"Q06_CANONICAL_SENTENCE": 129, "Q07R1_CHUNK_CONTROLLED_REALIZATION": 171}):
        raise Unit06LearnerFacingAcceptanceError(f"ROUTE_COUNTS_INVALID:{route_counts}")
    if len(chunk_bindings) != 182:
        raise Unit06LearnerFacingAcceptanceError(f"CHUNK_LEARNER_COVERAGE_INVALID:{len(chunk_bindings)}")
    if len(source_verbs) != 62:
        raise Unit06LearnerFacingAcceptanceError(f"SOURCE_VERB_LEARNER_COVERAGE_INVALID:{len(source_verbs)}")
    if len(scene_refs) != 17:
        raise Unit06LearnerFacingAcceptanceError(f"SCENE_LEARNER_COVERAGE_INVALID:{len(scene_refs)}")

    return {
        "form_count": 10,
        "activity_count": 300,
        "answer_key_binding_count": 300,
        "task_family_coverage": "10/10",
        "communicative_function_coverage": "6/6",
        "frame_coverage": "3/3",
        "q06_sentence_coverage": "129/129",
        "q07_scene_coverage": "17/17",
        "q07r1_functional_chunk_coverage": "182/182",
        "q07r1_source_verb_coverage": "62/62",
        "source_route_counts": dict(route_counts),
        "item_local_sentence_activity_count": item_local,
        "item_local_sentence_promoted_to_canonical_asset_count": 0,
        "restricted_deferred_chunk_sentence_realization_count": 0,
        "stage_activity_counts": dict(sorted(stage_counts.items())),
        "stage_support_levels": STAGE_SUPPORT_LEVEL,
        "stage_visible_support_counts": dict(sorted(stage_visible.items())),
        "selected_response_activity_count": selected_count,
        "short_text_activity_count": TOTAL_ACTIVITIES - selected_count,
        "learner_visible_exact_duplicate_count": _duplicate_excess(all_exact),
        "learner_visible_normalized_duplicate_count": _duplicate_excess(all_normalized),
        "within_form_exact_duplicate_count": within_exact,
        "within_form_normalized_duplicate_count": within_normalized,
        "minimum_distinct_prompts_per_form": min_distinct_prompts,
        "maximum_same_prompt_count_per_form": max_same_prompt,
        "engineering_marker_visible_count": 0,
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
            '<section class="unit06-section">'
            + f'<h2>{u01_pdf._safe_text(str(section["section_name"]))}</h2>'
            + cards
            + "</section>"
        )
        position += count
    document = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<title>Unit 6 Form {ordinal:02d}</title></head><body>"
        f"<h1>Unit 6 · Form {ordinal:02d}</h1>"
        f'<p>{u01_pdf._safe_text(str(form["progression_stage"]).replace("_", " ").title())}</p>'
        + "".join(blocks)
        + "</body></html>"
    )
    if document.count('<article class="activity">') != 30:
        raise Unit06LearnerFacingAcceptanceError(f"HTML_ACTIVITY_COUNT_INVALID:F{ordinal:02d}")
    lowered = document.casefold()
    for marker in FORBIDDEN_LEARNER_MARKERS:
        if marker.casefold() in lowered:
            raise Unit06LearnerFacingAcceptanceError(
                f"HTML_ENGINEERING_MARKER_VISIBLE:F{ordinal:02d}:{marker}"
            )
    return document

def build_acceptance_report(source_payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(source_payload or source.build_export_payload())
    _source_contract(payload)
    snapshot = _digest(payload)
    item_identity = _item_identity(payload["questionbank_items"])
    form_identity = _form_identity(payload["forms"])
    forms, answers = _project_forms(payload)
    acceptance = _validate_learner_forms(forms, answers, payload)
    rendered = [render_form_html(form) for form in forms]

    if _digest(payload) != snapshot:
        raise Unit06LearnerFacingAcceptanceError("SOURCE_PAYLOAD_MUTATED")
    if _item_identity(payload["questionbank_items"]) != item_identity:
        raise Unit06LearnerFacingAcceptanceError("SOURCE_ITEM_IDENTITY_MUTATED")
    if _form_identity(payload["forms"]) != form_identity:
        raise Unit06LearnerFacingAcceptanceError("SOURCE_FORM_IDENTITY_MUTATED")

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "source_task_id": source.TASK_ID,
        "source_status": source.PASS_STATUS,
        "source_q10_validator_reused": source_validator.VALIDATOR_ID,
        "source_snapshot_sha256": snapshot,
        "source_item_identity_sha256": item_identity,
        "source_form_identity_sha256": form_identity,
        "acceptance": {
            **acceptance,
            "rendered_activity_count": sum(
                html.count('<article class="activity">') for html in rendered
            ),
        },
        "answer_key_bindings": answers,
        "answer_key_binding_identity_sha256": _digest(answers),
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
            "engineering_prompt_projection_count": 300,
            "engineering_stimulus_metadata_suppression_count": 300,
            "progression_support_projection_count": 300,
            "ability_meaning_option_humanization_enabled": True,
            "tf07_scene_target_sentence_leak_suppressed": True,
            "tf08_generic_engineering_support_recast_as_learner_review_clue": True,
            "transfer_placeholder_recast_as_learner_visible_situation": True,
        },
        "claim_boundaries": {
            "source_questionbank_items_mutated": False,
            "source_forms_mutated": False,
            "q06_mutated": False,
            "q07_mutated": False,
            "q07r1_mutated": False,
            "q08_mutated": False,
            "q09_mutated": False,
            "q10_redone": False,
            "second_questionbank_authority_created": False,
            "second_renderer_created": False,
            "new_grammar_authority_created": False,
            "new_vocabulary_identity_created": False,
            "new_sentence_identity_created": False,
            "new_scene_identity_created": False,
            "new_functional_chunk_identity_created": False,
            "new_communicative_function_identity_created": False,
            "item_local_sentence_promoted_to_canonical_asset": False,
            "can_interrogative_mastery_activated": False,
            "can_negative_mastery_activated": False,
            "permission_can_activated": False,
            "offer_can_activated": False,
            "request_can_activated": False,
            "possibility_can_activated": False,
            "unit06_current360_materialized": False,
            "unit06_spoken360_materialized": False,
            "unit06_pattern360_materialized": False,
            "pdf_materialized": False,
            "a2_a2plus_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }

if __name__ == "__main__":
    print(json.dumps(build_acceptance_report(), ensure_ascii=False, indent=2))
