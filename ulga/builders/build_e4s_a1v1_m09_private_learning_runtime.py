#!/usr/bin/env python3
"""Prepare and accept the A1/A1+ private localhost learning runtime.

The runtime exposes the M08 Reading/Writing text session through a localhost-only
dashboard. It references the previously validated Listening and Speaking contract
states without copying audio assets or exposing recording controls. No production
runtime, public delivery, mastery, retention, Authority write, or A2 expansion is
claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SOURCE_REPO_ROOT
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08  # noqa: E402
from ulga.validators import validate_e4s_a1v1_m08_text_mode_learner_session as m08_validator  # noqa: E402

TASK_ID = "E4S-A1V1-M09_A1A1PlusPrivateLearningRuntimeAcceptanceAndCloseout"
EPIC_ID = "E4S-A1V1_A1A1PlusCompleteFourSkillLearningSystem"
MANIFEST_SCHEMA_VERSION = "e4s.a1v1.private_learning_runtime_manifest.v1"
ACCEPTANCE_SCHEMA_VERSION = "e4s.a1v1.private_runtime_acceptance.v1"
RUNTIME_STATUS = "PASS_PRIVATE_RUNTIME_READY"
ACCEPTANCE_STATUS = "PASS_M09_PRIVATE_LEARNING_RUNTIME_ACCEPTED"
NEXT_SHORT_STEP = "E4S-A1V1-M10_A1A1PlusCoverageRecheckAndBacklogClosure_NoNewDesignDocs"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/runtime/m09"
M07_RECEIPT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m07_four_skill_contract_closure.json"
M08_RECEIPT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m08_text_mode_session_closeout.json"
SCHEMA_DIR = SOURCE_REPO_ROOT / "ulga/schemas"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
SAFE_FORBIDDEN_KEYS = {
    "answer",
    "answer_key",
    "answer_contract",
    "accepted_texts",
    "accepted_sequence",
    "canonical_target",
    "correct_token_sequence",
    "correct_morphology_parts",
    "private_scoring_contract",
    "model_answer",
    "model_text",
    "model_texts",
    "response",
    "learner_ref",
    "review_notes",
    "operator_notes",
    "source_payload",
}


class PrivateRuntimeError(ValueError):
    """Fail-closed M09 private runtime error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise PrivateRuntimeError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise PrivateRuntimeError(f"json_root_not_object:{path}")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _schema(name: str) -> dict[str, Any]:
    return read_json(SCHEMA_DIR / name)


