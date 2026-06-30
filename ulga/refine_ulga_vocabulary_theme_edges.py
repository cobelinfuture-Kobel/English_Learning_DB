import datetime
import json
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
GRAPH_DIR = BASE_DIR / "ulga" / "graph"
REPORTS_DIR = BASE_DIR / "ulga" / "reports"

VOCAB_NODES_PATH = GRAPH_DIR / "vocabulary_nodes.json"
THEME_NODES_PATH = GRAPH_DIR / "theme_nodes.json"
ORIGINAL_EDGES_PATH = GRAPH_DIR / "vocabulary_theme_edges.json"

REFINED_EDGES_OUT_PATH = GRAPH_DIR / "vocabulary_theme_edges.refined.json"
REFINED_GRAPH_OUT_PATH = GRAPH_DIR / "ulga_graph.vocabulary_theme_layer.refined.json"
SUMMARY_OUT_PATH = REPORTS_DIR / "vocabulary_theme_refinement_summary.json"
REMOVED_EDGES_OUT_PATH = REPORTS_DIR / "vocabulary_theme_refinement_removed_edges.json"

REFINEMENT_STAGE = "ULGA-S5E-REFINEMENT"

SOURCE_PRIORITY = {
    "native_topic": 0,
    "themes/theme_vocab_mapping.json": 1,
    "theme_vocab_mapping": 1,
    "themes/theme_mapping.json": 2,
    "theme_mapping": 2,
    "inferred_rule": 3,
    "fallback_topic_normalization_rules": 4,
    "fallback": 4,
}


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def source_priority(edge):
    metadata = edge.get("metadata", {})
    mapping_source = metadata.get("mapping_source") or edge.get("authority_source", {}).get("source_file")
    return SOURCE_PRIORITY.get(mapping_source, 99)


def theme_specificity(edge, theme_by_id):
    theme = theme_by_id.get(edge["target_node_id"], {})
    active_count = theme.get("metadata", {}).get("active_vocabulary_count")
    if isinstance(active_count, int):
        return -active_count
    return 0


def ranking_key(edge, theme_by_id):
    metadata = edge.get("metadata", {})
    confidence = edge.get("confidence", {}).get("value", 0)
    weight = metadata.get("weight", 0)
    theme_id = metadata.get("target_theme_id") or edge["target_node_id"].removeprefix("theme:")
    return (
        -confidence,
        -weight,
        source_priority(edge),
        -theme_specificity(edge, theme_by_id),
        theme_id,
        edge["id"],
    )


def role_reason(role, rank, edge):
    membership_type = edge.get("metadata", {}).get("membership_type")
    if role == "primary":
        return f"Retained as primary rank {rank}: strongest primary membership after confidence, weight, source, specificity, and theme_id tie-breaks."
    if role == "secondary":
        return f"Retained as secondary rank {rank}: next strongest non-primary membership while keeping node total at or below 3."
    return f"Retained as inferred_low_confidence rank {rank}: no high-confidence primary/secondary edge was available; original membership_type={membership_type}."


def refined_edge(original_edge, role, rank, timestamp, theme_by_id):
    edge = json.loads(json.dumps(original_edge))
    edge["id"] = original_edge["id"].replace("edge:vocab_theme_", "edge:vocab_theme_refined_", 1)
    if edge["id"] == original_edge["id"]:
        edge["id"] = f"{original_edge['id']}:refined"
    edge["version"] = {
        **edge.get("version", {}),
        "contract": "ULGA-S2",
        "source_version": "1.0.0",
        "generated_at": timestamp,
    }
    metadata = edge.setdefault("metadata", {})
    original_membership_type = metadata.get("membership_type")
    original_weight = metadata.get("weight")
    original_confidence = edge.get("confidence", {}).get("value")
    metadata.update(
        {
            "membership_type": role,
            "sense_specific": True,
            "lemma_level_assignment": False,
            "mounting_stage": REFINEMENT_STAGE,
            "refined_from_original": True,
            "original_edge_id": original_edge["id"],
            "refinement_stage": REFINEMENT_STAGE,
            "refinement_reason": role_reason(role, rank, original_edge),
            "retained_rank": rank,
            "retained_role": role,
            "original_membership_type": original_membership_type,
            "original_weight": original_weight,
            "original_confidence": original_confidence,
            "morphology_layer_implemented": False,
            "chunk_layer_implemented": False,
            "vocabulary_dependency_layer_implemented": False,
        }
    )
    return edge


