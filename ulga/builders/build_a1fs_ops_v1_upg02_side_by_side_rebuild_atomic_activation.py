#!/usr/bin/env python3
"""Rebuild A1FS beside the active root and activate only after full acceptance.

This is deliberately not an in-place upgrade.  The active product root is used
only as a validated seed and shared-state source.  A clean sibling root is built,
upgraded, accepted, and checked for learner-state preservation.  Only then are
the two sibling directories atomically exchanged, with the old root retained as
an operator recovery backup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import threading
import time
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

# Prevent this process and every child runtime from writing transient bytecode
# into immutable release trees.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

from ulga.builders import (  # noqa: E402
    build_a1fs_ops_v1_upg01_release_residual_reconciliation_fullfix as upgrader,
)
from ulga.builders import (  # noqa: E402
    build_a1fs_online_v1_2_1_u01f_patch_release as v121,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Rebuilds an A1FS local product in a clean sibling root, reusing accepted "
    "release, migration, acceptance, shutdown, and rollback authorities. It "
    "copies and verifies existing learner-owned state, disables bytecode writes "
    "inside immutable releases, and performs an atomic directory exchange only "
    "after V1.2.1 acceptance passes. It creates no curriculum, item, answer, "
    "score, mastery decision, audio, A2 unlock, external route, or parallel "
    "runtime/content authority."
)
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = "A1FS-OPS-V1-UPG02_SideBySideRebuildAndAtomicActivation"
SCHEMA_VERSION = "a1fs.ops.v1.upg02.side_by_side_rebuild_atomic_activation.v1"
PASS_STATUS = "PASS_A1FS_OPS_V1_UPG02_SIDE_BY_SIDE_REBUILD_ATOMICALLY_ACTIVATED"
PLAN_STATUS = "PASS_A1FS_OPS_V1_UPG02_SIDE_BY_SIDE_REBUILD_PLAN"
TARGET_VERSION = "1.2.1"
DEFAULT_PORT = upgrader.DEFAULT_PORT
r01 = upgrader.r01

_ALLOWED_MIGRATION_TABLES = {
    "lesson_assets",
    "response_contracts",
    "u01e_coverage_denominators",
    "u01e_asset_target_bindings",
}
_COPY_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    ".git",
)


class SideBySideRebuildError(ValueError):
    """Fail-closed side-by-side rebuild error."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _token(path: Path) -> str:
    return hashlib.sha256(os.path.normcase(str(path.resolve())).encode()).hexdigest()[:10]


def _progress(reporter: Callable[[str], None] | None, message: str) -> None:
    if reporter is not None:
        reporter(message)


@contextmanager
def _heartbeat(
    reporter: Callable[[str], None] | None,
    phase: str,
    interval: float = 10.0,
):
    stop = threading.Event()
    started = time.monotonic()

    def emit() -> None:
        while not stop.wait(interval):
            elapsed = int(time.monotonic() - started)
            _progress(reporter, f"REBUILD_HEARTBEAT phase={phase} elapsed_seconds={elapsed}")

    thread = threading.Thread(target=emit, name="a1fs-rebuild-heartbeat", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=1.0)


def _normalize_cell(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if value is None or isinstance(value, (str, int, float)):
        return value
    return str(value)


def learner_database_projection(database: Path) -> dict[str, Any]:
    """Hash every non-migration table so learner-owned state cannot drift."""

    database = Path(database).resolve()
    with closing(sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        names = [
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            if str(row[0]) not in _ALLOWED_MIGRATION_TABLES
        ]
        tables: dict[str, Any] = {}
        for name in names:
            schema_row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)
            ).fetchone()
            columns = [
                str(row[1])
                for row in connection.execute(f'PRAGMA table_info("{name}")').fetchall()
            ]
            rows = [
                [_normalize_cell(value) for value in tuple(row)]
                for row in connection.execute(f'SELECT * FROM "{name}"').fetchall()
            ]
            rows.sort(key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))
            tables[name] = {
                "schema": None if schema_row is None else str(schema_row[0]),
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
            }
    rendered = json.dumps(tables, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "table_count": len(tables),
        "tables": {name: value["row_count"] for name, value in tables.items()},
        "sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
    }


