#!/usr/bin/env python3
"""Validate S11 secure authenticated boundary outputs."""
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

from ulga.builders import build_a1fs_online_v1_s11_secure_authenticated_boundary as s11  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Validates S11 authentication, signed-session, CSRF, Origin/Host, secure-cookie, TLS prerequisite, isolated-canary, source S10 binding, and production immutability evidence; it authors no curriculum, learner content, answers, audio, mastery, A2 unlock, or public deployment."


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
    if not database_path.is_file():
        errors.append("canary_database_missing")
        return {}
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
    try:
        with sqlite3.connect(database_path) as connection:
            counts = {
                key: int(connection.execute(sql, (s11.CANARY_LEARNER_ID,)).fetchone()[0])
                for key, sql in queries.items()
            }
            counts["distinct_unit_count"] = len({
                str(row[0]).split(":", 2)[1]
                for row in connection.execute(
                    "SELECT lesson_id FROM learning_sessions WHERE learner_id=?",
                    (s11.CANARY_LEARNER_ID,),
                ).fetchall()
            })
            counts["distinct_skill_count"] = int(connection.execute(
                "SELECT COUNT(DISTINCT skill) FROM learning_sessions WHERE learner_id=?",
                (s11.CANARY_LEARNER_ID,),
            ).fetchone()[0])
            return counts
    except (sqlite3.Error, IndexError) as exc:
        errors.append(f"canary_database_invalid:{exc}")
        return {}


