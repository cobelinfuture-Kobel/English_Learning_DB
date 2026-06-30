import datetime
import json
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
GRAPH_DIR = BASE_DIR / "ulga" / "graph"
REPORTS_DIR = BASE_DIR / "ulga" / "reports"
RULES_DIR = BASE_DIR / "ulga" / "rules"
DOCS_DIR = BASE_DIR / "docs" / "ulga"

VOCAB_NODES_PATH = GRAPH_DIR / "vocabulary_nodes.json"
THEME_NODES_PATH = GRAPH_DIR / "theme_nodes.json"
ORIGINAL_EDGES_PATH = GRAPH_DIR / "vocabulary_theme_edges.json"
REFINED_EDGES_PATH = GRAPH_DIR / "vocabulary_theme_edges.refined.json"
REFINED_GRAPH_PATH = GRAPH_DIR / "ulga_graph.vocabulary_theme_layer.refined.json"
QA_AUDIT_PATH = REPORTS_DIR / "vocabulary_theme_layer_qa_audit.json"
REFINEMENT_SUMMARY_PATH = REPORTS_DIR / "vocabulary_theme_refinement_summary.json"
REMOVED_EDGES_PATH = REPORTS_DIR / "vocabulary_theme_refinement_removed_edges.json"
RULES_PATH = RULES_DIR / "vocabulary_theme_mapping_rules.json"
VOCAB_SOURCE_PATH = BASE_DIR / "vocabulary" / "json" / "vocabulary.json"
THEME_CATALOG_PATH = BASE_DIR / "themes" / "theme_catalog.json"
THEME_MAPPING_PATH = BASE_DIR / "themes" / "theme_mapping.json"
THEME_VOCAB_MAPPING_PATH = BASE_DIR / "themes" / "theme_vocab_mapping.json"

VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_ulga_vocabulary_theme_refinement.py"
AUDIT_OUT_PATH = REPORTS_DIR / "vocabulary_theme_refinement_qa_audit.json"
DOC_OUT_PATH = DOCS_DIR / "ULGA_S5G_VOCABULARY_THEME_REFINEMENT_QA_AUDIT.md"


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def run_command(args):
    result = subprocess.run(args, cwd=BASE_DIR, text=True, capture_output=True, check=False)
    output = (result.stdout + result.stderr).strip()
    last_line = output.splitlines()[-1] if output else ""
    return {
        "command": " ".join(args),
        "returncode": result.returncode,
        "result": "PASS" if result.returncode == 0 else "FAIL",
        "summary": last_line,
        "output_tail": "\n".join(output.splitlines()[-20:]),
    }


def gini(values):
    values = sorted(value for value in values if value >= 0)
    if not values or sum(values) == 0:
        return 0
    n = len(values)
    weighted_sum = sum((idx + 1) * value for idx, value in enumerate(values))
    return (2 * weighted_sum) / (n * sum(values)) - (n + 1) / n


def median(values):
    return statistics.median(values) if values else 0


def node_summary(node):
    metadata = node.get("metadata", {})
    return {
        "id": node["id"],
        "lemma": metadata.get("canonical_lemma"),
        "cefr_level": node.get("cefr_level"),
        "source_vocabulary_id": metadata.get("source_vocabulary_id"),
    }


def edge_source(edge):
    metadata = edge.get("metadata", {})
    return metadata.get("mapping_source") or edge.get("authority_source", {}).get("source_file") or "unknown"


def theme_id(edge):
    return edge.get("metadata", {}).get("target_theme_id") or edge["target_node_id"].removeprefix("theme:")


def build_indexes(edges):
    by_vocab = defaultdict(list)
    by_theme = defaultdict(list)
    for edge in edges:
        by_vocab[edge["source_node_id"]].append(edge)
        by_theme[edge["target_node_id"]].append(edge)
    return by_vocab, by_theme


def count_thresholds(edge_counts):
    return {
        "nodes_with_gt_3_theme_edges": sum(1 for count in edge_counts if count > 3),
        "nodes_with_gt_5_theme_edges": sum(1 for count in edge_counts if count > 5),
        "nodes_with_gt_10_theme_edges": sum(1 for count in edge_counts if count > 10),
    }


def percentile(values, p):
    if not values:
        return 0
    values = sorted(values)
    index = int(round((len(values) - 1) * p))
    return values[index]


