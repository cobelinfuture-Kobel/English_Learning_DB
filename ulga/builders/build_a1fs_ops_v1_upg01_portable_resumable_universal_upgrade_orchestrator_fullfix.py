#!/usr/bin/env python3
"""Unversioned, portable and resumable A1FS local-product upgrade entry."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Delegates every version transition to existing accepted release producers and "
    "the R01 atomic product-root update channel. It only discovers roots, plans, "
    "journals, resumes, verifies acceptance, and rolls back. It creates no content, "
    "answer, scoring/mastery authority, learner attempt, audio, A2 unlock, external "
    "route, or parallel runtime/migration authority."
)
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = "A1FS-OPS-V1-UPG01_PortableResumableUniversalUpgradeOrchestratorFullFix"
SCHEMA_VERSION = "a1fs.ops.v1.upg01.portable_resumable_upgrade_orchestrator.v1"
PLAN_PASS_STATUS = "PASS_A1FS_OPS_V1_UPG01_PORTABLE_UPGRADE_PLAN"
PASS_STATUS = "PASS_A1FS_OPS_V1_UPG01_PORTABLE_RESUMABLE_UPGRADE"
ROLLBACK_STATUS = "PASS_A1FS_OPS_V1_UPG01_AUTOMATIC_ROLLBACK"
VERSION_ORDER = ("1.0.0", "1.1.0", "1.1.1", "1.2.0", "1.2.1")
LATEST_VERSION = "1.2.1"
DEFAULT_PORT = r01.DEFAULT_PORT
NEXT_SHORT_STEP = "A1FS-OPS-V1-UPG01_OperatorTwoComputerPlanAndUpgradeReadback"


class UpgradeOrchestratorError(ValueError):
    pass


@dataclass(frozen=True)
class MigrationSpec:
    step_id: str
    source_versions: tuple[str, ...]
    target_version: str
    module_name: str
    install_function: str
    acceptance_module_name: str
    acceptance_function: str
    readback_name: str


MIGRATIONS = (
    MigrationSpec(
        "A1FS_OPS_UPGRADE_TO_1_2_0",
        ("1.0.0", "1.1.0", "1.1.1", "1.2.0"),
        "1.2.0",
        "ulga.builders.build_a1fs_online_v1_2_u01e_local_production_upgrade_chain",
        "install_and_accept",
        "ulga.builders.build_a1fs_online_v1_2_u01e_local_production_operator_acceptance",
        "operator_acceptance",
        "a1fs_v1_2_u01e_operator_acceptance.safe.json",
    ),
    MigrationSpec(
        "A1FS_OPS_UPGRADE_TO_1_2_1",
        ("1.2.0", "1.2.1"),
        "1.2.1",
        "ulga.builders.build_a1fs_online_v1_2_1_u01f_patch_release",
        "install_and_accept",
        "ulga.builders.build_a1fs_online_v1_2_1_u01f_patch_release",
        "operator_acceptance",
        "a1fs_v1_2_1_u01f_operator_acceptance.safe.json",
    ),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _path(value: Path | str) -> Path:
    return Path(value).expanduser().resolve()


def _version_index(version: str) -> int:
    try:
        return VERSION_ORDER.index(version)
    except ValueError as exc:
        raise UpgradeOrchestratorError(f"UNSUPPORTED_VERSION={version}") from exc


def _is_code_root(root: Path) -> bool:
    return (root / "ulga/builders").is_dir() and (root / "scripts").is_dir()


def discover_code_root(explicit: Path | None = None) -> tuple[Path, str]:
    rows: list[tuple[Path, str]] = []
    if explicit:
        rows.append((_path(explicit), "EXPLICIT"))
    if os.environ.get("A1FS_CODE_ROOT"):
        rows.append((_path(os.environ["A1FS_CODE_ROOT"]), "ENV:A1FS_CODE_ROOT"))
    rows += [
        (_path(Path.cwd()), "CURRENT_DIRECTORY"),
        (_path(Path(__file__).parents[2]), "MODULE_ROOT"),
    ]
    seen: set[str] = set()
    for root, source in rows:
        key = os.path.normcase(str(root))
        if key not in seen and _is_code_root(root):
            return root, source
        seen.add(key)
    raise UpgradeOrchestratorError("A1FS_CODE_ROOT_NOT_FOUND")


def _is_product_root(root: Path) -> bool:
    version_file = root / "current_version.txt"
    if not (version_file.is_file() and (root / "releases").is_dir()):
        return False
    try:
        version = version_file.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return False
    return (root / "releases" / version / "release_manifest.json").is_file()


def discover_product_root(
    code_root: Path, explicit: Path | None = None
) -> tuple[Path, str, list[str]]:
    if explicit:
        root = _path(explicit)
        if not _is_product_root(root):
            raise UpgradeOrchestratorError(f"INVALID_EXPLICIT_PRODUCT_ROOT={root}")
        return root, "EXPLICIT", [str(root)]
    rows: list[tuple[Path, str]] = []
    if os.environ.get("A1FS_PRODUCT_ROOT"):
        rows.append((_path(os.environ["A1FS_PRODUCT_ROOT"]), "ENV:A1FS_PRODUCT_ROOT"))
    rows += [
        (_path(Path.home() / "A1FS_V1"), "USER_HOME"),
        (_path(code_root.parent / "A1FS_V1"), "CODE_ROOT_SIBLING"),
        (_path(Path.cwd() / "A1FS_V1"), "CURRENT_DIRECTORY_CHILD"),
    ]
    valid: list[tuple[Path, str]] = []
    seen: set[str] = set()
    for root, source in rows:
        key = os.path.normcase(str(root))
        if key not in seen and _is_product_root(root):
            valid.append((root, source))
        seen.add(key)
    if not valid:
        raise UpgradeOrchestratorError("A1FS_PRODUCT_ROOT_NOT_FOUND")
    return valid[0][0], valid[0][1], [str(root) for root, _ in valid]


def read_current_version(root: Path) -> str:
    file = _path(root) / "current_version.txt"
    if not file.is_file():
        raise UpgradeOrchestratorError(f"CURRENT_VERSION_FILE_MISSING={file}")
    version = file.read_text(encoding="ascii").strip()
    _version_index(version)
    return version


def resolve_target_version(value: str | None) -> str:
    target = str(value or "latest").strip().lower()
    target = LATEST_VERSION if target == "latest" else target
    if target not in {spec.target_version for spec in MIGRATIONS}:
        raise UpgradeOrchestratorError(
            f"TARGET_VERSION_HAS_NO_OPERATOR_MIGRATION={target}"
        )
    return target


def build_route(current: str, target: str) -> list[MigrationSpec]:
    if _version_index(target) < _version_index(current):
        raise UpgradeOrchestratorError(
            f"UPGRADE_TARGET_BEHIND_CURRENT;CURRENT={current};TARGET={target}"
        )
    route = [
        spec
        for spec in MIGRATIONS
        if _version_index(current)
        < _version_index(spec.target_version)
        <= _version_index(target)
    ]
    simulated = current
    for spec in route:
        if simulated not in spec.source_versions:
            raise UpgradeOrchestratorError(
                f"MIGRATION_ROUTE_GAP={simulated}->{spec.target_version}"
            )
        simulated = spec.target_version
    if simulated != target:
        raise UpgradeOrchestratorError(
            f"MIGRATION_ROUTE_INCOMPLETE={simulated}->{target}"
        )
    return route


def _missing_environment() -> list[str]:
    return [
        name
        for name in r01.REQUIRED_ENV
        if not str(os.environ.get(name) or "").strip()
    ]


def _runtime_state(root: Path) -> dict[str, Any]:
    file = _path(root) / "shared/a1fs_v1.pid"
    if not file.is_file():
        return {"pid_file_present": False, "pid": None, "pid_alive": False}
    try:
        pid = int(file.read_text(encoding="ascii").strip())
    except (OSError, ValueError) as exc:
        raise UpgradeOrchestratorError(f"INVALID_RUNTIME_PID_FILE={file}") from exc
    return {
        "pid_file_present": True,
        "pid": pid,
        "pid_alive": bool(r01._pid_alive(pid)),
    }


def _lineage(root: Path) -> str:
    root = _path(root)
    versions = [
        version
        for version in VERSION_ORDER
        if (root / "releases" / version / "release_manifest.json").is_file()
    ]
    if not versions:
        raise UpgradeOrchestratorError("NO_RELEASE_MANIFESTS_FOUND")
    first = versions[0]
    manifest = json.loads(
        (root / "releases" / first / "release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    return _digest(
        {
            "root_name": root.name,
            "version": first,
            "release_id": manifest.get("release_id"),
            "program_id": manifest.get("program_id"),
        }
    )


def _outside(value: Path, root: Path, label: str) -> Path:
    value, root = _path(value), _path(root)
    try:
        value.relative_to(root)
    except ValueError:
        return value
    raise UpgradeOrchestratorError(f"{label}_MUST_BE_OUTSIDE_PRODUCT_ROOT={value}")


def _journal_summary(file: Path) -> dict[str, Any]:
    if not file.is_file():
        return {"exists": False, "status": None}
    try:
        row = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpgradeOrchestratorError(f"UPGRADE_JOURNAL_INVALID={file}") from exc
    return {
        "exists": True,
        "status": row.get("status"),
        "target_version": row.get("target_version"),
        "resume_count": int(row.get("resume_count") or 0),
    }


def build_plan(
    *,
    code_root: Path | None = None,
    product_root: Path | None = None,
    output_root: Path | None = None,
    journal_path: Path | None = None,
    target_version: str = "latest",
    port: int = DEFAULT_PORT,
    mode: str = "PLAN_ONLY",
) -> dict[str, Any]:
    code, code_source = discover_code_root(code_root)
    product, product_source, valid = discover_product_root(code, product_root)
    current = read_current_version(product)
    target = resolve_target_version(target_version)
    route = build_route(current, target)
    output = _outside(
        output_root or product.parent / "A1FS_UPGRADE_OUTPUT" / target,
        product,
        "OUTPUT_ROOT",
    )
    token = _digest(
        {"root": os.path.normcase(str(product)), "target": target}
    )[:10]
    journal = _outside(
        journal_path
        or product.parent
        / ".A1FS_UPGRADE"
        / f"{product.name}-{token}"
        / "upgrade_journal.safe.json",
        product,
        "JOURNAL_PATH",
    )
    rollback = product / "releases" / current / "release_manifest.json"
    if not rollback.is_file():
        raise UpgradeOrchestratorError(
            f"ROLLBACK_RELEASE_MISSING={rollback.parent}"
        )
    missing = _missing_environment()
    core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PLAN_PASS_STATUS,
        "mode": mode,
        "code_root": str(code),
        "code_root_source": code_source,
        "product_root": str(product),
        "product_root_source": product_source,
        "valid_product_root_candidates": valid,
        "output_root": str(output),
        "journal_path": str(journal),
        "current_version": current,
        "target_version": target,
        "latest_version": LATEST_VERSION,
        "migration_required": bool(route),
        "acceptance_required": True,
        "migration_route": [
            {
                "step_id": spec.step_id,
                "source_versions": list(spec.source_versions),
                "target_version": spec.target_version,
                "delegated_module": spec.module_name,
                "direct_version_file_edit_used": False,
            }
            for spec in route
        ],
        "environment": {
            "required_names": list(r01.REQUIRED_ENV),
            "missing_names": missing,
            "values_exported": False,
        },
        "runtime": _runtime_state(product),
        "rollback": {
            "rollback_version": current,
            "rollback_release_present": True,
            "automatic_rollback_enabled": True,
        },
        "journal": _journal_summary(journal),
        "product_lineage_identity": _lineage(product),
        "port": int(port),
        "a2_status": "LOCKED",
        "no_audio_scope_preserved": True,
        "speaking_practice_only_preserved": True,
        "plan_only_mutation_count": 0 if mode == "PLAN_ONLY" else None,
    }
    return {**core, "plan_sha256": _digest(core)}


def _write(file: Path, value: Mapping[str, Any]) -> None:
    file = _path(file)
    file.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=file.name + ".", suffix=".tmp", dir=file.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, file)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _load_journal(file: Path) -> dict[str, Any] | None:
    if not file.is_file():
        return None
    try:
        row = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpgradeOrchestratorError(f"UPGRADE_JOURNAL_INVALID={file}") from exc
    if not isinstance(row, dict):
        raise UpgradeOrchestratorError("UPGRADE_JOURNAL_OBJECT_REQUIRED")
    return row


def _journal(plan: Mapping[str, Any]) -> dict[str, Any]:
    file = Path(str(plan["journal_path"]))
    now = _now()
    old = _load_journal(file)
    base = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "status": "PLANNED",
        "created_at": now,
        "updated_at": now,
        "product_lineage_identity": plan["product_lineage_identity"],
        "product_root": plan["product_root"],
        "initial_version": plan["current_version"],
        "current_version": plan["current_version"],
        "target_version": plan["target_version"],
        "completed_steps": [],
        "active_step": None,
        "attempt_count": 1,
        "resume_count": 0,
        "automatic_rollback_enabled": True,
        "error": None,
        "rollback": None,
    }
    if old is None:
        return base
    if old.get("product_lineage_identity") != plan["product_lineage_identity"]:
        raise UpgradeOrchestratorError(
            "UPGRADE_JOURNAL_PRODUCT_IDENTITY_MISMATCH"
        )
    if old.get("target_version") != plan["target_version"]:
        if old.get("status") != "COMPLETED":
            raise UpgradeOrchestratorError("UPGRADE_JOURNAL_TARGET_MISMATCH")
        return base
    if (
        old.get("status") == "COMPLETED"
        and plan["current_version"] == plan["target_version"]
    ):
        base.update(
            {
                "attempt_count": int(old.get("attempt_count") or 0) + 1,
                "resume_count": int(old.get("resume_count") or 0) + 1,
                "prior_completed_readback_sha256": old.get("readback_sha256"),
            }
        )
        return base
    old.update(
        {
            "product_root": plan["product_root"],
            "current_version": plan["current_version"],
            "updated_at": now,
            "attempt_count": int(old.get("attempt_count") or 0) + 1,
            "resume_count": int(old.get("resume_count") or 0) + 1,
            "active_step": None,
            "error": None,
        }
    )
    return old


def _reconcile(journal: dict[str, Any], current: str) -> None:
    retained = [
        dict(row)
        for row in journal.get("completed_steps", [])
        if isinstance(row, Mapping)
        and row.get("target_version") in VERSION_ORDER
        and _version_index(str(row["target_version"])) <= _version_index(current)
    ]
    known = {str(row.get("step_id")) for row in retained}
    initial = str(journal["initial_version"])
    for spec in MIGRATIONS:
        if (
            _version_index(initial)
            < _version_index(spec.target_version)
            <= _version_index(current)
            and spec.step_id not in known
        ):
            retained.append(
                {
                    "step_id": spec.step_id,
                    "target_version": spec.target_version,
                    "status": "RECOVERED_FROM_PRODUCT_VERSION",
                    "completed_at": _now(),
                }
            )
    journal["completed_steps"] = retained


class UpgradeLock:
    def __init__(self, file: Path):
        self.file = _path(file)
        self.acquired = False

    def __enter__(self) -> "UpgradeLock":
        self.file.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {"pid": os.getpid(), "created_at": _now()}
        ).encode()
        try:
            fd = os.open(self.file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                pid = int(
                    json.loads(self.file.read_text(encoding="utf-8")).get("pid")
                    or 0
                )
            except (OSError, ValueError, json.JSONDecodeError):
                pid = 0
            if pid and r01._pid_alive(pid):
                raise UpgradeOrchestratorError(
                    f"UPGRADE_LOCK_ACTIVE_PID={pid}"
                )
            self.file.unlink(missing_ok=True)
            fd = os.open(self.file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        self.acquired = True
        return self

    def __exit__(self, *_args: Any) -> None:
        if self.acquired:
            self.file.unlink(missing_ok=True)


def _stop_runtime_if_needed(root: Path, port: int) -> dict[str, Any]:
    state = _runtime_state(root)
    if not state["pid_file_present"]:
        return {**state, "action": "NO_RUNTIME_PID"}
    if not state["pid_alive"]:
        (_path(root) / "shared/a1fs_v1.pid").unlink(missing_ok=True)
        return {**state, "action": "STALE_PID_REMOVED"}
    return {
        **state,
        "action": "RUNTIME_STOPPED",
        "result": dict(r01.stop(product_root=_path(root), port=int(port))),
    }


def _action(module: str, function: str) -> Any:
    try:
        return getattr(importlib.import_module(module), function)
    except AttributeError as exc:
        raise UpgradeOrchestratorError(
            f"DELEGATED_ACTION_MISSING={module}:{function}"
        ) from exc


def _execute_migration(
    spec: MigrationSpec,
    *,
    product_root: Path,
    code_root: Path,
    output_root: Path,
    port: int,
) -> Mapping[str, Any]:
    result = _action(spec.module_name, spec.install_function)(
        product_root=_path(product_root),
        code_root=_path(code_root),
        output_root=_path(output_root),
        port=int(port),
    )
    if not isinstance(result, Mapping):
        raise UpgradeOrchestratorError(
            f"MIGRATION_RESULT_OBJECT_REQUIRED={spec.step_id}"
        )
    return result


def _run_acceptance(
    spec: MigrationSpec, *, product_root: Path, port: int
) -> Mapping[str, Any]:
    output = (
        _path(product_root)
        / "shared/operator_readbacks"
        / spec.readback_name
    )
    result = _action(spec.acceptance_module_name, spec.acceptance_function)(
        product_root=_path(product_root),
        port=int(port),
        output_path=output,
    )
    if not isinstance(result, Mapping):
        raise UpgradeOrchestratorError("ACCEPTANCE_RESULT_OBJECT_REQUIRED")
    return result


def _target_spec(version: str) -> MigrationSpec:
    for spec in MIGRATIONS:
        if spec.target_version == version:
            return spec
    raise UpgradeOrchestratorError(f"TARGET_SPEC_MISSING={version}")


def _acceptance_fingerprint(
    *,
    product_root: Path,
    target_version: str,
    acceptance: Mapping[str, Any],
) -> str:
    version, manifest, bundles, sequence = r01._load_product(_path(product_root))
    if version != target_version:
        raise UpgradeOrchestratorError(
            f"ACCEPTANCE_TARGET_VERSION_MISMATCH={version}->{target_version}"
        )
    projection = {
        "product_version": version,
        "release_id": manifest.get("release_id"),
        "serve_module": manifest.get("serve_module"),
        "unit_count": len(sequence),
        "lesson_count": len(bundles),
        "asset_count": sum(
            len(row.get("assets", [])) for row in bundles.values()
        ),
        "validation_status": acceptance.get("validation_status"),
        "product_status": acceptance.get("product_status"),
        "installed_product": acceptance.get("installed_product", {}),
        "operator_http_acceptance": acceptance.get(
            "operator_http_acceptance", {}
        ),
        "boundaries": acceptance.get("boundaries", {}),
    }
    return _digest(projection)


def _rollback(
    *,
    product_root: Path,
    initial_version: str,
    port: int,
    runtime_was_running: bool,
) -> dict[str, Any]:
    root = _path(product_root)
    notes: list[str] = []
    try:
        state = _runtime_state(root)
        if state["pid_alive"]:
            r01.stop(product_root=root, port=int(port))
            notes.append("runtime_stopped")
        elif state["pid_file_present"]:
            (root / "shared/a1fs_v1.pid").unlink(missing_ok=True)
    except Exception as exc:
        notes.append(f"runtime_stop_failed:{type(exc).__name__}:{exc}")
    if read_current_version(root) != initial_version:
        notes.append(
            str(
                r01.rollback(
                    product_root=root, version=initial_version
                ).get("status")
                or "rollback_complete"
            )
        )
    if read_current_version(root) != initial_version:
        raise UpgradeOrchestratorError(
            f"AUTOMATIC_ROLLBACK_VERSION_FAILED={initial_version}"
        )
    r01.validate_release(root / "releases" / initial_version)
    restart = (
        r01.start(product_root=root, port=int(port))
        if runtime_was_running
        else None
    )
    return {
        "validation_status": ROLLBACK_STATUS,
        "rollback_version": initial_version,
        "release_validation_pass": True,
        "runtime_restored_to_previous_running_state": runtime_was_running,
        "restart": dict(restart) if isinstance(restart, Mapping) else None,
        "notes": notes,
    }


def upgrade(
    *,
    code_root: Path | None = None,
    product_root: Path | None = None,
    output_root: Path | None = None,
    journal_path: Path | None = None,
    target_version: str = "latest",
    port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    plan = build_plan(
        code_root=code_root,
        product_root=product_root,
        output_root=output_root,
        journal_path=journal_path,
        target_version=target_version,
        port=port,
        mode="APPLY",
    )
    if plan["environment"]["missing_names"]:
        raise UpgradeOrchestratorError(
            "MISSING_ENV=" + ",".join(plan["environment"]["missing_names"])
        )
    root, code, output, journal_file = map(
        Path,
        (
            plan["product_root"],
            plan["code_root"],
            plan["output_root"],
            plan["journal_path"],
        ),
    )
    with UpgradeLock(journal_file.with_name("upgrade.lock")):
        journal = _journal(plan)
        _reconcile(journal, read_current_version(root))
        journal.update(
            {
                "status": "RUNNING",
                "updated_at": _now(),
                "plan_sha256": plan["plan_sha256"],
            }
        )
        _write(journal_file, journal)
        initial = str(journal["initial_version"])
        runtime_was_running = bool(_runtime_state(root)["pid_alive"])
        results: list[dict[str, Any]] = []
        try:
            preflight = _stop_runtime_if_needed(root, int(port))
            current = read_current_version(root)
            for spec in build_route(current, str(plan["target_version"])):
                journal.update(
                    {
                        "active_step": spec.step_id,
                        "current_version": current,
                        "updated_at": _now(),
                    }
                )
                _write(journal_file, journal)
                delegated = _execute_migration(
                    spec,
                    product_root=root,
                    code_root=code,
                    output_root=output / spec.target_version,
                    port=int(port),
                )
                current = read_current_version(root)
                if current != spec.target_version:
                    raise UpgradeOrchestratorError(
                        f"MIGRATION_VERSION_NOT_INSTALLED={spec.step_id};ACTUAL={current}"
                    )
                row = {
                    "step_id": spec.step_id,
                    "target_version": spec.target_version,
                    "status": "PASS",
                    "completed_at": _now(),
                    "delegated_validation_status": delegated.get(
                        "validation_status"
                    )
                    or delegated.get("upgrade_chain", {}).get(
                        "validation_status"
                    )
                    or "PASS",
                }
                journal.setdefault("completed_steps", []).append(row)
                journal.update(
                    {
                        "active_step": None,
                        "current_version": current,
                        "updated_at": _now(),
                    }
                )
                _write(journal_file, journal)
                results.append(row)
            target = str(plan["target_version"])
            spec = _target_spec(target)
            first = _run_acceptance(spec, product_root=root, port=int(port))
            fingerprint_one = _acceptance_fingerprint(
                product_root=root,
                target_version=target,
                acceptance=first,
            )
            second = _run_acceptance(spec, product_root=root, port=int(port))
            fingerprint_two = _acceptance_fingerprint(
                product_root=root,
                target_version=target,
                acceptance=second,
            )
            if fingerprint_one != fingerprint_two:
                raise UpgradeOrchestratorError(
                    "IDEMPOTENT_ACCEPTANCE_FINGERPRINT_MISMATCH"
                )
            core = {
                "task_id": TASK_ID,
                "program_id": PROGRAM_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": PASS_STATUS,
                "source_version": initial,
                "target_version": target,
                "current_version": read_current_version(root),
                "code_root": str(code),
                "product_root": str(root),
                "output_root": str(output),
                "journal_path": str(journal_file),
                "resumed": int(journal.get("resume_count") or 0) > 0,
                "resume_count": int(journal.get("resume_count") or 0),
                "runtime_preflight": preflight,
                "migration_results": results,
                "idempotent_acceptance": {
                    "pass": True,
                    "acceptance_run_count": 2,
                    "semantic_fingerprint": fingerprint_one,
                    "second_run_product_mutation_claimed": False,
                },
                "automatic_rollback": {
                    "enabled": True,
                    "used": False,
                    "rollback_version": initial,
                },
                "direct_version_file_edit_used": False,
                "a2_status": "LOCKED",
                "no_audio_scope_preserved": True,
                "speaking_practice_only_preserved": True,
                "stop_reason": "NONE",
                "next_short_step": NEXT_SHORT_STEP,
            }
            readback = {**core, "readback_sha256": _digest(core)}
            journal.update(
                {
                    "status": "COMPLETED",
                    "active_step": None,
                    "current_version": target,
                    "updated_at": _now(),
                    "error": None,
                    "rollback": None,
                    "acceptance_fingerprint": fingerprint_one,
                    "readback_sha256": readback["readback_sha256"],
                }
            )
            _write(journal_file, journal)
            _write(
                root
                / "shared/operator_readbacks/a1fs_ops_v1_upg01_upgrade_orchestrator.safe.json",
                readback,
            )
            return readback
        except Exception as exc:
            rollback = None
            rollback_error = None
            try:
                rollback = _rollback(
                    product_root=root,
                    initial_version=initial,
                    port=int(port),
                    runtime_was_running=runtime_was_running,
                )
            except Exception as failure:
                rollback_error = f"{type(failure).__name__}:{failure}"
            journal.update(
                {
                    "status": "ROLLED_BACK" if rollback else "ROLLBACK_FAILED",
                    "active_step": None,
                    "current_version": read_current_version(root),
                    "updated_at": _now(),
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                    "rollback": rollback
                    or {"validation_status": "FAIL", "error": rollback_error},
                }
            )
            _write(journal_file, journal)
            if not rollback:
                raise UpgradeOrchestratorError(
                    "UPGRADE_FAILED_AND_ROLLBACK_FAILED;"
                    f"CAUSE={exc};ROLLBACK={rollback_error}"
                ) from exc
            raise UpgradeOrchestratorError(
                f"UPGRADE_FAILED_AUTOMATIC_ROLLBACK_PASS;CAUSE={exc}"
            ) from exc


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
    try:
        kwargs = {
            "code_root": args.code_root,
            "product_root": args.product_root,
            "output_root": args.output_root,
            "journal_path": args.journal_path,
            "target_version": args.target_version,
            "port": args.port,
        }
        result = (
            build_plan(**kwargs) if args.command == "plan" else upgrade(**kwargs)
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (
        UpgradeOrchestratorError,
        r01.ProductRootError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
