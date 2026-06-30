import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
GRAPH_DIR = BASE_DIR / "ulga" / "graph"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_ulga_schema.py"


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_empty_scaffold_files_exist_and_are_valid_json():
    for filename in [
        "ulga_nodes.empty.json",
        "ulga_edges.empty.json",
        "ulga_graph.empty.json",
    ]:
        path = GRAPH_DIR / filename
        assert path.exists(), f"Missing {filename}"
        load_json(path)


def test_empty_node_and_edge_scaffolds_contain_no_formal_data():
    assert load_json(GRAPH_DIR / "ulga_nodes.empty.json") == []
    assert load_json(GRAPH_DIR / "ulga_edges.empty.json") == []


def test_empty_graph_scaffold_contains_no_formal_data():
    graph = load_json(GRAPH_DIR / "ulga_graph.empty.json")
    assert graph["formal_data_mounted"] is False
    assert graph["nodes"] == []
    assert graph["edges"] == []
    assert graph["metadata"]["data_policy"] == "empty_scaffold_only"


def test_validate_ulga_schema_script_passes():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ULGA schema validation: PASS" in result.stdout
