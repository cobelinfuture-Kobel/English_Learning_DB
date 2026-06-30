import os
import json
import pytest

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB_MAPPING_PATH = os.path.join(BASE_DIR, "themes", "theme_vocab_mapping.json")
CATALOG_PATH = os.path.join(BASE_DIR, "themes", "theme_catalog.json")
REPORT_PATH = os.path.join(BASE_DIR, "output", "reports", "theme_mapping_report.json")

def test_files_exist():
    """Verify that mapping and catalog JSON files exist."""
    assert os.path.exists(VOCAB_MAPPING_PATH), "theme_vocab_mapping.json does not exist"
    assert os.path.exists(CATALOG_PATH), "theme_catalog.json does not exist"
    assert os.path.exists(REPORT_PATH), "theme_mapping_report.json does not exist"

def test_every_theme_has_required_keys():
    """Verify that every theme in the database has theme_id, level, and primary_topics."""
    with open(VOCAB_MAPPING_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    themes = data.get("themes", [])
    assert len(themes) > 0, "No themes found in theme_vocab_mapping.json"
    
    for t in themes:
        assert "theme_id" in t, "Theme missing theme_id"
        assert "level" in t, f"Theme {t.get('theme_id')} missing level"
        assert "primary_topics" in t, f"Theme {t.get('theme_id')} missing primary_topics"
        assert isinstance(t["primary_topics"], list), f"primary_topics for {t.get('theme_id')} must be a list"

def test_no_blocked_topic_in_primary_topics():
    """Verify that no blocked topic appears inside primary_topics for any theme."""
    with open(VOCAB_MAPPING_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    themes = data.get("themes", [])
    for t in themes:
        primaries = set(t["primary_topics"])
        blocked = set(t.get("blocked_topics", []))
        overlap = primaries.intersection(blocked)
        assert not overlap, f"Theme {t['theme_id']} has overlap between primary and blocked topics: {overlap}"

def test_progression_references_valid():
    """Verify that next_theme_id and prev_theme_id references exist within the theme dataset."""
    with open(VOCAB_MAPPING_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    themes = data.get("themes", [])
    all_theme_ids = {t["theme_id"] for t in themes}
    
    for t in themes:
        next_id = t.get("next_theme_id")
        prev_id = t.get("prev_theme_id")
        
        if next_id is not None:
            assert next_id in all_theme_ids, f"Theme {t['theme_id']} has invalid next_theme_id: {next_id}"
        if prev_id is not None:
            assert prev_id in all_theme_ids, f"Theme {t['theme_id']} has invalid prev_theme_id: {prev_id}"

def test_vocabulary_counts_non_negative():
    """Verify that all vocabulary counts in the mapping database are non-negative integers."""
    with open(VOCAB_MAPPING_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    themes = data.get("themes", [])
    for t in themes:
        assert "vocabulary_count" in t, f"Theme {t['theme_id']} missing vocabulary_count"
        assert "active_vocabulary_count" in t, f"Theme {t['theme_id']} missing active_vocabulary_count"
        assert "primary_topic_word_count" in t, f"Theme {t['theme_id']} missing primary_topic_word_count"
        assert "secondary_topic_word_count" in t, f"Theme {t['theme_id']} missing secondary_topic_word_count"
        
        assert t["vocabulary_count"] >= 0, f"Theme {t['theme_id']} has negative vocabulary_count"
        assert t["active_vocabulary_count"] >= 0, f"Theme {t['theme_id']} has negative active_vocabulary_count"
        assert t["primary_topic_word_count"] >= 0, f"Theme {t['theme_id']} has negative primary_topic_word_count"
        assert t["secondary_topic_word_count"] >= 0, f"Theme {t['theme_id']} has negative secondary_topic_word_count"
        
        # Consistent mapping verification: active_vocabulary_count equals primary + secondary active counts
        assert t["active_vocabulary_count"] == t["primary_topic_word_count"] + t["secondary_topic_word_count"], \
            f"Active vocabulary count mismatch for {t['theme_id']}"
