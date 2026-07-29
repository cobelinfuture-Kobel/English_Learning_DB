from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from ulga.builders.build_a1fs_online_v1_s11_secure_authenticated_boundary import (
    _request,
)


PRODUCT = REPOSITORY / "product" / "a1fs_v1_2_1"
APP_JS = PRODUCT / "runtime" / "secure_static" / "app.js"
WRITING_ANSWERS = {
    "S03:WRITING:135ce4b7fe634394e245f545": "an apple",
    "S03:WRITING:58afeb3ef3661289da074411": "a cat",
    "S03:WRITING:6ea8894e606f1e67b79096b4": "the book",
    "S03:WRITING:ec6160a55f3c0e7624f1dba7": ["an", "apple"],
    "U01E-S03-C02-W01": "a",
    "U01E-S03-C03-W01": ["an", "egg"],
    "U01E-S03-C04-W01": "There is a toy shop near the bus stop.",
}
WRITING_REVIEW_ASSET = "U01E-S03-C05-W01"


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _product_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(REPOSITORY),
            "A1FS_V121_STATE_ROOT": str(tmp_path / "state"),
            "A1FS_S11_AUTH_USERNAME": "local-user",
            "A1FS_S11_AUTH_PASSWORD": "local-password",
            "A1FS_S11_SESSION_SECRET": "local-session-secret-for-v121-tests",
        }
    )
    return env


def _start_product(port: int, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "product.a1fs_v1_2_1.runtime_server",
            "start",
            "--port",
            str(port),
        ],
        cwd=REPOSITORY,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )


def _stop_product(port: int, env: dict[str, str]) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "product.a1fs_v1_2_1.runtime_server",
            "stop",
            "--port",
            str(port),
        ],
        cwd=REPOSITORY,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )


def _login(port: int) -> tuple[str, str]:
    login, headers = _request(
        port,
        "POST",
        "/auth/login",
        {"username": "local-user", "password": "local-password"},
        origin=f"http://127.0.0.1:{port}",
    )
    return str(headers.get("Set-Cookie") or "").split(";", 1)[0], str(login["csrf_token"])


def _submit_response(
    *,
    port: int,
    cookie: str,
    csrf: str,
    session_id: str,
    session_version: int,
    asset_key: str,
    response: object,
    attempt_id: str,
) -> dict[str, object]:
    exposure, _ = _request(
        port,
        "POST",
        "/api/exposure",
        {
            "session_id": session_id,
            "asset_key": asset_key,
            "expected_session_version": session_version,
            "at": "2026-07-29T00:00:10Z",
        },
        cookie=cookie,
        csrf=csrf,
        origin=f"http://127.0.0.1:{port}",
    )
    scored, _ = _request(
        port,
        "POST",
        "/api/response",
        {
            "learner_id": "A1FS_V121_LOCAL_LEARNER",
            "session_id": session_id,
            "asset_key": asset_key,
            "response": response,
            "expected_session_version": exposure["session_version"],
            "attempt_id": attempt_id,
            "submitted_at": "2026-07-29T00:00:20Z",
        },
        cookie=cookie,
        csrf=csrf,
        origin=f"http://127.0.0.1:{port}",
    )
    return scored


def _run_writing_to_review(
    *,
    port: int,
    cookie: str,
    csrf: str,
    bootstrap: dict[str, object],
    session_id: str,
    attempt_prefix: str,
) -> dict[str, object]:
    unit01 = bootstrap["units"][0]
    writing = next(lane for lane in unit01["lanes"] if lane["skill"] == "WRITING")
    session, _ = _request(
        port,
        "POST",
        "/api/session/start",
        {
            "learner_id": "A1FS_V121_LOCAL_LEARNER",
            "lesson_id": writing["lesson_id"],
            "session_id": session_id,
            "at": "2026-07-29T00:00:00Z",
        },
        cookie=cookie,
        csrf=csrf,
        origin=f"http://127.0.0.1:{port}",
    )
    session_version = int(session["session_version"])
    passed = 0
    for asset in writing["assets"]:
        asset_key = asset["asset_key"]
        if asset_key == WRITING_REVIEW_ASSET:
            continue
        scored = _submit_response(
            port=port,
            cookie=cookie,
            csrf=csrf,
            session_id=session_id,
            session_version=session_version,
            asset_key=asset_key,
            response=WRITING_ANSWERS[asset_key],
            attempt_id=f"{attempt_prefix}-{passed + 1}",
        )
        assert scored["outcome"] == "AUTO_PASS"
        session_version = int(scored["session_version"])
        passed += 1
    assert passed == 7
    pending = _submit_response(
        port=port,
        cookie=cookie,
        csrf=csrf,
        session_id=session_id,
        session_version=session_version,
        asset_key=WRITING_REVIEW_ASSET,
        response="I can write a clear sentence about the picture.",
        attempt_id=f"{attempt_prefix}-REVIEW",
    )
    assert pending["outcome"] == "PENDING_HUMAN_REVIEW"
    gate = pending["completion_gate"]
    assert gate["passed_response_count"] == 7
    assert gate["required_response_count"] == 8
    assert gate["completion_allowed"] is False
    return pending


