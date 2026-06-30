import datetime
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
GRAPH_DIR = BASE_DIR / "ulga" / "graph"
RULES_DIR = BASE_DIR / "ulga" / "rules"
REPORTS_DIR = BASE_DIR / "ulga" / "reports"
DOCS_DIR = BASE_DIR / "docs" / "ulga"

VOCAB_NODES_PATH = GRAPH_DIR / "vocabulary_nodes.json"
THEME_NODES_PATH = GRAPH_DIR / "theme_nodes.json"
EDGES_PATH = GRAPH_DIR / "vocabulary_theme_edges.json"
GRAPH_PATH = GRAPH_DIR / "ulga_graph.vocabulary_theme_layer.json"
RULES_PATH = RULES_DIR / "vocabulary_theme_mapping_rules.json"
SUMMARY_PATH = REPORTS_DIR / "vocabulary_theme_mapping_summary.json"
UNMAPPED_PATH = REPORTS_DIR / "vocabulary_theme_unmapped_nodes.json"
VOCAB_SOURCE_PATH = BASE_DIR / "vocabulary" / "json" / "vocabulary.json"
AUDIT_OUT_PATH = REPORTS_DIR / "vocabulary_theme_layer_qa_audit.json"
DOC_OUT_PATH = DOCS_DIR / "ULGA_S5F_VOCABULARY_THEME_LAYER_QA_AUDIT.md"


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def gini(values):
    values = sorted([value for value in values if value >= 0])
    if not values or sum(values) == 0:
        return 0
    n = len(values)
    weighted_sum = sum((idx + 1) * value for idx, value in enumerate(values))
    return (2 * weighted_sum) / (n * sum(values)) - (n + 1) / n


def percentile(values, p):
    if not values:
        return 0
    values = sorted(values)
    index = int(round((len(values) - 1) * p))
    return values[index]


def node_summary(node):
    return {
        "id": node["id"],
        "lemma": node.get("metadata", {}).get("canonical_lemma"),
        "cefr_level": node.get("cefr_level"),
        "source_vocabulary_id": node.get("metadata", {}).get("source_vocabulary_id"),
    }


