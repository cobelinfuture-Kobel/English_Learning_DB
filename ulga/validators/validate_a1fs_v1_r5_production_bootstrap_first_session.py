#!/usr/bin/env python3
"""Independently validate the R5 production bootstrap and first-session artifacts."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5
from ulga.builders import build_a1fs_v1_r5_production_bootstrap_first_session as bootstrap
from ulga.validators.validate_a1fs_v1_r3r4_authority_reviewed_production_population import validate as validate_population
from ulga.validators.validate_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector import validate_database

SAFE_FORBIDDEN_KEYS = {
    "learner_id", "session_id", "access_token", "prompt", "response", "answer",
    "answer_key", "accepted_texts", "accepted_sequence", "learner_contract",
    "private_scoring_contract", "operator_review", "options", "context",
}


def _safe_scan(value: Any, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in SAFE_FORBIDDEN_KEYS:
                errors.append(f"safe_private_field:{key}")
            _safe_scan(child, errors)
    elif isinstance(value, list):
        for child in value:
            _safe_scan(child, errors)
    elif isinstance(value, str):
        if Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":/", ":\\"}):
            errors.append("safe_absolute_path")


def validate(
    *, database_path: Path, ontology_path: Path, graph_path: Path, output_root: Path,
    consumer_path: Path | None = None, consumer_search_root: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    root = Path(output_root)
    private_path = root / bootstrap.PRIVATE_RECEIPT
    safe_path = root / bootstrap.SAFE_REPORT
    session_path = root / bootstrap.SESSION_PAYLOAD
    launcher_path = root / bootstrap.WINDOWS_LAUNCHER
    try:
        private = bootstrap.read_json(private_path, "private_receipt")
        safe = bootstrap.read_json(safe_path, "safe_report")
        stored_session = bootstrap.read_json(session_path, "session_payload")
    except bootstrap.ProductionBootstrapError as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [str(exc)]}

    private_core = {key: value for key, value in private.items() if key != "receipt_sha256"}
    safe_core = {key: value for key, value in safe.items() if key != "report_sha256"}
    if private.get("task_id") != bootstrap.TASK_ID or private.get("schema_version") != bootstrap.SCHEMA_VERSION:
        errors.append("private_identity_invalid")
    if safe.get("task_id") != bootstrap.TASK_ID or safe.get("schema_version") != bootstrap.SCHEMA_VERSION:
        errors.append("safe_identity_invalid")
    if private.get("validation_status") != bootstrap.STATUS or safe.get("validation_status") != bootstrap.STATUS:
        errors.append("bootstrap_status_invalid")
    if private.get("receipt_sha256") != bootstrap.digest(private_core):
        errors.append("private_receipt_digest_invalid")
    if safe.get("report_sha256") != bootstrap.digest(safe_core):
        errors.append("safe_report_digest_invalid")
    if safe.get("source_bindings", {}).get("private_receipt_sha256") != private.get("receipt_sha256"):
        errors.append("safe_private_binding_invalid")
    if safe.get("stop_reason") != "REAL_LEARNER_SESSION_EXECUTION_REQUIRED":
        errors.append("stop_reason_invalid")
    if safe.get("next_short_step") != bootstrap.NEXT_SHORT_STEP:
        errors.append("next_short_step_invalid")
    _safe_scan(safe, errors)

    for key in (
        "real_learner_evidence_claimed", "mastery_written", "retention_confirmed",
        "a2_unlocked", "public_delivery", "network_submission_enabled",
        "audio_or_recording_completed", "qwen_required",
    ):
        if private.get("claim_boundaries", {}).get(key) is not False:
            errors.append(f"private_boundary_broken:{key}")
        if safe.get("claim_boundaries", {}).get(key) is not False:
            errors.append(f"safe_boundary_broken:{key}")

    if not launcher_path.is_file():
        errors.append("windows_launcher_missing")
    else:
        launcher = launcher_path.read_text(encoding="utf-8")
        for required in ("serve --database", "--session-id", "--token", "--port"):
            if required not in launcher:
                errors.append(f"windows_launcher_token_missing:{required}")
        for forbidden in ("http://", "https://", "curl ", "Invoke-WebRequest", "Invoke-RestMethod"):
            if forbidden.casefold() in launcher.casefold():
                errors.append(f"windows_launcher_network_forbidden:{forbidden}")

    try:
        consumer = Path(consumer_path).resolve() if consumer_path else bootstrap.discover_consumer(
            database_path=database_path,
            graph_path=graph_path,
            search_root=consumer_search_root or (bootstrap.REPO_ROOT / ".local"),
        )
        population_result = validate_population(
            ontology_path=ontology_path,
            graph_path=graph_path,
            consumer_path=consumer,
            output_root=root / "r3r4",
        )
        if population_result.get("error_count") != 0:
            errors.extend(f"population:{row}" for row in population_result.get("errors", []))
        bindings = private.get("source_bindings", {})
        actual_bindings = {
            "ontology_sha256": bootstrap.file_digest(ontology_path),
            "graph_sha256": bootstrap.file_digest(graph_path),
            "consumer_sha256": bootstrap.file_digest(consumer),
            "session_payload_sha256": bootstrap.file_digest(session_path),
            "launcher_sha256": bootstrap.file_digest(launcher_path),
        }
        for key, value in actual_bindings.items():
            if bindings.get(key) != value:
                errors.append(f"source_binding_invalid:{key}")
        bank = bootstrap.read_json(root / "r3r4" / population.BANK_OUTPUT, "bank")
        supply = bootstrap.read_json(root / "r3r4" / population.SUPPLY_OUTPUT, "supply")
        if bindings.get("practice_bank_sha256") != bank.get("bank_sha256"):
            errors.append("practice_bank_binding_invalid")
        if bindings.get("supply_report_sha256") != supply.get("report_sha256"):
            errors.append("supply_report_binding_invalid")
    except (bootstrap.ProductionBootstrapError, OSError) as exc:
        errors.append(f"source_validation_failed:{exc}")

    database_result = validate_database(database_path)
    if database_result.get("error_count") != 0:
        errors.extend(f"database:{row}" for row in database_result.get("errors", []))
    try:
        with sqlite3.connect(database_path) as connection:
            connection.row_factory = sqlite3.Row
            session = connection.execute(
                "SELECT * FROM edge_sessions WHERE session_id=?", (private.get("session_id"),)
            ).fetchone()
            if not session:
                errors.append("bootstrap_session_missing")
            else:
                if session["learner_id"] != private.get("learner_id"):
                    errors.append("session_learner_binding_invalid")
                if session["breadth_cell_id"] != private.get("selected_cell", {}).get("breadth_cell_id"):
                    errors.append("session_cell_binding_invalid")
                if session["purpose"] != private.get("selected_cell", {}).get("purpose"):
                    errors.append("session_purpose_binding_invalid")
                if session["session_state"] != "ACTIVE":
                    errors.append("bootstrap_session_not_active")
                if r5.digest(str(private.get("access_token") or "")) != session["access_token_hash"]:
                    errors.append("bootstrap_access_token_invalid")
        runtime = r5.LocalEdgeRuntime(database_path)
        rebuilt = runtime.session_payload(
            session_id=str(private.get("session_id") or ""),
            access_token=str(private.get("access_token") or ""),
        )
        if rebuilt != stored_session:
            errors.append("session_payload_rebuild_drift")
        projected = bootstrap._safe_session_projection(rebuilt)
        if safe.get("session") != projected:
            errors.append("safe_session_projection_drift")
    except (sqlite3.Error, r5.LocalEdgeRuntimeError) as exc:
        errors.append(f"session_validation_failed:{exc}")

    current_database_sha = bootstrap.file_digest(database_path)
    if private.get("source_bindings", {}).get("database_sha256_after_start") != current_database_sha:
        errors.append("database_binding_drift")

    return {
        "validation_status": bootstrap.STATUS if not errors else "FAIL_A1FS_V1_R5_PRODUCTION_BOOTSTRAP_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        "next_short_step": bootstrap.NEXT_SHORT_STEP if not errors else bootstrap.TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--ontology", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--consumer", type=Path)
    parser.add_argument("--consumer-search-root", type=Path)
    args = parser.parse_args()
    result = validate(
        database_path=args.database,
        ontology_path=args.ontology,
        graph_path=args.graph,
        output_root=args.output_root,
        consumer_path=args.consumer,
        consumer_search_root=args.consumer_search_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
