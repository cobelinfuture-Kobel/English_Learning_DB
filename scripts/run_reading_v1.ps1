param(
    [int]$SitePort = 8765,
    [int]$ApiPort = 8781
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "Reading V1 local acceptance runner" -ForegroundColor Cyan
Write-Host "Repo root: $Root"

Write-Host "Running tests..." -ForegroundColor Cyan
python -m unittest tests.site.test_reading_v1_static_site
python -m unittest tests.tools.test_r2_local
python -m unittest tests.tools.test_r2_pick

Write-Host "Starting static worksheet server on 127.0.0.1:$SitePort" -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd `"$Root`"; python -m http.server $SitePort --bind 127.0.0.1"
)

Write-Host "Starting RAZ read-only API server on 127.0.0.1:$ApiPort" -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd `"$Root`"; python tools\r2_http.py"
)

Start-Sleep -Seconds 2

$WorksheetUrl = "http://127.0.0.1:$SitePort/site/rv1/index.html"
$StatusUrl = "http://127.0.0.1:$ApiPort/api/status"
$PackUrl = "http://127.0.0.1:$ApiPort/api/pack"
$ProbeUrl = "http://127.0.0.1:$ApiPort/api/probe"

Write-Host "Open these URLs for R3 readback:" -ForegroundColor Green
Write-Host "Worksheet: $WorksheetUrl"
Write-Host "Status:    $StatusUrl"
Write-Host "Pack:      $PackUrl"
Write-Host "Probe:     $ProbeUrl"

Start-Process $WorksheetUrl
