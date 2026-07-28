#!/usr/bin/env python3
"""Install A1FS V1.2 from its candidate app and produce a read-only operator readback.

This task consumes the already-approved U01E S05 candidate. It does not create
learner content, attempts, scores, mastery, audio, A2 state, or a parallel
runtime. The generated PowerShell entry point installs through the existing R01
atomic channel, starts the loopback-only V1.2 runtime, and verifies the installed
product without writing learner state.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s05_release_migration_acceptance as s05,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Orchestrates the already-approved S05 candidate through the existing R01 "
    "atomic installer and performs read-only product, database, and loopback "
    "health verification. It creates no content, answer, learner attempt, score, "
    "mastery decision, audio, A2 unlock, external route, or parallel authority."
)

PROGRAM_ID = s05.PROGRAM_ID
TASK_ID = (
    "A1FS-ONLINE-V1.2-U01E_"
    "LocalProductionInstallAndOperatorAcceptance"
)
SCHEMA_VERSION = "a1fs.online.v1_2.u01e.local_operator_acceptance.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_U01E_LOCAL_OPERATOR_ACCEPTANCE"
MODULE = (
    "ulga.builders."
    "build_a1fs_online_v1_2_u01e_local_production_install_operator_acceptance"
)
EXPECTED_TARGET_VERSION = s05.TARGET_VERSION
EXPECTED_UNIT_COUNT = s05.EXPECTED_UNIT_COUNT
EXPECTED_LESSON_COUNT = s05.EXPECTED_LESSON_COUNT
EXPECTED_ASSET_COUNT = s05.EXPECTED_TARGET_ASSET_COUNT
EXPECTED_UNIT01_COUNTS = dict(s05.EXPECTED_UNIT01_COUNTS)
EXPECTED_UNIT01_ACTIVITY_COUNT = s05.s04.EXPECTED_TOTAL_COUNT
EXPECTED_NEW_ACTIVITY_COUNT = s05.s04.EXPECTED_NEW_COUNT


class LocalOperatorAcceptanceError(ValueError):
    """Fail-closed local install or operator readback error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return s05.r01.digest(value)


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, target)


def _asset_count(bundles: Mapping[str, Mapping[str, Any]]) -> int:
    return sum(len(bundle.get("assets", [])) for bundle in bundles.values())


def _unit01_counts(bundles: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    return {
        skill: len(bundles[s05.m01.LESSON_IDS[skill]].get("assets", []))
        for skill in EXPECTED_UNIT01_COUNTS
    }


def _database_readback(database: Path) -> dict[str, Any]:
    before = s05.s04.file_digest(database)
    uri = f"file:{Path(database).resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        names = s05.s04.table_names(connection)
        missing = sorted(s05.s04.ADDITIVE_TABLES - names)
        if missing:
            raise LocalOperatorAcceptanceError(
                "missing_additive_tables:" + ",".join(missing)
            )
        binding_count = int(
            connection.execute("SELECT COUNT(*) FROM u01e_asset_target_bindings").fetchone()[0]
        )
        denominator_count = int(
            connection.execute("SELECT COUNT(*) FROM u01e_coverage_denominators").fetchone()[0]
        )
        snapshot_count = int(
            connection.execute("SELECT COUNT(*) FROM u01e_learner_coverage_snapshots").fetchone()[0]
        )
        placeholders = ",".join("?" for _ in s05.m01.LESSON_IDS)
        lesson_ids = tuple(s05.m01.LESSON_IDS.values())
        unit01_contract_count = int(
            connection.execute(
                f"SELECT COUNT(*) FROM response_contracts WHERE lesson_id IN ({placeholders})",
                lesson_ids,
            ).fetchone()[0]
        )
        new_contract_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM response_contracts WHERE asset_key LIKE 'U01E-S03-%'"
            ).fetchone()[0]
        )
        attempt_count = int(
            connection.execute("SELECT COUNT(*) FROM response_attempts").fetchone()[0]
        )
    after = s05.s04.file_digest(database)
    if before != after:
        raise LocalOperatorAcceptanceError("operator_readback_mutated_database")
    if binding_count != EXPECTED_UNIT01_ACTIVITY_COUNT:
        raise LocalOperatorAcceptanceError(
            f"target_binding_count_invalid:{binding_count}"
        )
    if unit01_contract_count != EXPECTED_UNIT01_ACTIVITY_COUNT:
        raise LocalOperatorAcceptanceError(
            f"unit01_contract_count_invalid:{unit01_contract_count}"
        )
    if new_contract_count != EXPECTED_NEW_ACTIVITY_COUNT:
        raise LocalOperatorAcceptanceError(
            f"new_contract_count_invalid:{new_contract_count}"
        )
    if denominator_count <= 0:
        raise LocalOperatorAcceptanceError("coverage_denominator_rows_missing")
    return {
        "read_only_probe": True,
        "database_sha256_preserved": True,
        "additive_tables": sorted(s05.s04.ADDITIVE_TABLES),
        "coverage_denominator_row_count": denominator_count,
        "asset_target_binding_count": binding_count,
        "learner_coverage_snapshot_count": snapshot_count,
        "unit01_response_contract_count": unit01_contract_count,
        "new_response_contract_count": new_contract_count,
        "existing_attempt_count_preserved": attempt_count,
    }


