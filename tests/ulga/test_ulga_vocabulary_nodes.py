import json
import sys
from pathlib import Path
import pytest

# Add project root to sys.path so we can import ulga
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_ulga_vocabulary_nodes import main as validate_main

VOCAB_NODES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json"
GRAPH_VOCAB_NODES_PATH = BASE_DIR / "ulga" / "graph" / "ulga_graph.vocabulary_nodes.json"

def test_node_files_exist():
    assert VOCAB_NODES_PATH.exists(), f"vocabulary_nodes.json not found at {VOCAB_NODES_PATH}"
    assert GRAPH_VOCAB_NODES_PATH.exists(), f"ulga_graph.vocabulary_nodes.json not found at {GRAPH_VOCAB_NODES_PATH}"

def test_node_counts_and_types():
    with open(VOCAB_NODES_PATH, "r", encoding="utf-8") as f:
        nodes = json.load(f)
    
    assert len(nodes) > 0, "No vocabulary nodes were mounted."
    assert len(nodes) == 15696, f"Expected 15696 nodes, got {len(nodes)}"
    
    seen_ids = set()
    for node in nodes:
        assert node["node_type"] == "vocabulary", f"Invalid node_type in node {node.get('id')}"
        assert node["id"].startswith("vocabulary:"), f"Invalid ID prefix in node {node.get('id')}"
        assert node["id"] not in seen_ids, f"Duplicate node ID: {node['id']}"
        seen_ids.add(node["id"])
        
        # Test required schema keys
        assert "id" in node
        assert "label" in node
        assert "authority_source" in node
        assert "cefr_level" in node
        assert "confidence" in node
        assert "version" in node
        assert "metadata" in node

def test_graph_wrapper():
    with open(GRAPH_VOCAB_NODES_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
        
    assert graph.get("graph_id") == "ulga_graph.vocabulary_nodes"
    assert graph.get("contract_version") == "ULGA-S2"
    assert graph.get("schema_version") == "1.0.0"
    assert graph.get("formal_data_mounted") is True
    assert graph.get("mounted_stage") == "ULGA-S5B"
    assert len(graph.get("nodes", [])) == 15696
    assert graph.get("node_count") == 15696
    assert graph.get("edges") == []
    assert graph.get("edge_count") == 0
    assert graph.get("dependency_layer_implemented") is False
    assert graph.get("theme_layer_implemented") is False
    assert graph.get("morphology_layer_implemented") is False

def test_authority_source_and_metadata():
    with open(VOCAB_NODES_PATH, "r", encoding="utf-8") as f:
        nodes = json.load(f)
        
    # Check a few sample nodes for field values
    sample_node = nodes[0]
    auth = sample_node.get("authority_source", {})
    assert auth.get("source_name") == "English Vocabulary Profile (EVP) / NGSL_SFI"
    assert auth.get("source_file") == "vocabulary/json/vocabulary.json"
    assert auth.get("derivation") == "derived_safe_layer"
    
    meta = sample_node.get("metadata", {})
    assert "source_vocabulary_id" in meta
    assert "evp_level" in meta
    assert "frequency_rank" in meta
    assert "frequency_score" in meta
    assert "part_of_speech" in meta
    assert meta.get("mounting_stage") == "ULGA-S5B"
    assert meta.get("theme_tags") == []
    assert meta.get("chunk_count") == 0
    assert meta.get("grammar_prerequisites") == []

def test_validator_run():
    # Calling the validator main function should exit with code 0
    exit_code = validate_main()
    assert exit_code == 0, "Validator failed."
