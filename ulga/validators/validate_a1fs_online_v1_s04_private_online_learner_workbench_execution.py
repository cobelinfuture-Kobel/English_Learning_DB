#!/usr/bin/env python3
"""Independent validator for A1FS Online V1 S04 private workbench execution."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_online_v1_s03_unified_learner_runtime as s03
from ulga.builders import build_a1fs_online_v1_s04_private_online_learner_workbench_execution as s04

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates private localhost execution, learner-safe serialization, SQLite evidence, and no-audio boundaries only."
)

VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_S04_PRIVATE_WORKBENCH_VALIDATED"
FORBIDDEN_BUNDLE_KEYS = {
    "answer_contract", "private_scoring_contract", "accepted_texts", "accepted_sequence",
    "correct_answer", "correct_token_sequence", "rubric",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else _canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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


def _walk_keys(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            result.add(str(key).casefold())
            result.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_walk_keys(child))
    return result


def _database_counts(path: Path, errors: list[str]) -> dict[str, int]:
    if not path.is_file():
        errors.append("workbench_database_missing")
        return {}
    queries = {
        "profile_count": "SELECT COUNT(*) FROM learner_profiles",
        "session_count": "SELECT COUNT(*) FROM learning_sessions",
        "completed_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE session_state='COMPLETED'",
        "response_contract_count": "SELECT COUNT(*) FROM response_contracts",
        "response_attempt_count": "SELECT COUNT(*) FROM response_attempts",
        "scoring_result_count": "SELECT COUNT(*) FROM scoring_results",
        "auto_fail_count": "SELECT COUNT(*) FROM scoring_results WHERE outcome='AUTO_FAIL'",
        "speaking_attempt_count": "SELECT COUNT(*) FROM response_attempts a JOIN response_contracts c USING(asset_key) WHERE c.skill='SPEAKING'",
        "listening_asset_count": "SELECT COUNT(*) FROM lesson_assets a JOIN lesson_catalog l USING(lesson_id) WHERE l.skill='LISTENING'",
    }
    try:
        with sqlite3.connect(path) as connection:
            counts = {key: int(connection.execute(sql).fetchone()[0]) for key, sql in queries.items()}
            rows = connection.execute(
                "SELECT session_state FROM learning_sessions WHERE session_id=?",
                (s04.CANARY_SESSION_ID,),
            ).fetchall()
            if rows != [("COMPLETED",)]:
                errors.append("s04_canary_session_not_completed")
            attempt = connection.execute(
                "SELECT outcome,score FROM scoring_results WHERE attempt_id=?",
                (s04.CANARY_ATTEMPT_ID,),
            ).fetchone()
            if attempt != ("AUTO_FAIL", 0.0):
                errors.append("s04_canary_scoring_result_invalid")
            return counts
    except sqlite3.Error as exc:
        errors.append(f"workbench_database_invalid:{exc}")
        return {}


def _validate_static(static_root: Path, errors: list[str]) -> None:
    required = {
        "index.html": ("Content-Security-Policy", "app.js", "styles.css", "aria-live"),
        "app.js": ("fetch(", "textContent", "replaceChildren"),
        "styles.css": ("body", ".card"),
    }
    for name, tokens in required.items():
        path = static_root / name
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"workbench_static_missing:{name}:{exc}")
            continue
        for token in tokens:
            if token not in text:
                errors.append(f"workbench_static_token_missing:{name}:{token}")
        if name == "app.js" and ("innerHTML" in text or "eval(" in text):
            errors.append("workbench_unsafe_dom_rendering_present")


def _validate_bundles(ui_root: Path, errors: list[str]) -> int:
    total = 0
    for skill, expected in (("reading", 4), ("writing", 4), ("speaking", 3)):
        bundle = _read(ui_root / skill / "lesson.private.json", errors, f"m5_bundle_{skill}")
        assets = bundle.get("assets")
        if not isinstance(assets, list) or len(assets) != expected:
            errors.append(f"m5_bundle_asset_count_invalid:{skill}")
            continue
        total += len(assets)
        keys = _walk_keys(bundle)
        leaked = sorted(keys & FORBIDDEN_BUNDLE_KEYS)
        if leaked:
            errors.append(f"m5_bundle_private_scoring_leak:{skill}:{','.join(leaked)}")
        capabilities = bundle.get("capabilities", {})
        if capabilities.get("audio_playback_enabled") is not False:
            errors.append(f"m5_audio_capability_invalid:{skill}")
        if capabilities.get("speaking_recording_enabled") is not False:
            errors.append(f"m5_speaking_recording_capability_invalid:{skill}")
    return total


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s03_receipt_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    output_root = Path(output_root).resolve()
    s03_receipt = _read(Path(s03_receipt_path), errors, "s03_receipt")
    if s03_receipt.get("task_id") != s03.TASK_ID or s03_receipt.get("validation_status") != s03.PASS_STATUS:
        errors.append("s03_source_status_invalid")
    if receipt.get("task_id") != s04.TASK_ID or receipt.get("schema_version") != s04.SCHEMA_VERSION:
        errors.append("s04_receipt_identity_invalid")
    if receipt.get("validation_status") != s04.PASS_STATUS:
        errors.append("s04_receipt_status_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s04.digest(core):
        errors.append("s04_receipt_digest_invalid")
    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s04.digest(safe_core):
        errors.append("s04_safe_digest_invalid")
    if safe_report.get("validation_status") != s04.PASS_STATUS:
        errors.append("s04_safe_status_invalid")
    try:
        s04.safe_scan(safe_report)
    except s04.WorkbenchError as exc:
        errors.append(str(exc))

    outputs = receipt.get("workbench_outputs", {})
    root = Path(str(outputs.get("root") or ""))
    database = Path(str(outputs.get("database_path") or ""))
    static_root = Path(str(outputs.get("static_root") or ""))
    ui_root = Path(str(outputs.get("ui_root") or ""))
    for name, path in (("root", root), ("database", database), ("static", static_root), ("ui", ui_root)):
        if not _inside(path, output_root):
            errors.append(f"workbench_output_outside_authority_root:{name}")
    if root.resolve() != (output_root / "workbench").resolve():
        errors.append("workbench_root_noncanonical")

    _validate_static(static_root, errors)
    learner_visible_asset_count = _validate_bundles(ui_root, errors)
    counts = _database_counts(database, errors)
    expected_counts = {
        "profile_count": 2,
        "session_count": 4,
        "completed_session_count": 4,
        "response_contract_count": 11,
        "response_attempt_count": 1,
        "scoring_result_count": 1,
        "auto_fail_count": 1,
        "speaking_attempt_count": 0,
        "listening_asset_count": 0,
    }
    for key, value in expected_counts.items():
        if counts.get(key) != value:
            errors.append(f"workbench_database_count_invalid:{key}:{counts.get(key)}:{value}")

    summary = receipt.get("execution_summary", {})
    expected_summary = {
        "lane_count": 3,
        "learner_visible_asset_count": 11,
        "http_loopback_canary_count": 1,
        "synthetic_response_attempt_count": 1,
        "synthetic_scoring_result_count": 1,
        "synthetic_auto_fail_count": 1,
        "speaking_attempt_count": 0,
        "listening_item_count": 0,
        "audio_runtime_asset_count": 0,
    }
    if summary != expected_summary:
        errors.append("s04_execution_summary_invalid")
    if learner_visible_asset_count != 11:
        errors.append("s04_learner_visible_asset_count_invalid")
    canary = receipt.get("http_canary", {})
    if (
        canary.get("loopback_transport_executed") is not True
        or canary.get("bootstrap_lane_count") != 3
        or canary.get("bootstrap_asset_count") != 11
        or canary.get("attempt_outcome") != "AUTO_FAIL"
        or canary.get("attempt_score") != 0.0
        or canary.get("session_state") != "COMPLETED"
    ):
        errors.append("s04_http_canary_invalid")
    capability = receipt.get("capability_contract", {})
    expected_capability = {
        "localhost_workbench_executable": True,
        "m3_session_state_engine_reused": True,
        "m5_learner_bundle_reused": True,
        "m6_response_scoring_engine_reused": True,
        "synthetic_response_submission_executed": True,
        "parallel_runtime_engine_created": False,
        "public_network_binding_allowed": False,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
    }
    if capability != expected_capability:
        errors.append("s04_capability_contract_invalid")
    boundaries = receipt.get("claim_boundaries", {})
    for key in (
        "real_learner_attempt_claimed", "learner_mastery_claimed", "retention_confirmed",
        "public_online_delivery_claimed", "audio_complete", "speaking_recording_complete", "a2_unlocked",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"s04_claim_boundary_invalid:{key}")
    if boundaries.get("synthetic_canary_only") is not True:
        errors.append("s04_synthetic_canary_boundary_invalid")
    if receipt.get("product_status") != "PRIVATE_LOCALHOST_WORKBENCH_EXECUTABLE_NOT_PUBLIC":
        errors.append("s04_product_status_invalid")
    if receipt.get("stop_reason") != "NONE" or receipt.get("next_short_step") != s04.NEXT_SHORT_STEP:
        errors.append("s04_continuation_contract_invalid")

    return {
        "task_id": s04.TASK_ID,
        "schema_version": s04.SCHEMA_VERSION,
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S04_PRIVATE_WORKBENCH",
        "error_count": len(errors),
        "errors": errors,
        "validated_counts": counts,
        "stop_reason": "NONE" if not errors else "S04_WORKBENCH_VALIDATION_FAILED",
        "next_short_step": s04.NEXT_SHORT_STEP if not errors else s04.TASK_ID,
    }