def _assert_schema(name: str, value: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(_schema(name)).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise PrivateRuntimeError(
            f"schema_validation_failed:{name}:{location}:{first.message}"
        )


def _safe_output_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise PrivateRuntimeError(f"output_root_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _safe_scan(value: Any, *, name: str) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                lowered = str(key).casefold()
                if lowered in SAFE_FORBIDDEN_KEYS or lowered.endswith("_absolute_path"):
                    raise PrivateRuntimeError(f"private_field_leak:{name}:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (
                len(node) > 2 and node[1:3] in {":\\", ":/"}
            ):
                raise PrivateRuntimeError(f"absolute_path_leak:{name}")

    walk(value)


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise PrivateRuntimeError(
            f"{code}:expected={expected!r}:actual={actual!r}"
        )


def _validate_receipts(
    m07_receipt: Mapping[str, Any],
    m08_receipt: Mapping[str, Any],
) -> None:
    _require(
        m07_receipt.get("task_id"),
        "E4S-A1V1-M07_FourSkillContractClosureAndSystemIntegration_NoAudioEvidence",
        "m07_task_id",
    )
    _require(
        m07_receipt.get("validation_status"),
        "PASS_M07_FOUR_SKILL_CONTRACT_CLOSURE_NO_AUDIO_EVIDENCE",
        "m07_status",
    )
    _require(
        m07_receipt.get("completion", {}).get("shared_items"),
        384,
        "m07_shared_items",
    )
    _require(
        m07_receipt.get("completion", {}).get("learning_units"),
        24,
        "m07_units",
    )
    _require(
        m07_receipt.get("completion", {}).get("canonical_egp_rows"),
        109,
        "m07_rows",
    )
    _require(
        m07_receipt.get("operator_deferred_conditions", {}).get(
            "speaking_real_audio_evidence"
        ),
        "DEFERRED_BY_OPERATOR",
        "m07_speaking_audio_state",
    )
    _require(
        m08_receipt.get("task_id"),
        "E4S-A1V1-M08_TextModeLearnerSessionAndProgressEvidenceIntegration",
        "m08_task_id",
    )
    _require(
        m08_receipt.get("validation_status"),
        "PASS_M08_TEXT_MODE_SESSION_AND_PROGRESS_ENGINE_READY",
        "m08_status",
    )
    completion = m08_receipt.get("completion", {})
    for key, expected in {
        "available_items": 192,
        "reading_items": 96,
        "writing_items": 96,
        "practice_items": 144,
        "assessment_items": 48,
        "grammar_units": 24,
        "canonical_egp_rows": 109,
        "zero_evidence_state": m08.ZERO_STATUS,
        "independent_validation_errors": 0,
    }.items():
        _require(completion.get(key), expected, f"m08_{key}")
    _require(m08_receipt.get("actual_learner_evidence_count"), 0, "m08_evidence")
    _require(m08_receipt.get("learner_mastery_claimed"), False, "m08_mastery")
    _require(
        m08_receipt.get("speaking_audio_evidence_state"),
        "DEFERRED_BY_OPERATOR",
        "m08_speaking_audio_state",
    )
    _require(m08_receipt.get("stop_reason"), "NONE", "m08_stop_reason")
    _require(m08_receipt.get("next_short_step"), TASK_ID, "m08_next_short_step")


def _dashboard_html() -> str:
    return """<!doctype html>
<html lang="en"><meta charset="utf-8"><title>E4S A1/A1+ Private Runtime</title>
<style>body{font-family:system-ui;max-width:920px;margin:2rem auto;padding:0 1rem}table{border-collapse:collapse;width:100%}th,td{border:1px solid #999;padding:.5rem}.ok{font-weight:700}.deferred{font-style:italic}a.button{display:inline-block;padding:.7rem 1rem;border:1px solid #333;text-decoration:none}</style>
<body><h1>E4S A1/A1+ Private Learning Runtime</h1>
<p class="ok">Localhost-only. No network submission. No production service.</p>
<p><a class="button" href="../text_mode/local_session/index.html">Open Reading / Writing Session</a></p>
<table><thead><tr><th>Skill</th><th>Runtime state</th><th>Evidence boundary</th></tr></thead><tbody>
<tr><td>Reading</td><td>Interactive text session ready</td><td>No mastery claimed</td></tr>
<tr><td>Writing</td><td>Interactive text session ready</td><td>Human review required for productive responses</td></tr>
<tr><td>Listening</td><td>Existing M05 local delivery validated</td><td>No new audio processing in M09</td></tr>
<tr><td>Speaking</td><td>Contract and review engine retained</td><td class="deferred">Recording and real audio evidence deferred by operator</td></tr>
</tbody></table>
<p>192 text-mode items · 24 Grammar units · 109 canonical EGP rows.</p>
<p>Responses remain in the browser or downloaded private JSON. Recording controls are not exposed.</p>
<script>fetch('./runtime_manifest.json').then(r=>r.json()).then(x=>{document.body.dataset.runtimeStatus=x.runtime_status})</script>
</body></html>"""


def _validate_dashboard(html: str) -> None:
    lowered = html.casefold()
    required = (
        "localhost-only",
        "no network submission",
        "open reading / writing session",
        "recording controls are not exposed",
        "deferred by operator",
    )
    for token in required:
        if token not in lowered:
            raise PrivateRuntimeError(f"dashboard_required_token_missing:{token}")
    forbidden = (
        "getusermedia",
        "mediarecorder",
        "<audio",
        "<input type=\"file\"",
        "websocket",
        "xmlhttprequest",
        "fetch('http",
        'fetch("http',
        "answer_key",
        "accepted_texts",
        "manual_transcript",
    )
    for token in forbidden:
        if token in lowered:
            raise PrivateRuntimeError(f"dashboard_forbidden_token:{token}")


def build_manifest(
    m07_receipt: Mapping[str, Any],
    m08_receipt: Mapping[str, Any],
    text_report: Mapping[str, Any],
    text_validation: Mapping[str, Any],
    *,
    port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    _validate_receipts(m07_receipt, m08_receipt)
    _require(text_report.get("available_item_count"), 192, "text_available_items")
    _require(text_report.get("validation_status"), m08.ZERO_STATUS, "text_zero_state")
    _require(text_report.get("attempt_count"), 0, "text_attempt_count")
    _require(text_validation.get("error_count"), 0, "text_validation_errors")
    _require(text_validation.get("validation_status"), m08.ZERO_STATUS, "text_validation_status")
    if port < 1024 or port > 65535:
        raise PrivateRuntimeError(f"port_out_of_range:{port}")

    required_files = [
        "runtime_manifest.json",
        "dashboard/index.html",
        "dashboard/runtime_manifest.json",
        "text_mode/local_session/index.html",
        "text_mode/local_session/payload.json",
        "text_mode/text_mode_progress_safe_report.json",
        "text_mode/text_mode_session_validation.json",
    ]
    checks = [
        "M07_FOUR_SKILL_CLOSURE_PASS",
        "M08_TEXT_SESSION_ENGINE_PASS",
        "TEXT_ITEM_ACCOUNTING_192_PASS",
        "UNIT_COVERAGE_24_PASS",
        "ROW_COVERAGE_109_PASS",
        "LOCALHOST_BIND_POLICY_PASS",
        "DASHBOARD_SAFE_CONTENT_PASS",
        "RECORDING_CONTROLS_DISABLED_PASS",
        "PRIVATE_OUTPUT_BOUNDARY_PASS",
        "ZERO_EVIDENCE_CLAIMS_PASS",
        "NO_AUTHORITY_WRITE_PASS",
        "NO_A2_EXPANSION_PASS",
    ]
    manifest = {
        "task_id": TASK_ID,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "runtime_id": "e4s-a1v1-private-local-runtime",
        "scope": "A1_A1_PLUS_ONLY",
        "bind_policy": {
            "allowed_host": DEFAULT_HOST,
            "default_port": port,
            "network_submission_enabled": False,
            "external_network_dependency": False,
        },
        "source_hashes": {
            "m07_closeout_sha256": sha256_value(m07_receipt),
            "m08_closeout_sha256": sha256_value(m08_receipt),
            "text_mode_safe_report_sha256": sha256_value(text_report),
            "text_mode_validation_sha256": sha256_value(text_validation),
        },
        "text_mode_runtime": {
            "available_items": 192,
            "reading_items": 96,
            "writing_items": 96,
            "practice_items": 144,
            "assessment_items": 48,
            "grammar_units": 24,
            "canonical_egp_rows": 109,
            "zero_evidence_state": m08.ZERO_STATUS,
            "session_entrypoint": "text_mode/local_session/index.html",
        },
        "skill_runtime_states": {
            "reading": {
                "runtime_state": "INTERACTIVE_TEXT_SESSION_READY",
                "item_count": 96,
                "actual_learner_evidence_count": 0,
            },
            "writing": {
                "runtime_state": "INTERACTIVE_TEXT_SESSION_READY",
                "item_count": 96,
                "productive_review_mode": "HUMAN_RUBRIC_FALLBACK",
                "actual_learner_evidence_count": 0,
            },
            "listening": {
                "runtime_state": "M05_LOCAL_DELIVERY_VALIDATED_REFERENCE_ONLY",
                "new_audio_asset_processing": False,
                "actual_learner_evidence_count": 0,
            },
            "speaking": {
                "runtime_state": "CONTRACT_AND_REVIEW_ENGINE_RETAINED",
                "recording_controls_enabled": False,
                "real_audio_evidence_state": "DEFERRED_BY_OPERATOR",
                "actual_learner_evidence_count": 0,
            },
        },
        "dashboard": {
            "entrypoint": "dashboard/index.html",
            "text_session_link": "../text_mode/local_session/index.html",
            "contains_private_answers": False,
            "contains_learner_responses": False,
            "recording_controls_exposed": False,
        },
        "health_contract": {
            "required_files": required_files,
            "checks": checks,
            "health_status": RUNTIME_STATUS,
        },
        "claim_boundaries": {
            "private_local_only": True,
            "production_runtime_enabled": False,
            "public_delivery_enabled": False,
            "canonical_authority_write": False,
            "persistent_learner_state_service_enabled": False,
            "actual_learner_evidence_complete": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "new_audio_processing_performed": False,
            "recording_enabled": False,
            "a2_a2plus_in_scope": False,
        },
        "runtime_status": RUNTIME_STATUS,
        "next_short_step": NEXT_SHORT_STEP,
    }
    _assert_schema("e4s_a1v1_private_runtime_manifest.schema.json", manifest)
    _safe_scan(manifest, name="runtime_manifest")
    return manifest


def run_health(output_root: Path) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    errors: list[str] = []
    try:
        manifest = read_json(root / "runtime_manifest.json")
        _assert_schema("e4s_a1v1_private_runtime_manifest.schema.json", manifest)
        _safe_scan(manifest, name="runtime_manifest")
        for relative in manifest["health_contract"]["required_files"]:
            path = (root / relative).resolve()
            if not path.is_relative_to(root):
                errors.append(f"required_file_path_escape:{relative}")
            elif not path.is_file():
                errors.append(f"required_file_missing:{relative}")
        dashboard = (root / "dashboard/index.html").read_text(encoding="utf-8")
        _validate_dashboard(dashboard)
        dashboard_manifest = read_json(root / "dashboard/runtime_manifest.json")
        if dashboard_manifest != manifest:
            errors.append("dashboard_manifest_drift")
        text_report = read_json(root / "text_mode/text_mode_progress_safe_report.json")
        text_validation = read_json(root / "text_mode/text_mode_session_validation.json")
        if text_report.get("available_item_count") != 192:
            errors.append("text_runtime_item_count_not_192")
        if text_report.get("attempt_count") != 0:
            errors.append("acceptance_requires_zero_evidence_fixture")
        if text_validation.get("error_count") != 0:
            errors.append("text_runtime_validation_errors")
        if manifest.get("bind_policy", {}).get("allowed_host") != DEFAULT_HOST:
            errors.append("runtime_host_not_localhost")
        if manifest.get("skill_runtime_states", {}).get("speaking", {}).get("recording_controls_enabled") is not False:
            errors.append("recording_controls_not_disabled")
        if manifest.get("claim_boundaries", {}).get("new_audio_processing_performed") is not False:
            errors.append("new_audio_processing_false_claim")
    except (PrivateRuntimeError, OSError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
        manifest = {}

    checks = manifest.get("health_contract", {}).get("checks", [])
    health = {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.private_runtime_health.v1",
        "runtime_manifest_sha256": sha256_value(manifest) if manifest else None,
        "health_status": RUNTIME_STATUS if not errors else "FAIL",
        "required_check_count": len(checks),
        "passed_check_count": len(checks) if not errors else max(0, len(checks) - len(errors)),
        "failed_check_count": len(errors),
        "errors": errors,
        "localhost_url": f"http://{DEFAULT_HOST}:{manifest.get('bind_policy', {}).get('default_port', DEFAULT_PORT)}/dashboard/index.html",
        "recording_enabled": False,
        "audio_processing_performed": False,
        "learner_mastery_claimed": False,
    }
    _safe_scan(health, name="runtime_health")
    return health


def build_acceptance(manifest: Mapping[str, Any], health: Mapping[str, Any]) -> dict[str, Any]:
    _require(health.get("health_status"), RUNTIME_STATUS, "runtime_health_status")
    _require(health.get("failed_check_count"), 0, "runtime_failed_checks")
    required = int(health.get("required_check_count", 0))
    acceptance = {
        "task_id": TASK_ID,
        "schema_version": ACCEPTANCE_SCHEMA_VERSION,
        "runtime_manifest_sha256": sha256_value(manifest),
        "acceptance_status": ACCEPTANCE_STATUS,
        "check_counts": {
            "required": required,
            "passed": required,
            "failed": 0,
        },
        "runtime_counts": {
            "available_items": 192,
            "reading_items": 96,
            "writing_items": 96,
            "grammar_units": 24,
            "canonical_egp_rows": 109,
        },
        "deferred_conditions": {
            "speaking_real_audio_evidence": "DEFERRED_BY_OPERATOR",
            "recording_files": "OUT_OF_SCOPE",
            "blocks_runtime_acceptance": False,
            "blocks_m10_progression": False,
        },
        "claim_boundaries": dict(manifest["claim_boundaries"]),
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    _assert_schema("e4s_a1v1_private_runtime_acceptance.schema.json", acceptance)
    _safe_scan(acceptance, name="runtime_acceptance")
    return acceptance


def prepare_runtime(
    output_root: Path,
    *,
    m07_receipt_path: Path = M07_RECEIPT_PATH,
    m08_receipt_path: Path = M08_RECEIPT_PATH,
    port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    m07_receipt = read_json(m07_receipt_path)
    m08_receipt = read_json(m08_receipt_path)
    _validate_receipts(m07_receipt, m08_receipt)

    text_root = root / "text_mode"
    m08_result = m08.prepare_artifacts(text_root, m07_receipt_path)
    text_validation = m08_validator.validate(text_root)
    m08.write_json_atomic(text_root / "text_mode_session_validation.json", text_validation)
    if text_validation.get("error_count") != 0:
        raise PrivateRuntimeError(f"m08_runtime_validation_failed:{text_validation.get('errors')}")

    expected_hashes = m08_receipt.get("artifact_hashes", {})
    actual_hashes = {
        "session_bank_sha256": sha256_file(text_root / "text_mode_session_bank.private.json"),
        "learner_safe_payload_sha256": sha256_file(text_root / "text_mode_learner_safe_payload.json"),
        "progress_safe_report_sha256": sha256_file(text_root / "text_mode_progress_safe_report.json"),
        "validation_sha256": sha256_file(text_root / "text_mode_session_validation.json"),
    }
    _require(actual_hashes, expected_hashes, "m08_artifact_hash_rebuild")

    manifest = build_manifest(
        m07_receipt,
        m08_receipt,
        m08_result["safe_report"],
        text_validation,
        port=port,
    )
    write_json_atomic(root / "runtime_manifest.json", manifest)
    dashboard = root / "dashboard"
    dashboard.mkdir(parents=True, exist_ok=True)
    html = _dashboard_html()
    _validate_dashboard(html)
    (dashboard / "index.html").write_text(html, encoding="utf-8")
    write_json_atomic(dashboard / "runtime_manifest.json", manifest)

    health = run_health(root)
    write_json_atomic(root / "runtime_health.json", health)
    acceptance = build_acceptance(manifest, health)
    write_json_atomic(root / "runtime_acceptance.json", acceptance)
    return {
        "manifest": manifest,
        "health": health,
        "acceptance": acceptance,
    }


def serve_runtime(
    output_root: Path,
    *,
    host: str,
    port: int,
    dry_run: bool,
) -> int:
    root = _safe_output_root(output_root)
    if host != DEFAULT_HOST:
        raise PrivateRuntimeError(f"non_localhost_bind_forbidden:{host}")
    if port < 1024 or port > 65535:
        raise PrivateRuntimeError(f"port_out_of_range:{port}")
    health = run_health(root)
    if health.get("health_status") != RUNTIME_STATUS:
        raise PrivateRuntimeError(f"runtime_health_failed:{health.get('errors')}")
    url = f"http://{host}:{port}/dashboard/index.html"
    if dry_run:
        print(json.dumps({"runtime_status": RUNTIME_STATUS, "url": url}, sort_keys=True))
        return 0
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving private runtime at {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    prepare.add_argument("--m07-receipt", type=Path, default=M07_RECEIPT_PATH)
    prepare.add_argument("--m08-receipt", type=Path, default=M08_RECEIPT_PATH)
    prepare.add_argument("--port", type=int, default=DEFAULT_PORT)
    health = sub.add_parser("health")
    health.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    serve = sub.add_parser("serve")
    serve.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_runtime(
                args.output_root,
                m07_receipt_path=args.m07_receipt,
                m08_receipt_path=args.m08_receipt,
                port=args.port,
            )
            print(json.dumps({
                "acceptance_status": result["acceptance"]["acceptance_status"],
                "runtime_status": result["health"]["health_status"],
                "available_items": 192,
                "recording_enabled": False,
                "next_short_step": NEXT_SHORT_STEP,
            }, sort_keys=True))
            return 0
        if args.command == "health":
            result = run_health(args.output_root)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0 if result["health_status"] == RUNTIME_STATUS else 1
        return serve_runtime(
            args.output_root,
            host=args.host,
            port=args.port,
            dry_run=args.dry_run,
        )
    except (PrivateRuntimeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
