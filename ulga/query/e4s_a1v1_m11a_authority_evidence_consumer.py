#!/usr/bin/env python3
"""Read-only safe/private query for M11A authority evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m11a_authority_evidence_review as builder  # noqa: E402


class AuthorityEvidenceQueryError(ValueError):
    """Fail-closed M11A query error."""


def _load(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    matrix = builder.read_json(root / "authority_evidence_matrix.private.json")
    bank = builder.read_json(root / "reviewed_private_learning_unit_bank.json")
    report = builder.read_json(root / "authority_review_safe_report.json")
    builder._safe_scan(report, name="m11a_authority_review_safe_report")
    return matrix, bank, report


def query(
    matrix: Mapping[str, Any],
    bank: Mapping[str, Any],
    report: Mapping[str, Any],
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
            "source_verification": report["source_verification"],
            "decision_counts": report["decision_counts"],
            "reviewed_unit_count": report["reviewed_unit_count"],
            "reviewed_row_count": report["reviewed_row_count"],
            "criteria_status_counts": report["criteria_status_counts"],
            "claim_boundaries": report["claim_boundaries"],
            "stop_reason": report["stop_reason"],
            "next_short_step": report["next_short_step"],
        }
    rows = list(matrix.get("entries", []))
    if command == "unit":
        matches = [row for row in rows if row.get("grammar_unit_id") == value]
        if not matches:
            raise AuthorityEvidenceQueryError(f"unknown_grammar_unit_id:{value}")
    elif command == "decision":
        if value not in builder.DECISIONS:
            raise AuthorityEvidenceQueryError(f"unknown_decision:{value}")
        matches = [row for row in rows if row.get("automated_decision") == value]
    elif command == "stage":
        matches = [row for row in rows if row.get("internal_stage") == value]
        if not matches:
            raise AuthorityEvidenceQueryError(f"no_units_for_stage:{value}")
    elif command == "row":
        matches = [row for row in rows if value in row.get("canonical_egp_row_ids", [])]
        if not matches:
            raise AuthorityEvidenceQueryError(f"no_units_for_row:{value}")
    else:
        raise AuthorityEvidenceQueryError(f"unknown_command:{command}")

    safe_rows = [
        {
            "grammar_unit_id": row["grammar_unit_id"],
            "internal_stage": row["internal_stage"],
            "canonical_egp_row_ids": row["canonical_egp_row_ids"],
            "cambridge_stage": row["cambridge_stage"],
            "automated_decision": row["automated_decision"],
            "warning_codes": row["warning_codes"],
            "conflict_codes": row["conflict_codes"],
            "criteria_statuses": {
                key: criterion["status"] for key, criterion in row["criteria"].items()
            },
            "evidence_refs": row["evidence_refs"],
            "evidence_record_sha256": row["evidence_record_sha256"],
        }
        for row in matches
    ]
    result: dict[str, Any] = {
        "task_id": report["task_id"],
        "command": command,
        "value": value,
        "match_count": len(matches),
        "units": safe_rows,
    }
    if private:
        by_id = {row["grammar_unit_id"]: row for row in bank.get("reviewed_units", [])}
        result["private_unit_payloads"] = [
            by_id[row["grammar_unit_id"]]["final_private_unit_payload"]
            for row in matches
            if row["grammar_unit_id"] in by_id
        ]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--private", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary")
    unit = sub.add_parser("unit")
    unit.add_argument("--grammar-unit-id", required=True)
    decision = sub.add_parser("decision")
    decision.add_argument("--value", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--value", required=True)
    row = sub.add_parser("row")
    row.add_argument("--egp-row-id", required=True)
    args = parser.parse_args(argv)
    value = None
    if args.command == "unit":
        value = args.grammar_unit_id
    elif args.command in {"decision", "stage"}:
        value = args.value
    elif args.command == "row":
        value = args.egp_row_id
    try:
        matrix, bank, report = _load(args.output_root)
        result = query(matrix, bank, report, args.command, value, private=args.private)
    except (AuthorityEvidenceQueryError, builder.AuthorityEvidenceError, OSError, KeyError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
