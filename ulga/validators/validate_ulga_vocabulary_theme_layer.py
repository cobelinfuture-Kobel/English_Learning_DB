import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_ulga_schema import ValidationError, require, validate_edge, validate_node


GRAPH_DIR = BASE_DIR / "ulga" / "graph"
REPORTS_DIR = BASE_DIR / "ulga" / "reports"
RULES_DIR = BASE_DIR / "ulga" / "rules"

VOCAB_NODES_PATH = GRAPH_DIR / "vocabulary_nodes.json"
THEME_NODES_PATH = GRAPH_DIR / "theme_nodes.json"
EDGES_PATH = GRAPH_DIR / "vocabulary_theme_edges.json"
GRAPH_PATH = GRAPH_DIR / "ulga_graph.vocabulary_theme_layer.json"
RULES_PATH = RULES_DIR / "vocabulary_theme_mapping_rules.json"
SUMMARY_PATH = REPORTS_DIR / "vocabulary_theme_mapping_summary.json"
UNMAPPED_PATH = REPORTS_DIR / "vocabulary_theme_unmapped_nodes.json"


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_vocabulary_theme_layer():
    for path in [VOCAB_NODES_PATH, THEME_NODES_PATH, EDGES_PATH, GRAPH_PATH, RULES_PATH, SUMMARY_PATH, UNMAPPED_PATH]:
        require(path.exists(), f"Missing required file: {path}")

    vocabulary_nodes = read_json(VOCAB_NODES_PATH)
    theme_nodes = read_json(THEME_NODES_PATH)
    edges = read_json(EDGES_PATH)
    graph = read_json(GRAPH_PATH)
    rules = read_json(RULES_PATH)
    summary = read_json(SUMMARY_PATH)
    unmapped = read_json(UNMAPPED_PATH)

    vocabulary_ids = {node["id"] for node in vocabulary_nodes}
    theme_ids = {node["id"] for node in theme_nodes}
    all_node_ids = vocabulary_ids | theme_ids

    require(len(theme_nodes) > 0, "theme_node_count must be greater than 0")
    for node in theme_nodes:
        validate_node(node)
        require(node["node_type"] == "theme", f"theme node has invalid node_type: {node['id']}")
        require(node["id"].startswith("theme:"), f"theme node id must start with theme: {node['id']}")
        require(node["metadata"].get("mounting_stage") == "ULGA-S5E", f"theme node mounting_stage invalid: {node['id']}")

    require(len(edges) > 0, "theme_edge_count must be greater than 0")
    mapped_vocabulary_ids = set()
    seen = set()
    forbidden_edge_types = {"prerequisite", "supports", "unlocks", "reviews", "contrasts_with", "uses", "contains", "spiral_to", "assesses"}
    for edge in edges:
        validate_edge(edge, node_ids=all_node_ids)
        require(edge["edge_type"] == "belongs_to", f"edge_type must be belongs_to: {edge['id']}")
        require(edge["edge_type"] not in forbidden_edge_types, f"forbidden edge type created: {edge['id']}")
        require(edge["source_node_id"] in vocabulary_ids, f"source_node_id is not a vocabulary node: {edge['id']}")
        require(edge["target_node_id"] in theme_ids, f"target_node_id is not a theme node: {edge['id']}")
        require(edge["source_node_id"] != edge["target_node_id"], f"self-loop detected: {edge['id']}")
        edge_tuple = (edge["source_node_id"], edge["target_node_id"], edge["edge_type"])
        require(edge_tuple not in seen, f"duplicate edge tuple detected: {edge_tuple}")
        seen.add(edge_tuple)
        metadata = edge["metadata"]
        require(metadata.get("sense_specific") is True, f"sense_specific must be true: {edge['id']}")
        require(metadata.get("lemma_level_assignment") is False, f"lemma_level_assignment must be false: {edge['id']}")
        require(metadata.get("mounting_stage") == "ULGA-S5E", f"mounting_stage must be ULGA-S5E: {edge['id']}")
        require(metadata.get("morphology_layer_implemented") is False, f"morphology flag invalid: {edge['id']}")
        require(metadata.get("chunk_layer_implemented") is False, f"chunk flag invalid: {edge['id']}")
        require(metadata.get("vocabulary_dependency_layer_implemented") is False, f"dependency flag invalid: {edge['id']}")
        require(edge["confidence"]["value"] <= 1.0, f"confidence must be <= 1.0: {edge['id']}")
        require(edge["confidence"]["method"] in {"source_topic_mapping", "theme_mapping", "inferred_rule"}, f"invalid confidence method: {edge['id']}")
        mapped_vocabulary_ids.add(edge["source_node_id"])

    require(len(mapped_vocabulary_ids) >= 9000, f"mapped vocabulary node count must be >= 9000, got {len(mapped_vocabulary_ids)}")
    require(isinstance(unmapped, list), "unmapped node report must be a list")
    require(len(rules) > 0, "mapping rules must be non-empty")

    require(graph.get("formal_data_mounted") is True, "graph formal_data_mounted must be true")
    require(graph.get("mounted_stage") == "ULGA-S5E", "graph mounted_stage must be ULGA-S5E")
    require(graph.get("vocabulary_node_count") == len(vocabulary_nodes), "graph vocabulary_node_count mismatch")
    require(graph.get("theme_node_count") == len(theme_nodes), "graph theme_node_count mismatch")
    require(graph.get("theme_edge_count") == len(edges), "graph theme_edge_count mismatch")
    require(graph.get("mapped_vocabulary_count") == len(mapped_vocabulary_ids), "graph mapped_vocabulary_count mismatch")
    require(graph.get("unmapped_vocabulary_count") == len(unmapped), "graph unmapped_vocabulary_count mismatch")
    require(graph.get("sense_specific_theme_assignment") is True, "graph sense_specific_theme_assignment must be true")
    require(graph.get("lemma_level_theme_assignment") is False, "graph lemma_level_theme_assignment must be false")
    require(graph.get("morphology_layer_implemented") is False, "graph morphology_layer_implemented must be false")
    require(graph.get("chunk_layer_implemented") is False, "graph chunk_layer_implemented must be false")
    require(graph.get("vocabulary_dependency_layer_implemented") is False, "graph vocabulary_dependency_layer_implemented must be false")
    require(graph.get("learner_state_implemented") is False, "graph learner_state_implemented must be false")
    require(graph.get("planner_implemented") is False, "graph planner_implemented must be false")
    require(graph.get("recommendation_implemented") is False, "graph recommendation_implemented must be false")

    require(summary.get("theme_edge_count") == len(edges), "summary theme_edge_count mismatch")
    require(summary.get("mapped_vocabulary_count") == len(mapped_vocabulary_ids), "summary mapped_vocabulary_count mismatch")
    print(
        "Validation: SUCCESS. "
        f"Verified {len(theme_nodes)} theme nodes, {len(edges)} belongs_to edges, "
        f"and {len(mapped_vocabulary_ids)} mapped vocabulary nodes."
    )


def main():
    try:
        validate_vocabulary_theme_layer()
    except Exception as exc:
        import traceback

        traceback.print_exc()
        print(f"ULGA vocabulary theme layer validation: FAIL - {exc}")
        return 1
    print("ULGA vocabulary theme layer validation: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
