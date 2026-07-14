#!/usr/bin/env python3
"""Read-only query consumer for recomputed A1/A1+ canonical coverage."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_actual_coverage_recheck import build_report

VALID_STATUSES = {"COVERED", "DRAFT_ONLY", "MISSING"}


def load_coverage() -> dict[str, Any]:
    report = build_report()
    if report.get("validation_status") != "PASS":
        raise RuntimeError("a1_a1plus_coverage_query_source_not_pass")
    return report


def coverage_summary(report: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = dict(report or load_coverage())
    return {
        "scope": source["scope"],
        "validation_status": source["validation_status"],
        "canonical_row_count": source["canonical_row_count"],
        "covered_row_count": source["covered_row_count"],
        "draft_only_row_count": source["draft_only_row_count"],
        "missing_row_count": source["missing_row_count"],
        "unexpected_row_count": source["unexpected_row_count"],
        "coverage_percent": source["coverage_percent"],
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
    }


def get_row(egp_row_id: str, report: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    if not isinstance(egp_row_id, str) or not egp_row_id.strip():
        raise ValueError("egp_row_id_required")
    target = egp_row_id.strip()
    source = report or load_coverage()
    return next((dict(row) for row in source.get("rows", []) if row.get("egp_row_id") == target), None)


def list_rows(status: str | None = None, report: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    source = report or load_coverage()
    rows = [dict(row) for row in source.get("rows", [])]
    if status is None:
        return rows
    normalized = status.strip().upper()
    if normalized not in VALID_STATUSES:
        raise ValueError(f"invalid_coverage_status:{status}")
    return [row for row in rows if row.get("status") == normalized]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--row", default=None)
    parser.add_argument("--status", choices=sorted(VALID_STATUSES), default=None)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = load_coverage()
    if args.row:
        payload = get_row(args.row, report)
        if payload is None:
            print(json.dumps({"validation_status": "NOT_FOUND", "egp_row_id": args.row}, ensure_ascii=False, indent=2))
            return 2
    elif args.status:
        payload = {"status": args.status, "row_count": len(list_rows(args.status, report)), "rows": list_rows(args.status, report)}
    else:
        payload = coverage_summary(report) if args.summary or not args.row else report
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
