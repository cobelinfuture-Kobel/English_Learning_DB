import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

THEME_CATALOG_PATH = BASE_DIR / "themes" / "theme_catalog.json"
THEME_VOCAB_MAPPING_PATH = BASE_DIR / "themes" / "theme_vocab_mapping.json"
LEARNING_SIGNAL_POLICY_PATH = BASE_DIR / "ulga" / "schema" / "learning_signal_policy.json"

THEME_SPIRAL_GRAPH_OUT_PATH = BASE_DIR / "ulga" / "graph" / "theme_spiral_graph.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "theme_spiral_graph_summary.json"
STAGE_GAP_REVIEW_QUEUE_OUT_PATH = BASE_DIR / "ulga" / "reports" / "theme_spiral_stage_gap_review_queue.json"

CONTRACT_VERSION = "ULGA-S8H"
RELATION = "SPIRAL_TO"
CEFR_ORDER = ["A1", "A1_plus", "A2", "A2_plus", "B1", "B1_plus", "B2", "B2_plus", "C1"]
CEFR_RANK = {level: index for index, level in enumerate(CEFR_ORDER)}


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def normalize_theme_id(parent_theme):
    base = str(parent_theme or "").replace("(Bridge)", "").strip()
    base = re.sub(r"\s+", "_", base.lower())
    base = re.sub(r"[^a-z0-9_]+", "", base)
    return base


def normalize_theme_label(parent_theme):
    return str(parent_theme or "").replace("(Bridge)", "").strip()


def collect_theme_records():
    catalog = read_json(THEME_CATALOG_PATH)
    mapping = read_json(THEME_VOCAB_MAPPING_PATH)

    records_by_id = {}
    for source_name, payload in [
        ("themes/theme_catalog.json", catalog),
        ("themes/theme_vocab_mapping.json", mapping),
    ]:
        for theme in payload.get("themes", []):
            theme_id = theme.get("theme_id")
            if not theme_id:
                continue
            merged = records_by_id.setdefault(theme_id, {})
            merged.update(theme)
            merged.setdefault("source_files", set()).add(source_name)

    records = []
    for record in records_by_id.values():
        source_files = sorted(record.pop("source_files", []))
        parent_theme = record.get("parent_theme")
        level = record.get("level") or record.get("progression_stage")
        theme_id = normalize_theme_id(parent_theme)
        if not theme_id or level not in CEFR_RANK:
            continue
        record["base_theme_id"] = theme_id
        record["base_theme_label"] = normalize_theme_label(parent_theme)
        record["cefr_band"] = level
        record["source_files"] = source_files
        records.append(record)
    return records


def build_theme_stage_nodes(records):
    grouped = defaultdict(list)
    for record in records:
        grouped[(record["base_theme_id"], record["cefr_band"])].append(record)

    nodes = []
    for (theme_id, cefr_band), group in sorted(grouped.items(), key=lambda item: (item[0][0], CEFR_RANK[item[0][1]])):
        stage_id = f"theme:{theme_id}:{cefr_band}"
        source_theme_ids = sorted(record["theme_id"] for record in group)
        parent_labels = sorted({record["base_theme_label"] for record in group})
        active_vocab_count = sum(int(record.get("active_vocabulary_count") or 0) for record in group)
        nodes.append(
            {
                "stage_id": stage_id,
                "node_type": "ThemeStageNode",
                "theme_id": theme_id,
                "theme_label": parent_labels[0] if parent_labels else theme_id,
                "cefr_band": cefr_band,
                "source_theme_ids": source_theme_ids,
                "source_parent_themes": sorted({record.get("parent_theme") for record in group if record.get("parent_theme")}),
                "source_files": sorted({path for record in group for path in record.get("source_files", [])}),
                "source_authority": {
                    "authority_name": "ThemeAuthority",
                    "source_files": [
                        "themes/theme_catalog.json",
                        "themes/theme_vocab_mapping.json",
                    ],
                    "source_theme_ids": source_theme_ids,
                    "derivation": "normalized_parent_theme_plus_cefr_stage",
                    "normalization_policy": "strip_bridge_suffix_and_slugify_parent_theme",
                    "confidence_basis": "derived_from_existing_theme_records",
                },
                "active_vocabulary_count": active_vocab_count,
                "confidence": {
                    "value": 0.75,
                    "method": "derived",
                    "notes": [
                        "Derived from Theme Authority parent_theme and CEFR stage records.",
                        "Bridge parent themes are normalized to their base theme for same-theme spiral sequencing.",
                    ],
                },
                "review_status": "accepted",
                "notes": [
                    "Aggregates one or more source theme records into a single ThemeStageNode.",
                    "This node is not a prerequisite node and must not gate.",
                ],
            }
        )
    return nodes


