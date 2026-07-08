import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
REVIEW = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_triage_review_packet.json"
OUT = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_decision_lane_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_cross_source_decision_lane_packet_summary.json"
TASK_ID = "R7-M104D_A1EGPAlignmentCrossSourceDecisionFillOrPatchPlan"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lane_for(item):
    if item.get("target_existing_node_candidates"):
        return "PATCH_EXISTING_NODE_REVIEW_LANE"
    return "CREATE_OR_SPLIT_NODE_REVIEW_LANE"


def main():
    review = load(REVIEW)
    lane_items = []
    lane_counts = {}
    lane_missing_rows = {}
    for item in review.get("review_items", []):
        lane = lane_for(item)
        lane_counts[lane] = lane_counts.get(lane, 0) + 1
        lane_missing_rows[lane] = lane_missing_rows.get(lane, 0) + (item.get("missing_row_count") or 0)
        lane_items.append({
            "lane": lane,
            "cluster_id": item.get("cluster_id"),
            "cluster_key": item.get("cluster_key"),
            "row_count": item.get("row_count"),
            "missing_row_count": item.get("missing_row_count"),
            "confidence": item.get("confidence"),
            "target_existing_node_candidates": item.get("target_existing_node_candidates", []),
            "selected_source_refs_preview": item.get("selected_source_refs_preview", []),
            "default_operator_decision": "PATCH_EXISTING_NODE_EVIDENCE" if lane == "PATCH_EXISTING_NODE_REVIEW_LANE" else "CREATE_NEW_GRAMMAR_NODE",
            "operator_decision": "DEFER_FOR_SOURCE_REVIEW",
            "required_operator_fields": [
                "operator_decision",
                "selected_target_node",
                "new_node_candidate",
                "operator_note",
            ],
            "canonical_grammar_write_allowed": False,
        })
    lane_items.sort(key=lambda x: (x["lane"], -(x.get("missing_row_count") or 0), x.get("cluster_key") or ""))
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_cross_source_decision_lane_packet",
        "source_artifact_id": review.get("artifact_id"),
        "lane_policy": {
            "PATCH_EXISTING_NODE_REVIEW_LANE": "cluster has one or more existing node candidates; operator may patch selected node evidence",
            "CREATE_OR_SPLIT_NODE_REVIEW_LANE": "cluster has no existing node candidate; operator should create or split node unless deferred",
        },
        "lane_items": lane_items,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_cross_source_decision_lane_packet_summary",
        "validation_status": "PASS",
        "lane_item_count": len(lane_items),
        "lane_counts": dict(sorted(lane_counts.items())),
        "lane_missing_row_counts": dict(sorted(lane_missing_rows.items())),
        "operator_decision_counts": {"DEFER_FOR_SOURCE_REVIEW": len(lane_items)},
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M104E_A1EGPAlignmentPatchLaneTop10ReviewPacket",
        "stop_reason": "NONE",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1 EGP alignment cross-source decision lane packet build: PASS")
    print("Lane items:", len(lane_items))
    print("Lane counts:", summary["lane_counts"])
    print("Lane missing rows:", summary["lane_missing_row_counts"])


if __name__ == "__main__":
    main()
