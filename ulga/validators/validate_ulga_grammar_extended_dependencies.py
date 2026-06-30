import json
import sys
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_ulga_grammar_core_dependencies import find_cycles
from ulga.validators.validate_ulga_schema import ValidationError, require, validate_edge


NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
CORE_EDGES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_dependency_core_edges.json"
EXTENDED_RULES_PATH = BASE_DIR / "ulga" / "rules" / "grammar_dependency_extended_rules.json"
EXTENDED_EDGES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_dependency_extended_edges.json"
ALL_EDGES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_dependency_all_edges.json"
GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "ulga_graph.grammar_extended_dependencies.json"
SKIPPED_PATH = BASE_DIR / "ulga" / "reports" / "grammar_dependency_extended_skipped_rules.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_dependency_extended_summary.json"

LAYER_C_FORBIDDEN_FAMILIES = {"FOCUS", "DISCOURSE MARKERS"}
LAYER_C_FORBIDDEN_TERMS = {
    "inversion",
    "cleft",
    "nominalisation",
    "nominalization",
    "subjunctive",
    "hedging",
    "advanced reporting",
    "advanced discourse",
    "discourse marker",
}


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def node_text(node):
    metadata = node.get("metadata", {})
    return " ".join(
        str(value or "")
        for value in [
            node.get("label"),
            metadata.get("canonical_grammar_key"),
            metadata.get("grammar_family"),
            metadata.get("grammar_subtype"),
            metadata.get("guideword"),
            metadata.get("can_do_statement"),
        ]
    ).lower()


def is_layer_c_node(node):
    family = node.get("metadata", {}).get("grammar_family")
    text = node_text(node)
    return family in LAYER_C_FORBIDDEN_FAMILIES or any(term in text for term in LAYER_C_FORBIDDEN_TERMS)


def validate_rules(rules):
    enabled = [rule for rule in rules if rule.get("enabled", True)]
    layer_a = [rule for rule in enabled if rule.get("layer") == "extended_core"]
    layer_b = [rule for rule in enabled if rule.get("layer") == "bridge"]
    require(200 <= len(layer_a) <= 250, f"Layer A enabled rules must be 200-250, got {len(layer_a)}")
    require(80 <= len(layer_b) <= 100, f"Layer B enabled rules must be 80-100, got {len(layer_b)}")
    require(280 <= len(enabled) <= 350, f"Total enabled rules must be 280-350, got {len(enabled)}")

    required = {
        "rule_id",
        "layer",
        "rule_name",
        "source_match",
        "target_match",
        "edge_type",
        "dependency_class",
        "confidence",
        "progression_band",
        "progression_stage",
        "progression_score",
        "cefr_scope",
        "rationale",
        "enabled",
    }
    semantic_keys = {
        "canonical_grammar_key_contains",
        "label_contains",
        "grammar_family_contains",
        "grammar_subtype_contains",
        "guideword_contains",
        "can_do_statement_contains",
    }
    for rule in enabled:
        require(required.issubset(rule), f"rule missing required fields: {rule.get('rule_id')}")
        require(rule["layer"] in {"extended_core", "bridge"}, f"invalid layer: {rule['rule_id']}")
        require(any(key in rule["source_match"] for key in semantic_keys), f"source match only uses CEFR: {rule['rule_id']}")
        require(any(key in rule["target_match"] for key in semantic_keys), f"target match only uses CEFR: {rule['rule_id']}")
        for side in ["source_match", "target_match"]:
            for level in rule[side].get("cefr_level_in", []):
                require("+" not in level, f"plus level used in rule {rule['rule_id']}: {level}")
        require(rule["confidence"] < 1.0, f"rule confidence must be < 1.0: {rule['rule_id']}")


