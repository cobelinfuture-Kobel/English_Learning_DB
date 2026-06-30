import importlib.util
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
SCHEMA_DIR = BASE_DIR / "ulga" / "schema"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_ulga_schema.py"


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_ulga_schema", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_node_schema_exists_and_supports_required_node_types():
    schema = load_json(SCHEMA_DIR / "ulga_node_schema.json")
    assert set(schema["required"]) == {
        "id",
        "node_type",
        "label",
        "authority_source",
        "cefr_level",
        "confidence",
        "version",
        "metadata",
    }
    assert set(schema["properties"]["node_type"]["enum"]) == {
        "grammar",
        "vocabulary",
        "chunk",
        "theme",
        "sentence_pattern",
        "skill",
        "exercise_type",
        "learner_state",
        "assessment",
    }


def test_edge_schema_exists_and_supports_required_edge_types():
    schema = load_json(SCHEMA_DIR / "ulga_edge_schema.json")
    assert set(schema["required"]) == {
        "id",
        "source_node_id",
        "target_node_id",
        "edge_type",
        "authority_source",
        "confidence",
        "version",
        "metadata",
    }
    assert set(schema["properties"]["edge_type"]["enum"]) == {
        "prerequisite",
        "supports",
        "belongs_to",
        "unlocks",
        "reviews",
        "contrasts_with",
        "uses",
        "contains",
        "spiral_to",
        "assesses",
    }


def test_graph_schema_requires_empty_scaffold_policy():
    schema = load_json(SCHEMA_DIR / "ulga_graph_schema.json")
    assert schema["properties"]["formal_data_mounted"]["const"] is False
    assert schema["properties"]["metadata"]["properties"]["data_policy"]["const"] == "empty_scaffold_only"


def test_validator_accepts_valid_node_and_edge_fixtures():
    validator = load_validator()
    node = {
        "id": "grammar:fixture",
        "node_type": "grammar",
        "label": "Fixture grammar node",
        "authority_source": {"source_name": "fixture", "derivation": "scaffold"},
        "cefr_level": "A1",
        "confidence": {"value": 1.0, "method": "fixture"},
        "version": {"contract": "ULGA-S2"},
        "metadata": {},
    }
    edge = {
        "id": "edge:fixture",
        "source_node_id": "grammar:fixture",
        "target_node_id": "grammar:fixture",
        "edge_type": "reviews",
        "authority_source": {"source_name": "fixture", "derivation": "scaffold"},
        "confidence": {"value": 1.0, "method": "fixture"},
        "version": {"contract": "ULGA-S2"},
        "metadata": {},
    }
    validator.validate_node(node)
    validator.validate_edge(edge, node_ids={"grammar:fixture"})


def test_validator_rejects_bad_node_id_prefix():
    validator = load_validator()
    node = {
        "id": "vocabulary:fixture",
        "node_type": "grammar",
        "label": "Bad fixture",
        "authority_source": {"source_name": "fixture", "derivation": "scaffold"},
        "cefr_level": "A1",
        "confidence": {"value": 1.0, "method": "fixture"},
        "version": {"contract": "ULGA-S2"},
        "metadata": {},
    }
    try:
        validator.validate_node(node)
    except validator.ValidationError:
        return
    raise AssertionError("validate_node should reject node id prefix mismatch")
