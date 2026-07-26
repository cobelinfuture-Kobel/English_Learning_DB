#!/usr/bin/env python3
"""Independently validate S09 24-unit no-audio production population outputs."""
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

from ulga.builders import build_a1fs_online_v1_s09_twentyfour_unit_production_population as s09  # noqa: E402
from ulga.builders import build_a1fs_online_v1_s07_multiunit_runtime_expansion as s07  # noqa: E402
from ulga.runners.run_a1fs_s07_with_explicit_sqlite_close import explicit_sqlite_context_close  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates existing S09 admission/runtime artifacts, SQLite counts, learner-state preservation, "
    "and safe-report boundaries. It creates no curriculum, content, answers, audio, mastery, or public delivery."
)

FORBIDDEN_SAFE_KEYS = {
    "accepted_texts", "accepted_sequence", "answer", "answer_contract", "answer_key",
    "asset_key", "database_path", "display_label", "learner_id", "learner_payload",
    "private_scoring_contract", "prompt", "prompt_text", "response", "rubric",
    "scoring_contract", "session_id", "subject_key",
}


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


def _safe_scan(value: Any, errors: list[str]) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                    errors.append(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
    cp01_path: Path,
    cp04_path: Path,
    m03_path: Path,
    s08_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    expected_identity = (
        s09.TASK_ID,
        s09.SCHEMA_VERSION,
        s09.PASS_STATUS,
        s09.PRODUCT_STATUS,
        "NONE",
    )
    actual_identity = (
        receipt.get("task_id"),
        receipt.get("schema_version"),
        receipt.get("validation_status"),
        receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    if actual_identity != expected_identity:
        errors.append("receipt_identity_or_status_invalid")
    receipt_core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s07.digest(receipt_core):
        errors.append("receipt_digest_invalid")

    safe_identity = (
        safe_report.get("task_id"),
        safe_report.get("schema_version"),
        safe_report.get("validation_status"),
        safe_report.get("product_status"),
        safe_report.get("stop_reason"),
    )
    if safe_identity != expected_identity:
        errors.append("safe_identity_or_status_invalid")
    safe_core = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != s07.digest(safe_core):
        errors.append("safe_digest_invalid")
    _safe_scan(safe_report, errors)

    cp01 = _read(cp01_path, "cp01", errors)
    cp04 = _read(cp04_path, "cp04", errors)
    m03 = _read(m03_path, "m03", errors)
    s08 = _read(s08_path, "s08", errors)
    if errors:
        return {"validation_status": "FAIL", "error_count": len(errors), "errors": errors}

    try:
        expected_admission = s09.build_full_admission(
            cp01_artifact=cp01,
            cp04_artifact=cp04,
            m03_artifact=m03,
        )
    except Exception as exc:  # fail-closed validator boundary
        errors.append(f"independent_admission_rebuild_failed:{exc}")
        expected_admission = {}

    outputs = receipt.get("runtime_outputs", {})
    admission_path = Path(str(outputs.get("admission_path") or "")).resolve()
    consumer_path = Path(str(outputs.get("consumer_path") or "")).resolve()
    database_path = Path(str(outputs.get("database_path") or "")).resolve()
    bundle_index_path = Path(str(outputs.get("bundle_index_path") or "")).resolve()
    static_root = Path(str(outputs.get("static_root") or "")).resolve()
    required_files = (admission_path, consumer_path, database_path, bundle_index_path)
    if any(not path.is_file() for path in required_files) or not static_root.is_dir():
        errors.append("runtime_outputs_missing")
        return {"validation_status": "FAIL", "error_count": len(errors), "errors": errors}

    admission = _read(admission_path, "admission", errors)
    consumer = _read(consumer_path, "consumer", errors)
    bundle_index = _read(bundle_index_path, "bundle_index", errors)
    if expected_admission and admission != expected_admission:
        errors.append("admission_not_independently_reproducible")

    summary = receipt.get("population_summary", {})
    expected_summary = {
        "canonical_unit_denominator": 24,
        "populated_unit_count": 24,
        "reading_item_count": 96,
        "writing_item_count": 96,
        "speaking_practice_card_count": 72,
        "admitted_nonaudio_item_count": 264,
        "runtime_lesson_count": 72,
        "listening_item_count": 0,
        "speaking_assessment_item_count": 0,
    }
    for key, value in expected_summary.items():
        if summary.get(key) != value:
            errors.append(f"population_summary_invalid:{key}:{summary.get(key)}:{value}")
    if summary.get("scene_authority_gap_unit_count") != cp04.get("coverage_summary", {}).get("scene_authority_gap_unit_count"):
        errors.append("scene_gap_not_reconciled")
    if summary.get("raz_material_binding_candidate_count") != cp04.get("coverage_summary", {}).get("raz_material_binding_candidate_count"):
        errors.append("raz_binding_count_not_reconciled")

    if len(admission.get("admitted_units", [])) != 24:
        errors.append("admitted_unit_count_not_24")
    if consumer.get("counts", {}).get("lesson_count") != 72:
        errors.append("consumer_lesson_count_not_72")
    if consumer.get("counts", {}).get("asset_record_count") != 264:
        errors.append("consumer_asset_count_not_264")
    if len(bundle_index.get("units", [])) != 24 or len(bundle_index.get("lessons", {})) != 72:
        errors.append("bundle_index_denominator_invalid")

    with explicit_sqlite_context_close():
        try:
            counts = s07._database_counts(database_path)
        except (sqlite3.Error, OSError) as exc:
            errors.append(f"database_count_read_failed:{exc}")
            counts = {}
    expected_counts = {
        "lesson_count": 72,
        "asset_count": 264,
        "response_contract_count": 264,
        "capture_enabled_contract_count": 192,
        "speaking_capture_enabled_count": 0,
        "listening_lesson_count": 0,
    }
    for key, value in expected_counts.items():
        if counts.get(key) != value:
            errors.append(f"database_count_invalid:{key}:{counts.get(key)}:{value}")

    migration = receipt.get("migration_summary", {})
    required_true = {
        "existing_profile_count_preserved": migration.get("existing_profile_count_preserved"),
        "existing_session_count_preserved": migration.get("existing_session_count_preserved"),
        "existing_attempt_count_preserved": migration.get("existing_attempt_count_preserved"),
        "production_progress_preserved": migration.get("production_progress_preserved"),
        "atomic_database_migration": migration.get("atomic_database_migration"),
        "first_three_unit_identity_preserved": migration.get("first_three_unit_identity_preserved"),
        "unit24_runtime_canary": receipt.get("unit24_runtime_canary", {}).get("newly_admitted_unit_runtime_canary"),
        "surface_reused": receipt.get("learner_surface", {}).get("s08_journey_surface_reused"),
        "twentyfour_navigation": receipt.get("learner_surface", {}).get("twentyfour_unit_navigation"),
    }
    for key, value in required_true.items():
        if value is not True:
            errors.append(f"required_true_invalid:{key}")
    if migration.get("progress_state_sha256_before") != migration.get("progress_state_sha256_after"):
        errors.append("progress_digest_changed")

    static_markers = {
        "index.html": "A1FS 多單元學習旅程工作台",
        "app.js": "Boolean(active || pendingResume)",
        "styles.css": ".selected",
    }
    for filename, marker in static_markers.items():
        path = static_root / filename
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"static_file_unreadable:{filename}:{exc}")
            continue
        if marker not in text:
            errors.append(f"static_marker_missing:{filename}:{marker}")

    expected_safe_sections = (
        "population_summary", "runtime_summary", "migration_summary",
        "unit24_runtime_canary", "learner_surface", "capability_contract",
    )
    for section in expected_safe_sections:
        if safe_report.get(section) != (
            {key: value for key, value in receipt.get(section, {}).items() if not key.startswith("progress_state_sha256")}
            if section == "migration_summary"
            else receipt.get(section)
        ):
            errors.append(f"safe_projection_invalid:{section}")

    if receipt.get("source_identity", {}).get("s08_sha256") != s09.s08.digest(s08):
        errors.append("s08_source_digest_invalid")
    return {
        "validation_status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "validated_counts": {
            "unit_count": summary.get("populated_unit_count"),
            "lesson_count": counts.get("lesson_count"),
            "asset_count": counts.get("asset_count"),
            "response_contract_count": counts.get("response_contract_count"),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--safe-report", type=Path, required=True)
    parser.add_argument("--cp01", type=Path, required=True)
    parser.add_argument("--cp04", type=Path, required=True)
    parser.add_argument("--m03", type=Path, required=True)
    parser.add_argument("--s08", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = _read(args.receipt, "receipt", [])
    safe = _read(args.safe_report, "safe_report", [])
    result = validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=args.receipt.parent,
        cp01_path=args.cp01,
        cp04_path=args.cp04,
        m03_path=args.m03,
        s08_path=args.s08,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
