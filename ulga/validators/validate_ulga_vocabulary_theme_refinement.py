import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_ulga_schema import require, validate_edge


GRAPH_DIR = BASE_DIR / "ulga" / "graph"
REPORTS_DIR = BASE_DIR / "ulga" / "reports"

VOCAB_NODES_PATH = GRAPH_DIR / "vocabulary_nodes.json"
THEME_NODES_PATH = GRAPH_DIR / "theme_nodes.json"
ORIGINAL_EDGES_PATH = GRAPH_DIR / "vocabulary_theme_edges.json"
REFINED_EDGES_PATH = GRAPH_DIR / "vocabulary_theme_edges.refined.json"
REFINED_GRAPH_PATH = GRAPH_DIR / "ulga_graph.vocabulary_theme_layer.refined.json"
SUMMARY_PATH = REPORTS_DIR / "vocabulary_theme_refinement_summary.json"
REMOVED_EDGES_PATH = REPORTS_DIR / "vocabulary_theme_refinement_removed_edges.json"

REFINEMENT_STAGE = "ULGA-S5E-REFINEMENT"
FORBIDDEN_EDGE_TYPES = {
    "prerequisite",
    "supports",
    "unlocks",
    "reviews",
    "contrasts_with",
    "uses",
    "contains",
    "spiral_to",
    "assesses",
}


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_ulga_vocabulary_theme_refinement():
    required_paths = [
        VOCAB_NODES_PATH,
        THEME_NODES_PATH,
        ORIGINAL_EDGES_PATH,
        REFINED_EDGES_PATH,
        REFINED_GRAPH_PATH,
        SUMMARY_PATH,
        REMOVED_EDGES_PATH,
    ]
    for path in required_paths:
        require(path.exists(), f"Missing required file: {path}")

    vocabulary_nodes = read_json(VOCAB_NODES_PATH)
    theme_nodes = read_json(THEME_NODES_PATH)
    original_edges = read_json(ORIGINAL_EDGES_PATH)
    refined_edges = read_json(REFINED_EDGES_PATH)
    graph = read_json(REFINED_GRAPH_PATH)
    summary = read_json(SUMMARY_PATH)
    removed_edges = read_json(REMOVED_EDGES_PATH)

    vocabulary_ids = {node["id"] for node in vocabulary_nodes}
    theme_ids = {node["id"] for node in theme_nodes}
    all_node_ids = vocabulary_ids | theme_ids

    require(len(refined_edges) < len(original_edges), "refined edge count must be smaller than original edge count")
    require(len(removed_edges) == len(original_edges) - len(refined_edges), "removed edge count mismatch")

    edge_counts = Counter()
    primary_counts = Counter()
    secondary_counts = Counter()
    inferred_counts = Counter()
    seen_tuples = set()
    mapped_vocabulary_ids = set()

    for edge in refined_edges:
        validate_edge(edge, node_ids=all_node_ids)
        require(edge["edge_type"] == "belongs_to", f"edge_type must be belongs_to: {edge['id']}")
        require(edge["edge_type"] not in FORBIDDEN_EDGE_TYPES, f"forbidden edge type created: {edge['id']}")
        require(edge["source_node_id"] in vocabulary_ids, f"source_node_id is not a vocabulary node: {edge['id']}")
        require(edge["target_node_id"] in theme_ids, f"target_node_id is not a theme node: {edge['id']}")
        require(edge["source_node_id"] != edge["target_node_id"], f"self-loop detected: {edge['id']}")

        edge_tuple = (edge["source_node_id"], edge["target_node_id"], edge["edge_type"])
        require(edge_tuple not in seen_tuples, f"duplicate edge tuple detected: {edge_tuple}")
        seen_tuples.add(edge_tuple)

        metadata = edge["metadata"]
        role = metadata.get("retained_role")
        source_node_id = edge["source_node_id"]
        edge_counts[source_node_id] += 1
        mapped_vocabulary_ids.add(source_node_id)

        require(metadata.get("sense_specific") is True, f"sense_specific must be true: {edge['id']}")
        require(metadata.get("lemma_level_assignment") is False, f"lemma_level_assignment must be false: {edge['id']}")
        require(metadata.get("refined_from_original") is True, f"refined_from_original must be true: {edge['id']}")
        require(metadata.get("refinement_stage") == REFINEMENT_STAGE, f"refinement_stage invalid: {edge['id']}")
        require(metadata.get("mounting_stage") == REFINEMENT_STAGE, f"mounting_stage invalid: {edge['id']}")
        require(metadata.get("original_edge_id"), f"original_edge_id missing: {edge['id']}")
        require(metadata.get("retained_rank") in {1, 2, 3}, f"retained_rank invalid: {edge['id']}")
        require(role in {"primary", "secondary", "inferred_low_confidence"}, f"retained_role invalid: {edge['id']}")
        require("original_membership_type" in metadata, f"original_membership_type missing: {edge['id']}")
        require("original_weight" in metadata, f"original_weight missing: {edge['id']}")
        require("original_confidence" in metadata, f"original_confidence missing: {edge['id']}")

        if role == "primary":
            primary_counts[source_node_id] += 1
        elif role == "secondary":
            secondary_counts[source_node_id] += 1
        elif role == "inferred_low_confidence":
            inferred_counts[source_node_id] += 1

    require(len(mapped_vocabulary_ids) >= 9000, f"mapped vocabulary node count must be >= 9000, got {len(mapped_vocabulary_ids)}")
    require(max(edge_counts.values()) <= 3, "no vocabulary node may have more than 3 refined theme edges")
    require(all(count <= 1 for count in primary_counts.values()), "primary per vocabulary node must be <= 1")
    require(all(count <= 2 for count in secondary_counts.values()), "secondary per vocabulary node must be <= 2")
    require(all(count <= 1 for count in inferred_counts.values()), "inferred_low_confidence per vocabulary node must be <= 1")

    average_edges = len(refined_edges) / len(mapped_vocabulary_ids)
    require(average_edges <= 3, f"average edges per mapped vocabulary must be <= 3, got {average_edges}")

    require(graph.get("formal_data_mounted") is True, "graph formal_data_mounted must be true")
    require(graph.get("mounted_stage") == REFINEMENT_STAGE, "graph mounted_stage mismatch")
    require(graph.get("nodes") == vocabulary_nodes + theme_nodes, "graph nodes must be vocabulary nodes + theme nodes")
    require(graph.get("edges") == refined_edges, "graph edges must match refined edge file")
    require(graph.get("original_theme_edge_count") == len(original_edges), "graph original edge count mismatch")
    require(graph.get("refined_theme_edge_count") == len(refined_edges), "graph refined edge count mismatch")
    require(graph.get("removed_theme_edge_count") == len(removed_edges), "graph removed edge count mismatch")
    require(graph.get("mapped_vocabulary_count") == len(mapped_vocabulary_ids), "graph mapped count mismatch")
    require(graph.get("average_edges_per_mapped_vocabulary") == average_edges, "graph average edge count mismatch")
    require(graph.get("refinement_applied") is True, "graph refinement_applied must be true")
    require(graph.get("original_full_layer_preserved") is True, "graph original_full_layer_preserved must be true")
    require(graph.get("sense_specific_theme_assignment") is True, "graph sense_specific_theme_assignment must be true")
    require(graph.get("lemma_level_theme_assignment") is False, "graph lemma_level_theme_assignment must be false")

    require(summary.get("original_theme_edge_count") == len(original_edges), "summary original edge count mismatch")
    require(summary.get("refined_theme_edge_count") == len(refined_edges), "summary refined edge count mismatch")
    require(summary.get("removed_theme_edge_count") == len(removed_edges), "summary removed edge count mismatch")
    require(summary.get("mapped_vocabulary_count") == len(mapped_vocabulary_ids), "summary mapped count mismatch")
    require(summary.get("average_edges_per_mapped_vocabulary") == average_edges, "summary average edge count mismatch")
    require(summary.get("overconnected_node_count_after") == 0, "summary overconnected count after must be 0")

    print(
        "Validation: SUCCESS. "
        f"Verified {len(refined_edges)} refined belongs_to edges, "
        f"{len(mapped_vocabulary_ids)} mapped vocabulary nodes, average {average_edges:.4f} edges/node."
    )


def main():
    try:
        validate_ulga_vocabulary_theme_refinement()
    except Exception as exc:
        import traceback

        traceback.print_exc()
        print(f"ULGA vocabulary theme refinement validation: FAIL - {exc}")
        return 1
    print("ULGA vocabulary theme refinement validation: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
