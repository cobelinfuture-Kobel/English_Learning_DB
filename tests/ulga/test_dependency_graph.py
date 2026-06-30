import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DEPENDENCY_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "dependency_graph.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "dependency_graph_summary.json"
QA_AUDIT_PATH = BASE_DIR / "ulga" / "reports" / "dependency_graph_qa_audit.json"
GRAMMAR_NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
LEARNING_SIGNAL_POLICY_PATH = BASE_DIR / "ulga" / "schema" / "learning_signal_policy.json"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_dependency_graph.py"


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def has_cycle(edges):
    graph = defaultdict(list)
    for edge in edges:
        if edge["relation"] == "REQUIRES" and edge["gate_eligible"] is True:
            graph[edge["source_node_id"]].append(edge["target_node_id"])

    visiting = set()
    visited = set()

    def visit(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in graph.get(node, []):
            if visit(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def test_builder_output_exists():
    assert DEPENDENCY_GRAPH_PATH.exists()
    assert SUMMARY_PATH.exists()
    graph = load_json(DEPENDENCY_GRAPH_PATH)
    summary = load_json(SUMMARY_PATH)
    assert graph["edges"]
    assert summary["dependency_edge_count"] == len(graph["edges"])


def test_schema_valid_minimal_shape():
    graph = load_json(DEPENDENCY_GRAPH_PATH)
    assert graph["graph_metadata"]["contract_version"] == "ULGA-S8C"
    for edge in graph["edges"]:
        for key in [
            "edge_id",
            "source_node_id",
            "target_node_id",
            "relation",
            "dependency_class",
            "confidence",
            "source_authority",
            "review_status",
            "gate_eligible",
            "evidence",
            "notes",
        ]:
            assert key in edge
        assert edge["edge_id"].startswith("dependency_edge:")


def test_all_node_ids_exist():
    graph = load_json(DEPENDENCY_GRAPH_PATH)
    grammar_nodes = load_json(GRAMMAR_NODES_PATH)
    grammar_node_ids = {node["id"] for node in grammar_nodes}
    for edge in graph["edges"]:
        assert edge["source_node_id"] in grammar_node_ids
        assert edge["target_node_id"] in grammar_node_ids


def test_only_grammar_requires_edges_emitted():
    graph = load_json(DEPENDENCY_GRAPH_PATH)
    for edge in graph["edges"]:
        assert edge["relation"] == "REQUIRES"
        assert edge["source_node_id"].startswith("grammar:")
        assert edge["target_node_id"].startswith("grammar:")


def test_gate_rules_enforced():
    graph = load_json(DEPENDENCY_GRAPH_PATH)
    policy = load_json(LEARNING_SIGNAL_POLICY_PATH)
    allowed_gate_relations = set(
        policy["validation_policy"]["invalid_gate_mapping"]["gate_allowed_only_for"]
    )
    blocked_methods = set(
        policy["validation_policy"]["gate_confidence_validation"]["blocked_confidence_methods"]
    )
    for edge in graph["edges"]:
        if edge["gate_eligible"]:
            assert edge["relation"] in allowed_gate_relations
            assert edge["dependency_class"] == "hard_prerequisite"
            assert edge["review_status"] == "accepted"
            assert edge["confidence"]["method"] not in blocked_methods


def test_hard_prerequisite_gate_allowed():
    graph = load_json(DEPENDENCY_GRAPH_PATH)
    hard_gate_edges = [
        edge
        for edge in graph["edges"]
        if edge["dependency_class"] == "hard_prerequisite"
        and edge["relation"] == "REQUIRES"
    ]
    assert hard_gate_edges
    assert all(edge["gate_eligible"] is True for edge in hard_gate_edges)


def test_soft_prerequisite_gate_blocked():
    graph = load_json(DEPENDENCY_GRAPH_PATH)
    assert not [
        edge
        for edge in graph["edges"]
        if edge["dependency_class"] == "soft_prerequisite"
        and edge["gate_eligible"] is True
    ]


def test_review_link_gate_blocked():
    graph = load_json(DEPENDENCY_GRAPH_PATH)
    assert not [
        edge
        for edge in graph["edges"]
        if edge["dependency_class"] == "review_link"
        and edge["gate_eligible"] is True
    ]


def test_no_circular_dependency():
    graph = load_json(DEPENDENCY_GRAPH_PATH)
    assert has_cycle(graph["edges"]) is False


def test_no_theme_or_signal_graph_generation():
    graph = load_json(DEPENDENCY_GRAPH_PATH)
    compliance = graph["graph_metadata"]["learning_signal_compliance"]
    assert compliance["theme_spiral_edges_generated"] is False
    assert compliance["learning_signal_graph_generated"] is False
    assert compliance["cefr_only_dependency_generated"] is False


def test_validator_run():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_qa_audit_exists_if_generated():
    if QA_AUDIT_PATH.exists():
        audit = load_json(QA_AUDIT_PATH)
        assert audit["final_verdict"] in {"PASS", "WARNING_ACCEPTED"}
