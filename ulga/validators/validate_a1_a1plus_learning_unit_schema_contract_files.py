import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SCHEMA_DIR = BASE / "ulga" / "schemas" / "learning_units"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_learning_unit_schema_contract_files_validation_summary.json"
TASK_ID = "R7-M104E9_A1A1PlusLearningUnitSchemaContractFilesImplementation"

EXPECTED_SCHEMAS = {
    "phrase_pattern_unit_schema.json": {
        "learning_unit_type": "PHRASE_PATTERN_NODE",
        "required_specific_fields": {
            "phrase_head_type",
            "slot_model",
            "constraints",
            "positive_examples",
            "negative_examples",
        },
    },
    "sentence_pattern_unit_schema.json": {
        "learning_unit_type": "SENTENCE_PATTERN_NODE",
        "required_specific_fields": {
            "sentence_role_model",
            "slot_sequence",
            "transformations",
            "positive_examples",
            "negative_examples",
        },
    },
    "construction_unit_schema.json": {
        "learning_unit_type": "CONSTRUCTION_NODE",
        "required_specific_fields": {
            "construction_type",
            "head_pattern",
            "complement_model",
            "constraints",
            "positive_examples",
            "negative_examples",
        },
    },
    "usage_constraint_unit_schema.json": {
        "learning_unit_type": "USAGE_CONSTRAINT",
        "required_specific_fields": {
            "constraint_type",
            "applies_to",
            "allowed_values",
            "blocked_values",
            "examples",
        },
    },
    "composite_learning_unit_schema.json": {
        "learning_unit_type": "MULTI_NODE_COMPOSITE",
        "required_specific_fields": {
            "component_node_refs",
            "composition_rule",
            "role_mapping",
            "positive_examples",
            "negative_examples",
        },
    },
}

COMMON_REQUIRED_FIELDS = {
    "learning_unit_id",
    "learning_unit_type",
    "schema_version",
    "cefr_level",
    "egp_cluster_refs",
    "source_refs",
    "status",
}
POLICY_FALSE_FIELDS = {
    "deferred_lane_processing_allowed",
    "a2_a2plus_progression_allowed",
    "canonical_grammar_write_allowed",
    "canonical_pattern_write_allowed",
}
POLICY_TRUE_FIELDS = {
    "foundation_not_final_taxonomy",
    "future_extension_allowed",
}


def fail(message):
    print("FAIL: " + message)
    write_summary("FAIL", error=message)
    return False


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path}: {exc}")


def validate_schema_file(filename, meta):
    path = SCHEMA_DIR / filename
    if not path.exists():
        raise ValueError(f"missing schema file: {filename}")
    schema = load_json(path)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ValueError(f"{filename}: $schema mismatch")
    if schema.get("type") != "object":
        raise ValueError(f"{filename}: type must be object")
    if schema.get("additionalProperties") is not False:
        raise ValueError(f"{filename}: additionalProperties must be false")
    required = set(schema.get("required", []))
    expected_required = COMMON_REQUIRED_FIELDS | meta["required_specific_fields"]
    if not expected_required.issubset(required):
        missing = sorted(expected_required - required)
        raise ValueError(f"{filename}: missing required fields {missing}")
    properties = schema.get("properties", {})
    for field in required:
        if field not in properties:
            raise ValueError(f"{filename}: required field {field} missing from properties")
    learning_type = properties.get("learning_unit_type", {}).get("const")
    if learning_type != meta["learning_unit_type"]:
        raise ValueError(f"{filename}: learning_unit_type const mismatch")
    cefr_enum = properties.get("cefr_level", {}).get("enum")
    if cefr_enum != ["A1", "A1_PLUS"]:
        raise ValueError(f"{filename}: cefr_level enum mismatch")
    for array_field in ["egp_cluster_refs", "source_refs"]:
        if properties.get(array_field, {}).get("minItems") != 1:
            raise ValueError(f"{filename}: {array_field} must require minItems=1")
    policy = schema.get("x_policy", {})
    if policy.get("task_id") != TASK_ID:
        raise ValueError(f"{filename}: x_policy task_id mismatch")
    for key in POLICY_TRUE_FIELDS:
        if policy.get(key) is not True:
            raise ValueError(f"{filename}: x_policy {key} must be true")
    for key in POLICY_FALSE_FIELDS:
        if policy.get(key) is not False:
            raise ValueError(f"{filename}: x_policy {key} must be false")
    return {
        "filename": filename,
        "path": str(path.relative_to(BASE)).replace("\\", "/"),
        "learning_unit_type": learning_type,
        "required_field_count": len(required),
        "policy": policy,
    }


def write_summary(status, validated_files=None, error=None):
    validated_files = validated_files or []
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    learning_unit_type_counts = {}
    field_counts = {}
    for item in validated_files:
        learning_unit_type_counts[item["learning_unit_type"]] = learning_unit_type_counts.get(item["learning_unit_type"], 0) + 1
        field_counts[item["filename"]] = item["required_field_count"]
    payload = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_learning_unit_schema_contract_files_validation_summary",
        "validation_status": status,
        "schema_contract_file_count": len(validated_files),
        "schema_contract_files": validated_files,
        "learning_unit_type_counts": dict(sorted(learning_unit_type_counts.items())),
        "required_field_counts": dict(sorted(field_counts.items())),
        "foundation_not_final_taxonomy": True,
        "future_extension_allowed": True,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E10_A1A1PlusClearLaneLearningUnitDraftArtifactsImplementation",
        "stop_reason": "OPERATOR_APPROVAL_REQUIRED",
    }
    if error:
        payload["error"] = error
    SUMMARY.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate():
    print("Validating A1/A1+ learning unit schema contract files...")
    validated_files = []
    for filename, meta in sorted(EXPECTED_SCHEMAS.items()):
        validated_files.append(validate_schema_file(filename, meta))
    write_summary("PASS", validated_files=validated_files)
    print("A1/A1+ learning unit schema contract files validation: PASS")
    print("Schema contract files:", len(validated_files))
    print("Summary:", SUMMARY.relative_to(BASE))
    return True


if __name__ == "__main__":
    try:
        ok = validate()
    except Exception as exc:
        ok = fail(str(exc))
    if not ok:
        sys.exit(1)
