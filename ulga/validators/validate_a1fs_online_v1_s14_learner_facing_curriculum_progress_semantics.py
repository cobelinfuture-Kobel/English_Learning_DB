#!/usr/bin/env python3
"""Independent validator for A1FS Online V1 S14 learner-facing semantics."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_online_v1_s14_learner_facing_curriculum_progress_semantics as s14

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates S14 bilingual labels, session-versus-unit/mastery semantics, structured progress UI, "
    "S13 authority reuse, production database preservation, and no-audio boundaries only."
)
VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_S14_LEARNER_FACING_SEMANTICS_VALIDATED"


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
            "完成本次學習",
            "聽力需使用音訊，暫緩至後續版本",
            "Operator debug readback",
            "/auth.js",
            "/app.js",
        ),
        "app.js": (
            "unit.learner_label",
            "unit.learner_title_en",
            "本次學習已完成（SESSION_COMPLETED）",
            "口說目前是練習模式：不錄音、不評分",
            "value.operator_debug",
            "progressSummary.replaceChildren",
        ),
        "styles.css": (
            ".unit-grid",
            ".summary-grid",
            ".progress-card",
            "details",
        ),
        "auth.js": ("/auth/session", "X-CSRF-Token", "/auth/logout"),
        "login.html": ("A1FS 安全登入", "login-form"),
    }
    for name, tokens in required.items():
        try:
            text = (secure_root / name).read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"s14_static_missing:{name}:{exc}")
            continue
        for token in tokens:
            if token not in text:
                errors.append(f"s14_static_token_missing:{name}:{token}")
        if name == "app.js":
            forbidden = (
                "text(button, unit.grammar_unit_id)",
                "text(progress, JSON.stringify",
                "innerHTML",
                "eval(",
            )
            for token in forbidden:
                if token in text:
                    errors.append(f"s14_static_forbidden_token:{name}:{token}")


def _launch_contract(outputs: Mapping[str, Any], errors: list[str]) -> None:
    start = Path(str(outputs.get("start_script_path") or ""))
    stop = Path(str(outputs.get("stop_script_path") or ""))
    status = Path(str(outputs.get("status_script_path") or ""))
    contract_path = Path(str(outputs.get("launch_contract_path") or ""))
    for name, path in (("start", start), ("stop", stop), ("status", status), ("contract", contract_path)):
        if not path.is_file():
            errors.append(f"s14_launch_output_missing:{name}")
    try:
        start_text = start.read_text(encoding="utf-8")
        stop_text = stop.read_text(encoding="utf-8")
        status_text = status.read_text(encoding="utf-8")
    except OSError:
        return
    if "build_a1fs_online_v1_s14_learner_facing_curriculum_progress_semantics" not in start_text:
        errors.append("s14_start_module_binding_invalid")
    for secret in (s14.CANARY_PASSWORD, s14.CANARY_SESSION_SECRET):
        if secret in start_text or secret in stop_text or secret in status_text:
            errors.append("s14_launcher_secret_embedded")
    if "PID_OWNERSHIP_MISMATCH" not in stop_text or "PORT_OWNERSHIP_INVALID" not in status_text:
        errors.append("s14_launcher_lifecycle_contract_invalid")
    contract = _read(contract_path, errors, "s14_launch_contract")
    expected = {
        "host": "127.0.0.1",
        "port": 8765,
        "authentication_required": True,
        "secret_values_embedded": False,
        "external_network_binding_allowed": False,
        "cloudflare_enabled": False,
        "audio_enabled": False,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            errors.append(f"s14_launch_contract_invalid:{key}")


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    s13_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    output_root = Path(output_root).resolve()
    s13_path = Path(s13_path).resolve()

    if (
        receipt.get("task_id") != s14.TASK_ID
        or receipt.get("schema_version") != s14.SCHEMA_VERSION
        or receipt.get("validation_status") != s14.PASS_STATUS
        or receipt.get("product_status") != s14.PRODUCT_STATUS
    ):
        errors.append("s14_receipt_identity_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s14.digest(core):
        errors.append("s14_receipt_digest_invalid")
    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s14.digest(safe_core):
        errors.append("s14_safe_digest_invalid")
    try:
        s14.safe_scan(safe_report)
    except s14.LearnerFacingSemanticsError as exc:
        errors.append(str(exc))

    outputs = receipt.get("runtime_outputs", {})
    root = Path(str(outputs.get("root") or "")).resolve()
    source_s13 = Path(str(outputs.get("source_s13_receipt_path") or "")).resolve()
    database = Path(str(outputs.get("source_database_path") or "")).resolve()
    learner_static = Path(str(outputs.get("learner_static_root") or "")).resolve()
    secure_static = Path(str(outputs.get("secure_static_root") or "")).resolve()
    bundle_root = Path(str(outputs.get("bundle_root") or "")).resolve()
    if root != (output_root / "learner_facing_semantics").resolve():
        errors.append("s14_runtime_root_noncanonical")
    for name, path in (
        ("learner_static", learner_static),
        ("secure_static", secure_static),
        ("bundle_root", bundle_root),
    ):
        if not _inside(path, output_root):
            errors.append(f"s14_output_outside_authority_root:{name}")
    if source_s13 != s13_path:
        errors.append("s14_source_s13_binding_invalid")

    try:
        _, expected_database, _, _, bundles, sequence = s14._verify_s13(s13_path)
    except (s14.LearnerFacingSemanticsError, OSError, sqlite3.Error, ValueError) as exc:
        errors.append(f"s14_source_verification_failed:{exc}")
        expected_database = Path(".")
        bundles = {}
        sequence = {}
    if database != expected_database:
        errors.append("s14_database_binding_invalid")

    if len(s14.UNIT_LABELS) != 24 or len(set(s14.UNIT_LABELS)) != 24:
        errors.append("s14_unit_label_denominator_invalid")
    sequence_values = [row["sequence_index"] for row in s14.UNIT_LABELS.values()]
    if sorted(sequence_values) != list(range(1, 25)):
        errors.append("s14_unit_label_sequence_invalid")
    if any(not row["title_zh"] or not row["title_en"] for row in s14.UNIT_LABELS.values()):
        errors.append("s14_bilingual_label_missing")

    if bundles and sequence:
        try:
            app = s14._app(database, bundles, sequence)
            bootstrap = app.bootstrap()
            progress = app.progress_readback()
        except Exception as exc:  # validator reports exact runtime contract failure
            errors.append(f"s14_runtime_rebuild_failed:{exc}")
            bootstrap = {}
            progress = {}
        units = bootstrap.get("units", [])
        if len(units) != 24:
            errors.append("s14_bootstrap_unit_count_invalid")
        else:
            lessons = 0
            assets = 0
            for unit in units:
                grammar_id = str(unit.get("internal_grammar_unit_id") or "")
                expected = s14.UNIT_LABELS.get(grammar_id)
                if expected is None:
                    errors.append(f"s14_bootstrap_unknown_unit:{grammar_id}")
                    continue
                if (
                    unit.get("learner_label") != expected["learner_label"]
                    or unit.get("learner_title_zh") != expected["title_zh"]
                    or unit.get("learner_title_en") != expected["title_en"]
                    or unit.get("primary_label_uses_internal_id") is not False
                ):
                    errors.append(f"s14_bootstrap_label_invalid:{grammar_id}")
                lanes = unit.get("lanes", [])
                lessons += len(lanes)
                assets += sum(int(lane.get("asset_count") or 0) for lane in lanes)
                for lane in lanes:
                    skill = str(lane.get("skill") or "")
                    spec = s14.SKILL_SEMANTICS.get(skill)
                    if spec is None or lane.get("learner_label") != spec["learner_label"]:
                        errors.append(f"s14_lane_semantics_invalid:{grammar_id}:{skill}")
            if lessons != 72 or assets != 264:
                errors.append(f"s14_bootstrap_denominator_invalid:{lessons}:{assets}")
        semantics = bootstrap.get("learner_product_semantics", {})
        if (
            semantics.get("internal_ids_used_as_primary_labels") is not False
            or semantics.get("session_completion_implies_unit_completion") is not False
            or semantics.get("session_completion_implies_mastery") is not False
            or semantics.get("raw_progress_default_visible") is not False
        ):
            errors.append("s14_bootstrap_semantic_boundary_invalid")
        boundaries = progress.get("semantic_boundaries", {})
        if (
            boundaries.get("session_completed_implies_lesson_completed") is not False
            or boundaries.get("session_completed_implies_unit_completed") is not False
            or boundaries.get("session_completed_implies_mastery") is not False
            or boundaries.get("speaking_is_practice_only") is not True
            or boundaries.get("listening_is_audio_deferred") is not True
        ):
            errors.append("s14_progress_semantic_boundary_invalid")
        if len(progress.get("skills", [])) != 4 or len(progress.get("units", [])) != 24:
            errors.append("s14_progress_projection_denominator_invalid")

    _static_contract(secure_static, errors)
    _launch_contract(outputs, errors)

    summary = receipt.get("learner_semantics_summary", {})
    expected_summary = {
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "bilingual_unit_label_count": 24,
        "learner_primary_internal_id_count": 0,
        "skill_semantics_count": 4,
        "session_completed_relabelled": True,
        "session_unit_mastery_semantics_separated": True,
        "structured_progress_dashboard": True,
        "raw_progress_default_visible": False,
        "operator_debug_collapsed": True,
        "speaking_practice_only_labelled": True,
        "speaking_recording_enabled": False,
        "listening_audio_deferred_labelled": True,
        "listening_lesson_count": 0,
        "audio_asset_count": 0,
        "authenticated_http_acceptance": True,
        "production_database_unchanged": True,
    }
    if summary != expected_summary:
        errors.append("s14_learner_semantics_summary_invalid")

    production = receipt.get("production_safety", {})
    try:
        actual_database_sha = s14.file_digest(database)
    except OSError as exc:
        errors.append(f"s14_database_digest_unreadable:{exc}")
        actual_database_sha = ""
    if (
        production.get("production_database_sha256_before") != actual_database_sha
        or production.get("production_database_sha256_after") != actual_database_sha
        or production.get("production_database_unchanged") is not True
        or production.get("learner_progress_mutated_by_acceptance") is not False
        or production.get("auth_state_reused_from_s13") is not True
    ):
        errors.append("s14_production_safety_invalid")

    capability = receipt.get("capability_contract", {})
    expected_capability = {
        "s13_authenticated_localhost_reused": True,
        "s09_twentyfour_unit_runtime_reused": True,
        "m3_session_progress_authority_reused": True,
        "m6_response_scoring_authority_reused": True,
        "parallel_curriculum_created": False,
        "parallel_learner_state_engine_created": False,
        "parallel_scoring_engine_created": False,
        "unit_completion_claim_enabled": False,
        "mastery_write_enabled": False,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "a2_unlocked": False,
        "cloudflare_enabled": False,
    }
    if capability != expected_capability:
        errors.append("s14_capability_contract_invalid")
    if receipt.get("stop_reason") != "NONE" or receipt.get("next_short_step") != s14.NEXT_SHORT_STEP:
        errors.append("s14_continuation_contract_invalid")

    safe_expected = {
        "task_id": s14.TASK_ID,
        "program_id": s14.PROGRAM_ID,
        "schema_version": s14.SCHEMA_VERSION,
        "validation_status": s14.PASS_STATUS,
        "release_profile": s14.RELEASE_PROFILE,
        "learner_semantics_summary": receipt.get("learner_semantics_summary"),
        "production_safety": {
            "production_database_unchanged": True,
            "learner_progress_mutated_by_acceptance": False,
            "auth_state_reused_from_s13": True,
        },
        "capability_contract": receipt.get("capability_contract"),
        "product_status": s14.PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": s14.NEXT_SHORT_STEP,
    }
    if {key: value for key, value in safe_report.items() if key != "report_sha256"} != safe_expected:
        errors.append("s14_safe_projection_invalid")

    return {
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_S14_LEARNER_FACING_SEMANTICS",
        "error_count": len(errors),
        "errors": errors,
    }
