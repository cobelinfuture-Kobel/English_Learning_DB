import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
CONSTRAINTS_PATH = BASE_DIR / "ulga" / "graph" / "pattern_vocabulary_constraints.json"
QUERY_CONTRACT_PATH = BASE_DIR / "ulga" / "graph" / "pattern_vocabulary_candidate_query_contract.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "pattern_vocabulary_constraint_summary.json"
SENTENCE_PATTERNS_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_json_load():
    constraints = load_json(CONSTRAINTS_PATH)
    query_contract = load_json(QUERY_CONTRACT_PATH)
    summary = load_json(SUMMARY_PATH)
    assert isinstance(constraints, list)
    assert isinstance(query_contract, dict)
    assert isinstance(summary, dict)
    assert constraints


def test_active_constraints_only_accepted_generator_allowed():
    constraints = load_json(CONSTRAINTS_PATH)
    patterns = load_json(SENTENCE_PATTERNS_PATH)
    active_pattern_ids = {
        node["id"]
        for node in patterns
        if node["metadata"]["review_status"] == "accepted"
        and node["metadata"]["generator_allowed"] is True
    }
    constraint_pattern_ids = {record["pattern_node_id"] for record in constraints}
    assert constraint_pattern_ids == active_pattern_ids
    for record in constraints:
        assert record["active"] is True
        assert record["review_status"] == "accepted"
        assert record["generator_allowed"] is True


def test_manual_a1_cefr_gate():
    constraints = load_json(CONSTRAINTS_PATH)
    manual = [record for record in constraints if record["source"] == "MANUAL_A1_CORE_PATTERN"]
    assert len(manual) == 17
    for record in manual:
        for slot in record["slot_constraints"]:
            assert slot["cefr_gate"]["mode"] == "max_cefr"
            assert slot["cefr_gate"]["max_level"] == "A1"
            assert slot["cefr_gate"]["allow_plus_one_for_review"] is False


def test_slash_multi_type_slot_constraints():
    constraints = load_json(CONSTRAINTS_PATH)
    by_canonical = {record["canonical_pattern"]: record for record in constraints}
    for canonical in [
        "I am {adjective/noun_phrase}.",
        "I like {noun_phrase/gerund}.",
        "I don't like {noun_phrase/gerund}.",
    ]:
        slot = by_canonical[canonical]["slot_constraints"][0]
        assert slot["slot_type"] == "multi_type"
        assert len(slot["allowed_slot_types"]) >= 2
        assert slot["compatibility_classes"]
        assert slot["allowed_pos"]


def test_noun_phrase_allowed_pos():
    constraints = load_json(CONSTRAINTS_PATH)
    record = next(r for r in constraints if r["canonical_pattern"] == "I have {noun_phrase}.")
    slot = record["slot_constraints"][0]
    assert "noun" in slot["allowed_pos"]
    assert "common_noun_phrase" in slot["compatibility_classes"]
    assert slot["morphology_requirements"]["requires_countability"] is True


def test_gerund_morphology_requirement():
    constraints = load_json(CONSTRAINTS_PATH)
    record = next(r for r in constraints if r["canonical_pattern"] == "I like {noun_phrase/gerund}.")
    slot = record["slot_constraints"][0]
    assert "verb" in slot["allowed_pos"]
    assert "activity_gerund" in slot["compatibility_classes"]
    assert slot["morphology_requirements"]["requires_gerund_capable"] is True


def test_theme_mode_rule():
    constraints = load_json(CONSTRAINTS_PATH)
    manual = next(r for r in constraints if r["source"] == "MANUAL_A1_CORE_PATTERN")
    chunk = next(r for r in constraints if r["source"] == "CHUNK_GRAMMAR_METADATA_DERIVED")
    assert manual["slot_constraints"][0]["theme_gate"]["mode"] == "hard_filter"
    assert manual["slot_constraints"][0]["theme_gate"]["allowed_theme_ids"]
    assert chunk["slot_constraints"][0]["theme_gate"]["mode"] == "soft_filter"


def test_frequency_ranking_signal():
    constraints = load_json(CONSTRAINTS_PATH)
    for record in constraints[:100]:
        for slot in record["slot_constraints"]:
            assert slot["frequency_hint"]["mode"] == "ranking_signal"
            assert slot["frequency_hint"]["low_frequency_allowed"] is True
            assert slot["candidate_query"]["frequency_mode"] == "ranking_signal"


def test_no_full_edge_materialization():
    constraints = load_json(CONSTRAINTS_PATH)
    summary = load_json(SUMMARY_PATH)
    assert summary["full_pattern_vocabulary_edges_generated"] is False
    for record in constraints:
        assert "source_node_id" not in record
        assert "target_node_id" not in record
        assert "edge_type" not in record


def test_candidate_query_contract_shape():
    query_contract = load_json(QUERY_CONTRACT_PATH)
    assert query_contract["contract_version"] == "S7D_v1"
    assert "limit_default" in query_contract
    assert "limit_max" in query_contract
    assert query_contract["query_inputs"]["pattern_id"] == "required"
    assert query_contract["query_inputs"]["slot_id"] == "required"
    assert "slot_constraint" in query_contract["gate_order"]
    assert "frequency_band" in query_contract["ranking_signals"]
    assert query_contract["materialization_policy"]["full_pattern_vocabulary_edges"] is False


def test_candidate_query_contract_limit_default_positive_integer():
    query_contract = load_json(QUERY_CONTRACT_PATH)
    assert isinstance(query_contract["limit_default"], int)
    assert query_contract["limit_default"] > 0


def test_candidate_query_contract_limit_max_positive_integer_and_le_200():
    query_contract = load_json(QUERY_CONTRACT_PATH)
    assert isinstance(query_contract["limit_max"], int)
    assert query_contract["limit_max"] > 0
    assert query_contract["limit_max"] <= 200
    assert query_contract["limit_default"] <= query_contract["limit_max"]


def test_limit_default_sanity():
    constraints = load_json(CONSTRAINTS_PATH)
    for record in constraints:
        for slot in record["slot_constraints"]:
            assert 1 <= slot["candidate_query"]["limit_default"] <= 200


def test_slot_level_limit_default_within_top_level_limit_max():
    constraints = load_json(CONSTRAINTS_PATH)
    query_contract = load_json(QUERY_CONTRACT_PATH)
    top_level_limit_max = query_contract["limit_max"]
    for record in constraints:
        for slot in record["slot_constraints"]:
            assert slot["candidate_query"]["limit_default"] <= top_level_limit_max


def test_needs_review_inactive_summary():
    patterns = load_json(SENTENCE_PATTERNS_PATH)
    summary = load_json(SUMMARY_PATH)
    inactive_count = sum(
        1
        for node in patterns
        if not (
            node["metadata"]["review_status"] == "accepted"
            and node["metadata"]["generator_allowed"] is True
        )
    )
    assert summary["inactive_skipped_pattern_count"] == inactive_count


def test_validator_run():
    result = subprocess.run(
        [sys.executable, "ulga/validators/validate_pattern_vocabulary_constraints.py"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
