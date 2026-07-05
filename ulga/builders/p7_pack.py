from __future__ import annotations


def pack(rows):
    rows = list(rows)
    return {
        "schema_version": "p7_pack.v1",
        "count": len(rows),
        "items": [str(row.get("question_id", "")) for row in rows],
        "print_ready": all(row.get("print_eligible") is True for row in rows),
    }
