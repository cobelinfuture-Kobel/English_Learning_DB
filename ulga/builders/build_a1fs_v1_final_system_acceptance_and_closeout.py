#!/usr/bin/env python3
"""Build the final A1FS-V1 acceptance and closeout evidence artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TASK_ID = "A1FS-V1_FinalSystemAcceptanceAndCloseout"
SCHEMA_VERSION = "a1fs.v1.final_system_acceptance_closeout.v1"
PASS_STATUS = "PASS_A1FS_V1_FINAL_SYSTEM_ACCEPTANCE_AND_CLOSEOUT"
TARGET_SESSION_ID = "R7_TARGETED_FEATURE_RUBRIC_SESSION_001"
TARGET_ATTEMPT_ID = "R5_ATTEMPT:58657b79-7624-4c86-8a6f-b3b1b6e951b0"
TARGET_ITEM_ID = "R4_CANDIDATE_REV2_066E9918A4A282497558"
EXPECTED_REVIEWER_ID = "A1FS_OPERATOR"
EXPECTED_REVIEW_NOTES = (
    'The response refers to a table that is not present in the visible layout and does not '
    'describe the information desk relative to the entrance. The noun phrase "table" also '
    "lacks a determiner."
)
EXPECTED_CRITERIA = {
    "complete_response": False,
    "grammar_target_match": False,
    "meaning_matches_context": False,
}
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Audits final runtime evidence only; cannot create canonical, projection, media, or Excel content."


class CloseoutError(RuntimeError):
    """Raised when a required final-acceptance invariant is not met."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CloseoutError(f"json_unreadable:{Path(path).name}:{exc}") from exc
    if not isinstance(value, dict):
        raise CloseoutError(f"json_object_required:{Path(path).name}")
    return value


def validate_owned_digest(value: Mapping[str, Any], field: str) -> None:
    core = {key: row for key, row in value.items() if key != field}
    if value.get(field) != digest(core):
        raise CloseoutError(f"owned_digest_invalid:{field}")


def atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise CloseoutError(code)


def _runtime_readback(database_path: Path) -> dict[str, Any]:
    uri = f"file:{Path(database_path).resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        row = connection.execute(
            """SELECT se.session_state,a.assignment_state,at.attempt_id,at.session_id,at.item_id,
                      at.validity_status,s.scoring_mode,s.outcome,s.score,s.human_review_required,
                      q.decision,q.reviewer_id,q.reviewed_at,q.criteria_json,q.notes
               FROM edge_attempts at
               JOIN edge_sessions se ON se.session_id=at.session_id
               JOIN edge_assignments a ON a.session_id=at.session_id AND a.item_id=at.item_id
               JOIN edge_scoring_results s ON s.attempt_id=at.attempt_id
               JOIN edge_review_queue q ON q.attempt_id=at.attempt_id
               WHERE at.attempt_id=?""",
            (TARGET_ATTEMPT_ID,),
        ).fetchone()
        reviewed_event_count = connection.execute(
            "SELECT COUNT(*) FROM edge_runtime_events WHERE event_type='EDGE_RESPONSE_REVIEWED' "
            "AND json_extract(payload_json,'$.attempt_id')=?",
            (TARGET_ATTEMPT_ID,),
        ).fetchone()[0]
    finally:
        connection.close()
    _require(integrity == "ok", "database_integrity_failed")
    _require(not foreign_keys, "database_foreign_key_failed")
    _require(row is not None, "target_attempt_missing")
    criteria = json.loads(row["criteria_json"])
    checks = {
        "session_completed": row["session_state"] == "COMPLETED",
        "assignment_submitted": row["assignment_state"] == "SUBMITTED",
        "target_binding_exact": row["session_id"] == TARGET_SESSION_ID and row["item_id"] == TARGET_ITEM_ID,
        "attempt_valid": row["validity_status"] == "VALID",
        "feature_rubric_used": row["scoring_mode"] == "FEATURE_RUBRIC",
        "human_reject_recorded": row["outcome"] == "HUMAN_REJECT" and row["decision"] == "REJECT",
        "score_zero": row["score"] == 0.0,
        "review_resolved": row["human_review_required"] == 0,
        "reviewer_exact": row["reviewer_id"] == EXPECTED_REVIEWER_ID,
        "criteria_exact": criteria == EXPECTED_CRITERIA,
        "review_notes_exact": row["notes"] == EXPECTED_REVIEW_NOTES,
        "review_event_present": reviewed_event_count >= 1,
    }
    for key, passed in checks.items():
        _require(passed, f"runtime_check_failed:{key}")
    return {
        "database_integrity": "PASS",
        "foreign_key_check": "PASS",
        "session_id": TARGET_SESSION_ID,
        "attempt_id": TARGET_ATTEMPT_ID,
        "item_id": TARGET_ITEM_ID,
        "session_state": row["session_state"],
        "assignment_state": row["assignment_state"],
        "scoring_mode": row["scoring_mode"],
        "outcome": row["outcome"],
        "score": row["score"],
        "decision": row["decision"],
        "reviewer_id": row["reviewer_id"],
        "reviewed_at": row["reviewed_at"],
        "criteria": criteria,
        "review_notes_sha256": digest(row["notes"]),
        "review_event_count": reviewed_event_count,
        "checks": checks,
    }


