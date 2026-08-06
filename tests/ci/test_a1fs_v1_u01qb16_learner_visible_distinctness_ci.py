from __future__ import annotations

import json

import pytest

from product import a1fs_v1_2_1 as product_package
from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as u16


def _row(item_id: str, stimulus: str, prompt: str, options: list[str], *, skill: str = "READING") -> dict:
    return {
        "item_id": item_id,
        "skill": skill,
        "private_item_json": json.dumps(
            {
                "stimulus": stimulus,
                "prompt": prompt,
                "options": options,
            }
        ),
    }


def test_product_package_installs_u01qb16_over_existing_matching_decision_only() -> None:
    assert product_package is not None
    assert u16.installed() is True
    assert matching.solve_distinct_activity_assignment is u16.solve_learner_visible_distinct_activity_assignment
    assert u16.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert u16.A1FS_CONTENT_POLICY_EXEMPTION


def test_visible_signature_ignores_case_whitespace_and_option_order() -> None:
    first = _row(
        "ITEM-1",
        "There is ___ tree in the park.",
        "Choose the article for the first mention.",
        ["a", "an", "the"],
    )
    second = _row(
        "ITEM-2",
        "  there IS ___ TREE in the park. ",
        "Choose   the article for the first mention.",
        ["the", "a", "an"],
    )
    assert u16.learner_visible_signature(first) == u16.learner_visible_signature(second)


def test_matching_chooses_lower_ranked_item_to_avoid_visible_duplicate() -> None:
    duplicate_a = _row(
        "ITEM-1",
        "There is ___ tree in the park.",
        "Choose the article for the first mention.",
        ["a", "an", "the"],
    )
    unique_a = _row(
        "ITEM-2",
        "There is ___ dog in the park.",
        "Choose the article for the first mention.",
        ["a", "an", "the"],
    )
    duplicate_b = _row(
        "ITEM-3",
        "There is ___ tree in the park.",
        "Choose the article for the first mention.",
        ["a", "an", "the"],
    )
    assignment = u16.solve_learner_visible_distinct_activity_assignment(
        {
            "A01": [((0,), duplicate_a), ((1,), unique_a)],
            "A02": [((0,), duplicate_b)],
        }
    )
    assert str(assignment["A01"][0]["item_id"]) == "ITEM-2"
    assert str(assignment["A02"][0]["item_id"]) == "ITEM-3"


def test_matching_fails_closed_when_only_distinct_ids_have_same_visible_question() -> None:
    first = _row(
        "ITEM-1",
        "There is ___ tree in the park.",
        "Choose the article for the first mention.",
        ["a", "an", "the"],
    )
    second = _row(
        "ITEM-2",
        "There is ___ tree in the park.",
        "Choose the article for the first mention.",
        ["a", "an", "the"],
    )
    with pytest.raises(
        u16.LearnerVisibleDistinctnessError,
        match="FORM_COMPONENT_LEARNER_VISIBLE_DISTINCTNESS_UNSAT",
    ):
        u16.solve_learner_visible_distinct_activity_assignment(
            {
                "A01": [((0,), first)],
                "A02": [((0,), second)],
            }
        )


def test_speaking_keeps_existing_item_distinctness_because_prompt_is_scene_projected() -> None:
    first = _row("SPK-1", "", "catalog placeholder", [], skill="SPEAKING")
    second = _row("SPK-2", "", "catalog placeholder", [], skill="SPEAKING")
    assignment = u16.solve_learner_visible_distinct_activity_assignment(
        {
            "S01": [((0,), first)],
            "S02": [((0,), second)],
        }
    )
    assert {str(value[0]["item_id"]) for value in assignment.values()} == {"SPK-1", "SPK-2"}
