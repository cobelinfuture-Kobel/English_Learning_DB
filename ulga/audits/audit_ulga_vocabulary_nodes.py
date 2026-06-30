import json
import sys
from pathlib import Path
from collections import Counter

# Resolve paths
BASE_DIR = Path(__file__).resolve().parents[2]
VOCAB_SOURCE_JSON = BASE_DIR / "vocabulary" / "json" / "vocabulary.json"
VOCAB_NODES_JSON = BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json"
GRAPH_VOCAB_NODES_JSON = BASE_DIR / "ulga" / "graph" / "ulga_graph.vocabulary_nodes.json"
EVP_XLSX_PATH = BASE_DIR / "vocabulary" / "source" / "English Vocabulary Profile Online.xlsx"
NGSL_XLSX_PATH = BASE_DIR / "vocabulary" / "source" / "NGSL+with+SFI+(31K).xlsx"
REPORT_OUT_PATH = BASE_DIR / "ulga" / "reports" / "vocabulary_authority_qa_audit.json"

def calculate_median(lst):
    clean_lst = [x for x in lst if x is not None]
    n = len(clean_lst)
    if n == 0:
        return None
    sorted_lst = sorted(clean_lst)
    if n % 2 == 1:
        return sorted_lst[n // 2]
    else:
        return (sorted_lst[n // 2 - 1] + sorted_lst[n // 2]) / 2.0

def main():
    print("Starting read-only QA audit of vocabulary nodes...")
    
    # 1. Load Files
    if not VOCAB_SOURCE_JSON.exists():
        print(f"Error: {VOCAB_SOURCE_JSON} not found.")
        sys.exit(1)
    if not VOCAB_NODES_JSON.exists():
        print(f"Error: {VOCAB_NODES_JSON} not found.")
        sys.exit(1)
    if not GRAPH_VOCAB_NODES_JSON.exists():
        print(f"Error: {GRAPH_VOCAB_NODES_JSON} not found.")
        sys.exit(1)
        
    with open(VOCAB_SOURCE_JSON, "r", encoding="utf-8") as f:
        source_data = json.load(f)
        
    with open(VOCAB_NODES_JSON, "r", encoding="utf-8") as f:
        nodes = json.load(f)
        
    with open(GRAPH_VOCAB_NODES_JSON, "r", encoding="utf-8") as f:
        graph = json.load(f)
        
    # Check if excel files exist
    evp_xlsx_exists = EVP_XLSX_PATH.exists()
    ngsl_xlsx_exists = NGSL_XLSX_PATH.exists()
    
    # A. Basic Counts
    source_vocabulary_count = len(source_data)
    mounted_node_count = len(nodes)
    mounting_rate = mounted_node_count / source_vocabulary_count if source_vocabulary_count > 0 else 0
    edge_count = len(graph.get("edges", []))
    node_type_counts = Counter(n.get("node_type") for n in nodes)
    
    # B. ID / Sense Integrity
    node_ids = [n.get("id") for n in nodes]
    unique_node_ids = set(node_ids)
    unique_node_id_count = len(unique_node_ids)
    duplicate_node_id_count = len(node_ids) - unique_node_id_count
    
    source_vocab_ids = [n.get("metadata", {}).get("source_vocabulary_id") for n in nodes]
    unique_source_vocab_ids = set(source_vocab_ids)
    unique_source_vocabulary_id_count = len(unique_source_vocab_ids)
    duplicate_source_vocabulary_id_count = len(source_vocab_ids) - unique_source_vocabulary_id_count
    
    lemmas = [n.get("metadata", {}).get("canonical_lemma") for n in nodes]
    lemma_counts = Counter(lemmas)
    unique_lemma_count = len(lemma_counts)
    polysemy_lemma_count = sum(1 for lemma, count in lemma_counts.items() if count > 1)
    top_50_polysemy_lemmas = [{"lemma": k, "count": v} for k, v in lemma_counts.most_common(50)]
    
    # Check if all source vocab_ids exist in mounted nodes
    source_ids_set = {s.get("vocab_id") for s in source_data}
    mounted_ids_set = {n.get("metadata", {}).get("source_vocabulary_id") for n in nodes}
    sense_preservation_check = (mounted_node_count == source_vocabulary_count) and (source_ids_set == mounted_ids_set)
    
    # C. CEFR Coverage
    allowed_cefr = {"A1", "A2", "B1", "B2", "C1", "C2"}
    cefr_levels = [n.get("cefr_level") for n in nodes]
    cefr_counts = Counter(cefr_levels)
    
    missing_cefr_count = sum(1 for lvl in cefr_levels if lvl is None)
    invalid_cefr_count = sum(1 for lvl in cefr_levels if lvl is not None and lvl not in allowed_cefr)
    plus_level_misuse_count = sum(1 for lvl in cefr_levels if lvl is not None and ("plus" in str(lvl).lower() or "+" in str(lvl)))
    
    # D. POS / Usage Domain Coverage
    pos_list = [n.get("metadata", {}).get("part_of_speech") for n in nodes]
    pos_counts = Counter(pos_list)
    missing_pos_count = sum(1 for pos in pos_list if not pos or str(pos).strip() == "")
    
    usage_domains_list = []
    for n in nodes:
        ud = n.get("metadata", {}).get("usage_domains", [])
        if isinstance(ud, list):
            usage_domains_list.extend(ud)
        else:
            usage_domains_list.append(ud)
    usage_domains_counts = Counter(usage_domains_list)
    
    top_pos_categories = [{"pos": k if k else "<empty>", "count": v} for k, v in pos_counts.most_common()]
    pos_anomaly_examples = [n.get("id") for n in nodes if not n.get("metadata", {}).get("part_of_speech") or str(n.get("metadata", {}).get("part_of_speech")).strip() == ""]
    
    # E. Frequency Coverage
    freq_ranks = [n.get("metadata", {}).get("frequency_rank") for n in nodes]
    freq_scores = [n.get("metadata", {}).get("frequency_score") for n in nodes]
    
    freq_rank_populated = sum(1 for r in freq_ranks if r is not None)
    freq_score_populated = sum(1 for s in freq_scores if s is not None)
    missing_frequency_rank = len(nodes) - freq_rank_populated
    missing_frequency_score = len(nodes) - freq_score_populated
    
    valid_scores = [s for s in freq_scores if s is not None]
    freq_score_min = min(valid_scores) if valid_scores else None
    freq_score_max = max(valid_scores) if valid_scores else None
    freq_score_median = calculate_median(valid_scores)
    
    # Frequency coverage by CEFR level
    frequency_by_cefr = {}
    for lvl in sorted(list(allowed_cefr)):
        lvl_scores = [n.get("metadata", {}).get("frequency_score") for n in nodes if n.get("cefr_level") == lvl]
        lvl_ranks = [n.get("metadata", {}).get("frequency_rank") for n in nodes if n.get("cefr_level") == lvl]
        
        valid_lvl_scores = [s for s in lvl_scores if s is not None]
        valid_lvl_ranks = [r for r in lvl_ranks if r is not None]
        
        frequency_by_cefr[lvl] = {
            "node_count": len(lvl_scores),
            "populated_scores": len(valid_lvl_scores),
            "median_score": calculate_median(valid_lvl_scores),
            "populated_ranks": len(valid_lvl_ranks),
            "median_rank": calculate_median(valid_lvl_ranks)
        }
        
    # F. Theme Readiness
    theme_tags_counts = [len(n.get("metadata", {}).get("theme_tags", [])) for n in nodes]
    theme_tags_populated = sum(1 for c in theme_tags_counts if c > 0)
    theme_tags_empty = sum(1 for c in theme_tags_counts if c == 0)
    projected_theme_readiness_pct = (theme_tags_populated / len(nodes)) * 100 if len(nodes) > 0 else 0
    
    # Detect nodes with source topic but empty theme_tags
    nodes_with_source_topic_but_empty_theme = 0
    source_topics = []
    for r, n in zip(source_data, nodes):
        src_topic = r.get("topic")
        meta_theme_tags = n.get("metadata", {}).get("theme_tags", [])
        if src_topic and not meta_theme_tags:
            nodes_with_source_topic_but_empty_theme += 1
        if src_topic:
            source_topics.append(src_topic)
    top_source_topics = [{"topic": k, "count": v} for k, v in Counter(source_topics).most_common(20)]
    
    # G. Chunk Readiness
    chunk_counts = [n.get("metadata", {}).get("chunk_count") for n in nodes]
    chunk_count_populated = sum(1 for c in chunk_counts if c is not None)
    chunk_count_greater_than_zero = sum(1 for c in chunk_counts if c is not None and c > 0)
    chunk_count_equals_zero = sum(1 for c in chunk_counts if c is not None and c == 0)
    
    # Likely chunk anchors heuristic (high-frequency verbs and nouns)
    likely_chunk_anchors = []
    for n in nodes:
        meta = n.get("metadata", {})
        pos = meta.get("part_of_speech", "")
        rank = meta.get("frequency_rank")
        if pos in ["verb", "noun"] and rank is not None and rank <= 500:
            likely_chunk_anchors.append(n.get("id"))
            
    # H. Grammar Reference Safety
    grammar_prerequisites_exists = all("grammar_prerequisites" in n.get("metadata", {}) for n in nodes)
    grammar_prerequisites_populated = sum(1 for n in nodes if len(n.get("metadata", {}).get("grammar_prerequisites", [])) > 0)
    
    # I. Authority Source Coverage
    authority_source_populated = sum(1 for n in nodes if n.get("authority_source") is not None)
    evp_authority_coverage = sum(1 for n in nodes if "evp" in str(n.get("authority_source", {}).get("source_name", "")).lower())
    ngsl_sfi_auxiliary_coverage = sum(1 for n in nodes if "ngsl" in str(n.get("authority_source", {}).get("source_name", "")).lower())
    missing_authority_source = len(nodes) - authority_source_populated
    
    # J. Confidence / Versioning
    confidence_populated = sum(1 for n in nodes if n.get("confidence") is not None)
    confidence_values = [n.get("confidence", {}).get("value") for n in nodes]
    confidence_value_distribution = dict(Counter(confidence_values))
    version_populated = sum(1 for n in nodes if n.get("version") is not None)
    mounting_stage_counts = Counter(n.get("metadata", {}).get("mounting_stage") for n in nodes)
    
    # K. Graph Wrapper Integrity
    formal_data_mounted = graph.get("formal_data_mounted")
    mounted_stage = graph.get("mounted_stage")
    wrapper_edge_count = graph.get("edge_count")
    dependency_layer_implemented = graph.get("dependency_layer_implemented")
    theme_layer_implemented = graph.get("theme_layer_implemented")
    morphology_layer_implemented = graph.get("morphology_layer_implemented")
    
    # L. Risk Classification
    high_risk_issues = []
    medium_risk_issues = []
    low_risk_issues = []
    
    if duplicate_node_id_count > 0:
        high_risk_issues.append(f"Duplicate node IDs detected: {duplicate_node_id_count}")
    if duplicate_source_vocabulary_id_count > 0:
        high_risk_issues.append(f"Duplicate source vocabulary IDs detected: {duplicate_source_vocabulary_id_count}")
    if invalid_cefr_count > 0:
        high_risk_issues.append(f"Invalid CEFR levels detected: {invalid_cefr_count}")
    if source_vocabulary_count != mounted_node_count:
        high_risk_issues.append(f"Source count ({source_vocabulary_count}) does not match mounted count ({mounted_node_count})")
        
    if missing_pos_count > 0:
        medium_risk_issues.append(f"Nodes missing part_of_speech metadata: {missing_pos_count}")
    if missing_frequency_rank > 0 or missing_frequency_score > 0:
        medium_risk_issues.append(f"Nodes missing frequency rank/score: rank={missing_frequency_rank}, score={missing_frequency_score}")
    if missing_authority_source > 0:
        medium_risk_issues.append(f"Nodes missing authority source: {missing_authority_source}")
        
    if theme_tags_empty > 0:
        low_risk_issues.append(f"Nodes with empty theme_tags metadata: {theme_tags_empty} (expected in S5B)")
    if chunk_count_equals_zero > 0:
        low_risk_issues.append(f"Nodes with chunk_count = 0: {chunk_count_equals_zero} (expected in S5B)")
    if grammar_prerequisites_populated == 0:
        low_risk_issues.append("All grammar prerequisites are currently empty (expected in S5B)")
        
    # Verdict determination
    validator_passed = True # Evaluated out-of-script but set to pass if true
    pytest_passed = True
    
    is_fail = (
        duplicate_node_id_count > 0 or
        duplicate_source_vocabulary_id_count > 0 or
        invalid_cefr_count > 0 or
        source_vocabulary_count != mounted_node_count or
        edge_count > 0 or
        not sense_preservation_check
    )
    
    is_warning = (
        missing_frequency_rank > 0 or
        missing_frequency_score > 0 or
        missing_pos_count > 0 or
        theme_tags_populated == 0 or
        chunk_count_greater_than_zero == 0 or
        grammar_prerequisites_populated == 0
    )
    
    verdict = "FAIL" if is_fail else ("WARNING" if is_warning else "PASS")
    
    # Save Report
    report = {
        "verdict": verdict,
        "audit_timestamp": graph.get("version", {}).get("generated_at"),
        "basic_counts": {
            "source_vocabulary_count": source_vocabulary_count,
            "mounted_node_count": mounted_node_count,
            "mounting_rate": mounting_rate,
            "edge_count": edge_count,
            "node_type_counts": dict(node_type_counts)
        },
        "id_sense_integrity": {
            "unique_node_id_count": unique_node_id_count,
            "duplicate_node_id_count": duplicate_node_id_count,
            "unique_source_vocabulary_id_count": unique_source_vocabulary_id_count,
            "duplicate_source_vocabulary_id_count": duplicate_source_vocabulary_id_count,
            "unique_lemma_count": unique_lemma_count,
            "polysemy_lemma_count": polysemy_lemma_count,
            "top_50_polysemy_lemmas": top_50_polysemy_lemmas,
            "sense_preservation_check": sense_preservation_check
        },
        "cefr_coverage": {
            "counts": dict(cefr_counts),
            "missing_cefr_count": missing_cefr_count,
            "invalid_cefr_count": invalid_cefr_count,
            "plus_level_misuse_count": plus_level_misuse_count
        },
        "pos_usage_domain_coverage": {
            "part_of_speech_counts": dict(pos_counts),
            "missing_pos_count": missing_pos_count,
            "usage_domains_counts": dict(usage_domains_counts),
            "top_pos_categories": top_pos_categories,
            "pos_anomaly_examples": pos_anomaly_examples[:10]
        },
        "frequency_coverage": {
            "frequency_rank_populated": freq_rank_populated,
            "frequency_score_populated": freq_score_populated,
            "missing_frequency_rank": missing_frequency_rank,
            "missing_frequency_score": missing_frequency_score,
            "frequency_score_min": freq_score_min,
            "frequency_score_max": freq_score_max,
            "frequency_score_median": freq_score_median,
            "frequency_by_cefr": frequency_by_cefr
        },
        "theme_readiness": {
            "theme_tags_populated": theme_tags_populated,
            "theme_tags_empty": theme_tags_empty,
            "projected_theme_readiness_pct": projected_theme_readiness_pct,
            "nodes_with_source_topic_but_empty_theme": nodes_with_source_topic_but_empty_theme,
            "top_source_topics": top_source_topics
        },
        "chunk_readiness": {
            "chunk_count_populated": chunk_count_populated,
            "chunk_count_greater_than_zero": chunk_count_greater_than_zero,
            "chunk_count_equals_zero": chunk_count_equals_zero,
            "likely_chunk_anchors_sample": likely_chunk_anchors[:20]
        },
        "grammar_reference_safety": {
            "grammar_prerequisites_exists": grammar_prerequisites_exists,
            "grammar_prerequisites_populated": grammar_prerequisites_populated,
            "edge_count_in_graph": edge_count
        },
        "authority_source_coverage": {
            "authority_source_populated": authority_source_populated,
            "evp_authority_coverage": evp_authority_coverage,
            "ngsl_sfi_auxiliary_coverage": ngsl_sfi_auxiliary_coverage,
            "missing_authority_source": missing_authority_source
        },
        "confidence_versioning": {
            "confidence_populated": confidence_populated,
            "confidence_value_distribution": {str(k): v for k, v in confidence_value_distribution.items()},
            "version_populated": version_populated,
            "mounting_stage_counts": dict(mounting_stage_counts)
        },
        "graph_wrapper_integrity": {
            "formal_data_mounted": formal_data_mounted,
            "mounted_stage": mounted_stage,
            "wrapper_edge_count": wrapper_edge_count,
            "dependency_layer_implemented": dependency_layer_implemented,
            "theme_layer_implemented": theme_layer_implemented,
            "morphology_layer_implemented": morphology_layer_implemented
        },
        "source_files": {
            "evp_xlsx_exists": evp_xlsx_exists,
            "evp_xlsx_size_bytes": EVP_XLSX_PATH.stat().st_size if evp_xlsx_exists else 0,
            "ngsl_xlsx_exists": ngsl_xlsx_exists,
            "ngsl_xlsx_size_bytes": NGSL_XLSX_PATH.stat().st_size if ngsl_xlsx_exists else 0
        },
        "risk_classification": {
            "high_risk_issues": high_risk_issues,
            "medium_risk_issues": medium_risk_issues,
            "low_risk_issues": low_risk_issues
        }
    }
    
    # Ensure reports directory exists
    REPORT_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(REPORT_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print(f"Audit completed successfully. Verdict: {verdict}")
    print(f"Report written to {REPORT_OUT_PATH}")

if __name__ == "__main__":
    main()
