import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REPORT = BASE / "ulga" / "reports" / "a1_a1plus_learning_unit_type_review_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_learning_unit_type_review_packet_summary.json"
TASK_ID = "R7-M104E4_A1A1PlusLearningUnitTypeReviewPacket"
VALID_ACTIONS = {
    "APPROVE_LEARNING_UNIT_TYPE_POLICY",
    "ADJUST_LEARNING_UNIT_TYPE_FOR_SELECTED_ITEMS",
    "DEFER_SELECTED_ITEMS_FOR_SOURCE_REVIEW",
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
    print("Validating A1/A1+ learning unit type review packet...")
    report = load(REPORT)
    summary = load(SUMMARY)
    if not isinstance(report, dict) or not isinstance(summary, dict):
        return fail("required review packet files missing")
    if report.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    groups = report.get("review_groups", [])
    if not groups:
        return fail("review_groups missing")
    if not set(VALID_ACTIONS).issubset(set(report.get("allowed_next_actions", []))):
        return fail("allowed_next_actions incomplete")
    group_item_count = 0
    no_action_items = report.get("no_action_items", [])
    type_counts = {}
    decision_counts = {}
    operator_required = 0
    seen = set()
    for group in groups:
        items = group.get("items", [])
        if group.get("item_count") != len(items):
            return fail("group item_count mismatch")
        group_item_count += len(items)
        missing_total = sum(item.get("missing_row_count") or 0 for item in items)
        if group.get("missing_row_count") != missing_total:
            return fail("group missing_row_count mismatch")
        for item in items:
            cid = item.get("cluster_id")
            if not cid or cid in seen:
                return fail("missing or duplicate review cluster_id")
            seen.add(cid)
            if item.get("operator_review_status") != "PENDING_OPERATOR_REVIEW":
                return fail("review item must be pending operator review")
            if item.get("operator_decision_required") is not True:
                return fail("review item must require operator decision")
            if item.get("canonical_grammar_write_allowed") is not False:
                return fail("canonical write must be false")
            type_counts[item.get("learning_unit_type")] = type_counts.get(item.get("learning_unit_type"), 0) + 1
            decision_counts[item.get("recommended_decision_path")] = decision_counts.get(item.get("recommended_decision_path"), 0) + 1
            operator_required += 1
    for item in no_action_items:
        cid = item.get("cluster_id")
        if not cid or cid in seen:
            return fail("missing or duplicate no-action cluster_id")
        seen.add(cid)
        if item.get("operator_review_status") != "NO_ACTION_REQUIRED":
            return fail("no-action item status mismatch")
        if item.get("operator_decision_required") is not False:
            return fail("no-action item must not require operator decision")
        if item.get("canonical_grammar_write_allowed") is not False:
            return fail("no-action canonical write must be false")
        type_counts[item.get("learning_unit_type")] = type_counts.get(item.get("learning_unit_type"), 0) + 1
        decision_counts[item.get("recommended_decision_path")] = decision_counts.get(item.get("recommended_decision_path"), 0) + 1
    if summary.get("review_group_count") != len(groups):
        return fail("review_group_count mismatch")
    if summary.get("review_item_count") != group_item_count:
        return fail("review_item_count mismatch")
    if summary.get("no_action_item_count") != len(no_action_items):
        return fail("no_action_item_count mismatch")
    if summary.get("source_reclassification_item_count") != len(seen):
        return fail("source_reclassification_item_count mismatch")
    if summary.get("learning_unit_type_counts") != dict(sorted(type_counts.items())):
        return fail("learning_unit_type_counts mismatch")
    if summary.get("recommended_decision_path_counts") != dict(sorted(decision_counts.items())):
        return fail("recommended_decision_path_counts mismatch")
    if summary.get("operator_decision_required_count") != operator_required:
        return fail("operator_decision_required_count mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed"]:
        if report.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if report.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if report.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104E5_A1A1PlusLearningUnitTypeOperatorReview":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "OPERATOR_REVIEW_REQUIRED":
        return fail("stop_reason mismatch")
    print("A1/A1+ learning unit type review packet validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