def _copy_clean_tree(source: Path, target: Path) -> None:
    source, target = Path(source).resolve(), Path(target).resolve()
    if not source.is_dir():
        raise SideBySideRebuildError(f"TREE_SOURCE_MISSING={source}")
    if target.exists():
        raise SideBySideRebuildError(f"TREE_TARGET_ALREADY_EXISTS={target}")
    shutil.copytree(
        r01._win32_long_path(source),
        r01._win32_long_path(target),
        ignore=_COPY_IGNORE,
    )


def _quarantine(path: Path, recovery_root: Path, label: str) -> Path | None:
    path = Path(path)
    if not path.exists():
        return None
    recovery_root.mkdir(parents=True, exist_ok=True)
    destination = recovery_root / label
    index = 1
    while destination.exists():
        destination = recovery_root / f"{label}.{index}"
        index += 1
    os.replace(path, destination)
    return destination


def _prepare_paths(product_root: Path) -> dict[str, Path]:
    source = Path(product_root).resolve()
    token = _token(source)
    parent = source.parent
    return {
        "source": source,
        "pending": parent / f".{source.name}.rebuild-{token}.pending",
        "work": parent / f".{source.name}.rebuild-{token}.work",
        "recovery": parent / f".{source.name}.rebuild-recovery",
    }


def build_plan(*, product_root: Path, code_root: Path, port: int = DEFAULT_PORT) -> dict[str, Any]:
    paths = _prepare_paths(product_root)
    source = paths["source"]
    current = r01._current_version(source)
    source_release = source / "releases" / current
    manifest = r01.validate_release(source_release)
    database = source / "shared/database/learner_runtime.sqlite3"
    auth = source / "shared/auth/auth_state.sqlite3"
    state = source / "shared/learner_state/canonical_learning_state"
    for path in (database, auth, state):
        if not path.exists():
            raise SideBySideRebuildError(f"SOURCE_SHARED_COMPONENT_MISSING={path}")
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PLAN_STATUS,
        "mode": "SIDE_BY_SIDE_REBUILD",
        "source_product_root": str(source),
        "source_version": current,
        "source_release_valid": True,
        "source_product_id": manifest.get("product_id"),
        "pending_product_root": str(paths["pending"]),
        "work_root": str(paths["work"]),
        "recovery_root": str(paths["recovery"]),
        "code_root": str(Path(code_root).resolve()),
        "target_version": TARGET_VERSION,
        "port": int(port),
        "bytecode_writes_disabled": True,
        "in_place_upgrade_used": False,
        "active_root_mutated_before_acceptance": False,
        "old_root_retained_after_activation": True,
    }


def _prepare_clean_seed(
    *,
    source: Path,
    pending: Path,
    recovery: Path,
    reporter: Callable[[str], None] | None,
) -> dict[str, Any]:
    stale = _quarantine(pending, recovery, "stale_pending")
    pending.mkdir(parents=True)
    current = r01._current_version(source)
    _progress(reporter, f"REBUILD_PHASE seed_release version={current}")
    _copy_clean_tree(source / "releases" / current, pending / "releases" / current)
    r01.validate_release(pending / "releases" / current)

    _progress(reporter, "REBUILD_PHASE snapshot_shared_database")
    r01._copy_sqlite(
        source / "shared/database/learner_runtime.sqlite3",
        pending / "shared/database/learner_runtime.sqlite3",
    )
    r01._copy_sqlite(
        source / "shared/auth/auth_state.sqlite3",
        pending / "shared/auth/auth_state.sqlite3",
    )
    _copy_clean_tree(
        source / "shared/learner_state/canonical_learning_state",
        pending / "shared/learner_state/canonical_learning_state",
    )
    config_source = source / "shared/config"
    if config_source.is_dir():
        _copy_clean_tree(config_source, pending / "shared/config")
    else:
        (pending / "shared/config").mkdir(parents=True)
    (pending / "shared/logs").mkdir(parents=True)
    (pending / "shared/operator_readbacks").mkdir(parents=True)
    r01._atomic_text(pending / "current_version.txt", current + "\n")
    r01._write_operator_bundle(pending)
    return {
        "source_version": current,
        "stale_pending_quarantined": None if stale is None else str(stale),
    }


