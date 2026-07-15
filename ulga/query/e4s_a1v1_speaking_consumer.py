#!/usr/bin/env python3
"""Read-only CLI for local E4S A1V1 Speaking V1 artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/speaking/m06"


def _read(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("artifact_root_not_object")
    return value


def _rows(item: dict[str, Any]) -> list[str]:
    return item.get("canonical_egp_row_ids", [])


def _matches(items: list[dict[str, Any]], field: str, value: str) -> list[dict[str, Any]]:
    if field == "canonical_egp_row_ids":
        return [item for item in items if value in _rows(item)]
    return [item for item in items if item.get(field) == value]


def _summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "items": len(items),
        "units": len({item["grammar_unit_id"] for item in items}),
        "rows": len({row for item in items for row in _rows(item)}),
        "roles": dict(sorted(Counter(item["item_role"] for item in items).items())),
        "dimensions": dict(sorted(Counter(item["evidence_dimension"] for item in items).items())),
        "stages": dict(sorted(Counter(item["internal_stage"] for item in items).items())),
        "capture_statuses": dict(sorted(Counter(item.get("capture_status", "UNKNOWN") for item in items).items())),
        "review_decisions": dict(sorted(Counter(item.get("review_decision", "PENDING") for item in items).items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--private", action="store_true", help="Read the private review bank.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary")
    item = sub.add_parser("item"); item.add_argument("--id", required=True)
    unit = sub.add_parser("unit"); unit.add_argument("--grammar-unit-id", required=True)
    row = sub.add_parser("row"); row.add_argument("--egp-row-id", required=True)
    for name in ("role", "dimension", "stage", "status"):
        command = sub.add_parser(name); command.add_argument("--value", required=True)
    args = parser.parse_args(argv)
    try:
        filename = "speaking_private_review_bank.json" if args.private else "speaking_query_index.private.json"
        artifact = _read(args.output_root / filename)
        items = artifact.get("items", [])
        if args.command == "summary":
            result: Any = _summary(items)
        else:
            if args.command == "item":
                field, value = "shared_item_id", args.id
            elif args.command == "unit":
                field, value = "grammar_unit_id", args.grammar_unit_id
            elif args.command == "row":
                field, value = "canonical_egp_row_ids", args.egp_row_id
            else:
                field = {
                    "role": "item_role",
                    "dimension": "evidence_dimension",
                    "stage": "internal_stage",
                    "status": "capture_status",
                }[args.command]
                value = args.value
            result = _matches(items, field, value)
            if args.command == "item":
                if len(result) != 1:
                    print(f"unknown_or_duplicate_item:{value}", file=sys.stderr)
                    return 2
                result = result[0]
            elif not result:
                print(f"no_matches:{args.command}:{value}", file=sys.stderr)
                return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
