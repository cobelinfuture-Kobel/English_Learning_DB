#!/usr/bin/env python3
"""Prepare or validate CP07F real learner four-skill end-to-end evidence.

The runner never fabricates learner evidence.  PREPARE emits a private manifest
template and a safe readiness report.  VALIDATE consumes operator-supplied
private evidence paths for all four skills and checks the existing CP07D,
M6, M7, M8, and M10 state without modifying those stores.
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

from ulga.builders import build_a1fs_v1_cp07e_diagnosis_remediation_reassessment_retention_closure as cp07e
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7
from ulga.builders import build_a1fs_v1_m8_review_scheduling_retention_spaced_practice as m8
from ulga.builders import build_a1fs_v1_m10_listening_audio_speaking_recording_integration as m10

TASK_ID = "A1FS-V1-CP07F_RealLearnerEndToEndAcceptanceAndCoverageReadback"
PROGRAM_ID = "A1FS-V1 A1/A1+ Four-Skill Learning System"
MANIFEST_SCHEMA_VERSION = "a1fs.v1.cp07f.real_learner_acceptance_manifest.private.v1"
REPORT_SCHEMA_VERSION = "a1fs.v1.cp07f.real_learner_acceptance.safe_report.v1"
PREPARE_STATUS = "PASS_CP07F_REAL_LEARNER_ACCEPTANCE_PIPELINE_READY"
TEST_STATUS = "PASS_CP07F_TEST_FIXTURE_ACCEPTANCE_VALIDATED"
REAL_STATUS = "PASS_CP07F_REAL_LEARNER_END_TO_END_ACCEPTANCE"
NEXT_SHORT_STEP = "A1FS-V1-POST_CP07_ControlledRuntimeUsabilityAndRemainingProductGapRecheck"
EVIDENCE_ORIGINS = {"REAL_LEARNER", "TEST_FIXTURE"}
SKILLS = ("LISTENING", "SPEAKING", "READING", "WRITING")
RESOLVED_OUTCOMES = {"AUTO_PASS", "AUTO_FAIL", "HUMAN_APPROVE", "HUMAN_REJECT"}
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
DENOMINATOR_UNITS = 24

DEFAULT_OUTPUT_ROOT = Path(".local/a1fs_v1/cp07f")
DEFAULT_MANIFEST = DEFAULT_OUTPUT_ROOT / "real_learner_acceptance_manifest.private.json"
DEFAULT_SAFE_REPORT = DEFAULT_OUTPUT_ROOT / "real_learner_acceptance.safe.json"
DEFAULT_VALIDATION = DEFAULT_OUTPUT_ROOT / "real_learner_acceptance.validation.json"

FORBIDDEN_SAFE_KEYS = {
    "learner_id", "learner_ref", "attempt_id", "response", "response_json",
    "source_text", "source_content", "prompt", "scoring_contract", "answer",
    "answer_key", "recording", "audio_bytes", "stored_path", "database",
    "consumer", "graph", "m6_registry", "m7_snapshot", "m8_snapshot",
    "reviewer_id", "notes",
}


class CP07FAcceptanceError(ValueError):
    """Fail-closed CP07F evidence or acceptance error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _read(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CP07FAcceptanceError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise CP07FAcceptanceError(f"{code}_object_required")
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
        os.chmod(path, 0o600 if private else 0o644)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _safe_scan(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_SAFE_KEYS:
                raise CP07FAcceptanceError(f"private_key_in_safe_report:{path}.{key}")
            _safe_scan(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _safe_scan(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":\\", ":/"}):
            raise CP07FAcceptanceError(f"absolute_path_in_safe_report:{path}")


def _resolve(manifest_path: Path, value: Any, code: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise CP07FAcceptanceError(f"{code}_path_required")
    path = Path(value)
    if not path.is_absolute():
        path = manifest_path.parent / path
    path = path.resolve()
    if path.is_symlink() or not path.is_file():
        raise CP07FAcceptanceError(f"{code}_file_missing_or_symlink")
    return path


def _template() -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "private_local_only": True,
        "evidence_origin": "REAL_LEARNER",
        "learner_ref": "REPLACE_WITH_PRIVATE_LEARNER_ID",
        "skill_packages": [
            {
                "skill": skill,
                "database": f"{skill.lower()}/learner_state.private.sqlite3",
                "consumer": f"{skill.lower()}/cp07d_consumer.private.json",
                "graph": f"{skill.lower()}/m1_graph.private.json",
                "m6_registry": f"{skill.lower()}/m6_evidence_registry.private.json",
                "m7_snapshot": f"{skill.lower()}/m7_mastery_snapshot.private.json",
                "m8_snapshot": f"{skill.lower()}/m8_retention_snapshot.private.json",
            }
            for skill in SKILLS
        ],
        "operator_attestation": {
            "learner_or_guardian_consent_confirmed": False,
            "evidence_is_not_test_fixture": False,
            "private_storage_confirmed": False,
        },
    }


def prepare(output_root: Path) -> dict[str, Any]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    template = _template()
    report = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": "PREPARE",
        "evidence_origin": "NONE",
        "validation_status": PREPARE_STATUS,
        "required_skill_count": 4,
        "required_skills": list(SKILLS),
        "real_learner_acceptance_completed": False,
        "real_retention_claimed": False,
        "a2_a2plus_status": "LOCKED",
        "claim_boundaries": {
            "private_paths_included": False,
            "learner_identity_included": False,
            "learner_response_included": False,
            "test_fixture_counted_as_real": False,
            "canonical_authority_changed": False,
            "public_delivery_claimed": False,
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
        },
        "stop_reason": "REAL_LEARNER_FOUR_SKILL_EVIDENCE_REQUIRED",
        "next_short_step": TASK_ID,
        "errors": [],
    }
    _safe_scan(report)
    _write_atomic(root / "real_learner_acceptance_manifest.template.private.json", template, private=True)
    _write_atomic(root / "real_learner_acceptance_readiness.safe.json", report)
    return report


def _m6_entries(registry: Mapping[str, Any], *, learner_ref: str, skill: str, allowed_keys: set[str]) -> list[dict[str, Any]]:
    if registry.get("task_id") != m6.TASK_ID or registry.get("schema_version") != m6.REGISTRY_SCHEMA_VERSION:
        raise CP07FAcceptanceError(f"{skill}:m6_registry_identity_invalid")
    if registry.get("validation_status") != m6.STATUS or registry.get("private_local_only") is not True:
        raise CP07FAcceptanceError(f"{skill}:m6_registry_not_passed")
    session = registry.get("session")
    if not isinstance(session, Mapping) or session.get("learner_id") != learner_ref or session.get("skill") != skill:
        raise CP07FAcceptanceError(f"{skill}:m6_session_identity_invalid")
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CP07FAcceptanceError(f"{skill}:resolved_attempt_required")
    normalized: list[dict[str, Any]] = []
    for row in entries:
        if not isinstance(row, Mapping):
            raise CP07FAcceptanceError(f"{skill}:m6_entry_invalid")
        if row.get("learner_id") != learner_ref or row.get("skill") != skill:
            raise CP07FAcceptanceError(f"{skill}:m6_entry_identity_drift")
        if row.get("asset_key") not in allowed_keys:
            raise CP07FAcceptanceError(f"{skill}:m6_entry_not_cp07d_projected_asset")
        if row.get("outcome") not in RESOLVED_OUTCOMES:
            raise CP07FAcceptanceError(f"{skill}:m6_unresolved_attempt_forbidden")
        normalized.append(dict(row))
    if not any(row["outcome"] in PASS_OUTCOMES for row in normalized):
        raise CP07FAcceptanceError(f"{skill}:at_least_one_pass_required")
    return normalized


def _database_checks(
    *,
    database: Path,
    consumer_path: Path,
    learner_ref: str,
    skill: str,
    m6_entries: list[Mapping[str, Any]],
    consumer_contract: Mapping[str, Any],
) -> dict[str, int | bool]:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata.get("validation_status") != m3.STATUS or metadata.get("m6_validation_status") != m6.STATUS:
            raise CP07FAcceptanceError(f"{skill}:runtime_database_status_invalid")
        if metadata.get("consumer_sha256") != hashlib.sha256(consumer_path.read_bytes()).hexdigest():
            raise CP07FAcceptanceError(f"{skill}:runtime_consumer_binding_mismatch")
        profile = connection.execute(
            "SELECT profile_state FROM learner_profiles WHERE learner_id=?",
            (learner_ref,),
        ).fetchone()
        if not profile or profile[0] != "ACTIVE":
            raise CP07FAcceptanceError(f"{skill}:learner_profile_not_active")
        for entry in m6_entries:
            row = connection.execute(
                "SELECT a.learner_id,a.asset_key,s.outcome FROM response_attempts a JOIN scoring_results s USING(attempt_id) WHERE a.attempt_id=?",
                (entry["attempt_id"],),
            ).fetchone()
            if not row or row["learner_id"] != learner_ref or row["asset_key"] != entry["asset_key"] or row["outcome"] != entry["outcome"]:
                raise CP07FAcceptanceError(f"{skill}:m6_registry_database_attempt_mismatch")

        listening_audio_registered = False
        speaking_recording_registered = False
        if skill in {"LISTENING", "SPEAKING"}:
            if "m10_metadata" not in tables or "private_media_assets" not in tables:
                raise CP07FAcceptanceError(f"{skill}:m10_media_tables_missing")
            m10_metadata = dict(connection.execute("SELECT key,value FROM m10_metadata"))
            if m10_metadata.get("validation_status") != m10.STATUS:
                raise CP07FAcceptanceError(f"{skill}:m10_status_invalid")
        if skill == "LISTENING":
            allowed_audio = set(consumer_contract.get("listening_audio_asset_keys", []))
            rows = connection.execute(
                "SELECT asset_key FROM private_media_assets WHERE media_kind='LISTENING_AUDIO'"
            ).fetchall()
            listening_audio_registered = any(row[0] in allowed_audio for row in rows)
            if not listening_audio_registered:
                raise CP07FAcceptanceError("LISTENING:registered_audio_required")
        elif skill == "SPEAKING":
            attempt_ids = {str(row["attempt_id"]) for row in m6_entries}
            rows = connection.execute(
                "SELECT attempt_id,consent_required,consent_granted FROM private_media_assets WHERE media_kind='SPEAKING_RECORDING' AND learner_id=?",
                (learner_ref,),
            ).fetchall()
            speaking_recording_registered = any(
                row[0] in attempt_ids and row[1] == 1 and row[2] == 1 for row in rows
            )
            if not speaking_recording_registered:
                raise CP07FAcceptanceError("SPEAKING:consented_recording_required")
        return {
            "listening_audio_registered": listening_audio_registered,
            "speaking_recording_registered": speaking_recording_registered,
        }


def _package(
    *,
    manifest_path: Path,
    manifest_row: Mapping[str, Any],
    learner_ref: str,
) -> dict[str, Any]:
    skill = str(manifest_row.get("skill") or "")
    if skill not in SKILLS:
        raise CP07FAcceptanceError("skill_package_skill_invalid")
    paths = {
        key: _resolve(manifest_path, manifest_row.get(key), f"{skill}:{key}")
        for key in ("database", "consumer", "graph", "m6_registry", "m7_snapshot", "m8_snapshot")
    }
    consumer = _read(paths["consumer"], f"{skill}:consumer")
    graph = _read(paths["graph"], f"{skill}:graph")
    registry = _read(paths["m6_registry"], f"{skill}:m6_registry")
    m7_snapshot = _read(paths["m7_snapshot"], f"{skill}:m7_snapshot")
    m8_snapshot = _read(paths["m8_snapshot"], f"{skill}:m8_snapshot")

    contract = cp07e._verify_consumer(consumer)
    cp07e._verify_graph(graph)
    if contract.get("selected_skill") != skill:
        raise CP07FAcceptanceError(f"{skill}:cp07d_selected_skill_mismatch")
    allowed_keys = set(contract.get("response_capture_asset_keys", []))
    if not allowed_keys:
        raise CP07FAcceptanceError(f"{skill}:cp07d_response_capture_asset_required")
    entries = _m6_entries(registry, learner_ref=learner_ref, skill=skill, allowed_keys=allowed_keys)

    if m7_snapshot.get("task_id") != m7.TASK_ID or m7_snapshot.get("validation_status") != m7.STATUS:
        raise CP07FAcceptanceError(f"{skill}:m7_snapshot_invalid")
    if m7_snapshot.get("learner_id") != learner_ref:
        raise CP07FAcceptanceError(f"{skill}:m7_learner_mismatch")
    graph_raw_sha = hashlib.sha256(paths["graph"].read_bytes()).hexdigest()
    if m7_snapshot.get("source_graph_sha256") != graph_raw_sha:
        raise CP07FAcceptanceError(f"{skill}:m7_graph_binding_mismatch")

    if m8_snapshot.get("task_id") != m8.TASK_ID or m8_snapshot.get("validation_status") != m8.STATUS:
        raise CP07FAcceptanceError(f"{skill}:m8_snapshot_invalid")
    if m8_snapshot.get("learner_id") != learner_ref:
        raise CP07FAcceptanceError(f"{skill}:m8_learner_mismatch")
    if m8_snapshot.get("source_graph_sha256") != graph_raw_sha:
        raise CP07FAcceptanceError(f"{skill}:m8_graph_binding_mismatch")
    if m8_snapshot.get("source_m7_snapshot_digest") != _digest(m7_snapshot):
        raise CP07FAcceptanceError(f"{skill}:m8_m7_binding_mismatch")
    if int(m8_snapshot.get("scheduled_node_count") or 0) < 1:
        raise CP07FAcceptanceError(f"{skill}:m8_review_schedule_required")

    database_counts = _database_checks(
        database=paths["database"],
        consumer_path=paths["consumer"],
        learner_ref=learner_ref,
        skill=skill,
        m6_entries=entries,
        consumer_contract=contract,
    )
    assets = {
        str(row.get("asset_key") or ""): row
        for row in consumer.get("asset_records", [])
        if isinstance(row, Mapping)
    }
    grammar_units = sorted({
        str(assets[row["asset_key"]].get("payload", {}).get("grammar_unit_id") or "")
        for row in entries
        if row["asset_key"] in assets
        and isinstance(assets[row["asset_key"]].get("payload"), Mapping)
        and assets[row["asset_key"]]["payload"].get("grammar_unit_id")
    })
    diagnoses = [row for row in m7_snapshot.get("error_diagnoses", []) if isinstance(row, Mapping)]
    remediation = [row for row in m7_snapshot.get("remediation_assignments", []) if isinstance(row, Mapping)]
    reassessment = [row for row in m7_snapshot.get("reassessment_queue", []) if isinstance(row, Mapping)]
    review_events = [row for row in m8_snapshot.get("review_events", []) if isinstance(row, Mapping)]
    return {
        "skill": skill,
        "selected_level": str(contract["selected_level"]),
        "selected_lesson_count": 1,
        "resolved_attempt_count": len(entries),
        "pass_attempt_count": sum(row["outcome"] in PASS_OUTCOMES for row in entries),
        "fail_attempt_count": sum(row["outcome"] not in PASS_OUTCOMES for row in entries),
        "attempted_grammar_unit_ids": grammar_units,
        "m7_diagnosis_count": len(diagnoses),
        "m7_completed_remediation_count": sum(row.get("assignment_state") == "COMPLETED" for row in remediation),
        "m7_completed_reassessment_count": sum(row.get("queue_state") == "COMPLETED" for row in reassessment),
        "m8_scheduled_node_count": int(m8_snapshot["scheduled_node_count"]),
        "m8_review_event_count": len(review_events),
        "m8_retention_confirmed": bool(m8_snapshot.get("retention_confirmed")),
        **database_counts,
        "source_package_sha256": _digest({
            "consumer": _digest(consumer),
            "graph": _digest(graph),
            "m6_registry": _digest(registry),
            "m7_snapshot": _digest(m7_snapshot),
            "m8_snapshot": _digest(m8_snapshot),
            "database": hashlib.sha256(paths["database"].read_bytes()).hexdigest(),
        }),
    }


def evaluate_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    manifest = _read(manifest_path, "acceptance_manifest")
    if manifest.get("task_id") != TASK_ID or manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise CP07FAcceptanceError("acceptance_manifest_identity_invalid")
    if manifest.get("private_local_only") is not True:
        raise CP07FAcceptanceError("acceptance_manifest_private_boundary_invalid")
    origin = str(manifest.get("evidence_origin") or "")
    if origin not in EVIDENCE_ORIGINS:
        raise CP07FAcceptanceError("evidence_origin_invalid")
    learner_ref = str(manifest.get("learner_ref") or "")
    if not learner_ref:
        raise CP07FAcceptanceError("learner_ref_required")
    packages = manifest.get("skill_packages")
    if not isinstance(packages, list) or len(packages) != 4:
        raise CP07FAcceptanceError("exact_four_skill_packages_required")
    skills = [str(row.get("skill") or "") for row in packages if isinstance(row, Mapping)]
    if sorted(skills) != sorted(SKILLS):
        raise CP07FAcceptanceError("four_skill_package_partition_invalid")
    attestation = manifest.get("operator_attestation")
    if not isinstance(attestation, Mapping):
        raise CP07FAcceptanceError("operator_attestation_required")
    if origin == "REAL_LEARNER":
        if attestation.get("learner_or_guardian_consent_confirmed") is not True:
            raise CP07FAcceptanceError("real_learner_consent_attestation_required")
        if attestation.get("evidence_is_not_test_fixture") is not True:
            raise CP07FAcceptanceError("real_evidence_attestation_required")
        if attestation.get("private_storage_confirmed") is not True:
            raise CP07FAcceptanceError("private_storage_attestation_required")

    summaries = [
        _package(manifest_path=manifest_path, manifest_row=row, learner_ref=learner_ref)
        for row in sorted(packages, key=lambda row: SKILLS.index(str(row["skill"])))
    ]
    total_attempts = sum(int(row["resolved_attempt_count"]) for row in summaries)
    total_diagnoses = sum(int(row["m7_diagnosis_count"]) for row in summaries)
    completed_remediation = sum(int(row["m7_completed_remediation_count"]) for row in summaries)
    completed_reassessment = sum(int(row["m7_completed_reassessment_count"]) for row in summaries)
    review_events = sum(int(row["m8_review_event_count"]) for row in summaries)
    grammar_units = sorted({unit for row in summaries for unit in row["attempted_grammar_unit_ids"]})
    listening_audio = next(row for row in summaries if row["skill"] == "LISTENING")["listening_audio_registered"]
    speaking_recording = next(row for row in summaries if row["skill"] == "SPEAKING")["speaking_recording_registered"]
    gates = {
        "same_private_learner_across_four_skills": True,
        "four_skill_resolved_attempts_present": all(row["resolved_attempt_count"] >= 1 for row in summaries),
        "four_skill_pass_evidence_present": all(row["pass_attempt_count"] >= 1 for row in summaries),
        "four_skill_m8_schedule_present": all(row["m8_scheduled_node_count"] >= 1 for row in summaries),
        "representative_completed_remediation_path_present": total_diagnoses >= 1 and completed_remediation >= 1 and completed_reassessment >= 1,
        "delayed_review_event_present": review_events >= 1,
        "listening_audio_registered": listening_audio is True,
        "speaking_consented_recording_registered": speaking_recording is True,
        "a2_a2plus_locked": True,
    }
    if not all(gates.values()):
        failed = sorted(key for key, value in gates.items() if value is not True)
        raise CP07FAcceptanceError(f"acceptance_gate_failed:{failed}")
    is_real = origin == "REAL_LEARNER"
    report = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": "VALIDATE",
        "evidence_origin": origin,
        "validation_status": REAL_STATUS if is_real else TEST_STATUS,
        "learner_ref_sha256": hashlib.sha256(learner_ref.encode("utf-8")).hexdigest(),
        "skill_readback": [
            {
                "skill": row["skill"],
                "selected_level": row["selected_level"],
                "resolved_attempt_count": row["resolved_attempt_count"],
                "pass_attempt_count": row["pass_attempt_count"],
                "fail_attempt_count": row["fail_attempt_count"],
                "attempted_grammar_unit_count": len(row["attempted_grammar_unit_ids"]),
                "m7_diagnosis_count": row["m7_diagnosis_count"],
                "m7_completed_remediation_count": row["m7_completed_remediation_count"],
                "m7_completed_reassessment_count": row["m7_completed_reassessment_count"],
                "m8_scheduled_node_count": row["m8_scheduled_node_count"],
                "m8_review_event_count": row["m8_review_event_count"],
                "m8_retention_confirmed": row["m8_retention_confirmed"],
                "source_package_sha256": row["source_package_sha256"],
            }
            for row in summaries
        ],
        "aggregate_readback": {
            "required_skill_count": 4,
            "attempted_skill_count": 4,
            "resolved_attempt_count": total_attempts,
            "m7_diagnosis_count": total_diagnoses,
            "completed_remediation_count": completed_remediation,
            "completed_reassessment_count": completed_reassessment,
            "m8_review_event_count": review_events,
            "attempted_grammar_unit_count": len(grammar_units),
            "existing_learning_unit_denominator": DENOMINATOR_UNITS,
            "remaining_unattempted_unit_count": DENOMINATOR_UNITS - len(grammar_units),
            "all_four_skills_retention_confirmed": all(row["m8_retention_confirmed"] for row in summaries),
        },
        "acceptance_gate": {
            **gates,
            "decision": "CONTROLLED_LEARNER_RUNTIME_USABLE" if is_real else "TEST_FIXTURE_CONTRACT_ONLY",
        },
        "real_learner_evidence_captured": is_real,
        "real_learner_acceptance_completed": is_real,
        "real_retention_claimed": False,
        "claim_boundaries": {
            "private_paths_included": False,
            "learner_identity_included": False,
            "learner_response_included": False,
            "attempt_identity_included": False,
            "test_fixture_counted_as_real": False,
            "canonical_authority_changed": False,
            "public_delivery_claimed": False,
            "full_24_unit_real_coverage_claimed": False,
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
        },
        "stop_reason": "NONE" if is_real else "REAL_LEARNER_FOUR_SKILL_EVIDENCE_REQUIRED",
        "next_short_step": NEXT_SHORT_STEP if is_real else TASK_ID,
        "errors": [],
    }
    _safe_scan(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_cmd = commands.add_parser("prepare")
    prepare_cmd.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    validate_cmd = commands.add_parser("validate")
    validate_cmd.add_argument("--manifest", type=Path, required=True)
    validate_cmd.add_argument("--safe-output", type=Path, default=DEFAULT_SAFE_REPORT)
    validate_cmd.add_argument("--validation-report", type=Path, default=DEFAULT_VALIDATION)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            report = prepare(args.output_root)
            validation = {
                "validation_status": PREPARE_STATUS,
                "error_count": 0,
                "errors": [],
                "real_learner_acceptance_completed": False,
                "stop_reason": report["stop_reason"],
            }
        else:
            report = evaluate_manifest(args.manifest)
            from ulga.validators import validate_a1fs_v1_cp07f_real_learner_end_to_end_acceptance as validator
            validation = validator.validate_report(report, manifest_path=args.manifest)
            _write_atomic(args.safe_output, report)
            _write_atomic(args.validation_report, validation)
        print(json.dumps({
            "validation_status": report["validation_status"],
            "evidence_origin": report["evidence_origin"],
            "real_learner_acceptance_completed": report["real_learner_acceptance_completed"],
            "stop_reason": report["stop_reason"],
            "next_short_step": report["next_short_step"],
        }, ensure_ascii=False, sort_keys=True))
        return 0 if validation.get("error_count") == 0 else 1
    except (CP07FAcceptanceError, OSError, sqlite3.Error, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
