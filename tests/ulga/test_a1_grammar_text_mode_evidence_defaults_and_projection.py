from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.builders.build_a1_grammar_text_mode_evidence_projection_review_routing import (
    REVIEW_STAGES,
    build_and_validate_from_repo,
    build_artifact,
    validate_artifact,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_package_source,
)


def package_source():
    package, report = build_package_source()
    assert report["validation_status"] == "PASS"
    return package


def blank_intake():
    return {
        "artifact_id": "a1_grammar_text_mode_private_pilot_evidence_normalized",
        "intake_status": "READY_AWAITING_REAL_ATTEMPTS",
        "accepted_attempts": [],
    }


def fixture_attempt(item_id: str, sequence: int, *, passed: bool, score: float):
    return {
        "event_id": f"FIXTURE:{item_id}:{sequence}",
        "item_id": item_id,
        "attempt_sequence": sequence,
        "submitted_at": "2026-07-11T10:00:00+08:00",
        "response_text": "fixture response",
        "score": score,
        "passed": passed,
        "outcome": "PASS" if passed else "FAIL",
        "error_tags": [] if passed else ["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"],
        "evaluator_type": "MANUAL",
        "evaluator_ref": "fixture:operator",
        "evidence_ref": f"fixture://{item_id}/{sequence}",
        "synthetic_fixture": False,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
        "fixture_only_not_real_evidence": True,
    }


def unit_item_ids(unit):
    plan = unit["delivery_plan"]
    return list(plan["practice_item_ids"]) + list(plan["assessment_item_ids"])


