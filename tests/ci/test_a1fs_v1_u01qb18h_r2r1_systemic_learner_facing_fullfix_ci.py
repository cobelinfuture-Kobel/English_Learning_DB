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
    assert sorted(positions.values()) == [2, 3, 3]
    assert fullfix.score_semantic_option(selected_value="a", canonical_answer="a") is True
    assert fullfix.score_semantic_option(selected_value="the", canonical_answer="a") is False


def test_every_form_activity_identity_has_three_three_two_positions() -> None:
    for form in range(1, 13):
        form_id = f"U01-FORM-{form:02d}"
        orders = [
            fullfix.deterministic_option_permutation(
                ["a", "an", "the"],
                canonical_answer="a",
                form_id=form_id,
                question_identity=f"{form_id}-S{scene:02d}-A{activity:02d}",
            )
            for scene in range(1, 5)
            for activity in (1, 2)
        ]
        positions = Counter(order.index("a") for order in orders)
        assert sorted(positions.values()) == [2, 3, 3], (form_id, positions)


def test_actual_materialization_replays_r4_under_hooks_before_pdf(
    monkeypatch,
    tmp_path,
) -> None:
    calls: list[str] = []
    r4_report = tmp_path / "r4.json"
    output_root = tmp_path / "pdfs"
    database = tmp_path / "unit01.sqlite3"

    def fake_r4_replay(*, database, output, learner_id):
        assert fullfix.u13._SYSTEMIC_CANDIDATE_GUARD is not None
        assert fullfix.u13._SYSTEMIC_OPTION_PERMUTER is fullfix.deterministic_option_permutation
        assert output == r4_report
        calls.append("R4")
        return {
            "task_id": fullfix.r4.TASK_ID,
            "validation_status": fullfix.r4.PASS_STATUS,
            "error_count": 0,
            "forms": [
                {"student_form": {"learner_visible_activity_count": 20}}
                for _ in range(12)
            ],
        }

    def fake_pdf_materialization(**kwargs):
        assert calls == ["R4"]
        assert fullfix.u13._SYSTEMIC_CANDIDATE_GUARD is not None
        assert fullfix.u13._SYSTEMIC_OPTION_PERMUTER is fullfix.deterministic_option_permutation
        assert kwargs["r4_report_path"] == r4_report
        assert kwargs["output_root"] == output_root
        calls.append("PDF")
        return {
            "form_count": 12,
            "materialized_pdf_count": 12,
            "machine_preflight_pass_count": 12,
        }

    monkeypatch.setattr(fullfix.r4, "materialize_full_replay", fake_r4_replay)
    monkeypatch.setattr(
        fullfix.presentation,
        "materialize_twelve_form_pdfs",
        fake_pdf_materialization,
    )

    result = fullfix.materialize_twelve_form_pdfs(
        database=database,
        r4_report_path=r4_report,
        output_root=output_root,
    )

    assert calls == ["R4", "PDF"]
    assert result["actual_r4_replay_executed"] is True
    assert result["actual_r4_replay_validation_status"] == fullfix.r4.PASS_STATUS
    assert result["actual_r4_replay_form_count"] == 12
    assert result["actual_r4_replay_activity_count"] == 240
    assert fullfix.u13._SYSTEMIC_CANDIDATE_GUARD is None
    assert fullfix.u13._SYSTEMIC_OPTION_PERMUTER is None
