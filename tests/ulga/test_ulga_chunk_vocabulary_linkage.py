import json
from pathlib import Path
from ulga.validators.validate_ulga_chunk_vocabulary_linkage import validate, EDGES_PATH, GRAPH_PATH

def test_chunk_vocabulary_linkage_files_exist():
    assert EDGES_PATH.exists(), f"Edges file not found at {EDGES_PATH}"
    assert GRAPH_PATH.exists(), f"Graph wrapper file not found at {GRAPH_PATH}"

def test_chunk_vocabulary_linkage_non_empty():
    with open(EDGES_PATH, "r", encoding="utf-8") as f:
        edges = json.load(f)
    assert len(edges) > 0, "No edges generated in chunk_vocabulary_edges.json"

def test_chunk_vocabulary_linkage_endpoint_types():
    with open(EDGES_PATH, "r", encoding="utf-8") as f:
        edges = json.load(f)
    for edge in edges:
        src = edge.get("source_node_id")
        tgt = edge.get("target_node_id")
        etype = edge.get("edge_type")
        assert src.startswith("chunk:"), f"Invalid source node ID: {src}"
        assert tgt.startswith("vocabulary:"), f"Invalid target node ID: {tgt}"
        assert etype == "uses", f"Invalid edge type: {etype}"

def test_chunk_vocabulary_linkage_metadata():
    with open(EDGES_PATH, "r", encoding="utf-8") as f:
        edges = json.load(f)
    for edge in edges:
        meta = edge.get("metadata", {})
        assert meta.get("relation_family") == "chunk_vocabulary"
        assert meta.get("mounting_stage") == "ULGA-S6D"
        assert meta.get("sense_resolution_method") in {
            "exact_unique_sense",
            "exact_multi_same_topic",
            "topic_assisted",
            "polysemy_fallback",
            "unresolved"
        }
        assert edge.get("confidence", {}).get("method") == meta.get("sense_resolution_method")

def test_chunk_vocabulary_linkage_validator_pass():
    assert validate() is True, "Linkage validator failed"
