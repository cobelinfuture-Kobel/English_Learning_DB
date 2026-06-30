import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
GRAPH_DIR = BASE_DIR / "ulga" / "graph"
GRAMMAR_PROFILE_PATH = BASE_DIR / "grammar_profile" / "json" / "grammar_profile.json"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_ulga_grammar_nodes.py"

def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def test_files_exist():
    assert (GRAPH_DIR / "grammar_nodes.json").exists()
    assert (GRAPH_DIR / "ulga_graph.grammar_nodes.json").exists()

def test_grammar_node_count():
    nodes = load_json(GRAPH_DIR / "grammar_nodes.json")
    profile = load_json(GRAMMAR_PROFILE_PATH)
    assert len(nodes) == len(profile)
    assert len(nodes) == 1222

def test_all_node_types():
    nodes = load_json(GRAPH_DIR / "grammar_nodes.json")
    for n in nodes:
        assert n["node_type"] == "grammar"

def test_all_ids_unique():
    nodes = load_json(GRAPH_DIR / "grammar_nodes.json")
    ids = [n["id"] for n in nodes]
    assert len(ids) == len(set(ids))

def test_all_source_record_ids_unique():
    nodes = load_json(GRAPH_DIR / "grammar_nodes.json")
    src_ids = [n["metadata"]["source_record_id"] for n in nodes]
    assert len(src_ids) == len(set(src_ids))

def test_graph_properties():
    graph = load_json(GRAPH_DIR / "ulga_graph.grammar_nodes.json")
    assert graph["formal_data_mounted"] is True
    assert graph["mounted_stage"] == "ULGA-S4A"
    assert graph["edges"] == []
    assert graph["edge_count"] == 0
    assert graph["node_count"] == len(graph["nodes"])

def test_no_forbidden_node_types():
    graph = load_json(GRAPH_DIR / "ulga_graph.grammar_nodes.json")
    forbidden = {"vocabulary", "chunk", "theme", "learner_state"}
    for n in graph["nodes"]:
        assert n["node_type"] not in forbidden

def test_schema_validation_script_passes():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ULGA grammar nodes validation: PASS" in result.stdout
