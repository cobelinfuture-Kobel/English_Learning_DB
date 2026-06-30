import json
import re
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
LEARNER_STATE_DIR = BASE_DIR / "ulga" / "learner_state"
SCHEMA_PATH = LEARNER_STATE_DIR / "learner_state_schema.json"
SAMPLE_PATH = LEARNER_STATE_DIR / "sample_learner_state.json"

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
MASTERY_BANDS = {
    "unknown",
    "seen",
    "practicing",
    "functional",
    "mastered",
    "automatic",
}
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
MASTERY_BAND_RANGES = {
    "unknown": (0.00, 0.10, False),
    "seen": (0.10, 0.25, False),
    "practicing": (0.25, 0.50, False),
    "functional": (0.50, 0.70, False),
    "mastered": (0.70, 0.90, False),
    "automatic": (0.90, 1.00, True),
}


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
        "node_type_enum",
        "mastery_band_enum",
        "learner_state_collection_schema",
    }
    require(isinstance(schema, dict), "schema must be a JSON object")
    properties = schema.get("properties")
    require(isinstance(properties, dict), "schema.properties must be an object")
    require(required_top_level.issubset(properties), "schema missing required top-level sections")
    require(set(schema.get("required", [])) == required_top_level, "schema.required mismatch")

    metadata = properties["contract_metadata"]["properties"]
    require(metadata["contract_id"]["const"] == "ulga.learner_state", "schema contract_id mismatch")
    require(metadata["contract_version"]["const"] == "ULGA-S9C", "schema contract_version mismatch")
    require(metadata["schema_version"]["const"] == "1.0.0", "schema schema_version mismatch")
    require(
        metadata["source_design_scan"]["const"] == "docs/ulga/ULGA_S9A_LEARNER_STATE_AUTHORITY_DESIGN_SCAN.md",
        "schema source_design_scan mismatch",
    )
    require(
        metadata["schema_only_no_builder_logic"]["const"] is True,
        "schema must declare no builder logic",
    )
    require(set(properties["node_type_enum"]["items"]["enum"]) == NODE_TYPES, "schema node_type_enum mismatch")
    require(set(properties["mastery_band_enum"]["items"]["enum"]) == MASTERY_BANDS, "schema mastery_band_enum mismatch")


def validate_iso_like_timestamp(value, field_name, allow_null=False):
    if value is None:
        require(allow_null, f"{field_name} must be an ISO-like string")
        return
    require(isinstance(value, str) and TIMESTAMP_RE.match(value), f"{field_name} must be an ISO-like string")


def validate_mastery_band_matches_score(score, mastery_band, path_label):
    require(mastery_band in MASTERY_BAND_RANGES, f"{path_label}.mastery_band is invalid: {mastery_band}")
    min_score, max_score, inclusive_max = MASTERY_BAND_RANGES[mastery_band]
    if inclusive_max:
        is_valid = min_score <= score <= max_score
    else:
        is_valid = min_score <= score < max_score
    require(is_valid, f"{path_label}.mastery_band does not match mastery_score range")


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
    required = {"authority_name", "derivation", "aggregation_version"}
    require(isinstance(source, dict), f"{path_label}.source must be an object")
    require(required.issubset(source), f"{path_label}.source missing required fields: {sorted(required - set(source))}")
    require(
        source["authority_name"] == "LearnerStateAuthority",
        f"{path_label}.source.authority_name must equal LearnerStateAuthority",
    )
    for key in {"derivation", "aggregation_version"}:
        require(isinstance(source[key], str) and source[key].strip(), f"{path_label}.source.{key} must be a non-empty string")
    if "notes" in source:
        require(isinstance(source["notes"], list), f"{path_label}.source.notes must be a list")


def validate_evidence_refs(evidence_refs, path_label):
    require(isinstance(evidence_refs, list), f"{path_label}.evidence_refs must be an array")
    for evidence_index, evidence_ref in enumerate(evidence_refs):
        require(
            isinstance(evidence_ref, str) and evidence_ref.strip(),
            f"{path_label}.evidence_refs[{evidence_index}] must be a non-empty string",
        )


