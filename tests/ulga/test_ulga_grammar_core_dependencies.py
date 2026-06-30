import json
import sys
import subprocess
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[2]
GRAPH_DIR = BASE_DIR / "ulga" / "graph"
RULES_DIR = BASE_DIR / "ulga" / "rules"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_ulga_grammar_core_dependencies.py"

def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def test_files_exist():
    assert (RULES_DIR / "grammar_dependency_core_rules.json").exists()
    assert (GRAPH_DIR / "grammar_dependency_core_edges.json").exists()
    assert (GRAPH_DIR / "ulga_graph.grammar_core_dependencies.json").exists()

def test_enabled_rules_count():
    rules = load_json(RULES_DIR / "grammar_dependency_core_rules.json")
    enabled = [r for r in rules if r.get("enabled", True)]
    assert 100 <= len(enabled) <= 300
    
def test_cefr_levels_in_rules_no_plus():
    rules = load_json(RULES_DIR / "grammar_dependency_core_rules.json")
    for r in rules:
        source_match = r.get("source_match", {})
        target_match = r.get("target_match", {})
        
        # Check source cefr level filter
        if "cefr_level_in" in source_match:
            for lvl in source_match["cefr_level_in"]:
                assert "+" not in lvl, f"Plus level '{lvl}' found in rule source match cefr levels"
        # Check target cefr level filter
        if "cefr_level_in" in target_match:
            for lvl in target_match["cefr_level_in"]:
                assert "+" not in lvl, f"Plus level '{lvl}' found in rule target match cefr levels"

def test_edges_exist_and_non_empty():
    edges = load_json(GRAPH_DIR / "grammar_dependency_core_edges.json")
    assert len(edges) > 0

def test_all_edge_ids_exist_in_nodes():
    nodes = load_json(GRAPH_DIR / "grammar_nodes.json")
    node_ids = {n["id"] for n in nodes}
    edges = load_json(GRAPH_DIR / "grammar_dependency_core_edges.json")
    
    for edge in edges:
        assert edge["source_node_id"] in node_ids, f"Source node {edge['source_node_id']} not found in grammar_nodes"
        assert edge["target_node_id"] in node_ids, f"Target node {edge['target_node_id']} not found in grammar_nodes"
        assert edge["source_node_id"].startswith("grammar:")
        assert edge["target_node_id"].startswith("grammar:")

def test_no_self_loops():
    edges = load_json(GRAPH_DIR / "grammar_dependency_core_edges.json")
    for edge in edges:
        assert edge["source_node_id"] != edge["target_node_id"], f"Self-loop detected on edge {edge['id']}"

def test_no_duplicate_edges():
    edges = load_json(GRAPH_DIR / "grammar_dependency_core_edges.json")
    seen = set()
    for edge in edges:
        edge_tuple = (edge["source_node_id"], edge["target_node_id"], edge["edge_type"])
        assert edge_tuple not in seen, f"Duplicate edge tuple {edge_tuple} detected"
        seen.add(edge_tuple)

def test_confidence_properties():
    edges = load_json(GRAPH_DIR / "grammar_dependency_core_edges.json")
    for edge in edges:
        assert edge["confidence"]["value"] < 1.0
        assert edge["confidence"]["method"] == "rule_based"

def test_metadata_properties():
    edges = load_json(GRAPH_DIR / "grammar_dependency_core_edges.json")
    for edge in edges:
        meta = edge["metadata"]
        assert meta["cefr_is_not_order"] is True
        assert meta["rule_based"] is True
        assert meta["mounting_stage"] == "ULGA-S4B"
        
        # Check progression fields exist
        assert "progression_band" in meta
        assert "progression_stage" in meta
        assert "progression_score" in meta

def test_no_forbidden_node_types_in_graph():
    graph = load_json(GRAPH_DIR / "ulga_graph.grammar_core_dependencies.json")
    assert graph["node_count"] == 1222
    assert len(graph["nodes"]) == 1222
    
    forbidden = {"vocabulary", "chunk", "theme", "learner_state"}
    for node in graph["nodes"]:
        assert node["node_type"] == "grammar"
        assert node["node_type"] not in forbidden

def test_graph_metadata_targeted_cefr_plus_levels_used():
    graph = load_json(GRAPH_DIR / "ulga_graph.grammar_core_dependencies.json")
    assert graph["metadata"]["plus_levels_used_as_cefr"] is False
    assert graph["formal_data_mounted"] is True
    assert graph["mounted_stage"] == "ULGA-S4B"

def test_no_cycles_in_prerequisite_unlocks():
    edges = load_json(GRAPH_DIR / "grammar_dependency_core_edges.json")
    nodes = load_json(GRAPH_DIR / "grammar_nodes.json")
    node_ids = {n["id"] for n in nodes}
    
    adj = defaultdict(list)
    for edge in edges:
        if edge["edge_type"] in ("prerequisite", "unlocks"):
            adj[edge["source_node_id"]].append(edge["target_node_id"])
            
    visited = {}
    
    def dfs(node, path):
        visited[node] = 1
        path.append(node)
        for neighbor in adj[node]:
            if visited.get(neighbor) == 1:
                return True
            elif visited.get(neighbor) != 2:
                if dfs(neighbor, path):
                    return True
        path.pop()
        visited[node] = 2
        return False

    for node in node_ids:
        if visited.get(node) != 2:
            assert dfs(node, []) is False, "Cycle detected in prerequisite/unlocks dependency graph"

def test_validation_script_passes():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ULGA core dependencies validation: PASS" in result.stdout
