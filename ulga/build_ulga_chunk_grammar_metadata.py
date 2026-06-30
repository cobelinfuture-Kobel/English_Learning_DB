import json
import os
import sys
import re
from pathlib import Path
from collections import defaultdict

# Setup base directory
BASE_DIR = Path(__file__).resolve().parent

CHUNK_NODES_PATH = BASE_DIR / "graph" / "chunk_nodes.json"
EDGES_PATH = BASE_DIR / "graph" / "chunk_vocabulary_edges.json"
RULES_PATH = BASE_DIR / "rules" / "chunk_grammar_metadata_rules.json"
GRAMMAR_NODES_PATH = BASE_DIR / "graph" / "grammar_nodes.json"

OUTPUT_METADATA_PATH = BASE_DIR / "graph" / "chunk_grammar_metadata.json"
OUTPUT_SUMMARY_PATH = BASE_DIR / "reports" / "chunk_grammar_parsing_summary.json"
OUTPUT_REVIEW_PATH = BASE_DIR / "reports" / "chunk_grammar_review_queue.json"

def get_tokens_fixed(normalized_chunk):
    """
    Tokenizer that incorporates the S6E trailing-s stripping fix:
    - Tokens with length <= 2 do not undergo trailing-s stripping (e.g. 'as' stays 'as', does not become 'a').
    """
    cleaned = normalized_chunk.replace('(', ' ').replace(')', ' ')
    cleaned = re.sub(r"[^\w\s']", ' ', cleaned)
    tokens = [t.strip() for t in cleaned.split() if t.strip()]
    return tokens

def get_candidate_lemmas_fixed(token):
    token = token.lower()
    candidates = [token]
    
    # Apply trailing-s stripping only if token length > 2
    if len(token) > 2:
        if token.endswith('ies'):
            candidates.append(token[:-3] + 'y')
        elif token.endswith('es'):
            candidates.append(token[:-2])
            candidates.append(token[:-1])
        elif token.endswith('s') and not token.endswith('ss'):
            candidates.append(token[:-1])
            
    # Past tense / past participle
    if len(token) > 3:
        if token.endswith('ied'):
            candidates.append(token[:-3] + 'y')
        elif token.endswith('ed'):
            candidates.append(token[:-2])
            candidates.append(token[:-1])
            if len(token) >= 6 and token[-3] == token[-4]:
                candidates.append(token[:-3])
                
    # Present participle
    if len(token) > 4:
        if token.endswith('ing'):
            candidates.append(token[:-3])
            candidates.append(token[:-3] + 'e')
            if len(token) >= 6 and token[-4] == token[-5]:
                candidates.append(token[:-4])
                
    return list(dict.fromkeys(candidates))

def parse_placeholders(label):
    text = label
    # Order of replacement: longer patterns first
    replacements = [
        ("doing sth", "{gerund}"),
        ("do sth", "{infinitive}"),
        ("sb's", "{sb_possessive}"),
        ("sth's", "{sth_possessive}"),
        ("sb", "{sb}"),
        ("sth", "{sth}")
    ]
    slots_found = []
    for placeholder, slot in replacements:
        pattern = re.compile(re.escape(placeholder), re.IGNORECASE)
        matches = pattern.findall(text)
        if matches:
            slots_found.extend([slot.strip("{}")] * len(matches))
            text = pattern.sub(slot, text)
    return text, slots_found