def _unique_backup_root(source: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = source.parent / f"{source.name}.pre_rebuild_{stamp}"
    index = 1
    while candidate.exists():
        candidate = source.parent / f"{source.name}.pre_rebuild_{stamp}.{index}"
        index += 1
    return candidate


def _activate_directory_exchange(
    *, source: Path, pending: Path, target_version: str
) -> dict[str, Any]:
    backup = _unique_backup_root(source)
    failed_new: Path | None = None
    os.replace(source, backup)
    try:
        os.replace(pending, source)
        if r01._current_version(source) != target_version:
            raise SideBySideRebuildError("ACTIVATED_VERSION_INVALID")
        r01.validate_release(source / "releases" / target_version)
    except Exception:
        if source.exists():
            failed_new = source.parent / f"{source.name}.failed_rebuild_{int(time.time())}"
            os.replace(source, failed_new)
        os.replace(backup, source)
        raise
    return {
        "active_product_root": str(source),
        "previous_product_backup_root": str(backup),
        "failed_new_root": None if failed_new is None else str(failed_new),
    }


def rebuild_and_activate(
    *,
    product_root: Path,
    code_root: Path,
    port: int = DEFAULT_PORT,
    reporter: Callable[[str], None] | None = None,
    upgrade_action: Callable[..., Mapping[str, Any]] | None = None,
    final_validator: Callable[[Path], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    plan = build_plan(product_root=product_root, code_root=code_root, port=port)
    paths = _prepare_paths(product_root)
    source, pending, work, recovery = (
        paths["source"], paths["pending"], paths["work"], paths["recovery"]
    )

    upgrader.activate()
    source_runtime = upgrader.runtime.core._runtime_state(source)
    runtime_was_running = bool(source_runtime.get("pid_alive"))
    _progress(reporter, "REBUILD_PHASE stop_source_runtime")
    if source_runtime.get("pid_file_present"):
        upgrader.runtime.robust_stop(product_root=source, port=int(port))

    source_database = source / "shared/database/learner_runtime.sqlite3"
    source_auth = source / "shared/auth/auth_state.sqlite3"
    source_state = source / "shared/learner_state/canonical_learning_state"
    learner_before = learner_database_projection(source_database)
    state_before = r01.directory_digest(source_state)

    stale_work = _quarantine(work, recovery, "stale_work")
    work.mkdir(parents=True)
    seed = _prepare_clean_seed(
        source=source, pending=pending, recovery=recovery, reporter=reporter
    )

    _progress(reporter, "REBUILD_PHASE build_and_accept_new_root")
    action = upgrade_action or upgrader.upgrade
    try:
        with _heartbeat(reporter, "BUILD_AND_ACCEPT_NEW_ROOT"):
            upgrade_result = action(
                product_root=pending,
                code_root=Path(code_root).resolve(),
                output_root=work / "upgrade_output",
                journal_path=work / "upgrade_journal.safe.json",
                target_version=TARGET_VERSION,
                port=int(port),
            )
        pending_runtime = upgrader.runtime.core._runtime_state(pending)
        if pending_runtime.get("pid_file_present"):
            upgrader.runtime.robust_stop(product_root=pending, port=int(port))

        if r01._current_version(pending) != TARGET_VERSION:
            raise SideBySideRebuildError(
                f"REBUILT_VERSION_INVALID={r01._current_version(pending)}"
            )
        r01.validate_release(pending / "releases" / TARGET_VERSION)
        validator = final_validator or v121.installed_product_readback
        final_readback = dict(validator(pending))

        learner_after = learner_database_projection(
            pending / "shared/database/learner_runtime.sqlite3"
        )
        state_after = r01.directory_digest(
            pending / "shared/learner_state/canonical_learning_state"
        )
        if learner_after["sha256"] != learner_before["sha256"]:
            raise SideBySideRebuildError(
                "LEARNER_OWNED_DATABASE_STATE_CHANGED_DURING_REBUILD"
            )
        if state_after != state_before:
            raise SideBySideRebuildError(
                "CANONICAL_LEARNER_STATE_CHANGED_DURING_REBUILD"
            )

        # Acceptance login may write transient auth/session rows. Restore the exact
        # source auth database after all acceptance checks and while runtime is down.
        target_auth = pending / "shared/auth/auth_state.sqlite3"
        target_auth.unlink(missing_ok=True)
        r01._copy_sqlite(source_auth, target_auth)

        if any(path.name == "__pycache__" for path in pending.rglob("__pycache__")):
            raise SideBySideRebuildError("BYTECODE_CACHE_PRESENT_IN_REBUILT_ROOT")
        if any(path.suffix in {".pyc", ".pyo"} for path in pending.rglob("*")):
            raise SideBySideRebuildError("BYTECODE_FILE_PRESENT_IN_REBUILT_ROOT")

        _progress(reporter, "REBUILD_PHASE atomic_directory_activation")
        activation = _activate_directory_exchange(
            source=source, pending=pending, target_version=TARGET_VERSION
        )
        restart: Mapping[str, Any] | None = None
        if runtime_was_running:
            restart = r01.start(product_root=source, port=int(port))

        result_core = {
            "task_id": TASK_ID,
            "program_id": PROGRAM_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "activation_mode": "SIDE_BY_SIDE_REBUILD_ATOMIC_DIRECTORY_EXCHANGE",
            "current_version": TARGET_VERSION,
            "source_version": seed["source_version"],
            "product_root": str(source),
            "old_product_retained": True,
            "in_place_upgrade_used": False,
            "active_root_mutated_before_acceptance": False,
            "bytecode_writes_disabled": True,
            "bytecode_cache_count": 0,
            "learner_database_projection_before": learner_before,
            "learner_database_projection_after": learner_after,
            "learner_owned_database_state_preserved": True,
            "canonical_learner_state_sha256": state_after,
            "canonical_learner_state_preserved": True,
            "auth_database_restored_from_source_after_acceptance": True,
            "upgrade_validation_status": upgrade_result.get("validation_status"),
            "installed_product_readback": final_readback,
            "activation": activation,
            "runtime_was_running": runtime_was_running,
            "runtime_restart": None if restart is None else dict(restart),
            "stale_pending_quarantined": seed["stale_pending_quarantined"],
            "stale_work_quarantined": None if stale_work is None else str(stale_work),
            "stop_reason": "NONE",
        }
        result_core["report_sha256"] = r01.digest(result_core)
        _progress(reporter, "REBUILD_COMPLETE current_version=1.2.1")
        return result_core
    except Exception:
        try:
            pending_runtime = upgrader.runtime.core._runtime_state(pending)
            if pending_runtime.get("pid_file_present"):
                upgrader.runtime.robust_stop(product_root=pending, port=int(port))
        except Exception:
            pass
        # The source root was never exchanged before this point unless activation
        # itself succeeded.  Pending/work roots are retained for diagnostics.
        if runtime_was_running and source.exists():
            try:
                if not upgrader.runtime.core._runtime_state(source).get("pid_alive"):
                    r01.start(product_root=source, port=int(port))
            except Exception:
                pass
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-root", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)

    def reporter(message: str) -> None:
        print(message, flush=True)

    try:
        if args.plan_only:
            result = build_plan(
                product_root=args.product_root,
                code_root=args.code_root,
                port=args.port,
            )
        else:
            result = rebuild_and_activate(
                product_root=args.product_root,
                code_root=args.code_root,
                port=args.port,
                reporter=reporter,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
        return 0
    except (
        SideBySideRebuildError,
        upgrader.PythonUpgradeFullFixError,
        upgrader.runtime.RuntimeShutdownFullFixError,
        upgrader.runtime.core.UpgradeOrchestratorError,
        r01.ProductRootError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{type(exc).__name__}:{exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
