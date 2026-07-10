from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (  # noqa: E402
    build_and_validate_from_repo as build_candidate_source,
)
from ulga.builders.build_a1_grammar_mastery_review_loop import (  # noqa: E402
    REVIEW_STAGES,
    activity_index,
    build_artifact,
    build_attempt_event,
    build_error_taxonomy,
    build_synthetic_attempts,
    project_mastery,
    validate_artifact,
    validate_attempt_event,
)
from ulga.builders.build_a1_grammar_reading_writing_closed_loop import (  # noqa: E402
    build_and_validate_from_repo as build_closure_source,
)


def sources():
    candidate, candidate_report = build_candidate_source()
    closure, closure_report = build_closure_source()
    assert candidate_report["validation_status"] == "PASS"
    assert closure_report["validation_status"] == "PASS"
    return candidate, closure


def built():
    candidate, closure = sources()
    artifact = build_artifact(candidate, closure)
    report = validate_artifact(artifact, candidate, closure)
    return artifact, report, candidate, closure


def test_mastery_review_loop_passes_with_109_row_simulation():
    artifact, report, _, _ = built()
    summary = report["coverage_summary"]

    assert report["validation_status"] == "PASS"
    assert summary["canonical_unit_count"] == 24
    assert summary["canonical_unique_egp_row_count"] == 109
    assert summary["activity_contract_count"] == 192
    assert summary["simulated_attempt_event_count"] == 192
    assert summary["simulated_mastery_ready_row_count"] == 109
    assert summary["actual_attempt_event_count"] == 0
    assert summary["actual_mastery_measured_row_count"] == 0


def test_error_taxonomy_covers_all_candidate_error_tags():
    artifact, _, candidate, _ = built()
    required = {
        error["tag"]
        for unit in candidate["learning_units"]
        for error in unit["common_error_tags"]
    }

    assert required.issubset(artifact["error_taxonomy"])
    assert "ERR_RESPONSE_MISSING" in artifact["error_taxonomy"]
    assert "ERR_UNCLASSIFIED_GRAMMAR_FAILURE" in artifact["error_taxonomy"]


def test_attempt_event_contract_validates_identity_and_outcome():
    _, _, candidate, closure = built()
    activities = activity_index(closure)
    taxonomy = build_error_taxonomy(candidate)
    activity = next(iter(activities.values()))
    event = build_attempt_event(
        activity,
        learner_ref="SYNTHETIC_LEARNER_A1",
        attempt_sequence=1,
        passed=True,
        synthetic_fixture=True,
    )

    assert validate_attempt_event(event, activities, taxonomy) == []
    assert event["persistent_learner_state_write"] is False
    assert event["production_runtime_event"] is False


def test_failure_projection_creates_four_stage_review_queue():
    artifact, _, _, _ = built()
    failure = artifact["failure_scenario_projection"]

    assert failure["needs_review_row_count"] >= 1
    assert len(failure["review_queue"]) == failure["needs_review_row_count"]
    for queue in failure["review_queue"]:
        assert queue["review_stages"] == [dict(stage) for stage in REVIEW_STAGES]
        assert queue["persistent_queue_write"] is False


def test_retry_with_later_pass_clears_failure_projection():
    _, _, candidate, closure = built()
    activities = activity_index(closure)
    taxonomy = build_error_taxonomy(candidate)
    failure_activity = next(
        activity_id
        for activity_id, activity in sorted(activities.items())
        if activity["skill"] == "writing" and activity["activity_role"] == "assessment"
    )
    attempts = build_synthetic_attempts(
        closure,
        failure_activity_id=failure_activity,
        failure_error_tag="ERR_UNCLASSIFIED_GRAMMAR_FAILURE",
    )
    retry = build_attempt_event(
        activities[failure_activity],
        learner_ref="SYNTHETIC_LEARNER_A1",
        attempt_sequence=2,
        passed=True,
        synthetic_fixture=True,
    )
    assert validate_attempt_event(retry, activities, taxonomy) == []

    projection = project_mastery(closure, attempts + [retry])

    assert projection["simulated_mastery_ready_row_count"] == 109
    assert projection["needs_review_row_count"] == 0
    assert projection["review_queue"] == []


def test_unknown_activity_and_invalid_error_usage_fail_closed():
    _, _, candidate, closure = built()
    activities = activity_index(closure)
    taxonomy = build_error_taxonomy(candidate)
    activity = next(iter(activities.values()))
    event = build_attempt_event(
        activity,
        learner_ref="SYNTHETIC_LEARNER_A1",
        attempt_sequence=1,
        passed=True,
        error_tags=["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"],
        synthetic_fixture=True,
    )
    event["activity_id"] = "UNKNOWN_ACTIVITY"

    errors = validate_attempt_event(event, activities, taxonomy)

    assert errors == ["unknown_activity_id:UNKNOWN_ACTIVITY"]


def test_passed_attempt_with_error_tag_is_rejected():
    _, _, candidate, closure = built()
    activities = activity_index(closure)
    taxonomy = build_error_taxonomy(candidate)
    activity = next(iter(activities.values()))
    event = build_attempt_event(
        activity,
        learner_ref="SYNTHETIC_LEARNER_A1",
        attempt_sequence=1,
        passed=True,
        error_tags=["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"],
        synthetic_fixture=True,
    )

    errors = validate_attempt_event(event, activities, taxonomy)

    assert any(error.startswith("passed_attempt_has_error_tags") for error in errors)


def test_builder_is_deterministic_and_does_not_mutate_sources():
    candidate, closure = sources()
    before = copy.deepcopy((candidate, closure))

    first = build_artifact(candidate, closure)
    second = build_artifact(candidate, closure)

    assert first == second
    assert (candidate, closure) == before


def test_false_actual_mastery_and_persistence_claims_fail_closed():
    artifact, _, candidate, closure = built()
    artifact["claim_boundaries"]["actual_learner_mastery_complete"] = True
    artifact["claim_boundaries"]["production_persistence_complete"] = True

    report = validate_artifact(artifact, candidate, closure)

    assert report["validation_status"] == "FAIL"
    assert "false_actual_mastery_claim" in report["errors"]
    assert "false_production_persistence_claim" in report["errors"]


def test_scope_remains_a1_only_without_persistent_learner_writes():
    artifact, _, _, _ = built()
    boundaries = artifact["claim_boundaries"]

    assert boundaries["attempt_event_contract_implemented"] is True
    assert boundaries["mastery_projection_implemented"] is True
    assert boundaries["review_queue_projection_implemented"] is True
    assert boundaries["retention_policy_implemented"] is True
    assert boundaries["actual_learner_attempt_collection_complete"] is False
    assert boundaries["actual_learner_mastery_complete"] is False
    assert boundaries["production_persistence_complete"] is False
    assert boundaries["no_a2_a2plus_expansion"] is True
    assert boundaries["no_persistent_learner_state_write"] is True