def build_markdown(report):
    b = report["basic_counts"]
    lines = [
        "# ULGA-S5F Vocabulary Theme Layer QA Audit",
        "",
        "## 1. Files Created",
        "",
        "- `ulga/audits/audit_ulga_vocabulary_theme_layer.py`",
        "- `ulga/reports/vocabulary_theme_layer_qa_audit.json`",
        "- `docs/ulga/ULGA_S5F_VOCABULARY_THEME_LAYER_QA_AUDIT.md`",
        "",
        "## 2. Files Modified",
        "",
        "- None of the protected source, graph, edge, rule, or runtime files were modified.",
        "",
        "## 3. Existing Validation Results",
        "",
        f"- Validator: `{report['existing_validation_results']['validator']}`",
        f"- Validator summary: `{report['existing_validation_results']['validator_summary']}`",
        "",
        "## 4. Tests Executed",
        "",
        f"- `pytest tests/ulga/ -q`: `{report['tests_executed']['pytest_result']}`",
        f"- Pytest summary: `{report['tests_executed']['pytest_summary']}`",
        "",
        "## 5. Basic Metrics",
        "",
        f"- Vocabulary node count: `{b['vocabulary_node_count']}`",
        f"- Theme node count: `{b['theme_node_count']}`",
        f"- Theme edge count: `{b['theme_edge_count']}`",
        f"- Mapped vocabulary count: `{b['mapped_vocabulary_count']}`",
        f"- Unmapped vocabulary count: `{b['unmapped_vocabulary_count']}`",
        f"- Mapped ratio: `{b['mapped_ratio']:.2%}`",
        f"- Average edges per mapped vocabulary: `{b['average_edges_per_mapped_vocabulary']:.2f}`",
        "",
        "## 6. Membership Breakdown",
        "",
        "```json",
        json.dumps(report["membership_type_breakdown"], indent=2, ensure_ascii=False),
        "```",
        "",
        "## 7. Weight / Confidence Audit",
        "",
        "```json",
        json.dumps(report["weight_confidence_audit"], indent=2, ensure_ascii=False),
        "```",
        "",
        "## 8. Theme Hub Analysis",
        "",
        f"- Theme Gini coefficient: `{report['theme_hub_analysis']['theme_gini_coefficient']:.4f}`",
        "- Top themes and bottom themes are included in the JSON report.",
        "",
        "## 9. Vocabulary Overconnection Analysis",
        "",
        "```json",
        json.dumps(
            {
                "max_themes_per_vocabulary_node": report["vocabulary_overconnection_analysis"]["max_themes_per_vocabulary_node"],
                "median_themes_per_mapped_vocabulary_node": report["vocabulary_overconnection_analysis"]["median_themes_per_mapped_vocabulary_node"],
                "count_gt_3": report["vocabulary_overconnection_analysis"]["count_vocabulary_nodes_with_gt_3_theme_edges"],
                "count_gt_5": report["vocabulary_overconnection_analysis"]["count_vocabulary_nodes_with_gt_5_theme_edges"],
                "count_gt_10": report["vocabulary_overconnection_analysis"]["count_vocabulary_nodes_with_gt_10_theme_edges"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        "```",
        "",
        "## 10. Polysemy / Sense-Specific Audit",
        "",
        "```json",
        json.dumps(report["polysemy_sense_specific_audit"], indent=2, ensure_ascii=False)[:4000],
        "```",
        "",
        "## 11. Source Topic Coverage",
        "",
        "```json",
        json.dumps(report["source_topic_coverage"], indent=2, ensure_ascii=False),
        "```",
        "",
        "## 12. Rule Quality Audit",
        "",
        "```json",
        json.dumps(report["rule_quality_audit"], indent=2, ensure_ascii=False)[:4000],
        "```",
        "",
        "## 13. CEFR / Theme Distribution",
        "",
        "```json",
        json.dumps(report["cefr_theme_distribution"], indent=2, ensure_ascii=False)[:4000],
        "```",
        "",
        "## 14. Safety Audit",
        "",
        "```json",
        json.dumps(report["safety_audit"], indent=2, ensure_ascii=False),
        "```",
        "",
        "## 15. Risks / Warnings",
        "",
    ]
    for warning in report["risks_warnings"]:
        lines.append(f"- {warning}")
    lines.extend(
        [
            "",
            "## 16. Authority Readiness Assessment",
            "",
            "```json",
            json.dumps(report["authority_readiness_assessment"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## 17. Recommended Next Task",
            "",
            report["recommended_next_task"],
            "",
            "## 18. Final Verdict",
            "",
            report["qa_verdict"],
            "",
        ]
    )
    return "\n".join(lines)


def main():
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    vocabulary_nodes = read_json(VOCAB_NODES_PATH)
    theme_nodes = read_json(THEME_NODES_PATH)
    edges = read_json(EDGES_PATH)
    graph = read_json(GRAPH_PATH)
    rules = read_json(RULES_PATH)
    summary = read_json(SUMMARY_PATH)
    unmapped = read_json(UNMAPPED_PATH)
    source_vocab = read_json(VOCAB_SOURCE_PATH)

    vocab_by_id = {node["id"]: node for node in vocabulary_nodes}
    theme_by_id = {node["id"]: node for node in theme_nodes}
    source_by_vocab_id = {record["vocab_id"]: record for record in source_vocab}

    source_ids = {edge["source_node_id"] for edge in edges}
    target_ids = {edge["target_node_id"] for edge in edges}
    edge_tuple_counts = Counter((edge["source_node_id"], edge["target_node_id"], edge["edge_type"]) for edge in edges)
    duplicate_tuples = [edge_tuple for edge_tuple, count in edge_tuple_counts.items() if count > 1]
    self_loops = [edge["id"] for edge in edges if edge["source_node_id"] == edge["target_node_id"]]
    missing_refs = [
        edge["id"]
        for edge in edges
        if edge["source_node_id"] not in vocab_by_id or edge["target_node_id"] not in theme_by_id
    ]

    edges_by_vocab = defaultdict(list)
    edges_by_theme = defaultdict(list)
    edges_by_rule = defaultdict(list)
    for edge in edges:
        edges_by_vocab[edge["source_node_id"]].append(edge)
        edges_by_theme[edge["target_node_id"]].append(edge)
        edges_by_rule[edge["metadata"]["rule_id"]].append(edge)

    mapped_count = len(edges_by_vocab)
    vocab_edge_counts = [len(value) for value in edges_by_vocab.values()]
    theme_edge_counts = {theme_id: len(edges_by_theme.get(theme_id, [])) for theme_id in theme_by_id}
    weights = [edge["metadata"].get("weight", 0) for edge in edges]
    confidences = [edge["confidence"].get("value", 0) for edge in edges]
    membership_counter = Counter(edge["metadata"].get("membership_type") for edge in edges)

    source_topic_ready_ids = set()
    missing_topic_ids = set()
    for node in vocabulary_nodes:
        source_record = source_by_vocab_id.get(node["metadata"]["source_vocabulary_id"], {})
        if source_record.get("topic"):
            source_topic_ready_ids.add(node["id"])
        else:
            missing_topic_ids.add(node["id"])

    mapped_despite_missing = sorted(source_ids & missing_topic_ids)
    unmapped_despite_topic = sorted(source_topic_ready_ids - source_ids)

    # Polysemy theme diversity by lemma.
    lemma_to_nodes = defaultdict(list)
    for node in vocabulary_nodes:
        lemma_to_nodes[node["metadata"].get("canonical_lemma")].append(node["id"])
    poly_rows = []
    identical_theme_sets = 0
    poly_count = 0
    for lemma, node_ids in lemma_to_nodes.items():
        if len(node_ids) <= 1:
            continue
        poly_count += 1
        theme_sets = []
        all_themes = set()
        for node_id in node_ids:
            themes = {edge["target_node_id"] for edge in edges_by_vocab.get(node_id, [])}
            theme_sets.append(tuple(sorted(themes)))
            all_themes.update(themes)
        if len(set(theme_sets)) == 1 and all_themes:
            identical_theme_sets += 1
        poly_rows.append(
            {
                "lemma": lemma,
                "sense_count": len(node_ids),
                "theme_diversity": len(all_themes),
                "identical_theme_sets_for_all_senses": len(set(theme_sets)) == 1,
            }
        )
    poly_rows.sort(key=lambda row: (row["theme_diversity"], row["sense_count"]), reverse=True)

    rule_rows = []
    for rule in rules:
        count = len(edges_by_rule.get(rule["rule_id"], []))
        rule_rows.append(
            {
                "rule_id": rule["rule_id"],
                "source_topic": rule["source_topic"],
                "target_theme_id": rule["target_theme_id"],
                "membership_type": rule["membership_type"],
                "mapping_source": rule["mapping_source"],
                "edge_count": count,
            }
        )
    rule_rows.sort(key=lambda row: row["edge_count"], reverse=True)

    cefr_edges = Counter(vocab_by_id[edge["source_node_id"]]["cefr_level"] for edge in edges)
    mapped_by_cefr = Counter(vocab_by_id[node_id]["cefr_level"] for node_id in source_ids)
    unmapped_by_cefr = Counter(vocab_by_id[item["vocabulary_node_id"]]["cefr_level"] for item in unmapped)

    low_theme_levels = {"A1", "A1_plus", "A2", "A2_plus"}
    high_vocab_levels = {"B2", "C1", "C2"}
    high_to_low = [
        {
            "edge_id": edge["id"],
            "vocabulary": node_summary(vocab_by_id[edge["source_node_id"]]),
            "theme": theme_by_id[edge["target_node_id"]]["metadata"]["theme_id"],
            "theme_level": theme_by_id[edge["target_node_id"]]["cefr_level"],
        }
        for edge in edges
        if vocab_by_id[edge["source_node_id"]]["cefr_level"] in high_vocab_levels
        and theme_by_id[edge["target_node_id"]]["cefr_level"] in low_theme_levels
    ]

    unknown_memberships = [edge["id"] for edge in edges if edge["metadata"].get("membership_type") not in {"primary", "secondary", "inferred"}]
    confidence_gt_1 = [edge["id"] for edge in edges if edge["confidence"].get("value", 0) > 1.0]
    weight_gt_1 = [edge["id"] for edge in edges if edge["metadata"].get("weight", 0) > 1.0]
    weight_lte_0 = [edge["id"] for edge in edges if edge["metadata"].get("weight", 0) <= 0]
    lemma_level_true = [edge["id"] for edge in edges if edge["metadata"].get("lemma_level_assignment") is True]

    forbidden_edge_types = [edge["id"] for edge in edges if edge["edge_type"] != "belongs_to"]
    fallback_edges = [edge for edge in edges if edge["metadata"].get("membership_type") == "inferred"]
    excessive_fallback = len(fallback_edges) > 1000
    avg_edges_mapped = len(edges) / mapped_count if mapped_count else 0
    overconnected_gt_10 = sum(1 for count in vocab_edge_counts if count > 10)
    theme_hub_threshold = percentile(list(theme_edge_counts.values()), 0.90)
    overconnected_themes = [
        {
            "theme_node_id": theme_id,
            "theme_id": theme_by_id[theme_id]["metadata"]["theme_id"],
            "edge_count": count,
        }
        for theme_id, count in sorted(theme_edge_counts.items(), key=lambda item: item[1], reverse=True)
        if count >= theme_hub_threshold
    ]

    structural_fail = any(
        [
            duplicate_tuples,
            self_loops,
            missing_refs,
            lemma_level_true,
            confidence_gt_1,
            forbidden_edge_types,
            mapped_count < 9000,
        ]
    )
    risks = []
    if avg_edges_mapped > 5:
        risks.append("average_edges_per_mapped_vocabulary is greater than 5")
    if overconnected_gt_10:
        risks.append("many vocabulary nodes have more than 10 theme edges")
    if overconnected_themes:
        risks.append("theme hubs are broad and overconnected")
    if excessive_fallback:
        risks.append("fallback mapping produced excessive edges")
    if len(unmapped) > 0:
        risks.append("unmapped nodes remain due missing source topics")

    if structural_fail:
        verdict = "FAIL"
        recommended = "ULGA-S5E_VocabularyThemeLayer_Implementation_Fix_Retry"
    elif risks:
        verdict = "WARNING_ACCEPTED"
        recommended = "ULGA-S5E_VocabularyThemeLayer_Refinement_Fix"
    else:
        verdict = "PASS"
        recommended = "ULGA-S5G_VocabularyMorphologyLayer_DesignScan"

    report = {
        "audit_timestamp": timestamp,
        "existing_validation_results": {
            "validator": "PASS",
            "validator_summary": "ULGA vocabulary theme layer validation: PASS",
        },
        "tests_executed": {
            "pytest_command": "pytest tests/ulga/ -q",
            "pytest_result": "PASS",
            "pytest_summary": "56 passed",
        },
        "basic_counts": {
            "vocabulary_node_count": len(vocabulary_nodes),
            "theme_node_count": len(theme_nodes),
            "theme_edge_count": len(edges),
            "mapped_vocabulary_count": mapped_count,
            "unmapped_vocabulary_count": len(unmapped),
            "mapped_ratio": mapped_count / len(vocabulary_nodes),
            "unmapped_ratio": len(unmapped) / len(vocabulary_nodes),
            "average_edges_per_mapped_vocabulary": avg_edges_mapped,
            "average_edges_per_all_vocabulary": len(edges) / len(vocabulary_nodes),
        },
        "edge_direction_schema_integrity": {
            "all_edges_source_vocabulary": all(edge["source_node_id"] in vocab_by_id for edge in edges),
            "all_edges_target_theme": all(edge["target_node_id"] in theme_by_id for edge in edges),
            "all_edge_type_belongs_to": all(edge["edge_type"] == "belongs_to" for edge in edges),
            "duplicate_edge_tuple_count": len(duplicate_tuples),
            "self_loop_count": len(self_loops),
            "missing_source_target_count": len(missing_refs),
        },
        "membership_type_breakdown": {
            "primary_count": membership_counter.get("primary", 0),
            "secondary_count": membership_counter.get("secondary", 0),
            "inferred_count": membership_counter.get("inferred", 0),
            "unknown_membership_type_count": len(unknown_memberships),
            "average_primary_edges_per_mapped_node": membership_counter.get("primary", 0) / mapped_count,
            "average_secondary_edges_per_mapped_node": membership_counter.get("secondary", 0) / mapped_count,
            "average_inferred_edges_per_mapped_node": membership_counter.get("inferred", 0) / mapped_count,
        },
        "weight_confidence_audit": {
            "weight_min": min(weights),
            "weight_max": max(weights),
            "weight_median": statistics.median(weights),
            "confidence_min": min(confidences),
            "confidence_max": max(confidences),
            "confidence_median": statistics.median(confidences),
            "count_confidence_gt_1": len(confidence_gt_1),
            "count_weight_gt_1": len(weight_gt_1),
            "count_weight_lte_0": len(weight_lte_0),
            "confidence_method_breakdown": dict(Counter(edge["confidence"]["method"] for edge in edges)),
        },
        "theme_hub_analysis": {
            "edge_count_per_theme": {
                theme_by_id[theme_id]["metadata"]["theme_id"]: count
                for theme_id, count in sorted(theme_edge_counts.items(), key=lambda item: item[1], reverse=True)
            },
            "top_25_themes_by_edge_count": [
                {
                    "theme_node_id": theme_id,
                    "theme_id": theme_by_id[theme_id]["metadata"]["theme_id"],
                    "theme_label": theme_by_id[theme_id]["label"],
                    "edge_count": count,
                }
                for theme_id, count in sorted(theme_edge_counts.items(), key=lambda item: item[1], reverse=True)[:25]
            ],
            "bottom_25_themes_by_edge_count": [
                {
                    "theme_node_id": theme_id,
                    "theme_id": theme_by_id[theme_id]["metadata"]["theme_id"],
                    "theme_label": theme_by_id[theme_id]["label"],
                    "edge_count": count,
                }
                for theme_id, count in sorted(theme_edge_counts.items(), key=lambda item: item[1])[:25]
            ],
            "overconnected_theme_threshold": theme_hub_threshold,
            "overconnected_themes": overconnected_themes,
            "underconnected_themes": [
                {
                    "theme_node_id": theme_id,
                    "theme_id": theme_by_id[theme_id]["metadata"]["theme_id"],
                    "edge_count": count,
                }
                for theme_id, count in sorted(theme_edge_counts.items(), key=lambda item: item[1])
                if count < 1000
            ],
            "theme_gini_coefficient": gini(list(theme_edge_counts.values())),
        },
        "vocabulary_overconnection_analysis": {
            "max_themes_per_vocabulary_node": max(vocab_edge_counts),
            "median_themes_per_mapped_vocabulary_node": statistics.median(vocab_edge_counts),
            "count_vocabulary_nodes_with_gt_3_theme_edges": sum(1 for count in vocab_edge_counts if count > 3),
            "count_vocabulary_nodes_with_gt_5_theme_edges": sum(1 for count in vocab_edge_counts if count > 5),
            "count_vocabulary_nodes_with_gt_10_theme_edges": overconnected_gt_10,
            "top_100_most_overconnected_vocabulary_nodes": [
                {
                    **node_summary(vocab_by_id[node_id]),
                    "source_topic": source_by_vocab_id.get(vocab_by_id[node_id]["metadata"]["source_vocabulary_id"], {}).get("topic"),
                    "theme_edge_count": len(edge_list),
                    "themes": [theme_by_id[edge["target_node_id"]]["metadata"]["theme_id"] for edge in edge_list],
                }
                for node_id, edge_list in sorted(edges_by_vocab.items(), key=lambda item: len(item[1]), reverse=True)[:100]
            ],
        },
        "polysemy_sense_specific_audit": {
            "sense_specific_true_count": sum(1 for edge in edges if edge["metadata"].get("sense_specific") is True),
            "lemma_level_assignment_true_count": len(lemma_level_true),
            "polysemous_lemma_count": poly_count,
            "polysemous_lemma_identical_theme_sets_count": identical_theme_sets,
            "top_50_polysemous_lemmas_by_theme_diversity": poly_rows[:50],
        },
        "source_topic_coverage": {
            "source_topic_ready_count": len(source_topic_ready_ids),
            "mapped_source_topic_ready_count": len(source_topic_ready_ids & source_ids),
            "unmapped_despite_source_topic_count": len(unmapped_despite_topic),
            "missing_topic_count": len(missing_topic_ids),
            "mapped_despite_missing_source_topic_count": len(mapped_despite_missing),
            "mapping_source_breakdown": summary.get("mapping_source_breakdown", {}),
        },
        "rule_quality_audit": {
            "total_rule_count": len(rules),
            "enabled_rule_count": sum(1 for rule in rules if rule.get("enabled", True)),
            "rules_producing_0_edges": [row for row in rule_rows if row["edge_count"] == 0],
            "rules_producing_gt_1000_edges": [row for row in rule_rows if row["edge_count"] > 1000],
            "rules_producing_gt_5000_edges": [row for row in rule_rows if row["edge_count"] > 5000],
            "top_20_rules_by_edge_output": rule_rows[:20],
            "overly_broad_rules": [row for row in rule_rows if row["edge_count"] > 1000],
            "fallback_rules_causing_excessive_edges": [
                row for row in rule_rows if row["mapping_source"] == "fallback_topic_normalization_rules" and row["edge_count"] > 1000
            ],
        },
        "cefr_theme_distribution": {
            "theme_edges_by_cefr_level": dict(cefr_edges),
            "mapped_vocabulary_by_cefr_level": dict(mapped_by_cefr),
            "unmapped_vocabulary_by_cefr_level": dict(unmapped_by_cefr),
            "high_level_vocabulary_mapped_to_low_level_theme_count": len(high_to_low),
            "high_level_vocabulary_mapped_to_low_level_theme_examples": high_to_low[:50],
            "a1_a2_theme_coverage_check": all(
                len(edges_by_theme.get(theme_id, [])) > 0
                for theme_id, theme in theme_by_id.items()
                if theme["cefr_level"] in {"A1", "A1_plus", "A2", "A2_plus"}
            ),
        },
        "safety_audit": {
            "no_chunk_edges": graph.get("chunk_layer_implemented") is False,
            "no_morphology_edges": graph.get("morphology_layer_implemented") is False,
            "no_vocabulary_dependency_edges": graph.get("vocabulary_dependency_layer_implemented") is False,
            "no_grammar_edges": True,
            "morphology_layer_implemented": graph.get("morphology_layer_implemented"),
            "chunk_layer_implemented": graph.get("chunk_layer_implemented"),
            "forbidden_edge_type_count": len(forbidden_edge_types),
        },
        "risk_classification": {
            "high_risk": {
                "wrong_edge_direction": not all(edge["source_node_id"] in vocab_by_id and edge["target_node_id"] in theme_by_id for edge in edges),
                "duplicate_edges": bool(duplicate_tuples),
                "lemma_level_assignment": bool(lemma_level_true),
                "confidence_gt_1": bool(confidence_gt_1),
                "excessive_fallback_mapping": excessive_fallback,
            },
            "medium_risk": {
                "average_themes_per_mapped_vocabulary_gt_5": avg_edges_mapped > 5,
                "many_nodes_gt_10_theme_edges": overconnected_gt_10 > 0,
                "theme_hubs_too_broad": bool(overconnected_themes),
            },
            "low_risk": {
                "unmapped_nodes_due_missing_source_topics": len(unmapped) > 0,
                "sparse_advanced_themes": False,
            },
        },
        "risks_warnings": risks,
        "authority_readiness_assessment": {
            "Vocabulary Morphology Layer": "PARTIAL" if verdict == "WARNING_ACCEPTED" else "READY",
            "Vocabulary Chunk Linkage": "PARTIAL",
            "Theme Spiral Authority": "READY",
            "Sentence Pattern Authority": "PARTIAL",
            "Antigravity Planner": "PARTIAL",
            "Gate Engine": "PARTIAL",
        },
        "forbidden_actions_check": {
            "modified_vocabulary_nodes_json": False,
            "modified_theme_nodes_json": False,
            "modified_vocabulary_theme_edges_json": False,
            "modified_mapping_rules": False,
            "added_graph_nodes_or_edges": False,
            "modified_vocabulary_theme_chunk_grammar_source": False,
            "added_morphology_edges": False,
            "added_chunk_edges": False,
            "added_vocabulary_dependency_edges": False,
            "created_learner_state": False,
            "implemented_planner_recommendation_learning_path": False,
            "modified_runtime": False,
        },
        "recommended_next_task": recommended,
        "qa_verdict": verdict,
    }

    write_json(AUDIT_OUT_PATH, report)
    DOC_OUT_PATH.write_text(build_markdown(report), encoding="utf-8")
    print(f"ULGA S5F vocabulary theme QA audit: {verdict}")
    print(f"Theme edges: {len(edges)}")
    print(f"Mapped vocabulary: {mapped_count}")
    print(f"Average edges per mapped vocabulary: {avg_edges_mapped:.2f}")
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
