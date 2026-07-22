import json
import sqlite3

import pytest

from ulga.builders import build_a1fs_v1_final_system_acceptance_and_closeout as closeout
from ulga.validators import validate_a1fs_v1_final_system_acceptance_and_closeout as validator


def _owned(value, field):
    value[field] = closeout.digest(value)
    return value


def _fixture(tmp_path):
    database = tmp_path / "runtime.sqlite3"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE edge_sessions(session_id TEXT PRIMARY KEY,session_state TEXT);
        CREATE TABLE edge_assignments(session_id TEXT,item_id TEXT,assignment_state TEXT);
        CREATE TABLE edge_attempts(
          attempt_id TEXT PRIMARY KEY,session_id TEXT,item_id TEXT,validity_status TEXT);
        CREATE TABLE edge_scoring_results(
          attempt_id TEXT PRIMARY KEY,scoring_mode TEXT,outcome TEXT,score REAL,human_review_required INTEGER);
        CREATE TABLE edge_review_queue(
          attempt_id TEXT PRIMARY KEY,decision TEXT,reviewer_id TEXT,reviewed_at TEXT,
          criteria_json TEXT,notes TEXT);
        CREATE TABLE edge_runtime_events(event_type TEXT,payload_json TEXT);
        """
    )
    connection.execute(
        "INSERT INTO edge_sessions VALUES(?,?)",
        (closeout.TARGET_SESSION_ID, "COMPLETED"),
    )
    connection.execute(
        "INSERT INTO edge_assignments VALUES(?,?,?)",
        (closeout.TARGET_SESSION_ID, closeout.TARGET_ITEM_ID, "SUBMITTED"),
    )
    connection.execute(
        "INSERT INTO edge_attempts VALUES(?,?,?,?)",
        (closeout.TARGET_ATTEMPT_ID, closeout.TARGET_SESSION_ID, closeout.TARGET_ITEM_ID, "VALID"),
    )
    connection.execute(
        "INSERT INTO edge_scoring_results VALUES(?,?,?,?,?)",
        (closeout.TARGET_ATTEMPT_ID, "FEATURE_RUBRIC", "HUMAN_REJECT", 0.0, 0),
    )
    connection.execute(
        "INSERT INTO edge_review_queue VALUES(?,?,?,?,?,?)",
        (
            closeout.TARGET_ATTEMPT_ID, "REJECT", closeout.EXPECTED_REVIEWER_ID,
            "2026-07-22T01:06:39Z", closeout.canonical(closeout.EXPECTED_CRITERIA),
            closeout.EXPECTED_REVIEW_NOTES,
        ),
    )
    connection.execute(
        "INSERT INTO edge_runtime_events VALUES(?,?)",
        ("EDGE_RESPONSE_REVIEWED", closeout.canonical({"attempt_id": closeout.TARGET_ATTEMPT_ID})),
    )
    connection.commit()
    connection.close()

    target = {
        "attempt_id": closeout.TARGET_ATTEMPT_ID,
        "session_id": closeout.TARGET_SESSION_ID,
        "item_id": closeout.TARGET_ITEM_ID,
        "scoring_mode": "FEATURE_RUBRIC",
        "outcome": "HUMAN_REJECT",
        "score": 0.0,
        "operator_review": {
            "decision": "REJECT", "reviewer_id": closeout.EXPECTED_REVIEWER_ID,
            "criteria": closeout.EXPECTED_CRITERIA, "notes": closeout.EXPECTED_REVIEW_NOTES,
        },
    }
    evidence = _owned({
        "entries": [target, *[{"attempt_id": f"A{i}"} for i in range(10)]],
        "claim_boundaries": {
            "mastery_written": False, "retention_confirmed": False, "a2_unlocked": False,
        },
    }, "package_sha256")
    intake = _owned({"counts": {
        "real_attempt_count": 11, "valid_real_evidence_ready_count": 11,
        "synthetic_evidence_count": 0, "candidate_binding_mismatch_count": 0,
        "deployment_binding_mismatch_count": 0, "evidence_invalidated_count": 0,
        "system_error_retry_required_count": 0, "duplicate_evidence_ignored_count": 0,
        "human_scoring_required_count": 0,
    }}, "intake_sha256")
    gate = _owned({
        "representative_acceptance_status": "PASS_R7_REPRESENTATIVE_REAL_EVIDENCE_ACCEPTANCE",
        "next_resume_task": closeout.TASK_ID,
        "counts": {
            "real_valid_attempt_count": 11, "scoring_reproducibility_count": 11,
            "scoring_reproducibility_failure_count": 0, "binding_error_count": 0,
            "system_error_count": 0, "synthetic_evidence_count": 0,
            "identified_engineering_defect_count": 4, "remediated_engineering_defect_count": 4,
            "unresolved_engineering_defect_count": 0, "targeted_additional_real_session_count": 0,
        },
        "verification": {
            "human_review_path_status": "VERIFIED",
            "required_representative_coverage_complete": True,
        },
        "coverage": {
            "evidenced": {"skills": ["READING", "WRITING"], "scoring_modes": ["FEATURE_RUBRIC"]},
            "missing": {"skills": [], "scoring_modes": [], "source_kinds": []},
        },
    }, "artifact_sha256")
    return database, evidence, intake, gate


def test_final_closeout_is_idempotent_and_passes_independent_validation(tmp_path):
    database, evidence, intake, gate = _fixture(tmp_path)
    first = closeout.build(
        database_path=database, evidence_package=evidence, intake=intake, representative_gate=gate,
    )
    second = closeout.build(
        database_path=database, evidence_package=evidence, intake=intake, representative_gate=gate,
    )
    assert first == second
    assert first["final_acceptance_status"] == closeout.PASS_STATUS
    assert first["coverage"]["human_review_path_status"] == "VERIFIED"
    assert first["coverage"]["writing_covered"] is True
    assert first["coverage"]["feature_rubric_covered"] is True
    safe = closeout.safe_artifact(first)
    result = validator.validate_artifact(first, safe)
    assert result["error_count"] == 0
    serialized = closeout.canonical(safe)
    assert closeout.EXPECTED_REVIEW_NOTES not in serialized
    assert closeout.TARGET_ATTEMPT_ID not in serialized


def test_closeout_rejects_non_exact_review_notes(tmp_path):
    database, evidence, intake, gate = _fixture(tmp_path)
    evidence["entries"][0]["operator_review"]["notes"] = "Different notes"
    evidence.pop("package_sha256")
    _owned(evidence, "package_sha256")
    with pytest.raises(closeout.CloseoutError, match="evidence_review_notes_invalid"):
        closeout.build(
            database_path=database, evidence_package=evidence, intake=intake, representative_gate=gate,
        )


def test_validator_rejects_tampering(tmp_path):
    database, evidence, intake, gate = _fixture(tmp_path)
    artifact = closeout.build(
        database_path=database, evidence_package=evidence, intake=intake, representative_gate=gate,
    )
    artifact["counts"]["synthetic_evidence_count"] = 1
    result = validator.validate_artifact(artifact)
    assert "artifact_digest_invalid" in result["errors"]
    assert "counts_invalid" in result["errors"]
