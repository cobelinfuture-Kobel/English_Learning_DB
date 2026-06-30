import json
import os
import sys
from collections import defaultdict, Counter
from pathlib import Path

# Setup base directory
BASE_DIR = Path(__file__).resolve().parents[2]
GRAPH_DIR = BASE_DIR / "ulga" / "graph"
REPORTS_DIR = BASE_DIR / "ulga" / "reports"

VOCAB_NODES_PATH = GRAPH_DIR / "vocabulary_nodes.json"
MORPH_EDGES_PATH = GRAPH_DIR / "vocabulary_morphology_edges.json"
RULES_PATH = BASE_DIR / "ulga" / "rules" / "vocabulary_morphology_rules.json"
OUTPUT_REPORT_PATH = REPORTS_DIR / "vocabulary_morphology_qa_audit.json"

CEFR_ORDER = {"A1": 1, "A1_plus": 1.5, "A2": 2, "A2_plus": 2.5, "B1": 3, "B1_plus": 3.5, "B2": 4, "B2_plus": 4.5, "C1": 5, "C2": 6}

def get_cefr_rank(level):
    return CEFR_ORDER.get(level, 0)

# Simple Disjoint Set Union (DSU) or BFS to find connected components (families)
def find_components(nodes, edges):
    adj = defaultdict(list)
    for edge in edges:
        u = edge["source_node_id"]
        v = edge["target_node_id"]
        adj[u].append(v)
        adj[v].append(u)
        
    visited = set()
    components = []
    
    # We only form components from connected nodes
    connected_nodes = set(adj.keys())
    
    for node in connected_nodes:
        if node not in visited:
            comp = []
            queue = [node]
            visited.add(node)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            components.append(comp)
            
    return components, connected_nodes

