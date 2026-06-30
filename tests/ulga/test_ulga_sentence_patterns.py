import json
import pytest
from pathlib import Path
from ulga.build_ulga_sentence_patterns import extract_slots_from_pattern

BASE_DIR = Path(__file__).resolve().parent.parent.parent
NODES_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"
EDGES_PATH = BASE_DIR / "ulga" / "graph" / "ulga_sentence_pattern_edges.json"
GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "ulga_sentence_pattern_nodes.json"

@pytest.fixture
def data():
    # Load files
    with open(NODES_PATH, "r", encoding="utf-8") as f:
        nodes = json.load(f)
    with open(EDGES_PATH, "r", encoding="utf-8") as f:
        edges = json.load(f)
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    return {"nodes": nodes, "edges": edges, "graph": graph}

def test_json_load(data):
    # JSON load test
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    assert isinstance(data["graph"], dict)
    assert len(data["nodes"]) > 0

def test_schema_fields(data):
    # schema field test
    required_keys = {"id", "node_type", "label", "authority_source", "cefr_level", "confidence", "version", "metadata"}
    metadata_required = {
        "pattern_id", "canonical_pattern", "normalized_pattern", "pattern_family_id", "pattern_type",
        "cefr_level", "difficulty_score", "slots", "grammar_refs", "vocabulary_slot_constraints",
        "chunk_refs", "theme_refs", "example_sentences", "generator_allowed", "validator_required",
        "source", "review_status"
    }
    for n in data["nodes"]:
        assert required_keys.issubset(n.keys())
        assert metadata_required.issubset(n["metadata"].keys())
        assert n["node_type"] == "sentence_pattern"
        assert n["id"].startswith("pattern:")

def test_unique_ids(data):
    # unique id test
    node_ids = [n["id"] for n in data["nodes"]]
    sp_ids = [n["metadata"]["pattern_id"] for n in data["nodes"]]
    assert len(node_ids) == len(set(node_ids))
    assert len(sp_ids) == len(set(sp_ids))

def test_manual_a1_presence(data):
    # manual A1 core pattern presence test
    manual_patterns = [n for n in data["nodes"] if n["metadata"]["source"] == "MANUAL_A1_CORE_PATTERN"]
    assert len(manual_patterns) == 17
    # verify unique IDs for manual patterns
    sp_ids = {n["authority_source"]["source_record_id"] for n in manual_patterns}
    assert len(sp_ids) == 17

def test_slot_constraints(data):
    # slot constraint test
    for n in data["nodes"]:
        slots = n["metadata"]["slots"]
        assert isinstance(slots, list)
        for s in slots:
            assert "slot_id" in s
            assert "slot_label" in s
            assert "slot_type" in s
            assert "required" in s
            assert "constraints" in s
            assert isinstance(s["constraints"], dict)
            assert isinstance(s["slot_label"], str)
            assert s["slot_label"].strip()

def test_edge_relation_validity(data):
    # edge relation validity test
    allowed_relations = {"prerequisite", "supports", "belongs_to", "unlocks", "reviews", "contrasts_with", "uses", "contains", "spiral_to", "assesses"}
    for e in data["edges"]:
        assert e["edge_type"] in allowed_relations
        assert e["id"].startswith("edge:")
        assert e["source_node_id"].startswith("pattern:")

def test_no_broken_edge_targets(data):
    # no broken edge target test
    node_ids = {n["id"] for n in data["nodes"]}
    # Load referenced databases to check validity
    with open(BASE_DIR / "ulga" / "graph" / "grammar_nodes.json", "r", encoding="utf-8") as f:
        grammar_ids = {n["id"] for n in json.load(f)}
    with open(BASE_DIR / "ulga" / "graph" / "chunk_nodes.json", "r", encoding="utf-8") as f:
        chunk_ids = {n["id"] for n in json.load(f)}
    with open(BASE_DIR / "ulga" / "graph" / "theme_nodes.json", "r", encoding="utf-8") as f:
        theme_ids = {n["id"] for n in json.load(f)}
        
    for e in data["edges"]:
        tgt = e["target_node_id"]
        tgt_prefix = tgt.split(":")[0] if ":" in tgt else None
        if tgt_prefix == "pattern" or tgt_prefix == "sentence_pattern":
            assert tgt in node_ids
        elif tgt_prefix == "grammar":
            assert tgt in grammar_ids
        elif tgt_prefix == "chunk":
            assert tgt in chunk_ids
        elif tgt_prefix == "theme":
            assert tgt in theme_ids

def test_review_status_distribution(data):
    # review_status distribution test
    statuses = [n["metadata"]["review_status"] for n in data["nodes"]]
    assert all(s in {"accepted", "needs_review", "blocked"} for s in statuses)

def test_generator_allowed_boolean(data):
    # generator_allowed boolean test
    for n in data["nodes"]:
        assert isinstance(n["metadata"]["generator_allowed"], bool)

def test_validator_required_boolean(data):
    # validator_required boolean test
    for n in data["nodes"]:
        assert isinstance(n["metadata"]["validator_required"], bool)

def test_slash_slot_extraction_returns_multi_type_slot():
    slots = extract_slots_from_pattern("I like {noun_phrase/gerund}.", "A1")
    assert len(slots) == 1
    assert slots[0]["slot_label"] == "noun_phrase/gerund"
    assert slots[0]["slot_type"] == "multi_type"
    assert slots[0]["allowed_slot_types"] == ["noun_phrase", "verb_gerund"]

def test_invalid_empty_placeholder_blocked():
    slots = extract_slots_from_pattern("I like {}.", "A1")
    assert slots == []

def test_invalid_nested_placeholder_blocked():
    slots = extract_slots_from_pattern("I like {{noun}}.", "A1")
    assert slots == []

def test_manual_a1_slots_are_non_empty(data):
    manual_patterns = [n for n in data["nodes"] if n["metadata"]["source"] == "MANUAL_A1_CORE_PATTERN"]
    assert manual_patterns
    for n in manual_patterns:
        assert n["metadata"]["slots"], n["metadata"]["canonical_pattern"]

def test_manual_a1_slash_patterns_are_parsed(data):
    expected = {
        "I am {adjective/noun_phrase}.": ["adjective", "noun_phrase"],
        "I like {noun_phrase/gerund}.": ["noun_phrase", "verb_gerund"],
        "I don't like {noun_phrase/gerund}.": ["noun_phrase", "verb_gerund"],
    }
    nodes_by_canonical = {
        n["metadata"]["canonical_pattern"]: n
        for n in data["nodes"]
        if n["metadata"]["source"] == "MANUAL_A1_CORE_PATTERN"
    }
    for canonical, allowed_types in expected.items():
        slot = nodes_by_canonical[canonical]["metadata"]["slots"][0]
        assert slot["slot_type"] == "multi_type"
        assert slot["allowed_slot_types"] == allowed_types

def test_accepted_generator_allowed_patterns_have_non_empty_slots(data):
    for n in data["nodes"]:
        meta = n["metadata"]
        if meta["review_status"] == "accepted" and meta["generator_allowed"]:
            assert meta["slots"], n["id"]
