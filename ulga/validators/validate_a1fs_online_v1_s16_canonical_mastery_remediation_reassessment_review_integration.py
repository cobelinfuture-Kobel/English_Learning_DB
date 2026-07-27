#!/usr/bin/env python3
"""Independent validator for A1FS Online V1 S16 canonical M7/M8 integration."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_s16_canonical_mastery_remediation_reassessment_review_integration as s16

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates the S16 runtime-only graph projection, isolated M7/M8 acceptance, learner projection, launcher, "
    "production immutability, and no-audio/A2/dashboard boundaries; no learner content is produced."
)
VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_S16_CANONICAL_LEARNING_INTEGRATION_VALIDATED"


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


def _validate_graph(graph: Mapping[str, Any], errors: list[str]) -> None:
    if graph.get("validation_status") != s16.m7.GRAPH_STATUS:
        errors.append("s16_graph_status_invalid")
    counts = graph.get("counts", {})
    expected = {
        "node_count": 73,
        "coverage_record_count": 24,
        "lesson_count": 48,
        "required_mastery_node_count": 72,
        "a2_handoff_lesson_count": 0,
        "uncovered_required_node_count": 0,
    }
    for key, value in expected.items():
        if counts.get(key) != value:
            errors.append(f"s16_graph_count_invalid:{key}")
    nodes = graph.get("nodes", [])
    coverage = graph.get("coverage", [])
    required = graph.get("a2_lock_contract", {}).get("required_mastery_node_ids", [])
    if len(nodes) != 73 or len({row.get("node_id") for row in nodes}) != 73:
        errors.append("s16_graph_node_identity_invalid")
    if len(required) != 72 or len(set(required)) != 72:
        errors.append("s16_graph_required_partition_invalid")
    if sum(str(row.get("node_id", "")).startswith("LESSON:") for row in nodes) != 48:
        errors.append("s16_graph_lesson_node_count_invalid")
    if sum(str(row.get("node_id", "")).startswith("CAPABILITY:GRAMMAR:") for row in nodes) != 24:
        errors.append("s16_graph_grammar_node_count_invalid")
    if len(coverage) != 24 or any(len(row.get("asset_body_ids", [])) != 8 for row in coverage):
        errors.append("s16_graph_coverage_denominator_invalid")
    boundary = graph.get("a2_lock_contract", {})
    if boundary.get("runtime_unlock_implemented") is not False or boundary.get("state") != "LOCKED_BY_DESIGN":
        errors.append("s16_graph_a2_boundary_invalid")
    projection = graph.get("projection_identity", {})
    if projection.get("new_curriculum_created") is not False or projection.get("runtime_projection_only") is not True:
        errors.append("s16_graph_projection_boundary_invalid")


def _validate_static(root: Path, errors: list[str]) -> None:
    required = {
        "index.html": ("精熟、補救與複習", "既有 M7", "沿用 M8", "/auth.js", "/app.js"),
        "app.js": (
            "renderCanonical", "mastered_required_count", "open_remediation_count",
            "pending_reassessment_count", "due_review_count", "A2 仍鎖定",
        ),
        "styles.css": (".canonical-panel",),
        "auth.js": ("/auth/session", "X-CSRF-Token", "/auth/logout"),
    }
    for name, tokens in required.items():
        path = root / name
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"s16_static_missing:{name}:{exc}")
            continue
        for token in tokens:
            if token not in text:
                errors.append(f"s16_static_token_missing:{name}:{token}")
        if name == "app.js" and ("innerHTML" in text or "eval(" in text):
            errors.append("s16_static_unsafe_dom_or_eval")


def _validate_launcher(outputs: Mapping[str, Any], errors: list[str]) -> None:
    paths = {
        "start": Path(str(outputs.get("start_script_path") or "")),
        "stop": Path(str(outputs.get("stop_script_path") or "")),
        "status": Path(str(outputs.get("status_script_path") or "")),
        "contract": Path(str(outputs.get("launch_contract_path") or "")),
    }
    for name, path in paths.items():
        if not path.is_file():
            errors.append(f"s16_launcher_missing:{name}")
    if errors and any(error.startswith("s16_launcher_missing") for error in errors):
        return
    start = paths["start"].read_text(encoding="utf-8")
    stop = paths["stop"].read_text(encoding="utf-8")
    status = paths["status"].read_text(encoding="utf-8")
    module = "build_a1fs_online_v1_s16_canonical_mastery_remediation_reassessment_review_integration"
    if module not in start:
        errors.append("s16_launcher_module_binding_invalid")
    if "PID_OWNERSHIP_MISMATCH" not in stop or "PORT_OWNERSHIP_INVALID" not in status:
        errors.append("s16_launcher_lifecycle_invalid")
    for secret in (s16.s15.CANARY_PASSWORD, s16.s15.CANARY_SESSION_SECRET):
        if secret in start or secret in stop or secret in status:
            errors.append("s16_launcher_secret_embedded")
    contract = _read(paths["contract"], errors, "s16_launch_contract")
    expected = {
        "host": "127.0.0.1",
        "port": 8765,
        "authentication_required": True,
        "secret_values_embedded": False,
        "canonical_m7_mastery_enabled": True,
        "canonical_m8_review_scheduling_enabled": True,
        "external_network_binding_allowed": False,
        "cloudflare_enabled": False,
        "audio_enabled": False,
        "a2_session_enabled": False,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            errors.append(f"s16_launch_contract_invalid:{key}")


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s15_path: Path,
    cp01_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    output_root = Path(output_root).resolve()
    if (
        receipt.get("task_id") != s16.TASK_ID
        or receipt.get("schema_version") != s16.SCHEMA_VERSION
        or receipt.get("validation_status") != s16.PASS_STATUS
        or receipt.get("product_status") != s16.PRODUCT_STATUS
    ):
        errors.append("s16_receipt_identity_invalid")
    body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s16.digest(body):
        errors.append("s16_receipt_digest_invalid")
    safe_body = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s16.digest(safe_body):
        errors.append("s16_safe_digest_invalid")
    try:
        s16.safe_scan(safe_report)
    except s16.CanonicalLearningError as exc:
        errors.append(str(exc))

    outputs = receipt.get("runtime_outputs", {})
    root = Path(str(outputs.get("root") or "")).resolve()
    graph_path = Path(str(outputs.get("canonical_graph_path") or "")).resolve()
    acceptance_database = Path(str(outputs.get("acceptance_database_path") or "")).resolve()
    state_root = Path(str(outputs.get("canonical_state_root") or "")).resolve()
    secure_static = Path(str(outputs.get("secure_static_root") or "")).resolve()
    production_database = Path(str(outputs.get("source_database_path") or "")).resolve()
    if root != (output_root / "canonical_learning_integration").resolve():
        errors.append("s16_runtime_root_noncanonical")
    for name, path in (
        ("graph", graph_path), ("acceptance_database", acceptance_database),
        ("state_root", state_root), ("secure_static", secure_static),
        ("launch_bundle", Path(str(outputs.get("bundle_root") or ""))),
    ):
        if not _inside(path, output_root):
            errors.append(f"s16_output_outside_authority_root:{name}")
    if Path(str(outputs.get("source_s15_receipt_path") or "")).resolve() != Path(s15_path).resolve():
        errors.append("s16_source_s15_binding_invalid")
    if Path(str(outputs.get("source_cp01_path") or "")).resolve() != Path(cp01_path).resolve():
        errors.append("s16_source_cp01_binding_invalid")

    graph = _read(graph_path, errors, "s16_graph")
    _validate_graph(graph, errors)
    _validate_static(secure_static, errors)
    _validate_launcher(outputs, errors)

    summary = receipt.get("canonical_learning_summary", {})
    expected_summary = {
        "unit_count": 24,
        "scored_lesson_count": 48,
        "required_mastery_node_count": 72,
        "mastered_required_count": 3,
        "missing_mastery_count": 69,
        "open_remediation_count": 2,
        "pending_reassessment_count": 2,
        "resolved_diagnosis_count": 1,
        "due_review_count": 3,
        "retained_required_count": 0,
        "retention_confirmed": False,
        "human_approved_attempt_count": 1,
        "latest_attempt_completion_gate_preserved": True,
        "high_failure_completed_session_count": 1,
        "m7_validation_pass": True,
        "m8_validation_pass": True,
        "learner_progress_projection_pass": True,
        "production_database_unchanged": True,
        "acceptance_used_isolated_database_clone": True,
        "mastery_write_connected": True,
        "remediation_connected": True,
        "reassessment_connected": True,
        "review_schedule_connected": True,
        "a2_unlocked": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
    }
    for key, value in expected_summary.items():
        if summary.get(key) != value:
            errors.append(f"s16_summary_invalid:{key}")

    m7_path = state_root / s16.core.CANARY_LEARNER_ID / "m7" / "a1fs_v1_m7_mastery_snapshot.private.json"
    m8_path = state_root / s16.core.CANARY_LEARNER_ID / "m8" / "a1fs_v1_m8_retention_snapshot.private.json"
    if graph and acceptance_database.is_file() and m7_path.is_file() and m8_path.is_file():
        m7_report = s16.core.validate_m7(acceptance_database, graph_path, m7_path)
        m8_report = s16.core.validate_m8(acceptance_database, graph_path, m7_path, m8_path)
        if m7_report.get("error_count"):
            errors.extend(f"s16_m7:{item}" for item in m7_report.get("errors", []))
        if m8_report.get("error_count"):
            errors.extend(f"s16_m8:{item}" for item in m8_report.get("errors", []))
    else:
        errors.append("s16_acceptance_outputs_missing")

    production = receipt.get("production_safety", {})
    try:
        actual_sha = s16.file_digest(production_database)
    except OSError as exc:
        errors.append(f"s16_production_database_unreadable:{exc}")
        actual_sha = ""
    if (
        production.get("production_database_sha256_before") != actual_sha
        or production.get("production_database_sha256_after") != actual_sha
        or production.get("production_database_unchanged") is not True
        or production.get("acceptance_used_isolated_database_clone") is not True
        or production.get("learner_progress_mutated_by_acceptance") is not False
        or production.get("runtime_mastery_writes_only_after_real_scored_session_completion") is not True
    ):
        errors.append("s16_production_safety_invalid")

    expected_capability = {
        "s15_scored_journey_reused": True,
        "cp01_canonical_twentyfour_unit_authority_reused": True,
        "m6_response_scoring_authority_reused": True,
        "m7_mastery_engine_reused": True,
        "m7_remediation_engine_reused": True,
        "m7_reassessment_queue_reused": True,
        "m8_review_scheduling_engine_reused": True,
        "parallel_curriculum_created": False,
        "parallel_learner_state_engine_created": False,
        "parallel_scoring_engine_created": False,
        "parallel_mastery_engine_created": False,
        "dashboard_created": False,
        "mastery_write_enabled_after_scored_completion": True,
        "a2_payload_access_granted": False,
        "a2_session_start_granted": False,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "cloudflare_enabled": False,
    }
    if receipt.get("capability_contract") != expected_capability:
        errors.append("s16_capability_contract_invalid")
    if receipt.get("stop_reason") != "NONE" or receipt.get("next_short_step") != s16.NEXT_SHORT_STEP:
        errors.append("s16_transition_contract_invalid")
    return {
        "task_id": s16.TASK_ID,
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S16_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--s15", type=Path, required=True)
    parser.add_argument("--cp01", type=Path, required=True)
    args = parser.parse_args(argv)
    errors: list[str] = []
    receipt = _read(args.receipt, errors, "receipt")
    safe = _read(args.report, errors, "report")
    result = validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=args.receipt.parent,
        s15_path=args.s15,
        cp01_path=args.cp01,
    )
    if errors:
        result["errors"] = errors + result["errors"]
        result["error_count"] = len(result["errors"])
        result["validation_status"] = "FAIL_A1FS_ONLINE_V1_S16_VALIDATION"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["error_count"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
