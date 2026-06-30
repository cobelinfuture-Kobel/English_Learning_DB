import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DEPENDENCY_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "dependency_graph.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "dependency_graph_summary.json"
QA_AUDIT_PATH = BASE_DIR / "ulga" / "reports" / "dependency_graph_qa_audit.json"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_dependency_graph.py"


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def run_command(command):
    result = subprocess.run(
        command,
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        timeout=180,
    )
    return {
        "command": " ".join(command),
        "returncode": result.returncode,
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "output": (result.stdout + result.stderr).strip(),
    }


def count_cycles(edges):
    graph = defaultdict(list)
    for edge in edges:
        if edge.get("relation") == "REQUIRES" and edge.get("gate_eligible") is True:
            graph[edge["source_node_id"]].append(edge["target_node_id"])

    visiting = set()
    visited = set()
    cycles = []

    def visit(node, path):
        if node in visiting:
            cycle_start = path.index(node) if node in path else 0
            cycles.append(path[cycle_start:] + [node])
            return
        if node in visited:
            return
        visiting.add(node)
        for nxt in graph.get(node, []):
            visit(nxt, path + [nxt])
        visiting.remove(node)
        visited.add(node)

    for node in list(graph):
        visit(node, [node])
    return cycles


def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    graph = read_json(DEPENDENCY_GRAPH_PATH)
    summary = read_json(SUMMARY_PATH)
    edges = graph.get("edges", [])

    validator_result = run_command([sys.executable, str(VALIDATOR_PATH)])
    pytest_result = run_command([sys.executable, "-m", "pytest", "tests/ulga/test_dependency_graph.py", "-q"])

    relation_counts = Counter(edge.get("relation") for edge in edges)
    dependency_class_counts = Counter(edge.get("dependency_class") for edge in edges)
    confidence_method_counts = Counter(edge.get("confidence", {}).get("method") for edge in edges)
    review_status_counts = Counter(edge.get("review_status") for edge in edges)
    gate_eligible_edges = [edge for edge in edges if edge.get("gate_eligible") is True]
    review_required_edges = [
        edge for edge in edges if edge.get("review_status") == "needs_review"
    ]
    orphan_edges = [
        edge
        for edge in edges
        if not edge.get("source_node_id") or not edge.get("target_node_id")
    ]
    theme_misuse_edges = [
        edge
        for edge in edges
        if edge.get("source_node_id", "").startswith("theme:")
        or edge.get("target_node_id", "").startswith("theme:")
    ]
    cross_authority_edges = [
        edge
        for edge in edges
        if not edge.get("source_node_id", "").startswith("grammar:")
        or not edge.get("target_node_id", "").startswith("grammar:")
    ]
    non_requires_edges = [edge for edge in edges if edge.get("relation") != "REQUIRES"]
    soft_gate_edges = [
        edge
        for edge in edges
        if edge.get("gate_eligible") is True
        and edge.get("dependency_class") != "hard_prerequisite"
    ]
    confidence_gate_misuse_edges = [
        edge
        for edge in edges
        if edge.get("gate_eligible") is True
        and edge.get("confidence", {}).get("method")
        in {"heuristic", "manual_review_required"}
    ]
    cycles = count_cycles(edges)

    blocked_findings = []
    warning_findings = []

    if validator_result["status"] != "PASS":
        blocked_findings.append("Dependency graph validator failed.")
    if pytest_result["status"] != "PASS":
        blocked_findings.append("Dependency graph pytest failed.")
    if cycles:
        blocked_findings.append(f"{len(cycles)} circular gate dependency cycle(s) detected.")
    if non_requires_edges:
        blocked_findings.append(f"{len(non_requires_edges)} non-REQUIRES edge(s) emitted.")
    if soft_gate_edges:
        blocked_findings.append(f"{len(soft_gate_edges)} non-hard prerequisite gate edge(s) emitted.")
    if confidence_gate_misuse_edges:
        blocked_findings.append(f"{len(confidence_gate_misuse_edges)} heuristic/manual-review gate edge(s) emitted.")
    if theme_misuse_edges:
        blocked_findings.append(f"{len(theme_misuse_edges)} theme dependency misuse edge(s) emitted.")
    if cross_authority_edges:
        blocked_findings.append(f"{len(cross_authority_edges)} cross-authority edge(s) emitted.")
    if orphan_edges:
        blocked_findings.append(f"{len(orphan_edges)} orphan edge(s) detected.")
    if len(edges) != summary.get("dependency_edge_count"):
        warning_findings.append("Summary dependency_edge_count does not match graph edge count.")

    final_verdict = "PASS" if not blocked_findings else "BLOCKED"

    audit = {
        "audit_stage": "ULGA-S8C",
        "audit_timestamp": timestamp,
        "files_inspected": [
            "ulga/graph/dependency_graph.json",
            "ulga/reports/dependency_graph_summary.json",
            "ulga/validators/validate_dependency_graph.py",
            "tests/ulga/test_dependency_graph.py",
        ],
        "total_edges": len(edges),
        "hard_prerequisites": dependency_class_counts.get("hard_prerequisite", 0),
        "soft_prerequisites": dependency_class_counts.get("soft_prerequisite", 0),
        "gate_eligible_edges": len(gate_eligible_edges),
        "authoritative_edges": confidence_method_counts.get("authoritative", 0),
        "derived_edges": confidence_method_counts.get("derived", 0),
        "review_required_edges": len(review_required_edges),
        "circular_dependency_count": len(cycles),
        "orphan_node_count": len(orphan_edges),
        "relation_breakdown": dict(relation_counts),
        "dependency_class_breakdown": dict(dependency_class_counts),
        "confidence_method_breakdown": dict(confidence_method_counts),
        "review_status_breakdown": dict(review_status_counts),
        "gate_safety": {
            "non_requires_edges": len(non_requires_edges),
            "soft_gate_edges": len(soft_gate_edges),
            "confidence_gate_misuse_edges": len(confidence_gate_misuse_edges),
            "theme_misuse_edges": len(theme_misuse_edges),
            "cross_authority_edges": len(cross_authority_edges),
        },
        "learning_signal_compliance": {
            "learning_signal_policy_used": True,
            "gate_relation_only_requires": len(non_requires_edges) == 0,
            "theme_spiral_edges_generated": graph["graph_metadata"]["learning_signal_compliance"].get("theme_spiral_edges_generated"),
            "learning_signal_graph_generated": graph["graph_metadata"]["learning_signal_compliance"].get("learning_signal_graph_generated"),
            "cefr_only_dependency_generated": graph["graph_metadata"]["learning_signal_compliance"].get("cefr_only_dependency_generated"),
        },
        "validator_result": validator_result,
        "pytest_result": pytest_result,
        "blocked_findings": blocked_findings,
        "warning_findings": warning_findings,
        "final_verdict": final_verdict,
        "recommended_next_task": "ULGA-S8D_DependencyAuthority_QA_Audit",
    }

    write_json(QA_AUDIT_PATH, audit)
    print(f"ULGA Dependency Graph QA Audit: {final_verdict}")
    print(f"Total edges: {len(edges)}")
    print(f"Gate eligible edges: {len(gate_eligible_edges)}")
    print(f"Validator: {validator_result['status']}")
    print(f"Pytest: {pytest_result['status']}")
    return 0 if final_verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
