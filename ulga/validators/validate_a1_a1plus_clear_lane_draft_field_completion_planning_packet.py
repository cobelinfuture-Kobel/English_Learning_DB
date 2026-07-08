import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DECISION_PACKET = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_artifact_operator_decision_packet.json"
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_planning_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_field_completion_planning_packet_summary.json"
TASK_ID = "R7-M104E13_A1A1PlusClearLaneDraftFieldCompletionPlanningPacket"
EXPECTED_COUNT = 19
EXPECTED_TYPE_COUNTS = {
    "CONSTRUCTION_NODE": 6,
    "MULTI_NODE_COMPOSITE": 1,
    "PHRASE_PATTERN_NODE": 8,
    "SENTENCE_PATTERN_NODE": 3,
    "USAGE_CONSTRAINT": 1,
}


def fail(message):
    print("FAIL: " + message)
    return False


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path}: {exc}")


def count_by(items, key_fn):
    counts = {}
    for item in items:
        key = key_fn(item)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def iter_decision_items(packet):
    for group in packet.get("decision_groups", []):
        for item in group.get("items", []):
            yield item


def validate():
    print("Validating A1/A1+ clear lane draft field completion planning packet...")
    decision_packet = load(DECISION_PACKET)
    report = load(REPORT)
    summary = load(SUMMARY)
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    decision_items = list(iter_decision_items(decision_packet))
    if len(decision_items) != EXPECTED_COUNT:
        return fail("source decision item count mismatch")
    decision_ids = {item.get("decision_item_id") for item in decision_items}
    decision_placeholder_total = sum(item.get("placeholder_field_count", 0) for item in decision_items)
    groups = report.get("planning_groups", [])
    if not groups:
        return fail("planning_groups missing")
    planning_items = []
    for group in groups:
        group_items = group.get("items", [])
        if group.get("planning_item_count") != len(group_items):
            return fail("group planning_item_count mismatch")
        if group.get("field_completion_task_count") != sum(len(item.get("field_completion_tasks", [])) for item in group_items):
            return fail("group field_completion_task_count mismatch")
        if group.get("placeholder_field_total") != sum(item.get("placeholder_field_count", 0) for item in group_items):
            return fail("group placeholder_field_total mismatch")
        for item in group_items:
            if item.get("learning_unit_type") != group.get("learning_unit_type"):
                return fail("item learning_unit_type mismatch with group")
            planning_items.append(item)
    if len(planning_items) != EXPECTED_COUNT:
        return fail("planning_item_count mismatch")
    seen_decisions = set()
    all_tasks = []
    for item in planning_items:
        did = item.get("decision_item_id")
        if did not in decision_ids or did in seen_decisions:
            return fail("missing, duplicate, or unknown decision_item_id")
        seen_decisions.add(did)
        if item.get("field_completion_status") != "PLANNED_NOT_IMPLEMENTED":
            return fail("field_completion_status must be PLANNED_NOT_IMPLEMENTED")
        if item.get("source_evidence_selection_required") is not True:
            return fail("source_evidence_selection_required must be true")
        for key in ["draft_artifact_update_allowed_now", "promotion_planning_allowed_now", "promotion_allowed_now", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
            if item.get(key) is not False:
                return fail(f"{key} must be false")
        fields = item.get("placeholder_fields_to_complete", [])
        tasks = item.get("field_completion_tasks", [])
        if item.get("placeholder_field_count") != len(fields):
            return fail("placeholder_field_count mismatch")
        if len(tasks) != len(fields):
            return fail("field_completion_tasks count mismatch")
        field_names = {task.get("field_name") for task in tasks}
        if field_names != set(fields):
            return fail("field task names must match placeholder fields")
        for task in tasks:
            if task.get("evidence_required") is not True:
                return fail("field completion task evidence_required must be true")
            if task.get("field_completion_status") != "SOURCE_EVIDENCE_REQUIRED":
                return fail("field completion task status mismatch")
            if task.get("implementation_allowed_now") is not False:
                return fail("field completion task implementation_allowed_now must be false")
            if task.get("canonical_write_allowed") is not False:
                return fail("field completion task canonical_write_allowed must be false")
            if not task.get("source_priority"):
                return fail("field completion task source_priority missing")
            all_tasks.append(task)
    type_counts = count_by(planning_items, lambda item: item.get("learning_unit_type"))
    if type_counts != EXPECTED_TYPE_COUNTS:
        return fail("learning_unit_type_counts mismatch")
    policy = report.get("planning_policy", {})
    expected_policy = {
        "field_completion_implementation_allowed_now": False,
        "source_evidence_selection_required": True,
        "draft_artifact_update_allowed_now": False,
        "promotion_planning_allowed_now": False,
        "promotion_allowed_now": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "deferred_lane_processing_allowed": False,
        "a2_a2plus_progression_allowed": False,
    }
    for key, expected in expected_policy.items():
        if policy.get(key) != expected:
            return fail(f"planning_policy {key} mismatch")
    expected_summary = {
        "validation_status": "PASS",
        "source_decision_item_count": EXPECTED_COUNT,
        "planning_group_count": len(groups),
        "planning_item_count": EXPECTED_COUNT,
        "learning_unit_type_counts": EXPECTED_TYPE_COUNTS,
        "field_completion_status_counts": {"PLANNED_NOT_IMPLEMENTED": EXPECTED_COUNT},
        "field_completion_task_count": len(all_tasks),
        "total_placeholder_field_count": decision_placeholder_total,
        "source_evidence_selection_required": True,
        "field_completion_implementation_allowed_now": False,
        "draft_artifact_update_allowed_now": False,
        "promotion_planning_allowed_now": False,
        "promotion_allowed_now": False,
        "foundation_not_final_taxonomy": True,
        "future_extension_allowed": True,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E14_A1A1PlusClearLaneDraftFieldCompletionSourceEvidenceSelection",
        "stop_reason": "OPERATOR_REVIEW_REQUIRED",
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            return fail(f"summary {key} mismatch")
    if summary.get("field_completion_task_kind_counts") != count_by(all_tasks, lambda task: task.get("completion_kind")):
        return fail("field_completion_task_kind_counts mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed"]:
        if report.get(key) is not False:
            return fail(f"report {key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    print("A1/A1+ clear lane draft field completion planning packet validation: PASS")
    print("Planning items:", len(planning_items))
    print("Field completion tasks:", len(all_tasks))
    return True


if __name__ == "__main__":
    try:
        ok = validate()
    except Exception as exc:
        ok = fail(str(exc))
    if not ok:
        sys.exit(1)