def validate_outputs(*, receipt: Mapping[str, Any], safe_report: Mapping[str, Any], output_root: Path, s10_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    expected_identity = (s11.TASK_ID, s11.SCHEMA_VERSION, s11.PASS_STATUS, s11.PRODUCT_STATUS, "NONE")
    actual_identity = (receipt.get("task_id"), receipt.get("schema_version"), receipt.get("validation_status"), receipt.get("product_status"), receipt.get("stop_reason"))
    if actual_identity != expected_identity:
        errors.append("receipt_identity_or_status_invalid")
    receipt_core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s11.digest(receipt_core):
        errors.append("receipt_digest_invalid")

    safe_identity = (safe_report.get("task_id"), safe_report.get("schema_version"), safe_report.get("validation_status"), safe_report.get("product_status"), safe_report.get("stop_reason"))
    if safe_identity != expected_identity:
        errors.append("safe_identity_or_status_invalid")
    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s11.digest(safe_core):
        errors.append("safe_digest_invalid")
    try:
        s11.safe_scan(safe_report)
    except s11.SecureBoundaryError as exc:
        errors.append(str(exc))

    source_s10 = _read(Path(s10_path), "s10", errors)
    if source_s10:
        source_core = {key: value for key, value in source_s10.items() if key != "artifact_sha256"}
        if (
            source_s10.get("task_id") != s11.s10.TASK_ID
            or source_s10.get("schema_version") != s11.s10.SCHEMA_VERSION
            or source_s10.get("validation_status") != s11.s10.PASS_STATUS
            or source_s10.get("product_status") != s11.s10.PRODUCT_STATUS
            or source_s10.get("stop_reason") != "NONE"
            or source_s10.get("artifact_sha256") != s11.digest(source_core)
        ):
            errors.append("source_s10_contract_invalid")
        if receipt.get("source_identity", {}).get("s10_sha256") != s11.digest(source_s10):
            errors.append("source_s10_binding_invalid")

    outputs = receipt.get("runtime_outputs", {})
    candidate_root = Path(str(outputs.get("root") or "")).resolve()
    canary_database = Path(str(outputs.get("canary_database_path") or "")).resolve()
    source_receipt = Path(str(outputs.get("source_s10_receipt_path") or "")).resolve()
    production_database = Path(str(outputs.get("source_database_path") or "")).resolve()
    bundle_index = Path(str(outputs.get("source_bundle_index_path") or "")).resolve()
    secure_static = Path(str(outputs.get("secure_static_root") or "")).resolve()
    if not _inside(candidate_root, output_root) or not _inside(canary_database, output_root) or not _inside(secure_static, output_root):
        errors.append("s11_output_outside_authority_root")
    if source_receipt != Path(s10_path).resolve():
        errors.append("source_s10_path_mismatch")
    if not production_database.is_file() or not bundle_index.is_file() or not secure_static.is_dir():
        errors.append("source_or_secure_runtime_missing")

    static_requirements = {
        "index.html": ("/auth.js", "id=\"logout\""),
        "auth.js": ("X-CSRF-Token", "/auth/logout", "/auth/session"),
        "login.html": ("A1FS 安全登入", "autocomplete=\"current-password\""),
        "login.js": ("/auth/login",),
        "login.css": ("#message",),
    }
    for filename, markers in static_requirements.items():
        path = secure_static / filename
        if not path.is_file():
            errors.append(f"secure_static_missing:{filename}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"secure_static_marker_missing:{filename}:{marker}")
        if s11.CANARY_PASSWORD in text or s11.CANARY_SESSION_SECRET in text:
            errors.append(f"secure_static_secret_leak:{filename}")

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
    for key, expected in expected_counts.items():
        if counts.get(key) != expected:
            errors.append(f"canary_count_invalid:{key}:{counts.get(key)}:{expected}")

    acceptance = receipt.get("security_acceptance_summary", {})
    expected_acceptance = {
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "session_count": 3,
        "completed_session_count": 2,
        "abandoned_session_count": 1,
        "active_session_count": 0,
        "exposure_count": 3,
        "attempt_count": 2,
        "auto_pass_count": 1,
        "auto_fail_count": 1,
        "unit_count_with_sessions": 2,
        "skill_count_with_sessions": 3,
        "server_process_start_count": 2,
    }
    for key, expected in expected_acceptance.items():
        if acceptance.get(key) != expected:
            errors.append(f"acceptance_count_invalid:{key}:{acceptance.get(key)}:{expected}")
    required_true = (
        "authentication_required", "unauthenticated_root_redirected", "unauthenticated_api_blocked",
        "invalid_credentials_blocked", "login_rate_limit_enabled", "signed_session_cookie",
        "session_cookie_http_only", "session_cookie_same_site_strict",
        "secure_cookie_required_in_reverse_proxy_mode", "csrf_required_for_state_change",
        "invalid_origin_blocked", "host_allowlist_enforced", "security_headers_enabled",
        "restart_authenticated_session_valid", "logout_revokes_session",
        "unit01_reading_auto_fail", "unit24_writing_auto_pass",
        "unit24_speaking_submission_blocked", "reverse_proxy_https_prerequisites_fail_closed",
        "loopback_application_server_only",
    )
    for key in required_true:
        if acceptance.get(key) is not True:
            errors.append(f"acceptance_required_true_invalid:{key}")

    safety = receipt.get("production_safety", {})
    if (
        safety.get("production_database_unchanged") is not True
        or safety.get("authenticated_acceptance_executed_on_isolated_clone") is not True
        or safety.get("real_learner_progress_mutated_by_canary") is not False
        or safety.get("database_sha256_before") != safety.get("database_sha256_after")
    ):
        errors.append("production_safety_invalid")
    if production_database.is_file() and safety.get("database_sha256_after") != s11.file_digest(production_database):
        errors.append("production_database_current_digest_invalid")

    boundary = receipt.get("deployment_boundary", {})
    expected_boundary = {
        "application_server_loopback_only": True,
        "reverse_proxy_required_for_online_delivery": True,
        "https_origin_required": True,
        "explicit_host_allowlist_required": True,
        "auth_secret_environment_required": True,
        "session_signing_secret_environment_required": True,
        "secrets_serialized_to_artifact": False,
        "public_release_completed": False,
    }
    if boundary != expected_boundary:
        errors.append("deployment_boundary_invalid")
    if receipt.get("entrypoint") != {"serve_command_available": True, "readback_command_available": True, "default_host": "127.0.0.1", "default_port": 8765}:
        errors.append("entrypoint_invalid")

    capability = receipt.get("capability_contract", {})
    for key in (
        "s10_release_candidate_reused", "s09_twentyfour_unit_runtime_reused",
        "m3_session_progress_authority_reused", "m5_renderer_authority_reused",
        "m6_response_scoring_authority_reused", "authenticated_boundary_connected",
        "signed_session_and_csrf_connected",
    ):
        if capability.get(key) is not True:
            errors.append(f"capability_required_true_invalid:{key}")
    for key in (
        "parallel_curriculum_created", "parallel_learner_state_engine_created",
        "parallel_scoring_engine_created", "direct_public_binding_allowed",
        "speaking_capture_enabled", "listening_enabled", "audio_enabled",
        "mastery_write_enabled",
    ):
        if capability.get(key) is not False:
            errors.append(f"capability_required_false_invalid:{key}")

    for section in ("security_acceptance_summary", "deployment_boundary", "entrypoint", "capability_contract"):
        if safe_report.get(section) != receipt.get(section):
            errors.append(f"safe_projection_invalid:{section}")
    if safe_report.get("production_safety") != {
        "production_database_unchanged": True,
        "authenticated_acceptance_executed_on_isolated_clone": True,
        "real_learner_progress_mutated_by_canary": False,
    }:
        errors.append("safe_projection_invalid:production_safety")

    return {
        "task_id": s11.TASK_ID,
        "schema_version": s11.SCHEMA_VERSION,
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
    parser.add_argument("--s10", type=Path, required=True)
    args = parser.parse_args(argv)
    errors: list[str] = []
    receipt = _read(args.receipt, "receipt", errors)
    safe = _read(args.safe_report, "safe", errors)
    if errors:
        result = {"validation_status": "FAIL", "error_count": len(errors), "errors": errors}
    else:
        result = validate_outputs(receipt=receipt, safe_report=safe, output_root=args.receipt.parent, s10_path=args.s10)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
