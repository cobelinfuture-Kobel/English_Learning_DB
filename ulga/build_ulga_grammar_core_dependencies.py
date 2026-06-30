import json
import datetime
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[1]
NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
RULES_PATH = BASE_DIR / "ulga" / "rules" / "grammar_dependency_core_rules.json"

EDGES_OUT_PATH = BASE_DIR / "ulga" / "graph" / "grammar_dependency_core_edges.json"
GRAPH_OUT_PATH = BASE_DIR / "ulga" / "graph" / "ulga_graph.grammar_core_dependencies.json"
SKIPPED_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_dependency_core_skipped_rules.json"
SUMMARY_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_dependency_core_summary.json"

def node_matches(node, match_dict):
    if not match_dict:
        return False
    metadata = node.get("metadata", {})
    
    # Check if there is at least one semantic field query
    semantic_keys = {
        "canonical_grammar_key_contains", "label_contains",
        "grammar_family_contains", "grammar_subtype_contains",
        "guideword_contains", "can_do_statement_contains"
    }
    has_semantic = any(k in match_dict for k in semantic_keys)
    if not has_semantic:
        # Require at least one semantic field query (cannot only query cefr_level_in)
        return False

    for k, val in match_dict.items():
        if k == "canonical_grammar_key_contains":
            node_val = metadata.get("canonical_grammar_key", "")
            if val.lower() not in node_val.lower():
                return False
        elif k == "label_contains":
            node_val = node.get("label", "")
            if val.lower() not in node_val.lower():
                return False
        elif k == "grammar_family_contains":
            node_val = metadata.get("grammar_family", "")
            if val.lower() not in node_val.lower():
                return False
        elif k == "grammar_subtype_contains":
            node_val = metadata.get("grammar_subtype", "")
            if val.lower() not in node_val.lower():
                return False
        elif k == "guideword_contains":
            node_val = metadata.get("guideword", "")
            if val.lower() not in node_val.lower():
                return False
        elif k == "can_do_statement_contains":
            node_val = metadata.get("can_do_statement", "")
            if val.lower() not in node_val.lower():
                return False
        elif k == "cefr_level_in":
            node_val = node.get("cefr_level")
            if node_val not in val:
                return False
        else:
            # Exact match fallback for other metadata/node properties
            node_val = node.get(k) or metadata.get(k)
            if node_val != val:
                return False
    return True

