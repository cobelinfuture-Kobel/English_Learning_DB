from ulga.builders.build_a1_a1plus_actual_coverage_recheck import build_report


def test_a1_a1plus_canonical_rows_are_fully_covered():
    report = build_report()
    assert report["validation_status"] == "PASS"
    assert report["scope"] == "A1_A1_PLUS_ONLY"
    assert report["canonical_row_count"] == 109
    assert report["covered_row_count"] == 109
    assert report["draft_only_row_count"] == 0
    assert report["missing_row_count"] == 0
    assert report["unexpected_row_count"] == 0
    assert report["coverage_percent"] == 100.0


def test_every_covered_row_has_reading_writing_and_assessment_items():
    report = build_report()
    assert len(report["rows"]) == 109
    for row in report["rows"]:
        assert row["status"] == "COVERED"
        assert row["grammar_unit_ids"]
        assert row["reading_item_count"] > 0
        assert row["writing_item_count"] > 0
        assert row["assessment_item_count"] > 0


def test_coverage_recheck_does_not_convert_pipeline_coverage_to_mastery():
    report = build_report()
    claims = report["claims"]
    assert claims["canonical_mapping_coverage_complete"] is True
    assert claims["synthetic_pipeline_coverage_is_learner_mastery"] is False
    assert claims["learner_mastery_claimed"] is False
    assert claims["retention_confirmed"] is False
    assert claims["a2_or_a2plus_in_scope"] is False
    assert report["next_short_step"] == "R7-M106A_A1A1PlusCoverageRegressionGateIntegration"