def operator_acceptance(
    *,
    product_root: Path,
    port: int,
    require_running: bool = True,
) -> dict[str, Any]:
    root = Path(product_root).resolve()
    (
        _,
        manifest,
        bundles,
        sequence,
        database,
        auth,
        state,
        graph,
        static,
        registry,
    ) = s05._load_v12(root)
    version = s05.r01._current_version(root)
    release = root / "releases" / version
    s05.r01.validate_release(release)

    unit_count = len(sequence)
    lesson_count = len(bundles)
    asset_count = _asset_count(bundles)
    unit01_counts = _unit01_counts(bundles)
    unit01_activity_count = sum(unit01_counts.values())
    registry_count = len(registry)
    if version != EXPECTED_TARGET_VERSION:
        raise LocalOperatorAcceptanceError(f"installed_version_invalid:{version}")
    if unit_count != EXPECTED_UNIT_COUNT:
        raise LocalOperatorAcceptanceError(f"unit_count_invalid:{unit_count}")
    if lesson_count != EXPECTED_LESSON_COUNT:
        raise LocalOperatorAcceptanceError(f"lesson_count_invalid:{lesson_count}")
    if asset_count != EXPECTED_ASSET_COUNT:
        raise LocalOperatorAcceptanceError(f"asset_count_invalid:{asset_count}")
    if int(manifest.get("asset_count") or -1) != EXPECTED_ASSET_COUNT:
        raise LocalOperatorAcceptanceError("manifest_asset_count_invalid")
    if unit01_counts != EXPECTED_UNIT01_COUNTS:
        raise LocalOperatorAcceptanceError(
            f"unit01_counts_invalid:{unit01_counts}"
        )
    if unit01_activity_count != EXPECTED_UNIT01_ACTIVITY_COUNT:
        raise LocalOperatorAcceptanceError(
            f"unit01_activity_count_invalid:{unit01_activity_count}"
        )
    if registry_count != EXPECTED_UNIT01_ACTIVITY_COUNT:
        raise LocalOperatorAcceptanceError(
            f"target_registry_count_invalid:{registry_count}"
        )
    for required in (database, auth, state, graph, static / "index.html", static / "app.js"):
        if not Path(required).exists():
            raise LocalOperatorAcceptanceError(f"runtime_path_missing:{required}")

    database_readback = _database_readback(database)
    running = bool(s05._health(port))
    pid_path = root / "shared/a1fs_v1.pid"
    pid: int | None = None
    process_alive = False
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text(encoding="ascii").strip())
            process_alive = bool(s05.r01._pid_alive(pid))
        except (OSError, ValueError):
            process_alive = False
    if require_running and not (running and process_alive):
        raise LocalOperatorAcceptanceError(
            f"runtime_not_ready:health={running};process_alive={process_alive}"
        )

    core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_root": str(root),
        "installed_version": version,
        "release_id": str(manifest.get("release_id") or s05.RELEASE_ID),
        "release_summary": {
            "unit_count": unit_count,
            "lesson_count": lesson_count,
            "asset_count": asset_count,
            "unit01_activity_count": unit01_activity_count,
            "unit01_counts": unit01_counts,
            "context_count": 5,
            "question_type_count": s05.s04.EXPECTED_ASSESSMENT_PATTERN_COUNT,
        },
        "database_readback": database_readback,
        "runtime_readback": {
            "require_running": require_running,
            "loopback_health_pass": running,
            "pid": pid,
            "process_alive": process_alive,
            "url": f"http://127.0.0.1:{port}",
            "authentication_required": True,
        },
        "operator_boundaries": {
            "learner_state_written": False,
            "attempt_created": False,
            "score_created": False,
            "mastery_inferred": False,
            "runtime_free_generation_allowed": False,
            "unit02_modified": False,
            "listening_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "external_binding_enabled": False,
        },
        "manual_operator_checks": [
            "Open the loopback URL and sign in with an existing local account.",
            "Confirm Unit 01 shows 24 activities: Reading 10, Writing 8, Speaking practice 6.",
            "Confirm the coverage readback page loads and does not count unattempted targets as PRACTISED.",
            "Do not unlock Unit 02, audio, Speaking capture, or A2 during this acceptance.",
        ],
        "stop_reason": "LOCAL_MANUAL_UI_CONFIRMATION_PENDING",
    }
    return {**core, "readback_sha256": digest(core)}


