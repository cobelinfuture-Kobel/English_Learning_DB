#!/usr/bin/env python3
'''Self-contained A1FS V1 product root with atomic update and rollback.'''
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
from urllib.error import URLError
from urllib.request import urlopen

from ulga.builders import build_a1fs_online_v1_s19_localhost_nonaudio_learner_product_release_candidate as s19

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Packages the accepted S19/S17 code, runtime projection, and persistent state into one "
    "versioned local product root and adds atomic update/rollback controls. It creates no "
    "learner content, answer, scoring, review, mastery, dashboard, role authority, audio, "
    "A2, Cloudflare route, external binding, or parallel engine."
)
PROGRAM_ID = "A1FS-ONLINE-V1"
TASK_ID = "A1FS-ONLINE-V1-R01_SelfContainedV1ProductRootAndAtomicUpdateChannel"
SCHEMA_VERSION = "a1fs.online.v1.r01.self_contained_product_root.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_R01_SELF_CONTAINED_PRODUCT_ROOT_UPDATE_CHANNEL_READY"
PRODUCT_STATUS = "SELF_CONTAINED_LOCALHOST_NONAUDIO_V1_PRODUCT_ROOT_READY_NOT_EXTERNAL"
RELEASE_PROFILE = "ONLINE_V1_AUDIO_DEFERRED"
PRODUCT_ID = "A1FS_A1_A1PLUS_LOCAL_NOAUDIO"
PRODUCT_VERSION = "1.0.0"
DEFAULT_PRODUCT_ROOT = Path(r"G:\HomeWork\A1FS_V1")
DEFAULT_PORT = 8765
MODULE = "ulga.builders.build_a1fs_online_v1_r01_self_contained_product_root_update_channel"
NEXT_SHORT_STEP = "A1FS-ONLINE-V1-R02_V1UpdatePackageAdmissionAndMigrationCompatibility"
REQUIRED_ENV = (
    "A1FS_S11_AUTH_USERNAME",
    "A1FS_S11_AUTH_PASSWORD",
    "A1FS_S11_SESSION_SECRET",
)


class ProductRootError(ValueError):
    pass


def digest(value: Any) -> str:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def directory_digest(root: Path) -> str:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ProductRootError(f"directory_missing:{root}")
    hasher = hashlib.sha256()
    for path in sorted((p for p in root.rglob("*") if p.is_file()),
                       key=lambda p: p.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        hasher.update(len(relative).to_bytes(8, "big"))
        hasher.update(relative)
        hasher.update(bytes.fromhex(file_digest(path)))
    return hasher.hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductRootError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ProductRootError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _atomic_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="ascii", newline="\n")
    os.replace(temporary, path)


def _copy_sqlite(source: Path, target: Path) -> None:
    """Copy SQLite state and close both handles before Windows atomic replace."""
    source, target = Path(source), Path(target)
    if not source.is_file():
        raise ProductRootError(f"sqlite_source_missing:{source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with closing(sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(temporary)) as dst:
                src.backup(dst)
                dst.commit()
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _copy_tree(source: Path, target: Path) -> None:
    source, target = Path(source), Path(target)
    if not source.is_dir():
        raise ProductRootError(f"tree_source_missing:{source}")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source, target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".git", ".pytest_cache"),
    )


def _relative(value: str) -> str:
    normalized = str(value).replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts or ":" in normalized:
        raise ProductRootError(f"product_manifest_path_not_relative:{value}")
    return normalized


def _resolve(product_root: Path, relative: str) -> Path:
    product_root = Path(product_root).resolve()
    candidate = (product_root / _relative(relative)).resolve()
    try:
        candidate.relative_to(product_root)
    except ValueError as exc:
        raise ProductRootError(f"product_path_escape:{relative}") from exc
    return candidate


def _write_checksums(release_root: Path) -> Path:
    release_root = Path(release_root).resolve()
    target = release_root / "checksums.json"
    rows = {
        path.relative_to(release_root).as_posix(): file_digest(path)
        for path in sorted(
            (p for p in release_root.rglob("*") if p.is_file() and p != target),
            key=lambda p: p.relative_to(release_root).as_posix(),
        )
    }
    write_json(target, {
        "schema_version": "a1fs.online.v1.r01.release_checksums.v1",
        "files": rows,
        "file_count": len(rows),
        "files_sha256": digest(rows),
    })
    return target


