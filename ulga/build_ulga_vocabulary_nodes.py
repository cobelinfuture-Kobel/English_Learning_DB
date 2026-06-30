import json
import re
import sys
import unicodedata
from pathlib import Path
from datetime import datetime, timezone

# Resolve paths
BASE_DIR = Path(__file__).resolve().parents[1]
VOCAB_JSON_PATH = BASE_DIR / "vocabulary" / "json" / "vocabulary.json"
OUTPUT_DIR = BASE_DIR / "ulga" / "graph"
VOCAB_NODES_OUT_PATH = OUTPUT_DIR / "vocabulary_nodes.json"
GRAPH_VOCAB_NODES_OUT_PATH = OUTPUT_DIR / "ulga_graph.vocabulary_nodes.json"

def normalize_lemma(word):
    if not word:
        return ""
    # Normalize unicode to decompose accents, e.g. café -> cafe
    s = unicodedata.normalize('NFKD', word)
    s = "".join([c for c in s if not unicodedata.combining(c)])
    # Lowercase
    s = s.lower()
    # Replace space and slash with underscore
    s = re.sub(r'[\s/]+', '_', s)
    # Remove characters not allowed in ID (allowed: a-z, 0-9, _, ., :, -)
    s = re.sub(r'[^a-z0-9_.:-]', '', s)
    # Clean up double underscores
    s = re.sub(r'_{2,}', '_', s)
    s = s.strip('_')
    return s

def main():
    print("Loading vocabulary authority data...")
    if not VOCAB_JSON_PATH.exists():
        print(f"Error: Vocabulary file not found at {VOCAB_JSON_PATH}")
        sys.exit(1)
        
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    source_count = len(records)
    print(f"Loaded {source_count} vocabulary records.")
    
    nodes = []
    seen_ids = set()
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    for record in records:
        vocab_id = record.get("vocab_id", "")
        word = record.get("word", "")
        level = record.get("level")
        
        # 1. Normalize lemma and generate unique ID
        canonical_lemma = word
        normalized_lemma = normalize_lemma(word)
        node_id = f"vocabulary:{normalized_lemma}:{vocab_id}"
        
        if node_id in seen_ids:
            print(f"Warning: Duplicate node ID generated: {node_id}")
        seen_ids.add(node_id)
        
        # 2. Extract frequency fields
        frequency_rank = record.get("corpus_rank")
        if frequency_rank is not None:
            try:
                frequency_rank = int(frequency_rank)
            except (ValueError, TypeError):
                frequency_rank = None
                
        frequency_score = record.get("frequency_score")
        if frequency_score is not None:
            try:
                frequency_score = float(frequency_score)
            except (ValueError, TypeError):
                frequency_score = None
                
        part_of_speech = record.get("part_of_speech")
        source_rows = record.get("source_rows", [])
        source_row = source_rows[0] if isinstance(source_rows, list) and len(source_rows) > 0 else None
        
        # 3. Construct authority source object
        authority_source = {
            "source_name": "English Vocabulary Profile (EVP) / NGSL_SFI",
            "source_file": "vocabulary/json/vocabulary.json",
            "source_record_id": vocab_id,
            "source_row": source_row,
            "derivation": "derived_safe_layer"
        }
        
        # 4. Construct confidence object
        confidence = {
            "value": 1.0,
            "method": "rule_based",
            "notes": ["Mapped from derived safe vocabulary authority layer"]
        }
        
        # 5. Construct version object
        version = {
            "contract": "ULGA-S2",
            "source_version": "1.0.0",
            "generated_at": gen_time
        }
        
        # 6. Construct metadata object
        metadata = {
            "source_vocabulary_id": vocab_id,
            "canonical_lemma": canonical_lemma,
            "evp_level": level,
            "frequency_rank": frequency_rank,
            "frequency_score": frequency_score,
            "part_of_speech": part_of_speech,
            "theme_tags": [],
            "chunk_count": 0,
            "grammar_prerequisites": [],
            "version": "1.0.0",
            "mounting_stage": "ULGA-S5B",
            "usage_domains": [part_of_speech] if part_of_speech else []
        }
        
        node = {
            "id": node_id,
            "node_type": "vocabulary",
            "label": canonical_lemma,
            "authority_source": authority_source,
            "cefr_level": level,
            "confidence": confidence,
            "version": version,
            "metadata": metadata
        }
        
        nodes.append(node)
        
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write vocabulary nodes
    with open(VOCAB_NODES_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(nodes, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(nodes)} vocabulary nodes to {VOCAB_NODES_OUT_PATH}")
    
    # Write graph wrapper representation
    graph = {
        "graph_id": "ulga_graph.vocabulary_nodes",
        "contract_version": "ULGA-S2",
        "schema_version": "1.0.0",
        "formal_data_mounted": True,
        "mounted_stage": "ULGA-S5B",
        "nodes": nodes,
        "edges": [],
        "node_count": len(nodes),
        "edge_count": 0,
        "dependency_layer_implemented": False,
        "theme_layer_implemented": False,
        "morphology_layer_implemented": False,
        "metadata": {
            "purpose": "ULGA-S5B vocabulary node mounting fix",
            "data_policy": "vocabulary_nodes_only"
        },
        "validation_status": "untested"
    }
    
    with open(GRAPH_VOCAB_NODES_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    print(f"Wrote vocabulary graph wrapper to {GRAPH_VOCAB_NODES_OUT_PATH}")
    
    # Report counts
    print(f"Mounting Complete.")
    print(f"source count: {source_count}")
    print(f"mounted count: {len(nodes)}")

if __name__ == "__main__":
    main()
