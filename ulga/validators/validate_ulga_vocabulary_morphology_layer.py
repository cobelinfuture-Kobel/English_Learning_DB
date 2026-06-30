import json
import sys
from pathlib import Path

# Setup base directory
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

try:
    from ulga.validators.validate_ulga_schema import require, validate_edge, ValidationError
except ImportError:
    class ValidationError(Exception):
        pass

    def require(condition, message):
        if not condition:
            raise ValidationError(message)

    def validate_edge(edge, node_ids=None):
        require(isinstance(edge, dict), "edge must be an object")
        require("id" in edge, "edge id is required")
        require("source_node_id" in edge, "source_node_id is required")
        require("target_node_id" in edge, "target_node_id is required")
        if node_ids is not None:
            require(edge["source_node_id"] in node_ids, f"edge source not found: {edge['id']}")
            require(edge["target_node_id"] in node_ids, f"edge target not found: {edge['id']}")

GRAPH_DIR = BASE_DIR / "ulga" / "graph"
REPORTS_DIR = BASE_DIR / "ulga" / "reports"

VOCAB_NODES_PATH = GRAPH_DIR / "vocabulary_nodes.json"
MORPH_EDGES_PATH = GRAPH_DIR / "vocabulary_morphology_edges.json"
MORPH_GRAPH_PATH = GRAPH_DIR / "ulga_graph.vocabulary_morphology_layer.json"
SUMMARY_PATH = REPORTS_DIR / "vocabulary_morphology_summary.json"

def validate_morphology_layer():
    # 1. Check file existence
    require(VOCAB_NODES_PATH.exists(), f"Missing vocabulary nodes: {VOCAB_NODES_PATH}")
    require(MORPH_EDGES_PATH.exists(), f"Missing morphology edges: {MORPH_EDGES_PATH}")
    require(MORPH_GRAPH_PATH.exists(), f"Missing morphology graph: {MORPH_GRAPH_PATH}")
    require(SUMMARY_PATH.exists(), f"Missing summary report: {SUMMARY_PATH}")

    # Load JSON files
    with open(VOCAB_NODES_PATH, "r", encoding="utf-8") as f:
        vocab_nodes = json.load(f)
    with open(MORPH_EDGES_PATH, "r", encoding="utf-8") as f:
        morph_edges = json.load(f)
    with open(MORPH_GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # Index vocab node IDs
    vocab_node_ids = {node["id"] for node in vocab_nodes}
    
    # 2. Verify edge count > 0
    require(len(morph_edges) > 0, "Morphology edge count must be greater than 0")

    seen_tuples = set()
    
    # 3. Verify each edge
    for edge in morph_edges:
        validate_edge(edge, node_ids=vocab_node_ids)
        
        # All source and target must be vocabulary nodes
        require(edge["source_node_id"].startswith("vocabulary:"), f"Source node must be vocabulary type: {edge['id']}")
        require(edge["target_node_id"].startswith("vocabulary:"), f"Target node must be vocabulary type: {edge['id']}")
        
        # No self-loops
        require(edge["source_node_id"] != edge["target_node_id"], f"Self-loop detected: {edge['id']}")
        
        # No duplicate tuples
        edge_tuple = (edge["source_node_id"], edge["target_node_id"], edge["edge_type"])
        require(edge_tuple not in seen_tuples, f"Duplicate edge tuple detected: {edge_tuple}")
        seen_tuples.add(edge_tuple)
        
        # edge_type == supports
        require(edge["edge_type"] == "supports", f"Edge type must be supports: {edge['id']}")
        
        # confidence constraints
        confidence = edge.get("confidence", {})
        require(confidence.get("value", 1.0) <= 0.85, f"Confidence value must be <= 0.85: {edge['id']}")
        require(confidence.get("method") == "rule_based", f"Confidence method must be rule_based: {edge['id']}")
        
        # metadata payload constraints
        metadata = edge.get("metadata", {})
        require(metadata.get("relation_family") == "morphology", f"Relation family must be morphology: {edge['id']}")
        require(metadata.get("word_family_hub_used") is False, f"word_family_hub_used must be False: {edge['id']}")
        require(metadata.get("morphology_node_created") is False, f"morphology_node_created must be False: {edge['id']}")
        require(metadata.get("mounting_stage") == "ULGA-S5I", f"Invalid mounting stage: {edge['id']}")
        require(metadata.get("sense_specific") is True, f"sense_specific must be True: {edge['id']}")
        require("inflection_promoted_to_lexical_node" in metadata, f"inflection_promoted_to_lexical_node missing: {edge['id']}")

    # 4. Verify graph wrapper
    require(graph.get("graph_id") == "ulga_graph.vocabulary_morphology_layer", "Invalid graph wrapper ID")
    require(graph.get("contract_version") == "ULGA-S2", "Graph contract version must be ULGA-S2")
    require(graph.get("schema_version") == "1.0.0", "Graph schema version must be 1.0.0")
    require(graph.get("formal_data_mounted") is True, "Graph formal_data_mounted must be true")
    require(graph.get("mounted_stage") == "ULGA-S5I", "Graph mounted stage must be ULGA-S5I")
    
    # Node and edge checks in wrapper
    require(graph.get("nodes") == vocab_nodes, "Graph nodes list must exactly match vocabulary nodes list")
    require(graph.get("edges") == morph_edges, "Graph edges list must exactly match morphology edges list")
    
    # Count checks in metadata
    graph_meta = graph.get("metadata", {})
    require(graph_meta.get("vocabulary_node_count") == len(vocab_nodes), "Graph vocabulary node count mismatch")
    require(graph_meta.get("morphology_edge_count") == len(morph_edges), "Graph morphology edge count mismatch")
    require(graph_meta.get("morphology_node_count") == 0, "Graph morphology node count must be 0")
    require(graph_meta.get("word_family_hub_node_count") == 0, "Graph word family hub count must be 0")
    require(graph_meta.get("relation_family") == "morphology", "Graph relation family must be morphology")
    require(graph_meta.get("morphology_nodes_created") is False, "Graph morphology_nodes_created must be False")
    require(graph_meta.get("word_family_hubs_created") is False, "Graph word_family_hubs_created must be False")

    # 5. Verify no forbidden structures (theme, chunk, grammar edges, learner_state)
    for edge in morph_edges:
        forbidden_types = {"theme", "chunk", "grammar", "learner_state"}
        for ft in forbidden_types:
            require(ft not in edge["id"].lower(), f"Forbidden edge name pattern: {edge['id']}")

    print(f"Validation: SUCCESS. Verified {len(morph_edges)} morphology edges, zero hubs, zero morphology nodes.")

def main():
    try:
        validate_morphology_layer()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"ULGA vocabulary morphology layer validation: FAIL - {exc}")
        return 1
    print("ULGA vocabulary morphology layer validation: PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
