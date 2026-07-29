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


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


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


def test_v121_product_starts_from_clean_pull_to_run_state(tmp_path: Path) -> None:
    port = _free_port()
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

    start = subprocess.run(
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
    assert "PASS_A1FS_V121_STARTED" in start.stdout

    try:
        login, headers = _request(
            port,
            "POST",
            "/auth/login",
            {"username": "local-user", "password": "local-password"},
            origin=f"http://127.0.0.1:{port}",
        )
        cookie = str(headers.get("Set-Cookie") or "").split(";", 1)[0]
        csrf = str(login["csrf_token"])
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
