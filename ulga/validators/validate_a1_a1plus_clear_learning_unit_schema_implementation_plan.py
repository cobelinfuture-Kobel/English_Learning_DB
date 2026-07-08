import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_schema_implementation_plan.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_schema_implementation_plan_summary.json"
TASK_ID = "R7-M104E7_A1A1PlusClearLearningUnitSchemaImplementationPlan"
EXPECTED_ITEM_COUNT = 19
EXPECTED_FAMILIES = {
    "composite_learning_unit_schema": 1,
    "construction_schema": 6,
    "phrase_pattern_schema": 8,
    "sentence_pattern_schema": 3,
    "usage_constraint_schema": 1,
}
REQUIRED_FUTURE_EXTENSIONS = {
    "clause pattern schema",
    "discourse connector schema",
    "paragraph structure schema",
    "essay structure schema",
    "writing genre schema",
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
    print("Validating A1/A1+ clear learning unit schema implementation plan...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required implementation plan files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    units = report.get("implementation_units", [])
    if not units:
        return fail("implementation_units missing")
    family_counts = {}
    cluster_ids = set()
    item_total = 0
    for unit in units:
        family = unit.get("schema_family")
        count = unit.get("source_item_count")
        clusters = unit.get("source_clusters", [])
        if count != len(clusters):
            return fail("unit source_item_count mismatch")
        if not unit.get("planned_schema_path", "").startswith("ulga/schemas/learning_units/"):
            return fail("planned_schema_path must live under ulga/schemas/learning_units")
        if not unit.get("planned_builder_family"):
            return fail("planned_builder_family missing")
        if not unit.get("planned_validator_family"):
            return fail("planned_validator_family missing")
        if unit.get("graph_output_policy") != "planned_static_report_only_before_canonical_promotion":
            return fail("graph_output_policy mismatch")
        if not unit.get("minimum_contract_fields"):
            return fail("minimum_contract_fields missing")
        item_total += len(clusters)
        family_counts[family] = family_counts.get(family, 0) + len(clusters)
        for cluster in clusters:
            cid = cluster.get("cluster_id")
            if not cid or cid in cluster_ids:
                return fail("missing or duplicate cluster_id")
            cluster_ids.add(cid)
    if item_total != EXPECTED_ITEM_COUNT:
        return fail("source item total mismatch")
    if family_counts != EXPECTED_FAMILIES:
        return fail("schema family counts mismatch")
    if summary.get("source_schema_group_count") != len(units):
        return fail("source_schema_group_count mismatch")
    if summary.get("implementation_unit_count") != len(units):
        return fail("implementation_unit_count mismatch")
    if summary.get("source_schema_planning_item_count") != EXPECTED_ITEM_COUNT:
        return fail("source_schema_planning_item_count mismatch")
    if summary.get("schema_family_counts") != EXPECTED_FAMILIES:
        return fail("summary schema_family_counts mismatch")
    if summary.get("foundation_not_final_taxonomy") is not True:
        return fail("foundation_not_final_taxonomy must be true")
    if summary.get("future_extension_allowed") is not True:
        return fail("future_extension_allowed must be true")
    if not REQUIRED_FUTURE_EXTENSIONS.issubset(set(report.get("future_extension_allowed", []))):
        return fail("future_extension_allowed list incomplete")
    if summary.get("deferred_lane_processing_allowed") is not False:
        return fail("deferred lane processing must be false")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
        if report.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104E8_A1A1PlusLearningUnitSchemaContractDesign":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason mismatch")
    print("A1/A1+ clear learning unit schema implementation plan validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
