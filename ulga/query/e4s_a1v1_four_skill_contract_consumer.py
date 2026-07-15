#!/usr/bin/env python3
"""Read-only metadata query surface for the M07 four-skill closure."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m07_four_skill_contract_closure as builder  # noqa: E402


class FourSkillQueryError(ValueError):
    """Fail-closed M07 query error."""


def load_artifact(path: Path | None = None) -> dict[str, Any]:
    selected = path or builder.OUTPUT_PATH
    if selected.exists():
        return builder.read_json(selected)
    return builder.build_artifact()


def query(
    artifact: Mapping[str, Any],
    command: str,
    value: str | None = None,
) -> dict[str, Any]:
    if command == "summary":
        return {
            "task_id": artifact["task_id"],
            "validation_status": artifact["last_completed_status"],
            "closure_summary": artifact["closure_summary"],
            "skill_states": artifact["skill_states"],
            "system_gate": artifact["system_gate"],
            "next_short_step": artifact["next_short_step"],
        }
    if command == "gate":
        return {
            "task_id": artifact["task_id"],
            "system_gate": artifact["system_gate"],
            "claim_boundaries": artifact["claim_boundaries"],
            "stop_reason": artifact["stop_reason"],
            "next_short_step": artifact["next_short_step"],
        }
    if command == "skill":
        if value not in builder.SKILLS:
            raise FourSkillQueryError(f"unknown_skill:{value}")
        return {
            "task_id": artifact["task_id"],
            "skill": value,
            "state": artifact["skill_states"][value],
        }
    if command == "unit":
        for row in artifact["by_grammar_unit_id"]:
            if row["grammar_unit_id"] == value:
                return {
                    "task_id": artifact["task_id"],
                    "grammar_unit": row,
                }
        raise FourSkillQueryError(f"unknown_grammar_unit_id:{value}")
    if command == "row":
        for row in artifact["by_canonical_egp_row_id"]:
            if row["canonical_egp_row_id"] == value:
                return {
                    "task_id": artifact["task_id"],
                    "canonical_egp_row": row,
                }
        raise FourSkillQueryError(f"unknown_canonical_egp_row_id:{value}")
    if command == "stage":
        unit_rows = [
            row
            for row in artifact["by_grammar_unit_id"]
            if row["internal_stage"] == value
        ]
        if not unit_rows:
            raise FourSkillQueryError(f"unknown_internal_stage:{value}")
        grammar_ids = {row["grammar_unit_id"] for row in unit_rows}
        row_ids = sorted(
            {
                row_id
                for row in unit_rows
                for row_id in row["canonical_egp_row_ids"]
            }
        )
        return {
            "task_id": artifact["task_id"],
            "internal_stage": value,
            "grammar_unit_count": len(unit_rows),
            "canonical_egp_row_count": len(row_ids),
            "shared_item_count": sum(row["shared_item_count"] for row in unit_rows),
            "grammar_unit_ids": sorted(grammar_ids),
            "canonical_egp_row_ids": row_ids,
        }
    raise FourSkillQueryError(f"unknown_command:{command}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary")
    sub.add_parser("gate")
    skill = sub.add_parser("skill")
    skill.add_argument("--value", required=True)
    unit = sub.add_parser("unit")
    unit.add_argument("--grammar-unit-id", required=True)
    row = sub.add_parser("row")
    row.add_argument("--egp-row-id", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--value", required=True)
    args = parser.parse_args(argv)

    value = None
    if args.command == "skill":
        value = args.value
    elif args.command == "unit":
        value = args.grammar_unit_id
    elif args.command == "row":
        value = args.egp_row_id
    elif args.command == "stage":
        value = args.value

    try:
        result = query(load_artifact(args.artifact), args.command, value)
    except (FourSkillQueryError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
