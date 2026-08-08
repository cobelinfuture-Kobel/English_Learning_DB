from __future__ import annotations

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from product.a1fs_v1_2_1 import u01qb15_runtime_server as runtime
from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb13_whole_form_distinct_item_matching_adapter as legacy_matching
from ulga.builders import _u01qb18c_form01_learner_quality_adapter as quality
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)


def _private(noun: str, stimulus: str = "") -> dict[str, object]:
    return {
        "lexical_slots": {"noun": noun},
        "stimulus": stimulus,
    }


def test_u01qb18c_rejects_self_location_tautology_without_banning_valid_first_mention() -> None:
    bad = _private("park", "There is ___ park in the park.")
    bad_second = _private("park", "There is a park in the park. ___ park is easy to see.")
    good = _private("tree", "There is ___ tree in the park.")

    assert quality.has_self_location_tautology(bad) is True
    assert quality.has_self_location_tautology(bad_second) is True
    assert quality.learner_content_quality_ok(bad) is False
    assert quality.learner_content_quality_ok(bad_second) is False
    assert quality.learner_content_quality_ok(good) is True


def test_u01qb18c_candidate_gate_preserves_scoring_then_applies_content_quality() -> None:
    activity = {"scored": True, "skill": "READING", "task_angle": "ARTICLE_CONTROL"}
    classes = {"BAD": matching.SCORING_CLASS_AUTO, "GOOD": matching.SCORING_CLASS_AUTO}
    bad_row = {
        "item_id": "BAD",
        "private_item_json": __import__("json").dumps(
            {"lexical_slots": {"noun": "park"}, "stimulus": "There is ___ park in the park."}
        ),
    }
    good_row = {
        "item_id": "GOOD",
        "private_item_json": __import__("json").dumps(
            {"lexical_slots": {"noun": "tree"}, "stimulus": "There is ___ tree in the park."}
        ),
    }

    assert quality.candidate_preserves_scoring_class_with_learner_quality(
        activity, bad_row, classes
    ) is False
    assert quality.candidate_preserves_scoring_class_with_learner_quality(
        activity, good_row, classes
    ) is True


def test_u01qb18c_word_order_uses_token_bank_and_reaches_ordered_tokens_contract() -> None:
    repaired = quality.repair_learner_item(
        {
            "item_id": "WORD-ORDER-1",
            "skill": "WRITING",
            "task_angle": "WORD_ORDER",
            "stimulus": "This is a blue bag. Target phrase: a blue bag.",
            "prompt": "Put the target phrase in the correct order.",
            "options": ["bag", "blue", "a"],
            "capture_enabled": True,
            "practice_only": False,
        },
        private_item=_private("bag"),
        form_ordinal=1,
        scene_anchors=["bag", "apple"],
        setting="SNACK_TIME",
    )

    assert repaired["ordered_tokens"] == ["bag", "blue", "a"]
    assert repaired["options"] == []
    assert repaired["word_order_interaction"] == quality.WORD_ORDER_INTERACTION
    assert "Words: bag | blue | a" in repaired["stimulus"]
    assert "Target phrase: a blue bag" not in repaired["stimulus"]
    assert runtime._response_mode(repaired) == "ordered_tokens"


def test_u01qb18c_form01_speaking_targets_selected_item_and_adds_model_frame_word() -> None:
    repaired = quality.repair_learner_item(
        {
            "item_id": "SPEAK-NOUN-BAG",
            "skill": "SPEAKING",
            "task_angle": "SCENE_DESCRIPTION",
            "stimulus": "",
            "prompt": "Say one short sentence about the apple in this scene.",
            "options": [],
            "capture_enabled": False,
            "practice_only": True,
        },
        private_item=_private("bag"),
        form_ordinal=1,
        scene_anchors=["apple", "bag"],
        setting="SNACK_TIME",
    )

    assert repaired["target_word"] == "bag"
    assert repaired["speaking_scaffold_stage"] == quality.FORM01_SCAFFOLD_STAGE
    assert repaired["sentence_frame"] == "This is ___ ______."
    assert repaired["prompt"] == "Complete the sentence frame, then say it aloud."
    assert "Example: This is an apple." in repaired["stimulus"]
    assert "Your turn: This is ___ ______." in repaired["stimulus"]
    assert "Word: bag" in repaired["stimulus"]
    assert "about the apple" not in repaired["prompt"]
    assert runtime._response_mode(repaired) == "practice_only"


def test_u01qb18c_speaking_support_withdraws_across_early_forms() -> None:
    common = {
        "task_angle": "SCENE_DESCRIPTION",
        "target_noun": "bed",
        "scene_anchors": ["bed", "box", "room"],
        "setting": "HOME",
    }
    f1 = quality.speaking_scaffold(form_ordinal=1, **common)
    f2 = quality.speaking_scaffold(form_ordinal=2, **common)
    f3 = quality.speaking_scaffold(form_ordinal=3, **common)
    f4 = quality.speaking_scaffold(form_ordinal=4, **common)

    assert f1["stage"] == quality.FORM01_SCAFFOLD_STAGE
    assert "Example:" in f1["stimulus"] and "Word: bed" in f1["stimulus"]
    assert f2["stage"] == quality.FORM02_SCAFFOLD_STAGE
    assert "Example:" not in f2["stimulus"] and "Word: bed" in f2["stimulus"]
    assert f3 == {
        "stage": quality.FORM03_SCAFFOLD_STAGE,
        "prompt": "Say one short sentence about the bed.",
        "stimulus": "Word: bed",
        "target_word": "bed",
        "sentence_frame": "",
    }
    assert f4 == {
        "stage": quality.FORM04_PLUS_SCAFFOLD_STAGE,
        "prompt": "Say one short sentence about the bed.",
        "stimulus": "",
        "target_word": "bed",
        "sentence_frame": "",
    }


def test_u01qb18c_is_installed_without_replacing_selector_authority() -> None:
    assert quality.installed() is True
    assert (
        matching.candidate_preserves_scoring_class
        is quality.candidate_preserves_scoring_class_with_learner_quality
    )
    assert u13.form_component_payload is quality.form_component_payload_with_learner_quality
    # U01QB18C must not occupy U01QB13's selector pointer; legacy R2 authority
    # identity remains valid when that runtime has been installed in this process.
    if legacy_matching.installed():
        assert u13._candidate_rank is legacy_matching._reserved_candidate_rank
        assert u13.assemble_form_component is legacy_matching.assemble_form_component_whole_form_matching
    assert quality.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert quality.A1FS_CONTENT_POLICY_EXEMPTION
    assert quality.NEXT_SHORT_STEP.startswith("A1FS-V1-U01QB18D_")