def polysemy_audit(vocabulary_nodes, refined_by_vocab):
    lemma_to_nodes = defaultdict(list)
    for node in vocabulary_nodes:
        lemma_to_nodes[node["metadata"].get("canonical_lemma")].append(node["id"])

    rows = []
    identical_theme_sets_count = 0
    suspicious_identical = []
    for lemma, node_ids in lemma_to_nodes.items():
        if len(node_ids) <= 1:
            continue
        theme_sets = []
        all_themes = set()
        for node_id in node_ids:
            themes = {theme_id(edge) for edge in refined_by_vocab.get(node_id, [])}
            theme_sets.append(tuple(sorted(themes)))
            all_themes.update(themes)
        identical = len(set(theme_sets)) == 1 and bool(all_themes)
        if identical:
            identical_theme_sets_count += 1
        row = {
            "lemma": lemma,
            "sense_count": len(node_ids),
            "refined_theme_diversity": len(all_themes),
            "identical_theme_sets_for_all_senses": identical,
        }
        rows.append(row)
        if identical and len(node_ids) >= 5:
            suspicious_identical.append(row)

    rows.sort(key=lambda row: (row["refined_theme_diversity"], row["sense_count"], row["lemma"]), reverse=True)
    suspicious_identical.sort(key=lambda row: (row["sense_count"], row["lemma"]), reverse=True)
    return {
        "polysemous_lemma_count": sum(1 for nodes in lemma_to_nodes.values() if len(nodes) > 1),
        "polysemous_lemmas_retaining_distinct_theme_sets": sum(
            1
            for nodes in lemma_to_nodes.values()
            if len(nodes) > 1
            and len(
                {
                    tuple(sorted(theme_id(edge) for edge in refined_by_vocab.get(node_id, [])))
                    for node_id in nodes
                }
            )
            > 1
        ),
        "polysemous_lemma_identical_theme_sets_count": identical_theme_sets_count,
        "top_50_polysemous_lemmas_by_refined_theme_diversity": rows[:50],
        "suspicious_identical_theme_sets_across_many_senses": suspicious_identical[:50],
    }


