from __future__ import annotations

from collections import Counter
from itertools import groupby
import json

import pytest

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


def test_candidate_guard_rejects_explicit_target_pattern_zero_overlap(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        fullfix.r4.cross_layer.authority,
        "canonical_scene_package",
        lambda _ref: {
            "unit_language_projection": {
                "eligible_pattern_refs": ["U01-PATTERN-ALLOWED"],
            }
        },
    )
    item = _item(target_pattern_ids=["U01-PATTERN-OTHER"])
    assert fullfix.candidate_guard(
        item,
        task_angle="FIRST_MENTION_CONTEXT",
        scene_ref_id="U01-TEST-SCENE",
    ) is False

    item["target_pattern_ids"] = ["U01-PATTERN-ALLOWED"]
    assert fullfix.candidate_guard(
        item,
        task_angle="FIRST_MENTION_CONTEXT",
        scene_ref_id="U01-TEST-SCENE",
    ) is True


@pytest.mark.parametrize(
    ("task_angle", "stimulus", "expected"),
    [
        (
            "FIRST_MENTION_CONTEXT",
            "I can see a book. Target phrase: ___ book.",
            True,
        ),
        (
            "KNOWN_REFERENCE_CONTEXT",
            "I can see a book. Target phrase: ___ book.",
            True,
        ),
        (
            "REFERENCE_EVIDENCE",
            "There is a book on the desk. Target phrase: ___ book.",
            True,
        ),
        (
            "TRANSFER_DECISION",
            "There is a book in the room. Target phrase: ___ book.",
            True,
        ),
    ],
)
def test_all_discourse_operations_preserve_source_context_in_final_projection(
    task_angle: str, stimulus: str, expected: bool
) -> None:
    previous = fullfix._install_projection_hooks()
    try:
        activity = _item(
            form_ordinal=7,
            response_mode="select_one",
            task_angle=task_angle,
            stimulus=stimulus,
        )
        projected = fullfix.presentation.r1b.base._clean_stimulus(activity)
    finally:
        fullfix._restore_projection_hooks(previous)
    assert ("book" in projected.casefold() and "target phrase" in projected.casefold()) is expected
    assert "I can see a book" in projected or "There is a book" in projected


def test_final_projection_rejects_duplicate_after_hidden_identity_and_option_order_change() -> None:
    first = _item(
        scene_ref_id="U01-C1-CLASSROOM-BAG",
        skill="READING",
        response_mode="select_one",
        options=["a", "an", "the"],
        stimulus="I can see a book. Target phrase: ___ book.",
    )
    second = dict(first)
    second.update(
        item_id="different-private-item",
        options=["the", "a", "an"],
    )
    with pytest.raises(fullfix.SystemicLearnerFacingFullFixError, match="DUPLICATES=1"):
        fullfix.validate_final_learner_projection({"activities": [first, second]})


def test_final_projection_accepts_same_operation_in_different_context() -> None:
    first = _item(
        scene_ref_id="U01-C1-CLASSROOM-BAG",
        skill="READING",
        stimulus="I can see a book. Target phrase: ___ book.",
    )
    second = dict(first)
    second["scene_ref_id"] = "U01-C2-HOME-TOY-BOX"
    assert fullfix.validate_final_learner_projection({"activities": [first, second]}) == {
        "context_stripping_failures": 0,
        "final_visible_duplicates": 0,
    }


def test_actual_writing_candidate_rank_blocks_self_containment_before_matching() -> None:
    fullfix.install()
    try:
        def row(private: dict[str, object]) -> dict[str, object]:
            return {
                "item_id": str(private["item_id"]),
                "skill": "WRITING",
                "pattern_family_id": private["pattern_family_id"],
                "private_item_json": json.dumps(private),
            }

        common = {
            "pattern_family_id": "U01-PF14-WRITING-COMPLETE-SENTENCE",
            "lexical_slots": {"context_id": "U01-C4-TOY-SHOP"},
            "options": [],
            "prompt": "Write one complete sentence.",
            "item_id": "candidate",
        }
        shop = dict(
            common,
            item_id="shop-in-shop",
            lexical_slots={
                "context_id": "U01-C4-TOY-SHOP",
                "noun": "shop",
                "place": "in the shop",
            },
            stimulus="item: shop | place: in the shop",
        )
        book = dict(
            common,
            item_id="book-in-room",
            lexical_slots={
                "context_id": "U01-C2-HOME-TOY-BOX",
                "noun": "book",
                "place": "in the room",
            },
            stimulus="item: book | place: in the room",
        )
        kwargs = dict(
            anchors={"shop"},
            situation_family="SHOPPING",
            learner_id="learner",
            session_id="session",
            activity_id="activity",
            exposed=set(),
            recent=set(),
            assessment=False,
            scene_ref_id="U01-C4-TOY-SHOP",
            task_angle="COMPLETE_SENTENCE_PRODUCTION",
        )
        assert fullfix.u13._candidate_rank(row=row(shop), **kwargs) is None
        kwargs["anchors"] = {"book"}
        kwargs["situation_family"] = "HOME"
        kwargs["scene_ref_id"] = "U01-C2-HOME-TOY-BOX"
        assert fullfix.u13._candidate_rank(row=row(book), **kwargs) is not None
    finally:
        fullfix.uninstall()


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


