import json
import os
import sys
import re
from pathlib import Path
from collections import defaultdict

# Setup base directories
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

VOCAB_NODES_PATH = BASE_DIR / "graph" / "vocabulary_nodes.json"
RULES_PATH = BASE_DIR / "rules" / "vocabulary_morphology_rules.json"

OUTPUT_EDGES_PATH = BASE_DIR / "graph" / "vocabulary_morphology_edges.json"
OUTPUT_GRAPH_PATH = BASE_DIR / "graph" / "ulga_graph.vocabulary_morphology_layer.json"
OUTPUT_SUMMARY_PATH = BASE_DIR / "reports" / "vocabulary_morphology_summary.json"
OUTPUT_SKIPPED_PATH = BASE_DIR / "reports" / "vocabulary_morphology_skipped_candidates.json"

def match_suffix(base, derived, suffix):
    base = base.lower()
    derived = derived.lower()
    suffix = suffix.lower()
    if len(derived) <= len(base):
        return False
    
    # 1. Standard suffixing
    if base + suffix == derived:
        return True
    
    # 2. Silent e deletion (e.g. write + er -> writer)
    if base.endswith('e') and base[:-1] + suffix == derived:
        return True
    
    # 3. Y to I conversion (e.g. happy + ness -> happiness)
    if base.endswith('y') and base[:-1] + 'i' + suffix == derived:
        return True
    
    # 4. Consonant doubling (e.g. run + er -> runner)
    if len(base) >= 3:
        last_char = base[-1]
        if last_char in "bcdfgklmnprstvz" and base[-2] not in "aeiouy" and base[-3] in "aeiouy":
            if base + last_char + suffix == derived:
                return True
                
    return False

def match_prefix(base, derived, prefix):
    base = base.lower()
    derived = derived.lower()
    prefix = prefix.lower()
    if len(derived) <= len(prefix):
        return False
    return prefix + base == derived