def make_spiral_edge(theme_id, source_node, target_node, sequence_number):
    source_rank = CEFR_RANK[source_node["cefr_band"]]
    target_rank = CEFR_RANK[target_node["cefr_band"]]
    stage_gap = target_rank - source_rank
    edge_id = f"theme_spiral_edge:{theme_id}:{source_node['cefr_band']}:to:{target_node['cefr_band']}"
    return {
        "edge_id": edge_id,
        "source_stage_id": source_node["stage_id"],
        "target_stage_id": target_node["stage_id"],
        "relation": RELATION,
        "theme_id": theme_id,
        "source_cefr": source_node["cefr_band"],
        "target_cefr": target_node["cefr_band"],
        "confidence": {
            "value": 0.75,
            "method": "derived",
        },
        "review_status": "accepted",
        "gate_eligible": False,
        "evidence": [
            {
                "evidence_type": "source_theme_stage_sequence",
                "source_file": "themes/theme_vocab_mapping.json",
                "theme_id": theme_id,
                "source_theme_ids": source_node["source_theme_ids"],
                "target_theme_ids": target_node["source_theme_ids"],
                "source_cefr": source_node["cefr_band"],
                "target_cefr": target_node["cefr_band"],
                "stage_gap": stage_gap,
                "sequence_number": sequence_number,
            },
            {
                "evidence_type": "learning_signal_policy",
                "source_file": "ulga/schema/learning_signal_policy.json",
                "source_relation": RELATION,
                "gate_allowed": False,
            },
        ],
        "notes": [
            "SPIRAL_TO is a same-theme curriculum sequencing edge.",
            "Generated only between adjacent available stages in the normalized parent_theme sequence.",
            "This edge is not a dependency prerequisite and cannot gate.",
        ],
    }


def build_spiral_edges(stage_nodes):
    nodes_by_theme = defaultdict(list)
    for node in stage_nodes:
        nodes_by_theme[node["theme_id"]].append(node)

    edges = []
    for theme_id, nodes in sorted(nodes_by_theme.items()):
        ordered = sorted(nodes, key=lambda node: CEFR_RANK[node["cefr_band"]])
        for index in range(len(ordered) - 1):
            edges.append(make_spiral_edge(theme_id, ordered[index], ordered[index + 1], index + 1))
    return edges


def build_stage_gap_review_queue(spiral_edges):
    queue = []
    for edge in spiral_edges:
        source_rank = CEFR_RANK[edge["source_cefr"]]
        target_rank = CEFR_RANK[edge["target_cefr"]]
        if target_rank - source_rank <= 1:
            continue
        queue.append(
            {
                "edge_id": edge["edge_id"],
                "theme_id": edge["theme_id"],
                "source_stage_id": edge["source_stage_id"],
                "target_stage_id": edge["target_stage_id"],
                "source_cefr": edge["source_cefr"],
                "target_cefr": edge["target_cefr"],
                "missing_intermediate_cefr": CEFR_ORDER[source_rank + 1 : target_rank],
                "review_reason": "absent_intermediate_cefr_stage",
                "review_status": "needs_review",
                "planner_weight_policy": "cap_or_ignore_until_reviewed",
                "gate_eligible": False,
                "notes": [
                    "Stage-gap edge remains non-gating.",
                    "Planner should cap or ignore this sequencing edge until manual review confirms intended jump.",
                    "No Learning Signal Graph record is generated by S8H.1.",
                ],
            }
        )
    return queue


