from __future__ import annotations

import copy

import pytest

from ulga.builders import build_a1fs_v1_post_cp07_controlled_runtime_usability_product_gap_recheck as builder
from ulga.builders import run_a1fs_v1_cp07f_real_learner_end_to_end_acceptance as cp07f
from ulga.validators import validate_a1fs_v1_post_cp07_controlled_runtime_usability_product_gap_recheck as validator


def cp07f_report(status: str) -> dict:
    real = status == cp07f.REAL_STATUS
    fixture = status == cp07f.TEST_STATUS
    return {
        "task_id": cp07f.TASK_ID,
        "program_id": cp07f.PROGRAM_ID,
        "schema_version": cp07f.REPORT_SCHEMA_VERSION,
        "mode": "VALIDATE" if status != cp07f.PREPARE_STATUS else "PREPARE",
        "evidence_origin": "REAL_LEARNER" if real else ("TEST_FIXTURE" if fixture else "NONE"),
        "validation_status": status,
        "aggregate_readback": {
            "attempted_skill_count": 4 if status != cp07f.PREPARE_STATUS else 0,
            "resolved_attempt_count": 11 if status != cp07f.PREPARE_STATUS else 0,
            "attempted_grammar_unit_count": 6 if status != cp07f.PREPARE_STATUS else 0,
            "m7_diagnosis_count": 1 if status != cp07f.PREPARE_STATUS else 0,
            "completed_remediation_count": 1 if status != cp07f.PREPARE_STATUS else 0,
            "completed_reassessment_count": 1 if status != cp07f.PREPARE_STATUS else 0,
            "m8_review_event_count": 1 if status != cp07f.PREPARE_STATUS else 0,
        },
        "acceptance_gate": {
            "listening_audio_registered": status != cp07f.PREPARE_STATUS,
            "speaking_consented_recording_registered": status != cp07f.PREPARE_STATUS,
        },
        "real_learner_evidence_captured": real,
        "real_learner_acceptance_completed": real,
        "real_retention_claimed": False,
        "a2_a2plus_status": "LOCKED",
        "claim_boundaries": {
            "public_delivery_claimed": False,
            "canonical_authority_changed": False,
            "test_fixture_counted_as_real": False,
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
        },
        "errors": [],
        "stop_reason": "NONE" if real else "REAL_LEARNER_FOUR_SKILL_EVIDENCE_REQUIRED",
        "next_short_step": cp07f.NEXT_SHORT_STEP if real else cp07f.TASK_ID,
    }


def test_prepare_state_stays_pending_and_does_not_claim_usability() -> None:
    artifact = builder.build_artifact(cp07f_report(cp07f.PREPARE_STATUS))
    assert artifact["validation_status"] == builder.PENDING_STATUS
    assert artifact["capability_state"]["controlled_runtime_usable"] is False
    assert artifact["mainline_distance_gate"]["overall_progress_increase_allowed"] is False
    assert artifact["counts"]["blocking_gap_count"] >= 1
    assert artifact["next_short_step"] == builder.NEXT_REAL_ACCEPTANCE


def test_test_fixture_never_promotes_to_real_runtime_usability() -> None:
    artifact = builder.build_artifact(cp07f_report(cp07f.TEST_STATUS))
    assert artifact["capability_state"]["test_fixture_only"] is True
    assert artifact["capability_state"]["real_four_skill_acceptance"] is False
    assert artifact["capability_state"]["controlled_runtime_usable"] is False
    assert artifact["claim_boundaries"]["test_fixture_promoted_to_real"] is False


def test_real_cp07f_acceptance_classifies_controlled_runtime_as_usable() -> None:
    source = cp07f_report(cp07f.REAL_STATUS)
    artifact = builder.build_artifact(source)
    assert artifact["validation_status"] == builder.USABLE_STATUS
    assert artifact["capability_state"]["controlled_runtime_usable"] is True
    assert artifact["capability_state"]["complete_product"] is False
    assert artifact["counts"]["blocking_gap_count"] == 0
    assert {row["gap_id"] for row in artifact["remaining_product_gaps"]} == {
        "REAL_RETENTION_LONGITUDINAL_EVIDENCE",
        "FULL_24_UNIT_REAL_ATTEMPT_COVERAGE",
        "PUBLIC_DELIVERY_OPERATIONAL_READINESS",
    }
    assert artifact["next_short_step"] == builder.NEXT_RETENTION_PILOT
    report = validator.validate_artifact(artifact, source)
    assert report["error_count"] == 0


def test_real_status_with_missing_media_fails_closed() -> None:
    source = cp07f_report(cp07f.REAL_STATUS)
    source["acceptance_gate"]["speaking_consented_recording_registered"] = False
    with pytest.raises(builder.ProductGapError, match="internal_gate_mismatch"):
        builder.build_artifact(source)


def test_validator_detects_tampered_complete_product_claim() -> None:
    source = cp07f_report(cp07f.REAL_STATUS)
    artifact = builder.build_artifact(source)
    artifact = copy.deepcopy(artifact)
    artifact["mainline_distance_gate"]["complete_product"] = True
    unsigned = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    artifact["artifact_sha256"] = builder.digest(unsigned)
    report = validator.validate_artifact(artifact, source)
    assert report["error_count"] > 0
    assert "complete_product_claim_forbidden" in report["errors"]
