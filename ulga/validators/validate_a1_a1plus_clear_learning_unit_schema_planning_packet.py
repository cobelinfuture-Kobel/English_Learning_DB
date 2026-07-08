import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_schema_planning_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_schema_planning_packet_summary.json"
TASK_ID = "R7-M104E6_A1A1PlusClearLearningUnitSchemaPlanningPacket"
EXPECTED_CLEAR_COUNT = 19
EXPECTED_TYPES = {
    "CONSTRUCTION_NODE": 6,
    "MULTI_NODE_COMPOSITE": 1,
    "PHRASE_PATTERN_NODE": 8,
    "SENTENCE_PATTERN_NODE": 3,
    "USAGE_CONSTRAINT": 1,
}
EXPECTED_FAMILIES = {
    "composite_learning_unit_schema": 1,
    "construction_schema": 6,
    "phrase_pattern_schema": 8,
    "sentence_pattern_schema": 3,
    "usage_constraint_schema": 1,
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
    print("Validating A1/A1+ clear learning unit schema planning packet...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required schema planning files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    groups = report.get("schema_groups", [])
    if not groups:
        return fail("schema_groups missing")
    seen = set()
    type_counts = {}
    family_counts = {}
    planning_items = 0
    for group in groups:
        lut = group.get("learning_unit_type")
        family = group.get("schema_family")
        items = group.get("items", [])
        if group.get("item_count") != len(items):
            return fail("group item_count mismatch")
        if not group.get("required_fields"):
            return fail("group required_fields missing")
        planning_items += len(items)
        type_counts[lut] = type_counts.get(lut, 0) + len(items)
        family_counts[family] = family_counts.get(family, 0) + len(items)
        for item in items:
            cid = item.get("cluster_id")
            if not cid or cid in seen:
                return fail("missing or duplicate schema planning cluster_id")
            seen.add(cid)
            if item.get("learning_unit_type") != lut:
                return fail("item learning_unit_type mismatch")
            if item.get("schema_family") != family:
                return fail("item schema_family mismatch")
            if item.get("operator_schema_review_status") != "PENDING_OPERATOR_REVIEW":
                return fail("item must be pending operator schema review")
            if item.get("canonical_grammar_write_allowed") is not False:
                return fail("item canonical grammar write must be false")
            if item.get("canonical_pattern_write_allowed") is not False:
                return fail("item canonical pattern write must be false")
            if not item.get("required_fields"):
                return fail("item required_fields missing")
    if planning_items != EXPECTED_CLEAR_COUNT or len(seen) != EXPECTED_CLEAR_COUNT:
        return fail("schema planning item count mismatch")
    if type_counts != EXPECTED_TYPES:
        return fail("learning unit type counts mismatch")
    if family_counts != EXPECTED_FAMILIES:
        return fail("schema family counts mismatch")
    if summary.get("source_clear_active_lane_item_count") != EXPECTED_CLEAR_COUNT:
        return fail("source_clear_active_lane_item_count mismatch")
    if summary.get("schema_group_count") != len(groups):
        return fail("schema_group_count mismatch")
    if summary.get("schema_planning_item_count") != EXPECTED_CLEAR_COUNT:
        return fail("schema_planning_item_count mismatch")
    if summary.get("learning_unit_type_counts") != EXPECTED_TYPES:
        return fail("summary learning_unit_type_counts mismatch")
    if summary.get("schema_family_counts") != EXPECTED_FAMILIES:
        return fail("summary schema_family_counts mismatch")
    if summary.get("deferred_lane_processing_allowed") is not False:
        return fail("deferred lane processing must be false")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
        if report.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104E7_A1A1PlusClearLearningUnitSchemaPlanReview":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "OPERATOR_REVIEW_REQUIRED":
        return fail("stop_reason mismatch")
    print("A1/A1+ clear learning unit schema planning packet validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
