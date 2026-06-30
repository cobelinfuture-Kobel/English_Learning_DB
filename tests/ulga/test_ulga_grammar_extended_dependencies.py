import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
GRAPH_DIR = BASE_DIR / "ulga" / "graph"
RULES_DIR = BASE_DIR / "ulga" / "rules"
REPORTS_DIR = BASE_DIR / "ulga" / "reports"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_ulga_grammar_extended_dependencies.py"


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_extended_files_exist():
    assert (RULES_DIR / "grammar_dependency_extended_rules.json").exists()
    assert (GRAPH_DIR / "grammar_dependency_extended_edges.json").exists()
    assert (GRAPH_DIR / "grammar_dependency_all_edges.json").exists()
    assert (GRAPH_DIR / "ulga_graph.grammar_extended_dependencies.json").exists()
    assert (REPORTS_DIR / "grammar_dependency_extended_skipped_rules.json").exists()
    assert (REPORTS_DIR / "grammar_dependency_extended_summary.json").exists()


def test_enabled_rule_count_target_checked():
    rules = load_json(RULES_DIR / "grammar_dependency_extended_rules.json")
    enabled = [rule for rule in rules if rule.get("enabled", True)]
    layer_a = [rule for rule in enabled if rule["layer"] == "extended_core"]
    layer_b = [rule for rule in enabled if rule["layer"] == "bridge"]
    assert 200 <= len(layer_a) <= 250
    assert 80 <= len(layer_b) <= 100
    assert 280 <= len(enabled) <= 350


def test_extended_edges_exist():
    edges = load_json(GRAPH_DIR / "grammar_dependency_extended_edges.json")
    assert len(edges) > 0


def test_all_edges_equals_core_plus_extended():
    core = load_json(GRAPH_DIR / "grammar_dependency_core_edges.json")
    extended = load_json(GRAPH_DIR / "grammar_dependency_extended_edges.json")
    all_edges = load_json(GRAPH_DIR / "grammar_dependency_all_edges.json")
    assert len(all_edges) == len(core) + len(extended)
    assert all_edges[: len(core)] == core
    assert all_edges[len(core) :] == extended


def test_no_duplicate_edges():
    all_edges = load_json(GRAPH_DIR / "grammar_dependency_all_edges.json")
    seen = set()
    for edge in all_edges:
        edge_tuple = (edge["source_node_id"], edge["target_node_id"], edge["edge_type"])
        assert edge_tuple not in seen
        seen.add(edge_tuple)


def test_no_self_loop():
    all_edges = load_json(GRAPH_DIR / "grammar_dependency_all_edges.json")
    for edge in all_edges:
        assert edge["source_node_id"] != edge["target_node_id"]


def test_no_missing_node_reference_and_no_non_grammar_nodes():
    nodes = load_json(GRAPH_DIR / "grammar_nodes.json")
    node_by_id = {node["id"]: node for node in nodes}
    all_edges = load_json(GRAPH_DIR / "grammar_dependency_all_edges.json")
    for edge in all_edges:
        assert edge["source_node_id"] in node_by_id
        assert edge["target_node_id"] in node_by_id
        assert node_by_id[edge["source_node_id"]]["node_type"] == "grammar"
        assert node_by_id[edge["target_node_id"]]["node_type"] == "grammar"


def test_no_plus_level_cefr():
    nodes = load_json(GRAPH_DIR / "grammar_nodes.json")
    for node in nodes:
        assert "+" not in str(node.get("cefr_level"))
    rules = load_json(RULES_DIR / "grammar_dependency_extended_rules.json")
    for rule in rules:
        for side in ["source_match", "target_match"]:
            for level in rule[side].get("cefr_level_in", []):
                assert "+" not in level


def test_no_advanced_layer_true():
    edges = load_json(GRAPH_DIR / "grammar_dependency_extended_edges.json")
    for edge in edges:
        assert edge["metadata"]["advanced_layer"] is False
        assert edge["metadata"]["mounting_stage"] == "ULGA-S4E"


def test_graph_wrapper_counts_and_flags():
    graph = load_json(GRAPH_DIR / "ulga_graph.grammar_extended_dependencies.json")
    core = load_json(GRAPH_DIR / "grammar_dependency_core_edges.json")
    extended = load_json(GRAPH_DIR / "grammar_dependency_extended_edges.json")
    assert graph["formal_data_mounted"] is True
    assert graph["mounted_stage"] == "ULGA-S4E"
    assert graph["node_count"] == 1222
    assert graph["core_edge_count"] == len(core)
    assert graph["extended_edge_count"] == len(extended)
    assert graph["total_edge_count"] == len(core) + len(extended)
    assert graph["implemented_layers"] == ["core", "extended_core", "bridge"]
    assert graph["advanced_layer_implemented"] is False
    assert graph["plus_levels_used_as_cefr"] is False


def test_hard_dag_cycle_check_pass():
    edges = load_json(GRAPH_DIR / "grammar_dependency_all_edges.json")
    nodes = load_json(GRAPH_DIR / "grammar_nodes.json")
    node_ids = {node["id"] for node in nodes}
    adj = defaultdict(list)
    for edge in edges:
        if edge["edge_type"] in ("prerequisite", "unlocks"):
            adj[edge["source_node_id"]].append(edge["target_node_id"])
    visited = {}

    def dfs(node):
        visited[node] = 1
        for neighbor in adj[node]:
            if visited.get(neighbor) == 1:
                return True
            if visited.get(neighbor) != 2 and dfs(neighbor):
                return True
        visited[node] = 2
        return False

    for node_id in node_ids:
        if visited.get(node_id) != 2:
            assert dfs(node_id) is False


def test_validation_script_passes():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ULGA extended grammar dependencies validation: PASS" in result.stdout
