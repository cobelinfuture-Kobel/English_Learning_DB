#!/usr/bin/env python3
"""Independently validate M12 real-learner pilot capture artifacts."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m12_real_learner_pilot_evidence_capture as builder  # noqa: E402

PASS_STATUSES = {builder.PREPARE_STATUS, builder.TEST_STATUS, builder.REAL_STATUS}
DEFAULT_VALIDATION_PATH = builder.DEFAULT_OUTPUT_ROOT / "pilot_capture_validation.json"


def _validate_manifest(manifest: dict[str, Any], root: Path, errors: list[str]) -> None:
    try:
        builder._assert_schema(
            "e4s_a1v1_m12_pilot_capture_manifest.schema.json",
            manifest,
        )
    except builder.PilotCaptureError as exc:
        errors.append(str(exc))
        return

    selection = manifest.get("selection", {})
    item_ids = list(selection.get("selectable_item_ids", []))
    if len(item_ids) != 184 or len(set(item_ids)) != 184:
        errors.append("selectable_item_identity_not_184")
    if manifest.get("source_hashes", {}).get("selectable_item_ids_sha256") != builder.sha256_value(sorted(item_ids)):
        errors.append("selectable_item_ids_hash_drift")
    for key, expected in {
        "selectable_item_count": 184,
        "private_ready_unit_count": 23,
        "private_ready_row_count": 107,
        "reading_item_count": 92,
        "writing_item_count": 92,
        "practice_item_count": 138,
        "assessment_item_count": 46,
    }.items():
        if selection.get(key) != expected:
            errors.append(f"selection_count_drift:{key}")

    contract = manifest.get("attempt_registry_contract", {})
    if contract.get("task_id") != builder.m08.TASK_ID:
        errors.append("attempt_registry_task_id_drift")
    if contract.get("schema_version") != "e4s.a1v1.text_mode_attempt_registry.v1":
        errors.append("attempt_registry_schema_version_drift")
    if contract.get("minimum_attempt_count") != 1 or contract.get("maximum_attempt_count") != 184:
        errors.append("attempt_registry_count_contract_drift")
    if contract.get("evidence_origin_required") != "REAL_LEARNER":
        errors.append("real_learner_origin_contract_missing")
    if contract.get("deferred_item_submission_allowed") is not False:
        errors.append("deferred_item_submission_not_forbidden")

    deferred = manifest.get("deferred_unit", {})
    if deferred != {
        "grammar_unit_id": builder.DEFERRED_GRAMMAR_ID,
        "excluded_item_count": 8,
        "canonical_egp_row_count": 2,
        "status": "DEFERRED_CAMBRIDGE_FLYERS_A2_CHILD_PATH_CEILING",
    }:
        errors.append("deferred_unit_contract_drift")

    runtime_root = root / "runtime"
    try:
        runtime_manifest = builder.read_json(runtime_root / "runtime_manifest.json")
        runtime_validation = builder.read_json(root / "runtime_validation.json")
        source_bank = builder.read_json(runtime_root / "source_m08/text_mode_session_bank.private.json")
        query = builder.read_json(runtime_root / "authority_runtime_query_index.json")
        payload = builder.read_json(runtime_root / "authority_session/payload.json")
    except builder.PilotCaptureError as exc:
        errors.append(str(exc))
        return

    if runtime_manifest.get("runtime_status") != builder.m11c.RUNTIME_STATUS:
        errors.append("m11c_runtime_status_drift")
    if runtime_validation.get("validation_status") != builder.m11c.RUNTIME_STATUS:
        errors.append("m11c_runtime_validation_status_drift")
    if runtime_validation.get("error_count") != 0:
        errors.append("m11c_runtime_validation_errors")
    source_hash = builder.m08.sha256_value(source_bank)
    if source_hash != manifest.get("source_hashes", {}).get("m08_source_bank_sha256"):
        errors.append("m08_source_bank_hash_drift")
    if source_hash != contract.get("session_bank_sha256"):
        errors.append("attempt_registry_source_bank_hash_drift")
    if builder.sha256_value(runtime_manifest) != manifest.get("source_hashes", {}).get("m11c_runtime_manifest_sha256"):
        errors.append("m11c_runtime_manifest_hash_drift")

    query_ids = sorted(str(row.get("item_id")) for row in query.get("items", []))
    payload_ids = sorted(str(row.get("item_id")) for row in payload.get("items", []))
    if query_ids != sorted(item_ids):
        errors.append("manifest_query_allowlist_drift")
    if payload_ids != sorted(item_ids):
        errors.append("manifest_payload_allowlist_drift")
    if any(row.get("grammar_unit_id") == builder.DEFERRED_GRAMMAR_ID for row in query.get("items", [])):
        errors.append("deferred_will_query_leak")
    if any(row.get("grammar_unit_id") == builder.DEFERRED_GRAMMAR_ID for row in payload.get("items", [])):
        errors.append("deferred_will_payload_leak")


def validate_prepare(output_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    report: dict[str, Any] = {}
    rebuild_root: Path | None = None
    try:
        root = builder._safe_output_root(output_root)
        manifest = builder.read_json(root / "pilot_capture_manifest.private.json")
        report = builder.read_json(root / "pilot_capture_readiness_safe_report.json")
        template = builder.read_json(root / "pilot_attempt_registry.template.json")
        _validate_manifest(manifest, root, errors)
        builder._safe_scan(report, name="m12_prepare_safe_report")
        builder._assert_schema(
            "e4s_a1v1_m12_pilot_capture_safe_report.schema.json",
            report,
        )
        contract = manifest.get("attempt_registry_contract", {})
        if template.get("session_bank_sha256") != contract.get("session_bank_sha256"):
            errors.append("template_session_bank_hash_drift")
        if template.get("attempts") != []:
            errors.append("prepare_template_not_empty")
        if report.get("mode") != "PREPARE" or report.get("evidence_origin") != "NONE":
            errors.append("prepare_report_mode_or_origin_drift")
        if report.get("actual_attempt_count") != 0:
            errors.append("prepare_report_attempt_count_nonzero")
        if report.get("real_learner_evidence_captured") is not False:
            errors.append("prepare_false_real_evidence_claim")
        if report.get("validation_status") != builder.PREPARE_STATUS:
            errors.append("prepare_status_drift")
        if report.get("stop_reason") != "REAL_LEARNER_SESSION_EVIDENCE_REQUIRED":
            errors.append("prepare_stop_reason_drift")
        if report.get("next_short_step") != builder.NEXT_IMPORT:
            errors.append("prepare_next_short_step_drift")

        rebuild_root = root.parent / f"m12-prepare-rebuild-{uuid.uuid4().hex}"
        rebuilt = builder.prepare_capture(
            rebuild_root,
            port=manifest.get("runtime", {}).get("default_port", builder.DEFAULT_PORT),
        )
        if rebuilt["manifest"] != manifest:
            errors.append("prepare_manifest_not_reproducible")
        if rebuilt["template"] != template:
            errors.append("prepare_template_not_reproducible")
        if rebuilt["safe_report"] != report:
            errors.append("prepare_safe_report_not_reproducible")
    except (
        builder.PilotCaptureError,
        builder.m11c.AuthorityRuntimeError,
        builder.m08.TextModeSessionError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    finally:
        if rebuild_root is not None:
            shutil.rmtree(rebuild_root, ignore_errors=True)

    return {
        "task_id": builder.TASK_ID,
        "mode": "PREPARE",
        "validation_status": builder.PREPARE_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "selectable_item_count": manifest.get("selection", {}).get("selectable_item_count", 0),
        "private_ready_unit_count": manifest.get("selection", {}).get("private_ready_unit_count", 0),
        "private_ready_row_count": manifest.get("selection", {}).get("private_ready_row_count", 0),
        "actual_attempt_count": 0,
        "evidence_origin": "NONE",
        "real_learner_evidence_captured": False,
        "real_learner_pilot_completed": False,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "canonical_authority_write": False,
        "public_delivery": False,
        "a2_content_promoted": False,
        "audio_or_recording_processed": False,
        "stop_reason": "REAL_LEARNER_SESSION_EVIDENCE_REQUIRED" if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_IMPORT if not errors else None,
    }


def validate_import(output_root: Path, *, expected_origin: str) -> dict[str, Any]:
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    report: dict[str, Any] = {}
    ledger: dict[str, Any] = {}
    try:
        if expected_origin not in builder.EVIDENCE_ORIGINS:
            raise builder.PilotCaptureError(f"evidence_origin_invalid:{expected_origin}")
        root = builder._safe_output_root(output_root)
        manifest = builder.read_json(root / "pilot_capture_manifest.private.json")
        registry = builder.read_json(root / "pilot_attempt_registry.private.json")
        ledger = builder.read_json(root / "pilot_progress_ledger.private.json")
        query = builder.read_json(root / "pilot_progress_query_index.json")
        report = builder.read_json(root / "pilot_evidence_capture_safe_report.json")
        _validate_manifest(manifest, root, errors)
        builder._validate_import_registry(
            manifest,
            registry,
            evidence_origin=expected_origin,
        )
        builder._safe_scan(report, name="m12_import_safe_report")
        builder._assert_schema(
            "e4s_a1v1_m12_pilot_capture_safe_report.schema.json",
            report,
        )

        attempts = list(registry.get("attempts", []))
        entries = list(ledger.get("entries", []))
        if len(attempts) < 1:
            errors.append("import_requires_nonzero_attempts")
        if len(entries) != len(attempts):
            errors.append("ledger_attempt_count_drift")
        if ledger.get("attempt_count") != len(attempts):
            errors.append("ledger_attempt_accounting_drift")
        if report.get("actual_attempt_count") != len(attempts):
            errors.append("safe_report_attempt_accounting_drift")
        if report.get("attempted_unit_count") != ledger.get("attempted_unit_count"):
            errors.append("safe_report_unit_accounting_drift")
        if report.get("attempted_row_count") != ledger.get("attempted_row_count"):
            errors.append("safe_report_row_accounting_drift")
        if report.get("outcome_counts") != ledger.get("outcome_counts"):
            errors.append("safe_report_outcome_accounting_drift")
        if query.get("attempt_count") != len(attempts):
            errors.append("query_attempt_accounting_drift")
        if any(entry.get("grammar_unit_id") == builder.DEFERRED_GRAMMAR_ID for entry in entries):
            errors.append("deferred_will_evidence_leak")
        if report.get("evidence_origin") != expected_origin:
            errors.append("import_evidence_origin_drift")
        if report.get("real_learner_pilot_completed") is not False:
            errors.append("pilot_completion_false_claim")
        if report.get("learner_mastery_claimed") is not False:
            errors.append("mastery_false_claim")
        if report.get("retention_confirmed") is not False:
            errors.append("retention_false_claim")

        if expected_origin == "TEST_FIXTURE":
            if report.get("validation_status") != builder.TEST_STATUS:
                errors.append("test_fixture_status_drift")
            if report.get("real_learner_evidence_captured") is not False:
                errors.append("test_fixture_counted_as_real_evidence")
            if report.get("stop_reason") != "REAL_LEARNER_SESSION_EVIDENCE_REQUIRED":
                errors.append("test_fixture_stop_reason_drift")
            if report.get("next_short_step") != builder.NEXT_IMPORT:
                errors.append("test_fixture_next_short_step_drift")
        else:
            if report.get("validation_status") != builder.REAL_STATUS:
                errors.append("real_learner_status_drift")
            if report.get("real_learner_evidence_captured") is not True:
                errors.append("real_learner_evidence_not_marked_captured")
            if report.get("stop_reason") != "NONE":
                errors.append("real_learner_stop_reason_drift")
            if report.get("next_short_step") != builder.NEXT_QA:
                errors.append("real_learner_next_short_step_drift")
    except (
        builder.PilotCaptureError,
        builder.m11c.AuthorityRuntimeError,
        builder.m08.TextModeSessionError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))

    real_captured = expected_origin == "REAL_LEARNER" and not errors
    expected_status = builder.REAL_STATUS if expected_origin == "REAL_LEARNER" else builder.TEST_STATUS
    return {
        "task_id": builder.TASK_ID,
        "mode": "IMPORT",
        "validation_status": expected_status if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "selectable_item_count": manifest.get("selection", {}).get("selectable_item_count", 0),
        "actual_attempt_count": ledger.get("attempt_count", 0),
        "attempted_unit_count": ledger.get("attempted_unit_count", 0),
        "attempted_row_count": ledger.get("attempted_row_count", 0),
        "evidence_origin": expected_origin,
        "real_learner_evidence_captured": real_captured,
        "real_learner_pilot_completed": False,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "canonical_authority_write": False,
        "public_delivery": False,
        "a2_content_promoted": False,
        "audio_or_recording_processed": False,
        "stop_reason": (
            "NONE"
            if real_captured
            else "REAL_LEARNER_SESSION_EVIDENCE_REQUIRED"
            if not errors
            else "VALIDATION_FAILURE"
        ),
        "next_short_step": (
            builder.NEXT_QA
            if real_captured
            else builder.NEXT_IMPORT
            if not errors
            else None
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    prepare.add_argument("--validation-report", type=Path, default=DEFAULT_VALIDATION_PATH)
    import_cmd = sub.add_parser("import-evidence")
    import_cmd.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    import_cmd.add_argument("--expected-origin", choices=sorted(builder.EVIDENCE_ORIGINS), required=True)
    import_cmd.add_argument("--validation-report", type=Path, default=DEFAULT_VALIDATION_PATH)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        result = validate_prepare(args.output_root)
    else:
        result = validate_import(args.output_root, expected_origin=args.expected_origin)
    builder.write_json_atomic(args.validation_report, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["validation_status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