def select_refined_edges(edges_by_vocab, theme_by_id, timestamp):
    refined = []
    removed = []
    retained_original_ids = set()

    for vocab_id in sorted(edges_by_vocab):
        node_edges = edges_by_vocab[vocab_id]
        primary_candidates = [
            edge for edge in node_edges if edge.get("metadata", {}).get("membership_type") == "primary"
        ]
        secondary_candidates = [
            edge for edge in node_edges if edge.get("metadata", {}).get("membership_type") == "secondary"
        ]
        inferred_candidates = [
            edge for edge in node_edges if edge.get("metadata", {}).get("membership_type") == "inferred"
        ]

        selected = []
        if primary_candidates:
            selected.append(("primary", sorted(primary_candidates, key=lambda edge: ranking_key(edge, theme_by_id))[0]))

        selected_target_ids = {edge["target_node_id"] for _, edge in selected}
        for edge in sorted(secondary_candidates, key=lambda edge: ranking_key(edge, theme_by_id)):
            if edge["target_node_id"] in selected_target_ids:
                continue
            selected.append(("secondary", edge))
            selected_target_ids.add(edge["target_node_id"])
            if sum(1 for role, _ in selected if role == "secondary") >= 2:
                break

        has_high_confidence_primary_or_secondary = any(
            edge.get("confidence", {}).get("value", 0) >= 0.6
            for role, edge in selected
            if role in {"primary", "secondary"}
        )
        if not has_high_confidence_primary_or_secondary and inferred_candidates:
            for edge in sorted(inferred_candidates, key=lambda edge: ranking_key(edge, theme_by_id)):
                if edge["target_node_id"] in selected_target_ids:
                    continue
                selected.append(("inferred_low_confidence", edge))
                selected_target_ids.add(edge["target_node_id"])
                break

        for rank, (role, edge) in enumerate(selected[:3], start=1):
            retained_original_ids.add(edge["id"])
            refined.append(refined_edge(edge, role, rank, timestamp, theme_by_id))

        for edge in node_edges:
            if edge["id"] not in retained_original_ids:
                removed.append(
                    {
                        "original_edge_id": edge["id"],
                        "source_node_id": edge["source_node_id"],
                        "target_node_id": edge["target_node_id"],
                        "edge_type": edge["edge_type"],
                        "original_membership_type": edge.get("metadata", {}).get("membership_type"),
                        "original_weight": edge.get("metadata", {}).get("weight"),
                        "original_confidence": edge.get("confidence", {}).get("value"),
                        "removal_stage": REFINEMENT_STAGE,
                        "removal_reason": "Pruned by per-vocabulary cap: max 1 primary, max 2 secondary, max 1 inferred only when no high-confidence primary/secondary exists.",
                    }
                )

    return refined, removed


