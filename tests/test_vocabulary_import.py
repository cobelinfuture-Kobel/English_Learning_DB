import os
import json
import pytest

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB_JSON_PATH = os.path.join(BASE_DIR, "vocabulary", "json", "vocabulary.json")
REPORT_PATH = os.path.join(BASE_DIR, "output", "reports", "vocab_import_report.json")
LEVEL_MAPPING_PATH = os.path.join(BASE_DIR, "vocabulary", "mapping", "vocabulary_level_mapping.json")
TOPIC_MAPPING_PATH = os.path.join(BASE_DIR, "vocabulary", "mapping", "topic_mapping.json")

def test_vocabulary_json_exists():
    """Test that vocabulary.json exists."""
    assert os.path.exists(VOCAB_JSON_PATH), "vocabulary.json file does not exist"

def test_row_count_preserved():
    """Test that all 15696 raw rows are preserved in the JSON output."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    assert len(records) == 15696, f"Expected 15696 rows, but got {len(records)}"

def test_required_keys_exist():
    """Test that all records contain all required database and recovery metadata keys."""
    required_keys = {
        "vocab_id", "word", "guideword", "level", "details",
        "raw_topic", "raw_pos", "topic", "topic_status",
        "part_of_speech", "pos_status", "duplicate_status",
        "recovery_method", "recovery_confidence", "review_required",
        "lexical_type", "frequency_band", "exam_tags",
        "theme_candidates", "active"
    }
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    for r in records:
        missing_keys = required_keys - set(r.keys())
        assert not missing_keys, f"Record with ID {r.get('vocab_id')} is missing keys: {missing_keys}"

def test_duplicate_policy_correct():
    """Test that duplicate policy is correctly enforced (redundant rows are active=false)."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    canonical_rows = [r for r in records if r["duplicate_status"] == "canonical"]
    redundant_rows = [r for r in records if r["duplicate_status"] == "redundant"]
    
    # Check duplicate status values
    for r in records:
        assert r["duplicate_status"] in ["canonical", "redundant"], f"Invalid duplicate status: {r['duplicate_status']}"
        
    # Check that all redundant rows are inactive
    for r in redundant_rows:
        assert r["active"] is False, f"Redundant row {r['vocab_id']} should be inactive"

def test_recovery_metadata_present():
    """Test that recovery metadata fields are populated correctly."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    for r in records:
        assert r["topic_status"] in ["natively_populated", "recovered", "unmapped"]
        assert r["pos_status"] in ["natively_populated", "recovered", "unmapped"]
        assert r["recovery_confidence"] in ["none", "high", "medium", "low"]
        assert isinstance(r["review_required"], bool)
        assert isinstance(r["active"], bool)

def test_active_rule_enforced():
    """Test that active=true is only allowed if canonical, level != C2, and topic/pos are resolved."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    for r in records:
        if r["active"]:
            assert r["duplicate_status"] == "canonical", "Active row must be canonical"
            assert r["level"].lower() != "c2", "Active row cannot be C2"
            assert r["topic"] != "", "Active row must have a non-empty topic"
            assert r["topic_status"] != "unmapped", "Active row cannot have unmapped topic"
            assert r["part_of_speech"] != "", "Active row must have a non-empty part of speech"
            assert r["pos_status"] != "unmapped", "Active row cannot have unmapped part of speech"

def test_c2_inactive():
    """Test that C2 rows are present but inactive."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    c2_rows = [r for r in records if r["level"].lower() == "c2"]
    assert len(c2_rows) > 0, "C2 rows should be present"
    for r in c2_rows:
        assert r["active"] is False, "All C2 rows must be inactive"

def test_report_counts_consistent():
    """Test that report counts are consistent with each other and the JSON database."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)
        
    # Check counts against JSON
    assert report["total_rows"] == len(records), "Total rows mismatch"
    assert report["imported_rows"] == len(records), "Imported rows mismatch"
    
    actual_active = sum(1 for r in records if r["active"])
    assert report["active_rows"] == actual_active, "Active rows count mismatch"
    
    actual_canonical = sum(1 for r in records if r["duplicate_status"] == "canonical")
    actual_redundant = sum(1 for r in records if r["duplicate_status"] == "redundant")
    assert report["canonical_count"] == actual_canonical, "Canonical count mismatch"
    assert report["redundant_count"] == actual_redundant, "Redundant count mismatch"
    
    # Active sum by level equals total active rows
    level_active_sum = sum(report["active_counts_by_level"].values())
    assert level_active_sum == report["active_rows"], "Active by level sum does not equal active_rows"
