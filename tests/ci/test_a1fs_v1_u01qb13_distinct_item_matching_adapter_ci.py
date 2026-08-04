from __future__ import annotations

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
