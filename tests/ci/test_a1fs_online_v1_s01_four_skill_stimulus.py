from __future__ import annotations

import json

import pytest

from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population
from ulga.builders import build_a1fs_v1_shared_learner_stimulus_contract_renderer as stimulus


def test_reading_text_and_unseen_text_are_learner_visible_without_private_evidence() -> None:
    context = population._learner_context(
        "READING",
        {
            "text": "Mia reads at the library after school.",
            "rubric": {"text_evidence": "PRIVATE-RUBRIC"},
            "answer_facts": {"article_item": "PRIVATE-ANSWER"},
            "text_attested_examples": ["PRIVATE-EXAMPLE"],
        },
    )
    assert context == {"source_text": "Mia reads at the library after school."}
    assert "PRIVATE" not in json.dumps(context)

    unseen = population._learner_context(
        "READING", {"unseen_text": "Ben takes the bus to school."}
    )
    assert unseen == {"source_text": "Ben takes the bus to school."}


def test_listening_maps_audio_but_does_not_expose_transcript_or_answer_evidence() -> None:
    context = population._learner_context(
        "LISTENING",
        {
            "audio_ref": "private-media://listening/L001",
            "transcript": "Do not expose during listening.",
            "answer_facts": {"answer": "bus"},
        },
    )
    assert context == {"audio_ref": "private-media://listening/L001"}


def test_speaking_and_writing_use_explicit_learner_visible_source_fields() -> None:
    speaking = population._learner_context(
        "SPEAKING",
        {"role_card": "Ask your partner about school.", "image_ref": "asset://school.png"},
    )
    assert speaking == {
        "source_text": "Ask your partner about school.",
        "image_ref": "asset://school.png",
    }

    writing = population._learner_context(
        "WRITING",
        {"source_message": "Can you come to my party on Saturday?", "model_answer": "Yes."},
    )
    assert writing == {"source_text": "Can you come to my party on Saturday?"}


def test_task_projection_routes_reading_text_into_formal_stimulus_contract() -> None:
    asset = {
        "skill": "READING",
        "role": "CHK",
        "payload": {
            "text": "Leo has lunch at school.",
            "options": ["at school", "at home"],
        },
    }
    derived = {
        "scoring_mode": "EXACT_OPTION",
        "prompt": "Where does Leo have lunch?",
        "accepted_texts": ["at school"],
        "case_insensitive": True,
        "punctuation_tolerance": True,
    }
    learner, scoring, *_ = population._task_projection(asset, derived)
    validated = stimulus.ensure_learner_contract(
        item_id="reading-text",
        task_type="select_one",
        learner=learner,
        scoring=scoring,
    )
    assert validated["context"]["source_text"] == "Leo has lunch at school."
    assert validated["stimulus_contract"]["answerability_policy"] == "ALL_REQUIRED_DEPENDENCIES_VISIBLE"
    assert validated["stimulus_validation"]["actual_dependency_kinds"] == ["OPTIONS", "TEXT"]


def test_article_referential_prompt_requires_visible_text() -> None:
    learner = {"prompt": "What is the article about?", "response_mode": "short_text"}
    scoring = {"response_type": "string", "accepted_texts": ["school"]}
    with pytest.raises(stimulus.StimulusContractError, match="REQUIRED_STIMULUS_MISSING:TEXT"):
        stimulus.ensure_learner_contract(
            item_id="article-without-text",
            task_type="guided_response",
            learner=learner,
            scoring=scoring,
        )
