#!/usr/bin/env python3
"""Upgrade supported A1FS local product roots to V1.2 and run operator acceptance.

The chain reuses the already accepted version-specific producers and the R01
atomic update channel. It never edits ``current_version.txt`` directly:

1.0.0 -> 1.1.0 (V1.1 M02)
1.1.0 -> 1.1.1 (M02F exact-sequence FullFix)
1.1.1 -> 1.2.0 (U01E S05)

An already installed 1.2.0 root runs read-only operator acceptance only.
Temporary release/acceptance work is placed in a short sibling directory of the
product root so deeply nested M7/M8 learner-state snapshots remain below legacy
Windows path limits. Safe diagnostics are copied back to the requested output
root; production learner state is never moved or rewritten by this workaround.

The V1.2 operator/runtime module is intentionally imported only after all V1.0
and V1.1 prerequisite acceptance has completed. The V1.2 facade installs scoped
runtime adapters over legacy modules; importing it before prerequisite acceptance
would make a valid 264-asset V1.1 bootstrap pass through the 277-asset V1.2 gate.

SQLite acceptance clones use direct SQLite backup when the target does not yet
exist, avoiding a Windows rename of a newly closed database. Existing targets
retain replace semantics with bounded PermissionError retry. Every copy must pass
SQLite ``quick_check`` before use.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ulga.builders import (
    build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01,
)
from ulga.builders import (
    build_a1fs_v1_1_m02_unit01_local_product_acceptance_release as v110,
)
from ulga.builders import (
    build_a1fs_v1_1_m02f_exact_sequence_learner_submission_fullfix as v111,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Orchestrates the existing accepted V1.1 M02, M02F, U01E S05, and R01 "
    "atomic update authorities so a supported 1.0.0, 1.1.0, 1.1.1, or 1.2.0 "
    "local product root reaches 1.2.0 without direct version-file edits. It "
    "delays V1.2 runtime adapter import until V1.0/V1.1 prerequisite acceptance "
    "has completed, preventing cross-version bootstrap-policy contamination, and "
    "uses a scoped Windows-safe SQLite backup adapter for acceptance clones. It "
    "creates no curriculum, item, answer, scoring rule, learner attempt, mastery "
    "decision, audio, A2 unlock, external route, or parallel runtime authority."
)

PROGRAM_ID = "A1FS-ONLINE-V1.2-U01E"
TASK_ID = "A1FS-ONLINE-V1.2-U01E_LocalProductionSequentialUpgradeAndOperatorAcceptance"
SCHEMA_VERSION = "a1fs.online.v1_2.u01e.local_production_upgrade_chain.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_U01E_SEQUENTIAL_UPGRADE_AND_OPERATOR_ACCEPTANCE"
SUPPORTED_VERSIONS = ("1.0.0", "1.1.0", "1.1.1", "1.2.0")
TARGET_VERSION = "1.2.0"
MODULE = __name__
_SHORT_WORK_PREFIX = ".A1FS_U12"
_SQLITE_REPLACE_ATTEMPTS = 12
_SQLITE_REPLACE_BASE_DELAY_SECONDS = 0.05


class UpgradeChainError(ValueError):
    """Fail-closed local prerequisite-upgrade error."""


def _current_version(product_root: Path) -> str:
    return r01._current_version(Path(product_root).resolve())


def _ensure_stopped(product_root: Path) -> None:
    root = Path(product_root).resolve()
    pid_path = root / "shared/a1fs_v1.pid"
    if not pid_path.is_file():
        return
    pid = int(pid_path.read_text(encoding="ascii").strip())
    if r01._pid_alive(pid):
        raise UpgradeChainError(f"STOP_A1FS_BEFORE_UPDATE_PID={pid}")
    pid_path.unlink(missing_ok=True)


def _required_environment() -> dict[str, str]:
    values: dict[str, str] = {}
    for name in r01.REQUIRED_ENV:
        value = str(os.environ.get(name) or "").strip()
        if not value:
            raise UpgradeChainError(f"MISSING_ENV={name}")
        values[name] = value
    return values


def _retry_permission(operation: Callable[[], None], *, code: str) -> None:
    last_error: PermissionError | None = None
    for attempt in range(_SQLITE_REPLACE_ATTEMPTS):
        try:
            operation()
            return
        except PermissionError as exc:
            last_error = exc
            if attempt + 1 >= _SQLITE_REPLACE_ATTEMPTS:
                break
            time.sleep(
                min(
                    _SQLITE_REPLACE_BASE_DELAY_SECONDS * (attempt + 1),
                    0.5,
                )
            )
    raise UpgradeChainError(f"{code}:{last_error}") from last_error


def _sqlite_quick_check(path: Path) -> None:
    database = Path(path).resolve()
    if not database.is_file():
        raise UpgradeChainError(f"SQLITE_COPY_TARGET_MISSING={database}")
    with sqlite3.connect(
        f"file:{database.as_posix()}?mode=ro",
        uri=True,
        timeout=5.0,
    ) as connection:
        connection.execute("PRAGMA busy_timeout=5000")
        row = connection.execute("PRAGMA quick_check").fetchone()
    if not row or str(row[0]).casefold() != "ok":
        raise UpgradeChainError(f"SQLITE_COPY_QUICK_CHECK_FAILED={database}")


def _windows_safe_copy_sqlite(source: Path, target: Path) -> None:
    """Copy live SQLite state without relying on a fresh-file Windows rename.

    A new acceptance target is created directly through SQLite backup, because it
    has no previous authority to preserve. When replacing an existing target, a
    validated temporary copy is atomically promoted with bounded PermissionError
    retry. The old target remains untouched if promotion never succeeds.
    """

    source = Path(source).resolve()
    target = Path(target).resolve()
    if not source.is_file():
        raise UpgradeChainError(f"SQLITE_COPY_SOURCE_MISSING={source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target_existed = target.exists()
    destination = (
        target.with_suffix(target.suffix + ".u01e-copying")
        if target_existed
        else target
    )
    if destination.exists() and destination != target:
        _retry_permission(
            lambda: destination.unlink(),
            code="SQLITE_STALE_TEMP_DELETE_FAILED",
        )

    try:
        with sqlite3.connect(
            f"file:{source.as_posix()}?mode=ro",
            uri=True,
            timeout=5.0,
        ) as source_connection:
            source_connection.execute("PRAGMA busy_timeout=5000")
            with sqlite3.connect(destination, timeout=5.0) as target_connection:
                target_connection.execute("PRAGMA busy_timeout=5000")
                source_connection.backup(target_connection)
                target_connection.commit()
        _sqlite_quick_check(destination)

        if target_existed:
            _retry_permission(
                lambda: os.replace(destination, target),
                code="SQLITE_ATOMIC_REPLACE_LOCK_TIMEOUT",
            )
            _sqlite_quick_check(target)
    except Exception:
        cleanup = destination if destination != target or not target_existed else None
        if cleanup is not None and cleanup.exists():
            try:
                _retry_permission(
                    lambda: cleanup.unlink(),
                    code="SQLITE_FAILED_COPY_CLEANUP_LOCK_TIMEOUT",
                )
            except UpgradeChainError:
                pass
        raise


def _call_with_windows_safe_sqlite_copy(
    action: Callable[..., Any], /, *args: Any, **kwargs: Any
) -> Any:
    previous = r01._copy_sqlite
    r01._copy_sqlite = _windows_safe_copy_sqlite
    try:
        return action(*args, **kwargs)
    finally:
        r01._copy_sqlite = previous


def _assert_version(product_root: Path, expected: str) -> None:
    actual = _current_version(product_root)
    if actual != expected:
        raise UpgradeChainError(
            f"UPGRADE_VERSION_SWITCH_FAILED;EXPECTED={expected};ACTUAL={actual}"
        )


def _short_work_root(product_root: Path, phase: str) -> Path:
    root = Path(product_root).resolve()
    normalized_phase = "".join(
        character for character in str(phase).upper() if character.isalnum()
    )[:8]
    if not normalized_phase:
        raise UpgradeChainError("SHORT_WORK_PHASE_REQUIRED")
    token = r01.digest(
        {"product_root": str(root), "phase": normalized_phase}
    )[:8]
    work = (root.parent / f"{_SHORT_WORK_PREFIX}_{normalized_phase}_{token}").resolve()
    try:
        work.relative_to(root)
    except ValueError:
        pass
    else:
        raise UpgradeChainError("SHORT_WORK_ROOT_MUST_BE_OUTSIDE_PRODUCT_ROOT")
    return work


def _prepare_short_work_root(product_root: Path, phase: str) -> Path:
    work = _short_work_root(product_root, phase)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    return work


def _publish_safe_report(source: Path, target: Path) -> None:
    source = Path(source)
    target = Path(target)
    if not source.is_file():
        raise UpgradeChainError(f"SAFE_DIAGNOSTIC_MISSING={source.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _install_release(
    *, product_root: Path, candidate: Path, target_version: str
) -> Mapping[str, Any]:
    result = _call_with_windows_safe_sqlite_copy(
        r01.install_candidate,
        product_root=Path(product_root).resolve(),
        candidate=Path(candidate).resolve(),
        version=target_version,
    )
    _assert_version(product_root, target_version)
    return result


def upgrade_prerequisites(
    *, product_root: Path, code_root: Path, output_root: Path
) -> dict[str, Any]:
    root = Path(product_root).resolve()
    code_root = Path(code_root).resolve()
    output_root = Path(output_root).resolve()
    initial = _current_version(root)
    if initial not in SUPPORTED_VERSIONS:
        raise UpgradeChainError(
            "SUPPORTED_SOURCE_VERSION_REQUIRED="
            + ",".join(SUPPORTED_VERSIONS)
            + f";ACTUAL={initial}"
        )
    if initial != TARGET_VERSION:
        _ensure_stopped(root)
    output_root.mkdir(parents=True, exist_ok=True)
    work_root = _prepare_short_work_root(root, "PRE")
    steps: list[dict[str, Any]] = []
    completed = False

    try:
        current = initial
        if current == "1.0.0":
            stage = work_root / "v110"
            receipt, _safe = _call_with_windows_safe_sqlite_copy(
                v110.materialize,
                product_root=root,
                code_root=code_root,
                output_path=stage / "m02.private.json",
                report_path=stage / "m02.safe.json",
            )
            _publish_safe_report(
                stage / "m02.safe.json",
                output_root / "prerequisites/v1_1_0/m02.safe.json",
            )
            candidate = Path(receipt["runtime_outputs"]["candidate_root"])
            install = _install_release(
                product_root=root,
                candidate=candidate,
                target_version=v110.TARGET_PRODUCT_VERSION,
            )
            steps.append(
                {
                    "task_id": v110.TASK_ID,
                    "source_version": "1.0.0",
                    "target_version": v110.TARGET_PRODUCT_VERSION,
                    "status": str(install.get("status") or "PASS"),
                    "atomic_update_channel_reused": True,
                }
            )
            current = _current_version(root)

        if current == "1.1.0":
            stage = work_root / "v111"
            receipt, _safe = _call_with_windows_safe_sqlite_copy(
                v111.materialize,
                product_root=root,
                output_path=stage / "m02f.private.json",
                report_path=stage / "m02f.safe.json",
            )
            _publish_safe_report(
                stage / "m02f.safe.json",
                output_root / "prerequisites/v1_1_1/m02f.safe.json",
            )
            candidate = Path(receipt["runtime_outputs"]["candidate_root"])
            install = _install_release(
                product_root=root,
                candidate=candidate,
                target_version=v111.TARGET_VERSION,
            )
            steps.append(
                {
                    "task_id": v111.TASK_ID,
                    "source_version": v111.SOURCE_VERSION,
                    "target_version": v111.TARGET_VERSION,
                    "status": str(install.get("status") or "PASS"),
                    "atomic_update_channel_reused": True,
                }
            )
            current = _current_version(root)

        if current not in {v111.TARGET_VERSION, TARGET_VERSION}:
            raise UpgradeChainError(f"PREREQUISITE_CHAIN_INCOMPLETE={current}")
        completed = True
        return {
            "initial_version": initial,
            "prerequisite_final_version": current,
            "steps": steps,
            "direct_version_file_edit_used": False,
            "short_work_root_used": True,
            "temporary_work_root_retained": False,
            "v12_runtime_imported_during_prerequisites": False,
            "windows_sqlite_copy_mode": "DIRECT_NEW_TARGET_VALIDATED_RETRY_EXISTING_TARGET",
        }
    finally:
        if completed and work_root.exists():
            shutil.rmtree(work_root)


def install_and_accept(
    *,
    product_root: Path,
    code_root: Path,
    output_root: Path,
    port: int,
    candidate: Path | None = None,
) -> dict[str, Any]:
    root = Path(product_root).resolve()
    code_root = Path(code_root).resolve()
    output_root = Path(output_root).resolve()
    _required_environment()

    # Deliberately complete V1.0/V1.1 acceptance before importing the V1.2
    # facade, because that facade installs V1.2-only adapters over shared legacy
    # runtime modules in the current Python process.
    chain = upgrade_prerequisites(
        product_root=root,
        code_root=code_root,
        output_root=output_root,
    )
    from ulga.builders import (
        build_a1fs_online_v1_2_u01e_local_production_operator_acceptance as operator,
    )

    final_work_root = _prepare_short_work_root(root, "FINAL")
    completed = False
    try:
        result = _call_with_windows_safe_sqlite_copy(
            operator.install_and_accept,
            product_root=root,
            code_root=code_root,
            output_root=final_work_root,
            port=port,
            candidate=candidate,
        )
        safe_source = final_work_root / "s05.safe.json"
        if safe_source.is_file():
            _publish_safe_report(
                safe_source,
                output_root / "v1_2_0/s05.safe.json",
            )
        final = _current_version(root)
        if final != TARGET_VERSION:
            raise UpgradeChainError(
                f"FINAL_TARGET_VERSION_REQUIRED={TARGET_VERSION};ACTUAL={final}"
            )
        completed = True
        return {
            **result,
            "upgrade_chain": {
                **chain,
                "final_version": final,
                "validation_status": PASS_STATUS,
                "final_short_work_root_used": True,
                "final_temporary_work_root_retained": False,
                "v12_runtime_imported_after_prerequisites": True,
                "windows_sqlite_copy_mode": "DIRECT_NEW_TARGET_VALIDATED_RETRY_EXISTING_TARGET",
            },
        }
    finally:
        if completed and final_work_root.exists():
            shutil.rmtree(final_work_root)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_subparsers(dest="command", required=True).add_parser(
        "install-and-accept"
    )
    command.add_argument("--product-root", type=Path, required=True)
    command.add_argument(
        "--code-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    command.add_argument("--output-root", type=Path, required=True)
    command.add_argument("--port", type=int, default=r01.DEFAULT_PORT)
    command.add_argument("--candidate", type=Path)
    args = parser.parse_args(argv)
    try:
        print(
            json.dumps(
                install_and_accept(
                    product_root=args.product_root,
                    code_root=args.code_root,
                    output_root=args.output_root,
                    port=args.port,
                    candidate=args.candidate,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except (
        UpgradeChainError,
        v110.M02ReleaseError,
        v110.core.ReleaseCoreError,
        v110.acceptance.AcceptanceError,
        v111.M02FFullFixError,
        r01.ProductRootError,
        sqlite3.Error,
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
