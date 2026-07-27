from __future__ import annotations

from pathlib import Path

import pytest

from ulga.builders import build_a1fs_online_v1_s11_secure_authenticated_boundary as s11


class _FakeApp:
    def bootstrap(self) -> dict:
        return {
            "task_id": s11.s10.s09.TASK_ID,
            "validation_status": s11.s10.s09.PASS_STATUS,
            "product_status": s11.s10.s09.PRODUCT_STATUS,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "unit_count": 24,
            "units": [],
        }


def _source_static(root: Path) -> Path:
    source = root / "source"
    source.mkdir(parents=True)
    (source / "index.html").write_text(
        '<main><h1>A1FS 多單元學習旅程工作台</h1></main><script src="/app.js"></script>',
        encoding="utf-8",
    )
    (source / "app.js").write_text("const navigationLocked=()=>false;", encoding="utf-8")
    (source / "styles.css").write_text("body{}", encoding="utf-8")
    return source


def _config() -> s11.BoundaryConfig:
    return s11.BoundaryConfig.from_values(
        username=s11.CANARY_USERNAME,
        password=s11.CANARY_PASSWORD,
        session_secret=s11.CANARY_SESSION_SECRET,
        mode="local",
        allowed_origin="http://127.0.0.1",
        allowed_host="127.0.0.1",
    )


def test_s11_rejects_weak_or_shared_secrets() -> None:
    with pytest.raises(s11.SecureBoundaryError, match="auth_password_too_short"):
        s11.BoundaryConfig.from_values(
            username="learner",
            password="short",
            session_secret="x" * 40,
            mode="local",
            allowed_origin="http://127.0.0.1",
            allowed_host="127.0.0.1",
        )
    same = "same-secret-value-that-is-long-enough-123456"
    with pytest.raises(s11.SecureBoundaryError, match="auth_and_session_secrets_must_differ"):
        s11.BoundaryConfig.from_values(
            username="learner",
            password=same,
            session_secret=same,
            mode="local",
            allowed_origin="http://127.0.0.1",
            allowed_host="127.0.0.1",
        )


def test_s11_signed_session_detects_tamper_expiry_and_revocation() -> None:
    config = _config()
    token, csrf, claims = config.issue_session(now=1_700_000_000)
    assert config.verify_session(token, now=1_700_000_001)["csrf"] == csrf
    with pytest.raises(s11.SecureBoundaryError):
        config.verify_session(token + "tampered", now=1_700_000_001)
    with pytest.raises(s11.SecureBoundaryError, match="session_claims_invalid"):
        config.verify_session(token, now=claims["exp"])
    config.revoke(claims["nonce"])
    with pytest.raises(s11.SecureBoundaryError, match="session_revoked"):
        config.verify_session(token, now=1_700_000_001)


def test_s11_login_throttle_activates_after_five_failures() -> None:
    config = _config()
    for index in range(5):
        assert config.login_blocked("127.0.0.1", now=100 + index) is False
        config.record_login_failure("127.0.0.1", now=100 + index)
    assert config.login_blocked("127.0.0.1", now=105) is True
    assert config.login_blocked("127.0.0.1", now=1000) is False


def test_s11_reverse_proxy_mode_requires_https_exact_host_and_secure_cookie() -> None:
    with pytest.raises(s11.SecureBoundaryError, match="reverse_proxy_https_origin_required"):
        s11.BoundaryConfig.from_values(
            username=s11.CANARY_USERNAME,
            password=s11.CANARY_PASSWORD,
            session_secret=s11.CANARY_SESSION_SECRET,
            mode="reverse_proxy",
            allowed_origin="http://learn.example.test",
            allowed_host="learn.example.test",
        )
    config = s11.BoundaryConfig.from_values(
        username=s11.CANARY_USERNAME,
        password=s11.CANARY_PASSWORD,
        session_secret=s11.CANARY_SESSION_SECRET,
        mode="reverse_proxy",
        allowed_origin="https://learn.example.test",
        allowed_host="learn.example.test",
    )
    assert config.cookie_name == s11.COOKIE_SECURE
    assert config.secure_cookie is True
    config.validate_transport_headers(
        host_header="learn.example.test",
        forwarded_proto="https",
    )
    with pytest.raises(s11.SecureBoundaryError, match="reverse_proxy_https_forwarding_required"):
        config.validate_transport_headers(
            host_header="learn.example.test",
            forwarded_proto="http",
        )
    with pytest.raises(s11.SecureBoundaryError, match="host_header_not_allowed"):
        config.validate_transport_headers(
            host_header="evil.example.test",
            forwarded_proto="https",
        )


