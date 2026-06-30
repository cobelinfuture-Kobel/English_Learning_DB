import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
GRAPH_DIR = BASE_DIR / "ulga" / "graph"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_ulga_vocabulary_morphology_layer.py"

def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def test_morphology_files_exist():
    assert (GRAPH_DIR / "vocabulary_morphology_edges.json").exists()
    assert (GRAPH_DIR / "ulga_graph.vocabulary_morphology_layer.json").exists()

def test_morphology_edge_count_greater_than_zero():
    edges = load_json(GRAPH_DIR / "vocabulary_morphology_edges.json")
    graph = load_json(GRAPH_DIR / "ulga_graph.vocabulary_morphology_layer.json")
    assert len(edges) > 0
    assert graph["metadata"]["morphology_edge_count"] == len(edges)

def test_all_edges_vocabulary_to_vocabulary_and_supports():
    vocabulary_nodes = load_json(GRAPH_DIR / "vocabulary_nodes.json")
    edges = load_json(GRAPH_DIR / "vocabulary_morphology_edges.json")
    vocabulary_ids = {node["id"] for node in vocabulary_nodes}
    
    seen_tuples = set()
    for edge in edges:
        assert edge["edge_type"] == "supports"
        assert edge["source_node_id"] in vocabulary_ids
        assert edge["target_node_id"] in vocabulary_ids
        assert edge["source_node_id"] != edge["target_node_id"], f"Self-loop: {edge['id']}"
        
        edge_tuple = (edge["source_node_id"], edge["target_node_id"], edge["edge_type"])
        assert edge_tuple not in seen_tuples, f"Duplicate tuple: {edge_tuple}"
        seen_tuples.add(edge_tuple)

def test_no_morphology_nodes_or_hubs():
    graph = load_json(GRAPH_DIR / "ulga_graph.vocabulary_morphology_layer.json")
    
    # Assert nodes are only vocabulary nodes
    for node in graph["nodes"]:
        assert node["node_type"] == "vocabulary"
        assert node["id"].startswith("vocabulary:")
        
    assert graph["metadata"]["morphology_node_count"] == 0
    assert graph["metadata"]["word_family_hub_node_count"] == 0
    assert graph["metadata"]["morphology_nodes_created"] is False
    assert graph["metadata"]["word_family_hubs_created"] is False

def test_metadata_flags():
    edges = load_json(GRAPH_DIR / "vocabulary_morphology_edges.json")
    for edge in edges:
        metadata = edge["metadata"]
        assert metadata["relation_family"] == "morphology"
        assert metadata["word_family_hub_used"] is False
        assert metadata["morphology_node_created"] is False
        assert metadata["mounting_stage"] == "ULGA-S5I"
        assert metadata["sense_specific"] is True
        assert "inflection_promoted_to_lexical_node" in metadata

def test_confidence_values_and_method():
    edges = load_json(GRAPH_DIR / "vocabulary_morphology_edges.json")
    for edge in edges:
        confidence = edge["confidence"]
        assert confidence["value"] <= 0.85
        assert confidence["method"] == "rule_based"

def test_validator_passes():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ULGA vocabulary morphology layer validation: PASS" in result.stdout