def validate_release(release_root: Path) -> dict[str, Any]:
    release_root = Path(release_root).resolve()
    manifest = read_json(release_root / "release_manifest.json", "r01_release_manifest")
    checksums = read_json(release_root / "checksums.json", "r01_checksums")
    files = checksums.get("files")
    if not isinstance(files, Mapping) or not files:
        raise ProductRootError("r01_checksum_files_invalid")
    actual = {str(rel): file_digest(release_root / _relative(str(rel))) for rel in files}
    if actual != dict(files) or checksums.get("files_sha256") != digest(dict(files)):
        raise ProductRootError("r01_release_checksum_mismatch")
    if manifest.get("product_id") != PRODUCT_ID:
        raise ProductRootError("r01_release_product_identity_invalid")
    for key in (
        "app_root", "secure_static_root", "graph_path", "bundle_registry_path",
        "sequence_path", "shared_database_path", "shared_auth_state_path",
        "shared_learner_state_root",
    ):
        _relative(str(manifest.get(key) or ""))
    return manifest


def _source_from_s19(s19_path: Path):
    s19_path = Path(s19_path).resolve()
    receipt = read_json(s19_path, "s19_receipt")
    identity = (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("release_candidate_id"), receipt.get("stop_reason"),
    )
    if identity != (
        s19.TASK_ID, s19.SCHEMA_VERSION, s19.PASS_STATUS, s19.PRODUCT_STATUS,
        s19.RELEASE_CANDIDATE_ID, "NONE",
    ):
        raise ProductRootError("s19_receipt_contract_invalid")
    body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != s19.digest(body):
        raise ProductRootError("s19_receipt_digest_invalid")
    outputs = receipt.get("runtime_outputs", {})
    s19._validate_checksums(
        Path(str(outputs.get("release_root") or "")).resolve(),
        Path(str(outputs.get("checksum_manifest_path") or "")).resolve(),
    )
    source_s17 = Path(str(outputs.get("source_s17_receipt_path") or "")).resolve()
    _, database, auth_state, bundles, sequence, graph, state, static = s19.s18.s17._load_runtime(source_s17)
    if len(bundles) != 72 or len(sequence) != 24:
        raise ProductRootError("r01_source_denominator_invalid")
    return receipt, Path(database), Path(auth_state), dict(bundles), dict(sequence), Path(graph), Path(state), Path(static)


def _bat_lines(lines: Sequence[str]) -> bytes:
    return ("\r\n".join(lines) + "\r\n").encode("ascii")


def _write_operator_bundle(product_root: Path) -> dict[str, str]:
    root = Path(product_root).resolve()
    bin_root = root / "bin"
    bin_root.mkdir(parents=True, exist_ok=True)
    prefix = [
        "@echo off",
        "setlocal EnableExtensions",
        'for %%I in ("%~dp0..") do set "ROOT=%%~fI"',
        'set /p VERSION=<"%ROOT%\\current_version.txt"',
        'set "PYTHONPATH=%ROOT%\\releases\\%VERSION%\\app"',
    ]
    scripts = {
        "OPEN_A1FS_V1.bat": prefix + [
            f'python -m {MODULE} start --product-root "%ROOT%" --port {DEFAULT_PORT}',
            "if errorlevel 1 goto FAIL",
            f'start "" "http://127.0.0.1:{DEFAULT_PORT}"',
            "exit /b 0",
            ":FAIL",
            "echo START FAILED",
            'echo Check "%ROOT%\\shared\\logs\\a1fs_v1.stderr.log"',
            "pause",
            "exit /b 1",
        ],
        "STOP_A1FS_V1.bat": prefix + [
            f'python -m {MODULE} stop --product-root "%ROOT%" --port {DEFAULT_PORT}',
            "if errorlevel 1 pause",
        ],
        "STATUS_A1FS_V1.bat": prefix + [
            f'python -m {MODULE} status --product-root "%ROOT%" --port {DEFAULT_PORT}',
            "pause",
        ],
        "UPDATE_A1FS_V1.bat": [
            "@echo off", "setlocal EnableExtensions",
            'if "%~1"=="" goto USAGE', 'if "%~2"=="" goto USAGE',
            'for %%I in ("%~dp0..") do set "ROOT=%%~fI"',
            'set /p VERSION=<"%ROOT%\\current_version.txt"',
            'set "PYTHONPATH=%ROOT%\\releases\\%VERSION%\\app"',
            f'python -m {MODULE} update --product-root "%ROOT%" --candidate "%~1" --version "%~2"',
            "if errorlevel 1 pause", "exit /b %ERRORLEVEL%", ":USAGE",
            "echo Usage: UPDATE_A1FS_V1.bat C:\\path\\to\\candidate 1.0.1",
            "pause", "exit /b 2",
        ],
        "ROLLBACK_A1FS_V1.bat": prefix + [
            f'python -m {MODULE} rollback --product-root "%ROOT%" %*',
            "if errorlevel 1 pause",
        ],
    }
    outputs = {}
    for name, lines in scripts.items():
        path = bin_root / name
        path.write_bytes(_bat_lines(lines))
        outputs[name] = str(path)
    return outputs


