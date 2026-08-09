from __future__ import annotations

import json
import sqlite3

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb18e_micro_scene_semantic_lineage_e2e_adapter as semantic
from ulga.builders import _u01qb18f_r1_sqlite_row_compat_adapter as compat


def _sqlite_row() -> sqlite3.Row:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        "CREATE TABLE item(item_id TEXT PRIMARY KEY, private_item_json TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO item VALUES(?,?)",
        (
            "ITEM-CAT",
            json.dumps(
                {
                    "lexical_slots": {"noun": "cat"},
                    "stimulus": "A cat is near a tree in the garden.",
                }
            ),
        ),
    )
    row = connection.execute(
        "SELECT item_id,private_item_json FROM item WHERE item_id='ITEM-CAT'"
    ).fetchone()
    assert row is not None
    connection.close()
    return row


def test_product_installs_u01qb18f_r1_sqlite_row_compatibility() -> None:
    assert compat.installed() is True
    assert semantic._private_item is compat.private_item_sqlite_row_compatible
    assert compat.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert compat.A1FS_CONTENT_POLICY_EXEMPTION


def test_private_item_parser_accepts_real_sqlite_row_without_changing_payload() -> None:
    row = _sqlite_row()
    assert not hasattr(row, "get")

    parsed = semantic._private_item(row)

    assert parsed["lexical_slots"]["noun"] == "cat"
    assert parsed["stimulus"] == "A cat is near a tree in the garden."


def test_plain_mapping_contract_remains_unchanged() -> None:
    source = {
        "item_id": "ITEM-BOX",
        "private_item_json": json.dumps({"lexical_slots": {"noun": "box"}}),
    }
    assert semantic._private_item(source) == {"lexical_slots": {"noun": "box"}}
