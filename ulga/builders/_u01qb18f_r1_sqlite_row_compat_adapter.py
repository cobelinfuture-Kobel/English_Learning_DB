"""Make U01QB18E private-item parsing compatible with sqlite3.Row.

The first real U01QB18F twelve-form replay reached U01QB18E's binding metadata
path with ``sqlite3.Row`` values.  U01QB18E's helper accepted a Mapping-shaped
contract but called ``row.get(...)``; ``sqlite3.Row`` supports keyed indexing
and ``keys()`` but intentionally has no ``get`` method.  CI fixtures had passed
plain dicts, so the mismatch was not exercised before production replay.

This product-scoped compatibility adapter preserves every U01QB18E semantic
rule and only normalizes an existing ``sqlite3.Row`` to ``dict`` immediately
before the already-approved private-item parser runs.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from ulga.builders import _u01qb18e_micro_scene_semantic_lineage_e2e_adapter as semantic

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Compatibility shim over the existing U01QB18E private-item parser. It only "
    "converts sqlite3.Row to dict before delegating to the unchanged semantic "
    "parser; it creates no content, selector, runtime, planner, database, scoring "
    "authority, Unit02-24 content, audio/Speaking score, or A2 content."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R1_SQLiteRowCompatibilityFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R1_SQLITE_ROW_COMPATIBILITY_FULLFIX"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18F_ActualTwelveFormSemanticReplayEvidenceReadback"

_ORIGINAL_PRIVATE_ITEM = semantic._private_item
_INSTALLED = False


class SQLiteRowCompatibilityError(ValueError):
    """Fail-closed U01QB18F R1 compatibility error."""


def private_item_sqlite_row_compatible(row: Mapping[str, Any] | sqlite3.Row) -> dict[str, Any]:
    """Delegate unchanged parsing after normalizing SQLite's row proxy."""
    normalized: Mapping[str, Any]
    if isinstance(row, sqlite3.Row):
        normalized = dict(row)
    else:
        normalized = row
    return _ORIGINAL_PRIVATE_ITEM(normalized)


def install() -> None:
    global _INSTALLED
    if semantic._private_item is private_item_sqlite_row_compatible:
        _INSTALLED = True
        return
    if semantic._private_item is not _ORIGINAL_PRIVATE_ITEM:
        raise SQLiteRowCompatibilityError(
            "U01QB18E_PRIVATE_ITEM_ALREADY_PATCHED_BY_OTHER_AUTHORITY"
        )
    semantic._private_item = private_item_sqlite_row_compatible
    _INSTALLED = True


def installed() -> bool:
    return _INSTALLED and semantic._private_item is private_item_sqlite_row_compatible
