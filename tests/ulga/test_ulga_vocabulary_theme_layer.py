import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
GRAPH_DIR = BASE_DIR / "ulga" / "graph"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_ulga_vocabulary_theme_layer.py"


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_theme_layer_files_exist():
    assert (GRAPH_DIR / "theme_nodes.json").exists()
    assert (GRAPH_DIR / "vocabulary_theme_edges.json").exists()
    assert (GRAPH_DIR / "ulga_graph.vocabulary_theme_layer.json").exists()


def test_theme_node_count_greater_than_zero():
    theme_nodes = load_json(GRAPH_DIR / "theme_nodes.json")
    assert len(theme_nodes) > 0
    assert all(node["node_type"] == "theme" for node in theme_nodes)


def test_theme_edge_count_greater_than_zero_and_mapped_count_target():
    graph = load_json(GRAPH_DIR / "ulga_graph.vocabulary_theme_layer.json")
    assert graph["theme_edge_count"] > 0
    assert graph["mapped_vocabulary_count"] >= 9000


def test_all_edges_source_vocabulary_to_target_theme_and_belongs_to():
    vocabulary_nodes = load_json(GRAPH_DIR / "vocabulary_nodes.json")
    theme_nodes = load_json(GRAPH_DIR / "theme_nodes.json")
    edges = load_json(GRAPH_DIR / "vocabulary_theme_edges.json")
    vocabulary_ids = {node["id"] for node in vocabulary_nodes}
    theme_ids = {node["id"] for node in theme_nodes}
    for edge in edges:
        assert edge["edge_type"] == "belongs_to"
        assert edge["source_node_id"] in vocabulary_ids
        assert edge["target_node_id"] in theme_ids


def test_all_metadata_sense_specific_and_not_lemma_level():
    edges = load_json(GRAPH_DIR / "vocabulary_theme_edges.json")
    for edge in edges:
        assert edge["metadata"]["sense_specific"] is True
        assert edge["metadata"]["lemma_level_assignment"] is False
        assert edge["metadata"]["mounting_stage"] == "ULGA-S5E"


def test_no_duplicate_edges():
    edges = load_json(GRAPH_DIR / "vocabulary_theme_edges.json")
    seen = set()
    for edge in edges:
        edge_tuple = (edge["source_node_id"], edge["target_node_id"], edge["edge_type"])
        assert edge_tuple not in seen
        seen.add(edge_tuple)


def test_no_forbidden_edge_types():
    edges = load_json(GRAPH_DIR / "vocabulary_theme_edges.json")
    forbidden = {"prerequisite", "supports", "unlocks", "reviews", "contrasts_with", "uses", "contains", "spiral_to", "assesses"}
    for edge in edges:
        assert edge["edge_type"] not in forbidden


def test_graph_wrapper_flags():
    graph = load_json(GRAPH_DIR / "ulga_graph.vocabulary_theme_layer.json")
    assert graph["formal_data_mounted"] is True
    assert graph["mounted_stage"] == "ULGA-S5E"
    assert graph["sense_specific_theme_assignment"] is True
    assert graph["lemma_level_theme_assignment"] is False
    assert graph["morphology_layer_implemented"] is False
    assert graph["chunk_layer_implemented"] is False
    assert graph["vocabulary_dependency_layer_implemented"] is False


def test_validator_passes():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ULGA vocabulary theme layer validation: PASS" in result.stdout
