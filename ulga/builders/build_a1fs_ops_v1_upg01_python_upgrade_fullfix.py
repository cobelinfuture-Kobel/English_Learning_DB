#!/usr/bin/env python3
"""Run UPG01 through one Python-only operator entry.

This adapter keeps the accepted portable/resumable orchestrator and Windows
runtime-shutdown FullFix. It additionally makes the V1.2 S01 admission step
idempotent after a failed additive migration: rollback may switch the immutable
release back to V1.1.1 while intentionally preserving already-added
``U01E-S03-*`` rows in the shared learner database. S01 must still consume the
original eleven Unit01 contracts, not count those governed V1.2 additive rows as
legacy assets.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_ops_v1_upg01_runtime_shutdown_fullfix as runtime
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Provides the canonical Python-only UPG01 operator entry, delegates migration, "
    "journaling, shutdown, acceptance, and rollback to the accepted UPG01 authorities, "
    "and scopes S01 legacy-contract reads to the original eleven asset identities when "
    "governed U01E-S03 additive rows remain after rollback. It creates or deletes no "
    "content, contract, answer, learner attempt, score, mastery state, audio, A2 unlock, "
    "external route, release authority, or parallel migration engine."
)
PROGRAM_ID = runtime.core.PROGRAM_ID
TASK_ID = runtime.core.TASK_ID
SCHEMA_VERSION = runtime.core.SCHEMA_VERSION
PASS_STATUS = runtime.core.PASS_STATUS
PLAN_PASS_STATUS = runtime.core.PLAN_PASS_STATUS
DEFAULT_PORT = runtime.DEFAULT_PORT
RESIDUAL_CONTRACT_PREFIX = "U01E-S03-"
MAX_GOVERNED_RESIDUAL_CONTRACT_COUNT = 13


class PythonUpgradeFullFixError(runtime.RuntimeShutdownFullFixError):
    """Fail-closed Python-entry or residual-contract compatibility error."""


def load_legacy_unit01_contracts(
    database_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Read only the original eleven Unit01 contracts from shared state.

    A previous V1.2 attempt may have committed up to thirteen governed additive
    ``U01E-S03-*`` contracts before a later acceptance failure caused the release
    pointer to roll back. Those rows are forward-compatible shared state and must
    not be deleted. They are excluded only from S01's legacy eleven-asset intake.
    """

    lesson_ids = list(s01.m01.LESSON_IDS.values())
    placeholders = ",".join("?" for _ in lesson_ids)
    with sqlite3.connect(Path(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT asset_key,lesson_id,skill,role,capture_enabled,contract_json "
            f"FROM response_contracts WHERE lesson_id IN ({placeholders}) "
            "ORDER BY lesson_id,asset_key",
            tuple(lesson_ids),
        ).fetchall()

    legacy_rows = [
        row
        for row in rows
        if not str(row["asset_key"]).startswith(RESIDUAL_CONTRACT_PREFIX)
    ]
    residual_rows = [
        row
        for row in rows
        if str(row["asset_key"]).startswith(RESIDUAL_CONTRACT_PREFIX)
    ]
    if len(legacy_rows) != s01.EXPECTED_EXISTING_ASSET_COUNT:
        raise s01.S01AdmissionError(
            f"unit01_legacy_response_contract_count_invalid:{len(legacy_rows)}"
        )
    if len(residual_rows) > MAX_GOVERNED_RESIDUAL_CONTRACT_COUNT:
        raise s01.S01AdmissionError(
            f"unit01_residual_u01e_contract_count_invalid:{len(residual_rows)}"
        )

    assets: list[dict[str, Any]] = []
    contracts: dict[str, dict[str, Any]] = {}
    for row in legacy_rows:
        asset_key = str(row["asset_key"])
        contract = json.loads(str(row["contract_json"]))
        if not isinstance(contract, dict):
            raise s01.S01AdmissionError(f"response_contract_not_object:{asset_key}")
        contract.update(
            {
                "asset_key": asset_key,
                "lesson_id": str(row["lesson_id"]),
                "role": str(row["role"]),
                "capture_enabled": bool(row["capture_enabled"]),
            }
        )
        contracts[asset_key] = contract
        assets.append(
            {
                "asset_key": asset_key,
                "lesson_id": str(row["lesson_id"]),
                "skill": str(row["skill"]),
                "role": str(row["role"]),
            }
        )
    return assets, contracts


def activate() -> None:
    """Activate both accepted shutdown and scoped S01 compatibility adapters."""

    runtime.activate()
    s01.load_contracts = load_legacy_unit01_contracts


def _entry_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **dict(value),
        "operator_entry": "PYTHON_ONLY",
        "powershell_required": False,
        "residual_u01e_contract_compatibility": {
            "enabled": True,
            "legacy_contract_count": s01.EXPECTED_EXISTING_ASSET_COUNT,
            "governed_residual_prefix": RESIDUAL_CONTRACT_PREFIX,
            "residual_rows_deleted": False,
            "legacy_denominator_relaxed": False,
        },
    }


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
        runtime.core.r01.ProductRootError,
        s01.S01AdmissionError,
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
