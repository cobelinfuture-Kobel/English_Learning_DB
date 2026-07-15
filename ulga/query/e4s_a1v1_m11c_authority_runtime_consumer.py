#!/usr/bin/env python3
"""Read-only query for the M11C Authority-reviewed private runtime."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m11c_authority_reviewed_private_runtime as builder  # noqa: E402


class AuthorityRuntimeQueryError(ValueError):
    """Fail-closed M11C query error."""


def _load(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = builder.read_json(root / "runtime_manifest.json")
    query_index = builder.read_json(root / "authority_runtime_query_index.json")
    report = builder.read_json(root / "authority_runtime_safe_report.json")
    return manifest, query_index, report


def query(
    manifest: Mapping[str, Any],
    query_index: Mapping[str, Any],
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
            "private_ready_unit_count": report["private_ready_unit_count"],
            "private_ready_row_count": report["private_ready_row_count"],
            "selectable_item_count": report["selectable_item_count"],
            "excluded_item_count": report["excluded_item_count"],
            "skill_counts": report["skill_counts"],
            "role_counts": report["role_counts"],
            "deferred_units": manifest["deferred_units"],
            "claim_boundaries": report["claim_boundaries"],
            "stop_reason": report["stop_reason"],
            "next_short_step": report["next_short_step"],
        }
    if command == "deferred":
        return {
            "task_id": report["task_id"],
            "match_count": len(manifest["deferred_units"]),
            "deferred_units": manifest["deferred_units"],
        }

    rows = list(query_index.get("items", []))
    if command == "unit":
        matches = [row for row in rows if row.get("grammar_unit_id") == value]
        if not matches:
            if value == builder.DEFERRED_GRAMMAR_ID:
                return {
                    "task_id": report["task_id"],
                    "command": command,
                    "value": value,
                    "match_count": 0,
                    "selectable": False,
                    "deferred_unit": manifest["deferred_units"][0],
                    "items": [],
                    "private_unit_payloads": [] if private else None,
                }
            raise AuthorityRuntimeQueryError(f"unknown_or_nonselectable_grammar_unit:{value}")
    elif command == "row":
        matches = [row for row in rows if value in row.get("canonical_egp_row_ids", [])]
        if not matches:
            raise AuthorityRuntimeQueryError(f"no_selectable_items_for_row:{value}")
    elif command == "stage":
        matches = [row for row in rows if row.get("internal_stage") == value]
        if not matches:
            raise AuthorityRuntimeQueryError(f"no_selectable_items_for_stage:{value}")
    elif command == "skill":
        if value not in {"reading", "writing"}:
            raise AuthorityRuntimeQueryError(f"invalid_skill:{value}")
        matches = [row for row in rows if row.get("skill") == value]
    elif command == "role":
        if value not in {"practice", "assessment"}:
            raise AuthorityRuntimeQueryError(f"invalid_role:{value}")
        matches = [row for row in rows if row.get("item_role") == value]
    elif command == "item":
        matches = [row for row in rows if row.get("item_id") == value]
        if not matches:
            raise AuthorityRuntimeQueryError(f"unknown_or_nonselectable_item:{value}")
    else:
        raise AuthorityRuntimeQueryError(f"unknown_command:{command}")

    result: dict[str, Any] = {
        "task_id": report["task_id"],
        "command": command,
        "value": value,
        "match_count": len(matches),
        "items": matches,
    }
    if private:
        _, authority_bank, _ = builder.m11b.build_artifacts()
        if builder.sha256_value(authority_bank) != manifest["source_hashes"]["m11b_private_bank_sha256"]:
            raise AuthorityRuntimeQueryError("m11b_private_bank_hash_drift")
        requested_units = {str(row["grammar_unit_id"]) for row in matches}
        by_id = {row["grammar_unit_id"]: row for row in authority_bank["reviewed_units"]}
        result["private_unit_payloads"] = [
            by_id[grammar_id]["final_private_unit_payload"]
            for grammar_id in sorted(requested_units)
            if grammar_id in by_id
        ]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=builder.DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--private", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary")
    sub.add_parser("deferred")
    unit = sub.add_parser("unit")
    unit.add_argument("--grammar-unit-id", required=True)
    row = sub.add_parser("row")
    row.add_argument("--egp-row-id", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--value", required=True)
    skill = sub.add_parser("skill")
    skill.add_argument("--value", required=True)
    role = sub.add_parser("role")
    role.add_argument("--value", required=True)
    item = sub.add_parser("item")
    item.add_argument("--id", required=True)
    args = parser.parse_args(argv)
    value = None
    if args.command == "unit":
        value = args.grammar_unit_id
    elif args.command == "row":
        value = args.egp_row_id
    elif args.command in {"stage", "skill", "role"}:
        value = args.value
    elif args.command == "item":
        value = args.id
    try:
        manifest, query_index, report = _load(args.output_root)
        result = query(manifest, query_index, report, args.command, value, private=args.private)
    except (AuthorityRuntimeQueryError, builder.AuthorityRuntimeError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
