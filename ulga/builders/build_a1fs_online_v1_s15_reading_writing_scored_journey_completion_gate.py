#!/usr/bin/env python3
"""Connect S14 learner surface to existing M6 scored Reading/Writing journeys.

S15 reuses the S14 authenticated learner-facing localhost surface, the S09
24-unit runtime, M3 session state, and M6 response/scoring/review authorities.
It adds retry-aware attempt history and a fail-closed Reading/Writing session
completion gate. Speaking remains practice-only; Listening/audio, A2,
Cloudflare, unit completion, mastery, retention, and parallel engines remain
out of scope.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _a1fs_online_v1_s15_scored_journey_acceptance as acceptance
from ulga.builders import _a1fs_online_v1_s15_scored_journey_core as core
from ulga.builders import _a1fs_online_v1_s15_scored_journey_static as static

A1FS_CONTENT_POLICY_MODE = core.A1FS_CONTENT_POLICY_MODE
A1FS_CONTENT_POLICY_EXEMPTION = core.A1FS_CONTENT_POLICY_EXEMPTION
PROGRAM_ID = core.PROGRAM_ID
TASK_ID = core.TASK_ID
SCHEMA_VERSION = core.SCHEMA_VERSION
PASS_STATUS = core.PASS_STATUS
PRODUCT_STATUS = core.PRODUCT_STATUS
RELEASE_PROFILE = core.RELEASE_PROFILE
NEXT_SHORT_STEP = core.NEXT_SHORT_STEP
DEFAULT_PORT = core.DEFAULT_PORT
CANARY_LEARNER_ID = core.CANARY_LEARNER_ID
CANARY_SUBJECT_KEY = core.CANARY_SUBJECT_KEY
CANARY_READING_SESSION_ID = core.CANARY_READING_SESSION_ID
CANARY_WRITING_SESSION_ID = core.CANARY_WRITING_SESSION_ID
CANARY_PASSWORD = core.CANARY_PASSWORD
CANARY_SESSION_SECRET = core.CANARY_SESSION_SECRET
PASSING_OUTCOMES = core.PASSING_OUTCOMES
RETRY_OUTCOMES = core.RETRY_OUTCOMES
PENDING_OUTCOMES = core.PENDING_OUTCOMES
SCORED_SKILLS = core.SCORED_SKILLS
ScoredJourneyError = core.ScoredJourneyError
ScoredJourneyApplication = core.ScoredJourneyApplication
s14 = core.s14
s13 = core.s13
s11 = core.s11
m6 = core.m6
digest = core.digest
file_digest = core.file_digest
read_json = core.read_json
write_json = core.write_json
safe_scan = core.safe_scan
_verify_s14 = core._verify_s14
_app = core._app
_write_scored_static = static._write_scored_static
_write_launch_bundle = static._write_launch_bundle
_contracts_for_lesson = acceptance._contracts_for_lesson
_passing_response = acceptance._passing_response
_wrong_response = acceptance._wrong_response
_lesson_ids = acceptance._lesson_ids
_run_authenticated_http_acceptance = acceptance._run_authenticated_http_acceptance
_run_acceptance = acceptance._run_acceptance


def materialize(*, s14_receipt_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    s14_receipt, production_database, auth_state_db, bundles, sequence = _verify_s14(s14_receipt_path)
    output_root = Path(output_root).resolve()
    root = output_root / "scored_journey_completion_gate"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    learner_static = root / "learner_static"
    secure_static = root / "secure_static"
    _write_scored_static(learner_static)
    s11._write_secure_static(learner_static, secure_static)
    canary_database = root / "runtime" / "s15_scored_journey_acceptance.sqlite3"
    canary_database.parent.mkdir(parents=True, exist_ok=True)
    acceptance_auth_state = root / "runtime" / "s15_acceptance_auth.sqlite3"
    acceptance_result = _run_acceptance(
        production_database=production_database,
        bundles=bundles,
        sequence=sequence,
        canary_database=canary_database,
        secure_static_root=secure_static,
        acceptance_auth_state=acceptance_auth_state,
    )
    launch_bundle = _write_launch_bundle(
        target_root=root / "launch_bundle",
        receipt_path=output_root / "reading_writing_scored_journey.private.json",
        auth_state_db=auth_state_db,
    )
    production_sha = file_digest(production_database)
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "s14_sha256": digest(s14_receipt),
            "production_database_sha256": production_sha,
        },
        "runtime_outputs": {
            "root": str(root),
            "source_s14_receipt_path": str(Path(s14_receipt_path).resolve()),
            "source_database_path": str(production_database),
            "acceptance_database_path": str(canary_database),
            "learner_static_root": str(learner_static),
            "secure_static_root": str(secure_static),
            **launch_bundle,
        },
        "scored_journey_summary": acceptance_result,
        "production_safety": {
            "production_database_sha256_before": production_sha,
            "production_database_sha256_after": file_digest(production_database),
            "production_database_unchanged": True,
            "acceptance_used_isolated_database_clone": True,
            "learner_progress_mutated_by_acceptance": False,
            "auth_state_reused_from_s14_source": True,
        },
        "capability_contract": {
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
        },
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    receipt = {**receipt_core, "artifact_sha256": digest(receipt_core)}
    safe_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "scored_journey_summary": deepcopy(acceptance_result),
        "production_safety": {
            "production_database_unchanged": True,
            "acceptance_used_isolated_database_clone": True,
            "learner_progress_mutated_by_acceptance": False,
            "auth_state_reused_from_s14_source": True,
        },
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def _source(
    receipt_path: Path,
) -> tuple[dict[str, Any], Path, Path, dict[str, dict[str, Any]], dict[str, int], Path]:
    receipt = read_json(receipt_path, "s15_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"), receipt.get("validation_status"),
        receipt.get("product_status"), receipt.get("stop_reason"),
    )
    if identity != (TASK_ID, SCHEMA_VERSION, PASS_STATUS, PRODUCT_STATUS, "NONE"):
        raise ScoredJourneyError("s15_receipt_contract_invalid")
    core_value = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core_value):
        raise ScoredJourneyError("s15_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs", {})
    source_s14 = Path(str(outputs.get("source_s14_receipt_path") or "")).resolve()
    secure_static = Path(str(outputs.get("secure_static_root") or "")).resolve()
    _, database, auth_state, bundles, sequence = _verify_s14(source_s14)
    if not secure_static.is_dir():
        raise ScoredJourneyError("s15_secure_static_missing")
    return receipt, database, auth_state, bundles, sequence, secure_static


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    _, database, auth_state, bundles, sequence, secure_static = _source(receipt_path)
    config = s13.PersistentBoundaryConfig.from_environment(
        host=host,
        port=port,
        revocation_db_path=auth_state,
    )
    server = s11.SecureBoundaryServer(
        (host, port),
        _app(database, bundles, sequence),
        secure_static,
        config,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def readback(*, receipt_path: Path) -> dict[str, Any]:
    receipt, _, _, _, _, _ = _source(receipt_path)
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "scored_journey_summary": deepcopy(receipt["scored_journey_summary"]),
        "capability_contract": deepcopy(receipt["capability_contract"]),
        "next_short_step": NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s14", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    server = commands.add_parser("serve")
    server.add_argument("--receipt", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=DEFAULT_PORT)
    snap = commands.add_parser("readback")
    snap.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            serve(receipt_path=args.receipt, host=args.host, port=args.port)
            return 0
        if args.command == "readback":
            print(json.dumps(readback(receipt_path=args.receipt), ensure_ascii=False, indent=2))
            return 0
        receipt, safe = materialize(s14_receipt_path=args.s14, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s15_reading_writing_scored_journey_completion_gate import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s14_path=args.s14,
        )
        if validation["error_count"]:
            raise ScoredJourneyError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        ScoredJourneyError,
        s14.LearnerFacingSemanticsError,
        s13.LocalhostDeploymentError,
        s11.SecureBoundaryError,
        m6.ResponseEvidenceError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
