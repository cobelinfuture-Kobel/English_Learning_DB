#!/usr/bin/env python3
"""Independent validation for A1FS Online V1 S03 unified no-audio runtime."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_online_v1_s03_unified_learner_runtime_integration as s03
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m5_four_skill_renderer_learner_ui as m5
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates runtime identities, counts, hashes, SQLite state, and no-audio boundaries only."
)

VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_S03_UNIFIED_LEARNER_RUNTIME_VALIDATED"
EXPECTED_SKILLS = ("READING", "WRITING", "SPEAKING")
EXPECTED_ASSET_COUNTS = {"READING": 4, "WRITING": 4, "SPEAKING": 3}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else _canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _safe_scan(value: Any, errors: list[str]) -> None:
    forbidden = {key.casefold() for key in s03.FORBIDDEN_SAFE_KEYS}

    def walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden:
                    errors.append(f"safe_private_content_key:{path}.{key}")
                walk(child, f"{path}.{key}")
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{path}[{index}]")

    walk(value, "$")


def _validate_receipt_identity(
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    s02_artifact: Mapping[str, Any],
    m03_artifact: Mapping[str, Any],
    errors: list[str],
) -> None:
    if receipt.get("task_id") != s03.TASK_ID:
        errors.append("receipt_task_id_invalid")
    if receipt.get("schema_version") != s03.SCHEMA_VERSION:
        errors.append("receipt_schema_version_invalid")
    if receipt.get("validation_status") != s03.PASS_STATUS:
        errors.append("receipt_status_invalid")
    if receipt.get("stop_reason") != "NONE":
        errors.append("receipt_stop_reason_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s03.digest(core):
        errors.append("receipt_artifact_digest_invalid")
    identity = receipt.get("source_identity", {})
    if identity.get("s02_task_id") != s03.s02.TASK_ID or identity.get("s02_sha256") != s03.digest(s02_artifact):
        errors.append("receipt_s02_binding_invalid")
    if identity.get("m03_task_id") != s03.m03.TASK_ID or identity.get("m03_sha256") != s03.digest(m03_artifact):
        errors.append("receipt_m03_binding_invalid")
    selected = receipt.get("selected_unit", {})
    expected_selected = {
        "learning_unit_id": s02_artifact.get("selected_unit", {}).get("learning_unit_id"),
        "grammar_unit_id": s02_artifact.get("selected_unit", {}).get("grammar_unit_id"),
        "sequence_index": s02_artifact.get("selected_unit", {}).get("sequence_index"),
    }
    if selected != expected_selected:
        errors.append("receipt_selected_unit_binding_invalid")
    if safe_report.get("task_id") != s03.TASK_ID or safe_report.get("validation_status") != s03.PASS_STATUS:
        errors.append("safe_report_identity_invalid")
    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s03.digest(safe_core):
        errors.append("safe_report_digest_invalid")
    for key in (
        "program_id", "schema_version", "validation_status", "release_profile", "selected_unit",
        "runtime_summary", "capability_contract", "product_status", "stop_reason", "next_short_step",
    ):
        if safe_report.get(key) != receipt.get(key):
            errors.append(f"safe_report_receipt_mismatch:{key}")
    _safe_scan(safe_report, errors)


def _validate_consumer(
    consumer: Mapping[str, Any],
    receipt: Mapping[str, Any],
    s02_artifact: Mapping[str, Any],
    errors: list[str],
) -> None:
    if (
        consumer.get("task_id") != m2.TASK_ID
        or consumer.get("schema_version") != m2.SCHEMA_VERSION
        or consumer.get("validation_status") != m2.STATUS
        or consumer.get("errors") != []
    ):
        errors.append("runtime_consumer_m2_compatibility_invalid")
    if consumer.get("access_contract", {}).get("a2_payload_query_allowed") is not False:
        errors.append("runtime_consumer_a2_payload_not_locked")
    projection = consumer.get("s03_runtime_projection", {})
    if projection.get("task_id") != s03.TASK_ID:
        errors.append("runtime_consumer_s03_projection_missing")
    if projection.get("source_s02_sha256") != s03.digest(s02_artifact):
        errors.append("runtime_consumer_s02_binding_invalid")
    if projection.get("m4_new_curriculum_selection_performed") is not False:
        errors.append("runtime_consumer_parallel_selection_claimed")
    if projection.get("runtime_engine_authorities") != {
        "session_state": m3.TASK_ID,
        "learner_renderer": m5.TASK_ID,
        "response_scoring": m6.TASK_ID,
    }:
        errors.append("runtime_consumer_engine_authority_invalid")

    lessons = consumer.get("lesson_catalog")
    assets = consumer.get("asset_records")
    if not isinstance(lessons, list) or len(lessons) != 3:
        errors.append("runtime_consumer_lesson_count_not_3")
        lessons = []
    if not isinstance(assets, list) or len(assets) != 11:
        errors.append("runtime_consumer_asset_count_not_11")
        assets = []
    lesson_index = {str(row.get("lesson_id") or ""): row for row in lessons if isinstance(row, Mapping)}
    asset_index = {str(row.get("asset_key") or ""): row for row in assets if isinstance(row, Mapping)}
    if len(lesson_index) != len(lessons):
        errors.append("runtime_consumer_lesson_identity_invalid")
    if len(asset_index) != len(assets):
        errors.append("runtime_consumer_asset_identity_invalid")
    skill_lessons = {str(row.get("skill") or ""): row for row in lessons if isinstance(row, Mapping)}
    if set(skill_lessons) != set(EXPECTED_SKILLS):
        errors.append("runtime_consumer_skill_set_invalid")
    admitted_ids = {
        str(item_id)
        for lane in s02_artifact.get("selected_unit", {}).get("admitted_lanes", {}).values()
        for item_id in lane.get("item_ids", [])
        if isinstance(lane, Mapping)
    }
    runtime_source_ids: set[str] = set()
    for skill, expected_count in EXPECTED_ASSET_COUNTS.items():
        lesson = skill_lessons.get(skill, {})
        keys = lesson.get("asset_keys", []) if isinstance(lesson, Mapping) else []
        if len(keys) != expected_count or any(key not in asset_index for key in keys):
            errors.append(f"runtime_consumer_asset_bundle_invalid:{skill}")
        if lesson.get("level") not in {"A1", "A1+"}:
            errors.append(f"runtime_consumer_lesson_level_invalid:{skill}")
        if lesson.get("runtime_projection", {}).get("new_curriculum_unit_created") is not False:
            errors.append(f"runtime_consumer_new_unit_claimed:{skill}")
        for key in keys:
            asset = asset_index.get(str(key), {})
            if asset.get("skill") != skill or asset.get("lesson_id") != lesson.get("lesson_id"):
                errors.append(f"runtime_consumer_asset_lesson_binding_invalid:{key}")
                continue
            payload = asset.get("payload")
            if not isinstance(payload, Mapping):
                errors.append(f"runtime_consumer_asset_payload_invalid:{key}")
                continue
            source_id = str(payload.get("source_binding", {}).get("shared_item_id") or "")
            if not source_id:
                errors.append(f"runtime_consumer_source_item_missing:{key}")
            runtime_source_ids.add(source_id)
            validation = payload.get("stimulus_validation", {})
            if validation.get("answerability_pass") is not True or validation.get("errors") != []:
                errors.append(f"runtime_consumer_stimulus_not_answerable:{key}")
            if skill == "SPEAKING":
                if payload.get("response_capture_enabled") is not False:
                    errors.append(f"speaking_capture_enabled:{key}")
                if payload.get("recording_capture_required") is not False:
                    errors.append(f"speaking_recording_required:{key}")
                if payload.get("delivery_mode") != "ORAL_PRACTICE_CARD_NO_CAPTURE":
                    errors.append(f"speaking_delivery_mode_invalid:{key}")
            elif payload.get("response_capture_enabled") is not True:
                errors.append(f"text_capture_not_enabled:{key}")
    if runtime_source_ids != admitted_ids:
        errors.append("runtime_consumer_admitted_item_identity_mismatch")
    if any(row.get("skill") == "LISTENING" for row in assets):
        errors.append("listening_runtime_asset_present")
    if receipt.get("runtime_summary", {}).get("runtime_asset_count") != len(assets):
        errors.append("receipt_consumer_asset_count_mismatch")


def _validate_database(
    database_path: Path,
    consumer_path: Path,
    consumer: Mapping[str, Any],
    receipt: Mapping[str, Any],
    errors: list[str],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not database_path.is_file():
        errors.append("runtime_database_missing")
        return counts
    try:
        with sqlite3.connect(database_path) as connection:
            connection.row_factory = sqlite3.Row
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            foreign = list(connection.execute("PRAGMA foreign_key_check"))
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
            queries = {
                "profile_count": "SELECT COUNT(*) FROM learner_profiles",
                "session_count": "SELECT COUNT(*) FROM learning_sessions",
                "completed_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE session_state='COMPLETED'",
                "active_session_count": "SELECT COUNT(*) FROM learning_sessions WHERE session_state='ACTIVE'",
                "lesson_count": "SELECT COUNT(*) FROM lesson_catalog",
                "asset_count": "SELECT COUNT(*) FROM lesson_assets",
                "state_event_count": "SELECT COUNT(*) FROM state_events",
                "profile_created_event_count": "SELECT COUNT(*) FROM state_events WHERE event_type='PROFILE_CREATED'",
                "session_started_event_count": "SELECT COUNT(*) FROM state_events WHERE event_type='SESSION_STARTED'",
                "asset_exposed_event_count": "SELECT COUNT(*) FROM state_events WHERE event_type='ASSET_EXPOSED'",
                "session_ended_event_count": "SELECT COUNT(*) FROM state_events WHERE event_type='SESSION_ENDED'",
                "response_contract_count": "SELECT COUNT(*) FROM response_contracts",
                "capture_enabled_contract_count": "SELECT COUNT(*) FROM response_contracts WHERE capture_enabled=1",
                "speaking_capture_enabled_count": "SELECT COUNT(*) FROM response_contracts WHERE skill='SPEAKING' AND capture_enabled=1",
                "response_attempt_count": "SELECT COUNT(*) FROM response_attempts",
                "scoring_result_count": "SELECT COUNT(*) FROM scoring_results",
            }
            counts = {name: int(connection.execute(sql).fetchone()[0]) for name, sql in queries.items()}
            sessions = list(connection.execute("SELECT skill,session_state,COUNT(*) count FROM learning_sessions GROUP BY skill,session_state"))
            progress = list(connection.execute("SELECT skill,exposure_count,progress_state FROM lesson_progress ORDER BY skill"))
    except sqlite3.Error as exc:
        errors.append(f"runtime_database_unreadable:{exc}")
        return counts
    if integrity != "ok" or foreign:
        errors.append("runtime_database_integrity_invalid")
    expected_consumer_sha = hashlib.sha256(consumer_path.read_bytes()).hexdigest() if consumer_path.is_file() else None
    if metadata.get("validation_status") != m3.STATUS or metadata.get("consumer_sha256") != expected_consumer_sha:
        errors.append("runtime_database_m3_binding_invalid")
    if metadata.get("m6_validation_status") != m6.STATUS:
        errors.append("runtime_database_m6_not_initialized")
    expected_counts = {
        "profile_count": 1,
        "session_count": 3,
        "completed_session_count": 3,
        "active_session_count": 0,
        "lesson_count": 3,
        "asset_count": 11,
        "state_event_count": 18,
        "profile_created_event_count": 1,
        "session_started_event_count": 3,
        "asset_exposed_event_count": 11,
        "session_ended_event_count": 3,
        "response_contract_count": 11,
        "capture_enabled_contract_count": 8,
        "speaking_capture_enabled_count": 0,
        "response_attempt_count": 0,
        "scoring_result_count": 0,
    }
    for key, expected in expected_counts.items():
        if counts.get(key) != expected:
            errors.append(f"runtime_database_count_invalid:{key}:{counts.get(key)}:{expected}")
    if {(row["skill"], row["session_state"], row["count"]) for row in sessions} != {
        ("READING", "COMPLETED", 1),
        ("WRITING", "COMPLETED", 1),
        ("SPEAKING", "COMPLETED", 1),
    }:
        errors.append("runtime_database_session_lane_state_invalid")
    if {(row["skill"], row["exposure_count"], row["progress_state"]) for row in progress} != {
        ("READING", 4, "PAUSED"),
        ("WRITING", 4, "PAUSED"),
        ("SPEAKING", 3, "PAUSED"),
    }:
        errors.append("runtime_database_progress_exposure_invalid")
    summary = receipt.get("runtime_summary", {})
    summary_map = {
        "m3_profile_count": "profile_count",
        "m3_session_count": "session_count",
        "m3_completed_session_count": "completed_session_count",
        "m3_exposure_event_count": "asset_exposed_event_count",
        "m6_response_contract_count": "response_contract_count",
        "m6_capture_enabled_contract_count": "capture_enabled_contract_count",
        "speaking_capture_enabled_count": "speaking_capture_enabled_count",
    }
    for summary_key, count_key in summary_map.items():
        if summary.get(summary_key) != counts.get(count_key):
            errors.append(f"receipt_database_count_mismatch:{summary_key}")
    if receipt.get("runtime_summary", {}).get("listening_runtime_item_count") != 0:
        errors.append("receipt_listening_runtime_count_not_zero")
    if receipt.get("runtime_summary", {}).get("audio_runtime_asset_count") != 0:
        errors.append("receipt_audio_runtime_count_not_zero")
    return counts


def _validate_ui(
    runtime_root: Path,
    consumer: Mapping[str, Any],
    receipt: Mapping[str, Any],
    errors: list[str],
) -> None:
    lessons = {str(row.get("skill") or ""): row for row in consumer.get("lesson_catalog", []) if isinstance(row, Mapping)}
    lane_receipts = {str(row.get("skill") or ""): row for row in receipt.get("lane_receipts", []) if isinstance(row, Mapping)}
    if set(lane_receipts) != set(EXPECTED_SKILLS):
        errors.append("lane_receipt_skill_set_invalid")
    for skill in EXPECTED_SKILLS:
        ui_root = runtime_root / "ui" / skill.casefold()
        required = ("lesson.private.json", "manifest.json", "index.html", "styles.css", "app.js")
        if any(not (ui_root / name).is_file() for name in required):
            errors.append(f"m5_ui_bundle_incomplete:{skill}")
            continue
        manifest = _read(ui_root / "manifest.json", errors, f"m5_manifest:{skill}")
        bundle = _read(ui_root / "lesson.private.json", errors, f"m5_bundle:{skill}")
        lesson = lessons.get(skill, {})
        expected_count = EXPECTED_ASSET_COUNTS[skill]
        if (
            manifest.get("validation_status") != m5.STATUS
            or manifest.get("lesson_id") != lesson.get("lesson_id")
            or manifest.get("skill") != skill
            or manifest.get("asset_count") != expected_count
            or manifest.get("private_localhost_only") is not True
            or manifest.get("learner_release_approved") is not False
        ):
            errors.append(f"m5_manifest_contract_invalid:{skill}")
        if (
            bundle.get("validation_status") != m5.STATUS
            or bundle.get("lesson", {}).get("lesson_id") != lesson.get("lesson_id")
            or len(bundle.get("assets", [])) != expected_count
            or bundle.get("capabilities", {}).get("audio_playback_enabled") is not False
            or bundle.get("capabilities", {}).get("speaking_recording_enabled") is not False
        ):
            errors.append(f"m5_bundle_contract_invalid:{skill}")
        lane = lane_receipts.get(skill, {})
        if lane.get("session_state") != "COMPLETED" or lane.get("asset_count") != expected_count:
            errors.append(f"lane_receipt_session_invalid:{skill}")
        if lane.get("m5_asset_count") != expected_count:
            errors.append(f"lane_receipt_m5_count_invalid:{skill}")
        expected_capture = expected_count if skill in {"READING", "WRITING"} else 0
        if lane.get("m6_capture_contract_count") != expected_capture:
            errors.append(f"lane_receipt_m6_capture_count_invalid:{skill}")


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s02_artifact: Mapping[str, Any],
    m03_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    output_root = Path(output_root).resolve()
    runtime_root = output_root / "runtime"
    _validate_receipt_identity(receipt, safe_report, s02_artifact, m03_artifact, errors)
    outputs = receipt.get("runtime_outputs", {})
    consumer_path = Path(str(outputs.get("consumer_path") or ""))
    database_path = Path(str(outputs.get("database_path") or ""))
    ui_root = Path(str(outputs.get("ui_root") or ""))
    if not all(_inside(path, output_root) for path in (consumer_path, database_path, ui_root)):
        errors.append("runtime_output_path_outside_authority_root")
    if consumer_path.resolve() != (runtime_root / "unified_runtime_consumer.private.json").resolve():
        errors.append("runtime_consumer_path_noncanonical")
    if database_path.resolve() != (runtime_root / "learner_state.sqlite3").resolve():
        errors.append("runtime_database_path_noncanonical")
    if ui_root.resolve() != (runtime_root / "ui").resolve():
        errors.append("runtime_ui_path_noncanonical")
    consumer = _read(consumer_path, errors, "runtime_consumer")
    if consumer:
        _validate_consumer(consumer, receipt, s02_artifact, errors)
    database_counts = _validate_database(database_path, consumer_path, consumer, receipt, errors)
    if consumer:
        _validate_ui(runtime_root, consumer, receipt, errors)
    capability = receipt.get("capability_contract", {})
    expected_capability = {
        "s02_admission_authority_preserved": True,
        "m3_session_state_engine_reused": True,
        "m5_renderer_engine_reused": True,
        "m6_response_contract_engine_reused": True,
        "parallel_runtime_created": False,
        "m4_new_curriculum_selection_performed": False,
        "speaking_practice_display_only": True,
        "listening_deferred": True,
    }
    if capability != expected_capability:
        errors.append("runtime_capability_contract_invalid")
    boundaries = receipt.get("claim_boundaries", {})
    for key in (
        "public_online_delivery_claimed", "real_learner_attempt_claimed", "actual_response_submitted",
        "learner_mastery_claimed", "retention_confirmed", "listening_complete",
        "speaking_recording_complete", "a2_unlocked",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"claim_boundary_invalid:{key}")
    return {
        "task_id": s03.TASK_ID,
        "schema_version": s03.SCHEMA_VERSION,
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S03_UNIFIED_LEARNER_RUNTIME",
        "error_count": len(errors),
        "errors": errors,
        "validated_counts": database_counts,
        "stop_reason": "NONE" if not errors else "S03_RUNTIME_VALIDATION_FAILED",
        "next_short_step": s03.NEXT_SHORT_STEP if not errors else s03.TASK_ID,
    }