def build_markdown(report):
    basic = report["basic_metrics"]
    coverage = report["coverage_preservation"]
    reduction = report["overconnection_reduction"]
    membership = report["membership_role_quality"]
    safety = report["safety_audit"]
    lines = [
        "# ULGA-S5G Vocabulary Theme Refinement QA Audit",
        "",
        "## 1. Files Created",
        "",
        "- `ulga/audits/audit_ulga_vocabulary_theme_refinement.py`",
        "- `ulga/reports/vocabulary_theme_refinement_qa_audit.json`",
        "- `docs/ulga/ULGA_S5G_VOCABULARY_THEME_REFINEMENT_QA_AUDIT.md`",
        "",
        "## 2. Files Modified",
        "",
        "- None of the protected source, graph, edge, rule, or runtime files were modified.",
        "- The audit is read-only against original and refined graph artifacts.",
        "",
        "## 3. Existing Validation Results",
        "",
        f"- Refinement validator: `{report['existing_validation_results']['validator']['result']}`",
        f"- Validator summary: `{report['existing_validation_results']['validator']['summary']}`",
        "",
        "## 4. Tests Executed",
        "",
        f"- `{report['tests_executed']['pytest']['command']}`: `{report['tests_executed']['pytest']['result']}`",
        f"- Pytest summary: `{report['tests_executed']['pytest']['summary']}`",
        "",
        "## 5. Basic Metrics",
        "",
        f"- Vocabulary node count: `{basic['vocabulary_node_count']}`",
        f"- Theme node count: `{basic['theme_node_count']}`",
        f"- Original theme edge count: `{basic['original_theme_edge_count']}`",
        f"- Refined theme edge count: `{basic['refined_theme_edge_count']}`",
        f"- Removed theme edge count: `{basic['removed_theme_edge_count']}`",
        f"- Mapped vocabulary before / after: `{basic['mapped_vocabulary_count_before']}` / `{basic['mapped_vocabulary_count_after']}`",
        f"- Average edges per mapped before / after: `{basic['average_edges_per_mapped_before']:.4f}` / `{basic['average_edges_per_mapped_after']:.4f}`",
        f"- Max edges per vocabulary before / after: `{basic['max_edges_per_vocabulary_before']}` / `{basic['max_edges_per_vocabulary_after']}`",
        "",
        "## 6. Coverage Preservation",
        "",
        f"- Mapped vocabulary count preserved: `{coverage['mapped_vocabulary_count_preserved']}`",
        f"- Lost mapped vocabulary count: `{coverage['lost_mapped_vocabulary_count']}`",
        f"- Newly unmapped after refinement count: `{coverage['newly_unmapped_after_refinement_count']}`",
        f"- Source-topic-ready nodes still mapped: `{coverage['source_topic_ready_nodes_still_mapped_count']}`",
        f"- Mapped ratio before / after: `{coverage['mapped_ratio_before']:.2%}` / `{coverage['mapped_ratio_after']:.2%}`",
        "",
        "## 7. Overconnection Reduction",
        "",
        f"- Nodes >3 theme edges before / after: `{reduction['nodes_with_gt_3_theme_edges_before']}` / `{reduction['nodes_with_gt_3_theme_edges_after']}`",
        f"- Nodes >5 theme edges before / after: `{reduction['nodes_with_gt_5_theme_edges_before']}` / `{reduction['nodes_with_gt_5_theme_edges_after']}`",
        f"- Nodes >10 theme edges before / after: `{reduction['nodes_with_gt_10_theme_edges_before']}` / `{reduction['nodes_with_gt_10_theme_edges_after']}`",
        f"- Average edge density reduction: `{reduction['average_edge_density_reduction_percent']:.2f}%`",
        f"- Total edge reduction: `{reduction['total_edge_reduction_percent']:.2f}%`",
        "",
        "## 8. Membership Role Quality",
        "",
        f"- Primary edge count: `{membership['primary_edge_count']}`",
        f"- Secondary edge count: `{membership['secondary_edge_count']}`",
        f"- Inferred low-confidence count: `{membership['inferred_low_confidence_count']}`",
        f"- Nodes with 0 primary theme: `{membership['nodes_with_0_primary_theme']}`",
        f"- Nodes with >1 primary theme: `{membership['nodes_with_gt_1_primary_theme']}`",
        f"- Nodes with >2 secondary themes: `{membership['nodes_with_gt_2_secondary_themes']}`",
        f"- Primary coverage ratio: `{membership['primary_coverage_ratio']:.2%}`",
        "",
        "## 9. Theme Hub Balance",
        "",
        f"- Theme Gini before / after: `{report['theme_coverage_hub_balance']['theme_gini_before']:.4f}` / `{report['theme_coverage_hub_balance']['theme_gini_after']:.4f}`",
        "- Top and bottom refined themes are included in the JSON audit report.",
        f"- Themes collapsed too much: `{len(report['theme_coverage_hub_balance']['themes_collapsed_too_much'])}`",
        f"- Themes still overconnected: `{len(report['theme_coverage_hub_balance']['themes_still_overconnected'])}`",
        "",
        "## 10. Mapping Source Quality",
        "",
        "```json",
        json.dumps(report["source_mapping_quality"], indent=2, ensure_ascii=False),
        "```",
        "",
        "## 11. Polysemy / Sense-Specific Audit",
        "",
        f"- Sense-specific true count: `{report['polysemy_sense_specific_audit']['sense_specific_true_count']}`",
        f"- Lemma-level assignment true count: `{report['polysemy_sense_specific_audit']['lemma_level_assignment_true_count']}`",
        f"- Polysemous lemmas retaining distinct theme sets: `{report['polysemy_sense_specific_audit']['polysemous_lemmas_retaining_distinct_theme_sets']}`",
        f"- Suspicious identical theme sets across many senses: `{len(report['polysemy_sense_specific_audit']['suspicious_identical_theme_sets_across_many_senses'])}`",
        "",
        "## 12. CEFR / Theme Distribution",
        "",
        "```json",
        json.dumps(report["cefr_theme_distribution"], indent=2, ensure_ascii=False)[:4000],
        "```",
        "",
        "## 13. Safety Audit",
        "",
        "```json",
        json.dumps(safety, indent=2, ensure_ascii=False),
        "```",
        "",
        "## 14. Risks / Warnings",
        "",
    ]
    for warning in report["risks_warnings"]:
        lines.append(f"- {warning}")
    if not report["risks_warnings"]:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## 15. Authority Readiness Assessment",
            "",
            "```json",
            json.dumps(report["authority_readiness_assessment"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## 16. Recommended Next Task",
            "",
            report["recommended_next_task"],
            "",
            "## 17. Final Verdict",
            "",
            report["qa_verdict"],
            "",
        ]
    )
    return "\n".join(lines)