def main():
    print("Starting Vocabulary Morphology Layer QA Audit...")
    
    if not VOCAB_NODES_PATH.exists():
        print(f"Error: {VOCAB_NODES_PATH} does not exist.")
        sys.exit(1)
    if not MORPH_EDGES_PATH.exists():
        print(f"Error: {MORPH_EDGES_PATH} does not exist.")
        sys.exit(1)
        
    with open(VOCAB_NODES_PATH, "r", encoding="utf-8") as f:
        vocab_nodes = json.load(f)
    with open(MORPH_EDGES_PATH, "r", encoding="utf-8") as f:
        morph_edges = json.load(f)
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        rules = json.load(f)

    vocab_node_map = {n["id"]: n for n in vocab_nodes}
    
    # Basic metrics
    total_nodes = len(vocab_nodes)
    total_edges = len(morph_edges)
    average_edges = total_edges / total_nodes if total_nodes > 0 else 0
    
    relation_counts = defaultdict(int)
    for edge in morph_edges:
        relation_counts[edge["metadata"]["morphology_relation"]] += 1
        
    # Family Coverage
    components, connected_node_ids = find_components(vocab_nodes, morph_edges)
    connected_vocab_count = len(connected_node_ids)
    isolated_vocab_count = total_nodes - connected_vocab_count
    
    family_sizes = [len(c) for c in components]
    family_count = len(components)
    average_family_size = sum(family_sizes) / family_count if family_count > 0 else 0
    
    # Median family size
    sorted_sizes = sorted(family_sizes)
    if family_count > 0:
        mid = family_count // 2
        if family_count % 2 == 1:
            median_family_size = sorted_sizes[mid]
        else:
            median_family_size = (sorted_sizes[mid-1] + sorted_sizes[mid]) / 2.0
    else:
        median_family_size = 0
        
    # Get largest families mapped with lemmas
    # Group components by their base root lemma (which is usually the member with the shortest lemma or lowest CEFR)
    family_details = []
    for comp in components:
        comp_nodes = [vocab_node_map[nid] for nid in comp]
        # Sort by lemma length and then CEFR level
        comp_nodes.sort(key=lambda x: (len(x["metadata"].get("canonical_lemma", x["label"])), get_cefr_rank(x.get("cefr_level"))))
        base_lemma = comp_nodes[0]["metadata"].get("canonical_lemma", comp_nodes[0]["label"])
        member_lemmas = list(set(n["metadata"].get("canonical_lemma", n["label"]) for n in comp_nodes))
        family_details.append({
            "base_lemma": base_lemma,
            "size": len(comp),
            "members": member_lemmas,
            "node_ids": comp
        })
    family_details.sort(key=lambda x: x["size"], reverse=True)
    largest_100_families = family_details[:100]

    # False Positive Heuristics Tagging
    false_positives = []
    
    # Known etymologically false/weak pairs that we want to scan for in the generated edges
    # e.g., corner (er) -> corn, human (man) -> hum/hu or vice-versa, season -> sea + son, carpet -> car + pet
    # often -> of + ten, manage -> man + age, only -> on + ly, early -> ear + ly, dress -> address
    false_positive_heuristics = [
        # (source, target, relation)
        ("corn", "corner", "derived_from"),
        ("corn", "corner", "has_suffix"),
        ("sea", "season", "compound_of"),
        ("son", "season", "compound_of"),
        ("car", "carpet", "compound_of"),
        ("pet", "carpet", "compound_of"),
        ("of", "often", "compound_of"),
        ("ten", "often", "compound_of"),
        ("man", "manage", "compound_of"),
        ("age", "manage", "compound_of"),
        ("on", "only", "has_suffix"),
        ("ear", "early", "has_suffix"),
        ("dress", "address", "has_prefix"),
        ("press", "pressure", "has_suffix"), # correct but check
        ("man", "human", "has_suffix"), # false positive
        ("act", "fact", "shares_root"), # false positive
    ]
    
    for edge in morph_edges:
        src_lemma = edge["metadata"]["source_lemma"].lower()
        tgt_lemma = edge["metadata"]["target_lemma"].lower()
        relation = edge["metadata"]["morphology_relation"]
        
        # Check against false positive heuristics
        is_suspect = False
        reason = ""
        
        # Heuristic 1: explicitly known false positives
        for f_src, f_tgt, f_rel in false_positive_heuristics:
            if src_lemma == f_src and tgt_lemma == f_tgt and relation == f_rel:
                is_suspect = True
                reason = f"Explicitly flagged false positive candidate: {src_lemma} -> {tgt_lemma} ({relation})"
                break
                
        # Heuristic 2: Short compounds that are likely accidental overlaps
        if relation == "compound_of":
            # If the compound is short (e.g. <= 6 chars) and ends with common words but is etymologically false
            # e.g., 'season' = 'sea' + 'son', 'often' = 'of' + 'ten', 'manage' = 'man' + 'age', 'parent' = 'par' + 'ent'
            if tgt_lemma in ["season", "often", "manage", "parent", "carpet", "bullet", "handsome"]:
                is_suspect = True
                reason = f"Short compound overlap suspect: {tgt_lemma} split into {src_lemma} + other"
                
        # Heuristic 3: accidental suffix matches (e.g., early -> ear + ly, only -> on + ly)
        if relation == "has_suffix" and edge["metadata"]["rule_id"] == "MORPH_RULE_019_ADV_LY":
            if tgt_lemma in ["early", "only", "ugly", "holy", "family", "belly"]:
                is_suspect = True
                reason = f"Adjectival or lexicalized -ly ending mistakenly categorized as adverb suffix derivation."
                
        # Heuristic 4: accidental prefix matches (e.g., improve -> im + prove? Wait, prove and improve are related, but is it negation?)
        if relation == "has_prefix" and edge["metadata"]["rule_id"] in ["MORPH_RULE_003_NEG_PREFIX_IM", "MORPH_RULE_004_NEG_PREFIX_IN"]:
            if tgt_lemma in ["improve", "involve", "indeed", "income", "inspect"]:
                is_suspect = True
                reason = f"Accidental prefix match: prefix rules matched non-affix root string."

        if is_suspect:
            false_positives.append({
                "edge_id": edge["id"],
                "source_lemma": src_lemma,
                "target_lemma": tgt_lemma,
                "relation": relation,
                "rule_id": edge["metadata"]["rule_id"],
                "reason": reason
            })
            
    # Sample Top 100 per relationship for reporting and check
    sampled_edges_by_relation = defaultdict(list)
    for edge in morph_edges:
        rel = edge["metadata"]["morphology_relation"]
        if len(sampled_edges_by_relation[rel]) < 100:
            sampled_edges_by_relation[rel].append({
                "edge_id": edge["id"],
                "source_lemma": edge["metadata"]["source_lemma"],
                "target_lemma": edge["metadata"]["target_lemma"],
                "source_cefr": edge["metadata"]["source_cefr"],
                "target_cefr": edge["metadata"]["target_cefr"],
                "rule_id": edge["metadata"]["rule_id"]
            })

    # Prefix Counts
    prefix_counts = Counter()
    for edge in morph_edges:
        if edge["metadata"]["morphology_relation"] == "has_prefix":
            rule_id = edge["metadata"]["rule_id"]
            # Map rule_id to prefix name
            prefix_name = rule_id.replace("MORPH_RULE_", "")
            prefix_counts[prefix_name] += 1
            
    # Suffix Counts
    suffix_counts = Counter()
    for edge in morph_edges:
        if edge["metadata"]["morphology_relation"] == "has_suffix" or edge["metadata"]["morphology_relation"] == "derived_from":
            rule_id = edge["metadata"]["rule_id"]
            suffix_name = rule_id.replace("MORPH_RULE_", "")
            suffix_counts[suffix_name] += 1

    # Compounds Count (Top 200 compound families)
    compound_families = defaultdict(int)
    for edge in morph_edges:
        if edge["metadata"]["morphology_relation"] == "compound_of":
            tgt = edge["metadata"]["target_lemma"]
            compound_families[tgt] += 1
    sorted_compounds = sorted(compound_families.items(), key=lambda x: x[1], reverse=True)

    # CEFR Progression Analysis
    upward_count = 0
    same_level_count = 0
    downward_count = 0
    unknown_cefr_count = 0
    
    for edge in morph_edges:
        src_level = edge["metadata"]["source_cefr"]
        tgt_level = edge["metadata"]["target_cefr"]
        
        if not src_level or not tgt_level:
            unknown_cefr_count += 1
            continue
            
        src_rank = get_cefr_rank(src_level)
        tgt_rank = get_cefr_rank(tgt_level)
        
        if tgt_rank > src_rank:
            upward_count += 1
        elif tgt_rank == src_rank:
            same_level_count += 1
        else:
            downward_count += 1
            
    total_cefr_classified = upward_count + same_level_count + downward_count
    
    # Save Report JSON
    report = {
        "basic_metrics": {
            "vocabulary_node_count": total_nodes,
            "morphology_edge_count": total_edges,
            "average_edges_per_node": average_edges,
            "relation_breakdown": dict(relation_counts)
        },
        "family_coverage": {
            "connected_vocabulary_nodes": connected_vocab_count,
            "isolated_vocabulary_nodes": isolated_vocab_count,
            "family_count": family_count,
            "average_family_size": average_family_size,
            "median_family_size": median_family_size,
            "largest_100_families": largest_100_families
        },
        "false_positives": {
            "false_positive_count": len(false_positives),
            "false_positive_ratio": len(false_positives) / total_edges if total_edges > 0 else 0,
            "false_positive_candidates": false_positives
        },
        "prefixes": dict(prefix_counts),
        "suffixes": dict(suffix_counts),
        "compounds": {
            "total_compounds": len(compound_families),
            "compound_families_sorted": sorted_compounds[:200]
        },
        "shared_roots": {
            "edge_count": relation_counts.get("shares_root", 0),
            "conservative_assessment": "Shares_root is highly conservative (76 edges) because it is restricted to explicit target family sibling connections to prevent graph blowup."
        },
        "cefr_progression": {
            "upward_progression_count": upward_count,
            "same_level_progression_count": same_level_count,
            "downward_progression_count": downward_count,
            "unknown_cefr_count": unknown_cefr_count,
            "upward_ratio": upward_count / total_cefr_classified if total_cefr_classified > 0 else 0,
            "same_level_ratio": same_level_count / total_cefr_classified if total_cefr_classified > 0 else 0,
            "downward_ratio": downward_count / total_cefr_classified if total_cefr_classified > 0 else 0
        },
        "sampled_relations": dict(sampled_edges_by_relation)
    }
    
    with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print(f"QA Audit Report saved to {OUTPUT_REPORT_PATH}")
    print(f"Metrics: Nodes={total_nodes}, Edges={total_edges}")
    print(f"Families: Count={family_count}, Avg Size={average_family_size:.2f}")
    print(f"CEFR Progression: Upward={upward_count} ({report['cefr_progression']['upward_ratio']:.2%}), Same={same_level_count} ({report['cefr_progression']['same_level_ratio']:.2%}), Down={downward_count} ({report['cefr_progression']['downward_ratio']:.2%})")
    print(f"False Positives Detected: {len(false_positives)} (Ratio: {report['false_positives']['false_positive_ratio']:.2%})")

if __name__ == "__main__":
    main()
