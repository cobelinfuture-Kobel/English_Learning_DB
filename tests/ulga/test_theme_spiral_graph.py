import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

THEME_SPIRAL_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "theme_spiral_graph.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "theme_spiral_graph_summary.json"
QA_AUDIT_PATH = BASE_DIR / "ulga" / "reports" / "theme_spiral_graph_qa_audit.json"
STAGE_GAP_REVIEW_QUEUE_PATH = BASE_DIR / "ulga" / "reports" / "theme_spiral_stage_gap_review_queue.json"
LEARNING_SIGNAL_POLICY_PATH = BASE_DIR / "ulga" / "schema" / "learning_signal_policy.json"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_theme_spiral_graph.py"

CEFR_ORDER = ["A1", "A1_plus", "A2", "A2_plus", "B1", "B1_plus", "B2", "B2_plus", "C1"]
CEFR_RANK = {level: index for index, level in enumerate(CEFR_ORDER)}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def has_cycle(edges):
    graph = defaultdict(list)
    for edge in edges:
        graph[edge["source_stage_id"]].append(edge["target_stage_id"])

    visiting = set()
    visited = set()

    def visit(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in graph.get(node, []):
            if visit(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in list(graph))


def test_builder_output_exists():
    assert THEME_SPIRAL_GRAPH_PATH.exists()
    assert SUMMARY_PATH.exists()
    graph = load_json(THEME_SPIRAL_GRAPH_PATH)
    summary = load_json(SUMMARY_PATH)
    assert graph["theme_stage_nodes"]
    assert graph["spiral_edges"]
    assert summary["stage_count"] == len(graph["theme_stage_nodes"])
    assert summary["spiral_edge_count"] == len(graph["spiral_edges"])


def test_schema_valid_minimal_shape():
    graph = load_json(THEME_SPIRAL_GRAPH_PATH)
    assert graph["graph_metadata"]["contract_version"] == "ULGA-S8H"
    for edge in graph["spiral_edges"]:
        for key in [
            "edge_id",
            "source_stage_id",
            "target_stage_id",
            "relation",
            "theme_id",
            "source_cefr",
            "target_cefr",
            "confidence",
            "review_status",
            "gate_eligible",
            "evidence",
            "notes",
        ]:
            assert key in edge
        assert edge["edge_id"].startswith("theme_spiral_edge:")


def test_theme_ids_valid():
    graph = load_json(THEME_SPIRAL_GRAPH_PATH)
    stage_theme_ids = {node["theme_id"] for node in graph["theme_stage_nodes"]}
    assert stage_theme_ids
    for edge in graph["spiral_edges"]:
        assert edge["theme_id"] in stage_theme_ids


def test_stage_ids_valid():
    graph = load_json(THEME_SPIRAL_GRAPH_PATH)
    stage_by_id = {node["stage_id"]: node for node in graph["theme_stage_nodes"]}
    for node in graph["theme_stage_nodes"]:
        assert node["stage_id"] == f"theme:{node['theme_id']}:{node['cefr_band']}"
    for edge in graph["spiral_edges"]:
        assert edge["source_stage_id"] in stage_by_id
        assert edge["target_stage_id"] in stage_by_id


def test_every_theme_stage_node_has_source_authority():
    graph = load_json(THEME_SPIRAL_GRAPH_PATH)
    for node in graph["theme_stage_nodes"]:
        authority = node["source_authority"]
        assert authority["authority_name"] == "ThemeAuthority"
        assert authority["source_theme_ids"] == node["source_theme_ids"]
        assert "themes/theme_catalog.json" in authority["source_files"]
        assert "themes/theme_vocab_mapping.json" in authority["source_files"]
        assert authority["derivation"]
        assert authority["normalization_policy"]
        assert authority["confidence_basis"]


def test_all_relations_spiral_to():
    graph = load_json(THEME_SPIRAL_GRAPH_PATH)
    assert all(edge["relation"] == "SPIRAL_TO" for edge in graph["spiral_edges"])


def test_all_gate_flags_false():
    graph = load_json(THEME_SPIRAL_GRAPH_PATH)
    assert all(edge["gate_eligible"] is False for edge in graph["spiral_edges"])


def test_no_cross_theme_edge():
    graph = load_json(THEME_SPIRAL_GRAPH_PATH)
    stage_by_id = {node["stage_id"]: node for node in graph["theme_stage_nodes"]}
    for edge in graph["spiral_edges"]:
        source_node = stage_by_id[edge["source_stage_id"]]
        target_node = stage_by_id[edge["target_stage_id"]]
        assert source_node["theme_id"] == target_node["theme_id"]
        assert edge["theme_id"] == source_node["theme_id"]


def test_no_backward_edge():
    graph = load_json(THEME_SPIRAL_GRAPH_PATH)
    for edge in graph["spiral_edges"]:
        assert CEFR_RANK[edge["target_cefr"]] > CEFR_RANK[edge["source_cefr"]]


def test_no_cycle():
    graph = load_json(THEME_SPIRAL_GRAPH_PATH)
    assert has_cycle(graph["spiral_edges"]) is False


def test_stage_gap_review_queue_exists_if_stage_gap_edges_exist():
    graph = load_json(THEME_SPIRAL_GRAPH_PATH)
    stage_gap_edges = [
        edge
        for edge in graph["spiral_edges"]
        if CEFR_RANK[edge["target_cefr"]] - CEFR_RANK[edge["source_cefr"]] > 1
    ]
    if stage_gap_edges:
        assert STAGE_GAP_REVIEW_QUEUE_PATH.exists()
        queue = load_json(STAGE_GAP_REVIEW_QUEUE_PATH)
        queue_by_edge_id = {entry["edge_id"]: entry for entry in queue}
        for edge in stage_gap_edges:
            entry = queue_by_edge_id[edge["edge_id"]]
            assert entry["gate_eligible"] is False
            assert entry["review_status"] == "needs_review"
            assert entry["review_reason"] == "absent_intermediate_cefr_stage"
            assert entry["missing_intermediate_cefr"]


def test_learning_signal_policy_compliance():
    graph = load_json(THEME_SPIRAL_GRAPH_PATH)
    policy = load_json(LEARNING_SIGNAL_POLICY_PATH)
    spiral_rule = next(
        rule for rule in policy["signal_mapping_rules"] if rule["source_relation"] == "SPIRAL_TO"
    )
    compliance = graph["graph_metadata"]["learning_signal_compliance"]
    assert spiral_rule["gate_allowed"] is False
    assert compliance["gate_allowed"] is False
    assert compliance["gate_signal_generated"] is False
    assert compliance["learning_signal_graph_generated"] is False


def test_no_learning_signal_graph_generated():
    assert not (BASE_DIR / "ulga" / "graph" / "learning_signal_graph.json").exists()


def test_validator_run():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_qa_audit_exists_if_generated():
    if QA_AUDIT_PATH.exists():
        audit = load_json(QA_AUDIT_PATH)
        assert audit["final_verdict"] in {"PASS", "PASS_WITH_WARNINGS"}