def summarize(original_edges, refined_edges, removed_edges, vocab_nodes, theme_nodes, timestamp):
    original_by_vocab = Counter(edge["source_node_id"] for edge in original_edges)
    refined_by_vocab = Counter(edge["source_node_id"] for edge in refined_edges)
    role_breakdown = Counter(edge["metadata"].get("retained_role") for edge in refined_edges)
    original_mapped_count = len(original_by_vocab)
    refined_mapped_count = len(refined_by_vocab)
    return {
        "generated_at": timestamp,
        "refinement_stage": REFINEMENT_STAGE,
        "vocabulary_node_count": len(vocab_nodes),
        "theme_node_count": len(theme_nodes),
        "original_theme_edge_count": len(original_edges),
        "refined_theme_edge_count": len(refined_edges),
        "removed_theme_edge_count": len(removed_edges),
        "original_mapped_vocabulary_count": original_mapped_count,
        "mapped_vocabulary_count": refined_mapped_count,
        "average_edges_per_mapped_vocabulary_before": len(original_edges) / original_mapped_count,
        "average_edges_per_mapped_vocabulary": len(refined_edges) / refined_mapped_count,
        "overconnected_node_count_before": sum(1 for count in original_by_vocab.values() if count > 3),
        "overconnected_node_count_after": sum(1 for count in refined_by_vocab.values() if count > 3),
        "max_edges_per_mapped_vocabulary_before": max(original_by_vocab.values()),
        "max_edges_per_mapped_vocabulary_after": max(refined_by_vocab.values()),
        "retained_role_breakdown": dict(role_breakdown),
        "refinement_applied": True,
        "original_full_layer_preserved": ORIGINAL_EDGES_PATH.exists(),
        "sense_specific_theme_assignment": True,
        "lemma_level_theme_assignment": False,
        "morphology_layer_implemented": False,
        "chunk_layer_implemented": False,
        "vocabulary_dependency_layer_implemented": False,
        "learner_state_implemented": False,
        "planner_implemented": False,
        "recommendation_implemented": False,
    }


def main():
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    vocab_nodes = read_json(VOCAB_NODES_PATH)
    theme_nodes = read_json(THEME_NODES_PATH)
    original_edges = read_json(ORIGINAL_EDGES_PATH)

    edges_by_vocab = defaultdict(list)
    for edge in original_edges:
        edges_by_vocab[edge["source_node_id"]].append(edge)

    theme_by_id = {node["id"]: node for node in theme_nodes}
    refined_edges, removed_edges = select_refined_edges(edges_by_vocab, theme_by_id, timestamp)
    summary = summarize(original_edges, refined_edges, removed_edges, vocab_nodes, theme_nodes, timestamp)

    graph = {
        "graph_id": "ulga_graph.vocabulary_theme_layer.refined",
        "contract_version": "ULGA-S2",
        "schema_version": "1.0.0",
        "formal_data_mounted": True,
        "mounted_stage": REFINEMENT_STAGE,
        "nodes": vocab_nodes + theme_nodes,
        "edges": refined_edges,
        "vocabulary_node_count": len(vocab_nodes),
        "theme_node_count": len(theme_nodes),
        "original_theme_edge_count": len(original_edges),
        "refined_theme_edge_count": len(refined_edges),
        "removed_theme_edge_count": len(removed_edges),
        "theme_edge_count": len(refined_edges),
        "mapped_vocabulary_count": summary["mapped_vocabulary_count"],
        "average_edges_per_mapped_vocabulary": summary["average_edges_per_mapped_vocabulary"],
        "refinement_applied": True,
        "original_full_layer_preserved": ORIGINAL_EDGES_PATH.exists(),
        "sense_specific_theme_assignment": True,
        "lemma_level_theme_assignment": False,
        "morphology_layer_implemented": False,
        "chunk_layer_implemented": False,
        "vocabulary_dependency_layer_implemented": False,
        "learner_state_implemented": False,
        "planner_implemented": False,
        "recommendation_implemented": False,
        "validation_status": "untested",
        "metadata": {
            "purpose": "Refined Vocabulary Theme Layer",
            "data_policy": "derived_refinement_only_original_full_layer_preserved",
            "generated_at": timestamp,
            "refinement_stage": REFINEMENT_STAGE,
        },
    }

    write_json(REFINED_EDGES_OUT_PATH, refined_edges)
    write_json(REFINED_GRAPH_OUT_PATH, graph)
    write_json(SUMMARY_OUT_PATH, summary)
    write_json(REMOVED_EDGES_OUT_PATH, removed_edges)

    print(f"Original vocabulary-theme edges: {len(original_edges)}")
    print(f"Refined vocabulary-theme edges: {len(refined_edges)}")
    print(f"Removed vocabulary-theme edges: {len(removed_edges)}")
    print(f"Mapped vocabulary nodes: {summary['mapped_vocabulary_count']}")
    print(f"Average edges per mapped vocabulary: {summary['average_edges_per_mapped_vocabulary']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
