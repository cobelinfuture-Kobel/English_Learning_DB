import json
import os
import sys
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

# Setup base directory
BASE_DIR = Path(__file__).resolve().parent

CHUNK_NODES_PATH = BASE_DIR / "graph" / "chunk_nodes.json"
VOCAB_NODES_PATH = BASE_DIR / "graph" / "vocabulary_nodes.json"
THEME_EDGES_PATH = BASE_DIR / "graph" / "vocabulary_theme_edges.refined.json"

OUTPUT_EDGES_PATH = BASE_DIR / "graph" / "chunk_vocabulary_edges.json"
OUTPUT_GRAPH_PATH = BASE_DIR / "graph" / "ulga_graph.chunk_vocabulary_linkage.json"
OUTPUT_SUMMARY_PATH = BASE_DIR / "reports" / "chunk_vocabulary_linkage_summary.json"
OUTPUT_UNRESOLVED_PATH = BASE_DIR / "reports" / "chunk_vocabulary_unresolved.json"

# CEFR level order for polysemy fallback
CEFR_ORDER = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

# Function Word Policy lists
EXCEPTIONS = {
    "going to", "used to", "have to", "as soon as", "on the other hand", "at last"
}

STOPWORDS = {
    "a", "an", "the",
    "of", "in", "on", "at", "to", "for",
    "and", "or", "but",
    "be", "do", "have",
    "sb", "sth", "sb's", "sth's"
}

BE_DO_HAVE_FORMS = {
    "be", "been", "being", "am", "is", "are", "was", "were",
    "do", "does", "did", "doing", "done",
    "have", "has", "had", "having"
}

ALL_STOPWORDS = STOPWORDS.union(BE_DO_HAVE_FORMS)

def get_tokens(normalized_chunk):
    # Strip parenthesis but keep content inside
    cleaned = normalized_chunk.replace('(', ' ').replace(')', ' ')
    # Replace punctuation with space but keep apostrophe for contractions
    cleaned = re.sub(r"[^\w\s']", ' ', cleaned)
    return [t.strip() for t in cleaned.split() if t.strip()]

def get_candidate_lemmas(token):
    token = token.lower()
    candidates = [token]
    
    # 1. Plurals and third person singular
    if token.endswith('ies'):
        candidates.append(token[:-3] + 'y')
    elif token.endswith('es'):
        candidates.append(token[:-2])    # e.g., clutches -> clutch, boxes -> box
        candidates.append(token[:-1])    # e.g., loves -> love
    elif token.endswith('s') and not token.endswith('ss'):
        candidates.append(token[:-1])    # e.g., eggs -> egg, looks -> look
        
    # 2. Past tense / past participle
    if token.endswith('ied'):
        candidates.append(token[:-3] + 'y')  # e.g., modified -> modify
    elif token.endswith('ed'):
        candidates.append(token[:-2])    # e.g., worked -> work
        candidates.append(token[:-1])    # e.g., loved -> love
        # Consonant doubling (e.g., stopped -> stop)
        if len(token) >= 6 and token[-3] == token[-4]:
            candidates.append(token[:-3])
            
    # 3. Present participle
    if token.endswith('ing'):
        candidates.append(token[:-3])    # e.g., speaking -> speak
        candidates.append(token[:-3] + 'e')  # e.g., writing -> write
        # Consonant doubling (e.g., running -> run)
        if len(token) >= 6 and token[-4] == token[-5]:
            candidates.append(token[:-4])
            
    # 4. Spelling normalizations (British vs American)
    if token.endswith('l') and not token.endswith('ll'):
        candidates.append(token + 'l')   # e.g. fulfil -> fulfill
        
    return list(dict.fromkeys(candidates))

def check_theme_match(chunk_theme_hints, vocab_node_themes):
    if not chunk_theme_hints or not vocab_node_themes:
        return False
    for hint in chunk_theme_hints:
        hint_lower = hint.strip().lower()
        if hint_lower == 'general':
            continue
        for theme_id in vocab_node_themes:
            theme_part = theme_id.split(':')[-1].lower()
            if hint_lower in theme_part:
                return True
    return False

