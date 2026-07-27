#!/usr/bin/env python3
"""Independent validator for A1FS Online V1 S18 E2E acceptance/recovery."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_s18_nonaudio_learner_product_e2e_release_acceptance_recovery as s18

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Validates S18 isolated end-to-end learner-product acceptance, restart persistence, logout revocation, operator lifecycle reuse, production immutability, and frozen no-audio/A2/Cloudflare/release-candidate boundaries; it produces no learner content or product capability."
VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_S18_NONAUDIO_E2E_RELEASE_ACCEPTANCE_RECOVERY_VALIDATED"

SAFE_PRIVATE_KEYS = frozenset({
    "attempt_id", "session_id", "asset_key", "response", "response_json",
    "review_queue", "csrf", "token", "password", "session_secret",
})


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


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


def validate_outputs(
    *, receipt: Mapping[str, Any], safe_report: Mapping[str, Any],
    output_root: Path, s17_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    output_root = Path(output_root).resolve()
    if (
        receipt.get("task_id") != s18.TASK_ID
        or receipt.get("schema_version") != s18.SCHEMA_VERSION
        or receipt.get("validation_status") != s18.PASS_STATUS
        or receipt.get("product_status") != s18.PRODUCT_STATUS
    ):
        errors.append("s18_receipt_identity_invalid")
    receipt_body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s18.digest(receipt_body):
        errors.append("s18_receipt_digest_invalid")
    safe_body = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s18.digest(safe_body):
        errors.append("s18_safe_digest_invalid")
    try:
        s18.safe_scan(safe_report)
    except (s18.E2ERecoveryError, s18.s17.DashboardReviewError) as exc:
        errors.append(str(exc))
    for key in sorted(_find_exact_private_keys(safe_report)):
        errors.append(f"s18_safe_private_key_present:{key}")

    outputs = receipt.get("runtime_outputs", {})
    root = Path(str(outputs.get("root") or "")).resolve()
    acceptance_database = Path(str(outputs.get("acceptance_database_path") or "")).resolve()
    acceptance_state = Path(str(outputs.get("acceptance_state_root") or "")).resolve()
    acceptance_auth = Path(str(outputs.get("acceptance_auth_state_path") or "")).resolve()
    production_database = Path(str(outputs.get("source_database_path") or "")).resolve()
    if root != (output_root / "nonaudio_e2e_release_acceptance_recovery").resolve():
        errors.append("s18_runtime_root_noncanonical")
    for name, path in (
        ("acceptance_database", acceptance_database),
        ("acceptance_state", acceptance_state),
        ("acceptance_auth", acceptance_auth),
    ):
        if not _inside(path, output_root):
            errors.append(f"s18_output_outside_authority_root:{name}")
    if Path(str(outputs.get("source_s17_receipt_path") or "")).resolve() != Path(s17_path).resolve():
        errors.append("s18_source_s17_binding_invalid")
    if not acceptance_database.is_file():
        errors.append("s18_acceptance_database_missing")
    if not acceptance_state.is_dir():
        errors.append("s18_acceptance_state_missing")
    if not acceptance_auth.is_file():
        errors.append("s18_acceptance_auth_missing")
    for key in (
        "source_start_script_path", "source_stop_script_path",
        "source_status_script_path", "source_launch_contract_path",
    ):
        if not Path(str(outputs.get(key) or "")).is_file():
            errors.append(f"s18_source_operator_artifact_missing:{key}")

    summary = receipt.get("e2e_release_acceptance_summary", {})
    expected_summary = {
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "scored_lesson_count": 48,
        "speaking_practice_lesson_count": 24,
        "dashboard_role_count": 3,
        "reading_scored_journey_completed": True,
        "writing_human_review_journey_completed": True,
        "pending_human_review_count_before": 1,
        "pending_human_review_count_after": 0,
        "authenticated_bootstrap_pass": True,
        "authenticated_progress_pass": True,
        "authenticated_dashboard_pass": True,
        "authenticated_review_queue_pass": True,
        "authenticated_session_survived_server_restart": True,
        "active_learning_session_survived_server_restart": True,
        "progress_survived_server_restart": True,
        "dashboard_survived_server_restart": True,
        "review_queue_survived_server_restart": True,
        "human_approval_after_restart_pass": True,
        "logout_revocation_survived_server_restart": True,
        "persistent_revocation_count": 1,
        "application_server_start_count": 3,
        "start_script_contract_pass": True,
        "stop_script_contract_pass": True,
        "status_script_contract_pass": True,
        "launch_contract_boundary_pass": True,
        "p0_blocker_count": 0,
        "p1_blocker_count": 0,
        "production_database_unchanged": True,
        "acceptance_used_isolated_database_clone": True,
        "acceptance_used_isolated_state_clone": True,
        "release_candidate_created": False,
        "role_based_identity_authorization_claimed": False,
        "a2_unlocked": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "cloudflare_enabled": False,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            errors.append(f"s18_summary_invalid:{key}")

    production = receipt.get("production_safety", {})
    try:
        actual_sha = s18.file_digest(production_database)
    except OSError as exc:
        errors.append(f"s18_production_database_unreadable:{exc}")
        actual_sha = ""
    if (
        production.get("production_database_sha256_before") != actual_sha
        or production.get("production_database_sha256_after") != actual_sha
        or production.get("production_database_unchanged") is not True
        or production.get("acceptance_used_isolated_database_clone") is not True
        or production.get("acceptance_used_isolated_state_clone") is not True
        or production.get("learner_progress_mutated_by_acceptance") is not False
        or production.get("raw_response_serialized_to_safe_artifact") is not False
    ):
        errors.append("s18_production_safety_invalid")

    expected_capability = {
        "s17_product_runtime_reused": True,
        "s17_operator_lifecycle_reused": True,
        "m6_scoring_review_reused": True,
        "m7_m8_canonical_learning_reused": True,
        "m9_dashboard_projection_reused": True,
        "new_product_capability_created": False,
        "parallel_curriculum_created": False,
        "parallel_learner_state_engine_created": False,
        "parallel_scoring_engine_created": False,
        "parallel_mastery_engine_created": False,
        "parallel_dashboard_engine_created": False,
        "parallel_review_engine_created": False,
        "release_candidate_created": False,
        "role_based_identity_authorization_claimed": False,
        "a2_payload_access_granted": False,
        "a2_session_start_granted": False,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "cloudflare_enabled": False,
    }
    if receipt.get("capability_contract") != expected_capability:
        errors.append("s18_capability_contract_invalid")
    if receipt.get("stop_reason") != "NONE" or receipt.get("next_short_step") != s18.NEXT_SHORT_STEP:
        errors.append("s18_transition_contract_invalid")
    if safe_report.get("product_status") != s18.PRODUCT_STATUS:
        errors.append("s18_safe_product_status_invalid")
    return {
        "task_id": s18.TASK_ID,
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S18_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--s17", type=Path, required=True)
    args = parser.parse_args(argv)
    initial_errors: list[str] = []
    receipt = _read(args.receipt, initial_errors, "receipt")
    safe = _read(args.report, initial_errors, "report")
    result = validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=args.receipt.parent,
        s17_path=args.s17,
    )
    if initial_errors:
        result["errors"] = initial_errors + result["errors"]
        result["error_count"] = len(result["errors"])
        result["validation_status"] = "FAIL_A1FS_ONLINE_V1_S18_VALIDATION"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["error_count"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
