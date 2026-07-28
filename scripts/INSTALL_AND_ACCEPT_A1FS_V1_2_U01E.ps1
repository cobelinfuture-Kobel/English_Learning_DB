param(
  [string]$CodeRoot = "G:\HomeWork\English_Learning_DB_Main",
  [string]$ProductRoot = "G:\HomeWork\A1FS_V1",
  [string]$OutputRoot = "G:\HomeWork\A1FS_V1_2_U01E_OPERATOR_RUN",
  [int]$Port = 8765,
  [string]$Candidate = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RequiredEnvironment = @(
  "A1FS_S11_AUTH_USERNAME",
  "A1FS_S11_AUTH_PASSWORD",
  "A1FS_S11_SESSION_SECRET"
)
foreach ($Name in $RequiredEnvironment) {
  $Value = [Environment]::GetEnvironmentVariable($Name)
  if ([string]::IsNullOrWhiteSpace($Value)) {
    throw "MISSING_ENV=$Name"
  }
}

if (-not (Test-Path -LiteralPath $CodeRoot -PathType Container)) {
  throw "CODE_ROOT_MISSING=$CodeRoot"
}
if (-not (Test-Path -LiteralPath $ProductRoot -PathType Container)) {
  throw "PRODUCT_ROOT_MISSING=$ProductRoot"
}
$TrimSeparators = [char[]]@(
  [IO.Path]::DirectorySeparatorChar,
  [IO.Path]::AltDirectorySeparatorChar
)
$ProductFull = [IO.Path]::GetFullPath($ProductRoot).TrimEnd($TrimSeparators)
$OutputFull = [IO.Path]::GetFullPath($OutputRoot).TrimEnd($TrimSeparators)
$ProductPrefix = $ProductFull + [IO.Path]::DirectorySeparatorChar
if (
  $OutputFull.Equals($ProductFull, [StringComparison]::OrdinalIgnoreCase) -or
  $OutputFull.StartsWith($ProductPrefix, [StringComparison]::OrdinalIgnoreCase)
) {
  throw "OUTPUT_ROOT_MUST_BE_OUTSIDE_PRODUCT_ROOT"
}

$CurrentVersionPath = Join-Path $ProductRoot "current_version.txt"
if (-not (Test-Path -LiteralPath $CurrentVersionPath -PathType Leaf)) {
  throw "CURRENT_VERSION_FILE_MISSING=$CurrentVersionPath"
}
$CurrentVersion = (Get-Content -LiteralPath $CurrentVersionPath -Raw).Trim()
if ($CurrentVersion -notin @("1.1.1", "1.2.0")) {
  throw "SOURCE_OR_TARGET_VERSION_REQUIRED=1.1.1_OR_1.2.0;ACTUAL=$CurrentVersion"
}

$env:PYTHONPATH = $CodeRoot
$Arguments = @(
  "-m",
  "ulga.builders.build_a1fs_online_v1_2_u01e_local_production_operator_acceptance",
  "install-and-accept",
  "--product-root", $ProductRoot,
  "--code-root", $CodeRoot,
  "--output-root", $OutputRoot,
  "--port", [string]$Port
)
if (-not [string]::IsNullOrWhiteSpace($Candidate)) {
  if (-not (Test-Path -LiteralPath $Candidate -PathType Container)) {
    throw "CANDIDATE_ROOT_MISSING=$Candidate"
  }
  $Arguments += @("--candidate", $Candidate)
}

& python @Arguments
if ($LASTEXITCODE -ne 0) {
  throw "A1FS_V1_2_U01E_LOCAL_INSTALL_ACCEPTANCE_FAILED=$LASTEXITCODE"
}

$InstalledVersion = (Get-Content -LiteralPath $CurrentVersionPath -Raw).Trim()
if ($InstalledVersion -ne "1.2.0") {
  throw "A1FS_V1_2_VERSION_SWITCH_FAILED=$InstalledVersion"
}

Write-Host "A1FS_V1_2_U01E_LOCAL_INSTALL_ACCEPTANCE=PASS"
Write-Host "PRODUCT_ROOT=$ProductRoot"
Write-Host "CURRENT_VERSION=$InstalledVersion"
Write-Host "READBACK=$(Join-Path $ProductRoot 'shared\operator_readbacks\a1fs_v1_2_u01e_operator_acceptance.safe.json')"
