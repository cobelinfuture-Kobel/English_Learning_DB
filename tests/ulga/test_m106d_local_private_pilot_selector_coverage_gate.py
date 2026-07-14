from __future__ import annotations

import pytest

from ulga.builders.run_a1_grammar_text_mode_private_pilot_covered_next_unit import (
    select_next_covered_unit,
    validate_unit_coverage,
)


def _unit(*, row_ids=None):
    return {
        "sequence_index": 1,
        "grammar_unit_id": "UNIT_A",
        "prerequisite_unit_ids": [],
        "canonical_egp_row_ids": row_ids if row_ids is not None else ["EGP_A1_001"],
        "delivery_plan": {
            "practice_item_ids": [f"P{i}" for i in range(6)],
            "assessment_item_ids": ["A1", "A2"],
        },
    }


def _package(unit=None):
    return {"learning_units": [unit or _unit()]}


def _coverage(status="COVERED"):
    return {
        "validation_status": "PASS",
        "rows": [
            {
                "egp_row_id": "EGP_A1_001",
                "status": status,
                "grammar_unit_ids": ["UNIT_A"],
                "reading_item_count": 1,
                "writing_item_count": 1,
                "assessment_item_count": 1,
            }
        ],
    }


def test_validate_unit_coverage_passes_only_covered_rows():
    result = validate_unit_coverage(_unit(), coverage_report=_coverage())
    assert result["status"] == "PASS_ALL_CANONICAL_ROWS_COVERED"
    assert result["canonical_egp_row_ids"] == ["EGP_A1_001"]
    assert result["learner_mastery_claimed"] is False
    assert result["retention_confirmed"] is False


@pytest.mark.parametrize("status", ["DRAFT_ONLY", "MISSING"])
def test_validate_unit_coverage_fails_closed_for_noncovered_rows(status):
    with pytest.raises(ValueError, match="coverage_gate_blocked"):
        validate_unit_coverage(_unit(), coverage_report=_coverage(status))


def test_validate_unit_coverage_fails_closed_for_unknown_row():
    report = {"validation_status": "PASS", "rows": []}
    with pytest.raises(ValueError, match='"status": "UNKNOWN"'):
        validate_unit_coverage(_unit(), coverage_report=report)


def test_validate_unit_coverage_requires_nonempty_canonical_rows():
    with pytest.raises(ValueError, match="has_no_canonical_rows"):
        validate_unit_coverage(_unit(row_ids=[]), coverage_report=_coverage())


def test_selector_applies_gate_after_prerequisite_selection():
    selected = select_next_covered_unit(
        _package(),
        executed_unit_ids=set(),
        progression_ready_unit_ids=set(),
        coverage_report=_coverage(),
    )
    assert selected["grammar_unit_id"] == "UNIT_A"


def test_selector_blocks_delivery_when_selected_unit_is_not_covered():
    with pytest.raises(ValueError, match="coverage_gate_blocked"):
        select_next_covered_unit(
            _package(),
            executed_unit_ids=set(),
            progression_ready_unit_ids=set(),
            coverage_report=_coverage("DRAFT_ONLY"),
        )


def test_selector_returns_none_without_querying_coverage_when_all_executed():
    assert (
        select_next_covered_unit(
            _package(),
            executed_unit_ids={"UNIT_A"},
            progression_ready_unit_ids={"UNIT_A"},
            coverage_report={"validation_status": "FAIL", "rows": []},
        )
        is None
    )
