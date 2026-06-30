import json
import re
from pathlib import Path
from datetime import datetime, timezone

# Resolve paths
BASE_DIR = Path(__file__).resolve().parents[1]
GRAMMAR_PROFILE_PATH = BASE_DIR / "grammar_profile" / "json" / "grammar_profile.json"
OUTPUT_DIR = BASE_DIR / "ulga" / "graph"
GRAMMAR_NODES_OUT_PATH = OUTPUT_DIR / "grammar_nodes.json"
GRAPH_GRAMMAR_NODES_OUT_PATH = OUTPUT_DIR / "ulga_graph.grammar_nodes.json"

def slugify(text):
    if not text:
        return ""
    # Lowercase, replace non-alphanumeric with underscores, strip extra underscores
    t = text.lower()
    t = re.sub(r'[^a-z0-9]+', '_', t)
    t = t.strip('_')
    t = re.sub(r'_{2,}', '_', t)
    return t

def generate_canonical_key(record, seen_keys):
    super_cat = slugify(record.get("super_category", ""))
    sub_cat = slugify(record.get("sub_category", ""))
    guideword = slugify(record.get("guideword", ""))
    level = slugify(record.get("level", ""))
    
    # Base pattern: egp_super_sub_guideword_level
    base = f"egp_{super_cat}_{sub_cat}_{guideword}_{level}"
    
    key = base
    suffix = 1
    while key in seen_keys:
        key = f"{base}_{suffix}"
        suffix += 1
    seen_keys.add(key)
    return key

def main():
    print("Loading grammar profile...")
    with open(GRAMMAR_PROFILE_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    
    print(f"Loaded {len(records)} grammar profile records.")
    
    nodes = []
    seen_keys = set()
    
    # Current timestamp for version
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    for idx, record in enumerate(records, 1):
        # 1. Generate ID
        node_id = f"grammar:GRAMMAR_NODE_{idx:06d}"
        
        # 2. Label
        guideword = record.get("guideword", "")
        sub_cat = record.get("sub_category", "")
        super_cat = record.get("super_category", "")
        src_id = record.get("id", "")
        
        label = ""
        if guideword and guideword.strip():
            label = guideword.strip()
        elif sub_cat and sub_cat.strip():
            label = sub_cat.strip()
        elif super_cat and super_cat.strip():
            label = super_cat.strip()
        else:
            label = src_id.strip()
            
        # 3. Canonical key
        canonical_key = generate_canonical_key(record, seen_keys)
        
        # 4. Construct authority source object
        authority_source = {
            "source_name": "English Grammar Profile",
            "source_file": "grammar_profile/json/grammar_profile.json",
            "source_record_id": src_id,
            "source_row": record.get("source_row"),
            "derivation": "source_direct"
        }
        
        # 5. Construct confidence object
        confidence = {
            "value": 1.0,
            "method": "authority_source_trust",
            "notes": ["Official English Grammar Profile record"]
        }
        
        # 6. Construct version object
        version = {
            "contract": "ULGA-S2",
            "source_version": "1.0.0",
            "generated_at": gen_time
        }
        
        # 7. Construct metadata object
        metadata = {
            "source_record_id": src_id,
            "canonical_grammar_key": canonical_key,
            "grammar_family": super_cat,
            "grammar_subtype": sub_cat,
            "skill_domain": "grammar",
            "guideword": guideword,
            "can_do_statement": record.get("can_do_statement", ""),
            "raw_level": record.get("level", ""),
            "source_file": "grammar_profile/json/grammar_profile.json",
            "mounting_stage": "ULGA-S4A",
            "dependency_edges_mounted": False,
            "example": record.get("example", ""),
            "lexical_range": record.get("lexical_range", "")
        }
        
        node = {
            "id": node_id,
            "node_type": "grammar",
            "label": label,
            "authority_source": authority_source,
            "cefr_level": record.get("level"),
            "confidence": confidence,
            "version": version,
            "metadata": metadata
        }
        nodes.append(node)
        
    # Write nodes output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(GRAMMAR_NODES_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(nodes, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(nodes)} grammar nodes to {GRAMMAR_NODES_OUT_PATH}")
    
    # Write graph output
    graph = {
        "graph_id": "ulga_graph.grammar_nodes",
        "contract_version": "ULGA-S2",
        "schema_version": "1.0.0",
        "formal_data_mounted": True,
        "mounted_stage": "ULGA-S4A",
        "nodes": nodes,
        "edges": [],
        "node_count": len(nodes),
        "edge_count": 0,
        "metadata": {
            "purpose": "ULGA-S4A grammar node mounting fix",
            "data_policy": "grammar_nodes_only"
        },
        "validation_status": "untested"
    }
    with open(GRAPH_GRAMMAR_NODES_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    print(f"Wrote graph representation to {GRAPH_GRAMMAR_NODES_OUT_PATH}")

if __name__ == "__main__":
    main()
