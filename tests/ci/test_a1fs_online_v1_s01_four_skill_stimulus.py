from __future__ import annotations

import json

import pytest

from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population
from ulga.builders import build_a1fs_v1_shared_learner_stimulus_contract_renderer as stimulus
from ulga.builders import build_e4s_a1v1_m12g_learner_contract_assessment_validity_fullfix as assessment


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


def _project_formal_asset(consumer: dict, asset_key: str):
    normalized = population._projection_consumer(consumer)
    asset = next(row for row in normalized["asset_records"] if row["asset_key"] == asset_key)
    derived = m6.derive_contract(asset)
    assert derived["capture_enabled"] is True
    learner, scoring, task_type, *_ = population._task_projection(asset, derived)
    validated_learner, validated_scoring = assessment.validate_learner_contract(
        item_id=asset_key,
        task_type=task_type.casefold(),
        learner=learner,
        scoring=scoring,
    )
    return asset, derived, validated_learner, validated_scoring


def test_listening_formal_asset_inherits_lesson_audio_and_private_review_evidence() -> None:
    consumer = {
        "asset_records": [
            {
                "asset_key": "LISTENING:AUD",
                "lesson_id": "L001",
                "skill": "LISTENING",
                "role": "AUD",
                "payload": {
                    "audio_asset_ref": "private-media://listening/L001",
                    "transcript": "Do not expose during listening.",
                },
            },
            {
                "asset_key": "LISTENING:MOD",
                "lesson_id": "L001",
                "skill": "LISTENING",
                "role": "MOD",
                "payload": {"body_text": "Model reference kept private."},
            },
            {
                "asset_key": "LISTENING:EVD",
                "lesson_id": "L001",
                "skill": "LISTENING",
                "role": "EVD",
                "payload": {
                    "body_title": "Listen and identify the place.",
                    "expected_evidence": "The learner identifies the intended place.",
                },
            },
        ]
    }
    asset, derived, learner, scoring = _project_formal_asset(consumer, "LISTENING:EVD")
    assert derived["scoring_mode"] == "FEATURE_RUBRIC"
    assert learner["context"] == {"audio_ref": "private-media://listening/L001"}
    assert learner["stimulus_validation"]["actual_dependency_kinds"] == ["AUDIO"]
    assert scoring["rubric"]["authority_source"] == "EXISTING_ASSET_BODY_PRIVATE_REVIEW_EVIDENCE"
    assert "Do not expose" not in json.dumps(learner)
    assert "Model reference" not in json.dumps(learner)
    assert "private_scoring_contract" in asset["payload"]


def test_speaking_formal_asset_inherits_lesson_context_and_private_rubric() -> None:
    consumer = {
        "asset_records": [
            {
                "asset_key": "SPEAKING:CTX",
                "lesson_id": "S001",
                "skill": "SPEAKING",
                "role": "CTX",
                "payload": {"body_text": "You are meeting a new classmate."},
            },
            {
                "asset_key": "SPEAKING:EVD",
                "lesson_id": "S001",
                "skill": "SPEAKING",
                "role": "EVD",
                "payload": {"expected_evidence": "The learner asks and answers a personal question."},
            },
            {
                "asset_key": "SPEAKING:PRD",
                "lesson_id": "S001",
                "skill": "SPEAKING",
                "role": "PRD",
                "payload": {"body_title": "Ask your classmate one question."},
            },
        ]
    }
    _asset, derived, learner, scoring = _project_formal_asset(consumer, "SPEAKING:PRD")
    assert derived["prompt"] == "Ask your classmate one question."
    assert learner["context"] == {"source_text": "You are meeting a new classmate."}
    assert scoring["scoring_mode"] == "FEATURE_RUBRIC"
    assert "expected_evidence" in scoring["rubric"]["criteria"]


def test_writing_formal_asset_inherits_source_message_and_private_rubric() -> None:
    consumer = {
        "asset_records": [
            {
                "asset_key": "WRITING:CTX",
                "lesson_id": "W001",
                "skill": "WRITING",
                "role": "CTX",
                "payload": {"body_text": "Sam asks: Can you come to the park?"},
            },
            {
                "asset_key": "WRITING:EVD",
                "lesson_id": "W001",
                "skill": "WRITING",
                "role": "EVD",
                "payload": {"acceptance_rule": "The response answers Sam and gives one detail."},
            },
            {
                "asset_key": "WRITING:PRD",
                "lesson_id": "W001",
                "skill": "WRITING",
                "role": "PRD",
                "payload": {"body_title": "Write a short reply to Sam."},
            },
        ]
    }
    _asset, derived, learner, scoring = _project_formal_asset(consumer, "WRITING:PRD")
    assert derived["prompt"] == "Write a short reply to Sam."
    assert learner["context"] == {"source_text": "Sam asks: Can you come to the park?"}
    assert learner["stimulus_validation"]["actual_dependency_kinds"] == ["TEXT"]
    assert scoring["scoring_mode"] == "FEATURE_RUBRIC"
    assert "acceptance_rule" in scoring["rubric"]["criteria"]


def test_projection_consumer_does_not_promote_nonformal_roles_to_capture_items() -> None:
    consumer = {
        "asset_records": [
            {
                "asset_key": "SPEAKING:CTX",
                "lesson_id": "S002",
                "skill": "SPEAKING",
                "role": "CTX",
                "payload": {
                    "body_text": "A context card.",
                    "expected_evidence": "Private evidence.",
                },
            }
        ]
    }
    normalized = population._projection_consumer(consumer)
    assert normalized["asset_records"][0]["payload"] == consumer["asset_records"][0]["payload"]
    assert "private_scoring_contract" not in normalized["asset_records"][0]["payload"]
