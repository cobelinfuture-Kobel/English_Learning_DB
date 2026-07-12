from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ulga.builders.run_a1_grammar_text_mode_retention_check import (
    NEXT_PRIVATE_PILOT_TASK,
    RETENTION_RESUME_TASK,
    WORKFLOW_PATCH_ID,
    build_deferred_report,
    build_no_candidate_report,
)


TZ_TAIPEI = timezone(timedelta(hours=8))


def test_minimum_delay_defer_is_nonblocking_and_does_not_create_evidence():
    baseline_completed = datetime(2026, 7, 12, 7, 15, 12, tzinfo=TZ_TAIPEI)
    eligible_at = baseline_completed + timedelta(hours=24)
    now = baseline_completed + timedelta(minutes=10)

    report = build_deferred_report(
        grammar_unit_id="GRAMMAR_ARTICLES_BASIC",
        baseline_completed_at=baseline_completed,
        retention_eligible_at=eligible_at,
        now=now,
    )

    assert report["workflow_patch_id"] == WORKFLOW_PATCH_ID
    assert report["validation_status"] == "PASS"
    assert report["retention_status"] == "DEFERRED_UNTIL_ELIGIBLE"
    assert report["workflow_status"] == "NON_BLOCKING_CONTINUE_ALLOWED"
    assert report["measurement_gate"] == "DEFERRED_MINIMUM_DELAY_NOT_REACHED"
    assert report["engineering_progress_gate"] == "PASS_CONTINUE"
    assert report["stop_reason"] == "NONE"
    assert report["next_task"] == NEXT_PRIVATE_PILOT_TASK
    assert report["retention_resume_task"] == RETENTION_RESUME_TASK
    assert report["retention_evidence_created"] is False
    assert report["final_mastery_claimed"] is False
    assert report["persistent_learner_state_write"] is False
    assert report["remaining_seconds"] == 23 * 3600 + 50 * 60


def test_same_day_recheck_is_explicitly_not_retention_evidence():
    baseline_completed = datetime(2026, 7, 12, 7, 15, 12, tzinfo=TZ_TAIPEI)
    eligible_at = baseline_completed + timedelta(hours=24)

    report = build_deferred_report(
        grammar_unit_id="GRAMMAR_ARTICLES_BASIC",
        baseline_completed_at=baseline_completed,
        retention_eligible_at=eligible_at,
        now=baseline_completed + timedelta(hours=2),
    )

    assert report["same_day_recheck_classification"] == "NOT_RETENTION_EVIDENCE"
    assert report["retention_evidence_created"] is False
    assert report["final_mastery_claimed"] is False


def test_no_retention_candidate_is_successful_noop_and_allows_progress():
    report = build_no_candidate_report()

    assert report["workflow_patch_id"] == WORKFLOW_PATCH_ID
    assert report["validation_status"] == "PASS"
    assert report["retention_status"] == "NO_RETENTION_CANDIDATE"
    assert report["workflow_status"] == "NON_BLOCKING_CONTINUE_ALLOWED"
    assert report["measurement_gate"] == "NO_ACTION_REQUIRED"
    assert report["engineering_progress_gate"] == "PASS_CONTINUE"
    assert report["stop_reason"] == "NONE"
    assert report["next_task"] == NEXT_PRIVATE_PILOT_TASK
    assert report["retention_resume_task"] == RETENTION_RESUME_TASK
    assert report["retention_evidence_created"] is False
