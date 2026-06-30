import json
import os
import sys
from pathlib import Path

# Setup base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

METADATA_PATH = BASE_DIR / "ulga" / "graph" / "chunk_grammar_metadata.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "chunk_grammar_parsing_summary.json"

def validate():
    print("Validating Chunk Grammar Metadata layer...")
    
    # 1. Check file existence
    if not METADATA_PATH.exists():
        print(f"FAIL: Derived metadata file does not exist at {METADATA_PATH}")
        return False
    if not SUMMARY_PATH.exists():
        print(f"FAIL: Parsing summary file does not exist at {SUMMARY_PATH}")
        return False
        
    # 2. Load data
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)
    except Exception as e:
        print(f"FAIL: Failed to parse metadata JSON: {e}")
        return False
        
    try:
        with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
            summary = json.load(f)
    except Exception as e:
        print(f"FAIL: Failed to parse summary JSON: {e}")
        return False
        
    # 3. Check counts
    record_count = len(records)
    if record_count != 3522:
        print(f"FAIL: Expected 3,522 records, but found {record_count}.")
        return False
    if summary.get("parsed_metadata_count") != record_count:
        print("FAIL: Summary parsed_metadata_count does not match actual record count.")
        return False
        
    # 4. Check individual records
    for idx, rec in enumerate(records):
        cid = rec.get("chunk_id")
        text = rec.get("chunk_text")
        signals = rec.get("grammar_signals")
        prereqs = rec.get("grammar_prerequisites")
        slot_pat = rec.get("slot_pattern")
        slot_cnt = rec.get("slot_count")
        slot_t = rec.get("slot_types")
        seed = rec.get("pattern_seed")
        conf = rec.get("parsing_confidence")
        rev_req = rec.get("manual_review_required")
        reasons = rec.get("review_reasons")
        stage = rec.get("mounting_stage")
        
        # Check IDs
        if not cid or not cid.startswith("chunk:"):
            print(f"FAIL: Record at index {idx} has invalid chunk_id '{cid}'.")
            return False
        if not text:
            print(f"FAIL: Record {cid} has no chunk_text.")
            return False
            
        # Check arrays
        if not isinstance(signals, list):
            print(f"FAIL: Record {cid} grammar_signals must be a list.")
            return False
        if not isinstance(prereqs, list):
            print(f"FAIL: Record {cid} grammar_prerequisites must be a list.")
            return False
        if not isinstance(slot_t, list):
            print(f"FAIL: Record {cid} slot_types must be a list.")
            return False
            
        # Check slot consistency
        if seed:
            if not slot_pat:
                print(f"FAIL: Record {cid} is marked as pattern_seed but has empty slot_pattern.")
                return False
            if slot_cnt < 1:
                print(f"FAIL: Record {cid} is marked as pattern_seed but slot_count is {slot_cnt}.")
                return False
            if len(slot_t) != slot_cnt:
                print(f"FAIL: Record {cid} slot_types size ({len(slot_t)}) does not match slot_count ({slot_cnt}).")
                return False
        else:
            if slot_pat is not None and usage_class != "phrasal_verb": # phrasal verbs can have slot patterns without being seeds
                pass # fine
                
        # Check confidence
        if conf is None or not (0.0 <= conf <= 1.0):
            print(f"FAIL: Record {cid} parsing_confidence must be between 0.0 and 1.0 (got {conf}).")
            return False
            
        # Check review fields
        if rev_req:
            if not isinstance(reasons, list) or len(reasons) == 0:
                print(f"FAIL: Record {cid} manual_review_required is True, but review_reasons is empty.")
                return False
        else:
            if isinstance(reasons, list) and len(reasons) > 0:
                print(f"FAIL: Record {cid} manual_review_required is False, but review_reasons has items.")
                return False
                
        # Check stage
        if stage != "ULGA-S6H":
            print(f"FAIL: Record {cid} mounting_stage must be 'ULGA-S6H' (got '{stage}').")
            return False
            
    print("ULGA chunk grammar metadata validation: PASS")
    return True

if __name__ == "__main__":
    success = validate()
    if not success:
        sys.exit(1)