def test_committed_intake_template_has_safe_default_fields():
    path = Path("ulga/evidence/a1_grammar_text_mode_private_pilot_evidence_intake.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    defaults = payload["attempt_defaults"]

    assert payload["template_status"] == "DEFAULT_FIELDS_READY_AWAITING_REAL_VALUES"
    assert payload["attempts"] == []
    assert defaults["event_id"] is None
    assert defaults["item_id"] is None
    assert defaults["attempt_sequence"] == 1
    assert defaults["submitted_at"] is None
    assert defaults["response_text"] == ""
    assert defaults["score"] == 0.0
    assert defaults["passed"] is False
    assert defaults["outcome"] == "FAIL"
    assert defaults["error_tags"] == ["ERR_RESPONSE_MISSING"]
    assert defaults["evaluator_type"] == "MANUAL"
    assert defaults["synthetic_fixture"] is False
    assert defaults["persistent_learner_state_write"] is False
    assert defaults["production_runtime_event"] is False


def test_default_repository_projection_is_complete_but_unobserved():
    artifact, report = build_and_validate_from_repo()
    summary = artifact["coverage_summary"]

    assert report["validation_status"] == "PASS"
    assert summary["package_unit_count"] == 24
    assert summary["package_row_count"] == 109
    assert summary["package_item_count"] == 192
    assert summary["actual_attempt_count"] == 0
    assert summary["not_measured_unit_count"] == 24
    assert summary["not_observed_row_count"] == 109
    assert summary["final_mastered_unit_count"] == 0
    assert summary["final_mastered_row_count"] == 0
    assert artifact["continuation_gate"]["stop_reason"] == (
        "REAL_LEARNER_EVIDENCE_REQUIRED"
    )


def test_one_real_attempt_routes_unit_to_complete_missing_items():
    package = package_source()
    unit = package["learning_units"][0]
    item_id = unit_item_ids(unit)[0]
    intake = blank_intake()
    intake["intake_status"] = "PARTIAL_REAL_EVIDENCE_ACCEPTED"
    intake["accepted_attempts"] = [
        fixture_attempt(item_id, 1, passed=True, score=1.0)
    ]

    artifact = build_artifact(package, intake)
    projection = artifact["by_grammar_unit_id"][unit["grammar_unit_id"]]

    assert projection["projection_status"] == "INSUFFICIENT_EVIDENCE"
    assert projection["next_route"] == "COMPLETE_MISSING_ITEMS"
    assert projection["attempted_item_count"] == 1
    assert len(projection["missing_item_ids"]) == 7
    assert artifact["coverage_summary"]["completion_route_count"] == 1


def test_full_passing_unit_becomes_candidate_pending_retention_not_mastered():
    package = package_source()
    unit = package["learning_units"][0]
    attempts = [
        fixture_attempt(item_id, 1, passed=True, score=1.0)
        for item_id in unit_item_ids(unit)
    ]
    intake = blank_intake()
    intake["intake_status"] = "PARTIAL_REAL_EVIDENCE_ACCEPTED"
    intake["accepted_attempts"] = attempts

    artifact = build_artifact(package, intake)
    projection = artifact["by_grammar_unit_id"][unit["grammar_unit_id"]]

    assert projection["projection_status"] == (
        "MASTERY_CANDIDATE_PENDING_RETENTION"
    )
    assert projection["next_route"] == "RETENTION_CHECK_REQUIRED"
    assert projection["final_mastery_status"] == "NOT_CLAIMED"
    assert projection["retention_confirmed"] is False
    assert artifact["coverage_summary"]["mastery_candidate_unit_count"] == 1
    assert artifact["coverage_summary"]["final_mastered_unit_count"] == 0
    assert artifact["continuation_gate"]["next_task"] == (
        "R7-M105S_A1A1PlusTextModeRetentionEvidenceIntake"
    )


def test_full_unit_with_latest_failure_routes_targeted_review():
    package = package_source()
    unit = package["learning_units"][0]
    item_ids = unit_item_ids(unit)
    attempts = [
        fixture_attempt(item_id, 1, passed=True, score=1.0)
        for item_id in item_ids
    ]
    attempts[0] = fixture_attempt(item_ids[0], 1, passed=False, score=0.0)
    intake = blank_intake()
    intake["intake_status"] = "PARTIAL_REAL_EVIDENCE_ACCEPTED"
    intake["accepted_attempts"] = attempts

    artifact = build_artifact(package, intake)
    projection = artifact["by_grammar_unit_id"][unit["grammar_unit_id"]]
    route = artifact["routing"]["targeted_review"][0]

    assert projection["projection_status"] == "REVIEW_REQUIRED"
    assert "UNRESOLVED_LATEST_FAILURE" in projection["review_reasons"]
    assert item_ids[0] in projection["unresolved_failure_item_ids"]
    assert route["review_stages"] == [dict(stage) for stage in REVIEW_STAGES]
    assert route["persistent_queue_write"] is False
    assert artifact["continuation_gate"]["next_task"] == (
        "R7-M105R_A1A1PlusTextModeReviewSessionPackageIntegration"
    )


def test_later_pass_replaces_earlier_failure_for_same_item():
    package = package_source()
    unit = package["learning_units"][0]
    item_ids = unit_item_ids(unit)
    attempts = [
        fixture_attempt(item_id, 1, passed=True, score=1.0)
        for item_id in item_ids
    ]
    attempts[0] = fixture_attempt(item_ids[0], 1, passed=False, score=0.0)
    attempts.append(fixture_attempt(item_ids[0], 2, passed=True, score=1.0))
    intake = blank_intake()
    intake["intake_status"] = "PARTIAL_REAL_EVIDENCE_ACCEPTED"
    intake["accepted_attempts"] = attempts

    artifact = build_artifact(package, intake)
    projection = artifact["by_grammar_unit_id"][unit["grammar_unit_id"]]

    assert projection["unresolved_failure_item_ids"] == []
    assert projection["projection_status"] == (
        "MASTERY_CANDIDATE_PENDING_RETENTION"
    )


def test_row_projection_remains_nonfinal_until_retention():
    package = package_source()
    unit = package["learning_units"][0]
    intake = blank_intake()
    intake["intake_status"] = "PARTIAL_REAL_EVIDENCE_ACCEPTED"
    intake["accepted_attempts"] = [
        fixture_attempt(item_id, 1, passed=True, score=1.0)
        for item_id in unit_item_ids(unit)
    ]

    artifact = build_artifact(package, intake)
    for row_id in unit["canonical_egp_row_ids"]:
        row = artifact["by_egp_row_id"][row_id]
        assert row["final_mastery_status"] == "NOT_CLAIMED"
        assert row["retention_confirmed"] is False


def test_false_final_mastery_and_persistence_claims_fail_closed():
    package = package_source()
    intake = blank_intake()
    artifact = build_artifact(package, intake)
    grammar_id = next(iter(artifact["by_grammar_unit_id"]))
    row_id = next(iter(artifact["by_egp_row_id"]))
    artifact["by_grammar_unit_id"][grammar_id]["final_mastery_status"] = "MASTERED"
    artifact["by_egp_row_id"][row_id]["persistent_learner_state_write"] = True
    artifact["claim_boundaries"]["actual_final_mastery_measured"] = True

    report = validate_artifact(artifact, package, intake)

    assert report["validation_status"] == "FAIL"
    assert f"projection_final_mastery_claimed:{grammar_id}" in report["errors"]
    assert f"projection_row_persistent_write:{row_id}" in report["errors"]
    assert "projection_false_completion_claim:actual_final_mastery_measured" in (
        report["errors"]
    )


def test_projection_is_deterministic_and_does_not_mutate_sources():
    package = package_source()
    intake = blank_intake()
    before = copy.deepcopy((package, intake))

    first = build_artifact(package, intake)
    second = build_artifact(package, intake)

    assert first == second
    assert (package, intake) == before