def _release_manifest(version: str) -> dict[str, Any]:
    base = f"releases/{version}"
    return {
        "schema_version": "a1fs.online.v1.r01.release_manifest.v1",
        "product_id": PRODUCT_ID,
        "product_version": version,
        "release_profile": RELEASE_PROFILE,
        "serve_module": MODULE,
        "app_root": f"{base}/app",
        "secure_static_root": f"{base}/runtime/secure_static",
        "graph_path": f"{base}/runtime/graph.json",
        "bundle_registry_path": f"{base}/runtime/bundles.json",
        "sequence_path": f"{base}/runtime/sequence.json",
        "shared_database_path": "shared/database/learner_runtime.sqlite3",
        "shared_auth_state_path": "shared/auth/auth_state.sqlite3",
        "shared_learner_state_root": "shared/learner_state/canonical_learning_state",
        "host": "127.0.0.1", "port": DEFAULT_PORT,
        "unit_count": 24, "lesson_count": 72, "asset_count": 264,
        "scored_lesson_count": 48, "speaking_practice_lesson_count": 24,
        "dashboard_role_count": 3,
        "external_network_binding_allowed": False,
        "public_delivery_enabled": False, "cloudflare_enabled": False,
        "listening_enabled": False, "audio_enabled": False,
        "speaking_capture_enabled": False, "a2_session_enabled": False,
    }


def _build_release(*, staging_root: Path, version: str, code_root: Path,
                   secure_static: Path, graph_path: Path,
                   bundles: Mapping[str, Any], sequence: Mapping[str, int]) -> Path:
    if staging_root.exists():
        shutil.rmtree(staging_root)
    release = staging_root / version
    _copy_tree(Path(code_root) / "ulga", release / "app" / "ulga")
    _copy_tree(secure_static, release / "runtime" / "secure_static")
    shutil.copy2(graph_path, release / "runtime" / "graph.json")
    write_json(release / "runtime" / "bundles.json", bundles)
    write_json(release / "runtime" / "sequence.json", sequence)
    write_json(release / "VERSION.json", {
        "product_id": PRODUCT_ID, "product_version": version, "immutable_release": True,
    })
    write_json(release / "release_manifest.json", _release_manifest(version))
    _write_checksums(release)
    validate_release(release)
    return release


def _initialize_shared(*, product_root: Path, database: Path,
                       auth_state: Path, state_root: Path) -> dict[str, str]:
    shared = Path(product_root) / "shared"
    target_db = shared / "database" / "learner_runtime.sqlite3"
    target_auth = shared / "auth" / "auth_state.sqlite3"
    target_state = shared / "learner_state" / "canonical_learning_state"
    if not target_db.exists():
        _copy_sqlite(database, target_db)
    if not target_auth.exists():
        _copy_sqlite(auth_state, target_auth)
    if not target_state.exists():
        _copy_tree(state_root, target_state)
    (shared / "config").mkdir(parents=True, exist_ok=True)
    (shared / "logs").mkdir(parents=True, exist_ok=True)
    return {
        "database_sha256": file_digest(target_db),
        "auth_state_sha256": file_digest(target_auth),
        "learner_state_sha256": directory_digest(target_state),
    }


