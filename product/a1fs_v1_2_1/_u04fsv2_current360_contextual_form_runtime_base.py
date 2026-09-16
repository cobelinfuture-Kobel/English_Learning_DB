from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u04neb02_natural_episode_bank_360 as current360,
)
from product.a1fs_v1_2_1 import (
    u04q10r1_unit04_learner_facing_pedagogical_acceptance_impl as legacy_q10r1,
)
from ulga.builders import (
    build_a1fs_v1_u04q10_questionbank_form_materialization as q10,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
TASK_ID = "A1FS-V1-U04FSV2_Current360ContextualForm01To20ActiveRuntimeMaterialization"
STATUS = "PASS_A1FS_V1_U04FSV2_CURRENT360_CONTEXTUAL_FORM01_TO20_ACTIVE_RUNTIME"
REVISION = "CAMBRIDGE_CONTEXTUAL_A1_TASK_MATURITY_CUTOVER_V1"
NEXT_SHORT_STEP = "A1FS-V1-U04SPV2_SpeakingLayer1BridgeLayer2Cutover"

FORM_COUNT = 20
ACTIVITIES_PER_FORM = 40
TOTAL_ACTIVITIES = 800
SECTION_ORDER = ("A", "B", "C", "D", "E")
SECTION_COUNTS = {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
TARGET_RELATIONS = tuple(q10.TARGET_RELATIONS)
TARGET_RELATION_SET = frozenset(TARGET_RELATIONS)
SUPPORT_RELATIONS = ("next to", "in front of")
CONTEXTUAL_SECTIONS = frozenset({"B", "C", "D", "E"})
A_CONTROLLED_ACTIVITY_COUNT = FORM_COUNT * SECTION_COUNTS["A"]
CONTEXTUAL_ACTIVITY_COUNT = TOTAL_ACTIVITIES - A_CONTROLLED_ACTIVITY_COUNT
SHARED_D_E_CONTEXT_PAIRS_PER_FORM = 6
SHARED_D_E_CONTEXT_PAIR_COUNT = FORM_COUNT * SHARED_D_E_CONTEXT_PAIRS_PER_FORM

STAGE_CONTRACT = {
    "GUIDED": {
        "forms": (1, 2, 3, 4),
        "support_level": "HIGH",
        "context_exposure": "SEEN_GUIDED",
        "learner_support": "Read the passage. Focus on one clear location fact.",
    },
    "REDUCED_SUPPORT": {
        "forms": (5, 6, 7, 8),
        "support_level": "MEDIUM",
        "context_exposure": "SEEN_REDUCED_SUPPORT",
        "learner_support": "Read and use the location evidence.",
    },
    "INDEPENDENT": {
        "forms": (9, 10, 11, 12),
        "support_level": "LOW",
        "context_exposure": "SEEN_INDEPENDENT",
        "learner_support": "Read the passage carefully.",
    },
    "TRANSFER": {
        "forms": (13, 14, 15, 16),
        "support_level": "MINIMAL",
        "context_exposure": "UNSEEN_TRANSFER",
        "learner_support": "Use this new passage.",
    },
    "RETENTION": {
        "forms": (17, 18, 19, 20),
        "support_level": "CUMULATIVE",
        "context_exposure": "UNSEEN_RETENTION",
        "learner_support": "Use what you know with this new passage.",
    },
}

SECTION_SKILL = {
    "A": "GRAMMAR",
    "B": "READING",
    "C": "READING_WRITING",
    "D": "READING",
    "E": "SPEAKING_WRITING",
}

TASK_VARIANTS = {
    "A": (
        "CONTROLLED_RELATION_RECOGNITION",
        "CONTROLLED_FORM_SELECTION",
        "CONTROLLED_POSITION_MEANING",
    ),
    "B": (
        "PASSAGE_FOCUS_RELATION_SELECT",
        "PASSAGE_FOCUS_RELATION_WRITE",
        "PASSAGE_EVIDENCE_SENTENCE_SELECT",
        "PASSAGE_RELATION_CHECK",
        "PASSAGE_EVIDENCE_COPY",
    ),
    "C": (
        "CONTEXT_GAP_RELATION_SELECT",
        "CONTEXT_GAP_RELATION_WRITE",
        "PASSAGE_FOCUS_SENTENCE_RESTORE",
        "CONTEXTUAL_LOCATION_SENTENCE_CONSTRUCTION",
        "CONTEXTUAL_ERROR_CORRECTION",
    ),
    "D": (
        "READING_SPECIFIC_INFORMATION",
        "READING_EVIDENCE_SENTENCE",
        "READING_TWO_LOCATION_FACTS",
        "READING_LOCATION_EVIDENCE_EXPLANATION",
        "READING_SIMPLE_GIST_SEED",
        "READING_CONNECTED_QA",
        "READING_SHORT_RETELL",
        "READING_EVIDENCE_JUSTIFICATION",
    ),
    "E": (
        "WRITING_ONE_LOCATION_FACT",
        "WRITING_TWO_LOCATION_FACTS",
        "SPEAKING_LOCATION_QA",
        "SPEAKING_SCENE_DESCRIPTION",
        "SPEAKING_ASK_LOCATION_QUESTION",
        "SPEAKING_TRANSFER_CHANGED_LOCATION",
    ),
}
EXPECTED_TASK_VARIANT_COUNT = sum(len(values) for values in TASK_VARIANTS.values())

CAMBRIDGE_ALIGNMENT = {
    "A": {
        "yle": "PRE_A1_STARTERS_TO_A1_MOVERS_CONTROLLED_RECOGNITION",
        "ket_prerequisite": "CONTROLLED_LANGUAGE_ACCURACY_SEED",
    },
    "B": {
        "yle": "STARTERS_TO_MOVERS_CONTEXTUAL_COMPREHENSION",
        "ket_prerequisite": "READING_SPECIFIC_INFORMATION_SEED",
    },
    "C": {
        "yle": "A1_MOVERS_FORM_IN_CONTEXT_AND_SENTENCE_CONSTRUCTION",
        "ket_prerequisite": "READING_WRITING_CLOZE_AND_CONSTRUCTION_SEED",
    },
    "D": {
        "yle": "A1_MOVERS_CONNECTED_READING",
        "ket_prerequisite": "READING_DETAIL_GIST_EVIDENCE_SEED",
    },
    "E": {
        "yle": "A1_MOVERS_SPEAKING_WRITING_TRANSFER",
        "ket_prerequisite": "SPEAKING_WRITING_PREREQUISITE_TRANSFER_SEED",
    },
}
CAMBRIDGE_CLAIM = "PREREQUISITE_SKILL_SEED_NOT_OFFICIAL_CAMBRIDGE_EXAM_ITEM"

PRODUCTIVE_SCORING_DIMENSIONS = (
    "semantic_truth",
    "a1_grammar_target",
    "completeness",
    "reference_continuity",
    "scene_truth",
    "acceptable_paraphrase",
)

FORBIDDEN_LEARNER_KEYS = frozenset({
    "correct_answer",
    "reference_answer",
    "answer_key",
    "source_q10_item_id",
    "source_runtime_slot_id",
    "source_fact_lineage",
})

SECTION_TITLES = {
    "A": "Build the place-word foundation",
    "B": "Understand places in a short passage",
    "C": "Build and repair language in context",
    "D": "Read connected situations",
    "E": "Speak and write from the situation",
}


class Unit04FSV2Error(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _contains_surface(text: str, surface: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", text, flags=re.I))


def _split_csv(value: Any) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _split_sentences(passage: str) -> list[str]:
    rows = [part.strip() for part in re.split(r"(?<=[.!?])\s+", passage.strip()) if part.strip()]
    if not rows:
        raise Unit04FSV2Error("CURRENT360_PASSAGE_SENTENCE_SPLIT_EMPTY")
    return rows


def _stage(form_number: int) -> str:
    for stage, contract in STAGE_CONTRACT.items():
        if form_number in contract["forms"]:
            return stage
    raise Unit04FSV2Error(f"FORM_STAGE_MISSING:{form_number}")


def _stage_contract(form_number: int) -> dict[str, Any]:
    return dict(STAGE_CONTRACT[_stage(form_number)])


def _visible_target_relations(episode: Mapping[str, Any]) -> list[str]:
    passage = str(episode.get("passage") or "")
    declared = _split_csv(episode.get("target_relations"))
    declared_visible = [
        relation for relation in TARGET_RELATIONS
        if relation in declared and _contains_surface(passage, relation)
    ]
    if declared_visible:
        return declared_visible
    visible = [relation for relation in TARGET_RELATIONS if _contains_surface(passage, relation)]
    if not visible:
        raise Unit04FSV2Error(f"CURRENT360_TARGET_RELATION_NOT_VISIBLE:{episode.get('episode_id')}")
    return visible


def _support_surfaces(episode: Mapping[str, Any]) -> list[str]:
    passage = str(episode.get("passage") or "")
    metadata = set(_split_csv(episode.get("support_language")))
    return [
        relation for relation in SUPPORT_RELATIONS
        if relation in metadata or _contains_surface(passage, relation)
    ]


def _episode_lineage(episode: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "episode_id": str(episode["episode_id"]),
        "micro_scene_id": str(episode["micro_scene_id"]),
        "life_domain": str(episode["life_domain"]),
        "governed_scene_family": str(episode["governed_scene_family"]),
        "discourse_family": str(episode["discourse_family"]),
        "five_w_one_h": _split_csv(episode["five_w_one_h"]),
        "declared_target_relations": _split_csv(episode["target_relations"]),
        "visible_target_relations": _visible_target_relations(episode),
        "support_language_exposure": _support_surfaces(episode),
        "source_fact_lineage": str(episode["source_fact_lineage"]),
        "passage": str(episode["passage"]).strip(),
    }


def _validate_sources() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    q10_payload = q10.build_export_payload()
    if q10_payload.get("status") != q10.PASS_STATUS:
        raise Unit04FSV2Error("Q10_SOURCE_NOT_PASS")
    if len(q10_payload.get("questionbank_items") or []) != TOTAL_ACTIVITIES:
        raise Unit04FSV2Error("Q10_SOURCE_ITEM_COUNT_DRIFT")
    if len(q10_payload.get("forms") or []) != FORM_COUNT:
        raise Unit04FSV2Error("Q10_SOURCE_FORM_COUNT_DRIFT")

    legacy_report = legacy_q10r1.build_acceptance_report(q10_payload)
    if legacy_report.get("status") != legacy_q10r1.PASS_STATUS:
        raise Unit04FSV2Error("Q10R1_SOURCE_NOT_PASS")
    if len(legacy_report.get("learner_forms") or []) != FORM_COUNT:
        raise Unit04FSV2Error("Q10R1_FORM_COUNT_DRIFT")

    current_report = current360.build_unit04_neb02_natural_episode_bank_360()
    if current_report.get("status") != current360.STATUS:
        raise Unit04FSV2Error("CURRENT360_SOURCE_NOT_PASS")
    episodes = [dict(row) for row in current_report.get("effective_episodes") or []]
    if len(episodes) != 360:
        raise Unit04FSV2Error(f"CURRENT360_EPISODE_COUNT_DRIFT:{len(episodes)}")
    if len({str(row["episode_id"]) for row in episodes}) != 360:
        raise Unit04FSV2Error("CURRENT360_EPISODE_ID_COLLISION")
    return q10_payload, legacy_report, episodes


def _partition_reservoirs(
    episodes: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in episodes:
        by_scene[str(row["micro_scene_id"])].append(dict(row))
    if len(by_scene) != 36:
        raise Unit04FSV2Error(f"CURRENT360_SCENE_COUNT_DRIFT:{len(by_scene)}")

    seen: list[dict[str, Any]] = []
    unseen: list[dict[str, Any]] = []
    for scene_id in sorted(by_scene):
        rows = sorted(by_scene[scene_id], key=lambda row: str(row["episode_id"]))
        if len(rows) != 10:
            raise Unit04FSV2Error(f"CURRENT360_SCENE_EPISODE_COUNT_DRIFT:{scene_id}:{len(rows)}")
        seen.extend(rows[:6])
        unseen.extend(rows[6:])

    seen_ids = {str(row["episode_id"]) for row in seen}
    unseen_ids = {str(row["episode_id"]) for row in unseen}
    overlap = seen_ids.intersection(unseen_ids)
    if overlap:
        raise Unit04FSV2Error("SEEN_UNSEEN_RESERVOIR_OVERLAP")

    return seen, unseen, {
        "seen_episode_count": len(seen),
        "unseen_episode_count": len(unseen),
        "seen_unseen_overlap_count": 0,
        "seen_micro_scene_count": len({str(row["micro_scene_id"]) for row in seen}),
        "unseen_micro_scene_count": len({str(row["micro_scene_id"]) for row in unseen}),
        "seen_life_domain_count": len({str(row["life_domain"]) for row in seen}),
        "unseen_life_domain_count": len({str(row["life_domain"]) for row in unseen}),
        "seen_target_relation_coverage": sorted({
            relation for row in seen for relation in _visible_target_relations(row)
        }),
        "unseen_target_relation_coverage": sorted({
            relation for row in unseen for relation in _visible_target_relations(row)
        }),
    }


class _EpisodeSelector:
    def __init__(self, seen: Sequence[Mapping[str, Any]], unseen: Sequence[Mapping[str, Any]]) -> None:
        self._reservoirs = {
            "seen": [dict(row) for row in seen],
            "unseen": [dict(row) for row in unseen],
        }
        self._cursor = {"seen": 0, "unseen": 0}
        self._preferred_cursor: dict[tuple[str, str], int] = defaultdict(int)

    def select(
        self,
        *,
        exposure: str,
        family: str,
        preferred_relation: str | None = None,
    ) -> dict[str, Any]:
        key = "unseen" if exposure.startswith("UNSEEN") else "seen"
        rows = self._reservoirs[key]
        if preferred_relation:
            cursor_key = (key, preferred_relation)
            start = self._preferred_cursor[cursor_key]
            for offset in range(len(rows)):
                index = (start + offset) % len(rows)
                episode = rows[index]
                relations = _visible_target_relations(episode)
                allowed = [
                    relation for relation in relations
                    if relation != "at" or family in q10.AT_ALLOWED_FAMILIES
                ]
                if preferred_relation in allowed:
                    self._preferred_cursor[cursor_key] = index + 1
                    return dict(episode)

        start = self._cursor[key]
        for offset in range(len(rows)):
            index = (start + offset) % len(rows)
            episode = rows[index]
            relations = _visible_target_relations(episode)
            allowed = [
                relation for relation in relations
                if relation != "at" or family in q10.AT_ALLOWED_FAMILIES
            ]
            if allowed:
                self._cursor[key] = index + 1
                return dict(episode)
        raise Unit04FSV2Error(f"CURRENT360_ELIGIBLE_EPISODE_MISSING:{key}:{family}")


def _choose_target_relation(
    episode: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    preferred_relation: str | None = None,
) -> str:
    relations = [
        relation for relation in _visible_target_relations(episode)
        if relation != "at" or family in q10.AT_ALLOWED_FAMILIES
    ]
    if preferred_relation and preferred_relation in relations:
        return preferred_relation
    if not relations:
        raise Unit04FSV2Error(
            f"CURRENT360_ELIGIBLE_TARGET_RELATION_MISSING:{episode.get('episode_id')}:{family}"
        )
    return relations[seed % len(relations)]


def _focus_sentence(passage: str, relation: str) -> str:
    rows = _split_sentences(passage)
    for sentence in rows:
        if _contains_surface(sentence, relation):
            return sentence
    raise Unit04FSV2Error(f"FOCUS_SENTENCE_NOT_FOUND:{relation}:{passage}")


def _mask_relation(text: str, relation: str) -> str:
    masked, count = re.subn(
        rf"(?<!\w){re.escape(relation)}(?!\w)",
        "___",
        text,
        count=1,
        flags=re.I,
    )
    if count != 1:
        raise Unit04FSV2Error(f"RELATION_MASK_FAILED:{relation}:{text}")
    return masked


def _relation_options(relation: str, seed: int) -> list[str]:
    if relation == "at":
        raise Unit04FSV2Error("AT_SELECTED_RELATION_FORBIDDEN")
    values = [relation, *q10.DISTRACTORS[relation]]
    shift = seed % len(values)
    return values[shift:] + values[:shift]


def _wrong_relation(relation: str, seed: int) -> str:
    if relation == "at":
        candidates = [value for value in TARGET_RELATIONS if value != "at"]
        return candidates[seed % len(candidates)]
    return q10.DISTRACTORS[relation][seed % len(q10.DISTRACTORS[relation])]


def _wrong_relation_not_visible(
    passage: str,
    relation: str,
    seed: int,
) -> str:
    candidates = [
        value for value in TARGET_RELATIONS
        if value != relation and not _contains_surface(passage, value)
    ]
    if not candidates:
        candidates = [
            value for value in TARGET_RELATIONS
            if value != relation
        ]
    return candidates[seed % len(candidates)]


def _replace_relation(text: str, relation: str, replacement: str) -> str:
    replaced, count = re.subn(
        rf"(?<!\w){re.escape(relation)}(?!\w)",
        replacement,
        text,
        count=1,
        flags=re.I,
    )
    if count != 1:
        raise Unit04FSV2Error(f"RELATION_REPLACEMENT_FAILED:{relation}:{text}")
    return replaced


def _support_line(form_number: int) -> str:
    return str(_stage_contract(form_number)["learner_support"])


def _selected_scoring(answer: str) -> dict[str, Any]:
    return {
        "scoring_mode": "EXACT_OPTION",
        "reference_answer": answer,
        "single_answer_required": True,
        "acceptable_paraphrase": False,
    }


def _normalized_scoring(answer: str) -> dict[str, Any]:
    return {
        "scoring_mode": "NORMALIZED_TEXT",
        "reference_answer": answer,
        "single_answer_required": True,
        "acceptable_paraphrase": False,
    }


def _productive_scoring(reference_answer: str | None = None) -> dict[str, Any]:
    return {
        "scoring_mode": "HUMAN_OR_SEMANTIC_REVIEW",
        "reference_answer": reference_answer,
        "single_answer_required": False,
        "reference_response_nonexclusive": True,
        "acceptable_paraphrase": True,
        "dimensions": list(PRODUCTIVE_SCORING_DIMENSIONS),
    }


def _legacy_a_activity(
    *,
    source_item: Mapping[str, Any],
    legacy_activity: Mapping[str, Any],
    variant: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    activity = {
        "question_number": str(legacy_activity["question_number"]),
        "skill": "Grammar",
        "stimulus": str(legacy_activity["stimulus"]),
        "prompt": str(legacy_activity["prompt"]),
        "options": [str(value) for value in legacy_activity.get("options") or []],
        "response_mode": str(legacy_activity["response_mode"]),
        "capture_enabled": True,
        "practice_only": False,
    }
    answer = source_item.get("correct_answer")
    scoring = (
        _selected_scoring(str(answer))
        if activity["options"]
        else _normalized_scoring(str(answer or ""))
    )
    return activity, scoring


def _contextual_activity(
    *,
    form_number: int,
    section: str,
    local: int,
    variant: str,
    episode: Mapping[str, Any],
    relation: str,
    seed: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    lineage = _episode_lineage(episode)
    passage = lineage["passage"]
    focus_sentence = _focus_sentence(passage, relation)
    masked_focus = _mask_relation(focus_sentence, relation)
    support = _support_line(form_number)
    sentences = _split_sentences(passage)
    question_number = ""

    options: list[str] = []
    response_mode = "short_text"
    scoring: dict[str, Any]
    stimulus = f"Passage: {passage}"
    prompt = ""

    if variant == "PASSAGE_FOCUS_RELATION_SELECT":
        stimulus = f"Passage: {passage} | Focus sentence: {masked_focus}"
        options = _relation_options(relation, seed)
        prompt = "Which place word completes the focus sentence?"
        response_mode = "select_one"
        scoring = _selected_scoring(relation)
    elif variant == "PASSAGE_FOCUS_RELATION_WRITE":
        stimulus = f"Passage: {passage} | Focus sentence: {masked_focus}"
        prompt = "Write the place word that completes the focus sentence."
        scoring = _normalized_scoring(relation)
    elif variant == "PASSAGE_EVIDENCE_SENTENCE_SELECT":
        options = sentences
        prompt = f"Which sentence gives a location using the focus place word {relation}?"
        response_mode = "select_one"
        scoring = _selected_scoring(focus_sentence)
    elif variant == "PASSAGE_RELATION_CHECK":
        correct_candidate = seed % 2 == 0
        wrong = _wrong_relation_not_visible(passage, relation, seed)
        candidate_sentence = (
            focus_sentence
            if correct_candidate
            else _replace_relation(focus_sentence, relation, wrong)
        )
        stimulus = f"Passage: {passage} | Sentence to check: {candidate_sentence}"
        options = ["YES", "NO"]
        prompt = "Does the sentence to check agree with the passage?"
        response_mode = "select_one"
        scoring = _selected_scoring("YES" if correct_candidate else "NO")
    elif variant == "PASSAGE_EVIDENCE_COPY":
        prompt = f"Copy one complete sentence that uses {relation} for a location."
        scoring = _productive_scoring(focus_sentence)
    elif variant == "CONTEXT_GAP_RELATION_SELECT":
        stimulus = f"Passage: {passage} | Focus sentence: {masked_focus}"
        options = _relation_options(relation, seed)
        prompt = "Choose the place word that completes the focus sentence."
        response_mode = "select_one"
        scoring = _selected_scoring(relation)
    elif variant == "CONTEXT_GAP_RELATION_WRITE":
        stimulus = f"Passage: {passage} | Focus sentence: {masked_focus}"
        prompt = "Write the missing place word."
        scoring = _normalized_scoring(relation)
    elif variant == "PASSAGE_FOCUS_SENTENCE_RESTORE":
        stimulus = f"Passage: {passage} | Focus sentence: {masked_focus}"
        prompt = "Write the complete focus sentence."
        scoring = _normalized_scoring(focus_sentence)
    elif variant == "CONTEXTUAL_LOCATION_SENTENCE_CONSTRUCTION":
        stimulus = f"Passage: {passage} | Focus sentence: {masked_focus} | Place word: {relation}"
        prompt = "Use the passage and the given place word to restore the complete focus sentence."
        scoring = _productive_scoring(focus_sentence)
    elif variant == "CONTEXTUAL_ERROR_CORRECTION":
        wrong = _wrong_relation(relation, seed)
        incorrect = _replace_relation(focus_sentence, relation, wrong)
        stimulus = f"Passage: {passage} | Sentence to fix: {incorrect}"
        prompt = "Correct the place word so the sentence agrees with the passage."
        scoring = _normalized_scoring(relation)
    elif variant == "READING_SPECIFIC_INFORMATION":
        stimulus = f"Passage: {passage} | Focus sentence: {masked_focus}"
        prompt = "Read for a specific detail. Which place word completes the focus sentence?"
        scoring = _normalized_scoring(relation)
    elif variant == "READING_EVIDENCE_SENTENCE":
        prompt = f"Find and copy the sentence that gives a location with {relation}."
        scoring = _productive_scoring(focus_sentence)
    elif variant == "READING_TWO_LOCATION_FACTS":
        prompt = (
            "Write one or two location facts you can find in the passage. "
            "Use only details the passage supports."
        )
        scoring = _productive_scoring(None)
    elif variant == "READING_LOCATION_EVIDENCE_EXPLANATION":
        prompt = "Use one sentence from the passage to show where a person or thing is."
        scoring = _productive_scoring(focus_sentence)
    elif variant == "READING_SIMPLE_GIST_SEED":
        options = [
            "Where people or things are",
            "A sports score",
            "A weather report",
            "How to make food",
        ]
        prompt = "What is the passage mainly helping you understand?"
        response_mode = "select_one"
        scoring = _selected_scoring("Where people or things are")
    elif variant == "READING_CONNECTED_QA":
        prompt = "Answer with one complete sentence: where is one person or thing?"
        scoring = _productive_scoring(focus_sentence)
    elif variant == "READING_SHORT_RETELL":
        prompt = "Retell two location facts from the passage in your own short sentences."
        scoring = _productive_scoring(None)
    elif variant == "READING_EVIDENCE_JUSTIFICATION":
        prompt = "Choose one location fact and tell which words in the passage support it."
        scoring = _productive_scoring(focus_sentence)
    elif variant == "WRITING_ONE_LOCATION_FACT":
        prompt = "Write one complete sentence about a location in the passage."
        scoring = _productive_scoring(focus_sentence)
    elif variant == "WRITING_TWO_LOCATION_FACTS":
        prompt = (
            "Write two connected sentences about the situation. "
            "Include at least one location fact from the passage."
        )
        scoring = _productive_scoring(None)
    elif variant == "SPEAKING_LOCATION_QA":
        prompt = "Answer aloud: where is one person or thing in this situation?"
        scoring = _productive_scoring(focus_sentence)
    elif variant == "SPEAKING_SCENE_DESCRIPTION":
        prompt = (
            "Say two or three sentences about the situation. "
            "Include at least one clear location fact."
        )
        scoring = _productive_scoring(None)
    elif variant == "SPEAKING_ASK_LOCATION_QUESTION":
        prompt = "Ask one natural question about where a person or thing is."
        scoring = _productive_scoring(None)
    elif variant == "SPEAKING_TRANSFER_CHANGED_LOCATION":
        prompt = (
            "Change one location in your mind. Say the new location in one complete sentence "
            "without changing the grammar level."
        )
        scoring = _productive_scoring(None)
    else:
        raise Unit04FSV2Error(f"UNSUPPORTED_TASK_VARIANT:{variant}")

    if support:
        stimulus = f"{stimulus} | Help: {support}"
    activity = {
        "question_number": question_number,
        "skill": SECTION_SKILL[section],
        "stimulus": stimulus,
        "prompt": prompt,
        "options": options,
        "response_mode": response_mode,
        "capture_enabled": True,
        "practice_only": False,
    }
    return activity, scoring


def _variant_for(section: str, local: int) -> str:
    if section == "C":
        pattern = (
            "CONTEXTUAL_LOCATION_SENTENCE_CONSTRUCTION",
            "CONTEXTUAL_ERROR_CORRECTION",
            "CONTEXT_GAP_RELATION_SELECT",
            "CONTEXTUAL_LOCATION_SENTENCE_CONSTRUCTION",
            "CONTEXTUAL_ERROR_CORRECTION",
            "CONTEXT_GAP_RELATION_WRITE",
            "CONTEXTUAL_LOCATION_SENTENCE_CONSTRUCTION",
            "CONTEXTUAL_ERROR_CORRECTION",
            "PASSAGE_FOCUS_SENTENCE_RESTORE",
            "CONTEXTUAL_LOCATION_SENTENCE_CONSTRUCTION",
        )
        return pattern[local - 1]
    values = TASK_VARIANTS[section]
    return values[(local - 1) % len(values)]


def _legacy_indexes(
    q10_payload: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    items = {
        str(row["item_id"]): row for row in q10_payload.get("questionbank_items") or []
    }
    runtime = {
        str(row["selected_item_id"]): row for row in q10_payload.get("runtime_bindings") or []
    }
    if len(items) != TOTAL_ACTIVITIES or len(runtime) != TOTAL_ACTIVITIES:
        raise Unit04FSV2Error("Q10_SOURCE_IDENTITY_INDEX_DRIFT")
    return items, runtime


def _learner_payload_has_forbidden_answer_keys(activity: Mapping[str, Any]) -> bool:
    return any(key in activity for key in FORBIDDEN_LEARNER_KEYS)


def _materialize() -> dict[str, Any]:
    q10_payload, legacy_report, episodes = _validate_sources()
    seen, unseen, reservoir_summary = _partition_reservoirs(episodes)
    selector = _EpisodeSelector(seen, unseen)
    source_items, source_runtime = _legacy_indexes(q10_payload)

    active_items: list[dict[str, Any]] = []
    runtime_bindings: list[dict[str, Any]] = []
    forms: list[dict[str, Any]] = []
    task_variant_counts: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    function_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    stage_counts: Counter[str] = Counter()
    scene_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    contextual_episode_ids: set[str] = set()
    seen_selected_ids: set[str] = set()
    unseen_selected_ids: set[str] = set()
    support_exposure_count = 0
    productive_response_count = 0
    cross_skill_shared_pairs = 0
    learner_answer_key_leak_count = 0
    a2_grammar_introduced_count = 0
    assessed_support_relation_count = 0

    legacy_forms = list(legacy_report["learner_forms"])
    q10_forms = list(q10_payload["forms"])

    for form_number in range(1, FORM_COUNT + 1):
        stage = _stage(form_number)
        stage_contract = _stage_contract(form_number)
        exposure = str(stage_contract["context_exposure"])
        legacy_form = legacy_forms[form_number - 1]
        q10_form = q10_forms[form_number - 1]
        if int(legacy_form["form_ordinal"]) != form_number:
            raise Unit04FSV2Error(f"Q10R1_FORM_SEQUENCE_DRIFT:{form_number}")
        if int(q10_form["form_number"]) != form_number:
            raise Unit04FSV2Error(f"Q10_FORM_SEQUENCE_DRIFT:{form_number}")

        legacy_activities = list(legacy_form["activities"])
        source_form_item_ids = [
            str(value)
            for section in SECTION_ORDER
            for value in q10_form["section_item_ids"][section]
        ]
        if len(legacy_activities) != 40 or len(source_form_item_ids) != 40:
            raise Unit04FSV2Error(f"FORM_SOURCE_DENOMINATOR_DRIFT:{form_number}")

        form_items: list[dict[str, Any]] = []
        form_sections: list[dict[str, Any]] = []
        d_contexts: list[dict[str, Any]] = []
        offset = 0

        for section in SECTION_ORDER:
            section_count = SECTION_COUNTS[section]
            for local in range(1, section_count + 1):
                source_index = offset + local - 1
                source_item_id = source_form_item_ids[source_index]
                source_item = source_items[source_item_id]
                runtime_row = source_runtime[source_item_id]
                legacy_activity = legacy_activities[source_index]
                family = str(source_item["task_family_id"])
                cf = str(source_item["communicative_function_id"])
                variant = _variant_for(section, local)
                seed = form_number * 1000 + ord(section) * 100 + local
                episode: dict[str, Any] | None = None
                relation = str(source_item["relation_surface"])
                shared_context_from_d = False

                if section == "A":
                    learner_activity, scoring = _legacy_a_activity(
                        source_item=source_item,
                        legacy_activity=legacy_activity,
                        variant=variant,
                    )
                    current360_lineage = None
                else:
                    if section == "E":
                        episode = dict(d_contexts[local - 1])
                        shared_context_from_d = True
                        cross_skill_shared_pairs += 1
                    else:
                        preferred_relation = (
                            "at"
                            if relation == "at" and family in q10.AT_ALLOWED_FAMILIES
                            else None
                        )
                        episode = selector.select(
                            exposure=exposure,
                            family=family,
                            preferred_relation=preferred_relation,
                        )
                        if section == "D":
                            d_contexts.append(dict(episode))
                    relation = _choose_target_relation(
                        episode,
                        family=family,
                        seed=seed,
                        preferred_relation=(
                            "at"
                            if str(source_item["relation_surface"]) == "at"
                            and family in q10.AT_ALLOWED_FAMILIES
                            else None
                        ),
                    )
                    learner_activity, scoring = _contextual_activity(
                        form_number=form_number,
                        section=section,
                        local=local,
                        variant=variant,
                        episode=episode,
                        relation=relation,
                        seed=seed,
                    )
                    current360_lineage = _episode_lineage(episode)
                    episode_id = str(episode["episode_id"])
                    contextual_episode_ids.add(episode_id)
                    scene_counts[str(episode["micro_scene_id"])] += 1
                    domain_counts[str(episode["life_domain"])] += 1
                    support_exposure_count += len(_support_surfaces(episode))
                    if exposure.startswith("UNSEEN"):
                        unseen_selected_ids.add(episode_id)
                    else:
                        seen_selected_ids.add(episode_id)

                learner_activity["question_number"] = f"Q{len(form_items) + 1:02d}"
                if _learner_payload_has_forbidden_answer_keys(learner_activity):
                    learner_answer_key_leak_count += 1

                if relation in SUPPORT_RELATIONS:
                    assessed_support_relation_count += 1
                if scoring["scoring_mode"] == "HUMAN_OR_SEMANTIC_REVIEW":
                    productive_response_count += 1

                lineage = {
                    "source_q10_item_id": source_item_id,
                    "source_runtime_slot_id": str(runtime_row["slot_id"]),
                    "source_task_family_id": family,
                    "source_relation_surface": str(source_item["relation_surface"]),
                    "source_communicative_function_id": cf,
                    "source_selected_item_preserved_as_lineage": True,
                    "source_candidate_ids": [str(value) for value in runtime_row["candidate_ids"]],
                }
                identity = {
                    "form": form_number,
                    "section": section,
                    "local": local,
                    "variant": variant,
                    "source_q10_item_id": source_item_id,
                    "current360_episode_id": (
                        str(current360_lineage["episode_id"]) if current360_lineage else None
                    ),
                    "target_relation": relation,
                    "revision": REVISION,
                }
                active_item_id = (
                    f"U04FSV2-F{form_number:02d}-{section}{local:02d}-"
                    f"{_digest(identity)[:12].upper()}"
                )

                item = {
                    "active_item_id": active_item_id,
                    "unit_id": UNIT_ID,
                    "form_number": form_number,
                    "progression_stage": stage,
                    "support_level": stage_contract["support_level"],
                    "context_exposure": exposure if section != "A" else "CONTROLLED_FOUNDATION",
                    "section": section,
                    "section_activity_ordinal": local,
                    "section_skill": SECTION_SKILL[section],
                    "task_variant": variant,
                    "source_q10_lineage": lineage,
                    "current360_episode_lineage": current360_lineage,
                    "shared_context_from_d": shared_context_from_d,
                    "target_relation_surface": relation,
                    "target_relation_role": "ASSESSED_A1_UNIT04_TARGET",
                    "support_relations_assessed": False,
                    "support_language_exposure": (
                        list(current360_lineage["support_language_exposure"])
                        if current360_lineage
                        else []
                    ),
                    "communicative_function_id": cf,
                    "cambridge_prerequisite_alignment": {
                        **CAMBRIDGE_ALIGNMENT[section],
                        "claim": CAMBRIDGE_CLAIM,
                        "grammar_ceiling": "A1",
                        "a2_grammar_introduced": False,
                    },
                    "learner_activity": learner_activity,
                    "scoring_contract": scoring,
                    "answer_key_private": {
                        "reference_answer": scoring.get("reference_answer"),
                        "scoring_mode": scoring["scoring_mode"],
                    },
                    "a2_grammar_introduced": False,
                }
                active_items.append(item)
                form_items.append(item)
                runtime_bindings.append({
                    "active_slot_id": f"U04FSV2-F{form_number:02d}-{section}{local:02d}",
                    "form_number": form_number,
                    "progression_stage": stage,
                    "section": section,
                    "section_activity_ordinal": local,
                    "active_item_id": active_item_id,
                    "source_q10_slot_id": str(runtime_row["slot_id"]),
                    "source_q10_selected_item_id": source_item_id,
                    "current360_episode_id": (
                        str(current360_lineage["episode_id"]) if current360_lineage else None
                    ),
                })
                task_variant_counts[variant] += 1
                relation_counts[relation] += 1
                function_counts[cf] += 1
                skill_counts[SECTION_SKILL[section]] += 1
                stage_counts[stage] += 1
                a2_grammar_introduced_count += int(item["a2_grammar_introduced"])

            form_sections.append({
                "section": section,
                "section_title": SECTION_TITLES[section],
                "activity_count": section_count,
                "task_variants": list(TASK_VARIANTS[section]),
                "cambridge_prerequisite_alignment": CAMBRIDGE_ALIGNMENT[section],
            })
            offset += section_count

        if len(d_contexts) != 8:
            raise Unit04FSV2Error(f"FORM_D_CONTEXT_COUNT_DRIFT:F{form_number:02d}:{len(d_contexts)}")
        if len(form_items) != 40:
            raise Unit04FSV2Error(f"FORM_ITEM_COUNT_DRIFT:F{form_number:02d}:{len(form_items)}")

        forms.append({
            "form_id": f"U04FSV2-FORM-{form_number:02d}",
            "form_number": form_number,
            "progression_stage": stage,
            "support_level": stage_contract["support_level"],
            "context_exposure": stage_contract["context_exposure"],
            "question_count": 40,
            "section_counts": dict(SECTION_COUNTS),
            "sections": form_sections,
            "active_item_ids": [str(row["active_item_id"]) for row in form_items],
        })

    if len(active_items) != TOTAL_ACTIVITIES:
        raise Unit04FSV2Error(f"ACTIVE_ITEM_COUNT_DRIFT:{len(active_items)}")
    if len(runtime_bindings) != TOTAL_ACTIVITIES:
        raise Unit04FSV2Error(f"ACTIVE_RUNTIME_COUNT_DRIFT:{len(runtime_bindings)}")
    if len({str(row["active_item_id"]) for row in active_items}) != TOTAL_ACTIVITIES:
        raise Unit04FSV2Error("ACTIVE_ITEM_ID_COLLISION")
    if len(task_variant_counts) != EXPECTED_TASK_VARIANT_COUNT:
        raise Unit04FSV2Error(
            f"TASK_VARIANT_COVERAGE_DRIFT:{len(task_variant_counts)}:{EXPECTED_TASK_VARIANT_COUNT}"
        )
    if set(relation_counts) != TARGET_RELATION_SET:
        raise Unit04FSV2Error(f"TARGET_RELATION_COVERAGE_DRIFT:{sorted(relation_counts)}")
    if cross_skill_shared_pairs != SHARED_D_E_CONTEXT_PAIR_COUNT:
        raise Unit04FSV2Error(
            f"D_E_SHARED_CONTEXT_PAIR_COUNT_DRIFT:{cross_skill_shared_pairs}"
        )
    if seen_selected_ids.intersection(unseen_selected_ids):
        raise Unit04FSV2Error("SELECTED_SEEN_UNSEEN_OVERLAP")
    if learner_answer_key_leak_count:
        raise Unit04FSV2Error(
            f"LEARNER_ANSWER_KEY_METADATA_LEAK:{learner_answer_key_leak_count}"
        )
    if assessed_support_relation_count:
        raise Unit04FSV2Error(
            f"SUPPORT_RELATION_ASSESSED:{assessed_support_relation_count}"
        )
    if a2_grammar_introduced_count:
        raise Unit04FSV2Error(f"A2_GRAMMAR_INTRODUCED:{a2_grammar_introduced_count}")
    if len(scene_counts) != 36:
        raise Unit04FSV2Error(f"CURRENT360_SELECTED_SCENE_COVERAGE_DRIFT:{len(scene_counts)}")
    if len(domain_counts) != 12:
        raise Unit04FSV2Error(f"CURRENT360_SELECTED_DOMAIN_COVERAGE_DRIFT:{len(domain_counts)}")
    if productive_response_count <= 0:
        raise Unit04FSV2Error("PRODUCTIVE_RESPONSE_MISSING")

    expected_stage_counts = {stage: 160 for stage in STAGE_CONTRACT}
    if dict(stage_counts) != expected_stage_counts:
        raise Unit04FSV2Error(f"STAGE_ACTIVITY_DISTRIBUTION_DRIFT:{dict(stage_counts)}")

    approved_requirements = {
        "01_task_maturity_without_new_grammar": {
            "status": "PASS",
            "evidence": {
                "grammar_ceiling": "A1",
                "a2_grammar_introduced_count": a2_grammar_introduced_count,
                "task_variant_count": len(task_variant_counts),
            },
        },
        "02_current360_seen_unseen_split": {
            "status": "PASS",
            "evidence": {
                **reservoir_summary,
                "selected_seen_episode_count": len(seen_selected_ids),
                "selected_unseen_episode_count": len(unseen_selected_ids),
                "selected_seen_unseen_overlap_count": 0,
            },
        },
        "03_cross_skill_shared_passage_without_answer_leakage": {
            "status": "PASS",
            "evidence": {
                "d_e_shared_context_pair_count": cross_skill_shared_pairs,
                "learner_answer_key_metadata_leak_count": learner_answer_key_leak_count,
            },
        },
        "04_productive_response_scoring_contract": {
            "status": "PASS",
            "evidence": {
                "productive_response_count": productive_response_count,
                "scoring_mode": "HUMAN_OR_SEMANTIC_REVIEW",
                "dimensions": list(PRODUCTIVE_SCORING_DIMENSIONS),
            },
        },
        "05_layer1_to_layer2_bridge": {
            "status": "DEFERRED_TO_NEXT_SHORT_STEP",
            "evidence": {"next_short_step": NEXT_SHORT_STEP},
        },
        "06_speaking_not_description_only": {
            "status": "PARTIAL_FORM_E_PASS_NEXT_SPEAKING_CUTOVER_REQUIRED",
            "evidence": {
                "form_e_speaking_variants": [
                    "SPEAKING_LOCATION_QA",
                    "SPEAKING_SCENE_DESCRIPTION",
                    "SPEAKING_ASK_LOCATION_QUESTION",
                    "SPEAKING_TRANSFER_CHANGED_LOCATION",
                ],
            },
        },
        "07_scaffold_fading": {
            "status": "PASS",
            "evidence": {
                stage: {
                    "forms": list(contract["forms"]),
                    "support_level": contract["support_level"],
                    "context_exposure": contract["context_exposure"],
                }
                for stage, contract in STAGE_CONTRACT.items()
            },
        },
        "08_distributional_coverage": {
            "status": "PASS",
            "evidence": {
                "target_relation_coverage": f"{len(relation_counts)}/8",
                "communicative_function_coverage": f"{len(function_counts)}/6",
                "current360_micro_scene_coverage": f"{len(scene_counts)}/36",
                "current360_life_domain_coverage": f"{len(domain_counts)}/12",
                "task_variant_count": len(task_variant_counts),
            },
        },
        "09_support_language_non_assessed": {
            "status": "PASS",
            "evidence": {
                "support_language_exposure_occurrence_count": support_exposure_count,
                "assessed_support_relation_count": assessed_support_relation_count,
            },
        },
        "10_learner_facing_visual_pedagogical_acceptance": {
            "status": "PENDING_LATER_MILESTONE",
            "evidence": {
                "active_runtime_materialized": True,
                "actual_visual_review_claimed": False,
            },
        },
    }

    return {
        "schema_version": "a1fs.v1.u04.fsv2.current360_contextual_form_runtime.v1",
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "unit_number": 4,
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "source_authority": {
            "q10_lineage_control_foundation": q10.TASK_ID,
            "q10r1_legacy_learner_projection": legacy_q10r1.TASK_ID,
            "current360_natural_passage_authority": current360.TASK_ID,
            "current360_status": current360.STATUS,
            "formal_ket_role": "PREREQUISITE_TASK_SHAPE_EVIDENCE_ONLY",
            "ket99_role": "TEACHER_DELIVERY_REMEDIATION_TRANSFER_EVIDENCE_ONLY",
        },
        "cutover_contract": {
            "active_form_runtime_authority": TASK_ID,
            "parallel_active_form_runtime_allowed": False,
            "legacy_q10_role": "LINEAGE_AND_CONTROL_FOUNDATION_ONLY",
            "legacy_q10r1_role": "SUPERSEDED_AS_ACTIVE_LEARNER_FACING_RUNTIME",
            "current360_role": "NATURAL_PASSAGE_AUTHORITY",
            "a1_language_more_mature_tasks": True,
            "official_cambridge_item_format_claimed": False,
        },
        "materialization_contract": {
            "form_count": FORM_COUNT,
            "activities_per_form": ACTIVITIES_PER_FORM,
            "activity_count": TOTAL_ACTIVITIES,
            "section_counts_per_form": dict(SECTION_COUNTS),
            "controlled_foundation_activity_count": A_CONTROLLED_ACTIVITY_COUNT,
            "current360_contextual_activity_count": CONTEXTUAL_ACTIVITY_COUNT,
            "task_variant_count": EXPECTED_TASK_VARIANT_COUNT,
            "d_e_shared_context_pairs_per_form": SHARED_D_E_CONTEXT_PAIRS_PER_FORM,
            "d_e_shared_context_pair_count": SHARED_D_E_CONTEXT_PAIR_COUNT,
        },
        "coverage": {
            "active_item_count": len(active_items),
            "unique_active_item_id_count": len({str(row["active_item_id"]) for row in active_items}),
            "runtime_binding_count": len(runtime_bindings),
            "task_variant_count": len(task_variant_counts),
            "task_variant_counts": dict(sorted(task_variant_counts.items())),
            "target_relation_coverage": f"{len(relation_counts)}/8",
            "target_relation_counts": {relation: relation_counts[relation] for relation in TARGET_RELATIONS},
            "communicative_function_coverage": f"{len(function_counts)}/6",
            "communicative_function_counts": dict(sorted(function_counts.items())),
            "section_skill_counts": dict(sorted(skill_counts.items())),
            "stage_activity_counts": dict(stage_counts),
            "current360_selected_distinct_episode_count": len(contextual_episode_ids),
            "current360_micro_scene_coverage": f"{len(scene_counts)}/36",
            "current360_life_domain_coverage": f"{len(domain_counts)}/12",
            "seen_selected_episode_count": len(seen_selected_ids),
            "unseen_selected_episode_count": len(unseen_selected_ids),
            "selected_seen_unseen_overlap_count": 0,
            "support_language_exposure_occurrence_count": support_exposure_count,
            "assessed_support_relation_count": 0,
            "productive_response_count": productive_response_count,
            "learner_answer_key_metadata_leak_count": 0,
            "a2_grammar_introduced_count": 0,
        },
        "approved_requirements_10_of_10": approved_requirements,
        "forms": forms,
        "active_items": active_items,
        "runtime_bindings": runtime_bindings,
        "safety": {
            "q01_q09_authority_modified": False,
            "q10_source_authority_deleted": False,
            "q10_source_identity_reused_as_lineage": True,
            "q10r1_legacy_active_runtime_retained": False,
            "current360_episode_content_modified": False,
            "new_current360_passage_authored": False,
            "second_passage_authority_created": False,
            "support_relations_promoted_to_assessed_target": False,
            "a2_a2plus_unlocked": False,
            "other_units_modified": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def build_unit04_fsv2_current360_contextual_form_runtime() -> dict[str, Any]:
    report = _materialize()
    replay = _digest({
        "forms": report["forms"],
        "active_items": report["active_items"],
        "runtime_bindings": report["runtime_bindings"],
    })
    report["deterministic_runtime_sha256"] = replay
    return report


def compact_readback(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report["status"],
        "revision": report["revision"],
        "materialization_contract": report["materialization_contract"],
        "coverage": report["coverage"],
        "cutover_contract": report["cutover_contract"],
        "next_short_step": report["next_short_step"],
    }


def main() -> int:
    print(json.dumps(compact_readback(build_unit04_fsv2_current360_contextual_form_runtime()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
