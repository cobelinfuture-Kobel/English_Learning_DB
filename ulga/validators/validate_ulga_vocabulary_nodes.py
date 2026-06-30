import json
import sys
from pathlib import Path

# Add project root to sys.path so we can import validate_ulga_schema
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

VOCAB_NODES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json"
GRAPH_VOCAB_NODES_PATH = BASE_DIR / "ulga" / "graph" / "ulga_graph.vocabulary_nodes.json"

ALLOWED_CEFR_LEVELS = {"A1", "A1_plus", "A2", "A2_plus", "B1", "B1_plus", "B2", "B2_plus", "C1", "C2", None}

def validate_vocabulary_node_list(nodes):
    node_ids = set()
    source_record_ids = set()
    
    for idx, node in enumerate(nodes):
        # 1.符合 ulga_node_schema.json via validate_node
        validate_node(node)
        
        # 2.node_type 全部為 vocabulary
        require(node["node_type"] == "vocabulary", f"Node at index {idx} has invalid node_type: {node['node_type']}")
        
        # 3.id 不重複
        node_id = node["id"]
        require(node_id not in node_ids, f"Duplicate node id found: {node_id}")
        node_ids.add(node_id)
        
        # 4.id 以 vocabulary: 開頭
        require(node_id.startswith("vocabulary:"), f"Node id does not start with 'vocabulary:': {node_id}")
        
        # 5.metadata / authority_source / confidence 必須存在
        require("metadata" in node, f"Node {node_id} is missing metadata")
        require("authority_source" in node, f"Node {node_id} is missing authority_source")
        require("confidence" in node, f"Node {node_id} is missing confidence")
        
        metadata = node["metadata"]
        authority_source = node["authority_source"]
        confidence = node["confidence"]
        
        # 6.metadata 至少包含指定欄位
        require("source_vocabulary_id" in metadata, f"Node {node_id} is missing source_vocabulary_id in metadata")
        require("evp_level" in metadata, f"Node {node_id} is missing evp_level in metadata")
        require("frequency_rank" in metadata, f"Node {node_id} is missing frequency_rank in metadata")
        require("frequency_score" in metadata, f"Node {node_id} is missing frequency_score in metadata")
        require("part_of_speech" in metadata, f"Node {node_id} is missing part_of_speech in metadata")
        require("theme_tags" in metadata, f"Node {node_id} is missing theme_tags in metadata")
        require("chunk_count" in metadata, f"Node {node_id} is missing chunk_count in metadata")
        require("grammar_prerequisites" in metadata, f"Node {node_id} is missing grammar_prerequisites in metadata")
        require("version" in metadata, f"Node {node_id} is missing version in metadata")
        require(metadata.get("mounting_stage") == "ULGA-S5B", f"Node {node_id} has invalid mounting_stage: {metadata.get('mounting_stage')}")
        
        # 7.cefr_level 合法
        require(node.get("cefr_level") in ALLOWED_CEFR_LEVELS, f"Node {node_id} has invalid cefr_level: {node.get('cefr_level')}")

def validate_vocabulary_graph(graph):
    # check top-level keys
    require(graph.get("formal_data_mounted") is True, "Graph formal_data_mounted must be true")
    require(graph.get("mounted_stage") == "ULGA-S5B", "Graph mounted_stage must be ULGA-S5B")
    require(graph.get("edges") == [], "Graph edges must be empty")
    require(graph.get("edge_count") == 0, "Graph edge_count must be 0")
    require(graph.get("dependency_layer_implemented") is False, "Graph dependency_layer_implemented must be False")
    require(graph.get("theme_layer_implemented") is False, "Graph theme_layer_implemented must be False")
    require(graph.get("morphology_layer_implemented") is False, "Graph morphology_layer_implemented must be False")
    
    nodes = graph.get("nodes", [])
    require(isinstance(nodes, list), "Graph nodes must be a list")
    require(len(nodes) > 0, "Graph node_count must be > 0")
    require(graph.get("node_count") == len(nodes), f"Graph node_count ({graph.get('node_count')}) does not match nodes length ({len(nodes)})")
    
    # Run node checks
    validate_vocabulary_node_list(nodes)
    
    # Check that no forbidden node types exist
    for node in nodes:
        forbidden_types = {"grammar", "chunk", "theme", "learner_state"}
        require(node["node_type"] not in forbidden_types, f"Forbidden node type found: {node['node_type']}")

def main():
    try:
        # Load and validate vocabulary_nodes.json
        if not VOCAB_NODES_PATH.exists():
            raise ValidationError(f"File not found: {VOCAB_NODES_PATH}")
        with open(VOCAB_NODES_PATH, "r", encoding="utf-8") as f:
            nodes = json.load(f)
        print("Validating vocabulary_nodes.json...")
        validate_vocabulary_node_list(nodes)
        
        # Load and validate ulga_graph.vocabulary_nodes.json
        if not GRAPH_VOCAB_NODES_PATH.exists():
            raise ValidationError(f"File not found: {GRAPH_VOCAB_NODES_PATH}")
        with open(GRAPH_VOCAB_NODES_PATH, "r", encoding="utf-8") as f:
            graph = json.load(f)
        print("Validating ulga_graph.vocabulary_nodes.json...")
        validate_vocabulary_graph(graph)
        
    except Exception as exc:
        print(f"ULGA vocabulary nodes validation: FAIL - {exc}")
        return 1
    
    print("ULGA vocabulary nodes validation: PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