def _backup_shared(product_root: Path, version: str) -> Path:
    root = Path(product_root)
    backup = root / "backups" / f"before_{version}"
    if backup.exists():
        raise ProductRootError(f"backup_already_exists:{backup}")
    _copy_sqlite(root / "shared/database/learner_runtime.sqlite3",
                 backup / "database/learner_runtime.sqlite3")
    _copy_sqlite(root / "shared/auth/auth_state.sqlite3",
                 backup / "auth/auth_state.sqlite3")
    _copy_tree(root / "shared/learner_state/canonical_learning_state",
               backup / "learner_state/canonical_learning_state")
    return backup


def _current_version(product_root: Path) -> str:
    path = Path(product_root) / "current_version.txt"
    if not path.is_file():
        raise ProductRootError("current_version_missing")
    value = path.read_text(encoding="ascii").strip()
    if not value:
        raise ProductRootError("current_version_empty")
    return value


def _switch_version(product_root: Path, version: str) -> None:
    root = Path(product_root)
    validate_release(root / "releases" / version)
    current_file = root / "current_version.txt"
    old = current_file.read_text(encoding="ascii").strip() if current_file.exists() else ""
    if old and old != version:
        _atomic_text(root / "previous_version.txt", old + "\n")
    _atomic_text(current_file, version + "\n")


def install_candidate(*, product_root: Path, candidate: Path, version: str) -> dict[str, Any]:
    root, candidate = Path(product_root).resolve(), Path(candidate).resolve()
    current = _current_version(root)
    target, staging = root / "releases" / version, root / "staging" / f"{version}.pending"
    if target.exists():
        raise ProductRootError(f"release_version_already_exists:{version}")
    switched = False
    try:
        _copy_tree(candidate, staging)
        manifest = validate_release(staging)
        if manifest.get("product_version") != version:
            raise ProductRootError("candidate_version_mismatch")
        backup = _backup_shared(root, version)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, target)
        _switch_version(root, version)
        switched = True
        return {
            "status": "PASS_ATOMIC_UPDATE_ACTIVATED",
            "previous_version": current, "current_version": version,
            "backup_root": str(backup), "shared_state_preserved": True,
        }
    except Exception:
        if switched:
            _atomic_text(root / "current_version.txt", current + "\n")
        if staging.exists():
            shutil.rmtree(staging)
        if target.exists() and (root / "current_version.txt").read_text(encoding="ascii").strip() != version:
            shutil.rmtree(target)
        raise


def rollback(*, product_root: Path, version: str | None = None) -> dict[str, Any]:
    root = Path(product_root).resolve()
    current = _current_version(root)
    target = version
    if not target:
        previous = root / "previous_version.txt"
        if not previous.is_file():
            raise ProductRootError("previous_version_missing")
        target = previous.read_text(encoding="ascii").strip()
    if not target or target == current:
        raise ProductRootError("rollback_target_invalid")
    _switch_version(root, target)
    return {
        "status": "PASS_ATOMIC_ROLLBACK_ACTIVATED",
        "previous_version": current, "current_version": target,
        "shared_state_preserved": True,
    }


