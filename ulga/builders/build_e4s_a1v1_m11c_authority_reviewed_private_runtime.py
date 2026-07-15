#!/usr/bin/env python3
"""Integrate the M11B Authority-reviewed bank into a localhost text runtime.

The complete M08 192-item private bank remains the scoring authority. The
learner-facing M11C projection exposes only items whose grammar unit is present
in the 23-unit M11B private-ready allowlist. Eight `will` items remain in the
private scoring source but are not selectable, queryable, or learner-facing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from copy import deepcopy
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
from ulga.builders import build_e4s_a1v1_m11b_authority_exception_resolution as m11b  # noqa: E402
from ulga.validators import validate_e4s_a1v1_m08_text_mode_learner_session as m08_validator  # noqa: E402

TASK_ID = "E4S-A1V1-M11C_AuthorityReviewedPrivateBankConsumerAndRuntimeIntegration"
SCHEMA_VERSION_MANIFEST = "e4s.a1v1.m11c_authority_runtime_manifest.v1"
SCHEMA_VERSION_REPORT = "e4s.a1v1.m11c_authority_runtime_safe_report.v1"
RUNTIME_STATUS = "PASS_M11C_AUTHORITY_REVIEWED_PRIVATE_RUNTIME_READY"
NEXT_SHORT_STEP = "E4S-A1V1-M11D_AuthorityReviewedPrivateRuntimeAcceptanceAndA1A1PlusCloseout"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/runtime/m11c"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8771
SCHEMA_DIR = SOURCE_REPO_ROOT / "ulga/schemas"
DEFERRED_GRAMMAR_ID = "GRAMMAR_WILL_FUTURE_A1"
EXPECTED_COUNTS = {
    "source_items": 192,
    "selectable_items": 184,
    "excluded_items": 8,
    "reading_items": 92,
    "writing_items": 92,
    "practice_items": 138,
    "assessment_items": 46,
    "grammar_units": 23,
    "canonical_egp_rows": 107,
}


class AuthorityRuntimeError(ValueError):
    """Fail-closed M11C runtime error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorityRuntimeError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise AuthorityRuntimeError(f"json_root_not_object:{path}")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
        raise AuthorityRuntimeError(f"schema_validation_failed:{name}:{location}:{first.message}")


