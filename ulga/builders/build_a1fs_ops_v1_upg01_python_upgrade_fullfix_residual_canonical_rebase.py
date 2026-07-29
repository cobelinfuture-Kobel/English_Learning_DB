#!/usr/bin/env python3
"""Canonicalize governed residual U01E rows before replaying Python UPG01.

A failed V1.2 admission can leave the 13 governed ``U01E-S03-*`` additive rows
in shared state while the immutable release pointer is rolled back to V1.1.1.
Those rows may contain derived digests or transport metadata from an earlier
approved-bank build. This adapter validates their stable identity, rejects any
row with learner attempts, and atomically rebases only derived fields to the
current canonical overlay before continuing the accepted UPG01 migration.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_upg01_python_upgrade_fullfix as base,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Extends the accepted Python-only UPG01 adapter with a fail-closed canonical "
    "rebase for the 13 governed U01E-S03 residual database identities. Stable asset, "
    "lesson, and skill identity must match; rows referenced by learner attempts are "
    "never changed. Only derived role, digest, canonical contract JSON, and capture "
    "metadata are reconciled to the current approved overlay. It creates no content, "
    "answer, learner attempt, score, mastery state, audio, A2 unlock, external route, "
    "release authority, PowerShell dependency, or parallel migration engine."
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
RESIDUAL_CONTRACT_PREFIX = base.RESIDUAL_CONTRACT_PREFIX

_REBASE_COUNTS = {"lesson_assets": 0, "response_contracts": 0}


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        is not None
    )


def _attempt_count(connection: sqlite3.Connection, asset_key: str) -> int:
    if not _table_exists(connection, "response_attempts"):
        return 0
    return int(
        connection.execute(
            "SELECT COUNT(*) FROM response_attempts WHERE asset_key=?",
            (asset_key,),
        ).fetchone()[0]
    )


def _insert_or_rebase_governed_residual(
    connection: sqlite3.Connection,
    table: str,
    key_column: str,
    key: str,
    values: Sequence[Any],
    sql: str,
) -> str:
    columns = base._TABLE_COLUMNS.get(table)
    if columns is None:
        raise PythonUpgradeFullFixError(f"migration_table_not_supported:{table}")
    row = connection.execute(
        f"SELECT {','.join(columns)} FROM {table} WHERE {key_column}=?",
        (key,),
    ).fetchone()
    if row is None:
        connection.execute(sql, tuple(values))
        return "INSERTED"

    actual = base._normalized_identity(table, tuple(row))
    expected = base._normalized_identity(table, tuple(values))
    if actual == expected:
        return "REUSED_IDENTICAL"
    if not str(key).startswith(RESIDUAL_CONTRACT_PREFIX):
        raise PythonUpgradeFullFixError(
            f"migration_identity_conflict:{table}:{key}"
        )
    if _attempt_count(connection, str(key)):
        raise PythonUpgradeFullFixError(
            f"migration_residual_identity_has_learner_attempts:{table}:{key}"
        )

    if table == "lesson_assets":
        # asset_key, asset_id and lesson_id are stable identity. Role and digest
        # are derived transport/content metadata and may change between approved
        # bank builds without changing the learner item identity.
        if actual[:3] != expected[:3]:
            raise PythonUpgradeFullFixError(
                f"migration_stable_identity_conflict:{table}:{key}"
            )
        connection.execute(
            "UPDATE lesson_assets SET role=?,content_digest=? WHERE asset_key=?",
            (expected[3], expected[4], key),
        )
    elif table == "response_contracts":
        # asset_key, lesson_id and skill are stable identity. The remaining
        # contract representation is a governed derivative of the approved bank.
        if actual[:3] != expected[:3]:
            raise PythonUpgradeFullFixError(
                f"migration_stable_identity_conflict:{table}:{key}"
            )
        connection.execute(
            "UPDATE response_contracts SET role=?,contract_digest=?,"
            "contract_json=?,capture_enabled=? WHERE asset_key=?",
            (expected[3], expected[4], expected[5], expected[6], key),
        )
    else:
        raise PythonUpgradeFullFixError(f"migration_table_not_supported:{table}")

    _REBASE_COUNTS[table] += 1
    return "REUSED_IDENTICAL"


def replay_safe_migrate_database(**kwargs: Any) -> dict[str, Any]:
    _REBASE_COUNTS["lesson_assets"] = 0
    _REBASE_COUNTS["response_contracts"] = 0
    base._insert_or_reuse_exact = _insert_or_rebase_governed_residual
    result = dict(base.replay_safe_migrate_database(**kwargs))
    lesson_rebased = _REBASE_COUNTS["lesson_assets"]
    contract_rebased = _REBASE_COUNTS["response_contracts"]
    result.update(
        {
            "lesson_asset_rows_rebased_to_canonical": lesson_rebased,
            "response_contract_rows_rebased_to_canonical": contract_rebased,
            "residual_canonical_rebase_applied": bool(
                lesson_rebased or contract_rebased
            ),
            "residual_rebase_attempt_guard": "FAIL_CLOSED",
            "residual_stable_identity_policy": (
                "ASSET_KEY_ASSET_ID_LESSON_ID_AND_ASSET_KEY_LESSON_ID_SKILL"
            ),
        }
    )
    if lesson_rebased or contract_rebased:
        result["migration_replay_mode"] = "RESIDUAL_CANONICAL_REBASE"
    return result


def activate() -> None:
    base.activate()
    base._insert_or_reuse_exact = _insert_or_rebase_governed_residual
    s05._core.migrate_database = replay_safe_migrate_database
    s05.migrate_database = replay_safe_migrate_database


def _entry_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(base._entry_metadata(value))
    compatibility = dict(result["residual_u01e_contract_compatibility"])
    compatibility.update(
        {
            "canonical_rebase_enabled": True,
            "stable_identity_drift_allowed": False,
            "learner_attempt_rebase_allowed": False,
            "derived_metadata_rebase_allowed": True,
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
        runtime.core.r01.ProductRootError,
        s01.S01AdmissionError,
        s05._core.S05ReleaseError,
        sqlite3.Error,
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
