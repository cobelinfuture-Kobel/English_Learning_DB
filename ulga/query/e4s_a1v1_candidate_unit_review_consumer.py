#!/usr/bin/env python3
"""Read-only safe/private query consumer for M11 candidate-unit review."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m11_candidate_content_review as builder  # noqa: E402


class CandidateReviewQueryError(ValueError):
    """Fail-closed M11 query error."""


def _load(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    report = builder.read_json(root / "candidate_unit_review_safe_report.json")
    bank = builder.read_json(root / "reviewed_private_learning_unit_bank.json")
    builder._safe_scan(report, name="candidate_review_safe_report")
    return report, bank


def query(
    report: Mapping[str, Any],
    bank: Mapping[str, Any],
    command: str,
    value: str | None = None,
    *,
    private: bool = False,
) -> dict[str, Any]:
    if command == "summary":
        return {
            "task_id": report["task_id"],
            "validation_status": report["validation_status"],
            "candidate_unit_count": report["candidate_unit_count"],
            "canonical_egp_row_count": report["canonical_egp_row_count"],
            "decision_counts": report["decision_counts"],
            "reviewed_unit_count": report["reviewed_unit_count"],
            "reviewed_row_count": report["reviewed_row_count"],
            "precheck_distribution": report["precheck_distribution"],
            "claim_boundaries": report["claim_boundaries"],
            "stop_reason": report["stop_reason"],
            "next_resume_task": report["next_resume_task"],
        }
    rows = list(bank.get("reviewed_units", []))
    if command == "unit":
        matches = [row for row in rows if row.get("grammar_unit_id") == value]
        if not matches:
            raise CandidateReviewQueryError(f"unknown_reviewed_grammar_unit_id:{value}")
    elif command == "stage":
        matches = [row for row in rows if row.get("internal_stage") == value]
        if not matches:
            raise CandidateReviewQueryError(f"no_reviewed_units_for_stage:{value}")
    elif command == "row":
        matches = [row for row in rows if value in row.get("canonical_egp_row_ids", [])]
        if not matches:
            raise CandidateReviewQueryError(f"no_reviewed_units_for_row:{value}")
    else:
        raise CandidateReviewQueryError(f"unknown_command:{command}")
    safe_rows = [
        {
            "reviewed_unit_id": row["reviewed_unit_id"],
            "status": row["status"],
            "grammar_unit_id": row["grammar_unit_id"],
            "internal_stage": row["internal_stage"],
            "canonical_egp_row_ids": row["canonical_egp_row_ids"],
            "reviewer_id": row["reviewer_id"],
            "decision_timestamp": row["decision_timestamp"],
            "private_learning_ready": row["private_learning_ready"],
            "mastery_trackable": row["mastery_trackable"],
            "canonical_authority_promotion": row["canonical_authority_promotion"],
        }
        for row in matches
    ]
    result: dict[str, Any] = {
        "task_id": report["task_id"],
        "command": command,
        "value": value,
        "match_count": len(matches),
        "reviewed_units": safe_rows,
    }
    if private:
        result["private_unit_payloads"] = [row["final_private_unit_payload"] for row in matches]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--private", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary")
    unit = sub.add_parser("unit")
    unit.add_argument("--grammar-unit-id", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--value", required=True)
    row = sub.add_parser("row")
    row.add_argument("--egp-row-id", required=True)
    args = parser.parse_args(argv)
    value = None
    if args.command == "unit":
        value = args.grammar_unit_id
    elif args.command == "stage":
        value = args.value
    elif args.command == "row":
        value = args.egp_row_id
    try:
        report, bank = _load(args.output_root)
        result = query(report, bank, args.command, value, private=args.private)
    except (CandidateReviewQueryError, builder.CandidateReviewError, OSError, KeyError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