def build_theme_spiral_graph():
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    policy = read_json(LEARNING_SIGNAL_POLICY_PATH)
    records = collect_theme_records()
    stage_nodes = build_theme_stage_nodes(records)
    spiral_edges = build_spiral_edges(stage_nodes)
    stage_gap_review_queue = build_stage_gap_review_queue(spiral_edges)

    spiral_rule = next(
        (
            rule
            for rule in policy.get("signal_mapping_rules", [])
            if rule.get("source_relation") == RELATION
        ),
        {},
    )

    theme_count = len({node["theme_id"] for node in stage_nodes})
    stage_gap_gt_one_count = sum(
        1
        for edge in spiral_edges
        if CEFR_RANK[edge["target_cefr"]] - CEFR_RANK[edge["source_cefr"]] > 1
    )

    graph = {
        "graph_metadata": {
            "graph_id": "ulga.theme_spiral_graph",
            "contract_version": CONTRACT_VERSION,
            "schema_version": "1.0.0",
            "generated_at": generated_at,
            "source_files": [
                "themes/theme_catalog.json",
                "themes/theme_vocab_mapping.json",
                "ulga/schema/learning_signal_policy.json",
            ],
            "relation_scope": [RELATION],
            "node_scope": ["ThemeStageNode"],
            "builder": "ulga/builders/build_theme_spiral_edges.py",
            "learning_signal_compliance": {
                "policy_file": "ulga/schema/learning_signal_policy.json",
                "source_relation": RELATION,
                "allowed_signal_types": spiral_rule.get("allowed_signal_types", []),
                "default_signal_types": spiral_rule.get("default_signal_types", []),
                "gate_allowed": spiral_rule.get("gate_allowed") is True,
                "gate_signal_generated": False,
                "learning_signal_graph_generated": False,
                "dependency_graph_modified": False,
            },
        },
        "theme_stage_nodes": stage_nodes,
        "spiral_edges": spiral_edges,
        "validation_status": "untested",
    }

    summary = {
        "stage": CONTRACT_VERSION,
        "generated_at": generated_at,
        "theme_count": theme_count,
        "stage_count": len(stage_nodes),
        "spiral_edge_count": len(spiral_edges),
        "relation_breakdown": {RELATION: len(spiral_edges)},
        "gate_eligible_edge_count": sum(1 for edge in spiral_edges if edge["gate_eligible"] is True),
        "review_status_breakdown": {"accepted": len(spiral_edges)},
        "confidence_method_breakdown": {"derived": len(spiral_edges)},
        "stage_gap_gt_one_count": stage_gap_gt_one_count,
        "stage_gap_review_queue_count": len(stage_gap_review_queue),
        "learning_signal_graph_generated": False,
        "dependency_graph_modified": False,
        "theme_to_content_edges_generated": False,
        "excluded_relations": [
            "INTRODUCES",
            "BROADENS_TO",
            "CONTRASTS_WITH",
            "REINFORCES",
        ],
    }
    return graph, summary, stage_gap_review_queue


def main():
    print("Building ULGA Theme Spiral Graph...")
    graph, summary, stage_gap_review_queue = build_theme_spiral_graph()
    write_json(THEME_SPIRAL_GRAPH_OUT_PATH, graph)
    write_json(SUMMARY_OUT_PATH, summary)
    write_json(STAGE_GAP_REVIEW_QUEUE_OUT_PATH, stage_gap_review_queue)
    print(f"Wrote {len(graph['theme_stage_nodes'])} theme stage nodes to {THEME_SPIRAL_GRAPH_OUT_PATH}")
    print(f"Wrote {len(graph['spiral_edges'])} SPIRAL_TO edges to {THEME_SPIRAL_GRAPH_OUT_PATH}")
    print(f"Wrote {len(stage_gap_review_queue)} stage-gap review queue entries to {STAGE_GAP_REVIEW_QUEUE_OUT_PATH}")
    print(f"Wrote summary to {SUMMARY_OUT_PATH}")
    print("ULGA Theme Spiral Graph build complete.")


if __name__ == "__main__":
    main()
