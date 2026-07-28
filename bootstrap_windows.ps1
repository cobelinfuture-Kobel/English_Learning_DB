[CmdletBinding()]
param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvRoot = Join-Path $RepoRoot ".venv"
$VenvPython = Join-Path $VenvRoot "Scripts\python.exe"
$Requirements = Join-Path $RepoRoot "requirements.txt"
$TestTempRoot = Join-Path $env:USERPROFILE "English_Learning_DB_TestTemp"

Set-Location $RepoRoot

if (-not (Test-Path -LiteralPath $Requirements)) {
    throw "REQUIREMENTS_FILE_MISSING=$Requirements"
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    & py -3.11 -c "import struct,sys; raise SystemExit(0 if sys.version_info[:2] == (3,11) and struct.calcsize('P')*8 == 64 else 1)"
    if ($LASTEXITCODE -ne 0) {
        throw "PYTHON_311_64BIT_REQUIRED"
    }

    & py -3.11 -m venv $VenvRoot
    if ($LASTEXITCODE -ne 0) {
        throw "VENV_CREATION_FAILED"
    }
}

& $VenvPython -c "import struct,sys; print('python =',sys.executable); print('version =',sys.version.split()[0]); print('bits =',struct.calcsize('P')*8); raise SystemExit(0 if sys.version_info[:2] == (3,11) and struct.calcsize('P')*8 == 64 else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "VENV_PYTHON_IDENTITY_INVALID"
}

& $VenvPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw "PIP_BOOTSTRAP_FAILED"
}

& $VenvPython -m pip install -r $Requirements
if ($LASTEXITCODE -ne 0) {
    throw "PROJECT_DEPENDENCY_INSTALL_FAILED"
}

& $VenvPython -m pip install pytest jsonschema
if ($LASTEXITCODE -ne 0) {
    throw "TEST_DEPENDENCY_INSTALL_FAILED"
}

& $VenvPython -m pip check
if ($LASTEXITCODE -ne 0) {
    throw "PIP_DEPENDENCY_CHECK_FAILED"
}

New-Item -ItemType Directory -Path $TestTempRoot -Force | Out-Null
$env:TEMP = $TestTempRoot
$env:TMP = $TestTempRoot

if (-not $SkipTests) {
    $BaseTemp = Join-Path $TestTempRoot "pytest-bootstrap"
    if (Test-Path -LiteralPath $BaseTemp) {
        Remove-Item -LiteralPath $BaseTemp -Recurse -Force
    }

    $FocusedTests = @(
        "tests/ci/test_a1fs_online_v1_r01_windows_sqlite_lifecycle.py",
        "tests/ci/test_a1fs_online_v1_r01_self_contained_product_root_update_channel.py",
        "tests/ci/test_a1fs_online_v1_r01_manifest_authority.py",
        "tests/ci/test_a1fs_artifact_authority_v1_s00.py"
    )

    & $VenvPython -m pytest -q --basetemp $BaseTemp @FocusedTests
    if ($LASTEXITCODE -ne 0) {
        throw "WINDOWS_FOCUSED_REGRESSION_FAILED"
    }
}

Write-Host ""
Write-Host "WINDOWS_BOOTSTRAP=PASS"
Write-Host "REPOSITORY=$RepoRoot"
Write-Host "PYTHON=$VenvPython"
Write-Host "TEMP=$TestTempRoot"
if ($SkipTests) {
    Write-Host "FOCUSED_TESTS=SKIPPED"
} else {
    Write-Host "FOCUSED_TESTS=PASS"
}