def test_s11_real_http_auth_csrf_origin_logout_and_security_headers(tmp_path) -> None:
    secure_static = tmp_path / "secure"
    s11._write_secure_static(_source_static(tmp_path), secure_static)
    config = _config()
    server, thread, port = s11._start_server(
        app=_FakeApp(),
        secure_static_root=secure_static,
        config=config,
    )
    origin = f"http://127.0.0.1:{port}"
    try:
        health, headers = s11._request(port, "GET", "/api/health")
        assert health["authentication_required"] is True
        assert headers["X-Frame-Options"] == "DENY"
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]

        value, _ = s11._request(port, "GET", "/api/bootstrap", expected_status=401)
        assert value["error"] == "authentication_required"

        value, _ = s11._request(
            port,
            "POST",
            "/auth/login",
            {"username": s11.CANARY_USERNAME, "password": "wrong-password"},
            origin=origin,
            expected_status=401,
        )
        assert value["error"] == "invalid_credentials"

        login, login_headers = s11._request(
            port,
            "POST",
            "/auth/login",
            {"username": s11.CANARY_USERNAME, "password": s11.CANARY_PASSWORD},
            origin=origin,
        )
        cookie_header = login_headers["Set-Cookie"]
        assert "HttpOnly" in cookie_header
        assert "SameSite=Strict" in cookie_header
        assert "Secure" not in cookie_header
        cookie = cookie_header.split(";", 1)[0]
        csrf = login["csrf_token"]

        session, _ = s11._request(port, "GET", "/auth/session", cookie=cookie)
        assert session["authenticated"] is True
        assert session["csrf_token"] == csrf
        bootstrap, _ = s11._request(port, "GET", "/api/bootstrap", cookie=cookie)
        assert bootstrap["unit_count"] == 24

        value, _ = s11._request(
            port,
            "POST",
            "/auth/logout",
            {},
            cookie=cookie,
            origin=origin,
            expected_status=403,
        )
        assert value["error"] == "csrf_token_invalid"
        value, _ = s11._request(
            port,
            "POST",
            "/auth/logout",
            {},
            cookie=cookie,
            csrf=csrf,
            origin="http://evil.invalid",
            expected_status=403,
        )
        assert value["error"] == "origin_not_allowed"
        logout, logout_headers = s11._request(
            port,
            "POST",
            "/auth/logout",
            {},
            cookie=cookie,
            csrf=csrf,
            origin=origin,
        )
        assert logout["authenticated"] is False
        assert "Max-Age=0" in logout_headers["Set-Cookie"]
        s11._request(port, "GET", "/api/bootstrap", cookie=cookie, expected_status=401)
    finally:
        s11._stop_server(server, thread)


def test_s11_secure_static_contains_login_and_csrf_bridge(tmp_path) -> None:
    target = tmp_path / "secure"
    s11._write_secure_static(_source_static(tmp_path), target)
    assert "/auth.js" in (target / "index.html").read_text(encoding="utf-8")
    auth_js = (target / "auth.js").read_text(encoding="utf-8")
    assert "X-CSRF-Token" in auth_js
    assert "/auth/session" in auth_js
    assert "/auth/logout" in auth_js
    assert "/auth/login" in (target / "login.js").read_text(encoding="utf-8")


def test_s11_non_loopback_server_binding_remains_forbidden(tmp_path) -> None:
    secure_static = tmp_path / "secure"
    s11._write_secure_static(_source_static(tmp_path), secure_static)
    with pytest.raises(s11.SecureBoundaryError, match="non_loopback_host_forbidden:0.0.0.0"):
        s11.SecureBoundaryServer(("0.0.0.0", 0), _FakeApp(), secure_static, _config())


def test_s11_safe_scan_rejects_serialized_secrets() -> None:
    with pytest.raises(s11.SecureBoundaryError, match="private_content_leak:password"):
        s11.safe_scan({"deployment_boundary": {"password": "forbidden"}})