def _safe_output_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise AuthorityRuntimeError(f"output_root_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise AuthorityRuntimeError(f"{code}:expected={expected!r}:actual={actual!r}")


def _validate_learner_payload(payload: Mapping[str, Any], allowed_ids: set[str]) -> None:
    items = payload.get("items", [])
    _require(payload.get("item_count"), 184, "learner_payload_item_count")
    if len(items) != 184 or len({row.get("item_id") for row in items}) != 184:
        raise AuthorityRuntimeError("learner_payload_identity_not_184")
    unit_ids = {str(row.get("grammar_unit_id")) for row in items}
    if unit_ids != allowed_ids:
        raise AuthorityRuntimeError("learner_payload_unit_allowlist_drift")
    if DEFERRED_GRAMMAR_ID in unit_ids:
        raise AuthorityRuntimeError("deferred_will_item_exposed")
    forbidden_keys = {
        "answer",
        "answer_key",
        "accepted_texts",
        "accepted_sequence",
        "private_scoring_contract",
        "model_answer",
        "model_texts",
        "correct_token_sequence",
        "correct_morphology_parts",
    }

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden_keys:
                    raise AuthorityRuntimeError(f"learner_payload_private_field:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(payload)


def _dashboard_html() -> str:
    return """<!doctype html>
<html lang="en"><meta charset="utf-8"><title>E4S Authority-Reviewed Runtime</title>
<style>body{font-family:system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}table{border-collapse:collapse;width:100%}th,td{border:1px solid #999;padding:.5rem}.ok{font-weight:700}.deferred{font-style:italic}</style>
<body><h1>E4S A1/A1+ Authority-Reviewed Private Runtime</h1>
<p class="ok">Localhost-only. No network submission. No production service.</p>
<p><a href="../authority_session/index.html">Open Authority-Reviewed Reading / Writing Session</a></p>
<table><tr><th>Selection</th><th>Status</th></tr>
<tr><td>Private-ready Grammar units</td><td>23</td></tr>
<tr><td>Selectable text items</td><td>184</td></tr>
<tr><td>Canonical EGP rows available</td><td>107</td></tr>
<tr><td>GRAMMAR_WILL_FUTURE_A1</td><td class="deferred">Deferred at Cambridge Flyers/A2 child-path ceiling; canonical EGP mapping preserved</td></tr></table>
<p>Responses remain local. Recording controls, audio processing, public delivery, and mastery claims are disabled.</p>
<script>fetch('./runtime_manifest.json').then(r=>r.json()).then(x=>{document.body.dataset.runtimeStatus=x.runtime_status})</script>
</body></html>"""


def _validate_dashboard(html: str) -> None:
    lowered = html.casefold()
    for token in (
        "localhost-only",
        "authority-reviewed reading / writing session",
        "private-ready grammar units",
        "deferred at cambridge flyers/a2",
        "canonical egp mapping preserved",
        "recording controls",
    ):
        if token not in lowered:
            raise AuthorityRuntimeError(f"dashboard_required_token_missing:{token}")
    for token in (
        "mediarecorder",
        "getusermedia",
        "<audio",
        "<input type=\"file\"",
        "websocket",
        "xmlhttprequest",
        "fetch('http",
        'fetch("http',
        "answer_key",
        "accepted_texts",
    ):
        if token in lowered:
            raise AuthorityRuntimeError(f"dashboard_forbidden_token:{token}")


def build_runtime_artifacts(output_root: Path, *, port: int = DEFAULT_PORT) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    if port < 1024 or port > 65535:
        raise AuthorityRuntimeError(f"port_out_of_range:{port}")

    resolution_matrix, authority_bank, authority_report = m11b.build_artifacts()
    _require(authority_report.get("validation_status"), "PASS_M11B_AUTHORITY_EXCEPTIONS_RESOLVED", "m11b_status")
    _require(authority_bank.get("reviewed_unit_count"), 23, "m11b_reviewed_units")
    _require(authority_bank.get("canonical_egp_row_count"), 107, "m11b_reviewed_rows")
    allowed_ids = {str(row["grammar_unit_id"]) for row in authority_bank["reviewed_units"]}
    if len(allowed_ids) != 23 or DEFERRED_GRAMMAR_ID in allowed_ids:
        raise AuthorityRuntimeError("m11b_allowlist_invalid")

    source_root = root / "source_m08"
    source = m08.prepare_artifacts(source_root)
    source_validation = m08_validator.validate(source_root)
    m08.write_json_atomic(source_root / "text_mode_session_validation.json", source_validation)
    if source_validation.get("error_count") != 0:
        raise AuthorityRuntimeError(f"m08_source_validation_failed:{source_validation.get('errors')}")
    source_bank = source["bank"]
    source_payload = source["payload"]
    _require(source_bank.get("item_count"), 192, "m08_source_items")
    _require(source_bank.get("unit_count"), 24, "m08_source_units")

    source_items = list(source_bank["items"])
    selected_private_items = [row for row in source_items if row["grammar_unit_id"] in allowed_ids]
    excluded_private_items = [row for row in source_items if row["grammar_unit_id"] not in allowed_ids]
    if len(selected_private_items) != 184 or len(excluded_private_items) != 8:
        raise AuthorityRuntimeError("m08_authority_filter_item_distribution_drift")
    if {row["grammar_unit_id"] for row in excluded_private_items} != {DEFERRED_GRAMMAR_ID}:
        raise AuthorityRuntimeError("excluded_item_unit_not_only_will")

    selected_ids = {row["item_id"] for row in selected_private_items}
    learner_items = [deepcopy(row) for row in source_payload["items"] if row["item_id"] in selected_ids]
    learner_payload = {
        "task_id": source_payload["task_id"],
        "schema_version": source_payload["schema_version"],
        "session_bank_sha256": source_payload["session_bank_sha256"],
        "item_count": len(learner_items),
        "audio_required": False,
        "network_submission_enabled": False,
        "authority_selection_task_id": TASK_ID,
        "authority_selection_sha256": sha256_value(authority_bank),
        "items": learner_items,
    }
    _validate_learner_payload(learner_payload, allowed_ids)

    skill_counts = Counter(row["skill"] for row in selected_private_items)
    role_counts = Counter(row["item_role"] for row in selected_private_items)
    row_ids = {
        row_id
        for row in selected_private_items
        for row_id in row["canonical_egp_row_ids"]
    }
    actual_counts = {
        "source_items": len(source_items),
        "selectable_items": len(selected_private_items),
        "excluded_items": len(excluded_private_items),
        "reading_items": skill_counts["reading"],
        "writing_items": skill_counts["writing"],
        "practice_items": role_counts["practice"],
        "assessment_items": role_counts["assessment"],
        "grammar_units": len({row["grammar_unit_id"] for row in selected_private_items}),
        "canonical_egp_rows": len(row_ids),
    }
    if actual_counts != EXPECTED_COUNTS:
        raise AuthorityRuntimeError(f"authority_runtime_count_drift:{actual_counts}")

    query_items = [
        {
            "item_id": row["item_id"],
            "shared_item_id": row["shared_item_id"],
            "grammar_unit_id": row["grammar_unit_id"],
            "canonical_egp_row_ids": list(row["canonical_egp_row_ids"]),
            "internal_stage": row["internal_stage"],
            "skill": row["skill"],
            "item_role": row["item_role"],
            "evidence_dimension": row["evidence_dimension"],
            "task_type": row["task_type"],
            "authority_resolution": next(
                unit["authority_resolution"]
                for unit in authority_bank["reviewed_units"]
                if unit["grammar_unit_id"] == row["grammar_unit_id"]
            ),
            "selectable": True,
        }
        for row in selected_private_items
    ]
    query_index = {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.m11c_authority_runtime_query.v1",
        "item_count": len(query_items),
        "unit_count": 23,
        "canonical_egp_row_count": len(row_ids),
        "items": query_items,
        "items_sha256": sha256_value(query_items),
        "deferred_units": deepcopy(authority_bank["deferred_units"]),
    }

    required_files = [
        "runtime_manifest.json",
        "dashboard/index.html",
        "dashboard/runtime_manifest.json",
        "authority_session/index.html",
        "authority_session/payload.json",
        "authority_runtime_query_index.json",
        "source_m08/text_mode_session_bank.private.json",
        "source_m08/text_mode_session_validation.json",
    ]
    checks = [
        "M11B_PRIVATE_BANK_PASS",
        "M08_SOURCE_BANK_PASS",
        "AUTHORITY_ALLOWLIST_23_PASS",
        "SELECTABLE_ITEMS_184_PASS",
        "EXCLUDED_WILL_ITEMS_8_PASS",
        "ROW_COVERAGE_107_PASS",
        "M08_ATTEMPT_HASH_COMPATIBILITY_PASS",
        "LEARNER_SAFE_PAYLOAD_PASS",
        "LOCALHOST_BIND_POLICY_PASS",
        "DASHBOARD_SAFE_CONTENT_PASS",
        "NO_AUTHORITY_WRITE_PASS",
        "NO_A2_PROMOTION_PASS",
        "NO_RECORDING_OR_AUDIO_PASS",
    ]
    manifest = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION_MANIFEST,
        "runtime_id": "e4s-a1v1-authority-reviewed-private-runtime",
        "scope": "A1_A1_PLUS_PRIVATE_CHILD_PATH_ONLY",
        "bind_policy": {
            "allowed_host": DEFAULT_HOST,
            "default_port": port,
            "network_submission_enabled": False,
            "external_network_dependency": False,
        },
        "source_hashes": {
            "m11b_resolution_matrix_sha256": sha256_value(resolution_matrix),
            "m11b_private_bank_sha256": sha256_value(authority_bank),
            "m08_source_bank_sha256": sha256_value(source_bank),
            "m08_source_validation_sha256": sha256_value(source_validation),
            "learner_safe_payload_sha256": sha256_value(learner_payload),
            "query_index_sha256": sha256_value(query_index),
        },
        "authority_selection": {
            "private_ready_units": 23,
            "private_ready_rows": 107,
            "deferred_units": 1,
            "unresolved_exceptions": 0,
            "selection_mode": "M11B_AUTHORITY_READY_ALLOWLIST",
        },
        "text_mode_runtime": {
            **actual_counts,
            "session_entrypoint": "authority_session/index.html",
            "attempt_registry_compatibility": "M08_FULL_BANK_HASH_COMPATIBLE",
        },
        "deferred_units": [{
            "grammar_unit_id": DEFERRED_GRAMMAR_ID,
            "status": "DEFERRED_CAMBRIDGE_FLYERS_A2_CEILING",
            "excluded_item_count": 8,
            "canonical_egp_mapping_preserved": True,
        }],
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
            "canonical_egp_mapping_changed": False,
            "persistent_learner_state_service_enabled": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "new_audio_processing_performed": False,
            "recording_enabled": False,
            "a2_content_promoted": False,
        },
        "runtime_status": RUNTIME_STATUS,
        "next_short_step": NEXT_SHORT_STEP,
    }
    _assert_schema("e4s_a1v1_m11c_authority_runtime_manifest.schema.json", manifest)

    write_json_atomic(root / "runtime_manifest.json", manifest)
    write_json_atomic(root / "authority_runtime_query_index.json", query_index)
    session = root / "authority_session"
    session.mkdir(parents=True, exist_ok=True)
    (session / "index.html").write_text(m08._local_session_html(), encoding="utf-8")
    write_json_atomic(session / "payload.json", learner_payload)
    dashboard = root / "dashboard"
    dashboard.mkdir(parents=True, exist_ok=True)
    html = _dashboard_html()
    _validate_dashboard(html)
    (dashboard / "index.html").write_text(html, encoding="utf-8")
    write_json_atomic(dashboard / "runtime_manifest.json", manifest)

    health = run_health(root)
    write_json_atomic(root / "runtime_health.json", health)
    if health["failed_check_count"]:
        raise AuthorityRuntimeError(f"runtime_health_failed:{health['errors']}")
    report = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION_REPORT,
        "private_ready_unit_count": 23,
        "private_ready_row_count": 107,
        "selectable_item_count": 184,
        "excluded_item_count": 8,
        "skill_counts": {"reading": 92, "writing": 92},
        "role_counts": {"practice": 138, "assessment": 46},
        "deferred_unit_count": 1,
        "health_check_count": health["required_check_count"],
        "failed_health_check_count": 0,
        "claim_boundaries": {
            "metadata_only_report": True,
            "private_answers_included": False,
            "learner_responses_included": False,
            "canonical_authority_write": False,
            "canonical_egp_mapping_changed": False,
            "public_delivery": False,
            "learner_mastery_claimed": False,
            "a2_content_promoted": False,
            "audio_or_recording_processed": False,
        },
        "validation_status": RUNTIME_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
        "errors": [],
    }
    m11b.m11a._safe_scan(report, name="m11c_runtime_safe_report")
    _assert_schema("e4s_a1v1_m11c_authority_runtime_safe_report.schema.json", report)
    write_json_atomic(root / "authority_runtime_safe_report.json", report)
    return {
        "manifest": manifest,
        "health": health,
        "safe_report": report,
        "query_index": query_index,
        "learner_payload": learner_payload,
        "authority_bank": authority_bank,
    }


