import json
import re
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
ULGA_DIR = BASE_DIR / "ulga"
SCHEMA_DIR = ULGA_DIR / "schema"
GRAPH_DIR = ULGA_DIR / "graph"

NODE_SCHEMA_PATH = SCHEMA_DIR / "ulga_node_schema.json"
EDGE_SCHEMA_PATH = SCHEMA_DIR / "ulga_edge_schema.json"
GRAPH_SCHEMA_PATH = SCHEMA_DIR / "ulga_graph_schema.json"
NODES_EMPTY_PATH = GRAPH_DIR / "ulga_nodes.empty.json"
EDGES_EMPTY_PATH = GRAPH_DIR / "ulga_edges.empty.json"
GRAPH_EMPTY_PATH = GRAPH_DIR / "ulga_graph.empty.json"

NODE_TYPES = {
    "grammar",
    "vocabulary",
    "chunk",
    "theme",
    "sentence_pattern",
    "skill",
    "exercise_type",
    "learner_state",
    "assessment",
}
EDGE_TYPES = {
    "prerequisite",
    "supports",
    "belongs_to",
    "unlocks",
    "reviews",
    "contrasts_with",
    "uses",
    "contains",
    "spiral_to",
    "assesses",
}
NODE_REQUIRED = {
    "id",
    "node_type",
    "label",
    "authority_source",
    "cefr_level",
    "confidence",
    "version",
    "metadata",
}
EDGE_REQUIRED = {
    "id",
    "source_node_id",
    "target_node_id",
    "edge_type",
    "authority_source",
    "confidence",
    "version",
    "metadata",
}
GRAPH_REQUIRED = {
    "graph_id",
    "contract_version",
    "schema_version",
    "formal_data_mounted",
    "nodes",
    "edges",
    "metadata",
    "validation_status",
}
NODE_ID_RE = re.compile(
    r"^(grammar|vocabulary|chunk|theme|sentence_pattern|skill|exercise_type|learner_state|assessment):[A-Za-z0-9_.:-]+$"
)
EDGE_ID_RE = re.compile(r"^edge:[A-Za-z0-9_.:-]+$")


class ValidationError(Exception):
    pass


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def validate_schema_files():
    node_schema = load_json(NODE_SCHEMA_PATH)
    edge_schema = load_json(EDGE_SCHEMA_PATH)
    graph_schema = load_json(GRAPH_SCHEMA_PATH)

    require(set(node_schema["required"]) == NODE_REQUIRED, "node schema required fields mismatch")
    require(
        set(node_schema["properties"]["node_type"]["enum"]) == NODE_TYPES,
        "node schema node_type enum mismatch",
    )
    require(set(edge_schema["required"]) == EDGE_REQUIRED, "edge schema required fields mismatch")
    require(
        set(edge_schema["properties"]["edge_type"]["enum"]) == EDGE_TYPES,
        "edge schema edge_type enum mismatch",
    )
    require(set(graph_schema["required"]) == GRAPH_REQUIRED, "graph schema required fields mismatch")
    require(
        graph_schema["properties"]["formal_data_mounted"].get("const") is False,
        "graph schema must require formal_data_mounted=false for S2 scaffold",
    )


def validate_authority_confidence_version(record, record_name):
    authority = record.get("authority_source")
    confidence = record.get("confidence")
    version = record.get("version")

    require(isinstance(authority, dict), f"{record_name} authority_source must be an object")
    require(authority.get("source_name"), f"{record_name} authority_source.source_name is required")
    require(authority.get("derivation"), f"{record_name} authority_source.derivation is required")

    require(isinstance(confidence, dict), f"{record_name} confidence must be an object")
    require("value" in confidence, f"{record_name} confidence.value is required")
    require(0 <= confidence["value"] <= 1, f"{record_name} confidence.value must be between 0 and 1")
    require(confidence.get("method"), f"{record_name} confidence.method is required")

    require(isinstance(version, dict), f"{record_name} version must be an object")
    require(version.get("contract") == "ULGA-S2", f"{record_name} version.contract must be ULGA-S2")


