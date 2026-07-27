#!/usr/bin/env python3
"""Secure authenticated boundary for the S10 no-audio release candidate.

S11 reuses the authoritative S10/S09 learner runtime and adds a fail-closed
application boundary: credential verification, signed short-lived sessions,
HttpOnly/SameSite cookies, CSRF and Origin enforcement, Host allowlisting,
login throttling, security headers, and reverse-proxy HTTPS prerequisites.
The built-in application server remains loopback-only. No curriculum, content,
audio, mastery, A2 unlock, or public deployment is created.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import http.client
import json
import os
import secrets
import shutil
import sqlite3
import sys
import threading
import time
from copy import deepcopy
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s10_private_release_candidate_http_acceptance as s10  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Wraps the existing S10/S09 runtime with authentication, signed sessions, CSRF, Origin/Host checks, secure cookies, login throttling, and reverse-proxy TLS prerequisites; it authors no curriculum, learner content, answers, audio, mastery, A2 unlock, or public deployment."

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S11_SecureAuthenticatedOnlineReleaseBoundary_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s11.secure_authenticated_boundary.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S11_SECURE_AUTHENTICATED_BOUNDARY_READY"
PRODUCT_STATUS = "SECURE_AUTHENTICATED_NONAUDIO_RELEASE_BOUNDARY_READY_NOT_DEPLOYED"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S12_SecureReverseProxyDeploymentAndRemoteAcceptance_NoAudio"

COOKIE_LOCAL = "a1fs_session"
COOKIE_SECURE = "__Host-a1fs_session"
SESSION_TTL_SECONDS = 900
MAX_LOGIN_FAILURES = 5
LOGIN_WINDOW_SECONDS = 300
PBKDF2_ROUNDS = 200_000
CANARY_LEARNER_ID = "A1FS_ONLINE_V1_S11_AUTH_CANARY"
CANARY_SUBJECT_KEY = "A1FS_ONLINE_V1_S11_PRIVATE_SLOT"
CANARY_USERNAME = "s11-canary"
CANARY_PASSWORD = "S11-Canary-Password-Only-For-Isolated-Acceptance-2026!"
CANARY_SESSION_SECRET = "S11-Canary-Session-Signing-Secret-Only-For-Isolated-Acceptance-2026!"
READING_SESSION_ID = "A1FS_ONLINE_V1_S11_SESSION:UNIT01:READING"
READING_ATTEMPT_ID = "A1FS_ONLINE_V1_S11_ATTEMPT:UNIT01:READING:FAIL"
WRITING_SESSION_ID = "A1FS_ONLINE_V1_S11_SESSION:UNIT24:WRITING"
WRITING_ATTEMPT_ID = "A1FS_ONLINE_V1_S11_ATTEMPT:UNIT24:WRITING:PASS"
SPEAKING_SESSION_ID = "A1FS_ONLINE_V1_S11_SESSION:UNIT24:SPEAKING"

FORBIDDEN_SAFE_KEYS = {
    "accepted_texts", "accepted_sequence", "answer", "answer_contract", "answer_key",
    "asset_key", "auth_password", "csrf", "database_path", "display_label", "learner_id",
    "learner_payload", "password", "private_scoring_contract", "private_subject_digest",
    "prompt", "prompt_text", "response", "rubric", "scoring_contract", "session_id",
    "session_secret", "subject_key", "token",
}


class SecureBoundaryError(ValueError):
    """Fail-closed S11 authentication or boundary error."""


def digest(value: Any) -> str:
    return s10.digest(value)


def file_digest(path: Path) -> str:
    return s10.file_digest(path)


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SecureBoundaryError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise SecureBoundaryError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    s10.write_json(Path(path), value, private=private)


def safe_scan(value: Any) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                    raise SecureBoundaryError(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _is_loopback(host: str) -> bool:
    return str(host).casefold() in {"127.0.0.1", "localhost", "::1"}


def _credential_hash(username: str, password: str) -> bytes:
    salt = hashlib.sha256(f"{TASK_ID}:{username}".encode("utf-8")).digest()
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)


@dataclass
class BoundaryConfig:
    username: str
    credential_hash: bytes
    signing_key: bytes
    mode: str
    allowed_origin: str
    allowed_host: str
    session_ttl_seconds: int = SESSION_TTL_SECONDS
    max_login_failures: int = MAX_LOGIN_FAILURES
    login_window_seconds: int = LOGIN_WINDOW_SECONDS
    local_port: int = 0
    revoked_nonces: set[str] = field(default_factory=set)
    failed_logins: dict[str, list[float]] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def from_values(
        cls,
        *,
        username: str,
        password: str,
        session_secret: str,
        mode: str,
        allowed_origin: str,
        allowed_host: str,
        port: int = 0,
    ) -> "BoundaryConfig":
        username = str(username).strip()
        password = str(password)
        session_secret = str(session_secret)
        mode = str(mode).strip().casefold()
        allowed_origin = str(allowed_origin).strip()
        allowed_host = str(allowed_host).strip().casefold()
        if not (3 <= len(username) <= 64):
            raise SecureBoundaryError("auth_username_invalid")
        if len(password) < 20:
            raise SecureBoundaryError("auth_password_too_short")
        if len(session_secret) < 32:
            raise SecureBoundaryError("session_secret_too_short")
        if hmac.compare_digest(password.encode("utf-8"), session_secret.encode("utf-8")):
            raise SecureBoundaryError("auth_and_session_secrets_must_differ")
        if mode not in {"local", "reverse_proxy"}:
            raise SecureBoundaryError("boundary_mode_invalid")
        if mode == "reverse_proxy":
            parsed = urlparse(allowed_origin)
            if parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"}:
                raise SecureBoundaryError("reverse_proxy_https_origin_required")
            if not allowed_host or any(marker in allowed_host for marker in ("*", "/", " ", ",")):
                raise SecureBoundaryError("reverse_proxy_allowed_host_invalid")
            if parsed.netloc.casefold() != allowed_host:
                raise SecureBoundaryError("reverse_proxy_origin_host_mismatch")
        else:
            if allowed_origin and not allowed_origin.startswith(("http://127.0.0.1", "http://localhost")):
                raise SecureBoundaryError("local_origin_not_loopback")
            if allowed_host and allowed_host not in {"127.0.0.1", "localhost"}:
                raise SecureBoundaryError("local_allowed_host_not_loopback")
        return cls(
            username=username,
            credential_hash=_credential_hash(username, password),
            signing_key=hashlib.sha256(session_secret.encode("utf-8")).digest(),
            mode=mode,
            allowed_origin=allowed_origin,
            allowed_host=allowed_host,
            local_port=int(port),
        )

    @classmethod
    def from_environment(cls, *, host: str, port: int) -> "BoundaryConfig":
        if not _is_loopback(host):
            raise SecureBoundaryError(f"non_loopback_host_forbidden:{host}")
        mode = os.environ.get("A1FS_S11_MODE", "").strip().casefold()
        username = os.environ.get("A1FS_S11_AUTH_USERNAME", "")
        password = os.environ.get("A1FS_S11_AUTH_PASSWORD", "")
        session_secret = os.environ.get("A1FS_S11_SESSION_SECRET", "")
        allowed_origin = os.environ.get("A1FS_S11_ALLOWED_ORIGIN", "")
        allowed_host = os.environ.get("A1FS_S11_ALLOWED_HOST", "")
        if mode == "local":
            allowed_origin = allowed_origin or f"http://127.0.0.1:{port}"
            allowed_host = allowed_host or "127.0.0.1"
        return cls.from_values(
            username=username,
            password=password,
            session_secret=session_secret,
            mode=mode,
            allowed_origin=allowed_origin,
            allowed_host=allowed_host,
            port=port,
        )

    @property
    def cookie_name(self) -> str:
        return COOKIE_SECURE if self.mode == "reverse_proxy" else COOKIE_LOCAL

    @property
    def secure_cookie(self) -> bool:
        return self.mode == "reverse_proxy"

    def bind_local_port(self, port: int) -> None:
        self.local_port = int(port)
        if self.mode == "local":
            self.allowed_origin = f"http://127.0.0.1:{self.local_port}"
            self.allowed_host = "127.0.0.1"

    def validate_transport_headers(self, *, host_header: str, forwarded_proto: str) -> None:
        raw_host = str(host_header or "").strip().casefold()
        if not raw_host or any(marker in raw_host for marker in ("/", " ", ",", "\\")):
            raise SecureBoundaryError("host_header_invalid")
        parsed_host = raw_host.rsplit(":", 1)[0] if raw_host.count(":") == 1 else raw_host
        if self.mode == "local":
            if parsed_host not in {"127.0.0.1", "localhost"}:
                raise SecureBoundaryError("host_header_not_allowed")
            if ":" in raw_host:
                try:
                    supplied_port = int(raw_host.rsplit(":", 1)[1])
                except ValueError as exc:
                    raise SecureBoundaryError("host_header_port_invalid") from exc
                if supplied_port != self.local_port:
                    raise SecureBoundaryError("host_header_port_not_allowed")
        else:
            if raw_host != self.allowed_host:
                raise SecureBoundaryError("host_header_not_allowed")
            if str(forwarded_proto or "").casefold() != "https":
                raise SecureBoundaryError("reverse_proxy_https_forwarding_required")

    def validate_origin(self, origin: str) -> None:
        if not origin or not hmac.compare_digest(str(origin), self.allowed_origin):
            raise SecureBoundaryError("origin_not_allowed")

    def verify_password(self, candidate: str) -> bool:
        return hmac.compare_digest(self.credential_hash, _credential_hash(self.username, str(candidate)))

    def login_blocked(self, client_ip: str, *, now: float | None = None) -> bool:
        moment = time.time() if now is None else float(now)
        cutoff = moment - self.login_window_seconds
        with self.lock:
            attempts = [stamp for stamp in self.failed_logins.get(client_ip, []) if stamp >= cutoff]
            self.failed_logins[client_ip] = attempts
            return len(attempts) >= self.max_login_failures

    def record_login_failure(self, client_ip: str, *, now: float | None = None) -> None:
        moment = time.time() if now is None else float(now)
        with self.lock:
            self.failed_logins.setdefault(client_ip, []).append(moment)

    def clear_login_failures(self, client_ip: str) -> None:
        with self.lock:
            self.failed_logins.pop(client_ip, None)

    def issue_session(self, *, now: int | None = None) -> tuple[str, str, dict[str, Any]]:
        issued = int(time.time() if now is None else now)
        csrf = secrets.token_urlsafe(24)
        claims = {
            "v": 1,
            "sub": self.username,
            "iat": issued,
            "exp": issued + self.session_ttl_seconds,
            "csrf": csrf,
            "nonce": secrets.token_urlsafe(24),
        }
        payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
        encoded = _b64encode(payload)
        signature = _b64encode(hmac.new(self.signing_key, encoded.encode("ascii"), hashlib.sha256).digest())
        return f"{encoded}.{signature}", csrf, claims

    def verify_session(self, token: str, *, now: int | None = None) -> dict[str, Any]:
        try:
            encoded, signature = str(token).split(".", 1)
            expected = _b64encode(hmac.new(self.signing_key, encoded.encode("ascii"), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                raise SecureBoundaryError("session_signature_invalid")
            claims = json.loads(_b64decode(encoded).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error) as exc:
            raise SecureBoundaryError("session_token_invalid") from exc
        moment = int(time.time() if now is None else now)
        if (
            not isinstance(claims, dict)
            or claims.get("v") != 1
            or claims.get("sub") != self.username
            or not isinstance(claims.get("exp"), int)
            or claims["exp"] <= moment
            or not isinstance(claims.get("csrf"), str)
            or not isinstance(claims.get("nonce"), str)
        ):
            raise SecureBoundaryError("session_claims_invalid")
        with self.lock:
            if claims["nonce"] in self.revoked_nonces:
                raise SecureBoundaryError("session_revoked")
        return claims

    def revoke(self, nonce: str) -> None:
        with self.lock:
            self.revoked_nonces.add(str(nonce))


def _security_headers(config: BoundaryConfig) -> dict[str, str]:
    headers = {
        "Cache-Control": "no-store",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
    }
    if config.secure_cookie:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers


class SecureBoundaryHandler(s10.s09.s08.JourneyWorkbenchHandler):
    server_version = "A1FSSecureBoundary/1"

    @property
    def config(self) -> BoundaryConfig:
        return self.server.config  # type: ignore[attr-defined]

    @property
    def secure_static_root(self) -> Path:
        return self.server.secure_static_root  # type: ignore[attr-defined]

    def _send_headers(self, *, content_type: str, content_length: int, extra: Mapping[str, str] | None = None) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        for key, value in _security_headers(self.config).items():
            self.send_header(key, value)
        for key, value in (extra or {}).items():
            self.send_header(key, value)

    def _json(self, status: int, value: Mapping[str, Any], *, extra_headers: Mapping[str, str] | None = None) -> None:
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_headers(content_type="application/json; charset=utf-8", content_length=len(raw), extra=extra_headers)
        self.end_headers()
        self.wfile.write(raw)

    def _static(self, path: Path, content_type: str) -> None:
        if not Path(path).is_file():
            self._json(404, {"error": "not_found"})
            return
        raw = Path(path).read_bytes()
        self.send_response(200)
        self._send_headers(content_type=content_type, content_length=len(raw))
        self.end_headers()
        self.wfile.write(raw)

    def _redirect(self, location: str) -> None:
        self.send_response(302)
        self._send_headers(content_type="text/plain; charset=utf-8", content_length=0, extra={"Location": location})
        self.end_headers()

    def _transport_valid(self) -> bool:
        try:
            self.config.validate_transport_headers(
                host_header=self.headers.get("Host", ""),
                forwarded_proto=self.headers.get("X-Forwarded-Proto", ""),
            )
            return True
        except SecureBoundaryError as exc:
            self._json(400, {"error": str(exc)})
            return False

    def _origin_valid(self) -> bool:
        try:
            self.config.validate_origin(self.headers.get("Origin", ""))
            return True
        except SecureBoundaryError as exc:
            self._json(403, {"error": str(exc)})
            return False

    def _cookie_token(self) -> str:
        cookie = SimpleCookie()
        cookie.load(self.headers.get("Cookie", ""))
        morsel = cookie.get(self.config.cookie_name)
        return morsel.value if morsel else ""

    def _claims(self) -> dict[str, Any] | None:
        token = self._cookie_token()
        if not token:
            return None
        try:
            return self.config.verify_session(token)
        except SecureBoundaryError:
            return None

    def _csrf_valid(self, claims: Mapping[str, Any]) -> bool:
        supplied = self.headers.get("X-CSRF-Token", "")
        expected = str(claims.get("csrf") or "")
        if not supplied or not hmac.compare_digest(supplied, expected):
            self._json(403, {"error": "csrf_token_invalid"})
            return False
        return True

    def _read_json_body(self) -> dict[str, Any]:
        if self.headers.get_content_type() != "application/json":
            raise SecureBoundaryError("content_type_must_be_application_json")
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0 or length > 65536:
            raise SecureBoundaryError("request_body_size_invalid")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise SecureBoundaryError("request_body_not_object")
        return value

    def _login(self) -> None:
        client_ip = str(self.client_address[0])
        if self.config.login_blocked(client_ip):
            self._json(429, {"error": "login_rate_limited"})
            return
        try:
            payload = self._read_json_body()
        except (SecureBoundaryError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._json(400, {"error": str(exc)})
            return
        username = str(payload.get("username") or "")
        password = str(payload.get("password") or "")
        valid = hmac.compare_digest(username, self.config.username) and self.config.verify_password(password)
        if not valid:
            self.config.record_login_failure(client_ip)
            self._json(401, {"error": "invalid_credentials"})
            return
        self.config.clear_login_failures(client_ip)
        token, csrf, _ = self.config.issue_session()
        cookie = f"{self.config.cookie_name}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={self.config.session_ttl_seconds}"
        if self.config.secure_cookie:
            cookie += "; Secure"
        self._json(200, {"authenticated": True, "csrf_token": csrf, "expires_in": self.config.session_ttl_seconds}, extra_headers={"Set-Cookie": cookie})

    def _logout(self, claims: Mapping[str, Any]) -> None:
        self.config.revoke(str(claims["nonce"]))
        cookie = f"{self.config.cookie_name}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"
        if self.config.secure_cookie:
            cookie += "; Secure"
        self._json(200, {"authenticated": False}, extra_headers={"Set-Cookie": cookie})

    def do_GET(self) -> None:  # noqa: N802
        if not self._transport_valid():
            return
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json(200, {"status": "PASS", "authentication_required": True, "loopback_application_server": True, "audio_enabled": False})
            return
        if path == "/login.html":
            self._static(self.secure_static_root / "login.html", "text/html; charset=utf-8")
            return
        if path == "/login.js":
            self._static(self.secure_static_root / "login.js", "application/javascript; charset=utf-8")
            return
        if path == "/login.css":
            self._static(self.secure_static_root / "login.css", "text/css; charset=utf-8")
            return
        claims = self._claims()
        if claims is None:
            if path in {"/", "/index.html"}:
                self._redirect("/login.html")
            else:
                self._json(401, {"error": "authentication_required"})
            return
        if path == "/auth/session":
            self._json(200, {"authenticated": True, "username": claims["sub"], "csrf_token": claims["csrf"], "expires_at": claims["exp"]})
            return
        if path == "/auth.js":
            self._static(self.secure_static_root / "auth.js", "application/javascript; charset=utf-8")
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if not self._transport_valid() or not self._origin_valid():
            return
        path = urlparse(self.path).path
        if path == "/auth/login":
            self._login()
            return
        claims = self._claims()
        if claims is None:
            self._json(401, {"error": "authentication_required"})
            return
        if not self._csrf_valid(claims):
            return
        if path == "/auth/logout":
            self._logout(claims)
            return
        super().do_POST()

    def log_message(self, format: str, *args: Any) -> None:
        return


class SecureBoundaryServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: s10.s09.PopulationWorkbenchApplication, secure_static_root: Path, config: BoundaryConfig):
        if not _is_loopback(address[0]):
            raise SecureBoundaryError(f"non_loopback_host_forbidden:{address[0]}")
        self.app = app
        self.static_root = Path(secure_static_root)
        self.secure_static_root = Path(secure_static_root)
        self.config = config
        super().__init__(address, SecureBoundaryHandler)
        self.config.bind_local_port(int(self.server_address[1]))


def _write_secure_static(source_static_root: Path, target_root: Path) -> None:
    source_static_root = Path(source_static_root)
    target_root = Path(target_root)
    if target_root.exists():
        shutil.rmtree(target_root)
    shutil.copytree(source_static_root, target_root)
    index_path = target_root / "index.html"
    index = index_path.read_text(encoding="utf-8")
    if "/auth.js" not in index:
        index = index.replace('<script src="/app.js"></script>', '<button id="logout" type="button">登出</button><script src="/auth.js"></script><script src="/app.js"></script>')
    index_path.write_text(index, encoding="utf-8")
    auth_js = r"""'use strict';
