import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
GRAPH_DIR = BASE_DIR / "ulga" / "graph"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_ulga_vocabulary_theme_refinement.py"


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_refined_files_exist():
    assert (GRAPH_DIR / "vocabulary_theme_edges.refined.json").exists()
    assert (GRAPH_DIR / "ulga_graph.vocabulary_theme_layer.refined.json").exists()


def test_refined_edge_count_reduced_and_original_preserved():
    original_edges = load_json(GRAPH_DIR / "vocabulary_theme_edges.json")
    refined_edges = load_json(GRAPH_DIR / "vocabulary_theme_edges.refined.json")
    graph = load_json(GRAPH_DIR / "ulga_graph.vocabulary_theme_layer.refined.json")
    assert len(refined_edges) < len(original_edges)
    assert graph["original_theme_edge_count"] == len(original_edges)
    assert graph["refined_theme_edge_count"] == len(refined_edges)
    assert graph["original_full_layer_preserved"] is True


def test_mapped_count_and_average_edges_target():
    refined_edges = load_json(GRAPH_DIR / "vocabulary_theme_edges.refined.json")
    mapped = {edge["source_node_id"] for edge in refined_edges}
    assert len(mapped) >= 9000
    assert len(refined_edges) / len(mapped) <= 3


def test_no_vocabulary_node_has_more_than_three_theme_edges():
    refined_edges = load_json(GRAPH_DIR / "vocabulary_theme_edges.refined.json")
    counts = Counter(edge["source_node_id"] for edge in refined_edges)
    assert max(counts.values()) <= 3


def test_primary_and_secondary_caps_per_node():
    refined_edges = load_json(GRAPH_DIR / "vocabulary_theme_edges.refined.json")
    primary_counts = Counter()
    secondary_counts = Counter()
    for edge in refined_edges:
        role = edge["metadata"]["retained_role"]
        if role == "primary":
            primary_counts[edge["source_node_id"]] += 1
        if role == "secondary":
            secondary_counts[edge["source_node_id"]] += 1
    assert all(count <= 1 for count in primary_counts.values())
    assert all(count <= 2 for count in secondary_counts.values())


def test_all_edges_source_vocabulary_to_target_theme_and_belongs_to():
    vocabulary_nodes = load_json(GRAPH_DIR / "vocabulary_nodes.json")
    theme_nodes = load_json(GRAPH_DIR / "theme_nodes.json")
    refined_edges = load_json(GRAPH_DIR / "vocabulary_theme_edges.refined.json")
    vocabulary_ids = {node["id"] for node in vocabulary_nodes}
    theme_ids = {node["id"] for node in theme_nodes}
    for edge in refined_edges:
        assert edge["edge_type"] == "belongs_to"
        assert edge["source_node_id"] in vocabulary_ids
        assert edge["target_node_id"] in theme_ids


def test_all_metadata_sense_specific_and_refined():
    refined_edges = load_json(GRAPH_DIR / "vocabulary_theme_edges.refined.json")
    for edge in refined_edges:
        metadata = edge["metadata"]
        assert metadata["sense_specific"] is True
        assert metadata["lemma_level_assignment"] is False
        assert metadata["refined_from_original"] is True
        assert metadata["refinement_stage"] == "ULGA-S5E-REFINEMENT"
        assert metadata["original_edge_id"]


def test_graph_wrapper_flags():
    graph = load_json(GRAPH_DIR / "ulga_graph.vocabulary_theme_layer.refined.json")
    assert graph["formal_data_mounted"] is True
    assert graph["mounted_stage"] == "ULGA-S5E-REFINEMENT"
    assert graph["refinement_applied"] is True
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
    assert "ULGA vocabulary theme refinement validation: PASS" in result.stdout
