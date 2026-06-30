import datetime
import json
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
CORE_EDGES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_dependency_core_edges.json"
RULES_PATH = BASE_DIR / "ulga" / "rules" / "grammar_dependency_extended_rules.json"

EXTENDED_EDGES_OUT_PATH = BASE_DIR / "ulga" / "graph" / "grammar_dependency_extended_edges.json"
ALL_EDGES_OUT_PATH = BASE_DIR / "ulga" / "graph" / "grammar_dependency_all_edges.json"
GRAPH_OUT_PATH = BASE_DIR / "ulga" / "graph" / "ulga_graph.grammar_extended_dependencies.json"
SKIPPED_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_dependency_extended_skipped_rules.json"
SUMMARY_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_dependency_extended_summary.json"


SEMANTIC_KEYS = {
    "canonical_grammar_key_contains",
    "label_contains",
    "grammar_family_contains",
    "grammar_subtype_contains",
    "guideword_contains",
    "can_do_statement_contains",
}


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def node_matches(node, match_dict):
    if not match_dict:
        return False
    metadata = node.get("metadata", {})
    if not any(key in match_dict for key in SEMANTIC_KEYS):
        return False

    for key, value in match_dict.items():
        if key == "canonical_grammar_key_contains":
            node_value = metadata.get("canonical_grammar_key", "")
            if value.lower() not in node_value.lower():
                return False
        elif key == "label_contains":
            node_value = node.get("label", "")
            if value.lower() not in node_value.lower():
                return False
        elif key == "grammar_family_contains":
            node_value = metadata.get("grammar_family", "")
            if value.lower() not in node_value.lower():
                return False
        elif key == "grammar_subtype_contains":
            node_value = metadata.get("grammar_subtype", "")
            if value.lower() not in node_value.lower():
                return False
        elif key == "guideword_contains":
            node_value = metadata.get("guideword", "")
            if value.lower() not in node_value.lower():
                return False
        elif key == "can_do_statement_contains":
            node_value = metadata.get("can_do_statement", "")
            if value.lower() not in node_value.lower():
                return False
        elif key == "cefr_level_in":
            if node.get("cefr_level") not in value:
                return False
        else:
            node_value = node.get(key) or metadata.get(key)
            if node_value != value:
                return False
    return True


def evidence(node):
    metadata = node.get("metadata", {})
    return {
        "id": node["id"],
        "canonical_grammar_key": metadata.get("canonical_grammar_key"),
        "grammar_family": metadata.get("grammar_family"),
        "grammar_subtype": metadata.get("grammar_subtype"),
        "guideword": metadata.get("guideword"),
        "cefr_level": node.get("cefr_level"),
    }


