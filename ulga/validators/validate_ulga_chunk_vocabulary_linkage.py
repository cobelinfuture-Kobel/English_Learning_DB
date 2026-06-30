import json
import os
import sys
from pathlib import Path

# Setup base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

EDGES_PATH = BASE_DIR / "ulga" / "graph" / "chunk_vocabulary_edges.json"
GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "ulga_graph.chunk_vocabulary_linkage.json"

ALLOWED_METHODS = {
    "exact_unique_sense",
    "exact_multi_same_topic",
    "topic_assisted",
    "polysemy_fallback",
    "unresolved"
}

def validate():
    print("Validating Chunk-Vocabulary Linkage Layer...")
    
    # 1. Check file existence
    if not EDGES_PATH.exists():
        print(f"FAIL: Edges file does not exist at {EDGES_PATH}")
        return False
    if not GRAPH_PATH.exists():
        print(f"FAIL: Graph wrapper file does not exist at {GRAPH_PATH}")
        return False
        
    # 2. Load data
    try:
        with open(EDGES_PATH, "r", encoding="utf-8") as f:
            edges = json.load(f)
    except Exception as e:
        print(f"FAIL: Failed to parse edges JSON: {e}")
        return False
        
    try:
        with open(GRAPH_PATH, "r", encoding="utf-8") as f:
            graph = json.load(f)
    except Exception as e:
        print(f"FAIL: Failed to parse graph JSON: {e}")
        return False
        
    # 3. Check edge count
    edge_count = len(edges)
    if edge_count == 0:
        print("FAIL: Edge count is 0.")
        return False
    print(f"Parsed {edge_count} edges for validation.")
    
    # 4. Check graph wrapper consistency
    if graph.get("chunk_vocabulary_edge_count") != edge_count:
        print(f"FAIL: Graph wrapper chunk_vocabulary_edge_count ({graph.get('chunk_vocabulary_edge_count')}) does not match actual edge count ({edge_count}).")
        return False
    if len(graph.get("edges", [])) != edge_count:
        print(f"FAIL: Graph wrapper edges array size ({len(graph.get('edges', []))}) does not match actual edge count ({edge_count}).")
        return False
    if graph.get("nodes") != []:
        print(f"FAIL: Graph wrapper nodes array must be empty (got {graph.get('nodes')}).")
        return False
    if graph.get("formal_data_mounted") is not True:
        print("FAIL: Graph wrapper formal_data_mounted must be True.")
        return False
    if graph.get("mounted_stage") != "ULGA-S6D":
        print(f"FAIL: Graph wrapper mounted_stage must be 'ULGA-S6D' (got '{graph.get('mounted_stage')}').")
        return False
        
    # 5. Check individual edges
    seen_edge_keys = set()
    for idx, edge in enumerate(edges):
        edge_id = edge.get("id")
        src = edge.get("source_node_id")
        tgt = edge.get("target_node_id")
        etype = edge.get("edge_type")
        dir_val = edge.get("direction")
        conf = edge.get("confidence", {})
        metadata = edge.get("metadata", {})
        
        # Check IDs
        if not edge_id:
            print(f"FAIL: Edge at index {idx} has no ID.")
            return False
            
        # Check source is chunk and target is vocabulary
        if not src or not src.startswith("chunk:"):
            print(f"FAIL: Edge {edge_id} source_node_id must start with 'chunk:' (got '{src}').")
            return False
        if not tgt or not tgt.startswith("vocabulary:"):
            print(f"FAIL: Edge {edge_id} target_node_id must start with 'vocabulary:' (got '{tgt}').")
            return False
            
        # Check self-loops
        if src == tgt:
            print(f"FAIL: Self-loop detected on edge {edge_id} ('{src}' -> '{tgt}').")
            return False
            
        # Check edge type and direction
        if etype != "uses":
            print(f"FAIL: Edge {edge_id} edge_type must be 'uses' (got '{etype}').")
            return False
        if dir_val != "from_requires_to":
            print(f"FAIL: Edge {edge_id} direction must be 'from_requires_to' (got '{dir_val}').")
            return False
            
        # Check confidence
        conf_val = conf.get("value")
        conf_method = conf.get("method")
        if conf_val is None or not (0.0 <= conf_val <= 1.0):
            print(f"FAIL: Edge {edge_id} confidence value must be between 0.0 and 1.0 (got {conf_val}).")
            return False
        if conf_method not in ALLOWED_METHODS:
            print(f"FAIL: Edge {edge_id} confidence method must be in {ALLOWED_METHODS} (got '{conf_method}').")
            return False
            
        # Check metadata
        if metadata.get("relation_family") != "chunk_vocabulary":
            print(f"FAIL: Edge {edge_id} metadata relation_family must be 'chunk_vocabulary' (got '{metadata.get('relation_family')}').")
            return False
        if metadata.get("sense_resolution_method") not in ALLOWED_METHODS:
            print(f"FAIL: Edge {edge_id} metadata sense_resolution_method must be in {ALLOWED_METHODS} (got '{metadata.get('sense_resolution_method')}').")
            return False
        if metadata.get("confidence_method") != conf_method:
            print(f"FAIL: Edge {edge_id} metadata confidence_method does not match confidence method.")
            return False
        if metadata.get("mounting_stage") != "ULGA-S6D":
            print(f"FAIL: Edge {edge_id} metadata mounting_stage must be 'ULGA-S6D'.")
            return False
            
        # Check duplicate edges
        token_pos = metadata.get("token_position")
        if token_pos is None:
            # For backward compatibility if token_position not set (though we set it)
            edge_key = (src, tgt, etype)
        else:
            edge_key = (src, tgt, etype, token_pos)
            
        if edge_key in seen_edge_keys:
            print(f"FAIL: Duplicate edge detected for key {edge_key} on edge {edge_id}.")
            return False
        seen_edge_keys.add(edge_key)
        
    print("ULGA chunk-vocabulary linkage validation: PASS")
    return True

if __name__ == "__main__":
    success = validate()
    if not success:
        sys.exit(1)