def main():
    # 1. Load files
    if not NODES_PATH.exists():
        raise FileNotFoundError(f"Grammar nodes file not found at {NODES_PATH}")
    if not RULES_PATH.exists():
        raise FileNotFoundError(f"Grammar dependency core rules not found at {RULES_PATH}")

    with open(NODES_PATH, "r", encoding="utf-8") as f:
        nodes = json.load(f)

    with open(RULES_PATH, "r", encoding="utf-8") as f:
        rules = json.load(f)

    print(f"Loaded {len(nodes)} grammar nodes.")
    print(f"Loaded {len(rules)} dependency rules.")

    # 2. Build edges
    edges = []
    skipped_rules = []
    
    # For duplicate checking
    seen_tuples = set()
    
    # For breakdown statistics
    dep_class_breakdown = defaultdict(int)
    prog_band_breakdown = defaultdict(int)
    cefr_scope_breakdown = defaultdict(int)

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    for rule in rules:
        if not rule.get("enabled", True):
            continue

        rule_id = rule["rule_id"]
        rule_name = rule["rule_name"]
        source_match = rule["source_match"]
        target_match = rule["target_match"]
        edge_type = rule["edge_type"]
        dep_class = rule["dependency_class"]

        # Find matching nodes
        sources = [n for n in nodes if node_matches(n, source_match)]
        targets = [n for n in nodes if node_matches(n, target_match)]

        if not sources or not targets:
            skipped_rules.append({
                "rule_id": rule_id,
                "rule_name": rule_name,
                "source_match": source_match,
                "target_match": target_match,
                "source_match_count": len(sources),
                "target_match_count": len(targets),
                "rationale": rule.get("rationale", "")
            })
            continue

        # Connect sources to targets
        for s in sources:
            for t in targets:
                s_id = s["id"]
                t_id = t["id"]

                # Prevent self-loop
                if s_id == t_id:
                    continue

                # Prevent duplicate edge tuples (source, target, type)
                edge_tuple = (s_id, t_id, edge_type)
                if edge_tuple in seen_tuples:
                    continue
                seen_tuples.add(edge_tuple)

                # Format edge ID
                s_short = s_id.replace("grammar:GRAMMAR_NODE_", "")
                t_short = t_id.replace("grammar:GRAMMAR_NODE_", "")
                edge_id = f"edge:grammar_dep_{rule_id}_{s_short}_{t_short}"

                # Gather evidence from matching fields
                source_evidence = {
                    "id": s_id,
                    "canonical_grammar_key": s["metadata"].get("canonical_grammar_key"),
                    "guideword": s["metadata"].get("guideword"),
                    "cefr_level": s.get("cefr_level")
                }
                target_evidence = {
                    "id": t_id,
                    "canonical_grammar_key": t["metadata"].get("canonical_grammar_key"),
                    "guideword": t["metadata"].get("guideword"),
                    "cefr_level": t.get("cefr_level")
                }

                # Construct edge conformant to schema
                edge = {
                    "id": edge_id,
                    "source_node_id": s_id,
                    "target_node_id": t_id,
                    "edge_type": edge_type,
                    "authority_source": {
                        "source_name": "ULGA-S4B_GrammarDependencyCoreLayer_Fix",
                        "source_file": "ulga/rules/grammar_dependency_core_rules.json",
                        "source_record_id": rule_id,
                        "derivation": "rule_based"
                    },
                    "confidence": {
                        "value": rule["confidence"],
                        "method": "rule_based",
                        "notes": [f"Generated from dependency rule {rule_id}: {rule_name}"]
                    },
                    "version": {
                        "contract": "ULGA-S2",
                        "source_version": "1.0.0",
                        "generated_at": timestamp
                    },
                    "metadata": {
                        "rule_id": rule_id,
                        "rule_name": rule_name,
                        "dependency_class": dep_class,
                        "progression_band": rule["progression_band"],
                        "progression_stage": rule["progression_stage"],
                        "progression_score": rule["progression_score"],
                        "cefr_scope": rule["cefr_scope"],
                        "rationale": rule["rationale"],
                        "source_match": source_match,
                        "target_match": target_match,
                        "source_match_evidence": source_evidence,
                        "target_match_evidence": target_evidence,
                        "mounting_stage": "ULGA-S4B",
                        "rule_based": True,
                        "cefr_is_not_order": True
                    }
                }
                edges.append(edge)
                dep_class_breakdown[dep_class] += 1
                prog_band_breakdown[rule["progression_band"]] += 1
                cefr_scope_breakdown[rule["cefr_scope"]] += 1

    print(f"Generated {len(edges)} unique edges.")
    print(f"Skipped {len(skipped_rules)} rules.")

    # 3. Write outputs
    # Write grammar_dependency_core_edges.json
    EDGES_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EDGES_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(edges, f, indent=2, ensure_ascii=False)
    print(f"Wrote edges to {EDGES_OUT_PATH}")

    # Write ulga_graph.grammar_core_dependencies.json
    # Read properties from ulga_graph.grammar_nodes.json to maintain consistency
    graph_data = {
        "graph_id": "ulga_graph.grammar_core_dependencies",
        "contract_version": "ULGA-S2",
        "schema_version": "1.0.0",
        "formal_data_mounted": True,
        "mounted_stage": "ULGA-S4B",
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "validation_status": "untested",
        "metadata": {
            "purpose": "Core Grammar Dependency Layer",
            "data_policy": "core_layer",
            "dependency_scope": "core_layer",
            "cefr_levels_targeted": ["A1", "A2", "B1"],
            "plus_levels_used_as_cefr": False,
            "generated_at": timestamp
        }
    }
    with open(GRAPH_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    print(f"Wrote full graph to {GRAPH_OUT_PATH}")

    # Write skipped rules report
    SKIPPED_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SKIPPED_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(skipped_rules, f, indent=2, ensure_ascii=False)
    print(f"Wrote skipped rules report to {SKIPPED_REPORT_PATH}")

    # Write summary report
    summary = {
        "generated_at": timestamp,
        "source_nodes_count": len(nodes),
        "enabled_rules_count": sum(1 for r in rules if r.get("enabled", True)),
        "skipped_rules_count": len(skipped_rules),
        "edge_count": len(edges),
        "dependency_class_breakdown": dict(dep_class_breakdown),
        "progression_band_breakdown": dict(prog_band_breakdown),
        "cefr_scope_breakdown": dict(cefr_scope_breakdown)
    }
    with open(SUMMARY_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Wrote summary report to {SUMMARY_REPORT_PATH}")

if __name__ == "__main__":
    main()
