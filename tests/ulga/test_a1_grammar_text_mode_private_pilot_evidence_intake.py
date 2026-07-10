from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.builders.build_a1_grammar_text_mode_private_pilot_evidence_intake import (
    INTAKE_PATH,
    normalize_and_validate,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_package_source,
)


def package():
    artifact, report = build_package_source()
    assert report["validation_status"] == "PASS"
    return artifact


def pending_payload():
    return json.loads(Path(INTAKE_PATH).read_text(encoding="utf-8"))


def session(*, complete: bool = False):
    return {
        "session_id": "session:A1_TEXT_001",
        "learner_ref": "learner:PRIVATE_001",
        "operator_ref": "operator:cobelinfuture-Kobel",
        "started_at": "2026-07-10T18:00:00+08:00",
        "completed_at": "2026-07-10T18:30:00+08:00" if complete else None,
        "delivery_environment": "LOCAL_PRIVATE_TEXT_MODE",
        "evidence_source_ref": "local_private_pilot://A1_TEXT_001",
    }


def attempt(item, sequence: int, *, passed: bool = True):
    target = item.get("answer_key", {}).get("canonical_target", "learner response")
    return {
        "event_id": f"event:{item['item_id']}:{sequence}",
        "item_id": item["item_id"],
        "attempt_sequence": sequence,
        "submitted_at": "2026-07-10T18:10:00+08:00",
        "response_text": target if passed else "incorrect learner response",
        "score": 1.0 if passed else 0.0,
        "passed": passed,
        "outcome": "PASS" if passed else "FAIL",
        "error_tags": [] if passed else ["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"],
        "evaluator_type": "MANUAL",
        "evaluator_ref": "operator:cobelinfuture-Kobel",
        "evidence_ref": f"local_private_pilot://A1_TEXT_001/{item['item_id']}/{sequence}",
        "synthetic_fixture": False,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
    }


def evidence_payload(attempts, claim: str, *, complete: bool = False):
    payload = pending_payload()
    payload["session"] = session(complete=complete)
    payload["pilot_completion_claim"] = claim
    payload["attempts"] = attempts
    return payload


def test_pending_manifest_passes_pipeline_readiness_without_starting_pilot():
    artifact, report = normalize_and_validate(pending_payload(), package())

    assert report["validation_status"] == "PASS"
    assert report["intake_status"] == "READY_AWAITING_REAL_ATTEMPTS"
    assert report["stop_reason"] == "REAL_LEARNER_EVIDENCE_REQUIRED"
    assert artifact["coverage_summary"]["actual_attempt_count"] == 0
    assert artifact["claim_boundaries"]["text_mode_private_pilot_started"] is False
    assert artifact["claim_boundaries"]["actual_mastery_measured"] is False


def test_one_real_attempt_is_accepted_as_partial_and_identity_is_derived():
    source_package = package()
    item = source_package["item_bank"][0]
    payload = evidence_payload([attempt(item, 1)], "PARTIAL")

    artifact, report = normalize_and_validate(payload, source_package)

    assert report["validation_status"] == "PASS"
    assert report["intake_status"] == "PARTIAL_REAL_EVIDENCE_ACCEPTED"
    assert report["stop_reason"] == "NONE"
    assert artifact["coverage_summary"]["actual_attempt_count"] == 1
    assert artifact["claim_boundaries"]["text_mode_private_pilot_started"] is True
    accepted = artifact["accepted_attempts"][0]
    assert accepted["grammar_unit_id"] == item["content_binding"]["grammar_focus"][0]
    assert accepted["canonical_egp_row_ids"] == item["content_binding"]["canonical_egp_row_ids"]
    assert accepted["skill"] == item["skill"]
    assert accepted["learner_state_write"] is False