def materialize(*, s19_path: Path, output_path: Path, report_path: Path,
                product_root: Path, code_root: Path,
                version: str = PRODUCT_VERSION) -> tuple[dict[str, Any], dict[str, Any]]:
    source, database, auth, bundles, sequence, graph, state, static = _source_from_s19(s19_path)
    root = Path(product_root).resolve()
    release_target = root / "releases" / version
    staging_root = root / "staging" / "initial.pending"
    root.mkdir(parents=True, exist_ok=True)
    shared_hashes = _initialize_shared(
        product_root=root, database=database, auth_state=auth, state_root=state,
    )
    if release_target.exists():
        manifest = validate_release(release_target)
        if manifest.get("product_version") != version:
            raise ProductRootError("existing_release_version_invalid")
    else:
        staged = _build_release(
            staging_root=staging_root, version=version, code_root=code_root,
            secure_static=static, graph_path=graph, bundles=bundles, sequence=sequence,
        )
        release_target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged, release_target)
        if staging_root.exists():
            shutil.rmtree(staging_root)
    _switch_version(root, version)
    operator = _write_operator_bundle(root)
    write_json(root / "product.json", {
        "schema_version": SCHEMA_VERSION,
        "product_id": PRODUCT_ID,
        "display_name": "A1FS A1/A1+ Local No-Audio Learner Product V1",
        "release_profile": RELEASE_PROFILE,
        "current_version_file": "current_version.txt",
        "release_root": "releases", "shared_root": "shared",
        "staging_root": "staging", "backup_root": "backups",
        "update_policy": "STAGE_VALIDATE_BACKUP_ATOMIC_SWITCH_ROLLBACK",
        "github_code_authority": "cobelinfuture-Kobel/English_Learning_DB:main",
        "external_network_binding_allowed": False,
        "audio_enabled": False, "a2_session_enabled": False,
    })
    release_manifest = validate_release(release_target)
    summary = {
        "product_id": PRODUCT_ID, "product_version": version,
        "unit_count": 24, "lesson_count": 72, "asset_count": 264,
        "scored_lesson_count": 48, "speaking_practice_lesson_count": 24,
        "dashboard_role_count": 3,
        "self_contained_product_root_created": True,
        "immutable_release_directory_created": True,
        "shared_persistent_state_created": True,
        "relative_path_manifest_created": True,
        "ascii_crlf_bat_bundle_created": True,
        "atomic_update_channel_created": True,
        "automatic_rollback_on_update_failure": True,
        "explicit_rollback_command_created": True,
        "shared_state_preserved_across_updates": True,
        "release_checksum_verified": True,
        "external_deployment_enabled": False, "public_delivery_enabled": False,
        "cloudflare_enabled": False, "listening_enabled": False,
        "audio_enabled": False, "speaking_capture_enabled": False,
        "a2_session_enabled": False,
    }
    receipt_core = {
        "task_id": TASK_ID, "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION, "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS, "release_profile": RELEASE_PROFILE,
        "product_id": PRODUCT_ID, "product_version": version,
        "source_identity": {
            "s19_sha256": s19.digest(source),
            "source_database_sha256": file_digest(database),
            "source_auth_state_sha256": file_digest(auth),
            "source_state_sha256": directory_digest(state),
        },
        "runtime_outputs": {
            "product_root": str(root), "release_root": str(release_target),
            "release_manifest_path": str(release_target / "release_manifest.json"),
            "checksum_manifest_path": str(release_target / "checksums.json"),
            "shared_database_path": str(root / release_manifest["shared_database_path"]),
            "shared_auth_state_path": str(root / release_manifest["shared_auth_state_path"]),
            "shared_learner_state_root": str(root / release_manifest["shared_learner_state_root"]),
            "current_version_path": str(root / "current_version.txt"),
            "product_manifest_path": str(root / "product.json"),
            "operator_paths": operator,
        },
        "shared_state_identity": shared_hashes,
        "product_root_summary": summary,
        "capability_contract": {
            "s19_release_candidate_reused": True, "s17_runtime_reused": True,
            "m6_scoring_review_reused": True,
            "m7_m8_canonical_learning_reused": True,
            "m9_dashboard_projection_reused": True,
            "parallel_curriculum_created": False,
            "parallel_learner_state_engine_created": False,
            "parallel_scoring_engine_created": False,
            "parallel_mastery_engine_created": False,
            "parallel_dashboard_engine_created": False,
            "parallel_review_engine_created": False,
        },
        "stop_reason": "NONE", "next_short_step": NEXT_SHORT_STEP,
    }
    receipt = {**receipt_core, "artifact_sha256": s19.digest(receipt_core)}
    safe_core = {
        "task_id": TASK_ID, "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION, "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS, "release_profile": RELEASE_PROFILE,
        "product_id": PRODUCT_ID, "product_version": version,
        "product_root_summary": summary,
        "capability_contract": receipt_core["capability_contract"],
        "stop_reason": "NONE", "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": s19.digest(safe_core)}
    write_json(output_path, receipt)
    write_json(report_path, safe)
    return receipt, safe


