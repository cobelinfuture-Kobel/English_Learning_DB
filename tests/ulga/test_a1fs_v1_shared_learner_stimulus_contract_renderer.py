from __future__ import annotations

import pytest

from ulga.builders import build_a1fs_v1_shared_learner_stimulus_contract_renderer as stimulus


def test_standalone_prompt_is_answerable() -> None:
    learner = {"prompt": "What is your name?", "response_mode": "short_text"}
    scoring = {"response_type": "string", "accepted_texts": ["Sam"]}
    value = stimulus.ensure_learner_contract(
        item_id="standalone", task_type="guided_response",
        learner=learner, scoring=scoring,
    )
    assert value["stimulus_contract"]["answerability_policy"] == "STANDALONE_PROMPT"
    assert value["stimulus_validation"]["answerability_pass"] is True
    assert value["stimulus_render_manifest"] == []


def test_text_dependent_prompt_requires_visible_text() -> None:
    learner = {"prompt": "文本中提到了哪個地點？", "response_mode": "short_text"}
    scoring = {"response_type": "string", "accepted_texts": ["the park"]}
    with pytest.raises(stimulus.StimulusContractError, match="REQUIRED_STIMULUS_MISSING:TEXT"):
        stimulus.ensure_learner_contract(
            item_id="missing-text", task_type="guided_response",
            learner=learner, scoring=scoring,
        )


def test_text_dependent_prompt_preserves_text_in_manifest() -> None:
    learner = {
        "prompt": "文本中提到了哪個地點？",
        "response_mode": "short_text",
        "context": {"source_text": "Mia is at the park."},
    }
    scoring = {"response_type": "string", "accepted_texts": ["the park"]}
    value = stimulus.ensure_learner_contract(
        item_id="text-item", task_type="guided_response",
        learner=learner, scoring=scoring,
    )
    block = value["stimulus_render_manifest"][0]
    assert block["kind"] == "TEXT"
    assert block["renderer_type"] == "TEXT_PASSAGE"
    assert block["payload"] == "Mia is at the park."
    assert value["stimulus_validation"]["answerability_pass"] is True


def test_dialogue_image_table_and_visible_controls_are_classified() -> None:
    learner = {
        "prompt": "Read the dialogue and look at the table.",
        "response_mode": "select_one",
        "context": {
            "dialogue": [{"speaker": "A", "text": "Where is Sam?"}],
            "table": {"headers": ["Name", "Place"], "rows": [["Sam", "Library"]]},
        },
        "options": ["Library", "Park"],
    }
    scoring = {"response_type": "string", "accepted_texts": ["Library"]}
    value = stimulus.ensure_learner_contract(
        item_id="multi", task_type="context_choice",
        learner=learner, scoring=scoring,
    )
    kinds = {row["kind"] for row in value["stimulus_contract"]["dependencies"]}
    assert {"DIALOGUE", "TABLE", "OPTIONS"} <= kinds


def test_audio_deferred_is_not_ready() -> None:
    learner = {
        "prompt": "Listen to the recording and answer.",
        "response_mode": "short_text",
        "context": {"audio_ref": "audio/example.mp3"},
    }
    scoring = {"response_type": "string", "accepted_texts": ["yes"]}
    with pytest.raises(stimulus.StimulusContractError, match="MEDIA_PAYLOAD_DEFERRED"):
        stimulus.ensure_learner_contract(
            item_id="audio", task_type="guided_response",
            learner=learner, scoring=scoring,
            media_payload_state="DEFERRED_MEDIA_PAYLOAD",
        )


def test_hidden_scoring_information_is_forbidden() -> None:
    learner = {"prompt": "Answer the question.", "response_mode": "short_text"}
    scoring = {
        "response_type": "string", "accepted_texts": ["yes"],
        "scoring_may_use_hidden_information": True,
    }
    with pytest.raises(stimulus.StimulusContractError, match="HIDDEN_SCORING_INFORMATION_FORBIDDEN"):
        stimulus.ensure_learner_contract(
            item_id="hidden", task_type="guided_response",
            learner=learner, scoring=scoring,
        )


def test_scan_reports_unanswerable_item_without_shrinking_denominator() -> None:
    report = stimulus.scan_items([
        {
            "item_id": "good",
            "learner_contract": {"prompt": "What is your name?", "response_mode": "short_text"},
            "private_scoring_contract": {"response_type": "string", "accepted_texts": ["Sam"]},
            "media_payload_state": "NOT_REQUIRED",
        },
        {
            "item_id": "bad",
            "learner_contract": {"prompt": "文本中提到了哪個地點？", "response_mode": "short_text"},
            "private_scoring_contract": {"response_type": "string", "accepted_texts": ["park"]},
            "media_payload_state": "NOT_REQUIRED",
        },
    ])
    assert report["counts"]["total_items"] == 2
    assert report["counts"]["ready_for_local_selection"] == 1
    assert report["counts"]["answerability_failed"] == 1
    assert report["counts"]["payload_missing"] == 1
    assert report["failures"][0]["item_id"] == "bad"


def test_shared_javascript_renderer_contains_all_renderer_paths() -> None:
    for renderer in (
        "IMAGE_ASSET", "AUDIO_PLAYER", "OPTION_LIST", "TOKEN_LIST",
        "MORPHEME_LIST", "WORD_BANK", "GAP_DISPLAY",
    ):
        assert renderer in stimulus.JS_RENDERER
    assert "renderA1FSStimulus" in stimulus.JS_RENDERER
