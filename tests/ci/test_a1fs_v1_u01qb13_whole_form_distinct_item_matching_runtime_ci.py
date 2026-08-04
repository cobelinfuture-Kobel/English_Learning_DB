from __future__ import annotations

import pytest

from ulga.builders import _u01qb13_whole_form_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb14r2_runtime_capacity_spiral_reuse_selector as r2
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u01qb13


def test_matching_avoids_activity_order_greedy_trap() -> None:
    # Historical U01QB13 activity-order greedy selection would take item-1 for
    # A01 first and strand A02. Whole-form matching must reserve item-2 for A01
    # and the only compatible item-1 for A02.
    candidates = {
        "U01-FORM-12-S04-A01": [
            ((0, "item-1"), "item-1"),
            ((1, "item-2"), "item-2"),
        ],
        "U01-FORM-12-S04-A02": [
            ((0, "item-1"), "item-1"),
        ],
    }
    reservations = matching._solve_distinct_reservations(candidates)
    assert reservations == {
        "U01-FORM-12-S04-A01": "item-2",
        "U01-FORM-12-S04-A02": "item-1",
    }


def test_matching_fails_closed_when_distinct_capacity_is_impossible() -> None:
    with pytest.raises(
        matching.WholeFormDistinctItemMatchingError,
        match="WHOLE_FORM_DISTINCT_ITEM_MATCHING_UNSAT",
    ):
        matching._solve_distinct_reservations(
            {
                "A01": [((0,), "item-1")],
                "A02": [((0,), "item-1")],
            }
        )


def test_r2_runtime_installs_single_u01qb13_matching_authority() -> None:
    assert matching.installed() is True
    assert u01qb13.assemble_form_component is matching.assemble_form_component_whole_form_matching
    assert u01qb13._candidate_rank is matching._reserved_candidate_rank
    assert matching.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert matching.A1FS_CONTENT_POLICY_EXEMPTION
    assert r2.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert r2.A1FS_CONTENT_POLICY_EXEMPTION
