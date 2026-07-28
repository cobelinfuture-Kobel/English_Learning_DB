#!/usr/bin/env python3
"""Upgrade supported A1FS local product roots to V1.2 and run operator acceptance.

The chain reuses the already accepted version-specific producers and the R01
atomic update channel. It never edits ``current_version.txt`` directly:

1.0.0 -> 1.1.0 (V1.1 M02)
1.1.0 -> 1.1.1 (M02F exact-sequence FullFix)
1.1.1 -> 1.2.0 (U01E S05)

An already installed 1.2.0 root runs read-only operator acceptance only.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_local_production_operator_acceptance as operator,
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
    "creates no curriculum, item, answer, scoring rule, learner attempt, mastery "
    "decision, audio, A2 unlock, external route, or parallel runtime authority."
)

PROGRAM_ID = operator.PROGRAM_ID
TASK_ID = "A1FS-ONLINE-V1.2-U01E_LocalProductionSequentialUpgradeAndOperatorAcceptance"
SCHEMA_VERSION = "a1fs.online.v1_2.u01e.local_production_upgrade_chain.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_U01E_SEQUENTIAL_UPGRADE_AND_OPERATOR_ACCEPTANCE"
SUPPORTED_VERSIONS = ("1.0.0", "1.1.0", "1.1.1", "1.2.0")
TARGET_VERSION = "1.2.0"
MODULE = __name__


class UpgradeChainError(ValueError):
    """Fail-closed local prerequisite-upgrade error."""


def _current_version(product_root: Path) -> str:
    return operator.s05._core.r01._current_version(Path(product_root).resolve())


def _ensure_stopped(product_root: Path) -> None:
    root = Path(product_root).resolve()
    pid_path = root / "shared/a1fs_v1.pid"
    if not pid_path.is_file():
        return
    pid = int(pid_path.read_text(encoding="ascii").strip())
    if operator.s05._core.r01._pid_alive(pid):
        raise UpgradeChainError(f"STOP_A1FS_BEFORE_UPDATE_PID={pid}")
    pid_path.unlink(missing_ok=True)


def _assert_version(product_root: Path, expected: str) -> None:
    actual = _current_version(product_root)
    if actual != expected:
        raise UpgradeChainError(
            f"UPGRADE_VERSION_SWITCH_FAILED;EXPECTED={expected};ACTUAL={actual}"
        )


def _install_release(
    *, product_root: Path, candidate: Path, target_version: str
) -> Mapping[str, Any]:
    result = operator.s05._core.r01.install_candidate(
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
    steps: list[dict[str, Any]] = []

    current = initial
    if current == "1.0.0":
        stage = output_root / "prerequisites/v1_1_0"
        receipt, _safe = v110.materialize(
            product_root=root,
            code_root=code_root,
            output_path=stage / "m02.private.json",
            report_path=stage / "m02.safe.json",
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
        stage = output_root / "prerequisites/v1_1_1"
        receipt, _safe = v111.materialize(
            product_root=root,
            output_path=stage / "m02f.private.json",
            report_path=stage / "m02f.safe.json",
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

    if current not in {operator.s05._core.SOURCE_VERSION, TARGET_VERSION}:
        raise UpgradeChainError(f"PREREQUISITE_CHAIN_INCOMPLETE={current}")
    return {
        "initial_version": initial,
        "prerequisite_final_version": current,
        "steps": steps,
        "direct_version_file_edit_used": False,
    }


def install_and_accept(
    *,
    product_root: Path,
    code_root: Path,
    output_root: Path,
    port: int,
    candidate: Path | None = None,
) -> dict[str, Any]:
    operator._required_environment()
    chain = upgrade_prerequisites(
        product_root=product_root,
        code_root=code_root,
        output_root=output_root,
    )
    result = operator.install_and_accept(
        product_root=product_root,
        code_root=code_root,
        output_root=output_root,
        port=port,
        candidate=candidate,
    )
    final = _current_version(product_root)
    if final != TARGET_VERSION:
        raise UpgradeChainError(
            f"FINAL_TARGET_VERSION_REQUIRED={TARGET_VERSION};ACTUAL={final}"
        )
    return {
        **result,
        "upgrade_chain": {
            **chain,
            "final_version": final,
            "validation_status": PASS_STATUS,
        },
    }


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
    command.add_argument(
        "--port", type=int, default=operator.s05._core.r01.DEFAULT_PORT
    )
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
        operator.LocalProductionAcceptanceError,
        v110.M02ReleaseError,
        v110.core.ReleaseCoreError,
        v110.acceptance.AcceptanceError,
        v111.M02FFullFixError,
        operator.s05._core.S05ReleaseError,
        operator.s05._core.r01.ProductRootError,
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
