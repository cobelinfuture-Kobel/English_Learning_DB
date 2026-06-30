import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_ulga_chunk_nodes import main as validate_main


CHUNK_NODES_PATH = BASE_DIR / "ulga" / "graph" / "chunk_nodes.json"
GRAPH_CHUNK_NODES_PATH = BASE_DIR / "ulga" / "graph" / "ulga_graph.chunk_nodes.json"


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_chunk_node_files_exist():
    assert CHUNK_NODES_PATH.exists(), f"chunk_nodes.json not found at {CHUNK_NODES_PATH}"
    assert GRAPH_CHUNK_NODES_PATH.exists(), f"ulga_graph.chunk_nodes.json not found at {GRAPH_CHUNK_NODES_PATH}"


def test_chunk_node_count_and_types():
    nodes = load_json(CHUNK_NODES_PATH)

    assert len(nodes) > 0, "No chunk nodes were mounted."

    seen_ids = set()
    seen_canonical_chunks = set()
    for node in nodes:
        assert node["node_type"] == "chunk", f"Invalid node_type in node {node.get('id')}"
        assert node["id"].startswith("chunk:"), f"Invalid ID prefix in node {node.get('id')}"
        assert node["id"] not in seen_ids, f"Duplicate node ID: {node['id']}"
        seen_ids.add(node["id"])

        metadata = node["metadata"]
        canonical_chunk = metadata["canonical_chunk"]
        assert canonical_chunk not in seen_canonical_chunks, f"Duplicate canonical chunk: {canonical_chunk}"
        seen_canonical_chunks.add(canonical_chunk)
        assert node["id"] == f"chunk:{canonical_chunk}"


def test_chunk_graph_wrapper():
    graph = load_json(GRAPH_CHUNK_NODES_PATH)

    assert graph.get("graph_id") == "ulga_graph.chunk_nodes"
    assert graph.get("contract_version") == "ULGA-S2"
    assert graph.get("schema_version") == "1.0.0"
    assert graph.get("formal_data_mounted") is True
    assert graph.get("mounted_stage") == "ULGA-S6B"
    assert graph.get("nodes")
    assert graph.get("node_count") == len(graph["nodes"])
    assert graph.get("chunk_node_count") == len(graph["nodes"])
    assert graph.get("edges") == []
    assert graph.get("edge_count") == 0
    assert graph.get("chunk_vocabulary_linkage") is False
    assert graph.get("chunk_theme_projection") is False
    assert graph.get("chunk_grammar_metadata") is False


def test_no_non_chunk_nodes_or_edges():
    graph = load_json(GRAPH_CHUNK_NODES_PATH)

    assert graph["edges"] == []
    forbidden_node_types = {"vocabulary", "grammar", "theme", "morphology", "learner_state"}
    for node in graph["nodes"]:
        assert node["node_type"] not in forbidden_node_types


def test_validator_run():
    exit_code = validate_main()
    assert exit_code == 0, "Chunk node validator failed."