def build(
    *, database_path: Path, evidence_package: Mapping[str, Any], intake: Mapping[str, Any],
    representative_gate: Mapping[str, Any],
) -> dict[str, Any]:
    validate_owned_digest(evidence_package, "package_sha256")
    validate_owned_digest(intake, "intake_sha256")
    validate_owned_digest(representative_gate, "artifact_sha256")
    runtime = _runtime_readback(database_path)

    entries = evidence_package.get("entries") or []
    target_entries = [row for row in entries if row.get("attempt_id") == TARGET_ATTEMPT_ID]
    _require(len(target_entries) == 1, "target_evidence_entry_count_invalid")
    target = target_entries[0]
    review = target.get("operator_review") or {}
    _require(target.get("session_id") == TARGET_SESSION_ID, "evidence_session_binding_invalid")
    _require(target.get("item_id") == TARGET_ITEM_ID, "evidence_item_binding_invalid")
    _require(target.get("scoring_mode") == "FEATURE_RUBRIC", "evidence_scoring_mode_invalid")
    _require(target.get("outcome") == "HUMAN_REJECT" and target.get("score") == 0.0, "evidence_review_outcome_invalid")
    _require(review.get("decision") == "REJECT", "evidence_review_decision_invalid")
    _require(review.get("criteria") == EXPECTED_CRITERIA, "evidence_review_criteria_invalid")
    _require(review.get("notes") == EXPECTED_REVIEW_NOTES, "evidence_review_notes_invalid")

    boundaries = evidence_package.get("claim_boundaries") or {}
    _require(len(entries) == 11, "cumulative_real_attempt_count_invalid")
    _require(boundaries.get("mastery_written") is False, "mastery_boundary_broken")
    _require(boundaries.get("retention_confirmed") is False, "retention_boundary_broken")
    _require(boundaries.get("a2_unlocked") is False, "a2_boundary_broken")

    intake_counts = intake.get("counts") or {}
    _require(intake_counts.get("real_attempt_count") == 11, "intake_attempt_count_invalid")
    _require(intake_counts.get("valid_real_evidence_ready_count") == 11, "intake_ready_count_invalid")
    for field in (
        "synthetic_evidence_count", "candidate_binding_mismatch_count",
        "deployment_binding_mismatch_count", "evidence_invalidated_count",
        "system_error_retry_required_count", "duplicate_evidence_ignored_count",
        "human_scoring_required_count",
    ):
        _require(intake_counts.get(field) == 0, f"intake_nonzero:{field}")

    gate_counts = representative_gate.get("counts") or {}
    verification = representative_gate.get("verification") or {}
    coverage = representative_gate.get("coverage") or {}
    _require(
        representative_gate.get("representative_acceptance_status")
        == "PASS_R7_REPRESENTATIVE_REAL_EVIDENCE_ACCEPTANCE",
        "representative_gate_not_passed",
    )
    _require(representative_gate.get("next_resume_task") == TASK_ID, "representative_gate_route_invalid")
    _require(verification.get("human_review_path_status") == "VERIFIED", "human_review_path_not_verified")
    _require(verification.get("required_representative_coverage_complete") is True, "coverage_not_complete")
    _require(not any((coverage.get("missing") or {}).values()), "coverage_missing_not_empty")
    _require("WRITING" in (coverage.get("evidenced") or {}).get("skills", []), "writing_coverage_missing")
    _require("FEATURE_RUBRIC" in (coverage.get("evidenced") or {}).get("scoring_modes", []), "feature_rubric_coverage_missing")
    expected_gate_counts = {
        "real_valid_attempt_count": 11,
        "scoring_reproducibility_count": 11,
        "scoring_reproducibility_failure_count": 0,
        "binding_error_count": 0,
        "system_error_count": 0,
        "synthetic_evidence_count": 0,
        "identified_engineering_defect_count": 4,
        "remediated_engineering_defect_count": 4,
        "unresolved_engineering_defect_count": 0,
        "targeted_additional_real_session_count": 0,
    }
    for field, expected in expected_gate_counts.items():
        _require(gate_counts.get(field) == expected, f"representative_count_invalid:{field}")

    artifact: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "content_policy_mode": A1FS_CONTENT_POLICY_MODE,
        "source_bindings": {
            "evidence_package_sha256": evidence_package["package_sha256"],
            "intake_sha256": intake["intake_sha256"],
            "representative_gate_sha256": representative_gate["artifact_sha256"],
        },
        "runtime_readback": runtime,
        "counts": {
            "cumulative_real_attempt_count": len(entries),
            "valid_real_evidence_ready_count": intake_counts["valid_real_evidence_ready_count"],
            "scoring_reproducibility_count": gate_counts["scoring_reproducibility_count"],
            "scoring_reproducibility_failure_count": gate_counts["scoring_reproducibility_failure_count"],
            "identified_engineering_defect_count": gate_counts["identified_engineering_defect_count"],
            "remediated_engineering_defect_count": gate_counts["remediated_engineering_defect_count"],
            "unresolved_engineering_defect_count": gate_counts["unresolved_engineering_defect_count"],
            "synthetic_evidence_count": 0,
        },
        "coverage": {
            "human_review_path_status": verification["human_review_path_status"],
            "writing_covered": True,
            "feature_rubric_covered": True,
            "representative_coverage_complete": True,
            "missing": coverage["missing"],
        },
        "claim_boundaries": {
            "r4_bank_changed": False,
            "candidate_identity_changed_count": 0,
            "a2_unlocked": False,
            "mastery_written": False,
            "retention_confirmed": False,
        },
        "final_acceptance_status": PASS_STATUS,
        "english_grammar_status": "PASS_A1FS_V1_SYSTEM_ACCEPTED_AND_CLOSED",
        "stop_reason": "NONE",
        "blocker_type": "NONE",
        "required_operator_action": "NONE",
        "last_completed": "A1FS-V1_FinalSystemAcceptanceAndCloseout",
        "next_resume_task": "NONE",
        "mainline_distance_delta": 0,
    }
    artifact["artifact_sha256"] = digest(artifact)
    return artifact


