import json
import os
import sys
import re
from pathlib import Path
from collections import defaultdict, Counter

# Setup base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

CHUNK_NODES_PATH = BASE_DIR / "ulga" / "graph" / "chunk_nodes.json"
VOCAB_NODES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json"
EDGES_PATH = BASE_DIR / "ulga" / "graph" / "chunk_vocabulary_edges.json"
UNRESOLVED_PATH = BASE_DIR / "ulga" / "reports" / "chunk_vocabulary_unresolved.json"
THEME_EDGES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_theme_edges.refined.json"
MORPHOLOGY_EDGES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_morphology_edges.json"

OUTPUT_AUDIT_JSON = BASE_DIR / "ulga" / "reports" / "chunk_vocabulary_linkage_qa_audit.json"

CEFR_ORDER = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

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

def main():
    print("Starting Chunk-Vocabulary Linkage QA Audit...")
    
    # 1. Load files
    with open(CHUNK_NODES_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    with open(VOCAB_NODES_PATH, "r", encoding="utf-8") as f:
        vocab = json.load(f)
    with open(EDGES_PATH, "r", encoding="utf-8") as f:
        edges = json.load(f)
    with open(UNRESOLVED_PATH, "r", encoding="utf-8") as f:
        unresolved = json.load(f)
        
    vocab_to_themes = defaultdict(list)
    if THEME_EDGES_PATH.exists():
        with open(THEME_EDGES_PATH, "r", encoding="utf-8") as f:
            theme_edges = json.load(f)
        for edge in theme_edges:
            vocab_to_themes[edge['source_node_id']].append(edge['target_node_id'])
            
    vocab_to_morph = defaultdict(list)
    if MORPHOLOGY_EDGES_PATH.exists():
        with open(MORPHOLOGY_EDGES_PATH, "r", encoding="utf-8") as f:
            morph_edges = json.load(f)
        for edge in morph_edges:
            vocab_to_morph[edge['source_node_id']].append(edge['target_node_id'])
            
    print(f"Loaded {len(chunks)} chunk nodes, {len(vocab)} vocabulary nodes, {len(edges)} edges, {len(unresolved)} unresolved chunks.")
    
    # Vocabulary nodes indexes
    vocab_map = {n['id']: n for n in vocab}
    vocab_lemmas = set()
    lemma_to_nodes_count = defaultdict(int)
    for n in vocab:
        lemma = n['metadata'].get('canonical_lemma', n['label']).lower()
        vocab_lemmas.add(lemma)
        lemma_to_nodes_count[lemma] += 1
        
    chunk_map = {c['id']: c for c in chunks}
    
    # A. Basic Counts
    chunk_node_count = len(chunks)
    vocabulary_node_count = len(vocab)
    edge_count = len(edges)
    
    anchored_chunks = {e['source_node_id'] for e in edges}
    anchored_chunk_count = len(anchored_chunks)
    unresolved_chunk_count = len(unresolved)
    
    anchored_ratio = (anchored_chunk_count / chunk_node_count) * 100
    unresolved_ratio = (unresolved_chunk_count / chunk_node_count) * 100
    average_edges = edge_count / chunk_node_count
    
    unique_vocab_targets = len({e['target_node_id'] for e in edges})
    
    # B. Edge Direction / Schema Integrity
    all_source_are_chunks = all(e['source_node_id'].startswith("chunk:") for e in edges)
    all_target_are_vocab = all(e['target_node_id'].startswith("vocabulary:") for e in edges)
    all_uses = all(e['edge_type'] == "uses" for e in edges)
    
    seen_edge_keys = set()
    dup_count = 0
    self_loops = 0
    missing_endpoints = 0
    invalid_conf = 0
    
    for e in edges:
        src = e['source_node_id']
        tgt = e['target_node_id']
        etype = e['edge_type']
        tpos = e['metadata'].get('token_position')
        
        edge_key = (src, tgt, etype, tpos)
        if edge_key in seen_edge_keys:
            dup_count += 1
        seen_edge_keys.add(edge_key)
        
        if src == tgt:
            self_loops += 1
        if src not in chunk_map or tgt not in vocab_map:
            missing_endpoints += 1
            
        cval = e['confidence'].get('value')
        if cval is None or not (0.0 <= cval <= 1.0):
            invalid_conf += 1
            
    # C. Confidence Breakdown
    method_counter = Counter(e['confidence']['method'] for e in edges)
    conf_values = [e['confidence']['value'] for e in edges]
    high_conf = sum(1 for v in conf_values if v >= 0.90)
    med_conf = sum(1 for v in conf_values if 0.70 <= v < 0.90)
    low_conf = sum(1 for v in conf_values if v < 0.70)
    
    confidence_breakdown = {
        "exact_unique_sense": {
            "count": method_counter.get("exact_unique_sense", 0),
            "ratio": method_counter.get("exact_unique_sense", 0) / edge_count * 100 if edge_count else 0
        },
        "exact_multi_same_topic": {
            "count": method_counter.get("exact_multi_same_topic", 0),
            "ratio": method_counter.get("exact_multi_same_topic", 0) / edge_count * 100 if edge_count else 0
        },
        "topic_assisted": {
            "count": method_counter.get("topic_assisted", 0),
            "ratio": method_counter.get("topic_assisted", 0) / edge_count * 100 if edge_count else 0
        },
        "polysemy_fallback": {
            "count": method_counter.get("polysemy_fallback", 0),
            "ratio": method_counter.get("polysemy_fallback", 0) / edge_count * 100 if edge_count else 0
        },
        "unresolved": {
            "count": method_counter.get("unresolved", 0),
            "ratio": method_counter.get("unresolved", 0) / edge_count * 100 if edge_count else 0
        }
    }
    
    # D. Polysemy Risk Audit
    fallback_edges = [e for e in edges if e['confidence']['method'] == "polysemy_fallback"]
    fallback_target_counts = Counter(e['target_node_id'] for e in fallback_edges)
    top_vocab_fallback = [{"vocab_id": k, "count": v, "lemma": vocab_map[k]['metadata'].get('canonical_lemma', vocab_map[k]['label'])} for k, v in fallback_target_counts.most_common(100)]
    
    chunk_fallback_counts = Counter(e['source_node_id'] for e in fallback_edges)
    top_chunks_fallback = [{"chunk_id": k, "count": v, "label": chunk_map[k]['label']} for k, v in chunk_fallback_counts.most_common(100)]
    
    top_ambiguous_lemmas = [{"lemma": k, "count": v} for k, v in sorted(lemma_to_nodes_count.items(), key=lambda x: x[1], reverse=True)[:100]]
    
    fallback_uc_counter = Counter(chunk_map[e['source_node_id']]['metadata'].get('usage_class', '') for e in fallback_edges)
    fallback_cefr_counter = Counter(chunk_map[e['source_node_id']].get('cefr_level', '') for e in fallback_edges)
    
    # Examples of specific polysemous lemmas
    specific_lemmas = ["take", "get", "go", "make", "have", "look", "play", "run", "right", "light"]
    specific_lemma_audit = {}
    for l in specific_lemmas:
        l_edges = [e for e in edges if e['metadata']['vocabulary_lemma'].lower() == l]
        l_methods = Counter(e['confidence']['method'] for e in l_edges)
        specific_lemma_audit[l] = {
            "total_edges": len(l_edges),
            "methods": dict(l_methods)
        }
        
    # E. Anchor Role Audit
    role_counter = Counter(e['metadata'].get('anchor_role', '') for e in edges)
    
    chunk_to_roles = defaultdict(list)
    for e in edges:
        chunk_to_roles[e['source_node_id']].append(e['metadata'].get('anchor_role', ''))
        
    chunks_no_head = []
    chunks_multiple_heads = []
    chunks_only_modifiers = []
    
    for cid, roles in chunk_to_roles.items():
        heads = sum(1 for r in roles if r == "head")
        modifiers = sum(1 for r in roles if r == "modifier")
        
        if heads == 0:
            chunks_no_head.append(chunk_map[cid]['label'])
        elif heads > 1:
            chunks_multiple_heads.append(chunk_map[cid]['label'])
            
        if all(r == "modifier" for r in roles):
            chunks_only_modifiers.append(chunk_map[cid]['label'])
            
    # F. Function Word Leakage Audit
    function_word_anchors = [e for e in edges if e['metadata']['vocabulary_lemma'].lower() in ALL_STOPWORDS]
    function_word_anchor_count = len(function_word_anchors)
    top_fw_anchors = Counter(e['metadata']['vocabulary_lemma'].lower() for e in function_word_anchors)
    
    illegal_fw_anchors = []
    exception_approved_fw_anchors = []
    
    for e in function_word_anchors:
        chunk_text = e['metadata']['chunk_text'].lower()
        is_exc = chunk_text in EXCEPTIONS
        record = {
            "edge_id": e['id'],
            "chunk": e['metadata']['chunk_text'],
            "word": e['metadata']['vocabulary_lemma'].lower(),
            "role": e['metadata']['anchor_role']
        }
        if is_exc:
            exception_approved_fw_anchors.append(record)
        else:
            illegal_fw_anchors.append(record)
            
    # G. Unresolved Chunk Audit
    unresolved_uc_counter = Counter(u.get('usage_class', '') for u in unresolved)
    unresolved_cefr_counter = Counter(u.get('cefr_level', '') for u in unresolved)
    
    classified_unresolved = []
    reason_counter = Counter()
    for u in unresolved:
        norm = u['normalized_chunk'].lower()
        label = u['label'].lower()
        tokens = u['tokens']
        
        # Heuristics for classification
        if any(p in norm for p in ["sb's", "sth's", "sb", "sth", "etc"]):
            reason = "placeholder pattern"
        elif any(w in tokens for w in ["lay", "genetically", "inverted", "commas", "prospective"]):
            reason = "vocabulary missing"
        elif any(c in cl for cl in tokens for c in ["/", "-"]) or any(t.endswith('s') for t in tokens):
            reason = "morphology gap"
        elif u.get('usage_class') in ['idiom', 'social_expression']:
            reason = "idiom/formulaic opaque"
        elif any(t.endswith('l') for t in tokens):
            reason = "spelling variant"
        else:
            reason = "tokenization problem"
            
        reason_counter[reason] += 1
        classified_unresolved.append({
            "chunk": u['label'],
            "normalized": u['normalized_chunk'],
            "tokens": tokens,
            "classified_reason": reason
        })
        
    # H. Usage Class Coverage
    uc_edge_count = Counter(chunk_map[e['source_node_id']]['metadata'].get('usage_class', '') for e in edges)
    
    usage_classes_all = Counter(c['metadata'].get('usage_class', '') for c in chunks)
    uc_coverage = {}
    for uc, total in usage_classes_all.items():
        anchored = sum(1 for c in chunks if c['metadata'].get('usage_class', '') == uc and c['id'] in anchored_chunks)
        unres = sum(1 for u in unresolved if u.get('usage_class', '') == uc)
        uc_edges = [e for e in edges if chunk_map[e['source_node_id']]['metadata'].get('usage_class', '') == uc]
        low_conf_uc = sum(1 for e in uc_edges if e['confidence']['value'] < 0.70)
        
        uc_coverage[uc] = {
            "total": total,
            "anchored_count": anchored,
            "anchored_ratio": (anchored / total) * 100 if total else 0.0,
            "unresolved_count": unres,
            "unresolved_ratio": (unres / total) * 100 if total else 0.0,
            "low_confidence_ratio": (low_conf_uc / len(uc_edges)) * 100 if uc_edges else 0.0
        }
        
    # I. CEFR Coverage
    cefr_levels_all = Counter(c.get('cefr_level', '') for c in chunks)
    cefr_coverage = {}
    for cl, total in cefr_levels_all.items():
        anchored = sum(1 for c in chunks if c.get('cefr_level', '') == cl and c['id'] in anchored_chunks)
        unres = sum(1 for u in unresolved if u.get('cefr_level', '') == cl)
        cl_edges = [e for e in edges if chunk_map[e['source_node_id']].get('cefr_level', '') == cl]
        low_conf_cl = sum(1 for e in cl_edges if e['confidence']['value'] < 0.70)
        
        cefr_coverage[cl] = {
            "total": total,
            "anchored_count": anchored,
            "anchored_ratio": (anchored / total) * 100 if total else 0.0,
            "unresolved_count": unres,
            "unresolved_ratio": (unres / total) * 100 if total else 0.0,
            "low_confidence_ratio": (low_conf_cl / len(cl_edges)) * 100 if cl_edges else 0.0
        }
        
    # CEFR mismatch examples
    cefr_mismatches_high_to_low = []  # high-level chunk, easy vocabulary anchors
    cefr_mismatches_low_to_high = []  # low-level chunk, hard vocabulary anchors
    
    for c in chunks:
        cid = c['id']
        c_cefr = c.get('cefr_level')
        c_cefr_val = CEFR_ORDER.get(c_cefr, 99)
        c_edges = [e for e in edges if e['source_node_id'] == cid]
        if not c_edges:
            continue
            
        vocab_levels = [vocab_map[e['target_node_id']].get('cefr_level') for e in c_edges]
        vocab_vals = [CEFR_ORDER.get(lvl, 99) for lvl in vocab_levels if lvl]
        if not vocab_vals:
            continue
            
        max_vocab_val = max(vocab_vals)
        min_vocab_val = min(vocab_vals)
        
        # High-level chunk anchored to only A1/A2 vocab
        if c_cefr_val >= 5 and max_vocab_val <= 2:
            cefr_mismatches_high_to_low.append({
                "chunk": c['label'],
                "chunk_level": c_cefr,
                "vocab_anchors": [{"lemma": vocab_map[e['target_node_id']]['label'], "level": vocab_map[e['target_node_id']].get('cefr_level')} for e in c_edges]
            })
            
        # Low-level chunk anchored to C1/C2 vocab
        if c_cefr_val <= 2 and min_vocab_val >= 5:
            cefr_mismatches_low_to_high.append({
                "chunk": c['label'],
                "chunk_level": c_cefr,
                "vocab_anchors": [{"lemma": vocab_map[e['target_node_id']]['label'], "level": vocab_map[e['target_node_id']].get('cefr_level')} for e in c_edges]
            })
            
    # J. Theme Projection Readiness
    projected_theme_count = 0
    chunks_with_no_projectable = 0
    chunks_with_too_many_themes = 0
    too_many_threshold = 5
    
    for cid in anchored_chunks:
        c_edges = [e for e in edges if e['source_node_id'] == cid]
        themes = set()
        for e in c_edges:
            themes.update(vocab_to_themes.get(e['target_node_id'], []))
        if themes:
            projected_theme_count += 1
            if len(themes) > too_many_threshold:
                chunks_with_too_many_themes += 1
        else:
            chunks_with_no_projectable += 1
            
    projected_theme_ratio = (projected_theme_count / anchored_chunk_count) * 100 if anchored_chunk_count else 0.0
    
    # K. Morphology Assistance Audit
    morphology_resolvable_candidates = []
    for u in unresolved:
        tokens = u['tokens']
        # check if any token morphology target is in vocab
        resolvable = False
        details = []
        for tok in tokens:
            tok_lower = tok.lower()
            # Check standard inflections
            if tok_lower.endswith('s') and tok_lower[:-1] in vocab_lemmas:
                resolvable = True
                details.append(f"{tok} -> {tok_lower[:-1]} (plural/singular)")
            elif tok_lower.endswith('es') and tok_lower[:-2] in vocab_lemmas:
                resolvable = True
                details.append(f"{tok} -> {tok_lower[:-2]} (plural/singular)")
            elif tok_lower.endswith('ed') and tok_lower[:-2] in vocab_lemmas:
                resolvable = True
                details.append(f"{tok} -> {tok_lower[:-2]} (past/present)")
            elif tok_lower.endswith('ed') and tok_lower[:-1] in vocab_lemmas:
                resolvable = True
                details.append(f"{tok} -> {tok_lower[:-1]} (past/present)")
                
        if resolvable:
            morphology_resolvable_candidates.append({
                "chunk": u['label'],
                "tokens": tokens,
                "resolutions": details
            })
            
    # Structured Audit JSON Output
    audit_report = {
        "audit_stage": "ULGA-S6E",
        "basic_counts": {
            "chunk_node_count": chunk_node_count,
            "vocabulary_node_count": vocabulary_node_count,
            "edge_count": edge_count,
            "anchored_chunk_count": anchored_chunk_count,
            "unresolved_chunk_count": unresolved_chunk_count,
            "anchored_ratio": anchored_ratio,
            "unresolved_ratio": unresolved_ratio,
            "average_edges_per_chunk": average_edges,
            "unique_vocabulary_targets": unique_vocab_targets
        },
        "schema_integrity": {
            "all_source_are_chunks": all_source_are_chunks,
            "all_target_are_vocab": all_target_are_vocab,
            "all_uses": all_uses,
            "duplicate_edge_count": dup_count,
            "self_loop_count": self_loops,
            "missing_endpoint_count": missing_endpoints,
            "invalid_confidence_count": invalid_conf
        },
        "confidence_breakdown": confidence_breakdown,
        "confidence_ranges": {
            "high_confidence_count": high_conf,
            "high_confidence_ratio": high_conf / edge_count * 100 if edge_count else 0,
            "medium_confidence_count": med_conf,
            "medium_confidence_ratio": med_conf / edge_count * 100 if edge_count else 0,
            "low_confidence_count": low_conf,
            "low_confidence_ratio": low_conf / edge_count * 100 if edge_count else 0
        },
        "polysemy_risk": {
            "top_vocab_fallback": top_vocab_fallback[:10],
            "top_chunks_fallback": top_chunks_fallback[:10],
            "top_ambiguous_lemmas": top_ambiguous_lemmas[:10],
            "specific_lemma_audit": specific_lemma_audit,
            "fallback_heavy_usage_class": dict(fallback_uc_counter),
            "fallback_heavy_cefr": dict(fallback_cefr_counter)
        },
        "anchor_role": {
            "roles": dict(role_counter),
            "chunks_no_head_count": len(chunks_no_head),
            "chunks_no_head_examples": chunks_no_head[:10],
            "chunks_multiple_heads_count": len(chunks_multiple_heads),
            "chunks_multiple_heads_examples": chunks_multiple_heads[:10],
            "chunks_only_modifiers_count": len(chunks_only_modifiers),
            "chunks_only_modifiers_examples": chunks_only_modifiers[:10]
        },
        "function_word_leakage": {
            "function_word_anchor_count": function_word_anchor_count,
            "top_fw_anchors": dict(top_fw_anchors),
            "illegal_fw_anchors_count": len(illegal_fw_anchors),
            "illegal_fw_anchors_examples": illegal_fw_anchors[:20],
            "exception_approved_fw_anchors_count": len(exception_approved_fw_anchors)
        },
        "unresolved_chunk_audit": {
            "unresolved_chunk_count": unresolved_chunk_count,
            "unresolved_reasons": dict(reason_counter),
            "unresolved_usage_class": dict(unresolved_uc_counter),
            "unresolved_cefr": dict(unresolved_cefr_counter)
        },
        "usage_class_coverage": uc_coverage,
        "cefr_coverage": cefr_coverage,
        "cefr_mismatches": {
            "high_to_low_count": len(cefr_mismatches_high_to_low),
            "high_to_low_examples": cefr_mismatches_high_to_low[:10],
            "low_to_high_count": len(cefr_mismatches_low_to_high),
            "low_to_high_examples": cefr_mismatches_low_to_high[:10]
        },
        "theme_projection": {
            "projected_theme_count": projected_theme_count,
            "projected_theme_ratio": projected_theme_ratio,
            "chunks_with_no_projectable": chunks_with_no_projectable,
            "chunks_with_too_many_themes": chunks_with_too_many_themes
        },
        "morphology_assistance": {
            "resolvable_count": len(morphology_resolvable_candidates),
            "resolvable_examples": morphology_resolvable_candidates[:10]
        }
    }
    
    with open(OUTPUT_AUDIT_JSON, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2, ensure_ascii=False)
    print(f"Saved QA Audit report JSON to {OUTPUT_AUDIT_JSON}.")
    
    # Simple printout of key figures for markdown verification
    print("\nQA Audit Metrics Summary:")
    print(f"  Anchored Ratio: {anchored_ratio:.2f}%")
    print(f"  Unresolved Ratio: {unresolved_ratio:.2f}%")
    print(f"  Function word anchors count: {function_word_anchor_count}")
    print(f"  Illegal function word anchors: {len(illegal_fw_anchors)}")
    print(f"  Unresolved by reason: {dict(reason_counter)}")
    print(f"  Morphology resolvable candidates: {len(morphology_resolvable_candidates)}")
    print(f"  Projected Theme Coverage: {projected_theme_ratio:.2f}%")
    
if __name__ == "__main__":
    main()
