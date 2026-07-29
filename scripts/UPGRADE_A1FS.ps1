[CmdletBinding()]
param(
  [string]$CodeRoot,
  [string]$ProductRoot,
  [string]$OutputRoot,
  [string]$JournalPath,
  [string]$TargetVersion = "latest",
  [int]$Port = 8765,
  [switch]$PlanOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($CodeRoot)) {
  $CodeRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
}
elseif (-not [System.IO.Path]::IsPathRooted($CodeRoot)) {
  $CodeRoot = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $CodeRoot))
}
else {
  $CodeRoot = [System.IO.Path]::GetFullPath($CodeRoot)
}

if (-not (Test-Path -LiteralPath (Join-Path $CodeRoot "ulga\builders") -PathType Container)) {
  throw "A1FS_CODE_ROOT_INVALID=$CodeRoot"
}

$Python = (Get-Command python -ErrorAction Stop).Source
$env:PYTHONPATH = $CodeRoot
$Command = if ($PlanOnly) { "plan" } else { "upgrade" }
$Arguments = @(
  "-m",
  "ulga.builders.build_a1fs_ops_v1_upg01_portable_resumable_universal_upgrade_orchestrator_fullfix",
  $Command,
  "--code-root", $CodeRoot,
  "--target-version", $TargetVersion,
  "--port", [string]$Port
)

foreach ($Pair in @(
  @("--product-root", $ProductRoot),
  @("--output-root", $OutputRoot),
  @("--journal-path", $JournalPath)
)) {
  if (-not [string]::IsNullOrWhiteSpace([string]$Pair[1])) {
    $Arguments += [string]$Pair[0]
    $Arguments += [string]$Pair[1]
  }
}

& $Python @Arguments
if ($LASTEXITCODE -ne 0) {
  throw "A1FS_OPS_V1_UPG01_FAILED=$LASTEXITCODE"
}

Write-Host "A1FS_OPS_V1_UPG01=PASS"
Write-Host "MODE=$Command"
Write-Host "CODE_ROOT=$CodeRoot"
Write-Host "TARGET_VERSION=$TargetVersion"
