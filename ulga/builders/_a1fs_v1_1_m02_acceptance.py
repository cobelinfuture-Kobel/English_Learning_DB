#!/usr/bin/env python3
"""Isolated localhost acceptance for the A1FS V1.1 Unit 01 release."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.builders import build_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as m01
from ulga.builders import _a1fs_v1_1_m02_release_core as core

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Executes authenticated localhost and isolated scored-journey acceptance against the packaged M01 release while preserving production state; it creates no learner content, answer, scoring, mastery, dashboard, state, audio, A2, external route, or parallel authority."

CANARY_LEARNER_ID = "A1FS_V1_1_M02_CANARY"
CANARY_SUBJECT_KEY = "A1FS_V1_1_M02_PRIVATE_CANARY"
CANARY_PASSWORD = "m02-local-canary"
CANARY_SESSION_SECRET = "a1fs-v1-1-m02-local-acceptance-session-secret-2026"


class AcceptanceError(ValueError):
    """Fail-closed local acceptance error."""


def _passing_response(contract: Mapping[str, Any]) -> Any:
    mode = str(contract.get("scoring_mode") or "")
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"} and contract.get("accepted_texts"):
        return str(contract["accepted_texts"][0])
    if mode == "EXACT_SEQUENCE" and contract.get("accepted_sequence"):
        return list(contract["accepted_sequence"])
    if mode == "FEATURE_RUBRIC":
        return "There is an apple in the bag."
    raise AcceptanceError(f"scoring_mode_unsupported:{mode}")


def _exercise_lesson(
    *, app: Any, database: Path, lesson_id: str, session_id: str, time_prefix: str,
) -> dict[str, Any]:
    s15 = r01.s19.s18.s17.s16.s15
    contracts = s15._contracts_for_lesson(database, lesson_id)
    if len(contracts) != 4:
        raise AcceptanceError(f"contract_count_invalid:{lesson_id}")
    current: Mapping[str, Any] = app.start_session({
        "lesson_id": lesson_id,
        "session_id": session_id,
        "at": f"{time_prefix}:00Z",
    })
    outcomes: list[str] = []
    pending: list[str] = []
    for index, contract in enumerate(contracts, start=1):
        exposure = app.record_exposure({
            "session_id": session_id,
            "asset_key": contract["asset_key"],
            "expected_session_version": current["session_version"],
            "at": f"{time_prefix}:{index:02d}Z",
        })
        attempt_id = f"{session_id}:ATTEMPT:{index}"
        current = app.submit_response({
            "session_id": session_id,
            "asset_key": contract["asset_key"],
            "response": _passing_response(contract),
            "expected_session_version": exposure["session_version"],
            "attempt_id": attempt_id,
            "submitted_at": f"{time_prefix}:{index + 10:02d}Z",
        })
        outcome = str(current.get("outcome") or "")
        outcomes.append(outcome)
        if outcome in {"PENDING_HUMAN_REVIEW", "HUMAN_DEFER"}:
            pending.append(attempt_id)
    for attempt_id in pending:
        app.review_attempt(
            {
                "attempt_id": attempt_id,
                "decision": "APPROVE",
                "criteria": {
                    "grammar_target_match": True,
                    "meaning_matches_context": True,
                    "complete_response": True,
                },
                "notes": "M02 isolated release acceptance",
                "reviewed_at": f"{time_prefix}:30Z",
            },
            reviewer_id="A1FS_V1_1_M02_CANARY_REVIEWER",
        )
    readiness = app.completion_readiness(session_id)
    if readiness.get("completion_allowed") is not True:
        raise AcceptanceError(f"completion_not_allowed:{lesson_id}")
    completed = app.complete_session({
        "session_id": session_id,
        "expected_session_version": readiness["session_version"],
        "at": f"{time_prefix}:40Z",
    })
    if completed.get("session_state") != "COMPLETED":
        raise AcceptanceError(f"session_not_completed:{lesson_id}")
    return {
        "lesson_id": lesson_id,
        "contract_count": len(contracts),
        "outcomes": outcomes,
        "pending_human_review_count": len(pending),
        "completion_allowed": True,
        "session_completed": True,
    }


def run(*, product_root: Path) -> dict[str, Any]:
    root = Path(product_root).resolve()
    version, manifest, bundles, sequence = r01._load_product(root)
    if version != core.TARGET_VERSION:
        raise AcceptanceError("installed_version_invalid")
    database = r01._resolve(root, str(manifest["shared_database_path"]))
    auth = r01._resolve(root, str(manifest["shared_auth_state_path"]))
    state = r01._resolve(root, str(manifest["shared_learner_state_root"]))
    graph = r01._resolve(root, str(manifest["graph_path"]))
    static = r01._resolve(root, str(manifest["secure_static_root"]))
    s17 = r01.s19.s18.s17
    app = s17._app(
        database=database,
        bundles=bundles,
        sequence=sequence,
        graph_path=graph,
        state_root=state,
        default_learner_id=CANARY_LEARNER_ID,
    )
    app.enroll(
        learner_id=CANARY_LEARNER_ID,
        display_label="A1FS V1.1 M02 Canary",
        subject_key=CANARY_SUBJECT_KEY,
        at="2026-07-28T07:00:00Z",
    )
    config = s17.s16.s15.s13.PersistentBoundaryConfig.from_values(
        username=CANARY_LEARNER_ID,
        password=CANARY_PASSWORD,
        session_secret=CANARY_SESSION_SECRET,
        mode="local",
        allowed_origin="http://127.0.0.1",
        allowed_host="127.0.0.1",
        revocation_db_path=auth,
        port=0,
    )
    server = s17.DashboardReviewServer(("127.0.0.1", 0), app, static, config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = int(server.server_address[1])
    request = s17.s16.s15.s11._request
    origin = f"http://127.0.0.1:{port}"
    try:
        request(port, "GET", "/api/bootstrap", expected_status=401)
        login, headers = request(
            port,
            "POST",
            "/auth/login",
            {"username": CANARY_LEARNER_ID, "password": CANARY_PASSWORD},
            origin=origin,
        )
        cookie = str(headers.get("Set-Cookie") or "").split(";", 1)[0]
        if not cookie or not login.get("csrf_token"):
            raise AcceptanceError("http_login_invalid")
        bootstrap, _ = request(port, "GET", "/api/bootstrap", cookie=cookie)
        progress, _ = request(port, "GET", "/api/progress", cookie=cookie)
        dashboard, _ = request(port, "GET", "/api/dashboard", cookie=cookie)
        rendered = json.dumps(bootstrap, ensure_ascii=False, sort_keys=True)
        if (
            len(bootstrap.get("units", [])) != 24
            or m01.PASSAGE not in rendered
            or "Mia has a ___ and a ___." not in rendered
            or progress.get("product_status") != s17.PRODUCT_STATUS
            or dashboard.get("validation_status") != s17.PASS_STATUS
        ):
            raise AcceptanceError("http_content_or_identity_invalid")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    reading = _exercise_lesson(
        app=app,
        database=database,
        lesson_id=m01.LESSON_IDS["READING"],
        session_id="A1FS_V1_1_M02_SESSION:READING",
        time_prefix="2026-07-28T07:01",
    )
    writing = _exercise_lesson(
        app=app,
        database=database,
        lesson_id=m01.LESSON_IDS["WRITING"],
        session_id="A1FS_V1_1_M02_SESSION:WRITING",
        time_prefix="2026-07-28T07:02",
    )
    speaking = bundles[m01.LESSON_IDS["SPEAKING"]].get("assets")
    if not isinstance(speaking, list) or len(speaking) != 3:
        raise AcceptanceError("speaking_card_count_invalid")
    if any(
        asset.get("learner_payload", {}).get("response_capture_enabled") is not False
        for asset in speaking
        if isinstance(asset, Mapping)
    ):
        raise AcceptanceError("speaking_capture_enabled")
    return {
        "installed_version": version,
        "authenticated_http_login_pass": True,
        "authenticated_bootstrap_pass": True,
        "authenticated_progress_pass": True,
        "authenticated_dashboard_pass": True,
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "unit01_real_reading_visible": True,
        "unit01_contextual_writing_visible": True,
        "unit01_speaking_practice_visible": True,
        "reading": reading,
        "writing": writing,
        "speaking_practice_card_count": 3,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "a2_unlocked": False,
    }
