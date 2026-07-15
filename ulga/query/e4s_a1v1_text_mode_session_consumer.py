#!/usr/bin/env python3
"""Read-only safe/private query consumer for M08 text-mode progress."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as builder  # noqa: E402


class TextModeQueryError(ValueError):
    """Fail-closed M08 query error."""


def _load(output_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = output_root.resolve()
    report = builder.read_json(root / "text_mode_progress_safe_report.json")
    index = builder.read_json(root / "text_mode_progress_query_index.json")
    builder._safe_scan(
        report,
        name="progress_safe_report",
        forbidden=builder.SAFE_REPORT_FORBIDDEN_KEYS,
    )
    builder._safe_scan(
        index,
        name="progress_query_index",
        forbidden=builder.SAFE_REPORT_FORBIDDEN_KEYS,
    )
    return report, index


def _filter(
    items: list[dict[str, Any]], key: str, value: str
) -> list[dict[str, Any]]:
    rows = [row for row in items if str(row.get(key)) == value]
    if not rows:
        raise TextModeQueryError(f"no_match:{key}:{value}")
    return rows


def query(
    report: Mapping[str, Any],
    index: Mapping[str, Any],
    command: str,
    value: str | None = None,
    *,
    private_ledger: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    items = list(index.get("items", []))
    if command == "summary":
        return {
            "task_id": report["task_id"],
            "validation_status": report["validation_status"],
            "available_item_count": report["available_item_count"],
            "attempt_count": report["attempt_count"],
            "unattempted_item_count": report["unattempted_item_count"],
            "skill_attempt_counts": report["skill_attempt_counts"],
            "role_attempt_counts": report["role_attempt_counts"],
            "outcome_counts": report["outcome_counts"],
            "attempted_unit_count": report["attempted_unit_count"],
            "attempted_row_count": report["attempted_row_count"],
            "pending_human_review_count": report[
                "pending_human_review_count"
            ],
            "claim_boundaries": report["claim_boundaries"],
            "next_short_step": report["next_short_step"],
        }
    if command == "item":
        rows = _filter(items, "item_id", str(value))
    elif command == "unit":
        rows = _filter(items, "grammar_unit_id", str(value))
    elif command == "skill":
        if value not in builder.SKILLS:
            raise TextModeQueryError(f"unknown_skill:{value}")
        rows = _filter(items, "skill", str(value))
    elif command == "role":
        if value not in {"practice", "assessment"}:
            raise TextModeQueryError(f"unknown_role:{value}")
        rows = _filter(items, "item_role", str(value))
    elif command == "stage":
        rows = _filter(items, "internal_stage", str(value))
    elif command == "outcome":
        if value not in builder.OUTCOMES:
            raise TextModeQueryError(f"unknown_outcome:{value}")
        rows = _filter(items, "outcome", str(value))
    elif command == "row":
        rows = [
            row
            for row in items
            if str(value) in row.get("canonical_egp_row_ids", [])
        ]
        if not rows:
            raise TextModeQueryError(f"no_match:canonical_egp_row_id:{value}")
    else:
        raise TextModeQueryError(f"unknown_command:{command}")

    result: dict[str, Any] = {
        "task_id": report["task_id"],
        "command": command,
        "value": value,
        "match_count": len(rows),
        "items": rows,
    }
    if private_ledger is not None:
        entry_by_item = {
            str(entry["item_id"]): entry
            for entry in private_ledger.get("entries", [])
        }
        result["private_progress_entries"] = [
            entry_by_item[row["item_id"]]
            for row in rows
            if row["item_id"] in entry_by_item
        ]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT
    )
    parser.add_argument(
        "--private-ledger",
        type=Path,
        help="Explicitly include private learner responses from this ledger.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary")
    item = sub.add_parser("item")
    item.add_argument("--id", required=True)
    unit = sub.add_parser("unit")
    unit.add_argument("--grammar-unit-id", required=True)
    row = sub.add_parser("row")
    row.add_argument("--egp-row-id", required=True)
    for name in ("skill", "role", "stage", "outcome"):
        command = sub.add_parser(name)
        command.add_argument("--value", required=True)
    args = parser.parse_args(argv)

    value = None
    if args.command == "item":
        value = args.id
    elif args.command == "unit":
        value = args.grammar_unit_id
    elif args.command == "row":
        value = args.egp_row_id
    elif args.command != "summary":
        value = args.value

    try:
        report, index = _load(args.output_root)
        ledger = (
            builder.read_json(args.private_ledger)
            if args.private_ledger
            else None
        )
        result = query(
            report,
            index,
            args.command,
            value,
            private_ledger=ledger,
        )
    except (
        TextModeQueryError,
        builder.TextModeSessionError,
        OSError,
        KeyError,
        ValueError,
    ) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
