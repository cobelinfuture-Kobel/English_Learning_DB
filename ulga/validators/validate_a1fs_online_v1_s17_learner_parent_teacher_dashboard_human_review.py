#!/usr/bin/env python3
"""Independent validator for A1FS Online V1 S17 dashboards and human review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review as s17

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Validates the S17 authenticated learner, parent, and teacher projections, M6 review action, privacy split, launcher, isolated acceptance, production immutability, and no-audio/A2/Cloudflare boundaries; it produces no learner content."
VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_S17_DASHBOARD_HUMAN_REVIEW_VALIDATED"
SAFE_PRIVATE_KEYS = frozenset({
    "attempt_id",
    "session_id",
    "asset_key",
    "response_json",
    "review_queue",
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
    """Return forbidden safe-artifact keys by exact key identity, not substrings."""
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


def _validate_static(root: Path, errors: list[str]) -> None:
    required = {
        "index.html": (
            "學習儀表板與人工審核", "data-dashboard-role=\"learner\"",
            "data-dashboard-role=\"parent\"", "data-dashboard-role=\"teacher\"",
            "human-review-list", "/auth.js", "/app.js",
        ),
        "app.js": (
            "/api/dashboard", "/api/human-review", "/api/human-review/decision",
            "renderRoleDashboard", "renderHumanReviews", "grammar_target_match",
            "meaning_matches_context", "complete_response",
        ),
        "styles.css": (".dashboard-panel", ".review-card", ".review-response"),
        "auth.js": ("/auth/session", "X-CSRF-Token", "/auth/logout"),
    }
    for name, tokens in required.items():
        path = root / name
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"s17_static_missing:{name}:{exc}")
            continue
        for token in tokens:
            if token not in text:
                errors.append(f"s17_static_token_missing:{name}:{token}")
        if name == "app.js" and ("innerHTML" in text or "eval(" in text):
            errors.append("s17_static_unsafe_dom_or_eval")


def _validate_launcher(outputs: Mapping[str, Any], errors: list[str]) -> None:
    paths = {
        "start": Path(str(outputs.get("start_script_path") or "")),
        "stop": Path(str(outputs.get("stop_script_path") or "")),
        "status": Path(str(outputs.get("status_script_path") or "")),
        "contract": Path(str(outputs.get("launch_contract_path") or "")),
    }
    for name, path in paths.items():
        if not path.is_file():
            errors.append(f"s17_launcher_missing:{name}")
    if any(error.startswith("s17_launcher_missing") for error in errors):
        return
    start = paths["start"].read_text(encoding="utf-8")
    stop = paths["stop"].read_text(encoding="utf-8")
    status = paths["status"].read_text(encoding="utf-8")
    if "build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review" not in start:
        errors.append("s17_launcher_module_binding_invalid")
    if "PID_OWNERSHIP_MISMATCH" not in stop or "PORT_OWNERSHIP_INVALID" not in status:
        errors.append("s17_launcher_lifecycle_invalid")
    for secret in (s17.s16.s15.CANARY_PASSWORD, s17.s16.s15.CANARY_SESSION_SECRET):
        if secret in start or secret in stop or secret in status:
            errors.append("s17_launcher_secret_embedded")
    contract = _read(paths["contract"], errors, "s17_launch_contract")
    expected = {
        "host": "127.0.0.1",
        "port": 8765,
        "authentication_required": True,
        "csrf_required_for_review_decision": True,
        "secret_values_embedded": False,
        "dashboard_role_count": 3,
        "role_based_identity_authorization_claimed": False,
        "human_review_authority": "A1FS_V1_M6",
        "external_network_binding_allowed": False,
        "cloudflare_enabled": False,
        "audio_enabled": False,
        "a2_session_enabled": False,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            errors.append(f"s17_launch_contract_invalid:{key}")


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s16_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    output_root = Path(output_root).resolve()
    if (
        receipt.get("task_id") != s17.TASK_ID
        or receipt.get("schema_version") != s17.SCHEMA_VERSION
        or receipt.get("validation_status") != s17.PASS_STATUS
        or receipt.get("product_status") != s17.PRODUCT_STATUS
    ):
        errors.append("s17_receipt_identity_invalid")
    body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s17.digest(body):
        errors.append("s17_receipt_digest_invalid")
    safe_body = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s17.digest(safe_body):
        errors.append("s17_safe_digest_invalid")
    try:
        s17.safe_scan(safe_report)
    except s17.DashboardReviewError as exc:
        errors.append(str(exc))
    for forbidden in sorted(_find_exact_private_keys(safe_report)):
        errors.append(f"s17_safe_private_key_present:{forbidden}")

    outputs = receipt.get("runtime_outputs", {})
    root = Path(str(outputs.get("root") or "")).resolve()
    acceptance_database = Path(str(outputs.get("acceptance_database_path") or "")).resolve()
    acceptance_state = Path(str(outputs.get("acceptance_state_root") or "")).resolve()
    secure_static = Path(str(outputs.get("secure_static_root") or "")).resolve()
    production_database = Path(str(outputs.get("source_database_path") or "")).resolve()
    if root != (output_root / "dashboard_human_review").resolve():
        errors.append("s17_runtime_root_noncanonical")
    for name, path in (
        ("acceptance_database", acceptance_database),
        ("acceptance_state", acceptance_state),
        ("secure_static", secure_static),
        ("launch_bundle", Path(str(outputs.get("bundle_root") or ""))),
    ):
        if not _inside(path, output_root):
            errors.append(f"s17_output_outside_authority_root:{name}")
    if Path(str(outputs.get("source_s16_receipt_path") or "")).resolve() != Path(s16_path).resolve():
        errors.append("s17_source_s16_binding_invalid")
    if not acceptance_database.is_file():
        errors.append("s17_acceptance_database_missing")
    if not acceptance_state.is_dir():
        errors.append("s17_acceptance_state_missing")
    _validate_static(secure_static, errors)
    _validate_launcher(outputs, errors)

    summary = receipt.get("dashboard_review_summary", {})
    expected_summary = {
        "unit_count": 24,
        "scored_lesson_count": 48,
        "dashboard_role_count": 3,
        "learner_dashboard_pass": True,
        "parent_dashboard_pass": True,
        "teacher_dashboard_pass": True,
        "m9_dashboard_projection_reused": True,
        "m6_human_review_authority_reused": True,
        "pending_human_review_count_before": 1,
        "pending_human_review_count_after": 0,
        "authenticated_dashboard_endpoint_pass": True,
        "authenticated_review_queue_endpoint_pass": True,
        "csrf_review_decision_pass": True,
        "human_approve_outcome_pass": True,
        "completion_after_human_approval": True,
        "dashboard_after_completion_pass": True,
        "raw_response_excluded_from_dashboard": True,
        "review_queue_raw_response_available": True,
        "role_based_identity_authorization_claimed": False,
        "production_database_unchanged": True,
        "acceptance_used_isolated_database_clone": True,
        "parallel_dashboard_engine_created": False,
        "parallel_review_engine_created": False,
        "a2_unlocked": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "cloudflare_enabled": False,
    }
    for key, value in expected_summary.items():
        if summary.get(key) != value:
            errors.append(f"s17_summary_invalid:{key}")

    production = receipt.get("production_safety", {})
    try:
        actual_sha = s17.file_digest(production_database)
    except OSError as exc:
        errors.append(f"s17_production_database_unreadable:{exc}")
        actual_sha = ""
    if (
        production.get("production_database_sha256_before") != actual_sha
        or production.get("production_database_sha256_after") != actual_sha
        or production.get("production_database_unchanged") is not True
        or production.get("acceptance_used_isolated_database_clone") is not True
        or production.get("learner_progress_mutated_by_acceptance") is not False
        or production.get("raw_response_serialized_to_safe_artifact") is not False
    ):
        errors.append("s17_production_safety_invalid")

    expected_capability = {
        "s16_canonical_learning_integration_reused": True,
        "m9_dashboard_projection_reused": True,
        "m6_human_review_authority_reused": True,
        "learner_dashboard_connected": True,
        "parent_dashboard_connected": True,
        "teacher_dashboard_connected": True,
        "authenticated_human_review_queue_connected": True,
        "authenticated_human_review_decision_connected": True,
        "parallel_curriculum_created": False,
        "parallel_learner_state_engine_created": False,
        "parallel_scoring_engine_created": False,
        "parallel_mastery_engine_created": False,
        "parallel_dashboard_engine_created": False,
        "parallel_review_engine_created": False,
        "role_based_identity_authorization_claimed": False,
        "a2_payload_access_granted": False,
        "a2_session_start_granted": False,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "cloudflare_enabled": False,
    }
    if receipt.get("capability_contract") != expected_capability:
        errors.append("s17_capability_contract_invalid")
    if receipt.get("stop_reason") != "NONE" or receipt.get("next_short_step") != s17.NEXT_SHORT_STEP:
        errors.append("s17_transition_contract_invalid")
    return {
        "task_id": s17.TASK_ID,
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S17_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--s16", type=Path, required=True)
    args = parser.parse_args(argv)
    errors: list[str] = []
    receipt = _read(args.receipt, errors, "receipt")
    safe = _read(args.report, errors, "report")
    result = validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=args.receipt.parent,
        s16_path=args.s16,
    )
    if errors:
        result["errors"] = errors + result["errors"]
        result["error_count"] = len(result["errors"])
        result["validation_status"] = "FAIL_A1FS_ONLINE_V1_S17_VALIDATION"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["error_count"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
