import pytest

from ulga.query.a1_a1plus_coverage_query import (
    coverage_summary,
    get_row,
    list_rows,
    load_coverage,
)


def test_summary_exposes_complete_canonical_coverage_without_mastery_claims():
    report = load_coverage()
    summary = coverage_summary(report)
    assert summary["validation_status"] == "PASS"
    assert summary["canonical_row_count"] == 109
    assert summary["covered_row_count"] == 109
    assert summary["coverage_percent"] == 100.0
    assert summary["draft_only_row_count"] == 0
    assert summary["missing_row_count"] == 0
    assert summary["learner_mastery_claimed"] is False
    assert summary["retention_confirmed"] is False


def test_row_lookup_and_status_filters_are_deterministic():
    report = load_coverage()
    rows = list_rows(report=report)
    assert len(rows) == 109
    first = rows[0]
    assert get_row(first["egp_row_id"], report) == first
    assert get_row("UNKNOWN_EGP_ROW", report) is None
    covered = list_rows("covered", report)
    assert len(covered) == 109
    assert all(row["status"] == "COVERED" for row in covered)
    assert list_rows("DRAFT_ONLY", report) == []
    assert list_rows("MISSING", report) == []


def test_query_rejects_invalid_inputs():
    report = load_coverage()
    with pytest.raises(ValueError, match="egp_row_id_required"):
        get_row("", report)
    with pytest.raises(ValueError, match="invalid_coverage_status"):
        list_rows("MASTERED", report)
