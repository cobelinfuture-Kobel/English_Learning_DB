from __future__ import annotations

from collections import Counter

from product.a1fs_v1_2_1 import (
    u01qb18h_r2r1_unit01_systemic_learner_facing_fullfix as fullfix,
)


def _item(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "pattern_family_id": "U01-PF04-FIRST-MENTION-CONTEXT",
        "stimulus": "There is ___ bag in the park.",
        "prompt": "Choose the article for the first mention.",
        "options": ["a", "an", "the"],
        "correct_answer": "a",
        "lexical_slots": {"noun": "bag"},
    }
    value.update(overrides)
    return value


def test_answerability_requires_visible_prior_reference_for_known_reference() -> None:
    item = _item(
        pattern_family_id="U01-PF05-KNOWN-REFERENCE-CONTEXT",
        stimulus="Target phrase: ___ park.",
        prompt="Choose the correct article for the target phrase.",
        lexical_slots={"noun": "park"},
    )
    assert fullfix.candidate_guard(item, task_angle="KNOWN_REFERENCE_CONTEXT") is False

    item["stimulus"] = "I can see a park. Target phrase: ___ park."
    assert fullfix.candidate_guard(item, task_angle="KNOWN_REFERENCE_CONTEXT") is True


def test_scene_self_containment_is_rejected_and_normal_pair_is_allowed() -> None:
    contradiction = _item(
        stimulus="There is ___ shop in the shop.",
        lexical_slots={"noun": "shop"},
    )
    assert fullfix.semantic_compatible(contradiction) is False
    assert fullfix.semantic_compatible(_item()) is True


def test_visible_signature_ignores_option_order_but_keeps_operation_identity() -> None:
    first = _item(options=["a", "an", "the"])
    second = _item(options=["the", "a", "an"])
    assert fullfix.visible_signature(item=first) == fullfix.visible_signature(item=second)
    second["prompt"] = "Choose the article for a known reference."
    assert fullfix.visible_signature(item=first) != fullfix.visible_signature(item=second)


def test_option_permutation_is_deterministic_and_scoring_is_value_based() -> None:
    orders = [
        fullfix.deterministic_option_permutation(
            ["a", "an", "the"],
            canonical_answer="a",
            form_id="U01-FORM-01",
            question_identity=f"Q{index:02d}",
        )
        for index in range(1, 9)
    ]
    assert orders == [
        fullfix.deterministic_option_permutation(
            ["a", "an", "the"],
            canonical_answer="a",
            form_id="U01-FORM-01",
            question_identity=f"Q{index:02d}",
        )
        for index in range(1, 9)
    ]
    positions = Counter(order.index("a") for order in orders)
    assert max(positions.values()) <= 3
    assert min(positions.values()) >= 2
    assert fullfix.score_semantic_option(selected_value="a", canonical_answer="a") is True
    assert fullfix.score_semantic_option(selected_value="the", canonical_answer="a") is False


def test_activity_identity_produces_form_level_three_three_two_positions() -> None:
    orders = [
        fullfix.deterministic_option_permutation(
            ["a", "an", "the"],
            canonical_answer="a",
            form_id="U01-FORM-04",
            question_identity=f"U01-FORM-04-S{scene:02d}-A{activity:02d}",
        )
        for scene in range(1, 5)
        for activity in (1, 2)
    ]
    positions = Counter(order.index("a") for order in orders)
    assert sorted(positions.values()) == [2, 3, 3]
