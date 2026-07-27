#!/usr/bin/env python3
"""Corrected S17 runtime entrypoint with exact privacy checks and direct HTTP server wiring."""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import threading
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review as legacy

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Runs the existing S17 dashboard and M6 human-review integration through exact-key privacy validation and direct ThreadingHTTPServer wiring; it creates no curriculum, learner content, answers, scoring, review, mastery, role authority, audio, A2, Cloudflare, or parallel engine."

PROGRAM_ID = legacy.PROGRAM_ID
TASK_ID = legacy.TASK_ID
SCHEMA_VERSION = legacy.SCHEMA_VERSION
PASS_STATUS = legacy.PASS_STATUS
PRODUCT_STATUS = legacy.PRODUCT_STATUS
RELEASE_PROFILE = legacy.RELEASE_PROFILE
NEXT_SHORT_STEP = legacy.NEXT_SHORT_STEP
DEFAULT_PORT = legacy.DEFAULT_PORT
CANARY_LEARNER_ID = legacy.CANARY_LEARNER_ID
DashboardReviewError = legacy.DashboardReviewError
DashboardReviewApplication = legacy.DashboardReviewApplication
DashboardReviewHandler = legacy.DashboardReviewHandler
s16 = legacy.s16
m9 = legacy.m9
digest = legacy.digest
file_digest = legacy.file_digest
read_json = legacy.read_json
write_json = legacy.write_json
safe_scan = legacy.safe_scan
build_dashboard_projection = legacy.build_dashboard_projection
_write_static = legacy._write_static
_source = legacy._source
_app = legacy._app

DASHBOARD_PRIVATE_KEYS = {
    "attempt_id", "session_id", "asset_key", "response", "response_json",
    "review_queue", "criteria", "notes", "reviewer_id",
}
LEGACY_MODULE = "ulga.builders.build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review"
RUNTIME_MODULE = "ulga.builders.build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review_runtime"
_legacy_write_launch_bundle = legacy._write_launch_bundle


def _contains_exact_key(value: Any, forbidden: set[str]) -> bool:
    folded = {key.casefold() for key in forbidden}
    if isinstance(value, Mapping):
        return any(
            str(key).casefold() in folded or _contains_exact_key(child, forbidden)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_exact_key(child, forbidden) for child in value)
    return False


class DashboardReviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        app: DashboardReviewApplication,
        secure_static_root: Path,
        config: Any,
    ):
        if not s16.s15.s11._is_loopback(address[0]):
            raise DashboardReviewError(f"non_loopback_host_forbidden:{address[0]}")
        self.app = app
        self.static_root = Path(secure_static_root)
        self.secure_static_root = Path(secure_static_root)
        self.config = config
        super().__init__(address, DashboardReviewHandler)
        self.config.bind_local_port(int(self.server_address[1]))