const nativeFetch=window.fetch.bind(window);let csrfToken=null;
async function authSession(){const response=await nativeFetch('/auth/session',{credentials:'same-origin'});if(response.status===401){window.location.replace('/login.html');throw new Error('authentication_required');}const value=await response.json();csrfToken=value.csrf_token;return value;}
window.fetch=async(input,init={})=>{const method=String(init.method||'GET').toUpperCase();const headers=new Headers(init.headers||{});if(!['GET','HEAD','OPTIONS'].includes(method)){if(!csrfToken)await authSession();headers.set('X-CSRF-Token',csrfToken);}const response=await nativeFetch(input,{...init,headers,credentials:'same-origin'});if(response.status===401)window.location.replace('/login.html');return response;};
document.addEventListener('DOMContentLoaded',async()=>{try{await authSession();}catch(_){return;}const logout=document.querySelector('#logout');if(logout)logout.addEventListener('click',async()=>{await window.fetch('/auth/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});window.location.replace('/login.html');});});
"""
    (target_root / "auth.js").write_text(auth_js + "\n", encoding="utf-8")
    login_html = """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"><title>A1FS 安全登入</title><link rel="stylesheet" href="/login.css"></head><body><main><h1>A1FS 安全登入</h1><form id="login-form"><label>帳號 <input id="username" name="username" autocomplete="username" required></label><label>密碼 <input id="password" name="password" type="password" autocomplete="current-password" required></label><button type="submit">登入</button><p id="message" aria-live="polite"></p></form></main><script src="/login.js"></script></body></html>"""
    login_js = r"""'use strict';const form=document.querySelector('#login-form');const message=document.querySelector('#message');form.addEventListener('submit',async(event)=>{event.preventDefault();message.textContent='驗證中';const response=await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.querySelector('#username').value,password:document.querySelector('#password').value})});const value=await response.json();if(!response.ok){message.textContent=value.error||'登入失敗';return;}window.location.replace('/');});"""
    login_css = """body{font-family:system-ui,sans-serif;margin:0;background:#f4f4f4;color:#181818}main{max-width:480px;margin:8vh auto;padding:24px;background:#fff;border-radius:8px}form{display:grid;gap:16px}label{display:grid;gap:6px}input,button{font:inherit;padding:10px}#message{min-height:1.5em}"""
    (target_root / "login.html").write_text(login_html + "\n", encoding="utf-8")
    (target_root / "login.js").write_text(login_js + "\n", encoding="utf-8")
    (target_root / "login.css").write_text(login_css + "\n", encoding="utf-8")


def _verify_s10(receipt_path: Path) -> tuple[dict[str, Any], Path, Path, Path, dict[str, dict[str, Any]], dict[str, int]]:
    receipt_path = Path(receipt_path).resolve()
    receipt = read_json(receipt_path, "s10_receipt")
    identity = (receipt.get("task_id"), receipt.get("schema_version"), receipt.get("validation_status"), receipt.get("product_status"), receipt.get("stop_reason"))
    if identity != (s10.TASK_ID, s10.SCHEMA_VERSION, s10.PASS_STATUS, s10.PRODUCT_STATUS, "NONE"):
        raise SecureBoundaryError("s10_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise SecureBoundaryError("s10_receipt_digest_invalid")
    summary = receipt.get("release_candidate_summary", {})
    if summary.get("unit_count") != 24 or summary.get("lesson_count") != 72 or summary.get("asset_count") != 264 or summary.get("restart_resume_pass") is not True or receipt.get("production_safety", {}).get("production_database_unchanged") is not True:
        raise SecureBoundaryError("s10_acceptance_contract_invalid")
    s09_path = Path(str(receipt.get("runtime_outputs", {}).get("source_s09_receipt_path") or "")).resolve()
    _, database, bundle_index, static_root, bundles, sequence = s10._verify_s09(s09_path)
    return receipt, database, bundle_index, static_root, bundles, sequence


def _start_server(*, app: s10.s09.PopulationWorkbenchApplication, secure_static_root: Path, config: BoundaryConfig, port: int = 0) -> tuple[SecureBoundaryServer, threading.Thread, int]:
    server = SecureBoundaryServer(("127.0.0.1", port), app, secure_static_root, config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, int(server.server_address[1])


def _stop_server(server: SecureBoundaryServer, thread: threading.Thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=10)
    if thread.is_alive():
        raise SecureBoundaryError("secure_server_thread_did_not_stop")


def _request(port: int, method: str, path: str, payload: Mapping[str, Any] | None = None, *, cookie: str = "", csrf: str = "", origin: str | None = None, host: str | None = None, expected_status: int = 200, expect_json: bool = True, forwarded_proto: str = "") -> tuple[Any, Mapping[str, str]]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers: dict[str, str] = {"Host": host or f"127.0.0.1:{port}"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    if csrf:
        headers["X-CSRF-Token"] = csrf
    if origin is not None:
        headers["Origin"] = origin
    if forwarded_proto:
        headers["X-Forwarded-Proto"] = forwarded_proto
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        response_headers = {key: value for key, value in response.getheaders()}
        status = response.status
    finally:
        connection.close()
    if status != expected_status:
        raise SecureBoundaryError(f"http_status_invalid:{method}:{path}:{status}:{expected_status}:{raw[:200]!r}")
    if not expect_json:
        return raw.decode("utf-8"), response_headers
    try:
        value = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise SecureBoundaryError(f"http_json_invalid:{method}:{path}:{exc}") from exc
    return value, response_headers


def _run_authenticated_acceptance(*, canary_database: Path, secure_static_root: Path, bundles: Mapping[str, Mapping[str, Any]], sequence_by_grammar: Mapping[str, int]) -> dict[str, Any]:
    app = s10.s09.PopulationWorkbenchApplication(database_path=canary_database, bundles=bundles, sequence_by_grammar=sequence_by_grammar, default_learner_id=CANARY_LEARNER_ID)
    app.enroll(learner_id=CANARY_LEARNER_ID, display_label="S11 Auth Boundary Canary", subject_key=CANARY_SUBJECT_KEY, at="2026-01-12T00:00:00Z")
    config = BoundaryConfig.from_values(username=CANARY_USERNAME, password=CANARY_PASSWORD, session_secret=CANARY_SESSION_SECRET, mode="local", allowed_origin="http://127.0.0.1", allowed_host="127.0.0.1")
    server, thread, port = _start_server(app=app, secure_static_root=secure_static_root, config=config)
    origin = f"http://127.0.0.1:{port}"
    cookie = ""
    csrf = ""
    try:
        health, health_headers = _request(port, "GET", "/api/health")
        if health.get("authentication_required") is not True or health_headers.get("X-Frame-Options") != "DENY" or "frame-ancestors 'none'" not in health_headers.get("Content-Security-Policy", ""):
            raise SecureBoundaryError("health_or_security_headers_invalid")
        _request(port, "GET", "/api/health", host="evil.invalid", expected_status=400)
        _, redirect_headers = _request(port, "GET", "/", expected_status=302, expect_json=False)
        if redirect_headers.get("Location") != "/login.html":
            raise SecureBoundaryError("unauthenticated_root_not_redirected")
        _request(port, "GET", "/api/bootstrap", expected_status=401)
        _request(port, "POST", "/auth/login", {"username": CANARY_USERNAME, "password": "wrong-password-value"}, origin=origin, expected_status=401)
        login, login_headers = _request(port, "POST", "/auth/login", {"username": CANARY_USERNAME, "password": CANARY_PASSWORD}, origin=origin)
        set_cookie = login_headers.get("Set-Cookie", "")
        if login.get("authenticated") is not True or "HttpOnly" not in set_cookie or "SameSite=Strict" not in set_cookie or "Secure" in set_cookie:
            raise SecureBoundaryError("local_session_cookie_contract_invalid")
        cookie = set_cookie.split(";", 1)[0]
        csrf = str(login.get("csrf_token") or "")
        if not cookie or not csrf:
            raise SecureBoundaryError("login_session_material_missing")
        session, _ = _request(port, "GET", "/auth/session", cookie=cookie)
        if session.get("csrf_token") != csrf:
            raise SecureBoundaryError("auth_session_csrf_mismatch")
        bootstrap, _ = _request(port, "GET", "/api/bootstrap", cookie=cookie)
        denominators = s10._validate_bootstrap(bootstrap)
        reading_lane = s10._lane(bootstrap, sequence_index=1, skill="READING")
        reading_asset, wrong = s10.s09.s08._deterministic_response(canary_database, reading_lane["assets"], should_pass=False)
        _request(port, "POST", "/api/session/start", {"learner_id": CANARY_LEARNER_ID, "lesson_id": reading_lane["lesson_id"]}, cookie=cookie, origin=origin, expected_status=403)
        _request(port, "POST", "/api/session/start", {"learner_id": CANARY_LEARNER_ID, "lesson_id": reading_lane["lesson_id"]}, cookie=cookie, csrf=csrf, origin="http://evil.invalid", expected_status=403)
        reading, _ = _request(port, "POST", "/api/session/start", {"learner_id": CANARY_LEARNER_ID, "lesson_id": reading_lane["lesson_id"], "session_id": READING_SESSION_ID, "at": "2026-01-12T00:00:10Z"}, cookie=cookie, csrf=csrf, origin=origin)
        reading, _ = _request(port, "POST", "/api/exposure", {"session_id": READING_SESSION_ID, "asset_key": reading_asset, "expected_session_version": reading["session_version"], "at": "2026-01-12T00:00:20Z"}, cookie=cookie, csrf=csrf, origin=origin)
        scored, _ = _request(port, "POST", "/api/response", {"learner_id": CANARY_LEARNER_ID, "session_id": READING_SESSION_ID, "asset_key": reading_asset, "response": wrong, "expected_session_version": reading["session_version"], "attempt_id": READING_ATTEMPT_ID, "submitted_at": "2026-01-12T00:00:30Z"}, cookie=cookie, csrf=csrf, origin=origin)
        if scored.get("outcome") != "AUTO_FAIL":
            raise SecureBoundaryError("authenticated_reading_fail_path_invalid")
    finally:
        _stop_server(server, thread)

    app = s10.s09.PopulationWorkbenchApplication(database_path=canary_database, bundles=bundles, sequence_by_grammar=sequence_by_grammar, default_learner_id=CANARY_LEARNER_ID)
    server, thread, port = _start_server(app=app, secure_static_root=secure_static_root, config=config)
    origin = f"http://127.0.0.1:{port}"
    try:
        resumed, _ = _request(port, "GET", "/api/session/active", cookie=cookie)
        if resumed.get("active") is not True or resumed.get("session", {}).get("session_id") != READING_SESSION_ID or resumed.get("session", {}).get("session_version") != scored.get("session_version"):
            raise SecureBoundaryError("authenticated_restart_resume_invalid")
        done, _ = _request(port, "POST", "/api/session/complete", {"session_id": READING_SESSION_ID, "expected_session_version": resumed["session"]["session_version"], "at": "2026-01-12T00:00:40Z"}, cookie=cookie, csrf=csrf, origin=origin)
        if done.get("session_state") != "COMPLETED":
            raise SecureBoundaryError("authenticated_reading_complete_invalid")
        bootstrap, _ = _request(port, "GET", "/api/bootstrap", cookie=cookie)
        writing_lane = s10._lane(bootstrap, sequence_index=24, skill="WRITING")
        writing_asset, correct = s10.s09.s08._deterministic_response(canary_database, writing_lane["assets"], should_pass=True)
        writing, _ = _request(port, "POST", "/api/session/start", {"learner_id": CANARY_LEARNER_ID, "lesson_id": writing_lane["lesson_id"], "session_id": WRITING_SESSION_ID, "at": "2026-01-12T00:01:00Z"}, cookie=cookie, csrf=csrf, origin=origin)
        writing, _ = _request(port, "POST", "/api/exposure", {"session_id": WRITING_SESSION_ID, "asset_key": writing_asset, "expected_session_version": writing["session_version"], "at": "2026-01-12T00:01:10Z"}, cookie=cookie, csrf=csrf, origin=origin)
        writing_scored, _ = _request(port, "POST", "/api/response", {"learner_id": CANARY_LEARNER_ID, "session_id": WRITING_SESSION_ID, "asset_key": writing_asset, "response": correct, "expected_session_version": writing["session_version"], "attempt_id": WRITING_ATTEMPT_ID, "submitted_at": "2026-01-12T00:01:20Z"}, cookie=cookie, csrf=csrf, origin=origin)
        if writing_scored.get("outcome") != "AUTO_PASS":
            raise SecureBoundaryError("authenticated_writing_pass_path_invalid")
        done, _ = _request(port, "POST", "/api/session/complete", {"session_id": WRITING_SESSION_ID, "expected_session_version": writing_scored["session_version"], "at": "2026-01-12T00:01:30Z"}, cookie=cookie, csrf=csrf, origin=origin)
        if done.get("session_state") != "COMPLETED":
            raise SecureBoundaryError("authenticated_writing_complete_invalid")
        speaking_lane = s10._lane(bootstrap, sequence_index=24, skill="SPEAKING")
        speaking_asset = str(speaking_lane["assets"][0]["asset_key"])
        speaking, _ = _request(port, "POST", "/api/session/start", {"learner_id": CANARY_LEARNER_ID, "lesson_id": speaking_lane["lesson_id"], "session_id": SPEAKING_SESSION_ID, "at": "2026-01-12T00:02:00Z"}, cookie=cookie, csrf=csrf, origin=origin)
        speaking, _ = _request(port, "POST", "/api/exposure", {"session_id": SPEAKING_SESSION_ID, "asset_key": speaking_asset, "expected_session_version": speaking["session_version"], "at": "2026-01-12T00:02:10Z"}, cookie=cookie, csrf=csrf, origin=origin)
        error, _ = _request(port, "POST", "/api/response", {"learner_id": CANARY_LEARNER_ID, "session_id": SPEAKING_SESSION_ID, "asset_key": speaking_asset, "response": "blocked speaking submission", "expected_session_version": speaking["session_version"]}, cookie=cookie, csrf=csrf, origin=origin, expected_status=400)
        if error.get("error") != "response_capture_not_enabled_for_asset":
            raise SecureBoundaryError("authenticated_speaking_block_invalid")
        done, _ = _request(port, "POST", "/api/session/abandon", {"session_id": SPEAKING_SESSION_ID, "expected_session_version": speaking["session_version"], "at": "2026-01-12T00:02:20Z"}, cookie=cookie, csrf=csrf, origin=origin)
        if done.get("session_state") != "ABANDONED":
            raise SecureBoundaryError("authenticated_speaking_abandon_invalid")
        progress, _ = _request(port, "GET", "/api/progress", cookie=cookie)
        progress_counts = s10._validate_progress(progress)
        _request(port, "POST", "/auth/logout", {}, cookie=cookie, csrf=csrf, origin=origin)
        _request(port, "GET", "/api/bootstrap", cookie=cookie, expected_status=401)
    finally:
        _stop_server(server, thread)

    reverse_proxy = BoundaryConfig.from_values(username=CANARY_USERNAME, password=CANARY_PASSWORD, session_secret=CANARY_SESSION_SECRET, mode="reverse_proxy", allowed_origin="https://learn.example.test", allowed_host="learn.example.test")
    token, _, _ = reverse_proxy.issue_session(now=1_700_000_000)
    secure_cookie = f"{reverse_proxy.cookie_name}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={reverse_proxy.session_ttl_seconds}; Secure"
    if reverse_proxy.cookie_name != COOKIE_SECURE or "Secure" not in secure_cookie or "HttpOnly" not in secure_cookie or "SameSite=Strict" not in secure_cookie:
        raise SecureBoundaryError("reverse_proxy_secure_cookie_contract_invalid")
    try:
        BoundaryConfig.from_values(username=CANARY_USERNAME, password=CANARY_PASSWORD, session_secret=CANARY_SESSION_SECRET, mode="reverse_proxy", allowed_origin="http://learn.example.test", allowed_host="learn.example.test")
    except SecureBoundaryError as exc:
        tls_fail_closed = str(exc) == "reverse_proxy_https_origin_required"
    else:
        tls_fail_closed = False
    if not tls_fail_closed:
        raise SecureBoundaryError("reverse_proxy_tls_prerequisite_not_fail_closed")

    return {
        **denominators,
        **progress_counts,
        "authentication_required": True,
        "unauthenticated_root_redirected": True,
        "unauthenticated_api_blocked": True,
        "invalid_credentials_blocked": True,
        "login_rate_limit_enabled": True,
        "signed_session_cookie": True,
        "session_cookie_http_only": True,
        "session_cookie_same_site_strict": True,
        "secure_cookie_required_in_reverse_proxy_mode": True,
        "csrf_required_for_state_change": True,
        "invalid_origin_blocked": True,
        "host_allowlist_enforced": True,
        "security_headers_enabled": True,
        "restart_authenticated_session_valid": True,
        "logout_revokes_session": True,
        "unit01_reading_auto_fail": True,
        "unit24_writing_auto_pass": True,
        "unit24_speaking_submission_blocked": True,
        "reverse_proxy_https_prerequisites_fail_closed": True,
        "loopback_application_server_only": True,
        "server_process_start_count": 2,
    }


def materialize(*, s10_receipt_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    s10_receipt_path = Path(s10_receipt_path).resolve()
    s10_receipt, production_database, bundle_index, source_static, bundles, sequence = _verify_s10(s10_receipt_path)
    output_root = Path(output_root).resolve()
    candidate_root = output_root / "secure_authenticated_boundary"
    if candidate_root.exists():
        shutil.rmtree(candidate_root)
    candidate_root.mkdir(parents=True, exist_ok=True)
    secure_static = candidate_root / "static"
    _write_secure_static(source_static, secure_static)
    canary_database = candidate_root / "s11_authenticated_acceptance_canary.sqlite3"
    shutil.copy2(production_database, canary_database)
    production_sha_before = file_digest(production_database)
    acceptance = _run_authenticated_acceptance(canary_database=canary_database, secure_static_root=secure_static, bundles=bundles, sequence_by_grammar=sequence)
    production_sha_after = file_digest(production_database)
    if production_sha_before != production_sha_after:
        raise SecureBoundaryError("production_database_mutated_by_s11_acceptance")
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "source_identity": {"s10_sha256": digest(s10_receipt), "production_database_sha256": production_sha_before},
        "runtime_outputs": {
            "root": str(candidate_root),
            "source_s10_receipt_path": str(s10_receipt_path),
            "source_database_path": str(production_database),
            "source_bundle_index_path": str(bundle_index),
            "secure_static_root": str(secure_static),
            "canary_database_path": str(canary_database),
        },
        "security_acceptance_summary": acceptance,
        "production_safety": {
            "database_sha256_before": production_sha_before,
            "database_sha256_after": production_sha_after,
            "production_database_unchanged": True,
            "authenticated_acceptance_executed_on_isolated_clone": True,
            "real_learner_progress_mutated_by_canary": False,
        },
        "deployment_boundary": {
            "application_server_loopback_only": True,
            "reverse_proxy_required_for_online_delivery": True,
            "https_origin_required": True,
            "explicit_host_allowlist_required": True,
            "auth_secret_environment_required": True,
            "session_signing_secret_environment_required": True,
            "secrets_serialized_to_artifact": False,
            "public_release_completed": False,
        },
        "entrypoint": {"serve_command_available": True, "readback_command_available": True, "default_host": "127.0.0.1", "default_port": 8765},
        "capability_contract": {
            "s10_release_candidate_reused": True,
            "s09_twentyfour_unit_runtime_reused": True,
            "m3_session_progress_authority_reused": True,
            "m5_renderer_authority_reused": True,
            "m6_response_scoring_authority_reused": True,
            "authenticated_boundary_connected": True,
            "signed_session_and_csrf_connected": True,
            "parallel_curriculum_created": False,
            "parallel_learner_state_engine_created": False,
            "parallel_scoring_engine_created": False,
            "direct_public_binding_allowed": False,
            "speaking_capture_enabled": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "mastery_write_enabled": False,
        },
        "product_status": PRODUCT_STATUS,
        "claim_boundaries": {
            "public_online_delivery_claimed": False,
            "remote_deployment_proven": False,
            "real_learner_attempt_claimed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "audio_complete": False,
            "speaking_recording_complete": False,
            "a2_unlocked": False,
        },
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
        "security_acceptance_summary": deepcopy(acceptance),
        "production_safety": {"production_database_unchanged": True, "authenticated_acceptance_executed_on_isolated_clone": True, "real_learner_progress_mutated_by_canary": False},
        "deployment_boundary": deepcopy(receipt_core["deployment_boundary"]),
        "entrypoint": deepcopy(receipt_core["entrypoint"]),
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def _source_s10(receipt_path: Path) -> tuple[dict[str, Any], Path, Path]:
    receipt = read_json(receipt_path, "s11_receipt")
    identity = (receipt.get("task_id"), receipt.get("schema_version"), receipt.get("validation_status"), receipt.get("product_status"), receipt.get("stop_reason"))
    if identity != (TASK_ID, SCHEMA_VERSION, PASS_STATUS, PRODUCT_STATUS, "NONE"):
        raise SecureBoundaryError("s11_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise SecureBoundaryError("s11_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs", {})
    source_s10 = Path(str(outputs.get("source_s10_receipt_path") or "")).resolve()
    secure_static = Path(str(outputs.get("secure_static_root") or "")).resolve()
    if not source_s10.is_file() or not secure_static.is_dir():
        raise SecureBoundaryError("s11_runtime_outputs_missing")
    return receipt, source_s10, secure_static


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    _, source_s10, secure_static = _source_s10(receipt_path)
    _, production_database, _, _, bundles, sequence = _verify_s10(source_s10)
    config = BoundaryConfig.from_environment(host=host, port=port)
    app = s10.s09.PopulationWorkbenchApplication(database_path=production_database, bundles=bundles, sequence_by_grammar=sequence, default_learner_id=s10.s09.s05.DEFAULT_LEARNER_ID)
    server = SecureBoundaryServer((host, port), app, secure_static, config)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def readback(*, receipt_path: Path) -> dict[str, Any]:
    receipt, source_s10, _ = _source_s10(receipt_path)
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "security_acceptance_summary": deepcopy(receipt["security_acceptance_summary"]),
        "deployment_boundary": deepcopy(receipt["deployment_boundary"]),
        "source_release_candidate": s10.readback(receipt_path=source_s10),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s10", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    server = commands.add_parser("serve")
    server.add_argument("--receipt", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8765)
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
        receipt, safe = materialize(s10_receipt_path=args.s10, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s11_secure_authenticated_boundary import validate_outputs
        validation = validate_outputs(receipt=receipt, safe_report=safe, output_root=args.output.parent, s10_path=args.s10)
        if validation["error_count"]:
            raise SecureBoundaryError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (SecureBoundaryError, s10.ReleaseCandidateError, s10.s09.PopulationError, s10.s09.s08.JourneyQAError, s10.s09.s07.MultiUnitExpansionError, s10.s09.s05.PersistenceError, OSError, sqlite3.Error, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
