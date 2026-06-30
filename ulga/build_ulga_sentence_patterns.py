import json
import re
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter, defaultdict

# Setup base directory
BASE_DIR = Path(__file__).resolve().parent.parent

CHUNK_METADATA_PATH = BASE_DIR / "ulga" / "graph" / "chunk_grammar_metadata.json"
RULES_PATH = BASE_DIR / "ulga" / "rules" / "chunk_grammar_metadata_rules.json"
GRAMMAR_NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
CHUNK_NODES_PATH = BASE_DIR / "ulga" / "graph" / "chunk_nodes.json"
THEME_NODES_PATH = BASE_DIR / "ulga" / "graph" / "theme_nodes.json"

# Outputs
NODES_OUT_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"
EDGES_OUT_PATH = BASE_DIR / "ulga" / "graph" / "ulga_sentence_pattern_edges.json"
GRAPH_OUT_PATH = BASE_DIR / "ulga" / "graph" / "ulga_sentence_pattern_nodes.json"
GRAPH_COMPILER_OUT_PATH = BASE_DIR / "ulga" / "graph" / "ulga_graph.sentence_patterns.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "sentence_pattern_mount_summary.json"

def load_json(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def normalize_slot_type(slot_label):
    if slot_label == "sb":
        return "noun_phrase"
    if slot_label == "sth":
        return "noun_phrase"
    if slot_label == "gerund":
        return "verb_gerund"
    if slot_label == "infinitive":
        return "verb_infinitive"
    if slot_label == "verb_stem":
        return "verb_stem"
    if slot_label == "name":
        return "proper_noun"
    return slot_label

def has_malformed_placeholders(pattern_text):
    if not isinstance(pattern_text, str):
        return True
    if "{}" in pattern_text or "{{" in pattern_text or "}}" in pattern_text:
        return True
    return pattern_text.count("{") != pattern_text.count("}")

def extract_slots_from_pattern(pattern_text, cefr_level):
    if has_malformed_placeholders(pattern_text):
        return []

    placeholders = re.findall(r"\{([^{}]+)\}", pattern_text)
    slots = []
    for idx, p in enumerate(placeholders):
        slot_label = p.strip()
        if not slot_label:
            continue

        slot_id = f"SLOT_{idx+1:02d}"
        slot_types = [normalize_slot_type(part.strip()) for part in slot_label.split("/") if part.strip()]
        is_multi_type = len(slot_types) > 1

        slot = {
            "slot_id": slot_id,
            "slot_label": slot_label,
            "slot_type": "multi_type" if is_multi_type else slot_types[0],
            "required": True,
            "constraints": {
                "cefr_max": cefr_level if cefr_level else "C2",
                "theme_prefilter": [],
                "number": "singular_or_plural"
            }
        }
        if is_multi_type:
            slot["allowed_slot_types"] = slot_types

        slots.append(slot)
    return slots

def main():
    print("Starting Sentence Pattern Authority compilation...")
    
    # 1. Load data
    chunk_metadata = load_json(CHUNK_METADATA_PATH)
    metadata_rules = load_json(RULES_PATH)
    grammar_nodes = load_json(GRAMMAR_NODES_PATH)
    chunk_nodes = load_json(CHUNK_NODES_PATH)
    theme_nodes = load_json(THEME_NODES_PATH)
    
    print(f"Loaded {len(chunk_metadata)} chunk metadata records.")
    print(f"Loaded {len(metadata_rules)} chunk grammar rules.")
    print(f"Loaded {len(grammar_nodes)} grammar nodes.")
    print(f"Loaded {len(chunk_nodes)} chunk nodes.")
    print(f"Loaded {len(theme_nodes)} theme nodes.")
    
    valid_grammar_ids = {n["id"] for n in grammar_nodes}
    valid_chunk_ids = {n["id"] for n in chunk_nodes}
    valid_theme_ids = {n["id"] for n in theme_nodes}
    
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # 2. Define Manual A1 Core Patterns
    manual_a1_defs = [
        # Identity / Personal
        {
            "canonical": "I am {adjective/noun_phrase}.",
            "family": "family:identity_be",
            "type": "identity_statement",
            "grammar": ["grammar:GRAMMAR_NODE_000718", "grammar:GRAMMAR_NODE_001215"],
            "themes": ["theme:a1_personal_information_and_greetings"],
            "examples": ["I am happy.", "I am a student."],
            "difficulty": 0.1
        },
        {
            "canonical": "My name is {name}.",
            "family": "family:identity_name",
            "type": "identity_statement",
            "grammar": ["grammar:GRAMMAR_NODE_000749"],
            "themes": ["theme:a1_personal_information_and_greetings"],
            "examples": ["My name is John.", "My name is Sarah."],
            "difficulty": 0.05
        },
        {
            "canonical": "I have {noun_phrase}.",
            "family": "family:possession_have",
            "type": "possession_statement",
            "grammar": ["grammar:GRAMMAR_NODE_001187"],
            "themes": ["theme:a1_personal_information_and_greetings"],
            "examples": ["I have a pen.", "I have a dog."],
            "difficulty": 0.12
        },
        # Preference
        {
            "canonical": "I like {noun_phrase/gerund}.",
            "family": "family:preference_like",
            "type": "preference_statement",
            "grammar": ["grammar:GRAMMAR_NODE_000670", "grammar:GRAMMAR_NODE_001196"],
            "themes": ["theme:a1_interests_and_abilities"],
            "examples": ["I like apples.", "I like swimming."],
            "difficulty": 0.15
        },
        {
            "canonical": "I don't like {noun_phrase/gerund}.",
            "family": "family:preference_like",
            "type": "preference_statement",
            "grammar": ["grammar:GRAMMAR_NODE_000671", "grammar:GRAMMAR_NODE_001196"],
            "themes": ["theme:a1_interests_and_abilities"],
            "examples": ["I don't like soccer.", "I don't like reading."],
            "difficulty": 0.18
        },
        # Ability
        {
            "canonical": "I can {verb_stem}.",
            "family": "family:ability_can",
            "type": "ability_statement",
            "grammar": ["grammar:GRAMMAR_NODE_000487", "grammar:GRAMMAR_NODE_000492"],
            "themes": ["theme:a1_interests_and_abilities"],
            "examples": ["I can swim.", "I can run."],
            "difficulty": 0.15
        },
        {
            "canonical": "Can you {verb_stem}?",
            "family": "family:ability_can",
            "type": "ability_question",
            "grammar": ["grammar:GRAMMAR_NODE_000488", "grammar:GRAMMAR_NODE_000492"],
            "themes": ["theme:a1_interests_and_abilities"],
            "examples": ["Can you cook?", "Can you swim?"],
            "difficulty": 0.18
        },
        # Location / Existence
        {
            "canonical": "There is {noun_phrase}.",
            "family": "family:existence_there",
            "type": "existence_statement",
            "grammar": ["grammar:GRAMMAR_NODE_001211"],
            "themes": ["theme:a1_homes_and_neighborhoods"],
            "examples": ["There is a cat.", "There is milk."],
            "difficulty": 0.15
        },
        {
            "canonical": "There is {noun_phrase_1} in/on/under {noun_phrase_2}.",
            "family": "family:existence_there",
            "type": "existence_statement",
            "grammar": ["grammar:GRAMMAR_NODE_001211"],
            "themes": ["theme:a1_homes_and_neighborhoods"],
            "examples": ["There is a book on the table.", "There is a cat in the box."],
            "difficulty": 0.2
        },
        {
            "canonical": "Where is {noun_phrase}?",
            "family": "family:location_where",
            "type": "wh_location_question",
            "grammar": ["grammar:GRAMMAR_NODE_001129"],
            "themes": ["theme:a1_homes_and_neighborhoods"],
            "examples": ["Where is the bathroom?", "Where is my book."],
            "difficulty": 0.15
        },
        # Daily Routine
        {
            "canonical": "I {verb_stem} every day.",
            "family": "family:routine_daily",
            "type": "routine_statement",
            "grammar": ["grammar:GRAMMAR_NODE_001187"],
            "themes": ["theme:a1_daily_life_and_routines"],
            "examples": ["I study every day.", "I run every day."],
            "difficulty": 0.12
        },
        {
            "canonical": "I {verb_stem} at {time}.",
            "family": "family:routine_daily",
            "type": "routine_statement",
            "grammar": ["grammar:GRAMMAR_NODE_001187"],
            "themes": ["theme:a1_daily_life_and_routines"],
            "examples": ["I sleep at 10 PM.", "I wake up at 7 AM."],
            "difficulty": 0.18
        },
        # Request / Classroom
        {
            "canonical": "Can I have {noun_phrase}?",
            "family": "family:request_polite",
            "type": "request_pattern",
            "grammar": ["grammar:GRAMMAR_NODE_000495"],
            "themes": ["theme:a1_school_and_classroom"],
            "examples": ["Can I have a pencil?", "Can I have some water?"],
            "difficulty": 0.15
        },
        {
            "canonical": "May I {verb_stem}?",
            "family": "family:request_polite",
            "type": "request_pattern",
            "grammar": ["grammar:GRAMMAR_NODE_000495"],
            "themes": ["theme:a1_school_and_classroom"],
            "examples": ["May I come in?", "May I leave?"],
            "difficulty": 0.18
        },
        # Description
        {
            "canonical": "It is {adjective}.",
            "family": "family:description_it",
            "type": "description_pattern",
            "grammar": ["grammar:GRAMMAR_NODE_000718", "grammar:GRAMMAR_NODE_001215"],
            "themes": ["theme:a1_homes_and_neighborhoods"],
            "examples": ["It is cold.", "It is hot.", "It is red."],
            "difficulty": 0.1
        },
        {
            "canonical": "This is {noun_phrase}.",
            "family": "family:description_demonstrative",
            "type": "description_pattern",
            "grammar": ["grammar:GRAMMAR_NODE_000326"],
            "themes": ["theme:a1_homes_and_neighborhoods"],
            "examples": ["This is a phone.", "This is my book."],
            "difficulty": 0.1
        },
        {
            "canonical": "That is {noun_phrase}.",
            "family": "family:description_demonstrative",
            "type": "description_pattern",
            "grammar": ["grammar:GRAMMAR_NODE_000326"],
            "themes": ["theme:a1_homes_and_neighborhoods"],
            "examples": ["That is a car.", "That is a bird."],
            "difficulty": 0.1
        }
    ]
    
    pattern_nodes = []
    pattern_edges = []
    
    # Store indices for prerequisite checks
    node_id_by_family_type = {}
    
    # 3. Mount Manual A1 Patterns
    pattern_id_num = 1
    for mdef in manual_a1_defs:
        node_id = f"pattern:PATTERN_NODE_{pattern_id_num:06d}"
        sp_id = f"SP_{pattern_id_num:06d}"
        
        # Verify and filter grammar nodes
        deferred_grammar = []
        valid_grammar = []
        for gid in mdef["grammar"]:
            if gid in valid_grammar_ids:
                valid_grammar.append(gid)
            else:
                deferred_grammar.append(gid)
                
        # Verify and filter themes
        deferred_themes = []
        valid_themes = []
        for tid in mdef["themes"]:
            if tid in valid_theme_ids:
                valid_themes.append(tid)
            else:
                deferred_themes.append(tid)
                
        # Slots
        slots = extract_slots_from_pattern(mdef["canonical"], "A1")
        
        metadata = {
            "pattern_id": node_id,
            "canonical_pattern": mdef["canonical"],
            "normalized_pattern": mdef["canonical"].lower(),
            "pattern_family_id": mdef["family"],
            "pattern_type": mdef["type"],
            "cefr_level": "A1",
            "difficulty_score": mdef["difficulty"],
            "slots": slots,
            "grammar_refs": valid_grammar,
            "vocabulary_slot_constraints": {},
            "chunk_refs": [],
            "theme_refs": valid_themes,
            "example_sentences": mdef["examples"],
            "generator_allowed": True,
            "validator_required": True,
            "source": "MANUAL_A1_CORE_PATTERN",
            "review_status": "accepted",
            "deferred_edges": [f"grammar:{gid}" for gid in deferred_grammar] + [f"theme:{tid}" for tid in deferred_themes]
        }
        
        node = {
            "id": node_id,
            "node_type": "sentence_pattern",
            "label": mdef["canonical"],
            "authority_source": {
                "source_name": "ULGA Sentence Pattern Authority",
                "source_file": "ulga/build_ulga_sentence_patterns.py",
                "source_record_id": sp_id,
                "derivation": "manual_review"
            },
            "cefr_level": "A1",
            "confidence": {
                "value": 1.0,
                "method": "manual_review",
                "notes": ["Manually designed A1 Core pattern."]
            },
            "version": {
                "contract": "ULGA-S2",
                "source_version": "1.0.0",
                "generated_at": generated_at
            },
            "metadata": metadata
        }
        
        pattern_nodes.append(node)
        node_id_by_family_type[(mdef["family"], mdef["type"])] = node_id
        
        # Build physical uses edges to grammar nodes
        for gid in valid_grammar:
            edge_id = f"edge:{node_id}:uses:{gid}"
            pattern_edges.append({
                "id": edge_id,
                "source_node_id": node_id,
                "target_node_id": gid,
                "edge_type": "uses",
                "authority_source": {
                    "source_name": "ULGA Sentence Pattern Edge Compiler",
                    "derivation": "manual_review"
                },
                "confidence": {
                    "value": 1.0,
                    "method": "deterministic_mapping"
                },
                "version": {
                    "contract": "ULGA-S2",
                    "source_version": "1.0.0",
                    "generated_at": generated_at
                },
                "metadata": {
                    "logical_edge_type": "PATTERN_USES_GRAMMAR"
                }
            })
            
        # Build physical belongs_to edges to themes
        for tid in valid_themes:
            edge_id = f"edge:{node_id}:belongs_to:{tid}"
            pattern_edges.append({
                "id": edge_id,
                "source_node_id": node_id,
                "target_node_id": tid,
                "edge_type": "belongs_to",
                "authority_source": {
                    "source_name": "ULGA Sentence Pattern Edge Compiler",
                    "derivation": "manual_review"
                },
                "confidence": {
                    "value": 1.0,
                    "method": "deterministic_mapping"
                },
                "version": {
                    "contract": "ULGA-S2",
                    "source_version": "1.0.0",
                    "generated_at": generated_at
                },
                "metadata": {
                    "logical_edge_type": "PATTERN_BELONGS_TO_THEME"
                }
            })
            
        pattern_id_num += 1
        
    # Build Manual Prerequisite Edges (e.g. question requires statement)
    prereq_pairs = [
        (("family:ability_can", "ability_question"), ("family:ability_can", "ability_statement")),
        (("family:preference_like", "preference_statement"), ("family:preference_like", "preference_statement")), # don't like requires like
        (("family:existence_there", "existence_statement"), ("family:existence_there", "existence_statement")), # complex there is requires basic
        (("family:routine_daily", "routine_statement"), ("family:routine_daily", "routine_statement")) # routine at time requires routine every day
    ]
    # To keep it safe and deterministic, let's manually write the exact pairs:
    # SP_000007 (Can you?) requires SP_000006 (I can)
    # SP_000005 (I don't like) requires SP_000004 (I like)
    # SP_000009 (There is x in y) requires SP_000008 (There is)
    # SP_000012 (I verb at time) requires SP_000011 (I verb every day)
    manual_prereqs = [
        ("pattern:PATTERN_NODE_000007", "pattern:PATTERN_NODE_000006"),
        ("pattern:PATTERN_NODE_000005", "pattern:PATTERN_NODE_000004"),
        ("pattern:PATTERN_NODE_000009", "pattern:PATTERN_NODE_000008"),
        ("pattern:PATTERN_NODE_000012", "pattern:PATTERN_NODE_000011")
    ]
    for src_id, tgt_id in manual_prereqs:
        edge_id = f"edge:{src_id}:prerequisite:{tgt_id}"
        pattern_edges.append({
            "id": edge_id,
            "source_node_id": src_id,
            "target_node_id": tgt_id,
            "edge_type": "prerequisite",
            "authority_source": {
                "source_name": "ULGA Sentence Pattern Edge Compiler",
                "derivation": "manual_review"
            },
            "confidence": {
                "value": 1.0,
                "method": "deterministic_mapping"
            },
            "version": {
                "contract": "ULGA-S2",
                "source_version": "1.0.0",
                "generated_at": generated_at
            },
            "metadata": {
                "logical_edge_type": "PATTERN_PRECEDES_PATTERN"
            }
        })

    # 4. Mount Chunk-Derived Patterns
    chunk_pattern_count = 0
    review_status_counts = Counter()
    review_status_counts["accepted"] = len(manual_a1_defs)
    
    difficulty_score_by_level = {
        "A1": 0.1,
        "A1_plus": 0.18,
        "A2": 0.25,
        "A2_plus": 0.35,
        "B1": 0.45,
        "B1_plus": 0.55,
        "B2": 0.65,
        "B2_plus": 0.72,
        "C1": 0.8,
        "C2": 0.95
    }

    for m in chunk_metadata:
        if not m.get("pattern_seed"):
            continue
            
        chunk_pattern_count += 1
        node_id = f"pattern:PATTERN_NODE_{pattern_id_num:06d}"
        sp_id = f"SP_{pattern_id_num:06d}"
        
        chunk_id = m["chunk_id"]
        slot_pat = m.get("slot_pattern")
        cefr = m.get("cefr_level")
        
        # Fallback level to C2 if null
        cefr_val = cefr if cefr else "C2"
        diff_score = difficulty_score_by_level.get(cefr_val, 0.5)
        
        # Verify grammar prerequisites
        deferred_grammar = []
        valid_grammar = []
        for gid in m.get("grammar_prerequisites", []):
            if gid in valid_grammar_ids:
                valid_grammar.append(gid)
            else:
                deferred_grammar.append(gid)
                
        # Slots list
        slots = extract_slots_from_pattern(slot_pat if slot_pat else "", cefr_val) if slot_pat else []

        # Determine review status
        has_placeholder = bool(slot_pat and "{" in slot_pat and "}" in slot_pat)
        is_invalid = (
            not slot_pat
            or m.get("slot_count", 0) == 0
            or has_malformed_placeholders(slot_pat)
            or (has_placeholder and len(slots) == 0)
        )
        review_required = m.get("manual_review_required", False) or is_invalid

        status = "needs_review" if review_required else "accepted"
        review_status_counts[status] += 1
        
        metadata = {
            "pattern_id": node_id,
            "canonical_pattern": slot_pat if slot_pat else "",
            "normalized_pattern": slot_pat.lower() if slot_pat else "",
            "pattern_family_id": f"family:chunk_derived_{chunk_id.replace('chunk:', '')}",
            "pattern_type": "chunk_derived_pattern",
            "cefr_level": cefr,
            "difficulty_score": diff_score,
            "slots": slots,
            "grammar_refs": valid_grammar,
            "vocabulary_slot_constraints": {},
            "chunk_refs": [chunk_id],
            "theme_refs": [],
            "example_sentences": [m["chunk_text"]],
            "generator_allowed": not review_required, # Don't allow generators to use needs_review patterns
            "validator_required": True,
            "source": "CHUNK_GRAMMAR_METADATA_DERIVED",
            "review_status": status,
            "deferred_edges": [f"grammar:{gid}" for gid in deferred_grammar]
        }
        
        node = {
            "id": node_id,
            "node_type": "sentence_pattern",
            "label": slot_pat if slot_pat else m["chunk_text"],
            "authority_source": {
                "source_name": "ULGA Sentence Pattern Authority",
                "source_file": "ulga/graph/chunk_grammar_metadata.json",
                "source_record_id": sp_id,
                "derivation": "derived_safe_layer"
            },
            "cefr_level": cefr,
            "confidence": {
                "value": m.get("parsing_confidence", 0.95),
                "method": "rule_based_compilation",
                "notes": ["Compiled from chunk grammar metadata parsing rules."]
            },
            "version": {
                "contract": "ULGA-S2",
                "source_version": "1.0.0",
                "generated_at": generated_at
            },
            "metadata": metadata
        }
        
        pattern_nodes.append(node)
        
        # Build physical uses edges to grammar nodes
        for gid in valid_grammar:
            edge_id = f"edge:{node_id}:uses:{gid}"
            pattern_edges.append({
                "id": edge_id,
                "source_node_id": node_id,
                "target_node_id": gid,
                "edge_type": "uses",
                "authority_source": {
                    "source_name": "ULGA Sentence Pattern Edge Compiler",
                    "derivation": "rule_based"
                },
                "confidence": {
                    "value": 0.95,
                    "method": "deterministic_mapping"
                },
                "version": {
                    "contract": "ULGA-S2",
                    "source_version": "1.0.0",
                    "generated_at": generated_at
                },
                "metadata": {
                    "logical_edge_type": "PATTERN_USES_GRAMMAR"
                }
            })
            
        # Build physical uses edges to chunk nodes
        if chunk_id in valid_chunk_ids:
            edge_id = f"edge:{node_id}:uses:{chunk_id}"
            pattern_edges.append({
                "id": edge_id,
                "source_node_id": node_id,
                "target_node_id": chunk_id,
                "edge_type": "uses",
                "authority_source": {
                    "source_name": "ULGA Sentence Pattern Edge Compiler",
                    "derivation": "rule_based"
                },
                "confidence": {
                    "value": 1.0,
                    "method": "deterministic_mapping"
                },
                "version": {
                    "contract": "ULGA-S2",
                    "source_version": "1.0.0",
                    "generated_at": generated_at
                },
                "metadata": {
                    "logical_edge_type": "PATTERN_USES_CHUNK"
                }
            })
        else:
            metadata["deferred_edges"].append(chunk_id)
            
        pattern_id_num += 1

    # 5. Build Graph Wrapper
    graph = {
        "graph_id": "ulga_graph.sentence_patterns",
        "contract_version": "ULGA-S2",
        "schema_version": "1.0.0",
        "formal_data_mounted": True,
        "mounted_stage": "ULGA-S7B",
        "nodes": pattern_nodes,
        "edges": pattern_edges,
        "node_count": len(pattern_nodes),
        "edge_count": len(pattern_edges),
        "metadata": {
            "purpose": "ULGA-S7B sentence pattern node mounting",
            "data_policy": "sentence_patterns_only",
            "manual_pattern_count": len(manual_a1_defs),
            "chunk_derived_pattern_count": chunk_pattern_count,
            "prerequisite_edge_count": len(manual_prereqs)
        },
        "validation_status": "untested"
    }

    # 6. Build Mount Summary
    edge_types = Counter(e["edge_type"] for e in pattern_edges)
    summary = {
        "mounting_stage": "ULGA-S7B",
        "manual_a1_core_pattern_count": len(manual_a1_defs),
        "chunk_derived_pattern_count": chunk_pattern_count,
        "total_sentence_patterns_generated": len(pattern_nodes),
        "review_status_distribution": dict(review_status_counts),
        "edge_count_by_type": dict(edge_types),
        "total_edges_generated": len(pattern_edges)
    }

    # Write files
    write_json(NODES_OUT_PATH, pattern_nodes)
    write_json(EDGES_OUT_PATH, pattern_edges)
    write_json(GRAPH_OUT_PATH, graph)
    write_json(GRAPH_COMPILER_OUT_PATH, graph)
    write_json(SUMMARY_OUT_PATH, summary)

    print(f"Wrote {len(pattern_nodes)} nodes to {NODES_OUT_PATH}")
    print(f"Wrote {len(pattern_edges)} edges to {EDGES_OUT_PATH}")
    print(f"Wrote graph wrapper to {GRAPH_OUT_PATH}")
    print(f"Wrote graph compiler wrapper to {GRAPH_COMPILER_OUT_PATH}")
    print(f"Wrote mount summary report to {SUMMARY_OUT_PATH}")
    print("Compilation complete.")

if __name__ == "__main__":
    main()
