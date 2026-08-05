from __future__ import annotations

import json
import sqlite3

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


def test_matching_repairs_greedy_trap_without_duplicate_items() -> None:
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


def test_scoring_class_is_loaded_from_canonical_response_contract_join() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE u01qb02_item_catalog(
            item_id TEXT PRIMARY KEY,
            asset_key TEXT NOT NULL,
            lesson_id TEXT NOT NULL,
            capture_enabled INTEGER NOT NULL,
            private_item_json TEXT NOT NULL
        );
        CREATE TABLE response_contracts(
            asset_key TEXT PRIMARY KEY,
            contract_json TEXT NOT NULL
        );
        """
    )
    connection.executemany(
        "INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?,?)",
        [
            (
                "human",
                "asset-human",
                "lesson-writing",
                1,
                json.dumps({"scoring_mode": "NORMALIZED_TEXT"}),
            ),
            (
                "auto",
                "asset-auto",
                "lesson-writing",
                1,
                json.dumps({"scoring_mode": "FEATURE_RUBRIC"}),
            ),
            (
                "practice",
                "asset-practice",
                "lesson-writing",
                0,
                json.dumps({}),
            ),
        ],
    )
    connection.executemany(
        "INSERT INTO response_contracts VALUES(?,?)",
        [
            ("asset-human", json.dumps({"scoring_mode": "FEATURE_RUBRIC"})),
            ("asset-auto", json.dumps({"scoring_mode": "NORMALIZED_TEXT"})),
            ("asset-practice", json.dumps({"scoring_mode": "NORMALIZED_TEXT"})),
        ],
    )

    classes = adapter.load_runtime_item_scoring_classes(
        connection,
        lesson_id="lesson-writing",
    )
    assert classes == {
        "auto": adapter.SCORING_CLASS_AUTO,
        "human": adapter.SCORING_CLASS_HUMAN_REVIEW,
        "practice": adapter.SCORING_CLASS_PRACTICE_ONLY,
    }


def test_complete_sentence_writing_uses_canonical_human_review_class() -> None:
    activity = {
        "skill": "WRITING",
        "task_angle": "COMPLETE_SENTENCE_PRODUCTION",
        "scored": 1,
    }
    classes = {
        "human": adapter.SCORING_CLASS_HUMAN_REVIEW,
        "auto": adapter.SCORING_CLASS_AUTO,
    }
    assert adapter.required_activity_scoring_class(activity) == adapter.SCORING_CLASS_HUMAN_REVIEW
    assert adapter.candidate_preserves_scoring_class(activity, _row("human"), classes)
    assert not adapter.candidate_preserves_scoring_class(activity, _row("auto"), classes)


def test_connected_sentence_writing_uses_canonical_human_review_class() -> None:
    activity = {
        "skill": "WRITING",
        "task_angle": "CONNECTED_SENTENCE_PRODUCTION",
        "scored": 1,
    }
    classes = {
        "human": adapter.SCORING_CLASS_HUMAN_REVIEW,
        "auto": adapter.SCORING_CLASS_AUTO,
    }
    assert adapter.candidate_preserves_scoring_class(activity, _row("human"), classes)
    assert not adapter.candidate_preserves_scoring_class(activity, _row("auto"), classes)


def test_auto_scored_activity_rejects_feature_rubric_candidate() -> None:
    activity = {
        "skill": "READING",
        "task_angle": "REFERENCE_EVIDENCE",
        "scored": 1,
    }
    classes = {
        "auto": adapter.SCORING_CLASS_AUTO,
        "human": adapter.SCORING_CLASS_HUMAN_REVIEW,
    }
    assert adapter.required_activity_scoring_class(activity) == adapter.SCORING_CLASS_AUTO
    assert adapter.candidate_preserves_scoring_class(activity, _row("auto"), classes)
    assert not adapter.candidate_preserves_scoring_class(activity, _row("human"), classes)


def test_practice_only_activity_does_not_create_new_scoring_requirement() -> None:
    activity = {
        "skill": "SPEAKING",
        "task_angle": "SCENE_DESCRIPTION",
        "scored": 0,
    }
    assert adapter.required_activity_scoring_class(activity) == adapter.SCORING_CLASS_PRACTICE_ONLY
    assert adapter.candidate_preserves_scoring_class(activity, _row("practice"), {})


def test_missing_canonical_scoring_contract_fails_closed_for_scored_activity() -> None:
    activity = {
        "skill": "READING",
        "task_angle": "ARTICLE_CONTROL",
        "scored": 1,
    }
    assert not adapter.candidate_preserves_scoring_class(activity, _row("missing"), {})


def test_contract_json_classification_fails_closed_on_missing_or_invalid_contract() -> None:
    assert (
        adapter.scoring_class_from_contract_json(None, capture_enabled=True)
        == adapter.SCORING_CLASS_UNKNOWN
    )
    assert (
        adapter.scoring_class_from_contract_json("not-json", capture_enabled=True)
        == adapter.SCORING_CLASS_UNKNOWN
    )
    assert (
        adapter.scoring_class_from_contract_json(None, capture_enabled=False)
        == adapter.SCORING_CLASS_PRACTICE_ONLY
    )


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