def _powershell_path(value: Path) -> str:
    return str(Path(value).resolve()).replace("'", "''")


def write_operator_scripts(
    *, package_root: Path, candidate: Path, default_port: int | None = None,
) -> dict[str, str]:
    package = Path(package_root).resolve()
    candidate_root = Path(candidate).resolve()
    package.mkdir(parents=True, exist_ok=True)
    port = int(default_port or s05.r01.DEFAULT_PORT)
    relative = candidate_root.relative_to(package).as_posix().replace("/", "\\")

    install = package / "INSTALL_A1FS_V1_2_U01E.ps1"
    install_text = f'''param([string]$ProductRoot = (Join-Path $env:USERPROFILE "A1FS_V1"))
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Candidate = Join-Path $PackageRoot "{relative}"
$CandidateApp = Join-Path $Candidate "app"
$Current = (Get-Content -LiteralPath (Join-Path $ProductRoot "current_version.txt") -Raw).Trim()
if ($Current -ne "{s05.SOURCE_VERSION}") {{ throw "SOURCE_VERSION_REQUIRED={s05.SOURCE_VERSION};ACTUAL=$Current" }}
$PidFile = Join-Path $ProductRoot "shared\\a1fs_v1.pid"
if (Test-Path -LiteralPath $PidFile) {{
  $PidValue = [int](Get-Content -LiteralPath $PidFile -Raw)
  if (Get-Process -Id $PidValue -ErrorAction SilentlyContinue) {{ throw "STOP_A1FS_BEFORE_UPDATE_PID=$PidValue" }}
  Remove-Item -LiteralPath $PidFile -Force
}}
$env:PYTHONPATH = $CandidateApp
& python -m {MODULE} install --product-root $ProductRoot --candidate $Candidate
if ($LASTEXITCODE -ne 0) {{ throw "A1FS_V1_2_UPDATE_FAILED" }}
$Installed = (Get-Content -LiteralPath (Join-Path $ProductRoot "current_version.txt") -Raw).Trim()
if ($Installed -ne "{s05.TARGET_VERSION}") {{ throw "A1FS_V1_2_VERSION_SWITCH_FAILED=$Installed" }}
Write-Host "A1FS_V1_2_U01E_INSTALL=PASS"
Write-Host "PRODUCT_ROOT=$ProductRoot"
Write-Host "CURRENT_VERSION=$Installed"
'''
    install.write_text(install_text.replace("\n", "\r\n"), encoding="ascii")

    combined = package / "INSTALL_START_ACCEPT_A1FS_V1_2_U01E.ps1"
    combined_text = f'''param(
  [string]$ProductRoot = (Join-Path $env:USERPROFILE "A1FS_V1"),
  [int]$Port = {port},
  [string]$Output = (Join-Path $env:USERPROFILE "A1FS_V1\\shared\\operator_acceptance_v1_2_u01e.json")
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $PackageRoot "INSTALL_A1FS_V1_2_U01E.ps1") -ProductRoot $ProductRoot
$InstalledApp = Join-Path $ProductRoot "releases\\{s05.TARGET_VERSION}\\app"
$env:PYTHONPATH = $InstalledApp
& python -m {MODULE} start --product-root $ProductRoot --port $Port
if ($LASTEXITCODE -ne 0) {{ throw "A1FS_V1_2_START_FAILED" }}
& python -m {MODULE} operator-accept --product-root $ProductRoot --port $Port --require-running --output $Output
if ($LASTEXITCODE -ne 0) {{ throw "A1FS_V1_2_OPERATOR_ACCEPTANCE_FAILED" }}
Write-Host "A1FS_V1_2_U01E_OPERATOR_ACCEPTANCE=PASS"
Write-Host "READBACK=$Output"
Write-Host "OPEN=http://127.0.0.1:$Port"
Start-Process "http://127.0.0.1:$Port"
'''
    combined.write_text(combined_text.replace("\n", "\r\n"), encoding="ascii")
    return {
        "install_script": str(install),
        "install_start_accept_script": str(combined),
    }


