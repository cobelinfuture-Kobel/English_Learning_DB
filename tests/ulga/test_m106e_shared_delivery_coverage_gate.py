from __future__ import annotations

import pytest

from ulga.validators.a1_a1plus_delivery_coverage_gate import (
    PASS_STATUS,
    validate_delivery_unit_coverage,
)


def _unit(row_ids=None):
    return {
        "grammar_unit_id": "UNIT_A",
        "canonical_egp_row_ids": row_ids if row_ids is not None else ["EGP_A1_001"],
    }


def _report(status="COVERED"):
    return {
        "validation_status": "PASS",
        "rows": [{"egp_row_id": "EGP_A1_001", "status": status}],
    }


def test_shared_gate_pass_contract():
    result = validate_delivery_unit_coverage(
        _unit(), coverage_report=_report(), error_prefix="consumer"
    )
    assert result["status"] == PASS_STATUS
    assert result["canonical_egp_row_ids"] == ["EGP_A1_001"]
    assert result["learner_mastery_claimed"] is False
    assert result["retention_confirmed"] is False


@pytest.mark.parametrize("status", ["DRAFT_ONLY", "MISSING"])
def test_shared_gate_blocks_noncovered_status(status):
    with pytest.raises(ValueError, match="consumer_coverage_gate_blocked"):
        validate_delivery_unit_coverage(
            _unit(), coverage_report=_report(status), error_prefix="consumer"
        )


def test_shared_gate_blocks_unknown_and_empty_mapping():
    with pytest.raises(ValueError, match='"status": "UNKNOWN"'):
        validate_delivery_unit_coverage(
            _unit(), coverage_report={"rows": []}, error_prefix="consumer"
        )
    with pytest.raises(ValueError, match="consumer_unit_has_no_canonical_rows"):
        validate_delivery_unit_coverage(
            _unit([]), coverage_report=_report(), error_prefix="consumer"
        )