def safe_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    runtime = artifact["runtime_readback"]
    safe = {
        "task_id": artifact["task_id"],
        "schema_version": artifact["schema_version"],
        "source_bindings": artifact["source_bindings"],
        "targeted_review": {
            "session_state": runtime["session_state"],
            "assignment_state": runtime["assignment_state"],
            "scoring_mode": runtime["scoring_mode"],
            "outcome": runtime["outcome"],
            "score": runtime["score"],
            "decision": runtime["decision"],
            "criteria": runtime["criteria"],
            "review_notes_sha256": runtime["review_notes_sha256"],
        },
        "counts": artifact["counts"],
        "coverage": artifact["coverage"],
        "claim_boundaries": artifact["claim_boundaries"],
        "final_acceptance_status": artifact["final_acceptance_status"],
        "english_grammar_status": artifact["english_grammar_status"],
        "stop_reason": artifact["stop_reason"],
        "blocker_type": artifact["blocker_type"],
        "required_operator_action": artifact["required_operator_action"],
        "next_resume_task": artifact["next_resume_task"],
        "mainline_distance_delta": artifact["mainline_distance_delta"],
    }
    safe["artifact_sha256"] = digest(safe)
    return safe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--evidence-package", type=Path, required=True)
    parser.add_argument("--intake", type=Path, required=True)
    parser.add_argument("--representative-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--safe-output", type=Path, required=True)
    args = parser.parse_args(argv)
    artifact = build(
        database_path=args.database,
        evidence_package=read_json(args.evidence_package),
        intake=read_json(args.intake),
        representative_gate=read_json(args.representative_gate),
    )
    atomic_write(args.output, artifact)
    atomic_write(args.safe_output, safe_artifact(artifact))
    print(json.dumps({
        "final_acceptance_status": artifact["final_acceptance_status"],
        "artifact_sha256": artifact["artifact_sha256"],
        "output": str(args.output),
        "safe_output": str(args.safe_output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
