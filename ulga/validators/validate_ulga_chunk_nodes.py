import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

try:
    from ulga.validators.validate_ulga_schema import validate_node, ValidationError, require
except ImportError:
    class ValidationError(Exception):
        pass

    def require(condition, message):
        if not condition:
            raise ValidationError(message)

    def validate_node(node):
        require(isinstance(node, dict), "node must be an object")
        require("id" in node, "node id is required")
        require("node_type" in node, "node_type is required")
        require("label" in node, "label is required")


CHUNK_NODES_PATH = BASE_DIR / "ulga" / "graph" / "chunk_nodes.json"
GRAPH_CHUNK_NODES_PATH = BASE_DIR / "ulga" / "graph" / "ulga_graph.chunk_nodes.json"

ALLOWED_CEFR_LEVELS = {"A1", "A1_plus", "A2", "A2_plus", "B1", "B1_plus", "B2", "B2_plus", "C1", "C2", None}
REQUIRED_METADATA_FIELDS = {
    "source_chunk_id",
    "canonical_chunk",
    "normalized_chunk",
    "safe_chunk_id",
    "equivalent_group_id",
    "equivalent_ids",
    "chunk_type",
    "usage_class",
    "theme_hint",
    "priority_band",
    "frequency_proxy_score",
    "generator_allowed",
    "validator_accepts_equivalents",
    "safe_layer_source",
    "is_canonical",
    "source_file",
    "mounting_stage",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_chunk_node_list(nodes):
    require(isinstance(nodes, list), "chunk_nodes must be a list")
    require(len(nodes) > 0, "chunk_nodes must not be empty")

    node_ids = set()
    canonical_chunks = set()

    for idx, node in enumerate(nodes):
        validate_node(node)

        node_id = node["id"]
        require(node["node_type"] == "chunk", f"Node at index {idx} has invalid node_type: {node['node_type']}")
        require(node_id.startswith("chunk:"), f"Node id does not start with chunk:: {node_id}")
        require(node_id not in node_ids, f"Duplicate node id found: {node_id}")
        node_ids.add(node_id)

        require(node.get("cefr_level") in ALLOWED_CEFR_LEVELS, f"Node {node_id} has invalid cefr_level")

        confidence = node.get("confidence", {})
        require(confidence.get("value") <= 1.0, f"Node {node_id} confidence exceeds 1.0")
        require(confidence.get("method") == "authority_mount", f"Node {node_id} confidence.method must be authority_mount")

        metadata = node.get("metadata", {})
        missing = REQUIRED_METADATA_FIELDS - set(metadata.keys())
        require(not missing, f"Node {node_id} missing metadata fields: {sorted(missing)}")
        require(metadata.get("mounting_stage") == "ULGA-S6B", f"Node {node_id} has invalid mounting_stage")
        require(isinstance(metadata.get("equivalent_ids"), list), f"Node {node_id} equivalent_ids must be a list")
        require(isinstance(metadata.get("theme_hint"), list), f"Node {node_id} theme_hint must be a list")
        require(metadata.get("generator_allowed") is True, f"Node {node_id} must be generator_allowed")
        require(
            metadata.get("validator_accepts_equivalents") is True,
            f"Node {node_id} must accept validator equivalents",
        )

        canonical_chunk = metadata.get("canonical_chunk")
        require(canonical_chunk, f"Node {node_id} missing canonical_chunk")
        require(canonical_chunk not in canonical_chunks, f"Duplicate canonical_chunk found: {canonical_chunk}")
        canonical_chunks.add(canonical_chunk)
        require(node_id == f"chunk:{canonical_chunk}", f"Node {node_id} does not match canonical_chunk")


def validate_chunk_graph(graph):
    require(graph.get("graph_id") == "ulga_graph.chunk_nodes", "Graph graph_id must be ulga_graph.chunk_nodes")
    require(graph.get("contract_version") == "ULGA-S2", "Graph contract_version must be ULGA-S2")
    require(graph.get("schema_version") == "1.0.0", "Graph schema_version must be 1.0.0")
    require(graph.get("formal_data_mounted") is True, "Graph formal_data_mounted must be true")
    require(graph.get("mounted_stage") == "ULGA-S6B", "Graph mounted_stage must be ULGA-S6B")
    require(graph.get("edges") == [], "Graph edges must be empty")
    require(graph.get("edge_count") == 0, "Graph edge_count must be 0")
    require(graph.get("chunk_vocabulary_linkage") is False, "chunk_vocabulary_linkage must be false")
    require(graph.get("chunk_theme_projection") is False, "chunk_theme_projection must be false")
    require(graph.get("chunk_grammar_metadata") is False, "chunk_grammar_metadata must be false")
    require(graph.get("chunk_morphology_linkage") is False, "chunk_morphology_linkage must be false")
    require(graph.get("chunk_chunk_linkage") is False, "chunk_chunk_linkage must be false")

    nodes = graph.get("nodes")
    require(isinstance(nodes, list), "Graph nodes must be a list")
    require(graph.get("node_count") == len(nodes), "Graph node_count must match nodes length")
    require(graph.get("chunk_node_count") == len(nodes), "Graph chunk_node_count must match nodes length")
    validate_chunk_node_list(nodes)

    forbidden_node_types = {"vocabulary", "grammar", "theme", "morphology", "learner_state"}
    for node in nodes:
        require(node["node_type"] not in forbidden_node_types, f"Forbidden node type found: {node['node_type']}")


def main():
    try:
        if not CHUNK_NODES_PATH.exists():
            raise ValidationError(f"File not found: {CHUNK_NODES_PATH}")
        if not GRAPH_CHUNK_NODES_PATH.exists():
            raise ValidationError(f"File not found: {GRAPH_CHUNK_NODES_PATH}")

        nodes = load_json(CHUNK_NODES_PATH)
        print("Validating chunk_nodes.json...")
        validate_chunk_node_list(nodes)

        graph = load_json(GRAPH_CHUNK_NODES_PATH)
        print("Validating ulga_graph.chunk_nodes.json...")
        validate_chunk_graph(graph)
    except Exception as exc:
        print(f"ULGA chunk nodes validation: FAIL - {exc}")
        return 1

    print("ULGA chunk nodes validation: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