def validate_extended_dependencies():
    for path in [
        NODES_PATH,
        CORE_EDGES_PATH,
        EXTENDED_RULES_PATH,
        EXTENDED_EDGES_PATH,
        ALL_EDGES_PATH,
        GRAPH_PATH,
        SKIPPED_PATH,
        SUMMARY_PATH,
    ]:
        require(path.exists(), f"File does not exist: {path}")

    nodes = read_json(NODES_PATH)
    core_edges = read_json(CORE_EDGES_PATH)
    rules = read_json(EXTENDED_RULES_PATH)
    extended_edges = read_json(EXTENDED_EDGES_PATH)
    all_edges = read_json(ALL_EDGES_PATH)
    graph = read_json(GRAPH_PATH)
    skipped = read_json(SKIPPED_PATH)
    summary = read_json(SUMMARY_PATH)

    validate_rules(rules)

    node_by_id = {node["id"]: node for node in nodes}
    node_ids = set(node_by_id)
    require(len(extended_edges) > 0, "extended_edge_count must be greater than 0")
    require(len(all_edges) == len(core_edges) + len(extended_edges), "all_edges must equal core + extended")
    require(len(all_edges) > len(core_edges), "total_edge_count must be greater than core_edge_count")

    seen = set()
    for edge in all_edges:
        validate_edge(edge, node_ids=node_ids)
        require(edge["source_node_id"].startswith("grammar:"), f"source is not grammar: {edge['id']}")
        require(edge["target_node_id"].startswith("grammar:"), f"target is not grammar: {edge['id']}")
        require(node_by_id[edge["source_node_id"]]["node_type"] == "grammar", f"source node is not grammar: {edge['id']}")
        require(node_by_id[edge["target_node_id"]]["node_type"] == "grammar", f"target node is not grammar: {edge['id']}")
        require(edge["source_node_id"] != edge["target_node_id"], f"self-loop detected: {edge['id']}")
        edge_tuple = (edge["source_node_id"], edge["target_node_id"], edge["edge_type"])
        require(edge_tuple not in seen, f"duplicate edge tuple: {edge_tuple}")
        seen.add(edge_tuple)

    for edge in extended_edges:
        confidence = edge["confidence"]
        metadata = edge["metadata"]
        require(confidence["value"] < 1.0, f"confidence must be < 1.0: {edge['id']}")
        require(confidence["method"] == "rule_based", f"confidence method must be rule_based: {edge['id']}")
        require(metadata.get("cefr_is_not_order") is True, f"cefr_is_not_order must be true: {edge['id']}")
        require(metadata.get("advanced_layer") is False, f"advanced_layer must be false: {edge['id']}")
        require(metadata.get("mounting_stage") == "ULGA-S4E", f"mounting_stage must be ULGA-S4E: {edge['id']}")
        require(metadata.get("rule_based") is True, f"rule_based must be true: {edge['id']}")
        for key in [
            "rule_id",
            "layer",
            "rule_name",
            "dependency_class",
            "progression_band",
            "progression_stage",
            "progression_score",
            "cefr_scope",
            "rationale",
            "source_match_evidence",
            "target_match_evidence",
        ]:
            require(key in metadata, f"metadata.{key} missing: {edge['id']}")
        require(metadata["layer"] in {"extended_core", "bridge"}, f"invalid layer: {edge['id']}")
        source = node_by_id[edge["source_node_id"]]
        target = node_by_id[edge["target_node_id"]]
        require("+" not in str(source.get("cefr_level")), f"plus-level source CEFR: {edge['id']}")
        require("+" not in str(target.get("cefr_level")), f"plus-level target CEFR: {edge['id']}")
        require(not is_layer_c_node(source), f"Layer C forbidden source implemented: {edge['id']}")
        require(not is_layer_c_node(target), f"Layer C forbidden target implemented: {edge['id']}")

    for node in graph.get("nodes", []):
        require(node["node_type"] == "grammar", f"non-grammar node mounted: {node['id']}")
        require("+" not in str(node.get("cefr_level")), f"plus-level CEFR mounted: {node['id']}")

    require(graph.get("formal_data_mounted") is True, "graph formal_data_mounted must be true")
    require(graph.get("mounted_stage") == "ULGA-S4E", "graph mounted_stage must be ULGA-S4E")
    require(graph.get("node_count") == len(nodes) == 1222, "graph node_count mismatch")
    require(graph.get("core_edge_count") == len(core_edges), "graph core_edge_count mismatch")
    require(graph.get("extended_edge_count") == len(extended_edges), "graph extended_edge_count mismatch")
    require(graph.get("total_edge_count") == len(all_edges), "graph total_edge_count mismatch")
    require(graph.get("implemented_layers") == ["core", "extended_core", "bridge"], "implemented_layers mismatch")
    require(graph.get("advanced_layer_implemented") is False, "advanced_layer_implemented must be false")
    require(graph.get("plus_levels_used_as_cefr") is False, "plus_levels_used_as_cefr must be false")

    require(summary["extended_edge_count"] == len(extended_edges), "summary extended edge count mismatch")
    require(summary["total_edge_count"] == len(all_edges), "summary total edge count mismatch")
    require(summary["skipped_rules_count"] == len(skipped), "summary skipped rule count mismatch")

    cycle = find_cycles(node_ids, all_edges)
    if cycle is not None:
        raise ValidationError(f"Cycle detected in prerequisite/unlocks graph: {' -> '.join(cycle)}")

    print(
        "Validation: SUCCESS. "
        f"Verified {len(extended_edges)} extended edges, {len(all_edges)} total edges, and DAG status."
    )


def main():
    try:
        validate_extended_dependencies()
    except Exception as exc:
        import traceback

        traceback.print_exc()
        print(f"ULGA extended grammar dependencies validation: FAIL - {exc}")
        return 1
    print("ULGA extended grammar dependencies validation: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
