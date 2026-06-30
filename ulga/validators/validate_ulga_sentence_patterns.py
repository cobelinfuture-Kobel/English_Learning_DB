import json
import os
import sys
import re
from pathlib import Path

# Setup base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

NODES_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"
EDGES_PATH = BASE_DIR / "ulga" / "graph" / "ulga_sentence_pattern_edges.json"
GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "ulga_sentence_pattern_nodes.json"

GRAMMAR_NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
CHUNK_NODES_PATH = BASE_DIR / "ulga" / "graph" / "chunk_nodes.json"
THEME_NODES_PATH = BASE_DIR / "ulga" / "graph" / "theme_nodes.json"

ALLOWED_CEFR = {"A1", "A1_plus", "A2", "A2_plus", "B1", "B1_plus", "B2", "B2_plus", "C1", "C2", None}
ALLOWED_RELATIONS = {"prerequisite", "supports", "belongs_to", "unlocks", "reviews", "contrasts_with", "uses", "contains", "spiral_to", "assesses"}
ALLOWED_STATUS = {"accepted", "needs_review", "blocked"}

def extract_placeholder_labels(pattern):
    if not isinstance(pattern, str):
        return []
    return [label.strip() for label in re.findall(r"\{([^{}]+)\}", pattern) if label.strip()]

def has_malformed_placeholders(pattern):
    if not isinstance(pattern, str):
        return True
    if "{}" in pattern or "{{" in pattern or "}}" in pattern:
        return True
    return pattern.count("{") != pattern.count("}")