def main():
    print("Starting Chunk Grammar Metadata Layer Builder...")
    
    # 1. Load data
    if not CHUNK_NODES_PATH.exists():
        print(f"Error: Chunk nodes file not found at {CHUNK_NODES_PATH}")
        sys.exit(1)
    with open(CHUNK_NODES_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    if not EDGES_PATH.exists():
        print(f"Error: Edges file not found at {EDGES_PATH}")
        sys.exit(1)
    with open(EDGES_PATH, "r", encoding="utf-8") as f:
        edges = json.load(f)
        
    if not RULES_PATH.exists():
        print(f"Error: Rules file not found at {RULES_PATH}")
        sys.exit(1)
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        rules = json.load(f)
        
    if not GRAMMAR_NODES_PATH.exists():
        print(f"Error: Grammar nodes file not found at {GRAMMAR_NODES_PATH}")
        sys.exit(1)
    with open(GRAMMAR_NODES_PATH, "r", encoding="utf-8") as f:
        grammar_nodes = json.load(f)
        
    print(f"Loaded {len(chunks)} chunk nodes.")
    print(f"Loaded {len(edges)} chunk-vocabulary edges.")
    print(f"Loaded {len(rules)} parsing rules.")
    print(f"Loaded {len(grammar_nodes)} grammar nodes.")
    
    # Grammar node ID index
    valid_grammar_ids = {n['id'] for n in grammar_nodes}
    
    # Map chunk ID to its edges
    chunk_to_edges = defaultdict(list)
    for edge in edges:
        chunk_to_edges[edge['source_node_id']].append(edge)
        
    derived_metadata = []
    review_queue = []
    
    rule_match_counts = defaultdict(int)
    
    for chunk in chunks:
        chunk_id = chunk['id']
        chunk_text = chunk['label']
        normalized_chunk = chunk['metadata'].get('normalized_chunk', chunk['label'])
        usage_class = chunk['metadata'].get('usage_class', 'general_phrase')
        cefr_level = chunk.get('cefr_level', '')
        source_chunk_id = chunk['metadata'].get('source_chunk_id', '')
        
        # Apply rules
        matched_rule_ids = []
        grammar_signals = set()
        grammar_prerequisites = set()
        chunk_semantics = None
        formulaic_type = None
        pattern_seed = False
        confidences = []
        
        for rule in rules:
            if not rule.get('enabled', True):
                continue
                
            # Filter by usage class
            uc_filter = rule.get('usage_class_filter', ["*"])
            if "*" not in uc_filter and usage_class not in uc_filter:
                continue
                
            # Check pattern match (case-insensitive regex)
            pattern_str = rule.get('pattern', '.*')
            if re.search(pattern_str, chunk_text, re.IGNORECASE):
                matched_rule_ids.append(rule['rule_id'])
                rule_match_counts[rule['rule_id']] += 1
                
                # Merge signals & prerequisites
                grammar_signals.update(rule.get('grammar_signals', []))
                for g_id in rule.get('grammar_prerequisites', []):
                    if g_id in valid_grammar_ids:
                        grammar_prerequisites.add(g_id)
                        
                if not chunk_semantics:
                    chunk_semantics = rule.get('chunk_semantics')
                if not formulaic_type:
                    formulaic_type = rule.get('formulaic_type')
                if rule.get('pattern_seed'):
                    pattern_seed = True
                    
                confidences.append(rule.get('confidence', 0.5))
                
        # Parse slot pattern
        slot_pattern = None
        slot_count = 0
        slot_types = []
        
        # Heuristic 1: If has placeholders, replace them
        placeholder_regex = r"\b(sb's|sth's|sb|sth|do sth|doing sth)\b"
        if re.search(placeholder_regex, chunk_text, re.IGNORECASE):
            parsed_text, slots = parse_placeholders(chunk_text)
            slot_pattern = parsed_text
            slot_count = len(slots)
            slot_types = slots
            pattern_seed = True
            
        # Heuristic 2: Phrasal verbs with no placeholders
        elif usage_class == "phrasal_verb" and not slot_pattern:
            # Look up verb anchor
            c_edges = chunk_to_edges[chunk_id]
            verb_anchor_edge = next((e for e in c_edges if e['metadata'].get('anchor_role') == 'verb_anchor'), None)
            if verb_anchor_edge:
                verb_lemma = verb_anchor_edge['metadata'].get('vocabulary_lemma', '')
                if verb_lemma:
                    # Replace verb lemma in text
                    pattern = re.compile(r'\b' + re.escape(verb_lemma) + r'\b', re.IGNORECASE)
                    if pattern.search(chunk_text):
                        slot_pattern = pattern.sub("{verb}", chunk_text)
                        slot_count = 1
                        slot_types = ["verb"]
                        pattern_seed = True
                        
        # Default parsing stats
        max_confidence = max(confidences) if confidences else 0.5
        parsing_method = matched_rule_ids[0] if matched_rule_ids else "RULE_GRA_011_FALLBACK"
        if not matched_rule_ids:
            matched_rule_ids.append("RULE_GRA_011_FALLBACK")
            rule_match_counts["RULE_GRA_011_FALLBACK"] += 1
            grammar_signals.add("lexical_phrase")
            chunk_semantics = "general_expression"
            max_confidence = 0.7
            
        # Review criteria
        review_reasons = []
        if "etc" in chunk_text.lower():
            review_reasons.append("Vague placeholder 'etc.' requires manual specification")
            
        # Phrasal verbs without slots or verb anchors
        if usage_class == "phrasal_verb" and not slot_pattern:
            review_reasons.append("Phrasal verb failed to resolve slot pattern")
            
        # Pattern seeds that failed to generate slots
        if any(p in chunk_text.lower() for p in ["sb", "sth"]) and not slot_pattern:
            review_reasons.append("Placeholder seed failed to generate slot pattern")
            
        manual_review_required = len(review_reasons) > 0
        
        record = {
            "chunk_id": chunk_id,
            "source_chunk_id": source_chunk_id,
            "chunk_text": chunk_text,
            "normalized_chunk": normalized_chunk,
            "usage_class": usage_class,
            "cefr_level": cefr_level,
            "grammar_signals": sorted(list(grammar_signals)),
            "grammar_prerequisites": sorted(list(grammar_prerequisites)),
            "slot_pattern": slot_pattern,
            "slot_count": slot_count,
            "slot_types": slot_types,
            "chunk_semantics": chunk_semantics,
            "formulaic_type": formulaic_type,
            "pattern_seed": pattern_seed,
            "parsing_confidence": max_confidence,
            "parsing_method": parsing_method,
            "matched_rule_ids": matched_rule_ids,
            "manual_review_required": manual_review_required,
            "review_reasons": review_reasons,
            "mounting_stage": "ULGA-S6H"
        }
        
        derived_metadata.append(record)
        if manual_review_required:
            review_queue.append(record)
            
    # Write outputs
    with open(OUTPUT_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(derived_metadata, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(derived_metadata)} grammar metadata records to {OUTPUT_METADATA_PATH}.")
    
    with open(OUTPUT_REVIEW_PATH, "w", encoding="utf-8") as f:
        json.dump(review_queue, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(review_queue)} manual review items to {OUTPUT_REVIEW_PATH}.")
    
    # Calculate stats
    pattern_seeds_count = sum(1 for r in derived_metadata if r["pattern_seed"])
    placeholders_count = sum(1 for r in derived_metadata if any(p in r["chunk_text"].lower() for p in ["sb", "sth", "etc"]))
    formulaic_count = sum(1 for r in derived_metadata if r["formulaic_type"] == "formulaic")
    grammar_like_count = sum(1 for r in derived_metadata if "RULE_GRA_001_MODAL_FRAME" in r["matched_rule_ids"])
    
    summary = {
        "mounting_stage": "ULGA-S6H",
        "chunk_count": len(chunks),
        "parsed_metadata_count": len(derived_metadata),
        "pattern_seeds_count": pattern_seeds_count,
        "placeholders_count": placeholders_count,
        "formulaic_count": formulaic_count,
        "grammar_like_count": grammar_like_count,
        "manual_review_required_count": len(review_queue),
        "rule_match_counts": dict(rule_match_counts)
    }
    
    with open(OUTPUT_SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved parsing summary to {OUTPUT_SUMMARY_PATH}.")
    
    print("\nBuilder Finished Successfully:")
    print(f"  Total parsed: {len(derived_metadata)}")
    print(f"  Pattern seeds generated: {pattern_seeds_count}")
    print(f"  Manual review required: {len(review_queue)}")

if __name__ == "__main__":
    main()