def validate_node(node):
    require(isinstance(node, dict), "node must be an object")
    require(NODE_REQUIRED.issubset(node.keys()), f"node missing required fields: {NODE_REQUIRED - set(node.keys())}")
    require(NODE_ID_RE.match(node["id"]), f"invalid node id: {node['id']}")
    require(node["node_type"] in NODE_TYPES, f"invalid node_type: {node['node_type']}")
    require(node["id"].startswith(f"{node['node_type']}:"), f"node id prefix does not match node_type: {node['id']}")
    require(isinstance(node["metadata"], dict), f"node metadata must be an object: {node['id']}")
    validate_authority_confidence_version(node, f"node {node['id']}")


def validate_edge(edge, node_ids=None):
    require(isinstance(edge, dict), "edge must be an object")
    require(EDGE_REQUIRED.issubset(edge.keys()), f"edge missing required fields: {EDGE_REQUIRED - set(edge.keys())}")
    require(EDGE_ID_RE.match(edge["id"]), f"invalid edge id: {edge['id']}")
    require(edge["edge_type"] in EDGE_TYPES, f"invalid edge_type: {edge['edge_type']}")
    require(edge.get("source_node_id"), f"edge source_node_id is required: {edge['id']}")
    require(edge.get("target_node_id"), f"edge target_node_id is required: {edge['id']}")
    if node_ids is not None:
        require(edge["source_node_id"] in node_ids, f"edge source not found: {edge['id']}")
        require(edge["target_node_id"] in node_ids, f"edge target not found: {edge['id']}")
    require(isinstance(edge["metadata"], dict), f"edge metadata must be an object: {edge['id']}")
    validate_authority_confidence_version(edge, f"edge {edge['id']}")


def validate_graph(graph):
    require(isinstance(graph, dict), "graph must be an object")
    require(GRAPH_REQUIRED.issubset(graph.keys()), f"graph missing required fields: {GRAPH_REQUIRED - set(graph.keys())}")
    require(graph["graph_id"] == "ulga_graph.empty", "S2 scaffold graph_id must be ulga_graph.empty")
    require(graph["contract_version"] == "ULGA-S2", "graph contract_version must be ULGA-S2")
    require(graph["schema_version"] == "1.0.0", "graph schema_version must be 1.0.0")
    require(graph["formal_data_mounted"] is False, "S2 scaffold must not mount formal data")
    require(isinstance(graph["nodes"], list), "graph nodes must be an array")
    require(isinstance(graph["edges"], list), "graph edges must be an array")
    require(graph["nodes"] == [], "S2 empty graph scaffold must contain zero nodes")
    require(graph["edges"] == [], "S2 empty graph scaffold must contain zero edges")
    require(graph["metadata"].get("data_policy") == "empty_scaffold_only", "graph data_policy must be empty_scaffold_only")

    node_ids = set()
    edge_ids = set()
    for node in graph["nodes"]:
        validate_node(node)
        require(node["id"] not in node_ids, f"duplicate node id: {node['id']}")
        node_ids.add(node["id"])
    for edge in graph["edges"]:
        validate_edge(edge, node_ids=node_ids)
        require(edge["id"] not in edge_ids, f"duplicate edge id: {edge['id']}")
        edge_ids.add(edge["id"])


def validate_empty_scaffolds():
    nodes = load_json(NODES_EMPTY_PATH)
    edges = load_json(EDGES_EMPTY_PATH)
    graph = load_json(GRAPH_EMPTY_PATH)

    require(nodes == [], "ulga_nodes.empty.json must be an empty array")
    require(edges == [], "ulga_edges.empty.json must be an empty array")
    validate_graph(graph)


def main():
    try:
        validate_schema_files()
        validate_empty_scaffolds()
    except Exception as exc:
        print(f"ULGA schema validation: FAIL - {exc}")
        return 1
    print("ULGA schema validation: PASS")
    print("Validated schema files and empty graph scaffold. No formal data mounted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
