#!/usr/bin/env python3
"""Validate static GrammarSkillTree pilot artifacts.

R5-M8 scope:
- Validate grammar_nodes.json
- Validate grammar_edges.json
- Validate grammar_order_table.json
- Validate grammar_coverage_matrix.json
- Validate grammar_query_index.json
- Emit ulga/reports/grammar_artifact_validation_report.json
- Do not generate learner-facing practice
- Do not read or write learner state
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAMMAR_DIR = REPO_ROOT / "ulga" / "grammar"
REPORTS_DIR = REPO_ROOT / "ulga" / "reports"

NODES_PATH = GRAMMAR_DIR / "grammar_nodes.json"
EDGES_PATH = GRAMMAR_DIR / "grammar_edges.json"
ORDER_TABLE_PATH = GRAMMAR_DIR / "grammar_order_table.json"
COVERAGE_MATRIX_PATH = GRAMMAR_DIR / "grammar_coverage_matrix.json"
QUERY_INDEX_PATH = GRAMMAR_DIR / "grammar_query_index.json"
OUTPUT_PATH = REPORTS_DIR / "grammar_artifact_validation_report.json"

REQUIRED_STAGE_KEYS = ["A1", "A1_PLUS", "A2", "A2_PLUS", "B1", "B1_PLUS", "B2"]
REQUIRED_ROLE_KEYS = ["focus", "recycle", "preview", "blocked", "maintenance", "out_of_scope"]
ORDERING_RELATIONS = {"REQUIRES", "PRECEDES"}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pass_check(check_id: str, detail: str) -> dict[str, Any]:
    return {"id": check_id, "status": "PASS", "detail": detail}


def fail_check(check_id: str, detail: str) -> dict[str, Any]:
    return {"id": check_id, "status": "FAIL", "detail": detail}


def add_check(checks: list[dict[str, Any]], check_id: str, condition: bool, detail: str) -> None:
    checks.append(pass_check(check_id, detail) if condition else fail_check(check_id, detail))


def ordered_ids_from_table(order_table: dict[str, Any]) -> list[str]:
    rows = order_table.get("rows", [])
    return [row["grammar_id"] for row in sorted(rows, key=lambda row: row["order_index"])]


def relation_order(edge: dict[str, Any]) -> tuple[str, str] | None:
    relation = edge.get("relation")
    if relation == "REQUIRES":
        return edge["target"], edge["source"]
    if relation == "PRECEDES":
        return edge["source"], edge["target"]
    return None


def validate() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    nodes = load_json(NODES_PATH)
    edges = load_json(EDGES_PATH)
    order_table = load_json(ORDER_TABLE_PATH)
    coverage_matrix = load_json(COVERAGE_MATRIX_PATH)
    query_index = load_json(QUERY_INDEX_PATH)

    add_check(checks, "NODES_IS_LIST", isinstance(nodes, list), "grammar_nodes.json must be a list")
    add_check(checks, "EDGES_IS_LIST", isinstance(edges, list), "grammar_edges.json must be a list")
    add_check(checks, "ORDER_TABLE_IS_OBJECT", isinstance(order_table, dict), "grammar_order_table.json must be an object")
    add_check(checks, "COVERAGE_MATRIX_IS_OBJECT", isinstance(coverage_matrix, dict), "grammar_coverage_matrix.json must be an object")
    add_check(checks, "QUERY_INDEX_IS_OBJECT", isinstance(query_index, dict), "grammar_query_index.json must be an object")

    if not isinstance(nodes, list) or not isinstance(edges, list):
        return finalize_report(nodes, edges, order_table, coverage_matrix, query_index, checks)
    if not isinstance(order_table, dict) or not isinstance(coverage_matrix, dict) or not isinstance(query_index, dict):
        return finalize_report(nodes, edges, order_table, coverage_matrix, query_index, checks)

    node_ids = [node.get("grammar_id") for node in nodes if isinstance(node, dict)]
    node_id_set = set(node_ids)
    add_check(checks, "NODE_IDS_UNIQUE", len(node_ids) == len(node_id_set), "grammar_id values must be unique")
    add_check(checks, "NODE_IDS_NON_EMPTY", all(node_ids), "all nodes must have grammar_id")

    edge_ids = [edge.get("edge_id") for edge in edges if isinstance(edge, dict)]
    add_check(checks, "EDGE_IDS_UNIQUE", len(edge_ids) == len(set(edge_ids)), "edge_id values must be unique")

    unknown_edge_refs = []
    for edge in edges:
        if edge.get("source") not in node_id_set:
            unknown_edge_refs.append(f"{edge.get('edge_id')}:source:{edge.get('source')}")
        if edge.get("target") not in node_id_set:
            unknown_edge_refs.append(f"{edge.get('edge_id')}:target:{edge.get('target')}")
    add_check(checks, "EDGE_REFS_RESOLVE", not unknown_edge_refs, f"unknown edge refs: {unknown_edge_refs}")

    order_rows = order_table.get("rows", [])
    add_check(checks, "ORDER_ROWS_LIST", isinstance(order_rows, list), "order table must contain rows[]")
    ordered_ids = ordered_ids_from_table(order_table) if isinstance(order_rows, list) else []
    add_check(checks, "ORDER_ROWS_COVER_NODES", set(ordered_ids) == node_id_set, "order rows must cover exactly the node set")
    add_check(checks, "ORDER_ROWS_UNIQUE", len(ordered_ids) == len(set(ordered_ids)), "order rows must not duplicate grammar_id")

    order_position = {grammar_id: index for index, grammar_id in enumerate(ordered_ids)}
    ordering_errors = []
    for edge in edges:
        if edge.get("relation") not in ORDERING_RELATIONS:
            continue
        pair = relation_order(edge)
        if pair is None:
            continue
        before, after = pair
        if before in order_position and after in order_position and order_position[before] > order_position[after]:
            ordering_errors.append(f"{edge.get('edge_id')} requires {before} before {after}")
    add_check(checks, "ORDERING_CONSTRAINTS_SATISFIED", not ordering_errors, f"ordering errors: {ordering_errors}")

    coverage_nodes = coverage_matrix.get("node_matrix", [])
    add_check(checks, "COVERAGE_NODE_MATRIX_LIST", isinstance(coverage_nodes, list), "coverage matrix must contain node_matrix[]")
    coverage_ids = [row.get("grammar_id") for row in coverage_nodes if isinstance(row, dict)]
    add_check(checks, "COVERAGE_COVERS_NODES", set(coverage_ids) == node_id_set, "coverage node_matrix must cover exactly the node set")

    stage_matrix = coverage_matrix.get("stage_matrix", [])
    add_check(checks, "COVERAGE_STAGE_MATRIX_LIST", isinstance(stage_matrix, list), "coverage matrix must contain stage_matrix[]")
    stage_keys = [row.get("stage") for row in stage_matrix if isinstance(row, dict)]
    add_check(checks, "COVERAGE_STAGE_KEYS_COMPLETE", stage_keys == REQUIRED_STAGE_KEYS, "coverage stage_matrix must use the canonical stage order")

    stage_role_errors = []
    if isinstance(stage_matrix, list):
        for row in stage_matrix:
            role_counts = row.get("role_counts", {}) if isinstance(row, dict) else {}
            missing_roles = [role for role in REQUIRED_ROLE_KEYS if role not in role_counts]
            if missing_roles:
                stage_role_errors.append(f"{row.get('stage')}:missing:{missing_roles}")
            total = sum(role_counts.get(role, 0) for role in REQUIRED_ROLE_KEYS)
            if total != len(nodes):
                stage_role_errors.append(f"{row.get('stage')}:role_count_total:{total}")
    add_check(checks, "COVERAGE_STAGE_ROLE_COUNTS", not stage_role_errors, f"stage role count errors: {stage_role_errors}")

    query_node_summaries = query_index.get("node_summaries", {})
    add_check(checks, "QUERY_NODE_SUMMARIES_OBJECT", isinstance(query_node_summaries, dict), "query index must contain node_summaries{}")
    query_ids = set(query_node_summaries) if isinstance(query_node_summaries, dict) else set()
    add_check(checks, "QUERY_COVERS_NODES", query_ids == node_id_set, "query node_summaries must cover exactly the node set")

    query_stage_role = query_index.get("by_stage_role", {})
    query_surface_errors = []
    if not isinstance(query_stage_role, dict):
        query_surface_errors.append("by_stage_role_not_object")
    else:
        for stage in REQUIRED_STAGE_KEYS:
            stage_bucket = query_stage_role.get(stage)
            if not isinstance(stage_bucket, dict):
                query_surface_errors.append(f"{stage}:missing_bucket")
                continue
            for role in REQUIRED_ROLE_KEYS:
                if role not in stage_bucket:
                    query_surface_errors.append(f"{stage}:{role}:missing")
    add_check(checks, "QUERY_STAGE_ROLE_SURFACE_COMPLETE", not query_surface_errors, f"query surface errors: {query_surface_errors}")

    learner_state_errors = []
    for node in nodes:
        if node.get("traceability", {}).get("learner_state_write") is not False:
            learner_state_errors.append(f"node:{node.get('grammar_id')}")
    for row in order_rows:
        if row.get("learner_state_write") is not False:
            learner_state_errors.append(f"order:{row.get('grammar_id')}")
    for row in coverage_nodes:
        if row.get("learner_state_write") is not False:
            learner_state_errors.append(f"coverage:{row.get('grammar_id')}")
    if isinstance(query_node_summaries, dict):
        for grammar_id, row in query_node_summaries.items():
            if row.get("learner_state_write") is not False:
                learner_state_errors.append(f"query:{grammar_id}")
    add_check(checks, "LEARNER_STATE_WRITE_FALSE", not learner_state_errors, f"learner_state_write errors: {learner_state_errors}")

    return finalize_report(nodes, edges, order_table, coverage_matrix, query_index, checks)


def finalize_report(
    nodes: Any,
    edges: Any,
    order_table: Any,
    coverage_matrix: Any,
    query_index: Any,
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    fail_count = sum(1 for check in checks if check["status"] != "PASS")
    return {
        "artifact": "grammar_artifact_validation_report",
        "status": "PASS" if fail_count == 0 else "FAIL",
        "generated_by_task": "R5-M8 build static grammar artifact validator",
        "inputs": {
            "nodes": str(NODES_PATH.relative_to(REPO_ROOT)),
            "edges": str(EDGES_PATH.relative_to(REPO_ROOT)),
            "order_table": str(ORDER_TABLE_PATH.relative_to(REPO_ROOT)),
            "coverage_matrix": str(COVERAGE_MATRIX_PATH.relative_to(REPO_ROOT)),
            "query_index": str(QUERY_INDEX_PATH.relative_to(REPO_ROOT)),
        },
        "scope": {
            "learner_facing_practice": False,
            "learner_state_write": False,
            "validator_only": True,
        },
        "summary": {
            "node_count": len(nodes) if isinstance(nodes, list) else None,
            "edge_count": len(edges) if isinstance(edges, list) else None,
            "order_row_count": len(order_table.get("rows", [])) if isinstance(order_table, dict) else None,
            "coverage_node_count": len(coverage_matrix.get("node_matrix", [])) if isinstance(coverage_matrix, dict) else None,
            "query_node_count": len(query_index.get("node_summaries", {})) if isinstance(query_index, dict) else None,
            "check_count": len(checks),
            "fail_count": fail_count,
        },
        "checks": checks,
    }


def main() -> None:
    report = validate()
    write_json(OUTPUT_PATH, report)
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
