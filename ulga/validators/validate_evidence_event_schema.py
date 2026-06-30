import json
import re
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
LEARNER_STATE_DIR = BASE_DIR / "ulga" / "learner_state"
SCHEMA_PATH = LEARNER_STATE_DIR / "evidence_event_schema.json"
SAMPLE_PATH = LEARNER_STATE_DIR / "sample_evidence_events.json"

EVENT_TYPES = {
    "worksheet",
    "quiz",
    "reading",
    "dialogue",
    "speaking",
    "writing",
    "listening",
    "manual_parent_input",
    "manual_teacher_input",
}
NODE_TYPES = {
    "grammar",
    "vocabulary",
    "chunk",
    "sentence_pattern",
    "theme",
    "morphology",
    "reading",
    "dialogue",
    "assessment",
    "skill",
    "exercise_type",
}
NODE_ROLES = {
    "primary_target",
    "supporting_context",
    "prerequisite",
    "diagnostic_signal",
    "review_signal",
    "coverage_signal",
}
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


class ValidationError(Exception):
    pass


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def validate_schema_file(schema):
    required_top_level = {
        "contract_metadata",
        "event_type_enum",
        "node_type_enum",
        "role_enum",
        "evidence_event_collection_schema",
    }
    require(isinstance(schema, dict), "schema must be a JSON object")
    properties = schema.get("properties")
    require(isinstance(properties, dict), "schema.properties must be an object")
    require(required_top_level.issubset(properties), "schema missing required top-level sections")
    require(set(schema.get("required", [])) == required_top_level, "schema.required mismatch")

    metadata = properties["contract_metadata"]["properties"]
    require(metadata["contract_id"]["const"] == "ulga.evidence_event", "schema contract_id mismatch")
    require(metadata["contract_version"]["const"] == "ULGA-S9B", "schema contract_version mismatch")
    require(metadata["schema_version"]["const"] == "1.0.0", "schema schema_version mismatch")
    require(
        metadata["source_design_scan"]["const"] == "docs/ulga/ULGA_S9A_LEARNER_STATE_AUTHORITY_DESIGN_SCAN.md",
        "schema source_design_scan mismatch",
    )
    require(
        metadata["schema_only_no_learner_state_aggregation"]["const"] is True,
        "schema must declare no learner-state aggregation",
    )
    require(set(properties["event_type_enum"]["items"]["enum"]) == EVENT_TYPES, "schema event_type_enum mismatch")
    require(set(properties["node_type_enum"]["items"]["enum"]) == NODE_TYPES, "schema node_type_enum mismatch")
    require(set(properties["role_enum"]["items"]["enum"]) == NODE_ROLES, "schema role_enum mismatch")


def validate_confidence(confidence, path_label):
    require(isinstance(confidence, dict), f"{path_label}.confidence must be an object")
    require("value" in confidence, f"{path_label}.confidence.value is required")
    require("method" in confidence, f"{path_label}.confidence.method is required")
    value = confidence["value"]
    require(isinstance(value, (int, float)), f"{path_label}.confidence.value must be a number")
    require(0 <= value <= 1, f"{path_label}.confidence.value must be between 0 and 1")
    require(isinstance(confidence["method"], str) and confidence["method"].strip(), f"{path_label}.confidence.method must be non-empty")
    if "notes" in confidence:
        require(isinstance(confidence["notes"], list), f"{path_label}.confidence.notes must be a list")


def validate_source(source, path_label):
    required = {"producer", "channel", "derivation"}
    require(isinstance(source, dict), f"{path_label}.source must be an object")
    require(required.issubset(source), f"{path_label}.source missing required fields: {sorted(required - set(source))}")
    for key in required:
        require(isinstance(source[key], str) and source[key].strip(), f"{path_label}.source.{key} must be a non-empty string")
    if "notes" in source:
        require(isinstance(source["notes"], list), f"{path_label}.source.notes must be a list")


