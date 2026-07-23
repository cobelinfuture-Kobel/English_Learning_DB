#!/usr/bin/env python3
"""Run the CP07D -> M7 -> M8 diagnosis, recovery, and retention contract canary.

This orchestrator does not create a second mastery or retention engine.  It
verifies one CP07D private delivery consumer, delegates all state transitions
to the existing M7 and M8 engines, and emits a content-free safe readback.
The milestone is a deterministic contract canary only; real learner and real
longitudinal retention claims remain reserved for CP07F.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7
from ulga.builders import build_a1fs_v1_m8_review_scheduling_retention_spaced_practice as m8
from ulga.builders import build_a1fs_v1_cp07d_private_four_skill_delivery_consumer as cp07d

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Runtime-only delegation to existing M7 and M8 engines over already captured CP07D evidence; no candidate content, prompt, scoring contract, canonical Authority, learner response, media, mastery rule, retention rule, or A2 payload is created."

TASK_ID = "A1FS-V1-CP07E_DiagnosisRemediationReassessmentAndRetentionClosure"
PROGRAM_ID = "A1FS-V1 A1/A1+ Four-Skill Learning System"
SCHEMA_VERSION = "a1fs.v1.cp07e.diagnosis_remediation_retention_closure.safe.v1"
REVIEW_REFERENCE_SCHEMA_VERSION = "a1fs.v1.cp07e.review_evidence_references.private.v1"
PASS_STATUS = "PASS_CP07E_DIAGNOSIS_REMEDIATION_REASSESSMENT_RETENTION_CONTRACT_CLOSED"
NEXT_SHORT_STEP = "A1FS-V1-CP07F_RealLearnerEndToEndAcceptanceAndCoverageReadback"
EVIDENCE_CLASSIFICATION = "SYNTHETIC_CONTRACT_CANARY_ONLY"

DEFAULT_DATABASE = Path(".local/a1fs_v1/m3/learner_state.private.sqlite3")
DEFAULT_GRAPH = Path(".local/a1fs_v1/m1/a1a1plus_prerequisite_graph_and_coverage.private.json")
DEFAULT_CONSUMER = cp07d.DEFAULT_OUTPUT
DEFAULT_REVIEW_REFERENCES = Path(".local/a1fs_v1/cp07e/review_evidence_references.private.json")
DEFAULT_PRIVATE_OUTPUT_ROOT = Path(".local/a1fs_v1/cp07e/private")
DEFAULT_SAFE_OUTPUT = Path(".local/a1fs_v1/cp07e/diagnosis_remediation_retention_closure.safe.json")
DEFAULT_REPORT = Path(".local/a1fs_v1/cp07e/diagnosis_remediation_retention_closure.validation.json")

FORBIDDEN_SAFE_KEYS = {
    "learner_id",
    "attempt_id",
    "response",
    "response_json",
    "source_text",
    "source_content",
    "prompt",
    "scoring_contract",
    "correct_answer",
    "answer_key",
    "recording",
    "audio_bytes",
    "transcript_text",
    "reviewer_id",
    "notes",
}


class CP07EClosureError(ValueError):
    """Fail-closed CP07E orchestration or evidence error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _read(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CP07EClosureError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise CP07EClosureError(f"{code}_object_required")
    return value


def _write_atomic(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        if private:
            os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _assert_safe(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_SAFE_KEYS:
                raise CP07EClosureError(f"private_key_in_safe_readback:{path}.{key}")
            _assert_safe(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_safe(child, f"{path}[{index}]")


def _verify_consumer(consumer: Mapping[str, Any]) -> Mapping[str, Any]:
    if consumer.get("task_id") != m2.TASK_ID or consumer.get("schema_version") != m2.SCHEMA_VERSION:
        raise CP07EClosureError("cp07d_m2_contract_invalid")
    if consumer.get("validation_status") != m2.STATUS or consumer.get("errors") != []:
        raise CP07EClosureError("cp07d_m2_consumer_not_passed")
    if consumer.get("cp07d_task_id") != cp07d.TASK_ID or consumer.get("cp07d_schema_version") != cp07d.SCHEMA_VERSION:
        raise CP07EClosureError("cp07d_identity_invalid")
    if consumer.get("cp07d_validation_status") != cp07d.PASS_STATUS or consumer.get("cp07d_errors") != []:
        raise CP07EClosureError("cp07d_consumer_not_passed")
    if consumer.get("cp07d_stop_reason") != "NONE":
        raise CP07EClosureError("cp07d_stop_reason_invalid")
    contract = consumer.get("cp07d_delivery_contract")
    if not isinstance(contract, Mapping):
        raise CP07EClosureError("cp07d_delivery_contract_required")
    level = str(contract.get("selected_level") or "")
    if level not in {"A1", "A1+"}:
        raise CP07EClosureError("cp07d_selected_level_invalid")
    projected_keys = contract.get("projected_asset_keys")
    if not isinstance(projected_keys, list) or not projected_keys or len(projected_keys) != len(set(projected_keys)):
        raise CP07EClosureError("cp07d_projected_asset_keys_invalid")
    asset_index = {
        str(row.get("asset_key") or ""): row
        for row in consumer.get("asset_records", [])
        if isinstance(row, Mapping) and str(row.get("asset_key") or "")
    }
    if any(key not in asset_index for key in projected_keys):
        raise CP07EClosureError("cp07d_projected_asset_missing")
    if any(asset_index[key].get("level") != level for key in projected_keys):
        raise CP07EClosureError("cp07d_projected_asset_selected_lesson_level_drift")
    if contract.get("a2_payload_included") is not False:
        raise CP07EClosureError("cp07d_a2_payload_boundary_invalid")
    boundaries = consumer.get("cp07d_claim_boundaries")
    if not isinstance(boundaries, Mapping) or boundaries.get("a2_a2plus_in_scope") is not False:
        raise CP07EClosureError("cp07d_claim_boundary_invalid")
    return contract


def _verify_graph(graph: Mapping[str, Any]) -> None:
    if graph.get("task_id") != m1.TASK_ID or graph.get("schema_version") != m1.SCHEMA_VERSION:
        raise CP07EClosureError("m1_graph_identity_invalid")
    if graph.get("validation_status") != m1.STATUS or graph.get("errors") != []:
        raise CP07EClosureError("m1_graph_not_passed")
    lock = graph.get("a2_lock_contract")
    if not isinstance(lock, Mapping) or lock.get("state") != "LOCKED_BY_DESIGN":
        raise CP07EClosureError("m1_a2_lock_invalid")
    required = lock.get("required_mastery_node_ids")
    if not isinstance(required, list) or not required:
        raise CP07EClosureError("m1_required_mastery_nodes_missing")
    if len(required) != graph.get("counts", {}).get("required_mastery_node_count"):
        raise CP07EClosureError("m1_required_mastery_count_mismatch")


def _verify_database_binding(database: Path, consumer: Mapping[str, Any]) -> None:
    if not Path(database).is_file():
        raise CP07EClosureError("runtime_database_missing")
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        required_tables = {
            "metadata",
            "learner_profiles",
            "learning_sessions",
            "lesson_assets",
            "response_contracts",
            "response_attempts",
            "scoring_results",
            "human_review_queue",
        }
        if not required_tables.issubset(tables):
            raise CP07EClosureError("runtime_database_contract_incomplete")
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata.get("validation_status") != m3.STATUS:
            raise CP07EClosureError("m3_database_status_invalid")
        if metadata.get("m6_validation_status") != m6.STATUS:
            raise CP07EClosureError("m6_database_status_invalid")
        if metadata.get("consumer_sha256") != hashlib.sha256(
            json.dumps(consumer, ensure_ascii=False, indent=2).encode("utf-8")
        ).hexdigest():
            # M3 binds raw consumer bytes.  The caller-side exact check is done in
            # main from consumer_path; this fallback rejects only obvious drift.
            if not metadata.get("consumer_sha256"):
                raise CP07EClosureError("runtime_consumer_binding_missing")


def _review_references(value: Mapping[str, Any]) -> list[dict[str, str]]:
    if value.get("schema_version") != REVIEW_REFERENCE_SCHEMA_VERSION:
        raise CP07EClosureError("review_reference_schema_invalid")
    if value.get("evidence_classification") != EVIDENCE_CLASSIFICATION:
        raise CP07EClosureError("review_reference_evidence_classification_invalid")
    records = value.get("records")
    if not isinstance(records, list) or not records:
        raise CP07EClosureError("review_reference_records_required")
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in records:
        if not isinstance(row, Mapping):
            raise CP07EClosureError("review_reference_row_invalid")
        node_id = str(row.get("node_id") or "")
        attempt_id = str(row.get("attempt_id") or "")
        if not node_id or not attempt_id or (node_id, attempt_id) in seen:
            raise CP07EClosureError("review_reference_identity_missing_or_duplicate")
        seen.add((node_id, attempt_id))
        normalized.append({"node_id": node_id, "attempt_id": attempt_id})
    return normalized


def _closed_m7(snapshot: Mapping[str, Any]) -> dict[str, int]:
    diagnoses = snapshot.get("error_diagnoses")
    remediation = snapshot.get("remediation_assignments")
    reassessment = snapshot.get("reassessment_queue")
    if not isinstance(diagnoses, list) or not diagnoses:
        raise CP07EClosureError("m7_representative_failure_diagnosis_required")
    if not isinstance(remediation, list) or not remediation:
        raise CP07EClosureError("m7_remediation_assignment_required")
    if not isinstance(reassessment, list) or not reassessment:
        raise CP07EClosureError("m7_reassessment_queue_required")
    resolved = sum(row.get("diagnosis_state") == "RESOLVED_BY_REASSESSMENT" for row in diagnoses if isinstance(row, Mapping))
    completed_remediation = sum(row.get("assignment_state") == "COMPLETED" for row in remediation if isinstance(row, Mapping))
    completed_reassessment = sum(row.get("queue_state") == "COMPLETED" for row in reassessment if isinstance(row, Mapping))
    if resolved != len(diagnoses):
        raise CP07EClosureError("m7_diagnosis_not_fully_resolved")
    if completed_remediation != len(remediation):
        raise CP07EClosureError("m7_remediation_not_fully_completed")
    if completed_reassessment != len(reassessment):
        raise CP07EClosureError("m7_reassessment_not_fully_completed")
    if snapshot.get("mastered_required_count") != snapshot.get("required_mastery_node_count"):
        raise CP07EClosureError("m7_required_mastery_canary_not_closed")
    return {
        "diagnosis_count": len(diagnoses),
        "resolved_diagnosis_count": resolved,
        "remediation_assignment_count": len(remediation),
        "completed_remediation_count": completed_remediation,
        "reassessment_queue_count": len(reassessment),
        "completed_reassessment_count": completed_reassessment,
    }


def _closed_m8(snapshot: Mapping[str, Any]) -> dict[str, int]:
    schedules = snapshot.get("review_schedules")
    events = snapshot.get("review_events")
    states = snapshot.get("retention_states")
    if not isinstance(schedules, list) or not isinstance(events, list) or not isinstance(states, list):
        raise CP07EClosureError("m8_snapshot_lists_required")
    if snapshot.get("retention_confirmed") is not True:
        raise CP07EClosureError("m8_synthetic_retention_state_not_reached")
    required = int(snapshot.get("required_mastery_node_count") or 0)
    retained = int(snapshot.get("retained_required_count") or 0)
    if required <= 0 or retained != required:
        raise CP07EClosureError("m8_required_retention_partition_invalid")
    stages_by_node: dict[str, set[int]] = {}
    for row in schedules:
        if not isinstance(row, Mapping):
            raise CP07EClosureError("m8_schedule_row_invalid")
        stages_by_node.setdefault(str(row.get("node_id") or ""), set()).add(int(row.get("spacing_stage") or 0))
        if row.get("schedule_state") != "PASSED":
            raise CP07EClosureError("m8_schedule_not_passed")
    if len(stages_by_node) != required or any(stages != {1, 2, 3} for stages in stages_by_node.values()):
        raise CP07EClosureError("m8_three_stage_spacing_not_closed")
    if len(events) != required * 3:
        raise CP07EClosureError("m8_review_event_count_invalid")
    if any(row.get("retention_state") != "RETAINED" for row in states if isinstance(row, Mapping)):
        raise CP07EClosureError("m8_retention_state_not_closed")
    return {
        "review_schedule_count": len(schedules),
        "review_event_count": len(events),
        "retention_state_count": len(states),
        "retained_required_count": retained,
    }


def build_closure(
    *,
    database: Path,
    graph_path: Path,
    consumer_path: Path,
    learner_id: str,
    review_references_path: Path,
    private_output_root: Path,
    m7_created_at: str,
    schedule_as_of: str,
    export_as_of: str,
) -> tuple[dict[str, Any], Path, Path]:
    consumer = _read(consumer_path, "cp07d_consumer")
    graph = _read(graph_path, "m1_graph")
    review_reference_artifact = _read(review_references_path, "review_references")
    contract = _verify_consumer(consumer)
    _verify_graph(graph)
    _verify_database_binding(database, consumer)
    references = _review_references(review_reference_artifact)

    private_output_root = Path(private_output_root)
    m7_root = private_output_root / "m7"
    m8_root = private_output_root / "m8"
    m7_engine = m7.MasteryRemediationEngine(database_path=database, graph_path=graph_path)
    m7_engine.initialize()
    m7_result = m7_engine.build_snapshot(
        learner_id=learner_id,
        output_root=m7_root,
        created_at=m7_created_at,
    )
    m7_path = Path(m7_result["snapshot_path"])
    m7_snapshot = _read(m7_path, "m7_snapshot")
    m7_counts = _closed_m7(m7_snapshot)

    m8_engine = m8.ReviewRetentionEngine(
        database_path=database,
        graph_path=graph_path,
        m7_snapshot_path=m7_path,
    )
    m8_engine.initialize()
    m8_engine.build_schedule(learner_id=learner_id, as_of=schedule_as_of)
    review_results = [
        m8_engine.record_review(
            learner_id=learner_id,
            node_id=row["node_id"],
            attempt_id=row["attempt_id"],
        )
        for row in references
    ]
    if not review_results or any(row.get("validation_status") != m8.STATUS for row in review_results):
        raise CP07EClosureError("m8_review_recording_incomplete")
    m8_result = m8_engine.export_snapshot(
        learner_id=learner_id,
        output_root=m8_root,
        as_of=export_as_of,
    )
    m8_path = Path(m8_result["snapshot_path"])
    m8_snapshot = _read(m8_path, "m8_snapshot")
    m8_counts = _closed_m8(m8_snapshot)
    if len(references) != m8_counts["review_event_count"]:
        raise CP07EClosureError("review_reference_count_not_reconciled")

    artifact = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "scope": "A1_A1_PLUS_ONLY",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "source_identity": {
            "cp07d_consumer_sha256": _digest(consumer),
            "m1_graph_sha256": _digest(graph),
            "review_reference_set_sha256": _digest(review_reference_artifact),
            "m7_snapshot_sha256": _digest(m7_snapshot),
            "m8_snapshot_sha256": _digest(m8_snapshot),
            "runtime_database_sha256": hashlib.sha256(Path(database).read_bytes()).hexdigest(),
        },
        "runtime_selection": {
            "learner_ref_sha256": hashlib.sha256(learner_id.encode("utf-8")).hexdigest(),
            "selected_lesson_id": str(contract["selected_lesson_id"]),
            "selected_skill": str(contract["selected_skill"]),
            "selected_level": str(contract["selected_level"]),
            "projected_asset_count": len(contract["projected_asset_keys"]),
            "review_reference_count": len(references),
        },
        "m7_closure": {
            "required_mastery_node_count": int(m7_snapshot["required_mastery_node_count"]),
            "mastered_required_count": int(m7_snapshot["mastered_required_count"]),
            "a2_lock_state_in_canary": str(m7_snapshot["a2_lock_state"]),
            **m7_counts,
        },
        "m8_closure": {
            "scheduled_node_count": int(m8_snapshot["scheduled_node_count"]),
            "synthetic_retention_state_reached": bool(m8_snapshot["retention_confirmed"]),
            **m8_counts,
        },
        "closure_gate": {
            "cp07d_projection_consumer_bound": True,
            "m6_resolved_attempt_evidence_consumed": True,
            "failure_diagnosis_resolved": True,
            "remediation_completed": True,
            "reassessment_completed": True,
            "three_stage_spaced_review_completed": True,
            "synthetic_retention_state_machine_completed": True,
            "real_learner_acceptance_required": True,
            "decision": "READY_FOR_CP07F_REAL_LEARNER_ACCEPTANCE",
        },
        "claim_boundaries": {
            "private_content_included": False,
            "learner_identity_included": False,
            "learner_response_included": False,
            "attempt_identity_included": False,
            "real_learner_attempt_claimed": False,
            "real_retention_claimed": False,
            "public_delivery_claimed": False,
            "canonical_authority_changed": False,
            "mastery_policy_changed": False,
            "retention_policy_changed": False,
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
            "a2_a2plus_in_scope": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    _assert_safe(artifact)
    return artifact, m7_path, m8_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--consumer", type=Path, default=DEFAULT_CONSUMER)
    parser.add_argument("--learner-id", required=True)
    parser.add_argument("--review-references", type=Path, default=DEFAULT_REVIEW_REFERENCES)
    parser.add_argument("--private-output-root", type=Path, default=DEFAULT_PRIVATE_OUTPUT_ROOT)
    parser.add_argument("--safe-output", type=Path, default=DEFAULT_SAFE_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--m7-created-at", required=True)
    parser.add_argument("--schedule-as-of", required=True)
    parser.add_argument("--export-as-of", required=True)
    args = parser.parse_args(argv)
    try:
        artifact, m7_path, m8_path = build_closure(
            database=args.database,
            graph_path=args.graph,
            consumer_path=args.consumer,
            learner_id=args.learner_id,
            review_references_path=args.review_references,
            private_output_root=args.private_output_root,
            m7_created_at=args.m7_created_at,
            schedule_as_of=args.schedule_as_of,
            export_as_of=args.export_as_of,
        )
        from ulga.validators import validate_a1fs_v1_cp07e_diagnosis_remediation_reassessment_retention_closure as validator
        report = validator.validate_artifact(
            artifact,
            database=args.database,
            graph_path=args.graph,
            consumer_path=args.consumer,
            review_references_path=args.review_references,
            m7_snapshot_path=m7_path,
            m8_snapshot_path=m8_path,
        )
        _write_atomic(args.safe_output, artifact)
        _write_atomic(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (
        CP07EClosureError,
        m7.MasteryError,
        m8.ReviewRetentionError,
        OSError,
        sqlite3.Error,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