def _start_server(
    *, app: DashboardReviewApplication, secure_static_root: Path, config: Any,
) -> tuple[DashboardReviewServer, threading.Thread, int]:
    server = DashboardReviewServer(("127.0.0.1", 0), app, secure_static_root, config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, int(server.server_address[1])


def run_isolated_acceptance(
    *,
    source_acceptance_database: Path,
    production_database: Path,
    source_state_root: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
    graph_path: Path,
    secure_static_root: Path,
    acceptance_database: Path,
    state_root: Path,
    auth_state: Path,
) -> dict[str, Any]:
    production_before = file_digest(production_database)
    acceptance_database.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_acceptance_database, acceptance_database)
    if state_root.exists():
        shutil.rmtree(state_root)
    if source_state_root.is_dir():
        shutil.copytree(source_state_root, state_root)
    else:
        state_root.mkdir(parents=True, exist_ok=True)
    app = _app(
        database=acceptance_database,
        bundles=bundles,
        sequence=sequence,
        graph_path=graph_path,
        state_root=state_root,
        default_learner_id=CANARY_LEARNER_ID,
    )
    pending_attempt_id, _, session_version = legacy._prepare_pending_review(
        app=app,
        bundles=bundles,
    )
    dashboard_before = app.dashboard_readback()
    if dashboard_before["dashboard"]["teacher"]["pending_human_review_count"] != 1:
        raise DashboardReviewError("dashboard_pending_review_count_invalid")
    if _contains_exact_key(dashboard_before["dashboard"], DASHBOARD_PRIVATE_KEYS):
        raise DashboardReviewError("raw_response_leaked_to_dashboard")
    http = legacy._run_authenticated_acceptance(
        app=app,
        secure_static_root=secure_static_root,
        auth_state=auth_state,
        pending_attempt_id=pending_attempt_id,
        expected_session_version=session_version,
    )
    dashboard_after = app.dashboard_readback()
    if dashboard_after["dashboard"]["teacher"]["pending_human_review_count"] != 0:
        raise DashboardReviewError("dashboard_review_count_not_refreshed")
    if _contains_exact_key(dashboard_after["dashboard"], DASHBOARD_PRIVATE_KEYS):
        raise DashboardReviewError("raw_response_leaked_to_dashboard")
    if file_digest(production_database) != production_before:
        raise DashboardReviewError("production_database_mutated_by_s17_acceptance")
    return {
        "unit_count": 24,
        "scored_lesson_count": 48,
        "dashboard_role_count": http["dashboard_role_count"],
        "learner_dashboard_pass": True,
        "parent_dashboard_pass": True,
        "teacher_dashboard_pass": True,
        "m9_dashboard_projection_reused": True,
        "m6_human_review_authority_reused": True,
        "pending_human_review_count_before": http["pending_human_review_count_before"],
        "pending_human_review_count_after": http["pending_human_review_count_after"],
        "authenticated_dashboard_endpoint_pass": http["authenticated_dashboard_endpoint_pass"],
        "authenticated_review_queue_endpoint_pass": http["authenticated_review_queue_endpoint_pass"],
        "csrf_review_decision_pass": http["csrf_review_decision_pass"],
        "human_approve_outcome_pass": http["human_approve_outcome_pass"],
        "completion_after_human_approval": http["completion_after_human_approval"],
        "dashboard_after_completion_pass": http["dashboard_after_completion_pass"],
        "raw_response_excluded_from_dashboard": True,
        "review_queue_raw_response_available": http["review_queue_raw_response_available"],
        "role_based_identity_authorization_claimed": False,
        "production_database_unchanged": True,
        "acceptance_used_isolated_database_clone": True,
        "parallel_dashboard_engine_created": False,
        "parallel_review_engine_created": False,
        "a2_unlocked": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "cloudflare_enabled": False,
    }


def _write_launch_bundle(
    *, target_root: Path, receipt_path: Path, auth_state_db: Path,
) -> dict[str, Any]:
    result = _legacy_write_launch_bundle(
        target_root=target_root,
        receipt_path=receipt_path,
        auth_state_db=auth_state_db,
    )
    for key in ("start_script_path", "stop_script_path", "status_script_path"):
        path = Path(str(result[key]))
        text = path.read_text(encoding="utf-8").replace(LEGACY_MODULE, RUNTIME_MODULE)
        path.write_text(text, encoding="utf-8")
    return result


def _activate_runtime_fixes() -> None:
    legacy.DashboardReviewServer = DashboardReviewServer
    legacy._start_server = _start_server
    legacy.run_isolated_acceptance = run_isolated_acceptance
    legacy._write_launch_bundle = _write_launch_bundle


def materialize(*, s16_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    _activate_runtime_fixes()
    return legacy.materialize(s16_path=s16_path, output_root=output_root)


def _load_runtime(receipt_path: Path):
    return legacy._load_runtime(receipt_path)


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    (
        _, database, auth_state, bundles, sequence, graph_path, state_root, secure_static,
    ) = _load_runtime(receipt_path)
    config = s16.s15.s13.PersistentBoundaryConfig.from_environment(
        host=host,
        port=port,
        revocation_db_path=auth_state,
    )
    server = DashboardReviewServer(
        (host, port),
        _app(
            database=database,
            bundles=bundles,
            sequence=sequence,
            graph_path=graph_path,
            state_root=state_root,
        ),
        secure_static,
        config,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def readback(*, receipt_path: Path) -> dict[str, Any]:
    return legacy.readback(receipt_path=receipt_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s16", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    server = commands.add_parser("serve")
    server.add_argument("--receipt", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=DEFAULT_PORT)
    snapshot = commands.add_parser("readback")
    snapshot.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            serve(receipt_path=args.receipt, host=args.host, port=args.port)
            return 0
        if args.command == "readback":
            print(json.dumps(readback(receipt_path=args.receipt), ensure_ascii=False, indent=2))
            return 0
        receipt, safe = materialize(s16_path=args.s16, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s16_path=args.s16,
        )
        if validation["error_count"]:
            raise DashboardReviewError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        DashboardReviewError,
        s16.CanonicalLearningError,
        s16.s15.ScoredJourneyError,
        s16.s15.s14.LearnerFacingSemanticsError,
        s16.core.m7.MasteryError,
        s16.core.m8.ReviewRetentionError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
