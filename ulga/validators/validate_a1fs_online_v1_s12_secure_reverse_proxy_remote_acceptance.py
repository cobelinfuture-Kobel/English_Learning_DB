#!/usr/bin/env python3
"""Validate S12 reverse-proxy deployment and remote-shaped acceptance outputs."""
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

from ulga.builders import build_a1fs_online_v1_s12_secure_reverse_proxy_remote_acceptance as s12  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Validates the S12 deployment bundle, simulated external HTTPS edge acceptance, isolated canary database, source S11 binding, production digest preservation, rollback gates, and safe-report boundaries; it creates no curriculum, learner content, answers, secrets, audio, mastery, A2 unlock, live deployment, or public-release claim."


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
                key: int(connection.execute(sql, (s12.CANARY_LEARNER_ID,)).fetchone()[0])
                for key, sql in queries.items()
            }
            counts["distinct_unit_count"] = len({
                str(row[0]).split(":", 2)[1]
                for row in connection.execute(
                    "SELECT lesson_id FROM learning_sessions WHERE learner_id=?",
                    (s12.CANARY_LEARNER_ID,),
                ).fetchall()
            })
            counts["distinct_skill_count"] = int(connection.execute(
                "SELECT COUNT(DISTINCT skill) FROM learning_sessions WHERE learner_id=?",
                (s12.CANARY_LEARNER_ID,),
            ).fetchone()[0])
            return counts
    except (sqlite3.Error, IndexError) as exc:
        errors.append(f"canary_database_invalid:{exc}")
        return {}


