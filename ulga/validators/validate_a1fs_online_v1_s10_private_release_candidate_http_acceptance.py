#!/usr/bin/env python3
"""Validate S10 private 24-unit HTTP release-candidate acceptance outputs."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s10_private_release_candidate_http_acceptance as s10  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates S10 loopback HTTP acceptance evidence, isolated-canary state, source S09 binding, "
    "production database immutability, and safe-report boundaries. It creates no learner content, "
    "answers, audio, mastery, public delivery, or parallel runtime."
)


def _read(path: Path, code: str, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{code}_unreadable:{exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{code}_not_object")
        return {}
    return value


def _inside(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def _canary_counts(database_path: Path, errors: list[str]) -> dict[str, int]:
    queries = {
        "profile_count": "SELECT COUNT(*) FROM learner_profiles WHERE learner_id=?",
        "session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=?",
        "completed_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='COMPLETED'",
        "abandoned_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='ABANDONED'",
        "active_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND session_state='ACTIVE'",
        "exposure_count": "SELECT COUNT(*) FROM state_events WHERE learner_id=? AND event_type='ASSET_EXPOSED'",
        "attempt_count": "SELECT COUNT(*) FROM response_attempts WHERE learner_id=?",
        "auto_pass_count": """SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id)
                              WHERE a.learner_id=? AND r.outcome='AUTO_PASS'""",
        "auto_fail_count": """SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id)
                              WHERE a.learner_id=? AND r.outcome='AUTO_FAIL'""",
        "speaking_attempt_count": """SELECT COUNT(*) FROM response_attempts a JOIN response_contracts c USING(asset_key)
                                     WHERE a.learner_id=? AND c.skill='SPEAKING'""",
        "listening_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND skill='LISTENING'",
        "checkpoint_count": "SELECT COUNT(*) FROM s05_progress_checkpoints WHERE learner_id=?",
    }
    if not Path(database_path).is_file():
        errors.append("canary_database_missing")
        return {}
    try:
        with sqlite3.connect(database_path) as connection:
            counts = {
                key: int(connection.execute(sql, (s10.CANARY_LEARNER_ID,)).fetchone()[0])
                for key, sql in queries.items()
            }
            counts["distinct_unit_count"] = len({
                str(row[0]).split(":", 2)[1]
                for row in connection.execute(
                    "SELECT lesson_id FROM learning_sessions WHERE learner_id=?",
                    (s10.CANARY_LEARNER_ID,),
                ).fetchall()
            })
            counts["distinct_skill_count"] = int(connection.execute(
                "SELECT COUNT(DISTINCT skill) FROM learning_sessions WHERE learner_id=?",
                (s10.CANARY_LEARNER_ID,),
            ).fetchone()[0])
            return counts
    except (sqlite3.Error, IndexError) as exc:
        errors.append(f"canary_database_invalid:{exc}")
        return {}


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s09_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    expected_identity = (
        s10.TASK_ID, s10.SCHEMA_VERSION, s10.PASS_STATUS, s10.PRODUCT_STATUS, "NONE"
    )
    actual_identity = (
        receipt.get("task_id"), receipt.get("schema_version"), receipt.get("validation_status"),
        receipt.get("product_status"), receipt.get("stop_reason"),
    )
    if actual_identity != expected_identity:
        errors.append("receipt_identity_or_status_invalid")
    receipt_core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s10.digest(receipt_core):
        errors.append("receipt_digest_invalid")

    safe_identity = (
        safe_report.get("task_id"), safe_report.get("schema_version"),
        safe_report.get("validation_status"), safe_report.get("product_status"),
        safe_report.get("stop_reason"),
    )
    if safe_identity != expected_identity:
        errors.append("safe_identity_or_status_invalid")
    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s10.digest(safe_core):
        errors.append("safe_digest_invalid")
    try:
        s10.safe_scan(safe_report)
    except s10.ReleaseCandidateError as exc:
        errors.append(str(exc))

    source_s09 = _read(Path(s09_path), "s09", errors)
    if source_s09:
        source_core = {key: value for key, value in source_s09.items() if key != "artifact_sha256"}
        if (
            source_s09.get("task_id") != s10.s09.TASK_ID
            or source_s09.get("validation_status") != s10.s09.PASS_STATUS
            or source_s09.get("product_status") != s10.s09.PRODUCT_STATUS
            or source_s09.get("stop_reason") != "NONE"
            or source_s09.get("artifact_sha256") != s10.digest(source_core)
        ):
            errors.append("source_s09_contract_invalid")
        if receipt.get("source_identity", {}).get("s09_sha256") != s10.digest(source_s09):
            errors.append("source_s09_binding_invalid")

    outputs = receipt.get("runtime_outputs", {})
    candidate_root = Path(str(outputs.get("root") or "")).resolve()
    canary_database = Path(str(outputs.get("canary_database_path") or "")).resolve()
    source_receipt = Path(str(outputs.get("source_s09_receipt_path") or "")).resolve()
    production_database = Path(str(outputs.get("source_database_path") or "")).resolve()
    source_bundle_index = Path(str(outputs.get("source_bundle_index_path") or "")).resolve()
    source_static_root = Path(str(outputs.get("source_static_root") or "")).resolve()
    if not _inside(candidate_root, output_root) or not _inside(canary_database, output_root):
        errors.append("s10_output_outside_authority_root")
    if source_receipt != Path(s09_path).resolve():
        errors.append("source_s09_path_mismatch")
    if not source_bundle_index.is_file() or not source_static_root.is_dir() or not production_database.is_file():
        errors.append("source_runtime_outputs_missing")

    counts = _canary_counts(canary_database, errors)
    expected_counts = {
        "profile_count": 1,
        "session_count": 3,
        "completed_session_count": 2,
        "abandoned_session_count": 1,
        "active_session_count": 0,
        "exposure_count": 3,
        "attempt_count": 2,
        "auto_pass_count": 1,
        "auto_fail_count": 1,
        "speaking_attempt_count": 0,
        "listening_session_count": 0,
        "checkpoint_count": 2,
        "distinct_unit_count": 2,
        "distinct_skill_count": 3,
    }
    for key, value in expected_counts.items():
        if counts.get(key) != value:
            errors.append(f"canary_count_invalid:{key}:{counts.get(key)}:{value}")

    acceptance = receipt.get("release_candidate_summary", {})
    expected_acceptance = {
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "session_count": 3,
        "completed_session_count": 2,
        "active_session_count": 0,
        "abandoned_session_count": 1,
        "exposure_count": 3,
        "attempt_count": 2,
        "auto_pass_count": 1,
        "auto_fail_count": 1,
        "pending_human_review_count": 0,
        "unit_count_with_sessions": 2,
        "skill_count_with_sessions": 3,
        "server_process_start_count": 2,
    }
    for key, value in expected_acceptance.items():
        if acceptance.get(key) != value:
            errors.append(f"acceptance_summary_invalid:{key}:{acceptance.get(key)}:{value}")
    required_true = (
        "health_endpoint_pass", "static_index_served", "static_application_served",
        "restart_resume_pass", "unit01_reading_auto_fail", "unit24_writing_auto_pass",
        "unit24_speaking_submission_blocked", "unit24_speaking_abandoned",
        "non_loopback_binding_blocked", "loopback_only",
    )
    for key in required_true:
        if acceptance.get(key) is not True:
            errors.append(f"acceptance_required_true_invalid:{key}")

    safety = receipt.get("production_safety", {})
    if (
        safety.get("production_database_unchanged") is not True
        or safety.get("http_acceptance_executed_on_isolated_clone") is not True
        or safety.get("real_learner_progress_mutated_by_canary") is not False
        or safety.get("database_sha256_before") != safety.get("database_sha256_after")
    ):
        errors.append("production_safety_invalid")
    if production_database.is_file() and safety.get("database_sha256_after") != s10.file_digest(production_database):
        errors.append("production_database_current_digest_invalid")

    entrypoint = receipt.get("release_candidate_entrypoint", {})
    if entrypoint != {
        "serve_command_available": True,
        "readback_command_available": True,
        "default_host": "127.0.0.1",
        "default_port": 8765,
        "public_network_binding_allowed": False,
    }:
        errors.append("release_candidate_entrypoint_invalid")

    capability = receipt.get("capability_contract", {})
    for key in (
        "s09_twentyfour_unit_runtime_reused", "s08_learner_journey_surface_reused",
        "m3_session_progress_authority_reused", "m5_renderer_authority_reused",
        "m6_response_scoring_authority_reused", "real_http_acceptance_executed",
        "restart_resume_proven_over_http",
    ):
        if capability.get(key) is not True:
            errors.append(f"capability_required_true_invalid:{key}")
    for key in (
        "parallel_curriculum_created", "parallel_state_engine_created",
        "parallel_scoring_engine_created", "public_network_binding_allowed",
        "speaking_capture_enabled", "listening_enabled", "audio_enabled",
        "mastery_write_enabled",
    ):
        if capability.get(key) is not False:
            errors.append(f"capability_required_false_invalid:{key}")

    expected_safe_sections = (
        "release_candidate_summary", "production_safety",
        "release_candidate_entrypoint", "capability_contract",
    )
    for section in expected_safe_sections:
        expected_section = receipt.get(section)
        if section == "production_safety":
            expected_section = {
                "production_database_unchanged": True,
                "http_acceptance_executed_on_isolated_clone": True,
                "real_learner_progress_mutated_by_canary": False,
            }
        if safe_report.get(section) != expected_section:
            errors.append(f"safe_projection_invalid:{section}")

    return {
        "task_id": s10.TASK_ID,
        "schema_version": s10.SCHEMA_VERSION,
        "validation_status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "validated_counts": {
            "unit_count": acceptance.get("unit_count"),
            "lesson_count": acceptance.get("lesson_count"),
            "asset_count": acceptance.get("asset_count"),
            "session_count": counts.get("session_count"),
            "attempt_count": counts.get("attempt_count"),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--safe-report", type=Path, required=True)
    parser.add_argument("--s09", type=Path, required=True)
    args = parser.parse_args(argv)
    errors: list[str] = []
    receipt = _read(args.receipt, "receipt", errors)
    safe = _read(args.safe_report, "safe", errors)
    if errors:
        result = {"validation_status": "FAIL", "error_count": len(errors), "errors": errors}
    else:
        result = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.receipt.parent,
            s09_path=args.s09,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
