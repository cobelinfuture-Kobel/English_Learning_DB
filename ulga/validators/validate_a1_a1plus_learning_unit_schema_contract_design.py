import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_learning_unit_schema_contract_design.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_learning_unit_schema_contract_design_summary.json"
TASK_ID = "R7-M104E8_A1A1PlusLearningUnitSchemaContractDesign"
EXPECTED_ITEM_COUNT = 19
EXPECTED_FAMILIES = {
    "composite_learning_unit_schema": 1,
    "construction_schema": 6,
    "phrase_pattern_schema": 8,
    "sentence_pattern_schema": 3,
    "usage_constraint_schema": 1,
}
REQUIRED_COMMON_FIELDS = {
    "learning_unit_id",
    "learning_unit_type",
    "schema_version",
    "cefr_level",
    "egp_cluster_refs",
    "source_refs",
    "status",
}


def fail(message):
    print("FAIL: " + message)
    return False


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: {path}: {exc}")
        return None


def validate():
    print("Validating A1/A1+ learning unit schema contract design...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required contract design files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    designs = report.get("contract_designs", [])
    if len(designs) != len(EXPECTED_FAMILIES):
        return fail("contract_design_count mismatch")
    family_counts = {}
    field_counts = {}
    source_cluster_ids = set()
    total_items = 0
    for design in designs:
        family = design.get("schema_family")
        if family not in EXPECTED_FAMILIES:
            return fail("unexpected schema_family")
        if design.get("contract_status") != "DESIGN_ONLY_NOT_IMPLEMENTED":
            return fail("contract_status must be design-only")
        if not design.get("planned_schema_path", "").startswith("ulga/schemas/learning_units/"):
            return fail("planned_schema_path must live under ulga/schemas/learning_units")
        draft = design.get("draft_schema_contract", {})
        if draft.get("type") != "object":
            return fail("draft schema type must be object")
        if draft.get("additionalProperties") is not False:
            return fail("additionalProperties must be false")
        required = set(draft.get("required", []))
        if not REQUIRED_COMMON_FIELDS.issubset(required):
            return fail("common required fields missing")
        properties = draft.get("properties", {})
        for field in required:
            if field not in properties:
                return fail("required field missing from properties")
        if draft.get("properties", {}).get("cefr_level", {}).get("enum") != ["A1", "A1_PLUS"]:
            return fail("cefr_level enum mismatch")
        validator_contract = design.get("validator_contract", {})
        for key in [
            "must_validate_required_fields",
            "must_reject_unknown_fields",
            "must_validate_cefr_a1_a1plus_only",
            "must_require_egp_cluster_refs",
            "must_require_source_refs",
            "must_keep_canonical_write_blocked",
        ]:
            if validator_contract.get(key) is not True:
                return fail(f"validator contract {key} must be true")
        builder_contract = design.get("builder_contract", {})
        if builder_contract.get("output_policy") != "static report artifacts only before canonical promotion":
            return fail("builder output policy mismatch")
        cluster_ids = builder_contract.get("source_cluster_ids", [])
        if len(cluster_ids) != design.get("source_item_count"):
            return fail("source_cluster_ids count mismatch")
        for cid in cluster_ids:
            if not cid or cid in source_cluster_ids:
                return fail("missing or duplicate source cluster id")
            source_cluster_ids.add(cid)
        count = design.get("source_item_count")
        family_counts[family] = family_counts.get(family, 0) + count
        field_counts[family] = len(draft.get("required", []))
        total_items += count
    if family_counts != EXPECTED_FAMILIES:
        return fail("schema_family_counts mismatch")
    if total_items != EXPECTED_ITEM_COUNT or len(source_cluster_ids) != EXPECTED_ITEM_COUNT:
        return fail("source item total mismatch")
    if report.get("implementation_not_started") is not True or summary.get("implementation_not_started") is not True:
        return fail("implementation_not_started must be true")
    foundation = report.get("foundation_policy", {})
    if foundation.get("foundation_not_final_taxonomy") is not True:
        return fail("foundation_not_final_taxonomy must be true")
    if foundation.get("future_extension_allowed") is not True:
        return fail("future_extension_allowed must be true")
    if summary.get("source_implementation_unit_count") != len(EXPECTED_FAMILIES):
        return fail("source_implementation_unit_count mismatch")
    if summary.get("contract_design_count") != len(EXPECTED_FAMILIES):
        return fail("contract_design_count mismatch")
    if summary.get("source_schema_planning_item_count") != EXPECTED_ITEM_COUNT:
        return fail("source_schema_planning_item_count mismatch")
    if summary.get("schema_family_counts") != EXPECTED_FAMILIES:
        return fail("summary schema_family_counts mismatch")
    if summary.get("contract_field_counts") != dict(sorted(field_counts.items())):
        return fail("contract_field_counts mismatch")
    if summary.get("foundation_not_final_taxonomy") is not True:
        return fail("summary foundation_not_final_taxonomy must be true")
    if summary.get("future_extension_allowed") is not True:
        return fail("summary future_extension_allowed must be true")
    if summary.get("deferred_lane_processing_allowed") is not False:
        return fail("deferred lane processing must be false")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
        if report.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104E9_A1A1PlusLearningUnitSchemaContractFilesImplementation":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "OPERATOR_APPROVAL_REQUIRED":
        return fail("stop_reason mismatch")
    print("A1/A1+ learning unit schema contract design validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