def main():
    print("Starting Vocabulary Morphology Layer Edge Builder...")
    
    # 1. Load Rules
    if not RULES_PATH.exists():
        print(f"Error: Rules file not found at {RULES_PATH}")
        sys.exit(1)
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        rules = json.load(f)
    rules_map = {r["rule_id"]: r for r in rules}
    print(f"Loaded {len(rules)} morphology rules.")

    # 2. Load Vocabulary Nodes
    if not VOCAB_NODES_PATH.exists():
        print(f"Error: Vocabulary nodes not found at {VOCAB_NODES_PATH}")
        sys.exit(1)
    with open(VOCAB_NODES_PATH, "r", encoding="utf-8") as f:
        nodes = json.load(f)
    print(f"Loaded {len(nodes)} vocabulary nodes.")

    # Group nodes by lowercase lemma and construct lemma index
    lemma_to_nodes = defaultdict(list)
    for n in nodes:
        lemma = n["metadata"].get("canonical_lemma", n["label"]).lower()
        lemma_to_nodes[lemma].append(n)
        
    all_lemmas = set(lemma_to_nodes.keys())
    
    generated_edges = []
    skipped_candidates = []
    seen_edge_tuples = set() # (source_id, target_id, edge_type)
    
    # Helper function to add edge
    def add_edge(src_node, tgt_node, rule_id, relation_type):
        if src_node["id"] == tgt_node["id"]:
            return False # no self-loop
            
        edge_tuple = (src_node["id"], tgt_node["id"], "supports")
        if edge_tuple in seen_edge_tuples:
            return False # no duplicates
            
        rule = rules_map[rule_id]
        
        # Calculate inflection promotion metadata
        tgt_lemma = tgt_node["metadata"].get("canonical_lemma", tgt_node["label"]).lower()
        tgt_pos = tgt_node["metadata"].get("part_of_speech", "")
        is_inflection_promoted = tgt_lemma.endswith(('ing', 'ed', 's')) and tgt_pos in ('noun', 'adjective')
        
        edge_id = f"edge:vocab_morph_{rule_id}_{src_node['metadata']['source_vocabulary_id']}_{tgt_node['metadata']['source_vocabulary_id']}"
        
        edge = {
            "id": edge_id,
            "source_node_id": src_node["id"],
            "target_node_id": tgt_node["id"],
            "edge_type": "supports",
            "authority_source": {
                "source_name": "Vocabulary Morphology Authority",
                "derivation": "rule_based"
            },
            "confidence": {
                "value": rule["confidence"],
                "method": "rule_based"
            },
            "version": {
                "contract": "ULGA-S2"
            },
            "metadata": {
                "source_vocabulary_id": src_node["metadata"]["source_vocabulary_id"],
                "target_vocabulary_id": tgt_node["metadata"]["source_vocabulary_id"],
                "source_lemma": src_node["metadata"].get("canonical_lemma", src_node["label"]),
                "target_lemma": tgt_node["metadata"].get("canonical_lemma", tgt_node["label"]),
                "source_pos": src_node["metadata"].get("part_of_speech", ""),
                "target_pos": tgt_node["metadata"].get("part_of_speech", ""),
                "source_cefr": src_node.get("cefr_level"),
                "target_cefr": tgt_node.get("cefr_level"),
                "relation_family": "morphology",
                "morphology_relation": relation_type,
                "rule_id": rule_id,
                "rule_type": rule["rule_type"],
                "confidence_method": "rule_based",
                "sense_specific": True,
                "word_family_hub_used": False,
                "morphology_node_created": False,
                "mounting_stage": "ULGA-S5I",
                "inflection_promoted_to_lexical_node": is_inflection_promoted
            }
        }
        generated_edges.append(edge)
        seen_edge_tuples.add(edge_tuple)
        return True

    # 3. Explicit Target Word Family Resolver (Play, Teach, Happy, Act, Possible, Help, Move, Use)
    explicit_derivations = [
        # play family
        ("play", "player", "MORPH_RULE_001_AGENT_NOUN", "derived_from"),
        ("play", "playground", "MORPH_RULE_020_COMPOUND", "compound_of"),
        ("play", "playful", "MORPH_RULE_014_ADJ_FUL", "has_suffix"),
        # teach family
        ("teach", "teacher", "MORPH_RULE_001_AGENT_NOUN", "derived_from"),
        ("teach", "teaching", "MORPH_RULE_011_NOUN_TION", "has_suffix"),
        # happy family
        ("happy", "unhappy", "MORPH_RULE_002_NEG_PREFIX_UN", "has_prefix"),
        ("happy", "happily", "MORPH_RULE_019_ADV_LY", "has_suffix"),
        ("happy", "happiness", "MORPH_RULE_010_NOUN_NESS", "has_suffix"),
        ("unhappy", "unhappily", "MORPH_RULE_019_ADV_LY", "has_suffix"),
        ("unhappy", "unhappiness", "MORPH_RULE_010_NOUN_NESS", "has_suffix"),
        ("happily", "unhappily", "MORPH_RULE_002_NEG_PREFIX_UN", "has_prefix"),
        # act family
        ("act", "actor", "MORPH_RULE_001_AGENT_NOUN", "derived_from"),
        ("act", "action", "MORPH_RULE_011_NOUN_TION", "has_suffix"),
        ("act", "active", "MORPH_RULE_016_ADJ_IVE", "has_suffix"),
        ("active", "actively", "MORPH_RULE_019_ADV_LY", "has_suffix"),
        ("active", "activity", "MORPH_RULE_013_NOUN_ITY", "has_suffix"),
        ("active", "activate", "MORPH_RULE_021_SHARED_ROOT", "shares_root"),
        ("activate", "activation", "MORPH_RULE_011_NOUN_TION", "has_suffix"),
        ("act", "actual", "MORPH_RULE_021_SHARED_ROOT", "shares_root"),
        ("actual", "actually", "MORPH_RULE_019_ADV_LY", "has_suffix"),
        ("act", "react", "MORPH_RULE_008_PREFIX_RE", "has_prefix"),
        ("react", "reaction", "MORPH_RULE_011_NOUN_TION", "has_suffix"),
        ("act", "interact", "MORPH_RULE_021_SHARED_ROOT", "shares_root"),
        ("interact", "interaction", "MORPH_RULE_011_NOUN_TION", "has_suffix"),
        ("interact", "interactive", "MORPH_RULE_016_ADJ_IVE", "has_suffix"),
        ("act", "transaction", "MORPH_RULE_021_SHARED_ROOT", "shares_root"),
        # possible family
        ("possible", "possibly", "MORPH_RULE_019_ADV_LY", "has_suffix"),
        ("possible", "impossible", "MORPH_RULE_003_NEG_PREFIX_IM", "has_prefix"),
        ("possible", "possibility", "MORPH_RULE_013_NOUN_ITY", "has_suffix"),
        ("impossible", "impossibly", "MORPH_RULE_019_ADV_LY", "has_suffix"),
        ("impossible", "impossibility", "MORPH_RULE_013_NOUN_ITY", "has_suffix"),
        # help family
        ("help", "helper", "MORPH_RULE_001_AGENT_NOUN", "derived_from"),
        ("help", "helpful", "MORPH_RULE_014_ADJ_FUL", "has_suffix"),
        ("helpful", "unhelpful", "MORPH_RULE_002_NEG_PREFIX_UN", "has_prefix"),
        ("help", "helpless", "MORPH_RULE_015_ADJ_LESS", "has_suffix"),
        ("helpless", "helplessness", "MORPH_RULE_010_NOUN_NESS", "has_suffix"),
        # move family
        ("move", "movement", "MORPH_RULE_012_NOUN_MENT", "has_suffix"),
        ("move", "moving", "MORPH_RULE_021_SHARED_ROOT", "shares_root"),
        ("move", "remove", "MORPH_RULE_008_PREFIX_RE", "has_prefix"),
        ("remove", "removal", "MORPH_RULE_011_NOUN_TION", "has_suffix"),
        # use family
        ("use", "user", "MORPH_RULE_001_AGENT_NOUN", "derived_from"),
        ("use", "useful", "MORPH_RULE_014_ADJ_FUL", "has_suffix"),
        ("useful", "usefulness", "MORPH_RULE_010_NOUN_NESS", "has_suffix"),
        ("use", "useless", "MORPH_RULE_015_ADJ_LESS", "has_suffix"),
        ("useless", "uselessness", "MORPH_RULE_010_NOUN_NESS", "has_suffix"),
        ("use", "usage", "MORPH_RULE_021_SHARED_ROOT", "shares_root"),
        ("use", "misuse", "MORPH_RULE_009_PREFIX_MIS", "has_prefix"),
        ("use", "reuse", "MORPH_RULE_008_PREFIX_RE", "has_prefix"),
        ("reuse", "reusable", "MORPH_RULE_018_ADJ_ABLE", "has_suffix"),
    ]

    for src_l, tgt_l, rule_id, relation_type in explicit_derivations:
        if src_l in lemma_to_nodes and tgt_l in lemma_to_nodes:
            for src_n in lemma_to_nodes[src_l]:
                for tgt_n in lemma_to_nodes[tgt_l]:
                    add_edge(src_n, tgt_n, rule_id, relation_type)

    # Explicit Shared Roots
    shared_root_groups = [
        # act family
        ["action", "active", "actor", "activity", "actual", "react", "interact", "transaction"],
        # move family
        ["movement", "remove", "removal"]
    ]
    for group in shared_root_groups:
        for idx in range(len(group) - 1):
            l1 = group[idx]
            l2 = group[idx + 1]
            if l1 in lemma_to_nodes and l2 in lemma_to_nodes:
                for n1 in lemma_to_nodes[l1]:
                    for n2 in lemma_to_nodes[l2]:
                        add_edge(n1, n2, "MORPH_RULE_021_SHARED_ROOT", "shares_root")

    # 4. Systematic Rule-Based Heuristic Matcher
    # Suffixes
    suffixes_rules = [
        ("er", "MORPH_RULE_001_AGENT_NOUN", "derived_from"),
        ("or", "MORPH_RULE_001_AGENT_NOUN", "derived_from"),
        ("ness", "MORPH_RULE_010_NOUN_NESS", "has_suffix"),
        ("tion", "MORPH_RULE_011_NOUN_TION", "has_suffix"),
        ("sion", "MORPH_RULE_011_NOUN_TION", "has_suffix"),
        ("ation", "MORPH_RULE_011_NOUN_TION", "has_suffix"),
        ("ment", "MORPH_RULE_012_NOUN_MENT", "has_suffix"),
        ("ity", "MORPH_RULE_013_NOUN_ITY", "has_suffix"),
        ("ful", "MORPH_RULE_014_ADJ_FUL", "has_suffix"),
        ("less", "MORPH_RULE_015_ADJ_LESS", "has_suffix"),
        ("ive", "MORPH_RULE_016_ADJ_IVE", "has_suffix"),
        ("ous", "MORPH_RULE_017_ADJ_OUS", "has_suffix"),
        ("able", "MORPH_RULE_018_ADJ_ABLE", "has_suffix"),
        ("ible", "MORPH_RULE_018_ADJ_ABLE", "has_suffix"),
        ("ly", "MORPH_RULE_019_ADV_LY", "has_suffix"),
    ]

    # Prefixes
    prefixes_rules = [
        ("un", "MORPH_RULE_002_NEG_PREFIX_UN", "has_prefix"),
        ("im", "MORPH_RULE_003_NEG_PREFIX_IM", "has_prefix"),
        ("in", "MORPH_RULE_004_NEG_PREFIX_IN", "has_prefix"),
        ("ir", "MORPH_RULE_005_NEG_PREFIX_IR", "has_prefix"),
        ("il", "MORPH_RULE_006_NEG_PREFIX_IL", "has_prefix"),
        ("dis", "MORPH_RULE_007_PREFIX_DIS", "has_prefix"),
        ("re", "MORPH_RULE_008_PREFIX_RE", "has_prefix"),
        ("mis", "MORPH_RULE_009_PREFIX_MIS", "has_prefix"),
    ]

    for lemma in all_lemmas:
        # Suffix Check
        for suffix, rule_id, rel_type in suffixes_rules:
            if lemma.endswith(suffix) and len(lemma) > len(suffix) + 2:
                # Find candidate base word
                for base in all_lemmas:
                    if len(base) < len(lemma) and match_suffix(base, lemma, suffix):
                        for src_n in lemma_to_nodes[base]:
                            for tgt_n in lemma_to_nodes[lemma]:
                                add_edge(src_n, tgt_n, rule_id, rel_type)

        # Prefix Check
        for prefix, rule_id, rel_type in prefixes_rules:
            if lemma.startswith(prefix) and len(lemma) > len(prefix) + 2:
                for base in all_lemmas:
                    if len(base) < len(lemma) and match_prefix(base, lemma, prefix):
                        for src_n in lemma_to_nodes[base]:
                            for tgt_n in lemma_to_nodes[lemma]:
                                add_edge(src_n, tgt_n, rule_id, rel_type)

        # Compound Check (e.g. classroom -> class + room)
        if len(lemma) >= 6:
            for i in range(3, len(lemma) - 2):
                left = lemma[:i]
                right = lemma[i:]
                if left in all_lemmas and right in all_lemmas:
                    for left_n in lemma_to_nodes[left]:
                        for tgt_n in lemma_to_nodes[lemma]:
                            add_edge(left_n, tgt_n, "MORPH_RULE_020_COMPOUND", "compound_of")
                    for right_n in lemma_to_nodes[right]:
                        for tgt_n in lemma_to_nodes[lemma]:
                            add_edge(right_n, tgt_n, "MORPH_RULE_020_COMPOUND", "compound_of")

    # 5. Skipped Candidates Tagger
    # Any pair where one starts with the other but it doesn't match rules is logged.
    for base in sorted(list(all_lemmas)):
        if len(base) >= 4:
            for derived in all_lemmas:
                if derived != base and derived.startswith(base) and len(derived) > len(base) + 2:
                    # check if connected
                    connected = False
                    for base_n in lemma_to_nodes[base]:
                        for der_n in lemma_to_nodes[derived]:
                            if (base_n["id"], der_n["id"], "supports") in seen_edge_tuples:
                                connected = True
                                break
                    if not connected:
                        skipped_candidates.append({
                            "source_lemma": base,
                            "target_lemma": derived,
                            "reason": "Prefix match found but no morphological rule matched suffix requirements."
                        })

    # 6. Save Edges JSON
    with open(OUTPUT_EDGES_PATH, "w", encoding="utf-8") as f:
        json.dump(generated_edges, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(generated_edges)} edges to {OUTPUT_EDGES_PATH}.")

    # 7. Save Graph JSON Wrapper
    graph_wrapper = {
        "graph_id": "ulga_graph.vocabulary_morphology_layer",
        "contract_version": "ULGA-S2",
        "schema_version": "1.0.0",
        "formal_data_mounted": True,
        "mounted_stage": "ULGA-S5I",
        "nodes": nodes,
        "edges": generated_edges,
        "metadata": {
            "purpose": "Vocabulary Morphology Layer",
            "data_policy": "vocabulary_to_vocabulary_morphology_only",
            "vocabulary_node_count": len(nodes),
            "morphology_edge_count": len(generated_edges),
            "morphology_node_count": 0,
            "word_family_hub_node_count": 0,
            "relation_family": "morphology",
            "morphology_nodes_created": False,
            "word_family_hubs_created": False,
            "mounted_stage": "ULGA-S5I"
        },
        "validation_status": "untested"
    }
    with open(OUTPUT_GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(graph_wrapper, f, indent=2, ensure_ascii=False)
    print(f"Saved graph wrapper to {OUTPUT_GRAPH_PATH}.")

    # 8. Save Reports
    relation_counts = defaultdict(int)
    confidence_counts = defaultdict(int)
    for e in generated_edges:
        relation_counts[e["metadata"]["morphology_relation"]] += 1
        confidence_counts[str(e["confidence"]["value"])] += 1

    summary = {
        "mounting_stage": "ULGA-S5I",
        "vocabulary_node_count": len(nodes),
        "morphology_edge_count": len(generated_edges),
        "morphology_node_count_created": 0,
        "word_family_hub_count_created": 0,
        "relation_breakdown": dict(relation_counts),
        "confidence_breakdown": dict(confidence_counts),
        "skipped_candidates_count": len(skipped_candidates)
    }
    with open(OUTPUT_SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved summary report to {OUTPUT_SUMMARY_PATH}.")

    with open(OUTPUT_SKIPPED_PATH, "w", encoding="utf-8") as f:
        json.dump(skipped_candidates[:200], f, indent=2, ensure_ascii=False) # cap report
    print(f"Saved skipped candidates to {OUTPUT_SKIPPED_PATH}.")

if __name__ == "__main__":
    main()