def validate_record(record, record_index):
    path_label = f"learner_state_records[{record_index}]"
    required = {
        "learner_id",
        "node_id",
        "node_type",
        "mastery_score",
        "mastery_band",
        "exposure_count",
        "correct_count",
        "incorrect_count",
        "last_seen_at",
        "last_success_at",
        "evidence_refs",
        "decay_adjusted_score",
        "review_due_at",
        "confidence",
        "source",
        "state_updated_at",
        "processing_idempotency_key",
    }
    require(isinstance(record, dict), f"{path_label} must be an object")
    require(required.issubset(record), f"{path_label} missing required fields: {sorted(required - set(record))}")
    require(isinstance(record["learner_id"], str) and record["learner_id"].strip(), f"{path_label}.learner_id must be a non-empty string")
    require(isinstance(record["node_id"], str) and record["node_id"].strip(), f"{path_label}.node_id must be a non-empty string")
    require(record["node_type"] in NODE_TYPES, f"{path_label}.node_type is invalid: {record['node_type']}")

    mastery_score = record["mastery_score"]
    require(isinstance(mastery_score, (int, float)), f"{path_label}.mastery_score must be a number")
    require(0 <= mastery_score <= 1, f"{path_label}.mastery_score must be between 0 and 1")
    mastery_band = record["mastery_band"]
    require(mastery_band in MASTERY_BANDS, f"{path_label}.mastery_band is invalid: {mastery_band}")
    validate_mastery_band_matches_score(mastery_score, mastery_band, path_label)

    exposure_count = record["exposure_count"]
    correct_count = record["correct_count"]
    incorrect_count = record["incorrect_count"]
    require(isinstance(exposure_count, int) and exposure_count >= 0, f"{path_label}.exposure_count must be an integer >= 0")
    require(isinstance(correct_count, int) and correct_count >= 0, f"{path_label}.correct_count must be an integer >= 0")
    require(isinstance(incorrect_count, int) and incorrect_count >= 0, f"{path_label}.incorrect_count must be an integer >= 0")
    require(
        correct_count + incorrect_count <= exposure_count,
        f"{path_label}.correct_count + incorrect_count must not exceed exposure_count",
    )

    validate_iso_like_timestamp(record["last_seen_at"], f"{path_label}.last_seen_at", allow_null=True)
    validate_iso_like_timestamp(record["last_success_at"], f"{path_label}.last_success_at", allow_null=True)
    validate_iso_like_timestamp(record["review_due_at"], f"{path_label}.review_due_at", allow_null=True)
    validate_iso_like_timestamp(record["state_updated_at"], f"{path_label}.state_updated_at")
    validate_evidence_refs(record["evidence_refs"], path_label)

    decay_adjusted_score = record["decay_adjusted_score"]
    require(isinstance(decay_adjusted_score, (int, float)), f"{path_label}.decay_adjusted_score must be a number")
    require(0 <= decay_adjusted_score <= 1, f"{path_label}.decay_adjusted_score must be between 0 and 1")

    validate_confidence(record["confidence"], path_label)
    validate_source(record["source"], path_label)
    require(
        isinstance(record["processing_idempotency_key"], str) and record["processing_idempotency_key"].strip(),
        f"{path_label}.processing_idempotency_key must be a non-empty string",
    )


def validate_learner_state_collection(payload):
    require(isinstance(payload, dict), "sample learner state payload must be an object")
    require(payload.get("contract_version") == "ULGA-S9C", "sample learner state contract_version must be ULGA-S9C")
    records = payload.get("learner_state_records")
    require(isinstance(records, list) and records, "sample learner state must contain a non-empty learner_state_records array")

    seen_pairs = set()
    seen_idempotency_keys = set()
    for record_index, record in enumerate(records):
        validate_record(record, record_index)
        pair = (record["learner_id"], record["node_id"])
        idem_key = record["processing_idempotency_key"]
        require(pair not in seen_pairs, f"duplicate learner_id + node_id detected: {pair[0]} | {pair[1]}")
        require(idem_key not in seen_idempotency_keys, f"duplicate processing_idempotency_key detected: {idem_key}")
        seen_pairs.add(pair)
        seen_idempotency_keys.add(idem_key)


def validate_paths(schema_path=SCHEMA_PATH, sample_path=SAMPLE_PATH):
    schema = load_json(schema_path)
    sample = load_json(sample_path)
    validate_schema_file(schema)
    validate_learner_state_collection(sample)


def main():
    try:
        validate_paths()
    except Exception as exc:
        print(f"Learner state schema validation: FAIL - {exc}")
        return 1
    print("Learner state schema validation: PASS")
    print(f"Validated {SCHEMA_PATH.relative_to(BASE_DIR)}")
    print(f"Validated {SAMPLE_PATH.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