def run_health(output_root: Path) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    try:
        manifest = read_json(root / "runtime_manifest.json")
        _assert_schema("e4s_a1v1_m11c_authority_runtime_manifest.schema.json", manifest)
        for relative in manifest["health_contract"]["required_files"]:
            path = (root / relative).resolve()
            if not path.is_relative_to(root):
                errors.append(f"required_file_path_escape:{relative}")
            elif not path.is_file():
                errors.append(f"required_file_missing:{relative}")
        dashboard_html = (root / "dashboard/index.html").read_text(encoding="utf-8")
        _validate_dashboard(dashboard_html)
        if read_json(root / "dashboard/runtime_manifest.json") != manifest:
            errors.append("dashboard_manifest_drift")
        payload = read_json(root / "authority_session/payload.json")
        query = read_json(root / "authority_runtime_query_index.json")
        allowed_ids = {str(row["grammar_unit_id"]) for row in query["items"]}
        _validate_learner_payload(payload, allowed_ids)
        if query.get("item_count") != 184:
            errors.append("query_item_count_not_184")
        if query.get("unit_count") != 23:
            errors.append("query_unit_count_not_23")
        if query.get("canonical_egp_row_count") != 107:
            errors.append("query_row_count_not_107")
        if any(row.get("grammar_unit_id") == DEFERRED_GRAMMAR_ID for row in query.get("items", [])):
            errors.append("deferred_will_query_leak")
        source_bank = read_json(root / "source_m08/text_mode_session_bank.private.json")
        if payload.get("session_bank_sha256") != sha256_value(source_bank):
            errors.append("m08_attempt_registry_hash_compatibility_drift")
        source_validation = read_json(root / "source_m08/text_mode_session_validation.json")
        if source_validation.get("error_count") != 0:
            errors.append("m08_source_validation_errors")
        if manifest.get("bind_policy", {}).get("allowed_host") != DEFAULT_HOST:
            errors.append("runtime_host_not_localhost")
        boundaries = manifest.get("claim_boundaries", {})
        for key in (
            "production_runtime_enabled",
            "public_delivery_enabled",
            "canonical_authority_write",
            "canonical_egp_mapping_changed",
            "persistent_learner_state_service_enabled",
            "learner_mastery_claimed",
            "retention_confirmed",
            "new_audio_processing_performed",
            "recording_enabled",
            "a2_content_promoted",
        ):
            if boundaries.get(key) is not False:
                errors.append(f"runtime_claim_boundary_drift:{key}")
    except (AuthorityRuntimeError, OSError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    checks = manifest.get("health_contract", {}).get("checks", [])
    return {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.m11c_authority_runtime_health.v1",
        "runtime_manifest_sha256": sha256_value(manifest) if manifest else None,
        "health_status": RUNTIME_STATUS if not errors else "FAIL",
        "required_check_count": len(checks),
        "passed_check_count": len(checks) if not errors else max(0, len(checks) - len(errors)),
        "failed_check_count": len(errors),
        "errors": errors,
        "localhost_url": f"http://{DEFAULT_HOST}:{manifest.get('bind_policy', {}).get('default_port', DEFAULT_PORT)}/dashboard/index.html",
        "selectable_item_count": manifest.get("text_mode_runtime", {}).get("selectable_items", 0),
        "deferred_unit_count": len(manifest.get("deferred_units", [])),
        "recording_enabled": False,
        "audio_processing_performed": False,
        "learner_mastery_claimed": False,
    }


def serve_runtime(output_root: Path, *, host: str, port: int, dry_run: bool) -> int:
    root = _safe_output_root(output_root)
    if host != DEFAULT_HOST:
        raise AuthorityRuntimeError(f"non_localhost_bind_forbidden:{host}")
    if port < 1024 or port > 65535:
        raise AuthorityRuntimeError(f"port_out_of_range:{port}")
    health = run_health(root)
    if health.get("health_status") != RUNTIME_STATUS:
        raise AuthorityRuntimeError(f"runtime_health_failed:{health.get('errors')}")
    url = f"http://{host}:{port}/dashboard/index.html"
    if dry_run:
        print(json.dumps({"runtime_status": RUNTIME_STATUS, "url": url}, sort_keys=True))
        return 0
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving authority-reviewed private runtime at {url}")
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
            result = build_runtime_artifacts(args.output_root, port=args.port)
            payload = {
                "runtime_status": result["safe_report"]["validation_status"],
                "private_ready_units": result["safe_report"]["private_ready_unit_count"],
                "selectable_items": result["safe_report"]["selectable_item_count"],
                "private_ready_rows": result["safe_report"]["private_ready_row_count"],
                "deferred_units": result["safe_report"]["deferred_unit_count"],
                "stop_reason": result["safe_report"]["stop_reason"],
                "next_short_step": result["safe_report"]["next_short_step"],
            }
            print(json.dumps(payload, sort_keys=True))
            return 0
        if args.command == "health":
            result = run_health(args.output_root)
            print(json.dumps(result, sort_keys=True))
            return 0 if result["health_status"] == RUNTIME_STATUS else 1
        return serve_runtime(args.output_root, host=args.host, port=args.port, dry_run=args.dry_run)
    except (AuthorityRuntimeError, m11b.AuthorityExceptionError, m08.TextModeSessionError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
