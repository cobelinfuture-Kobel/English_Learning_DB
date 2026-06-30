import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

THEME_SPIRAL_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "theme_spiral_graph.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "theme_spiral_graph_summary.json"
QA_AUDIT_PATH = BASE_DIR / "ulga" / "reports" / "theme_spiral_graph_qa_audit.json"
STAGE_GAP_REVIEW_QUEUE_PATH = BASE_DIR / "ulga" / "reports" / "theme_spiral_stage_gap_review_queue.json"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_theme_spiral_graph.py"

CEFR_ORDER = ["A1", "A1_plus", "A2", "A2_plus", "B1", "B1_plus", "B2", "B2_plus", "C1"]
CEFR_RANK = {level: index for index, level in enumerate(CEFR_ORDER)}


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
        graph[edge["source_stage_id"]].append(edge["target_stage_id"])

    visiting = set()
    visited = set()
    cycles = []

    def visit(node, path):
        if node in visiting:
            start = path.index(node) if node in path else 0
            cycles.append(path[start:] + [node])
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
    graph = read_json(THEME_SPIRAL_GRAPH_PATH)
    summary = read_json(SUMMARY_PATH)
    stage_gap_review_queue = read_json(STAGE_GAP_REVIEW_QUEUE_PATH) if STAGE_GAP_REVIEW_QUEUE_PATH.exists() else []
    stage_nodes = graph.get("theme_stage_nodes", [])
    edges = graph.get("spiral_edges", [])
    stage_by_id = {node["stage_id"]: node for node in stage_nodes}

    validator_result = run_command([sys.executable, str(VALIDATOR_PATH)])
    pytest_result = run_command([sys.executable, "-m", "pytest", "tests/ulga/test_theme_spiral_graph.py", "-q"])

    relation_counts = Counter(edge.get("relation") for edge in edges)
    confidence_method_counts = Counter(edge.get("confidence", {}).get("method") for edge in edges)
    review_status_counts = Counter(edge.get("review_status") for edge in edges)
    stage_counts_by_theme = Counter(node.get("theme_id") for node in stage_nodes)
    edge_counts_by_theme = Counter(edge.get("theme_id") for edge in edges)

    cross_theme_edges = []
    backward_edges = []
    gate_misuse_edges = []
    duplicate_tuples = []
    self_edges = []
    stage_gap_edges = []
    stage_node_missing_source_authority = []
    source_authority_mismatches = []
    for node in stage_nodes:
        authority = node.get("source_authority")
        if not isinstance(authority, dict):
            stage_node_missing_source_authority.append(node)
            continue
        if authority.get("authority_name") != "ThemeAuthority":
            source_authority_mismatches.append(node)
        if authority.get("source_theme_ids") != node.get("source_theme_ids"):
            source_authority_mismatches.append(node)
        if not {"themes/theme_catalog.json", "themes/theme_vocab_mapping.json"}.issubset(
            set(authority.get("source_files", []))
        ):
            source_authority_mismatches.append(node)
    seen_tuples = set()

    for edge in edges:
        source_node = stage_by_id.get(edge.get("source_stage_id"))
        target_node = stage_by_id.get(edge.get("target_stage_id"))
        edge_tuple = (edge.get("source_stage_id"), edge.get("target_stage_id"), edge.get("relation"))
        if edge_tuple in seen_tuples:
            duplicate_tuples.append(edge)
        seen_tuples.add(edge_tuple)
        if edge.get("source_stage_id") == edge.get("target_stage_id"):
            self_edges.append(edge)
        if edge.get("gate_eligible") is not False:
            gate_misuse_edges.append(edge)
        if source_node and target_node and source_node.get("theme_id") != target_node.get("theme_id"):
            cross_theme_edges.append(edge)
        if edge.get("source_cefr") in CEFR_RANK and edge.get("target_cefr") in CEFR_RANK:
            gap = CEFR_RANK[edge["target_cefr"]] - CEFR_RANK[edge["source_cefr"]]
            if gap <= 0:
                backward_edges.append(edge)
            if gap > 1:
                stage_gap_edges.append({**edge, "stage_gap": gap})

    cycles = count_cycles(edges)
    queue_by_edge_id = {entry.get("edge_id"): entry for entry in stage_gap_review_queue if isinstance(entry, dict)}
    stage_gap_edges_without_review_queue = [
        edge for edge in stage_gap_edges if edge["edge_id"] not in queue_by_edge_id
    ]
    stage_gap_review_queue_gate_misuse = [
        entry for entry in stage_gap_review_queue if isinstance(entry, dict) and entry.get("gate_eligible") is not False
    ]

    blocked_findings = []
    warning_findings = []
    if validator_result["status"] != "PASS":
        blocked_findings.append("Theme Spiral graph validator failed.")
    if pytest_result["status"] != "PASS":
        blocked_findings.append("Theme Spiral graph pytest failed.")
    if stage_node_missing_source_authority:
        blocked_findings.append(
            f"{len(stage_node_missing_source_authority)} ThemeStageNode(s) missing source_authority."
        )
    if source_authority_mismatches:
        blocked_findings.append(
            f"{len(source_authority_mismatches)} ThemeStageNode source_authority mismatch(es) detected."
        )
    if stage_gap_edges_without_review_queue:
        blocked_findings.append(
            f"{len(stage_gap_edges_without_review_queue)} stage-gap edge(s) missing review queue entry."
        )
    if stage_gap_review_queue_gate_misuse:
        blocked_findings.append(
            f"{len(stage_gap_review_queue_gate_misuse)} stage-gap review queue entry/entries are gate eligible."
        )
    if cross_theme_edges:
        blocked_findings.append(f"{len(cross_theme_edges)} cross-theme SPIRAL_TO edge(s) detected.")
    if backward_edges:
        blocked_findings.append(f"{len(backward_edges)} backward or non-progressing SPIRAL_TO edge(s) detected.")
    if gate_misuse_edges:
        blocked_findings.append(f"{len(gate_misuse_edges)} gate misuse edge(s) detected.")
    if duplicate_tuples:
        blocked_findings.append(f"{len(duplicate_tuples)} duplicate SPIRAL_TO tuple(s) detected.")
    if self_edges:
        blocked_findings.append(f"{len(self_edges)} self edge(s) detected.")
    if cycles:
        blocked_findings.append(f"{len(cycles)} cycle(s) detected.")
    if summary.get("spiral_edge_count") != len(edges):
        warning_findings.append("Summary spiral_edge_count does not match graph edge count.")
    if summary.get("stage_count") != len(stage_nodes):
        warning_findings.append("Summary stage_count does not match graph stage count.")
    if stage_gap_edges:
        warning_findings.append(
            f"{len(stage_gap_edges)} edge(s) skip absent intermediate CEFR stage(s); tracked in review queue."
        )

    final_verdict = "PASS" if not blocked_findings and not warning_findings else "PASS_WITH_WARNINGS"
    if blocked_findings:
        final_verdict = "BLOCKED"

    audit = {
        "audit_stage": "ULGA-S8H",
        "audit_timestamp": timestamp,
        "files_inspected": [
            "ulga/graph/theme_spiral_graph.json",
            "ulga/reports/theme_spiral_graph_summary.json",
            "ulga/validators/validate_theme_spiral_graph.py",
            "tests/ulga/test_theme_spiral_graph.py",
            "ulga/schema/learning_signal_policy.json",
        ],
        "theme_count": len(stage_counts_by_theme),
        "stage_count": len(stage_nodes),
        "spiral_edge_count": len(edges),
        "cross_theme_count": len(cross_theme_edges),
        "backward_edge_count": len(backward_edges),
        "gate_misuse_count": len(gate_misuse_edges),
        "cycle_count": len(cycles),
        "duplicate_edge_count": len(duplicate_tuples),
        "self_edge_count": len(self_edges),
        "stage_gap_gt_one_count": len(stage_gap_edges),
        "stage_node_missing_source_authority_count": len(stage_node_missing_source_authority),
        "stage_gap_review_queue_count": len(stage_gap_review_queue),
        "stage_gap_edges_without_review_queue_count": len(stage_gap_edges_without_review_queue),
        "source_authority_mismatch_count": len(source_authority_mismatches),
        "relation_breakdown": dict(relation_counts),
        "confidence_method_breakdown": dict(confidence_method_counts),
        "review_status_breakdown": dict(review_status_counts),
        "stage_counts_by_theme": dict(stage_counts_by_theme),
        "edge_counts_by_theme": dict(edge_counts_by_theme),
        "learning_signal_compliance": {
            "source_relation": "SPIRAL_TO",
            "gate_signal_generated": graph["graph_metadata"]["learning_signal_compliance"].get("gate_signal_generated"),
            "gate_allowed": graph["graph_metadata"]["learning_signal_compliance"].get("gate_allowed"),
            "learning_signal_graph_generated": graph["graph_metadata"]["learning_signal_compliance"].get("learning_signal_graph_generated"),
            "all_edges_gate_eligible_false": len(gate_misuse_edges) == 0,
            "stage_gap_review_queue_all_non_gating": len(stage_gap_review_queue_gate_misuse) == 0,
        },
        "validator_result": validator_result,
        "pytest_result": pytest_result,
        "blocked_findings": blocked_findings,
        "warning_findings": warning_findings,
        "warning_samples": {
            "stage_gap_gt_one_edges": stage_gap_edges[:10],
        },
        "final_verdict": final_verdict,
        "recommended_next_task": "ULGA-S8I_ThemeSpiralAuthority_QA_Audit",
    }

    write_json(QA_AUDIT_PATH, audit)
    print(f"ULGA Theme Spiral Graph QA Audit: {final_verdict}")
    print(f"Themes: {audit['theme_count']}")
    print(f"Stages: {audit['stage_count']}")
    print(f"SPIRAL_TO edges: {audit['spiral_edge_count']}")
    print(f"Validator: {validator_result['status']}")
    print(f"Pytest: {pytest_result['status']}")
    return 0 if final_verdict in {"PASS", "PASS_WITH_WARNINGS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
