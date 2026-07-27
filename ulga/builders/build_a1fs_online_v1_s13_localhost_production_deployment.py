#!/usr/bin/env python3
"""Materialize and accept the formal localhost deployment for A1FS Online V1.

S13 keeps the application on 127.0.0.1, reuses the S11 authenticated boundary and
S09 learner runtime, renders operational Windows launch/stop/status scripts, proves
read-only authenticated access against the production database, and persists logout
revocation across process restarts in a separate auth-state SQLite database. It does
not enable audio, Listening, Speaking capture, mastery, Cloudflare, DNS, or external
network access.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_online_v1_s12_secure_reverse_proxy_remote_acceptance as s12  # noqa: E402

s11 = s12.s11

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Builds and accepts an operational 127.0.0.1 deployment bundle around the existing S11/S09 runtime, including persistent auth-session revocation and process lifecycle scripts; it authors no curriculum, learner content, answers, audio, mastery, A2 unlock, Cloudflare route, DNS change, or external release."

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S13_LocalhostProductionDeploymentAndOperatorAcceptance_NoAudio"
SCHEMA_VERSION = "a1fs.online.v1.s13.localhost_production_deployment.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S13_LOCALHOST_PRODUCTION_DEPLOYMENT_READY"
PRODUCT_STATUS = "LOCALHOST_PRODUCTION_DEPLOYMENT_OPERATOR_ACCEPTED_NOT_EXTERNAL"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S14_CloudflareDeploymentTargetSelectionAndExternalAcceptance_NoAudio"

CANARY_USERNAME = "s13-local-canary"
CANARY_PASSWORD = "S13-Local-Canary-Password-Only-For-Acceptance-2026!"
CANARY_SESSION_SECRET = "S13-Local-Canary-Session-Signing-Secret-For-Acceptance-2026!"
DEFAULT_PORT = 8765

FORBIDDEN_SAFE_KEYS = {
    "accepted_texts", "accepted_sequence", "answer", "answer_contract", "answer_key",
    "asset_key", "auth_password", "csrf", "database_path", "display_label", "learner_id",
    "learner_payload", "password", "private_scoring_contract", "private_subject_digest",
    "prompt", "prompt_text", "response", "rubric", "scoring_contract", "session_id",
    "session_secret", "subject_key", "token",
}


class LocalhostDeploymentError(ValueError):
    """Fail-closed S13 deployment or acceptance error."""


def digest(value: Any) -> str:
    return s12.digest(value)


def file_digest(path: Path) -> str:
    return s12.file_digest(path)


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalhostDeploymentError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise LocalhostDeploymentError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    s12.write_json(Path(path), value, private=private)


def safe_scan(value: Any) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in FORBIDDEN_SAFE_KEYS:
                    raise LocalhostDeploymentError(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def _verify_s12(
    receipt_path: Path,
) -> tuple[dict[str, Any], Path, Path, Path, dict[str, dict[str, Any]], dict[str, int]]:
    receipt_path = Path(receipt_path).resolve()
    receipt = read_json(receipt_path, "s12_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    if identity != (s12.TASK_ID, s12.SCHEMA_VERSION, s12.PASS_STATUS, s12.PRODUCT_STATUS, "NONE"):
        raise LocalhostDeploymentError("s12_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise LocalhostDeploymentError("s12_receipt_digest_invalid")
    remote = receipt.get("remote_acceptance_summary", {})
    if (
        remote.get("unit_count") != 24
        or remote.get("lesson_count") != 72
        or remote.get("asset_count") != 264
        or remote.get("remote_shaped_edge_acceptance") is not True
        or receipt.get("production_safety", {}).get("production_database_unchanged") is not True
    ):
        raise LocalhostDeploymentError("s12_acceptance_contract_invalid")
    source_s11 = Path(str(receipt.get("runtime_outputs", {}).get("source_s11_receipt_path") or "")).resolve()
    if not source_s11.is_file():
        raise LocalhostDeploymentError("s12_source_s11_missing")
    _, database, bundle_index, secure_static, bundles, sequence = s12._verify_s11(source_s11)
    return receipt, database, bundle_index, secure_static, bundles, sequence


class PersistentBoundaryConfig(s11.BoundaryConfig):
    """S11 boundary configuration with process-persistent session revocation."""

    revocation_db_path: Path

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
        revocation_db_path: Path,
        port: int = 0,
    ) -> "PersistentBoundaryConfig":
        base = s11.BoundaryConfig.from_values(
            username=username,
            password=password,
            session_secret=session_secret,
            mode=mode,
            allowed_origin=allowed_origin,
            allowed_host=allowed_host,
            port=port,
        )
        config = cls(
            username=base.username,
            credential_hash=base.credential_hash,
            signing_key=base.signing_key,
            mode=base.mode,
            allowed_origin=base.allowed_origin,
            allowed_host=base.allowed_host,
            session_ttl_seconds=base.session_ttl_seconds,
            max_login_failures=base.max_login_failures,
            login_window_seconds=base.login_window_seconds,
            local_port=base.local_port,
        )
        config.revocation_db_path = Path(revocation_db_path).resolve()
        config._initialize_revocation_store()
        return config

    @classmethod
    def from_environment(
        cls,
        *,
        host: str,
        port: int,
        revocation_db_path: Path,
    ) -> "PersistentBoundaryConfig":
        import os

        if not s11._is_loopback(host):
            raise LocalhostDeploymentError(f"non_loopback_host_forbidden:{host}")
        mode = os.environ.get("A1FS_S11_MODE", "local").strip().casefold() or "local"
        if mode != "local":
            raise LocalhostDeploymentError("s13_local_mode_required")
        return cls.from_values(
            username=os.environ.get("A1FS_S11_AUTH_USERNAME", ""),
            password=os.environ.get("A1FS_S11_AUTH_PASSWORD", ""),
            session_secret=os.environ.get("A1FS_S11_SESSION_SECRET", ""),
            mode="local",
            allowed_origin=f"http://127.0.0.1:{port}",
            allowed_host="127.0.0.1",
            revocation_db_path=revocation_db_path,
            port=port,
        )

    def _initialize_revocation_store(self) -> None:
        self.revocation_db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.revocation_db_path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS revoked_sessions (
                       nonce TEXT PRIMARY KEY,
                       revoked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                   )"""
            )
            connection.commit()

    def verify_session(self, token: str, *, now: int | None = None) -> dict[str, Any]:
        claims = super().verify_session(token, now=now)
        with sqlite3.connect(self.revocation_db_path) as connection:
            row = connection.execute(
                "SELECT 1 FROM revoked_sessions WHERE nonce=?",
                (str(claims["nonce"]),),
            ).fetchone()
        if row is not None:
            raise s11.SecureBoundaryError("session_revoked")
        return claims

    def revoke(self, nonce: str) -> None:
        super().revoke(nonce)
        with sqlite3.connect(self.revocation_db_path) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO revoked_sessions(nonce) VALUES(?)",
                (str(nonce),),
            )
            connection.commit()


