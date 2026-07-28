#!/usr/bin/env python3
"""Release packaging helpers for A1FS V1.1 M02."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.builders import build_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as m01

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Packages already-approved M01 content through the existing R01 local release/update authority; it creates no learner content, answer, scoring, mastery, dashboard, state, audio, A2, external route, or parallel authority."

SOURCE_VERSION = "1.0.0"
TARGET_VERSION = "1.1.0"
RELEASE_ID = "A1FS-ONLINE-V1.1-UNIT01-RC1"


class ReleaseCoreError(ValueError):
    """Fail-closed release packaging or identity error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return r01.digest(value)


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseCoreError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseCoreError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def shared_identity(product_root: Path) -> dict[str, str]:
    root = Path(product_root).resolve()
    database = root / "shared/database/learner_runtime.sqlite3"
    auth = root / "shared/auth/auth_state.sqlite3"
    state = root / "shared/learner_state/canonical_learning_state"
    if not database.is_file() or not auth.is_file() or not state.is_dir():
        raise ReleaseCoreError("product_shared_authority_missing")
    return {
        "database_sha256": r01.file_digest(database),
        "auth_state_sha256": r01.file_digest(auth),
        "learner_state_sha256": r01.directory_digest(state),
    }


def response_contract_identity(database: Path, lesson_ids: list[str]) -> str:
    placeholders = ",".join("?" for _ in lesson_ids)
    query = (
        "SELECT lesson_id,asset_key,role,capture_enabled,contract_json,contract_digest "
        f"FROM response_contracts WHERE lesson_id IN ({placeholders}) ORDER BY lesson_id,asset_key"
    )
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute(query, tuple(lesson_ids)).fetchall()]
    if len(rows) != 11:
        raise ReleaseCoreError("unit01_response_contract_denominator_invalid")
    return digest(rows)


def asset_identity(bundle: Mapping[str, Any]) -> list[tuple[str, str]]:
    assets = bundle.get("assets")
    if not isinstance(assets, list):
        raise ReleaseCoreError("bundle_assets_invalid")
    result: list[tuple[str, str]] = []
    for asset in assets:
        if not isinstance(asset, Mapping):
            raise ReleaseCoreError("bundle_asset_not_object")
        key = str(asset.get("asset_key") or "")
        role = str(asset.get("role") or "")
        if not key or not role:
            raise ReleaseCoreError("bundle_asset_identity_missing")
        result.append((key, role))
    return result


def validate_overlay(
    *, source_bundles: Mapping[str, Any], target_bundles: Mapping[str, Any],
) -> dict[str, Any]:
    if set(source_bundles) != set(target_bundles) or len(source_bundles) != 72:
        raise ReleaseCoreError("release_bundle_identity_set_changed")
    changed: list[str] = []
    total_assets = 0
    for lesson_id in sorted(source_bundles):
        source = source_bundles[lesson_id]
        target = target_bundles[lesson_id]
        if not isinstance(source, Mapping) or not isinstance(target, Mapping):
            raise ReleaseCoreError(f"release_bundle_not_object:{lesson_id}")
        if asset_identity(source) != asset_identity(target):
            raise ReleaseCoreError(f"release_asset_identity_changed:{lesson_id}")
        total_assets += len(asset_identity(target))
        if canonical(source) != canonical(target):
            changed.append(lesson_id)
    if set(changed) != set(m01.LESSON_IDS.values()):
        raise ReleaseCoreError("release_changed_lesson_set_invalid")
    if total_assets != 264:
        raise ReleaseCoreError("release_asset_denominator_invalid")
    for skill, lesson_id in m01.LESSON_IDS.items():
        assets = target_bundles[lesson_id].get("assets")
        if not isinstance(assets, list) or len(assets) != m01.EXPECTED_LANE_COUNTS[skill]:
            raise ReleaseCoreError(f"release_unit01_lane_count_invalid:{skill}")
        for asset in assets:
            learner = asset.get("learner_payload") if isinstance(asset, Mapping) else None
            if not isinstance(learner, Mapping):
                raise ReleaseCoreError(f"release_learner_payload_missing:{lesson_id}")
            stimulus = learner.get("stimulus")
            if not isinstance(stimulus, Mapping) or stimulus.get("body") != m01.PASSAGE:
                raise ReleaseCoreError(f"release_unit01_passage_missing:{lesson_id}")
            if skill == "SPEAKING" and (
                learner.get("response_capture_enabled") is not False
                or learner.get("recording_capture_required") is not False
                or not str(learner.get("sentence_frame") or "").strip()
                or not str(learner.get("model_language") or "").strip()
            ):
                raise ReleaseCoreError("release_speaking_practice_boundary_invalid")
    return {
        "changed_lesson_ids": changed,
        "modified_lesson_count": 3,
        "preserved_lesson_count": 69,
        "asset_count": total_assets,
        "reading_activity_count": 4,
        "writing_activity_count": 4,
        "speaking_practice_count": 3,
    }


