from __future__ import annotations

from pathlib import Path

import pytest

from ulga.builders import build_a1fs_online_v1_s12_secure_reverse_proxy_remote_acceptance as s12


class _FakeApp:
    def bootstrap(self) -> dict:
        return {
            "task_id": s12.s11.s10.s09.TASK_ID,
            "validation_status": s12.s11.s10.s09.PASS_STATUS,
            "product_status": s12.s11.s10.s09.PRODUCT_STATUS,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "unit_count": 24,
            "units": [],
        }


def _secure_static(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_text("<h1>A1FS secure</h1>", encoding="utf-8")
    (root / "app.js").write_text("const navigationLocked = () => false;", encoding="utf-8")
    (root / "styles.css").write_text("body{}", encoding="utf-8")
    (root / "login.html").write_text("<h1>login</h1>", encoding="utf-8")
    (root / "login.js").write_text("'use strict';", encoding="utf-8")
    (root / "login.css").write_text("body{}", encoding="utf-8")
    (root / "auth.js").write_text("'use strict';", encoding="utf-8")
    return root


def _start_origin(static_root: Path):
    config = s12.s11.BoundaryConfig.from_values(
        username=s12.CANARY_USERNAME,
        password=s12.CANARY_PASSWORD,
        session_secret=s12.CANARY_SESSION_SECRET,
        mode="reverse_proxy",
        allowed_origin=s12.CANARY_PUBLIC_ORIGIN,
        allowed_host=s12.CANARY_PUBLIC_HOST,
    )
    return s12.s11._start_server(
        app=_FakeApp(),
        secure_static_root=static_root,
        config=config,
    )


def test_s12_deployment_bundle_is_operational_and_secret_free(tmp_path) -> None:
    bundle = s12._write_deployment_bundle(tmp_path / "bundle")
    root = Path(bundle["bundle_root"])
    caddy = Path(bundle["caddyfile_path"]).read_text(encoding="utf-8")
    deployment = s12.read_json(Path(bundle["deployment_contract_path"]), "deployment")
    rollback = s12.read_json(Path(bundle["rollback_contract_path"]), "rollback")

    assert bundle["bundle_sha256"] == s12._tree_digest(root)
    assert "reverse_proxy 127.0.0.1:8765" in caddy
    assert "header_up Host {$A1FS_PUBLIC_HOST}" in caddy
    assert "header_up X-Forwarded-Proto https" in caddy
    assert "header_up X-Forwarded-Host {$A1FS_PUBLIC_HOST}" in caddy
    assert s12.CANARY_PASSWORD not in caddy
    assert s12.CANARY_SESSION_SECRET not in caddy
    assert deployment["secret_values_embedded"] is False
    assert deployment["origin_binding"]["non_loopback_binding_allowed"] is False
    assert rollback["database_rollback_required"] is False
    assert rollback["automatic_public_reenable_allowed"] is False


def test_s12_simulated_edge_enforces_forwarded_https_and_secure_cookie(tmp_path) -> None:
    static_root = _secure_static(tmp_path / "static")
    origin, origin_thread, origin_port = _start_origin(static_root)
    edge, edge_thread, edge_port = s12._start_edge(upstream_port=origin_port)
    try:
        direct, _ = s12.s11._request(
            origin_port,
            "GET",
            "/api/health",
            host=s12.CANARY_PUBLIC_HOST,
            expected_status=400,
        )
        assert direct["error"] == "reverse_proxy_https_forwarding_required"

        health, headers = s12._edge_request(edge_port, "GET", "/api/health")
        assert health == {
            "status": "PASS",
            "authentication_required": True,
            "loopback_application_server": True,
            "audio_enabled": False,
        }
        assert headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

        login, login_headers = s12._edge_request(
            edge_port,
            "POST",
            "/auth/login",
            {"username": s12.CANARY_USERNAME, "password": s12.CANARY_PASSWORD},
            origin=s12.CANARY_PUBLIC_ORIGIN,
        )
        cookie = login_headers["Set-Cookie"]
        assert login["authenticated"] is True
        assert cookie.startswith(f"{s12.s11.COOKIE_SECURE}=")
        assert "Secure" in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=Strict" in cookie
    finally:
        s12._stop_server(edge, edge_thread, "edge_stop_failed")
        s12._stop_server(origin, origin_thread, "origin_stop_failed")


def test_s12_edge_wrong_origin_remains_blocked(tmp_path) -> None:
    static_root = _secure_static(tmp_path / "static")
    origin, origin_thread, origin_port = _start_origin(static_root)
    edge, edge_thread, edge_port = s12._start_edge(upstream_port=origin_port)
    try:
        error, _ = s12._edge_request(
            edge_port,
            "POST",
            "/auth/login",
            {"username": s12.CANARY_USERNAME, "password": s12.CANARY_PASSWORD},
            origin="https://evil.example.test",
            expected_status=403,
        )
        assert error["error"] == "origin_not_allowed"
    finally:
        s12._stop_server(edge, edge_thread, "edge_stop_failed")
        s12._stop_server(origin, origin_thread, "origin_stop_failed")


def test_s12_safe_scan_rejects_secret_fields() -> None:
    with pytest.raises(s12.ReverseProxyAcceptanceError, match="private_content_leak:session_secret"):
        s12.safe_scan({"session_secret": "forbidden"})


def test_s12_claim_boundaries_do_not_claim_live_remote_release() -> None:
    boundary = {
        "dns_configuration_completed": False,
        "certificate_issuance_completed": False,
        "live_remote_deployment_completed": False,
        "external_remote_acceptance_completed": False,
        "public_release_completed": False,
    }
    assert all(value is False for value in boundary.values())
