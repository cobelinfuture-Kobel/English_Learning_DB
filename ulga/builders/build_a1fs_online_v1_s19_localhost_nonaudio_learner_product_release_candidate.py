#!/usr/bin/env python3
"""Build the formal localhost no-audio learner-product release candidate.

S19 packages the S17 runtime that passed S18 end-to-end recovery acceptance as a
versioned localhost release candidate. It snapshots only executable/static release
assets and operator contracts; authoritative learner, canonical-learning, and auth
state remain in their existing locations. Stateful smoke acceptance uses isolated
copies. No new learner capability, content, audio, A2, Cloudflare route, external
binding, or parallel engine is created.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_s18_nonaudio_learner_product_e2e_release_acceptance_recovery as s18

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Packages the already accepted S17/S18 localhost runtime into a versioned release candidate, "
    "writes operator/checksum contracts, and runs read-only authenticated smoke acceptance on "
    "isolated state copies. It creates no curriculum, learner content, answer, scoring, review, "
    "mastery, dashboard, role authority, audio, A2, Cloudflare route, external deployment, or "
    "parallel engine."
)

PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-S19_LocalhostNoAudioLearnerProductReleaseCandidate"
SCHEMA_VERSION = "a1fs.online.v1.s19.localhost_nonaudio_release_candidate.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_S19_LOCALHOST_NONAUDIO_RELEASE_CANDIDATE_READY"
PRODUCT_STATUS = "LOCALHOST_NONAUDIO_LEARNER_PRODUCT_RELEASE_CANDIDATE_READY_NOT_EXTERNAL"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
RELEASE_CANDIDATE_ID = "A1FS-ONLINE-V1-D0-RC1"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-S20_CloudflareDeploymentAndExternalAcceptance_NoAudio"
DEFAULT_PORT = 8765
CANARY_USERNAME = "s19-rc-operator"


class ReleaseCandidateError(ValueError):
    """Fail-closed S19 release-candidate error."""


def digest(value: Any) -> str:
    return s18.digest(value)


def file_digest(path: Path) -> str:
    return s18.file_digest(path)


def read_json(path: Path, code: str) -> dict[str, Any]:
    return s18.read_json(path, code)


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    s18.write_json(path, value, private=private)


def safe_scan(value: Any) -> None:
    s18.safe_scan(value)


def directory_digest(root: Path) -> str:
    """Hash relative paths and bytes for a deterministic directory identity."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise ReleaseCandidateError(f"directory_missing:{root}")
    hasher = hashlib.sha256()
    for path in sorted((row for row in root.rglob("*") if row.is_file()), key=lambda row: row.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        hasher.update(len(relative).to_bytes(8, "big"))
        hasher.update(relative)
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
    return hasher.hexdigest()


def _copy_state(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        target.mkdir(parents=True, exist_ok=True)


def _verify_s18(
    receipt_path: Path,
) -> tuple[
    dict[str, Any], Path, Path, dict[str, dict[str, Any]], dict[str, int], Path,
    Path, Path, Path, dict[str, Path],
]:
    receipt_path = Path(receipt_path).resolve()
    receipt = read_json(receipt_path, "s18_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    if identity != (s18.TASK_ID, s18.SCHEMA_VERSION, s18.PASS_STATUS, s18.PRODUCT_STATUS, "NONE"):
        raise ReleaseCandidateError("s18_receipt_contract_invalid")
    body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(body):
        raise ReleaseCandidateError("s18_receipt_digest_invalid")
    summary = receipt.get("e2e_release_acceptance_summary", {})
    expected = {
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "scored_lesson_count": 48,
        "speaking_practice_lesson_count": 24,
        "dashboard_role_count": 3,
        "authenticated_session_survived_server_restart": True,
        "active_learning_session_survived_server_restart": True,
        "progress_survived_server_restart": True,
        "dashboard_survived_server_restart": True,
        "review_queue_survived_server_restart": True,
        "logout_revocation_survived_server_restart": True,
        "start_script_contract_pass": True,
        "stop_script_contract_pass": True,
        "status_script_contract_pass": True,
        "launch_contract_boundary_pass": True,
        "p0_blocker_count": 0,
        "p1_blocker_count": 0,
        "production_database_unchanged": True,
        "release_candidate_created": False,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise ReleaseCandidateError(f"s18_acceptance_contract_invalid:{key}")
    source_s17 = Path(str(receipt.get("runtime_outputs", {}).get("source_s17_receipt_path") or "")).resolve()
    if not source_s17.is_file():
        raise ReleaseCandidateError("s18_source_s17_receipt_missing")
    (
        _, production_database, auth_state, bundles, sequence, graph_path,
        state_root, secure_static,
    ) = s18.s17._load_runtime(source_s17)
    if len(bundles) != 72 or len(sequence) != 24:
        raise ReleaseCandidateError("s19_runtime_denominator_invalid")
    if not production_database.is_file() or not graph_path.is_file() or not state_root.is_dir():
        raise ReleaseCandidateError("s19_authoritative_runtime_source_missing")
    if not auth_state.is_file() or not secure_static.is_dir():
        raise ReleaseCandidateError("s19_auth_or_static_source_missing")
    s17_outputs = read_json(source_s17, "s17_receipt").get("runtime_outputs", {})
    launch_paths = {
        name: Path(str(s17_outputs.get(key) or "")).resolve()
        for name, key in {
            "start": "start_script_path",
            "stop": "stop_script_path",
            "status": "status_script_path",
            "contract": "launch_contract_path",
        }.items()
    }
    if any(not path.is_file() for path in launch_paths.values()):
        raise ReleaseCandidateError("s17_operator_bundle_missing")
    return (
        receipt, production_database, auth_state, bundles, sequence, graph_path,
        state_root, secure_static, source_s17, launch_paths,
    )


def _write_operator_bundle(
    *, target_root: Path, receipt_path: Path, auth_state: Path,
) -> dict[str, str]:
    target_root = Path(target_root).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    pid_file = target_root / "a1fs_s19_localhost_rc.pid"
    stdout_log = target_root / "a1fs_s19_localhost_rc.stdout.log"
    stderr_log = target_root / "a1fs_s19_localhost_rc.stderr.log"
    module = "ulga.builders.build_a1fs_online_v1_s19_localhost_nonaudio_learner_product_release_candidate"
    start = f'''param([string]$CodeRoot = "G:\\HomeWork\\English_Learning_DB_Main",[int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Receipt = "{receipt_path}"
$PidFile = "{pid_file}"
$Stdout = "{stdout_log}"
$Stderr = "{stderr_log}"
foreach ($Name in @("A1FS_S11_AUTH_USERNAME","A1FS_S11_AUTH_PASSWORD","A1FS_S11_SESSION_SECRET")) {{ if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name))) {{ throw "MISSING_ENV=$Name" }} }}
$env:A1FS_S11_MODE = "local"
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {{ throw "PORT_IN_USE=$Port" }}
if (Test-Path -LiteralPath $PidFile) {{ throw "PID_FILE_ALREADY_EXISTS=$PidFile" }}
Set-Location $CodeRoot
$Process = Start-Process -FilePath (Get-Command python).Source -WorkingDirectory $CodeRoot -ArgumentList @("-m","{module}","serve","--receipt",$Receipt,"--host","127.0.0.1","--port",[string]$Port) -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr -PassThru
[System.IO.File]::WriteAllText($PidFile,[string]$Process.Id)
for ($Attempt=1; $Attempt -le 40; $Attempt++) {{ if ($Process.HasExited) {{ throw "A1FS_S19_PROCESS_EXITED=$($Process.ExitCode)" }}; try {{ $Health=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2; if ($Health.status -eq "PASS" -and $Health.authentication_required -eq $true) {{ Write-Host "A1FS_S19_LOCALHOST_RC_STARTED=PASS"; Write-Host "RELEASE_CANDIDATE_ID={RELEASE_CANDIDATE_ID}"; Write-Host "PID=$($Process.Id)"; Write-Host "URL=http://127.0.0.1:$Port"; exit 0 }} }} catch {{ Start-Sleep -Milliseconds 500 }} }}
Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
throw "A1FS_S19_LOCALHOST_READINESS_TIMEOUT"
'''
    stop = f'''param([int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PidFile = "{pid_file}"
if (-not (Test-Path -LiteralPath $PidFile)) {{ throw "PID_FILE_MISSING=$PidFile" }}
$PidValue=[int](Get-Content -LiteralPath $PidFile -Raw)
$Process=Get-Process -Id $PidValue -ErrorAction SilentlyContinue
if ($null -eq $Process) {{ Remove-Item -LiteralPath $PidFile -Force; throw "STALE_PID_FILE=$PidValue" }}
$Command=(Get-CimInstance Win32_Process -Filter "ProcessId=$PidValue").CommandLine
if ($Command -notlike "*build_a1fs_online_v1_s19_localhost_nonaudio_learner_product_release_candidate*") {{ throw "PID_OWNERSHIP_MISMATCH=$PidValue" }}
Stop-Process -Id $PidValue -Force
for ($Attempt=1; $Attempt -le 20; $Attempt++) {{ if (-not (Get-Process -Id $PidValue -ErrorAction SilentlyContinue)) {{ break }}; Start-Sleep -Milliseconds 250 }}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {{ throw "PORT_STILL_LISTENING=$Port" }}
Remove-Item -LiteralPath $PidFile -Force
Write-Host "A1FS_S19_LOCALHOST_RC_STOPPED=PASS"
'''
    status = f'''param([int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PidFile = "{pid_file}"
if (-not (Test-Path -LiteralPath $PidFile)) {{ throw "A1FS_S19_LOCALHOST_RC_STATUS=STOPPED" }}
$PidValue=[int](Get-Content -LiteralPath $PidFile -Raw)
if (-not (Get-Process -Id $PidValue -ErrorAction SilentlyContinue)) {{ throw "A1FS_S19_LOCALHOST_RC_STATUS=STALE_PID" }}
$Listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($null -eq $Listener -or $Listener.OwningProcess -ne $PidValue) {{ throw "A1FS_S19_LOCALHOST_RC_STATUS=PORT_OWNERSHIP_INVALID" }}
$Health=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
if ($Health.status -ne "PASS" -or $Health.authentication_required -ne $true) {{ throw "A1FS_S19_LOCALHOST_RC_STATUS=UNHEALTHY" }}
Write-Host "A1FS_S19_LOCALHOST_RC_STATUS=RUNNING"
Write-Host "RELEASE_CANDIDATE_ID={RELEASE_CANDIDATE_ID}"
Write-Host "PID=$PidValue"
Write-Host "URL=http://127.0.0.1:$Port"
'''
    readback = f'''param()
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
python -m {module} readback --receipt "{receipt_path}"
if ($LASTEXITCODE -ne 0) {{ throw "A1FS_S19_LOCALHOST_RC_READBACK_FAILED" }}
'''
    scripts = {
        "start_a1fs_s19_localhost_rc.ps1": start,
        "stop_a1fs_s19_localhost_rc.ps1": stop,
        "status_a1fs_s19_localhost_rc.ps1": status,
        "readback_a1fs_s19_localhost_rc.ps1": readback,
    }
    for name, content in scripts.items():
        (target_root / name).write_text(content, encoding="utf-8")
    contract = {
        "schema_version": "a1fs.online.v1.s19.localhost_release_contract.v1",
        "release_candidate_id": RELEASE_CANDIDATE_ID,
        "host": "127.0.0.1",
        "port": DEFAULT_PORT,
        "authentication_required": True,
        "csrf_required_for_state_change": True,
        "dashboard_role_count": 3,
        "human_review_authority": "A1FS_V1_M6",
        "required_environment_variables": [
            "A1FS_S11_AUTH_USERNAME", "A1FS_S11_AUTH_PASSWORD", "A1FS_S11_SESSION_SECRET",
        ],
        "secret_values_embedded": False,
        "auth_state_database_reused": str(Path(auth_state).resolve()),
        "external_network_binding_allowed": False,
        "public_delivery_enabled": False,
        "cloudflare_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "a2_session_enabled": False,
    }
    contract_path = target_root / "localhost_release_contract.json"
    write_json(contract_path, contract)
    return {
        "operator_root": str(target_root),
        "start_script_path": str(target_root / "start_a1fs_s19_localhost_rc.ps1"),
        "stop_script_path": str(target_root / "stop_a1fs_s19_localhost_rc.ps1"),
        "status_script_path": str(target_root / "status_a1fs_s19_localhost_rc.ps1"),
        "readback_script_path": str(target_root / "readback_a1fs_s19_localhost_rc.ps1"),
        "release_contract_path": str(contract_path),
        "pid_file_path": str(pid_file),
        "stdout_log_path": str(stdout_log),
        "stderr_log_path": str(stderr_log),
    }


def _operator_checks(outputs: Mapping[str, str]) -> dict[str, bool]:
    start = Path(outputs["start_script_path"]).read_text(encoding="utf-8")
    stop = Path(outputs["stop_script_path"]).read_text(encoding="utf-8")
    status = Path(outputs["status_script_path"]).read_text(encoding="utf-8")
    readback = Path(outputs["readback_script_path"]).read_text(encoding="utf-8")
    contract = read_json(Path(outputs["release_contract_path"]), "s19_release_contract")
    checks = {
        "start_script_contract_pass": all(token in start for token in (
            "A1FS_S19_LOCALHOST_RC_STARTED=PASS", "PORT_IN_USE", "PID_FILE_ALREADY_EXISTS",
            "build_a1fs_online_v1_s19_localhost_nonaudio_learner_product_release_candidate",
        )),
        "stop_script_contract_pass": all(token in stop for token in (
            "PID_OWNERSHIP_MISMATCH", "PORT_STILL_LISTENING", "A1FS_S19_LOCALHOST_RC_STOPPED=PASS",
        )),
        "status_script_contract_pass": all(token in status for token in (
            "PORT_OWNERSHIP_INVALID", "UNHEALTHY", "A1FS_S19_LOCALHOST_RC_STATUS=RUNNING",
        )),
        "readback_script_contract_pass": "readback --receipt" in readback and "A1FS_S19_LOCALHOST_RC_READBACK_FAILED" in readback,
        "release_contract_boundary_pass": (
            contract.get("release_candidate_id") == RELEASE_CANDIDATE_ID
            and contract.get("host") == "127.0.0.1"
            and contract.get("authentication_required") is True
            and contract.get("csrf_required_for_state_change") is True
            and contract.get("secret_values_embedded") is False
            and contract.get("external_network_binding_allowed") is False
            and contract.get("public_delivery_enabled") is False
            and contract.get("cloudflare_enabled") is False
            and contract.get("listening_enabled") is False
            and contract.get("audio_enabled") is False
            and contract.get("speaking_capture_enabled") is False
            and contract.get("a2_session_enabled") is False
        ),
    }
    if not all(checks.values()):
        raise ReleaseCandidateError("s19_operator_contract_invalid")
    return checks


def _write_checksums(release_root: Path) -> tuple[Path, dict[str, str]]:
    release_root = Path(release_root).resolve()
    checksum_path = release_root / "checksums.json"
    rows = {
        path.relative_to(release_root).as_posix(): file_digest(path)
        for path in sorted(
            (row for row in release_root.rglob("*") if row.is_file() and row != checksum_path),
            key=lambda row: row.relative_to(release_root).as_posix(),
        )
    }
    write_json(checksum_path, {
        "schema_version": "a1fs.online.v1.s19.release_checksums.v1",
        "release_candidate_id": RELEASE_CANDIDATE_ID,
        "files": rows,
        "file_count": len(rows),
        "files_sha256": digest(rows),
    })
    return checksum_path, rows


def _validate_checksums(release_root: Path, checksum_path: Path) -> dict[str, Any]:
    value = read_json(checksum_path, "s19_checksums")
    files = value.get("files")
    if not isinstance(files, Mapping) or not files:
        raise ReleaseCandidateError("s19_checksum_files_invalid")
    actual = {
        str(relative): file_digest(Path(release_root) / str(relative))
        for relative in files
    }
    if actual != dict(files) or value.get("files_sha256") != digest(dict(files)):
        raise ReleaseCandidateError("s19_checksum_mismatch")
    return value


def _candidate_smoke(
    *, production_database: Path, production_auth: Path, production_state: Path,
    bundles: Mapping[str, Mapping[str, Any]], sequence: Mapping[str, int],
    graph_path: Path, secure_static: Path, acceptance_database: Path,
    acceptance_auth: Path, acceptance_state: Path,
) -> dict[str, Any]:
    database_before = file_digest(production_database)
    auth_before = file_digest(production_auth)
    state_before = directory_digest(production_state)
    acceptance_database.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(production_database, acceptance_database)
    shutil.copy2(production_auth, acceptance_auth)
    _copy_state(production_state, acceptance_state)
    app = s18.s17._app(
        database=acceptance_database,
        bundles=bundles,
        sequence=sequence,
        graph_path=graph_path,
        state_root=acceptance_state,
    )
    config = s18.s17.s16.s15.s13.PersistentBoundaryConfig.from_values(
        username=CANARY_USERNAME,
        password=s18.s17.s16.s15.CANARY_PASSWORD,
        session_secret=s18.s17.s16.s15.CANARY_SESSION_SECRET,
        mode="local",
        allowed_origin="http://127.0.0.1",
        allowed_host="127.0.0.1",
        revocation_db_path=acceptance_auth,
        port=0,
    )
    server, thread, port = s18.s17._start_server(
        app=app, secure_static_root=secure_static, config=config,
    )
    origin = f"http://127.0.0.1:{port}"
    try:
        s18._request(port, "GET", "/api/bootstrap", expected_status=401)
        login, headers = s18._request(
            port, "POST", "/auth/login",
            {"username": CANARY_USERNAME, "password": s18.s17.s16.s15.CANARY_PASSWORD},
            origin=origin,
        )
        cookie_header = str(headers.get("Set-Cookie") or "")
        cookie = cookie_header.split(";", 1)[0]
        csrf = str(login.get("csrf_token") or "")
        if not cookie or not csrf:
            raise ReleaseCandidateError("s19_candidate_login_invalid")
        bootstrap, _ = s18._request(port, "GET", "/api/bootstrap", cookie=cookie)
        denominators = s18.s17.s16.s15.s11.s10._validate_bootstrap(bootstrap)
        progress, _ = s18._request(port, "GET", "/api/progress", cookie=cookie)
        dashboard, _ = s18._request(port, "GET", "/api/dashboard", cookie=cookie)
        review, _ = s18._request(port, "GET", "/api/human-review", cookie=cookie)
        if not isinstance(progress.get("summary"), Mapping):
            raise ReleaseCandidateError("s19_candidate_progress_invalid")
        if dashboard.get("dashboard", {}).get("role_count") != 3:
            raise ReleaseCandidateError("s19_candidate_dashboard_invalid")
        if not isinstance(review.get("review_queue"), list):
            raise ReleaseCandidateError("s19_candidate_review_queue_invalid")
    finally:
        s18.s17.s16.s15.s13._stop_server(server, thread)
    if file_digest(production_database) != database_before:
        raise ReleaseCandidateError("production_database_mutated_by_s19_smoke")
    if file_digest(production_auth) != auth_before:
        raise ReleaseCandidateError("production_auth_mutated_by_s19_smoke")
    if directory_digest(production_state) != state_before:
        raise ReleaseCandidateError("production_state_mutated_by_s19_smoke")
    return {
        **denominators,
        "scored_lesson_count": 48,
        "speaking_practice_lesson_count": 24,
        "dashboard_role_count": 3,
        "authenticated_candidate_bootstrap_pass": True,
        "authenticated_candidate_progress_pass": True,
        "authenticated_candidate_dashboard_pass": True,
        "authenticated_candidate_review_queue_pass": True,
        "candidate_smoke_server_start_count": 1,
        "production_database_unchanged": True,
        "production_state_unchanged": True,
        "production_auth_state_unchanged": True,
        "acceptance_used_isolated_database_clone": True,
        "acceptance_used_isolated_state_clone": True,
        "acceptance_used_isolated_auth_clone": True,
    }


def materialize(*, s18_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    (
        s18_receipt, production_database, production_auth, bundles, sequence,
        graph_path, production_state, source_static, source_s17, _,
    ) = _verify_s18(s18_path)
    output_root = Path(output_root).resolve()
    root = output_root / "localhost_nonaudio_release_candidate"
    if root.exists():
        shutil.rmtree(root)
    release_root = root / "release"
    secure_static = release_root / "secure_static"
    secure_static.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_static, secure_static)
    receipt_path = output_root / "localhost_nonaudio_release_candidate.private.json"
    operator = _write_operator_bundle(
        target_root=release_root / "operator",
        receipt_path=receipt_path,
        auth_state=production_auth,
    )
    operator_checks = _operator_checks(operator)
    release_manifest = {
        "schema_version": "a1fs.online.v1.s19.release_manifest.v1",
        "release_candidate_id": RELEASE_CANDIDATE_ID,
        "task_id": TASK_ID,
        "release_profile": RELEASE_PROFILE,
        "source_s18_receipt_path": str(Path(s18_path).resolve()),
        "source_s17_receipt_path": str(source_s17),
        "source_s18_sha256": digest(s18_receipt),
        "production_database_path": str(production_database),
        "production_database_sha256_at_build": file_digest(production_database),
        "production_auth_state_path": str(production_auth),
        "production_auth_state_sha256_at_build": file_digest(production_auth),
        "production_state_root": str(production_state),
        "production_state_sha256_at_build": directory_digest(production_state),
        "source_graph_path": str(graph_path),
        "source_graph_sha256": file_digest(graph_path),
        "secure_static_root": str(secure_static),
        "secure_static_sha256": directory_digest(secure_static),
        "serve_module": "ulga.builders.build_a1fs_online_v1_s19_localhost_nonaudio_learner_product_release_candidate",
        "host": "127.0.0.1",
        "port": DEFAULT_PORT,
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "scored_lesson_count": 48,
        "speaking_practice_lesson_count": 24,
        "dashboard_role_count": 3,
        "external_deployment_enabled": False,
        "public_delivery_enabled": False,
        "cloudflare_enabled": False,
        "audio_enabled": False,
        "a2_session_enabled": False,
    }
    release_manifest_path = release_root / "release_manifest.private.json"
    write_json(release_manifest_path, release_manifest, private=True)
    checksum_path, checksum_rows = _write_checksums(release_root)
    _validate_checksums(release_root, checksum_path)
    acceptance_database = root / "acceptance" / "runtime" / "s19_candidate_smoke.sqlite3"
    acceptance_auth = root / "acceptance" / "runtime" / "s19_candidate_auth.sqlite3"
    acceptance_state = root / "acceptance" / "runtime" / "canonical_learning_state"
    smoke = _candidate_smoke(
        production_database=production_database,
        production_auth=production_auth,
        production_state=production_state,
        bundles=bundles,
        sequence=sequence,
        graph_path=graph_path,
        secure_static=secure_static,
        acceptance_database=acceptance_database,
        acceptance_auth=acceptance_auth,
        acceptance_state=acceptance_state,
    )
    production_database_sha = file_digest(production_database)
    production_auth_sha = file_digest(production_auth)
    production_state_sha = directory_digest(production_state)
    summary = {
        "release_candidate_id": RELEASE_CANDIDATE_ID,
        **{key: smoke[key] for key in (
            "unit_count", "lesson_count", "asset_count", "scored_lesson_count",
            "speaking_practice_lesson_count", "dashboard_role_count",
            "authenticated_candidate_bootstrap_pass", "authenticated_candidate_progress_pass",
            "authenticated_candidate_dashboard_pass", "authenticated_candidate_review_queue_pass",
            "candidate_smoke_server_start_count", "production_database_unchanged",
            "production_state_unchanged", "production_auth_state_unchanged",
            "acceptance_used_isolated_database_clone", "acceptance_used_isolated_state_clone",
            "acceptance_used_isolated_auth_clone",
        )},
        "source_s18_e2e_acceptance_pass": True,
        "release_manifest_created": True,
        "checksum_manifest_created": True,
        "checksum_file_count": len(checksum_rows),
        "secure_static_snapshot_created": True,
        **operator_checks,
        "p0_blocker_count": 0,
        "p1_blocker_count": 0,
        "release_candidate_created": True,
        "release_candidate_externally_deployed": False,
        "role_based_identity_authorization_claimed": False,
        "a2_unlocked": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "cloudflare_enabled": False,
    }
    capability = {
        "s18_e2e_acceptance_reused": True,
        "s17_product_runtime_reused": True,
        "s17_operator_lifecycle_repackaged": True,
        "m6_scoring_review_reused": True,
        "m7_m8_canonical_learning_reused": True,
        "m9_dashboard_projection_reused": True,
        "versioned_localhost_release_candidate_created": True,
        "new_product_capability_created": False,
        "parallel_curriculum_created": False,
        "parallel_learner_state_engine_created": False,
        "parallel_scoring_engine_created": False,
        "parallel_mastery_engine_created": False,
        "parallel_dashboard_engine_created": False,
        "parallel_review_engine_created": False,
        "external_deployment_created": False,
        "public_delivery_enabled": False,
        "role_based_identity_authorization_claimed": False,
        "a2_payload_access_granted": False,
        "a2_session_start_granted": False,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "cloudflare_enabled": False,
    }
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "release_candidate_id": RELEASE_CANDIDATE_ID,
        "source_identity": {
            "s18_sha256": digest(s18_receipt),
            "production_database_sha256": production_database_sha,
            "production_auth_state_sha256": production_auth_sha,
            "production_state_sha256": production_state_sha,
            "source_graph_sha256": file_digest(graph_path),
        },
        "runtime_outputs": {
            "root": str(root),
            "release_root": str(release_root),
            "source_s18_receipt_path": str(Path(s18_path).resolve()),
            "source_s17_receipt_path": str(source_s17),
            "source_database_path": str(production_database),
            "source_auth_state_path": str(production_auth),
            "source_state_root": str(production_state),
            "source_graph_path": str(graph_path),
            "secure_static_root": str(secure_static),
            "release_manifest_path": str(release_manifest_path),
            "checksum_manifest_path": str(checksum_path),
            "acceptance_database_path": str(acceptance_database),
            "acceptance_auth_state_path": str(acceptance_auth),
            "acceptance_state_root": str(acceptance_state),
            **operator,
        },
        "release_candidate_summary": summary,
        "production_safety": {
            "production_database_sha256_before": production_database_sha,
            "production_database_sha256_after": file_digest(production_database),
            "production_auth_state_sha256_before": production_auth_sha,
            "production_auth_state_sha256_after": file_digest(production_auth),
            "production_state_sha256_before": production_state_sha,
            "production_state_sha256_after": directory_digest(production_state),
            "production_database_unchanged": True,
            "production_auth_state_unchanged": True,
            "production_state_unchanged": True,
            "acceptance_used_isolated_database_clone": True,
            "acceptance_used_isolated_state_clone": True,
            "acceptance_used_isolated_auth_clone": True,
            "learner_progress_mutated_by_acceptance": False,
            "raw_response_serialized_to_safe_artifact": False,
        },
        "capability_contract": capability,
        "product_status": PRODUCT_STATUS,
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
        "release_candidate_id": RELEASE_CANDIDATE_ID,
        "release_candidate_summary": deepcopy(summary),
        "production_safety": {
            "production_database_unchanged": True,
            "production_auth_state_unchanged": True,
            "production_state_unchanged": True,
            "acceptance_used_isolated_database_clone": True,
            "acceptance_used_isolated_state_clone": True,
            "acceptance_used_isolated_auth_clone": True,
            "learner_progress_mutated_by_acceptance": False,
            "raw_response_serialized_to_safe_artifact": False,
        },
        "capability_contract": deepcopy(capability),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def _load_receipt(receipt_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = read_json(receipt_path, "s19_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("stop_reason"),
    )
    if identity != (TASK_ID, SCHEMA_VERSION, PASS_STATUS, PRODUCT_STATUS, "NONE"):
        raise ReleaseCandidateError("s19_receipt_contract_invalid")
    body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(body):
        raise ReleaseCandidateError("s19_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs", {})
    _validate_checksums(
        Path(str(outputs.get("release_root") or "")).resolve(),
        Path(str(outputs.get("checksum_manifest_path") or "")).resolve(),
    )
    return receipt, dict(outputs)


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    if not s18.s17.s16.s15.s11._is_loopback(host):
        raise ReleaseCandidateError(f"non_loopback_host_forbidden:{host}")
    receipt, outputs = _load_receipt(receipt_path)
    source_s17 = Path(str(outputs.get("source_s17_receipt_path") or "")).resolve()
    (
        _, database, auth_state, bundles, sequence, graph_path, state_root, _,
    ) = s18.s17._load_runtime(source_s17)
    secure_static = Path(str(outputs.get("secure_static_root") or "")).resolve()
    manifest = read_json(Path(str(outputs.get("release_manifest_path") or "")), "s19_release_manifest")
    if manifest.get("release_candidate_id") != RELEASE_CANDIDATE_ID or directory_digest(secure_static) != manifest.get("secure_static_sha256"):
        raise ReleaseCandidateError("s19_release_manifest_runtime_invalid")
    config = s18.s17.s16.s15.s13.PersistentBoundaryConfig.from_environment(
        host=host, port=port, revocation_db_path=auth_state,
    )
    server = s18.s17.DashboardReviewServer(
        (host, port),
        s18.s17._app(
            database=database,
            bundles=bundles,
            sequence=sequence,
            graph_path=graph_path,
            state_root=state_root,
        ),
        secure_static,
        config,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def readback(*, receipt_path: Path) -> dict[str, Any]:
    receipt, _ = _load_receipt(receipt_path)
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "release_candidate_id": RELEASE_CANDIDATE_ID,
        "release_candidate_summary": deepcopy(receipt["release_candidate_summary"]),
        "capability_contract": deepcopy(receipt["capability_contract"]),
        "next_short_step": NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s18", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    server = commands.add_parser("serve")
    server.add_argument("--receipt", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=DEFAULT_PORT)
    snapshot = commands.add_parser("readback")
    snapshot.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            serve(receipt_path=args.receipt, host=args.host, port=args.port)
            return 0
        if args.command == "readback":
            print(json.dumps(readback(receipt_path=args.receipt), ensure_ascii=False, indent=2))
            return 0
        receipt, safe = materialize(s18_path=args.s18, output_root=args.output.parent)
        from ulga.validators.validate_a1fs_online_v1_s19_localhost_nonaudio_learner_product_release_candidate import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s18_path=args.s18,
        )
        if validation["error_count"]:
            raise ReleaseCandidateError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        ReleaseCandidateError,
        s18.E2ERecoveryError,
        s18.s17.DashboardReviewError,
        s18.s17.s16.CanonicalLearningError,
        s18.s17.s16.s15.ScoredJourneyError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
