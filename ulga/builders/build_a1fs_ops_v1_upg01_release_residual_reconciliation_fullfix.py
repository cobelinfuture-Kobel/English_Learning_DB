#!/usr/bin/env python3
"""Reconcile inactive release, staging, and backup residuals before Python UPG01.

A failed post-install acceptance can roll the active pointer back while leaving a
validated immutable target release, a version backup, or a pending staging tree.
R01's base installer intentionally rejects all of those paths. This adapter keeps
that fail-closed base behavior for normal callers, but gives UPG01 a scoped,
validated resume path:

* an inactive release is reused only when its product/runtime identity matches the
  newly built candidate;
* a different or invalid inactive release is moved to deterministic recovery
  quarantine before the candidate is installed;
* stale staging and version backups are quarantined and a fresh pre-step backup is
  created;
* active releases are never replaced, and shared learner state is never deleted.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_upg01_python_upgrade_fullfix_residual_canonical_rebase as base,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Extends the accepted Python-only UPG01 path with scoped reconciliation of "
    "inactive validated release, staging, and backup residuals left by a failed "
    "post-install acceptance. Matching immutable releases are reactivated; invalid "
    "or semantically different residuals are quarantined before the existing R01 "
    "installer runs. Shared learner data is never deleted or rewritten by this "
    "adapter. It creates no content, answer, learner attempt, score, mastery state, "
    "audio, A2 unlock, external route, release authority, or parallel installer."
)

PROGRAM_ID = base.PROGRAM_ID
TASK_ID = base.TASK_ID
SCHEMA_VERSION = base.SCHEMA_VERSION
PASS_STATUS = base.PASS_STATUS
PLAN_PASS_STATUS = base.PLAN_PASS_STATUS
DEFAULT_PORT = base.DEFAULT_PORT
PythonUpgradeFullFixError = base.PythonUpgradeFullFixError
runtime = base.runtime
s01 = base.s01
s05 = base.s05
r01 = runtime.core.r01
_BASE_INSTALL_CANDIDATE = r01.install_candidate

_MANIFEST_IDENTITY_KEYS = (
    "product_id",
    "product_version",
    "release_id",
    "source_product_version",
    "serve_module",
    "unit_count",
    "lesson_count",
    "asset_count",
    "graph_path",
    "bundle_registry_path",
    "sequence_path",
    "unit01_target_registry_path",
    "approved_content_sha256",
    "runtime_patch_task_id",
    "database_migration_mode",
)


def _tree_projection(root: Path, *, exclude_upg01: bool = False) -> str:
    root = Path(root).resolve()
    if not root.is_dir():
        return "MISSING"
    rows: list[tuple[str, str]] = []
    for path in sorted(
        (row for row in root.rglob("*") if row.is_file()),
        key=lambda row: row.relative_to(root).as_posix(),
    ):
        relative = path.relative_to(root).as_posix()
        lowered = relative.casefold()
        if "__pycache__" in lowered or lowered.endswith((".pyc", ".pyo")):
            continue
        if exclude_upg01 and "build_a1fs_ops_v1_upg01" in lowered:
            continue
        rows.append((relative, r01.file_digest(path)))
    return r01.digest(rows)


def release_resume_identity(release_root: Path) -> dict[str, Any]:
    release_root = Path(release_root).resolve()
    manifest = r01.validate_release(release_root)
    return {
        "manifest": {
            key: manifest.get(key)
            for key in _MANIFEST_IDENTITY_KEYS
            if key in manifest
        },
        "runtime_sha256": _tree_projection(release_root / "runtime"),
        "app_runtime_sha256": _tree_projection(
            release_root / "app", exclude_upg01=True
        ),
    }


def _quarantine(root: Path, source: Path, *, version: str, label: str) -> str | None:
    source = Path(source).resolve()
    if not source.exists():
        return None
    try:
        fingerprint = r01.directory_digest(source)[:16]
    except Exception:
        fingerprint = "invalid"
    target = (
        Path(root).resolve()
        / "recovery"
        / "upg01_residuals"
        / str(version)
        / f"{label}-{fingerprint}"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(r01._win32_long_path(source))
        return str(target)
    os.replace(r01._win32_long_path(source), r01._win32_long_path(target))
    return str(target)


def _fresh_backup(root: Path, version: str) -> tuple[Path, str | None]:
    backup = Path(root).resolve() / "backups" / f"before_{version}"
    quarantined = _quarantine(
        root, backup, version=version, label="stale-backup"
    )
    created = r01._backup_shared(Path(root).resolve(), version)
    return created, quarantined


def resumable_install_candidate(
    *, product_root: Path, candidate: Path, version: str
) -> dict[str, Any]:
    root = Path(product_root).resolve()
    candidate = Path(candidate).resolve()
    current = r01._current_version(root)
    candidate_manifest = r01.validate_release(candidate)
    if candidate_manifest.get("product_version") != version:
        raise r01.ProductRootError("candidate_version_mismatch")

    target = root / "releases" / version
    staging = root / "staging" / f"{version}.pending"
    reconciliation: dict[str, Any] = {
        "target_version": version,
        "current_version_before": current,
        "existing_release_present": target.exists(),
        "existing_release_reused": False,
        "existing_release_quarantined": None,
        "staging_quarantined": _quarantine(
            root, staging, version=version, label="stale-staging"
        ),
        "stale_backup_quarantined": None,
        "fresh_backup_created": False,
        "shared_state_deleted": False,
    }

    if current == version:
        manifest = r01.validate_release(target)
        if manifest.get("product_version") != version:
            raise r01.ProductRootError("active_release_version_invalid")
        return {
            "status": "PASS_TARGET_RELEASE_ALREADY_ACTIVE",
            "previous_version": current,
            "current_version": current,
            "backup_root": None,
            "shared_state_preserved": True,
            "upg01_release_residual_reconciliation": reconciliation,
        }

    if target.exists():
        try:
            existing_identity = release_resume_identity(target)
        except Exception:
            existing_identity = None
        candidate_identity = release_resume_identity(candidate)
        if existing_identity == candidate_identity:
            backup, old_backup = _fresh_backup(root, version)
            r01._switch_version(root, version)
            reconciliation.update(
                {
                    "existing_release_reused": True,
                    "stale_backup_quarantined": old_backup,
                    "fresh_backup_created": True,
                    "release_identity_match": True,
                }
            )
            return {
                "status": "PASS_ATOMIC_UPDATE_REACTIVATED_VALID_EXISTING_RELEASE",
                "previous_version": current,
                "current_version": version,
                "backup_root": str(backup),
                "shared_state_preserved": True,
                "upg01_release_residual_reconciliation": reconciliation,
            }
        reconciliation["existing_release_quarantined"] = _quarantine(
            root, target, version=version, label="inactive-release"
        )
        reconciliation["release_identity_match"] = False

    backup = root / "backups" / f"before_{version}"
    reconciliation["stale_backup_quarantined"] = _quarantine(
        root, backup, version=version, label="stale-backup"
    )
    installed = dict(
        _BASE_INSTALL_CANDIDATE(
            product_root=root,
            candidate=candidate,
            version=version,
        )
    )
    reconciliation["fresh_backup_created"] = True
    installed["upg01_release_residual_reconciliation"] = reconciliation
    return installed


def activate() -> None:
    base.activate()
    r01.install_candidate = resumable_install_candidate


def _entry_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(base._entry_metadata(value))
    compatibility = dict(result["residual_u01e_contract_compatibility"])
    compatibility.update(
        {
            "inactive_release_resume_enabled": True,
            "stale_staging_reconciliation_enabled": True,
            "stale_backup_reconciliation_enabled": True,
            "active_release_replacement_allowed": False,
            "shared_state_deletion_allowed": False,
            "release_mismatch_policy": "QUARANTINE_THEN_BASE_R01_INSTALL",
        }
    )
    result["residual_u01e_contract_compatibility"] = compatibility
    return result


def build_plan(**kwargs: Any) -> dict[str, Any]:
    return _entry_metadata(runtime.build_plan(**kwargs))


def upgrade(**kwargs: Any) -> dict[str, Any]:
    activate()
    return _entry_metadata(runtime.upgrade(**kwargs))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "upgrade"):
        command = commands.add_parser(name)
        command.add_argument("--code-root", type=Path)
        command.add_argument("--product-root", type=Path)
        command.add_argument("--output-root", type=Path)
        command.add_argument("--journal-path", type=Path)
        command.add_argument("--target-version", default="latest")
        command.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    kwargs = {
        "code_root": args.code_root,
        "product_root": args.product_root,
        "output_root": args.output_root,
        "journal_path": args.journal_path,
        "target_version": args.target_version,
        "port": args.port,
    }
    try:
        result = build_plan(**kwargs) if args.command == "plan" else upgrade(**kwargs)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (
        PythonUpgradeFullFixError,
        runtime.RuntimeShutdownFullFixError,
        runtime.core.UpgradeOrchestratorError,
        r01.ProductRootError,
        s01.S01AdmissionError,
        s05._core.S05ReleaseError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
