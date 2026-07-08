import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
PLAN = BASE / "ulga" / "reports" / "a1_egp_alignment_operator_decision_plan.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_operator_decision_plan_summary.json"
TASK_ID = "R7-M103_A1EGPAlignmentOperatorDecisionPlan"
ALLOWED_OPERATOR_DECISIONS = {
    "NO_ACTION_REQUIRED",
    "EXTEND_EXISTING_NODE_EVIDENCE",
    "PATCH_EXISTING_NODE_EVIDENCE",
    "SPLIT_CLUSTER_AND_CREATE_NODE",
    "CREATE_NEW_GRAMMAR_NODE",
    "MARK_OUT_OF_SCOPE",
    "DEFER_FOR_SOURCE_REVIEW",
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
    print("Validating A1 EGP alignment operator decision plan...")
    plan = load(PLAN)
    summary = load(SUMMARY)
    if not isinstance(plan, dict) or not isinstance(summary, dict):
        return fail("required decision plan files missing")
    if plan.get("task_id") != TASK_ID or summary.get("task_id") != TASK_ID:
        return fail("task_id mismatch")
    items = plan.get("plan_items", [])
    if not items:
        return fail("plan_items missing")
    ids = set()
    action_counts = {}
    decision_counts = {}
    fill_required = 0
    for item in items:
        cid = item.get("cluster_id")
        if not cid or cid in ids:
            return fail("missing or duplicate cluster_id")
        ids.add(cid)
        operator_decision = item.get("operator_decision")
        if operator_decision not in ALLOWED_OPERATOR_DECISIONS:
            return fail("invalid operator_decision")
        allowed = set(item.get("allowed_operator_decisions", []))
        if not ALLOWED_OPERATOR_DECISIONS.issubset(allowed):
            return fail("allowed_operator_decisions incomplete")
        if item.get("canonical_write_allowed") is not False:
            return fail("canonical write must be false")
        if item.get("operator_decision") == "DEFER_FOR_SOURCE_REVIEW":
            fill_required += 1
        action = item.get("proposed_action")
        action_counts[action] = action_counts.get(action, 0) + 1
        decision_counts[operator_decision] = decision_counts.get(operator_decision, 0) + 1
    if summary.get("plan_item_count") != len(items):
        return fail("plan_item_count mismatch")
    if summary.get("proposed_action_counts") != dict(sorted(action_counts.items())):
        return fail("proposed_action_counts mismatch")
    if summary.get("operator_decision_counts") != dict(sorted(decision_counts.items())):
        return fail("operator_decision_counts mismatch")
    if summary.get("operator_fill_required_count") != fill_required:
        return fail("operator_fill_required_count mismatch")
    for key in ["final_closeout_allowed", "a2_a2plus_progression_allowed", "canonical_grammar_write_allowed"]:
        if plan.get(key) is not False or summary.get(key) is not False:
            return fail(f"{key} must be false")
    if plan.get("local_validation_required") is not True:
        return fail("local_validation_required must be true")
    if plan.get("ci_gate_required") is not False:
        return fail("ci_gate_required must be false")
    if summary.get("next_short_step") != "R7-M104_A1EGPAlignmentOperatorDecisionFill":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "OPERATOR_DECISION_REQUIRED":
        return fail("stop_reason mismatch")
    print("A1 EGP alignment operator decision plan validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
