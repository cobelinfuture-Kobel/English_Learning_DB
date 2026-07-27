#!/usr/bin/env python3
"""Accept the complete S17 non-audio learner product and recovery path.

S18 is an acceptance-only milestone. It reuses the S17 authenticated runtime,
M6 scoring/review, M7/M8 canonical learning state, M9 dashboard projection,
and S17 operator launch lifecycle. All stateful acceptance runs on isolated
copies. No release candidate, product feature, content, audio, A2, Cloudflare,
or parallel engine is created.
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

from ulga.builders import build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review_runtime as s17

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Runs full non-audio product acceptance and restart/revocation recovery against isolated copies of the existing S17 runtime; it creates no curriculum, learner content, answer, scoring, review, mastery, dashboard, role authority, audio, A2, Cloudflare route, release candidate, or parallel engine."

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S18_NonAudioLearnerProductE2EReleaseAcceptanceAndRecovery_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s18.nonaudio_e2e_release_acceptance_recovery.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S18_NONAUDIO_E2E_RELEASE_ACCEPTANCE_RECOVERY_READY"
PRODUCT_STATUS = "LOCALHOST_NONAUDIO_PRODUCT_E2E_ACCEPTED_RECOVERY_VERIFIED_NOT_RELEASE_CANDIDATE"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S19_LocalhostNoAudioLearnerProductReleaseCandidate"

CANARY_USERNAME = "s18-e2e-operator"
CANARY_READING_SESSION_ID = "A1FS_ONLINE_V1_S18_SESSION:READING"
CANARY_WRITING_SESSION_ID = "A1FS_ONLINE_V1_S18_SESSION:WRITING_REVIEW"
CANARY_REVIEWED_AT = "2026-01-19T00:20:00Z"
CANARY_LEARNER_ID = s17.CANARY_LEARNER_ID


class E2ERecoveryError(ValueError):
    """Fail-closed S18 acceptance error."""


def digest(value: Any) -> str:
    return s17.digest(value)


def file_digest(path: Path) -> str:
    return s17.file_digest(path)


def read_json(path: Path, code: str) -> dict[str, Any]:
    return s17.read_json(path, code)


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    s17.write_json(path, value, private=private)


def safe_scan(value: Any) -> None:
    s17.safe_scan(value)


def _verify_s17(
    receipt_path: Path,
) -> tuple[
    dict[str, Any], Path, dict[str, dict[str, Any]], dict[str, int], Path, Path,
    Path, Path, Path, dict[str, Path],
]:
    receipt_path = Path(receipt_path).resolve()
    receipt = read_json(receipt_path, "s17_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    if identity != (s17.TASK_ID, s17.SCHEMA_VERSION, s17.PASS_STATUS, s17.PRODUCT_STATUS, "NONE"):
        raise E2ERecoveryError("s17_receipt_contract_invalid")
    body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(body):
        raise E2ERecoveryError("s17_receipt_digest_invalid")
    (
        _, production_database, _, bundles, sequence, graph_path, source_state_root,
        secure_static,
    ) = s17._load_runtime(receipt_path)
    outputs = receipt.get("runtime_outputs", {})
    acceptance_database = Path(str(outputs.get("acceptance_database_path") or "")).resolve()
    acceptance_state = Path(str(outputs.get("acceptance_state_root") or "")).resolve()
    if not acceptance_database.is_file() or not acceptance_state.is_dir():
        raise E2ERecoveryError("s17_acceptance_sources_missing")
    if len(bundles) != 72 or len(sequence) != 24:
        raise E2ERecoveryError("s17_runtime_denominator_invalid")
    launch_paths = {
        name: Path(str(outputs.get(key) or "")).resolve()
        for name, key in {
            "start": "start_script_path",
            "stop": "stop_script_path",
            "status": "status_script_path",
            "contract": "launch_contract_path",
        }.items()
    }
    if any(not path.is_file() for path in launch_paths.values()):
        raise E2ERecoveryError("s17_operator_launch_bundle_missing")
    summary = receipt.get("dashboard_review_summary", {})
    if (
        summary.get("unit_count") != 24
        or summary.get("scored_lesson_count") != 48
        or summary.get("dashboard_role_count") != 3
        or summary.get("production_database_unchanged") is not True
    ):
        raise E2ERecoveryError("s17_acceptance_denominator_invalid")
    return (
        receipt, production_database, bundles, sequence, graph_path,
        source_state_root, secure_static, acceptance_database, acceptance_state,
        launch_paths,
    )


def _copy_state(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        target.mkdir(parents=True, exist_ok=True)


def _config(auth_state: Path):
    return s17.s16.s15.s13.PersistentBoundaryConfig.from_values(
        username=CANARY_USERNAME,
        password=s17.s16.s15.CANARY_PASSWORD,
        session_secret=s17.s16.s15.CANARY_SESSION_SECRET,
        mode="local",
        allowed_origin="http://127.0.0.1",
        allowed_host="127.0.0.1",
        revocation_db_path=auth_state,
        port=0,
    )


def _application(
    *, database: Path, bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int], graph_path: Path, state_root: Path,
):
    return s17._app(
        database=database,
        bundles=bundles,
        sequence=sequence,
        graph_path=graph_path,
        state_root=state_root,
        default_learner_id=CANARY_LEARNER_ID,
    )


def _reading_journey(app: Any, bundles: Mapping[str, Mapping[str, Any]]) -> None:
    lesson_id = ""
    contracts: list[dict[str, Any]] = []
    for candidate in s17.s16.s15._lesson_ids(bundles, "READING"):
        rows = s17.s16.s15._contracts_for_lesson(app.database_path, candidate)
        if len(rows) == 4 and not any(row.get("scoring_mode") == "FEATURE_RUBRIC" for row in rows):
            lesson_id, contracts = candidate, rows
            break
    if not lesson_id:
        raise E2ERecoveryError("reading_e2e_lesson_missing")
    current: Mapping[str, Any] = app.start_session({
        "lesson_id": lesson_id,
        "session_id": CANARY_READING_SESSION_ID,
        "at": "2026-01-19T00:00:00Z",
    })
    for index, contract in enumerate(contracts, start=1):
        exposed = app.record_exposure({
            "session_id": CANARY_READING_SESSION_ID,
            "asset_key": contract["asset_key"],
            "expected_session_version": current["session_version"],
            "at": f"2026-01-19T00:01:{index:02d}Z",
        })
        current = app.submit_response({
            "session_id": CANARY_READING_SESSION_ID,
            "asset_key": contract["asset_key"],
            "response": s17.s16.s15._passing_response(contract),
            "expected_session_version": exposed["session_version"],
            "attempt_id": f"A1FS_ONLINE_V1_S18_ATTEMPT:READING:{index}",
            "submitted_at": f"2026-01-19T00:02:{index:02d}Z",
        })
    readiness = app.completion_readiness(CANARY_READING_SESSION_ID)
    if readiness.get("completion_allowed") is not True or readiness.get("passed_response_count") != 4:
        raise E2ERecoveryError("reading_e2e_completion_gate_invalid")
    completed = app.complete_session({
        "session_id": CANARY_READING_SESSION_ID,
        "expected_session_version": current["session_version"],
        "at": "2026-01-19T00:03:00Z",
    })
    if completed.get("session_state") != "COMPLETED":
        raise E2ERecoveryError("reading_e2e_session_not_completed")


def _writing_pending_journey(
    app: Any, bundles: Mapping[str, Mapping[str, Any]],
) -> tuple[str, int]:
    lesson_id, contracts = s17.legacy._select_review_lesson(app.database_path, bundles)
    current: Mapping[str, Any] = app.start_session({
        "lesson_id": lesson_id,
        "session_id": CANARY_WRITING_SESSION_ID,
        "at": "2026-01-19T00:05:00Z",
    })
    pending_attempt = ""
    for index, contract in enumerate(contracts, start=1):
        exposed = app.record_exposure({
            "session_id": CANARY_WRITING_SESSION_ID,
            "asset_key": contract["asset_key"],
            "expected_session_version": current["session_version"],
            "at": f"2026-01-19T00:06:{index:02d}Z",
        })
        attempt_id = f"A1FS_ONLINE_V1_S18_ATTEMPT:WRITING:{index}"
        current = app.submit_response({
            "session_id": CANARY_WRITING_SESSION_ID,
            "asset_key": contract["asset_key"],
            "response": s17.s16.s15._passing_response(contract),
            "expected_session_version": exposed["session_version"],
            "attempt_id": attempt_id,
            "submitted_at": f"2026-01-19T00:07:{index:02d}Z",
        })
        if current.get("outcome") == "PENDING_HUMAN_REVIEW":
            pending_attempt = attempt_id
    readiness = app.completion_readiness(CANARY_WRITING_SESSION_ID)
    if (
        not pending_attempt
        or readiness.get("completion_allowed") is not False
        or readiness.get("pending_human_review_count") != 1
    ):
        raise E2ERecoveryError("writing_e2e_pending_gate_invalid")
    return pending_attempt, int(current["session_version"])


def _operator_lifecycle_contract(paths: Mapping[str, Path]) -> dict[str, bool]:
    start = paths["start"].read_text(encoding="utf-8")
    stop = paths["stop"].read_text(encoding="utf-8")
    status = paths["status"].read_text(encoding="utf-8")
    contract = read_json(paths["contract"], "s17_launch_contract")
    checks = {
        "start_script_contract_pass": all(token in start for token in (
            "A1FS_S17_LOCALHOST_STARTED=PASS", "PORT_IN_USE", "PID_FILE_ALREADY_EXISTS",
            "build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review_runtime",
        )),
        "stop_script_contract_pass": all(token in stop for token in (
            "PID_OWNERSHIP_MISMATCH", "PORT_STILL_LISTENING", "A1FS_S17_LOCALHOST_STOPPED=PASS",
        )),
        "status_script_contract_pass": all(token in status for token in (
            "PORT_OWNERSHIP_INVALID", "UNHEALTHY", "A1FS_S17_LOCALHOST_STATUS=RUNNING",
        )),
        "launch_contract_boundary_pass": (
            contract.get("host") == "127.0.0.1"
            and contract.get("authentication_required") is True
            and contract.get("csrf_required_for_review_decision") is True
            and contract.get("external_network_binding_allowed") is False
            and contract.get("cloudflare_enabled") is False
            and contract.get("audio_enabled") is False
            and contract.get("a2_session_enabled") is False
        ),
    }
    if not all(checks.values()):
        raise E2ERecoveryError("s17_operator_lifecycle_contract_invalid")
    return checks


def _request(port: int, method: str, path: str, *args: Any, **kwargs: Any):
    return s17.s16.s15.s11._request(port, method, path, *args, **kwargs)


def run_isolated_acceptance(
    *, source_database: Path, source_state: Path, production_database: Path,
    bundles: Mapping[str, Mapping[str, Any]], sequence: Mapping[str, int],
    graph_path: Path, secure_static: Path, acceptance_database: Path,
    acceptance_state: Path, acceptance_auth: Path, launch_paths: Mapping[str, Path],
) -> dict[str, Any]:
    production_before = file_digest(production_database)
    acceptance_database.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_database, acceptance_database)
    _copy_state(source_state, acceptance_state)
    acceptance_auth.unlink(missing_ok=True)

    app1 = _application(
        database=acceptance_database, bundles=bundles, sequence=sequence,
        graph_path=graph_path, state_root=acceptance_state,
    )
    _reading_journey(app1, bundles)
    pending_attempt, writing_version = _writing_pending_journey(app1, bundles)

    server1, thread1, port1 = s17._start_server(
        app=app1, secure_static_root=secure_static, config=_config(acceptance_auth),
    )
    origin1 = f"http://127.0.0.1:{port1}"
    try:
        health, _ = _request(port1, "GET", "/api/health")
        if health.get("authentication_required") is not True:
            raise E2ERecoveryError("s18_health_contract_invalid")
        _request(port1, "GET", "/api/bootstrap", expected_status=401)
        login, login_headers = _request(
            port1, "POST", "/auth/login",
            {"username": CANARY_USERNAME, "password": s17.s16.s15.CANARY_PASSWORD},
            origin=origin1,
        )
        cookie_header = str(login_headers.get("Set-Cookie") or "")
        cookie = cookie_header.split(";", 1)[0]
        csrf = str(login.get("csrf_token") or "")
        if not cookie or not csrf or "HttpOnly" not in cookie_header or "SameSite=Strict" not in cookie_header:
            raise E2ERecoveryError("s18_login_cookie_invalid")
        bootstrap, _ = _request(port1, "GET", "/api/bootstrap", cookie=cookie)
        denominators = s17.s16.s15.s11.s10._validate_bootstrap(bootstrap)
        progress_before, _ = _request(port1, "GET", "/api/progress", cookie=cookie)
        dashboard_before, _ = _request(port1, "GET", "/api/dashboard", cookie=cookie)
        queue_before, _ = _request(port1, "GET", "/api/human-review", cookie=cookie)
        if dashboard_before.get("dashboard", {}).get("role_count") != 3:
            raise E2ERecoveryError("s18_dashboard_role_count_invalid")
        if queue_before.get("pending_count") != 1:
            raise E2ERecoveryError("s18_review_queue_before_restart_invalid")
    finally:
        s17.s16.s15.s13._stop_server(server1, thread1)

    app2 = _application(
        database=acceptance_database, bundles=bundles, sequence=sequence,
        graph_path=graph_path, state_root=acceptance_state,
    )
    server2, thread2, port2 = s17._start_server(
        app=app2, secure_static_root=secure_static, config=_config(acceptance_auth),
    )
    origin2 = f"http://127.0.0.1:{port2}"
    try:
        session, _ = _request(port2, "GET", "/auth/session", cookie=cookie)
        if session.get("authenticated") is not True or session.get("csrf_token") != csrf:
            raise E2ERecoveryError("s18_authenticated_session_restart_invalid")
        active = app2.active_session_readback()
        if not active.get("active") or active.get("session", {}).get("session_id") != CANARY_WRITING_SESSION_ID:
            raise E2ERecoveryError("s18_active_learning_session_restart_invalid")
        progress_restart, _ = _request(port2, "GET", "/api/progress", cookie=cookie)
        dashboard_restart, _ = _request(port2, "GET", "/api/dashboard", cookie=cookie)
        queue_restart, _ = _request(port2, "GET", "/api/human-review", cookie=cookie)
        if progress_restart.get("summary") != progress_before.get("summary"):
            raise E2ERecoveryError("s18_progress_restart_mismatch")
        if dashboard_restart.get("dashboard") != dashboard_before.get("dashboard"):
            raise E2ERecoveryError("s18_dashboard_restart_mismatch")
        if queue_restart.get("pending_count") != 1:
            raise E2ERecoveryError("s18_review_queue_restart_mismatch")
        decision, _ = _request(
            port2, "POST", "/api/human-review/decision",
            {
                "attempt_id": pending_attempt,
                "decision": "APPROVE",
                "criteria": {
                    "grammar_target_match": True,
                    "meaning_matches_context": True,
                    "complete_response": True,
                },
                "notes": "S18 restart recovery acceptance.",
                "reviewed_at": CANARY_REVIEWED_AT,
            },
            cookie=cookie, csrf=csrf, origin=origin2,
        )
        if (
            decision.get("review_result", {}).get("outcome") != "HUMAN_APPROVE"
            or decision.get("pending_count") != 0
            or decision.get("completion_gate", {}).get("completion_allowed") is not True
        ):
            raise E2ERecoveryError("s18_review_decision_after_restart_invalid")
        completed = app2.complete_session({
            "session_id": CANARY_WRITING_SESSION_ID,
            "expected_session_version": writing_version,
            "at": "2026-01-19T00:21:00Z",
        })
        if completed.get("session_state") != "COMPLETED":
            raise E2ERecoveryError("s18_writing_session_not_completed")
        dashboard_after, _ = _request(port2, "GET", "/api/dashboard", cookie=cookie)
        queue_after, _ = _request(port2, "GET", "/api/human-review", cookie=cookie)
        if (
            queue_after.get("pending_count") != 0
            or dashboard_after.get("dashboard", {}).get("teacher", {}).get("pending_human_review_count") != 0
        ):
            raise E2ERecoveryError("s18_dashboard_after_review_invalid")
        _request(
            port2, "POST", "/auth/logout", {}, cookie=cookie, csrf=csrf, origin=origin2,
        )
        _request(port2, "GET", "/api/bootstrap", cookie=cookie, expected_status=401)
    finally:
        s17.s16.s15.s13._stop_server(server2, thread2)

    app3 = _application(
        database=acceptance_database, bundles=bundles, sequence=sequence,
        graph_path=graph_path, state_root=acceptance_state,
    )
    server3, thread3, port3 = s17._start_server(
        app=app3, secure_static_root=secure_static, config=_config(acceptance_auth),
    )
    try:
        _request(port3, "GET", "/api/bootstrap", cookie=cookie, expected_status=401)
    finally:
        s17.s16.s15.s13._stop_server(server3, thread3)

    with sqlite3.connect(acceptance_auth) as connection:
        revoked_count = int(connection.execute("SELECT COUNT(*) FROM revoked_sessions").fetchone()[0])
    if revoked_count != 1:
        raise E2ERecoveryError(f"s18_revocation_denominator_invalid:{revoked_count}")
    if file_digest(production_database) != production_before:
        raise E2ERecoveryError("production_database_mutated_by_s18_acceptance")
    lifecycle = _operator_lifecycle_contract(launch_paths)
    speaking_count = sum(
        str(lane.get("skill") or "").upper() == "SPEAKING"
        for unit in bootstrap.get("units", [])
        for lane in unit.get("lanes", [])
    )
    if speaking_count != 24:
        raise E2ERecoveryError(f"speaking_practice_denominator_invalid:{speaking_count}")
    return {
        **denominators,
        "scored_lesson_count": 48,
        "speaking_practice_lesson_count": 24,
        "dashboard_role_count": 3,
        "reading_scored_journey_completed": True,
        "writing_human_review_journey_completed": True,
        "pending_human_review_count_before": 1,
        "pending_human_review_count_after": 0,
        "authenticated_bootstrap_pass": True,
        "authenticated_progress_pass": True,
        "authenticated_dashboard_pass": True,
        "authenticated_review_queue_pass": True,
        "authenticated_session_survived_server_restart": True,
        "active_learning_session_survived_server_restart": True,
        "progress_survived_server_restart": True,
        "dashboard_survived_server_restart": True,
        "review_queue_survived_server_restart": True,
        "human_approval_after_restart_pass": True,
        "logout_revocation_survived_server_restart": True,
        "persistent_revocation_count": 1,
        "application_server_start_count": 3,
        **lifecycle,
        "p0_blocker_count": 0,
        "p1_blocker_count": 0,
        "production_database_unchanged": True,
        "acceptance_used_isolated_database_clone": True,
        "acceptance_used_isolated_state_clone": True,
        "release_candidate_created": False,
        "role_based_identity_authorization_claimed": False,
        "a2_unlocked": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "cloudflare_enabled": False,
    }


def materialize(*, s17_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    (
        s17_receipt, production_database, bundles, sequence, graph_path,
        source_state_root, secure_static, source_acceptance_database,
        source_acceptance_state, launch_paths,
    ) = _verify_s17(s17_path)
    output_root = Path(output_root).resolve()
    root = output_root / "nonaudio_e2e_release_acceptance_recovery"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    acceptance_database = root / "runtime" / "s18_e2e_acceptance.sqlite3"
    acceptance_state = root / "runtime" / "canonical_learning_state"
    acceptance_auth = root / "runtime" / "s18_auth_state.sqlite3"
    acceptance = run_isolated_acceptance(
        source_database=source_acceptance_database,
        source_state=source_acceptance_state,
        production_database=production_database,
        bundles=bundles,
        sequence=sequence,
        graph_path=graph_path,
        secure_static=secure_static,
        acceptance_database=acceptance_database,
        acceptance_state=acceptance_state,
        acceptance_auth=acceptance_auth,
        launch_paths=launch_paths,
    )
    production_sha = file_digest(production_database)
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "s17_sha256": digest(s17_receipt),
            "production_database_sha256": production_sha,
        },
        "runtime_outputs": {
            "root": str(root),
            "source_s17_receipt_path": str(Path(s17_path).resolve()),
            "source_database_path": str(production_database),
            "source_graph_path": str(graph_path),
            "acceptance_database_path": str(acceptance_database),
            "acceptance_state_root": str(acceptance_state),
            "acceptance_auth_state_path": str(acceptance_auth),
            "source_start_script_path": str(launch_paths["start"]),
            "source_stop_script_path": str(launch_paths["stop"]),
            "source_status_script_path": str(launch_paths["status"]),
            "source_launch_contract_path": str(launch_paths["contract"]),
        },
        "e2e_release_acceptance_summary": acceptance,
        "production_safety": {
            "production_database_sha256_before": production_sha,
            "production_database_sha256_after": file_digest(production_database),
            "production_database_unchanged": True,
            "acceptance_used_isolated_database_clone": True,
            "acceptance_used_isolated_state_clone": True,
            "learner_progress_mutated_by_acceptance": False,
            "raw_response_serialized_to_safe_artifact": False,
        },
        "capability_contract": {
            "s17_product_runtime_reused": True,
            "s17_operator_lifecycle_reused": True,
            "m6_scoring_review_reused": True,
            "m7_m8_canonical_learning_reused": True,
            "m9_dashboard_projection_reused": True,
            "new_product_capability_created": False,
            "parallel_curriculum_created": False,
            "parallel_learner_state_engine_created": False,
            "parallel_scoring_engine_created": False,
            "parallel_mastery_engine_created": False,
            "parallel_dashboard_engine_created": False,
            "parallel_review_engine_created": False,
            "release_candidate_created": False,
            "role_based_identity_authorization_claimed": False,
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
            "speaking_capture_enabled": False,
            "listening_enabled": False,
            "audio_enabled": False,
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
        "e2e_release_acceptance_summary": deepcopy(acceptance),
        "production_safety": {
            "production_database_unchanged": True,
            "acceptance_used_isolated_database_clone": True,
            "acceptance_used_isolated_state_clone": True,
            "learner_progress_mutated_by_acceptance": False,
            "raw_response_serialized_to_safe_artifact": False,
        },
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def readback(*, receipt_path: Path) -> dict[str, Any]:
    receipt = read_json(receipt_path, "s18_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    if identity != (TASK_ID, SCHEMA_VERSION, PASS_STATUS, PRODUCT_STATUS, "NONE"):
        raise E2ERecoveryError("s18_receipt_contract_invalid")
    body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(body):
        raise E2ERecoveryError("s18_receipt_digest_invalid")
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "e2e_release_acceptance_summary": deepcopy(receipt["e2e_release_acceptance_summary"]),
        "capability_contract": deepcopy(receipt["capability_contract"]),
        "next_short_step": NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s17", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    snapshot = commands.add_parser("readback")
    snapshot.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "readback":
            print(json.dumps(readback(receipt_path=args.receipt), ensure_ascii=False, indent=2))
            return 0
        receipt, safe = materialize(s17_path=args.s17, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s18_nonaudio_learner_product_e2e_release_acceptance_recovery import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s17_path=args.s17,
        )
        if validation["error_count"]:
            raise E2ERecoveryError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        E2ERecoveryError,
        s17.DashboardReviewError,
        s17.s16.CanonicalLearningError,
        s17.s16.s15.ScoredJourneyError,
        s17.s16.core.m7.MasteryError,
        s17.s16.core.m8.ReviewRetentionError,
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
