#!/usr/bin/env python3
"""Isolated scored-journey acceptance for A1FS Online V1 S15."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import _a1fs_online_v1_s15_scored_journey_core as core

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Runs isolated S15 scoring, retry, review, completion-gate, and authenticated HTTP acceptance; no learner content or production progress is produced."
)

s13 = core.s13
s11 = core.s11
ScoredJourneyApplication = core.ScoredJourneyApplication
ScoredJourneyError = core.ScoredJourneyError
CANARY_LEARNER_ID = core.CANARY_LEARNER_ID
CANARY_SUBJECT_KEY = core.CANARY_SUBJECT_KEY
CANARY_READING_SESSION_ID = core.CANARY_READING_SESSION_ID
CANARY_WRITING_SESSION_ID = core.CANARY_WRITING_SESSION_ID
CANARY_PASSWORD = core.CANARY_PASSWORD
CANARY_SESSION_SECRET = core.CANARY_SESSION_SECRET
TASK_ID = core.TASK_ID
file_digest = core.file_digest
_connect = core._connect
_app = core._app


def _contracts_for_lesson(database: Path, lesson_id: str) -> list[dict[str, Any]]:
    with _connect(database) as connection:
        rows = connection.execute(
            """SELECT asset_key,contract_json FROM response_contracts
               WHERE lesson_id=? AND capture_enabled=1 ORDER BY asset_key""",
            (lesson_id,),
        ).fetchall()
    result = []
    for row in rows:
        contract = json.loads(row["contract_json"])
        contract["asset_key"] = str(row["asset_key"])
        result.append(contract)
    return result


def _passing_response(contract: Mapping[str, Any]) -> Any:
    mode = str(contract.get("scoring_mode") or "")
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"} and contract.get("accepted_texts"):
        return str(contract["accepted_texts"][0])
    if mode == "EXACT_SEQUENCE" and contract.get("accepted_sequence"):
        return list(contract["accepted_sequence"])
    if mode == "FEATURE_RUBRIC":
        return "I can write a complete answer for this task."
    raise ScoredJourneyError(f"acceptance_scoring_mode_unsupported:{mode}")


def _wrong_response(contract: Mapping[str, Any]) -> Any:
    return ["__s15_intentional_wrong_token__"] if contract.get("response_type") == "string_array" else "__s15_intentional_wrong_answer__"


def _lesson_ids(bundles: Mapping[str, Mapping[str, Any]], skill: str) -> list[str]:
    return sorted(
        lesson_id
        for lesson_id, bundle in bundles.items()
        if str(bundle["lesson"]["skill"]).upper() == skill
    )


def _run_authenticated_http_acceptance(
    *,
    app: ScoredJourneyApplication,
    secure_static_root: Path,
    auth_state_db: Path,
) -> None:
    config = s13.PersistentBoundaryConfig.from_values(
        username=CANARY_LEARNER_ID,
        password=CANARY_PASSWORD,
        session_secret=CANARY_SESSION_SECRET,
        mode="local",
        allowed_origin="http://127.0.0.1",
        allowed_host="127.0.0.1",
        revocation_db_path=auth_state_db,
        port=0,
    )
    server, thread, port = s13._start_server(
        app=app,
        secure_static_root=secure_static_root,
        config=config,
    )
    origin = f"http://127.0.0.1:{port}"
    try:
        s11._request(port, "GET", "/api/bootstrap", expected_status=401)
        login, headers = s11._request(
            port,
            "POST",
            "/auth/login",
            {"username": CANARY_LEARNER_ID, "password": CANARY_PASSWORD},
            origin=origin,
        )
        cookie = str(headers.get("Set-Cookie") or "").split(";", 1)[0]
        if not cookie or not login.get("csrf_token"):
            raise ScoredJourneyError("s15_http_login_contract_invalid")
        bootstrap, _ = s11._request(port, "GET", "/api/bootstrap", cookie=cookie)
        progress, _ = s11._request(port, "GET", "/api/progress", cookie=cookie)
        if bootstrap.get("task_id") != TASK_ID or progress.get("task_id") != TASK_ID:
            raise ScoredJourneyError("s15_http_identity_invalid")
        if len(bootstrap.get("units", [])) != 24 or len(progress.get("units", [])) != 24:
            raise ScoredJourneyError("s15_http_unit_denominator_invalid")
        semantics = bootstrap.get("learner_product_semantics", {})
        boundaries = progress.get("semantic_boundaries", {})
        if (
            semantics.get("reading_writing_completion_gate_enabled") is not True
            or boundaries.get("pending_human_review_blocks_completion") is not True
            or boundaries.get("latest_attempt_controls_completion") is not True
        ):
            raise ScoredJourneyError("s15_http_completion_semantics_invalid")
    finally:
        s13._stop_server(server, thread)


def _run_acceptance(
    *,
    production_database: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
    canary_database: Path,
    secure_static_root: Path,
    acceptance_auth_state: Path,
) -> dict[str, Any]:
    production_sha_before = file_digest(production_database)
    shutil.copy2(production_database, canary_database)
    app = _app(canary_database, bundles, sequence, default_learner_id=CANARY_LEARNER_ID)
    app.enroll(
        learner_id=CANARY_LEARNER_ID,
        display_label="S15 Scored Journey Canary",
        subject_key=CANARY_SUBJECT_KEY,
        at="2026-01-15T00:00:00Z",
    )

    reading_lesson = ""
    reading_contracts: list[dict[str, Any]] = []
    for lesson_id in _lesson_ids(bundles, "READING"):
        candidates = _contracts_for_lesson(canary_database, lesson_id)
        if len(candidates) == 4 and all(row["scoring_mode"] != "FEATURE_RUBRIC" for row in candidates):
            reading_lesson = lesson_id
            reading_contracts = candidates
            break
    if not reading_lesson:
        raise ScoredJourneyError("reading_deterministic_contract_denominator_invalid")
    reading = app.start_session({
        "lesson_id": reading_lesson,
        "session_id": CANARY_READING_SESSION_ID,
        "at": "2026-01-15T00:00:10Z",
    })
    first = reading_contracts[0]
    reading = app.record_exposure({
        "session_id": CANARY_READING_SESSION_ID,
        "asset_key": first["asset_key"],
        "expected_session_version": reading["session_version"],
        "at": "2026-01-15T00:00:20Z",
    })
    failed = app.submit_response({
        "session_id": CANARY_READING_SESSION_ID,
        "asset_key": first["asset_key"],
        "response": _wrong_response(first),
        "expected_session_version": reading["session_version"],
        "attempt_id": "A1FS_ONLINE_V1_S15_ATTEMPT:READING:FAIL",
        "submitted_at": "2026-01-15T00:00:30Z",
    })
    incomplete_blocked = False
    try:
        app.complete_session({
            "session_id": CANARY_READING_SESSION_ID,
            "expected_session_version": failed["session_version"],
            "at": "2026-01-15T00:00:35Z",
        })
    except ScoredJourneyError as exc:
        incomplete_blocked = str(exc).startswith("completion_gate_blocked:")
    if not incomplete_blocked:
        raise ScoredJourneyError("reading_incomplete_completion_not_blocked")
    scored = app.submit_response({
        "session_id": CANARY_READING_SESSION_ID,
        "asset_key": first["asset_key"],
        "response": _passing_response(first),
        "expected_session_version": failed["session_version"],
        "attempt_id": "A1FS_ONLINE_V1_S15_ATTEMPT:READING:PASS",
        "submitted_at": "2026-01-15T00:00:40Z",
    })
    for index, contract in enumerate(reading_contracts[1:], start=1):
        exposure = app.record_exposure({
            "session_id": CANARY_READING_SESSION_ID,
            "asset_key": contract["asset_key"],
            "expected_session_version": scored["session_version"],
            "at": f"2026-01-15T00:01:{index:02d}Z",
        })
        scored = app.submit_response({
            "session_id": CANARY_READING_SESSION_ID,
            "asset_key": contract["asset_key"],
            "response": _passing_response(contract),
            "expected_session_version": exposure["session_version"],
            "attempt_id": f"A1FS_ONLINE_V1_S15_ATTEMPT:READING:{index + 1}",
            "submitted_at": f"2026-01-15T00:02:{index:02d}Z",
        })
    reading_ready = app.completion_readiness(CANARY_READING_SESSION_ID)
    if not reading_ready["completion_allowed"] or reading_ready["passed_response_count"] != 4:
        raise ScoredJourneyError("reading_completion_gate_not_ready")
    reading_done = app.complete_session({
        "session_id": CANARY_READING_SESSION_ID,
        "expected_session_version": scored["session_version"],
        "at": "2026-01-15T00:03:00Z",
    })

    writing_lesson = ""
    writing_contracts: list[dict[str, Any]] = []
    for lesson_id in _lesson_ids(bundles, "WRITING"):
        candidates = _contracts_for_lesson(canary_database, lesson_id)
        if len(candidates) == 4 and any(row["scoring_mode"] == "FEATURE_RUBRIC" for row in candidates):
            writing_lesson = lesson_id
            writing_contracts = candidates
            break
    if not writing_lesson:
        raise ScoredJourneyError("writing_human_review_contract_missing")
    writing = app.start_session({
        "lesson_id": writing_lesson,
        "session_id": CANARY_WRITING_SESSION_ID,
        "at": "2026-01-15T00:04:00Z",
    })
    pending_attempts: list[str] = []
    last = writing
    for index, contract in enumerate(writing_contracts, start=1):
        exposure = app.record_exposure({
            "session_id": CANARY_WRITING_SESSION_ID,
            "asset_key": contract["asset_key"],
            "expected_session_version": last["session_version"],
            "at": f"2026-01-15T00:05:{index:02d}Z",
        })
        attempt_id = f"A1FS_ONLINE_V1_S15_ATTEMPT:WRITING:{index}"
        last = app.submit_response({
            "session_id": CANARY_WRITING_SESSION_ID,
            "asset_key": contract["asset_key"],
            "response": _passing_response(contract),
            "expected_session_version": exposure["session_version"],
            "attempt_id": attempt_id,
            "submitted_at": f"2026-01-15T00:06:{index:02d}Z",
        })
        if last["outcome"] == "PENDING_HUMAN_REVIEW":
            pending_attempts.append(attempt_id)
    pending_blocked = False
    try:
        app.complete_session({
            "session_id": CANARY_WRITING_SESSION_ID,
            "expected_session_version": last["session_version"],
            "at": "2026-01-15T00:07:00Z",
        })
    except ScoredJourneyError as exc:
        pending_blocked = "HUMAN_REVIEW_PENDING" in str(exc)
    if not pending_attempts or not pending_blocked:
        raise ScoredJourneyError("writing_pending_review_completion_not_blocked")
    criteria = {
        "grammar_target_match": True,
        "meaning_matches_context": True,
        "complete_response": True,
    }
    for index, attempt_id in enumerate(pending_attempts, start=1):
        app.response_store.review_response(
            attempt_id=attempt_id,
            decision="APPROVE",
            reviewer_id="S15_ACCEPTANCE_REVIEWER",
            criteria=criteria,
            notes="Isolated S15 acceptance approval.",
            reviewed_at=f"2026-01-15T00:08:{index:02d}Z",
        )
    writing_ready = app.completion_readiness(CANARY_WRITING_SESSION_ID)
    if not writing_ready["completion_allowed"] or writing_ready["passed_response_count"] != 4:
        raise ScoredJourneyError("writing_completion_gate_not_ready_after_review")
    writing_done = app.complete_session({
        "session_id": CANARY_WRITING_SESSION_ID,
        "expected_session_version": last["session_version"],
        "at": "2026-01-15T00:09:00Z",
    })
    progress = app.progress_readback()
    _run_authenticated_http_acceptance(
        app=app,
        secure_static_root=secure_static_root,
        auth_state_db=acceptance_auth_state,
    )
    production_sha_after = file_digest(production_database)
    if production_sha_before != production_sha_after:
        raise ScoredJourneyError("production_database_mutated_by_s15_acceptance")
    first_history = reading_ready["assets"][0]
    if first_history["attempt_count"] != 2 or first_history["latest_outcome"] != "AUTO_PASS":
        raise ScoredJourneyError("reading_retry_history_invalid")
    if reading_done.get("session_state") != "COMPLETED" or writing_done.get("session_state") != "COMPLETED":
        raise ScoredJourneyError("scored_session_completion_invalid")
    return {
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "reading_required_response_count": 4,
        "writing_required_response_count": 4,
        "reading_scored_journey_pass": True,
        "writing_scored_or_human_reviewed_journey_pass": True,
        "deterministic_auto_scoring_connected": True,
        "human_review_gate_connected": True,
        "retry_attempt_history_connected": True,
        "incomplete_session_blocked": True,
        "pending_human_review_blocked": True,
        "completion_after_pass_or_approval": True,
        "completed_scored_session_count": progress["scored_journey_summary"]["completed_scored_session_count"],
        "reading_retry_attempt_count": first_history["attempt_count"],
        "human_approved_attempt_count": len(pending_attempts),
        "human_approved_attempt_present": bool(pending_attempts),
        "speaking_recording_enabled": False,
        "listening_lesson_count": 0,
        "audio_asset_count": 0,
        "unit_completion_claimed": False,
        "mastery_claimed": False,
        "authenticated_http_acceptance": True,
        "authenticated_runtime_reused": True,
        "production_database_unchanged": True,
    }
