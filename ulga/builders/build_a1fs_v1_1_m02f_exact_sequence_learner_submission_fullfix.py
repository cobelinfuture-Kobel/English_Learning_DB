#!/usr/bin/env python3
"""Package and accept the A1FS V1.1 M02 exact-sequence learner submission FullFix."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _a1fs_v1_1_m02_exact_sequence_static_adapter as adapter
from ulga.builders import _a1fs_v1_1_m02_release_core as m02_core
from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.builders import build_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as m01

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Packages a learner-transport adapter over the already-approved Unit 01 release without creating learner content, answers, scoring, state, mastery, dashboard, review, audio, A2, external routes, or parallel authority."

PROGRAM_ID = "A1FS-ONLINE-V1.1"
TASK_ID = "A1FS-ONLINE-V1.1-M02F_ExactSequenceLearnerSubmissionFullFix"
SCHEMA_VERSION = "a1fs.online.v1_1.m02f.exact_sequence_submission_fullfix.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_1_M02F_EXACT_SEQUENCE_SUBMISSION_FULLFIX"
PRODUCT_STATUS = "A1FS_V1_1_UNIT01_EXACT_SEQUENCE_SUBMISSION_FIXED"
SOURCE_VERSION = "1.1.0"
TARGET_VERSION = "1.1.1"
RELEASE_ID = "A1FS-ONLINE-V1.1-UNIT01-RC1-EXACT-SEQUENCE-FULLFIX"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1.1-M02_LocalPrivateProductInstallAndVisualReadback"


class M02FFullFixError(ValueError):
    """Fail-closed M02F release or acceptance error."""


def digest(value: Any) -> str:
    return r01.digest(value)


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    m02_core.write_json(path, value, private=private)


def source_product(product_root: Path) -> dict[str, Any]:
    root = Path(product_root).resolve()
    version, manifest, bundles, sequence = r01._load_product(root)
    if version != SOURCE_VERSION:
        raise M02FFullFixError(f"source_product_version_invalid:{version}")
    if manifest.get("product_id") != r01.PRODUCT_ID:
        raise M02FFullFixError("source_product_id_invalid")
    if len(bundles) != 72 or len(sequence) != 24:
        raise M02FFullFixError("source_product_denominator_invalid")
    rendered = json.dumps(bundles, ensure_ascii=False, sort_keys=True)
    if m01.PASSAGE not in rendered or "CONTROLLED_SEQUENCE" not in rendered:
        raise M02FFullFixError("source_m01_unit01_content_missing")
    release_root = root / "releases" / version
    app_js = release_root / "runtime/secure_static/app.js"
    if not app_js.is_file():
        raise M02FFullFixError("source_app_js_missing")
    if adapter.TARGET_RESPONSE_FOR in app_js.read_text(encoding="utf-8"):
        raise M02FFullFixError("source_release_already_contains_fullfix")
    return {
        "root": root,
        "version": version,
        "manifest": manifest,
        "bundles": bundles,
        "sequence": sequence,
        "release_root": release_root,
        "shared_identity": m02_core.shared_identity(root),
    }


def _target_manifest(source_manifest: Mapping[str, Any]) -> dict[str, Any]:
    manifest = r01._release_manifest(TARGET_VERSION)
    required = (
        "content_release_task_id",
        "approved_content_sha256",
        "modified_unit_ids",
        "modified_lesson_ids",
    )
    missing = [key for key in required if key not in source_manifest]
    if missing:
        raise M02FFullFixError(f"source_release_content_metadata_missing:{missing[0]}")
    manifest.update({
        "schema_version": SCHEMA_VERSION,
        "release_id": RELEASE_ID,
        "source_product_version": SOURCE_VERSION,
        "content_release_task_id": source_manifest["content_release_task_id"],
        "approved_content_sha256": source_manifest["approved_content_sha256"],
        "modified_unit_ids": list(source_manifest["modified_unit_ids"]),
        "modified_lesson_ids": list(source_manifest["modified_lesson_ids"]),
        "learner_state_migration_required": False,
        "shared_state_packaged_as_release_authority": False,
        "atomic_update_channel": r01.TASK_ID,
        "learner_submission_adapter": "CONTROLLED_SEQUENCE_TEXT_TO_TOKEN_LIST",
        "answer_contract_changed": False,
        "scoring_authority_changed": False,
    })
    return manifest


def build_candidate_release(*, source: Mapping[str, Any], package_root: Path) -> tuple[Path, dict[str, Any]]:
    package_root = Path(package_root).resolve()
    candidate = package_root / "release_candidate" / TARGET_VERSION
    if candidate.exists():
        shutil.rmtree(candidate)
    r01._copy_tree(Path(source["release_root"]), candidate)
    app_js = candidate / "runtime/secure_static/app.js"
    adapter_result = adapter.patch_app_js(app_js)
    version_path = candidate / "VERSION.json"
    version_data = m02_core.read_json(version_path, "m02f_version")
    version_data.update({
        "product_version": TARGET_VERSION,
        "release_id": RELEASE_ID,
        "fullfix_task_id": TASK_ID,
        "exact_sequence_submission_fixed": True,
        "immutable_release": True,
    })
    write_json(version_path, version_data)
    write_json(candidate / "release_manifest.json", _target_manifest(source["manifest"]))
    r01._write_checksums(candidate)
    manifest = r01.validate_release(candidate)
    if (
        manifest.get("product_version") != TARGET_VERSION
        or manifest.get("release_id") != RELEASE_ID
        or manifest.get("learner_submission_adapter") != "CONTROLLED_SEQUENCE_TEXT_TO_TOKEN_LIST"
    ):
        raise M02FFullFixError("candidate_manifest_invalid")
    return candidate, adapter_result


def write_installer(*, package_root: Path, candidate_root: Path) -> Path:
    package_root = Path(package_root).resolve()
    relative = candidate_root.relative_to(package_root).as_posix().replace("/", "\\")
    script = f'''param([string]$ProductRoot = (Join-Path $env:USERPROFILE "A1FS_V1"))
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Candidate = Join-Path $PackageRoot "{relative}"
$CurrentFile = Join-Path $ProductRoot "current_version.txt"
if (-not (Test-Path -LiteralPath $CurrentFile)) {{ throw "A1FS_PRODUCT_ROOT_NOT_FOUND=$ProductRoot" }}
$Current = (Get-Content -LiteralPath $CurrentFile -Raw).Trim()
if ($Current -ne "{SOURCE_VERSION}") {{ throw "SOURCE_VERSION_REQUIRED={SOURCE_VERSION};ACTUAL=$Current" }}
$PidFile = Join-Path $ProductRoot "shared\\a1fs_v1.pid"
if (Test-Path -LiteralPath $PidFile) {{
  $PidValue = [int](Get-Content -LiteralPath $PidFile -Raw)
  if (Get-Process -Id $PidValue -ErrorAction SilentlyContinue) {{ throw "STOP_A1FS_BEFORE_UPDATE_PID=$PidValue" }}
  Remove-Item -LiteralPath $PidFile -Force
}}
$CurrentApp = Join-Path $ProductRoot "releases\\$Current\\app"
$env:PYTHONPATH = $CurrentApp
& python -m {r01.MODULE} update --product-root $ProductRoot --candidate $Candidate --version {TARGET_VERSION}
if ($LASTEXITCODE -ne 0) {{ throw "A1FS_V1_1_1_UPDATE_FAILED" }}
$Installed = (Get-Content -LiteralPath $CurrentFile -Raw).Trim()
if ($Installed -ne "{TARGET_VERSION}") {{ throw "A1FS_V1_1_1_VERSION_SWITCH_FAILED=$Installed" }}
Write-Host "A1FS_V1_1_1_EXACT_SEQUENCE_FULLFIX_INSTALL=PASS"
Write-Host "PRODUCT_ROOT=$ProductRoot"
Write-Host "CURRENT_VERSION=$Installed"
'''
    path = package_root / "INSTALL_A1FS_V1_1_1_EXACT_SEQUENCE_FULLFIX.ps1"
    path.write_text(script.replace("\n", "\r\n"), encoding="ascii")
    return path


def materialize(
    *, product_root: Path, output_path: Path, report_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    product_root = Path(product_root).resolve()
    output_path = Path(output_path).resolve()
    report_path = Path(report_path).resolve()
    package_root = output_path.parent / "a1fs_v1_1_m02f_exact_sequence_fullfix"
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True)
    source = source_product(product_root)
    production_before = {
        "current_version": r01._current_version(product_root),
        "shared_identity": dict(source["shared_identity"]),
    }
    candidate, adapter_result = build_candidate_release(source=source, package_root=package_root)
    acceptance_root = m02_core.build_acceptance_root(
        product_root=product_root,
        target_root=package_root / "acceptance_product_root",
    )
    acceptance_before = m02_core.shared_identity(acceptance_root)
    installed = r01.install_candidate(
        product_root=acceptance_root,
        candidate=candidate,
        version=TARGET_VERSION,
    )
    acceptance_after = m02_core.shared_identity(acceptance_root)
    if installed.get("current_version") != TARGET_VERSION:
        raise M02FFullFixError("acceptance_version_switch_failed")
    if acceptance_before != acceptance_after:
        raise M02FFullFixError("acceptance_shared_state_changed")
    installed_app_js = acceptance_root / f"releases/{TARGET_VERSION}/runtime/secure_static/app.js"
    installed_adapter = adapter.validate_app_js(installed_app_js)
    if r01._current_version(product_root) != SOURCE_VERSION:
        raise M02FFullFixError("production_version_mutated")
    if m02_core.shared_identity(product_root) != production_before["shared_identity"]:
        raise M02FFullFixError("production_shared_state_mutated")
    installer = write_installer(package_root=package_root, candidate_root=candidate)
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "release_id": RELEASE_ID,
        "source_product_version": SOURCE_VERSION,
        "target_product_version": TARGET_VERSION,
        "source_identity": {
            "source_release_sha256": r01.directory_digest(source["release_root"]),
            "shared_identity": production_before["shared_identity"],
        },
        "runtime_outputs": {
            "package_root": str(package_root),
            "candidate_root": str(candidate),
            "acceptance_product_root": str(acceptance_root),
            "installer_path": str(installer),
            "candidate_app_js": str(candidate / "runtime/secure_static/app.js"),
        },
        "acceptance_summary": {
            "source_version": SOURCE_VERSION,
            "installed_version": TARGET_VERSION,
            "adapter": installed_adapter,
            "adapter_patch": adapter_result,
            "r01_atomic_update_pass": True,
            "shared_state_preserved": True,
            "controlled_sequence_text_serializes_to_token_list": True,
            "ordinary_text_serialization_preserved": True,
        },
        "production_safety": {
            "production_current_version_unchanged": True,
            "production_shared_state_unchanged": True,
            "learner_state_migration_required": False,
            "answer_contract_changed": False,
            "scoring_authority_changed": False,
        },
        "boundaries": {
            "unit02_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "external_binding_enabled": False,
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
        "product_status": PRODUCT_STATUS,
        "release_id": RELEASE_ID,
        "source_product_version": SOURCE_VERSION,
        "target_product_version": TARGET_VERSION,
        "acceptance_summary": receipt_core["acceptance_summary"],
        "production_safety": receipt_core["production_safety"],
        "boundaries": receipt_core["boundaries"],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    write_json(output_path, receipt, private=True)
    write_json(report_path, safe)
    return receipt, safe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_subparsers(dest="command", required=True)
    build = command.add_parser("materialize")
    build.add_argument("--product-root", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt, safe = materialize(
            product_root=args.product_root,
            output_path=args.output,
            report_path=args.report,
        )
        from ulga.validators import validate_a1fs_v1_1_m02f_exact_sequence_learner_submission_fullfix as validator
        validation = validator.validate_outputs(
            receipt=receipt,
            safe_report=safe,
            product_root=args.product_root,
            output_root=args.output.parent,
        )
        if validation["error_count"]:
            raise M02FFullFixError("validation_failed:" + "|".join(validation["errors"]))
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        M02FFullFixError,
        adapter.ExactSequenceStaticAdapterError,
        m02_core.ReleaseCoreError,
        r01.ProductRootError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
