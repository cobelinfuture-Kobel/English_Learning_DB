#!/usr/bin/env python3
"""Materialize A1FS Online V1 S16 canonical M7/M8 learner integration."""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _a1fs_online_v1_s16_canonical_learning_core as core

A1FS_CONTENT_POLICY_MODE = core.A1FS_CONTENT_POLICY_MODE
A1FS_CONTENT_POLICY_EXEMPTION = core.A1FS_CONTENT_POLICY_EXEMPTION
PROGRAM_ID = core.PROGRAM_ID
TASK_ID = core.TASK_ID
SCHEMA_VERSION = core.SCHEMA_VERSION
PASS_STATUS = core.PASS_STATUS
PRODUCT_STATUS = core.PRODUCT_STATUS
RELEASE_PROFILE = core.RELEASE_PROFILE
NEXT_SHORT_STEP = core.NEXT_SHORT_STEP
DEFAULT_PORT = core.DEFAULT_PORT
CanonicalLearningError = core.CanonicalLearningError
CanonicalLearningApplication = core.CanonicalLearningApplication
s15 = core.s15
s09 = core.s09
m7 = core.m7
m8 = core.m8
digest = core.digest
file_digest = core.file_digest
read_json = core.read_json
write_json = core.write_json
safe_scan = core.safe_scan
build_runtime_mastery_graph = core.build_runtime_mastery_graph
run_isolated_acceptance = core.run_isolated_acceptance
_app = core._app
_source = core._source


def _write_static(target_root: Path) -> None:
    target_root = Path(target_root)
    s15._write_scored_static(target_root)
    index_path = target_root / "index.html"
    index = index_path.read_text(encoding="utf-8")
    marker = '<section class="panel progress-panel">'
    panel = '''<section id="canonical-learning" class="panel canonical-panel">
      <div class="section-heading"><h2>精熟、補救與複習</h2></div>
      <p class="note">精熟依既有 M7 規則計算；補救與重新評量沿用 M7，間隔複習沿用 M8。完成一次學習不等於整個單元精熟。</p>
      <div id="canonical-summary" class="summary-grid"></div>
      <p id="canonical-state" class="note"></p>
    </section>
    <section class="panel progress-panel">'''
    if marker not in index:
        raise CanonicalLearningError("s15_progress_panel_marker_missing")
    index = index.replace(marker, panel, 1)
    index_path.write_text(index + ("" if index.endswith("\n") else "\n"), encoding="utf-8")

    css_path = target_root / "styles.css"
    css = css_path.read_text(encoding="utf-8")
    css += "\n.canonical-panel{border-width:2px}.canonical-panel .metric{min-height:84px}\n"
    css_path.write_text(css, encoding="utf-8")

    app_path = target_root / "app.js"
    app = app_path.read_text(encoding="utf-8")
    old_decl = "gateItems=document.querySelector('#gate-items');"
    new_decl = (
        "gateItems=document.querySelector('#gate-items'),"
        "canonicalSummary=document.querySelector('#canonical-summary'),"
        "canonicalState=document.querySelector('#canonical-state');"
    )
    if old_decl not in app:
        raise CanonicalLearningError("s15_gate_declaration_marker_missing")
    app = app.replace(old_decl, new_decl, 1)
    marker_load = "async function loadProgress(){const value=await api('/api/progress');renderGate(value.active_scored_journey);"
    replacement = (
        "function renderCanonical(value){canonicalSummary.replaceChildren();const state=value||{};"
        "canonicalSummary.append(metric('已精熟節點',state.mastered_required_count||0),"
        "metric('待補救',state.open_remediation_count||0),"
        "metric('待重新評量',state.pending_reassessment_count||0),"
        "metric('到期複習',Number(state.due_review_count||0)+Number(state.overdue_review_count||0)));"
        "text(canonicalState,state.evaluation_state==='EVALUATED'?"
        "`尚未精熟：${state.missing_mastery_count}；已保留：${state.retained_required_count}。A2 仍鎖定。`:"
        "'完成第一個閱讀或寫作 scored session 後，系統才會建立精熟與複習狀態。')}"
        "async function loadProgress(){const value=await api('/api/progress');renderGate(value.active_scored_journey);"
        "renderCanonical(value.canonical_learning);"
    )
    if marker_load not in app:
        raise CanonicalLearningError("s15_load_progress_marker_missing")
    app = app.replace(marker_load, replacement, 1)
    app_path.write_text(app + ("" if app.endswith("\n") else "\n"), encoding="utf-8")