def validate_node_ref(node_ref, event_index, node_index):
    path_label = f"events[{event_index}].node_refs[{node_index}]"
    required = {"node_id", "node_type", "role", "weight"}
    require(isinstance(node_ref, dict), f"{path_label} must be an object")
    require(required.issubset(node_ref), f"{path_label} missing required fields: {sorted(required - set(node_ref))}")
    require(isinstance(node_ref["node_id"], str) and node_ref["node_id"].strip(), f"{path_label}.node_id must be a non-empty string")
    require(node_ref["node_type"] in NODE_TYPES, f"{path_label}.node_type is invalid: {node_ref['node_type']}")
    require(node_ref["role"] in NODE_ROLES, f"{path_label}.role is invalid: {node_ref['role']}")
    weight = node_ref["weight"]
    require(isinstance(weight, (int, float)), f"{path_label}.weight must be a number")
    require(0 <= weight <= 1, f"{path_label}.weight must be between 0 and 1")


def validate_event(event, event_index):
    path_label = f"events[{event_index}]"
    required = {
        "event_id",
        "learner_id",
        "event_type",
        "timestamp",
        "node_refs",
        "score",
        "attempt_count",
        "response_time",
        "error_type",
        "confidence",
        "source",
        "processing_idempotency_key",
    }
    require(isinstance(event, dict), f"{path_label} must be an object")
    require(required.issubset(event), f"{path_label} missing required fields: {sorted(required - set(event))}")
    require(isinstance(event["event_id"], str) and event["event_id"].strip(), f"{path_label}.event_id must be a non-empty string")
    require(isinstance(event["learner_id"], str) and event["learner_id"].strip(), f"{path_label}.learner_id must be a non-empty string")
    require(event["event_type"] in EVENT_TYPES, f"{path_label}.event_type is invalid: {event['event_type']}")
    require(isinstance(event["timestamp"], str) and TIMESTAMP_RE.match(event["timestamp"]), f"{path_label}.timestamp must be an ISO-like string")
    require(isinstance(event["node_refs"], list) and event["node_refs"], f"{path_label}.node_refs must contain at least one item")
    for node_index, node_ref in enumerate(event["node_refs"]):
        validate_node_ref(node_ref, event_index, node_index)
    score = event["score"]
    require(isinstance(score, (int, float)), f"{path_label}.score must be a number")
    require(0 <= score <= 1, f"{path_label}.score must be between 0 and 1")
    attempt_count = event["attempt_count"]
    require(isinstance(attempt_count, int) and attempt_count >= 1, f"{path_label}.attempt_count must be an integer >= 1")
    response_time = event["response_time"]
    require(
        response_time is None or (isinstance(response_time, (int, float)) and response_time >= 0),
        f"{path_label}.response_time must be null or a number >= 0",
    )
    error_type = event["error_type"]
    require(error_type is None or isinstance(error_type, str), f"{path_label}.error_type must be null or a string")
    validate_confidence(event["confidence"], path_label)
    validate_source(event["source"], path_label)
    require(
        isinstance(event["processing_idempotency_key"], str) and event["processing_idempotency_key"].strip(),
        f"{path_label}.processing_idempotency_key must be a non-empty string",
    )


def validate_event_collection(payload):
    require(isinstance(payload, dict), "sample evidence events payload must be an object")
    require(payload.get("contract_version") == "ULGA-S9B", "sample evidence events contract_version must be ULGA-S9B")
    events = payload.get("events")
    require(isinstance(events, list) and events, "sample evidence events must contain a non-empty events array")

    seen_event_ids = set()
    seen_idempotency_keys = set()
    for event_index, event in enumerate(events):
        validate_event(event, event_index)
        event_id = event["event_id"]
        idem_key = event["processing_idempotency_key"]
        require(event_id not in seen_event_ids, f"duplicate event_id detected: {event_id}")
        require(idem_key not in seen_idempotency_keys, f"duplicate processing_idempotency_key detected: {idem_key}")
        seen_event_ids.add(event_id)
        seen_idempotency_keys.add(idem_key)


def validate_paths(schema_path=SCHEMA_PATH, sample_path=SAMPLE_PATH):
    schema = load_json(schema_path)
    sample = load_json(sample_path)
    validate_schema_file(schema)
    validate_event_collection(sample)


def main():
    try:
        validate_paths()
    except Exception as exc:
        print(f"Evidence event schema validation: FAIL - {exc}")
        return 1
    print("Evidence event schema validation: PASS")
    print(f"Validated {SCHEMA_PATH.relative_to(BASE_DIR)}")
    print(f"Validated {SAMPLE_PATH.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
