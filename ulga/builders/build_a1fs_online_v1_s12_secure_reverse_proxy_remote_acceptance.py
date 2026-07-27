#!/usr/bin/env python3
"""Build and accept a secure reverse-proxy deployment bundle for A1FS Online V1.

S12 reuses the authoritative S11 authenticated boundary and S09 learner runtime.
It renders an operational Caddy reverse-proxy bundle, runs a remote-shaped HTTPS
edge acceptance over loopback, proves signed-session continuity across upstream
and proxy restarts, and validates rollback/readback contracts. It does not deploy
to a real domain, serialize secrets, mutate production progress, enable audio,
write mastery, unlock A2, or claim a public release.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import shutil
import sqlite3
import sys
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s11_secure_authenticated_boundary as s11  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Renders a reverse-proxy deployment bundle and executes remote-shaped HTTPS acceptance against the existing S11/S09 runtime on an isolated database clone; it creates no curriculum, learner content, answers, audio, mastery, A2 unlock, real external deployment, or public-release claim."

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S12_SecureReverseProxyDeploymentAndRemoteAcceptance_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s12.secure_reverse_proxy_remote_acceptance.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S12_SECURE_REVERSE_PROXY_REMOTE_ACCEPTANCE_READY"
PRODUCT_STATUS = "SECURE_REVERSE_PROXY_DEPLOYMENT_BUNDLE_REMOTE_SHAPED_ACCEPTED_NOT_LIVE"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S13_OperatorSelectedLiveDeploymentAndExternalRemoteAcceptance_NoAudio"

CANARY_PUBLIC_HOST = "learn.example.test"
CANARY_PUBLIC_ORIGIN = f"https://{CANARY_PUBLIC_HOST}"
CANARY_USERNAME = "s12-canary"
CANARY_PASSWORD = "S12-Canary-Password-Only-For-Isolated-Acceptance-2026!"
CANARY_SESSION_SECRET = "S12-Canary-Session-Signing-Secret-Only-For-Isolated-Acceptance-2026!"
CANARY_LEARNER_ID = "A1FS_ONLINE_V1_S12_REMOTE_CANARY"
CANARY_SUBJECT_KEY = "A1FS_ONLINE_V1_S12_REMOTE_SLOT"
READING_SESSION_ID = "A1FS_ONLINE_V1_S12_SESSION:UNIT01:READING"
READING_ATTEMPT_ID = "A1FS_ONLINE_V1_S12_ATTEMPT:UNIT01:READING:FAIL"
WRITING_SESSION_ID = "A1FS_ONLINE_V1_S12_SESSION:UNIT24:WRITING"
WRITING_ATTEMPT_ID = "A1FS_ONLINE_V1_S12_ATTEMPT:UNIT24:WRITING:PASS"
SPEAKING_SESSION_ID = "A1FS_ONLINE_V1_S12_SESSION:UNIT24:SPEAKING"

FORBIDDEN_SAFE_KEYS = {
    "accepted_texts", "accepted_sequence", "answer", "answer_contract", "answer_key",
    "asset_key", "auth_password", "csrf", "database_path", "display_label", "learner_id",
    "learner_payload", "password", "private_scoring_contract", "private_subject_digest",
    "prompt", "prompt_text", "response", "rubric", "scoring_contract", "session_id",
    "session_secret", "subject_key", "token",
}


class ReverseProxyAcceptanceError(ValueError):
    """Fail-closed S12 deployment or remote-shaped acceptance error."""


def digest(value: Any) -> str:
    return s11.digest(value)


def file_digest(path: Path) -> str:
    return s11.file_digest(path)


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReverseProxyAcceptanceError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ReverseProxyAcceptanceError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    s11.write_json(Path(path), value, private=private)


def safe_scan(value: Any) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                    raise ReverseProxyAcceptanceError(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def _tree_digest(root: Path) -> str:
    root = Path(root).resolve()
    hasher = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        hasher.update(path.relative_to(root).as_posix().encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def _verify_s11(
    receipt_path: Path,
) -> tuple[
    dict[str, Any], Path, Path, Path, dict[str, dict[str, Any]], dict[str, int]
]:
    receipt_path = Path(receipt_path).resolve()
    receipt = read_json(receipt_path, "s11_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    expected = (s11.TASK_ID, s11.SCHEMA_VERSION, s11.PASS_STATUS, s11.PRODUCT_STATUS, "NONE")
    if identity != expected:
        raise ReverseProxyAcceptanceError("s11_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise ReverseProxyAcceptanceError("s11_receipt_digest_invalid")
    summary = receipt.get("security_acceptance_summary", {})
    if (
        summary.get("unit_count") != 24
        or summary.get("lesson_count") != 72
        or summary.get("asset_count") != 264
        or summary.get("authentication_required") is not True
        or summary.get("restart_authenticated_session_valid") is not True
        or receipt.get("production_safety", {}).get("production_database_unchanged") is not True
    ):
        raise ReverseProxyAcceptanceError("s11_security_acceptance_contract_invalid")
    boundary = receipt.get("deployment_boundary", {})
    if (
        boundary.get("application_server_loopback_only") is not True
        or boundary.get("reverse_proxy_required_for_online_delivery") is not True
        or boundary.get("https_origin_required") is not True
        or boundary.get("public_release_completed") is not False
    ):
        raise ReverseProxyAcceptanceError("s11_deployment_boundary_invalid")
    source_s10 = Path(str(receipt.get("runtime_outputs", {}).get("source_s10_receipt_path") or "")).resolve()
    secure_static = Path(str(receipt.get("runtime_outputs", {}).get("secure_static_root") or "")).resolve()
    if not source_s10.is_file() or not secure_static.is_dir():
        raise ReverseProxyAcceptanceError("s11_runtime_outputs_missing")
    _, production_database, bundle_index, _, bundles, sequence = s11._verify_s10(source_s10)
    return receipt, production_database, bundle_index, secure_static, bundles, sequence


def _write_deployment_bundle(target_root: Path) -> dict[str, Any]:
    target_root = Path(target_root).resolve()
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True, exist_ok=True)

    caddyfile = r"""{$A1FS_PUBLIC_HOST} {
    encode zstd gzip

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "no-referrer"
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
    }

    reverse_proxy 127.0.0.1:8765 {
        header_up Host {$A1FS_PUBLIC_HOST}
        header_up X-Forwarded-Host {$A1FS_PUBLIC_HOST}
        header_up X-Forwarded-Proto https
        header_up X-Real-IP {remote_host}
    }
}
"""
    (target_root / "Caddyfile").write_text(caddyfile, encoding="utf-8")

    contract = {
        "schema_version": "a1fs.online.v1.s12.deployment_contract.v1",
        "application_upstream": "127.0.0.1:8765",
        "reverse_proxy": "CADDY",
        "tls_termination": "AUTOMATIC_HTTPS_AT_EDGE",
        "required_environment_variables": [
            "A1FS_PUBLIC_HOST",
            "A1FS_S11_MODE",
            "A1FS_S11_AUTH_USERNAME",
            "A1FS_S11_AUTH_PASSWORD",
            "A1FS_S11_SESSION_SECRET",
            "A1FS_S11_ALLOWED_ORIGIN",
            "A1FS_S11_ALLOWED_HOST",
        ],
        "required_runtime_values": {
            "A1FS_S11_MODE": "reverse_proxy",
            "A1FS_S11_ALLOWED_ORIGIN": "https://${A1FS_PUBLIC_HOST}",
            "A1FS_S11_ALLOWED_HOST": "${A1FS_PUBLIC_HOST}",
        },
        "origin_binding": {
            "host": "127.0.0.1",
            "port": 8765,
            "non_loopback_binding_allowed": False,
        },
        "forwarded_header_contract": {
            "Host": "${A1FS_PUBLIC_HOST}",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "${A1FS_PUBLIC_HOST}",
        },
        "health_endpoint": "/api/health",
        "secret_values_embedded": False,
        "public_release_completed": False,
    }
    write_json(target_root / "deployment_contract.json", contract)

    rollback = {
        "schema_version": "a1fs.online.v1.s12.rollback_contract.v1",
        "trigger_conditions": [
            "AUTHENTICATION_GATE_FAILURE",
            "CSRF_ORIGIN_HOST_GATE_FAILURE",
            "HEALTH_ENDPOINT_FAILURE",
            "PRODUCTION_DATABASE_DIGEST_DRIFT",
        ],
        "actions": [
            "REMOVE_PUBLIC_PROXY_ROUTE",
            "KEEP_APPLICATION_BOUND_TO_127_0_0_1",
            "PRESERVE_PRODUCTION_DATABASE",
            "RESTORE_LAST_ACCEPTED_PROXY_CONFIGURATION",
        ],
        "database_rollback_required": False,
        "automatic_public_reenable_allowed": False,
    }
    write_json(target_root / "rollback_contract.json", rollback)

    return {
        "bundle_root": str(target_root),
        "caddyfile_path": str(target_root / "Caddyfile"),
        "deployment_contract_path": str(target_root / "deployment_contract.json"),
        "rollback_contract_path": str(target_root / "rollback_contract.json"),
        "bundle_sha256": _tree_digest(target_root),
    }


class EdgeProxyHandler(BaseHTTPRequestHandler):
    server_version = "A1FSSimulatedSecureEdge/1"

    @property
    def upstream_port(self) -> int:
        return int(self.server.upstream_port)  # type: ignore[attr-defined]

    @property
    def public_host(self) -> str:
        return str(self.server.public_host)  # type: ignore[attr-defined]

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(length) if length else None
        headers: dict[str, str] = {
            "Host": self.public_host,
            "X-Forwarded-Host": self.public_host,
            "X-Forwarded-Proto": "https",
            "X-Real-IP": str(self.client_address[0]),
        }
        for key in ("Content-Type", "Cookie", "Origin", "X-CSRF-Token"):
            value = self.headers.get(key)
            if value:
                headers[key] = value
        connection = http.client.HTTPConnection("127.0.0.1", self.upstream_port, timeout=10)
        try:
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            response_headers = response.getheaders()
            status = response.status
        finally:
            connection.close()
        self.send_response(status)
        excluded = {"connection", "transfer-encoding", "content-length", "server", "date"}
        for key, value in response_headers:
            if key.casefold() not in excluded:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        self._proxy()

    def do_POST(self) -> None:  # noqa: N802
        self._proxy()

    def log_message(self, format: str, *args: Any) -> None:
        return


class EdgeProxyServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *, upstream_port: int, public_host: str):
        self.upstream_port = int(upstream_port)
        self.public_host = str(public_host)
        super().__init__(("127.0.0.1", 0), EdgeProxyHandler)


def _start_edge(*, upstream_port: int) -> tuple[EdgeProxyServer, threading.Thread, int]:
    server = EdgeProxyServer(upstream_port=upstream_port, public_host=CANARY_PUBLIC_HOST)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, int(server.server_address[1])


def _stop_server(server: ThreadingHTTPServer, thread: threading.Thread, code: str) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=10)
    if thread.is_alive():
        raise ReverseProxyAcceptanceError(code)


def _edge_request(
    port: int,
    method: str,
    path: str,
    payload: Mapping[str, Any] | None = None,
    *,
    cookie: str = "",
    csrf: str = "",
    origin: str | None = None,
    expected_status: int = 200,
    expect_json: bool = True,
) -> tuple[Any, Mapping[str, str]]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers: dict[str, str] = {"Host": CANARY_PUBLIC_HOST}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    if csrf:
        headers["X-CSRF-Token"] = csrf
    if origin is not None:
        headers["Origin"] = origin
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        response_headers = {key: value for key, value in response.getheaders()}
        status = response.status
    finally:
        connection.close()
    if status != expected_status:
        raise ReverseProxyAcceptanceError(
            f"edge_http_status_invalid:{method}:{path}:{status}:{expected_status}:{raw[:200]!r}"
        )
    if not expect_json:
        return raw.decode("utf-8"), response_headers
    try:
        value = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ReverseProxyAcceptanceError(f"edge_http_json_invalid:{method}:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ReverseProxyAcceptanceError(f"edge_http_json_not_object:{method}:{path}")
    return value, response_headers


def _start_origin(
    *,
    canary_database: Path,
    secure_static_root: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence_by_grammar: Mapping[str, int],
) -> tuple[s11.SecureBoundaryServer, threading.Thread, int]:
    app = s11.s10.s09.PopulationWorkbenchApplication(
        database_path=canary_database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
        default_learner_id=CANARY_LEARNER_ID,
    )
    config = s11.BoundaryConfig.from_values(
        username=CANARY_USERNAME,
        password=CANARY_PASSWORD,
        session_secret=CANARY_SESSION_SECRET,
        mode="reverse_proxy",
        allowed_origin=CANARY_PUBLIC_ORIGIN,
        allowed_host=CANARY_PUBLIC_HOST,
    )
    server, thread, port = s11._start_server(
        app=app,
        secure_static_root=secure_static_root,
        config=config,
    )
    return server, thread, port


def _run_remote_shaped_acceptance(
    *,
    canary_database: Path,
    secure_static_root: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence_by_grammar: Mapping[str, int],
) -> dict[str, Any]:
    app = s11.s10.s09.PopulationWorkbenchApplication(
        database_path=canary_database,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
        default_learner_id=CANARY_LEARNER_ID,
    )
    app.enroll(
        learner_id=CANARY_LEARNER_ID,
        display_label="S12 Reverse Proxy Canary",
        subject_key=CANARY_SUBJECT_KEY,
        at="2026-01-13T00:00:00Z",
    )

    origin_server, origin_thread, origin_port = _start_origin(
        canary_database=canary_database,
        secure_static_root=secure_static_root,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
    )
    edge_server, edge_thread, edge_port = _start_edge(upstream_port=origin_port)
    cookie = ""
    csrf = ""
    try:
        direct, _ = s11._request(
            origin_port,
            "GET",
            "/api/health",
            host=CANARY_PUBLIC_HOST,
            expected_status=400,
        )
        if direct.get("error") != "reverse_proxy_https_forwarding_required":
            raise ReverseProxyAcceptanceError("direct_origin_bypass_not_blocked")

        health, headers = _edge_request(edge_port, "GET", "/api/health")
        if (
            health.get("status") != "PASS"
            or health.get("authentication_required") is not True
            or headers.get("Strict-Transport-Security") != "max-age=31536000; includeSubDomains"
        ):
            raise ReverseProxyAcceptanceError("edge_health_or_hsts_invalid")
        _, redirect_headers = _edge_request(
            edge_port, "GET", "/", expected_status=302, expect_json=False
        )
        if redirect_headers.get("Location") != "/login.html":
            raise ReverseProxyAcceptanceError("edge_unauthenticated_redirect_invalid")
        _edge_request(edge_port, "GET", "/api/bootstrap", expected_status=401)
        login, login_headers = _edge_request(
            edge_port,
            "POST",
            "/auth/login",
            {"username": CANARY_USERNAME, "password": CANARY_PASSWORD},
            origin=CANARY_PUBLIC_ORIGIN,
        )
        set_cookie = login_headers.get("Set-Cookie", "")
        if (
            login.get("authenticated") is not True
            or not set_cookie.startswith(f"{s11.COOKIE_SECURE}=")
            or "Secure" not in set_cookie
            or "HttpOnly" not in set_cookie
            or "SameSite=Strict" not in set_cookie
        ):
            raise ReverseProxyAcceptanceError("edge_secure_cookie_contract_invalid")
        cookie = set_cookie.split(";", 1)[0]
        csrf = str(login.get("csrf_token") or "")
        if not cookie or not csrf:
            raise ReverseProxyAcceptanceError("edge_login_material_missing")
        session, _ = _edge_request(edge_port, "GET", "/auth/session", cookie=cookie)
        if session.get("csrf_token") != csrf:
            raise ReverseProxyAcceptanceError("edge_authenticated_session_invalid")
        bootstrap, _ = _edge_request(edge_port, "GET", "/api/bootstrap", cookie=cookie)
        denominators = s11.s10._validate_bootstrap(bootstrap)
        reading_lane = s11.s10._lane(bootstrap, sequence_index=1, skill="READING")
        reading_asset, wrong = s11.s10.s09.s08._deterministic_response(
            canary_database, reading_lane["assets"], should_pass=False
        )
        reading, _ = _edge_request(
            edge_port,
            "POST",
            "/api/session/start",
            {
                "learner_id": CANARY_LEARNER_ID,
                "lesson_id": reading_lane["lesson_id"],
                "session_id": READING_SESSION_ID,
                "at": "2026-01-13T00:00:10Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
        )
        reading, _ = _edge_request(
            edge_port,
            "POST",
            "/api/exposure",
            {
                "session_id": READING_SESSION_ID,
                "asset_key": reading_asset,
                "expected_session_version": reading["session_version"],
                "at": "2026-01-13T00:00:20Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
        )
        scored, _ = _edge_request(
            edge_port,
            "POST",
            "/api/response",
            {
                "learner_id": CANARY_LEARNER_ID,
                "session_id": READING_SESSION_ID,
                "asset_key": reading_asset,
                "response": wrong,
                "expected_session_version": reading["session_version"],
                "attempt_id": READING_ATTEMPT_ID,
                "submitted_at": "2026-01-13T00:00:30Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
        )
        if scored.get("outcome") != "AUTO_FAIL":
            raise ReverseProxyAcceptanceError("edge_reading_fail_path_invalid")
    finally:
        _stop_server(edge_server, edge_thread, "edge_server_thread_did_not_stop")
        _stop_server(origin_server, origin_thread, "origin_server_thread_did_not_stop")

    origin_server, origin_thread, origin_port = _start_origin(
        canary_database=canary_database,
        secure_static_root=secure_static_root,
        bundles=bundles,
        sequence_by_grammar=sequence_by_grammar,
    )
    edge_server, edge_thread, edge_port = _start_edge(upstream_port=origin_port)
    try:
        resumed, _ = _edge_request(edge_port, "GET", "/api/session/active", cookie=cookie)
        if (
            resumed.get("active") is not True
            or resumed.get("session", {}).get("session_id") != READING_SESSION_ID
            or resumed.get("session", {}).get("session_version") != scored.get("session_version")
        ):
            raise ReverseProxyAcceptanceError("edge_restart_resume_invalid")
        done, _ = _edge_request(
            edge_port,
            "POST",
            "/api/session/complete",
            {
                "session_id": READING_SESSION_ID,
                "expected_session_version": resumed["session"]["session_version"],
                "at": "2026-01-13T00:00:40Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
        )
        if done.get("session_state") != "COMPLETED":
            raise ReverseProxyAcceptanceError("edge_reading_completion_invalid")

        bootstrap, _ = _edge_request(edge_port, "GET", "/api/bootstrap", cookie=cookie)
        writing_lane = s11.s10._lane(bootstrap, sequence_index=24, skill="WRITING")
        writing_asset, correct = s11.s10.s09.s08._deterministic_response(
            canary_database, writing_lane["assets"], should_pass=True
        )
        writing, _ = _edge_request(
            edge_port,
            "POST",
            "/api/session/start",
            {
                "learner_id": CANARY_LEARNER_ID,
                "lesson_id": writing_lane["lesson_id"],
                "session_id": WRITING_SESSION_ID,
                "at": "2026-01-13T00:01:00Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
        )
        writing, _ = _edge_request(
            edge_port,
            "POST",
            "/api/exposure",
            {
                "session_id": WRITING_SESSION_ID,
                "asset_key": writing_asset,
                "expected_session_version": writing["session_version"],
                "at": "2026-01-13T00:01:10Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
        )
        writing_scored, _ = _edge_request(
            edge_port,
            "POST",
            "/api/response",
            {
                "learner_id": CANARY_LEARNER_ID,
                "session_id": WRITING_SESSION_ID,
                "asset_key": writing_asset,
                "response": correct,
                "expected_session_version": writing["session_version"],
                "attempt_id": WRITING_ATTEMPT_ID,
                "submitted_at": "2026-01-13T00:01:20Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
        )
        if writing_scored.get("outcome") != "AUTO_PASS":
            raise ReverseProxyAcceptanceError("edge_writing_pass_path_invalid")
        done, _ = _edge_request(
            edge_port,
            "POST",
            "/api/session/complete",
            {
                "session_id": WRITING_SESSION_ID,
                "expected_session_version": writing_scored["session_version"],
                "at": "2026-01-13T00:01:30Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
        )
        if done.get("session_state") != "COMPLETED":
            raise ReverseProxyAcceptanceError("edge_writing_completion_invalid")

        speaking_lane = s11.s10._lane(bootstrap, sequence_index=24, skill="SPEAKING")
        speaking_asset = str(speaking_lane["assets"][0]["asset_key"])
        speaking, _ = _edge_request(
            edge_port,
            "POST",
            "/api/session/start",
            {
                "learner_id": CANARY_LEARNER_ID,
                "lesson_id": speaking_lane["lesson_id"],
                "session_id": SPEAKING_SESSION_ID,
                "at": "2026-01-13T00:02:00Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
        )
        speaking, _ = _edge_request(
            edge_port,
            "POST",
            "/api/exposure",
            {
                "session_id": SPEAKING_SESSION_ID,
                "asset_key": speaking_asset,
                "expected_session_version": speaking["session_version"],
                "at": "2026-01-13T00:02:10Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
        )
        error, _ = _edge_request(
            edge_port,
            "POST",
            "/api/response",
            {
                "learner_id": CANARY_LEARNER_ID,
                "session_id": SPEAKING_SESSION_ID,
                "asset_key": speaking_asset,
                "response": "blocked remote speaking submission",
                "expected_session_version": speaking["session_version"],
            },
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
            expected_status=400,
        )
        if error.get("error") != "response_capture_not_enabled_for_asset":
            raise ReverseProxyAcceptanceError("edge_speaking_block_invalid")
        done, _ = _edge_request(
            edge_port,
            "POST",
            "/api/session/abandon",
            {
                "session_id": SPEAKING_SESSION_ID,
                "expected_session_version": speaking["session_version"],
                "at": "2026-01-13T00:02:20Z",
            },
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
        )
        if done.get("session_state") != "ABANDONED":
            raise ReverseProxyAcceptanceError("edge_speaking_abandon_invalid")
        progress, _ = _edge_request(edge_port, "GET", "/api/progress", cookie=cookie)
        progress_counts = s11.s10._validate_progress(progress)
        _edge_request(
            edge_port,
            "POST",
            "/auth/logout",
            {},
            cookie=cookie,
            csrf=csrf,
            origin=CANARY_PUBLIC_ORIGIN,
        )
        _edge_request(edge_port, "GET", "/api/bootstrap", cookie=cookie, expected_status=401)
    finally:
        _stop_server(edge_server, edge_thread, "edge_server_thread_did_not_stop")
        _stop_server(origin_server, origin_thread, "origin_server_thread_did_not_stop")

    return {
        **denominators,
        **progress_counts,
        "reverse_proxy_bundle_rendered": True,
        "remote_shaped_edge_acceptance": True,
        "direct_origin_bypass_blocked": True,
        "forwarded_https_enforced": True,
        "forwarded_host_enforced": True,
        "hsts_observed_at_edge": True,
        "secure_host_cookie_observed": True,
        "authenticated_session_survived_origin_and_edge_restart": True,
        "unit01_reading_auto_fail": True,
        "unit24_writing_auto_pass": True,
        "unit24_speaking_submission_blocked": True,
        "logout_revocation_observed": True,
        "origin_server_start_count": 2,
        "edge_proxy_start_count": 2,
        "acceptance_mode": "SIMULATED_EXTERNAL_HTTPS_EDGE",
    }


def materialize(*, s11_receipt_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    s11_receipt_path = Path(s11_receipt_path).resolve()
    s11_receipt, production_database, bundle_index, secure_static, bundles, sequence = _verify_s11(
        s11_receipt_path
    )
    output_root = Path(output_root).resolve()
    candidate_root = output_root / "secure_reverse_proxy_remote_acceptance"
    if candidate_root.exists():
        shutil.rmtree(candidate_root)
    candidate_root.mkdir(parents=True, exist_ok=True)
    deployment_bundle = _write_deployment_bundle(candidate_root / "deployment_bundle")
    canary_database = candidate_root / "s12_remote_acceptance_canary.sqlite3"
    shutil.copy2(production_database, canary_database)
    production_sha_before = file_digest(production_database)
    acceptance = _run_remote_shaped_acceptance(
        canary_database=canary_database,
        secure_static_root=secure_static,
        bundles=bundles,
        sequence_by_grammar=sequence,
    )
    production_sha_after = file_digest(production_database)
    if production_sha_before != production_sha_after:
        raise ReverseProxyAcceptanceError("production_database_mutated_by_s12_acceptance")

    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "s11_sha256": digest(s11_receipt),
            "production_database_sha256": production_sha_before,
        },
        "runtime_outputs": {
            "root": str(candidate_root),
            "source_s11_receipt_path": str(s11_receipt_path),
            "source_database_path": str(production_database),
            "source_bundle_index_path": str(bundle_index),
            "secure_static_root": str(secure_static),
            "canary_database_path": str(canary_database),
            **deployment_bundle,
        },
        "remote_acceptance_summary": acceptance,
        "production_safety": {
            "database_sha256_before": production_sha_before,
            "database_sha256_after": production_sha_after,
            "production_database_unchanged": True,
            "remote_acceptance_executed_on_isolated_clone": True,
            "real_learner_progress_mutated_by_canary": False,
        },
        "deployment_boundary": {
            "application_origin_loopback_only": True,
            "reverse_proxy_tls_termination_required": True,
            "exact_public_host_required": True,
            "exact_https_origin_required": True,
            "forwarded_https_required": True,
            "forwarded_host_required": True,
            "secrets_environment_only": True,
            "secrets_serialized_to_artifact": False,
            "dns_configuration_completed": False,
            "certificate_issuance_completed": False,
            "live_remote_deployment_completed": False,
            "external_remote_acceptance_completed": False,
            "public_release_completed": False,
        },
        "rollback_boundary": {
            "proxy_route_removal_preserves_origin": True,
            "database_rollback_required": False,
            "automatic_public_reenable_allowed": False,
        },
        "entrypoint": {
            "origin_serve_command_available": True,
            "deployment_bundle_available": True,
            "readback_command_available": True,
            "default_origin_host": "127.0.0.1",
            "default_origin_port": 8765,
        },
        "capability_contract": {
            "s11_authenticated_boundary_reused": True,
            "s10_release_candidate_reused": True,
            "s09_twentyfour_unit_runtime_reused": True,
            "m3_session_progress_authority_reused": True,
            "m5_renderer_authority_reused": True,
            "m6_response_scoring_authority_reused": True,
            "reverse_proxy_deployment_bundle_materialized": True,
            "remote_shaped_https_acceptance_executed": True,
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
            "live_remote_deployment_claimed": False,
            "external_remote_acceptance_claimed": False,
            "public_online_delivery_claimed": False,
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
        "remote_acceptance_summary": deepcopy(acceptance),
        "production_safety": {
            "production_database_unchanged": True,
            "remote_acceptance_executed_on_isolated_clone": True,
            "real_learner_progress_mutated_by_canary": False,
        },
        "deployment_boundary": deepcopy(receipt_core["deployment_boundary"]),
        "rollback_boundary": deepcopy(receipt_core["rollback_boundary"]),
        "entrypoint": deepcopy(receipt_core["entrypoint"]),
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def _source_s11(receipt_path: Path) -> tuple[dict[str, Any], Path]:
    receipt = read_json(receipt_path, "s12_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    if identity != (TASK_ID, SCHEMA_VERSION, PASS_STATUS, PRODUCT_STATUS, "NONE"):
        raise ReverseProxyAcceptanceError("s12_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise ReverseProxyAcceptanceError("s12_receipt_digest_invalid")
    source = Path(str(receipt.get("runtime_outputs", {}).get("source_s11_receipt_path") or "")).resolve()
    _verify_s11(source)
    return receipt, source


def serve_origin(*, receipt_path: Path, host: str, port: int) -> None:
    _, source_s11 = _source_s11(receipt_path)
    s11.serve(receipt_path=source_s11, host=host, port=port)


def readback(*, receipt_path: Path) -> dict[str, Any]:
    receipt, source_s11 = _source_s11(receipt_path)
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "remote_acceptance_summary": deepcopy(receipt["remote_acceptance_summary"]),
        "deployment_boundary": deepcopy(receipt["deployment_boundary"]),
        "rollback_boundary": deepcopy(receipt["rollback_boundary"]),
        "source_authenticated_boundary": s11.readback(receipt_path=source_s11),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s11", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    server = commands.add_parser("serve-origin")
    server.add_argument("--receipt", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8765)
    snap = commands.add_parser("readback")
    snap.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve-origin":
            serve_origin(receipt_path=args.receipt, host=args.host, port=args.port)
            return 0
        if args.command == "readback":
            print(json.dumps(readback(receipt_path=args.receipt), ensure_ascii=False, indent=2))
            return 0
        receipt, safe = materialize(s11_receipt_path=args.s11, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s12_secure_reverse_proxy_remote_acceptance import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s11_path=args.s11,
        )
        if validation["error_count"]:
            raise ReverseProxyAcceptanceError(
                "validation_failed:" + "|".join(validation["errors"])
            )
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        ReverseProxyAcceptanceError,
        s11.SecureBoundaryError,
        s11.s10.ReleaseCandidateError,
        s11.s10.s09.PopulationError,
        s11.s10.s09.s08.JourneyQAError,
        OSError,
        sqlite3.Error,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
