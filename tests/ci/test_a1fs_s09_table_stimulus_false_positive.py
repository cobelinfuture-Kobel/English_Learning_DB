from __future__ import annotations

import pytest

from ulga.builders import build_a1fs_v1_shared_learner_stimulus_contract_renderer as stimulus


ITEM_ID = "E4S_A1V1_ITEM:GRAMMAR_THERE_IS__TFX_P04"


def test_s09_there_is_gap_prompt_does_not_require_data_table() -> None:
    learner = {
        "prompt": (
            "Complete the sentence or phrase with the missing target form: "
            "There ____ a book on the table."
        ),
        "response_mode": "short_text",
    }
    scoring = {"response_type": "string", "accepted_texts": ["is"]}

    value = stimulus.ensure_learner_contract(
        item_id=ITEM_ID,
        task_type="structured_gap_fill",
        learner=learner,
        scoring=scoring,
    )

    assert value["stimulus_validation"]["answerability_pass"] is True
    assert "TABLE" not in value["stimulus_validation"]["expected_dependency_kinds"]


def test_true_table_instruction_remains_fail_closed_without_payload() -> None:
    learner = {
        "prompt": "Read the table and choose the correct answer.",
        "response_mode": "select_one",
        "options": ["A", "B"],
    }
    scoring = {"response_type": "string", "accepted_texts": ["A"]}

    with pytest.raises(
        stimulus.StimulusContractError,
        match="REQUIRED_STIMULUS_MISSING:TABLE",
    ):
        stimulus.ensure_learner_contract(
            item_id="TRUE_TABLE_WITHOUT_PAYLOAD",
            task_type="context_choice",
            learner=learner,
            scoring=scoring,
        )
