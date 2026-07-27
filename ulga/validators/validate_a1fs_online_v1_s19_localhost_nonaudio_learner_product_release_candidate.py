#!/usr/bin/env python3
"""Independent validator for the S19 localhost no-audio release candidate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_s19_localhost_nonaudio_learner_product_release_candidate as s19

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates the versioned S19 localhost release manifest, checksums, operator scripts, "
    "authenticated isolated smoke, production-state immutability, and no-audio/A2/Cloudflare "
    "boundaries; it produces no learner content or product capability."
)
VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_S19_LOCALHOST_NONAUDIO_RELEASE_CANDIDATE_VALIDATED"
SAFE_PRIVATE_KEYS = frozenset({
    "attempt_id", "session_id", "asset_key", "response", "response_json", "review_queue",
    "database_path", "auth_state_path", "state_root", "release_manifest_path",
})


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _read(path: Path, errors: list[str], code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{code}_unreadable:{exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{code}_not_object")
        return {}
    return value


def _find_exact_private_keys(value: Any) -> set[str]:
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                folded = str(key).casefold()
                if folded in SAFE_PRIVATE_KEYS:
                    found.add(folded)
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return found


def _validate_operator(outputs: Mapping[str, Any], errors: list[str]) -> None:
    paths = {
        "start": Path(str(outputs.get("start_script_path") or "")),
        "stop": Path(str(outputs.get("stop_script_path") or "")),
        "status": Path(str(outputs.get("status_script_path") or "")),
        "readback": Path(str(outputs.get("readback_script_path") or "")),
        "contract": Path(str(outputs.get("release_contract_path") or "")),
    }
    for name, path in paths.items():
        if not path.is_file():
            errors.append(f"s19_operator_file_missing:{name}")
    if any(error.startswith("s19_operator_file_missing") for error in errors):
        return
    start = paths["start"].read_text(encoding="utf-8")
    stop = paths["stop"].read_text(encoding="utf-8")
    status = paths["status"].read_text(encoding="utf-8")
    readback = paths["readback"].read_text(encoding="utf-8")
    if not all(token in start for token in (
        "A1FS_S19_LOCALHOST_RC_STARTED=PASS", "PORT_IN_USE", "PID_FILE_ALREADY_EXISTS",
        "build_a1fs_online_v1_s19_localhost_nonaudio_learner_product_release_candidate",
    )):
        errors.append("s19_start_script_contract_invalid")
    if not all(token in stop for token in (
        "PID_OWNERSHIP_MISMATCH", "PORT_STILL_LISTENING", "A1FS_S19_LOCALHOST_RC_STOPPED=PASS",
    )):
        errors.append("s19_stop_script_contract_invalid")
    if not all(token in status for token in (
        "PORT_OWNERSHIP_INVALID", "UNHEALTHY", "A1FS_S19_LOCALHOST_RC_STATUS=RUNNING",
    )):
        errors.append("s19_status_script_contract_invalid")
    if "readback --receipt" not in readback or "A1FS_S19_LOCALHOST_RC_READBACK_FAILED" not in readback:
        errors.append("s19_readback_script_contract_invalid")
    for secret in (
        s19.s18.s17.s16.s15.CANARY_PASSWORD,
        s19.s18.s17.s16.s15.CANARY_SESSION_SECRET,
    ):
        if any(secret in text for text in (start, stop, status, readback)):
            errors.append("s19_operator_secret_embedded")
    contract = _read(paths["contract"], errors, "s19_release_contract")
    expected = {
        "release_candidate_id": s19.RELEASE_CANDIDATE_ID,
        "host": "127.0.0.1",
        "port": 8765,
        "authentication_required": True,
        "csrf_required_for_state_change": True,
        "dashboard_role_count": 3,
        "human_review_authority": "A1FS_V1_M6",
        "secret_values_embedded": False,
        "external_network_binding_allowed": False,
        "public_delivery_enabled": False,
        "cloudflare_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "a2_session_enabled": False,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            errors.append(f"s19_release_contract_invalid:{key}")


def validate_outputs(
    *, receipt: Mapping[str, Any], safe_report: Mapping[str, Any],
    output_root: Path, s18_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    output_root = Path(output_root).resolve()
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("release_candidate_id"),
    )
    if identity != (
        s19.TASK_ID, s19.SCHEMA_VERSION, s19.PASS_STATUS,
        s19.PRODUCT_STATUS, s19.RELEASE_CANDIDATE_ID,
    ):
        errors.append("s19_receipt_identity_invalid")
    body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s19.digest(body):
        errors.append("s19_receipt_digest_invalid")
    safe_body = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s19.digest(safe_body):
        errors.append("s19_safe_digest_invalid")
    try:
        s19.safe_scan(safe_report)
    except Exception as exc:  # underlying safe scanner has a task-specific exception type
        errors.append(str(exc))
    for key in sorted(_find_exact_private_keys(safe_report)):
        errors.append(f"s19_safe_private_key_present:{key}")

    outputs = receipt.get("runtime_outputs", {})
    root = Path(str(outputs.get("root") or "")).resolve()
    release_root = Path(str(outputs.get("release_root") or "")).resolve()
    secure_static = Path(str(outputs.get("secure_static_root") or "")).resolve()
    manifest_path = Path(str(outputs.get("release_manifest_path") or "")).resolve()
    checksum_path = Path(str(outputs.get("checksum_manifest_path") or "")).resolve()
    acceptance_database = Path(str(outputs.get("acceptance_database_path") or "")).resolve()
    acceptance_auth = Path(str(outputs.get("acceptance_auth_state_path") or "")).resolve()
    acceptance_state = Path(str(outputs.get("acceptance_state_root") or "")).resolve()
    if root != (output_root / "localhost_nonaudio_release_candidate").resolve():
        errors.append("s19_runtime_root_noncanonical")
    for name, path in (
        ("release_root", release_root),
        ("secure_static", secure_static),
        ("release_manifest", manifest_path),
        ("checksums", checksum_path),
        ("acceptance_database", acceptance_database),
        ("acceptance_auth", acceptance_auth),
        ("acceptance_state", acceptance_state),
        ("operator_root", Path(str(outputs.get("operator_root") or ""))),
    ):
        if not _inside(path, output_root):
            errors.append(f"s19_output_outside_authority_root:{name}")
    if Path(str(outputs.get("source_s18_receipt_path") or "")).resolve() != Path(s18_path).resolve():
        errors.append("s19_source_s18_binding_invalid")
    for name, path, kind in (
        ("release_root", release_root, "dir"),
        ("secure_static", secure_static, "dir"),
        ("release_manifest", manifest_path, "file"),
        ("checksums", checksum_path, "file"),
        ("acceptance_database", acceptance_database, "file"),
        ("acceptance_auth", acceptance_auth, "file"),
        ("acceptance_state", acceptance_state, "dir"),
    ):
        present = path.is_dir() if kind == "dir" else path.is_file()
        if not present:
            errors.append(f"s19_output_missing:{name}")
    if release_root.is_dir() and checksum_path.is_file():
        try:
            s19._validate_checksums(release_root, checksum_path)
        except (s19.ReleaseCandidateError, OSError, KeyError, ValueError) as exc:
            errors.append(str(exc))
    _validate_operator(outputs, errors)

    manifest = _read(manifest_path, errors, "s19_release_manifest") if manifest_path.is_file() else {}
    manifest_expected = {
        "release_candidate_id": s19.RELEASE_CANDIDATE_ID,
        "task_id": s19.TASK_ID,
        "host": "127.0.0.1",
        "port": 8765,
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "scored_lesson_count": 48,
        "speaking_practice_lesson_count": 24,
        "dashboard_role_count": 3,
        "external_deployment_enabled": False,
        "public_delivery_enabled": False,
        "cloudflare_enabled": False,
        "audio_enabled": False,
        "a2_session_enabled": False,
    }
    for key, value in manifest_expected.items():
        if manifest.get(key) != value:
            errors.append(f"s19_release_manifest_invalid:{key}")
    if secure_static.is_dir():
        try:
            if manifest.get("secure_static_sha256") != s19.directory_digest(secure_static):
                errors.append("s19_secure_static_digest_invalid")
        except (s19.ReleaseCandidateError, OSError) as exc:
            errors.append(str(exc))

    summary = receipt.get("release_candidate_summary", {})
    expected_summary = {
        "release_candidate_id": s19.RELEASE_CANDIDATE_ID,
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "scored_lesson_count": 48,
        "speaking_practice_lesson_count": 24,
        "dashboard_role_count": 3,
        "source_s18_e2e_acceptance_pass": True,
        "release_manifest_created": True,
        "checksum_manifest_created": True,
        "secure_static_snapshot_created": True,
        "start_script_contract_pass": True,
        "stop_script_contract_pass": True,
        "status_script_contract_pass": True,
        "readback_script_contract_pass": True,
        "release_contract_boundary_pass": True,
        "authenticated_candidate_bootstrap_pass": True,
        "authenticated_candidate_progress_pass": True,
        "authenticated_candidate_dashboard_pass": True,
        "authenticated_candidate_review_queue_pass": True,
        "candidate_smoke_server_start_count": 1,
        "p0_blocker_count": 0,
        "p1_blocker_count": 0,
        "release_candidate_created": True,
        "release_candidate_externally_deployed": False,
        "production_database_unchanged": True,
        "production_state_unchanged": True,
        "production_auth_state_unchanged": True,
        "acceptance_used_isolated_database_clone": True,
        "acceptance_used_isolated_state_clone": True,
        "acceptance_used_isolated_auth_clone": True,
        "role_based_identity_authorization_claimed": False,
        "a2_unlocked": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "cloudflare_enabled": False,
    }
    for key, value in expected_summary.items():
        if summary.get(key) != value:
            errors.append(f"s19_summary_invalid:{key}")
    if not isinstance(summary.get("checksum_file_count"), int) or summary.get("checksum_file_count", 0) < 9:
        errors.append("s19_checksum_file_count_invalid")

    production = receipt.get("production_safety", {})
    source_database = Path(str(outputs.get("source_database_path") or "")).resolve()
    source_auth = Path(str(outputs.get("source_auth_state_path") or "")).resolve()
    source_state = Path(str(outputs.get("source_state_root") or "")).resolve()
    try:
        database_sha = s19.file_digest(source_database)
        auth_sha = s19.file_digest(source_auth)
        state_sha = s19.directory_digest(source_state)
    except (OSError, s19.ReleaseCandidateError) as exc:
        errors.append(f"s19_production_source_unreadable:{exc}")
        database_sha = auth_sha = state_sha = ""
    if (
        production.get("production_database_sha256_before") != database_sha
        or production.get("production_database_sha256_after") != database_sha
        or production.get("production_auth_state_sha256_before") != auth_sha
        or production.get("production_auth_state_sha256_after") != auth_sha
        or production.get("production_state_sha256_before") != state_sha
        or production.get("production_state_sha256_after") != state_sha
        or production.get("production_database_unchanged") is not True
        or production.get("production_auth_state_unchanged") is not True
        or production.get("production_state_unchanged") is not True
        or production.get("acceptance_used_isolated_database_clone") is not True
        or production.get("acceptance_used_isolated_state_clone") is not True
        or production.get("acceptance_used_isolated_auth_clone") is not True
        or production.get("learner_progress_mutated_by_acceptance") is not False
        or production.get("raw_response_serialized_to_safe_artifact") is not False
    ):
        errors.append("s19_production_safety_invalid")

    expected_capability = {
        "s18_e2e_acceptance_reused": True,
        "s17_product_runtime_reused": True,
        "s17_operator_lifecycle_repackaged": True,
        "m6_scoring_review_reused": True,
        "m7_m8_canonical_learning_reused": True,
        "m9_dashboard_projection_reused": True,
        "versioned_localhost_release_candidate_created": True,
        "new_product_capability_created": False,
        "parallel_curriculum_created": False,
        "parallel_learner_state_engine_created": False,
        "parallel_scoring_engine_created": False,
        "parallel_mastery_engine_created": False,
        "parallel_dashboard_engine_created": False,
        "parallel_review_engine_created": False,
        "external_deployment_created": False,
        "public_delivery_enabled": False,
        "role_based_identity_authorization_claimed": False,
        "a2_payload_access_granted": False,
        "a2_session_start_granted": False,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "cloudflare_enabled": False,
    }
    if receipt.get("capability_contract") != expected_capability:
        errors.append("s19_capability_contract_invalid")
    if receipt.get("stop_reason") != "NONE" or receipt.get("next_short_step") != s19.NEXT_SHORT_STEP:
        errors.append("s19_transition_contract_invalid")
    return {
        "task_id": s19.TASK_ID,
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S19_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--s18", type=Path, required=True)
    args = parser.parse_args(argv)
    errors: list[str] = []
    receipt = _read(args.receipt, errors, "s19_receipt")
    report = _read(args.report, errors, "s19_report")
    result = validate_outputs(
        receipt=receipt,
        safe_report=report,
        output_root=args.receipt.parent,
        s18_path=args.s18,
    )
    result["errors"] = errors + result["errors"]
    result["error_count"] = len(result["errors"])
    if result["error_count"]:
        result["validation_status"] = "FAIL_A1FS_ONLINE_V1_S19_VALIDATION"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