def test_actual_form_allocator_balances_realistic_eight_reading_identities() -> None:
    activities = [
        {
            "activity_id": f"U01-FORM-04-S{scene:02d}-A{activity:02d}",
            "options": ["a", "an", "the"],
            "canonical_answer": answer,
        }
        for scene, activity, answer in [
            (1, 1, "the"),
            (1, 2, "a"),
            (2, 1, "an"),
            (2, 2, "the"),
            (3, 1, "a"),
            (3, 2, "the"),
            (4, 1, "a"),
            (4, 2, "the"),
        ]
    ]
    first = fullfix.allocate_form_option_orders(
        form_id="U01-FORM-04", activities=activities
    )
    second = fullfix.allocate_form_option_orders(
        form_id="U01-FORM-04", activities=activities
    )
    assert first == second
    answers = {str(row["activity_id"]): str(row["canonical_answer"]) for row in activities}
    positions = Counter(order.index(answers[activity_id]) for activity_id, order in first.items())
    assert sorted(positions.values()) == [2, 3, 3]
    position_sequence = [
        order.index(answers[activity_id])
        for activity_id, order in sorted(first.items())
    ]
    assert max(
        len(list(group)) for _value, group in groupby(position_sequence)
    ) <= 2
    assert all(
        fullfix.score_semantic_option(
            selected_value=order[order.index(answers[activity_id])],
            canonical_answer=answers[activity_id],
        )
        for activity_id, order in first.items()
    )


def test_manifest_stamp_preserves_sha_bound_review_fields(tmp_path) -> None:
    path = tmp_path / fullfix.presentation.r1b.base.MANIFEST_NAME
    original = {
        "rendered_html_sha256": "html-sha",
        "pdf_sha256": "pdf-sha",
        "render_action": "REUSED",
        "human_visual_review": "PASS",
    }
    path.write_text(json.dumps(original), encoding="utf-8")
    fullfix._stamp_manifest_provenance(tmp_path)
    stamped = json.loads(path.read_text(encoding="utf-8"))
    assert stamped["latest_fullfix_task_id"].startswith("A1FS-V1-U01QB18H-R2R1_")
    assert stamped["latest_fullfix_validation_status"] == fullfix.PASS_STATUS
    assert stamped["next_short_step"] == fullfix.NEXT_SHORT_STEP
    for key, value in original.items():
        assert stamped[key] == value


def test_shared_print_css_uses_compact_non_form_specific_layout_rules() -> None:
    student = {
        "unit_id": "UNIT01",
        "form_ordinal": 1,
        "scene_count": 4,
        "learner_visible_activity_count": 20,
        "skill_counts": {"READING": 8, "WRITING": 8, "SPEAKING": 4},
        "scenes": [{"scene_ref_id": f"scene-{index}", "setting": "room"} for index in range(1, 5)],
        "activities": [
            {
                "scene_ref_id": f"scene-{(index - 1) // 5 + 1}",
                "skill": ("READING", "READING", "WRITING", "WRITING", "SPEAKING")[(index - 1) % 5],
                "stimulus": (
                    "There is ___ book in the room."
                    if (index - 1) % 5 == 0
                    else "I can see a book. Target phrase: ___ book."
                    if (index - 1) % 5 == 1
                    else "Say a sentence."
                ),
                "prompt": "Speak.",
                "task_angle": (
                    "FIRST_MENTION_CONTEXT"
                    if (index - 1) % 5 == 0
                    else "KNOWN_REFERENCE_CONTEXT"
                    if (index - 1) % 5 == 1
                    else ""
                ),
                "response_mode": "select_one" if (index - 1) % 5 < 2 else ("short_text" if (index - 1) % 5 < 4 else "practice_only"),
                "options": ["a", "an", "the"] if (index - 1) % 5 < 2 else [],
                "capture_enabled": (index - 1) % 5 < 4,
                "practice_only": (index - 1) % 5 == 4,
                "question_number": f"Q{index:02d}",
            }
            for index in range(1, 21)
        ],
    }
    html = fullfix.presentation.render_form_html(student)
    assert "body{font-size:10.5pt;line-height:1.3}" in html
    assert ".speaking-space{height:12px}" in html
    assert "q20" not in html.split("</style>", 1)[0].casefold()


def test_every_form_activity_identity_has_three_three_two_positions() -> None:
    for form in range(1, 13):
        form_id = f"U01-FORM-{form:02d}"
        activities = [
            {
                "activity_id": f"{form_id}-S{scene:02d}-A{activity:02d}",
                "options": ["a", "an", "the"],
                "canonical_answer": "a",
            }
            for scene in range(1, 5)
            for activity in (1, 2)
        ]
        orders = fullfix.allocate_form_option_orders(form_id=form_id, activities=activities)
        positions = Counter(
            order.index("a") for order in orders.values()
        )
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