def source_product(product_root: Path) -> dict[str, Any]:
    root = Path(product_root).resolve()
    version, manifest, bundles, sequence = r01._load_product(root)
    if version != SOURCE_VERSION:
        raise ReleaseCoreError(f"source_product_version_invalid:{version}")
    if manifest.get("product_id") != r01.PRODUCT_ID:
        raise ReleaseCoreError("source_product_id_invalid")
    if len(bundles) != 72 or len(sequence) != 24:
        raise ReleaseCoreError("source_product_denominator_invalid")
    database = r01._resolve(root, str(manifest["shared_database_path"]))
    static = r01._resolve(root, str(manifest["secure_static_root"]))
    graph = r01._resolve(root, str(manifest["graph_path"]))
    if not database.is_file() or not static.is_dir() or not graph.is_file():
        raise ReleaseCoreError("source_product_runtime_missing")
    return {
        "root": root,
        "version": version,
        "manifest": manifest,
        "bundles": bundles,
        "sequence": sequence,
        "database": database,
        "static": static,
        "graph": graph,
        "shared_identity": shared_identity(root),
        "unit01_contract_sha256": response_contract_identity(database, list(m01.LESSON_IDS.values())),
    }


def build_m01_overlay(source: Mapping[str, Any], work_root: Path) -> dict[str, Any]:
    source_bindings = {
        "r01_product_id": r01.PRODUCT_ID,
        "source_product_version": SOURCE_VERSION,
        "source_release_manifest_sha256": digest(source["manifest"]),
        "source_bundle_sha256": digest(source["bundles"]),
        "source_unit01_response_contract_sha256": source["unit01_contract_sha256"],
        "operator_decision_ref": m01.DECISION_REF,
    }
    candidate = m01.build_candidate(source_bindings)
    approved = m01.admit_candidate(candidate)
    projections = m01.build_projections(approved)
    contracts = m01._contracts_for_lessons(source["database"], list(m01.LESSON_IDS.values()))
    bundles = m01.overlay_bundles(
        bundles=source["bundles"],
        approved=approved,
        contracts=contracts,
    )
    overlay = validate_overlay(source_bundles=source["bundles"], target_bundles=bundles)
    root = Path(work_root).resolve() / "m01_materialization"
    if root.exists():
        shutil.rmtree(root)
    content = root / "content"
    runtime = root / "runtime"
    content.mkdir(parents=True)
    runtime.mkdir(parents=True)
    write_json(content / "unit01.candidate.private.json", candidate, private=True)
    write_json(content / "unit01.approved.private.json", approved, private=True)
    write_json(content / "unit01.projections.private.json", projections, private=True)
    write_json(runtime / "bundles.private.json", bundles, private=True)
    static = runtime / "secure_static"
    m01.patch_static(source["static"], static)
    return {
        "root": root,
        "candidate": candidate,
        "approved": approved,
        "projections": projections,
        "bundles": bundles,
        "bundles_path": runtime / "bundles.private.json",
        "static": static,
        "overlay": overlay,
    }