def _start_server(
    *,
    app: Any,
    secure_static_root: Path,
    config: PersistentBoundaryConfig,
    port: int = 0,
) -> tuple[s11.SecureBoundaryServer, threading.Thread, int]:
    server = s11.SecureBoundaryServer(("127.0.0.1", port), app, secure_static_root, config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, int(server.server_address[1])


def _stop_server(server: s11.SecureBoundaryServer, thread: threading.Thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=10)
    if thread.is_alive():
        raise LocalhostDeploymentError("localhost_server_thread_did_not_stop")


def _app(database: Path, bundles: Mapping[str, Mapping[str, Any]], sequence: Mapping[str, int]) -> Any:
    return s11.s10.s09.PopulationWorkbenchApplication(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence,
        default_learner_id=s11.s10.s09.s05.DEFAULT_LEARNER_ID,
    )


def _config(state_db: Path, port: int = 0) -> PersistentBoundaryConfig:
    return PersistentBoundaryConfig.from_values(
        username=CANARY_USERNAME,
        password=CANARY_PASSWORD,
        session_secret=CANARY_SESSION_SECRET,
        mode="local",
        allowed_origin="http://127.0.0.1",
        allowed_host="127.0.0.1",
        revocation_db_path=state_db,
        port=port,
    )


def _run_localhost_acceptance(
    *,
    production_database: Path,
    secure_static_root: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
    auth_state_db: Path,
) -> dict[str, Any]:
    production_sha_before = file_digest(production_database)
    config1 = _config(auth_state_db)
    server, thread, port = _start_server(
        app=_app(production_database, bundles, sequence),
        secure_static_root=secure_static_root,
        config=config1,
    )
    origin = f"http://127.0.0.1:{port}"
    try:
        health, headers = s11._request(port, "GET", "/api/health")
        if health.get("authentication_required") is not True:
            raise LocalhostDeploymentError("localhost_health_contract_invalid")
        if headers.get("X-Frame-Options") != "DENY":
            raise LocalhostDeploymentError("localhost_security_headers_invalid")
        s11._request(port, "GET", "/api/bootstrap", expected_status=401)
        login, login_headers = s11._request(
            port,
            "POST",
            "/auth/login",
            {"username": CANARY_USERNAME, "password": CANARY_PASSWORD},
            origin=origin,
        )
        cookie_header = str(login_headers.get("Set-Cookie") or "")
        cookie = cookie_header.split(";", 1)[0]
        csrf = str(login.get("csrf_token") or "")
        if not cookie or not csrf or "HttpOnly" not in cookie_header or "SameSite=Strict" not in cookie_header:
            raise LocalhostDeploymentError("localhost_login_cookie_invalid")
        bootstrap, _ = s11._request(port, "GET", "/api/bootstrap", cookie=cookie)
        denominators = s11.s10._validate_bootstrap(bootstrap)
        progress, _ = s11._request(port, "GET", "/api/progress", cookie=cookie)
        if not isinstance(progress.get("summary"), Mapping):
            raise LocalhostDeploymentError("localhost_progress_readback_invalid")
    finally:
        _stop_server(server, thread)

    config2 = _config(auth_state_db)
    server, thread, port = _start_server(
        app=_app(production_database, bundles, sequence),
        secure_static_root=secure_static_root,
        config=config2,
    )
    origin = f"http://127.0.0.1:{port}"
    try:
        session, _ = s11._request(port, "GET", "/auth/session", cookie=cookie)
        if session.get("authenticated") is not True or session.get("csrf_token") != csrf:
            raise LocalhostDeploymentError("localhost_signed_session_restart_invalid")
        s11._request(
            port,
            "POST",
            "/auth/logout",
            {},
            cookie=cookie,
            csrf=csrf,
            origin=origin,
        )
        s11._request(port, "GET", "/api/bootstrap", cookie=cookie, expected_status=401)
    finally:
        _stop_server(server, thread)

    config3 = _config(auth_state_db)
    server, thread, port = _start_server(
        app=_app(production_database, bundles, sequence),
        secure_static_root=secure_static_root,
        config=config3,
    )
    try:
        s11._request(port, "GET", "/api/bootstrap", cookie=cookie, expected_status=401)
    finally:
        _stop_server(server, thread)

    production_sha_after = file_digest(production_database)
    if production_sha_before != production_sha_after:
        raise LocalhostDeploymentError("production_database_mutated_by_localhost_acceptance")
    with sqlite3.connect(auth_state_db) as connection:
        revoked_count = int(connection.execute("SELECT COUNT(*) FROM revoked_sessions").fetchone()[0])
    if revoked_count != 1:
        raise LocalhostDeploymentError(f"persistent_revocation_count_invalid:{revoked_count}")
    return {
        **denominators,
        "health_endpoint_pass": True,
        "authentication_required": True,
        "production_database_read_only_smoke": True,
        "authenticated_bootstrap_pass": True,
        "progress_readback_pass": True,
        "session_survived_process_restart": True,
        "logout_revocation_survived_process_restart": True,
        "persistent_revocation_count": 1,
        "application_server_start_count": 3,
        "loopback_binding_only": True,
        "port": DEFAULT_PORT,
    }


def _write_launch_bundle(
    *,
    target_root: Path,
    receipt_path: Path,
    auth_state_db: Path,
) -> dict[str, Any]:
    target_root = Path(target_root).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    pid_file = target_root / "a1fs_localhost.pid"
    stdout_log = target_root / "a1fs_localhost.stdout.log"
    stderr_log = target_root / "a1fs_localhost.stderr.log"

    start_script = f'''param(
    [string]$CodeRoot = "G:\\HomeWork\\English_Learning_DB_Main",
    [int]$Port = {DEFAULT_PORT}
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Receipt = "{str(receipt_path).replace(chr(34), chr(34)+chr(34))}"
$PidFile = "{str(pid_file).replace(chr(34), chr(34)+chr(34))}"
$Stdout = "{str(stdout_log).replace(chr(34), chr(34)+chr(34))}"
$Stderr = "{str(stderr_log).replace(chr(34), chr(34)+chr(34))}"
foreach ($Name in @("A1FS_S11_AUTH_USERNAME","A1FS_S11_AUTH_PASSWORD","A1FS_S11_SESSION_SECRET")) {{
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name))) {{ throw "MISSING_ENV=$Name" }}
}}
$env:A1FS_S11_MODE = "local"
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {{ throw "PORT_IN_USE=$Port" }}
if (Test-Path -LiteralPath $PidFile) {{ throw "PID_FILE_ALREADY_EXISTS=$PidFile" }}
Set-Location $CodeRoot
$Python = (Get-Command python).Source
$Process = Start-Process -FilePath $Python -WorkingDirectory $CodeRoot -ArgumentList @(
    "-m","ulga.builders.build_a1fs_online_v1_s13_localhost_production_deployment",
    "serve","--receipt",$Receipt,"--host","127.0.0.1","--port",[string]$Port
) -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr -PassThru
[System.IO.File]::WriteAllText($PidFile,[string]$Process.Id)
for ($Attempt=1; $Attempt -le 40; $Attempt++) {{
    if ($Process.HasExited) {{ throw "A1FS_PROCESS_EXITED=$($Process.ExitCode)" }}
    try {{
        $Health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2
        if ($Health.status -eq "PASS" -and $Health.authentication_required -eq $true) {{
            Write-Host "A1FS_LOCALHOST_STARTED=PASS"
            Write-Host "PID=$($Process.Id)"
            Write-Host "URL=http://127.0.0.1:$Port"
            exit 0
        }}
    }} catch {{ Start-Sleep -Milliseconds 500 }}
}}
Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
throw "A1FS_LOCALHOST_READINESS_TIMEOUT"
'''

    stop_script = f'''param([int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PidFile = "{str(pid_file).replace(chr(34), chr(34)+chr(34))}"
if (-not (Test-Path -LiteralPath $PidFile)) {{ throw "PID_FILE_MISSING=$PidFile" }}
$PidValue = [int](Get-Content -LiteralPath $PidFile -Raw)
$Process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
if ($null -eq $Process) {{ Remove-Item -LiteralPath $PidFile -Force; throw "STALE_PID_FILE=$PidValue" }}
$Command = (Get-CimInstance Win32_Process -Filter "ProcessId=$PidValue").CommandLine
if ($Command -notlike "*build_a1fs_online_v1_s13_localhost_production_deployment*") {{ throw "PID_OWNERSHIP_MISMATCH=$PidValue" }}
Stop-Process -Id $PidValue -Force
for ($Attempt=1; $Attempt -le 20; $Attempt++) {{
    if (-not (Get-Process -Id $PidValue -ErrorAction SilentlyContinue)) {{ break }}
    Start-Sleep -Milliseconds 250
}}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {{ throw "PORT_STILL_LISTENING=$Port" }}
Remove-Item -LiteralPath $PidFile -Force
Write-Host "A1FS_LOCALHOST_STOPPED=PASS"
'''

    status_script = f'''param([int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PidFile = "{str(pid_file).replace(chr(34), chr(34)+chr(34))}"
if (-not (Test-Path -LiteralPath $PidFile)) {{ throw "A1FS_LOCALHOST_STATUS=STOPPED" }}
$PidValue = [int](Get-Content -LiteralPath $PidFile -Raw)
if (-not (Get-Process -Id $PidValue -ErrorAction SilentlyContinue)) {{ throw "A1FS_LOCALHOST_STATUS=STALE_PID" }}
$Listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($null -eq $Listener -or $Listener.OwningProcess -ne $PidValue) {{ throw "A1FS_LOCALHOST_STATUS=PORT_OWNERSHIP_INVALID" }}
$Health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
if ($Health.status -ne "PASS" -or $Health.authentication_required -ne $true) {{ throw "A1FS_LOCALHOST_STATUS=UNHEALTHY" }}
Write-Host "A1FS_LOCALHOST_STATUS=RUNNING"
Write-Host "PID=$PidValue"
Write-Host "URL=http://127.0.0.1:$Port"
'''

    files = {
        "start_a1fs_localhost.ps1": start_script,
        "stop_a1fs_localhost.ps1": stop_script,
        "status_a1fs_localhost.ps1": status_script,
    }
    for name, content in files.items():
        (target_root / name).write_text(content, encoding="utf-8")

    contract = {
        "schema_version": "a1fs.online.v1.s13.localhost_deployment_contract.v1",
        "host": "127.0.0.1",
        "port": DEFAULT_PORT,
        "authentication_required": True,
        "required_environment_variables": [
            "A1FS_S11_AUTH_USERNAME",
            "A1FS_S11_AUTH_PASSWORD",
            "A1FS_S11_SESSION_SECRET",
        ],
        "secret_values_embedded": False,
        "pid_file": str(pid_file),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "auth_state_database": str(auth_state_db),
        "external_network_binding_allowed": False,
        "cloudflare_enabled": False,
        "audio_enabled": False,
    }
    write_json(target_root / "localhost_deployment_contract.json", contract)
    return {
        "bundle_root": str(target_root),
        "start_script_path": str(target_root / "start_a1fs_localhost.ps1"),
        "stop_script_path": str(target_root / "stop_a1fs_localhost.ps1"),
        "status_script_path": str(target_root / "status_a1fs_localhost.ps1"),
        "deployment_contract_path": str(target_root / "localhost_deployment_contract.json"),
        "pid_file_path": str(pid_file),
        "stdout_log_path": str(stdout_log),
        "stderr_log_path": str(stderr_log),
        "auth_state_database_path": str(auth_state_db),
    }


def materialize(*, s12_receipt_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    s12_receipt, production_database, bundle_index, secure_static, bundles, sequence = _verify_s12(s12_receipt_path)
    output_root = Path(output_root).resolve()
    root = output_root / "localhost_production_deployment"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    auth_state_db = root / "runtime" / "a1fs_auth_state.sqlite3"
    acceptance = _run_localhost_acceptance(
        production_database=production_database,
        secure_static_root=secure_static,
        bundles=bundles,
        sequence=sequence,
        auth_state_db=auth_state_db,
    )
    production_sha = file_digest(production_database)
    launch_bundle = _write_launch_bundle(
        target_root=root / "launch_bundle",
        receipt_path=output_root / "localhost_production_deployment.private.json",
        auth_state_db=auth_state_db,
    )
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "s12_sha256": digest(s12_receipt),
            "production_database_sha256": production_sha,
        },
        "runtime_outputs": {
            "root": str(root),
            "source_s12_receipt_path": str(Path(s12_receipt_path).resolve()),
            "source_database_path": str(production_database),
            "source_bundle_index_path": str(bundle_index),
            "secure_static_root": str(secure_static),
            **launch_bundle,
        },
        "localhost_acceptance_summary": acceptance,
        "production_safety": {
            "production_database_unchanged": True,
            "acceptance_used_read_only_production_smoke": True,
            "learner_progress_mutated_by_acceptance": False,
            "auth_state_separated_from_learner_database": True,
        },
        "deployment_boundary": {
            "formal_localhost_launch_ready": True,
            "host": "127.0.0.1",
            "port": DEFAULT_PORT,
            "external_network_binding_allowed": False,
            "cloudflare_enabled": False,
            "dns_configuration_completed": False,
            "public_release_completed": False,
            "secrets_environment_only": True,
            "secrets_serialized_to_artifact": False,
        },
        "rollback_boundary": {
            "stop_script_available": True,
            "pid_ownership_verified_before_stop": True,
            "port_released_after_stop_required": True,
            "production_database_rollback_required": False,
            "automatic_external_reenable_allowed": False,
        },
        "capability_contract": {
            "s12_deployment_bundle_reused": True,
            "s11_authenticated_boundary_reused": True,
            "s09_twentyfour_unit_runtime_reused": True,
            "persistent_logout_revocation_connected": True,
            "process_lifecycle_bundle_materialized": True,
            "formal_localhost_launch_ready": True,
            "parallel_curriculum_created": False,
            "parallel_learner_state_engine_created": False,
            "parallel_scoring_engine_created": False,
            "speaking_capture_enabled": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "mastery_write_enabled": False,
        },
        "product_status": PRODUCT_STATUS,
        "claim_boundaries": {
            "localhost_production_ready_claimed": True,
            "external_remote_deployment_claimed": False,
            "cloudflare_deployment_claimed": False,
            "public_online_delivery_claimed": False,
            "audio_complete": False,
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
        "localhost_acceptance_summary": deepcopy(acceptance),
        "production_safety": deepcopy(receipt_core["production_safety"]),
        "deployment_boundary": deepcopy(receipt_core["deployment_boundary"]),
        "rollback_boundary": deepcopy(receipt_core["rollback_boundary"]),
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def _source_s12(receipt_path: Path) -> tuple[dict[str, Any], Path, Path]:
    receipt = read_json(receipt_path, "s13_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    if identity != (TASK_ID, SCHEMA_VERSION, PASS_STATUS, PRODUCT_STATUS, "NONE"):
        raise LocalhostDeploymentError("s13_receipt_contract_invalid")
    core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(core):
        raise LocalhostDeploymentError("s13_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs", {})
    source_s12 = Path(str(outputs.get("source_s12_receipt_path") or "")).resolve()
    auth_state = Path(str(outputs.get("auth_state_database_path") or "")).resolve()
    _verify_s12(source_s12)
    return receipt, source_s12, auth_state


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    _, source_s12, auth_state = _source_s12(receipt_path)
    _, production_database, _, secure_static, bundles, sequence = _verify_s12(source_s12)
    config = PersistentBoundaryConfig.from_environment(
        host=host,
        port=port,
        revocation_db_path=auth_state,
    )
    app = _app(production_database, bundles, sequence)
    server = s11.SecureBoundaryServer((host, port), app, secure_static, config)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def readback(*, receipt_path: Path) -> dict[str, Any]:
    receipt, source_s12, _ = _source_s12(receipt_path)
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "localhost_acceptance_summary": deepcopy(receipt["localhost_acceptance_summary"]),
        "deployment_boundary": deepcopy(receipt["deployment_boundary"]),
        "source_reverse_proxy_acceptance": s12.readback(receipt_path=source_s12),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s12", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    server = commands.add_parser("serve")
    server.add_argument("--receipt", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=DEFAULT_PORT)
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
        receipt, safe = materialize(s12_receipt_path=args.s12, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s13_localhost_production_deployment import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s12_path=args.s12,
        )
        if validation["error_count"]:
            raise LocalhostDeploymentError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        LocalhostDeploymentError,
        s12.ReverseProxyAcceptanceError,
        s11.SecureBoundaryError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