def _write_launch_bundle(*, target_root: Path, receipt_path: Path, auth_state_db: Path) -> dict[str, Any]:
    target_root = Path(target_root).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    pid_file = target_root / "a1fs_s16_localhost.pid"
    stdout_log = target_root / "a1fs_s16_localhost.stdout.log"
    stderr_log = target_root / "a1fs_s16_localhost.stderr.log"
    module = "ulga.builders.build_a1fs_online_v1_s16_canonical_mastery_remediation_reassessment_review_integration"
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
for ($Attempt=1; $Attempt -le 40; $Attempt++) {{ if ($Process.HasExited) {{ throw "A1FS_S16_PROCESS_EXITED=$($Process.ExitCode)" }}; try {{ $Health=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2; if ($Health.status -eq "PASS" -and $Health.authentication_required -eq $true) {{ Write-Host "A1FS_S16_LOCALHOST_STARTED=PASS"; Write-Host "PID=$($Process.Id)"; Write-Host "URL=http://127.0.0.1:$Port"; exit 0 }} }} catch {{ Start-Sleep -Milliseconds 500 }} }}
Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
throw "A1FS_S16_LOCALHOST_READINESS_TIMEOUT"
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
if ($Command -notlike "*build_a1fs_online_v1_s16_canonical_mastery_remediation_reassessment_review_integration*") {{ throw "PID_OWNERSHIP_MISMATCH=$PidValue" }}
Stop-Process -Id $PidValue -Force
for ($Attempt=1; $Attempt -le 20; $Attempt++) {{ if (-not (Get-Process -Id $PidValue -ErrorAction SilentlyContinue)) {{ break }}; Start-Sleep -Milliseconds 250 }}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {{ throw "PORT_STILL_LISTENING=$Port" }}
Remove-Item -LiteralPath $PidFile -Force
Write-Host "A1FS_S16_LOCALHOST_STOPPED=PASS"
'''
    status = f'''param([int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PidFile = "{pid_file}"
if (-not (Test-Path -LiteralPath $PidFile)) {{ throw "A1FS_S16_LOCALHOST_STATUS=STOPPED" }}
$PidValue=[int](Get-Content -LiteralPath $PidFile -Raw)
if (-not (Get-Process -Id $PidValue -ErrorAction SilentlyContinue)) {{ throw "A1FS_S16_LOCALHOST_STATUS=STALE_PID" }}
$Listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($null -eq $Listener -or $Listener.OwningProcess -ne $PidValue) {{ throw "A1FS_S16_LOCALHOST_STATUS=PORT_OWNERSHIP_INVALID" }}
$Health=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
if ($Health.status -ne "PASS" -or $Health.authentication_required -ne $true) {{ throw "A1FS_S16_LOCALHOST_STATUS=UNHEALTHY" }}
Write-Host "A1FS_S16_LOCALHOST_STATUS=RUNNING"
Write-Host "PID=$PidValue"
Write-Host "URL=http://127.0.0.1:$Port"
'''
    for name, content in {
        "start_a1fs_s16_localhost.ps1": start,
        "stop_a1fs_s16_localhost.ps1": stop,
        "status_a1fs_s16_localhost.ps1": status,
    }.items():
        (target_root / name).write_text(content, encoding="utf-8")
    contract = {
        "schema_version": "a1fs.online.v1.s16.localhost_launch_contract.v1",
        "host": "127.0.0.1",
        "port": DEFAULT_PORT,
        "authentication_required": True,
        "required_environment_variables": [
            "A1FS_S11_AUTH_USERNAME", "A1FS_S11_AUTH_PASSWORD", "A1FS_S11_SESSION_SECRET"
        ],
        "secret_values_embedded": False,
        "auth_state_database_reused_from_s15_source": str(auth_state_db),
        "canonical_m7_mastery_enabled": True,
        "canonical_m8_review_scheduling_enabled": True,
        "external_network_binding_allowed": False,
        "cloudflare_enabled": False,
        "audio_enabled": False,
        "a2_session_enabled": False,
    }
    contract_path = target_root / "localhost_launch_contract.json"
    write_json(contract_path, contract)
    return {
        "bundle_root": str(target_root),
        "start_script_path": str(target_root / "start_a1fs_s16_localhost.ps1"),
        "stop_script_path": str(target_root / "stop_a1fs_s16_localhost.ps1"),
        "status_script_path": str(target_root / "status_a1fs_s16_localhost.ps1"),
        "launch_contract_path": str(contract_path),
        "pid_file_path": str(pid_file),
        "stdout_log_path": str(stdout_log),
        "stderr_log_path": str(stderr_log),
        "auth_state_database_path": str(auth_state_db),
    }


def materialize(*, s15_path: Path, cp01_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    (
        s15_receipt, cp01, units, production_database, auth_state, bundles, sequence,
        _, source_acceptance_database,
    ) = _source(s15_receipt_path=s15_path, cp01_path=cp01_path)
    output_root = Path(output_root).resolve()
    root = output_root / "canonical_learning_integration"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    graph = build_runtime_mastery_graph(
        cp01_artifact=cp01,
        units=units,
        database=production_database,
        sequence=sequence,
    )
    graph_path = root / "canonical_runtime_mastery_graph.private.json"
    write_json(graph_path, graph, private=True)
    learner_static = root / "learner_static"
    secure_static = root / "secure_static"
    _write_static(learner_static)
    s15.s11._write_secure_static(learner_static, secure_static)
    acceptance_database = root / "runtime" / "s16_canonical_learning_acceptance.sqlite3"
    state_root = root / "runtime" / "canonical_learning_state"
    acceptance = run_isolated_acceptance(
        source_acceptance_database=source_acceptance_database,
        production_database=production_database,
        bundles=bundles,
        sequence=sequence,
        graph_path=graph_path,
        acceptance_database=acceptance_database,
        state_root=state_root,
    )
    launch_bundle = _write_launch_bundle(
        target_root=root / "launch_bundle",
        receipt_path=output_root / "canonical_mastery_remediation_review.private.json",
        auth_state_db=auth_state,
    )
    production_sha = file_digest(production_database)
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "release_profile": RELEASE_PROFILE,
        "source_identity": {
            "s15_sha256": digest(s15_receipt),
            "cp01_sha256": digest(cp01),
            "production_database_sha256": production_sha,
        },
        "runtime_outputs": {
            "root": str(root),
            "source_s15_receipt_path": str(Path(s15_path).resolve()),
            "source_cp01_path": str(Path(cp01_path).resolve()),
            "source_database_path": str(production_database),
            "canonical_graph_path": str(graph_path),
            "acceptance_database_path": str(acceptance_database),
            "canonical_state_root": str(state_root),
            "learner_static_root": str(learner_static),
            "secure_static_root": str(secure_static),
            **launch_bundle,
        },
        "canonical_learning_summary": acceptance,
        "production_safety": {
            "production_database_sha256_before": production_sha,
            "production_database_sha256_after": file_digest(production_database),
            "production_database_unchanged": True,
            "acceptance_used_isolated_database_clone": True,
            "learner_progress_mutated_by_acceptance": False,
            "runtime_mastery_writes_only_after_real_scored_session_completion": True,
        },
        "capability_contract": {
            "s15_scored_journey_reused": True,
            "cp01_canonical_twentyfour_unit_authority_reused": True,
            "m6_response_scoring_authority_reused": True,
            "m7_mastery_engine_reused": True,
            "m7_remediation_engine_reused": True,
            "m7_reassessment_queue_reused": True,
            "m8_review_scheduling_engine_reused": True,
            "parallel_curriculum_created": False,
            "parallel_learner_state_engine_created": False,
            "parallel_scoring_engine_created": False,
            "parallel_mastery_engine_created": False,
            "dashboard_created": False,
            "mastery_write_enabled_after_scored_completion": True,
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
            "speaking_capture_enabled": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "cloudflare_enabled": False,
        },
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
        "canonical_learning_summary": deepcopy(acceptance),
        "production_safety": {
            "production_database_unchanged": True,
            "acceptance_used_isolated_database_clone": True,
            "learner_progress_mutated_by_acceptance": False,
            "runtime_mastery_writes_only_after_real_scored_session_completion": True,
        },
        "capability_contract": deepcopy(receipt_core["capability_contract"]),
        "product_status": PRODUCT_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    safe_scan(safe)
    return receipt, safe


def _load_runtime(
    receipt_path: Path,
) -> tuple[dict[str, Any], Path, Path, dict[str, dict[str, Any]], dict[str, int], Path, Path, Path]:
    receipt = read_json(receipt_path, "s16_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"), receipt.get("validation_status"),
        receipt.get("product_status"), receipt.get("stop_reason"),
    )
    if identity != (TASK_ID, SCHEMA_VERSION, PASS_STATUS, PRODUCT_STATUS, "NONE"):
        raise CanonicalLearningError("s16_receipt_contract_invalid")
    body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != digest(body):
        raise CanonicalLearningError("s16_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs", {})
    source_s15 = Path(str(outputs.get("source_s15_receipt_path") or "")).resolve()
    source_cp01 = Path(str(outputs.get("source_cp01_path") or "")).resolve()
    graph_path = Path(str(outputs.get("canonical_graph_path") or "")).resolve()
    secure_static = Path(str(outputs.get("secure_static_root") or "")).resolve()
    state_root = Path(str(outputs.get("canonical_state_root") or "")).resolve()
    (
        _, _, _, database, auth_state, bundles, sequence, _, _,
    ) = _source(s15_receipt_path=source_s15, cp01_path=source_cp01)
    if not graph_path.is_file() or not secure_static.is_dir():
        raise CanonicalLearningError("s16_runtime_outputs_missing")
    return receipt, database, auth_state, bundles, sequence, graph_path, state_root, secure_static


def serve(*, receipt_path: Path, host: str, port: int) -> None:
    _, database, auth_state, bundles, sequence, graph_path, state_root, secure_static = _load_runtime(receipt_path)
    config = s15.s13.PersistentBoundaryConfig.from_environment(
        host=host,
        port=port,
        revocation_db_path=auth_state,
    )
    server = s15.s11.SecureBoundaryServer(
        (host, port),
        _app(
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
    receipt, _, _, _, _, _, _, _ = _load_runtime(receipt_path)
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "canonical_learning_summary": deepcopy(receipt["canonical_learning_summary"]),
        "capability_contract": deepcopy(receipt["capability_contract"]),
        "next_short_step": NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s15", type=Path, required=True)
    build.add_argument("--cp01", type=Path, required=True)
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
        receipt, safe = materialize(
            s15_path=args.s15,
            cp01_path=args.cp01,
            output_root=args.output.parent,
        )
        from ulga.validators.validate_a1fs_online_v1_s16_canonical_mastery_remediation_reassessment_review_integration import validate_outputs
        validation = validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            s15_path=args.s15,
            cp01_path=args.cp01,
        )
        if validation["error_count"]:
            raise CanonicalLearningError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        CanonicalLearningError,
        s15.ScoredJourneyError,
        s15.s14.LearnerFacingSemanticsError,
        m7.MasteryError,
        m8.ReviewRetentionError,
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
