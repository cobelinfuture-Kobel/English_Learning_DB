#!/usr/bin/env python3
"""Build a static GrammarSkillTree order table.

R5-M5 scope:
- Read ulga/grammar/grammar_nodes.json
- Read ulga/grammar/grammar_edges.json
- Emit ulga/grammar/grammar_order_table.json
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
DEFAULT_EDGES_PATH = REPO_ROOT / "ulga" / "grammar" / "grammar_edges.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "ulga" / "grammar" / "grammar_order_table.json"

STAGE_ORDER = {
    "A1": 0,
    "A1_PLUS": 1,
    "A2": 2,
    "A2_PLUS": 3,
    "B1": 4,
    "B1_PLUS": 5,
    "B2": 6,
}

AUTHORITY_ORDER = {
    "accepted": 0,
    "candidate": 1,
    "deprecated": 2,
    "blocked": 3,
}


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


def node_priority(node: dict[str, Any]) -> tuple[int, int, str]:
    return (
        STAGE_ORDER.get(node.get("introduced_stage", "B2"), 999),
        AUTHORITY_ORDER.get(node.get("authority_status", "candidate"), 99),
        node["grammar_id"],
    )


def edge_to_order_constraint(edge: dict[str, Any]) -> tuple[str, str] | None:
    relation = edge.get("relation")
    source = edge.get("source")
    target = edge.get("target")

    if relation == "REQUIRES":
        # Source depends on target, so target must appear before source.
        return target, source

    if relation == "PRECEDES":
        # Source explicitly precedes target.
        return source, target

    if relation == "REINFORCES":
        # Reinforcement can influence recycle views later, but not first-order sequencing.
        return None

    if relation in {"CONTRASTS_WITH", "CONFUSABLE_WITH"}:
        return None

    raise SystemExit(f"Unsupported grammar edge relation: {relation!r}")


def build_order(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[str]:
    node_by_id = {node["grammar_id"]: node for node in nodes}
    if len(node_by_id) != len(nodes):
        raise SystemExit("Duplicate grammar_id values found in grammar_nodes.json")

    adjacency: dict[str, set[str]] = {grammar_id: set() for grammar_id in node_by_id}
    indegree: dict[str, int] = {grammar_id: 0 for grammar_id in node_by_id}

    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        edge_id = edge["edge_id"]

        if source not in node_by_id:
            raise SystemExit(f"Edge {edge_id} has unknown source grammar_id: {source}")
        if target not in node_by_id:
            raise SystemExit(f"Edge {edge_id} has unknown target grammar_id: {target}")

        constraint = edge_to_order_constraint(edge)
        if constraint is None:
            continue

        before, after = constraint
        if after not in adjacency[before]:
            adjacency[before].add(after)
            indegree[after] += 1

    heap: list[tuple[tuple[int, int, str], str]] = [
        (node_priority(node_by_id[grammar_id]), grammar_id)
        for grammar_id, degree in indegree.items()
        if degree == 0
    ]
    heap.sort()

    ordered: list[str] = []
    while heap:
        _, grammar_id = heap.pop(0)
        ordered.append(grammar_id)

        for next_id in sorted(adjacency[grammar_id], key=lambda item: node_priority(node_by_id[item])):
            indegree[next_id] -= 1
            if indegree[next_id] == 0:
                heap.append((node_priority(node_by_id[next_id]), next_id))
                heap.sort()

    if len(ordered) != len(nodes):
        remaining = sorted(grammar_id for grammar_id, degree in indegree.items() if degree > 0)
        raise SystemExit(f"Grammar edge cycle detected; unresolved nodes: {remaining}")

    return ordered


def build_lookup(edges: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    lookup: dict[str, dict[str, list[str]]] = defaultdict(lambda: {
        "prerequisites": [],
        "required_by": [],
        "precedes": [],
        "preceded_by": [],
        "edge_refs": [],
    })

    for edge in edges:
        edge_id = edge["edge_id"]
        source = edge["source"]
        target = edge["target"]
        relation = edge["relation"]

        lookup[source]["edge_refs"].append(edge_id)
        lookup[target]["edge_refs"].append(edge_id)

        if relation == "REQUIRES":
            lookup[source]["prerequisites"].append(target)
            lookup[target]["required_by"].append(source)
        elif relation == "PRECEDES":
            lookup[source]["precedes"].append(target)
            lookup[target]["preceded_by"].append(source)

    for value in lookup.values():
        for key in value:
            value[key] = sorted(set(value[key]))

    return lookup


def build_order_table(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    ordered_ids = build_order(nodes, edges)
    node_by_id = {node["grammar_id"]: node for node in nodes}
    edge_lookup = build_lookup(edges)

    rows = []
    for index, grammar_id in enumerate(ordered_ids, start=1):
        node = node_by_id[grammar_id]
        edge_data = edge_lookup[grammar_id]
        rows.append({
            "order_index": index,
            "grammar_id": grammar_id,
            "label": node["label"],
            "category": node["category"],
            "authority_status": node["authority_status"],
            "cefr_band": node["cefr_band"],
            "introduced_stage": node["introduced_stage"],
            "stage_roles": node["stage_roles"],
            "prerequisites": edge_data["prerequisites"],
            "required_by": edge_data["required_by"],
            "precedes": edge_data["precedes"],
            "preceded_by": edge_data["preceded_by"],
            "edge_refs": edge_data["edge_refs"],
            "source_evidence_count": len(node.get("source_evidence", [])),
            "learner_state_write": node.get("traceability", {}).get("learner_state_write"),
        })

    return {
        "artifact": "grammar_order_table",
        "status": "GENERATED_STATIC_PILOT",
        "generated_by_task": "R5-M5 build static grammar order table generator",
        "inputs": {
            "nodes": str(DEFAULT_NODES_PATH.relative_to(REPO_ROOT)),
            "edges": str(DEFAULT_EDGES_PATH.relative_to(REPO_ROOT)),
        },
        "scope": {
            "learner_facing_practice": False,
            "learner_state_write": False,
            "generator_only": True,
        },
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "ordered_node_count": len(rows),
        },
        "rows": rows,
    }


def main() -> None:
    nodes = load_json(DEFAULT_NODES_PATH)
    edges = load_json(DEFAULT_EDGES_PATH)

    if not isinstance(nodes, list):
        raise SystemExit("grammar_nodes.json must contain a list")
    if not isinstance(edges, list):
        raise SystemExit("grammar_edges.json must contain a list")

    order_table = build_order_table(nodes, edges)
    write_json(DEFAULT_OUTPUT_PATH, order_table)


if __name__ == "__main__":
    main()
