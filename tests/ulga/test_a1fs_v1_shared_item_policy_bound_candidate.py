from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as envelope_builder
from ulga.builders import build_a1fs_v1_shared_item_policy_bound_candidate as builder
from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as envelope_validator
from ulga.validators import validate_a1fs_v1_shared_item_policy_bound_candidate as validator


@pytest.fixture(scope="module")
def candidate():
    return builder.build_policy_bound_candidate()


def test_real_384_item_source_materializes_as_policy_bound_candidate(candidate):
    envelope = envelope_validator.validate_artifact(
        candidate,
        expected_role="CANDIDATE_JSON",
    )
    report = validator.validate_candidate(candidate)

    assert envelope["error_count"] == 0, envelope["errors"]
    assert report["validation_status"] == validator.PASS_STATUS, report["errors"]
    assert report["shared_item_count"] == 384
    assert report["skill_item_counts"] == validator.EXPECTED_SKILL_COUNTS
    assert candidate["artifact_role"] == "CANDIDATE_JSON"
    assert candidate["learner_facing"] is False
    assert candidate["admission"] == {
        "status": "PENDING_VALIDATION",
        "decision_ref": None,
    }


def test_candidate_preserves_existing_m03_artifact_without_canonical_admission(candidate):
    payload = candidate["payload"]
    source_bindings = candidate["source_bindings"]

    assert payload["task_id"] == "E4S-A1V1-M03_SharedItemAnswerScoringMediaContract"
    assert payload["artifact_id"] == "e4s_a1v1_shared_item_contract"
    assert payload["schema_version"] == "e4s.a1v1.shared_item.v1"
    assert payload["coverage_summary"]["shared_item_count"] == 384
    assert source_bindings["source_artifact_sha256"] == validator.digest(payload)
    assert source_bindings["source_builder_path"] == (
        "ulga/builders/build_a1_a1plus_shared_item_contract.py"
    )
    assert source_bindings["source_validator_path"] == (
        "ulga/validators/validate_a1_a1plus_shared_item_contract.py"
    )
    assert candidate["validation_receipts"] == []


def test_all_384_item_identities_and_four_skill_counts_are_preserved(candidate):
    items = candidate["payload"]["shared_items"]
    assert len(items) == 384
    assert len({row["shared_item_id"] for row in items}) == 384
    assert len({row["source_item_id"] for row in items}) == 384
    assert {
        skill: sum(row["skill"] == skill for row in items)
        for skill in ("reading", "writing", "listening", "speaking")
    } == validator.EXPECTED_SKILL_COUNTS


def test_a2_item_injection_fails_even_when_outer_hash_is_rebuilt(candidate):
    tampered = deepcopy(candidate)
    tampered["payload"]["shared_items"][0]["official_cefr_level"] = "A2"
    tampered["source_bindings"]["source_artifact_sha256"] = validator.digest(
        tampered["payload"]
    )
    tampered["artifact_sha256"] = envelope_builder.digest(
        {
            key: value
            for key, value in tampered.items()
            if key != "artifact_sha256"
        }
    )

    report = validator.validate_candidate(tampered)
    assert report["validation_status"] == "FAIL"
    assert "a2_or_out_of_scope_item_detected" in report["errors"]


def test_payload_drift_fails_source_lineage_and_envelope_identity(candidate):
    tampered = deepcopy(candidate)
    tampered["payload"]["shared_items"][0]["task_type"] = "TAMPERED"

    report = validator.validate_candidate(tampered)
    assert report["validation_status"] == "FAIL"
    assert "envelope:artifact_sha256_mismatch" in report["errors"]
    assert "source_artifact_sha256_mismatch" in report["errors"]


def test_source_validator_failure_stops_materialization(monkeypatch):
    monkeypatch.setattr(
        builder,
        "validate_shared_item_contract",
        lambda _artifact: {"validation_status": "FAIL", "errors": ["fixture"]},
    )
    with pytest.raises(
        builder.SharedItemCandidateBuildError,
        match="source_validation_not_pass",
    ):
        builder.build_policy_bound_candidate()