def materialize(
    *, product_root: Path, code_root: Path, output_path: Path, report_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    receipt, safe = s05.materialize(
        product_root=product_root,
        code_root=code_root,
        output_path=output_path,
        report_path=report_path,
    )
    scripts = write_operator_scripts(
        package_root=Path(receipt["runtime_outputs"]["package_root"]),
        candidate=Path(receipt["runtime_outputs"]["candidate_root"]),
    )
    return receipt, safe, scripts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("materialize")
    build.add_argument("--product-root", type=Path, required=True)
    build.add_argument("--code-root", type=Path, default=Path(__file__).resolve().parents[2])
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)

    install = commands.add_parser("install")
    install.add_argument("--product-root", type=Path, required=True)
    install.add_argument("--candidate", type=Path, required=True)

    start = commands.add_parser("start")
    start.add_argument("--product-root", type=Path, required=True)
    start.add_argument("--port", type=int, default=s05.r01.DEFAULT_PORT)

    serve = commands.add_parser("serve")
    serve.add_argument("--product-root", type=Path, required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=s05.r01.DEFAULT_PORT)

    accept = commands.add_parser("operator-accept")
    accept.add_argument("--product-root", type=Path, required=True)
    accept.add_argument("--port", type=int, default=s05.r01.DEFAULT_PORT)
    accept.add_argument("--require-running", action="store_true")
    accept.add_argument("--output", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "materialize":
            receipt, safe, scripts = materialize(
                product_root=args.product_root,
                code_root=args.code_root,
                output_path=args.output,
                report_path=args.report,
            )
            print(json.dumps({"safe": safe, "operator_scripts": scripts}, ensure_ascii=False, indent=2))
        elif args.command == "install":
            source = s05.source_product(args.product_root)
            overlay = s05.build_runtime_overlay(source)
            result = s05.install_with_migration(
                product_root=args.product_root,
                candidate=args.candidate,
                overlay=overlay,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "start":
            print(json.dumps(s05.start(product_root=args.product_root, port=args.port), ensure_ascii=False, indent=2))
        elif args.command == "serve":
            s05.serve(product_root=args.product_root, host=args.host, port=args.port)
        else:
            readback = operator_acceptance(
                product_root=args.product_root,
                port=args.port,
                require_running=args.require_running,
            )
            if args.output:
                write_json(args.output, readback)
            print(json.dumps(readback, ensure_ascii=False, indent=2))
        return 0
    except (
        LocalOperatorAcceptanceError,
        s05.S05ReleaseError,
        s05.static_adapter.S05StaticError,
        s05.s03.S03ItemBankError,
        s05.s04.S04CoverageError,
        s05.r01.ProductRootError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
