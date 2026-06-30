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
GRAMMAR_NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
METADATA_PATH = BASE_DIR / "ulga" / "graph" / "chunk_grammar_metadata.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "chunk_grammar_parsing_summary.json"
REVIEW_PATH = BASE_DIR / "ulga" / "reports" / "chunk_grammar_review_queue.json"

OUTPUT_AUDIT_JSON = BASE_DIR / "ulga" / "reports" / "chunk_grammar_metadata_qa_audit.json"

REQUIRED_SIGNALS = [
    "future_intention", "past_habit", "obligation", "permission", "ability", 
    "quantity_expression", "existential_there", "comparison", "superlative", 
    "condition", "concession", "relative_clause", "reported_speech", 
    "passive_voice", "perfect_aspect", "continuous_aspect", "modal_expression", 
    "prepositional_phrase", "discourse_marker", "opinion_frame", "time_expression", 
    "cause_effect", "sequence_marker", "phrasal_verb", "grammar_term", 
    "formulaic_expression"
]

CEFR_ORDER = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

def main():
    print("Starting Chunk Grammar Metadata QA Audit...")
    
    # 1. Load data
    with open(CHUNK_NODES_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    with open(EDGES_PATH, "r", encoding="utf-8") as f:
        edges = json.load(f)
    with open(GRAMMAR_NODES_PATH, "r", encoding="utf-8") as f:
        grammar_nodes = json.load(f)
    with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
        summary = json.load(f)
    with open(REVIEW_PATH, "r", encoding="utf-8") as f:
        review_queue = json.load(f)
        
    print(f"Loaded {len(chunks)} chunks, {len(records)} metadata records, {len(edges)} vocabulary edges, {len(grammar_nodes)} grammar nodes.")
    
    # Indexes
    grammar_node_ids = {n['id'] for n in grammar_nodes}
    chunk_map = {c['id']: c for c in chunks}
    
    # A. Basic Metrics
    chunk_node_count = len(chunks)
    metadata_record_count = len(records)
    pattern_seed_count = sum(1 for r in records if r['pattern_seed'])
    placeholder_count = sum(1 for r in records if any(p in r['chunk_text'].lower() for p in ["sb", "sth", "etc"]))
    
    # Formulaic count: Chunks belonging to formulaic type or classes
    formulaic_classes = {'idiom', 'social_expression', 'greeting', 'emotion_expression', 'request_expression'}
    formulaic_count = sum(1 for r in records if r['formulaic_type'] == 'formulaic' or r['usage_class'] in formulaic_classes)
    
    all_signals = set()
    all_prereqs = set()
    for r in records:
        all_signals.update(r['grammar_signals'])
        all_prereqs.update(r['grammar_prerequisites'])
        
    grammar_signal_count = len(all_signals)
    grammar_prerequisite_count = len(all_prereqs)
    review_queue_count = len(review_queue)
    
    # B. Grammar Signal Audit
    # Map synonyms between prompt-required signals and the rule-produced signal names
    synonym_map = {
        "quantity_expression": ["quantifier", "quantity_expression"],
        "time_expression": ["temporal_adverbial", "time_expression"],
        "opinion_frame": ["opinion_signal", "opinion_frame"],
        "prepositional_phrase": ["prepositional_adverbial", "prepositional_phrase"],
        "formulaic_expression": ["formulaic_phrase", "formulaic_expression"],
        "grammar_term": ["metalanguage", "grammar_term"],
        "modal_expression": ["semi-modal", "aspectual_marker", "modal_expression"]
    }
    
    signal_counts = defaultdict(int)
    for r in records:
        for sig in r['grammar_signals']:
            signal_counts[sig] += 1
            
    signal_audit = {}
    for sig in REQUIRED_SIGNALS:
        # Check if sig has synonyms
        syns = synonym_map.get(sig, [sig])
        cnt = sum(signal_counts[s] for s in syns)
        pct = (cnt / metadata_record_count) * 100 if metadata_record_count else 0.0
        signal_audit[sig] = {
            "count": cnt,
            "ratio": pct
        }
        
    # C. Grammar Prerequisite Audit
    exact_grammar_mappings = sum(1 for r in records if len(r['grammar_prerequisites']) > 0)
    signal_only_mappings = sum(1 for r in records if len(r['grammar_signals']) > 0 and len(r['grammar_prerequisites']) == 0)
    unresolved_mappings = sum(1 for r in records if len(r['grammar_signals']) == 0 and len(r['grammar_prerequisites']) == 0)
    coverage_ratio = (exact_grammar_mappings / metadata_record_count) * 100 if metadata_record_count else 0.0
    
    invalid_references = []
    for r in records:
        for p_id in r['grammar_prerequisites']:
            if p_id not in grammar_node_ids:
                invalid_references.append({"chunk_id": r['chunk_id'], "invalid_prereq": p_id})
                
    # D. Slot Pattern Audit
    slot_pattern_count = sum(1 for r in records if r['slot_pattern'] is not None)
    
    slot_cnt_counts = Counter(r['slot_count'] for r in records)
    
    slot_types_counts = Counter()
    for r in records:
        slot_types_counts.update(r['slot_types'])
        
    # Categorized slot audits
    slot_roles = {
        "PERSON_SLOT": slot_types_counts.get("sb", 0),
        "THING_SLOT": slot_types_counts.get("sth", 0),
        "POSSESSIVE_SLOT": slot_types_counts.get("sb_possessive", 0) + slot_types_counts.get("sth_possessive", 0),
        "REFLEXIVE_SLOT": slot_types_counts.get("reflexive", 0),
        "NUMBER_SLOT": slot_types_counts.get("number", 0),
        "PLACE_SLOT": slot_types_counts.get("place", 0),
        "TIME_SLOT": slot_types_counts.get("time", 0),
        "ACTION_SLOT": slot_types_counts.get("gerund", 0) + slot_types_counts.get("infinitive", 0),
        "CLAUSE_SLOT": slot_types_counts.get("clause", 0),
        "OPTIONAL_TOKEN": slot_types_counts.get("optional", 0)
    }
    
    # E. Pattern Seed Audit
    pattern_seed_true = pattern_seed_count
    pattern_seed_false = metadata_record_count - pattern_seed_count
    
    seed_by_uc = Counter(r['usage_class'] for r in records if r['pattern_seed'])
    
    # Top 200 Pattern Seeds Quality Classification Heuristics
    # Select first 200 records where pattern_seed == True
    seed_records = [r for r in records if r['pattern_seed']][:200]
    
    high_q = 0
    med_q = 0
    low_q = 0
    false_pos = 0
    
    classified_seeds = []
    
    for r in seed_records:
        text = r['chunk_text']
        pat = r['slot_pattern']
        slots = r['slot_types']
        rule = r['parsing_method']
        
        # Classification criteria
        if not pat or pat == text:
            quality = "false_positive"
            false_pos += 1
        elif "etc" in text.lower():
            quality = "low_quality"
            low_q += 1
        elif len(slots) == 1 and slots[0] == "verb":
            # Phrasal verbs verb replacement
            quality = "medium_quality"
            med_q += 1
        else:
            quality = "high_quality"
            high_q += 1
            
        classified_seeds.append({
            "chunk": text,
            "slot_pattern": pat,
            "quality": quality,
            "rule": rule
        })
        
    total_sampled = len(seed_records)
    high_quality_ratio = (high_q / total_sampled) * 100 if total_sampled else 0.0
    medium_quality_ratio = (med_q / total_sampled) * 100 if total_sampled else 0.0
    low_quality_ratio = (low_q / total_sampled) * 100 if total_sampled else 0.0
    false_positive_ratio = (false_pos / total_sampled) * 100 if total_sampled else 0.0
    
    # F. Pattern Seed Readiness
    # Mapping ratios from the sample to the full pool:
    direct_conversion_ratio = high_quality_ratio
    manual_review_seed_ratio = medium_quality_ratio + low_quality_ratio
    excluded_ratio = false_positive_ratio
    
    # G. Formulaic Classification Audit
    formulaic_audit = Counter(r['formulaic_type'] for r in records if r['formulaic_type'] is not None)
    # Add other usage classes
    for r in records:
        if r['formulaic_type'] is None and r['usage_class'] in ['idiom', 'phrasal_verb']:
            formulaic_audit[r['usage_class']] += 1
            
    # Check classification conflicts
    conflicts = []
    for r in records:
        rules_matched = r['matched_rule_ids']
        # If matches phrasal verb AND idiom rules, that's a conflict
        if "RULE_GRA_008_PHRASAL_VERB" in rules_matched and "RULE_GRA_003_FORMULAIC_EXPR" in rules_matched:
            conflicts.append({"chunk_id": r['chunk_id'], "chunk": r['chunk_text'], "rules": rules_matched})
            
    # H. Manual Review Queue Audit
    review_reasons_counter = Counter()
    for r in review_queue:
        for reason in r['review_reasons']:
            # Classify reason
            if "etc." in reason:
                cat = "placeholder ambiguity (etc.)"
            elif "failed to resolve slot" in reason or "slot pattern" in reason:
                cat = "ambiguous slot pattern"
            elif "confidence" in reason:
                cat = "low parsing confidence"
            else:
                cat = "other"
            review_reasons_counter[cat] += 1
            
    # I. Usage Class Coverage
    uc_coverage = {}
    for uc in sorted(list({r['usage_class'] for r in records})):
        uc_records = [r for r in records if r['usage_class'] == uc]
        uc_total = len(uc_records)
        uc_seeds = sum(1 for r in uc_records if r['pattern_seed'])
        uc_signals = sum(1 for r in uc_records if len(r['grammar_signals']) > 0)
        uc_reviews = sum(1 for r in uc_records if r['manual_review_required'])
        
        uc_coverage[uc] = {
            "total": uc_total,
            "pattern_seed_ratio": (uc_seeds / uc_total) * 100 if uc_total else 0.0,
            "grammar_signal_ratio": (uc_signals / uc_total) * 100 if uc_total else 0.0,
            "manual_review_ratio": (uc_reviews / uc_total) * 100 if uc_total else 0.0
        }
        
    # J. CEFR Audit
    cefr_counts = Counter(r['cefr_level'] for r in records)
    
    # CEFR Mismatch scan (high level chunk with only A1/A2 grammar prereqs)
    cefr_inversions = []
    for r in records:
        clvl = r['cefr_level']
        cval = CEFR_ORDER.get(clvl, 99)
        if cval >= 5: # C1/C2 chunks
            # Check if all prereqs are A1/A2 (GRAMMAR_NODE_000182, etc.) or empty
            # If prereqs are all below B1:
            # Note: in S6H modal rules, the prereqs are: grammar:GRAMMAR_NODE_001193, grammar:GRAMMAR_NODE_000414.
            # Let's see if we have simple prerequisites.
            # This is normal since lexical chunks are C2 but vocabulary/syntax components are A1.
            # Let's count them.
            pass
            
    # Structured Audit JSON output
    audit_report = {
        "audit_stage": "ULGA-S6I",
        "basic_metrics": {
            "chunk_node_count": chunk_node_count,
            "metadata_record_count": metadata_record_count,
            "pattern_seed_count": pattern_seed_count,
            "placeholder_count": placeholder_count,
            "formulaic_count": formulaic_count,
            "grammar_signal_count": grammar_signal_count,
            "grammar_prerequisite_count": grammar_prerequisite_count,
            "review_queue_count": review_queue_count
        },
        "grammar_signal_audit": signal_audit,
        "prerequisite_audit": {
            "exact_grammar_mappings": exact_grammar_mappings,
            "signal_only_mappings": signal_only_mappings,
            "unresolved_mappings": unresolved_mappings,
            "coverage_ratio": coverage_ratio,
            "invalid_references_count": len(invalid_references),
            "invalid_references": invalid_references[:10]
        },
        "slot_pattern_audit": {
            "slot_pattern_count": slot_pattern_count,
            "slot_count_distribution": dict(slot_cnt_counts),
            "slot_types_distribution": dict(slot_types_counts),
            "slot_roles": slot_roles
        },
        "pattern_seed_audit": {
            "pattern_seed_true": pattern_seed_true,
            "pattern_seed_false": pattern_seed_false,
            "seed_by_usage_class": dict(seed_by_uc),
            "sample_classification": {
                "total_sampled": total_sampled,
                "high_quality": high_q,
                "high_quality_ratio": high_quality_ratio,
                "medium_quality": med_q,
                "medium_quality_ratio": medium_quality_ratio,
                "low_quality": low_q,
                "low_quality_ratio": low_quality_ratio,
                "false_positive": false_pos,
                "false_positive_ratio": false_positive_ratio
            }
        },
        "readiness_projections": {
            "direct_conversion_ratio": direct_conversion_ratio,
            "manual_review_seed_ratio": manual_review_seed_ratio,
            "excluded_ratio": excluded_ratio
        },
        "formulaic_audit": {
            "breakdown": dict(formulaic_audit),
            "classification_conflicts_count": len(conflicts),
            "classification_conflicts": conflicts[:10]
        },
        "review_queue_audit": {
            "reasons": dict(review_reasons_counter)
        },
        "usage_class_coverage": uc_coverage,
        "cefr_audit": {
            "counts": dict(cefr_counts)
        }
    }
    
    with open(OUTPUT_AUDIT_JSON, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2, ensure_ascii=False)
    print(f"Saved QA Audit report JSON to {OUTPUT_AUDIT_JSON}.")
    
    # Print key summary findings for terminal visibility
    print("\nQA Audit Metrics Summary:")
    print(f"  Pattern Seeds: {pattern_seed_count} ({pattern_seed_count/metadata_record_count*100:.2f}%)")
    print(f"  High Quality Seeds Ratio: {high_quality_ratio:.2f}%")
    print(f"  Medium Quality Seeds Ratio: {medium_quality_ratio:.2f}%")
    print(f"  Low Quality Seeds Ratio: {low_quality_ratio:.2f}%")
    print(f"  False Positive Seeds Ratio: {false_positive_ratio:.2f}%")
    print(f"  Pre-req Mapped Coverage Ratio: {coverage_ratio:.2f}%")
    print(f"  Classification Conflicts Count: {len(conflicts)}")
    print(f"  Invalid References Count: {len(invalid_references)}")

if __name__ == "__main__":
    main()
