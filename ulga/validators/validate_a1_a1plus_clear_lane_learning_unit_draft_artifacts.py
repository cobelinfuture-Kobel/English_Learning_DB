import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
LANE_PACKET = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_lane_packet.json"
DRAFTS = BASE / "ulga" / "learning_units" / "draft" / "a1_a1plus_clear_lane_learning_unit_draft_artifacts.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_learning_unit_draft_artifacts_summary.json"
TASK_ID = "R7-M104E10_A1A1PlusClearLaneLearningUnitDraftArtifactsImplementation"
EXPECTED_DRAFT_COUNT = 19
EXPECTED_TYPE_COUNTS = {
    "CONSTRUCTION_NODE": 6,
    "MULTI_NODE_COMPOSITE": 1,
    "PHRASE_PATTERN_NODE": 8,
    "SENTENCE_PATTERN_NODE": 3,
    "USAGE_CONSTRAINT": 1,
}
TYPE_TO_SCHEMA = {
    "PHRASE_PATTERN_NODE": BASE / "ulga" / "schemas" / "learning_units" / "phrase_pattern_unit_schema.json",
    "SENTENCE_PATTERN_NODE": BASE / "ulga" / "schemas" / "learning_units" / "sentence_pattern_unit_schema.json",
    "CONSTRUCTION_NODE": BASE / "ulga" / "schemas" / "learning_units" / "construction_unit_schema.json",
    "USAGE_CONSTRAINT": BASE / "ulga" / "schemas" / "learning_units" / "usage_constraint_unit_schema.json",
    "MULTI_NODE_COMPOSITE": BASE / "ulga" / "schemas" / "learning_units" / "composite_learning_unit_schema.json",
}


def fail(message):
    print("FAIL: " + message)
    return False


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path}: {exc}")


def validate_against_schema(unit, schema, schema_file):
    if schema.get("type") != "object":
        raise ValueError(f"{schema_file}: schema type must be object")
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    missing = sorted(field for field in required if field not in unit)
    if missing:
        raise ValueError(f"{unit.get('learning_unit_id')}: missing required fields {missing}")
    extra = sorted(field for field in unit if field not in properties)
    if extra:
        raise ValueError(f"{unit.get('learning_unit_id')}: unknown fields {extra}")
    expected_type = properties.get("learning_unit_type", {}).get("const")
    if unit.get("learning_unit_type") != expected_type:
        raise ValueError(f"{unit.get('learning_unit_id')}: learning_unit_type mismatch")
    cefr_enum = properties.get("cefr_level", {}).get("enum", [])
    if unit.get("cefr_level") not in cefr_enum:
        raise ValueError(f"{unit.get('learning_unit_id')}: cefr_level mismatch")
    for field in ["egp_cluster_refs", "source_refs"]:
        value = unit.get(field)
        if not isinstance(value, list) or not value:
            raise ValueError(f"{unit.get('learning_unit_id')}: {field} must be non-empty array")
    if unit.get("status") != "draft":
        raise ValueError(f"{unit.get('learning_unit_id')}: status must be draft")


def count_by(values):
    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def validate():
    print("Validating A1/A1+ clear lane learning unit draft artifacts...")
    lane = load(LANE_PACKET)
    collection = load(DRAFTS)
    summary = load(SUMMARY)
    if collection.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    lane_ids = {item.get("cluster_id") for item in lane.get("clear_active_lane_items", [])}
    if len(lane_ids) != EXPECTED_DRAFT_COUNT:
        return fail("source clear lane count mismatch")
    artifacts = collection.get("draft_artifacts", [])
    if len(artifacts) != EXPECTED_DRAFT_COUNT:
        return fail("draft_artifact_count mismatch")
    seen_artifact_ids = set()
    seen_learning_unit_ids = set()
    seen_cluster_ids = set()
    learning_types = []
    artifact_statuses = []
    cefr_levels = []
    schema_paths = set()
    for artifact in artifacts:
        artifact_id = artifact.get("artifact_id")
        if not artifact_id or artifact_id in seen_artifact_ids:
            return fail("missing or duplicate artifact_id")
        seen_artifact_ids.add(artifact_id)
        if artifact.get("artifact_status") != "DRAFT_NOT_CANONICAL":
            return fail("artifact_status must be DRAFT_NOT_CANONICAL")
        source_cluster = artifact.get("source_cluster", {})
        cid = source_cluster.get("cluster_id")
        if cid not in lane_ids:
            return fail("draft artifact source cluster not in clear lane")
        seen_cluster_ids.add(cid)
        unit = artifact.get("draft_learning_unit", {})
        unit_id = unit.get("learning_unit_id")
        if not unit_id or unit_id in seen_learning_unit_ids:
            return fail("missing or duplicate learning_unit_id")
        seen_learning_unit_ids.add(unit_id)
        if unit.get("egp_cluster_refs") != [cid]:
            return fail("egp_cluster_refs must match source cluster")
        lut = unit.get("learning_unit_type")
        if lut not in TYPE_TO_SCHEMA:
            return fail("unsupported learning_unit_type")
        expected_schema = TYPE_TO_SCHEMA[lut]
        schema_path = artifact.get("schema_contract_path")
        if schema_path != str(expected_schema.relative_to(BASE)).replace("\\", "/"):
            return fail("schema_contract_path mismatch")
        schema = load(expected_schema)
        validate_against_schema(unit, schema, expected_schema.name)
        promotion = artifact.get("promotion_policy", {})
        if promotion.get("requires_operator_review_before_promotion") is not True:
            return fail("promotion review gate must be true")
        if promotion.get("canonical_grammar_write_allowed") is not False:
            return fail("canonical grammar write must be false")
        if promotion.get("canonical_pattern_write_allowed") is not False:
            return fail("canonical pattern write must be false")
        learning_types.append(lut)
        artifact_statuses.append(artifact.get("artifact_status"))
        cefr_levels.append(unit.get("cefr_level"))
        schema_paths.add(schema_path)
    if seen_cluster_ids != lane_ids:
        return fail("draft artifacts do not cover clear lane exactly")
    type_counts = count_by(learning_types)
    if type_counts != EXPECTED_TYPE_COUNTS:
        return fail("learning_unit_type_counts mismatch")
    expected_summary_values = {
        "validation_status": "PASS",
        "draft_artifact_count": EXPECTED_DRAFT_COUNT,
        "schema_contract_file_count": len(TYPE_TO_SCHEMA),
        "learning_unit_type_counts": EXPECTED_TYPE_COUNTS,
        "artifact_status_counts": {"DRAFT_NOT_CANONICAL": EXPECTED_DRAFT_COUNT},
        "cefr_level_counts": {"A1": EXPECTED_DRAFT_COUNT},
        "foundation_not_final_taxonomy": True,
        "future_extension_allowed": True,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E11_A1A1PlusClearLaneDraftArtifactReviewPacket",
        "stop_reason": "OPERATOR_REVIEW_REQUIRED",
    }
    for key, expected in expected_summary_values.items():
        if summary.get(key) != expected:
            return fail(f"summary {key} mismatch")
    for key in ["deferred_lane_processing_allowed", "final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
        if collection.get(key) is not False:
            return fail(f"collection {key} must be false")
    if collection.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if collection.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    print("A1/A1+ clear lane learning unit draft artifacts validation: PASS")
    print("Draft artifacts:", len(artifacts))
    print("Learning unit types:", type_counts)
    return True


if __name__ == "__main__":
    try:
        ok = validate()
    except Exception as exc:
        ok = fail(str(exc))
    if not ok:
        sys.exit(1)
