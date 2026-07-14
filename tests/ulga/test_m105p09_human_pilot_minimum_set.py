from ulga.builders.build_a1_private_pilot_human_minimum_set import build_report


def test_human_minimum_set_closes_all_detected_dimensions():
    report = build_report()
    assert report["validation_status"] == "PASS"
    assert report["scope"] == "A1_A1_PLUS_ONLY"
    assert report["unit_count"] == 24
    assert report["coverage_dimension_count"] > 0
    assert report["missing_dimension_count_after_recommendation"] == 0
    assert report["missing_dimensions_after_recommendation"] == []
    assert report["computed_minimum_human_pilot_unit_count"] >= 3
    assert set(report["existing_human_pilot_unit_ids"]) <= set(
        report["computed_minimum_human_pilot_unit_ids"]
    )


def test_report_stops_per_unit_human_input_and_preserves_evidence_boundaries():
    report = build_report()
    assert report["human_input_policy"] == "NO_MORE_PER_UNIT_INPUT"
    claims = report["claims"]
    assert claims["synthetic_pipeline_coverage_complete"] is True
    assert claims["learner_evidence_created"] is False
    assert claims["learner_mastery_claimed"] is False
    assert claims["retention_confirmed"] is False
    assert claims["automatic_per_unit_human_input_required"] is False


def test_recommendations_are_deterministic_and_have_real_incremental_coverage():
    first = build_report()
    second = build_report()
    assert first["recommended_additional_human_pilot_unit_ids"] == second[
        "recommended_additional_human_pilot_unit_ids"
    ]
    recommended = set(first["recommended_additional_human_pilot_unit_ids"])
    rows = {row["grammar_unit_id"]: row for row in first["units"]}
    assert all(rows[unit_id]["new_dimensions_over_existing_sample"] for unit_id in recommended)
    assert first["next_short_step"] == "R7-M105P10_A1A1PlusRetentionScheduleAndCoverageCloseout"
