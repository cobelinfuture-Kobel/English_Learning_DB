from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_online_v1_s13_localhost_production_deployment as s13


def _config(path: Path) -> s13.PersistentBoundaryConfig:
    return s13.PersistentBoundaryConfig.from_values(
        username=s13.CANARY_USERNAME,
        password=s13.CANARY_PASSWORD,
        session_secret=s13.CANARY_SESSION_SECRET,
        mode="local",
        allowed_origin="http://127.0.0.1:8765",
        allowed_host="127.0.0.1",
        revocation_db_path=path,
        port=8765,
    )


def test_signed_session_survives_config_reconstruction(tmp_path: Path) -> None:
    state = tmp_path / "auth.sqlite3"
    first = _config(state)
    token, csrf, claims = first.issue_session(now=1_700_000_000)
    second = _config(state)
    verified = second.verify_session(token, now=1_700_000_001)
    assert verified["nonce"] == claims["nonce"]
    assert verified["csrf"] == csrf


def test_logout_revocation_survives_config_reconstruction(tmp_path: Path) -> None:
    state = tmp_path / "auth.sqlite3"
    first = _config(state)
    token, _, claims = first.issue_session(now=1_700_000_000)
    first.revoke(claims["nonce"])

    second = _config(state)
    with pytest.raises(s13.s11.SecureBoundaryError, match="session_revoked"):
        second.verify_session(token, now=1_700_000_001)

    with sqlite3.connect(state) as connection:
        assert connection.execute("SELECT COUNT(*) FROM revoked_sessions").fetchone()[0] == 1


def test_persistent_config_rejects_non_loopback_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("A1FS_S11_AUTH_USERNAME", s13.CANARY_USERNAME)
    monkeypatch.setenv("A1FS_S11_AUTH_PASSWORD", s13.CANARY_PASSWORD)
    monkeypatch.setenv("A1FS_S11_SESSION_SECRET", s13.CANARY_SESSION_SECRET)
    with pytest.raises(s13.LocalhostDeploymentError, match="non_loopback_host_forbidden"):
        s13.PersistentBoundaryConfig.from_environment(
            host="0.0.0.0",
            port=8765,
            revocation_db_path=tmp_path / "auth.sqlite3",
        )


def test_launch_bundle_contains_lifecycle_gates_without_secrets(tmp_path: Path) -> None:
    receipt = tmp_path / "localhost_production_deployment.private.json"
    auth_state = tmp_path / "runtime" / "auth.sqlite3"
    outputs = s13._write_launch_bundle(
        target_root=tmp_path / "bundle",
        receipt_path=receipt,
        auth_state_db=auth_state,
    )
    start = Path(outputs["start_script_path"]).read_text(encoding="utf-8")
    stop = Path(outputs["stop_script_path"]).read_text(encoding="utf-8")
    status = Path(outputs["status_script_path"]).read_text(encoding="utf-8")
    combined = "\n".join((start, stop, status))

    for marker in (
        "A1FS_S11_AUTH_USERNAME",
        "A1FS_S11_AUTH_PASSWORD",
        "A1FS_S11_SESSION_SECRET",
        "PORT_IN_USE",
        "A1FS_LOCALHOST_STARTED=PASS",
    ):
        assert marker in start
    assert "PID_OWNERSHIP_MISMATCH" in stop
    assert "A1FS_LOCALHOST_STOPPED=PASS" in stop
    assert "A1FS_LOCALHOST_STATUS=RUNNING" in status
    assert "PORT_OWNERSHIP_INVALID" in status
    assert s13.CANARY_PASSWORD not in combined
    assert s13.CANARY_SESSION_SECRET not in combined

    contract = s13.read_json(Path(outputs["deployment_contract_path"]), "contract")
    assert contract["host"] == "127.0.0.1"
    assert contract["port"] == 8765
    assert contract["secret_values_embedded"] is False
    assert contract["external_network_binding_allowed"] is False
    assert contract["cloudflare_enabled"] is False
    assert contract["audio_enabled"] is False


def test_safe_scan_rejects_secret_material() -> None:
    with pytest.raises(s13.LocalhostDeploymentError, match="private_content_leak:password"):
        s13.safe_scan({"deployment": {"password": "forbidden"}})
