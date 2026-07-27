#!/usr/bin/env python3
"""Static learner surface and launcher bundle for A1FS Online V1 S15."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ulga.builders import _a1fs_online_v1_s15_scored_journey_core as core

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Generates only the S15 learner UI and localhost launcher around existing runtime authorities; no learner content or answer authority is produced."
)

s14 = core.s14
ScoredJourneyError = core.ScoredJourneyError
DEFAULT_PORT = core.DEFAULT_PORT
CANARY_PASSWORD = core.CANARY_PASSWORD
CANARY_SESSION_SECRET = core.CANARY_SESSION_SECRET
write_json = core.write_json


def _write_scored_static(target_root: Path) -> None:
    target_root = Path(target_root)
    s14._write_learner_static(target_root)

    index_path = target_root / "index.html"
    index = index_path.read_text(encoding="utf-8")
    old_button = '<button id="complete" class="primary" hidden>完成本次學習</button>'
    gate_markup = '''<section id="completion-gate" class="panel gate-panel" hidden>
      <h2>本次學習完成條件</h2><p id="gate-summary"></p><div id="gate-items" class="gate-grid"></div>
    </section>
    <button id="complete" class="primary" hidden disabled>完成本次學習</button>'''
    if old_button not in index:
        raise ScoredJourneyError("s14_static_complete_button_marker_missing")
    index = index.replace(old_button, gate_markup)
    index = index.replace(
        "「本次學習已完成」只代表一個session結束，不代表整個單元完成或已精熟。",
        "閱讀與寫作必須完成全部題目，且最新作答皆通過或經人工核准，才能結束本次學習；這仍不代表整個單元完成或已精熟。",
    )
    index_path.write_text(index + ("" if index.endswith("\n") else "\n"), encoding="utf-8")

    css_path = target_root / "styles.css"
    css = css_path.read_text(encoding="utf-8")
    css += (
        "\n.gate-panel{border-width:2px}.gate-grid{display:grid;"
        "grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}"
        ".gate-item{border:1px solid #d7dee5;border-radius:10px;padding:12px}"
        ".gate-ready{border-color:#2f6f44}.gate-blocked{border-color:#9a2b2b}"
        ".attempt-note{font-size:.9rem;color:#53616e}\n"
    )
    css_path.write_text(css, encoding="utf-8")

    app_path = target_root / "app.js"
    app = app_path.read_text(encoding="utf-8")
    replacements = {
        "progressDebug=document.querySelector('#progress-debug');": (
            "progressDebug=document.querySelector('#progress-debug'),"
            "gatePanel=document.querySelector('#completion-gate'),"
            "gateSummary=document.querySelector('#gate-summary'),"
            "gateItems=document.querySelector('#gate-items');"
        ),
        "PENDING_HUMAN_REVIEW:'等待人工審核',RECORDED:'練習已記錄'": (
            "PENDING_HUMAN_REVIEW:'等待人工審核',HUMAN_APPROVE:'人工審核通過',"
            "HUMAN_REJECT:'人工審核未通過',HUMAN_DEFER:'人工審核暫緩',RECORDED:'練習已記錄'"
        ),
        "async function loadProgress(){const value=await api('/api/progress');": (
            "function gateStateLabel(value){return({NOT_ATTEMPTED:'尚未作答',PASSED:'已通過',"
            "RETRY_REQUIRED:'請再作答',PENDING_HUMAN_REVIEW:'等待人工審核'}[value]||value||'')}"
            "function renderGate(gate){gateItems.replaceChildren();if(!active||!gate){gatePanel.hidden=true;"
            "complete.disabled=true;return}gatePanel.hidden=false;if(gate.skill==='SPEAKING'){"
            "text(gateSummary,'口說是練習模式，不錄音、不評分。');complete.disabled=false;return}"
            "text(gateSummary,gate.completion_allowed?'全部最新作答已通過，可以完成本次學習。':"
            "`已通過 ${gate.passed_response_count}／${gate.required_response_count}；請完成其餘項目。`);"
            "for(const row of gate.assets){const card=document.createElement('article');"
            "card.className='gate-item '+(row.completion_state==='PASSED'?'gate-ready':'gate-blocked');"
            "const title=document.createElement('strong');text(title,`第 ${row.asset_index} 題`);"
            "const stateNode=document.createElement('p');text(stateNode,gateStateLabel(row.completion_state));"
            "const attempts=document.createElement('p');attempts.className='attempt-note';"
            "text(attempts,`作答次數：${row.attempt_count}${row.latest_outcome?'；最新：'+outcomeLabel(row.latest_outcome):''}`);"
            "card.append(title,stateNode,attempts);gateItems.append(card)}complete.disabled=!gate.completion_allowed}"
            "async function loadProgress(){const value=await api('/api/progress');renderGate(value.active_scored_journey);"
        ),
        "完成本次學習只代表session結束；評分與單元完成規則將於S15接通。": (
            "閱讀與寫作可以重試；只有每一題的最新作答通過或經人工核准，才能完成本次學習。"
        ),
        "text(result,outcomeLabel(scored.outcome));await loadProgress()": (
            "text(result,outcomeLabel(scored.outcome));renderGate(scored.completion_gate);await loadProgress()"
        ),
        "complete.hidden=false;renderLane(lane);": "complete.hidden=false;complete.disabled=true;renderLane(lane);",
        "text(status,`本次學習開始：${currentUnit.learner_label}／${lane.learner_label}`)}": (
            "text(status,`本次學習開始：${currentUnit.learner_label}／${lane.learner_label}`);await loadProgress()}"
        ),
        "complete.hidden=false;renderLane(match.lane);": "complete.hidden=false;complete.disabled=true;renderLane(match.lane);",
        "complete.hidden=true;items.replaceChildren();": (
            "complete.hidden=true;complete.disabled=true;gatePanel.hidden=true;items.replaceChildren();"
        ),
    }
    for old, new in replacements.items():
        if old not in app:
            raise ScoredJourneyError(f"s14_static_app_marker_missing:{old[:48]}")
        app = app.replace(old, new)
    app_path.write_text(app + ("" if app.endswith("\n") else "\n"), encoding="utf-8")


def _write_launch_bundle(*, target_root: Path, receipt_path: Path, auth_state_db: Path) -> dict[str, Any]:
    target_root = Path(target_root).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    pid_file = target_root / "a1fs_s15_localhost.pid"
    stdout_log = target_root / "a1fs_s15_localhost.stdout.log"
    stderr_log = target_root / "a1fs_s15_localhost.stderr.log"
    module = "ulga.builders.build_a1fs_online_v1_s15_reading_writing_scored_journey_completion_gate"
    start_script = f'''param([string]$CodeRoot = "G:\\HomeWork\\English_Learning_DB_Main",[int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Receipt = "{str(receipt_path).replace(chr(34), chr(34)+chr(34))}"
$PidFile = "{str(pid_file).replace(chr(34), chr(34)+chr(34))}"
$Stdout = "{str(stdout_log).replace(chr(34), chr(34)+chr(34))}"
$Stderr = "{str(stderr_log).replace(chr(34), chr(34)+chr(34))}"
foreach ($Name in @("A1FS_S11_AUTH_USERNAME","A1FS_S11_AUTH_PASSWORD","A1FS_S11_SESSION_SECRET")) {{ if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name))) {{ throw "MISSING_ENV=$Name" }} }}
$env:A1FS_S11_MODE = "local"
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {{ throw "PORT_IN_USE=$Port" }}
if (Test-Path -LiteralPath $PidFile) {{ throw "PID_FILE_ALREADY_EXISTS=$PidFile" }}
Set-Location $CodeRoot
$Python = (Get-Command python).Source
$Process = Start-Process -FilePath $Python -WorkingDirectory $CodeRoot -ArgumentList @("-m","{module}","serve","--receipt",$Receipt,"--host","127.0.0.1","--port",[string]$Port) -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr -PassThru
[System.IO.File]::WriteAllText($PidFile,[string]$Process.Id)
for ($Attempt=1; $Attempt -le 40; $Attempt++) {{ if ($Process.HasExited) {{ throw "A1FS_S15_PROCESS_EXITED=$($Process.ExitCode)" }}; try {{ $Health=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2; if ($Health.status -eq "PASS" -and $Health.authentication_required -eq $true) {{ Write-Host "A1FS_S15_LOCALHOST_STARTED=PASS"; Write-Host "PID=$($Process.Id)"; Write-Host "URL=http://127.0.0.1:$Port"; exit 0 }} }} catch {{ Start-Sleep -Milliseconds 500 }} }}
Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
throw "A1FS_S15_LOCALHOST_READINESS_TIMEOUT"
'''
    stop_script = f'''param([int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PidFile = "{str(pid_file).replace(chr(34), chr(34)+chr(34))}"
if (-not (Test-Path -LiteralPath $PidFile)) {{ throw "PID_FILE_MISSING=$PidFile" }}
$PidValue=[int](Get-Content -LiteralPath $PidFile -Raw)
$Process=Get-Process -Id $PidValue -ErrorAction SilentlyContinue
if ($null -eq $Process) {{ Remove-Item -LiteralPath $PidFile -Force; throw "STALE_PID_FILE=$PidValue" }}
$Command=(Get-CimInstance Win32_Process -Filter "ProcessId=$PidValue").CommandLine
if ($Command -notlike "*build_a1fs_online_v1_s15_reading_writing_scored_journey_completion_gate*") {{ throw "PID_OWNERSHIP_MISMATCH=$PidValue" }}
Stop-Process -Id $PidValue -Force
for ($Attempt=1; $Attempt -le 20; $Attempt++) {{ if (-not (Get-Process -Id $PidValue -ErrorAction SilentlyContinue)) {{ break }}; Start-Sleep -Milliseconds 250 }}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {{ throw "PORT_STILL_LISTENING=$Port" }}
Remove-Item -LiteralPath $PidFile -Force
Write-Host "A1FS_S15_LOCALHOST_STOPPED=PASS"
'''
    status_script = f'''param([int]$Port = {DEFAULT_PORT})
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PidFile = "{str(pid_file).replace(chr(34), chr(34)+chr(34))}"
if (-not (Test-Path -LiteralPath $PidFile)) {{ throw "A1FS_S15_LOCALHOST_STATUS=STOPPED" }}
$PidValue=[int](Get-Content -LiteralPath $PidFile -Raw)
if (-not (Get-Process -Id $PidValue -ErrorAction SilentlyContinue)) {{ throw "A1FS_S15_LOCALHOST_STATUS=STALE_PID" }}
$Listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($null -eq $Listener -or $Listener.OwningProcess -ne $PidValue) {{ throw "A1FS_S15_LOCALHOST_STATUS=PORT_OWNERSHIP_INVALID" }}
$Health=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
if ($Health.status -ne "PASS" -or $Health.authentication_required -ne $true) {{ throw "A1FS_S15_LOCALHOST_STATUS=UNHEALTHY" }}
Write-Host "A1FS_S15_LOCALHOST_STATUS=RUNNING"
Write-Host "PID=$PidValue"
Write-Host "URL=http://127.0.0.1:$Port"
'''
    files = {
        "start_a1fs_s15_localhost.ps1": start_script,
        "stop_a1fs_s15_localhost.ps1": stop_script,
        "status_a1fs_s15_localhost.ps1": status_script,
    }
    for name, content in files.items():
        (target_root / name).write_text(content, encoding="utf-8")
    contract = {
        "schema_version": "a1fs.online.v1.s15.localhost_launch_contract.v1",
        "host": "127.0.0.1",
        "port": DEFAULT_PORT,
        "authentication_required": True,
        "required_environment_variables": [
            "A1FS_S11_AUTH_USERNAME", "A1FS_S11_AUTH_PASSWORD", "A1FS_S11_SESSION_SECRET"
        ],
        "secret_values_embedded": False,
        "auth_state_database_reused_from_s14_source": str(auth_state_db),
        "reading_writing_completion_gate_enabled": True,
        "external_network_binding_allowed": False,
        "cloudflare_enabled": False,
        "audio_enabled": False,
    }
    write_json(target_root / "localhost_launch_contract.json", contract)
    return {
        "bundle_root": str(target_root),
        "start_script_path": str(target_root / "start_a1fs_s15_localhost.ps1"),
        "stop_script_path": str(target_root / "stop_a1fs_s15_localhost.ps1"),
        "status_script_path": str(target_root / "status_a1fs_s15_localhost.ps1"),
        "launch_contract_path": str(target_root / "localhost_launch_contract.json"),
        "pid_file_path": str(pid_file),
        "stdout_log_path": str(stdout_log),
        "stderr_log_path": str(stderr_log),
        "auth_state_database_path": str(auth_state_db),
    }
