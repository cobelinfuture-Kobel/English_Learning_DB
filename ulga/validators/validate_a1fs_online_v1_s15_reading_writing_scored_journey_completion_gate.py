#!/usr/bin/env python3
"""Independent validator for A1FS Online V1 S15 scored journeys and completion gate."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_s15_reading_writing_scored_journey_completion_gate as s15

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates reuse of S14/M3/M6 authorities, Reading/Writing latest-attempt completion gating, "
    "retry history, human-review approval, isolated acceptance, learner UI, and no-audio boundaries only."
)
VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_S15_READING_WRITING_SCORED_JOURNEY_VALIDATED"


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _read(path: Path, errors: list[str], code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{code}_unreadable:{exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{code}_not_object")
        return {}
    return value


def _static_contract(secure_root: Path, errors: list[str]) -> None:
    required = {
        "index.html": (
            "A1FS A1／A1+ 學習工作台",
            "本次學習完成條件",
            "最新作答皆通過或經人工核准",
            "完成本次學習",
            "/auth.js",
            "/app.js",
        ),
        "app.js": (
            "completion_gate",
            "latest_outcome",
            "attempt_count",
            "PENDING_HUMAN_REVIEW",
            "HUMAN_APPROVE",
            "complete.disabled=!gate.completion_allowed",
            "value.active_scored_journey",
        ),
        "styles.css": (".gate-panel", ".gate-grid", ".gate-item", ".gate-ready", ".gate-blocked"),
        "auth.js": ("/auth/session", "X-CSRF-Token", "/auth/logout"),
        "login.html": ("A1FS 安全登入", "login-form"),
    }
    for name, tokens in required.items():
        try:
            text = (secure_root / name).read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"s15_static_missing:{name}:{exc}")
            continue
        for token in tokens:
            if token not in text:
                errors.append(f"s15_static_token_missing:{name}:{token}")
        if name == "app.js":
            for token in ("innerHTML", "eval(", "text(progress, JSON.stringify"):
                if token in text:
                    errors.append(f"s15_static_forbidden_token:{name}:{token}")


def _launch_contract(outputs: Mapping[str, Any], errors: list[str]) -> None:
    start = Path(str(outputs.get("start_script_path") or ""))
    stop = Path(str(outputs.get("stop_script_path") or ""))
    status = Path(str(outputs.get("status_script_path") or ""))
    contract_path = Path(str(outputs.get("launch_contract_path") or ""))
    for name, path in (("start", start), ("stop", stop), ("status", status), ("contract", contract_path)):
        if not path.is_file():
            errors.append(f"s15_launch_output_missing:{name}")
    try:
        start_text = start.read_text(encoding="utf-8")
        stop_text = stop.read_text(encoding="utf-8")
        status_text = status.read_text(encoding="utf-8")
    except OSError:
        return
    module = "build_a1fs_online_v1_s15_reading_writing_scored_journey_completion_gate"
    if module not in start_text:
        errors.append("s15_start_module_binding_invalid")
    for secret in (s15.CANARY_PASSWORD, s15.CANARY_SESSION_SECRET):
        if secret in start_text or secret in stop_text or secret in status_text:
            errors.append("s15_launcher_secret_embedded")
    if "PID_OWNERSHIP_MISMATCH" not in stop_text or "PORT_OWNERSHIP_INVALID" not in status_text:
        errors.append("s15_launcher_lifecycle_contract_invalid")
    contract = _read(contract_path, errors, "s15_launch_contract")
    expected = {
        "host": "127.0.0.1",
        "port": 8765,
        "authentication_required": True,
        "secret_values_embedded": False,
        "reading_writing_completion_gate_enabled": True,
        "external_network_binding_allowed": False,
        "cloudflare_enabled": False,
        "audio_enabled": False,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            errors.append(f"s15_launch_contract_invalid:{key}")


def _acceptance_database(path: Path, summary: Mapping[str, Any], errors: list[str]) -> None:
    if not path.is_file():
        errors.append("s15_acceptance_database_missing")
        return
    try:
        with sqlite3.connect(path) as connection:
            connection.row_factory = sqlite3.Row
            sessions = connection.execute(
                """SELECT session_id,skill,session_state FROM learning_sessions
                   WHERE session_id IN (?,?) ORDER BY session_id""",
                (s15.CANARY_READING_SESSION_ID, s15.CANARY_WRITING_SESSION_ID),
            ).fetchall()
            if len(sessions) != 2 or any(row["session_state"] != "COMPLETED" for row in sessions):
                errors.append("s15_acceptance_scored_sessions_not_completed")
            if {str(row["skill"]) for row in sessions} != {"READING", "WRITING"}:
                errors.append("s15_acceptance_scored_session_skill_set_invalid")

            reading_attempts = connection.execute(
                """SELECT asset_key,COUNT(*) AS total,MAX(attempt_sequence) AS max_sequence
                   FROM response_attempts WHERE session_id=? GROUP BY asset_key ORDER BY asset_key""",
                (s15.CANARY_READING_SESSION_ID,),
            ).fetchall()
            if len(reading_attempts) != 4 or sorted(int(row["total"]) for row in reading_attempts) != [1, 1, 1, 2]:
                errors.append("s15_reading_retry_attempt_history_invalid")
            latest_reading = connection.execute(
                """SELECT a.asset_key,r.outcome FROM response_attempts a
                   JOIN scoring_results r USING(attempt_id)
                   JOIN (SELECT asset_key,MAX(attempt_sequence) AS seq FROM response_attempts
                         WHERE session_id=? GROUP BY asset_key) latest
                     ON latest.asset_key=a.asset_key AND latest.seq=a.attempt_sequence
                   WHERE a.session_id=? ORDER BY a.asset_key""",
                (s15.CANARY_READING_SESSION_ID, s15.CANARY_READING_SESSION_ID),
            ).fetchall()
            if len(latest_reading) != 4 or any(row["outcome"] != "AUTO_PASS" for row in latest_reading):
                errors.append("s15_reading_latest_attempt_gate_invalid")

            latest_writing = connection.execute(
                """SELECT a.asset_key,r.scoring_mode,r.outcome FROM response_attempts a
                   JOIN scoring_results r USING(attempt_id)
                   JOIN (SELECT asset_key,MAX(attempt_sequence) AS seq FROM response_attempts
                         WHERE session_id=? GROUP BY asset_key) latest
                     ON latest.asset_key=a.asset_key AND latest.seq=a.attempt_sequence
                   WHERE a.session_id=? ORDER BY a.asset_key""",
                (s15.CANARY_WRITING_SESSION_ID, s15.CANARY_WRITING_SESSION_ID),
            ).fetchall()
            if len(latest_writing) != 4 or any(
                row["outcome"] not in s15.PASSING_OUTCOMES for row in latest_writing
            ):
                errors.append("s15_writing_latest_attempt_gate_invalid")
            approvals = sum(row["outcome"] == "HUMAN_APPROVE" for row in latest_writing)
            if approvals < 1 or approvals != int(summary.get("human_approved_attempt_count") or 0):
                errors.append("s15_writing_human_review_approval_invalid")
            pending = int(connection.execute(
                """SELECT COUNT(*) FROM scoring_results r JOIN response_attempts a USING(attempt_id)
                   WHERE a.session_id=? AND r.outcome='PENDING_HUMAN_REVIEW'""",
                (s15.CANARY_WRITING_SESSION_ID,),
            ).fetchone()[0])
            if pending != 0:
                errors.append("s15_writing_pending_review_not_resolved")
    except sqlite3.Error as exc:
        errors.append(f"s15_acceptance_database_unreadable:{exc}")


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s14_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    output_root = Path(output_root).resolve()
    s14_path = Path(s14_path).resolve()

    if (
        receipt.get("task_id") != s15.TASK_ID
        or receipt.get("schema_version") != s15.SCHEMA_VERSION
        or receipt.get("validation_status") != s15.PASS_STATUS
        or receipt.get("product_status") != s15.PRODUCT_STATUS
    ):
        errors.append("s15_receipt_identity_invalid")
    core_value = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s15.digest(core_value):
        errors.append("s15_receipt_digest_invalid")
    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s15.digest(safe_core):
        errors.append("s15_safe_digest_invalid")
    try:
        s15.safe_scan(safe_report)
    except s15.s14.LearnerFacingSemanticsError as exc:
        errors.append(str(exc))

    outputs = receipt.get("runtime_outputs", {})
    root = Path(str(outputs.get("root") or "")).resolve()
    source_s14 = Path(str(outputs.get("source_s14_receipt_path") or "")).resolve()
    production_database = Path(str(outputs.get("source_database_path") or "")).resolve()
    acceptance_database = Path(str(outputs.get("acceptance_database_path") or "")).resolve()
    learner_static = Path(str(outputs.get("learner_static_root") or "")).resolve()
    secure_static = Path(str(outputs.get("secure_static_root") or "")).resolve()
    if root != (output_root / "scored_journey_completion_gate").resolve():
        errors.append("s15_runtime_root_noncanonical")
    for name, path in (
        ("acceptance_database", acceptance_database),
        ("learner_static", learner_static),
        ("secure_static", secure_static),
        ("bundle_root", Path(str(outputs.get("bundle_root") or ""))),
    ):
        if not _inside(path, output_root):
            errors.append(f"s15_output_outside_authority_root:{name}")
    if source_s14 != s14_path:
        errors.append("s15_source_s14_binding_invalid")

    try:
        _, expected_database, _, bundles, sequence = s15._verify_s14(s14_path)
    except (s15.ScoredJourneyError, OSError, sqlite3.Error, ValueError) as exc:
        errors.append(f"s15_source_verification_failed:{exc}")
        expected_database = Path(".")
        bundles = {}
        sequence = {}
    if production_database != expected_database:
        errors.append("s15_database_binding_invalid")
    if bundles and sequence:
        try:
            app = s15._app(production_database, bundles, sequence)
            bootstrap = app.bootstrap()
        except Exception as exc:
            errors.append(f"s15_runtime_rebuild_failed:{exc}")
            bootstrap = {}
        if len(bootstrap.get("units", [])) != 24:
            errors.append("s15_bootstrap_unit_count_invalid")
        lanes = [lane for unit in bootstrap.get("units", []) for lane in unit.get("lanes", [])]
        if len(lanes) != 72 or sum(int(lane.get("asset_count") or 0) for lane in lanes) != 264:
            errors.append("s15_bootstrap_runtime_denominator_invalid")
        scored_lanes = [lane for lane in lanes if lane.get("skill") in s15.SCORED_SKILLS]
        if len(scored_lanes) != 48 or any(lane.get("completion_gate_required") is not True for lane in scored_lanes):
            errors.append("s15_bootstrap_scored_lane_gate_invalid")
        speaking = [lane for lane in lanes if lane.get("skill") == "SPEAKING"]
        if len(speaking) != 24 or any(lane.get("completion_gate_required") is not False for lane in speaking):
            errors.append("s15_bootstrap_speaking_boundary_invalid")

    summary = receipt.get("scored_journey_summary", {})
    exact_summary = {
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "reading_required_response_count": 4,
        "writing_required_response_count": 4,
        "reading_scored_journey_pass": True,
        "writing_scored_or_human_reviewed_journey_pass": True,
        "deterministic_auto_scoring_connected": True,
        "human_review_gate_connected": True,
        "retry_attempt_history_connected": True,
        "incomplete_session_blocked": True,
        "pending_human_review_blocked": True,
        "completion_after_pass_or_approval": True,
        "completed_scored_session_count": 2,
        "reading_retry_attempt_count": 2,
        "human_approved_attempt_present": True,
        "authenticated_http_acceptance": True,
        "authenticated_runtime_reused": True,
        "speaking_recording_enabled": False,
        "listening_lesson_count": 0,
        "audio_asset_count": 0,
        "unit_completion_claimed": False,
        "mastery_claimed": False,
        "production_database_unchanged": True,
    }
    for key, value in exact_summary.items():
        if summary.get(key) != value:
            errors.append(f"s15_scored_journey_summary_invalid:{key}")
    if not isinstance(summary.get("human_approved_attempt_count"), int) or summary.get("human_approved_attempt_count", 0) < 1:
        errors.append("s15_human_approved_attempt_count_invalid")

    _acceptance_database(acceptance_database, summary, errors)
    _static_contract(secure_static, errors)
    _launch_contract(outputs, errors)

    production = receipt.get("production_safety", {})
    try:
        actual_sha = s15.file_digest(production_database)
    except OSError as exc:
        errors.append(f"s15_database_digest_unreadable:{exc}")
        actual_sha = ""
    if (
        production.get("production_database_sha256_before") != actual_sha
        or production.get("production_database_sha256_after") != actual_sha
        or production.get("production_database_unchanged") is not True
        or production.get("acceptance_used_isolated_database_clone") is not True
        or production.get("learner_progress_mutated_by_acceptance") is not False
        or production.get("auth_state_reused_from_s14_source") is not True
    ):
        errors.append("s15_production_safety_invalid")

    expected_capability = {
        "s14_learner_surface_reused": True,
        "s09_twentyfour_unit_runtime_reused": True,
        "m3_session_progress_authority_reused": True,
        "m6_response_scoring_authority_reused": True,
        "m6_attempt_history_reused": True,
        "m6_human_review_authority_reused": True,
        "reading_writing_completion_gate_enabled": True,
        "parallel_curriculum_created": False,
        "parallel_learner_state_engine_created": False,
        "parallel_scoring_engine_created": False,
        "parallel_mastery_engine_created": False,
        "unit_completion_claim_enabled": False,
        "mastery_write_enabled": False,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "a2_unlocked": False,
        "cloudflare_enabled": False,
    }
    if receipt.get("capability_contract") != expected_capability:
        errors.append("s15_capability_contract_invalid")
    if receipt.get("stop_reason") != "NONE" or receipt.get("next_short_step") != s15.NEXT_SHORT_STEP:
        errors.append("s15_transition_contract_invalid")

    return {
        "task_id": s15.TASK_ID,
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S15_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--s14", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = _read(args.receipt, [], "receipt")
    report = _read(args.report, [], "report")
    result = validate_outputs(
        receipt=receipt,
        safe_report=report,
        output_root=args.receipt.parent,
        s14_path=args.s14,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["error_count"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