def test_full_192_item_attempt_set_opens_projection_gate_but_not_mastery():
    source_package = package()
    attempts = [
        attempt(item, 1)
        for item in source_package["item_bank"]
    ]
    payload = evidence_payload(attempts, "COMPLETE", complete=True)

    artifact, report = normalize_and_validate(payload, source_package)

    assert report["validation_status"] == "PASS"
    assert report["intake_status"] == "FULL_PACKAGE_REAL_EVIDENCE_ACCEPTED"
    assert artifact["coverage_summary"]["unique_attempted_item_count"] == 192
    assert artifact["coverage_summary"]["completed_unit_count"] == 24
    assert artifact["release_gates"]["mastery_projection_gate"] == "READY_FOR_PROJECTION"
    assert artifact["claim_boundaries"]["full_package_attempt_coverage_complete"] is True
    assert artifact["claim_boundaries"]["actual_mastery_measured"] is False


def test_unknown_item_fails_closed():
    source_package = package()
    raw = attempt(source_package["item_bank"][0], 1)
    raw["item_id"] = "UNKNOWN_ITEM"
    payload = evidence_payload([raw], "PARTIAL")

    _, report = normalize_and_validate(payload, source_package)

    assert report["validation_status"] == "FAIL"
    assert any("unknown_item_id:UNKNOWN_ITEM" in error for error in report["errors"])


def test_synthetic_fixture_is_rejected_as_real_evidence():
    source_package = package()
    raw = attempt(source_package["item_bank"][0], 1)
    raw["synthetic_fixture"] = True
    payload = evidence_payload([raw], "PARTIAL")

    artifact, report = normalize_and_validate(payload, source_package)

    assert report["validation_status"] == "FAIL"
    assert any("synthetic_fixture_forbidden" in error for error in report["errors"])
    assert artifact["accepted_attempts"] == []


def test_forged_complete_claim_is_rejected():
    source_package = package()
    raw = attempt(source_package["item_bank"][0], 1)
    payload = evidence_payload([raw], "COMPLETE", complete=True)

    _, report = normalize_and_validate(payload, source_package)

    assert report["validation_status"] == "FAIL"
    assert "pilot_completion_claim_mismatch:COMPLETE:PARTIAL" in report["errors"]


def test_passed_attempt_cannot_carry_error_tags():
    source_package = package()
    raw = attempt(source_package["item_bank"][0], 1)
    raw["error_tags"] = ["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"]
    payload = evidence_payload([raw], "PARTIAL")

    _, report = normalize_and_validate(payload, source_package)

    assert report["validation_status"] == "FAIL"
    assert any("passed_attempt_has_error_tags" in error for error in report["errors"])


def test_failed_attempt_requires_error_tag():
    source_package = package()
    raw = attempt(source_package["item_bank"][0], 1, passed=False)
    raw["error_tags"] = []
    payload = evidence_payload([raw], "PARTIAL")

    _, report = normalize_and_validate(payload, source_package)

    assert report["validation_status"] == "FAIL"
    assert any("failed_attempt_missing_error_tag" in error for error in report["errors"])


def test_unknown_error_tag_is_rejected():
    source_package = package()
    raw = attempt(source_package["item_bank"][0], 1, passed=False)
    raw["error_tags"] = ["ERR_NOT_IN_TAXONOMY"]
    payload = evidence_payload([raw], "PARTIAL")

    _, report = normalize_and_validate(payload, source_package)

    assert report["validation_status"] == "FAIL"
    assert any("unknown_error_tags:ERR_NOT_IN_TAXONOMY" in error for error in report["errors"])


def test_persistent_write_and_production_event_are_rejected():
    source_package = package()
    raw = attempt(source_package["item_bank"][0], 1)
    raw["persistent_learner_state_write"] = True
    raw["production_runtime_event"] = True
    payload = evidence_payload([raw], "PARTIAL")

    _, report = normalize_and_validate(payload, source_package)

    assert report["validation_status"] == "FAIL"
    assert any("persistent_learner_state_write_forbidden" in error for error in report["errors"])
    assert any("production_runtime_event_forbidden" in error for error in report["errors"])


def test_builder_does_not_mutate_payload_or_package():
    source_package = package()
    payload = evidence_payload([attempt(source_package["item_bank"][0], 1)], "PARTIAL")
    before = copy.deepcopy((payload, source_package))

    normalize_and_validate(payload, source_package)

    assert (payload, source_package) == before