def resolve_sense(token, chunk_theme_hints, lemma_to_nodes, vocab_to_themes):
    candidate_lemmas = get_candidate_lemmas(token)
    matching_nodes = []
    for cl in candidate_lemmas:
        if cl in lemma_to_nodes:
            matching_nodes.extend(lemma_to_nodes[cl])
            
    if not matching_nodes:
        return None, "unresolved", 0.40
        
    # Case A: Unique match
    if len(matching_nodes) == 1:
        return matching_nodes[0], "exact_unique_sense", 1.0
        
    # Case B: Multiple matches
    # B1: Topic assisted match
    topic_matched_nodes = []
    for node in matching_nodes:
        themes = vocab_to_themes.get(node['id'], set())
        if check_theme_match(chunk_theme_hints, themes):
            topic_matched_nodes.append(node)
            
    if len(topic_matched_nodes) == 1:
        return topic_matched_nodes[0], "topic_assisted", 0.80
    elif len(topic_matched_nodes) > 1:
        cefr_levels = {n.get('cefr_level') for n in topic_matched_nodes}
        if len(cefr_levels) == 1:
            selected = sorted(topic_matched_nodes, key=lambda n: n['metadata'].get('frequency_score', 0.0), reverse=True)[0]
            return selected, "exact_multi_same_topic", 0.85
        else:
            selected = sorted(topic_matched_nodes, key=lambda n: (CEFR_ORDER.get(n.get('cefr_level'), 99), -n['metadata'].get('frequency_score', 0.0)))[0]
            return selected, "polysemy_fallback", 0.60
            
    # B2: No topic match. Check if all matching nodes share the same CEFR level
    cefr_levels = {n.get('cefr_level') for n in matching_nodes}
    if len(cefr_levels) == 1:
        selected = sorted(matching_nodes, key=lambda n: n['metadata'].get('frequency_score', 0.0), reverse=True)[0]
        return selected, "exact_multi_same_topic", 0.85
        
    # B3: Fallback polysemy
    selected = sorted(matching_nodes, key=lambda n: (CEFR_ORDER.get(n.get('cefr_level'), 99), -n['metadata'].get('frequency_score', 0.0)))[0]
    return selected, "polysemy_fallback", 0.60

def determine_anchor_role(token, chunk, selected_vocab_node, token_index, total_tokens):
    usage_class = chunk['metadata'].get('usage_class', 'general_phrase')
    pos = selected_vocab_node['metadata'].get('part_of_speech', '').lower()
    
    # 1. Formulaic usage classes
    if usage_class in ['idiom', 'social_expression', 'greeting', 'emotion_expression']:
        return "formulaic_component"
        
    # 2. Stopwords
    token_lower = token.lower()
    if token_lower in ALL_STOPWORDS:
        return "function_word"
        
    # 3. Phrasal verbs
    if usage_class == 'phrasal_verb':
        if 'verb' in pos or 'modal' in pos or 'auxiliary' in pos:
            return "verb_anchor"
        else:
            return "modifier"
            
    # 4. Compound nouns
    if usage_class == 'compound_noun':
        if token_index == total_tokens - 1:
            return "head"
        else:
            return "modifier"
            
    # 5. Prepositional phrases
    if usage_class == 'prepositional_phrase':
        if token_lower in STOPWORDS:
            return "function_word"
        elif 'noun' in pos:
            return "noun_anchor"
        elif 'adj' in pos:
            return "adjective_anchor"
        else:
            return "head"
            
    # 6. General/Default rules
    if 'noun' in pos:
        return "noun_anchor"
    elif 'verb' in pos:
        return "verb_anchor"
    elif 'adj' in pos:
        return "adjective_anchor"
        
    return "head"