def release_manifest(*, m01_approved: Mapping[str, Any]) -> dict[str, Any]:
    manifest = r01._release_manifest(TARGET_VERSION)
    manifest.update({
        "schema_version": "a1fs.online.v1_1.m02.release_manifest.v1",
        "release_id": RELEASE_ID,
        "source_product_version": SOURCE_VERSION,
        "content_release_task_id": m01.TASK_ID,
        "approved_content_sha256": m01_approved["artifact_sha256"],
        "modified_unit_ids": [m01.UNIT_ID],
        "modified_lesson_ids": [m01.LESSON_IDS[key] for key in ("READING", "WRITING", "SPEAKING")],
        "learner_state_migration_required": False,
        "shared_state_packaged_as_release_authority": False,
        "atomic_update_channel": r01.TASK_ID,
    })
    return manifest


def build_candidate_release(
    *, package_root: Path, code_root: Path, source: Mapping[str, Any], overlay: Mapping[str, Any],
) -> Path:
    candidate = Path(package_root).resolve() / "release_candidate" / TARGET_VERSION
    if candidate.exists():
        shutil.rmtree(candidate)
    candidate.mkdir(parents=True)
    r01._copy_tree(Path(code_root).resolve() / "ulga", candidate / "app/ulga")
    r01._copy_tree(overlay["static"], candidate / "runtime/secure_static")
    shutil.copy2(source["graph"], candidate / "runtime/graph.json")
    write_json(candidate / "runtime/bundles.json", overlay["bundles"])
    write_json(candidate / "runtime/sequence.json", source["sequence"])
    write_json(candidate / "VERSION.json", {
        "product_id": r01.PRODUCT_ID,
        "product_version": TARGET_VERSION,
        "release_id": RELEASE_ID,
        "content_release_task_id": m01.TASK_ID,
        "approved_content_sha256": overlay["approved"]["artifact_sha256"],
        "immutable_release": True,
    })
    write_json(candidate / "release_manifest.json", release_manifest(m01_approved=overlay["approved"]))
    r01._write_checksums(candidate)
    manifest = r01.validate_release(candidate)
    if (
        manifest.get("product_version") != TARGET_VERSION
        or manifest.get("release_id") != RELEASE_ID
        or manifest.get("approved_content_sha256") != overlay["approved"]["artifact_sha256"]
    ):
        raise ReleaseCoreError("candidate_release_manifest_invalid")
    return candidate


def build_acceptance_root(*, product_root: Path, target_root: Path) -> Path:
    source = Path(product_root).resolve()
    target = Path(target_root).resolve()
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    current = r01._current_version(source)
    r01._copy_tree(source / "releases" / current, target / "releases" / current)
    r01._copy_sqlite(
        source / "shared/database/learner_runtime.sqlite3",
        target / "shared/database/learner_runtime.sqlite3",
    )
    r01._copy_sqlite(
        source / "shared/auth/auth_state.sqlite3",
        target / "shared/auth/auth_state.sqlite3",
    )
    r01._copy_tree(
        source / "shared/learner_state/canonical_learning_state",
        target / "shared/learner_state/canonical_learning_state",
    )
    for folder in ("shared/logs", "shared/config", "staging", "backups"):
        (target / folder).mkdir(parents=True, exist_ok=True)
    if (source / "product.json").is_file():
        shutil.copy2(source / "product.json", target / "product.json")
    (target / "current_version.txt").write_text(current + "\n", encoding="ascii")
    return target


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
if ($LASTEXITCODE -ne 0) {{ throw "A1FS_V1_1_UPDATE_FAILED" }}
$Installed = (Get-Content -LiteralPath $CurrentFile -Raw).Trim()
if ($Installed -ne "{TARGET_VERSION}") {{ throw "A1FS_V1_1_VERSION_SWITCH_FAILED=$Installed" }}
Write-Host "A1FS_V1_1_UNIT01_INSTALL=PASS"
Write-Host "PRODUCT_ROOT=$ProductRoot"
Write-Host "CURRENT_VERSION=$Installed"
'''
    path = package_root / "INSTALL_A1FS_V1_1_UNIT01.ps1"
    path.write_text(script.replace("\n", "\r\n"), encoding="ascii")
    return path