def _review_attempt(
    *,
    port: int,
    cookie: str,
    csrf: str,
    attempt_id: str,
    decision: str,
) -> dict[str, object]:
    queue_before, _ = _request(port, "GET", "/api/human-review", cookie=cookie)
    assert any(row["attempt_id"] == attempt_id for row in queue_before["review_queue"])
    reviewed, _ = _request(
        port,
        "POST",
        "/api/human-review/decision",
        {
            "attempt_id": attempt_id,
            "decision": decision,
            "criteria": {
                "grammar_target_match": True,
                "meaning_matches_context": True,
                "complete_response": True,
            },
            "notes": f"{decision} regression",
            "reviewed_at": "2026-07-29T00:00:30Z",
        },
        cookie=cookie,
        csrf=csrf,
        origin=f"http://127.0.0.1:{port}",
    )
    return reviewed


def test_v121_product_manifest_and_seed_are_pull_to_run_clean() -> None:
    manifest = json.loads((PRODUCT / "product_manifest.json").read_text(encoding="utf-8"))

    assert manifest["product_version"] == "1.2.1"
    assert manifest["serve_module"] == "product.a1fs_v1_2_1.runtime_server"
    assert manifest["install_script_required"] is False
    assert manifest["rebuild_required"] is False
    assert manifest["upgrade_required"] is False
    assert manifest["root_rename_required"] is False
    assert manifest["unit_count"] == 24
    assert manifest["lesson_count"] == 72
    assert manifest["asset_count"] == 277

    with sqlite3.connect(PRODUCT / "seeds" / "learner_runtime_seed.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM lesson_catalog").fetchone()[0] == 72
        assert connection.execute("SELECT COUNT(*) FROM lesson_assets").fetchone()[0] == 277
        assert connection.execute("SELECT COUNT(*) FROM response_contracts").fetchone()[0] == 277
        assert connection.execute("SELECT COUNT(*) FROM response_attempts").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM scoring_results").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM human_review_queue").fetchone()[0] == 0
        assert connection.execute("SELECT learner_id FROM learner_profiles").fetchone()[0] == "A1FS_V121_LOCAL_LEARNER"


def test_v121_review_frontend_posts_payload_and_refreshes_completion_gate() -> None:
    app_js = APP_JS.read_text(encoding="utf-8")

    assert "api('/api/human-review/decision',{attempt_id:row.attempt_id,decision,criteria,notes})" in app_js
    assert "method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify" not in app_js
    assert "if(response.completion_gate)renderGate(response.completion_gate)" in app_js
    assert "loadProgress(),loadDashboard(),loadHumanReviews()" in app_js
    assert "reviewSubmitting" in app_js
    assert "restore(pendingResume);await loadProgress()" in app_js