def _validate_bundle(outputs: Mapping[str, Any], output_root: Path, errors: list[str]) -> None:
    bundle_root = Path(str(outputs.get("bundle_root") or "")).resolve()
    caddyfile = Path(str(outputs.get("caddyfile_path") or "")).resolve()
    deployment_path = Path(str(outputs.get("deployment_contract_path") or "")).resolve()
    rollback_path = Path(str(outputs.get("rollback_contract_path") or "")).resolve()
    for path in (bundle_root, caddyfile, deployment_path, rollback_path):
        if not _inside(path, output_root):
            errors.append(f"deployment_path_outside_authority_root:{path.name}")
    if not bundle_root.is_dir() or not caddyfile.is_file() or not deployment_path.is_file() or not rollback_path.is_file():
        errors.append("deployment_bundle_missing")
        return
    if outputs.get("bundle_sha256") != s12._tree_digest(bundle_root):
        errors.append("deployment_bundle_digest_invalid")

    caddy = caddyfile.read_text(encoding="utf-8")
    required_markers = (
        "{$A1FS_PUBLIC_HOST}",
        "reverse_proxy 127.0.0.1:8765",
        "header_up Host {$A1FS_PUBLIC_HOST}",
        "header_up X-Forwarded-Proto https",
        "header_up X-Forwarded-Host {$A1FS_PUBLIC_HOST}",
        "Strict-Transport-Security",
    )
    for marker in required_markers:
        if marker not in caddy:
            errors.append(f"caddyfile_marker_missing:{marker}")
    for forbidden in (s12.CANARY_PASSWORD, s12.CANARY_SESSION_SECRET):
        if forbidden in caddy:
            errors.append("secret_value_embedded_in_caddyfile")

    deployment = _read(deployment_path, "deployment_contract", errors)
    if deployment:
        expected_env = {
            "A1FS_PUBLIC_HOST",
            "A1FS_S11_MODE",
            "A1FS_S11_AUTH_USERNAME",
            "A1FS_S11_AUTH_PASSWORD",
            "A1FS_S11_SESSION_SECRET",
            "A1FS_S11_ALLOWED_ORIGIN",
            "A1FS_S11_ALLOWED_HOST",
        }
        if set(deployment.get("required_environment_variables", [])) != expected_env:
            errors.append("deployment_required_environment_invalid")
        if (
            deployment.get("application_upstream") != "127.0.0.1:8765"
            or deployment.get("reverse_proxy") != "CADDY"
            or deployment.get("tls_termination") != "AUTOMATIC_HTTPS_AT_EDGE"
            or deployment.get("origin_binding", {}).get("non_loopback_binding_allowed") is not False
            or deployment.get("forwarded_header_contract", {}).get("X-Forwarded-Proto") != "https"
            or deployment.get("secret_values_embedded") is not False
            or deployment.get("public_release_completed") is not False
        ):
            errors.append("deployment_contract_invalid")

    rollback = _read(rollback_path, "rollback_contract", errors)
    if rollback:
        required_actions = {
            "REMOVE_PUBLIC_PROXY_ROUTE",
            "KEEP_APPLICATION_BOUND_TO_127_0_0_1",
            "PRESERVE_PRODUCTION_DATABASE",
            "RESTORE_LAST_ACCEPTED_PROXY_CONFIGURATION",
        }
        if (
            set(rollback.get("actions", [])) != required_actions
            or rollback.get("database_rollback_required") is not False
            or rollback.get("automatic_public_reenable_allowed") is not False
        ):
            errors.append("rollback_contract_invalid")


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s11_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    expected_identity = (
        s12.TASK_ID, s12.SCHEMA_VERSION, s12.PASS_STATUS, s12.PRODUCT_STATUS, "NONE"
    )
    actual_identity = (
        receipt.get("task_id"), receipt.get("schema_version"), receipt.get("validation_status"),
        receipt.get("product_status"), receipt.get("stop_reason"),
    )
    if actual_identity != expected_identity:
        errors.append("receipt_identity_or_status_invalid")
    receipt_core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s12.digest(receipt_core):
        errors.append("receipt_digest_invalid")

    safe_identity = (
        safe_report.get("task_id"), safe_report.get("schema_version"),
        safe_report.get("validation_status"), safe_report.get("product_status"),
        safe_report.get("stop_reason"),
    )
    if safe_identity != expected_identity:
        errors.append("safe_identity_or_status_invalid")
    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s12.digest(safe_core):
        errors.append("safe_digest_invalid")
    try:
        s12.safe_scan(safe_report)
    except s12.ReverseProxyAcceptanceError as exc:
        errors.append(str(exc))

    source_s11 = _read(Path(s11_path), "s11", errors)
    if source_s11:
        source_core = {key: value for key, value in source_s11.items() if key != "artifact_sha256"}
        if (
            source_s11.get("task_id") != s12.s11.TASK_ID
            or source_s11.get("validation_status") != s12.s11.PASS_STATUS
            or source_s11.get("product_status") != s12.s11.PRODUCT_STATUS
            or source_s11.get("stop_reason") != "NONE"
            or source_s11.get("artifact_sha256") != s12.digest(source_core)
        ):
            errors.append("source_s11_contract_invalid")
        if receipt.get("source_identity", {}).get("s11_sha256") != s12.digest(source_s11):
            errors.append("source_s11_binding_invalid")

    outputs = receipt.get("runtime_outputs", {})
    candidate_root = Path(str(outputs.get("root") or "")).resolve()
    canary_database = Path(str(outputs.get("canary_database_path") or "")).resolve()
    source_receipt = Path(str(outputs.get("source_s11_receipt_path") or "")).resolve()
    production_database = Path(str(outputs.get("source_database_path") or "")).resolve()
    if not _inside(candidate_root, output_root) or not _inside(canary_database, output_root):
        errors.append("s12_output_outside_authority_root")
    if source_receipt != Path(s11_path).resolve():
        errors.append("source_s11_path_mismatch")
    if not production_database.is_file():
        errors.append("source_production_database_missing")
    _validate_bundle(outputs, output_root, errors)

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

    acceptance = receipt.get("remote_acceptance_summary", {})
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
        "origin_server_start_count": 2,
        "edge_proxy_start_count": 2,
        "acceptance_mode": "SIMULATED_EXTERNAL_HTTPS_EDGE",
    }
    for key, value in expected_acceptance.items():
        if acceptance.get(key) != value:
            errors.append(f"acceptance_summary_invalid:{key}:{acceptance.get(key)}:{value}")
    required_true = (
        "reverse_proxy_bundle_rendered", "remote_shaped_edge_acceptance",
        "direct_origin_bypass_blocked", "forwarded_https_enforced",
        "forwarded_host_enforced", "hsts_observed_at_edge",
        "secure_host_cookie_observed",
        "authenticated_session_survived_origin_and_edge_restart",
        "unit01_reading_auto_fail", "unit24_writing_auto_pass",
        "unit24_speaking_submission_blocked", "logout_revocation_observed",
    )
    for key in required_true:
        if acceptance.get(key) is not True:
            errors.append(f"acceptance_required_true_invalid:{key}")

    safety = receipt.get("production_safety", {})
    if (
        safety.get("production_database_unchanged") is not True
        or safety.get("remote_acceptance_executed_on_isolated_clone") is not True
        or safety.get("real_learner_progress_mutated_by_canary") is not False
        or safety.get("database_sha256_before") != safety.get("database_sha256_after")
    ):
        errors.append("production_safety_invalid")
    if production_database.is_file() and safety.get("database_sha256_after") != s12.file_digest(production_database):
        errors.append("production_database_current_digest_invalid")

    boundary = receipt.get("deployment_boundary", {})
    for key in (
        "application_origin_loopback_only", "reverse_proxy_tls_termination_required",
        "exact_public_host_required", "exact_https_origin_required",
        "forwarded_https_required", "forwarded_host_required", "secrets_environment_only",
    ):
        if boundary.get(key) is not True:
            errors.append(f"deployment_boundary_required_true_invalid:{key}")
    for key in (
        "secrets_serialized_to_artifact", "dns_configuration_completed",
        "certificate_issuance_completed", "live_remote_deployment_completed",
        "external_remote_acceptance_completed", "public_release_completed",
    ):
        if boundary.get(key) is not False:
            errors.append(f"deployment_boundary_required_false_invalid:{key}")

    rollback = receipt.get("rollback_boundary", {})
    if (
        rollback.get("proxy_route_removal_preserves_origin") is not True
        or rollback.get("database_rollback_required") is not False
        or rollback.get("automatic_public_reenable_allowed") is not False
    ):
        errors.append("rollback_boundary_invalid")

    capability = receipt.get("capability_contract", {})
    for key in (
        "s11_authenticated_boundary_reused", "s10_release_candidate_reused",
        "s09_twentyfour_unit_runtime_reused", "m3_session_progress_authority_reused",
        "m5_renderer_authority_reused", "m6_response_scoring_authority_reused",
        "reverse_proxy_deployment_bundle_materialized", "remote_shaped_https_acceptance_executed",
    ):
        if capability.get(key) is not True:
            errors.append(f"capability_required_true_invalid:{key}")
    for key in (
        "parallel_curriculum_created", "parallel_learner_state_engine_created",
        "parallel_scoring_engine_created", "direct_public_binding_allowed",
        "speaking_capture_enabled", "listening_enabled", "audio_enabled", "mastery_write_enabled",
    ):
        if capability.get(key) is not False:
            errors.append(f"capability_required_false_invalid:{key}")

    expected_safe_sections = (
        "remote_acceptance_summary", "production_safety", "deployment_boundary",
        "rollback_boundary", "entrypoint", "capability_contract",
    )
    for section in expected_safe_sections:
        expected_section = receipt.get(section)
        if section == "production_safety":
            expected_section = {
                "production_database_unchanged": True,
                "remote_acceptance_executed_on_isolated_clone": True,
                "real_learner_progress_mutated_by_canary": False,
            }
        if safe_report.get(section) != expected_section:
            errors.append(f"safe_projection_invalid:{section}")

    return {
        "task_id": s12.TASK_ID,
        "schema_version": s12.SCHEMA_VERSION,
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
    parser.add_argument("--s11", type=Path, required=True)
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
            s11_path=args.s11,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
