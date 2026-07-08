import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DRAFTS_PATH = BASE / "ulga" / "learning_units" / "draft" / "a1_a1plus_clear_lane_learning_unit_draft_artifacts.json"
TASK_ID = "R7-M104E16B_A1A1PlusDraftArtifactFieldCompletionPatch_NoNewDesignDocs"
EXPECTED_ARTIFACT_COUNT = 19
EXPECTED_PATCHED_FIELD_COUNT = 48
EXPECTED_TYPE_COUNTS = {
    "CONSTRUCTION_NODE": 6,
    "MULTI_NODE_COMPOSITE": 1,
    "PHRASE_PATTERN_NODE": 8,
    "SENTENCE_PATTERN_NODE": 3,
    "USAGE_CONSTRAINT": 1,
}
FORBIDDEN_PLACEHOLDER_STRINGS = {
    "DRAFT_EXAMPLE_REQUIRES_OPERATOR_REVIEW",
    "DRAFT_COMPONENT_NODE_REQUIRES_OPERATOR_REVIEW",
    "DRAFT_SLOT_SEQUENCE_REQUIRES_OPERATOR_REVIEW",
}


def fail(message):
    print("FAIL: " + message)
    return False


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def count_by(items, key_fn):
    result = {}
    for item in items:
        key = key_fn(item)
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def walk(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)
        yield value
    else:
        yield value


def contains_forbidden_placeholder(value):
    for node in walk(value):
        if isinstance(node, dict) and node.get("status") == "draft_placeholder":
            return True
        if isinstance(node, str):
            if "draft_placeholder" in node:
                return True
            if any(marker in node for marker in FORBIDDEN_PLACEHOLDER_STRINGS):
                return True
    return False


def validate_learning_unit(artifact):
    unit = artifact.get("draft_learning_unit", {})
    cluster = artifact.get("source_cluster", {})
    cluster_id = cluster.get("cluster_id")
    lut = unit.get("learning_unit_type")
    if artifact.get("artifact_status") != "DRAFT_NOT_CANONICAL":
        return fail("artifact_status must remain DRAFT_NOT_CANONICAL")
    if unit.get("status") != "draft":
        return fail("draft_learning_unit status must remain draft")
    if contains_forbidden_placeholder(unit):
        return fail(f"forbidden placeholder remains in {artifact.get('artifact_id')}")
    if not unit.get("source_refs") or not unit.get("egp_cluster_refs"):
        return fail("source_refs and egp_cluster_refs are required")
    if lut == "CONSTRUCTION_NODE":
        for key in ["head_pattern", "complement_model"]:
            if not isinstance(unit.get(key), dict) or unit[key].get("patch_status") != "draft_field_completed_not_canonical":
                return fail(f"{key} not patched")
        if not unit.get("positive_examples"):
            return fail("positive_examples missing")
    elif lut == "PHRASE_PATTERN_NODE":
        if not isinstance(unit.get("slot_model"), dict) or unit["slot_model"].get("patch_status") != "draft_field_completed_not_canonical":
            return fail("slot_model not patched")
        if not unit.get("positive_examples"):
            return fail("positive_examples missing")
    elif lut == "SENTENCE_PATTERN_NODE":
        if not isinstance(unit.get("sentence_role_model"), dict) or unit["sentence_role_model"].get("patch_status") != "draft_field_completed_not_canonical":
            return fail("sentence_role_model not patched")
        if not isinstance(unit.get("slot_sequence"), list) or not unit["slot_sequence"]:
            return fail("slot_sequence not patched")
        if not unit.get("positive_examples"):
            return fail("positive_examples missing")
    elif lut == "MULTI_NODE_COMPOSITE":
        if not isinstance(unit.get("component_node_refs"), list) or not unit["component_node_refs"]:
            return fail("component_node_refs not patched")
        if any("DRAFT_COMPONENT_NODE_REQUIRES_OPERATOR_REVIEW" in ref for ref in unit["component_node_refs"]):
            return fail("component_node_refs still contain placeholder marker")
        for key in ["composition_rule", "role_mapping"]:
            if not isinstance(unit.get(key), dict) or unit[key].get("patch_status") != "draft_field_completed_not_canonical":
                return fail(f"{key} not patched")
        if not unit.get("positive_examples"):
            return fail("positive_examples missing")
    elif lut == "USAGE_CONSTRAINT":
        if not unit.get("examples"):
            return fail("usage constraint examples missing")
        if not unit.get("allowed_values"):
            return fail("usage constraint allowed_values missing")
    else:
        return fail(f"unexpected learning_unit_type {lut}")
    patch = artifact.get("field_completion_patch", {})
    if patch.get("task_id") != TASK_ID:
        return fail("artifact patch task_id mismatch")
    if patch.get("coverage_credit_now") != 0:
        return fail("patch coverage_credit_now must be zero")
    for key in ["canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
        if patch.get(key) is not False:
            return fail(f"patch {key} must be false")
    if cluster_id not in unit.get("egp_cluster_refs", []):
        return fail("cluster_id must remain in egp_cluster_refs")
    return True


def validate():
    print("Validating A1/A1+ clear lane draft artifact field completion patch...")
    data = load(DRAFTS_PATH)
    artifacts = data.get("draft_artifacts", [])
    if len(artifacts) != EXPECTED_ARTIFACT_COUNT:
        return fail("draft artifact count mismatch")
    type_counts = count_by(artifacts, lambda artifact: artifact.get("draft_learning_unit", {}).get("learning_unit_type"))
    if type_counts != EXPECTED_TYPE_COUNTS:
        return fail("learning_unit_type_counts mismatch")
    for artifact in artifacts:
        ok = validate_learning_unit(artifact)
        if ok is not True:
            return False
    metadata = data.get("field_completion_patch_metadata", {})
    if metadata.get("task_id") != TASK_ID:
        return fail("patch metadata task_id mismatch")
    if metadata.get("draft_artifact_count") != EXPECTED_ARTIFACT_COUNT:
        return fail("metadata draft_artifact_count mismatch")
    if metadata.get("patched_field_count") != EXPECTED_PATCHED_FIELD_COUNT:
        return fail("metadata patched_field_count mismatch")
    if metadata.get("coverage_credit_now") != 0:
        return fail("metadata coverage_credit_now must be zero")
    for key in [
        "new_design_docs_created",
        "new_planning_docs_created",
        "canonical_grammar_write_allowed",
        "canonical_pattern_write_allowed",
        "a2_a2plus_progression_allowed",
    ]:
        if metadata.get(key) is not False:
            return fail(f"metadata {key} must be false")
    if contains_forbidden_placeholder(data):
        return fail("forbidden placeholder remains in draft artifact file")
    print("A1/A1+ clear lane draft artifact field completion patch validation: PASS")
    print("Draft artifacts patched:", EXPECTED_ARTIFACT_COUNT)
    print("Patched fields:", EXPECTED_PATCHED_FIELD_COUNT)
    print("Coverage credit now: 0")
    return True


if __name__ == "__main__":
    try:
        ok = validate()
    except Exception as exc:
        ok = fail(str(exc))
    if not ok:
        sys.exit(1)
