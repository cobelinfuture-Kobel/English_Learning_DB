import datetime
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
VOCAB_NODES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json"
VOCAB_SOURCE_PATH = BASE_DIR / "vocabulary" / "json" / "vocabulary.json"
THEME_CATALOG_PATH = BASE_DIR / "themes" / "theme_catalog.json"
THEME_VOCAB_MAPPING_PATH = BASE_DIR / "themes" / "theme_vocab_mapping.json"

THEME_NODES_OUT_PATH = BASE_DIR / "ulga" / "graph" / "theme_nodes.json"
RULES_OUT_PATH = BASE_DIR / "ulga" / "rules" / "vocabulary_theme_mapping_rules.json"
EDGES_OUT_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_theme_edges.json"
GRAPH_OUT_PATH = BASE_DIR / "ulga" / "graph" / "ulga_graph.vocabulary_theme_layer.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "vocabulary_theme_mapping_summary.json"
UNMAPPED_OUT_PATH = BASE_DIR / "ulga" / "reports" / "vocabulary_theme_unmapped_nodes.json"


TOPIC_NORMALIZATION = {
    "animal": "animals",
    "people-actions": "people: actions",
    "people-personality": "people: personality",
}


FALLBACK_TOPIC_RULES = {
    "animals": [
        ("a1_interests_and_abilities", "inferred", 0.4, 0.55, "Fallback maps animals topic to A1 interests and abilities."),
        ("a1_travel_and_weather", "inferred", 0.35, 0.5, "Fallback maps animals topic to natural-world adjacent A1 travel/weather."),
    ],
    "clothes": [
        ("a1_shopping_and_basic_transactions", "inferred", 0.4, 0.55, "Fallback maps clothes topic to A1 shopping."),
        ("a1_personal_information_and_greetings", "inferred", 0.35, 0.5, "Fallback maps clothes topic to appearance/social description."),
    ],
}


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def slug(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def normalize_topic(topic):
    if not topic:
        return None
    normalized = str(topic).strip().lower()
    return TOPIC_NORMALIZATION.get(normalized, normalized)


def build_theme_nodes(theme_catalog, timestamp):
    nodes = []
    for theme in theme_catalog["themes"]:
        theme_id = theme["theme_id"]
        nodes.append(
            {
                "id": f"theme:{theme_id}",
                "node_type": "theme",
                "label": theme["theme_name"],
                "authority_source": {
                    "source_name": "Theme Authority",
                    "source_file": "themes/theme_catalog.json",
                    "source_record_id": theme_id,
                    "source_row": None,
                    "derivation": "source_direct",
                },
                "cefr_level": theme.get("level"),
                "confidence": {
                    "value": 1.0,
                    "method": "theme_catalog_authority",
                    "notes": ["Mounted from theme catalog without modifying source data."],
                },
                "version": {
                    "contract": "ULGA-S2",
                    "source_version": "1.0.0",
                    "generated_at": timestamp,
                },
                "metadata": {
                    "theme_id": theme_id,
                    "theme_name": theme["theme_name"],
                    "parent_theme": theme.get("parent_theme"),
                    "level_scope": theme.get("level"),
                    "progression_stage": theme.get("progression_stage"),
                    "description": theme.get("description"),
                    "active_vocabulary_count": theme.get("active_vocabulary_count"),
                    "mounting_stage": "ULGA-S5E",
                },
            }
        )
    return nodes


def build_mapping_rules(theme_vocab_mapping, theme_by_id):
    rules = []
    seen = set()

    def add_rule(source_topic, target_theme_id, membership_type, weight, confidence, rationale, mapping_source):
        normalized_topic = normalize_topic(source_topic)
        rule_tuple = (normalized_topic, target_theme_id, membership_type)
        if rule_tuple in seen:
            return
        seen.add(rule_tuple)
        theme = theme_by_id[target_theme_id]
        rule_id = f"VOCAB_THEME_RULE_{len(rules) + 1:04d}"
        rules.append(
            {
                "rule_id": rule_id,
                "source_topic": normalized_topic,
                "raw_source_topic": source_topic,
                "target_theme_id": target_theme_id,
                "target_theme_label": theme["theme_name"],
                "membership_type": membership_type,
                "weight": weight,
                "confidence": confidence,
                "confidence_method": "source_topic_mapping" if membership_type in {"primary", "secondary"} else "inferred_rule",
                "mapping_source": mapping_source,
                "rationale": rationale,
                "enabled": True,
            }
        )

    for theme in theme_vocab_mapping["themes"]:
        theme_id = theme["theme_id"]
        for topic in theme.get("primary_topics", []):
            add_rule(
                topic,
                theme_id,
                "primary",
                1.0,
                0.9,
                f"Primary topic '{topic}' belongs to theme '{theme_id}'.",
                "themes/theme_vocab_mapping.json",
            )
        for topic in theme.get("secondary_topics", []):
            add_rule(
                topic,
                theme_id,
                "secondary",
                0.65,
                0.75,
                f"Secondary topic '{topic}' supports theme '{theme_id}'.",
                "themes/theme_vocab_mapping.json",
            )

    for topic, targets in FALLBACK_TOPIC_RULES.items():
        for theme_id, membership_type, weight, confidence, rationale in targets:
            add_rule(topic, theme_id, membership_type, weight, confidence, rationale, "fallback_topic_normalization_rules")

    return rules


def build_edges(vocab_nodes, vocab_source, theme_nodes, rules, timestamp):
    vocab_source_by_id = {record["vocab_id"]: record for record in vocab_source}
    theme_node_by_theme_id = {node["metadata"]["theme_id"]: node for node in theme_nodes}
    rules_by_topic = defaultdict(list)
    for rule in rules:
        if rule.get("enabled", True):
            rules_by_topic[rule["source_topic"]].append(rule)

    edges = []
    seen_edges = set()
    mapped_vocab_ids = set()
    unmapped = []
    mapping_source_breakdown = Counter()
    membership_breakdown = Counter()
    theme_edge_breakdown = Counter()

    for vocab_node in vocab_nodes:
        source_vocabulary_id = vocab_node["metadata"]["source_vocabulary_id"]
        source_record = vocab_source_by_id.get(source_vocabulary_id)
        raw_topic = source_record.get("topic") if source_record else None
        normalized_topic = normalize_topic(raw_topic)
        matching_rules = rules_by_topic.get(normalized_topic, [])

        if not matching_rules:
            unmapped.append(
                {
                    "vocabulary_node_id": vocab_node["id"],
                    "source_vocabulary_id": source_vocabulary_id,
                    "canonical_lemma": vocab_node["metadata"].get("canonical_lemma"),
                    "cefr_level": vocab_node.get("cefr_level"),
                    "source_topic": raw_topic,
                    "normalized_topic": normalized_topic,
                    "reason": "missing_source_topic" if not normalized_topic else "no_theme_mapping_rule",
                }
            )
            continue

        mapped_vocab_ids.add(vocab_node["id"])
        for rule in matching_rules:
            theme_node = theme_node_by_theme_id[rule["target_theme_id"]]
            edge_tuple = (vocab_node["id"], theme_node["id"], "belongs_to")
            if edge_tuple in seen_edges:
                continue
            seen_edges.add(edge_tuple)
            edge_id = f"edge:vocab_theme_{rule['rule_id']}_{slug(source_vocabulary_id)}_{slug(rule['target_theme_id'])}"
            edge = {
                "id": edge_id,
                "source_node_id": vocab_node["id"],
                "target_node_id": theme_node["id"],
                "edge_type": "belongs_to",
                "authority_source": {
                    "source_name": "Vocabulary Theme Authority",
                    "source_file": rule["mapping_source"],
                    "source_record_id": rule["rule_id"],
                    "derivation": "rule_based",
                },
                "confidence": {
                    "value": rule["confidence"],
                    "method": rule["confidence_method"],
                    "notes": [rule["rationale"]],
                },
                "version": {
                    "contract": "ULGA-S2",
                    "source_version": "1.0.0",
                    "generated_at": timestamp,
                },
                "metadata": {
                    "source_vocabulary_id": source_vocabulary_id,
                    "canonical_lemma": vocab_node["metadata"].get("canonical_lemma"),
                    "source_topic": raw_topic,
                    "normalized_source_topic": normalized_topic,
                    "target_theme_id": rule["target_theme_id"],
                    "target_theme_label": rule["target_theme_label"],
                    "membership_type": rule["membership_type"],
                    "weight": rule["weight"],
                    "sense_specific": True,
                    "lemma_level_assignment": False,
                    "rule_id": rule["rule_id"],
                    "mapping_source": rule["mapping_source"],
                    "mounting_stage": "ULGA-S5E",
                    "rule_based": True,
                    "blocked_topic_checked": True,
                    "morphology_layer_implemented": False,
                    "chunk_layer_implemented": False,
                    "vocabulary_dependency_layer_implemented": False,
                },
            }
            edges.append(edge)
            mapping_source_breakdown[rule["mapping_source"]] += 1
            membership_breakdown[rule["membership_type"]] += 1
            theme_edge_breakdown[rule["target_theme_id"]] += 1

    return edges, unmapped, mapped_vocab_ids, mapping_source_breakdown, membership_breakdown, theme_edge_breakdown


def main():
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    vocab_nodes = read_json(VOCAB_NODES_PATH)
    vocab_source = read_json(VOCAB_SOURCE_PATH)
    theme_catalog = read_json(THEME_CATALOG_PATH)
    theme_vocab_mapping = read_json(THEME_VOCAB_MAPPING_PATH)

    theme_nodes = build_theme_nodes(theme_catalog, timestamp)
    theme_by_id = {theme["theme_id"]: theme for theme in theme_catalog["themes"]}
    rules = build_mapping_rules(theme_vocab_mapping, theme_by_id)
    edges, unmapped, mapped_vocab_ids, mapping_source_breakdown, membership_breakdown, theme_edge_breakdown = build_edges(
        vocab_nodes,
        vocab_source,
        theme_nodes,
        rules,
        timestamp,
    )

    graph = {
        "graph_id": "ulga_graph.vocabulary_theme_layer",
        "contract_version": "ULGA-S2",
        "schema_version": "1.0.0",
        "formal_data_mounted": True,
        "mounted_stage": "ULGA-S5E",
        "nodes": vocab_nodes + theme_nodes,
        "edges": edges,
        "vocabulary_node_count": len(vocab_nodes),
        "theme_node_count": len(theme_nodes),
        "theme_edge_count": len(edges),
        "mapped_vocabulary_count": len(mapped_vocab_ids),
        "unmapped_vocabulary_count": len(unmapped),
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
            "purpose": "Vocabulary Theme Layer",
            "data_policy": "sense_specific_vocabulary_theme_membership",
            "generated_at": timestamp,
        },
    }

    summary = {
        "generated_at": timestamp,
        "vocabulary_node_count": len(vocab_nodes),
        "theme_node_count": len(theme_nodes),
        "theme_edge_count": len(edges),
        "mapped_vocabulary_count": len(mapped_vocab_ids),
        "unmapped_vocabulary_count": len(unmapped),
        "mapping_rule_count": len(rules),
        "mapping_source_breakdown": dict(mapping_source_breakdown),
        "membership_type_breakdown": dict(membership_breakdown),
        "theme_coverage_breakdown": dict(theme_edge_breakdown),
        "sense_specific_theme_assignment": True,
        "lemma_level_theme_assignment": False,
        "morphology_layer_implemented": False,
        "chunk_layer_implemented": False,
        "vocabulary_dependency_layer_implemented": False,
    }

    write_json(THEME_NODES_OUT_PATH, theme_nodes)
    write_json(RULES_OUT_PATH, rules)
    write_json(EDGES_OUT_PATH, edges)
    write_json(GRAPH_OUT_PATH, graph)
    write_json(SUMMARY_OUT_PATH, summary)
    write_json(UNMAPPED_OUT_PATH, unmapped)

    print(f"Loaded {len(vocab_nodes)} vocabulary nodes.")
    print(f"Generated {len(theme_nodes)} theme nodes.")
    print(f"Generated {len(rules)} mapping rules.")
    print(f"Generated {len(edges)} vocabulary-theme edges.")
    print(f"Mapped vocabulary nodes: {len(mapped_vocab_ids)}")
    print(f"Unmapped vocabulary nodes: {len(unmapped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
