import json
import sys
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DEPENDENCY_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "dependency_graph.json"
GRAMMAR_NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
LEARNING_SIGNAL_POLICY_PATH = BASE_DIR / "ulga" / "schema" / "learning_signal_policy.json"

ALLOWED_RELATIONS = {"REQUIRES"}
ALLOWED_DEPENDENCY_CLASSES = {
    "hard_prerequisite",
    "soft_prerequisite",
    "recommended_order",
    "review_link",
}
ALLOWED_CONFIDENCE_METHODS = {
    "authoritative",
    "derived",
    "heuristic",
    "manual_review_required",
}
ALLOWED_REVIEW_STATUS = {"accepted", "needs_review", "blocked", "deprecated"}


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"FAIL: could not load {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def has_cycle(edges):
    graph = defaultdict(list)
    for edge in edges:
        if edge.get("relation") == "REQUIRES" and edge.get("gate_eligible") is True:
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

    return any(visit(node) for node in list(graph))


def validate_edge_shape(edge, index):
    required = {
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
    }
    missing = required - set(edge)
    if missing:
        return fail(f"edge[{index}] missing required fields: {sorted(missing)}")
    if not str(edge["edge_id"]).startswith("dependency_edge:"):
        return fail(f"edge[{index}] has invalid edge_id prefix.")
    if edge["source_node_id"] == edge["target_node_id"]:
        return fail(f"edge[{index}] is a self dependency.")
    if edge["relation"] not in ALLOWED_RELATIONS:
        return fail(f"edge[{index}] has invalid relation: {edge['relation']}")
    if edge["dependency_class"] not in ALLOWED_DEPENDENCY_CLASSES:
        return fail(f"edge[{index}] has invalid dependency_class: {edge['dependency_class']}")
    if edge["review_status"] not in ALLOWED_REVIEW_STATUS:
        return fail(f"edge[{index}] has invalid review_status.")
    if not isinstance(edge["gate_eligible"], bool):
        return fail(f"edge[{index}] gate_eligible must be boolean.")
    if not isinstance(edge["evidence"], list) or not edge["evidence"]:
        return fail(f"edge[{index}] evidence must be a non-empty list.")
    if not isinstance(edge["notes"], list):
        return fail(f"edge[{index}] notes must be a list.")

    confidence = edge["confidence"]
    if not isinstance(confidence, dict):
        return fail(f"edge[{index}] confidence must be an object.")
    value = confidence.get("value")
    method = confidence.get("method")
    if not isinstance(value, (int, float)) or value < 0 or value > 1:
        return fail(f"edge[{index}] confidence.value must be between 0 and 1.")
    if method not in ALLOWED_CONFIDENCE_METHODS:
        return fail(f"edge[{index}] confidence.method is invalid: {method}")
    return True


def validate():
    print("Validating ULGA Dependency Graph...")
    if not DEPENDENCY_GRAPH_PATH.exists():
        return fail(f"required file does not exist: {DEPENDENCY_GRAPH_PATH}")

    graph = read_json(DEPENDENCY_GRAPH_PATH)
    grammar_nodes = read_json(GRAMMAR_NODES_PATH)
    policy = read_json(LEARNING_SIGNAL_POLICY_PATH)
    if graph is None or grammar_nodes is None or policy is None:
        return False

    if not isinstance(graph, dict):
        return fail("dependency_graph.json must be an object.")
    if "graph_metadata" not in graph or "edges" not in graph:
        return fail("dependency graph must contain graph_metadata and edges.")
    if graph["graph_metadata"].get("contract_version") != "ULGA-S8C":
        return fail("dependency graph contract_version must be ULGA-S8C.")
    if graph["graph_metadata"].get("learning_signal_compliance", {}).get("learning_signal_graph_generated") is not False:
        return fail("dependency graph must not generate a learning signal graph.")
    if graph["graph_metadata"].get("learning_signal_compliance", {}).get("theme_spiral_edges_generated") is not False:
        return fail("dependency graph must not generate Theme Spiral edges.")

    edges = graph["edges"]
    if not isinstance(edges, list) or not edges:
        return fail("dependency graph edges must be a non-empty list.")

    grammar_node_ids = {node["id"] for node in grammar_nodes}
    gate_allowed_only_for = set(
        policy.get("validation_policy", {})
        .get("invalid_gate_mapping", {})
        .get("gate_allowed_only_for", [])
    )
    blocked_gate_methods = set(
        policy.get("validation_policy", {})
        .get("gate_confidence_validation", {})
        .get("blocked_confidence_methods", [])
    )

    seen_ids = set()
    seen_tuples = set()
    for index, edge in enumerate(edges):
        if not validate_edge_shape(edge, index):
            return False
        if edge["edge_id"] in seen_ids:
            return fail(f"duplicate edge_id: {edge['edge_id']}")
        seen_ids.add(edge["edge_id"])

        edge_tuple = (edge["source_node_id"], edge["target_node_id"], edge["relation"])
        if edge_tuple in seen_tuples:
            return fail(f"duplicate dependency tuple: {edge_tuple}")
        seen_tuples.add(edge_tuple)

        if edge["source_node_id"] not in grammar_node_ids:
            return fail(f"missing source node: {edge['source_node_id']}")
        if edge["target_node_id"] not in grammar_node_ids:
            return fail(f"missing target node: {edge['target_node_id']}")
        if not edge["source_node_id"].startswith("grammar:") or not edge["target_node_id"].startswith("grammar:"):
            return fail("S8C dependency graph may only contain GrammarNode -> GrammarNode edges.")

        if edge["gate_eligible"] is True:
            if edge["relation"] not in gate_allowed_only_for:
                return fail(f"gate misuse: {edge['relation']} is not gate allowed.")
            if edge["dependency_class"] != "hard_prerequisite":
                return fail("gate misuse: only hard_prerequisite may gate.")
            if edge["review_status"] != "accepted":
                return fail("gate misuse: gate edge must be accepted.")
            if edge["confidence"]["method"] in blocked_gate_methods:
                return fail("confidence misuse: heuristic/manual_review_required edge cannot gate.")

        evidence_blob = json.dumps(edge.get("evidence", []), ensure_ascii=False)
        if "hard_prerequisite" not in evidence_blob:
            return fail("CEFR-only dependency misuse: evidence must include hard_prerequisite source.")
        if "cefr_is_not_order" not in evidence_blob:
            return fail("CEFR-only dependency misuse: evidence must preserve cefr_is_not_order.")
        if edge["source_authority"] != "Grammar Authority":
            return fail("source_authority must be Grammar Authority for S8C.")

    if has_cycle(edges):
        return fail("circular dependency detected among gate-eligible REQUIRES edges.")

    print("ULGA Dependency Graph validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