def test_v121_product_starts_from_clean_pull_to_run_state(tmp_path: Path) -> None:
    port = _free_port()
    env = _product_env(tmp_path)

    start = _start_product(port, env)
    assert "PASS_A1FS_V121_STARTED" in start.stdout

    try:
        cookie, csrf = _login(port)
        bootstrap, _ = _request(port, "GET", "/api/bootstrap", cookie=cookie)
        unit01 = bootstrap["units"][0]
        reading = next(lane for lane in unit01["lanes"] if lane["skill"] == "READING")
        asset_key = reading["assets"][0]["asset_key"]
        session, _ = _request(
            port,
            "POST",
            "/api/session/start",
            {
                "learner_id": "A1FS_V121_LOCAL_LEARNER",
                "lesson_id": reading["lesson_id"],
                "session_id": "V121-PULL-TO-RUN-READING",
                "at": "2026-07-29T00:00:00Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=f"http://127.0.0.1:{port}",
        )
        exposure, _ = _request(
            port,
            "POST",
            "/api/exposure",
            {
                "session_id": "V121-PULL-TO-RUN-READING",
                "asset_key": asset_key,
                "expected_session_version": session["session_version"],
                "at": "2026-07-29T00:00:10Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=f"http://127.0.0.1:{port}",
        )
        scored, _ = _request(
            port,
            "POST",
            "/api/response",
            {
                "learner_id": "A1FS_V121_LOCAL_LEARNER",
                "session_id": "V121-PULL-TO-RUN-READING",
                "asset_key": asset_key,
                "response": "a cat",
                "expected_session_version": exposure["session_version"],
                "attempt_id": "V121-PULL-TO-RUN-READING-ATTEMPT",
                "submitted_at": "2026-07-29T00:00:20Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=f"http://127.0.0.1:{port}",
        )
        progress, _ = _request(port, "GET", "/api/progress", cookie=cookie)

        assert len(bootstrap["units"]) == 24
        assert scored["outcome"] == "AUTO_PASS"
        assert scored["score"] == 1.0
        assert isinstance(progress["summary"], dict)
    finally:
        _stop_product(port, env)


def test_v121_writing_human_review_approval_completes_session_and_reject_defer_block(tmp_path: Path) -> None:
    port = _free_port()
    env = _product_env(tmp_path)

    start = _start_product(port, env)
    assert "PASS_A1FS_V121_STARTED" in start.stdout

    try:
        cookie, csrf = _login(port)
        bootstrap, _ = _request(port, "GET", "/api/bootstrap", cookie=cookie)
        assert len(bootstrap["units"]) == 24
        assert sum(len(unit["lanes"]) for unit in bootstrap["units"]) == 72
        assert sum(len(lane["assets"]) for unit in bootstrap["units"] for lane in unit["lanes"]) == 277

        pending = _run_writing_to_review(
            port=port,
            cookie=cookie,
            csrf=csrf,
            bootstrap=bootstrap,
            session_id="V121-HR01-APPROVE",
            attempt_prefix="V121-HR01-APPROVE",
        )
        reviewed = _review_attempt(
            port=port,
            cookie=cookie,
            csrf=csrf,
            attempt_id="V121-HR01-APPROVE-REVIEW",
            decision="APPROVE",
        )
        assert reviewed["review_result"]["outcome"] == "HUMAN_APPROVE"
        assert reviewed["pending_count"] == 0
        gate = reviewed["completion_gate"]
        assert gate["passed_response_count"] == 8
        assert gate["required_response_count"] == 8
        assert gate["completion_allowed"] is True
        review_asset = next(row for row in gate["assets"] if row["asset_key"] == WRITING_REVIEW_ASSET)
        assert review_asset["latest_outcome"] == "HUMAN_APPROVE"
        assert review_asset["completion_state"] == "PASSED"

        progress, _ = _request(port, "GET", "/api/progress", cookie=cookie)
        progress_gate = progress["active_scored_journey"]
        assert progress_gate["completion_allowed"] is True
        assert progress_gate["passed_response_count"] == 8
        assert progress_gate["required_response_count"] == 8

        completed, _ = _request(
            port,
            "POST",
            "/api/session/complete",
            {
                "session_id": "V121-HR01-APPROVE",
                "expected_session_version": pending["session_version"],
            },
            cookie=cookie,
            csrf=csrf,
            origin=f"http://127.0.0.1:{port}",
        )
        assert completed["session_state"] == "COMPLETED"

        for decision, expected_outcome in [
            ("REJECT", "HUMAN_REJECT"),
            ("DEFER", "HUMAN_DEFER"),
        ]:
            session_id = f"V121-HR01-{decision}"
            attempt_prefix = f"V121-HR01-{decision}"
            pending = _run_writing_to_review(
                port=port,
                cookie=cookie,
                csrf=csrf,
                bootstrap=bootstrap,
                session_id=session_id,
                attempt_prefix=attempt_prefix,
            )
            reviewed = _review_attempt(
                port=port,
                cookie=cookie,
                csrf=csrf,
                attempt_id=f"{attempt_prefix}-REVIEW",
                decision=decision,
            )
            assert reviewed["review_result"]["outcome"] == expected_outcome
            assert reviewed["completion_gate"]["completion_allowed"] is False
            assert reviewed["completion_gate"]["passed_response_count"] == 7
            failed_complete, _ = _request(
                port,
                "POST",
                "/api/session/complete",
                {
                    "session_id": session_id,
                    "expected_session_version": pending["session_version"],
                },
                cookie=cookie,
                csrf=csrf,
                origin=f"http://127.0.0.1:{port}",
                expected_status=400,
            )
            assert "completion_gate_blocked" in failed_complete["error"]
            _request(
                port,
                "POST",
                "/api/session/abandon",
                {
                    "session_id": session_id,
                    "expected_session_version": pending["session_version"],
                },
                cookie=cookie,
                csrf=csrf,
                origin=f"http://127.0.0.1:{port}",
            )
    finally:
        _stop_product(port, env)