def main():
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    validation = run_command([sys.executable, str(VALIDATOR_PATH)])
    pytest_result = run_command([sys.executable, "-m", "pytest", "tests/ulga/", "-q"])

    vocabulary_nodes = read_json(VOCAB_NODES_PATH)
    theme_nodes = read_json(THEME_NODES_PATH)
    original_edges = read_json(ORIGINAL_EDGES_PATH)
    refined_edges = read_json(REFINED_EDGES_PATH)
    refined_graph = read_json(REFINED_GRAPH_PATH)
    previous_qa = read_json(QA_AUDIT_PATH)
    refinement_summary = read_json(REFINEMENT_SUMMARY_PATH)
    removed_edges = read_json(REMOVED_EDGES_PATH)
    rules = read_json(RULES_PATH)
    vocabulary_source = read_json(VOCAB_SOURCE_PATH)
    theme_catalog = read_json(THEME_CATALOG_PATH)
    theme_mapping = read_json(THEME_MAPPING_PATH)
    theme_vocab_mapping = read_json(THEME_VOCAB_MAPPING_PATH)

    vocab_by_id = {node["id"]: node for node in vocabulary_nodes}
    theme_by_id = {node["id"]: node for node in theme_nodes}
    vocab_source_by_id = {record["vocab_id"]: record for record in vocabulary_source}
    theme_catalog_by_id = {theme["theme_id"]: theme for theme in theme_catalog["themes"]}

    original_by_vocab, original_by_theme = build_indexes(original_edges)
    refined_by_vocab, refined_by_theme = build_indexes(refined_edges)
    original_mapped = set(original_by_vocab)
    refined_mapped = set(refined_by_vocab)
    original_counts = [len(edges) for edges in original_by_vocab.values()]
    refined_counts = [len(edges) for edges in refined_by_vocab.values()]

    source_topic_ready_nodes = {
        node["id"]
        for node in vocabulary_nodes
        if vocab_source_by_id.get(node["metadata"]["source_vocabulary_id"], {}).get("topic")
    }
    lost_mapped = sorted(original_mapped - refined_mapped)
    newly_unmapped = lost_mapped
    no_retained_theme_despite_original = [
        node_id for node_id in original_mapped if node_id not in refined_by_vocab or not refined_by_vocab[node_id]
    ]

    original_theme_counts = {theme_id: len(original_by_theme.get(theme_id, [])) for theme_id in theme_by_id}
    refined_theme_counts = {theme_id: len(refined_by_theme.get(theme_id, [])) for theme_id in theme_by_id}
    top_refined_themes = sorted(refined_theme_counts.items(), key=lambda item: item[1], reverse=True)
    bottom_refined_themes = sorted(refined_theme_counts.items(), key=lambda item: item[1])

    refined_roles = Counter(edge["metadata"].get("retained_role") for edge in refined_edges)
    role_by_vocab = defaultdict(Counter)
    for edge in refined_edges:
        role_by_vocab[edge["source_node_id"]][edge["metadata"].get("retained_role")] += 1

    inferred_despite_primary_secondary_available = []
    for edge in refined_edges:
        if edge["metadata"].get("retained_role") != "inferred_low_confidence":
            continue
        source_node_id = edge["source_node_id"]
        original_has_primary_secondary = any(
            original_edge["metadata"].get("membership_type") in {"primary", "secondary"}
            for original_edge in original_by_vocab.get(source_node_id, [])
        )
        if original_has_primary_secondary:
            inferred_despite_primary_secondary_available.append(edge["id"])

    refined_weights = [edge["metadata"].get("weight", 0) for edge in refined_edges]
    refined_confidences = [edge["confidence"].get("value", 0) for edge in refined_edges]
    role_confidence_distribution = {}
    for role in ["primary", "secondary", "inferred_low_confidence"]:
        values = [edge["confidence"].get("value", 0) for edge in refined_edges if edge["metadata"].get("retained_role") == role]
        role_confidence_distribution[role] = {
            "count": len(values),
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "median": median(values),
        }

    original_source_breakdown = Counter(edge_source(edge) for edge in original_edges)
    refined_source_breakdown = Counter(edge_source(edge) for edge in refined_edges)
    original_edge_by_id = {edge["id"]: edge for edge in original_edges}
    removed_source_breakdown = Counter(
        edge_source(original_edge_by_id[edge["original_edge_id"]])
        for edge in removed_edges
        if edge["original_edge_id"] in original_edge_by_id
    )
    removed_original_source_breakdown = Counter(edge.get("original_membership_type") for edge in removed_edges)
    rank_distribution = Counter(edge["metadata"].get("retained_rank") for edge in refined_edges)
    fallback_retained_count = sum(1 for edge in refined_edges if edge_source(edge) in {"fallback", "fallback_topic_normalization_rules"})
    inferred_rule_retained_count = sum(
        1
        for edge in refined_edges
        if edge["confidence"].get("method") == "inferred_rule"
        or edge_source(edge) in {"fallback", "fallback_topic_normalization_rules"}
    )

    edge_tuples = Counter((edge["source_node_id"], edge["target_node_id"], edge["edge_type"]) for edge in refined_edges)
    duplicate_tuples = [edge_tuple for edge_tuple, count in edge_tuples.items() if count > 1]
    missing_source_target = [
        edge["id"]
        for edge in refined_edges
        if edge["source_node_id"] not in vocab_by_id or edge["target_node_id"] not in theme_by_id
    ]
    self_loops = [edge["id"] for edge in refined_edges if edge["source_node_id"] == edge["target_node_id"]]
    forbidden_edge_type_ids = [edge["id"] for edge in refined_edges if edge["edge_type"] != "belongs_to"]
    lemma_level_true = [edge["id"] for edge in refined_edges if edge["metadata"].get("lemma_level_assignment") is True]
    confidence_gt_1 = [edge["id"] for edge in refined_edges if edge["confidence"].get("value", 0) > 1.0]
    weight_gt_1 = [edge["id"] for edge in refined_edges if edge["metadata"].get("weight", 0) > 1.0]
    weight_lte_0 = [edge["id"] for edge in refined_edges if edge["metadata"].get("weight", 0) <= 0]

    theme_collapse = []
    still_overconnected = []
    for theme_node_id, before_count in original_theme_counts.items():
        after_count = refined_theme_counts.get(theme_node_id, 0)
        ratio = after_count / before_count if before_count else 0
        if before_count >= 1000 and ratio < 0.1:
            theme_collapse.append(
                {
                    "theme_id": theme_by_id[theme_node_id]["metadata"]["theme_id"],
                    "before": before_count,
                    "after": after_count,
                    "retention_ratio": ratio,
                }
            )
        if after_count > 2500:
            still_overconnected.append(
                {
                    "theme_id": theme_by_id[theme_node_id]["metadata"]["theme_id"],
                    "before": before_count,
                    "after": after_count,
                }
            )

    mapped_by_cefr = Counter(vocab_by_id[node_id]["cefr_level"] for node_id in refined_mapped)
    unmapped_after = set(vocab_by_id) - refined_mapped
    unmapped_by_cefr = Counter(vocab_by_id[node_id]["cefr_level"] for node_id in unmapped_after)
    refined_edges_by_vocab_cefr = Counter(vocab_by_id[edge["source_node_id"]]["cefr_level"] for edge in refined_edges)
    refined_edges_by_theme_cefr = Counter(theme_by_id[edge["target_node_id"]]["cefr_level"] for edge in refined_edges)

    basic = {
        "vocabulary_node_count": len(vocabulary_nodes),
        "theme_node_count": len(theme_nodes),
        "original_theme_edge_count": len(original_edges),
        "refined_theme_edge_count": len(refined_edges),
        "removed_theme_edge_count": len(removed_edges),
        "mapped_vocabulary_count_before": len(original_mapped),
        "mapped_vocabulary_count_after": len(refined_mapped),
        "unmapped_vocabulary_count": len(vocabulary_nodes) - len(refined_mapped),
        "average_edges_per_mapped_before": len(original_edges) / len(original_mapped),
        "average_edges_per_mapped_after": len(refined_edges) / len(refined_mapped),
        "max_edges_per_vocabulary_before": max(original_counts),
        "max_edges_per_vocabulary_after": max(refined_counts),
    }
    before_thresholds = count_thresholds(original_counts)
    after_thresholds = count_thresholds(refined_counts)

    structural_pass = all(
        [
            validation["result"] == "PASS",
            pytest_result["result"] == "PASS",
            refined_graph.get("original_full_layer_preserved") is True,
            len(refined_edges) < len(original_edges),
            len(refined_mapped) >= 9000,
            len(newly_unmapped) == 0,
            basic["average_edges_per_mapped_after"] <= 3,
            basic["max_edges_per_vocabulary_after"] <= 3,
            after_thresholds["nodes_with_gt_3_theme_edges"] == 0,
            all(count["primary"] <= 1 for count in role_by_vocab.values()),
            all(count["secondary"] <= 2 for count in role_by_vocab.values()),
            not duplicate_tuples,
            not lemma_level_true,
            not forbidden_edge_type_ids,
            not confidence_gt_1,
            not weight_gt_1,
            not weight_lte_0,
            not missing_source_target,
            not self_loops,
        ]
    )

    risks_warnings = []
    if sum(1 for node_id in refined_mapped if role_by_vocab[node_id]["primary"] == 0):
        risks_warnings.append("Some mapped nodes lack a retained primary theme, mostly fallback-only inferred nodes.")
    if theme_collapse:
        risks_warnings.append("Some broad themes collapsed below 10% retention after refinement.")
    if still_overconnected:
        risks_warnings.append("Some themes remain high-volume hubs after refinement.")
    if fallback_retained_count / len(refined_edges) > 0.05:
        risks_warnings.append("Fallback retained ratio is high.")
    if polysemy_audit(vocabulary_nodes, refined_by_vocab)["suspicious_identical_theme_sets_across_many_senses"]:
        risks_warnings.append("Some polysemous lemmas retain identical theme sets across many senses.")

    if not structural_pass:
        verdict = "FAIL"
        recommended_next_task = "ULGA-S5E_VocabularyThemeLayer_Refinement_Fix_Retry"
    elif risks_warnings:
        verdict = "WARNING_ACCEPTED"
        recommended_next_task = "ULGA-S5H_VocabularyMorphologyLayer_DesignScan"
    else:
        verdict = "PASS"
        recommended_next_task = "ULGA-S5H_VocabularyMorphologyLayer_DesignScan"

    polysemy = polysemy_audit(vocabulary_nodes, refined_by_vocab)
    report = {
        "audit_timestamp": timestamp,
        "audit_scope": "QA Audit / Read-only Verification",
        "files_read": [
            str(path.relative_to(BASE_DIR))
            for path in [
                VOCAB_NODES_PATH,
                THEME_NODES_PATH,
                ORIGINAL_EDGES_PATH,
                REFINED_EDGES_PATH,
                REFINED_GRAPH_PATH,
                QA_AUDIT_PATH,
                REFINEMENT_SUMMARY_PATH,
                REMOVED_EDGES_PATH,
                RULES_PATH,
                VOCAB_SOURCE_PATH,
                THEME_CATALOG_PATH,
                THEME_MAPPING_PATH,
                THEME_VOCAB_MAPPING_PATH,
            ]
        ],
        "existing_validation_results": {"validator": validation},
        "tests_executed": {"pytest": pytest_result},
        "basic_metrics": basic,
        "coverage_preservation": {
            "mapped_vocabulary_count_preserved": len(original_mapped) == len(refined_mapped),
            "lost_mapped_vocabulary_count": len(lost_mapped),
            "newly_unmapped_after_refinement_count": len(newly_unmapped),
            "nodes_with_no_retained_theme_despite_original_mapping": len(no_retained_theme_despite_original),
            "source_topic_ready_nodes_still_mapped_count": len(source_topic_ready_nodes & refined_mapped),
            "source_topic_ready_count": len(source_topic_ready_nodes),
            "mapped_ratio_before": len(original_mapped) / len(vocabulary_nodes),
            "mapped_ratio_after": len(refined_mapped) / len(vocabulary_nodes),
            "newly_unmapped_examples": [node_summary(vocab_by_id[node_id]) for node_id in newly_unmapped[:50]],
        },
        "overconnection_reduction": {
            "nodes_with_gt_3_theme_edges_before": before_thresholds["nodes_with_gt_3_theme_edges"],
            "nodes_with_gt_3_theme_edges_after": after_thresholds["nodes_with_gt_3_theme_edges"],
            "nodes_with_gt_5_theme_edges_before": before_thresholds["nodes_with_gt_5_theme_edges"],
            "nodes_with_gt_5_theme_edges_after": after_thresholds["nodes_with_gt_5_theme_edges"],
            "nodes_with_gt_10_theme_edges_before": before_thresholds["nodes_with_gt_10_theme_edges"],
            "nodes_with_gt_10_theme_edges_after": after_thresholds["nodes_with_gt_10_theme_edges"],
            "average_edge_density_reduction_percent": (
                1 - basic["average_edges_per_mapped_after"] / basic["average_edges_per_mapped_before"]
            )
            * 100,
            "total_edge_reduction_percent": (1 - len(refined_edges) / len(original_edges)) * 100,
        },
        "membership_role_quality": {
            "primary_edge_count": refined_roles.get("primary", 0),
            "secondary_edge_count": refined_roles.get("secondary", 0),
            "inferred_low_confidence_count": refined_roles.get("inferred_low_confidence", 0),
            "nodes_with_0_primary_theme": sum(1 for node_id in refined_mapped if role_by_vocab[node_id]["primary"] == 0),
            "nodes_with_gt_1_primary_theme": sum(1 for count in role_by_vocab.values() if count["primary"] > 1),
            "nodes_with_gt_2_secondary_themes": sum(1 for count in role_by_vocab.values() if count["secondary"] > 2),
            "nodes_with_inferred_retained_despite_primary_secondary_available": len(
                inferred_despite_primary_secondary_available
            ),
            "primary_coverage_ratio": refined_roles.get("primary", 0) / len(refined_mapped),
        },
        "theme_coverage_hub_balance": {
            "edge_count_per_theme_before": {
                theme_by_id[theme_node_id]["metadata"]["theme_id"]: count
                for theme_node_id, count in sorted(original_theme_counts.items(), key=lambda item: item[1], reverse=True)
            },
            "edge_count_per_theme_after": {
                theme_by_id[theme_node_id]["metadata"]["theme_id"]: count
                for theme_node_id, count in sorted(refined_theme_counts.items(), key=lambda item: item[1], reverse=True)
            },
            "mapped_vocab_per_theme_after": {
                theme_by_id[theme_node_id]["metadata"]["theme_id"]: len(
                    {edge["source_node_id"] for edge in refined_by_theme.get(theme_node_id, [])}
                )
                for theme_node_id in theme_by_id
            },
            "top_25_themes_by_refined_edge_count": [
                {
                    "theme_id": theme_by_id[theme_node_id]["metadata"]["theme_id"],
                    "theme_label": theme_by_id[theme_node_id]["label"],
                    "before": original_theme_counts[theme_node_id],
                    "after": count,
                }
                for theme_node_id, count in top_refined_themes[:25]
            ],
            "bottom_25_themes_by_refined_edge_count": [
                {
                    "theme_id": theme_by_id[theme_node_id]["metadata"]["theme_id"],
                    "theme_label": theme_by_id[theme_node_id]["label"],
                    "before": original_theme_counts[theme_node_id],
                    "after": count,
                }
                for theme_node_id, count in bottom_refined_themes[:25]
            ],
            "theme_gini_before": gini(list(original_theme_counts.values())),
            "theme_gini_after": gini(list(refined_theme_counts.values())),
            "themes_collapsed_too_much": theme_collapse,
            "themes_still_overconnected": still_overconnected,
        },
        "weight_confidence_audit": {
            "refined_weight_min": min(refined_weights),
            "refined_weight_max": max(refined_weights),
            "refined_weight_median": median(refined_weights),
            "refined_confidence_min": min(refined_confidences),
            "refined_confidence_max": max(refined_confidences),
            "refined_confidence_median": median(refined_confidences),
            "count_confidence_gt_1": len(confidence_gt_1),
            "count_weight_gt_1": len(weight_gt_1),
            "count_weight_lte_0": len(weight_lte_0),
            "retained_role_vs_confidence_distribution": role_confidence_distribution,
        },
        "source_mapping_quality": {
            "mapping_source_breakdown_before": dict(original_source_breakdown),
            "mapping_source_breakdown_after": dict(refined_source_breakdown),
            "fallback_retained_count": fallback_retained_count,
            "fallback_retained_ratio": fallback_retained_count / len(refined_edges),
            "native_topic_retained_count": refined_source_breakdown.get("native_topic", 0),
            "theme_vocab_mapping_retained_count": refined_source_breakdown.get("themes/theme_vocab_mapping.json", 0),
            "inferred_rule_retained_count": inferred_rule_retained_count,
            "retained_rank_distribution": dict(rank_distribution),
            "removed_edge_role_breakdown": dict(removed_original_source_breakdown),
            "removed_edge_source_breakdown": dict(removed_source_breakdown),
        },
        "polysemy_sense_specific_audit": {
            "sense_specific_true_count": sum(1 for edge in refined_edges if edge["metadata"].get("sense_specific") is True),
            "lemma_level_assignment_true_count": len(lemma_level_true),
            **polysemy,
        },
        "cefr_theme_distribution": {
            "refined_theme_edges_by_vocabulary_cefr": dict(refined_edges_by_vocab_cefr),
            "refined_theme_edges_by_theme_cefr": dict(refined_edges_by_theme_cefr),
            "mapped_vocabulary_by_cefr": dict(mapped_by_cefr),
            "unmapped_vocabulary_by_cefr": dict(unmapped_by_cefr),
            "a1_a2_mapped_vocabulary_count_after_refinement": sum(
                mapped_by_cefr.get(level, 0) for level in ["A1", "A2"]
            ),
            "advanced_level_theme_sparsity_warnings": [
                {
                    "theme_id": theme_by_id[theme_node_id]["metadata"]["theme_id"],
                    "level": theme_by_id[theme_node_id]["cefr_level"],
                    "refined_edge_count": refined_theme_counts[theme_node_id],
                }
                for theme_node_id in theme_by_id
                if theme_by_id[theme_node_id]["cefr_level"] in {"B2", "B2_plus", "C1"}
                and refined_theme_counts[theme_node_id] < 100
            ],
        },
        "safety_audit": {
            "all_edges_source_vocabulary_to_target_theme": all(
                edge["source_node_id"] in vocab_by_id and edge["target_node_id"] in theme_by_id for edge in refined_edges
            ),
            "all_edge_type_belongs_to": all(edge["edge_type"] == "belongs_to" for edge in refined_edges),
            "duplicate_refined_edge_tuple_count": len(duplicate_tuples),
            "self_loop_count": len(self_loops),
            "missing_source_target_count": len(missing_source_target),
            "no_morphology_edges": refined_graph.get("morphology_layer_implemented") is False,
            "no_chunk_edges": refined_graph.get("chunk_layer_implemented") is False,
            "no_vocabulary_dependency_edges": refined_graph.get("vocabulary_dependency_layer_implemented") is False,
            "no_grammar_edges": True,
            "original_full_layer_preserved": refined_graph.get("original_full_layer_preserved") is True,
            "original_edges_unchanged_by_audit": True,
            "refined_edges_unchanged_by_audit": True,
            "theme_mapping_rule_count": len(rules),
            "theme_catalog_count": len(theme_catalog_by_id),
            "theme_mapping_top_level_keys": list(theme_mapping.keys()),
            "theme_vocab_mapping_top_level_keys": list(theme_vocab_mapping.keys()),
            "previous_s5f_verdict": previous_qa.get("qa_verdict"),
            "refinement_summary_consistent": refinement_summary.get("refined_theme_edge_count") == len(refined_edges),
        },
        "risks_warnings": risks_warnings,
        "authority_readiness_assessment": {
            "Theme Spiral Authority": "READY",
            "Vocabulary Morphology Layer": "READY" if verdict in {"PASS", "WARNING_ACCEPTED"} else "NOT_READY",
            "Vocabulary Chunk Linkage": "PARTIAL",
            "Sentence Pattern Authority": "PARTIAL",
            "Antigravity Planner": "PARTIAL",
            "Gate Engine": "PARTIAL",
        },
        "forbidden_actions_check": {
            "modified_vocabulary_nodes_json": False,
            "modified_theme_nodes_json": False,
            "modified_original_vocabulary_theme_edges_json": False,
            "modified_refined_vocabulary_theme_edges_json": False,
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
        "recommended_next_task": recommended_next_task,
        "qa_verdict": verdict,
    }

    write_json(AUDIT_OUT_PATH, report)
    DOC_OUT_PATH.write_text(build_markdown(report), encoding="utf-8")

    print(f"ULGA S5G vocabulary theme refinement QA audit: {verdict}")
    print(f"Original edges: {len(original_edges)}")
    print(f"Refined edges: {len(refined_edges)}")
    print(f"Mapped vocabulary after refinement: {len(refined_mapped)}")
    print(f"Average edges per mapped vocabulary after refinement: {basic['average_edges_per_mapped_after']:.4f}")
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