def _load_product(product_root: Path):
    root = Path(product_root).resolve()
    version = _current_version(root)
    manifest = validate_release(root / "releases" / version)
    if manifest.get("product_version") != version:
        raise ProductRootError("current_release_manifest_version_mismatch")
    bundles = read_json(_resolve(root, manifest["bundle_registry_path"]), "bundles")
    raw_sequence = read_json(_resolve(root, manifest["sequence_path"]), "sequence")
    sequence = {str(key): int(value) for key, value in raw_sequence.items()}
    if len(bundles) != 72 or len(sequence) != 24:
        raise ProductRootError("current_release_denominator_invalid")
    return version, manifest, bundles, sequence


def serve(*, product_root: Path, host: str, port: int) -> None:
    if not s19.s18.s17.s16.s15.s11._is_loopback(host):
        raise ProductRootError(f"non_loopback_host_forbidden:{host}")
    root = Path(product_root).resolve()
    _, manifest, bundles, sequence = _load_product(root)
    database = _resolve(root, manifest["shared_database_path"])
    auth = _resolve(root, manifest["shared_auth_state_path"])
    state = _resolve(root, manifest["shared_learner_state_root"])
    graph = _resolve(root, manifest["graph_path"])
    static = _resolve(root, manifest["secure_static_root"])
    config = s19.s18.s17.s16.s15.s13.PersistentBoundaryConfig.from_environment(
        host=host, port=port, revocation_db_path=auth,
    )
    server = s19.s18.s17.DashboardReviewServer(
        (host, port),
        s19.s18.s17._app(
            database=database, bundles=bundles, sequence=sequence,
            graph_path=graph, state_root=state,
        ),
        static, config,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return pid > 0


def _health(port: int, timeout: float = 2.0) -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
        return value.get("status") == "PASS" and value.get("authentication_required") is True
    except (OSError, URLError, json.JSONDecodeError):
        return False


def start(*, product_root: Path, port: int) -> dict[str, Any]:
    root = Path(product_root).resolve()
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise ProductRootError(f"MISSING_ENV={missing[0]}")
    version, manifest, _, _ = _load_product(root)
    pid_path = root / "shared" / "a1fs_v1.pid"
    if pid_path.exists():
        pid = int(pid_path.read_text(encoding="ascii").strip())
        if _pid_alive(pid) and _health(port):
            return {"status": "ALREADY_RUNNING", "pid": pid, "version": version}
        pid_path.unlink(missing_ok=True)
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise ProductRootError(f"PORT_IN_USE={port}")
    logs = root / "shared" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    app_root = _resolve(root, manifest["app_root"])
    env = os.environ.copy()
    env["PYTHONPATH"] = str(app_root) + os.pathsep + env.get("PYTHONPATH", "")
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    with (logs / "a1fs_v1.stdout.log").open("ab") as stdout, \
         (logs / "a1fs_v1.stderr.log").open("ab") as stderr:
        process = subprocess.Popen(
            [sys.executable, "-m", MODULE, "serve", "--product-root", str(root),
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=app_root, env=env, stdout=stdout, stderr=stderr,
            stdin=subprocess.DEVNULL, creationflags=flags, close_fds=(os.name != "nt"),
        )
    _atomic_text(pid_path, str(process.pid) + "\n")
    for _ in range(40):
        if process.poll() is not None:
            pid_path.unlink(missing_ok=True)
            raise ProductRootError(f"A1FS_V1_PROCESS_EXITED={process.returncode}")
        if _health(port, 1.0):
            return {
                "status": "PASS_A1FS_V1_STARTED", "pid": process.pid,
                "version": version, "url": f"http://127.0.0.1:{port}",
            }
        time.sleep(0.5)
    process.terminate()
    pid_path.unlink(missing_ok=True)
    raise ProductRootError("A1FS_V1_READINESS_TIMEOUT")


def status(*, product_root: Path, port: int) -> dict[str, Any]:
    root = Path(product_root).resolve()
    version = _current_version(root)
    pid_path = root / "shared" / "a1fs_v1.pid"
    if not pid_path.is_file():
        raise ProductRootError("A1FS_V1_STATUS=STOPPED")
    pid = int(pid_path.read_text(encoding="ascii").strip())
    if not _pid_alive(pid):
        raise ProductRootError("A1FS_V1_STATUS=STALE_PID")
    if not _health(port):
        raise ProductRootError("A1FS_V1_STATUS=UNHEALTHY")
    return {
        "status": "A1FS_V1_STATUS=RUNNING", "pid": pid,
        "version": version, "url": f"http://127.0.0.1:{port}",
    }


def stop(*, product_root: Path, port: int) -> dict[str, Any]:
    root = Path(product_root).resolve()
    pid_path = root / "shared" / "a1fs_v1.pid"
    if not pid_path.is_file():
        raise ProductRootError("PID_FILE_MISSING")
    pid = int(pid_path.read_text(encoding="ascii").strip())
    if _pid_alive(pid):
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"], check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            if not _pid_alive(pid):
                break
            time.sleep(0.25)
    if _pid_alive(pid):
        raise ProductRootError(f"PROCESS_STILL_RUNNING={pid}")
    pid_path.unlink(missing_ok=True)
    if _health(port, 0.5):
        raise ProductRootError(f"PORT_STILL_LISTENING={port}")
    return {"status": "PASS_A1FS_V1_STOPPED", "pid": pid}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--s19", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    build.add_argument("--product-root", type=Path)
    build.add_argument("--code-root", type=Path, default=Path(__file__).resolve().parents[2])
    build.add_argument("--version", default=PRODUCT_VERSION)
    server = commands.add_parser("serve")
    server.add_argument("--product-root", type=Path, default=DEFAULT_PRODUCT_ROOT)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=DEFAULT_PORT)
    for name in ("start", "stop", "status"):
        command = commands.add_parser(name)
        command.add_argument("--product-root", type=Path, default=DEFAULT_PRODUCT_ROOT)
        command.add_argument("--port", type=int, default=DEFAULT_PORT)
    update = commands.add_parser("update")
    update.add_argument("--product-root", type=Path, default=DEFAULT_PRODUCT_ROOT)
    update.add_argument("--candidate", type=Path, required=True)
    update.add_argument("--version", required=True)
    undo = commands.add_parser("rollback")
    undo.add_argument("--product-root", type=Path, default=DEFAULT_PRODUCT_ROOT)
    undo.add_argument("--version")
    args = parser.parse_args(argv)
    try:
        if args.command == "materialize":
            product_root = args.product_root or (args.output.parent / "A1FS_V1")
            receipt, safe = materialize(
                s19_path=args.s19, output_path=args.output, report_path=args.report,
                product_root=product_root, code_root=args.code_root, version=args.version,
            )
            from ulga.validators.validate_a1fs_online_v1_r01_self_contained_product_root_update_channel import validate_outputs
            validation = validate_outputs(
                receipt=receipt, safe_report=safe,
                output_root=args.output.parent, s19_path=args.s19,
            )
            if validation["error_count"]:
                raise ProductRootError("validation_failed:" + "|".join(validation["errors"]))
            print(json.dumps(safe, ensure_ascii=False, indent=2))
        elif args.command == "serve":
            serve(product_root=args.product_root, host=args.host, port=args.port)
        elif args.command == "start":
            print(json.dumps(start(product_root=args.product_root, port=args.port), indent=2))
        elif args.command == "stop":
            print(json.dumps(stop(product_root=args.product_root, port=args.port), indent=2))
        elif args.command == "status":
            print(json.dumps(status(product_root=args.product_root, port=args.port), indent=2))
        elif args.command == "update":
            print(json.dumps(install_candidate(
                product_root=args.product_root, candidate=args.candidate, version=args.version
            ), indent=2))
        else:
            print(json.dumps(rollback(
                product_root=args.product_root, version=args.version
            ), indent=2))
        return 0
    except (
        ProductRootError, s19.ReleaseCandidateError, sqlite3.Error, OSError,
        KeyError, TypeError, ValueError, json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
