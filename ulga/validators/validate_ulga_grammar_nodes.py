import json
import sys
from pathlib import Path

# Add project root to sys.path so we can import validate_ulga_schema
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

try:
    from ulga.validators.validate_ulga_schema import validate_node, ValidationError, require
except ImportError:
    # Fallback/stub if imported differently in some environments
    class ValidationError(Exception):
        pass

    def require(condition, message):
        if not condition:
            raise ValidationError(message)

    def validate_node(node):
        # minimal fallback validator
        require(isinstance(node, dict), "node must be an object")
        require("id" in node, "node id is required")
        require("node_type" in node, "node_type is required")
        require("label" in node, "label is required")

GRAMMAR_NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
GRAPH_GRAMMAR_NODES_PATH = BASE_DIR / "ulga" / "graph" / "ulga_graph.grammar_nodes.json"

ALLOWED_CEFR_LEVELS = {"A1", "A1_plus", "A2", "A2_plus", "B1", "B1_plus", "B2", "B2_plus", "C1", "C2", None}

def validate_grammar_node_list(nodes):
    node_ids = set()
    source_record_ids = set()
    
    for idx, node in enumerate(nodes):
        # 1. 符合 ulga_node_schema.json via validate_node
        validate_node(node)
        
        # 2. node_type 全部為 grammar
        require(node["node_type"] == "grammar", f"Node at index {idx} has invalid node_type: {node['node_type']}")
        
        # 3. id 不重複
        node_id = node["id"]
        require(node_id not in node_ids, f"Duplicate node id found: {node_id}")
        node_ids.add(node_id)
        
        # 4. metadata.source_record_id 不重複
        metadata = node.get("metadata", {})
        source_rec_id = metadata.get("source_record_id")
        require(source_rec_id, f"Node {node_id} is missing source_record_id in metadata")
        require(source_rec_id not in source_record_ids, f"Duplicate source_record_id found: {source_rec_id}")
        source_record_ids.add(source_rec_id)
        
        # 5. cefr_level 合法
        require(node.get("cefr_level") in ALLOWED_CEFR_LEVELS, f"Node {node_id} has invalid cefr_level: {node.get('cefr_level')}")
        
        # 6. authority_source 存在 (already checked by validate_node, but let's be explicit about it)
        require("authority_source" in node, f"Node {node_id} is missing authority_source")
        
        # 7. confidence 存在且為 1.0
        confidence = node.get("confidence", {})
        require(confidence.get("value") == 1.0, f"Node {node_id} must have confidence.value = 1.0, got: {confidence.get('value')}")
        
        # 8. version 存在 (checked by validate_node)
        require("version" in node, f"Node {node_id} is missing version")
        
        # 9. metadata contains required fields
        require("canonical_grammar_key" in metadata, f"Node {node_id} is missing canonical_grammar_key in metadata")
        require(metadata.get("mounting_stage") == "ULGA-S4A", f"Node {node_id} has invalid mounting_stage: {metadata.get('mounting_stage')}")
        require(metadata.get("dependency_edges_mounted") is False, f"Node {node_id} dependency_edges_mounted must be false")

def validate_grammar_graph(graph):
    # check top-level keys
    require(graph.get("formal_data_mounted") is True, "Graph formal_data_mounted must be true")
    require(graph.get("mounted_stage") == "ULGA-S4A", "Graph mounted_stage must be ULGA-S4A")
    require(graph.get("edges") == [], "Graph edges must be empty")
    require(graph.get("edge_count") == 0, "Graph edge_count must be 0")
    
    nodes = graph.get("nodes", [])
    require(isinstance(nodes, list), "Graph nodes must be a list")
    require(graph.get("node_count") == len(nodes), f"Graph node_count ({graph.get('node_count')}) does not match nodes length ({len(nodes)})")
    
    # Run node checks
    validate_grammar_node_list(nodes)
    
    # Check that no forbidden node types exist
    for node in nodes:
        forbidden_types = {"vocabulary", "chunk", "theme", "learner_state"}
        require(node["node_type"] not in forbidden_types, f"Forbidden node type found: {node['node_type']}")

def main():
    try:
        # Load and validate grammar_nodes.json
        if not GRAMMAR_NODES_PATH.exists():
            raise ValidationError(f"File not found: {GRAMMAR_NODES_PATH}")
        with open(GRAMMAR_NODES_PATH, "r", encoding="utf-8") as f:
            nodes = json.load(f)
        print("Validating grammar_nodes.json...")
        validate_grammar_node_list(nodes)
        
        # Load and validate ulga_graph.grammar_nodes.json
        if not GRAPH_GRAMMAR_NODES_PATH.exists():
            raise ValidationError(f"File not found: {GRAPH_GRAMMAR_NODES_PATH}")
        with open(GRAPH_GRAMMAR_NODES_PATH, "r", encoding="utf-8") as f:
            graph = json.load(f)
        print("Validating ulga_graph.grammar_nodes.json...")
        validate_grammar_graph(graph)
        
    except Exception as exc:
        print(f"ULGA grammar nodes validation: FAIL - {exc}")
        return 1
    
    print("ULGA grammar nodes validation: PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