def main():
    print("Starting Chunk-Vocabulary Linkage Edge Builder...")
    
    # 1. Load data
    if not CHUNK_NODES_PATH.exists():
        print(f"Error: Chunk nodes file not found at {CHUNK_NODES_PATH}")
        sys.exit(1)
    with open(CHUNK_NODES_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    if not VOCAB_NODES_PATH.exists():
        print(f"Error: Vocabulary nodes file not found at {VOCAB_NODES_PATH}")
        sys.exit(1)
    with open(VOCAB_NODES_PATH, "r", encoding="utf-8") as f:
        vocab = json.load(f)
        
    vocab_to_themes = defaultdict(set)
    if THEME_EDGES_PATH.exists():
        with open(THEME_EDGES_PATH, "r", encoding="utf-8") as f:
            theme_edges = json.load(f)
        for edge in theme_edges:
            vocab_to_themes[edge['source_node_id']].add(edge['target_node_id'])
            
    print(f"Loaded {len(chunks)} chunk nodes.")
    print(f"Loaded {len(vocab)} vocabulary nodes.")
    print(f"Loaded theme mappings for {len(vocab_to_themes)} vocabulary nodes.")
    
    # Group vocabulary nodes by canonical lemma
    lemma_to_nodes = defaultdict(list)
    for n in vocab:
        lemma = n['metadata'].get('canonical_lemma', n['label']).lower()
        lemma_to_nodes[lemma].append(n)
        
    generated_edges = []
    unresolved_chunks = []
    seen_edge_keys = set()
    
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    anchored_chunks_count = 0
    confidence_counts = defaultdict(int)
    method_counts = defaultdict(int)
    unique_vocab_targets = set()
    
    for chunk in chunks:
        norm_chunk = chunk['metadata'].get('normalized_chunk', chunk['label'])
        tokens = get_tokens(norm_chunk)
        
        is_exception = norm_chunk.lower() in EXCEPTIONS
        
        chunk_edges = []
        
        for idx, token in enumerate(tokens):
            # Apply stopword filtering unless chunk is an exception
            if token.lower() in ALL_STOPWORDS and not is_exception:
                continue
                
            selected_node, method, confidence = resolve_sense(
                token, 
                chunk['metadata'].get('theme_hint', []), 
                lemma_to_nodes, 
                vocab_to_themes
            )
            
            if selected_node:
                vocab_id = selected_node['id']
                # Determine anchor role
                role = determine_anchor_role(token, chunk, selected_node, idx, len(tokens))
                
                # Check for duplicate edge (from_node_id, to_node_id, edge_type, token_position)
                edge_key = (chunk['id'], vocab_id, "uses", idx)
                if edge_key in seen_edge_keys:
                    continue
                seen_edge_keys.add(edge_key)
                
                # Generate unique deterministic edge ID
                edge_id = f"edge:chunk_vocab_{chunk['metadata']['source_chunk_id']}_{selected_node['metadata']['source_vocabulary_id']}_{idx}"
                
                edge = {
                    "id": edge_id,
                    "source_node_id": chunk['id'],
                    "target_node_id": vocab_id,
                    "edge_type": "uses",
                    "direction": "from_requires_to",
                    "authority_source": {
                        "source_name": "ULGA Chunk Vocabulary Linkage",
                        "source_file": None,
                        "source_record_id": None,
                        "derivation": "rule_based"
                    },
                    "confidence": {
                        "value": confidence,
                        "method": method
                    },
                    "version": {
                        "contract": "ULGA-S2",
                        "source_version": "1.0.0",
                        "generated_at": timestamp
                    },
                    "metadata": {
                        "source_chunk_id": chunk['metadata']['source_chunk_id'],
                        "target_vocabulary_id": selected_node['metadata']['source_vocabulary_id'],
                        "chunk_text": chunk['label'],
                        "vocabulary_lemma": selected_node['metadata'].get('canonical_lemma', selected_node['label']),
                        "vocabulary_pos": selected_node['metadata'].get('part_of_speech', ''),
                        "vocabulary_cefr": selected_node.get('cefr_level'),
                        "anchor_role": role,
                        "token_position": idx,
                        "sense_resolution_method": method,
                        "relation_family": "chunk_vocabulary",
                        "usage_class": chunk['metadata'].get('usage_class', ''),
                        "theme_hint": chunk['metadata'].get('theme_hint', []),
                        "chunk_cefr": chunk.get('cefr_level'),
                        "confidence_method": method,
                        "mounting_stage": "ULGA-S6D"
                    }
                }
                chunk_edges.append(edge)
                unique_vocab_targets.add(vocab_id)
                confidence_counts[str(confidence)] += 1
                method_counts[method] += 1
                
        if chunk_edges:
            generated_edges.extend(chunk_edges)
            anchored_chunks_count += 1
        else:
            unresolved_chunks.append({
                "chunk_id": chunk['id'],
                "label": chunk['label'],
                "normalized_chunk": norm_chunk,
                "usage_class": chunk['metadata'].get('usage_class', ''),
                "cefr_level": chunk.get('cefr_level', ''),
                "tokens": tokens,
                "reason": "no vocabulary match after stopword filtering and morphology checks"
            })
            
    # Write output edges JSON
    with open(OUTPUT_EDGES_PATH, "w", encoding="utf-8") as f:
        json.dump(generated_edges, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(generated_edges)} edges to {OUTPUT_EDGES_PATH}.")
    
    # Write unresolved chunks JSON
    with open(OUTPUT_UNRESOLVED_PATH, "w", encoding="utf-8") as f:
        json.dump(unresolved_chunks, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(unresolved_chunks)} unresolved chunks to {OUTPUT_UNRESOLVED_PATH}.")
    
    # Write Graph Wrapper JSON
    graph_wrapper = {
        "graph_id": "ulga_graph.chunk_vocabulary_linkage",
        "contract_version": "ULGA-S2",
        "schema_version": "1.0.0",
        "formal_data_mounted": True,
        "mounted_stage": "ULGA-S6D",
        "chunk_node_count": len(chunks),
        "vocabulary_node_count": len(vocab),
        "chunk_vocabulary_edge_count": len(generated_edges),
        "nodes": [],
        "edges": generated_edges,
        "chunk_theme_projection": False,
        "chunk_grammar_metadata": False,
        "chunk_collocation_expansion": False,
        "validation_status": "untested"
    }
    with open(OUTPUT_GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(graph_wrapper, f, indent=2, ensure_ascii=False)
    print(f"Saved graph wrapper to {OUTPUT_GRAPH_PATH}.")
    
    # Calculate coverage metrics
    anchored_ratio = (anchored_chunks_count / len(chunks)) * 100 if chunks else 0.0
    avg_edges = len(generated_edges) / len(chunks) if chunks else 0.0
    
    # Confidence groups
    high_conf = sum(count for score, count in confidence_counts.items() if float(score) >= 0.90)
    med_conf = sum(count for score, count in confidence_counts.items() if 0.70 <= float(score) < 0.90)
    low_conf = sum(count for score, count in confidence_counts.items() if float(score) < 0.70)
    
    summary = {
        "mounting_stage": "ULGA-S6D",
        "chunk_count": len(chunks),
        "anchored_chunk_count": anchored_chunks_count,
        "anchored_ratio": anchored_ratio,
        "edge_count": len(generated_edges),
        "avg_edges_per_chunk": avg_edges,
        "unique_vocabulary_targets": len(unique_vocab_targets),
        "confidence_breakdown": dict(confidence_counts),
        "method_breakdown": dict(method_counts),
        "high_confidence_edges": high_conf,
        "medium_confidence_edges": med_conf,
        "low_confidence_edges": low_conf,
        "unresolved_chunk_count": len(unresolved_chunks)
    }
    
    with open(OUTPUT_SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved summary report to {OUTPUT_SUMMARY_PATH}.")
    
    print("\nBuilder Finished Successfully:")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Anchored: {anchored_chunks_count} ({anchored_ratio:.2f}%)")
    print(f"  Edges created: {len(generated_edges)}")
    print(f"  Unresolved chunks: {len(unresolved_chunks)}")

if __name__ == "__main__":
    main()