def build_extended_dependencies():
    nodes = read_json(NODES_PATH)
    core_edges = read_json(CORE_EDGES_PATH)
    rules = read_json(RULES_PATH)

    seen_tuples = {(edge["source_node_id"], edge["target_node_id"], edge["edge_type"]) for edge in core_edges}
    extended_edges = []
    skipped_rules = []
    dependency_class_breakdown = defaultdict(int)
    progression_band_breakdown = defaultdict(int)
    cefr_scope_breakdown = defaultdict(int)
    layer_breakdown = defaultdict(int)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    for rule in rules:
        if not rule.get("enabled", True):
            continue

        rule_id = rule["rule_id"]
        sources = [node for node in nodes if node_matches(node, rule["source_match"])]
        targets = [node for node in nodes if node_matches(node, rule["target_match"])]

        produced = 0
        skip_reasons = []
        if not sources:
            skip_reasons.append("source_match_empty")
        if not targets:
            skip_reasons.append("target_match_empty")

        for source in sources:
            for target in targets:
                if source["id"] == target["id"]:
                    skip_reasons.append("self_loop")
                    continue
                edge_tuple = (source["id"], target["id"], rule["edge_type"])
                if edge_tuple in seen_tuples:
                    skip_reasons.append("duplicate_edge_tuple")
                    continue
                seen_tuples.add(edge_tuple)

                source_short = source["id"].replace("grammar:GRAMMAR_NODE_", "")
                target_short = target["id"].replace("grammar:GRAMMAR_NODE_", "")
                edge = {
                    "id": f"edge:grammar_ext_dep_{rule_id}_{source_short}_{target_short}",
                    "source_node_id": source["id"],
                    "target_node_id": target["id"],
                    "edge_type": rule["edge_type"],
                    "authority_source": {
                        "source_name": "ULGA-S4E_ExtendedGrammarDependencyAuthority_Implementation_Fix",
                        "source_file": "ulga/rules/grammar_dependency_extended_rules.json",
                        "source_record_id": rule_id,
                        "derivation": "rule_based",
                    },
                    "confidence": {
                        "value": rule["confidence"],
                        "method": "rule_based",
                        "notes": [f"Generated from extended dependency rule {rule_id}: {rule['rule_name']}"],
                    },
                    "version": {
                        "contract": "ULGA-S2",
                        "source_version": "1.0.0",
                        "generated_at": timestamp,
                    },
                    "metadata": {
                        "rule_id": rule_id,
                        "layer": rule["layer"],
                        "rule_name": rule["rule_name"],
                        "dependency_class": rule["dependency_class"],
                        "progression_band": rule["progression_band"],
                        "progression_stage": rule["progression_stage"],
                        "progression_score": rule["progression_score"],
                        "cefr_scope": rule["cefr_scope"],
                        "rationale": rule["rationale"],
                        "source_match": rule["source_match"],
                        "target_match": rule["target_match"],
                        "source_match_evidence": evidence(source),
                        "target_match_evidence": evidence(target),
                        "mounting_stage": "ULGA-S4E",
                        "rule_based": True,
                        "cefr_is_not_order": True,
                        "advanced_layer": False,
                    },
                }
                extended_edges.append(edge)
                produced += 1
                dependency_class_breakdown[rule["dependency_class"]] += 1
                progression_band_breakdown[rule["progression_band"]] += 1
                cefr_scope_breakdown[rule["cefr_scope"]] += 1
                layer_breakdown[rule["layer"]] += 1

        if produced == 0:
            skipped_rules.append(
                {
                    "rule_id": rule_id,
                    "rule_name": rule["rule_name"],
                    "layer": rule["layer"],
                    "source_match": rule["source_match"],
                    "target_match": rule["target_match"],
                    "source_match_count": len(sources),
                    "target_match_count": len(targets),
                    "skip_reasons": sorted(set(skip_reasons)),
                    "rationale": rule.get("rationale", ""),
                }
            )

    all_edges = core_edges + extended_edges
    graph_data = {
        "graph_id": "ulga_graph.grammar_extended_dependencies",
        "contract_version": "ULGA-S2",
        "schema_version": "1.0.0",
        "formal_data_mounted": True,
        "mounted_stage": "ULGA-S4E",
        "nodes": nodes,
        "edges": all_edges,
        "node_count": len(nodes),
        "core_edge_count": len(core_edges),
        "extended_edge_count": len(extended_edges),
        "total_edge_count": len(all_edges),
        "implemented_layers": ["core", "extended_core", "bridge"],
        "advanced_layer_implemented": False,
        "plus_levels_used_as_cefr": False,
        "validation_status": "untested",
        "metadata": {
            "purpose": "Extended Grammar Dependency Authority Layer A/B",
            "data_policy": "grammar_dependency_extended_layer",
            "dependency_scope": "core_plus_extended_core_plus_bridge",
            "cefr_levels_targeted": ["A1", "A2", "B1", "B2"],
            "plus_levels_used_as_cefr": False,
            "advanced_layer_implemented": False,
            "generated_at": timestamp,
        },
    }
    summary = {
        "generated_at": timestamp,
        "source_nodes_count": len(nodes),
        "core_edge_count": len(core_edges),
        "enabled_rules_count": sum(1 for rule in rules if rule.get("enabled", True)),
        "enabled_rules_by_layer": {
            "extended_core": sum(1 for rule in rules if rule.get("enabled", True) and rule.get("layer") == "extended_core"),
            "bridge": sum(1 for rule in rules if rule.get("enabled", True) and rule.get("layer") == "bridge"),
        },
        "skipped_rules_count": len(skipped_rules),
        "extended_edge_count": len(extended_edges),
        "total_edge_count": len(all_edges),
        "dependency_class_breakdown": dict(dependency_class_breakdown),
        "progression_band_breakdown": dict(progression_band_breakdown),
        "cefr_scope_breakdown": dict(cefr_scope_breakdown),
        "layer_breakdown": dict(layer_breakdown),
        "implemented_layers": ["core", "extended_core", "bridge"],
        "advanced_layer_implemented": False,
        "plus_levels_used_as_cefr": False,
    }

    write_json(EXTENDED_EDGES_OUT_PATH, extended_edges)
    write_json(ALL_EDGES_OUT_PATH, all_edges)
    write_json(GRAPH_OUT_PATH, graph_data)
    write_json(SKIPPED_REPORT_PATH, skipped_rules)
    write_json(SUMMARY_REPORT_PATH, summary)

    print(f"Loaded {len(nodes)} grammar nodes.")
    print(f"Loaded {len(core_edges)} core edges.")
    print(f"Loaded {len(rules)} extended rules.")
    print(f"Generated {len(extended_edges)} extended edges.")
    print(f"Skipped {len(skipped_rules)} rules.")
    print(f"Wrote all-edge graph with {len(all_edges)} total edges.")


def main():
    build_extended_dependencies()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
