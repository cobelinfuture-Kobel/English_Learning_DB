import os
import json
import pytest

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_DIR = os.path.join(BASE_DIR, "chunk_profile", "json")
REPORTS_DIR = os.path.join(BASE_DIR, "chunk_profile", "reports")

def load_json(name, folder=JSON_DIR):
    path = os.path.join(folder, name)
    assert os.path.exists(path), f"File {name} does not exist at {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="module")
def generator_safe():
    return load_json("chunks_generator_safe.json")

@pytest.fixture(scope="module")
def safe_enhanced():
    return load_json("chunks_generator_safe_theme_enhanced.json")

@pytest.fixture(scope="module")
def enhanced_mapping():
    return load_json("chunk_theme_hint_enhanced_mapping.json")

@pytest.fixture(scope="module")
def rulebook():
    return load_json("chunk_theme_rulebook.json")

@pytest.fixture(scope="module")
def coverage_delta():
    return load_json("chunk_theme_coverage_delta.json")

@pytest.fixture(scope="module")
def enhancement_policy():
    return load_json("chunk_theme_enhancement_policy.json")

@pytest.fixture(scope="module")
def report():
    return load_json("chunk_theme_coverage_enhancement_report.json", REPORTS_DIR)

# Test 1-6: File Existence and basic loading
def test_files_exist_and_are_valid(enhanced_mapping, safe_enhanced, rulebook,
                                    coverage_delta, enhancement_policy, report):
    assert isinstance(enhanced_mapping, dict)
    assert isinstance(safe_enhanced, list)
    assert isinstance(rulebook, dict)
    assert isinstance(coverage_delta, dict)
    assert isinstance(enhancement_policy, dict)
    assert isinstance(report, dict)

# Test 6: Report exists and verdict is STRONG_PASS / PASS / WARNING
def test_report_verdict(report):
    assert report.get("verdict") in ["STRONG_PASS", "PASS", "WARNING"]

# Test 7: enhanced safe layer count equals chunks_generator_safe count
def test_safe_layer_count_match(safe_enhanced, generator_safe):
    assert len(safe_enhanced) == len(generator_safe)

# Test 8-9 & 14-16: verify safe layer values remain unchanged
def test_safe_layer_values_unchanged(safe_enhanced, generator_safe):
    gen_by_safe_id = {c["safe_id"]: c for c in generator_safe}
    
    for sc in safe_enhanced:
        sid = sc["safe_id"]
        assert sid in gen_by_safe_id, f"Safe ID {sid} not found in original generator safe layer"
        orig = gen_by_safe_id[sid]
        
        # 8. every safe_id unchanged
        assert sc["safe_id"] == orig["safe_id"]
        # 9. every canonical_chunk_id unchanged
        assert sc["canonical_chunk_id"] == orig["canonical_chunk_id"]
        # 14. no CEFR level changed
        assert sc["level"] == orig["level"]
        # 15. no priority_band changed
        assert sc["priority_band"] == orig["priority_band"]
        # 16. no usage_class changed
        assert sc["usage_class"] == orig["usage_class"]
        # equivalent_ids unchanged
        assert sc["equivalent_ids"] == orig["equivalent_ids"]

# Test 10-12: enhanced theme values and confidence
def test_enhanced_themes_and_confidence(safe_enhanced, rulebook):
    allowed_themes = set(rulebook["theme_set"])
    
    for sc in safe_enhanced:
        themes = sc["theme_hint_enhanced"]
        confidence = sc["theme_enhancement_confidence"]
        
        # 10. every enhanced_theme_hint is non-empty list
        assert isinstance(themes, list)
        assert len(themes) > 0
        
        # 11. every theme value is in allowed theme set
        for t in themes:
            assert t in allowed_themes, f"Theme {t} not in allowed theme set"
            
        # 12. confidence in high / medium / low
        assert confidence in ["high", "medium", "low"]

# Test 13: low confidence does not override existing non-General theme
def test_low_confidence_guard(safe_enhanced):
    for sc in safe_enhanced:
        confidence = sc["theme_enhancement_confidence"]
        orig_themes = sc["theme_hint_original"]
        enhanced_themes = sc["theme_hint_enhanced"]
        
        if confidence == "low" and orig_themes != ["General"]:
            assert sorted(enhanced_themes) == sorted(orig_themes), \
                f"Low confidence override occurred for {sc['safe_id']}: original {orig_themes} became {enhanced_themes}"

# Test 17: policy theme_enhancement_is_derived = true
def test_policy_theme_enhancement_is_derived(enhancement_policy):
    rules = enhancement_policy.get("rules", {})
    assert rules.get("theme_enhancement_is_derived") is True

# Test 18: general_only_ratio_after <= general_only_ratio_before
def test_general_only_ratio_delta(report):
    before_ratio = report["general_only_ratio_before"]
    after_ratio = report["general_only_ratio_after"]
    assert after_ratio <= before_ratio
