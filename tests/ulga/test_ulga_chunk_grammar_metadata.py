import json
from pathlib import Path
from ulga.validators.validate_ulga_chunk_grammar_metadata import validate, METADATA_PATH, SUMMARY_PATH

def test_grammar_metadata_files_exist():
    assert METADATA_PATH.exists(), f"Derived metadata file not found at {METADATA_PATH}"
    assert SUMMARY_PATH.exists(), f"Summary file not found at {SUMMARY_PATH}"

def test_grammar_metadata_record_count():
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    assert len(records) == 3522, f"Expected 3,522 records, got {len(records)}"

def test_grammar_metadata_consistency():
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    for r in records:
        if r.get("pattern_seed"):
            assert r.get("slot_pattern") is not None
            assert r.get("slot_count") >= 1
            assert len(r.get("slot_types")) == r.get("slot_count")
            
        if r.get("manual_review_required"):
            assert len(r.get("review_reasons")) > 0
        else:
            assert len(r.get("review_reasons")) == 0

def test_grammar_metadata_validator_pass():
    assert validate() is True, "Grammar metadata validator failed"
