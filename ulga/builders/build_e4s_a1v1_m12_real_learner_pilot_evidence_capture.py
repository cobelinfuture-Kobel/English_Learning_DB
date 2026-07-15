#!/usr/bin/env python3
"""Prepare and import A1/A1+ real learner pilot evidence.

PREPARE builds the accepted M11C localhost runtime and emits a private capture
manifest plus an M08-compatible attempt-registry template. IMPORT accepts only
non-empty registries tied to the exact M08 source-bank hash and restricted to the
184 Authority-reviewed selectable items. CI fixtures must be explicitly labelled
TEST_FIXTURE and can never create a real-learner evidence claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SOURCE_REPO_ROOT
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08  # noqa: E402
from ulga.builders import build_e4s_a1v1_m11c_authority_reviewed_private_runtime as m11c  # noqa: E402
from ulga.validators import validate_e4s_a1v1_m11c_authority_reviewed_private_runtime as m11c_validator  # noqa: E402

TASK_ID = "E4S-A1V1-M12_A1A1PlusRealLearnerPilotEvidenceCapture"
MANIFEST_SCHEMA_VERSION = "e4s.a1v1.m12_pilot_capture_manifest.v1"
REPORT_SCHEMA_VERSION = "e4s.a1v1.m12_pilot_capture_safe_report.v1"
PREPARE_STATUS = "PASS_M12_REAL_LEARNER_PILOT_CAPTURE_PIPELINE_READY"
TEST_STATUS = "PASS_M12_CAPTURE_PIPELINE_TEST_FIXTURE_VALIDATED"
REAL_STATUS = "PASS_M12_REAL_LEARNER_PILOT_EVIDENCE_CAPTURED"
NEXT_IMPORT = "E4S-A1V1-M12B_RealLearnerPilotEvidenceImportAndQA"
NEXT_QA = "E4S-A1V1-M12C_RealLearnerPilotEvidenceQAAndIteration"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12"
DEFAULT_PORT = 8771
M11D_CLOSEOUT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m11d_system_acceptance_closeout.json"
SCHEMA_DIR = REPO_ROOT / "ulga/schemas"
DEFERRED_GRAMMAR_ID = "GRAMMAR_WILL_FUTURE_A1"
EVIDENCE_ORIGINS = {"REAL_LEARNER", "TEST_FIXTURE"}


class PilotCaptureError(ValueError):
    """Fail-closed M12 capture/import error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotCaptureError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise PilotCaptureError(f"json_root_not_object:{path}")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _safe_output_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise PilotCaptureError(f"output_root_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise PilotCaptureError(f"{code}:expected={expected!r}:actual={actual!r}")


def _assert_schema(name: str, value: Mapping[str, Any]) -> None:
    schema = read_json(SCHEMA_DIR / name)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise PilotCaptureError(f"schema_validation_failed:{name}:{location}:{first.message}")


def _safe_scan(value: Any, *, name: str) -> None:
    forbidden = {
        "response",
        "learner_response",
        "learner_responses",
        "prompt",
        "answer",
        "answer_key",
        "accepted_texts",
        "accepted_sequence",
        "private_scoring_contract",
        "model_texts",
        "source_payload",
    }

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                lowered = str(key).casefold()
                if lowered in forbidden or lowered.endswith("_absolute_path"):
                    raise PilotCaptureError(f"private_field_leak:{name}:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (len(node) > 2 and node[1:3] in {":\\", ":/"}):
                raise PilotCaptureError(f"absolute_path_leak:{name}")

    walk(value)


def _validate_m11d_closeout(closeout: Mapping[str, Any]) -> None:
    _require(
        closeout.get("task_id"),
        "E4S-A1V1-M11D_AuthorityReviewedPrivateRuntimeAcceptanceAndA1A1PlusCloseout",
        "m11d_task_id",
    )
    _require(
        closeout.get("acceptance_status"),
        "PASS_M11D_A1A1PLUS_AUTHORITY_REVIEWED_PRIVATE_SYSTEM_CLOSED",
        "m11d_acceptance_status",
    )
    _require(closeout.get("authority_reviewed_private_path", {}).get("selectable_items"), 184, "m11d_selectable_items")
    _require(closeout.get("authority_reviewed_private_path", {}).get("private_ready_units"), 23, "m11d_private_units")
    _require(closeout.get("authority_reviewed_private_path", {}).get("private_ready_rows"), 107, "m11d_private_rows")
    _require(closeout.get("cambridge_ceiling_deferred", {}).get("grammar_unit_id"), DEFERRED_GRAMMAR_ID, "m11d_deferred_unit")
    _require(closeout.get("evidence_state", {}).get("actual_learner_attempts"), 0, "m11d_actual_attempts")
    _require(closeout.get("evidence_state", {}).get("learner_mastery_claimed"), False, "m11d_mastery")


def _prepare_report() -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": "PREPARE",
        "evidence_origin": "NONE",
        "selectable_item_count": 184,
        "private_ready_unit_count": 23,
        "private_ready_row_count": 107,
        "actual_attempt_count": 0,
        "attempted_unit_count": 0,
        "attempted_row_count": 0,
        "outcome_counts": {},
        "pending_human_review_count": 0,
        "real_learner_evidence_captured": False,
        "real_learner_pilot_completed": False,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "claim_boundaries": {
            "metadata_only_report": True,
            "private_responses_included": False,
            "test_fixture_counted_as_real_evidence": False,
            "canonical_authority_write": False,
            "canonical_egp_mapping_changed": False,
            "public_delivery": False,
            "production_runtime_enabled": False,
            "a2_content_promoted": False,
            "audio_or_recording_processed": False,
        },
        "validation_status": PREPARE_STATUS,
        "stop_reason": "REAL_LEARNER_SESSION_EVIDENCE_REQUIRED",
        "next_short_step": NEXT_IMPORT,
        "errors": [],
    }


def prepare_capture(output_root: Path, *, port: int = DEFAULT_PORT) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    closeout = read_json(M11D_CLOSEOUT_PATH)
    _validate_m11d_closeout(closeout)

    runtime_result = m11c.build_runtime_artifacts(root / "runtime", port=port)
    runtime_validation = m11c_validator.validate(root / "runtime")
    write_json_atomic(root / "runtime_validation.json", runtime_validation)
    _require(runtime_validation.get("validation_status"), m11c.RUNTIME_STATUS, "m11c_runtime_validation")
    _require(runtime_validation.get("error_count"), 0, "m11c_runtime_errors")

    source_bank = read_json(root / "runtime/source_m08/text_mode_session_bank.private.json")
    source_bank_hash = m08.sha256_value(source_bank)
    query = runtime_result["query_index"]
    selectable_ids = sorted(str(row["item_id"]) for row in query["items"])
    _require(len(selectable_ids), 184, "selectable_item_count")
    _require(len(set(selectable_ids)), 184, "selectable_item_identity")
    if any(row.get("grammar_unit_id") == DEFERRED_GRAMMAR_ID for row in query["items"]):
        raise PilotCaptureError("deferred_will_item_in_selectable_query")

    manifest = {
        "task_id": TASK_ID,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "private_local_only": True,
        "source_hashes": {
            "m11d_closeout_sha256": sha256_value(closeout),
            "m11c_runtime_manifest_sha256": sha256_value(runtime_result["manifest"]),
            "m08_source_bank_sha256": source_bank_hash,
            "selectable_item_ids_sha256": sha256_value(selectable_ids),
        },
        "runtime": {
            "allowed_host": "127.0.0.1",
            "default_port": port,
            "dashboard_entrypoint": "runtime/dashboard/index.html",
            "session_entrypoint": "runtime/authority_session/index.html",
            "network_submission_enabled": False,
        },
        "selection": {
            "selectable_item_count": 184,
            "private_ready_unit_count": 23,
            "private_ready_row_count": 107,
            "reading_item_count": 92,
            "writing_item_count": 92,
            "practice_item_count": 138,
            "assessment_item_count": 46,
            "selectable_item_ids": selectable_ids,
        },
        "attempt_registry_contract": {
            "task_id": m08.TASK_ID,
            "schema_version": "e4s.a1v1.text_mode_attempt_registry.v1",
            "session_bank_sha256": source_bank_hash,
            "minimum_attempt_count": 1,
            "maximum_attempt_count": 184,
            "evidence_origin_required": "REAL_LEARNER",
            "deferred_item_submission_allowed": False,
        },
        "deferred_unit": {
            "grammar_unit_id": DEFERRED_GRAMMAR_ID,
            "excluded_item_count": 8,
            "canonical_egp_row_count": 2,
            "status": "DEFERRED_CAMBRIDGE_FLYERS_A2_CHILD_PATH_CEILING",
        },
        "capture_status": "READY_FOR_REAL_LEARNER_SESSION",
        "claim_boundaries": {
            "private_local_only": True,
            "real_learner_evidence_captured": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "canonical_authority_write": False,
            "public_delivery": False,
            "a2_content_promoted": False,
            "audio_or_recording_processed": False,
        },
    }
    _assert_schema("e4s_a1v1_m12_pilot_capture_manifest.schema.json", manifest)

    template = m08.empty_attempt_registry(source_bank)
    report = _prepare_report()
    _safe_scan(report, name="m12_prepare_safe_report")
    _assert_schema("e4s_a1v1_m12_pilot_capture_safe_report.schema.json", report)
    write_json_atomic(root / "pilot_capture_manifest.private.json", manifest)
    write_json_atomic(root / "pilot_attempt_registry.template.json", template)
    write_json_atomic(root / "pilot_capture_readiness_safe_report.json", report)
    return {
        "manifest": manifest,
        "template": template,
        "safe_report": report,
        "runtime": runtime_result,
        "runtime_validation": runtime_validation,
    }


def _validate_import_registry(
    manifest: Mapping[str, Any],
    registry: Mapping[str, Any],
    *,
    evidence_origin: str,
) -> list[str]:
    if evidence_origin not in EVIDENCE_ORIGINS:
        raise PilotCaptureError(f"evidence_origin_invalid:{evidence_origin}")
    contract = manifest["attempt_registry_contract"]
    _require(registry.get("task_id"), contract["task_id"], "registry_task_id")
    _require(registry.get("schema_version"), contract["schema_version"], "registry_schema_version")
    _require(registry.get("private_local_only"), True, "registry_private_local_only")
    _require(registry.get("session_bank_sha256"), contract["session_bank_sha256"], "registry_session_bank_hash")
    attempts = registry.get("attempts")
    if not isinstance(attempts, list):
        raise PilotCaptureError("registry_attempts_not_array")
    if not 1 <= len(attempts) <= 184:
        raise PilotCaptureError(f"registry_attempt_count_out_of_range:{len(attempts)}")
    allowed = set(manifest["selection"]["selectable_item_ids"])
    item_ids = [str(row.get("item_id") or "") for row in attempts]
    if len(set(item_ids)) != len(item_ids):
        raise PilotCaptureError("registry_duplicate_attempt_item")
    unknown = sorted(set(item_ids) - allowed)
    if unknown:
        raise PilotCaptureError(f"registry_nonselectable_items:{unknown}")
    return item_ids


def import_evidence(
    output_root: Path,
    attempt_registry_path: Path,
    *,
    evidence_origin: str,
    port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    prepared = prepare_capture(root, port=port)
    manifest = prepared["manifest"]
    registry = read_json(attempt_registry_path)
    _validate_import_registry(manifest, registry, evidence_origin=evidence_origin)
    source_bank = read_json(root / "runtime/source_m08/text_mode_session_bank.private.json")
    ledger, progress_report, query = m08.build_progress_artifacts(source_bank, registry)
    attempt_count = int(ledger["attempt_count"])
    if attempt_count < 1:
        raise PilotCaptureError("real_pilot_import_requires_nonzero_attempts")

    is_real = evidence_origin == "REAL_LEARNER"
    report = {
        "task_id": TASK_ID,
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": "IMPORT",
        "evidence_origin": evidence_origin,
        "selectable_item_count": 184,
        "private_ready_unit_count": 23,
        "private_ready_row_count": 107,
        "actual_attempt_count": attempt_count,
        "attempted_unit_count": int(ledger["attempted_unit_count"]),
        "attempted_row_count": int(ledger["attempted_row_count"]),
        "outcome_counts": dict(ledger["outcome_counts"]),
        "pending_human_review_count": int(progress_report["pending_human_review_count"]),
        "real_learner_evidence_captured": is_real,
        "real_learner_pilot_completed": False,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "claim_boundaries": {
            "metadata_only_report": True,
            "private_responses_included": False,
            "test_fixture_counted_as_real_evidence": False,
            "canonical_authority_write": False,
            "canonical_egp_mapping_changed": False,
            "public_delivery": False,
            "production_runtime_enabled": False,
            "a2_content_promoted": False,
            "audio_or_recording_processed": False,
        },
        "validation_status": REAL_STATUS if is_real else TEST_STATUS,
        "stop_reason": "NONE" if is_real else "REAL_LEARNER_SESSION_EVIDENCE_REQUIRED",
        "next_short_step": NEXT_QA if is_real else NEXT_IMPORT,
        "errors": [],
    }
    _safe_scan(report, name="m12_import_safe_report")
    _assert_schema("e4s_a1v1_m12_pilot_capture_safe_report.schema.json", report)

    write_json_atomic(root / "pilot_attempt_registry.private.json", registry)
    write_json_atomic(root / "pilot_progress_ledger.private.json", ledger)
    write_json_atomic(root / "pilot_progress_query_index.json", query)
    write_json_atomic(root / "pilot_evidence_capture_safe_report.json", report)
    return {
        "manifest": manifest,
        "registry": registry,
        "ledger": ledger,
        "progress_report": progress_report,
        "query": query,
        "safe_report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    prepare.add_argument("--port", type=int, default=DEFAULT_PORT)
    import_cmd = sub.add_parser("import-evidence")
    import_cmd.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    import_cmd.add_argument("--attempt-registry", type=Path, required=True)
    import_cmd.add_argument("--evidence-origin", choices=sorted(EVIDENCE_ORIGINS), required=True)
    import_cmd.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_capture(args.output_root, port=args.port)
        else:
            result = import_evidence(
                args.output_root,
                args.attempt_registry,
                evidence_origin=args.evidence_origin,
                port=args.port,
            )
        report = result["safe_report"]
        print(json.dumps({
            "mode": report["mode"],
            "evidence_origin": report["evidence_origin"],
            "selectable_items": report["selectable_item_count"],
            "actual_attempts": report["actual_attempt_count"],
            "attempted_units": report["attempted_unit_count"],
            "attempted_rows": report["attempted_row_count"],
            "real_learner_evidence_captured": report["real_learner_evidence_captured"],
            "validation_status": report["validation_status"],
            "stop_reason": report["stop_reason"],
            "next_short_step": report["next_short_step"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        PilotCaptureError,
        m11c.AuthorityRuntimeError,
        m08.TextModeSessionError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
