from datetime import datetime, timezone

from ulga.builders.build_a1_private_pilot_retention_schedule_closeout import build_report


def test_engineering_coverage_closeout_passes_without_claiming_retention():
    report = build_report(now=datetime(2026, 7, 14, 2, 10, tzinfo=timezone.utc))
    assert report["validation_status"] == "PASS"
    assert report["pipeline_coverage"] == {
        "unit_count": 24,
        "pipeline_pass_unit_count": 24,
    }
    assert report["human_pilot_coverage"]["missing_dimension_count"] == 0
    assert report["human_pilot_coverage"]["per_unit_human_input_required"] is False
    assert report["engineering_closeout_status"] == "PASS_COVERAGE_CLOSED_RETENTION_REMAINS_SEPARATE"
    assert report["claims"]["retention_confirmed"] is False
    assert report["claims"]["learner_mastery_claimed"] is False


def test_public_baselines_are_deferred_before_24_hours_and_eligible_afterward():
    before = build_report(now=datetime(2026, 7, 14, 2, 10, tzinfo=timezone.utc))
    after = build_report(now=datetime(2026, 7, 15, 2, 10, tzinfo=timezone.utc))
    before_rows = {row["grammar_unit_id"]: row for row in before["retention_schedule"]}
    after_rows = {row["grammar_unit_id"]: row for row in after["retention_schedule"]}
    for unit_id in ("GRAMMAR_REGULAR_PLURAL_NOUNS", "GRAMMAR_SUBJECT_PRONOUNS"):
        assert before_rows[unit_id]["status"] == "DEFERRED_UNTIL_ELIGIBLE"
        assert after_rows[unit_id]["status"] == "ELIGIBLE_FOR_REAL_RETENTION"
        assert before_rows[unit_id]["retention_evidence_created"] is False
        assert after_rows[unit_id]["final_mastery_claimed"] is False


def test_private_baseline_is_not_invented_or_committed():
    report = build_report(now=datetime(2026, 7, 15, 2, 10, tzinfo=timezone.utc))
    rows = {row["grammar_unit_id"]: row for row in report["retention_schedule"]}
    articles = rows["GRAMMAR_ARTICLES_BASIC"]
    assert articles["status"] == "PRIVATE_BASELINE_NOT_COMMITTED"
    assert "baseline_completed_at" not in articles
    assert "retention_eligible_at" not in articles
    assert report["next_short_step"] == "R7-M106_A1A1PlusActualCoverageRecheck_NoNewDesignDocs"
