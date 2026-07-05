#!/usr/bin/env python3
"""Build a static GrammarSkillTree query index.

R5-M7 scope:
- Read ulga/grammar/grammar_nodes.json
- Read ulga/grammar/grammar_order_table.json
- Read ulga/grammar/grammar_coverage_matrix.json
- Emit ulga/grammar/grammar_query_index.json
- Do not generate learner-facing practice
- Do not read or write learner state
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NODES_PATH = REPO_ROOT / "ulga" / "grammar" / "grammar_nodes.json"
DEFAULT_ORDER_TABLE_PATH = REPO_ROOT / "ulga" / "grammar" / "grammar_order_table.json"
DEFAULT_COVERAGE_MATRIX_PATH = REPO_ROOT / "ulga" / "grammar" / "grammar_coverage_matrix.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "ulga" / "grammar" / "grammar_query_index.json"

STAGES = ["A1", "A1_PLUS", "A2", "A2_PLUS", "B1", "B1_PLUS", "B2"]
ROLES = ["focus", "recycle", "preview", "blocked", "maintenance", "out_of_scope"]


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing input file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise SystemExit(f"{label} must be a list")
    if not all(isinstance(item, dict) for item in value):
        raise SystemExit(f"{label} must contain only objects")
    return value


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be an object")
    return value


def node_by_id(nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {node["grammar_id"]: node for node in nodes}
    if len(out) != len(nodes):
        raise SystemExit("Duplicate grammar_id values found in grammar_nodes.json")
    return out


def order_lookup(order_table: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = order_table.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("grammar_order_table.json must contain rows[]")
    out = {row["grammar_id"]: row for row in rows}
    if len(out) != len(rows):
        raise SystemExit("Duplicate grammar_id values found in grammar_order_table.json rows")
    return out


def coverage_lookup(coverage_matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = coverage_matrix.get("node_matrix")
    if not isinstance(rows, list):
        raise SystemExit("grammar_coverage_matrix.json must contain node_matrix[]")
    out = {row["grammar_id"]: row for row in rows}
    if len(out) != len(rows):
        raise SystemExit("Duplicate grammar_id values found in grammar_coverage_matrix.json node_matrix")
    return out


def empty_stage_role_index() -> dict[str, dict[str, list[str]]]:
    return {stage: {role: [] for role in ROLES} for stage in STAGES}


def build_query_index(
    nodes: list[dict[str, Any]],
    order_table: dict[str, Any],
    coverage_matrix: dict[str, Any],
) -> dict[str, Any]:
    nodes_by_id = node_by_id(nodes)
    order_by_id = order_lookup(order_table)
    coverage_by_id = coverage_lookup(coverage_matrix)

    missing_order = sorted(set(nodes_by_id) - set(order_by_id))
    missing_coverage = sorted(set(nodes_by_id) - set(coverage_by_id))
    if missing_order:
        raise SystemExit(f"Nodes missing from grammar_order_table.json: {missing_order}")
    if missing_coverage:
        raise SystemExit(f"Nodes missing from grammar_coverage_matrix.json: {missing_coverage}")

    ordered_ids = [row["grammar_id"] for row in sorted(order_table["rows"], key=lambda row: row["order_index"])]

    by_stage_role = empty_stage_role_index()
    by_category: dict[str, list[str]] = defaultdict(list)
    by_stage: dict[str, list[str]] = {stage: [] for stage in STAGES}
    by_authority_status: dict[str, list[str]] = defaultdict(list)
    node_summaries: dict[str, dict[str, Any]] = {}

    for grammar_id in ordered_ids:
        node = nodes_by_id[grammar_id]
        coverage = coverage_by_id[grammar_id]
        order_row = order_by_id[grammar_id]
        stage_roles = coverage["stage_roles"]

        by_category[node["category"]].append(grammar_id)
        by_authority_status[node["authority_status"]].append(grammar_id)

        for stage in STAGES:
            role = stage_roles.get(stage, "out_of_scope")
            if role not in ROLES:
                raise SystemExit(f"Unsupported role {role!r} for {grammar_id} at {stage}")
            by_stage_role[stage][role].append(grammar_id)
            if role != "out_of_scope":
                by_stage[stage].append(grammar_id)

        node_summaries[grammar_id] = {
            "order_index": order_row["order_index"],
            "label": node["label"],
            "category": node["category"],
            "authority_status": node["authority_status"],
            "introduced_stage": node["introduced_stage"],
            "cefr_band": node["cefr_band"],
            "stage_roles": stage_roles,
            "prerequisites": order_row.get("prerequisites", []),
            "required_by": order_row.get("required_by", []),
            "precedes": order_row.get("precedes", []),
            "preceded_by": order_row.get("preceded_by", []),
            "learner_state_write": coverage.get("learner_state_write"),
        }

    return {
        "artifact": "grammar_query_index",
        "status": "GENERATED_STATIC_PILOT",
        "generated_by_task": "R5-M7 build static grammar query index generator",
        "inputs": {
            "nodes": str(DEFAULT_NODES_PATH.relative_to(REPO_ROOT)),
            "order_table": str(DEFAULT_ORDER_TABLE_PATH.relative_to(REPO_ROOT)),
            "coverage_matrix": str(DEFAULT_COVERAGE_MATRIX_PATH.relative_to(REPO_ROOT)),
        },
        "scope": {
            "learner_facing_practice": False,
            "learner_state_write": False,
            "generator_only": True,
        },
        "query_surfaces": {
            "by_stage": "stage -> grammar_id[]",
            "by_stage_role": "stage -> role -> grammar_id[]",
            "by_category": "category -> grammar_id[]",
            "by_authority_status": "authority_status -> grammar_id[]",
            "node_summaries": "grammar_id -> static lookup summary",
        },
        "summary": {
            "node_count": len(ordered_ids),
            "stage_count": len(STAGES),
            "category_count": len(by_category),
            "authority_status_count": len(by_authority_status),
        },
        "by_stage": {stage: sorted(set(ids), key=ordered_ids.index) for stage, ids in by_stage.items()},
        "by_stage_role": by_stage_role,
        "by_category": dict(sorted((key, value) for key, value in by_category.items())),
        "by_authority_status": dict(sorted((key, value) for key, value in by_authority_status.items())),
        "node_summaries": node_summaries,
    }


def main() -> None:
    nodes = require_list(load_json(DEFAULT_NODES_PATH), "grammar_nodes.json")
    order_table = require_object(load_json(DEFAULT_ORDER_TABLE_PATH), "grammar_order_table.json")
    coverage_matrix = require_object(load_json(DEFAULT_COVERAGE_MATRIX_PATH), "grammar_coverage_matrix.json")
    query_index = build_query_index(nodes, order_table, coverage_matrix)
    write_json(DEFAULT_OUTPUT_PATH, query_index)


if __name__ == "__main__":
    main()
