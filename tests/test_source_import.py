import os
import json
import pytest

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAMMAR_JSON_PATH = os.path.join(BASE_DIR, "grammar_profile", "json", "grammar_profile.json")
LEVEL_MAPPING_PATH = os.path.join(BASE_DIR, "grammar_profile", "mapping", "level_mapping.json")
THEME_MAPPING_PATH = os.path.join(BASE_DIR, "themes", "theme_mapping.json")
REPORT_PATH = os.path.join(BASE_DIR, "output", "reports", "source_import_report.json")

def test_grammar_profile_json_exists():
    """Test that grammar_profile.json exists."""
    assert os.path.exists(GRAMMAR_JSON_PATH), "grammar_profile.json file does not exist"

def test_total_imported_rows():
    """Test that total imported rows equals 1222."""
    with open(GRAMMAR_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    assert len(records) == 1222, f"Expected 1222 records, but got {len(records)}"

def test_no_duplicate_ids():
    """Test that there are no duplicate ids in the imported records."""
    with open(GRAMMAR_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids)), "Duplicate IDs found in grammar_profile.json"

def test_required_normalized_keys():
    """Test that all rows contain the required normalized keys."""
    required_keys = {
        "id", "super_category", "sub_category", "level", 
        "lexical_range", "guideword", "can_do_statement", 
        "example", "source_sheet", "source_row", "import_warnings"
    }
    with open(GRAMMAR_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    for record in records:
        record_keys = set(record.keys())
        missing_keys = required_keys - record_keys
        assert not missing_keys, f"Record with ID {record.get('id')} is missing keys: {missing_keys}"

def test_c2_rows_present_but_inactive():
    """Test that C2 rows are present in grammar_profile.json but set as inactive by default in mapping."""
    with open(GRAMMAR_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    c2_records = [r for r in records if r["level"] == "C2"]
    assert len(c2_records) > 0, "No C2 rows found in grammar_profile.json"
    
    with open(LEVEL_MAPPING_PATH, "r", encoding="utf-8") as f:
        level_mapping = json.load(f)
        
    c2_mapping = level_mapping.get("mappings", {}).get("C2", {})
    assert c2_mapping, "C2 mapping not found in level_mapping.json"
    assert c2_mapping.get("active") is False, "C2 level should be inactive by default"

def test_missing_can_do_and_example_imported_with_warnings():
    """Test that missing Can-do / Example rows are imported and have warning flags."""
    with open(GRAMMAR_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    # We know specific rows are missing Can-do or Example from the inspection report.
    # Excel rows: 214, 422, 838, 1001.
    warning_rows = {214, 422, 838, 1001}
    warning_records = [r for r in records if r["source_row"] in warning_rows]
    
    assert len(warning_records) == 4, f"Expected 4 records with warning rows, got {len(warning_records)}"
    
    for r in warning_records:
        assert len(r["import_warnings"]) > 0, f"Record at row {r['source_row']} is missing import warnings"
        # Validate that warnings contain correct description
        warnings_str = " ".join(r["import_warnings"])
        assert "missing Can-do statement" in warnings_str or "missing Example" in warnings_str

def test_theme_mapping_target_levels():
    """Test that the theme mapping contains all 9 target levels."""
    expected_levels = {
        "A1", "A1_plus", "A2", "A2_plus", "B1", "B1_plus", "B2", "B2_plus", "C1"
    }
    with open(THEME_MAPPING_PATH, "r", encoding="utf-8") as f:
        theme_mapping = json.load(f)
        
    mapped_levels = set(theme_mapping.keys())
    missing_levels = expected_levels - mapped_levels
    assert not missing_levels, f"Theme mapping is missing levels: {missing_levels}"
    
    # Check that plus levels have mapping_status == descriptive_only
    for lvl in ["A1_plus", "A2_plus", "B1_plus", "B2_plus"]:
        assert theme_mapping[lvl]["mapping_status"] == "descriptive_only", f"{lvl} should be descriptive_only"
