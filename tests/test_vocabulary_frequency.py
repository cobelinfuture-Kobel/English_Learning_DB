import os
import json
import pytest

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB_JSON_PATH = os.path.join(BASE_DIR, "vocabulary", "json", "vocabulary.json")
REPORT_PATH = os.path.join(BASE_DIR, "reports", "ngsl_frequency_upgrade_report.json")
MAPPING_PATH = os.path.join(BASE_DIR, "vocabulary", "mapping", "frequency_mapping.json")

def test_files_exist():
    """Verify that frequency output files exist."""
    assert os.path.exists(VOCAB_JSON_PATH), "vocabulary.json does not exist"
    assert os.path.exists(REPORT_PATH), "ngsl_frequency_upgrade_report.json does not exist"
    assert os.path.exists(MAPPING_PATH), "frequency_mapping.json does not exist"

def test_valid_frequency_bands():
    """Verify that all populated frequency bands are in the standard set."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    allowed_bands = {"tier_1", "tier_2", "tier_3", "tier_4", "tier_5"}
    for r in records:
        band = r.get("frequency_band")
        assert band in allowed_bands, f"Record {r.get('vocab_id')} has invalid frequency band: {band}"

def test_no_empty_frequency_band():
    """Verify that no record has an empty frequency_band placeholder."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    for r in records:
        assert r.get("frequency_band") != "", f"Record {r.get('vocab_id')} has empty frequency_band"

def test_non_negative_frequency_score():
    """Verify that all frequency scores are non-negative floats."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    for r in records:
        score = r.get("frequency_score")
        assert isinstance(score, (int, float)), f"Record {r.get('vocab_id')} has non-numeric frequency_score"
        assert score >= 0.0, f"Record {r.get('vocab_id')} has negative frequency_score: {score}"

def test_corpus_rank_consistency():
    """Verify that corpus_rank matches the new hybrid frequency_band constraints."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    for r in records:
        rank = r.get("corpus_rank")
        band = r.get("frequency_band")
        assert isinstance(rank, int), f"Record {r.get('vocab_id')} has non-integer corpus_rank"
        
        # Verify rank vs band thresholds
        # Note: Phrase capping can push a phrase to a lower tier (e.g. tier_3 instead of tier_1),
        # so for capped phrases, the band can be lower (higher tier number) than the rank threshold.
        # But a word's band should NEVER be higher (lower tier number) than its rank threshold allows.
        # Let's verify that the band is consistent with rank thresholds (accounting for capping).
        if rank <= 1000:
            # Can be capped to lower tiers
            assert band in ["tier_1", "tier_2", "tier_3", "tier_4", "tier_5"]
        elif rank <= 3000:
            assert band in ["tier_2", "tier_3", "tier_4", "tier_5"]
        elif rank <= 7000:
            assert band in ["tier_3", "tier_4", "tier_5"]
        elif rank <= 11500:
            assert band in ["tier_4", "tier_5"]
        else:
            assert band == "tier_5"

def test_phrase_fallback_behavior():
    """Verify that phrases match or fallback correctly, checking their recovery method."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    phrases = [r for r in records if " " in r["word"]]
    assert len(phrases) > 0, "No phrases found in vocabulary.json"
    
    allowed_methods = {
        "direct_match", 
        "spelling_normalization", 
        "plural_normalization", 
        "participle_normalization",
        "hyphenated_normalization", 
        "abbreviation_normalization", 
        "ordinal_normalization",
        "phrase_headword_fallback", 
        "tier_5_fallback"
    }
    
    for r in phrases:
        method = r.get("frequency_recovery_method")
        assert method in allowed_methods, \
            f"Phrase {r.get('vocab_id')} has invalid frequency recovery method: {method}"
            
        if method == "phrase_headword_fallback":
            assert r["frequency_score"] > 0, "Phrase headword fallback should have a non-zero score"

def test_phrase_tier_capping():
    """Verify that phrase-derived frequency bands never exceed their CEFR ceilings."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    ceilings = {
        "a1": "tier_1", "a1_plus": "tier_1",
        "a2": "tier_1", "a2_plus": "tier_1",
        "b1": "tier_2", "b1_plus": "tier_2",
        "b2": "tier_3", "b2_plus": "tier_3",
        "c1": "tier_4", "c1_plus": "tier_4",
        "c2": "tier_5"
    }
    tier_values = {"tier_1": 1, "tier_2": 2, "tier_3": 3, "tier_4": 4, "tier_5": 5}
    
    for r in records:
        w_raw = r["word"]
        pos = str(r.get("part_of_speech", "")).lower()
        is_phrase = " " in w_raw or pos in ["phrase", "phrasal verb"]
        
        if is_phrase:
            lvl = r["level"].strip().lower()
            band = r.get("frequency_band")
            ceiling = ceilings.get(lvl, "tier_5")
            assert tier_values[band] >= tier_values[ceiling], \
                f"Phrase {r['vocab_id']} ({r['word']}) at level {r['level']} has band {band}, exceeding ceiling {ceiling}"

def test_unmatched_rate():
    """Verify that the unmatched rate is <= 5% (Success Criteria)."""
    with open(VOCAB_JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    unmatched = [r for r in records if r.get("frequency_recovery_method") == "tier_5_fallback"]
    unmatched_rate = len(unmatched) / len(records)
    print(f"Unmatched Rate: {unmatched_rate*100:.2f}% ({len(unmatched)} records)")
    assert unmatched_rate <= 0.05, f"Unmatched rate is too high: {unmatched_rate*100:.2f}% (max 5%)"
