from ulga.builders.build_a1_private_pilot_synthetic_pipeline_coverage import build_report


def test_all_a1_a1plus_units_pass_engineering_pipeline_without_mastery_claims():
    report = build_report()
    assert report["validation_status"] == "PASS"
    assert report["scope"] == "A1_A1_PLUS_ONLY"
    assert report["unit_count"] == 24
    assert report["pipeline_pass_unit_count"] == 24
    assert report["human_pilot_sampled_unit_count"] == 3
    assert report["synthetic_only_unit_count"] == 21
    assert report["failed_unit_ids"] == []
    assert report["claims"] == {
        "learner_evidence_created": False,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
    }
    assert all(unit["synthetic_engineering_probe"] is True for unit in report["units"])
    assert all(unit["projection_status"] == "MASTERY_CANDIDATE_PENDING_RETENTION" for unit in report["units"])
    assert all(all(unit["checks"].values()) for unit in report["units"])


def test_human_sample_is_exact_and_synthetic_results_are_not_learner_evidence():
    report = build_report()
    sampled = {row["grammar_unit_id"] for row in report["units"] if row["human_pilot_sampled"]}
    assert sampled == {
        "GRAMMAR_ARTICLES_BASIC",
        "GRAMMAR_REGULAR_PLURAL_NOUNS",
        "GRAMMAR_SUBJECT_PRONOUNS",
    }
    assert report["next_short_step"] == "R7-M105P09_A1A1PlusSyntheticCoverageGapReviewAndHumanPilotMinimumSet"
