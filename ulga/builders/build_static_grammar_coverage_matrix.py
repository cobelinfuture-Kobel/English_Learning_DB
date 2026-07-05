#!/usr/bin/env python3
"""Build a static GrammarSkillTree coverage matrix.

R5-M6 scope:
- Read ulga/grammar/grammar_nodes.json
- Read ulga/grammar/grammar_order_table.json
- Emit ulga/grammar/grammar_coverage_matrix.json
- Do not generate learner-facing practice
- Do not read or write learner state
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NODES_PATH = REPO_ROOT / "ulga" / "grammar" / "grammar_nodes.json"
DEFAULT_ORDER_TABLE_PATH = REPO_ROOT / "ulga" / "grammar" / "grammar_order_table.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "ulga" / "grammar" / "grammar_coverage_matrix.json"

STAGES = ["A1", "A1_PLUS", "A2", "A2_PLUS", "B1", "B1_PLUS", "B2"]
ROLE_KEYS = ["focus", "recycle", "preview", "blocked", "maintenance", "out_of_scope"]


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


def require_order_rows(order_table: dict[str, Any]) -> list[dict[str, Any]]:
    rows = order_table.get("rows")
    if not isinstance(rows, list) or not all(isinstance(item, dict) for item in rows):
        raise SystemExit("grammar_order_table.json must contain rows[] objects")
    return rows


def build_node_lookup(nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    node_by_id = {node["grammar_id"]: node for node in nodes}
    if len(node_by_id) != len(nodes):
        raise SystemExit("Duplicate grammar_id values found in grammar_nodes.json")
    return node_by_id


def validate_order_table(node_by_id: dict[str, dict[str, Any]], order_rows: list[dict[str, Any]]) -> None:
    ordered_ids = [row.get("grammar_id") for row in order_rows]
    if len(set(ordered_ids)) != len(ordered_ids):
        raise SystemExit("Duplicate grammar_id values found in grammar_order_table.json rows")

    missing_from_nodes = sorted(grammar_id for grammar_id in ordered_ids if grammar_id not in node_by_id)
    if missing_from_nodes:
        raise SystemExit(f"Order-table rows reference unknown grammar IDs: {missing_from_nodes}")

    missing_from_order = sorted(grammar_id for grammar_id in node_by_id if grammar_id not in set(ordered_ids))
    if missing_from_order:
        raise SystemExit(f"grammar_nodes.json IDs missing from order table: {missing_from_order}")


def empty_role_bucket() -> dict[str, list[str]]:
    return {role: [] for role in ROLE_KEYS}


def build_stage_matrix(ordered_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stage_rows: list[dict[str, Any]] = []

    for stage in STAGES:
        role_to_ids = empty_role_bucket()
        authority_counts: Counter[str] = Counter()

        for node in ordered_nodes:
            grammar_id = node["grammar_id"]
            role = node.get("stage_roles", {}).get(stage, "out_of_scope")
            if role not in ROLE_KEYS:
                raise SystemExit(f"Unsupported stage role {role!r} for {grammar_id} at {stage}")

            role_to_ids[role].append(grammar_id)
            authority_counts[node["authority_status"]] += 1

        stage_rows.append({
            "stage": stage,
            "node_count": len(ordered_nodes),
            "role_counts": {role: len(role_to_ids[role]) for role in ROLE_KEYS},
            "roles": role_to_ids,
            "authority_status_counts": dict(sorted(authority_counts.items())),
        })

    return stage_rows


def build_node_matrix(ordered_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, node in enumerate(ordered_nodes, start=1):
        rows.append({
            "order_index": index,
            "grammar_id": node["grammar_id"],
            "label": node["label"],
            "category": node["category"],
            "authority_status": node["authority_status"],
            "introduced_stage": node["introduced_stage"],
            "cefr_band": node["cefr_band"],
            "stage_roles": {stage: node.get("stage_roles", {}).get(stage, "out_of_scope") for stage in STAGES},
            "source_evidence_count": len(node.get("source_evidence", [])),
            "learner_state_write": node.get("traceability", {}).get("learner_state_write"),
        })
    return rows


def build_coverage_matrix(nodes: list[dict[str, Any]], order_table: dict[str, Any]) -> dict[str, Any]:
    node_by_id = build_node_lookup(nodes)
    order_rows = require_order_rows(order_table)
    validate_order_table(node_by_id, order_rows)

    ordered_nodes = [node_by_id[row["grammar_id"]] for row in sorted(order_rows, key=lambda row: row["order_index"])]
    stage_matrix = build_stage_matrix(ordered_nodes)
    node_matrix = build_node_matrix(ordered_nodes)

    category_counts = Counter(node["category"] for node in ordered_nodes)
    authority_counts = Counter(node["authority_status"] for node in ordered_nodes)

    return {
        "artifact": "grammar_coverage_matrix",
        "status": "GENERATED_STATIC_PILOT",
        "generated_by_task": "R5-M6 build grammar coverage matrix generator",
        "inputs": {
            "nodes": str(DEFAULT_NODES_PATH.relative_to(REPO_ROOT)),
            "order_table": str(DEFAULT_ORDER_TABLE_PATH.relative_to(REPO_ROOT)),
        },
        "scope": {
            "learner_facing_practice": False,
            "learner_state_write": False,
            "generator_only": True,
        },
        "summary": {
            "node_count": len(ordered_nodes),
            "stage_count": len(STAGES),
            "category_counts": dict(sorted(category_counts.items())),
            "authority_status_counts": dict(sorted(authority_counts.items())),
        },
        "stage_matrix": stage_matrix,
        "node_matrix": node_matrix,
    }


def main() -> None:
    nodes = require_list(load_json(DEFAULT_NODES_PATH), "grammar_nodes.json")
    order_table = load_json(DEFAULT_ORDER_TABLE_PATH)
    if not isinstance(order_table, dict):
        raise SystemExit("grammar_order_table.json must contain an object")

    coverage_matrix = build_coverage_matrix(nodes, order_table)
    write_json(DEFAULT_OUTPUT_PATH, coverage_matrix)


if __name__ == "__main__":
    main()
