from __future__ import annotations

import json

from ulga.builders import _u01qb13_distinct_item_matching_adapter as adapter
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u01qb13,
)
from ulga.builders import (
    build_a1fs_v1_u01qb15_actual_real62_fresh474_r2_distinct_matching_acceptance_runner
    as runner,
)


def _row(item_id: str) -> dict[str, str]:
    return {"item_id": item_id}


def _runtime_row(item_id: str, scoring_mode: str, *, capture_enabled: int = 1) -> dict[str, object]:
    return {
        "item_id": item_id,
        "capture_enabled": capture_enabled,
        "private_item_json": json.dumps(
            {
                "scoring_mode": scoring_mode,
                "response_contract": {"scoring_mode": scoring_mode},
            }
        ),
    }


def test_matching_repairs_greedy_trap_without_duplicate_items() -> None:
    # Historical greedy order would give A01 -> item-1 and then strand A02.
    # A valid whole-form matching exists: A01 -> item-2, A02 -> item-1.
    candidates = {
        "A01": [
            ((0, "item-1"), _row("item-1")),
            ((1, "item-2"), _row("item-2")),
        ],
        "A02": [
            ((0, "item-1"), _row("item-1")),
        ],
    }
    solved = adapter.solve_distinct_activity_assignment(candidates)
    assert solved["A01"][0]["item_id"] == "item-2"
    assert solved["A02"][0]["item_id"] == "item-1"
    assert len({value[0]["item_id"] for value in solved.values()}) == 2


def test_matching_fails_closed_when_no_distinct_assignment_exists() -> None:
    candidates = {
        "A01": [((0,), _row("item-1"))],
        "A02": [((0,), _row("item-1"))],
    }
    try:
        adapter.solve_distinct_activity_assignment(candidates)
    except adapter.DistinctItemMatchingError as exc:
        assert str(exc).startswith("FORM_COMPONENT_DISTINCT_ITEM_MATCHING_UNSAT:")
    else:
        raise AssertionError("unsatisfiable distinct-item graph was accepted")


def test_complete_sentence_writing_preserves_human_review_scoring_class() -> None:
    activity = {
        "skill": "WRITING",
        "task_angle": "COMPLETE_SENTENCE_PRODUCTION",
        "scored": 1,
    }
    assert adapter.required_activity_scoring_class(activity) == adapter.SCORING_CLASS_HUMAN_REVIEW
    assert adapter.candidate_preserves_scoring_class(
        activity, _runtime_row("feature", "FEATURE_RUBRIC")
    )
    assert not adapter.candidate_preserves_scoring_class(
        activity, _runtime_row("auto", "NORMALIZED_TEXT")
    )


def test_connected_sentence_writing_preserves_human_review_scoring_class() -> None:
    activity = {
        "skill": "WRITING",
        "task_angle": "CONNECTED_SENTENCE_PRODUCTION",
        "scored": 1,
    }
    assert adapter.candidate_preserves_scoring_class(
        activity, _runtime_row("feature", "FEATURE_RUBRIC")
    )
    assert not adapter.candidate_preserves_scoring_class(
        activity, _runtime_row("auto", "EXACT_OPTION")
    )


def test_auto_scored_activity_rejects_feature_rubric_candidate() -> None:
    activity = {
        "skill": "READING",
        "task_angle": "REFERENCE_EVIDENCE",
        "scored": 1,
    }
    assert adapter.required_activity_scoring_class(activity) == adapter.SCORING_CLASS_AUTO
    assert adapter.candidate_preserves_scoring_class(
        activity, _runtime_row("auto", "EXACT_OPTION")
    )
    assert not adapter.candidate_preserves_scoring_class(
        activity, _runtime_row("feature", "FEATURE_RUBRIC")
    )


def test_practice_only_activity_does_not_create_new_scoring_requirement() -> None:
    activity = {
        "skill": "SPEAKING",
        "task_angle": "SCENE_DESCRIPTION",
        "scored": 0,
    }
    row = {
        "item_id": "practice",
        "capture_enabled": 0,
        "private_item_json": json.dumps({}),
    }
    assert adapter.required_activity_scoring_class(activity) == adapter.SCORING_CLASS_PRACTICE_ONLY
    assert adapter.candidate_preserves_scoring_class(activity, row)


def test_unknown_scoring_contract_fails_closed_for_scored_activity() -> None:
    activity = {
        "skill": "READING",
        "task_angle": "ARTICLE_CONTROL",
        "scored": 1,
    }
    row = {
        "item_id": "unknown",
        "capture_enabled": 1,
        "private_item_json": json.dumps({}),
    }
    assert adapter.runtime_item_scoring_class(row) == adapter.SCORING_CLASS_UNKNOWN
    assert not adapter.candidate_preserves_scoring_class(activity, row)


def test_install_is_idempotent_and_targets_existing_u01qb13_runtime() -> None:
    original = u01qb13.assemble_form_component
    try:
        adapter.install()
        assert u01qb13.assemble_form_component is adapter.assemble_form_component
        adapter.install()
        assert u01qb13.assemble_form_component is adapter.assemble_form_component
    finally:
        u01qb13.assemble_form_component = original


def test_operator_runner_reuses_existing_acceptance_status_and_policy_boundaries() -> None:
    assert runner.PASS_STATUS
    assert runner.NEXT_SHORT_STEP
    assert runner.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert runner.A1FS_CONTENT_POLICY_EXEMPTION
