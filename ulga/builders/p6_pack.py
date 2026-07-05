from __future__ import annotations


def pack(rows):
    rows = list(rows)
    return {
        "schema_version": "p6_pack.v1",
        "count": len(rows),
        "items": [str(row.get("source_unit_id", "")) for row in rows],
    }
