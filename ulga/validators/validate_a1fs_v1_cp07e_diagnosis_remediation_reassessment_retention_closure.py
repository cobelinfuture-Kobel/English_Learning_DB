#!/usr/bin/env python3
"""Independently validate CP07E M7/M8 contract closure and safe readback."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_cp07e_diagnosis_remediation_reassessment_retention_closure as builder
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7
from ulga.builders import build_a1fs_v1_m8_review_scheduling_retention_spaced_practice as m8

FAIL_STATUS = "FAIL_CP07E_DIAGNOSIS_REMEDIATION_REASSESSMENT_RETENTION_CONTRACT"


class CP07EValidationError(ValueError):
    """Independent CP07E validation error."""


def _read(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CP07EValidationError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise CP07EValidationError(f"{code}_object_required")
    return value


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise CP07EValidationError(code)


def _safe_walk(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            _require(str(key) not in builder.FORBIDDEN_SAFE_KEYS, f"private_key_in_safe_readback:{path}.{key}")
            _safe_walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _safe_walk(child, f"{path}[{index}]")


def _validate_sources(
    artifact: Mapping[str, Any],
    *,
    database: Path,
    graph_path: Path,
    consumer_path: Path,
    review_references_path: Path,
    m7_snapshot_path: Path,
    m8_snapshot_path: Path,
) -> dict[str, int]:
    consumer = _read(consumer_path, "cp07d_consumer")
    graph = _read(graph_path, "m1_graph")
    references_artifact = _read(review_references_path, "review_references")
    m7_snapshot = _read(m7_snapshot_path, "m7_snapshot")
    m8_snapshot = _read(m8_snapshot_path, "m8_snapshot")

    contract = builder._verify_consumer(consumer)
    builder._verify_graph(graph)
    references = builder._review_references(references_artifact)
    m7_counts = builder._closed_m7(m7_snapshot)
    m8_counts = builder._closed_m8(m8_snapshot)

    source_identity = artifact.get("source_identity")
    _require(isinstance(source_identity, Mapping), "source_identity_required")
    expected_hashes = {
        "cp07d_consumer_sha256": builder._digest(consumer),
        "m1_graph_sha256": builder._digest(graph),
        "review_reference_set_sha256": builder._digest(references_artifact),
        "m7_snapshot_sha256": builder._digest(m7_snapshot),
        "m8_snapshot_sha256": builder._digest(m8_snapshot),
        "runtime_database_sha256": hashlib.sha256(Path(database).read_bytes()).hexdigest(),
    }
    _require(dict(source_identity) == expected_hashes, "source_identity_hash_mismatch")

    runtime = artifact.get("runtime_selection")
    _require(isinstance(runtime, Mapping), "runtime_selection_required")
    _require(runtime.get("selected_lesson_id") == contract.get("selected_lesson_id"), "selected_lesson_drift")
    _require(runtime.get("selected_skill") == contract.get("selected_skill"), "selected_skill_drift")
    _require(runtime.get("selected_level") == contract.get("selected_level"), "selected_level_drift")
    _require(runtime.get("projected_asset_count") == len(contract.get("projected_asset_keys", [])), "projected_asset_count_mismatch")
    _require(runtime.get("review_reference_count") == len(references), "review_reference_count_mismatch")
    learner_ref = runtime.get("learner_ref_sha256")
    _require(isinstance(learner_ref, str) and len(learner_ref) == 64, "learner_ref_hash_invalid")

    _require(m7_snapshot.get("task_id") == m7.TASK_ID, "m7_task_id_invalid")
    _require(m7_snapshot.get("schema_version") == m7.SCHEMA_VERSION, "m7_schema_invalid")
    _require(m7_snapshot.get("validation_status") == m7.STATUS, "m7_status_invalid")
    _require(m8_snapshot.get("task_id") == m8.TASK_ID, "m8_task_id_invalid")
    _require(m8_snapshot.get("schema_version") == m8.SCHEMA_VERSION, "m8_schema_invalid")
    _require(m8_snapshot.get("validation_status") == m8.STATUS, "m8_status_invalid")
    _require(m8_snapshot.get("source_m7_snapshot_digest") == builder._digest(m7_snapshot), "m8_m7_binding_mismatch")

    expected_review_pairs = {(row["node_id"], row["attempt_id"]) for row in references}
    actual_review_pairs = {
        (str(row.get("node_id") or ""), str(row.get("attempt_id") or ""))
        for row in m8_snapshot.get("review_events", [])
        if isinstance(row, Mapping)
    }
    _require(expected_review_pairs == actual_review_pairs, "review_reference_event_set_mismatch")

    m7_artifact = artifact.get("m7_closure")
    _require(isinstance(m7_artifact, Mapping), "m7_closure_required")
    expected_m7 = {
        "required_mastery_node_count": int(m7_snapshot["required_mastery_node_count"]),
        "mastered_required_count": int(m7_snapshot["mastered_required_count"]),
        "a2_lock_state_in_canary": str(m7_snapshot["a2_lock_state"]),
        **m7_counts,
    }
    _require(dict(m7_artifact) == expected_m7, "m7_closure_count_mismatch")

    m8_artifact = artifact.get("m8_closure")
    _require(isinstance(m8_artifact, Mapping), "m8_closure_required")
    expected_m8 = {
        "scheduled_node_count": int(m8_snapshot["scheduled_node_count"]),
        "synthetic_retention_state_reached": bool(m8_snapshot["retention_confirmed"]),
        **m8_counts,
    }
    _require(dict(m8_artifact) == expected_m8, "m8_closure_count_mismatch")

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        _require(metadata.get("validation_status") == m3.STATUS, "database_m3_status_invalid")
        _require(metadata.get("m6_validation_status") == m6.STATUS, "database_m6_status_invalid")
        _require(metadata.get("consumer_sha256") == hashlib.sha256(Path(consumer_path).read_bytes()).hexdigest(), "database_consumer_raw_hash_mismatch")
        m7_metadata = dict(connection.execute("SELECT key,value FROM m7_metadata"))
        m8_metadata = dict(connection.execute("SELECT key,value FROM m8_metadata"))
        _require(m7_metadata.get("validation_status") == m7.STATUS, "database_m7_status_invalid")
        _require(m8_metadata.get("validation_status") == m8.STATUS, "database_m8_status_invalid")
        _require(m8_metadata.get("source_m7_snapshot_digest") == builder._digest(m7_snapshot), "database_m8_m7_digest_mismatch")
        persisted_m7 = connection.execute(
            "SELECT COUNT(*) FROM mastery_snapshots WHERE snapshot_digest=?",
            (builder._digest(m7_snapshot),),
        ).fetchone()[0]
        _require(persisted_m7 == 1, "m7_snapshot_not_uniquely_persisted")
        schedule_count = connection.execute("SELECT COUNT(*) FROM review_schedules").fetchone()[0]
        event_count = connection.execute("SELECT COUNT(*) FROM review_events").fetchone()[0]
        retained_count = connection.execute("SELECT COUNT(*) FROM retention_states WHERE retention_state='RETAINED'").fetchone()[0]
        _require(schedule_count == m8_counts["review_schedule_count"], "database_schedule_count_mismatch")
        _require(event_count == m8_counts["review_event_count"], "database_review_event_count_mismatch")
        _require(retained_count == m8_counts["retained_required_count"], "database_retained_count_mismatch")

    return {
        "resolved_diagnosis_count": m7_counts["resolved_diagnosis_count"],
        "completed_remediation_count": m7_counts["completed_remediation_count"],
        "completed_reassessment_count": m7_counts["completed_reassessment_count"],
        "review_event_count": m8_counts["review_event_count"],
        "retained_required_count": m8_counts["retained_required_count"],
    }


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    database: Path,
    graph_path: Path,
    consumer_path: Path,
    review_references_path: Path,
    m7_snapshot_path: Path,
    m8_snapshot_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    counts = {
        "resolved_diagnosis_count": 0,
        "completed_remediation_count": 0,
        "completed_reassessment_count": 0,
        "review_event_count": 0,
        "retained_required_count": 0,
    }
    try:
        _require(artifact.get("task_id") == builder.TASK_ID, "task_id_invalid")
        _require(artifact.get("program_id") == builder.PROGRAM_ID, "program_id_invalid")
        _require(artifact.get("schema_version") == builder.SCHEMA_VERSION, "schema_version_invalid")
        _require(artifact.get("validation_status") == builder.PASS_STATUS, "validation_status_invalid")
        _require(artifact.get("scope") == "A1_A1_PLUS_ONLY", "scope_invalid")
        _require(artifact.get("evidence_classification") == builder.EVIDENCE_CLASSIFICATION, "evidence_classification_invalid")
        _require(artifact.get("errors") == [], "artifact_errors_not_empty")
        _require(artifact.get("stop_reason") == "NONE", "stop_reason_invalid")
        _require(artifact.get("next_short_step") == builder.NEXT_SHORT_STEP, "next_short_step_invalid")
        _safe_walk(artifact)

        gate = artifact.get("closure_gate")
        _require(isinstance(gate, Mapping), "closure_gate_required")
        required_true = {
            "cp07d_projection_consumer_bound",
            "m6_resolved_attempt_evidence_consumed",
            "failure_diagnosis_resolved",
            "remediation_completed",
            "reassessment_completed",
            "three_stage_spaced_review_completed",
            "synthetic_retention_state_machine_completed",
            "real_learner_acceptance_required",
        }
        _require(all(gate.get(key) is True for key in required_true), "closure_gate_not_closed")
        _require(gate.get("decision") == "READY_FOR_CP07F_REAL_LEARNER_ACCEPTANCE", "closure_decision_invalid")

        boundaries = artifact.get("claim_boundaries")
        _require(isinstance(boundaries, Mapping), "claim_boundaries_required")
        _require(all(value is False for value in boundaries.values()), "claim_boundary_must_remain_false")

        counts = _validate_sources(
            artifact,
            database=database,
            graph_path=graph_path,
            consumer_path=consumer_path,
            review_references_path=review_references_path,
            m7_snapshot_path=m7_snapshot_path,
            m8_snapshot_path=m8_snapshot_path,
        )
    except (CP07EValidationError, builder.CP07EClosureError, OSError, sqlite3.Error, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))

    return {
        "task_id": builder.TASK_ID,
        "schema_version": "a1fs.v1.cp07e.diagnosis_remediation_retention_closure.validation.v1",
        "validation_status": builder.PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        **counts,
        "source_state_reconciled": not errors,
        "stateful_rebuild_performed": False,
        "synthetic_canary_only": True,
        "real_learner_attempt_claimed": False,
        "real_retention_claimed": False,
        "a2_a2plus_status": "LOCKED",
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--review-references", type=Path, required=True)
    parser.add_argument("--m7-snapshot", type=Path, required=True)
    parser.add_argument("--m8-snapshot", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    artifact = _read(args.artifact, "artifact")
    report = validate_artifact(
        artifact,
        database=args.database,
        graph_path=args.graph,
        consumer_path=args.consumer,
        review_references_path=args.review_references,
        m7_snapshot_path=args.m7_snapshot,
        m8_snapshot_path=args.m8_snapshot,
    )
    if args.report:
        builder._write_atomic(args.report, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
