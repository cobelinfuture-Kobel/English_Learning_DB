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

SQLite acceptance clones use the R01 SQLite backup helper, which writes through
SQLite's backup API, closes every handle, and verifies ``quick_check`` without a
fresh-file Windows rename.
"""
from __future__ import annotations

import argparse
import gc
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
_CLEANUP_ATTEMPTS = 20
_CLEANUP_BASE_DELAY_SECONDS = 0.05


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


def _windows_safe_copy_sqlite(source: Path, target: Path) -> None:
    """Delegate to the authoritative R01 Windows-safe SQLite backup helper."""
    try:
        r01._copy_sqlite(source, target)
    except r01.ProductRootError as exc:
        raise UpgradeChainError(str(exc)) from exc


def _call_with_windows_safe_sqlite_copy(
    action: Callable[..., Any], /, *args: Any, **kwargs: Any
) -> Any:
    return action(*args, **kwargs)


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
        _remove_tree(work)
    work.mkdir(parents=True)
    return work


def _remove_tree(path: Path) -> None:
    target = Path(path)
    last_error: OSError | None = None
    for attempt in range(_CLEANUP_ATTEMPTS):
        try:
            shutil.rmtree(r01._win32_long_path(target))
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            gc.collect()
            if attempt + 1 >= _CLEANUP_ATTEMPTS:
                break
            time.sleep(min(_CLEANUP_BASE_DELAY_SECONDS * (attempt + 1), 0.5))
    raise UpgradeChainError(f"SHORT_WORK_ROOT_CLEANUP_FAILED:{last_error}") from last_error


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
            stage = work_root / "a"
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
            stage = work_root / "b"
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
            _remove_tree(work_root)


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
            _remove_tree(final_work_root)


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