def validate():
    print("Validating Sentence Pattern Authority layer...")
    
    # 1. Check file existence
    for path in [NODES_PATH, EDGES_PATH, GRAPH_PATH]:
        if not path.exists():
            print(f"FAIL: File does not exist at {path}")
            return False
            
    # 2. Load data
    try:
        with open(NODES_PATH, "r", encoding="utf-8") as f:
            nodes = json.load(f)
    except Exception as e:
        print(f"FAIL: Failed to parse sentence_patterns.json: {e}")
        return False
        
    try:
        with open(EDGES_PATH, "r", encoding="utf-8") as f:
            edges = json.load(f)
    except Exception as e:
        print(f"FAIL: Failed to parse ulga_sentence_pattern_edges.json: {e}")
        return False
        
    try:
        with open(GRAPH_PATH, "r", encoding="utf-8") as f:
            graph = json.load(f)
    except Exception as e:
        print(f"FAIL: Failed to parse graph wrapper JSON: {e}")
        return False

    # Load target nodes for validation
    grammar_nodes = {n["id"] for n in load_json(GRAMMAR_NODES_PATH)}
    chunk_nodes = {n["id"] for n in load_json(CHUNK_NODES_PATH)}
    theme_nodes = {n["id"] for n in load_json(THEME_NODES_PATH)}
    
    # Track node and SP IDs for duplicates
    node_ids = set()
    sp_ids = set()
    manual_pattern_count = 0
    
    # 3. Check individual records
    for idx, node in enumerate(nodes):
        nid = node.get("id")
        ntype = node.get("node_type")
        label = node.get("label")
        metadata = node.get("metadata", {})
        
        # Check rule 1: All node IDs must start with pattern:
        if not nid or not nid.startswith("pattern:"):
            print(f"FAIL: Node at index {idx} has invalid ID: {nid}")
            return False
            
        # Check rule 2: node_type must be sentence_pattern
        if ntype != "sentence_pattern":
            print(f"FAIL: Node {nid} has invalid node_type: {ntype}")
            return False
            
        # Check node ID uniqueness
        if nid in node_ids:
            print(f"FAIL: Duplicate node ID: {nid}")
            return False
        node_ids.add(nid)
        
        # Check rule 3: SP id must be unique (stored in metadata.pattern_id or authority_source.source_record_id)
        source_rec = node.get("authority_source", {}).get("source_record_id")
        if not source_rec or not source_rec.startswith("SP_"):
            print(f"FAIL: Node {nid} has missing or invalid SP source_record_id: {source_rec}")
            return False
        if source_rec in sp_ids:
            print(f"FAIL: Duplicate SP ID: {source_rec}")
            return False
        sp_ids.add(source_rec)
        
        # Check rule 4 & 5: canonical and normalized pattern must be non-empty
        canonical = metadata.get("canonical_pattern")
        normalized = metadata.get("normalized_pattern")
        if not canonical:
            print(f"FAIL: Node {nid} canonical_pattern is empty.")
            return False
        if not normalized:
            print(f"FAIL: Node {nid} normalized_pattern is empty.")
            return False
            
        # Check label is equal to canonical
        if label != canonical:
            print(f"FAIL: Node {nid} label '{label}' does not match canonical_pattern '{canonical}'.")
            return False
            
        # Check rule 6: cefr_level must be valid
        cefr = node.get("cefr_level")
        if cefr not in ALLOWED_CEFR:
            print(f"FAIL: Node {nid} has invalid cefr_level: {cefr}")
            return False
            
        # Check rule 7: slots must be list
        slots = metadata.get("slots")
        if not isinstance(slots, list):
            print(f"FAIL: Node {nid} slots is not a list.")
            return False
            
        # Check slot structure
        for s_idx, slot in enumerate(slots):
            if not isinstance(slot, dict) or "slot_id" not in slot or "slot_type" not in slot:
                print(f"FAIL: Node {nid} slot at index {s_idx} is missing required fields.")
                return False
            slot_label = slot.get("slot_label")
            slot_type = slot.get("slot_type")
            if not isinstance(slot_label, str) or not slot_label.strip():
                print(f"FAIL: Node {nid} slot at index {s_idx} has empty slot_label.")
                return False
            if "/" in slot_label:
                allowed_slot_types = slot.get("allowed_slot_types")
                if slot_type != "multi_type":
                    print(f"FAIL: Node {nid} slash slot '{slot_label}' must use slot_type='multi_type'.")
                    return False
                if not isinstance(allowed_slot_types, list) or len(allowed_slot_types) < 2:
                    print(f"FAIL: Node {nid} slash slot '{slot_label}' must define >=2 allowed_slot_types.")
                    return False
                if any(not isinstance(item, str) or not item.strip() for item in allowed_slot_types):
                    print(f"FAIL: Node {nid} slash slot '{slot_label}' has invalid allowed_slot_types members.")
                    return False
            elif "allowed_slot_types" in slot:
                print(f"FAIL: Node {nid} non-slash slot '{slot_label}' should not define allowed_slot_types.")
                return False

        # Check rule 8 & 9: generator_allowed and validator_required must be boolean
        gen_allowed = metadata.get("generator_allowed")
        val_required = metadata.get("validator_required")
        if not isinstance(gen_allowed, bool):
            print(f"FAIL: Node {nid} generator_allowed is not a boolean: {type(gen_allowed)}")
            return False
        if not isinstance(val_required, bool):
            print(f"FAIL: Node {nid} validator_required is not a boolean: {type(val_required)}")
            return False
            
        # Check rule 10: review_status must be accepted / needs_review / blocked
        status = metadata.get("review_status")
        if status not in ALLOWED_STATUS:
            print(f"FAIL: Node {nid} has invalid review_status: {status}")
            return False

        placeholder_labels = extract_placeholder_labels(canonical)
        malformed_placeholders = has_malformed_placeholders(canonical)
        if malformed_placeholders and status == "accepted":
            print(f"FAIL: Node {nid} accepted canonical_pattern contains malformed placeholders: {canonical}")
            return False
        if not malformed_placeholders and placeholder_labels and len(slots) != len(placeholder_labels):
            print(f"FAIL: Node {nid} placeholder count does not match slots count.")
            return False

        if status == "accepted" and gen_allowed and len(slots) == 0:
            print(f"FAIL: Node {nid} is accepted and generator_allowed but has empty slots.")
            return False

        # Check rule 15: chunk-derived patterns with parsing issues must be needs_review
        source = metadata.get("source")
        if source == "CHUNK_GRAMMAR_METADATA_DERIVED":
            if not canonical or len(slots) == 0 or malformed_placeholders:
                if status != "needs_review":
                    print(f"FAIL: Node {nid} is chunk-derived with missing slot pattern or empty slots, but review_status is '{status}'.")
                    return False
        elif source == "MANUAL_A1_CORE_PATTERN":
            manual_pattern_count += 1
            if len(slots) == 0:
                print(f"FAIL: Manual A1 core pattern {nid} has empty slots.")
                return False
        else:
            print(f"FAIL: Node {nid} has unknown source: {source}")
            return False
            
    # Check rule 14: manual A1 core patterns must all exist (17 patterns defined)
    if manual_pattern_count != 17:
        print(f"FAIL: Expected exactly 17 manual A1 core patterns, but found {manual_pattern_count}.")
        return False
        
    # Check rule 11, 12, 13: Edge validations
    edge_ids = set()
    valid_target_prefixes = {"grammar", "vocabulary", "chunk", "theme", "sentence_pattern", "skill", "pattern"}
    
    for idx, edge in enumerate(edges):
        eid = edge.get("id")
        src = edge.get("source_node_id")
        tgt = edge.get("target_node_id")
        rel = edge.get("edge_type")
        
        # Verify edge ID starting with edge:
        if not eid or not eid.startswith("edge:"):
            print(f"FAIL: Edge at index {idx} has invalid ID: {eid}")
            return False
            
        # Unique edge ID
        if eid in edge_ids:
            print(f"FAIL: Duplicate edge ID: {eid}")
            return False
        edge_ids.add(eid)
        
        # Verify relation is valid in schema
        if rel not in ALLOWED_RELATIONS:
            print(f"FAIL: Edge {eid} has invalid relation: {rel}")
            return False
            
        # Check rule 11: edges prefix must be valid
        src_prefix = src.split(":")[0] if src and ":" in src else None
        tgt_prefix = tgt.split(":")[0] if tgt and ":" in tgt else None
        if src_prefix != "pattern":
            print(f"FAIL: Edge {eid} source prefix must be pattern: (got '{src_prefix}').")
            return False
        if tgt_prefix not in valid_target_prefixes:
            print(f"FAIL: Edge {eid} target prefix '{tgt_prefix}' is invalid.")
            return False
            
        # Check rule 13: Target node must exist unless deferred_edges is used
        # Note: If target node exists in our indexes, it's valid. If not, it shouldn't be here.
        if src not in node_ids:
            print(f"FAIL: Edge {eid} source pattern node does not exist: {src}")
            return False
            
        # Verify target node existence
        target_exists = False
        if tgt_prefix == "grammar" and tgt in grammar_nodes:
            target_exists = True
        elif tgt_prefix == "chunk" and tgt in chunk_nodes:
            target_exists = True
        elif tgt_prefix == "theme" and tgt in theme_nodes:
            target_exists = True
        elif (tgt_prefix == "sentence_pattern" or tgt_prefix == "pattern") and tgt in node_ids:
            target_exists = True
            
        if not target_exists:
            print(f"FAIL: Edge {eid} target node does not exist in graph database: {tgt}")
            return False
            
    # Verify graph wrapper consistency
    if len(graph.get("nodes", [])) != len(nodes):
        print("FAIL: Graph wrapper nodes count does not match raw nodes count.")
        return False
    if len(graph.get("edges", [])) != len(edges):
        print("FAIL: Graph wrapper edges count does not match raw edges count.")
        return False
    if graph.get("graph_id") != "ulga_graph.sentence_patterns":
        print(f"FAIL: Graph wrapper graph_id must be 'ulga_graph.sentence_patterns' (got '{graph.get('graph_id')}').")
        return False
        
    print("Sentence Pattern Authority validation: PASS")
    return True

def load_json(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

if __name__ == "__main__":
    success = validate()
    if not success:
        sys.exit(1)
