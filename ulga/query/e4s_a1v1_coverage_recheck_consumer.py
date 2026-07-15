#!/usr/bin/env python3
"""Read-only metadata query consumer for the M10 coverage recheck."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m10_coverage_recheck as builder  # noqa: E402


class CoverageQueryError(ValueError):
    """Fail-closed M10 query error."""


def load_report(path: Path | None = None) -> dict[str, Any]:
    selected = path or builder.OUTPUT_PATH
    return builder.read_json(selected) if selected.exists() else builder.build_report()


def query(report: Mapping[str, Any], command: str, value: str | None = None) -> dict[str, Any]:
    rows = list(report.get("rows", []))
    if command == "summary":
        return {
            "task_id": report["task_id"],
            "validation_status": report["validation_status"],
            "coverage_summary": report["coverage_summary"],
            "coverage_layer_counts": report["coverage_layer_counts"],
            "claim_boundaries": report["claim_boundaries"],
            "stop_reason": report["stop_reason"],
            "next_short_step": report["next_short_step"],
        }
    if command == "backlog":
        return {
            "task_id": report["task_id"],
            "backlog": report["backlog"],
            "next_short_step": report["next_short_step"],
        }
    if command == "row":
        matches = [row for row in rows if row["canonical_egp_row_id"] == value]
        if not matches:
            raise CoverageQueryError(f"unknown_canonical_egp_row_id:{value}")
    elif command == "unit":
        matches = [row for row in rows if value in row.get("grammar_unit_ids", [])]
        if not matches:
            raise CoverageQueryError(f"unknown_grammar_unit_id:{value}")
    elif command == "classification":
        if value not in builder.CLASSIFICATIONS:
            raise CoverageQueryError(f"unknown_classification:{value}")
        matches = [row for row in rows if row.get("classification") == value]
    elif command == "stage":
        matches = [row for row in rows if value in row.get("internal_stages", [])]
        if not matches:
            raise CoverageQueryError(f"unknown_internal_stage:{value}")
    elif command == "layer":
        if value not in builder.COVERAGE_LAYERS:
            raise CoverageQueryError(f"unknown_coverage_layer:{value}")
        matches = [row for row in rows if row.get("coverage_layers", {}).get(value) is True]
    else:
        raise CoverageQueryError(f"unknown_command:{command}")
    return {
        "task_id": report["task_id"],
        "command": command,
        "value": value,
        "match_count": len(matches),
        "rows": matches,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary")
    sub.add_parser("backlog")
    row = sub.add_parser("row")
    row.add_argument("--egp-row-id", required=True)
    unit = sub.add_parser("unit")
    unit.add_argument("--grammar-unit-id", required=True)
    classification = sub.add_parser("classification")
    classification.add_argument("--value", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--value", required=True)
    layer = sub.add_parser("layer")
    layer.add_argument("--value", required=True)
    args = parser.parse_args(argv)

    value = None
    if args.command == "row":
        value = args.egp_row_id
    elif args.command == "unit":
        value = args.grammar_unit_id
    elif args.command in {"classification", "stage", "layer"}:
        value = args.value
    try:
        result = query(load_report(args.report), args.command, value)
    except (CoverageQueryError, builder.CoverageRecheckError, OSError, KeyError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
