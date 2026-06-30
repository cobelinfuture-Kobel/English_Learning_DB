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
def chunks():
    return load_json("chunks.json")

@pytest.fixture(scope="module")
def generator_safe():
    return load_json("chunks_generator_safe.json")

@pytest.fixture(scope="module")
def equivalence_groups():
    return load_json("chunk_equivalence_groups.json")

@pytest.fixture(scope="module")
def usage_class_mapping():
    return load_json("chunk_usage_class_mapping.json")

@pytest.fixture(scope="module")
def theme_hint_mapping():
    return load_json("chunk_theme_hint_mapping.json")

@pytest.fixture(scope="module")
def priority_mapping():
    return load_json("chunk_priority_mapping.json")

@pytest.fixture(scope="module")
def validator_acceptance_map():
    return load_json("chunk_validator_acceptance_map.json")

@pytest.fixture(scope="module")
def safe_layer_policy():
    return load_json("chunk_safe_layer_policy.json")

@pytest.fixture(scope="module")
def report():
    return load_json("chunk_safe_layer_design_report.json", REPORTS_DIR)

# Test 1-7: File Existence and basic loading
def test_files_exist_and_are_valid(generator_safe, equivalence_groups, usage_class_mapping,
                                    theme_hint_mapping, priority_mapping, validator_acceptance_map,
                                    safe_layer_policy, report):
    assert isinstance(generator_safe, list)
    assert isinstance(equivalence_groups, list)
    assert isinstance(usage_class_mapping, dict)
    assert isinstance(theme_hint_mapping, dict)
    assert isinstance(priority_mapping, dict)
    assert isinstance(validator_acceptance_map, dict)
    assert isinstance(safe_layer_policy, dict)
    assert isinstance(report, dict)

# Test 8: Report exists and verdict is PASS or WARNING
def test_report_verdict(report):
    assert report.get("verdict") in ["PASS", "WARNING"]

# Test 9: safe_chunks_total <= input_chunks_total
def test_safe_chunks_total_limit(report):
    assert report["safe_chunks_total"] <= report["input_chunks_total"]
    assert report["safe_chunks_total"] > 0

# Test 10: every safe canonical_chunk_id exists in chunks.json
def test_safe_canonical_ids_exist(generator_safe, chunks):
    chunk_ids = {c["id"] for c in chunks}
    for sc in generator_safe:
        assert sc["canonical_chunk_id"] in chunk_ids, f"Canonical chunk ID {sc['canonical_chunk_id']} not in chunks.json"

# Test 11: every equivalent_id exists in chunks.json
def test_equivalent_ids_exist(equivalence_groups, chunks):
    chunk_ids = {c["id"] for c in chunks}
    for eg in equivalence_groups:
        for eq_id in eg["equivalent_ids"]:
            assert eq_id in chunk_ids, f"Equivalent ID {eq_id} not in chunks.json"

# Test 12-14: validator acceptance map coverage and validity
def test_validator_acceptance_map(validator_acceptance_map, chunks):
    chunk_ids = {c["id"] for c in chunks}
    
    # 12. every original chunk id appears in validator acceptance map
    # 13. validator acceptance map coverage == input_chunks_total
    assert len(validator_acceptance_map) == len(chunks)
    
    for cid in chunk_ids:
        assert cid in validator_acceptance_map, f"Original chunk ID {cid} missing from validator acceptance map"
        
        # 14. every original chunk id has validator_accept = true
        entry = validator_acceptance_map[cid]
        assert entry["validator_accept"] is True, f"validator_accept is not True for {cid}"
        assert entry["canonical_chunk_id"] in chunk_ids, f"canonical_chunk_id {entry['canonical_chunk_id']} not in chunks.json"
        assert entry["accepted_as"] in chunk_ids, f"accepted_as {entry['accepted_as']} not in chunks.json"

# Test 15: no duplicate safe canonical_chunk_id
def test_no_duplicate_safe_canonical_ids(generator_safe):
    canonical_ids = [sc["canonical_chunk_id"] for sc in generator_safe]
    assert len(canonical_ids) == len(set(canonical_ids)), "Duplicate canonical chunk IDs found in safe layer"

# Test 16-17: priority mapping checks
def test_priority_mapping(priority_mapping, chunks):
    for cid in priority_mapping:
        pm = priority_mapping[cid]
        score = pm["frequency_proxy_score"]
        band = pm["priority_band"]
        
        # 16. priority score between 0 and 1
        assert 0.0 <= score <= 1.0, f"Score {score} for {cid} not in [0.0, 1.0]"
        
        # 17. priority_band in core/common/extended/low
        assert band in ["core", "common", "extended", "low"], f"Invalid priority band {band} for {cid}"

# Test 18: usage_class not empty
def test_usage_class_mapping_valid(usage_class_mapping):
    for cid, val in usage_class_mapping.items():
        assert val["usage_class"], f"Usage class empty for {cid}"
        assert isinstance(val["usage_class"], str)

# Test 19: theme_hint is non-empty list
def test_theme_hint_mapping_valid(theme_hint_mapping):
    for cid, val in theme_hint_mapping.items():
        assert isinstance(val["theme_hint"], list), f"Theme hint for {cid} must be a list"
        assert len(val["theme_hint"]) > 0, f"Theme hint list empty for {cid}"
        for hint in val["theme_hint"]:
            assert isinstance(hint, str)

# Test 20-22: policy rules are true
def test_safe_layer_policy_rules(safe_layer_policy):
    rules = safe_layer_policy.get("rules", {})
    # 20. policy raw_chunks_are_immutable = true
    assert rules.get("raw_chunks_are_immutable") is True
    # 21. policy generator_uses_safe_layer = true
    assert rules.get("generator_uses_safe_layer") is True
    # 22. policy validator_accepts_raw_and_equivalent_ids = true
    assert rules.get("validator_accepts_raw_and_equivalent_ids") is True
