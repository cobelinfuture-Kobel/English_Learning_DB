import json
import sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

try:
    from ulga.validators.validate_ulga_schema import validate_edge, ValidationError, require
except ImportError:
    class ValidationError(Exception):
        pass

    def require(condition, message):
        if not condition:
            raise ValidationError(message)

    def validate_edge(edge, node_ids=None):
        # Fallback edge validator
        require(isinstance(edge, dict), "edge must be an object")
        require("id" in edge, "edge id is required")
        require("source_node_id" in edge, "source_node_id is required")
        require("target_node_id" in edge, "target_node_id is required")
        require("edge_type" in edge, "edge_type is required")
        if node_ids is not None:
            require(edge["source_node_id"] in node_ids, f"source_node_id {edge['source_node_id']} not found in nodes")
            require(edge["target_node_id"] in node_ids, f"target_node_id {edge['target_node_id']} not found in nodes")

NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
RULES_PATH = BASE_DIR / "ulga" / "rules" / "grammar_dependency_core_rules.json"
EDGES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_dependency_core_edges.json"
GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "ulga_graph.grammar_core_dependencies.json"

def find_cycles(nodes_set, edges):
    adj = defaultdict(list)
    for edge in edges:
        if edge["edge_type"] in ("prerequisite", "unlocks"):
            adj[edge["source_node_id"]].append(edge["target_node_id"])
            
    visited = {} # 1: visiting (stack), 2: visited (done)
    
    def dfs(node, path):
        visited[node] = 1
        path.append(node)
        for neighbor in adj[node]:
            if visited.get(neighbor) == 1:
                cycle_start_idx = path.index(neighbor)
                return path[cycle_start_idx:] + [neighbor]
            elif visited.get(neighbor) != 2:
                cycle_path = dfs(neighbor, path)
                if cycle_path:
                    return cycle_path
        path.pop()
        visited[node] = 2
        return None

    for node in nodes_set:
        if visited.get(node) != 2:
            cycle = dfs(node, [])
            if cycle:
                return cycle
    return None

def validate_core_dependencies():
    # 1. Check file existence
    require(NODES_PATH.exists(), f"File does not exist: {NODES_PATH}")
    require(RULES_PATH.exists(), f"File does not exist: {RULES_PATH}")
    require(EDGES_PATH.exists(), f"File does not exist: {EDGES_PATH}")
    require(GRAPH_PATH.exists(), f"File does not exist: {GRAPH_PATH}")

    # 2. Load data
    with open(NODES_PATH, "r", encoding="utf-8") as f:
        nodes = json.load(f)
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        rules = json.load(f)
    with open(EDGES_PATH, "r", encoding="utf-8") as f:
        edges = json.load(f)
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    node_ids = {n["id"] for n in nodes}

    # 3. Rule count checks
    enabled_rules = [r for r in rules if r.get("enabled", True)]
    require(100 <= len(enabled_rules) <= 300, f"Enabled rules count must be between 100 and 300, got: {len(enabled_rules)}")

    # 4. Edge checks
    require(len(edges) > 0, "Edge count must be greater than 0")
    seen_edges = set()

    for idx, edge in enumerate(edges):
        # Schema compliance
        validate_edge(edge, node_ids=node_ids)

        # Source / Target must be grammar nodes
        require(edge["source_node_id"].startswith("grammar:"), f"Source is not a grammar node: {edge['source_node_id']}")
        require(edge["target_node_id"].startswith("grammar:"), f"Target is not a grammar node: {edge['target_node_id']}")

        # No self-loop
        require(edge["source_node_id"] != edge["target_node_id"], f"Self-loop detected on edge: {edge['id']}")

        # No duplicate edge tuple
        edge_tuple = (edge["source_node_id"], edge["target_node_id"], edge["edge_type"])
        require(edge_tuple not in seen_edges, f"Duplicate edge tuple detected: {edge_tuple}")
        seen_edges.add(edge_tuple)

        # Confidence checks
        conf = edge.get("confidence", {})
        require(conf.get("value", 1.0) < 1.0, f"Confidence value must be less than 1.0, got: {conf.get('value')}")
        require(conf.get("method") == "rule_based", f"Confidence method must be 'rule_based', got: {conf.get('method')}")

        # Metadata checks
        meta = edge.get("metadata", {})
        require(meta.get("cefr_is_not_order") is True, f"metadata.cefr_is_not_order must be true in edge: {edge['id']}")
        require(meta.get("rule_based") is True, f"metadata.rule_based must be true in edge: {edge['id']}")
        require(meta.get("mounting_stage") == "ULGA-S4B", f"metadata.mounting_stage must be ULGA-S4B in edge: {edge['id']}")
        
        # Progression fields checks
        require("progression_band" in meta, f"progression_band is missing in edge: {edge['id']}")
        require("progression_stage" in meta, f"progression_stage is missing in edge: {edge['id']}")
        require("progression_score" in meta, f"progression_score is missing in edge: {edge['id']}")

        # Validate cefr levels (no + allowed)
        cefr_level = s_node = [n for n in nodes if n["id"] == edge["source_node_id"]][0].get("cefr_level")
        t_node = [n for n in nodes if n["id"] == edge["target_node_id"]][0].get("cefr_level")
        require("+" not in str(cefr_level), f"Source node {edge['source_node_id']} has forbidden plus level as CEFR: {cefr_level}")
        require("+" not in str(t_node), f"Target node {edge['target_node_id']} has forbidden plus level as CEFR: {t_node}")

    # 5. Graph wrapper checks
    require(graph.get("formal_data_mounted") is True, "Graph formal_data_mounted must be true")
    require(graph.get("mounted_stage") == "ULGA-S4B", "Graph mounted_stage must be ULGA-S4B")
    require(graph.get("node_count") == len(nodes), f"Graph node_count ({graph.get('node_count')}) does not match nodes count ({len(nodes)})")
    require(graph.get("edge_count") == len(edges), f"Graph edge_count ({graph.get('edge_count')}) does not match edges count ({len(edges)})")
    
    # Check that forbidden nodes are not in nodes list
    for node in graph.get("nodes", []):
        require(node["node_type"] == "grammar", f"Forbidden node type found: {node['node_type']} for node {node['id']}")

    # 6. Cycle check on prerequisite and unlocks
    cycle = find_cycles(node_ids, edges)
    if cycle is not None:
        raise ValidationError(f"Cycle detected in prerequisite/unlocks graph! Path: {' -> '.join(cycle)}")

    print(f"Validation: SUCCESS. Verified {len(edges)} edges and verified DAG status.")

def main():
    try:
        validate_core_dependencies()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"ULGA core dependencies validation: FAIL - {exc}")
        return 1
    
    print("ULGA core dependencies validation: PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
