import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
PLAN = BASE / "ulga" / "reports" / "a1_egp_alignment_operator_decision_plan.json"
OUT = BASE / "ulga" / "reports" / "a1_egp_alignment_top_priority_decision_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_top_priority_decision_packet_summary.json"
TASK_ID = "R7-M104A_A1EGPAlignmentTopPriorityDecisionPacket"
TOP_N = 10


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def priority_score(item):
    action_rank = {
        "OPERATOR_CHOOSE_CREATE_NODE_OR_OUT_OF_SCOPE": 0,
        "OPERATOR_CHOOSE_PATCH_EXISTING_OR_SPLIT_CLUSTER": 1,
        "OPERATOR_CONFIRM_EXTEND_EXISTING_NODE_EVIDENCE": 2,
        "NO_ACTION_REQUIRED": 9,
    }.get(item.get("proposed_action"), 8)
    return (action_rank, -(item.get("missing_row_count") or 0), item.get("cluster_key") or "")


def main():
    plan = load(PLAN)
    items = [item for item in plan.get("plan_items", []) if item.get("operator_decision") != "NO_ACTION_REQUIRED"]
    selected = sorted(items, key=priority_score)[:TOP_N]
    packet_items = []
    for index, item in enumerate(selected, start=1):
        packet_items.append({
            "priority_rank": index,
            "cluster_id": item.get("cluster_id"),
            "cluster_key": item.get("cluster_key"),
            "decision_from_audit": item.get("decision_from_audit"),
            "row_count": item.get("row_count"),
            "missing_row_count": item.get("missing_row_count"),
            "proposed_action": item.get("proposed_action"),
            "target_existing_node_candidates": item.get("target_existing_node_candidates", []),
            "selected_source_refs_preview": item.get("selected_source_refs", [])[:5],
            "operator_decision": item.get("operator_decision"),
            "allowed_operator_decisions": item.get("allowed_operator_decisions", []),
            "required_fill_fields": [
                "operator_decision",
                "selected_target_node",
                "new_node_candidate",
                "operator_note",
            ],
        })
    action_counts = {}
    for item in packet_items:
        action = item.get("proposed_action")
        action_counts[action] = action_counts.get(action, 0) + 1
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_top_priority_decision_packet",
        "source_artifact_id": plan.get("artifact_id"),
        "top_n": TOP_N,
        "selection_policy": "highest_missing_rows_first_with_create_or_out_of_scope_review_first",
        "packet_items": packet_items,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_top_priority_decision_packet_summary",
        "validation_status": "PASS",
        "source_plan_item_count": len(plan.get("plan_items", [])),
        "source_operator_fill_required_count": len(items),
        "top_priority_item_count": len(packet_items),
        "top_priority_missing_row_count": sum(item.get("missing_row_count", 0) for item in packet_items),
        "proposed_action_counts": dict(sorted(action_counts.items())),
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M104B_A1EGPAlignmentTopPriorityOperatorDecisionFill",
        "stop_reason": "OPERATOR_DECISION_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1 EGP alignment top priority decision packet build: PASS")
    print("Top priority items:", len(packet_items))
    print("Top priority missing rows:", summary["top_priority_missing_row_count"])
    print("Proposed action counts:", summary["proposed_action_counts"])


if __name__ == "__main__":
    main()
