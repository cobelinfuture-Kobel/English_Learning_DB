import json
import datetime
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[2]
NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
EDGES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_dependency_core_edges.json"
RULES_PATH = BASE_DIR / "ulga" / "rules" / "grammar_dependency_core_rules.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_dependency_core_summary.json"
SKIPPED_PATH = BASE_DIR / "ulga" / "reports" / "grammar_dependency_core_skipped_rules.json"

AUDIT_JSON_OUT = BASE_DIR / "ulga" / "reports" / "grammar_dependency_core_qa_audit.json"

CEFR_ORDER = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

def get_cefr_rank(level):
    return CEFR_ORDER.get(level, 0)

def find_longest_chain(nodes_list, edges):
    adj = defaultdict(list)
    for edge in edges:
        if edge["edge_type"] in ("prerequisite", "unlocks"):
            adj[edge["source_node_id"]].append(edge["target_node_id"])
            
    memo = {}
    
    def dfs(node):
        if node in memo:
            return memo[node]
        longest = 0
        for neighbor in adj[node]:
            longest = max(longest, 1 + dfs(neighbor))
        memo[node] = longest
        return longest
        
    max_len = 0
    for node in nodes_list:
        max_len = max(max_len, dfs(node))
    return max_len

def run_audit():
    # 1. Load data
    with open(NODES_PATH, "r", encoding="utf-8") as f:
        nodes = json.load(f)
    with open(EDGES_PATH, "r", encoding="utf-8") as f:
        edges = json.load(f)
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        rules = json.load(f)
    with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
        summary = json.load(f)
    with open(SKIPPED_PATH, "r", encoding="utf-8") as f:
        skipped = json.load(f)

    node_count = len(nodes)
    edge_count = len(edges)
    enabled_rules = [r for r in rules if r.get("enabled", True)]
    enabled_rule_count = len(enabled_rules)
    skipped_rule_count = len(skipped)

    node_dict = {n["id"]: n for n in nodes}
    node_ids = set(node_dict.keys())

    # Degree initialization
    in_degrees = defaultdict(int)
    out_degrees = defaultdict(int)
    
    # Degrees for prerequisite/unlocks subgraph
    hard_in_degrees = defaultdict(int)
    hard_out_degrees = defaultdict(int)

    for edge in edges:
        src = edge["source_node_id"]
        tgt = edge["target_node_id"]
        in_degrees[tgt] += 1
        out_degrees[src] += 1
        if edge["edge_type"] in ("prerequisite", "unlocks"):
            hard_in_degrees[tgt] += 1
            hard_out_degrees[src] += 1

    # B. Isolated Node Analysis
    isolated_nodes = []
    zero_in_degree = []
    zero_out_degree = []
    connected_nodes = []

    for nid in node_ids:
        in_d = in_degrees[nid]
        out_d = out_degrees[nid]
        if in_d == 0 and out_d == 0:
            isolated_nodes.append(nid)
        else:
            connected_nodes.append(nid)
        if in_d == 0:
            zero_in_degree.append(nid)
        if out_d == 0:
            zero_out_degree.append(nid)

    isolated_node_count = len(isolated_nodes)
    isolated_node_ratio = isolated_node_count / node_count
    connected_node_count = len(connected_nodes)
    connected_node_ratio = connected_node_count / node_count

    # C. Degree Distribution
    all_in_degrees = [in_degrees[nid] for nid in node_ids]
    all_out_degrees = [out_degrees[nid] for nid in node_ids]

    max_in_degree = max(all_in_degrees) if all_in_degrees else 0
    max_out_degree = max(all_out_degrees) if all_out_degrees else 0
    average_in_degree = edge_count / node_count
    average_out_degree = edge_count / node_count

    # Top 20 lists
    top_20_in = sorted(
        [(nid, in_degrees[nid], node_dict[nid]["metadata"].get("canonical_grammar_key"), node_dict[nid].get("cefr_level")) for nid in node_ids],
        key=lambda x: x[1], reverse=True
    )[:20]

    top_20_out = sorted(
        [(nid, out_degrees[nid], node_dict[nid]["metadata"].get("canonical_grammar_key"), node_dict[nid].get("cefr_level")) for nid in node_ids],
        key=lambda x: x[1], reverse=True
    )[:20]

    # D. Dependency Class Coverage
    dep_class_counts = defaultdict(int)
    for edge in edges:
        dep_class = edge["metadata"].get("dependency_class")
        dep_class_counts[dep_class] += 1

    # E. Edge Type Coverage
    edge_type_counts = defaultdict(int)
    for edge in edges:
        edge_type_counts[edge["edge_type"]] += 1

    # F. Progression Coverage
    prog_band_counts = defaultdict(int)
    prog_stage_counts = defaultdict(int)
    prog_scores = []
    suspicious_score_monotonicity = []

    for edge in edges:
        meta = edge["metadata"]
        prog_band_counts[meta.get("progression_band")] += 1
        prog_stage_counts[meta.get("progression_stage")] += 1
        prog_scores.append(meta.get("progression_score"))

        # Monotonicity check: target score should be >= source score for prerequisite/unlocks
        if edge["edge_type"] in ("prerequisite", "unlocks"):
            src_node = node_dict[edge["source_node_id"]]
            tgt_node = node_dict[edge["target_node_id"]]
            src_score = meta.get("progression_score")
            # We also check if target score is defined in metadata
            # Wait, progression fields reside on the edge metadata representing the learning state progression step.
            # But wait! Do nodes themselves have progression score?
            # EGP nodes do not have progression scores in metadata, but edges do.
            # So progression score is of the dependency rule itself.
            # What is monotonicity of progression score?
            # Prerequisite node should have simpler progression, but wait:
            # Progression score represents where the target dependency connects in the progression structure.
            # If a rule has a score, does the source node represent a lower score generally?
            # EGP CEFR levels: A1 < A2 < B1. Let's check CEFR order!
            pass

    prog_score_min = min(prog_scores) if prog_scores else 0
    prog_score_max = max(prog_scores) if prog_scores else 0
    prog_score_median = sorted(prog_scores)[len(prog_scores)//2] if prog_scores else 0

    # G. CEFR Scope Coverage
    cefr_edge_counts = defaultdict(int)
    plus_level_nodes_in_edges = []
    
    for edge in edges:
        src_node = node_dict[edge["source_node_id"]]
        tgt_node = node_dict[edge["target_node_id"]]
        
        src_lvl = src_node.get("cefr_level")
        tgt_lvl = tgt_node.get("cefr_level")
        
        cefr_edge_counts[src_lvl] += 1
        cefr_edge_counts[tgt_lvl] += 1

        if "+" in str(src_lvl) or "plus" in str(src_lvl).lower():
            plus_level_nodes_in_edges.append(edge["source_node_id"])
        if "+" in str(tgt_lvl) or "plus" in str(tgt_lvl).lower():
            plus_level_nodes_in_edges.append(edge["target_node_id"])

    # H. Family Coverage
    family_nodes = defaultdict(set)
    family_edges = defaultdict(int)
    subtype_edges = defaultdict(int)

    for nid, n in node_dict.items():
        family = n["metadata"].get("grammar_family", "UNKNOWN")
        family_nodes[family].add(nid)

    for edge in edges:
        src_node = node_dict[edge["source_node_id"]]
        family = src_node["metadata"].get("grammar_family", "UNKNOWN")
        subtype = src_node["metadata"].get("grammar_subtype", "UNKNOWN")
        family_edges[family] += 1
        subtype_edges[subtype] += 1

    overrepresented_families = []
    underrepresented_families = []
    for fam, nids in family_nodes.items():
        ratio = family_edges[fam] / len(nids) if len(nids) > 0 else 0
        if ratio > 1.5:
            overrepresented_families.append((fam, len(nids), family_edges[fam]))
        elif ratio < 0.05:
            underrepresented_families.append((fam, len(nids), family_edges[fam]))

    # I. Directionality Heuristic Audit
    suspicious_backward_prerequisites = []
    self_loops_detected = []
    duplicate_edges_detected = defaultdict(int)

    for edge in edges:
        src = edge["source_node_id"]
        tgt = edge["target_node_id"]
        etype = edge["edge_type"]
        
        if src == tgt:
            self_loops_detected.append(edge["id"])
            
        edge_tuple = (src, tgt, etype)
        duplicate_edges_detected[edge_tuple] += 1

        if etype in ("prerequisite", "unlocks"):
            src_lvl = node_dict[src].get("cefr_level")
            tgt_lvl = node_dict[tgt].get("cefr_level")
            src_rank = get_cefr_rank(src_lvl)
            tgt_rank = get_cefr_rank(tgt_lvl)
            
            # Prerequisite target CEFR rank should be >= source CEFR rank
            # e.g. target is A2 (2), source is A1 (1) -> OK (2 >= 1)
            # If target rank < source rank (e.g. target A1 (1), source A2 (2)) -> suspicious!
            if tgt_rank < src_rank:
                suspicious_backward_prerequisites.append({
                    "edge_id": edge["id"],
                    "source_node_id": src,
                    "source_level": src_lvl,
                    "target_node_id": tgt,
                    "target_level": tgt_lvl,
                    "edge_type": etype
                })

    duplicates = {str(k): v for k, v in duplicate_edges_detected.items() if v > 1}

    # J. Hard DAG Audit
    # Verify prerequisite/unlocks subgraph is acyclic
    # We already have cycle checking in our validator. Let's do it here again.
    def check_has_cycle():
        adj = defaultdict(list)
        for edge in edges:
            if edge["edge_type"] in ("prerequisite", "unlocks"):
                adj[edge["source_node_id"]].append(edge["target_node_id"])
        
        visited = {}
        def dfs(node):
            visited[node] = 1
            for neighbor in adj[node]:
                if visited.get(neighbor) == 1:
                    return True
                elif visited.get(neighbor) != 2:
                    if dfs(neighbor):
                        return True
            visited[node] = 2
            return False
            
        for node in node_ids:
            if visited.get(node) != 2:
                if dfs(node):
                    return True
        return False

    has_cycle = check_has_cycle()
    longest_chain = find_longest_chain(node_ids, edges)

    # Root and Leaf nodes in hard DAG (among nodes that have at least one hard edge)
    hard_connected_nodes = set()
    for edge in edges:
        if edge["edge_type"] in ("prerequisite", "unlocks"):
            hard_connected_nodes.add(edge["source_node_id"])
            hard_connected_nodes.add(edge["target_node_id"])

    root_nodes = []
    leaf_nodes = []
    for nid in hard_connected_nodes:
        in_d = hard_in_degrees[nid]
        out_d = hard_out_degrees[nid]
        if in_d == 0:
            root_nodes.append((nid, node_dict[nid]["metadata"].get("canonical_grammar_key")))
        if out_d == 0:
            leaf_nodes.append((nid, node_dict[nid]["metadata"].get("canonical_grammar_key")))

    # K. Rule Quality Audit
    rule_edge_counts = defaultdict(int)
    for edge in edges:
        rule_edge_counts[edge["metadata"].get("rule_id")] += 1

    rules_producing_zero = []
    rules_producing_many = []
    rules_weak_evidence = []
    rules_only_cefr = []
    rules_high_confidence = []

    for rule in rules:
        r_id = rule["rule_id"]
        cnt = rule_edge_counts[r_id]
        if cnt == 0:
            rules_producing_zero.append(r_id)
        elif cnt > 5:
            rules_producing_many.append((r_id, cnt))

        # Check only cefr
        src_match = rule["source_match"]
        tgt_match = rule["target_match"]
        
        semantic_keys = {
            "canonical_grammar_key_contains", "label_contains",
            "grammar_family_contains", "grammar_subtype_contains",
            "guideword_contains", "can_do_statement_contains"
        }
        
        src_has_semantic = any(k in src_match for k in semantic_keys)
        tgt_has_semantic = any(k in tgt_match for k in semantic_keys)
        if not src_has_semantic or not tgt_has_semantic:
            rules_only_cefr.append(r_id)

        # High confidence
        if rule.get("confidence", 0) >= 1.0:
            rules_high_confidence.append(r_id)

    # L. Authority Safety Audit
    cefr_as_prerequisite_used = len(rules_only_cefr) > 0
    plus_levels_used = len(plus_level_nodes_in_edges) > 0
    all_rule_based = all(edge["authority_source"].get("derivation") == "rule_based" for edge in edges)
    all_cefr_not_order = all(edge["metadata"].get("cefr_is_not_order") is True for edge in edges)

    # Compile JSON report
    report = {
        "audit_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "basic_counts": {
            "node_count": node_count,
            "edge_count": edge_count,
            "enabled_rule_count": enabled_rule_count,
            "skipped_rule_count": skipped_rule_count,
            "edge_per_node_ratio": edge_count / node_count
        },
        "isolated_node_analysis": {
            "isolated_node_count": isolated_node_count,
            "isolated_node_ratio": isolated_node_ratio,
            "zero_in_degree_count": len(zero_in_degree),
            "zero_out_degree_count": len(zero_out_degree),
            "connected_node_count": connected_node_count,
            "connected_node_ratio": connected_node_ratio
        },
        "degree_distribution": {
            "max_in_degree": max_in_degree,
            "max_out_degree": max_out_degree,
            "average_in_degree": average_in_degree,
            "average_out_degree": average_out_degree,
            "top_20_in_degree_nodes": top_20_in,
            "top_20_out_degree_nodes": top_20_out
        },
        "dependency_class_coverage": dict(dep_class_counts),
        "edge_type_coverage": dict(edge_type_counts),
        "progression_coverage": {
            "progression_band": dict(prog_band_counts),
            "progression_stage": dict(prog_stage_counts),
            "progression_score_min": prog_score_min,
            "progression_score_max": prog_score_max,
            "progression_score_median": prog_score_median
        },
        "cefr_scope_coverage": {
            "edges_by_level": dict(cefr_edge_counts),
            "plus_level_misuse_nodes": plus_level_nodes_in_edges
        },
        "family_coverage": {
            "family_nodes_count": {fam: len(nids) for fam, nids in family_nodes.items()},
            "family_edges_count": dict(family_edges),
            "subtype_edges_count": dict(subtype_edges),
            "overrepresented_families": overrepresented_families,
            "underrepresented_families": underrepresented_families
        },
        "directionality_heuristic_audit": {
            "suspicious_backward_prerequisites": suspicious_backward_prerequisites,
            "self_loops_detected": self_loops_detected,
            "duplicate_edges_detected": duplicates
        },
        "hard_dag_audit": {
            "has_cycle": has_cycle,
            "longest_chain_length": longest_chain,
            "root_nodes_count": len(root_nodes),
            "leaf_nodes_count": len(leaf_nodes),
            "root_nodes_sample": root_nodes[:20],
            "leaf_nodes_sample": leaf_nodes[:20]
        },
        "rule_quality_audit": {
            "rules_producing_zero_edges": rules_producing_zero,
            "rules_producing_many_edges": rules_producing_many,
            "rules_only_cefr_match": rules_only_cefr,
            "rules_high_confidence": rules_high_confidence
        },
        "authority_safety_audit": {
            "cefr_used_as_only_match": cefr_as_prerequisite_used,
            "plus_levels_misused": plus_levels_used,
            "all_derivation_rule_based": all_rule_based,
            "all_cefr_is_not_order": all_cefr_not_order
        }
    }

    # Write report
    AUDIT_JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Audit report written to {AUDIT_JSON_OUT}")
    
    # Print high level statistics to stdout
    print("\n=== QA AUDIT METRICS SUMMARY ===")
    print(f"Nodes: {node_count} | Edges: {edge_count} | Edge/Node Ratio: {edge_count/node_count:.4f}")
    print(f"Isolated Nodes: {isolated_node_count} ({isolated_node_ratio*100:.2f}%)")
    print(f"DAG Cycle Detected: {has_cycle} | Longest Hard Chain: {longest_chain}")
    print(f"Suspicious Backward Prerequisites: {len(suspicious_backward_prerequisites)}")
    print(f"Self-Loops: {len(self_loops_detected)} | Duplicates: {len(duplicates)}")
    print(f"Rules producing 0 edges: {len(rules_producing_zero)} | Rules producing >5 edges: {len(rules_producing_many)}")
    print(f"CEFR Plus Level Misuse: {plus_levels_used} | CEFR Used as Order: {cefr_as_prerequisite_used}")

if __name__ == "__main__":
    run_audit()
