param(
  [string]$CodeRoot = "G:\HomeWork\English_Learning_DB_Main",
  [string]$ProductRoot = "G:\HomeWork\A1FS_V1",
  [string]$OutputRoot = "G:\HomeWork\A1FS_V1_2_1_U01F_OPERATOR_RUN",
  [int]$Port = 8765
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

foreach ($Path in @($CodeRoot, $ProductRoot)) {
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "REQUIRED_ROOT_MISSING=$Path"
  }
}

foreach ($Name in @(
  "A1FS_S11_AUTH_USERNAME",
  "A1FS_S11_AUTH_PASSWORD",
  "A1FS_S11_SESSION_SECRET"
)) {
  $Value = [Environment]::GetEnvironmentVariable($Name, "Process")
  if ([string]::IsNullOrWhiteSpace($Value)) {
    throw "MISSING_PROCESS_ENV=$Name"
  }
}

$VersionPath = Join-Path $ProductRoot "current_version.txt"
$CurrentVersion = ([System.IO.File]::ReadAllText($VersionPath)).Trim()
if ($CurrentVersion -notin @("1.2.0", "1.2.1")) {
  throw "SOURCE_OR_TARGET_VERSION_REQUIRED=1.2.0_OR_1.2.1;ACTUAL=$CurrentVersion"
}

$ResolvedProduct = [System.IO.Path]::GetFullPath($ProductRoot).TrimEnd('\')
$ResolvedOutput = [System.IO.Path]::GetFullPath($OutputRoot).TrimEnd('\')
if ($ResolvedOutput.StartsWith($ResolvedProduct + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "OUTPUT_ROOT_MUST_BE_OUTSIDE_PRODUCT_ROOT=$ResolvedOutput"
}

Set-Location $CodeRoot
$Python = (Get-Command python -ErrorAction Stop).Source
& $Python -m ulga.builders.build_a1fs_online_v1_2_1_u01f_patch_release `
  install-and-accept `
  --product-root $ProductRoot `
  --code-root $CodeRoot `
  --output-root $OutputRoot `
  --port $Port

if ($LASTEXITCODE -ne 0) {
  throw "A1FS_V1_2_1_U01F_LOCAL_INSTALL_ACCEPTANCE_FAILED=$LASTEXITCODE"
}

$InstalledVersion = ([System.IO.File]::ReadAllText($VersionPath)).Trim()
if ($InstalledVersion -ne "1.2.1") {
  throw "A1FS_V1_2_1_U01F_VERSION_NOT_INSTALLED=$InstalledVersion"
}

$Readback = Join-Path $ProductRoot `
  "shared\operator_readbacks\a1fs_v1_2_1_u01f_operator_acceptance.safe.json"
if (-not (Test-Path -LiteralPath $Readback)) {
  throw "A1FS_V1_2_1_U01F_READBACK_MISSING=$Readback"
}

Write-Host "A1FS_V1_2_1_U01F_LOCAL_INSTALL_ACCEPTANCE=PASS"
Write-Host "PRODUCT_ROOT=$ProductRoot"
Write-Host "SOURCE_VERSION=$CurrentVersion"
Write-Host "CURRENT_VERSION=$InstalledVersion"
Write-Host "READBACK=$Readback"
