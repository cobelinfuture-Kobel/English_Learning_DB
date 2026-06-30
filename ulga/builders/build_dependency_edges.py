import json
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

GRAMMAR_NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
GRAMMAR_DEPENDENCY_EDGES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_dependency_all_edges.json"
LEARNING_SIGNAL_POLICY_PATH = BASE_DIR / "ulga" / "schema" / "learning_signal_policy.json"

DEPENDENCY_GRAPH_OUT_PATH = BASE_DIR / "ulga" / "graph" / "dependency_graph.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "dependency_graph_summary.json"

CONTRACT_VERSION = "ULGA-S8C"
RELATION = "REQUIRES"
DEPENDENCY_CLASS = "hard_prerequisite"


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def normalize_confidence(original_confidence):
    value = float(original_confidence.get("value", 0.0))
    return {
        "value": value,
        "method": "derived",
        "notes": [
            "Derived from accepted grammar hard prerequisite edge.",
            "Original confidence method: "
            + str(original_confidence.get("method", "unknown")),
        ],
    }


def make_dependency_edge(source_edge):
    metadata = source_edge.get("metadata", {})
    original_confidence = source_edge.get("confidence", {})
    rule_id = metadata.get("rule_id") or source_edge.get("authority_source", {}).get("source_record_id")

    evidence = [
        {
            "evidence_type": "source_edge",
            "source_edge_id": source_edge.get("id"),
            "source_edge_type": source_edge.get("edge_type"),
            "source_file": "ulga/graph/grammar_dependency_all_edges.json",
        },
        {
            "evidence_type": "grammar_dependency_rule",
            "rule_id": rule_id,
            "rule_name": metadata.get("rule_name"),
            "original_dependency_class": metadata.get("dependency_class"),
            "cefr_is_not_order": metadata.get("cefr_is_not_order") is True,
            "rationale": metadata.get("rationale"),
        },
        {
            "evidence_type": "source_match_evidence",
            "value": metadata.get("source_match_evidence", {}),
        },
        {
            "evidence_type": "target_match_evidence",
            "value": metadata.get("target_match_evidence", {}),
        },
    ]

    source_id = source_edge["source_node_id"]
    target_id = source_edge["target_node_id"]
    suffix = source_edge["id"].replace("edge:", "").replace(":", "_")

    return {
        "edge_id": f"dependency_edge:{suffix}",
        "source_node_id": source_id,
        "target_node_id": target_id,
        "relation": RELATION,
        "dependency_class": DEPENDENCY_CLASS,
        "confidence": normalize_confidence(original_confidence),
        "source_authority": "Grammar Authority",
        "review_status": "accepted",
        "gate_eligible": True,
        "source_edge_id": source_edge.get("id"),
        "learning_signal_policy": {
            "policy_file": "ulga/schema/learning_signal_policy.json",
            "signal_type": "GATE_SIGNAL",
            "source_relation": RELATION,
            "gate_allowed": True,
        },
        "evidence": evidence,
        "notes": [
            "Generated only from accepted grammar hard_prerequisite edge.",
            "No Theme, Vocabulary, Chunk, Pattern, SPIRAL_TO, BELONGS_TO, USES, supports, or reviews relation was promoted to a dependency gate.",
        ],
    }


def build_dependency_graph():
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    grammar_nodes = read_json(GRAMMAR_NODES_PATH)
    grammar_edges = read_json(GRAMMAR_DEPENDENCY_EDGES_PATH)
    learning_signal_policy = read_json(LEARNING_SIGNAL_POLICY_PATH)

    grammar_node_ids = {node["id"] for node in grammar_nodes}
    gate_allowed_relations = set(
        learning_signal_policy.get("validation_policy", {})
        .get("invalid_gate_mapping", {})
        .get("gate_allowed_only_for", [])
    )

    dependency_edges = []
    skipped_edges = []

    for edge in grammar_edges:
        metadata = edge.get("metadata", {})
        is_hard_prerequisite = (
            edge.get("edge_type") == "prerequisite"
            and metadata.get("dependency_class") == DEPENDENCY_CLASS
            and edge.get("source_node_id") in grammar_node_ids
            and edge.get("target_node_id") in grammar_node_ids
        )
        if is_hard_prerequisite:
            dependency_edges.append(make_dependency_edge(edge))
        else:
            skipped_edges.append(
                {
                    "source_edge_id": edge.get("id"),
                    "edge_type": edge.get("edge_type"),
                    "dependency_class": metadata.get("dependency_class"),
                    "reason": "not_accepted_hard_grammar_prerequisite",
                }
            )

    graph = {
        "graph_metadata": {
            "graph_id": "ulga.dependency_graph",
            "contract_version": CONTRACT_VERSION,
            "schema_version": "1.0.0",
            "generated_at": generated_at,
            "source_files": [
                "ulga/graph/grammar_nodes.json",
                "ulga/graph/grammar_dependency_all_edges.json",
                "ulga/schema/learning_signal_policy.json",
            ],
            "relation_scope": [RELATION],
            "dependency_class_scope": [DEPENDENCY_CLASS],
            "builder": "ulga/builders/build_dependency_edges.py",
            "learning_signal_compliance": {
                "policy_file": "ulga/schema/learning_signal_policy.json",
                "gate_signal_only": True,
                "gate_allowed_relations": sorted(gate_allowed_relations),
                "theme_spiral_edges_generated": False,
                "learning_signal_graph_generated": False,
                "cefr_only_dependency_generated": False,
            },
        },
        "edges": dependency_edges,
        "validation_status": "untested",
    }

    summary = {
        "stage": CONTRACT_VERSION,
        "generated_at": generated_at,
        "source_edge_count": len(grammar_edges),
        "dependency_edge_count": len(dependency_edges),
        "skipped_source_edge_count": len(skipped_edges),
        "relation_breakdown": {RELATION: len(dependency_edges)},
        "dependency_class_breakdown": {DEPENDENCY_CLASS: len(dependency_edges)},
        "gate_eligible_edge_count": sum(1 for edge in dependency_edges if edge["gate_eligible"]),
        "review_status_breakdown": {"accepted": len(dependency_edges)},
        "confidence_method_breakdown": {
            "derived": len(dependency_edges),
        },
        "authoritative_edge_count": 0,
        "derived_edge_count": len(dependency_edges),
        "review_required_edge_count": 0,
        "theme_dependency_edge_count": 0,
        "cross_authority_edge_count": 0,
        "theme_spiral_edges_generated": False,
        "learning_signal_graph_generated": False,
        "skipped_edge_samples": skipped_edges[:20],
    }

    return graph, summary


def main():
    print("Building ULGA Dependency Graph...")
    graph, summary = build_dependency_graph()
    write_json(DEPENDENCY_GRAPH_OUT_PATH, graph)
    write_json(SUMMARY_OUT_PATH, summary)
    print(f"Wrote {len(graph['edges'])} dependency edges to {DEPENDENCY_GRAPH_OUT_PATH}")
    print(f"Wrote summary to {SUMMARY_OUT_PATH}")
    print("ULGA Dependency Graph build complete.")


if __name__ == "__main__":
    main()
