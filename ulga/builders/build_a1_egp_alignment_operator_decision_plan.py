import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
PACKET = BASE / "ulga" / "reports" / "a1_egp_alignment_operator_review_packet.json"
OUT = BASE / "ulga" / "reports" / "a1_egp_alignment_operator_decision_plan.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_operator_decision_plan_summary.json"
TASK_ID = "R7-M103_A1EGPAlignmentOperatorDecisionPlan"

ACTION_BY_DECISION = {
    "COVERED_BY_EXISTING_NODE_REFS": "NO_ACTION_REQUIRED",
    "REVIEW_EXTEND_EXISTING_NODE_EVIDENCE": "OPERATOR_CONFIRM_EXTEND_EXISTING_NODE_EVIDENCE",
    "REVIEW_PATCH_EXISTING_NODE_OR_SPLIT_CLUSTER": "OPERATOR_CHOOSE_PATCH_EXISTING_OR_SPLIT_CLUSTER",
    "REVIEW_CREATE_NODE_OR_MARK_OUT_OF_SCOPE": "OPERATOR_CHOOSE_CREATE_NODE_OR_OUT_OF_SCOPE",
}
ALLOWED_OPERATOR_DECISIONS = {
    "NO_ACTION_REQUIRED",
    "EXTEND_EXISTING_NODE_EVIDENCE",
    "PATCH_EXISTING_NODE_EVIDENCE",
    "SPLIT_CLUSTER_AND_CREATE_NODE",
    "CREATE_NEW_GRAMMAR_NODE",
    "MARK_OUT_OF_SCOPE",
    "DEFER_FOR_SOURCE_REVIEW",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def plan_item(item):
    decision = item.get("decision")
    proposed_action = ACTION_BY_DECISION.get(decision, "OPERATOR_REVIEW_REQUIRED")
    suggested_nodes = [node.get("grammar_id") for node in item.get("suggested_existing_nodes", []) if node.get("grammar_id")]
    default_operator_decision = "NO_ACTION_REQUIRED" if proposed_action == "NO_ACTION_REQUIRED" else "DEFER_FOR_SOURCE_REVIEW"
    return {
        "cluster_id": item.get("cluster_id"),
        "cluster_key": item.get("cluster_key"),
        "decision_from_audit": decision,
        "row_count": item.get("row_count"),
        "missing_row_count": item.get("missing_row_count"),
        "proposed_action": proposed_action,
        "allowed_operator_decisions": sorted(ALLOWED_OPERATOR_DECISIONS),
        "operator_decision": default_operator_decision,
        "target_existing_node_candidates": suggested_nodes[:5],
        "selected_target_node": None,
        "selected_source_refs": [row.get("source_ref") for row in item.get("sample_rows_for_review", []) if row.get("source_ref")],
        "new_node_candidate": None,
        "operator_note": "Fill this record before any canonical grammar patch.",
        "canonical_write_allowed": False,
    }


def main():
    packet = load(PACKET)
    items = packet.get("review_items", [])
    plan_items = [plan_item(item) for item in items]
    action_counts = {}
    decision_counts = {}
    for item in plan_items:
        action_counts[item["proposed_action"]] = action_counts.get(item["proposed_action"], 0) + 1
        decision_counts[item["operator_decision"]] = decision_counts.get(item["operator_decision"], 0) + 1
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_operator_decision_plan",
        "source_artifact_id": packet.get("artifact_id"),
        "decision_mode": "OPERATOR_FILL_REQUIRED_BEFORE_PATCH",
        "plan_items": plan_items,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_operator_decision_plan_summary",
        "validation_status": "PASS",
        "plan_item_count": len(plan_items),
        "proposed_action_counts": dict(sorted(action_counts.items())),
        "operator_decision_counts": dict(sorted(decision_counts.items())),
        "operator_fill_required_count": sum(1 for item in plan_items if item["operator_decision"] == "DEFER_FOR_SOURCE_REVIEW"),
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M104_A1EGPAlignmentOperatorDecisionFill",
        "stop_reason": "OPERATOR_DECISION_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1 EGP alignment operator decision plan build: PASS")
    print("Plan items:", len(plan_items))
    print("Operator fill required:", summary["operator_fill_required_count"])
    print("Proposed action counts:", summary["proposed_action_counts"])


if __name__ == "__main__":
    main()
