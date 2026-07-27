#!/usr/bin/env python3
"""Validate S13 localhost production deployment outputs."""
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

from ulga.builders import build_a1fs_online_v1_s13_localhost_production_deployment as s13  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Validates the S13 localhost process-lifecycle bundle, persistent auth revocation store, source S12 binding, production database immutability, and no-external/no-audio boundaries; it authors no curriculum, learner content, answers, audio, mastery, A2 unlock, Cloudflare route, or public release."


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


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s12_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    expected_identity = (
        s13.TASK_ID,
        s13.SCHEMA_VERSION,
        s13.PASS_STATUS,
        s13.PRODUCT_STATUS,
        "NONE",
    )
    if (
        receipt.get("task_id"),
        receipt.get("schema_version"),
        receipt.get("validation_status"),
        receipt.get("product_status"),
        receipt.get("stop_reason"),
    ) != expected_identity:
        errors.append("receipt_identity_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s13.digest(core):
        errors.append("receipt_digest_invalid")
    if (
        safe_report.get("task_id"),
        safe_report.get("schema_version"),
        safe_report.get("validation_status"),
        safe_report.get("product_status"),
        safe_report.get("stop_reason"),
    ) != expected_identity:
        errors.append("safe_identity_invalid")
    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s13.digest(safe_core):
        errors.append("safe_digest_invalid")
    try:
        s13.safe_scan(safe_report)
    except s13.LocalhostDeploymentError as exc:
        errors.append(str(exc))

    source_s12 = _read(Path(s12_path), "s12", errors)
    if source_s12:
        source_core = {key: value for key, value in source_s12.items() if key != "artifact_sha256"}
        if (
            source_s12.get("task_id") != s13.s12.TASK_ID
            or source_s12.get("validation_status") != s13.s12.PASS_STATUS
            or source_s12.get("product_status") != s13.s12.PRODUCT_STATUS
            or source_s12.get("artifact_sha256") != s13.digest(source_core)
        ):
            errors.append("source_s12_contract_invalid")
        if receipt.get("source_identity", {}).get("s12_sha256") != s13.digest(source_s12):
            errors.append("source_s12_binding_invalid")

    outputs = receipt.get("runtime_outputs", {})
    root = Path(str(outputs.get("root") or "")).resolve()
    source_receipt = Path(str(outputs.get("source_s12_receipt_path") or "")).resolve()
    production_database = Path(str(outputs.get("source_database_path") or "")).resolve()
    auth_state = Path(str(outputs.get("auth_state_database_path") or "")).resolve()
    start_script = Path(str(outputs.get("start_script_path") or "")).resolve()
    stop_script = Path(str(outputs.get("stop_script_path") or "")).resolve()
    status_script = Path(str(outputs.get("status_script_path") or "")).resolve()
    deployment_contract = Path(str(outputs.get("deployment_contract_path") or "")).resolve()

    if source_receipt != Path(s12_path).resolve():
        errors.append("source_s12_path_mismatch")
    if not _inside(root, output_root):
        errors.append("s13_root_outside_authority")
    for path, code in (
        (auth_state, "auth_state_missing"),
        (start_script, "start_script_missing"),
        (stop_script, "stop_script_missing"),
        (status_script, "status_script_missing"),
        (deployment_contract, "deployment_contract_missing"),
        (production_database, "production_database_missing"),
    ):
        if not path.is_file():
            errors.append(code)
    if auth_state.is_file():
        try:
            with sqlite3.connect(auth_state) as connection:
                revoked_count = int(connection.execute("SELECT COUNT(*) FROM revoked_sessions").fetchone()[0])
            if revoked_count != 1:
                errors.append(f"revoked_session_count_invalid:{revoked_count}")
        except (sqlite3.Error, TypeError) as exc:
            errors.append(f"auth_state_invalid:{exc}")

    contract = _read(deployment_contract, "deployment_contract", errors) if deployment_contract.is_file() else {}
    if contract and contract != {
        "schema_version": "a1fs.online.v1.s13.localhost_deployment_contract.v1",
        "host": "127.0.0.1",
        "port": 8765,
        "authentication_required": True,
        "required_environment_variables": [
            "A1FS_S11_AUTH_USERNAME",
            "A1FS_S11_AUTH_PASSWORD",
            "A1FS_S11_SESSION_SECRET",
        ],
        "secret_values_embedded": False,
        "pid_file": str(Path(str(outputs.get("pid_file_path") or "")).resolve()),
        "stdout_log": str(Path(str(outputs.get("stdout_log_path") or "")).resolve()),
        "stderr_log": str(Path(str(outputs.get("stderr_log_path") or "")).resolve()),
        "auth_state_database": str(auth_state),
        "external_network_binding_allowed": False,
        "cloudflare_enabled": False,
        "audio_enabled": False,
    }:
        errors.append("deployment_contract_invalid")

    scripts = {}
    for name, path in (("start", start_script), ("stop", stop_script), ("status", status_script)):
        if path.is_file():
            scripts[name] = path.read_text(encoding="utf-8")
    required_start = (
        "A1FS_S11_AUTH_USERNAME",
        "A1FS_S11_AUTH_PASSWORD",
        "A1FS_S11_SESSION_SECRET",
        "127.0.0.1",
        "build_a1fs_online_v1_s13_localhost_production_deployment",
        "A1FS_LOCALHOST_STARTED=PASS",
    )
    for marker in required_start:
        if marker not in scripts.get("start", ""):
            errors.append(f"start_script_marker_missing:{marker}")
    for marker in ("PID_OWNERSHIP_MISMATCH", "A1FS_LOCALHOST_STOPPED=PASS"):
        if marker not in scripts.get("stop", ""):
            errors.append(f"stop_script_marker_missing:{marker}")
    for marker in ("A1FS_LOCALHOST_STATUS=RUNNING", "PORT_OWNERSHIP_INVALID"):
        if marker not in scripts.get("status", ""):
            errors.append(f"status_script_marker_missing:{marker}")
    combined_scripts = "\n".join(scripts.values())
    if s13.CANARY_PASSWORD in combined_scripts or s13.CANARY_SESSION_SECRET in combined_scripts:
        errors.append("secret_value_embedded_in_scripts")

    acceptance = receipt.get("localhost_acceptance_summary", {})
    expected_counts = {
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "persistent_revocation_count": 1,
        "application_server_start_count": 3,
        "port": 8765,
    }
    for key, value in expected_counts.items():
        if acceptance.get(key) != value:
            errors.append(f"acceptance_count_invalid:{key}:{acceptance.get(key)}:{value}")
    for key in (
        "health_endpoint_pass",
        "authentication_required",
        "production_database_read_only_smoke",
        "authenticated_bootstrap_pass",
        "progress_readback_pass",
        "session_survived_process_restart",
        "logout_revocation_survived_process_restart",
        "loopback_binding_only",
    ):
        if acceptance.get(key) is not True:
            errors.append(f"acceptance_required_true_invalid:{key}")

    safety = receipt.get("production_safety", {})
    if (
        safety.get("production_database_unchanged") is not True
        or safety.get("acceptance_used_read_only_production_smoke") is not True
        or safety.get("learner_progress_mutated_by_acceptance") is not False
        or safety.get("auth_state_separated_from_learner_database") is not True
    ):
        errors.append("production_safety_invalid")
    if production_database.is_file() and receipt.get("source_identity", {}).get("production_database_sha256") != s13.file_digest(production_database):
        errors.append("production_database_digest_invalid")

    boundary = receipt.get("deployment_boundary", {})
    if (
        boundary.get("formal_localhost_launch_ready") is not True
        or boundary.get("host") != "127.0.0.1"
        or boundary.get("port") != 8765
        or boundary.get("external_network_binding_allowed") is not False
        or boundary.get("cloudflare_enabled") is not False
        or boundary.get("public_release_completed") is not False
        or boundary.get("secrets_serialized_to_artifact") is not False
    ):
        errors.append("deployment_boundary_invalid")

    capability = receipt.get("capability_contract", {})
    for key in (
        "s12_deployment_bundle_reused",
        "s11_authenticated_boundary_reused",
        "s09_twentyfour_unit_runtime_reused",
        "persistent_logout_revocation_connected",
        "process_lifecycle_bundle_materialized",
        "formal_localhost_launch_ready",
    ):
        if capability.get(key) is not True:
            errors.append(f"capability_required_true_invalid:{key}")
    for key in (
        "parallel_curriculum_created",
        "parallel_learner_state_engine_created",
        "parallel_scoring_engine_created",
        "speaking_capture_enabled",
        "listening_enabled",
        "audio_enabled",
        "mastery_write_enabled",
    ):
        if capability.get(key) is not False:
            errors.append(f"capability_required_false_invalid:{key}")

    for section in (
        "localhost_acceptance_summary",
        "production_safety",
        "deployment_boundary",
        "rollback_boundary",
        "capability_contract",
    ):
        if safe_report.get(section) != receipt.get(section):
            errors.append(f"safe_projection_invalid:{section}")

    return {
        "task_id": s13.TASK_ID,
        "schema_version": s13.SCHEMA_VERSION,
        "validation_status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--safe-report", type=Path, required=True)
    parser.add_argument("--s12", type=Path, required=True)
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
            s12_path=args.s12,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
